# Agent guide

A deterministic, verifiable game template. Godot 4.7 + GDScript.

This starter contains a placeholder, not a game. Replace it with whatever the
task asks for; keep the harness, the boundaries and the verification loop.

## The one command

```
just verify
```

Green means done. Red means not done. Nothing else counts as evidence — not "it
runs", not "it looks right", not your own reasoning about the code.

Warm `verify` is **~3 seconds**; there is no compile step and no cold-build
cliff, so run it often. `just check` (~0.3s) and `just test-sim` (~1s) are the
inner loop. **Run `just warm` once after cloning** — it creates the Python venv
holding `gdformat`/`gdlint`; everything else works without it.

`just verify` **opens a real 640x400 window for about a second.** Not a
misconfiguration, and there is no flag to avoid it — see below.

## Layout

| Directory | Contains | Needs a display? |
|---|---|---|
| `sim/` | All game rules and state. The source of truth. | **No.** Every class is a plain `RefCounted` — no `Node`, no scene tree. `just check` FAILS if a scene-tree, input, or nondeterminism symbol appears here. |
| `view/` | Drawing, input, the window. Reads `sim`, never writes to it. | Yes |
| `tests/` | Test runner, `Frame` helper, the three suites. | Only `render_test.gd` |
| `tools/` | `check.gd` (compile + boundary), the `Boundary` rules, the probes. | Only `film.gd` |

**Put game logic in `sim/`.** A rule that lives in `view/` cannot be tested
without a display, and will not be replayable or networkable. It is the single
most important convention here, and the one the tooling enforces hardest.

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
   Add systems to that array with an explicit stage; never call one from inside
   another. Tests call `Sim.step` directly, never `_physics_process`.
2. **Read `Sim.Intents`, never `Input`.** A rendered frame contains 0, 1, or many
   physics ticks, so device state is frame-scoped and reading it inside a tick
   drops and duplicates input. `view/main.gd` latches devices into intent once a
   frame, and is the only script allowed to touch a device.
3. **No wall clock in `sim/`.** No `Time.`, `OS.`, `Engine.`. Use `world.tick`.
4. **Sort order-sensitive iteration on the sim id** (`world.by_sim_id()`), never
   on array position — array order changes when an entity is removed.
5. **All randomness comes from `world.rng` (`Sim.SimRng`)**, which is part of
   snapshotted state. No `randf`, `randi`, `RandomNumberGenerator`.
6. **Simulation state lives in `Vector2`.** Its components are `real_t`, i.e.
   f32 in a standard build, and `Sim.state_hash` hashes f32 bit patterns. A
   coordinate that escapes into a bare GDScript `float` (f64) is hashed lossily.
   A `precision=double` build changes every hash; do not use one.
7. **No signals, `await`, or threads in `sim/`.** They resolve on the frame, not
   the tick. Use per-tick state (`Sim.TickEvents`).

If a determinism test fails, **find the nondeterminism — do not relax the
assertion.** An exact hash comparison that becomes approximate is worthless.

## Testing

Write the cheapest test that would actually catch the bug:

1. **Simulation test** (`tests/determinism_test.gd`, `tests/invariants_test.gd`)
   — pure logic, headless, ~1s. Most changes need only this.
2. **Replay test** — record inputs, assert the hash chain is stable. One catches
   most determinism regressions at once.
3. **Rendering test** (`tests/render_test.gd`) — real GPU, real pixels. For bugs
   *invisible to logic tests*: a rectangle that never draws, a transform that
   frames nothing, a view that stops following the sim.

There is no auto-discovery: a new suite has to be named in a runner to run at all.

Prefer rendering assertions in this order: **invariants** ("something rendered",
"the ink is where the state says it is") → **relational** ("holding a key moved
those pixels up") → **golden image** (only when the exact look is under test).
The first two survive colour tweaks and driver differences; golden images do not.

On a golden failure the test writes `frame.actual.png`, `frame.expected.png` and
`frame.diff.png` (magenta = disagrees) and prints their paths. **Open the diff.**
A silhouette means geometry moved — a real bug; speckle means driver rounding.
Tolerance exists for the second, never the first.

## Everything the player sees goes under the view

`RenderTests.capture_frame` — which `just film` reuses verbatim — renders a
viewport holding **only the `View` node**. `main.tscn` and its `Main` node are
never instantiated. Anything parented beside the view instead of under it
therefore appears in `just run` and is absent from every filmed frame and every
rendering test, with nothing red to say so.

So HUD, overlays and effects belong inside `view/view.gd`'s tree. The tick and
marker readout is the worked example: `_draw_hud` draws it from `_draw`, in
screen space via `draw_set_transform_matrix(transform.affine_inverse())` because
the view's own transform carries the arena's negative Y scale, and the "the HUD
is inside the captured frame" test fails if those pixels leave the capture.

## Particles — use them, they are one call

Godot ships a GPU particle system. `view/fx.gd` wires it up; `View` already owns
an idle `Fx`, so a burst costs one line:

```gdscript
fx.show_bursts([Fx.Burst.new(position, Color.ORANGE, age_seconds, entity.id)])
```

**A burst must be a pure function of simulation state.** `capture_frame` steps to
tick N with no view attached and syncs once, so anything the view accumulated
frame by frame — an emitter you started when an event fired, a tween, a shake —
is missing from every filmed frame and every rendering test, with nothing red to
say so. Keep the tick a thing happened on, and pass the age. That is also what
makes a burst reproducible: `fx.gd` runs the emitters with `speed_scale = 0` so
wall time cannot reach them, and three rendering tests hold it — the burst is
drawn, the age drives it, and two identical bursts are byte-identical.

`GPUParticles3D`, `CPUParticles2D/3D`, `MultiMesh`, `AtlasTexture`,
`AnimatedSprite2D` and `Skeleton3D` are all in the engine at this version and
need no addon. The `Viewport` antialiasing and `WorldEnvironment` post-processing
knobs are the deliberate exception: `tests/render_test.gd` asserts exact byte
values, and a tonemapper or an MSAA pass changes those bytes without changing any
geometry — see the `[rendering]` block in `project.godot`.

## Probing a run

Three recipes let you watch a run without playing it.

**`just probe SEED`** — a live session, and the one to reach for. It prints a
trace line for tick 0, before anything has been stepped, then reads one JSON
object per line from stdin, steps **exactly one tick per line**, and prints one
trace line per tick, flushed. End of input, a blank line, or `quit` exits 0.
Anything that is not a trace line goes to stderr, so stdout is safe to parse.

```
printf '{}\n{"nudge_up":true}\n' | just probe 7
```

**`just probe-file SEED TICKS SCRIPT OUT`** — the batch form: `TICKS` ticks from
`SEED`, one input per tick from `SCRIPT` (a JSON file
`{"version": 1, "inputs": [ {…}, … ]}`, or `-` for none), written to `OUT` as
JSON Lines, one line per tick from tick 1. Past the end of the array nothing is
pressed. Exits non-zero if it could not run every tick.

**`just film SEED TICKS SCRIPT OUTDIR`** — at most 12 PNGs, evenly spaced over
`0..TICKS` inclusive. It renders, so it needs a display.

One trace line, exactly:

```json
{"tick": 1, "hash": "0x...", "state": { ... }, "events": ["bounce"]}
```

`state` is game-defined, and built in `Trace.state_json`. **Expose the values
that describe what the game is doing right now**, in a stable, machine-readable
shape. Numbers must be finite; key order is fixed. Both probes stay headless and
deterministic: same seed and same inputs, byte-identical trace.

## Rendering CANNOT run headless. This is structural, not your mistake.

**`godot --headless` cannot draw anything.** It forces a dummy rendering driver,
so `get_viewport().get_texture().get_image()` returns **null** and no pixel is
ever produced. This is not a flag you are missing: adding an explicit
`--rendering-driver metal` (or `vulkan`) was tested and still returns null.
Godot 4.7 has no offscreen path that works without a display server.

The consequences, which will otherwise cost you a turn each:

* **`just test-render` opens a real 640x400 window** for about a second, and so
  does `just verify`. Expected. Do not "fix" it by adding `--headless` — that
  turns all five render tests into skips.
* **On a machine with no display, run `xvfb-run -a just test-render`.** That is
  what CI does, with `LIBGL_ALWAYS_SOFTWARE=1`.
* **`await RenderingServer.frame_post_draw` never fires** with no display, and
  the `await` hangs the script forever with no error and no timeout. Use
  `await tree.process_frame`, which always fires. `tests/render_test.gd` does.
* **A skip is not a pass.** With no display the render suite reports SKIP and
  still exits 0, so a developer who cannot fix it is not blocked — but the
  summary prints a loud `N TEST(S) SKIPPED` banner, and `just ci` runs with
  `--strict`, where every skip is a FAILURE. Green CI over zero render coverage
  is worse than red CI. If you see that banner, the pixels were never checked.
* Every `SceneTree` entry point connects an abort watchdog first, because a
  runtime error inside `_initialize` does **not** stop the engine — it spins
  forever with no output. On `RUNNER ABORTED`, scroll up for the `SCRIPT ERROR`,
  or run `just check`, which prints compile errors on their own.

## Gameplay is not correctness

A change can pass every test and still make the game worse. Tests catch "nothing
moves"; not "it moves so fast the game is unplayable". When you change a tuning
constant, assert on **the consequence you care about, measured over a run** —
where things ended up, how often something happened, whether a held input changed
the outcome — never on the constant you just changed. That is what
`tests/invariants_test.gd` is for.

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
| `--quiet` hides the banner | it silences `print` too; `--no-header` drops only the banner |

## Boundaries

✅ Always: put game rules in `sim/`; draw what the player sees under `View`; run
`just verify` before finishing; add a test for behaviour you changed; type every
declaration.

⚠️ Ask first: adding an addon or dependency; changing the tick rate (two places —
`Sim.TICK_HZ` and `physics/common/physics_ticks_per_second`); changing
`state_hash`, the replay format, the trace line shape, or the entity ids (they
are compatibility surfaces); changing the rendering method or colour settings in
`project.godot`.

🚫 Never: delete a test, or `skip()` a failing one, to make `verify` pass —
`skip()` is only for a missing capability of the machine, and `just ci` fails on
it regardless; weaken a determinism assertion or widen the golden budget to hide
a moved sprite; lower a `gdscript/warnings/*` level; add a rule to `disable` in
`gdlintrc`; delete a rule from `tools/boundary.gd`; put game logic in `view/`.

If a test is genuinely wrong, say so explicitly and explain why — do not silently
weaken it.

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
