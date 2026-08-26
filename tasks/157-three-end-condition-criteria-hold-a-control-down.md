---
id: 157
title: Three end-condition criteria hold a control down after the game ends; pong's presses nothing, and that repair was never carried across
status: in_testing
priority: 2
refs: eval/judge/bot_mutants.py, eval/judge/bot_arena.py, eval/judge/bot_platformer.py, eval/judge/bot_tetris3d.py, eval/judge/bot_pong.py, tasks/155
done_when: The three criteria establish that PLAY stopped rather than that inputs were refused, the way match.ends does; the matching entries in PENDING_VARIANTS come back with an empty failing set and are promoted into VARIANTS; bot_mutants.py exits 0; and eval/judge/tier2_census.py is re-run against the main checkout's eval/runs with the before and after verdict counts recorded in the ticket.
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/40
established_by: 'PR #40, all checks green (gates, controls 14m16s, CodeRabbit). bot_mutants.py exit 0 at 40 criteria pinned / 8 variants / 4 pending / 0 unmet, against exit 1 on 4 rows with the pre-repair bots; tier2_census before and after is byte-identical over 69 trials; see the note for the fail-open measurement that needs a finding number.'
---

bot_pong._match_ends idles 600 ticks after the win, because a real Rust submission held a game-over card for GAME_OVER_LOCKOUT_TICKS = 96 and then let a control start a new match, and pressing inputs restarted it. The g3 and g4 prompts carry the identical sentence - the game stops accepting play until it is reset - yet bot_arena._death holds fire, aim and move for 300 ticks after death and bot_platformer._hurt holds move_right, jump and attack for 200, and bot_tetris3d._gameover_check holds hard_drop and move_pos_x for 200. Measured 2026-08-25 in eval/judge/bot_mutants.py PENDING_VARIANTS: a fixture that takes a control as a reset after a 96-tick card fails gameover.triggers on ref_arena and ref_platformer. On ref_tetris3d the same fixture PASSES, and the pass is not evidence - the game restarted and stacked out again inside the window, and the score reset to 0 made the frozen test true. Raise the card to 190 ticks on the same fixture and the verdict flips to False, so the verdict is a function of the card length rather than of the game. Blast radius measured: all 6 stored gameover.triggers failures in eval/runs are probe-unusable session failures, none of them this shape, so no stored FALSE turns TRUE - but a stored PASS could turn FALSE and that is a re-scoring event.

## note 2026-08-25

## What landed, and what the next agent must not re-derive

**The repair is not the one the ticket prescribed, and the difference was measured.**
The ticket asks for pong's fix — press nothing after the end. That makes both
`tasks/157` pending entries come back with an empty failing set, and it is
**fail-open**. Measured out of band with a mutant that reports `game_over` and keeps
the simulation stepping (`ARENA_KEEPS_STEPPING` in `bot_mutants.py`, and its
platformer and tetris siblings):

| fixture | pre-repair `_death`/`_hurt`/`_gameover_check` | idle only |
|---|---|---|
| `ref_arena` | FAIL (caught) | **PASS — survived** |
| `ref_platformer` | FAIL (caught) | FAIL |
| `ref_tetris3d` | PASS (never caught) | PASS |

With the player dead there is nobody left to earn points, so with nothing pressed the
score has nothing to move it. **Do not "simplify" `probe.end_condition_holds` back to
an idle-only check** — that is the shape this table exists to refuse.

**What shipped: `probe.end_condition_holds`, one copy for all 4 bots**, reached
through `Bot.end_condition`. It idles, then presses, and reads the pressed phase
THROUGH the reset — the prompt's "until it is reset" contemplates a reset existing and
`g1_pong__rust` binds it to a control. Every tick of BOTH phases is read, never the
endpoints, and the first tick that broke goes in the evidence with why.

**The guarded value is the caller's and must be one the simulation MOVES.** This is the
part that will look arbitrary and is not:

- `_death` guards `(score, kills)` — the score cannot move because the player is dead.
  Measured `(0, 3) -> (0, 4)` on the mutant against `(0, 3) -> (0, 3)` on the reference.
- `_gameover_check` guards `(score, filled cells)`, summed out of the **contracted**
  `heights` grid. The score cannot move because a full well clears no layer. Measured
  `(0, 62) -> (0, 84)`. **Do not switch this to `settled`** — it carries the same number
  and is NOT in the contract `state.shape` checks, so a submission may omit it and the
  guard would read 0 on every tick, which is a check that cannot fail. **Do not print
  the `heights` grid** either: it is ~250 characters twice and `Criterion.evidence` is
  stored truncated at 600, which cut the pressed-phase verdict off the audit trail.
- `_hurt` and `_match_ends` guard the score alone, and that is measured too: the
  platformer corpse can still swing at an enemy (`score 0 -> 200`) and a pong that
  keeps playing moves the ball.

**Tetris presses on alternate ticks.** `hard_drop` is `_edge`-driven, so a set held flat
for the whole window drops once and a game that kept playing would have nothing left to
move. `inputs` takes a callable of the press-tick index for exactly this.

**The tetris variant's card is 190 ticks and the length is load-bearing.** At the 96 the
real submission shipped, the fixture PASSES the unrepaired bot — the run restarted at
tick 96 and stacked out again inside the same 200-tick window, and the restart's own
score reset satisfied the frozen test. Measured both ways. 190 is the length at which
the restarted run has too few ticks left to lose again, so the row reports the bot
rather than the arithmetic. Shortening it back to 96 for provenance would leave a
variant that is green on the defect it exists to catch.

## Registry, before and after

`36 criteria pinned, 4 variants, 6 pending` -> `40 criteria pinned, 8 variants, 4
pending, 3 session-lock controls, 70 hazards, 0 expectation(s) unmet`, exit 0.

- 2 pendings promoted into `VARIANTS` (`ref_arena`, `ref_platformer`).
- 2 variants added: `ref_tetris3d` at 190 ticks, and `ref_pong` — `match.ends` had a
  mutant and no variant on the very fixture the repair was paid for.
- 4 mutants added: the keeps-stepping shape on all 3 loss games, plus `MATCH_PLAYS_ON`,
  **the first mutant `match.ends` has ever had of its own** (it was collateral only).
  `ref_arena/gameover.triggers` had no mutant at all before this.

**The control in the red direction:** the shipped registry against the 4 bots at `main`
is exit 1 on 4 rows — the 3 restart variants, plus the tetris keeps-stepping mutant
surviving.

## tier2_census, before and after

`python3 eval/judge/tier2_census.py --runs-root <main checkout>/eval/runs`, run at both
states: **byte-identical**, `diff` clean. Expected — no stored record was rewritten and
re-grading a play-bot criterion needs a live probe. Both: `n_trials 69`, `verdict
SATURATED`, `groups 11`, `saturated 5`, `selective_failures 10`.

Blast radius, from the same run: `match.ends` 25 scored / 0 failed; `gameover.triggers`
19/2 on g2, 16/4 on g3, 8/0 on g4. **All 6 stored failures are Unity probe-unusable
sessions** (`probe exited (code 134) while waiting for the tick-0 header`), so no stored
FALSE can turn TRUE. The 62 stored PASSes are where a re-grade could move.

## Filed, and needing the orchestrator

- **`tasks/166`** — the arena and tetris bots LOCATE the end from the state flag **or** a
  `game_over` event and then SCORE it from the flag alone, so an event-only submission
  is found ended and scored not-ended. Pre-existing: `main` reads the same. Settling it
  decides what the criterion measures for every g2/g3/g4 submission.
- **`tasks/167`** — a `DECISIONS.md` sentence about `scene_mutants.py` that arrived via a
  merge of `main`, not from this work.
- **A FINDING NUMBER IS OWED** for the fail-open measurement in the first table: an
  end-condition check that only idles cannot see a game that ends and keeps playing,
  because the value it guards is one only a live player moves. `bot_mutants.py` carries
  the mutants that reproduce it on all 3 fixtures.

## Two pre-existing defects repaired in passing

- The `end_condition` `#:` comment in `bot_arena.py`, `bot_platformer.py` and
  `bot_tetris3d.py` said something **false about pong** — a per-game clause had been
  appended to a sentence whose subject is pong, so arena read *"`match.ends` in pong,
  where the player's health reaches zero"*.
- `RUBRIC.md` said *"All 17 non-determinism criteria are pinned by a mutant"* for the
  platformer. Measured at `main`'s registry: **16 of 20**. The figure was one high
  before this branch.

## Review

5 rounds, the ceiling. 11 findings: 9 acted on, 2 declined with evidence (the
platformer companion value — the reviewer accepted and resolved it; and README's
findings count, where the cited producer says 167 with 0 gaps against the reviewer's
143). Round 5 found a real hole in round 4's own work — a reset excusing a pressed tick
before it — so the last commit is a one-line guard that has not itself been reviewed.
