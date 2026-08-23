---
id: 38
title: Fix two defects in tasks.py found while surveying doc tooling
status: done
priority: 4
refs: research/11-doc-linting-for-agents.md, eval/tools/tasks.py
done_when: tasks.py add run from inside an agent worktree exits 0 and prints the created path, and tasks.py check no longer warns on a done_when whose escape branch is phrased outside the ESCAPE keyword list, pinned in both directions against task 32's wording and against a done_when with no escape branch at all
established_by: 'Defect 1 was already fixed by task 41 in 466d436; re-established rather than assumed, with a scratch main-plus-worktree pair where 466d436^ exits 1 having written the file and HEAD exits 0 printing the path, both kept as control rows. Defect 2 was real but masked by cmd_check skipping done tasks: run against the wordings directly it warned on tasks 32, 35 and 58, all three of which carry an escape branch. Escape detection now tests the closed class of English conditional and alternative function words instead of nine phrases, four of which were sentences copied off tasks 01 and 08; addresses and the at-all idiom are removed first, which also killed the only reachability warning check was printing (task 59, where under eval/findings/ was read as a threshold). Warnings over the 60 queue files go 6 to 2, both survivors genuine. New eval/tools/tasks_control.py, the first control this tool has had: 20 measurements, 0 FAILED, 0 NOT CHECKED, covering byte-for-byte round trip over all 60 queue files, add from an agent worktree with the pre-fix copy as positive control, check still failing on a duplicate id and a missing done_when and a bad status against a well-formed negative control, and reachability in both directions over ten wordings. Five mutants, all killed by the row naming their mechanism; two wordings were added because a mutant survived without them. The shared queue is untouched by the control. Separately measured and deliberately left alone: _set rewriting the whole file costs nothing, since start then done on a real 102-line task file produced one-line diffs and moved the blame of zero unchanged lines, 100 of 102 staying on the authoring commit, so a targeted write would restore no recall and would give up what makes the YAML round trip safe.'
---
## What is this thing?

`eval/tools/tasks.py` is the convenience layer over the open-work queue in `tasks/`. The queue
lives in the **main checkout** and `tasks.py` resolves it there no matter which worktree it is run
from -- that is deliberate, and #94 records what happened when it was per-worktree.

## What is wrong, and how do we know?

Both defects were hit while filing tasks for task 32 on 2026-08-23.

**1. `add` writes the file, then crashes.** `eval/tools/tasks.py:252` prints the created path
using `Path.relative_to(ROOT)`. `TASKS` resolves to the main checkout while `ROOT` is the current
worktree, so from an agent worktree the call raises:

    ValueError: '/.../game-research-claude/tasks/35-....md' is not in the subpath of
    '/.../game-research-claude/.claude/worktrees/agent-...'

The task file **is created correctly**. The tool then exits non-zero with a traceback. Five tasks
were filed this way and all five landed; a caller reading the exit code would conclude none had.

**2. `check`'s reachability warning fires where nothing is wrong.** The heuristic at
`eval/tools/tasks.py:298-312` warns when a `done_when` makes a universal or threshold claim with
no alternative branch, deciding "no alternative branch" by testing a nine-word `ESCAPE` keyword
list at line 302. It warned on task 32, whose `done_when` reads: *"... If no tool is worth
adopting, the file records that as the result with the evidence behind it, and that closes the
task too."* That is an escape branch. It matches none of the nine keywords.

## Why does it matter?

Defect 1 is a successful operation that reports failure -- the opposite polarity of rule 7, and it
will make an agent re-file a task that already exists, which is how a queue forks.

Defect 2 is `AGENTS.md`'s own lesson implemented as the thing it warns against: *"a rule whose
trigger is a list must be re-derived by every reader who meets an item not on the list. Write the
trigger as the RESOURCE or the PROPERTY, never as an enumeration."* And it is the companion to
rule 16: a check that fires where nothing is wrong spends exactly the attention a check firing
correctly needs.

## What should be done?

For 1: print the path relative to the queue root, or print it absolute. One line.

For 2: the honest options are (a) detect a conditional clause structurally rather than by keyword,
(b) widen the list and accept it will be widened again, or (c) decide the warning cannot be made
precise and downgrade it so it never claims to be a verdict. **(b) is the option this project's
own rule argues against**; whichever is chosen, say why in the code comment, which already
explains the heuristic's reasoning and should explain its limit too.

**Pin it in both directions**, per rule 1: the check must stay quiet on task 32's wording and on
the two repairs already pinned (tasks 08 and 01), and must still warn on 08-original,
01-original, and a `done_when` with a universal claim and no escape at all.

## What NOT to conclude

Do not remove the reachability warning. It caught two genuinely unreachable `done_when` conditions
(#75) and the comment recording why is worth more than the false positive costs.

## Dispatch knowledge, 2026-08-23 — written back from a launch message

**`tasks.py` changed twice since this ticket was filed** — it now parses and emits real YAML
(task 40, #117) and resolves the queue to the main worktree (#94). **Re-establish that each
reported defect still exists before fixing it.** One or both may already be gone, and *"it was
already fixed"* is a legitimate closure with evidence.

**You are editing the tool every other agent uses to claim and close work.** Verify from inside a
worktree, where the queue path and `ROOT` deliberately disagree — that asymmetry already produced
a defect where `add` wrote the file and then exited 1.

**The `id` is deliberately bare digits rather than quoted.** That was measured, not an oversight:
a peer running an older reader takes `'07'` literally and its `done NN` would answer "no task NN".

**One thing the migration left open, worth reporting on even if you do not change it:** `_set`
rewrites a *whole* queue file when it writes one field, which is why a closed task's evidence is
blamed to the last queue write and why `docstat.py --renumbered` loses recall on `tasks/`. A
targeted write would restore that recall — but the whole-file rewrite is what makes the YAML
round-trip safe. Say which it is.
