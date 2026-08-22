# Stack decision

**Verdict: Rust + Bevy 0.19 for the client/simulation, Rust for the authoritative realtime
server, Elixir/Phoenix 1.8.9+ for meta-services.**

Decided 2026-08-10 from the eight research briefs in this directory. The decisive criterion was
the user's core ask: *"E2E tests by actually rendering and verifying things happen."*

## ⚠️ Read this first

This document originally decided the stack from research alone and eliminated candidates on paper.
That was the wrong method for the question being asked, and two of the eliminations were wrong on
the facts. **Godot and Unity are both in the empirical bake-off**, on byte-identical task prompts,
with results in `eval/FINDINGS.md`. Treat the reasoning below as the *prior*, and the bake-off as
the evidence.

## How the candidates fell out (initial paper assessment)

| Stack | Outcome | Reason |
|---|---|---|
| **Godot 4.7 (GDScript)** | ⚠️ **Was eliminated on paper — WRONGLY. Now in the bake-off.** | Measured: `--headless` genuinely cannot render (`get_image()` returns null, `frame_post_draw` deadlocks) — **but windowed capture works fine** (PNG visually confirmed). The real cost is that render verification needs a display server: fine on a dev machine or a GUI CI session, not on a bare headless Linux runner without Xvfb. Material, not disqualifying. Secondary: gdext iOS/Android/Wasm are explicitly *experimental*. |
| **Unreal 5.8** | ❌ Eliminated | Multi-minute compiles, 100 GB+ engine, and **binary `.uasset` assets an agent cannot diff, review, or author**. Feedback loop 100–1000× slower than alternatives. Not OSI-licensed. UE6 transition adds instability. |
| **Zig, Stride, Flax, KorGE, O3DE** | ❌ Eliminated | Pre-1.0 churn (worst possible LLM target) / 9 months without a release / proprietary + 4% royalty / near-zero training density. |
| **Unity 6** | ⚠️ **Was excluded on licence — now in the bake-off** | Proprietary, and excluded on the open-source preference rather than on capability. Measured since: batchmode is fully automatable with an auto-resolving Personal licence and NUnit XML output. It has the **highest LLM training density of any engine**, so excluding it untested was leaving the most agent-friendly option unmeasured. |
| **MonoGame 3.8.5** | 🥉 Third | Genuinely strong: **the only stack with first-party console support for PS4/PS5/Switch/Xbox**, permissive Ms-PL, no editor and no binary scene format (100% of the game is C# text), `IsFixedTimeStep` 60 Hz determinism nearly free, plain xUnit tests. But 3D is basic, visual testing is DIY offscreen capture, and C# doesn't share a simulation crate with a Rust realtime server. |
| **TypeScript + three.js** | 🥈 Runner-up | **The best-evidenced verification loop of anything surveyed** — three.js runs WebGPU headless pixel-diff CI on CPU-only runners via lavapipe today, plus a shipped deterministic-injection harness (seeded `Math.random`, frozen `Date.now`/`performance.now`, single-shot `requestAnimationFrame`), plus an llms.txt. Highest training density. **Lost on the user's other constraints**: the flagship "ship a real game in TS" proof (Vampire Survivors) *migrated off Phaser to Unity for performance*; console is effectively unavailable without a publisher-funded rewrite; and WebGPU-inside-WKWebView on iOS is unverified. |
| **Bevy 0.19** | ✅ **Selected** | See below. |

## Why Bevy wins

1. **Headless rendering is first-class and already proven in production CI.** Five official
   examples (`headless.rs`, `headless_renderer.rs`, `externally_driven_headless_renderer.rs`,
   `no_renderer.rs`, `without_winit.rs`); a first-party `Screenshot` component +
   `ScreenshotCaptured` observer; the `bevy_ci_testing` feature driven by a `.ron` config keyed on
   **frame number**; and Bevy's own CI pipeline uploading example screenshots to Pixel Eagle for
   visual regression. **No template has ever wired this up** — that is precisely our gap to fill.
2. **`bevy_brp_mcp` gives the agent eyes and hands, and nothing else in Rust does.** v0.22.2
   (2026-07-29) tracks Bevy 0.19, 0 open issues. Over the Bevy Remote Protocol the agent can
   `brp_launch` the game, `world_query`/`world_mutate_components` a live ECS world,
   `brp_extras_send_keys` to drive input, `brp_extras_screenshot`, `brp_extras_get_diagnostics`
   for FPS, and `read_log`. This closes the runtime-blindness gap the Chier Hu survey named as
   the field's central failure.
3. **The compiler is the harness.** Rust gives the best feedback *signal* — and the measured cost
   on this machine is acceptable: **3m46s cold, 3.8s incremental** (M3 Max, 16 cores, rustc 1.97.1).
4. **One simulation crate shared by client and authoritative server** — exactly the architecture
   the user chose, and impossible in the C#/TS options.
5. **The determinism recipe is fully documented and enforceable**: `TimeUpdateStrategy::FixedTimesteps(n)`
   for exact tick counts in tests, `ambiguity_detection: LogLevel::Error`, query `sort::<SimId>()`
   adapters, `bevy_math/libm` for cross-platform transcendentals, `bevy_rand` forkable seeds, and
   `bevy_ggrs`'s `SyncTestSession` for synthetic rollback checksum comparison.
6. 2D **and** 3D, macOS/iOS/Windows, MIT/Apache-2.0, and the ECS (`bevy_ecs`, 7.8M downloads —
   *more* than the engine itself) is usable standalone on the server.

## The risk we are accepting, and the mitigation

**Bevy's API churn is the worst in the field and it is the #1 threat to agent success.** In four
releases: `OnAdd`→`Add`; Events split into `Event`/`EntityEvent`/`Message`; `Transform`→`UiTransform`
in UI; the `RenderGraph`/`Node` trait **deleted**; Resources reimplemented as components; an
entirely new scene language (BSN). The documented failure mode is that a model *"will happily
acknowledge the correct version, read the correct documentation, and promptly implement code for an
**imagined** Bevy 0.17 API."*

And **no grounding asset exists** — `llms.txt` 404s on all seven candidate URLs (bevy.org,
docs.rs/bevy, godot-rust book, taintedcoders, bevy-cheatbook). The Bevy Cheat Book self-marks as
documenting **0.12**. Third-party Claude Skills target unverified versions.

**Mitigation, and it is the template's second reason to exist:** ship a version-pinned, in-repo API
grounding pack for Bevy 0.19 — the exact idioms this template uses, a "remembered 0.17 → actual
0.19" correction sheet, and compile-checked doctest examples so the grounding cannot silently rot.
**This is the highest-leverage thing in the whole template**, and the eval suite's B1 task exists
specifically to measure whether it works.

Secondary risks accepted: no console path (user rated aspirational); iOS works but carries an
active bug tail; wgpu 30.0 migration pain expected in Bevy 0.20; no official editor.

## Locked component choices

| Concern | Choice | Note |
|---|---|---|
| Engine | `bevy = "0.19"` | pin exactly; feature collections `2d`/`3d`/`ui` to cut compile time (rendering is 75% of it) |
| Math determinism | `bevy_math/libm` | **never** `glam/fast-math` |
| Physics | `avian` 0.7 + `enhanced-determinism` | composes libm across parry/bevy_heavy |
| Interpolation | `bevy_transform_interpolation` 0.5.0 | no first-party equivalent; Avian builds on it |
| RNG | `bevy_rand` 0.15.1 | per-entity `Entropy` forked from a global seed |
| Rollback / lockstep | `bevy_ggrs` 0.22 + `ggrs` 0.13 | 0.13 first version with working lockstep (`max_prediction=0`) |
| Client-server + prediction | `lightyear` 0.29 | now **replicon-backed** since 0.27 — no longer a competing stack |
| Transport | `quinn` 0.11.11, QUIC DATAGRAM | behind our own `Transport` trait — see below |
| Wire format | `postcard` (Rust↔Rust), protobuf (Elixir↔Rust) | **`bincode`'s repo is archived** |
| DST | `turmoil` 0.7.2 | 🚨 **cannot simulate QUIC** — hence the `Transport` trait from commit one |
| Meta-services | Phoenix **≥1.8.9** | CVE-2026-56811, CVSS 8.7, unlimited channel joins = lobby DoS |
| Orchestration | Agones v1.59.0 + official `agones` Rust crate | matchmaker written in Elixir; **Open Match 2 is a 59★ preview** |
| Task runner | `just` 1.58.0 | `just --dump --dump-format json` is the machine-readable manifest |
| Test runner | `cargo-nextest` 0.9.143 | |
| Perf gate | **`gungraun` 0.19.4** | renamed from `iai-callgrind`; instruction counts, ~0% CI noise |
| Bench | **Criterion 0.8.2** | **not divan — divan is unmaintained since 2025-04; the common advice is inverted** |

## Two architectural decisions that are cheap now and expensive later

1. **A `Transport` trait between simulation and wire, from the first commit.** `turmoil` — the
   best deterministic-simulation-testing tool — simulates UDP but **not QUIC**. Implement the trait
   over `quinn` for production and `turmoil::net::UdpSocket` for tests. Also buys the WebSocket:443
   fallback needed for networks that block UDP.
2. **Gate `bevy/*` render features behind our own crate features**, never strip plugins at runtime.
   🚨 **Cargo unifies features across a workspace build** — a root `cargo test` will unify the
   client's `bevy/bevy_render` into the server build and silently un-headless it. Verify with
   `cargo tree -p server -e features | grep render`.

## What still needs empirical settling
The paper case for Bevy is strong on verification and weak on API churn. **The bake-off task B1
("API fluency under churn") measures exactly that**, and the instruction experiment tests whether
in-repo doc grounding closes the gap. If grounding does *not* work, the honest fallback is
TypeScript + three.js, which loses on performance ceiling and console but wins on training density.
