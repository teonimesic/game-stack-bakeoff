# Agent guide

A deterministic, headlessly-verifiable game template. Bevy 0.19 + Rust.

## The one command

`just verify` green means done; red means not done. Nothing counts as
evidence — not "it compiles", not "it looks right", not your own reasoning
about the code. A Stop hook re-runs it when you try to finish, so ending the
turn red does not work; fix the cause instead.

| Command | Warm | From an empty build dir | What it proves |
|---|---|---|---|
| `just quick` | ~2 s | ~25 s | all of `crates/sim`: logic, determinism, replay, boundary, lints |
| `just verify` | ~4 s | ~3–4 min | the above **plus** real pixels from a real GPU |

**`just quick` is the inner loop — run it constantly.** It is a complete signal
for simulation work and never compiles the renderer. If the build directory is
empty, `just warm` does the cold build up front so neither surprises you.

## Layout

| Crate | Contains | GPU? |
|---|---|---|
| `crates/sim` | All game rules and state. The source of truth. | **No — cannot.** |
| `crates/game` | Rendering, input, window. Reads `sim`, never writes to it. | Yes |

**Put game logic in `crates/sim`.** A rule in `crates/game` cannot be tested
without a GPU and is never replayable or networkable. `crates/sim/tests/
boundary.rs` enforces this against the real dependency graph: adding
`bevy_render`, `wgpu`, `winit`, `rand` or `getrandom` to `crates/sim/Cargo.toml`
fails the build. The view draws only entities it knows (`Ball`, `Paddle`), so a
new simulation entity does not silently change the rendered frame.

## Determinism rules — load-bearing, not style

The simulation must produce byte-identical results from the same seed and
inputs. Replay, rollback netcode and desync detection all depend on it.

**Mechanically enforced** — a build error, not a review comment. Read it; do
not edit the guard.

- No wall clock in `sim` — `Instant`/`SystemTime` are banned by
  `crates/sim/clippy.toml`. Use `Tick`.
- No `HashMap`/`HashSet` in `sim` — iteration order is not part of the
  snapshot. Use `BTreeMap`/`BTreeSet`.
- No `f32::sin`/`cos`/`powf`/… in `sim` — std calls the *platform's* libm and
  macOS, glibc and MSVC disagree in the last bit. Use `bevy_math::ops::*`.
- No entropy crate in `sim`; `glam/libm` stays on and `glam/fast-math` stays
  off (`crates/sim/tests/boundary.rs`).

**Not mechanically enforceable — these are on you:**

1. **Simulation runs in `FixedUpdate`, inside `SimSet`, `.chain()`ed.** Never
   add game logic to `Update`.
2. **Read `Intents`, never `ButtonInput`.** `FixedUpdate` runs 0, 1 or many
   times per frame; device state is frame-scoped, so reading it directly drops
   and duplicates inputs. The client converts devices → intent once per frame.
3. **All randomness comes from `SimRng`**, which is part of snapshotted state.
4. **Sort order-sensitive queries on `SimId`.** Bevy documents query iteration
   order as *not guaranteed*. Never sort or network on `Entity` — its index is
   reused after despawn.
5. **No `par_iter` reductions in `sim`.** Float addition is not associative.
6. **Don't route simulation events through `Messages`** — those buffers are
   frame-scoped, not tick-scoped. Use per-tick state (`TickEvents`).

If a determinism test fails, **find the nondeterminism — do not relax the
assertion.** An exact hash comparison that becomes approximate is worthless.

## Testing

Write the cheapest test that would actually catch the bug:

1. **Simulation test** (`crates/sim/tests/`) — pure logic, milliseconds, no
   GPU. Most changes need only this.
2. **Replay test** — record inputs, assert the hash chain is stable. One
   catches most determinism regressions at once.
3. **Rendering test** (`crates/game/tests/render.rs`) — real GPU, real pixels,
   no window. For bugs *invisible to logic tests*: a sprite that never spawns,
   a camera that frames nothing, a view that stopped following the simulation.
   A test with no GPU is a test that proved nothing; `just ci` makes that red.

Prefer rendering assertions in this order — the first two survive colour tweaks
and GPU differences, golden images do not: **invariants** ("something
rendered", "ink is in the left sixth") → **relational** ("holding up moved the
paddle's pixels up") → **golden image** (only when the exact look is the thing
under test).

A failing pixel assertion writes `*.actual.png`, `*.expected.png` and
`*.diff.png` (magenta = differing pixel) next to the golden and prints the
paths, pixel count and bounding box. **Open the diff before changing
anything.** A handful of pixels with a small channel delta is cross-vendor GPU
rounding; thousands, or a tight box somewhere you did not touch, is a real bug.

## Gameplay is not correctness

A change can pass every test and still make the game worse. Tests catch "the
ball does not move"; not "the ball is so fast the game is unplayable". When you
change tuning constants (`PADDLE_SPEED`, `BALL_SPEEDUP`, `MAX_BALL_SPEED`),
assert on the *consequence* — rally length, time-to-score, ball speed after N
hits — not just on the constant.

## Bevy 0.19 API notes

Your training data is probably older than this Bevy. When something doesn't
compile, trust the compiler over your memory, then check
`docs/bevy-0.19-notes.md` — it has the full delta and how to verify a claim
against the vendored source. The ones that bite most often:

| You may remember | Bevy 0.19 |
|---|---|
| `Camera { target, .. }` | `RenderTarget` is a **separate component** |
| `Events<T>`, `EventReader`, `EventWriter` | `Messages<T>`, `MessageReader`, `MessageWriter` |
| `App::add_event` / `Events::send` | `App::add_message` / `Messages::write` |
| `Trigger<E>` / `OnAdd` | `On<E>` / `Add` |
| Resources are their own storage | resources are components on singleton entities |

Pin the version. Do not upgrade Bevy as a side effect of another task.

## Boundaries

✅ Always: put game rules in `crates/sim`; run `just verify` before finishing;
add a test for behaviour you changed.

⚠️ Ask first: adding a dependency; changing the tick rate; changing
`state_hash`, the replay format or the wire protocol (compatibility surfaces);
upgrading Bevy; changing `bevy`'s feature list (a 2.4× build-time difference).

🚫 Never: `#[ignore]` or delete a failing test to make `verify` pass; widen a
determinism assertion; edit `crates/sim/clippy.toml` or the ban lists in
`crates/sim/tests/boundary.rs` to get unblocked; add game logic to
`crates/game`. If a test is genuinely wrong, say so explicitly and explain why
— do not silently weaken it.
