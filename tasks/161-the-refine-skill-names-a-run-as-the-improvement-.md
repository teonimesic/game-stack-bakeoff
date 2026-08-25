---
id: 161
title: The refine skill names a run as the improvement loop's trigger, and three of its iterations did not come from one
status: todo
priority: 3
refs: .agents/skills/refine/SKILL.md, eval/IMPROVEMENTS.md, IMPROVEMENTS.md, AGENTS.md
done_when: The refine skill states the loop's trigger as a property that covers the iterations the file actually contains - checked by naming iterations 13, 14 and 15 and saying whether each qualifies - and says where an evaluator change that did not come from a run belongs. Deciding the loop is run-only, with ticket-driven changes going to findings, closes this. No iteration is retro-filed.
---

`.agents/skills/refine/SKILL.md` says the improvement loop fires when *"a matrix has finished AND
been evaluated"*. That describes some of the loop and not all of it.

Measured 2026-08-25:

- last matrix: **`wg-g4c-2026-08-21`**; the only later record is a single-trial harness probe.
- last iteration in `eval/IMPROVEMENTS.md`: **15**, dated **2026-08-23** — after that run.
- **iterations 13, 14 and 15 were not run-driven.** Iteration 13 opens *"Iteration 11a repurposed
  `pack_completeness` … what it did not ask is whether the pack on disk is the pack the manifest
  describes"* — a grader change reasoned from a previous iteration, with no run between.

So the loop is **not stale**: it is idle because no matrix has run, which is correct behaviour under
the documented trigger. The gap is that the trigger under-describes what has actually fed it.

## Why it matters now rather than as tidiness

2026-08-24 and 08-25 produced several changes with exactly the iteration shape — a hypothesis, a
change, and a measurement that could have come out against it:

| change | the measurement that could have refuted it |
|---|---|
| excluding cross-stack-barred aspects from the pooled figure | 3 of 8 readings flip; max excess +22.6% → +14.3% |
| repairing the grader's transcription of declared events | re-scoring census: 59 unchanged, 0 moved, **with the reason** |
| specifying the zero-aim contract | 7,540 ticks / 4,636 zero-aim / 33 firing, and a separated null |

Each is recorded — in `eval/FINDINGS.md`, in a ticket, and in `eval/RUNS.md` where a boundary was
crossed. **Nothing is lost.** The question is whether the loop is meant to hold them too, because
right now the answer is decided by whoever happens to be writing.

## What would answer it

State the trigger as the **property**, not the occasion. Candidates, and this is the whole ticket:

- *"a change to the evaluator whose effect was measured before and after"* — which would have
  claimed all three rows above, and iterations 13–15;
- *"anything a run taught"* — which claims none of the three and matches the skill as written;
- something else, argued.

**Concluding that the loop is run-only and that ticket-driven changes belong in findings is a
complete answer** — it costs one sentence in the skill and stops the next reader wondering. What is
not acceptable is the current state, where the skill names one trigger and the file contains
iterations that trigger names.

## What NOT to do

Do not retro-file today's changes as iterations to make the file look fed. If the answer is that
they belong there, say so and let the next one land there; rewriting history into a loop that did
not produce it is the narration this project already removes from live documents.
