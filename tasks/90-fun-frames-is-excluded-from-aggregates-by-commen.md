---
id: 90
title: fun_frames is excluded from aggregates by comment only - nothing enforces it
status: done
priority: 3
refs: eval/judge/aspects.py, eval/judge/field_ranks.py, eval/judge/RUBRIC.md
done_when: 'either FUN_FRAMES sets diagnostic_only and every aggregate over aspects reads it, or the guard is removed from the comment and replaced with what actually holds. Whichever way, pinned in both directions: a mutant that pools the control must go red, and a variant that pools five scored aspects with one of them missing must stay green. field_ranks.py must state, in its output, which aspects a pooled figure is over'
established_by: 'Aspect.diagnostic_only was renamed to Aspect.control_for and set to fun on FUN_FRAMES; field_ranks.assert_poolable now raises on any population mixing a control with another aspect, and field_ranks.report names the aspects each pooled figure is over plus every round excluded. Broken state established FIRST: python3 eval/judge/field_ranks.py --rounds runs/wg-aspect-reliability pooled 30 rounds of which 5 were fun_frames, printing score/pool 0.3667/0.2417 with no indication a control was in it; after the repair 25 rounds over 5 scored aspects give 0.4000/0.2400, and the between-exceeds-within verdict is unchanged on all four value/order readings, so the pollution moved the figures and not the conclusion. Same on the other two mixed directories wg-funframes-crossgame/arena (8 of 10 pooled) and /platformer (10 of 12). NO PUBLISHED NUMBER MOVED, verified rather than assumed: wg-tetris-judge-2026-08-17/post reproduces rank/pool 2.1000/1.9250 and /pre 1.9000/2.2750 against README 2.10/1.93 and 1.90/2.27, both reporting POOLED over 5 scored aspects with nothing excluded, and a grep of every live doc for the polluted figures returned nothing. The rename is half the repair: the old name collided with an unrelated field on probe.py and the three play bots holding criterion ids, so a grep for the guard returned twenty hits all belonging to the other mechanism. field_ranks is the ONLY aggregate over aspects that pools scores, established by reading every module mentioning aspect; field_sweep keys per game:aspect, adjudicate and field only read sees, judge_ledger aggregates COST where control rounds must stay in and now says so in its docstring. PINNED IN BOTH DIRECTIONS: field_ranks --selftest check 7 goes red with a legible message when no aspect sets control_for - run against the pre-task tree it exited 1 naming the defect, and the first draft IndexErrored there instead which is why existence is checked before anything is built on it; check 11 patches ASPECTS to reclassify the control as scored and requires the guard to STOP firing, proving the verdict is read from aspects.py; check 10 requires pooling the control to move between from 2.0000 to 2.3333 so the exclusion is not decorative; check 12 is the variant, a field holding four of the five scored aspects stays green and pools exactly those four; check 13 pins an unknown aspect id as unmeasurable rather than scored, exit 1 on a directory with nothing poolable. Separately report was edited to pool SCORED+CONTROL+UNKNOWN and the selftest went red at check 9, so report cannot be made to pool the control without also disabling the guard in figures. aspects_selftest.py gains a fourth check with a mutant reconstructing the exact task-90 state and a variant where control_for names an aspect that does not exist; every other check in that file stays green on the mutant, which is why the defect survived in a comment. Gates all exit 0 unpiped: aspects_selftest, field_ranks --selftest, judge_ledger --selftest, docstat --sweep, docstat --selftest, tasks check 93 well-formed. Docs updated in session: RUBRIC.md, JUDGING.md, DECISIONS.md now state the population as a third parameter of the separation figure. NOT DONE deliberately: no finding number allocated, six peer worktrees active and eleven collisions on 2026-08-23; the measurement is in the ticket. Branch task-90-control-aspect-not-pooled, commit 49aeed6.'
---

aspects.py says FUN_FRAMES is a control that must never be pooled with the other five and that it is diagnostic_only so no aggregate can absorb it by accident. Aspect.diagnostic_only is defined at aspects.py:41, is NOT set on FUN_FRAMES (measured: frozenset() empty), and is read by no code anywhere - the only readers of that name are probe.py and the play bots, a different mechanism with the same field name. field_ranks.py without --per-aspect pools every round in the directory it is given regardless of aspect: measured on runs/wg-aspect-reliability it pools 30 rounds of which 5 are fun_frames, and reports between exceeds within on all four value/order readings. Three stored directories mix the control with scored aspects - wg-aspect-reliability, wg-funframes-crossgame/arena, wg-funframes-crossgame/platformer. NO PUBLISHED NUMBER IS AFFECTED: the separation figure README and DECISIONS quote comes from wg-tetris-judge-2026-08-17/pre and /post, which hold no fun_frames rounds - the control lives in sibling directories funframes, repeats and repeats7.

## What was done (2026-08-23), and what not to re-derive

**The field was renamed, and the rename is half the repair.** `Aspect.diagnostic_only` is now
`Aspect.control_for: str` - the id of the aspect this one controls, `""` for a scored opinion -
and `FUN_FRAMES` sets `control_for="fun"`. The old name collided with an unrelated field on
`probe.py` and the three play bots holding CRITERION IDS, which is why a `grep diagnostic_only`
returned twenty hits that all belonged to the other mechanism and why the false claim survived.
Keeping the name would have left that collision in place. `aspects.py` also exports
`SCORED_ASPECTS`, `CONTROL_ASPECTS` and `is_control()`, all derived from `ASPECTS`, never listed.

**`field_ranks.py` is the only aggregate over aspects that pools SCORES.** Established by
reading every module that mentions `aspect`: `field_sweep.py` keys its summary `game:aspect`
and its own comment already forbids pooling across aspects; `adjudicate.py` and `field.py` only
look up `sees`/`blind_language`; `judge_ledger.py` aggregates COST, where a control's rounds
must stay in - the money left the account - and it already refuses to print a per-call mean.
A note saying so is now in `judge_ledger.load_rounds`, so the exclusion is not copied there.

**The guard is `field_ranks.assert_poolable`, called from `figures()`, not from `report()`.**
Two legitimate shapes: one aspect (per-aspect, a control alone is fine), or many aspects all
scored. Anything else raises. It is in `figures()` because the resource is "a pooled figure" and
a guard beside one caller is a guard the next caller does not have. An aspect id `aspects.py`
does not define is UNKNOWN, is excluded and named, and is not assumed scored; a directory with
nothing poolable prints `UNMEASURABLE` and exits 1.

**Numbers, measured both ways on `runs/wg-aspect-reliability` (30 rounds, 5 of them the control):**

| reading | control pooled in (30 rounds) | scored aspects only (25) |
|---|---|---|
| score/pool | 0.3667 / 0.2417 | 0.4000 / 0.2400 |
| score/perround | 1.0833 / 0.5917 | 1.1600 / 0.6400 |
| rank/pool | 1.2833 / 0.7667 | 1.3400 / 0.6200 |
| rank/perround | 4.2667 / 2.3500 | 4.2600 / 2.3000 |

The verdict - "between exceeds within" - is unchanged on all four. The pollution moved the
figures and not the conclusion, on this directory.

**No published number moved, verified rather than assumed.** `wg-tetris-judge-2026-08-17/pre`
and `/post` reproduce to the digit: post `rank`/`pool` 2.1000 / 1.9250 and pre 1.9000 / 2.2750,
against README's 2.10/1.93 and 1.90/2.27. Both report "POOLED over 5 scored aspect(s)" with no
excluded rounds. A grep of every live doc for the polluted figures returned nothing.

**Pinned in both directions, four ways:**
- `field_ranks.py --selftest` check 7 goes red with a legible message if NO aspect sets
  `control_for` - run against the pre-task tree it printed the defect by name, exit 1. The
  first draft raised `IndexError` there instead, which reads as a broken selftest; that is why
  the existence of a control is checked before anything is built out of it.
- check 11 reclassifies the control as scored by patching `ASPECTS` at runtime and requires the
  guard to STOP firing - proving the verdict comes from `aspects.py`, not from a constant here.
- check 10 requires pooling the control to MOVE `between` from 2.0000 to 2.3333, so the
  exclusion is not decorative.
- check 12 is the variant: a field holding four of the five scored aspects stays green, pools
  exactly those four and reports nothing excluded.
- Separately, `report()` was edited to pool `SCORED + CONTROL + UNKNOWN` and the selftest went
  red at check 9 - the guard in `figures()` fires, so `report` cannot be made to pool the
  control without also disabling the guard.
- `aspects_selftest.py` gains a fourth check with a mutant (the exact task-90 state: nothing
  marked) and a variant (the field set to an aspect id that does not exist). Every other check
  in that file stays green on the mutant, which is why the defect survived in a comment.

**NOT DONE, deliberately: no finding number was allocated.** Six peer worktrees were active and
the queue had eleven finding-number collisions on 2026-08-23. The measurement is recorded here,
in `eval/judge/RUBRIC.md`, `DECISIONS.md` (the `field_ranks` producer section, as a third
parameter: the POPULATION) and `eval/judge/JUDGING.md`. If the orchestrator wants it numbered,
everything it needs is above.
