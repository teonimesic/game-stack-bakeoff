// Playability assertions: the tests that catch "correct but not a game".
//
// The documented signature failure of agent-built games is that everything
// compiles, every unit test passes, and the result is unplayable — zero damage
// in sixty seconds, or level-ups every 3.9s instead of the intended 10-30s.
// Correctness tests cannot see that class of defect, because nothing is
// *wrong*; the numbers are just bad.
//
// So these assert on CONSEQUENCES of the tuning constants, not on the constants
// themselves. Changing BALL_SPEEDUP from 1.05 to 1.5 leaves every other test
// green and breaks this file immediately.
//
// Keep the bounds wide. They exist to catch "this is not a game any more", not
// to freeze the design.

using NUnit.Framework;
using Pong.Sim;

namespace Pong.Sim.Tests
{
    public class PlayabilityTests
    {
        /// Drive both paddles to track the ball perfectly. A skilled-player
        /// upper bound: if a rally cannot be sustained under perfect play, it
        /// cannot be sustained.
        private static (int hits, float peakSpeed, int scores) PerfectTrackingRun(
            ulong seed, int ticks)
        {
            var state = new SimState(seed);
            int hits = 0, scores = 0;
            float peakSpeed = 0f;

            for (int i = 0; i < ticks; i++)
            {
                var ball = state.Ball;
                float ballY = ball.Position.Y;
                peakSpeed = System.Math.Max(peakSpeed, ball.Velocity.Length);

                PlayerIntent IntentFor(Side side)
                {
                    float y = state.Paddle(side).Position.Y;
                    return new PlayerIntent(ballY > y + 2f, ballY < y - 2f);
                }

                state.Step(new Intents(IntentFor(Side.Left), IntentFor(Side.Right)));
                hits += state.Events.PaddleHits.Count;
                if (state.Events.Scored.HasValue) scores++;
            }
            return (hits, peakSpeed, scores);
        }

        [Test]
        public void ASkilledRallyCanActuallyBeSustained()
        {
            // 30 seconds of perfect play should produce a real rally. If paddles
            // cannot reach the ball, or the ball outruns them immediately, the
            // game is unplayable no matter how correct the physics are.
            var (hits, _, _) = PerfectTrackingRun(1, 30 * Constants.TICK_HZ);
            Assert.GreaterOrEqual(hits, 10,
                $"only {hits} paddle hits in 30s of perfect tracking. Either the paddle " +
                "is too slow to reach the ball or the ball is too fast to return.");
        }

        [Test]
        public void BallSpeedStaysWithinPlayableBounds()
        {
            var (_, peak, _) = PerfectTrackingRun(2, 60 * Constants.TICK_HZ);
            Assert.LessOrEqual(peak, Constants.MAX_BALL_SPEED + 1f,
                $"ball reached {peak:F0} u/s, above the {Constants.MAX_BALL_SPEED:F0} cap - " +
                "the clamp is not being applied");

            // NOTE: there is deliberately no "the ball escalates" assertion here.
            // Mutation testing on the reference implementation showed peak speed
            // cannot distinguish BALL_SPEEDUP=1.05 from 1.00 over 60s - the
            // per-hit deflection term adds more speed than the multiplier does at
            // these constants, so any such assertion passes either way and would
            // give false confidence. If escalation becomes a design requirement,
            // measure it directly (speed sampled at hit N vs hit 1 in a scripted
            // rally), not via observed peak.

            // A ball that crosses the arena in under ~2 fixed ticks is
            // untrackable.
            float ticksToCross = (Constants.ARENA_HALF_WIDTH * 2f) / (peak * Constants.TICK_DT);
            Assert.Greater(ticksToCross, 8f,
                $"at peak speed the ball crosses the arena in {ticksToCross:F1} ticks, " +
                "which is faster than a player can react");
        }

        [Test]
        public void AMissingPlayerConcedesAtAReasonablePace()
        {
            // NOTE: this deliberately does NOT use idle input. Two stationary
            // paddles parked at the centre rally forever, which is correct Pong
            // behaviour, not a defect - measured 25-31 hits and 0 scores over
            // 3000 ticks at every seed. Asserting that idle play scores would be
            // asserting a falsehood.
            //
            // What IS a requirement: when a player stops defending, they concede
            // at a sane rate. Not instantly (the ball is trivially fast) and not
            // never (the ball cannot leave the arena).
            var miss = new Intents(default, new PlayerIntent(true, false));
            var outcome = Replay.Run(Replay.Held(3, miss, 60 * Constants.TICK_HZ));
            uint total = outcome.FinalScore.Left + outcome.FinalScore.Right;
            Assert.That(total, Is.InRange(2u, 120u),
                $"{total} points in 60s while the right player holds up and never " +
                "defends; expected roughly 2-120. Too few means the ball cannot leave " +
                "the arena; too many means a round resets almost instantly.");
        }

        [Test]
        public void TheBallNeverGetsStuck()
        {
            // A ball trapped in a corner, or oscillating inside a paddle, passes
            // every correctness test while making the game unplayable.
            var state = new SimState(4);
            int stalled = 0, worst = 0;
            Vec2 last = state.Ball.Position;

            for (int i = 0; i < 60 * Constants.TICK_HZ; i++)
            {
                state.Step(Intents.None);
                var pos = state.Ball.Position;
                if (pos.Equals(last)) { stalled++; worst = System.Math.Max(worst, stalled); }
                else stalled = 0;
                last = pos;
            }
            Assert.Less(worst, Constants.TICK_HZ,
                $"the ball held exactly the same position for {worst} consecutive ticks " +
                $"(~{worst / (float)Constants.TICK_HZ:F1}s). It is stuck.");
        }

        [Test]
        public void APointIsAlwaysReachable()
        {
            // Guards against a change that makes scoring impossible - e.g.
            // widening the paddles until they seal the goal. Again: driven by a
            // player who is actively out of position, not by idle input.
            var miss = new Intents(default, new PlayerIntent(true, false));
            foreach (ulong seed in new ulong[] { 10, 11, 12 })
            {
                var outcome = Replay.Run(Replay.Held(seed, miss, 30 * Constants.TICK_HZ));
                Assert.Greater(outcome.FinalScore.Left + outcome.FinalScore.Right, 0u,
                    $"seed {seed}: nobody scored in 30s even though the right player " +
                    "never defended - scoring may be unreachable");
            }
        }

        [Test]
        public void TickEventsReportWhatHappened()
        {
            // TickEvents is the presentation and test-facing record of a tick.
            // Held-out tests read it, so it must actually be populated.
            var (hits, _, _) = PerfectTrackingRun(6, 30 * Constants.TICK_HZ);
            Assert.Greater(hits, 0, "TickEvents.PaddleHits was never populated during a rally");

            var state = new SimState(7);
            uint bounces = 0;
            for (int i = 0; i < 60 * Constants.TICK_HZ; i++)
            {
                state.Step(Intents.None);
                bounces += state.Events.WallBounces;
            }
            Assert.Greater(bounces, 0u, "the ball never bounced off a wall in 60s");
        }
    }
}
