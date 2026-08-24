---
id: 140
title: tasks.py check reports ORPHANED for every squash-merged branch, and the repository merges by squash
status: in_progress
priority: 2
refs: eval/tools/tasks.py landed_status, DECISIONS.md "A closed ticket is checked against the tree", .agents/skills/dispatch/SKILL.md merging section, tasks/122
done_when: landed_status distinguishes a branch that was squash-merged from one that was never merged, with the three-valued contract preserved and NOT_CHECKED still never a pass; a control pins it red on a genuinely orphaned branch and green on a squash-merged one, using real refs in this repository; and tasks.py check is green on the queue as it stands or names only tickets whose work really is absent from the tree
---

Measured 2026-08-24 from an agent worktree on task 127. tasks.py check exits 1 with: "131: status done, but refs/remotes/origin/task-131-controls-filter-into-a-step is not an ancestor of main", and the same for 130. Both are wrong. PR #16 was merged 2026-08-24T12:55:34Z and its merge commit 399280e7f059aaf694fa517c331f83f875a5cfb8 IS an ancestor of origin/main - but it has ONE parent and a tree of its own, because gh pr merge --squash creates a new commit rather than a merge of the branch. So the branch tip 58df942db5fae6a6537c26b40096c2894b1f3c90 is not an ancestor of anything and never will be. landed_status uses merge-base --is-ancestor on the BRANCH TIP, which is the right test for the git merge --no-ff flow this project abandoned and the wrong test for the squash flow DECISIONS.md now records. The failure direction is fail-closed, which costs attention rather than evidence - but it fires on every merged ticket whose remote ref survives, so the count grows with every merge, and a gate that is red for reasons unrelated to the change in front of you is a gate that gets bypassed as a habit. The pre-push hook already refuses to block on it from a linked worktree, which is a second reason nobody sees it go green. The signal that is actually available is the squash commit: gh pr view <n> --json mergeCommit gives it, and the PR is reachable from the ticket via the pr field that in_review already requires.

## note 2026-08-24

## The knowledge already existed in one file and contradicted the gate

`.agents/skills/dispatch/SKILL.md`, merging section, already states it: *"`git branch -d` refuses
a squash-merged branch. Its commits are not ancestors of `main` — the content is, the commits are
not — so git reports it unmerged and is correct."*

So one live document says the branch tip is not an ancestor **by design**, and
`tasks.py landed_status` treats exactly that condition as `ORPHANED` and exits 1. Neither file is
wrong about git; they were written for different merge flows and nothing compared them. That is
`AGENTS.md`'s *when a fact is spelled in two files, assert them equal in code* with the two
spellings being a sentence and a predicate.

Re-derived 2026-08-24: PR #16's merge commit `399280e7f059aaf694fa517c331f83f875a5cfb8` has one
parent, is an ancestor of `origin/main`, and its branch tip `58df942db5fae6a6537c26b40096c2894b1f3c90`
is an ancestor of nothing.

Whatever replaces the ancestry test, keep the third value. `NOT_CHECKED` exists because 112 of 119
closed tickets had no surviving ref, and a two-valued check would have reported them all verified.

## note 2026-08-24

## note 2026-08-24 (orchestrator) — it will NOT reproduce for you, and why that is the interesting part

`tasks.py check` on `main` is **exit 0** as of this note. Do not conclude it is fixed.

The full sequence, measured:

| state | `check` |
|---|---|
| stale `refs/remotes/origin/task-13{0,1}` present locally | **exit 1**, both named ORPHANED — your original measurement, reproduced |
| after `git fetch --prune` | **exit 0** |

The remote branches were already gone from GitHub — `git ls-remote --heads origin` returned 3 while
`refs/remotes/origin/*` held 6. So the gate was reading **stale local remote-tracking refs**, and a
prune cleared them.

**That makes the defect intermittent rather than absent, and harder to see, not easier.**
`delete_branch_on_merge` is on, so every squash-merged branch disappears upstream within seconds.
Whether `check` fires therefore depends on **when the local clone last pruned** — which means:

- it is red in the window between a merge and the next prune, and that window is exactly when
  agents and the pre-push hook run;
- it is red in **agent worktrees**, which fetch on their own schedule — which is where you measured
  it;
- and it goes green by itself, so anyone investigating after a prune finds nothing and concludes
  the report was wrong.

The underlying defect is unchanged and is what the ticket says: `landed_status` tests the BRANCH TIP
for ancestry, which is right for `git merge --no-ff` and wrong for squash, where the tip is an
ancestor of nothing and never will be.

**Consequences for the control.** It cannot rely on the ambient state of `refs/remotes`, because
that state is a function of prune timing. Construct the refs deliberately — a ref pointing at a
squash-merged branch tip (green) and one pointing at genuinely unmerged work (red) — and do not
assume a pruned clone proves anything. A control that passes only because the refs happened to be
absent is the vacuous pass this project keeps paying for.

## note 2026-08-24

## note 2026-08-24 (later) — it has TWO faces, and pruning only clears one

Reproduced live on task 133's merge, immediately after PR #19 squash-merged:

    133: status done, but refs/heads/task-133-scene-prompts,
         refs/remotes/origin/task-133-scene-prompts is not an ancestor of main

`git fetch --prune` cleared the remote-tracking ref and `check` **stayed red**, because the gate
names **both** `refs/heads` and `refs/remotes/origin`. Only deleting the local branch turned it
green. So the earlier note's "prune makes it go green" is true of the remote face only.

That matters for the fix and for the control:

- **The local branch cannot be pruned away.** `delete_branch_on_merge` removes the remote one; the
  local one survives until somebody deletes it by hand, so this face does **not** heal itself and
  will accumulate one red row per merged ticket.
- **`git branch -d` refuses it** — squash-merged, so the tip is an ancestor of nothing. Cleanup
  needs `-D`, which is the flag that also deletes genuinely unmerged work. **A gate that pushes an
  operator toward `-D` as routine is a gate with a cost**, and that is an argument for fixing
  `landed_status` rather than for tidying refs after every merge.

The control therefore needs both faces: a local branch and a remote-tracking ref, each pointing at
a squash-merged tip (must be GREEN) and each pointing at genuinely unmerged work (must be RED).
