---
id: 101
title: 'Number and land the task 83 finding: a stated bot ceiling was really a ceiling on the length of a key press'
status: done
priority: 3
refs: DECISIONS.md 'A harder task is PRICED here', eval/judge/RUBRIC.md g4 stage.completes, eval/G4-PLATFORMER.md, eval/judge/bot_platformer.py _stage, task 83
done_when: 'The finding has a number taken from the highest in eval/FINDINGS.md on main at the time, a row in the index table, a body in the eval/findings/ file whose shape it matches, and docstat.py --sweep exits 0. State the claim as something someone could disagree with: not ''the bot could not jump far enough'' but that a measured ceiling was attributed to the subject when it belonged to the instrument, and that the reference control shared the defect. The numbers above are measured and must not be re-derived; the raw per-submission fractions are in the task 83 ticket.'
established_by: 'Seven (#139) citations landed on branch task-101-cite-139, each on the sentence stating a measurement: DECISIONS.md x3 (pre-test head, the levels-were-never-the-constraint bullet, the harder-task re-open row), eval/judge/RUBRIC.md x4 (traversal-repair paragraph, length-of-the-key-press, improving-the-instrument-reordered-the-field, crossing-the-SMALLEST-gap), eval/G4-PLATFORMER.md x2 including a new paragraph retracting the traversal ceiling as a level property. Every claim beside a citation re-read against the #139 body and agreeing to the digit, including 14.3-29.0 percent and 27.4-80.3 percent as the percentage form of the 0.143-0.290 and 0.274-0.803 rows. No number allocated: #139 was already published at merge of task 83. Gates unpiped: docstat.py --sweep exit 0, --findings exit 0 at 127 findings #19-#145, --renumbered exit 0 with 0 untriaged, tasks.py check exit 0 at 111 tasks. Rubric canary present; citations only, so no weight or grading change and no re-grade. NEGATIVE CONTROL: a fabricated (#999) planted in a live document reads exit 0 on --sweep, --findings and --renumbered, so the gate this ticket''s done_when names cannot distinguish a landed citation from an invented one; --renumbered is derived from git renumber events and #139 never moved. Census of out-of-range #NN over the 53 live markdown files: 20 rows, 2 true positives (eval/RUNS.md 1140 and 1153 cite #17, below the published range and not task 17), 18 correct non-finding uses, so the obvious widening is 18 false positives to 2 true and is #140''s open-class trap. Extraction pinned both directions before the count was believed: 20 clean, 21 with the plant, 20 after restore. The 2 true positives filed as tasks/112, not fixed here because the intended target is unknown and AGENTS.md forbids renumbering a finding to satisfy a citation.'
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

## Done, 2026-08-23 — where the citations landed, and the hole the done_when leans on

**Seven `(#139)` citations, on branch `task-101-cite-139`.** Each sits on the sentence that
states the measurement, not at the head of the section, so a reader who arrives by grep gets the
number with the claim:

| file | line | what it states |
|---|---|---|
| `DECISIONS.md` | the pre-test paragraph | "published as #139" — the block head |
| `DECISIONS.md` | "The levels were never the constraint" | 93.5-141.8 held vs a widest gap of 110 |
| `DECISIONS.md` | the harder-task re-open row | rho=0.405, p=0.163, 0.274-0.803 |
| `eval/judge/RUBRIC.md` | the traversal-repair paragraph | the free pre-test |
| `eval/judge/RUBRIC.md` | "the length of the key press, not the logic" | 29.0-88.4 vs 93.5-141.8 vs 110 |
| `eval/judge/RUBRIC.md` | "Improving the instrument reordered the field" | rho=0.405, p=0.163 |
| `eval/judge/RUBRIC.md` | "crossing the SMALLEST gap the submission would allow" | the ceiling claim |
| `eval/G4-PLATFORMER.md` | "that paragraph's prediction was tested" | the control half |
| `eval/G4-PLATFORMER.md` | a new paragraph | the ceiling belonged to the INPUT, with the three ranges |

Every claim beside a new citation was re-read against the #139 body and agrees to the digit,
including `eval/G4-PLATFORMER.md`'s percentages: 14.3%-29.0% and 27.4%-80.3% are the same
0.143-0.290 and 0.274-0.803 rows of the finding's table.

**`eval/G4-PLATFORMER.md` gained a paragraph rather than only a citation**, because it was the
document that stated the traversal ceiling as a level property in the first place and had no
sentence retracting it — the criterion's driving description already said *holding the control
while still rising*, so the file described the repaired bot and the old ceiling at once.

**The `done_when` names a gate that cannot see what this task delivers, and that is measured.**
A fabricated `(#999)` planted in a live document reads **exit 0** on `docstat.py --sweep`, on
`--findings` and on `--renumbered` — indistinguishable from the clean tree. `--renumbered` is
derived from git renumber events, so a number that never moved is invisible to it, and #139 is
not in the renumber map. Landing a citation is therefore only as good as the person who read it.

**Do not add the obvious check without measuring it first.** A census of out-of-range `#NN` over
the 53 live markdown files returns **20 rows, of which 2 are true positives** — the other 18 are
rule numbers, task ids, table-row references, GitHub issue numbers and "the #1 risk". That is
#140's open-class trap exactly. Extraction pinned both directions before the count was believed:
20 clean, 21 with a planted `#999`, 20 again after restore.

**The 2 true positives are filed as `tasks/112`:** `eval/RUNS.md` lines 1140 and 1153 cite `#17`,
which is below the published range #19-#145 and is not task 17 either. Not fixed here — the
target is unknown and AGENTS.md forbids renumbering a finding to satisfy a citation.
