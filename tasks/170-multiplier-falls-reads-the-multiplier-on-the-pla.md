---
id: 170
title: multiplier.falls reads the multiplier on the player_hit tick, and the g3 contract does not define the multiplier at all
status: todo
priority: 3
refs: eval/judge/bot_arena.py, eval/judge/bot_mutants.py, eval/suites/wholegame_prompts.py, tasks/159
done_when: Either the one-tick reading is DECLINED with the reason written into bot_arena.py and the HAZARDS answer for ref_arena/multiplier.falls updated to state it, or a Pending is added to bot_mutants.PENDING_VARIANTS with a constructed correct game and its measured failing set, and the criterion repaired. Either way the ref_arena/multiplier.falls HAZARDS row stops saying OPEN and not constructed, and bot_mutants.py exits 0.
---

tasks/159 declined the same one-tick reading for rally.counts, and the reason does not carry here. It turned on the g1 contract DEFINING rally as the number of consecutive paddle hits since the last point - a count of the very events the trace line carries - so a line raising paddle_hit with a rally that excludes it contradicts itself. The g3 contract gives multiplier no definition: the state block shows the field, and the prose says only that a multiplier rises with sustained killing and falls when the player is hit. Nothing there fixes the tick on which it falls, so bot_arena reading it across the player_hit tick may be a false negative for a game that drops it a tick later, or on the next kill, or over a ramp. Decide it, do not copy 159. Note the same question applies to multiplier.rises, which asks only that the multiplier rose by any mechanism and is therefore not exposed the same way.
