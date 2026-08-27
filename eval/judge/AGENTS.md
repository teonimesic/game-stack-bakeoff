# eval/judge/ — grading a submission

**`JUDGING.md` is the design document for the subjective layer** — what each judge looks at, the
layer matrix, the validation gates, and what the 24-submission matrix showed about which criteria
carry information. Read it before adding or changing a judge.

Three tiers. The building agent must see none of them.

| Tier | Weight | Implemented in |
|---|---|---|
| **Programmatic** — builds, gate green, lints, tests, frames render and animate, perf probe, **audio** | **GATE — not scored** | `checks.py`, `static.py`, `probe.py`, `png.py`, `audio.py` |
| **Play-bot** — a scripted bot drives thousands of ticks and asserts the game actually plays | **1.00** | `bot_pong.py`, `bot_tetris3d.py`, `bot_arena.py` |
| **LLM judge** — one specialist per aspect, each ranking a whole eight-submission field | **0.00** | `aspects.py`, `field.py`, `field_sweep.py`, `adjudicate.py`, `anonymise.py`, `RUBRIC.md` |

`evaluate.py` runs all three. `regrade_wholegame.py` recomputes scores from stored tier files.

## The play-bot tier carries the whole weight, and `bot_mutants.py` asks 3 questions of it

```bash
python3 judge/bot_mutants.py               # all 3, ~90s, needs `just`
python3 judge/bot_mutants.py --hazards     # the per-criterion registry, offline
python3 judge/bot_mutants.py --selftest    # can the registry gate go red? offline
```

| | asks | subject |
|---|---|---|
| **mutant** | can this criterion FAIL? | the reference with the behaviour surgically removed |
| **variant** | can it still PASS on a correct game the reference does not resemble? | a correct game; **every** criterion must pass |
| **pending** | a correct game it FAILS today, with the failing ids declared | a correct game; the measured set must equal the declared one |

**A VARIANT RUNS THE WHOLE BOT ON ONE FIXTURE, so its coverage is per fixture and not per
suite.** "N variants for M criteria" is the wrong shape twice: the population is the **70**
criterion instances the 4 bots report rather than the smaller set that carries a mutant, and
a `ref_pong` variant says nothing about `ref_arena`. Read the per-fixture count, and read it out
of `--hazards` rather than off a total.

**An end condition has 2 ways to be wrong and both need pinning.** *Does the game ever say it
is over*, and *does saying so stop it* — the prompt's own second clause. Every bot reaches the
second through `probe.end_condition_holds`, 1 copy for all 4: it idles with nothing
pressed, then presses the bot's controls and reads that phase **through the reset**, because the
prompt's "until it is reset" contemplates a reset existing and an agent may bind it to a
control. **Every tick of both phases is read, never the endpoints** — a value that moves and
comes back passes an endpoint comparison — and the first tick that broke goes in the evidence
with why. The value each bot guards is its own and must be one its simulation MOVES — a dead
arena player earns nothing and a full tetris well clears no layer, so in both the score is a
constant whatever the game does, and `_death` guards `kills` and `_gameover_check` the
well's filled-cell total beside it (`tasks/157`).

**`HAZARDS` is one recorded answer per criterion to *what correct-but-unusual game would
mis-score this?*, and the gate is that there are 70 of them.** A criterion added without an
answer fails the suite; "nobody could construct one" is an answer and has a shape id for it.
Each entry names a shape — the families #34, #29 and #46 adjudicated — so *"is anything covering
the shapes #46 names?"* is a group-by rather than a memory.

**A `Pending` is a DECLARED false negative and it is not a tolerance.** `Variant.tolerates`
waives a criterion silently and is the one field in the suite where a failure is allowed not to
count; a pending entry names the criterion, names the ticket that owns the repair, and goes red
on any set but the declared one — **including the empty set**, which is what a landed repair
looks like and which is the only thing that makes the entry get promoted into `VARIANTS`.
Repairing the criterion instead is a **re-scoring event** and belongs to its own ticket with a
`tier2_census.py` before-and-after, which is why the entry exists rather than a quiet fix.

## Scenes are the second task class, and tier 2 is a different instrument

A scene has no player, so `bot_*.py` has no referent. **`scene_probe.py` replaces it** and
carries the same weight, because it is the same kind of thing: binary criteria computed
deterministically, every one reported, nothing asked of a model. It reads the per-tick telemetry
AND the captured frames, and each criterion says which halves it has.

```bash
python3 judge/scene_probe.py s1_parallax <submission>   # drive one submission
python3 judge/scene_mutants.py                          # both directions, ~22s
python3 judge/scene_mutants.py --census                 # what each criterion separated
python3 judge/scene_mutants.py --census-selftest        # can the census say NO?
python3 judge/scene_mutants.py --attribution-selftest   # which rows are one layer's?
```

6 things to know before you touch any of it:

- **1 submission has met these criteria** (`eval/RUNS.md`), and every threshold was still
  chosen against fixtures written by the same hand as the criterion. Treat a scene score as
  fixture-validated until a matrix has run, and say so wherever one is reported. First contact
  scored 5 of 6, left 2 of 8 criteria unscored, and produced a false negative in
  `layers.depth_ordered`, which read a wrapped `offset` as a scroll rate — #46's shape, and a
  mutant could not have found it. `tasks/162` repaired it — `ParallaxScene._walk` is now the only
  way to read an `offset` — and `tasks/164` repaired the reliability filter that repair unblocked.
  The re-grade stands at **6 of 6**, with `layers.image_parallax` back to `scored=False` — and
  unmoved by `tasks/174`, which repaired the reason it gives rather than the verdict.
- **`--census` reports over FIXTURES and says so.** It answers whether a criterion can take both
  values on material this repository wrote. `--runs-root` looks for stored scene gradings and
  prints `NOT ASKED` when there are none, never `0 separated` — the 2 are different claims
  (rule 12).
- **An absent image half and an unestablished experiment are not the same thing**, and
  `scene_probe.py`'s docstring holds the table. A film recipe that produced no frames is a fact
  about the submission; a run in which no captured frame lands inside the light ramp is an
  experiment that could not be set up, and comes back `scored=False`.
- **The image-side shift estimator is not exact, and its error has one shape**: a band holding a
  large object that is stationary on screen. `ParallaxScene._reliable` and the wrap check's
  `blind` counter both name it, so the robustness lives in the criteria rather than in the
  estimator. `DECISIONS.md` holds the 5-candidate comparison and the per-fixture miss counts.
- **A DECLARED BAND IS NOT A REGION OF THE FRAME THAT BELONGS TO ONE LAYER.** Declared bands
  overlap, and `best_shift` answers for whichever visible content carries the band's gradient
  energy rather than for the layer it was asked about. So a layer is measured only on rows no
  other declared band covers, clipped to the frame; below `MIN_OWN_ROWS` of them it is
  UNATTRIBUTABLE — reported, kept out of the ordering and out of the score, and never given
  another layer's motion. The subtraction is over **every** other band, nearer and farther both,
  and `eval/SCENES.md` holds the measurement that decided that. The pin is `scene_mutants.py
  --attribution-selftest`, offline: a variant carrying such a scene must tolerate
  `layers.image_parallax`, and a tolerated criterion cannot go red (`tasks/174`).
- **A band the frames cannot resolve is refused before agreement is asked, and agreement is
  asked in PIXELS.** A layer that moves half its own span or more between 2 captures draws a
  picture that is a residue of its repeat length, and it can agree with itself perfectly while
  doing it — which is why the aliasing test is a precondition on the pair (`eval/SCENES.md`).
  Neither half is reachable by a fixture that exercises the other, so `scene_mutants.py
  --reliability-selftest` drives `_reliable` over hand-written layer records and 3 mutants of the
  shipped file, and reads the NOTE as well as the verdict: a note naming a reason the record does
  not have is a false sentence no pass/fail check can see, and 1 of the 3 mutants moves nothing
  else. It reads no fixture and needs no toolchain.

**Tier 3 for scenes is `fidelity`, `motion` and `framework_fluency`**, in the same `ASPECTS`
registry as the 6 game aspects and at the same weight, 0.00. 2 things govern using them:

- **An aspect is asked only of its own task class, and `aspects.applicability()` refuses the
  rest** — at `field.py pack`, at `field.run_field`, at `field_sweep.py` and at the 3 routes
  `eval/wholegame.py` reaches a grading instrument or a judge pack by, because the resource is
  *a graded task* and it is reached by 6 paths. It refuses a task id it cannot classify rather
  than reading it as a game, and **it answers for the deterministic instruments too**:
  `aspects.INSTRUMENTS` declares the class of `playbot`, `scene_probe` and `legacy_judge`.
  `eval/tools/scene_runner_control.py --paths` prints the routes; each has a mutant.
- **`framework_fluency` and `idiomatic` may not be ranked across stacks**, and
  `Aspect.cross_stack_bar` says so to code rather than only to a reader. `field_ranks.py`
  prints the reason and the aspect's per-stack means — alphabetically by stack, never sorted
  by value — beside every figure it produces for them. **A barred aspect is also kept out of
  every pooled figure**, since 2026-08-24: a pooled figure is a between-stack range, so
  `assert_poolable` refuses it exactly as it refuses a control (`tasks/146`).

`RUBRIC.md` holds what each scene aspect asks, what `fidelity` is read against, and why the
weight question reads **NOT ASKED** rather than "no effect" while there are 0 scene gradings.

**A scene pack carries `SCENE.md`, a hand-written stack-neutral statement of the scene, and a
game pack must not.** `field.SCENE_STATEMENTS` is the text and `field.build_pack` writes it
**raw** — every other piece of pack text goes through `neutralise`, and this one may not, because
laundering harness-authored text leaves `verify_blind.py --packs` reading a file the harness has
already cleaned. `blurb_selftest.py` is the gate: on disk for a scene field and absent for a game
one, byte-identical to `field.scene_statement`, different for the 2 scenes, free of stack tokens
under `verify_blind.py --packs`, and free of `tools/prompt_guard.py`'s criterion and threshold
vocabulary — a tier-3 opinion told what tier 2 measures is a restatement of tier 2.

**Both the packer and the spender refuse.** `build_pack` will not build a pack for a scene the
module cannot state, and `run_field` will not judge one whose `SCENE.md` is missing, undecodable
or **not this scene's statement** — a pack is built once and judged later from a directory
anything may have touched, and an empty or wrong-scene file passes a presence test while buying
a judge invocation that scores the whole field against the wrong subject. There is no escape
flag: a pack whose `SCENE.md` differs from this checkout's statement of its scene is refused,
whatever produced the difference — re-pack it.

**A scene round records `provenance.scene_statement_sha256`, and `brief_sha256` cannot stand in
for it** — the brief NAMES `SCENE.md` and does not contain it, so two rounds with the same brief
hash can have been read against two different subjects. `None` on a game round is a third value
and not an empty statement. `field._provenance` is a function rather than a literal inside
`run_field` so the record-assembling tail is reachable at all; `blurb_selftest.py` drives it
through **`run_field` with `field.subprocess` stubbed**, because a direct call to `_provenance`
proves only that it copies its argument.

**`SCENE.md` is UTF-8 by contract, written and read with the encoding named.** `write_text` and
`read_text` default to the LOCALE codec, so a packer and a judge host on different code pages
would disagree about what the statement says with every check still green — and the invalid-byte
refusal would decode instead of refusing. Each refusal state in the selftest asserts *which*
branch answered, so the undecodable case cannot pass through the mismatch branch.

**What each tier has ever DONE is a tool, not a memory.** `tier1_census.py` and `tier2_census.py`
both take `--runs-root <main checkout>/eval/runs` (required — the path is gitignored, so a
worktree's copy is empty and either would report a confident, uniform "nothing ever failed"), and
both carry `--selftest`. Tier 2 currently prints `SATURATED`: 5 of 10 groups return one value, and
`DECISIONS.md` records why that is accepted rather than repaired. **Before adding or promoting a
tier-2 criterion, run it** — the promotion column already says that scoring `layer.clears`,
`score.rewards_clears` or `stage.completes` would move every score in its group by the same amount
and separate nothing (#128).

**The within-cell noise floor has a producer, and it is a RANGE over 9 groups, not one number.**
`paired_verdicts.py --runs-root <main checkout>/eval/runs` counts, per (run, game) and per tier
set, how often a cell's two trials disagree on `passed`. Three things it refuses to smooth over,
each of which produced a published wrong number: **the tier set is part of the figure** (156 of
`wg-matrix`'s widely-quoted 436 are LLM-judge criteria at weight 0.00, and `wg-audio48`'s 232
contains none — the two were quoted side by side as one measurement); a cross-game sum is a
**count, never a rate**; and a cell whose trials did not both `complete` is **not a cell**. Its
`--selftest` pins the extraction on fixtures whose answers are written into the checks, and its
5 corpus pins reproduce the published figures — run it with `--runs-root` before quoting any of
them, because without the flag the pins are `NOT RUN`, which the output says and a reader may not
assume.

**Whether the deterministic tiers may rank stacks is `discrimination.py`'s `THE RANKING TEST`,
not a judgement.** It compares only `completed`, **gate-green** cells — tier 1 gates, so a
submission that does not build has no rank position — and requires the between-stack range to
beat the within-cell floor by at least `1/N`, the smallest gap a pass count over `N` criteria can
represent. `--selftest` proves it can say `CROSSES`, including on the exactly-one-criterion
boundary. `NOT ASKED` (fewer than two gate-green stacks) is a third value and is not a pass.

**Because tier 1 GATES, a bound calibrated on one task class does not cost the other a
fraction of a score — it stops a correct submission being scored at all.** So every tier-1
criterion declares which population its bound came from, in `static.TIER1_BOUND_POPULATION`,
and `static.assert_tier1_bounds_declared()` fails a criterion added without an answer. **0** bounds
are class-dependent today — `python3 judge/ink_window_control.py` prints the whole tally and pins
it — and `task_class` keeps its slot in the closed list for the next one, since declaring it
without a per-class table fails.

`render.nonempty` is a **floor of 0.001 and no ceiling**, plus a refusal of a frame set in which
every frame is a single colour — both the same in either class, both properties every starter
shares. **`mean_ink` does not measure how much was drawn**: it is departure from **frame 0's**
modal colour, so a full screen reads 0.0 and a gradient reads near 1.0, and no bound on it can
stand for a blank render. `RUBRIC.md` holds the rule, both derivation tables and what the retired
ceiling did.

**Before changing either half, run the producer** — `python3 judge/ink_window_control.py
--runs-root <main checkout>/eval/runs` — which verifies both tables on real pixels, prints what
the bounds have ever done over the stored corpus, and re-grades every firing under today's rule.

**Tier 1 gates; it does not score.** `overall = tier2`, and a tier-1 failure is reported as
`gate: FAIL` with the failing criterion ids rather than deducted — the derivation, the two
sweeps behind it and what would re-open it are in `RUBRIC.md`. Two consequences you will meet
before you meet the rubric: a record written before 2026-08-23 has no `gate` and no
`scoring_regime` and its `overall` is on the old 0.31/0.69 scale, so **never average across the
boundary**; and `regrade_wholegame.py` refuses to rewrite a pre-gate record without
`--accept-regime-change`, because converting one silently would leave a run directory half in
each regime with nothing on disk saying which.

**The audio criteria need `ffmpeg` and `ffprobe` on the grading machine.** Without them every
audio criterion fails with that as the recorded reason — fail-closed, never skipped, because
`total=0 passed=0` is indistinguishable from correct failure.

**`audio.*` applies only to a task that asked for sound.** `evaluate(..., audio=False)` and
`wholegame.py evaluate --no-audio` exist for re-scoring the runs that predate it; applying the
criteria retroactively would measure the task change rather than the work.

**Every audio criterion has a mutant.** `audio_selftest.py` runs 37 expectations: five criteria
plus `audio.triggered` against a healthy fixture, then against nine mutants each of which must turn
one of them red. Run it before believing an audio score. A criterion that cannot fail is worse than
absent, because it looks like success.

**`capability.py` is captured, not scored, and it is measured from OUTSIDE the submission.** Nine
fields — capture geometry, frame count, the wall/CPU/peak-RSS cost of `just film`, and the headless
probe's throughput and start-up — same names, same units, all four arms. Nothing in the submission
is ever asked to report a number about itself, because **a field the subject reports is a field
that can go missing in a stack-correlated way** (#62, #72, #77); a harness-side mechanism cannot.
`no_stack_correlated_gap()` enforces that and `capability_selftest.py` carries its mutant *and* its
variant. **Do not add a frametime or fps field** — the TS arm films on SwiftShader while the other
three film on the GPU, so it would rank the backend; `DECLINED` in that module says what would have
to change first. Adding any of this to the score is a regime boundary and needs its own task.

## What a stored command record holds: two streams, sampled apart

Every command tier 1 runs — `just check`, `verify`, `lint`, `test`, `film` — is stored by
`static.Cmd.to_dict` with **`stdout` and `stderr` as separate fields**, each sampled on its own
budget: the first `STREAM_HEAD_CHARS` characters and the last `STREAM_TAIL_CHARS`, the middle
replaced by a marker naming how many characters and lines went, and the full length of each stream
recorded beside it as `stdout_chars` / `stderr_chars`. The harness's own words — a timeout, a
binary that could not be spawned — go in `note`, never into a stream the command did not write.

**There is exactly one copy of that policy and it is not here.** `STREAM_HEAD_CHARS`,
`STREAM_TAIL_CHARS`, `_sample_stream`, `capture_fields`, `stored_stdout` and `stored_output` are
defined in **`runner.py`** and imported by this module, because the spec-change harness stores
command output too and had the identical defect (#114). Two truncation policies in one repository
is how #100 recurred; `runner_capture_selftest.py` asserts each of those names is still defined in
`runner.py` rather than re-implemented here.

It used to be one `tail` field holding the last 4000 characters of `stdout + stderr`. **A
truncation policy is a sampling policy**, and that one sampled *whichever stream the tool happened
to write second*: 15 of 16 green Rust `verify` records kept no trace of the recipe's own
`✅ verify passed`, because `cargo-nextest` fills stderr (#100). **Raising a cap is not a fix for
that class of defect** — it moves the boundary and leaves in place the rule that stdout is
sacrificed first, still correlated with a stack by a property nobody chose.

Reading stored records: `static.stored_stdout()` returns **None** for anything written before the
repair, because a line missing from a merged buffer is not evidence the command never printed it —
those records are unmeasurable, not empty. `static.stored_output()` reads either shape. In memory
`Cmd.tail` is unchanged and still means stdout-then-stderr, because the test-count and coverage
parsers read it; only the stored shape moved. Stored records cannot be repaired — the discarded
stdout was never written down — so the corpus is mixed and any sweep over it must partition on
which shape it is reading.

`judge/capture_selftest.py` pins both directions (a flood on either stream keeps the other) and
carries the mutant that proves those checks can fail. `runner_capture_selftest.py` does the same
through the other harness's entry point. Both must stay green.

## The judge is diagnostic only

It contributes **zero** to `overall` — not a token weight. Two independent reasons, either
sufficient:

1. **It cannot reorder anything.** Bounded contribution 0.10 against a tightest adjacent gap of
   0.0622 on tiers 1+2 alone. Holds regardless of noise.
2. **It is noisiest exactly where it would matter.** Score spread 0.308 and instability up to 0.462
   on a contested submission, against 0.000 on an uncontested one. Holds regardless of weight.

Its per-criterion verdicts **are** reported and are genuinely useful — it catches surviving
placeholders, tautological tests, and pixel-identical frames that no deterministic tier sees.
Anywhere it appears in a report, label it as diagnostic so no reader can mistake it for something
that fed the ranking.

## Validating the judge

**Verdict stability is a property of the artifact, not of the rubric.** Criteria agree when the
answer is obvious and diverge when it is borderline — which is exactly when you need them.

Consequences, all learned the expensive way:

- **Validating on clear-cut fixtures systematically overstates reliability.** A submission scoring
  13/13 unanimously proves nothing about a contested criterion. So does one scoring 0/13 — that is
  a ceiling at the floor.
- **Validate on borderline artifacts**, and report per-artifact stability rather than a global
  figure. A single instability number for "the judge" is not meaningful.
- `instability` measures forward-vs-reverse disagreement **within** a run. Run-to-run variance on
  identical input is a separate and equally large effect. Report both.
- **When a binary criterion flips run to run, read the reasons before blaming the model.** Several
  near-identical reasons with different verdicts is the signature of an unstated threshold. Rewrite
  the question — though note that rewriting the three worst criteria here did not fix them.
- A criterion every run answers identically **because the question never arose** has not been
  tested. Check that a criterion is exercised, not just that it is stable.

## Blinding

`verify_blind.py` scans for the rubric's canary GUID, its reachability from every ancestor
directory, and every criterion id the rubric defines.

- **Run it after *any* starter edit**, not just before a run. A criterion id once reached the Unity
  starter through a comment written while documenting an unrelated floating-point finding — not
  through the prompt, template or `AGENTS.md`, which are the three places the design watched.
- Run it **unpiped**. A `verify_blind.py | tail` "pass" is `tail`'s exit status.
- **Point it at a copy of the starter OUTSIDE this repository**, laid out the way a trial tree is.
  Check 2 asks whether the rubric is reachable from an ancestor, and `eval/starters/<stack>` has
  `eval/judge/RUBRIC.md` up its own path — so run in place it is red for all four stacks, on a
  condition that says nothing about the edit (measured 2026-08-23, task 67). That verdict is
  *correct about the path it was given* and useless about the question, which is rule 12: the
  address is an input to the check. Copy the four starters to a directory outside the repo and
  pass those. The error text says "see `--work-root`" — that flag is `wholegame.py`'s, not this
  tool's, and this tool takes bare paths.
- Never fix a leak mid-run. Changing a starter partway through gives later trials a different
  starter than earlier ones — a real within-run inconsistency traded for a usually-minor leak.
- **`verify_blind.py` scans the trial tree, not the judge's brief.** An aspect's own `question`,
  `evidence_rule` and `notes` are handed straight to the judge and nothing above reads them.
  `aspects_selftest.py` is that check: no stack name, **no arm count** — "three of the four" hands
  over the partition as surely as "Bevy" does — and `fun`/`fun_frames` briefed byte-identically,
  because a control whose briefing differs from its treatment's is not a control. It must stay
  green, and it carries a mutant per check plus a variant that counts the arms without naming one.

## Anonymisation

`anonymise.py` strips identifying structure before judging.

**What `neutralise` matches is a PROPERTY, and `_STACK_NAMES` is a list of names, not of
spellings.** A name matches wherever it forms a whole identifier segment — segments split on
`_`, digit boundaries and camel/Pascal boundaries — in any case convention, in any position
inside an identifier or a path. One entry therefore covers `cargo`, `Cargo`, `CARGO`,
`CARGO_MANIFEST_DIR` and `cargoRoot`, and a multi-segment entry covers `TypeScript`,
`MonoBehaviour`, `GDScript` and `node_modules`. **Never repair a leak by adding the spelling you
just saw** — that is the third time this defect was fixed at the instance (#32, #83, #131).

Two consequences to know before touching it:

- **A case-insensitive substring search is a worse bug than the leak it fixes.** It rewrites
  `immunity`, `Vec3.UnitY`, `main.tscn`, `bestScore` and `is_three_dimensional`. `three` and
  `node` are excluded from the vocabulary outright, as literal patterns, because no segmentation
  saves an English numeral or the scene-tree noun.
- **`find_stack_names()` is the audit, and it is deliberately the same code path as the
  rewrite.** A detector with its own vocabulary agrees with the rewriter by construction and
  measures nothing. What makes it informative is running it over **real stored pack text**, which
  is what `anonymise_selftest.py` does: 128 lines the old rewriter left carrying a stack name,
  400 lines where a stack name sits inside an innocent word and which must come out
  byte-identical, a mutant per name, and idempotence. It must stay green.

**The extensions a file MENTIONS are blinded in `field.py`, not here.** `neutralise` runs for
every aspect and `idiomatic` cannot be asked whether Rust reads like Rust with `.rs` taken out
of it, so the extension rewrite lives in `field.build_pack`'s `blind_language` branch —
`field.BLIND_EXT` and `field.blind_extensions()`. Before that split existed, renaming each file
to `.src` hid the extension of the file the judge OPENS and none of the ones it READS (**#137**):
2,083 arm-naming extension tokens across all 84 stored packs after `neutralise`, 0 after.

`judge/blind_ext_selftest.py` pins it — a mutant, a variant proving the non-blind pack is
byte-identical to `neutralise` alone, 12 collision inputs the rewrite must not touch, and a
vocabulary audit read from the four starters. **It must stay green**, and pass it
`--runs-root <main checkout>/eval/runs` to re-sweep the stored packs; without that flag a
worktree's gitignored, empty `eval/runs` makes the sweep silently skip. Four things to know
before touching it:

- **`CHANGED.txt` is pack content and was the densest leak in it (#137).** `field.build_pack`
  writes it from `git diff --stat`, so the harness itself handed every blind pack a list of the
  real authored paths with their true suffixes — 80 `.cs`, 78 `.gd`, 60 `.meta`, 43 `.ts`, 43
  `.rs` in the 8 stored `architecture` packs, and per pack it is a clean partition: **each one
  names exactly one arm's suffixes and no other arm's.** In a whole unblinded field it is 345 of
  the 667 extension tokens against 322 in all 199 code files together. **When you ask what a pack
  leaks, ask what the packer ADDED, not only what the submission carried** — every gate this
  project owns is pointed at the subject.
- **The vocabulary has two halves and neither can be derived from the other.** What is
  arm-exclusive comes from the four starters and is audited mechanically by the selftest; what
  can also be a *member name* comes only from the corpus. `.lock` is 108 `Mutex::lock()` calls
  and 0 filenames, `.anim` is 128 member accesses and 0 filenames — both are excluded by name in
  `field._NOT_AN_EXTENSION` with the count that decided it.
- **Directory names are the same defect through the sibling property, and the total that
  states it is the wrong shape.** 1,561 arm-naming tokens survived `blind_extensions` in the 8
  stored `architecture` packs, and partitioning them is what decided the repair: **182 in
  `CHANGED.txt`, every one a real path segment; 1,379 in code content, of which only 149 are
  paths.** 1,129 of the 1,148 `public` hits are the C# access modifier and `Assets` is a Bevy
  type in Rust packs. **A single total over two channels with a 0% and an 89% collision rate
  describes neither** (rule 4, one level below where it usually fires). `CHANGED.txt` is now
  rebuilt from the pack's own manifest, which repairs the extension half (#137) and the
  directory half together; the code-content half is **declined on measurement, not on
  feasibility** — four candidate rewrites were tried and every one hands the judge the arm
  partition. `python3 judge/blind_dir_selftest.py --runs-root <main>/eval/runs` re-derives it.
  Task 103.
- **`field.py pack` read the aspect's `sees` and not its `blind_language` (#138)**, so a pack built
  the way the module docstring tells you to build one was not blinded at all: 199 of the 207
  evidence files in a real `wg-g4c` `architecture` field kept a language-naming filename and the
  content carried 667 arm-naming extension tokens, against 0 and 11 after. `field_sweep.py`
  passed both at all three of its call sites, so **no stored round is affected — which is
  exactly why nothing noticed for as long as the CLI has existed.** Fixed 2026-08-23 and driven
  by the selftest as a subprocess. **When an aspect gains a property, grep for every reader of
  its siblings**; one call site reading half an object is invisible to every test that calls
  the function directly.

### `CHANGED.txt` under `blind_language` is REBUILT, not rewritten

`field.blind_changed_txt` maps every `git diff --stat` row through the pack's own
origin → label manifest, so a blind `CHANGED.txt` reads ` sim/01.src | 42 ++--`. There is **no
directory vocabulary anywhere in the repair**, which is the point: a vocabulary can fire on a
word that is not a path and can miss a directory nobody listed, and the manifest can do neither.
`judge/blind_dir_selftest.py` pins it with a mutant, a variant, seven `git diff --stat` shapes and a
fail-closed case, and takes `--runs-root <main checkout>/eval/runs` for the per-segment re-sweep.
Three properties to preserve if you touch it:

- **A row must name a file that is on disk in that pack.** The mapping checks each candidate
  label against what the copy loop actually wrote rather than re-deriving the `.src` rename — a
  second copy of that rule is how #100 recurred. The judge's brief already tells it to cite pack
  labels; before this, the one file that named the real paths was the one the harness added.
- **Unmapped rows are omitted and NOT counted to the judge.** 228 of 424 rows in `wg-g4c` name
  files outside the pack. The count of them runs 53 and 43 for the two Unity submissions against
  15 and 15 for the two TypeScript ones, so printing it — or printing the `git diff --stat` summary tail
  — hands over a partition of the field (#62). The counts go in `evidence_counts` as
  `changed_rows` / `changed_rows_dropped`, beside the pack, never in it.
- **Zero mapped rows is a REFUSAL.** A manifest whose origins stop spelling the diff's paths
  still parses and still maps — it just maps nothing, and an empty `CHANGED.txt` reads as a
  submission that changed nothing (rule 7, rule 12).

**The code-content half is deliberately not repaired, and four candidate rewrites were measured
before that was settled.** The census is part 6 of `blind_dir_selftest.py` and re-runs with
`--runs-root`, so the decision has a producer rather than a remembered table:

| candidate | godot | rust | ts | unity | density ratio | isolates an arm |
|---|---|---|---|---|---|---|
| arm-exclusive vocabulary from `git ls-files` | 0 | 43 | 265 | 228 | infinite | **6 of 9 fields** |
| every starter directory, shared included | 271 | 102 | 830 | 273 | 8.9x | **9 of 9** |
| vocabulary-free: every path component | 831 | 927 | 1701 | 668 | 2.8x | **9 of 9** |
| the same, minus the four bucket labels | 428 | 690 | 1021 | 668 | 2.1x | **9 of 9** |

**Read the last column, not the ratio.** *Isolates* means a strict threshold on ONE pack's
redaction count separates a whole arm from the other six packs — measured per field over the 9
independent stored fields, against **7.1%** by chance. A per-arm total is an aggregate no judge
ever sees; eight packs and how redacted each looks is what it does see. Driving the aggregate
from infinite to 2.1x — which satisfies the reversal condition as it was first written — moved
the leak from Godot's zero to TypeScript's extreme and made the per-field figure **worse**.

Two things a reader will otherwise re-derive. **The published table excludes `bin`**: it is the
only arm-exclusive segment firing in all four arms, and it does so through `#!/usr/bin/env` —
19 of its 26 hits are shebang lines. Including it reads 9/50/265/238, and the 9 in Godot is a
redaction that removes nothing. The `CHANGED.txt` detector above keeps `bin`, correctly, because
every row of a `git diff` summary *is* a path. And **`wg-g4c-capgate/uncapped` is not an
independent field**: it
shares 176 of 199 pack file blobs with `wg-g4c-2026-08-21T02-26-46`, so the census collapses
fields on shared content rather than on a run name (rule 9). See `tasks/103`.

Three more things it has got wrong before:

- **Check `CODE_EXT` covers the stack's extensions.** A missing extension produced an empty file
  pack that the judge scored confidently at 0.08.
- **A criterion cannot ask about something anonymisation destroys.** `code.navigable` asked about
  file layout, which is exactly what the anonymiser removes; every run argued with the
  anonymisation instead of answering.
- **A pack is a NUMBERING, not a set of files.** Labels are `bucket/NN.ext` counted within the
  bucket, so any change to the picked set — a starter edit, an exclusion, a new extension, a
  directory added to `SKIP_DIRS` — shifts the numbering and would strand the previous pass's
  files under labels the new manifest does not list. `build_pack` clears its destination for that
  reason; `wg-g4c` accumulated 23 stale files in 222 across nine passes before it did (#95).

**Verify a stored pack by opening it, not by reading what `anonymise` said about its input.**

```
python3 judge/field.py packcheck --run runs/<run>          # unpiped: exit 1 means not clean
```

`pack_completeness` reads `files_dropped_for_length`, which #69 made 0 by construction — a gate
on the function's *input*. `pack_matches_manifest` reads the directory the judge will be handed
and asserts set equality per submission; `field.build_pack` refuses a code field that fails it,
and `--allow-truncated` does not excuse it. A pack with no manifest is **unmeasurable, not
clean**. `judge/pack_selftest.py` pins both halves and must stay green.

`evaluate.py` returns `usable: false` and excludes a tier with weight renormalisation rather than
scoring an empty pack.

### What the judge is TOLD about the pack is an instrument, and it needs a gate of its own

**Every gate above reads the pack. None read the brief** — and that is how a sentence describing a
mechanism deleted on 2026-08-22 went on being handed to every code judge. `EVIDENCE_BLURB["code"]`
said the pack "may not contain every file the author wrote" while `files_dropped_for_length` was
0 by construction, so the harness invited each judge to discount an absence it was seeing in full.
All 10 stored code rounds that recorded a `brief_sha256` rebuild byte-identically to that text
(`eval/RUNS.md`); the other 26 stored no hash and are unassessable.

Four things to know before touching any of it:

- **The subject is the RESOURCE — judge-facing text that makes a claim about the packer — not the
  one constant that was wrong.** It is two objects today: `EVIDENCE_BLURB`, rendered into
  `BRIEF.md`, and the sampling skill written into every pack. A third is covered by being added to
  `blurb_selftest.judge_facing_texts()`.
- **A claim about the pack is a FUNCTION of the pack.** `field.COMPLETENESS_NOTE` holds both
  states and `build_pack`/`run_field` select on `knowingly_truncated`. Keeping one wording is what
  produced the defect: **a claim with only one possible value is not a claim and nothing can check
  it.** The skill had the same defect pointing the other way — it asserted completeness
  unconditionally, so a field built on purpose with `--allow-truncated` got a skill and a brief
  that contradicted each other.
- **A pack built before `knowingly_truncated` was recorded is refused, not assumed complete.**
  `run_field` returns `usable: false` and asks for a re-pack, because a missing key read as falsy
  would assert completeness about a pack nothing on disk describes — #62's direction (rule 7).
- **`PACK_PATH_EXAMPLE` is keyed on `blind_language` and must stay suffix-free when it is off.**
  Only `architecture` blinds extensions; under `idiomatic` the labels keep their real suffixes, and
  one brief serves eight submissions from four stacks, so any real suffix in an example names an
  arm. The pre-repair brief showed `` `sim/03.src` `` to both.

```
python3 judge/blurb_selftest.py          # unpiped: exit 1 means a claim has drifted
python3 judge/blurb_selftest.py --stored-rounds <main checkout>/eval/runs
python3 judge/stored_rounds_mutants.py   # the red half of the census arm, ~5s, no corpus
```

It builds real packs in both completeness states, both blinding modes and both task classes,
and must stay green. Its own docstring is the register of what it checks; the coverage is
**7 mutants** — the 2026-08-22 sentence restored, a blurb naming an artifact no pack holds, a
real suffix in the non-blind pack-path example, the two completeness notes collapsed into one, a
constant `claude -p` prompt, a stack token in `SCENE.md`, the withheld claim in `SCENE.md` —
**2 variants** no mutant can manufacture (a field whose *stored* drop count is non-zero; a
statement naming an engine driven through the real packer) and **2 fail-closed cases**, a
deleted completeness claim and a scene the packer cannot state. **The claims it reads are not
all about the packer** — `SCENE.md` claims what the task was, and the frames blurb claims who is
watching — so each is checked against what it is a function of.

**`--stored-rounds` is the producer for every figure in `eval/RUNS.md`'s section on this, and for
the POPULATION beside each one** — a population with no producer goes stale exactly as a quantity
with no producer does. It prints the directory and the recorded pack state of every code round it
counts, hashed and unassessable alike, and every hashed row carries `n = same + moved +
unbuildable`, so a record the headline counts cannot go missing between two verdicts.

It reads a gitignored directory, so `blurb_selftest.py` builds a fixture tree whose answer is
written out as literals and asserts the census against it. `judge/stored_rounds_mutants.py` is the
red half — **7 mutants**, plus `--variant-control`, which measures that the variant catches what
no mutant does rather than asserting it.

**Where the caution-vocabulary check is aimed was chosen on the false-positive count, not on
which address sounded more general** (rule 12, and the census-trigger derivation in
`DECISIONS.md`). Aimed at the rendered `BRIEF.md`/`SKILL.md` it fires on the skill's closing
paragraph, which narrates the removed cap in the past tense — 3 hits, 0 of them defects. Aimed at
the **claims themselves**, which describe the pack in the present tense, it is 0 false positives
on the live corpus and 2 true positives on the pre-repair one.

**Re-packing a stored run is `repack.py`, and it is not "run the packer again".** The
starter-identical filter compares against the starter as it is NOW, so a starter that moved since
the run was packed makes template code look authored (#77) — the opposite failure to the one you
are repairing. `repack.py` computes the exclusion set as *(rebuilt origins) minus (stored
manifest) minus (files dropped for length, asserted 0)*, then requires each excluded file to be
byte-identical to its blob in the work tree's `starter baseline` commit, and **refuses** when that
corroboration is unavailable — no manifest, no work tree, a non-zero length-drop count, or a
disagreement between the two methods. A refused submission is **marked, not re-packed**. It reads
the starter path out of `report.json` rather than deriving one, because a derived path resolves
inside whatever checkout the script is running from (rule 12).

**Every judge round stored before a re-pack read a field that no longer exists.** Say so wherever
the run's results are reported; no gate can reconstruct what a stored round was shown.

## Changing weights or the rubric

Update `RUBRIC.md` **and** the grading table in `README.md`. Then **re-grade offline** — re-running
a stochastic judge to apply a weight change silently changes the verdicts too, so you would be
measuring two things at once.

## Dead code in a judge module is a conclusion waiting to rest on it

`PlatformerBot._approach` was defined in five of the six commits that touched
`bot_platformer.py` and called from none of them. Two conclusions in the archive rest on repairs
made to it, and one of them — the re-grade that falsified the pit hypothesis for #82 by returning
a byte-identical 0.793 — could not have returned anything else, because the gap-crossing code the
repair touched was reachable only from inside `_approach` (#136).

> **A second copy of a loop and an unreachable copy of a loop are indistinguishable by a score
> diff.** Before reading an unchanged result as evidence about a hypothesis, establish that the
> code you changed executed.

`eval/tools/dead_private_control.py` is the offline check, and it is a **gate**: run it before
interpreting any re-grade, and after touching a bot.

```bash
python3 eval/tools/dead_private_control.py             # 18 measurements; 0 green · 1 FAILED · 3 NOT CHECKED
python3 eval/tools/dead_private_control.py --census    # just name what is unreachable in eval/judge/
```

Three things worth knowing before you act on it, all of them measured rather than assumed and all
pinned by the control's own directions:

- **It is reachability, not "is this name mentioned".** #136's per-method census could not see a
  cluster dead as a whole, and there was one: `ArenaBot._corners`, `_far_corner` and
  `_turn_corner`, where the last was the only caller of the other two. Shallow named one of the
  three, reachability all three. Direction 3 pins both modes against that cluster as it stood at
  `03cdb90`.
- **A string mention counts as a use; a comment does not.** The first keeps a
  `getattr(self, "_step_once")` dispatch from going dead spuriously. The second is what makes the
  check fire at all — `_approach` appeared in every tree that defined it as its own `def` line and
  as two *comments*.
- **It gets two things wrong and says so.** A name assembled at runtime
  (`getattr(self, "_han" + suffix)`) reads dead — noise, fail-closed, and there is no such site in
  `eval/judge/` today. A method named only in another method's docstring reads live — a real miss,
  and the price of the string rule. Both are variant rows in direction 4, so widening the string
  handling cannot quietly lose either.

**The tree is at 0 unreachable private methods out of 118 and that is the gate's whole content.**
If you delete a method to satisfy it, the measurement in its docstring is evidence and has to land
somewhere first: `_turn_corner`'s went into `_chase`'s docstring, beside the two discarded designs
already recorded there. **Do not add a name allowlist** — an exemption list is a fail-open channel
(AGENTS.md rule 7), and the one hit this check has had was resolved by deletion instead.
