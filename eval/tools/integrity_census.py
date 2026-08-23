#!/usr/bin/env python3
"""How often has the debris the two integrity gates look for actually occurred, and how much
margin does the duplicate-fragment window still have?

WHY THIS EXISTS. `docstat.py`'s two integrity checks both measure 0 over the corpus at HEAD,
and a gate whose triggering case has not occurred is indistinguishable, from inside, from a
gate that cannot fire (`total=0 passed=0`). Their pins answer the second half — each fires on
a real historical blob — and nothing answered the first: *how often does this defect happen?*
A census over one commit cannot ask that, because the tree at any commit holds only the
defects nobody has repaired yet.

The population is therefore EVERY REVISION of every reference document across `--all`, not
the tree at HEAD. That is the only population in which a defect that was introduced and later
fixed is still visible.

    python3 eval/tools/integrity_census.py             # the historical census, both checks
    python3 eval/tools/integrity_census.py --windows   # the window sweep, at HEAD
    python3 eval/tools/integrity_census.py --control   # just the known-answer control

A VERSION IS NOT AN INCIDENT. An unrepaired defect is re-counted in every commit that touches
its file, so a raw version count reports how busy the file was, not how often the defect
happened. Incidents are therefore keyed on the DUPLICATED TEXT ITSELF: same text, same file,
one incident. Both figures are printed, because their ratio is the thing that would otherwise
be silently confused.

THE CONTROL RUNS FIRST AND THE CENSUS DOES NOT PRINT WITHOUT IT (AGENTS.md rule 12). Two blobs
have an answer stated in advance by `docstat.py`'s own pins, and this file re-states neither:
it calls those pin functions, so there is no second spelling of either address to drift. A
census that returns one value across a population it exists to discriminate is reporting the
instrument, and the cheapest way to find that out is a row whose true value you already know.

WHAT THIS IS NOT. It is a census, not a gate: it exits 1 only when the control fails or the
population is empty, never because it found a historical defect. Every defect it can find in
history is one that was already repaired.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import docstat as DS  # noqa: E402

#: Window sizes the sweep reports. The shipped value sits in `DS._DUP_FRAGMENT_WINDOW`; these
#: bracket it on both sides so the row that decides it is visible next to its neighbours.
SWEEP_WINDOWS = (8, 9, 10, 11, 12, 13, 14, 16)


def _git(*args: str) -> str:
    """git in the audited repository. Unpiped, and a failure is raised, never returned as 0.

    `DS._git` deliberately swallows a non-zero exit because several of its callers ASK a
    question whose negative answer is an error. Nothing here does: every call below is a
    read that must succeed, and `cmd || echo 0` on a measurement is the shape this project
    calls the most dangerous a broken check can take (AGENTS.md rule 3).
    """
    r = subprocess.run(["git", "-C", DS.ROOT, *args], capture_output=True, text=True,
                       check=False)
    if r.returncode != 0:
        raise SystemExit(f"git {' '.join(args)} failed ({r.returncode}): {r.stderr.strip()[:300]}")
    return r.stdout


def is_reference_path(p: str) -> bool:
    """`reference_docs()`'s membership rule, expressed over a path in a git tree.

    THE TWO SPELLINGS CANNOT BE MADE ONE. `reference_docs()` walks a filesystem and can only
    describe the tree that exists now; a historical census has to decide membership for a
    path in a commit, where no file is on disk. So this is a second statement of the same
    rule, and the guard against drift is that it is stated as the same three clauses:
    markdown, not vendored, not stored run data -- plus `SKILL.md` anywhere, which is the one
    thing `project_docs()` misses and `_all_skill_files()` adds.
    """
    if not p.endswith(".md"):
        return False
    if DS.is_vendored(p) or p.startswith("runs/") or "/runs/" in p:
        return False
    if p.startswith("worktrees/") or "/worktrees/" in p:
        return False
    # `glob` does not descend into a dot-directory, so `project_docs()` contains no path under
    # one; `_all_skill_files()` walks and adds exactly the SKILL.md files that live there.
    if os.path.basename(p) != "SKILL.md" and p.split("/")[0].startswith("."):
        return False
    return True


def control(verbose: bool = True) -> int:
    """Both pins, run through the code that owns them. Red here stops everything below.

    `_orphan_tail_pins` and `_duplicate_fragment_pins` return a list of problems and an empty
    list means every case came out as stated -- including the RED ones, which is the half that
    matters here: this census is worthless if the checks cannot fire at all.
    """
    problems = DS._orphan_tail_pins() + DS._duplicate_fragment_pins()
    if verbose:
        for p in problems:
            print(f"  RED  {p}")
        if not problems:
            print("  ok   both checks reproduce their known-answer blobs "
                  "(1f6fb65:eval/FINDINGS.md line 6; 75dde71:DECISIONS.md line 745, 4 windows)")
    return 1 if problems else 0


def commits() -> list[str]:
    """Every commit reachable from any ref."""
    return _git("rev-list", "--all").split()


def revisions() -> list[tuple[str, str]]:
    """(blob, path) for every version of every reference document, over every commit's TREE.

    READING THE TREES IS WHY THIS IS SLOWER THAN THE OBVIOUS THING, AND WHY IT IS RIGHT. The
    obvious enumeration is `git log --all --name-only`, which is 80x faster and WRONG: git
    omits a merge commit's file list by default, so any document whose only introduction was a
    merge is invisible. Measured on this repository -- `git log --name-only` finds 216 paths
    and `.agents/skills/update-readme/SKILL.md`, tracked and added by merge `6129034`, is not
    one of them; the tree walk finds 218, and 1,543 distinct (blob, path) versions against the
    1,196 the log-based enumeration reached. It under-counted the denominator by 22% and named
    no error doing it.

    `--diff-merges=first-parent` also recovers all 218, and this walks trees instead because
    the tree IS the population: no rename detection, no diff semantics, nothing to be subtly
    wrong about. `enumeration_control` asserts the result against `git ls-files` rather than
    trusting either, and `no_skill_files` and `empty_enumeration` are the other two ways it has
    been pinned red.
    """
    out = set()
    for c in commits():
        for line in _git("ls-tree", "-r", "--format=%(objectname) %(path)", c).splitlines():
            sha, _, path = line.partition(" ")
            if path and is_reference_path(path):
                out.add((sha, path))
    return sorted(out)


def enumeration_control(pairs: list[tuple[str, str]]) -> int:
    """Every reference document tracked TODAY must appear in the historical enumeration.

    A denominator is the whole of a base rate, and an enumeration that quietly drops files
    reports a smaller one with nothing able to disagree — which is exactly what happened here
    before this row existed. HEAD's own file list is the one population whose membership can
    be stated in advance, so it is the known-answer case (AGENTS.md rule 12).

    It cannot go the other way: history legitimately holds paths HEAD does not, which is the
    point of the census.
    """
    tracked = {p for p in _git("ls-files").splitlines() if is_reference_path(p)}
    seen = {p for _, p in pairs}
    missing = sorted(tracked - seen)
    if missing:
        print(f"  RED  {len(missing)} reference document(s) tracked at HEAD are absent from "
              f"the history enumeration, so the denominator is understated: {missing[:5]}")
        return 1
    print(f"  ok   all {len(tracked)} reference documents tracked at HEAD appear in the "
          f"enumeration, which reaches {len(seen)} paths in total")
    return 0


def read_blobs(pairs: list[tuple[str, str]]) -> dict[tuple[str, str], str]:
    """Every blob in one `git cat-file --batch`, rather than one subprocess per version.

    1,500-odd `git show` calls is a minute of process spawning for a question that should cost
    a second. `--batch` reads object ids on stdin and answers with a header line and then
    exactly that many bytes, so the framing is by LENGTH and never by a delimiter that could
    occur inside a document.
    """
    order = sorted({sha for sha, _ in pairs})
    r = subprocess.run(["git", "-C", DS.ROOT, "cat-file", "--batch"],
                       input="".join(f"{s}\n" for s in order).encode(),
                       capture_output=True, check=False)
    if r.returncode != 0:
        raise SystemExit(f"git cat-file --batch failed ({r.returncode}): "
                         f"{r.stderr.decode(errors='replace')[:300]}")
    text_of, buf, i = {}, r.stdout, 0
    for sha in order:
        nl = buf.index(b"\n", i)
        header = buf[i:nl].decode(errors="replace").split()
        i = nl + 1
        if len(header) < 3:          # "<oid> missing" - unreachable, not an empty document
            continue
        size = int(header[2])
        text_of[sha] = buf[i:i + size].decode("utf-8", errors="replace")
        i += size + 1                # git writes a trailing newline after the object
    return {(sha, p): text_of[sha] for sha, p in pairs if sha in text_of}


def census() -> int:
    print("KNOWN-ANSWER CONTROL")
    if control():
        print("\nthe control failed - the extraction below would be unbelievable, stopping")
        return 1

    n_commits = len(commits())
    pairs = revisions()
    if not pairs:
        print("\nno reference-document versions found - this census is aimed at nothing")
        return 1
    if enumeration_control(pairs):
        print("\nthe enumeration is incomplete, so any rate below it would be understated")
        return 1
    blobs = read_blobs(pairs)

    orphan: dict[tuple[str, str], list[str]] = {}
    fragment: dict[tuple[str, str], list[str]] = {}
    for (sha, p), text in blobs.items():
        for h in DS._check_orphaned_tail(text, p):
            orphan.setdefault((p, h.split("produces: ", 1)[-1]), []).append(sha)
        for h in DS._check_duplicate_fragment(text, p):
            fragment.setdefault((p, h.split("leaves behind: ", 1)[-1]), []).append(sha)

    seen = set(blobs)
    print(f"\nPOPULATION: {len(blobs)} distinct (version, path) pairs of reference documents, "
          f"over {len({p for _, p in pairs})} paths and all {n_commits} commits reachable "
          f"from --all")

    for title, hits, unit in (
        ("STRANDED TAIL   (a whole line recurring in the paragraph above it)", orphan, "line"),
        (f"DUPLICATE FRAGMENT   (a {DS._DUP_FRAGMENT_WINDOW}-word window recurring in one "
         f"block)", fragment, "window"),
    ):
        # A SPAN IS NOT AN INCIDENT AND A VERSION IS NOT EITHER. One rewrite leaving one
        # duplicated sentence behind is seen as several OVERLAPPING windows of it, and is then
        # re-counted in every version of the file until somebody repairs it. Summing either
        # would report the file's edit rate. What overlapping views of a single rewrite share
        # is the exact set of versions they appear in, so that set is the grouping key.
        #
        # IT IS A GROUPING, NOT A PROOF: two genuinely separate defects introduced in one
        # commit and repaired in another would share a version set and be reported as one.
        # The unaggregated span count is printed beside it for that reason.
        files = {p for p, _ in hits}
        carrying = {c for cs in hits.values() for c in cs}
        groups: dict[tuple[str, tuple[str, ...]], list[str]] = {}
        for (p, txt), cs in hits.items():
            groups.setdefault((p, tuple(sorted(cs))), []).append(txt)
        print(f"\n{title}")
        print(f"  {len(groups)} incident(s) - spans sharing one set of versions - "
              f"from {len(hits)} duplicated {unit}(s) in {len(files)} file(s), "
              f"present in {len(carrying)} of the {len(seen)} versions")
        for (p, cs), texts in sorted(groups.items()):
            print(f"    {p}: {len(cs)} versions, {len(texts)} overlapping {unit}(s), "
                  f"e.g. {sorted(texts)[0][:62]!r}")
    return 0


def windows() -> int:
    """The false-positive count that decides the window, at every size around the shipped one.

    THIS IS THE PRODUCER FOR A NUMBER THAT WAS PUBLISHED WITHOUT ONE. `docstat.py`'s comment
    and `audit-docs/SKILL.md` both say to re-measure this count before retuning the window,
    and until this existed the only way to do it was to re-derive the sweep by hand -- so the
    published figure could go stale with nothing able to disagree with it.

    HITS AND DISTINCT PHRASES ARE BOTH REPORTED, and the pair is the point. A hit count
    conflates *the corpus acquired a new kind of false positive* -- which is a reason to move
    the window -- with *one existing false positive got quoted somewhere else*, which is not.
    """
    if control(verbose=False):
        print("the known-answer control failed; run --control")
        return 1
    docs = DS.reference_docs()
    if not docs:
        print("no reference documents - this sweep is aimed at nothing")
        return 1
    texts = {os.path.relpath(p, DS.ROOT): open(p, encoding="utf-8", errors="replace").read()
             for p in docs}
    prefix = DS._git("show", "75dde71:DECISIONS.md")

    print(f"{len(docs)} reference documents at HEAD, live AND archive; "
          f"shipped window is {DS._DUP_FRAGMENT_WINDOW}\n")
    print(f"  {'window':>6}  {'corpus hits':>11}  {'distinct phrases':>16}  "
          f"{'files':>5}  {'the real defect':>15}")
    original = DS._DUP_FRAGMENT_WINDOW
    rows = []
    try:
        for w in SWEEP_WINDOWS:
            DS._DUP_FRAGMENT_WINDOW = w
            hits = [(rel, h.split("leaves behind: ", 1)[-1])
                    for rel, t in texts.items() for h in DS._check_duplicate_fragment(t, rel)]
            phrases = {ph for _, ph in hits}
            # The real defect, from the blob that carried it: a window with 0 corpus hits and
            # 0 on the defect is not a safe setting, it is a blind one.
            real = len(DS._check_duplicate_fragment(prefix, "DECISIONS.md")) if prefix else -1
            mark = "  <- shipped" if w == original else ""
            print(f"  {w:>6}  {len(hits):>11}  {len(phrases):>16}  "
                  f"{len({f for f, _ in hits}):>5}  "
                  f"{real if real >= 0 else 'unread':>15}{mark}")
            rows.append((w, hits, phrases))
    finally:
        DS._DUP_FRAGMENT_WINDOW = original

    if not prefix.strip():
        print("\n  NOTE: 75dde71:DECISIONS.md could not be read, so the last column is "
              "unmeasured - on a shallow clone this sweep shows only the false-positive half")

    print("\nWhat the false positives below the boundary actually are:")
    for w, hits, phrases in rows:
        if not hits or w > original:
            continue
        print(f"\n  window {w}: {len(hits)} hit(s), {len(phrases)} distinct phrase(s)")
        for ph in sorted(phrases):
            where = sorted({f for f, q in hits if q == ph})
            print(f"    {sum(1 for _, q in hits if q == ph)}x {ph[:72]!r}")
            print(f"       in {', '.join(where)}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--windows", action="store_true",
                    help="sweep the duplicate-fragment window over the corpus at HEAD")
    ap.add_argument("--control", action="store_true",
                    help="only the known-answer control both censuses depend on")
    a = ap.parse_args()
    if a.control:
        print("KNOWN-ANSWER CONTROL")
        return control()
    return windows() if a.windows else census()


if __name__ == "__main__":
    sys.exit(main())
