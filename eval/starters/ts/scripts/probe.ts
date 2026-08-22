/**
 * `just probe SEED` — the streaming probe.
 *
 * A long-lived headless process driven over stdin/stdout, so a driver can react
 * to the state instead of replaying a fixed tape.
 *
 *   stdout : one JSON trace line per tick, flushed immediately. Nothing else.
 *   stdin  : one JSON input object per line. An empty line means "all false".
 *            `quit`, or EOF, ends the run with exit code 0.
 *
 * Everything diagnostic goes to stderr — a stray `console.log` here corrupts
 * the protocol for whoever is reading.
 */

import { createInterface } from 'node:readline';
import { step } from '../src/sim/index.ts';
import { headlessWorld } from '../src/sim/replay.ts';
import { parseIntents, traceLine } from './trace.ts';

const seed = process.argv[2];
if (seed === undefined) {
  process.stderr.write('usage: probe SEED\n');
  process.exit(2);
}

const world = headlessWorld(BigInt(seed));

/** stdout is the protocol. One line, one write, no buffering of our own. */
function emit(line: string): void {
  process.stdout.write(`${line}\n`);
}

// The header: the world before any tick has run, so a driver has a complete
// picture before it has to choose its first input.
emit(traceLine(world));

const lines = createInterface({ input: process.stdin, crlfDelay: Infinity });

try {
  for await (const line of lines) {
    const trimmed = line.trim();
    if (trimmed === 'quit') {
      break;
    }
    step(world, trimmed === '' ? undefined : parseIntents(JSON.parse(trimmed)));
    emit(traceLine(world));
  }
} catch (error) {
  process.stderr.write(`${error instanceof Error ? error.message : String(error)}\n`);
  process.exitCode = 1;
}

lines.close();
process.stdin.destroy();
