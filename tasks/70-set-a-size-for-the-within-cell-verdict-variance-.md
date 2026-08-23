---
id: 70
title: Set a size for the within-cell verdict variance that re-opens the deterministic-tier ranking ban
status: in_flight
priority: 5
refs: DECISIONS.md 'Deterministic tiers may not rank stacks' row, eval/withdrawn.json WR-paired-verdict-tie, tasks/13
done_when: DECISIONS.md's re-open condition for the deterministic-tier ranking ban names a threshold with a size and a scope, and states what measurement would cross it; and the current 5-of-436 reading is adjudicated against it either way
---

Task 62 registered the unscoped '0 verdict differences across 380 paired criteria' figure as withdrawn and repaired every live document restating it. One of those documents was the DECISIONS.md row whose re-open condition read: any instrument change producing NON-ZERO within-cell verdict variance - currently 0 of 380. The scoped recount is not zero. It is 5 of 436 paired criteria in wg-matrix (1.1 percent) and 0 of 232 in wg-audio48, and part of that 5 is this project's own criterion repairs re-grading cells. So the condition as written is met in letter by a number that was always going to be non-zero once it was scoped, while the thing it was protecting - that the tiers cannot resolve below the cell - is unchanged. Task 62 restated the row as 'large enough to resolve a between-stack gap' and left the size open, because choosing it is a research call and not derivable from the repair. What is needed is a number, a scope and a producer, so the row stops being a sign test on a quantity that has no reason to be exactly zero.

## What this is

When a trial finishes, the building agent writes a closing message about its own work. It is
stored whole in `agent_result.json` as `.result`, and truncated to the last 3000 characters in
`trials/*.json` as `agent.final_text`.

`AGENTS.md` has carried **rule 11** for weeks: *read what the subject said about its own work
before grading it.* It is a rule with no implementation.

## What is wrong, and how we know

Measured by task 46 over all 90 stored `agent_result.json`, hand-classified against a rule fixed
before reading:

- **75 trials completed**, one homogeneous population.
- **31 of those 75 (41.3%) disclose** something unverified or a residual risk — 10 under a
  dedicated heading.
- **Nothing in the grading pipeline reads any of it.**

This is not hypothetical value. Rule 11 exists *because* agents twice diagnosed harness defects
in that paragraph and nothing noticed: both Godot agents described the broken `check.gd` gate
(#98) in their own words, and bounding that defect's radius came from reading those two
paragraphs plus two greps.

## Why it matters

A grader that ignores the subject's own account keeps re-deriving what the subject already told
it — and sometimes fails to derive it at all. The 41% is already on disk, already paid for, and
already correct. **Reading it costs nothing and re-running trials to raise it costs a matrix.**

That comparison is the point: task 46 declined to *instruct* agents to disclose more, partly
because raising a rate the graders ignore buys nothing. This is the other half of that argument.

## What should be done

Surface each completed trial's disclosure to whoever reads its score — most naturally in
`wholegame.py report`, beside the tier verdicts. It does not need to be interpreted; a human or
a judge reading a score should simply see what the agent said about it.

**Read `.result` from `agent_result.json`, not `agent.final_text`.** The latter is the last 3000
characters and **44 of 161 stored values sit at that cap** — you would be reading the end of the
message and calling it the message.

**Guard the quota case.** 9 of 90 `.result` values hold the API's error string rather than agent
text; a check testing only for non-empty would surface *"You've hit your weekly limit"* as a
closing report.

## Outcomes that count

Either it is surfaced — verified by a trial known to disclose appearing with its text and one
known not to appearing without — **or** the decision not to is recorded in `DECISIONS.md` with
the reason. A reasoned decline closes this.

## What not to conclude

Do not build a classifier that scores disclosure quality. That would make disclosure a criterion,
which changes what agents optimise for, and task 46 already declined that regime change on cost
grounds. This surfaces text; it does not grade it.
