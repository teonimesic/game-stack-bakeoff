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
import pathlib
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
MINE = "somebody else's file\n"
# The signals `install_handlers` must register, stated INDEPENDENTLY of the tool and compared
# with it in a row of `pin_a_caught_signal_restores`. See that docstring for what sharing the
# tool's tuple hid.
CAUGHT = (signal.SIGINT, signal.SIGTERM, signal.SIGHUP)


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


def _read(path: str) -> str:
    return pathlib.Path(path).read_text() if os.path.exists(path) else "<gone>"






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

    def refuses(self, name: str, fn, want: bool = True):
        """Did `fn` REFUSE - raise the tool's own RuntimeError?

        Three outcomes, not two. Any other exception is a failed pin carrying its text, never
        a refusal and never an aborted suite: a check that dies on an unexpected input reports
        nothing about the inputs after it, which is the shape a mutant hides in.
        """
        self.n += 1
        try:
            fn()
            got, note = False, "returned normally"
        except RuntimeError as exc:
            got, note = True, f"refused: {exc}"
        except Exception as exc:                      # noqa: BLE001 - reported, not swallowed
            got, note = None, f"{type(exc).__name__}: {exc}"
        ok = got is want
        if not ok:
            self.failed.append(f"{name}: {note}")
        print(f"  {'PASS' if ok else 'FAIL'}  {name}")


# ---------------------------------------------------------------------------------------
def pin_each_plant_is_seen_and_repaired(p: Pins, tmp: str) -> None:
    """Every plant, one at a time: leftovers() sees it, repair() undoes it, git agrees.

    This is also the guard on a NEW plant. `CREATED_FILES`/`FROM_INDEX_PATHS` are derived
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


def pin_a_foreign_tree_survives_the_repair(p: Pins, tmp: str) -> None:
    """VARIANT: `.codex/` is not ours, and `--repair` is a command the tool tells people to run.

    The plant is a FILE. `rm -rf .codex` undoes it and also deletes a `.codex/` tree another
    agent owns, which is the wrong answer for the one input that matters. Raised by CodeRabbit
    on PR #28. The pin is that the planted file goes, the foreign content stays, and the
    directories the plant created are pruned only while they are empty.
    """
    print("\na pre-existing .codex tree survives the repair; only the plant is removed")
    root = make_fixture(os.path.join(tmp, "foreign"))
    keep = os.path.join(root, ".codex", "config.toml")
    keep_deep = os.path.join(root, ".codex", "skills", "other", "SKILL.md")
    os.makedirs(os.path.dirname(keep_deep))
    for f in (keep, keep_deep):
        with open(f, "w") as fh:
            fh.write("not ours\n")

    slc.PlantRealCopy(root).plant()
    p.check("the plant is seen", bool(slc.leftovers(root)), True)
    acted = slc.repair(root)
    p.check("repair() removed the planted file",
            any("rm -f .codex/skills/tasks/SKILL.md" in a for a in acted), True)
    p.check("the foreign config survives", os.path.exists(keep), True)
    p.check("the foreign skill survives", os.path.exists(keep_deep), True)
    p.check("the foreign .codex root survives", os.path.isdir(os.path.join(root, ".codex")),
            True)
    p.check("the empty scaffolding the plant made is pruned",
            os.path.exists(os.path.join(root, ".codex", "skills", "tasks")), False)
    p.check("leftovers() clear", slc.leftovers(root), [])

    # And the same for the deep plant: `.agents/skills/tasks/` is real and must not be pruned
    # when its `extra/` child goes.
    slc.PlantDeepCopy(root).plant()
    slc.repair(root)
    p.check("the authoritative skill directory survives the deep plant's repair",
            os.path.exists(os.path.join(root, SKILLS_REAL, "tasks", "SKILL.md")), True)
    p.check("only the extra/ scaffolding went",
            os.path.exists(os.path.join(root, SKILLS_REAL, "tasks", "extra")), False)


def pin_a_symlinked_component_is_refused(p: Pins, tmp: str) -> None:
    """VARIANT: a symlink on a plant's path takes the write and the prune OUTSIDE the tree.

    `.codex/skills -> /elsewhere` makes `os.makedirs` write the plant outside the repository
    and the parent walk remove a directory the repository does not contain. Raised by
    CodeRabbit on PR #28. Delete `assert_inside` from either call site and the two "survives"
    rows below go red, because that is exactly what the unguarded code does.
    """
    print("\na symlinked path component is refused, and nothing outside the tree is touched")
    root = make_fixture(os.path.join(tmp, "symlinked"))
    outside = os.path.join(tmp, "outside")
    os.makedirs(os.path.join(outside, "tasks"))
    victim = os.path.join(outside, "tasks", "SKILL.md")
    with open(victim, "w") as fh:
        fh.write(MINE)
    os.makedirs(os.path.join(root, ".codex"))
    os.symlink(outside, os.path.join(root, ".codex", "skills"))

    p.refuses("plant() refuses", slc.PlantRealCopy(root).plant)
    # The CONTENT, not the listing. An unguarded plant copies its SKILL.md straight over the
    # victim, and the directory listing is byte-identical before and after - a row that cannot
    # tell those two apart is reporting the instrument (AGENTS.md rule 9).
    p.check("the file outside is not overwritten", _read(victim), MINE)

    # The leftover a pre-guard run could have left: the file already sitting out there,
    # reachable through the symlink. repair() must refuse it rather than follow it.
    p.refuses("repair() refuses", lambda: slc.repair(root))
    p.check("the file outside survives", _read(victim), MINE)
    p.check("the directory outside survives", os.path.isdir(os.path.join(outside, "tasks")),
            True)

    # And the leaf must be the regular file a plant writes, never a directory `_rm` would
    # rmtree. Same fixture shape, no symlink, so only the leaf test can fire.
    clean = make_fixture(os.path.join(tmp, "leafdir"))
    os.makedirs(os.path.join(clean, ".codex", "skills", "tasks", "SKILL.md", "inner"))
    p.refuses("a directory standing where the plant's file belongs is refused",
              lambda: slc.repair(clean))
    p.check("and it is still there", os.path.isdir(
        os.path.join(clean, ".codex", "skills", "tasks", "SKILL.md", "inner")), True)

    # VARIANT: the guard must not fire on the shipped layout, or every plant refuses.
    ok = make_fixture(os.path.join(tmp, "guard-variant"))
    p.refuses("the guard passes a clean path",
              lambda: slc.assert_inside(ok, ".codex/skills/tasks/SKILL.md"), want=False)
    p.refuses("and passes the deep plant's path",
              lambda: slc.assert_inside(ok, f"{SKILLS_REAL}/tasks/extra/SKILL.md"), want=False)


def pin_an_occupied_leaf_is_refused(p: Pins, tmp: str) -> None:
    """VARIANT: something is already standing where the plant writes its file.

    `shutil.copy` onto an existing DIRECTORY writes `SKILL.md/SKILL.md` inside it, and
    `repair()` then correctly refuses to remove that directory - so the modification is
    permanent. Raised by CodeRabbit on PR #28. Delete the `lexists` test in `_copy_skill_to`
    and the nested-content row below goes red.
    """
    print("\nan occupied plant leaf is refused, and its contents are not modified")
    root = make_fixture(os.path.join(tmp, "occupied"))
    leaf = os.path.join(root, ".codex", "skills", "tasks", "SKILL.md")
    os.makedirs(leaf)
    nested = os.path.join(leaf, "SKILL.md")
    with open(nested, "w") as fh:
        fh.write(MINE)

    p.refuses("plant() refuses a directory at the leaf", slc.PlantRealCopy(root).plant)
    p.check("its nested content is untouched", _read(nested), MINE)
    p.check("the listing is unchanged", sorted(os.listdir(leaf)), ["SKILL.md"])

    # A regular file there is refused too: removing it afterwards would be the same loss one
    # step later, and `leftovers()` already reports it so a run never gets here.
    root2 = make_fixture(os.path.join(tmp, "occupied-file"))
    leaf2 = os.path.join(root2, SKILLS_REAL, "tasks", "extra", "SKILL.md")
    os.makedirs(os.path.dirname(leaf2))
    with open(leaf2, "w") as fh:
        fh.write(MINE)
    p.refuses("plant() refuses a file at the leaf", slc.PlantDeepCopy(root2).plant)
    p.check("that file is untouched", _read(leaf2), MINE)
    p.check("leftovers() reports it, so a run stops before planting",
            slc.leftovers(root2), [f"{SKILLS_REAL}/tasks/extra/SKILL.md"])


def pin_the_lock_holds_the_tree(p: Pins, tmp: str) -> None:
    """A second run must not plant into a tree the first one is already planting into.

    Not the reviewer's symlink race - this is the concurrency that IS reachable here, with no
    adversary at all: two runs in one work tree interleave their plants, and the second reads
    the first's plant as a leftover to clean up underneath it.

    The lock is an OS lock and the test uses a REAL second process, because that is the only
    thing that can hold one: `flock` is per open file description, so a second acquisition
    inside this process would succeed and the pin would be green on nothing. It is also why
    the pid-in-the-state-file version this replaces was wrong twice over - two runs could
    both classify the tree before either wrote a state file, and a reused pid names a
    stranger (CodeRabbit, PR #28).
    """
    print("\nan OS lock holds the tree, and the kernel drops it when the holder dies")
    root = make_fixture(os.path.join(tmp, "lock"))
    holder = subprocess.Popen([sys.executable, CHILD, root, "lock"],
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    try:
        p.check("the holder says it has the lock", holder.stdout.readline().strip(), "ready")
        p.refuses("a second hold() is refused", lambda: _take(root))
        p.check("and it is a Busy, so a caller can tell it from a real failure",
                _busy(lambda: _take(root)), True)
        p.check("cmd_repair refuses rather than deleting under the holder",
                slc.cmd_repair(root), 1)
    finally:
        holder.kill()
        holder.wait(timeout=30)

    # The kernel releases an flock when the holder dies, SIGKILL included - so a crashed run
    # leaves the lock FREE and its state file behind. MUTANT of that: if the lock survived
    # its holder, this row would refuse and the tree would be locked out permanently.
    p.refuses("the dead holder's lock is free", lambda: _take(root), want=False)
    p.check("the tree is unlocked for a real run", slc.cmd_repair(root), 0)


def _take(root: str) -> None:
    with slc.hold(root):
        pass


def _busy(fn) -> bool:
    try:
        fn()
    except slc.Busy:
        return True
    except Exception:                                 # noqa: BLE001 - reported by the caller
        return False
    return False


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
    if "ready" not in line:
        proc.kill()
        raise RuntimeError(f"child never planted: {line!r}{proc.stdout.read()}")
    proc.send_signal(sig)
    proc.wait(timeout=60)
    proc.stdout.read()
    return proc.returncode


def pin_a_caught_signal_restores(p: Pins, tmp: str) -> None:
    """EVERY signal `install_handlers` registers, not the one that produced the ticket.

    SIGTERM alone left a missing SIGINT or SIGHUP handler completely invisible, and Ctrl-C is
    the commonest way this ever gets interrupted by hand. CodeRabbit, PR #28.

    THE POPULATION IS STATED HERE AND COMPARED TO THE TOOL'S, never imported from it. The
    first version looped over `slc._SIGNALS` directly - which is AGENTS.md rule 12's
    corollary, a control importing its expectation from its subject - and the mutant that
    shrinks `_SIGNALS` to `(SIGTERM,)` came back SURVIVED, 0 red of 6, having quietly
    shrunk the pin from 14 rows to 6. A row that compares the two is what makes a removal
    visible; sharing the object is what hides it.
    """
    print("\na caught signal mid-plant restores before dying (and its mutant does not)")
    p.check("the tool registers exactly the signals pinned below",
            tuple(slc._SIGNALS), CAUGHT)
    for sig in CAUGHT:
        name = signal.Signals(sig).name
        root = make_fixture(os.path.join(tmp, f"caught-{name}"))
        rc = _run_child(root, "guarded", sig)
        p.check(f"{name}: child died of the signal, not of exit(1)", rc, -sig)
        p.check(f"{name}: leftovers() clear after the kill", slc.leftovers(root), [])
        p.check(f"{name}: git status clean after the kill", dirty(root), "")
        p.check(f"{name}: the state file is gone too", slc.read_state(root), None)

    # MUTANT: the handler is what does the work. Delete it and the same kill must break the
    # tree - otherwise this pin would be green on a tool with no crash safety at all.
    mroot = make_fixture(os.path.join(tmp, "signal-mutant"))
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
    # `(state or {})` because `recovery_verdict` returns None for `state` on the refuse path.
    # A pin must report a wrong answer, never raise one: an AttributeError here would abort
    # the run and the remaining pins and the summary count would never print. CodeRabbit, #28.
    p.check("and the state file names the dead pid",
            isinstance((state or {}).get("pid"), int), True)
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


def pin_cmd_run_itself(p: Pins, tmp: str) -> None:
    """Drive the REAL entry point, not the pieces it is built from.

    Every other section here calls `hold()`, `recovery_verdict()` and `repair()` directly, so
    a change that removed the lock from `cmd_run`, or removed its stale-run recovery, would
    leave all of them green while allowing concurrent planting and leaving a SIGKILL-damaged
    tree unrepaired. CodeRabbit, PR #28 - and it is AGENTS.md rule 1: a control that never
    exercises the entry point is a control the entry point can be deleted from.

    The five sweeps are stubbed through `cmd_run`'s `plants` seam and nothing else is. They
    take two minutes and, run against a fixture, read the real repository's documents rather
    than the fixture's - so they could only ever answer a question about this checkout.
    """
    print("\nthe normal entry point takes the lock, recovers, and reports the plants' result")
    calls = []

    def stub(root):
        calls.append(root)
        return 0

    # 1. UNDER CONTENTION. A real second process holds the tree; cmd_run must refuse, and the
    #    stub must never be reached - proving it stopped at the lock and not later.
    root = make_fixture(os.path.join(tmp, "cmdrun-busy"))
    holder = subprocess.Popen([sys.executable, CHILD, root, "lock"],
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    try:
        holder.stdout.readline()
        p.check("cmd_run refuses while another run holds the tree",
                slc.cmd_run(root, plants=stub), 1)
        p.check("and it never reached the plants", calls, [])
    finally:
        holder.kill()
        holder.wait(timeout=30)

    # 2. AFTER A SIGKILL. The tree is damaged and the state file explains it; cmd_run must
    #    repair before planting, and leave nothing behind.
    kroot = make_fixture(os.path.join(tmp, "cmdrun-resume"))
    _run_child(kroot, "guarded", signal.SIGKILL)
    p.check("the SIGKILLed tree really is damaged", bool(slc.leftovers(kroot)), True)
    calls.clear()
    p.check("cmd_run returns the plants' result", slc.cmd_run(kroot, plants=stub), 0)
    p.check("it reached the plants this time", calls, [kroot])
    p.check("the leftover was repaired", slc.leftovers(kroot), [])
    p.check("git status clean", dirty(kroot), "")
    p.check("and the state file cleared", slc.read_state(kroot), None)

    # 3. VARIANT: an unexplained leftover must still stop it, through the entry point.
    rroot = make_fixture(os.path.join(tmp, "cmdrun-refuse"))
    _run_child(rroot, "no-state", signal.SIGKILL)
    calls.clear()
    p.check("cmd_run refuses an unexplained leftover", slc.cmd_run(rroot, plants=stub), 1)
    p.check("and never reached the plants", calls, [])
    p.check("nothing was deleted for us", bool(slc.leftovers(rroot)), True)

    # 4. VARIANT: a clean tree runs, and the failing case is reported rather than swallowed.
    croot = make_fixture(os.path.join(tmp, "cmdrun-clean"))
    p.check("a clean tree runs", slc.cmd_run(croot, plants=stub), 0)
    p.check("a failing plant run is reported", slc.cmd_run(croot, plants=lambda r: 1), 1)
    p.check("and it left the tree clean", dirty(croot), "")
    p.check("and no state file", slc.read_state(croot), None)


def pin_the_advice_says_what_to_do(p: Pins, _tmp: str) -> None:
    """The `or` half of the ticket: a red baseline must name the repair and the cause."""
    print("\nthe advice names the repair command, the cause, and every guarded path")
    advice = slc.repair_advice()
    p.contains("names the one-command repair", advice,
               "skill_layout_control.py --repair")
    p.contains("names the interrupted run as the likely cause", advice,
               "was killed between")
    for rel in [f for f, _ in slc.CREATED_FILES] + list(slc.FROM_INDEX_PATHS):
        p.contains(f"names {rel}", advice, rel)
    p.contains("names the index restore by hand", advice, "git checkout --")
    # The sentence that redirects a reader away from the skills belongs only where a sweep
    # has actually printed rows. VARIANT and MUTANT of the same flag, in both directions.
    p.contains("with rows_above, redirects the reader off the skills",
               slc.repair_advice(rows_above=True), "skills are fine")
    p.check("without rows_above, points at no output that is not there",
            "rows above" in advice, False)


# ---------------------------------------------------------------------------------------
SECTIONS = (pin_each_plant_is_seen_and_repaired,
            pin_clean_tree_is_left_alone,
            pin_a_foreign_tree_survives_the_repair,
            pin_a_symlinked_component_is_refused,
            pin_an_occupied_leaf_is_refused,
            pin_the_lock_holds_the_tree,
            pin_state_file_is_outside_the_work_tree,
            pin_a_caught_signal_restores,
            pin_sigkill_is_recovered_next_run,
            pin_cmd_run_itself,
            pin_the_advice_says_what_to_do)


def cmd_selftest() -> int:
    """Run every section. A section that DIES is one failed pin, not a silenced suite.

    Sections mutate real trees and kill real processes, so an unexpected exception is a live
    possibility - and a suite that stops at the first one reports nothing about the sections
    after it while still printing a count. That count would then be smaller than the last
    green run's and nothing would say why, which is the shape a mutant hides in.
    """
    tmp = tempfile.mkdtemp(prefix="skill-layout-selftest-")
    p = Pins()
    try:
        for section in SECTIONS:
            try:
                section(p, tmp)
            except Exception as exc:                  # noqa: BLE001 - recorded, not swallowed
                p.n += 1
                p.failed.append(f"{section.__name__} ABORTED: {type(exc).__name__}: {exc}")
                print(f"  FAIL  {section.__name__} ABORTED: {type(exc).__name__}: {exc}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    for f in p.failed:
        print(f"  {f}")
    kills = ", ".join(signal.Signals(s).name for s in CAUGHT) + ", SIGKILL"
    print(f"\n{p.n - len(p.failed)}/{p.n} pins over {len(slc.PLANTS)} plants and "
          f"{len(SECTIONS)} sections, with real kills: {kills}")
    return 1 if p.failed else 0


if __name__ == "__main__":
    raise SystemExit(cmd_selftest())
