---
id: 209
title: paired_verdicts.load() drops unparseable trial ids and passed-less criteria from every denominator, printing nothing
status: todo
priority: 5
refs: eval/judge/paired_verdicts.py,eval/judge/capability.py
done_when: load() no longer loses either class silently - a report.json whose trial id is not 3 parts, and a criterion carrying `id` without `passed`, are each counted and NAMED where the module reports (the excluded/skipped list render() already prints, or a summary line beside it), with fixtures in the selftest whose answers are stated in the expectation (a 2-part tid is red because it is counted, not because the walk broke); a criterion without `passed` present on BOTH sides of a cell must land somewhere stated - today it vanishes from paired AND unpaired - and the fix says where; python3 eval/judge/paired_verdicts.py --selftest --runs-root <main checkout>/eval/runs exits 0 unpiped after.
established_by: 'Cleanup pass 2026-08-29 (seventh), CLEANUP-LOG.md. Both channels measured LATENT on the stored corpus: 85 report.json walked under eval/runs, 0 with a tid not of 3 `__`-parts, 0 criteria with `id` but no `passed` (measured by script over the tree, not read from code). The paths: paired_verdicts.py load() line ~130 `if len(parts) != 3: continue`, and line ~137 `if "id" in c and "passed" in c`. The sibling module solved the first shape - capability.py no_stack_correlated_gap check 2 counts a record whose class it cannot name, "counted rather than quietly skipped" - so this is the one module of the pair still carrying the gap. Rule 7: every reason not to count a failure is a channel a bug can widen; the module exists because hand recounting smoothed over exactly this class.'
---

`eval/judge/paired_verdicts.py` `load()` has two silent-drop channels in the counting path,
in a module whose docstring spends three refusals on refusing to smooth things over:

1. **Unparseable trial ids.** The walk is `**/artifacts/*/eval/report.json`; a report whose
   directory name does not split into `game__stack__slot` is `continue`d away at
   `load()`. It reaches no cell, no exclusion list, no count - a reader of the report
   cannot tell it was walked. `wg-g4c-capgate`'s 16 arm reports are the case the module
   already handles the RIGHT way for a different reason (no trial JSONs → terminal reason
   `unknown` → excluded BY NAME); a malformed tid gets less than capgate gets.

2. **Criteria without `passed`.** The crits filter keeps only `id`-and-`passed` criteria.
   One dropped on one side of a cell lands in `unpaired_criteria` (counted, mislabelled a
   suite change but visible); one dropped on BOTH sides vanishes from every denominator.

Both are latent today: measured 2026-08-29 over the stored tree, 85 reports walked, 0 of
either. That is the finding's whole claim to a p5: fix the channel before a future run
directory (judge packs land inside run directories, #83) puts a differently-shaped
directory under `artifacts/` and the floor silently narrows.

**What NOT to conclude:** nothing in the stored corpus is miscounted - every pin
reproduces (436/5/332, 232/0/120, 280/4/176, delta 156, re-run 2026-08-29). This ticket
is about the channel, not a wrong number. Do not touch the PINS or the published figures;
do not write into `eval/runs/`.

**Model for the fix:** capability.py's `no_stack_correlated_gap` - a record the module
cannot classify is a counted problem with its name attached, never a quiet skip. The
cheapest shape here: `load()` returns the skips it made alongside rows, `render()` prints
them beside `EXCLUDED CELLS`, and the selftest fixture plants one 2-part tid and one
`passed`-less criterion on both sides of a cell with the expected counts stated.
