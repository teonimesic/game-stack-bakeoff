---
id: 164
title: 'The reliability filter passes a fast layer whatever the estimator returned: its agreement slack is a floor in RATIO units'
status: in_review
priority: 2
refs: eval/judge/scene_probe.py,eval/judge/scene_mutants.py,eval/RUNS.md,tasks/162
done_when: the agreement test refuses a layer whose per-pair ratios agree only because the slack floor exceeds the signal - a slack derived from the estimator quantisation the pair actually has, not a constant in ratio units - with the FIXTURE census before and after so nothing that used to be readable silently stops being; a variant built from a scene whose near layer crosses more than one span between captured frames is red before and green after; whether an aliased band should be unreadable or whether 12 frames is too few for this scene is decided and written in eval/SCENES.md; and eval/runs/wg-scene-s1ts-2026-08-25 is re-graded and the layers.image_parallax verdict recorded either way
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/46
---

ParallaxScene._reliable keeps a layer when at least 80% of its per-pair shift-to-offset ratios sit within max(|median| * 0.15, 0.15) of the median. The second term is a floor in ratio units and it does not scale with how fast the layer moves, so on a fast layer it swallows the whole search window. Measured on the one stored scene submission after the tasks/162 repair: the road band has median ratio 0.053 and slack 0.150, which is 2.8x the median, so every one of its 8 usable pairs agrees and the layer is called readable - while its measured shifts run from -73px to +67px and it crosses 1.6-2.25 spans between two captured frames, which means the shift is aliased against its own tile and carries no rate at all. That promotion is what let layers.image_parallax establish itself on 3 bands and score the submission FALSE, where the honest verdict is scored=False; eval/RUNS.md records both and says not to quote the FAIL. The two bands it was compared against, clouds and sky, move 25 and 8 world units per captured pair and measured 0px on 11 of 11 and 9 of 11 pairs, so a sub-pixel band and a stationary one are the same reading here. Note the shifts are near-identical ACROSS bands at the same pair (-46,-46,-46,-45 at pair 1; -66,-66,-66,-43 at pair 5), which is the estimator locking onto one whole-frame feature rather than each band - the instrument error DECISIONS.md records, at a rate the fixtures never showed.

## note 2026-08-27

## note 2026-08-27 (orchestrator) — a second agent is reading eval/runs concurrently: READ it, do not WRITE it

`tasks/158` is in flight as of now and its `done_when` runs `eval/judge/tier2_census.py` against
the main checkout's `eval/runs`. Yours re-grades `eval/runs/wg-scene-s1ts-2026-08-25`. Both are
fine as long as both stay **read-only against that tree**, which is the only piece of state here
that is not branchable — your worktree gives you an isolated checkout of the code and does *not*
isolate a stored run you write into.

**So: compute the re-grade and record the verdict in this ticket and in `eval/RUNS.md`. Do not
store a new judge round under `eval/runs/`.** If your `done_when` turns out to be unreachable
without writing there, that is the unanticipated decision this ticket did not cover — say so here
and stop that one clause, rather than writing into the tree while another agent is counting it.
Everything else in the ticket proceeds regardless.

**One thing to carry from `tasks/163`, which merged the same day.** Its window was calibrated per
task class and the temptation the ticket named was to widen a bound until the one stored
submission passed. Yours has the same shape pointed the other way: the honest outcome may be that
the road band is **unreadable**, not that the slack needs a better constant. `eval/RUNS.md`
already says not to quote that FAIL. A repair that makes the stored scene readable is not
self-evidently the right one — say which population your new slack is calibrated on, the way
`static.TIER1_BOUND_POPULATION` now does for the ink window.
