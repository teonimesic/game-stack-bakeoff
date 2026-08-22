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
  BALL_RADIUS,
  PADDLE_HALF_HEIGHT,
  type SimId,
  type World,
} from '../sim/index.ts';

export const VIEW_WIDTH = 640;
export const VIEW_HEIGHT = 400;

/** Linear 0..1 RGB, matching how the shader receives it. */
export type Rgb = readonly [number, number, number];

export const BALL_COLOR: Rgb = [1.0, 0.92, 0.3];
export const PADDLE_COLOR: Rgb = [0.35, 0.78, 1.0];
export const BACKGROUND_COLOR: Rgb = [0.04, 0.05, 0.09];

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

/** Drives a three.js scene from simulation state. */
export interface View {
  readonly scene: THREE.Scene;
  readonly camera: THREE.OrthographicCamera;
  /** Copy simulation state onto the scene graph. One way only. */
  sync(world: World): void;
  dispose(): void;
}

export function createView(): View {
  const scene = new THREE.Scene();
  const camera = arenaCamera();
  // Links a mesh back to the simulation entity it draws. The indirection is
  // what lets the simulation run with no view at all — which is exactly what
  // every test in `tests/sim` does.
  const meshes = new Map<SimId, THREE.Mesh>();

  const spawn = (world: World): void => {
    for (const entity of world.entities) {
      if (meshes.has(entity.id)) {
        continue;
      }
      const isBall = entity.kind === 'ball';
      const [width, height] = isBall
        ? [BALL_RADIUS * 2, BALL_RADIUS * 2]
        : [16, PADDLE_HALF_HEIGHT * 2];
      const mesh = new THREE.Mesh(
        new THREE.PlaneGeometry(width, height),
        new THREE.MeshBasicMaterial({
          color: new THREE.Color(...(isBall ? BALL_COLOR : PADDLE_COLOR)),
        }),
      );
      meshes.set(entity.id, mesh);
      scene.add(mesh);
    }
  };

  return {
    scene,
    camera,
    sync(world: World): void {
      spawn(world);
      for (const entity of world.entities) {
        const mesh = meshes.get(entity.id);
        if (mesh !== undefined) {
          mesh.position.set(entity.position.x, entity.position.y, 0);
        }
      }
    },
    dispose(): void {
      for (const mesh of meshes.values()) {
        mesh.geometry.dispose();
        (mesh.material as THREE.Material).dispose();
      }
      meshes.clear();
      scene.clear();
    },
  };
}
