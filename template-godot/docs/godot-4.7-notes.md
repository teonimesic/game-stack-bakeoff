# Godot 4.7 notes

Version-grounding for a model whose training data is mostly Godot 3.x and early
4.x. Pinned to **4.7.1.stable**. When something disagrees with your memory,
trust the parser and this file.

## Renamed / removed since Godot 3

| Godot 3 | Godot 4.7 |
|---|---|
| `Reference` | `RefCounted` |
| `Spatial`, `KinematicBody2D` | `Node3D`, `CharacterBody2D` |
| `yield(obj, "signal")` | `await obj.signal` |
| `export var speed = 3` | `@export var speed: float = 3.0` |
| `onready var x = $Y` | `@onready var x: Node = $Y` |
| `PoolByteArray`, `PoolIntArray` | `PackedByteArray`, `PackedInt64Array` |
| `OS.get_ticks_msec()` | `Time.get_ticks_msec()` |
| `Vector2.clamped(len)` | `Vector2.limit_length(len)` |
| `rand_range(a, b)` | `randf_range(a, b)` |
| `connect("sig", self, "_on")` | `sig.connect(_on)` |
| `instance()` | `instantiate()` |
| `.tres`/`.tscn` reference by path | referenced by `uid://…`; paths still work |

## Typing, which this project turns up to error level

* `var x := 1` infers `int`; `var x = 1` is UNTYPED and fails to compile here.
* Typed arrays: `Array[int]`, `Array[Sim.Entity]`. Typed dictionaries
  (`Dictionary[String, String]`) exist since 4.4.
* `Callable.call()` returns `Variant` — always. Under `unsafe_call_argument=2`
  you cannot pass it where a `bool`/`int` is declared. Use a named method.
* `ProjectSettings.get_setting()` returns `Variant`. Prefer the typed engine
  property (`Engine.physics_ticks_per_second`) when one exists.
* Comparing two `Variant`s yields a `Variant`, not a `bool`.
* Re-parsing a script (`GDScript.reload()`) gives its INNER classes a fresh
  identity, after which `Array[Outer.Inner]` no longer matches an array made
  before the reload. `tools/check.gd` orders its work around this.

## Numbers

* GDScript `int` is 64-bit **signed** and wraps silently on overflow — which is
  what makes the wrapping-u64 PCG in `Sim.SimRng` work with no masking. But `>>`
  is an **arithmetic** shift and sign-extends; `SimRng._lsr` exists for that.
* A hex literal larger than `2**63 - 1` does not parse: Godot clamps it to
  `INT64_MAX` and prints an error. Write the signed two's-complement value
  instead (see `_FNV_OFFSET`).
* GDScript `float` is 64-bit. `Vector2`/`Vector3` components are `real_t`, which
  is **32-bit** in a standard build. Reading `v.x` widens; writing narrows. This
  is why simulation state lives in `Vector2`.

## Rendering and the headless display driver

* `--headless` == `--display-driver headless`, which forces a dummy rendering
  driver. `get_viewport().get_texture().get_image()` returns **null**. Passing
  `--rendering-driver metal/vulkan` alongside it does not help — verified.
* `RenderingServer.frame_post_draw` never fires without a display; awaiting it
  deadlocks with no error. `SceneTree.process_frame` always fires.
* A script passed to `-s` must extend `MainLoop` (usually `SceneTree`).
  `_initialize()` runs before the first frame, `root` already exists, and you
  end the process with `quit(exit_code)`.
* A runtime error inside `_initialize()` aborts the function but NOT the engine.
  The process then spins forever. Connect a watchdog to `process_frame` first.
* Arguments after a bare `--` reach the script via `OS.get_cmdline_user_args()`.
* `--check-only` reports parse errors but always exits 0, so it cannot gate
  anything. `GDScript.reload()` returns a real `Error`; `tools/check.gd` uses it.
* 2D canvas colours are written to the framebuffer verbatim: `Color(0.35, …)`
  lands as `round(0.35 * 255) = 89`. No tonemapper sits between `draw_rect` and
  the pixel unless you add a `WorldEnvironment`.

## Project structure

* `class_name` registers a global name via `.godot/global_script_class_cache.cfg`,
  written during import. **Adding** a file with a new `class_name` needs
  `godot --headless --path . --import` before the name resolves; the `just`
  recipes do this automatically when sources are newer than the cache.
* A `.gdignore` file makes a directory invisible to the import system. That is
  how `tests/golden/` keeps its PNGs as plain files instead of imported
  `CompressedTexture2D` resources.
