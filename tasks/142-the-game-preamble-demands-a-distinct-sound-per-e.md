---
id: 142
title: The game preamble demands a distinct sound per event and the audio section allows two events to share one
status: in_review
priority: 2
refs: eval/suites/wholegame_prompts.py _preamble and _probe_section, eval/suites/rendered/g1_pong__unity.txt, eval/judge/RUBRIC.md audio criteria, eval/RUNS.md, PR 19
done_when: One of the two clauses is gone or reworded so no rendered game prompt states both, decided against what judge/ actually scores. eval/RUNS.md records the comparability break with the date, since every future game trial is then cross-regime with the 90 stored ones. prompt_guard.py exits 0, prompt_guard_control.py exits 0, and the snapshot at eval/suites/rendered is re-recorded in the same commit. If the answer is that the two clauses are NOT in conflict, say why in the ticket with the criterion that adjudicates it, and close as a negative result.
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/27
---

Every rendered game prompt states both. The definition of done in _preamble(): 'a distinct sound effect for each of the events listed below'. The audio-manifest section of _probe_section(), 40 lines later: 'Whether two events share a sound, and what the sounds are, is yours to design.' A submission that maps three events to one file satisfies the manifest contract and fails the stated definition of done, and the audio criteria in judge/ decide which of the two the grader believes. Found by CodeRabbit on PR 19 against eval/suites/rendered/g1_pong__unity.txt lines 27-28 and 115-118, which only became reviewable because task 133 checked the rendered prompts in. NOT fixed there: _preamble() and _probe_section() are shared by all four games, 90 stored whole-game trials ran under this wording, and editing either is a regime boundary that task 133 was not scoped for.

## note 2026-08-25

## note 2026-08-25 — the blast radius is smaller than when this was filed, and it is measured

This ticket was written before task 133 landed, when `_preamble()` was shared by everything. It is
not any more: scenes have their own `_scene_preamble()` in `eval/suites/scene_prompts.py`, and the
isolation was verified in both directions at merge by perturbing each preamble in turn —

| edit | moves |
|---|---|
| the **game** preamble | **16 of 16** game prompts, **0 of 8** scene prompts |
| the **scene** preamble | 8 of 8 scene prompts, 0 of 16 game prompts |

So this edit reaches 16 rendered prompts and no scene. It is still a regime boundary against the
**90 stored game trials** and still needs its `eval/RUNS.md` entry — but it does not put scenes on
the far side of one, and the scene suite has no stored trials to be cross-regime with anyway.

## Let `judge/` adjudicate, not taste

The `done_when` says decide *"against what judge/ actually scores"*, and that is the whole ticket.
Read `eval/judge/audio.py` and the audio criteria in `RUBRIC.md` **first**, and let the wording
follow the criterion. Do not pick the clause that reads better.

**Both outcomes close this**, including *"they are not in conflict, and here is the criterion that
adjudicates it"*. A negative result here is worth as much as an edit and costs a regime boundary
less.

## What NOT to do

Do not edit `_preamble()` and re-snapshot in separate commits — `eval/suites/rendered/` is diffed
by CI, and a snapshot that lags its source is a red gate on the next unrelated pull request.

Do not treat the 90 stored trials as re-gradeable afterwards. If the wording changes, trials before
and after are **different populations**, and the `RUNS.md` entry is what stops someone pooling them
a month from now.
