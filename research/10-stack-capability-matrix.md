# Stack capability matrix, at the pinned versions (surveyed 2026-08-22/23)

What each of the four stacks can actually do **at the version this project pins**, what it costs
to reach, and whether it exists on the measurement machine at all.

Written for task 24. It is the evidence base `DECISIONS.md` ("The templates are measured at each
stack's best, not at a common floor") requires task 26 to cite. **It changes no template and
recommends no change on its own.** §9 states which capability changes would move a *valid*
signal and which would only move colour count.

**Read §2 before trusting any cell.** Three of the four pins are far narrower than the engine's
name suggests, and most of what "the engine has" is not in the pin.

---

## 1. Method, and how to disagree with this document

Per `research/AGENTS.md`: vendored source beats documentation, documentation beats memory; every
claim dated and version-named; anything unverified labelled.

| column | ground truth used |
|---|---|
| Rust / Bevy | vendored crate sources under `~/.cargo/registry/src/index.crates.io-1949cf8c6b5b557f/`, at the exact versions in `eval/starters/rust/Cargo.lock`; plus a `wgpu` 29.0.4 adapter probe run **on the measurement machine** |
| TypeScript / three | the `three@0.185.1` npm tarball (shasum `63e9e241a17b101e211965121a017b4b4d8054ae`, 1195 files), plus **live probes through Playwright 1.62.1 Chromium** using the harness's exact `CHROMIUM_ARGS` and page setup |
| Unity | **live batchmode probes on the measurement machine**, plus the installed editor at `/Applications/Unity/Hub/Editor/6000.0.45f1/` and its offline Manual |
| Godot | the installed `4.7.1.stable.official.a13da4feb` binary — `--doctool` ClassDB dump (1076 class XMLs), headless `ProjectSettings` reads, `otool`/`strings` on the Mach-O |

Two citation conventions, so nothing below is ambiguous about what it points at:

- **`*.xml` in the Godot column** means a class file from `godot --headless --doctool`, which
  dumps the installed binary's whole ClassDB. Those files are not in this repo; regenerate them
  from the pinned binary. Their `<description>` blocks come out empty, so the dump sources API
  surface — classes, members, methods, enums, defaults — and never prose. Godot prose claims here
  come from `strings`/`otool` on the Mach-O instead, and say so.
- **A bare crate path** like `bevy_audio-0.19.0/src/audio.rs:55` is relative to
  `~/.cargo/registry/src/index.crates.io-1949cf8c6b5b557f/`. Repo paths are always written in
  full from the repository root.

**No cell was filled in because it was plausible.** What could not be established at the pinned
version is in §7 as unresolved, with what would settle it. An unresolved cell is a finding; a
guessed one is a number that gets acted on.

### Status vocabulary

| mark | meaning |
|---|---|
| **YES** | usable in the starter **as pinned** — no manifest, feature-flag or project-setting change |
| **YES\*** | present in the engine, excluded by the pin. Reaching it is a pin change every starter's `AGENTS.md` marks ⚠️ *ask first* |
| **CAVEAT** | present, with a named limitation that changes what it is worth here |
| **NO** | not available at this version by any change short of writing it |
| **UNRESOLVED** | see §7 |

### Effort tiers

| tier | means |
|---|---|
| **E1** | ~5 lines. A component, node or property reachable from what the starter already ships |
| **E2** | tens of lines against an existing API. No new dependency |
| **E3** | a **pin change** — package, crate, feature flag or project setting. ⚠️ *ask first* in every starter |
| **E4** | custom shader, custom render pass, or writing the subsystem yourself |

E3 is subscripted by where the dependency already is: **E3ₗ** resolves from disk (offline);
**E3ₙ** needs a registry. Both are ask-first; only E3ₙ can also fail. Network *is* available
during a trial — `eval/starters/ts/justfile:47-49` runs `pnpm install` and
`playwright install chromium` in `just warm` — so E3ₙ is a cost in turns, not a blocker.

**E3 is the interesting boundary, not E1/E2.** It is where a capability stops being something
an agent uses and becomes something an agent must first decide to *ask about*.

---

## 2. The pins — read from the artifacts, 2026-08-22

`eval/starters/` is what a trial gets. `template*/` differs only in the placeholder game; the
pins are identical in both.

| stack | pinned at | read from |
|---|---|---|
| Rust | **Bevy 0.19.0**, wgpu **29.0.4**, naga 29.0.4, Rust 1.95 / edition 2024 | `eval/starters/rust/Cargo.toml`, `Cargo.lock` |
| TypeScript | **three 0.185.1**, @types/three 0.185.4, playwright 1.62.1, TypeScript 6.0.3, Node ≥22, esbuild 0.28.2 | `eval/starters/ts/package.json` |
| Unity | **6000.0.45f1** (`d91bd3d4e081`) | `eval/starters/unity/ProjectSettings/ProjectVersion.txt` |
| Godot | **4.7**, Forward+ | `eval/starters/godot/project.godot`. Installed binary: `4.7.1.stable.official.a13da4feb` |

### The three narrowings that decide most of this document

**(a) Rust is pinned to Bevy's `2d` bundle, not to Bevy.**

```toml
bevy = { version = "0.19", default-features = false, features = ["2d", "png", "libm"] }
```

Resolved against vendored `bevy-0.19.0/Cargo.toml` (`2d = ["default_app", "default_platform",
"2d_bevy_render", "scene", "picking"]`, `2d_bevy_render = ["2d_api", "bevy_render",
"bevy_core_pipeline", "bevy_post_process", "bevy_sprite_render", "bevy_gizmos_render"]`), the pin

- **includes** `bevy_render`, `bevy_core_pipeline`, **`bevy_post_process`**, `bevy_sprite_render`,
  `bevy_gizmos_render`, `bevy_mesh`, `bevy_material`, `bevy_text`, `bevy_animation`,
  `bevy_picking`, `bevy_scene`, `bevy_winit`, `multi_threaded`, `png`, `hdr`;
- **excludes** `bevy_pbr`, `bevy_light`, `bevy_gltf`, `bevy_anti_alias`, `bevy_ui`, `bevy_audio`,
  `ktx2`, `tonemapping_luts`, `smaa_luts`, `bevy_solari`.

So at the pin: **no PBR, no lights, no shadows, no glTF, no anti-aliasing crate, no audio.**
`Mesh3d` exists (`bevy_mesh-0.19.0/src/components.rs:102`) but `MeshMaterial3d` lives in
`bevy_pbr` (`bevy_pbr-0.19.0/src/mesh_material.rs:41`), so **the Rust arm cannot render a lit 3D
mesh at the pin at all** — an agent can attach a mesh and has no material to draw it with. The
task prompt anticipates this: `THREE_D_NOTE["rust"]` says *"Building in 3D means enabling Bevy's
3D feature"*. Cost of doing so, from the starter's own comment: **405 s vs 294 s** cold
`just verify`; `template/AGENTS.md` calls the feature list *"a 2.4× build-time difference"* and
marks it ⚠️ ask first. All the crates are already vendored, so it is **E3ₗ**.

**(b) Unity is pinned to the Built-in Render Pipeline and five packages.**
`Packages/manifest.json` declares `com.unity.modules.imageconversion`, `.imgui`,
`.jsonserialize`, `com.unity.test-framework`, `com.unity.testtools.codecoverage`.
`packages-lock.json` additionally resolves `com.unity.ext.nunit` 2.0.5 (builtin) and
`com.unity.settings-manager` 2.0.1 (**registry**), and pins `test-framework` to **1.5.1**, not
the 1.4.5 requested. Nothing graphics-relevant, but the project is not registry-free.

Measured in batchmode on the machine: `renderPipelineAsset = null (Built-in RP)`,
`graphicsDeviceType = Metal`, `graphicsDeviceName = Apple M3 Max`, `graphicsShaderLevel = 50`,
`colorSpace = Gamma`, `activeBuildTarget = StandaloneOSX`.

**Module exclusion is real and was measured, not assumed.** `CompilationPipeline.GetAssemblies`
on the project's own `View` assembly returns **40** `UnityEngine.*Module` references; Physics,
Physics2D, Audio, Animation, ParticleSystem, AssetBundle, Terrain and UI are **all absent**.
`Sim` has **0** (its `noEngineReferences: true`). One asymmetry that will mislead someone:
**`Assets/Editor` gets all 73 modules**, so `Rigidbody` compiles in editor-only code and does
not in `Assets/View`.

**The good news for effort:** URP, HDRP, Shader Graph and VFX Graph 17.0.4 ship *inside the
editor* at `Unity.app/Contents/Resources/PackageManager/BuiltInPackages/`, and ~135 registry
packages ship pre-cached as tarballs at `.../PackageManager/Editor/*.tgz` — including
`com.unity.postprocessing-3.4.0`, `burst-1.8.19`, `entities-1.3.2`, `addressables-2.4.1`,
`physics-1.3.2`. Most Unity E3 is therefore E3ₗ. **No glTF package anywhere.**

**(c) The TypeScript arm renders on a CPU rasteriser.** `eval/starters/ts/src/view/harness.ts:287`
sets `CHROMIUM_ARGS = ['--use-angle=swiftshader', '--enable-unsafe-swiftshader']`;
`capture.ts:50` takes a **`webgl2`** context; `scripts/film.ts` drives the same harness. Renderer
string measured in-page: `ANGLE (Google, Vulkan 1.3.0 (SwiftShader Device (LLVM 10.0.0)),
SwiftShader driver)`. This is deliberate and the reason is sound —
`docs/three-0.185-notes.md`: *"software rasterisation is what makes the render tests
reproducible on any machine."* Every GPU-cost cell in the TS column is a CPU-cost cell.

### Two places a task prompt asks for something the pin does not contain

Both in `eval/suites/wholegame_prompts.py`.

| prompt says | pin says |
|---|---|
| `AUDIO_NOTE["rust"]`: *"Audio is Bevy's `AudioPlayer`"* | `bevy_audio` is not in `features = ["2d","png","libm"]`. `AudioPlayer` does not exist until the agent adds the `audio` feature |
| `AUDIO_NOTE["unity"]`: *"Audio is `AudioSource`/`AudioClip`"* | `com.unity.modules.audio` is absent; measured, `UnityEngine.AudioModule` is not among `View`'s 40 module references |

**This is not new**, and it is important that it is not: `eval/judge/starter_parity.py:110-115`
already records it — *"rust … and unity … cannot, and the task asks every agent for audio on a
SCORED criterion. Reported, not failed."* The survey confirms it from the other direction and
adds one measured trap: **`SystemInfo.supportsAudio` returns `True` on Unity** while no audio
API is reachable. Godot and TypeScript need no change to make sound.

---

## 3. The measurement machine, and what it actually exposes

**Apple M3 Max, macOS 26.2 (build 25C56).** Rule 10 — hold the machine, not just the
configuration.

### wgpu / Metal, enumerated rather than assumed

A ~60-line probe (`scratchpad/wgpuprobe/`, ~2 min from cold) opens a `wgpu` 29.0.4 adapter with
no surface and no window and prints `adapter.features()`:

```
adapter: AdapterInfo { name: "Apple M3 Max", ..., backend: Metal, ... }

EXPERIMENTAL_RAY_QUERY .............................. true
BUFFER_BINDING_ARRAY ................................ false
TEXTURE_BINDING_ARRAY ............................... true
SAMPLED_TEXTURE_AND_STORAGE_BUFFER_ARRAY_NON_UNIFORM_INDEXING ... true
PARTIALLY_BOUND_BINDING_ARRAY ....................... true

TEXTURE_COMPRESSION_ASTC true | TEXTURE_COMPRESSION_BC true | TEXTURE_COMPRESSION_ETC2 true
TIMESTAMP_QUERY true | SHADER_F16 true | INDIRECT_FIRST_INSTANCE true
EXPERIMENTAL_RAY_HIT_VERTEX_RETURN false | MULTI_DRAW_INDIRECT_COUNT false
```

**Hardware ray query IS available on this Mac.**
`wgpu-types-29.0.4/src/features.rs:1048` documents `EXPERIMENTAL_RAY_QUERY` as *"Supported
platforms: - Vulkan"*. **The doc comment is stale and the source contradicts it**:
`wgpu-hal-29.0.4/src/metal/adapter.rs:1155` sets the feature from `supports_raytracing`, which at
`adapter.rs:1019` is `macOS ≥ 15.0 && device.supportsRaytracing() &&
device.supportsRaytracingFromRender()`; `naga-29.0.4/src/back/msl/writer.rs` emits ray-query MSL
at MSL 2.4+. Probe: **true**. Reading the doc alone would have produced a confident, wrong
"no RT on Mac" — which is exactly why `research/AGENTS.md` ranks vendored source first.

**And it is still not enough for Bevy's ray tracing.** `bevy_solari` 0.19.0
(`src/lib.rs`, `SolariPlugins::required_wgpu_features()`) demands `EXPERIMENTAL_RAY_QUERY |
BUFFER_BINDING_ARRAY | TEXTURE_BINDING_ARRAY |
SAMPLED_TEXTURE_AND_STORAGE_BUFFER_ARRAY_NON_UNIFORM_INDEXING | PARTIALLY_BOUND_BINDING_ARRAY`.
`BUFFER_BINDING_ARRAY` is set by wgpu 29's **Vulkan backend only** (`grep -rn BUFFER_BINDING_ARRAY
wgpu-hal-29.0.4/src/` hits `vulkan/adapter.rs` and nothing else). Probe verdict, printed by the
program: `VERDICT bevy_solari can init on this adapter: false / MISSING: BUFFER_BINDING_ARRAY`.

**And it fails open.** `bevy_solari-0.19.0/src/scene/mod.rs:42-46` checks the features and, if
they are missing, emits `warn!("RaytracingScenePlugin not loaded. GPU lacks support for required
features: …")` and continues. An agent that adds Solari here ships a game that compiles, runs,
renders with **no** ray tracing, and leaves one warning line. Rule 7's shape exactly.

### Ray tracing on the other three, established the same way

**Godot 4.7.1 defaults to Metal on Apple silicon and its Metal backend has a ray-tracing path.**
`rendering/rendering_device/driver.macos = metal`, read headlessly from the installed binary
(`driver = vulkan` is the Intel fallback; the binary carries *"Metal is not supported on Intel
Macs, switching to Vulkan."*). `otool -v -s __TEXT __objc_methname /Applications/Godot.app/…/Godot`
finds `supportsRaytracing`, `supportsRaytracingFromRender`,
`newAccelerationStructureWithDescriptor:`, `newAccelerationStructureWithSize:` and
`accelerationStructureSizesWithDescriptor:`. The GDScript API is there too — `blas_create`,
`tlas_create`, `raytracing_pipeline_create`, `raytracing_list_trace_rays`,
`RDAccelerationStructureGeometry/Instance`, `SUPPORTS_RAY_QUERY`, `SUPPORTS_RAYTRACING_PIPELINE`
— but **only on `RenderingDevice`. There is zero scene-renderer integration**: `Environment` has
no ray-tracing member and no `rendering/*raytracing*` project setting exists.

**Unity 6000.0.45f1 has no ray tracing on this machine, by two independent measurements.**

1. Runtime, in batchmode on the machine: `supportsRayTracing = False`,
   `supportsRayTracingShaders = False`, `supportsInlineRayTracing = False`.
2. Statically: the *same* `otool` command against
   `/Applications/Unity/Hub/Editor/6000.0.45f1/Unity.app/Contents/MacOS/Unity` — which links
   `Metal.framework` directly and ships no separate graphics dylib — finds **none** of the five
   selectors. Only generic binding selectors (`setFragmentAccelerationStructure:atBufferIndex:`)
   are present, and a binding selector with no construction selector cannot build an
   acceleration structure.

> **The negative has a positive control, per rule 1.** The identical `otool` command on the
> Godot binary returns all five selectors. The probe can fire; it does not fire on Unity. A grep
> that found nothing in both would have proved nothing.

Documentation agrees:
`BuiltInPackages/com.unity.render-pipelines.high-definition/Documentation~/Ray-Tracing-Getting-Started.md:5`
— *"HDRP only supports ray tracing using the DirectX 12 API, so ray tracing only works in the
Unity Editor or the Windows Unity Player when they render with DirectX 12."*

**Yet Unity's ray-tracing managed API is fully present and needs no package.**
`UnityEngine.Rendering.RayTracingAccelerationStructure`, `RayTracingShader`,
`RayTracingInstanceCulling*` and 16 more types are declared in `UnityEngine.CoreModule.xml`,
which `Assets/View` references. **An agent can write, compile and ship DXR code on this machine;
it will never execute, and nothing errors.** That is rule 13's accepted-but-ignored-flag shape,
and it costs turns before the platform is discovered to be wrong.

### Which arm renders on what — the asymmetry that precedes every cell below

The judged frames are `film`'s output: at most **12 PNGs at 640x400**
(`eval/starters/godot/tools/film.gd:20` `MAX_FRAMES = 12`; the other three `film` recipes match).

| arm | what draws the judged frames | source |
|---|---|---|
| Rust | real Metal GPU (M3 Max), offscreen | `eval/starters/rust/justfile:172` |
| Unity | real Metal GPU — `film` runs **without** `-nographics`, deliberately | `eval/starters/unity/justfile:119-124` |
| Godot | real Metal GPU, windowed — no `--headless`, deliberately | `eval/starters/godot/justfile:169-176` |
| **TypeScript** | **SwiftShader, a CPU rasteriser** | `harness.ts:287`, `capture.ts:50` |

Three arms have an M3 Max; one has a software rasteriser, on purpose. **Every GPU-capability row
is therefore not merely harder for the TS arm but a different kind of quantity** — and it places
that arm structurally at the low end of the distinct-colour distribution #78 shows `ux` tracking.
See §9.

**The 12-frame budget cuts the other way, though, and it matters.** A capture is 12 single
frames, not a real-time run. Measured on SwiftShader at 640x400: `EffectComposer` baseline 1.6
ms/frame, `UnrealBloomPass` 14.3, `SSAOPass` 29.1, `GTAOPass` 41.9, `SSRPass` 55.9. At twelve
frames, **56 ms/frame is 0.7 s for the whole capture** — free. Frame cost only bites `just run`.
Expensive post-processing is affordable in every arm's *graded* artifact.

---

## 4. Summary matrix

Status / effort. `†` = platform-conditional; the capability's section says how.

| capability | Rust · Bevy 0.19 (`2d` pin) | TS · three 0.185.1 (SwiftShader) | Unity 6000.0.45f1 (BiRP, 5 pkgs) | Godot 4.7 Forward+ |
|---|---|---|---|---|
| Hardware ray tracing | **NO†** — Solari fails open | **NO** | **NO†** — API compiles, never runs | **CAVEAT†** E4, `RenderingDevice` only, no renderer integration |
| Software GI / probes / lightmaps | **YES\*** E3ₗ (needs `3d`) | **YES** E1–E2 (IBL/PMREM/lightmap) | **CAVEAT** E3–E4 (lightmaps only; APV/SSGI need URP/HDRP) | **YES** E1–E2 (SDFGI, VoxelGI, LightmapGI, SSAO, SSIL) |
| Real-time + soft shadows | **YES\*** E3ₗ (needs `3d`) | **CAVEAT** E1 hard; soft = VSM only, ~8× | **YES** E1 — already on | **YES** E1 (PCSS, 4-split PSSM) |
| Post-processing (bloom etc.) | **YES** E1 — bloom works in 2D | **YES** E2 — 29 passes ship | **NO** E3ₗ — BiRP has no post stack | **YES** E1 (glow, AgX, DOF, SSR) |
| Antialiasing | **YES\*** E3ₗ (`bevy_anti_alias`, 3D) | **YES** E2 (SMAA/FXAA/TAA/SSAA passes) | **YES** E1 — MSAA 2× already on | **YES** E1 via `Viewport` (MSAA/FXAA/SMAA/TAA) |
| **Native particle system** | **NO** E4 | **NO** E4 — `Points`/`Sprite` only | **NO** E3ₗ (Shuriken); VFX Graph needs URP/HDRP | **YES** E1–E2 — `GPUParticles3D/2D` |
| **Native 3D physics** | **NO** E3ₙ (avian/rapier) | **NO** E4 in practice | **NO** E3ₗ (PhysX module) | **YES** E1–E2 — Godot Physics default, **Jolt in-tree, not default** |
| GPU instancing | **YES** E1 — automatic | **YES** E1 — `InstancedMesh`/`BatchedMesh` | **YES** E2 (shader needs a pragma) | **YES** E1–E2 — `MultiMesh` |
| Sprite / texture atlas | **YES** E1 | **CAVEAT** E2 — no atlas API, hand-roll UVs | **YES** E2 — `SpriteAtlas` | **YES** E1 + automatic packer (editor) |
| Texture compression | **YES\*** E3ₗ (`ktx2`/`dds`) | **CAVEAT** E2 — SwiftShader accepts BC/ASTC/ETC2; **KTX2Loader breaks the bundle** | **CAVEAT†** E1 — **BC/DXT only** for Mac; ASTC silently becomes DXT5 | **CAVEAT†** E3 — off by default; arm64 → ETC2/ASTC |
| LOD / mesh simplification | **NO** (meshlets E3ₗ, 3D-only) | **YES** E1 LOD, E2 `SimplifyModifier` | **CAVEAT** E2 `LODGroup`; **no simplifier** (E4) | **YES** E1–E2 (`generate_lods`, visibility ranges) |
| **Spatial audio / HRTF** | **NO HRTF**; spatial pan YES\* E3ₗ | **YES** E1 — HRTF measured working | **NO** — no audio at all at the pin; no spatializer ships | **CAVEAT** E1–E2 spatial; **HRTF absent** |
| Compute shaders | **YES** E4 | **NO** WebGL2; WebGPU unreachable | **YES** E2 — `supportsComputeShaders=True` | **CAVEAT** E2–E4 — **null under `--headless`** |
| Multithreaded scheduling | **YES** E1 (`multi_threaded` on) | **CAVEAT** E2 — no `SharedArrayBuffer` | **CAVEAT** E2 on paper, blocked in practice | **YES** E2 — `WorkerThreadPool` |
| Streaming asset loading | **YES** E2 | **CAVEAT** E1–E2 — **capture page cannot fetch a file** | **YES** E1 (Resources); AssetBundles E3ₗ | **YES** E1–E2 |
| Skeletal animation / glTF | **YES\*** E3ₗ (glTF needs `3d`) | **CAVEAT** E2 — **frozen clock stops the mixer** | **CAVEAT** E3ₗ (`Animator`); **no glTF importer at all** | **YES** E1–E2 (`Skeleton3D`, `GLTFDocument`) |

---

## 5. The three differences that actually matter for the current task set

Everything else in §6 is real and mostly irrelevant here (§8 says why). These three are not.

**1. Native particle systems: Godot has one, nobody else does at the pin.** `GPUParticles3D`,
`GPUParticles2D`, `CPUParticles3D/2D` are all in Godot's ClassDB (probed). Unity's Shuriken is
one manifest line away (**E3ₗ**) and VFX Graph is unreachable without a render-pipeline switch.
Bevy 0.19 ships **no** particle system — there is no `particle` module anywhere in the crate
tree. three 0.185.1 ships none either, and this was machine-checked rather than asserted:
esbuild reports *"Import `ParticleEmitter` will always be undefined because there is no matching
export in three.module.js"*, and in-page `Object.keys(THREE).filter(/particle/i)` returns `[]`.
`PointsMaterial` gives `size`/`sizeAttenuation`/`map`/`alphaMap` and nothing else — no emitter,
lifetime, curve, burst, sub-emitter or collision. A line clear or an enemy death is exactly where
particles land, and the spread between "one node" and "write it yourself" is the widest
effort gap in the matrix.

**2. Native physics is the largest *nominal* difference and the smallest real one — and the
direction is inverted from what it looks like.** Godot ships two 3D engines (Godot Physics is the
default; **Jolt is in-tree but NOT default** — measured behaviourally with positive controls:
`DEFAULT` and `GodotPhysics3D` both give 9966.69/4983.35 velocity clamps, `Jolt Physics` gives
498.33/46.97; the 2D hint offers no Jolt at all). Unity's PhysX is one manifest line. Bevy needs
a crate; three needs a library — and three's `examples/jsm/physics/*.js` are **not** engines,
they fetch the engine from a CDN at runtime (`AmmoPhysics.js:1` → `cdn.jsdelivr.net`,
`RapierPhysics.js:3` → `cdn.skypack.dev`), which cannot work from a page whose origin is `null`.

**But none of the four games needs a physics engine, and two prompts forbid one**
(`wholegame_prompts.py:497` *"Use no physics engine: collisions are spheres and boxes"*; `:589`
*"gravity is a constant, collisions are rectangles"*). More decisively, **all four starters make
engine physics structurally unreachable from where game rules must live**: Unity's `Sim.asmdef`
sets `noEngineReferences: true` (0 module refs, measured); Godot's `tools/boundary.gd` bans every
`Node` type, `_physics_process`, `add_child` and `PhysicsServer2D` inside `sim/`; Bevy's
`crates/sim/tests/boundary.rs` bans the render/entropy crates; the TS `src/sim` firewall bans
`three`, `node:*`, `async`, `await` and `Promise`.

> **The asymmetry inverts.** Unity and Godot ship the better physics engines and **cannot put
> them where the rules live**. Rust and TypeScript ship none and **could** pin a deterministic
> f32 library inside `sim` — Bevy's ban list does not name `avian`/`rapier`, and TS's bans a wasm
> engine only via its `async`/`Promise` rules. What the templates would showcase is not "Unity
> has PhysX" but "which stacks can put a deterministic solver behind the sim boundary".

**3. Ray tracing is unavailable in three arms and non-integrated in the fourth.** §3 settles it:
Rust has the hardware feature and Bevy cannot use it (missing `BUFFER_BINDING_ARRAY`, fails
open); Unity has no Metal path at all (two independent measurements, positive control); TS has
no WebGPU (`navigator.gpu` absent in **all eight** Playwright configurations tested, including
`headless:false`); Godot has the RenderingDevice API and the Metal selectors but no renderer
integration, so it is E4 and effectively a research project.

> **The operator's headline example does not survive contact with the pins.** A ray-traced 3D
> Tetris is not reachable in any of the four arms on this machine at anything under E4, and in
> two of them not at all. Whatever task 26 does, it should not be this.

---

## 6. Per-capability detail

Every row: status, effort, Apple-silicon conditionality, source.

### 6.1 Hardware ray tracing

| stack | status | effort | Apple silicon | source |
|---|---|---|---|---|
| Rust | **NO** — `EXPERIMENTAL_RAY_QUERY` is true but `bevy_solari` needs `BUFFER_BINDING_ARRAY`, which Metal never sets. **Fails open with a `warn!`** | E4 | **†decisive** | wgpu probe (§3); `bevy_solari-0.19.0/src/lib.rs`, `src/scene/mod.rs:42-46`; `wgpu-hal-29.0.4/src/{metal,vulkan}/adapter.rs` |
| TS | **NO** — no RT in WebGL2; WebGPU unreachable. The only `pathtrac` hits in the tarball are doc comments citing the *external* `three-gpu-pathtracer` | E4 | **†** | `examples/jsm/tsl/display/ImportanceSampledEnvironment.js:5` |
| Unity | **NO** — measured `supportsRayTracing/Shaders/InlineRayTracing = False`; no Metal acceleration-structure selectors. **API compiles anyway** | — | **†decisive** | batchmode probe; `otool` with positive control; HDRP `Ray-Tracing-Getting-Started.md:5` |
| Godot | **CAVEAT** — full `RenderingDevice` RT API and Metal backend present; **zero scene-renderer integration**. Dedicated HW intersection units are M3+, so this machine qualifies and an M1/M2 would not | E4 | **†** | `docs/doc/classes/RenderingDevice.xml`, `RDAccelerationStructureInstance.xml`; `otool` selectors |

### 6.2 Software GI — lightmaps, probes, SDFGI

| stack | status | effort | source |
|---|---|---|---|
| Rust | **YES\*** — `bevy_pbr` 0.19 ships `lightmap/`, `light_probe/`, `environment_map/`, `ssao/`, `ssr/`, `volumetric_fog/`, `atmosphere/`. All gated behind the `3d` feature | E3ₗ | vendored `bevy_pbr-0.19.0/src/` |
| TS | **YES** — `lightMap`/`lightMapIntensity`/`aoMap` on `MeshStandardMaterial`; `PMREMGenerator.fromScene(RoomEnvironment)` measured at **49 ms**; `LightProbeGenerator`, `ProgressiveLightMap`. ⚠️ `HemisphereLightProbe`/`AmbientLightProbe` are **no longer exported** in 0.185 (measured `undefined`); `LightProbe` remains | E1–E2 | `src/materials/MeshStandardMaterial.js:123,131,143`; `examples/jsm/environments/RoomEnvironment.js` |
| Unity | **CAVEAT** — Progressive CPU/GPU lightmappers are BiRP-supported and `GIModule` *is* in `View`'s refs. **Adaptive Probe Volumes: BiRP = No. SSGI: HDRP only.** In practice lightmapping is an editor bake over a *saved scene with static geometry*, and the starter deliberately commits no `.unity` scene — so it is E3–E4 by workflow, not by packages | E3–E4 | feature-comparison §Global Illumination / §Adaptive Probe Volumes; `Assets/Editor/BuildScript.cs` |
| Godot | **YES** — SDFGI as 12 `Environment.sdfgi_*` properties (not a class), plus `VoxelGI`+`VoxelGIData`, `LightmapGI`+`LightmapperRD`, SSAO (9 members), SSIL (5 members) | E1 props / E2 bake | `Environment.xml`; ClassDB probe |

### 6.3 Real-time and soft shadows

| stack | status | effort | source |
|---|---|---|---|
| Rust | **YES\*** — `bevy_pbr` ships `contact_shadows.rs`; `experimental_pbr_pcss` is a feature. Needs `3d` | E3ₗ | vendored `bevy_pbr-0.19.0/src/` |
| TS | **CAVEAT** — **`PCFSoftShadowMap` is deprecated in 0.185 and silently renders as `PCFShadowMap`**. Real soft shadows are VSM only, ~8× the cost. Measured at 640×400, 24 casters, 1024px map: Basic 3.3 / PCF 3.7 / PCFSoft→PCF 3.7 / **VSM 29.4** ms/frame. CSM ships as an addon | E1 hard, E2 CSM, E4 PCSS | `src/renderers/webgl/WebGLShadowMap.js:101` — `warn('WebGLShadowMap: PCFSoftShadowMap has been deprecated. Using PCFShadowMap instead.')` |
| Unity | **YES, already on** — `QualitySettings.asset` has `m_CurrentQuality: 5` (Ultra), `shadows: 2` (hard + soft), `pixelLightCount: 4`. Measured `supportsShadows=True`. Contact shadows / PCSS / EVSM are **HDRP-only** | E1 | `ProjectSettings/QualitySettings.asset`; feature-comparison §Shadows |
| Godot | **YES** — `shadow_enabled/bias/blur/opacity/normal_bias/caster_mask`; PCSS via `light_angular_distance` (directional) and `light_size` (positional); 4-split PSSM; `soft_shadow_filter_quality` defaults to **2** | E1 | `Light3D.xml`, `DirectionalLight3D.xml`; ProjectSettings probe |

### 6.4 Post-processing and antialiasing

| stack | status | effort | source |
|---|---|---|---|
| Rust | **YES for bloom, at the pin.** `bevy_post_process` is pulled in by the `2d` bundle and its `bloom` module registers on **both** `Core2d` and `Core3d`. `dof`, `motion_blur`, `auto_exposure` register on `Core3d` only. **AA is a separate crate** (`bevy_anti_alias`: fxaa/smaa/taa/cas/dlss) and is 3D-bundle-only. ⚠️ `tonemapping_luts` is off, so `AgX`/`TonyMcMapface`/`BlenderFilmic` load a **placeholder LUT and log an error** rather than failing to compile | E1 bloom; E3ₗ AA | `bevy_post_process-0.19.0/src/bloom/mod.rs:82-83`, `dof/mod.rs:235`, `motion_blur/mod.rs:178`; `bevy_core_pipeline-0.19.0/src/tonemapping/mod.rs:72-80` |
| TS | **YES — 29 passes ship in the tarball.** `EffectComposer`, `UnrealBloomPass`, `SSAOPass`, `GTAOPass`, `SAOPass`, `SMAAPass`, `FXAAPass`, `TAARenderPass`, `SSAARenderPass`, `BokehPass`, `SSRPass`, `OutlinePass`, `OutputPass` + 16 more. Cost measured (§3): all affordable at 12 frames. **Plus 43 TSL node effects** reachable because `three/webgpu` auto-falls back to `WebGLBackend` with no `navigator.gpu` — measured rendering 640×400 with shadows, 256000/256000 non-black px, at a 2.4–3.0 MB bundle cost. ⚠️ `PostProcessing` was renamed **`RenderPipeline`**; `renderAsync()` is deprecated | E2 | `examples/jsm/postprocessing/`; `src/renderers/webgpu/WebGPURenderer.js:57-73`; `examples/jsm/tsl/display/` |
| Unity | **NO at the pin.** *"BiRP = Uses separate package: Post-Processing V2"*. `com.unity.postprocessing-3.4.0.tgz` is pre-cached in the editor, so it is E3ₗ, then E2. AA is better: **MSAA 2× is already on** (`antiAliasing: 2`, forward path) | E3ₗ post; E1 MSAA | feature-comparison §Post-processing; `.../PackageManager/Editor/com.unity.postprocessing-3.4.0.tgz`; `QualitySettings.asset` |
| Godot | **YES** — glow (11 members incl. `glow_map`), tonemap `LINEAR/REINHARDT/FILMIC/ACES/`**`AGX`**, DOF via `CameraAttributesPractical`, SSR (5 members). AA: MSAA 3D 2×/4×/8×, FXAA, **SMAA** (new in 4.7: `SCREEN_SPACE_AA_SMAA` + `smaa_edge_detection_threshold`), TAA. **All settable from GDScript as `Viewport` properties** — `get_viewport().msaa_3d = Viewport.MSAA_4X` — which keeps them at E1 and never touches the ask-first `project.godot` surface. MetalFX spatial/temporal scaling exists on `Viewport` but is absent from the project-setting dropdown, so code-only; *"FSR 2 or MetalFX Temporal is not compatible with TAA. Disabling TAA internally."* | E1 | `Environment.xml`, `Viewport.xml`, `CameraAttributesPractical.xml`; binary strings |

**A Godot-specific conflict worth carrying into task 26.** `eval/starters/godot/project.godot`
states its `[rendering]` block exists because *"The render tests assert on exact byte values…
Anything that introduces a tonemapper or an sRGB round trip between draw_rect and the framebuffer
changes those bytes."* Adding a `WorldEnvironment` for glow or tonemapping does exactly that.
**Any Godot submission using 3D post-processing breaks `tests/render_test.gd` byte assertions
without changing any geometry** — and the failure looks like a rendering bug and is not one.

### 6.5 Native particle systems

| stack | status | effort | source |
|---|---|---|---|
| Rust | **NO.** No `particle` module anywhere in bevy 0.19's crate tree | E4 | crate-tree scan |
| TS | **NO.** `Points` and `Sprite` only; machine-checked (esbuild "will always be undefined"; `Object.keys(THREE).filter(/particle/i)` → `[]`). ⚠️ Perf note: `Points` is the **only** viable large-count primitive on SwiftShader — 50 000 points **4.1 ms** vs 50 000 `InstancedMesh` **590 ms** (144×) | E4 | `src/objects/Points.js`, `src/objects/Sprite.js`; absence in `src/Three.Core.js` |
| Unity | **NO at the pin** — `com.unity.modules.particlesystem` absent from the manifest *and* from `View`'s 40 refs (measured). Module ships in the editor → **E3ₗ**. **VFX Graph is BiRP = No**, so it needs a pipeline switch on top | E3ₗ | probe; `.../BuiltInPackages/com.unity.modules.particlesystem/`; feature-comparison §GPU Particles |
| Godot | **YES** — `GPUParticles3D`, `GPUParticles2D`, `CPUParticles3D`, `CPUParticles2D` all exist (probed) | E1–E2 | ClassDB probe; `GPUParticles3D.xml` |

### 6.6 Native physics

See §5.2 for why the nominal ranking inverts. Facts:

| stack | status | effort | source |
|---|---|---|---|
| Rust | **NO built-in.** A crate (`avian`/`rapier`) would have to be pinned. Not on `crates/sim/tests/boundary.rs`'s ban list, so it *could* sit behind the sim boundary | E3ₙ | `eval/starters/rust/crates/sim/tests/boundary.rs:22-56` |
| TS | **NO.** `examples/jsm/physics/*.js` are CDN loaders, not engines, and the capture page's `null` origin cannot fetch http. The `src/sim` firewall bans `async`/`await`/`Promise`, so a wasm engine cannot hold game logic | E4 in practice | `AmmoPhysics.js:1`, `RapierPhysics.js:3`, `JoltPhysics.js:3`; `eval/starters/ts/eslint.config.js` |
| Unity | **NO at the pin** — neither `com.unity.modules.physics` (PhysX) nor `.physics2d` (Box2D) in the manifest or in `View`'s refs. Both ship in the editor. DOTS Physics and Havok are pre-cached tarballs | E3ₗ | probe; `Manual/PhysicsSection.html` |
| Godot | **YES** — Godot Physics 3D is the default; **Jolt is in-tree and NOT the default** (measured with both positive controls); 32 `physics/jolt_physics_3d/*` settings are registered. 2D hint is `DEFAULT,GodotPhysics2D,Dummy` — **no Jolt for 2D** | E1–E2 to switch | behavioural discriminator on Jolt-only velocity clamps; ProjectSettings hints |

### 6.7 GPU instancing

| stack | status | effort | source |
|---|---|---|---|
| Rust | **YES, automatic** — meshes sharing mesh+material batch into one draw call with no code; `MeshTag` carries per-instance data | E1 | `bevy-0.19.0/examples/shader/automatic_instancing.rs:1-3` |
| TS | **YES** — `InstancedMesh` (2000 instances → **3 draw calls**, measured) and `BatchedMesh`; both WebGL2-native. `SceneOptimizer` addon auto-batches. SwiftShader is vertex-bound: 1k 14.2 / 10k 134 / 50k 590 ms/frame | E1 | `src/objects/InstancedMesh.js`, `BatchedMesh.js`; `examples/jsm/utils/SceneOptimizer.js` |
| Unity | **YES** — `DrawMeshInstanced`, `RenderMeshInstanced`, `DrawMeshInstancedIndirect`, `RenderMeshIndirect`, `BatchRendererGroup`, all in `CoreModule`. Measured `supportsInstancing=True`. The starter's `Flat.shader` needs `#pragma multi_compile_instancing` added. GPU Resident Drawer / GPU occlusion culling are BiRP = No | E2 | probe; `UnityEngine.CoreModule.xml` |
| Godot | **YES** — `MultiMesh` + `MultiMeshInstance3D/2D`: `instance_count`, `visible_instance_count`, `buffer`, `custom_data_array`, `transform_format` | E1–E2 | `MultiMesh.xml` |

### 6.8 Sprite and texture atlasing

| stack | status | effort | source |
|---|---|---|---|
| Rust | **YES** — `TextureAtlas`, `TextureAtlasLayout`, `TextureAtlasBuilder`, `DynamicTextureAtlasBuilder` in `bevy_image` (enabled at the pin). This is exactly what `SPRITE_NOTE["rust"]` asks for | E1 | `bevy_image-0.19.0/src/texture_atlas{,_builder}.rs` |
| TS | **CAVEAT — no atlas API.** Zero `Atlas` exports in `Addons.js` or `Three.Core.js`. Hand-roll via `texture.offset/repeat`, or use `DataArrayTexture`/`CompressedArrayTexture` (both exported). A packer ships as `three/addons/libs/potpack.module.js`, but only as an internal dependency of `ProgressiveLightMap` | E2 | `src/Three.Core.js:29,32`; `examples/jsm/libs/potpack.module.js` |
| Unity | **YES** — `UnityEngine.U2D.SpriteAtlas` in `CoreModule`; `SpriteAtlasImporter`/`SpriteAtlasAsset` in `UnityEditor.CoreModule`; `SpriteRenderer` in `CoreModule`. The Sprite Editor *window* is `com.unity.2d.sprite` (bundled, E3ₗ) but is not needed for API use | E2 | `UnityEngine.CoreModule.xml`, `UnityEditor.CoreModule.xml` |
| Godot | **YES + an automatic packer** — `AtlasTexture` (`atlas`/`region`/`margin`/`filter_clip`), `ResourceImporterTextureAtlas` (`atlas_file`, `import_mode`, `crop_to_region`, `trim_alpha_border_from_region`), `TileSetAtlasSource`. Caveats in the binary: *"AtlasTexture not supported as a source for blit_rect"*; STRETCH_TILE unsupported with a non-zero margin | E1 manual / E2–E3 auto (importer is an **editor** pass) | `AtlasTexture.xml`, `ResourceImporterTextureAtlas.xml` |

### 6.9 Texture compression on Apple silicon

The most platform-conditional row in the matrix, and the four answers disagree.

| stack | status | effort | Apple silicon | source |
|---|---|---|---|---|
| Rust | **YES\*** — `TEXTURE_COMPRESSION_ASTC`, `_BC` and `_ETC2` are **all true** on the M3 Max (measured). But `ktx2`, `dds` and `basis-universal` are all excluded by the pin | E3ₗ | **all three families available** | wgpu probe (§3); `bevy-0.19.0/Cargo.toml` feature list |
| TS | **CAVEAT** — SwiftShader accepts more than expected: `compressedTexImage2D` returned GL error 0 for **S3TC DXT1/DXT5, ASTC 4×4, ETC2, BC7**, plus `s3tc_srgb` and `RGTC`. **PVRTC absent.** ⚠️ **`KTX2Loader` cannot be used at all**: its top-level `new URL('../libs/basis/…', import.meta.url)` leaves `import_meta.url` undefined under esbuild's IIFE output, throwing *"Failed to construct 'URL': Invalid URL"* and **taking the whole bundle down** — reproduced on the harness's exact page setup | E2 raw / E4 KTX2 | SwiftShader is more permissive than a real WebGL2 driver would be | live `getSupportedExtensions()` + upload probe; `examples/jsm/loaders/KTX2Loader.js:106-107` |
| Unity | **CAVEAT — BC/DXT only for the Mac standalone target.** Measured importer request→actual: `ASTC_6x6 → DXT5`, `ETC2_RGBA8 → DXT5`, `BC7 → BC7`, `DXT5 → DXT5`. **The substitution is silent** — reading back `TextureImporterPlatformSettings.format` still says ASTC; only `Texture2D.format` after reimport reveals it. Meanwhile the *GPU* supports ASTC/ETC/PVRTC (`SystemInfo.SupportsTextureFormat` = True for all six probed), so *"does the M3 support ASTC"* and *"can this build target ship ASTC"* have **opposite answers** | E1–E2 | **†decisive** | batchmode importer probe; `Manual/texture-formats-reference.html` |
| Godot | **CAVEAT — present, off by default, ask-first to enable.** `import_s3tc_bptc = false` and `import_etc2_astc = false`; `ResourceImporterTexture.compress/mode = 0` (lossless). Binary strings: *"Cannot export for universal or arm64 if ETC2 ASTC texture format is disabled"* vs *"…or x86_64 if S3TC BPTC…"* → **arm64 macOS uses ETC2/ASTC**, x86_64 uses S3TC/BPTC | E3 | **†** | ProjectSettings probe; `Image.xml`, `ResourceImporterTexture.xml` |

### 6.10 LOD and mesh simplification

| stack | status | effort | source |
|---|---|---|---|
| Rust | **NO general LOD.** `meshlet`/`meshlet_processor` are `bevy_pbr` features (Nanite-like, "for dense high-poly scenes (experimental)") and need `3d`. No distance-LOD component | E3ₗ, 3D-only | `bevy-0.19.0/examples/3d/meshlet.rs:1`; `bevy_pbr-0.19.0/src/meshlet/` |
| TS | **YES both** — `THREE.LOD` (`levels`, `getCurrentLevel`, `autoUpdate`); `SimplifyModifier` measured 561 → 279 verts in **9 ms**; `meshopt_simplifier.module.js` and `meshopt_clusterizer.module.js` also ship (unused by any addon) | E1 / E2 | `src/objects/LOD.js`; `examples/jsm/modifiers/SimplifyModifier.js` |
| Unity | **CAVEAT** — `LODGroup` is in `CoreModule` and `lodBias`/`maximumLODLevel` are already in QualitySettings, but **Unity 6000.0 has no mesh decimator**. LOD meshes must be authored externally (`_LOD0`/`_LOD1` FBX naming) or assembled by hand | E2 / E4 | `Manual/importing-lod-meshes.html`, `configure-mesh-lod.html` |
| Godot | **YES** — `ImporterMesh.generate_lods()` does real simplification; `GeometryInstance3D.lod_bias` + `visibility_range_*`; `rendering/mesh_lod/lod_change/threshold_pixels = 1.0`. `OccluderInstance3D` exists (occlusion culling default off) | E1 ranges / E2 on procedural `ArrayMesh` | `GeometryInstance3D.xml`, `ImporterMesh.xml` |

### 6.11 Spatial audio and HRTF

**Only one of four stacks has HRTF at its pin, and it is the one whose capture path records no
audio.**

| stack | status | effort | source |
|---|---|---|---|
| Rust | **NO HRTF, stated in the source.** `bevy_audio-0.19.0/src/audio.rs:55` — *"Note: Bevy does not currently support HRTF or any other high-quality 3D sound rendering."* Spatial panning + `SpatialListener` + `SpatialScale` exist. All of it is behind the `audio` feature, which the pin excludes | E3ₗ then E1 | vendored `bevy_audio-0.19.0/src/audio.rs:51-60` |
| TS | **YES, and it genuinely runs headless.** three sets `panningModel='HRTF'` by default on `PositionalAudio`; measured in Playwright: `AudioContext` state `running` at 48 kHz, and an `OfflineAudioContext` HRTF render produced real L/R divergence (ΣL 4482.6 vs ΣR 7713.1). **But `capture.ts` returns RGBA from a render target and nothing captures audio**, so none of it reaches any judge | E1 | `src/audio/PositionalAudio.js`; live probe; `capture.ts:70-80` |
| Unity | **NO — no audio at all at the pin, and no spatializer ships.** `find Unity.app -iname "*spatializ*"` returns **zero files**. `Manual/AudioSpatializerSDK.html` describes built-in panning as *"a simple form of spatialization… based on the distance and angle"* and says the HRTF example *"is intended for example purposes only"*, living in the external Native Audio Plugin SDK | E3ₗ for audio; E4 or E3ₙ for HRTF | probe; `Manual/AudioSpatializerSDK.html` |
| Godot | **CAVEAT — full spatial audio, no HRTF.** `AudioStreamPlayer3D` has `attenuation_model`, `max_distance`, `unit_size`, `panning_strength`, `emission_angle_*`, `attenuation_filter_*`, `area_mask`; `doppler_tracking`; `AudioEffectReverb` and the full bus API. **HRTF: 0 hits across all 1076 class XMLs and 0 hits in the binary strings** | E1–E2 | `AudioStreamPlayer3D.xml`; `grep -ci hrtf` = 0 |

**And the instrument discards it anyway.** `eval/judge/audio.py:117,135` decodes every clip to
**mono** float samples before analysis. Stereo image, panning and spatialisation are thrown away
by the grader before any criterion sees them. **No spatial-audio capability is observable today
in any arm.** That is a task-25 input, not a task-26 one.

### 6.12 Compute shaders

| stack | status | effort | source |
|---|---|---|---|
| Rust | **YES at the pin.** `bevy_render`'s `ComputePipeline`/render-graph API is in the `2d` bundle; `compute_shader_game_of_life.rs` imports only `bevy::render`, `core_pipeline` and `Camera2d`, all present. Cost is a render-graph node + WGSL + pipeline cache | E4 | vendored example imports; `bevy-0.19.0/examples/shader/compute_shader_game_of_life.rs:6-22` |
| TS | **NO.** WebGL2 has no compute. **WebGPU is unreachable**: `navigator.gpu` absent in **all eight** configurations tested — harness flags, no flags, `--enable-unsafe-webgpu`, `--use-webgpu-adapter=swiftshader`, `channel:'chromium'`, and `headless:false`. A GPGPU path does exist via `GPUComputationRenderer` (ping-pong render-to-texture, WebGL2-native, **E2**) and the WebGL fallback backend implements TSL compute over transform feedback | E2 for RTT-GPGPU; E4 otherwise | live probes; `examples/jsm/misc/GPUComputationRenderer.js`; `src/renderers/webgl-fallback/WebGLBackend.js:919-951` |
| Unity | **YES** — `ComputeShader`/`ComputeBuffer`/`GraphicsBuffer` in `CoreModule`; measured `supportsComputeShaders=True`, `graphicsShaderLevel=50`. Measured caveats: **`supportsAsyncCompute=False`**, **`supportsGeometryShaders=False`** (*"Metal doesn't support geometry shaders"*), `supportsTessellationShaders=True` | E2 | probe; `Manual/class-ComputeShader-introduction.html` |
| Godot | **CAVEAT — available, but not in the starter's headless path.** Full compute API (`compute_pipeline_create`, `compute_list_*`, `RDShaderFile`/`RDShaderSource`). **Measured blocker: `RenderingServer.create_local_rendering_device()` returns null under `--headless`, and still null with `--headless --rendering-driver metal`.** The windowed `film`/`test-render` recipes are unaffected | E2 dispatch / E4 real work | two headless probe runs; `RenderingDevice.xml` |

### 6.13 Multithreaded scheduling

**Every starter's determinism rules constrain this more than the engine does.**

| stack | status | effort | source |
|---|---|---|---|
| Rust | **YES** — `multi_threaded` is pulled in by `2d` → `default_platform`, so the parallel ECS executor is on. Starter rule 5 bans `par_iter` **reductions** in `sim` (float addition is not associative), not parallelism generally | E1 | `bevy-0.19.0/Cargo.toml` `default_platform`; `template/AGENTS.md` |
| TS | **CAVEAT** — Worker ✔, `hardwareConcurrency` 16, `OffscreenCanvas` ✔ with a working `webgl2` context, `transferControlToOffscreen` ✔, WebAssembly ✔. ⚠️ **`SharedArrayBuffer` absent and `crossOriginIsolated === false`** — `setContent` gives origin `null` with no COOP/COEP, so no zero-copy sharing and no wasm threads. And `src/sim` bans async, so the sim cannot live in a worker | E2 | live probe; `examples/jsm/utils/WorkerPool.js` |
| Unity | **CAVEAT — E2 on paper, blocked in practice.** `Unity.Jobs.JobHandle`, `IJobParallelFor`, `NativeArray<T>` are in `UnityEngine.CoreModule`. But `Assets/Sim` sets `noEngineReferences: true` (0 refs, measured) so it cannot see them, `Assets/View` is forbidden game logic, and starter rule 7 bans parallel reductions in `Sim` outright. Burst and DOTS are pre-cached (E3ₗ) | E2 / blocked | `UnityEngine.CoreModule.xml`; `Sim.asmdef`; `eval/starters/unity/AGENTS.md` |
| Godot | **YES** — `WorkerThreadPool` (`add_task`, `add_group_task`, `wait_for_*_completion`), `Thread`; `threading/worker_pool/max_threads = -1`; render thread model `1` (Safe). Starter rule 7 bans threads in `sim/` | E2 | `WorkerThreadPool.xml`; ProjectSettings probe |

### 6.14 Streaming asset loading

| stack | status | effort | source |
|---|---|---|---|
| Rust | **YES** — `bevy_asset` is in `default_app`, so `AssetServer` async loading is on at the pin | E2 | `bevy-0.19.0/Cargo.toml` `default_app` |
| TS | **CAVEAT, and it is a trap.** `FileLoader` uses `fetch` + `ReadableStream.getReader()` + `AbortController` — genuinely streaming. **But in the capture page (`about:blank`, origin `null`) a relative fetch THROWS** (*"Failed to parse URL from ./model.glb"*) and http fetch fails; **only `data:` and `blob:` return 200**. Assets must be inlined or generated | E1–E2 to write; **E4 to make it reach a filmed frame** | `src/loaders/FileLoader.js:133,141,157-174`; live fetch probe |
| Unity | **YES** — `Resources` + async scene load in `CoreModule`. AssetBundles are absent from the manifest (E3ₗ); Addressables are pre-cached (E3ₗ). Caveat: the starter commits **no** `.unity` scene and generates a throwaway empty one at build time | E1 | api scan; `Assets/Editor/BuildScript.cs` |
| Godot | **YES** — `ResourceLoader.load_threaded_request` / `load_threaded_get_status` / `load_threaded_get` | E1–E2 | `ResourceLoader.xml` |

### 6.15 Skeletal animation and glTF

| stack | status | effort | source |
|---|---|---|---|
| Rust | **YES\*** — `bevy_animation` **is** in the pin (via `common_api`), so an `AnimationPlayer`/`AnimationGraph` works. `bevy_gltf` and `gltf_animation` are **not** — they are in the `3d` bundle | E1 animation; E3ₗ glTF | `bevy-0.19.0/Cargo.toml` `common_api` / `3d_bevy_render` |
| TS | **CAVEAT, and it is a trap.** `GLTFLoader` ships with `setDRACOLoader`/`setKTX2Loader`/`setMeshoptDecoder` and 10× `KHR_materials_*`; `SkinnedMesh`/`Skeleton`/`Bone`/`AnimationMixer` are core, and skinning is a vertex shader so SwiftShader is fine. ⚠️ **`Clock` and `Timer` both read `performance.now()`, which `DETERMINISM_SCRIPT` pins to 0** (`harness.ts:273`) — a clock-driven `AnimationMixer` gets `delta = 0` and never advances, so **every captured frame shows the bind pose**. Drive it from the sim tick | E2 | `examples/jsm/loaders/GLTFLoader.js:85-99`; `src/core/Clock.js:71,120`; `harness.ts:266-277` |
| Unity | **CAVEAT** — `SkinnedMeshRenderer` is in `CoreModule` (bones as Transforms, driven yourself, `gpuSkinning: 0`). `Animator`/`AnimationClip`/`Avatar` are in `AnimationModule`, absent from `View` → E3ₗ. FBX/OBJ/DAE/DXF import works out of the box. **No glTF importer anywhere and no glTFast tarball** in the offline cache | E2 / E3ₗ / E3ₙ for glTF | probe; `Manual/3D-formats.html`; `ls .../PackageManager/Editor/` |
| Godot | **YES** — `Skeleton3D` (full bone API), `SkeletonModifier3D`, `SkeletonIK3D`, `SkeletonProfileHumanoid`, `AnimationPlayer/Tree/Mixer`; glTF in-tree with 21 classes (`GLTFDocument`, `GLTFState`, `GLTFSkin`, …); FBX module also present | E1 editor import / E2 runtime `append_from_file` | `docs/modules/gltf/doc_classes/`; `Skeleton3D.xml` |

---

## 7. Unresolved — what could not be established at the pinned version

Listed rather than guessed, per the ticket. Each says what would settle it.

| # | cell | what is unresolved | what would settle it |
|---|---|---|---|
| U1 | **Godot, §6.1 — Metal RT at runtime** | The API, the Metal backend and M3 hardware are all confirmed present, but `has_feature(SUPPORTS_RAY_QUERY)` was never observed true: a Metal `RenderingDevice` cannot be instantiated without a window, and both `--headless` and `--headless --rendering-driver metal` returned null. Also open: whether Godot gates on `supportsRaytracing` or the stricter `supportsRaytracingFromRender`, and the minimum GPU family | One **windowed** run on this M3 Max evaluating `RenderingServer.create_local_rendering_device().has_feature(...)` for `SUPPORTS_RAY_QUERY` and `SUPPORTS_RAYTRACING_PIPELINE`. **Deliberately not run — it opens a window on the operator's machine** (rule: their machine, their call) |
| U2 | **Unity, §6.4 — does PPv2 render through the capture path?** | Whether `com.unity.postprocessing` 3.4.0 actually affects `camera.Render()` → RenderTexture in batchmode. Not installed | Add it to a scratchpad copy, attach `PostProcessLayer` + a runtime-built profile, run `just test-render`, open the PNG. Unchanged ⇒ BiRP post is **E4 in practice for this harness**, not E3 |
| U3 | **Unity — do `BuiltInPackages` resolve offline?** | URP/HDRP/VFXGraph sit in the built-in folder but are registry-versioned (17.0.4) rather than `1.0.0` modules, so the E3ₗ/E3ₙ classification for them is inferred, not measured | Add `com.unity.render-pipelines.universal: 17.0.4` to a scratchpad manifest with the network down and read the `"source"` field in the regenerated `packages-lock.json`. `"builtin"` settles it |
| U4 | **Unity — is HDRP usable at all here?** | Only the Mono Mac player is installed (`modules.json` lists `webgl` + `documentation`; `MacStandaloneSupport/Variations/` are all `_mono`, `mac-il2cpp` absent). Every HDRP row assumes HDRP installs and builds | Add HDRP to a scratchpad copy and run `BuildScript.BuildMacOS`, checking `report.summary.result` |
| U5 | **Unity — Metal compute caveats scope** | The Manual scopes *"no atomics on textures, no `GetDimensions` on buffers"* to *"Metal (for iOS and tvOS platforms)"*. Whether it applies to macOS Metal at 45f1 is unestablished | Compile a `.compute` using `InterlockedAdd` on `RWTexture2D<uint>` and `buf.GetDimensions()`, and read the Metal shader-compiler output |
| U6 | **Unity — GPU vs CPU lightmapper on this M3** | `Manual/GPUProgressiveLightmapper.html`: *"On macOS it is more difficult to determine how much memory is available. As a result, fallback to CPU is more likely on this platform."* Whether it falls back here is unmeasured | Bake a static scene with `LightingSettings.lightmapper = ProgressiveGPU` in batchmode and grep the log for the fallback warning |
| U7 | **Unity — runtime ASTC** | `SystemInfo.SupportsTextureFormat(ASTC_6x6) = True`, but only the *importer* substitution was measured. Whether a runtime-created ASTC texture loads and samples on the Mac player is untested | `Texture2D.LoadRawTextureData` with `TextureFormat.ASTC_6x6` in a render test, asserting on sampled pixels |
| U8 | **TS — TSL compute correctness on the WebGL2 fallback** | `computeAsync()` resolved without error but `getArrayBufferAsync()` returned all zeros where 1998 was expected — **and the render-based control was non-discriminating** (1 lit pixel with *and* without dispatch), so it proves nothing either way. The transform-feedback implementation is real and double-buffers via `switchBuffers()`, a plausible reason a naive readback reads the stale buffer | Run three's own `webgpu_compute_*` examples from the repo (not the tarball) under `forceWebGL: true`, or read back through `StorageBufferAttribute` **after a second dispatch**. Until then compute on this path is neither working nor broken |
| U9 | **TS — cost of TSL node post-processing** | Measured 1.00 ms/frame scene-pass vs 1.25 with `bloom()` — bloom costing 0.25 ms where `UnrealBloomPass` costs 14.3 ms on the same rasteriser. **Not believable**: `renderAsync()` is async and the `readPixels`+`finish()` sync may not cover `RenderPipeline`'s internal targets | Time it via `readRenderTargetPixelsAsync()` on an explicit `RenderTarget`, as §6.4's `EffectComposer` numbers were |
| U10 | **Doc-version skew on the Unity column** | The offline Manual is stamped *"Built from 6000.0.47f1 (51c60e1b33cb), 2025-04-04"*, while every binary, DLL and package inspected is 6000.0.45f1. Only the prose is from the 47f1 stream | Cross-check any Manual-sourced Unity claim against the 6000.0.45f1 release notes before acting on it. Affects the feature-comparison-table rows (§6.2, §6.4, §6.5), not the measured ones |

**Two cells were *not* left unresolved because a measurement settled them**, and it is worth
saying which, because they were the ones most likely to be guessed: Bevy ray tracing on Metal
(settled by the wgpu probe, §3) and Godot's default physics engine (settled behaviourally with
both positive controls, §6.6).

---

## 8. Which of these plausibly matter for the current task set

The ticket is explicit that a capability a stack has is not thereby a capability that matters.
The four games are `g1_pong` (2D), `g2_tetris3d` (a **5×5×12** well — at most 300 cells),
`g3_arena` (3D twin-stick, *"Use no physics engine"*), `g4_platformer` (2D, sprite-sheet
animation, *"gravity is a constant, collisions are rectangles"*).

| capability | relevant here? | why |
|---|---|---|
| **Native particles** | **Yes — most of all** | A layer clear (g2), an enemy death (g3), a landing (g4) are exactly where particles land, and §5.1's effort gap is the widest in the matrix |
| **Post-processing / bloom** | **Yes, with a caveat** | Cheap in every arm at 12 frames, and readable at 640x400. The caveat is §9 |
| **Sprite atlasing** | **Yes** | `SPRITE_NOTE` asks for a sheet by name in all four stacks; g4 needs it |
| **Shadows / GI** | Partly | Only g2 and g3 are 3D, and both are small scenes with flat geometry. Real shadows would read at 640x400; GI would mostly not |
| **Spatial audio** | Marginal — g3 only | Enemies surrounding the player in 3D is the one honest case. **Currently unobservable: `audio.py` decodes to mono (§6.11)** |
| **GPU instancing** | Marginal | 300 cubes and a few dozen bullets. It changes no visible pixel and no captured metric; it is an `idiomatic` signal, not a performance one |
| Ray tracing | **No** | §5.3 — unreachable at ≤E3 in all four arms |
| LOD / mesh simplification | **No** | Peak geometry is ~300 unit cubes. No LOD system can ever bind |
| Texture compression | **No** | A handful of generated PNGs. Format choice is invisible in the artifact and in every criterion |
| Streaming asset loading | **No** | Same reason. And the TS capture page cannot fetch a file at all (§6.14) |
| Compute shaders | **No** | No game in the set has work that wants a compute pass |
| Multithreaded scheduling | **No, and partly forbidden** | The sims are tiny, and every starter bans parallel reductions in `sim` (§6.13) |
| Native physics | **No — see §5.2** | Two prompts forbid an engine; all four starters make one structurally unreachable from where the rules live |
| Skeletal animation / glTF | **No** | g4 asks for a *frame-indexed sprite sheet*, explicitly, in all four stacks |

**Nine of fifteen surveyed capabilities are irrelevant to the current task set.** That is a
result, not a gap in the survey: it means task 26's surface is much smaller than
"what these engines can do", and the argument for each inclusion has to be made here rather than
inside a template change.

### One thing this survey turned up that belongs to somebody else

`eval/starters/godot/tools/boundary.gd` bans `PhysicsServer2D` inside `sim/` and **does not ban
`PhysicsServer3D`** — a `RefCounted` in `sim/` can call it directly. Node types are covered
indirectly (`_physics_process`, `add_child`, `queue_free` are all banned), so this is narrow, but
it is the exact shape `AGENTS.md`'s own rule audit warns about: *"a rule whose trigger is a list
must be re-derived by every reader who meets an item not on the list."* If task 26 goes anywhere
near Godot physics, that ban list needs auditing first. **Not fixed here** — this task changes
no template.

---

## 9. The `ux` / #59 question: which recommendations would move a valid signal

The ticket's sharpest constraint. #59, replicated as **#78** on three games (Spearman on average
ranks, n=8 per game): `ux` ~ distinct colours = **+0.528** (`g2_tetris3d`), **+0.733**
(`g3_arena`), **+0.573** (`g4_platformer`). `ux` was retired for it. Bloom, soft shadows, GI and
particles all raise distinct-colour count enormously, so making the games prettier moves a
retired metric in the direction that looks like improvement.

**But #78 says something more specific than "prettier is invalid", and it is load-bearing:**

> *"it proves the aspect is dominated by a property of the renderer rather than of the authored
> work, which is disqualifying for a **cross-stack** comparison and says nothing about a
> **within-stack A/B**."*

That splits the recommendations cleanly.

| a capability change that… | verdict |
|---|---|
| **widens the cross-stack colour gap** | Contaminated. The spread is already ~60-fold; SwiftShader/TS structurally sits at the bottom (§3) and cannot be raised without changing the capture path, which is task 25's business, not task 26's |
| **is evaluated as a within-stack A/B** — same stack, same task, template with vs without | **Not contaminated by #78.** This is the only design under which "the one with particles scored higher" is falsifiable |
| **moves an aspect that reads code** (`idiomatic`, `architecture`) | **Valid, and it is the strongest available signal.** `idiomatic` asks *"was the stack used as that stack is meant to be used"* and `sees: code`. A stack that ships `GPUParticles3D` and a submission that hand-rolls a sprite loop instead is exactly what it is for — and it is palette-blind by construction |
| **moves `audio`** | **Valid in principle, unobservable in practice.** `audio` reads decoded clip files, not frames. But `audio.py` decodes to **mono** (§6.11), so anything spatial is discarded before scoring |
| **moves `fun_frames`** | **Probably valid.** It reads the same pixels as `ux` and correlates **-0.120** with distinct colours (#78), which is what establishes the frames channel is not intrinsically contaminated |

**Read against the capability list, per capability:**

| capability | effect on the judge layer |
|---|---|
| **Particles** | **The best case in the matrix.** A particle burst on a line clear is a *legible event marker* — it tells the player what just happened, which is `fun`/`fun_frames` territory, not palette depth. It also raises colour count, so it must not be scored cross-stack. And it is a first-class `idiomatic` signal on all four arms |
| **Bloom / post-processing** | **Pure #59 risk.** Bloom's entire mechanism is spreading luminance across pixels that did not have it — a distinct-colour generator with no independent readability claim. Cheap in all four arms and therefore tempting. **The clearest "louder version of #59" in the matrix** |
| **Soft shadows / GI** | Mostly #59, with a thin real claim: contact shadows communicate *where a piece will land* in g2, which is a genuine readability property. Would need an argument on that basis, not on looks |
| **Antialiasing** | **Pure #59, and worse than bloom** — AA raises distinct-colour count almost by definition, along edges, changing nothing a player can act on. Note the Godot starter turns `msaa_2d` off deliberately for byte-exact render tests |
| **Sprite atlasing** | **Valid, `idiomatic`-only.** Invisible in frames if done right; visible in code |
| **GPU instancing** | **Valid, `idiomatic`-only.** No pixel changes |
| **Spatial audio** | **Would be valid, and is currently unmeasurable** (mono decode). A task-25 item |
| Ray tracing / LOD / compression / streaming / compute | Not reachable, or not relevant — §5.3, §8 |

**Conclusion for task 26.** Two capability classes are worth pursuing and they are worth pursuing
for different reasons: **particles**, because the effort gap is real and the effect is a legible
event marker rather than only a palette; and **the code-visible ones — atlasing, instancing,
using each engine's native constructs** — because `idiomatic` reads code and is palette-blind, so
they can be scored today without any of #59's problem. **Bloom and antialiasing should be
declined**, and §5.3's finding means ray tracing is not a decision anyone has to make.

And the gate stands: **without task 25, none of this is falsifiable.** The judged evidence is 12
PNGs at 640x400 plus mono audio plus gameplay-event telemetry, which is why a submission that
ray-traces and one that draws flat quads produce the same record.

---

## 10. What this document does not establish

- **It does not measure anything about agents.** Every "effort" tier is a judgement about API
  surface, not an observation of what an agent did. Nothing here has been through a trial.
- **It does not establish that a reachable capability will be reached.** E1 means an agent
  *could*; whether one does under a turn budget is an empirical question this survey cannot
  answer and §8's relevance column cannot either.
- **The effort tiers are the softest thing in it.** Status cells are sourced to a file or a
  measurement; tiers are calibrated judgement across four ecosystems by four different readers.
  Treat an E1/E2 boundary as approximate and an E2/E3 boundary as sharp — the latter is a fact
  about a manifest.
- **It is version-locked and will rot fast.** Bevy publishes breaking releases quarterly and
  three does so monthly. Re-derive from §1's sources rather than trusting a cell after the next
  pin bump; a stale cell here is worse than no cell.
- **The Unity prose rows carry a doc-version skew** (U10): the offline Manual is 47f1-stream
  while the binaries are 45f1. The measured Unity rows do not.
- **One unresolved cell — U1, Godot's Metal ray-tracing runtime check — is unresolved because
  resolving it requires opening a window on the operator's machine.** That is their call, not
  ours. The other nine are unresolved for ordinary reasons: an install not performed, a bake not
  run, a readback that needs a better control.
