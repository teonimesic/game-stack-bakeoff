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


---

## RESULT, 2026-08-23 — surfaced. `eval/tools/disclosure.py`, printed by `wholegame.py report`

**The broken state, established before the change** (rule 14). `python3 eval/wholegame.py
report --run-dir runs/wg-g4c-2026-08-21T02-26-46` from the unmodified main checkout: 82 lines,
0 occurrences of `agent_result.json`, 0 of "I could not". The same command on this branch: 110
lines, and the six trials that disclosed appear with their own sentences under the score table.

| file | what |
|---|---|
| `eval/tools/disclosure.py` | reads `artifacts/<trial>/agent_result.json` → `.result` **whole**. `--run-dir` (per trial), `--full` (every message whole, no selection), `--trial <id>` (one message whole), `--runs-dir` (the tree), `--json`, `--selftest` |
| `eval/wholegame.py` `cmd_report` | prints the located passages beside the per-trial score table, and names `--full` in its footer |
| `eval/tools/disclosure_mutants.py` | six mutants, each removing one mechanism; all six caught |

Both are in `tools/precampaign_smoke.py`. Both exit **2**, not 0, when the corpus is absent:
four of the six mutants are caught only by a real stored message, so a worktree run is a
non-measurement and says so.

### Both directions, on rows whose answer the documents state in advance

- **Known to disclose, appears with its text.** `wg-g4c` `godot__t0` and `t1` — #98 states both
  described the red `check.gd` gate. Both appear, and the `starter` cue is the one that fires on
  them, pinned separately so that family cannot go dead behind another cue. `wg-arena3d`
  `rust__t0/t1`, `ts__t0/t1` — rule 11 / #49. All four appear.
- **Known not to disclose, appears without it.** `archive-arena2d-wg-audio48` is recorded in
  `eval/RUNS.md` at a **0%** hand-classified rate over its n=3 readable messages. All three come
  back `quiet`; the other five come back `NO MESSAGE`, not quiet.
- **The whole message, not the truncated field.** `wg-arena3d` `g3_arena__rust__t1` states #49's
  mechanism at **character 0 of 3912**. The `tail` mutant — one line, `result[-3000:]` instead of
  `result` — loses it, and the selftest goes red naming that trial.
- **The quota case.** `classify()` is three-valued. Measured now rather than quoted: of 90
  `agent_result.json`, **6 `.result` are null and 9 hold the API's limit string**; the `limit`
  mutant turns two real aborted trials into quiet closing reports.

### It surfaces text; it does not grade it

No criterion id, no tier, no weight, nothing reaching `overall`. The cue set is a **convenience
for finding the passage**, and `--full` prints every message whole with no selection applied —
so the located view is never the only way to see the evidence. Where the two disagree, the whole
message is the evidence.

Its count is **not** a disclosure rate and must not be quoted as one. Over the same 75 messages
it locates **26** against the hand pass's 31: godot 3/15 (hand 3), rust 12/21 (hand 13), ts 3/23
(hand 4), unity 8/16 (hand 11). It under-reports in every arm and reproduces the same shape. It
finds 4 dedicated headings against the ticket's 10. **The six the hand pass called disclosures
and this leaves quiet were not adjudicated one by one** — that is the honest limit of the
agreement figure.

### A figure in this ticket that does not reproduce

*"44 of 161 stored values sit at that cap"*. Measured 2026-08-23 over `runs/**`: **137** trial
records carry an `agent.final_text` at all, and the two harnesses have different caps and must
not be pooled — whole-game **43 of 90 at 3000**, spec-change **25 of 47 at 1500**, pooled 68 of
137. The conclusion the sentence draws is unchanged and stronger: nearly half the whole-game
corpus is truncated. Left as written here, since `tasks/` is the archive; the live statement is
in `eval/AGENTS.md`, which already carried the 43-of-90 figure and has now been checked.

### What it found on its first pass, which the hand pass had not

A second family: **the agent reporting that the starter arrived broken** — where #98 came from,
and one-arm bias, since `build.compiles` and `verify.green` are the exit codes of the
submission's own recipes. Seven trials carry one, and **four are Rust agents in three different
runs** saying `just run` was broken in the starter because `crates/game` ships two binaries with
no `default-run`. Filed as `tasks/81`, not fixed here: `eval/starters/` is out of bounds without
a ticket, and repairing it is a regime boundary.

### Do not re-derive these

- The cue set is written from the rule, and every widening and narrowing is commented with the
  real message that forced it. Three drafts had false positives that **only a documented row
  caught**: an open `.{0,70}` window linked "aren't" to a later "run" (3 false positives);
  `never execut\w+` matched *"verify never executes `main.ts`"* and broke the `archive-arena2d`
  negative control; bare "nobody has" matched *"a paddle nobody has claimed"*. All three are
  mutants now.
- `residual` fires on **0 of 90** stored messages — kept for the phrasing `tasks/46` describes,
  and marked in the source as untested against anything an agent has actually written.
- `docstat.py --sweep` began failing on `--wildcards` in root `AGENTS.md` the moment this work
  added the words `wholegame.py` to that file: the flag check is suppressed unless a doc names
  one of our harnesses, so that false positive had been latent since the flag was written. Fixed
  by adding it to `FOREIGN_FLAG_PREFIXES` — it is bsdtar's, and the sentence naming it says so.
- The hand figures (31 of 75, per stack) came from a scratch classifier that was **not kept**.
  A second hand pass costs a careful read of 90 messages and would not agree to the row.
