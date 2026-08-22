---
id: 13
title: Pin or withdraw the 380-paired-criteria figure
status: open
priority: 2
refs: README.md:22, eval/FINDINGS.md #72
done_when: README's 380-paired-criteria row either names the exact runs and games that reproduce it, or is withdrawn in place the way the 20-of-24 figure was
---

README.md's headline evidence table claims '0 verdict differences across 380 paired criteria' and '219 of 380 evidence strings do' differ.

THE PROBLEM: the figure does not say which runs or games it spans. A 2026-08-22 recount from the stored reports could not reproduce 380 under any obvious reading - per (run, game) pair counts came out 30, 112, 112, 120, 140, 148, 148, 140, 148, totalling 1098 across everything. No subset obviously sums to 380.

WHY IT WAS NOT WITHDRAWN THEN: the recount counted every criterion carrying an id and a passed flag, including tier 1. The original may have counted only tier 2, or only scored criteria, or excluded diagnostics. So it is UNSPECIFIED, not shown to be wrong, and withdrawing a possibly-correct number is its own error.

THIS IS THE SAME DEFECT AS '20 of 24', which was withdrawn on 2026-08-22 because eight different combinations of 8-cell groups all produced it. An aggregate is a name within a scope, and neither figure named one (#70's shape).

WHAT TO DO: try the plausible scopes in order - tier 2 only, scored-only, diagnostics excluded, per-run and per-game subsets - and see which yields exactly 380 with 219 evidence-string differences. If one reproduces, write the scope into the README row. If none does after a bounded search, withdraw it in place with the same marking used for 20-of-24, stating what was tried.

Offline and free. Do not re-grade anything.
