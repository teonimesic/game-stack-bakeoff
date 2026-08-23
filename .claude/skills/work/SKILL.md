---
name: work
description: "Work one item from the open-work queue end to end: read the ticket, do it, verify it in both directions, and hand back a branch the orchestrator can merge. Invoked as /work <id>."
when_to_use: "You have been dispatched to do a single queued task and given its id. Also use it yourself when picking up work from the queue rather than reconstructing the procedure."
argument-hint: "<task-id>"
---

# Work one task

**Authoritative files: the ticket at `tasks/<id>-*.md`, and `AGENTS.md`.** If this skill and
either disagree, they win and this skill is the bug.

> **The ticket is the brief. There is no second brief.** Everything you need is in the ticket
> or in the documents it names. If you were dispatched with extra instructions in a message,
> that is a defect in the ticket — **write what you learned back into the ticket before you
> finish**, so the next agent gets it from the file. A brief delivered in a message dies with
> the session.

## 1. Read, in this order

1. `AGENTS.md` — always-loaded rules. Not optional; several were paid for with lost trials.
2. The folder-scoped `AGENTS.md` for wherever the ticket sends you (`eval/`, `eval/judge/`,
   `research/`). Each holds rules that apply only there.
3. `python3 eval/tools/tasks.py show <id>` — the ticket, in full, including anything a previous
   agent or the orchestrator appended to it.
4. Whatever the ticket's `refs` names. Cite by path; two files are named `IMPROVEMENTS.md`.

Then `python3 eval/tools/tasks.py start <id>`.

## 2. Know where you are standing

You run in an **isolated git worktree**. Three consequences bite every time:

| | |
|---|---|
| **The queue is shared** | `tasks.py` resolves `tasks/` to the **main checkout**, so your `start`/`done`/`add` land in the one real queue and appear as uncommitted changes *there*, not on your branch. That is deliberate (#94). |
| **Your copy of a tool may be stale** | Your worktree was forked at some commit. If `main` has moved, your `eval/tools/*.py` is older. A pre-migration `tasks.py` once wrote an unparseable task file. When in doubt run the tool from the main checkout by absolute path. |
| **`eval/runs/` does not exist here** | It is gitignored. Read stored evidence by absolute path from the main checkout. |

**Finding numbers collide.** Every agent reads the highest number from its own branch, which was
forked before the last merge. Eleven collisions happened on 2026-08-23. So: re-read the highest
number from `main` immediately before you take one, and prefer *not* taking one at all if a peer
is working a findings-heavy task — hand it to the orchestrator instead. `docstat.py --sweep`
fails on a duplicate or unindexed finding.

## 3. Do the work — the standard, not the steps

The steps are the ticket's. These are the properties every result here is held to:

- **Establish the broken state first.** A control run after the fix tests the fix, not the claim
  (#60). If you cannot make it fail, you have not measured it.
- **Pin in both directions.** Green proves nothing without a red. A mutant asks whether a check
  *can* fail; only a **variant** asks whether it can still *pass* on an input it mishandles
  (rule 15) — and every false negative adjudicated here has been of the second kind.
- **Prove the extraction before believing a census.** Not the whole set: one row whose true value
  you can state in advance. A census returning one value across a population it exists to
  discriminate is reporting the instrument, not the population.
- **Read unpiped.** A pipeline's exit status is the last stage's, and `|| true` turns an error
  into a plausible in-range number.
- **Read `agent.final_text`** when the ticket concerns a trial. Subjects have twice diagnosed
  harness defects in a paragraph nothing reads.
- **A negative result closes a task.** *"No pair resolves, here is the measured gap"* is a
  result. *"The experiment did not finish"* is not.

## 4. What you may not touch without the ticket saying so

| Never | Why |
|---|---|
| `eval/starters/*/`, `template*/` | The **product** — what a building agent reads. Editing one is a regime boundary: `verify_blind.py`, `starter_parity.py`, `starter_gate_control.py`, and a note in `eval/RUNS.md`. |
| `eval/findings/`, `eval/FINDINGS.md` | The archive. A number published and later proven wrong **stays**, marked. |
| Regime boundaries in `eval/RUNS.md` | They say which runs may be compared with which. |
| Files another agent is editing | Ask the orchestrator, or file a task. A conflict in a doc that states what is true now costs more than the edit is worth. |

## 5. Finish

```bash
python3 eval/tools/tasks.py done <id> "what established it"
```

Evidence means a measurement, a control, a file — never "completed". **No backticks in that
string**: they execute as command substitution and silently strip text from a durable record
(#80).

Then, in the same session as the work:

- **Update the ticket with what you learned** — see the box at the top. Anything the next agent
  would otherwise re-derive belongs in the file.
- Update the docs the change makes stale. `README.md` and `DECISIONS.md` state what is true now;
  replace superseded content rather than annotating it.
- Something that ran and measured nothing is a numbered finding.
- Run the gates unpiped: `docstat.py --sweep`, `tasks.py check`, and whatever the area's own
  `AGENTS.md` names.

**Commit on `task-<id>-<slug>`. Do not push. Do not merge.** The orchestrator merges after
verifying the result against the artifacts rather than against your report.

## 6. Report

To `main`, in this shape:

- what you **established**, with the numbers, and how
- the control in **both** directions
- what you could **not** establish — stated as plainly as the rest
- what you changed, what you deliberately did not, and why
- anything you filed, and anything the next agent must not re-derive

**Do not round off uncertainty.** A number that is wrong is worse than no number here, because
it gets acted on.
