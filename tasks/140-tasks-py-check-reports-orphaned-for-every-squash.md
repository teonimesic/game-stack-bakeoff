---
id: 140
title: tasks.py check reports ORPHANED for every squash-merged branch, and the repository merges by squash
status: in_testing
priority: 2
refs: eval/tools/tasks.py landed_status, DECISIONS.md "A closed ticket is checked against the tree", .agents/skills/dispatch/SKILL.md merging section, tasks/122
done_when: landed_status distinguishes a branch that was squash-merged from one that was never merged, with the three-valued contract preserved and NOT_CHECKED still never a pass; a control pins it red on a genuinely orphaned branch and green on a squash-merged one, using real refs in this repository; and tasks.py check is green on the queue as it stands or names only tickets whose work really is absent from the tree
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/23
established_by: 'tasks_control 100 to 111 rows 0 FAILED 0 NOT CHECKED (115 with --live-squash-refs), tasks_mutants 28 to 35 with 0 surviving, and the fixture reproducing a real merge --squash goes from exit 1 naming all 4 refs on main''s tool to exit 1 naming only the 2 that never landed. PR #23, gates and controls both green at b97291b.'
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

## note 2026-08-24

## What the fix is, and why it is not `gh pr view --json mergeCommit`

`_is_landed` asks 2 questions and keeps the 3-valued contract:

- `_is_ancestor` first, **unchanged** — still the whole answer for the `git merge --no-ff` refs
  stored before the flow changed.
- then `_squash_landed`, which renders `merge-base..ref` as one diff and asks whether its
  `git patch-id` is among the patch-ids of the commits the base gained since.

A `True` from either arm wins; an arm that could not answer outranks a `False`, so an unreadable
ref is `NOT_CHECKED` and never an accusation.

The ticket suggested `gh pr view <n> --json mergeCommit`. Rejected, and the reason is in
`DECISIONS.md`: it needs the network and an authenticated `gh`, while `check` runs in a git hook
and in CI, where an unavailable answer becomes a third population of NOT_CHECKED with nothing to
distinguish it from a clean queue. A patch-id is also a closed test, which is the property the
original entry rejected the `pr` field for lacking.

## The measurement, both directions

Fixture: a real `git merge --squash` over 4 refs — a local branch and a remote-tracking ref, each
squash-merged and each genuinely unmerged.

| tool | result |
|---|---|
| `main`'s `tasks.py` | exit 1 naming all 4 — 2 of them false |
| this branch | exit 1 naming only the 2 that never landed, census `2 reachable from main` |

Real objects, 2026-08-24: PR #16's squash commit `399280e` has **1** parent and is an ancestor of
`main`; its branch tip `58df942` is an ancestor of no commit on `main`; the tip's change **is** on
`main`, patch-id `cc2213e`, matching `399280e` exactly.

## Two things the next agent should not re-derive

**The deleted tip cannot be a default control row.** `delete_branch_on_merge` is on, so
`58df942` is reachable from nothing and no clone that did not perform the merge can fetch it —
`actions/checkout` at `fetch-depth: 0` fetches live branch heads only. An unconditional row on it
reports NOT CHECKED, `tasks_control.py` exits **3**, and `gates.yml` goes red on every machine but
one. It is behind `--live-squash-refs`, recorded as a deliberate exclusion in
`.github/workflows/README.md`. The row that runs everywhere is the one-parent property of
`399280e`, which is on `main`.

**The patch-id cache: `(base_sha, rev)`, and a control that moves one thing at a time.** Measured
over 12 orphaned refs on a 60-commit `main`, best of 3: `check` is 288ms with ancestry alone,
1070ms with the squash arm, 720ms once the base range is cached — and unchanged at 1037ms when the
refs fork from different commits, which is what says the cache collapses what it claims and
nothing else. A git failure is never cached.

The mutant that drops `rev` from the key **survived its first control row**, and the row was the
defect: it compared one fork point against 2 different bases, under which `merge-base` moves as
well, so both halves of the key change together and dropping one is invisible. It now advances
`main`, holding the fork point fixed. A variant that moves 2 things at once cannot say which one
the check is reading.

## What was NOT established

**The false-negative direction has no real case.** A squash whose diff was rewritten by conflict
resolution has a different patch-id and reads `ORPHANED`. That is fail-closed — attention, not
evidence — and it is written into `_squash_landed`'s docstring and into `DECISIONS.md` as what
would re-open the choice. No such commit exists in this repository's history to test against.

**The live queue is entirely `NOT_CHECKED`** (145 tasks, 0 reachable, 133 NOT CHECKED), so the
end-to-end proof is the fixture, not the queue.

## For the orchestrator

**A finding number is needed and none was allocated.** The claim: *a decision that named its own
reversal condition had that condition fire the next day, and nothing connected the two.*
`DECISIONS.md`'s entry said ancestry would be re-opened by *"the repository adopting squash
merges"*; `.agents/skills/dispatch/SKILL.md` already stated the git fact the predicate
contradicted. Two live documents, one predicate, and no check comparing them — the same shape as
*a fact spelled in two files and asserted equal nowhere*. The failure was fail-closed and
intermittent: the remote face heals on `fetch --prune`, the local face never does, so an
investigator arriving after a prune finds nothing.

**Filed: `tasks/147`** — `.github/workflows/README.md` narrating its own history (run ids, dated
timings, change-history sentences). Raised by the reviewer on this pull request and declined here
because those lines arrived with the merge of `main` from task 135 (`c29429a`, #22).

## Numbers

`tasks_control.py` 100 → **111** rows, 0 FAILED, 0 NOT CHECKED (**115** with
`--live-squash-refs`). `tasks_mutants.py` 28 → **35**, 0 survived, `--selftest` green.
`docstat.py --sweep`, `linkcheck.py`, `skill_layout_control.py`, `tasks.py check`,
`lint.py --gate --rule invalid-syntax` all exit 0; `lint.py --counts` unchanged at 83.
