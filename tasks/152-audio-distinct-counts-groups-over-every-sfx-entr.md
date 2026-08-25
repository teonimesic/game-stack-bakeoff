---
id: 152
title: audio.distinct counts groups over every sfx entry but floors on declared events, so undeclared extras buy a pass
status: in_review
priority: 1
refs: eval/judge/audio.py collect() distinct block and GAME_EVENTS, eval/judge/audio_selftest.py, eval/judge/RUBRIC.md audio section, tasks/151, PR 27
done_when: 'audio.distinct''s numerator and denominator range over the same set. Either group only the sfx entries naming a declared event, or fail audio.manifest on undeclared entries - decide which, and say why in the ticket, because the two differ for a submission that declares extra events legitimately. audio_selftest.py gains BOTH halves: a mutant that makes audio.distinct go red on all-events-share-one-clip, and the VARIANT that is the actual defect here - all-share-one-clip PLUS unique extras, which must also be red and is the case a mutant cannot construct (AGENTS.md rule 15). Establish the broken state first by running the selftest with the variant added and showing it green before the fix. Then re-score every stored submission that has an audio grading and report how many audio.distinct verdicts move; if any moves, eval/RUNS.md gets a grader-side regime boundary entry naming them, in the shape of the fifth boundary. If none moves, say so with the count and the population, and no boundary is needed. Note g4_platformer is separately broken by tasks/151 - GAME_EVENTS has no g4 key, so n_events falls back to len(sfx_clips) there and this fix must not assume expected is non-empty.'
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/30
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

## note 2026-08-25

## note 2026-08-25 (orchestrator) — DO BOTH. You are authorised to fix 151 in this branch.

142 has merged, so `RUBRIC.md`'s audio section is free and both audio tickets are unblocked.

**Take `tasks/151` as well, in this branch, and close both in one pull request.** They are one
change to one file: `GAME_EVENTS` has 3 keys for 4 games (151), and your fix here must not assume
`expected` is non-empty — which is that same hole. Splitting them across two branches means the
second agent re-reads everything the first learned and the two edits collide in `audio.py`,
`audio_selftest.py` and `RUBRIC.md`.

Read `tasks/151` in full before starting; its note carries my independent confirmation.

## Both defects reproduced by the orchestrator, so you start from measurements

| | |
|---|---|
| `GAME_EVENTS` keys | `g1_pong`, `g2_tetris3d`, `g3_arena` — **`g4_platformer` absent** |
| `g1_pong` | 5 declared events, `floor = max(2, ceil(5/2)) = 3` |
| `g2_tetris3d`, `g3_arena` | 6 declared events, floor 3 |

So on Pong, 5 events on one clip = 1 group = **fail**; plus 2 unique junk entries = 3 groups =
**pass**. The same two-entry purchase works on tetris and arena.

## The part most likely to be skipped

**The variant is the test, and a mutant cannot construct it.** The failing input is
*all-share-one-clip **plus** unique extras*. Establish the broken state first: add the variant,
show `audio_selftest.py` **green** with it in the tree, and only then fix. A variant added after
the fix tests the fix, not the claim (#60).

## The re-scoring clause is the expensive half and it is the point

Both fixes can move **stored** tier-1 verdicts — 151 makes a criterion that could never fail able
to fail. Re-score every stored submission with an audio grading and report how many verdicts move,
**with the population**. If any moves, `eval/RUNS.md` gets a grader-side boundary entry in the
shape of the twenty-first, which task 142 just wrote and is the model to copy. If none moves, say
so with the count — a null needs its number as much as a hit does.

**Do not re-grade beyond that census.** `eval/judge/AGENTS.md` governs; the census answers "did
this change verdicts", it is not a re-grading pass.
