---
id: 76
title: The play-bot cannot cross a gap, which costs six g4 criteria their measurability on a correct level
status: open
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

## Done 2026-08-23. What the next agent must not re-derive

The pre-run line above was confirmed unchanged before anything was touched: 4 of 6 fired, and
they were the contact cluster. The cause was **two defects, and the second one is in the check,
not the bot.**

**1. `_hurt` was the third inline copy of "walk toward the target", and the only one with no
edge jump.** `bot_platformer.py` held three: `_approach`, `_combat`, `_hurt`. The gap-crossing
repair that closed task 15 reached `_combat`. `_hurt` — whose whole experiment is making contact
with an enemy — walked into the pit, fell out of the world, respawned on the start ledge and
repeated for the session. That is exactly why the *reach* pair passed and the *contact* four
failed on the same level: two loops, two behaviours. All callers now build their inputs through
one `_walk_toward`.

**2. The variant's own geometry made the level uncrossable, so no bot could ever have passed
it.** `PIT_UNDER_LEDGE` put the ground's start at x=800 while the start ledge ends at x=120 — a
680-unit chasm. The fixture's jump clears about 148 units (JUMP_SPEED 520, GRAVITY -1500,
WALK_SPEED 180, ledge 80 above the floor). An exhaustive sweep over the jump tick, holding
right, **never landed below the start ledge at all**. Four of the six tolerances were therefore
a level-design error in the check wearing the vocabulary of a bot limitation. The pit is now 100
units (ground removed for x in 120..220) — the size the real submissions shipped (`unity__t0`
78.5; `ts__t0` at 520-600, 1080-1180, 1700-1790) — still bottomless, and crossable: walking off
lands in it, jumping at `_EDGE_JUMP_WITHIN` lands at x=248.1 against a far lip at x=208.

**Pinned in both directions, by monkeypatching the repaired bot and re-running the variant:**

| knocked out | variant goes |
|---|---|
| nothing (as repaired) | GREEN, all 19 scored criteria |
| `_hurt` reverted to its pre-repair body | RED on exactly the 4 contact criteria — reproduces the pre-fix state |
| `_edge_distance` blinded to `None` | RED on all 6 |
| the edge jump removed from `_walk_toward` | RED on all 6 |

Full suite: 36 criteria pinned both ways, 4 variants, 3 session-lock controls, 0 unmet, exit 0.
The evidence on the pit level is measurement rather than tolerance: 4 `player_hit`, hp 4.0 →
0.0, smallest inter-hit gap 48 ticks (= `INVULN_TICKS`), knockback vx 180.0 → -240.0 (=
`KNOCKBACK_X`).

**`wg-g4c` needs no re-grade.** Its eight stored `playbot.json` files already pass all six on
all eight submissions; the only exception is `unity__t0`'s `knockback.applied`, *unscored* for
the separate reason in #89. The repair is prospective, for the next gapped submission.

**Found on the way, filed as task 91: `_approach` never had a caller.** `git log -S
"self._approach"` finds no commit in which the call site appears, and a spy on the method counts
0 calls across a full probe session against 390 for `_walk_toward` (the spy's own positive
control). It was deleted here and its measured history folded into `_walk_toward`'s docstring.
`eval/findings/certifies-nothing.md` read `attack.damages` coming back byte-identical after
`_approach` was "repaired" as proof that `_combat` shadowed it; the fuller cause is that nothing
ran it — a second copy of a loop and an unreachable copy of a loop are indistinguishable by
exactly the observation that was made. Task 18's stated mechanism named it too. A finding number
was not taken because ten tasks were in flight and several allocate numbers.

**Not done, deliberately:** `stage.completes` stays diagnostic-only. It still fails on the pit
level (reaches x=242.5 of a goal at 2300 — it crosses the pit and then dies walking into enemies
without ever attacking), because `_stage` is a *fourth* "walk right" loop that `_walk_toward`
does not serve: it has no target to walk toward. Promoting it needs its own three awkward
reference levels (#126), as the done-when says.
