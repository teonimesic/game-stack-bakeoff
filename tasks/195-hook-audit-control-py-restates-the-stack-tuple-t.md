---
id: 195
title: hook_audit_control.py restates the stack tuple, the same second-literal class task 194 repaired in prompt_guard.py
status: done
priority: 4
refs: eval/tools/hook_audit_control.py,eval/tools/prompt_guard.py,tasks/194
done_when: A change to wholegame_prompts.STACKS (say a temporarily renamed entry, in a temp copy) makes hook_audit_control disagree visibly - fail, or print the disagreement - instead of auditing a stale population; and its own selftest/harness still exits 0 unpiped against the pristine tree. State what must still FAIL after the change; do not merely widen an equality check that a restated literal satisfies.
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/73
established_by: 'Verified against artifacts: scope from merge-base 561f0a4 is hook_audit_control.py only (+86/-11). Battery reproduced myself in the branch worktree at de02293: pristine 39 ok / 0 FAILED exit 0 under python3 and python3 -O; --stack bevy refused exit 2; owner+bevy probe in a temp tree (eval/ minus runs) exits 1 with 39 ok / 2 FAILED - printed named rows, not silence (was exit 0 with the new stack in no line); planted literal AssertionError at import under both interpreters, stderr-checked so the exit-1 is the guard and not an import error (my first probe attempt hit ModuleNotFoundError from an incomplete temp tree - discarded and redone with the full closure). The review round-1 WARM_GUARD_DIR and partial-population findings were the agent accepting reviewer-correct evidence against its own round-0 claims; the STARTERS planted-drop case was an exit-0 silent pass before the fix. Review verdict at de02293 via pr_review_state.py: round 2 clean. CI green at the updated head; merged by --auto as bbeec59 after the branch update. Worktree and branch cleaned.'
---

eval/tools/hook_audit_control.py line 88 defines STACKS = ("rust", "ts", "unity", "godot") and never imports wholegame_prompts, which owns the tuple (established by task 194: prompt_guard.py held the same restated literal and now reads W.STACKS, pinned by identity at import). hook_audit_control iterates these names over eval/starters/ to audit the per-stack hooks, so a fifth stack added at the owner would leave the hook audit checking the old four while every suite and the guard moved on - and its verdicts would read clean, because the audit derives its population from its own copy, the same invisible-drift shape 194 measured. Found by the task-194 agent at handback and routed to the orchestrator rather than fixed in-ticket (the ticket scoped prompt_guard.py). Differs from 194 in one respect worth the agent attention: this file is a control harness that may not want to import the prompt suites at import time for one tuple, so the mechanism is the agent to choose - what is required is the property, not the mechanism.

## note 2026-08-28

## Fix, and the two review rounds (2026-08-28)

`hook_audit_control.py` now assigns `STACKS = W.STACKS` from `wholegame_prompts`, pinned
by identity with an if/raise at import (survives `python3 -O` and `PYTHONOPTIMIZE`;
equality cannot catch a restated literal, which is == the owner's forever). Same shape
as task 194 in prompt_guard.py; that precedent is why no DECISIONS.md entry was added.

Three further changes the property forced, all in the same file:

- `check_build_trial` derives its fixture stack (`fixture = STACKS[0]` after a full
  agreement check) instead of hardcoding "rust". On the pre-fix file a renamed owner
  entry KeyError'd on that hardcoded line BEFORE any row printed, so even the failure
  said nothing about the population.
- `check_stack` and `check_grader_view` each return a FAILED row when the stack named
  by the owner has no `eval/starters/<stack>/` hook, and now also when it has a hook
  but no `WARM_GUARD_DIR` entry (review round 1, Major: that KeyError was reachable
  and discarded the summary). The rows name the owner relationship, so the
  disagreement is readable where it appears.
- `check_build_trial` requires `wholegame.STARTERS` to agree with the owner on every
  stack, BOTH directions, before substituting anything (review round 1, Major: the
  first version failed only on no-overlap, and a planted `P.STACKS[1:]` derivation
  passed at 39 ok / 0 FAILED). The disagreement is a RETURNED row, not a raise --
  main() catches nothing, and a raise trades the whole summary for a traceback.

`WARM_GUARD_DIR` stays a starter-owned literal on purpose: it maps stack -> warm-guard
directory, a property of the hooks, and the owner holds no such data. It is now
guarded at both call sites, so "unreachable" is no longer the claim -- every reachable
path prints a row. The seeded TSV rows in `check_harness` spelling \trust are inert
parser fixtures (the stack column is not asserted) and were deliberately left.

## Probes, all against temp copies, all unpiped

Pre-fix broken state: owner + fifth stack -> exit 0, 39 ok / 0 FAILED, new stack in no
line (the ticket's invisible drift, verbatim); owner rename -> exit 1 by the unrelated
fixture KeyError, audit rows unprinted. Round-1 broken states: bevy WITH a starter hook
-> KeyError 'bevy', rows unprinted; STARTERS planted to drop rust -> exit 0, silent pass.

Post-fix battery: pristine 39 ok / 0 FAILED exit 0 under python3 and python3 -O;
owner +bevy (no starter) 39 ok / 2 FAILED; rust->rusty 31 ok / 2 FAILED, trial row
builds as g1_pong__rusty__t0 from the derived fixture; bevy-with-hook 39 ok / 2 FAILED
naming WARM_GUARD_DIR, 0 KeyErrors; STARTERS drift 35 ok / 1 FAILED naming the
disagreement, 0 tracebacks; planted literal AssertionError at import under python3 and
python3 -O; disarmed guard with plant kept 39 ok / 0 FAILED (the red is the guard);
--stack godot 16 ok exit 0; --stack bevy refused exit 2. docstat --sweep and tasks.py
check exit 0. PR #73 review round 2 clean (LANDED_COMMENT; round-1 threads all
answered "confirmed"/"Verified" by the reviewer), gates and controls CI green at head
de02293. One practical note: the probe scripts use grep -c whose 0-match exit 1 killed
a set -e battery on a WANTED zero -- count with python, not grep -c, under set -e.

Do not re-derive: the owner of the tuple is wholegame_prompts.STACKS; wholegame.STARTERS
is derived from it keyed by it; a finding number was not taken (no measurement output
changed -- the pristine 39-row verdict is byte-identical before and after).
