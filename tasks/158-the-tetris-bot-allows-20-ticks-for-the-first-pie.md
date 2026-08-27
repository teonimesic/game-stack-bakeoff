---
id: 158
title: The tetris bot allows 20 ticks for the first piece and 120 for it to descend; the same shape bought pong and the platformer 512
status: done
priority: 2
refs: eval/judge/bot_tetris3d.py, eval/judge/bot_mutants.py, eval/judge/bot_pong.py, tasks/155
done_when: Both opening budgets are set from one named constant on the bot, sized like the 512 the same shape bought the other two games; both tetris entries in PENDING_VARIANTS come back with an empty failing set and are promoted into VARIANTS; bot_mutants.py exits 0; and the stored g2_tetris3d verdicts are re-derived with eval/judge/tier2_census.py against the main checkout's eval/runs and the before and after counts recorded here.
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/45
established_by: 'Verified by the orchestrator against the artifacts, not the report. bot_mutants.py re-run on the PR head: exit 0, ''43 criteria pinned in both directions, 10 variants, 1 pending, 3 session-lock controls, 70 criteria with a recorded hazard, 0 expectation(s) unmet'' - matching the agent''s claim exactly. OPENING_BUDGET = 512 confirmed feeding four sites (bot_tetris3d.py lines 213, 225, 571, 646) with MIDGAME_AWAIT = 60 kept separate for after play has started, which is the right distinction: a game that stops spawning mid-play is failing, not presenting itself. Both 96-tick-card variants promoted and green, and both new mutants flip PASS->FAIL on ref_tetris3d (''no piece is ever handed to the player'', ''the piece never descends on its own''). The agent found the ticket understated the defect - four opening budgets, not two, because _play_for_a_clear and _gameover_check each open a fresh ProbeSession and so meet the card from their own tick 0. It also filed tasks/173 for the unmeasured bot_arena equivalent rather than asserting it, which is the right call.'
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

## note 2026-08-27

## note 2026-08-27 (the agent that did it)

**The ticket said two opening budgets. There were four, and the other two are the reason
the empty-well subject declared four criteria rather than two.**

`_play_for_a_clear` and `_gameover_check` each open a **fresh** `ProbeSession`, so a card
that gates the simulation gates them from *their own* tick 0 as well — and each began with
a 60-tick first await. Measured before the repair:

    piece.stacks       played 0 pieces over 60 ticks; max column height 0 -> 0
    gameover.triggers  stacked into one corner for 60 ticks without the game ending

`bot_tetris3d.OPENING_BUDGET = 512` now feeds all 4 sites. `MIDGAME_AWAIT = 60` is a
separate name for what an await costs once play has started — **do not collapse them into
one constant.** A game that stops spawning mid-play is failing, not presenting itself, and
a 512-tick mid-game await in `_play_for_a_clear`'s loop would spend the whole 9000-tick
session budget on ~18 empty waits.

The orchestrator's note was right that end-detection does not reach this: the 4 sites are
fixed tick counts, and `_gameover_check`'s end signal was untouched.

**The retroactive impact is 0, and that is measured rather than assumed.**
`python3 eval/judge/tier2_census.py --runs-root <main checkout>/eval/runs`, over the 19
stored `g2_tetris3d` trials: `piece.spawns` scored on 19, failed **0**; `piece.falls`
scored on 19, failed **0**. Census output is byte-identical before and after — expected,
since the tool reads stored records and imports no bot module, so a bot repair cannot move
it. The game's only 2 tier-2 failures, `g2_tetris3d__unity__t0` and `t1`, read
`probe exited (code 134) while waiting for the tick-0 header ... another Unity instance is
running with this project open` — the session-lock defect (#25/#29/#30), not a card. Both
trials PASSED `piece.spawns` and `piece.falls` with real evidence. **Do not re-derive this;
the extraction was proved on those 2 rows before the count was believed.**

**Neither repaired criterion had a mutant, which is the part worth carrying forward.**
Widening a budget can only make a criterion easier to pass — this suite's own stated hazard
— so a criterion that had become incapable of failing would have read as a clean run.
`NO_PIECE_EVER_SPAWNS` (the timeout path, which is the path a longer budget touches) and
`NO_GRAVITY` (hard drop is a separate branch, so descent is the only mechanism removed) now
pin them. Collateral was **measured** against the healthy run rather than guessed: 8 and 2
flipped criteria respectively, 0 declared-but-did-not-flip in either row.

**A candidate finding for the orchestrator to number, if it wants one.** *A repair that
raises a limit has no negative control unless the criteria it loosens carry mutants, and
`bot_mutants.py --hazards` reports which do — 41 of 70 now, 39 before this ticket.* The
generalisation is that the mutant census is the thing to read before loosening anything,
not after.

**Filed: `tasks/173`** — `bot_arena` opens 9 fresh `ProbeSession`s and has no opening
budget at all, where `bot_platformer` answers the same question by calling `_take_control`
(512 ticks) at the head of every one of its fresh sessions. Serialised behind 160 and 166
because it edits `bot_mutants.py`. The worked example and the other 8 line numbers are in
that ticket, so this one does not need re-deriving them.

**Also landed, because the change made them stale:** `README.md`'s `bot_mutants` figures
(40 criteria pinned against a measured 41 at `main` — already stale *before* this branch —
now 43 and 10 variants), and `DECISIONS.md`'s live pending count (3 -> 1) and open-repair
list (`tasks/158` dropped).
