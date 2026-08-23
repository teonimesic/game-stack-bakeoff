---
id: 36
title: Re-indent AGENTS.md rules 10-16 so their paragraphs stay inside the rule
status: open
priority: 3
refs: research/11-doc-linting-for-agents.md
done_when: the list-continuation scan reports 0 detached paragraphs in AGENTS.md, and round-tripping AGENTS.md through remark emits no top-level paragraph between numbered rules; if re-indenting turns out to change nothing a parser can see, record that and close
---
## What is this thing?

`AGENTS.md` at the repository root ends with a numbered list, "Rules this project learned the hard
way". It is loaded into every session via `CLAUDE.md`'s `@AGENTS.md` import.

## What is wrong, and how do we know?

Under CommonMark, a continuation line inside an ordered list item must be indented to the width of
the marker: a one-digit marker needs 3 spaces, a two-digit marker needs 4. Rules 1-9 use one-digit
markers and are indented 3 -- correct. **Rules 10-16 use two-digit markers and are also indented
3 -- one short.**

Lazy continuation keeps each rule's first paragraph attached. Any paragraph after a blank line is
not. Measured 2026-08-23 by round-tripping `AGENTS.md` through `remark`; five paragraphs come out
at top level, outside the rule they belong to:

| line | paragraph | belongs to |
|---|---|---|
| 397 | "A run is not a controlled experiment merely because it is one command." | rule 10 |
| 419 | "Its companion: an accepted-but-ignored flag is worse than an unsupported one." | rule 13 |
| 439 | "Worked example: the no-cap Tetris trial ..." | rule 15 |
| 455 | "The check is free, it is offline, and it comes out either way ..." | rule 16 |
| 459 | "Its companion, learned in the same hour: sweep the OPEN interval." | rule 16 |

A repo-wide scan found **one affected file and five paragraphs**. Only `AGENTS.md`, and only
because its own rule list crossed from one digit to two. `markdownlint` reports the same thing as
22 confusing `MD029/ol-prefix` alerts buried inside 9,697 total.

## Why does it matter?

The five detached paragraphs are among the most load-bearing sentences in the file. Any
CommonMark parser -- `remark`, `markdownlint`, a retrieval chunker, a renderer -- separates them
from the rule they qualify.

**What is NOT established is whether a model reading the raw bytes mis-associates them.** That is
unmeasured and nothing in the literature answers it. The defect is that the document's structure
does not match its intent.

## What should be done?

Add one space to every continuation line under rules 10-16 in `AGENTS.md`. Whitespace only; no
wording changes. Verify with the scan described in task 37, or by re-running remark.

## What NOT to conclude

Do not treat this as evidence that agents have been misreading `AGENTS.md`. It is not, and
claiming so would be exactly the proxy-for-a-real-thing error recorded as #59.
