---
established_by: '1.70/2.05 appears in no live document as a measurement: DECISIONS.md, eval/judge/JUDGING.md and README.md In-flight now state figures produced by judge/field_ranks.py with field, value and order named. Method decided: value=rank order=pool for single-pair quotations, recorded in DECISIONS.md under Grading with three grounds and a reversal condition. JUDGING.md per-aspect tables labelled score/perround, the only method that reproduces them. DECISIONS.md tier-3 bullet no longer rests on the between-smaller-than-within direction, which reverses in four of eight readings; it now states a bound that no method flips - between never exceeds within by more than 23 percent. New FINDINGS 115: the ~10 percent replacement reading published 2026-08-22 is wrong on the pre field (19.7 percent, not 10) and was the ground 113 fell back on. docstat.py --sweep clean exit 0; field_ranks.py --selftest exit 0. eval/IMPROVEMENTS.md left alone as a log.'
id: 54
title: Retire the withdrawn 1.70/2.05 tier-3 figure from the three live documents that still publish it
status: done
priority: 2
refs: 'eval/judge/field_ranks.py, eval/findings/certifies-nothing.md #112, DECISIONS.md, eval/judge/JUDGING.md, README.md'
done_when: the pair 1.70/2.05 appears in no live document as a current measurement; each of the three sites states instead a figure reproduced by judge/field_ranks.py together with the field, the value (score or rank) and the order (pool or perround) it was computed under; DECISIONS.md's tier-3 bullet no longer rests on an inequality that reverses under a method change; and eval/IMPROVEMENTS.md is left alone because it is a log
---


WHAT THIS IS

FINDINGS #112. `README.md`'s headline table withdrew "between-stack range of mean ranks 1.70,
mean gap 2.05" on 2026-08-22. Three live documents still state it as a current measurement:
`DECISIONS.md` (tier-3 weight bullet), `eval/judge/JUDGING.md` ("Does any aspect separate the
four stacks?"), and `README.md`'s own In-flight section 250 lines below its withdrawal.

`eval/IMPROVEMENTS.md` also states it and is **deliberately out of scope**: it is an iteration
log and a log records what was believed at the time.

WHAT IS ALREADY ESTABLISHED, SO YOU DO NOT REDO IT

`eval/judge/field_ranks.py --rounds <dir>` is the producer. The quantity has two independent
method parameters, so there are four figures per field, not one. Measured over both stored
fields of `wg-tetris-judge-2026-08-17`, `g2_tetris3d`, 5 aspects x 2 orders, 10 usable rounds:

| field | score/pool | score/perround | rank/pool | rank/perround |
|---|---|---|---|---|
| pre  | 0.350 / 0.725 | 0.950 / 0.775 | 1.900 / 2.275 | 3.300 / 2.825 |
| post | 0.700 / 0.675 | 0.850 / 0.875 | 2.100 / 1.925 | 3.300 / 3.325 |

None is 1.70 / 2.05. A census of all 93 stored judge rounds finds no other five-aspect
two-order `g2_tetris3d` field, so there is nowhere else it could have come from.

`README.md`'s headline table already quotes `rank`/`pool` for both fields and reproduces exactly.
`JUDGING.md`'s per-aspect table reproduces exactly under `score`/`perround` and under no other
method — all ten cells.

THE DECISION THIS TASK HAS TO MAKE, AND WHY IT IS NOT A FIND-AND-REPLACE

**Which method the project reports.** `JUDGING.md` currently uses one method for its per-aspect
table and quotes a pooled line beneath it that matches no method at all. Pick one, state it in
`JUDGING.md` beside the figures, and make the other sites agree — or report the spread across
methods, which is the honest alternative and is what the four-column table above is for.

`DECISIONS.md` is the hard one. It does not merely quote the pair, it rests the tier-3 weight on
the direction: between smaller than within. **That direction holds in four of the eight readings
and reverses in the other four**, including under the one method proved to reproduce
`JUDGING.md`'s own table. The decision itself is safe on independent grounds — `README.md`'s
reading that the two sit within ~10% of each other in both fields, and #83, under which neither
round is defensible as blind at all. Rewrite the bullet onto those grounds. Do not restate the
inequality with a different pair of numbers; it is the wrong shape of argument regardless of
which numbers fill it.

WHAT NOT TO DO

Do not add a cross-document figure-agreement gate. It was built and measured (#112): 52 labels,
one hit, that hit a false positive, and it cannot see this defect by construction, because four
restatements of a stale number **agree** with each other. Propagation and consistency are the
same observation.

The thing that would have caught it is a declared withdrawal register — a machine-readable record
of what was withdrawn, checked against the live surface. That is filed separately as task 55.
