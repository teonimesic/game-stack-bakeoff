// Determinism guarantees. These tests are the template's backstop: they fail
// loudly when a change makes the simulation depend on iteration order, wall
// clock, or unseeded entropy.
//
// If one of these fails, DO NOT relax the assertion. An exact hash comparison
// that becomes an approximate one is worthless. Find the nondeterminism.

using System.Collections.Generic;
using NUnit.Framework;
using Starter.Sim;

namespace Starter.Sim.Tests
{
    public class DeterminismTests
    {
        internal static Intents[] AlternatingInputs(int ticks)
        {
            // A pattern that actually pushes the world around, so the hash chain
            // exercises input handling and collisions rather than a body left
            // completely alone.
            var inputs = new Intents[ticks];
            for (int t = 0; t < ticks; t++)
            {
                inputs[t] = new Intents((t / 17) % 2 == 0, (t / 23) % 2 == 1);
            }
            return inputs;
        }

        [Test]
        public void IdenticalReplaysProduceIdenticalHashChains()
        {
            var replay = new Replay(0xDEADBEEF, AlternatingInputs(600));
            Assert.AreEqual(-1, Replay.FindDivergence(replay),
                "the same replay produced different state on two runs — the simulation " +
                "is reading something outside its snapshot (iteration order, wall clock, " +
                "or unseeded RNG)");
        }

        [Test]
        public void DifferentSeedsProduceDifferentRuns()
        {
            // Guards against the opposite failure: a "deterministic" simulation
            // that is actually ignoring its seed would pass every determinism
            // test trivially.
            var a = Replay.Run(Replay.Idle(1, 400));
            var b = Replay.Run(Replay.Idle(2, 400));
            Assert.AreNotEqual(a.Digest(), b.Digest(),
                "two different seeds produced identical runs — the seed is not reaching " +
                "the simulation");
        }

        [Test]
        public void DifferentInputsProduceDifferentRuns()
        {
            const ulong seed = 7;
            var idle = Replay.Run(Replay.Idle(seed, 400));
            var active = Replay.Run(new Replay(seed, AlternatingInputs(400)));
            Assert.AreNotEqual(idle.Digest(), active.Digest(),
                "player intent had no effect on the simulation");
        }

        [Test]
        public void TickCountIsExactlyTheNumberOfUpdates()
        {
            // This asserts that one Step() is one tick, always. If it regresses,
            // every other determinism test silently becomes time-dependent.
            foreach (int ticks in new[] { 1, 10, 137 })
            {
                var outcome = Replay.Run(Replay.Idle(3, ticks));
                Assert.AreEqual((ulong)ticks, outcome.FinalTick,
                    $"expected exactly {ticks} fixed ticks from {ticks} updates");
                Assert.AreEqual(ticks, outcome.Hashes.Count);
            }
        }

        [Test]
        public void ReplayIsResumableFromAPrefix()
        {
            // A replay's first N hashes must not depend on what comes after
            // them. This is what makes rollback and mid-run desync detection
            // possible.
            var replay = new Replay(11, AlternatingInputs(500));
            var longRun = Replay.Run(replay);
            var shortRun = Replay.Run(replay.Prefix(200));

            for (int i = 0; i < 200; i++)
            {
                Assert.AreEqual(longRun.Hashes[i], shortRun.Hashes[i],
                    $"a 500-tick run and a 200-tick run diverged at tick {i + 1}, " +
                    "inside their common prefix");
            }
        }

        [Test]
        public void CoreTickPipelineKeepsItsRelativeOrder()
        {
            // Pins the ORDER of the stages that must not move, not the length of
            // the pipeline. Reordering — Collision before Motion, Scoring before
            // Collision — silently changes every recorded replay. ADDING a stage
            // is a normal thing to do, and this must not stand in its way.
            //
            // The structural half of this guarantee (every stage runs exactly
            // once, and no stage writes state it did not declare) lives in
            // StageAccessTests.
            var core = new[]
            {
                SimStage.Begin, SimStage.Intent, SimStage.Motion,
                SimStage.Collision, SimStage.Scoring,
            };

            var order = new List<int>();
            foreach (var stage in core)
            {
                int index = System.Array.IndexOf(SimState.Stages, stage);
                Assert.AreNotEqual(-1, index,
                    $"SimStage.{stage} is no longer in SimState.Stages, so it never runs");
                order.Add(index);
            }

            for (int i = 1; i < order.Count; i++)
            {
                Assert.Less(order[i - 1], order[i],
                    $"SimStage.{core[i - 1]} must run before SimStage.{core[i]}. " +
                    "Reordering the tick silently changes every recorded replay.");
            }
        }

        [Test]
        public void FreshStateIsSpawnedAndAtTickZero()
        {
            // A new SimState is fully spawned and has run zero ticks, so the tick
            // invariant is exact. If this breaks, every replay length in the
            // suite silently shifts by one.
            var state = new SimState(0);
            Assert.AreEqual(0UL, state.Tick);

            // Asserted BY KIND, not by total count. A total count would turn
            // "the game gained an entity" into a red test for a reason nobody
            // cares about; what actually matters is that the bodies the rules
            // refer to exist, exactly once each, with unique identities.
            var markers = state.Entities.FindAll(e => e.Kind == EntityKind.Marker);
            Assert.AreEqual(1, markers.Count, "expected exactly one marker after construction");

            var ids = state.Entities.ConvertAll(e => e.SimId);
            CollectionAssert.AllItemsAreUnique(ids,
                "SimId is the stable identity every order-sensitive pass sorts on; " +
                "duplicates make the sort order — and therefore the state hash — arbitrary");

            state.Step(Intents.None);
            Assert.AreEqual(1UL, state.Tick, "one step, one tick");
        }

        [Test]
        public void StateHashIsSensitiveToEveryFloatBit()
        {
            // The hash feeds raw float bit patterns, not rounded values. A
            // one-ULP change must change the hash, or desync detection would
            // silently miss the drift that matters.
            var a = new SimState(5);
            var b = new SimState(5);
            Assert.AreEqual(a.StateHash(), b.StateHash());

            var marker = b.Marker;
            marker.Position = new Vec2(marker.Position.X + float.Epsilon * 8, marker.Position.Y);
            Assert.AreNotEqual(a.StateHash(), b.StateHash(),
                "a sub-ULP-scale position change did not change the state hash");
        }
    }
}
