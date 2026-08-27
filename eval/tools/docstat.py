#!/usr/bin/env python3
"""Analyse this project's documentation: structure, size, and names that do not exist.

`--sweep` asks three kinds of question. REFERENCES: does a name used in a doc resolve?
STRUCTURE: does a file parse as the thing it is being read as? The second kind was added
2026-08-23 after eleven documentation linters were measured against this repository and
produced over 14,000 alerts and two defects, both structural, both missed by every prose
linter (research/11-doc-linting-for-agents.md).

INTEGRITY: is the text intact, or did an edit leave debris behind? See `_check_orphaned_tail`
and `_check_duplicate_fragment`. This is the kind no consistency check can ask, because debris
states nothing and therefore disagrees with nothing - the reason a stranded half-sentence sat at
line 6 of eval/FINDINGS.md, the file every session is told to read first, through every gate in
this module.

The two integrity checks are NOT one check with a parameter, and the gap between them is
measured in BOTH directions, not assumed. `_check_orphaned_tail` asks whether a whole LINE
recurs in the paragraph above it; `_check_duplicate_fragment` asks whether any 12-word WINDOW
recurs inside one block. Run each against the other's real instance:

    1f6fb65:eval/FINDINGS.md:6   orphaned tail 1 hit   duplicate fragment 0
    75dde71:DECISIONS.md:745     orphaned tail 0 hits  duplicate fragment 4

NEITHER SUBSUMES THE OTHER. The fragment defect's duplicated span begins mid-sentence and ends
mid-sentence, so no line of it recurs whole; the orphan's repeated run is **6 words**, far below
any window this side of the false-positive floor. Merging them into one parameterised rule looks
obvious and would lose an instance, so `_duplicate_fragment_pins` asserts the top-right cell.

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
    python3 tools/docstat.py                    # size + structure of project docs
    python3 tools/docstat.py --outline FILE     # fence-aware heading map of one file
    python3 tools/docstat.py --sweep            # names in docs that do not resolve
    python3 tools/docstat.py --findings         # THE PRODUCER for any count of the log
    python3 tools/docstat.py --findings --json  # ... machine-readable
    python3 tools/docstat.py --count-triggers   # what each candidate count trigger costs
    python3 tools/docstat.py --renumbered       # citations of a finding that was renumbered
    python3 tools/docstat.py --renumbered --at REV   # ... as of any revision
    python3 tools/docstat.py --withdrawn        # live docs restating a retired figure
    python3 tools/docstat.py --withdrawn --at REV    # ... as of any revision
    python3 tools/docstat.py --money            # live docs calling a token valuation money
    python3 tools/docstat.py --money --at REV        # ... as of any revision
    python3 tools/docstat.py --all

A THIRD KIND OF QUESTION, added 2026-08-23. WITHDRAWAL: is a figure or a claim that was
RETIRED still being stated as current? It is neither of the two above, because a retired
figure RESOLVES and every copy of it AGREES - propagation and consistency are the same
observation (#113). The register is `eval/withdrawn.json`, the rule is in
`_check_withdrawal_register`, and its controls are `tools/withdrawn_control.py`.

A FOURTH, added 2026-08-23. QUANTITY: how many findings are there, and does every live
document say so? `README.md` said "Thirty-seven numbered findings" over a log that had
reached #131 — past a range gate that was green, because a range is not a count and
`#19-#131` is equally true of 113 findings and of 40. `--findings` is the producer, it reads
`eval/findings/` and `eval/FINDINGS.md` independently, and `_findings_census_pins` proves it
disagrees when a finding is added, renumbered or duplicated — and still agrees when one is
added correctly.

The count question reads 2 triggers over `_count_corpus()` — the live corpus plus
`RANGE_DOCS`. One is the phrase `N numbered findings`; the other is any cardinal governing a
plural noun on a line that names the findings log by its range, its path or its producer. It
read 1 wording over 3 documents until task 179, which is how `143 entries` stood in
`README.md` beside `docstat.py --findings` against a measured 171. `--count-triggers` is the
producer for what each candidate trigger would cost, and `_stated_counts` holds the reasoning
that chose the scoped one over the obvious quantifier widening.

Exit code is 1 if --sweep finds anything unresolved, so it can gate a commit.
`--renumbered` never gates: it is a smell detector, and its second half is explicitly
undecidable. See `_check_renumbered_citations` for which half is which. `--withdrawn` DOES
gate: its verdict is mechanical - a declared entry either sits in a live block that cites
its id or it does not.

The undecidable half is a STANDING list that never reaches zero, so what a reader needs
from it is not the list but which rows are NEW. `eval/renumber_triage.json` records the
verdict a person reached on a row, keyed by the citing text rather than by a line number;
`_triage_for` prints it beside the row and `_check_triage_register` gates - inside --sweep -
on an entry that no longer matches anything. See `_check_renumbered_citations` for why the
verdict has to be recorded by hand and cannot be re-derived.
"""

from __future__ import annotations

import argparse
import collections
import datetime as _dt
import glob
import json
import os
import re
import subprocess
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # .../eval
ROOT = os.path.dirname(REPO)
VENDORED = ("PackageCache", "node_modules", "/target/", "/.godot/", "/Library/")


def is_vendored(p: str) -> bool:
    return any(v in p for v in VENDORED)


def _tracked_md(root: str | None = None, rev: str | None = None) -> list[str]:
    """Every markdown path IN THE TREE, relative to `root`, `/`-separated.

    ONE spelling of "which files are in this repository". Three checks used to ask that
    question three ways - a filesystem `glob`, `git ls-files`, and `git ls-tree` - and a
    tree with two spellings has two answers (#60). The filesystem is the one that is
    wrong: a file can sit on disk without being in the repository, and then a document
    nobody wrote and nobody can review is an input to a gate.

    RAISES rather than returning empty when git itself fails. An empty corpus is the one
    result indistinguishable from a clean one; every caller here reports "clean over N
    documents", and N=0 would print as a pass. `_git_at` is what makes the two
    distinguishable - a tree that genuinely holds no markdown returns `[]` at exit 0 and
    is the caller's business, while a failed listing stops here.

    `-z`, AND IT IS LOAD-BEARING. `core.quotePath` defaults to true, so a path holding any
    byte outside ASCII comes back C-quoted and wrapped in double quotes -
    `"caf\\303\\251.md"` for `café.md` - and `endswith(".md")` is then False. The document
    would leave the corpus silently, which is the same fail-open shape as the untracked
    file entering it, one filter later. `-z` turns quoting off and separates on NUL, so a
    name holding a newline survives too. `corpus_control.py --mutate no_nul` is the pin.
    """
    base = ROOT if root is None else root
    ok, out = (_git_at(base, "ls-tree", "-r", "--name-only", "-z", rev) if rev
               else _git_at(base, "ls-files", "-z"))
    if not ok:
        raise RuntimeError(
            f"git {'ls-tree ' + rev if rev else 'ls-files'} failed in {base}: {out.strip()[:200]}. "
            f"The corpus is an input to every check in this file, and an empty one reads "
            f"as clean.")
    return sorted(r for r in out.split("\0") if r.endswith(".md"))


def project_docs(root: str | None = None) -> list[str]:
    """Every TRACKED project markdown file outside a dot-directory, as absolute paths.

    Two exclusions, and they are different in kind:

    `runs/` and vendored trees are stored data, filtered here by path.

    Dot-directories are excluded because the skills live under them and this helper feeds
    the size report and the bare-trial-id ratchet, which is pinned to an EXACT count a
    larger corpus would move. The reference checks want the skills and read
    `reference_docs()` instead. Until 2026-08-27 that exclusion was an accident of `glob`
    not descending into a dotted name; it is now stated, so a reader can see it is a
    choice and a mutant can remove it.

    TRACKED, not "on disk". `glob` counted any markdown lying in the tree, so an untracked
    scratch note under a gitignored directory joined a corpus the ratchet is pinned to:
    writing `staging/task-176-note.md` took `--sweep` from 249 documents to 250 at exit 0,
    and the same note under `staging/findings/` citing three trial ids took the ratchet
    from 18 to 21 and failed the sweep. A file that is not in the repository must not be
    able to move a gate that is.

    The INDEX, not `HEAD`: a document written and `git add`ed is swept before it is
    committed, which is what the pre-commit hook needs and why `.agents/skills/work`
    tells you to stage before running the gates. A document written and never staged is
    not in the repository yet, and this says so rather than guessing.

    `root` exists for `_corpus_pins`, which drives a fixture repository through this
    function. Everything else takes the default.
    """
    base = ROOT if root is None else root
    out = []
    for rel in _tracked_md(root=base):
        if any(part.startswith(".") for part in rel.split("/")):
            continue
        p = os.path.join(base, *rel.split("/"))
        if is_vendored(p) or f"{os.sep}runs{os.sep}" in p:
            continue
        if not os.path.exists(p):
            continue                      # tracked, deleted in the working tree
        out.append(p)
    return sorted(out)


def _all_skill_files() -> list[str]:
    """Every SKILL.md in the tree, dot-directories included.

    `glob` skips names beginning with a dot, and every skill in this project lives under
    one. Anything asking a question ABOUT the skills must walk instead.

    `runs/` is stored data and `worktrees/` are whole checkouts of this repo; a copy of
    the authoritative tree inside either is not a second source of truth.
    """
    out = []
    for d, subs, files in os.walk(ROOT):
        subs[:] = [s for s in subs
                   if s not in ("runs", "worktrees", ".git") and not is_vendored(s)]
        if is_vendored(d):
            continue
        if "SKILL.md" in files:
            out.append(os.path.join(d, "SKILL.md"))
    return out


def github_docs(root: str | None = None) -> list[str]:
    """Every non-vendored markdown file under `.github/`, at any depth.

    `project_docs()` excludes every dot-directory, so `.github/` is invisible to it for
    exactly the reason `.claude/` is. That left
    `.github/workflows/README.md` - the register `AGENTS.md` tells every session to read
    before adding a gate, and which names dozens of this repository's own tools and flags -
    outside every reference check, passing nothing rather than passing. Measured with the
    same `--no-such-flag-147` planted on a fenced command line of each file: `--sweep` came
    back exit 0 on the register and exit 1 naming the flag on the identical plant in
    `DECISIONS.md`.

    Globbed by DIRECTORY, never by filename, and recursively rather than at one level.
    Naming the one file that exists today is the enumeration failure `AGENTS.md`'s rule
    audit describes, and the next document added under `.github/` would be unswept in the
    same silent way - which is what `_corpus_pins` drives a nested fixture through.

    WHAT THIS BUYS, AND WHAT IT DOES NOT. Being in `reference_docs()` is necessary and not
    sufficient: two of the reference halves carry their own file-wide trigger, and one of
    them does not admit this file. Measured by planting the same phantom token 4 ways in
    the register and in `DECISIONS.md`:

      plant                                   register   DECISIONS.md
      bare flag on a fenced command line       exit 1     exit 1     <- reads .github/
      backticked flag, script named on line    exit 0     exit 1     <- does NOT
      backticked flag, no script on the line   exit 0     exit 1     <- does NOT
      phantom aspect in prose                  exit 0     exit 0     <- neither: see below

    The backticked half is gated on `harness`, a file-wide search for 4 harness script
    names, and the register names none of them - it names tools. The aspect half is
    scoped to documents that make a claim about aspects, which this file never does, so
    its exit 0 is agreement rather than absence.

    THE OBVIOUS REPAIR IS MEASURABLY WORSE, which is why it is recorded here instead of
    applied. Replacing the 4-name enumeration with the closed class `_our_script_names()`
    takes the admitted corpus from 43 documents to 165 and adds **25 rows, of which 0 are
    true positives** - `--auto`, `--body-file`, `--ours`, `--theirs` (`gh` and `git`),
    `--doctool` (Godot), `--enable-unsafe-webgpu` (Chrome), and the deliberately-fake
    tokens task files name on purpose. That is the shape `AGENTS.md`'s rule audit
    describes: an open-class property that fires on correct input is how a gate gets
    disabled. `_corpus_pins` holds the exclusion so it cannot become silent.

    `root` exists for those pins. Everything else takes the default.
    """
    base = ROOT if root is None else root
    return sorted(q for q in glob.glob(os.path.join(base, ".github", "**", "*.md"),
                                       recursive=True)
                  if not is_vendored(q))


def _github_docs_by_walk(root: str | None = None) -> list[str]:
    """The same set, found by WALKING - the pins' independent statement of the answer.

    A control that computes its expectation by calling the function under test agrees with
    every mutant of that function: the `tasks.py note` control built its expected bytes from
    `tasks.py`'s own helper and came back SURVIVED on 48 rows (task 113, `AGENTS.md` rule 12).
    So this reaches the same files by a different mechanism, and `_corpus_pins` compares the
    two rather than making them one object.
    """
    base = ROOT if root is None else root
    out = []
    for d, subs, files in os.walk(os.path.join(base, ".github")):
        # FULL PATHS, because that is what `is_vendored` tests. 3 of the 5 VENDORED
        # entries are path fragments carrying separators - `/target/`, `/.godot/`,
        # `/Library/` - so `is_vendored("target")` on a bare directory NAME is False
        # while `is_vendored(".../target/x.md")` is True. An oracle filtering names
        # would keep a file the subject drops and redden `--selftest` against a correct
        # `reference_docs()`: a check that fails on correct input is one that gets
        # disabled. Raised by CodeRabbit on PR #25.
        subs[:] = [s for s in subs if not is_vendored(os.path.join(d, s) + os.sep)]
        if is_vendored(d + os.sep):
            continue
        out += [os.path.join(d, f) for f in files
                if f.endswith(".md") and not is_vendored(os.path.join(d, f))]
    return sorted(out)


def reference_docs() -> list[str]:
    """The corpus for the REFERENCE checks: every project doc, every skill, and `.github/`.

    The skills are always-loaded instruction documents. A skill naming a flag or an aspect
    that does not exist is the exact defect this sweep was built for (#38), and until
    2026-08-23 nothing had ever looked: `project_docs()` excludes dot-directories, and every
    skill lives under one.

    `project_docs()` is deliberately NOT widened to fix that. It also feeds the size report
    and the bare-trial-id ratchet, and the ratchet is pinned to an EXACT count; a larger
    corpus would move it silently, in the direction that makes the guard pass. A corpus is
    an input to a check (#60), so each check names the one it wants rather than inheriting
    whatever a shared helper happens to return.

    BEING IN THIS LIST IS NECESSARY AND NOT SUFFICIENT, because a half can carry its own
    trigger on top of the corpus. All three now read every skill, and the backticked flag
    half did not until 2026-08-25: it is gated file-wide on 4 harness script names, which
    admitted 4 of the 10. `_backticked_flags()` records what admitting the rest cost and
    why the answer changed; `_skill_flag_coverage()` is its producer and
    `_skill_flag_pins()` holds both directions, so neither the coverage nor its price can
    move silently.

    The aspect check finds 2 hits over the skills before fence-masking and 0 after, both
    on the same line of `audit-docs/SKILL.md` - the shell command that plants the phantom
    aspects `feel` and `tuning` as this sweep's own positive control. The ratchet is
    scoped to `findings/`, so no skill can move it.
    """
    return sorted(set(project_docs()) | set(_all_skill_files()) | set(github_docs()))


def _fence_mask(lines: list[str]) -> list[bool]:
    """True for every line inside (or delimiting) a ``` fence.

    ONE fence tracker, used by every check that reads markdown structure. Two spellings
    of the same rule drift, and the drift is invisible until one of them reads a code
    comment as prose — which is the defect this module was written for.
    """
    mask, fence = [], False
    for l in lines:
        if l.lstrip().startswith("```"):
            mask.append(True)
            fence = not fence
            continue
        mask.append(fence)
    return mask


# WHAT THE STRUCTURE GATES ARE POINTED AT, and what they are deliberately not.
#
# `--sweep`'s reference checks run over every project doc. The two STRUCTURE checks below
# (skill frontmatter, list-continuation indent) run over a smaller set: the documents that
# are read as instructions — skills, the open-work queue, and the always-on root docs.
#
# `eval/findings/`, `eval/FINDINGS.md` and `eval/RUNS.md` are excluded because they are the
# ARCHIVE. A findings log records what was true when it was written, including the broken
# shapes it is about; re-indenting one to satisfy a gate edits evidence. The reference
# checks already exempt `findings/` for the same reason, one line at a time.
#
# Measured, 2026-08-23: the indent check finds 0 in this scope AND 0 across all 365 markdown
# files in the main checkout, so the scope is not hiding false positives — it is a statement
# about which files anyone is allowed to reformat.
#
# The root docs are addressed as A PROPERTY - any markdown file directly at the repo root -
# not as the six names that happen to be there today. AGENTS.md's own audit: a trigger
# written as an enumeration has to be re-derived by every reader who meets an item not on
# the list, and the next always-on root doc would silently not be gated.
# THE SKILLS ADDRESS IS SPELLED ONCE, HERE, AND EVERY CHECK DERIVES FROM IT.
#
# AGENTS.md rule 12: when a path is spelled in two places, assert them equal in code. It
# used to be spelled three times in this file - `GATED_DIRS`, the size-report glob, and the
# skill-location gate - which is the same defect with a shorter blast radius. Changing the
# layout on 2026-08-23 meant changing all three, and a reader who changed two would get a
# gate that reported clean over zero files.
#
# The real files live at SKILLS_REAL. Every other path that reaches them is in SKILLS_LINKS
# and must be a SYMLINK to SKILLS_REAL - never a copy. That is the whole of #99: its
# objection was to a duplicate that drifts, not to a location, and a symlink cannot drift.
# `_check_skill_location` asserts both halves, so neither is a promise in a comment.
SKILLS_REAL = ".agents/skills"
SKILLS_LINKS = (".claude/skills",)
GATED_DIRS = (SKILLS_REAL, "tasks")


def gated_docs() -> list[str]:
    """Instruction documents the structure checks may hold to a format.

    The skills live under DOT-directories, which `project_docs()` excludes, so it has
    never contained a single `SKILL.md` and neither has any check built on it. They are
    globbed explicitly here. Reading a scope off a helper whose exclusions you have not
    checked is how a gate comes to run over 0 of its subjects.
    """
    out = []
    for p in project_docs():
        rel = os.path.relpath(p, ROOT)
        if os.sep not in rel or rel.startswith(tuple(d + os.sep for d in GATED_DIRS)):
            out.append(p)
    for d in GATED_DIRS:
        out += [p for p in glob.glob(os.path.join(ROOT, d, "**", "*.md"), recursive=True)
                if p not in out]
    return sorted(set(out))


def skill_files() -> list[str]:
    """Every skill the frontmatter gate must parse.

    Delegates to `_all_skill_files()`, which WALKS, rather than globbing a list of
    directories. Two reasons, and the second is the point of the gate:

    1. `glob` does not descend into dot-directories, and every skill here lives under one.
       A `**` spelling of this returned zero files while reporting clean.
    2. Enumerating directories means a skill in a directory nobody listed is not parsed —
       and an unparseable skill in an unexpected place is exactly what this checks for.
       The address is the property; the directory name is an instance of it.
    """
    return _all_skill_files()

def headings(path: str) -> list[tuple[int, str, int]]:
    """Fence-aware. Returns (line_no, heading, section_chars).

    Without the fence mask, any code comment starting with # is read as a heading — the
    exact defect this module exists to prevent.
    """
    lines = open(path, encoding="utf-8", errors="replace").read().split("\n")
    fenced = _fence_mask(lines)
    hits: list[tuple[int, str]] = []
    for i, l in enumerate(lines):
        if fenced[i]:
            continue
        if re.match(r"^#{1,6} ", l):
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

    skills = sorted(glob.glob(os.path.join(ROOT, SKILLS_REAL, "*", "SKILL.md")))
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


def _our_script_names() -> set[str]:
    """Basenames of eval/ python files that own an argparse.

    Derived from the code, never enumerated: this is the same glob `_argparse_flags()`
    walks, asking which files parse a command line rather than which flags they declare.
    An enumeration would go stale the first time a tool is added, in the direction that
    makes the gate quiet.
    """
    out = set()
    for p in glob.glob(os.path.join(REPO, "**", "*.py"), recursive=True):
        if is_vendored(p):
            continue
        if "add_argument(" in open(p, errors="replace").read():
            out.add(os.path.basename(p))
    return out


# A shell operator ends the command our script name introduced. `docstat.py --sweep |
# grep --color=auto` names one of ours and then hands the rest of the line to a program
# that is not ours; without this cut, `--color` reads as a phantom of ours.
_SHELL_BREAK = re.compile(r"[|;&><]")


def _blank_code_spans(line: str) -> str:
    """Backticked spans blanked to spaces, PRESERVING OFFSETS.

    Two reasons it is spaces and not deletion. The bare-flag scan below finds a script
    name in the raw line and then reads the tail after it, so the two strings have to
    agree on where things are. And deletion silently removes the script name itself when
    a doc writes `judge/runner.py` in backticks and its flag bare -- a false negative
    produced by the very substitution meant to prevent a double report.
    """
    return re.sub(r"`[^`]*`", lambda m: " " * len(m.group(0)), line)


def _bare_fenced_flags(lines: list[str], scripts: set[str]) -> list[str]:
    """Bare `--flags` on a fenced line that invokes one of OUR argparse scripts.

    THE GAP THIS CLOSES (task 89): the backticked flag check is spelled `` `--flag` ``,
    so it sees inline code and nothing else. A usage block is written bare -- it is text
    a reader COPIES AND PASTES -- so the highest-damage position for a phantom flag was
    the one position nothing looked at. Measured, not assumed: a fenced
    `python3 judge/runner.py --no-such-flag-bare1` read sweep exit 0, while the same fake
    flag backticked inside the same fence read exit 1.

    WHY THE TRIGGER IS THE SCRIPT NAME AND NOT THE `--` TOKEN. Both candidates were run
    over the live corpus of 167 reference docs on 2026-08-23:

      any bare flag on any fenced line     8 hits, 0 true positives -- `git merge
                                           --no-ff`, `cargo doc --open`, `Godot --path`,
                                           `vale --config`, `npx --yes`, the claude CLI's
                                           `--output-format`. Every one another tool's.
      after one of OUR scripts, cut at     0 hits, over a population of 56 fenced lines
      the first shell operator              naming our scripts and 31 in-scope tokens, of
                                            which 30 resolve to our own argparse and 1 is
                                            known-foreign.

    The second number is the one that matters: **0 on a clean corpus is worthless unless
    the check had something to discriminate**, and this one reads 31 real tokens and
    finds them all sound. `--selftest` pins both directions.

    NOT WIDENED TO UNFENCED PROSE. The same trigger over every line, fenced or not, sees
    234 lines and 96 tokens and returns 2 unresolved, both false: a sentence naming
    `field.py` and then the claude CLI's `--output-format`, and one naming a script and
    then `git diff --stat`. 0 true positives, because prose backticks its flags and the
    existing check already has those. A gate that fails on correct input gets disabled.

    THE FALSE NEGATIVE IT ACCEPTS, stated because a mutant found it rather than a reader:
    only the tail of the line AFTER the script name is read, so a flag written BEFORE the
    program it belongs to is invisible. That is right for a command line -- flags follow
    the program -- and it is why the first draft of the prose pin below tested nothing:
    it placed the flag first, so it stayed green no matter what the trigger did.

    NOT GATED ON THE DOCUMENT-WIDE `harness` TEST that the backticked check uses. This
    trigger carries stronger evidence per line than that gate does per file, and the
    comment on FOREIGN_FLAG_PREFIXES records what the document-wide form cost: it hid a
    false positive for three weeks until an unrelated edit added a harness name to the
    file. A condition that hides a defect until a distant edit reveals it is a latent
    report, not a clean one.
    """
    mask = _fence_mask(lines)
    out: list[str] = []
    for i, ln in enumerate(lines):
        if not mask[i] or re.search(_DELIBERATELY_FAKE, ln, re.I):
            continue
        start = None
        for s in scripts:
            m = re.search(re.escape(s), ln)
            if m and (start is None or m.end() < start):
                start = m.end()
        if start is None:
            continue
        tail = _blank_code_spans(ln)[start:]
        brk = _SHELL_BREAK.search(tail)
        if brk:
            tail = tail[:brk.start()]
        out.extend(re.findall(r"(?<![\w`-])(--[a-z0-9-]{2,})", tail))
    return out


def _aspect_ids() -> set[str]:
    p = os.path.join(REPO, "judge", "aspects.py")
    if not os.path.exists(p):
        return set()
    s = open(p, errors="replace").read()
    m = re.search(r"ASPECTS\s*=\s*\{[^}]*\(([^)]*)\)", s, re.S)
    if not m:
        return set()
    return {t.strip().lower() for t in m.group(1).split(",") if t.strip()}


# NO CRITERION-ID CHECK, and no `_criterion_ids()` helper. One sat here unused from the
# start while AGENTS.md and audit-docs/SKILL.md both told readers criterion ids were swept;
# planted phantom ids read exit 0 (task 77). A function named for a check that does not run
# is the same defect as a document naming one, one layer down, so it is deleted rather than
# left as documentation of intent. Its extraction was also unusable: every `"a.b_c"` string
# literal in judge/*.py, which harvests `re.search` and `aspects.py`.


def _project_root_for(doc: str) -> list[str]:
    """Roots a relative path in a doc could legitimately be written against.

    A doc inside eval/starters/godot/ writes `tools/boundary.gd` relative to that
    starter's root, not to the repo root and not to the doc's own directory. Without
    this, every stack's own docs report dozens of phantom paths. (The example used to
    be template-godot/, deleted 2026-08-23 — #119. The shape is unchanged: any tree a
    building agent is handed is its own root.)
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
    # `prime-agent`'s autonomous family, named by the ticket that adds it as a second agent
    # harness. A PREFIX because it is a family -- `--autonomous`, `--autonomous-max-turns`,
    # `--autonomous-gate`, `--autonomous-gate-retries`, `--autonomous-max-continuations` --
    # and distinctive enough that it cannot swallow a flag of ours.
    "--autonomous",
    "--max-turns", "--max-budget", "--permission-mode", "--setting-sources",
    "--strict-mcp", "--exclude-dynamic", "--append-system-prompt", "--system-prompt",
    "--json-schema", "--include-partial", "--fallback-model", "--no-session",
    "--forward-subagent", "--bare", "--tools", "--headless", "--help", "--version",
    "--quiet", "--strict", "--no-header", "--check-only", "--experimental-",
    "--write-movie", "--update-snapshots", "--keep-going", "--no-patch", "--no-verify",
    "--file", "--re", "--flags",
    # the claude CLI's. `field.py` runs the judge with `--output-format stream-json`, and
    # tasks/19 and research/01 both say so. It was invisible until task 89: both wrote it
    # BARE, which the backticked half never saw, and research/01 writes it inside a fence.
    # The first live document to backtick it turned the sweep red -- which is the
    # FOREIGN_FLAG_PREFIXES note above repeating itself, a false positive kept latent by
    # the shape of the mention rather than by anything being right.
    "--output-format",
    # rsync's. `backup_evidence.py` documents that it runs WITHOUT --delete, which is
    # why the copy is a superset (#115); the flag it names is rsync's, not ours.
    "--delete",
    # bsdtar's, and it does not exist there — which is the point of the sentence naming
    # it (root `AGENTS.md` rule 12, "bsdtar rejecting `--wildcards`"). This one is worth
    # a note beyond the entry: the suppression above is "does this doc mention one of our
    # harnesses", so the false positive was INVISIBLE until an unrelated edit added the
    # word `wholegame.py` to that file, three weeks after the flag was written. A
    # condition that hides a defect until a distant edit reveals it is a latent report,
    # not a clean one.
    "--wildcards",
    # cargo's. `eval/RUNS.md`'s rust `default-run` break quotes cargo's own error, which
    # offers `--bin` as the alternative remedy, and argues why the manifest key was taken
    # instead. A doc that reproduces a foreign tool's error text verbatim is the case this
    # list exists for; the alternative is paraphrasing the error, which is how a quoted
    # measurement stops being quotable.
    "--bin",
    # gh's. `DECISIONS.md`'s review-completion entry argues WHY the poll paginates and why
    # the pages are aggregated by an external `jq -s` — gh rejects `--slurp` alongside
    # `--jq`, which is the whole reason the recipe is shaped the way it is (task 121). The
    # flags appear backticked in prose because the argument is about them; the fenced
    # recipe in `.agents/skills/work/SKILL.md` was already green, because a flag on a
    # command line naming `gh` is not read as one of ours. That asymmetry is the case this
    # list exists for.
    #
)

# Foreign flags matched EXACTLY, not by prefix. Everything above is a prefix because it
# has to be -- `--experimental-` is written as one, and `--max-budget` stands in for
# `--max-budget-usd`. These do not, and prefix-matching them would be a widening nobody
# asked for: `--jq` is 4 characters, so `--jq-local` on one of our own scripts would be
# silently exempt forever, and every reason not to count a failure is a channel a bug can
# widen (root AGENTS.md rule 7).
#
# gh's. `DECISIONS.md`'s review-completion entry argues WHY the poll paginates and why the
# pages are aggregated by an external `jq -s` -- gh rejects `--slurp` alongside `--jq`,
# which is the whole reason the recipe is shaped the way it is (task 121). The flags appear
# backticked in prose because the argument is about them; the fenced recipe in
# `.agents/skills/work/SKILL.md` was already green, because a flag on a command line naming
# `gh` is not read as one of ours. That asymmetry is the case this list exists for.
#
# The red control was run both ways on 2026-08-23 and the FIRST attempt was a FALSE GREEN:
# the planted token was `--zzqphantomflag`, and `_DELIBERATELY_FAKE` matches the substring
# `phantom`, so the check reported clean about a line it never read. Plant a name with no
# exemption word in it. `--zzqnotaflag` turns this red; `--jq-local` turns it red too, which
# is the pin that the exact match is doing something.
# `gh` and `jq`, spelled exactly: these are short enough that a prefix match would
# swallow flags of ours that merely start the same way. `--admin` is `gh pr merge`'s
# bypass, which DECISIONS.md and #162 both have to name to say what is not covered.
# The last six are `prime-agent`'s, the second agent harness. EXACT and not a prefix on
# purpose: `--print` and `--cwd` are generic enough that a prefix would swallow a flag of
# ours that merely starts the same way. The two `--autonomous` ones are here because
# `eval/RUNS.md` and `eval/PROTOCOL.md` have to NAME the flag they refuse to pass — it is
# the only turn ceiling that arm has, and it comes with continuations and gate re-runs the
# claude arm never sees, so a document that could not name it could not say why the arm is
# bounded by wall clock instead.
FOREIGN_FLAGS_EXACT = frozenset({"--absolute-git-dir", "--show-toplevel",
                                 "--paginate", "--slurp", "--jq", "--admin",
                                 "--print", "--cwd", "--provider", "--thinking",
                                 "--autonomous", "--autonomous-max-turns",
                                 # git's own, named whenever a merge method is discussed in prose
                                 "--no-ff", "--no-edit", "--porcelain",
                                 "--ours", "--theirs", "--merge", "--offline",
                                 # `gh`'s, and two from tools named in tasks/149's census of
                                 # candidate false positives: a doc tool and Chrome.
                                 "--auto", "--body", "--body-file",
                                 "--doctool", "--enable-unsafe-webgpu"})


def _check_skill_frontmatter() -> list[str]:
    """Every SKILL.md must expose metadata a YAML parser can actually read.

    THE DEFECT THIS WAS BOUGHT WITH: 5 of 7 project skills, and 5 of 6 of their
    `.agents/` duplicates, had frontmatter no external tool could parse — an unquoted
    scalar containing `": "`, e.g. `description: Add a game task...: prompt rules that`.
    At load time the whole block is dropped and the skill gets EMPTY metadata, so it is
    never selected, and nothing in the file looks wrong. Seven prose linters read those
    files and reported them clean; only a schema parser saw it (research/11, §1.2).

    WHAT WOULD MAKE THIS FIRE FALSELY: nothing that is also valid YAML. This is the one
    check here with no judgement in it — the value either `safe_load`s or it does not.

    Failing CLOSED when PyYAML is absent is deliberate. A structure check that quietly
    skips itself is the vacuous pass this whole module exists to prevent.
    """
    problems, files = [], skill_files()
    if not files:
        return [f"no SKILL.md found under {' or '.join(GATED_DIRS[:2])} - "
                f"the frontmatter check has nothing to read (wrong root?)"]
    try:
        import yaml
    except ImportError:
        return ["PyYAML is not importable, so SKILL.md frontmatter was NOT checked. "
                "Install it (pip install pyyaml) rather than ignoring this line: an "
                "unparseable skill loads with empty metadata and never gets selected."]
    for p in files:
        rel = os.path.relpath(p, ROOT)
        text = open(p, encoding="utf-8", errors="replace").read()
        m = re.match(r"^---\n(.*?)\n---\s*?\n", text, re.S)
        if not m:
            problems.append(f"{rel}: no YAML frontmatter block; the skill loads with no "
                            f"name or description and is never selected")
            continue
        try:
            meta = yaml.safe_load(m.group(1))
        # Narrow: YAMLError is the base of every parse failure PyYAML raises, and it is
        # the only thing `safe_load` on a string should produce. A blind catch would
        # have reported a bug in this sweep as "your frontmatter is malformed", i.e.
        # sent the reader to edit a file that was fine.
        except yaml.YAMLError as e:
            problems.append(f"{rel}: frontmatter does not parse as YAML "
                            f"({str(e).splitlines()[0]}). A value containing `: ` must be "
                            f"quoted; unparsed frontmatter is DROPPED, not reported")
            continue
        if not isinstance(meta, dict):
            problems.append(f"{rel}: frontmatter parses as {type(meta).__name__}, not a "
                            f"mapping of fields")
            continue
        # name and description are what the loader selects a skill BY. Measured
        # 2026-08-23: present in 13 of 13 skill files, so this costs 0 false positives.
        for k in ("name", "description"):
            if not str(meta.get(k) or "").strip():
                problems.append(f"{rel}: frontmatter has no `{k}`")
    return problems


def _check_list_indent() -> list[str]:
    """Ordered-list continuations that fall outside the item they belong to.

    THE DEFECT: `AGENTS.md` rules 1-9 use one-digit markers, whose continuation indent is
    3 spaces. Rules 10-16 use two-digit markers, which need 4. Every continuation there
    was indented 3, so lazy continuation held the FIRST paragraph of each rule and every
    paragraph after a blank line detached to top level - five of them, structurally no
    longer part of the rule they argue for (research/11, §1.1). markdownlint reported it
    as 22 confusing MD029 alerts inside 9,697; remark-preset-lint-recommended called the
    file completely clean while remark's own parser was detaching the paragraphs.

    NARROW BY MEASUREMENT, not by taste. The broad form - "no root-level block indented
    1-3 spaces" - fires where nothing is wrong. Task 36 measured it at 15 hits across 10
    files in `tasks/` and inspected every one; an independent implementation of the same
    idea, run here on 2026-08-23 over the gated scope, measured 7, also all in `tasks/`.
    The two counts differ because "root-level" is a judgement call and the broad form is
    made of judgement calls - which is the point. Neither set contains this defect: they
    are 2-space lists and prose introduced by a paragraph ending in a colon, with no
    ordered item above them. Nothing lost a parent.

    A gate that fails on correct input gets disabled, which is why the path check above was
    deleted rather than tuned. So this asks only the question that has a true positive:
    does a 2+ DIGIT top-level ordered marker have a continuation indented less than its
    own marker width?

    Measured with THIS code, 2026-08-23: 0 hits across all 365 markdown files in the main
    checkout with the scope removed, and 5 hits - at exactly the five lines §1.1 names -
    against a reconstruction of the pre-task-36 AGENTS.md.
    """
    marker = re.compile(r"^(\d{2,})([.)])( {1,4})\S")
    docs = gated_docs()
    # THE ADDRESS IS AN INPUT TO THE CHECK (#60). An empty corpus passes silently and is
    # indistinguishable from a clean one, so say so instead of returning green.
    if not docs:
        return [f"no instruction docs found under {', '.join(GATED_DIRS)} or at the repo "
                f"root - the list-indent check read an empty corpus (wrong root?)"]
    problems = []
    for p in docs:
        rel = os.path.relpath(p, ROOT)
        lines = open(p, encoding="utf-8", errors="replace").read().split("\n")
        fenced = _fence_mask(lines)
        i = 0
        while i < len(lines):
            m = marker.match(lines[i])
            if not m or fenced[i]:
                i += 1
                continue
            # CommonMark: continuation lines belong to the item only if indented to the
            # column its content starts at - digits + delimiter + the spaces after it.
            need = len(m.group(1)) + 1 + len(m.group(3))
            j, blank = i + 1, False
            while j < len(lines):
                l = lines[j]
                if fenced[j]:
                    j += 1
                    continue
                if not l.strip():
                    blank = True
                    j += 1
                    continue
                ind = len(l) - len(l.lstrip(" "))
                # Indent 0 after a blank ENDS the list, which is how lists are meant to
                # end - not a defect. Only 1..need-1 is the half-attached case: it looks
                # indented, and it is outside the item.
                if ind == 0:
                    break
                if blank and ind < need:
                    problems.append(
                        f"{rel}:{j + 1}: continuation indented {ind} under a "
                        f"{len(m.group(1))}-digit marker `{m.group(1)}{m.group(2)}` "
                        f"needing {need} - this block detaches from item "
                        f"{m.group(1)} in every CommonMark parser: {l.strip()[:48]}")
                blank = False
                j += 1
            i = j
    return problems


# THE ORPHANED EDIT TAIL, and why the trigger is not the one task 99 asked for.
#
# The defect: an edit rewrites a sentence that was WRAPPED across several lines and replaces
# only the lines it touched, leaving the last wrapped line of the OLD sentence stranded below
# the new one. It is not a wrong claim and not a stale number, so no withdrawal register entry
# and no consistency check applies - it is text corruption, and it sat at line 6 of
# `eval/FINDINGS.md`, the file every session is told to read first.
#
# `tasks/99` specified the trigger as "a strict suffix of the sentence ending on the line
# above". MEASURED AGAINST THE REAL BLOB, THAT TRIGGER DOES NOT FIRE. At `1f6fb65` the
# stranded line 6 is
#
#     number has been retracted before trusting it.**
#
# and the sentence ending on line 5 is "...`docstat.py --withdrawn` enforces it over the live
# documents." The fragment is a suffix of the sentence that was DELETED, whose head ("**Check
# whether a") still sits on line 3 - not of anything ending on line 5. Writing the ticket's
# trigger would have produced a check that is green on the only defect anyone has ever seen,
# which is the failure mode this file exists to catch. The ticket is the bug; this is the note.
#
# THE PROPERTY ACTUALLY SHIPPED: an unfenced, non-structural prose line of >=5 words whose
# normalised text already appears verbatim in the same paragraph above it. The orphan is a
# REPETITION - that is what an editor leaving half a replaced sentence behind produces - and
# repetition is a closed property of the text, not a vocabulary. AGENTS.md's census-trigger
# rule asks for a closed class chosen on its live-corpus false-positive count, and this is the
# first trigger tried here that opens at 0 rather than at 8, 18 or 26 (#140, #142, #146).
#
# MEASURED over the whole reference corpus (live AND archive) at HEAD: 0 hits, 188 documents
# when last re-derived - `cmd_sweep` runs this on every invocation, so the count is the
# sweep's own. The tighter variant that also requires the line to END its paragraph is
# likewise 0, so the looser one ships - same measured cost, strictly more coverage.
#
# 0 AT HEAD IS NOT A BASE RATE, because the tree at any commit holds only the defects nobody
# has repaired yet, and this one was repaired. Over every version of every reference document -
# 1,551 (version, path) pairs across all 451 commits when last run - this check finds exactly 1
# incident, the same stranded line carried in 34 versions of `eval/FINDINGS.md`. The producer
# is `python3 eval/tools/integrity_census.py`; DECISIONS.md holds the decision that rests on it.
#
# SCOPE IS `reference_docs()`, WHICH INCLUDES THE ARCHIVE, and that is deliberate against the
# usual rule two hundred lines up. The structure checks exempt `eval/findings/` because
# re-indenting an archived entry edits evidence. A half-sentence left by a botched edit is not
# evidence of anything - it is damage - and the one instance was in the archive. A findings
# entry QUOTING such a defect would sit in a fence, which is masked.
_ORPHAN_MIN_WORDS = 5

# Anything a markdown structure puts at the start of a line. A table row, a list item or a
# heading repeating text within one paragraph is ordinary formatting, not a stranded edit.
_ORPHAN_STRUCTURAL_RX = re.compile(r"^\s*(\||>|#|[-*+]\s|\d+[.)]\s|\[|!\[|:?-{3,})")


def _orphan_normalise(s: str) -> str:
    """Prose content of a line, with the punctuation an edit boundary disturbs removed.

    The stranded line and its origin differ by exactly the debris of the cut: the orphan ends
    `trusting it.**` where the surviving copy reads `trusting it** - `. Emphasis runs,
    backticks and terminal punctuation are therefore stripped on both sides. Case is folded
    because a re-wrapped sentence may capitalise a word that was mid-sentence before.
    """
    s = s.replace("`", "")
    s = re.sub(r"[*_]{1,3}", "", s)
    s = re.sub(r"\s+", " ", s.lower()).strip()
    return s.strip(".,;:!?—–- ")


def _check_orphaned_tail(text: str, rel: str) -> list[str]:
    """Prose lines that repeat text already present in the paragraph above them.

    A FUNCTION OF ITS INPUTS, not of the repository, so the pins can hand it the historical
    blob that carries the real defect rather than a retyped imitation of it.
    """
    lines = text.split("\n")
    mask = _fence_mask(lines)
    problems = []
    for i, line in enumerate(lines):
        if i == 0 or mask[i] or not line.strip():
            continue
        if _ORPHAN_STRUCTURAL_RX.match(line):
            continue
        cand = _orphan_normalise(line)
        if len(cand.split()) < _ORPHAN_MIN_WORDS:
            continue
        # The paragraph: contiguous non-blank, unfenced lines immediately above. Scoping to
        # the paragraph rather than the document is what keeps a sentence legitimately
        # restated later in a long file from reading as damage.
        above, j = [], i - 1
        while j >= 0 and lines[j].strip() and not mask[j]:
            above.append(lines[j])
            j -= 1
        if not above:
            continue
        if cand in _orphan_normalise(" ".join(reversed(above))):
            problems.append(
                f"{rel}:{i + 1}: this line repeats text already in the paragraph above it, "
                f"which is what an edit that rewrote a wrapped sentence and left its last "
                f"line behind produces: {line.strip()[:60]}")
    return problems


def _orphan_tail_pins(verbose: bool = False) -> list[str]:
    """Pin the orphaned-tail check in both directions, red from a real blob.

    THE RED CASE IS A BLOB, NOT A RECONSTRUCTION. `1f6fb65:eval/FINDINGS.md` is the tree as it
    stood with the defect in it; the fix landed as a side effect of an unrelated commit, so
    HEAD cannot supply it. A defect retyped from memory is a defect whose shape the author has
    already decided, and the check would then be pinned against its own assumptions.

    The expectation is stated HERE - line 6, and the words on it - rather than computed from
    the blob by the same code under test. A control that imports its expectation from its
    subject is not a control (AGENTS.md rule 12, task 113).

    The GREEN cases are the half that matters. Each is an input this trigger could plausibly
    mishandle, and repetition is common in correct markdown: tables restate terms, lists
    restate stems, fenced blocks contain literal duplicate lines, and a document may say the
    same sentence twice in two different paragraphs. All four must stay quiet.
    """
    out: list[str] = []

    def case(name: str, text: str, expect_red: bool, rel: str = "pin.md"):
        got = _check_orphaned_tail(text, rel)
        good = bool(got) == expect_red
        if verbose:
            print(f"{'PASS' if good else 'FAIL'}  {name}: {len(got)} hit(s), "
                  f"expected {'>=1' if expect_red else '0'}")
        if not good:
            out.append(f"the orphaned-tail pin '{name}' came out wrong: {len(got)} hit(s), "
                       f"expected {'>=1' if expect_red else '0'} - {got[:1]}")

    # `_git` returns "" on a non-zero exit and never raises, so the failure to guard against
    # is an EMPTY STRING, not an exception. Guarding the exception instead would leave the
    # red pin silently unrun on a shallow clone: `_check_orphaned_tail("")` returns no hits,
    # and no hits with nothing to find is indistinguishable from a check that cannot fire.
    blob = _git("show", "1f6fb65:eval/FINDINGS.md")
    if not blob.strip():
        # Unproven is a problem, not a pass. A shallow clone reaches this, so does a
        # rewritten history, and in both cases nothing has shown this check fires at all.
        out.append("the orphaned-tail red pin could not read 1f6fb65:eval/FINDINGS.md, so "
                   "the check is unproven - nothing here shows it can fire")
    else:
        hits = _check_orphaned_tail(blob, "eval/FINDINGS.md")
        want = "eval/FINDINGS.md:6:"
        if not any(h.startswith(want) for h in hits):
            out.append(f"the orphaned-tail red pin did not flag line 6 of "
                       f"1f6fb65:eval/FINDINGS.md, the one instance of this defect the "
                       f"project has seen - it found {hits or 'nothing'}")
        elif verbose:
            print(f"PASS  red, real blob 1f6fb65:eval/FINDINGS.md line 6: {hits[0][-60:]}")

    head = os.path.join(ROOT, "eval", "FINDINGS.md")
    if os.path.exists(head):
        case("green, the same file at HEAD with the orphan gone",
             open(head, encoding="utf-8", errors="replace").read(), False, "eval/FINDINGS.md")

    case("red, a stranded tail planted in ordinary prose",
         "The gate reads the stored manifest and compares it with what the\n"
         "run actually wrote, so a truncated upload is visible.\n"
         "run actually wrote, so a truncated upload is visible.\n", True)
    case("green, a duplicate line inside a fence",
         "Sample output:\n\n```\ntotal=0 passed=0 skipped=0 in this build\n"
         "total=0 passed=0 skipped=0 in this build\n```\n", False)
    case("green, a table restating a term in consecutive rows",
         "| what | why |\n|---|---|\n| the manifest of what was dropped | the manifest of "
         "what was dropped |\n", False)
    case("green, the same sentence in two different paragraphs",
         "A control shares the assumptions of the thing it controls.\n\n"
         "A control shares the assumptions of the thing it controls.\n", False)
    case("green, list items sharing a stem",
         "- the judge reads the pack and scores the field\n"
         "- the judge reads the pack and scores the field\n", False)
    return out


# ------------------------------------------------ the in-block duplicated fragment (task 119)
#
# THE DEFECT THIS CATCHES, AND WHY THE CHECK ABOVE CANNOT. A rewrite applied to half of one
# bullet leaves the old text and the new text side by side inside a single claim. In
# `DECISIONS.md` at 75dde71 the bullet on the rubric ceiling carried
# `40 of 56 matrix trials at the ceiling with *zero* variance, not merely near it (#92)` TWICE,
# eight lines apart, once continuing `. **What to do about it...` and once continuing ` - and
# became a gate...`. Task 116 removed it by hand. Nothing found it: `--sweep`, `--findings`,
# `--withdrawn`, `--renumbered`, `linkcheck.py`, `tasks.py check` and `withdrawn_control.py`
# all exit 0 on the tree that carried it, and so does `_check_orphaned_tail` - re-measured
# 2026-08-23 at HEAD, 0 hits on the pre-fix blob.
#
# The reason is structural, not a tuning gap. The duplicated span is a FRAGMENT: it starts
# mid-sentence and ends mid-sentence, so no LINE of it recurs whole and no SENTENCE of it
# recurs whole. Measured before this check was written: an exact-match rule over repeated
# sentences of 40+ characters scores 0 on the pre-fix blob AND 0 on the live corpus - the
# obvious property, and a complete false negative.
#
# WHY A WORD WINDOW, AND WHY TWELVE. Repetition is a closed property of the text rather than a
# vocabulary, which is what AGENTS.md's census-trigger rule asks for; the free parameter is the
# window, and it was chosen on the live false-positive count, never on which size sounds more
# principled. THE PRODUCER IS `python3 eval/tools/integrity_census.py --windows`, and these are
# its figures over the 188 reference docs (live AND archive) the corpus held when it last ran,
# with fences, table rows and frontmatter keys handled as below:
#
#     window   corpus hits   distinct phrases   pre-fix DECISIONS.md
#        8        11                5                  11
#        9         6                2                   9
#       10         3                1                   7
#       11         0                0                   5
#       12         0                0                   4      <- shipped
#       13         0                0                   3
#       14         0                0                   2
#       16         0                0                   0      <- invisible from here up
#
# The hits at 10 are FALSE POSITIVES and worth naming, because they are the shape this check
# will keep meeting: `DECISIONS.md`'s headroom blockquote runs "a stated mechanic gives an axis
# with no direction and every submission at the same point; a free parameter gives an axis with
# no direction and every submission at a different point". That is an antithesis - deliberate
# parallel construction, the repetition carrying the argument. Correct prose does this, and a
# gate that reddens it is a gate that gets switched off.
#
# READ THE DISTINCT-PHRASE COLUMN, NOT THE HIT COUNT. At 183 documents window 10 gave 1 hit; at
# 188 it gives 3, and all three are that one antithesis - quoted twice in DECISIONS.md and once
# in tasks/119 BECAUSE it was named as the false positive that set the boundary. The corpus
# acquired copies of the hit already counted, not a new kind of hit, so the growth is not
# evidence of an open class and must not be read as an argument for widening the window.
#
# 11 also measures 0, and 12 ships instead because 11 sits directly ON the boundary: one more
# antithesis one word longer turns it red. 12 keeps a word of margin at each end and still
# clears the real defect by three (14 is red, 16 is not). If this is ever retuned, retune it on
# a re-measured count over the corpus as it stands then - run the producer, do not re-derive
# the sweep by hand.
#
# AND 0 AT HEAD IS NOT A BASE RATE. Over every version of every reference document - 1,551
# (version, path) pairs across all 451 commits when last run - this check finds exactly 1
# incident, the `DECISIONS.md` bullet below, seen as 4 overlapping windows carried in 55
# versions. `integrity_census.py` is that census; DECISIONS.md holds what rests on it.
#
# SCOPE IS `reference_docs()`, live AND archive, for `_check_orphaned_tail`'s reason: a
# half-applied rewrite is damage, not evidence, and the archive is entitled to record retired
# figures but not to be broken. It costs nothing here - the archive contributes 0 hits at 12.
_DUP_FRAGMENT_WINDOW = 12

# A GFM table row, after any blockquote markers are stripped. EXCLUDED, and this exclusion is
# doing most of the work: a table's whole purpose is to repeat a stem down a column, and at
# window 12 the corpus goes from 6 hits to 0 when rows are dropped. Every one of the 6 was a
# table - `RESULT.md`'s identical confidence-interval rows, `JUDGING.md`'s repeated tau rows.
_DUP_TABLE_RX = re.compile(r"^\|")


def _frontmatter_span(lines: list[str]) -> int:
    """Index of the closing `---` of a leading YAML frontmatter block, or -1.

    A task file opens with one and `tasks.py` writes long free-text values into it.

    THE LIMIT, stated rather than left to be discovered: a document opening with a `---`
    HORIZONTAL RULE and carrying a second one later reads as frontmatter between the two.
    It can only make the block scope finer over that span - one line per line, so a repeat
    inside it is missed - and never coarser, so it cannot manufacture a hit. No document in
    the corpus has that shape; the whole corpus measures 0 either way.
    """
    if not lines or lines[0].strip() != "---":
        return -1
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return i
    return -1  # unterminated: not frontmatter, just a horizontal rule at the top


def _fragment_blocks(lines: list[str]) -> list[tuple[int, int]]:
    """`_claim_blocks`, except every frontmatter KEY is a block of its own.

    ONE KEY IS ONE CLAIM, and that is the whole of the frontmatter rule. `_claim_blocks`
    sees no blank line in a YAML header and returns the entire thing as one window, which
    made `tasks/42` the only hit in the archive at window 12: its `done_when` says the
    stale-files block must state that every judge round stored before the re-pack read a
    field that no longer exists, and its `established_by` reports that it now does. That is
    the queue's designed workflow - the goal restated as the result - not damage.

    Masking the header wholesale would also have measured 0, and this is chosen over it
    because it is strictly more coverage at the same cost: a fragment duplicated INSIDE one
    value still fires, and `established_by` is routinely a paragraph on one line.
    """
    end = _frontmatter_span(lines)
    head = [(i, i + 1) for i in range(end + 1) if lines[i].strip() not in ("---", "")]
    body = [("" if i <= end else l) for i, l in enumerate(lines)]
    return head + _claim_blocks(body)


def _fragment_words(line: str) -> list[str]:
    """Words of one line, with the markup an edit boundary disturbs removed.

    Backticks and emphasis runs only. Terminal punctuation is deliberately KEPT, unlike
    `_orphan_normalise`: there the two copies differ by the debris of the cut and had to be
    brought together, here the window is interior to both copies and every character that
    survives is another way for two merely-similar spans to disagree.
    """
    line = line.replace("`", "")
    line = re.sub(r"[*_]{1,3}", "", line)
    return [w for w in re.split(r"\s+", line.lower()) if w]


def _check_duplicate_fragment(text: str, rel: str) -> list[str]:
    """A word window that occurs twice inside ONE paragraph, list item or frontmatter key.

    A FUNCTION OF ITS INPUTS, not of the repository, so the pins can hand it the historical
    blob that carries the real defect rather than a retyped imitation of it.

    THE BLOCK IS THE UNIT AND IT IS LOAD-BEARING. A document may say the same twelve words
    in two paragraphs, in two bullets, or in a heading and again below it, and all of that is
    ordinary writing. What is not ordinary is saying them twice inside one claim, because a
    claim is what an editor rewrites in one motion.

    The words are accumulated ACROSS the lines of a block, so a duplicated span that straddles
    a line break is seen. That is not a nicety: the real instance happened to sit inside single
    lines, and a per-line implementation would have passed the pin while being unable to catch
    the same defect in a bullet wrapped one word earlier.
    """
    lines = text.split("\n")
    fenced = _fence_mask(lines)
    problems: list[str] = []
    for a, b in _fragment_blocks(lines):
        seq: list[tuple[str, int]] = []
        for i in range(a, b):
            if fenced[i]:
                continue
            stripped = lines[i].strip()
            while stripped.startswith(">"):
                stripped = stripped[1:].strip()
            if _DUP_TABLE_RX.match(stripped):
                continue
            seq += [(w, i + 1) for w in _fragment_words(stripped)]
        first: dict[tuple[str, ...], int] = {}
        n = _DUP_FRAGMENT_WINDOW
        for k in range(len(seq) - n + 1):
            window = tuple(w for w, _ in seq[k:k + n])
            if window in first:
                problems.append(
                    f"{rel}:{seq[k][1]}: these {n} words already occur at line "
                    f"{first[window]} of the same paragraph or list item, which is what a "
                    f"rewrite applied to half of one claim leaves behind: "
                    f"{' '.join(window)[:70]}")
            else:
                first[window] = seq[k][1]
    return problems


def _duplicate_fragment_pins(verbose: bool = False) -> list[str]:
    """Pin the duplicate-fragment check in both directions, red from a real blob.

    THE RED CASE IS A BLOB, NOT A RECONSTRUCTION, for `_orphan_tail_pins`' reason: task 116
    repaired `DECISIONS.md` by hand, so HEAD cannot supply the defect, and a defect retyped
    from memory is one whose shape the author has already decided.

    THE EXPECTATION IS STATED HERE - line 745, four windows - rather than computed from the
    blob by the code under test. A control that imports its expectation from its subject is
    not a control (AGENTS.md rule 12's corollary, task 113). The count is pinned as well as
    the line because the count is what moves when `_DUP_FRAGMENT_WINDOW` is retuned: at 16 the
    defect is invisible, and a pin that asked only "at least one hit" would let a silent
    retune out of the door.

    THE GREEN CASES ARE THE HALF THAT MATTERS (AGENTS.md rule 15). A mutant only asks whether
    this can fail; every green below is an input it could plausibly mishandle, and each one is
    a shape that occurs in correct markdown many times a document.
    """
    out: list[str] = []

    def case(name: str, text: str, expect_red: bool, rel: str = "pin.md"):
        got = _check_duplicate_fragment(text, rel)
        good = bool(got) == expect_red
        if verbose:
            print(f"{'PASS' if good else 'FAIL'}  {name}: {len(got)} hit(s), "
                  f"expected {'>=1' if expect_red else '0'}")
        if not good:
            out.append(f"the duplicate-fragment pin '{name}' came out wrong: {len(got)} "
                       f"hit(s), expected {'>=1' if expect_red else '0'} - {got[:1]}")

    # `_git` returns "" on a non-zero exit and never raises, so the failure to guard against
    # is an EMPTY STRING. Guarding an exception instead would leave the red pin silently
    # unrun on a shallow clone, where no hits with nothing to find is indistinguishable from
    # a check that cannot fire at all.
    blob = _git("show", "75dde71:DECISIONS.md")
    if not blob.strip():
        out.append("the duplicate-fragment red pin could not read 75dde71:DECISIONS.md, so "
                   "the check is unproven - nothing here shows it can fire")
    else:
        hits = _check_duplicate_fragment(blob, "DECISIONS.md")
        at_745 = [h for h in hits if h.startswith("DECISIONS.md:745:")]
        if len(at_745) != 4 or len(hits) != 4:
            out.append(
                f"the duplicate-fragment red pin expected exactly 4 windows at line 745 of "
                f"75dde71:DECISIONS.md - the half-applied rewrite task 116 removed by hand - "
                f"and got {len(hits)} hit(s), {len(at_745)} of them at 745. If "
                f"_DUP_FRAGMENT_WINDOW moved, re-measure the corpus false-positive count "
                f"before changing this number: {hits[:1] or 'nothing'}")
        elif verbose:
            print(f"PASS  red, real blob 75dde71:DECISIONS.md line 745: 4 windows, "
                  f"{at_745[0][-58:]}")

    case("red, a fragment duplicated inside one paragraph",
         "The gate reads the stored manifest and compares it with what the run actually\n"
         "wrote at the time of the upload, so a truncated one is visible. It then compares\n"
         "it with what the run actually wrote at the time of the upload, and became a gate\n"
         "rather than a score.\n", True)

    # THE VARIANT the ticket names, and the reason the words are pooled across a block. The
    # duplicated span here is broken by a line wrap in BOTH copies and at DIFFERENT words, so
    # nothing matches line-to-line and only the block-level sequence sees it. Every false
    # negative adjudicated in this project has been of this kind.
    case("red, VARIANT: a duplicated fragment split across a list-item line break",
         "- **The rubric ceiling.** Tier 1 returned 1.0 on all 24 submissions and on all 16\n"
         "  of the audio run, 40 of 56 matrix trials at the ceiling with zero\n"
         "  variance, not merely near it. What to do about it was decided later.\n"
         "  The remedy is harder criteria, not a weight. 40 of 56 matrix trials at\n"
         "  the ceiling with zero variance, not merely near it, and it became a gate.\n", True)

    case("green, the same window in two different paragraphs",
         "A control shares the assumptions of the thing it controls unless you make it not,\n"
         "which is the failure this rule exists to prevent.\n\n"
         "A control shares the assumptions of the thing it controls unless you make it not,\n"
         "which is the failure this rule exists to prevent.\n", False)
    case("green, the same window in two top-level list items",
         "- the judge reads the pack and scores the field on every criterion it was given\n"
         "- the judge reads the pack and scores the field on every criterion it was given\n",
         False)
    case("green, a duplicated window inside a fence",
         "Sample output:\n\n```\nrun the harness with the stored manifest and read the exit "
         "status unpiped\nrun the harness with the stored manifest and read the exit status "
         "unpiped\n```\n", False)
    case("green, two table rows repeating a long stem",
         "| what | why |\n|---|---|\n"
         "| the manifest of what the run dropped and why it dropped it, per file | kept |\n"
         "| the manifest of what the run dropped and why it dropped it, per file | kept |\n",
         False)
    # The archive's one shape at window 12 before frontmatter keys were separated. This is
    # what `tasks/42` looks like, and it is the queue working as designed.
    case("green, a task file restating done_when in established_by",
         "---\nestablished_by: 'the block now states that every judge round stored before "
         "the re-pack read a field that no longer exists, and it does'\nid: 42\n"
         "done_when: the block states that every judge round stored before the re-pack read "
         "a field that no longer exists\n---\n\nSome prose.\n", False)
    # ...and the half of that rule which is NOT bought by masking the header outright.
    case("red, a fragment duplicated inside ONE frontmatter value",
         "---\nid: 7\nestablished_by: 'the sweep reads the stored manifest and compares it "
         "with what the run wrote, so a truncated upload is visible; the sweep reads the "
         "stored manifest and compares it with what the run wrote'\n---\n\nProse.\n", True)

    # The same file at HEAD, repaired. The corpus-wide 0 is not restated here: `cmd_sweep`
    # runs this check over every reference doc and reports what it finds, so a second pass
    # would report the same hit twice and cost the I/O again.
    head = os.path.join(ROOT, "DECISIONS.md")
    if os.path.exists(head):
        case("green, the same file at HEAD with the half-applied rewrite removed",
             open(head, encoding="utf-8", errors="replace").read(), False, "DECISIONS.md")

    # NON-REDUNDANCY, measured on the OTHER check's real instance. Two integrity checks that
    # a reader describes with the same sentence - "an edit left debris behind" - is exactly
    # the shape that invites merging them into one parameterised rule, and the merge would
    # lose an instance: the stranded tail at 1f6fb65:eval/FINDINGS.md:6 repeats a run of only
    # 6 words, so no window this side of the false-positive floor reaches it, while the
    # stranded-tail rule scores 0 on the fragment defect. Neither subsumes the other.
    #
    # This row is not a claim that catching both would be WRONG. It is a claim that the
    # decision to run two checks rests on a number, and that the number should be re-derived
    # rather than assumed if it ever moves.
    orphan_blob = _git("show", "1f6fb65:eval/FINDINGS.md")
    if orphan_blob.strip():
        cross = _check_duplicate_fragment(orphan_blob, "eval/FINDINGS.md")
        if cross:
            out.append(
                f"the duplicate-fragment check now finds {len(cross)} hit(s) in "
                f"1f6fb65:eval/FINDINGS.md, the stranded-tail check's own instance, which "
                f"measured 0 at window {_DUP_FRAGMENT_WINDOW} (that orphan repeats 6 words). "
                f"That is not a defect - it means the two integrity checks are no longer "
                f"independent, and DECISIONS.md's reason for running both needs re-deriving: "
                f"{cross[:1]}")
        elif verbose:
            print(f"PASS  non-redundant, 1f6fb65:eval/FINDINGS.md (the stranded-tail "
                  f"instance, a 6-word repeat): 0 hit(s) at window {_DUP_FRAGMENT_WINDOW}")
    return out


# A row of the "Every finding" index in eval/FINDINGS.md, and the GFM delimiter row that
# has to sit above the first of them for any of it to be a table.
_INDEX_ROW_RX = re.compile(r"^\| \*\*(\d+)\*\*")
_TABLE_DELIM_RX = re.compile(r"^\|[\s:|-]+\|\s*$")


def _index_rows(itext: str) -> list[tuple[int, int]]:
    """(1-based line number, finding number) for every index row, fences excluded."""
    lines = itext.split("\n")
    fenced = _fence_mask(lines)
    out = []
    for i, ln in enumerate(lines):
        if fenced[i]:
            continue
        m = _INDEX_ROW_RX.match(ln)
        if m:
            out.append((i + 1, int(m.group(1))))
    return out


def _check_index_renders_as_one_table(itext: str) -> list[str]:
    """The FINDINGS.md index must be ONE table, not a run of rows that happens to grep.

    THE DEFECT THIS EXISTS FOR, and why every other check here was blind to it.

    On 2026-08-23 a blank line sat between the row for #105 and the row for #106. Under
    CommonMark that ENDS the table: #19-#105 were one table and #106-#111 a second one
    with no header row. Every renderer, every chunker and every markdown parser saw two
    tables; the index a reader is shown stopped six findings short of the end.

    Nothing caught it, and the reason generalises. A row-count check counts 100 rows either
    way. The body-vs-index reconciliation above resolves every number either way. `grep`
    finds every row either way. **A structural break is invisible to every check that reads
    the file as a set of lines**, which is exactly how this one arrived and survived.

    So this reads the file as a PARSER does. Two conditions, both of which the split
    violated and neither of which any other check states:

      1. the rows are contiguous - nothing between the first and the last that is not
         itself a row, because a blank line, a heading or a paragraph in there starts a
         second, headerless table;
      2. a delimiter row (`|---|---|---|`) sits immediately above the first row, because
         without one the whole block is a paragraph of pipes rather than a table at all.

    Pinned in both directions by `_index_pins()`, which `cmd_sweep` runs every time and
    `--selftest` prints: red on a planted blank line, a whitespace-only line, a prose line,
    a deleted delimiter and a duplicated row; green on the committed index, on a blank line
    after the LAST row (where the table legally ends) and on a row inside a ``` fence.
    """
    rows = _index_rows(itext)
    if not rows:
        # An index with no rows at all is already reported by the body-vs-index
        # reconciliation in the caller, as one problem per unindexed finding. Saying it
        # again here would bury that under a second phrasing of the same fact.
        return []

    lines = itext.split("\n")
    problems: list[str] = []
    rownum = dict(rows)                 # line number -> finding number
    first, last = rows[0][0], rows[-1][0]

    # (1) contiguity. Consecutive interrupting lines are collapsed into ONE report: a
    # three-line paragraph dropped into the table is one break, not three.
    gaps = [ln for ln in range(first, last + 1) if ln not in rownum]
    run_start = None
    for ln in gaps + [None]:
        if run_start is None:
            run_start, prev_ln = ln, ln
            continue
        if ln == prev_ln + 1:
            prev_ln = ln
            continue
        # By line position, not by value: the neighbouring ROWS are what the break
        # separates, whether or not the index happens to be in numeric order.
        above = rownum[max(n for n in rownum if n < run_start)]
        below = rownum[min(n for n in rownum if n > prev_ln)]
        where = (f"line {run_start}" if run_start == prev_ln
                 else f"lines {run_start}-{prev_ln}")
        what = ("a blank line" if not lines[run_start - 1].strip()
                else f"`{lines[run_start - 1].strip()[:40]}`")
        problems.append(
            f"eval/FINDINGS.md {where}: {what} interrupts the finding index between the "
            f"rows for #{above} and #{below}. Under CommonMark that ENDS the table - "
            f"#{below} onward become a SECOND table with no header, so every renderer and "
            f"chunker shows an index that stops at #{above}. grep sees no difference, "
            f"which is why this went unnoticed once already.")
        run_start, prev_ln = ln, ln

    # (2) the header delimiter. Rows with no `|---|` line above them are not a table.
    above_line = lines[first - 2] if first >= 2 else ""
    if not _TABLE_DELIM_RX.match(above_line.strip()):
        problems.append(
            f"eval/FINDINGS.md line {first}: the first index row (#{rownum[first]}) has no "
            f"table delimiter row above it (found `{above_line.strip()[:40]}`). Without a "
            f"`|---|---|---|` line the index is not a table at all - it renders as a "
            f"paragraph of pipe characters.")
    return problems


def _index_row_count() -> int:
    """Rows in the FINDINGS.md index, for the sweep to REPORT rather than merely assert.

    A gate that prints only "clean" cannot be distinguished from one reading an empty
    corpus. Printing the count is how a reader notices the day it says 0.
    """
    p = os.path.join(ROOT, "eval", "FINDINGS.md")
    if not os.path.exists(p):
        return 0
    return len(_index_rows(open(p, encoding="utf-8", errors="replace").read()))


def _check_index(itext: str, body: set[int]) -> list[str]:
    """Everything the FINDINGS.md index must satisfy, as a function of TEXT and body numbers.

    A FUNCTION OF ITS INPUTS, not of the repository, so that `--selftest` can hand it a
    mutated copy of the index in memory. The alternative — planting a defect in the real
    `eval/FINDINGS.md` and restoring it afterwards — writes to the ARCHIVE to test a gate,
    and leaves it broken if the run dies in between. Nothing here opens a file.
    """
    problems: list[str] = []
    rows = _index_rows(itext)

    # THE SET RECONCILIATION IS NOT HERE ANY MORE, and its move is the only reason to trust
    # either half. `findings_census` needs the same two set differences to produce a count,
    # so for one afternoon this repository had two implementations of "is the index the same
    # set as the bodies" - one gating, one producing. `findings_control.py --mutate
    # no_count_check` deleted one of them and all ten controls still passed. A duplicated
    # mechanism buys you half a gate and no way to tell which half you removed.
    #
    # What stays here is what a SET cannot express: a number indexed TWICE. A set collapses
    # it, both differences come back empty, both rows resolve, and only counting sees it -
    # and the line numbers are what a person needs in order to delete the right row.
    counts = collections.Counter(n for _, n in rows)
    for n in sorted(n for n, c in counts.items() if c > 1):
        at = ", ".join(str(ln) for ln, x in rows if x == n)
        problems.append(f"eval/FINDINGS.md indexes #{n} on more than one row (lines {at}) "
                        f"- the index has {len(rows)} rows for {len(body)} findings, and a "
                        f"reader following the first row may land on a different entry "
                        f"than one following the second")

    # The stated range is not checked here either, for the same reason and an older one: it
    # used to be, for eval/FINDINGS.md alone, which is how AGENTS.md and README.md carried
    # `#19-#110` for a day after the index was repaired. `findings_census` asks it of all
    # three live statements at once, with line numbers.
    return problems + _check_index_renders_as_one_table(itext)


# "Findings #19-#118" - the sentence that tells a reader where the log ends.
_RANGE_RX = re.compile(r"Findings #(\d+)-#(\d+)")

# The files that state that range and are read as CURRENT. Both defects in task 59 were
# drift, and drift returns: the range was spelled in THREE files and only one of them was
# ever checked, so `eval/FINDINGS.md` was repaired while `AGENTS.md` went on saying #110.
# AGENTS.md rule 12 - when a value is spelled in two files, assert them equal in code; a
# comment promising they match is not a defence.
#
# `tasks/`, `eval/findings/` and `CLEANUP-LOG.md` are deliberately NOT here. They quote
# historical states on purpose - task 59's own body quotes "#19-#110" as the evidence for
# the defect - and gating them would fail on correct input, which is how a gate gets
# switched off. These three carry the opposite rule: `README.md` and `AGENTS.md` state what
# is true now and replace superseded content rather than annotating it, so a range in them
# that is not current is a defect by their own standard.
RANGE_DOCS = ("AGENTS.md", "README.md", os.path.join("eval", "FINDINGS.md"))


def _check_range_in(rel: str, text: str, highest: int) -> list[str]:
    """One document's statement of the findings range, as a function of its TEXT.

    Pure, for the same reason `_check_index` is: the pins feed it a mutated copy rather
    than editing a live instruction document to prove a gate works.
    """
    problems = []
    lines = text.split("\n")
    fenced = _fence_mask(lines)
    found = False
    for i, ln in enumerate(lines):
        if fenced[i]:
            continue
        m = _RANGE_RX.search(ln)
        if not m:
            continue
        found = True
        if int(m.group(2)) != highest:
            problems.append(
                f"{rel}:{i + 1} says the findings log covers #{m.group(1)}-#{m.group(2)}, "
                f"but the highest finding in eval/findings/ is #{highest}. This sentence "
                f"is what a session is told to trust to know where the log ends, and an "
                f"undercount invites the next agent to reuse a number already taken.")
    if not found:
        problems.append(
            f"{rel} no longer states the findings range at all (`Findings #A-#B`). Either "
            f"the sentence was dropped - a reader has no way to tell where the log ends - "
            f"or its wording changed and this check is now reading nothing.")
    return problems


#: A finding's body heading. Two styles are in the archive and both are live:
#: `## #19 - the failure mode ...` and `## 26. The judge's only measured signal ...`.
_BODY_HEADING_RX = re.compile(r"^##\s+#?(\d+)[.\s]")


def _body_findings(fdir: str) -> dict[int, list[str]]:
    """{finding number: [file, ...]} for every `## #NN` heading in `fdir`/*.md.

    Fence-aware for the reason in this module's docstring: a GDScript doc-comment inside a
    ``` block starts with `##` and once read as a malformed finding heading.

    One extractor, two readers -- `_check_findings_integrity` (the gate) and
    `findings_census` (the producer). They were written apart and would have drifted apart;
    a count and the gate over it disagreeing about what a finding IS is the failure the
    producer exists to prevent.
    """
    seen: dict[int, list[str]] = collections.defaultdict(list)
    for p in sorted(glob.glob(os.path.join(fdir, "*.md"))):
        lines = open(p, encoding="utf-8", errors="replace").read().split("\n")
        fenced = _fence_mask(lines)
        for i, ln in enumerate(lines):
            if fenced[i]:
                continue
            m = _BODY_HEADING_RX.match(ln)
            if m:
                seen[int(m.group(1))].append(os.path.basename(p))
    return dict(seen)


def _check_findings_integrity() -> list[str]:
    """A finding number must identify exactly one finding, and be reachable from the index.

    WHY THIS IS MECHANICAL AND NOT A CONVENTION
    -------------------------------------------
    Findings are numbered by hand in markdown. Under one-agent-per-task, agents work in
    isolated worktrees and each reads the highest number from ITS OWN branch, which was
    forked before the previous merge landed. On 2026-08-23 that produced SIX collisions in
    one day: #89, #90, #91, #95 and #99 were each allocated twice, by agents that had no way
    to see each other.

    Every one was caught by a person reading a merge diff. That is not a mechanism, and it
    is the same lesson as #94: renumbering at merge time treats a structural problem as a
    clerical one, so it recurs on the next parallel run.

    A duplicate is worse than a missing finding. Both numbers look valid, every citation to
    them resolves to two different pieces of work, and nothing downstream can tell which one
    an author meant.

    Five questions, all cheap:
      1. does any number appear twice in the bodies?
      2. is every body finding present in the FINDINGS.md index, and vice versa?
      3. does every LIVE statement of the range - three files - match the highest number?
      4. does the index still render as ONE table?
      5. does every LIVE statement of the COUNT match how many there are?

    (3) matters because that sentence is what a reader trusts to know where the log ends,
    and it is edited by hand in three files. It has been wrong before, in two of the three:
    `eval/FINDINGS.md` was repaired and `AGENTS.md` went on saying `#19-#110`, because only
    the first was ever checked.

    (4) is the one the other three cannot see. 1-3 read the index as a SET of numbers, and a
    set is identical whether or not a blank line has split the rows into two tables — see
    `_check_index_renders_as_one_table` for the split that stood undetected.

    (5) is the one 1-4 cannot see either, and for the same kind of reason: they are all
    about the RANGE, and a range is not a count. `#19-#131` is equally true of 113 findings
    and of 40. `findings_census` asks it, and `--findings` prints what it counted.

    THE GATE AND THE PRODUCER ARE ONE FUNCTION. Questions 1, 2, 3 and 5 are exactly
    `findings_census(...)["disagreements"]`; this wrapper adds only what the census does not
    express - the index's structure (4) and which LINES an over-indexed number sits on. The
    first draft implemented 1, 2 and 3 here and again in the census, and
    `findings_control.py --mutate no_count_check` proved what that costs: it deleted one
    copy and all ten controls stayed green.
    """
    try:
        c = read_findings_census()
    except FileNotFoundError as exc:
        return [f"{exc} - this check ran over nothing"]

    problems = list(c["disagreements"])
    index_path = os.path.join(ROOT, "eval", "FINDINGS.md")
    itext = open(index_path, encoding="utf-8", errors="replace").read()
    return problems + _check_index(itext, set(_body_findings(
        os.path.join(ROOT, "eval", "findings"))))


# --------------------------------------------------------------- the findings producer
#
# WHY A COUNT OF THE FINDINGS LOG NEEDS A PRODUCER AT ALL
# -------------------------------------------------------
# `README.md` opened its "one thing this project actually learned" section with "Thirty-seven
# numbered findings" from 2026-08-12 until 2026-08-23, while the log ran to #131. Nothing in
# the repository produced that 37, so nothing could disagree with it -- the exact shape
# AGENTS.md names: a count with a producer goes stale for an hour; a count with none goes
# stale forever.
#
# The range sentence (`Findings #19-#131`) already had a gate, added by task 59. A range is
# not a count: #19-#131 is consistent with any number of findings between 1 and 113, and the
# range gate is green on a log with half its entries missing. This asks the other question.
#
# TWO SOURCES, DELIBERATELY. `eval/findings/*.md` holds the bodies; `eval/FINDINGS.md` holds
# the index rows. Counting one and reporting it as "the findings" is how #127 happened one
# directory over -- a census certified by a cross-check that shared its extractor. Here the
# two are counted independently and their disagreement IS the output.

#: "Thirty-seven numbered findings" -- a cardinal spelled in words. It is not that words are
#: wrong; it is that no check can read one, which is why this particular figure outlived
#: eleven merges. Digits are gated against the producer, words are reported as ungateable.
_COUNT_WORD_RX = re.compile(
    r"\b((?:twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety)(?:-\w+)?|"
    r"one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|"
    r"fifteen|sixteen|seventeen|eighteen|nineteen|hundred)\s+numbered findings\b", re.I)
_COUNT_DIGIT_RX = re.compile(r"\b(\d+)\s+numbered findings\b")

#: A line that IDENTIFIES the findings log, by one of the three addresses this repository
#: defines for it: the range sentence, the path, and the producer command. That is a closed
#: class -- three identifiers, not a vocabulary of English -- which is what
#: `DECISIONS.md`'s census-trigger section asks a trigger to be scoped on.
_LOGREF_RX = re.compile(r"Findings #\d+-#\d+|eval/FINDINGS\.md|docstat\.py --findings")

#: A cardinal governing a plural noun, up to two words away: `180 entries`,
#: `180 numbered findings`, `180 separate numbered entries`. `(?<![#\w.-])` keeps `#19`, a
#: commit prefix and `0.19` out. Alone this is the QUANTIFIER trigger `DECISIONS.md`
#: rejected for the aspect census, and it costs the same here -- see `_stated_counts`.
_CARDINAL_PLURAL_RX = re.compile(
    r"(?<![#\w.-])(\d+)\s+(?:[a-z`*]+\s+){0,2}?([a-z][a-z-]+s)\b")


def _stated_counts(rel: str, text: str, count: int) -> list[str]:
    """One live document's statement of HOW MANY findings there are, as a function of TEXT.

    Pure, like `_check_range_in`, so the pins feed it a mutated copy rather than editing a
    live instruction document to prove the gate works.

    TWO TRIGGERS, AND THE SECOND IS WHY THIS DOCSTRING IS LONG. The first reads the exact
    phrase `N numbered findings`. That is an enumeration of one wording, and it failed the
    way an enumeration fails: `README.md` line 187 read `143 entries. Findings #19-#189,
    count and range from python3 eval/tools/docstat.py --findings` against a measured 171,
    and this function was green on it while reddening a count in the SAME FILE that happened
    to be phrased the gated way (task 179).

    The second trigger is scoped on the closed class `_LOGREF_RX` -- a line that names the
    findings log by its range sentence, its path or its producer -- and reads any cardinal
    governing a plural noun on that line as a statement of the count. The quantifier half is
    the shape `DECISIONS.md` rejected for the aspect census, and unscoped it is just as bad
    here: over the live corpus plus RANGE_DOCS, a cardinal governing `findings|entries`
    turns 6 correct lines red and the fuller quantifier form 12, every one a false positive
    -- lint findings, Bevy migration entries, and DECISIONS.md's own worked example of why a
    range is not a count. Conjoined with the address it is 2 matches and 0 red.

    A count on a line that names the log and is NOT the findings count therefore reds, and
    the repair is the one the aspect census already declares: put the example in a ``` fence,
    where a line is an example rather than a claim.

    The word form is reported rather than tolerated, and stays on the `numbered findings`
    phrasing alone. Scoping the word form the same way costs 2 false positives on the live
    corpus (`eight ... lines`, `eleven ... days`), so a count spelled in words in any other
    phrasing is still invisible -- which is why AGENTS.md tells you to write it in digits.
    """
    problems = []
    lines = text.split("\n")
    fenced = _fence_mask(lines)
    for i, ln in enumerate(lines):
        if fenced[i]:
            continue
        seen: set[int] = set()
        for m in _COUNT_DIGIT_RX.finditer(ln):
            seen.add(m.start())
            if int(m.group(1)) != count:
                problems.append(
                    f"{rel}:{i + 1} says there are {m.group(1)} numbered findings; "
                    f"eval/findings/ holds {count}. Produce it with "
                    f"`python3 eval/tools/docstat.py --findings` rather than editing the "
                    f"digit, and check the range sentence in the same pass.")
        if _LOGREF_RX.search(ln):
            for m in _CARDINAL_PLURAL_RX.finditer(ln):
                if m.start() in seen or int(m.group(1)) == count:
                    continue
                problems.append(
                    f"{rel}:{i + 1} names the findings log and states `{m.group(0)}`; "
                    f"eval/findings/ holds {count}. Produce it with "
                    f"`python3 eval/tools/docstat.py --findings` rather than editing the "
                    f"digit. If that number is not the findings count, put the line in a "
                    f"``` fence or reword it - a count beside the log's own address reads "
                    f"as derived, which is what made `143 entries` survive (task 179).")
        m = _COUNT_WORD_RX.search(ln)
        if m:
            problems.append(
                f"{rel}:{i + 1} states a findings count in words (`{m.group(1)}`). No check "
                f"can compare a cardinal it cannot parse, which is why `Thirty-seven` "
                f"survived to #131. Write it in digits, beside its producer.")
    return problems


def _count_corpus(stated: dict[str, str] | None = None) -> tuple[dict[str, str], list[str]]:
    """({relpath: text}, problems) for every document a findings COUNT is reconciled in.

    ONE SPELLING OF THE COUNT CORPUS, because two readers ask about it - the gate and
    `--count-triggers` - and a population spelled twice has two answers (rule 12). It is the
    live corpus plus `RANGE_DOCS`: `AGENTS.md` and `README.md` are already live, so the union
    adds exactly `eval/FINDINGS.md`, which is archive and still states the figure.

    Wider than the RANGE corpus, deliberately and at a measured cost of 0 red lines. Until
    task 179 the count was reconciled in `RANGE_DOCS` alone, so a stale figure in any other
    live document - a skill, `eval/PROTOCOL.md`, the CI register - was unreachable by a gate
    that reported itself clean. `_live_corpus` RAISES rather than returning an empty tree, so
    a failed listing stops the caller instead of shrinking the corpus to 3 and reading clean.
    """
    if stated is None:
        stated = {rel: open(os.path.join(ROOT, rel), encoding="utf-8",
                            errors="replace").read()
                  for rel in RANGE_DOCS if os.path.exists(os.path.join(ROOT, rel))}
    live, problems = _live_corpus()
    return {**live, **stated}, problems


#: The candidate digit triggers task 179 chose between, kept so the choice can be RE-DERIVED
#: rather than believed. The rejected two are the shape `DECISIONS.md`'s census-trigger
#: section rejected for the aspect census, and they are here for the same reason the window
#: sweep keeps its rejected window sizes: an open-class trigger's cost GROWS with the corpus,
#: so a number measured once is a number about a tree that no longer exists.
#:
#: Each is `(label, regex, needs the log's address on the line)`. The shipped row is the two
#: `_stated_counts` actually runs, and it must stay at 0.
_COUNT_TRIGGER_CANDIDATES = (
    ("`N numbered findings` alone - the enumeration that shipped until task 179",
     _COUNT_DIGIT_RX, False),
    ("the same list plus one noun - `N (numbered )?(findings|entries)`",
     re.compile(r"\b(\d+)\s+(?:numbered\s+)?(?:findings|entries)\b"), False),
    ("the QUANTIFIER - a cardinal governing findings|entries, up to two words away",
     re.compile(r"(?<![#\w.-])(\d+)\s+(?:[\w`*-]+\s+){0,2}?(?:findings|entries)\b"), False),
    ("SHIPPED - a cardinal governing a plural noun on a line naming the log",
     _CARDINAL_PLURAL_RX, True),
)


def count_trigger_census(corpus: dict[str, str], count: int) -> list[dict]:
    """How many lines each candidate digit trigger would turn RED, over `corpus`.

    THE PRODUCER for the candidate table in `DECISIONS.md`, *the findings count is read from
    the log's ADDRESS*. A trigger chosen on a false-positive count is a claim about a corpus,
    and the corpus grows: the aspect census's quantifier trigger cost 26 correct lines when it
    was measured and 31 four weeks later. A number nothing re-derives cannot notice that.

    A function of its inputs, so `--selftest` can hand it text rather than the repository.
    """
    out = []
    for label, rx, scoped in _COUNT_TRIGGER_CANDIDATES:
        rows = []
        for rel, text in sorted(corpus.items()):
            lines = text.split("\n")
            fenced = _fence_mask(lines)
            for i, ln in enumerate(lines):
                if fenced[i] or (scoped and not _LOGREF_RX.search(ln)):
                    continue
                for m in rx.finditer(ln):
                    if int(m.group(1)) != count:
                        rows.append({"doc": rel, "line": i + 1, "says": int(m.group(1)),
                                     "text": m.group(0)})
        out.append({"trigger": label, "red": len(rows), "rows": rows})
    return out


def _count_trigger_pins(verbose: bool = False) -> list[str]:
    """Pin `count_trigger_census` in both directions, on text built in memory.

    WHY A PRODUCER THAT GATES NOTHING NEEDS PINS. Its output is a table `DECISIONS.md`
    quotes, and every row of it is a number someone will act on. An extractor that has
    silently stopped matching returns `red 0` for every candidate - which is also what a
    corpus with nothing wrong returns, and which would read as *the rejected triggers are
    fine after all*. That is the ambiguity this repository keeps paying for.

    Each case asserts an EXACT red count per candidate, never `bool(rows)`, because the
    whole claim of the table is the SIZE of the difference between the candidates.
    """
    count = 180
    cases = [
        ("the real defect: a count short in the `entries` wording, beside the producer",
         {"README.md": "[`eval/FINDINGS.md`](eval/FINDINGS.md) - 143 entries. Findings "
                       "#19-#198, from `python3 eval/tools/docstat.py --findings`\n"},
         # the enumeration misses it; `entries` alone and the quantifier catch it because
         # the noun is on their list; the shipped trigger catches it via the address
         [0, 1, 1, 1]),
        ("a real live false positive: untriaged lint findings, naming no log",
         {".github/workflows/README.md": "| the full `lint.py` rule set | 72 findings "
                                         "stand untriaged (`lint.py --counts`) |\n"},
         [0, 1, 1, 0]),
        ("a count short in the gated wording, on a line naming nothing",
         {"README.md": "143 numbered findings, and all but a few are one pattern.\n"},
         [1, 1, 1, 0]),
        ("GREEN: the count stated correctly in every wording",
         {"README.md": f"{count} numbered findings.\n",
          "AGENTS.md": f"`eval/FINDINGS.md` - {count} entries.\n"}, [0, 0, 0, 0]),
        ("GREEN: a stale count beside the log inside a ``` fence",
         {"README.md": "```\n143 entries. Findings #19-#198\n```\n"}, [0, 0, 0, 0]),
        ("GREEN: an empty corpus - and every row reads 0, which is why the rows above "
         "assert exact counts rather than `some`", {}, [0, 0, 0, 0]),
    ]
    failed = []
    for name, corpus, want in cases:
        got = [r["red"] for r in count_trigger_census(corpus, count)]
        ok = got == want
        if not ok:
            failed.append(
                f"count-trigger pin came out wrong: `{name}` measured {got} red where "
                f"{want} was expected, one per candidate in _COUNT_TRIGGER_CANDIDATES. "
                f"The candidate table in DECISIONS.md is produced by this function, so a "
                f"drift here is a drift in a published measurement.")
        if verbose:
            print(f"{'PASS' if ok else 'FAIL'}  {name}: red {got}, expected {want}")
    return failed


def cmd_count_triggers(as_json: bool = False) -> int:
    """`--count-triggers`: what each candidate would cost over today's corpus. Never gates.

    Exit 0 whatever it finds, like `--citations`: the SHIPPED row going above 0 is a fact
    `--findings` already gates on, and the rejected rows are expected to be non-zero. This
    prints the cost so a reader can see whether it has moved.
    """
    try:
        count = read_findings_census()["bodies"]["count"]
        corpus, problems = _count_corpus()
    except (FileNotFoundError, RuntimeError) as exc:
        print(f"docstat --count-triggers: {exc}", file=sys.stderr)
        return 2
    rows = count_trigger_census(corpus, count)
    if as_json:
        print(json.dumps({"documents": len(corpus), "count": count, "candidates": rows,
                          "corpus_problems": problems}, indent=2))
        return 0
    for p in problems:
        print(f"  corpus: {p}")
    print(f"{len(corpus)} document(s) - the live corpus, which already contains AGENTS.md "
          f"and README.md, plus eval/FINDINGS.md, which is archive")
    print(f"the measured count is {count} (--findings)\n")
    for r in rows:
        print(f"  red {r['red']:>3}  {r['trigger']}")
        for row in r["rows"]:
            print(f"           {row['doc']}:{row['line']} `{row['text']}`")
    print("\nred = correct lines a candidate would turn red today. Every non-zero row here "
          "has been\nadjudicated a false positive; see DECISIONS.md, the findings-count "
          "entry.")
    return 0


def findings_census(bodies: dict[int, list[str]], index_text: str,
                    stated: dict[str, str], corpus_files: list[str] | None = None,
                    counted: dict[str, str] | None = None) -> dict:
    """How many numbered findings exist, from both sources, and where the two disagree.

    A FUNCTION OF ITS INPUTS, for the same reason `_check_index` is: the pins hand it a
    mutated copy in memory, so proving that the producer notices an added or renumbered
    finding never writes to the archive.

    `bodies` is `{number: [file, ...]}` from `eval/findings/`; `index_text` is
    `eval/FINDINGS.md`. Every disagreement is a string, and the caller's exit code is
    `bool(disagreements)`.

    TWO DOCUMENT CORPORA, because the two questions have different populations. `stated` is
    `RANGE_DOCS` -- the three documents required to carry the range sentence, where a
    document that does NOT state it is itself a defect. `counted` is every document that may
    state how many findings there are: `stated` plus the whole live corpus, where saying
    nothing is the normal case. Defaults to `stated` so a caller asking only about the three
    range documents keeps the older behaviour.
    """
    counted = stated if counted is None else counted
    rows = _index_rows(index_text)
    indexed = collections.Counter(n for _, n in rows)
    with_findings = {f for fs in bodies.values() for f in fs}
    numbers = sorted(bodies)
    lo, hi = (numbers[0], numbers[-1]) if numbers else (0, 0)
    gaps = [n for n in range(lo, hi + 1) if n not in bodies] if numbers else []
    count = len(bodies)

    disagreements: list[str] = []
    for num in sorted(n for n, f in bodies.items() if len(f) > 1):
        disagreements.append(
            f"finding #{num} is defined {len(bodies[num])} times "
            f"({', '.join(bodies[num])}) - a citation to it resolves to more than one "
            f"piece of work, and the count is ambiguous by exactly that much. Renumber "
            f"the later one; see #94 for why this keeps happening.")
    if len(rows) != count:
        disagreements.append(
            f"eval/findings/ holds {count} finding bodies and eval/FINDINGS.md indexes "
            f"{len(rows)} rows. The two sources of the count disagree by "
            f"{abs(len(rows) - count)}.")
    for num in sorted(set(bodies) - set(indexed)):
        disagreements.append(f"#{num} has a body and no index row - uncountable to a "
                             f"reader of eval/FINDINGS.md")
    for num in sorted(set(indexed) - set(bodies)):
        disagreements.append(f"#{num} has an index row and no body - counted by the index "
                             f"and by nothing else")
    if gaps:
        disagreements.append(
            f"the numbering has {len(gaps)} gap(s) - #{', #'.join(map(str, gaps))} - so "
            f"the count ({count}) is not the range width ({hi - lo + 1}), and any document "
            f"deriving one from the other is wrong")

    for rel, text in sorted(counted.items()):
        disagreements += _stated_counts(rel, text, count)

    occurrences = {rel: _range_occurrences(text) for rel, text in sorted(stated.items())}
    for rel, text in sorted(stated.items()):
        disagreements += _check_range_in(rel, text, hi) if numbers else []
        if len(occurrences[rel]) > 1:
            at = ", ".join(str(o["line"]) for o in occurrences[rel])
            disagreements.append(
                f"{rel} states the findings range on {len(occurrences[rel])} lines "
                f"({at}). `_check_range_in` validates each one, so N correct copies are N "
                f"passes and a merge can duplicate the sentence in silence - which is what "
                f"8fef835 did here, in this file and in the other one, on the same day. "
                f"One statement per live document; delete the copy.")

    return {
        "bodies": {
            "population": "`## #NN` headings in eval/findings/*.md, outside ``` fences",
            "count": count,
            "lowest": lo,
            "highest": hi,
            "files": len(with_findings),
            "files_in_dir": len(corpus_files) if corpus_files is not None else None,
            # A file that defines no finding is either prose (`early-single-stack.md`, the
            # pre-numbering phase) or a heading style this extractor stopped matching. The
            # two look identical in a count, so the names are printed and a reader decides.
            "files_without_findings": sorted(set(corpus_files or []) - with_findings),
            "gaps": gaps,
        },
        "index": {
            "population": "`| **NN** |` rows in the eval/FINDINGS.md index, outside fences",
            "rows": len(rows),
            "distinct": len(indexed),
        },
        "stated": occurrences,
        "counted": {
            "population": "unfenced lines of the live corpus and RANGE_DOCS that state a "
                          "findings count, by `N numbered findings` or by a cardinal on a "
                          "line naming the log's range, path or producer",
            "documents": len(counted),
        },
        "disagreements": disagreements,
    }


def _range_occurrences(text: str) -> list[dict]:
    """Every unfenced `Findings #A-#B` in one document, with its line number.

    Reported rather than merely checked, because two copies of the sentence in ONE file are
    invisible to `_check_range_in`: it validates every occurrence it finds, so N identical
    correct copies are N passes. An evil merge (8fef835, 2026-08-23) duplicated the row in
    both `AGENTS.md` and `README.md` and `--sweep` stayed green on it for a day.
    """
    out = []
    lines = text.split("\n")
    fenced = _fence_mask(lines)
    for i, ln in enumerate(lines):
        if fenced[i]:
            continue
        m = _RANGE_RX.search(ln)
        if m:
            out.append({"line": i + 1, "lo": int(m.group(1)), "hi": int(m.group(2))})
    return out


def read_findings_census() -> dict:
    """`findings_census` over the real repository. Raises FileNotFoundError, never returns 0.

    Refusing beats reporting zero for the reason `census.py` refuses: an empty tree and an
    unreadable one produce the same number, and that number is in range.
    """
    fdir = os.path.join(ROOT, "eval", "findings")
    index_path = os.path.join(ROOT, "eval", "FINDINGS.md")
    if not os.path.isdir(fdir):
        raise FileNotFoundError(f"no findings directory at {fdir} - refusing to report a "
                                f"count over nothing")
    bodies = _body_findings(fdir)
    if not bodies:
        raise FileNotFoundError(
            f"{fdir} holds no `## #NN` headings - the heading pattern has changed and this "
            f"would report 0 findings over a full directory")
    if not os.path.exists(index_path):
        raise FileNotFoundError(f"no index at {index_path}")
    stated, absent = {}, []
    for rel in RANGE_DOCS:
        p = os.path.join(ROOT, rel)
        # A document named as a place the figure is stated, and absent, must be REPORTED.
        # Skipping it silently is the fail-open shape: the corpus quietly shrinks by one and
        # the census goes on agreeing with itself (rule 7, and #60 - the address is an input
        # to the check).
        if os.path.exists(p):
            stated[rel] = open(p, encoding="utf-8", errors="replace").read()
        else:
            absent.append(f"{rel} is named in RANGE_DOCS as a place the findings count and "
                          f"range are stated, and it does not exist at {p} - the census "
                          f"covered one document fewer than it claims to")
    counted, live_problems = _count_corpus(stated)
    c = findings_census(
        bodies, open(index_path, encoding="utf-8", errors="replace").read(), stated,
        corpus_files=[os.path.basename(p)
                      for p in sorted(glob.glob(os.path.join(fdir, "*.md")))],
        counted=counted)
    c["disagreements"] = absent + live_problems + c["disagreements"]
    c["read_on"] = _dt.date.today().isoformat()
    c["findings_dir"] = fdir
    c["index_path"] = index_path
    return c


def _findings_summary() -> str:
    """The count and range, PRINTED by a clean sweep rather than merely asserted.

    A gate that prints only "clean" is indistinguishable from one reading an empty corpus,
    which is why `_index_row_count` prints its number too. This is the same move for the
    quantity the documents actually quote.
    """
    try:
        c = read_findings_census()
    except FileNotFoundError:
        return "findings count: NOT READ"
    b = c["bodies"]
    return (f"{b['count']} findings #{b['lowest']}-#{b['highest']} agreeing with "
            f"{c['index']['rows']} index rows, with the range in {len(c['stated'])} "
            f"document(s) and with every count stated across {c['counted']['documents']} "
            f"(--findings)")


def cmd_findings(as_json: bool = False) -> int:
    """`--findings`: the producer for any count of the findings log. Exit 1 on disagreement.

    Quote it beside the command, as AGENTS.md requires of every count -- and quote the
    POPULATION with it, because "113 findings" and "113 index rows" are different claims
    that happen to be equal today.
    """
    try:
        c = read_findings_census()
    except (FileNotFoundError, RuntimeError) as exc:
        # RuntimeError is `_tracked_md` refusing a failed git listing. It exits 2 with the
        # refusals rather than 1, because 1 means "the sources disagree" - a broken address
        # reported as a disagreement is the fail-open shape one step later (#60).
        print(f"docstat --findings: {exc}", file=sys.stderr)
        return 2
    if as_json:
        print(json.dumps(c, indent=2))
    else:
        b, ix = c["bodies"], c["index"]
        print(f"read on {c['read_on']}")
        print(f"  bodies   {b['count']} findings, #{b['lowest']}-#{b['highest']}, "
              f"{len(b['gaps'])} gap(s), across {b['files']} of "
              f"{b['files_in_dir']} file(s)")
        print(f"           {b['population']}")
        print(f"           {c['findings_dir']}")
        if b["files_without_findings"]:
            print(f"           defines none: {', '.join(b['files_without_findings'])} "
                  f"- prose, or a heading style this no longer matches")
        print(f"  index    {ix['rows']} rows, {ix['distinct']} distinct")
        print(f"           {ix['population']}")
        print(f"           {c['index_path']}")
        for rel, occ in c["stated"].items():
            where = ", ".join(f"line {o['line']}: #{o['lo']}-#{o['hi']}" for o in occ)
            print(f"  stated   {rel}: {where or 'states no range'}")
        # The count corpus is printed as a NUMBER, for the reason `_index_row_count` prints
        # its own: a gate that only says "clean" reads the same over three documents as
        # over none, and this one silently ran over three until task 179.
        print(f"  counted  {c['counted']['documents']} document(s) reconciled for the "
              f"count itself")
        print(f"           {c['counted']['population']}")
    if c["disagreements"]:
        print(f"\n{len(c['disagreements'])} disagreement(s):")
        for d in c["disagreements"]:
            print(f"  {d}")
        return 1
    print("\nthe two sources agree, and every live document states this count and range.")
    return 0


#: A `#NN` that could be read as a citation of a numbered finding.
#:
#: THE TWO EXCLUSIONS ARE THE WHOLE EXTRACTOR, and each was measured on the live corpus
#: before it shipped rather than reasoned about:
#:
#:   `(?![0-9A-Za-z_])`  `#1a2b3c` is a colour, and a bare `#(\d+)` reads `#1` out of it.
#:   `(?!-(?!#))`        `#68-the-subjective-layer` is a markdown ANCHOR, not a citation of
#:                       #68, while `#19-#152` IS two citations spelling a range. A hyphen
#:                       followed by `#` continues a range; a hyphen followed by anything
#:                       else begins a slug.
#:
#: WHAT THEY ARE WORTH TODAY, measured rather than assumed, and the answer is not what it
#: looks like. Over the live corpus at `24bc9af` the shipped pair and a bare `#(\d+)` return
#: the SAME 51 matches on 45 lines: 20 live lines tokenise differently - 19 in README.md, 1
#: in DECISIONS.md, every one an anchor - but each anchor carries an IN-RANGE number, so the
#: range test was already discarding them. On today's corpus both exclusions are free.
#:
#: THEY ARE ONE UNIT, AND HALF OF THEM IS MUCH WORSE THAN NEITHER. Drop only the word-char
#: exclusion and the count goes to **71 on 65** - `#(\d+)` is greedy, the anchor lookahead
#: rejects `#30` in `#30-a-guard-...`, and the engine BACKTRACKS to `#3`, which is out of
#: range. A regex exclusion is not an independent term you can price on its own, and a
#: reader deleting one because "it changes nothing" would land on the worst of the three.
#:
#: WHAT IT STILL CANNOT SEE, stated here rather than discovered by someone quoting it:
#: a six-digit hex colour written `#123456` is indistinguishable from a citation of finding
#: 123456 by anything short of reading the sentence, and would be counted. There is none in
#: the live corpus today (every hex there carries a letter or sits in a fence).
_CITATION_RX = re.compile(r"#(\d+)(?![0-9A-Za-z_])(?!-(?!#))")


def citation_census(corpus: dict[str, str], lo: int, hi: int) -> dict:
    """Every `#NN` in a live document that names NO finding, because NN is out of range.

    THIS IS A PRODUCER, NOT A GATE, and the distinction is the finding it was built for.
    #146 asked whether the obvious dangling-citation check could be built, measured it, and
    answered no: `#` before a number is a rule number, a task id, a table row, a GitHub
    issue and *"the #1 risk"* as well as a finding citation, so the trigger fires on correct
    input. Nothing here exits 1 on a row. What it fixes is the OTHER half of #146 - the
    census itself was published with no command beside it and does not reproduce.

    A FUNCTION OF ITS INPUTS, like `findings_census` next to it, so the pins can hand it a
    corpus built in memory and the archive is never written to.

    `corpus` is `{relpath: text}` for the LIVE documents; `lo`/`hi` bound the published
    findings range. Rows are per LINE and matches are per TOKEN - **they are different
    numbers** and #146's own correction note conflated them, quoting one run's match count
    beside another run's line count.
    """
    rows, matches = [], 0
    for rel, text in sorted(corpus.items()):
        lines = text.split("\n")
        fenced = _fence_mask(lines)
        for i, ln in enumerate(lines):
            # A `#999` inside a ``` block is an example of a citation, not one: this
            # module's own docstrings quote planted controls, and `--findings` output
            # gets pasted into documents verbatim.
            if fenced[i]:
                continue
            out = [int(m.group(1)) for m in _CITATION_RX.finditer(ln)
                   if not lo <= int(m.group(1)) <= hi]
            if out:
                matches += len(out)
                rows.append({"file": rel, "line": i + 1, "numbers": out,
                             "excerpt": " ".join(ln.split())[:96]})
    areas: dict[str, int] = collections.Counter(
        r["file"].split("/")[0] if "/" in r["file"] else r["file"] for r in rows)
    return {
        "population": "every unfenced `#NN` in the LIVE markdown corpus - git-tracked "
                      "*.md, minus vendored, minus docstat.ARCHIVE_PATHS - whose NN falls "
                      f"outside the published findings range #{lo}-#{hi}",
        "range": {"lowest": lo, "highest": hi},
        "files": len(corpus),
        "matches": matches,
        "lines": len(rows),
        "by_area": dict(sorted(areas.items())),
        "rows": rows,
    }


def read_citation_census() -> dict:
    """`citation_census` over the real repository. Raises rather than reporting 0 over none.

    THE ADDRESS IS AN INPUT (#60). Two things can be aimed wrong here and both return a
    plausible number: the corpus, and the range it is compared against. The corpus comes
    from `_live_corpus`, which reports an empty read instead of returning it as clean; the
    range comes from `read_findings_census`, the same producer `--findings` prints - never
    from a number typed into this file, which would go stale the next time a finding lands.

    IT DELIBERATELY TAKES NO `--at REV`, unlike `--withdrawn` beside it. `_live_corpus`
    would read the corpus at a revision and `read_findings_census` globs a directory on
    disk, so the two halves would come from different trees and the comparison would be
    between a document as it stood then and a range as it stands now. A half-correct
    revision argument is worse than none: its answer is in range and nothing says which
    tree it describes. Quote the reading with the revision you ran it at instead.
    """
    corpus, problems = _live_corpus()
    if problems:
        raise FileNotFoundError("; ".join(problems))
    c = read_findings_census()
    out = citation_census(corpus, c["bodies"]["lowest"], c["bodies"]["highest"])
    out["read_on"] = _dt.date.today().isoformat()
    out["range"]["producer"] = "eval/tools/docstat.py --findings"
    out["corpus_files"] = sorted(corpus)
    return out


def cmd_citations(as_json: bool = False) -> int:
    """`--citations`: the producer for any count of out-of-range `#NN` in live documents.

    Exit 0 on any number of rows and 2 when it could not read a corpus, because a row is
    not a defect: adjudicating one needs a reader, and 43 of 43 rows at dce1172 are
    correct prose. Quote the number beside this command and beside the date, as AGENTS.md
    requires of every count - it moves whenever a finding lands or a document is edited.
    """
    try:
        c = read_citation_census()
    except FileNotFoundError as exc:
        print(f"docstat --citations: {exc}", file=sys.stderr)
        return 2
    if as_json:
        print(json.dumps(c, indent=2))
        return 0
    r = c["range"]
    print(f"read on {c['read_on']}")
    print(f"  population  {c['files']} live markdown document(s)")
    print(f"              {c['population']}")
    print(f"  range       #{r['lowest']}-#{r['highest']} ({r['producer']})")
    print()
    for row in c["rows"]:
        nums = ", ".join(f"#{n}" for n in row["numbers"])
        print(f"  {row['file']}:{row['line']}: {nums}")
        print(f"      {row['excerpt']}")
    print(f"\n{c['matches']} match(es) on {c['lines']} distinct line(s), "
          f"by area: {', '.join(f'{k} {v}' for k, v in c['by_area'].items()) or 'none'}")
    print("These are CANDIDATES, not defects. How many are real dangling citations is a "
          "question\nfor a reader - see FINDINGS #146, which measured the naive check at "
          "18 false positives\nto 2 true and is the reason this exits 0.")
    return 0


ORDINALS = ("first", "second", "third", "fourth", "fifth", "sixth", "seventh", "eighth",
            "ninth", "tenth", "eleventh", "twelfth", "thirteenth", "fourteenth", "fifteenth",
            "sixteenth", "seventeenth", "eighteenth", "nineteenth", "twentieth",
            "twenty-first", "twenty-second", "twenty-third", "twenty-fourth", "twenty-fifth",
            "twenty-sixth", "twenty-seventh", "twenty-eighth", "twenty-ninth", "thirtieth",
            "thirty-first", "thirty-second", "thirty-third", "thirty-fourth", "thirty-fifth",
            "thirty-sixth", "thirty-seventh", "thirty-eighth", "thirty-ninth", "fortieth")

#: The ordinal word a heading uses, whatever it is. Matched GENERICALLY rather than by
#: alternating `ORDINALS`, so a word the list does not carry is reported instead of missed.
_BREAK_HEADING = re.compile(r"\b([A-Za-z][A-Za-z-]*)\s+comparability break", re.I)

#: An ATX heading, INCLUDING the up-to-three leading spaces CommonMark allows. `startswith("#")`
#: was the test until 2026-08-25 and it is a stricter reader than the renderer: ` ## a SEVENTH
#: comparability break` heads a section in every markdown viewer and was invisible here, so an
#: indented duplicate ordinal evaded the collision check entirely. A fourth space makes it an
#: indented code block rather than a heading, which is why the bound is 3 and not `*`.
_ATX_HEADING = re.compile(r"^ {0,3}#{1,6}(?:[ \t]|$)")


def _regime_ordinal_problems(text: str) -> list[str]:
    """A comparability break's ordinal must name exactly one break.

    THE FOURTH IDENTIFIER NAMESPACE TO COLLIDE, and for the same reason as the other three.

    `eval/RUNS.md` numbers regime boundaries in words -- "a SEVENTH comparability break".
    The ordinal is how every other document cites one. On 2026-08-23 two sessions working
    in isolated worktrees each wrote "an ELEVENTH comparability break" on the same day and
    neither could see the other, so two different starter edits shared a citation key.

    Task ids were fixed by making the queue shared (#94); finding numbers by checking them
    here. This is the same shape a third time, so it gets the same treatment rather than
    another round of renumbering by hand.

    ONLY HEADINGS COUNT. Prose legitimately cites an ordinal many times -- "the same
    starter edit as the seventh comparability break" -- and a check that counted those
    would fire on correct documents, which is how a gate gets disabled. A first pass at
    this counted every mention and reported two collisions that were not there.

    THE ORDINAL IS READ GENERICALLY, AND THAT IS THE POINT. `ORDINALS` used to be
    alternated straight into the pattern, which is an enumeration as a trigger (AGENTS.md,
    the rule audit) -- and it ran out. The list ended at `twentieth`, so the twenty-first
    break matched `\\bFIRST\\s+comparability break` inside the word `TWENTY-FIRST` and was
    filed under `first`: a correct document read as a gap at `second, third, fourth`, and a
    second twenty-first break would have been reported as colliding with a `first` that does
    not exist (`tasks/142`). Reading whatever word the heading uses and reporting an
    unrecognised one turns running out of list from a WRONG ANSWER into a LOUD one -- the
    list still has to be extended, but the extension is asked for rather than guessed at.

    A FUNCTION OF ITS INPUT, so `--selftest` can hand it a document instead of the tree.
    """
    lines = text.split("\n")
    fenced = _fence_mask(lines)
    seen: dict[str, list[int]] = {}
    problems: list[str] = []
    for i, ln in enumerate(lines, 1):
        if fenced[i - 1] or not _ATX_HEADING.match(ln):
            continue
        m = _BREAK_HEADING.search(ln)
        if not m:
            continue
        word = m.group(1).lower()
        if word not in ORDINALS:
            problems.append(
                f"eval/RUNS.md line {i} heads a section '{m.group(1)} comparability break' "
                f"and '{word}' is not an ordinal this check knows - either the heading is "
                f"malformed or ORDINALS in eval/tools/docstat.py needs extending past "
                f"'{ORDINALS[-1]}'. Until then the ordering and gap checks cannot see it.")
            continue
        seen.setdefault(word, []).append(i)
    if not seen:
        return problems + ["no comparability-break headings parsed from eval/RUNS.md - the "
                           "wording has changed and this check is reading nothing"]
    for word, at in sorted(seen.items(), key=lambda kv: ORDINALS.index(kv[0])):
        if len(at) > 1:
            problems.append(
                f"eval/RUNS.md heads {len(at)} sections '{word} comparability break' "
                f"(lines {', '.join(map(str, at))}) - the ordinal is the citation key, so "
                f"two regimes now share one. Renumber the later; see #94.")
    idx = sorted(ORDINALS.index(w) for w in seen)
    missing = [ORDINALS[i] for i in range(idx[0], idx[-1] + 1) if i not in idx]
    if missing:
        problems.append(f"eval/RUNS.md skips {', '.join(missing)} between "
                        f"{ORDINALS[idx[0]]} and {ORDINALS[idx[-1]]} - a gap means a "
                        f"citation resolves to nothing")
    return problems


def _check_regime_ordinals() -> list[str]:
    """`_regime_ordinal_problems` over the real `eval/RUNS.md`."""
    path = os.path.join(ROOT, "eval", "RUNS.md")
    if not os.path.exists(path):
        return [f"eval/RUNS.md not found at {path} - this check ran over nothing"]
    return _regime_ordinal_problems(
        open(path, encoding="utf-8", errors="replace").read())


def _regime_ordinal_pins(verbose: bool = False) -> list[str]:
    """Pin the regime-ordinal check in both directions, including the case that broke it.

    The RED half asks whether the check can fail: a collision, a gap, a heading whose
    ordinal the list does not carry, and a corpus with no heading at all.

    The GREEN half is the one that matters here, because the defect this replaces was a
    FALSE POSITIVE on correct input -- a real twenty-first break read as a gap. A mutant
    could never have found it: nothing was missing from the check, it answered the wrong
    thing on an input it mishandled, which only a variant asks (AGENTS.md rule 15). So the
    green cases are compound ordinals, an ordinal cited in PROSE beside a heading, and one
    inside a fence.

    EVERY RED CASE NAMES THE DIAGNOSTIC IT EXPECTS, and that is not tidiness. This function
    has four distinct failure messages, and one of them -- "no comparability-break headings
    parsed" -- fires whenever the scan finds nothing at all. A red pin asserting only
    `bool(got)` therefore passes when the parser has stopped recognising headings entirely,
    which is the exact defect the scan exists to notice. `expect` is the fragment the case
    is really about, so a pin can only go green for its own reason.
    """
    out: list[str] = []

    def case(name: str, text: str, expect: str | None):
        """`expect` is a required fragment of the diagnostic, or None meaning silent."""
        got = _regime_ordinal_problems(text)
        if expect is None:
            good, want = not got, "0 hit(s)"
        else:
            good, want = any(expect in g for g in got), f"a hit saying {expect!r}"
        if verbose:
            print(f"{'PASS' if good else 'FAIL'}  {name}: {len(got)} hit(s), "
                  f"expected {want}")
        if not good:
            out.append(f"the regime-ordinal pin '{name}' came out wrong: {len(got)} "
                       f"hit(s), expected {want} - {got[:2]}")

    _COLLISION = "the ordinal is the citation key"
    _GAP = "a gap means a citation resolves to nothing"
    _UNKNOWN = "is not an ordinal this check knows"
    _NOTHING = "this check is reading nothing"

    head = os.path.join(ROOT, "eval", "RUNS.md")
    if os.path.exists(head):
        case("green, eval/RUNS.md at HEAD",
             open(head, encoding="utf-8", errors="replace").read(), None)

    run = ["## a FIRST comparability break", "## a SECOND comparability break"]
    case("green, two consecutive ordinals", "\n".join(run) + "\n", None)
    case("red, the same ordinal heads two sections",
         "\n".join(run + ["## another SECOND comparability break"]) + "\n", _COLLISION)
    case("red, a gap in the middle",
         "\n".join(run + ["## a FOURTH comparability break"]) + "\n", _GAP)
    case("red, an ordinal past the end of ORDINALS",
         "\n".join(run + ["## a FIFTY-FIRST comparability break"]) + "\n", _UNKNOWN)
    case("red, a heading with no ordinal at all",
         "## the starters changed, a comparability break\n", _UNKNOWN)
    case("red, no comparability-break heading anywhere",
         "## the starters changed on 2026-08-25\n", _NOTHING)

    # The variant. Every compound ordinal ends in a word that is itself an ordinal, so a
    # trigger that alternates ORDINALS files `TWENTY-FIRST` under `first` -- and a document
    # whose breaks run 1..21 then reads as a gap at 2, 3, 4. That is what shipped.
    #
    # THE WORDS ARE WRITTEN OUT, not sliced from ORDINALS. A control that imports its
    # expectation from its subject is not a control (AGENTS.md rule 12, task 113): built as
    # `ORDINALS[:22]`, a regression trimming the tuple back to `twentieth` would silently
    # hand this case 20 SIMPLE ordinals, and it would go green having tested no compound one
    # at all -- green for the absence of the thing it exists to check.
    COMPOUND_FIXTURE = (
        "first", "second", "third", "fourth", "fifth", "sixth", "seventh", "eighth",
        "ninth", "tenth", "eleventh", "twelfth", "thirteenth", "fourteenth", "fifteenth",
        "sixteenth", "seventeenth", "eighteenth", "nineteenth", "twentieth",
        "twenty-first", "twenty-second")
    if len(COMPOUND_FIXTURE) != 22 or "twenty-second" not in COMPOUND_FIXTURE:
        out.append("the compound-ordinal fixture no longer runs to twenty-second, so the "
                   "variant it exists to pin is not being tested")
    compound = ["## a %s comparability break" % w.upper() for w in COMPOUND_FIXTURE]
    case("green, 22 breaks running first..twenty-second (the compound-ordinal variant)",
         "\n".join(compound) + "\n", None)
    case("green, an ordinal cited in prose under its own heading",
         "## a FIRST comparability break\n\nSame starter edit as the first comparability "
         "break, and unlike the first comparability break it changes no score.\n", None)
    case("green, a heading-shaped line inside a fence",
         "## a FIRST comparability break\n\n```\n## a FIRST comparability break\n```\n",
         None)

    # An ATX heading may carry up to three leading spaces. `startswith("#")` read those as
    # prose, so an indented duplicate ordinal was invisible to the collision check while
    # rendering as a heading everywhere else. Three spaces is a heading; four is an indented
    # code block, and must stay invisible -- both directions, or the fix is a new defect.
    case("red, an indented duplicate ordinal (up to 3 spaces is still a heading)",
         "\n".join(run + ["   ## another SECOND comparability break"]) + "\n", _COLLISION)
    case("green, 4 spaces is an indented code block, not a heading",
         "\n".join(run + ["    ## another SECOND comparability break"]) + "\n", None)
    return out


#: A sentence that claims the aspect list is COMPLETE.
#:
#: WHAT THE TRIGGER IS SCOPED TO, and why it is not the quantifier. Until 2026-08-23 this
#: was three alternations - the three wordings the two defective documents happened to
#: use - and task 92 measured what that cost: of 14 planted census claims, each FALSE in
#: the exact way this check exists to catch, it fired on 2. `The five judge aspects are
#: X.`, `There are five aspects: X.` and `The full list of aspects is X.` all passed.
#: That is AGENTS.md's most-repeated defect, a trigger written as an enumeration of the
#: instances someone had seen, and it fails on the first instance they had not. Published
#: as FINDINGS #137, where the old trigger is re-measured against the 15 red pins below:
#: it reds 4, and all 4 are the wordings quoted from the two documents it was built from.
#:
#: The obvious repair is the one that does not work, and it was measured before this one
#: was written. A trigger built on the QUANTIFIER - a cardinal or `all`/`every`/`each`
#: governing `aspects` - caught 10 of the 14 and turned **26 correct lines of the live
#: corpus red**, every single hit a false positive: `All five aspects were run over a
#: full eight-submission field` (DECISIONS.md), `All five aspects failed their gates`
#: (G4-PLATFORMER.md), `ALL SIX aspects separate g4_platformer at n=5` (JUDGING.md),
#: `Six aspects x 5 repeats` (RUNS.md). In this corpus a counted plural `aspects` is
#: overwhelmingly a description of what RAN, COST or FAILED, not a census. A gate that
#: fails on correct input is a gate that gets disabled, which is recorded three times in
#: this file already.
#:
#: SO THE PROPERTY IS THE PREDICATE, not the quantifier. What a census has and a run
#: description does not is an EXISTENCE, IDENTITY or DEFINITION predicate in the present
#: tense, with the enumeration adjacent to it. `were run`, `failed`, `separate`, `x 5
#: repeats` are none of those. That distinction is not a wordlist that grows with each
#: new document: copula, existential `there are`, and `define`/`list`/`set` are closed
#: classes of English, which is what makes this statable as a property at all.
#:
#: A RESTRICTIVE DETERMINER IS NOT A CENSUS. `which aspects are included:` in JUDGING.md
#: heads a table of POOLING SUBSETS and was the single false positive the predicate
#: trigger produced before `NOTREL`; `every aspect that reads them is told so` is the
#: singular form of the same shape. An interrogative or a relative clause narrows the
#: set; it never asserts what the set IS.
#:
#: MEASURED, 2026-08-23, task 92: 14 of 15 planted false censuses red, and **0 red across
#: the 152-document swept corpus**. Widened to all 2090 markdown files in the checkout it
#: is 6 red, all 6 inside `tasks/` or `eval/findings/` and therefore archive-exempt, and
#: all 6 true statements of a superseded census - which is what the archive is for.
#:
#: WHAT IS DELIBERATELY NOT COVERED, with its price. A bare table - an `aspect`-headed
#: column listing five ids with no sentence above it - stays invisible. A structural
#: trigger for it was written and measured at **9 false positives** on the live corpus
#: (JUDGING.md's per-aspect results tables at 361, 467, 547, 612, 662, 799, 1279,
#: G4-PLATFORMER.md:301, DECISIONS.md:651), every one a legitimate table over the subset
#: of aspects that a particular round actually ran. 9 false positives to close one gap
#: that has never occurred is the trade `docstat.py` already refused when it deleted its
#: path check rather than tuning it quiet.
_CENSUS_CARD = (r"(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve)")
#: A list, as it looks where it starts: a backticked id, possibly behind markdown emphasis.
_CENSUS_LIST = r"[*_\s]*`"
#: `which aspects are counted` restricts; it does not declare. Each lookbehind is its own
#: fixed width, which is why they are separate rather than one alternation.
_CENSUS_NOTREL = r"(?<!which\s)(?<!what\s)(?<!whichever\s)"

_ASPECT_CENSUS_RX = re.compile(
    r"(?:"
    # IDENTITY: `... aspects [that exist] ARE <list>`. Present-tense copula with the
    # enumeration adjacent. `aspects were run`, `aspects failed`, `aspects separate` are
    # not copulas and are the commonest true sentences about aspects in this corpus.
    r"\b" + _CENSUS_NOTREL + r"aspects\s+(?:that\s+(?:exist|are\s+defined|are\s+runnable)\s+)?"
    r"(?:are|is)\b(?:[^.`\n]{0,30}?)"
    r"(?:" + _CENSUS_LIST + r"|:|\bdefined\b|\blisted\b|\bthe\s+following\b)"
    # EXISTENCE: `Six aspects exist`, `the aspects are defined`, `There are five aspects`.
    r"|\b" + _CENSUS_NOTREL + r"aspects\s+(?:exist|are\s+defined)\b"
    r"|\bthere\s+(?:are|is)\s+(?:only\s+|just\s+)?" + _CENSUS_CARD + r"\s+(?:\w+\s+)?aspects\b"
    # COMPLETENESS NOUN: `the full list of aspects`, `the complete set of aspects`.
    r"|\b(?:full|complete|entire|exhaustive|whole)\s+(?:list|set)\s+of\s+(?:\w+\s+)?aspects\b"
    # EXCLUSION: the claim that the list has no remainder. `nothing else is runnable` is
    # RUBRIC.md's own wording and is kept because it is still the sentence in the file.
    r"|\bno\s+other\s+aspects?\b"
    r"|\bnothing\s+else\s+is\s+runnable\b"
    r"|\bthese\s+\w+\s+exist\b"
    # DEFINITION BY THE SOURCE: `aspects.py defines five`. A CARDINAL is required, which is
    # what the deleted 2026-08-22 draft lacked - it would have fired on the correct
    # "`aspects.py` defines `FRAMES_BLIND_SPOT`", which has no count in it.
    r"|\bdefines?\s+" + _CENSUS_CARD + r"\b"
    # ENUMERATION PUNCTUATION: `aspects:` / `aspects, in full -` immediately before a list.
    # The 12-character gap admits `Aspects available:` and `The aspects, in full:` without
    # admitting a new sentence; `[^.\n`]` is what stops it crossing one.
    r"|\baspects\b[^.\n`]{0,12}[:\-–—]" + _CENSUS_LIST +
    # UNIVERSAL + SET MEMBERSHIP: `every aspect is one of ...`. The only singular form
    # here, and it is safe because the copula must be adjacent: `every aspect that reads
    # them is told so` and `every aspect resolves in 4 rounds` both have a verb in between.
    r"|\bevery\s+aspects?\s+is\s+(?:one\s+of|either)\b"
    r")", re.I)

#: How far past the claim an id may be named. The claim is a sentence; the ids are in the
#: table under it. 25 lines covers a six-row table with its header and a paragraph either
#: side, and is short enough that a second, unrelated table does not satisfy the first
#: claim's requirement by accident.
_ASPECT_CENSUS_WINDOW = 25


def _check_aspect_census(corpus: dict[str, str], aspects: set[str]) -> list[str]:
    """A doc that claims to list every aspect must list every aspect.

    THE INVERSE OF THE ASPECT CHECK IN `cmd_sweep`, and the reason this exists. That one
    asks whether a name a doc uses resolves, which catches #38 - `RUBRIC.md` naming five
    judges that do not exist. It cannot catch the same defect with the sign reversed: a
    doc DENYING a judge that does exist. `.claude/skills/evaluate-run/SKILL.md` said "the
    five aspects that exist are `fun`, `ux`, `audio`, `idiomatic`, `architecture`" and
    that anything else in prose is a candidate, while `ASPECTS` held six and
    `field_sweep.py --aspects fun_frames` was accepted. `--sweep` was clean, exit 0,
    printing `6 aspects known` in the same line - it knew the count and had nothing that
    compared it with anything. The reader loses on the quiet side: they never run the
    control, and never learn why.

    Pure - takes the corpus and the id set - so the pins can hand it a planted document
    rather than editing a real one.

    Archive docs are exempt. `eval/findings/`, `eval/FINDINGS.md`, both `IMPROVEMENTS.md`
    and `tasks/` record what was believed at the time, and a five-aspect census that was
    true when it was written is their subject matter, not a defect.
    """
    if not aspects:
        return ["no aspect ids parsed from judge/aspects.py, so the aspect-census check "
                "is comparing every doc against an empty set and cannot fire"]
    problems: list[str] = []
    for rel in sorted(corpus):
        if is_archive(rel):
            continue
        lines = corpus[rel].split("\n")
        fenced = _fence_mask(lines)
        for i, ln in enumerate(lines):
            # A FENCED LINE IS NOT A CLAIM - the same discriminator the aspect check uses.
            if fenced[i] or not _ASPECT_CENSUS_RX.search(ln):
                continue
            # THE CLAIM MUST BE ABOUT ASPECTS, on the line making it. `these five exist`
            # is a shape, not a subject, and without this it fires on any doc that counts
            # anything. Scoping it to the line rather than the window is the same lesson
            # the aspect check paid for: a document-scope test lets one unrelated mention
            # 25 lines away satisfy the condition.
            if "aspect" not in ln.lower():
                continue
            window = "\n".join(lines[i:i + _ASPECT_CENSUS_WINDOW])
            # CASE-INSENSITIVE, because an id named in its CONSTANT form is still named.
            # eval/instrfollow/DESIGN.md quotes the defective sentence in order to REPORT
            # it, and names all six two lines later as `IDIOMATIC, ARCHITECTURE, FUN,
            # FUN_FRAMES, AUDIO, UX`. A lowercase-only match read that correct document as
            # the defect it was describing - the third time a gate here has fired on
            # correct input, which is how a gate gets disabled.
            # Identifiers are pulled from INSIDE each backtick span, not required to BE
            # the whole span, and matched case-insensitively. Both halves were needed by
            # one real document: eval/instrfollow/DESIGN.md quotes the defective sentence
            # in order to REPORT it, and names all six two lines later inside a SINGLE
            # span as `IDIOMATIC, ARCHITECTURE, FUN, FUN_FRAMES, AUDIO, UX`. A pattern
            # demanding one-identifier-per-span read that correct document as the very
            # defect it was describing.
            named = {w.lower()
                     for span in re.findall(r"`([^`]+)`", window)
                     for w in re.findall(r"[A-Za-z_]+", span)} & aspects
            missing = aspects - named
            if missing:
                problems.append(
                    f"{rel}:{i + 1}: claims to name every aspect and does not name "
                    f"{', '.join(sorted(missing))}; ASPECTS = {sorted(aspects)}. A doc "
                    f"that denies a judge which exists is #38 with the sign reversed - "
                    f"the reader under-runs the layer and never learns why.")
    return problems


# =============================================================================
# RENUMBERED CITATIONS
#
# Every other check in this file asks whether a name RESOLVES. This one exists because
# the defect it is about resolves perfectly. When two agents in isolated worktrees
# allocate the same finding number, `_check_findings_integrity` above catches the
# collision at merge and one finding is renumbered - and every document that already
# cited the old number now points, in well-formed prose, at somebody else's finding.
# Eight findings were renumbered this way on 2026-08-23, a ninth later the same day.
#
# There is no dangling link to look for. The only record of which numbers moved is git
# history, so that is what this reads.
# =============================================================================

_HEADING_RX = re.compile(r"^##\s+#?(\d+)\s*[.—-]\s*(.*)$")

# `#95`, `FINDINGS #95`, `FINDINGS 95`, `finding 95`. Two digits minimum: `#1`..`#9`
# in this corpus are list markers and anchors, never findings.
_CITE_RX = re.compile(r"(?:#|FINDINGS?\s+#?|[Ff]inding\s+#?)(\d{2,3})\b")


def _git_at(root: str, *args: str,
            extra_env: dict[str, str] | None = None) -> tuple[bool, str]:
    """git in `root`, with the exit status RETURNED rather than folded into the output.

    `_git` below is the right shape for a question whose negative answer is a non-zero exit.
    It is the wrong shape for a question whose answer is a POPULATION: a failed `ls-files`
    and a tree with no files both come back "", and a corpus that is empty for the wrong
    reason gets scanned clean. `_tracked_md` needs the two kept apart, so the split lives
    here and the folding happens only where it is safe.

    EVERY `GIT_*` VARIABLE IS DROPPED FROM THE CHILD, because `-C <root>` does not decide
    which repository git uses - `GIT_DIR` and friends override it, silently and at exit 0:

        GIT_DIR=<other>/.git  git -C <tmp> init -q     ->  rc 0, <tmp>/.git NEVER CREATED
        GIT_DIR=<other>/.git  git -C <tmp> add doc.md  ->  rc 0, staged in <other>'s index
        GIT_DIR=<other>/.git  git -C <tmp> ls-files    ->  <other>'s index, not <tmp>'s

    Every call in this module means *the repository at `root`*, so an inherited one is
    never what was wanted - it is `AGENTS.md` rule 12 with the address supplied by the
    caller's environment. Measured 2026-08-27: `_tree_fixture` ran once under an inherited
    `GIT_DIR` and left 6 fixture paths staged in a live worktree's index with `.gitignore`
    replaced there, the working tree untouched, at exit 0 throughout.

    ALL of `GIT_*`, not the 4 that steer discovery. A list of variable names is an
    enumeration, and the next reader meets `GIT_COMMON_DIR` or `GIT_NAMESPACE`, which are
    not on it; nothing this module runs needs any of them. `extra_env` is for a caller that
    must set one deliberately.
    """
    child = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    child.update(extra_env or {})
    try:
        r = subprocess.run(["git", "-C", root, *args], capture_output=True, text=True,
                           check=False, env=child)
    except (OSError, ValueError) as exc:
        return False, str(exc)
    if r.returncode != 0:
        # STDERR, because that is where git writes the reason and a failing `ls-files`
        # writes nothing to stdout. Returning the empty stdout would make `_tracked_md`
        # refuse loudly and name no cause, which is the half that decides how long the
        # repair takes. Raised by CodeRabbit on PR #54.
        return False, r.stderr or f"exit {r.returncode} with no diagnostic"
    return True, r.stdout


def _git(*args: str) -> str:
    """git in the repository this file lives in. Empty string on failure, never a raise.

    `check=False` is the point, not an oversight: several calls here ASK a question whose
    negative answer is a non-zero exit - `cat-file -t` on a path a parent does not have, or
    `blame` on a file that revision never contained. Raising on those would turn a normal
    reading into a crash. The exit code is read (#105); it is just read here, once, instead
    of at every call site.
    """
    ok, out = _git_at(ROOT, *args)
    return out if ok else ""


class _History:
    """The findings numbering as it stood at any commit, cached by blob and by tree.

    THE ADDRESS IS AN INPUT TO THE CHECK (#60). `ROOT` is a filesystem path and
    `eval/findings/` is a path inside a git tree; nothing makes those agree by
    construction, so `ok()` asserts it rather than trusting it.
    """

    UNCOMMITTED = "0" * 40

    def __init__(self, rev: str = "HEAD") -> None:
        self.rev = rev
        # READ THE WORKING TREE, NOT THE LAST COMMIT, unless a revision was asked for.
        # Every other check in this file reads files off disk. If this one read
        # `HEAD:path` instead, a citation repaired but not yet committed would still be
        # reported, the reader would conclude the check is noise, and the next real hit
        # would be skipped with it. `git blame` with no revision blames the working tree
        # and marks uncommitted lines with an all-zero sha, which is exactly the signal
        # needed: a line edited just now cannot be a citation written before a renumber.
        self.worktree = rev == "HEAD"
        self._blob: dict[str, list[tuple[int, str]]] = {}
        self._tree: dict[str, dict[int, str]] = {}
        self._parents: dict[str, list[str]] = {}
        self._blame: dict[tuple[str, str], list[tuple[str, str]]] = {}
        self._ctime: dict[str, int] = {}
        top = _git("rev-parse", "--show-toplevel").strip()
        self.rooted = bool(top) and os.path.realpath(top) == os.path.realpath(ROOT)

    def headings(self, blob_sha: str) -> list[tuple[int, str]]:
        if blob_sha not in self._blob:
            lines = _git("cat-file", "blob", blob_sha).split("\n")
            fenced = _fence_mask(lines)
            out = []
            for i, ln in enumerate(lines):
                if fenced[i]:
                    continue
                m = _HEADING_RX.match(ln)
                if m:
                    out.append((int(m.group(1)), m.group(2).strip()))
            self._blob[blob_sha] = out
        return self._blob[blob_sha]

    def numbering(self, commit: str) -> dict[int, str]:
        """{finding number: heading text} in eval/findings/ as of `commit`."""
        if commit not in self._tree:
            m: dict[int, str] = {}
            for ln in _git("ls-tree", "-r", commit, "eval/findings/").split("\n"):
                p = ln.split()
                if len(p) >= 4 and p[1] == "blob" and p[3].endswith(".md"):
                    for num, h in self.headings(p[2]):
                        m[num] = h
            self._tree[commit] = m
        return self._tree[commit]

    def parents(self, commit: str) -> list[str]:
        if commit not in self._parents:
            out = _git("rev-list", "--parents", "-n", "1", commit).split()
            self._parents[commit] = out[1:]
        return self._parents[commit]

    def ctime(self, commit: str) -> int:
        if commit not in self._ctime:
            s = _git("show", "-s", "--format=%ct", commit).strip()
            self._ctime[commit] = int(s) if s.isdigit() else 0
        return self._ctime[commit]

    def blame(self, rev: str, path: str) -> list[tuple[str, str]]:
        """[(commit, line text)], one entry per line.

        `-w` IS LOAD-BEARING, NOT TIDINESS. `AGENTS.md` rule 16's `(#90)` was written
        against a tree where #90 was the weight-sensitivity finding, which is #92 now.
        A later commit re-indented rules 10-16 by one space and nothing else; plain
        blame therefore dates that citation AFTER the renumber and reads it as fresh.
        With `-w` it dates to the commit that wrote it and the staleness is visible.
        A whitespace-only edit must not be able to launder a citation.
        """
        key = (rev, path)
        if key not in self._blame:
            out: list[tuple[str, str]] = []
            cur = ""
            argv = ["blame", "-w", "-M", "--line-porcelain"]
            if not (self.worktree and rev == self.rev):
                argv.append(rev)
            for ln in _git(*argv, "--", path).split("\n"):
                m = re.match(r"^([0-9a-f]{40}) ", ln)
                if m:
                    cur = m.group(1)
                elif ln.startswith("\t"):
                    out.append((cur, ln[1:]))
            self._blame[key] = out
        return self._blame[key]

    def authoring_commit(self, path: str, index: int) -> tuple[str, str]:
        """Follow one line back through merges to the side that actually wrote it.

        A merge that resolves a number collision lands TWO things in one commit: the
        renumbered heading, and the closing branch's prose citing the old number. Blame
        stops at the merge, whose tree already disagrees with what the citation's author
        was looking at. Descending into the single parent that carries the line verbatim
        recovers the tree the author saw.

        Stops at the merge when both parents carry the line (it predates the merge on
        both sides, so either tree answers the same) or when neither does (the merge
        itself wrote the line, which is what a hand-corrected citation looks like).
        """
        b = self.blame(self.rev, path)
        if index >= len(b):
            return "", ""
        commit, text = b[index]
        if commit == self.UNCOMMITTED:
            return "", text      # written in the working tree, i.e. after every renumber
        seen: set[str] = set()
        while commit and commit not in seen:
            seen.add(commit)
            ps = self.parents(commit)
            if len(ps) < 2:
                return commit, text
            holders = []
            for p in ps:
                if _git("cat-file", "-t", f"{p}:{path}").strip() != "blob":
                    continue
                pb = self.blame(p, path)
                hit = [i for i, (_, t) in enumerate(pb) if t == text]
                if hit:
                    holders.append(pb[hit[0]][0])
            if len(holders) != 1:
                return commit, text
            commit = holders[0]
        return commit, text


def _norm_heading(h: str) -> str:
    """A heading's identity, stable under later copy-edits to its tail.

    Eight words of alphanumerics. Headings here get corrected after the fact; the number
    in front of them is what this module is tracking, so the key has to survive a reworded
    ending without merging two distinct findings. Measured over all 47 commits that have
    touched `eval/findings/`: 0 collisions between distinct findings.
    """
    return " ".join(re.sub(r"[^a-z0-9 ]", " ", h.lower()).split()[:8])


def _renumber_events(hist: _History) -> list[tuple[int, int, int, str]]:
    """Every (old, new, when, heading) the history of `eval/findings/` contains.

    Replays each commit that touched the directory and records a heading whose number
    differs from the last number that heading had. This is derived, never listed: a
    hand-kept table of renumbers is a second source of truth and goes stale in exactly
    the way the citations it describes went stale.
    """
    seq: dict[str, list[tuple[int, str, int]]] = {}
    commits = _git("rev-list", "--reverse", "--date-order", hist.rev, "--",
                   "eval/findings/").split()
    for c in commits:
        for num, h in sorted(hist.numbering(c).items()):
            k = _norm_heading(h)
            if not k:
                continue
            prev = seq.setdefault(k, [])
            if not prev or prev[-1][0] != num:
                prev.append((num, h, hist.ctime(c)))
    events = []
    for runs in seq.values():
        for a, b in zip(runs, runs[1:], strict=False):
            events.append((a[0], b[0], b[2], b[1]))
    return sorted(events)


def _check_renumbered_citations(rev: str = "HEAD") -> tuple[list[str], list[str], str]:
    """(decided stale, undecided, summary). Returns, never raises, never gates.

    WHAT IS DECIDABLE AND WHAT IS NOT
    ---------------------------------
    A citation cannot be judged by whether it resolves - it always does. It has to be
    resolved against the numbering its OWN AUTHOR was looking at, and then that finding
    followed to the number it carries today. Three cases fall out, and only the first
    is decidable:

    A. THE CITATION AND THE RENUMBER ARE IN DIFFERENT COMMITS. Resolve `#N` against the
       findings tree at the citation's authoring commit, take that heading's number now,
       and report if they differ. No judgement in it. 17 hits at the revision this was
       written against, 0 false positives on inspection.

    B. THEY ARE IN THE SAME COMMIT. The merge that resolves a collision writes the
       renumbered heading and the closing task's `established_by` string together, and
       there is no ordering inside a commit. Four of the five citations repaired by hand
       on 2026-08-23 are this shape - tasks 25, 34 and 42 - and case A cannot see them.

    C. THE AUTHOR'S TREE WAS NEVER COMMITTED. Task 45 cited `#99` for a finding that was
       `#99` only in another agent's worktree; on every committed tree of that hour `#99`
       already meant the skills mirror. The citation was wrong the moment it was written,
       and no reading of history recovers what its author saw, because what its author saw
       does not exist in history.

    So this reports two lists. The first is a verdict. The second is a SHORT LIST FOR A
    PERSON: every citation of a number that has ever been reused, written no later than
    the last time that number changed hands. B and C both live there, and so do plenty of
    perfectly correct citations - which is why it prints and does not fail.

    THE CONTROL. Run `--renumbered --at 1120695^`, the commit before the five known
    citations were repaired by hand: the decided list contains `eval/PROTOCOL.md:541`
    (`#103`, now `#104`) and the undecided list contains the other four. Run it at HEAD
    and none of the five appear. A check that cannot find a defect that is known to be
    there is reporting its own silence.

    THIS CHECK CANNOT GRADE YOUR REPAIR, AND GOES GREEN TWICE FOR REASONS THAT ARE NOT
    THE REPAIR. Both were met head-on repairing the 33 of task 72:

    - UNCOMMITTED. A line edited in the working tree blames to UNCOMMITTED, so
      `authoring_commit` returns "" and the loop skips it. Every repair is invisible
      until it is committed, correct and incorrect alike, and the count falls to zero
      either way. **Re-run after committing; a clean report over a dirty tree is the
      tool declining to look.**
    - COMMITTED. A repair committed today has today's findings tree as its authoring
      tree, so `then[num] is current[num]`, `now == num`, and it is never stale - again
      whatever number you wrote. The same holds for the undecided half, whose `when`
      is now later than every renumber.

    So zero after a repair is necessary and not sufficient (rule 1): it establishes that
    no citation OLDER than the renumbers is still stale, and says nothing about the
    replacements. The only thing that grades a replacement is reading it against the
    heading in eval/findings/. A plant at HEAD cannot restore the alarm either, for the
    second reason above - to see it fire once the sweep is clean, commit the citation on
    a branch rooted at a pre-renumber commit and merge it forward, which is the shape
    that produced these in the first place. Done for task 72 off `e86e09d0` (where #119
    was the retired suite): decided went 0 -> 1, naming the plant and #122.
    """
    hist = _History(rev)
    if not hist.rooted:
        return ([], [], "renumbered-citation check did NOT run: git is unavailable, or "
                        f"its toplevel is not {ROOT}. This check reads history and has no "
                        f"answer without it - it is not clean, it is blind.")
    current = hist.numbering(rev)
    if not current:
        return ([], [], f"renumbered-citation check did NOT run: no `## NN.` headings "
                        f"parsed from eval/findings/ at {rev}. An empty numbering is "
                        f"indistinguishable from a clean one, so this is an error.")
    by_key = {_norm_heading(h): n for n, h in current.items()}

    events = _renumber_events(hist)
    reused: dict[int, int] = {}          # old number -> last time it changed hands
    for old, _new, when, _h in events:
        reused[old] = max(reused.get(old, 0), when)
    if not events:
        return ([], [], f"no finding has ever been renumbered under {rev}; "
                        f"{len(current)} findings, nothing to check")

    files = [f for f in _tracked_md(rev=None if hist.worktree else rev)
             if "/runs/" not in f and not is_vendored(f)]

    stale: list[str] = []
    undecided: list[str] = []
    for path in files:
        if hist.worktree:
            disk = os.path.join(ROOT, path)
            if not os.path.exists(disk):
                continue                       # deleted in the working tree
            lines = open(disk, encoding="utf-8", errors="replace").read().split("\n")
        else:
            lines = _git("show", f"{rev}:{path}").split("\n")
        # Blame is the expensive call. Only a file citing a number that has actually
        # been reused can produce a hit, so ask that question from the text first.
        if not any(int(m.group(1)) in reused
                   for ln in lines for m in _CITE_RX.finditer(ln)):
            continue
        for i, ln in enumerate(lines):
            if _HEADING_RX.match(ln):
                continue            # a finding's own heading is the definition, not a citation
            nums = {int(m.group(1)) for m in _CITE_RX.finditer(ln)}
            if not nums & set(reused):
                continue
            commit, _text = hist.authoring_commit(path, i)
            if not commit:
                continue
            then = hist.numbering(commit)
            when = hist.ctime(commit)
            for num in sorted(nums & set(reused)):
                meant = then.get(num)
                now = by_key.get(_norm_heading(meant)) if meant else None
                where = f"{path}:{i + 1}"
                excerpt = ln.strip()[:96]
                if meant and now is not None and now != num:
                    stale.append(
                        f"{where}: #{num} meant \"{meant[:64]}\" when it was written "
                        f"({commit[:8]}); that finding is #{now} today. "
                        f"Fix the CITATION - the published number is #{now}. | {excerpt}")
                elif when <= reused[num]:
                    held = f"\"{meant[:56]}\"" if meant else "nothing yet in eval/findings/"
                    undecided.append(
                        f"{where}: #{num} written {commit[:8]} while #{num} was still "
                        f"changing hands; the committed trees of that moment say it meant "
                        f"{held}. Read it. | {excerpt}")

    summary = (f"{len(events)} renumber event(s) in eval/findings/ history; "
               f"{len(reused)} number(s) have named more than one finding")
    return stale, undecided, summary


# =============================================================================
# THE TRIAGE REGISTER, added 2026-08-23 under task 102.
#
# The undecidable half of `--renumbered` is a STANDING list. It contains correct
# citations by construction, so it never reaches zero, and the reader who runs the
# command gets no way to tell a row somebody has already adjudicated from one nobody
# has ever looked at. Task 102 read all 51 rows at that revision: 15 were wrong and
# were repaired, 36 were right. Without somewhere to put those 36 verdicts, the next
# reader re-derives every one of them - which is the cost this file exists to remove.
#
# THE VERDICT CANNOT BE DERIVED, which is the whole reason the register is by hand:
# `_check_renumbered_citations` already exhausts what history can say about these rows.
# What decides them is reading the citing sentence against the heading in eval/findings/.
# So this stores a judgement, exactly as `withdrawn.json` does, and for the same reason:
# the only detectable property of an adjudication is that somebody wrote it down.
#
# KEYED BY THE CITING TEXT, NEVER BY A LINE NUMBER. A line number is invalidated by any
# edit anywhere above it in the file, which would silently unpair every entry in a
# document and report 36 fresh rows as if nobody had read them. The anchor is a substring
# of the citing line that must itself contain the citation, so it cannot drift onto a
# neighbouring sentence.
# =============================================================================

TRIAGE_PATH = os.path.join(REPO, "renumber_triage.json")


def _load_triage() -> list[dict]:
    """The register, or [] if it is absent. Malformed is an ERROR, not an absence.

    A register that fails to parse must not read as "nothing has been triaged": that is
    the vacuous pass this module exists to prevent, and it would present 36 adjudicated
    rows as untouched. `_check_triage_register` turns the raise into a reported problem.
    """
    if not os.path.exists(TRIAGE_PATH):
        return []
    with open(TRIAGE_PATH, encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError(f"{TRIAGE_PATH}: expected a list of entries")
    return data


def _triage_index(entries: list[dict]) -> dict[tuple[str, int], list[dict]]:
    idx: dict[tuple[str, int], list[dict]] = {}
    for e in entries:
        idx.setdefault((e.get("path", ""), int(e.get("cites", 0))), []).append(e)
    return idx


def _row_line(hist: _History, where: str) -> str:
    """The WHOLE citing line named by a `path:lineno` row.

    THE ADDRESS IS AN INPUT TO THE CHECK (#60), and the first draft of this got it wrong
    in the way that looks like a result. It matched anchors against the row's printed
    excerpt, which `_check_renumbered_citations` truncates to 96 characters - so four
    entries whose anchor sits past column 96 reported as UNTRIAGED, indistinguishable
    from four rows nobody had read. `established_by` lines run to several thousand
    characters, so the truncation is the common case there, not the corner.
    """
    path, _, lineno = where.rpartition(":")
    if not lineno.isdigit():
        return ""
    if hist.worktree:
        disk = os.path.join(ROOT, path)
        if not os.path.exists(disk):
            return ""
        lines = open(disk, encoding="utf-8", errors="replace").read().split("\n")
    else:
        lines = _git("show", f"{hist.rev}:{path}").split("\n")
    i = int(lineno) - 1
    return lines[i] if 0 <= i < len(lines) else ""


def _triage_for(idx: dict, where: str, num: int, line_text: str) -> dict | None:
    """The recorded verdict for one undecidable row, matched on the citing text."""
    path = where.rsplit(":", 1)[0]
    for e in idx.get((path, num), []):
        if e.get("anchor", "\0") in line_text:
            return e
    return None


def _check_triage_register() -> list[str]:
    """An entry that matches nothing is a reference that does not resolve - so it GATES.

    This is the same question `--sweep` asks of every other name in the corpus, pointed
    at the register itself. Three ways an entry can stop meaning anything, all mechanical
    and none of them a judgement:

      absent    the file it names is gone
      unmatched its anchor occurs nowhere in that file - the sentence was rewritten, and
                the verdict recorded against it no longer describes anything
      ambiguous its anchor occurs more than once, so which line it adjudicated is unknown

    A fourth is self-consistency: an anchor that does not contain the citation it claims
    to adjudicate cannot have come from that row. That one caught a bad key while the
    register was being written, which is the only reason it is here rather than assumed.

    NOT an error, and deliberately: an entry whose row is no longer REPORTED. A repair or
    a later renumber can retire a row without touching the sentence, and gating on that
    would fire on correct input every time the decidability of a row changes. Those are
    printed by `--renumbered` as recorded-but-unreported instead.
    """
    problems: list[str] = []
    try:
        entries = _load_triage()
    except (ValueError, json.JSONDecodeError, OSError) as exc:
        return [f"eval/renumber_triage.json does not parse ({exc}). An unreadable "
                f"register is not an empty one - every recorded verdict is invisible "
                f"until it parses."]
    for e in entries:
        path, anchor = e.get("path", ""), e.get("anchor", "")
        num = int(e.get("cites", 0))
        disk = os.path.join(ROOT, path)
        if not anchor or not path:
            problems.append("renumber_triage.json: an entry has no path or no anchor")
            continue
        if num not in {int(m.group(1)) for m in _CITE_RX.finditer(anchor)}:
            problems.append(
                f"renumber_triage.json: the entry for {path} claims to adjudicate "
                f"#{num}, but its anchor `{anchor[:50]}` does not contain that citation.")
            continue
        if not os.path.exists(disk):
            problems.append(f"renumber_triage.json: {path} does not exist, but an entry "
                            f"records a verdict on #{num} in it.")
            continue
        text = open(disk, encoding="utf-8", errors="replace").read()
        n = text.count(anchor)
        if n == 0:
            problems.append(
                f"renumber_triage.json: no line of {path} contains "
                f"`{anchor[:50]}`. The verdict recorded for #{num} there adjudicates a "
                f"sentence that no longer exists - re-read the row and re-record it.")
        elif n > 1:
            problems.append(
                f"renumber_triage.json: `{anchor[:50]}` occurs {n} times in {path}, so "
                f"the entry for #{num} does not say which row it adjudicated.")
    return problems


def cmd_renumbered(rev: str = "HEAD") -> int:
    stale, undecided, summary = _check_renumbered_citations(rev)
    hist = _History(rev)
    if hist.rooted and hist.numbering(rev):
        print("RENUMBER MAP (derived from git, never listed by hand)\n")
        for old, new, _when, h in _renumber_events(hist):
            print(f"  #{old:>3} -> #{new:<3}  {h[:88]}")
        print()
    print(summary + "\n")
    print(f"DECIDED STALE - {len(stale)}. The citing commit's own tree says so:\n")
    for s in stale:
        print(f"  {s}")

    try:
        entries = _load_triage()
    except (ValueError, json.JSONDecodeError, OSError):
        entries = []
        print("\n!! eval/renumber_triage.json does not parse; every recorded verdict is "
              "invisible below. `--sweep` names the defect.")
    idx = _triage_index(entries)
    seen: list[int] = []
    triaged, fresh = [], []
    for s in undecided:
        where, rest = s.split(": ", 1)
        num = int(rest.split("#", 1)[1].split(" ", 1)[0])
        e = _triage_for(idx, where, num, _row_line(hist, where))
        (triaged if e else fresh).append((s, e))
        if e:
            seen.append(id(e))

    print(f"\nUNTRIAGED - {len(fresh)} of {len(undecided)}. History cannot say; "
          f"READ THESE and record the verdict in eval/renumber_triage.json:\n")
    for s, _ in fresh:
        print(f"  {s}")
    print(f"\nALREADY TRIAGED - {len(triaged)}. A person read the citing sentence "
          f"against the heading in eval/findings/ and recorded this:\n")
    for s, e in triaged:
        where = s.split(": ", 1)[0]
        print(f"  {where}: #{e['cites']} {e['verdict'].upper()} - {e['note']} "
              f"[{e['triaged']}]")

    orphan = [e for e in entries if id(e) not in seen]
    if orphan:
        print(f"\nRECORDED BUT NOT REPORTED - {len(orphan)}. The sentence is still there; "
              f"the row is no longer\nreported undecidable. Harmless, and the entry can "
              f"go when someone is in here anyway:\n")
        for e in orphan:
            print(f"  {e['path']}: #{e['cites']} `{e['anchor'][:48]}`")

    print("\nNever renumber a finding to satisfy this. The number in eval/findings/ is")
    print("the published one; the citation is what is wrong.")
    return 0


# ======================================================================
# THE WITHDRAWAL REGISTER
#
# Every other reference check here asks whether a name RESOLVES. This one asks whether a
# figure or a claim that was RETIRED is still being stated as current - and a retired
# figure resolves perfectly, agrees with every copy of itself, and reads as established.
#
# The obvious design was built first and measured, and it comes out against. A
# cross-document figure-agreement check over the six live docs found 52 labelled figures,
# 1 disagreement, and that one a false positive (#113). It cannot see this defect by
# construction: when a stale figure propagates, the restatements agree TO THE DIGIT.
# Propagation and consistency are the same observation.
#
# So the register inverts it. A figure is DECLARED retired, by id, in `eval/withdrawn.json`,
# and the question becomes whether anything still states it as current.
# =============================================================================

#: Documents that record what was believed WHEN THEY WERE WRITTEN, and must therefore be
#: free to state a retired figure without marking. Stated as a property in prose and as
#: paths here because there is no property in the filesystem to read it off: `FINDINGS.md`
#: and `README.md` are both markdown at similar depths and only one of them is a log.
#:
#: THE COST OF THIS IS REAL AND IS THE REASON IT IS SMALL. A whole-file exemption is
#: document-scope, and document-scope exemptions are what made the aspect check vacuous
#: once - one legitimate disclaimer silenced every check in its file. Inside a LIVE
#: document nothing is exempt by file: the only exemption is an id inside the block.
#:
#: `tasks/` is here because a task's whole subject can be a figure that is being retired -
#: task 54's `done_when` states the pair three times, correctly.
ARCHIVE_PATHS = (
    "eval/findings/",       # the findings log, per finding
    "eval/FINDINGS.md",     # its index
    "eval/IMPROVEMENTS.md", # iteration log for the evaluator
    "IMPROVEMENTS.md",      # iteration log for the templates
    "CLEANUP-LOG.md",       # what each cleanup pass looked at
    "tasks/",               # the open-work queue: a retired figure can be the task
    "eval/runs/",           # stored data, not guidance
)

REGISTER_PATH = os.path.join(REPO, "withdrawn.json")


def is_archive(rel: str) -> bool:
    """True for a document whose job is to record what was believed at the time."""
    rel = rel.replace(os.sep, "/")
    return any(rel == a or rel.startswith(a) for a in ARCHIVE_PATHS if a.endswith("/")) or \
        rel in ARCHIVE_PATHS


def _claim_blocks(lines: list[str]) -> list[tuple[int, int]]:
    """Maximal runs of lines that make one claim together: [start, end).

    THE WINDOW IS THE UNIT THE EXEMPTION IS SCOPED TO, so what counts as one is the whole
    design. Three properties, each bought:

    1. A LINE IS TOO SMALL. `1.70` and `2.05` sit on two rows of a table and in two lines
       of one sentence; a per-line rule would never see the pair co-occur.
    2. A FILE IS TOO BIG. `JUDGING.md` declares this exact withdrawal 114 lines below a
       block that restates it. A file-scoped exemption would call that green, which is the
       vacuous pass this module exists to prevent.
    3. `>` ON ITS OWN SEPARATES. Inside a blockquote an empty line is written `>`, and
       `README.md`'s corrections table is one 30-line quote holding four INDEPENDENT
       withdrawal notices. Treating it as one block would let any one notice's id excuse
       the other three.
    4. A TOP-LEVEL LIST ITEM STARTS A NEW ONE. A tight markdown list is one block to a
       parser, and `DECISIONS.md`'s open-questions list is 54 consecutive lines of
       independent bullets. Measured before this rule: the whole list came back as ONE
       window, so an id in any bullet would have excused every other bullet in it.
       Continuation lines stay with their item, which is what makes a multi-line bullet
       still able to state a pair.

    Fenced lines separate and never join a block, following the rule the aspect check
    already uses here: inside ``` a line is a command to run or an output to expect, and
    a shell command asserts nothing about its own arguments. The cost is stated in
    `_check_withdrawal_register`'s docstring rather than assumed.
    """
    fenced = _fence_mask(lines)
    item = re.compile(r"^([-*+]|\d{1,3}[.)])\s")
    blocks: list[tuple[int, int]] = []
    start: int | None = None
    for i, raw in enumerate(lines):
        text = raw.strip()
        while text.startswith(">"):
            text = text[1:].strip()
        empty = fenced[i] or not text
        if empty:
            if start is not None:
                blocks.append((start, i))
                start = None
            continue
        # A NEW TOP-LEVEL ITEM ENDS THE PREVIOUS ONE. `raw`, not `text`: an indented
        # sub-item is a continuation of the item above it and must not split the window,
        # while the same marker at column 0 is a new claim.
        if start is not None and item.match(raw):
            blocks.append((start, i))
            start = i
        elif start is None:
            start = i
    if start is not None:
        blocks.append((start, len(lines)))
    return blocks


def load_register(path: str = REGISTER_PATH) -> tuple[list[dict], list[str]]:
    """(entries, problems). Never raises: an unreadable register is a REPORTED failure.

    Failing closed is the point. A register that quietly returns zero entries passes every
    document in the repository and is indistinguishable from a clean one.
    """
    if not os.path.exists(path):
        return [], [f"the withdrawal register is missing at {os.path.relpath(path, ROOT)}. "
                    f"With no register nothing is declared retired, and this check passes "
                    f"every document in the repository - which is not the same as clean."]
    try:
        data = json.loads(open(path, encoding="utf-8").read())
    except (OSError, ValueError) as e:
        return [], [f"{os.path.relpath(path, ROOT)} does not parse: {e}"]
    entries = data.get("entries") if isinstance(data, dict) else None
    if not isinstance(entries, list) or not entries:
        return [], [f"{os.path.relpath(path, ROOT)} declares no entries; the check would "
                    f"run over 0 subjects and report clean"]

    problems, seen = [], set()
    for n, e in enumerate(entries):
        where = f"{os.path.relpath(path, ROOT)} entry {n}"
        if not isinstance(e, dict):
            problems.append(f"{where}: not an object")
            continue
        for k in ("id", "withdrawn", "claim", "match", "anchor", "replaced_by"):
            if not e.get(k):
                problems.append(f"{where}: no `{k}`")
        eid = e.get("id")
        if eid in seen:
            problems.append(f"{where}: duplicate id `{eid}` - the id is the exemption key, "
                            f"so two entries sharing one means citing either excuses both")
        seen.add(eid)
        for pat in e.get("match") or []:
            try:
                re.compile(pat)
            except re.error as ex:
                problems.append(f"{where}: `match` pattern {pat!r} does not compile ({ex})")
        anchor = e.get("anchor")
        if anchor and not is_archive(anchor):
            problems.append(
                f"{where}: anchor `{anchor}` is a LIVE document. The anchor exists to prove "
                f"the patterns still match something; a live anchor would have to carry the "
                f"id to stay green, and then it proves only that the id is present.")
    return entries, problems


def _states(entry: dict, block_text: str) -> bool:
    """Does this block state the entry? ALL patterns must occur in it.

    ALL and not ANY. One loose pattern - `#54`, `1.70` - fires on unrelated prose; the
    conjunction is what makes an entry specific enough to gate on. An entry that needs
    only one pattern is declaring that the one pattern IS the signature, which is true
    for a citation id and false for a bare number.
    """
    return all(re.search(p, block_text) for p in entry.get("match") or [])


def scan_withdrawn(entries: list[dict], corpus: dict[str, str]) -> list[str]:
    """Live restatements of a registered entry. `corpus` is {relpath: text}, live only.

    Pure, so the controls can hand it a planted document rather than a temp checkout.
    """
    hits = []
    for rel, text in sorted(corpus.items()):
        lines = text.split("\n")
        for a, b in _claim_blocks(lines):
            block = "\n".join(lines[a:b])
            for e in entries:
                if not _states(e, block):
                    continue
                if e["id"] in block:
                    continue     # a declared withdrawal notice, keyed on the id
                excerpt = " ".join(lines[a].strip().split())[:88]
                hits.append(
                    f"{rel}:{a + 1}-{b}: states `{e['id']}`, withdrawn {e['withdrawn']}, "
                    f"in a block that does not cite it. {e['claim'][:88]} "
                    f"| Instead: {e['replaced_by'][:110]} | {excerpt}")
    return hits


def _live_corpus(rev: str | None = None) -> tuple[dict[str, str], list[str]]:
    """({relpath: text}, problems) for every LIVE markdown document.

    THE ADDRESS IS AN INPUT TO THE CHECK (#60). The tree is spelled once, in `_tracked_md`,
    which `project_docs()` also reads - and `_corpus_pins` asserts the two agree about
    membership rather than leaving it to a comment. An empty corpus is the one result
    indistinguishable from a clean one, so it is reported rather than returned as green.
    """
    corpus, problems, empty = {}, [], []
    for rel in _tracked_md(rev=rev):
        if is_vendored(rel) or is_archive(rel):
            continue
        if rev:
            # `_git` returns "" on a non-zero exit, so an unreadable blob would enter the
            # corpus as an empty document and be scanned clean. That is fail-open: the
            # check would report nothing about a file it never read. Count them instead.
            text = _git("show", f"{rev}:{rel}")
            if not text.strip():
                empty.append(rel)
                continue
            corpus[rel] = text
        else:
            disk = os.path.join(ROOT, rel)
            if not os.path.exists(disk):
                continue                      # deleted in the working tree
            corpus[rel] = open(disk, encoding="utf-8", errors="replace").read()
    if empty:
        problems.append(
            f"{len(empty)} live document(s) read as empty at {rev} and were NOT scanned "
            f"(git show failed, or they really are empty): {', '.join(empty[:4])}")
    if not corpus:
        problems.append(
            f"the withdrawal check found 0 live markdown documents"
            f"{' at ' + rev if rev else ''}. git is unavailable, or every document was "
            f"classified as archive. This is blind, not clean.")
    return corpus, problems


def _check_withdrawal_register(rev: str | None = None) -> tuple[list[str], str]:
    """(problems, summary). Is a retired figure still stated as current in a live document?

    THE RULE, and there is only one: if every `match` pattern of a register entry occurs
    inside one block of a LIVE document, and that block does not contain the entry's `id`,
    the block states a retired figure as current.

    WHY THE EXEMPTION IS THE ID AND NOT A MARKER WORD. A vocabulary - `withdrawn`,
    `superseded`, `retracted`, `a previous version read` - is an enumeration, and this
    project has measured an enumeration failing on ONE INFLECTION OF A VERB: the aspect
    check's exemption listed `planted` and went red on `planting`. An id has no
    inflections. A file/line allowlist was rejected for the ordinary reason: lines move.

    WHAT THIS SEPARATES, AND WHAT IT DOES NOT. It does not decide whether a sentence STATES
    a retired figure or ASSERTS it as current - nothing mechanical here can, and the two
    are the same characters. What it does is make the author declare which, in place, at a
    cost of one parenthetical. That is a CONVENTION imposed on live documents, and it is
    the convention doing the work, not an inference:

        (#54 - withdrawn, WR-arch-ux-redundancy)

    A reader who lands on that line is warned there; a reader who lands on a paragraph
    whose withdrawal is declared 114 lines below is not. So the false positives this
    produces on genuinely historical prose in a live document are not noise to be tuned
    away - they are the check asking for a marking that the document wanted anyway.

    WHAT IT CANNOT SEE, stated rather than discovered later:

      - A PARAPHRASE. `match` is a string signature. "the two judges with disjoint evidence
        agreed perfectly" restates WR-arch-ux-redundancy and contains none of its patterns.
        The register can only find a restatement that carries the number or the citation.
      - ANYTHING INSIDE A FENCE, by the same rule the aspect check uses. A retired figure
        pasted as tool output is invisible here.
      - A FIGURE NOBODY DECLARED. This is the whole premise: the register records decisions
        already made. It cannot discover a withdrawal, only enforce one.
      - A BLOCK THAT CITES AN ID FOR A DIFFERENT REASON. Citing `WR-tier3-pair` anywhere in
        a block excuses that block for that entry. The window is a few lines, so the surface
        is small, but it is a channel and it is named here rather than left implicit.

    THE ANCHOR IS THE POSITIVE CONTROL, AND IT RUNS EVERY TIME. Each entry names an ARCHIVE
    document that states it in full. If the patterns do not match there, the entry is
    reporting its own silence and that is a failure - rule 12: prove the extraction on one
    case whose answer you can state in advance, before believing the census.
    """
    entries, problems = load_register()
    if not entries:
        return problems, "withdrawal register: NOT READ"

    for e in entries:
        anchor = os.path.join(ROOT, e.get("anchor", ""))
        if not os.path.exists(anchor):
            problems.append(f"{e['id']}: anchor {e.get('anchor')} does not exist, so the "
                            f"entry's patterns are proved against nothing")
            continue
        lines = open(anchor, encoding="utf-8", errors="replace").read().split("\n")
        if not any(_states(e, "\n".join(lines[a:b])) for a, b in _claim_blocks(lines)):
            problems.append(
                f"{e['id']}: its `match` patterns co-occur in no block of its anchor "
                f"{e['anchor']}. The entry matches nothing it is known to describe, so a "
                f"green result from it is silence, not evidence (AGENTS.md rule 12).")

    corpus, corpus_problems = _live_corpus(rev)
    problems += corpus_problems
    problems += scan_withdrawn(entries, corpus)
    return problems, (f"withdrawal register: {len(entries)} entr(y/ies) over "
                      f"{len(corpus)} live document(s)"
                      f"{' at ' + rev if rev else ''}")


def cmd_withdrawn(rev: str | None = None) -> int:
    entries, _ = load_register()
    print(f"REGISTER - {os.path.relpath(REGISTER_PATH, ROOT)}\n")
    for e in entries:
        print(f"  {e.get('id')}  withdrawn {e.get('withdrawn')}  ({e.get('kind')})")
        print(f"      {e.get('claim')}")
        print(f"      match {e.get('match')}  anchor {e.get('anchor')}")
        print(f"      instead: {e.get('replaced_by')}\n")
    problems, summary = _check_withdrawal_register(rev)
    print(summary + "\n")
    if not problems:
        print("no live document states a registered entry outside a block citing its id.")
        return 0
    print(f"{len(problems)} live restatement(s) or register defect(s):\n")
    for p in problems:
        print(f"  {p}")
    print("\nA retired figure resolves, agrees with every copy of itself, and reads as")
    print("established. That is why no consistency check can see it (#113).")
    return 1
# --------------------------------------------------------------------------- money unit
#
# EVERY DOLLAR FIGURE IN THIS PROJECT IS A LIST-PRICE VALUATION OF TOKENS on a
# subscription account, so no `$` here is an expenditure (#159). The token counts are
# real; the unit and the noun were not, and a research decision was declined on one.
#
# WHY THE TRIGGER IS THE PREDICATE AND NOT THE SIGIL. Requiring every `$` figure to be
# respelled would be a find-and-replace over `eval/RUNS.md`'s 132 per-run rows, which are
# the ledger a reader compares runs by; the unit belongs at the top of that file once, not
# beside each row. And a `$` is not always ours: `research/03-rust-engines.md` quotes W4
# Games' published console pricing, which is real money and must not be reddened.
#
# So the defect this gates is the NOUN: a live block that states one of these figures AND
# asserts money moved. That is a CLOSED class of English - the verbs and nouns of paying -
# and the choice between candidates was made on live-corpus counts, not on which sounded
# more general (AGENTS.md, the census-trigger rule):
#
#   | candidate trigger      | blocks hit | false positives |
#   |------------------------|-----------:|----------------:|
#   | `cost`/`costs`         |         39 |    many; `cost` is open class and mostly not about money |
#   | `price`/`priced`       |         15 |    hits W4 Games' real console pricing |
#   | `pay`/`pays`/`paid`    |          3 |    2 - "it paid for itself", "the numbers it paid for" |
#   | SHIPPED, without `pay` |         22 |    0 |
#
# `pay` was dropped for the two idioms, and it cost no true positive: the one real hit it
# had (`eval/RUNS.md`'s "money is spent") also carries `spent`. Measured 2026-08-23 over
# 55 live documents, before the repairs.
#
#: The closed class. Only what asserts an expenditure - `cost` and `price` are deliberately
#: absent, and the table above is why.
MONEY_PREDICATE = re.compile(
    r"\b(spend|spends|spent|spending|charged|charges|charging|"
    r"bill|billed|billing|expenditure|expenditures)\b", re.I)

#: A figure in the unit the project reports: `$` immediately followed by a digit.
MONEY_FIGURE = re.compile(r"\$[\d]")

#: The declaration that exempts a block. AN ID, NEVER A MARKER WORD, for the reason the
#: withdrawal register gives one screen up: a vocabulary is an enumeration, and one has
#: already failed here on a single inflection of one verb. A block that means to discuss
#: what the unit IS cites the finding that settled it.
MONEY_EXEMPTION = "#159"


def scan_money(corpus: dict[str, str]) -> list[str]:
    """Live blocks that state a token valuation and call it money."""
    problems = []
    for rel in sorted(corpus):
        lines = corpus[rel].split("\n")
        for a, b in _claim_blocks(lines):
            block = "\n".join(lines[a:b])
            if not (MONEY_FIGURE.search(block) and MONEY_PREDICATE.search(block)):
                continue
            if MONEY_EXEMPTION in block:
                continue
            words = sorted({w.lower() for w in MONEY_PREDICATE.findall(block)})
            problems.append(
                f"{rel}:{a + 1}: states a `$` figure and calls it {', '.join(words)}. "
                f"Every dollar figure here is a list-price valuation of tokens on a "
                f"subscription account (#159) - name the unit, or cite {MONEY_EXEMPTION} "
                f"in this block if the block is about the unit itself.")
    return problems


def _check_money_unit(rev: str | None = None) -> tuple[list[str], str]:
    """(problems, summary). Does a live document call a token valuation an expenditure?"""
    corpus, problems = _live_corpus(rev)
    problems = list(problems) + scan_money(corpus)
    return problems, (f"money-unit check: {len(corpus)} live document(s)"
                      f"{' at ' + rev if rev else ''}")


def _money_pins() -> list[str]:
    """Both directions, in memory, on strings whose answer is stated before it is measured.

    A trigger that returns 0 on a clean corpus is indistinguishable from one that cannot
    fire, which is the shape this file exists to catch. These run inside `--sweep`.
    """
    cases = [
        # (name, document text, should_be_red)
        ("a live doc calling a valuation spend",
         "The run spent $421.00 over eight trials.", True),
        ("... charged", "Ten judge calls were charged $31.66.", True),
        ("... billed", "The sweep was billed $60.00 against its ceiling.", True),
        ("... expenditure", "Total expenditure: $2,466.31.", True),
        ("a figure with no money noun",
         "The run used 421.00 tokval over eight trials.", False),
        ("a `$` figure with no money noun",
         "The eight trials come to $421.00 of token valuation.", False),
        ("a money noun with no figure",
         "Nothing here is spend, because nothing is charged per token.", False),
        (f"a block citing {MONEY_EXEMPTION} may say either",
         f"No $421.00 figure here was ever spend ({MONEY_EXEMPTION}).", False),
        ("an external vendor's real price is not ours to redden",
         "Console via W4 Games: Starter (<$300k rev) $800/yr single platform.", False),
        ("the exemption is scoped to the BLOCK, not the file",
         f"A paragraph about the unit ({MONEY_EXEMPTION}).\n\n"
         f"A separate paragraph that spent $421.00.", True),
    ]
    problems = []
    for name, text, want_red in cases:
        got_red = bool(scan_money({"pin.md": text}))
        if got_red != want_red:
            problems.append(
                f"money-unit pin `{name}`: expected {'RED' if want_red else 'green'}, "
                f"got {'RED' if got_red else 'green'}. The trigger no longer separates a "
                f"valuation named for what it is from one called an expenditure.")
    return problems


def cmd_money(rev: str | None = None) -> int:
    """`--money`: live documents that call a list-price token valuation an expenditure."""
    pins = _money_pins()
    problems, summary = _check_money_unit(rev)
    print(summary)
    print(f"trigger: {MONEY_PREDICATE.pattern}")
    print(f"exemption: a block citing {MONEY_EXEMPTION}\n")
    if pins:
        for q in pins:
            print(f"  PIN {q}")
        return 1
    if not problems:
        print("no live document states a `$` figure and calls it an expenditure.")
        return 0
    print(f"{len(problems)} live block(s):\n")
    for q in problems:
        print(f"  {q}")
    print("\nThe token counts are real and every comparison built on them stands. What is")
    print("wrong is the unit and the noun (#159).")
    return 1


def _index_pins(verbose: bool = False) -> list[str]:
    """Pin the FINDINGS-index checks in BOTH directions, against the real index.

    RUN BY `--sweep` ITSELF, every time, and separately as `--selftest` when you want to
    read the cases. A gate written while the repository is clean is a gate nobody has seen
    go red — `--sweep` was green on the real two-table split for as long as it stood — and
    a pin that has to be remembered is one that will be forgotten. This one costs
    microseconds and no I/O beyond re-reading a file the sweep already read, so it runs
    with the check rather than beside it.

    The mutations are applied to a COPY of the index text in memory. Nothing is written to
    `eval/FINDINGS.md`: it is the archive, and a selftest that edits it to prove a point is
    one crash away from leaving it edited.

    The GREEN cases are the half that matters most. A mutant asks whether a check can fail;
    only a variant asks whether it can still pass on an input it mishandles (AGENTS.md rule
    15), and both green cases here are inputs an earlier draft of this check got wrong: the
    blank line that legitimately ENDS the table after its last row, and a fenced example
    row that is not an index row at all.

    Returns the list of pins that came out wrong; empty means the check demonstrably both
    fires and stays quiet.
    """
    index_path = os.path.join(ROOT, "eval", "FINDINGS.md")
    if not os.path.exists(index_path):
        return [f"the FINDINGS-index pins found no index at {index_path}, so the index "
                f"checks are unproven - they cannot be shown to fire"]
    orig = open(index_path, encoding="utf-8", errors="replace").read()
    rows = _index_rows(orig)
    if len(rows) < 3:
        return [f"the FINDINGS-index pins parsed only {len(rows)} row(s) from "
                f"eval/FINDINGS.md - the row pattern has changed and the pins are "
                f"mutating nothing, so a green index check means nothing either"]
    body = {n for _, n in rows}
    mid = rows[len(rows) // 2]          # a row with rows on both sides of it
    first, last = rows[0], rows[-1]

    def with_line(at: int, text: str | None = None) -> str:
        """A copy of the index with `text` inserted at 1-based line `at`, or that line cut."""
        lines = orig.split("\n")
        if text is None:
            del lines[at - 1]
        else:
            lines.insert(at - 1, text)
        return "\n".join(lines)

    hi = max(body)

    def idx(text: str):
        return lambda: _check_index(text, body)

    def rng(text: str):
        return lambda: _check_range_in("AGENTS.md", text, hi)

    stated = f"Findings #19-#{hi}"
    cases = [
        ("committed index, unmutated", idx(orig), False),
        (f"blank line between the rows for #{mid[1]} and the next",
         idx(with_line(mid[0] + 1, "")), True),
        ("whitespace-only line between two rows (blank to CommonMark)",
         idx(with_line(mid[0] + 1, "   ")), True),
        ("prose line between two rows", idx(with_line(mid[0] + 1, "Added later.")), True),
        ("the |---|---| delimiter row deleted", idx(with_line(first[0] - 1)), True),
        ("blank line between the delimiter and the first row",
         idx(with_line(first[0], "")), True),
        (f"#{mid[1]} indexed on two rows - invisible to the set reconciliation",
         idx(with_line(mid[0] + 1, orig.split("\n")[mid[0] - 1])), True),
        ("GREEN: blank line after the LAST row, where the table legally ends",
         idx(with_line(last[0] + 1, "")), False),
        ("GREEN: an example row inside a ``` fence is not an index row",
         idx(orig + "\n```markdown\n| **7** | an example row |\n```\n"), False),
        # The stated range, which is spelled in three live files and drifted in two of them.
        (f"a doc stating the range one short (#{hi - 1})",
         rng(f"| `eval/FINDINGS.md` | Findings #19-#{hi - 1}, incl. retractions |"), True),
        ("a doc that states no range at all",
         rng("| `eval/FINDINGS.md` | the findings log |"), True),
        (f"GREEN: a doc stating the current range ({stated})",
         rng(f"| `eval/FINDINGS.md` | {stated}, incl. retractions |"), False),
        ("GREEN: a stale range inside a ``` fence is an example, not a claim",
         rng(f"{stated}\n\n```\nFindings #19-#42 from an old README\n```\n"), False),
    ]

    failed = []
    for name, run, expect_red in cases:
        got = run()
        good = bool(got) == expect_red
        if not good:
            failed.append(
                f"FINDINGS-index pin came out wrong: `{name}` produced {len(got)} "
                f"problem(s) where {'at least one' if expect_red else 'none'} was "
                f"expected. The check is no longer proven to "
                f"{'fire' if expect_red else 'stay quiet'}, so its green is not evidence.")
        if verbose:
            print(f"{'PASS' if good else 'FAIL'}  {name}: "
                  f"{len(got)} problem(s), expected {'>=1' if expect_red else '0'}")
            for g in got:
                print(f"        {g[:150]}")
    return failed


def _findings_census_pins(verbose: bool = False) -> list[str]:
    """Pin `findings_census` in both directions: does the count MOVE when the log does?

    THE QUESTION THIS ANSWERS, and why the range gate does not answer it. `_check_range_in`
    asks whether three documents name the highest finding. A range is not a count: `#19-#131`
    is true of a log with 113 entries and of one with 40, so a producer built on it can be
    green over a corpus it has lost 60% of. These cases move the CORPUS and ask whether the
    number follows.

    RED, and every one is a way the log has actually changed on a working day:
    a finding added to the bodies; added to bodies and index with the documents left behind;
    renumbered; defined twice (six collisions in one day, #94); a document's count one short;
    a count spelled in words; a range sentence duplicated by a merge.

    GREEN is the half that matters (rule 15). A mutant asks whether the producer can
    disagree; only a **correct addition** asks whether it can still agree afterwards - and if
    it cannot, the gate is unusable and gets deleted the first day someone writes a finding.

    Everything is a copy in memory. `eval/findings/` is the archive, and a selftest that
    plants a finding in it to prove a point is one crash away from having published one.
    """
    fdir = os.path.join(ROOT, "eval", "findings")
    index_path = os.path.join(ROOT, "eval", "FINDINGS.md")
    if not os.path.isdir(fdir) or not os.path.exists(index_path):
        return [f"the findings-census pins found no corpus at {fdir} / {index_path}, so "
                f"the producer is unproven - it cannot be shown to disagree with anything"]
    bodies = _body_findings(fdir)
    index = open(index_path, encoding="utf-8", errors="replace").read()
    rows = _index_rows(index)
    if len(bodies) < 3 or len(rows) < 3:
        return [f"the findings-census pins parsed {len(bodies)} bodie(s) and {len(rows)} "
                f"index row(s) - the patterns have changed and the pins are mutating "
                f"nothing, so a green census means nothing either"]

    hi, count = max(bodies), len(bodies)
    mid = sorted(bodies)[len(bodies) // 2]
    row_of = {n: ln for ln, n in rows}

    def doc(high: int, n: int, extra: str = "") -> dict[str, str]:
        """A live document stating a range and a count -- the shape README and AGENTS use."""
        return {"AGENTS.md": f"| `eval/FINDINGS.md` | Findings #19-#{high} |\n"
                             f"\n{n} numbered findings, and all but a few are one pattern.\n"
                             f"{extra}"}

    def with_row(after: int, num: int) -> str:
        """The index with a row for `num` inserted after the row for `after`."""
        lines = index.split("\n")
        lines.insert(row_of[after], f"| **{num}** | planted | [x](findings/x.md) |")
        return "\n".join(lines)

    added = {**bodies, hi + 1: ["certifies-nothing.md"]}
    renamed = {n: f for n, f in bodies.items() if n != mid}
    renamed[hi + 1] = bodies[mid]
    twice = {**bodies, mid: bodies[mid] + ["documentation.md"]}

    cases = [
        # --- GREEN: the corpus as committed, against documents that state it correctly
        (f"GREEN: the committed log - {count} findings, #19-#{hi}",
         (bodies, index, doc(hi, count)), False),
        # --- RED: the log moves
        ("a finding added to the bodies only",
         (added, index, doc(hi, count)), True),
        ("a finding added to the bodies AND the index, documents left behind",
         (added, with_row(hi, hi + 1), doc(hi, count)), True),
        (f"#{mid} renumbered to #{hi + 1} in the bodies",
         (renamed, index, doc(hi, count)), True),
        (f"#{mid} defined in two files - the collision that happened six times in a day",
         (twice, index, doc(hi, count)), True),
        # --- RED: the documents drift
        ("a document stating the count one short",
         (bodies, index, doc(hi, count - 1)), True),
        ("a document stating the count in words, as README did to #131",
         (bodies, index, {"README.md": f"Findings #19-#{hi}\n\nThirty-seven numbered "
                                       f"findings, and all but a few are one pattern."}),
         True),
        ("a document stating the range twice - what an evil merge did on 2026-08-23",
         (bodies, index, {"AGENTS.md": f"| Findings #19-#{hi} |\n| Findings #19-#{hi} |\n"
                                       f"\n{count} numbered findings.\n"}), True),
        # --- GREEN: the variants. Can it still agree on inputs it must not fire on?
        (f"GREEN: a finding added EVERYWHERE - bodies, index and documents at #{hi + 1}",
         (added, with_row(hi, hi + 1), doc(hi + 1, count + 1)), False),
        ("GREEN: a stale count inside a ``` fence is an example, not a claim",
         (bodies, index, doc(hi, count, extra="```\n37 numbered findings\n```\n")), False),
        ("GREEN: `the numbered findings` - a determiner is not a cardinal",
         (bodies, index, doc(hi, count, extra="All of the numbered findings resolve.\n")),
         False),
        # --- task 179: the count check was bound to ONE wording, and a figure 28 short
        # survived beside its own producer. These pass `counted` explicitly, which is also
        # what proves the count corpus is separate from the three RANGE_DOCS.
        ("THE REAL DEFECT, in shape: a count 28 short in the `entries` wording with "
         "`docstat.py --findings` named in the same sentence, which is README.md line 187 "
         "on 2026-08-27 - `143 entries` against a measured 171",
         (bodies, index, doc(hi, count),
          {"README.md": f"| What went wrong? | [`eval/FINDINGS.md`](eval/FINDINGS.md) - "
                        f"{count - 28} entries. Findings #19-#{hi}, count and range from "
                        f"`python3 eval/tools/docstat.py --findings` |\n"}),
         f"names the findings log and states `{count - 28} entries`"),
        ("a stale count in a live document that is NOT in RANGE_DOCS - unreachable by the "
         "gate until the count corpus was widened",
         (bodies, index, doc(hi, count),
          {".agents/skills/update-readme/SKILL.md":
           f"The log holds {count - 1} separate numbered entries "
           f"(`docstat.py --findings`).\n"}),
         "names the findings log and states"),
        # GREEN, and these are the half that matters (rule 15): every one is a real live
        # line that names the findings log and carries a number which is not the count.
        # The scoped trigger's quantifier half, run unscoped over the live corpus, reds 6
        # correct lines; scoped it reds none of these.
        ("GREEN: a LINE NUMBER inside the log's own path",
         (bodies, index, doc(hi, count),
          {"DECISIONS.md": "an edit left its last line stranded at line 6 of "
                           "`eval/FINDINGS.md`, the file every session reads first.\n"}),
         False),
        ("GREEN: `1 hit` beside the log's path - a singular noun is not a count",
         (bodies, index, doc(hi, count),
          {"DECISIONS.md": "| `1f6fb65:eval/FINDINGS.md:6` | 1 hit | **0** |\n"}), False),
        ("GREEN: a cardinal and a plural noun in DIFFERENT table cells",
         (bodies, index, doc(hi, count),
          {"DECISIONS.md": "| `!eval/findings/**`, `!eval/FINDINGS.md` | 10 | archives. A "
                           "figure proven wrong **stays** there |\n"}), False),
        ("GREEN: a DATE on a line naming the producer",
         (bodies, index, doc(hi, count),
          {"DECISIONS.md": "### The producer for the findings count is "
                           "`docstat.py --findings` - decided 2026-08-23\n"}), False),
        ("GREEN: the count stated correctly in the `entries` wording",
         (bodies, index, doc(hi, count),
          {"README.md": f"[`eval/FINDINGS.md`](eval/FINDINGS.md) - {count} entries. "
                        f"Findings #19-#{hi}, from `docstat.py --findings`\n"}), False),
        ("GREEN: a stale count beside the log INSIDE a ``` fence - an example, not a claim",
         (bodies, index, doc(hi, count),
          {"DECISIONS.md": f"Planted as:\n\n```\n{count - 28} entries. Findings "
                           f"#19-#{hi}\n```\n\nand it went red.\n"}), False),
    ]

    failed = []
    for name, payload, expect_red in cases:
        b, ix, st, ct = payload + (None,) * (4 - len(payload))
        got = findings_census(b, ix, st, counted=ct)["disagreements"]
        # `expect_red` may be a SUBSTRING rather than True. A red case is only controlling
        # the mechanism it names if the disagreement it produced is that mechanism's -
        # three mutants once survived here because another check happened to fire on the
        # same input, which reads exactly like a pass.
        good = bool(got) == bool(expect_red)
        if good and isinstance(expect_red, str):
            good = any(expect_red in g for g in got)
            if not good:
                name += f" [no disagreement contained `{expect_red}`]"
        if not good:
            failed.append(
                f"findings-census pin came out wrong: `{name}` produced {len(got)} "
                f"disagreement(s) where {'at least one' if expect_red else 'none'} was "
                f"expected. The producer is no longer proven to "
                f"{'notice a change' if expect_red else 'accept a correct log'}, so its "
                f"count is not evidence.")
        if verbose:
            print(f"{'PASS' if good else 'FAIL'}  {name}: "
                  f"{len(got)} disagreement(s), expected {'>=1' if expect_red else '0'}")
            for g in got:
                print(f"        {g[:150]}")
    return failed


def _citation_census_pins(verbose: bool = False) -> list[str]:
    """Pin `citation_census` in both directions, on text built in memory (task 118).

    WHY A PRODUCER THAT GATES NOTHING NEEDS PINS AT ALL. Its output is a NUMBER someone
    will quote, and #146 is the finding about a number quoted with no producer behind it.
    An extractor that has silently stopped matching reports 0 rows over a full corpus, and
    0 is also what a clean corpus reports - the ambiguity this project keeps paying for.

    Every case asserts an EXACT count, not merely "some" or "none". Rows and matches are
    different quantities, and #146's own correction note conflated them; a pin that only
    asked `bool(rows)` would have been green through exactly that mistake.

    THE RED CASE THAT MATTERS is `eval/RUNS.md`'s `(#17)`, quoted as it stood before task
    112 repaired it - a row whose true value is known in advance (rule 12's corollary).
    Today's live corpus contains no true positive at all, so without this pin the extractor
    would be proven only against text nobody has adjudicated.

    THE GREEN HALF IS THE HALF THAT MATTERS (rule 15), and here it is the half no
    live-corpus measurement could have produced. A bare `#(\\d+)` reds exactly two of these
    - the anchor slug and the colour - while returning the same 51 matches on 45 lines as
    the shipped extractor over the corpus at `24bc9af`, because every anchor there carries
    an in-range number. **The totals agree and the tokenisation does not**, so the corpus
    cannot choose between the two extractors and these cases have to. The fence case is not
    about the regex at all: it pins a decision `citation_census` makes around it.
    """
    lo, hi = 19, 152
    anchor = "See [the subjective layer](eval/FINDINGS.md#3-the-subjective-layer)."
    cases = [
        # --- RED: a number that names no finding, in a live document
        ("the real (#17) in eval/RUNS.md, before task 112 repaired it",
         {"eval/RUNS.md": "whether 2.15x is a property of rust or of our gate is open "
                          "(#17)\n"}, 1, 1),
        ("the fabricated (#999) #146 planted as its control",
         {"DECISIONS.md": "A fabricated citation planted for a control (#999).\n"}, 1, 1),
        ("TWO out-of-range numbers on ONE line - matches and rows differ here",
         {"AGENTS.md": "Tasks #14/#15 were marked complete having guarded the capture.\n"},
         2, 1),
        ("a range whose LOW end names no finding - the hyphen continues a range",
         {"README.md": f"Findings #5-#{hi} are the log.\n"}, 1, 1),
        # --- GREEN: inputs it must not fire on
        ("GREEN: in-range citations, including both endpoints",
         {"AGENTS.md": f"See #{lo}, #{(lo + hi) // 2} and #{hi}.\n"}, 0, 0),
        ("GREEN: the published range spelled as a range",
         {"README.md": f"Findings #{lo}-#{hi}, including retractions.\n"}, 0, 0),
        ("GREEN: a markdown ANCHOR slug, which a bare #(\\d+) reads as a citation",
         {"README.md": anchor + "\n"}, 0, 0),
        ("GREEN: a colour, which a bare #(\\d+) reads as a citation of #1",
         {"eval/PROTOCOL.md": "The overlay is drawn in #1a2b3c on #0f0f0f.\n"}, 0, 0),
        ("GREEN: a ``` fence - an EXAMPLE of a citation is not one",
         {"DECISIONS.md": "Planted as:\n\n```\na dangling (#999)\n```\n\nand it went "
                          "red.\n"}, 0, 0),
        ("GREEN: an empty document",
         {"README.md": ""}, 0, 0),
    ]

    failed = []
    for name, corpus, want_matches, want_rows in cases:
        c = citation_census(corpus, lo, hi)
        good = (c["matches"], c["lines"]) == (want_matches, want_rows)
        if not good:
            failed.append(
                f"citation-census pin came out wrong: `{name}` produced "
                f"{c['matches']} match(es) on {c['lines']} line(s) where "
                f"{want_matches} on {want_rows} was expected. The extractor has moved, so "
                f"any count `--citations` prints is unproven.")
        if verbose:
            print(f"{'PASS' if good else 'FAIL'}  {name}: {c['matches']} match(es) on "
                  f"{c['lines']} line(s), expected {want_matches} on {want_rows}")

    # THE ADDRESS, checked rather than promised (#60). The census is defined over LIVE
    # documents, and every figure it prints is wrong by the size of the archive if the
    # archive leaks in. `eval/FINDINGS.md` alone would contribute hundreds of rows.
    for rel, want_archive in (("eval/FINDINGS.md", True), ("eval/findings/x.md", True),
                              ("tasks/118-x.md", True), ("README.md", False),
                              ("eval/RUNS.md", False)):
        got = is_archive(rel)
        if got != want_archive:
            failed.append(
                f"citation-census population is wrong at the address: ARCHIVE_PATHS now "
                f"classifies `{rel}` as {'archive' if got else 'LIVE'} where "
                f"{'archive' if want_archive else 'live'} is expected. Every count over "
                f"this corpus is wrong by whatever that document holds.")
    return failed


def _aspect_census_pins(aspects: set[str], verbose: bool = False) -> list[str]:
    """Pin `_check_aspect_census` in both directions, on planted text, every sweep.

    The RED cases are the two real documents this check was written for, quoted as they
    stood at 7e82b19, plus the phrasings task 92 measured the old three-alternation
    trigger MISSING - it caught 2 of 14 planted false censuses, and every one below was
    among the 12 that passed.

    The GREEN cases are the half that matters (AGENTS.md rule 15). Every one is REAL
    CORPUS TEXT that a draft of this trigger turned red: four from the 2026-08-22 draft
    (the sibling check's own sentence, the `5 aspects x 2 orders` run description, the
    singular `every aspect`, an archive doc), and five from task 92's quantifier-based
    draft, which produced 26 false positives and no true ones. A mutant asks whether the
    check can fail; only these ask whether it can still pass on the inputs that made
    every previous draft unusable.

    Returns the pins that came out wrong; empty means the check demonstrably both fires
    and stays quiet.
    """
    if not aspects:
        return []  # the check itself already reports an empty id set
    all_six = ", ".join(f"`{a}`" for a in sorted(aspects))
    five = ", ".join(f"`{a}`" for a in sorted(aspects) if a != "fun_frames")
    one = sorted(aspects)[0]
    far = "\n".join(["filler"] * (_ASPECT_CENSUS_WINDOW + 2))

    cases = [
        # --- RED
        ("the pre-fix skill sentence: claims exhaustive, names five of six",
         {"a.md": f"The five aspects that exist are {five}."}, True),
        ("a claim followed by a table that drops one id",
         {"a.md": f"Six aspects exist.\n\n| aspect id | sees |\n|---|---|\n"
                  + "".join(f"| `{a}` | code |\n" for a in sorted(aspects) if a != one)},
         True),
        ("all six named, but one of them past the window",
         {"a.md": f"Six aspects exist: {five}.\n{far}\n`fun_frames`"}, True),
        ("RUBRIC's own exhaustiveness phrasing, five named",
         {"a.md": f"These five exist. The ids `--aspects` accepts: {five}."}, True),
        # --- RED: the wordings the three-alternation trigger missed (task 92)
        ("task 92 #A: plain copula - `The five judge aspects are ...`",
         {"a.md": f"The five judge aspects are **{five}**."}, True),
        ("task 92 #B: existential - `There are five aspects: ...`",
         {"a.md": f"There are five aspects: {five}."}, True),
        ("task 92 #C: a forward reference - `the six aspects are listed below`",
         {"a.md": f"the six aspects are listed below\n\n{five}"}, True),
        ("task 92 #D: completeness noun - `The full list of aspects is ...`",
         {"a.md": f"The full list of aspects is {five}."}, True),
        ("task 92 #I: completeness noun - `The complete set of aspects is ...`",
         {"a.md": f"The complete set of aspects is {five}."}, True),
        ("task 92 #F: exclusion - `... There are no other aspects.`",
         {"a.md": f"The judge aspects: {five}. There are no other aspects."}, True),
        ("task 92 #G: enumeration punctuation - `all five aspects: ...`",
         {"a.md": f"all five aspects: {five}"}, True),
        ("task 92 #H: a dash instead of a colon - `the five aspects - ... -`",
         {"a.md": f"Each of the five aspects - {five} - is judged."}, True),
        ("task 92 #J: definition by source - `aspects.py defines five aspects: ...`",
         {"a.md": f"`aspects.py` defines five aspects: {five}"}, True),
        ("task 92 #L: universal + membership - `every aspect is one of ...`",
         {"a.md": f"Every aspect is one of these five: {five}."}, True),
        ("task 92 #M: adverbial - `The aspects, in full: ...`",
         {"a.md": f"The aspects, in full: {five}."}, True),
        # --- GREEN
        (f"GREEN: the same claim naming all {len(aspects)}",
         {"a.md": f"The aspects that exist are {all_six}."}, False),
        ("GREEN: a stale census inside a ``` fence is an example, not a claim",
         {"a.md": f"```\nThe five aspects that exist are {five}.\n```"}, False),
        ("GREEN: a run description - `5 aspects x 2 orders` counts what RAN",
         {"a.md": "10 usable rounds, 5 aspects x 2 presentation orders, 8 submissions."},
         False),
        ("GREEN: the sibling check described - singular `aspect`, about naming",
         {"a.md": "| **references** | does a flag, aspect or criterion a doc names "
                  "actually exist? |"}, False),
        ("GREEN: singular quantifier over a subset - `every aspect that reads them`",
         {"a.md": "The frames are not equivalent across arms, and every aspect that "
                  "reads them is told so."}, False),
        ("GREEN: an archive doc whose subject IS the superseded census",
         {"tasks/79-x.md": f"says five aspects exist: {five}"}, False),
        # --- GREEN: real live-corpus lines the quantifier-based draft turned red.
        # These are the whole reason the trigger is scoped to the predicate.
        ("GREEN: JUDGING.md - `which aspects are included:` restricts, never declares",
         {"a.md": "And the ordering is not stable to which aspects are included:\n\n"
                  "| aspects pooled | ordering |\n|---|---|\n| all five | rust, godot |"},
         False),
        ("GREEN: DECISIONS.md - `All five aspects were run` counts a ROUND",
         {"a.md": "All five aspects were run over a full eight-submission field for "
                  f"**$33.63** - naming `{one}` among them."}, False),
        ("GREEN: G4-PLATFORMER.md - `All five aspects failed their gates`",
         {"a.md": "**But do not budget for it.** All five aspects failed their gates "
                  "on `g2_tetris3d` - three of them at the ceiling."}, False),
        ("GREEN: JUDGING.md - `ALL SIX aspects separate g4_platformer at n=5`",
         {"a.md": "## Task 23 result: ALL SIX aspects separate `g4_platformer` at n=5."},
         False),
        ("GREEN: RUNS.md - `six aspects x 5 repeats` is a design, not a census",
         {"a.md": "Task 23: six aspects x 5 repeats of one field, 30 calls, $100.84."},
         False),
        ("GREEN: RUNS.md - `a pooled mean over all aspects` prices, never enumerates",
         {"a.md": "A pooled per-call mean over all aspects would have priced "
                  f"`{one}` at a third of its cost."}, False),
        ("GREEN: a per-aspect RESULTS table over the subset one round ran",
         {"a.md": "| aspect | seed | range | reads as |\n|---|---|---|---|\n"
                  f"| `{one}` | 0 | 0.25 | flat |"}, False),
    ]

    failed = []
    for name, corpus, expect_red in cases:
        got = _check_aspect_census(corpus, aspects)
        good = bool(got) == expect_red
        if not good:
            failed.append(
                f"aspect-census pin came out wrong: `{name}` produced {len(got)} "
                f"problem(s) where {'at least one' if expect_red else 'none'} was "
                f"expected. The check is no longer proven to "
                f"{'fire' if expect_red else 'stay quiet'}, so its green is not evidence.")
        if verbose:
            print(f"{'PASS' if good else 'FAIL'}  {name}: "
                  f"{len(got)} problem(s), expected {'>=1' if expect_red else '0'}")
            for g in got:
                print(f"        {g[:150]}")
    return failed


def _size_mtime(path: str) -> tuple[int, int] | None:
    if not os.path.exists(path):
        return None
    st = os.stat(path)
    return (st.st_size, st.st_mtime_ns)


def _bare_flag_pins(verbose: bool = False) -> list[str]:
    """Pin the BARE fenced-flag check in both directions (task 89).

    The clean corpus returns 0 hits from this trigger, and 0 is exactly the reading a
    check that cannot fire produces. That ambiguity is the defect this project keeps
    finding, so the pins run inside `--sweep` rather than in a command someone has to
    remember.

    THE GREEN HALF IS THE HALF THAT MATTERS (AGENTS.md rule 15). A mutant only asks
    whether the check can fail. Four cases below are inputs an earlier draft of this
    trigger got WRONG, each found by measurement rather than by reading -- three green,
    one red:

      GREEN  a pipe to `grep --color=auto`   the broad candidate reported `--color`. 8
                                             such hits on the live corpus, 0 of them true.
                                             The shell-operator cut is why.
      GREEN  `cargo doc --open -p bevy`      a fenced line owning no script of ours.
      GREEN  a bare flag in PROSE            out of scope on purpose: measured at 2 false
                                             positives and 0 true over the same corpus. If
                                             someone widens the trigger to all lines, this
                                             pin goes red and says so.
      RED    a backticked SCRIPT NAME with   deleting backticked spans removed the script
             its flag written bare           name and the line went quiet -- a false
                                             negative created by the substitution meant to
                                             prevent a double report. Blanking to
                                             equal-length spaces is the fix, and this case
                                             is what notices it regressing.

    A function of its inputs, never of the repository, so nothing here reads or writes a
    file. Returns the pins that came out wrong; empty means the check demonstrably both
    fires and stays quiet.
    """
    scripts = _our_script_names()
    if not scripts:
        return ["the bare-flag pins found no argparse-owning script in eval/, so the "
                "bare fenced-flag check is matching nothing and its green means nothing"]
    real = _argparse_flags()
    if "--sweep" not in real:
        return ["the bare-flag pins could not find --sweep among this repo's argparse "
                "flags, so the green cases below prove nothing about resolution"]

    def hits(body: str) -> list[str]:
        """What the check reports for a document made of `body`, foreign/known filtered."""
        out = []
        for tok in _bare_fenced_flags(body.split("\n"), scripts):
            if tok.startswith(FOREIGN_FLAG_PREFIXES) or tok in FOREIGN_FLAGS_EXACT or tok in real:
                continue
            out.append(tok)
        return out

    def fence(*cmd: str) -> str:
        return "```\n" + "\n".join(cmd) + "\n```\n"

    cases = [
        # RED: a phantom flag in every shape a usage block is really written in.
        ("the ticket's own case: a bare phantom after our script in a fence",
         fence("python3 judge/runner.py --no-such-flag-bare1"), True),
        ("bare phantom alongside a REAL flag of ours",
         fence("python3 tools/docstat.py --sweep --no-such-flag-bare2"), True),
        ("bare phantom written with an = value",
         fence("python3 tools/docstat.py --no-such-flag-bare3=7"), True),
        ("bare phantom on an indented fenced line",
         fence("  $ python3 judge/runner.py --no-such-flag-bare4"), True),
        ("bare phantom after a script named with its full path",
         fence("python3 eval/tools/wholegame.py report --no-such-flag-bare5"), True),
        ("script backticked, flag bare - the offset-preserving blank",
         fence("`judge/runner.py` --no-such-flag-bare6"), True),

        # GREEN: inputs the check must still pass. Four are measured mistakes.
        ("GREEN: a real flag of ours, bare in a fence",
         fence("python3 tools/docstat.py --sweep"), False),
        ("GREEN: another tool's flag AFTER a pipe from our script",
         fence("python3 tools/docstat.py --sweep | grep --color=auto"), False),
        ("GREEN: another tool's flag after a ; from our script",
         fence("python3 tools/docstat.py --sweep ; ls --no-such-thing"), False),
        ("GREEN: a fenced line naming no script of ours",
         fence("cargo doc --open -p bevy"), False),
        ("GREEN: a known-foreign flag on one of our own command lines",
         fence("python3 tools/wholegame.py run --max-turns 250"), False),
        # FOREIGN_FLAGS_EXACT, both directions. The three gh flags are exempt by EQUALITY,
        # so a flag of ours that merely starts with one is still caught -- the widening a
        # prefix entry would have bought silently, and the reason the exact set exists.
        ("GREEN: an exactly-exempt foreign flag on our command line",
         fence("python3 tools/docstat.py --sweep --jq ."), False),
        ("GREEN: the prefix entries still match by prefix",
         fence("python3 tools/wholegame.py run --max-budget-usd 40"), False),
        ("a flag of ours merely PREFIXED by an exactly-exempt one",
         fence("python3 tools/docstat.py --jq-local"), True),
        ("another one, so the pin is not about a single token",
         fence("python3 tools/docstat.py --paginated"), True),
        # The flag must come AFTER the script name here, or this pin is unmoved by the
        # mutant that drops the fence requirement and it guards nothing. Written the
        # other way round first, and the mutant sailed through it: the check reads the
        # tail of a line after the script name, so a flag placed BEFORE the name is
        # invisible whether the fence rule is present or not, and the pin passed for a
        # reason that had nothing to do with what it claimed to test.
        ("GREEN: the same phantom UNFENCED - prose is out of scope, measured",
         "Run judge/runner.py --no-such-flag-prose to reproduce it.\n", False),
        ("GREEN: a line declaring the name deliberately fake exempts itself",
         fence("python3 judge/runner.py --no-such-flag-x   # phantom"), False),
        ("GREEN: a backticked phantom in a fence - the other half's job, not this one's",
         fence("python3 judge/runner.py `--no-such-flag-bare7`"), False),
        ("GREEN: an empty document", "", False),
    ]

    failed = []
    for name, body, expect_red in cases:
        got = hits(body)
        good = bool(got) == expect_red
        if not good:
            failed.append(
                f"bare fenced-flag pin came out wrong: `{name}` produced {len(got)} "
                f"hit(s) {got} where {'at least one' if expect_red else 'none'} was "
                f"expected. The check is no longer proven to "
                f"{'fire' if expect_red else 'stay quiet'}, so its green is not evidence.")
        if verbose:
            print(f"{'PASS' if good else 'FAIL'}  {name}: {len(got)} hit(s) {got}, "
                  f"expected {'>=1' if expect_red else '0'}")
    return failed


# THE BOUNDARY IS DELIBERATELY LOOSE, and it is load-bearing rather than sloppy.
# `wholegame\.py` unanchored is the only alternative that admits a document naming
# `eval/judge/regrade_wholegame.py`, which is one of this repository's own harnesses and
# appears in 8 places across the reference corpus. Requiring a complete path component -
# the obvious tightening, raised by CodeRabbit on PR #29 - drops it, and buys nothing
# measurable in exchange: over the reference corpus the tightened form changes admission
# for 0 documents, and the near-misses it exists to exclude (`myrunner.py`, `runner.pyc`)
# occur 0 times. Both directions are pinned in `_skill_flag_pins()`.
#
# THE `judge/` ALTERNATIVE IS INERT and every write-up here says 4 names for that reason:
# the `\.py` applies to the whole group, so it requires the literal text `judge/.py`,
# which occurs 0 times. `eval/judge/blind_dir.py` does not admit through it. Recorded
# rather than repaired, because making it mean `judge/<anything>.py` would WIDEN the
# trigger and move every published figure below, which needs its own re-adjudication.
HARNESS_TRIGGER = re.compile(r"(wholegame|runner|judge/|evaluate|regrade)\.py")


def _backticked_flags(text: str, flags: set[str], is_skill: bool = False) -> set[str]:
    """Backticked `--flag` tokens in one document that match no argparse of ours.

    Only flags this repo's own harnesses would own, so the check is gated on
    `HARNESS_TRIGGER` - a FILE-WIDE search for 4 harness script names - OR on the document
    being a skill. An ordinary document naming neither is naming someone else's flags, and
    checking those produced 40 false positives on the first run of this sweep.

    LINE-SCOPED EXEMPTION, so a line can exempt itself the way the aspect check allows.
    It could not before, and on 2026-08-23 that turned the sweep red for a correct
    document: task 77's own write-up names the phantom flag it PLANTED as a control, in a
    file that also mentions `judge/runner.py`. A gate that fails on correct input is a gate
    that gets disabled - the reason recorded twice already in this file.

    NOT FENCE-EXEMPT, and the asymmetry with the aspect check is deliberate. The aspect
    rule reasons that a fenced line is a command and asserts nothing about its own
    arguments; that does not transfer here, because a fenced command line is exactly where
    someone COPIES a flag.

    THIS HALF SEES ONLY INLINE CODE, measured 2026-08-23 rather than assumed, and the
    prediction was wrong before the controls corrected it: the pattern requires BACKTICKS.
    A backticked flag inside ``` is caught (no fence exemption); a BARE one on a fenced
    command line was invisible - the ordinary way a usage block is written, and the
    highest-damage place a phantom flag can sit, because it is the text a reader copies and
    pastes. That was task 89, and `_bare_fenced_flags()` covers it with its own trigger and
    its own false-positive measurement; read its docstring before changing either half.

    EVERY SKILL IS ADMITTED, and the reason is a measurement that MOVED.
    ------------------------------------------------------------------
    Skills are where commands and flags are most densely written, and the harness trigger
    read only the 4 that happen to name one. On 2026-08-25 the other 6 were about to be
    recorded as a deliberate exclusion, because admitting them cost 8 correct lines and
    bought 0 genuine hits - `gh`, `git` and `just` flags argued about in prose, which is
    the shape `AGENTS.md` says never to widen a gate into.

    All 9 of those tokens then entered `FOREIGN_FLAGS_EXACT` on `main` (6bfc80b) for an
    unrelated reason: ticket prose was reddening the sweep with the same foreign flags. The
    cost of admitting every skill fell to 0 rows the moment that landed, and an exclusion
    argued from a cost of 8 does not survive the cost becoming 0.

    THE ASYMMETRY IS THE ARGUMENT, and it is worth keeping: the exemptions are the
    fail-open half and they were paid for regardless; widening the trigger is the
    fail-closed half. Declining the coverage would have paid the price and taken nothing
    for it.

    Measured over the skills corpus, 2026-08-25, after that merge. `reads` is how many of
    the 29 backticked mentions of a real flag of ours a trigger would look at; `rows` is
    how many correct lines it turns red:

      trigger                                     reads   rows
      the retired 4 harness names, file-wide       10/29     0
      one of our scripts named on the same line     2/29     0
      one of our scripts in the same section       26/29     0
      SHIPPED: every skill                         29/29     0

    Every candidate now costs nothing, so recall decides, and admitting every skill has
    all of it. `_skill_flag_coverage()` is the producer and recounts this live;
    `_skill_flag_pins()` drives this function over both sides of the old split, so if a
    row ever costs something again it is a red pin rather than a silent regression.

    WHAT IS STILL EXCLUDED, and it is not the skills. An ordinary document naming none of
    the 4 harness scripts is still unread by this half. Widening THAT to the closed class
    `_our_script_names()` is measured by `_harness_trigger_census()` and still loses - 13
    candidate rows over the reference corpus, 11 of them in `tasks/`, which is an archive.
    `.agents/skills/audit-docs/SKILL.md` states both halves for its readers.
    """
    if not (is_skill or HARNESS_TRIGGER.search(text)):
        return set()
    bad: set[str] = set()
    for ln in text.split("\n"):
        if re.search(_DELIBERATELY_FAKE, ln, re.I):
            continue
        for tok in re.findall(r"`(--[a-z0-9-]{2,})`", ln):
            if tok.startswith(FOREIGN_FLAG_PREFIXES) or tok in FOREIGN_FLAGS_EXACT or tok in flags:
                continue
            bad.add(tok)
    return bad


def _skill_flag_coverage(skills: list[str] | None = None) -> dict:
    """What each candidate trigger would read across the skills, and what it would cost.

    THE PRODUCER for the table in `_backticked_flags()`'s docstring, for the entry in
    `DECISIONS.md` and for the row in `.agents/skills/audit-docs/SKILL.md`. A count with no
    producer goes stale forever, so these are recomputed on the live corpus every
    `--selftest`.

    `reads` counts backticked mentions of flags that DO resolve - the population each
    candidate trigger would look at, which is the recall half of the choice. `rows` counts
    the tokens that do not resolve - the cost half. Both are needed: a trigger can be cheap
    because it reads almost nothing, and the line-scoped one is. `harness_only` is the set
    of skills the RETIRED trigger did not admit, kept because the shipped one is only
    defensible while those rows cost nothing.

    IT REPORTS CANDIDATES, NOT VERDICTS, for the same reason `_harness_trigger_census()`
    does. The only exclusions applied are the ones the check itself applies, so a genuinely
    unresolved flag of ours appears here exactly as a `gh` flag does. Calling the list
    false positives in the OUTPUT would be a reason not to count a failure (`AGENTS.md`
    rule 7).

    `skills` exists for the pins that drive this over a synthetic corpus.
    """
    flags, scripts = _argparse_flags(), _our_script_names()
    wide_rx = re.compile(r"\b(" + "|".join(re.escape(s) for s in sorted(scripts)) + r")\b")
    skills = _all_skill_files() if skills is None else skills
    triggers = ("harness", "line", "section", "shipped")
    reads = {t: 0 for t in triggers}
    rows: dict[str, set[str]] = {t: set() for t in triggers}
    mentions = 0
    unread: list[str] = []

    for q in skills:
        rel = os.path.relpath(q, ROOT)
        text = open(q, encoding="utf-8", errors="replace").read()
        lines = text.split("\n")
        narrow = bool(HARNESS_TRIGGER.search(text))
        if not narrow:
            unread.append(rel)
        # Section = from one ATX heading to the next. Numbered rather than keyed by title,
        # so two sections that happen to share a heading cannot merge into one.
        #
        # FENCE-AWARE, and via the one `_fence_mask()` every structure check here shares.
        # A `#` inside ``` is a shell comment, and these documents are full of them: 31 of
        # the 130 lines starting with `#` across the 10 skills are fenced. Counting those
        # as headings splits real sections, which moves a flag away from the harness name
        # that governs it and silently understates the section trigger's reach - the
        # figure this producer publishes. Raised by CodeRabbit on PR #29.
        fenced = _fence_mask(lines)
        sec, sec_of = 0, []
        for i, ln in enumerate(lines):
            if not fenced[i] and _ATX_HEADING.match(ln):
                sec += 1
            sec_of.append(sec)
        named = {sec_of[i] for i, ln in enumerate(lines) if wide_rx.search(ln)}
        for i, ln in enumerate(lines):
            toks = re.findall(r"`(--[a-z0-9-]{2,})`", ln)
            # The deliberately-fake exemption drops the whole LINE, exactly as
            # `_backticked_flags()` does, and it is applied before anything is counted.
            # Counting a resolving flag from a line the check never reads would inflate
            # `mentions` and every `reads` alongside it, so the recall figures would
            # describe a population the check does not have. 0 such lines in the live
            # skills today; the pins drive a fixture that has one. Raised by CodeRabbit
            # on PR #29.
            if not toks or re.search(_DELIBERATELY_FAKE, ln, re.I):
                continue
            fires = {"harness": narrow, "line": bool(wide_rx.search(ln)),
                     "section": sec_of[i] in named, "shipped": True}
            for tok in toks:
                if tok in flags:
                    mentions += 1
                    for t in triggers:
                        reads[t] += fires[t]
                    continue
                if tok.startswith(FOREIGN_FLAG_PREFIXES) or tok in FOREIGN_FLAGS_EXACT:
                    continue
                for t in triggers:
                    if fires[t]:
                        rows[t].add(f"{rel}: {tok}")
    return {"skills": len(skills), "harness_only": sorted(unread), "mentions": mentions,
            "reads": reads, "rows": {t: sorted(rows[t]) for t in triggers}}


def _published_skill_figures(cov: dict) -> list[tuple[str, str]]:
    """The sentences the live census forces three documents to be saying.

    Every figure in the coverage table is published as prose in `_backticked_flags`'s own
    docstring, in `DECISIONS.md` and in `.agents/skills/audit-docs/SKILL.md`. A count with
    a producer goes stale for an hour and a count with none goes stale forever - but so
    does one whose producer nothing compares it against, which is what these are for.
    Change what the trigger reads, or let a candidate start costing rows, and the phrase
    built here stops matching: the pin reddens and the prose has to be re-measured rather
    than left standing. Raised by CodeRabbit on PR #29.

    Built from the live census and searched for, rather than copied into the documents and
    trusted: the expectation and the fact stay two objects with a row comparing them, which
    is what a control that imports its expectation from its subject does not have
    (task 113).
    """
    m, reads, rows = cov["mentions"], cov["reads"], cov["rows"]
    table = [("the retired 4 harness names, file-wide", "harness"),
             ("one of our scripts named on the same line", "line"),
             ("one of our scripts in the same section", "section"),
             ("SHIPPED: every skill", "shipped")]
    out = [("eval/tools/docstat.py", f"{label} {reads[t]}/{m} {len(rows[t])}")
           for label, t in table]
    out += [("DECISIONS.md", f"| {label} | {reads[t]}/{m} | {len(rows[t])} |")
            for label, t in table]
    out += [("DECISIONS.md",
             f"reads all {cov['skills']} `SKILL.md` files, at a cost of "
             f"{len(rows['shipped'])} correct lines"),
            (".agents/skills/audit-docs/SKILL.md",
             f"all {cov['skills']} skills"),
            (".agents/skills/audit-docs/SKILL.md",
             f"reads {reads['shipped']} of the {m} backticked flag mentions")]
    return out


def _skill_flag_pins(verbose: bool = False) -> list[str]:
    """Skills are read, and the widening that admitted them still costs nothing.

    THE COVERAGE AND ITS PRICE ARE THE SAME PIN. `_backticked_flags()` admits every skill
    because the 9 foreign tokens its prose argues about are in `FOREIGN_FLAGS_EXACT`, which
    took the cost of admitting them from 8 correct lines to 0. That is a live property, not
    a fact: a skill that discusses a new tool's flag reddens the sweep on correct input,
    which is how a gate gets disabled. So the pins hold BOTH - that a phantom flag in a
    skill is caught, and that no candidate trigger costs a row - and every published figure
    is searched for in the document that publishes it.

    Both directions on SYNTHETIC input, because green on the live tree proves only that the
    live tree is clean. The fixtures differ in exactly one thing at a time.

    The expectation is stated here, never imported from the subject: `_backticked_flags()`
    is called, its answer compared against a literal. A control that computes its expected
    value by calling the function under test agrees with every mutant of that function
    (task 113).
    """
    flags = _argparse_flags()
    plant = "Pass `--zzq-unresolved-tok` when you do this.\n"
    with_harness = "Run `python3 eval/judge/runner.py` first.\n" + plant
    without = "Run `python3 eval/tools/prune_scan.py` first.\n" + plant
    fake = "We planted `--zzq-unresolved-tok` here as a control.\n"
    # A RESOLVING flag on a deliberately-fake line. `_backticked_flags()` drops the whole
    # line, so the coverage producer must not count it as a mention it read - the defect
    # this fixture exists for, latent on the live skills at 0 such lines.
    exempt_only = ("Run `python3 eval/judge/runner.py` first.\n"
                   "We planted `--sweep` on this line, so nothing here is a claim.\n")
    # A FENCED `#` between a script name and a flag, which is a shell comment and not a
    # heading. Counting it as one puts the flag in a section of its own, where no script
    # is named, and the `section` figure comes back short. 31 of the 130 `#` lines across
    # the live skills are fenced, so this is the shape and not a curiosity.
    fenced_hash = ("# A heading\n"
                   "Run `python3 eval/tools/prune_scan.py` like this.\n"
                   "```bash\n"
                   "# a shell comment, not a section\n"
                   "echo hello\n"
                   "```\n"
                   "Then pass `--zzq-unresolved-tok` to it.\n")

    with tempfile.TemporaryDirectory() as tmp:
        paths = {}
        for name, body in (("names_a_harness", with_harness),
                           ("names_no_harness", without),
                           ("all_exempt", exempt_only),
                           ("fenced_hash", fenced_hash)):
            paths[name] = os.path.join(tmp, name, "SKILL.md")
            os.makedirs(os.path.dirname(paths[name]))
            open(paths[name], "w").write(body)
        split = _skill_flag_coverage(skills=[paths["names_a_harness"],
                                             paths["names_no_harness"]])
        exempt_cov = _skill_flag_coverage(skills=[paths["all_exempt"]])
        hash_cov = _skill_flag_coverage(skills=[paths["fenced_hash"]])

    live = _skill_flag_coverage()
    published = _published_skill_figures(live)
    texts = {rel: " ".join(open(os.path.join(ROOT, rel), encoding="utf-8",
                                errors="replace").read().split())
             for rel in {r for r, _ in published}}

    cases = [
        # RED, and on the half of the corpus the old trigger could not see. This is the
        # coverage this task bought: before it, the second row was `set()`.
        ("a phantom backticked flag in a skill that names a harness is caught",
         _backticked_flags(with_harness, flags, is_skill=True), {"--zzq-unresolved-tok"}),
        ("...and the identical plant in a skill that names none is caught too",
         _backticked_flags(without, flags, is_skill=True), {"--zzq-unresolved-tok"}),
        # ...and the gate did NOT become unconditional. An ordinary document naming no
        # harness is still out of scope, which is the exclusion that remains.
        ("an ordinary document naming no harness is still not read",
         _backticked_flags(without, flags), set()),
        # GREEN: the line exemption still works, so the reds above are the check doing its
        # job rather than firing on everything.
        ("a line saying the flag is planted exempts itself in a skill",
         _backticked_flags(with_harness.replace(plant, fake), flags, is_skill=True), set()),
        ("the coverage producer still separates the two by harness name",
         [os.path.basename(os.path.dirname(q)) for q in split["harness_only"]],
         ["names_no_harness"]),
        # The producer counts the population the CHECK reads, not the population on disk.
        ("a resolving flag on a deliberately-fake line is not counted as read",
         (exempt_cov["mentions"], exempt_cov["reads"]["shipped"]), (0, 0)),
        ("...and the same line planted with an UNRESOLVED flag adds no row either",
         exempt_cov["rows"]["shipped"], []),
        # The section trigger reads markdown structure, so it must read it the way every
        # other structure check here does. A fenced `#` is a shell comment.
        ("a fenced `#` does not split a section away from the script name above it",
         len(hash_cov["rows"]["section"]), 1),
        # THE TRIGGER'S BOUNDARY, both directions. The loose match is what admits a real
        # harness of ours whose name merely ENDS in one of the four; the tightened form
        # would not, which is why it is not shipped.
        ("a doc naming eval/judge/regrade_wholegame.py is admitted",
         _backticked_flags("Run `python3 eval/judge/regrade_wholegame.py`.\n" + plant,
                           flags), {"--zzq-unresolved-tok"}),
        ("...and a complete-path-component boundary would not admit it",
         bool(re.search(r"(?<![\w.-])(wholegame|runner|judge/|evaluate|regrade)\.py(?![\w-])",
                        "eval/judge/regrade_wholegame.py")), False),
        # The recorded dead alternative. If this reddens, `judge/` started matching and
        # the trigger widened without anyone saying so.
        ("the `judge/` alternative is inert - it requires the literal `judge/.py`",
         bool(HARNESS_TRIGGER.search("Run `python3 eval/judge/blind_dir.py` now.")), False),
        # THE PRICE OF THE WIDENING, live. Admitting every skill is only defensible while
        # this is 0; at 1 a correct document is red and someone will disable the gate.
        ("admitting every skill still costs 0 correct lines",
         live["rows"]["shipped"], []),
        ("...and it reads every backticked flag mention a skill makes",
         live["reads"]["shipped"], live["mentions"]),
        ("the retired trigger really did read fewer - the coverage is not a no-op",
         live["reads"]["harness"] < live["mentions"], True),
    ]
    # Every published figure, against the document that publishes it. An inequality lets a
    # trigger change move `10/29` or a row count while every case above stays green.
    cases += [(f"{rel} still says: {phrase}", phrase in texts[rel], True)
              for rel, phrase in published]

    failed = []
    for name, got, want in cases:
        ok = got == want
        if verbose:
            print(f"{'PASS' if ok else 'FAIL'}  {name}: {got}, expected {want}")
        if not ok:
            failed.append(f"skill flag pin: {name}: got {got}, want {want}")
    if verbose:
        print(f"\n  backticked-flag coverage over {live['skills']} SKILL.md, "
              f"{live['mentions']} backticked mention(s) of flags that resolve:")
        for t in ("harness", "line", "section", "shipped"):
            print(f"    {t:8s} reads {live['reads'][t]:3d}/{live['mentions']} "
                  f"and costs {len(live['rows'][t]):2d} row(s)")
        print("  unread by the RETIRED harness trigger, and read now: "
              f"{', '.join(live['harness_only'])}")
        print("  Rows over the skills, last adjudicated 2026-08-25 at 0. Any row here is "
              "a correct\n  document turned red or a real phantom flag, and either way it "
              "must be read:")
        for row in live["rows"]["shipped"]:
            print(f"    {row}")
    return failed


def _harness_trigger_census(docs: list[str] | None = None) -> dict:
    """What widening the backticked-flag half's file-wide trigger would cost.

    THE PRODUCER for the figures `.github/workflows/README.md` and `github_docs()` state.
    A count with no producer goes stale forever, so this is computed on the live corpus
    every `--selftest` rather than remembered from the day it was measured.

    The half is gated on `harness`, a file-wide search for 4 harness script names. The
    obvious property to replace it with is the CLOSED class `_our_script_names()` - does
    this document name any script this repository owns. `AGENTS.md`'s rule audit says to
    choose between candidate triggers on the live-corpus false-positive count, never on
    which sounds more general, and this one loses.

    IT REPORTS CANDIDATES, NOT VERDICTS. The only exclusions applied are the ones the check
    itself applies - known local flags, `FOREIGN_FLAG_PREFIXES`, `FOREIGN_FLAGS_EXACT` and
    the deliberately-fake line exemption. Nothing here classifies a remaining row, so a
    genuinely unresolved flag of ours would appear in this list exactly as a `gh` flag does.
    Calling the whole list false positives in the OUTPUT would be a reason not to count a
    failure, and every one of those is a channel a bug can widen (`AGENTS.md` rule 7).
    Raised by CodeRabbit on PR #25.

    The adjudication is a dated one-off and is stated as one: 2026-08-24, 25 rows, none
    genuine - `gh`, `git`, Godot and Chrome flags, and tokens task files name as fake. The
    live count prints beside it, so the two disagreeing is visible rather than silent.

    `docs` exists for the pin that drives this over a synthetic corpus. Everything else
    takes the default.
    """
    flags, scripts = _argparse_flags(), _our_script_names()
    old_rx = re.compile(r"(wholegame|runner|judge/|evaluate|regrade)\.py")
    wide_rx = re.compile(r"\b(" + "|".join(re.escape(s) for s in sorted(scripts)) + r")\b")
    old_admitted = wide_admitted = 0
    new_rows = []
    docs = reference_docs() if docs is None else docs
    for q in docs:
        text = open(q, encoding="utf-8", errors="replace").read()
        narrow, wide = bool(old_rx.search(text)), bool(wide_rx.search(text))
        old_admitted += narrow
        wide_admitted += wide
        if not (wide and not narrow):
            continue
        for ln in text.split("\n"):
            if re.search(_DELIBERATELY_FAKE, ln, re.I):
                continue
            for tok in re.findall(r"`(--[a-z0-9-]{2,})`", ln):
                if (tok.startswith(FOREIGN_FLAG_PREFIXES)
                        or tok in FOREIGN_FLAGS_EXACT or tok in flags):
                    continue
                new_rows.append(f"{os.path.relpath(q, ROOT)}: {tok}")
    return {"corpus": len(docs), "narrow": old_admitted,
            "wide": wide_admitted, "new_rows": sorted(new_rows)}


def _assert_own_repo(tmp: str, extra_env: dict[str, str]) -> None:
    """Refuse unless the git directory `tmp` resolves to lives inside `tmp`.

    A guard that fails closed AT THE MOMENT OF USE, in front of the only `git` call in this
    module that writes. `_git_at` dropping `GIT_*` is what makes this pass; the two are
    separate mechanisms on purpose, so a control can remove either one alone.

    `--absolute-git-dir`, not `--show-toplevel`: under an inherited `GIT_DIR` with no
    `GIT_WORK_TREE` the work tree IS the current directory, so `--show-toplevel` answers
    `tmp` and agrees while the index being written belongs to another repository. Measured
    2026-08-27 - the toplevel question is green on exactly the input this exists to catch.
    """
    ok, gitdir = _git_at(tmp, "rev-parse", "--absolute-git-dir", extra_env=extra_env)
    inside = os.path.realpath(gitdir.strip()).startswith(os.path.realpath(tmp) + os.sep)
    if not ok or not inside:
        raise RuntimeError(
            f"the corpus fixture would write to {gitdir.strip() or '<unknown>'}, which is "
            f"not inside {tmp}. Refusing to `git add` into a repository this function did "
            f"not create.")


def _tree_fixture(tmp: str) -> dict[str, str]:
    """A throwaway git repository whose tracked set is known in advance.

    The live tree cannot pin `project_docs()`'s TRACKED filter: it is clean, so globbing
    the filesystem and reading the index return the same 238 documents and a mutant that
    deletes the filter survives. The discriminating input is a repository holding markdown
    that is NOT in it, which has to be built.

    Returns the absolute paths by role so the caller states its expectation itself, rather
    than deriving it from the subject (rule 12, task 113).
    """
    def write(relpath: str, text: str = "# fixture\n") -> str:
        p = os.path.join(tmp, *relpath.split("/"))
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w", encoding="utf-8") as fh:
            fh.write(text)
        return p

    paths = {
        "gitignore": write(".gitignore", "staging/\n"),
        "tracked_top": write("doc.md"),
        "tracked_nested": write("sub/nested.md"),
        # A VARIANT, not a mutant (rule 15): correct input the repaired reader could
        # mishandle. `git ls-files` C-quotes any path outside ASCII unless `-z` is passed,
        # and a quoted name fails `endswith(".md")`. U+00F8 has no canonical decomposition,
        # so this row cannot turn on a filesystem's unicode normalisation.
        "tracked_unicode": write("sub/nøte.md"),
        "tracked_dotdir": write(".dotdir/hidden.md"),
        "tracked_runs": write("runs/stored.md"),
        "tracked_deleted": write("gone.md"),
        "ignored": write("staging/scratch.md"),
        "untracked": write("loose.md"),
    }
    # THIS FUNCTION WRITES, so it asserts the repository it is about to write into.
    # `_git_at` drops `GIT_*` from the child, which is what makes the assertion pass; the
    # assertion is here because a guard that fails closed at the moment of use is worth
    # more than a property held somewhere else. `--absolute-git-dir` is the discriminating
    # question: under an inherited `GIT_DIR` with no `GIT_WORK_TREE`, `--show-toplevel`
    # answers `<tmp>` and AGREES while the index being written is another repository's.
    #
    # No user config: `init.templateDir` would install hooks into a repository this
    # function created and then deletes.
    cfg = {"GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_SYSTEM": os.devnull}

    # `add` respects .gitignore, which is what makes `staging/scratch.md` untracked, and
    # `loose.md` is simply never named. No commit: `ls-files` reads the INDEX, and the
    # gate runs against staged content for exactly that reason.
    #
    # THE EXIT STATUS IS READ. A failed `add` leaves an EMPTY index, `_tracked_md` then
    # returns [] at exit 0 because the listing itself succeeded, and every row below
    # reddens as a defect in `project_docs()` - a control blaming its subject for its own
    # harness. Raised by CodeRabbit on PR #54.
    ok, out = _git_at(tmp, "-c", "init.defaultBranch=main", "init", "-q", extra_env=cfg)
    if not ok:
        raise RuntimeError(f"the corpus fixture could not be built: git init failed in "
                           f"{tmp}: {out.strip()[:200]}")
    _assert_own_repo(tmp, cfg)
    ok, out = _git_at(tmp, "add", "--", ".gitignore", "doc.md", "sub/nested.md",
                      "sub/nøte.md", ".dotdir/hidden.md", "runs/stored.md", "gone.md",
                      extra_env=cfg)
    if not ok:
        raise RuntimeError(f"the corpus fixture could not be built: git add failed in "
                           f"{tmp}: {out.strip()[:200]}")
    # In the index, gone from the disk. Every caller OPENS what this returns, so a path
    # that cannot be read is a crash rather than a finding.
    os.remove(paths["tracked_deleted"])
    return paths


def _corpus_pins(verbose: bool = False) -> list[str]:
    """The two corpora reach what they are meant to reach, and nothing else.

    A corpus is an input to a check (#60), and this one failed silently twice. A
    dot-directory is skipped by `glob`, so a document could be read by every session and by
    no gate. And `glob` reads the FILESYSTEM, so a scratch note under a gitignored
    directory joined a corpus the bare-trial-id ratchet is pinned to - a file that is not in
    the repository moving a gate that is.

    ASKED AS COMPLETENESS, not as one filename. Pinning only
    `.github/workflows/README.md` passes for a `github_docs()` that returns exactly that
    file, so the second document added under `.github/` would be unswept and green - the
    same silent shape this whole repair exists to close. The live case therefore compares
    `reference_docs()` against `_github_docs_by_walk()`, which reaches the files by a
    different mechanism, and the adversarial case drives a NESTED fixture no one-level and
    no hardcoded implementation can satisfy.

    The register is still named explicitly, because the one row whose answer you can state
    in advance is what proves the extraction before you believe the census (rule 12).

    Both directions, because the separation is the point:

      in `reference_docs()`      swept for phantom names
      NOT in `project_docs()`    that helper feeds the size report and the bare-trial-id
                                 ratchet, and the ratchet is pinned to an EXACT count a
                                 larger corpus would move in the direction that passes

    THE TRACKED FILTER NEEDS A FIXTURE, not the live tree. On a clean checkout the
    filesystem and the index hold the same documents, so a mutant deleting the filter
    passes every live case here. `_tree_fixture` builds the repository that tells them
    apart.
    """
    register = os.path.join(ROOT, ".github", "workflows", "README.md")
    rel = os.path.relpath(register, ROOT)
    refs = set(reference_docs())
    walked = _github_docs_by_walk()
    unswept = sorted(os.path.relpath(q, ROOT) for q in walked if q not in refs)

    # THE TWO SPELLINGS OF THE TREE, COMPARED rather than promised equal. They filter
    # differently on purpose - `project_docs()` keeps the archive and drops dot-directories
    # and `runs/`, `_live_corpus()` does the opposite on the archive - so what is asserted
    # is the overlap each one claims to hold, after removing exactly the deliberate
    # differences. Comparing the raw lists would only say they are different, which is
    # already known; this says they agree about WHICH FILES ARE IN THE REPOSITORY.
    proj_rel = {os.path.relpath(p, ROOT).replace(os.sep, "/") for p in project_docs()}
    live_rel = set(_live_corpus()[0])
    proj_live = {r for r in proj_rel if not is_archive(r)}
    live_proj = {r for r in live_rel
                 if not any(part.startswith(".") for part in r.split("/"))}

    with tempfile.TemporaryDirectory() as tmp:
        # ADVERSARIAL: nested two deep, and a sibling at the top. A one-level glob, a
        # hardcoded `workflows/README.md`, and a `.md` test that forgets to recurse each
        # come back short here while the live tree above still looks perfect.
        deep = os.path.join(tmp, ".github", "ISSUE_TEMPLATE", "nested", "deep.md")
        os.makedirs(os.path.dirname(deep))
        open(deep, "w").write("# deep\n")
        shallow = os.path.join(tmp, ".github", "CONTRIBUTING.md")
        open(shallow, "w").write("# shallow\n")
        open(os.path.join(tmp, ".github", "notes.txt"), "w").write("not markdown\n")
        # VENDORED, nested. The subject drops it by full-path match; an oracle that
        # tested the bare directory name would keep it, and the completeness case above
        # would then be red while `reference_docs()` was right.
        vendored = os.path.join(tmp, ".github", "target", "generated.md")
        os.makedirs(os.path.dirname(vendored))
        open(vendored, "w").write("# vendored\n")
        found = github_docs(root=tmp)
        fixture_walked = _github_docs_by_walk(root=tmp)

        # The census reports CANDIDATES, and this is the direction that matters: a
        # genuinely unresolved flag of OURS, in a document the wider trigger would newly
        # admit, must appear. Measured rather than asserted, because the claim in the
        # output is what stops a reader dismissing a real hit as a known false positive.
        # `no_harness` names a script and no harness, which is exactly that population.
        no_harness = os.path.join(tmp, "names_a_script.md")
        open(no_harness, "w").write(
            "Run `eval/tools/prune_scan.py` with `--zzq-unresolved-tok` for this.\n")
        quiet = os.path.join(tmp, "names_nothing.md")
        open(quiet, "w").write("Run it with `--zzq-unresolved-tok` for this.\n")
        cens = _harness_trigger_census(docs=[no_harness, quiet])
        surfaced = [r for r in cens["new_rows"] if "--zzq-unresolved-tok" in r]

    with tempfile.TemporaryDirectory() as tree_tmp:
        fx = _tree_fixture(tree_tmp)
        fx_docs = project_docs(root=tree_tmp)
        # STATED HERE, not derived from the subject. Three documents survive every filter;
        # each of the other four is excluded by a DIFFERENT one, so a mutant that removes
        # any single filter reddens this row.
        fx_want = sorted([fx["tracked_top"], fx["tracked_nested"], fx["tracked_unicode"]])
        fx_ignored_on_disk = os.path.exists(fx["ignored"]) and os.path.exists(fx["untracked"])
        fx_tracked = _tracked_md(root=tree_tmp)
        # The fixture is only discriminating if the subject could have reached it. A
        # `$TMPDIR` under a vendored name would drop every fixture document and the rows
        # below would go red for a reason that is not the subject's fault, so say which.
        fx_root_reachable = not is_vendored(tree_tmp + os.sep)

        # An empty corpus is the one result indistinguishable from a clean one. `_git`
        # folds a failed listing into "" and every check downstream would then report
        # itself clean over 0 documents. A path that does not exist is the unambiguous
        # failure: "not a repository" depends on where `$TMPDIR` happens to sit.
        try:
            _tracked_md(root=os.path.join(tree_tmp, "no-such-directory"))
            raised = False
        except RuntimeError:
            raised = True

    # WHICH REPOSITORY, asked with a HOSTILE `GIT_DIR` in the environment. `-C <root>`
    # names a directory and does not name a repository; `GIT_DIR` outranks it at exit 0,
    # so a reader steered this way answers about another tree and a writer WRITES to one.
    # `$TMPDIR` is where this is provable without touching anything that matters.
    with tempfile.TemporaryDirectory() as hostile:
        # BOTH STATUSES READ, as `_tree_fixture` reads its own. A failed setup leaves
        # `hostile_index` holding something other than `["victim.md"]`, and the row below
        # would then report a harness failure as a scrub failure. Raised by CodeRabbit on
        # PR #54.
        ok, out = _git_at(hostile, "init", "-q")
        if not ok:
            raise RuntimeError(f"the hostile-GIT_DIR fixture could not be built: git init "
                               f"failed in {hostile}: {out.strip()[:200]}")
        open(os.path.join(hostile, "victim.md"), "w", encoding="utf-8").write("# v\n")
        ok, out = _git_at(hostile, "add", "--", "victim.md")
        if not ok:
            raise RuntimeError(f"the hostile-GIT_DIR fixture could not be built: git add "
                               f"failed in {hostile}: {out.strip()[:200]}")
        saved = os.environ.get("GIT_DIR")
        os.environ["GIT_DIR"] = os.path.join(hostile, ".git")
        try:
            with tempfile.TemporaryDirectory() as steered_tmp:
                # A REFUSAL IS A RESULT, not a crash. `_assert_own_repo` firing here means
                # the scrub failed, which is a red row - and a red row is what a reader can
                # act on. Letting it propagate would take the whole pin set out instead.
                try:
                    _tree_fixture(steered_tmp)
                    steered_read = _tracked_md(root=steered_tmp)
                except RuntimeError as exc:
                    steered_read = [f"the fixture refused: {exc}"[:120]]
                steered_live = len(project_docs())
        finally:
            if saved is None:
                os.environ.pop("GIT_DIR", None)
            else:
                os.environ["GIT_DIR"] = saved
        hostile_index = sorted(_git_at(hostile, "ls-files")[1].split())

    census = _harness_trigger_census()
    reg_text = open(register, encoding="utf-8", errors="replace").read()
    reg_lines = reg_text.split("\n")
    planted = reg_lines + ["```bash", "python3 eval/tools/docstat.py --zzq-not-a-flag", "```"]

    cases = [
        (f"{rel} is in the reference corpus", register in refs, True),
        (f"{rel} is NOT in project_docs() - the ratchet's corpus is unmoved",
         register in project_docs(), False),
        ("every .md under .github/ is swept, found by walking rather than by the same glob",
         unswept, []),
        # project_docs() and _live_corpus() are two READERS of one tree. Asserted, not
        # promised in a comment: the deliberate differences are removed and what is left
        # must match exactly, in both directions.
        ("project_docs() holds no live document _live_corpus() is missing",
         sorted(proj_live - live_proj), []),
        ("..._live_corpus() holds no non-dot document project_docs() is missing",
         sorted(live_proj - proj_live), []),
        ("...and that overlap is not the empty set agreeing with itself",
         len(proj_live) > 0, True),
        # THE TRACKED FILTER. Every row below is red under the glob this replaced.
        ("fixture: the untracked and the gitignored .md are really on the fixture's disk",
         fx_ignored_on_disk, True),
        ("...and the fixture root is not itself vendored, so the subject can reach it",
         fx_root_reachable, True),
        ("fixture: project_docs() returns the 3 TRACKED, non-dot, non-runs, on-disk "
         "documents and nothing else", fx_docs == fx_want, True),
        ("variant: a tracked .md whose name is not ASCII stays in the tree - `ls-files` "
         "C-quotes it without -z", "sub/nøte.md" in fx_tracked, True),
        ("fixture: a path in the index but deleted from the disk is dropped, because "
         "every caller opens what this returns",
         "gone.md" in fx_tracked and fx["tracked_deleted"] not in fx_docs, True),
        ("fixture: the gitignored scratch note is not in the tree at all",
         "staging/scratch.md" in fx_tracked, False),
        ("fixture: nor is the untracked one, which no .gitignore mentions",
         "loose.md" in fx_tracked, False),
        ("fixture: a TRACKED .md under a dot-directory is in the tree, and project_docs() "
         "drops it", ".dotdir/hidden.md" in fx_tracked
         and fx["tracked_dotdir"] not in fx_docs, True),
        ("fixture: a TRACKED .md under runs/ is in the tree, and project_docs() drops it",
         "runs/stored.md" in fx_tracked and fx["tracked_runs"] not in fx_docs, True),
        ("_tracked_md RAISES on a git failure rather than returning an empty corpus",
         raised, True),
        # THE ADDRESS IS NOT THE CALLER'S ENVIRONMENT TO SET. All three rows were WRONG
        # before the scrub, and all three at exit 0.
        ("a hostile GIT_DIR does not steer what _tracked_md reads",
         steered_read, ['.dotdir/hidden.md', 'doc.md', 'gone.md', 'runs/stored.md',
                        'sub/nested.md', 'sub/nøte.md']),
        ("...nor what project_docs() reads on the live tree",
         steered_live == len(project_docs()) and steered_live > 0, True),
        ("...and the repository it names is not WRITTEN to",
         hostile_index, ["victim.md"]),
        ("the walk found the register too - neither side is an empty set agreeing",
         register in walked, True),
        ("adversarial: a nested and a top-level .github doc, and no .txt",
         found == sorted([deep, shallow]), True),
        ("adversarial: a VENDORED nested doc is dropped by the glob",
         vendored in found, False),
        ("...and the walking oracle drops exactly the same set",
         fixture_walked == found, True),
        ("the census surfaces an unresolved flag of OURS as a candidate, not only "
         "foreign ones", len(surfaced), 1),
        ("...and only from the doc the wider trigger would newly admit",
         [r for r in surfaced if "names_a_script.md" in r] == surfaced, True),
        # POSITIVE CONTROL for the corpus, not just membership. Being in the list is not
        # being read: the bare-fenced half must actually fire on a token planted in this
        # file's own lines. Green membership with a check that never looks is the exact
        # shape this repair closed.
        ("the bare-fenced half fires on a flag planted in the register's own lines",
         "--zzq-not-a-flag" in _bare_fenced_flags(planted, _our_script_names()), True),
        ("...and says nothing about the register unplanted",
         [t for t in _bare_fenced_flags(reg_lines, _our_script_names())
          if t not in _argparse_flags()], []),
        # THE RECORDED EXCLUSION, pinned so it cannot go stale silently. If this reddens,
        # the register began naming a harness and the backticked half now reads it - the
        # docstring table above is then wrong and must be re-measured, not deleted.
        ("the backticked half still does NOT admit the register (recorded exclusion)",
         bool(re.search(r"(wholegame|runner|judge/|evaluate|regrade)\.py", reg_text)),
         False),
        # The recorded exclusion rests on the wider trigger costing rows. Asserted
        # mechanically; whether those rows are FALSE positives is adjudication, and the
        # census prints them so the next reader adjudicates rather than trusts.
        ("widening that trigger is not free - it admits more docs and adds rows",
         census["wide"] > census["narrow"] and len(census["new_rows"]) > 0, True),
    ]
    failed = []
    for name, got, want in cases:
        ok = got == want
        if verbose:
            print(f"{'PASS' if ok else 'FAIL'}  {name}: {got}, expected {want}")
        if not ok:
            failed.append(f"corpus pin: {name}: got {got}, want {want}")
    if verbose:
        print(f"\n  harness-trigger census over {census['corpus']} reference docs: "
              f"the shipped 4-name trigger admits {census['narrow']}, "
              f"`names any script of ours` would admit {census['wide']}")
        print(f"  and add {len(census['new_rows'])} CANDIDATE row(s). Each needs "
              f"ADJUDICATING before it counts as a false positive - this census excludes "
              f"known\n  local and known foreign flags and classifies nothing beyond that, "
              f"so a genuinely\n  unresolved flag of ours would appear here too:")
        for row in census["new_rows"]:
            print(f"    {row}")
        print("  Last adjudicated 2026-08-24 at 25 rows: none genuine. A count above that, "
              "or a\n  row naming a script of ours, is unadjudicated and must be read.")
    return failed


def cmd_selftest() -> int:
    """`--selftest`: the pins with their cases printed, plus proof the archive was untouched.

    The mtime/size assertion is not decoration. The obvious way to write this selftest is
    to plant a defect in the real `eval/FINDINGS.md` and restore it afterwards, and the
    obvious way is wrong: a crash between the two leaves the archive edited. This states
    the property the in-memory design buys, in a form that would notice if someone later
    "simplified" it back to writing on disk.
    """
    index_path = os.path.join(ROOT, "eval", "FINDINGS.md")
    before = _size_mtime(index_path)
    failed = _index_pins(verbose=True)
    print()
    failed += _aspect_census_pins(_aspect_ids(), verbose=True)
    print()
    failed += _findings_census_pins(verbose=True)
    print()
    failed += _bare_flag_pins(verbose=True)
    print()
    failed += _citation_census_pins(verbose=True)
    print()
    failed += _count_trigger_pins(verbose=True)
    print()
    failed += _orphan_tail_pins(verbose=True)
    print()
    failed += _duplicate_fragment_pins(verbose=True)
    print()
    failed += _regime_ordinal_pins(verbose=True)
    print()
    failed += _corpus_pins(verbose=True)
    print()
    failed += _skill_flag_pins(verbose=True)
    after = _size_mtime(index_path)
    untouched = before == after
    print(f"\n{'PASS' if untouched else 'FAIL'}  eval/FINDINGS.md size and mtime unchanged "
          f"({before} -> {after}) - the pins mutate copies in memory, never the archive")
    for f in failed:
        print(f"  {f}")
    print(f"{len(failed)} pin(s) came out wrong")
    return 0 if not failed and untouched else 1


# A line saying a name is DELIBERATELY fake is not a claim that it exists. This lives at one
# address because two checks need it and an exemption vocabulary kept in two places drifts:
# the aspect check already failed once because its list held ONE inflection of `plant`, so
# "PLANTING the control" was red and the past tense was green (2026-08-23).
_DELIBERATELY_FAKE = r"does not exist|phantom|plant\w*|do not name them"


def cmd_sweep() -> int:
    """Names in docs that do not resolve, and files that do not parse as what they are.

    Deliberately CONSERVATIVE. Every category here has produced a real defect, but a
    false positive costs more than a false negative: it trains the reader to skip the
    output, and then the real hit is invisible. When unsure, say nothing.
    """
    docs = project_docs()
    refs = reference_docs()  # docs + skills; see why they are two corpora, not one
    flags, aspects = _argparse_flags(), _aspect_ids()
    scripts = _our_script_names()
    bare_seen = 0
    problems: list[str] = []
    corpus: dict[str, str] = {}

    for p in refs:
        rel = os.path.relpath(p, ROOT)
        text = open(p, encoding="utf-8", errors="replace").read()
        corpus[rel] = text

        lines = text.split("\n")

        # The backticked half. Its trigger, its exclusions and what widening either
        # would cost are in `_backticked_flags()`; read that before changing this line.
        #
        # Dedup is per DOCUMENT and the output sorted, preserving the old `set(...)` count
        # of one problem per token however often it occurs -- and fixing that set's
        # iteration order, which varied between runs under hash randomisation.
        bad_flags: set[str] = set(
            _backticked_flags(text, flags, is_skill=os.path.basename(p) == "SKILL.md"))
        # The bare half. Deliberately OUTSIDE the `harness` gate: its trigger is the
        # script name on the line itself, which is stronger evidence than the file-wide
        # test, and the file-wide form is the one that hid a false positive for three
        # weeks (see FOREIGN_FLAG_PREFIXES). It shares `bad_flags`, so a token written
        # both ways in one document is still one problem.
        for tok in _bare_fenced_flags(lines, scripts):
            bare_seen += 1  # the POPULATION, reported below: 0 hits out of 0 looked at
            if tok.startswith(FOREIGN_FLAG_PREFIXES) or tok in FOREIGN_FLAGS_EXACT or tok in flags:
                continue           # is a check that cannot fire, and reads identically
            bad_flags.add(tok)
        for tok in sorted(bad_flags):
            problems.append(f"{rel}: flag {tok} matches no argparse in eval/")

        # NO PATH CHECK. Docs legitimately write paths relative to a context stated in
        # prose or a table cell -- README named `tools/boundary.gd` in a row about
        # template-godot/, where it did exist (that tree is gone, #119; the reason is
        # not). Measured when it was live: 0 true positives, 2 false.
        # A check that cannot be made reliable is removed, not tuned until it is quiet;
        # tuning until quiet is how a check comes to pass vacuously.

        # Aspect ids named as if they exist. The exemption is checked on the LINE, not
        # the document: a file-wide search for "candidate"/"not built" let one legitimate
        # disclaimer silence every check in the file, and the planted-phantom control
        # went green. Document-scope exemptions make a check vacuous.
        # findings/ is an archive: naming a superseded aspect is its subject matter.
        if aspects and "findings/" not in rel:
            fenced = _fence_mask(lines)
            for i, ln in enumerate(lines):
                # A FENCED LINE IS NOT A CLAIM. Inside ``` a line is a command to run or an
                # output to expect; the reference checks ask whether a doc ASSERTS that a
                # name exists, and a shell command asserts nothing about its own arguments.
                # This is the discriminator that let the skills into the corpus at all:
                # `audit-docs/SKILL.md` names `feel` and `tuning` in the printf that PLANTS
                # them as this sweep's positive control, and it is the only place in 124
                # documents where the aspect check fires on correct input. A gate that fails
                # on correct input gets disabled - which is why the path check below was
                # deleted rather than tuned.
                #
                # LINE-SCOPED, and that is the whole design. A file-wide exemption for this
                # once let a single legitimate disclaimer silence every aspect check in its
                # file, and the planted-phantom control went green.
                #
                # THE COST, measured rather than assumed: a phantom planted INSIDE a fence
                # is now invisible. The documented positive control appends unfenced prose
                # to `judge/JUDGING.md`, so it still goes red; a control that planted its
                # phantom in a code block would not, and would be testing nothing.
                if fenced[i]:
                    continue
                # `phantom` and `planted` are this project's OWN vocabulary for an id that
                # deliberately does not exist -- the comment above this function already
                # says "the planted-phantom control went green". A task describing how to
                # plant one therefore names `feel` and `tuning` legitimately, and on
                # 2026-08-23 that turned the whole sweep red for a document that was
                # correct. A gate that fails on correct input is a gate that gets disabled,
                # which is why the path check below this was deleted rather than tuned.
                # `plant\w*`, not `planted`. The exemption listed ONE INFLECTION of the verb,
                # so the sentence "…where `feel` and `tuning` are PLANTING the control" was
                # red and the same sentence in the past tense was green. Found 2026-08-23 by
                # this check firing on a line written to document this check. A trigger
                # spelled as an enumeration has to be re-derived by the first reader who
                # meets an item not on it (AGENTS.md, the 2026-08-15 rule audit) - and the
                # enumeration does not have to be a list to be one.
                if re.search(_DELIBERATELY_FAKE + r"|no `\w+` judge|not built|candidate|"
                             r"retired|superseded", ln, re.I):
                    continue
                for tok in set(re.findall(r"`(feel|tuning|design|polish|gameplay)`", ln)):
                    problems.append(
                        f"{rel}: `{tok}` reads as an aspect id; ASPECTS = {sorted(aspects)}")

    # ONE ADDRESS PER PROCEDURE. A skill is how a procedure survives; a second copy of one
    # is a second source of truth, and the second copy is the one nobody edits.
    #
    # `.agents/skills/` held a duplicate of the skills for a Codex CLI (#99). It was never
    # once in sync: `add-game` was born 39 lines short in the very first commit, missing the
    # entire `prompt_guard.py` section - the guard that exists because a shared preamble
    # contaminated a single-variable experiment (#41). After the import, `.claude/skills/` took
    # 6 edits that changed a procedure and it took 0. Deleted 2026-08-23 rather than synced,
    # because syncing buys one day: a mirror with no reader drifts again by the next commit.
    #
    # WHAT CHANGED ON 2026-08-23, AND WHY IT IS NOT A REVERSAL OF #99. The real files now
    # live at SKILLS_REAL (`.agents/skills`), so Codex, Claude and anything else read ONE
    # source rather than a copy each, and `.claude/skills` is a SYMLINK to it. #99's
    # objection was to a COPY that drifts - its own escape clause says "add a pointer, never
    # a copy" - and a symlink has no second file to get edited. The count of copies is still
    # exactly one; only which end holds the pointer moved.
    #
    # THE PROPERTY IS THE ADDRESS, NOT THE DIRECTORY NAME. This does not bless `.agents/` by
    # name; it requires that a real SKILL.md resolve under SKILLS_REAL and nowhere else, so
    # it fires on `.codex/`, `.cursor/`, `skills/` or a wrong nesting depth just the same -
    # a trigger written as an enumeration has to be re-derived by the first reader who meets
    # an item not on it.
    #
    # NOT A RATCHET. The correct count is 0 and there is no legacy population to accommodate.
    #
    # os.walk, NOT glob. `glob` does not descend into dot-directories, so a `**/SKILL.md`
    # pattern returns zero paths here - including the authoritative ones - and the check
    # passes by finding nothing. The planted control is the only reason that was visible;
    # it is also why `project_docs()` above has never seen a file under `.claude/`.
    #
    # `_all_skill_files()` walks with followlinks=False, so a symlinked pointer contributes
    # no paths and cannot be mistaken for a second copy. REALPATH, not string equality: the
    # walk reaches the real files by whichever route it took, and a check that compared
    # spellings would redden the very layout it is meant to accept.
    SKILLS_ROOT = os.path.join(ROOT, SKILLS_REAL)
    real_root = os.path.realpath(SKILLS_ROOT)
    skills = sorted(_all_skill_files())
    for sk in skills:
        if os.path.realpath(os.path.dirname(os.path.dirname(sk))) == real_root:
            continue
        problems.append(
            f"{os.path.relpath(sk, ROOT)}: a real skill file outside {SKILLS_REAL}/<name>/, "
            f"which AGENTS.md names as the sole authoritative path. A second copy is a "
            f"second source of truth and only one of them gets edited (#99). If you want "
            f"another path to reach the skills, make it a symlink to {SKILLS_REAL}.")

    # THE POINTER IS PART OF THE LAYOUT, AND IT IS THE HALF THAT FAILS SILENTLY.
    #
    # Measured 2026-08-23 against `claude` 2.1.220, one probe skill per layout, unique names
    # so a same-named skill could not be deduplicated, and every tool but `Skill` denied so
    # the token could not arrive by the model reading the file:
    #
    #   real .claude/skills/<n>/SKILL.md          LOADED   (positive control)
    #   .claude/skills -> ../.agents/skills       LOADED   (the shipped layout)
    #   .claude/skills/<n> -> ../../.agents/...   LOADED
    #   .agents/skills only, no .claude           NOSKILL  (negative control)
    #   real .claude/skills, .agents/skills link  LOADED
    #
    # The negative control is the reason this block exists: Claude Code does NOT read
    # `.agents/skills` natively. Delete the symlink and the nine skills still sit in the
    # tree, `--sweep` still finds them at the authoritative address, every check above still
    # reads clean - and no agent can load a single one. That is the vacuous pass this module
    # exists to prevent, so the pointer is asserted rather than assumed.
    for rel in SKILLS_LINKS:
        p = os.path.join(ROOT, rel)
        if not os.path.islink(p):
            what = "a real directory" if os.path.isdir(p) else "missing"
            problems.append(
                f"{rel}: must be a symlink to {SKILLS_REAL}, and is {what}. Claude Code does "
                f"not discover skills under {SKILLS_REAL} on its own (measured: a project "
                f"with only {SKILLS_REAL} loads no skills), so without this link every skill "
                f"is unreachable while the tree still looks correct.")
        elif os.path.realpath(p) != real_root:
            problems.append(
                f"{rel}: symlink resolves to {os.path.realpath(p)}, not to {real_root}. "
                f"A dangling or misaimed pointer loads no skills and reports nothing.")

    # THE ADDRESS IS AN INPUT TO THE CHECK (#60). Finding nothing is the one result this
    # check cannot distinguish from being pointed at the wrong place, so say so out loud
    # rather than returning the same silence a clean repository returns.
    if not skills:
        problems.append(
            f"no SKILL.md found anywhere under {SKILLS_REAL} or outside it. The skills "
            f"exist; this check is looking at the wrong root.")

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
            f"An id is not unique across runs (#70). Last by path: {bare[-1]}")
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

    # STRUCTURE, not references. Both of these are schema questions with a demonstrated
    # true positive in this repository and no judgement in the answer; see their
    # docstrings for the defect each was bought with and its measured false-positive count.
    problems += _check_skill_frontmatter()
    problems += _check_list_indent()
    problems += _check_findings_integrity()
    problems += _check_regime_ordinals()
    # THE OTHER DIRECTION of the aspect check above. That one asks whether a name a doc
    # USES resolves; this one asks whether a doc that claims to name them all does. The
    # sweep printed `6 aspects known` and exit 0 for as long as two documents said five.
    problems += _check_aspect_census(corpus, aspects)
    problems += _aspect_census_pins(aspects)

    # Runs over `corpus`, which is `reference_docs()` - live AND archive. See the comment on
    # `_check_orphaned_tail` for why the archive is in scope here when the other structure
    # checks exempt it, and for the 0-false-positive measurement that let it ship.
    for _rel, _text in sorted(corpus.items()):
        problems += _check_orphaned_tail(_text, _rel)
        problems += _check_duplicate_fragment(_text, _rel)
    problems += _orphan_tail_pins()
    # Same corpus, same reasoning, different question - and the gap between the two is the
    # reason both run. See the module docstring: the one instance of the fragment defect
    # scores 0 under the orphaned-tail rule, and a single check would have shipped believing
    # it was covered.
    problems += _duplicate_fragment_pins()

    # THE WITHDRAWAL REGISTER GATES, unlike `--renumbered` next to it, because its verdict
    # has no judgement in it: a declared entry either occurs in a live block that cites its
    # id or it does not. It was wired in only after it was measured RED on real data - the
    # tree at 25fe630 has the pair in three live documents - and after
    # `tools/withdrawn_control.py` showed five mutants each flipping the control that names
    # them. A gate installed while green and never seen red is the shape this file exists
    # to prevent.
    withdrawn_problems, _ = _check_withdrawal_register()
    problems += withdrawn_problems
    # THE TRIAGE REGISTER GATES for the same reason the withdrawal register does, and on
    # the narrower question: an entry either still matches exactly one line of the file it
    # names or it does not. The VERDICT it records is a judgement and is never checked here;
    # only whether the thing it was recorded against still exists.
    problems += _check_triage_register()
    # THE MONEY-UNIT GATE, wired in for the same reason and on the same shape of question:
    # a live block either states a `$` figure beside an expenditure noun or it does not.
    # `_money_pins` runs first and in memory, because a trigger returning 0 on a clean
    # corpus reads exactly like one that cannot fire.
    problems += _money_pins()
    money_problems, _ = _check_money_unit()
    problems += money_problems
    # The findings-index checks carry their own red control, and it runs HERE rather than
    # in a command someone has to remember. `--sweep` was green on a real two-table split
    # for as long as that split stood; a check whose ability to fail is never exercised is
    # the shape this project keeps finding. In memory, no I/O beyond one re-read.
    problems += _index_pins()
    # The COUNT of the log, which the range gate above cannot see: `#19-#131` is equally
    # true of 113 findings and of 40. `--findings` is the producer; these pins are what
    # stop it being a number that agrees with itself. Same reasoning, same place.
    problems += _findings_census_pins()
    # The bare fenced-flag trigger returns 0 on the clean corpus, and 0 is what a check
    # that cannot fire returns too. These pins are what separates the two, and they cost
    # no I/O: every case is a string built in memory.
    problems += _bare_flag_pins()
    # `--citations` GATES NOTHING - #146 measured that check at 18 false positives to 2 true
    # and it is not built. Its pins run here anyway, because the producer prints a number
    # documents quote, and an extractor that has stopped matching returns 0 rows over a full
    # corpus - the same reading a clean corpus gives. In memory, no I/O.
    problems += _citation_census_pins()
    # `--count-triggers` gates nothing either, and its failure mode is the same shape one
    # step worse: an extractor that stopped matching reports `red 0` for the REJECTED
    # candidates, which reads as "the obvious trigger was fine after all".
    problems += _count_trigger_pins()

    # A WARNING, not a gate, in the manner `tasks.py check` already uses for a smell that
    # is not a verdict. The decided half IS a verdict and would gate cleanly; the reason
    # it does not is that its evidence is `git blame`, which dates the last edit of a line
    # rather than the writing of a citation. That is sound enough to send someone to look
    # and not sound enough to block a commit on.
    #
    # Only the decided half prints here. The undecidable half never reaches zero - it
    # contains correct citations by construction - and a permanent block of output that
    # cannot be cleared is how a reader learns to skip this command's output entirely.
    # `--renumbered` is where a person goes to read it, on purpose.
    stale, _undecided, renum_summary = _check_renumbered_citations()
    if not stale and "did NOT run" in renum_summary:
        problems.append(renum_summary)
    elif stale:
        print(f"{len(stale)} citation(s) of a finding number that has since been "
              f"reassigned ({renum_summary}):")
        for s in stale:
            print(f"  {s}")
        print("Every one of these still RESOLVES, which is why no other check here sees\n"
              "them. `docstat.py --renumbered` adds the cases history cannot decide.\n")

    if problems:
        print(f"{len(problems)} unresolved reference(s) or structure defect(s):\n")
        for x in problems:
            print(f"  {x}")
        print("\nA document naming something that does not exist is confidently wrong,")
        print("and it will be followed. See FINDINGS #38. A document that does not parse")
        print("as what it is read as is worse: it looks right to everyone but the parser.")
        return 1

    _, wsummary = _check_withdrawal_register()
    print(f"sweep clean: references over {len(refs)} docs "
          f"({len(project_docs())} project + {len(skills)} skills "
          f"+ {len(github_docs())} under .github); {len(flags)} of our "
          f"flags, of which {bare_seen} bare occurrence(s) on a fenced command line of one "
          f"of our {len(scripts)} argparse scripts (pinned red and green); "
          f"{len(aspects)} aspects known and every exhaustive census of them checked "
          f"against that set (pinned red and green); structure: {len(skill_files())} SKILL.md "
          f"frontmatter, {len(gated_docs())} instruction docs for list indent, "
          f"{len(refs)} docs for a stranded edit tail "
          f"(pinned red on the real blob 1f6fb65:eval/FINDINGS.md and green; --selftest), "
          f"the same {len(refs)} for a {_DUP_FRAGMENT_WINDOW}-word fragment repeated inside "
          f"one claim (pinned red on the real blob 75dde71:DECISIONS.md and green; "
          f"--selftest), "
          f"{_index_row_count()} FINDINGS index rows in ONE table "
          f"(pinned red and green; --selftest to read the pins); {_findings_summary()}; "
          f"the out-of-range citation census pinned red and green over 10 cases and its "
          f"population pinned against ARCHIVE_PATHS (--citations is the producer, and "
          f"gates nothing); "
          f"regime ordinals: {len(ORDINALS)} known, headings read generically so an "
          f"unrecognised one is reported rather than missed (pinned red and green, "
          f"including the compound-ordinal variant; --selftest); "
          f"{wsummary}; renumber triage: {len(_load_triage())} adjudicated row(s), each "
          f"still matching exactly one line of the document it names")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--outline", metavar="FILE")
    ap.add_argument("--sweep", action="store_true")
    ap.add_argument("--renumbered", action="store_true",
                    help="citations of a finding number that has named more than one finding")
    ap.add_argument("--withdrawn", action="store_true",
                    help="live documents restating a figure declared retired in "
                         "eval/withdrawn.json; --at REV reads the corpus at a revision")
    ap.add_argument("--money", action="store_true",
                    help="live documents that state a `$` figure and call it an "
                         "expenditure; every one here is a list-price valuation of "
                         "tokens on a subscription account (#159). --at REV reads the "
                         "corpus at a revision, which is where the red control lives: "
                         "--money --at f598726 reports 21 blocks")
    ap.add_argument("--at", default="HEAD", metavar="REV",
                    help="revision --renumbered reads (default HEAD); the positive control "
                         "is a revision where a known-stale citation still stands")
    ap.add_argument("--findings", action="store_true",
                    help="the producer for any count of the findings log: bodies, index "
                         "rows and every live document's statement of the two")
    ap.add_argument("--count-triggers", action="store_true",
                    help="what each candidate findings-count trigger would cost over "
                         "today's corpus; the producer for DECISIONS.md's candidate "
                         "table, and never a gate")
    ap.add_argument("--citations", action="store_true",
                    help="the producer for any count of `#NN` in a live document that "
                         "names no finding; a census, never a gate (FINDINGS #146)")
    ap.add_argument("--json", action="store_true",
                    help="machine-readable output, where the command supports it")
    ap.add_argument("--selftest", action="store_true",
                    help="pin the FINDINGS-index checks in both directions, in memory")
    ap.add_argument("--all", action="store_true")
    a = ap.parse_args()

    if a.outline:
        return cmd_outline(a.outline)
    if a.findings:
        return cmd_findings(a.json)
    if a.count_triggers:
        return cmd_count_triggers(a.json)
    if a.citations:
        return cmd_citations(a.json)
    if a.selftest:
        return cmd_selftest()
    if a.renumbered:
        return cmd_renumbered(a.at)
    if a.withdrawn:
        return cmd_withdrawn(None if a.at == "HEAD" else a.at)
    if a.money:
        return cmd_money(None if a.at == "HEAD" else a.at)
    if a.sweep:
        return cmd_sweep()
    rc = cmd_sizes()
    if a.all:
        print()
        rc = cmd_sweep() or rc
    return rc


if __name__ == "__main__":
    sys.exit(main())
