---
id: 82
title: Task 70s ticket file carries task 71s entire brief, and task 71s file is a stub
status: open
priority: 1
refs: tasks/70-set-a-size-for-the-within-cell-verdict-variance-.md, tasks/71-nothing-reads-the-disclosures-31-of-75-completed.md, commit 436bf64, AGENTS.md rule 12
done_when: tasks/70 holds only its own body, tasks/71 holds the 59-line brief commit 436bf64 wrote into the wrong file, and tasks.py check fails on a task file whose body describes another task id
---

Commit 436bf64 appended task 71s 59-line brief to tasks/70-set-a-size-... instead of tasks/71-nothing-reads-... . Recover it with: git show 436bf64 -- tasks/70-set-a-size-for-the-within-cell-verdict-variance-.md . This is AGENTS.md rule 12s first table row happening a second time: an append aimed at a filename guessed from a queue listing title. It is URGENT because task 71 is in flight right now and its agent is reading a ticket with no body at all, while tasks.py show 70 renders a brief about trial disclosures. tasks.py check exits 0 on both files, so no gate sees it.
