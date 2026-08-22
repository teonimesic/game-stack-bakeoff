// Deterministic replay: the template's most load-bearing test primitive.
//
// A replay is (seed, per-tick intents). Running it produces a per-tick hash
// chain. Two runs of the same replay must produce identical chains; if they do
// not, something in the simulation is order-dependent, clock-dependent, or
// reading unseeded entropy.
//
// This single mechanism catches most determinism regressions, which is why
// every gameplay change should come with a replay test.

using System;
using System.Collections.Generic;

namespace Pong.Sim
{
    /// A recorded run: everything needed to reproduce a simulation exactly.
    public sealed class Replay
    {
        public readonly ulong Seed;

        /// Intent for each tick, in order. Length determines the run length.
        public readonly Intents[] Inputs;

        public Replay(ulong seed, Intents[] inputs)
        {
            Seed = seed;
            Inputs = inputs ?? Array.Empty<Intents>();
        }

        /// A replay with no player input — useful for testing the ball alone.
        public static Replay Idle(ulong seed, int ticks) => new Replay(seed, new Intents[ticks]);

        /// A replay that holds the same intent for every tick.
        public static Replay Held(ulong seed, Intents intent, int ticks)
        {
            var inputs = new Intents[ticks];
            for (int i = 0; i < ticks; i++) inputs[i] = intent;
            return new Replay(seed, inputs);
        }

        public int Length => Inputs.Length;
        public bool IsEmpty => Inputs.Length == 0;

        public Replay Prefix(int ticks)
        {
            var slice = new Intents[ticks];
            Array.Copy(Inputs, slice, ticks);
            return new Replay(Seed, slice);
        }

        /// Run a replay to completion, hashing the world after every tick.
        public static ReplayOutcome Run(Replay replay)
        {
            var state = new SimState(replay.Seed);
            var hashes = new ulong[replay.Length];
            for (int i = 0; i < replay.Length; i++)
            {
                state.Step(replay.Inputs[i]);
                hashes[i] = state.StateHash();
            }
            return new ReplayOutcome(hashes, state.Tick, state.Score);
        }

        /// Run the same replay twice and return the first tick at which the two
        /// runs diverge, or -1 if they are identical.
        ///
        /// This is deliberately exact: any divergence at all is a bug, not a
        /// tolerance to be widened.
        public static int FindDivergence(Replay replay)
        {
            var a = Run(replay);
            var b = Run(replay);
            for (int i = 0; i < a.Hashes.Count && i < b.Hashes.Count; i++)
            {
                if (a.Hashes[i] != b.Hashes[i]) return i;
            }
            return -1;
        }
    }

    /// Outcome of running a replay.
    public sealed class ReplayOutcome
    {
        /// World hash after each tick. `Hashes[i]` is the state after tick i+1.
        public readonly IReadOnlyList<ulong> Hashes;
        public readonly ulong FinalTick;
        public readonly Score FinalScore;

        public ReplayOutcome(ulong[] hashes, ulong finalTick, Score finalScore)
        {
            Hashes = hashes;
            FinalTick = finalTick;
            FinalScore = finalScore;
        }

        /// Hash of the whole run — cheap to compare and to store as a golden.
        public ulong Digest()
        {
            const ulong PRIME = 0x00000100000001b3UL;
            ulong acc = 0xcbf29ce484222325UL;
            foreach (var h in Hashes) acc = unchecked((acc ^ h) * PRIME);
            return acc;
        }
    }
}
