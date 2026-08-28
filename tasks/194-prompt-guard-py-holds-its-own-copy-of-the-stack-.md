---
id: 194
title: prompt_guard.py holds its own copy of the stack tuple instead of reading wholegame_prompts, which owns it
status: done
priority: 3
refs: eval/tools/prompt_guard.py,eval/suites/wholegame_prompts.py
done_when: 'prompt_guard.py no longer holds a second literal: read STACKS from wholegame_prompts (W.STACKS) or assert equality at import, fail-closed. Add the check that would catch a reintroduced copy: a selftest case or assertion that the module attribute is the imported object, so a future literal edit fails rather than drifts. python3 eval/tools/prompt_guard.py --snapshot --diff (or the invocation the module documents) and its selftest exit 0 unpiped afterward.'
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/71
established_by: 'Verified against artifacts: scope from merge-base c77f2f8 is prompt_guard.py + new prompt_guard_control.py only. The fix reads W.STACKS with an if/raise identity guard - not an assert - and I reproduced the property the review round added myself: planted the literal into a temp copy of the fixed file and ran both python3 and python3 -O --identity, exit 1 under both (asserts would have exited 0 under -O). Guard pristine exits 0 bare and under -O. Control harness reproduced: 27 rows as declared (15 mutants red, 5 variants green, 4 disarmed green, 2 pristine green, 1 filesystem pin), exit 0. Review verdict at head 7e1d342 verified by running pr_review_state.py myself: LANDED_COMMENT, 0 unresolved, 0 in flight; mergeable exit 0; CI gates+controls green at that head. Routed item adjudicated: hook_audit_control.py:88 does hold the same literal with no import of the owner - same defect class, filed as task 195 rather than folded into this merge (different file, own ticket). Merged squash as 0e50590; worktree and branch cleaned.'
---

eval/tools/prompt_guard.py line 44 defines STACKS = ("rust", "ts", "unity", "godot") two lines below "import wholegame_prompts as W", and never reads W.STACKS. Every other consumer takes the tuple from wholegame_prompts: wholegame.py reads P.STACKS for starters, iteration and CLI choices, and scene_prompts.py imports STACKS from it and re-exports. So prompt_guard carries the only unpinned copy of a value the module beside it owns. prompt_guard is the tool that asserts prompt identity across stacks; if a fifth stack is added in wholegame_prompts, prompt_guard would go on rendering and identity-checking the old four and report a clean population of the wrong size — the drift is invisible in its own output because the count it prints is derived from the copy. This is the rule-12 corollary spelled in AGENTS.md for paths, applied to a value: spelled in two files with nothing asserting them equal. Found in the 2026-08-28 cleanup pass over eval/suites/wholegame_prompts.py and its readers.

## note 2026-08-28

## What the fix is, and why it is shaped that way (2026-08-28)

`prompt_guard.py` now assigns `STACKS = W.STACKS` and enforces it with
`if STACKS is not W.STACKS: raise AssertionError(...)`. Two properties are load-bearing:

- **Identity, not equality.** A restated tuple is `==` the owner's forever and `is` only
  on the day it is written. Measured on the pre-fix file: `prompt_guard.STACKS ==
  W.STACKS` True, `is` False, while `scene_prompts.STACKS is W.STACKS` True — the guard
  was the one module holding a non-identical copy. No value check could ever have caught
  the drift; the population the guard prints is derived from the copy, so its own output
  would have stayed clean.
- **`if`/`raise`, not `assert`.** CodeRabbit's round-1 Major, measured true before
  acting: with the literal planted into a temp copy of the guard, `python3` exited 1 but
  `python3 -O` printed `ok:` at exit 0 — the fail-closed check stripped by the
  interpreter on exactly the input it exists to catch. The raise survives `-O` and
  `PYTHONOPTIMIZE`. Do not simplify it back to an assert.

## The control (prompt_guard_control.py)

Two rows pin it. `stack-literal-restated` (MUTANT) plants the literal over
`STACKS = W.STACKS` and requires the AssertionError at exit 1;
`disarmed-stack-identity` (DISARMED) replaces the `if` line with `if False:` while
keeping the plant and requires the guard green — proof the red row is the guard and not
the literal. Both rows read BROKEN (anchor count 0) against the pre-fix guard, harness
exit 1, so the failing state was established before the fix. If you reword the guard in
`prompt_guard.py`, the anchors `STACKS = W.STACKS` and `if STACKS is not W.STACKS:` in
the control break loudly — update both together.

## Verified (all unpiped)

guard bare exit 0; `--diff eval/suites/rendered` exit 0 (24 prompts match);
`--snapshot`/`--diff` roundtrip in a temp dir exit 0 both halves; `--identity` exit 0,
population line unchanged; control harness 27 rows as declared exit 0;
`docstat.py --sweep` exit 0; `tasks.py check` exit 0. Round-2 probe: planted literal
exits 1 under both `python3` and `python3 -O`; pristine guard green under `-O`.

## For the orchestrator

- **No finding number claimed.** The change alters no measurement output.
- **Same literal elsewhere:** `eval/tools/hook_audit_control.py` line 88 also holds
  `("rust", "ts", "unity", "godot")`, but it never imports `wholegame_prompts` — it is a
  self-contained hook-audit harness, not a consumer of the prompt modules, and the
  ticket scoped prompt_guard.py. Route as its own decision (fix or declare the
  self-containment deliberate).
- PR: #71, round 2 came back clean (LANDED_COMMENT), controls workflow in progress at
  handback.
