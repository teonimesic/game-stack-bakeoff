# Game loop & schedule-graph engineering — Bevy 0.19 (verified 2026-08-10)

## Fixed timestep

`Time<Fixed>` default is **64 Hz = 15,625 µs** — not 60. Bevy's rationale: 60 Hz "has the
potential for a pathological interaction with the monitor refresh rate," and 64 is a power of two
→ lossless f32/f64 conversion. `FixedUpdate` runs `overstep()/timestep()` times per frame — **0, 1,
or many**.

`Time<Virtual>` holds the spiral-of-death guard: `DEFAULT_MAX_DELTA = 250ms` — **exactly Gaffer's
0.25 s clamp**. ⇒ at most **16 `FixedUpdate` passes per frame**. There is no separate max-steps
knob; `Time<Virtual>::set_max_delta` *is* the knob.

```
Main → First → PreUpdate → RunFixedMainLoop{ BeforeFixedMainLoop,
        loop{ FixedFirst→FixedPreUpdate→FixedUpdate→FixedPostUpdate→FixedLast },
        AfterFixedMainLoop } → Update → PostUpdate → Last
```
Generic `Res<Time>` resolves to `Time<Fixed>` inside `FixedMain` and `Time<Virtual>` elsewhere.
Systems added *directly* to `RunFixedMainLoop` are **not parallelized between each other**.

**Interpolation: no first-party plugin.** Use **`bevy_transform_interpolation` 0.5.0**
(2026-06-20 → Bevy 0.19). Records `start` in `FixedFirst`, `end` in `FixedLast`, eases in
`RunFixedMainLoop` after `FixedMain`. Opt-in components (`TransformInterpolation`, …), opt-out
(`NoTransformEasing`, …), or `TransformInterpolationPlugin::interpolate_all()`.
**Avian 0.7's `PhysicsInterpolationPlugin` is explicitly built on it.**
Bevy's official example (`movement/physics-in-fixed-timestep`) shows the manual pattern and — key
point — treats `Transform` as **presentation state** with physical position in separate components
(`PhysicalTranslation`, `PreviousPhysicalTranslation`), easing with `overstep_fraction()`.
That is the sim/view split at the smallest scale.

## Schedule graph — the highest-value guardrail ships OFF by default

`ScheduleBuildSettings.ambiguity_detection` defaults to **`LogLevel::Ignore`**. Turn it on:

```rust
app.configure_schedules(ScheduleBuildSettings {
    ambiguity_detection: LogLevel::Error,
    ..default()
});
// or per-schedule, with manual sync points:
app.edit_schedule(FixedUpdate, |s| s.set_build_settings(ScheduleBuildSettings {
    ambiguity_detection: LogLevel::Error,
    auto_insert_apply_deferred: false,   // don't let sync points MASK real ambiguities
    ..default()
}));
```
⚠️ `configure_schedules` "does not apply to any custom schedules added in the future" — call it
**after** all plugins are added.

**CI gate — copy Bevy's own `tests/ecs/ambiguity_detection.rs`:**
```rust
schedule.set_build_settings(ScheduleBuildSettings {
    ambiguity_detection: LogLevel::Warn, auto_insert_apply_deferred: false,
    use_shortnames: false, ..default() });
schedule.initialize(app.world_mut()).unwrap();
total += schedule.graph().conflicting_systems().len();
```
Bevy tracks a *count* and decrements as they're fixed; for a new project **assert `== 0` from day
one**. Signatures verified for 0.19: `Schedule::initialize(&mut World) -> Result<Option<ScheduleBuildMetadata>, ScheduleBuildError>`,
`ScheduleGraph::conflicting_systems() -> &ConflictingSystems` (must be called after build).

Ordering API: `in_set`, `before`/`after` (**auto-inserts `ApplyDeferred`**),
`before_ignore_deferred`/`after_ignore_deferred`, `chain()`, `chain_ignore_deferred()`,
`run_if` (evaluated **once per schedule run**) vs `distributive_run_if` (per system —
**picking the wrong one changes outcomes**), `ambiguous_with` (document *why*, every time).

**⚠️ API changed in 0.19: `ExecutorKind` is no longer in the public `bevy_ecs::schedule` module and
`SimpleExecutor` is GONE.** Current API: `Schedule::set_executor(impl SystemExecutor)` with
`SingleThreadedExecutor` / `MultiThreadedExecutor`. `SingleThreadedExecutor` **makes no determinism
guarantee** — it removes thread nondeterminism but topological order is whatever the build produced.

Three levers, increasing strength: (a) **ambiguity-free graph** — best, preserves parallelism;
(b) single-threaded executor — weaker than it looks; (c) **`.chain()` — the only *documented*
guarantee.** For lockstep netcode, `.chain()`.

Graph build itself: `DiGraph` uses `IndexMap` + `FixedHasher`, with an in-repo test invariant
*"must preserve the order that nodes are inserted in if no removals occur"* ⇒ deterministic for a
fixed binary and fixed plugin-registration order. ⚠️ **Inference, not a documented guarantee.**

Tooling: `bevy_mod_debugdump` 0.16.0 (DOT/SVG of the graph); Bevy 0.19 ships
`bevy::dev_tools::schedule_data`.

## Determinism hazards

### Hash maps
`std::HashMap` uses `RandomState` — iteration order differs **between runs of the same binary**.
**Bevy's own `bevy::platform::collections::{HashMap,HashSet}` already default to `FixedHasher`**
(foldhash, fixed seed) — an explicit trade of HashDoS resistance for determinism.

| Need | Use |
|---|---|
| Deterministic within a platform/build | `bevy::platform::collections::HashMap` |
| Deterministic **insertion** order, cross-platform | **`indexmap` 2.14.0** |
| Deterministic **sorted** order, cross-platform, zero deps | `BTreeMap`/`BTreeSet` |
| **Anything crossing the network in lockstep** | **`BTreeMap`/`IndexMap`, or sort before iterating** |

Even `FixedHasher` maps diverge across peers if insertion history differs, and order can shift on a
`hashbrown`/`foldhash` version bump.

### Query iteration order — NOT GUARANTEED
Bevy docs, verbatim: *"Iteration order is not guaranteed."* Archetype order is not documented at
all. **Never accumulate order-dependent results (float sums, RNG draws, command spawns) in
`par_iter`** — float addition isn't associative.

Fix — sorting adapters on `QueryIter`: `sort::<L>()`, `sort_by_key::<L,K>()`,
`sort_by_cached_key`, and `_unstable` variants.
```rust
for (_, mut hp) in q.iter_mut().sort::<&SimId>() { /* deterministic */ }
```
⚠️ `sort_unstable` is safe **only** with a total order and no ties. Sort on a unique sim-owned id.

### Entity IDs
Docs: *"`Entity` should be treated as an opaque identifier… it is possible for a later entity to be
spawned at the exact same id!"* Index reused from a free list + generation bumped.
👉 **Mint your own stable `SimId`** — exactly `bevy_ggrs`'s `RollbackId`. Anything storing an
`Entity` must `impl MapEntities`.
⚠️ **Cross-system `Commands` flush order is undocumented**; `ApplyDeferred` docs warn *"modifying a
`Schedule` may change the order in which buffers are applied."* Adding an unrelated system elsewhere
can shift entity IDs.

### Floating point
Rust std math is **explicitly nondeterministic**. From `f32` docs, on `sin/cos/tan/asin/…/exp/ln/
powi/powf/cbrt/hypot`: *"The precision of this function is non-deterministic. This means it varies
by platform, Rust version, **and can even differ within the same execution from one invocation to
the next.**"*

**Guaranteed IEEE-754 exact**: `sqrt()`, `mul_add()`, `floor/ceil/round/round_ties_even/trunc/
fract/div_euclid`, and the four basic ops. Rust does **not** enable fast-math and does **not**
allow implicit FMA contraction.

**The fix is already wired into Bevy:**
```toml
# bevy_math 0.19 features
libm = ["dep:libm", "glam/libm"]   # pure-Rust bit-stable transcendentals
```
Avian 0.7 composes it as one flag:
```toml
enhanced-determinism = ["dep:libm","bevy_math/libm","bevy_heavy/libm",
                        "parry3d?/enhanced-determinism", ...]
```
— *"Enables cross-platform deterministic math… at a small performance cost."* **Not on by default.**

**glam 0.33.3**: *"By default, glam attempts to provide bit-for-bit identical results on all
platforms. Using this feature [`fast-math`] will enable platform specific optimizations that may
not be identical."* **NEVER enable `glam/fast-math`.**

### Randomness
`bevy_rand` 0.15.1 → Bevy 0.19. `Res<GlobalEntropy>` forces every system touching it to run
**serially** — that's what preserves determinism, at the cost of parallelism. Scalable pattern:
per-entity `Entropy` components forked from a global seed via `ForkableSeed`, so draw order no
longer depends on scheduling. RNG state must itself be snapshotted for rollback.

### `bevy_ggrs`'s `pitfalls.md` — the best determinism doc in the ecosystem
1. **Non-deterministic query iteration — listed as THE most common desync cause.**
2. **No `Events`/`MessageReader` in the rollback schedule** — *"`Events<T>` is not snapshotted."*
3. **No `Local<T>`** — per-system state, not snapshotted.
4. **No raw input resources** — during resimulation they hold the *current* frame's input.
5. **Unregistered state is silently lost.**
6. Don't store raw `Entity` across frames — `impl MapEntities`.
7. No `GlobalTransform` (updated in `PostUpdate`, outside the schedule).
8. `Changed<T>` fires after every rollback restore.
9. Floats deterministic on the same platform, not across — consider fixed-point.
10. Use `RollbackFrameCount`, not `Res<Time>`.

Desync tooling: `.with_check_distance(7).start_synctest_session()` (local synthetic rollback
comparing checksums 7 frames back), `DesyncDetection::On { interval: 10 }` for P2P.
⚠️ **Checksums are separately opt-in** — `.checksum_component_with_hash::<Health>()`; ggrs 0.13
removed wording implying an automatic Fletcher checksum.
⚠️ **Absent from bevy_ggrs's docs**: HashMap order, and Bevy's parallel executor / ambiguity
detection. `GgrsSchedule` is a normal schedule using the parallel executor — **`.chain()` it and
enable `ambiguity_detection` yourself.**

⚠️ **`lightyear` has NO determinism-requirements document comparable to `pitfalls.md`** — a real
gap if you pick it for a deterministic game.

## Events → Messages (0.17 rename, current in 0.19)
`Event` is now **exclusively** the observer/trigger concept; **`Message`** is the buffered one.
`Events<E>`→`Messages<M>`, `EventWriter/Reader`→`MessageWriter/Reader`, `add_event`→`add_message`,
`send`→`write`, `Trigger<E>`→`On<E>`, plus new `EntityEvent`. 0.19 adds run conditions on observers.

**Double-buffered**: messages live ~1–2 frames; *"silently dropped if unhandled by the end of the
frame after being updated."* Docs warn: *"If no ordering is applied between writing and reading
systems, there is a risk of a race condition."*

🚨 **Rule: do NOT route sim-relevant edges through `Messages` into `FixedUpdate`.** The buffer is
*frame*-scoped, not *tick*-scoped, so the number of ticks observing a message is frame-rate
dependent. [#7691](https://github.com/bevyengine/bevy/issues/7691) (messages) is **closed/fixed**,
but [**#6183**](https://github.com/bevyengine/bevy/issues/6183) *"Inputs can be missed (or
duplicated) when using a fixed time step"* is **STILL OPEN**.
👉 Use state components/resources sampled once per tick, or an explicit per-tick buffer you own and
snapshot. Every netcode crate converges on this: `PlayerInputs<T>` (ggrs), `ActionState<I>` +
`InputBuffer` (lightyear), `Action<A>` entities (`bevy_enhanced_input` 0.26).

⚠️ SubApp footgun [#23780](https://github.com/bevyengine/bevy/issues/23780) (open): `SubApp::add_message`
never schedules `message_update_system` → buffers grow forever.

## Sim/presentation split — Bevy's own render world is the reference
`RenderApp` is a `SubApp` with its own `World`; `ExtractSchedule` moves data main→render;
**mutations never flow back.** The entity mapping is worth copying verbatim:
`SyncToRenderWorld` (marker), `RenderEntity` (main→render), `MainEntity` (render→main),
`TemporaryRenderEntity`. Transplant as `ViewEntity`/`SimEntity`/`SyncToView`, spawning views
reactively via `On<Add, SimThing>` observers.

Clearest written statement — **`moonshine-save` 0.7.0** (2026-06-21):
> *"use concepts inspired from MVC to separate the aesthetic elements of the game (the 'view') from
> its logical and saved state (the 'model'). This allows the application to treat the saved data as
> the singular source of truth."* … *"Save data may be tested without a view."*

⚠️ `bevy_save` 2.0.1 is **stale (max Bevy 0.16)** — but its `capture()/apply()`,
`checkpoint()/rollback()`, and versioned `Migrate`/`Migrator` design are worth studying.

⚠️ **Bevy 0.19 wrinkle: resources are now components on singleton entities.** Snapshot code that
enumerates entities may now see resource entities. Verify your save/rollback crate on 0.19.

## Testing — the first-party primitives

Two official examples: `tests/how_to_test_systems.rs` (bare `App::new()`, no plugins) and
`tests/how_to_test_apps.rs`:
> *"By substituting `DefaultPlugins` with `MinimalPlugins`, Bevy can run completely headless…
> The upside is that the test has complete control over these resources, meaning we can fake user
> input, fake the window being moved around, and more."*
> *"Splitting a Bevy project into multiple smaller plugins can make it more testable."*

Gotcha: *"`update` needs to be called at least once for the startup systems to run."*
`MinimalPlugins` (0.19) = `TaskPoolPlugin, FrameCountPlugin, TimePlugin, ScheduleRunnerPlugin`.
⚠️ `TimePlugin` wires message-update signalling — a bare `App::new()` has **different message
lifetime semantics** than a `MinimalPlugins` app.

**🔑 THE test primitive — `TimeUpdateStrategy`:**
| Variant | Behaviour |
|---|---|
| `Automatic` | default |
| `ManualInstant(Instant)` / `ManualDuration(Duration)` | manual clock |
| **`FixedTimesteps(u32)`** | **"`App::update()` will always run the fixed loop exactly n times"** |

```rust
app.insert_resource(TimeUpdateStrategy::FixedTimesteps(1));
for _ in 0..10_000 { app.update(); }   // exactly 10,000 fixed ticks
```
⚠️ Watch the 250 ms clamp with `ManualDuration`; `FixedTimesteps(n)` sidesteps it.

`World::run_system_once` is a good assertion probe but *"not an efficient method"* and
*"Local variables are reset on every run and change detection does not work"* — if the system uses
`MessageReader` (a `Local` cursor), use `run_system_cached`.

`Stepping` (`add_schedule`, `enable`, `step_frame`, `set_breakpoint`, `cursor()`) gives
frame-by-frame, system-by-system debugging.

⚠️ **Bevy's official testing documentation is thin** — those two files plus `RunSystemOnce`. No Book
chapter. The real prior art is `bevy_ggrs`'s `SyncTestSession` and lightyear's `crates/tests`.

**`bevy_ci_testing`** (`bevy::dev_tools::ci_testing`) driven by `CI_TESTING_CONFIG` → `.ron`:
```ron
( setup: (fixed_frame_time: Some(0.015625)),      // 64 Hz
  events: [ (500, Screenshot), (1000, AppExit) ] )
```
`fixed_frame_time` is documented as *"set through the `TimeUpdateStrategy::ManualDuration`
resource"*. Events keyed by **frame number**: `AppExit`, `Screenshot`, `ScreenshotAndExit`,
`NamedScreenshot`, `StartScreenRecording`, `MoveCamera`, `Custom(String)`.

## Netcode — the defining 2026 event
**lightyear 0.27.0 (2026-06-22) switched its replication backend to `bevy_replicon`.**
> *"The goal is to reuse the wider Bevy networking ecosystem's work, avoid splitting contributor
> efforts, and benefit from Replicon's well-optimized and documented code."*

**They are no longer competitors.** The old "replicon + hand-rolled prediction" vs "lightyear's
separate engine" fork is gone. Replicon's README now marks `bevy_replicon_snap`, `bevy_timewarp`,
`bevy_replicon_repair`, `bevy_replicon_attributes`, `bevy_bundlication` as **unmaintained** — the
old prediction recipes are dead. ⚠️ replicon moved orgs → `github.com/simgine/bevy_replicon`.

| Use case | Pick |
|---|---|
| Rollback deterministic P2P / lockstep | **`bevy_ggrs` 0.22 + `ggrs` 0.13** (0.13 **fixed lockstep mode**, `max_prediction=0`) |
| Client-server authoritative + prediction | **`lightyear` 0.29** (replicon-backed) |
| Replication only, no prediction | **`bevy_replicon` 0.42.1** + `bevy_replicon_renet` 0.18 or `aeronet_replicon` 0.21 |
| Own your replication | `bevy_renet` 5.0 + `renet` 2.0 |

⚠️ **Version-alignment trap**: bevy_ggrs 0.22 → Bevy 0.19, but **`bevy_matchbox` 0.14 → Bevy 0.18**
(last substantive commit 2026-02-21). For browser P2P: use `matchbox_socket` directly (it has a
ggrs-compatible feature) without the Bevy integration.
Correction: **`naia` is not dead** — 0.25.0 (2026-05-12), pushed 2026-08-01, targets Bevy 0.19 —
but downloads are ~2 orders of magnitude below replicon/lightyear.

### Shared-simulation-crate pattern
lightyear's approach: **gate `bevy/*` render features behind your own crate's features**, don't
strip plugins at runtime:
```toml
gui2d = ["bevy/2d", "bevy/2d_bevy_render", "bevy/2d_api", "bevy/bevy_text", "bevy/bevy_ui", ...]
```
so `cargo build --no-default-features --features server` genuinely links no renderer.

🚨 **Cargo unifies features across a workspace build.** `cargo build --workspace` or a root
`cargo test` **will unify the client's `bevy/bevy_render` into the server build, silently
un-headless-ing it.** Mitigate: build with explicit `-p server --no-default-features`, keep
`default-features = false` on the shared crate's bevy dep, and verify with
`cargo tree -p server -e features | grep render`.

Steal from naia/replicon: a **protocol hash** exchanged at handshake — mismatch ⇒ rejection.

## Performance in CI

🚨 **MAJOR CORRECTION: `iai-callgrind` has been RENAMED to `gungraun`.** The GitHub repo
301-redirects. iai-callgrind last released 0.16.1 (2025-07-30); **`gungraun` is 0.19.4 (2026-07-10)**
and actively developed.
> *"Gungraun can take accurate measurements even in virtualized CI environments and make them
> comparable between different systems completely negating the noise of the environment."*

🚨 **SECOND CORRECTION: `divan` is effectively unmaintained** (0.1.21, 2025-04-10, then 16 months of
silence) while **Criterion was revived** (0.8.2, 2026-02-04). **The common "Criterion is dead, use
Divan" advice is now inverted.**

Noise numbers: GitHub runners **>30% variance** vs **<2%** bare metal; Criterion's author notes
differences "as much as **50%**" across VM allocations; Cachegrind instruction counts are
**~0.000001%** noise.

**The recipe — instruction-count gate on N deterministic ticks, on free shared runners:**
```rust
app.add_plugins(MinimalPlugins.set(ScheduleRunnerPlugin::run_loop(Duration::ZERO)))
   .insert_resource(TimeUpdateStrategy::FixedTimesteps(1))
   .insert_resource(Time::<Fixed>::from_hz(64.0));
// gungraun: Callgrind::default().soft_limits([(EventKind::Ir, 3.0)])
```
`cargo bench -- --callgrind-limits='ir=3%'` exits with code 3 on regression. Requires Valgrind
≥3.20, `[profile.bench] debug = true`, **cannot run on Windows**. Because you count instructions,
Valgrind's ~50× slowdown corrupts neither the measurement nor (time being manual) the simulation.
⚠️ **Pin the Valgrind version** — instruction counts shift between releases. This gate covers
**sim/ECS only**; GPU regressions need fixed hardware.

Honest caveat from gungraun: *"If you need only wall-clock times, Gungraun cannot help you much."*
Instruction counts are blind to cache stalls, branch mispredicts, memory bandwidth, and anything GPU.

**Frame pacing**: Bevy has **no first-party frame pacing** in 0.19 ([#1343](https://github.com/bevyengine/bevy/issues/1343)
open since 2021; [#17975](https://github.com/bevyengine/bevy/issues/17975) "Upstream bevy_framepace"
closed as duplicate, no code merged). Use **`bevy_framepace` 0.22.0** (2026-07-16 → Bevy 0.19).
⚠️ `UpdateMode::reactive()` is **not** a frame limiter — `wait` is a coarse winit timeout.
Low-latency config: `PresentMode::AutoVsync` + `desired_maximum_frame_latency: NonZero::new(1)`
+ `FramepacePlugin` + `WinitSettings::game()`.

**Profiling**: `bevy/trace_tracy` (implies `debug` in 0.19). ⚠️ **Tracy wire protocol is versioned
and an older UI HARD-FAILS against a newer client** — always
`cargo tree --features bevy/trace_tracy | grep tracy` before downloading Tracy, and pin
`tracy-client = "=0.18.3"` (→ Tracy v0.13.0) for a team.
⚠️ **`bevy_puffin` is dead** (0.4.0, 2023-04-09, pins bevy ^0.10). Use Tracy.
🆕 0.19 ships **`DiagnosticsOverlayPlugin`** — first-party draggable in-game diagnostics, obsoleting
third-party FPS-overlay crates.

Bevy's own benches use **Criterion 0.8** (not divan) and **Bevy does not gate CI on them**.
`many_cubes --benchmark` "locks camera animation to fixed timesteps for consistent runs" — copy
that pattern for stress scenes.

## The checklist
1. Sim in `FixedUpdate`; presentation in `Update`/`PostUpdate`. Sim never reads `Time<Real>`/
   `Time<Virtual>`, `ButtonInput`, `GlobalTransform`, or `Local<T>`.
2. `ambiguity_detection: LogLevel::Error` + `auto_insert_apply_deferred: false` on the sim schedule.
3. `.chain()` the sim tick.
4. **Assert zero ambiguities in CI** via `schedule.graph().conflicting_systems().len()`.
5. Intent, not input — devices → intent component in a variable-rate schedule.
6. **Never route sim edges through `Messages` into `FixedUpdate`** (#6183 still open).
7. Sort every order-sensitive query on a stable unique sim-owned `SimId`; `sort`, not `sort_unstable`.
8. `BTreeMap`/`IndexMap` for anything crossing the network.
9. Enable `bevy_math/libm`; **never `glam/fast-math`**. Prefer `sqrt`/`mul_add`/`floor`.
10. No `par_iter` reductions in the sim.
11. Seed and snapshot the RNG.
12. Mint a `SimId`; `impl MapEntities`.
13. Two-way sim↔view index mirroring `bevy_render::sync_world`. One-way data flow.
14. Test headlessly with `MinimalPlugins` + `TimeUpdateStrategy::FixedTimesteps(1)`.
15. **Ship a checksum + replay harness early** — hash sim state per tick, record inputs, replay,
    assert identical checksum sequence. **That one test catches most of items 5–12.**
16. Gate CI on instruction counts (gungraun) over N deterministic ticks.
