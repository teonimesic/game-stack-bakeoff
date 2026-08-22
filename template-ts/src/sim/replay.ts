/**
 * Deterministic replay: the template's most load-bearing test primitive.
 *
 * A replay is `(seed, per-tick intents)`. Running it produces a per-tick hash
 * chain. Two runs of the same replay must produce identical chains; if they do
 * not, something in the simulation is order-dependent, clock-dependent, or
 * reading unseeded entropy.
 *
 * This single mechanism catches most determinism regressions, which is why
 * every gameplay change should come with a replay test.
 */

import {
  type Intents,
  NO_INTENTS,
  type Score,
  type Seed,
  type World,
  spawnWorld,
  stateHash,
  step,
} from './index.ts';

/** A recorded run: everything needed to reproduce a simulation exactly. */
export interface Replay {
  readonly seed: Seed;
  /** Intent for each tick, in order. Length determines the run length. */
  readonly inputs: readonly Intents[];
}

export function replay(seed: Seed, inputs: readonly Intents[]): Replay {
  return { seed, inputs };
}

/** A replay with no player input — useful for testing the ball alone. */
export function idleReplay(seed: Seed, ticks: number): Replay {
  return { seed, inputs: new Array<Intents>(ticks).fill(NO_INTENTS) };
}

/** Outcome of running a replay. */
export interface ReplayOutcome {
  /** World hash after each tick. `hashes[i]` is the state after tick `i + 1`. */
  readonly hashes: readonly bigint[];
  readonly finalTick: number;
  readonly finalScore: Score;
}

/** Hash of the whole run — cheap to compare and to store as a golden value. */
export function digest(outcome: ReplayOutcome): bigint {
  const PRIME = 0x00000100000001b3n;
  const MASK = (1n << 64n) - 1n;
  let acc = 0xcbf29ce484222325n;
  for (const hash of outcome.hashes) {
    acc = ((acc ^ hash) * PRIME) & MASK;
  }
  return acc;
}

/**
 * Build a headless world.
 *
 * There is nothing to warm up and no event loop to drive: the invariant is
 * exact by construction — **after `headlessWorld`, one `step()` is one tick.**
 * Tests advance time by calling `step`, never by elapsed seconds.
 */
export function headlessWorld(seed: Seed): World {
  return spawnWorld(seed);
}

/** Run a replay to completion, hashing the world after every tick. */
export function run(replay: Replay): ReplayOutcome {
  const world = headlessWorld(replay.seed);
  const hashes: bigint[] = [];

  for (const intents of replay.inputs) {
    step(world, intents);
    hashes.push(stateHash(world));
  }

  return {
    hashes,
    finalTick: world.tick,
    finalScore: { ...world.score },
  };
}

/**
 * Run the same replay twice and return the first tick at which the two runs
 * diverge, or `null` if they are identical.
 *
 * This is the assertion behind `just test-determinism`. It is deliberately
 * exact: any divergence at all is a bug, not a tolerance to be widened.
 */
export function findDivergence(replay: Replay): number | null {
  const a = run(replay);
  const b = run(replay);
  const shared = Math.min(a.hashes.length, b.hashes.length);
  for (let tick = 0; tick < shared; tick += 1) {
    if (a.hashes[tick] !== b.hashes[tick]) {
      return tick;
    }
  }
  return a.hashes.length === b.hashes.length ? null : shared;
}
