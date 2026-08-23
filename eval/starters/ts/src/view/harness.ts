/**
 * Node half of the headless render harness — the template's answer to "prove it
 * actually drew something".
 *
 * Bundles `capture.ts`, runs it in headless Chromium, and pulls the rendered
 * pixels back as bytes. No display, no window, no jsdom: the pixels come
 * out of a real GL rasteriser.
 */

import { Buffer } from 'node:buffer';
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, join, relative, resolve, sep } from 'node:path';
import { fileURLToPath } from 'node:url';
import * as esbuild from 'esbuild';
import { PNG } from 'pngjs';
import { type Browser, type Page, chromium } from 'playwright';
import { TICK_HZ } from '../sim/index.ts';
import type { Intents, Seed } from '../sim/index.ts';
import type { CaptureRequest, CaptureResult } from './capture.ts';
import { VIEW_HEIGHT, VIEW_WIDTH } from './index.ts';

/** A captured frame: tightly packed RGBA8, `width * height * 4` bytes. */
export class Frame {
  constructor(
    readonly width: number,
    readonly height: number,
    readonly rgba: Uint8Array,
  ) {}

  pixel(x: number, y: number): [number, number, number, number] {
    const index = (y * this.width + x) * 4;
    return [this.rgba[index]!, this.rgba[index + 1]!, this.rgba[index + 2]!, this.rgba[index + 3]!];
  }

  private isInk(index: number, background: readonly number[], tolerance: number): boolean {
    for (let channel = 0; channel < 3; channel += 1) {
      if (Math.abs(this.rgba[index + channel]! - background[channel]!) > tolerance) {
        return true;
      }
    }
    return false;
  }

  /**
   * Fraction of pixels that are not the background colour. A cheap, robust
   * "did anything actually render?" signal that does not depend on a golden
   * file and does not break when colours are tweaked.
   */
  inkCoverage(background: readonly number[], tolerance: number): number {
    let lit = 0;
    for (let index = 0; index < this.rgba.length; index += 4) {
      if (this.isInk(index, background, tolerance)) {
        lit += 1;
      }
    }
    return lit / (this.width * this.height);
  }

  /**
   * Centre of mass of non-background pixels, in pixel coordinates, or `null`
   * for an empty frame.
   *
   * This is how you assert "the marker moved right" without a golden image and
   * without caring about exact pixel values.
   */
  inkCentroid(
    background: readonly number[],
    tolerance: number,
    region?: { x0: number; x1: number },
  ): { x: number; y: number } | null {
    const x0 = region?.x0 ?? 0;
    const x1 = region?.x1 ?? this.width;
    let sumX = 0;
    let sumY = 0;
    let count = 0;
    for (let y = 0; y < this.height; y += 1) {
      for (let x = x0; x < x1; x += 1) {
        if (this.isInk((y * this.width + x) * 4, background, tolerance)) {
          sumX += x;
          sumY += y;
          count += 1;
        }
      }
    }
    return count === 0 ? null : { x: sumX / count, y: sumY / count };
  }

  /**
   * Fraction of pixels whose colour differs from `other` by more than
   * `tolerance` on any channel.
   *
   * Tolerance exists because rasterisers are not bit-identical across vendors,
   * drivers, or backends — the same scene on SwiftShader and on a discrete GPU
   * will differ in the last bit or two of an edge. Tolerance does NOT exist to
   * paper over a quad being in the wrong place; that shows up as a large
   * fraction, not a small one.
   */
  diffFraction(other: Frame, tolerance: number): number {
    if (this.width !== other.width || this.height !== other.height) {
      throw new Error('cannot diff frames of different sizes');
    }
    let differing = 0;
    for (let index = 0; index < this.rgba.length; index += 4) {
      for (let channel = 0; channel < 3; channel += 1) {
        if (Math.abs(this.rgba[index + channel]! - other.rgba[index + channel]!) > tolerance) {
          differing += 1;
          break;
        }
      }
    }
    return differing / (this.width * this.height);
  }

  /**
   * Everything an agent that can only read text needs in order to act on a
   * pixel mismatch: how much differs, WHERE it differs, and by how much.
   *
   * "0.4% of pixels differ" is not actionable. "0.4% of pixels differ, all of
   * them in a 24x180 box at x=316" says "something new is drawn down the middle
   * of the screen" without ever opening the PNG.
   */
  diffReport(other: Frame, tolerance: number, grid = { cols: 8, rows: 5 }): DiffReport {
    if (this.width !== other.width || this.height !== other.height) {
      throw new Error(
        `cannot diff frames of different sizes: ${this.width}x${this.height} vs ` +
          `${other.width}x${other.height}`,
      );
    }
    const cells = Array.from({ length: grid.rows }, () => new Array<number>(grid.cols).fill(0));
    let differing = 0;
    let maxDelta = 0;
    let x0 = this.width;
    let y0 = this.height;
    let x1 = -1;
    let y1 = -1;

    for (let y = 0; y < this.height; y += 1) {
      for (let x = 0; x < this.width; x += 1) {
        const index = (y * this.width + x) * 4;
        let delta = 0;
        for (let channel = 0; channel < 3; channel += 1) {
          delta = Math.max(
            delta,
            Math.abs(this.rgba[index + channel]! - other.rgba[index + channel]!),
          );
        }
        if (delta > tolerance) {
          differing += 1;
          maxDelta = Math.max(maxDelta, delta);
          if (x < x0) x0 = x;
          if (y < y0) y0 = y;
          if (x > x1) x1 = x;
          if (y > y1) y1 = y;
          const col = Math.min(grid.cols - 1, Math.floor((x * grid.cols) / this.width));
          const row = Math.min(grid.rows - 1, Math.floor((y * grid.rows) / this.height));
          cells[row]![col]! += 1;
        }
      }
    }

    const total = this.width * this.height;
    const cellArea = (this.width / grid.cols) * (this.height / grid.rows);
    return {
      differing,
      total,
      fraction: differing / total,
      maxChannelDelta: maxDelta,
      bbox: x1 < 0 ? null : { x0, y0, x1, y1 },
      grid: { ...grid, fractions: cells.map((row) => row.map((n) => n / cellArea)) },
    };
  }

  /**
   * A frame that shows the difference: everything that matches is dimmed to a
   * quarter brightness, everything that differs is solid magenta. Readable at a
   * glance, and it does not depend on the viewer's diff tooling.
   */
  diffImage(other: Frame, tolerance: number): Frame {
    const out = new Uint8Array(this.rgba.length);
    for (let index = 0; index < this.rgba.length; index += 4) {
      let delta = 0;
      for (let channel = 0; channel < 3; channel += 1) {
        delta = Math.max(
          delta,
          Math.abs(this.rgba[index + channel]! - other.rgba[index + channel]!),
        );
      }
      if (delta > tolerance) {
        out[index] = 255;
        out[index + 1] = 0;
        out[index + 2] = 255;
      } else {
        for (let channel = 0; channel < 3; channel += 1) {
          out[index + channel] = this.rgba[index + channel]! >> 2;
        }
      }
      out[index + 3] = 255;
    }
    return new Frame(this.width, this.height, out);
  }

  savePng(path: string): string {
    mkdirSync(dirname(path), { recursive: true });
    const png = new PNG({ width: this.width, height: this.height });
    png.data = Buffer.from(this.rgba.buffer, this.rgba.byteOffset, this.rgba.byteLength);
    writeFileSync(path, PNG.sync.write(png));
    return path;
  }

  static loadPng(path: string): Frame {
    const png = PNG.sync.read(readFileSync(path));
    return new Frame(png.width, png.height, new Uint8Array(png.data));
  }
}

export interface DiffReport {
  /** Pixels differing by more than the tolerance on any channel. */
  readonly differing: number;
  readonly total: number;
  readonly fraction: number;
  /** Largest single-channel difference seen, 0..255. */
  readonly maxChannelDelta: number;
  /** Tight box around the differing pixels, or `null` if there are none. */
  readonly bbox: { x0: number; y0: number; x1: number; y1: number } | null;
  /** Per-region diff density, so the failure text says *where*. */
  readonly grid: { cols: number; rows: number; fractions: number[][] };
}

/**
 * Render the report as text. This is what an agent reads instead of the PNGs,
 * so it has to be self-explanatory with no image viewer.
 */
export function formatDiffReport(report: DiffReport): string {
  const pct = (value: number): string => `${(value * 100).toFixed(3)}%`;
  const lines = [
    `differing pixels : ${report.differing} of ${report.total} (${pct(report.fraction)})`,
    `max channel delta: ${report.maxChannelDelta} of 255 ` +
      `(a small delta over a wide area is a colour/AA change; a large delta in a ` +
      `tight box is geometry in the wrong place)`,
  ];
  if (report.bbox === null) {
    lines.push('bounding box     : none — the frames match');
    return lines.join('\n');
  }
  const { x0, y0, x1, y1 } = report.bbox;
  lines.push(
    `bounding box     : x ${x0}..${x1}, y ${y0}..${y1} ` +
      `(${x1 - x0 + 1}x${y1 - y0 + 1} px; y grows DOWNWARD)`,
  );
  lines.push(
    `region map       : % of each cell that differs, ${report.grid.cols} cols x ${report.grid.rows} rows`,
  );
  for (const row of report.grid.fractions) {
    lines.push(`  ${row.map((f) => (f * 100).toFixed(1).padStart(6)).join(' ')}`);
  }
  return lines.join('\n');
}

/**
 * Make the page reproducible before any of our code runs.
 *
 * The same injection three.js uses in its own screenshot CI: seed `Math.random`
 * so anything that reaches for entropy gets the same sequence, put both clocks
 * under the harness's control so time-dependent code cannot vary, and make
 * `requestAnimationFrame` single-shot so a stray animation loop cannot race the
 * capture.
 *
 * `addInitScript` only runs on document creation, so this is registered BEFORE
 * `page.goto`. Registering it against an `about:blank` page that is never
 * navigated leaves the whole script dead, and a dead determinism script is
 * indistinguishable from a live one by anything the page can see: `Math.random`
 * simply stays unseeded and both clocks stay on wall time.
 *
 * THE CLOCKS ARE NOT FROZEN — they are VIRTUAL. `captureFrame` sets
 * `__nowMs` to the wall-clock time the captured tick corresponds to, so
 * `performance.now()` is a pure function of the request (same tick, same
 * value: still deterministic) that nevertheless ADVANCES from one filmed frame
 * to the next. Pinning it to a constant instead makes every time-driven view
 * effect — a tween, a shader `uTime`, `AnimationMixer.setTime` — show its t=0
 * state in all 12 frames of `just film`, which looks exactly like a submission
 * that never animated anything.
 */
const DETERMINISM_SCRIPT = `
  let seed = 1;
  Math.random = () => {
    seed = (seed * 16807) % 2147483647;
    return (seed - 1) / 2147483646;
  };
  window.__nowMs = 0;
  Date.now = () => window.__nowMs;
  performance.now = () => window.__nowMs;
  const raf = window.requestAnimationFrame;
  let fired = false;
  window.requestAnimationFrame = (callback) => (fired ? 0 : ((fired = true), raf(() => callback(0))));
  // Record that this ran. A determinism script registered against a page that
  // is never navigated is dead, and a dead one is invisible from inside the
  // page — every pixel assertion passes either way. This is the marker that
  // makes "did the instrument do its job?" answerable rather than assumed.
  window.__determinismApplied = true;
`;

/**
 * A real origin for the capture page.
 *
 * `page.setContent` leaves the document on `about:blank`, whose origin is
 * `null` and which has no base URL. In that page a relative `fetch` does not
 * fail — it THROWS at URL parsing, before any request — so `TextureLoader`,
 * `GLTFLoader`, `FileLoader` and everything else in three that routes through
 * `fetch` reports a bare `error` with no cause. An asset pipeline that works
 * under `just run` then renders nothing into any of the 12 PNGs `just film`
 * produces, with no error anywhere the judge or the agent can see.
 *
 * Nothing is ever fetched over the network: `page.route` intercepts this origin
 * and serves it from `public/` on disk. The hostname is under `.localhost`,
 * which Chromium treats as a secure context, so `AudioContext`, `crypto.subtle`
 * and friends behave as they do under the dev server.
 */
const HARNESS_ORIGIN = 'http://harness.localhost';

/** Served as the capture document root. */
const HARNESS_PUBLIC = fileURLToPath(new URL('../../public/', import.meta.url));

const CONTENT_TYPES: Readonly<Record<string, string>> = {
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.webp': 'image/webp',
  '.gif': 'image/gif',
  '.svg': 'image/svg+xml',
  '.json': 'application/json',
  '.gltf': 'model/gltf+json',
  '.glb': 'model/gltf-binary',
  '.bin': 'application/octet-stream',
  '.ktx2': 'image/ktx2',
  '.hdr': 'image/vnd.radiance',
  '.wav': 'audio/wav',
  '.mp3': 'audio/mpeg',
  '.ogg': 'audio/ogg',
  '.js': 'text/javascript',
  '.css': 'text/css',
  '.html': 'text/html; charset=utf-8',
  '.txt': 'text/plain; charset=utf-8',
};

/** `public/` is the document root and nothing above it is reachable. */
function resolveUnderPublic(pathname: string): string | null {
  const candidate = resolve(join(HARNESS_PUBLIC, decodeURIComponent(pathname).replace(/^\/+/, '')));
  const inside = relative(resolve(HARNESS_PUBLIC), candidate);
  return inside === '' || (!inside.startsWith('..') && !inside.startsWith(sep)) ? candidate : null;
}

/**
 * Pin the rasteriser instead of taking whatever the host has.
 *
 * SwiftShader is ANGLE's software backend and is present in every Chromium
 * build, so the same flags produce the same pixels on a laptop with a discrete
 * GPU and on a CI container with none. This is the browser-stack equivalent of
 * forcing lavapipe in a Vulkan CI job.
 */
const CHROMIUM_ARGS = ['--use-angle=swiftshader', '--enable-unsafe-swiftshader'];

let session: Promise<{ browser: Browser; page: Page }> | null = null;
let bundle: Promise<string> | null = null;

function captureBundle(): Promise<string> {
  bundle ??= esbuild
    .build({
      entryPoints: [fileURLToPath(new URL('./capture.ts', import.meta.url))],
      bundle: true,
      write: false,
      format: 'iife',
      platform: 'browser',
      target: 'chrome120',
    })
    .then((result) => result.outputFiles[0]!.text);
  return bundle;
}

/**
 * Everything the page said, kept so a failure can quote it.
 *
 * A WebGL error, a shader compile warning or a `console.error` from three
 * otherwise vanishes: `page.evaluate` only propagates the thrown value. Without
 * this, "readback returned 0 bytes" is all you get, and the actual cause —
 * "THREE.WebGLRenderer: Context Lost" — is lost with it.
 */
const pageLog: string[] = [];

async function harnessPage(): Promise<Page> {
  session ??= (async () => {
    const browser = await chromium.launch({ args: CHROMIUM_ARGS });
    const page = await browser.newPage();
    page.on('console', (message) => pageLog.push(`[${message.type()}] ${message.text()}`));
    page.on('pageerror', (error) => pageLog.push(`[pageerror] ${error.message}`));

    // Serve the capture document and everything under `public/` from disk, so
    // the page has a real origin and relative URLs resolve the way they do
    // under `just run`. Requests never leave the process.
    await page.route(`${HARNESS_ORIGIN}/**`, (route) => {
      const { pathname } = new URL(route.request().url());
      if (pathname === '/') {
        return route.fulfill({
          contentType: 'text/html; charset=utf-8',
          body: '<!doctype html><meta charset="utf-8"><body></body>',
        });
      }
      const file = resolveUnderPublic(pathname);
      if (file === null) {
        pageLog.push(`[harness] refused to serve outside public/: ${pathname}`);
        return route.fulfill({ status: 403, body: 'outside public/' });
      }
      let body: Buffer;
      try {
        body = readFileSync(file);
      } catch {
        // Logged, not silent: "the texture is missing from public/" and "the
        // loader is broken" look identical from inside the page.
        pageLog.push(`[harness] 404 ${pathname} (looked in ${HARNESS_PUBLIC})`);
        return route.fulfill({ status: 404, body: 'not found' });
      }
      const extension = pathname.slice(pathname.lastIndexOf('.')).toLowerCase();
      return route.fulfill({
        contentType: CONTENT_TYPES[extension] ?? 'application/octet-stream',
        body,
      });
    });

    // ORDER IS LOAD-BEARING: `addInitScript` runs on document creation, so it
    // must be registered before the navigation that creates the document.
    await page.addInitScript(DETERMINISM_SCRIPT);
    await page.goto(`${HARNESS_ORIGIN}/`);
    await page.addScriptTag({ content: await captureBundle() });
    return { browser, page };
  })();
  return (await session).page;
}

/**
 * Run `body` inside the very page the captures happen in.
 *
 * For asserting things ABOUT the capture environment — its origin, whether an
 * asset URL resolves, whether the injected determinism actually took effect.
 * Those are exactly the properties that cannot be checked from a replica page:
 * a second page built "the same way" shares whatever assumption is wrong, so it
 * agrees with the harness and proves nothing. A dead `addInitScript` went
 * unnoticed here for precisely that reason.
 *
 * This is a test and diagnostic seam. Game code has no reason to call it.
 */
export async function evaluateInCapturePage<T>(
  body: (argument: string | null) => T | Promise<T>,
  argument: string | null,
): Promise<T> {
  const page = await harnessPage();
  // The body is serialised and re-parsed in the page, so it cannot close over
  // anything from this module — everything it needs arrives as `argument`.
  // Deliberately `string | null` rather than a generic: this is a diagnostic
  // seam, and a concrete argument type keeps it free of casts.
  return page.evaluate(body, argument);
}

/** The last `limit` lines the page logged, formatted for a failure message. */
export function pageDiagnostics(limit = 20): string {
  if (pageLog.length === 0) {
    return 'browser console: (silent)';
  }
  return ['browser console (last lines):', ...pageLog.slice(-limit).map((l) => `  ${l}`)].join(
    '\n',
  );
}

/** Shut the browser down. Call once, from an `afterAll`. */
export async function closeHarness(): Promise<void> {
  const open = session;
  session = null;
  if (open !== null) {
    await (await open).browser.close();
  }
}

/**
 * Render the simulation headlessly and capture one frame after `ticks`
 * simulation ticks.
 *
 * The simulation is advanced by whole ticks, exactly as the pure `sim` tests
 * do, so the rendered frame corresponds to an exactly known tick — there is no
 * "roughly one second in" ambiguity.
 */
export async function captureFrame(
  seed: Seed,
  ticks: number,
  inputs: readonly Intents[] = [],
  size: { width: number; height: number } = { width: VIEW_WIDTH, height: VIEW_HEIGHT },
): Promise<Frame> {
  const page = await harnessPage();
  const request: CaptureRequest = {
    seed: BigInt(seed).toString(),
    ticks,
    inputs,
    width: size.width,
    height: size.height,
  };

  // Move the virtual clock to the moment this tick happens, so a time-driven
  // view effect reads a DIFFERENT time in each filmed frame while staying a
  // pure function of the request. See DETERMINISM_SCRIPT.
  await page.evaluate(
    (ms: number) => {
      window.__nowMs = ms;
    },
    (ticks / TICK_HZ) * 1000,
  );

  // `capture()` is synchronous — it steps, renders and reads back inside one
  // call — so anything that resolves on a later task (an image decode, a
  // loader, a `fetch`) has to have finished BEFORE it runs. A view that loads
  // assets registers `window.__capturePreload` and warms its cache here; it is
  // awaited once per capture and is a no-op if unset.
  try {
    await page.evaluate(async () => {
      await window.__capturePreload?.();
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    throw new Error(`__capturePreload failed: ${message}\n${pageDiagnostics()}`, { cause: error });
  }

  let result: CaptureResult;
  try {
    result = await page.evaluate((payload: CaptureRequest): CaptureResult => {
      if (window.__capture === undefined) {
        throw new Error('capture bundle did not load');
      }
      return window.__capture(payload);
    }, request);
  } catch (error) {
    // Re-throw with what the PAGE saw. The bare evaluate error is usually the
    // symptom; the cause is in the browser console.
    const message = error instanceof Error ? error.message : String(error);
    throw new Error(
      `capture failed (seed=${String(seed)}, ticks=${ticks}, ${size.width}x${size.height}): ` +
        `${message}\n${pageDiagnostics()}`,
      { cause: error },
    );
  }

  if (result.tick !== ticks) {
    throw new Error(`expected ${ticks} ticks before capture, simulation reported ${result.tick}`);
  }
  const rgba = new Uint8Array(Buffer.from(result.rgba, 'base64'));
  const expected = size.width * size.height * 4;
  if (rgba.length !== expected) {
    throw new Error(
      `readback returned ${rgba.length} bytes, expected ${expected} ` +
        `(${size.width}x${size.height}x4)\n${pageDiagnostics()}`,
    );
  }
  return new Frame(size.width, size.height, rgba);
}

/** Which rasteriser produced the last capture. Printed by the render tests so a
 * surprising golden diff can be traced to a backend change. */
export async function adapterName(): Promise<string> {
  const page = await harnessPage();
  return (
    await page.evaluate((payload: CaptureRequest) => window.__capture!(payload), {
      seed: '0',
      ticks: 0,
      inputs: [],
      width: 16,
      height: 16,
    } satisfies CaptureRequest)
  ).adapter;
}
