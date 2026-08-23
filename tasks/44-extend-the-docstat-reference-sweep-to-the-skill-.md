---
id: 44
title: Extend the docstat reference sweep to the skill files it has never read
status: open
priority: 4
refs: eval/tools/docstat.py, tasks/37-add-two-deterministic-documentation-gates-to-doc.md
done_when: python3 eval/tools/docstat.py --sweep reads the 13 SKILL.md files under .claude/skills and .agents/skills with the flag and aspect-id checks, at 0 false positives, pinned by a planted phantom aspect inside a SKILL.md going red; or the check is left scoped out and the reason is recorded in docstat.py next to the scope
---

## What is this thing?

`eval/tools/docstat.py --sweep` is this project's mechanical documentation check. It asks two
kinds of question. **Reference** checks ask whether a name a document uses resolves -- is this
`--flag` in some argparse, is this an aspect id in `eval/judge/aspects.py`? That half caught
`eval/judge/RUBRIC.md` naming five judge aspects that do not exist (finding #38). **Structure**
checks, added by task 37, ask whether a file parses as the thing it is read as.

The corpus for the reference checks is `project_docs()`, which globs `ROOT/**/*.md`.

## What is wrong, and how do we know?

**Python's `glob` does not descend into dot-directories**, and the project skills live in
`.claude/skills/` and `.agents/skills/`. So `project_docs()` has never returned a single
`SKILL.md`, and the reference checks have never read one -- in a repository whose own rule is
that the address is an input to the check (finding #60).

Measured 2026-08-23 while doing task 37, by running the existing flag and aspect-id checks over
the 13 skill files directly: **4 hits, all false.** All four are the same worked example --
`audit-docs/SKILL.md` documents the sweep's own positive control, a shell line that plants the
phantom aspect ids `feel` and `tuning` into `judge/JUDGING.md`, and the aspect check reads that
demonstration line as if it were a claim.

Task 37 therefore scoped only its two new structure checks over the skills, via an explicit
glob in `gated_docs()`, and left the reference checks where they were, rather than turning on a
check that fails on correct input on its first run.

## Why does it matter?

The seven skills are procedures an agent follows. A skill naming a flag or an aspect that does
not exist is the exact defect the sweep was built for, and nothing has ever looked. The size is
small -- 13 files -- so the risk is bounded, but it is unmeasured, and "unmeasured" is what the
sweep exists to remove.

## What should be done?

Include the skill files in the reference corpus and exempt the demonstration. The exemption
must be **line-scoped, not file-scoped**: `docstat.py` already records that a file-wide
exemption let one legitimate disclaimer silence every aspect check in a file and the
planted-phantom control went green. A line inside a fenced block, or one that is a shell
command rather than prose, is the natural discriminator -- `_fence_mask()` already exists and
may remove all four hits on its own, so measure that first.

## Outcomes that count as success

| result | what it means |
|---|---|
| skills in the corpus, 0 false positives, and a phantom planted in a SKILL.md goes red | turn it on |
| the exemption needed to reach 0 is broader than one line | leave the skills scoped out and record the measured false-positive count in `docstat.py`, the way the path check was |

## What NOT to conclude

Do not widen `project_docs()` itself without re-measuring every check built on it -- it also
feeds the size report and the trial-id ratchet, and the ratchet is set to an exact count that a
larger corpus would move.
