#!/usr/bin/env python3
"""Cleanup candidates: text and code that may no longer earn its space.

WHAT THIS IS FOR
----------------
`docstat.py sweep` asks whether a name in a doc RESOLVES -- does this flag exist, does this
aspect id exist. This asks a different question: **does this text still earn the tokens it
costs?** Stale prose, history nobody needs, the same paragraph in two files, a function
nothing calls, a doc section so long nobody finishes it.

`AGENTS.md` already states the principle:

    Prune. Every rule that does not earn its place makes the ones that do harder to find.
    A document nobody finishes reading protects nothing. When a rule is superseded,
    replace it -- do not annotate it.

This is the instrument for that. It **reports candidates and decides nothing.** Every
category below is a question for a reader, never a verdict, because the difference between
dead weight and load-bearing evidence is not mechanically decidable here -- and getting it
wrong destroys the record.

WHAT MUST NEVER BE PRUNED, AND WHY THE SCANNER SKIPS IT
-------------------------------------------------------
`eval/findings/` and `eval/FINDINGS.md` are an ARCHIVE. Words like "superseded",
"retracted" and "no longer" are their SUBJECT MATTER, not staleness. `AGENTS.md`:

    eval/FINDINGS.md is the exception: it is a findings log, and a number that was
    published and later proven wrong stays marked there, because someone may have acted
    on it.

`eval/RUNS.md` records regime boundaries -- which runs may be compared with which. A
boundary that looks like obsolete history is exactly what makes an old number safe to read.

So both are excluded from the staleness categories by default. A cleanup pass that
"tidied" them would delete the only reason anyone can trust the rest. Pass `--include-archive`
to look anyway, and read the result as a question, not a to-do list.

    python3 eval/tools/prune_scan.py              # all categories, top candidates
    python3 eval/tools/prune_scan.py --only dup   # one category
    python3 eval/tools/prune_scan.py --json
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# The archive. Staleness language here is the subject matter, not a defect.
ARCHIVE = ("eval/findings/", "eval/FINDINGS.md", "eval/RUNS.md")

# Prose that describes a former state. Outside the archive, each is a question:
# does a future run need to know this, or is it a rule that should have been REPLACED
# rather than annotated?
#
# STRONG markers describe a former state of THIS SYSTEM: something was one way and is now
# another. That is the thing worth pruning, because a future run needs what IS true.
#
# WEAK markers -- "no longer", "legacy" -- fire mostly inside RULE PROSE, where they are
# load-bearing rather than stale. Measured 2026-08-23: "no longer" was 20 of 49 hits and
# nearly all were rules explaining why something matters, e.g. AGENTS.md's "a file that
# names a flag that no longer exists is worse than one that says nothing". Pruning that
# sentence would delete a rule, not a fossil.
#
# So weak markers are COUNTED and not listed. A category whose output is mostly wrong
# trains the reader to skip it, and then the real hit is invisible -- the failure docstat
# already records for its own path check.
HISTORY_STRONG = re.compile(
    r"\b(used to|previously|formerly|originally|in the past|"
    r"has been renamed|was renamed|deprecated|obsolete|"
    r"old (?:behaviour|behavior|version|way)|before the (?:fix|change|migration))\b",
    re.I,
)
HISTORY_WEAK = re.compile(r"\b(no longer|legacy)\b", re.I)

# The .agents/skills mirror duplicates every skill and is ALREADY FILED as task 27.
# Reporting it 51 more times every six hours is how a scanner gets ignored.
MIRROR = ".agents/"

# Reference implementations the harness executes by discovering their names, the way
# pytest does. "Nothing calls this by name" is what they are FOR, so the dead-code
# question does not apply to them.
DYNAMIC_ENTRYPOINTS = "fixtures/"


def _tracked(suffixes: tuple[str, ...]) -> list[Path]:
    out = subprocess.run(["git", "-C", str(ROOT), "ls-files", "-z"],
                         capture_output=True, text=True, check=True)
    return [ROOT / p for p in out.stdout.split("\0")
            if p and p.endswith(suffixes) and ".claude/worktrees/" not in p]


def _is_archive(rel: str) -> bool:
    return any(rel.startswith(a) or rel == a for a in ARCHIVE)


def _rel(p: Path) -> str:
    return str(p.relative_to(ROOT))


# ---------------------------------------------------------------- categories

def cat_history(include_archive: bool) -> list[dict]:
    """Prose describing how things used to be.

    A future run needs to know what IS true. It needs history only where the history
    explains why a rule exists -- otherwise the rule should have replaced its predecessor
    instead of accumulating next to it.
    """
    hits, weak = [], 0
    for p in _tracked((".md",)):
        rel = _rel(p)
        if MIRROR in rel or (not include_archive and _is_archive(rel)):
            continue
        for i, ln in enumerate(p.read_text(encoding="utf-8", errors="replace").split("\n"), 1):
            if ln.lstrip().startswith(("|", ">")):
                continue
            m = HISTORY_STRONG.search(ln)
            if m:
                hits.append({"file": rel, "line": i, "marker": m.group(0),
                             "text": ln.strip()[:130]})
            elif HISTORY_WEAK.search(ln):
                weak += 1
    if weak:
        hits.append({"file": "(weak markers)", "line": 0, "marker": "no longer/legacy",
                     "text": f"{weak} lines matched weak markers, not listed — mostly rule "
                             f"prose where the phrase is load-bearing"})
    return hits


def cat_dup(include_archive: bool) -> list[dict]:
    """The same substantial paragraph in more than one file.

    Two files named IMPROVEMENTS.md, cited by name alone, is already a recorded defect in
    this project. Duplicated PROSE is the same failure one level down: two copies drift,
    and the reader who finds the stale one has no way to know.

    GROUPED BY FILE SET, not per paragraph. Ungrouped, one pair of mirrored documents
    produced 21 identical lines of output and buried everything else. What a reader needs
    is "these two files share 21 paragraphs", once.
    """
    seen: dict[str, list[str]] = defaultdict(list)
    for p in _tracked((".md",)):
        rel = _rel(p)
        if MIRROR in rel or (not include_archive and _is_archive(rel)):
            continue
        for para in re.split(r"\n\s*\n", p.read_text(encoding="utf-8", errors="replace")):
            norm = re.sub(r"\s+", " ", para).strip()
            if len(norm) < 240:
                continue
            seen[hashlib.sha1(norm.encode()).hexdigest()].append(rel)

    pairs: dict[tuple[str, ...], int] = defaultdict(int)
    for files in seen.values():
        uniq = tuple(sorted(set(files)))
        if len(uniq) > 1:
            pairs[uniq] += 1
    return sorted(({"files": list(k), "shared_paragraphs": v} for k, v in pairs.items()),
                  key=lambda d: -d["shared_paragraphs"])


def cat_fat(include_archive: bool) -> list[dict]:
    """Document SECTIONS large enough that nobody finishes them.

    File size is the wrong unit -- a big file of short sections is fine. What defeats a
    reader is one section that will not end. These are the summarisation candidates.
    """
    out = []
    for p in _tracked((".md",)):
        rel = _rel(p)
        lines = p.read_text(encoding="utf-8", errors="replace").split("\n")
        cur, start, fence = "(preamble)", 0, False
        def flush(end: int) -> None:
            chars = sum(len(x) + 1 for x in lines[start:end])
            if chars > 6000:
                out.append({"file": rel, "line": start + 1, "heading": cur[:90],
                            "chars": chars, "tokens": chars // 4})
        for i, ln in enumerate(lines):
            if ln.startswith("```"):
                fence = not fence
            if not fence and re.match(r"^#{1,3} ", ln):
                flush(i)
                cur, start = ln.strip(), i
        flush(len(lines))
    return sorted(out, key=lambda d: -d["chars"])


def cat_deadcode() -> list[dict]:
    """Top-level functions whose name appears nowhere else in the repository.

    Deliberately crude and deliberately conservative: a name used only where it is defined
    is a candidate, not a corpse. Dynamic dispatch, argparse wiring and string lookups all
    defeat it, which is why this reports rather than deletes.
    """
    py = _tracked((".py",))
    corpus = "\n".join(p.read_text(encoding="utf-8", errors="replace")
                       for p in py + _tracked((".md",)))
    out = []
    for p in py:
        rel = _rel(p)
        if DYNAMIC_ENTRYPOINTS in rel:
            continue  # discovered by name; being uncalled is the point
        try:
            tree = ast.parse(p.read_text(encoding="utf-8", errors="replace"))
        except SyntaxError:
            continue
        for node in tree.body:
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            name = node.name
            if name.startswith(("_", "test_", "cmd_", "main")):
                continue
            if len(re.findall(rf"\b{re.escape(name)}\b", corpus)) <= 1:
                out.append({"file": rel, "line": node.lineno, "name": name})
    return out


def cat_longfn() -> list[dict]:
    """Functions long enough to be worth splitting. A refactor prompt, not a defect."""
    out = []
    for p in _tracked((".py",)):
        rel = _rel(p)
        try:
            tree = ast.parse(p.read_text(encoding="utf-8", errors="replace"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                span = (node.end_lineno or node.lineno) - node.lineno
                if span > 90:
                    out.append({"file": rel, "line": node.lineno,
                                "name": node.name, "lines": span})
    return sorted(out, key=lambda d: -d["lines"])


def cat_todo() -> list[dict]:
    out = []
    for p in _tracked((".py", ".md", ".just", ".ts", ".rs", ".cs", ".gd")):
        rel = _rel(p)
        for i, ln in enumerate(p.read_text(encoding="utf-8", errors="replace").split("\n"), 1):
            if re.search(r"\b(TODO|FIXME|XXX|HACK)\b", ln):
                out.append({"file": rel, "line": i, "text": ln.strip()[:130]})
    return out


CATEGORIES = {
    "history": ("prose describing a former state (replace, do not annotate)", cat_history),
    "dup":     ("the same paragraph in more than one file (they will drift)", cat_dup),
    "fat":     ("sections too long to finish (summarisation candidates)", cat_fat),
    "dead":    ("functions referenced nowhere else (candidates, not corpses)", cat_deadcode),
    "longfn":  ("functions worth splitting", cat_longfn),
    "todo":    ("TODO/FIXME/HACK markers", cat_todo),
}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", choices=sorted(CATEGORIES))
    ap.add_argument("--include-archive", action="store_true",
                    help="also scan eval/findings, FINDINGS.md and RUNS.md, where "
                         "staleness language is the subject matter")
    ap.add_argument("--top", type=int, default=8)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    results: dict[str, list] = {}
    for key, (_desc, fn) in CATEGORIES.items():
        if a.only and key != a.only:
            continue
        results[key] = (fn(a.include_archive)
                        if fn in (cat_history, cat_dup, cat_fat) else fn())

    if a.json:
        print(json.dumps(results, indent=2))
        return 0

    total_tokens = sum(d["tokens"] for d in results.get("fat", []))
    print("CLEANUP CANDIDATES — questions, not verdicts. Nothing here is known to be dead.")
    if not a.include_archive:
        print("eval/findings, FINDINGS.md and RUNS.md excluded: staleness language there is")
        print("the subject matter. --include-archive to look anyway.\n")
    for key, items in results.items():
        desc = CATEGORIES[key][0]
        print(f"── {key}  ({len(items)})  {desc}")
        for d in items[:a.top]:
            if key == "dup":
                print(f"     {d['shared_paragraphs']:>3} shared  "
                      f"{'  <->  '.join(d['files'])}")
            elif key == "fat":
                print(f"     ~{d['tokens']:>5,} tok  {d['file']}:{d['line']}  {d['heading']}")
            elif key in ("dead", "longfn"):
                extra = f"  ({d['lines']} lines)" if key == "longfn" else ""
                print(f"     {d['file']}:{d['line']}  {d['name']}{extra}")
            else:
                print(f"     {d['file']}:{d['line']}  {d.get('text', d.get('marker'))}")
        if len(items) > a.top:
            print(f"     … {len(items) - a.top} more")
        print()
    if total_tokens:
        print(f"long sections cost ~{total_tokens:,} tokens if all loaded.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
