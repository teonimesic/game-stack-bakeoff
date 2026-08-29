---
id: 208
title: 'renumbered-citation corpus: code files'
status: todo
priority: 3
refs: 'eval/tools/docstat.py (_check_renumbered_citations corpus, _tracked_md), eval/findings/documentation.md #211, tasks/207'
done_when: Either _check_renumbered_citations reads code files for finding-number citations, with its corpus asserted against a walking oracle the way the doc corpus one is, and both directions pinned in the selftest (a stale code citation planted at a historical commit is reported; a correct one is not), and the false-positive cost over the live tree measured before shipping - or the corpus is deliberately pinned to documents with the reason recorded beside the check and in this ticket, in which case the finding stands as the record and code-file citations are read only by passes. Whichever way, the finding text in documentation.md must name the real outcome instead of task <TASK>.
---

Finding #211 (2026-08-29): the renumbered-citation check selects its corpus with _tracked_md, so a stale #N inside a .py docstring or comment is invisible to it. Measured: 8 stale code-file citations across two sessions (the judge_ledger/field_sweep pair in task 206, six more in task 207), 0 caught by the gate, every one found by manual reading, while --renumbered reported exit 0 in the same window. Each was correct when written - #119 changed hands four times on 2026-08-23 - so no resolve-check can see it either.
