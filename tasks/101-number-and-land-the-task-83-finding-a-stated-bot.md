---
id: 101
title: 'Number and land the task 83 finding: a stated bot ceiling was really a ceiling on the length of a key press'
status: open
priority: 3
refs: DECISIONS.md 'A harder task is PRICED here', eval/judge/RUBRIC.md g4 stage.completes, eval/G4-PLATFORMER.md, eval/judge/bot_platformer.py _stage, task 83
done_when: 'The finding has a number taken from the highest in eval/FINDINGS.md on main at the time, a row in the index table, a body in the eval/findings/ file whose shape it matches, and docstat.py --sweep exits 0. State the claim as something someone could disagree with: not ''the bot could not jump far enough'' but that a measured ceiling was attributed to the subject when it belonged to the instrument, and that the reference control shared the defect. The numbers above are measured and must not be re-derived; the raw per-submission fractions are in the task 83 ticket.'
---

Task 83 measured it and no finding number was taken, because ten tasks were in flight and several allocate numbers - the collision mode the work skill warns about. The claim: the play-bot's traversal ceiling was declared and documented as a LEVEL property (pits the bot cannot cross) when it was a property of the INPUT the bot sent - _walk_toward presses jump for one tick and the character is airborne on the next, so the guard never re-fires, and all 8 wg-g4c submissions implement a variable-height jump. Measured over the eight: a one-tick press reaches 29.0 to 88.4 units, holding the control while still rising reaches 93.5 to 141.8, and the widest gap in any of the eight levels is 110. No level was ever uncrossable and every one of them stopped the bot. The second half is the control failure: stage.completes passes on ref_platformer under the broken bot AND the repaired one, so the reference could never have detected this - eval/G4-PLATFORMER.md predicted that in writing when the criterion was designed. Shape is #37 with a key press instead of a code path, and the file to match is certifies-nothing.

## Updated at merge, 2026-08-23 — the number is already allocated, do not take another

**The finding is published as #139**, in `eval/findings/certifies-nothing.md`, with its index row
in `eval/FINDINGS.md`. The orchestrator allocated it when task 83's branch was merged, because
three collisions on one number happened in a single afternoon and the merging tree is the only
one that holds every peer's claim.

**So the numbering half of `done_when` is met and what remains is the citing.** Task 83 edited
`DECISIONS.md`, `eval/judge/RUBRIC.md` and `eval/G4-PLATFORMER.md` while the finding had no
number, so those files carry the measurements with **no citation to point at**. Add `(#139)` where
each states one, and check the claim beside it still matches the finding body — several of task
83's numbers were re-measured during the work.

**File conflict, live:** task 102 is being dispatched in parallel and also edits `DECISIONS.md`
and `eval/judge/RUBRIC.md`. If it is still in flight, do `eval/G4-PLATFORMER.md` first and expect
to merge `main` before finishing.

**What not to conclude:** #139 does not say the play-bot should be repaired in the scored path.
`_walk_toward` is deliberately untouched — a one-tick jump press moves scored criteria, which is a
regime question and not this ticket's.

## Updated at dispatch, 2026-08-23 (second time) — the blocker cleared, and the numbers moved

**The file conflict with `tasks/102` is GONE.** It merged at `c34b014`. `DECISIONS.md` and
`eval/judge/RUBRIC.md` are free, and 102 already repaired the stale `#126`/`#133`/`#137` citations
in both — so **do not re-fix those**; check with `python3 eval/tools/docstat.py --renumbered`
before touching any citation, and read `eval/renumber_triage.json`, which now records a verdict
per row keyed by the citing text.

**The finding is #139 and it is published.** Do not allocate a number. What remains is citing it
in `DECISIONS.md`, `eval/judge/RUBRIC.md` and `eval/G4-PLATFORMER.md`.

**The log has moved to #19-#145** since this ticket was written — #141 through #145 landed today.
Any range or count you touch must come from `python3 eval/tools/docstat.py --findings`, not from
this ticket and not from memory.

**#144, landed today, is directly about the mistake this task could make.** A count with a
producer still goes stale, because citing a producer is not running it — and the instruction-count
figure it is about drifted twice inside one session. If you write any quantity, run its producer
in the session you write it.

**#139 does not say the play-bot should be repaired in the scored path.** It says the proposed
`stage.completes` fraction was measuring the bot rather than the field. Landing the citation is
not landing a repair, and proposing one is out of scope for this ticket.
