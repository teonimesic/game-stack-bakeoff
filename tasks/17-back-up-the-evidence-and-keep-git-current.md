---
id: 17
status: open
priority: 2
title: Back up eval/runs (the evidence) and keep the git mirror current
refs: https://github.com/teonimesic/game-stack-bakeoff, eval/RUNS.md
done_when: eval/runs/ has a verified copy on a second physical location with a restore that has been tested by reading files back, and eval/PROTOCOL.md names when to commit and when to re-sync the evidence
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
