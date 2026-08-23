---
id: 88
title: 'README says thirty-seven numbered findings; the log runs to #129'
status: done
priority: 3
refs: README.md line 539 area, AGENTS.md 'Read before changing anything' table, eval/FINDINGS.md, eval/tools/census.py
done_when: census.py (or docstat.py) emits a findings count and a highest-number over eval/FINDINGS.md plus eval/findings/, README.md and AGENTS.md quote it with the command written beside it as the AGENTS.md rule requires, and a control shows the producer disagrees when a finding is added or renumbered
established_by: 'The producer is python3 eval/tools/docstat.py --findings, not census.py: census counts the stored tree and exits 2 in an agent worktree, which is exactly where documents get edited. It counts eval/findings/ and eval/FINDINGS.md INDEPENDENTLY, prints the population and the absolute path of each, exits 2 rather than reporting 0, and exits 1 when the two sources or any live document disagree. Broken state established BEFORE the fix: --findings exit 1 on 3 real defects. README.md and AGENTS.md now quote 115 numbered findings, #19-#133, with the command beside them, one range statement per file. The ticket''s premise was one item short: task 59 had already gated the RANGE across three live files and it was green the whole time, because a range is not a count - #19-#132 is equally true of 114 findings and of 40. Controls in both directions. In-tool pins, 11 cases, run inside --sweep every time and printed by --selftest: red on a finding added to the bodies, added to bodies and index with the documents behind, renumbered, defined twice, a count one short, a count in words, a range stated twice; GREEN on the committed log and on a finding added CORRECTLY everywhere, which is the variant that decides whether the gate is usable at all. Out of process, eval/tools/findings_control.py, the real command over a tree whose answer is written down first: 13 controls 0 failed, 7 mutants 0 survived. The mutants earned their place. no_count_check deleted one of TWO implementations of the same reconciliation and all ten controls stayed green - the gate path and the producer path had each grown a copy - so _check_findings_integrity now returns findings_census disagreements plus only what a census cannot express. Two more mutants survived their first run because some other check fired on the same input, and two cases were added where the named mechanism is the only signal: a renumber applied consistently everywhere, where sets, count and range all agree and only the numbering has a hole, and one number on two index rows, invisible to both set differences. Second defect, not in the ticket and now gated: an evil merge 8fef835 had duplicated the range table row in BOTH AGENTS.md and README.md with --sweep green, because _check_range_in validates every occurrence it finds, so N correct copies are N passes; the same merge shape recurred mid-task at #19-#132. Third: AGENTS.md''s trigger row enumerated trials, runs, games, stacks, submissions, spend - findings were not on the list, which is the rule audit''s own conclusion firing on the rule audit''s own document; it now states the property and routes to three producers. WR-readme-findings-count added to eval/withdrawn.json, pinned red at 1717a1e (--withdrawn --at 1717a1e exit 1, README.md:556) and green at HEAD. Filed task 99 for an orphaned half-sentence at eval/FINDINGS.md line 6, deliberately not touched: the archive is out of scope without the ticket saying so. Cost paid and recorded as part of #133: the first mutant runner patched the repository''s docstat.py in place and printed restore with git checkout; the instruction was followed and discarded an hour of uncommitted work, so mutants now apply to a copy in a tempdir and the repository file is never written to. Gates all unpiped: docstat --sweep exit 0 over 160 docs reporting 115 findings #19-#133 agreeing with 115 index rows, --selftest 0 pins wrong, --withdrawn exit 0 over 8 entries and 53 live documents, --findings exit 0, findings_control 13/0, --all-mutants 7/0, tasks.py check 99 well-formed. Branch task-88-findings-count, commits b771665, 6391186, 49c4dd4, not pushed.'
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
