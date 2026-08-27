---
id: 174
title: The shift estimator answers for the whole frame, not for the band it was asked about
status: in_review
priority: 2
refs: eval/judge/scene_probe.py,eval/SCENES.md,tasks/164,#189
done_when: 'The estimator either scores each band from pixels belonging to that band only - masking or windowing the search to the band''s own region - or it is established with a measurement that it cannot, and the criterion is re-scoped to what it can actually read. Either way: the cross-band agreement above is re-measured and stated per pair, the 6 s1_parallax fixtures are run before and after with each criterion''s fail and unsc columns compared, scene_mutants.py exits 0 with its counts stated, and eval/runs/wg-scene-s1ts-2026-08-25 is re-graded READ-ONLY with layers.image_parallax recorded either way. A null result - the estimator is doing the best obtainable thing and three bands are genuinely unreadable - closes this, provided the cross-band figures are what establishes it.'
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/50
---

`ParallaxScene` measures each layer's per-frame shift by searching for the offset that best aligns a band between two captures. The repair in tasks/164 stopped the reliability filter from passing every layer regardless of what came back, and doing so made a SECOND defect legible that the first was hiding: the estimator locks onto one whole-frame feature rather than onto the band it is scoring.

Measured on the first stored scene (eval/runs/wg-scene-s1ts-2026-08-25). At frame pair 4 all five lower bands answer -9px. At pairs 1, 3, 5 and 10, four of them answer -46, -19, -66 and +8 respectively. Bands that are contracted to move at DIFFERENT rates - that is the entire point of a parallax scene - are returning the same number, which is the signature of one dominant feature crossing the frame and every band's search finding it.

Consequence now that the filter is honest: three bands fail on CONFIDENCE rather than on aliasing. So the criterion is currently unable to read a scene it should be able to read, and the reason is the instrument rather than the submission. tasks/164 recorded this as visible-and-out-of-scope rather than repairing it, which was the right call - it is a different mechanism from the slack floor and the aliasing precondition.

Note the shape: near-identical readings ACROSS independent subjects at the same pair is rule 9 - a repeated identical measurement across subjects that share nothing but the instrument is reporting the instrument.
