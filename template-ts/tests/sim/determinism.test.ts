/**
 * Determinism guarantees. These tests are the template's safety net: they fail
 * loudly when a change makes the simulation depend on iteration order, wall
 * clock, or unseeded entropy.
 *
 * If one of these fails, DO NOT relax the assertion. An exact hash comparison
 * that becomes an approximate one is worthless. Find the nondeterminism.
 */

import { describe, expect, test } from 'vitest';
import {
  FixedClock,
  type Intents,
  SIM_PIPELINE,
  SIM_STAGES,
  TICK_DT,
  spawnWorld,
  step,
} from '../../src/sim/index.ts';
import {
  digest,
  findDivergence,
  headlessWorld,
  idleReplay,
  replay,
  run,
} from '../../src/sim/replay.ts';

function alternatingInputs(ticks: number): Intents[] {
  // A pattern that actually moves both paddles and produces rallies, so the
  // hash chain exercises collisions rather than an untouched ball.
  return Array.from({ length: ticks }, (_unused, tick) => ({
    left: { up: Math.floor(tick / 17) % 2 === 0, down: Math.floor(tick / 17) % 2 === 1 },
    right: { up: Math.floor(tick / 23) % 2 === 1, down: Math.floor(tick / 23) % 2 === 0 },
  }));
}

test('identical replays produce identical hash chains', () => {
  const recorded = replay(0xdeadbeef, alternatingInputs(600));
  expect(
    findDivergence(recorded),
    'the same replay produced different state on two runs — the simulation is ' +
      'reading something outside its snapshot (iteration order, wall clock, or unseeded RNG)',
  ).toBeNull();
});

test('different seeds produce different runs', () => {
  // Guards against the opposite failure: a "deterministic" simulation that is
  // actually ignoring its seed would pass every determinism test trivially.
  const a = run(idleReplay(1, 400));
  const b = run(idleReplay(2, 400));
  expect(
    digest(a),
    'two different seeds produced identical runs — the seed is not reaching the simulation',
  ).not.toBe(digest(b));
});

test('different inputs produce different runs', () => {
  const seed = 7;
  const idle = run(idleReplay(seed, 400));
  const active = run(replay(seed, alternatingInputs(400)));
  expect(digest(idle), 'player intent had no effect on the simulation').not.toBe(digest(active));
});

test('tick count is exactly the number of updates', () => {
  // Time in the simulation is a count of `step` calls and nothing else. If this
  // regresses, every other determinism test silently becomes time-dependent.
  for (const ticks of [1, 10, 137]) {
    const outcome = run(idleReplay(3, ticks));
    expect(outcome.finalTick, `expected exactly ${ticks} ticks from ${ticks} updates`).toBe(ticks);
    expect(outcome.hashes.length).toBe(ticks);
  }
});

test('replay is resumable from a prefix', () => {
  // A replay's first N hashes must not depend on what comes after them. This is
  // what makes rollback and mid-run desync detection possible.
  const inputs = alternatingInputs(500);
  const long = run(replay(11, inputs));
  const short = run(replay(11, inputs.slice(0, 200)));

  expect(
    long.hashes.slice(0, 200),
    'a 500-tick run and a 200-tick run diverged within their common prefix',
  ).toEqual(short.hashes);
});

test('the tick pipeline is a declared total order', () => {
  // The analogue of a schedule-ambiguity check: every system names the stage it
  // belongs to, and the systems run in stage order. Two systems that touch the
  // same state with no declared order between them are exactly the race this
  // catches — inserting a system without a stage, or out of stage order, fails
  // here rather than showing up as an unreproducible desync months later.
  const stageIndex = SIM_PIPELINE.map((system) => SIM_STAGES.indexOf(system.stage));
  expect(stageIndex, 'a system declares a stage that is not in SIM_STAGES').not.toContain(-1);
  expect(
    stageIndex,
    'SIM_PIPELINE is not sorted by stage; the declared order and the run order disagree',
  ).toEqual([...stageIndex].sort((a, b) => a - b));

  const names = SIM_PIPELINE.map((system) => system.name);
  expect(new Set(names).size, 'two systems share a name').toBe(names.length);
});

test('simulation state stays in f32', () => {
  // The `F32` brand makes storing unrounded arithmetic a compile error (see
  // tests/sim/f32.test.ts). This is the runtime backstop for the one hole the
  // brand cannot close: an `as F32` cast, or a multi-operation expression
  // rounded once at the end instead of at every step. Every coordinate must
  // survive a round trip through f32 unchanged.
  const world = headlessWorld(19);
  for (let tick = 0; tick < 400; tick += 1) {
    step(world, alternatingInputs(1)[0]);
    for (const entity of world.entities) {
      for (const value of [
        entity.position.x,
        entity.position.y,
        entity.velocity.x,
        entity.velocity.y,
      ]) {
        expect(
          Math.fround(value),
          `entity ${entity.id} holds ${value}, which is not representable in f32 — ` +
            'some arithmetic bypassed the helpers in src/sim/vec2.ts',
        ).toBe(value);
      }
    }
  }
});

test('a headless world starts spawned and at tick zero', () => {
  // If this breaks, every replay length in the suite silently shifts by one.
  const world = headlessWorld(0);
  expect(world.tick).toBe(0);

  // Asserted by kind, not by `entities.length`: the invariant is "the players
  // and the ball exist", and counting everything would go red the moment you
  // add a pickup or a particle, for no reason a reviewer would care about.
  const kinds = world.entities.map((entity) => entity.kind);
  expect(kinds.filter((kind) => kind === 'paddle').length, 'expected two paddles').toBe(2);
  expect(kinds.filter((kind) => kind === 'ball').length, 'expected one ball').toBe(1);
  expect(new Set(world.entities.map((entity) => entity.id)).size, 'SimIds must be unique').toBe(
    world.entities.length,
  );

  step(world);
  expect(world.tick, 'one step, one tick').toBe(1);
});

describe('the fixed clock', () => {
  // The renderer is the only caller of FixedClock, and it is the one place
  // where real time meets the simulation. Everything here is about making sure
  // real time can only ever produce WHOLE ticks.
  test('converts real seconds into whole ticks', () => {
    const world = spawnWorld(0);
    const clock = new FixedClock();
    for (let frame = 0; frame < 64; frame += 1) {
      clock.advance(world, TICK_DT);
    }
    expect(world.tick, '64 frames of exactly one tick each must be 64 ticks').toBe(64);
  });

  test('tracks a display rate that is not a multiple of the tick rate', () => {
    // 60fps against a 64Hz tick. The accumulator must not drift: one second of
    // frames is 64 ticks, give or take the sub-tick residue still in the
    // accumulator (1/60 is not exactly representable, so 60 additions of it
    // land a hair under 1.0 and the 64th tick falls into the next frame).
    const world = spawnWorld(0);
    const clock = new FixedClock();
    for (let frame = 0; frame < 60; frame += 1) {
      clock.advance(world, 1 / 60);
    }
    expect(world.tick, 'a second of 60fps frames should be ~64 ticks').toBeGreaterThanOrEqual(63);
    expect(world.tick).toBeLessThanOrEqual(64);
  });

  test('runs no ticks for a delta shorter than one tick', () => {
    const world = spawnWorld(0);
    expect(new FixedClock().advance(world, TICK_DT / 4)).toBe(0);
    expect(world.tick).toBe(0);
  });

  test('caps catch-up after a stall instead of spiralling', () => {
    const world = spawnWorld(0);
    expect(new FixedClock().advance(world, 10)).toBe(FixedClock.MAX_CATCHUP_TICKS);
  });
});
