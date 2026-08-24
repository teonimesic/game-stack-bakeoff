---
id: 134
title: 'Build the scene probe: the tier-2 criteria for s1_parallax and s2_glass, each with a mutant and a variant'
status: in_review
priority: 1
refs: 'eval/SCENES.md, eval/judge/bot_mutants.py, eval/judge/RUBRIC.md, tasks/133, #45, #46, #92, #123'
done_when: Every criterion in eval/SCENES.md is implemented, binary, and reported per-criterion; each has a mutant that dies and a variant that probes an input the check could mishandle, both run by a single command in CI; the seed pair is scored as ONE criterion; the criteria that can be are measured from BOTH telemetry and pixels with the two compared; and a census reports how many submissions each criterion separated, with any criterion that separated none named as an open question rather than shipped quietly. BLOCKED BEHIND 133.
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/20
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
