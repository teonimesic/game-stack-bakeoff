---
id: 74
title: The only route left to tier-2 discrimination is a harder task, and nobody has priced one
status: open
priority: 2
refs: 'DECISIONS.md saturated-tier-2 decision, eval/judge/tier2_census.py, eval/suites/wholegame_prompts.py, FINDINGS #126'
done_when: 'a costed proposal in DECISIONS.md for what a harder task looks like - either a fifth game or a raised bar on an existing one - with the measured trial price from eval/RUNS.md and a statement of what tier-2 criterion would have headroom on it. OR a measurement showing some existing group can be de-saturated without a new run, which would retire this. Do not launch anything: the spend is the operator''s call and this task is to bring them the number.'
---

tier2_census.py reports 5 of 10 groups returning a single value, every selective tier-2 failure in the corpus is from wg-matrix-2026-08-13, and both in-rubric repairs were measured and do not work (FINDINGS #126): the three withheld diagnostics are single-valued wherever recorded, and four criteria built from requirements the g4 prompt states and no criterion checks passed 8 of 8 on wg-g4c. g4_platformer was added as the most plausible remaining route to discrimination and tied. That leaves the task, and a task change costs a matrix, so it needs a price before it needs a design.
