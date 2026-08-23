---
id: 37
title: Add two deterministic documentation gates to docstat.py
status: open
priority: 3
refs: research/11-doc-linting-for-agents.md, eval/tools/docstat.py
done_when: python3 eval/tools/docstat.py --sweep exits 1 on a planted unparseable SKILL.md frontmatter and on a planted 3-space continuation under a two-digit list marker, and exits 0 on the repaired repository; if either check cannot be made to run at 0 false positives across the 99 project markdown files, drop that check and record the measured false-positive count
---
## What is this thing?

`eval/tools/docstat.py` is this project's mechanical documentation sweep. `--sweep` asks whether
names used in the docs **resolve** -- it is what caught `eval/judge/RUBRIC.md` naming five judge
aspects that do not exist (#38). It exits 1 when it finds anything, so it can gate a commit.

## What is wrong, and how do we know?

Eleven documentation linters were run against this repository on 2026-08-23 (see
`research/11-doc-linting-for-agents.md`). Together they produced over 14,000 alerts and found
**two** defects. Both were found by checks on structure or schema, not prose. Neither is covered
by `docstat.py` today:

1. **Unparseable SKILL.md frontmatter** -- 5 of 7 project skills, found by
   `claude plugin validate --strict` and corroborated by PyYAML and vale. Task 35.
2. **List continuations one space short under a two-digit marker** -- 5 paragraphs in `AGENTS.md`
   structurally outside the rule they belong to. Task 36.

Every prose linter surveyed missed both. `remark-preset-lint-recommended` reported `AGENTS.md`
completely clean while remark's own parser was silently detaching its paragraphs.

## Why does it matter?

These are the only two checks with a demonstrated true positive here, and both are cheap and
deterministic. Without them the two defects recur the next time a description gains a colon or a
numbered list passes item 9.

They belong in `docstat.py` rather than in a new linter because `docstat.py` already exists,
already gates on exit 1, and already carries the conservatism this repository needs. Its own
comment at lines 195-199 records that a path-resolution check was tried and removed for measuring
"0 true positives, 2 false". **That judgement is correct and must not be undone.** An independent
re-measurement on 2026-08-23 found 265 distinct backtick-quoted paths, 68 unresolved, 0 true
positives.

## What should be done?

Add two checks to `cmd_sweep()` in `eval/tools/docstat.py`:

- **Frontmatter parse.** For every `SKILL.md` under `.claude/skills/` and `.agents/skills/`,
  `yaml.safe_load` the frontmatter and report a failure. Roughly ten lines. Shelling out to
  `claude plugin validate --strict` is the alternative but needs a plugin manifest wrapper.
- **List continuation indent.** For each top-level ordered marker, compute the required
  continuation width from the marker's digit count, and report any post-blank-line continuation
  indented less than that but more than zero. Roughly twenty lines. Must be fence-aware --
  `docstat.py` already has `headings()` doing fence tracking for exactly this reason.

**Both need a positive control and a negative control**, per rule 1: plant a bad SKILL.md and a
3-space continuation, confirm exit 1; run against the repaired repository, confirm exit 0.

## Outcomes that count as success

| result | what it means |
|---|---|
| both checks fire on planted defects and are silent on the repaired repo | add them |
| a check cannot reach 0 false positives across the 99 project markdown files | **drop that check** and record the measured false-positive count, the way the path check was dropped |

## What NOT to conclude

Do not add a markdown linter, a prose linter, or a readability gate as part of this. The survey
measured all of them and none earns its place; the reasoning is in
`research/11-doc-linting-for-agents.md` section 6.
