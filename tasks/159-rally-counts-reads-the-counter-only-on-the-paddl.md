---
id: 159
title: rally.counts reads the counter only on the paddle_hit tick, and its evidence string does not say which way it read
status: todo
priority: 3
refs: eval/judge/bot_pong.py, eval/judge/bot_mutants.py, tasks/155
done_when: Either the criterion accepts an increment within a small window after the hit and the pending entry comes back with an empty failing set and is promoted into VARIANTS, or the one-tick contract is DECLINED with the reason written into bot_pong.py and the pending entry removed with that reason. Either way the evidence string states what it measured, and bot_mutants.py exits 0.
---

bot_pong._rally compares state rally across the single tick that raises paddle_hit. Nothing in the g1 prompt orders the event against the counter, and a simulation that emits the event where the collision is resolved and settles its counters in an end-of-tick pass lands the increment one tick later. Measured 2026-08-25 in eval/judge/bot_mutants.py PENDING_VARIANTS: a ref_pong fixture whose counter settles one tick after the hit fails rally.counts. PROVENANCE IS WEAKER THAN THE OTHER PENDING ENTRIES and that is worth stating - those trace to an adjudicated submission, this one is constructed from the state contract, and rally.counts has never failed in the 25 stored g1_pong gradings. A second and smaller defect sits in the same criterion: its evidence reads rally counter incremented on paddle hits regardless of the verdict, so a reader cannot tell a pass from a fail without the boolean beside it.
