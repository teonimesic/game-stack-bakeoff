---
name: dispatch
description: "Send one queued task to an agent, and take its branch back. Covers making the ticket current before dispatch, the launch itself, and verifying and merging the result. Invoked as /dispatch <id>."
when_to_use: "You are orchestrating and want work started on a queued task; an agent has reported and its branch needs verifying and merging; the queue is idle and the heartbeat says to pick something."
argument-hint: "<task-id>"
---

# Dispatch one task

**Authoritative files: `tasks/<id>-*.md` (the ticket), `.claude/skills/tasks/SKILL.md` (the
queue), `.claude/skills/work/SKILL.md` (what the agent will follow).** If this skill and any of
those disagree, they win and this skill is the bug.

> **You may not put task-specific instructions in the agent's prompt.** The prompt is
> `/work <id>` and nothing else. Anything the agent needs to know goes in the **ticket**, before
> you launch. A brief in a message dies with the session, and on 2026-08-23 roughly 1,500 words
> of real constraints were dispatched that way and had to be retrofitted into seven tickets.
>
> **If you catch yourself typing the constraint, that is the signal the ticket is not ready.**

---

## 1. Make the ticket current — this is the actual work of dispatching

Read the ticket in full: `python3 eval/tools/tasks.py show <id>`. Then ask what has changed since
it was filed, and **write the answers into the file**.

| Check | If it has moved, put in the ticket |
|---|---|
| Does anything it *assumes* still hold? | The correction, dated, and what it now implies |
| Has a **dependency appeared** since filing? | Which file, what it forbids, and who created it |
| Has a peer's result landed that bears on it? | The measurement itself, never a pointer to a conversation |
| Is its `done_when` still reachable and still right? | Rewrite it, and say why it moved |
| Did an earlier agent hand back knowledge? | Append it under a dated heading |
| Do its **`refs`** still resolve? | Fix them — a renumbered finding still resolves and now means something else |

Then hold the ticket to the standard in the `tasks` skill: **a stranger in a fresh session, with
no memory of why this exists, must be able to start it and know when to stop.** Concretely, before
you launch, the ticket must answer:

1. **What is this thing?** — define the component before naming its problem.
2. **What is wrong, and how do we know?** — the defect *with its measurement*.
3. **Why does it matter?** — what conclusion is unsafe while it stands.
4. **What should be done?** — the concrete first move, naming files.

And where they apply: what **not** to conclude; what each outcome would mean, so a null result
closes it; and any regime boundary the work would cross.

**A ticket that only you could work is not a ticket.** Fix it now, in the file — the next agent,
and every future reader, gets it for free.

## 2. Check it is safe to run now

- **Dependencies.** The ticket's `refs` may say "blocked by". Do not launch behind an unmet one.
- **File conflicts.** List what your running agents are touching. Two agents editing the same
  document is the one conflict worth spending effort to avoid — especially in a file that states
  what is true *now*. If the ticket collides, either wait or write the scope limit **into the
  ticket**.
- **Shared, non-branchable state.** `eval/runs/`, the operator's machine, anything outside the
  repo: only one agent at a time, and say so in the ticket.
- **Irreversible or outward-facing work** — deleting evidence, spending money, anything touching
  the operator's machine — is **not** dispatchable on your own authority. Ask first.

## 3. Launch

`Agent` tool, and only these settings:

| | |
|---|---|
| `prompt` | `/work <id>` — exactly this, nothing appended |
| `model` | `opus` — the queue is the project's reasoning about its own instrument |
| `isolation` | `worktree` |
| `subagent_type` | `general-purpose` |
| `description` | `Task <id> — <a few words>` |

Then `python3 eval/tools/tasks.py` to confirm it shows `in_flight`, and keep dispatching. **Never
leave the queue idle behind one item** — a task in the queue was authorised when it was filed.

## 4. Take the branch back

When the agent reports, **verify against the artifacts, not against the report.** Run its
controls yourself; a result you have not reproduced is a claim.

```bash
git add tasks/ && git commit -m "Queue: agents' status writes through the shared queue"
git merge --no-ff task-<id>-<slug>
```

The queue commit comes first because agents close tasks in the **main** checkout, and an
uncommitted `tasks/` blocks the merge.

**Conflicts you will meet every time, and how they resolve:**

| Conflict | Resolution |
|---|---|
| `eval/FINDINGS.md` range line | Keep one, then set it to the real highest number |
| Two findings with the same number | The already-merged one keeps it; renumber the incoming one **in the body, the index row, and every citation** |
| Appended sections in `RUNS.md`, `IMPROVEMENTS.md`, `CLEANUP-LOG.md` | Keep both |
| The same fix made twice | Take the better one, and say in the commit why |
| **Two branches added code to one file** | Keeping both sides is right and does not mean the result parses. A nested marker whose outer pair was already consumed, and two halves of one statement each ending differently, both surface as `SyntaxError`, not as a conflict. Parse the file before you trust the merge |
| **Both sides right in the same region** | Neither `--ours` nor `--theirs`. Merge by hand and say what each contributed — on 2026-08-23 `DECISIONS.md` held a withdrawal-register sentence on one side and a corrected cost figure on the other, and taking either wholesale would have discarded a real result |

Then, unpiped: `docstat.py --sweep`, `docstat.py --renumbered`, `tasks.py check`. Renumbering
creates stale citations that still *resolve* — `--renumbered` is what finds them.

Finally: `git worktree remove --force`, `git branch -d`, `git push`, and write a commit message
that records **what was established and what it cost**, not what was changed. Use `git commit -F`
with a file: backticks in `-m` are executed by the shell and silently strip text (#80).

## 5. Go back to step 1 before you report

**A merge is not the end of the loop. It is the middle of it.**

The moment a branch is merged, ask the queue what is open — and dispatch it, **before** writing
a word to the operator. Reporting first is how the queue goes idle, because a report reads like
a stopping point and the next thing to happen is whatever the operator says.

This has failed **twice on 2026-08-23**, both times with the same shape: a wave of agents
reported, every branch was merged and verified carefully, a summary was written — and six
authorised tasks sat untouched until the operator asked why nothing was running. The rule *never
leave the queue idle* was already in step 3 and did not fire, because it reads as advice about
dispatching and the failure happens after merging.

```bash
python3 eval/tools/tasks.py        # open count, every time you finish a merge
```

If that number is above zero and no agent is running, **you are the bottleneck.** Dispatch, then
report — and say in the report what is now in flight, so the state is visible without asking.

The two legitimate reasons not to dispatch an open task, and they are the only two:

- it is **blocked** by an unmet dependency in its `refs`, or
- it needs a decision that is **not yours** (step 2's last bullet) — in which case ask *and*
  dispatch everything else. **Never idle a queue behind one item.**

## 6. Improve this skill as you use it

**When a dispatch goes wrong, the defect is here or in the ticket — not in the agent.** If you had
to explain something in a message, put it in a ticket and add the case to the table in step 1. If a
merge surprised you, add it to the table in step 4. This file is how the next orchestration session
starts ahead of this one.
