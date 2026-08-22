/**
 * Minimal f32 2-vector. The simulation's only arithmetic vocabulary.
 *
 * WHY f32 AND NOT PLAIN `number`: a JS `number` is f64. Every operation here
 * rounds its result to f32 with `Math.fround`, which makes the state exactly
 * representable in 32 bits — `stateHash` can then hash bit patterns rather than
 * approximate values, and the hash of a run is comparable with the same run in
 * any other f32 implementation of these rules.
 *
 * Double rounding (compute in f64, round to f32) is provably identical to
 * computing directly in f32 for +, -, *, / and sqrt, because f64 carries more
 * than 2p+2 = 50 bits of mantissa. So these helpers are not an approximation of
 * f32 arithmetic; they are f32 arithmetic.
 *
 * WHY THE BRAND: `F32` is a nominal (branded) subtype of `number`. `+`, `-`,
 * `*` and `/` on two `F32`s widen back to plain `number`, and plain `number` is
 * NOT assignable to `F32`. So the compiler rejects
 *
 *     entity.position = { x: a.x + b.x, y: a.y };   // Type error
 *
 * and accepts only values that went through `f32()`. The only way to produce an
 * `F32` is `f32()`, which rounds. This closes the gap Rust gets for free from
 * `f32` being a distinct type.
 *
 * WHAT THE BRAND DOES NOT CATCH: `f32(a * b + c * d)` type-checks but is one
 * rounding, not three. Round every intermediate — `f32(f32(a * b) + f32(c * d))`
 * — whenever the result is stored in the world or fed to `stateHash`.
 */

declare const F32_BRAND: unique symbol;

/**
 * A `number` that is known to be exactly representable as an IEEE-754 binary32.
 * Produced only by {@link f32}.
 */
export type F32 = number & { readonly [F32_BRAND]: 'f32' };

/** Round an f64 to the nearest f32. The only way to make an {@link F32}. */
export function f32(value: number): F32 {
  return Math.fround(value) as F32;
}

export interface Vec2 {
  readonly x: F32;
  readonly y: F32;
}

export function vec2(x: number, y: number): Vec2 {
  return { x: f32(x), y: f32(y) };
}

export const ZERO: Vec2 = vec2(0, 0);

export function add(a: Vec2, b: Vec2): Vec2 {
  return { x: f32(a.x + b.x), y: f32(a.y + b.y) };
}

export function sub(a: Vec2, b: Vec2): Vec2 {
  return { x: f32(a.x - b.x), y: f32(a.y - b.y) };
}

/**
 * Negate a scalar. Use this instead of `-x` on simulation state.
 *
 * The cast is the one real ergonomic cost of the brand:
 * `@typescript-eslint/no-unsafe-unary-minus` does not see through an
 * intersection type, so `-someF32` is reported as unsafe. Widening to `number`
 * for the negation is value-preserving — including the sign of zero, which
 * `0 - x` would NOT preserve and which `stateHash` can see.
 */
export function neg(a: F32): F32 {
  return f32(-(a as number));
}

export function negate(a: Vec2): Vec2 {
  return { x: neg(a.x), y: neg(a.y) };
}

export function scale(a: Vec2, scalar: number): Vec2 {
  const s = f32(scalar);
  return { x: f32(a.x * s), y: f32(a.y * s) };
}

export function lengthSquared(a: Vec2): F32 {
  return f32(f32(a.x * a.x) + f32(a.y * a.y));
}

export function length(a: Vec2): F32 {
  return f32(Math.sqrt(lengthSquared(a)));
}

/**
 * Shorten `a` to at most `max`, leaving direction untouched. Ported operation
 * for operation from `glam::Vec2::clamp_length_max`, including the order of the
 * divide and the multiply — a different order rounds differently.
 */
export function clampLengthMax(a: Vec2, max: number): Vec2 {
  const lengthSq = lengthSquared(a);
  if (lengthSq > f32(max * max)) {
    const norm = f32(Math.sqrt(lengthSq));
    return { x: f32(max * f32(a.x / norm)), y: f32(max * f32(a.y / norm)) };
  }
  return a;
}

/**
 * Rescale `a` to exactly `len`, leaving its direction untouched — a clamp that
 * binds from both sides rather than only from above.
 *
 * Same divide-then-multiply order as {@link clampLengthMax}, because a
 * different order rounds differently and the hash can see it. A zero vector has
 * no direction, so it is returned unchanged.
 */
export function withLength(a: Vec2, len: number): Vec2 {
  const norm = length(a);
  if (norm === 0) {
    return a;
  }
  return { x: f32(len * f32(a.x / norm)), y: f32(len * f32(a.y / norm)) };
}
