---
id: 74
title: The only route left to tier-2 discrimination is a harder task, and nobody has priced one
status: open
priority: 2
refs: 'DECISIONS.md saturated-tier-2 decision, eval/judge/tier2_census.py, eval/suites/wholegame_prompts.py, FINDINGS #126'
done_when: 'a costed proposal in DECISIONS.md for what a harder task looks like - either a fifth game or a raised bar on an existing one - with the measured trial price from eval/RUNS.md and a statement of what tier-2 criterion would have headroom on it. OR a measurement showing some existing group can be de-saturated without a new run, which would retire this. Do not launch anything: the spend is the operator''s call and this task is to bring them the number.'
---

tier2_census.py reports 5 of 10 groups returning a single value, every selective tier-2 failure in the corpus is from wg-matrix-2026-08-13, and both in-rubric repairs were measured and do not work (FINDINGS #126): the three withheld diagnostics are single-valued wherever recorded, and four criteria built from requirements the g4 prompt states and no criterion checks passed 8 of 8 on wg-g4c. g4_platformer was added as the most plausible remaining route to discrimination and tied. That leaves the task, and a task change costs a matrix, so it needs a price before it needs a design.

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
