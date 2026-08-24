---
id: 134
title: 'Build the scene probe: the tier-2 criteria for s1_parallax and s2_glass, each with a mutant and a variant'
status: done
priority: 1
refs: 'eval/SCENES.md, eval/judge/bot_mutants.py, eval/judge/RUBRIC.md, tasks/133, #45, #46, #92, #123'
done_when: Every criterion in eval/SCENES.md is implemented, binary, and reported per-criterion; each has a mutant that dies and a variant that probes an input the check could mishandle, both run by a single command in CI; the seed pair is scored as ONE criterion; the criteria that can be are measured from BOTH telemetry and pixels with the two compared; and a census reports how many submissions each criterion separated, with any criterion that separated none named as an open question rather than shipped quietly. BLOCKED BEHIND 133.
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/20
established_by: 'PR #20 squash-merged. Verified independently: scene_mutants reports 20 mutants over 15 criteria, 8 variants, 0 expectations unmet; the water-surface criterion filters to phase==''tilting'' and reports ''no tilt to hold'' rather than passing when the glass never leans, which is the fail-closed shape the ticket asked for; sweep, ci_minutes selftest and tasks check all green on the merged tree, and all 41 gates.yml checks pass on it.'
---

Scenes have no player, so the play-bot tier has no referent. Its replacement is a **scene probe**:
criteria computed deterministically from captured frames and per-tick telemetry. It carries the
tier-2 weight, so it must be built to the play-bot's standard, not below it.

`eval/SCENES.md` lists the criteria for both scenes and, for each, the naive implementation it is
there to catch. Read it first.

## The standard this has to meet

- Every criterion **binary** and equally weighted, and **per-criterion results always reported**.
- Every criterion needs a **mutant** (can this check fail?) AND a **variant** (can it still pass
  on an input it mishandles?). A mutant removes the mechanism the check names; it cannot
  manufacture an input the check gets wrong. Every false negative ever adjudicated in this project
  has been of the second kind. `judge/bot_mutants.py` runs both halves for games and is the model.
- **Measure twice where the image allows it — once from telemetry, once from the pixels.**
  Telemetry is what the submission says it did. A criterion reading only telemetry is satisfiable
  by a submission that quietly lies, and the parallax and water-surface criteria are exactly where
  that is cheapest.

## The two criteria worth building first, because they are the discriminating ones

- **Water surface stays world-horizontal while the glass tilts.** The wrong implementation -
  water parented to the cup - is the one a hurried agent reaches for first, and it is invisible to
  any check that does not compare the surface normal to world up.
- **Same seed identical, different seeds different.** Two-sided on purpose: *different seeds
  differ* is satisfied by wall-clock noise that ignores the seed; *same seed matches* is satisfied
  by a canned pre-fractured mesh. Only the pair identifies seeded procedural fracture, so it must
  be scored as a pair and not as two independent criteria.

## What NOT to conclude

A criterion that no submission fails is not thereby safe - it may be measuring nothing. Games
learned this as a whole tier: tier 1 returned a single value across 7 of 10 groups, so its weight
was inert, and the fix was to ask what the tier had ever measured rather than to reweight it
(#92, #123). Report, for each criterion, how many submissions it separated. A criterion that
separated nothing is a question about the criterion.

Six submissions failing identically is a claim about the INSTRUMENT, not the population (#45,
#46). If every stack fails the refraction criterion byte-identically, suspect the check before
concluding anything about refraction.

## note 2026-08-24

## note 2026-08-24 — task 133 has landed, so the contract is real. Use these names.

`eval/suites/scene_prompts.py` is merged. Read the rendered prompts at `eval/suites/rendered/s*.txt`
— that is what an agent will actually see, and it is the authority over any summary including this
one. Both scenes run **660 ticks** and capture **12 frames** at `floor(i*660/11)`, `i` in `0..11`.

The telemetry the submissions must emit is already specified, and it was designed so the criteria
in `eval/SCENES.md` are computable rather than approximated:

| criterion | what it now reads |
|---|---|
| water stays world-horizontal under tilt | `water.up` against world up, **while** `glass.up` diverges from it — two separate vectors, so the wrong implementation (water parented to the cup) makes them equal |
| volume conservation | `water.volume + drips.volume`, which the prompt states is the same water |
| pieces rest ON the ground | `pieces[].y` and `settled` against `table.y` |
| reversal is a true inverse | `phase` reaches `"whole"`; compare that state to the `"draining"` opening |
| image-side checks | `glass.screen` gives the glass's box in frame coordinates as fractions |

`phase` is one of `draining`, `tilting`, `falling`, `broken`, `rewinding`, `whole`. **Measure the
tilt criterion only during `tilting`** — `water.up` is unconstrained once the glass is in flight,
and a criterion that reads it during `falling` would fail correct submissions.

## The thing that makes this ticket harder than it looks: there is no corpus

**No scene has been built or graded.** Games had stored trials to develop criteria against; you
have none, and none is coming until a matrix runs. So every criterion is written against
**fixtures you construct**, and that is a hazard as much as a convenience:

- A fixture written by the same hand as the criterion agrees with it by construction. State each
  fixture's expected verdict **before** running the criterion on it, in the fixture itself.
- The reference implementations under `eval/judge/fixtures` and `ref_arena/game.py` are the model
  for how this project does it for games — read one before inventing a scheme.
- **A criterion that has only ever seen fixtures has never met a real submission.** Say so where
  the results are published: the probe's first real run is also its first real test, and the
  honest expectation is that some criteria will turn out to be false-negative machines (#46 is
  sixteen of them in one sweep).

## What NOT to do

Do not tune a criterion until the fixtures pass. That is fitting the instrument to the only data
it has. If a criterion cannot be made to work on a fixture whose answer you stated in advance,
that is a finding about the criterion, and reporting it is a complete outcome.

## note 2026-08-24

The scene probe is `eval/judge/scene_probe.py`; `eval/judge/scene_mutants.py` pins it in
both directions and both run in `controls.yml`. Two reference fixtures were written for
it: `eval/judge/fixtures/ref_parallax` and `ref_glass`, on the `ref_arena` model.

## What the next agent should not re-derive

**The seed pair is one criterion and `table.y` is not a floor.** `DECISIONS.md` holds
both, with the reasoning. The `table.y` reading disagrees with this ticket's own note:
the contract calls it *"the height of the surface everything stands on"* and the scene
has two surfaces, so a floor test on that field fails correct work. It is used for the
SCALE — `max |glass.y - table.y|` — which is what makes every distance tolerance a share
of the drop rather than a number in somebody's world units.

**`front.occludes` is telemetry-only and cannot be otherwise.** The trace contract gives
the car's world position and each foreground thing's world position and no screen box for
the car, so the pixels cannot be asked whether one covered the other. Adding `car.screen`
to the contract would make it measurable twice — and that is a prompt change, which is a
regime boundary. Do not "fix" it inside the judge.

**The image-side shift estimator was chosen on measured counts, and the obvious
robustification is worse.** 5 candidates over the same 88 frame pairs; clipping the
profile at 3x its own mean — the textbook fix for one strong edge dominating a sum — is
9 pairs worse than doing nothing. The table is in `DECISIONS.md`. The shipped estimator
misses 8 of the 132 pairs in the 3 parallax fixtures and every miss is one shape: a band
holding an object that is stationary on screen. Two gates absorb it —
`ParallaxScene._reliable`'s 80% self-agreement, and the wrap check's `blind` counter.
**Do not go looking for a better estimator without re-running that comparison**; the
scratch harness that produced it is gone, but the 5 candidates are named in
`DECISIONS.md` and the fixtures reproduce them.

**Not wired into `judge/evaluate.py`, deliberately.** Nothing launches a scene, so the
wiring would be an unexercised path through the evaluator that every game trial runs. It
is a separate change and it needs its own regime note in `eval/RUNS.md`.

## What the census does and does not say

`scene_mutants.py --census` reports over **fixtures**, and says so in its own output.
`--runs-root <main>/eval/runs` prints `NOT ASKED - 0 scene gradings on disk`, never
`0 separated`. `--census-selftest` proves the census can print `NO - AN OPEN QUESTION`;
without it a census that has only ever printed `yes` is indistinguishable from one that
cannot print anything else.

All 15 criteria read `yes` over the 30 fixture-derived subjects. **That is not a result
about the criteria.** No scene has been built or graded, every threshold was chosen
against fixtures written by the same hand as the criterion, and #46 — sixteen false
negatives in one sweep of criteria that were green on their reference — is the honest
prior. Say so wherever a scene score is reported; four documents already do.

## Three things the suite found that I had expected to pass

1. A mutant that did not bite: `the rewind holds on the broken state` left the closing
   snap-back in place, so the criterion correctly passed. A mutant must remove the
   mechanism the criterion names, not one next to it.
2. A variant found a real false negative — the reversed-id scene, which is the same
   scene with its textures dealt to different bands. That is what produced the estimator
   comparison above.
3. The geometry variant found a fixture defect: `ref_parallax`'s renderer had no camera
   scale, so a bigger frame was a wider window rather than a zoom. `the same scene filmed
   1.5x larger` is now a real measurement of the #59 claim rather than a restatement.

## What the review found, and it was all real

Three rounds, the third clean. A published number was wrong — `DECISIONS.md` and
`scene_probe.py` named two different fourth estimator candidates and the pair attributed
to clipping belonged to neither (it is 40/44 and 33/44). Six ways the probe could publish
a wrong number rather than crash, the worst being `_wheels` raising `StatisticsError` on
a speed distribution with an empty slow half, which `drive` turned into every criterion
FALSE. And `ref_glass` reported a stationary fragment as unsettled for several ticks,
while `shatter.pieces_rest` reads exactly that field.

`judge/png.py` now writes atomically and is the single writer for all 6 fixtures; run
`bot_mutants.py` after touching it.

## Needs a finding number

The estimator measurement — 5 candidates over 88 frame pairs, with the textbook
robustification measurably worse than the thing it was meant to fix, and an independently
rebuilt fixed-window variant landing on the identical 82/88 as the shipped one. It is
another instance of *choose between candidates on the live-corpus count, never on which
one sounds more principled*, this time against an image estimator rather than a regex.
Allocate it against `main` at merge.
