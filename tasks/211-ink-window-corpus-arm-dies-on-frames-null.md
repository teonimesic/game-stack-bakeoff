---
id: 211
title: 'ink_window_control''s corpus arm dies on one stored record carrying "frames": null instead of naming it'
status: done
priority: 5
refs: eval/judge/ink_window_control.py
done_when: a fixture runs tree holding one healthy record and one whose `programmatic.frames` is null takes `python3 eval/judge/ink_window_control.py --runs-root <fixture> --reference-shift` unpiped to exit 0, with the null-frames record NAMED and COUNTED in the corpus report — partitioned out beside the existing "carry no mean_ink" line, never sorted among the floats — and the healthy record's figures intact; the same tolerance holds at the failure-listing block (`tier1.get("frames", {})`, reading as NOT REGRADABLE) and in reference_shift's extraction chain (counting as an unproved row, the `stored is None` branch that already exists); every site states its answer in a check rather than in a comment; the stored corpus still reproduces the figures read 2026-08-29 (85 gradings, 69 submissions, 0 skipped, the 4 firings with their bounds, 10 of 67 sets moving, extraction proved on all 67); `python3 eval/judge/ink_window_control.py --runs-root <main checkout>/eval/runs --reference-shift` exits 0 unpiped after.
established_by: 'PR #91 squash ea00cb6, branch head cdc76dad93071719445833016786676316850380; verified at cdc76da in own checkout unpiped: bare gate 64/64 exit 0 (~35 s wall, confirming the ~30 s register figure), corpus+shift exit 0 with every done_when figure read at that head (85 gradings, 69 submissions, 16 superseded, 0 skipped, 4 firings with bounds, 10 of 67 sets moving, extraction proved on 67); corpus pins byte-identical to pre-change capture; merge head aca82edb gates+controls green (gates 3m36s, controls 16m22s); zero inline CodeRabbit threads; no finding allocated (the defect is the ticket itself, filed by the eighth cleanup pass with the crash reproduced pre-fix); merged main gates green unpiped (sweep, renumbered, tasks.py check).'
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/91
---

`eval/judge/ink_window_control.py`'s corpus arm — the producer for every ink figure the
documents quote — reaches the frames block with `.get("frames", {})` and then calls `.get`
on the result. For a stored record whose `programmatic` holds `"frames": null`, the first
`.get` returns None (the key EXISTS, so the default never applies) and the second raises:

    line 881 (per-class range loop):
    AttributeError: 'NoneType' object has no attribute 'get'   — exit 1

and the run dies there: every healthy record's figures are lost with the malformed one.
The same `.get` chain sits at line 896 (`f = tier1.get("frames", {})` in the failure
listing) and line 966 (`reference_shift`'s stored-mean_ink extraction); the corpus crash
masks both on the same tree, which is why the reproduction is stated for the corpus arm.

**Measured 2026-08-29:** reproduced end-to-end on a two-record fixture tree before
filing (this ticket's established_by). 0 of the 69 stored records carry a null `frames`
— the corpus arm ran clean over all of them the same day — so nothing live is broken.
Latent only; that is why p5.

**Why it is a ticket at all:** this is the #176 shape — a refusal at the wrong
granularity is an outage; one unreadable record in 464 made the minutes producer exit 2
for a day — applied to the producer for every published ink figure, in a module whose
own standard everywhere else is NAME-AND-COUNT: absent `mean_ink` is partitioned out and
counted, a criterion that never measured is NOT REGRADABLE (a third value, never a
fabricated 0.0), and an unproved extraction refuses to report a shift rather than
reporting one. A null frames block is the one input shape that bypasses all three.

**What NOT to conclude:** today's published figures are unaffected — RUNS.md's
10-mover reference-shift table reproduces row-for-row against the producer this pass.
Do not touch the published tables; do not write into `eval/runs/`.

**Model for the fix:** the module's own handling of absent `mean_ink`. `frames` null or
absent partitions the record out of the range loop with a count and a name, reads as NOT
REGRADABLE in the failure listing, and counts as an unproved row in reference_shift —
the `stored is None` branch is already built for exactly that. `or {}` after each
`.get(..., {})` is the minimal shape; the fixture in `done_when` is the check, and the
corpus pins prove the tolerance changed nothing on the real tree.

## note 2026-08-29

## Done — PR #91, head cdc76da, review round clean

Branch `task-211-null-frames-named-and-counted`, single commit, PR
https://github.com/teonimesic/game-stack-bakeoff/pull/91. CodeRabbit landed
`LANDED_COMMENT` at that head with **no actionable comments** (merge risk Minimal);
`gates` workflow passed with the change in it; `controls` was still running at
hand-back.

**What landed.** One module-level helper `_frames(programmatic)` now mediates all
three readers of the stored frames block (per-class range loop, failure listing,
reference_shift's stored-mean_ink extraction), tolerating missing AND null at both
the `programmatic` and `frames` links. The range loop additionally NAMES each
partitioned record with the shape it hit, via `_no_ink_why` (no frames block /
frames null / no frames.mean_ink) — the existing `(N carry no mean_ink)` count
line is unchanged, so on the real corpus (0 such records) the report is
byte-identical. reference_shift flows null into the existing `stored is None`
unproved branch; no new branch there.

**Design deviation from the ticket's minimal shape, declared:** the ticket
suggested inline `or {}` at each site; this ships one helper with three readers
instead. Reason: the module's own doctrine (the stream-capture policy, #100) is
one copy of a tolerance policy, and a single address is what makes the mutant
patchable in-process — the new phase's two mutants restore the pre-fix chain at
`_frames` and must go red (range loop dies on the fixture; extraction chain dies
decoding a record it holds PNGs for, instead of reporting it unproved). If the
orchestrator prefers the literal inline shape, the helper inlines mechanically.

**Checks, both directions.** New phase `test_the_corpus_arm_tolerates_a_null_frames_block`
(8 expectations, declared in `phases()`; file goes 56 -> 64): drives the null
record in BOTH disk states — no stored frames, and PNGs on disk — asserting
partition-and-name, NOT REGRADABLE with no gate re-grade, and unproved-row with
no shift reported. Red was established BEFORE the fix: the done_when command on
the fixture tree exited 1 with AttributeError at the range loop, 56/56 fixture
expectations green above it. After: same command exits 0 with

    game: n=1  mean_ink min=0.02 max=0.02  (1 carry no mean_ink)
      partitioned out (frames null): g1_nullframes__t0

One fixture-builder bug was caught by the new checks themselves and fixed before
landing: passing frames pixels used to overwrite the record's frames block, so
the null-with-PNGs record was never null; `setdefault` now keeps the disk state
and the field independent.

**Corpus pins.** Both arms diffed against a pre-change capture: byte-identical
except the new phase's rows and the 56->64 total. 85 gradings, 69 submissions,
16 superseded, 0 skipped; 4 firings with their bounds; 67 frame sets read,
extraction proved on all 67, 10 of 67 moving. `--runs-root <main>/eval/runs
--reference-shift` exits 0 unpiped. Nothing written into eval/runs; no published
table touched; no finding number needed (nothing measured beyond what this
ticket already recorded).

**Outside the module, measured and repaired:** the bare gate costs about 30 s
wall locally (29.6 s at that day's HEAD, 30.3 s after this change; two samples
each), not the 0.6 s carried by the gates.yml comment and the workflows README
— nearly all of it the pre-existing fixture phases' per-pixel ink reads
(cProfile: png.ink_coverage / png.Image.differs_from). Both documents now carry
the measured figure, and the cost itself is filed as tasks/212 (this task's
phase is ~0.6 s of the 30 and is not the target).

**Declined in the review, for the record:** an ast-grep info note suggesting
`jsonify` over `json.dumps` in the fixture builder — a Flask-ism; this is a CLI
module writing a fixture file, and `json.dumps` is correct there. No reply
thread was opened (the note is informational, not a conversation).
