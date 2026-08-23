#!/usr/bin/env python3
"""Controls for `evidence_set.py`: does its .gitignore matcher agree with git?

`evidence_set.py` decides what NOT to back up. A matcher that over-ignores drops
evidence from the copy, and a copy that skipped something is indistinguishable
from a complete one until the day it is needed. So the matcher needs an
adjudicator that is not itself.

Git is that adjudicator. This runs three controls:

  NEGATIVE   Real path lists from the real work trees, reproduced as empty files
             in a scratch repo with the real .gitignore. `git status --ignored`
             gives git's own partition; the matcher must reproduce it exactly.
             Establishes it does not over-ignore on the data it will be run on.

  POSITIVE   The same comparison must be non-trivial: git must classify some
             files ignored AND some not. A fixture where everything lands in one
             bucket would be passed by a matcher that always answers that bucket.

  ADVERSARIAL  Hand-built near-misses — names that look like build output but
             are not (`src/node_modules_helper.ts`, `docs/target.md`,
             `Assets/Library.cs`) and real ignorables buried at depth. Git
             adjudicates these too.

And a MUTANT (`--mutate NAME`) removes a mechanism the matcher relies on, to
prove these controls can go red. A control that has never failed and a control
that cannot fail look identical from the outside.

    ./evidence_set_control.py                 # run the controls
    ./evidence_set_control.py --mutate dir_only
    ./evidence_set_control.py --list-mutants
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import evidence_set as ES  # noqa: E402

#: Set from --runs-root in main(). Defaults to the same place `evidence_set.py`
#: derives, so the control and the thing it controls address one tree unless a
#: caller deliberately says otherwise (AGENTS.md rule 12).
RUNS = ES.DEFAULT_RUNS_ROOT

# Paths that git never reports and that the matcher never sees, so they are
# excluded from both sides rather than being a difference nobody can act on.
GIT_INTERNAL = ".git/"

MUTANTS = {
    "dir_only": "directory-only patterns (`.godot/`) also match plain files",
    "anchored": "leading-slash patterns (`/Library/`) match at any depth",
    "depth": "unanchored patterns (`node_modules`) match only at the root",
    "last_wins": "first matching pattern wins instead of the last",
}


def apply_mutant(name: str) -> None:
    if name == "dir_only":
        orig = ES.Pattern.matches

        def matches(self, relpath, is_dir):
            self_dir_only, self.dir_only = self.dir_only, False
            try:
                return orig(self, relpath, is_dir)
            finally:
                self.dir_only = self_dir_only
        ES.Pattern.matches = matches
    elif name == "anchored":
        orig = ES.Pattern.matches

        def matches(self, relpath, is_dir):
            was, self.anchored = self.anchored, False
            try:
                return orig(self, relpath, is_dir)
            finally:
                self.anchored = was
        ES.Pattern.matches = matches
    elif name == "depth":
        orig = ES.Pattern.matches

        def matches(self, relpath, is_dir):
            was, self.anchored = self.anchored, True
            try:
                return orig(self, relpath, is_dir)
            finally:
                self.anchored = was
        ES.Pattern.matches = matches
    elif name == "last_wins":
        def ignored(self, relpath, is_dir):
            for p in self.patterns:
                if p.matches(relpath, is_dir):
                    return None if p.negate else p
            return None
        ES.Ignore.ignored = ignored
    else:
        raise SystemExit(f"unknown mutant {name!r}; --list-mutants")


# --------------------------------------------------------------------------

def distinct_work_trees() -> list[Path]:
    """One work tree per distinct root .gitignore, so every shipped ignore
    file is exercised without walking 77 near-copies."""
    seen: dict[str, Path] = {}
    for gi in RUNS.glob("*/work/*/.gitignore"):
        seen.setdefault(gi.read_text(errors="replace"), gi.parent)
    for gi in RUNS.glob("*/*/work/*/.gitignore"):
        seen.setdefault(gi.read_text(errors="replace"), gi.parent)
    for gi in RUNS.glob("_control/*/.gitignore"):
        seen.setdefault(gi.read_text(errors="replace"), gi.parent)
    return sorted(seen.values())


def relpaths(tree: Path, cap: int) -> list[str]:
    out: list[str] = []
    for sub, dirs, files in os.walk(tree):
        if ".git" in dirs:
            dirs.remove(".git")
        for f in files:
            out.append(str((Path(sub) / f).relative_to(tree)))
            if len(out) >= cap:
                return out
    return out


ADVERSARIAL = [
    # look like build output, are not
    "src/node_modules_helper.ts",
    "docs/target.md",
    "docs/notes-about-Library.md",
    "Assets/Library.cs",
    "src/coverage_report_writer.ts",
    "tests/godot_notes.md",
    "tools/build_helper.py",
    "src/obj_loader.ts",
    # real ignorables, buried where a root-only matcher would miss them
    "packages/inner/node_modules/left-pad/index.js",
    "sub/deep/.godot/uid_cache.bin",
    "a/b/c/screenshot.actual.png",
    # things that must survive
    "tests/golden/blessed.png",
    "crates/game/src/main.rs",
    "AGENTS.md",
]

# SYNTHETIC case. The four templates' .gitignore files between them never
# exercise anchoring, directory-only matching or a negation, so three of the
# four mutants below were INERT against real data and "10/10 passed" said
# nothing about those branches. This fixture exists to exercise them — the
# variant half of AGENTS.md rule 15, which the real trees cannot supply.
#
# It is not hypothetical maintenance: the moment a fifth template ships a
# `!keep.this` line, the matcher's precedence starts mattering to what gets
# backed up, and this is the only place that would notice.
SYNTHETIC_IGNORE = """\
/Library/
.godot/
node_modules
*.log
!important.log
"""

SYNTHETIC_PATHS = [
    "Library",                              # a FILE; `/Library/` is dir-only
    "Assets/Library/foo.dll",               # `/Library/` is anchored to root
    "deep/node_modules/left-pad/index.js",  # unanchored, matches at depth
    "node_modules/root-pkg/index.js",
    "sub/.godot/uid_cache.bin",
    "debug.log",
    "important.log",                        # re-included by the last pattern
    "src/main.rs",
    "notes/godot.md",
]


def git_partition(fixture: Path, all_paths: list[str]) -> tuple[set[str], set[str]]:
    """Git's own verdict on every path in `all_paths`.

    `git status` collapses a wholly-ignored directory to one entry ending in
    `/` — `Library/`, not its 2,171 files. Comparing that raw against a
    per-file matcher produces thousands of phantom disagreements, so the
    directory entries are expanded back over the path list here. This is a
    defect in the COMPARISON, not in either partition, and it is the reason
    the two are reconciled explicitly rather than eyeballed.
    """
    subprocess.run(["git", "init", "-q"], cwd=fixture, check=True,
                   capture_output=True)
    r = subprocess.run(
        ["git", "status", "--porcelain", "-uall", "--ignored=matching"],
        cwd=fixture, check=True, capture_output=True, text=True)
    ignored_files: set[str] = set()
    ignored_dirs: list[str] = []
    for line in r.stdout.splitlines():
        code, path = line[:2], line[3:]
        if path.startswith('"') and path.endswith('"'):
            path = path[1:-1].encode().decode("unicode_escape")
        if path.startswith(GIT_INTERNAL):
            continue
        if code != "!!":
            continue
        if path.endswith("/"):
            ignored_dirs.append(path)
        else:
            ignored_files.add(path)

    ignored = set()
    for p in all_paths:
        if p in ignored_files or any(p.startswith(d) for d in ignored_dirs):
            ignored.add(p)
    return ignored, set(all_paths) - ignored


def matcher_partition(fixture: Path, paths: list[str]) -> tuple[set[str], set[str]]:
    ig = ES.Ignore(fixture)
    ignored, kept = set(), set()
    for rel in paths:
        p = Path(rel)
        hit = None
        # git ignores a file if the file or ANY parent directory is ignored.
        for i in range(len(p.parts) - 1):
            d = "/".join(p.parts[: i + 1])
            if ig.ignored(d, True) is not None:
                hit = d
                break
        if hit is None and ig.ignored(rel, False) is not None:
            hit = rel
        (ignored if hit else kept).add(rel)
    return ignored, kept


def build_fixture(dest: Path, gitignore: str, paths: list[str]) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    (dest / ".gitignore").write_text(gitignore)
    for rel in paths:
        f = dest / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.touch()


def run_case(name: str, gitignore: str, paths: list[str], scratch: Path,
             require_both: bool) -> tuple[bool, str, int]:
    """Returns (passed, message, n_ignored_by_git).

    `require_both` is the positive control, and it is demanded of the
    adversarial fixtures rather than of every fixture: a rust work tree
    genuinely contains nothing its .gitignore names — cargo's output lives in
    `<run>/targets/`, not in the tree — so requiring both buckets there would
    fail a correct partition. The suite as a whole still asserts that some
    fixture exercised the ignoring path, which is what the positive control is
    actually for.
    """
    fixture = scratch / name
    if fixture.exists():
        shutil.rmtree(fixture)
    build_fixture(fixture, gitignore, paths)
    all_paths = sorted(set(paths) | {".gitignore"})
    g_ign, g_keep = git_partition(fixture, all_paths)
    m_ign, m_keep = matcher_partition(fixture, all_paths)

    if require_both and (not g_ign or not g_keep):
        return False, (f"{name}: fixture is degenerate — git put "
                       f"{len(g_ign)} in ignored and {len(g_keep)} in kept. "
                       f"A matcher answering one bucket always would pass it."), 0

    over = sorted(m_ign - g_ign)      # matcher ignores what git keeps -> DATA LOSS
    under = sorted(g_ign - m_ign)     # matcher keeps what git ignores -> over-copy
    if over or under:
        msg = [f"{name}: {len(g_ign)} ignored / {len(g_keep)} kept by git"]
        if over:
            msg.append(f"  OVER-IGNORED ({len(over)}) — these would be LOST: "
                       f"{over[:8]}")
        if under:
            msg.append(f"  under-ignored ({len(under)}) — copied needlessly: "
                       f"{under[:8]}")
        return False, "\n".join(msg), len(g_ign)
    return True, (f"{name}: agrees with git on {len(all_paths)} paths "
                  f"({len(g_ign)} ignored, {len(g_keep)} kept)"), len(g_ign)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mutate", help="apply a named mutation, expect red")
    ap.add_argument("--list-mutants", action="store_true")
    ap.add_argument("--cap", type=int, default=4000,
                    help="max real paths sampled per work tree (default 4000)")
    ap.add_argument("--runs-root", type=Path, default=None,
                    help="the eval/runs tree to draw fixtures from; defaults to "
                         "the one evidence_set.py addresses")
    a = ap.parse_args()

    global RUNS
    if a.runs_root is not None:
        RUNS = a.runs_root.resolve()

    if a.list_mutants:
        for k, v in MUTANTS.items():
            print(f"  {k:<12} {v}")
        return 0
    if a.mutate:
        apply_mutant(a.mutate)
        print(f"MUTANT ACTIVE: {a.mutate} — {MUTANTS[a.mutate]}\n")

    if not RUNS.is_dir():
        print(f"runs root missing: {RUNS}", file=sys.stderr)
        return 2

    results: list[tuple[bool, str, int]] = []
    with tempfile.TemporaryDirectory(prefix="evset-control-") as td:
        scratch = Path(td)

        trees = distinct_work_trees()
        if not trees:
            print("no work trees found — nothing was controlled", file=sys.stderr)
            return 2
        for tree in trees:
            gi = (tree / ".gitignore").read_text(errors="replace")
            paths = relpaths(tree, a.cap)
            results.append(run_case(f"real__{tree.name}", gi, paths, scratch,
                                    require_both=False))

        # ADVERSARIAL: every shipped .gitignore against the hand-built probes.
        # These carry the per-case positive control — each fixture is built to
        # contain both ignorables and near-misses.
        for tree in trees:
            gi = (tree / ".gitignore").read_text(errors="replace")
            results.append(run_case(f"adv__{tree.name}", gi, list(ADVERSARIAL),
                                    scratch, require_both=True))

        # SYNTHETIC: the branches no shipped .gitignore reaches.
        results.append(run_case("synthetic__precedence", SYNTHETIC_IGNORE,
                                list(SYNTHETIC_PATHS), scratch,
                                require_both=True))

    npass = sum(1 for ok, _, _ in results if ok)
    for ok, msg, _ in results:
        print(f"[{'PASS' if ok else 'FAIL'}] {msg}")

    # SUITE-LEVEL POSITIVE CONTROL. If nothing anywhere was ignored, every case
    # above was passed by a matcher that never had to say yes, and "10/10" would
    # mean nothing. total=0 passed=0 is indistinguishable from correct.
    total_ignored = sum(n for _, _, n in results)
    print(f"\n{npass}/{len(results)} controls passed; "
          f"git classified {total_ignored:,} paths ignored across the suite")
    if total_ignored == 0:
        print("NOTHING WAS EVER IGNORED — the suite exercised only one branch "
              "and establishes nothing.")
        return 1

    if a.mutate:
        if npass == len(results):
            print("MUTANT SURVIVED — these controls cannot detect this defect.")
            return 1
        print("mutant killed: the controls can go red.")
        return 0
    return 0 if npass == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
