# How judgement works

The deterministic tiers answer *does it work*. This layer answers *is it any good* — the only
question left once every submission works.

## Why this layer is being redesigned

The matrix produced an exact 24-way tie on the deterministic tiers: all four stacks, all three
games, all 1.000 once harness defects were adjudicated out. If the templates all produce
functionally perfect games, **every remaining difference is subjective by definition**, and this
layer is the only instrument that can see it.

The first version of it could not.

### What 24 submissions showed

| judge score | submissions |
|---|---|
| 13/13 | 15 |
| 12/13 | 7 |
| 11/13 | 2 |

Mean 0.965, range 0.846–1.000, instability 0.000 on 22 of 24.

**Only 2 of 13 criteria ever fired:**

| criterion | failed |
|---|---|
| `look.feedback` | 7 / 24 |
| `look.legible` | 4 / 24 |
| **the other eleven** | **0 / 24** |

That is the finding that drives everything below: **ten of the thirteen criteria ask about code
quality, and the code-quality dimension produced zero information across the entire matrix.** All
of the layer's discrimination came from two of the three visual criteria — a dimension it barely
covers.

The rubric spends 77% of its questions where there is no variance, and 15% where all the variance
is.

### That ordering is withdrawn — it was a screenshot artifact

Per-stack judge means were Godot 1.000, Rust 0.974, TypeScript 0.974, Unity 0.910. **All eleven
firings have been adjudicated against the frames and the source, and none of them is a property of
the games.** Full mechanism in `FINDINGS.md` §26.

`look.feedback` failed submissions for showing no HUD. It fired on exactly the two stacks whose HUD
*cannot* reach the capture: Unity draws it with `OnGUI`, which is never part of the `camera.Render()`
that `RenderHarness.CaptureFrame` reads back; TypeScript draws it into a `#hud` DOM node, which
cannot be in the pixels of the offscreen canvas `capture.ts` creates. The submissions with the most
HUD code are the ones it failed. All 7 firings are false negatives.

`look.legible` fails its own test: Rust fails with 13–14 distinct colours while TypeScript passes
with 9. Only Unity's two firings have measurable support.

The withdrawn ordering reproduces the exact shape the project-lock defect manufactured — Unity last,
every game. **Three stack-specific instrument defects have now been found in this project, and every
one of them was consistent enough to look like a result.** `instability` read 0.000 throughout.
Consistency is not correctness; only reading the mechanism separated artifact from effect.

This also makes `just film` a **template** defect: an agent that builds a correct scoreboard on Unity
or TypeScript and films it sees no scoreboard, and may delete working code to chase the ghost.

## The redesign

Two structural changes, neither of which is "add more criteria".

**One judge per aspect.** A single judge answering thirteen shallow questions is replaced by
specialists, each holding one lens and going deep.

**Each judge scores the whole field.** A judge shown one submission can only ask *is this good?* —
the question that saturated at 13/13 on 15 of 24. A judge shown all eight submissions for a game
must place them relative to one another, and cannot award everything full marks without that being
a visible, defensible claim.

The unit is **within-game**: 8 submissions = 4 stacks × 2 trials. That is the comparison the matrix
exists to make. Cross-game ranking is not meaningful and is not forced.

## The layer matrix

Existing layers are marked; the rest are candidates, ordered by expected value.

| Layer | Sees | Catches what nothing else does | Expected discrimination | Inert risk |
|---|---|---|---|---|
| **Code quality** *(exists)* | source | — | **None measured.** 0/24 firings | **Proven inert** on this task set |
| **Visual coherence** *(exists)* | frames | debug shapes, illegible scenes | All measured signal so far | Low |
| **Idiomatic stack use** | source + stack docs | Unity written like Rust; three.js written like a game engine it isn't | **Highest — the only aspect that is *about* the stack** | Low |
| **Gameplay & fun** | frames + telemetry | unplayable pacing, no challenge curve, trivially won | High | Low |
| **Game feel / juice** | frame sequence + input trace | input latency, no impact feedback, floaty controls | High | Medium |
| **Difficulty & tuning** | telemetry | unwinnable, unloseable, flat ramp | High | Low |
| **UX & onboarding** | frames | no start state, no restart, unclear controls | Medium–high | Low |
| **Polish & completeness** | frames + source | missing win/lose screens, no pause, stub menus | Medium | Low |
| **Audio** | audio output | **Total blind spot — nothing in the project touches sound** | Unknown | High (tasks never asked) |
| **Accessibility** | frames | colour-only state encoding, contrast, text size | Medium | Medium |
| **Performance & smoothness** | frame timing | stutter, allocation in hot loop, frame spikes | Medium | Low — partly deterministic |
| **Architecture & extensibility** | source | "could you add a second enemy type?" — beyond static separation | Medium | Medium |
| **Error handling & resilience** | source + runtime | focus loss, resize, bad input, save corruption | Low–medium | Medium |
| **Security** | source | input validation, unsafe deserialisation | **Likely inert** on single-player local games | **High until netcode exists** |

### The three worth building first

**Idiomatic stack use.** Every other aspect asks about the game. This one asks about *the stack* —
whether the agent used C# and Unity's component model as a Unity developer would, or wrote Rust in
C#. In a comparison of four stacks it is the only aspect whose whole subject is the variable under
test, and it is currently unmeasured. If any layer separates the stacks, it is most likely this one.

**Gameplay & fun.** The stated goal was a template that helps agents build *good games*. Nothing in
any tier currently asks whether the result is enjoyable. The play-bot telemetry already collected —
rally lengths, time-to-score, difficulty ramp, whether anything stalls — is evidence of tuning that
is presently used only to assert correctness.

**Audio.** A complete blind spot. No task requires sound, no tier examines it, no criterion mentions
it. That is a gap in the *task set* as much as the rubric, and worth naming before adding a judge
that would score every submission zero for a thing nobody asked for.

## What is built, and what it sees

Implemented in `aspects.py` (the questions), `field.py` (packing, running, gates) and
`field_sweep.py` (a whole matrix with a measured cost ceiling).

**Six aspects exist, and all six are runnable.** Five are opinions; `fun_frames` is `fun`'s
control and is listed last for that reason, not because it is optional. The count is
`len(ASPECTS)` and `docstat.py --sweep` fails on any live doc that claims to name them all
and does not — this table said five for as long as `ASPECTS` held six.

| aspect | sees | evidence in the pack |
|---|---|---|
| `idiomatic` | source | anonymised source + `CHANGED.txt` (what the author actually wrote) |
| `architecture` | source | same |
| `fun` | frames + telemetry | the 12 filmed frames, and `telemetry.json` measured from the play-bot's own driven run |
| `ux` | frames | the 12 filmed frames |
| `audio` | audio | `audio.json`: per-clip duration, RMS, peak, and which clips are the same sound as which |
| `fun_frames` | frames | the same 12 frames, **with `telemetry.json` withheld** — `fun`'s control, briefed byte-identically to it. See the pre-registration below |

It says it is a control **in code**, as `control_for="fun"`, and `field_ranks.assert_poolable`
raises rather than pooling it with the five opinions. Read it against `fun`, never added to it.
Until 2026-08-23 that was a comment naming a field nothing set and nothing read (task 90).

**The frames are not equivalent across arms, and every aspect that reads them is told so.**
Measured 2026-08-23 (task 68, FINDINGS #107): one arm's `just film` runs the whole app per tick so
its renderer observes the entire run, while the other **three** advance the simulation to the
sampled tick with no renderer attached and draw once. A probe painting one cell per observed tick
read `1, 1, 1` at ticks 8/60/240 in three arms and `9, 32, 32` in the fourth, with a positive
control reaching 32 in all four. So presentation state that accumulates across ticks — a trail, a
burst, a shake, a decay — is structurally absent from three arms' PNGs, and its absence is
indistinguishable from a submission that never wrote one.

`aspects.py` defines `FRAMES_BLIND_SPOT` and every frames-reading aspect carries it. It states the
blind spot **without naming or counting the arms**: a brief saying "three of the four" would leak
the partition to a judge that is supposed to be blind (#32), which is why
`aspects_selftest.py` carries a variant that counts without naming. This is the second measured way
the frames channel reports the arm rather than the work — see #59, palette depth, a 60× split by
renderer. Full record and the decision not to equalise the harnesses: `eval/RUNS.md`.

Four properties of the packing are load-bearing:

**The identity mapping is written BESIDE the pack, never inside it.** The judge's working
directory *is* the pack, and it is told it does not know which stack is which — so a
`MAPPING.json` in that directory hands it the answer key. It was there, and was found by
listing the pack rather than reading the code that builds it (FINDINGS #32). `build_pack`
now raises if any `MAPPING` file remains inside, and `run_field` refuses to judge such a
pack rather than producing a ranking. **No validation gate here can detect a judge that
knew the answer** — order-invariance, independence and adjudication would all pass — so
this is checked structurally, before the call, and never inferred from the output.

**A pack is built for one aspect and `run_field` refuses a mismatch.** Judging `fun`
over a code-only pack would produce eight confident scores derived from nothing that was
asked about — the same shape as the empty file pack that was scored 0.08.

**An aspect that needs evidence a submission does not have raises rather than judging.**
No aspect may quietly score a blank field.

**Paths are stripped from the audio evidence.** `assets/audio/hit.wav` versus
`Assets/Audio/hit.wav` identifies the stack, and the judge is told not to guess.

The telemetry the `fun` judge reads is the *same drive* the play-bot scored — one
session, two readers — so the tiers cannot disagree about what happened in the run.

## Sequential sampling — how many times a judge runs

A single judging is one sample from a stochastic instrument. Judges therefore run **repeatedly,
with presentation order reshuffled each round, until the DECISION resolves** — not for a fixed
count.

The unit of resolution is the **pair**, not the score:

1. For every pair of submissions, track how often A is ranked above B across rounds.
2. Put a **Wilson interval** on that win rate.
3. A pair **resolves** when the interval excludes 0.5 (a real ordering), and stops sampling.
4. Ambiguous pairs keep sampling; resolved ones stop. Budget goes where the uncertainty is.
5. **Report the N each decision required.** A ranking that needs 20 rounds to stabilise is weak
   evidence even when it converges — the N is as informative as the ordering.

This replaces `instability` as the reliability metric. Forward-vs-reverse disagreement within a
single run measured presentation-order sensitivity only, and read 0.000 on 22 of 24 submissions —
consistent and uninformative. Run-to-run pair agreement measures the thing that matters and its
interval is directly interpretable.

### It had no code path until 2026-08-16, and that is its own finding

`sequential.py` implements all of the above and passes a six-case self-test. **Nothing
imported it.** `field_sweep.py` took `--orders N`, ran a fixed number of presentation orders,
and reported `order_invariance` — which measures whether a ranking moves when the pack is
reshuffled, and cannot say whether a pair is `ORDERED`, `TIED` or `UNRESOLVED`. Those three
verdicts are what the whole design turns on.

So the protocol was specified here, implemented next door, self-tested, and approximated by
whoever read this document and reached for the runner. **A protocol with no code path is a
protocol that gets re-derived, differently, by every reader** — the failure this project
records about instructions in messages, in a second form.

`field_sweep.py --sequential` now drives `Sampler`. One correctness point is worth stating
because getting it wrong would produce a confident number from nothing: **the sampler is
keyed by SUBMISSION id, never by pack label.** `A`..`H` are reshuffled every round by design,
so a sampler keyed on labels accumulates win rates between *positions* and converges on
noise.

Validated with the model call stubbed, so it cost nothing and both arms were exercised:

| stub | rounds | verdict |
|---|---|---|
| a real ordering by stack | 4 | `RESOLVED: 24 of 28 pairs ordered` (the 4 same-stack pairs correctly `TIED_EXACT`) |
| a saturated judge, identical scores every round | 4 | `CONVERGED TIE: all 28 pairs indistinguishable` |

Two arms, because a control that only exercises the happy path shares the assumption it
exists to test.

**Cost, at the measured $5.29 per call:** a (game, aspect) that resolves in 4 rounds costs
~$21; one that runs to `MAX_RUNS = 24` costs ~$127. Five aspects on one game is therefore
somewhere between **$105 and $635**, and which end depends on the answer — which is the
point of sampling until the decision resolves rather than a fixed number of times.

### Cost is per (GAME, ASPECT), and it spans an order of magnitude

**Measured, 2026-08-16.** Two separate corrections, the second larger than the first:

| game | aspect | sees | pack | per call |
|---|---|---|---|---|
| `g1_pong` | architecture, idiomatic | code | 1.2 MB | $2.82-$5.29 |
| `g2_tetris3d` | architecture | code | 1.3 MB | **$8.08**, $5.53 |
| `g2_tetris3d` | **audio** | audio | **10 KB** | **$0.60**, $0.61 |

An `audio` call is **~11x cheaper** than an `architecture` call on the same game, because the
pack it reads is a few hundred numbers rather than a hundred source files. Projecting a sweep
from a per-game mean is therefore still wrong — it averages a $0.60 aspect with an $8 one.

> **Price per (game, aspect), from the pack size.** The cost of a field call is dominated by
> what the judge has to read, and `evidence_counts` from `build_pack` tells you that before
> any money is spent.

The first correction was cross-game and is kept because the reasoning still holds: three
`g1_pong` calls (mean $4.39) projected a five-aspect `--max-runs 6` sweep at ~$131; the first
tetris call measured $8.08 and repriced it at ~$256, over its authorised ceiling.

A `--max-runs 6` sweep over five aspects was priced at ~$131 from the pong mean. At the
measured tetris rate it is **~$256** — over the ceiling it was authorised under. `AGENTS.md`
already forbade extrapolating a cost projection across games; it was written in the
vocabulary of *agent trials* and did not fire for a *judge call*.

> **Price a sweep from a call on the game you are about to sweep, and treat one call as a
> lower bound rather than an estimate** (#42: one trial cannot calibrate a process whose
> spread is this wide).

**Depth-first is the wrong shape under a fixed ceiling.** Aspects run in alphabetical order,
so a budget that stops part-way starves whichever aspects sort last — here `idiomatic` and
`ux`, which are the aspect whose subject *is* the variable under test and one of the two that
read the played result. Losing them would have been an accident of the alphabet. **Go breadth
first: every aspect at shallow depth, then deepen the ones that look like they carry
something.** Rounds are stored per seed and re-read for free, so depth added later costs only
the new rounds.

### What a full sequential sweep costs — priced 2026-08-16, NOT RUN

From the measured per-call figures, and the **12** (game, aspect) combinations that build a
non-empty pack. The range spans the pong and tetris rates:

| assumption | calls | cost |
|---|---|---|
| floor — every aspect resolves in 4 rounds | 48 | **$211-$388** |
| median — half resolve at 4, half run to the cap | 168 | **$738-$1,357** |
| cap — `MAX_RUNS = 24` everywhere | 288 | **$1,264-$2,327** |

**Even the floor is $210**, and the floor assumes every aspect resolves as fast as the
fastest case in the self-test. The regime this field is actually in — clustered but not
saturated, modal fraction 0.625 — is the expensive one: `TIED_EXACT` stops at 4 rounds only
when the judge gives *identical* scores, and these judges do not.

> **The instrument is cheapest exactly where it is least informative.** A saturated judge
> resolves in four rounds and tells you nothing; a genuinely close field runs to the cap and
> still reports `UNRESOLVED`. Price the close case, because that is the one this project
> keeps landing in.

Under a $150 ceiling the affordable experiment is **one game, five aspects, `--max-runs` cut
to about 6** — roughly 30 calls, ~$131 — which reaches gates 1 to 4 on that game and reports
`UNRESOLVED` for pairs that need more. `UNRESOLVED` is not a tie and must not be written as
one.

### The verdicts, and why three are needed

| verdict | meaning |
|---|---|
| `ORDERED` | interval excludes 0.5 — a real ordering at this confidence |
| `TIED_EXACT` | the judge assigned identical scores every round. More sampling cannot change this. Stops at n=4 |
| `UNRESOLVED` | sampling ended without resolution. **This is not a tie — it is a failure to decide, and the two must never be reported as the same thing** |

### What this instrument cannot do

**At affordable N it can detect an ordering but cannot statistically prove a tie.** A Wilson 95%
half-width at p=0.5 is 0.186 at n=24 and 0.098 at n=96 — so a ±0.10 statistical tie needs about
**96 rounds per aspect, roughly $1,150**.

The honest claims available at n=24 are therefore *"no ordering was found, ±0.19"* or *"the judge
never separated this pair at all"*. `n_for_statistical_tie` is reported so the cost of the stronger
claim is visible before anyone commits to it.

This matters because a tie is the **expected** outcome: three games have already tied on the
deterministic tiers. The branch this project is most likely to land on is the one the instrument
proves least well, and that limitation must be stated wherever a tie is reported.

Two failure modes were found by testing the sampler before running it, and both would have cost
real money:

- **The tie branch was unreachable** at any affordable N — dead code that would have manifested as
  a run reporting "unresolved" forever while burning budget.
- **A saturated judge was indistinguishable from a hard question.** Identical scores every round
  give every pair exactly 0.5 and an interval of [0.31, 0.69] → `UNRESOLVED`. An instrument
  measuring nothing looked exactly like a genuinely close field — the same collapse as the
  independence gate, one layer up. `TIED_EXACT` exists to separate them.

## Before any gate: prove the pack is not empty

**Measured 2026-08-16, before the first specialist judge was ever run on real submissions.**
12 of the 15 (game, aspect) combinations build a non-empty pack. The three that do not are
`g3_arena` x `fun`, `ux` and `audio`: two of that game's eight submissions do not compile, so
they render no frames and ship no sound, and `build_pack` refuses rather than judging a field
of six. That is the fail-closed refusal working.

Finding it required repairing the guard itself. **The empty-pack check counted the evidence
FILE, not its contents** — a submission whose measured audio was `{"clips": {}}` wrote an
`audio.json` and passed a check whose entire purpose is to stop a judge scoring a blank field.
`_audio_evidence` now returns `None` when there are no clips, and `_submissions` filters on
that, so the aspect reports "found 6" the way the frame aspects already did.

> **A guard that counts artifacts rather than reading them is the empty-pack failure wearing
> the empty-pack guard's clothes.** List what the judge will actually read, per submission,
> and require it to be non-trivial — not present.

Run this check before spending anything. It costs nothing and it is the only thing standing
between a blank field and eight confident scores.

## Validation gates

In order. Do not skip to results.

### Gate 0. Reproducibility — run this before believing any of the others

Judge the same field in the SAME presentation order twice and compare.
`field.reproducibility()`.

It was added on 2026-08-17 after an accidental control showed the layer does not agree
with itself. `audio` reads only `audio.json`, which neither the telemetry repair nor
`blind_language` touched, so two sweeps judged a byte-identical pack with a
verified-identical label->submission mapping:

| aspect | seed | scores changed | modal fraction | ceiling verdict |
|---|---|---|---|---|
| `audio` (evidence UNCHANGED) | 0 | 2 / 8 | 0.625 -> 0.625 | stable |
| `audio` (evidence UNCHANGED) | 1 | **4 / 8** | **0.750 -> 0.375** | **CEILING -> separates** |
| `architecture` | 0 | 3 / 8 | 0.625 -> 0.500 | stable |
| `architecture` | 1 | 3 / 8 | **0.875 -> 0.500** | **CEILING -> separates** |

`audio`'s order-invariance tau moved **0.75 -> 0.333** on nothing at all — a pass turning
into a failure against the pre-registered floor.

> **A single-run gate verdict is a sample, not a measurement.** Two of four comparisons
> flipped their ceiling verdict with the evidence held constant, so every gate result in
> this document that rests on one run per (aspect, seed) rests on n=1.

**Open, and it matters for what to spend next on:** both flips are on seed 1 and both go
the same way. That is consistent with per-call noise and equally consistent with a drift
between the two sweeps, and four comparisons cannot separate them. Measuring it properly
means repeats at a fixed seed — cheap for `audio` ($0.60/call), `ux` and `fun`, expensive
for the two code aspects ($6.50-$8.00).

### Gate 1. Ceiling test

No judge may give effectively the same score to everything. Run over the stored submissions
first — free, no rebuilds. A judge that cannot separate the field has wrong criteria, and no
amount of running it will fix that.

**The gate watches the mode, not the maximum.** The falsifier was originally written as ">70%
sit at the top score", which misses the symmetric failure: a judge putting seven of eight at the
*bottom* has separated the field exactly as poorly while reporting a reassuring
`at_max_fraction` of 0.125. A ceiling at the floor is still a ceiling — the same error as
validating a judge on a fixture that scored 0/13 and calling the agreement evidence. `ceiling()`
now reports `modal_fraction` and fails above 0.7 at **any** score. Tightened 2026-08-14, before
any specialist judge had been run, so no data influenced it.

### Gate 2. Independence

Correlate specialists against each other. **Hold the presentation order fixed across aspects
when you do** — correlate seed *k* of one aspect against seed *k* of another. `independence()`
keys by (game, aspect) and takes the LAST result for each, so passing several orders per aspect
silently correlates one aspect's seed 1 against another's seed 0 and mixes aspect disagreement
with presentation noise, inside the one gate whose job is to tell those apart. Measured on the
first real sweep: `_basis_order_seed` was `{"architecture": 1, "idiomatic": 0}`. It now reports
`_basis_order_seed` and `_orders_collapsed` so the basis is visible in the output rather than
inferred from the call site. **If `fun`, `ux` and `idiomatic` produce the same ranking, there
are not five judges — there is one judge with five names.** This is the gate most likely to
fail, and measuring it is the point of splitting the aspects at all. `field.independence()`
reports Kendall tau **per pair of aspects**, and flags every pair at tau >= 0.8 by name. It
also reports how many pairs were actually **comparable**: these judges score 0–4 over 8
submissions, so ties are common, and a tau computed over three comparable pairs must not be
read like one computed over twenty-eight. Below six comparable pairs the tau is labelled
arithmetic rather than evidence, and an aspect that gave the whole field one score makes every
correlation against it undefined — which is reported as a **ceiling failure to fix first**,
never as "these aspects are independent". Reading a judge that measured nothing as good news is
how three artifacts in this project were mistaken for results. It deliberately does not
aggregate: a set holding one redundant pair and one opposed pair has a low average and is still
not independent, and hiding that inside a mean is the same mistake as averaging a criterion
that is sound on three stacks and broken on the fourth.

### Gate 3. Order-invariance

Reshuffle presentation order and re-run. A ranking that moves is a presentation artifact. This
replaces the old `instability` metric, which only measured within-artifact order sensitivity
and read 0.000 on 22 of 24 — consistent and uninformative.

**The metric itself was repaired on 2026-08-16, before its first real reading was
reported.** `order_invariance()` converted scores to ranks by sorting, which hands every
*tied* submission an arbitrary distinct rank and then correlates those invented orderings.
On the first real field 21 of 28 pairs were tied, so most of what it was measuring did not
exist. `independence()` had already been fixed for exactly this and carries a comment
explaining why; nobody asked whether the same defect lived in its sibling. It now shares
`_tau` and reports `comparable_pairs`.

Pinned in both directions: a field compared with **itself** returns `kendall_tau: 1.0`, so
the metric is not merely returning small numbers.

### Gate 4. Adjudication

Spot-check firings against the underlying evidence, the way play-bot failures were adjudicated.

**On an anonymised pack, a path check measures PATH RECONSTRUCTION, not claim validity.**
Measured 2026-08-16 on the first real `architecture` field: 11 of 16 claims cite a path that
exists nowhere in the pack. Spot-checked in depth, one of them reads *"a direct `match kind
{ PieceKind::I => ... }` over the enum in `game/src/lib.rs:75-85` with no wildcard arm"* —
and the pack contains exactly that construct at **`view/03.rs:76-77`**. Right substance,
near-right line range, **invented filename**: the judge reconstructed a plausible original
Rust path for the anonymised one it actually read.

A second population was being miscounted outright. `anonymise.py` renames files but leaves
the filenames the *authors* wrote inside them, so `sim/04.gd` contains the string
`sim/sim.gd` in a doc comment and a judge citing it is quoting something it really read.
The first run of this gate reported **15 of 16 claims citing a missing path**; splitting the
two populations gives **9 traceable to pack text** and **11 found nowhere**. The single
number overstated the flag by about half, and it is the exact population the old rubric's
entire measured signal turned out to live in — so an inflated count here is a number
someone acts on.

`adjudicate.py` now reports the two separately. **Read the flag as "the citation cannot be
followed", never as "the claim is false"** — 15 of 23 quoted code tokens (65%) do locate
verbatim in the pack.

**Over the full five-aspect field the flag needed four separate repairs**, each of which had
been inflating it: resolving every aspect against the code pack (so `ux` citing
`frame_0000.png` was flagged), `PATH_RE` matching `js` inside `json`, and pack artifacts
(`telemetry.json`, `audio.json`) living in a temp directory that is deleted before anyone
adjudicates. Headline across the fixes: **54 -> 31 -> 15 of 80**. What survives is clean:

| aspect | reads | cites a name found nowhere |
|---|---|---|
| `architecture` | code | **11 of 16** |
| `idiomatic` | code | 4 of 16 (all naming `three.js`, a library) |
| `audio`, `fun`, `ux` | audio / frames | **0 of 16 each** |

Only the two aspects that read **anonymised filenames** invent citations. A judge shown
`frame_0000.png` cites it correctly; one shown `sim/04.gd` cites `sim/sim.gd`, because that
is what the file calls itself inside. Consistency is not correctness: the project-lock defect was perfectly
consistent for three games. `adjudicate.py` does the mechanical half — it resolves every path a
judge cited back to the real submission and flags two kinds of claim that could never have been
checked by anyone: evidence naming a file the submission does not contain, and evidence with no
path and no number in it at all. Note that `anonymise.py` renames files to `sim/01.gd`,
`view/02.ts` and so on, so a judge cites **pack** paths; the adjudicator resolves against the
pack, which is what the judge actually read. Neither flag proves a claim wrong. They remove the
claims nobody could have verified — the population the old rubric's entire measured signal
turned out to belong to.

### Gate 5. Blinding

Unchanged. `verify_blind.py`, unpiped, after any starter or fixture change.

## First run on real submissions — 2026-08-16

**Three calls, $13.15, then halted** so the deterministic result could be read without the
subjective layer alongside it. **Measured cost: $2.82-$5.29 per field call (mean $4.38),
450-572 s wall.** That is the number to plan with; every earlier figure here was an estimate.
At the mean, 3 games x 5 aspects x 2 orders is about **$130**, and the ~96 rounds per aspect a
statistical tie would need is about **$420 per aspect**, not the $1,150 previously quoted.

**Gate 1, ceiling — PASSES, narrowly, on both aspects measured.**

| call | scores | modal fraction | verdict |
|---|---|---|---|
| `idiomatic` seed 0 | `[3, 3, 4, 4, 3, 4, 3, 3]` | 0.625 | separates the field |
| `architecture` seed 0 | `[2, 2, 2, 3, 2, 3, 2, 3]` | 0.625 | separates the field |
| `architecture` seed 1 | `[3, 3, 3, 3, 3, 2, 2, 2]` | 0.625 | separates the field |

The threshold is 0.7 and every reading is 0.625, which is one submission's worth of margin.
The judge's own field note says the same thing in words: *"this field clusters unusually
high... none reads as written by someone unfamiliar with their stack, and I could not find a
genuine 'competent but unremarkable hobby project' anywhere either."*

**Gate 3, order-invariance — FAILS on `architecture`, the only aspect with two orders.**

| | |
|---|---|
| Kendall tau between the two orders | **0.143** |
| comparable pairs | 7 of 28 (21 tied) |
| submissions whose score changed | **4 of 8** |
| mean absolute score shift | 0.5 |

Iteration 6 in `../IMPROVEMENTS.md` pre-registered the falsifier as *"Kendall tau between the
two orderings is < 0.5"*. It is 0.143. **A ranking that moves this much when the pack is
reshuffled is a presentation artifact**, and no amount of further sampling makes it one.

Two things stop that being over-read:

- the tau is computed on **7 comparable pairs**, which is barely above the six below which
  this file says a tau is arithmetic rather than evidence. The score-shift row does not
  depend on the tau at all: half the field moved.
- gate 2, **independence, was never reached** — it needs two aspects with a usable ranking on
  the same game, and only one aspect has one. The gates are ordered for a reason and the
  order held.

**What this does not license.** `idiomatic` has one order and therefore no order-invariance
reading at all. Its ceiling pass says only that it can produce different numbers, not that the
numbers mean anything.

## RESULT — the five specialist judges, `g2_tetris3d`, 2026-08-16

10 field calls, **$33.63**, 8 submissions the deterministic tiers score identically (all
1.000, and with no resolution below the cell to separate them — #50). Two presentation
orders per aspect, sequential sampling capped at `--max-runs 2`. Summed from the ten stored rounds in
`runs/wg-tetris-judge-2026-08-17/pre/` by `judge/judge_ledger.py`. This read *13 calls,
$46.79* until 2026-08-23: that figure is the whole day, and three of its calls, $13.16, are
`g1_pong` — a different game and a different field (FINDINGS #121).

### Gates, in order

| aspect | 1. ceiling | 3. order-invariance | 4. adjudication |
|---|---|---|---|
| `architecture` | **FAIL** — seed 1 puts 7 of 8 at one score (modal 0.875) | no usable tau (3 comparable pairs); **4 of 8** moved | — |
| `audio` | **FAIL** — seed 1 puts 6 of 8 at one score (modal 0.750) | tau 0.75 on 8 pairs — pass | — |
| `fun` | pass, both orders (modal 0.375, 0.500) | tau 1.00 on **19** pairs — pass | **FAIL — withdrawn (#52)** |
| `idiomatic` | **FAIL** — seed 1 puts 6 of 8 at one score (modal 0.750) | tau 1.00 on 10 pairs — pass | **FAIL — withdrawn (#53)** |
| `ux` | pass, both orders (modal 0.375, 0.375) | tau 0.778 on 18 pairs — pass | see below |

**Three of five ceiling on one presentation order and separate on the other.** The judge
saturates on the same field the deterministic tiers cannot separate — and does so unstably, so
a single run lands on either answer.

**Gate 2, independence** — the gate this spend existed to reach, computed per seed so the
presentation basis is held fixed. One pair replicates on both orders:

> `architecture ~ ux`: **tau 1.00** on both. One reads only source, the other only frames.
> They share no input at all (#54 — **withdrawn on the repeat**, register
> `WR-arch-ux-redundancy`; see "RESULT after the repairs" below).

`audio~idiomatic` and `fun~idiomatic` each hit 1.00 on a single order and are noise. Every
other pair sits between −0.14 and 0.71.

### Does any aspect separate the four stacks?

**No — and the reason is not the one this section used to give.**

Everything below is reproduced by the producer, not computed by hand:

```
python3 judge/field_ranks.py --rounds runs/wg-tetris-judge-2026-08-17/pre [--per-aspect]
```

10 usable rounds, 5 aspects x 2 presentation orders, 8 submissions, ranked 0 (best) to 7.
**All five are scored opinions — this field holds no `fun_frames` rounds**, which the tool now
states in its own output. On a directory that does hold them the pooled figure covers the scored
aspects only, so the population is a third parameter (`DECISIONS.md`, task 90).

**The quantity has two free parameters and they change the answer.** `value` is what a round
asserts about a submission — its `score`, or its `rank` in the field. `order` is whether the
rounds are averaged before the spread is taken (`pool`) or after (`perround`). All four, on
this field:

| value | order | between-stack range | mean within-stack gap | direction |
|---|---|---|---|---|
| `score` | `pool` | 0.350 | 0.725 | between **<** within |
| `score` | `perround` | 0.950 | 0.775 | between **>** within |
| **`rank`** | **`pool`** | **1.900** | **2.275** | between **<** within |
| `rank` | `perround` | 3.300 | 2.825 | between **>** within |

**`rank` + `pool`, in bold, is the pair this project quotes** when it quotes one — decided in
`DECISIONS.md`, "The tier-3 separation figure is reported under `rank` + `pool`". The
post-repair field gives **2.100 against 1.925** the same way.

> **The comparison changes direction on a free parameter, so no argument may rest on its
> direction.** A previous version of this section read a two-row table, 1.70 and 2.05, with no
> field and no method; it matches none of the four and was **withdrawn** — FINDINGS #113,
> register entry `WR-tier3-pair`. Do not restore an argument of the form *between is smaller
> than within*: on this field that inequality is decided by a choice nobody had made
> deliberately.

What survives the parameter is the magnitude. **On none of the four readings does the
between-stack range exceed the within-stack gap by more than 23%**, and on two of the four it
is smaller — against a field the deterministic tiers score identically. A stack effect would
have to dwarf the within-stack gap. Nothing here does, under any method.

Per aspect, **`value=score` `order=perround`** — the one method that reproduces this table, and
the reason the method could be identified at all (#113):

| aspect | range | within | reads as |
|---|---|---|---|
| `architecture` | 0.50 | 0.50 | no separation |
| `audio` | 0.75 | 0.62 | marginal |
| `fun` | 1.25 | **1.50** | no separation |
| `idiomatic` | 0.75 | 0.38 | nominally separates — but see #53 |
| `ux` | 1.50 | 0.88 | nominally separates — but is redundant with a judge that never saw a frame |

The unrounded column means are **0.950** and **0.775** — exactly the `score`/`perround` row
above, because `perround` averages the same per-aspect-per-order statistics. **`pool` does not
decompose that way**, so the bolded `rank`/`pool` pair is *not* the average of any per-aspect
table and must never be presented as one. That mismatch — a pooled line sitting three lines
under a table it does not summarise — is how the withdrawn pair survived unchecked.

And the ordering is not stable to which aspects are included:

| aspects pooled | ordering |
|---|---|
| all five | rust, godot, ts, unity |
| minus `idiomatic` | rust, godot, unity = ts |
| minus `idiomatic` and `fun` | godot, rust, unity, ts |
| `ux` alone | rust, godot, unity, ts |

The top two swap and `ts` moves from third to last depending on which aspects are counted.
**There is no ordering here to report.**

### What was checked and did NOT hold

`ux` ranks `ts` lowest on both orders, which is the exact shape of #26 — where `look.feedback`
failed the submissions whose HUD could not reach the capture. Adjudicated against the
evidence: the `ux` judge quotes on-screen text from the ts frames (*"SCORE 000000, LEVEL 01,
LAYERS 000"*, control legends), so the HUD **is** in the pixels and the #27 repair held. That
mechanism is not operating here.

A different one may be. Three of 16 `ux` claims turn on whether the HUD numbers **changed
across the 12 filmed frames** — and those frames are sampled from the same 6-to-9-second bot
run that made `fun` unusable (#52), in which only 2-3 pieces lock. Whether the score visibly
moves is close to a coin flip on the harness, not a property of the game.

## RESULT after the repairs — 2026-08-17, 10 more calls, $31.66

Re-run on repaired evidence, both orders, all five aspects. Artifacts:
`runs/wg-tetris-judge-2026-08-17/{pre,post}/`. The heading read *$21.05* until 2026-08-23,
which is the `charged_to_ceiling_usd` counter in `post/SEQUENTIAL.json` and not a cost: the
sweep was resumed, so its first four rounds — $10.61 of `architecture` and `audio` — were
correctly charged $0.00 to that invocation's ceiling and wrongly absent from the published
figure. FINDINGS #121. The **separates stacks** column is
`value=score` `order=perround` on the `post` field — `judge/field_ranks.py --per-aspect`
reproduces all ten of its numbers.

| aspect | 0. reproducibility | 1. ceiling | 3. order-invariance | separates stacks | usable? |
|---|---|---|---|---|---|
| `architecture` | no clean repeat (evidence changed) | pass both | tau 1.00 (13 pairs) | no — 0.75 vs 1.00 within | **no** |
| `audio` | **1 of 2 verdicts flipped** | pass both | **FAIL** tau 0.333 (15) | no — 0.50 vs 1.12 | **no** |
| `fun` | no clean repeat (evidence rebuilt) | pass both | pass tau 0.857 (14) | no — 1.00 vs 1.00 | **no**, but now honest |
| `idiomatic` | **2 of 2 verdicts flipped** | **FAIL** seed 0 | tau 1.00 (12) | 0.75 vs 0.62 | **no** — cross-stack barred (#53) |
| `ux` | 0 of 2 flipped | pass both | pass tau 1.00 (12) | **1.25 vs 0.62** | **the only candidate** |

Gate 4: **4 of 80** claims unlocatable, 12 reconstructed, 8 named only in the pack's text.

**`fun`'s repair is confirmed and is the layer's one clear success.** `seconds_of_play` and
`ticks` are now *constant* across the field (46.9 s, 3001 ticks), so the run-length confound is
gone by construction rather than weakened; the scores instead track
`longest_quiet_stretch_seconds` at **-0.639 / -0.630** and `events_per_second` at
**+0.511 / +0.770**, consistently across both orders. It still does not separate the stacks.

**`ux` is the only aspect clearing every gate with a between-stack range above its within-stack
noise.** It is not reported as a stack signal: its own scores moved 5 of 8 and 3 of 8 between
identical rounds, and nothing statistical here can say whether it reads the frames or a
rendering style (#55). It licenses one targeted experiment, not a ranking.

**#54 is withdrawn** — register entry `WR-arch-ux-redundancy`. `architecture ~ ux` was tau 1.00
on both orders and read as two judges with disjoint inputs agreeing twice; on the repeat it is
0.385 and 0.667, and the redundant pairs the new round finds are different ones that agree with
neither. Two orders of one round are not two observations.

**Tier 3 remains weight 0.00**, now on a repaired instrument rather than a broken one.

## PRE-REGISTERED, 2026-08-17, before the packs were judged

Three comparisons over packs that already exist. Written before the numbers so the reading
cannot be chosen to fit them, and so the outcome most damaging to this layer is named in
advance rather than discovered.

`fun` sees `frames+telemetry`. `fun_frames` is the same question, the same anchors and the
same scale with **the telemetry withheld**. `ux` asks a different question over **the same 96
frames**. Every tau below is reported with its **comparable-pair count**, and a tau computed on
fewer than 6 comparable pairs is arithmetic, not evidence (#52) — `ux` seed 1 has previously
come in at exactly 6, so this is a live constraint and not a formality.

### 1. `fun` vs `fun_frames` — does the telemetry contribute anything?

| outcome | reading |
|---|---|
| rankings **agree** | the telemetry contributed nothing; `fun` is `ux` with extra files, and its post-repair pacing correlations (quiet stretch -0.63, events/second +0.51..+0.77) are the frames talking |
| rankings **differ** | the telemetry is doing work, and `fun`'s pacing claim has support |

### 2. `fun_frames` vs `ux` — is the FRAMES CHANNEL contaminated, or just `ux`?

| outcome | reading |
|---|---|
| **high tau** | two different questions over the same frames produce the same ranking. The frames channel carries one dominant signal, and #59 measured that signal as palette depth (+0.735/+0.823, a 60x split by renderer). **Any frames-only aspect is measuring the rasteriser, whatever it asks.** |
| **low tau** | the frames carry more than one separable signal; #59 retires `ux` specifically rather than the channel |

### 3. The interaction, which is the one that matters

> **If `fun` ≈ `fun_frames` AND `fun_frames` ≈ `ux`, then `fun`'s post-repair pacing
> correlation is palette depth reaching it through the frames.** That retires `fun` on the
> same grounds as `ux` and **closes tier 3 completely**, rather than leaving one
> honest-but-non-separating aspect standing.

That is the outcome most damaging to the layer, so it is stated first. It is also the one the
evidence currently points at: `fun` survived adjudication only because its *telemetry*
confound was removed (#52), and nobody has yet asked whether a *frames* confound replaced it.

The two weaker outcomes are worth as much and must not be reported as disappointments:

- `fun` ≉ `fun_frames` would be **the first positive result the subjective layer has
  produced** — evidence that a judge read the evidence it was given rather than the packaging.
- `fun_frames` ≉ `ux` would bound #59 to one aspect instead of a whole channel, which changes
  what a future frames-based aspect may be asked.

**No outcome here rescues a cross-stack ranking.** Even the best case leaves `fun`'s
between-stack range at 1.00 against a within-stack spread of 1.00 (measured), which separates
nothing. What is at stake is whether the layer measures *anything real about a submission*, not
whether it can rank stacks.

## RESULT, 2026-08-21 — the pre-registration answered. $10.20

`fun_frames` run on `g2_tetris3d` at two presentation orders ($2.08) plus four repeats of one
order for gate 0 ($8.12). `fun` and `ux` were **not** re-run: their 2026-08-17 rounds are stored,
which is what "over packs that already exist" meant. Same 8 submissions in all six rounds.

**Field choice.** `g2_tetris3d`, because the pre-registration was written against it and `fun`
exists there, so comparison 1 is like-for-like against a stored round. On `g4c`, `fun` has never
run, so comparison 1 would have needed a fresh `fun` round on a different task — changing the
comparison after the fact.

### Gates, run rather than inferred

| gate | verdict |
|---|---|
| completeness (#62) | **executed on the field judged**, not assumed: `code` REFUSED (5 of 8 dropped, spread 3), `frames` BUILT. Neither aspect reads code |
| pack non-emptiness | n=8, `usable=true`, 6055 and 4655 evidence chars |
| blinding of the withheld channel | **0 telemetry-vocabulary hits** in `fun_frames` evidence; 50 and 24 frame references |
| ceiling | "separates the field" both orders, not saturated |
| order-invariance | `fun_frames` seed0~seed1 tau +0.692 (13 pairs); `fun` +0.857 (14); `ux` +1.000 (12) |
| **gate 0, reproducibility** | see below — it is the one that makes the rest readable |

### Gate 0 first, because it sets the floor

Four judgings of the **same field in the same presentation order**. Absolute scores wobble —
5 of 8 submissions moved, mean absolute change 0.75, one moved by 2 — but the **order** is
stable:

| | |
|---|---|
| mean self-tau, instrument vs itself | **+0.853** (range +0.714 .. +1.000, 14-18 pairs) |

**That is the floor any cross-aspect tau must be read against.** A disagreement is only real if
it is worse than the instrument's disagreement with itself.

### The three comparisons

Seed-averaged scores, Kendall tau over pairs comparable in both rankings, pair counts stated
(<6 would be arithmetic, not evidence — none are):

| # | comparison | tau | pairs | vs floor +0.853 |
|---|---|---|---|---|
| 1 | `fun` ~ `fun_frames` | **+0.043** | 23 | far below |
| 2 | `fun_frames` ~ `ux` | **-0.364** | 22 | far below |
| - | `fun` ~ `ux` (context) | +0.143 | 21 | far below |

**1. The telemetry is doing work — the pre-registered positive result.** The rankings do not
agree, and they miss by far more than the instrument misses itself. Adjudicated to specific
submissions rather than left as a coefficient: `godot__t1` is `fun`'s best (3, 3) on telemetry
evidence — *"lock median 5.48s, fastest of 8; quiet_fraction 0.145, lowest of 8"* — and
`fun_frames`'s worst (1, 1), where the frames-only evidence sees a HUD that never changes.
`unity__t0` moves the opposite way for the mirror reason. **The submissions that move are
exactly the ones whose telemetry was extreme.** This is the first positive result the subjective
layer has produced.

**2. The frames carry more than one separable signal, so #59 bounds to `ux` and not the
channel.** Two different questions over the *same* 96 frames produce opposed rankings. Confirmed
by mechanism, not only by tau: correlating each aspect against distinct-colour counts (#59's own
method, Spearman on average ranks, n=8) gives

| aspect | ~ distinct colours |
|---|---|
| `ux` | **+0.528** — replicates #59's +0.735/+0.823, same sign |
| `fun_frames` | **-0.120** — not tracking palette depth |

**3. The interaction — the outcome most damaging to this layer — DID NOT LAND.** It required
`fun` ≈ `fun_frames` **and** `fun_frames` ≈ `ux`. Neither holds. `fun`'s pacing signal is not
palette depth reaching it through the frames, and **tier 3 does not close on these grounds.**

### What this does NOT establish

- **No cross-stack ranking, exactly as pre-registered.** `fun_frames`'s between-stack range is
  1.50 against a within-stack floor of 0.75 — but that is unity at 2.25 with godot, rust and ts
  all on *exactly* 0.75, at n=2 per stack on a 0-3 scale. Three independent stacks on an
  identical value is rule 9's shape; it is not reportable as an ordering.
- **Tier 3 stays at weight 0.00.** What moved is the evidence that an aspect reads its evidence,
  not evidence that it can rank stacks.
- The floor was measured on `fun_frames` alone. Applying it to `fun` and `ux` is an assumption,
  supported but not established by their order-to-order taus (+0.857, +1.000).

### A capture-geometry confound, declared

`frame_parity.py` reports `g2_tetris3d__unity__t1` filmed at **420x640** where the other seven
are 640x400 — a portrait/landscape flip, and both frames-only aspects were shown it directly.

**It cannot manufacture the disagreements above**, because all three aspects saw identical
frames, so a shared anomaly cancels in any comparison between them. It does qualify each
aspect's absolute ranking of that submission.

**It should have been run before spending, not after.** Its own docstring says "Run BEFORE
reading any frame-derived number." The completeness gate was run explicitly on instruction; this
one was not, and the fact that it turned out not to carry the result is luck rather than method.

**Now wired into the path (2026-08-21).** `field.py::pack_parity` runs inside `build_pack`, and
a frames-reading aspect on a field with mixed capture geometry is **refused**, beside the
completeness gate. It refuses rather than annotating because an annotation is #62 — a manifest
field nothing reads. Pinned both ways and for scope: divergent refuses, uniform builds, a `code`
aspect never consults it.

**Consequently this very round would now be refused.** That is correct. The remedy is to re-film
`g2_tetris3d__unity__t1` at 640x400 and re-judge, and until then the two taus above stand with
the confound declared. `g4_platformer`, `g1_pong` and `g3_arena` are uniform and unaffected.

## PRE-REGISTERED, 2026-08-22, before the capped/uncapped packs were judged

Task 09. **Written before any call was made**, so the reading cannot be chosen to fit the result.

`idiomatic` on `g4_platformer` (`wg-g4c-2026-08-21`), two presentation orders per arm, four calls
total. The only difference between arms is the pack: the stored **capped** packs (160,000-char
budget, files dropped by sort order) against **uncapped** packs rebuilt from the same submissions
with the same filters and no budget (#69). Same submissions, same starter, same aspect, same
seeds, same model.

Measured on one submission, `g4_platformer__unity__t0`: capped 15 files / 160,038 chars,
uncapped 32 files / 388,968 chars. **53% of it was never shown to any code judge.**

### What each outcome means

| outcome | reading |
|---|---|
| **ordering unchanged** (tau ≈ +1 between arms) | the extra 59% of code did not change the verdict. That is **not** a null: it is a finding about what `idiomatic` attends to — it reaches its answer from a fraction of the evidence, which is consistent with #53's prior hypothesis and makes it sharper, not weaker |
| **ordering changed** | every stored code judgement in this project was made on a biased sample, and #53 must be re-read from scratch. #62 stops being "the field was truncated" and becomes "the truncation moved the answer" |
| **ordering changes less than the instrument's own noise** | uninterpretable at this n, and must be reported that way rather than as "unchanged" |

**The floor is already measured and this comparison must be read against it**: gate 0 gave a mean
self-tau of **+0.853** for repeated judging of an identical field (FINDINGS #68). A between-arm
tau at or above +0.853 is indistinguishable from the instrument disagreeing with itself, and
**"unchanged" may only be claimed above that line.** Below it, the packs changed the answer.

### Stated in advance because it is the uncomfortable one

**"Ordering unchanged" is the outcome that most complicates the story**, because it would mean the
budget removal — a real defect, correctly fixed — bought no change in any conclusion. It will be
reported exactly as plainly as the other. The fix stands on its own regardless: a judge shown half
a submission cannot be said to have read it, whatever score it produced.

### Also captured, because it has never been captured before

The **file-open tool calls** each judge actually makes, per arm, into the round's record. That
answers a question nothing in this project can currently answer: *did the judge that was given 32
files read more of them than the one given 15, or does it open roughly N files regardless?* If the
counts are similar across arms, that is the mechanism behind an unchanged ordering, and it is
measured rather than inferred.

## RESULT of the capped/uncapped pre-registration, 2026-08-22. $27.30

`idiomatic` on `g4_platformer` (`wg-g4c-2026-08-21`), two presentation orders per arm.
Uncapped $15.24, capped $12.06. The capped arm required `--allow-truncated`, because the
repurposed completeness gate refused it — the gate working exactly as intended on a field that
really is truncated.

**Verdict: outcome 3 of the three pre-registered — UNINTERPRETABLE at this n.** Not "unchanged",
which the pre-registration explicitly forbade claiming below the floor, and not "changed" either.

| measurement | value | pairs |
|---|---|---|
| between arms, seed-averaged | **tau -0.231** | 13 |
| between arms, seed 0 | +1.000 | **3** — below the 6-pair bar, arithmetic not evidence |
| between arms, seed 1 | -1.000 | 8 |
| **capped arm against ITSELF** (order stability) | **+0.333** | **6** |
| uncapped arm against itself | +1.000 | **4** — also below the bar |
| reference floor (#68, `fun_frames` on tetris) | +0.853 | 14-18 |

**Why it cannot be read as "the packs moved the answer", tempting though the -0.231 is.** The
capped arm disagrees *with itself* across presentation orders at +0.333 — nearly as far from the
floor as the two arms are from each other. When an instrument's disagreement with itself is the
same size as the effect, the effect is not measurable. The +0.853 floor was measured on a
different aspect and a different game and **does not transfer**; this aspect on this field has no
measured floor, which is precisely what task 08 exists to supply.

### The ceiling is the cause, and it fails its own gate

Every round produced only **2 distinct scores** across 8 submissions, and **2 of the 4 rounds fail
the ceiling gate outright** (uncapped seed0: 7 of 8 at score 3; capped seed1: 6 of 8). Nearly
every pair is a tie, tie counts are what tau discards, and 13/8/6/4/3 comparable pairs is the
result. A near-saturated field cannot support a ranking comparison however many times it is run.

This is `eval/IMPROVEMENTS.md` 11b's critique arriving as data: the two rounds that "passed" the
ceiling gate did so on **modal fraction** while having the same 2 distinct scores as the two that
failed. The gate is measuring bunching, not separation.

### What IS interpretable: the judge reads more when given more

The pre-registered mechanism question — *does the judge open roughly N files regardless?* — has a
clean answer, and it is no.

| arm | pack size | files opened | subagents | tool calls | cost |
|---|---|---|---|---|---|
| capped seed0 | 1.28 M chars total | 79 | 8 | 134 | $5.98 |
| capped seed1 | | 98 | 4 | 171 | $6.08 |
| uncapped seed0 | 2.23 M chars total | **115** | 4 | 185 | $7.84 |
| uncapped seed1 | | **178** | 8 | 246 | $7.41 |

**1.74x the content produced 1.5-1.8x the file opens and ~1.25x the cost.** The judge scales its
reading with what it is handed rather than sampling a fixed budget — so the removed cap was
genuinely constraining what it could read, not merely what it was offered. It also used subagents
in every round (4-8), which is the capability verified before it was put in the brief.

**This is the first audit trail of what a judge actually read in this project.** It answers a
question that was previously unanswerable, and it is the part of this round that survives.

### What this does and does not settle

- It does **not** show the cap changed conclusions. It shows the experiment cannot tell, and why.
- It does **not** weaken #69. A judge shown 57% of a submission cannot be said to have read it,
  whatever score came out; the removal stands on that argument, not on this measurement.
- The re-run needs a **measured floor for `idiomatic` on this field** and enough rounds to beat
  the tie rate — task 08, sequential to resolution, reporting SD and SE separately.

## The judge's own SD, measured at last — 2026-08-22, at zero cost

Task 08 asks for repeats until SE beats the between-submission difference, and notes that
**repeats shrink SE = SD/sqrt(n) but never SD**, which had never been measured. It can be
computed from the four identical-input `fun_frames` repeats already on disk.

| | |
|---|---|
| pooled within-submission **SD** | **0.612** (on a 0-4 scale) |
| SE at n=4 | 0.306 |
| between-submission spread of means | 2.250 |
| smallest adjacent gap between means | 0.250 |
| **n for SE < that gap** | **7** (n=6 gives SE = 0.250, equal, not below) |

**The judge moves ±0.6 on evidence that has not changed.** That is the instrument's reliability
and no amount of repeating improves it — it is why #68's rank-order stability (+0.853) and its
score instability (5 of 8 moving) were both true and not in conflict.

### The number that decides where to spend

**Seven repeats is tractable.** But that figure is for `fun_frames` on `g2_tetris3d`, a field it
separates well (spread 2.250). On `idiomatic`/`g4_platformer` the same arithmetic is hopeless:
that field returned **2 distinct scores in every round with 2 of 4 rounds failing the ceiling
gate** (#74), so the adjacent gaps are ~0 and `n = (SD/gap)^2` diverges.

> **Task 08's target is reachable or unreachable depending on the field, and the field is chosen
> before any money is spent.** Repeating on a saturated field measures a tie with ever-greater
> precision. Choose a field whose ceiling gate passes, or the sequential run cannot terminate.

This is #63's precision-is-not-validity in a third form: n buys precision about a mean, and
buys nothing at all when the quantity has no spread to resolve.

## #58's ceiling gate is REPLACED by `separation()` — 2026-08-22

`field.ceiling()` asked whether one round's scores are **bunched**: `modal_fraction <= 0.7`. Two
independent reasons that is the wrong test, one arithmetic and one empirical:

- Over eight submissions the statistic can only take k/8, so **0.7 sits in the gap between 0.625
  and 0.75 with nothing between**. 52% of measured judgements sit on that edge, and three of six
  verdicts flipped on unchanged input — two because a single score out of eight moved (#58).
- **Bunching is not separation.** On `idiomatic`/`g4_platformer`, two of four rounds passed this
  gate and two failed while **all four had the same two distinct scores** across eight
  submissions (#74).

`field.separation()` asks the question directly, from repeats rather than one round:

```
SE = SD / sqrt(n)                      per submission, n judgements of the SAME field
resolved(i, j)  iff  |mean_i - mean_j| > SE_i + SE_j
```

A field separates if at least one pair resolves. Three properties that matter:

| property | why |
|---|---|
| **refuses at n<2** | SE is undefined from one round — which is precisely what the old gate tried to compute |
| **warns below n=4** | an SD from two points flatters SE. The uncapped `idiomatic` arm reported "SEPARATES: 4 of 28" at n=2 on a field with two distinct scores; it is now `separates_field=False` with a low-n warning |
| **distinguishes "not yet" from "never"** | if every mean is identical the required n is reported as `None`: no repetition resolves it |

**`ceiling()` is kept and still reported**, marked superseded in its own docstring, because it
explains every round already run. It describes a round's score shape; it no longer decides
whether an aspect separates a field.

### Non-termination is a measurement

> A field where no n terminates is a field whose submissions are **indistinguishable to that
> aspect** — the same answer this project's four other instruments have returned about the four
> stacks. It is reported with its measured gap, never as an experiment that did not finish.

### A correction to the n=7 figure I quoted

The "n=7" estimate used `SE < gap` for a single submission. The correct two-sample test compares a
gap against the **sum of both SEs**, which is stricter: on the stored `fun_frames` repeats the
smallest non-zero gap (0.250) needs **n≈24**, not 7. The field nonetheless already separates —
**19 of 28 pairs resolve at n=4** — because most gaps are much larger than the smallest one.
Resolving *some* pair and resolving *every* pair are different targets and the second is far more
expensive.

## Task 08 result: `fun_frames` / `g2_tetris3d` SEPARATES at n=7. $10.12

Seven repeats of the same field in the same presentation order. **All seven were re-run from
scratch rather than topping up the four stored ones**, because the brief now names the capture
geometry for this field and the stored repeats predate it — topping up would have pooled two
briefs mid-experiment.

| | |
|---|---|
| pooled within-submission **SD** | **0.577** (0-4 scale) |
| SE at n=7 | 0.218 |
| **pairs resolved** (`gap > SE_i + SE_j`) | **18 of 28** |
| verdict | **SEPARATES** |

| submission | scores | mean | SD |
|---|---|---|---|
| unity t1 | 3 2 2 3 3 3 3 | 2.71 | 0.49 |
| unity t0 | 2 2 3 3 3 3 3 | 2.71 | 0.49 |
| rust t1 | 2 2 1 2 2 1 2 | 1.71 | 0.49 |
| ts t0 | 1 1 2 1 1 2 1 | 1.29 | 0.49 |
| ts t1 | 2 1 1 0 1 1 2 | 1.14 | 0.69 |
| godot t1 | 1 0 0 1 2 2 1 | 1.00 | 0.82 |
| rust t0 | 2 1 1 1 1 1 0 | 1.00 | 0.58 |
| godot t0 | 1 1 0 1 1 0 1 | 0.71 | 0.49 |

The brief change looks neutral: old brief n=4 gave pooled SD 0.612 and 19/28 resolved, new brief
n=7 gives 0.577 and 18/28. **Not a clean comparison** — brief and n both changed — but nothing
suggests naming the geometry moved the judge.

### The done-when's literal criterion is self-defeating, and this run proves it

"SE below the smallest non-zero between-submission gap" cannot be satisfied, and not because the
field is hard. Computed on this one dataset by truncating it:

| n | pooled SD | SE | smallest gap | SE < gap? | pairs resolved |
|---|---|---|---|---|---|
| 2 | 0.500 | 0.354 | 0.500 | YES | 9/28 |
| 3 | 0.577 | 0.333 | 0.334 | YES | 17/28 |
| 4 | 0.577 | 0.288 | 0.250 | no | 17/28 |
| 5 | 0.570 | 0.255 | 0.200 | no | 17/28 |
| 6 | 0.581 | 0.237 | 0.166 | no | 18/28 |
| 7 | 0.577 | 0.218 | **0.143** | no | 18/28 |

> **Means over n rounds live on k/n, so the smallest gap shrinks as 1/n. SE shrinks as
> 1/sqrt(n). The target recedes faster than the estimate closes on it** — so the criterion is
> satisfiable only at n=2 and n=3, where SE is least trustworthy, and becomes permanently
> unreachable exactly as the measurement gets good.

"Resolve the smallest gap in the field" is also not a question anyone has: at n=7 it would need
**n=66**, and at n=66 a new smaller gap appears. The meaningful question is whether ANY pair
resolves, which is what `separation()` tests and what plateaus at 17-18/28 from n=3.

**Proposed done-when, in place of the SE-vs-smallest-gap clause:** *at least one pair resolves at
the reported n, with pooled SD, SE and the resolved-pair count stated — or no pair resolves and
the field is reported unresolvable with its measured gaps.* The OR branch is untouched.

### ⚠️ An unadjudicated stack pattern, flagged and NOT claimed

| | |
|---|---|
| between-stack range of means | **1.857** |
| mean within-stack gap | **0.286** |

Unity 2.71/2.71, rust 1.71/1.00, ts 1.29/1.14, godot 1.00/0.71. That is the first tier-3 result
where between-stack clearly exceeds within-stack spread, at 6.5x.

**It is not reportable and must not be quoted as a stack result.** A stack-correlated pattern here
is an instrument defect until a mechanism is named in the code, and this project is six for six on
that. Two checks already done: it is **not** palette depth (`fun_frames` ~ distinct colours =
-0.120, where `ux` was +0.528), and it is **not** aspect ratio (unity t0 is 640x400 and t1 is
420x640, and both score 2.71). Unity's two trials returning *identical* means is itself rule 9's
shape. What it is remains unknown, and until it is named this is an open flag.

## Task 23 result: ALL SIX aspects separate `g4_platformer` at n=5. $100.84

The gap task 23 was filed against: `separation()` had been run on **one** aspect and **one**
field, so five of six aspects had no measured reliability at all. Six aspects x 5 repeats of the
same field in the same presentation order, `wg-g4c-2026-08-21`, artifacts in
`runs/wg-aspect-reliability/`.

**Per aspect, never pooled across aspects.** The aspects read different evidence — code, frames,
telemetry, audio — and an SD across them would be rule 4's own example. `pooled_sd` below pools
across the eight *submissions* of one aspect, which is a homogeneous population.

| aspect | n | pooled SD | SE | resolved | marginal | verdict |
|---|---|---|---|---|---|---|
| `audio` | 5 | **0.418** | 0.187 | 21/28 | 4 | SEPARATES |
| `ux` | 5 | 0.447 | 0.200 | 20/28 | 7 | SEPARATES |
| `architecture` | 5 | 0.461 | 0.206 | **10/28** | 1 | SEPARATES |
| `fun_frames` | 5 | 0.487 | 0.218 | 12/28 | 1 | SEPARATES |
| `idiomatic` | 5 | 0.512 | 0.229 | 13/28 | 1 | SEPARATES |
| `fun` | 5 | **0.536** | 0.240 | **23/28** | 0 | SEPARATES |

**No aspect is in the "cannot ever resolve" branch.** That branch is reserved for a field whose
means are identical, where no n helps; here every aspect has real gaps and the question *"does
any pair resolve"* is already answered yes at n=5. Resolving the **smallest** gap is a different
and far more expensive target — n=18 (`audio`) to n=29 (`fun`) — and per the correction recorded
above it recedes as n grows, so it is not a target anyone should adopt.

### The result that contradicts what was expected

**#74 read `idiomatic` on this field as saturated** — four rounds, two distinct scores across
eight submissions, "a saturated field cannot be made informative by more rounds of the same
size." At n=5 it resolves **13 of 28 pairs**, and `architecture`, which uses only **two** distinct
score values in all five rounds, still resolves 10.

The reconciliation is arithmetic, and it is the point of `separation()` over `ceiling()`. A round
scores on integers; a **mean over five rounds lands on fifths**. Two submissions that are always
"3 or 2" separate as 2.8 against 2.4 once the rounds are averaged. Bunching within a round is not
the same as indistinguishability across rounds, which is exactly what #74's own conclusion
assumed and could not test at n=2.

### Three caveats, all of which cut against the headline

**1. A submission the judge scores identically five times gets SE exactly 0**, and then resolves
against everything with any gap at all. Five equal integers are weak evidence that the true SD is
zero. Discounting every pair that touches a zero-SE submission:

| aspect | resolved | of which touch a zero-SE submission | survive |
|---|---|---|---|
| `fun` | 23/28 | 7 | **16** |
| `audio` | 21/28 | 11 | **10** |
| `ux` | 20/28 | 6 | **14** |
| `idiomatic` | 13/28 | 0 | **13** |
| `fun_frames` | 12/28 | 7 | **5** |
| `architecture` | 10/28 | 7 | **3** |

`idiomatic` is the only aspect with no zero-SE submission, so its 13 is the one count needing no
discount. `architecture` and `fun_frames` are the two that mostly do not survive it.

**2. The resolved-pair count is itself noisy at this n**, and not monotone in n — which a
well-behaved estimator over nested subsets of the *same* rounds would be:

| aspect | n=2 | n=3 | n=4 | n=5 |
|---|---|---|---|---|
| `ux` | 7 | 19 | **15** | 20 |
| `fun_frames` | 2 | 8 | 11 | 12 |
| `fun` | 19 | 22 | 22 | 23 |
| `audio` | 13 | 18 | **23** | 21 |
| `architecture` | 4 | 12 | **8** | 10 |
| `idiomatic` | 15 | 21 | **11** | 13 |

Four of six fall as n rises somewhere in that range. **Read the verdict (separates / does not),
not the count**; a count quoted to the pair implies a precision this instrument does not have.

**3. Gate 0 fails on four of six.** `ux`, `fun_frames`, `architecture` and `idiomatic` all flip
their `ceiling()` verdict on byte-identical input; only `fun` and `audio` are "scores move,
verdict stable". This is #58 reproducing on a second field and a wider set of aspects, and it is
the reason `ceiling()` no longer decides anything.

### Rule 9 checked on every flag, and cleared on all of them

Independent submissions returned byte-identical five-round score vectors in four aspects —
`godot__t0`/`godot__t1` under `ux`, three submissions under `fun_frames`, two pairs under
`architecture`, `rust__t0`/`rust__t1` under `idiomatic`. That is rule 9's signature and it was
tested against the evidence rather than argued about:

- **frames** (what `ux` and `fun_frames` read): all eight submissions have distinct frame-strip
  hashes. No two were shown the same pictures.
- **code** (what `architecture` and `idiomatic` read): all eight have distinct pack hashes, and
  `rust__t0` (27 files) and `rust__t1` (18 files) share **zero** identical file bodies.

The actual cause is the scale's granularity. `architecture` used two distinct values across all
five rounds, so only **32** distinct five-round vectors exist for eight submissions; `fun_frames`
used three, giving 243. Collisions at those counts are expected, and `fun` and `audio` — the two
aspects that used the widest range — produced none.

### What it costs, per aspect, because a pooled mean would misprice it 3x

| aspect | $ for 5 rounds | median wall | files opened |
|---|---|---|---|
| `audio` | $3.71 | 261 s | 9 |
| `fun_frames` | $9.70 | 372 s | 97 |
| `fun` | $9.82 | 435 s | 105 |
| `ux` | $10.78 | 347 s | 96 |
| `architecture` | $28.77 | 510 s | 86 |
| `idiomatic` | $38.07 | 559 s | 145 |

**$100.84 total.** A pooled per-call mean would have priced `idiomatic` at a third of its cost and
`audio` at triple — the mistake `eval/AGENTS.md` records against itself.

### What this does NOT establish

**No cross-stack ordering, from any of the six.** Separation is a statement about the *instrument*
— that it can tell two submissions apart — not about which stack is better. The two code aspects
additionally read packs carrying #95's stale files, unequally and stack-correlated, so their
orderings are unreadable for a second independent reason. **Tier 3 stays at weight 0.00**; this
measures whether re-weighting is *conceivable*, and the answer is that reliability is no longer
the blocker for any of the six.

## The three repairs, 2026-08-16 — made, pinned, NOT re-run

No judge call was made for any of this. The decision to spend again is the user's and should be
made against a repaired instrument with its controls shown.

| # | aspect | repair | pinned both directions? |
|---|---|---|---|
| 1 | `fun` | a dedicated 3000-tick play session, separate from the criteria drive; pacing computed over **world** events only, with input echoes classified by a property | **yes** — healthy 0.192, deliberately dead **1.000** |
| 2 | `architecture` | `blind_language=True`: every source file renamed to a neutral `.src`, and since 2026-08-23 every extension the content NAMES rewritten too | **partly** — pack still complete (126 files, identical bytes), but **8 of 8** submissions remain identifiable by syntax |
| 3 | `architecture` | code briefs now require citing **pack** paths; `adjudicate.py` splits reconstruction from fabrication | **yes** — 11 of 11 flags were reconstruction, **0** fabrication |

**Repair 1's first attempt was wrong and the pin caught it.** Computing pacing over every event
name meant a bot pressing keys on a cadence manufactured a cadence: a deliberately dead 3D
Tetris emitted 200 `move` and 100 `rotate` events, nothing else, and scored a quiet fraction of
0.005 — indistinguishable from a healthy game. Fixed by classifying echoes (an event that never
fires on an idle tick), guaranteeing idle ticks every other tick, dropping hard-drop from the
tetris policy so gravity does the locking, and treating *zero* world events as quiet for the
whole run rather than 0.0.

Result on the eight real submissions: `quiet_fraction_of_run` **0.93–1.00 for all eight** ->
**0.145–0.194, varying between submissions**. Events per run 6–9 -> 83–115. All four references
still pass every criterion.

**Repair 2 is honest about its own limits.** Renaming `.gd`/`.rs`/`.ts`/`.cs` to `.src` removes
a label, not the leak: `func`/`extends`, `fn`/`impl`, `export const` and `using UnityEngine`
identify the stack in all 8. A leak closable only by destroying the evidence is a constraint on
what the aspect can be asked, not a bug. `idiomatic` keeps its extensions and stays
**per-stack-only** — a result, not a defect to engineer away.

**And it was less than it claimed until 2026-08-23.** The rename covered the extension of the
file the judge OPENS and nothing covered the ones it READS — an import specifier, a comment
naming a sibling, and above all the `CHANGED.txt` the packer itself writes from
`git diff --stat`, which lists every authored path with its true suffix. Measured over all 84
stored packs after `neutralise`: **2,083 arm-naming extension tokens, 0 after**
`field.blind_extensions`, which runs only where `blind_language` is set. **Every stored
`architecture` round was judged before this** — say so wherever their ordering is reported,
alongside the `neutralise` caveat in `eval/RUNS.md`. The 81 surviving `import.meta` occurrences
are declined deliberately: ESM's namespace object is spelled like a path and names no file.
**The directory half of the same leak split in two when it was partitioned (task 95).** Of the
1,561 tokens surviving `blind_extensions` in the 8 stored `architecture` packs, **182 were in
`CHANGED.txt` and every one was a real path**; the other 1,379 were in code content and only 149
were paths — `public` is the C# access modifier 1,129 times. `CHANGED.txt` is now rebuilt from
the pack's own origin → label manifest under `blind_language`, so it reads ` sim/01.src | 42 ++--`:
**330 arm-naming directory segments to 0** on a rebuild of `wg-g4c`'s field, with the other 199
files of the pack byte-identical. The code half stays open, and the measurement that declined a
vocabulary rewrite for it is in `tasks/103`. **No stored round is repaired by this** — every
`architecture` round on disk read a `CHANGED.txt` listing the real authored tree.

**Repair 3 changed the number by two orders of magnitude in interpretation.** "The judges
fabricate their evidence, 15 of 16" is, correctly split, **1 unlocatable claim in 80**.

> **After all three, the statistical gates still cannot tell you whether these aspects work.**
> An artifact is more order-invariant than a judgement (#55). Only adjudication can, and it
> must be run on the passes.

## The discrimination test — pre-registered 2026-08-16, BEFORE the tetris sweep landed

Passing the four gates says a judge is *usable*. It does not say it found anything. The
question the whole matrix now rests on is narrower:

> **Does any aspect separate four stacks whose deterministic scores are identical?**

A per-stack mean cannot answer that on its own, because it has no noise floor attached. The
floor is already available and costs nothing: **each stack appears twice**, as two
independent agent runs, so the spread between a stack's own two submissions is exactly the
variation that is *not* a stack difference.

    between-stack range  =  max(per-stack mean) - min(per-stack mean)
    within-stack noise   =  mean over stacks of |score(t0) - score(t1)|

    range <= noise  ->  NO SEPARATION, whatever the ordering looks like

This is the deterministic tiers' own lesson applied one layer up: within a cell they differ on
almost no criterion — **5 of 436** paired criteria in `wg-matrix`, **0 of 232** in `wg-audio48`,
reported per run and never pooled — so those tiers have no usable resolution below the cell and
cannot report a difference above it. An aspect whose between-stack range sits inside its own
within-stack spread is in the same position, and reporting its ranking would be reporting
noise with an order imposed on it.

Registered before the numbers, so the threshold cannot be chosen to fit them. First reading,
on the two `g1_pong` calls already paid for, showing exactly why it is needed:

| aspect | seed | range | within-stack | reads as |
|---|---|---|---|---|
| `architecture` | 0 | 1.00 | 0.25 | separates |
| `architecture` | 1 | 0.50 | 0.75 | **no separation** |

Same aspect, same field, opposite answers on two presentation orders — which is the gate-3
failure showing up in the thing gate 3 exists to protect.

## Weights

**All subjective layers are weight 0.00 until they pass the gates above.** There is now exactly
one scored tier: **play-bot 1.00**. Tier 1 became a PASS/FAIL gate on 2026-08-23 and carries no
weight — `RUBRIC.md` has the measurement, FINDINGS #92 and #123.

That matters here for one reason beyond bookkeeping: the standing argument for keeping tier 3 at
0.00 is that its bounded contribution — 0.0154 at the 0.10 weight it briefly held — could not
reorder anything against the deterministic tiers' **tightest adjacent gap of 0.0622**. That gap
was computed on tiers 1+2 combined, and `overall` is now tier 2 alone, so it was recomputed
before being relied on again.

Recomputed from the 24 stored `wg-matrix-2026-08-13` records, per game, as the smallest
difference between adjacent *distinct* values:

| game | tier 2 alone | old 0.31/0.69 |
|---|---|---|
| `g1_pong` | 0.0769 | 0.0531 |
| `g2_tetris3d` | 0.0769 | 0.0531 |
| `g3_arena` | **0.0667** | 0.0460 |

**Dropping tier 1 widens every gap**, because the constant 0.31 it contributed compressed them.
The judge's 0.0154 is still a factor of four short of the tightest, so the argument survives and
is slightly stronger than when it was made. Note that **0.0622 is not reproduced by this method
and the method behind it is not recorded anywhere** — quote 0.0667 with the method above, not the
older number. The second argument for the 0.00 — the aggregate is noisiest exactly where it would
matter — does not depend on the weighting at all, which is why the two were kept separate.

Weight decisions belong to the project owner and have been reversed twice on evidence. Bring
discrimination, independence and stability numbers; do not bring an argument.

## What would improve the layer most, in order

1. **Adjudicate the 11 existing firings against frames.** Free. Determines whether the only measured
   signal in the entire subjective layer is real or a capture artifact.
2. **Build the idiomatic-stack-use judge.** The only aspect whose subject is the variable under test.
3. **Retire or radically rewrite the ten code criteria.** They produced zero information across 24
   submissions. Rewriting them as comparative — *rank these eight codebases* — is the only version
   worth keeping; asking "is this good code" of work that is uniformly competent will always
   saturate.
4. **Add gameplay and tuning judges** fed by telemetry that already exists.
5. **Decide whether audio belongs in the task set.** DONE — the task now requires it, and the
   mechanical half is graded deterministically (six criteria, each with a mutant that makes it go
   red). The `audio` judge is left only the part a script cannot answer: fit and readability.
