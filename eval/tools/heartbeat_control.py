#!/usr/bin/env python3
"""Can the heartbeat's work-tree guard go red, and can it still go green?

    python3 eval/tools/heartbeat_control.py

`heartbeat.py` refuses to report a count when the MAIN CHECKOUT is not a work tree
(`core.bare` true). This is the pair of questions `AGENTS.md` rules 1 and 15 ask of that
guard: a mutant asks whether it *can* fail, and the variants ask whether it can still *pass*
on inputs it might mishandle.

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
`mutant_bare_silent` deletes the guard call and runs the result against the bare fixture. It
must exit **0 with a full count block** — which is not only "the check can fail", it is the
pre-fix behaviour reproduced: on 2026-08-27 `heartbeat.py` printed byte-identical output in a
bare checkout and in a healthy one, at exit 0 both times, while `git status` beside it exited
128.

WHAT IT DOES NOT COVER
----------------------
It does not ask what set `core.bare`. That cause is unestablished and `tasks/184` says
explicitly not to spend the ticket hunting it — the guard is worth more than the attribution.
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

#: The four things the refusal has to say, stated here and NOT read from `heartbeat.py`.
#: `tasks/184`: the guard "names `core.bare` and states the one-line repair in its own output,
#: so the next session reads the fix rather than deriving it".
WANT_IN_REFUSAL = (
    "NOT A WORK TREE",
    "core.bare",
    "config core.bare false",
)


def _clean_env() -> dict[str, str]:
    """The environment with every `GIT_*` variable dropped.

    An inherited `GIT_DIR` steers a child's git at a repository the child never named, which
    `tasks/176` measured writing into a real checkout's index. Nothing here should ever reach
    a repository other than the one its `-C` names.
    """
    return {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", "-C", str(repo), *args],
                          capture_output=True, text=True, env=_clean_env())


def _run_heartbeat(script: Path) -> subprocess.CompletedProcess[str]:
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


def main() -> int:
    rows: list[tuple[str, bool, str]] = []

    def row(name: str, ok: bool, note: str) -> None:
        rows.append((name, ok, note))

    # ---- the known-good row: the live repository, read and not touched -------------------
    r = _run_heartbeat(TOOLS / "heartbeat.py")
    row("live_green", r.returncode == 0 and "project_lines=" in r.stdout,
        f"this checkout, unmodified: exit {r.returncode}")

    base = Path(tempfile.mkdtemp(prefix="heartbeat_control_"))
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
            # The state is set here and read by a process that did not set it.
            r = _run_heartbeat(hb_main)
            missing = [w for w in WANT_IN_REFUSAL if w not in r.stderr]
            row("bare_red_from_main",
                r.returncode != 0 and not missing and str(main_ck) in r.stderr,
                f"exit {r.returncode}; missing from the refusal: {missing or 'nothing'}")

            # The variant a naive probe misses: from a linked worktree `git rev-parse
            # --is-bare-repository` answers `false`, and everything the agent does still works.
            wt_status = _git(wt, "status", "--porcelain")
            r = _run_heartbeat(hb_wt)
            missing = [w for w in WANT_IN_REFUSAL if w not in r.stderr]
            row("bare_red_from_linked_worktree",
                r.returncode != 0 and not missing and str(main_ck) in r.stderr,
                f"exit {r.returncode} while `git status` in that worktree is exit "
                f"{wt_status.returncode}; missing: {missing or 'nothing'}")

            # The mutant: the pre-fix behaviour, reproduced.
            r = _run_heartbeat(mutant)
            row("mutant_bare_silent", r.returncode == 0 and r.stdout == healthy,
                f"guard call deleted: exit {r.returncode}, output "
                f"{'identical to the healthy run' if r.stdout == healthy else 'DIFFERS'}")
        finally:
            _git(main_ck, "config", "core.bare", "false")

        # The `finally` above is the whole reason this row can run at all.
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
        row("not_a_repo_red", r.returncode != 0 and "git worktree list" in r.stderr,
            f"no repository at the root: exit {r.returncode}")
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
