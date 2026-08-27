---
id: 173
title: The arena bot opens 9 fresh probe sessions and none of them has an opening budget
status: done
priority: 2
refs: eval/judge/bot_arena.py, eval/judge/bot_tetris3d.py, eval/judge/bot_mutants.py, tasks/158
done_when: 'Every fresh ProbeSession bot_arena opens is read for how many ticks it will wait before it concludes anything, that number is written down per session, and either all of them are at or above an arena opening budget sized like bot_pong.LIVE_BUDGET or the short ones are repaired from one named constant the way tasks/158 repaired bot_tetris3d. Either way bot_mutants.py gains a ref_arena subject carrying a 96-tick opening card: a Variant if it comes back with an empty failing set, a Pending declaring exactly what it fails with this ticket as owner if it does not. Every criterion the repair makes easier to pass carries a mutant proving it can still go red. bot_mutants.py exits 0.'
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/56
established_by: 'Merged as PR #56. MEASURED rather than reasoned: the agent lengthened a simulation-gating title card over ref_arena and read the failing set at each length, predicting every flip point from the code first and matching each one. Per-session ticks-before-it-concludes and the card that first reddens it: main->_moves 30/axis 90 total, reddens at 30; main->enemies.spawn 300 after _moves'' 90, at 390; _analog.push 30, at 30; _walls 900, at 701-800; _kinds 6000, none <=1000; _materialises 300, at 300; _chase 400, at 368; _firing_in 120/240/360, at 120 and 360 for aim.three_axis; _combat/_multiplier_falls/_death 9000/6000/9000, none. The first boundary is exact - 29 clean, 30 red. THE TICKET''S POPULATION WAS WRONG AND THE AGENT CORRECTED IT: I wrote 9 fresh probe sessions; the shortest budget is _moves, which runs in the main session probe.drive opens, so it is 10 places. Verified independently - _take_control appears 11 times in bot_arena.py, one definition and ten call sites. OPENING_BUDGET = 512 now feeds all ten via _take_control, the same budget bot_platformer uses, and NO criterion''s own budget was widened - only a wait added in front of it, returning on the first answering tick, so a playing game pays 1 tick. Verified: bot_mutants.py exit 0 at ''49 mutants pinned in both directions over 45 criteria, 13 variants, 0 pending, 3 session-lock controls, 70 hazards, 0 unmet'' against a 45/41/12 baseline. THE COST IS STATED RATHER THAN HIDDEN: a card of 513-800 ticks used to leave player.bounded and wall.graze green and now does not. Two further pieces of judgement worth keeping: the 9 sibling ''if not live:'' branches are UNREACHABLE on a deterministic game, because every session opens the same seed on the same fixture so the main session''s take-control decides them all - kept fail-closed for a nondeterministic submission and recorded in the ticket rather than papered over with a contrived mutant; and 4 mutants were added for criteria the repair makes EASIER that had never been shown able to fail, which is 158''s lesson applied without being told. Blast radius zero: 6 of 8 stored wg-arena3d trials pass all 23 criteria, 2 are probe-unusable, and no stored FALSE is card-shaped. Findings #197.'
---

Task 158 found that bot_tetris3d had FOUR opening budgets, not the two its ticket named: the 20-tick await and the 120-tick fall loop in the criteria drive, AND the first await of each of the two fresh ProbeSessions that _play_for_a_clear and _gameover_check open, both of which were 60. A card that gates the simulation gates every session from that session's own tick 0, so a fresh session's FIRST wait is an opening budget and not a mid-game one. Measured 2026-08-27 on ref_tetris3d: a 96-tick card over an empty well failed piece.stacks and gameover.triggers on exactly that, reading 'played 0 pieces over 60 ticks' and 'stacked into one corner for 60 ticks'. bot_platformer already answers this - every fresh session it opens calls _take_control, which waits _CONTROL_TICKS = 512. bot_arena has no equivalent: it opens 9 fresh sessions (ProbeSession at bot_arena.py lines 314, 357, 448, 501, 730, 860, 936, 1015 and 1066) and there is no shared opening wait among them. Whether any is short enough to be gated by a 96-tick card is UNMEASURED. The HAZARDS registry carries a recorded answer per arena criterion, but none of those answers was written against this property - the one opening-card row on ref_arena, enemies.spawn, answers for the 300 ticks that ONE criterion waits. SERIALISE: this edits eval/judge/bot_mutants.py, so it cannot run alongside 160 or 166.

## note 2026-08-27

## the one session already read, so the next agent starts from 8

`_analog` at `bot_arena.py:302` opens a fresh `ProbeSession` inside `push()` (line 314)
and immediately steps `_ANALOG_TICKS = 30` with a movement vector held, then reads the
displacement. A card that gates the simulation for 96 ticks leaves that displacement at
0 for every magnitude, and the criterion's own next branch reads `a full push moved only
0.00 units, so a proportional response cannot be measured`. **That is a construction, not
a measurement** - nobody has driven a carded `ref_arena` yet, which is what the subject in
`done_when` is for.

The other 8 are `bot_arena.py` lines 357, 448, 501, 730, 860, 936, 1015 and 1066.

**Do not read a short wait as a defect on its own.** `_kinds` at line 448 opens with a
1200-second timeout and plays until three kinds have been met, so its budget may already
swallow a card; the question is per session, and the answer that closes this ticket is the
per-session number, not a single verdict about the bot.

## note 2026-08-27

## note 2026-08-27 (orchestrator) — 158 and 160 have MERGED; you are next on bot_mutants.py

This ticket was filed by 158's agent and says it is serialised behind 160 and 166. **160 merged.**
166 is still todo and is deliberately LAST — see `tasks/166`, which carries the ordering and its
derivation. Nothing else holds `eval/judge/bot_mutants.py` right now, so branch from `main` and
expect no rebase.

**Your baseline, re-run by the orchestrator at the merged head:** `python3 eval/judge/bot_mutants.py`
exits 0 at **45 mutants pinned in both directions over 41 criteria, 12 variants, 0 pending, 3
session-lock controls, 70 criteria with a recorded hazard, 0 unmet**. State the new figures after
your change rather than assuming only your own rows moved — two tickets in a row found the summary
line's populations had drifted.

**What 158 established, since this ticket is its direct descendant.** `bot_tetris3d` had FOUR
opening budgets, not the two its ticket named, because `_play_for_a_clear` and `_gameover_check`
each open a *fresh* `ProbeSession` and so meet a title card from their own tick 0.
`OPENING_BUDGET = 512` now feeds all four, with `MIDGAME_AWAIT = 60` kept separate on the
reasoning that **a game that stops spawning mid-play is failing, not presenting itself**. That
distinction is the one to carry: your 9 sessions are not all opening sessions, and the ticket is a
construction rather than a measurement — nobody has driven a carded `ref_arena`. Measure before
repairing, and if some of the 9 turn out not to need a budget, that is a result.

**And from 170, which merged an hour ago and is the same module:** `multiplier.falls` compared a
peak against a value **459 ticks** later and credited everything in between to the damage (#195).
If your work touches a window, state what must still FAIL after the change.

## note 2026-08-27

## the per-session numbers, so nobody re-derives them

Measured on `ref_arena` by lengthening a title card that gates the simulation and reading
the failing set at each length. Every flip point was predicted from the code first and
each one matched, which is the known-good row rule 12 asks for.

| session | opened at | ticks before it concludes | card that first reddens it |
|---|---|---|---|
| main (`probe.drive`) -> `_moves` | — | 30 per axis, 90 total | **30** |
| main -> `enemies.spawn` | — | 300, after `_moves`' 90 | **390** |
| `_analog.push` | `bot_arena.py` 314 | `_ANALOG_TICKS = 30` | **30** |
| `_walls` | 357 | 900 | **701-800** |
| `_kinds` | 448 | `_KINDS_TICKS = 6000` | none <= 1000 |
| `_materialises` | 501 | 300 | **300** |
| `_chase` | 730 | 400, then 260 + 2x145 | **368** |
| `_firing_in` | 860 | 120 / 240 / 360 | **120**, and **360** for `aim.three_axis` |
| `_combat` | 981 | 9000 | none |
| `_multiplier_falls` | 1095 | 6000 then 4000 | none |
| `_death` | 1179 | 9000 | none |

Line numbers are pre-repair, matching the ticket's own list. **The ticket's 9 sessions
were the wrong population**: the shortest budget in the bot is `_moves`, which runs in
the MAIN session `probe.drive` opens, so the answer is 10 places and not 9.

3 of the flip points are not the loop budget and it is worth knowing why:
`_chase` flips at 368 rather than 400 because the game's own spawn latency
(`WAVE_GAP_TICKS` then `SPAWN_TICKS = 32`) is spent out of the same 400; `enemies.spawn`
flips at 390 because its 300 sit behind `_moves`' 90; and `_walls` flips in a range
rather than at a point because its 900 ticks are a MEASUREMENT window, not a wait - the
card eats travel, and the criterion asks for half the extent on each axis.

## what the repair is, and the one thing it costs

`OPENING_BUDGET = 512` feeds `ArenaBot._take_control`, called at all 10 session heads.
It is `bot_platformer._take_control` on the same budget: hold a full +x push, step until
the player's position moves more than 1.0 unit, return on the FIRST answering tick.

**No criterion's own budget was widened.** Only a wait was added in front of it. That
matters for `move.analog`, which needs its two pushes to start identically: they do, one
tick of movement in - 3.4 units on the reference against a 400-unit half-extent - and
because the wait returns at the first answering tick rather than running to the budget,
an accelerating game is barely moving when it returns.

**The cost, stated because it is real:** at a card of 513-800 ticks, `player.bounded` and
`wall.graze` used to pass and now fail with everything else. A card longer than the
budget is out of scope by the same decision that put pong, tetris and the platformer at
512, and one sentence naming the cause beats 2 greens beside 9 reds.

**The 9 sibling `if not live:` branches are unreachable on a deterministic game** and are
kept anyway: every session opens the same seed on the same fixture, so the main session's
take-control decides them all. They are the platformer's shape, they fail closed, and
they are what a nondeterministic submission would land in.

## blast radius: nothing re-scored, and this is the check to repeat

Over the 8 stored `wg-arena3d` trials, 6 pass all 23 criteria and 2 are probe-unusable (a
Rust submission that does not compile). No stored FALSE is card-shaped, so the repair
re-scores nothing. **Do not read the `wg-matrix` g3 failures as evidence either way** —
that is the retired 2D arena regime and this bot no longer matches its state shape.

## `aim_contract_control.py` had to move with it

Its extraction row read "the 90 opening `player.moves` ticks". The tape's opening is now
**92**: 1 take-control tick, 90 from `_moves`, and 1 more because `enemies.spawn` finds
the wave already present and steps nothing, so `_kinds`' own take-control is next on the
tape. The row now asserts **both directions** - tick 93 must not be pure movement - and
the 92 is written down rather than read out of `bot_arena`.

## for the orchestrator: a finding number is needed

Claim: *the arena play-bot had no opening budget in any of its 10 sessions, and a 96-tick
title card - shorter than the platformer reference's own `OPENING_TICKS` - failed 2 of
its 22 criteria, rising to 9 by 400 ticks and 11 by 900.* Nothing stored is affected, so
it is a false-negative surface that was never exercised rather than a published number
that was wrong.
