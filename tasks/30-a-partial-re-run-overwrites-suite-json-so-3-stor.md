---
id: 30
title: A partial re-run overwrites suite.json, so 3 stored runs have a manifest describing a different run
status: done
priority: 4
refs: 'eval/findings/documentation.md #93, eval/runs/wg-matrix-2026-08-13T14-02-50/suite.json, eval/runs/wg-audio48-2026-08-14T19-55-47/suite.json, eval/PROTOCOL.md'
done_when: 'Two things, and the first is not optional. (1) A repair to the run harness so a re-run never destroys an existing manifest - append a new record, or write suite-<timestamp>.json, or refuse to start when suite.json exists and disagrees. Whichever, it must be the WRITE path that changes, not a doc telling operators to be careful. (2) A check, runnable offline over eval/runs/, that asserts each manifest describes the reports present beside it and that started_at is consistent with the directory name. The check must be demonstrated to FAIL on the three known-bad runs above before any repair to their records, and PASS on wg-arena3d, wg-g4c and wg-calib which are currently consistent - a negative control alone is not sufficient here, per rule 1. Do NOT retro-edit the three broken suite.json files into looking correct: reconstruct them under a new name if useful, and leave a record of what was found, since eval/runs is evidence.'
established_by: 'Branch task-30-suite-manifest, commit 31d66bb. WRITE PATH: eval/tools/manifest.py write_manifest() reserves the target with O_EXCL and puts a re-launch in suite-<stamp>.json carrying supersedes and previous_started_at; eval/wholegame.py cmd_build and eval/runner.py both route through it, asserted in the selftest rather than promised. Schema 2 adds run_dir so a manifest names its own directory. CHECK: manifest.py audit, offline over eval/runs, asks two independent questions - does the manifest describe the reports beside it, and does it belong to the directory it sits in. Demonstrated FAILING on all three known-bad runs before any marking, exit 1, with wg-matrix MISMATCH declared=4 present=24, wg-audio48 MISMATCH declaring g3_arena with zero g3_arena reports, wg-audio INCOMPLETE declared=24 present=11. POSITIVE CONTROL: wg-calib, wg-g4c, wg-cal48, wg-cal48b and wg-g4b all pass clean, so the check can go green. wg-arena3d does NOT pass, contrary to the ticket, and the ticket was wrong: its started_at 2026-08-16T13:47:06.522 equals g3_arena__unity__t0 to 2 ms and is 22 hours after the directory name, because the run was built in two waves and the second rewrote the manifest - the same split RUNS.md draws for #49. Two more affected directories found beyond #93''s three, wg-g4 and archive-arena2d-wg-audio48, so five plus one. #93''s third row is also corrected: wg-audio is 1 second from its directory name in local time and is NOT an overwrite; #93 compared a UTC string against a local-time directory name by eye, and this project has stamped run directories both ways. STORED RECORDS MARKED, NOT REPAIRED: six MANIFEST-DEFECT.json written by manifest.py mark; no suite.json was modified and their mtimes are unchanged; wg-audio48''s surviving original was deliberately not promoted over the canonical name. The marker stores the exact issue list it acknowledges and the audit re-measures every run, so MARKER_STALE fires on any change - it is not a mute. Decision and its reversal condition in DECISIONS.md. CONTROLS: eval/tools/manifest_selftest.py, exit 0, whose mutant is the pre-repair writer itself so the suite can see the defect and not only the fix; it caught a real integration bug where cmd_build loaded tools/ modules by path without registering them in sys.modules, which breaks @dataclass. Finding #120 in eval/findings/documentation.md, index and the three range statements updated, docstat.py --sweep exit 0. Follow-up task 63 filed for REPRODUCIBILITY.json and MEASURED.json, which have the same overwrite shape; judge pack mapping.json checked and found sound because each stored round copies its own order_seed.'
---

FINDINGS #93. Launching a partial re-run into an existing run directory overwrites that directory's suite.json, so the canonical manifest ends up describing the re-run and the run it is named for has no manifest at all. Measured over all 18 stored run directories: wg-matrix-2026-08-13 says 2 stacks x 1 game x 2 = 4 trials while holding 24 reports across 4 stacks and 3 games; wg-audio48-2026-08-14 says 4 stacks x 1 game g3_arena x 2 = 8 while holding 16 reports across g1_pong and g2_tetris3d, i.e. it names a game with ZERO reports in that directory; wg-audio-2026-08-14 says 24 and holds 11. Each carries a tell that nothing reads - the started_at inside suite.json contradicts the directory name it sits in, by a full day for wg-audio48. Someone noticed twice and rescued the real content into suite-full-matrix.json and rerun-note.json, while leaving the canonical name pointing at the wrong thing. FINDINGS #68 is NOT affected: DECISIONS.md records it as verified by matching stored per-trial telemetry values, which never read suite.json. The principle was already written down as #77 - keep manifests rather than just scores - but its trigger names judge packs, so it never reached run manifests. Guard the RESOURCE, which is any durable record of what a measurement was configured to be.

## Dispatch knowledge, 2026-08-23 — written back from a launch message

**#68 is not affected.** `DECISIONS.md` records it as verified against stored per-trial
telemetry, which never reads `suite.json`. Do not re-open it.

**Someone already noticed twice** and rescued the real content into `suite-full-matrix.json` and
`rerun-note.json`, leaving the canonical name pointing at the wrong thing. So a repair path
partly exists.

**The principle was already written down as #77 — keep manifests, not just scores — and its
trigger names JUDGE PACKS, so it never reached run manifests.** State the guard as the RESOURCE:
*any durable record of what a measurement was configured to be.* A fix that only handles
`suite.json` repeats the mistake in a smaller way.

**A detector already exists in the data:** each wrong manifest's `started_at` contradicts the
directory name it sits in — by a full day for `wg-audio48`. Nothing reads it.

**The second direction is the one that matters.** Beyond preventing a re-run from destroying the
original, decide what to do about the three already-wrong stored manifests: repair from the
rescued files, or mark them. Repairing evidence is not automatically right — a manifest
reconstructed today is not the record written then — so whichever you choose, a reader must be
able to tell reconstructed from original.
