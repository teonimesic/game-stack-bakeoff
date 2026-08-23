---
id: 50
title: Repair the same merged-stream capture in runner.py, where the agent's own gate output is stored
status: open
priority: 4
refs: eval/runner.py:177, eval/runner.py:592, eval/runner.py:622, eval/judge/static.py, eval/FINDINGS.md #100
done_when: sh() returns the two streams separately or the callers stop merging them; self_verify and holdout store stdout and stderr apart with the full length of each recorded; every caller of sh() that parses the text is checked, and parse_test_counts and parse_skipped keep reading exactly what they read today; a selftest in the shape of judge/capture_selftest.py pins both directions against the runner path, run against the unfixed function first; and if any reader of the old self_verify.tail or holdout.tail field is found, it is listed and updated rather than left to fail quietly
---

Task 45 repaired the tier-1 capture in judge/static.py: stdout and stderr are stored as separate fields, each sampled on its own budget. The spec-change harness has the identical shape and was not touched: sh() returns (p.stdout + p.stderr) as one string (runner.py:177), and that buffer is stored as self_verify.tail[-4000:] (:592) and holdout.tail[-5000:] (:622). Measured 2026-08-23 over the stored trials/*.json: 26 records have self_verify exit 0, 24 contain the recipe's completion line, and the 2 that do not are exactly the 2 whose tail hit the 4000 cap - one on the rust_bevy arm, one on the baseline arm, which is the same Rust template. Same mechanism, same arm, lower rate because the spec-change tasks are smaller. self_verify is the record of the agent's OWN gate, which is the one place a future check could ask whether the agent ran it to completion.
