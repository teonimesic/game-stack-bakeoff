---
id: 146
title: field_ranks pools idiomatic into the between-stack figure that JUDGING.md says it is barred from
status: todo
priority: 2
refs: 'eval/judge/field_ranks.py, eval/judge/JUDGING.md, eval/judge/RUBRIC.md, eval/judge/aspects.py, tasks/135, #53'
done_when: Either (a) the pooled figure excludes cross-stack-barred aspects, assert_poolable refuses them the way it refuses a control, every live document quoting a pooled figure is recomputed and restated with the new value, and the change is recorded in eval/RUNS.md as a comparability note; or (b) the pooling is deliberately kept, and the reason is written in DECISIONS.md with the recomputed leave-one-out figure showing what excluding idiomatic would have changed. Either way the figure is produced by running field_ranks.py, not quoted from memory, and the answer is not left as a difference between what the code does and what two live documents say.
---

JUDGING.md and RUBRIC.md have recorded idiomatic as cross-stack barred since #53 - 'per-stack-only, a result rather than a defect to engineer away'. field_ranks.classify() calls it SCORED, so every pooled between-stack figure this project publishes includes it. Task 135 made the bar readable by code (Aspect.cross_stack_bar) and made field_ranks PRINT it with the aspect's per-stack means, but deliberately did not change what is pooled: JUDGING.md's per-aspect table states that field_ranks --per-aspect reproduces all ten of its numbers, and dropping idiomatic from the pool re-analyses published game results. That is a decision with evidence behind it, not a side effect of adding scene aspects.
