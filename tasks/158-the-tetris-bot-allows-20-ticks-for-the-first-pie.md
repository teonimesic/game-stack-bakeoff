---
id: 158
title: The tetris bot allows 20 ticks for the first piece and 120 for it to descend; the same shape bought pong and the platformer 512
status: todo
priority: 2
refs: eval/judge/bot_tetris3d.py, eval/judge/bot_mutants.py, eval/judge/bot_pong.py, tasks/155
done_when: Both opening budgets are set from one named constant on the bot, sized like the 512 the same shape bought the other two games; both tetris entries in PENDING_VARIANTS come back with an empty failing set and are promoted into VARIANTS; bot_mutants.py exits 0; and the stored g2_tetris3d verdicts are re-derived with eval/judge/tier2_census.py against the main checkout's eval/runs and the before and after counts recorded here.
---

A Godot pong submission held the ball for OPENING_DELAY = 104 so the title card is readable, which is FINDINGS #34; bot_pong.LIVE_BUDGET became 512 and bot_platformer._CONTROL_TICKS is 512. bot_tetris3d was never revisited: its piece.spawns loop awaits a four-cell piece for 20 ticks and its piece.falls loop steps 120 ticks against a fall interval of 48. The task preamble asks every game to present itself, and the platformer REFERENCE in this repository ships OPENING_TICKS = 96. Measured 2026-08-25 in eval/judge/bot_mutants.py PENDING_VARIANTS, on ref_tetris3d, two independent budgets: a 96-tick card that freezes the well with the piece visible fails piece.falls alone; a 96-tick card that shows the well empty until the card clears fails piece.spawns, piece.falls, piece.stacks and gameover.triggers - four of fifteen criteria. The boundary is exact: an 18-tick card passes and a 21-tick one fails, against an await limit of 20.

## note 2026-08-27

## note 2026-08-27 (orchestrator) — you are first of three, and 166 is NOT a blocker

`158`, `160` and `166` all edit `eval/judge/bot_mutants.py` and cannot run concurrently. The order
is settled — **158, then 160, then 166** — and the derivation is in `tasks/166`.

What matters for you: **166 says the bots locate the end of a game from the state flag OR a
`game_over` event and then score it from the flag alone.** That defect is real and it does not
reach you. The first-piece window you are repairing is `for _ in range(20)` at `bot_tetris3d.py`
line 189 and `for _ in range(120)` at line 201 — fixed tick counts, not a window truncated by
end-detection, which is built separately at line 250 from `_gameover_check` at line 607.

So do not widen your scope into end-detection, and do not wait on 166. If you find your repair
DOES depend on which end signal is authoritative, that contradicts the check above — say so in the
ticket and stop, because it would re-open the ordering.
