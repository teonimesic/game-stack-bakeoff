/**
 * Browser half of the headless render harness.
 *
 * Runs the real simulation and the real renderer inside headless Chromium,
 * draws into an offscreen framebuffer, and reads the pixels back to the CPU.
 * Shaders run, the camera projects, quads rasterise: this is a genuine GPU
 * path (ANGLE → SwiftShader on a CI box, ANGLE → Metal/D3D/Vulkan on a
 * workstation), not a mock and not a 2D canvas.
 *
 * The node half is `src/view/harness.ts`, which bundles this file, injects it,
 * and calls `window.__capture`.
 */

import * as THREE from 'three';
import { type Intents, NO_INTENTS, step } from '../sim/index.ts';
import { headlessWorld } from '../sim/replay.ts';
import { VIEW_HEIGHT, VIEW_WIDTH, configureColorPipeline, createView } from './index.ts';

export interface CaptureRequest {
  /** Decimal string: the seed is a u64 and does not fit in a `number`. */
  readonly seed: string;
  readonly ticks: number;
  readonly inputs: readonly Intents[];
  readonly width?: number;
  readonly height?: number;
}

export interface CaptureResult {
  readonly tick: number;
  readonly adapter: string;
  readonly width: number;
  readonly height: number;
  /** Base64 RGBA8, top-left origin, `width * height * 4` bytes. */
  readonly rgba: string;
}

export function capture(request: CaptureRequest): CaptureResult {
  const width = request.width ?? VIEW_WIDTH;
  const height = request.height ?? VIEW_HEIGHT;

  const canvas = document.createElement('canvas');
  canvas.width = width;
  canvas.height = height;
  const context = canvas.getContext('webgl2', { antialias: false, depth: true });
  if (context === null) {
    throw new Error('no adapter: WebGL2 is unavailable in this browser');
  }

  const renderer = new THREE.WebGLRenderer({ canvas, context, antialias: false });
  renderer.setPixelRatio(1);
  renderer.setSize(width, height, false);
  configureColorPipeline(renderer);

  const view = createView();
  const world = headlessWorld(BigInt(request.seed));
  for (let tick = 0; tick < request.ticks; tick += 1) {
    step(world, request.inputs[tick] ?? NO_INTENTS);
  }
  view.sync(world);

  // Render into an offscreen target rather than the visible canvas: readback
  // from a render target is defined without `preserveDrawingBuffer`, and it
  // mirrors how the game would render for a post-process chain.
  const target = new THREE.WebGLRenderTarget(width, height, {
    colorSpace: THREE.LinearSRGBColorSpace,
    depthBuffer: true,
  });
  renderer.setRenderTarget(target);
  renderer.render(view.scene, view.camera);

  const pixels = new Uint8Array(width * height * 4);
  renderer.readRenderTargetPixels(target, 0, 0, width, height, pixels);

  const debug = context.getExtension('WEBGL_debug_renderer_info');
  const adapter = String(
    debug === null
      ? context.getParameter(context.RENDERER)
      : context.getParameter(debug.UNMASKED_RENDERER_WEBGL),
  );

  target.dispose();
  view.dispose();
  renderer.dispose();
  renderer.forceContextLoss();

  return {
    tick: world.tick,
    adapter,
    width,
    height,
    rgba: encode(flipVertically(pixels, width, height)),
  };
}

/** GL reads bottom-up; every test and every PNG here is top-down. */
function flipVertically(pixels: Uint8Array, width: number, height: number): Uint8Array {
  const stride = width * 4;
  const flipped = new Uint8Array(pixels.length);
  for (let y = 0; y < height; y += 1) {
    flipped.set(pixels.subarray((height - 1 - y) * stride, (height - y) * stride), y * stride);
  }
  return flipped;
}

function encode(bytes: Uint8Array): string {
  let binary = '';
  const CHUNK = 0x8000;
  for (let offset = 0; offset < bytes.length; offset += CHUNK) {
    binary += String.fromCharCode(...bytes.subarray(offset, offset + CHUNK));
  }
  return btoa(binary);
}

declare global {
  interface Window {
    __capture?: (request: CaptureRequest) => CaptureResult;
  }
}

window.__capture = capture;
