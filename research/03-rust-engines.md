# Rust game engines for agent-driven dev (verified 2026-08-10)

## Bevy 0.19.0 — released 2026-06-19

Release cadence has stretched from ~3mo to 3.5–5mo: 0.15 (2024-11-29), 0.16 (2025-04-24),
0.17 (2025-09-30), 0.18 (**2026-01-13**), 0.18.1 (2026-03-04), 0.19 (2026-06-19).
0.20 milestone open, **no due date**. Repo: 47,563★, 3,391 open issues.

Feature highlights by release:
- 0.15 Required Components; 0.16 ECS Relationships, GPU-driven rendering, systems return `Result`
- 0.17 Event/Observer overhaul (`Trigger`, `EntityEvent`, `Message`, `OnAdd`→`Add`),
  `hotpatching` feature, `UiTransform` replacing `Transform` in UI, Solari raytracer
- 0.18 **cargo feature collections `2d`/`3d`/`ui`** (compile only what you need),
  **first-party screenshot + video recording plugins**
- 0.19 **BSN (Bevy Scene Notation)** via `bsn!` macro (code-driven only; `.bsn` asset format
  deferred), Scene Components, **Resources-as-Components**, **Render Graph as ECS Schedules**
  (deleted the `RenderGraph`/`Node` trait), 2.6× `many_cubes` speedup, GPU light clustering (20×)

**No 1.0 roadmap exists.** cart's on-record estimate is still "a year or two away" (2023,
unrevised). The notable 2026 governance event is Discussion #21838 — a long-time user quit over
unrelenting breaking changes; cart acknowledged he "mismanaged" BSN/UI through perfectionism and
scope creep and announced 2026 restructuring around "trustable processes."

**No official editor.** `bevy_editor_prototypes` was **ARCHIVED 2026-04-16**; work moved into
the main repo. Community successor is [Jackdaw](https://github.com/jbuehler23/jackdaw) (379★,
Bevy 0.19) — self-described "very early in dev."

### Compile time — measured, and getting WORSE
From Bevy's own metrics service (https://metrics.bevy.org), method
`hyperfine --prepare 'cargo clean' -- cargo build --jobs N --release --example breakout`:

| Metric (Linux x86_64) | 2026-02-09 | 2026-08-07 | Δ |
|---|---|---|---|
| Clean release, 16 jobs | 88.1 s | **107.3 s** | **+22%** |
| Clean release, 8 jobs | 128.9 s | **157.6 s** | **+22%** |
| Native binary | 138 MB | 182 MB | +31% |
| Wasm optimized | 19.9 MB | **23.3 MB** | +17% |

Open issue #23642 (Apr 2026): **"Rendering makes up 75% of compile time."** The 0.18 feature
collections are the mitigation. Incremental dev rebuilds cluster ~10–15 s with a good linker.

**Hot-patching does not rescue this.** Upstream `hotpatching` feature (0.17+, Dioxus subsecond)
is buggy: #24832 linker issue, #22334 doesn't work for workspaces, #21846 stack overflow on large
system bodies. Documented limits: **binary crate only, no Wasm, and it will not reload if a
system's parameters change** — which is exactly what an agent editing code does most often.
`bevy_simple_subsecond_system` is stale (0.2.0, 2025-06-02) — superseded, don't use.

### THE KILLER AGENT FEATURE: Bevy Remote Protocol + `bevy_brp_mcp`

`bevy_brp_mcp` **v0.22.2 (2026-07-29), tracks Bevy 0.19**, repo `natepiano/bevy_brp` (67★,
**0 open issues**). MCP server over BRP (JSON-RPC/WebSocket into a live ECS world).

Tools: `brp_list_bevy`, `brp_launch`, `world_query`, `world_find_entities_by_name`,
`world_get_components_watch`, `world_mutate_components`, `world_trigger_event`,
`read_log` (stdout to temp files the agent can read), `brp_type_guide`.
With the `bevy_brp_extras` plugin: **`brp_extras_screenshot`** (full window / camera viewport /
entity crop), **`brp_extras_send_keys`**, mouse/trackpad gestures,
`brp_extras_get_diagnostics` (FPS/frame time), graceful shutdown.

Setup: `cargo install bevy_brp_mcp`, enable the `bevy_remote` feature,
`add_plugins(RemotePlugin::default())`, register the stdio server with the agent.

**This closes the runtime-blindness gap** — the agent can launch the game, drive input,
screenshot, and inspect/mutate live ECS state. **No other engine offers this to a Rust agent.**
(`bevy_debugger_mcp` also exists but only reached v0.1.4 — far less mature.)

### Headless rendering — strong
Official examples in `examples/app/`: `headless.rs`, `headless_renderer.rs`,
`externally_driven_headless_renderer.rs`, `no_renderer.rs`, `without_winit.rs`,
`render_recovery.rs`. `Screenshot` component + `ScreenshotCaptured` observer is first-party.
**`bevy_ci_testing` cargo feature exists in 0.19** (frame-N screenshot harness).
`examples/testbed/{2d,3d,ui,full_ui}.rs` are deterministic visual fixtures.
⚠️ A `TestPlugins` plugin group could **not** be verified upstream — `MinimalPlugins` definitely
exists; treat `TestPlugins` as unconfirmed.

### THE #1 RISK: API churn vs stale training data
In the last 4 releases: `OnAdd`→`Add`; Events split into `Event`/`EntityEvent`/`Message` with a
new `Trigger` trait; `Transform`→`UiTransform` in UI; `RenderGraph`/`Node` trait **deleted**;
Resources reimplemented as components; an entirely new scene language (BSN).

The Chier Hu survey (Jun 2026) documents the failure mode precisely: the model is
*"(nearly) always wrong on unstable APIs without external grounding"* and *"will happily
acknowledge the correct version, read the correct documentation, and promptly implement code for
an **imagined** Bevy 0.17 API."*

**Grounding assets — verified absent:**
`llms.txt` / `llms-full.txt` **404s on all 7 candidate URLs** (bevy.org, docs.rs/bevy,
godot-rust book, docs.godotengine.org, taintedcoders, bevy-cheatbook).
**No curated LLM docs bundle exists for Bevy or godot-rust. We have to build one.**
Bevy Cheat Book self-marks as **outdated (documents 0.12)** — do not point an agent at it.
Third-party Claude Skills for Bevy exist but **target unverified versions** — an 0.16-era skill
is worse than nothing. Ecosystem crates trail the engine by 1–2 releases.

### Cross-platform
- Windows/macOS/Linux: works out of the box, wgpu (Vulkan/D3D12/Metal/GL/WebGL2/WebGPU).
  0.19 added partial bindless on Metal + typed render-recovery error policies.
- **iOS: supported but bumpy, actively so.** Ships a real `bevy_mobile_example.xcodeproj`.
  Open bugs today: #25335 atmosphere unsupported on some iOS devices, #25198 GPU light clustering
  not disabled on iOS (~45% more CPU w/ one point light), #23453 **memory leak** transforming
  Mesh2d/Sprites, #13822 no IME. Recently fixed: uninitialized-drawable pink screen,
  simulator rendering, uncatchable panics. Discussion #20998 notes there simply aren't enough
  mobile Bevy devs to debug these. **You will hit platform bugs and be the one filing them.**
- Wasm: works, single-threaded, 23.3 MB optimized bundle (heavy). **WebGPU is now on by default
  in Safari for macOS/iOS/iPadOS/visionOS 26.**
- ⚠️ **wgpu 30.0.0 shipped 2026-07-01**; Bevy 0.19 predates it. Each wgpu major historically
  produces a wave of backend-specific regressions. Expect migration pain in 0.20.

### Commercial track record — weak
**Tiny Glade** remains the flagship, but it uses **Bevy ECS with a custom renderer**, not the
full engine, and shipped in 2024. Other 2026 claims (Toroban, Nominal, Foresight) are
secondary-source only and **could not be verified**. bevy.org/assets is almost entirely hobby
projects, many pinned to 0.4–0.15.

`bevy_ecs` standalone is healthy: **7,813,766 downloads vs 6,688,810 for `bevy`** — the ECS is
pulled *more* than the engine, corroborating significant standalone use.

## Godot 4.7 + gdext 0.5.5

- **Godot 4.6** (2026-01-26): Jolt promoted to default for new 3D projects; SSR rewrite;
  LibGodot (embed engine as a library). **Godot 4.7** (2026-06-18): AreaLight3D, **HDR output**
  on Windows/macOS/iOS/visionOS, SDL3 controllers on macOS/iOS. 4.7.1 (07-14), 4.8 dev snapshots.
- Godot Foundation's 2026 vision statement: "best tool for **small to medium-size teams**",
  "a smaller, solid engine is better than a large, brittle one." **No mention of AI/LLM tooling
  or third-party bindings like Rust.**
- **gdext `godot` v0.5.5 (2026-08-09)**, repo 5,078★, pushed 2026-08-10. Supports Godot API
  4.6 and 4.7 (`api-4-7` since 0.5.4). v0.5.3 **dropped the bindgen/LLVM dependency** for a JSON
  workflow — meaningfully simpler CI. Book states plainly: "expect occasional breaking changes."
- **Testing is gdext's strongest agent story**: `godot --headless` is first-class; gdext's own
  `itest` suite runs Rust + GDScript integration tests in CI; v0.5.3 added `#[itest(editor)]`
  running under `-e --headless`. Third-party `gd-rehearse`, `godot-testability-runtime`.
- ⚠️ **Hot reload works but crashes**: godot#115496 "Godot Crashes on Hot Reload with Rust gdext
  Extension" affects **4.6.stable and 4.7.stable**; gdext #434 "Hot reload final steps" still open.
- ❌ **DEALBREAKER FOR iOS: gdext iOS, Android, and Wasm support are explicitly labeled
  EXPERIMENTAL** in the README — "lack documentation and tooling." A WASM export CLI is
  roadmapped, not shipped. **If iOS matters and you want Rust, Godot+Rust is the *riskier*
  choice, not the safer one.**
- Console via **W4 Games** (published pricing): Starter (<$300k rev) **$800/yr single platform,
  $2,000/yr all**; Pro (>$300k) **$4,000 / $10,000**. Switch, Switch 2, PS5, Xbox Series X|S.
  ⚠️ Console templates support **Godot 4.5/4.4 (+4.3)** — lag ~2 releases behind 4.7.
  ⚠️ **No mention of GDExtension/Rust support anywhere on the W4 page — unverified and a
  material risk** if console + Rust are both required.

## Fyrox 1.0.1

- **Fyrox 1.0.0 released 2026-03-24** (~7 years in). Repo 9,495★, pushed 2026-08-06, only 60 open
  issues. Ships **FyroxEd**, a native scene editor — its structural advantage over Bevy.
- **The killer number: 70,267 all-time downloads vs Bevy's 6,688,810 — ~1/100th.** For an agent
  that means ~100× less training-data coverage and far fewer examples.
- **No commercial game shipped with Fyrox could be verified, ever.** Claims of "battle-tested"
  trace to a low-quality aggregator, not a primary source.
- Only Rust engine with a **1.0 stable-API commitment** — the direct antidote to Bevy's churn —
  but adoption is too thin to matter for training density.

## Ecosystem health signals
- **"This Month in Rust GameDev" is DEAD.** Last issue #52, June 2024; repo last commit
  2025-03-05; **gamedev.rs fails DNS resolution entirely.** Maintainer burnout (issue #50).
- "This Week in Bevy" — most recent issue found is **2026-01-12**; may or may not be dormant
  (CMS-driven, uncertain).
- `godot-bevy` (Bevy ECS driving Godot 4, 527★) is interesting but its latest release still
  depends on `bevy_ecs ^0.18` / `godot ^0.4.5` — one major behind both.

## Compiler-as-harness — the core trade
Multiple 2026 writeups argue the Rust compiler is an ideal agent harness (types as
machine-checkable contracts, structured/actionable diagnostics, uniform
`cargo check|test|fmt|clippy`). Best-known: ["The Compiler Is the Harness"](https://medium.com/@ashbenen/the-compiler-is-the-harness-why-agentic-coding-works-so-well-in-rust-730bca7faf8e)
(2026-01-15) — ⚠️ **explicitly no empirical data, argumentative not measured.**
A GitHub analysis (Jan 2026) reportedly found **94% of compilation errors in LLM-generated code
are type-check failures** — ⚠️ secondary source only, could not verify primary.

**Net: Rust gives the best feedback *signal* and the worst feedback *latency*.
That trade-off is the entire decision.**

## Summary table

| | Bevy 0.19 | Godot 4.7 + gdext 0.5.5 | Fyrox 1.0.1 |
|---|---|---|---|
| API stability vs stale training data | ❌ **worst** | ⚠️ moderate | ✅ 1.0 commitment |
| Ecosystem / training mass | ✅✅ 6.7M dl, 47.5k★ | ✅✅ Godot huge; gdext 382k dl | ❌ 70k dl |
| Runtime observability for agents | ✅✅ **BRP + bevy_brp_mcp** best in class | ✅ headless + gd-rehearse | ❌ none |
| Headless + screenshot CI | ✅✅ 5 official examples, `bevy_ci_testing`, Pixel Eagle | ✅ `--headless` | ❓ |
| Iteration latency | ❌ 10–15 s incr / 105–158 s clean, **worsening** | ✅ GDScript instant; ⚠️ Rust hot-reload crashes | ⚠️ |
| Editor | ❌ none (Jackdaw alpha) | ✅✅ mature | ✅ FyroxEd |
| iOS | ⚠️ works, active bug tail | ❌ **gdext iOS experimental** | ❓ |
| Console | ❌ none | ✅ W4 $800–10k/yr, **Rust support unverified** | ❌ |

## Explicitly NOT verified (do not treat as established)
1. Whether "This Week in Bevy" still publishes after 2026-01-12
2. Any commercial game shipped on **full** Bevy in 2026
3. Any commercial game shipped on Fyrox, ever
4. Whether **W4 Consoles supports Rust GDExtension** on console targets
5. The GitHub "94% of LLM compile errors are type errors" figure
6. Existence of a `TestPlugins` group upstream
7. Which Bevy version third-party Claude Skills target
