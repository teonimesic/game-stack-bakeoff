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

THE MAIN CHECKOUT MUST BE A WORK TREE, AND NOTHING ELSE ASKS
------------------------------------------------------------
Every git command in a main checkout that is not a work tree fails, every working file
stays normal, and every count below is byte-identical to a healthy run — so this script
could not tell the two apart, and nothing else looks (`tasks/184`). `collect` refuses
before counting anything and prints the one-line repair.
`_assert_main_checkout_is_a_work_tree` holds the measurement, the two settings that reach
that state, and why no git hook can carry this check.

AND THE COPY THAT RUNS MUST BE THAT CHECKOUT'S
----------------------------------------------
The work-tree assertion verifies the checkout git names as the main one; the counts then
read ROOT -- the tree the RUNNING COPY lives in. Nothing compared the two (`tasks/229`):
from a linked worktree's copy, agent worktrees being full checkouts, the assertion passed
and every count went branch-local, plausible and wrong -- work landing on any other
branch read as work disappearing, and `eval/runs/` being untracked, a fresh worktree
reported 0 runs, 0 judge rounds and 0 graded submissions (measured before the fix: exit
0, `runs=0`, against a main checkout holding 16, 97 and 85). `_assert_root_is_main_
checkout` compares the two addresses and refuses, naming both, and is asked FIRST -- so a
worktree copy is answered with both addresses even when the main checkout is broken too.
`heartbeat_control.py`
pins it in both directions and carries the mutant that deletes the call.

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


def _main_checkout_path() -> str:
    """Where the main checkout is, asked from wherever this is running.

    `git worktree list --porcelain` prints one blank-line-separated record per worktree and
    the MAIN one first, so this answers the same from the main checkout and from any linked
    worktree. It is also the only probe here that keeps working in every broken state below:
    it needs no work tree, and it exits 0 whether `core.bare` is true, false or absent.
    """
    out = subprocess.run(
        ["git", "-C", str(ROOT), "worktree", "list", "--porcelain"],
        capture_output=True, text=True,
    )
    if out.returncode != 0:
        raise SystemExit(
            f"heartbeat: `git worktree list` failed in {ROOT} (exit {out.returncode}).\n"
            f"{out.stderr.strip()}\n"
            "No count is reported: they would be counts of a repository git will not describe."
        )
    for line in out.stdout.split("\n\n", 1)[0].splitlines():
        if line.startswith("worktree "):
            return line[len("worktree "):]
    raise SystemExit(
        "heartbeat: `git worktree list --porcelain` named no worktree in its first record, "
        f"so the main checkout could not be identified from {ROOT}. It printed:\n"
        f"{out.stdout.strip()!r}"
    )


def _config(repo: str, key: str) -> str:
    """One config value, or `<unset>`. Exit 1 from `--get` means absent, not an error."""
    out = subprocess.run(["git", "-C", repo, "config", "--get", key],
                         capture_output=True, text=True)
    return out.stdout.strip() if out.returncode == 0 and out.stdout.strip() else "<unset>"


def _assert_main_checkout_is_a_work_tree(main: str) -> None:
    """The main checkout must be a work tree, and nothing else here notices when it is not.

    `core.bare` went true in the main checkout's `.git/config` on 2026-08-27 (`tasks/184`).
    Every git command run there failed with `fatal: this operation must be run in a work tree`,
    and the repair was one line. What makes it worth a standing check is the asymmetry: git is
    loud and everything else is silent, because every working file is present and unchanged.
    Measured in a throwaway repository in that state, `git status` exits 128 while `git
    ls-files` exits 0 listing the index -- and `heartbeat.py` exited 0 printing output
    BYTE-IDENTICAL to the healthy run, because `_tracked_files` asks `git ls-files` and
    `_count_lines` opens paths on the filesystem.

    THE PROPERTY IS "GIT CAN OPERATE ON A WORK TREE THERE", NOT "core.bare IS FALSE".
    The first version of this check read the `bare` marker out of `git worktree list`, which is
    the vocabulary of the one incident that produced it rather than the property it protects
    (`AGENTS.md`, the rule audit). A second setting reaches the identical symptom and that
    marker cannot see it: with `core.worktree` pointing at a directory that does not exist,
    `git worktree list` prints an ordinary non-bare record, `git status` still exits 128 with
    the same message, `git ls-files` still exits 0, and the marker check passed. So the probe
    is `git rev-parse --is-inside-work-tree`, asked AT the main checkout, which answers `false`
    in both states and in any third one that has the same effect. Raised by CodeRabbit on
    PR #64.

    Asked AT the main checkout, because the answer is about a place: run in a linked worktree
    it says `true` while the main checkout is unusable. That is also the case a naive probe
    misses, since linked worktrees go on working -- `status`, `commit`, `ls-files` and
    `rev-parse --show-toplevel` in one were all exit 0 against a bare main checkout.

    WHY THIS IS HERE RATHER THAN IN `.githooks/run-gates.sh`. The hook cannot fire in the state
    it would detect: in the same fixture `git commit` exited 128 and the `pre-commit` hook
    printed nothing, so no hook runs at all in a main checkout that is not a work tree. A hook
    guard would therefore only ever be reached from a linked worktree, where the state is
    invisible. Duty cycle argues the same way and more weakly: the flip appeared while nothing
    was committing, and the heartbeat runs hourly regardless.
    """
    path = main
    probe = subprocess.run(["git", "-C", path, "rev-parse", "--is-inside-work-tree"],
                           capture_output=True, text=True)
    if probe.returncode == 0 and probe.stdout.strip() == "true":
        return

    # REPORTED AS FACTS, not branched on. Which of these is the cause decides only which
    # repair is printed; the refusal itself is the same one, so there is no second path
    # through here to get wrong. `directory exists` is in the census because a main checkout
    # that has been moved or deleted reaches this with both keys unreadable.
    bare = _config(path, "core.bare")
    worktree = _config(path, "core.worktree")
    exists = "yes" if Path(path).is_dir() else "NO"
    if bare == "true":
        repair = f"git -C {path} config core.bare false"
    elif worktree != "<unset>":
        repair = f"git -C {path} config --unset core.worktree"
    else:
        repair = (f"read {path}/.git/config -- neither `core.bare` nor `core.worktree` "
                  "explains this, so the repair is not one this check can name")
    raise SystemExit(
        "heartbeat: THE MAIN CHECKOUT IS NOT A WORK TREE.\n"
        f"\n    {path}\n\n"
        "`git rev-parse --is-inside-work-tree` answers "
        f"{(probe.stdout.strip() or probe.stderr.strip())!r} there.\n"
        "Every git command run in it fails with `fatal: this operation must be run in a work "
        "tree`,\nwhile every working file is present and unchanged -- so nothing but git "
        "reports it, and\nlinked worktrees go on working, which is why no agent will notice.\n"
        "\nWhat that address says for itself:\n"
        f"\n    directory exists = {exists}\n    core.bare        = {bare}\n"
        f"    core.worktree    = {worktree}\n"
        "\nRepair, one line:\n"
        f"\n    {repair}\n"
        "\nNo count is reported: they would be counts of a checkout nobody can commit to or "
        "merge into."
    )


def _assert_root_is_main_checkout(root: Path, main: str) -> None:
    """The copy that runs must BE the main checkout's, and this is the only check that asks.

    `_assert_main_checkout_is_a_work_tree` verifies the checkout git names as the main one;
    `collect` then counts ROOT, derived from `__file__` -- the tree the RUNNING COPY lives
    in. Nothing compared the two (`tasks/229`). Run from a linked worktree's copy -- and
    agent worktrees are full checkouts -- the work-tree assertion passed, because the main
    checkout IS a work tree, and every count went branch-local: findings, the task counts
    and `project_lines` became plausible and wrong, which reads as work disappearing, and
    `eval/runs/` is untracked so a fresh worktree reported 0 runs, 0 judge rounds and
    0 graded submissions. Measured before the fix, from a worktree copy of this file:
    exit 0 with `runs=0` while the main checkout held 16 runs, 97 judge rounds and 85
    graded submissions. The fivefold jump of 2026-08-22 was worktrees counted TWICE; this
    was the same defect one step later -- worktrees counted INSTEAD.

    THE PROPERTY IS THE INVOCATION ADDRESS, not the metric. `project_lines`'s tracked-files
    definition excludes worktrees from the MAIN checkout's count by construction, but which
    tree is counted at all is decided by which copy of this file was invoked -- a property
    of the address, and only a comparison of two addresses can hold it (`AGENTS.md`,
    rule 12). `main` is already computed, by `_main_checkout_path`, for the work-tree
    assertion; the defect was that nothing asked whether this copy lives there.

    `heartbeat_control.py` pins this refusal in both directions, from the live repository
    and from a fixture, and carries the mutant that deletes the call below -- the pre-fix
    behaviour, reproduced on demand.

    IT RUNS BEFORE THE WORK-TREE PROBE. A worktree copy with a broken main checkout is
    answered HERE, with both addresses, rather than by a refusal about the checkout that
    names only the checkout: run the right copy first, and the next refusal, if one still
    fires, fires where ROOT is the main checkout and its address is the running copy's.
    """
    if Path(root).resolve() == Path(main).resolve():
        return
    raise SystemExit(
        "heartbeat: THIS COPY IS NOT THE MAIN CHECKOUT'S.\n"
        "\n"
        f"    this copy (ROOT, from __file__):   {Path(root).resolve()}\n"
        f"    main checkout (git worktree list): {Path(main).resolve()}\n"
        "\n"
        "Every count would be THIS tree's, not the project's: findings, the task counts\n"
        "and `project_lines` would read branch-local, so work landing anywhere else reads\n"
        "as work disappearing -- and `eval/runs/` is untracked, so a fresh worktree\n"
        "reports no runs, no judge rounds and no graded submissions at all.\n"
        "\n"
        "Repair, one line -- run the main checkout's copy:\n"
        f"\n"
        f"    python3 {Path(main).resolve()}/eval/tools/heartbeat.py\n"
        "\n"
        "No count is reported: a count of one branch, read as the whole project, is the\n"
        "shape of a number that gets acted on."
    )


def _tracked_files() -> list[Path]:
    """Git-tracked files only.

    This is the defence against the worktree inflation AT THE ADDRESS THAT COUNTS: agent
    worktrees live under `.claude/worktrees/`, which is gitignored, so they are absent
    here by construction. That they never count anywhere else is the address refusal's
    job -- `_assert_root_is_main_checkout` stops the run before this is reached from the
    wrong copy.
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
        # A TRACKED SYMLINK HAS NO LINES, and it is not an error. `.claude/skills` is a
        # mode-120000 blob pointing at `.agents/skills` (task 114), so `git ls-files`
        # yields it and `open()` follows it to a directory and raises. Skipped SILENTLY
        # and by `is_symlink()` rather than by catching IsADirectoryError, because the
        # two conditions are different: this one is deliberate and permanent, and the
        # warning below exists to surface the other one.
        if p.is_symlink():
            continue
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
    # FIRST, because every metric below is a statement about the main checkout and
    # `git ls-files` answers happily in a bare one. TWO refusals, one address each, and
    # THE ORDER IS LOAD-BEARING: the address comparison runs before the work-tree probe,
    # so a reader in the wrong copy is sent to the right one before anything about the
    # checkout itself is diagnosed -- and every refusal that can then fire names both
    # paths, or fires where ROOT IS the main checkout, so naming main names the running
    # copy. Work-tree first, the order until PR #109's review, refused a worktree copy
    # with a broken main checkout by naming only the main checkout -- and telling the
    # reader that linked worktrees go on working, which that reader would have taken as
    # licence to count branch-local. Either guard alone leaves the other unguarded: the
    # address guard alone would count a bare checkout's index (`tasks/184`), the work-tree
    # guard alone counted branch-local from a worktree (`tasks/229`).
    main = _main_checkout_path()
    _assert_root_is_main_checkout(ROOT, main)
    _assert_main_checkout_is_a_work_tree(main)
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
