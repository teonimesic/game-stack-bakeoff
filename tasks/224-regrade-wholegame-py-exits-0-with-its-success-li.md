---
id: 224
title: regrade_wholegame.py exits 0 with its success line on a run dir holding no reports
status: in_progress
priority: 4
refs: eval/judge/regrade_wholegame.py
done_when: '1. A run dir that does not exist, and one holding no artifacts/*/eval/report.json, each exit nonzero and do not print the success line; a real run dir in dry-run still exits 0 and its output is unchanged. 2. Controls are run and recorded in the ticket: the two failing shapes above, the real-dir positive control (eval/runs/wg-scene-s1ts-2026-08-25 dry-run), and the regime guard unchanged - eval/runs/wg-matrix-2026-08-13T14-02-50 dry-run still holds back 24 with the LEFT ALONE message. 3. Dry-run still writes nothing (mtime+size of a report.json unchanged across a run). 4. Whatever check is added (selftest or fixture) fails if the guard is removed - a mutant proves the check can fail. 5. eval/tools/docstat.py --sweep and --renumbered and eval/tools/tasks.py check all exit 0 at the branch head.'
---

WHAT IT IS: eval/judge/regrade_wholegame.py is the offline re-scoring path - it rebuilds report.json's overall from the stored per-tier JSON files instead of re-running anything; README.md:292, eval/RUNS.md (twice) and eval/AGENTS.md:171 ('prefer offline re-grading to any re-run') all send readers to it, and it mutates stored evidence under --write.

WHAT IS WRONG, MEASURED 2026-08-30 against HEAD a26c7ac: pointed at a run directory holding no reports - and at a path that does not exist - it prints the empty table plus '0 report(s) inspected (dry run; pass --write)' and EXITS 0, on both shapes. I reproduced both unpiped:

  python3 eval/judge/regrade_wholegame.py /tmp/empty-run-ctl      -> exit 0, success line
  python3 eval/judge/regrade_wholegame.py /tmp/no-such-run-dir-xyz -> exit 0, success line

The three states - missing dir, dir with no artifacts, real run dir - are indistinguishable from the output, and exit 0 reads as completion. With --write the failure direction is the worst one available to this tool: a regrade believed done was not done. This is the repository's one pattern - a mechanism that runs, reports success, and measures nothing - and the rule-3 sibling: a success read from a path structurally incapable of producing one.

WHY IT MATTERS: the sibling tools refuse exactly this input. weight_sensitivity.py exits 1 with 'no stored tier scores found in the given runs' on an empty population; tier1_census.py requires --runs-root and names the worktree-zero failure it refuses. This file has neither guard nor any selftest anywhere (grep: nothing exercises it; its only pins are doc references), so nothing would catch a regression here either.

WHAT MUST STILL FAIL AFTER THE FIX: an invocation whose run-dir resolves to no artifacts/*/eval/report.json must not exit 0 carrying the success line. Either shape the siblings use satisfies this ticket - refuse a missing/empty path up front, or exit nonzero on the empty population - the agent chooses the mechanism. The three states do not have to be distinguished from each other; they must be distinguishable from success.
