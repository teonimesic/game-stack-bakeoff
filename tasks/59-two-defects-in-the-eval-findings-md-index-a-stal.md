---
id: 59
title: Two defects in the eval/FINDINGS.md index: a stale range and a table split in half
status: open
priority: 4
refs: eval/FINDINGS.md, AGENTS.md read-before-changing table, eval/tools/docstat.py
done_when: eval/FINDINGS.md's opening line names the highest finding number actually present, and the index renders as one table - verified by parsing the file and asserting the row count equals the number of entries found under eval/findings/, with the same assertion added to docstat.py --sweep so it cannot drift again
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
