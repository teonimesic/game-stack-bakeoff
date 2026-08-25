---
id: 160
title: fire.rate_limited counts BULLETS and asks about SHOTS, and prints the right number beside the wrong verdict
status: todo
priority: 2
refs: eval/judge/bot_arena.py, eval/judge/bot_mutants.py, tasks/155
done_when: The criterion counts fire events rather than bullet ids, or states in bot_arena.py why a bullet count is the right proxy and what a spread weapon should score; the ref_arena spread entry in PENDING_VARIANTS comes back with an empty failing set and is promoted into VARIANTS; bot_mutants.py exits 0; and the stored g3_arena verdicts are re-derived with eval/judge/tier2_census.py against the main checkout's eval/runs with before and after counts recorded here.
---

The criterion's own question is: is there a minimum interval between shots rather than one bullet per tick. bot_arena._firing_in scores it as 0 less than n_x and n_x at most 80, where n_x is the number of distinct BULLET ids created over 120 ticks of held fire. A weapon that fires a spread puts several bullets in the world per shot, which is an ordinary design for a game the g3 prompt asks to make loud, fast and readable at a glance. Measured 2026-08-25 in eval/judge/bot_mutants.py PENDING_VARIANTS: a ref_arena fixture firing a three-round spread on a 4-tick cooldown fails with 90 bullets from 120 ticks of held fire (30 fire events). 30 shots in 120 ticks IS a rate limit, and the criterion prints that number in its own evidence string beside a verdict computed from the other one.
