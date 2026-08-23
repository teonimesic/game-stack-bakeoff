#!/usr/bin/env python3
"""Analyse this project's documentation: structure, size, and names that do not exist.

WHY THIS EXISTS
---------------
The prose version of these checks lives in the `audit-docs` skill, and prose is executed
by a person. Two failures came from doing it by hand:

  A fence-blind heading scan reported a malformed heading and a 6.7k orphan section in
  FINDINGS.md. It was a GDScript doc-comment (`## Longer for the very first serve...`)
  inside a ``` block. The file was fine; the analysis was not, and its output looked
  exactly like a finding about the file.

  `RUBRIC.md` named five judge aspects that do not exist. Nothing but a mechanical
  cross-check against `judge/aspects.py` would have caught it — a reader sees a plausible
  list, and unlike code, prose gets no argparse error.

Both are the same shape: an unvalidated probe whose wrong answer is indistinguishable
from a real reading.

Usage, from eval/:
    python3 tools/docstat.py                  # size + structure of project docs
    python3 tools/docstat.py --outline FILE   # fence-aware heading map of one file
    python3 tools/docstat.py --sweep          # names in docs that do not resolve
    python3 tools/docstat.py --all

Exit code is 1 if --sweep finds anything unresolved, so it can gate a commit.
"""

from __future__ import annotations

import argparse
import glob
import os
import re
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # .../eval
ROOT = os.path.dirname(REPO)
VENDORED = ("PackageCache", "node_modules", "/target/", "/.godot/", "/Library/")


def is_vendored(p: str) -> bool:
    return any(v in p for v in VENDORED)


def project_docs() -> list[str]:
    out = []
    for p in glob.glob(os.path.join(ROOT, "**", "*.md"), recursive=True):
        if is_vendored(p) or f"{os.sep}runs{os.sep}" in p:
            continue
        out.append(p)
    return sorted(out)


def headings(path: str) -> list[tuple[int, str, int]]:
    """Fence-aware. Returns (line_no, heading, section_chars).

    A ``` line toggles fence state. Without this, any code comment starting with # is
    read as a heading — the exact defect this module exists to prevent.
    """
    lines = open(path, encoding="utf-8", errors="replace").read().split("\n")
    fence = False
    hits: list[tuple[int, str]] = []
    for i, l in enumerate(lines):
        if l.lstrip().startswith("```"):
            fence = not fence
            continue
        if not fence and re.match(r"^#{1,6} ", l):
            hits.append((i, l))
    out = []
    for k, (i, l) in enumerate(hits):
        end = hits[k + 1][0] if k + 1 < len(hits) else len(lines)
        out.append((i + 1, l, sum(len(x) + 1 for x in lines[i:end])))
    return out


def cmd_sizes() -> int:
    docs = project_docs()
    rows = []
    for p in docs:
        n = len(open(p, encoding="utf-8", errors="replace").read())
        rows.append((os.path.relpath(p, ROOT), n))
    rows.sort(key=lambda r: -r[1])
    total = sum(n for _, n in rows)
    print(f"{'file':<48}{'chars':>9}{'~tokens':>9}")
    for f, n in rows[:20]:
        print(f"{f:<48}{n:>9,}{n // 4:>9,}")
    if len(rows) > 20:
        print(f"... {len(rows) - 20} more")
    print(f"\n{len(rows)} project docs  {total:,} chars  ~{total // 4:,} tokens")

    skills = sorted(glob.glob(os.path.join(ROOT, ".claude/skills/*/SKILL.md")))
    if skills:
        s = sum(len(open(p).read()) for p in skills)
        print(f"{len(skills)} skills  ~{s // 4:,} tokens if all loaded "
              f"(a loaded skill stays in context across turns)")
    return 0


def cmd_outline(path: str) -> int:
    hs = headings(path)
    print(f"{len(hs)} headings in {os.path.relpath(path, ROOT)}\n")
    for line, h, size in hs:
        depth = len(h) - len(h.lstrip("#"))
        print(f"{size:>7,}  L{line:<5} {'  ' * (depth - 1)}{h[:84]}")
    return 0


def _argparse_flags() -> set[str]:
    flags = set()
    for p in glob.glob(os.path.join(REPO, "**", "*.py"), recursive=True):
        if is_vendored(p):
            continue
        for m in re.finditer(r'add_argument\(\s*"(--[a-z0-9-]+)"', open(p, errors="replace").read()):
            flags.add(m.group(1))
    return flags


def _aspect_ids() -> set[str]:
    p = os.path.join(REPO, "judge", "aspects.py")
    if not os.path.exists(p):
        return set()
    s = open(p, errors="replace").read()
    m = re.search(r"ASPECTS\s*=\s*\{[^}]*\(([^)]*)\)", s, re.S)
    if not m:
        return set()
    return {t.strip().lower() for t in m.group(1).split(",") if t.strip()}


def _criterion_ids() -> set[str]:
    ids = set()
    for p in glob.glob(os.path.join(REPO, "judge", "*.py")):
        for m in re.finditer(r'["\']([a-z]+\.[a-z_]+)["\']', open(p, errors="replace").read()):
            ids.add(m.group(1))
    return ids


def _project_root_for(doc: str) -> list[str]:
    """Roots a relative path in a doc could legitimately be written against.

    A doc inside template-godot/ writes `tools/check.gd` relative to that template's
    root, not to the repo root and not to the doc's own directory. Without this, every
    stack's own docs report dozens of phantom paths.
    """
    roots, d = [], os.path.dirname(os.path.abspath(doc))
    while d and d.startswith(ROOT):
        roots.append(d)
        if any(os.path.exists(os.path.join(d, m)) for m in
               ("Cargo.toml", "package.json", "project.godot", "justfile", "Assets")):
            break
        d = os.path.dirname(d)
    return roots + [ROOT, REPO]


# Flags belonging to tools that are not ours. A doc naming `--permission-mode` is
# describing the claude CLI, not a missing argparse entry. Checking these produced 40
# false positives on the first run of this sweep — a checker nobody trusts is a checker
# nobody runs.
FOREIGN_FLAG_PREFIXES = (
    "--max-turns", "--max-budget", "--permission-mode", "--setting-sources",
    "--strict-mcp", "--exclude-dynamic", "--append-system-prompt", "--system-prompt",
    "--json-schema", "--include-partial", "--fallback-model", "--no-session",
    "--forward-subagent", "--bare", "--tools", "--headless", "--help", "--version",
    "--quiet", "--strict", "--no-header", "--check-only", "--experimental-",
    "--write-movie", "--update-snapshots", "--keep-going", "--no-patch", "--no-verify",
    "--file", "--re", "--flags",
)


def cmd_sweep() -> int:
    """Names in docs that do not resolve.

    Deliberately CONSERVATIVE. Every category here has produced a real defect, but a
    false positive costs more than a false negative: it trains the reader to skip the
    output, and then the real hit is invisible. When unsure, say nothing.
    """
    docs = project_docs()
    flags, aspects = _argparse_flags(), _aspect_ids()
    problems: list[str] = []

    for p in docs:
        rel = os.path.relpath(p, ROOT)
        text = open(p, encoding="utf-8", errors="replace").read()

        # Only flags this repo's own harnesses would own.
        for tok in set(re.findall(r"`(--[a-z0-9-]{2,})`", text)):
            if tok.startswith(FOREIGN_FLAG_PREFIXES) or tok in flags:
                continue
            if not re.search(r"(wholegame|runner|judge/|evaluate|regrade)\.py", text):
                continue  # doc never mentions our harness; the flag is someone else's
            problems.append(f"{rel}: flag {tok} matches no argparse in eval/")

        # NO PATH CHECK. Docs legitimately write paths relative to a context stated in
        # prose or a table cell -- README names `tools/boundary.gd` in a row about
        # template-godot/, where it does exist. Measured: 0 true positives, 2 false.
        # A check that cannot be made reliable is removed, not tuned until it is quiet;
        # tuning until quiet is how a check comes to pass vacuously.

        # Aspect ids named as if they exist. The exemption is checked on the LINE, not
        # the document: a file-wide search for "candidate"/"not built" let one legitimate
        # disclaimer silence every check in the file, and the planted-phantom control
        # went green. Document-scope exemptions make a check vacuous.
        # findings/ is an archive: naming a superseded aspect is its subject matter.
        if aspects and "findings/" not in rel:
            for ln in text.split("\n"):
                if re.search(r"(no `\w+` judge|not built|candidate|does not exist|retired|"
                             r"superseded|do not name them)", ln, re.I):
                    continue
                for tok in set(re.findall(r"`(feel|tuning|design|polish|gameplay)`", ln)):
                    problems.append(
                        f"{rel}: `{tok}` reads as an aspect id; ASPECTS = {sorted(aspects)}")

    # A trial id is NOT a key. `g2_tetris3d__unity__t1` names 420x640 frames in
    # wg-matrix-2026-08-13 and 640x400 frames in wg-audio48-2026-08-14 - and in those two
    # runs it is not even the same work: different prompt, 266 files against 442,
    # `Assets/Sim/Sim.cs` differing (#70). Citing an id without its run is the same defect
    # as citing "IMPROVEMENTS iteration 1b" when two files share the name, which this
    # project already fixed by requiring paths.
    #
    # A RATCHET, not an allowlist. The count may fall and must never rise, so the 20
    # legacy cases do not block the sweep while a NEW bare id fails it immediately. An
    # allowlist of specific ids would be a channel a bug can widen (rule 7); a number that
    # can only decrease is not. Resolve one whenever you touch its finding, and lower this.
    # Set to the EXACT current count, never rounded up. At 20 against an actual 18 the
    # ratchet had two units of slack, and a planted bare id passed the sweep - a guard
    # with headroom is not a guard. Lower this every time one is resolved.
    LEGACY_BARE_IDS = 18
    idrx = re.compile(r"\b(g[1-4]_[a-z0-9]+__(?:rust|ts|unity|godot)__t[01])\b")
    runrx = re.compile(r"\bwg-[a-z0-9]+\b")
    bare = []
    for p in docs:
        rel = os.path.relpath(p, ROOT)
        if "findings/" not in rel:
            continue
        lines = open(p, encoding="utf-8", errors="replace").read().split("\n")
        sec = 0
        for i, ln in enumerate(lines):
            if ln.startswith("## "):
                sec = i
            for m in idrx.finditer(ln):
                if not runrx.search(" ".join(lines[sec:i + 3])):
                    bare.append(f"{rel}:{i + 1}: `{m.group(1)}` cited with no run in scope")
    if len(bare) > LEGACY_BARE_IDS:
        problems.append(
            f"trial ids cited without a run: {len(bare)}, ratchet allows {LEGACY_BARE_IDS}. "
            f"An id is not unique across runs (#70). Newest: {bare[-1]}")
    elif len(bare) < LEGACY_BARE_IDS:
        print(f"note: bare trial-id citations down to {len(bare)} "
              f"(ratchet {LEGACY_BARE_IDS}) - lower LEGACY_BARE_IDS in docstat.py")

    # A PACK LABEL IS NOT A KEY ACROSS ROUNDS (#70). `build_pack` reshuffles the
    # label->submission mapping every round, so `A` in round 0 and `A` in round 1 are
    # different submissions. Code that reads several rounds and keys by that field averages
    # different submissions together and produces a clean, plausible, wrong table - which
    # is exactly what happened on 2026-08-22, contradicting a correct result.
    #
    # Every stored round carries submissions[].submission, resolved at judging time. That
    # is the only correct join key. This is wrong-by-construction and therefore greppable.
    for py in sorted(glob.glob(os.path.join(REPO, "**", "*.py"), recursive=True)):
        if os.sep + "runs" + os.sep in py:
            continue
        src = open(py, encoding="utf-8", errors="replace").read()
        multi_round = re.search(r'(rep\*|seed\*|__seed|repeats7|rounds\b)', src)
        if not multi_round:
            continue
        for ln in src.split("\n"):
            if not re.search(r"""\[\s*["']label["']\s*\]""", ln):
                continue
            # THE PROPERTY THIS PROTECTS IS THE SCOPE OF THE KEY, not the word `label`.
            # A label is the primary key WITHIN one pack - that is what it is for - and is
            # not a key ACROSS rounds, because every round reshuffles the mapping. So two
            # uses are correct and exempt: resolving a label through a mapping (which is
            # how submissions[].submission is produced in the first place), and reading a
            # single pack's own manifest, where the label is the only identifier there is.
            # Only accumulation across rounds keyed by label is wrong. The regex that
            # defines this very check is skipped too.
            stripped = ln.strip()
            if (stripped.startswith("#") or "mapping" in ln or "manifest" in ln
                    or "re.search" in ln or "re.compile" in ln):
                continue
            problems.append(
                f"{os.path.relpath(py, ROOT)}: `{ln.strip()[:70]}` keys by pack label "
                f"while reading multiple rounds. A label is scoped to ONE round - join "
                f"on submissions[].submission instead (#70).")

    if problems:
        print(f"{len(problems)} unresolved reference(s):\n")
        for x in problems:
            print(f"  {x}")
        print("\nA document naming something that does not exist is confidently wrong,")
        print("and it will be followed. See FINDINGS #38.")
        return 1

    print(f"sweep clean: {len(docs)} docs checked; {len(flags)} of our flags, "
          f"{len(aspects)} aspects known")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--outline", metavar="FILE")
    ap.add_argument("--sweep", action="store_true")
    ap.add_argument("--all", action="store_true")
    a = ap.parse_args()

    if a.outline:
        return cmd_outline(a.outline)
    if a.sweep:
        return cmd_sweep()
    rc = cmd_sizes()
    if a.all:
        print()
        rc = cmd_sweep() or rc
    return rc


if __name__ == "__main__":
    sys.exit(main())
