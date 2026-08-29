---
id: 211
title: 'ink_window_control''s corpus arm dies on one stored record carrying "frames": null instead of naming it'
status: todo
priority: 5
refs: eval/judge/ink_window_control.py
done_when: a fixture runs tree holding one healthy record and one whose `programmatic.frames` is null takes `python3 eval/judge/ink_window_control.py --runs-root <fixture> --reference-shift` unpiped to exit 0, with the null-frames record NAMED and COUNTED in the corpus report — partitioned out beside the existing "carry no mean_ink" line, never sorted among the floats — and the healthy record's figures intact; the same tolerance holds at the failure-listing block (`tier1.get("frames", {})`, reading as NOT REGRADABLE) and in reference_shift's extraction chain (counting as an unproved row, the `stored is None` branch that already exists); every site states its answer in a check rather than in a comment; the stored corpus still reproduces the figures read 2026-08-29 (85 gradings, 69 submissions, 0 skipped, the 4 firings with their bounds, 10 of 67 sets moving, extraction proved on all 67); `python3 eval/judge/ink_window_control.py --runs-root <main checkout>/eval/runs --reference-shift` exits 0 unpiped after.
established_by: 'eighth cleanup pass (CLEANUP-LOG.md), 2026-08-29; reproduced on a fixture tree BEFORE filing — corpus arm AttributeError at ink_window_control.py:881 on `"frames": null`, exit 1, the healthy record''s figures lost with it; reference_shift (line 966) and the failure listing (line 896) carry the same `.get` chain but are masked by the corpus crash, and a null `programmatic` never reaches either arm because tier1_census.load_gradings skips it — frames-inside-a-dict is the one reachable shape; 0 of 69 stored records carry it today, so latent'
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
