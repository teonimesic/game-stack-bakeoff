---
id: 16
title: Give fun a representative play session instead of the criteria drive
status: open
priority: 2
refs: eval/FINDINGS.md #52, eval/judge/telemetry.py, eval/judge/probe.py
done_when: fun's telemetry comes from a session driven to look like play rather than from the criteria sweep, AND the effect is measured on stored submissions - EITHER quiet_fraction_of_run moves materially, with the before/after reported, OR it does not, in which case the criteria drive was representative enough and the change is reported as buying nothing rather than shipped
---

The 'fun' aspect reads telemetry.json - event counts, intervals, how long the run went quiet - measured from a real driven run of the submission.

THE PROBLEM, recorded in #52 and explicitly left unfixed: the telemetry comes from the session that DRIVES THE CRITERIA, not from anything resembling play. A criteria sweep deliberately idles, holds inputs, waits for windows to expire and repeats the same probe - so 'how long the run went quiet' measures the test harness's rhythm, not the game's.

WHAT WAS DONE INSTEAD: _telemetry_evidence now reports quiet_fraction_of_run and, above 0.9, a pacing_evidence_warning naming the event count and run length. The finding says plainly that this 'stops the number being read as pacing; it does not make the evidence good.'

WHY IT MATTERS NOW RATHER THAN THEN: 'fun' produced tier 3's only positive result (#68) - the telemetry demonstrably moves the ranking, adjudicated to the two submissions with extreme telemetry. That makes the quality of the telemetry load-bearing for the one aspect that has been shown to read its evidence. If the pacing numbers are an artifact of the criteria drive, the positive result is measuring the harness.

WHAT TO DO: add a representative play session to probe.py - the bot already has play_inputs for exactly this purpose, used by the arena and platformer bots - and feed fun's telemetry from that session rather than the criteria sweep.

FALSIFICATION: if quiet_fraction_of_run barely moves on stored submissions, the criteria drive was representative enough and the change buys nothing. Report that rather than shipping it.
