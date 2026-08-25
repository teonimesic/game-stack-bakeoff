---
id: 152
title: audio.distinct counts groups over every sfx entry but floors on declared events, so undeclared extras buy a pass
status: todo
priority: 1
refs: eval/judge/audio.py collect() distinct block and GAME_EVENTS, eval/judge/audio_selftest.py, eval/judge/RUBRIC.md audio section, tasks/151, PR 27
done_when: 'audio.distinct''s numerator and denominator range over the same set. Either group only the sfx entries naming a declared event, or fail audio.manifest on undeclared entries - decide which, and say why in the ticket, because the two differ for a submission that declares extra events legitimately. audio_selftest.py gains BOTH halves: a mutant that makes audio.distinct go red on all-events-share-one-clip, and the VARIANT that is the actual defect here - all-share-one-clip PLUS unique extras, which must also be red and is the case a mutant cannot construct (AGENTS.md rule 15). Establish the broken state first by running the selftest with the variant added and showing it green before the fix. Then re-score every stored submission that has an audio grading and report how many audio.distinct verdicts move; if any moves, eval/RUNS.md gets a grader-side regime boundary entry naming them, in the shape of the fifth boundary. If none moves, say so with the count and the population, and no boundary is needed. Note g4_platformer is separately broken by tasks/151 - GAME_EVENTS has no g4 key, so n_events falls back to len(sfx_clips) there and this fix must not assume expected is non-empty.'
---

In eval/judge/audio.py collect(), sfx_clips is every manifest sfx entry that decoded, groups = distinct_groups(sfx_clips), and floor = max(2, ceil(n_events/2)) where n_events = len(expected) - the events the GAME DECLARES. The numerator ranges over the manifest; the denominator comes from the task. Undeclared extras are recorded in info[extra_events] and never enter shape_problems, so audio.manifest does not fail them either. Reproduced against the real arithmetic for g1_pong, which declares 5 events and so floors at 3: all 5 declared events mapped to ONE clip plus 2 unique extra sfx entries gives 3 groups and PASSES; the identical submission without the extras gives 1 group and FAILS. Two junk entries convert a fail into a pass. That is precisely the failure audio.py's own docstring says the criterion exists to catch - one beep copied under many names - and it is fail-open, which AGENTS.md rule 7 ranks as the expensive direction because it costs the result rather than a trial. Found by CodeRabbit on PR 27. NOT fixed there: task 142 was scoped to the prompt wording, and changing what audio.distinct scores is a grader-side change that can move stored tier-1 gate outcomes. RUBRIC.md now states the loophole and cites this ticket rather than describing behaviour the code does not have.

## note 2026-08-25

## note 2026-08-25 (orchestrator) — arithmetic reproduced, and the ordering constraint

Re-derived from the live table rather than from the ticket: `g1_pong` declares **5** events, so
`floor = max(2, ceil(5/2)) = 3`. Five declared events on one clip gives 1 group and **fails**; the
same submission plus 2 unique junk sfx entries gives 3 groups and **passes**. Two junk entries
convert a fail into a pass, exactly as filed. `g2_tetris3d` and `g3_arena` both declare 6 and floor
at 3, so the same two-entry purchase works there.

**Do not run this concurrently with 151.** Both edit `audio.py` and `audio_selftest.py`, and this
ticket's fix must not assume `expected` is non-empty — which is 151's defect. One branch for both
is a reasonable answer.

**Also blocked behind 142** while it is in flight, on `RUBRIC.md`'s audio section.

## The variant is the whole test, and a mutant cannot construct it

The `done_when` already says this and it is worth repeating because it is the part that gets
skipped: the failing input is *all-share-one-clip **plus** unique extras*. A mutant removes the
mechanism; it cannot manufacture that input. Establish the broken state first — add the variant,
show `audio_selftest.py` **green** with it, and only then fix. A variant added after a fix tests
the fix, not the claim (#60).
