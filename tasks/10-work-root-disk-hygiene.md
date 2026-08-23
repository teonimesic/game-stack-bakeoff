---
established_by: eval/PROTOCOL.md gained a post-run reclaim section. Measured first: 55G across three g4 runs (16G/14G/24G) on a volume at 87%. Rule is per-TREE not per-run, and that distinction is load-bearing: wg-g4 has 6 work trees but only 4 archived tarballs because it was stopped mid-build, so g4_platformer__unity__t0 (177M) and __t1 (40M) have NO submission.tar.gz - a rule phrased 'delete work trees of finished runs' would have destroyed them, one phrased 'delete a tree whose own tarball exists' does not. Includes the verification loop, NEVER-delete-eval/runs, and the caveat that wg-g4c's warm unity trees must be kept while task 07 is open because warm-vs-cold is what makes #66 provable - a warm build cache is evidence, not waste, being the only copy of a state the archive cannot reconstruct. SUPERSEDED IN PART, 2026-08-23, by eval/FINDINGS.md #104: the rule this task established - delete a tree whose own tarball exists - was tested by task 42 and would have destroyed the trees it cleared. submission.tar.gz carries no .git, so a work tree's root commit named starter baseline is the only record anywhere of the starter the agent was actually given, and it is what let task 42 compute wg-g4c's exclusion set instead of guessing it. All eight wg-g4c trees had tarballs and the rule declared every one safe to delete. The 22 surviving trees' baselines were preserved before anything was reclaimed, which was sequencing luck and not the rule working. The condition in eval/PROTOCOL.md is now BOTH the tarball AND a preserved starter baseline; read that file, not this string, before deleting a tree. The warm-tree caveat is also restated there: its trigger was task 07 being open, task 07 closed on 2026-08-23, and a task closing is not a decision to destroy the only reproduction of finding #66.
id: 10
status: done
priority: 4
title: Add a disk-reclaim step after a run
refs: eval/PROTOCOL.md
done_when: eval/PROTOCOL.md has a post-run reclaim step that names what is build output and what is evidence
---

This project measures how well coding agents build whole games in four stacks
(Rust/Bevy, TypeScript/three.js, Unity, Godot). Submissions are graded in three tiers:
tier 1 programmatic checks, tier 2 a scripted play-bot, tier 3 six LLM-judged 'aspects'
(architecture, idiomatic, fun, fun_frames, ux, audio) that score eight anonymised
submissions side by side as a 'field'. Tier 3 currently has weight 0.00.

THE SITUATION: trials build in `~/game-research-work/<run>/<trial>/`, outside the repo, so that
the artifact under measurement is durable and not in a temp directory the OS reaps.

THE PROBLEM: nothing ever cleans it. It currently holds 55G across three runs, of which about 46G
is `_targets` — cargo build output, roughly 15G for a single Rust trial. `eval/PROTOCOL.md` has no
reclaim step, so it grows by around 24G per matrix.

WHY IT IS WORTH DOING BEFORE IT BITES: a run that fails partway through because the disk filled
would present as a harness bug, and this project has already spent days tracing failures whose
real cause was environmental (a pegged system daemon, a temp directory being reaped).

WHAT TO DO: add a post-run step to `eval/PROTOCOL.md` that distinguishes clearly:
  - SAFE to delete: `_targets/` build output, and work trees of runs whose submissions are already
    archived as `submission.tar.gz` under `eval/runs/<run>/artifacts/`.
  - NEVER delete: anything under `eval/runs/` — that is the evidence.
One caveat worth recording: warm work trees were what made #66 provable (Unity's lint answers
differently warm versus cold), so keep at least one warm tree while that task is open.
