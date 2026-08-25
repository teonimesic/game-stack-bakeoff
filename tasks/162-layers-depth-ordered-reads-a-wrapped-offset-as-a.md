---
id: 162
title: layers.depth_ordered reads a WRAPPED offset as a scroll rate, and scored the first real scene FALSE
status: in_review
priority: 1
refs: eval/judge/scene_probe.py,eval/SCENES.md,eval/RUNS.md,tasks/156
done_when: layers.depth_ordered returns a scroll rate that survives wrapping - unwrap the offset series against each layer's declared span, or read the per-tick deltas the wrap events bound - and scene_mutants.py carries a VARIANT built from a wrapping scene that is red before the repair and green after; the stored grading in eval/runs/wg-scene-s1ts-2026-08-25 is re-graded offline and the new verdict recorded either way; and whether the contract means offset cumulative or wrapped is decided and written in eval/SCENES.md, since the prompt does not say
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/39
---

The criterion computes abs(offset_last - offset_first) per layer and asks whether it decreases with declared depth. A submission that WRAPS offset - which the scene contract asks for, and which loop.seamless exists to check - returns a modular residue instead of a scroll rate. Measured on s1_parallax__ts__t0, the first scene ever built: all 7 layers came back BELOW their own declared span (road 120.1/240, verge 165.1/340, grove 304.0/440, ridge 232.0/400, range 36.0/480, clouds 245.7/900, sky 84.6/1800) while 37 wrap events fired in the same trace. The submission's own convention agrees with the criterion's (layerFactor = 1/(1+depth)), so a sign-convention reading does not rescue it. This is a FALSE NEGATIVE and a mutant could not have found it: only a submission that wraps could, which is rule 15 and #46's shape.

## note 2026-08-25

## note 2026-08-25 (orchestrator) — the evidence reproduced, and the decision is the harder half

Read from the stored grading rather than the hand-back:

    layers.depth_ordered  passed=False  scored=True
    evidence: depth 0 moved 120.1, depth 0.6 moved 165.1, depth 1.5 moved 304.0,
              depth 4 moved 232.0, depth 9 moved 36.0, depth 20 moved 245.7,
              depth 60 moved 84.6 - not strictly decreasing at separation 0.95

Every figure is below its layer's own declared span, and 37 `wrap` events fired in the same trace.
The numbers are residues, and the criterion read them as rates.

## The decision is not downstream of the repair — it gates it

`done_when` asks whether the contract means `offset` **cumulative** or **wrapped**, and the prompt
does not say. **Decide that first**, because the two answers give different repairs:

- **cumulative** → the submission is wrong and the criterion is right, and the fix is in the
  *prompt*, which is a regime boundary against every scene trial ever run (currently 1).
- **wrapped** → the criterion is wrong, unwrap against each layer's declared span, and the stored
  grading changes.

The submission chose wrapped and nothing told it not to. **A contract that does not say, read by a
submission that had to choose, is a prompt defect whichever way the decision goes** — so say which
in `eval/SCENES.md` even if the code change lands in `scene_probe.py`.

## The variant is the whole test and cannot be a mutant

Rule 15, and this ticket is its cleanest instance to date: **no mutant could have found this**,
because a mutant removes a mechanism and what was needed was an *input* — a scene that wraps. The
8 existing variants were written by the hand that wrote the criteria and none of them wrapped.

So the variant must be **built from a wrapping scene**, red before the repair and green after, and
established in that order (#60: a control run after the fix tests the fix, not the claim).

## What NOT to do

Do not widen the tolerance until the stored submission passes. The separation threshold is 0.95 and
the numbers are residues — a tolerance that admits residues admits anything.

Do not re-grade beyond the one stored scene grading. There is exactly **1**, in
`eval/runs/wg-scene-s1ts-2026-08-25`, and it was salvaged from a killed build — record the new
verdict either way, and keep saying the trial never reached `completed`.
