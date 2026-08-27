# Scenes: a second task class

A **scene** is a timed audiovisual sequence with no player. It asks a different question from a
game: not *can the agent build working interactive logic*, but *can it drive the stack's
rendering and animation facilities*, and *how much does a rich engine actually buy there*.

Scenes are graded, stored and reported separately from games. **Never pool a scene score with a
game score** — different task class, different criteria, different tier weights.

## The contract, which already exists

Every starter's capture harness makes a frame **a pure function of `(seed, ticks, inputs)`**
(`eval/starters/*/AGENTS.md`). A scene is that contract with `inputs` dropped:

    frame(seed, tick)   — deterministic, headless, no wall-clock

So a scene submission must:

1. render frames at a fixed list of **tick indices**, never at wall-clock times;
2. emit one telemetry record per captured tick;
3. produce byte-identical frames for a given `seed` across runs.

Determinism is not a nicety here. It is what lets every criterion below be computed by a script
instead of by an opinion, and what makes the same-seed / different-seed pair a real control.

**The fixed list of tick indices already exists and is the same in all 4 starters.**
`just film SEED TICKS SCRIPT OUTDIR` captures at most **12** frames evenly spaced over `0..=TICKS`
with both ends included, at ticks `floor(i * TICKS / 11)` for `i` in `0..11` —
`crates/game/src/bin/film.rs`, `scripts/film.ts`, `tools/film.gd`, `Assets/Editor/Probe.cs`. So
the tick list is a pure function of the tick count, and each starter carries a
`rendering is reproducible across runs` test asserting the frames for a seed are unchanged from
one run to the next. **No starter change is needed for scenes** — which matters, because a starter
edit is a regime boundary.

## The prompts

`eval/suites/scene_prompts.py` renders the 2 scenes for all 4 stacks: 1 template per scene over
vocabulary dicts, the same structure the games use, and **a separate module** from
`wholegame_prompts.py` because the scenes need preamble text the games do not — no player, no
controls, no sound, a fixed-length run. Editing the scene preamble moves **8** rendered prompts
and no game; editing the game preamble moves **16** and no scene
(`tools/prompt_guard_control.py`, the 2 `diff-sees-*-preamble-edit` rows). Under 1 shared
preamble either would move 24, which is #41. `DECISIONS.md` holds the derivation.

How much of a prompt is the same in every stack:

| | lines shared across all 4 stacks | characters |
|---|---|---|
| the 4 games | 97.3–98.4% | 90.4–95.0% |
| `s1_parallax` | 96.3% | 88.5% |
| `s2_glass` | 96.8% | 88.2% |
| all 24 rendered prompts | 97.3% | 90.9% |

    python3 eval/tools/prompt_guard.py --identity

**Quote the unit.** In the aggregate the line share and the character share differ by about 6
percentage points, because a substituted line is a long one — a whole vocabulary paragraph on 1
line — so a share counted in lines runs well above the same prompt counted in characters.

### The prompt is not the rubric, and that is checked mechanically

Nothing on this page may appear in a prompt. Not the criteria, not the naive implementations they
catch, not a threshold, not a tolerance. Writing *"make sure the water stays level"* because a
criterion checks it converts the measurement into an instruction and there is nothing left to
measure. The two sharpest omissions are deliberate and look like oversights:

- **s1 does not say the layers scroll at rates ordered by depth.** It asks for a background with
  real distance in it and lets the trace contract carry `layers[].depth`.
- **s2 does not say the water surface stays level while the glass tilts.** That is the criterion
  the scene exists for.

`python3 eval/tools/prompt_guard.py` greps the **rendered** scene prompts — not the templates,
because a leak can arrive through a vocabulary dict and leave the body looking clean — against 2
closed lists in `tools/prompt_guard.py`: the measurement vocabulary this file uses to state a
criterion, and English bound expressions, which is what a threshold is. Every term on the first
list must appear in this file, so the list cannot drift into words this file never used.
`tools/prompt_guard_control.py` pins both directions, and `DECISIONS.md` records why the lists are
curated rather than derived from this file's criterion columns, with the false-positive counts
that decided it.

**The same 2 lists govern the scene statement the tier-3 judge is handed** — `SCENE.md`, below.
A prompt that names a criterion teaches to the test; a judge's brief that names one turns a
tier-3 opinion into a restatement of tier 2. `judge/blurb_selftest.py` runs that grep.

## Launching one

    python3 eval/wholegame.py plan  --scenes s1_parallax --stacks ts --trials 1
    python3 eval/wholegame.py build --scenes s1_parallax --stacks ts --trials 1 \
        --run-dir eval/runs/<name>
    python3 eval/wholegame.py evaluate --run-dir eval/runs/<name>

**`--scenes` defaults to NONE and `--games` still defaults to every game, so the standing matrix
command launches no scene.** That asymmetry is deliberate and `DECISIONS.md` holds the reason: a
default is a value somebody can widen without noticing, and a scene trial is not a cheap addition
to a game run. `wholegame.select_tasks()` is where both defaults are written.

Every record carries `task_class`, and `wholegame.py report` computes each aggregate per class —
a per-stack mean over both describes neither. Tier 2 for a scene is `scene_probe.py` and the
record says so in `tier2_instrument` and in the tier's own `tier` field; the SLOT keeps the name
`playbot`, because that is what `WEIGHTS`, the completeness gate and every stored grading spell.

2 tier-1 inputs are class-dependent, and the runner hands both to `static.collect`:

| input | for a scene | what goes wrong otherwise |
|---|---|---|
| `film_ticks` | the scene's own contracted tick count, not the game default | the capture runs past the end of the sequence, and those frames are what `fidelity` and `motion` read |
| `audio_game` | `None` | the 5 tier-1 audio criteria are asked of a scene whose prompt tells it to spend no effort on sound, so the grader deducts for compliance |

**No tier-1 BOUND differs by class.** `static.TIER1_BOUND_POPULATION` answers that for all 14
criteria — a registry rather than a paragraph, so a criterion added without an answer fails, and
`judge/ink_window_control.py` prints the tally. `render.nonempty` is a floor with no ceiling in
both classes; `judge/RUBRIC.md` holds the rule and its derivation.

The runner hands the class itself over as a third argument, and the 2 ways it can be wrong are
caught in 2 different places: `static.assert_task_class` refuses an **unregistered** class before
a toolchain is spent, and `eval/tools/scene_runner_control.py` catches a **registered but wrong**
one — a scene routed as a game — by spying on what the runner passes down.

## Grading: what replaces the play-bot

| tier | games | scenes |
|---|---|---|
| 1 | builds, lints — a **gate** | unchanged |
| 2 | play-bot drives the game | **scene probe** — `judge/scene_probe.py`: criteria computed from frames + telemetry. Carries the weight |
| 3 | LLM judge | LLM judge, different aspects (below) |

The play-bot tier carries the whole weight for games because it is the only tier that is both
objective and discriminating. The scene probe is built to the same standard, so it inherits the
weight. Each criterion is binary and equally weighted, and **every criterion needs a mutant** (can
it fail?) **and a variant** (can it still pass on an input it mishandles?) — a mutant alone has
never been sufficient here.

**Where possible a criterion is measured twice, once from telemetry and once from the image.**
Telemetry is what the submission says it did; the image is what it did. A criterion that reads
only telemetry is gradeable by a submission that lies, and the cheapest lie is the one an agent
writes without meaning to.

### What the probe is, and what it is not yet

`judge/scene_probe.py` implements every criterion below; `judge/scene_mutants.py` pins each one
against a mutant that removes the behaviour it names and against correct scenes the reference
does not resemble, and both run in `controls.yml`. The two reference scenes are
`judge/fixtures/ref_parallax` and `judge/fixtures/ref_glass`.

**1 submission has now met these criteria, and it is 1.** `eval/RUNS.md` holds it. Every
threshold was still chosen against fixtures written by the same hand as the criterion, so
`python3 judge/scene_mutants.py --census` — which reports over FIXTURES and says so — is still
what a scene result must be read against.

**First contact with a real submission found a false negative and 2 criteria it could not set
up at all.** What it found, on which trial, with the numbers, is in `eval/RUNS.md`.
`layers.depth_ordered` is repaired and re-graded (`tasks/162`, and the decision it forced is
below); so is the tier-1 ink ceiling, which no longer exists (`judge/RUBRIC.md`). The
standing limit is the sentence above: every threshold was chosen against fixtures, and a scene
result is read against `scene_mutants.py --census` until that stops being true.

**One instrument error is already measured**, so the first run does not have to rediscover it:
across the 3 parallax fixtures the image-side shift estimator misses **8 of 132 frame pairs** — 1
of 44 on the reference, 5 of 44 on the `numbered nearest-first` variant, 2 of 44 on the `1.5x
larger` one — and every one of the 8 is on the band holding a large object that is stationary on
screen. `scene_probe.py`'s docstring holds the detail and `DECISIONS.md` the comparison that
chose the estimator.

## `s1_parallax` — 2D, a car on a road

A side-on car driving a looping road, with a layered background, running for a fixed number of
ticks and passing through a lighting transition.

| criterion | id in `judge/scene_probe.py` | reads | the naive implementation it catches |
|---|---|---|---|
| the contracted state shape, with finite numbers | `state.shape` | telemetry | a scene that answers a different contract |
| layers scroll at **distinct rates ordered by declared depth** | `layers.depth_ordered` | telemetry | one flat background image scrolled as a unit |
| the same ordering is visible **in the image** — horizontal bands at different heights shift at different rates | `layers.image_parallax` | **image** | telemetry that reports parallax the renderer does not draw |
| the loop **wraps seamlessly** — the drawn shift at a wrap continues the scroll the layer keeps elsewhere | `loop.seamless` | both | a background that visibly jumps when it repeats |
| wheel angular velocity **matches ground speed** | `wheels.match_speed` | telemetry | wheels spun at a constant rate unrelated to motion |
| a foreground element **occludes** the car at a known tick | `front.occludes` | telemetry | everything drawn in one z-layer |
| the lighting transition ramps **monotonically** across its window | `light.monotonic` | both | an instant cut between two palettes |
| same seed identical **and** different seeds different | `seed.pair` | both | anything wall-clock or unseeded, and anything canned |

Two of these — the image-side parallax check and the wrap check — are what make the scene about
rendering rather than about arithmetic.

**`front.occludes` is telemetry-only and cannot be otherwise.** The contract gives the car's world
position and each foreground thing's world position, and no screen box for the car — so there is
no way to ask the pixels whether one covered the other. Adding `car.screen` to the trace contract
would make it measurable twice, and that is a prompt change, which is a regime boundary.

**Two of these are implemented differently from the shape first proposed here, and both
differences are what makes them measurable at 12 frames.**

- `loop.seamless` does **not** look for an outlier in a per-frame difference series. Consecutive
  captures are 60 ticks apart, so every consecutive pair already differs enormously and a seam is
  a few columns inside that — the outlier would be swamped. Instead it estimates each band's
  drawn displacement between frames, divides by the offset that band reports, and asks whether
  the crossing keeps the ratio the band holds everywhere else. A layer that snaps at its repeat
  breaks the ratio at exactly that pair and nowhere else.
- `seed.pair` compares the captured PNG **bytes**, not a frame hash. A hash a submission computes
  about its own frames is another field it can get wrong or quietly stop updating; the files on
  disk are not.

### `layers[].offset` may ACCUMULATE or WRAP, and both are contracted

The prompt says `offset` is *"how far that layer has been displaced sideways so far"* and `span` is
*"the width after which the layer repeats itself"*. It does not say whether the number keeps
growing or stays inside `[0, span)`, and **a submission may report either.**

**The prompt is not changed, and that is the decision rather than an omission from it.** A layer
declares its own `span`, so a wrapped series and a cumulative one carry the same information.
Naming an encoding would be a regime boundary against every scene trial, and it would deduct marks
for reporting `offset` the way a renderer wants it.

**No criterion in `ParallaxScene` may difference two reported `offset` values.** `_walk` rebuilds
each layer's series from the per-tick trace, mapping every step into `(-span/2, span/2]` before
adding it, and `layers.depth_ordered`, `layers.image_parallax` and `loop.seamless` read that
series. `_walk` is the only place that subtracts 2 reported offsets, and only ever consecutive
ones: that difference is a modular residue anywhere else. It is exact while a layer moves less
than half a span in 1 tick, and a no-op on a scene that already accumulates. Per tick, not per
captured frame: 2 captures are 60 ticks apart, which is long enough for a near layer to cross more
than half its span.

**A layer earns a walk by carrying a finite `offset` and a positive `span` on every trace line,
and `layers.depth_ordered` fails one that does not.** `state.shape` reads tick 0 only, so all 3
ways of falling short are silent and all 3 read as a smaller, plausible travel: a hole between 2
reported ticks, a layer that stops reporting and never resumes, and a row that declares no usable
`span` to unwrap against.

`scene_mutants.py` holds both directions: a variant reporting `offset` inside its own span, and 3
mutants that break a layer's reporting — a hole, a truncation, and a row with no span.
`eval/RUNS.md` holds what the first submission measured.

## `s2_glass` — 3D, a glass of water that falls, breaks and un-breaks

A transparent glass holds water. The water drains slowly. The glass tilts, then falls, hits the
ground and shatters into irregular pieces. After a pause the sequence runs backwards: pieces
reassemble, water returns, the glass rises.

| criterion | id in `judge/scene_probe.py` | reads | the naive implementation it catches |
|---|---|---|---|
| the contracted state shape, with finite numbers | `state.shape` | telemetry | a scene that answers a different contract |
| the **water surface stays world-horizontal while the glass tilts** | `water.level_under_tilt` | telemetry | water modelled as a child of the cup, so it tilts with it |
| water volume **decreases monotonically** and agrees with the drips (mass balance) | `water.volume_conserved` | telemetry | a water mesh that is merely scaled down |
| the region seen through the glass is a **distorted** version of a known backdrop, not a flat tint | `glass.refracts` | **image** | alpha transparency with no refraction |
| shatter yields **≥ 8 pieces**, all coming to rest on a common surface rather than sinking through it | `shatter.pieces_rest` | telemetry | a single mesh swapped for a "broken" texture; pieces that sink |
| **different seeds → different piece transforms; same seed → identical** | `seed.pair` | both | a canned pre-fractured mesh played back |
| reversal returns to the initial state within tolerance, in **both** telemetry and frame distance | `reversal.inverts` | both | a reversal that fades out instead of inverting |

**`shatter.pieces_rest` does not use `table.y` as the ground plane, and that is a decision rather
than an omission.** The contract calls `table.y` *"the height of the surface everything stands on"* and
the scene has two surfaces: the glass stands on a table and its fragments come to rest on
whatever is below it. A submission may reasonably report either. So the criterion asks the two
questions that need no plane at all — a settled fragment must not go on descending, and the
settled fragments must lie within a band rather than being scattered through the world — and uses
`table.y` only as the SCALE, `max |glass.y − table.y|` over the run, which is what makes every
tolerance here a share of the drop rather than a number in somebody's world units.

The tilt criterion is the one worth building the scene for: the water surface is the single place
where "looks about right" and "is actually simulated" separate, and the wrong implementation is
the one a hurried agent reaches for first.

The seed pair is deliberately two-sided. *Different seeds differ* alone is satisfied by anything
random, including a scene that ignores the seed and uses wall-clock noise; *same seed matches*
alone is satisfied by a canned animation. Only the pair distinguishes seeded procedural fracture.

## Ambition: specify the RESULT, never the technique

Scenes should push each stack as far as it goes — ray-traced or path-traced lighting, real
refraction and caustics through the glass, GPU particle systems in the thousands, post-processing.
But **the prompt must ask for the visible result, not the technique.**

Saying *"use ray tracing"* prescribes the implementation and destroys the most interesting
measurement: which facility the agent reached for. Saying *"the caustics cast by the glass onto
the table must move as the glass tilts"* asks for something that is hard to fake, leaves the
method open, and turns the method into a **finding** — that is what `framework_fluency` reads.

The same applies to the fragment count. Ask for *"the glass breaks into many small irregular
pieces, each moving independently"*; do not name a number. A number in the prompt is a threshold,
and thresholds are rubric.

## Performance is a SECOND pass, and it is not the correctness pass

The correctness criteria above require deterministic, headless, tick-indexed capture with no
wall-clock anywhere. Frame rate is the opposite measurement: real-time, wall-clock, GPU-bound.
**Running one pass cannot produce the other**, and a scene that captures deterministically is
expected to be slower than real time. Two passes, two records, never one number.

**Raw FPS is not comparable across submissions, because the workload is not fixed.** An agent that
renders 200 particles at 240 fps has not beaten one rendering 200,000 at 60. Reporting FPS alone
would rank the least ambitious submission first — a metric that rewards doing less is worse than
no metric.

The comparable form is a **ramp**: the scene exposes a complexity level, the harness raises it
until median frame time exceeds a fixed budget, and the score is the highest level sustained.
That asks *how much can this stack do before it runs out*, which is the question worth asking, and
it is one number per submission.

### What a performance pass needs before it means anything

**`eval/PERF-HOST.md` is the authority for everything in this section**: it measured what this
host does to a frame-time number, and it decides the design. The short form:

- **No tested host mechanism gives a usable GPU, RAM or CPU-rate cap.** Every capping candidate
  the report tried leaves GPU throughput untouched, `taskpolicy -m` accepts a memory limit and
  ignores it, and the address-space rlimits cannot be set at all. `RLIMIT_CPU` is the exception
  and it only kills on cumulative CPU seconds. A Linux VM has real cgroup caps and **no GPU
  device**, so it is a different experiment rather than a stricter one. The pass is an uncapped
  ramp with the machine recorded.
- **Space the trials, and require an exclusive machine.** Spaced 25 s apart, the same fixed
  workload holds to ~1% and costs about a tenth of a ramp level. Run back to back it swings
  **1.975x**, and the report's isolation measurement — 1 competing GPU process — costs **2.13x**.
  Either is 1.0 to 3.4 ramp levels of host contribution depending on the step size chosen,
  which is larger than any stack gap smaller than it — and no stack gap here is measured yet.
- **Hold the machine, per arm, and prove it.** A perf number is far more machine-sensitive than a
  correctness one. AGENTS.md rule 10 was bought by a system daemon that gated `execve` for ten
  days and split a run's results by whether the arm linked new binaries (#49). Capture machine
  state per trial rather than assuming it held.
- **Interleave the arms, record each trial's timestamp, and never pool trials across time
  windows.** This host's throughput moves under sustained load — by 1.975x over 10 minutes — so a
  run that does all of stack A then all of stack B measures the ORDER as much as the stacks. The
  movement is **not monotone** and its cause is not established, so a block design cannot be
  repaired afterwards by assuming the machine only ever got slower.
- **Read a harness-side wall clock, not each engine's own timer.** Bevy on Metal records CPU time
  only, and the ts capture path has no GPU at all, while godot and unity both expose a real
  GPU-side frame timer. Reading each engine's best clock would compare different quantities.
- **Report the ramp with its budget and resolution.** A level number without them is not a
  quantity anyone can compare later.

**What is still unmeasured is the run-to-run spread of a real submission**, because no scene has
been built. Every figure above is one fixed synthetic workload and is therefore a floor: it says
the machine is not what stops a ramp, and it cannot say the submission is not. Measure that on
the first scene that exists, before reporting any stack comparison.

## Tier 3 aspects for scenes

Games are judged on `architecture`, `idiomatic`, `fun`, `fun_frames`, `ux`, `audio`. Scenes have
no player, so `fun` has no referent, `fun_frames` controls a question nobody asks and `audio` has
nothing to hear. 3 aspects replace those 6, and they are defined in `judge/aspects.py`
alongside the game ones:

| aspect | sees | asks | across stacks? |
|---|---|---|---|
| `fidelity` | frames | does this read as the scene it was asked for? | yes |
| `motion` | frames | does what moves move as though it had mass, or slide at one unchanging rate? | yes |
| `framework_fluency` | code | did it reach for the engine's facilities, or hand-roll around them? | **no — per stack** |

**An aspect is asked only of its own task class, and that is a guard rather than a convention.**
`aspects.applicability()` refuses every cross pairing and refuses a task id it cannot classify,
at `judge/field.py pack`, at `field.run_field`, at `field_sweep.py` and at the 3 routes the
RUNNER reaches a grading instrument or a judge pack by — 6 paths, because the resource is *a
graded task* and a guard placed beside one caller is a guard the next caller does not have.

**It answers for the deterministic instruments too.** `aspects.INSTRUMENTS` declares the class of
`playbot`, `scene_probe` and the retired `legacy_judge`, so the same function guards them. What
stood in for a guard on the play-bot was `evaluate.BOTS[task]` raising `KeyError` — a refusal that
exists because a dict holds 4 keys, that arrives after tier 1 has run, and that a 5th key would
remove. `judge/aspects_selftest.py` pins both registries with a mutant and a variant, and
`tools/scene_runner_control.py` names each route and drives it.

**`framework_fluency` cannot be blinded and must never enter a blind comparison.** The whole
question is which engine's APIs appear in the source, so naming the stack *is* the measurement.
Report it per stack, never as a cross-stack ranking. This is the same wall the judge field hit:
`idiomatic` is structurally unblindable for the identical reason. Both now carry the bar in
`Aspect.cross_stack_bar`, which `judge/field_ranks.py` prints — with that aspect's per-stack
means, alphabetically by stack — beside every figure it produces for them, and which keeps
them out of every pooled figure, a pooled figure being a between-stack range (`tasks/146`).

**2 gates, and they answer different questions.** `judge/verify_blind.py` scans the *trial
tree* and is about the building agent; an aspect id is not a criterion id, so adding one moves
nothing there. What the *judge* is told is `judge/aspects_selftest.py`'s question, and it is
the one `fidelity` and `motion` have to pass: no stack name, no arm count, and the
frames-channel blind spot carried verbatim. Run both — `verify_blind.py` against a copy of the
starters laid out as a trial tree **outside** this repository, or it is red on its own path.

**Scene tier 3 is weight 0.00, and while there are 0 scene gradings the weight question reads
NOT ASKED rather than "no effect".** Two independent reasons: there is no scene population, and
`judge/weight_sensitivity.py` sweeps `w1` over `(tier 1, tier 2)` while this question is `w3`
over `(tier 2, tier 3)`. `judge/RUBRIC.md` holds the commands and the current counts;
`tasks/145` asks the question on real data. Do not propose a weight from an argument.

**`fidelity` is read against a statement of the scene, and that statement is in the pack.**
"Looks like the thing that was described" needs the description. It is `field.SCENE_STATEMENTS`,
written into every scene pack as `SCENE.md` by `judge/field.py build_pack` — one hand-written
statement per scene, the same text in all 8 submissions' packs, so it separates nothing. The
rendered prompt is not a candidate and never was: it exists per stack, and
`anonymise.find_stack_names` returns a stack token in every one of the 8.

**Two gates decide what may be in it, and they answer different questions.**
`judge/verify_blind.py --packs <pack>` asks whether it names a stack; `judge/blurb_selftest.py`
asks whether it names a criterion, using the 2 closed lists above. **The statement preserves both
deliberate omissions**, and the plain-English phrasings of them — *rates ordered by depth*, *stays
level* — are `RUBRIC_TERMS` entries, so the grep can see them in a statement as well as in a
prompt. It could not before 2026-08-25: planted into a rendered prompt, both read 0 hits on all 8.

## What scenes are for — the questions, stated so they can come out against us

- **Does a rich editor stack beat a code-first stack by MORE on scenes than on games?** The
  reason to build scenes at all. If the gap is the same size as on games, that is a finding about
  what engines actually buy, and it argues against keeping the class.
- **Do agents reach for the engine's facilities or hand-roll?** Answerable by static analysis of
  which APIs appear, independent of any judge.
- **Does the LLM judge earn weight here when it does not on games?** Tier 3 is at weight 0.00
  because it could not reorder anything. Scenes have an aesthetic component the probe cannot
  reach, so they are the honest test of whether that weight should ever be above zero.
- **Is scene ability separable from game ability, per stack?** If a stack's scene rank and game
  rank agree, one of the two task classes is redundant.

## Sequencing, and the rule it is protecting

Scenes and a second agent harness are two variables. Introducing both in one run makes every
result attributable to either, which is the failure this project has already paid for twice
(AGENTS.md rule 8). Establish the scene instrument under the existing harness first; add the
harness as a crossed arm afterwards, or cross it fully and analyse it as a factorial design —
but do not stumble into the middle case where each cell differs in two ways.
