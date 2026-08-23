#!/usr/bin/env python3
"""Count the INSTRUCTIONS in this project's always-loaded documentation.

Why this exists
---------------
arXiv:2509.21051 (*When Instructions Multiply*) reports that instruction-following
compliance degrades with the NUMBER of simultaneously-active instructions, and that a
logistic regression on count alone predicts compliance to ~10% error. Its benchmarks
top out at 10 (text) and 6 (code) instructions. This project's always-loaded context is
plainly larger than that, and nobody had ever counted it.

`n` is the x-axis of that curve. So the first question is: where does this repository
sit on it?

THE COUNT IS NOT A FACT, IT IS A DEFINITION
-------------------------------------------
"How many instructions are in a document" has no ground truth. Any counter is a
heuristic, and a keyword list is exactly the enumeration failure `AGENTS.md`'s rule
audit warns about -- a trigger written as the instances the author happened to see.

So this tool reports THREE definitions and their range, and never a single number:

  strict    a sentence with a hard deontic marker (must / never / do not / always /
            required / mandatory) -- the instructions a reader could not treat as advice
  broad     strict, plus soft normatives (should / prefer / avoid / do not need to) and
            bare-imperative sentences
  blocks    normative *units* rather than sentences: a bullet, a numbered rule, or a
            table row that contains at least one broad-normative sentence, counted once

`strict <= broad` always. `blocks` is not bracketed by either: it merges multi-sentence
rules (pushing it below `broad`) and counts table rows that are not sentences at all.

Report the range. A number produced by one keyword list, quoted alone, is the shape this
repository distrusts.

Usage
-----
    python3 eval/tools/instruction_census.py                  # always-loaded set
    python3 eval/tools/instruction_census.py --all            # every project doc
    python3 eval/tools/instruction_census.py --json
    python3 eval/tools/instruction_census.py --selftest       # controls, both directions
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# The set a session actually pays for on every turn: the root file plus each
# folder-scoped file. `CLAUDE.md` is a one-line `@AGENTS.md` import and is not counted
# separately. `eval/starters/*/AGENTS.md` are NOT here: they are the product, read by a
# building agent inside a trial, never by a session working on the repository.
ALWAYS_LOADED = [
    "AGENTS.md",
    "eval/AGENTS.md",
    "eval/judge/AGENTS.md",
    "research/AGENTS.md",
]

# Markers a reader cannot downgrade to advice.
HARD = r"must|never|do not|don't|always|required|mandatory|may not|cannot be|shall"
# Markers that carry force but leave discretion.
SOFT = r"should|prefer|avoid|ought to|do it yourself|worth doing|needs to"

RE_HARD = re.compile(rf"\b({HARD})\b", re.I)
RE_SOFT = re.compile(rf"\b({SOFT})\b", re.I)

# A bare imperative: sentence opens with an uninflected verb. Deliberately a small,
# named list rather than a POS tagger, and its size is REPORTED as a limitation rather
# than hidden -- see `--selftest`, which pins that it misses verbs not on it.
IMPERATIVE_VERBS = (
    "read|write|run|check|use|add|remove|delete|fix|update|report|record|verify|hold|"
    "partition|cite|count|keep|drop|pin|guard|name|state|ask|launch|stop|invoke|prune|"
    "replace|treat|diff|sweep|measure|quote|give|put|leave|start|make|let|consider|"
    "decide|raise|assert|enumerate|reserve|filter|archive|arm|re-run|rewrite|restate"
)
RE_IMPERATIVE = re.compile(rf"^\s*(?:\*\*)?({IMPERATIVE_VERBS})\b", re.I)

# Lines that are structure, not prose.
RE_HEADING = re.compile(r"^\s{0,3}#{1,6}\s")
RE_TABLE_SEP = re.compile(r"^\s*\|?[\s:|-]+\|[\s:|-]*$")
RE_FENCE = re.compile(r"^\s*```")

# A normative unit: bullet, ordered item, or table row.
RE_BULLET = re.compile(r"^\s*([-*+]|\d+\.)\s+")
RE_TABLEROW = re.compile(r"^\s*\|.*\|\s*$")

SPACE = chr(32)


def strip_code(text: str) -> tuple[str, int]:
    """Drop fenced code blocks. Returns the prose and the number of fenced blocks."""
    out, fenced, n = [], False, 0
    for line in text.splitlines():
        if RE_FENCE.match(line):
            if not fenced:
                n += 1
            fenced = not fenced
            out.append("")
            continue
        out.append("" if fenced else line)
    return "\n".join(out), n


def sentences(block: str) -> list[str]:
    """Split on sentence-final punctuation. Inline code spans are masked first so that
    `judge/bot_mutants.py` and `e.g.` do not create sentence boundaries."""
    masked = re.sub(r"`[^`]*`", lambda m: SPACE * len(m.group(0)), block)
    masked = re.sub(r"\b(e\.g|i\.e|vs|etc|Dr|No)\.", lambda m: m.group(0)[:-1],
                    masked)
    parts, start = [], 0
    for m in re.finditer(r"[.!?](?=\s|$)", masked):
        parts.append(block[start:m.end()])
        start = m.end()
    if block[start:].strip():
        parts.append(block[start:])
    return [p.strip() for p in parts if p.strip()]


def classify(sent: str) -> str:
    """'hard' | 'soft' | 'imperative' | ''"""
    s = re.sub(r"`[^`]*`", " ", sent)
    if RE_HARD.search(s):
        return "hard"
    if RE_SOFT.search(s):
        return "soft"
    if RE_IMPERATIVE.match(s.lstrip("*_> ")):
        return "imperative"
    return ""


def count_doc(text: str) -> dict:
    prose, fenced = strip_code(text)
    lines = prose.splitlines()

    strict = broad = 0
    blocks_hit = 0
    hard_ex: list[str] = []

    # Sentence-level counts, over every non-structural line.
    body = []
    for ln in lines:
        if RE_HEADING.match(ln) or RE_TABLE_SEP.match(ln):
            continue
        body.append(ln)
    for sent in sentences("\n".join(body)):
        kind = classify(sent)
        if kind == "hard":
            strict += 1
            broad += 1
            if len(hard_ex) < 5:
                hard_ex.append(" ".join(sent.split())[:90])
        elif kind in ("soft", "imperative"):
            broad += 1

    # Block-level count: a normative UNIT, counted once however many sentences it has.
    # A unit is a bullet/ordered item (with its lazy continuation), a table row, or a
    # run of plain paragraph lines.
    unit: list[str] = []

    def flush():
        nonlocal blocks_hit
        if unit and any(classify(s) for s in sentences(" ".join(unit))):
            blocks_hit += 1
        unit.clear()

    for ln in lines:
        if RE_HEADING.match(ln) or RE_TABLE_SEP.match(ln):
            flush()
            continue
        if not ln.strip():
            flush()
            continue
        if RE_BULLET.match(ln) or RE_TABLEROW.match(ln):
            flush()
            unit.append(ln)
            continue
        unit.append(ln)
    flush()

    return {
        "lines": len(text.splitlines()),
        "chars": len(text),
        "approx_tokens": round(len(text) / 4),
        "fenced_blocks": fenced,
        "strict": strict,
        "broad": broad,
        "blocks": blocks_hit,
        "hard_examples": hard_ex,
    }


# --------------------------------------------------------------------------- #
# Controls. Rule 1: a counter that can only return a number is not a measurement.
# --------------------------------------------------------------------------- #

POSITIVE = """# Title

You must always run the gate.

Never quote a value you did not read.

- Prefer the vendored source.
- Read the ticket first.

| when | do |
|---|---|
| a run finishes | update `README.md` |
"""

NEGATIVE = """# Title

The harness stores cost in `modelUsage`. Twelve trials finished in August.

The judge opened four files. Its reasoning is stored beside its scores.

```
must never always do not   # inside a fence: not prose, must not count
```
"""


def selftest() -> int:
    """Both directions, per the project's control rule.

    POSITIVE pins that each definition can go UP -- a counter stuck at zero is
    indistinguishable from a document with no instructions in it.
    NEGATIVE pins that each can go DOWN to zero on declarative prose, INCLUDING prose
    whose fenced block is full of the exact marker words. A counter that cannot return
    zero would report every document as instruction-dense and the census would be
    reporting the instrument.
    """
    ok = True
    p, n = count_doc(POSITIVE), count_doc(NEGATIVE)

    checks = [
        ("positive strict >= 2", p["strict"] >= 2, p["strict"]),
        ("positive broad > strict", p["broad"] > p["strict"], (p["broad"], p["strict"])),
        ("positive blocks >= 3", p["blocks"] >= 3, p["blocks"]),
        ("negative strict == 0", n["strict"] == 0, n["strict"]),
        ("negative broad == 0", n["broad"] == 0, n["broad"]),
        ("negative blocks == 0", n["blocks"] == 0, n["blocks"]),
        ("fence was seen", n["fenced_blocks"] == 1, n["fenced_blocks"]),
    ]
    for name, good, got in checks:
        print(f"  {'PASS' if good else 'FAIL'}  {name}   got={got}")
        ok &= good

    # The KNOWN LIMITATION, pinned rather than described. `IMPERATIVE_VERBS` is an
    # enumeration; this asserts it misses a verb that is not on it, so the miss is a
    # recorded property of the tool and not a surprise to the next reader.
    miss = count_doc("Refactor the grader before the sweep.\n")
    lim = miss["broad"] == 0
    print(f"  {'PASS' if lim else 'FAIL'}  known limit: bare imperative not on the "
          f"verb list is MISSED   got broad={miss['broad']}")
    ok &= lim

    print("\nselftest:", "clean" if ok else "FAILED")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--all", action="store_true",
                    help="every tracked project .md outside eval/runs and tasks")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("paths", nargs="*")
    a = ap.parse_args()

    if a.selftest:
        return selftest()

    if a.paths:
        files = [Path(p) for p in a.paths]
    elif a.all:
        files = sorted(p for p in ROOT.rglob("*.md")
                       if "eval/runs" not in p.as_posix()
                       and "/tasks/" not in p.as_posix()
                       and ".claude/worktrees" not in p.as_posix()
                       and "node_modules" not in p.as_posix())
    else:
        files = [ROOT / p for p in ALWAYS_LOADED]

    rows = []
    for f in files:
        if not f.exists():
            print(f"missing: {f}", file=sys.stderr)
            return 2
        r = count_doc(f.read_text(encoding="utf-8"))
        r["path"] = f.relative_to(ROOT).as_posix() if ROOT in f.parents or f.is_relative_to(ROOT) else str(f)
        rows.append(r)

    tot = {k: sum(r[k] for r in rows)
           for k in ("lines", "chars", "approx_tokens", "strict", "broad", "blocks")}

    if a.json:
        print(json.dumps({"rows": rows, "total": tot}, indent=2))
        return 0

    print(f"{'doc':<26} {'lines':>6} {'~tok':>7} {'strict':>7} {'broad':>7} {'blocks':>7}")
    for r in rows:
        print(f"{r['path']:<26} {r['lines']:>6} {r['approx_tokens']:>7} "
              f"{r['strict']:>7} {r['broad']:>7} {r['blocks']:>7}")
    print(f"{'TOTAL':<26} {tot['lines']:>6} {tot['approx_tokens']:>7} "
          f"{tot['strict']:>7} {tot['broad']:>7} {tot['blocks']:>7}")
    print(f"\ninstruction count, always-loaded set: {min(tot['strict'], tot['blocks'])}"
          f"-{max(tot['broad'], tot['blocks'])} depending on definition.")
    print("ManyIFEval tops out at 10; StyleMBPP at 6 (arXiv:2509.21051).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
