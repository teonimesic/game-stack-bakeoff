---
id: 76
title: The play-bot cannot cross a gap, which costs six g4 criteria their measurability on a correct level
status: done
priority: 3
refs: 'eval/judge/bot_mutants.py PIT_UNDER_LEDGE tolerates, eval/judge/bot_platformer.py, eval/judge/RUBRIC.md g4 section, FINDINGS #82 #126'
done_when: 'the PIT_UNDER_LEDGE variant in bot_mutants.py passes with its tolerates tuple EMPTY - attack.damages, score.on_kill, enemy.damages_player, invuln.window, knockback.applied and gameover.triggers each measured on a level whose opening ledge overlooks a pit - and bot_mutants.py green in both halves. Removing a tolerance without the bot crossing the gap is the failure this task exists to prevent, so the variant must be run, not reasoned about. OR, if some of the six cannot be reached even by a bot that crosses the gap: report which ones and the measured reason each stays unreachable, shrink the tolerates tuple to exactly those, and record the residue in RUBRIC.md - a smaller declared ceiling with its measurement is a result and closes this. Promoting stage.completes is NOT part of either branch: it is single-valued False on all 8 wg-g4c submissions and promoting it would separate nothing (#126), so it needs its own three awkward reference levels afterwards.'
established_by: 'PIT_UNDER_LEDGE now passes with tolerates=() and all six combat criteria measured, and it was TWO defects. (1) _hurt was the third inline copy of walk-toward-the-target and the only one with no edge jump, so it walked into the pit, fell out of the world, respawned and repeated - which is why the reach pair passed and the contact four failed on the same level; all callers now go through one _walk_toward. (2) The variant''s own geometry was uncrossable: ground started at x=800 against a start ledge ending at x=120, a 680-unit chasm versus a jump that clears about 148 (JUMP_SPEED 520, GRAVITY -1500, WALK_SPEED 180, ledge 80 up), and an exhaustive sweep over the jump tick never landed below the start ledge at all - so four of the six tolerances were a level-design error in the check. The pit is now 100 units, ground removed for x in 120..220, the size the real submissions shipped (unity__t0 78.5; ts__t0 at 520-600, 1080-1180, 1700-1790), still bottomless: walking off lands in it, jumping at _EDGE_JUMP_WITHIN lands at x=248.1 against a far lip at x=208. PINNED BOTH WAYS by monkeypatching the repaired bot and re-running the variant: as repaired GREEN on all 19 scored criteria; _hurt reverted to its pre-repair body RED on exactly the four contact criteria, reproducing the pre-fix state; _edge_distance blinded RED on all six; the edge jump removed from _walk_toward RED on all six. Full suite exit 0: 36 criteria pinned both ways, 4 variants, 3 session-lock controls, 0 unmet. Evidence on the pit level is measurement not tolerance - 4 player_hit, hp 4.0 to 0.0, smallest inter-hit gap 48 ticks equal to INVULN_TICKS, knockback vx 180.0 to -240.0 equal to KNOCKBACK_X. wg-g4c needs no re-grade: its eight stored playbot.json files already pass all six on all eight submissions, the only exception being unity__t0 knockback.applied, unscored for the separate reason in #89. FOUND ON THE WAY AND FILED AS TASK 91: _approach never had a caller - git log -S self._approach finds no commit and a spy counts 0 calls against 390 for _walk_toward - so it was deleted and its measured history folded into _walk_toward; certifies-nothing.md had attributed its null result to _combat shadowing it. stage.completes stays diagnostic-only and still fails on the pit level at x=242.5 of a goal at 2300, because _stage is a fourth walk-right loop with no target; promoting it needs its own three awkward levels (#126). Branch task-76-play-bot-cross-a-gap. Docs updated: RUBRIC.md g4 ceiling block replaced, RUNS.md wg-g4c grading note corrected. docstat.py --sweep clean, tasks.py check green.'
---

bot_platformer reaches every enemy by walking right, so a level with a pit makes six combat criteria unmeasurable and a submission is penalised in proportion to how much real platforming it builds. The ceiling is declared in the PIT_UNDER_LEDGE variant's tolerates tuple, which is the one place in the mutant suite where a failure is allowed not to count - rule 7 says every such channel is one a real bug can widen. The bot has the platforms list in state and can measure its own jump envelope, so this is tractable without level knowledge.

## Measured 2026-08-23, before anyone starts: two of the six tolerances never fire

A clean `judge/bot_mutants.py` run reports, for that variant:

    tolerates ['attack.damages', 'score.on_kill', 'enemy.damages_player', 'invuln.window',
               'knockback.applied', 'gameover.triggers']; fired for ['enemy.damages_player',
               'gameover.triggers', 'invuln.window', 'knockback.applied']

So **4 of the 6 actually go red on the pit level; `attack.damages` and `score.on_kill` pass
already.** Those two can come out of the tuple today, with the run above as the evidence, and
that shrinks the declared ceiling before any bot work happens. It also narrows what the bot has
to achieve: the four that fire are the ones needing the player to reach an enemy and be hurt by
it, which is the contact cluster, not the reach cluster.

Start by re-running the suite and confirming that line still reads the same — a tolerance list
is exactly the kind of thing that drifts, and #46 is what happens when the reference stops
resembling the case a check was written for.
