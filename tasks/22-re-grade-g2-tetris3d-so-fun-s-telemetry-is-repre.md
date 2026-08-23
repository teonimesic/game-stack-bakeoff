---
established_by: CLOSED AS UNNECESSARY - the premise was false and no spend was needed. Task 22 assumed #68's fun rounds read pre-repair telemetry from g2_tetris3d. Established from the round files instead of from reasoning: the rounds read wg-audio48-2026-08-14, which carries representative telemetry on 8 of 8 and was re-driven offline on 2026-08-17 specifically so the judge would not be run against unrepaired evidence. Fingerprint match, since the rounds did not record their run: all 7 of 7 quiet_fraction_of_run values and 4 of 4 events_per_second values quoted in #68's evidence strings appear in wg-audio48's stored telemetry, and 0 of 7 and 0 of 4 appear in wg-matrix-2026-08-13's. #68 stands as reported. The defect worth having found is different and is fixed: a stored judge round recorded its GAME but not its RUN, and g2_tetris3d names four fields in different states of repair - #70 (an id is not a key) one level up, with the namespace being the run. field.py now carries mapping['run'] into every stored round.
id: 22
title: Re-grade g2_tetris3d so fun's telemetry is representative
status: done
priority: 1
refs: eval/FINDINGS.md #52 #68, DECISIONS.md
done_when: g2_tetris3d's stored playbot.json reports representative telemetry for all 8 submissions, and fun is re-run on the repaired field with the result compared against #68's - either the positive result survives, or it does not and #68 is corrected
---

Tier 3's ONLY positive result (#68) is that fun's telemetry demonstrably moves the ranking - adjudicated to the two submissions whose telemetry was extreme.

THE PROBLEM: those fun rounds read telemetry that is NOT representative. g2_tetris3d was graded 2026-08-13; the representative play session landed 2026-08-16. Its stored playbot.json files report representative:false on 0 of 8. DECISIONS.md said the confound was 'gone by construction' - true of the code, false of the field that was judged. Corrected there 2026-08-22.

WHY IT MATTERS RATHER THAN BEING BOOKKEEPING: #52's whole point is that criteria-drive telemetry measures the test harness's rhythm, not the game's - the sweep idles, holds inputs and waits for windows to expire. Measured on g4_platformer__ts__t0 (wg-g4c-2026-08-21): a held-input drive gives quiet_fraction 0.780 where the representative session gives 0.033, a 24x difference. If tetris moves comparably, the pacing numbers #68's judge reasoned over were artifacts.

WHAT TO DO: re-grade g2_tetris3d (offline, no agent trials, ~2 minutes per submission) so playbot.json carries the representative session, then re-run fun on that field and compare against the stored 2026-08-17 rounds.

BOTH OUTCOMES ARE PUBLISHABLE. If the ranking holds, #68 survives on better evidence than it had. If it does not, tier 3's only positive result was reading the harness, and that must be said plainly.

CAVEAT ON METHOD: the historical criteria-drive telemetry cannot be reconstructed exactly - an improvised held-input drive on tetris gives 0.999 where the stored evidence cites 0.15, so it is not the same session. Compare the NEW representative numbers against the STORED ones, not against a reconstruction.
