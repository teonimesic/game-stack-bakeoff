---
id: 29
title: Tier 1 is a saturated floor test carrying a 0.31 discriminating weight - decide what it should be
status: in_flight
priority: 4
refs: 'eval/findings/certifies-nothing.md #92, eval/judge/weight_sensitivity.py, eval/judge/RUBRIC.md, DECISIONS.md'
done_when: 'eval/judge/weight_sensitivity.py --all --runs-root <main checkout>/eval/runs still reports FLIPS=0 (it must, or something else broke), AND one of: (a) RUBRIC.md states where 0.31 came from with the evidence, or (b) tier 1 is re-scoped as a gate with the RUBRIC.md scoring block and README.md grading table both updated and the change recorded in DECISIONS.md, or (c) new tier-1 criteria are added that produce more than one distinct tier-1 value on a re-grade of the 24 stored wg-matrix submissions, each pinned by both halves of judge/bot_mutants.py. Whichever is chosen, DECISIONS.md''s rubric-ceiling open item is updated to say what was decided and why.'
---

FINDINGS #92 measured tier 1 returning 1.0 on all 24 wg-matrix submissions and all 16 wg-audio48 submissions - 40 of 56 matrix trials at the ceiling with zero variance. wg-audio48 returns 1.0 on BOTH scored tiers for all 16 of its trials, so that run's entire deterministic grade is the constant 1.0. The 0.31 weight in front of tier 1 is arithmetically present and informationally absent: at the w1=1 endpoint all four stacks tie in all three wg-matrix games. Separately, no document anywhere derives the 0.31/0.69 split; RUBRIC.md, JUDGING.md, DECISIONS.md and README.md all quote it and none justifies it. Tier 1 is not useless - it caught wg-arena3d (0.0) and wg-g4c (0.857), i.e. submissions that fail outright. It is a FLOOR TEST that works, mislabelled and weighted as a discriminating score. Three options, and this task is to pick one on evidence: (a) keep the split and state its derivation, (b) re-scope tier 1 explicitly as a pass/fail gate outside the weighted score, which is what the gpt project at ~/Documents/heavenstudio/game-research-gpt does with its hard gates before scoring, (c) add tier 1 criteria with actual headroom. Do NOT simply reweight: a weight change that moves no ordering, which weight_sensitivity.py shows is the case for every stored group, would be a change that measures nothing.

## Dispatch knowledge, 2026-08-23 — written back from a launch message

Two things changed after this ticket was filed, and both bear on the choice:

**`eval/judge/weight_sensitivity.py` now exists** and reports zero ordering flips at any weight
over the stored trials. Run it. That is evidence for option (b) and against a naive reweight —
but read its own caveat about degenerate endpoints before quoting it.

**Task 54 set a precedent to follow.** When a published quantity had no producer, the fix was to
*build the producer* and require every published figure to come from it (`field_ranks.py`). If
you choose option (a), the derivation must be reproducible by running something, not asserted in
prose.

**Do not simply reweight.** A weight change that moves no ordering — which
`weight_sensitivity.py` shows for every stored group — is a change that measures nothing.

Options (b) and (c) are a **rubric change and a regime boundary**: an `eval/RUNS.md` note, and
the `README.md` grading table must agree with `RUBRIC.md`. A criterion added without a mutant is
not added. **Do not re-grade stored submissions to make a new scheme look better** — if a change
would move stored scores, say so and leave them.
