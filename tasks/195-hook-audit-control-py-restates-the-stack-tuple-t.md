---
id: 195
title: hook_audit_control.py restates the stack tuple, the same second-literal class task 194 repaired in prompt_guard.py
status: todo
priority: 4
refs: eval/tools/hook_audit_control.py,eval/tools/prompt_guard.py,tasks/194
done_when: A change to wholegame_prompts.STACKS (say a temporarily renamed entry, in a temp copy) makes hook_audit_control disagree visibly - fail, or print the disagreement - instead of auditing a stale population; and its own selftest/harness still exits 0 unpiped against the pristine tree. State what must still FAIL after the change; do not merely widen an equality check that a restated literal satisfies.
---

eval/tools/hook_audit_control.py line 88 defines STACKS = ("rust", "ts", "unity", "godot") and never imports wholegame_prompts, which owns the tuple (established by task 194: prompt_guard.py held the same restated literal and now reads W.STACKS, pinned by identity at import). hook_audit_control iterates these names over eval/starters/ to audit the per-stack hooks, so a fifth stack added at the owner would leave the hook audit checking the old four while every suite and the guard moved on - and its verdicts would read clean, because the audit derives its population from its own copy, the same invisible-drift shape 194 measured. Found by the task-194 agent at handback and routed to the orchestrator rather than fixed in-ticket (the ticket scoped prompt_guard.py). Differs from 194 in one respect worth the agent attention: this file is a control harness that may not want to import the prompt suites at import time for one tuple, so the mechanism is the agent to choose - what is required is the property, not the mechanism.
