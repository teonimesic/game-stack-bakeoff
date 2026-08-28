---
id: 200
title: run-matrix and evaluate-run skills invoke verify_blind.py bare, which has exited 2 since the tool's first commit
status: done
priority: 4
refs: .agents/skills/run-matrix/SKILL.md,.agents/skills/evaluate-run/SKILL.md,eval/judge/verify_blind.py,README.md
done_when: every verify_blind invocation in .agents/skills/run-matrix/SKILL.md and .agents/skills/evaluate-run/SKILL.md is a form that exits 0-running or refuses-with-its-own-message when followed as written from the document's stated working directory, each repaired form run for real (exit 0, or the tool's own refusal printed) before committing, and the invocation form agrees with README.md's fence about frame (repo root, eval/-prefixed) unless the skill states its own frame and the stated frame is the one the command is run from. docstat.py --sweep exit 0 unpiped after. Note skill edits are safe here - these are orchestrator-facing skills, not eval/starters/**.
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/80
established_by: 'Task 200 merged as PR 80 squash. Verified against artifacts in the agent worktree at 13b8c15a, not the report: both skills new fence run verbatim from the eval frame - copy-form blind check exit 0 BLIND over 5 trial trees and 83 criterion ids; the run-matrix section 3 trial-tree form exit 0 BLIND against the one surviving real work root ~/game-research-work/wg-scene-s1ts-2026-08-25 (1 tree); in-place form python3 judge/verify_blind.py starters/*/ exit 1 RUBRIC REACHABLE on all 5 trees (the reason the copies are the form, reproduced); canary planted in an outside copy exit 1 CANARY IN TRIAL TREE naming the planted file; docstat --sweep exit 0 over 266 docs and tasks check exit 0 unpiped at head. Review rounds 3 of 5, round 3 clean (LANDED_COMMENT, no review object at final head). Pre-merge repair: the PR body still showed the round-1-rejected &&-rm cleanup form that strands 377M of copies on a red exit; corrected to the landed EXIT-trap subshell since the body is the squash commit message. Left for a decision, not filed: no standing procedure runs verify_blind --packs before subjective-layer rounds on a stored run.'
---

Found by task 197's agent while verifying the README fence (recorded in its handback; do not re-derive): .agents/skills/run-matrix/SKILL.md and .agents/skills/evaluate-run/SKILL.md both spell python3 judge/verify_blind.py with no positional argument, and the tool's argparse requires trial directories, --packs, or both - argparse exits 2 'the following arguments are required' on the bare form, and has since the tool's initial commit. verify_blind.py:225 defines paths nargs=* and :229 --packs nargs=*. The skills' address is also eval-frame (judge/verify_blind.py) while README.md's fence is now repo-root-frame after task 197, so the two documents spell the same invocation differently AND at most one of them works. Why it matters: these are the procedures a session follows to verify blinding before believing judge data - a command in the procedure that cannot run is the confidently-wrong-document class, and the run that skipped blinding verification would not notice. MEASURED by the task-197 agent; my check of the argparse confirms the required-group shape (verify before repairing - the skill files may have moved since).

## note 2026-08-28

## What the repair is, and why it is these forms (2026-08-28)

The bare invocation was argparse exit 2 ("give trial directories, --packs, or both"), measured at cwd=eval before repairing. Three working forms now exist, each run for real before landing:

- **Starter blind check (run-matrix s1, evaluate-run s0):** `( blind=$(mktemp -d); trap 'rm -rf "$blind"' EXIT; cp -R starters "$blind"/s && python3 judge/verify_blind.py "$blind"/s/*/ )` — copies of the starters scanned outside the repository, the form eval/judge/AGENTS.md (Blinding) prescribes and precampaign_smoke.py runs. Measured verbatim on the main checkout corpus: exit 0 BLIND, 5 trees, 83 criterion ids. The real starters carry 377M of untracked build dirs; the plain cp -R costs 3.6s and the scanner's SKIP_DIRS skips them, so no exclude list is needed.
- **Trial-tree blind check (run-matrix s3, new):** `python3 judge/verify_blind.py <work-root>/*/` on the work root wholegame.py build prints. Measured exit 0 against the one surviving real work root, /Users/stefano/game-research-work/wg-scene-s1ts-2026-08-25 (1 trial tree).

Two forms were rejected on measurement, do not re-derive them:

- **In place (`verify_blind.py starters/*/`)** reads CONTAMINATED exit 1, RUBRIC REACHABLE from ancestor, on all 5 trees — red on a healthy corpus (true about the path, not the question; the same measurement judge/AGENTS.md records from task 67).
- **`--packs` in evaluate-run s0** would false-alarm every fresh run: judge packs are built during evaluate (anonymise.build_pack via judge.py), so before s1 they do not exist and the tool fails closed with "pack path does not exist" exit 1 — the crying-wolf shape its own docstring warns about. The pack gate remains operator-run, as RUBRIC.md documents.

Red controls: a canary planted in an outside-repo copy reads CANARY IN TRIAL TREE exit 1 (the same form that went green on clean copies); the bare form's exit 2 is the broken state.

## Review rounds (3 of the 5-round ceiling, round 3 clean)

- Round 1, 2 comments, both acted on: conditional `&& rm` never ran on CONTAMINATED (stranding a measured 377M per red round) — fixed with status-preserving cleanup; and the prose restated measured facts that live in eval/judge/AGENTS.md — trimmed to a pointer (second-source-of-truth, #38 discipline).
- Round 2, 1 comment: asked for an exit-trapped subshell. Acted, after measuring the proposed mechanism instead of arguing: a subshell EXIT trap fires in bash AND zsh on normal exit and on SIGINT death (both probes returned REMOVED). The trap + subshell shape also made the line simpler — one physical line, no ec re-raise, and no `exec` (which would replace the subshell and skip the trap). Measured: green exit 0, red shape exit 1, SIGINT shape DIR REMOVED.
- Round 3: "No actionable comments" on the fix diff.

Left unfiled, for the orchestrator to weigh: no procedure runs `verify_blind.py --packs` before subjective-layer rounds on a stored run (the packs are what the judge reads). RUBRIC.md documents the gate; no skill invokes it. Small, well-scoped, possibly already covered by blurb_selftest for scenes — do not build without reading that first.

PR: https://github.com/teonimesic/game-stack-bakeoff/pull/80
