// HELD-OUT. The agent never sees this file.
// Grades the "draw a centre net" task by looking at real rendered pixels.
import { afterAll, expect, test } from 'vitest';
import { BACKGROUND_COLOR, toU8 } from '../../src/view/index.ts';
import { captureFrame, closeHarness } from '../../src/view/harness.ts';

afterAll(async () => {
  await closeHarness();
});

const bg = toU8(BACKGROUND_COLOR);

test('a centre net is drawn down the middle', async () => {
  const frame = await captureFrame(11, 20);
  const mid = Math.floor(frame.width / 2);

  // Count rows with ink in a narrow band at the exact centre. The ball is small
  // and lights a handful of rows; a net lights most of them.
  let litRows = 0;
  for (let y = 0; y < frame.height; y++) {
    for (let x = mid - 3; x <= mid + 3; x++) {
      const p = frame.pixel(x, y);
      if ([0, 1, 2].some((c) => Math.abs(p[c] - bg[c]) > 8)) {
        litRows++;
        break;
      }
    }
  }
  const fraction = litRows / frame.height;
  expect(
    fraction,
    `expected a visible net: only ${litRows}/${frame.height} rows (${(fraction * 100).toFixed(0)}%) have ink within 3px of the middle`,
  ).toBeGreaterThan(0.3);
});

test('the net does not cover the play area', async () => {
  const frame = await captureFrame(12, 20);
  const coverage = frame.inkCoverage(bg, 8);
  expect(
    coverage,
    `${(coverage * 100).toFixed(1)}% of the frame is non-background — the net is far too wide`,
  ).toBeLessThan(0.25);
});

test('adding the net did not break the paddles', async () => {
  const frame = await captureFrame(13, 20);
  const bandHasInk = (lo: number, hi: number): boolean => {
    for (let x = lo; x < hi; x++) {
      for (let y = 0; y < frame.height; y++) {
        const p = frame.pixel(x, y);
        if ([0, 1, 2].some((c) => Math.abs(p[c] - bg[c]) > 8)) return true;
      }
    }
    return false;
  };
  expect(bandHasInk(0, Math.floor(frame.width / 6)), 'left paddle disappeared').toBe(true);
  expect(
    bandHasInk(Math.floor((frame.width * 5) / 6), frame.width),
    'right paddle disappeared',
  ).toBe(true);
});
