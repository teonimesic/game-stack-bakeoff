#!/usr/bin/env python3
"""Pin the skill-location gate in BOTH directions, on the live tree.

A gate relaxed to accept symlinks that also accepts copies has been deleted, not moved.
This plants each way the layout can break, asserts `docstat.py --sweep` goes RED, removes
the plant, and asserts it goes GREEN again — so a green sweep is evidence rather than a
silence that a mis-aimed check would also produce.

Exit status is read UNPIPED from `subprocess.run` (AGENTS.md rule 3).

    python3 eval/tools/skill_layout_control.py
"""
import os, shutil, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
from docstat import SKILLS_REAL, SKILLS_LINKS  # the address, not a second spelling of it

SWEEP = [sys.executable, os.path.join(HERE, "docstat.py"), "--sweep"]


def sweep() -> int:
    return subprocess.run(SWEEP, cwd=ROOT, capture_output=True, text=True).returncode


class PlantRealCopy:
    """A genuine second copy: a real SKILL.md, not a symlink, in a second location.

    This is the #99 defect itself. If the gate cannot see this, the gate is gone.
    """
    name = "a real SKILL.md copied to .codex/skills/<name>/"

    def __init__(self):
        self.dir = os.path.join(ROOT, ".codex", "skills", "tasks")

    def plant(self):
        os.makedirs(self.dir, exist_ok=True)
        shutil.copy(os.path.join(ROOT, SKILLS_REAL, "tasks", "SKILL.md"),
                    os.path.join(self.dir, "SKILL.md"))

    def remove(self):
        shutil.rmtree(os.path.join(ROOT, ".codex"))


class PlantDeepCopy:
    """A copy at the wrong NESTING DEPTH inside the authoritative root.

    `.agents/skills/tasks/extra/SKILL.md` is under SKILLS_REAL, so a check that asked only
    "is this path a prefix of the root" would pass it. The grandparent test is what fails it.
    """
    name = "a real SKILL.md nested one level too deep inside the authoritative root"

    def __init__(self):
        self.dir = os.path.join(ROOT, SKILLS_REAL, "tasks", "extra")

    def plant(self):
        os.makedirs(self.dir, exist_ok=True)
        shutil.copy(os.path.join(ROOT, SKILLS_REAL, "tasks", "SKILL.md"),
                    os.path.join(self.dir, "SKILL.md"))

    def remove(self):
        shutil.rmtree(self.dir)


class BreakPointer:
    """The pointer removed entirely.

    The nine skills are still present and still at the authoritative address; every other
    check reads clean; and no agent can load one, because Claude Code does not discover
    `.agents/skills` on its own. Measured, not assumed — see `_check_skill_location`.
    """
    name = "the .claude/skills pointer deleted (skills present but unreachable)"

    def __init__(self):
        self.link = os.path.join(ROOT, SKILLS_LINKS[0])
        self.target = None

    def plant(self):
        self.target = os.readlink(self.link)
        os.unlink(self.link)

    def remove(self):
        os.symlink(self.target, self.link)


class DanglingPointer:
    """The pointer present but aimed at nothing.

    A dangling symlink is the shape that looks most like a working layout: `ls` shows the
    entry, git stores a 120000 blob, and it resolves to a path that is not there.
    """
    name = "the .claude/skills pointer aimed at a target that does not exist"

    def __init__(self):
        self.link = os.path.join(ROOT, SKILLS_LINKS[0])
        self.target = None

    def plant(self):
        self.target = os.readlink(self.link)
        os.unlink(self.link)
        os.symlink("../.agents/skills-typo", self.link)

    def remove(self):
        os.unlink(self.link)
        os.symlink(self.target, self.link)


class PointerAsRealCopy:
    """The pointer replaced by a real directory holding real copies.

    This is exactly what a git merge of a branch forked before the move would produce, and
    it is how the mirror came back on 2026-08-23 in the first place.
    """
    name = "the .claude/skills pointer replaced by a real directory of copies"

    def __init__(self):
        self.link = os.path.join(ROOT, SKILLS_LINKS[0])
        self.target = None

    def plant(self):
        self.target = os.readlink(self.link)
        os.unlink(self.link)
        shutil.copytree(os.path.join(ROOT, SKILLS_REAL), self.link, symlinks=False)

    def remove(self):
        shutil.rmtree(self.link)
        os.symlink(self.target, self.link)


PLANTS = [PlantRealCopy, PlantDeepCopy, BreakPointer, DanglingPointer, PointerAsRealCopy]


def main() -> int:
    base = sweep()
    print(f"{'baseline, no plant':<62} exit={base} {'GREEN' if base == 0 else 'RED'}")
    if base != 0:
        print("  the tree is already red; fix that before trusting anything below")
        return 1

    bad = 0
    for cls in PLANTS:
        p = cls()
        p.plant()
        try:
            red = sweep()
        finally:
            p.remove()
        back = sweep()
        ok = (red != 0) and (back == 0)
        bad += not ok
        print(f"{p.name:<62} exit={red} {'RED' if red else 'GREEN(!)'} "
              f"-> restored exit={back} {'GREEN' if back == 0 else 'RED(!)'} "
              f"{'ok' if ok else 'FAILED'}")

    print(f"\n{len(PLANTS) - bad}/{len(PLANTS)} plants caught and cleanly restored")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
