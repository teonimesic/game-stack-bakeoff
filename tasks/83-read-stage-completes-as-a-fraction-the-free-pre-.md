---
id: 83
title: Read stage.completes as a fraction - the free pre-test that decides whether a harder task is worth buying
status: done
priority: 2
refs: DECISIONS.md decision 'A harder task is PRICED here, and gated behind a free pre-test', task 76, eval/judge/bot_platformer.py, eval/judge/RUBRIC.md g4 section, eval/runs/wg-g4c-2026-08-21T02-26-46
done_when: 'the eight surviving wg-g4c work trees are re-driven by a bot that crosses gaps (task 76 closed and bot_mutants.py green in both halves), stage.completes is recorded per submission as fraction-of-goal, and the result is stated as ONE of three named outcomes: SPREAD, in which case promote stage.completes to scored with a mutant and a variant and retire the harder-task decision in DECISIONS.md; ALL EIGHT AT 1.000, in which case a harder task is justified and this task reports by how much the bar must move; or FLAT AT A LOW FRACTION, in which case the bot is still the constraint and no task change is warranted. Eight numbers without a verdict on which of the three it is does not close this, and neither does a verdict without the eight numbers.'
established_by: 'Eight fractions measured on the surviving wg-g4c work trees with a repaired traversal loop: 0.274 to 0.803, against 0.143 to 0.290 as shipped, stage.completes False on all eight in both. Verdict SPREAD but not discriminating - Spearman rho 0.405 between the shipped and repaired bots'' rankings, exact permutation p 0.163, and 8 of 8 end having taken exactly hp0 hits with no victory, so the scalar is health pool times distance per hit over goal_x. Harder task not justified, criterion not promoted. Dominant bot defect was the length of the jump key press: one tick reaches 29.0-88.4 units, holding reaches 93.5-141.8, widest gap in any of the eight levels 110. Controls: stage.completes True on ref_platformer under both bots; re-driving all eight moves 0 scored verdicts, run twice against main''s bot and this branch''s; bot_mutants.py 36 criteria pinned both directions, 4 variants, 3 session-lock controls, 0 unmet, exit 0. Branch task-83-stage-completes-fraction; finding filed as task 101.'
---

Task 74 priced a harder task at 421 dollars for one clean 8-cell field and 698.21 all-in at the only precedent, and found that the money is only worth spending if a GRADED criterion can discriminate at all - which nothing in the corpus has ever shown. stage.completes is the only tier-2 criterion not at the ceiling (0 of 8 on wg-g4c) and the only g4 requirement stated as a goal with a direction. Its stored evidence already yields eight distinct fractions, 14.3 to 29.0 percent of the way to the goal, and that spread is an artifact: the bot walks right until it falls in a hole, so the scalar ranks the field on where each submission put its first pit. This task is that same reading taken again once the bot can actually pursue the goal. It costs no trials - the eight wg-g4c work trees survive under the work root. BLOCKED ON 76: doing it before the bot crosses a gap reproduces the artifact.

## Done 2026-08-23. The verdict, the eight numbers, and what must not be re-derived

**VERDICT: the numbers are SPREAD; the consequence the done-when attaches to SPREAD does not
follow; the operative decision is the third branch's - the bot is still the constraint, no task
change is warranted, and `stage.completes` is NOT promoted.** Stated that way deliberately: the
trichotomy assumed *spread implies the tier can discriminate*, and that inference is exactly what
the measurement broke. `DECISIONS.md` and `eval/judge/RUBRIC.md` now carry it.

### The eight numbers, fraction of `goal_x` reached

| submission | as shipped | repaired | goal_x | hp0 |
|---|---|---|---|---|
| `g4_platformer__godot__t0` | 0.225 | **0.803** | 2300 | 4 |
| `g4_platformer__godot__t1` | 0.143 | **0.591** | 3500 | 5 |
| `g4_platformer__rust__t0`  | 0.206 | **0.417** | 3100 | 4 |
| `g4_platformer__rust__t1`  | 0.290 | **0.609** | 2300 | 4 |
| `g4_platformer__ts__t0`    | 0.256 | **0.686** | 2300 | 5 |
| `g4_platformer__ts__t1`    | 0.178 | **0.274** | 2320 | 5 |
| `g4_platformer__unity__t0` | 0.158 | **0.617** | 2320 | 5 |
| `g4_platformer__unity__t1` | 0.203 | **0.401** | 2920 | 5 |

`stage.completes` is `False` on all eight in both columns. The "as shipped" column reproduces the
stored `playbot.json` evidence byte for byte - that is what proved the extraction before any of
this was believed.

### Why the spread does not license promotion - the two measurements that decide it

1. **Improving the instrument reorders the field.** Spearman rho between the shipped bot's ranking
   of the eight and the repaired bot's is **0.405**, exact permutation p = 0.163 over all 8!
   orderings. `godot t0` 6th -> 8th, `unity t0` 2nd -> 6th, `godot t1` 1st -> 4th.
2. **8 of 8 end having taken exactly `hp0` hits, with no victory.** Run length is set by the health
   bar, so the scalar is `(health pool x distance per hit taken) / goal_x`: two free design
   parameters over a third. The axis is directed; the quantity that ENDS the run is not.

### What the bot was doing, and the four repairs - do not re-derive any of this

`_stage` was the **fourth** inline copy of "walk right" and the one task 76's unification did not
reach. Each step measured on all eight:

| bot | range over the eight | what it added |
|---|---|---|
| as shipped | 0.143 - 0.290 | `move_right` every tick, jump only after 12 stalled ticks, never attacks |
| + `_walk_toward` | 0.143 - 0.327 | one-tick edge jump |
| + swing while closing | 0.143 - 0.509 | attacks, but walks INTO the enemy and bleeds out |
| + stand off at 26 to swing | 0.143 - 0.510 | `_combat`'s own reach |
| **+ hold jump while rising** | **0.274 - 0.803** | the rest of the jump arc |

**The dominant defect was the LENGTH OF THE KEY PRESS.** `_walk_toward` sets `jump` only when
`grounded is True`, so it fires for exactly one tick, and all eight submissions implement a
variable-height jump. Measured per submission by sweeping the hold: a one-tick press reaches
**29.0 to 88.4** units, holding reaches **93.5 to 141.8**, and the widest gap in any of the eight
levels is **110**. **No level was ever uncrossable.** Filed as task 101.

Terminal cause as shipped: all 8 ended `game_over` at negative y, having spent the whole health bar
falling into the SAME pit repeatedly - so the stored 14.3-29.0% did rank the field on where each
submission put its first pit, exactly as `DECISIONS.md` suspected. Now measured, not suspected.

### Controls, both directions

- **Positive:** `stage.completes` returns True on `ref_platformer` under the broken bot AND the
  repaired one (`victory=True`, x=2302.1 and x=2301.2 of a goal at 2300). The criterion is not
  structurally incapable of passing - **and the reference could therefore never have detected any
  of this**, which `eval/G4-PLATFORMER.md` predicted in writing when the criterion was designed.
- **Negative / regression:** re-driving all eight work trees with the full bot moves **0** scored
  verdicts. Run twice, once with main's bot and once with this branch's; the two arms are
  identical - one diff each, `unity__t0`'s `knockback.applied` False -> True, which is task 76's
  already-merged repair and is unscored under #89. `_stage` is `diagnostic_only` and
  `_walk_toward` was not touched.
- `judge/bot_mutants.py`: **36 criteria pinned in both directions, 4 variants, 3 session-lock
  controls, 0 expectations unmet, exit 0.** Two mutants now also flip `stage.completes` as
  collateral, which they did not before - the repaired loop depends on mechanisms it used to die
  before reaching.

### Not done, deliberately

- **No finding number taken** - ten tasks were in flight and several allocate numbers. Filed as
  **task 101** with the numbers, so nothing needs re-measuring.
- **Seed sensitivity not measured.** `_stage` hardcodes `seed=7`, as do `_combat`, `_hurt` and
  `_bounded`; changing that is a separate question and would touch scored paths.
- **`_stage` still does not backtrack, drop to a lower ledge, or route around an enemy it cannot
  kill.** It dies of attrition on 8 of 8. That is the remaining gap between this and a bot whose
  fraction is about the level, and it is what would re-open the harder-task question.
