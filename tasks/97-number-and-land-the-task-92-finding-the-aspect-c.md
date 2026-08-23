---
id: 97
title: 'Number and land the task 92 finding: the aspect-census gate could catch 2 of 14 census shapes'
status: open
priority: 3
refs: eval/tools/docstat.py _ASPECT_CENSUS_RX, DECISIONS.md the census trigger section, tasks/92
done_when: the finding is numbered in eval/findings/, indexed in eval/FINDINGS.md, and docstat.py --sweep is clean unpiped
---

Task 92 measured the census gate task 79 shipped. It ran on every sweep for four days and could fire on 2 of 14 planted census claims, each false in exactly the way the check exists to catch. That is the project signature - a mechanism that runs, reports success, and measures almost nothing - and it is not numbered.

The numbers, re-measurable from eval/tools/docstat.py --selftest:
- old trigger, three alternations: 2 of 14 planted false censuses red
- quantifier-based widening: 10 of 14 red, and 26 correct live-corpus lines red, with 0 true positives among them
- predicate-scoped widening, shipped: 14 of 15 red, 0 red over the 152-document swept corpus, 6 over all 2090 markdown files and all 6 archive-exempt
- the structural bare-table trigger, rejected: 9 false positives on live docs

What earns a number rather than only a DECISIONS.md paragraph is the second line. The obvious repair - widen to the quantifier - is not merely imperfect, it is 100 percent false positives, and it is what anybody widening this would reach for first.

A number was deliberately NOT allocated by task 92: tasks 86, 91, 93 and 96 are all findings-numbering work, several in flight, and eleven finding-number collisions happened on 2026-08-23.

## What was done, 2026-08-23 - do not re-derive any of this

**The number is #137**, in eval/findings/certifies-nothing.md, indexed in eval/FINDINGS.md.

**Two of this ticket's own numbers were wrong, and both are corrected in the finding.**

1. "It ran on every sweep for four days" is false. The trigger shipped at 15a7129 (09:53:12 -0300) and was replaced at 0db6ac9 (10:13:22 -0300) - **20 minutes of committed history, same day.** Nothing ever made it go red; it was re-opened by auditing the trigger's shape, not by a failure. The finding says so, because "a gate that was green for four days" and "a gate that was green and could never have been anything else" are different claims and only the second is supported.

2. "2 of 14" is task 92's own planting set, which was not preserved. What IS preserved and re-measurable is the pin table, and over it the number is **4 of 15**. The 4 are exactly the wordings quoted from the two documents the trigger was built from; of the 11 wordings nobody had in front of them that day it caught **0**. That is the stronger statement and it is the one published.

**How to re-measure any of this in two minutes.** The pre-fix trigger is at `0db6ac9^:eval/tools/docstat.py`. Load both modules, spy on `_check_aspect_census` while calling `_aspect_census_pins` to recover the 28 pin corpora, then substitute each trigger into the real check. Measured 2026-08-23, and re-verified after merging main:

| trigger | of 15 planted false censuses | of 13 correct corpus lines | over the 53 live docs |
|---|---|---|---|
| old, three alternations | 4 red | 0 wrongly red | 0 |
| quantifier, cardinal-or-all governing aspects | 8 red | 6 wrongly red | 27 red, 0 true |
| shipped, predicate-scoped | 15 red | 0 wrongly red | 0 |

**The most useful thing found that task 92 did not state.** Three independent reconstructions of "the obvious repair" give **26** (task 92), **31** (AGENTS.md, task 98) and **27** (here) false positives, all with zero true positives. The count is a property of whichever draft you happened to write, not of the corpus, and it grows with the corpus. **That instability is the diagnosis**: a trigger drawn from an open class has no stable false-positive rate to tune against. AGENTS.md and audit-docs/SKILL.md now carry the spread rather than one draft's figure.

**On the finding number, for whoever merges this.** 136 was free when this task started and gone twenty minutes later - task 86 merged into main mid-work. Worktree agent-a624b03513b44b574 (task 96) holds 136 AND 137 in its uncommitted tree and will collide on both. This branch merged main first so its numbering is contiguous; a gap is worse than a collision here, because `docstat.py --findings` gates the gap and nothing gates a number a peer has not committed yet.
