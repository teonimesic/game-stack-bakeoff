---
id: 91
title: 'Number and land the dead _approach finding: a documented repair that could not run'
status: done
priority: 3
refs: eval/judge/bot_platformer.py, eval/findings/certifies-nothing.md row 5 of the unity__t0 chain, tasks/18, tasks/76
done_when: a numbered finding exists in eval/FINDINGS.md stating that PlatformerBot._approach never had a caller, that the archive attributed its null result to a second loop shadowing it when nothing ran it at all, and that task 18's stated mechanism named it; docstat.py --sweep green with the finding indexed
established_by: 'Landed as FINDINGS #133 in eval/findings/certifies-nothing.md, indexed in eval/FINDINGS.md, range bumped to #19-#133 in AGENTS.md and README.md; docstat.py --sweep exit 0, 115 index rows, tasks.py check 99 tasks well-formed, bot_mutants.py exit 0 with 36 criteria pinned both ways. RE-MEASURED rather than quoted: six commits have touched eval/judge/bot_platformer.py, _approach is defined in five of them and no tree at any of them contains a call site self._approach( - only the def line and two comments. A spy on the class attribute counts 0 calls at d2b683f across a session where 20 of 20 criteria pass, against positive controls _nearest 391, _edge_distance 72, _combat 1, _hurt 1; today _walk_toward 390 and _edge_distance 171. Pinned the other way: a direct call takes the counter 0 to 1, so the zero is the code''s and not the wrapper''s. SECOND NULL FOUND, bigger than the one the ticket named: at 9fc044a, the commit that published #82, _edge_distance''s only call site is line 734 inside _approach and _EDGE_JUMP_WITHIN is read only at line 735 inside it, and the spy measures _edge_distance at 0 calls - so the sentence the re-grade with gap-crossing alone left ts__t0 byte-identical at 0.793, quoted there to falsify the pit hypothesis, was the only obtainable result. #82''s headline is NOT retracted, the _nearest height fix is live at 391 and 1796 calls. Both archive sites marked with a block citing #133; task 18''s mechanism sentence covered as the third rest. The ticket''s own phrasing was wrong and is corrected in it and in the module docstring: git log --all -S self._approach now returns two commits, both of which added task 76''s docstring quoting that command, so the check refuted itself - the stable statement is the call-site census. Adding the finding took the bare-trial-id ratchet 18 to 19 and turned the sweep red, a free control in the red direction, fixed by citing the run wg-g4c-2026-08-21. Filed task 100 for the AST dead-private-method census, which names _approach at 9fc044a and finds 2 unreferenced methods today, ArenaBot._turn_corner and Bot._num, neither of which is this defect. Also deduplicated the FINDINGS range row that merge 8fef835 doubled in AGENTS.md and README.md. Branch task-91-dead-approach-finding.'
---

Task 76 measured it: git log -S self._approach finds no commit in which the call site ever appears, and a spy on the method counts 0 calls across a full probe session while a spy on _walk_toward counts 390 (positive control for the spy itself). The method was deleted in task 76's branch and its measured history folded into _walk_toward's docstring, so the CODE is repaired - what is missing is the numbered finding. It is filed rather than taken because ten tasks were in flight on 2026-08-23 and several allocate finding numbers; the work skill says hand a number to the orchestrator rather than collide. THE SHAPE, which is why it is worth a number: eval/findings/certifies-nothing.md says 'a fix that changes nothing at all is evidence about where the code is' and reached the right conclusion from the wrong cause - it read byte-identical evidence as proof that _combat shadowed _approach, when _approach could not have run either way. A second copy of a loop and an unreachable copy of a loop are indistinguishable from the outside by exactly the observation that was made.

## Done 2026-08-23 as FINDINGS #133. What the next agent must not re-derive

**The number is #133, not #132.** Main moved between reading the queue and writing the
finding: #132 was merged by another agent inside the same session. The worktree was
forked before that merge, so the fix was to merge main into the task branch FIRST and
re-read the highest number from the merged tree. Doing that also avoids a textual
conflict, because both findings append to the end of `certifies-nothing.md`.

**Everything the ticket asserted was re-measured, and one phrasing in it is wrong.**
`git log --all -S"self._approach"` does NOT return nothing any more - it returns two
commits, `58dc6cd` and the merge that carried it, both of which added task 76's own
DOCSTRING quoting that command. The check refuted itself by being written down. State it
as the census instead: six commits have touched `eval/judge/bot_platformer.py`,
`_approach` is defined in five of them (`a3d0fd1`, `9fc044a`, `307c957`, `a0d6a01`,
`d2b683f`), and no tree at any of them contains `self._approach(` - only the `def` line
and two comments naming it. That statement is stable. `bot_platformer.py`'s docstring has
been corrected to say it that way.

**The spy, re-run rather than quoted.** Wrapping the method on the class and driving a
full `ref_platformer` session: `d2b683f` (immediately pre-task-76) 20 of 20 criteria pass
with `_approach` at **0 calls** against `_nearest` 391, `_edge_distance` 72, `_combat` 1,
`_hurt` 1. Today, `_approach` absent, `_walk_toward` 390, `_edge_distance` 171. Pinned the
other way too: calling `_approach` directly after the session takes its counter 0 -> 1, so
the zero is the code's and not the wrapper's.

**A SECOND null was resting on it, and it is the bigger one.** #82's section says *"the
re-grade with gap-crossing alone left ts__t0 byte-identical at 0.793"* and uses that to
falsify the pit hypothesis. At `9fc044a` - the commit that published #82 - the whole
gap-crossing mechanism was unreachable: `_edge_distance`'s only call site is line 734
inside `_approach`, `_EDGE_JUMP_WITHIN` is read only at line 735 inside `_approach`, and
the spy measures `_edge_distance` at **0 calls** across a full session. Byte-identical was
the only obtainable result. #82's headline is NOT retracted - the `_nearest` height fix is
live at 391 and 1796 calls and is what moved ts__t0 - but the falsifying sentence is not
evidence. Both sites in `certifies-nothing.md` are now marked with a block citing #133.

**Watch for on the sweep:** adding the finding took the bare-trial-id ratchet from 18 to
19 and `docstat.py --sweep` went red - a free control in the red direction. Cite a trial
id inside `eval/findings/` with its run in the same block: `g4_platformer__unity__t0`
(`wg-g4c-2026-08-21`).

**Found on the way, filed as task 100:** a fifty-line AST census of private methods
defined in a class minus every reference in the tree names `PlatformerBot._approach` at
`9fc044a` - it would have fired before the re-grade was interpreted. Over `eval/judge/` it
sees 121 private methods, 3 unreferenced at `9fc044a` and **2 today**: `ArenaBot._turn_corner`
and `Bot._num`. Neither is this defect and neither should be presented as one -
`_turn_corner` is a cluster of three implementing a design `_chase`'s own docstring records
as measured and discarded, and its docstring is the only record of that measurement. The
design question the gate needs, which #133 does not answer, is what happens to those two.

**Also repaired here, off-ticket and worth one line:** the merge at `8fef835` left the
`eval/FINDINGS.md` range row DUPLICATED in both `AGENTS.md` and `README.md`.
`docstat.py`'s range check reads every matching line and requires each to equal the
highest, so two identical correct rows pass it. Deduplicated.
