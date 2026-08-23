---
id: 42
title: Re-pack wg-g4c once the aspect-reliability sweep is finished, and compute the exclusion set rather than guessing it
status: open
priority: 2
refs: eval/RUNS.md wg-g4c-2026-08-21, eval/FINDINGS.md #95 #77 #83, eval/judge/field.py packcheck
done_when: the sweep process is confirmed gone (not inferred from its log), then wg-g4c is re-packed with the exclusion set computed and shown rather than assumed; python3 judge/field.py packcheck --run runs/wg-g4c-2026-08-21T02-26-46 run UNPIPED reports clean=True stale=0 and exits 0; the .codex hooks configs are gone from every submission's pack, checked by grepping the packs on disk for the trial-id and game-research-work patterns; and eval/RUNS.md's stale-files block is replaced with what is then true, stating that any judge round stored before the re-pack read a field that no longer exists
---

wg-g4c carries 23 stale files in 222 on disk (unity 10, godot 8, ts 3, rust 2), left in place deliberately because the wg-aspect-reliability sweep was reading the run live and re-packing would have changed the field underneath its own repeats. anonymise.build_pack now clears its destination, so a re-pack fixes it - but a re-pack is NOT free of judgement. Rebuilding an old pack against today's starter reclassifies template code as authored work (#77), so the exclusion set must be computed as (files in the rebuilt pack) MINUS (files in the stored manifest) MINUS (files the original dropped for length, which is 0 since #69), not guessed. Until this is done, judge/field.py refuses every code aspect on this run, and no idiomatic or architecture ordering from it is readable. Eleven of the stale files carry content nothing lists, including a .codex hooks config in 7 of 8 submissions naming its own trial id - the #83 answer key. Blinding currently holds only because field.build_pack neutralises it at copy time, which is a second mechanism, not the repair.
