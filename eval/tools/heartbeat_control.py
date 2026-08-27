#!/usr/bin/env python3
"""Can the heartbeat's work-tree guard go red, and can it still go green?

    python3 eval/tools/heartbeat_control.py

`heartbeat.py` refuses to report a count when the MAIN CHECKOUT is not a work tree — the
state `core.bare=true` reaches, and a `core.worktree` pointing nowhere reaches too. This is
the pair of questions `AGENTS.md` rules 1 and 15 ask of that guard: a mutant asks whether it
*can* fail, and the variants ask whether it can still *pass* on inputs it might mishandle.

THE SUBJECT IS A FIXTURE, AND THE LIVE REPOSITORY IS ONLY EVER READ
------------------------------------------------------------------
Row `live_green` runs the real `heartbeat.py` against this checkout and changes nothing. Every
red row is produced in a throwaway repository under `$TMPDIR` instead, because setting
`core.bare` on the real main checkout would, for as long as it stood, stop `git worktree add`,
every merge, and every git command any concurrent session ran there. `tasks/184` asks for the
red direction to restore the flag in a `finally`; the fixture does that too, since a fixture
left bare would poison the rows after it.

THE GUARD IS NOT ASKED TO CONFIRM ITSELF
----------------------------------------
Each row sets the state with `git config` and then reads the answer out of a **fresh
`python3` process**, so acceptance is never mistaken for propagation (`tasks/175`, #202). The
expected text is spelled out here rather than imported from `heartbeat.py`: a control that
builds its expectation by calling its subject has no second statement of the fact to compare
against (`AGENTS.md` rule 12, task 113).

WHAT THE MUTANT ESTABLISHES
---------------------------
`mutant_bare_silent` deletes the guard call and runs the result against the broken fixture.
It must exit **0 with a full count block** — which is not only "the check can fail", it is
the pre-fix behaviour reproduced: `heartbeat.py` printed byte-identical output in a bare
checkout and in a healthy one, at exit 0 both times, while `git status` beside it exited 128.

WHAT IT DOES NOT COVER
----------------------
It does not ask what set `core.bare` in the incident behind `tasks/184`. That cause is
unestablished and the ticket says explicitly not to spend itself hunting it — the guard is
worth more than the attribution.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parents[1]

#: The 3 things every refusal has to say, stated here and NOT read from `heartbeat.py`.
#: `tasks/184`: the guard "names `core.bare` and states the one-line repair in its own output,
#: so the next session reads the fix rather than deriving it". The refusal prints BOTH keys it
#: knows about whichever one is set, so a reader who meets the other state still learns that the
#: check looked at it.
WANT_IN_REFUSAL = (
    "NOT A WORK TREE",
    "core.bare",
    "core.worktree",
)


def _clean_env() -> dict[str, str]:
    """The environment with every `GIT_*` variable dropped.

    An inherited `GIT_DIR` steers a child's git at a repository the child never named, which
    `tasks/176` measured writing into a real checkout's index. Nothing here should ever reach
    a repository other than the one its `-C` names.
    """
    return {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """One git command against `repo`, never raising: the exit code IS the measurement here."""
    return subprocess.run(["git", "-C", str(repo), *args],
                          capture_output=True, text=True, env=_clean_env())


def _run_heartbeat(script: Path) -> subprocess.CompletedProcess[str]:
    """A heartbeat in a FRESH process, so it cannot inherit what the caller just set."""
    return subprocess.run([sys.executable, str(script)],
                          capture_output=True, text=True, env=_clean_env())


def _build_fixture(base: Path) -> tuple[Path, Path]:
    """A repository shaped like this one, plus a linked worktree. Returns (main, worktree).

    Only the files `heartbeat.py` reads are populated. `tasks.py` is copied because
    `heartbeat._statuses` imports it by path to get the status vocabulary.
    """
    main = base / "fx"
    for rel in ("eval/tools", "eval/findings", "eval/judge", "tasks", ".claude/skills"):
        (main / rel).mkdir(parents=True, exist_ok=True)
    for name in ("heartbeat.py", "tasks.py"):
        shutil.copy2(TOOLS / name, main / "eval" / "tools" / name)
    (main / "eval/findings/f.md").write_text("## #19 - a finding\n", encoding="utf-8")
    (main / "tasks/001-t.md").write_text(
        "---\nid: 1\ntitle: t\nstatus: todo\npriority: 2\ndone_when: x\n---\n\nbody\n",
        encoding="utf-8")
    (main / "IMPROVEMENTS.md").write_text("x\n", encoding="utf-8")
    (main / "eval/IMPROVEMENTS.md").write_text("x\n", encoding="utf-8")

    subprocess.run(["git", "init", "-q", "-b", "main", str(main)],
                   check=True, capture_output=True, text=True, env=_clean_env())
    _git(main, "config", "user.email", "control@example.invalid")
    _git(main, "config", "user.name", "heartbeat_control")
    _git(main, "add", "-A")
    r = _git(main, "commit", "-qm", "fixture")
    if r.returncode != 0:
        raise SystemExit(f"heartbeat_control: could not build the fixture: {r.stderr.strip()}")

    wt = base / "fx-wt"
    r = _git(main, "worktree", "add", "-q", str(wt), "-b", "linked")
    if r.returncode != 0:
        raise SystemExit(f"heartbeat_control: could not add the linked worktree: "
                         f"{r.stderr.strip()}")
    return main, wt


def _mutant(script: Path) -> Path:
    """`heartbeat.py` with the guard CALL deleted, written beside the original.

    The replacement is asserted to have changed something. A mutant that silently failed to
    apply is a row that passes for the wrong reason, which is the defect this file exists to
    catch elsewhere.
    """
    src = script.read_text(encoding="utf-8")
    call = "    _assert_main_checkout_is_a_work_tree()\n"
    if call not in src:
        raise SystemExit("heartbeat_control: the mutant could not find the guard call "
                         f"{call.strip()!r} in {script} — it has been renamed or removed, so "
                         "no row below is asking what it claims to ask.")
    out = script.with_name("heartbeat_mutant.py")
    out.write_text(src.replace(call, "", 1), encoding="utf-8")
    return out


def _refused(r: subprocess.CompletedProcess[str], want: list[str]) -> tuple[bool, list[str]]:
    """Did this run refuse, and refuse with exactly the lines a repair needs? -> (ok, missing).

    TWO THINGS BEYOND THE EXIT CODE, both of which a row asserting less would let through.

    **Nothing on stdout.** The guard's own refusal ends *"No count is reported"*, and a row
    that checks only the exit code cannot see that promise break: move the guard below
    `collect()` and every count is printed, the process still exits nonzero, and the row goes
    on passing while an unusable checkout produces a number. Counts are the thing being
    guarded, so their absence is part of the claim.

    **WHOLE LINES, not fragments.** A repair naming the WRONG checkout still contains the
    right path, because the diagnostic header above it names the right one -- so
    `str(main_ck) in stderr` and `"config core.bare false" in stderr` can both be true of a
    command pointed somewhere else. `AGENTS.md` rule 12: the address is an input to the check,
    and a caller passes the full `git -C <path> config ...` line it expects. Both raised by
    CodeRabbit on PR #64.
    """
    missing = [w for w in want if w not in r.stderr]
    if r.stdout:
        missing.append(f"stdout should be empty, carries {len(r.stdout)} bytes")
    return (r.returncode != 0 and not missing), missing


def main() -> int:
    """Run every row, print each with its measurement, and exit 1 if any came out wrong."""
    rows: list[tuple[str, bool, str]] = []

    def row(name: str, ok: bool, note: str) -> None:
        """Record one row: its name, whether it came out as expected, and what was read."""
        rows.append((name, ok, note))

    # ---- the known-good row: the live repository, read and not touched -------------------
    r = _run_heartbeat(TOOLS / "heartbeat.py")
    row("live_green", r.returncode == 0 and "project_lines=" in r.stdout,
        f"this checkout, unmodified: exit {r.returncode}")

    # RESOLVED, and that is not tidiness. On darwin `$TMPDIR` is `/var/folders/...`
    # while `/var` is a symlink to `/private/var`, so `git worktree list` reports the
    # resolved path and `mkdtemp` returns the unresolved one -- two addresses for one
    # directory, which is `AGENTS.md` rule 12. The whole-line assertions below compare
    # this path against what git prints, so they must be the same spelling.
    base = Path(tempfile.mkdtemp(prefix="heartbeat_control_")).resolve()
    try:
        main_ck, wt = _build_fixture(base)
        hb_main = main_ck / "eval" / "tools" / "heartbeat.py"
        hb_wt = wt / "eval" / "tools" / "heartbeat.py"
        mutant = _mutant(hb_main)

        # ---- green: the three states in which the main checkout IS a work tree -----------
        r = _run_heartbeat(hb_main)
        row("fixture_false_green", r.returncode == 0 and "project_lines=" in r.stdout,
            f"core.bare=false, run in the main checkout: exit {r.returncode}")

        healthy = r.stdout

        r = _run_heartbeat(hb_wt)
        row("linked_worktree_green", r.returncode == 0 and "project_lines=" in r.stdout,
            f"core.bare=false, run in a LINKED WORKTREE: exit {r.returncode}")

        _git(main_ck, "config", "--unset", "core.bare")
        try:
            r = _run_heartbeat(hb_main)
            row("fixture_unset_green", r.returncode == 0 and "project_lines=" in r.stdout,
                f"core.bare absent — the third value: exit {r.returncode}")
        finally:
            _git(main_ck, "config", "core.bare", "false")

        # ---- red: the main checkout is bare ---------------------------------------------
        _git(main_ck, "config", "core.bare", "true")
        try:
            # Every line a reader needs in order to repair THIS checkout, spelled whole.
            want_bare = [*WANT_IN_REFUSAL, f"    {main_ck}\n",
                         "    core.bare        = true\n",
                         f"    git -C {main_ck} config core.bare false\n"]

            # The state is set here and read by a process that did not set it.
            r = _run_heartbeat(hb_main)
            ok, missing = _refused(r, want_bare)
            row("bare_red_from_main", ok,
                f"exit {r.returncode}; missing from the refusal: {missing or 'nothing'}")

            # The variant a naive probe misses: from a linked worktree `git rev-parse
            # --is-bare-repository` answers `false`, and everything the agent does still
            # works. That second half is asserted rather than only printed — it is the
            # reason no git hook can carry this check, and a row that merely reported it
            # would go on passing if linked worktrees stopped working.
            wt_status = _git(wt, "status", "--porcelain")
            r = _run_heartbeat(hb_wt)
            ok, missing = _refused(r, want_bare)
            row("bare_red_from_linked_worktree", ok and wt_status.returncode == 0,
                f"exit {r.returncode} while `git status` in that worktree is exit "
                f"{wt_status.returncode}; missing: {missing or 'nothing'}")

            # The mutant: the pre-fix behaviour, reproduced.
            r = _run_heartbeat(mutant)
            row("mutant_bare_silent", r.returncode == 0 and r.stdout == healthy,
                f"guard call deleted: exit {r.returncode}, output "
                f"{'identical to the healthy run' if r.stdout == healthy else 'DIFFERS'}")
        finally:
            _git(main_ck, "config", "core.bare", "false")

        # ---- red: the SECOND way to reach the identical symptom -------------------------
        # `core.worktree` at a directory that does not exist. `git status` exits 128 with the
        # same message and `git ls-files` still exits 0, but `git worktree list` prints an
        # ordinary NON-BARE record -- so the marker this check first read cannot see it, and
        # the shipped `--is-inside-work-tree` probe can. Raised by CodeRabbit on PR #64.
        gone = base / "gone-work-tree"
        _git(main_ck, "config", "core.worktree", str(gone))
        try:
            status = _git(main_ck, "status", "--porcelain")
            marker = _git(main_ck, "worktree", "list", "--porcelain")
            r = _run_heartbeat(hb_main)
            ok, missing = _refused(r, [
                *WANT_IN_REFUSAL, f"    {main_ck}\n",
                "    core.bare        = false\n",
                f"    core.worktree    = {gone}\n",
                f"    git -C {main_ck} config --unset core.worktree\n"])
            # `marker.returncode == 0` IS PART OF THE CLAIM, not housekeeping. A failed
            # `git worktree list` returns empty stdout, and `"bare" not in ""` is true — so
            # without it this row could pass by the probe erroring rather than by the marker
            # being absent, which is a reason not to count a failure (`AGENTS.md` rule 7).
            # Raised by CodeRabbit on PR #64.
            row("core_worktree_missing_red",
                ok and status.returncode == 128 and marker.returncode == 0
                and "bare" not in marker.stdout.split("\n\n")[0],
                f"exit {r.returncode} while `git status` there is exit {status.returncode} "
                f"and `git worktree list` (exit {marker.returncode}) reports no `bare` "
                f"marker; missing: {missing or 'nothing'}")
        finally:
            _git(main_ck, "config", "--unset", "core.worktree")

        # The two `finally` blocks above are the whole reason this row can run at all.
        st = _git(main_ck, "status", "--porcelain")
        row("fixture_restored", st.returncode == 0,
            f"`git status` in the fixture main checkout after the red rows: exit "
            f"{st.returncode}")

        # ---- red: git will not answer at all --------------------------------------------
        # A heartbeat outside any repository must refuse rather than report. `_tracked_files`
        # would have raised a traceback here before; the guard now names the cause first.
        loose = base / "loose"
        (loose / "eval" / "tools").mkdir(parents=True)
        shutil.copy2(hb_main, loose / "eval" / "tools" / "heartbeat.py")
        shutil.copy2(main_ck / "eval/tools/tasks.py", loose / "eval" / "tools" / "tasks.py")
        r = _run_heartbeat(loose / "eval" / "tools" / "heartbeat.py")
        ok, missing = _refused(r, ["`git worktree list` failed", "No count is reported"])
        row("not_a_repo_red", ok,
            f"no repository at the root: exit {r.returncode}; missing: {missing or 'nothing'}")
    finally:
        shutil.rmtree(base, ignore_errors=True)

    width = max(len(n) for n, _, _ in rows)
    bad = 0
    for name, ok, note in rows:
        if not ok:
            bad += 1
        print(f"{'ok  ' if ok else 'RED '} {name:<{width}}  {note}")
    print(f"\n{len(rows) - bad} / {len(rows)} rows as expected")
    if bad:
        print("A row above did not come out as expected. The heartbeat's work-tree guard "
              "is not doing what this control says it does.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
