---
id: 167
title: DECISIONS.md says 3 scene mutants in a way that also reads as 3 per failure mode
status: todo
priority: 4
refs: DECISIONS.md, eval/judge/scene_mutants.py, eval/SCENES.md, tasks/162, tasks/164
done_when: The sentence states the count and the mapping without either reading being available - 1 variant and 3 mutants, 1 mutant per reporting failure, with the 3 failures named - and the count is checked against `python3 eval/judge/scene_mutants.py` rather than against the sentence it replaces. `docstat.py --sweep` and `docstat.py --findings` stay green.
---

DECISIONS.md, the scene-parallax entry, reads "`scene_mutants.py` holds both directions: a variant reporting `offset` inside its own span, and 3 mutants that break a layer's reporting in each of those ways." "3 mutants ... in each of those ways" reads as 3 per failure mode against a registry that has 3 in total, 1 per mode. A reader taking the first reading would look for 9 and conclude the registry had been cut. Raised by CodeRabbit on PR #40 against a paragraph that had merged into main minutes earlier; declined there because it belongs to the scene work rather than to a play-bot repair, and AGENTS.md says not to edit a document another agent is working in.
