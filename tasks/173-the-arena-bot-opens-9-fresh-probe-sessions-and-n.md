---
id: 173
title: The arena bot opens 9 fresh probe sessions and none of them has an opening budget
status: in_progress
priority: 2
refs: eval/judge/bot_arena.py, eval/judge/bot_tetris3d.py, eval/judge/bot_mutants.py, tasks/158
done_when: 'Every fresh ProbeSession bot_arena opens is read for how many ticks it will wait before it concludes anything, that number is written down per session, and either all of them are at or above an arena opening budget sized like bot_pong.LIVE_BUDGET or the short ones are repaired from one named constant the way tasks/158 repaired bot_tetris3d. Either way bot_mutants.py gains a ref_arena subject carrying a 96-tick opening card: a Variant if it comes back with an empty failing set, a Pending declaring exactly what it fails with this ticket as owner if it does not. Every criterion the repair makes easier to pass carries a mutant proving it can still go red. bot_mutants.py exits 0.'
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
