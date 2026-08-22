// Headless, deterministic game simulation.
//
// This assembly MUST NOT depend on UnityEngine. `Sim.asmdef` sets
// "noEngineReferences": true, so the compiler enforces it: no MonoBehaviour, no
// UnityEngine.Vector2, no Time.deltaTime, no UnityEngine.Random. It is the
// single source of truth for game state and is fully testable in EditMode with
// no scene, no GameObject and no GPU.
//
// WHAT IS HERE TODAY IS A PLACEHOLDER, NOT A GAME. One entity drifts around a
// box and reflects off the walls. It exists so the harness has something to
// assert on. Replace it with the real rules; keep the shape.
//
// Determinism rules enforced here:
// - the tick pipeline is an explicit ordered list of stages (SimState.Step)
// - stages read intent (Intents), never Input.GetKey
// - no wall-clock reads; tick count comes from SimState.Tick
// - order-sensitive passes sort on SimId, never on list position
// - randomness comes from SimRng, which is part of snapshotted state

using System;
using System.Collections.Generic;

namespace Starter.Sim
{
    public static class Constants
    {
        /// Fixed simulation rate. A power of two so 1/TICK_HZ is exact in binary
        /// floating point, which matters for reproducible accumulation.
        public const int TICK_HZ = 64;

        /// Duration of one tick in seconds. Exact in float (1/64).
        public const float TICK_DT = 1.0f / TICK_HZ;

        public const float ARENA_HALF_WIDTH = 400.0f;
        public const float ARENA_HALF_HEIGHT = 250.0f;

        /// Half the side length of the marker's square body.
        public const float MARKER_HALF_SIZE = 12.0f;

        /// The marker's invariant speed, in world units per second.
        public const float MARKER_SPEED = 220.0f;

        /// How hard one tick of input pushes the marker's vertical velocity
        /// before the speed invariant is re-applied.
        public const float NUDGE_SPEED = 300.0f;
    }

    /// Simulation-owned 2D vector.
    ///
    /// Deliberately NOT UnityEngine.Vector2: the simulation must be compilable
    /// and testable without the engine, and Unity's math types have historically
    /// changed implementation between versions.
    public readonly struct Vec2 : IEquatable<Vec2>
    {
        public readonly float X;
        public readonly float Y;

        public Vec2(float x, float y) { X = x; Y = y; }

        public static readonly Vec2 Zero = new Vec2(0f, 0f);

        public static Vec2 operator +(Vec2 a, Vec2 b) => new Vec2(a.X + b.X, a.Y + b.Y);
        public static Vec2 operator -(Vec2 a, Vec2 b) => new Vec2(a.X - b.X, a.Y - b.Y);
        public static Vec2 operator *(Vec2 a, float s) => new Vec2(a.X * s, a.Y * s);
        public static Vec2 operator /(Vec2 a, float s) => new Vec2(a.X / s, a.Y / s);

        public float LengthSquared => X * X + Y * Y;
        public float Length => (float)Math.Sqrt(LengthSquared);

        /// Scale down to `max` if longer. Mirrors glam's `clamp_length_max`.
        public Vec2 ClampLengthMax(float max)
        {
            float lengthSq = LengthSquared;
            return lengthSq > max * max ? (this / (float)Math.Sqrt(lengthSq)) * max : this;
        }

        /// Rescale to exactly `length`, keeping direction. A zero vector has no
        /// direction to keep, so it is returned untouched rather than turned
        /// into an arbitrary one.
        public Vec2 WithLength(float length)
        {
            float lengthSq = LengthSquared;
            if (lengthSq <= 0f) return this;
            // NOTE ON CROSS-STACK PARITY, and why this is not "fixed":
            // driven through an identical 400-tick tape at seed 7, the Rust,
            // TypeScript and Godot starters produce byte-identical state hashes on
            // all 401 lines; this one matches 400 of 401, differing by a single ULP
            // in vx at tick 53. Reordering the divide and the multiply to match the
            // other stacks was tried and moved the divergence to tick 41 rather than
            // removing it - Mono's float pipeline is a property of the stack under
            // comparison, not a defect to engineer around. Cross-stack hash equality
            // is deliberately NOT a requirement; within-stack determinism is, and
            // that holds (see the determinism tests).
            return (this / (float)Math.Sqrt(lengthSq)) * length;
        }

        public Vec2 WithX(float x) => new Vec2(x, Y);
        public Vec2 WithY(float y) => new Vec2(X, y);

        public static bool operator ==(Vec2 a, Vec2 b) => a.Equals(b);
        public static bool operator !=(Vec2 a, Vec2 b) => !a.Equals(b);

        public bool Equals(Vec2 other) => X.Equals(other.X) && Y.Equals(other.Y);
        public override bool Equals(object obj) => obj is Vec2 v && Equals(v);
        public override int GetHashCode() => (X.GetHashCode() * 397) ^ Y.GetHashCode();
        public override string ToString() => $"({X}, {Y})";
    }

    /// The kinds of body the simulation knows how to spawn.
    ///
    /// The starter has exactly one. A real game adds more here, and gives each
    /// new kind a visual in the view deliberately.
    public enum EntityKind { Marker = 0 }

    // ----------------------------------------------------------------------
    // Intent — the only way input enters the simulation
    // ----------------------------------------------------------------------

    /// Intent for the current tick.
    ///
    /// The simulation reads *this*, never `UnityEngine.Input`. Device state is
    /// frame-scoped, not tick-scoped: a fixed step may run 0, 1, or many times
    /// per frame, so reading devices inside the simulation drops or duplicates
    /// inputs. The client translates devices into intent once per frame; a
    /// remote peer sends intent over the wire. Both feed the same simulation.
    public readonly struct Intents : IEquatable<Intents>
    {
        public readonly bool NudgeUp;
        public readonly bool NudgeDown;

        public Intents(bool nudgeUp, bool nudgeDown)
        {
            NudgeUp = nudgeUp;
            NudgeDown = nudgeDown;
        }

        /// -1 down, 0 still, +1 up. Opposing inputs cancel.
        public float Axis() => (NudgeUp ? 1f : 0f) - (NudgeDown ? 1f : 0f);

        /// Nothing held. Spelled out rather than `default` so the meaning is
        /// readable at the call site.
        public static readonly Intents None = new Intents(false, false);

        public static bool operator ==(Intents a, Intents b) => a.Equals(b);
        public static bool operator !=(Intents a, Intents b) => !a.Equals(b);

        public bool Equals(Intents o) => NudgeUp == o.NudgeUp && NudgeDown == o.NudgeDown;
        public override bool Equals(object o) => o is Intents i && Equals(i);
        public override int GetHashCode() => (NudgeUp ? 1 : 0) | (NudgeDown ? 2 : 0);
    }

    // ----------------------------------------------------------------------
    // Simulation state
    // ----------------------------------------------------------------------

    /// Deterministic PRNG (PCG-XSH-RR 64/32), seeded explicitly and carried in
    /// the snapshot. Never use `UnityEngine.Random`, `System.Random`, or any OS
    /// entropy source in the simulation: it would make replay and rollback
    /// impossible.
    public struct SimRng : IEquatable<SimRng>
    {
        private const ulong MUL = 6364136223846793005UL;
        private const ulong INC = 1442695040888963407UL;

        private ulong _state;

        public static SimRng FromSeed(ulong seed)
        {
            var rng = new SimRng { _state = 0UL };
            rng.NextU32();
            rng._state = unchecked(rng._state + seed);
            rng.NextU32();
            return rng;
        }

        public uint NextU32()
        {
            ulong old = _state;
            _state = unchecked(old * MUL + INC);
            uint xorshifted = (uint)(((old >> 18) ^ old) >> 27);
            int rot = (int)(old >> 59);
            return RotateRight(xorshifted, rot);
        }

        private static uint RotateRight(uint value, int amount) =>
            (value >> amount) | (value << ((32 - amount) & 31));

        /// Uniform in [0, 1).
        public float NextFloat() =>
            // 24 bits of mantissa, exactly representable, no rounding surprise.
            (NextU32() >> 8) / (float)(1u << 24);

        /// Uniform in [lo, hi).
        public float RangeFloat(float lo, float hi) => lo + NextFloat() * (hi - lo);

        public bool CoinFlip() => (NextU32() & 1u) == 1u;

        public static bool operator ==(SimRng a, SimRng b) => a.Equals(b);
        public static bool operator !=(SimRng a, SimRng b) => !a.Equals(b);

        public bool Equals(SimRng o) => _state == o._state;
        public override bool Equals(object o) => o is SimRng r && Equals(r);
        public override int GetHashCode() => _state.GetHashCode();
    }

    /// What happened during the tick that just ran. Consumed by presentation
    /// layers for sound and VFX, by tests, and by the probe protocol.
    ///
    /// This is per-tick state that is cleared at the start of every tick, not an
    /// event queue: queues drain on a frame boundary, and a fixed step may run
    /// zero or many times per frame, so a queue would drop or duplicate.
    ///
    /// `Names` is the flat, machine-readable projection the probe emits. Keep
    /// pushing a name for anything a driver outside the process should be able
    /// to notice.
    public sealed class TickEvents
    {
        /// How many wall reflections happened this tick.
        public uint Bounces;

        /// One string per notable thing that happened, in the order it happened.
        public readonly List<string> Names = new List<string>();

        public void Clear()
        {
            Bounces = 0;
            Names.Clear();
        }

        public void Bounce()
        {
            Bounces += 1;
            Names.Add("bounce");
        }

        public TickEvents Snapshot()
        {
            var copy = new TickEvents { Bounces = Bounces };
            copy.Names.AddRange(Names);
            return copy;
        }
    }

    /// One simulated body.
    ///
    /// `SimId` is the stable identity. Never sort, serialise, or send on list
    /// position: it changes when entities are added or removed. Sort on SimId.
    public sealed class SimEntity
    {
        public int SimId;
        public EntityKind Kind;
        public Vec2 Position;
        public Vec2 Velocity;
    }

    /// Declares which parts of `SimState` a stage is allowed to write.
    ///
    /// Names are member paths as seen from `SimState`: `Rng`,
    /// `Entities[].Position`. A declared name also covers everything under it,
    /// so `Events` covers `Events.Names`.
    ///
    /// This is not documentation. `StageAccessTests` runs each stage, watches
    /// what it actually changed by reflection, and fails if a stage writes
    /// something it did not declare — or declares something it never writes.
    [AttributeUsage(AttributeTargets.Field)]
    public sealed class WritesAttribute : Attribute
    {
        public string[] Members { get; }

        public WritesAttribute(params string[] members) => Members = members;
    }

    /// Ordered stages of one simulation tick.
    ///
    /// Declared explicitly and executed in this order by `SimState.Step`. A
    /// total order is the only ordering guarantee worth relying on, and lockstep
    /// replay needs one.
    ///
    /// A new stage must be added here, to `SimState.Stages`, to
    /// `SimState.RunStage`, and must declare its writes. Three tests enforce
    /// that; none of them is satisfied by comments.
    public enum SimStage
    {
        /// Advance the tick counter and clear per-tick event state.
        [Writes("Tick", "Events")]
        Begin = 0,

        /// Apply intent to velocities.
        [Writes("Entities[].Velocity")]
        Intent = 1,

        /// Integrate positions.
        [Writes("Entities[].Position")]
        Motion = 2,

        /// Resolve collisions.
        [Writes("Entities[].Position", "Entities[].Velocity", "Events")]
        Collision = 3,

        /// Outcome resolution: whatever decides that a round, a life or a run
        /// has ended, and what happens next.
        ///
        /// INTENTIONALLY EMPTY IN THE STARTER. The placeholder has no outcome to
        /// resolve, so the body is a no-op and the attribute declares nothing.
        /// The stage keeps its slot because the pipeline shape is part of the
        /// harness: removing it and adding it back later shifts every recorded
        /// replay.
        [Writes]
        Scoring = 4,
    }

    /// The headless simulation. Contains no rendering, windowing, audio, or
    /// input.
    public sealed class SimState
    {
        public const int MarkerId = 1;

        /// The order in which `Step` runs its stages. Public so a test can
        /// assert the pipeline is explicitly ordered rather than incidental.
        public static readonly SimStage[] Stages =
        {
            SimStage.Begin, SimStage.Intent, SimStage.Motion,
            SimStage.Collision, SimStage.Scoring,
        };

        /// Monotonic simulation tick counter. Simulation code uses this instead
        /// of any wall clock so that a replay produces byte-identical results.
        public ulong Tick { get; private set; }

        public SimRng Rng;
        public readonly TickEvents Events = new TickEvents();

        /// Entities in SimId order. Kept sorted on construction; every
        /// order-sensitive pass sorts or relies on this invariant explicitly.
        public readonly List<SimEntity> Entities = new List<SimEntity>();

        /// Deterministic initial world. Ids are assigned explicitly and never
        /// derived from allocation or insertion order.
        public SimState(ulong seed)
        {
            Rng = SimRng.FromSeed(seed);
            Entities.Add(new SimEntity
            {
                SimId = MarkerId,
                Kind = EntityKind.Marker,
                Position = Vec2.Zero,
                Velocity = StartVelocity(ref Rng),
            });
            SortById();
        }

        private void SortById() => Entities.Sort((a, b) => a.SimId.CompareTo(b.SimId));

        public SimEntity Marker => Find(MarkerId);

        public SimEntity Find(int simId)
        {
            foreach (var e in Entities)
            {
                if (e.SimId == simId) return e;
            }
            return null;
        }

        /// The one place the seed turns into world state: a coin flip for the
        /// horizontal sign, then a small random angle. Two RNG draws, in this
        /// order — changing the call sequence changes every seeded run.
        private static Vec2 StartVelocity(ref SimRng rng)
        {
            bool positiveX = rng.CoinFlip();
            // Keep the direction away from vertical so the run is not degenerate.
            float angle = rng.RangeFloat(-0.5f, 0.5f);
            var dir = new Vec2(
                (positiveX ? 1f : -1f) * (float)Math.Cos(angle),
                (float)Math.Sin(angle));
            return dir * Constants.MARKER_SPEED;
        }

        /// Advance exactly one fixed tick. One call == one tick, always.
        public void Step(Intents intents)
        {
            foreach (var stage in Stages) RunStage(stage, intents);
        }

        /// Run a single stage. `Step` is exactly this, in `Stages` order.
        ///
        /// Public so `StageAccessTests` can run one stage at a time and watch
        /// what it writes. Do not call it from gameplay code: a partial tick is
        /// not a tick, and the hash chain would not line up.
        public void RunStage(SimStage stage, Intents intents)
        {
            switch (stage)
            {
                case SimStage.Begin: BeginTick(); break;
                case SimStage.Intent: ApplyIntent(intents); break;
                case SimStage.Motion: IntegrateMotion(); break;
                case SimStage.Collision: CollideWalls(); break;
                case SimStage.Scoring: RunScoring(); break;
                default:
                    throw new ArgumentOutOfRangeException(
                        nameof(stage),
                        $"SimStage.{stage} has no implementation in SimState.RunStage. " +
                        "A stage that does nothing is a silently dropped tick phase.");
            }
        }

        private void BeginTick()
        {
            Tick += 1;
            Events.Clear();
        }

        private void ApplyIntent(Intents intents)
        {
            float axis = intents.Axis();
            if (axis == 0f) return;

            foreach (var e in Entities)
            {
                if (e.Kind != EntityKind.Marker) continue;
                var pushed = e.Velocity.WithY(
                    e.Velocity.Y + axis * Constants.NUDGE_SPEED * Constants.TICK_DT);
                // Input steers, it does not accelerate: the speed is invariant,
                // so only the direction can change.
                e.Velocity = pushed.WithLength(Constants.MARKER_SPEED);
            }
        }

        private void IntegrateMotion()
        {
            // `Entities` is maintained in SimId order so integration order is
            // independent of insertion order. Integration is per-entity and
            // order-independent today, but the invariant keeps it correct if
            // someone later introduces coupling.
            foreach (var e in Entities)
            {
                e.Position += e.Velocity * Constants.TICK_DT;
            }
        }

        private void CollideWalls()
        {
            foreach (var e in Entities)
            {
                if (e.Kind != EntityKind.Marker) continue;

                float limitX = Constants.ARENA_HALF_WIDTH - Constants.MARKER_HALF_SIZE;
                float limitY = Constants.ARENA_HALF_HEIGHT - Constants.MARKER_HALF_SIZE;

                if (e.Position.X > limitX)
                {
                    e.Position = e.Position.WithX(Reflect(e.Position.X, limitX));
                    e.Velocity = e.Velocity.WithX(-e.Velocity.X);
                    Events.Bounce();
                }
                else if (e.Position.X < -limitX)
                {
                    e.Position = e.Position.WithX(-Reflect(-e.Position.X, limitX));
                    e.Velocity = e.Velocity.WithX(-e.Velocity.X);
                    Events.Bounce();
                }

                if (e.Position.Y > limitY)
                {
                    e.Position = e.Position.WithY(Reflect(e.Position.Y, limitY));
                    e.Velocity = e.Velocity.WithY(-e.Velocity.Y);
                    Events.Bounce();
                }
                else if (e.Position.Y < -limitY)
                {
                    e.Position = e.Position.WithY(-Reflect(-e.Position.Y, limitY));
                    e.Velocity = e.Velocity.WithY(-e.Velocity.Y);
                    Events.Bounce();
                }
            }
        }

        /// Mirror an overshoot back inside the wall, then clamp: a single tick
        /// can never overshoot by more than the arena, but a future change to
        /// the speed could, and a body outside the box is worse than a body that
        /// merely stopped.
        private static float Reflect(float coordinate, float limit)
        {
            float mirrored = limit - (coordinate - limit);
            return mirrored < -limit ? -limit : mirrored;
        }

        private static void RunScoring()
        {
            // INTENTIONALLY EMPTY IN THE STARTER. The placeholder has no round,
            // no life and no end condition to resolve, so there is nothing to do
            // here — but the stage keeps its slot in the pipeline. See the
            // comment on SimStage.Scoring.
        }

        // ------------------------------------------------------------------
        // State hashing — the backbone of replay and desync detection
        // ------------------------------------------------------------------

        /// A whole-world checksum for a single tick.
        ///
        /// Floats are hashed via their bit pattern so the hash is exact rather
        /// than tolerance-based: a replay either reproduces the run bit-for-bit
        /// or it does not. Entities are visited in SimId order so the hash
        /// cannot depend on storage layout.
        public ulong StateHash()
        {
            // FNV-1a, chosen because it is trivially reimplementable in any
            // language, so external tooling can verify hashes too.
            const ulong OFFSET = 0xcbf29ce484222325UL;
            ulong hash = OFFSET;

            Feed(ref hash, Tick);

            var rows = new List<SimEntity>(Entities);
            rows.Sort((a, b) => a.SimId.CompareTo(b.SimId));
            foreach (var e in rows)
            {
                Feed(ref hash, (ulong)(uint)e.SimId);
                Feed(ref hash, FloatBits(e.Position.X));
                Feed(ref hash, FloatBits(e.Position.Y));
                Feed(ref hash, FloatBits(e.Velocity.X));
                Feed(ref hash, FloatBits(e.Velocity.Y));
            }
            return hash;
        }

        /// Raw IEEE-754 bit pattern of a float.
        ///
        /// `BitConverter.SingleToUInt32Bits` is .NET 6+; Unity 6's netstandard
        /// 2.1 profile only ships `SingleToInt32Bits`. The reinterpret cast
        /// below is bit-identical — same bytes, different signedness.
        public static uint FloatBits(float value) =>
            unchecked((uint)BitConverter.SingleToInt32Bits(value));

        internal static void Feed(ref ulong hash, ulong value)
        {
            const ulong PRIME = 0x00000100000001b3UL;
            for (int i = 0; i < 8; i++)
            {
                hash ^= (value >> (i * 8)) & 0xFFUL;
                hash = unchecked(hash * PRIME);
            }
        }
    }
}
