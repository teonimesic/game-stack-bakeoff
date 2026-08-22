/**
 * `just probe-file SEED TICKS SCRIPT OUT` — the batch probe.
 *
 * Runs the simulation headlessly for TICKS ticks from SEED, feeding one input
 * per tick from SCRIPT, and writes a JSON Lines trace to OUT: one line per
 * tick, starting at tick 1.
 *
 * SCRIPT is `{"version": 1, "inputs": [{...}, ...]}`, or `-` for no input at
 * all. Exits non-zero if it could not run every requested tick.
 */

import { mkdirSync, writeFileSync } from 'node:fs';
import { dirname } from 'node:path';
import { step } from '../src/sim/index.ts';
import { headlessWorld } from '../src/sim/replay.ts';
import { intentsAt, readScript, traceLine } from './trace.ts';

const [seed, ticksArg, scriptPath, out] = process.argv.slice(2);

if (seed === undefined || ticksArg === undefined || out === undefined) {
  process.stderr.write('usage: probe-file SEED TICKS SCRIPT OUT   (SCRIPT may be "-")\n');
  process.exit(2);
}

const ticks = Number(ticksArg);
if (!Number.isInteger(ticks) || ticks < 0) {
  process.stderr.write(`TICKS must be a non-negative integer, got ${ticksArg}\n`);
  process.exit(2);
}

try {
  const script = readScript(scriptPath);
  const world = headlessWorld(BigInt(seed));
  const lines: string[] = [];

  for (let index = 0; index < ticks; index += 1) {
    step(world, intentsAt(script, index));
    lines.push(traceLine(world));
  }

  if (lines.length !== ticks) {
    throw new Error(`produced ${lines.length} trace lines, expected ${ticks}`);
  }

  mkdirSync(dirname(out), { recursive: true });
  writeFileSync(out, lines.length === 0 ? '' : `${lines.join('\n')}\n`);
  process.stderr.write(`wrote ${lines.length} ticks to ${out}\n`);
} catch (error) {
  process.stderr.write(`${error instanceof Error ? error.message : String(error)}\n`);
  process.exit(1);
}
