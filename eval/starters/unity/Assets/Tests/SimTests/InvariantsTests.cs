// Invariants: the tests that catch "correct but not a game".
//
// The documented signature failure of agent-built games is that everything
// compiles, every unit test passes, and the result is unplayable — nothing
// happens in sixty seconds, or the pace is ten times what was intended.
// Correctness tests cannot see that class of defect, because nothing is
// *wrong*; the numbers are just bad.
//
// So these assert on CONSEQUENCES of the tuning constants, measured over a run,
// not on the constants themselves. Changing MARKER_SPEED or NUDGE_SPEED leaves
// every other test green and breaks this file immediately.
//
// Keep the bounds wide. They exist to catch "this is not a game any more", not
// to freeze the design.

using NUnit.Framework;
using Starter.Sim;

namespace Starter.Sim.Tests
{
    public class InvariantsTests
    {
        private const int LongRunTicks = 3000;

        /// The box the body is allowed to occupy: the arena, shrunk by the
        /// body's own half extent, plus a hair of slack for float rounding at
        /// the reflection point.
        private const float SlackUnits = 0.001f;

        [Test]
        public void TheWorldStaysInsideTheArena()
        {
            // Nothing may tunnel out of the box, ever. A body that escapes is
            // gone for good: every later assertion about it is meaningless.
            var state = new SimState(1);
            float limitX = Constants.ARENA_HALF_WIDTH - Constants.MARKER_HALF_SIZE;
            float limitY = Constants.ARENA_HALF_HEIGHT - Constants.MARKER_HALF_SIZE;

            for (int i = 0; i < LongRunTicks; i++)
            {
                state.Step(Intents.None);
                var p = state.Marker.Position;
                Assert.That(System.Math.Abs(p.X), Is.LessThanOrEqualTo(limitX + SlackUnits),
                    $"after {i + 1} ticks the marker is at x={p.X:F3}, outside the arena " +
                    $"(|x| must stay within {limitX:F3}). Collision is not containing it.");
                Assert.That(System.Math.Abs(p.Y), Is.LessThanOrEqualTo(limitY + SlackUnits),
                    $"after {i + 1} ticks the marker is at y={p.Y:F3}, outside the arena " +
                    $"(|y| must stay within {limitY:F3}). Collision is not containing it.");
            }
        }

        [Test]
        public void SomethingActuallyHappensWithoutInput()
        {
            // A world that is inert when nobody touches it is not a world. The
            // cheapest proof of life the starter has is a wall reflection, and
            // it must be reported through TickEvents, not merely happen.
            var state = new SimState(2);
            int bounces = 0;
            for (int i = 0; i < LongRunTicks; i++)
            {
                state.Step(Intents.None);
                bounces += state.Events.Names.Count;
            }

            Assert.Greater(bounces, 0,
                $"no event fired in {LongRunTicks} ticks (~{LongRunTicks / Constants.TICK_HZ}s) " +
                "with no input. Either nothing moves or TickEvents is never populated — " +
                "both make the run unobservable from outside the simulation.");
        }

        [Test]
        public void InputMovesTheWorld()
        {
            // A relational assertion, deliberately: it compares two runs of the
            // same seed rather than pinning a coordinate, so it survives every
            // retune of the constants and still fails the moment input stops
            // reaching the simulation.
            //
            // Seed 9 spends these 120 ticks clear of every wall, so the
            // comparison measures the input and nothing else.
            const ulong Seed = 9;
            const int Ticks = 120;

            float held = FinalY(Seed, Ticks, new Intents(true, false));
            float idle = FinalY(Seed, Ticks, Intents.None);

            Assert.Greater(held, idle,
                $"holding nudge_up for {Ticks} ticks left the marker at y={held:F3}, " +
                $"no higher than the y={idle:F3} it reaches with no input at all. " +
                "Intent is not reaching the simulation.");
        }

        [Test]
        public void SpeedIsInvariantUnderInput()
        {
            // Input steers; it must not accelerate. If this drifts, the world
            // slowly turns into a different game than the one that was tuned —
            // the exact defect a correctness test cannot see.
            const int Ticks = 600;
            const float ToleranceFraction = 0.01f;

            var state = new SimState(3);
            for (int i = 0; i < Ticks; i++)
            {
                // Input on half the ticks, alternating direction, so the clamp
                // is exercised from both sides.
                bool active = i % 2 == 0;
                state.Step(new Intents(active && (i / 2) % 2 == 0, active && (i / 2) % 2 == 1));

                float speed = state.Marker.Velocity.Length;
                float drift = System.Math.Abs(speed - Constants.MARKER_SPEED)
                              / Constants.MARKER_SPEED;
                Assert.That(drift, Is.LessThanOrEqualTo(ToleranceFraction),
                    $"after {i + 1} ticks the marker is moving at {speed:F3} u/s, " +
                    $"{drift * 100f:F2}% away from the {Constants.MARKER_SPEED:F0} u/s it is " +
                    "supposed to hold. Input is adding energy instead of steering.");
            }
        }

        private static float FinalY(ulong seed, int ticks, Intents held)
        {
            var state = new SimState(seed);
            for (int i = 0; i < ticks; i++) state.Step(held);
            return state.Marker.Position.Y;
        }
    }
}
