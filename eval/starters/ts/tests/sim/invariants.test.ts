/**
 * Invariants: the properties that must hold over a whole run, not at one tick.
 *
 * The documented signature failure of agent-built games is that everything
 * compiles, every unit test passes, and the result is unplayable. Correctness
 * tests cannot see that class of defect, because nothing is *wrong*; the
 * numbers are just bad. So these assert on CONSEQUENCES measured over a run —
 * where things end up, how often something happens, whether input has the
 * effect it claims — rather than on the constants that produce them.
 *
 * Keep the bounds wide. They exist to catch "this stopped behaving", not to
 * freeze the design.
 */

import { expect, test } from 'vitest';
import {
  ARENA_HALF_HEIGHT,
  ARENA_HALF_WIDTH,
  type Intents,
  MARKER_HALF_SIZE,
  MARKER_SPEED,
  NO_INTENTS,
  type Seed,
  length,
  step,
} from '../../src/sim/index.ts';
import { headlessWorld } from '../../src/sim/replay.ts';

const NUDGE_UP: Intents = { nudgeUp: true, nudgeDown: false };

/** The marker, which the starter guarantees exists. */
function marker(world: ReturnType<typeof headlessWorld>) {
  const found = world.entities.find((entity) => entity.kind === 'marker');
  if (found === undefined) {
    throw new Error('the world has no marker — spawnWorld no longer spawns one');
  }
  return found;
}

/** Run `ticks` ticks, feeding `inputFor(tick)` each time. */
function drive(
  seed: Seed,
  ticks: number,
  inputFor: (tick: number) => Intents = () => NO_INTENTS,
): {
  world: ReturnType<typeof headlessWorld>;
  bounces: number;
  minSpeed: number;
  maxSpeed: number;
} {
  const world = headlessWorld(seed);
  let bounces = 0;
  let minSpeed = Number.POSITIVE_INFINITY;
  let maxSpeed = 0;

  for (let tick = 0; tick < ticks; tick += 1) {
    step(world, inputFor(tick));
    bounces += world.events.events.filter((event) => event === 'bounce').length;
    const speed = length(marker(world).velocity);
    minSpeed = Math.min(minSpeed, speed);
    maxSpeed = Math.max(maxSpeed, speed);
  }
  return { world, bounces, minSpeed, maxSpeed };
}

test('the marker never leaves the arena', () => {
  // A body that escapes the play area is the single most common physics bug and
  // it is invisible to a hash test: the run is perfectly deterministic, it is
  // just wrong. Checked every tick, not only at the end.
  const limitX = ARENA_HALF_WIDTH - MARKER_HALF_SIZE;
  const limitY = ARENA_HALF_HEIGHT - MARKER_HALF_SIZE;

  for (const seed of [1, 2, 3]) {
    const world = headlessWorld(seed);
    for (let tick = 0; tick < 3000; tick += 1) {
      step(world);
      const { position } = marker(world);
      expect(
        Math.abs(position.x),
        `seed ${seed}, tick ${tick + 1}: the marker is at x=${position.x}, outside the arena. ` +
          'Collision is not clamping, or it reflects without correcting the overshoot.',
      ).toBeLessThanOrEqual(limitX);
      expect(
        Math.abs(position.y),
        `seed ${seed}, tick ${tick + 1}: the marker is at y=${position.y}, outside the arena.`,
      ).toBeLessThanOrEqual(limitY);
    }
  }
});

test('the marker bounces off the arena', () => {
  // The mirror image of the test above: a marker that never reaches an edge is
  // also wrong, and would make "never leaves the arena" pass vacuously.
  const { bounces } = drive(4, 3000);
  expect(
    bounces,
    'no bounce event in 3000 idle ticks. Either nothing is moving or the collision stage ' +
      'reflects without emitting an event, which the view and the probe both read.',
  ).toBeGreaterThan(0);
});

test('holding nudge up moves the marker up', () => {
  // A relational assertion: it survives retuning NUDGE_SPEED, and it is the
  // only thing that proves input actually reaches the simulation.
  const idle = drive(5, 120);
  const raised = drive(5, 120, () => NUDGE_UP);

  const idleY = marker(idle.world).position.y;
  const raisedY = marker(raised.world).position.y;
  expect(
    raisedY,
    `after 120 ticks the marker is at y=${raisedY} holding nudge up and y=${idleY} idle. ` +
      'Holding up must end strictly higher; check that Intents reaches the intent stage.',
  ).toBeGreaterThan(idleY);
});

test('the marker holds its speed while being steered', () => {
  // Input steers; it does not accelerate. If this drifts, the marker slowly
  // stops or slowly runs away, and every other test still passes.
  const { minSpeed, maxSpeed } = drive(6, 600, (tick) => (tick % 2 === 0 ? NUDGE_UP : NO_INTENTS));
  const tolerance = MARKER_SPEED * 0.01;

  expect(
    minSpeed,
    `speed fell to ${minSpeed.toFixed(3)}, more than 1% below MARKER_SPEED (${MARKER_SPEED}). ` +
      'The intent stage is bleeding energy out of the velocity.',
  ).toBeGreaterThanOrEqual(MARKER_SPEED - tolerance);
  expect(
    maxSpeed,
    `speed rose to ${maxSpeed.toFixed(3)}, more than 1% above MARKER_SPEED (${MARKER_SPEED}). ` +
      'The clamp in the intent stage is not being applied.',
  ).toBeLessThanOrEqual(MARKER_SPEED + tolerance);
});
