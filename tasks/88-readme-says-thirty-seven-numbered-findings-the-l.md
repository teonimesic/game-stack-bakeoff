---
id: 88
title: 'README says thirty-seven numbered findings; the log runs to #129'
status: in_flight
priority: 3
refs: README.md line 539 area, AGENTS.md 'Read before changing anything' table, eval/FINDINGS.md, eval/tools/census.py
done_when: census.py (or docstat.py) emits a findings count and a highest-number over eval/FINDINGS.md plus eval/findings/, README.md and AGENTS.md quote it with the command written beside it as the AGENTS.md rule requires, and a control shows the producer disagrees when a finding is added or renumbered
---

Found incidentally under task 78, not looked for. README.md's 'The one thing this project actually learned' section opens 'Thirty-seven numbered findings, and all but a few are instances of one pattern'. eval/FINDINGS.md cites up to #129 and AGENTS.md's own index table says #19-#126 - so the two live documents disagree with each other AND both disagree with the log. This is exactly the shape AGENTS.md names: a count with no producer goes stale forever, because nothing can disagree with it and every restatement agrees with the original to the digit. census.py produces trial, run, game, stack and cost counts and does NOT produce a findings count, which is why this one had nowhere to be checked against. The sentence that follows the number is still true - the pattern claim does not depend on the count - so this is a stale figure, not a wrong conclusion.

## What was built, and what the next agent must not re-derive

**The producer is `python3 eval/tools/docstat.py --findings`, not `census.py`.** `census.py`
counts the stored tree and exits 2 in an agent worktree, where `eval/runs/` is gitignored — and a
worktree is exactly where documents get edited. The findings log is markdown, so its producer
lives in the tool that already parses it. `heartbeat.py` also prints `findings` and
`findings_highest`; those are hourly deltas, not a citable figure, and they read only the bodies.

**The gate and the producer are ONE function.** `_check_findings_integrity` returns
`findings_census(...)["disagreements"]` plus the index's structure. Do not add a second
implementation of the reconciliation: the first draft had two, and
`findings_control.py --mutate no_count_check` deleted one of them with all ten controls still
green. That is #133.

**The ticket's premise was one item short.** Task 59 had already gated the *range* across three
live files. What had no producer was the *count* — and a range is not a count, which is why the
gate was green over `Thirty-seven` the whole time. The ticket's stated disagreement between
AGENTS.md and eval/FINDINGS.md was already repaired by then; the count was not.

**Two defects found while doing this, neither in the ticket:**

- An evil merge (8fef835) had duplicated the `Findings #19-#131` table row in **both**
  `AGENTS.md` and `README.md`, and `--sweep` was green because `_check_range_in` validates every
  occurrence it finds. The same merge shape recurred mid-task at `#19-#132`. Now gated: one range
  statement per live document.
- `eval/FINDINGS.md` line 6 is an orphaned half-sentence from an unrelated edit. NOT touched — the
  archive is out of scope without the ticket saying so. Filed as **task 99**.

**The word form is the second half of the defect and must stay.** `Thirty-seven` is a cardinal
spelled in words; no check can compare one, and a digits-only gate lets the next stale figure past
by being written out in full. `_stated_counts` reports a word-cardinal as ungateable.

**`AGENTS.md`'s trigger row was the third half.** It said *"trials, runs, games, stacks,
submissions, spend"* — an enumeration, findings not on it. It now states the property and routes
to three producers.

Withdrawal register entry: `WR-readme-findings-count`, anchored on this file. Pinned red at
`1717a1e` (`--withdrawn --at 1717a1e` → exit 1, README.md:556) and green at HEAD.
