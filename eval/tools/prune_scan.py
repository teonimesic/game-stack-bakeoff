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
import shutil
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

# No MIRROR exemption. It existed to stop this scanner reporting the `.agents/skills`
# duplicate 51 times every six hours while task 27 was open. The duplicate was deleted on
# 2026-08-23 (#99) and `docstat.py --sweep` now fails on any SKILL.md outside
# `.claude/skills/<name>/`, so the suppression has nothing left to suppress and would only
# hide the next copy from the scanner that found this one.

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
        if not include_archive and _is_archive(rel):
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
        if not include_archive and _is_archive(rel):
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

    THE ARCHIVE EXCLUSION WAS A BANNER, NOT A BEHAVIOUR. This function took
    `include_archive` and never read it, while the command's header printed "eval/findings,
    FINDINGS.md and RUNS.md excluded" above a list whose largest entry was
    `eval/FINDINGS.md`'s own index -- 3,994 tokens, 14% of the reported total, heading a
    list the prune skill forbids touching. A reader trusting the banner would have been
    handed the one file it promised to keep out. Found by task 53 while measuring against
    that very list.

    The exclusion is now performed where it is claimed, and `--include-archive` reaches it.
    """
    out = []
    for p in _tracked((".md",)):
        rel = _rel(p)
        if not include_archive and _is_archive(rel):
            continue
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


def _cyclomatic(node: ast.AST) -> int:
    """Cyclomatic complexity: one path, plus one per branch point.

    Counted here rather than pulled from `radon` so the scanner has no dependency -- the
    definition is small and stable, and a tool the next session cannot run because a
    package is missing is a tool that does not run.

    Boolean operators count `len(values) - 1` because `a and b and c` is two branch points,
    not one. Each `except` handler is a path; `else`/`finally` are not.
    """
    score = 1
    for n in ast.walk(node):
        if isinstance(n, (ast.If, ast.For, ast.AsyncFor, ast.While, ast.ExceptHandler,
                          ast.With, ast.AsyncWith, ast.Assert, ast.IfExp)):
            score += 1
        elif isinstance(n, ast.BoolOp):
            score += len(n.values) - 1
        elif isinstance(n, ast.comprehension):
            score += 1 + len(n.ifs)
    return score


def _churn(days: int = 90) -> dict[str, int]:
    """Commits touching each tracked file in the window. Empty dict if git is unavailable."""
    try:
        out = subprocess.run(
            ["git", "-C", str(ROOT), "log", f"--since={days}.days", "--pretty=format:",
             "--name-only"], capture_output=True, text=True, check=True).stdout
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        return {}
    counts: dict[str, int] = defaultdict(int)
    for line in out.split("\n"):
        line = line.strip()
        if line:
            counts[line] += 1
    return counts


def cat_hotspot() -> list[dict]:
    """CHURN x COMPLEXITY. The refactor signal neither number gives alone.

    Complexity alone flags code that is hard but settled -- rewriting it buys nothing and
    risks a working thing. Churn alone flags code that changes often because the work is
    there, which is not a defect. The product is the classic hotspot: complicated code that
    people keep having to touch, where the difficulty is being paid for repeatedly.

    Reported per FILE, since churn is only recorded per file. `longfn` and `complexity`
    stay separate because they point at a specific function; this points at a file to read.

    A hotspot is a QUESTION. High churn on a file under active development is expected and
    means nothing on its own.
    """
    churn = _churn()
    if not churn:
        return []
    out = []
    for p in _tracked((".py",)):
        rel = _rel(p)
        c = churn.get(rel, 0)
        if not c:
            continue
        try:
            tree = ast.parse(p.read_text(encoding="utf-8", errors="replace"))
        except SyntaxError:
            continue
        cx = sum(_cyclomatic(n) for n in ast.walk(tree)
                 if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)))
        if cx and c > 1:
            out.append({"file": rel, "commits": c, "complexity": cx, "score": c * cx})
    return sorted(out, key=lambda d: -d["score"])


def cat_complexity() -> list[dict]:
    """Individual functions with high cyclomatic complexity.

    >20 is the conventional "hard to test" threshold. It is a prompt to look, not a defect:
    a dispatch table of 30 branches is simple to read and scores badly.
    """
    out = []
    for p in _tracked((".py",)):
        rel = _rel(p)
        try:
            tree = ast.parse(p.read_text(encoding="utf-8", errors="replace"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                cx = _cyclomatic(node)
                if cx > 20:
                    out.append({"file": rel, "line": node.lineno,
                                "name": node.name, "complexity": cx})
    return sorted(out, key=lambda d: -d["complexity"])


#: THE PINNED RULE SET, and the single place it is spelled. `eval/tools/lint.py` imports
#: these four names rather than restating them: a selection written in two files is a
#: selection that will disagree with itself, and the disagreement would look like the
#: codebase moving (AGENTS.md rule 12 -- the address is an input to the check).
#:
#: RULES ARE PINNED, and to CORRECTNESS rather than style. Two reasons.
#:
#: Determinism: with no `--select`, the set of rules is whatever the installed ruff
#: defaults to, so the number moves when the tool updates and the movement looks like
#: work. A measurement whose definition drifts is the `project_lines` failure again.
#:
#: Relevance: the default run reported 491 issues here, 132 of them percent-formatting.
#: Mass-fixing those is churn -- tokens and review attention spent moving text -- and it
#: would bury the handful that matter. The selected rules map onto failures this project
#: has actually recorded:
#:
#:     F, E9      real bugs: undefined names, unused variables
#:     PLW1510    `subprocess.run` without `check=` -- an ignored exit status, which is
#:                rule 3 in `AGENTS.md` and has cost this project real measurements
#:     BLE001     blind `except Exception` -- the fail-open shape (#31)
#:     S110,S112  `try/except/pass` and `/continue` -- a swallowed failure that leaves a
#:                plausible in-range value behind
#:     B          bugbear: mutable defaults, loop-variable capture in closures
LINT_SELECT = "F,E9,B,BLE001,PLW1510,S110,S112"

#: Scoped to the HARNESS. Everything excluded below is an object of measurement rather
#: than an instrument, and linting the object of measurement is measuring the thing being
#: measured.
LINT_ROOT = ROOT / "eval"
LINT_EXCLUDE = (
    # Stored results. Data, including per-trial copies of the starters.
    ROOT / "eval/runs",
    # Stand-in SUBMISSIONS, the same class of artifact as `eval/starters/*/`: reference
    # implementations the graders are validated against, one of which (`broken/`) is
    # DELIBERATELY defective. Editing one invalidates the control it is, and a lint
    # finding against a fixture is a finding about the thing being graded. They were in
    # scope until 2026-08-23 and contributed 14 of the 30 BLE001 and 3 of the 11 B905,
    # every one of them the two idioms a fixture needs: a test runner catching whatever a
    # test raises, and an import fallback for the judge's PNG writer.
    ROOT / "eval/judge/fixtures",
)


def ruff_exe() -> str | None:
    return shutil.which("ruff") or shutil.which(str(Path.home() / ".local/bin/ruff"))


def run_ruff(fmt: str = "json") -> tuple[int, str, str]:
    """(returncode, stdout, stderr) for the pinned set. Raises OSError if ruff is gone.

    The ADDRESS is checked before the command is: ruff exits **0** with `[]` on a path
    that does not exist, printing only a warning to stderr, so a wrong root here would
    report a clean codebase forever -- #60's shape, in the instrument that is supposed to
    find that shape (AGENTS.md rule 12).
    """
    exe = ruff_exe()
    if exe is None:
        raise OSError("ruff is not installed")
    if not LINT_ROOT.is_dir():
        raise OSError(f"lint root does not exist: {LINT_ROOT} — ruff would exit 0 on it")
    argv = [exe, "check", str(LINT_ROOT)]
    for ex in LINT_EXCLUDE:
        argv += ["--exclude", str(ex)]
    argv += ["--select", LINT_SELECT, "--output-format", fmt]
    # check=False: ruff exits **1** when it finds violations, which is the normal and
    # expected result. `check=True` would raise on every non-clean run. The status that
    # actually matters is 2 -- ruff refused to run -- and it is handled explicitly below
    # rather than left to a CalledProcessError nobody catches.
    r = subprocess.run(argv, capture_output=True, text=True, check=False)
    return r.returncode, r.stdout, r.stderr


def cat_lint() -> list[dict]:
    """ruff over the harness, grouped by rule. Reports its own failure, never silence.

    A linter that did not run must not read as a clean bill of health -- that is the
    `-disable-audio` failure (#61), where a flag accepted and ignored was indistinguishable
    from a working guard. Until 2026-08-23 that was controlled for only ONE way ruff can
    fail to run (not installed). Two others returned an empty list, i.e. green:

      * **exit 2** -- ruff refused the invocation (a removed or unknown rule selector).
        stdout is empty, `json.loads(r.stdout or "[]")` yields `[]`, and the category
        prints `lint (0)`. MEASURED: `--select E999` gives rc=2, stdout `''`.
      * **a wrong root** -- ruff exits **0** with `[]` and only a stderr warning.
        MEASURED: `ruff check /no/such/dir` gives rc=0, stdout `'[]'`.

    Both are handled in `run_ruff`, which is also what `lint.py` calls, so the two
    entry points cannot disagree about what was scanned.
    """
    try:
        rc, stdout, stderr = run_ruff()
    except OSError as e:
        hint = ("uv tool install ruff — absence is not a clean result"
                if ruff_exe() is None else
                "the lint ROOT is wrong, not the tool — fix LINT_ROOT")
        return [{"rule": f"(ruff did not run: {e})", "count": 0, "hint": hint}]
    if rc not in (0, 1):
        return [{"rule": f"(ruff refused the invocation, exit {rc})", "count": 0,
                 "hint": (stderr.strip().replace("\n", " ")[:120]
                          or "no stderr — investigate, this is NOT a clean result")}]
    try:
        items = json.loads(stdout or "[]")
    except json.JSONDecodeError as e:
        return [{"rule": f"(ruff output is not JSON: {e})", "count": 0,
                 "hint": "investigate — this is NOT a clean result"}]
    by_rule: dict[str, int] = defaultdict(int)
    for it in items:
        by_rule[f"{it.get('code')} {it.get('message', '')[:58]}"] += 1
    return sorted(({"rule": k, "count": v} for k, v in by_rule.items()),
                  key=lambda d: -d["count"])


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
    "hotspot": ("churn x complexity — the refactor signal neither gives alone", cat_hotspot),
    "complexity": ("functions above the conventional hard-to-test threshold", cat_complexity),
    "lint":    ("ruff on the harness (NOT the templates — those are the product)", cat_lint),
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
            elif key == "hotspot":
                print(f"     score {d['score']:>5}  {d['commits']:>3} commits x cx "
                      f"{d['complexity']:<4}  {d['file']}")
            elif key == "lint":
                print(f"     {d['count']:>4}  {d['rule']}"
                      + (f"   [{d['hint']}]" if d.get("hint") else ""))
            elif key == "complexity":
                print(f"     cx {d['complexity']:>3}  {d['file']}:{d['line']}  {d['name']}")
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
