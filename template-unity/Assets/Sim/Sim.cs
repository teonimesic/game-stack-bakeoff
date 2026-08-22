// Headless, deterministic game simulation.
//
// This assembly MUST NOT depend on UnityEngine. `Sim.asmdef` sets
// "noEngineReferences": true, so the compiler enforces it: no MonoBehaviour, no
// UnityEngine.Vector2, no Time.deltaTime, no UnityEngine.Random. It is the
// single source of truth for game state and is fully testable in EditMode with
// no scene, no GameObject and no GPU.
//
// Determinism rules enforced here:
// - the tick pipeline is an explicit ordered list of stages (SimState.Step)
// - stages read intent (PlayerIntent), never Input.GetKey
// - no wall-clock reads; tick count comes from SimState.Tick
// - order-sensitive passes sort on SimId, never on list position
// - randomness comes from SimRng, which is part of snapshotted state

using System;
using System.Collections.Generic;

namespace Pong.Sim
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
        public const float PADDLE_HALF_HEIGHT = 50.0f;
        public const float PADDLE_INSET = 370.0f;
        public const float PADDLE_SPEED = 300.0f;
        public const float BALL_RADIUS = 8.0f;
        public const float BALL_START_SPEED = 250.0f;

        /// Multiplier applied to ball speed on every paddle hit.
        public const float BALL_SPEEDUP = 1.05f;
        public const float MAX_BALL_SPEED = 900.0f;
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

        public Vec2 WithX(float x) => new Vec2(x, Y);
        public Vec2 WithY(float y) => new Vec2(X, y);

        public static bool operator ==(Vec2 a, Vec2 b) => a.Equals(b);
        public static bool operator !=(Vec2 a, Vec2 b) => !a.Equals(b);

        public bool Equals(Vec2 other) => X.Equals(other.X) && Y.Equals(other.Y);
        public override bool Equals(object obj) => obj is Vec2 v && Equals(v);
        public override int GetHashCode() => (X.GetHashCode() * 397) ^ Y.GetHashCode();
        public override string ToString() => $"({X}, {Y})";
    }

    /// Which player a paddle belongs to.
    public enum Side { Left = 0, Right = 1 }

    public enum EntityKind { Paddle = 0, Ball = 1 }

    // ----------------------------------------------------------------------
    // Intent — the only way input enters the simulation
    // ----------------------------------------------------------------------

    /// Per-player intent for the current tick.
    ///
    /// The simulation reads *this*, never `UnityEngine.Input`. Device state is
    /// frame-scoped, not tick-scoped: a fixed step may run 0, 1, or many times
    /// per frame, so reading devices inside the simulation drops or duplicates
    /// inputs. The client translates devices into intent once per frame; a
    /// server receives intent over the wire. Both feed the same simulation.
    public readonly struct PlayerIntent : IEquatable<PlayerIntent>
    {
        public readonly bool Up;
        public readonly bool Down;

        public PlayerIntent(bool up, bool down) { Up = up; Down = down; }

        /// -1 down, 0 still, +1 up. Opposing inputs cancel.
        public float Axis() => (Up ? 1f : 0f) - (Down ? 1f : 0f);

        public static bool operator ==(PlayerIntent a, PlayerIntent b) => a.Equals(b);
        public static bool operator !=(PlayerIntent a, PlayerIntent b) => !a.Equals(b);

        public bool Equals(PlayerIntent o) => Up == o.Up && Down == o.Down;
        public override bool Equals(object o) => o is PlayerIntent p && Equals(p);
        public override int GetHashCode() => (Up ? 1 : 0) | (Down ? 2 : 0);
    }

    /// Intent for both players this tick.
    public readonly struct Intents : IEquatable<Intents>
    {
        public readonly PlayerIntent Left;
        public readonly PlayerIntent Right;

        public Intents(PlayerIntent left, PlayerIntent right) { Left = left; Right = right; }

        /// Both players idle. Spelled out rather than `default` so the meaning
        /// is readable at the call site.
        public static readonly Intents None =
            new Intents(new PlayerIntent(false, false), new PlayerIntent(false, false));

        public static bool operator ==(Intents a, Intents b) => a.Equals(b);
        public static bool operator !=(Intents a, Intents b) => !a.Equals(b);

        public bool Equals(Intents o) => Left.Equals(o.Left) && Right.Equals(o.Right);
        public override bool Equals(object o) => o is Intents i && Equals(i);
        public override int GetHashCode() => (Left.GetHashCode() * 397) ^ Right.GetHashCode();
    }

    // ----------------------------------------------------------------------
    // Simulation state
    // ----------------------------------------------------------------------

    public struct Score : IEquatable<Score>
    {
        public uint Left;
        public uint Right;

        public static bool operator ==(Score a, Score b) => a.Equals(b);
        public static bool operator !=(Score a, Score b) => !a.Equals(b);

        public bool Equals(Score o) => Left == o.Left && Right == o.Right;
        public override bool Equals(object o) => o is Score s && Equals(s);
        public override int GetHashCode() => (int)(Left * 397 + Right);
        public override string ToString() => $"{Left}-{Right}";
    }

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
    /// layers for sound and VFX, and by tests.
    ///
    /// This is per-tick state that is cleared at the start of every tick, not an
    /// event queue: queues drain on a frame boundary, and a fixed step may run
    /// zero or many times per frame, so a queue would drop or duplicate.
    public sealed class TickEvents
    {
        public readonly List<Side> PaddleHits = new List<Side>();
        public uint WallBounces;
        public Side? Scored;

        public void Clear()
        {
            PaddleHits.Clear();
            WallBounces = 0;
            Scored = null;
        }

        public TickEvents Snapshot()
        {
            var copy = new TickEvents { WallBounces = WallBounces, Scored = Scored };
            copy.PaddleHits.AddRange(PaddleHits);
            return copy;
        }
    }

    /// One simulated body.
    ///
    /// `SimId` is the stable identity. Never sort, serialise, or network on list
    /// position: it changes when entities are added or removed. Sort on SimId.
    public sealed class SimEntity
    {
        public int SimId;
        public EntityKind Kind;
        /// Only meaningful for paddles.
        public Side Side;
        public Vec2 Position;
        public Vec2 Velocity;
    }

    /// Declares which parts of `SimState` a stage is allowed to write.
    ///
    /// Names are member paths as seen from `SimState`: `Score`, `Rng`,
    /// `Entities[].Position`. A declared name also covers everything under it,
    /// so `Events` covers `Events.PaddleHits`.
    ///
    /// This is not documentation. `StageAccessTests` runs each stage, observes
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
    /// netcode needs one.
    ///
    /// A new stage must be added here, to `SimState.Stages`, to
    /// `SimState.RunStage`, and must declare its writes. Three tests enforce
    /// that; none of them is satisfied by comments.
    public enum SimStage
    {
        /// Advance the tick counter and clear per-tick event state.
        [Writes("Tick", "Events")]
        Begin = 0,

        /// Apply intent to paddle velocities.
        [Writes("Entities[].Velocity")]
        Intent = 1,

        /// Integrate positions.
        [Writes("Entities[].Position")]
        Motion = 2,

        /// Resolve collisions.
        [Writes("Entities[].Position", "Entities[].Velocity", "Events")]
        Collision = 3,

        /// Scoring and round reset.
        [Writes("Score", "Events", "Entities[].Position", "Entities[].Velocity", "Rng")]
        Scoring = 4,
    }

    /// The headless simulation. Contains no rendering, windowing, audio, or
    /// input.
    public sealed class SimState
    {
        public const int LeftPaddleId = 1;
        public const int RightPaddleId = 2;
        public const int BallId = 3;

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

        public Score Score;
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
                SimId = LeftPaddleId,
                Kind = EntityKind.Paddle,
                Side = Side.Left,
                Position = new Vec2(-Constants.PADDLE_INSET, 0f),
                Velocity = Vec2.Zero,
            });
            Entities.Add(new SimEntity
            {
                SimId = RightPaddleId,
                Kind = EntityKind.Paddle,
                Side = Side.Right,
                Position = new Vec2(Constants.PADDLE_INSET, 0f),
                Velocity = Vec2.Zero,
            });
            Entities.Add(new SimEntity
            {
                SimId = BallId,
                Kind = EntityKind.Ball,
                Position = Vec2.Zero,
                Velocity = ServeVelocity(ref Rng),
            });
            SortById();
        }

        private void SortById() => Entities.Sort((a, b) => a.SimId.CompareTo(b.SimId));

        public SimEntity Ball => Find(BallId);
        public SimEntity Paddle(Side side) => Find(side == Side.Left ? LeftPaddleId : RightPaddleId);

        public SimEntity Find(int simId)
        {
            foreach (var e in Entities)
            {
                if (e.SimId == simId) return e;
            }
            return null;
        }

        private static Vec2 ServeVelocity(ref SimRng rng)
        {
            bool towardRight = rng.CoinFlip();
            // Keep the serve away from near-vertical so rallies actually start.
            float angle = rng.RangeFloat(-0.5f, 0.5f);
            var dir = new Vec2(
                (towardRight ? 1f : -1f) * (float)Math.Cos(angle),
                (float)Math.Sin(angle));
            return dir * Constants.BALL_START_SPEED;
        }

        /// Advance exactly one fixed tick. One call == one tick, always.
        public void Step(Intents intents)
        {
            foreach (var stage in Stages) RunStage(stage, intents);
        }

        /// Run a single stage. `Step` is exactly this, in `Stages` order.
        ///
        /// Public so `StageAccessTests` can run one stage at a time and observe
        /// what it writes. Do not call it from gameplay code: a partial tick is
        /// not a tick, and the hash chain would not line up.
        public void RunStage(SimStage stage, Intents intents)
        {
            switch (stage)
            {
                case SimStage.Begin: BeginTick(); break;
                case SimStage.Intent: ApplyIntent(intents); break;
                case SimStage.Motion: IntegrateMotion(); break;
                case SimStage.Collision: CollideWalls(); CollidePaddles(); break;
                case SimStage.Scoring: ScoreAndReset(); break;
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
            foreach (var e in Entities)
            {
                if (e.Kind != EntityKind.Paddle) continue;
                var intent = e.Side == Side.Left ? intents.Left : intents.Right;
                e.Velocity = new Vec2(0f, intent.Axis() * Constants.PADDLE_SPEED);
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
                if (e.Kind == EntityKind.Paddle)
                {
                    // Paddles clamp against the arena and stop dead.
                    float limit = Constants.ARENA_HALF_HEIGHT - Constants.PADDLE_HALF_HEIGHT;
                    if (e.Position.Y > limit)
                    {
                        e.Position = e.Position.WithY(limit);
                        e.Velocity = e.Velocity.WithY(0f);
                    }
                    else if (e.Position.Y < -limit)
                    {
                        e.Position = e.Position.WithY(-limit);
                        e.Velocity = e.Velocity.WithY(0f);
                    }
                }
                else if (e.Kind == EntityKind.Ball)
                {
                    float limit = Constants.ARENA_HALF_HEIGHT - Constants.BALL_RADIUS;
                    if (e.Position.Y > limit)
                    {
                        e.Position = e.Position.WithY(limit - (e.Position.Y - limit));
                        e.Velocity = e.Velocity.WithY(-e.Velocity.Y);
                        Events.WallBounces += 1;
                    }
                    else if (e.Position.Y < -limit)
                    {
                        e.Position = e.Position.WithY(-limit - (e.Position.Y + limit));
                        e.Velocity = e.Velocity.WithY(-e.Velocity.Y);
                        Events.WallBounces += 1;
                    }
                }
            }
        }

        private void CollidePaddles()
        {
            // Deterministic paddle order: without the SimId ordering invariant,
            // two paddles that could both claim the ball on the same tick would
            // resolve in whatever order they happen to sit in the list.
            foreach (var ball in Entities)
            {
                if (ball.Kind != EntityKind.Ball) continue;
                foreach (var paddle in Entities)
                {
                    if (paddle.Kind != EntityKind.Paddle) continue;

                    float faceX = paddle.Side == Side.Left
                        ? paddle.Position.X + Constants.BALL_RADIUS
                        : paddle.Position.X - Constants.BALL_RADIUS;
                    bool movingInto = paddle.Side == Side.Left
                        ? ball.Velocity.X < 0f && ball.Position.X <= faceX
                        : ball.Velocity.X > 0f && ball.Position.X >= faceX;
                    bool verticallyOverlapping =
                        Math.Abs(ball.Position.Y - paddle.Position.Y)
                        <= Constants.PADDLE_HALF_HEIGHT + Constants.BALL_RADIUS;

                    if (movingInto && verticallyOverlapping)
                    {
                        ball.Position = ball.Position.WithX(faceX);
                        ball.Velocity = ball.Velocity.WithX(-ball.Velocity.X);
                        // Deflection angle depends on where the ball struck.
                        float offset = (ball.Position.Y - paddle.Position.Y)
                                       / Constants.PADDLE_HALF_HEIGHT;
                        ball.Velocity = ball.Velocity.WithY(
                            ball.Velocity.Y + offset * Constants.BALL_START_SPEED * 0.5f);
                        ball.Velocity = (ball.Velocity * Constants.BALL_SPEEDUP)
                            .ClampLengthMax(Constants.MAX_BALL_SPEED);
                        Events.PaddleHits.Add(paddle.Side);
                        break;
                    }
                }
            }
        }

        private void ScoreAndReset()
        {
            foreach (var ball in Entities)
            {
                if (ball.Kind != EntityKind.Ball) continue;

                Side? scorer = null;
                if (ball.Position.X > Constants.ARENA_HALF_WIDTH) scorer = Side.Left;
                else if (ball.Position.X < -Constants.ARENA_HALF_WIDTH) scorer = Side.Right;

                if (scorer.HasValue)
                {
                    if (scorer.Value == Side.Left) Score.Left += 1;
                    else Score.Right += 1;
                    Events.Scored = scorer;
                    ball.Position = Vec2.Zero;
                    ball.Velocity = ServeVelocity(ref Rng);
                }
            }
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
            Feed(ref hash, Score.Left);
            Feed(ref hash, Score.Right);

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
