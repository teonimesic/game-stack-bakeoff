---
id: 151
title: audio.GAME_EVENTS has no g4_platformer key, so the platformer's audio manifest criterion cannot fail
status: in_review
priority: 1
refs: eval/judge/audio.py GAME_EVENTS and collect(), eval/suites/wholegame_prompts.py _G4_EVENTS, eval/judge/audio_selftest.py, eval/judge/RUBRIC.md audio table, tasks/142
done_when: 'GAME_EVENTS carries a g4_platformer entry whose event names are byte-equal to the names in _G4_EVENTS - assert that equality in code across every game rather than transcribing it, since a transcription is a second address for one fact (AGENTS.md rule 12). audio_selftest.py gains a mutant that makes audio.manifest go red on a g4 submission missing a declared cue, and it must be shown red before the fix and green after. Establish the broken state first: score a stored g4_platformer submission with a deliberately gutted manifest and record that audio.manifest passes today. Then say in eval/RUNS.md whether re-scoring the 20 stored g4_platformer trials under a working criterion is a grader-side regime boundary, and if any stored score moves, record which. If the answer is that g4 was deliberately excluded from audio grading, say so with the decision that excluded it and close as a negative result.'
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/30
---

GAME_EVENTS in eval/judge/audio.py has three keys - g1_pong, g2_tetris3d, g3_arena. The platformer is absent, and its prompt declares eight events verbatim in _G4_EVENTS: jump, land, attack, enemy_hit, enemy_dead, player_hit, stage_clear, game_over. Audio grading is on by default (evaluate.py audio: bool = True), so for g4 collect() takes GAME_EVENTS.get(game, ()) -> (), and three things go wrong at once. missing_events is empty, so audio.manifest passes for any submission shipping a music object and an sfx object even with zero of the eight declared cues - a tier-1 gate criterion that CANNOT FAIL on this game. extra_events lists every real cue as extra. And n_events = len(expected) or len(sfx_clips) silently falls back to the submission's own clip count, so audio.distinct's floor is set by what the agent shipped rather than by what the task asked for. Only audio.triggered still bites, because it reads the events the probe actually fired. This is the shape AGENTS.md calls a mechanism that runs, reports success and measures nothing, and it is fail-open. Found while reading audio.py for task 142; not fixed there because task 142 was scoped to the prompt wording and this is a grader change that moves stored scores.

## note 2026-08-25

## note 2026-08-25 (orchestrator) — confirmed independently, and 151/152 must not run concurrently

`GAME_EVENTS` holds **3 keys for 4 games**: `g1_pong`, `g2_tetris3d`, `g3_arena`. `g4_platformer`
is absent, so `n_events` falls back to `len(sfx_clips)` there — numerator and denominator drawn
from the same set, which is a criterion that cannot fail. That is rule 1's shape in a scored
criterion, and it is fail-open (rule 7), which is the direction that costs the result rather than
a trial.

**Do not dispatch 151 and 152 to different agents.** Both edit `eval/judge/audio.py` and
`audio_selftest.py`, and 152's `done_when` explicitly says its fix must not assume `expected` is
non-empty — which is *this* ticket's defect. Whoever takes one should read the other first and may
reasonably do both in one branch, saying so in the pull request.

**Also blocked behind task 142** while it is in flight: 142 touches `RUBRIC.md`'s audio section,
and both of these do too.

**The re-scoring clause is the expensive half, and it is the point.** Adding a `g4_platformer` key
makes a criterion that could never fail able to fail, so stored platformer gradings may move.
Report the count and the population either way; a null needs the number just as much.
