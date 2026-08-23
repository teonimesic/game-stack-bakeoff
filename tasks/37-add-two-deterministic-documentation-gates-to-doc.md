---
established_by: Two structure checks added to cmd_sweep in eval/tools/docstat.py, commit 3308f1e on branch task-37-doc-gates, not pushed. GATE 1, SKILL.md frontmatter: every SKILL.md under .claude/skills and .agents/skills must yaml.safe_load to a mapping carrying name and description; 13 files. GATE 2, list indent, the NARROW form per task 36: a top-level ordered marker of 2 or more digits whose post-blank-line continuation is indented less than the marker width; 61 instruction docs. NEGATIVE CONTROL: sweep exit 0 on the repaired repository, 108 docs, 13 SKILL.md, 61 instruction docs, re-run after every edit including the last. POSITIVE CONTROLS, all against the committed code: unquoting one skill description so its value contains a colon-space gives exit 1 with the YAML parse error, the exact shape that silently emptied 5 of 7 skills; reconstructing the pre-task-36 AGENTS.md gives exit 1 with 5 hits at lines 397, 419, 439, 455 and 459, which is exactly the five detached paragraphs research/11 section 1.1 names, so the check reproduces the original defect rather than only a synthetic one; a planted 3-space continuation under a 10. marker fires in tasks/ and in .agents/skills/refine/SKILL.md. VARIANTS: a dropped description key fires; PyYAML unimportable fails closed with an install instruction rather than skipping; either check pointed at a root with no subjects reports an empty corpus instead of green. FALSE POSITIVES: 0. Measured with the shipped code over all 365 markdown files in the main checkout with the scope removed, not only the 108 in-scope ones. The broad indent form was measured at 7 hits by an independent implementation here against task 36's 15, all in tasks/ and all legitimate in both, so the narrow form was taken. NOT GATED, deliberately: eval/findings/, eval/FINDINGS.md and eval/RUNS.md, because the archive records the broken shapes it is about; an identical plant appended to eval/FINDINGS.md does NOT fire, so the exclusion is proven rather than assumed. Scope addresses root docs as a property, any markdown file at the repo root, not the six names present today. SIDE FINDING, filed as task 44: glob with a double-star does not descend into dot-directories, so project_docs never contained a single SKILL.md and the reference checks have never read one; extending them gives 4 hits, every one the phantom-aspect worked example inside audit-docs/SKILL.md, so it was left scoped out and documented at project_docs. DOCS: DECISIONS.md gains a decision that documentation is gated on structure and names, never prose, with the 14000-alerts-2-defects measurement; both copies of the audit-docs skill updated with the two question kinds, the new controls and the two exclusions. Other docstat modes re-verified: outline and sizes both unchanged.
id: 37
title: Add two deterministic documentation gates to docstat.py
status: done
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

## Specification note from task 36 (2026-08-23), before you write the check

Task 36 fixed the `AGENTS.md` indent defect and scanned the whole repository afterwards. Its
result decides how you should scope this gate, and getting it the wrong way round produces a
check that fires where nothing is wrong.

**The narrow form — "an ordered-list marker of 2+ digits whose continuation lines are indented
less than the marker width" — currently returns 0 across all 117 markdown files.** That is a
gate you can add today and it passes. `AGENTS.md` was the only file that ever crossed from
single- to double-digit markers.

**The broad form — "no root-level block indented 1-3 spaces" — fails immediately on 15 hits
across 10 files in `tasks/`.** Task 36 inspected every one and none is this defect: they are
2-space-indented lists and prose blocks introduced by a paragraph ending in a colon, with no
ordered-list item preceding them. Nothing lost a parent.

So the broad form would fail on correct input on its first run, and **a gate that fails on
correct input gets disabled** — the failure `AGENTS.md` rule 16 names and the reason
`docstat.py` already removed its path check rather than tuning it quiet.

Take the narrow form unless you can show the broad one earns its false positives. If you do take
the broad form, fix or exempt the 15 `tasks/` hits **in the same change**, and say why each
exemption is legitimate rather than adding a blanket directory skip.

The second gate — YAML frontmatter parseability — has no equivalent ambiguity: it either
`safe_load`s or it does not. Task 35 is fixing the five files that currently fail, so verify the
repository is clean before adding the gate, and pin it red against a deliberately broken fixture
rather than trusting that it would have caught the original.
