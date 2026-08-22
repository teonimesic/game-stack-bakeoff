# Game testing state of the art (verified 2026-08-10)

## The signal hierarchy — rank your verification by reliability

1. **Headless state assertions** — most reliable, fastest, no GPU
2. **Replay / rollback state checksums** — catches determinism regressions wholesale
3. **Static determinism checks** (schedule ambiguity, lint) — free, requires running nothing
4. **Perceptual image diffs** — advisory, GPU-dependent
5. **VLM assertions** — last resort, see the accuracy numbers below

## 🚨 VLM oracles are near chance on the things that matter

**Four independent 2025–26 studies put VLM game-test oracles at ~50% accuracy, and near chance
on temporal properties.**

This is the strongest argument against the "let a vision model judge the screenshot" design that
`godogen` and `game-creator` both use, and it validates deterministic pixel assertions instead.
A VLM can tell you *"this looks like a menu"*; it cannot reliably tell you *"the ball reversed
direction on frame 47"*. Use pixel invariants and relational assertions for anything temporal.

## How real graphics projects do image comparison

- **wgpu and Vello both use [`nv-flip`](https://github.com/gfx-rs/nv-flip-rs)** — Rust bindings to
  NVIDIA's FLIP perceptual metric. Real in-tree thresholds range `Mean(0.005)` to `Mean(0.05)`,
  with comments literally reading `// Bounded by Apple A9`. That is what an honest cross-device
  tolerance looks like: derived from the weakest device you support, not guessed.
- **Bevy sidesteps GPU nondeterminism entirely.** Its Pixel Eagle pipeline compares only
  `os: "<equal>"` — same-OS runs against same-OS baselines — and posts an **advisory PR comment**
  rather than failing the build. 97 PRs carry the `M-Deliberate-Rendering-Change` label.
  ⇒ **Nobody hard-fails CI on cross-platform pixel equality.** Our template's approach (exact
  reproducibility within a platform, tolerance-based golden diff, invariants preferred over
  goldens) matches the state of the art.
- **Lavapipe in GitHub Actions is proven twice**: wgpu pins Mesa 26.1.3; Vello and Bevy use
  `ppa:kisak/turtle`. ⚠️ **macOS has no software rasterisation path — real Metal only.** So
  macOS CI needs a real GPU runner, and Linux CI can run entirely on CPU.

## Determinism oracles

- **GGRS `SyncTestSession` is a drop-in determinism oracle.** The canonical harness is
  `bevy_ggrs/tests/common/mod.rs`: `MinimalPlugins` + `TimeUpdateStrategy::ManualDuration` +
  SyncTest + an `app.update()` loop. It runs synthetic rollbacks locally and compares checksums,
  so you get desync detection without a network.
- **Bevy's `tests/ecs/ambiguity_detection.rs` asserts zero system-order ambiguities** — a
  determinism check that requires *running nothing*. Cheapest useful test in the whole space.
  (Implemented in our template as `fixed_update_schedule_has_no_ambiguities`.)

## Corrections to widely-cited claims

- **`iai-callgrind` is now `gungraun`** (0.19.4). Confirmed independently a second time.
- **Meta's Hermit is NOT abandoned** — active through 2026-08, contradicting a widely-cited 2024
  survey.
- **`bevy_mod_debugdump` is a visualizer, not a profiler.**

## Confirmed ecosystem gaps
- **No golden-image testing crate exists for Bevy.** (`bevy_mod_screenshot_test` v0.2.0 has 61
  downloads and is two weeks old.) Our harness fills this.
- **No open-source project hard-fails CI on frame-time regression.** Everyone treats wall-clock
  perf as advisory; the only credible CI gate is instruction counts (gungraun).
