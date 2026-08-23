---
established_by: eval/runs partitioned by regenerability: 368,571 files / 138.146 GB total, evidence 14,192 files / 1.109 GB. Copied to /Users/stefano/game-research-evidence and verified by reading the destination back — SHA-256 matched on both sides for all 14,192 files, 728 harness JSON records parsed, 89/89 submission tarballs extracted (25,642 members decompressed), and shasum -c on MANIFEST.sha256 exited 0. Verifier pinned red by deleting one file, truncating one tarball and flipping 100 bytes in a JSON: tiers 1, 2 and 3 each caught their own, exit 1. Classifier controlled against real git on 7,461 paths across 11 fixtures, plus 4 mutants (3 were inert until a synthetic fixture reached their branches — finding #90). Also found and copied 2 work trees in ~/game-research-work/wg-g4 with no submission tarball anywhere. CAVEAT: the copy is SAME-DISK and is documented in eval/PROTOCOL.md and the destination README as NOT a backup.
id: 17
status: done
priority: 2
title: Back up eval/runs (the evidence) and keep the git mirror current
refs: https://github.com/teonimesic/game-stack-bakeoff, eval/RUNS.md
done_when: the ~1.2 GB evidentiary core of eval/runs/ has a verified second copy — verified by reading files back, not by a copy's exit code — and eval/PROTOCOL.md names what is evidence, what is build output, and when to re-sync
---

This project measures how well coding agents build whole games in four stacks. Two things exist
and they have very different backup needs.

THE PRODUCT is now in git and pushed: https://github.com/teonimesic/game-stack-bakeoff
(private, MIT, 597 files, ~11 MB). Four templates, the harness, the docs, findings, tasks and
skills. Committing is cheap and should happen whenever a batch of work lands.

THE EVIDENCE is not, and cannot be. `eval/runs/` is **129 GB** — every stored submission,
frames, telemetry, audio, judge rounds and per-trial records. It is excluded by `.gitignore`
and it is the part that is genuinely irreplaceable: the templates can be rewritten, a matrix
costs ~$420 and several days to reproduce, and the judge rounds behind the findings cannot be
reproduced at all because the model and the harness have both moved since.

RIGHT NOW IT EXISTS IN EXACTLY ONE PLACE. A disk failure loses every number in
`eval/FINDINGS.md` that anyone might later want to check.

WHAT TO DO:

1. Copy `eval/runs/` to a second physical location — external disk or cloud object storage.
   Not another directory on the same disk, which protects against nothing that actually happens.
2. **Verify by reading files back**, not by trusting the exit code of the copy. Open several
   `report.json` and `submission.tar.gz` from the copy and confirm they parse and extract.
   This project has a rule about exit codes for a reason; a copy that reports success and
   wrote nothing is the same defect class as a check that passes and measures nothing.
3. Prefer an incremental tool (`rsync -a --delete`, or `restic`/`borg` if dedup matters —
   the per-trial starter copies are highly redundant, so dedup may cut this dramatically).
4. Add to `eval/PROTOCOL.md`: commit the product after a batch of work; re-sync the evidence
   after any run completes, before the work root is reclaimed (task 10).

WHAT NOT TO DO: do not try to push `eval/runs/` to GitHub, with or without LFS. 129 GB is far
past what that is for, and splitting evidence across two backup mechanisms means neither is
known to be complete.

CHECK FIRST whether `~/game-research-work` (55 GB, mostly cargo `_targets`) needs backing up at
all — it should not, since every submission is archived as `submission.tar.gz` under
`eval/runs/`. Confirm that holds for every trial before excluding it; task 10 found `wg-g4` has
6 work trees but only 4 tarballs, so the mapping is not automatic.

MEASURED 2026-08-22 — THE 129 GB FIGURE WAS WRONG, AND THE TASK IS MUCH SMALLER

`eval/runs/` is 138 GB, but **99.2% of it is not evidence**:

    other (cargo build output)  136.99 GB   328,402 files   <- 66 GB in debug/deps alone
    submission tarballs           0.80 GB        89 files
    diffs / logs / text           0.16 GB     5,895 files
    JSON records                  0.11 GB    30,210 files
    frames (PNG)                  0.08 GB     2,610 files
    judge packs                   0.01 GB     1,364 files   <- rebuildable from tarballs

The bulk is `debug/deps` and `debug/incremental` from old `t1_rally`/`t2_net`/`t3_powerup`
spec-change trials — Rust compiler output that was never evidence and regenerates from source.

**The evidentiary core is ~1.15 GB**: every score, every judge round, every diff, every
submission tarball, every frame. That fits anywhere — including a second git repository, or
alongside this one, without any of the LFS/object-storage machinery the original task assumed.

THE TASK IS THEREFORE:

1. Establish the boundary precisely — what in `eval/runs/` is evidence and what is build
   output. Do it by rule, not by listing directories: an enumeration misses the next case,
   which is this project's most-repeated defect.
2. Copy the evidentiary core to a second location and **verify by reading files back**: parse
   several `report.json`, extract several `submission.tar.gz`. Never trust a copy's exit code.
3. Only then consider reclaiming the 137 GB of build output — but coordinate with task 10,
   and note that at least one warm work tree was worth keeping while task 07 was open.
4. Record the boundary in `eval/PROTOCOL.md` so the next run does not re-accumulate it silently.

DO NOT delete anything before step 2 is verified. The reason the core is worth protecting is
precisely that a matrix costs ~$420 and days to reproduce, and the judge rounds cannot be
reproduced at all — the model and harness have both moved since they ran.
