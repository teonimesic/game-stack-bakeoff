/**
 * `just film SEED TICKS SCRIPT OUTDIR` — see what a run looked like.
 *
 * Captures at most 12 frames, evenly spaced over `0..=TICKS` inclusive (both
 * ends always included), and writes them to OUTDIR as `frame_0000.png`,
 * `frame_0001.png`, … Same simulation, same inputs and same renderer as the
 * render tests: this drives `captureFrame` from `src/view/harness.ts` rather
 * than re-implementing a second render path that could disagree with it.
 *
 * SCRIPT is the same file the probe reads, or `-` for no input at all.
 */

import { mkdirSync } from 'node:fs';
import { captureFrame, closeHarness } from '../src/view/harness.ts';
import { intentsAt, readScript } from './trace.ts';

/** Never more than this many PNGs, however long the run is. */
const MAX_FRAMES = 12;

const [seed, ticksArg, scriptPath, outDir] = process.argv.slice(2);

if (seed === undefined || ticksArg === undefined || outDir === undefined) {
  process.stderr.write('usage: film SEED TICKS SCRIPT OUTDIR   (SCRIPT may be "-")\n');
  process.exit(2);
}

const ticks = Number(ticksArg);
if (!Number.isInteger(ticks) || ticks < 0) {
  process.stderr.write(`TICKS must be a non-negative integer, got ${ticksArg}\n`);
  process.exit(2);
}

/** Evenly spaced tick numbers over `0..=ticks`, truncating, ends included. */
function sampleTicks(total: number): number[] {
  const count = Math.min(MAX_FRAMES, total + 1);
  if (count <= 1) {
    return [0];
  }
  return Array.from({ length: count }, (_unused, index) =>
    Math.floor((index * total) / (count - 1)),
  );
}

try {
  const script = readScript(scriptPath);
  const inputs = Array.from({ length: ticks }, (_unused, index) => intentsAt(script, index));
  mkdirSync(outDir, { recursive: true });

  const wanted = sampleTicks(ticks);
  for (const [index, tick] of wanted.entries()) {
    const frame = await captureFrame(BigInt(seed), tick, inputs);
    const path = frame.savePng(`${outDir}/frame_${String(index).padStart(4, '0')}.png`);
    process.stderr.write(`tick ${tick} -> ${path}\n`);
  }
  process.stderr.write(`wrote ${wanted.length} frames to ${outDir}\n`);
} catch (error) {
  process.stderr.write(`${error instanceof Error ? error.message : String(error)}\n`);
  process.exitCode = 1;
} finally {
  await closeHarness();
}
