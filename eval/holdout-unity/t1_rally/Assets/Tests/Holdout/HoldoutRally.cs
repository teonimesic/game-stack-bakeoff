// HELD-OUT. The agent never sees this file.
// Mirrors expected rally length from TickEvents and compares tick by tick.
using NUnit.Framework;
using Pong.Sim;

namespace Pong.Holdout
{
    public class HoldoutRally
    {
        // Drive the right paddle to the top so it misses and a point is conceded.
        // Do NOT rely on idle input: two centred paddles rally indefinitely, so an
        // idle replay exercises the increment path but never the reset path.
        static Intents Miss() => new Intents(
            new PlayerIntent(false, false), new PlayerIntent(true, false));

        [Test]
        public void RallyLengthTracksHitsAndResetsOnScore()
        {
            var state = new SimState(42);
            // Compare as long so int/uint/long all work. The prompt deliberately does not
            // specify a width; asserting 0u made NUnit report a type mismatch as the
            // baffling "Expected: 0, But was: 0" and failed a correct implementation.
            Assert.AreEqual(0L, (long)state.RallyLength, "rally length should start at zero");

            long expected = 0, maxSeen = 0;
            int resets = 0;

            for (int tick = 1; tick <= 3000; tick++)
            {
                state.Step(Miss());
                if (state.Events.Scored.HasValue) { expected = 0; resets++; }
                else { expected += state.Events.PaddleHits.Count; }
                if (expected > maxSeen) maxSeen = expected;

                Assert.AreEqual(expected, (long)state.RallyLength,
                    $"tick {tick}: hits={state.Events.PaddleHits.Count} scored={state.Events.Scored}");
            }

            Assert.Greater(maxSeen, 0L, "no paddle hit ever occurred; a constant zero would pass");
            Assert.Greater(resets, 0, "no score ever occurred; the reset path was never exercised");
        }

        [Test]
        public void RallyLengthIsPartOfTheSnapshot()
        {
            var a = new SimState(7);
            var b = new SimState(7);
            for (int tick = 1; tick <= 500; tick++)
            {
                a.Step(Miss());
                b.Step(Miss());
                Assert.AreEqual((long)a.RallyLength, (long)b.RallyLength,
                    $"tick {tick}: two runs of seed 7 disagreed on RallyLength");
            }
        }
    }
}
