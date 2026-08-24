---
id: 134
title: 'Build the scene probe: the tier-2 criteria for s1_parallax and s2_glass, each with a mutant and a variant'
status: todo
priority: 1
refs: 'eval/SCENES.md, eval/judge/bot_mutants.py, eval/judge/RUBRIC.md, tasks/133, #45, #46, #92, #123'
done_when: Every criterion in eval/SCENES.md is implemented, binary, and reported per-criterion; each has a mutant that dies and a variant that probes an input the check could mishandle, both run by a single command in CI; the seed pair is scored as ONE criterion; the criteria that can be are measured from BOTH telemetry and pixels with the two compared; and a census reports how many submissions each criterion separated, with any criterion that separated none named as an open question rather than shipped quietly. BLOCKED BEHIND 133.
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
