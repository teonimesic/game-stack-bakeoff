/**
 * Presentation layer: turns simulation state into something you can see.
 *
 * Strict one-way data flow. This module reads `src/sim` and never writes to it.
 * Everything here is disposable; the simulation is the source of truth.
 */

import * as THREE from 'three';
import {
  ARENA_HALF_HEIGHT,
  ARENA_HALF_WIDTH,
  MARKER_HALF_SIZE,
  type SimId,
  type World,
} from '../sim/index.ts';

export const VIEW_WIDTH = 640;
export const VIEW_HEIGHT = 400;

/** Linear 0..1 RGB, matching how the shader receives it. */
export type Rgb = readonly [number, number, number];

export const MARKER_COLOR: Rgb = [1.0, 0.92, 0.3];
export const BACKGROUND_COLOR: Rgb = [0.04, 0.05, 0.09];
/** Deliberately far from `MARKER_COLOR` in blue, so a test can tell HUD ink
 * from gameplay ink by colour alone. */
export const HUD_COLOR: Rgb = [0.8, 0.94, 1.0];

/** The same colour as the renderer writes it: 0..255 per channel. */
export function toU8(color: Rgb): [number, number, number] {
  return [Math.round(color[0] * 255), Math.round(color[1] * 255), Math.round(color[2] * 255)];
}

/**
 * Colour management OFF, on purpose.
 *
 * three enables it by default (r152+), which converts material colours from
 * sRGB into a linear working space and back on output. That is right for a lit
 * scene and wrong here: it makes the exact byte value of a pixel a function of
 * three's internal transfer functions, so a pixel assertion in a test would be
 * asserting on three's colour pipeline rather than on our geometry. With it
 * off, a material colour of 0.35 lands on screen as `round(0.35 * 255) = 89`.
 */
export function configureColorPipeline(renderer: THREE.WebGLRenderer): void {
  THREE.ColorManagement.enabled = false;
  renderer.outputColorSpace = THREE.LinearSRGBColorSpace;
  renderer.setClearColor(new THREE.Color(...BACKGROUND_COLOR), 1);
}

/**
 * A camera that frames the whole arena.
 *
 * The half-extents come from the simulation, so the view cannot drift out of
 * sync with the arena the rules are enforced against.
 */
export function arenaCamera(): THREE.OrthographicCamera {
  const camera = new THREE.OrthographicCamera(
    -ARENA_HALF_WIDTH,
    ARENA_HALF_WIDTH,
    ARENA_HALF_HEIGHT,
    -ARENA_HALF_HEIGHT,
    0.1,
    1000,
  );
  camera.position.z = 100;
  return camera;
}

// --------------------------------------------------------------------------
// HUD — text, in the framebuffer
// --------------------------------------------------------------------------

/**
 * THE HUD IS GEOMETRY, NOT DOM.
 *
 * Everything the player is meant to see has to go through the renderer, because
 * that is the only thing `just film` and `tests/render` can see: they read the
 * pixels of an offscreen render target, not the page. A `<div>` over the canvas
 * looks right in `just run` and is invisible to every automated check you have.
 *
 * So the HUD is a second, screen-space scene: an orthographic camera in PIXEL
 * units, and one textured quad whose texture is a 2D canvas we rasterise text
 * into. `renderFrame` draws it after the arena with `autoClear = false`.
 *
 * The font is a 5x7 bitmap drawn with `fillRect`, not `fillText`, on purpose:
 * `fillText` depends on which fonts the host has installed and on the
 * platform's glyph hinting, so the same tick would produce different pixels on
 * a laptop and in CI, and the golden test would be a coin flip. These glyphs
 * are the same bytes everywhere.
 */
const GLYPH_WIDTH = 5;
const GLYPH_HEIGHT = 7;
/** Texture texels per glyph pixel. The quad is drawn 1:1, so this is also the
 * on-screen size of one glyph pixel. */
const GLYPH_SCALE = 2;
/** Padding inside the HUD texture, in screen pixels. */
const HUD_PADDING = 4;
/** Widest line the HUD reserves room for; longer lines are clipped. */
const HUD_COLUMNS = 13;
const HUD_LINES = 2;
const ADVANCE_X = (GLYPH_WIDTH + 1) * GLYPH_SCALE;
const ADVANCE_Y = (GLYPH_HEIGHT + 3) * GLYPH_SCALE;

/**
 * Where the HUD lands in a captured frame: top-left origin, y growing DOWNWARD,
 * same coordinates as {@link Frame.pixel}. Tests assert on this box.
 */
export const HUD_REGION = {
  x: 8,
  y: 8,
  width: HUD_PADDING * 2 + HUD_COLUMNS * ADVANCE_X,
  height: HUD_PADDING * 2 + HUD_LINES * ADVANCE_Y,
} as const;

/**
 * 5x7 glyphs, one row of the bitmap per space-separated group, MSB left.
 *
 * Add characters here rather than reaching for a font file — the whole point is
 * that the rasterisation has no host dependency.
 */
const GLYPH_BITMAPS: Readonly<Record<string, string>> = {
  ' ': '00000 00000 00000 00000 00000 00000 00000',
  '-': '00000 00000 00000 11111 00000 00000 00000',
  '+': '00000 00100 00100 11111 00100 00100 00000',
  '.': '00000 00000 00000 00000 00000 01100 01100',
  ':': '00000 01100 01100 00000 01100 01100 00000',
  ',': '00000 00000 00000 00000 01100 00100 01000',
  '/': '00001 00010 00010 00100 01000 01000 10000',
  '%': '11000 11001 00010 00100 01000 10011 00011',
  '0': '01110 10001 10011 10101 11001 10001 01110',
  '1': '00100 01100 00100 00100 00100 00100 01110',
  '2': '01110 10001 00001 00010 00100 01000 11111',
  '3': '11111 00010 00100 00010 00001 10001 01110',
  '4': '00010 00110 01010 10010 11111 00010 00010',
  '5': '11111 10000 11110 00001 00001 10001 01110',
  '6': '00110 01000 10000 11110 10001 10001 01110',
  '7': '11111 00001 00010 00100 01000 01000 01000',
  '8': '01110 10001 10001 01110 10001 10001 01110',
  '9': '01110 10001 10001 01111 00001 00010 01100',
  A: '01110 10001 10001 11111 10001 10001 10001',
  B: '11110 10001 10001 11110 10001 10001 11110',
  C: '01110 10001 10000 10000 10000 10001 01110',
  D: '11100 10010 10001 10001 10001 10010 11100',
  E: '11111 10000 10000 11110 10000 10000 11111',
  F: '11111 10000 10000 11110 10000 10000 10000',
  G: '01110 10001 10000 10111 10001 10001 01111',
  H: '10001 10001 10001 11111 10001 10001 10001',
  I: '01110 00100 00100 00100 00100 00100 01110',
  J: '00111 00010 00010 00010 00010 10010 01100',
  K: '10001 10010 10100 11000 10100 10010 10001',
  L: '10000 10000 10000 10000 10000 10000 11111',
  M: '10001 11011 10101 10101 10001 10001 10001',
  N: '10001 11001 10101 10011 10001 10001 10001',
  O: '01110 10001 10001 10001 10001 10001 01110',
  P: '11110 10001 10001 11110 10000 10000 10000',
  Q: '01110 10001 10001 10001 10101 10010 01101',
  R: '11110 10001 10001 11110 10100 10010 10001',
  S: '01111 10000 10000 01110 00001 00001 11110',
  T: '11111 00100 00100 00100 00100 00100 00100',
  U: '10001 10001 10001 10001 10001 10001 01110',
  V: '10001 10001 10001 10001 10001 01010 00100',
  W: '10001 10001 10001 10101 10101 11011 10001',
  X: '10001 10001 01010 00100 01010 10001 10001',
  Y: '10001 10001 01010 00100 00100 00100 00100',
  Z: '11111 00001 00010 00100 01000 10000 11111',
};

/** A character with no glyph draws a filled box, so it is obvious on screen
 * rather than silently missing. */
const MISSING_GLYPH = '11111 10001 10001 10001 10001 10001 11111';

const FONT = new Map<string, readonly string[]>(
  Object.entries(GLYPH_BITMAPS).map(([character, bitmap]) => [character, bitmap.split(' ')]),
);
const MISSING_ROWS = MISSING_GLYPH.split(' ');

/** The screen-space overlay: its own scene, its own camera, its own texture. */
interface Hud {
  readonly scene: THREE.Scene;
  readonly camera: THREE.OrthographicCamera;
  /** Rasterise `lines` into the HUD texture. Uploads only when the text
   * changed, so a static HUD costs nothing per frame. */
  draw(lines: readonly string[]): void;
  dispose(): void;
}

function createHud(width: number, height: number): Hud {
  const canvas = document.createElement('canvas');
  canvas.width = HUD_REGION.width;
  canvas.height = HUD_REGION.height;
  const context = canvas.getContext('2d');
  if (context === null) {
    throw new Error('HUD: the browser gave no 2D context for the overlay texture');
  }

  const texture = new THREE.CanvasTexture(canvas);
  // Nearest filtering and a 1:1 quad keep every glyph pixel an exact texel: no
  // interpolation, no mipmap selection, so the bytes are reproducible.
  texture.magFilter = THREE.NearestFilter;
  texture.minFilter = THREE.NearestFilter;
  texture.generateMipmaps = false;
  // No transfer-function decode, matching `configureColorPipeline`.
  texture.colorSpace = THREE.LinearSRGBColorSpace;

  const material = new THREE.MeshBasicMaterial({
    map: texture,
    color: new THREE.Color(...HUD_COLOR),
    transparent: true,
    // The overlay pass does not clear, so the arena's depth buffer is still
    // there. The HUD is always on top of it.
    depthTest: false,
    depthWrite: false,
  });
  const mesh = new THREE.Mesh(
    new THREE.PlaneGeometry(HUD_REGION.width, HUD_REGION.height),
    material,
  );
  // Pixel coordinates with y UP (that is what the camera below defines), so the
  // top-left corner of the HUD box sits at `height - HUD_REGION.y`.
  mesh.position.set(
    HUD_REGION.x + HUD_REGION.width / 2,
    height - (HUD_REGION.y + HUD_REGION.height / 2),
    0,
  );

  const scene = new THREE.Scene();
  scene.add(mesh);

  const camera = new THREE.OrthographicCamera(0, width, height, 0, -1, 1);

  let drawn: string | null = null;

  return {
    scene,
    camera,
    draw(lines: readonly string[]): void {
      const text = lines.join('\n');
      if (text === drawn) {
        return;
      }
      drawn = text;
      context.clearRect(0, 0, canvas.width, canvas.height);
      // White texels, tinted by `material.color`: one place to change the HUD
      // colour, and the texture stays a pure mask.
      context.fillStyle = '#ffffff';
      for (const [line, characters] of lines.entries()) {
        for (const [column, character] of [...characters].entries()) {
          const rows = FONT.get(character.toUpperCase()) ?? MISSING_ROWS;
          const originX = HUD_PADDING + column * ADVANCE_X;
          const originY = HUD_PADDING + line * ADVANCE_Y;
          for (const [row, bits] of rows.entries()) {
            for (let bit = 0; bit < GLYPH_WIDTH; bit += 1) {
              if (bits[bit] === '1') {
                context.fillRect(
                  originX + bit * GLYPH_SCALE,
                  originY + row * GLYPH_SCALE,
                  GLYPH_SCALE,
                  GLYPH_SCALE,
                );
              }
            }
          }
        }
      }
      texture.needsUpdate = true;
    },
    dispose(): void {
      mesh.geometry.dispose();
      material.dispose();
      texture.dispose();
      scene.clear();
    },
  };
}

/** Signed, zero-padded, locale-free. `(-0.4)` formats as `+000`, not `-000`. */
function hudNumber(value: number, digits: number): string {
  const rounded = Math.round(value);
  return (rounded < 0 ? '-' : '+') + String(Math.abs(rounded)).padStart(digits, '0');
}

/**
 * What the HUD says. Tick number and marker position — the two things you need
 * in order to match a filmed frame against a `just probe` trace line.
 *
 * Replace the content when you replace the placeholder; keep the shape: plain
 * strings, derived only from `World`, with no clock and no locale formatting.
 */
function hudLines(world: World): readonly string[] {
  const marker = world.entities
    .filter((entity) => entity.kind === 'marker')
    .sort((a, b) => a.id - b.id)[0];
  return [
    `TICK ${String(world.tick).padStart(5, '0')}`,
    marker === undefined
      ? 'POS ---- ----'
      : `POS ${hudNumber(marker.position.x, 3)} ${hudNumber(marker.position.y, 3)}`,
  ];
}

// --------------------------------------------------------------------------
// The view
// --------------------------------------------------------------------------

/** Drives a three.js scene from simulation state. */
export interface View {
  readonly scene: THREE.Scene;
  readonly camera: THREE.OrthographicCamera;
  /** The HUD: a screen-space scene drawn on top of `scene` by
   * {@link renderFrame}. Rendered, not DOM — see {@link HUD_REGION}. */
  readonly overlayScene: THREE.Scene;
  readonly overlayCamera: THREE.OrthographicCamera;
  /** Copy simulation state onto the scene graph. One way only. */
  sync(world: World): void;
  dispose(): void;
}

/**
 * Draw one frame: the arena, then the HUD on top of it.
 *
 * Both the window (`src/view/main.ts`) and the offscreen capture
 * (`src/view/capture.ts`) call THIS, so what you film is what you play. Add a
 * pass here, never in only one of them.
 */
export function renderFrame(renderer: THREE.WebGLRenderer, view: View): void {
  renderer.autoClear = true;
  renderer.render(view.scene, view.camera);
  // Keep the arena that was just drawn; the HUD is composited over it.
  renderer.autoClear = false;
  renderer.render(view.overlayScene, view.overlayCamera);
  renderer.autoClear = true;
}

export function createView(
  size: { width: number; height: number } = { width: VIEW_WIDTH, height: VIEW_HEIGHT },
): View {
  const scene = new THREE.Scene();
  const camera = arenaCamera();
  const hud = createHud(size.width, size.height);
  // Links a mesh back to the simulation entity it draws. The indirection is
  // what lets the simulation run with no view at all — which is exactly what
  // every test in `tests/sim` does.
  const meshes = new Map<SimId, THREE.Mesh>();

  const spawn = (world: World): void => {
    for (const entity of world.entities) {
      if (meshes.has(entity.id)) {
        continue;
      }
      const side = MARKER_HALF_SIZE * 2;
      const mesh = new THREE.Mesh(
        new THREE.PlaneGeometry(side, side),
        new THREE.MeshBasicMaterial({ color: new THREE.Color(...MARKER_COLOR) }),
      );
      meshes.set(entity.id, mesh);
      scene.add(mesh);
    }
  };

  return {
    scene,
    camera,
    overlayScene: hud.scene,
    overlayCamera: hud.camera,
    sync(world: World): void {
      spawn(world);
      for (const entity of world.entities) {
        const mesh = meshes.get(entity.id);
        if (mesh !== undefined) {
          mesh.position.set(entity.position.x, entity.position.y, 0);
        }
      }
      hud.draw(hudLines(world));
    },
    dispose(): void {
      for (const mesh of meshes.values()) {
        mesh.geometry.dispose();
        (mesh.material as THREE.Material).dispose();
      }
      meshes.clear();
      scene.clear();
      hud.dispose();
    },
  };
}
