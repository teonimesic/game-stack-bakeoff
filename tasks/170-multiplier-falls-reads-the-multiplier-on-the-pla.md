---
id: 170
title: multiplier.falls reads the multiplier on the player_hit tick, and the g3 contract does not define the multiplier at all
status: done
priority: 3
refs: eval/judge/bot_arena.py, eval/judge/bot_mutants.py, eval/suites/wholegame_prompts.py, tasks/159
done_when: Either the one-tick reading is DECLINED with the reason written into bot_arena.py and the HAZARDS answer for ref_arena/multiplier.falls updated to state it, or a Pending is added to bot_mutants.PENDING_VARIANTS with a constructed correct game and its measured failing set, and the criterion repaired. Either way the ref_arena/multiplier.falls HAZARDS row stops saying OPEN and not constructed, and bot_mutants.py exits 0.
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/52
established_by: 'Merged as PR #52. REPAIRED rather than declined, and tasks/159''s reason genuinely does not carry: 159 turned on g1 DEFINING rally as a count of the events a tick line carries, and g3 defines multiplier nowhere. What decided it is internal to the criterion pair - one sentence of the g3 contract governs both halves, and multiplier.rises reads its half over hundreds of ticks by any mechanism, so reading the fall to the exact tick was an asymmetry nothing licensed. The criterion now reads the damage tick and the 8 after it. The half the ticket did not anticipate is the one that mattered: the criterion compared the PEAK the killing phase reached against the value on the hit tick, and on ref_arena those readings are 459 idle ticks apart - so a game with NO damage link at all passed, because a combo timer lowered the multiplier somewhere inside the gap and the criterion credited the decay to the damage, with an evidence string byte-identical to a correct submission''s. The baseline is now the value on the tick BEFORE the damage, making this a widening in time and a tightening in what it compares. Verified by the orchestrator on the branch: bot_mutants.py exit 0 at ''45 mutants pinned in both directions over 41 criteria, 12 variants, 0 pending, 3 session-lock controls, 70 hazards, 0 unmet'' against a 44/11 baseline, with the combo-timer mutant flipping PASS->FAIL and the one-tick-late correct game passing. The control was built the right way round: the pre-repair bot_arena.py was loaded from git ahead of the worktree copy on sys.path with an assertion on bot_arena.__file__, so the old behaviour was established rather than inferred from the repair. The tasks/166 check I asked for was run and recorded there: multiplier.falls'' windows ARE truncated by end-detection, unlike 158 and 160, but it does not re-open the ordering because both loops break on the state flag alone and never on a game_over event, so the event branch could only make them exit earlier on a game that fails either way. One hazard left open and bounded rather than closed: a correct game with both a combo timer and a damage collapse whose timer lapses inside the window - the span it could land in was 459 ticks and is now 9. Findings #195.'
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

## note 2026-08-27

## Outcome: REPAIRED, not declined — and the repair closed a fail-open channel nobody had asked about

**The one-tick reading is not derivable from the g3 contract, and `tasks/159`'s reason does not
carry.** 159 turned on g1 **defining** `rally` as a count of the very events the tick line
carries. g3 defines `multiplier` nowhere: it says a multiplier *"rises with sustained killing and
falls when the player is hit"* and declares a `multiplier` event meaning *"the score multiplier
changed"*.

**What decided it is internal to the criterion pair.** One sentence governs both halves, and
`multiplier.rises` reads its half over hundreds of ticks by any mechanism. Reading the fall to
the exact tick was an asymmetry the contract does not license. The criterion now reads the damage
tick **and the 8 ticks after it**, taking the first of those 9 on which the multiplier moves.

## The half the ticket did not anticipate, and it is the one that mattered

The criterion compared the **peak the killing phase reached** against the value on the hit tick.
On `ref_arena` those two readings are **459 idle ticks apart** — phase 1 ends after 188 ticks with
the multiplier at 2, and the first `player_hit` arrives 459 idle ticks later. Anything that
lowered the multiplier in between passed, whether or not damage caused it.

**The baseline is now the value on the tick BEFORE the damage.** So the change is a widening in
time and a tightening in what it compares.

## Measured, both directions, before the repair was written

`git show HEAD:eval/judge/bot_arena.py` (at `4258c135e`) loaded ahead of the worktree copy on
`sys.path`, with an assertion on `bot_arena.__file__`, driving `_multiplier_falls` over three
builds of `eval/judge/fixtures/ref_arena`:

| fixture | old | new |
|---|---|---|
| reference | PASS | PASS |
| the collapse lands the tick after the damage (**correct**) | **FAIL** | **PASS** |
| a combo timer, and damage never touches the multiplier (**incorrect**) | **PASS** | **FAIL** |

Row 2 is now a `VARIANTS` entry, row 3 a `MUTANTS` entry. No `Pending` was added: a pending is a
declared false negative *waiting* for a repair, and the repair landed on the same branch.

## THE FINDING, and it needs a number from the orchestrator

**`multiplier.falls` had a fail-open channel that predates this ticket, and its evidence string
was byte-identical to a correct submission's.** A game with **no damage link at all** passed,
because a combo timer had lowered the multiplier somewhere inside that 459-tick gap and the
criterion credited the decay to the damage. Both the reference and that game produced
`multiplier was 2 before damage and 1 on the tick of the first hit`.

**A mutant could not have found it** (rule 15). `NO_MULT_FALL` removes the collapse and leaves a
multiplier that never moves after the killing stops, and the criterion goes red as designed. This
needed a correct-**shaped** input the criterion mishandles — a multiplier that moves for a reason
that is not the damage — which is the variant half.

**The honest limit, and it is `tasks/159`'s exactly:** whether any stored pass came through that
channel **cannot be read back**, because the old evidence printed the peak rather than the
pre-hit value. `python3 eval/judge/tier2_census.py --runs-root <checkout>/eval/runs` —
`g3_arena/multiplier.falls` is 8 gradings, 2 failures, unchanged, and the census cannot move
offline because tier-2 verdicts are stored rather than recomputed. The 2 failures are both
`g3_arena__rust__*`, whose probe would not compile. All 6 measurable submissions dropped the
multiplier on the hit tick, so all 6 remain a pass under the new reading.

## What must still FAIL, and does (#190)

- **survives damage** — `NO_MULT_FALL`: FAIL, `8 tick(s) after the first hit it still read 2`
- **moves for a reason that is not the damage** — the new mutant: FAIL, `the multiplier peaked at
  2 and was already back to 1 on the tick before the first hit ... it moved 1 time(s) on its own
  while idling`
- **never rises** — `NO_MULT_RISE`, collateral: unchanged

The 3 evidence strings read differently from each other and from a pass.

## The one hazard left OPEN, and why it was not closed

A *correct* game with **both** a combo timer **and** a collapse on damage, whose timer happens to
lapse inside the window, has that drop credited to the damage. **Bounded rather than closed:** the
span it could land in was 459 ticks and is 9, and a timer that lapses *before* the hit is now
caught outright by the baseline moving. Closing it needs a **second** hit to compare against, and
the multiplier is at 1 by then. Recorded in the `ref_arena/multiplier.falls` HAZARDS answer.

## For the next agent

- **The scripted driver is NOT in the repository.** It is 60 lines: copy `fixtures/ref_arena` to a
  temp dir, apply `bot_mutants.MULT_DEFERS_THE_DROP` / `MULT_DECAYS_ON_A_TIMER` by exact-string
  replacement, then call `bot_arena.BOT._multiplier_falls(repo, None)` directly. Driving the one
  criterion takes ~1.4s against ~4min for the whole suite, and the `old`-vs-`new` axis is a
  `sys.path` shadow over `git show HEAD:eval/judge/bot_arena.py` plus an assertion on
  `bot_arena.__file__` — without that assertion the comparison silently runs the same module twice.
- **The 459 is a measurement, not a constant.** Phase 2 idles that long on `ref_arena` at seed 7.
  Anything reasoning about the window's width should re-measure rather than quote it.
- **`multiplier.rises` was deliberately left alone.** It already asks only that the multiplier
  rose, by any mechanism, over the whole combat session, so it is not exposed the same way.

## Three stale counts fixed in passing

- `bot_mutants.py`'s summary line said **`criteria`** over a count of **mutant rows**. The second
  mutant on `multiplier.falls` moved it 44 → 45 while the per-criterion count stayed at 41. It now
  names both populations: `45 mutants pinned in both directions over 41 criteria`.
- The `HAZARDS` header comment carried 3 hardcoded figures, one of them (`36 criteria carry a
  mutant`) wrong by 5 *before* this branch. Replaced with the argument and a pointer at
  `--hazards`.
- `eval/judge/RUBRIC.md` restated `40 criteria across 4 games, 8 variants`, and its prose list of
  arena mutants was an **incomplete census** — 12 of the 15 rows, missing `enemies.chase` and the
  second `fire.rate_limited`. Both repaired.

`eval/G4-PLATFORMER.md` restates a stale mutant count and was left alone: it opens by saying it is
a record of what was expected rather than of what is true now.

## The loop-bound check for `tasks/166` — recorded there, and it did not move the order

`multiplier.falls`' windows **are** truncated by end-detection (both loops, lines 1065 and 1086 at
`4258c135e`), unlike 158's and 160's fixed tick counts. **It does not re-open 166's ordering**,
because both break on the **state flag alone** and never on a `game_over` event. Adding the event
branch could only make them exit earlier on a game that raises the event and leaves the flag
`False`, and on such a game the verdict is a fail either way.
