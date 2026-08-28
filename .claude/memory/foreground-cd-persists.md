---
name: foreground-cd-persists
description: "A foreground `cd` in a Bash call persists for the rest of the session; only backgrounded commands get a \"Session cwd remains\" notice — queue-state confusion on 2026-08-28 came from reads hitting the agent worktree while tasks.py wrote main"
metadata: 
  node_type: memory
  type: project
  originSessionId: 5b6b2ba6-3368-4451-b4e7-13653d8168ff
  modified: 2026-08-28T06:35:23.994Z
---

In this environment, a **foreground** `cd` inside a Bash call changes the session's working
directory for every later call; only **backgrounded** commands print "Session cwd remains …"
after being moved. On 2026-08-28 a foreground `cd` into an agent's worktree was forgotten, and
every later relative-path read (`grep`/`sed`/`wc` on `tasks/188-…`) silently read the **worktree's**
stale ticket copy, while `tasks.py show/note/done` — which resolve the shared queue to the **main
checkout regardless of cwd** by design — read and wrote main's copies. The disagreement produced a
false "the handback note is missing / the file was mid-write" theory, and a `git pull` that named
the task branch as its upstream because HEAD was the worktree's branch.

**Why:** the address of a relative path is the session cwd — rule 12's "the address is an input"
with the session itself as the thing that moved.

**How to apply:** after any `cd` in a compound command, `cd` back in the same command, or use
absolute paths for everything that names a file. Before queue-state operations (`tasks.py done`,
commits, `git pull`), run `pwd` and `git branch --show-current` and check they name the main
checkout and `main`. When two observations about one file disagree, check whether they were made
from different trees before concluding the file was mid-write.
