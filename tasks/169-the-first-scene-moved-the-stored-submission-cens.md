---
id: 169
title: the first scene moved the stored-submission census from 68 to 69 and four live documents still say 68
status: todo
priority: 3
refs: README.md,DECISIONS.md,eval/AGENTS.md,eval/judge/RUBRIC.md,eval/judge/tier1_census.py,eval/judge/tier2_census.py,tasks/163
done_when: every live document stating a tier-1 or tier-2 census figure either matches its producer's output today, or says in the same block which population and date it is reporting - and the distinction between the two is deliberate rather than whichever the author happened to leave. Both producers re-run unpiped with --runs-root <main>/eval/runs and their output pasted into the ticket.
---

wg-scene-s1ts-2026-08-25 added the 69th stored submission, and every census figure derived from the corpus moved by one. python3 eval/judge/tier1_census.py --runs-root <main>/eval/runs today prints 69 stored submissions, 85 gradings, 16 superseded, 8 failing trials, 11 groups, 0 both-vary, FLOOR-ONLY, and 0 reversed / 3 coarsened / 8 identical. tasks/163 repaired the two figures in eval/judge/RUBRIC.md that are explicitly headed 'what it reports today' plus its 5-of-5 corroboration row, because they sat directly above the section it was rewriting and leaving a knowingly-false 'today' figure is worse than a stale one elsewhere. It did NOT chase the rest, because most of them are decision-time evidence and repairing them blind would erase the population a decision was made on. Known restatements, read 2026-08-26: README.md:222 ('68 stored submissions ... 7 of 10 groups'); DECISIONS.md:160 (the tier-1 gate evidence bullet), :174 ('14 of 68 would move'), :203/:206/:228 (tier-2 census, 35 of 68), :982/:988 (the Open section's rubric-ceiling paragraph, 61 of 68 and 35 of 68), :1233, :2947 ('62 of 68'); eval/AGENTS.md:30 ('68 submissions before and after, over 84 gradings'); eval/RUNS.md:390; eval/judge/RUBRIC.md:144/:213/:215. Note that 84 is also now 85. The rule this is under is AGENTS.md's: a count with a producer goes stale for an hour, a count with none goes stale forever - these all have producers, so the work is deciding per figure whether it is a live count or a dated one, and saying which.

## note 2026-08-27

## note 2026-08-27 (orchestrator) — the numbers you must reconcile MOVED today; re-run before reading anything

This ticket was filed when the census was 68 games + 1 scene. Three tickets have merged since and
two of them change what the producers say. **Do not start from any figure in this ticket body or in
any document — run both producers first and work from that.**

What landed:

- **`tasks/163`** made `render.nonempty`'s bound per task class, and added
  `static.TIER1_BOUND_POPULATION`, a closed map from every tier-1 criterion to the population its
  bound was calibrated on.
- **`tasks/168`** then removed the ink CEILING for every class, because `mean_ink` is departure
  from frame 0's modal colour and so cannot bound 'was anything drawn' at all (#191).
  **`wg-g4c g4_platformer__godot__t1` re-grades from `gate: FAIL 1/14` to `PASS 14/14`.** Any
  document stating the tier-1 failure count, or the '7 failures in 68 trials' breakdown, or the
  five non-blocking failures, is now stating a figure from a retired rule.
- **`tasks/164`** moved `layers.image_parallax` on the stored scene to `scored=False`, taking that
  trial's tier 2 from `6 of 7 = 0.857` to `6 of 6 = 1.000`.

**So this ticket is larger than 'four documents say 68'** — the population count moved by one and
several of the VERDICTS inside it moved too. Its `done_when` already asks the right question, and
it is the important half: for each figure, is it a live count that must match its producer today, or
a historical reading that must name its population and date? **Decide that per figure and say so,
rather than making them all current or all dated.**

**`eval/runs/` is read-only for you.** Re-grade offline and record; store nothing there.

One thing worth knowing before you quote a per-class figure: `ink_window_control.py` reports that
`task_class` is **read** from the record on 1 of 69 stored submissions and **inferred** by
`_class_of` from the id shape on the other 68. The classes are almost entirely inferred. That is
not wrong - the id shape is a real second channel - but a sentence about 'the game corpus' rests on
`_class_of`, and should say so rather than implying the classes were read.
