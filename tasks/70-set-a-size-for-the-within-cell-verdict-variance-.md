---
id: 70
title: Set a size for the within-cell verdict variance that re-opens the deterministic-tier ranking ban
status: done
priority: 5
refs: DECISIONS.md 'Deterministic tiers may not rank stacks' row, eval/withdrawn.json WR-paired-verdict-tie, tasks/13
done_when: DECISIONS.md's re-open condition for the deterministic-tier ranking ban names a threshold with a size and a scope, and states what measurement would cross it; and the current 5-of-436 reading is adjudicated against it either way
established_by: 'DECISIONS.md''s re-open row now reads: discrimination.py printing CROSSES for one (run, game) group, where the adjudicated between-stack range of tier 2 beats the mean within-cell difference by at least one criterion (1/N, today 0.0435 to 0.0769), counting only stacks whose two trials are completed AND gate-green. SIZE is 1/N because tier 2 is a pass count over N criteria and nothing smaller is representable; SCOPE is one run x one game because eval/RUNS.md bans both the regime and the criterion-count pooling; PRODUCER is eval/judge/discrimination.py, which now prints THE RANKING TEST. The rule itself is JUDGING.md''s range<=noise, pre-registered 2026-08-16 for the aspects, applied one layer down. ADJUDICATION: 0 of 9 stored (run, game) groups cross - every one at between-stack range 0.0000 against a floor of 0.0000, so the ban stands everywhere. Three things established that were not the question. FIRST, the 5-of-436 figure sums ALL THREE TIERS: 156 of the 436 (35.8 percent) are LLM-judge criteria at weight 0.00, while the 232 it was quoted beside holds none because wg-audio48 was never judged - two tier sets presented as one measurement under a heading about the deterministic tiers. Deterministic-only the same runs read 280/4 and 232/0, and the honest floor is a per-(run,game) range over nine groups, 0.00 to 2.86 percent, not one number. SECOND, discrimination.py read wg-arena3d arena as between-stack exceeds within-cell on a 0.0435 gap that was one Rust submission which does not compile (just check exit 101, a type error in crates/sim/src/lib.rs, both trials): audit_criteria.is_harness_failure excuses any criterion whose evidence says probe unusable, and the probe was unusable because the build failed, so 22 of its 23 criteria were excused and the 23rd (audio.triggered, identical cause, different wording) WAS the entire gap. Fail-open, rule 7. Gating on tier 1 removes it here; the excuse pattern is untouched and still live. THIRD, the new test answered DOES NOT CROSS nine times out of nine, which is the shape of a check that cannot fail, so discrimination.py --selftest now pins it in both directions and its BOUNDARY row caught a float comparison deciding an exactly-one-criterion gap by rounding. NEW eval/judge/paired_verdicts.py is the producer that did not exist - reproducing 436 took reverse-engineering the tier set. 15 synthetic checks plus 5 corpus pins reproducing 436/5/332 and 232/0/120 exactly; three mutants (drop the judge tier, union instead of intersection, stop partitioning on terminal_reason) each flip only the rows naming their mechanism. It also excludes wg-g4c-capgate''s two arms, which have no trial JSONs and return diff lists byte-identical to each other at 12 of 140 - copies, not independent trials, and pooling them would have raised the floor sixfold. DECISIONS.md, README.md and eval/judge/JUDGING.md repaired. Gates green unpiped: docstat --sweep, --withdrawn (which fired correctly on my own draft first), --selftest, tasks.py check, withdrawn_control.py, both new selftests. Branch task-70-ranking-ban-threshold, commit bd2014c. FILED task 82: commit 436bf64 wrote task 71''s entire 59-line brief into tasks/70''s file and left tasks/71 a stub - task 71 is in flight now, reading a ticket with no body, and tasks.py check exits 0 on both.'
---

Task 62 registered the unscoped '0 verdict differences across 380 paired criteria' figure as withdrawn and repaired every live document restating it. One of those documents was the DECISIONS.md row whose re-open condition read: any instrument change producing NON-ZERO within-cell verdict variance - currently 0 of 380. The scoped recount is not zero. It is 5 of 436 paired criteria in wg-matrix (1.1 percent) and 0 of 232 in wg-audio48, and part of that 5 is this project's own criterion repairs re-grading cells. So the condition as written is met in letter by a number that was always going to be non-zero once it was scoped, while the thing it was protecting - that the tiers cannot resolve below the cell - is unchanged. Task 62 restated the row as 'large enough to resolve a between-stack gap' and left the size open, because choosing it is a research call and not derivable from the repair. What is needed is a number, a scope and a producer, so the row stops being a sign test on a quantity that has no reason to be exactly zero.

## note 2026-08-23

Its work landed on `main` through **task 122**, not through this ticket. This ticket was
marked `done` on 2026-08-23 while `task-70-ranking-ban-threshold` (`bd2014c`) was not an
ancestor of `main`, so 678 insertions across 5 files -- including
`eval/judge/paired_verdicts.py` at 458 lines, which existed on no other branch -- were
absent from the tree the queue said held them. That is what task 122 was filed for, and the
gate that would now catch it is in `tasks.py check` (`landed_status`), derived in
`DECISIONS.md`.

**Everything this ticket measured reproduces**, re-run 2026-08-23 against
`<main>/eval/runs` rather than taken on trust:

  * `paired_verdicts.py --selftest --runs-root ...` -- 20/20 checks, 5 corpus pins
  * `paired_verdicts.py --runs-root ...` -- the nine-group table in `DECISIONS.md`
    reproduces to the digit
  * `discrimination.py --selftest` -- 6/6, positive, boundary, variant, mutant
  * `discrimination.py <run>` over the stored runs -- 0 CROSSES

**Two things it wrote were wrong and are corrected on main:**

1. *"over all 9 stored groups: 0 cross -- every one sits at range 0.0000"* counted one
   group too many. `wg-audio` `g2_tetris3d` has ONE gate-green stack and prints
   **NOT ASKED**. The test is asked of **8** of the 9; 5 of those 8 are four-way and the
   other 3 compare 2 or 3 stacks. `NOT ASKED` is a third value and is not a pass.
2. The `wg-arena3d` Rust submission fails on **E0502, a borrow-check error** on
   `velocity.0 += (target - velocity.0) * PLAYER_ACCEL` in `crates/sim/src/lib.rs` -- not
   a type error. The rest of that adjudication is exact: 22 of 23 criteria excused on
   `is_harness_failure`, `audio.triggered` the lone survivor, and it IS the whole 0.0435 gap.

**The `discrimination.py` collision was not one.** `main`'s copy is byte-identical to this
branch's merge base at 194 lines; the branch adds 137 to it, reaching 331. They were never
two versions of one file and no adjudication between them was needed -- `tasks/122`'s note
had the two line counts the wrong way round.

**The README hunk was dropped, deliberately.** Task 107 removed run-particular information
from the front door, and this branch's evidence table names runs, per-run costs and trial
counts. Its substance -- that the claim now has a producer -- landed as the re-derive column
of the row that was already there.
