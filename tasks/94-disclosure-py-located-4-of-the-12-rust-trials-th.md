---
id: 94
title: disclosure.py located 4 of the 12 rust trials that reported the broken just run recipe - the starter-arrived-broken cue set under-reports by 3x and its docstring states no rate for that family
status: open
priority: 3
refs: eval/tools/disclosure.py, tasks/81, eval/RUNS.md, AGENTS.md rule 11
done_when: either the cue set is widened and re-measured against a hand pass over the same 90 messages, with the new located/hand pair recorded in the docstring for BOTH families and a control showing the widened set does not fire on a trial that reported nothing; or the family is documented as a locator with no measured rate and every doc citing its counts says so
---

tasks/81 reproduced the default-run defect and, while doing so, counted the corpus directly: 12 rust trials across 5 runs say in their closing message that just run was broken and that they added default-run themselves. disclosure.py fires on 4 of them, and its docstring quotes an under-report ratio only for the what-I-could-not-verify family (26 located against 31 hand-classified), not for this one. A locator that finds a third of a family it names as a family will be read as a census by the next reader, exactly as tasks/81 was written from it. The producer for the 12 is a grep of runs/**/artifacts/*rust*/agent_result.json .result for default-run|two binar|ambiguous|could not determine which binar|just run|cargo run; the 8 it misses are phrased as fixes rather than as complaints - 'default-run = game was needed', 'crates/game gained default-run', 'it needed default-run in the manifest'.
