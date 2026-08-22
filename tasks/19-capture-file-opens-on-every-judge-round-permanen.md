---
id: 19
title: Capture file-opens on every judge round, permanently
status: open
priority: 1
refs: eval/FINDINGS.md #83, eval/judge/field.py
done_when: every judge round writes the files it opened into its stored record, and a check refuses to report a code-aspect result from a round that has no such log
---

Task 09 added a capture of which files a judge actually opens, to answer an unrelated question: does a bigger pack make it read more?

WHY IT NOW MATTERS MORE: FINDINGS #83 found trial ids inside 25 stored packs - the answer key in a directory the judge is told is anonymous. Bounding the damage was only possible for rounds that HAPPENED to have a file-open log. 37 of 63 rounds have one; 14 of those 37 opened a leaking file, 3 of them for all eight submissions. The other 26 rounds cannot be assessed at all and stay permanently suspect.

#32 concluded that no gate can ask what the judge knew. That is no longer true - the file-open log answers it directly - but only where the log exists.

WHAT TO DO: field.py already runs the judge with --output-format stream-json and records tool calls, so the capture exists. Verify it is on for EVERY aspect and every path through field_sweep (orders mode, sequential mode, repeats mode), not just the ones exercised so far. Then add a check that a code-aspect result from a round with no file-open log is reported as unverifiable rather than quoted.

THE GENERAL PRINCIPLE, worth stating wherever it lands: capture what the instrument DID, not only what it concluded. An audit trail added for one question answered a different and more serious one two weeks later, and it cost nothing to keep.

Offline. No new judging required to do the wiring; verifying coverage may need one cheap round per mode.
