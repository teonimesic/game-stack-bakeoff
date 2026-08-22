# Agent guide

A deterministic, headlessly-verifiable game template. Bevy 0.19 + Rust.

## The one command

```
just verify
```

Green means done. Red means not done. Nothing else counts as evidence — not
"it compiles", not "it looks right", not your own reasoning about the code.

While iterating, `just test-sim` (~1s, no GPU) is the fast loop.
Run `just verify` before you claim to be finished.

**If `target/` is empty, run `just warm` first.** A cold build is ~5–6 minutes —
it fits inside the 10-minute command ceiling, but only just, and you do not want
to spend a turn discovering that.

## Layout

| Crate | Contains | Depends on a GPU? |
|---|---|---|
| `crates/sim` | All game rules and state. The source of truth. | **No.** Deliberately cannot — it does not depend on `bevy`, only on `bevy_ecs`/`bevy_app`/`bevy_math`/`bevy_time`. |
| `crates/game` | Rendering, input, window. Reads `sim`, never writes to it. | Yes |

**Put game logic in `crates/sim`.** If a rule lives in `crates/game` it cannot be
tested without a GPU, and it will not be replayable or networkable. This is the
single most important convention in the repo.

## Determinism rules — these are load-bearing, not style

The simulation must produce byte-identical results from the same seed and
inputs. Replay tests, rollback netcode, and desync detection all depend on it.

1. **Simulation runs in `FixedUpdate`, inside `SimSet`, `.chain()`ed.** Never add
   game logic to `Update`.
2. **Read `Intents`, never `ButtonInput`.** `FixedUpdate` runs 0, 1, or many
   times per frame; device state is frame-scoped, so reading it directly drops
   and duplicates inputs. The client converts devices → intent once per frame.
3. **No wall clock in `sim`.** No `Instant`, `SystemTime`, or `Time<Real>`. Use
   `Tick`.
4. **Sort order-sensitive queries on `SimId`.** Bevy documents query iteration
   order as *not guaranteed*. Never sort or network on `Entity` — its index is
   reused after despawn.
5. **All randomness comes from `SimRng`**, which is part of snapshotted state.
   No `rand::thread_rng`, no OS entropy.
6. **Never enable `glam/fast-math`.** It explicitly trades away bit-for-bit
   cross-platform identity. `bevy_math/libm` is on for the same reason — leave it.
7. **No `par_iter` reductions in `sim`.** Float addition is not associative.
8. **Don't route simulation events through `Messages`.** Message buffers are
   frame-scoped, not tick-scoped. Use per-tick state (`TickEvents`).

`just test-sim` enforces most of these. If a determinism test fails, **find the
nondeterminism — do not relax the assertion.** An exact hash comparison that
becomes approximate is worthless.

## Testing

Write the cheapest test that would actually catch the bug:

1. **Simulation test** (`crates/sim/tests/`) — pure logic. Milliseconds, no GPU.
   Most changes need only this.
2. **Replay test** — record inputs, assert the hash chain is stable. One replay
   test catches most determinism regressions at once.
3. **Rendering test** (`crates/game/tests/render.rs`) — real GPU, real pixels,
   no window. Use these when the bug would be *invisible to logic tests*: a
   sprite that never spawns, a camera that frames nothing, a view that stops
   following the simulation.

For rendering, prefer assertions in this order:
- **invariants** — "something rendered", "ink is in the left sixth"
- **relational** — "holding up moved the paddle's pixels up"
- **golden image** — only when the exact look is the thing under test

The first two survive colour tweaks and GPU differences. Golden images do not.

**Tolerance in image comparison exists for cross-vendor GPU rounding, not for
misplaced geometry.** A sprite in the wrong place moves thousands of pixels.
If a golden test fails by a lot, it found a real bug — do not widen the budget.

## Gameplay is not correctness

A change can pass every test and still make the game worse. Tests catch "the
ball does not move"; they do not catch "the ball is so fast the game is
unplayable". When you change tuning constants (`PADDLE_SPEED`, `BALL_SPEEDUP`,
`MAX_BALL_SPEED`), add or update an assertion on the *consequence* — rally
length, time-to-score, ball speed after N hits — not just on the constant.

## Boundaries

✅ Always: put game rules in `crates/sim`; run `just verify` before finishing;
add a test for behaviour you changed.

⚠️ Ask first: adding a dependency; changing the tick rate; changing
`state_hash`, the replay format, or the wire protocol (they are compatibility
surfaces); upgrading Bevy.

🚫 Never: `#[ignore]` or delete a failing test to make `verify` pass; widen a
determinism assertion; `git commit --no-verify`; enable `glam/fast-math`; add
game logic to `crates/game`.

If a test is genuinely wrong, say so explicitly and explain why — do not
silently weaken it.
