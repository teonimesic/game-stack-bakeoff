# Agent guide

A deterministic, verifiable game template. Godot 4.7 + GDScript.

## The one command

```
just verify
```

Green means done. Red means not done. Nothing else counts as evidence — not "it
runs", not "it looks right", not your own reasoning about the code.

Warm `verify` is **~3 seconds**. There is no compile step and no cold-build
cliff, so run it often. `just check` (~0.3s) and `just test-sim` (~1s) are the
inner loop. **Run `just warm` once after cloning** — it creates the Python venv
holding `gdformat`/`gdlint`; everything else works without it.

`just verify` **opens a real 640x400 window for about a second.** That is not a
misconfiguration and there is no flag to avoid it — see below.

## Layout

| Directory | Contains | Needs a display? |
|---|---|---|
| `sim/` | All game rules and state. The source of truth. | **No.** Every class is a plain `RefCounted` — no `Node`, no scene tree. `just check` FAILS if a scene-tree, input, or nondeterminism symbol appears here. |
| `view/` | Drawing, input, the window. Reads `sim`, never writes to it. | Yes |
| `tests/` | Test runner, `Frame` helper, the three suites. | Only `render_test.gd` |
| `tools/` | `check.gd` (compile + boundary) and the `Boundary` rules. | No |

**Put game logic in `sim/`.** A rule that lives in `view/` cannot be tested
without a display, and will not be replayable or networkable. This is the single
most important convention in the repo, and it is the one the tooling enforces
hardest.

## Static typing is ON, as errors

`project.godot` sets `debug/gdscript/warnings/untyped_declaration` and every
`unsafe_*` warning to **2 (error)**. `var x = foo()` does not compile. This is
the highest-value setting in a Godot project and it ships off by default — leave
it on. Annotate types; do not lower the level. If a call is genuinely dynamic,
suppress it at that one line with `@warning_ignore("unsafe_call_argument")` and
say why (there is exactly one example, in `tests/test_runner.gd`).

Consequences you will hit: `Callable.call()`, `ProjectSettings.get_setting()`,
and `a == b` on two `Variant`s all return `Variant`, which is rejected wherever a
concrete type is declared. Use a named method and `Engine.physics_ticks_per_second`.

## Determinism rules — these are load-bearing, not style

The simulation must produce byte-identical results from the same seed and
inputs. `tools/boundary.gd` mechanically enforces 1, 2, 3, 5 and 7.

1. **One tick is one `Sim.step()`, which runs `SIM_PIPELINE` in stage order.**
   Add systems to that array with an explicit stage; never call one system from
   inside another. Tests call `Sim.step` directly and never `_physics_process`.
2. **Read `Sim.Intents`, never `Input`.** A rendered frame contains 0, 1, or many
   physics ticks, so device state is frame-scoped and reading it inside a tick
   drops and duplicates input. `view/main.gd` latches devices into intent once
   per frame; it is the only script allowed to touch a device.
3. **No wall clock in `sim/`.** No `Time.`, `OS.`, `Engine.`. Use `world.tick`.
4. **Sort order-sensitive iteration on the sim id** (`world.by_sim_id()`), never
   on array position — array order changes when an entity is removed.
5. **All randomness comes from `world.rng` (`Sim.SimRng`)**, which is part of
   snapshotted state. No `randf`, `randi`, `RandomNumberGenerator`.
6. **Simulation state lives in `Vector2`.** Its components are `real_t`, i.e.
   f32 in a standard build, and `Sim.state_hash` hashes f32 bit patterns. A
   coordinate that escapes into a bare GDScript `float` (f64) is hashed lossily.
   A build with `precision=double` changes every hash; do not use one.
7. **No signals, `await`, or threads in `sim/`.** They resolve on the frame, not
   the tick. Use per-tick state (`Sim.TickEvents`).

If a determinism test fails, **find the nondeterminism — do not relax the
assertion.** An exact hash comparison that becomes approximate is worthless.

## Testing

Write the cheapest test that would actually catch the bug:

1. **Simulation test** (`tests/determinism_test.gd`, `tests/playability_test.gd`)
   — pure logic, headless, ~1s. Most changes need only this.
2. **Replay test** — record inputs, assert the hash chain is stable. One replay
   test catches most determinism regressions at once.
3. **Rendering test** (`tests/render_test.gd`) — real GPU, real pixels. Use these
   when the bug would be *invisible to logic tests*: a rectangle that never
   draws, a transform that frames nothing, a view that stops following the sim.

Prefer rendering assertions in this order: **invariants** ("something rendered",
"ink is in the left sixth") → **relational** ("holding up moved the paddle's
pixels up") → **golden image** (only when the exact look is under test). The
first two survive colour tweaks and driver differences; golden images do not.

On a golden failure the test writes `rally.actual.png`, `rally.expected.png` and
`rally.diff.png` (magenta = disagrees) and prints their paths. **Open the diff.**
A silhouette means geometry moved — a real bug. Speckle means driver rounding.
Tolerance exists for the second, never the first; do not widen the budget.

## Rendering CANNOT run headless. This is structural, not your mistake.

**`godot --headless` cannot draw anything.** It forces a dummy rendering driver,
so `get_viewport().get_texture().get_image()` returns **null** and no pixel is
ever produced. This is not a flag you are missing: `--headless` combined with an
explicit `--rendering-driver metal` (or `vulkan`) was tested and still returns
null. There is no offscreen path in Godot 4.7 that works without a display
server.

The consequences, which will otherwise cost you a turn each:

* **`just test-render` opens a real 640x400 window** for about a second, every
  time, and so does `just verify`. Expected. Do not try to "fix" it by adding
  `--headless` — that turns all five render tests into skips.
* **On a machine with no display, run `xvfb-run -a just test-render`.** That is
  what CI does, with `LIBGL_ALWAYS_SOFTWARE=1`.
* **`await RenderingServer.frame_post_draw` never fires** with no display, and
  the `await` hangs the script forever with no error and no timeout. Use
  `await get_tree().process_frame` / `await tree.process_frame`, which always
  fires. `tests/render_test.gd` does.
* **A skip is not a pass.** With no display the render suite reports SKIP and
  still exits 0, so a developer who cannot fix it is not blocked — but the
  summary prints a loud `N TEST(S) SKIPPED` banner, and `just ci` runs with
  `--strict`, where every skip is a FAILURE. Green CI over zero render coverage
  is worse than red CI, so CI is not allowed to do it. If you see that banner,
  the pixels were never checked.
* Both runners connect an abort watchdog before doing anything else, because a
  runtime error inside `SceneTree._initialize` does **not** stop the engine — it
  spins forever with no output. If you see `RUNNER ABORTED`, scroll up for the
  `SCRIPT ERROR`, or run `just check`, which prints compile errors on their own.

## Gameplay is not correctness

A change can pass every test and still make the game worse. Tests catch "the ball
does not move"; not "the ball is so fast the game is unplayable". When you change
a tuning constant (`PADDLE_SPEED`, `BALL_SPEEDUP`, `MAX_BALL_SPEED`), add or
update an assertion on the *consequence* — rally length, time-to-score, ball
speed after N hits — not just on the constant. That is what
`tests/playability_test.gd` is for.

## Godot 4.7 API notes

Your training data is probably older than this Godot. See
`docs/godot-4.7-notes.md`. The ones that bite here:

| You may remember | Godot 4.7 |
|---|---|
| `Reference` | `RefCounted` |
| `yield(...)` | `await` |
| `export var x` | `@export var x: int` |
| `PoolByteArray` | `PackedByteArray` |
| `OS.get_ticks_msec` | `Time.get_ticks_msec` (and banned in `sim/`) |
| `Vector2.clamped(n)` | `Vector2.limit_length(n)` |
| `.gd` files resolve by path | a new `class_name` needs a registry refresh — every `just` recipe does it; a bare `godot` call does not |

## Boundaries

✅ Always: put game rules in `sim/`; run `just verify` before finishing; add a
test for behaviour you changed; type every declaration.

⚠️ Ask first: adding an addon or dependency; changing the tick rate (two places —
`Sim.TICK_HZ` and `physics/common/physics_ticks_per_second`); changing
`state_hash`, the replay format, or the entity ids (they are compatibility
surfaces); changing the rendering method or colour settings in `project.godot`.

🚫 Never: delete a test, or `skip()` a failing one, to make `verify` pass —
`skip()` is only for a missing capability of the machine, and `just ci` fails on
it regardless; weaken a determinism assertion or widen the golden budget to hide
a moved sprite; lower a `gdscript/warnings/*` level; add a rule to `disable` in
`gdlintrc`; delete a rule from `tools/boundary.gd`; put game logic in `view/`.

If a test is genuinely wrong, say so explicitly and explain why — do not silently
weaken it.
