---
id: 159
title: rally.counts reads the counter only on the paddle_hit tick, and its evidence string does not say which way it read
status: in_review
priority: 3
refs: eval/judge/bot_pong.py, eval/judge/bot_mutants.py, tasks/155
done_when: Either the criterion accepts an increment within a small window after the hit and the pending entry comes back with an empty failing set and is promoted into VARIANTS, or the one-tick contract is DECLINED with the reason written into bot_pong.py and the pending entry removed with that reason. Either way the evidence string states what it measured, and bot_mutants.py exits 0.
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/43
---

bot_pong._rally compares state rally across the single tick that raises paddle_hit. Nothing in the g1 prompt orders the event against the counter, and a simulation that emits the event where the collision is resolved and settles its counters in an end-of-tick pass lands the increment one tick later. Measured 2026-08-25 in eval/judge/bot_mutants.py PENDING_VARIANTS: a ref_pong fixture whose counter settles one tick after the hit fails rally.counts. PROVENANCE IS WEAKER THAN THE OTHER PENDING ENTRIES and that is worth stating - those trace to an adjudicated submission, this one is constructed from the state contract, and rally.counts has never failed in the 25 stored g1_pong gradings. A second and smaller defect sits in the same criterion: its evidence reads rally counter incremented on paddle hits regardless of the verdict, so a reader cannot tell a pass from a fail without the boolean beside it.

## note 2026-08-26

## note 2026-08-26 (orchestrator) — independent of 166, and DECLINING is the stronger-looking outcome here

**Safe to run now.** `tasks/166` says the bots locate a game's end from the state flag *or* a
`game_over` event and score it from the flag alone, and that may reframe `158` (tetris) and `160`
(arena). This one is pong and does not touch end-detection, so it is the member of that cluster
with no ordering dependency. It still edits `bot_mutants.py`, so it must not run beside the other
three.

## Take the provenance paragraph seriously — it is the ticket's own warning

The body says it plainly: this pending entry is **constructed from the state contract**, not traced
to an adjudicated submission like its siblings, and `rally.counts` has **never failed in the 25
stored g1_pong gradings**. That is a materially weaker case than `157`'s, which came from a real
Rust submission with a 96-tick lockout.

So **declining the one-tick contract, with the reason written into `bot_pong.py`, is a real
outcome and may be the right one.** What decides it is not taste: read the g1 prompt and say
whether it orders the event against the counter. If it does, the criterion is right and the
constructed fixture is a submission that violates the contract. If it does not, a submission that
settles counters in an end-of-tick pass is correct and the criterion is a false negative.

**Do not widen the window because widening is cheap.** A window that accepts an increment "soon
after" also accepts one caused by something else — and this criterion has 25 stored passes whose
meaning would change.

## The second defect is separable and should land either way

The evidence string reads *"rally counter incremented on paddle hits"* **regardless of the
verdict**, so a reader cannot tell a pass from a fail without the boolean beside it. That is
unambiguous, cheap, and independent of the contract question. **Fix it even if the main change is
declined** — an evidence string that reads the same on both verdicts is the shape #183 found in
`fire.rate_limited`, printing the right number beside the wrong reading.
