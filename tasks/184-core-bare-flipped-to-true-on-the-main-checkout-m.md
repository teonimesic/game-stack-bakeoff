---
id: 184
title: core.bare flipped to true on the main checkout mid-session, and nothing would have caught it but a git command failing
status: todo
priority: 2
refs: .githooks/run-gates.sh,eval/tools/heartbeat.py,AGENTS.md
done_when: 'A cheap assertion fails loudly and by name when the main checkout is not a work tree - the natural homes are `.githooks/run-gates.sh` (which already runs on every commit and push) and `eval/tools/heartbeat.py` (which already reports what moved each hour, and would catch it even when nobody is committing). Whichever is chosen, it names `core.bare` and states the one-line repair in its own output, so the next session reads the fix rather than deriving it. Pinned in both directions: with `core.bare` set true the check goes red naming it, and with it false the check is green - and the red-direction control must restore the flag in a `finally`, because a control that leaves the repository bare is worse than the defect. If the guard is put in the hook rather than the heartbeat, say why the hook''s duty cycle is enough given that this appeared while no commit was running.'
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
