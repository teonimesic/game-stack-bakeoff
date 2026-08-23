---
id: 85
title: manifest.py audit never asks its second question of a spec-change run
status: done
priority: 5
refs: eval/tools/manifest.py, eval/tools/manifest_selftest.py
done_when: Either audit_run asks the placement question (MISPLACED / STAMP_DRIFT) of a LEGACY_SHAPE manifest and the result over all 12 spec-change directories is stated, or LEGACY_SHAPE is documented as covering placement too with the reason. State the count before and after; 12 of the 23 run directories currently return early.
established_by: 'audit_run no longer returns before question 2. BEFORE: 12 of 23 stored run directories returned early on LEGACY_SHAPE, so placement was asked of 10 (the 23rd has no manifest at all); AFTER: asked of 22, unchanged verdicts marked=6 ok=5 skip=12 exit 0, no marker went stale. THE TICKET''S PREMISE WAS WRONG AND THAT IS THE RESULT: a legacy manifest has no started_at - all 12 hold exactly suite, template, trials - so both existing channels were unavailable and deleting the early return alone would have bought UNPLACEABLE on 12 directories instead of an answer. runner.py builds its run dir as suite.name plus stamp in one expression, so the suite field self-identifies the directory the way schema 2''s run_dir later did. Placement is now _placement_issues(), three channels keyed on which FIELDS a manifest carries rather than on which harness wrote it, every available one runs, and the LEGACY_SHAPE line names which acted because asked-and-clean and never-asked printed the same word. MEASURED OVER ALL 12: placed and correct on 12 of 12 via the suite channel. Uniformity is rule 9''s tell, so it is corroborated by a channel sharing none of its assumptions - earliest trials/*.json started_at against the directory stamp, 0 to 4 seconds on the local basis for all 12. CONTROLS BOTH DIRECTIONS ON REAL CORPUS BYTES, not only fixtures: bakeoff-godot-2026-08-12T07-55-48''s own suite.json and trials copied into a directory of the same name audits skip exit 0, and copied into core-2026-08-12T07-55-48 audits ERROR SUITE_MISPLACED exit 1, both answers stated before running. manifest_selftest.py all green, 7 new expectations including the variant no channel can place (UNPLACEABLE, a path that had no test), the negative that the suite channel stays silent on a manifest with no suite field, and a MUTANT stubbing _placement_issues to empty which puts the misplaced legacy directory back to severity skip. Detail strings of MISPLACED, STAMP_DRIFT, INCOMPLETE, MISMATCH and NO_MANIFEST left byte-identical because MANIFEST-DEFECT.json acknowledges issues by their exact detail text; UNSTAMPED renamed UNPLACEABLE, warn-level and cited in no document. NOT DONE ON PURPOSE: the earliest-trial-start channel is documented in _placement_issues and not wired in - it exceeds tolerance on 1 of 22 stamped directories, already marked, and disagrees with the manifest channel on exactly the three whose manifest was overwritten, which is question 1''s territory. NO FINDING NUMBER TAKEN, on task 75''s precedent for the same tool and defect class, with four task branches unmerged; handed to the orchestrator. GATES UNPIPED: docstat.py --sweep 0, --withdrawn 0, withdrawn_control.py 54/54 0, tasks.py check 0, census.py --selftest 0, manifest_selftest.py 0. Branch task-85-legacy-manifest-placement, commit ce31070.'
---

audit_run() returns immediately on LEGACY_SHAPE, before the placement checks. Question 2 - does this manifest belong to the directory it sits in - needs only started_at and the directory-name stamp, both of which a legacy manifest has, so the early return is a scope decision nobody recorded rather than a limitation. Task 75 raised the swept population from 19 to 23 and all four added directories are LEGACY_SHAPE, so 12 of 23 are now examined and told unmeasurable on a question that is in fact measurable for them. The module docstring says both questions run, never one instead of the other, and cites a directory each one alone would clear - that argument does not currently apply to any spec-change run.

## Worked 2026-08-23. What the next agent must not re-derive

**The ticket's premise above is wrong and the correction is the whole of the work.** A legacy
manifest does NOT have started_at. All 12 stored spec-change manifests hold exactly
`{suite, template, trials}` - no started_at, no run_dir - so both placement channels that
existed were unavailable, and simply deleting the early return would have bought a warning on
12 directories rather than an answer. Verified by reading all 12 off disk, not from the shape
of the code.

The channel that works is `suite`. `eval/runner.py` line ~1078 builds the run directory as
`f"{suite.name}-{stamp}"` in one expression, so the field identifies the directory by
construction - the same self-identification schema 2 later made explicit as `run_dir`. Placement
is now `_placement_issues()`, three channels, keyed on which FIELDS a manifest carries rather
than on which harness wrote it, and every available one runs.

Other things established, so they are not re-measured:

- Marker files store the exact issue *detail string* under `acknowledges`. Changing the wording
  of MISPLACED / STAMP_DRIFT / INCOMPLETE / MISMATCH / NO_MANIFEST makes every MANIFEST-DEFECT.json
  in eval/runs go MARKER_STALE. Those strings were deliberately left byte-identical.
- `UNSTAMPED` was renamed `UNPLACEABLE` - it now means "no channel could act", not "no stamp".
  Warn-level, so no marker ever acknowledged it, and it was cited in no doc. It had no test
  before; it has one now.
- The earliest `trials/*.json` started_at against the directory stamp is a REAL fourth channel
  and was deliberately not wired in. Reasoning and the measured numbers are in the
  `_placement_issues` docstring; the short version is that it answers question 1's question, not
  question 2's, and it disagrees with the manifest channel on exactly the three directories whose
  manifest was overwritten. It IS used, once, as the independent corroboration of the suite
  channel's 12/12 - a control that shares its subject's assumptions is not a control.
- No finding number was taken, on task 75's precedent for the same tool and the same defect
  class (a sweep printing one word for directories it never examined), and because four task
  branches were unmerged at the time. Handed to the orchestrator.
