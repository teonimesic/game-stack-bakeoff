---
id: 15
title: Let the play-bot cross a gap so combat criteria are measurable on real levels
status: open
priority: 1
refs: eval/FINDINGS.md #65, eval/judge/bot_platformer.py
done_when: the platformer bot reaches an enemy on a level whose ground has pits, demonstrated by the six combat criteria passing on a reference level with a gap; or the limit is promoted to diagnostic_only for gapped levels with the measurement showing why
---

This project measures how well coding agents build whole games in four stacks, graded in three tiers; tier 2 is a scripted play-bot driving thousands of ticks and scoring criteria.

THE DEFECT: the platformer bot reaches every enemy by WALKING RIGHT. It cannot jump a gap. On a level whose ground has pits it walks into the first one and dies, so attack.damages, score.on_kill, enemy.damages_player, invuln.window, knockback.applied and gameover.triggers all fail - six criteria, on a submission that is working correctly.

MEASURED, TWICE: g4_platformer__ts__t0 (wg-g4c-2026-08-21) has four ground segments with pits at x 520-600, 1080-1180 and 1700-1790; its own evidence says the bot reached x=588.8, inside the first pit. It scored the field's LOWEST at 0.793. g4_platformer__unity__t0 is the same mechanism - its Level.cs says 'Six pits to clear' and the bot reached x=367.5 against a 300-wide start pad.

WHY THIS IS THE WORST REMAINING TIER-2 DEFECT: the penalty is indexed to how good the level is. A submission that builds real platforming - gaps that must be jumped - is punished for it, and a flat corridor scores full marks. That is the instrument rewarding the opposite of the thing the task asks for.

CONSTRAINT FROM #65: whatever is built must ESTABLISH its condition, not hope. The bot already knows platform geometry from the state contract, so a gap is locatable rather than something to be discovered by dying in it. The pit variant added to bot_mutants.py declares six tolerated criteria for exactly this reason - if the bot learns to cross a gap, those tolerances must shrink, and that is the check that this actually worked.

Offline: reference fixtures and stored submissions only, no new trials.
