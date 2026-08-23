---
id: 85
title: manifest.py audit never asks its second question of a spec-change run
status: open
priority: 5
refs: eval/tools/manifest.py, eval/tools/manifest_selftest.py
done_when: Either audit_run asks the placement question (MISPLACED / STAMP_DRIFT) of a LEGACY_SHAPE manifest and the result over all 12 spec-change directories is stated, or LEGACY_SHAPE is documented as covering placement too with the reason. State the count before and after; 12 of the 23 run directories currently return early.
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
