---
id: 209
title: paired_verdicts.load() drops unparseable trial ids and passed-less criteria from every denominator, printing nothing
status: in_testing
priority: 5
refs: eval/judge/paired_verdicts.py,eval/judge/capability.py
done_when: load() no longer loses either class silently - a report.json whose trial id is not 3 parts, and a criterion carrying `id` without `passed`, are each counted and NAMED where the module reports (the excluded/skipped list render() already prints, or a summary line beside it), with fixtures in the selftest whose answers are stated in the expectation (a 2-part tid is red because it is counted, not because the walk broke); a criterion without `passed` present on BOTH sides of a cell must land somewhere stated - today it vanishes from paired AND unpaired - and the fix says where; python3 eval/judge/paired_verdicts.py --selftest --runs-root <main checkout>/eval/runs exits 0 unpiped after.
established_by: 'PR https://github.com/teonimesic/game-stack-bakeoff/pull/90 - 5 review rounds worked, all findings fixed in-round, ceiling reached with no open findings. python3 eval/judge/paired_verdicts.py --selftest --runs-root <main checkout>/eval/runs exits 0 unpiped: 38/38 checks, 5 corpus pins, all published figures reproduce, stored corpus 0 skips over 85 reports. Mutant verified 10/38 red after fixing a suite-crash in my own check that had undercounted it as 3.'
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/90
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

## note 2026-08-29

## Handback, 2026-08-29

Both ticket channels were real, demonstrated on a fixture tree before any fix: a report whose tid is not `game__stack__slot` was continued away at the walk with no render line; a criterion carrying `id` without `passed` read as unpaired=1 on one side and vanished from every denominator on both sides.

The fix, after 5 CodeRabbit rounds (all findings fixed in-round): `load()` returns `(rows, skips)` and render() prints a SKIPPED AT LOAD block naming five skip classes - unusable tid; undecodable/non-mapping report; tier block not a mapping with a criteria list (explicit null named, absent stays silent); criteria absent/null/not a list; criterion not a mapping, id not a string (hash(True)==hash(1)), or id without passed. A named no-passed criterion joins its row's `skipped_crits`, so count_cell distinguishes a malformed record from a suite change: one malformed side reads unpaired=0, a criterion only the other side recorded stays a difference, and the skip label states that scope.

Verified: selftest --runs-root <main>/eval/runs exit 0 unpiped, 38/38 checks (33 synthetic, answers stated in expectations; 5 corpus pins). Published figures reproduce (436/5/332, 232/0/120, 280/4/176, delta 156); stored corpus measures 0 skips over 85 reports (85 re-counted with find, not quoted from the ticket). eval/runs untouched; no finding number allocated.

Controls both directions: red-first every round (each new fixture failed against the unfixed code before its fix); mutant (both original drops re-introduced behind the new API) turns 10 of 38 checks red with corpus pins unaffected - NOT the 3 first measured, because the label check's next() had no default and the suite crashed mid-run, hiding the six expectations after it. Fixed to fail gracefully and re-measured; the lesson - a check that dies is not a check that reports - may warrant a finding number, orchestrator's call. Variants pin one-side and both-side malformed input counted correctly and named.

Declined once, with evidence: the reviewer's round-1 counting rewrite (valid keys minus opposite-side skips) would make a criterion recorded only as malformed invisible to unpaired (r10: theirs 1, stated answer 2); the reviewer withdrew it.
