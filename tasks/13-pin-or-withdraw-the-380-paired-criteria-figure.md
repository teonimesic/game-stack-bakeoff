---
established_by: 'WITHDRAWN, the same way 20-of-24 was. Searched every coherent scope for a paired-criteria count of 380: all runs 1098, wg-matrix alone 436, wg-matrix+wg-arena3d 584, wg-audio48 232, everything-except-g4 958; by tier, playbot 540 and programmatic 402; and scored-only variants of each. NONE gives 380. Six arbitrary subsets do, but every one mixes runs and games incoherently (e.g. wg-audio pong + wg-matrix arena + wg-audio48 tetris) - the same signature as 20-of-24, where many combinations reach the number and none is principled. Separately, the claim''s OTHER half is false under every scope with a plausible count: ''0 verdict differences'' is 5 for wg-matrix and 13 across all runs. Part of that drift is this session''s own criterion repairs re-grading cells, so the figure may have been true when written - which is the argument for recording an aggregate''s scope AND its date. README now reports per scope instead: wg-matrix 436 paired / 5 verdict diffs / 332 evidence diffs; wg-audio48 232 / 0 / 120.'
id: 13
title: Pin or withdraw the 380-paired-criteria figure
status: done
priority: 2
refs: 'README.md:22, eval/FINDINGS.md #72'
done_when: README's 380-paired-criteria row either names the exact runs and games that reproduce it, or is withdrawn in place the way the 20-of-24 figure was
---

README.md's headline evidence table claims '0 verdict differences across 380 paired criteria' and '219 of 380 evidence strings do' differ.

THE PROBLEM: the figure does not say which runs or games it spans. A 2026-08-22 recount from the stored reports could not reproduce 380 under any obvious reading - per (run, game) pair counts came out 30, 112, 112, 120, 140, 148, 148, 140, 148, totalling 1098 across everything. No subset obviously sums to 380.

WHY IT WAS NOT WITHDRAWN THEN: the recount counted every criterion carrying an id and a passed flag, including tier 1. The original may have counted only tier 2, or only scored criteria, or excluded diagnostics. So it is UNSPECIFIED, not shown to be wrong, and withdrawing a possibly-correct number is its own error.

THIS IS THE SAME DEFECT AS '20 of 24', which was withdrawn on 2026-08-22 because eight different combinations of 8-cell groups all produced it. An aggregate is a name within a scope, and neither figure named one (#70's shape).

WHAT TO DO: try the plausible scopes in order - tier 2 only, scored-only, diagnostics excluded, per-run and per-game subsets - and see which yields exactly 380 with 219 evidence-string differences. If one reproduces, write the scope into the README row. If none does after a bounded search, withdraw it in place with the same marking used for 20-of-24, stating what was tried.

Offline and free. Do not re-grade anything.
