# Agent guide

A deterministic, headlessly-verifiable game starter. Bevy 0.19 + Rust.

This starter contains a placeholder, not a game. Replace it with whatever the
task asks for; keep the harness, the boundaries and the verification loop.

## The one command

`just verify` green means done; red means not done. Nothing else counts as
evidence — not "it compiles", not "it looks right", not your own reasoning. A
Stop hook re-runs it when you try to finish, so ending the turn red does not
work.

| Command | Warm | From an empty build dir | What it proves |
|---|---|---|---|
| `just quick` | ~2 s | ~25 s | all of `crates/sim`: logic, determinism, replay, boundary, lints |
| `just verify` | ~4 s | ~3–4 min | the above **plus** real pixels from a real GPU |

**`just quick` is the inner loop — run it constantly.** It is a complete signal
for simulation work and never compiles the renderer. From an empty build
directory, run `just warm` first.

## Layout

| Crate | Contains | GPU? |
|---|---|---|
| `crates/sim` | All game rules and state. The source of truth. | **No — cannot.** |
| `crates/game` | Rendering, input, window. Reads `sim`, never writes to it. | Yes |

**Put game logic in `crates/sim`.** A rule in `crates/game` cannot be tested
without a GPU and is never replayable or sendable over the wire. `crates/sim/
tests/boundary.rs` enforces this against the real dependency graph: adding
`bevy_render`, `wgpu`, `winit`, `rand` or `getrandom` to `crates/sim/Cargo.toml`
fails the build. The view draws only the entity kinds it knows, so a new
simulation entity does not silently change the rendered frame.

## Determinism rules — load-bearing, not style

The simulation must produce byte-identical results from the same seed and
inputs. Replay, rollback and desync detection all depend on it.

**Mechanically enforced** — a build error, not a review comment. Do not edit
the guard.

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
   and duplicates inputs.
3. **All randomness comes from `SimRng`**, which is part of snapshotted state.
4. **Sort order-sensitive queries on `SimId`.** Bevy documents query iteration
   order as *not guaranteed*, and an `Entity` index is reused after despawn.
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
   A test with no GPU proved nothing; `just ci` makes that red.

Prefer rendering assertions in this order — the first two survive colour tweaks
and GPU differences, golden images do not: **invariants** ("something
rendered", "the ink is where it should be") → **relational** ("holding that
input moved its pixels up") → **golden image** (only when the exact look is the
thing under test).

A failing pixel assertion writes `*.actual.png`, `*.expected.png` and
`*.diff.png` (magenta = differing pixel) next to the golden, with the pixel
count and bounding box. **Open the diff first.** A handful of pixels with a
small channel delta is cross-vendor GPU rounding; thousands, or a tight box you
did not touch, is a real bug.

## Draw it through the camera the capture reads

`just film` and every test in `crates/game/tests/render.rs` read exactly one
thing: the pixels the arena camera renders into its `RenderTarget`. **Anything
the player reads — HUD, score, timer, game-over card — must be drawn by that
camera**, or it appears in the window and in nothing else, and you can no longer
tell a broken scoreboard from a scoreboard the capture never looked at.

The starter's HUD is the worked example: `game::spawn_hud` puts a `Text2d` in
the arena's corner, so the 2D camera draws it wherever that camera points —
window or offscreen image. `render.rs::the_hud_is_in_the_captured_frame` counts
its ink inside `game::HUD_REGION` and fails if it leaves the frame or stops
tracking the simulation. Copy that shape for anything you add.

Two consequences worth keeping: HUD content is a pure function of `Tick` and
simulation state, because the captured frame is asserted byte-reproducible; and
an overlay is ink like any other, so measure the scene with
`Frame::ink_centroid_outside(HUD_REGION, …)` rather than averaging the readout
in with the thing you meant to weigh.

## Gameplay is not correctness

A change can pass every test and still make the game worse. Tests catch "it
does not move"; not "it moves so fast the game is unplayable". When you change
a tuning constant, assert on the *consequence you care about, measured over a
run* — how long something takes, how often it happens, where things end up —
never on the constant you just changed.

## Probing a run

`just probe SEED` is a long-lived headless process: it prints one trace line
for tick 0, then reads one JSON input object per line from stdin, steps exactly
one tick per line, and prints one trace line per tick, flushed. A blank line
means no input; EOF or `quit` exits 0. **stdout carries only
trace lines**; send anything else to stderr.

`just probe-file SEED TICKS SCRIPT OUT` is the batch form: it replays a whole
script and writes the same lines to `OUT`. A script is
`{"version": 1, "inputs": [{…}, …]}`, one object of input fields per tick; `-`
means no input, and past the end of `inputs` is idle.

`just film SEED TICKS SCRIPT OUTDIR` renders at most 12 evenly spaced frames of
the run to `OUTDIR/frame_0000.png`, …. It needs a GPU; the probes do not.

Every trace line is exactly:

```json
{"tick": 1, "hash": "0x1234abcd...", "state": { ... }, "events": ["bounce"]}
```

`hash` is `state_hash` as lowercase hex; `events` is a list of strings. `state`
is **game-defined**: expose the values that describe what the game is doing
right now, as finite JSON numbers, in a stable machine-readable shape. Both
probes must stay headless and deterministic — the same seed and the same inputs
produce a byte-identical trace.

## Bevy 0.19 API notes

Your training data is probably older than this Bevy. When something doesn't
compile, trust the compiler over your memory, then check
`docs/bevy-0.19-notes.md` — it has the full delta. The ones that bite most
often:

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
`state_hash`, the replay format or the trace format (compatibility surfaces);
upgrading Bevy; changing `bevy`'s feature list (a 2.4× build-time difference).

🚫 Never: `#[ignore]` or delete a failing test to make `verify` pass; widen a
determinism assertion; edit `crates/sim/clippy.toml` or the ban lists in
`crates/sim/tests/boundary.rs` to get unblocked; add game logic to
`crates/game`. If a test is genuinely wrong, say so explicitly and explain why
— do not silently weaken it.

## When the gate itself is wrong

`just verify` and `just check` can be wrong, and this template's are not exempt. If one
of them is red on a tree you have not changed yet, that is a defect here, not in your
work.

1. **Say so in your final message**, naming the recipe and the file. Nothing else
   reports it, and the turns you spend on it are otherwise invisible.
2. **Repairing it is allowed** — it is not on the never-list above.
3. **A repair must leave the check able to fail.** Fix how the check handles the input
   it got wrong. Do not take that input out of what the check looks at: narrowing a
   check's scope — a skip list, an ignore entry, an exclusion — turns a check that
   fails wrongly into one that cannot fail at all. That is worse than the defect it
   replaces, and it reads as compliance.

**How to tell the two apart, before you move on:** put a real error into the thing the
gate stopped complaining about, run the gate, and confirm it goes red; then take the
error out. A repair you cannot make go red is not a repair — say so in your final
message and leave the gate red rather than shipping it.
