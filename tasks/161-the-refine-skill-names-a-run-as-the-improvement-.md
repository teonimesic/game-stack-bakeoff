---
id: 161
title: The refine skill names a run as the improvement loop's trigger, and three of its iterations did not come from one
status: in_testing
priority: 3
refs: .agents/skills/refine/SKILL.md, eval/IMPROVEMENTS.md, IMPROVEMENTS.md, AGENTS.md
done_when: The refine skill states the loop's trigger as a property that covers the iterations the file actually contains - checked by naming iterations 13, 14 and 15 and saying whether each qualifies - and says where an evaluator change that did not come from a run belongs. Deciding the loop is run-only, with ticket-driven changes going to findings, closes this. No iteration is retro-filed.
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/44
established_by: 'PR #44, 4 review rounds then a clean one; iterations 13/14/15 traced to tasks/33, tasks/87 and iteration 14''s loose end, 0 of 3 from a finished matrix; gates green unpiped and linkcheck pinned red then green on the citation'
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

## note 2026-08-27

## Closed on PR #44 — the loop is triggered by a change, not by a run

**The check the ticket asked for, run 2026-08-27.** Iterations 13, 14 and 15 were all committed
2026-08-23 (`git log -S'<heading>' -- eval/IMPROVEMENTS.md`) and **none** qualifies under the
skill's old trigger. 13 came from `tasks/33`, 14 from `tasks/87`, 15 from the loose end iteration
14 handed on; each measured a stored corpus offline. The last multi-cell matrix is
`wg-g4c-2026-08-21T02-26-46`, at 8 by `ls eval/runs/<run>/artifacts | wc -l`; the 2 later run
directories (`wg-harness-probe-primeagent-2026-08-24`, `wg-scene-s1ts-2026-08-25`) are at 1 each,
so the ticket's "the only later record is a single-trial harness probe" is now two of them.

**Decided: the trigger is the change, not the occasion.** The loop fires when the instrument, the
product, or the guidance for either is about to change and the effect can be measured before and
after. The run-only alternative was declined and the reason is in `DECISIONS.md`: a finding
records what was *observed* and carries no pre-registration, no falsifier and no keep-or-revert,
so filing a measured change there drops exactly what makes an iteration falsifiable — and it
would still leave 13-15 in a file whose trigger excluded them. Nothing was retro-filed.

**Where the contract now lives, because this took 4 review rounds to get right.**
`eval/IMPROVEMENTS.md`'s preamble **owns** it — the trigger, the instrument/product split, where
guidance goes, and what separates an iteration from a finding. Root `IMPROVEMENTS.md` points at
it. The skill states its own trigger and then sends the reader there; it defines nothing. Two
successive review rounds fired on the skill restating the contract (a table, then just the
definition and one example), which is #38's shape — **do not put the record contract back in the
skill.**

**Two things the next agent should not re-derive.**

- `DECISIONS.md` has **no** reference-link definition block and dozens of bare `(#NN)` citations.
  A `[#95]` shortcut there is red under `linkcheck.py` until a definition is written. This branch
  added the first one, at the foot of the file:
  `[`#95`]: eval/findings/one-arm-bias.md#95-a-judge-pack-is-a-numbering-not-a-set-so-re-evaluating-a-run-left-nine-passes-stacked-on-disk`
  Breaking one character of that anchor takes `linkcheck.py` to exit 1 naming the fragment.
- `pr_review_state.py` answered `LANDED_COMMENT ... notice=Reviews paused` at `elapsed=1s` after
  the resume request, because the paused summary comment names the head and the comment arm is
  left alone by a pause. Posting `@coderabbitai review` returned *"Already reviewed the last
  commit"* — which is how a clean round reads once the pause is on. The round at head `93f4ec7`
  ran (IN_FLIGHT for ~250s) and produced **0** inline comments.

**Not established.** Whether all 17 `## Iteration` headings in `eval/IMPROVEMENTS.md` came from
somewhere other than a finished run — only 13, 14, 15 and the 2 root-loop entries were traced.
