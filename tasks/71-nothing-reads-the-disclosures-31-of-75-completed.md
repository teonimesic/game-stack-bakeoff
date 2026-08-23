---
id: 71
title: Nothing reads the disclosures 31 of 75 completed trials already wrote
status: done
priority: 2
refs: 'AGENTS.md rule 11, eval/FINDINGS.md #98, tasks/46, eval/AGENTS.md agent_result.json'
done_when: either a grader or report surfaces each completed trial's self-disclosure to whoever reads its score, verified by a trial known to disclose appearing with it and one known not to appearing without, or the decision not to is recorded in DECISIONS.md with the reason; and whatever reads it reads the whole message, not the truncated field
established_by: 'eval/tools/disclosure.py reads artifacts/<trial>/agent_result.json .result WHOLE and wholegame.py report prints each trial''s located passages under the score table. Broken state established first: report on wg-g4c from the unmodified main checkout is 82 lines with 0 mentions of agent_result.json; on the branch 110 lines with the six disclosing trials quoting themselves. Both directions on rows the documents already answer - FINDINGS 98''s two wg-g4c godot trials and rule 11 / FINDINGS 49''s four wg-arena3d trials appear with their own words, and archive-arena2d, recorded in eval/RUNS.md at a 0 percent hand-classified rate over n=3, comes back quiet on all three readable messages and NO MESSAGE on the other five. Truncation control on real data: wg-arena3d g3_arena__rust__t1 states FINDINGS 49''s mechanism at character 0 of 3912 and the tail mutant that reads result[-3000:] loses it. It is a locator not a classifier - 26 of 75 against the hand-classified 31, godot 3/15 rust 12/21 ts 3/23 unity 8/16, under-reporting in every arm; three values not two, 15 of 90 stored results are null or the API limit string. eval/tools/disclosure_mutants.py runs six mutants, all six caught, four of them only by real stored data; both selftests added to tools/precampaign_smoke.py. First pass surfaced four Rust agents in three runs reporting the same broken starter recipe, filed as tasks/81. docstat.py --sweep exit 0 after adding --wildcards to FOREIGN_FLAG_PREFIXES, tasks.py check exit 0. Branch task-71-read-the-disclosures, commit c2bc8ce.'
---


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
