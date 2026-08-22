---
established_by: unity__t0 0.896 -> 0.966; attack.damages and score.on_kill recovered. The falsifier ruled the submission out first (lowest enemy density in the field: 1 within 600px vs ts__t0's 5, which scores 1.000). Instrumentation then found two more causes where reasoning had found none, and ONE OF THEM WAS INTRODUCED BY THE EARLIER FIX. (6) _combat held attack down on every tick and this submission's swing roots the character: the same walk with attack OFF reaches x=387.4 and crosses the 78.5-unit gap at full health, with attack ON reaches x=360.3 and falls in - so the bot failed attack.damages for a reason unrelated to whether attacks damage. Now swings only within 44 units of the target. (7) the height-aware _nearest from task 15 re-decided the target mid-jump: at apex y=119 it excluded the target at y=37 (dy=82) and retargeted an enemy 1,700 units away, reversing the bot into the gap. Airborne now falls back to nearest-by-x. bot_mutants green: 36 criteria both directions, 4 variants, 3 controls, 0 unmet. REMAINING failure knockback.applied is a CRITERION defect adjudicated to source, not a submission defect: the submission implements knockback correctly, but its first player_hit is a PIT fall, which Sim.cs deliberately handles by respawning with zero velocity ('falling forever is not a punishment, it is an ending'). Filed as task 20.
id: 18
title: The play-bot dies on the way to its target instead of fighting through
status: done
priority: 2
refs: eval/FINDINGS.md #82, eval/judge/bot_platformer.py
done_when: either g4_platformer__unity__t0 (wg-g4c-2026-08-21) passes attack.damages, score.on_kill and knockback.applied, or the behaviour is shown to be a property of that submission rather than of the bot, with the measurement that distinguishes them
---

Tier 2 drives a scripted play-bot through each submission and scores criteria on what happens.

THE OBSERVATION: g4_platformer__unity__t0 scores 0.896, failing attack.damages, score.on_kill and knockback.applied. It is NOT the two causes already fixed - the target is at a reachable height (dy=7, so #82's targeting repair does not apply) and no pit lies between the player and it.

MEASURED by instrumenting a probe session: the player starts at x=61 y=44 with 5 hp and the nearest reachable enemy is at x=521 y=37. Walking right, hp falls 5 -> 4 -> 3 -> 1 -> dead by tick 275, before covering the 460 units. The combat session reports only '329 ticks of walk-and-swing' against 3002 for a healthy submission - it is a short session because the player died in it.

THE LIKELY MECHANISM: _approach walks toward its chosen target and only swings when within stop_at*1.6 of THAT enemy. Everything else it meets on the way is walked into, and on a dense level that is fatal. The bot needs to fight what it collides with, not only what it aimed at.

WHY IT MIGHT INSTEAD BE THE SUBMISSION: a level dense enough to kill a walking character in 275 ticks may simply be hard, and 'the player dies quickly' can be a true fact about the game rather than a bot defect. That is what the second branch of the done-when is for. Distinguish by comparing enemy density and contact damage against the other seven submissions - if unity__t0 is an outlier on those, the bot is fine and the submission is punishing.

Offline: stored submissions only, no new trials.
