---
id: 162
title: layers.depth_ordered reads a WRAPPED offset as a scroll rate, and scored the first real scene FALSE
status: todo
priority: 1
refs: eval/judge/scene_probe.py,eval/SCENES.md,eval/RUNS.md,tasks/156
done_when: layers.depth_ordered returns a scroll rate that survives wrapping - unwrap the offset series against each layer's declared span, or read the per-tick deltas the wrap events bound - and scene_mutants.py carries a VARIANT built from a wrapping scene that is red before the repair and green after; the stored grading in eval/runs/wg-scene-s1ts-2026-08-25 is re-graded offline and the new verdict recorded either way; and whether the contract means offset cumulative or wrapped is decided and written in eval/SCENES.md, since the prompt does not say
---

The criterion computes abs(offset_last - offset_first) per layer and asks whether it decreases with declared depth. A submission that WRAPS offset - which the scene contract asks for, and which loop.seamless exists to check - returns a modular residue instead of a scroll rate. Measured on s1_parallax__ts__t0, the first scene ever built: all 7 layers came back BELOW their own declared span (road 120.1/240, verge 165.1/340, grove 304.0/440, ridge 232.0/400, range 36.0/480, clouds 245.7/900, sky 84.6/1800) while 37 wrap events fired in the same trace. The submission's own convention agrees with the criterion's (layerFactor = 1/(1+depth)), so a sign-convention reading does not rescue it. This is a FALSE NEGATIVE and a mutant could not have found it: only a submission that wraps could, which is rule 15 and #46's shape.
