// HELD-OUT. The agent never sees this file.
// A determinism trap: the obvious implementation reaches for UnityEngine.Random
// or DateTime.Now, both of which pass review and fail here.
using System.Collections.Generic;
using System.Linq;
using NUnit.Framework;
using Pong.Sim;

namespace Pong.Holdout
{
    public class HoldoutPowerup
    {
        static List<string> Positions(ulong seed, int ticks)
        {
            var state = new SimState(seed);
            var outp = new List<string>(ticks);
            for (int i = 0; i < ticks; i++)
            {
                state.Step(default);
                var p = state.Entities
                    .Where(e => e.Kind.ToString() == "Powerup")
                    .Select(e => $"{e.Position.X},{e.Position.Y}")
                    .OrderBy(s => s).FirstOrDefault();
                outp.Add(p);
            }
            return outp;
        }

        [Test]
        public void PowerupExistsAndMoves()
        {
            var seen = Positions(3, 900);
            Assert.Greater(seen.Count(p => p != null), 0,
                "no entity with EntityKind.Powerup ever existed in 900 ticks");
            Assert.Greater(seen.Where(p => p != null).Distinct().Count(), 1,
                "the powerup never changed position in 900 ticks");
        }

        [Test]
        public void PlacementIsDeterministicForASeed()
        {
            var a = Positions(11, 900);
            var b = Positions(11, 900);
            for (int i = 0; i < a.Count; i++)
                Assert.AreEqual(a[i], b[i],
                    $"two runs with seed 11 disagreed at tick {i}: placement reads entropy from outside the sim");
        }

        [Test]
        public void PlacementDependsOnTheSeed()
        {
            CollectionAssert.AreNotEqual(Positions(1, 900), Positions(2, 900),
                "seeds 1 and 2 produced identical placements");
        }

        [Test]
        public void PowerupStaysInsideTheArena()
        {
            foreach (var seed in new ulong[] { 5, 6, 7 })
                foreach (var p in Positions(seed, 600).Where(p => p != null))
                {
                    var parts = p.Split(',');
                    float x = float.Parse(parts[0]), y = float.Parse(parts[1]);
                    Assert.LessOrEqual(System.Math.Abs(x), Constants.ARENA_HALF_WIDTH, $"seed {seed}: outside at {p}");
                    Assert.LessOrEqual(System.Math.Abs(y), Constants.ARENA_HALF_HEIGHT, $"seed {seed}: outside at {p}");
                }
        }
    }
}
