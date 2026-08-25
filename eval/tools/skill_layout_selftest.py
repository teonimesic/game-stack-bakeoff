#!/usr/bin/env python3
"""Pin `skill_layout_control.py`'s CRASH SAFETY in both directions, offline.

    python3 eval/tools/skill_layout_selftest.py
    python3 eval/tools/skill_layout_control.py --selftest    # the same entry point

WHAT THIS PINS, AND WHAT IT DELIBERATELY DOES NOT. The control's other half - that
`docstat.py --sweep` goes RED on each of the five plants - needs the real document corpus and
is pinned by running the control itself, in `controls.yml`. This file pins the half that only
shows up when the control DIES: that an interrupted run leaves the working tree either
unplanted or self-identifying.

THE KILLS ARE REAL. `subprocess` + `SIGTERM` and `SIGKILL` against a child that has actually
planted a breakage - not a simulated failure, not an exception raised where a signal would
land. The two signals are different questions and both have to be asked:

  SIGTERM is catchable, so the handler must restore before dying. This is the ordinary case:
  a Bash timeout, a Ctrl-C, a killed CI step. Its MUTANT is the same child with the handler
  never installed, and it must leave the tree broken - otherwise the handler is decoration
  and the pin is green for the wrong reason.

  SIGKILL is not catchable, so nothing can restore in-process and the tree IS left broken.
  The property there is the NEXT run: the state file must account for the leftover so it is
  repaired and announced (`resume`), and with no state file the tool must refuse and name the
  repair (`refuse`) rather than delete a path it cannot prove it created.

THE FIXTURE IS A THROWAWAY GIT REPOSITORY, not the live tree. A control that repairs the
repository it is testing cannot tell "the repair worked" from "the repair was never needed",
and it would have exactly the failure mode this whole ticket is about.
"""
import os
import shutil
import signal
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import skill_layout_control as slc
from docstat import SKILLS_REAL, SKILLS_LINKS

CHILD = os.path.join(HERE, "_skill_layout_child.py")


# ---------------------------------------------------------------------------------------
def _git(root, *args):
    r = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed in {root}: {r.stderr.strip()}")
    return r.stdout


def make_fixture(tmp: str) -> str:
    """A repository with the shipped layout: real skills at SKILLS_REAL, a symlink pointer."""
    root = os.path.join(tmp, "repo")
    real = os.path.join(root, SKILLS_REAL, "tasks")
    os.makedirs(real)
    with open(os.path.join(real, "SKILL.md"), "w") as fh:
        fh.write("---\nname: tasks\n---\n\n# Tasks\n\nA fixture skill.\n")
    link = os.path.join(root, SKILLS_LINKS[0])
    os.makedirs(os.path.dirname(link), exist_ok=True)
    os.symlink(os.path.relpath(os.path.join(root, SKILLS_REAL), os.path.dirname(link)), link)

    _git(root, "init", "-q")
    _git(root, "config", "user.email", "fixture@example.invalid")
    _git(root, "config", "user.name", "fixture")
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", "fixture layout")
    if _git(root, "status", "--porcelain").strip():
        raise RuntimeError("fixture is dirty at birth; every row below would be meaningless")
    return root


def dirty(root: str) -> str:
    return _git(root, "status", "--porcelain").strip()


# ---------------------------------------------------------------------------------------
class Pins:
    def __init__(self):
        self.failed = []
        self.n = 0

    def check(self, name: str, got, want):
        self.n += 1
        ok = got == want
        if not ok:
            self.failed.append(f"{name}: got {got!r}, want {want!r}")
        print(f"  {'PASS' if ok else 'FAIL'}  {name}")

    def contains(self, name: str, haystack: str, needle: str):
        self.n += 1
        ok = needle in haystack
        if not ok:
            self.failed.append(f"{name}: {needle!r} not in {haystack!r}")
        print(f"  {'PASS' if ok else 'FAIL'}  {name}")


# ---------------------------------------------------------------------------------------
def pin_each_plant_is_seen_and_repaired(p: Pins, tmp: str) -> None:
    """Every plant, one at a time: leftovers() sees it, repair() undoes it, git agrees.

    This is also the guard on a NEW plant. `CREATED_PATHS`/`FROM_INDEX_PATHS` are derived
    from the plant classes, so a plant that declares neither is invisible to the repair - and
    it would be invisible here too, as a red row, which is the point.
    """
    print("\neach plant is seen as a leftover and repaired from the index")
    for cls in slc.PLANTS:
        root = make_fixture(os.path.join(tmp, cls.__name__))
        cls(root).plant()
        p.check(f"{cls.__name__}: leftovers() sees it",
                bool(slc.leftovers(root)), True)
        acted = slc.repair(root)
        p.check(f"{cls.__name__}: repair() acted", bool(acted), True)
        p.check(f"{cls.__name__}: leftovers() clear after repair", slc.leftovers(root), [])
        p.check(f"{cls.__name__}: git status clean after repair", dirty(root), "")
        p.check(f"{cls.__name__}: repair() is idempotent", slc.repair(root), [])


def pin_clean_tree_is_left_alone(p: Pins, tmp: str) -> None:
    """VARIANT: the input the repair must NOT act on.

    A repair that always acts cannot be distinguished from one that works, and it would
    `git checkout --` over an operator's uncommitted pointer edit on every invocation.
    """
    print("\na clean tree is a leftover-free tree, and repair() does nothing to it")
    root = make_fixture(os.path.join(tmp, "clean"))
    p.check("leftovers() empty on a clean fixture", slc.leftovers(root), [])
    p.check("repair() acts on nothing", slc.repair(root), [])
    p.check("git status still clean", dirty(root), "")
    p.check("recovery_verdict is 'clean'", slc.recovery_verdict(root)[0], "clean")


def pin_state_file_is_outside_the_work_tree(p: Pins, tmp: str) -> None:
    """The marker must be invisible to `git status`, or `git add -A` can commit it.

    Task 135 staged a plant that no longer existed on disk by racing this control with a
    `git add -A`. A marker in the work tree would be the same defect, permanently.
    """
    print("\nthe state file lives in the git directory, not in the work tree")
    root = make_fixture(os.path.join(tmp, "state"))
    path = slc.write_state(root)
    p.check("state file exists", os.path.exists(path), True)
    p.check("it is under the git directory",
            os.path.realpath(path).startswith(os.path.realpath(os.path.join(root, ".git"))),
            True)
    p.check("git status sees nothing", dirty(root), "")
    p.check("read_state finds it", slc.read_state(root) is not None, True)
    slc.clear_state(root)
    p.check("clear_state removes it", slc.read_state(root), None)
    p.check("clear_state is idempotent", (slc.clear_state(root), slc.read_state(root))[1], None)


def _run_child(root: str, mode: str, sig: int) -> int:
    """Start a child that plants and waits, kill it with `sig`, return its exit status."""
    proc = subprocess.Popen([sys.executable, CHILD, root, mode],
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    line = proc.stdout.readline()
    if "planted" not in line:
        proc.kill()
        raise RuntimeError(f"child never planted: {line!r}{proc.stdout.read()}")
    proc.send_signal(sig)
    proc.wait(timeout=60)
    proc.stdout.read()
    return proc.returncode


def pin_sigterm_restores(p: Pins, tmp: str) -> None:
    print("\nSIGTERM mid-plant: the handler restores before dying (and its mutant does not)")
    root = make_fixture(os.path.join(tmp, "sigterm"))
    rc = _run_child(root, "guarded", signal.SIGTERM)
    p.check("child died of SIGTERM, not of exit(1)", rc, -signal.SIGTERM)
    p.check("leftovers() clear after the kill", slc.leftovers(root), [])
    p.check("git status clean after the kill", dirty(root), "")
    p.check("the state file is gone too", slc.read_state(root), None)

    # MUTANT: the handler is what does the work. Delete it and the same kill must break the
    # tree - otherwise this pin would be green on a tool with no crash safety at all.
    mroot = make_fixture(os.path.join(tmp, "sigterm-mutant"))
    _run_child(mroot, "no-handler", signal.SIGTERM)
    p.check("MUTANT no handler: the tree IS left broken", bool(slc.leftovers(mroot)), True)
    p.check("MUTANT no handler: git status is dirty", dirty(mroot) != "", True)


def pin_sigkill_is_recovered_next_run(p: Pins, tmp: str) -> None:
    print("\nSIGKILL mid-plant: uncatchable, so the NEXT run is what must cope")
    root = make_fixture(os.path.join(tmp, "sigkill"))
    rc = _run_child(root, "guarded", signal.SIGKILL)
    p.check("child died of SIGKILL", rc, -signal.SIGKILL)
    p.check("the tree IS broken - nothing can catch SIGKILL", bool(slc.leftovers(root)), True)

    verdict, stale, state = slc.recovery_verdict(root)
    p.check("recovery_verdict is 'resume'", verdict, "resume")
    p.check("it names the leftover", bool(stale), True)
    p.check("and the state file names the dead pid", isinstance(state.get("pid"), int), True)
    p.check("repair() acts", bool(slc.repair(root)), True)
    slc.clear_state(root)
    p.check("tree clean after the resume", dirty(root), "")

    # MUTANT: no state file written. The leftover is then unexplained, and the tool must
    # REFUSE and name the repair rather than delete a path it cannot prove it created.
    mroot = make_fixture(os.path.join(tmp, "sigkill-nostate"))
    _run_child(mroot, "no-state", signal.SIGKILL)
    p.check("MUTANT no state file: the tree is broken", bool(slc.leftovers(mroot)), True)
    p.check("MUTANT no state file: verdict is 'refuse'", slc.recovery_verdict(mroot)[0],
            "refuse")
    p.check("MUTANT no state file: asking the question deleted nothing",
            bool(slc.leftovers(mroot)), True)


def pin_the_advice_says_what_to_do(p: Pins) -> None:
    """The `or` half of the ticket: a red baseline must name the repair and the cause."""
    print("\nthe advice names the repair command, the cause, and every guarded path")
    advice = slc.repair_advice()
    p.contains("names the one-command repair", advice,
               "skill_layout_control.py --repair")
    p.contains("names the interrupted run as the likely cause", advice,
               "was killed between")
    for rel in slc.CREATED_PATHS + slc.FROM_INDEX_PATHS:
        p.contains(f"names {rel}", advice, rel)
    p.contains("names the index restore by hand", advice, "git checkout --")
    # The sentence that redirects a reader away from the skills belongs only where a sweep
    # has actually printed rows. VARIANT and MUTANT of the same flag, in both directions.
    p.contains("with rows_above, redirects the reader off the skills",
               slc.repair_advice(rows_above=True), "skills are fine")
    p.check("without rows_above, points at no output that is not there",
            "rows above" in advice, False)


# ---------------------------------------------------------------------------------------
def cmd_selftest() -> int:
    tmp = tempfile.mkdtemp(prefix="skill-layout-selftest-")
    p = Pins()
    try:
        pin_each_plant_is_seen_and_repaired(p, tmp)
        pin_clean_tree_is_left_alone(p, tmp)
        pin_state_file_is_outside_the_work_tree(p, tmp)
        pin_sigterm_restores(p, tmp)
        pin_sigkill_is_recovered_next_run(p, tmp)
        pin_the_advice_says_what_to_do(p)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    for f in p.failed:
        print(f"  {f}")
    print(f"\n{p.n - len(p.failed)}/{p.n} pins over {len(slc.PLANTS)} plants, "
          f"2 real kills (SIGTERM, SIGKILL) and 2 mutants")
    return 1 if p.failed else 0


if __name__ == "__main__":
    raise SystemExit(cmd_selftest())
