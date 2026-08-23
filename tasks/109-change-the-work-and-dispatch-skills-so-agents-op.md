---
id: 109
title: Change the work and dispatch skills so agents open PRs and address a CodeRabbit review before handing back
status: todo
priority: 2
refs: BLOCKED BY tasks/108 - do not start until a real PR here has received a CodeRabbit review. .claude/skills/work/SKILL.md, .claude/skills/dispatch/SKILL.md, AGENTS.md
done_when: work/SKILL.md and dispatch/SKILL.md describe the PR flow end to end including how an agent waits for a review, how it decides which recommendations to act on, and what it does when the review never arrives; the flow has been run end to end on at least one real task and the resulting PR is cited; and the failure modes are stated with what an agent does in each rather than left to be re-derived
---

The operator specified the flow on 2026-08-23: agents should pick up tasks, then submit PRs, then trigger CodeRabbit reviews, then address whatever CodeRabbit recommends, then submit it as ready to be merged for the orchestrator to verify and merge. Today agents hand back a raw branch and the orchestrator merges it with git merge --no-ff; no pull request is ever opened and nothing external reviews the work. The two skills are the only place this workflow is written down, so this is where it changes.

WHAT THIS IS

Two skills describe how a queued task becomes merged work:

- `.claude/skills/work/SKILL.md` — what a dispatched agent follows
- `.claude/skills/dispatch/SKILL.md` — what the orchestrator follows

Today the flow is: orchestrator makes the ticket current → launches an agent in a worktree →
agent commits to a branch and reports → orchestrator verifies against artifacts, merges with
`git merge --no-ff`, runs the gates, pushes. **No pull request is opened. Nothing external reviews
anything.**

THE FLOW THE OPERATOR SPECIFIED, 2026-08-23

Quoted, because this is the specification and not a paraphrase:

> *"agents should pick up tasks, then submit PRs, then trigger code rabbit reviews, then address
> whatever coderabbit recommends, then submit it as ready to be merged for you to verify and
> merge"*

> *"it should update the ticket status accordingly, so tasks can be in todo, in progress, in
> review (PR open and coderabbit review loop), then 'in testing' (waiting for you to verify) and
> finally done when merged"*

So there are **three** changes, and they are separable:

1. the agent opens a PR instead of handing back a bare branch
2. the agent waits for a CodeRabbit review and addresses it before handing back
3. the **status vocabulary grows from three values to five**

THE STATUS CHANGE IS A CODE CHANGE, NOT A DOCUMENTATION CHANGE

`eval/tools/tasks.py:83` reads:

    STATUSES = ("open", "in_flight", "done")

Every one of these has to move together, and **`tasks.py check` fails any file whose status is not
in `STATUSES`** (line 698) — so a half-done rename breaks the queue lint for every agent at once:

| site | what it does |
|---|---|
| `tasks.py:83` `STATUSES` | the vocabulary, and what `check` validates against |
| `tasks.py:479` the `mark` dict | `[ ]` / `[~]` / `[x]` in the listing — needs a glyph per state |
| `tasks.py:492` | the summary line, which counts `in_flight` by name |
| `tasks.py:761` | `list --status` choices |
| `tasks.py:757-780` the subcommands | today `start` → `in_flight` and `done` → `done`. Five states need transitions, and `done` takes a mandatory `evidence` argument — decide what the new ones require |
| `eval/tools/heartbeat.py:121,178` | counts `open`/`in_flight`/`done` and emits `tasks_inflight`. **The heartbeat compares against the previous hour**, so silently renaming a counted key makes an interval read as movement that did not happen |
| `.claude/skills/dispatch/SKILL.md:76` | tells the orchestrator to confirm `in_flight` |
| `.claude/skills/tasks/SKILL.md:197` | the verify step, by name |

**Existing tickets carry the old values.** There are ~107 files in `tasks/`. Decide whether
`open`/`in_flight` are renamed or kept as aliases of the new names, migrate accordingly, and run
`tasks.py check` unpiped after — a queue where some files say `open` and the tool says `todo` is a
lint failure for everyone.

A mapping that keeps the change small, offered as a starting point rather than a decision:
`open`→`todo`, `in_flight`→`in_progress`, plus new `in_review` and `in_testing`, `done` unchanged.
**Whatever you choose, `tasks_control.py`'s round-trip direction must still pass** — it asserts
task files survive a status change byte for byte.

WHAT SHOULD BE DONE

**Order matters.** The status change is independently useful and can land first; the PR flow
depends on `tasks/108`. If 108 has not established that a review actually arrives, do the status
half, land it, and say the PR half is blocked — **do not** write a skill instructing agents to
wait for something unproven.

For the PR half, the skills must answer these, because an agent that has to invent an answer will
invent a different one each time:

- **How does the agent open the PR?** It works in a git worktree with `gh` available and
  authenticated. Name the command, the base branch, and what goes in the PR body — the ticket's
  `done_when` and what the agent established are the obvious candidates, and the existing
  commit-message rule applies: `gh pr create --body-file`, never `--body` with backticks (#80).
- **How does it trigger and wait for the review?** CodeRabbit reviews automatically on PR open;
  whether an explicit trigger is needed is `tasks/108`'s finding to supply. **Waiting is the part
  most likely to go wrong.** Name the poll command, a bounded wait, and what the agent does when
  it expires. An unbounded wait is an agent that never reports.
- **Which recommendations does it act on?** This project's standard is higher than "the reviewer
  said so". A CodeRabbit suggestion that contradicts a rule in `AGENTS.md` or a recorded
  `DECISIONS.md` entry is **wrong, and the agent should say so in the PR thread rather than
  comply.** Write that down. An agent that silently applies every suggestion will eventually
  apply one that loosens a test — which the global instructions forbid outright.
- **What does "ready to be merged" look like to the orchestrator?** The operator wants to verify
  and merge. Say how the orchestrator can tell a PR is at that point without reading the whole
  thread — the `in_testing` status is the obvious signal, and the PR should be findable from the
  ticket and vice versa.

For `dispatch/SKILL.md`, step 4 currently opens with `git merge --no-ff task-<id>-<slug>`. Decide
whether the orchestrator merges the PR through `gh pr merge` or keeps merging locally, and say
which — **the whole conflict table in step 4 is written for local merges** and does not
automatically survive a switch.

WHAT NOT TO CHANGE

- **The verification standard.** `dispatch/SKILL.md` says *verify against the artifacts, not
  against the report* and *run its controls yourself*. A CodeRabbit review does not replace that
  and must not be allowed to read as if it does — it is a second opinion on the code, not a
  measurement of the claim. **Say this explicitly in the skill**, because "it passed review" is
  exactly the shape of a mechanism that runs and reports success.
- **The one-line dispatch rule.** The prompt stays `/work <id>`; everything an agent needs stays
  in the ticket.
- **`eval/starters/*/`** — untouched, as always.

WHAT EACH OUTCOME MEANS

- **The flow runs end to end on a real task** — done. Cite the PR and the ticket.
- **The status half lands and the PR half is blocked on 108** — a good partial result. Land it,
  say so, and leave this task open with the blocker named.
- **The waiting step turns out to be unworkable** (no reliable way to know a review has finished)
  — that is a real finding about the design, not a failure. Record what you measured, and propose
  what the orchestrator does instead.
