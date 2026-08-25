#!/usr/bin/env python3
"""Pin the skill-location gate in BOTH directions, on the live tree, crash-safely.

A gate relaxed to accept symlinks that also accepts copies has been deleted, not moved.
This plants each way the layout can break, asserts `docstat.py --sweep` goes RED, removes
the plant, and asserts it goes GREEN again - so a green sweep is evidence rather than a
silence that a mis-aimed check would also produce.

Exit status is read UNPIPED from `subprocess.run` (AGENTS.md rule 3).

    python3 eval/tools/skill_layout_control.py             # the five plants, ~2 minutes
    python3 eval/tools/skill_layout_control.py --repair     # undo an interrupted run
    python3 eval/tools/skill_layout_control.py --selftest   # offline pins, on a fixture repo

THE PLANTS GO INTO THE REAL WORKING TREE, SO AN INTERRUPTED RUN IS A REPOSITORY STATE.
A 2-minute Bash timeout killed this at exit 143 and left `.claude/skills` a real directory
of copies; the next four gate runs were exit 1 with ten rows blaming the skills, for a
reason that had nothing to do with the change under test, and the repair was written down
nowhere (`tasks/147`, `tasks/150`). `docstat.py --selftest` avoids the whole class by
mutating copies in memory. A symlink plant cannot be done in memory, so this file buys the
same property three other ways:

  RESTORE FROM THE INDEX, NEVER FROM A VARIABLE. `repair()` deletes whatever sits at each
  planted path and runs `git checkout --` on the tracked ones. A restore held in memory dies
  with the process holding it; the index outlives the process, so one call repairs a live run
  between plants AND a tree a previous run abandoned. That is also why there is no separate
  recovery path to rot: an ordinary run exercises the crash repair five times.

  THE RUN DECLARES ITSELF WHILE IT IS PLANTED. A state file in the git directory - never in
  the work tree, so it cannot reach `git status`, `.gitignore` or any document corpus -
  records the paths this run may touch. Written before the first plant, removed after the
  last restore, so its presence means a run is in flight or died in flight.

  IT SAYS WHAT TO DO. A leftover the state file does not explain is not silently deleted:
  the tool names the repair command and the interrupted-run hypothesis, and refuses.

SIGTERM, SIGINT and SIGHUP restore before dying, so an ordinary timeout leaves nothing
behind at all. SIGKILL cannot be caught - that is what the state file is for.

EVERY LINE IS FLUSHED. The interrupted run behind this design wrote a log file that was
completely EMPTY at exit 143: stdout is block-buffered into a file, so a killed run discards
the very output that would have named the plant in place. What an instrument did is worth
more than the confidence you had in it (AGENTS.md), and only if it survives the instrument.

`skill_layout_selftest.py` pins all of it offline, on a throwaway git repository, with a
real SIGTERM and a real SIGKILL rather than a simulated failure.
"""
import json
import os
import shutil
import signal
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
from docstat import SKILLS_REAL, SKILLS_LINKS  # the address, not a second spelling of it

SWEEP = [sys.executable, os.path.join(HERE, "docstat.py"), "--sweep"]
STATE_NAME = "skill_layout_control_state.json"
SELF = "python3 eval/tools/skill_layout_control.py"


def say(*a):
    """Every line, immediately. A killed run's log is the only account of where it died."""
    print(*a, flush=True)


def sweep(root: str = ROOT) -> tuple[int, str]:
    """Exit status and text of one `docstat.py --sweep`, read unpiped."""
    r = subprocess.run(SWEEP, cwd=root, capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


# ---------------------------------------------------------------------------------------
# The state file lives in the GIT DIRECTORY, resolved per work tree.
#
# Not in the work tree, for three reasons that each rule out the obvious placement: a root
# dotfile would show up in `git status` and could be committed; ignoring it would need a
# `.gitignore` entry, and that file's own header says every entry is build output or
# oversized evidence and this is neither; and a per-checkout fact belongs in the per-checkout
# directory. `--absolute-git-dir` returns a linked worktree's PRIVATE directory, so two
# agents planting in two worktrees cannot read each other's state.
# ---------------------------------------------------------------------------------------
def state_path(root: str = ROOT) -> str:
    r = subprocess.run(["git", "rev-parse", "--absolute-git-dir"],
                       cwd=root, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"not a git checkout: {root}\n{r.stderr.strip()}")
    return os.path.join(r.stdout.strip(), STATE_NAME)


def write_state(root: str = ROOT) -> str:
    p = state_path(root)
    tmp = p + ".tmp"
    with open(tmp, "w") as fh:
        json.dump({"pid": os.getpid(), "started": time.strftime("%Y-%m-%dT%H:%M:%S"),
                   "creates": [list(pair) for pair in CREATED_FILES],
                   "from_index": list(FROM_INDEX_PATHS)},
                  fh, indent=2)
    os.replace(tmp, p)          # one writer, atomically (eval/AGENTS.md)
    return p


def read_state(root: str = ROOT) -> dict | None:
    """The record, `{}` if it is unreadable, `None` if there is none.

    Unreadable is not absent. A truncated write still means a run was in flight, and
    collapsing the two would send the reader down the "something else owns these paths"
    branch for a file this tool wrote itself.
    """
    p = state_path(root)
    if not os.path.exists(p):
        return None
    try:
        with open(p) as fh:
            return json.load(fh)
    except (json.JSONDecodeError, OSError):
        return {}


def clear_state(root: str = ROOT) -> None:
    p = state_path(root)
    if os.path.exists(p):
        os.unlink(p)


# ---------------------------------------------------------------------------------------
# Repair
# ---------------------------------------------------------------------------------------
def _rm(p: str) -> None:
    if os.path.islink(p) or os.path.isfile(p):
        os.unlink(p)
    elif os.path.isdir(p):
        shutil.rmtree(p)


def _differs_from_index(root: str, rel: str) -> bool:
    """Does the work tree at `rel` disagree with the index?

    Deliberately NOT "is it a symlink resolving to SKILLS_REAL" - that is the subject's own
    expectation, and a control that imports its expectation from its subject is not a control
    (AGENTS.md rule 12's corollary). `git status` is an independent second statement of the
    same fact, and it is the one `git checkout --` restores against.
    """
    r = subprocess.run(["git", "status", "--porcelain", "--", rel],
                       cwd=root, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"git status failed on {rel}: {r.stderr.strip()}")
    return bool(r.stdout.strip())


def _unplant_file(root: str, file_rel: str, stop_rel: str) -> list[str]:
    """Remove one planted FILE, then only the directories it left empty, up to `stop_rel`.

    THE PLANT IS A FILE; THE DIRECTORIES ARE SCAFFOLDING, AND THEY MAY NOT BE OURS.
    `rm -rf .codex` was the obvious undo and it is wrong in the one case that matters: a
    `.codex/` tree somebody else owns is deleted wholesale by a repair the reader was told to
    run. So the file goes, and a parent goes only while it is EMPTY - anything still holding
    content stops the walk, whoever put it there. Raised by CodeRabbit on PR #28.

    The residue is a directory that was empty before the plant and is removed after it. An
    empty directory carries no content and no git object, so nothing is lost; a directory
    with anything in it survives, which is the property being bought.
    """
    acted = []
    fp = os.path.join(root, file_rel)
    if os.path.lexists(fp):
        _rm(fp)
        acted.append(f"rm -f {file_rel}")
    stop = os.path.abspath(os.path.join(root, stop_rel))
    d = os.path.dirname(os.path.abspath(fp))
    while os.path.isdir(d) and os.path.commonpath([d, stop]) == stop:
        if os.listdir(d):
            break                                    # not ours, or not empty: stop here
        os.rmdir(d)
        acted.append(f"rmdir {os.path.relpath(d, root)}")
        if d == stop:
            break
        d = os.path.dirname(d)
    return acted


def leftovers(root: str = ROOT) -> list[str]:
    """Every path a plant can be left at. Empty means the tree carries no plant."""
    out = [f for f, _ in CREATED_FILES if os.path.lexists(os.path.join(root, f))]
    out += [rel for rel in FROM_INDEX_PATHS if _differs_from_index(root, rel)]
    return out


def repair(root: str = ROOT) -> list[str]:
    """Undo every plant, from the index. Idempotent, and returns what it actually did."""
    acted = []
    for file_rel, stop_rel in CREATED_FILES:
        acted += _unplant_file(root, file_rel, stop_rel)
    for rel in FROM_INDEX_PATHS:
        if not _differs_from_index(root, rel):
            continue
        p = os.path.join(root, rel)
        if os.path.lexists(p):
            _rm(p)
        r = subprocess.run(["git", "checkout", "--", rel],
                           cwd=root, capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError(f"git checkout -- {rel} failed: {r.stderr.strip()}")
        acted.append(f"rm -rf {rel} && git checkout -- {rel}")
    return acted


def recovery_verdict(root: str = ROOT) -> tuple[str, list[str], dict | None]:
    """What a starting run must do about the tree it found: `clean`, `resume` or `refuse`.

    Separated from `cmd_run` so the decision can be pinned without a sweep. `resume` is a
    leftover this tool's own state file accounts for; `refuse` is a leftover nothing accounts
    for, and those must not be deleted for the reader - a path we cannot prove we created is
    a path something else may own.
    """
    stale = leftovers(root)
    if not stale:
        return "clean", [], None
    state = read_state(root)
    return ("refuse" if state is None else "resume"), stale, state


def repair_advice(rows_above: bool = False) -> str:
    """The repair, spelled out.

    `rows_above` is set only where a `--sweep` has just printed its rows, because that is the
    reader's actual problem: ten rows naming `SKILL.md` files send them to the skills, and the
    skills are not what is broken. Printing that sentence where no rows were printed would
    point at output that is not there.
    """
    by_hand = "; ".join([f"rm -f {f}" for f, _ in CREATED_FILES]
                        + [f"rm -rf {r} && git checkout -- {r}" for r in FROM_INDEX_PATHS])
    lead = ("  LIKELY CAUSE: a previous skill_layout_control.py run was killed between\n"
            "  planting a breakage and restoring it.")
    if rows_above:
        lead += ("\n  The rows above blame the skills; the skills are fine and the working\n"
                 "  tree is not.")
    return (f"{lead}\n"
            f"  REPAIR, one command:  {SELF} --repair\n"
            f"  or by hand:           {by_hand}")


# ---------------------------------------------------------------------------------------
# The plants
# ---------------------------------------------------------------------------------------
class PlantRealCopy:
    """A genuine second copy: a real SKILL.md, not a symlink, in a second location.

    This is the #99 defect itself. If the gate cannot see this, the gate is gone.
    """
    name = "a real SKILL.md copied to .codex/skills/<name>/"
    creates = ((".codex/skills/tasks/SKILL.md", ".codex"),)
    from_index = ()

    def __init__(self, root: str = ROOT):
        self.root = root
        self.dir = os.path.join(root, ".codex", "skills", "tasks")

    def plant(self):
        os.makedirs(self.dir, exist_ok=True)
        shutil.copy(os.path.join(self.root, SKILLS_REAL, "tasks", "SKILL.md"),
                    os.path.join(self.dir, "SKILL.md"))


class PlantDeepCopy:
    """A copy at the wrong NESTING DEPTH inside the authoritative root.

    `.agents/skills/tasks/extra/SKILL.md` is under SKILLS_REAL, so a check that asked only
    "is this path a prefix of the root" would pass it. The grandparent test is what fails it.
    """
    name = "a real SKILL.md nested one level too deep inside the authoritative root"
    creates = ((f"{SKILLS_REAL}/tasks/extra/SKILL.md", f"{SKILLS_REAL}/tasks/extra"),)
    from_index = ()

    def __init__(self, root: str = ROOT):
        self.root = root
        self.dir = os.path.join(root, SKILLS_REAL, "tasks", "extra")

    def plant(self):
        os.makedirs(self.dir, exist_ok=True)
        shutil.copy(os.path.join(self.root, SKILLS_REAL, "tasks", "SKILL.md"),
                    os.path.join(self.dir, "SKILL.md"))


class BreakPointer:
    """The pointer removed entirely.

    The nine skills are still present and still at the authoritative address; every other
    check reads clean; and no agent can load one, because Claude Code does not discover
    `.agents/skills` on its own. Measured, not assumed - see `_check_skill_location`.
    """
    name = "the .claude/skills pointer deleted (skills present but unreachable)"
    creates = ()
    from_index = SKILLS_LINKS

    def __init__(self, root: str = ROOT):
        self.link = os.path.join(root, SKILLS_LINKS[0])

    def plant(self):
        os.unlink(self.link)


class DanglingPointer:
    """The pointer present but aimed at nothing.

    A dangling symlink is the shape that looks most like a working layout: `ls` shows the
    entry, git stores a 120000 blob, and it resolves to a path that is not there.
    """
    name = "the .claude/skills pointer aimed at a target that does not exist"
    creates = ()
    from_index = SKILLS_LINKS

    def __init__(self, root: str = ROOT):
        self.link = os.path.join(root, SKILLS_LINKS[0])

    def plant(self):
        os.unlink(self.link)
        os.symlink("../.agents/skills-typo", self.link)


class PointerAsRealCopy:
    """The pointer replaced by a real directory holding real copies.

    This is exactly what a git merge of a branch forked before the move would produce, it is
    how the mirror came back on 2026-08-23 in the first place, and it is the shape an
    interrupted run of this very file leaves in the tree (`tasks/147`, `tasks/150`).
    """
    name = "the .claude/skills pointer replaced by a real directory of copies"
    creates = ()
    from_index = SKILLS_LINKS

    def __init__(self, root: str = ROOT):
        self.root = root
        self.link = os.path.join(root, SKILLS_LINKS[0])

    def plant(self):
        os.unlink(self.link)
        shutil.copytree(os.path.join(self.root, SKILLS_REAL), self.link, symlinks=False)


PLANTS = [PlantRealCopy, PlantDeepCopy, BreakPointer, DanglingPointer, PointerAsRealCopy]

# The union of what any plant touches, DERIVED from the plants rather than restated beside
# them: a second list is a second source of truth, and a plant whose path was left out of it
# would be exactly the un-repaired leftover this file exists to prevent.
CREATED_FILES = tuple(dict.fromkeys(pair for cls in PLANTS for pair in cls.creates))
FROM_INDEX_PATHS = tuple(dict.fromkeys(p for cls in PLANTS for p in cls.from_index))


# ---------------------------------------------------------------------------------------
# Signals
# ---------------------------------------------------------------------------------------
_ACTIVE_ROOT: str | None = None
_SIGNALS = (signal.SIGINT, signal.SIGTERM, signal.SIGHUP)


def _on_signal(signum, _frame):
    name = signal.Signals(signum).name
    if _ACTIVE_ROOT:
        try:
            acted = repair(_ACTIVE_ROOT)
            clear_state(_ACTIVE_ROOT)
            say(f"\n{name}: restored the working tree before dying"
                f" ({'; '.join(acted) if acted else 'nothing was planted'})")
        except Exception as exc:                     # never swallow it: say what is left
            say(f"\n{name}: RESTORE FAILED - {exc}\n{repair_advice()}")
    signal.signal(signum, signal.SIG_DFL)
    os.kill(os.getpid(), signum)                     # die OF the signal, not of exit(1)


def install_handlers(root: str) -> None:
    """Arm the restore. Call BEFORE the first plant, never after."""
    global _ACTIVE_ROOT
    _ACTIVE_ROOT = root
    for sig in _SIGNALS:
        signal.signal(sig, _on_signal)


# ---------------------------------------------------------------------------------------
def cmd_repair(root: str = ROOT) -> int:
    acted = repair(root)
    clear_state(root)
    for a in acted:
        say(f"  {a}")
    say(f"{len(acted)} planted path(s) undone" if acted
        else "nothing to repair: no plant is in the tree")
    return 0


def cmd_run(root: str = ROOT) -> int:
    verdict, stale, state = recovery_verdict(root)
    if verdict == "refuse":
        say("REFUSING TO RUN: the tree already carries a plant and no state file "
            "explains it.")
        for rel in stale:
            say(f"  {rel}")
        say("  Either a run from before this tool recorded its state died mid-plant, or\n"
            "  something else owns these paths - so they are not deleted for you.")
        say(repair_advice())
        return 1
    if verdict == "resume":
        say(f"a previous run died mid-plant (state file from pid {state.get('pid', '?')}, "
            f"started {state.get('started', '?')}) - repairing first:")
        for a in repair(root):
            say(f"  {a}")
        clear_state(root)

    write_state(root)
    install_handlers(root)
    try:
        return _run_plants(root)
    finally:
        repair(root)
        clear_state(root)


def _run_plants(root: str) -> int:
    base, text = sweep(root)
    say(f"{'baseline, no plant':<62} exit={base} {'GREEN' if base == 0 else 'RED'}")
    if base != 0:
        say("  the tree is already red; fix that before trusting anything below")
        if "a real skill file outside" in text or "must be a symlink to" in text:
            say(repair_advice(rows_above=True))
        else:
            say("  the rows do not name the skill layout, so this is a documentation "
                "defect rather than an abandoned plant. Run docstat.py --sweep to read it.")
        return 1

    bad = 0
    for cls in PLANTS:
        p = cls(root)
        p.plant()
        try:
            red, _ = sweep(root)
        finally:
            repair(root)
        back, _ = sweep(root)
        ok = (red != 0) and (back == 0)
        bad += not ok
        say(f"{p.name:<62} exit={red} {'RED' if red else 'GREEN(!)'} "
            f"-> restored exit={back} {'GREEN' if back == 0 else 'RED(!)'} "
            f"{'ok' if ok else 'FAILED'}")

    say(f"\n{len(PLANTS) - bad}/{len(PLANTS)} plants caught and cleanly restored")
    return 1 if bad else 0


def main(argv: list[str]) -> int:
    if "--repair" in argv:
        return cmd_repair()
    if "--selftest" in argv:
        from skill_layout_selftest import cmd_selftest
        return cmd_selftest()
    return cmd_run()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
