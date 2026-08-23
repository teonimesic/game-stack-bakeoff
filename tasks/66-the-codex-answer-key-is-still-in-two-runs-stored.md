---
id: 66
title: The .codex answer key is still in two runs' stored judge packs, and a re-grade would read it
status: in_flight
priority: 2
refs: 'eval/FINDINGS.md #83, eval/judge/field.py build_pack, eval/judge/repack.py, tasks/42'
done_when: wg-matrix and wg-audio48 either hold packs with no trial-id, work-root or .codex pattern in any file, verified by grep over every pack in both runs, or are marked in eval/RUNS.md as carrying the key with the per-stack counts stated and re-grading them barred
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
