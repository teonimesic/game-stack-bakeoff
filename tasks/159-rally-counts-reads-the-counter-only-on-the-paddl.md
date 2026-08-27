---
id: 159
title: rally.counts reads the counter only on the paddle_hit tick, and its evidence string does not say which way it read
status: in_testing
priority: 3
refs: eval/judge/bot_pong.py, eval/judge/bot_mutants.py, tasks/155
done_when: Either the criterion accepts an increment within a small window after the hit and the pending entry comes back with an empty failing set and is promoted into VARIANTS, or the one-tick contract is DECLINED with the reason written into bot_pong.py and the pending entry removed with that reason. Either way the evidence string states what it measured, and bot_mutants.py exits 0.
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/43
established_by: 'DECLINED: bot_mutants.py exit 0 (41 criteria both directions, 3 pending, 0 unmet), rally.counts now carries its own mutant, evidence reads 6 of 6 / 0 of 33 with 33 late / 0 of 33, and a scripted-tape drive shows origin/main PASSED a late counter with back-to-back hits and it now FAILS. gates + controls + CodeRabbit green on PR 43.'
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

## note 2026-08-26

## Outcome: DECLINED, and the review found a fail-open channel in the same criterion

**The one-tick contract is the task's.** The pending entry `ref_pong/rally.counts` was declared
against a sim that raises `paddle_hit` where the collision resolves and settles its counter a
tick later. That game is **not correct**, so the entry is removed rather than the criterion
widened. Three facts from the task decide it, in order:

1. the probe prints a tick-0 line before anything is stepped, then one line after each step -
   **all four** starter guides say so, so a line describes the state AFTER its own tick;
2. the g1 prompt defines `rally` as *"the number of consecutive paddle hits since the last point
   was scored"* - a count of the events the line carries, not a free variable;
3. so a line cannot both raise `paddle_hit` and report a `rally` that excludes it.

Reproduced on the pending fixture before touching anything: tick 89 reads
`rally=0 events=['paddle_hit']`, tick 90 reads `rally=1 events=[]`. **Where the sim increments
stays free; what the tick's line PUBLISHES does not.** The derivation lives in
`bot_pong._rally`'s docstring and the `HAZARDS` answer for `ref_pong/rally.counts`.

Widening to a window was declined on top of that: rule 7, it would accept an increment caused by
anything, and it would re-mean 25 stored `g1_pong` gradings (`python3 eval/judge/tier2_census.py
--runs-root <checkout>/eval/runs`: `rally.counts` 25 gradings, 0 failures) to buy a pass the
criterion has never once withheld.

## THE FINDING, and it needs a number from the orchestrator

`rally.counts` had a **fail-open channel that predates this ticket**. A counter that settles late
still rises ON a hit tick whenever two hits land back to back - the rise is the PREVIOUS hit's
deferred increment - and reading it as this hit's own let a late game earn its pass off its own
backlog. `ref_pong`'s physics cannot produce consecutive-tick hits, so it was driven over
scripted `(rally, events)` tapes:

| tape | `origin/main` | first push | now |
|---|---|---|---|
| correct, spaced | PASS | PASS 6 of 6 | PASS 6 of 6 |
| correct, back to back | PASS | PASS 6 of 6 | PASS 6 of 6 |
| **late, back to back** | **PASS** | **PASS 5 of 6** | **FAIL 0 of 6, 6 late** |
| late, spaced | FAIL | FAIL 0 of 6 | FAIL 0 of 6, 6 late |
| frozen | FAIL | FAIL 0 of 3 | FAIL 0 of 3 |

`settled_late` now gives each rise exactly one owner, and the hit whose own increment is still
outstanding re-arms the watch. A watch is not opened on a scoring tick, where a zeroed `rally`
would make the next rise read as late.

**The honest limit: whether any of the 25 stored gradings passed through that channel cannot be
read back**, because the evidence string of the day printed the same sentence on both verdicts.
That is the argument for the new one, and it means this repair MAY move a stored verdict with
nothing on disk able to say whether it does. It is a fail-open repair, so rule 7 says take it.

**A mutant could not have found this** (rule 15): `RALLY_FROZEN` removes the counter and the
criterion goes red as designed. The channel needed a correct-shaped INPUT the criterion
mishandles, which is the variant half - and it took a reviewer, not the suite.

## What else changed

- **`rally.counts` gains a mutant of its own**, `RALLY_FROZEN`. It carried only collateral on
  `ball.moves` and `paddle.deflects`, both of which stop the rally happening at all, so neither
  asked whether the counter can be read wrong while the game plays normally. `rally.resets` is
  not collateral: a counter frozen at 0 reads 0 on the scoring tick.
- **The evidence string reads differently on each verdict** and separates the two failures:
  `rally rose on 6 of 6 paddle_hit ticks` / `0 of 33 ... on 33 of them it rose on the FOLLOWING
  tick instead` / `0 of 33` with no late line.
- **Two stale counts fixed with a producer.** `bot_mutants.py`'s docstring said 36 criteria carry
  a mutant against a measured 38, and *"2 of the 6"* pending false negatives are unmutated
  against a measured 3 of 6; `DECISIONS.md` repeated both. `--hazards` now prints all three and
  names the unmutated criteria; both documents point at it instead of restating a number.

## What this deliberately did NOT settle

- **`ref_arena/multiplier.falls`** said it should be settled with this ticket. It should not: the
  g3 contract gives `multiplier` **no definition at all**, only that it *"falls when the player
  is hit"*, so step 2 above is missing there. Its `HAZARDS` answer now says so. **`tasks/170`.**
- **`rose_on_hit > 0`** still answers *"on at least one of them"* to a question that asks *"on
  each"*, and `deflect_ok` beside it is already all-or-nothing. Raised by the reviewer as a
  Major; tightening it is a deliberate re-scoring event with its own `tier2_census.py`
  before-and-after, which `eval/judge/AGENTS.md` and `DECISIONS.md` both require to carry its own
  ticket. **`tasks/171`**, which records that the obvious `hits >= 6` sample floor is itself a
  new false-negative channel of the #46 family and that the loop's early break has to move with
  it.

## For the next agent

The scripted-tape driver used for the table is throwaway and is NOT in the repository - a
`FakeSession` yielding `(rally, events)` per tick into `PongBot._rally`. `rose_late` is
diagnostic-only and enters no verdict, so a shipped pin looked disproportionate; if `tasks/171`
changes the verdict function, that is the moment to ship one.
