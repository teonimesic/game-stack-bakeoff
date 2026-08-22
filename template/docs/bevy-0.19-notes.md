# Bevy 0.19 — what changed since your training data

Bevy 0.19 shipped **2026-06-19**. Between 0.11 and 0.19 the project published roughly
**840 breaking-change entries across ~83,000 words** of migration guides — 103 entries in
0.18→0.19 alone. If your training data predates mid-2026, you will confidently write APIs that
no longer exist.

**This file is deliberately a table of signatures and deltas, not a tutorial with examples.**
That is an evidence-based choice: a 2025 ICSE study measured that when the surrounding context
already contains stale API usage, deprecated-API output rises to **70–90%** (versus 9–18% with
clean context), and a separate study found that retrieving *similar code* hurt accuracy by up to
**−15%** while retrieving *API descriptions* helped by up to **+20%**. Stale example code is worse
than no example code.

**When in doubt, trust the compiler over this file, and trust this file over your memory.**

Every signature and default below was checked against the vendored 0.19.0 sources in
`~/.cargo/registry` rather than recalled. Re-check anything you are about to depend on — the
recipe is at the bottom of this file.

## Renames and moves that will bite you

| If you write | It is now | Since |
|---|---|---|
| `Camera { target, .. }` | `RenderTarget` is a **separate component** — spawn it alongside `Camera2d`/`Camera3d` | 0.19 |
| `Events<T>` | `Messages<T>` | 0.17 |
| `EventReader<T>` / `EventWriter<T>` | `MessageReader<T>` / `MessageWriter<T>` | 0.17 |
| `App::add_event::<T>()` | `App::add_message::<T>()` | 0.17 |
| `Events::send()` / `Commands::send_event()` | `Messages::write()` / `Commands::write_message()` | 0.17 |
| `Trigger<E>` | `On<E>` | 0.17 |
| `OnAdd` / `OnInsert` / `OnRemove` | `Add` / `Insert` / `Remove` | 0.17 |
| `Transform` on UI nodes | `UiTransform` | 0.17 |
| `ExecutorKind`, `SimpleExecutor` | **removed.** `Schedule::set_executor(impl SystemExecutor)`; only `SingleThreadedExecutor` and `MultiThreadedExecutor` remain | 0.19 |
| `RenderGraph` as a graph, the `Node`/`ViewNode` traits | **gone.** `RenderGraph` is now a `ScheduleLabel` (`bevy_render::renderer`) for a schedule of ordinary ECS systems; there is no graph object and no node trait to implement | 0.19 |
| Resources as a distinct storage | Resources are **components on singleton entities** — literally `pub trait Resource: Component {}` | 0.19 |
| `x.sin()`, `x.cos()`, `x.powf(y)` in simulation code | `bevy_math::ops::{sin, cos, sin_cos, powf, …}`, which route through the vendored `libm` when `bevy_math/libm` is on. `crates/sim/clippy.toml` makes the std methods a build error | — |

`Event` still exists but now means **exclusively** the observer/trigger concept. Anything buffered
is a `Message`. This split is the single most common source of code that looks right and does not
compile.

## Signatures this template actually depends on

```
// bevy_ecs
Schedule::initialize(&mut World) -> Result<Option<ScheduleBuildMetadata>, ScheduleBuildError>
ScheduleGraph::conflicting_systems(&self) -> &ConflictingSystems   // call after build
Schedules::remove(impl ScheduleLabel) -> Option<Schedule>          // needs a CONCRETE label
                                                                    // type; `&dyn ScheduleLabel`
                                                                    // does not implement it and
                                                                    // `.intern()` cannot be
                                                                    // called on a trait object
ScheduleBuildSettings { ambiguity_detection: LogLevel,             // DEFAULT IS LogLevel::Ignore
                        auto_insert_apply_deferred: bool,          // default true
                        use_shortnames: bool, hierarchy_detection: LogLevel, .. }

// bevy_time
Time::<Fixed>::from_hz(f64)              // default is 64 Hz, not 60
TimeUpdateStrategy::FixedTimesteps(u32)  // App::update() runs the fixed loop exactly n times
Time::<Virtual>::set_max_delta(Duration) // default 250ms => at most 16 fixed steps per frame

// bevy_image
Image::new_target_texture(width: u32, height: u32, format: TextureFormat,
                          view_format: Option<TextureFormat>) -> Image
// sets TEXTURE_BINDING | COPY_DST | RENDER_ATTACHMENT.
// Reading it back additionally requires |= TextureUsages::COPY_SRC.

// bevy_render::gpu_readback
Readback::texture(Handle<Image>) -> Readback           // component
struct ReadbackComplete { entity: Entity, data: Vec<u8> }  // EntityEvent, Deref<Target=Vec<u8>>
// Fires EVERY rendered frame while the component is present. Keep the LATEST, not the first.
```

## Behaviours that are easy to get wrong

- **The first `App::update()` runs `Startup` but advances the fixed loop ZERO times**, because the
  virtual clock has no delta yet. Measured on 0.19. `sim::replay::headless_app` absorbs this
  warm-up so that afterwards one `update()` == exactly one tick.
- **Query iteration order is explicitly not guaranteed**, and archetype order is undocumented.
  Use the `QueryIter::sort::<L>()` family. `sort_unstable` is only safe with a total order and no
  ties.
- **`Messages<T>` is double-buffered and frame-scoped.** Messages are dropped if unread by the end
  of the frame after they were written. With `TimePlugin`, buffers swap in `First` only after at
  least one `FixedUpdate` pass. This still does not make them tick-scoped — do not route
  simulation-relevant edges through them.
- **`bevy::platform::collections::HashMap` uses a fixed-seed hasher**, unlike `std`'s. It is
  deterministic within a build but still sensitive to insertion history, so prefer `BTreeMap` for
  anything crossing a network or a snapshot boundary.
- **`Entity` indices are reused after despawn**, and the bit layout is explicitly not stable across
  releases. Never sort, serialise, or network on `Entity`.

## Feature flags that matter here

| Flag | Why |
|---|---|
| `bevy/libm` → `bevy_math/libm` → `glam/libm` | Pure-Rust transcendentals, bit-identical across platforms. **On. Leave it on.** With `default-features = false`, dropping it is a hard error: glam's own `compile_error!` says "You must specify a math backend". |
| `glam/fast-math` | Explicitly trades away bit-for-bit cross-platform identity. **Never enable.** `crates/sim/tests/boundary.rs` fails if you do. |
| `bevy`'s `default` | Is `["2d", "3d", "ui", "audio"]`. `crates/game` sets `default-features = false`, so it compiles no PBR, no glTF, no UI and no audio. Measured: 405 s -> 294 s cold `just verify`. |

## Verifying a claim about the API

Do not guess, and do not trust this file blindly either — it will age too.

```
cargo doc --open -p bevy                          # local docs for the pinned version
rg "pub fn new_target_texture" ~/.cargo/registry/src/*/bevy_image-0.19.0/src/
cargo tree -p game -e features | rg render        # what features are actually active
cargo tree -p sim  -e features | rg glam          # sim resolves separately (resolver 3)
```

Reading the vendored source in `~/.cargo/registry` is the fastest ground truth available, and it
is always the version you are actually compiling against.
