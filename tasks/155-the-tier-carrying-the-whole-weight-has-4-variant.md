---
id: 155
title: The tier carrying the whole weight has 4 variant games for 36 criteria; the newest tier has 8 for 15
status: in_testing
priority: 2
refs: 'eval/judge/bot_mutants.py, eval/judge/scene_mutants.py, AGENTS.md rule 15, #46'
done_when: 'A per-criterion answer to ''what correct-but-unusual game would mis-score this'', recorded for all 36; the 4 existing variants checked against the shapes #46 names, with any uncovered shape either added as a variant or recorded as deliberately out of scope with the reason; and bot_mutants.py still exits 0 with every criterion pinned in both directions. Concluding that 4 is sufficient, with the per-criterion reasoning, is a complete answer and closes this.'
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/38
established_by: '6 reproducible false negatives found and shipped as declared Pending subjects; HAZARDS records one answer for each of the 70 criterion instances; bot_mutants.py exit 0 at 229.4s, --selftest 13 checks each red under its own mutation; PR #38 gates+controls+CodeRabbit all pass at 18abc7a'
---

The play-bot tier carries **the whole weight** of a submission's score — tier 1 is a gate, tier 3 is
0.00. Its correctness rests on `judge/bot_mutants.py`, which runs both halves the rules require:
mutants (can a criterion fail?) and variants (can it still pass on a **correct** game the reference
does not resemble?).

Measured 2026-08-25:

| suite | criteria | variant subjects |
|---|---|---|
| `bot_mutants.py` — tier 2, weight **1.00** | 36 | **4** |
| `scene_mutants.py` — scene probe, built 2026-08-24 | 15 | **8** |

Every criterion is exercised by every variant, so this is not *"32 criteria have no variant"*.
The honest statement is: **each play-bot criterion has been tested against 4 correct-but-different
games; each scene criterion against 8.**

## Why this is a question and not yet a defect

`AGENTS.md` rule 15 says every false negative ever adjudicated in this project has been of the
variant kind, and #46 is **sixteen in one sweep**, then three more under a harder task, then two
more. So the variant is the half that has historically found things, and the tier carrying all the
weight has the thinner coverage of it.

**That may still be enough.** Four variants chosen well can beat eight chosen badly, and the four
here are pointed at real failure shapes — a title card that holds the ball for 104 ticks, enemies
faster than the player, an `active` span wider than the hitbox, an opening ledge over a pit. This
ticket asks whether the number is right, not whether the existing ones are good.

**The asymmetry has a cause worth naming**: the scene probe's ticket carried the mutant/variant
rule explicitly, and the play-bot suite predates that being written into a brief. The discipline
was applied to new work and never retrofitted.

## What would answer it

1. **What correct-but-unusual game would each criterion mis-score?** Ask it per criterion rather
   than per suite. A criterion nobody can construct a failing input for is either robust or
   under-imagined, and saying which is the work.
2. **Do the 4 existing variants cover the shapes #46 actually found?** That finding names sixteen
   adjudicated false negatives; if the variants do not exercise those shapes, the gap is concrete.
3. Add variants where a shape is missing. **Finding that the 4 are sufficient, with the reasoning
   per criterion, closes this ticket** — a null here is a real answer and is cheaper than adding
   variants nobody derived from a failure mode.

## What NOT to do

Do not add variants to match a ratio. A variant exists to encode a specific way a correct game can
differ from the reference; one written to raise a count tests nothing and costs 226s of CI.

Do not touch the 36 criteria themselves. This ticket is about coverage of the checks, not about
what they check — changing a criterion moves stored verdicts and is a different ticket with a
re-scoring census.

## note 2026-08-25

## Answered 2026-08-25: no, 4 is not sufficient — and the population in this ticket is wrong twice

**The ticket's premise.** A variant runs the whole bot on **one fixture**, so `Every criterion is
exercised by every variant` is true only within a fixture. The 4 variants land 1 on `ref_pong`,
**0** on `ref_tetris3d`, 1 on `ref_arena`, 2 on `ref_platformer`. And the scored population is the
**70** criterion instances the four bots report, not the 36 that carry a mutant — 2 of the 6 false
negatives below are on criteria with **no mutant at all**, so a registry scoped to the 36 would
have missed a third of the answer.

**6 reproducible false negatives**, each shipped as a `Pending` subject in `bot_mutants.py` that
asserts its exact failing set every run. Repairs are `tasks/157`, `tasks/158`, `tasks/159`,
`tasks/160` — not done here, because every one is a criterion change and therefore a re-scoring
event over 68 graded submissions.

| fixture / criterion | subject | measured |
|---|---|---|
| `ref_arena/gameover.triggers` | a game-over card, then a control restarts | `after 300 more ticks of input: game_over=False, alive=True` |
| `ref_platformer/gameover.triggers` | the same | `after 200 more ticks of input: game_over=False, alive=True` |
| `ref_tetris3d/piece.falls` | a 96-tick card over a frozen well | `lowest cell height went from 11 to 11 without input` |
| `ref_tetris3d/piece.spawns` +3 | a 96-tick card over an empty well | `first piece has 0 cells: []` |
| `ref_arena/fire.rate_limited` | a 3-round spread weapon | `90 bullets from 120 ticks of held fire (30 fire events)` |
| `ref_pong/rally.counts` | the counter settles one tick late | reads `rally` only on the `paddle_hit` tick |

**Things a later agent should not re-derive.**

- The end-condition repair already exists and was never carried across. `bot_pong._match_ends`
  presses **nothing** for 600 ticks after the win, for the Rust submission with
  `GAME_OVER_LOCKOUT_TICKS = 96`. The `g3` and `g4` prompts carry the identical *"stops accepting
  play until it is reset"* sentence.
- On `ref_tetris3d` that same card **passes**, and the pass is not evidence: the game restarted
  and stacked out again inside the window, and the score reset to 0 satisfied `frozen`. At a
  190-tick card the verdict flips to `False`. **Do not raise the card to manufacture the red** —
  96 is the platformer reference's own `OPENING_TICKS`, and tuning the fixture to get the answer
  is what task 76 recorded.
- The tetris opening boundary is exact: an **18**-tick card passes, **21** fails. `_await_piece`'s
  limit is 20. There are **two** independent budgets — that await, and `piece.falls`' 120-tick
  descent loop — which is why there are two tetris pending subjects. A repair to one leaves the
  other red, on purpose.
- **Measured green, so do not go looking again:** a 40-tick get-ready beat with the ball at the
  centre (`serve.resets` tests `|x| < 60`, and a held ball is at the centre); 6-tick coyote time
  on the platformer; a 30-tick beat between *later* tetris pieces (those get `_await_piece`'s
  limit of 60).
- **Blast radius of the `gameover.triggers` repair, measured:** all **6** stored
  `gameover.triggers` failures in `eval/runs` are probe-unusable session failures (a second Unity
  instance, a Rust compile error). None is this shape, so no stored `FALSE` becomes `TRUE`. A
  stored `PASS` can still move, which is why each ticket keeps its `tier2_census.py` census.
- **The line that decides whether presentation is this suite's problem: whether it gates the
  SIMULATION.** A title card and a game-over card stop the sim stepping, so the play-bot sees
  them. A paddle bob, a screen shake and a score counting up on screen live in the view layer,
  which the prompt puts in a different module and the probe never reads. That is why
  `paddle.bounded`'s idle-bob hazard is declined rather than pending.
- 3 rows are recorded **`OPEN`, not constructed**, with the reason: end-of-wave score banking
  (`ref_arena/score.on_kill`), a multiplier that drops one tick late (`ref_arena/multiplier.falls`
  — the same shape as `tasks/159`, settle them together), and an animation slower than a 40-tick
  walk (`ref_platformer/anim.frames_advance`).

**Where the answer lives, and it is a producer rather than this note.**
`python3 eval/judge/bot_mutants.py --hazards` prints all 70 entries grouped by the failure shape
each belongs to; `--selftest` is the offline both-directions pin on the registry gate and the
pending adjudication (13 checks). Of the 11 shapes, 6 carry a variant or pending subject and the
rest are answered by machinery a variant cannot be — `lock_controls` for the session family, the
reference itself for `late-unlock` since #46 — or are `no-construction`.

**Suite cost:** 229.4s, exit 0. The 6 pending subjects are ~7.3s of that.

**A finding is owed a number.** 6 false negatives in the tier carrying weight 1.00; 3 of them in
the game that had no variant subject at all; and one criterion (`fire.rate_limited`) whose
evidence string prints the correct number beside a verdict computed from the wrong one. No number
was allocated on the branch — that is `main`'s at merge.
