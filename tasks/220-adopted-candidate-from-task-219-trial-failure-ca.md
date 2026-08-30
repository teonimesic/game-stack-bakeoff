---
id: 220
title: 'ADOPTED-CANDIDATE from task 219: trial failure-cause labels with a producer, from the sibling failure taxonomy'
status: in_progress
priority: 3
refs: research/12-sibling-comparison.md, ~/Documents/heavenstudio/game-research-gpt/research/raw/evaluation-methodology.md, eval/FINDINGS.md, eval/tools/census.py, eval/tools/disclosure.py
done_when: 'A closed label vocabulary for trial failure cause exists in the repo; every stored whole-game trial carries one label applied by hand in one session, population taken from tools/census.py, the retired suite excluded or named; a producer cross-tabs labels by run and by stack; and the accept-or-reject measurement is written into the ticket: ACCEPT when some label group surfaces a cross-run or cross-stack pattern not already recorded in FINDINGS or DECISIONS - a rule-9 shared-cause cluster, or a published figure the labels qualify; REJECT and withdraw the vocabulary when every group maps one-to-one onto an already-recorded finding or a terminal_reason partition, which would mean the labels add no dimension. Either outcome closes the task.'
---

Task 219, research/12-sibling-comparison.md, marks the sibling failure taxonomy and its infrastructure-versus-agent failure separation as the one ADOPTED-CANDIDATE from the systematic comparison with game-research-gpt. This repo answers why trials failed ad hoc each time: FINDINGS #45 TMPDIR deletion, #46 a bot that stood still, #49 a daemon gating execve, #37 stalled versus compiling - each found by hand, each invisible to terminal_reason, which partitions how a session ended and not whose fault the outcome was. The sibling applies stable labels per output (setup/version, oracle-weakened, claim-not-reproduced and 13 more, research/raw/evaluation-methodology.md) and aggregates them in its final tables.
