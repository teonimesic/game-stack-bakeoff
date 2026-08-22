/**
 * Playability assertions: the tests that catch "correct but not a game".
 *
 * The documented signature failure of agent-built games is that everything
 * compiles, every unit test passes, and the result is unplayable — zero damage
 * in sixty seconds, or level-ups every 3.9s instead of the intended 10-30s.
 * Correctness tests cannot see that class of defect, because nothing is
 * *wrong*; the numbers are just bad.
 *
 * So these assert on CONSEQUENCES of the tuning constants, not on the constants
 * themselves. Changing `BALL_SPEEDUP` from 1.05 to 1.5 leaves every other test
 * green and breaks this file immediately.
 *
 * Keep the bounds wide. They exist to catch "this is not a game any more", not
 * to freeze the design.
 */

import { expect, test } from 'vitest';
import {
  ARENA_HALF_WIDTH,
  type Intents,
  MAX_BALL_SPEED,
  type Seed,
  type Side,
  TICK_DT,
  TICK_HZ,
  length,
  step,
} from '../../src/sim/index.ts';
import { headlessWorld, replay, run } from '../../src/sim/replay.ts';

/**
 * Drive both paddles to track the ball perfectly. A skilled-player upper bound:
 * if a rally cannot be sustained under perfect play, it cannot be sustained.
 */
function perfectTrackingRun(
  seed: Seed,
  ticks: number,
): { hits: number; peakSpeed: number; scores: number } {
  const world = headlessWorld(seed);
  let hits = 0;
  let peakSpeed = 0;
  let scores = 0;

  for (let tick = 0; tick < ticks; tick += 1) {
    const ball = world.entities.find((entity) => entity.kind === 'ball');
    const ballY = ball?.position.y ?? 0;
    peakSpeed = Math.max(peakSpeed, ball === undefined ? 0 : length(ball.velocity));

    const intentFor = (side: Side): { up: boolean; down: boolean } => {
      const paddleY = world.entities.find((entity) => entity.side === side)?.position.y ?? 0;
      return { up: ballY > paddleY + 2, down: ballY < paddleY - 2 };
    };
    const intents: Intents = { left: intentFor('left'), right: intentFor('right') };

    step(world, intents);
    hits += world.events.paddleHits.length;
    if (world.events.scored !== null) {
      scores += 1;
    }
  }
  return { hits, peakSpeed, scores };
}

test('a skilled rally can actually be sustained', () => {
  // 30 seconds of perfect play should produce a real rally. If paddles cannot
  // reach the ball, or the ball outruns them immediately, the game is
  // unplayable no matter how correct the physics are.
  const { hits } = perfectTrackingRun(1, 30 * TICK_HZ);
  expect(
    hits,
    `only ${hits} paddle hits in 30s of perfect tracking. Either the paddle is too slow ` +
      'to reach the ball or the ball is too fast to return.',
  ).toBeGreaterThanOrEqual(10);
});

test('ball speed stays within playable bounds', () => {
  const { peakSpeed } = perfectTrackingRun(2, 60 * TICK_HZ);
  expect(
    peakSpeed,
    `ball reached ${peakSpeed.toFixed(0)} u/s, above the ${MAX_BALL_SPEED} cap — ` +
      'the clamp is not being applied',
  ).toBeLessThanOrEqual(MAX_BALL_SPEED + 1);

  // NOTE: there is deliberately no "the ball escalates" assertion here.
  // Mutation testing showed peak speed cannot distinguish BALL_SPEEDUP=1.05
  // from 1.00 over 60s — the per-hit deflection term adds more speed than the
  // multiplier does at these constants, so any such assertion passes either way
  // and would give false confidence. If escalation becomes a design
  // requirement, measure it directly (speed sampled at hit N vs hit 1 in a
  // scripted rally), not via observed peak.

  // A ball that crosses the arena in under ~2 fixed ticks is untrackable.
  const ticksToCross = (ARENA_HALF_WIDTH * 2) / (peakSpeed * TICK_DT);
  expect(
    ticksToCross,
    `at peak speed the ball crosses the arena in ${ticksToCross.toFixed(1)} ticks, ` +
      'which is faster than a player can react',
  ).toBeGreaterThan(8);
});

test('a missing player concedes at a reasonable pace', () => {
  // NOTE: this deliberately does NOT use idle input. Two stationary paddles
  // parked at the centre rally forever, which is correct Pong behaviour, not a
  // defect — measured 25-31 hits and 0 scores over 3000 ticks at every seed.
  // Asserting that idle play scores would be asserting a falsehood.
  //
  // What IS a requirement: when a player stops defending, they concede at a
  // sane rate. Not instantly (the ball is trivially fast) and not never (the
  // ball cannot leave the arena).
  const miss: Intents = { left: { up: false, down: false }, right: { up: true, down: false } };
  const outcome = run(replay(3, new Array<Intents>(60 * TICK_HZ).fill(miss)));
  const total = outcome.finalScore.left + outcome.finalScore.right;
  expect(
    total,
    `${total} points in 60s while the right player holds up and never defends; expected ` +
      'roughly 2-120. Too few means the ball cannot leave the arena; too many means a ' +
      'round resets almost instantly.',
  ).toBeGreaterThanOrEqual(2);
  expect(total).toBeLessThanOrEqual(120);
});

test('the ball never gets stuck', () => {
  // A ball trapped in a corner, or oscillating inside a paddle, passes every
  // correctness test while making the game unplayable.
  const world = headlessWorld(4);
  let stalled = 0;
  let worst = 0;
  let last: { x: number; y: number } | null = null;

  for (let tick = 0; tick < 60 * TICK_HZ; tick += 1) {
    step(world);
    const position = world.entities.find((entity) => entity.kind === 'ball')?.position ?? null;
    if (last !== null && position !== null && position.x === last.x && position.y === last.y) {
      stalled += 1;
      worst = Math.max(worst, stalled);
    } else {
      stalled = 0;
    }
    last = position;
  }
  expect(
    worst,
    `the ball held exactly the same position for ${worst} consecutive ticks ` +
      `(~${(worst / TICK_HZ).toFixed(1)}s). It is stuck.`,
  ).toBeLessThan(TICK_HZ);
});

test('a point is always reachable', () => {
  // Guards against a change that makes scoring impossible — e.g. widening the
  // paddles until they seal the goal. Again: driven by a player who is actively
  // out of position, not by idle input.
  const miss: Intents = { left: { up: false, down: false }, right: { up: true, down: false } };
  for (const seed of [10, 11, 12]) {
    const outcome = run(replay(seed, new Array<Intents>(30 * TICK_HZ).fill(miss)));
    expect(
      outcome.finalScore.left + outcome.finalScore.right,
      `seed ${seed}: nobody scored in 30s even though the right player never defended — ` +
        'scoring may be unreachable',
    ).toBeGreaterThan(0);
  }
});
