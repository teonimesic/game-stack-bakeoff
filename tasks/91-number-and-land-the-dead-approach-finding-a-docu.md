---
id: 91
title: 'Number and land the dead _approach finding: a documented repair that could not run'
status: in_flight
priority: 3
refs: eval/judge/bot_platformer.py, eval/findings/certifies-nothing.md row 5 of the unity__t0 chain, tasks/18, tasks/76
done_when: a numbered finding exists in eval/FINDINGS.md stating that PlatformerBot._approach never had a caller, that the archive attributed its null result to a second loop shadowing it when nothing ran it at all, and that task 18's stated mechanism named it; docstat.py --sweep green with the finding indexed
---

Task 76 measured it: git log -S self._approach finds no commit in which the call site ever appears, and a spy on the method counts 0 calls across a full probe session while a spy on _walk_toward counts 390 (positive control for the spy itself). The method was deleted in task 76's branch and its measured history folded into _walk_toward's docstring, so the CODE is repaired - what is missing is the numbered finding. It is filed rather than taken because ten tasks were in flight on 2026-08-23 and several allocate finding numbers; the work skill says hand a number to the orchestrator rather than collide. THE SHAPE, which is why it is worth a number: eval/findings/certifies-nothing.md says 'a fix that changes nothing at all is evidence about where the code is' and reached the right conclusion from the wrong cause - it read byte-identical evidence as proof that _combat shadowed _approach, when _approach could not have run either way. A second copy of a loop and an unreachable copy of a loop are indistinguishable from the outside by exactly the observation that was made.
