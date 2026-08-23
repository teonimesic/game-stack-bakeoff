---
id: 66
title: The .codex answer key is still in two runs' stored judge packs, and a re-grade would read it
status: done
priority: 2
refs: 'eval/FINDINGS.md #83, eval/judge/field.py build_pack, eval/judge/repack.py, tasks/42'
done_when: wg-matrix and wg-audio48 either hold packs with no trial-id, work-root or .codex pattern in any file, verified by grep over every pack in both runs, or are marked in eval/RUNS.md as carrying the key with the per-stack counts stated and re-grading them barred
established_by: repack.py dry-run refuses 24 of 24 in wg-matrix (no pack.manifest) and 16 of 16 in wg-audio48 (12 on files_dropped_for_length 1-11, 4 on a missing starter baseline commit); all 40 work trees have a .git with no HEAD and 0 loose objects against wg-g4c's 8 with HEAD and 87-211, so the baseline is destroyed and re-packing is the wrong repair; radius measured per pack at 18 of 24 and 6 of 16 with per-stack counts; field.build_pack sees=code already refuses all five game fields in both runs while the same call on wg-g4c builds 199 files; both runs marked and barred in eval/RUNS.md
---

## What this is

A **judge pack** is the anonymised copy of a submission that an LLM judge reads. Its whole
purpose is that the judge cannot tell which stack or trial it is looking at — blinding is what
makes a cross-submission comparison mean anything, and `eval/judge/verify_blind.py` exists to
prove it.

## What is wrong, and how we know

Finding **#83** established that a `.codex` hooks configuration inside a submission names its own
trial id verbatim — `g2_tetris3d__unity__t1` and the like. That is an **answer key**: a judge that
opens it knows the stack, the game and the trial.

Task 42 re-packed `wg-g4c-2026-08-21` and verified the key gone: 0 hits for the trial-id,
`game-research-work` and `.codex` patterns across all eight of its packs.

**It re-packed only that run.** Measured 2026-08-23, the pattern is still present in the stored
packs of:

    eval/runs/wg-matrix-2026-08-13T14-02-50
    eval/runs/wg-audio48-2026-08-14T19-55-47

## Why it matters

Two different exposures, and they need separating rather than conflating:

1. **Historical.** Rounds already judged against those packs may have read it. #83 bounded that
   with the judge's file-open log where the log exists, and 26 rounds have no log and are
   permanently unassessable. **Nothing in this task can change that** — do not re-open it.
2. **Live, and this is the actionable one.** Those packs are still on disk. Any offline re-grade
   of either run — which `evaluate-run` supports and which this project does routinely — builds
   its field from them and hands a judge the key again.

So the exposure is not only in the past: it is armed.

## What should be done

Establish the radius first: `grep` every pack in both runs for all three patterns and report the
per-stack counts, the way task 42 did. Then either re-pack, or bar re-grading.

**If you re-pack, the exclusion set must be COMPUTED, not guessed.** Task 42 established the
method and `eval/judge/repack.py` implements it: the prescribed subtraction, corroborated against
the `starter baseline` commit in the trial's work tree. Both runs are older than `wg-g4c` — check
that a baseline survives for them at all before assuming the method applies. `#104` is why:
those commits exist in no archive, and only 22 trees' baselines were preserved.

**If no baseline survives, do not re-pack.** A pack rebuilt against today's starter reclassifies
template code as authored work (#77) and would silently change what every code aspect was
reading. Marking the run and barring re-grade is the correct outcome in that case, and it closes
this task.

## What not to conclude

Do not treat `verify_blind.py` passing as evidence the key is gone. It checks the canary, the
rubric and the criterion vocabulary — the key is a trial id inside a submission's own config
file, which is a different thing. Task 42 found the key by grepping for it directly.


## WHAT THIS TICKET GOT WRONG, established 2026-08-23 while working it

**"The exposure is armed" is false, and it was this ticket's stated reason for priority.**
`field.build_pack` does not copy a pack file, it writes `anonymise.neutralise(text)`, and
`neutralise` rewrites any `g<n>_<game>__<stack>__t<n>` token to `SUBMISSION`. Applying it to
every file of all 40 stored packs in both runs leaves **0 files in which the trial id survives**,
and the 32 `telemetry.json` / `audio.json` blobs an offline re-grade would build carry no trial
id, work path or `.codex` string either. The stored packs carry the key; what a judge would be
handed does not.

That distinction is the thing to keep. **A leak in stored evidence and a leak on the live path
are two questions, and the second has to be measured on the OUTPUT of the copy** rather than by
grepping its input. This ticket grepped the input and inferred the output.

The measured outcome, recorded in `eval/RUNS.md` in the section naming both runs:

- **Radius.** 18 of 24 packs in `wg-matrix` (godot 4/6, rust 5/6, ts 6/6, unity 2/6); 6 of 16 in
  `wg-audio48` (godot 3/4, ts 3/4, rust 0/4, unity 0/4). Always exactly one file per pack, always
  `code/other/NN.json`, always the `.codex` hooks config verbatim.
- **`repack.py` refuses 24/24 and 16/16.** `wg-matrix`: no `pack.manifest` in any
  `eval/report.json`. `wg-audio48`: 12 on `files_dropped_for_length` 1-11 (pre-#69 cap), 4 on a
  missing `starter baseline` root commit.
- **The baseline is destroyed, not merely unreadable** - do not spend time trying to recover it.
  All 40 work trees are still under `$TMPDIR/wholegame-work/`, all 40 have a `.git`, **none has
  `HEAD` and none has a single loose object**; only empty `hooks/ info/ logs/ objects/ refs/`
  skeletons remain. `wg-g4c`'s 8 trees, as a control, all have `HEAD` and 87-211 objects. This is
  #45's `$TMPDIR` reaper, and it is what #104 predicted.
- **Code re-grading was already barred mechanically**, which nothing in this ticket knew:
  `build_pack(..., sees="code")` refuses all five game fields across the two runs - two on
  UNMEASURABLE pack/manifest parity, three on #62 truncation - while the same call on
  `wg-g4c`/`g4_platformer` builds 199 files.

**A separate live leak was found on the way and is `tasks/73`.** `neutralise`'s `_STACK_TOKENS`
is case-sensitive and has no rule for the bare words `cargo` or `rust`, so `CARGO_MANIFEST_DIR`,
`BEVY_ASSET_ROOT` and `crates/game` pass through untouched. 22 of the 68 stored code packs across
6 runs carry a surviving stack token, including 3 of `wg-g4c`'s 8 - and `architecture` is the one
aspect with `blind_language=True`, so it is the one this actually costs.
