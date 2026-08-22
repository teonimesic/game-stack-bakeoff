/**
 * The probe trace format, shared by `probe.ts`, `probe-file.ts` and `film.ts`.
 *
 * A trace line is the machine-readable answer to "what is the game doing right
 * now". One line per tick, one JSON object per line:
 *
 *   {"tick": 1, "hash": "0x...", "state": {...}, "events": ["bounce"]}
 *
 * `state` is game-defined. Keep it small, flat and stable: whatever a reader
 * outside this process needs in order to know what happened, expressed as
 * finite JSON numbers, strings and booleans. When you replace the placeholder,
 * replace `stateOf` — nothing else here needs to change.
 *
 * This file lives outside `src/sim` on purpose, so it may touch `node:*`. The
 * simulation itself stays free of I/O.
 */

import { readFileSync } from 'node:fs';
import { type Intents, NO_INTENTS, type World, stateHash } from '../src/sim/index.ts';

/** The hash as an unsigned 64-bit lowercase hex string, zero-padded. */
export function hashHex(world: World): string {
  return `0x${stateHash(world).toString(16).padStart(16, '0')}`;
}

/**
 * A finite JSON number carrying enough digits to round-trip an f32.
 *
 * Nine significant digits is the shortest precision that is guaranteed to
 * recover the same binary32 value. NaN and Infinity are not JSON, so they are
 * an error here rather than something a reader has to guess at.
 */
export function jsonNumber(value: number, what: string): number {
  if (!Number.isFinite(value)) {
    throw new Error(`${what} is ${String(value)}, which cannot appear in a trace line`);
  }
  return Number(value.toPrecision(9));
}

/** The game-defined part of a trace line. Replace this with the real game. */
export function stateOf(world: World): Record<string, unknown> {
  const marker = world.entities.find((entity) => entity.kind === 'marker');
  if (marker === undefined) {
    throw new Error('the world has no marker to report');
  }
  return {
    marker: {
      x: jsonNumber(marker.position.x, 'marker.x'),
      y: jsonNumber(marker.position.y, 'marker.y'),
      vx: jsonNumber(marker.velocity.x, 'marker.vx'),
      vy: jsonNumber(marker.velocity.y, 'marker.vy'),
    },
  };
}

/** One line of the trace, with no trailing newline. */
export function traceLine(world: World): string {
  return JSON.stringify({
    tick: world.tick,
    hash: hashHex(world),
    state: stateOf(world),
    events: [...world.events.events],
  });
}

function flag(source: Record<string, unknown>, ...names: string[]): boolean {
  for (const name of names) {
    if (source[name] === true) {
      return true;
    }
  }
  return false;
}

/** Turn one JSON input object into `Intents`. Unknown fields are ignored. */
export function parseIntents(value: unknown): Intents {
  if (value === null || typeof value !== 'object' || Array.isArray(value)) {
    throw new Error(`expected a JSON object of input fields, got ${JSON.stringify(value)}`);
  }
  const source = value as Record<string, unknown>;
  return {
    nudgeUp: flag(source, 'nudge_up', 'nudgeUp'),
    nudgeDown: flag(source, 'nudge_down', 'nudgeDown'),
  };
}

/**
 * Load an input script: `{"version": 1, "inputs": [{...}, ...]}`.
 *
 * `-` (or an empty path) means "no input at all". Past the end of `inputs` the
 * input is all-false, so a short script is legal.
 */
export function readScript(path: string | undefined): Intents[] {
  if (path === undefined || path === '' || path === '-') {
    return [];
  }
  const parsed: unknown = JSON.parse(readFileSync(path, 'utf8'));
  if (parsed === null || typeof parsed !== 'object' || Array.isArray(parsed)) {
    throw new Error(`${path}: expected a JSON object with "version" and "inputs"`);
  }
  const script = parsed as { version?: unknown; inputs?: unknown };
  if (script.version !== 1) {
    throw new Error(`${path}: unsupported script version ${JSON.stringify(script.version)}`);
  }
  if (!Array.isArray(script.inputs)) {
    throw new Error(`${path}: "inputs" must be an array of input objects`);
  }
  return script.inputs.map(parseIntents);
}

/**
 * The input for step `index`, counted from zero — `inputs[0]` drives the step
 * that produces tick 1. All-false past the end of the script.
 */
export function intentsAt(script: readonly Intents[], index: number): Intents {
  return script[index] ?? NO_INTENTS;
}
