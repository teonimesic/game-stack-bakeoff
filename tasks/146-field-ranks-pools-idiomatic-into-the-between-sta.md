---
id: 146
title: field_ranks pools idiomatic into the between-stack figure that JUDGING.md says it is barred from
status: todo
priority: 2
refs: 'eval/judge/field_ranks.py, eval/judge/JUDGING.md, eval/judge/RUBRIC.md, eval/judge/aspects.py, tasks/135, #53'
done_when: Either (a) the pooled figure excludes cross-stack-barred aspects, assert_poolable refuses them the way it refuses a control, every live document quoting a pooled figure is recomputed and restated with the new value, and the change is recorded in eval/RUNS.md as a comparability note; or (b) the pooling is deliberately kept, and the reason is written in DECISIONS.md with the recomputed leave-one-out figure showing what excluding idiomatic would have changed. Either way the figure is produced by running field_ranks.py, not quoted from memory, and the answer is not left as a difference between what the code does and what two live documents say.
---

JUDGING.md and RUBRIC.md have recorded idiomatic as cross-stack barred since #53 - 'per-stack-only, a result rather than a defect to engineer away'. field_ranks.classify() calls it SCORED, so every pooled between-stack figure this project publishes includes it. Task 135 made the bar readable by code (Aspect.cross_stack_bar) and made field_ranks PRINT it with the aspect's per-stack means, but deliberately did not change what is pooled: JUDGING.md's per-aspect table states that field_ranks --per-aspect reproduces all ten of its numbers, and dropping idiomatic from the pool re-analyses published game results. That is a decision with evidence behind it, not a side effect of adding scene aspects.

## note 2026-08-24

## note 2026-08-24 (orchestrator) — it reaches README, and the direction is probably harmless and unmeasured

Checked before leaving this at p2, because "does it touch a published number" is the question that
decides urgency.

**It reaches the front door.** `README.md`'s result row *"the LLM judge is not a fifth route — no
subjective aspect separates the stacks either"* names `field_ranks.py --rounds` as its producer.
That is a between-stack claim computed over a pool that includes `idiomatic`, which
`JUDGING.md` and `RUBRIC.md` have barred from between-stack use since #53.

**Two things hold it below p1, and neither is a reason to skip it:**

1. **The published claim is a NULL.** *No* aspect separates the stacks. Removing an aspect from a
   pool that separates nothing is unlikely to make it start separating something — but *unlikely*
   is not a measurement, and this project's standard is that a number is produced, not reasoned
   about.
2. **Tier 3 is weight 0.00 and contributes nothing to any score**, and the same README row already
   records that the blinding failed and all 84 stored packs carried text naming the stack. So the
   claim is heavily caveated before this defect is applied to it.

**What settles it is one number: the leave-one-out figure.** Recompute the pooled result with
`idiomatic` excluded and compare. Both outcomes are publishable and both close this ticket —
`(a)` the null survives, in which case the bar can be honoured at no cost to any published claim,
or `(b)` it does not, which is a considerably more interesting finding and a correction to
`README.md`.

**Do not let the null tempt you into skipping the recomputation.** "It would not have changed
anything" is exactly the claim that needs the number, and a mechanism that runs, agrees with what
was already believed, and measures nothing is the shape this project keeps paying for.
