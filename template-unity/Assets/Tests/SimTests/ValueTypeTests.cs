// The simulation's value types. Small, boring, and load-bearing: Vec2 is the
// arithmetic every rule is written in, and the equality/hash members are what
// `StateHash`, snapshots and test assertions lean on.
//
// These are cheap to write and cheap to run, and they are the reason a bug in
// `ClampLengthMax` shows up here rather than as a mysterious rally-length
// failure three tests away.

using NUnit.Framework;
using Pong.Sim;

namespace Pong.Sim.Tests
{
    public class ValueTypeTests
    {
        [Test]
        public void Vec2ArithmeticIsComponentwise()
        {
            var a = new Vec2(3f, -4f);
            var b = new Vec2(1f, 2f);

            Assert.AreEqual(new Vec2(4f, -2f), a + b);
            Assert.AreEqual(new Vec2(2f, -6f), a - b);
            Assert.AreEqual(new Vec2(6f, -8f), a * 2f);
            Assert.AreEqual(new Vec2(1.5f, -2f), a / 2f);
            Assert.AreEqual(25f, a.LengthSquared);
            Assert.AreEqual(5f, a.Length);
            Assert.AreEqual(new Vec2(9f, -4f), a.WithX(9f));
            Assert.AreEqual(new Vec2(3f, 9f), a.WithY(9f));
            Assert.AreEqual(Vec2.Zero, new Vec2(0f, 0f));
        }

        [Test]
        public void ClampLengthMaxOnlyShortens()
        {
            var longVec = new Vec2(3f, 4f);            // length 5
            Assert.AreEqual(new Vec2(1.5f, 2f), longVec.ClampLengthMax(2.5f));

            // Already inside the limit: returned untouched, not renormalised.
            // Renormalising here would quietly speed the ball UP.
            Assert.AreEqual(longVec, longVec.ClampLengthMax(10f));
            Assert.AreEqual(longVec, longVec.ClampLengthMax(5f));
        }

        [Test]
        public void ValueTypesCompareByValue()
        {
            Assert.IsTrue(new Vec2(1f, 2f) == new Vec2(1f, 2f));
            Assert.IsTrue(new Vec2(1f, 2f) != new Vec2(1f, 2.5f));
            Assert.AreEqual(new Vec2(1f, 2f).GetHashCode(), new Vec2(1f, 2f).GetHashCode());
            Assert.AreEqual("(1, 2)", new Vec2(1f, 2f).ToString());
            Assert.IsFalse(new Vec2(1f, 2f).Equals("not a vector"));

            Assert.IsTrue(new PlayerIntent(true, false) == new PlayerIntent(true, false));
            Assert.IsTrue(new PlayerIntent(true, false) != new PlayerIntent(false, true));
            Assert.AreEqual(new PlayerIntent(true, false).GetHashCode(),
                new PlayerIntent(true, false).GetHashCode());
            Assert.IsFalse(new PlayerIntent(true, false).Equals(7));

            var up = new Intents(new PlayerIntent(true, false), new PlayerIntent(false, true));
            Assert.IsTrue(up == new Intents(new PlayerIntent(true, false), new PlayerIntent(false, true)));
            Assert.IsTrue(up != Intents.None);
            Assert.AreEqual(up.GetHashCode(),
                new Intents(new PlayerIntent(true, false), new PlayerIntent(false, true)).GetHashCode());
            Assert.IsFalse(up.Equals(null));

            var score = new Score { Left = 2, Right = 3 };
            Assert.IsTrue(score == new Score { Left = 2, Right = 3 });
            Assert.IsTrue(score != new Score { Left = 3, Right = 2 });
            Assert.AreEqual(score.GetHashCode(), new Score { Left = 2, Right = 3 }.GetHashCode());
            Assert.AreEqual("2-3", score.ToString());
            Assert.IsFalse(score.Equals("2-3"));
        }

        [Test]
        public void IntentsNoneIsBothPlayersIdle()
        {
            Assert.AreEqual(0f, Intents.None.Left.Axis());
            Assert.AreEqual(0f, Intents.None.Right.Axis());
        }

        [Test]
        public void OpposingIntentsCancel()
        {
            Assert.AreEqual(1f, new PlayerIntent(true, false).Axis());
            Assert.AreEqual(-1f, new PlayerIntent(false, true).Axis());
            Assert.AreEqual(0f, new PlayerIntent(true, true).Axis(),
                "up and down held together must cancel, not pick a winner");
            Assert.AreEqual(0f, new PlayerIntent(false, false).Axis());
        }

        [Test]
        public void SimRngIsSeededAndSnapshottable()
        {
            var a = SimRng.FromSeed(42);
            var b = SimRng.FromSeed(42);
            Assert.IsTrue(a == b, "two RNGs from the same seed must start equal");

            for (int i = 0; i < 100; i++) Assert.AreEqual(a.NextU32(), b.NextU32());
            Assert.IsTrue(a == b);
            Assert.AreEqual(a.GetHashCode(), b.GetHashCode());

            var other = SimRng.FromSeed(43);
            Assert.IsTrue(a != other, "different seeds must not land on the same state");
            Assert.IsFalse(a.Equals("not an rng"));
        }

        [Test]
        public void SimRngStaysInsideItsAdvertisedRanges()
        {
            var rng = SimRng.FromSeed(9);
            int heads = 0;
            for (int i = 0; i < 2000; i++)
            {
                float unit = rng.NextFloat();
                Assert.That(unit, Is.InRange(0f, 0.99999994f), "NextFloat must be in [0, 1)");

                float ranged = rng.RangeFloat(-3f, 7f);
                Assert.That(ranged, Is.InRange(-3f, 7f));

                if (rng.CoinFlip()) heads++;
            }
            // Not a statistics test — just a guard against a coin that always
            // lands the same way, which would silently kill serve variety.
            Assert.That(heads, Is.InRange(800, 1200),
                $"{heads}/2000 heads: the coin flip is biased or constant");
        }

        [Test]
        public void TickEventsSnapshotIsACopy()
        {
            var events = new TickEvents { WallBounces = 2, Scored = Side.Left };
            events.PaddleHits.Add(Side.Right);

            var copy = events.Snapshot();
            events.Clear();

            Assert.AreEqual(2u, copy.WallBounces, "the snapshot aliased the live events object");
            Assert.AreEqual(Side.Left, copy.Scored);
            CollectionAssert.AreEqual(new[] { Side.Right }, copy.PaddleHits);

            Assert.AreEqual(0u, events.WallBounces);
            Assert.IsNull(events.Scored);
            CollectionAssert.IsEmpty(events.PaddleHits);
        }

        [Test]
        public void ReplayHelpersProduceTheRequestedLength()
        {
            Assert.AreEqual(0, new Replay(1, null).Length);
            Assert.IsTrue(new Replay(1, null).IsEmpty);

            var held = Replay.Held(1, new Intents(new PlayerIntent(true, false), default), 10);
            Assert.AreEqual(10, held.Length);
            Assert.IsFalse(held.IsEmpty);
            Assert.IsTrue(held.Inputs[9].Left.Up);

            var prefix = held.Prefix(4);
            Assert.AreEqual(4, prefix.Length);
            Assert.AreEqual(held.Seed, prefix.Seed);
        }
    }
}
