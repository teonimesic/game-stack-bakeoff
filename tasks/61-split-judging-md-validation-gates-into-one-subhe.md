---
id: 61
title: Split JUDGING.md Validation gates into one subheading per gate
status: open
priority: 5
refs: eval/judge/JUDGING.md:325-453, eval/tools/prune_scan.py --only fat, CLEANUP-LOG.md 2026-08-23 task 53
done_when: each of the six gates is its own subheading under the Validation gates heading, in the same order, with no text removed and no claim reworded; docstat.py --sweep clean and unpiped; and prune_scan.py --only fat no longer reports the parent heading as one section
---

Six gates - 0 reproducibility, 1 ceiling, 2 independence, 3 order-invariance, 4 adjudication, 5 blinding - sit under one heading of ~9,000 characters, the fourth-largest section in the repository. Each gate carries its own evidence table and its own repair history, so a reader who is running gate 3 loads the other five to reach it, and nothing in the document is addressable below the heading: docstat.py --outline shows one entry, and a citation can only say the section, never the gate. Task 53 judged this a split and not a compression - every gate's text is the measurement that bought it, and the reproducibility table plus the n=1 warning are the most load-bearing paragraphs in the file. It was left unedited only because four agents were working in eval/judge at the time and a conflict there costs more than the navigation gain.
