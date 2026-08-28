#!/usr/bin/env python3
"""Resolve every relative markdown link in the live documents - path AND fragment.

WHY THIS EXISTS. `docstat.py --sweep` deliberately does not check file paths, and that is
stated in `AGENTS.md`: a phantom path (`eval/RUBRIC.md` for `eval/judge/RUBRIC.md`) passed a
green sweep. Turning bare finding numbers into links makes that gap worse, not better - a bare
`(#68)` is honestly useless, while a link is a claim that somewhere specific says something,
and a link to a heading that has since been reworded LOOKS CHECKED and is not. A citation that
still resolves while pointing at a stranger is the failure `AGENTS.md` names for renamed
findings; a fragment that resolves to nothing is the same shape one level down.

WHAT IT CHECKS, and nothing else:

  1. inline links          `[text](path)` and `[text](path#fragment)`
  2. reference definitions `[label]: path#fragment`
  3. shortcut references   `[#NN]` used in prose with no definition anywhere in the file

Relative targets only. `http:`, `https:` and `mailto:` are skipped by design - this repository
is offline-gradeable and a network check would be a different tool with a different failure
mode. Targets inside fenced code blocks are skipped, because those are transcripts of commands
rather than references.

THE FRAGMENT RULE IS GITHUB'S, AND IT IS IMPLEMENTED HERE RATHER THAN ASSUMED. Anchors are
derived from the target file's own ATX headings: strip inline markdown, lowercase, drop every
character that is not alphanumeric / space / hyphen / underscore, then spaces to hyphens, with
`-1`, `-2` ... for repeats in document order.

BOTH DIRECTIONS. `--selftest` plants one link known to be good and one known to be broken, in
each of the three shapes, and asserts the checker separates them. Rule 12's corollary: prove
the extraction on a case whose answer you can state in advance, before believing the census.

Usage:
    python3 eval/tools/linkcheck.py              # the live documents
    python3 eval/tools/linkcheck.py FILE ...     # named files
    python3 eval/tools/linkcheck.py --selftest   # controls, both directions

Exit 0 when every link resolves, 1 otherwise. Read it unpiped.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# The front door and the documents it links into. Not the archive sweep - this is about links
# a reader is invited to click, and the address is an input to the check (#60). `eval/RUNS.md`
# joined the set with the citation-scope decision in `DECISIONS.md` (2026-08-28): the front door
# links into it five times, which is the set's own definition, and its one `[#46]` shortcut had
# already rotted unseen.
LIVE_DOCS = [
    "README.md",
    "AGENTS.md",
    "DECISIONS.md",
    "eval/FINDINGS.md",
    "eval/RUNS.md",
]

_FENCE_RX = re.compile(r"^\s*(```|~~~)")
_INLINE_RX = re.compile(r"(?<!\!)\[(?P<text>[^\]\[]*)\]\((?P<target>[^)\s]+)\)")
_REFDEF_RX = re.compile(r"^\[(?P<label>[^\]]+)\]:\s*(?P<target>\S+)\s*$")
_SHORTCUT_RX = re.compile(r"(?<!\!)\[(?P<label>#\d{2,3})\](?![(:])")
_HEADING_RX = re.compile(r"^(?P<hashes>#{1,6})\s+(?P<text>.*?)\s*$")
_SKIP_SCHEME_RX = re.compile(r"^(https?|mailto|ftp):", re.I)
_CODESPAN_RX = re.compile(r"`+[^`]*`+")


def _mask_codespans(line: str) -> str:
    """Blank out inline code spans. `[#68]` inside backticks is an EXAMPLE, not a link.

    Without this the checker fires on a document explaining the link convention - which is
    exactly what happened to `DECISIONS.md` the first time this ran, and it is the fail-open
    direction that matters: a gate firing where nothing is wrong spends the attention a real
    firing needs. Length is preserved so line numbers and offsets stay honest.
    """
    return _CODESPAN_RX.sub(lambda m: " " * len(m.group(0)), line)


def github_anchor(heading_text: str) -> str:
    """GitHub's heading-to-fragment rule, implemented rather than assumed."""
    t = heading_text
    t = re.sub(r"`([^`]*)`", r"\1", t)          # code spans
    t = re.sub(r"\*\*([^*]*)\*\*", r"\1", t)    # bold
    t = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"\1", t)  # italics
    t = re.sub(r"_([^_]+)_", r"\1", t)
    t = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", t)     # links keep their text
    t = t.lower()
    t = "".join(c for c in t if c.isalnum() or c in " -_")
    return t.replace(" ", "-")


def anchors_of(path: Path) -> set[str]:
    """Every fragment `path` offers, with GitHub's duplicate suffixes."""
    seen: dict[str, int] = {}
    out: set[str] = set()
    in_fence = False
    for line in path.read_text(errors="replace").splitlines():
        if _FENCE_RX.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        m = _HEADING_RX.match(line)
        if not m:
            continue
        base = github_anchor(m.group("text"))
        n = seen.get(base, 0)
        seen[base] = n + 1
        out.add(base if n == 0 else f"{base}-{n}")
    return out


def _targets(path: Path) -> tuple[list[tuple[int, str, str]], set[str], list[tuple[int, str]]]:
    """(line, kind, target) for every link, the set of defined ref labels, and shortcut uses."""
    found: list[tuple[int, str, str]] = []
    labels: set[str] = set()
    shortcuts: list[tuple[int, str]] = []
    in_fence = False
    for i, line in enumerate(path.read_text(errors="replace").splitlines(), 1):
        if _FENCE_RX.match(line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        m = _REFDEF_RX.match(line)
        if m:
            labels.add(m.group("label").strip().lower())
            found.append((i, "refdef", m.group("target")))
            continue
        line = _mask_codespans(line)
        for im in _INLINE_RX.finditer(line):
            found.append((i, "inline", im.group("target")))
        for sm in _SHORTCUT_RX.finditer(line):
            shortcuts.append((i, sm.group("label")))
    return found, labels, shortcuts


def _rel(p: Path, root: Path) -> str:
    """Display path, tolerant of a root that is not an ancestor (temp dirs, symlinks)."""
    try:
        return str(p.relative_to(root))
    except ValueError:
        return str(p)


def check_file(path: Path, root: Path) -> list[str]:
    problems: list[str] = []
    found, labels, shortcuts = _targets(path)
    rel = _rel(path, root)
    for line, kind, target in found:
        if _SKIP_SCHEME_RX.match(target) or target.startswith("<"):
            continue
        target = target.split(" ", 1)[0].strip("<>")
        frag = ""
        if "#" in target:
            target, frag = target.split("#", 1)
        dest = path.parent if target else path.parent
        resolved = (dest / target).resolve() if target else path
        if not resolved.exists():
            problems.append(f"{rel}:{line}: {kind} target does not exist: {target!r}")
            continue
        if frag and resolved.suffix == ".md":
            if frag not in anchors_of(resolved):
                problems.append(
                    f"{rel}:{line}: {kind} fragment does not name a heading in "
                    f"{_rel(resolved, root)}: #{frag}")
    for line, label in shortcuts:
        if label.lower() not in labels:
            problems.append(
                f"{rel}:{line}: shortcut reference {label} has no definition in this file "
                f"- it renders as literal text")
    return problems


def _selftest() -> int:
    import tempfile

    ok = True
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        (root / "sub").mkdir()
        (root / "sub" / "target.md").write_text(
            "# Heading One\n\n## 128. Tier 2 saturates - four criteria passed 8 of 8\n")
        cases = [
            # (name, body, expect_problem_substring or None)
            ("inline path GOOD", "see [t](sub/target.md)\n", None),
            ("inline path BAD", "see [t](sub/absent.md)\n", "does not exist"),
            ("inline frag GOOD",
             "see [t](sub/target.md#128-tier-2-saturates---four-criteria-passed-8-of-8)\n", None),
            ("inline frag BAD", "see [t](sub/target.md#128-tier-2-saturates)\n",
             "does not name a heading"),
            ("refdef GOOD", "x [#128]\n\n[#128]: sub/target.md#heading-one\n", None),
            ("refdef BAD", "x [#128]\n\n[#128]: sub/target.md#heading-nine\n",
             "does not name a heading"),
            ("shortcut GOOD", "x [#128]\n\n[#128]: sub/target.md\n", None),
            ("shortcut BAD", "x [#129] and nothing defines it\n", "no definition"),
            # a document EXPLAINING the convention must not trip it, and the same page's
            # real links must still be found - variant, not mutant (rule 15)
            ("codespan example ignored", "write `[#129]` and `[t](sub/absent.md)` in prose\n",
             None),
            ("codespan does not blind it",
             "`[#129]` is an example, [t](sub/absent.md) is not\n", "does not exist"),
        ]
        for name, body, expect in cases:
            f = root / "doc.md"
            f.write_text(body)
            problems = check_file(f, root)
            if expect is None:
                good = not problems
            else:
                good = any(expect in p for p in problems)
            ok &= good
            print(f"  {'ok  ' if good else 'FAIL'}  {name:18}  "
                  f"{problems[0] if problems else '(clean)'}")
    # the anchor rule itself, against a heading whose answer is stated in advance
    a = github_anchor("128. Tier 2 saturates because the task is finished — four harder criteria")
    want = "128-tier-2-saturates-because-the-task-is-finished--four-harder-criteria"
    print(f"  {'ok  ' if a == want else 'FAIL'}  anchor rule        {a}")
    ok &= (a == want)
    print("selftest:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="*")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return _selftest()
    paths = [Path(f).resolve() for f in args.files] or [ROOT / d for d in LIVE_DOCS]
    problems: list[str] = []
    for p in paths:
        if not p.exists():
            problems.append(f"{p}: not found")
            continue
        problems += check_file(p, ROOT)
    for p in problems:
        print(p)
    n = sum(1 for p in paths if p.exists())
    print(f"\n{len(problems)} unresolved link(s) across {n} file(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
