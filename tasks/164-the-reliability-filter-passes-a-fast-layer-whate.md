---
id: 164
title: 'The reliability filter passes a fast layer whatever the estimator returned: its agreement slack is a floor in RATIO units'
status: in_testing
priority: 2
refs: eval/judge/scene_probe.py,eval/judge/scene_mutants.py,eval/RUNS.md,tasks/162
done_when: the agreement test refuses a layer whose per-pair ratios agree only because the slack floor exceeds the signal - a slack derived from the estimator quantisation the pair actually has, not a constant in ratio units - with the FIXTURE census before and after so nothing that used to be readable silently stops being; a variant built from a scene whose near layer crosses more than one span between captured frames is red before and green after; whether an aliased band should be unreadable or whether 12 frames is too few for this scene is decided and written in eval/SCENES.md; and eval/runs/wg-scene-s1ts-2026-08-25 is re-graded and the layers.image_parallax verdict recorded either way
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/46
established_by: 'PR #46, 2 review rounds, 4 findings acted on. Variant RED before the repair at 1 unmet, GREEN after at 23 mutants over 15 criteria, 10 variants, 0 unmet; fixture census unchanged in fail and unscored; new offline --reliability-selftest at 7 records and 3 mutants; read-only re-grade of wg-scene-s1ts-2026-08-25 moves layers.image_parallax to scored=False and the trial 6 of 7 to 6 of 6. Round 2 is UNREVIEWED, review allowance spent; both CI checks green at 921aca1. A finding is owed and unnumbered.'
---

ParallaxScene._reliable keeps a layer when at least 80% of its per-pair shift-to-offset ratios sit within max(|median| * 0.15, 0.15) of the median. The second term is a floor in ratio units and it does not scale with how fast the layer moves, so on a fast layer it swallows the whole search window. Measured on the one stored scene submission after the tasks/162 repair: the road band has median ratio 0.053 and slack 0.150, which is 2.8x the median, so every one of its 8 usable pairs agrees and the layer is called readable - while its measured shifts run from -73px to +67px and it crosses 1.6-2.25 spans between two captured frames, which means the shift is aliased against its own tile and carries no rate at all. That promotion is what let layers.image_parallax establish itself on 3 bands and score the submission FALSE, where the honest verdict is scored=False; eval/RUNS.md records both and says not to quote the FAIL. The two bands it was compared against, clouds and sky, move 25 and 8 world units per captured pair and measured 0px on 11 of 11 and 9 of 11 pairs, so a sub-pixel band and a stationary one are the same reading here. Note the shifts are near-identical ACROSS bands at the same pair (-46,-46,-46,-45 at pair 1; -66,-66,-66,-43 at pair 5), which is the estimator locking onto one whole-frame feature rather than each band - the instrument error DECISIONS.md records, at a rate the fixtures never showed.

## note 2026-08-27

## note 2026-08-27 (orchestrator) — a second agent is reading eval/runs concurrently: READ it, do not WRITE it

`tasks/158` is in flight as of now and its `done_when` runs `eval/judge/tier2_census.py` against
the main checkout's `eval/runs`. Yours re-grades `eval/runs/wg-scene-s1ts-2026-08-25`. Both are
fine as long as both stay **read-only against that tree**, which is the only piece of state here
that is not branchable — your worktree gives you an isolated checkout of the code and does *not*
isolate a stored run you write into.

**So: compute the re-grade and record the verdict in this ticket and in `eval/RUNS.md`. Do not
store a new judge round under `eval/runs/`.** If your `done_when` turns out to be unreachable
without writing there, that is the unanticipated decision this ticket did not cover — say so here
and stop that one clause, rather than writing into the tree while another agent is counting it.
Everything else in the ticket proceeds regardless.

**One thing to carry from `tasks/163`, which merged the same day.** Its window was calibrated per
task class and the temptation the ticket named was to widen a bound until the one stored
submission passed. Yours has the same shape pointed the other way: the honest outcome may be that
the road band is **unreadable**, not that the slack needs a better constant. `eval/RUNS.md`
already says not to quote that FAIL. A repair that makes the stored scene readable is not
self-evidently the right one — say which population your new slack is calibrated on, the way
`static.TIER1_BOUND_POPULATION` now does for the ink window.

## note 2026-08-27

## What landed — 2026-08-27

PR #46, `task-164-reliability-slack-pixels`. `eval/RUNS.md` is the authority for the run
figures; `DECISIONS.md` and `eval/SCENES.md` for the decision.

### The defect was two, not one, and the second is what the decision clause is about

`ParallaxScene._reliable` kept a layer when 80% of its per-pair shift-to-offset ratios sat within
`max(abs(median) * 0.15, 0.15)` of the median.

1. **The floor was in RATIO units**, so in pixels it is `0.15 * abs(d_offset)` and grows without
   bound as a submission reports offsets in finer units. On the road band that is **+/-60 to
   +/-81 px inside a +/-89 px search window** — every answer the estimator could return agreed
   with every other, and it was called readable on **8 of 8** pairs while its usable shifts ran
   **-73px to +3px**.
2. **An aliased band can agree with itself PERFECTLY**, which no slack fixes at any value. The
   road crosses **1.66–2.25 spans between captures** on every pair, so what the frames show is a
   residue of its repeat length. A band that crosses its span an exact whole number of times
   reads **0px on 11 of 11 pairs at confidence 0.83–0.92**.

So the repair is 2 constants and they answer different questions:

- `K_PIXEL_FLOOR = 1.5` — agreement moves into PIXELS. The proportional term is **unchanged**:
  a ratio slack of `abs(median) * K_TOLERANCE` is exactly `abs(predicted) * K_TOLERANCE` px.
- `NYQUIST_SHARE = 0.5` — a pair whose layer moves half its own span **or more** is refused
  before agreement is asked. At exactly half a span the 2 candidates are equally far from zero,
  so neither is the answer.

### Where the floor comes from, since the orchestrator asked which population

**Not a population — the estimator's own quantisation.** `best_shift` answers in whole pixels, so
two pairs of one layer can report displacements a whole pixel apart from rounding alone, and the
median ratio the prediction is built from is itself one of those rounded answers. The 6
s1_parallax fixtures (24 layer rows, 264 pairs) are the no-regression check, not the calibration:
setting aside the 8 pairs that are the estimator's documented miss, the worst residual is 0.78px,
and **exactly 1.00px** on the constant-speed variant where a true 13.33px shift is answered 13 on
7 pairs and 14 on 4. The floor binds only where `abs(predicted) < 10px` and no fixture pair is
that slow, so it moves no fixture verdict either way.

### The decision (`eval/SCENES.md`, `DECISIONS.md`)

**The band is unreadable; the 12-frame capture contract does not move.** `span` is the
submission's own choice, so no capture rate is safe from it: this road band needs more than 50
frames, and one repeating every 10 world units needs thousands. It has to be a PRECONDITION and
not a widened tolerance, because an aliased band and a background reported as moving and drawn
stationary are the same reading — only the reported offset separates them, and the second is the
one thing `layers.image_parallax` exists to catch.

### The control, both directions

- **Variant first, against the unrepaired probe**, and it was RED: `13 mutants over 8 criteria,
  6 variants, 1 expectation(s) unmet`, `layers.image_parallax` failing a correct scene with
  `depth 1 shifted 0px/frame, depth 2 shifted 40px/frame`. After: `23 mutants over 15 criteria,
  10 variants, 0 expectation(s) unmet`, exit 0.
- **FIXTURE census before and after**: s1_parallax 19 subjects -> 20, and every criterion's
  `fail` and `unsc` column unchanged. s2_glass untouched.
- **`scene_mutants.py --reliability-selftest`** (new, offline, in `controls.yml`): 7 hand-written
  layer records with verdicts stated before it runs, 3 mutants of the shipped file. The slack
  half has no fixture that can reach it — an aliased fixture is refused by the precondition
  whatever the slack does — so this is the only pin it has.

### The re-grade — READ-ONLY, nothing written into `eval/runs`

`layers.image_parallax` FAIL scored -> **`scored=False`**; the trial moves 6 of 7 = 0.857 to
**6 of 6 = 1.000**. Established from both sides: the unrepaired probe on the same extracted tree
returns FAIL at 6/7, evidence `depth 0 shifted 26px/frame, depth 20 shifted 0px/frame, depth 60
shifted 0px/frame`. 2 of 7 bands readable, below `MIN_LAYERS`. Per-band spans-per-pair: road
1.66–2.25, verge 0.76–0.99, grove 0.46–0.48, ridge 0.24–0.26, range 0.10, clouds 0.02–0.03,
sky 0.00.

Re-grading needs the submission extracted, `pnpm install --frozen-lockfile` and
`pnpm exec playwright install chromium`; ~20s once warm.

### What the next agent must not re-derive

- **The estimator is locking onto one whole-frame feature, not onto each band.** At frame pair 4
  all 5 of range, ridge, grove, verge and road answer **-9px**; at pairs 1, 3, 5 and 10 four of
  them answer -46, -19, -66 and +8. Five bands at five declared depths did not move the same
  distance. That is a bigger instrument problem than this ticket, and it is why only 2 bands were
  readable even before aliasing was considered — grove, ridge and range fail `MIN_PAIRS_PER_LAYER`
  on CONFIDENCE, not on resolvability.
- **A sub-pixel band and a stationary one are still the same reading**, deliberately. Clouds and
  sky read 0px on 11 of 11 and 9 of 11 pairs and are `readable` with `median_shift = 0`. Excluding
  a zero median would be a fail-open channel round the criterion (rule 7). Not in this
  `done_when`; untouched; changes nothing on this submission because the criterion is unscored on
  the layer count anyway.
- **The ratio-unit floor was wrong in BOTH directions.** It admitted a band drawn wherever the
  window allowed AND refused a correct slow band whose only spread is whole-pixel rounding. The
  selftest's first mutant moves both records.
- **`ci_minutes.py --selftest` is not in either git-hook tier.** Adding a `controls.yml` step
  turns it red and `run-gates.sh pre-push` stays green. Run it by hand after touching a workflow.

### A finding is owed and I did not number it

The work skill forbids allocating one. The claim, the measurement and the control are above and
in `eval/RUNS.md`; the orchestrator should number it at merge.

### The review, and round 2 is UNREVIEWED

2 rounds, 4 findings, all acted on: the `controls.yml` step count (a real red gate — see above),
the half-span boundary stated one case wide, a `DECISIONS.md` paragraph narrating its own
deliberation, and — round 2 — the evidence naming a mechanism it had not established, where a
pair dropped for a missing `span` was described as having moved half a span. That last one is
fixed and pinned by a third mutant that moves **no verdict at all, only the note**.

**Round 2's fixes were never reviewed.** CodeRabbit's check reports `pass — Review rate limited`,
and its summary comment says *"You've used all 10 included reviews currently available"*. Three
`@coderabbitai review` requests over ~40 minutes each came back to the same notice, and
`pr_review_state.py` answers `LANDED_COMMENT ... notice=Review limit reached` at the head — which
is the false "finished with nothing to say" `tasks/162` recorded. **Not a clean round.** Both CI
checks are green at `921aca1`: `gates` 1m49s, `controls` 14m15s.
