/**
 * The game, with a window. `just run`.
 *
 * The only place that touches input devices. Key state is read once per frame
 * and turned into intent; the simulation never sees a `KeyboardEvent`.
 */

import * as THREE from 'three';
import { FixedClock, type Intents, spawnWorld } from '../sim/index.ts';
import {
  VIEW_HEIGHT,
  VIEW_WIDTH,
  configureColorPipeline,
  createView,
  renderFrame,
} from './index.ts';

const canvas = document.querySelector<HTMLCanvasElement>('#game');
if (canvas === null) {
  throw new Error('no #game canvas in the page');
}

const renderer = new THREE.WebGLRenderer({ canvas, antialias: false });
renderer.setPixelRatio(1);
renderer.setSize(VIEW_WIDTH, VIEW_HEIGHT, false);
configureColorPipeline(renderer);

const view = createView({ width: VIEW_WIDTH, height: VIEW_HEIGHT });
// The seed is read from the wall clock exactly once, here, outside the
// simulation. Everything downstream of it is a pure function of the seed.
const world = spawnWorld(BigInt(Date.now()));
const clock = new FixedClock();

const pressed = new Set<string>();
window.addEventListener('keydown', (event) => pressed.add(event.code));
window.addEventListener('keyup', (event) => pressed.delete(event.code));

function readIntents(): Intents {
  return {
    nudgeUp: pressed.has('ArrowUp') || pressed.has('KeyW'),
    nudgeDown: pressed.has('ArrowDown') || pressed.has('KeyS'),
  };
}

let previous = performance.now();
renderer.setAnimationLoop((now) => {
  const delta = Math.min((now - previous) / 1000, 0.25);
  previous = now;
  clock.advance(world, delta, readIntents());
  view.sync(world);
  // Arena + HUD, through the renderer — the same call `capture.ts` makes, so
  // the window and a filmed frame show the same thing.
  renderFrame(renderer, view);
});
