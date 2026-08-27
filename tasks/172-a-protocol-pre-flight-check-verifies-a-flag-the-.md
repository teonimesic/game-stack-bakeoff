---
id: 172
title: A PROTOCOL pre-flight check verifies a flag the standing configuration never passes
status: todo
priority: 3
refs: 'eval/PROTOCOL.md, DECISIONS.md, #159, .agents/skills/run-matrix/SKILL.md'
done_when: The cap row names a flag the standing configuration actually passes, or is removed with the row below it re-worded so it no longer depends on 'the cap' as its antecedent. Every other row in that table is checked for the same defect and the result stated, with 'this was the only one' being a complete answer. eval/PROTOCOL.md's two statements about what bounds a trial agree, and docstat --sweep and linkcheck stay green.
---

`eval/PROTOCOL.md`'s pre-flight table is headed *"run every check below. Each has cost trials at
least once."* One of its rows cannot fire:

> **Verify the cap in the live driver's process list**, not in a config file. — `--max-budget-usd`
> is read at import; editing a file changes nothing for a running process.

**The standing configuration passes no `--max-budget-usd`.** The same file says so 66 lines later:
*"What bounds a trial: `--max-turns 1000`, and no budget cap. **Do not pass `--max-budget-usd`.**"*
So the check asks the operator to verify a flag that is never set, in a table whose whole claim is
that skipping any row has cost trials.

**The lesson is right and the flag is wrong.** Read-at-import is a real property and it applies to
`--max-turns 1000`, which *is* passed on every trial — so the row should name the flag the run
actually carries. The mechanism is unchanged; only its instance is stale.

## Do not simply delete the row

The row **below** it begins *"Same mechanism as the cap"* — the prompts row depends on this one as
its antecedent. Deleting leaves that dangling, which is the renaming-breaks-references shape
`AGENTS.md` records. Re-point both, or re-word the second so it stands alone.

## Why this is worth a ticket rather than a quiet edit

A pre-flight check that cannot fire is the project's central concern in the place most likely to be
trusted: a table of checks each of which is documented as having cost trials. A reader running the
list will verify a flag, find nothing, and read that as a pass.

**Ask the same question of every row while you are there.** Six rows, and at least the harness ones
are new and correct. If another names a configuration the project has since abandoned, it has the
same defect — and finding that this is the only one is a complete answer.
