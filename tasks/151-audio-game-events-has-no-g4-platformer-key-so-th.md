---
id: 151
title: audio.GAME_EVENTS has no g4_platformer key, so the platformer's audio manifest criterion cannot fail
status: done
priority: 1
refs: eval/judge/audio.py GAME_EVENTS and collect(), eval/suites/wholegame_prompts.py _G4_EVENTS, eval/judge/audio_selftest.py, eval/judge/RUBRIC.md audio table, tasks/142
done_when: 'GAME_EVENTS carries a g4_platformer entry whose event names are byte-equal to the names in _G4_EVENTS - assert that equality in code across every game rather than transcribing it, since a transcription is a second address for one fact (AGENTS.md rule 12). audio_selftest.py gains a mutant that makes audio.manifest go red on a g4 submission missing a declared cue, and it must be shown red before the fix and green after. Establish the broken state first: score a stored g4_platformer submission with a deliberately gutted manifest and record that audio.manifest passes today. Then say in eval/RUNS.md whether re-scoring the 20 stored g4_platformer trials under a working criterion is a grader-side regime boundary, and if any stored score moves, record which. If the answer is that g4 was deliberately excluded from audio grading, say so with the decision that excluded it and close as a negative result.'
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/30
established_by: 'Closed with 152 in PR #30. Verified on merged main: GAME_EVENTS now holds 4 keys including g4_platformer, so the criterion that could never fail can. The ticket''s ''20 stored g4_platformer trials'' was wrong and the producer wins - 24 gradings over 8 submissions, 16 of them wg-g4c-capgate re-grades.'
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

## note 2026-08-25

## note 2026-08-25 (agent) — closed inside PR 30 with 152

**`GAME_EVENTS` is no longer transcribed.** `eval/suites/wholegame_prompts.py` gains
`EVENTS`, parsed from the fenced `_G*_EVENTS` blocks the prompts render, and
`eval/judge/audio.py` reads it from there — the same lazy-import shape `aspects.py` already
uses to learn task ids. The parse fails loudly on a missing fence, a non-declaration line
inside the fence, an empty parse or a duplicate, and `EVENTS` refuses to load if it and
`TASKS` disagree about which games exist.

**The drift was on 2 of the 4 games, not 1.** `g4_platformer` was absent, as filed — and
`g3_arena`'s prompt declares **9** events while the transcription held **6**. `enemy_spawn`,
`wall_graze` and `multiplier` were never asked for, and were recorded as `extra_events`
whenever a submission shipped them: `30 of 59` stored audio gradings.

**`collect()` now refuses a game the suites declare no events for** — every criterion fails
with that as the reason, rather than passing over an empty contract.

### The pin, and why the copy in the selftest is deliberate

`audio_selftest.py` carries `EVENTS_AS_WRITTEN`, transcribed by hand, and
`pin_declared_events` compares it with `audio.GAME_EVENTS` **and** with all 16 rendered game
prompts. That is the row task 113 asks for: the expectation must be a second, independent
statement, never the same object as the subject. **Every fixture in that file is built from
the transcription, never from `audio.GAME_EVENTS`** — a fixture that asks the grader which
cues to ship omits exactly the cues the grader has forgotten to look for, and
`audio.manifest` goes green on both halves of one mistake.

Broken state established first: with the pins added and the grader untouched, the selftest
read **88 expectations, 11 unmet, exit 1**. After the fix, **97 / 0 / exit 0**.

### Re-scoring: a null, and it is not a boundary for stored scores

`python3 eval/judge/audio_regrade_census.py --runs-root <main checkout>/eval/runs` —
**0 of 59 gradings move, 43 distinct submissions, 0 refused.** For g4 the producer counts
**24 gradings over 8 submissions**, not the 20 this ticket estimated; 16 of the 24 are the
`wg-g4c-capgate` re-grades.

**Why g4 does not move**, which is worth not re-deriving: all 24 gradings shipped exactly
the 8 declared cues, so `missing_events` was empty either way — and the old
`len(expected) or len(sfx_clips)` fallback happened to give floor 4 over 8 clips, which is
what the declared list gives too. The criterion could not fail; the corpus never asked it to.

`eval/RUNS.md` records this as a **twenty-second** comparability break, grader-side, stating
that no stored score, gate outcome or `overall` changes.
