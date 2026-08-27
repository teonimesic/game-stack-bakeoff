---
id: 170
title: multiplier.falls reads the multiplier on the player_hit tick, and the g3 contract does not define the multiplier at all
status: in_progress
priority: 3
refs: eval/judge/bot_arena.py, eval/judge/bot_mutants.py, eval/suites/wholegame_prompts.py, tasks/159
done_when: Either the one-tick reading is DECLINED with the reason written into bot_arena.py and the HAZARDS answer for ref_arena/multiplier.falls updated to state it, or a Pending is added to bot_mutants.PENDING_VARIANTS with a constructed correct game and its measured failing set, and the criterion repaired. Either way the ref_arena/multiplier.falls HAZARDS row stops saying OPEN and not constructed, and bot_mutants.py exits 0.
---

tasks/159 declined the same one-tick reading for rally.counts, and the reason does not carry here. It turned on the g1 contract DEFINING rally as the number of consecutive paddle hits since the last point - a count of the very events the trace line carries - so a line raising paddle_hit with a rally that excludes it contradicts itself. The g3 contract gives multiplier no definition: the state block shows the field, and the prose says only that a multiplier rises with sustained killing and falls when the player is hit. Nothing there fixes the tick on which it falls, so bot_arena reading it across the player_hit tick may be a false negative for a game that drops it a tick later, or on the next kill, or over a ramp. Decide it, do not copy 159. Note the same question applies to multiplier.rises, which asks only that the multiplier rose by any mechanism and is therefore not exposed the same way.

## note 2026-08-27

## note 2026-08-27 (orchestrator) — run the loop-bound check for yourself; it was NOT done for you

`tasks/166` records an ordering decision over the tickets that serialise on `eval/judge/bot_mutants.py`,
and it shows `158` and `160` independent of 166's end-detection defect by reading their loop bounds.
**That showing does not extend to you and must not be inherited.** You are `bot_arena`, which is the
one module whose wave/kills collection at lines 465-472 *does* break on `t.state.get('game_over') is
True` — the flag alone. So you have a prior reason to be entangled with end-detection that the
other two did not.

Do the same cheap check first and record the answer in `tasks/166`: is the window
`multiplier.falls` is computed over truncated by end-detection, or is it a fixed tick count? If it
is truncated, say so there — it re-opens the order and 166 may need to run before you rather than
last.

**158 and 160 have both merged**, so branch from `main` and expect no rebase. The suite is at
**44 criteria pinned in both directions, 11 variants, 0 pending, 3 session-lock controls, 70
hazards, 0 unmet**, exit 0 — that is your baseline; re-run it and state the new figures rather than
assuming only your own rows moved.

**And the thing 160 established that bears directly on your decision**, because your ticket offers
the same two-way choice: 160's ticket prescribed a repair and the prescribed repair was **fail-open**
(#190). The rule it produced — *a criterion that fails on a HIGH count takes the maximum of its
candidate signals; one that fails on a LOW count the minimum* — generalises past counting. Whichever
way you decide the one-tick reading, state **what must still FAIL** after your change, and check it
does.
