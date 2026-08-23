---
established_by: 'tasks.py add printed its result relative to ROOT while writing to the shared queue under the main worktree; from an agent worktree those differ, so relative_to raised ValueError AFTER the file was written and the command exited 1 having succeeded. Fixed to print relative to the shared queue''s own parent. Verified by running add from a live agent worktree: exit 0, correct path printed, file created once. Checked for the damage this invites - a retry after a false failure would file a duplicate - and found none: 40 tasks, no duplicate ids, no duplicate titles.'
id: 41
title: tasks.py add succeeds then exits 1 with a traceback when run from a worktree
status: done
priority: 2
refs: eval/tools/tasks.py
done_when: python3 eval/tools/tasks.py add run from inside an agent worktree prints the created path and exits 0, with the file created in the main checkout exactly once; verified by running it from a worktree and from the main checkout and comparing exit codes, or, if the printed path cannot be made meaningful from both locations, the tool prints the absolute path and that is recorded as the resolution
---

Hit while filing task 40 from an agent worktree on 2026-08-23.

_write_task ends with print(f'created {(TASKS / name).relative_to(ROOT)}'). TASKS is deliberately the MAIN worktree (see _main_worktree, which exists so the queue is shared), but ROOT is parents[2] of __file__, which inside an agent worktree is the WORKTREE. relative_to then raises ValueError: not in the subpath of.

The write has already happened at that point, so the task file is created correctly and then the process dies with a traceback and exit 1. Reproduced: task 40 was created in the main checkout while tasks.py exited 1.

Why this is worth priority 2 rather than cosmetic: the failure is indistinguishable from a failed add. An agent that reads the exit code and retries gets a SECOND task file with a new id for the same work. That is precisely the duplicate-task collision the shared-queue design was introduced to stop, reintroduced through the status channel instead of the storage one.

Note this is the same shape as the rule about a pipeline reporting the wrong stage's status: the operation succeeded and the process reported failure. Fix is to make the display path relative to the main worktree, or absolute.
