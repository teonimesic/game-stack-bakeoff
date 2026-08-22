/**
 * End-to-end rendering tests: the real renderer, a real GPU path, real pixels.
 *
 * These are the tests that catch "the code compiles, the logic is right, and
 * nothing appears on screen." Unit tests on `sim` cannot catch that class of
 * bug, and it is the class that matters most in a game.
 *
 * Ordered from most robust to most brittle:
 *   1. invariants on the pixels (something rendered; it is where we expect)
 *   2. relational assertions (it moved in the right direction)
 *   3. golden-image comparison (it looks exactly like the approved frame)
 *
 * Prefer 1 and 2. Reach for 3 only when the exact look is the thing under test.
 *
 * EVERY failure here writes PNGs to `tests/render/artifacts/` and prints their
 * absolute paths plus a numeric description of the difference, so a failure is
 * actionable without opening an image.
 */

import { rmSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { afterAll, beforeAll, expect, test } from 'vitest';
import type { Intents } from '../../src/sim/index.ts';
import { BACKGROUND_COLOR, VIEW_HEIGHT, VIEW_WIDTH, toU8 } from '../../src/view/index.ts';
import {
  Frame,
  adapterName,
  captureFrame,
  closeHarness,
  formatDiffReport,
  pageDiagnostics,
} from '../../src/view/harness.ts';

afterAll(closeHarness);

/** Background as u8 RGB, for "is this pixel ink?" tests. */
const BACKGROUND = toU8(BACKGROUND_COLOR);
const INK_TOLERANCE = 8;

const GOLDEN = fileURLToPath(new URL('./golden/rally.png', import.meta.url));
/** Failure evidence lands here. Wiped at the start of every run so a stale PNG
 * can never be mistaken for the current failure. Gitignored. */
const ARTIFACTS = fileURLToPath(new URL('./artifacts/', import.meta.url));

beforeAll(async () => {
  rmSync(ARTIFACTS, { recursive: true, force: true });
  // Print the rasteriser once. A golden diff that appears from nowhere is
  // almost always this line changing.
  try {
    console.log(`GL adapter: ${await adapterName()}`);
  } catch {
    /* frameOrSkip reports the same problem with more context */
  }
});

/** Write a frame into the artifacts directory and return its absolute path. */
function artifact(name: string, frame: Frame): string {
  return frame.savePng(`${ARTIFACTS}${name}.png`);
}

/**
 * Skip rather than fail when there is no usable GL adapter. A developer on a
 * machine that cannot create a WebGL2 context should not see red tests they
 * cannot fix; CI pins a rasteriser and runs them for real.
 */
async function frameOrSkip(
  seed: number,
  ticks: number,
  inputs: readonly Intents[] = [],
): Promise<Frame | null> {
  try {
    return await captureFrame(seed, ticks, inputs);
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    if (message.includes('no adapter')) {
      console.warn(`SKIP: no usable GL adapter in this environment (${message})`);
      return null;
    }
    throw error;
  }
}

test('renders a non-empty frame', async () => {
  // The single most valuable rendering assertion there is: the renderer ran and
  // drew something other than the clear colour.
  const frame = await frameOrSkip(1, 30);
  if (frame === null) return;

  expect(frame.width).toBe(VIEW_WIDTH);
  expect(frame.height).toBe(VIEW_HEIGHT);

  const coverage = frame.inkCoverage(BACKGROUND, INK_TOLERANCE);
  if (coverage <= 0.001 || coverage >= 0.5) {
    const path = artifact('non-empty-frame', frame);
    throw new Error(
      `${(coverage * 100).toFixed(4)}% of pixels differ from the background ` +
        `(expected between 0.1% and 50%).\n` +
        (coverage <= 0.001
          ? 'Nothing was drawn. The simulation may be running correctly while the view is ' +
            'broken: check that createView() spawns a mesh for every entity and that the ' +
            'camera frames the arena.\n'
          : 'Almost everything was drawn. The camera is probably mis-scaled or a quad is ' +
            'covering the screen.\n') +
        `frame: ${path}\n${pageDiagnostics(5)}`,
    );
  }
});

test('both paddles and the ball are visible', async () => {
  const frame = await frameOrSkip(2, 1);
  if (frame === null) return;

  // Paddles sit near the left and right edges; the ball starts centred.
  const regions = [
    { what: 'the left paddle', x0: 0, x1: Math.floor(frame.width / 6) },
    {
      what: 'the ball',
      x0: Math.floor((frame.width * 2) / 5),
      x1: Math.floor((frame.width * 3) / 5),
    },
    { what: 'the right paddle', x0: Math.floor((frame.width * 5) / 6), x1: frame.width },
  ];
  const missing = regions.filter(
    (region) => frame.inkCentroid(BACKGROUND, INK_TOLERANCE, region) === null,
  );
  if (missing.length > 0) {
    const path = artifact('paddles-and-ball', frame);
    throw new Error(
      missing.map((r) => `no ink in x ${r.x0}..${r.x1} — ${r.what} is missing`).join('\n') +
        `\nframe: ${path}`,
    );
  }
});

test('moving a paddle up moves its pixels up', async () => {
  // A relational assertion: robust to colour changes, sprite-size changes and
  // rasteriser differences, but still a genuine end-to-end check that input
  // reaches the screen.
  //
  // Screen y grows downward, so "up" in world space means a SMALLER pixel y.
  const holdUp = new Array<Intents>(60).fill({
    left: { up: true, down: false },
    right: { up: false, down: false },
  });

  const still = await frameOrSkip(3, 60);
  const raised = await frameOrSkip(3, 60, holdUp);
  if (still === null || raised === null) return;

  // Look only at the left sixth so the ball and right paddle can't confuse us.
  const leftPaddleY = (frame: Frame): number | null =>
    frame.inkCentroid(BACKGROUND, INK_TOLERANCE, { x0: 0, x1: Math.floor(frame.width / 6) })?.y ??
    null;

  const stillY = leftPaddleY(still);
  const raisedY = leftPaddleY(raised);
  if (stillY === null || raisedY === null || raisedY >= stillY - 10) {
    const paths = [artifact('paddle-still', still), artifact('paddle-raised', raised)];
    throw new Error(
      `holding 'up' for 60 ticks should raise the left paddle by more than 10px on screen.\n` +
        `left-paddle centroid: idle y=${stillY?.toFixed(1) ?? 'not found'}, ` +
        `holding-up y=${raisedY?.toFixed(1) ?? 'not found'} (screen y grows DOWNWARD, so ` +
        `holding up must DECREASE it).\n` +
        `Check that main.ts maps the key to PlayerIntent.up and that intent reaches step().\n` +
        `frames: ${paths.join(', ')}\n` +
        formatDiffReport(still.diffReport(raised, INK_TOLERANCE)),
    );
  }
});

test('rendering is reproducible across runs', async () => {
  // Same seed, same ticks, same pixels. If this fails, either the simulation is
  // nondeterministic (check the `sim` tests first) or the render path is.
  const a = await frameOrSkip(4, 45);
  const b = await frameOrSkip(4, 45);
  if (a === null || b === null) return;

  const report = a.diffReport(b, 0);
  if (report.differing > 0) {
    const paths = [
      artifact('reproducible-a', a),
      artifact('reproducible-b', b),
      artifact('reproducible-diff', a.diffImage(b, 0)),
    ];
    throw new Error(
      'two identical runs produced different frames. Run `just test-sim` first: if the ' +
        'determinism tests are red the cause is in src/sim, otherwise it is in the render ' +
        `path (an unsorted draw order, or a mesh keyed on array position).\n` +
        `${formatDiffReport(report)}\nframes: ${paths.join(', ')}`,
    );
  }
});

/**
 * Golden-image comparison.
 *
 * Regenerate deliberately with `just bless`, and *look at the new image* before
 * committing it. Blessing without looking turns this test into a rubber stamp.
 */
test('matches the golden frame', async () => {
  const frame = await frameOrSkip(5, 90);
  if (frame === null) return;

  if (process.env.BLESS !== undefined) {
    frame.savePng(GOLDEN);
    console.warn(`blessed ${GOLDEN}`);
    return;
  }

  let golden: Frame;
  try {
    golden = Frame.loadPng(GOLDEN);
  } catch {
    console.warn(
      `SKIP: no golden image at ${GOLDEN}. Create it with \`just bless\`, then inspect ` +
        'the PNG before committing.',
    );
    return;
  }

  // Tolerance absorbs cross-vendor rasteriser rounding, not misplaced geometry.
  // A quad in the wrong place moves thousands of pixels, not a handful.
  const TOLERANCE = 4;
  const BUDGET = 0.002;
  const report = frame.diffReport(golden, TOLERANCE);
  if (report.fraction > BUDGET) {
    const paths = {
      actual: artifact('golden-actual', frame),
      expected: artifact('golden-expected', golden),
      diff: artifact('golden-diff', frame.diffImage(golden, TOLERANCE)),
    };
    throw new Error(
      `the rendered frame differs from the golden image by more than the ` +
        `${(BUDGET * 100).toFixed(1)}% budget (per-channel tolerance ${TOLERANCE}/255).\n\n` +
        `${formatDiffReport(report)}\n\n` +
        `actual  : ${paths.actual}\n` +
        `expected: ${paths.expected}\n` +
        `diff    : ${paths.diff}   (magenta = differs, dimmed = matches)\n\n` +
        'A wide, low-delta difference is usually a colour or anti-aliasing change. A dense ' +
        'difference inside a small box is geometry that moved — find it before you bless. ' +
        'If the change is intended and you have LOOKED at the actual PNG, run `just bless`. ' +
        'Do NOT widen the budget.',
    );
  }
});
