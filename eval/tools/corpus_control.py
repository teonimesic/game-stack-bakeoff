#!/usr/bin/env python3
"""Pin `docstat.py`'s CORPUS selection in both directions (task 176).

`project_docs()` globbed the filesystem, so any markdown lying in the working tree entered
the corpus every reference check reads and the bare-trial-id ratchet is pinned to. Measured
2026-08-27 at `67d4967`: one untracked note at `staging/task-176-note.md` - a gitignored
directory, a file no review ever sees - took `--sweep` from 249 documents to 250 at exit 0,
and the same note under `staging/findings/` citing three trial ids took the ratchet from 18
to 21 and failed the sweep. It now reads `git ls-files`, which is the tree.

WHY THIS FILE EXISTS AND `--selftest` IS NOT ENOUGH. `docstat.py --selftest` runs the pins;
this runs them with one mechanism removed and asserts they FAIL. On a clean checkout the
filesystem and the index hold the same 238 documents, so every live row stays green under
the old glob - the discriminating input is a repository holding markdown that is not in it,
which `docstat._tree_fixture` builds and every mutant below attacks.

Two halves (AGENTS.md rule 15):

  MUTANTS   remove a mechanism and the pins must redden. Each is a plausible simplification
            - `glob_tree` is literally the shipped code of 2026-08-26, and `no_nul` is the
            obvious way to write the replacement.
  VARIANT   correct input the repaired reader could mishandle, which must stay green. A
            tracked path outside ASCII is C-quoted by `git ls-files` without `-z` and then
            fails `endswith(".md")`, so the document would leave the corpus silently. That
            row lives in `_corpus_pins` beside the rest and `no_nul` is what reddens it.

**The default runs the clean pass AND every mutant**, and is red if any of them survives.
`docstat --selftest` already makes the clean call, so a default that only repeated it would
be a gate duplicating a gate while the mutants ran nowhere but an operator's terminal.

Exit status is read UNPIPED (AGENTS.md rule 3). A single mutant run under `--mutate` is
EXPECTED to fail, so that mode inverts its status: exit 0 there would mean the pins cannot
see the mechanism the mutant names.

    python3 eval/tools/corpus_control.py                      # clean pass + every mutant
    python3 eval/tools/corpus_control.py --clean-only
    python3 eval/tools/corpus_control.py --list-mutants
    python3 eval/tools/corpus_control.py --mutate glob_tree --verbose
"""

from __future__ import annotations

import argparse
import glob
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import docstat as DS  # noqa: E402

MUTANTS = {
    "glob_tree": "project_docs() globs the filesystem again - the implementation this "
                 "replaced, under which an untracked scratch note is a project document",
    "no_dot_filter": "the dot-directory exclusion is dropped, so every SKILL.md joins the "
                     "corpus the ratchet is pinned to",
    "no_runs_filter": "the runs/ exclusion is dropped, so stored evidence is read as "
                      "guidance",
    "no_exists_filter": "a path in the index but deleted from the disk is kept, which the "
                        "callers open",
    "no_nul": "`-z` is dropped from the git listing, so a tracked path outside ASCII comes "
              "back C-quoted and leaves the corpus silently",
    "empty_on_failure": "_tracked_md returns [] when git fails instead of raising, so every "
                        "check downstream reports itself clean over 0 documents",
    "inherit_git_env": "the child keeps the caller's GIT_* variables, so an inherited "
                       "GIT_DIR decides which repository is read - and which one is written",
}

#: Every module attribute a mutant may rebind. `main` snapshots these before and after, so a
#: mutant that silently changed nothing is a FAILURE rather than a run of green rows.
PATCHED = ("project_docs", "_tracked_md", "_git_at", "_assert_own_repo")


def apply_mutant(name: str) -> None:
    """Remove one mechanism the pins name.

    REBINDING IS SAFE HERE ONLY BECAUSE EVERY READER LOOKS THESE UP AT CALL TIME, as module
    globals. `_corpus_pins` calls `project_docs(...)` and `_live_corpus` calls
    `_tracked_md(...)` by name; neither captures them at import or as a default argument,
    which is how a lint control once linted the real tree while claiming a bad root
    (AGENTS.md rule 12). `main` asserts the rebinding took rather than trusting it.
    """
    real_tracked = DS._tracked_md

    if name == "glob_tree":
        def globbed(root: str | None = None) -> list[str]:
            base = DS.ROOT if root is None else root
            return sorted(p for p in glob.glob(os.path.join(base, "**", "*.md"),
                                               recursive=True)
                          if not DS.is_vendored(p)
                          and f"{os.sep}runs{os.sep}" not in p)
        DS.project_docs = globbed

    elif name == "no_dot_filter":
        def no_dot(root: str | None = None) -> list[str]:
            base = DS.ROOT if root is None else root
            out = []
            for rel in DS._tracked_md(root=base):
                p = os.path.join(base, *rel.split("/"))
                if DS.is_vendored(p) or f"{os.sep}runs{os.sep}" in p:
                    continue
                if os.path.exists(p):
                    out.append(p)
            return sorted(out)
        DS.project_docs = no_dot

    elif name == "no_runs_filter":
        def no_runs(root: str | None = None) -> list[str]:
            base = DS.ROOT if root is None else root
            out = []
            for rel in DS._tracked_md(root=base):
                if any(part.startswith(".") for part in rel.split("/")):
                    continue
                p = os.path.join(base, *rel.split("/"))
                if DS.is_vendored(p) or not os.path.exists(p):
                    continue
                out.append(p)
            return sorted(out)
        DS.project_docs = no_runs

    elif name == "no_exists_filter":
        def no_exists(root: str | None = None) -> list[str]:
            base = DS.ROOT if root is None else root
            out = []
            for rel in DS._tracked_md(root=base):
                if any(part.startswith(".") for part in rel.split("/")):
                    continue
                p = os.path.join(base, *rel.split("/"))
                if DS.is_vendored(p) or f"{os.sep}runs{os.sep}" in p:
                    continue
                out.append(p)
            return sorted(out)
        DS.project_docs = no_exists

    elif name == "no_nul":
        def quoted(root: str | None = None, rev: str | None = None) -> list[str]:
            base = DS.ROOT if root is None else root
            ok, out = (DS._git_at(base, "ls-tree", "-r", "--name-only", rev) if rev
                       else DS._git_at(base, "ls-files"))
            if not ok:
                raise RuntimeError("git listing failed")
            return sorted(r for r in out.split("\n") if r.endswith(".md"))
        DS._tracked_md = quoted

    elif name == "inherit_git_env":
        def leaky(root: str, *args: str,
                  extra_env: dict[str, str] | None = None) -> tuple[bool, str]:
            child = dict(os.environ)          # GIT_* kept, which is the whole mutation
            child.update(extra_env or {})
            r = subprocess.run(["git", "-C", root, *args], capture_output=True,
                               text=True, check=False, env=child)
            if r.returncode != 0:
                return False, r.stderr or f"exit {r.returncode}"
            return True, r.stdout
        DS._git_at = leaky
        # BOTH mechanisms, because either alone hides the other. With the guard left in,
        # the fixture refuses and the WRITE never happens, so the row about the hostile
        # repository's index stays green and reports nothing about the scrub.
        DS._assert_own_repo = lambda tmp, extra_env: None

    elif name == "empty_on_failure":
        def quiet(root: str | None = None, rev: str | None = None) -> list[str]:
            try:
                return real_tracked(root=root, rev=rev)
            except RuntimeError:
                return []
        DS._tracked_md = quiet

    else:
        raise SystemExit(f"unknown mutant {name}; --list-mutants")


def controls(verbose: bool = True) -> list[str]:
    """`_corpus_pins` is the check. This runs it and hands back what came out wrong.

    The pins are not restated here. A control that keeps its own copy of the expectation
    has two copies to keep in step, and the one that goes stale is the copy nobody runs.
    """
    failed = DS._corpus_pins(verbose=verbose)
    for f in failed:
        print(f"  {f}")
    return failed


def sweep(verbose: bool = False) -> int:
    """The clean run and EVERY mutant, in one invocation.

    THIS IS WHAT THE CI STEP RUNS, and it is why the step exists at all. Without it the
    default was `_corpus_pins` a second time - the same call `docstat --selftest` already
    makes - so the gate duplicated a gate and no mutant ever ran outside an operator's
    terminal. A suite whose mutants are opt-in is a suite whose mutants are the one thing
    nobody re-runs. Raised by CodeRabbit on PR #54.
    """
    print(f"corpus pins over {len(DS.project_docs())} project documents, "
          f"{len(DS._tracked_md())} markdown paths in the tree\n")
    clean = controls(verbose=verbose)
    print(f"CLEAN  {len(clean)} pin(s) came out wrong, expected 0\n")

    pristine = {n: getattr(DS, n) for n in PATCHED}
    survived, killed = [], []
    for name in MUTANTS:
        for n, v in pristine.items():           # a mutant must not leak into the next
            setattr(DS, n, v)
        apply_mutant(name)
        if all(getattr(DS, n) is pristine[n] for n in PATCHED):
            survived.append(f"{name}: rebound nothing - it is not testing anything")
            continue
        failed = controls(verbose=verbose)
        print(f"MUTANT {name:<18} {len(failed)} pin(s) red"
              + ("  <- SURVIVED" if not failed else ""))
        (killed if failed else survived).append(name)
    for n, v in pristine.items():
        setattr(DS, n, v)

    print(f"\n{len(killed)} of {len(MUTANTS)} mutants died; "
          f"{len(clean)} pin(s) wrong on the clean tree")
    for s in survived:
        print(f"  SURVIVED  {s}")
    return 1 if clean or survived else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--mutate", metavar="NAME")
    ap.add_argument("--list-mutants", action="store_true")
    ap.add_argument("--clean-only", action="store_true",
                    help="the pins on the unmutated tree, without the mutant sweep")
    ap.add_argument("--verbose", action="store_true",
                    help="print every pin's case, not only the verdict")
    a = ap.parse_args()

    if a.list_mutants:
        for k, v in MUTANTS.items():
            print(f"  {k:<18} {v}")
        return 0

    if a.mutate:
        before = tuple(getattr(DS, n) for n in PATCHED)
        apply_mutant(a.mutate)
        after = tuple(getattr(DS, n) for n in PATCHED)
        if before == after:
            print(f"MUTANT {a.mutate} changed nothing - it is not testing anything")
            return 1
        print(f"MUTANT {a.mutate}: {MUTANTS[a.mutate]}\n")
        failed = controls(verbose=a.verbose)
        print(f"\n{len(failed)} pin(s) came out wrong. A mutant run is EXPECTED to fail: "
              "exit 0 here would mean the pins cannot see the mechanism they name.")
        return 0 if failed else 1

    if a.clean_only:
        print(f"corpus pins over {len(DS.project_docs())} project documents, "
              f"{len(DS._tracked_md())} markdown paths in the tree\n")
        failed = controls(verbose=a.verbose)
        print(f"\n{len(failed)} pin(s) came out wrong")
        return 1 if failed else 0

    return sweep(verbose=a.verbose)


if __name__ == "__main__":
    sys.exit(main())
