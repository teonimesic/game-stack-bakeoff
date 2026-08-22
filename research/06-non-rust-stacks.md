# Non-Rust stacks (verified 2026-08-10 against npm/GitHub APIs and engine source)

## THREE FINDINGS THAT DECIDE THIS

### 1. 🚨 Godot's `--headless` CANNOT RENDER — structural, not a config gap
Verified by reading engine source: `servers/display/display_server_headless.h` exposes exactly
**one** rendering driver, `"dummy"`. `--headless` == `--display-driver headless --audio-driver Dummy`.

So headless Godot runs logic, scripts, and gdUnit4 scene-runner input simulation, but produces
**no framebuffer** — no `get_viewport().get_texture().get_image()`, no screenshot diffing. Visual
regression requires a real display driver under Xvfb (**which does not exist on macOS**).

Corroborating: a GitHub search for Godot visual-regression tooling returns only **0-star hobby
repos**. There is no GUT/gdUnit4 equivalent of `toHaveScreenshot()`.

**This disqualifies Godot from the template's single most important requirement.**

### 2. ✅ three.js runs WebGPU headless pixel-diff CI on CPU-only runners TODAY
Read from their actual CI (`.github/workflows/ci.yml`, `test/e2e/puppeteer.js`):
- installs `mesa-vulkan-drivers` + `xvfb`
- Puppeteer flags: `--enable-unsafe-webgpu --enable-features=Vulkan --disable-vulkan-surface --ignore-gpu-blocklist`
- `VK_DRIVER_FILES=/usr/share/vulkan/icd.d/lvp_icd.x86_64.json` (**lavapipe = software Vulkan**)
- pixel-diffs **~400 examples** against committed reference screenshots at **0.1 threshold**,
  sharded across 5 parallel runners, uploading diff artifacts on failure. **No GPU required.**

Even better — `test/e2e/deterministic-injection.js` monkey-patches `Math.random` (seeded sine
PRNG), `Date.now`, `performance.now` (→ constant 0), and `requestAnimationFrame` into a single-shot
deterministic frame. **That is exactly the deterministic-verification primitive an agent loop
needs, existing as maintained production code.**

three.js also ships `build-llms` generating an **llms.txt** — the grounding asset Bevy lacks.

### 3. ⚠️ The flagship "you can ship a real game in TS" proof migrated OFF TypeScript
**Vampire Survivors** shipped early access on Phaser, then **switched to Unity at v1.6**
explicitly to improve performance before console rollout. Treat web-stack performance claims for
entity-dense 2D with real skepticism — budget a native rewrite past ~10k active entities.
(CrossCode *did* ship JS to Switch/PS4/PS5/Xbox — via a bespoke publisher-funded JS compilation
effort, not an off-the-shelf pipeline.)

## Scorecard

### Godot 4.7.1 (MIT) — 4.7 released 2026-06-18, 4.7.1 on 2026-07-14
| | GDScript | C#/.NET |
|---|---|---|
| Platforms | mac/iOS/Win/Linux/Android/Web | mac/Win/Linux stable; **iOS + Android experimental since 4.2**; **Web export impossible** |
| Headless logic test | **A** — GUT 9.6.1 + gdUnit4 6.2.x, CLI runners, JUnit XML, official GH Action | **A** + xUnit/NUnit on pure-logic assemblies |
| **Visual test** | **D** — see finding #1 | **D** |
| Static checking | **C** — typing exists but **OFF BY DEFAULT**; no nested generics (`Array[Array[int]]` unsupported); must manually enable `UNTYPED_DECLARATION`/`UNSAFE_*` warnings | **A** — full Roslyn |
| Iteration | **A** — no compile step | B — 2–10 s |
| LLM density | **C+** — 115k★ but the **3.x→4.x API break is the dominant agent failure mode** (models emit `KinematicBody`, `export var`, `yield` into 4.x) | **B** — but agents leak *Unity* idioms (`MonoBehaviour`, `Update()`) |

Determinism: fixed `_physics_process`; Movie Maker (`--write-movie`) gives guaranteed frame pacing
+ PNG-sequence output, but is undocumented for testing and **needs a real display driver**.

Shipped 2026: Slay the Spire 2, Road to Vostok (migrated from Unity), Battlefield 6's Portal map
editor, Cassette Beasts, Until Then.

⚠️ **W4 Games console**: public pages state no pricing, no confirmed console list, and **nothing
about whether C#/.NET games can ship to console**. .NET on consoles historically needs a
vendor-specific runtime. Assume GDScript-only for console until confirmed. Unresolved risk.

### TypeScript / Web
| Engine | Version | License | Headless test | Visual test | Determinism | LLM |
|---|---|---|---|---|---|---|
| **three.js** | **r185.1** (2026-07-01) | MIT | A | **A — proven WebGPU pixel-diff in CI** | **A — shipped injection harness** | **A**, ships llms.txt |
| **Babylon.js** | 9.20.0 (2026-08-06) | Apache-2.0 | A | A (own visual suite) | B | A− |
| **Phaser** | 4.2.1 (2026-07-09) | MIT | A | B | B | **A** |
| PlayCanvas | 2.21.3 (2026-07-29) | MIT | A | B | B | B |
| Pixi.js | 8.19.0 (2026-06-04) | MIT | A | B | n/a | A− |
| Excalibur.js | 0.32.0 (2025-12-23) | BSD-2 | **A** | **A** | **A** fixed timestep | **D** — 2.3k★, pre-1.0 |
| react-three-fiber | 9.7.0 (2026-07-31) | MIT | A | A | B | B+ |

Phaser 4 = all-new node-based **WebGL** renderer, **no WebGPU**. Vendor shipping AI tooling
("Phaser Game Agent"). Excalibur's devDeps include `vitest`, `@vitest/browser-playwright`,
`pixelmatch`, `puppeteer`, `playwright`, `excalibur-jasmine` (`toEqualImage` canvas matcher) —
per-unit-test pixel assertion in a real browser — but pre-1.0 with thin training data.

**WebGPU on Apple is now real.** MDN BCD `api/GPU.json`: `safari: 26`, `safari_ios: mirror`,
`chrome: 144`, `chrome_android: 121`, `firefox: 141` (Windows only). WebKit confirms WebGPU
shipped **enabled-by-default in Safari 26 for macOS, iOS, iPadOS, visionOS**.

⚠️ **UNVERIFIED AND LOAD-BEARING: whether WebGPU is exposed inside WKWebView** (i.e. inside a
Tauri/Capacitor iOS app) as opposed to Safari.app. MDN marks `webview_ios` as `"mirror"` — that's
BCD's automated default, not a tested assertion. **Probe with a 20-line WKWebView test calling
`navigator.gpu.requestAdapter()` on a real iOS 26 device before committing.** Fallback: WebGL2,
universally available in WKWebView.

Native wrappers: **Electron 43.3.0** (mac/Win/Linux, **no iOS**, bundles Chromium →
**your CI browser and shipped browser are the same binary**, which is what makes screenshot
baselines meaningful); **Tauri v2 2.11.5** (adds iOS, but mac/iOS use WKWebView).

⚠️ **Playwright + WebGPU headless is NOT proven** — the lavapipe recipe is proven under
**Puppeteer**. Playwright docs say nothing about WebGPU; open issues since 2022 (#11627, #39762).
Playwright's `toHaveScreenshot()` (with `maxDiffPixels`/`threshold`/`--update-snapshots`) is
excellent and worth using, but verify the WebGPU flags empirically on day one.

**Console for web: poor and bespoke.** No supported "publish your Phaser game to Switch" path.

### C# beyond Godot — the dark horse holds up
| Engine | Version | License | Console | Headless test | Visual test | Determinism |
|---|---|---|---|---|---|---|
| **MonoGame** | **3.8.5** (2026-07-15) | **Ms-PL** (OSI-approved) | **A — PS4/PS5/Switch/Xbox, official, NDA-gated** | **A** — logic is plain C#, xUnit/NUnit directly | **C** — DIY offscreen render-target capture | **A** — `IsFixedTimeStep` 60 Hz default |
| FNA | 26.08 (2026-08-01) | Ms-PL-ish | **A** — Xbox/Switch/PS5/mac/iOS/tvOS | A | C | A |
| Stride3D | 4.3.0.2507 (2025-11-22) | MIT | **F** | B | C | B |
| Flax | 1.12.6912 | **Proprietary EULA, 4% royalty >$250k/qtr** | via partner | C | C | B |

MonoGame 3.8.5 adds **Vulkan and DirectX 12** backends. Shipped: Stardew Valley, Celeste, Bastion,
Fez, Barotrauma. **The only stack in the survey with a first-party documented path to all three
console families.** Structural agent advantage: **no editor, no binary scene format** — 100% of the
game is C# text the agent can read and diff. Weakness: framework not engine — no scene editor, no
physics, agent must generate more code. ⚠️ Stride has **no tagged release in ~9 months** — bus-factor
risk. Flax ruled out on license + tiny corpus.

### C++
| Engine | License | Verdict |
|---|---|---|
| **Unreal 5.8** (2026-06-17) | Source-available, **not OSI**, 5% royalty >$1M | **Reject for agents.** Multi-minute compiles, 100 GB+ engine, feedback loop 100–1000× slower than any alternative. **UE6 announced 2026-05-24**, early access "late 2027-ish" — adds instability. |
| O3DE 2605.0 | Apache-2.0/MIT | Genuinely open, genuinely huge, **9.6k★** — agents will flounder |
| Cocos Creator 3.8.8 | MIT | TS over a C++ core; China-centric docs, last release 8 months ago |

**Binary assets are the C++/UE killer for agents, not just compile time.** An agent cannot diff,
review, or author a `.uasset`. Every gameplay change routes through an editor GUI it can't drive.

### Others
- **Defold** 1.13.0 — source-available (not OSI), **official Switch/PS4/PS5/Xbox**, `bob.jar`
  headless CLI. Killed by tiny Lua-Defold corpus.
- **LÖVE 11.5 — last release 2023-12-03 (2.5 years!)**. But **Balatro** shipped day-one to every
  console and sold 5M+ — proof a Lua 2D stack can reach console.
- **Heaps** (Haxe) 2.1.1 — **official Switch/PS4/Xbox**, Dead Cells (10M+), Northgard.
  Technically superb, **Haxe LLM density near-zero**.
- **Flame** (Dart) 1.38.0 — Flutter's `golden` image tests are a genuinely good visual-diff story.
  No console, weak perf ceiling.
- **libGDX** 1.14.2 — mature and testable (JVM/JUnit), **no console support documented**.
- **Zig 0.16.0 + SDL3** — pre-1.0 with breaking changes every release, **the single worst possible
  LLM target. Rule out.**
- **Unity 6** (6000.4.0f1, 2026-03-18) — Runtime Fee cancelled Sept 2024, Personal free under
  $200k. **Highest LLM density of any engine.** Excluded by the open-source preference — flagging
  explicitly as a real trade-off, not an oversight.

### SDL3 as a foundation
**SDL3 3.4.14** (2026-08-03), zlib, 16.3k★, pushed daily. **The SDL3 GPU API is real and
production-usable**: one API over **Vulkan** (Win/Linux/**Nintendo Switch**/Android), **Metal**
(macOS 10.14+, iOS/tvOS 13+), **D3D12** (Win10+, **Xbox One/Series X|S**). `SDL_shadercross` does
runtime + offline shader cross-compilation. raylib 6.0 (2026-04-23, 34.3k★), flecs 4.1.6.

"Roll your own thin engine" is viable *on paper* — pure text, no binary assets, instant headless
testing, full determinism control, and SDL3's backends *literally name Switch and Xbox*. But the
agent must author renderer, asset pipeline, scene format, physics and audio before any gameplay.
**Recommend as a fallback for a narrowly-scoped 2D game, not as the general template.**

## Verdict for our purposes

Requirement #1 is *"E2E tests by actually rendering and verifying things happen."*

- **Godot is out** — `--headless` cannot produce pixels, and there is no Xvfb on macOS.
- **TypeScript/three.js is in** — the only stack with *running, maintained, production* evidence
  of headless GPU rendering + committed reference screenshots + deterministic RNG/clock injection.
- **MonoGame is a credible dark horse** — best console record, all-text source, plain C# tests,
  but DIY visual capture.
- **Unreal/Zig/Stride/Flax/KorGE are out** on compile loop, churn, staleness, or licence.

Combined with the Rust brief (03), the real finalists are **Bevy** (first-class offscreen
rendering + `bevy_brp_mcp` live-world inspection, but worst API churn and slowest loop) and
**TypeScript/three.js** (proven visual CI + highest training density, but weakest native/console
ceiling), with **MonoGame** third.

## Open risks
1. **WebGPU inside WKWebView on iOS** — MDN infers it; no primary source confirms. Blocks the TS
   iOS story. Probe on device.
2. **W4 Games**: console list, pricing, and whether C#/.NET Godot games can ship to console.
3. **Playwright + WebGPU headless** — proven under Puppeteer only.
4. Unreal royalty terms (unrealengine.com/license 403'd; figures from Wikipedia).
5. LÖVE 12.0 cadence — repo active (pushed 2026-08-08) but last tag is 11.5 from 2023.

---

## ⚠️ CORRECTION: Godot renders fine WINDOWED; only `--headless` cannot (tested 2026-08-10)

**I eliminated Godot prematurely and that was wrong.** The `--headless` finding below is accurate,
but I generalised it into "Godot cannot do render verification", which is false. Run windowed,
Godot captures pixels correctly:

```
$ Godot --path . --resolution 320x200      # note: NO --headless
RESULT image=320x200 lit=660
capture.png written  # visually confirmed: the exact ColorRect, right size, right position
```

So the accurate statement is:

| Mode | Logic tests | Pixel capture |
|---|---|---|
| `--headless` | ✅ works | ❌ `get_image()` → null; `frame_post_draw` **deadlocks** |
| windowed | ✅ works | ✅ full `get_viewport().get_texture().get_image()` |

**What this actually costs:** render verification needs a display server. That is fine on a dev
machine and on a macOS CI runner with a GUI session; it fails on a standard headless Linux runner
unless you add Xvfb (which does not exist on macOS, but is trivial on Linux). Compare with Bevy
and the TypeScript stack, both of which capture pixels with no display at all.

That is a real and material limitation — it is **not** a disqualification, and Godot is included
in the bake-off on the same tasks as every other stack.

### The original headless finding (accurate, narrower than I first claimed)

The disqualification above was originally asserted from reading
`servers/display/display_server_headless.h`. It has now been **measured** on Godot 4.7.1.stable
(installed via `brew install --cask godot`) rather than inferred.

Probe: a minimal `Node2D` scene adds a bright `ColorRect`, waits five process frames, then calls
`get_viewport().get_texture().get_image()`.

```
$ Godot --headless --path .
RESULT ready ok
ERROR: Parameter "t" is null.
RESULT image=NULL -- headless produced no framebuffer
```

Two separate findings, both decisive for our purposes:

1. **`get_image()` returns null.** There is no framebuffer to read, so there is nothing to diff.
   The scene tree runs, the script runs, the node is added — and no pixels exist.
2. **`await RenderingServer.frame_post_draw` never fires and deadlocks the script.** An earlier
   version of the probe used that idiom (the one you would naturally reach for) and hung
   indefinitely with no output until killed. In headless there is no post-draw, ever.

The second is worse than the first for an agent: the obvious approach does not fail loudly, it
**hangs**. An agent burning its command timeout on a deadlocked screenshot attempt gets no error
message to reason about.

Combined with macOS having no software-rasterisation fallback (no Xvfb, Metal only), this closes
the question: **Godot cannot support the rendering-verification requirement on the user's primary
platform.** The `godot-probe` project used for this test is under `staging/`.

## EMPIRICAL: Unity 6 batchmode IS automatable (tested 2026-08-10)

Unity 6000.0.45f1 on macOS. Contrary to the assumption that a proprietary editor-centric engine
cannot be driven headlessly, **Unity runs tests in CI-style batchmode with no interactive step**:

```
Serial number assigned to: "4674078975355-UnityPersXXXX"      # Personal licence, auto-resolved
Pro License: NO
Test run completed. Exiting with code 2 (Failed). One or more tests failed.
results.xml -> total="2" passed="1" failed="1"
```

Working invocation:
```
Unity -batchmode -nographics -logFile <log> -projectPath <proj> \
      -runTests -testPlatform EditMode -testResults <results.xml>
```
Exit code 0 = all passed, 2 = one or more failed. That is a usable gate.

**Three pieces of friction an agent would hit, each of which cost a run to discover:**

1. **Never pass `-quit` with `-runTests`.** It makes the editor exit before the tests execute —
   silently, with exit 0 and no results file. This is the single most common Unity CI mistake and
   produces a *false green*.
2. **`.asmdef` syntax is version-sensitive.** The widely-copied 2018-era form with
   `"optionalUnityReferences": ["TestAssemblies"]` yields `Scripts have compiler errors` and
   `Aborting batchmode`. Unity 6 needs `"overrideReferences": true` +
   `"precompiledReferences": ["nunit.framework.dll"]` + `"defineConstraints": ["UNITY_INCLUDE_TESTS"]`.
   Exactly the stale-API failure mode measured for Bevy, in a different ecosystem.
3. **`manifest.json` needs `"testables": ["com.unity.test-framework"]`** or the runner finds
   nothing and reports success over zero tests.

**Cost note:** editor start-up dominates. A two-test EditMode run takes ~30–60 s wall even warm,
versus ~20 ms for the equivalent Rust simulation suite. That is a ~1000× difference in the inner
loop, and it lands directly on the agent's iteration budget.

⚠️ **Open risk for the bake-off:** `-nographics` gives no graphics device, so pixel capture needs
batchmode *with* graphics plus a `RenderTexture` + `ReadPixels`/`AsyncGPUReadback`. Whether that
works on a macOS batchmode session is unverified and is the Unity template's main build risk.
