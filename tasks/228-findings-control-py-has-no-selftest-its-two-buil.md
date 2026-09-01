---
id: 228
title: 'findings_control.py has no --selftest: its two build() refusals are unpinned'
status: todo
priority: 2
refs: CLEANUP-LOG pass 39; .agents/skills/tasks/SKILL.md
done_when: 'python3 eval/tools/findings_control.py --selftest exists, prints ok/FAIL per assertion and exits 1 on failure, asserting: (a) a mutant whose anchor is absent from docstat.py refuses; (b) a mutant whose anchor is AMBIGUOUS refuses — built at run time from a string measured to occur more than once in the live docstat.py, never a hardcoded line (the code moves). Read .github/workflows/README.md before adding the mode: ci_minutes.py --controls''s selftest census counts scripts declaring --selftest and asks that a workflow step or git hook names each one, so the new mode must be added to the workflow step that runs findings_control.py, or the census goes red. Plain controls and --all-mutants must still exit 0.'
---

Pass 39 (CLEANUP-LOG) added the ambiguity refusal to build() — a mutant anchor occurring more than once in docstat.py must SystemExit rather than silently mutate whichever copy came first — beside the existing absent-anchor refusal, and verified both by ad-hoc invocation in that session only. Nothing in the repository pins them. tasks_mutants.py pins its drifted-anchor refusal with a --selftest mode and is named in CI for it; findings_control's guards are one edit away from silent removal, and the failure is invisible when they go: a deleted guard just means the next ambiguous anchor mutates the first copy and the controls grade a mutation the file did not name.
