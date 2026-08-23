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

THE TASK SERIES DID NOT RESET WHEN THE STATUS VOCABULARY GREW, AND THAT WAS THE POINT
-------------------------------------------------------------------------------------
On 2026-08-23 `tasks.py`'s statuses went from 3 to 5 -- `open`/`in_flight` renamed to
`todo`/`in_progress`, and `in_review`/`in_testing` added for the pull-request flow.
`tasks_open` and `tasks_inflight` KEPT THEIR NAMES, because this file's output is read as a
diff and a renamed key is indistinguishable from a series ending at 0 while another starts
from nothing. Only `tasks_inreview`, `tasks_intesting` and `tasks_unknown` are new, and each
starts at 0, so the first hour across the change is readable rather than meaningless.

The mapping is `TASK_METRIC`, asserted against `tasks.STATUSES` on every run.

    python3 eval/tools/heartbeat.py          # key=value lines, one per metric
    python3 eval/tools/heartbeat.py --json
"""

from __future__ import annotations

import argparse
import importlib.util
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


#: status -> the METRIC KEY it is reported under. Two things are deliberate here.
#:
#: 1. THE KEYS ARE THE OLD NAMES, AND THE STATUSES ARE THE NEW ONES. The vocabulary grew from
#:    3 values to 5 on 2026-08-23 (`todo`/`in_progress`/`in_review`/`in_testing`/`done`). The
#:    heartbeat's whole output is read as a DIFF against the previous hour, and a renamed key
#:    is not a rename to a differ -- it is one series ending at 0 and another starting from
#:    nothing. `tasks_open` going to absent and `tasks_todo` appearing at 6 reads as twelve
#:    tasks' worth of movement in an hour where nothing happened. The series continue.
#: 2. IT IS A MAP, NOT THREE HAND-WRITTEN KEYS, so `collect` cannot report a subset of the
#:    vocabulary. The old code held `{"open", "in_flight", "done"}` and dropped anything else
#:    silently: over a queue holding 1 file in each of the 5 states it counted 3 of 5, so a
#:    ticket moving into review vanished from every counter and the hour read as work
#:    disappearing. `_tasks` now asserts these keys against `tasks.STATUSES` (rule 12: one
#:    value at two addresses is asserted equal in code, never promised in a comment).
TASK_METRIC = {
    "todo": "tasks_open",
    "in_progress": "tasks_inflight",
    "in_review": "tasks_inreview",
    "in_testing": "tasks_intesting",
    "done": "tasks_done",
}


def _statuses() -> tuple[tuple[str, ...], dict[str, str]]:
    """`tasks.py`'s vocabulary and its legacy aliases, IMPORTED rather than restated.

    Imported by path for the reason `tasks_control.py` gives: `sys.path` games reach whatever
    copy happens to be first. If the import fails this raises -- a heartbeat that silently
    fell back to a hardcoded 3-value list would go on printing plausible counts while the
    thing it counts had 5 states, which is the exact defect this replaces.
    """
    spec = importlib.util.spec_from_file_location("tasks_for_heartbeat",
                                                  Path(__file__).resolve().parent / "tasks.py")
    if spec is None or spec.loader is None:
        raise SystemExit("heartbeat.py cannot import eval/tools/tasks.py, which defines the "
                         "status vocabulary it counts")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.STATUSES, mod.LEGACY_STATUSES


def _tasks() -> dict[str, int]:
    """One count per status, keyed by STATUS. `collect` maps them to metric names.

    Unknown values are counted under `""` rather than dropped, and `collect` adds them to no
    metric but the total -- so `tasks_unknown` is what a typo or a status this file has not
    been taught about shows up as, instead of a file that exists in the queue and in none of
    the counts.
    """
    statuses, legacy = _statuses()
    if tuple(TASK_METRIC) != statuses:
        raise SystemExit(f"heartbeat.py's TASK_METRIC covers {tuple(TASK_METRIC)} but "
                         f"tasks.py's STATUSES is {statuses}. A status missing from the map "
                         f"is a task counted by nothing: add it, and give it a metric key.")
    counts: dict[str, int] = {s: 0 for s in statuses}
    counts[""] = 0
    for p in sorted((ROOT / "tasks").glob("*.md")):
        m = re.search(r"^status:\s*(\S+)", p.read_text(encoding="utf-8"), re.M)
        raw = m.group(1) if m else ""
        canonical = legacy.get(raw, raw)
        counts[canonical if canonical in counts else ""] += 1
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
        **{metric: tasks[status] for status, metric in TASK_METRIC.items()},
        "tasks_unknown": tasks[""],
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
