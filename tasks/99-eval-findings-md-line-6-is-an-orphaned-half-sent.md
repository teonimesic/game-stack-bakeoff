---
id: 99
title: eval/FINDINGS.md line 6 is an orphaned half-sentence left by an edit that replaced the line above it
status: todo
priority: 4
refs: eval/FINDINGS.md, eval/tools/docstat.py, tasks/88
done_when: eval/FINDINGS.md line 6 is gone, docstat.py --sweep exits 0, and the sweep gains a check that would have caught it -- an unfenced line in a live or archive instruction document that is a strict suffix of the sentence ending on the line above, pinned red on the real line as it stands at HEAD before the fix and green after
---

Task 88 found it while giving the findings count a producer, and did not touch it: eval/FINDINGS.md is the archive and the ticket did not authorise editing it. Lines 3-6 read 'Check whether a number has been retracted before trusting it -- eval/withdrawn.json is the machine-readable half of that, and docstat.py --withdrawn enforces it over the live documents.' followed by a bare 'number has been retracted before trusting it.**'. git blame: line 4-5 come from 07dea94b, which rewrote the sentence and left the tail of the old one behind. It is not a number and not a claim, so no withdrawal register entry applies; it is text corruption in the file every session is told to read first. Related shape, same paragraph family: an evil merge (8fef835) duplicated the range ROW in AGENTS.md and README.md, which task 88 did fix and now gates.
