---
id: 147
title: 'The CI register narrates its own history: run ids, past timings and variance history in a document that states what runs'
status: todo
priority: 3
refs: ''
done_when: every dated timing, run id and change-history sentence in .github/workflows/README.md either states a standing instruction with its producer command beside it, or has moved to eval/findings/ or eval/RUNS.md; the register's own job - what runs in which tier and every gate deliberately left out with the reason - is intact and still names every workflow step; and docstat.py --sweep and linkcheck.py are green
---

CodeRabbit flagged .github/workflows/README.md lines 19-32 and 41-42 on PR #23 (task 140) under the .coderabbit.yaml rule that a live document states the choices in force and is not a log of what happened. The finding is valid and was declined THERE rather than acted on, because git log -L 19,32 and -L 41,42 both name c29429a (task 135, PR #22), which landed on main while #23 was open - editing a section another task had just landed, inside an unrelated pull request, is what .agents/skills/work/SKILL.md section 4 forbids. The content at issue: a floor timing dated 2026-08-24 with per-tool step times, a named CI run id, and a sentence recording that two selftests became gated. What a reader needs is what runs in which tier and how to re-derive the timings (ci_minutes.py), not the history of how the numbers moved.
