/**
 * Headless, deterministic game simulation.
 *
 * This module MUST NOT import from `src/view`, from `three`, or from anything
 * that touches a canvas, a window, or an input device. It is the single source
 * of truth for game state and is fully testable under plain Node with no GPU.
 *
 * Determinism rules enforced here (see AGENTS.md for the why):
 * - one tick is one call to {@link step}; systems run in a fixed, declared order
 * - systems read intent ({@link PlayerIntent}), never keyboard state
 * - no wall-clock reads; time is {@link World.tick}
 * - order-sensitive iteration sorts on {@link Entity.id}, never on array order
 * - all arithmetic goes through the f32 helpers in `./vec2` (the compiler
 *   enforces this: {@link F32} is a branded type and `+` on two `F32`s widens
 *   back to plain `number`, which cannot be stored in a {@link Vec2})
 * - randomness comes from {@link SimRng}, which is part of snapshotted state
 */

import { type F32, type Vec2, ZERO, add, clampLengthMax, f32, neg, scale, vec2 } from './vec2.ts';

export {
  type F32,
  type Vec2,
  ZERO,
  add,
  clampLengthMax,
  f32,
  length,
  lengthSquared,
  neg,
  negate,
  scale,
  sub,
  vec2,
} from './vec2.ts';

/** Fixed simulation rate. A power of two so `1 / TICK_HZ` is exact in binary
 * floating point, which matters for reproducible accumulation. */
export const TICK_HZ = 64;
/** Duration of one tick in seconds. Exact in f32 (1/64). */
export const TICK_DT = f32(1 / TICK_HZ);

export const ARENA_HALF_WIDTH = 400;
export const ARENA_HALF_HEIGHT = 250;
export const PADDLE_HALF_HEIGHT = 50;
export const PADDLE_INSET = 370;
export const PADDLE_SPEED = 300;
export const BALL_RADIUS = 8;
export const BALL_START_SPEED = 250;
/** Multiplier applied to ball speed on every paddle hit. */
export const BALL_SPEEDUP = 1.05;
export const MAX_BALL_SPEED = 900;

// --------------------------------------------------------------------------
// Identity
// --------------------------------------------------------------------------

/**
 * Stable simulation identity.
 *
 * Array position is not identity: it changes when an entity is removed, and it
 * is not stable across machines. Never sort, serialise, or network on it. Sort
 * on this instead.
 */
export type SimId = number;

/** Which player a paddle belongs to. */
export type Side = 'left' | 'right';

export type EntityKind = 'paddle' | 'ball';

export interface Entity {
  readonly id: SimId;
  readonly kind: EntityKind;
  /** Present exactly when `kind === 'paddle'`. */
  readonly side?: Side;
  position: Vec2;
  velocity: Vec2;
}

// --------------------------------------------------------------------------
// Intent — the only way input enters the simulation
// --------------------------------------------------------------------------

/**
 * Per-player intent for the current tick.
 *
 * The simulation reads *this*, never `KeyboardEvent`/key state. Key state is
 * frame-scoped, not tick-scoped: a frame may contain 0, 1, or many fixed ticks,
 * so reading it directly drops or duplicates inputs. The client translates
 * devices into intent once per frame; a server would receive intent over the
 * wire. Both feed the same simulation.
 */
export interface PlayerIntent {
  readonly up: boolean;
  readonly down: boolean;
}

export const NO_INTENT: PlayerIntent = { up: false, down: false };

/** -1 down, 0 still, +1 up. Opposing inputs cancel. */
export function intentAxis(intent: PlayerIntent): number {
  return (intent.up ? 1 : 0) - (intent.down ? 1 : 0);
}

/** Intent for both players this tick. */
export interface Intents {
  readonly left: PlayerIntent;
  readonly right: PlayerIntent;
}

export const NO_INTENTS: Intents = { left: NO_INTENT, right: NO_INTENT };

// --------------------------------------------------------------------------
// Simulation state
// --------------------------------------------------------------------------

export interface Score {
  left: number;
  right: number;
}

/**
 * Presentation-facing events produced by a single tick. Cleared at the start of
 * every tick, so a reader sees exactly the events of the tick that just ran.
 *
 * Deliberately per-tick state rather than an event queue: a queue drained on
 * the render frame would drop or duplicate against a fixed tick rate.
 */
export interface TickEvents {
  paddleHits: Side[];
  wallBounces: number;
  scored: Side | null;
}

export type Seed = number | bigint;

/**
 * Deterministic PRNG (PCG-XSH-RR 64/32), seeded explicitly and carried in the
 * simulation state. Never use `Math.random` or `crypto.getRandomValues` in the
 * simulation: they would make replays and rollback impossible.
 *
 * The state is a `bigint` because the algorithm is defined on wrapping u64
 * arithmetic, which `number` cannot represent exactly.
 */
export class SimRng {
  private static readonly MUL = 6364136223846793005n;
  private static readonly INC = 1442695040888963407n;
  private static readonly MASK = (1n << 64n) - 1n;

  private state: bigint;

  private constructor(state: bigint) {
    this.state = state;
  }

  static fromSeed(seed: Seed): SimRng {
    const rng = new SimRng(0n);
    rng.nextU32();
    rng.state = (rng.state + (BigInt(seed) & SimRng.MASK)) & SimRng.MASK;
    rng.nextU32();
    return rng;
  }

  clone(): SimRng {
    return new SimRng(this.state);
  }

  nextU32(): number {
    const old = this.state;
    this.state = (old * SimRng.MUL + SimRng.INC) & SimRng.MASK;
    const xorshifted = Number((((old >> 18n) ^ old) >> 27n) & 0xffffffffn) >>> 0;
    const rot = Number((old >> 59n) & 31n);
    return ((xorshifted >>> rot) | (xorshifted << ((32 - rot) & 31))) >>> 0;
  }

  /** Uniform in [0, 1). */
  nextF32(): F32 {
    // 24 bits of mantissa, exactly representable, no rounding surprise.
    return f32((this.nextU32() >>> 8) / (1 << 24));
  }

  /** Uniform in [lo, hi). The way to place anything randomly in the arena. */
  rangeF32(lo: number, hi: number): F32 {
    return f32(lo + f32(this.nextF32() * f32(hi - lo)));
  }

  coinFlip(): boolean {
    return (this.nextU32() & 1) === 1;
  }
}

/** The whole simulation. Everything needed to reproduce the next tick. */
export interface World {
  tick: number;
  score: Score;
  intents: Intents;
  events: TickEvents;
  rng: SimRng;
  entities: Entity[];
}

/**
 * Deterministic initial world. Ids are assigned explicitly and never derived
 * from creation order.
 */
export function spawnWorld(seed: Seed): World {
  const rng = SimRng.fromSeed(seed);
  return {
    tick: 0,
    score: { left: 0, right: 0 },
    intents: NO_INTENTS,
    events: { paddleHits: [], wallBounces: 0, scored: null },
    rng,
    entities: [
      { id: 1, kind: 'paddle', side: 'left', position: vec2(-PADDLE_INSET, 0), velocity: ZERO },
      { id: 2, kind: 'paddle', side: 'right', position: vec2(PADDLE_INSET, 0), velocity: ZERO },
      { id: 3, kind: 'ball', position: ZERO, velocity: serveVelocity(rng) },
    ],
  };
}

function serveVelocity(rng: SimRng): Vec2 {
  const towardRight = rng.coinFlip();
  // Keep the serve away from near-vertical so rallies actually start.
  const angle = rng.rangeF32(-0.5, 0.5);
  const dir = vec2((towardRight ? 1 : -1) * Math.cos(angle), Math.sin(angle));
  return scale(dir, BALL_START_SPEED);
}

// --------------------------------------------------------------------------
// Schedule
// --------------------------------------------------------------------------

/**
 * Ordered stages of one simulation tick. A total order is the only ordering
 * guarantee worth having, and lockstep netcode needs one.
 */
export const SIM_STAGES = ['begin', 'intent', 'motion', 'collision', 'scoring'] as const;
export type SimStage = (typeof SIM_STAGES)[number];

export interface SimSystem {
  readonly stage: SimStage;
  readonly name: string;
  readonly run: (world: World) => void;
}

/**
 * The tick, as data. Systems run top to bottom, always, on every machine.
 *
 * Add new systems HERE with an explicit stage rather than calling them from
 * inside another system — the declared order is what `just test-sim` checks and
 * what makes the tick reviewable at a glance.
 */
export const SIM_PIPELINE: readonly SimSystem[] = [
  { stage: 'begin', name: 'beginTick', run: beginTick },
  { stage: 'intent', name: 'applyIntent', run: applyIntent },
  { stage: 'motion', name: 'integrateMotion', run: integrateMotion },
  { stage: 'collision', name: 'collideWalls', run: collideWalls },
  { stage: 'collision', name: 'collidePaddles', run: collidePaddles },
  { stage: 'scoring', name: 'scoreAndReset', run: scoreAndReset },
];

/** Advance the world by exactly one tick. The only way time passes. */
export function step(world: World, intents: Intents = NO_INTENTS): void {
  world.intents = intents;
  for (const system of SIM_PIPELINE) {
    system.run(world);
  }
}

/** Iteration order that does not depend on array layout or removal history. */
function bySimId(world: World, kind?: EntityKind): Entity[] {
  const chosen =
    kind === undefined ? [...world.entities] : world.entities.filter((e) => e.kind === kind);
  return chosen.sort((a, b) => a.id - b.id);
}

function beginTick(world: World): void {
  world.tick += 1;
  world.events = { paddleHits: [], wallBounces: 0, scored: null };
}

function applyIntent(world: World): void {
  for (const paddle of bySimId(world, 'paddle')) {
    const intent = paddle.side === 'left' ? world.intents.left : world.intents.right;
    paddle.velocity = vec2(0, intentAxis(intent) * PADDLE_SPEED);
  }
}

function integrateMotion(world: World): void {
  // Sorting on SimId makes iteration order independent of storage layout.
  // Integration is per-entity and order-independent today, but sorting keeps it
  // correct if someone later introduces coupling between entities.
  for (const entity of bySimId(world)) {
    entity.position = add(entity.position, scale(entity.velocity, TICK_DT));
  }
}

function collideWalls(world: World): void {
  for (const entity of bySimId(world)) {
    if (entity.kind === 'paddle') {
      // Paddles clamp against the arena and stop dead.
      const limit = f32(ARENA_HALF_HEIGHT - PADDLE_HALF_HEIGHT);
      if (entity.position.y > limit) {
        entity.position = vec2(entity.position.x, limit);
        entity.velocity = vec2(entity.velocity.x, 0);
      } else if (entity.position.y < neg(limit)) {
        entity.position = vec2(entity.position.x, neg(limit));
        entity.velocity = vec2(entity.velocity.x, 0);
      }
    } else if (entity.kind === 'ball') {
      const limit = f32(ARENA_HALF_HEIGHT - BALL_RADIUS);
      if (entity.position.y > limit) {
        entity.position = vec2(entity.position.x, f32(limit - f32(entity.position.y - limit)));
        entity.velocity = vec2(entity.velocity.x, neg(entity.velocity.y));
        world.events.wallBounces += 1;
      } else if (entity.position.y < neg(limit)) {
        entity.position = vec2(entity.position.x, f32(neg(limit) - f32(entity.position.y + limit)));
        entity.velocity = vec2(entity.velocity.x, neg(entity.velocity.y));
        world.events.wallBounces += 1;
      }
    }
  }
}

function collidePaddles(world: World): void {
  // Deterministic paddle order: without this, two paddles that could both claim
  // the ball on the same tick would resolve in storage order.
  const paddles = bySimId(world, 'paddle');

  for (const ball of bySimId(world, 'ball')) {
    for (const paddle of paddles) {
      const faceX =
        paddle.side === 'left'
          ? f32(paddle.position.x + BALL_RADIUS)
          : f32(paddle.position.x - BALL_RADIUS);
      const movingInto =
        paddle.side === 'left'
          ? ball.velocity.x < 0 && ball.position.x <= faceX
          : ball.velocity.x > 0 && ball.position.x >= faceX;
      const verticallyOverlapping =
        Math.abs(f32(ball.position.y - paddle.position.y)) <= f32(PADDLE_HALF_HEIGHT + BALL_RADIUS);

      if (movingInto && verticallyOverlapping) {
        ball.position = vec2(faceX, ball.position.y);
        // Deflection angle depends on where the ball struck the paddle.
        const offset = f32(f32(ball.position.y - paddle.position.y) / PADDLE_HALF_HEIGHT);
        const deflected = vec2(
          neg(ball.velocity.x),
          f32(ball.velocity.y + f32(f32(offset * BALL_START_SPEED) * 0.5)),
        );
        ball.velocity = clampLengthMax(scale(deflected, BALL_SPEEDUP), MAX_BALL_SPEED);
        world.events.paddleHits.push(paddle.side as Side);
        break;
      }
    }
  }
}

function scoreAndReset(world: World): void {
  for (const ball of bySimId(world, 'ball')) {
    let scorer: Side | null = null;
    if (ball.position.x > ARENA_HALF_WIDTH) {
      scorer = 'left';
    } else if (ball.position.x < -ARENA_HALF_WIDTH) {
      scorer = 'right';
    }

    if (scorer !== null) {
      world.score[scorer] += 1;
      world.events.scored = scorer;
      ball.position = ZERO;
      ball.velocity = serveVelocity(world.rng);
    }
  }
}

// --------------------------------------------------------------------------
// Fixed timestep — the bridge between real time and simulation time
// --------------------------------------------------------------------------

/**
 * Accumulator that converts variable frame deltas into whole ticks.
 *
 * The renderer owns one of these; the tests do not use it at all, because a
 * test that advances time by calling `step` directly is exactly reproducible
 * and a test that advances it by elapsed seconds is not.
 */
export class FixedClock {
  /** Never simulate more than this many ticks in one frame. Without a cap, a
   * long stall makes the next frame simulate for longer than the stall did, and
   * the game spirals. Dropped time is dropped, deliberately. */
  static readonly MAX_CATCHUP_TICKS = 8;

  private accumulator = 0;

  /** Run whole ticks for `deltaSeconds` of real time. Returns the count. */
  advance(world: World, deltaSeconds: number, intents: Intents = NO_INTENTS): number {
    this.accumulator += deltaSeconds;
    let ticks = 0;
    while (this.accumulator >= TICK_DT && ticks < FixedClock.MAX_CATCHUP_TICKS) {
      this.accumulator -= TICK_DT;
      step(world, intents);
      ticks += 1;
    }
    if (ticks === FixedClock.MAX_CATCHUP_TICKS) {
      this.accumulator = 0;
    }
    return ticks;
  }
}

// --------------------------------------------------------------------------
// State hashing — the backbone of replay and desync detection
// --------------------------------------------------------------------------

const FNV_OFFSET = 0xcbf29ce484222325n;
const FNV_PRIME = 0x00000100000001b3n;
const U64 = (1n << 64n) - 1n;

const bitsF32 = new Float32Array(1);
const bitsU32 = new Uint32Array(bitsF32.buffer);

/** The IEEE-754 bit pattern of a value as an f32. The equivalent of Rust's
 * `f32::to_bits`, and the reason simulation state is kept in f32. */
export function toBits(value: number): number {
  bitsF32[0] = value;
  return bitsU32[0]!;
}

/**
 * A whole-world checksum for a single tick.
 *
 * Floats are hashed via their bit pattern so the hash is exact rather than
 * tolerance-based: a replay either reproduces the run bit for bit or it does
 * not. Entities are visited in `SimId` order so the hash cannot depend on
 * storage layout.
 *
 * FNV-1a, chosen because it is trivially reimplementable in any language — a
 * server or a tool in another stack can verify the same hashes.
 */
export function stateHash(world: World): bigint {
  let hash = FNV_OFFSET;
  const feed = (value: bigint): void => {
    for (let byte = 0; byte < 8; byte += 1) {
      hash ^= (value >> BigInt(8 * byte)) & 0xffn;
      hash = (hash * FNV_PRIME) & U64;
    }
  };

  feed(BigInt(world.tick));
  feed(BigInt(world.score.left));
  feed(BigInt(world.score.right));

  for (const entity of bySimId(world)) {
    feed(BigInt(entity.id));
    feed(BigInt(toBits(entity.position.x)));
    feed(BigInt(toBits(entity.position.y)));
    feed(BigInt(toBits(entity.velocity.x)));
    feed(BigInt(toBits(entity.velocity.y)));
  }
  return hash;
}
