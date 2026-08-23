---
id: 119
title: No gate detects a half-overwritten paragraph, and a 12-word in-block n-gram trigger measures red 4 green 0
status: in_progress
priority: 3
refs: eval/tools/docstat.py, DECISIONS.md, tasks/99, tasks/116
done_when: 'docstat.py grows an in-block duplicate-fragment check, pinned in both directions: red on the pre-fix DECISIONS.md at commit 75dde71 (4 windows of the ''40 of 56 matrix trials at the ceiling with zero variance, not merely near it'' fragment) and green on the live corpus, plus a mutant that deletes the check and a variant that feeds it a duplicated fragment split across a list-item line break. OR a measurement showing the false-positive count does not hold up, which retires it.'
---

Task 116 removed a duplicated, half-overwritten paragraph fragment from DECISIONS.md's Open section. Every existing gate was green with the defect in place - docstat.py --sweep, --findings, --withdrawn, --renumbered, linkcheck.py, tasks.py check and withdrawn_control.py all exit 0 both before and after the repair. Task 99 is the same class in eval/FINDINGS.md line 6. Three instances, nothing mechanical looking for them.

Measured 2026-08-23 in the task-116 worktree, so the next agent does not re-derive it.

SENTENCE-LEVEL EXACT MATCH DOES NOT WORK. An in-block repeated sentence of 40+ chars scores 0 on the live corpus AND 0 on the pre-fix DECISIONS.md - it misses the real defect entirely, because the duplicated span is a FRAGMENT starting mid-sentence and ending mid-sentence: the tail of one sentence plus the head of the next. This is the obvious property and it is a complete false negative.

12-WORD N-GRAM WITHIN A BLOCK DOES WORK. Repeated 12-word window inside one paragraph or list item, fenced code stripped and markdown table rows excluded:
  RED   pre-fix DECISIONS.md: 4 hits, all four overlapping windows of the true defect.
  GREEN repaired live corpus: 2 hits over 39 live md files, both in .agents/skills/audit-docs/SKILL.md and both a DELIBERATELY repeated shell recipe inside the fence opened at its line 119. They survive only because a non-greedy triple-backtick regex mis-parses its lines 143 and 146, which carry literal triple backticks inside a printf string. A line-state fence parser drops both, giving 0 false positives.

Shorter windows are worse and the count grows with the corpus, which is the open-class signature AGENTS.md warns about: n=8 gives 58 live hits, n=10 gives 27, n=12 gives 8 before the table exclusion. Choose n on the live false-positive count, not on which sounds more general.

Do not ship it without the mutant and the variant. The variant that matters is a duplicated fragment split across a list-item line break, because that is the shape the real one had, and splitting blocks on blank lines alone may not group it.
