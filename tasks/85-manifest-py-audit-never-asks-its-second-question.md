---
id: 85
title: manifest.py audit never asks its second question of a spec-change run
status: in_flight
priority: 5
refs: eval/tools/manifest.py, eval/tools/manifest_selftest.py
done_when: Either audit_run asks the placement question (MISPLACED / STAMP_DRIFT) of a LEGACY_SHAPE manifest and the result over all 12 spec-change directories is stated, or LEGACY_SHAPE is documented as covering placement too with the reason. State the count before and after; 12 of the 23 run directories currently return early.
---

audit_run() returns immediately on LEGACY_SHAPE, before the placement checks. Question 2 - does this manifest belong to the directory it sits in - needs only started_at and the directory-name stamp, both of which a legacy manifest has, so the early return is a scope decision nobody recorded rather than a limitation. Task 75 raised the swept population from 19 to 23 and all four added directories are LEGACY_SHAPE, so 12 of 23 are now examined and told unmeasurable on a question that is in fact measurable for them. The module docstring says both questions run, never one instead of the other, and cites a directory each one alone would clear - that argument does not currently apply to any spec-change run.
