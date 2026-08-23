---
id: 72
title: docstat --renumbered reports 33 decided stale citations after the 2026-08-23 merge wave, and nothing has repaired them
status: in_flight
priority: 3
refs: 'eval/tools/docstat.py --renumbered, eval/FINDINGS.md, eval/findings/documentation.md #118'
done_when: 'python3 eval/tools/docstat.py --renumbered reports zero DECIDED stale citations, with every repair made to the CITATION and never to a finding number; the undecidable list is read individually and each entry either repaired or recorded as correct, with the count stated. A positive control is required: the tool must still fire on a planted stale citation after the sweep is clean, otherwise a green result is indistinguishable from a tool that stopped looking.'
---

Task 58 built --renumbered and repaired the five citations known then, recording that the 21 remaining were read and correct. A later merge wave renumbered #119 four ways - it is #120 (the manifest guard), #121 (the ceiling counter), #122 (the retired suite) and #123 (the tier-1 weight) depending on which sentence you are reading - and 33 citations across 16 files now name a finding that history shows meant something else. Every one of them RESOLVES, which is why --sweep stays exit 0 and nothing else can see them. Found while closing task 63, whose own ticket cites documentation.md #119 for what is now #120; the two citations inside the changed sentences were repaired there and the rest were deliberately left rather than expand that task's diff into sixteen documents.
