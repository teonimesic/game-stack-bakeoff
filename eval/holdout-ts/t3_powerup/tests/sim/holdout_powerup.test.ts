// HELD-OUT. The agent never sees this file.
// A determinism trap: the obvious implementation reaches for Math.random or
// Date.now, both of which pass review and fail here.
import { describe, expect, it } from 'vitest';
import { headlessWorld } from '../../src/sim/replay';
import { step, ARENA_HALF_WIDTH, ARENA_HALF_HEIGHT } from '../../src/sim/index';

function powerupPositions(seed: number, ticks: number): (string | null)[] {
  const w = headlessWorld(seed);
  const out: (string | null)[] = [];
  for (let i = 0; i < ticks; i++) {
    step(w);
    const p = w.entities
      .filter((e) => (e as { kind: string }).kind === 'powerup')
      .map((e) => `${e.position.x},${e.position.y}`)
      .sort();
    out.push(p.length > 0 ? p[0]! : null);
  }
  return out;
}

describe('powerup', () => {
  it('exists and moves over time', () => {
    const seen = powerupPositions(3, 900);
    expect(seen.filter((p) => p !== null).length, 'no entity with kind "powerup" ever existed').toBeGreaterThan(0);
    expect(new Set(seen.filter((p) => p !== null)).size, 'the powerup never changed position in 900 ticks').toBeGreaterThan(1);
  });

  it('is deterministic for a seed', () => {
    const a = powerupPositions(11, 900);
    const b = powerupPositions(11, 900);
    const diff = a.findIndex((v, i) => v !== b[i]);
    expect(diff, `two runs with seed 11 disagreed at tick ${diff} — placement reads entropy from outside the sim`).toBe(-1);
  });

  it('actually depends on the seed', () => {
    expect(powerupPositions(1, 900), 'seeds 1 and 2 produced identical placements').not.toEqual(powerupPositions(2, 900));
  });

  it('stays inside the arena', () => {
    for (const seed of [5, 6, 7]) {
      for (const p of powerupPositions(seed, 600)) {
        if (p === null) continue;
        const [x, y] = p.split(',').map(Number) as [number, number];
        expect(Math.abs(x), `seed ${seed}: powerup outside arena at ${p}`).toBeLessThanOrEqual(ARENA_HALF_WIDTH);
        expect(Math.abs(y), `seed ${seed}: powerup outside arena at ${p}`).toBeLessThanOrEqual(ARENA_HALF_HEIGHT);
      }
    }
  });
});
