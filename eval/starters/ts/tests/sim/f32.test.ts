/**
 * The f32 guarantee.
 *
 * `stateHash` hashes IEEE-754 binary32 bit patterns, so a replay reproduces a
 * run bit for bit or it does not. That only works if every number in the world
 * really is an f32. In Rust the type system gives this for free. Here it comes
 * from `F32`, a branded subtype of `number` whose only producer is `f32()`.
 *
 * The `@ts-expect-error` lines below are the load-bearing part of this file and
 * they are checked by `tsc`, not by vitest: if the brand were ever weakened to
 * `type F32 = number`, those lines would stop erroring and `tsc` would fail with
 * "Unused '@ts-expect-error' directive". They are a compile-time assertion that
 * the guard is still armed.
 */

import { expect, test } from 'vitest';
import {
  type F32,
  type Vec2,
  add,
  clampLengthMax,
  f32,
  length,
  neg,
  scale,
  vec2,
  withLength,
} from '../../src/sim/vec2.ts';

test('unrounded f64 arithmetic cannot be stored in a Vec2', () => {
  const a = vec2(0.1, 0.2);
  const b = vec2(0.2, 0.3);

  // @ts-expect-error `a.x + b.x` widens to `number`, which is not an `F32`. Use `add(a, b)`.
  const wrong: Vec2 = { x: a.x + b.x, y: a.y + b.y };

  // ...and the compiler was right to complain: the f64 sum is genuinely not
  // representable in 32 bits, so `stateHash` would have hashed a rounded value
  // that no longer matches the state.
  expect(
    Math.fround(wrong.x),
    'the f64 sum should not survive a round trip through f32 — that is the whole point',
  ).not.toBe(wrong.x);
  expect(Math.fround(add(a, b).x), 'add() must produce an exact f32').toBe(add(a, b).x);
});

test('a raw number literal cannot be used as a coordinate', () => {
  // @ts-expect-error a literal has not been through `f32()`. Use `vec2(1.1, 2.2)`.
  const wrong: Vec2 = { x: 1.1, y: 2.2 };
  expect(wrong.x).toBe(1.1);
});

test('a raw number cannot be passed where an F32 is required', () => {
  // @ts-expect-error `neg` takes an `F32`, so its argument is provably rounded.
  const wrong = neg(1.1);
  expect(wrong).toBe(Math.fround(-1.1));
});

test('f32() is the way in, and it round-trips', () => {
  const value: F32 = f32(0.1 + 0.2);
  expect(Math.fround(value)).toBe(value);
  expect(vec2(1 / 3, 2 / 7)).toEqual({ x: f32(1 / 3), y: f32(2 / 7) });
});

test('neg preserves the sign of zero', () => {
  // `0 - x` would turn -0 into +0. stateHash can see the difference: -0 and +0
  // have different bit patterns, so a "harmless" rewrite would desync a replay.
  expect(Object.is(neg(f32(0)), -0)).toBe(true);
  expect(Object.is(neg(f32(-0)), 0)).toBe(true);
});

test('every helper returns an exact f32', () => {
  const a = vec2(1 / 3, 2 / 7);
  const b = vec2(Math.PI, Math.E);
  const results: number[] = [
    add(a, b).x,
    add(a, b).y,
    scale(a, 1 / 9).x,
    scale(a, 1 / 9).y,
    length(b),
    clampLengthMax(scale(b, 1000), 7).x,
    clampLengthMax(scale(b, 1000), 7).y,
    withLength(a, 13).x,
    withLength(a, 13).y,
  ];
  for (const value of results) {
    expect(Math.fround(value), `${value} is not representable in f32`).toBe(value);
  }
});

test('clampLengthMax leaves short vectors untouched and shortens long ones', () => {
  const short = vec2(3, 4);
  expect(clampLengthMax(short, 10)).toBe(short);
  expect(length(clampLengthMax(vec2(300, 400), 10))).toBeCloseTo(10, 4);
  // withLength binds from both sides: it lengthens as well as shortens.
  expect(length(withLength(short, 10))).toBeCloseTo(10, 4);
  expect(withLength(vec2(0, 0), 10)).toEqual(vec2(0, 0));
});
