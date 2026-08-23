---
id: 90
title: fun_frames is excluded from aggregates by comment only - nothing enforces it
status: open
priority: 3
refs: eval/judge/aspects.py, eval/judge/field_ranks.py, eval/judge/RUBRIC.md
done_when: 'either FUN_FRAMES sets diagnostic_only and every aggregate over aspects reads it, or the guard is removed from the comment and replaced with what actually holds. Whichever way, pinned in both directions: a mutant that pools the control must go red, and a variant that pools five scored aspects with one of them missing must stay green. field_ranks.py must state, in its output, which aspects a pooled figure is over'
---

aspects.py says FUN_FRAMES is a control that must never be pooled with the other five and that it is diagnostic_only so no aggregate can absorb it by accident. Aspect.diagnostic_only is defined at aspects.py:41, is NOT set on FUN_FRAMES (measured: frozenset() empty), and is read by no code anywhere - the only readers of that name are probe.py and the play bots, a different mechanism with the same field name. field_ranks.py without --per-aspect pools every round in the directory it is given regardless of aspect: measured on runs/wg-aspect-reliability it pools 30 rounds of which 5 are fun_frames, and reports between exceeds within on all four value/order readings. Three stored directories mix the control with scored aspects - wg-aspect-reliability, wg-funframes-crossgame/arena, wg-funframes-crossgame/platformer. NO PUBLISHED NUMBER IS AFFECTED: the separation figure README and DECISIONS quote comes from wg-tetris-judge-2026-08-17/pre and /post, which hold no fun_frames rounds - the control lives in sibling directories funframes, repeats and repeats7.
