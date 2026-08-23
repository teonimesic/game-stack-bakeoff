---
id: 71
title: Nothing reads the disclosures 31 of 75 completed trials already wrote
status: open
priority: 2
refs: 'AGENTS.md rule 11, eval/FINDINGS.md #98, tasks/46, eval/AGENTS.md agent_result.json'
done_when: either a grader or report surfaces each completed trial's self-disclosure to whoever reads its score, verified by a trial known to disclose appearing with it and one known not to appearing without, or the decision not to is recorded in DECISIONS.md with the reason; and whatever reads it reads the whole message, not the truncated field
---

## Background this ticket was filed without

`tasks/46` measured the baseline by hand over all 90 stored `agent_result.json` and declined
the starter change; its closing paragraph is where this ticket came from. The hand figures —
31 of 75 completed trials disclose, godot 3/15, rust 13/21, ts 4/23, unity 11/16 — are in
`eval/RUNS.md`, "DECLINED: requiring a finish-report section in the starters". **Do not
re-derive them**: the scratch classifier that produced them was not kept, so a second hand
pass would cost a careful read of 90 messages and would not agree to the row.

## RESULT, 2026-08-23 — built. `eval/tools/disclosure.py`, printed by `wholegame.py report`

**The broken state, established first.** `python3 eval/wholegame.py report --run-dir
runs/wg-g4c-2026-08-21T02-26-46` from the unmodified main checkout: 82 lines, 0 occurrences of
`agent_result.json`, 0 of "I could not". The same command on this branch: 110 lines, and the
six trials that disclosed appear with their own sentences under the score table.

### What was built

| file | what |
|---|---|
| `eval/tools/disclosure.py` | reads `artifacts/<trial>/agent_result.json` → `.result` **whole**, locates disclosure passages, prints them verbatim. `--run-dir`, `--runs-dir`, `--trial <id>` (whole message), `--json`, `--selftest` |
| `eval/wholegame.py` `cmd_report` | prints the located passages beside the per-trial score table |
| `eval/tools/disclosure_mutants.py` | six mutants, each removing one mechanism; all six caught |

Both selftests are wired into `tools/precampaign_smoke.py`, and both exit 2 rather than 0 when
the corpus is absent — four of the six mutants are caught only by a real stored message, so a
worktree run is a non-measurement and says so.

### The verification the `done_when` asks for, both directions

- **Known to disclose, appears with it.** `wg-g4c` `g4_platformer__godot__t0` and `t1` — #98
  states both said the starter gate was red before they touched anything. Both appear, and the
  `starter` cue is the one that fires on them, pinned separately so that family cannot go dead
  behind another cue. `wg-arena3d` `rust__t0/t1` and `ts__t0/t1` — rule 11 / #49. All four
  appear.
- **Known not to disclose, appears without it.** `archive-arena2d-wg-audio48` is recorded in
  `eval/RUNS.md` at a **0%** hand-classified rate over its n=3 readable messages. All three come
  back `quiet`; the other five come back `NO MESSAGE`, not quiet.
- **Reads the whole message, not the truncated field.** `wg-arena3d` `g3_arena__rust__t1` states
  #49's mechanism at **character 0 of 3912**. The `tail` mutant — one line, `result[-3000:]`
  instead of `result` — loses it, and the selftest goes red naming that trial.

### What it is, stated so nobody quotes it wrongly

A **locator, not a classifier**. Over the same 75 messages it fires on **26** against the hand
pass's 31: godot 3/15 (hand 3), rust 12/21 (hand 13), ts 3/23 (hand 4), unity 8/16 (hand 11).
It under-reports in every arm and reproduces the same shape. `quiet` means no cue matched, not
that a trial disclosed nothing. **Three values, never two**: 15 of 90 `.result`s are `null` or
hold the API's own limit string, and anything testing for non-empty scores an error message as
a closing report.

Recall against the hand set is measured only in aggregate and on the documented rows; the six
messages the hand pass called disclosures and this tool leaves quiet have **not** been
adjudicated one by one. That is the honest limit of the agreement figure above.

### What it found on its first pass, which the hand pass had not

A second family: **the agent reporting that the starter arrived broken** — where #98 came from,
and one-arm bias, because `build.compiles` and `verify.green` are the exit codes of the
submission's own recipes. Seven trials carry one, and **four are Rust agents in three different
runs** saying `just run` was broken in the starter because `crates/game` ships two binaries with
no `default-run`. Filed as `tasks/81`, not fixed here: `eval/starters/` is out of bounds without
a ticket, and repairing it is a regime boundary.

### Do not re-derive these

- The cue set is written from the rule, and every widening and narrowing is commented with the
  real message that forced it. Three drafts had false positives that only a **documented row**
  caught: an open `.{0,70}` window linked "aren't" to a later "run" (3 false positives);
  `never execut\w+` matched *"verify never executes `main.ts`"* and broke the `archive-arena2d`
  negative control; bare "nobody has" matched *"a paddle nobody has claimed"*. All three are
  mutants now.
- `residual` fires on **0 of 90** stored messages. Kept for the phrasing `tasks/46` describes,
  and marked in the source as untested against anything an agent has actually written.
- `docstat.py --sweep` began failing on `--wildcards` in root `AGENTS.md` the moment this work
  added the words `wholegame.py` to that file: the flag check is suppressed unless a doc names
  one of our harnesses, so the false positive had been latent since the flag was written. Fixed
  by adding it to `FOREIGN_FLAG_PREFIXES` — it is bsdtar's, and the sentence naming it says so.
