#!/usr/bin/env python3
"""Partition `eval/runs/` into EVIDENCE and REGENERABLE, and emit the backup set.

THE RULE, and it is a burden of proof, not a list of directories:

    A file under eval/runs/ is EVIDENCE until something in the tree itself
    proves it can be regenerated. The proof must name a producer that
    declared the file its own output. Nothing else counts, and a file no
    proof reaches stays evidence.

Stating it as a rule rather than an enumeration is deliberate. An enumeration
misses the next stack, the next cache directory and the next harness — this
project's most-repeated defect (AGENTS.md, "a rule whose trigger is a list").
It also fails in the dangerous direction: a missed name silently drops evidence
from the backup, and a backup that skipped something is indistinguishable from
one that copied everything until the day you need it.

The rule fails CLOSED. Every unproven file is copied. Over-copying costs disk;
under-copying costs the run.

TWO PROOFS ARE DISCHARGED HERE. Both are the producer's own declaration, read
out of the tree at classification time — not a name this file invented:

  1. CACHEDIR.TAG at a directory root.
     The Cache Directory Tagging Specification. Cargo writes it into every
     target dir. The tag says "a backup tool may skip me" in the words of the
     tool that filled the directory. `eval/runs/*/targets/*` and
     `_cargo-target-pristine` carry it; nothing here had to know their names.

  2. The work tree's own .gitignore.
     Every trial work tree is a git repo seeded from a template, and the
     template ships the .gitignore that names what its toolchain regenerates
     (`node_modules`, `/Library/`, `/target`, `.godot/`). The project declares
     its own build output, per stack, and adding a fifth stack updates this
     classifier for free.

WHY THE WORK TREES MATTER AT ALL. `wholegame.py` puts work trees OUTSIDE the
repo (`--work-root`, default ~/game-research-work) and archives each submission
as `artifacts/<tid>/submission.tar.gz`. The older `runner.py` did not: it wrote
`run_dir/work/<tid>` and `run_dir/targets/<tid>` INSIDE eval/runs/, and it
stores no tarball and no diff.patch — only a 3000-character `diff_stat` tail in
the trial JSON. So for every spec-change trial the work tree is the ONLY copy
of what the agent wrote. It is evidence, and the ticket's "136.99 GB of cargo
build output" quietly contained it.

USAGE

    evidence_set.py                    # measure and print the partition
    evidence_set.py --print0 > set.z   # NUL-delimited paths, for rsync/tar
    evidence_set.py --json out.json    # full manifest, incl. exclusion reasons

Exit status is 0 on a clean partition and 1 if any directory could not be read,
because a walk that silently skipped a subtree would report a smaller core and
look exactly like a correct one.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path

# The address is an input to the check (AGENTS.md rule 12): derive the runs root
# from this file's own location rather than letting a caller and a doc drift.
DEFAULT_RUNS_ROOT = Path(__file__).resolve().parent.parent / "runs"

CACHE_TAG = "CACHEDIR.TAG"
CACHE_TAG_SIGNATURE = b"Signature: 8a477f597d28d172789f06886806bc55"


# --------------------------------------------------------------------------
# gitignore matching
#
# Only the patterns the templates actually use are supported, and anything
# unsupported RAISES rather than being skipped. A matcher that silently ignores
# a pattern it does not understand under-copies, which is the failure this whole
# file exists to prevent.
# --------------------------------------------------------------------------

class Pattern:
    def __init__(self, raw: str):
        self.raw = raw
        self.negate = raw.startswith("!")
        body = raw[1:] if self.negate else raw
        self.dir_only = body.endswith("/")
        body = body.rstrip("/")
        # A pattern containing a slash anywhere but the trailing position is
        # anchored to the .gitignore's directory; otherwise it matches at any depth.
        self.anchored = "/" in body
        body = body.lstrip("/")
        self.body = body
        self.regex = re.compile(self._translate(body))

    @staticmethod
    def _translate(body: str) -> str:
        """gitwildmatch -> regex, for the subset in use.

        Raises on anything outside that subset: character classes and the
        `a/**/b` infix form are not used by any template here, and guessing at
        them would be a mechanism that runs and measures nothing.
        """
        if "[" in body or "]" in body:
            raise ValueError(f"unsupported gitignore character class: {body!r}")
        out = []
        i = 0
        while i < len(body):
            c = body[i]
            if c == "*":
                if body[i : i + 3] == "**/":
                    out.append("(?:.*/)?")
                    i += 3
                    continue
                if body[i : i + 2] == "**":
                    out.append(".*")
                    i += 2
                    continue
                out.append("[^/]*")
                i += 1
                continue
            if c == "?":
                out.append("[^/]")
                i += 1
                continue
            out.append(re.escape(c))
            i += 1
        return "^" + "".join(out) + "$"

    def matches(self, relpath: str, is_dir: bool) -> bool:
        if self.dir_only and not is_dir:
            return False
        if self.anchored:
            return bool(self.regex.match(relpath))
        # Unanchored: match the basename, or any path suffix beginning at a
        # component boundary — git matches such a pattern at every depth.
        parts = relpath.split("/")
        for start in range(len(parts)):
            if self.regex.match("/".join(parts[start:])):
                return True
        return False


class Ignore:
    """The patterns of one work tree's root .gitignore.

    Nested .gitignore files are NOT read. That is safe in one direction only,
    and it is the safe one: a nested file can only add ignores, so skipping it
    classifies more as evidence.
    """

    def __init__(self, root: Path):
        self.root = root
        self.patterns: list[Pattern] = []
        gi = root / ".gitignore"
        if gi.is_file():
            for line in gi.read_text(errors="replace").splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                self.patterns.append(Pattern(line))

    def ignored(self, relpath: str, is_dir: bool) -> Pattern | None:
        hit = None
        for p in self.patterns:
            if p.matches(relpath, is_dir):
                hit = None if p.negate else p
        return hit


# --------------------------------------------------------------------------
# classification
# --------------------------------------------------------------------------

def is_cache_dir(d: Path) -> bool:
    """True iff the directory carries a valid Cache Directory Tag.

    The signature is checked, not merely the filename. A file called
    CACHEDIR.TAG with the wrong first line is not a declaration by anything,
    and treating it as one would let a name in the evidence exclude the
    evidence.
    """
    tag = d / CACHE_TAG
    try:
        if not tag.is_file():
            return False
        with tag.open("rb") as fh:
            return fh.read(len(CACHE_TAG_SIGNATURE)) == CACHE_TAG_SIGNATURE
    except OSError:
        return False


class Partition:
    def __init__(self) -> None:
        self.evidence: list[tuple[Path, int]] = []
        self.evidence_bytes = 0
        self.regenerable_files = 0
        self.regenerable_bytes = 0
        self.reasons: Counter[str] = Counter()
        self.reason_bytes: Counter[str] = Counter()
        self.errors: list[str] = []
        self.work_trees: list[Path] = []
        self.cache_dirs: list[Path] = []

    def drop(self, reason: str, nbytes: int) -> None:
        self.regenerable_files += 1
        self.regenerable_bytes += nbytes
        self.reasons[reason] += 1
        self.reason_bytes[reason] += nbytes

    def keep(self, path: Path, nbytes: int) -> None:
        self.evidence.append((path, nbytes))
        self.evidence_bytes += nbytes


def size_of(p: Path) -> int | None:
    try:
        st = p.lstat()
    except OSError:
        return None
    return st.st_size


def partition(root: Path) -> Partition:
    part = Partition()

    def walk(d: Path, ignore: Ignore | None) -> None:
        # A directory that declares itself a cache is regenerable whole.
        if is_cache_dir(d):
            part.cache_dirs.append(d)
            for sub, _dirs, files in os.walk(d, onerror=part.errors.append):
                for f in files:
                    n = size_of(Path(sub) / f)
                    if n is None:
                        part.errors.append(f"unstattable: {Path(sub) / f}")
                        continue
                    part.drop("CACHEDIR.TAG", n)
            return

        # A git repo starts a new ignore scope. Its .git is kept: it holds the
        # baseline commit the agent's diff is taken against.
        if (d / ".git").is_dir():
            ignore = Ignore(d)
            part.work_trees.append(d)

        try:
            entries = list(os.scandir(d))
        except OSError as e:
            part.errors.append(f"unreadable dir {d}: {e}")
            return

        for e in entries:
            p = Path(e.path)
            try:
                is_dir = e.is_dir(follow_symlinks=False)
            except OSError as err:
                part.errors.append(f"unstattable: {p}: {err}")
                continue

            if ignore is not None and p != ignore.root:
                rel = str(p.relative_to(ignore.root))
                hit = ignore.ignored(rel, is_dir)
                if hit is not None:
                    reason = f".gitignore:{hit.raw}"
                    if is_dir:
                        for sub, _dirs, files in os.walk(p, onerror=part.errors.append):
                            for f in files:
                                n = size_of(Path(sub) / f)
                                if n is None:
                                    part.errors.append(f"unstattable: {Path(sub)/f}")
                                    continue
                                part.drop(reason, n)
                    else:
                        n = size_of(p)
                        if n is None:
                            part.errors.append(f"unstattable: {p}")
                        else:
                            part.drop(reason, n)
                    continue

            if is_dir:
                walk(p, ignore)
            else:
                n = size_of(p)
                if n is None:
                    part.errors.append(f"unstattable: {p}")
                else:
                    part.keep(p, n)

    walk(root, None)
    return part


def human(n: int) -> str:
    return f"{n / 1e9:.3f} GB ({n:,} bytes)"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--runs-root", type=Path, default=DEFAULT_RUNS_ROOT,
                    help=f"default {DEFAULT_RUNS_ROOT}")
    ap.add_argument("--print0", action="store_true",
                    help="write NUL-delimited evidence paths to stdout "
                         "(relative to --runs-root), for rsync --files-from "
                         "or tar -T; report goes to stderr")
    ap.add_argument("--json", type=Path, help="write the full manifest here")
    a = ap.parse_args()

    root = a.runs_root.resolve()
    if not root.is_dir():
        print(f"runs root does not exist: {root}", file=sys.stderr)
        return 2

    part = partition(root)
    out = sys.stderr if a.print0 else sys.stdout

    total_files = len(part.evidence) + part.regenerable_files
    total_bytes = part.evidence_bytes + part.regenerable_bytes

    print(f"runs root        {root}", file=out)
    print(f"total            {total_files:,} files  {human(total_bytes)}", file=out)
    print(f"EVIDENCE         {len(part.evidence):,} files  "
          f"{human(part.evidence_bytes)}", file=out)
    print(f"regenerable      {part.regenerable_files:,} files  "
          f"{human(part.regenerable_bytes)}", file=out)
    print(f"work trees       {len(part.work_trees)}", file=out)
    print(f"cache dirs       {len(part.cache_dirs)}", file=out)
    print("\nwhy each byte was dropped (the proof that discharged it):", file=out)
    for reason, nbytes in part.reason_bytes.most_common():
        print(f"  {human(nbytes):>34}  {part.reasons[reason]:>9,} files  "
              f"{reason}", file=out)

    if part.errors:
        print(f"\n{len(part.errors)} PATHS COULD NOT BE READ — the partition is "
              f"incomplete:", file=out)
        for e in part.errors[:20]:
            print(f"  {e}", file=out)

    if a.json:
        a.json.write_text(json.dumps({
            "runs_root": str(root),
            "total_files": total_files,
            "total_bytes": total_bytes,
            "evidence_files": len(part.evidence),
            "evidence_bytes": part.evidence_bytes,
            "regenerable_files": part.regenerable_files,
            "regenerable_bytes": part.regenerable_bytes,
            "work_trees": [str(p.relative_to(root)) for p in part.work_trees],
            "cache_dirs": [str(p.relative_to(root)) for p in part.cache_dirs],
            "dropped_by_reason": {
                r: {"files": part.reasons[r], "bytes": part.reason_bytes[r]}
                for r in part.reason_bytes
            },
            "errors": part.errors,
        }, indent=2))

    if a.print0:
        w = sys.stdout.buffer
        for p, _n in part.evidence:
            w.write(str(p.relative_to(root)).encode())
            w.write(b"\0")
        w.flush()

    return 1 if part.errors else 0


if __name__ == "__main__":
    sys.exit(main())
