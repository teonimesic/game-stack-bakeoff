---
id: 59
title: 'Two defects in the eval/FINDINGS.md index: a stale range and a table split in half'
status: done
priority: 4
refs: eval/FINDINGS.md, AGENTS.md read-before-changing table, eval/tools/docstat.py
done_when: eval/FINDINGS.md's opening line names the highest finding number actually present, and the index renders as one table - verified by parsing the file and asserting the row count equals the number of entries found under eval/findings/, with the same assertion added to docstat.py --sweep so it cannot drift again
established_by: 'Established the gap before changing anything: a blank line planted between the #105 and #106 index rows left docstat.py --sweep at exit 0. Added to eval/tools/docstat.py a contiguity plus header-delimiter check on the index, a duplicate-row check (the done_when row-count clause - a set reconciliation collapses a duplicated row, only counting sees it), and a cross-file stated-range check over AGENTS.md, README.md and eval/FINDINGS.md. Pinned in both directions by _index_pins, which cmd_sweep runs on every invocation and --selftest prints: 13 in-tool pins, 10 end-to-end pins mutating the real index on disk (restored to sha256 b9c89fa9c3a4), 7 mutating the real range sentence in all three files (all restored byte-for-byte), and 2 mutants of the check itself both making the sweep exit 1 and name the failing pin. docstat.py --sweep exit 0 clean over 135 docs; tasks.py check exit 0 over 63 tasks; eval/tools/lint.py 47 findings with 0 in docstat.py, unchanged. Re-measured independently: 100 findings #19-#118 no duplicates, 100 index rows, body set equals index set, 0 blank lines between adjacent rows - both original defects were already fixed. Branch task-59-index-one-table commit 18d2e3e, not pushed. eval/findings/ and eval/FINDINGS.md not edited.'
---

the index is the only route from a finding number to its entry, and half of it currently sits outside the table

## What is this thing?

`eval/FINDINGS.md` is not the findings log itself — the entries live in `eval/findings/`, grouped
by the shape of the failure. `FINDINGS.md` is the **index**: an opening line stating the range it
covers, and a table under "Every finding" with one row per number pointing at the file that holds
it. Citations everywhere in the project are by number and resolve through that table, so the
table is the only route from `#104` to the paragraph it names.

## What is wrong, and how do we know?

Two defects, both mechanical, both measured 2026-08-23 by reading the committed file:

1. **The stated range is stale.** Line 3 reads "Findings #19-#110" and the row for `#111` is
   present in the same file. The identical sentence in `AGENTS.md`'s read-before-changing table
   also says `#19-#110`. Finding #111 was added by task 44 and neither line moved.

2. **The index table is split in two.** There is a blank line between the `#105` row and the
   `#106` row. Under CommonMark that ends the table: rows #106 to #111 form a second table with
   no header, and #105 is the last row of the first. Every renderer, every chunker and every
   parser sees two tables; grep does not, which is why it has gone unnoticed.

This is the same class as task 36 — a load-bearing document whose structure does not match its
intent, found by a parser rather than by reading.

## Why does it matter?

The last six findings are the newest, and they are outside the structure that exists to make them
findable. #106 through #111 include two comparability breaks and the retraction-shaped #110. An
agent that reads the index as a table gets a table that stops at #105.

The stale range is smaller but it is the sentence `AGENTS.md` tells every session to trust, and a
range that undercounts invites exactly the wrong inference: that #111 is not a finding yet, and
the next number to take is 111.

## What should be done?

- Fix the blank line and the two range sentences.
- Then make it mechanical, because both defects are drift and drift returns: add an assertion to
  `docstat.py --sweep` that the index row count equals the number of `## NN.` headings across
  `eval/findings/`, and that the stated range's upper bound equals the maximum of those. Both
  numbers are already parsed by the sweep's existing finding-number checks.

Note that `eval/tools/docstat.py` was under active edit on 2026-08-23; rebase before starting.

## What NOT to conclude

**Do not touch anything else in `eval/FINDINGS.md` or `eval/findings/` while in there.** The
retraction and withdrawal language is the subject matter, and a tidying pass through it is how
the most valuable text in the repository gets lost. This task is a blank line and two numbers.

## Status when dispatched, 2026-08-23 — BOTH DEFECTS ARE ALREADY FIXED

Re-measured before dispatch, against the committed file:

| the ticket's defect | now |
|---|---|
| stated range disagreed with the highest finding | `Findings #19-#118`, and the highest present is **118** — agrees |
| a blank line split the index into two tables | **0** blank lines between adjacent `\| **NN** \|` rows |

Both were repaired incidentally while merging other work, not by anyone working this ticket.
`docstat.py --sweep` also already asserts the range and reconciles body against index in
`_check_findings_integrity()`, and it has caught real drift five times since it landed.

**So what remains is only the third clause of `done_when`, and it is the one that matters:**
nothing asserts the index renders as **one table**. A blank line between two rows is invisible
to a row-count check — every row still parses, and every citation still resolves — while a
markdown renderer shows two tables and the second has no header. That is exactly how the defect
arrived and why nobody noticed.

**What to do:** add that assertion to `_check_findings_integrity()` in `eval/tools/docstat.py`,
where the other findings-index checks already live. Do not build a second mechanism.

**Prove it can fail.** The repository is clean right now, so a check written against it is a
check nobody has seen go red: plant a blank line between two index rows, confirm the sweep exits
1 and names the line, remove it, confirm exit 0. A gate that is green on arrival and never tested
is the shape this project keeps finding.

**Do not touch the finding entries themselves** — `eval/findings/` and `eval/FINDINGS.md` are the
archive. This adds a check over the index; it does not edit the log.


## Done, 2026-08-23 — branch `task-59-index-one-table`

**The measurement that established the gap.** Before any change, a blank line was planted
between the `#105` and `#106` rows of the committed `eval/FINDINGS.md` and
`docstat.py --sweep` was run unpiped: **exit 0**. The defect the ticket describes was
invisible to the sweep as it stood, and that control was taken before the fix, not after
(AGENTS.md rule 14).

**What was added, all in `eval/tools/docstat.py`:**

- `_check_index_renders_as_one_table()` — the index rows must be contiguous, and a
  `|---|---|---|` delimiter must sit immediately above the first of them. Fence-aware.
- a **duplicate-row** check in `_check_index()`. This is the `done_when`'s row-count clause,
  and it is not redundant: the body-vs-index reconciliation compares SETS, so a number
  indexed twice collapses, both differences come back empty and both rows resolve. Only
  counting sees it.
- `_check_stated_range()` over `RANGE_DOCS = AGENTS.md, README.md, eval/FINDINGS.md`. The
  range sentence is spelled in three live files and only the third was ever checked — which
  is exactly why the index got repaired while `AGENTS.md` went on saying `#19-#110`. It also
  fires when a file stops stating a range at all, so the check cannot go quiet by the
  sentence being deleted.
- `_index_pins()` — the red/green controls, **run by `cmd_sweep` itself on every
  invocation**, and printed by the new `docstat.py --selftest`. They mutate copies of the
  text in memory; nothing writes to the archive.

**Why the pins live inside `--sweep` rather than in a separate selftest command.** A pin
that has to be remembered is one that will be forgotten, and the thing being guarded is a
check that was green on a real defect. The pins are pure-function and cost microseconds.

**Measured results, all unpiped:**

| | |
|---|---|
| 13 in-tool pins (`--selftest`) | all as expected; `eval/FINDINGS.md` size and mtime unchanged |
| 10 end-to-end pins mutating the real `eval/FINDINGS.md` on disk | all as expected, file restored to sha256 `b9c89fa9c3a4…` |
| 7 end-to-end pins mutating the real range sentence in all three files | all red where expected, all three restored byte-for-byte |
| 2 mutants of the check itself (gutted one-table check; row parser returning nothing) | `--sweep` exit 1 both times, naming which pin came out wrong |
| `--sweep` | exit 0, clean over 135 docs |
| `tasks.py check` | exit 0, 63 tasks well-formed |
| `eval/tools/lint.py` | 47 findings, **0 in `docstat.py`** — unchanged from before |

**Independently re-measured, confirming the ticket's dispatch note:** `eval/findings/`
holds 100 findings, `#19`-`#118`, no duplicates; the index holds 100 rows, `#19`-`#118`;
body set == index set; 0 blank lines between adjacent rows. Both original defects were
already fixed.

**What the next agent should not re-derive:**

- **`grep -rhno "^## #\?[0-9]\+" eval/findings/*.md | sort -n | tail -1` gives the highest
  LINE NUMBER, not the highest finding.** It returned `117` against a true `118`. Parse with
  Python; the shell one-liner is the rule-12 shape and it looks like an answer.
- The old range check inside `_check_index` was **removed**, not kept — with
  `_check_stated_range` covering `eval/FINDINGS.md` too, keeping both reported the same
  fact twice (verified: 2 problems for one stale range).
- `tasks/`, `eval/findings/` and `CLEANUP-LOG.md` are deliberately **outside** `RANGE_DOCS`.
  They quote historical ranges on purpose — this ticket's own body quotes `#19-#110` as
  evidence — and gating them would fail on correct input.

**Filed for the orchestrator, deliberately NOT written here:** a candidate finding —
*`docstat.py --sweep` was green on a two-table split in the finding index for as long as it
stood; the row count, the set reconciliation and `grep` are all identical either way.*
A finding number was not allocated: this ticket forbids touching `eval/findings/` and
`eval/FINDINGS.md`, and numbers collide across worktrees (11 collisions on 2026-08-23).
