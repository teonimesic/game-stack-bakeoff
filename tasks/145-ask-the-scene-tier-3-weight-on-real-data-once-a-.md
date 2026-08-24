---
id: 145
title: Ask the scene tier-3 weight on real data, once a scene matrix exists
status: todo
priority: 3
refs: 'eval/SCENES.md, eval/judge/RUBRIC.md, eval/judge/weight_sensitivity.py, eval/judge/aspects.py, tasks/135, #92, #123'
done_when: 'A scene matrix has been run and graded, and the scene tier-3 weight has been swept over the OPEN interval with a tool that actually varies it - which means weight_sensitivity.py gains a w3 mode with its own constructed-crossover control, or a sibling does. The result is recorded in RUBRIC.md and eval/RUNS.md whichever way it comes out. If the sweep says the weight cannot act, do NOT tune it: read #92 and go and measure what the scene tier 3 has ever separated, the way tier1_census.py did for tier 1.'
---

Task 135 shipped the three scene aspects at weight 0.00 and could not ask whether that weight should ever move. Two reasons, both measured 2026-08-24: weight_sensitivity.py found 10 groups and every one is a game - 0 scene gradings are stored, because no scene has been built; and the parameter it sweeps is w1 over (tier 1, tier 2), while the scene question is w3 over (tier 2, tier 3), which the tool does not sweep. The answer today is NOT ASKED, which is not the same claim as no effect, and eval/SCENES.md names this as the reason to build scenes at all.
