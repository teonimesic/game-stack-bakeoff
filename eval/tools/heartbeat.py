#!/usr/bin/env python3
"""The hourly heartbeat's measurement, as a file rather than a shell string in a monitor.

WHY THIS EXISTS
---------------
The heartbeat answers one question: *is new work actually happening to improve the judges
and the templates?* It answers it by printing a handful of counts, and the caller diffs
them against the previous hour.

It lived as an inline shell command inside a background monitor. Two things were wrong
with that, and the second one bit:

1. It was an instruction that lived in a message, not a file. Nothing in the repository
   recorded what the heartbeat measured, so nobody could correct it, and it would have
   died with the session -- the exact failure `AGENTS.md` names.

2. `project_lines` counted every line under the project root. On 2026-08-22 the queue
   moved to one-agent-per-task in isolated git worktrees under `.claude/worktrees/`, and
   the count went 65,107 -> 327,795 in one hour. Four checkouts of the same code read as
   a fivefold explosion of work. **A metric that moves for reasons unrelated to the thing
   it measures is worse than no metric, because the movement gets acted on.**

THE FIX IS A DEFINITION, NOT AN EXCLUSION
-----------------------------------------
`project_lines` is now the line count of **git-tracked files**. Worktrees, build output,
`eval/runs/` and every future generated directory are excluded because they are not
tracked -- not because they appear on a list. This project's most-repeated defect is a
rule whose trigger is an enumeration: it misses the first case that was not present when
it was written. `git ls-files` cannot miss one.

The same reasoning applies to `findings`: it counts `## #NN` headings, which is what a
finding IS, rather than lines in a file that also holds prose.

Every count here is a proxy. None of them says the work was any GOOD -- only that
something moved. That judgement belongs to whoever reads the diff.

THE SERIES RESETS HERE, AND THAT IS NOT A BUG TO ROUTE AROUND
-------------------------------------------------------------
`project_lines` under the old shell command read 65,107; under the tracked-files
definition it reads 199,717. **The first hour's diff across this change is meaningless
and must not be read as work.** Neither number is wrong -- they count different things,
and the old command's definition was never written down anywhere, which is why it is not
reproduced here. Comparisons are valid from this commit forward only.

`findings` and the task counts are unaffected: both were verified to reproduce the old
command's values exactly (71 findings, highest #89, matching the documented #19-#89 range
with no gaps).

    python3 eval/tools/heartbeat.py          # key=value lines, one per metric
    python3 eval/tools/heartbeat.py --json
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _tracked_files() -> list[Path]:
    """Git-tracked files only.

    This is the whole defence against the worktree inflation. Agent worktrees live under
    `.claude/worktrees/`, which is gitignored, so they are absent here by construction.
    Fails loudly rather than returning a plausible zero -- an empty list would read as
    "the project has no code", which is exactly the shape of a broken check that produces
    an in-range number.
    """
    out = subprocess.run(
        ["git", "-C", str(ROOT), "ls-files", "-z"],
        capture_output=True, text=True, check=True,
    )
    return [ROOT / p for p in out.stdout.split("\0") if p]


def _count_lines(paths: list[Path]) -> int:
    total = 0
    for p in paths:
        try:
            with open(p, "rb") as fh:
                total += fh.read().count(b"\n")
        except (OSError, FileNotFoundError):
            # A tracked file that is absent from the working tree is a real condition
            # (partial checkout, mid-rebase). Skipping it is right; hiding it is not.
            print(f"heartbeat: tracked but unreadable: {p}", file=sys.stderr)
    return total


def _findings() -> tuple[int, int]:
    """(distinct finding numbers, highest number).

    A finding is a level-2 heading under `eval/findings/`. TWO forms are in use and both
    count -- this was written with only the first and reported 7 findings against a real
    71, which is the failure this project exists to avoid, caught only because the number
    was checked against a range someone remembered:

        ## #19 - ...   the original style, findings 19-25
        ## 26. ...     the current style, findings 26 onward

    Continuations (`### #31, continued`) are level 3 and deliberately do NOT count. They
    are more evidence for an existing finding, and counting them would raise the number
    every time an old finding got deeper rather than when a new one was found.

    The heading style has already changed once. If it changes again this undercounts
    silently, so `findings_highest` is reported alongside: when the count and the highest
    number drift apart, the pattern has stopped matching something.
    """
    nums: set[int] = set()
    for p in sorted((ROOT / "eval" / "findings").glob("*.md")):
        for m in re.finditer(r"^##\s+#?(\d+)[.\s]", p.read_text(encoding="utf-8"), re.M):
            nums.add(int(m.group(1)))
    return len(nums), (max(nums) if nums else 0)


def _tasks() -> dict[str, int]:
    counts = {"open": 0, "in_flight": 0, "done": 0}
    for p in sorted((ROOT / "tasks").glob("*.md")):
        m = re.search(r"^status:\s*(\S+)", p.read_text(encoding="utf-8"), re.M)
        if m and m.group(1) in counts:
            counts[m.group(1)] += 1
    return counts


def _results() -> dict[str, int]:
    """Counts of OUTPUTS, not source.

    These are the most important metrics here and the ones most easily lost. Judge rounds
    land as JSON *inside existing run directories*, so they move neither a directory count
    nor any source-line count. An hour in which ten rounds landed was reported as "NO NEW
    WORK" because the snapshot counted only source.

    That was the THIRD time an enumerated snapshot missed the next location -- after
    `launch.just` (missed because the file list went by extension) and `eval/tools`
    (missed because the list went by directory). Counting what the work PRODUCES closes
    the class, where adding one more directory to a list would only have postponed it.

    `eval/runs/` is deliberately untracked and large, so these are read from disk rather
    than from git. That is the one place a filesystem walk is the right instrument.
    """
    runs = ROOT / "eval" / "runs"
    if not runs.is_dir():
        return {"runs": 0, "judge_rounds": 0, "graded_submissions": 0}
    return {
        "runs": sum(1 for p in runs.glob("wg-*") if p.is_dir()),
        "judge_rounds": sum(1 for _ in runs.rglob("*__seed*.json")),
        "graded_submissions": sum(1 for _ in runs.rglob("report.json")),
    }


def _criteria() -> int:
    """Distinct criterion ids across the play-bots and the programmatic checks."""
    ids: set[str] = set()
    judge = ROOT / "eval" / "judge"
    for p in list(judge.glob("bot_*.py")) + [judge / "checks.py"]:
        if p.exists():
            ids.update(re.findall(r'"([a-z]+\.[a-z_]+)"', p.read_text(encoding="utf-8")))
    return len(ids)


def collect() -> dict[str, int]:
    tracked = _tracked_files()
    n_findings, highest = _findings()
    tasks = _tasks()

    def _lines_under(rel: str) -> int:
        return _count_lines([p for p in tracked
                             if p.suffix == ".py" and rel in p.as_posix()])

    m = {
        "findings": n_findings,
        "findings_highest": highest,
        "tasks_open": tasks["open"],
        "tasks_inflight": tasks["in_flight"],
        "tasks_done": tasks["done"],
        "judge_code": _lines_under("eval/judge/"),
        "tools_code": _lines_under("eval/tools/"),
        "criteria": _criteria(),
        "skills": sum(1 for p in (ROOT / ".claude" / "skills").glob("*")
                      if (p / "SKILL.md").exists()),
        "improv_eval": _count_lines([ROOT / "eval" / "IMPROVEMENTS.md"]),
        "improv_root": _count_lines([ROOT / "IMPROVEMENTS.md"]),
        "project_lines": _count_lines(tracked),
        "tracked_files": len(tracked),
    }
    m.update(_results())
    return m


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    m = collect()
    if a.json:
        print(json.dumps(m, indent=2))
    else:
        for k, v in m.items():
            print(f"{k}={v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
