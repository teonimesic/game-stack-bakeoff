---
established_by: 'Every judge round now records a provenance block, verified populated against a real pack: run, sees, blind_language, brief_sha256 + brief_chars, evidence_counts, capture_geometry, knowingly_truncated, max_turns, per_call_budget_usd, judged_at - alongside the files_opened capture task 09 added. Chosen by asking which parts of ''what did this round see?'' would be GONE in a month rather than which seemed interesting. The brief hash is the sharpest of them: the brief is not fixed (a geometry note was added 2026-08-22) and rounds either side saw different text, which is why task 08 re-ran seven repeats rather than topping up four - a decision made by argument that a hash turns into a comparison. field_sweep.warn_rounds_without_provenance() reports pre-existing rounds that cannot answer for themselves: 10 of 10 in the tetris judge round, 12 of 12 in the cross-game sweep. FINDINGS #86 records the argument in its strongest form: the #68 rescue worked by matching numbers quoted in fun''s PROSE against stored telemetry, which was luck about one aspect''s writing style - ux and idiomatic quote no figures and would have been unresolvable, so prose is not a substitute for a field.'
id: 19
title: Capture file-opens on every judge round, permanently
status: done
priority: 1
refs: 'eval/FINDINGS.md #83, eval/judge/field.py'
done_when: every judge round writes the files it opened into its stored record, and a check refuses to report a code-aspect result from a round that has no such log
---

Task 09 added a capture of which files a judge actually opens, to answer an unrelated question: does a bigger pack make it read more?

WHY IT NOW MATTERS MORE: FINDINGS #83 found trial ids inside 25 stored packs - the answer key in a directory the judge is told is anonymous. Bounding the damage was only possible for rounds that HAPPENED to have a file-open log. 37 of 63 rounds have one; 14 of those 37 opened a leaking file, 3 of them for all eight submissions. The other 26 rounds cannot be assessed at all and stay permanently suspect.

#32 concluded that no gate can ask what the judge knew. That is no longer true - the file-open log answers it directly - but only where the log exists.

WHAT TO DO: field.py already runs the judge with --output-format stream-json and records tool calls, so the capture exists. Verify it is on for EVERY aspect and every path through field_sweep (orders mode, sequential mode, repeats mode), not just the ones exercised so far. Then add a check that a code-aspect result from a round with no file-open log is reported as unverifiable rather than quoted.

THE GENERAL PRINCIPLE, worth stating wherever it lands: capture what the instrument DID, not only what it concluded. An audit trail added for one question answered a different and more serious one two weeks later, and it cost nothing to keep.

Offline. No new judging required to do the wiring; verifying coverage may need one cheap round per mode.
