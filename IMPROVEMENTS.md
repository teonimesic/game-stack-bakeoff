# Improvement loop — the templates

`eval/IMPROVEMENTS.md` is the same loop for the **evaluator**; this file is the loop for the
**product** — `eval/starters/*/` and the task prompts.

Each iteration is a hypothesis, a change, and a measurement that could have come out
against it. The falsification criterion is written **before** the measurement runs.
A reverted change is a successful iteration: it bought a real answer.

An iteration that ends "I improved X" with no number attached has measured nothing.

**The trigger is a change, not an occasion**, and the boundary between an iteration and a
finding is the same for both loops. `eval/IMPROVEMENTS.md`'s preamble states it.

---

## Iteration 1 — does the play-bot tier notice a game no human can play?

**Status: PRE-REGISTERED, not yet run.**

> **Still true, re-verified 2026-09-02.** Nothing added since grades the device-input path:
> every tier-1 id and every tier-2 id is probe/simulation-path, and #128's four harder
> criteria replay a *played* tape through the same probe. The execution is filed as
> `tasks/233` (offline, no agent spend); this note exists so the next reader does not
> re-derive that the iteration is still live.

### Why this first

The play-bot tier carries **the whole grade** — 0.69 of it when this was written, and 1.00
since tier 1 became a gate on 2026-08-23 (`eval/judge/RUBRIC.md`) —
and it has only ever been validated against artifacts where the answer was obvious:
three reference implementations scoring 13/13, 13/13 and 15/15, and two broken controls
scoring 0/13. That is the identical ceiling error already written up for the LLM judge
in FINDINGS #21: reliability measured where reliability is cheap.

### The suspected gap

The play-bot reaches the simulation **only** through `just probe`. It never exercises
the view layer or the device-input path. Tier 1 checks that frames render and that
consecutive frames differ — but frames animate from the simulation alone, so a
submission whose keyboard handling is broken still passes.

The task's definition of done says *"`just run` opens a window and the game is actually
playable with a keyboard."* Nothing in the grading system tests that clause.

### Hypothesis

A submission whose probe path is correct but whose **view-layer keyboard-to-intent
wiring is severed** will score **unchanged** on tiers 1 and 2 — i.e. the grading system
cannot distinguish a playable game from an unplayable one.

### Falsification

If severing the keyboard path drops the tier-1 or tier-2 score **at all**, the
hypothesis is wrong and the tiers already cover this. I will report that outcome and
keep the tiers unchanged.

### Method

1. Take a completed matrix submission (extracted from its archive, so the original is
   untouched).
2. Sever only the view layer's keyboard-to-intent wiring. Do not touch the simulation,
   the probe, the tests, or the justfile.
3. Confirm the submission still builds and `just verify` is green — otherwise tier 1
   fails for the wrong reason and the experiment says nothing.
4. Run tiers 1 and 2 on both the pristine and the severed copy.
5. Compare per-criterion, not just totals.

Offline; no agent spend.

### Predicted result

Tier 1 unchanged at 9/9, tier 2 unchanged at 13/13, `overall` unchanged at 1.000.

### If confirmed

Add a criterion that exercises the real input path — the cheapest honest version is a
check that the view layer actually maps device input to the simulation's intent type,
since driving a real window from the harness is not portable across all four stacks.
Then re-measure: the severed copy must fail it and the pristine copy must pass it.
Both directions, or the new criterion is worth nothing.

---

## Iteration 2 — a design judge for aesthetics and game feel

**Status: PRE-REGISTERED, not yet built.**

> **Built, and its falsification has never run (established 2026-09-02).**
> `judge/judge_design.py` and `judge/design_criteria.py` exist with exactly this shape —
> frames + telemetry, no source, anchored 0–4, no weight until separation — and price their
> calls through `tokenvalue.py`'s PRODUCERS. No stored round, no doc, no decision records a
> run. `tasks/234` is filed to run the tuned-vs-detuned measurement or retire the module as
> superseded by the aspect tier; until then this status line is false in the other direction.

### Why this is not a reversal of dropping the code judge

The code judge scored 13 binary criteria about code hygiene, and the deterministic
tiers already covered most of what it could see — so it was droppable at no loss.
Aesthetics and feel are the opposite case: **the play-bot can prove the ball bounces
and cannot tell you whether the game looks good or feels good to play.** No
deterministic tier will ever cover that. If it is to be measured at all, a subjective
judge is the only available instrument.

### What it sees

Not source code. The artifact as a player meets it:

- **Rendered frames as images**, several across a real play session, so motion,
  feedback and state changes are visible.
- **Play-bot telemetry as evidence of tuning**, not just correctness — pacing,
  time-to-first-meaningful-action, rally lengths, time-to-score, round duration,
  difficulty ramp, and whether anything ever stalls. Already collected; currently used
  only to assert things work.

### Criteria

Graded with stated anchors, not binary. Binary was right for "is there a placeholder";
it is wrong for "does this look good", where the information is in the middle.
Dimensions: visual coherence, readability of game state at a glance, feedback and juice,
pacing and tuning, polish (start state, end state, score, anything beyond a bare
mechanic).

### The measurement that decides whether this tier is worth anything

Two fixtures **differing only in the judged dimension** — same game, same mechanics,
same tests passing:

* **tuned**: legible palette, visible score, sane ball speed, visible feedback on events
* **detuned**: ball ~3x too fast, no visual feedback, low-contrast colours, no score
  readout

### Falsification

**If the design judge cannot separate the tuned fixture from the detuned one, it
measures nothing and does not ship.** I will report that plainly rather than keeping it
as a diagnostic that looks like signal.

Separation must exceed run-to-run noise: the tuned-vs-detuned gap has to be larger than
the spread across repeated judgings of the *same* fixture. A difference smaller than the
instrument's own variance is not a difference.

### Also required before it can be trusted

- Validate on **borderline** artifacts, not just the two extremes — a gorgeous and a
  broken submission will both judge unanimously and prove nothing (FINDINGS #21).
- Report **run-to-run variance on identical input** and forward/reverse instability
  **separately**. Subjective criteria are expected to be noisier; the question is
  whether they discriminate despite the noise, not whether they are quiet.
- Check every criterion is **exercised**. A criterion answered identically every run
  because the question never arose has not been tested.

### Weight

**None, pending validation.** Deciding a weight before knowing whether it separates a
well-tuned game from a badly-tuned one would repeat exactly the error that made the
code judge worthless at 0.10.

---

## Iteration: make Unity's `lint` answer the same question twice (FINDINGS #66)

**Not yet applied.** `starters/unity` is the product under measurement; editing it is a regime
boundary and requires re-running `verify_blind.py` and `starter_parity.py`. Filed here so the
change is made deliberately, between matrices, rather than mid-analysis.

### The observation

`g4_platformer__unity__t1`'s agent ran the gate it was told to run and was told it passed:

```
✓ lint: all assemblies compile clean
✅ verify passed
```

The same tree, extracted from its own `submission.tar.gz` into an empty directory, fails
`just lint` with exit 1 and five `CA1861` errors. The tarball and the work tree are byte-identical
on the offending file. The Editor assembly was not re-analysed after the agent's edit, so
violations that were still in the file never reappeared.

### The hypothesis

> **Unity's `lint` recipe reports the state of the build cache, not the state of the code.
> Forcing the analyzer to re-run will make a cold and a warm `just lint` agree.**

Candidate change: have `lint` build with analyzers forced (a clean or non-incremental
compile of the Editor and player assemblies) rather than accepting whatever the cache holds.

### MEASURED 2026-08-22 — hypothesis confirmed, mechanism named

Run on `g4_platformer__unity__t1` (`wg-g4c-2026-08-21`), a tree known to hold five CA1861
violations. Three arms, same submission, one copy each:

| arm | `Library/` state | `just lint` | wall |
|---|---|---|---|
| **A** — as it is today | full warm cache | **exit 0**, "all assemblies compile clean" | 8.9s |
| **B** — `Library/ScriptAssemblies` deleted | asset cache kept | **exit 0** — still wrong | 4.9s |
| **C** — whole `Library/` deleted | cold | **exit 1, all five CA1861 reported** | 10.9s |

**The cause is `tools/unity-compile.sh` copying `Library/` into its scratch project.** It already
compiles against a copy, to dodge Unity's project-wide lock, and strips only `artifacts/` and the
lock — so the warm build cache travels with it and Unity re-uses cached analysis for assemblies
it considers unchanged. A violation still in the file is never re-reported.

**Arm B is the informative negative.** Deleting the compiled assemblies is not enough; the
analysis is cached elsewhere under `Library/`. A surgical fix aimed at `ScriptAssemblies` would
have looked principled, changed nothing, and shipped as a repair.

### The cost objection did not survive measurement

This entry worried that a cold compile would slow `verify`, which agents run often, and that a
slower gate gets run less. **Measured: 10.9s cold against 8.9s warm — two seconds.** The worry
was reasonable and it was wrong.

The fast inner loop can still be preserved exactly: scope the change to `STRICT=warnings`, so
`just lint` (the authoritative gate) goes cold while `just check` (errors only) stays warm.

### The change, PREPARED AND NOT APPLIED

One line in `starters/unity/tools/unity-compile.sh`, immediately after the copy:

```sh
# The copy inherits Library/, so Unity re-uses cached analysis and a violation still in
# the file is never re-reported (#66). The strict gate must answer from the code.
[ "$STRICT" = "warnings" ] && rm -rf "$WORK/proj/Library"
```

`starters/` is the product, so applying this is a **regime boundary**: it needs
`judge/verify_blind.py`, `judge/starter_parity.py` and a `eval/RUNS.md` comparability note, and
no future matrix would pool with any previous one on Unity. **Awaiting a decision.**

> **Applied — the decision was made and this section was never closed out (established
> 2026-09-02).** The prepared guard is in `eval/starters/unity/tools/unity-compile.sh` under
> `if [ "$STRICT" = "warnings" ]`, with the arm-B negative and the ~2 s cold-path cost recorded
> in its comment. The predicted consequence is visible and verified: `g4_platformer__unity__t1`
> is in tier 1's failing 8 — `verify.green` and `lint.clean` both exit 1 on the re-grade — while
> its tier 2 stays 1.000. The submission ships code failing its own strict gate; #66 remains
> valid as a description of what the agent was told at the time.

**Pins to run with it, both directions:** arm A must go exit 0 → exit 1 with five CA1861, *and* a
tree with no violations must stay exit 0. Without the second, this is a gate proved only in the
failing direction.

**One consequence, stated plainly:** with this applied, `g4_platformer__unity__t1` becomes a
genuine `verify.green` failure rather than a template defect — that submission really does ship
code failing the project's own strict gate. #66 remains valid as a description of what the agent
was told at the time, which is what made it not-a-submission-defect *then*.

### The original falsifier, kept

On a tree **known** to contain violations, run `just lint` warm and cold and compare exit codes.
The change is only justified if they currently disagree and agree afterwards.

Two outcomes and what each would establish:

| outcome | reading |
|---|---|
| cold and warm disagree now, agree after | the defect is incremental analysis, and the fix holds |
| they agree now | #66 has another cause and this change is cosmetic — **do not ship it** |

The second is a real possibility and must be checked first: the evidence for #66 is a clean
*extract*, which differs from the work tree in more than cache state, and that difference has not
been isolated. **Establish the mechanism before changing the product.**

### What it cuts against

It makes `verify` slower, and `verify` is the command the templates ask agents to run often —
the justfile says so in its own header. A slower gate is run less, and an agent that stops
running the gate is a worse outcome than a gate that is occasionally stale. If forcing analyzers
costs more than a few seconds, the honest fix may be a separate `lint-cold` recipe used by the
grader, plus wording in the template that the fast path is incremental.

### Scope

This is not a `g4` problem. The gate has been green on the Unity arm across four matrices and
nothing has ever compared its answer to a cold build, so **"Unity passed lint" has never been the
claim it appeared to be**. `starter_parity.py` compares recipe *text*, not recipe
*reproducibility*, which is why it never fired — a second gap worth its own iteration.

---

## Iteration: each template at its own stack's best — rust and godot, 2026-08-23

Task 26, on the evidence base of `research/10-stack-capability-matrix.md` (task 24) and the
fields of `judge/capability.py` (task 25). `DECISIONS.md` decided the design; this is the
first instalment of it, and it covers **two arms of four**.

### The rule that decided every case below

> **A template exposes what its stack SHIPS. It does not implement what its stack lacks.**

Lowering a capability from E2/E3 to E1 for something the engine already contains is exposing
it. Writing the subsystem (E4) is manufacturing one — and it would erase exactly the
asymmetry the decision exists to measure. §5.1 of the survey makes native particles the
widest effort gap in the matrix; a template-provided emitter for Bevy or three.js would
delete that gap and report a number about four template authors.

### What changed, and the field that would move

Every entry names an observable that is **palette-blind**, because `ux` was retired for
correlating +0.53 to +0.73 with distinct-colour count (#59, replicated as #78) and a change
whose only consequence is more colours cannot be shown to have helped.

| arm | change | field that would move if it worked |
|---|---|---|
| **rust** | `bevy` features `["2d","png","libm"]` → Bevy's own default set `["2d","3d","ui","audio"]` + `wav`, `png`, `libm` | `idiomatic` (reads code): a 3D game built from `Mesh3d` + `MeshMaterial3d` and lights instead of orthographic sprites. Tier-1 `audio.*`: the arm can now open an audio device at all. `capture.cpu_seconds` and `capture.peak_rss_mb`: a lit 3D scene costs more than flat quads, measured from outside the submission |
| **rust** | `AudioPlugin` disabled on the capture path, and on `just run` under `STARTER_SILENT_LAUNCH` | Nothing scored — this is the guard the new capability requires. Measured: `just test-render` 11.7 s → 8.5 s, which is what opening a device six times cost |
| **godot** | `view/fx.gd`: `GPUParticles2D` as one call, deterministic under the capture path | `idiomatic`: Godot is the only arm with a native particle system, and a submission that hand-rolls a `draw_rect` loop instead is exactly what that aspect is for. `fun_frames`: a burst is a legible event marker, and it correlates **−0.120** with distinct colours (#78), which is what makes the frames channel usable where `ux` is not. `capture.cpu_seconds` |

### The hypothesis, and what would falsify it

**Hypothesis.** Effort, not availability, is what decides whether a capability reaches a
submission. Two of four games are 3D and the Rust arm could not render a lit 3D mesh at all;
`AUDIO_NOTE["rust"]` named an API that did not exist at the pin. Removing those two
pin-changes should change what Rust submissions contain, not merely what they could contain.

**Falsifier, written first.** Re-run `g2_tetris3d` and `g3_arena` on the Rust arm under the
new starter. If the submissions still build orthographic sprite scenes and still ship no
audio, then the pin was not what was stopping them, the ~103 s of extra cold build bought
nothing, and this iteration should be reverted. Likewise for Godot: if no Godot submission
touches `Fx` on a task with an obvious event to mark, the file is dead weight and the
capability was never reachable in the way this claims.

**What is NOT claimed.** Nothing here has been through a trial. The survey's effort tiers are
judgements about API surface (§10 of the matrix says so), and this iteration inherits that
limit. It is also **not** a claim that scores will rise: a bigger engine is more rope.

### Measured costs, all on the grading machine, 2026-08-23

| | before | after |
|---|---|---|
| rust cold `just verify` from an empty target dir | warm 129 s + verify 38 s = **167 s** | warm 248 s + verify 22 s = **270 s** |
| rust warm `just verify` | **2.7 s** | **4.2 s** |
| rust warm `just quick` (the documented inner loop) | — | **0.8 s**, links none of it |
| godot `just verify` | 4.4 s, 17 sim + 6 render assertions | **3.4-4.5 s**, 17 sim + **9** render assertions |

The godot row is **not a clean comparison and is not offered as one**: the 4.4 s was measured before `just warm` had created the gdtoolkit venv, so `fmt` and `lint` skipped themselves. What it does establish is that three more render assertions, each of them a GPU capture, did not move the gate out of its ~4 s band.

### Surveyed as available and DELIBERATELY NOT ADOPTED

The ticket asks for this list, and it is a deliverable rather than a leftover: a capability
rejected for a stated reason is evidence; one that was never considered is a gap.

| capability | arm(s) | why not |
|---|---|---|
| **Bloom / post-processing** | rust (E1 at the pin, `bevy_post_process` registers `Bloom` on `Core2d`), godot (E1, `Environment` glow) | **#59, in its loudest form.** Bloom's entire mechanism is spreading luminance onto pixels that did not have it — a distinct-colour generator with no independent readability claim. It is cheap in every arm and therefore tempting, which is what makes stating the refusal worth more than the refusal itself. It is compiled and reachable; the template does not pre-enable it |
| **Antialiasing** | rust (`bevy_anti_alias`, now compiled), godot (`Viewport.msaa_2d`, FXAA, SMAA, TAA) | Worse than bloom on the same ground: AA raises distinct-colour count almost by definition, along edges, and changes nothing a player can act on. In Godot it additionally breaks `tests/render_test.gd`'s byte assertions, so it would look like a rendering bug |
| **A particle system for rust or ts** | rust, ts | Bevy 0.19 ships none (no `particle` module in the crate tree) and three 0.185 ships none (`Object.keys(THREE).filter(/particle/i)` → `[]`). Writing one in the template is E4 work the agent would have to do, done for it — the one thing the ticket forbids, and it would erase the matrix's widest effort gap |
| **Ray tracing** | all four | Unreachable. Bevy's Solari needs `BUFFER_BINDING_ARRAY`, which wgpu 29 sets only on Vulkan, **and fails open with a `warn!`**; Unity measures `supportsRayTracing = False` with no Metal acceleration-structure selectors; Playwright exposes no `navigator.gpu` in any of eight configurations; Godot has the `RenderingDevice` API and no scene-renderer integration. `judge/capability.py` declines `render.ray_tracing` for the same reason: the field would be a constant |
| **Godot 3D post-processing / `WorldEnvironment`** | godot | `project.godot`'s `[rendering]` block exists so `tests/render_test.gd` can assert exact byte values. A tonemapper or an sRGB round trip changes those bytes without changing any geometry, and the failure reads as a rendering bug that is not one |
| **Native physics** | godot (Godot Physics default, Jolt in-tree), unity (PhysX one manifest line) | Two of the four prompts forbid a physics engine outright, and **all four starters make one structurally unreachable from where game rules must live** — `Sim.asmdef`'s `noEngineReferences`, `tools/boundary.gd`'s node ban, `crates/sim/tests/boundary.rs`, the `src/sim` firewall. Shipping it would showcase a capability the architecture forbids using |
| **Spatial audio / HRTF** | ts (HRTF measured working), godot (full `AudioStreamPlayer3D`) | **Structurally unobservable.** `judge/audio.py` decodes every clip with `-ac 1`, so the channel layout is discarded before any analysis runs, and the shipped clip FILES are all the harness ever hears. `judge/capability.py` declines `audio.spatialisation` for the same reason. A task-25 item, not a task-26 one |
| **GPU instancing, LOD, texture compression, streaming, compute, multithreading, skeletal animation/glTF** | various | §8 of the survey: irrelevant to the current task set. Peak geometry is ~300 unit cubes; the sprite note asks for a frame-indexed sheet by name; every starter bans parallel reductions in `sim`. Nine of fifteen surveyed capabilities are in this row, which is a result rather than a gap |
| **Sprite atlasing** | all four | Available and relevant, and **not adopted because nothing needed adding**: `TextureAtlas`/`TextureAtlasLayout` (rust) and `AtlasTexture` (godot) are already E1 at the pin. Both AGENTS.md files now name them. Exposing a capability that is already one line away is documentation, not scaffolding |

### Not done — two arms, stated so nobody reads silence as coverage

**TypeScript and Unity were not touched.** Both have a clear next step and neither was taken:

- **unity**: `com.unity.modules.audio` and `com.unity.modules.particlesystem` are one manifest
  line each (E3ₗ, both ship inside the editor), and audio has a **scored criterion** behind
  it that the arm currently cannot satisfy at all. This is the single highest-value
  outstanding item in this task and it is left open deliberately: it needs a batchmode
  editor run to regenerate `packages-lock.json` and a re-run of `unity-compile.sh`, which is
  a longer verification loop than the two arms above.
- **ts**: `EffectComposer` and the 29 shipped passes are declined above; the genuine
  candidates are `InstancedMesh`/`BatchedMesh` and `Points`, where the survey measured 50 000
  points at **4.1 ms** against 50 000 `InstancedMesh` at **590 ms** on SwiftShader (144×) —
  the largest single measured capability effect in the matrix, and one that lands directly in
  `capture.cpu_seconds`.

  > **Both sentences in this bullet are wrong, and task 52 measured why (#110).** The 144×
  > is `Points` against `InstancedMesh`, not against the N-separate-meshes baseline a
  > submission would otherwise write — against that, instancing is worth 5-6% at every size
  > on this rasteriser. And `capture.cpu_seconds` covers the whole of `just film`, which
  > costs 3.91 s of CPU on the pristine starter, so at this task set's ~300 objects the
  > entire difference is 55 ms. Left in place rather than edited, because it was acted on.

---

## Iteration: each template at its own stack's best — unity and ts, 2026-08-23

Task 52, the second and final instalment. Same evidence base, same rule, the two arms task 26
deliberately stopped short of. `eval/RUNS.md` records it as the **thirteenth** comparability
break.

### What changed, and the field that would move

| arm | change | field that would move if it worked |
|---|---|---|
| **unity** | `Packages/manifest.json` gains `com.unity.modules.audio`; `packages-lock.json` regenerated, resolving it `source: "builtin"` | Tier-1 `audio.*`, which is **scored**. Before this the arm could not compile the API the prompt names: measured on the pristine tree, `AudioSource`/`AudioClip` give four `error CS1069 … forwarded to assembly 'UnityEngine.AudioModule'` and `just check` exits 1. `idiomatic`, which reads code: a submission triggering `AudioSource.PlayOneShot` rather than explaining in prose why it shipped none |
| **unity** | `com.unity.modules.particlesystem`, plus `Assets/View/Fx.cs` exposing Shuriken as one call, with `GameView` owning an idle `Fx` | `idiomatic`: godot and unity are the only two arms with a native particle system, and a submission that hand-rolls a quad-spawner instead is exactly what that aspect is for. `fun_frames`: a burst is a legible event marker, correlating **−0.120** with distinct colours (#78), which is what makes the frames channel usable where `ux` is not. `capture.cpu_seconds` |
| **ts** | **Nothing in the code, the pins or the recipes.** One `AGENTS.md` section carrying the measurement below | `idiomatic` only — and that is why nothing was built. See the decline register |

### The falsifier, written first

**Unity.** Re-run any game on the Unity arm under the new starter. If submissions still ship no
audio, the manifest line was not what was stopping them — an agent that *could* have added it
itself all along, at the cost of asking permission it was told to ask for. Likewise `Fx`: if no
Unity submission touches it on a task with an obvious event to mark, the file is dead weight.

**The uncomfortable half, stated because it is the more likely outcome for `Fx`.** Godot's
equivalent has never been through a trial either, so a null result would be about **two** files
and would say the particle asymmetry the survey calls the widest effort gap does not reach a
submission at all. That is a finding about the survey's effort tiers, not about the templates.

### Measured costs, on the grading machine, 2026-08-23

| | before | after |
|---|---|---|
| unity warm `just verify` | ~12 s, 26 sim + 6 render assertions | **15.8 s**, 26 sim + **9** render assertions |
| unity `just check` (the fast inner loop) | ~6 s | **6.1-6.7 s** |
| unity `packages-lock.json` | 7 entries | 9, both new ones `builtin` — resolved from the installed editor, network irrelevant |
| ts anything | — | unchanged; no code, no pin, no recipe touched |

### The three new render tests, and the mutant that pins them

`ABurstIsDrawn`, `ABurstAges`, `RenderingIsReproducibleWithABurstOnScreen`, mirroring godot's
three. Commenting out the single `view.Fx.ShowBursts(bursts)` line in `RenderHarness` turns the
first two red — *"a burst added 0.0000% ink to a frame that already had 0.4660%"*, *"differ in
only 0.0000% of pixels"* — and leaves the other seven green. The golden frame is **unchanged**:
an idle `Fx` builds no GameObject, no material and no emitter until asked.

`ABurstAges` is the **variant**, not the mutant (`AGENTS.md` rule 15): an emitter frozen so hard
it never advances would pass the reproducibility test perfectly, so two ages must produce two
pictures or `age` is decorative.

### Surveyed as available and DELIBERATELY NOT ADOPTED

| capability | arm(s) | why not |
|---|---|---|
| **`InstancedMesh` / `BatchedMesh`** | ts | **Measured, and it is not the win the task-26 note said (#110).** 640x400, SwiftShader, ms/frame incl. readback: at 300 objects 4.73 instanced vs 5.06 for N meshes; at 2 000, 28.47 vs 30.19; at 10 000, 140.68 vs 149.16. **5-6% at every size.** The 144× that made it a candidate was instancing measured against *`Points`*, not against the baseline a submission writes |
| **`Points`** | ts | A real **10.3×** at 300 objects (0.49 vs 5.06 ms) — and **not adopted as scaffolding, because it is already E1 and five lines.** `capture.cpu_seconds` covers all of `just film`, measured at **3.91 s of CPU** on the pristine starter, so twelve frames × 4.6 ms = 55 ms is unresolvable. The only field left is `idiomatic`, and a wrapper adds surface without adding reach. Documented instead, with the table and the one trap that costs a turn: under an orthographic camera `PointsMaterial.size` is device pixels and `sizeAttenuation` is **ignored**, because three 0.185's point shader guards attenuation with `if ( isPerspective )` |
| **A particle system for ts** | ts | Unchanged from task 26 and now load-bearing in the other direction: unity has one and ts does not, so the 2/2 split in `starter_parity`'s register is the measurement. Writing an emitter into the ts template would delete it |
| **`com.unity.modules.physics` / `.physics2d`** | unity | Unchanged from task 26. Two of four prompts forbid a physics engine and `Sim.asmdef`'s `noEngineReferences` makes one structurally unreachable from where game rules must live |
| **`com.unity.modules.animation`** | unity | E3ₗ and one manifest line, and **declined for the same reason `Sim` cannot see it**: `Animator` state is engine-owned, frame-driven and outside `StateHash`, so a submission driving gameplay from it fails determinism rather than gaining a capability. `SkinnedMeshRenderer` is already in `CoreModule` for the bones-as-Transforms path |
| **`com.unity.postprocessing` (BiRP PPv2)** | unity | #59, exactly as bloom was declined in task 26 — and it is worse here: U2 in the survey's open list asks whether PPv2 even renders through `camera.Render()` into a RenderTexture in batchmode, and nobody has measured it. Adopting an effect that may be invisible to the capture path, in service of a palette-coupled field, is two errors |
| **Unity GPU instancing** | unity | E2 and measured `supportsInstancing = true`, but `Assets/View/Flat.shader` would need `#pragma multi_compile_instancing` and §8 of the survey applies unchanged: peak geometry is ~300 unit cubes. The ts measurement above is the direct evidence — one batched draw against N is 5-6% on a software rasteriser, and Unity's capture path runs on real Metal, where it is smaller still |

### What was checked and found sound rather than changed

- **Does the audio module open a device on the capture path?** No, and the reason is not the
  one anybody would have guessed — the batchmode editor already ran an FMOD CoreAudio output
  with **no audio module and `-disable-audio` set**. Three arms, pristine as the control:
  **#109**. No new guard was needed; the flag's rationale was repaired instead.
- **`StarterLaunchGuard`'s live branch.** Written by reflection in anticipation of exactly this
  change, and never once executed. It now logs *"SILENT LAUNCH ACTIVE — AudioListener.volume=0,
  pause=True"*, against a control launch that logs *"silent launch NOT requested"*.
- **#106 on the two arms it could not reach.** Independently re-measured here: unity's
  `tools/fmt.mjs --check` and ts's `prettier --check .` are both clean on the pristine tree,
  and `just verify` leaves both trees untouched. Task 51 had already established this with a
  stronger control in `starter_gate_control.py`; this is corroboration, not a new result.
