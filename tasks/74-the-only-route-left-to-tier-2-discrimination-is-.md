---
id: 74
title: The only route left to tier-2 discrimination is a harder task, and nobody has priced one
status: done
priority: 2
refs: 'DECISIONS.md saturated-tier-2 decision, eval/judge/tier2_census.py, eval/suites/wholegame_prompts.py, FINDINGS #128'
done_when: 'a costed proposal in DECISIONS.md for what a harder task looks like - either a fifth game or a raised bar on an existing one - with the measured trial price from eval/RUNS.md and a statement of what tier-2 criterion would have headroom on it. OR a measurement showing some existing group can be de-saturated without a new run, which would retire this. Do not launch anything: the spend is the operator''s call and this task is to bring them the number.'
established_by: 'Costed proposal written into DECISIONS.md as ''A harder task is PRICED here, and gated behind a free pre-test'', on branch task-74-price-a-harder-task commit 2bc1cdc, plus a reversal-conditions row and task 83 for the pre-test. PRICE, re-read from eval/RUNS.md on 2026-08-23 rather than carried forward: one clean 8-cell field under the standing regime is wg-g4c at 421.00 dollars, 8/8 completed, 36.16 to 77.60 per trial, 55.7 to 86.3 min wall; the last game actually added cost 698.21 all-in, being wg-g4 211.64 stopped at 4 of 8 plus wg-g4b 65.57 as an 8/8 api_error null plus wg-g4c 421.00, so two of three runs produced nothing gradeable. Judge spend is zero because tier 2 is deterministic and tier 3 carries no weight. A raised bar on an existing game is the same order: wg-arena3d was 374.05 for 8 completed but straddled the finding-49 machine repair so its cost is contaminated too. CRITERION WITH HEADROOM: stage.completes made graded rather than binary, the fraction of the stage reached. Three tier-2 criteria sit at the FLOOR not the ceiling and all three are diagnostic_only because the bot cannot play well enough - layer.clears and score.rewards_clears False on all 19 tetris trials where recorded, stage.completes False on all 8 platformer trials - and stage.completes is the only one whose quantity is a fraction on an axis the prompt gives a direction for. TWO OF THE TICKET PREMISES DID NOT SURVIVE CHECKING, and both corrections change the decision. First, adjudicated the corpus is flat in 10 of 10 groups, not 5 of 10: tier 2 has never produced a selective failure that survives adjudication. wg-matrix-2026-08-13, the only run where it separated submissions, has 9 selective-failure trials carrying 38 criterion-failures - 22 are a probe dead before tick 0 on the two Unity arena trials, and the other 16 are exactly the 16 entries in ADJUDICATED in eval/judge/audit_criteria.py, every one marked false_negative, with all 7 distinct criteria marked REPAIRED in CONSTRUCTIBLE_FAILURE in the same file. python3 eval/judge/discrimination.py eval/runs/wg-matrix-2026-08-13T14-02-50 prints ADJUDICATED spread 0.0000 in all three games against RAW 0.2308 / 0.3077 / 0.7333. The same effect without adjudication, on one field across one day: wg-g4c-capgate re-grades the eight wg-g4c work trees and scores g4_platformer__ts__t0 at 14 of 20 on 2026-08-22 and 20 of 20 on 2026-08-23, same submission, same 20 criteria, play-bot repaired between. Observed tier-2 spread has tracked the play-bot false-negative rate, not the submissions, so there is no precedent for any binary play-bot criterion discriminating between competent submissions and a matrix bought today would be bought on an untested assumption. Second, the criteria are not short of resolution, they are on the wrong axis: over the eight wg-g4c submissions 16 of the 20 scored criteria already record more than one distinct numeric evidence vector and 8 record eight distinct vectors on eight submissions, and every axis is a free design parameter the prompt states no direction for - hitbox offset 22.0 to 32.0, jump rise 44.6 to 66.8, i-frames 43 to 80 ticks, health 4 or 5, first platform edge x=300.0 to x=560.0. Scoring any of them ranks the four stacks on jump height. THE SECOND DONE-WHEN BRANCH IS A TRAP AND THAT IS THE RESULT: an existing group can be de-saturated today, because stage.completes already stores 14.3 / 15.8 / 17.8 / 20.3 / 20.6 / 22.5 / 25.6 / 29.0 percent of the way to the goal, eight distinct values - and the number is meaningless, since the bot walks right until it falls in a hole (task 76) so the scalar ranks the field on where each submission put its first pit. De-saturating is easy; de-saturating meaningfully is the whole problem. WHAT IS DECIDED IS THE ORDERING, NOT THE SPEND, per the ticket: the free pre-test first, filed as task 83, re-driving the eight surviving wg-g4c work trees under the work root once task 76 lands and reading stage.completes as a fraction, with three named outcomes each of which is decisive. TICKET REFS THAT DO NOT RESOLVE ON MAIN, recorded in the ticket body: eval/judge/tier2_census.py and the saturated-tier-2 DECISIONS.md section exist only on the unmerged branch task-65-tier2-saturation commit 897d334, which also allocates FINDINGS #125 against a different #125 already on main. NO FINDING NUMBER TAKEN, deliberately: task-65 and task-72 are both in flight in the findings namespace. GATES, unpiped: docstat.py --sweep exit 0 clean over 140 docs, tasks.py check exit 0 with 82 tasks well-formed. NOT TOUCHED: the DECISIONS.md Open bullet stating 24 of 56, because task-65-tier2-saturation rewrites exactly those lines.'
---

tier2_census.py reports 5 of 10 groups returning a single value, every selective tier-2 failure in the corpus is from wg-matrix-2026-08-13, and both in-rubric repairs were measured and do not work (FINDINGS #128): the three withheld diagnostics are single-valued wherever recorded, and four criteria built from requirements the g4 prompt states and no criterion checks passed 8 of 8 on wg-g4c. g4_platformer was added as the most plausible remaining route to discrimination and tied. That leaves the task, and a task change costs a matrix, so it needs a price before it needs a design.

## Corrections to this ticket's own premises, measured 2026-08-23 — do not re-derive

**Two refs above do not resolve on main.** `eval/judge/tier2_census.py` exists only on the
unmerged branch `task-65-tier2-saturation` (commit 897d334), and the "saturated-tier-2 decision"
in `DECISIONS.md` is added by that same commit. On main the live producers are
`eval/judge/tier1_census.py` (its per-group table carries the tier-2 column) and
`eval/judge/discrimination.py`. The FINDINGS number is also unsafe: that commit allocates #125
for this work while main's #125 is something else, so cite the branch, not the number.

**The 5-of-10 figure is real but understates the state, and the correct figure changes the
question.** Adjudicated it is **10 of 10**. Tier 2 has produced no selective failure anywhere in
the 68-trial corpus that survives adjudication:

- `wg-matrix-2026-08-13` is the only run where tier 2 separated submissions. Its 9
  selective-failure trials carry **38 criterion-failures**. 22 are a probe that died before
  tick 0 (both Unity arena trials). The other **16 are exactly the 16 entries in `ADJUDICATED`
  in `eval/judge/audit_criteria.py`, every one marked `false_negative`**, and all **7** distinct
  criteria involved are marked `REPAIRED` in `CONSTRUCTIBLE_FAILURE` in that same file.
- `python3 eval/judge/discrimination.py eval/runs/wg-matrix-2026-08-13T14-02-50` prints
  ADJUDICATED spread **0.0000** in all three games, against raw 0.2308 / 0.3077 / 0.7333.
- The same effect without adjudication: `wg-g4c-capgate` re-grades the eight `wg-g4c` work trees,
  and `g4_platformer__ts__t0` is **14 of 20 on 2026-08-22 and 20 of 20 on 2026-08-23** — same
  submission, same 20 criteria, play-bot repaired in between.

Observed tier-2 spread has tracked the play-bot's false-negative rate, not the submissions. There
is no precedent in this corpus for **any** binary play-bot criterion discriminating between
competent submissions, which is why the proposal gates the spend behind a free pre-test rather
than buying a matrix on that assumption.

**The measurement that decides the design, and it is not a resolution problem.** Over the eight
`wg-g4c` submissions, **16 of the 20 scored criteria record more than one distinct numeric
evidence vector and 8 record eight distinct vectors on eight submissions.** The criteria
discriminate perfectly; what they discriminate on is free design parameters — hitbox offset 22.0
to 32.0, jump rise 44.6 to 66.8, i-frames 43 to 80 ticks, health 4 or 5, first platform edge
x=300.0 to x=560.0. Scoring any of them ranks the four stacks on jump height.

**The trap the second `done_when` branch walks into.** An existing group *can* be made to show
eight distinct values today: `stage.completes` already stores 14.3 / 15.8 / 17.8 / 20.3 / 20.6 /
22.5 / 25.6 / 29.0 percent of the way to the goal. It is meaningless — the bot walks right until
it falls in a hole (task 76), so that scalar ranks the field on where each submission put its
first pit. **De-saturating is easy; de-saturating meaningfully is the whole problem.**

**Filed: task 83**, the free pre-test — re-read `stage.completes` as a fraction once task 76
lands. The proposal is in `DECISIONS.md` under *"A harder task is PRICED here, and gated behind
a free pre-test"*, with the price: **$421.00** for one clean 8-cell field (`wg-g4c`, 8/8
`completed`, $36.16-$77.60 per trial) and **$698.21** all-in at the only precedent, since two of
the three runs that delivered `g4_platformer` produced nothing gradeable.
