---
id: 116
title: DECISIONS.md Open section states a launched game as not launched, and carries a duplicated paragraph fragment
status: open
priority: 3
refs: DECISIONS.md Open section, eval/judge/tier1_census.py, eval/judge/tier2_census.py, AGENTS.md Keep the documentation current
done_when: the g4 bullet in DECISIONS.md's Open section states what is true now - re-read from a producer run in the session, not from memory - and the duplicated fragment is gone, with docstat.py --sweep, --findings and --withdrawn green and no new figure introduced without its producer
---

Found while re-checking README's headline for task 115. The Open section says 'g4, the platformer, is designed and NOT launched. Launching needs approval and at least two calibration trials; the honest cost range is 800-1900 dollars (#42)'. The platformer has since run: tier1_census and tier2_census both report a g4_platformer group of 8 trials, and the harder-task pricing section a few hundred lines above quotes its field as a completed 8/8. The same bullet also carries a duplicated, half-overwritten paragraph - the sentence '40 of 56 matrix trials at the ceiling with zero variance, not merely near it (#92)' appears twice, the second time as an orphan continuing a sentence that already ended. AGENTS.md says DECISIONS.md states what is true now and superseded content is replaced, not annotated, so both are live defects in an always-cited document. Out of scope for 115, which was README only.
