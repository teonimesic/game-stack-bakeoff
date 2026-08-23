---
id: 45
title: Repair the tier-1 command capture so a gate's own completion line survives truncation
status: open
priority: 3
refs: eval/FINDINGS.md #99, eval/judge/static.py, eval/IMPROVEMENTS.md axis 2 candidate 1
done_when: a stored programmatic.json written after the change contains the verify recipe's completion line for all four stacks on a run where stderr exceeds 4000 characters, and a selftest pins both directions
---

the evidence for verify.green is stack-correlated incomplete, which blocks any check keyed on a completion token
