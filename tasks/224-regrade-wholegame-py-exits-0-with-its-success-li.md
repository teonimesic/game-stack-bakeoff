---
id: 224
title: regrade_wholegame.py exits 0 with its success line on a run dir holding no reports
status: in_testing
priority: 4
refs: eval/judge/regrade_wholegame.py
done_when: '1. A run dir that does not exist, and one holding no artifacts/*/eval/report.json, each exit nonzero and do not print the success line; a real run dir in dry-run still exits 0 and its output is unchanged. 2. Controls are run and recorded in the ticket: the two failing shapes above, the real-dir positive control (eval/runs/wg-scene-s1ts-2026-08-25 dry-run), and the regime guard unchanged - eval/runs/wg-matrix-2026-08-13T14-02-50 dry-run still holds back 24 with the LEFT ALONE message. 3. Dry-run still writes nothing (mtime+size of a report.json unchanged across a run). 4. Whatever check is added (selftest or fixture) fails if the guard is removed - a mutant proves the check can fail. 5. eval/tools/docstat.py --sweep and --renumbered and eval/tools/tasks.py check all exit 0 at the branch head.'
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/104
established_by: 'Both failing shapes exit nonzero with no success line (empty dir 1, nonexistent 2, file-not-dir 2); wg-scene-s1ts-2026-08-25 dry-run byte-identical at exit 0; wg-matrix-2026-08-13T14-02-50 still holds back 24 LEFT ALONE byte-identical; report.json mtime+size unchanged, 0 .tmp; selftest 28/28 with a source-excision mutant that flips all 6 refusal rows red, and the selftest ran red first (20/29) on the unfixed tool; sweep, renumbered, tasks check, ci_minutes --selftest, lint all exit 0 at head 7e294bf. PR #104.'
---

WHAT IT IS: eval/judge/regrade_wholegame.py is the offline re-scoring path - it rebuilds report.json's overall from the stored per-tier JSON files instead of re-running anything; README.md:292, eval/RUNS.md (twice) and eval/AGENTS.md:171 ('prefer offline re-grading to any re-run') all send readers to it, and it mutates stored evidence under --write.

WHAT IS WRONG, MEASURED 2026-08-30 against HEAD a26c7ac: pointed at a run directory holding no reports - and at a path that does not exist - it prints the empty table plus '0 report(s) inspected (dry run; pass --write)' and EXITS 0, on both shapes. I reproduced both unpiped:

  python3 eval/judge/regrade_wholegame.py /tmp/empty-run-ctl      -> exit 0, success line
  python3 eval/judge/regrade_wholegame.py /tmp/no-such-run-dir-xyz -> exit 0, success line

The three states - missing dir, dir with no artifacts, real run dir - are indistinguishable from the output, and exit 0 reads as completion. With --write the failure direction is the worst one available to this tool: a regrade believed done was not done. This is the repository's one pattern - a mechanism that runs, reports success, and measures nothing - and the rule-3 sibling: a success read from a path structurally incapable of producing one.

WHY IT MATTERS: the sibling tools refuse exactly this input. weight_sensitivity.py exits 1 with 'no stored tier scores found in the given runs' on an empty population; tier1_census.py requires --runs-root and names the worktree-zero failure it refuses. This file has neither guard nor any selftest anywhere (grep: nothing exercises it; its only pins are doc references), so nothing would catch a regression here either.

WHAT MUST STILL FAIL AFTER THE FIX: an invocation whose run-dir resolves to no artifacts/*/eval/report.json must not exit 0 carrying the success line. Either shape the siblings use satisfies this ticket - refuse a missing/empty path up front, or exit nonzero on the empty population - the agent chooses the mechanism. The three states do not have to be distinguished from each other; they must be distinguishable from success.

## note 2026-08-30

## Account, 2026-08-30 (branch task-224-regrade-refuses-empty, PR #104, head 7e294bf)

**Repair.** Two refusals in `eval/judge/regrade_wholegame.py`, shaped on the siblings the
ticket named: a path that is not a directory exits 2 with `no run directory at <path>` on
stderr (tier1_census.py's missing-store shape); a directory the glob reads nothing out of
exits 1 with `no report(s) found under <path> (want artifacts/*/eval/report.json)` (the
weight_sensitivity.py empty-population shape). The success line is never printed on either.
The regime guard is untouched.

**Controls, all unpiped, all recorded here per done-when 2.**

- Failing shape 1, existing dir with no reports: before `exit 0` + success line; after
  `exit 1`, message on stderr, no success line. (/tmp/empty-run-ctl224)
- Failing shape 2, nonexistent dir: before `exit 0` + success line; after `exit 2`,
  path named on stderr. (/tmp/no-such-run-dir-xyz-224)
- Third shape, free: run-dir argument resolving to a plain file exits 2.
- Positive control, `eval/runs/wg-scene-s1ts-2026-08-25` dry-run: exit 0, output
  byte-identical to the pre-fix capture (diff clean, 1 report inspected).
- Regime guard, `eval/runs/wg-matrix-2026-08-13T14-02-50` dry-run: exit 0, still 24 held
  back with the LEFT ALONE message, output byte-identical to the pre-fix capture.
  `--accept-regime-change` without `--write` still reads `24 report(s) inspected` at exit 0.
- Dry-run writes nothing: `artifacts/s1_parallax__ts__t0/eval/report.json` mtime 1787688789
  size 24463 unchanged across every run before and after; 0 `.tmp` files left in either run dir.

**Check and mutant (done-when 4).** The tool carries `--selftest`: 28 offline expectations on
fixtures it writes (0.8s, no corpus, no `just`): the three refusal shapes, the green dry-run
and `--write` paths, the regime guard, and the mutant that excises both refusals out of the
tool's own source by marked-block regex and must turn them red - 6 behavioural rows read the
mutated copy answering exit 0 with the success line on every refusal shape. Run RED FIRST
against the unfixed tool: 20/29 held, failures exactly the shipped defect, so the check
detects the defect on the real shipped code and not only on the mutant.

One expectation built and then removed: asserting the mutated source no longer contains the
guard's message strings searches for a string the selftest's own code carries, so the search
finds the searcher (task 113's shared-object trap one level down). The behavioural mutant
rows are the load-bearing pin; the only structural row left is `mutation changed the source`.

**CI wiring** (register discipline: a check nothing runs is the defect this gate exists for):
`regrade_wholegame --selftest` added to gates.yml; register count and coverage sentence
73 → 74; `ci_minutes --selftest` pins moved to 30 scripts declaring a `--selftest` mode / 29
tier-named, with task 224 added to that comment's precedent list.

**Gates at the staged head** (done-when 5): selftest 28/28, ci_minutes --selftest (124
mutants died, 80 variants passed), lint.py --gate --rule invalid-syntax 0 findings,
docstat --sweep clean over 291 docs, docstat --renumbered exit 0, tasks.py check 223 tasks
all well-formed - all exit 0, run after staging with the status check on both sides.

**For the orchestrator:** the defect (exit 0 + success line on a path holding no reports,
2026-08-30, HEAD a26c7ac) matches the class the findings log exists for; it needs a number
if you want it in `eval/FINDINGS.md` - not allocated here, per the hand-back rule.
