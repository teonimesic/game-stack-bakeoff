// HELD-OUT. The agent never sees this file.
// Mirrors the expected rally length from TickEvents and compares tick by tick.
import { describe, expect, it } from 'vitest';
import { headlessWorld } from '../../src/sim/replay';
import { step, type Intents } from '../../src/sim/index';

// Drive the right paddle to the top so it misses and a point is conceded.
const MISS: Intents = { left: { up: false, down: false }, right: { up: true, down: false } };

function rallyOf(world: unknown): number {
  const v = (world as Record<string, unknown>).rallyLength;
  expect(typeof v, 'world.rallyLength must exist and be a number').toBe('number');
  return v as number;
}

describe('rally counter', () => {
  it('tracks paddle hits and resets on a score', () => {
    const w = headlessWorld(42);
    expect(rallyOf(w)).toBe(0);

    let expected = 0;
    let maxSeen = 0;
    let resets = 0;

    for (let tick = 1; tick <= 3000; tick++) {
      step(w, MISS);
      if (w.events.scored !== null) {
        expected = 0;
        resets++;
      } else {
        expected += w.events.paddleHits.length;
      }
      maxSeen = Math.max(maxSeen, expected);
      expect(rallyOf(w), `tick ${tick}: hits=${w.events.paddleHits.length} scored=${w.events.scored}`).toBe(expected);
    }

    expect(maxSeen, 'no paddle hit ever occurred, so a constant zero would pass').toBeGreaterThan(0);
    expect(resets, 'no score ever occurred, so the reset path was never exercised').toBeGreaterThan(0);
  });

  it('is part of the simulation snapshot', () => {
    const a = headlessWorld(7);
    const b = headlessWorld(7);
    for (let tick = 1; tick <= 500; tick++) {
      step(a, MISS);
      step(b, MISS);
      expect(rallyOf(a), `tick ${tick}: two runs of seed 7 disagreed`).toBe(rallyOf(b));
    }
  });
});
