---
id: 113
title: a dispatched agent cannot write what it learned back into a ticket BODY
status: open
priority: 3
refs: ''
done_when: tasks.py grows a subcommand that appends a section to a ticket body and writes it to the queue in the MAIN checkout, exercised from a real agent worktree in eval/tools/tasks_control.py direction 2 alongside add, with the round-trip row proving the rest of the file is byte-identical afterwards; or, if a body append is judged wrong, the work skill and AGENTS.md are corrected to name where a dispatched agent's learnings actually go and the two tickets that used established_by are cited as the precedent
---

The work skill says: 'Update the ticket with what you learned - anything the next agent would otherwise re-derive belongs in the file.' From an agent worktree there is no way to do it. tasks.py has next, show, start, done, list, add, check and nothing that appends to a body; the worktree copy of tasks/NNN-*.md is a git-tracked file whose main-checkout twin is edited concurrently by tasks.py start/done, so committing an edit to it on a task branch invites a merge conflict with a file the merge is also rewriting; and an Edit aimed at the shared checkout is refused by worktree isolation. Both tasks 105 and 106 hit this and both did the same workaround - emptied everything into the established_by string, which is one unbroken line of prose in YAML frontmatter, cannot contain a backtick (#80), and is not where the next agent looks. That is a rule in an always-invoked skill that cannot be obeyed, which AGENTS.md classes as the rule being unusable as written rather than as the agents being careless. Note what the fix is NOT: relaxing the isolation guard. The queue resolving to the main checkout is deliberate (#94).
