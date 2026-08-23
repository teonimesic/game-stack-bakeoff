---
id: 82
title: Task 70s ticket file carries task 71s entire brief, and task 71s file is a stub
status: open
priority: 1
refs: tasks/70-set-a-size-for-the-within-cell-verdict-variance-.md, tasks/71-nothing-reads-the-disclosures-31-of-75-completed.md, commit 436bf64, AGENTS.md rule 12
done_when: tasks/70 holds only its own body, tasks/71 holds the 59-line brief commit 436bf64 wrote into the wrong file, and tasks.py check fails on a task file whose body describes another task id
---

Commit 436bf64 appended task 71s 59-line brief to tasks/70-set-a-size-... instead of tasks/71-nothing-reads-... . Recover it with: git show 436bf64 -- tasks/70-set-a-size-for-the-within-cell-verdict-variance-.md . This is AGENTS.md rule 12s first table row happening a second time: an append aimed at a filename guessed from a queue listing title. It is URGENT because task 71 is in flight right now and its agent is reading a ticket with no body at all, while tasks.py show 70 renders a brief about trial disclosures. tasks.py check exits 0 on both files, so no gate sees it.

## What the next agent must not re-derive

**The first two clauses of the done_when were already satisfied when this was picked up.**
Commit 28f6598, "Repair tasks 70 and 71: I wrote one ticket's body into the other", had moved
the brief. Verified against the blobs rather than against the commit message: of the 59 lines
436bf64 appended to tasks/70, 41 are non-blank, all 41 are present in the live tasks/71, and 0
remain in tasks/70. The only clause left was the gate.

A live defect that WAS present and is not in the ticket: tasks/71 held unresolved git conflict
markers in the shared queue when this task started, and the orchestrator resolved them minutes
later. Recorded rather than fixed. Neither new check catches that shape - a body holding both
sides of a conflict still scores highest against its own brief - so it remains ungated.

**The done_when's own wording is not implementable, and this is the load-bearing finding.**
It asks that check fail "on a task file whose body describes another task id". Measured before
anything was written: **58 of the 85 live bodies name another task id**. Tickets cite their
neighbours - that is the queue working, not failing. Worse, the defect itself walks straight
through such a check: **the 59 misfiled lines never say "task 71" once**. A check keyed on id
mentions fires on 68% of the queue and misses the case it was filed for.

What was implemented instead is **containment against another ticket's title and done_when**,
because a misfiled body is one that is ABOUT another task, not one that mentions it. Do not
"simplify" this back to an id scan.

**The threshold is measured and the sweep is reproducible from git alone.** Score every version
of every task file git has ever tracked - 3175 file-versions across 81 queue snapshots - on
best_other minus own. The defect sits at 0.3615; the highest of the other 3174 sits at 0.1399
(task 62, whose subject genuinely is the DECISIONS.md row task 70 owns). MISFILED_MARGIN = 0.25
has 1.45x air below the true positive and 1.79x above the worst false positive. Both sides are
pinned in tasks_control.py, so moving it in either direction goes red.

**The empty-body half is exact, not heuristic, and it is the half that actually hurt.** One file
in 275 tracked file-versions ever had an empty body: tasks/71, at exactly the two commits of this
defect. It is a separate failure from the containment one on purpose - containment cannot see a
body that resembles nothing, and an empty body resembles nothing.

add now requires --why, because --why is what becomes the body and a tool must not create a file
its own lint rejects.
