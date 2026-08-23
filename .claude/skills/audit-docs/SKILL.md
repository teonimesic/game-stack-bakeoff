---
name: audit-docs
description: "Audit this project's documentation against reality and against its own rules: the mechanical sweep for names that do not exist, the rule-firing audit, and pruning."
when_to_use: "After a working session; a rule failed to prevent what it was written for; before trusting a document that names code; the docs feel stale. Trigger phrases: audit the docs, are the docs current, why did that rule not fire, check for phantom names."
---

# Auditing the documentation

The docs are an instrument, and the same question applies to them as to any grader:
*what would it take for this to be wrong?*

## 1. The mechanical sweep — run the tool, do not do this by hand

```
cd eval
python3 tools/docstat.py --sweep      # references + structure; exit 1 if anything fails
python3 tools/docstat.py              # size and token cost of every project doc
python3 tools/docstat.py --outline FILE   # fence-aware heading map
python3 tools/docstat.py --renumbered # citations of a finding number that has moved
```

`--sweep` asks two kinds of question:

| | asks | bought with |
|---|---|---|
| **references** | does a flag, aspect or criterion a doc names actually exist? | `RUBRIC.md` named five judges that do not exist (#38) |
| **structure** | does a file parse as the thing it is read as? | 5 of 7 skills had frontmatter no YAML parser could read; `AGENTS.md` rules 10-16 detached from their own list |

**`--renumbered` asks the third kind, and it is the one the other two cannot ask: does a
name still mean what its author meant?** When two worktrees allocate the same finding number
the merge renumbers one of them, and every document that already cited it now points at a
stranger *while still resolving* — so nothing above can see it. It derives the map of moved
numbers from git history, resolves each citation against the numbering its own authoring
commit saw, and prints two lists: **decided** (a verdict, and the half `--sweep` echoes) and
**undecidable** (a short list to read, because a merge writes the renumber and the citation
in one commit and there is no ordering inside a commit). 27 stale citations across eight
corpora on first run, plus two more that landed while it was being written (#118).

Never renumber a finding to satisfy it. The number in `eval/findings/` is the published one;
the citation is what is wrong.

**The references half reads the skills too, including this one** — since 2026-08-23 (task
44). It did not before: the corpus was built with `glob`, `glob` does not descend into
dot-directories, and every skill lives under one, so for the whole life of the sweep the
always-loaded instruction documents were the only files it could not see. Measured when
they were let in: **0 false positives**, after fenced lines stopped counting as claims.

Prose is executed by a person, and **a person does not get an argparse error**. A file
naming a flag, path, aspect or criterion that does not exist is worse than one that says
nothing: it is confidently wrong and it will be followed.

The structure half exists because eleven documentation linters were measured against this
repository and produced **over 14,000 alerts and two defects, both structural**
(`research/11-doc-linting-for-agents.md`). Do not add a prose linter; that survey already
came out.

**Do not hand-roll this scan.** Four hand-written versions were wrong before the tool
existed, each in a way whose output looked like a real finding:

| attempt | failure |
|---|---|
| fence-blind heading scan | reported a GDScript `##` doc-comment inside a ``` block as a malformed heading |
| first sweep | 73 hits, ~65 false — `--max-turns` is the claude CLI's, not our argparse |
| narrowed sweep | 2 hits, both false; the path check had **0** true positives |
| aspect check | went silent under a planted phantom — a file-wide exemption let one legitimate "candidate" sentence silence every check in that file |

The last one matters most: the sweep read **clean**, and clean-because-nothing-is-wrong
was indistinguishable from clean-because-it-cannot-fire. Only the planted-phantom control
separated them.

**If you change the tool, re-run both controls**, or you have not changed it — you have
replaced it with something that agrees with you:

```
# negative: clean corpus -> exit 0
python3 tools/docstat.py --sweep

# positive: plant a phantom aspect -> exit 1
cp judge/JUDGING.md /tmp/jm.bak
printf '\nIf `feel` and `tuning` rank alike they are one judge.\n' >> judge/JUDGING.md
python3 tools/docstat.py --sweep ; echo "expect exit 1"
cp /tmp/jm.bak judge/JUDGING.md

# positive: unquote a skill description so it contains ": " -> exit 1
# positive: append "10. x", a 4-space line, a blank, then a 3-space line -> exit 1
```

**Plant the phantom in prose, never inside a ``` fence** — a fenced line is not read as a
claim (see below), so a control planted in a code block goes green and tests nothing. The
`printf` above appends an unfenced sentence for exactly that reason. This is the same shape
as the file-wide exemption in the table above: the control agrees with you because it never
ran, not because the tool is sound.

Both structure checks arrived on an **already-repaired** repository, which is the state in
which a gate has never been seen to fail. Plant the defect each names before trusting it.

**What it deliberately does not check**, and why — do not "fix" these by adding them back:

- **Paths.** Docs legitimately write them relative to a context stated in prose or a table
  cell: `README.md` names `tools/boundary.gd` in a row about `template-godot/`, where it
  exists. Measured 0 true positives, 2 false. A check that cannot be made reliable is
  removed, not tuned until it is quiet — tuning until quiet is how a check comes to pass
  vacuously.
- **Foreign flags.** `--max-turns`, `--permission-mode` belong to the claude CLI.
- **`code` and `look` as aspect ids.** Ordinary words that appear as inline code for other
  reasons.
- **`findings/`.** An archive whose subject matter is naming superseded things.
- **Anything inside a ``` fence, for the aspect check.** A fenced line is a command to run
  or an output to expect; it asserts nothing about its own arguments. This is what let the
  skills into the corpus: the only aspect hit across all 124 documents was the `printf`
  above, in this file, planting `feel` and `tuning` as the sweep's own positive control.
  The exemption is **line-scoped** — a file-wide one once let a single legitimate
  disclaimer silence every aspect check in its file, and the control went green.
- **Root blocks indented 1-3 spaces, in general.** The indent check asks only about a
  continuation under a **2+ digit** ordered marker, which is the only form with a true
  positive here. The broad form fires on `tasks/` files where nothing is wrong — 2-space
  lists and prose introduced by a colon, with no list item above them. A gate that fails
  on correct input gets disabled.
- **`eval/findings/`, `eval/FINDINGS.md`, `eval/RUNS.md` for structure.** The archive
  records what was true when it was written, including broken shapes it is about;
  reformatting one to satisfy a gate edits evidence.

## 2. The rule audit

For each rule: **has it ever fired?** *Fired* means it changed what happened, not that it
was read. Of those that fired, did they fire correctly?

- **Fired and was wrong as written** → rewrite it. Several rules here were violated by the
  person who had just written them; that is evidence about the rule, not the author.
- **Never fired** → is it preventing failures silently, or dead weight? Those look
  identical from outside. The test: can you construct a plausible situation where it
  would fire? If yes, keep it.
- **Fired and was ignored** → it is in the wrong place, or buried under rules that do not
  earn their space.

**The commonest defect is a trigger written in the vocabulary of the incident that
produced it.** "Do not run judge or LLM calls during the build" missed *subagent* — it
named mechanisms when what mattered was the resource. State what the rule protects, not
what went wrong last time. A trigger that is a list must be re-derived by every reader who
meets an item not on it.

## 3. Prune

Every rule that does not earn its place makes the ones that do harder to find. A document
nobody finishes reading protects nothing. When a rule is superseded, **replace** it.

Two exceptions, both about numbers rather than rules:

- A **published figure later proven wrong** stays marked, because someone may have acted
  on it.
- A **superseded reading of evidence** stays marked where the reading was published — the
  numbers were right, the inference was not, and deleting it hides that the inference
  moved.

## 4. What is a doc and what is a skill

- **Skill** — a procedure with a start and an end, invoked when you are doing that thing.
- **Doc** — what is true: evidence logs, ledgers, contracts, decisions.
- **Always-loaded rules** — constraints belong in `AGENTS.md`, never a skill. A constraint
  you have to remember to invoke is a constraint that will fail.

A skill that restates a doc creates two sources of truth. Every skill here names its
authoritative file and says explicitly: if they disagree, the doc wins and the skill is
the bug.

## The test

Not whether the documentation is thorough. **Whether the next session makes new mistakes
instead of these ones.**
