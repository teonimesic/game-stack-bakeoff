/**
 * Headless, deterministic game simulation.
 *
 * This module MUST NOT import from `src/view`, from `three`, or from anything
 * that touches a canvas, a window, or an input device. It is the single source
 * of truth for game state and is fully testable under plain Node with no GPU.
 *
 * WHAT IS HERE TODAY IS A PLACEHOLDER, NOT A GAME. One entity, a {@link Marker},
 * drifts around the arena and reflects off the edges. It exists so the harness
 * has something to assert on. Replace it with the real rules; keep the shape.
 *
 * Determinism rules enforced here (see AGENTS.md for the why):
 * - one tick is one call to {@link step}; systems run in a fixed, declared order
 * - systems read intent ({@link Intents}), never keyboard state
 * - no wall-clock reads; time is {@link World.tick}
 * - order-sensitive iteration sorts on {@link Entity.id}, never on array order
 * - all arithmetic goes through the f32 helpers in `./vec2` (the compiler
 *   enforces this: {@link F32} is a branded type and `+` on two `F32`s widens
 *   back to plain `number`, which cannot be stored in a {@link Vec2})
 * - randomness comes from {@link SimRng}, which is part of snapshotted state
 */

import { type F32, type Vec2, ZERO, add, f32, neg, scale, vec2, withLength } from './vec2.ts';

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
  withLength,
} from './vec2.ts';

/** Fixed simulation rate. A power of two so `1 / TICK_HZ` is exact in binary
 * floating point, which matters for reproducible accumulation. */
export const TICK_HZ = 64;
/** Duration of one tick in seconds. Exact in f32 (1/64). */
export const TICK_DT = f32(1 / TICK_HZ);

export const ARENA_HALF_WIDTH = 400;
export const ARENA_HALF_HEIGHT = 250;
/** Half the side length of the marker quad, in world units. */
export const MARKER_HALF_SIZE = 12;
/** The marker's constant speed, in world units per second. */
export const MARKER_SPEED = 220;
/** How hard one tick of input pushes the marker, in world units per second. */
export const NUDGE_SPEED = 300;

/** `NUDGE_SPEED` for the duration of one tick. Exact in f32 (300 / 64). */
const NUDGE_PER_TICK = f32(NUDGE_SPEED * TICK_DT);

// --------------------------------------------------------------------------
// Identity
// --------------------------------------------------------------------------

/**
 * Stable simulation identity.
 *
 * Array position is not identity: it changes when an entity is removed, and it
 * is not stable across machines. Never sort, serialise, or transmit on it. Sort
 * on this instead.
 */
export type SimId = number;

export type EntityKind = 'marker';

export interface Entity {
  readonly id: SimId;
  readonly kind: EntityKind;
  position: Vec2;
  velocity: Vec2;
}

// --------------------------------------------------------------------------
// Intent — the only way input enters the simulation
// --------------------------------------------------------------------------

/**
 * Input for the current tick.
 *
 * The simulation reads *this*, never `KeyboardEvent`/key state. Key state is
 * frame-scoped, not tick-scoped: a frame may contain 0, 1, or many fixed ticks,
 * so reading it directly drops or duplicates inputs. The client translates
 * devices into intent once per frame; a host process would receive intent over
 * the wire. Both feed the same simulation.
 */
export interface Intents {
  readonly nudgeUp: boolean;
  readonly nudgeDown: boolean;
}

export const NO_INTENTS: Intents = { nudgeUp: false, nudgeDown: false };

/** -1 down, 0 still, +1 up. Opposing inputs cancel. */
export function intentAxis(intents: Intents): number {
  return (intents.nudgeUp ? 1 : 0) - (intents.nudgeDown ? 1 : 0);
}

// --------------------------------------------------------------------------
// Simulation state
// --------------------------------------------------------------------------

/**
 * Presentation-facing events produced by a single tick. Cleared at the start of
 * every tick, so a reader sees exactly the events of the tick that just ran.
 *
 * Deliberately per-tick state rather than an event queue: a queue drained on
 * the render frame would drop or duplicate against a fixed tick rate.
 *
 * `events` is the flat, machine-readable projection of the same information —
 * one string per thing that happened, in the order it happened. Tools outside
 * the process (the probe in `scripts/`) read that list, so keep pushing to it
 * whenever you add a structured field.
 */
export interface TickEvents {
  /** Reflections off the arena edge this tick. */
  bounces: number;
  /** Flat list of the same events, one entry each. */
  events: string[];
}

function emptyEvents(): TickEvents {
  return { bounces: 0, events: [] };
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
    intents: NO_INTENTS,
    events: emptyEvents(),
    rng,
    entities: [{ id: 1, kind: 'marker', position: ZERO, velocity: launchVelocity(rng) }],
  };
}

/**
 * A direction drawn from the seeded RNG, at exactly {@link MARKER_SPEED}.
 *
 * Two RNG draws, in this order: a coin flip for the horizontal sign, then a
 * small angle offset. Keep the call *sequence* stable when you change this —
 * reordering the draws changes every run at every seed.
 */
function launchVelocity(rng: SimRng): Vec2 {
  const towardRight = rng.coinFlip();
  // Keep the launch away from vertical so the run is not degenerate.
  const angle = rng.rangeF32(-0.5, 0.5);
  const direction = vec2((towardRight ? 1 : -1) * Math.cos(angle), Math.sin(angle));
  return scale(direction, MARKER_SPEED);
}

// --------------------------------------------------------------------------
// Schedule
// --------------------------------------------------------------------------

/**
 * Ordered stages of one simulation tick. A total order is the only ordering
 * guarantee worth having, and lockstep simulation needs one.
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
  { stage: 'collision', name: 'collideBounds', run: collideBounds },
  { stage: 'scoring', name: 'resolveOutcome', run: resolveOutcome },
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
  world.events = emptyEvents();
}

function applyIntent(world: World): void {
  const axis = intentAxis(world.intents);
  if (axis === 0) {
    // Nothing pressed, or both directions pressed and cancelling. Leave the
    // velocity byte-identical rather than rescaling it to the same magnitude.
    return;
  }
  for (const marker of bySimId(world, 'marker')) {
    const nudged = vec2(marker.velocity.x, f32(marker.velocity.y + f32(axis * NUDGE_PER_TICK)));
    // Speed is an invariant of the placeholder: input steers, it never
    // accelerates or brakes. Rescaling pins the magnitude at MARKER_SPEED.
    marker.velocity = withLength(nudged, MARKER_SPEED);
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

/**
 * Reflect off the arena edge and stay fully inside it.
 *
 * The mirror (`limit - (position - limit)`) preserves the overshoot instead of
 * snapping to the wall, so a reflection does not depend on how much of the tick
 * was left when it happened. The clamp afterwards is the backstop for a speed
 * high enough to cross the whole arena in one tick.
 */
function collideBounds(world: World): void {
  const xLimit = f32(ARENA_HALF_WIDTH - MARKER_HALF_SIZE);
  const yLimit = f32(ARENA_HALF_HEIGHT - MARKER_HALF_SIZE);

  for (const entity of bySimId(world)) {
    let x = entity.position.x;
    let y = entity.position.y;
    let vx = entity.velocity.x;
    let vy = entity.velocity.y;
    let bounces = 0;

    if (x > xLimit) {
      x = f32(xLimit - f32(x - xLimit));
      vx = neg(vx);
      bounces += 1;
    } else if (x < neg(xLimit)) {
      x = f32(neg(xLimit) - f32(x + xLimit));
      vx = neg(vx);
      bounces += 1;
    }

    if (y > yLimit) {
      y = f32(yLimit - f32(y - yLimit));
      vy = neg(vy);
      bounces += 1;
    } else if (y < neg(yLimit)) {
      y = f32(neg(yLimit) - f32(y + yLimit));
      vy = neg(vy);
      bounces += 1;
    }

    entity.position = vec2(clampAxis(x, xLimit), clampAxis(y, yLimit));
    entity.velocity = vec2(vx, vy);

    for (let i = 0; i < bounces; i += 1) {
      world.events.bounces += 1;
      world.events.events.push('bounce');
    }
  }
}

/** Keep a coordinate inside `[-limit, limit]` without changing its precision. */
function clampAxis(value: F32, limit: F32): F32 {
  if (value > limit) {
    return limit;
  }
  if (value < neg(limit)) {
    return neg(limit);
  }
  return value;
}

/**
 * The `scoring` stage.
 *
 * INTENTIONALLY EMPTY IN THE STARTER. The pipeline shape is part of the
 * harness, so the stage stays declared and wired even though the placeholder
 * has nothing to resolve. Win/lose conditions, round resets and progression
 * belong here, after motion and collision have settled.
 */
function resolveOutcome(): void {
  // Deliberately no body. See the doc comment above.
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
 * host process or a tool in another stack can verify the same hashes.
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

  for (const entity of bySimId(world)) {
    feed(BigInt(entity.id));
    feed(BigInt(toBits(entity.position.x)));
    feed(BigInt(toBits(entity.position.y)));
    feed(BigInt(toBits(entity.velocity.x)));
    feed(BigInt(toBits(entity.velocity.y)));
  }
  return hash;
}
