/**
 * What the capture PAGE can do — as opposed to what the renderer draws.
 *
 * `render.test.ts` asks "did the right pixels come out?". These tests ask the
 * question underneath it: "could this page have loaded the asset, and did the
 * determinism we injected actually take effect?" Both were silently false, and
 * neither is visible in a captured frame:
 *
 *  - the page ran on `about:blank`, so its origin was `null` and a relative
 *    `fetch` THREW at URL parsing. Every three loader routes through `fetch`,
 *    so an asset pipeline that works under `just run` rendered nothing into any
 *    filmed PNG — with no error reaching the agent or the judge.
 *  - `addInitScript` was registered against a page that was never navigated, so
 *    the determinism script never ran at all. `Math.random` was unseeded and
 *    both clocks were on wall time, in the harness whose entire purpose is
 *    reproducibility.
 *
 * A page built "the same way" inside a test would have shared both defects and
 * agreed with the harness, so everything here runs in the REAL capture page via
 * `evaluateInCapturePage`.
 *
 * Each test asserts BOTH directions: the capability works, AND the mechanism
 * can still report failure. A check that cannot go red is not a check.
 */

import { rmSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { afterAll, expect, test } from 'vitest';
import {
  Frame,
  captureFrame,
  closeHarness,
  evaluateInCapturePage,
} from '../../src/view/harness.ts';

afterAll(closeHarness);

/**
 * A planted asset with a colour nothing else in the scene uses, written into
 * the served document root. Removed afterwards, and gitignored so a crashed run
 * cannot leave it behind.
 */
const PROBE_NAME = '__harness-probe.png';
const PROBE_PATH = fileURLToPath(new URL(`../../public/${PROBE_NAME}`, import.meta.url));
const PROBE_RGBA = [237, 41, 191, 255] as const;
const PROBE_SIZE = 8;

function plantProbeAsset(): void {
  const rgba = new Uint8Array(PROBE_SIZE * PROBE_SIZE * 4);
  for (let index = 0; index < rgba.length; index += 4) {
    rgba.set(PROBE_RGBA, index);
  }
  new Frame(PROBE_SIZE, PROBE_SIZE, rgba).savePng(PROBE_PATH);
}

afterAll(() => rmSync(PROBE_PATH, { force: true }));

/** Fetch a URL in the capture page and decode it, exactly as a loader would. */
async function loadInPage(url: string): Promise<{
  status: number | string;
  width?: number;
  height?: number;
  pixel?: number[];
}> {
  return evaluateInCapturePage(async (target: string | null) => {
    let response: Response;
    try {
      response = await fetch(target ?? '');
    } catch (error) {
      // The null-origin failure lands HERE, not in a non-2xx status: the URL
      // cannot even be parsed, so no request is ever made.
      return { status: `THREW: ${(error as Error).message}` };
    }
    if (!response.ok) {
      return { status: response.status };
    }
    const bitmap = await createImageBitmap(await response.blob());
    const canvas = document.createElement('canvas');
    canvas.width = bitmap.width;
    canvas.height = bitmap.height;
    const context = canvas.getContext('2d');
    if (context === null) {
      return { status: 'no 2d context' };
    }
    context.drawImage(bitmap, 0, 0);
    return {
      status: response.status,
      width: bitmap.width,
      height: bitmap.height,
      pixel: [...context.getImageData(0, 0, 1, 1).data],
    };
  }, url);
}

test('the capture page has a real origin and a base URL', async () => {
  const page = await evaluateInCapturePage(
    () => ({ origin: location.origin, baseURI: document.baseURI }),
    null,
  );
  // `about:blank` gives origin "null" as a STRING, which is falsy-looking but
  // is not empty — assert against the real thing rather than truthiness.
  expect(page.origin).not.toBe('null');
  expect(page.baseURI).not.toBe('about:blank');
  expect(page.baseURI).toMatch(/^https?:\/\//);
});

test('a relative asset URL loads in the capture page, with its real pixels', async () => {
  plantProbeAsset();
  const loaded = await loadInPage(`./${PROBE_NAME}`);
  expect(loaded.status).toBe(200);
  expect([loaded.width, loaded.height]).toEqual([PROBE_SIZE, PROBE_SIZE]);
  // Not merely "a response arrived" — the bytes are the planted ones. A 200
  // carrying the wrong file would pass a status-only assertion.
  expect(loaded.pixel).toEqual([...PROBE_RGBA]);
});

test('a missing asset is a 404, not a silent empty texture', async () => {
  // The failing direction. Without this, "loads correctly" and "reports success
  // for everything" are indistinguishable.
  expect((await loadInPage('./__definitely-not-here.png')).status).toBe(404);
});

test('the document root cannot be escaped', async () => {
  // A plain `../` never reaches the route handler: the URL parser resolves it
  // against the origin first, so it arrives as `/package.json` and is simply
  // absent from `public/`.
  expect((await loadInPage('../package.json')).status).toBe(404);

  // Percent-encoded, it survives normalisation and arrives at the handler as
  // literal `..` segments, which the handler itself decodes. THIS is the case
  // the containment check exists for, and it is reachable — without the check
  // it would read `package.json` from the starter root and serve it.
  expect((await loadInPage('/%2e%2e%2fpackage.json')).status).toBe(403);
});

test('the injected determinism script actually ran', async () => {
  // This is the test whose absence let a dead `addInitScript` survive: every
  // pixel assertion in render.test.ts passes whether or not it ran, because
  // the placeholder view happens not to read entropy or a clock.
  expect(await evaluateInCapturePage(() => window.__determinismApplied === true, null)).toBe(true);

  // The marker alone would pass if someone set it without seeding anything, so
  // check the generator IS the injected one. Its recurrence is
  // `seed = (seed * 16807) % 2147483647` over `seed = r * 2147483646 + 1`, and
  // two consecutive draws must satisfy it. The platform's generator does not:
  // it is not an LCG with these constants, and cannot be by chance at 1-in-2^31.
  const [first, second] = await evaluateInCapturePage(
    () => [Math.random(), Math.random()] as const,
    null,
  );
  const seedOf = (value: number): number => Math.round(value * 2147483646 + 1);
  expect(seedOf(second)).toBe((seedOf(first) * 16807) % 2147483647);
});

test('the clocks are virtual and under the harness, not on wall time', async () => {
  const read = async (): Promise<number> => evaluateInCapturePage(() => performance.now(), null);

  await captureFrame(1, 0);
  const atTickZero = await read();
  await captureFrame(1, 64);
  const atTickSixtyFour = await read();

  // Frozen at 0 -> every filmed frame shows the t=0 state and these are equal.
  // On wall time -> reproducibility is gone. Virtual -> exactly one second of
  // simulated time apart, because TICK_HZ is 64.
  expect(atTickZero).toBe(0);
  expect(atTickSixtyFour).toBe(1000);

  // And it is a pure function of the request: same tick, same clock reading.
  await captureFrame(9, 64);
  expect(await read()).toBe(atTickSixtyFour);
});

test('a view that preloads assets still films, and the hook really is awaited', async () => {
  plantProbeAsset();

  // Install the hook the way an asset-loading view would, then film through the
  // ordinary path. Two things must hold: the hook runs before each capture, and
  // the capture still produces a correct frame.
  await evaluateInCapturePage((name: string | null) => {
    const w = window as unknown as { __preloadCount?: number; __preloadPixel?: number[] };
    w.__preloadCount = 0;
    window.__capturePreload = async () => {
      const bitmap = await createImageBitmap(await (await fetch(`./${name}`)).blob());
      const canvas = document.createElement('canvas');
      canvas.width = bitmap.width;
      canvas.height = bitmap.height;
      canvas.getContext('2d')!.drawImage(bitmap, 0, 0);
      w.__preloadPixel = [...canvas.getContext('2d')!.getImageData(0, 0, 1, 1).data];
      w.__preloadCount = (w.__preloadCount ?? 0) + 1;
    };
  }, PROBE_NAME);

  try {
    const frame = await captureFrame(1, 30);
    expect(frame.width).toBeGreaterThan(0);
    // The regression direction: a submission whose assets DO load must still
    // film a normal, non-empty frame.
    const coverage = frame.inkCoverage([10, 13, 23], 8);
    expect(coverage).toBeGreaterThan(0.001);
    expect(coverage).toBeLessThan(0.5);

    const state = await evaluateInCapturePage(() => {
      const w = window as unknown as { __preloadCount?: number; __preloadPixel?: number[] };
      return { count: w.__preloadCount ?? 0, pixel: w.__preloadPixel ?? null };
    }, null);
    expect(state.count).toBeGreaterThan(0);
    // The asset really was decoded inside the capture, with its real bytes.
    expect(state.pixel).toEqual([...PROBE_RGBA]);
  } finally {
    await evaluateInCapturePage(() => {
      window.__capturePreload = undefined;
    }, null);
  }
});

test('a failing preload is reported, not swallowed', async () => {
  // Rule: every reason not to count a failure is a channel a bug can widen.
  // If the hook throws, the capture must fail loudly rather than film a frame
  // with half its assets missing.
  await evaluateInCapturePage(() => {
    window.__capturePreload = () => Promise.reject(new Error('probe: preload exploded'));
  }, null);
  try {
    await expect(captureFrame(1, 5)).rejects.toThrow(/__capturePreload failed/);
  } finally {
    await evaluateInCapturePage(() => {
      window.__capturePreload = undefined;
    }, null);
  }
});
