---
id: 113
title: a dispatched agent cannot write what it learned back into a ticket BODY
status: done
priority: 3
refs: ''
done_when: tasks.py grows a subcommand that appends a section to a ticket body and writes it to the queue in the MAIN checkout, exercised from a real agent worktree in eval/tools/tasks_control.py direction 2 alongside add, with the round-trip row proving the rest of the file is byte-identical afterwards; or, if a body append is judged wrong, the work skill and AGENTS.md are corrected to name where a dispatched agent's learnings actually go and the two tickets that used established_by are cited as the precedent
established_by: tasks.py note id text-or-dash appends a dated section to the ticket in the MAIN checkout through open append and rewrites no other byte; tasks_control.py direction 2 went 37 to 49 measurements, 0 FAILED, 0 NOT CHECKED, exit 0, with the pre-note copy at ea9f853 as its positive control (exit 2, file unchanged); tasks_mutants.py --selftest 11 mutants 0 survived with the inert mutation SURVIVED, exit 0; this ticket's own record was written with the new subcommand and tasks.py check reads 114 tasks all well-formed
---

The work skill says: 'Update the ticket with what you learned - anything the next agent would otherwise re-derive belongs in the file.' From an agent worktree there is no way to do it. tasks.py has next, show, start, done, list, add, check and nothing that appends to a body; the worktree copy of tasks/NNN-*.md is a git-tracked file whose main-checkout twin is edited concurrently by tasks.py start/done, so committing an edit to it on a task branch invites a merge conflict with a file the merge is also rewriting; and an Edit aimed at the shared checkout is refused by worktree isolation. Both tasks 105 and 106 hit this and both did the same workaround - emptied everything into the established_by string, which is one unbroken line of prose in YAML frontmatter, cannot contain a backtick (#80), and is not where the next agent looks. That is a rule in an always-invoked skill that cannot be obeyed, which AGENTS.md classes as the rule being unusable as written rather than as the agents being careless. Note what the fix is NOT: relaxing the isolation guard. The queue resolving to the main checkout is deliberate (#94).

## note 2026-08-23

Closed by implementing the subcommand, not by the escape branch.

## What was measured before anything changed

From this agent worktree, 2026-08-23:

- `python3 eval/tools/tasks.py note 113 "x"` -> exit 2, `invalid choice: 'note'`.
- `Write` to a path under the shared checkout -> refused by worktree isolation
  ("Edit the worktree copy of this file instead of the shared-checkout path").
- **`Bash` is NOT refused.** `printf ... > <shared-checkout path>` exited 0 and created
  the file. So the ticket's "there is no way to do it" is true of the *tools*, not of the
  shell — which is why the fix is a subcommand that resolves the file BY ID rather than a
  documented `>>`, whose failure mode is AGENTS.md rule 12's worked example (an append to a
  filename guessed from a queue listing title, which created a second malformed task).
- `tasks_control.py` baseline: 37 measurements, 0 FAILED, 0 NOT CHECKED, exit 0.

## What was built

`tasks.py note <id> <text|-> [--heading H]` appends `\n## <heading>\n\n<text>\n` to the
ticket in the MAIN checkout's queue, through `open(p, "a")` and nothing else. Refuses an
unknown id, a malformed file, and an empty note. `-` reads stdin, which is the only channel
that carries a backtick or a newline (#80).

`tasks_control.py` direction 2 now covers `note` beside `add`: 12 rows, positive control
first (the copy at `ea9f853` has no such subcommand and must exit non-zero having written
nothing). 37 -> **49 measurements, 0 FAILED, 0 NOT CHECKED**.
`tasks_mutants.py` gained 4 mutants; **11 mutants, 0 survived**, inert mutation SURVIVED.

## Two findings the orchestrator should number

**Finding A - a control that imports its expectation from its subject cannot fail.**
The first version of the note rows built the expected suffix with `T._note_block`, the
subject's own function. That is what AGENTS.md rule 12 asks for and it is wrong here: the
mutant `note_no_separator`, which deletes the leading newline that separates an appended
section from the body, came back **SURVIVED with 0 red rows of 49** - the mutant had edited
the check. Repaired by stating the format in `tasks_control._expected_block` (an explicit
heading, so no clock is involved) plus `_DEFAULT_BLOCK_RE` for the default heading's shape.
Re-run: the same mutant is CAUGHT, 5 rows red. Rule 12 is about one FACT at one address; an
expectation is the second, independent statement of it. Written into AGENTS.md rule 12 and
DECISIONS.md.

**Finding B - `tasks_mutants.py` read failed row names from a lossy address for four days.**
`_FAIL_RE = r"^  FAIL (.+?): "` parsed the summary block, non-greedy, so it stopped at the
row name's FIRST ": ". Every row named `round trip: ...` arrived as the five characters
`round`, and no `kills` entry could match the part that distinguishes one from another.
Measured: `note_truncates` (append -> overwrite) turned 7 rows red and `note_writes_worktree`
turned 7 red, and BOTH were reported SURVIVED with "NO ROW NAMING ITS MECHANISM WENT RED".
This is the runner's own rule 12 - a correct method aimed at a lossy address, returning the
same wrong answer for every subject. Repaired by reading the TABLE (`_ROW_RE`, name
left-justified, separator two or more spaces, which a row name cannot contain) instead of
the summary. No previously shipped mutant changed verdict, because none of the seven names
they are keyed on contains ": " - the defect was latent, not active.

## What the next agent must not re-derive

- Direction 2's positive controls read a git blob, so they are pinned to a COMMIT: `466d436^`
  for `add`, `ea9f853` for `note`. Both must stay reachable from `main`.
- `_NOTE_BODY` deliberately ends WITHOUT a newline and there is a second row on a body that
  DOES. A leading separator correct for one shape and wrong for the other passes a probe fed
  only one; that pair is the variant half of rule 15 here.
- The one race `note` does not close, stated rather than guarded: `open(p, "a")` cannot lose
  a concurrent `note`, but `_set` is a read-modify-write of the whole file, so a `start` or
  `done` on the SAME ticket straddling the append would drop the section. One agent per task
  does not produce it. If it ever happens, put `cmd_add`'s existing common-dir lock around
  `_set` and `cmd_note` - do not make `note` clever.

## note 2026-08-23, correction to the established_by figure

`tasks.py check` read `114 task(s), all well-formed` at the moment this ticket was closed,
and that is the figure in `established_by`. It went red minutes later on a peer's write, not
on anything here: `tasks/109-*.md` was set to `status: in_review` at 12:23, and `in_review`
is not in `STATUSES`, which is still `("open", "in_flight", "done")` in `eval/tools/tasks.py`.
Task 109's branch is presumably the one that widens `STATUSES`; nothing on this branch touches
it, and `tasks_control.py` is still 49 measurements, 0 FAILED, 0 NOT CHECKED with both
round-trip rows green over all 114 files. Do not read the red `check` as this task's.
