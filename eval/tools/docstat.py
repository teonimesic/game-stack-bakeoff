#!/usr/bin/env python3
"""Analyse this project's documentation: structure, size, and names that do not exist.

`--sweep` asks two kinds of question. REFERENCES: does a name used in a doc resolve?
STRUCTURE: does a file parse as the thing it is being read as? The second kind was added
2026-08-23 after eleven documentation linters were measured against this repository and
produced over 14,000 alerts and two defects, both structural, both missed by every prose
linter (research/11-doc-linting-for-agents.md).

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
    python3 tools/docstat.py --renumbered       # citations of a finding that was renumbered
    python3 tools/docstat.py --renumbered --at REV   # ... as of any revision
    python3 tools/docstat.py --all

Exit code is 1 if --sweep finds anything unresolved, so it can gate a commit.
`--renumbered` never gates: it is a smell detector, and its second half is explicitly
undecidable. See `_check_renumbered_citations` for which half is which.
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
    """Every project markdown file OUTSIDE a dot-directory.

    `glob("**")` does not descend into `.claude/`, so this list contains no `SKILL.md`.
    That is now a PROPERTY of this helper and not a gap: the reference checks read
    `reference_docs()` instead, and the size report and the bare-trial-id ratchet read
    this one, because the ratchet is pinned to an exact count a larger corpus would move.
    """
    out = []
    for p in glob.glob(os.path.join(ROOT, "**", "*.md"), recursive=True):
        if is_vendored(p) or f"{os.sep}runs{os.sep}" in p:
            continue
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


def reference_docs() -> list[str]:
    """The corpus for the REFERENCE checks: every project doc, PLUS every skill.

    The skills are always-loaded instruction documents. A skill naming a flag or an aspect
    that does not exist is the exact defect this sweep was built for (#38), and until
    2026-08-23 nothing had ever looked: `project_docs()` globs, `glob` does not descend into
    dot-directories, and every skill lives under one.

    `project_docs()` is deliberately NOT widened to fix that. It also feeds the size report
    and the bare-trial-id ratchet, and the ratchet is pinned to an EXACT count; a larger
    corpus would move it silently, in the direction that makes the guard pass. A corpus is
    an input to a check (#60), so each check names the one it wants rather than inheriting
    whatever a shared helper happens to return.

    Measured with this code, 2026-08-23, over the 7 SKILL.md files:

      flag check    0 hits. Also 0 unresolved among the 17 flags the skills name WITHOUT
                    backticks, which the extraction does not see either way.
      aspect check  2 hits before fence-masking, 0 after. Both were the same line of
                    `audit-docs/SKILL.md` - the shell command that plants the phantom
                    aspects `feel` and `tuning` as this sweep's own positive control.
      ratchet       0 trial ids appear in any skill, and it is scoped to `findings/`
                    regardless, so the count is unmoved.
    """
    return sorted(set(project_docs()) | set(_all_skill_files()))


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
# `.agents/skills` was removed here on 2026-08-23 (#99): it was a second copy of every
# skill, never once in sync, and `--sweep` now FAILS on any SKILL.md outside
# `.claude/skills/<name>/`. Naming it here would re-admit the path this gate exists to
# reject.
GATED_DIRS = (".claude/skills", "tasks")


def gated_docs() -> list[str]:
    """Instruction documents the structure checks may hold to a format.

    The skills live under DOT-directories, which `glob(**)` does not descend into, so
    `project_docs()` has never contained a single `SKILL.md` and neither has any check
    built on it. They are globbed explicitly here. Reading a scope off a helper whose
    exclusions you have not checked is how a gate comes to run over 0 of its subjects.
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
    # rsync's. `backup_evidence.py` documents that it runs WITHOUT --delete, which is
    # why the copy is a superset (#115); the flag it names is rsync's, not ours.
    "--delete",
)


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

    Three questions, all cheap:
      1. does any number appear twice in the bodies?
      2. is every body finding present in the FINDINGS.md index, and vice versa?
      3. does the range stated in the FINDINGS.md header match the highest number?

    (3) matters because the header is what a reader trusts to know where the log ends, and
    it is edited by hand in three files. It has been wrong before.
    """
    import collections
    problems: list[str] = []
    fdir = os.path.join(ROOT, "eval", "findings")
    if not os.path.isdir(fdir):
        return [f"findings directory not found at {fdir} - this check ran over nothing"]

    seen: dict[int, list[str]] = collections.defaultdict(list)
    for p in sorted(glob.glob(os.path.join(fdir, "*.md"))):
        text = open(p, encoding="utf-8", errors="replace").read()
        lines = text.split("\n")
        fenced = _fence_mask(lines)
        for i, ln in enumerate(lines):
            if fenced[i]:
                continue
            m = re.match(r"^##\s+#?(\d+)[.\s]", ln)
            if m:
                seen[int(m.group(1))].append(os.path.basename(p))
    if not seen:
        return ["no findings parsed from eval/findings/ - the heading pattern has changed "
                "and this check is reading nothing (two styles exist: '## #19 -' and '## 26.')"]

    for num, files in sorted(seen.items()):
        if len(files) > 1:
            problems.append(
                f"finding #{num} is defined {len(files)} times ({', '.join(files)}) - a "
                f"citation to it resolves to more than one piece of work. Renumber the "
                f"later one; see #94 for why this keeps happening.")

    index_path = os.path.join(ROOT, "eval", "FINDINGS.md")
    if os.path.exists(index_path):
        itext = open(index_path, encoding="utf-8", errors="replace").read()
        indexed = {int(m) for m in re.findall(r"^\| \*\*(\d+)\*\*", itext, re.M)}
        body = set(seen)
        for n in sorted(body - indexed):
            problems.append(f"finding #{n} has a body but no row in eval/FINDINGS.md - it "
                            f"is uncitable, which is how a finding becomes invisible")
        for n in sorted(indexed - body):
            problems.append(f"eval/FINDINGS.md indexes #{n} but no body defines it")
        m = re.search(r"Findings #(\d+)-#(\d+)", itext)
        if m and body and int(m.group(2)) != max(body):
            problems.append(f"eval/FINDINGS.md says the log ends at #{m.group(2)}, but the "
                            f"highest finding is #{max(body)}")
    return problems


ORDINALS = ("first", "second", "third", "fourth", "fifth", "sixth", "seventh", "eighth",
            "ninth", "tenth", "eleventh", "twelfth", "thirteenth", "fourteenth", "fifteenth",
            "sixteenth", "seventeenth", "eighteenth", "nineteenth", "twentieth")


def _check_regime_ordinals() -> list[str]:
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
    """
    path = os.path.join(ROOT, "eval", "RUNS.md")
    if not os.path.exists(path):
        return [f"eval/RUNS.md not found at {path} - this check ran over nothing"]
    text = open(path, encoding="utf-8", errors="replace").read()
    lines = text.split("\n")
    fenced = _fence_mask(lines)
    seen: dict[str, list[int]] = {}
    for i, ln in enumerate(lines, 1):
        if fenced[i - 1] or not ln.startswith("#"):
            continue
        m = re.search(r"\b(" + "|".join(ORDINALS) + r")\s+comparability break", ln, re.I)
        if m:
            seen.setdefault(m.group(1).lower(), []).append(i)
    if not seen:
        return ["no comparability-break headings parsed from eval/RUNS.md - the wording "
                "has changed and this check is reading nothing"]
    problems = []
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


def _git(*args: str) -> str:
    """git in the repository this file lives in. Empty string on failure, never a raise.

    `check=False` is the point, not an oversight: several calls here ASK a question whose
    negative answer is a non-zero exit - `cat-file -t` on a path a parent does not have, or
    `blame` on a file that revision never contained. Raising on those would turn a normal
    reading into a crash. The exit code is read (#105); it is just read here, once, instead
    of at every call site.
    """
    try:
        r = subprocess.run(["git", "-C", ROOT, *args], capture_output=True, text=True,
                           check=False)
    except (OSError, ValueError):
        return ""
    return r.stdout if r.returncode == 0 else ""


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

    listing = (_git("ls-files") if hist.worktree
               else _git("ls-tree", "-r", "--name-only", rev))
    files = [f for f in listing.split("\n")
             if f.endswith(".md") and "/runs/" not in f and not is_vendored(f)]

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
    print(f"\nUNDECIDABLE - {len(undecided)}. History cannot say; a person must read these:\n")
    for s in undecided:
        print(f"  {s}")
    print("\nNever renumber a finding to satisfy this. The number in eval/findings/ is")
    print("the published one; the citation is what is wrong.")
    return 0


def cmd_sweep() -> int:
    """Names in docs that do not resolve, and files that do not parse as what they are.

    Deliberately CONSERVATIVE. Every category here has produced a real defect, but a
    false positive costs more than a false negative: it trains the reader to skip the
    output, and then the real hit is invisible. When unsure, say nothing.
    """
    docs = project_docs()
    refs = reference_docs()  # docs + skills; see why they are two corpora, not one
    flags, aspects = _argparse_flags(), _aspect_ids()
    problems: list[str] = []

    for p in refs:
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
            lines = text.split("\n")
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
                if re.search(r"(no `\w+` judge|not built|candidate|does not exist|retired|"
                             r"superseded|do not name them|phantom|plant\w*)", ln, re.I):
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
    # THE PROPERTY IS THE ADDRESS, NOT THE DIRECTORY NAME. This does not ban `.agents/`; it
    # requires that a SKILL.md live at `.claude/skills/<name>/SKILL.md` and nowhere else, so
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
    SKILLS_ROOT = os.path.join(ROOT, ".claude", "skills")
    skills = sorted(_all_skill_files())
    for sk in skills:
        if os.path.dirname(os.path.dirname(sk)) == SKILLS_ROOT:
            continue
        problems.append(
            f"{os.path.relpath(sk, ROOT)}: a skill outside .claude/skills/<name>/, which "
            f"AGENTS.md names as the sole authoritative path. A second copy is a second "
            f"source of truth and only one of them gets edited (#99).")
    # THE ADDRESS IS AN INPUT TO THE CHECK (#60). Finding nothing is the one result this
    # check cannot distinguish from being pointed at the wrong place, so say so out loud
    # rather than returning the same silence a clean repository returns.
    if not skills:
        problems.append(
            f"no SKILL.md found anywhere under {os.path.relpath(SKILLS_ROOT, ROOT)} or "
            f"outside it. The skills exist; this check is looking at the wrong root.")

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

    # STRUCTURE, not references. Both of these are schema questions with a demonstrated
    # true positive in this repository and no judgement in the answer; see their
    # docstrings for the defect each was bought with and its measured false-positive count.
    problems += _check_skill_frontmatter()
    problems += _check_list_indent()
    problems += _check_findings_integrity()
    problems += _check_regime_ordinals()

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

    print(f"sweep clean: references over {len(refs)} docs "
          f"({len(refs) - len(skills)} project + {len(skills)} skills); {len(flags)} of our "
          f"flags, {len(aspects)} aspects known; structure: {len(skill_files())} SKILL.md "
          f"frontmatter, {len(gated_docs())} instruction docs for list indent")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--outline", metavar="FILE")
    ap.add_argument("--sweep", action="store_true")
    ap.add_argument("--renumbered", action="store_true",
                    help="citations of a finding number that has named more than one finding")
    ap.add_argument("--at", default="HEAD", metavar="REV",
                    help="revision --renumbered reads (default HEAD); the positive control "
                         "is a revision where a known-stale citation still stands")
    ap.add_argument("--all", action="store_true")
    a = ap.parse_args()

    if a.outline:
        return cmd_outline(a.outline)
    if a.renumbered:
        return cmd_renumbered(a.at)
    if a.sweep:
        return cmd_sweep()
    rc = cmd_sizes()
    if a.all:
        print()
        rc = cmd_sweep() or rc
    return rc


if __name__ == "__main__":
    sys.exit(main())
