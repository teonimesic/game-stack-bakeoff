---
name: audit-docs
description: Audit this project's documentation against reality and against its own rules: the mechanical sweep for names that do not exist, the rule-firing audit, and pruning.
when_to_use: After a working session; a rule failed to prevent what it was written for; before trusting a document that names code; the docs feel stale. Trigger phrases: audit the docs, are the docs current, why did that rule not fire, check for phantom names.
---

# Auditing the documentation

The docs are an instrument, and the same question applies to them as to any grader:
*what would it take for this to be wrong?*

## 1. The mechanical sweep — run the tool, do not do this by hand

```
cd eval
python3 tools/docstat.py --sweep      # names that do not resolve; exit 1 if any
python3 tools/docstat.py              # size and token cost of every project doc
python3 tools/docstat.py --outline FILE   # fence-aware heading map
```

Prose is executed by a person, and **a person does not get an argparse error**. A file
naming a flag, path, aspect or criterion that does not exist is worse than one that says
nothing: it is confidently wrong and it will be followed.

**Do not hand-roll this scan.** Four hand-written versions were wrong before the tool
existed, each in a way whose output looked like a real finding:

| attempt | failure |
|---|---|
| fence-blind heading scan | reported a GDScript `##` doc-comment inside a ``` block as a malformed heading |
| first sweep | 73 hits, ~65 false — `--max-turns` is the Codex CLI's, not our argparse |
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
```

**What it deliberately does not check**, and why — do not "fix" these by adding them back:

- **Paths.** Docs legitimately write them relative to a context stated in prose or a table
  cell: `README.md` names `tools/boundary.gd` in a row about `template-godot/`, where it
  exists. Measured 0 true positives, 2 false. A check that cannot be made reliable is
  removed, not tuned until it is quiet — tuning until quiet is how a check comes to pass
  vacuously.
- **Foreign flags.** `--max-turns`, `--permission-mode` belong to the Codex CLI.
- **`code` and `look` as aspect ids.** Ordinary words that appear as inline code for other
  reasons.
- **`findings/`.** An archive whose subject matter is naming superseded things.

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
