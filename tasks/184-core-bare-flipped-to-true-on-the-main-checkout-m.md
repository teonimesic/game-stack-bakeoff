---
id: 184
title: core.bare flipped to true on the main checkout mid-session, and nothing would have caught it but a git command failing
status: done
priority: 2
refs: .githooks/run-gates.sh,eval/tools/heartbeat.py,AGENTS.md
done_when: 'A cheap assertion fails loudly and by name when the main checkout is not a work tree - the natural homes are `.githooks/run-gates.sh` (which already runs on every commit and push) and `eval/tools/heartbeat.py` (which already reports what moved each hour, and would catch it even when nobody is committing). Whichever is chosen, it names `core.bare` and states the one-line repair in its own output, so the next session reads the fix rather than deriving it. Pinned in both directions: with `core.bare` set true the check goes red naming it, and with it false the check is green - and the red-direction control must restore the flag in a `finally`, because a control that leaves the repository bare is worse than the defect. If the guard is put in the hook rather than the heartbeat, say why the hook''s duty cycle is enough given that this appeared while no commit was running.'
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/64
established_by: 'heartbeat_control.py 10/10 rows, 5 mutants killed; pre-fix heartbeat exit 0 byte-identical in a bare fixture while git status was 128; PR #64 head 752c538'
---

Observed 2026-08-27 ~11:34-11:42. Every git command in the main checkout began failing with 'fatal: this operation must be run in a work tree', and `git worktree list` reported the main checkout as **(bare)**. The cause was `core.bare=true` in `.git/config`. `git config core.bare false` restored it; nothing was lost - the `.git` directory was intact, every working file was present, HEAD was on `main`, and the tree matched HEAD before and after.

**The cause is not established.** What is known: `.git/config`'s mtime after the repair is 11:42:04 and the last commit before the failure is 11:33:36, so the flip happened inside that window. The session was running up to six worktrees at once and had just removed five of them in a loop. Nothing in the repository sets `core.bare`, and the only other non-default local key is `core.hookspath`, which is deliberate.

**Why it matters more than a one-off annoyance.** The failure is loud for git and silent for everything else: the working files look completely normal to any reader, editor or test runner, so a session that meets it without knowing this can happen may conclude the checkout is corrupt. The repair is one command. **Diagnosis cost far more than the fix, which is the signature of a missing check rather than a missing capability.**

It also blocks every agent at once - a worktree-isolated agent depends on the main checkout's object store and on `core.hookspath` pointing into it - so a recurrence during a matrix would stop all concurrent work with an error message that names none of this.

**Do NOT spend the ticket hunting the cause.** It may not be reproducible, and a guard is worth more than an attribution: the point is that this state existed for some minutes and the only thing that reported it was an unrelated command failing.

## note 2026-08-27

## From task 176: one candidate in that window, TESTED AND RULED OUT

Not the cause, recorded so the next agent does not re-derive it. `tasks/176` was in flight in
the same window and was running `git init` in `$TMPDIR` **with an inherited `GIT_DIR`
pointing at a real checkout** — a shape that does write to the repository `GIT_DIR` names.
It was measured: on 2026-08-27 it staged 6 fixture paths into a worktree's index at exit 0
with `.gitignore` replaced there.

So it is a genuine writer, in the window, aimed at a real `.git`. **It still does not
produce `core.bare=true`.** Asked three ways against a victim repository:

| `git init` under an inherited `GIT_DIR`, victim's state | `core.bare` after |
|---|---|
| victim has `core.bare=false` | `false` |
| victim has `core.bare` **unset** | `false` (written as false, not true) |
| cwd is a directory that no longer exists | rc 128, victim untouched |

`git status` in the victim stayed rc 0 in every row, so the symptom `tasks/184` describes
did not appear either.

**What this leaves.** The `GIT_DIR`-steered writer is ruled out as the mechanism, and
`tasks/176` has since made it impossible anyway — `docstat._git_at` drops every `GIT_*`
variable from the child and `_assert_own_repo` refuses in front of the one call that writes.
The ticket's instruction stands: build the guard, do not hunt the cause.

## note 2026-08-27

## note 2026-08-27 (orchestrator) — 175 has MERGED and its agent says your guard folds into the same script cleanly

`tasks/175` put `ci_minutes.py --selftest` into `pre-push` and, in doing so, hardened
`.githooks/run-gates.sh` considerably — read what it did before adding to it (#202):

- The hook now carries a **`GATES_DEPTH` ceiling**, because making a register-reading tool a hook
  gate made the two mutually recursive: 8 hook levels in 25 seconds before it was killed.
- Its first ceiling control **was itself the reason no recursion occurred** — it pinned
  `GATES_DEPTH=1` and executed, and a control that pins a counter also resets it.
- `$((${GATES_DEPTH:-0} + 1))` reads `-1000` as `-999` and `abc` as `0` under `/bin/sh`, so the
  value is matched against a **closed set** now.

**Two of those bear directly on your control.** Your ticket already says the red-direction control
must restore `core.bare` in a `finally`, because a control that leaves the repository bare is worse
than the defect. Add the second lesson to it: **do not let the control set the state and then read
its own answer.** If the guard reads `core.bare`, the control must observe the refusal from a
process that did not set it — acceptance is not propagation.

The tier question is also now decided by precedent rather than by argument: 175 chose `pre-push`
over `pre-commit` on **duty cycle**, not cost, because 88% of commits could not move its verdict
while all would pay. `core.bare` flipping is rarer still. Say which tier you chose and on which of
the two grounds.

## note 2026-08-27

## What the guard is, and the two things the ticket got wrong

`eval/tools/heartbeat.py` refuses before counting when the main checkout is not a work tree.
`eval/tools/heartbeat_control.py` pins it, 10 rows, about 1s, offline, in `gates.yml`.
PR #64.

**The ticket says this "blocks every agent at once". It does not.** Measured: with the main
checkout bare, a linked worktree's `status`, `commit`, `ls-files` and `rev-parse
--show-toplevel` are all exit 0. Agent worktrees keep working entirely. What breaks is the
main checkout — where merges happen, where the shared `tasks/` queue lives, and where
`git worktree add` for the next agent runs.

**The tier question is settled by reachability, not duty cycle.** `git commit` in a main
checkout that is not a work tree exits 128 **before any hook runs** — the fixture's
`pre-commit` printed nothing. So no git hook can carry this check at all; a hook guard would
only ever be reached from a linked worktree, which is the one place the state is invisible.
Duty cycle agrees and is the weaker reason.

## The property, and why `core.bare` was the wrong trigger

**Do not write a check for `core.bare`.** That is the vocabulary of this one incident, and it
already failed once here. A second setting reaches the identical symptom and the `bare` marker
cannot see it — `core.worktree` pointing at a directory that does not exist:

| | `core.bare=true` | `core.worktree` missing |
|---|---|---|
| `git status` | 128 | **128, same message** |
| `git ls-files` | 0, lists the index | **0, lists the index** |
| `git worktree list --porcelain` | carries `bare` | **ordinary non-bare record** |
| `heartbeat.py`, marker version | refused | **exit 0, counts printed** |

The shipped probe is `git rev-parse --is-inside-work-tree`, **asked at the main checkout**,
which answers `false` in both and in any third state with the same effect. The path comes from
`git worktree list --porcelain`, which needs no work tree and answers the same from anywhere;
asked at `ROOT` instead, the check passes from every linked worktree.

## Things measured here that the next agent should not re-derive

- `git ls-files` **exits 0 in a bare repository**, listing the index. Any check built on it is
  blind to this whole class of state.
- `git config --get core.bare` exits **1** when the key is absent — a third value. `git
  worktree list --porcelain` exits 0 in every state, which is why it is the locator.
- On darwin `$TMPDIR` is `/var/folders/…` while `/var` symlinks to `/private/var`, so
  `mkdtemp` and `git worktree list` spell the same fixture directory two ways. Resolve the
  fixture root before comparing paths against git's output.
- **The shared scratchpad is not session-private.** A `doc.py` written by another session was
  sitting at the path this one was about to write, and running it aimed an edit at a different
  agent's worktree. Namespace scratchpad files by task id.

## The cause is still unestablished, and that was deliberate

Nothing here attributes the flip. `tasks/176`'s `GIT_DIR`-steered `git init` was already ruled
out on this ticket. The guard bounds exposure to one hour (the heartbeat's interval) instead of
"whenever somebody next runs a git command"; it is not a claim of immediacy.

## For the orchestrator

**A finding number is needed at merge** (not allocated here — `.agents/skills/work/SKILL.md`):
*the hourly heartbeat reported byte-identical counts at exit 0 through a main checkout that
`git status` refused to look at — and the first guard written for it read the marker of the one
known cause rather than the property, so a second cause with the identical symptom passed it.*

**`tasks/192` was filed** from CodeRabbit's review: `CHECKS_ROW_RE` in `ci_minutes.py` reads the
first `| checks | … |` row anywhere in the register rather than the opening table's row.
Verified — a decoy row above a corrupted table keeps `--selftest` green. Written by PR #63, not
by this branch.

**The head at `752c538` is unreviewed.** Round 5 is the ceiling and it was still finding real
defects, so the last fixes were handed back rather than carried into a sixth round.

## note 2026-08-27

## Head correction after two merges with `main`

The head is now `4d1d572`, not `752c538`. Two things happened after the note above:

- `main` moved twice while this was in review. The branch is merged up to `origin/main`
  and `mergeable.py`'s "behind its base" condition is clear.
- **The second merge silently dropped `main`'s gate-count edit.** `main` added
  `mergeable_mutants` and bumped the count; this branch had bumped it for its own gate.
  Git auto-resolved those lines to this branch's value with **no conflict**, so three
  addresses disagreed with the workflow they describe. `python3 eval/tools/ci_minutes.py
  --gates` reads the merged workflow and says **60**; `ci_minutes --selftest` named all
  three places before they were fixed. `main`'s gate step itself survived intact.

  Worth knowing generally: a merge that produces no conflict is not a merge that kept both
  sides. This is exactly the case a count with a producer survives and a count without one
  does not.

Everything from `752c538` onward — that merge resolution and the count repair — is
unreviewed, for the reason the note above gives.

## note 2026-08-28 (orchestrator) — CLOSED at the merge

Merged as squash `5c3871b` (PR #64). Verified against the artifacts on the merged head, unpiped,
not against the handback: `heartbeat_control.py` **10/10 rows** exit 0; `ci_minutes --selftest`
ok (101 mutants died, 63 variants passed); `ci_minutes --gates` reads **60** with
`.github/workflows/README.md` and the selftest pin agreeing — the three-way repair the head
correction below describes held through the final merge. Finding allocated as requested:
**#206**, in `eval/findings/certifies-nothing.md`.
