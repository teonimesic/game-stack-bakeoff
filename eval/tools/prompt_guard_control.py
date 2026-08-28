#!/usr/bin/env python3
"""Can `prompt_guard.py` fail — and can it still pass on the inputs it must not flag?

WHY THIS EXISTS
---------------
`prompt_guard.py` prints `ok:` and exits 0 on every prompt this project has ever shipped.
A guard that has only ever printed `ok` has not been shown to be capable of anything else,
and two of its three assertions were extended to a second task class (scenes) in one edit —
the regex that finds task bodies, and a rubric-vocabulary assertion that did not exist. Both
extensions are the kind that go green by not looking.

WHAT IT DOES
------------
Builds a faithful copy of the guard and its inputs under a temporary directory —
`tools/prompt_guard.py`, `suites/*.py`, `SCENES.md`, same relative layout, because the guard
resolves `suites/` and `SCENES.md` from its own path — applies each row's edits (one; the
DISARMED rows carry two, the disarm and the plant), runs the
guard as a subprocess and compares its exit code and output against what the row declares in
advance.

THE FOUR KINDS OF ROW, AND WHY THE LAST TWO ARE NOT OPTIONAL
------------------------------------------------------------
  PRISTINE   the unedited copy exits 0. Not a result on its own; it proves the temp tree is
             faithful, so a red row below is the plant and not the copying.

  MUTANT     a plant the guard MUST report. "Can it fail?"

  VARIANT    an input the guard must still PASS on. AGENTS.md rule 15: every false negative
             adjudicated in this project has been of this kind, and a mutant cannot find
             one. The scene prompts are full of text that LOOKS like rubric — tick counts,
             `layers[].depth`, `just probe SEED` — and a guard that reddens on those is a
             guard someone switches off. `probe` was on the term list and came off it for
             exactly that reason: 8 hits, 0 true.

  DISARMED   the guard's own mechanism removed, with a plant from the MUTANT rows still in
             place, asserting the guard now exits 0. This is what proves a red row above was
             caused by the mechanism it names rather than by anything else in the file — the
             failure task 113 recorded, where a control that shares state with its subject
             reports SURVIVED because the mutant edited the check.

  FSPIN      one row that reads the FILESYSTEM rather than the guard's output, because the 2
             ways `_write_atomic` can go wrong are invisible to every row above: `mkstemp`
             creates at 0600 and `os.replace` would publish that, and a temporary file left
             behind is a file in the snapshot directory nothing owns. Both directions were
             checked against the shipped code — dropping the `chmod` gives 25 unreadable
             files, and swapping `os.replace` for a copy gives 50 files of which 25 are
             temporaries. The row goes red on either.

Run it unpiped and read its own exit code:

    python3 eval/tools/prompt_guard_control.py
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
EVAL = os.path.dirname(HERE)

# Anchors: text that exists exactly once in the file named, checked before use.
S1_BODY = "## The scene: a car on a road"
S2_BODY = "## The scene: a glass of water"
G1_BODY = "## The game: Pong"
TWO_D_RUST = "\"The starter's view is configured for 2D with a 2D camera, which is what this \""
BODY_REGEX = 'r"^def ([gs]\\d+_\\w+)\\(", src, re.M'
RUBRIC_LIST_HEAD = '    "criterion", "criteria", "rubric", "threshold", "tolerance", "graded", "grading",'

# The stack tuple's one owner is `wholegame_prompts.STACKS`. The guard must hold a
# REFERENCE to it, and the identity guard below is what a restated literal trips:
# equal is not the same object, which is the only property that separates a reference
# from a copy that is equal on the day it was written (task 194). The guard is an
# `if`/`raise` and not an `assert` -- asserts are stripped under `python -O`, which
# measured exit 0 on a planted literal in review round 1.
STACKS_REF = "STACKS = W.STACKS"
STACKS_LITERAL = 'STACKS = ("rust", "ts", "unity", "godot")'
IDENTITY_GUARD = "if STACKS is not W.STACKS:"

SCENES = "suites/scene_prompts.py"
GAMES = "suites/wholegame_prompts.py"
GUARD = "tools/prompt_guard.py"
RENDERED = "suites/rendered"
DIFF = ("--diff", RENDERED)

# (id, kind, [(file, anchor, replacement), ...], expected_exit, (every substring wanted)
#  [, argv for the guard])
ROWS: list[tuple] = [
    ("pristine", "PRISTINE", [], 0, ("ok:",)),

    # ---- STACK axis: an engine name in a SCENE body ---------------------------------
    ("engine-name-s1", "MUTANT",
     [(SCENES, S1_BODY, S1_BODY + "\n\nDraw the sky with a Bevy shader.")],
     1, ("s1_parallax: task body names `Bevy`",)),
    ("engine-name-s2", "MUTANT",
     [(SCENES, S2_BODY, S2_BODY + "\n\nUse an AudioStreamPlayer for the impact.")],
     1, ("s2_glass: task body names `AudioStreamPlayer`",)),

    # ---- TASK axis: rules that diverge by stack --------------------------------------
    ("rules-diverge-by-stack", "MUTANT",
     [(SCENES, "{TWO_D_NOTE[stack]}",
       '{TWO_D_NOTE[stack]}{"" if stack == "rust" else chr(10).join(["- an extra rule"] * 20)}')],
     1, ("rules, not just vocabulary, vary by stack",)),

    # ---- RUBRIC axis: a criterion, a threshold or a tolerance in a scene prompt -------
    ("rubric-criterion-phrase", "MUTANT",
     [(SCENES, S1_BODY, S1_BODY + "\n\n- The layers scroll at distinct rates.")],
     1, ("criterion vocabulary `distinct rates`",)),
    ("rubric-monotonic", "MUTANT",
     [(SCENES, S2_BODY, S2_BODY + "\n\n- The volume decreases monotonically.")],
     1, ("criterion vocabulary `monotonically`",)),
    # An inflection of a listed term. The list says `occlude`; a prompt would write
    # `occluded`, and a bare-literal match would walk straight past it.
    ("rubric-inflected", "MUTANT",
     [(SCENES, S1_BODY, S1_BODY + "\n\n- The car is occluded at a known tick.")],
     1, ("criterion vocabulary `occluded`",)),
    ("rubric-threshold-words", "MUTANT",
     [(SCENES, S2_BODY, S2_BODY + "\n\n- It breaks into at least twenty pieces.")],
     1, ("threshold vocabulary `at least`",)),
    ("rubric-threshold-symbol", "MUTANT",
     [(SCENES, S2_BODY, S2_BODY + "\n\n- The count is ≥ 20.")],
     1, ("threshold vocabulary `≥`",)),
    # THE ONE THAT MATTERS MOST. A leak that arrives through a vocabulary dict leaves the
    # scene body looking clean. This is why the assertion greps the RENDERED prompt.
    ("rubric-via-vocabulary-dict", "MUTANT",
     [(SCENES, TWO_D_RUST, TWO_D_RUST[:-1] + ' The light must ramp monotonically. "')],
     # One violation, not four: only the rust entry was edited, so only the rust rendering
     # leaks. A check reading the template instead would see zero.
     1, ("1 violation(s)", "s1_parallax/rust",
         "criterion vocabulary `monotonically`")),
    # The anti-invention guard: the term list is SCENES.md's vocabulary, not a new one.
    ("invented-term", "MUTANT",
     [(GUARD, RUBRIC_LIST_HEAD, RUBRIC_LIST_HEAD + '\n    "chromatic aberration budget",')],
     1, ("which is not in eval/SCENES.md",)),

    # ---- THE GUARD'S OWN SOURCE: the stack tuple has one owner ----------------------
    # `wholegame_prompts.STACKS` owns the tuple; `scene_prompts` re-exports the same
    # object. A guard that restates it keeps rendering and identity-checking the old
    # population at exit 0 after the owner changes -- and the population it prints is
    # derived from the copy, so nothing in its own output would show the drift (task
    # 194). The restated literal below is EQUAL to the owner's tuple, which is exactly
    # why only the identity guard can catch it.
    ("stack-literal-restated", "MUTANT",
     [(GUARD, STACKS_REF, STACKS_LITERAL)],
     1, ("AssertionError", "STACKS is not W.STACKS")),
    # DISARMED removes the identity guard and keeps the plant: the guard must go green
    # again, which is what proves the red row above was the guard and not the literal.
    ("disarmed-stack-identity", "DISARMED",
     [(GUARD, IDENTITY_GUARD, "if False:"),
      (GUARD, STACKS_REF, STACKS_LITERAL)],
     0, ("ok:",)),

    # ---- VARIANTS: inputs the guard must still pass on --------------------------------
    # Numbers that are not thresholds. A scene prompt is full of them.
    ("variant-plain-numbers", "VARIANT",
     [(SCENES, S1_BODY, S1_BODY + "\n\n- There are 3 lamp posts and the run is 900 ticks.")],
     0, ("ok:",)),
    # Contract vocabulary that reads like measurement and is functional spec.
    ("variant-contract-fields", "VARIANT",
     [(SCENES, S2_BODY,
       S2_BODY + "\n\n- `water.volume`, `drips.count` and `glass.screen` are reported"
                 "\n  every tick, and `just probe SEED` still works.")],
     0, ("ok:",)),
    # A game prompt already says `score` and `at least three kinds of enemy`. The rubric
    # assertion is addressed at SCENE prompts, and this row is what says so in code.
    ("variant-game-prompt-untouched", "VARIANT",
     [(GAMES, G1_BODY, G1_BODY + "\n\n- The score is at least eleven and monotonically rises.")],
     0, ("ok:",)),
    # Vocabulary substitution differing by stack is the whole design; it must not read as
    # rules diverging. 20 extra lines is over the limit, 8 is not.
    ("variant-vocabulary-differs", "VARIANT",
     [(SCENES, "{TWO_D_NOTE[stack]}",
       '{TWO_D_NOTE[stack]}{"" if stack == "rust" else chr(10).join(["- a line"] * 4)}')],
     0, ("ok:",)),

    # ---- DISARMED: remove the mechanism, keep the plant, require green ----------------
    # If either of these went red, the MUTANT row above it would be passing for some other
    # reason and would be measuring nothing.
    ("disarmed-body-regex", "DISARMED",
     [(GUARD, BODY_REGEX, 'r"^def (g\\d+_\\w+)\\(", src, re.M'),
      (SCENES, S1_BODY, S1_BODY + "\n\nDraw the sky with a Bevy shader.")],
     0, ("ok:",)),
    ("disarmed-rubric-terms", "DISARMED",
     [(GUARD, "RUBRIC_TERMS + BOUND_TERMS", "()"),
      (SCENES, S2_BODY, S2_BODY + "\n\n- The volume decreases monotonically.")],
     0, ("ok:",)),

    # ---- --diff against the checked-in snapshot --------------------------------------
    # The three assertions above cannot see #41 at all: an edit to a shared preamble keeps
    # every rule identical across stacks and names no engine. Only diffing the RENDERED
    # text against a stored copy catches it, which is why the snapshot is checked in.
    ("diff-matches-snapshot", "PRISTINE", [], 0,
     ("all 24 rendered prompts match the snapshot",), DIFF),
    # These two also MEASURE the isolation the separate module bought. An edit to the scene
    # preamble reaches 8 rendered prompts and stops there; an edit to the game preamble
    # reaches 16 and does not touch a scene. Under one shared preamble either would have
    # been 24, which is #41.
    ("diff-sees-shared-preamble-edit", "MUTANT",
     [(SCENES, "**The scene has no sound.**", "**The scene has some sound.**")],
     1, ("8 rendered prompt(s) differ", "s1_parallax__rust", "s2_glass__godot",
         "cross-regime"), DIFF),
    ("diff-sees-game-preamble-edit", "MUTANT",
     [(GAMES, "Keep the harness.", "Keep the harness, please.")],
     1, ("16 rendered prompt(s) differ", "g1_pong__rust", "g4_platformer__godot",
         "cross-regime"), DIFF),
    # A `.txt` the index does not name is invisible to every loop `--diff` runs, and it
    # reads to anyone opening the directory as a prompt that was sent. This is the shape a
    # snapshot re-recorded over an older one leaves behind when a task is removed.
    ("diff-refuses-unindexed-txt", "MUTANT",
     [(RENDERED + "/g9_ghost__rust.txt", None, "a prompt no index entry names\n")],
     1, ("named by no index entry", "g9_ghost__rust.txt"), DIFF),
    # VARIANT: the scope is prompt files. A note left in the directory is not one, and a
    # check that reddens on it is a check somebody moves the note out of.
    ("variant-non-prompt-file-in-snapshot", "VARIANT",
     [(RENDERED + "/NOTES.md", None, "why this snapshot exists\n")],
     0, ("all 24 rendered prompts match the snapshot",), DIFF),
    ("disarmed-stale-check", "DISARMED",
     [(GUARD, "    wanted = {f\"{k}.txt\" for k in idx}", "    return []\n    wanted = {}"),
      (RENDERED + "/g9_ghost__rust.txt", None, "a prompt no index entry names\n")],
     0, ("all 24 rendered prompts match the snapshot",), DIFF),
    ("diff-sees-a-new-task", "MUTANT",
     [(SCENES, '    "s2_glass": s2_glass,',
       '    "s2_glass": s2_glass,\n    "s3_extra": s1_parallax,')],
     1, ("s3_extra__rust", "exist now and are not in the snapshot"), DIFF),
]


def _build(dest: str) -> None:
    os.makedirs(os.path.join(dest, "tools"))
    os.makedirs(os.path.join(dest, "suites"))
    shutil.copy(os.path.join(EVAL, "tools", "prompt_guard.py"), os.path.join(dest, GUARD))
    for name in ("wholegame_prompts.py", "scene_prompts.py"):
        shutil.copy(os.path.join(EVAL, "suites", name), os.path.join(dest, "suites", name))
    shutil.copytree(os.path.join(EVAL, "suites", "rendered"),
                    os.path.join(dest, RENDERED))
    shutil.copy(os.path.join(EVAL, "SCENES.md"), os.path.join(dest, "SCENES.md"))


def _apply(dest: str, edits: list[tuple[str, str | None, str]]) -> str | None:
    """Apply one row's edits. `anchor is None` CREATES `rel` with `replacement` as its body.

    The anchor count is checked rather than assumed: an anchor that stopped matching would
    turn a MUTANT row into a run against an unedited tree, which passes as a VARIANT and
    reports nothing.
    """
    for rel, anchor, replacement in edits:
        path = os.path.join(dest, rel)
        if anchor is None:
            if os.path.exists(path):
                return f"{rel} already exists; this row means to create it"
            open(path, "w").write(replacement)
            continue
        src = open(path).read()
        n = src.count(anchor)
        if n != 1:
            return f"anchor appears {n} times in {rel}, expected exactly 1: {anchor[:60]!r}"
        open(path, "w").write(src.replace(anchor, replacement))
    return None


def main() -> int:
    print(f"prompt_guard controls: {len(ROWS)} rows\n")
    failures = []
    for row in ROWS:
        rid, kind, edits, want_exit, want_text = row[:5]
        argv = list(row[5]) if len(row) > 5 else []
        with tempfile.TemporaryDirectory() as tmp:
            _build(tmp)
            problem = _apply(tmp, edits)
            if problem:
                failures.append(f"{rid}: {problem}")
                print(f"  {kind:8} {rid:30} BROKEN  {problem}")
                continue
            # RENDERED is relative to the temp tree, not to the cwd the guard inherits.
            argv = [os.path.join(tmp, a) if a == RENDERED else a for a in argv]
            r = subprocess.run([sys.executable, os.path.join(tmp, GUARD)] + argv,
                               capture_output=True, text=True)
            out = r.stdout + r.stderr
            absent = [w for w in want_text if w not in out]
            ok = r.returncode == want_exit and not absent
            if not ok:
                failures.append(f"{rid}: exit {r.returncode} (wanted {want_exit}), "
                                f"absent from output: {absent!r}")
            first = next((l for l in out.splitlines() if l.strip()), "")
            print(f"  {kind:8} {rid:30} {'ok  ' if ok else 'FAIL'} "
                  f"exit={r.returncode} {first[:70]}")

    # The 2 things `_write_atomic` can get wrong that no row above can see: `mkstemp`
    # creates at 0600 and `os.replace` would publish that, and a temporary file left
    # behind is a file in the snapshot directory nothing owns.
    with tempfile.TemporaryDirectory() as tmp:
        _build(tmp)
        dest = os.path.join(tmp, "fresh")
        r = subprocess.run([sys.executable, os.path.join(tmp, GUARD), "--snapshot", dest],
                           capture_output=True, text=True)
        names = sorted(os.listdir(dest)) if os.path.isdir(dest) else []
        leftovers = [n for n in names if ".tmp" in n]
        unreadable = [n for n in names if not os.stat(os.path.join(dest, n)).st_mode & 0o044]
        ok = r.returncode == 0 and len(names) == 25 and not leftovers and not unreadable
        if not ok:
            failures.append(f"snapshot-publishes-cleanly: exit {r.returncode}, "
                            f"{len(names)} file(s), leftovers={leftovers}, "
                            f"unreadable={unreadable}")
        print(f"  {'FSPIN':8} {'snapshot-publishes-cleanly':30} {'ok  ' if ok else 'FAIL'} "
              f"exit={r.returncode} {len(names)} files, 0 temporaries, all readable")

    print()
    if failures:
        print(f"{len(failures)} control(s) failed:")
        for f in failures:
            print(f"  {f}")
        return 1
    kinds = {k: sum(1 for r in ROWS if r[1] == k) for k in ("MUTANT", "VARIANT",
                                                            "DISARMED", "PRISTINE")}
    print(f"all {len(ROWS) + 1} rows as declared: {kinds['MUTANT']} mutants red, "
          f"{kinds['VARIANT']} variants green, {kinds['DISARMED']} disarmed green, "
          f"{kinds['PRISTINE']} pristine green, 1 filesystem pin on what --snapshot "
          f"publishes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
