---
id: 76
title: The play-bot cannot cross a gap, which costs six g4 criteria their measurability on a correct level
status: in_flight
priority: 3
refs: 'eval/judge/bot_mutants.py PIT_UNDER_LEDGE tolerates, eval/judge/bot_platformer.py, eval/judge/RUBRIC.md g4 section, FINDINGS #82 #126'
done_when: 'the PIT_UNDER_LEDGE variant in bot_mutants.py passes with its tolerates tuple EMPTY - attack.damages, score.on_kill, enemy.damages_player, invuln.window, knockback.applied and gameover.triggers each measured on a level whose opening ledge overlooks a pit - and bot_mutants.py green in both halves. Removing a tolerance without the bot crossing the gap is the failure this task exists to prevent, so the variant must be run, not reasoned about. OR, if some of the six cannot be reached even by a bot that crosses the gap: report which ones and the measured reason each stays unreachable, shrink the tolerates tuple to exactly those, and record the residue in RUBRIC.md - a smaller declared ceiling with its measurement is a result and closes this. Promoting stage.completes is NOT part of either branch: it is single-valued False on all 8 wg-g4c submissions and promoting it would separate nothing (#126), so it needs its own three awkward reference levels afterwards.'
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
