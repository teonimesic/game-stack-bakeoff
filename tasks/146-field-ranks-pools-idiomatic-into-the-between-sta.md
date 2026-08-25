---
id: 146
title: field_ranks pools idiomatic into the between-stack figure that JUDGING.md says it is barred from
status: in_testing
priority: 2
refs: 'eval/judge/field_ranks.py, eval/judge/JUDGING.md, eval/judge/RUBRIC.md, eval/judge/aspects.py, tasks/135, #53'
done_when: Either (a) the pooled figure excludes cross-stack-barred aspects, assert_poolable refuses them the way it refuses a control, every live document quoting a pooled figure is recomputed and restated with the new value, and the change is recorded in eval/RUNS.md as a comparability note; or (b) the pooling is deliberately kept, and the reason is written in DECISIONS.md with the recomputed leave-one-out figure showing what excluding idiomatic would have changed. Either way the figure is produced by running field_ranks.py, not quoted from memory, and the answer is not left as a difference between what the code does and what two live documents say.
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/24
established_by: 'Option (a) taken. field_ranks.classify returns BARRED from Aspect.cross_stack_bar, assert_poolable refuses it like a control. Broken state established first with the pre-change tool from git show HEAD: 3 of 9 stored directories pooled idiomatic ALONE and printed a full separation table at exit 0, capped reading rank/pool 5.2500 against 1.7500. Selftest checks 15-18 written first, red at 7 unmet exit 1, green at 0 unmet after. All 44 gates.yml gates unpiped 0 red. PR #24, 4 review rounds ending clean. Needs a finding number at merge.'
---

JUDGING.md and RUBRIC.md have recorded idiomatic as cross-stack barred since #53 - 'per-stack-only, a result rather than a defect to engineer away'. field_ranks.classify() calls it SCORED, so every pooled between-stack figure this project publishes includes it. Task 135 made the bar readable by code (Aspect.cross_stack_bar) and made field_ranks PRINT it with the aspect's per-stack means, but deliberately did not change what is pooled: JUDGING.md's per-aspect table states that field_ranks --per-aspect reproduces all ten of its numbers, and dropping idiomatic from the pool re-analyses published game results. That is a decision with evidence behind it, not a side effect of adding scene aspects.

## note 2026-08-24

## note 2026-08-24 (orchestrator) — it reaches README, and the direction is probably harmless and unmeasured

Checked before leaving this at p2, because "does it touch a published number" is the question that
decides urgency.

**It reaches the front door.** `README.md`'s result row *"the LLM judge is not a fifth route — no
subjective aspect separates the stacks either"* names `field_ranks.py --rounds` as its producer.
That is a between-stack claim computed over a pool that includes `idiomatic`, which
`JUDGING.md` and `RUBRIC.md` have barred from between-stack use since #53.

**Two things hold it below p1, and neither is a reason to skip it:**

1. **The published claim is a NULL.** *No* aspect separates the stacks. Removing an aspect from a
   pool that separates nothing is unlikely to make it start separating something — but *unlikely*
   is not a measurement, and this project's standard is that a number is produced, not reasoned
   about.
2. **Tier 3 is weight 0.00 and contributes nothing to any score**, and the same README row already
   records that the blinding failed and all 84 stored packs carried text naming the stack. So the
   claim is heavily caveated before this defect is applied to it.

**What settles it is one number: the leave-one-out figure.** Recompute the pooled result with
`idiomatic` excluded and compare. Both outcomes are publishable and both close this ticket —
`(a)` the null survives, in which case the bar can be honoured at no cost to any published claim,
or `(b)` it does not, which is a considerably more interesting finding and a correction to
`README.md`.

**Do not let the null tempt you into skipping the recomputation.** "It would not have changed
anything" is exactly the claim that needs the number, and a mechanism that runs, agrees with what
was already believed, and measures nothing is the shape this project keeps paying for.

## note 2026-08-24

## Done — option (a). PR #24, branch `task-146-barred-aspects-not-pooled`

**Taken (a): the bar now decides what is pooled.** `field_ranks.classify()` returns a fourth
value, `BARRED`, read from `Aspect.cross_stack_bar` exactly as `CONTROL` is read from
`control_for`. `assert_poolable` refuses it, `report` names it under `NOT POOLED` with the
reason, and the aspect's own per-aspect pair and per-stack means are still printed — barring is a
refusal to rank across stacks, not a refusal to measure.

**The reason (a) rather than (b): a pooled figure IS a between-stack range.** Pooling a barred
aspect is not a different quantity that happens to include it; it is the barred reading with
extra steps. The leave-one-out figure `(b)` asks for was computed anyway, because it is what
decides whether honouring the bar costs a published claim. It does not.

### The measurement the next agent must not re-derive

Before/after over the whole stored tree, pre-change tool taken from `git show HEAD:` rather than
from memory. **9 directories produced a pooled figure.**

| directory | before | after |
|---|---|---|
| `wg-tetris-judge-2026-08-17/pre` | 5 aspects, 10 rounds, `rank`/`pool` 1.9000 / 2.2750 | 4 aspects, 8 rounds, **1.3125 / 2.5625** |
| `wg-tetris-judge-2026-08-17/post` | 5 aspects, 10 rounds, `rank`/`pool` 2.1000 / 1.9250 | 4 aspects, 8 rounds, **1.8750 / 2.0938** |
| `wg-aspect-reliability` | 5 aspects, 25 rounds, `score`/`pool` 0.4000 / 0.2400 | 4 aspects, 20 rounds, **0.5250 / 0.4000** |
| `wg-funframes-crossgame/arena` | 3 aspects, 8 rounds | 2 aspects, 4 rounds |
| `wg-funframes-crossgame/platformer` | 5 aspects, 10 rounds | 4 aspects, 8 rounds |
| `wg-g4c-.../judge-blind-2026-08-23` | 2 aspects, 4 rounds | 1 aspect, 2 rounds |
| `wg-funframes-crossgame/pong` | **`idiomatic` alone** | **UNMEASURABLE**, exit 1 |
| `wg-g4c-capgate/out/capped` | **`idiomatic` alone**, `rank`/`pool` 5.2500 / 1.7500 | **UNMEASURABLE**, exit 1 |
| `wg-g4c-capgate/out/uncapped` | **`idiomatic` alone** | **UNMEASURABLE**, exit 1 |

Exact eight-reading table on `wg-tetris-judge-2026-08-17`, after (all over the 4 poolable
aspects), with the direction change from before:

| field | value/order | between | within | before | after |
|---|---|---|---|---|---|
| pre | score/pool | 0.3750 | 0.8125 | no sep | no sep |
| pre | score/perround | 1.0000 | 0.8750 | exceeds | exceeds |
| pre | rank/pool | 1.3125 | 2.5625 | no sep | no sep |
| pre | rank/perround | 2.7500 | 3.1875 | **exceeds** | **no sep** |
| post | score/pool | 0.7500 | 0.7500 | **exceeds** | **no sep** (exactly equal, 3/4 vs 3/4) |
| post | score/perround | 0.8750 | 0.9375 | no sep | no sep |
| post | rank/pool | 1.8750 | 2.0938 | **exceeds** | **no sep** |
| post | rank/perround | 3.0000 | 3.5312 | no sep | no sep |

Max excess of between over within across the 8: **+22.6% → +14.3%**. Between strictly smaller on
**4 of 8 → 6 of 8**, equal on 1, larger on 1.

### The finding, and it needs a number allocated at merge

**3 of the 9 stored directories that produced a pooled separation figure held nothing but the
barred aspect, and printed a full four-row separation table at exit 0.** `pong`, and both arms of
`wg-g4c-capgate/out`. The loudest, `capped`, read `rank`/`pool` **5.2500 against 1.7500** — the
widest between-over-within `field_ranks` ever returned anywhere in the stored tree, and it was a
pure ranking of the one aspect that may not be ranked across stacks.

**The shape worth recording is why nothing could see it.** `JUDGING.md` and `RUBRIC.md` had
stated the bar since #53; `Aspect.cross_stack_bar` had declared it to code since task 135;
`field_ranks.report` printed it beside the figure. A live document stating *this aspect may not
be ranked across stacks*, beside a number that ranked it across stacks, is a disagreement **no
consistency check can find**, because the two statements are about different things — the
document is about the aspect and the number is about a pool. It took a person reading both.

### Pinned in both directions

- Checks 15-18 were written and run **against the unchanged tool first**: 7 unmet, exit 1.
  After: 0 unmet, exit 0.
- Check 16: pooling the barred aspect moves `between` 2.0000 → 2.3333, so the exclusion acts.
- Check 17: clearing `cross_stack_bar` on the live `ASPECTS` makes the guard **stop** firing —
  the verdict is read from `aspects.py`, not from a constant in `field_ranks`.
- Check 18 is the **variant**: a barred-only directory exits 1 *and still prints the per-stack
  means the bar permits*. That is why `report` no longer returns early when nothing is poolable.
- `docstat.py --withdrawn` red on `eval/RUNS.md` for the two new register entries, green once
  the ids were cited in the same block.
- All 44 `gates.yml` gates unpiped, 0 red, at every review round.

### Three traps for whoever touches this next

1. **`_A_SCORED` was defined as `not ASPECTS[i].control_for`** and therefore held both barred
   ids while the guard excluding them was being written. It is now derived through `classify`.
   **A fixture that re-spells the predicate of the function it tests agrees with every bug that
   function has.**
2. **`report` returning early when nothing is poolable was hiding a second defect.** Removing it
   exposed `--per-aspect` printing numbers for an aspect id `aspects.py` does not define —
   `assert_poolable`'s lone-aspect exemption is on cardinality, and a lone unknown is one aspect.
   The exemption rests on knowing *what* the aspect is, so `UNKNOWN` is now rejected before the
   cardinality return. Found by review, not by me.
3. **The barred aspect must never get a row in an ordering table, however labelled.** I gave it
   one in `JUDGING.md` — stacks sorted by its mean rank behind a warning — in the same commit
   that stopped the tool doing exactly that. `_by_stack` prints alphabetically for this reason.
   A warning beside a ranking is still a ranking.

### Docs

`eval/judge/JUDGING.md`, `eval/judge/RUBRIC.md`, `eval/judge/AGENTS.md`, `eval/judge/aspects.py`,
`eval/SCENES.md`, `DECISIONS.md`, a TWENTIETH comparability note in `eval/RUNS.md`, and
`WR-tier3-pool-pre` / `WR-tier3-pool-post` in `eval/withdrawn.json`. **`README.md` untouched** —
its tier-3 row states a null and quotes no figure, and the null got stronger.

Two defects fixed in passing: `JUDGING.md`'s ordering-instability table **named no method and
reproduced under none** (the #113 failure, in the section warning against it), and `RUBRIC.md`
carried a task-90 pooled pair the producer no longer prints.

### Review

4 rounds, ended clean — *"No actionable comments were generated in the recent review"* over
`8638971..3e1fa91`. 2 declined with measurements in the threads: reference-style finding links
(`linkcheck.LIVE_DOCS` is 4 paths, neither file among them; only `README.md` carries link
definitions, 20 against 0), and updating `README.md`'s grading table (`evaluate.WEIGHTS` is
`{"playbot": 1.0}` with no tier-3 entry, and no module imports `field_ranks` — all 12 mentions
across `eval/` are comments, so a re-grade would be byte-identical).
