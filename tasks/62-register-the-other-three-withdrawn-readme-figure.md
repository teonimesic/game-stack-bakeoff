---
id: 62
title: Register the other three withdrawn README figures, and measure whether any live document still states them
status: open
priority: 4
refs: eval/withdrawn.json, eval/tools/docstat.py, eval/tools/withdrawn_control.py, README.md corrections table
done_when: eval/withdrawn.json carries an entry for each of 20-of-24, the 380-paired-criteria pair (0 verdict differences and 219 of 380), each with match patterns proved against an archive anchor; docstat.py --withdrawn is green at HEAD after whatever repairs those entries name; and each entry was measured RED at a revision before its own withdrawal landed, so it is known the patterns can fire
---

Task 55 built the register and seeded it with two entries: the tier-3 pair (task 54) and finding 54's redundancy claim. README's corrections table declares three more withdrawals that predate it and are in no register entry, so nothing checks whether a live document still states them. They were left out of task 55 deliberately - that task's instruction was to record decisions already made, one at a time, each with its own anchor proof and its own historical red measurement, and adding three unverified entries would have been the vacuous-green shape the register exists to avoid. The 20-of-24 figure is the harder one: eight different combinations of cells reach it, so its signature may need more than the bare number to avoid firing on unrelated prose.
