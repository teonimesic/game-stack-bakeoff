---
id: 97
title: 'Number and land the task 92 finding: the aspect-census gate could catch 2 of 14 census shapes'
status: done
priority: 3
refs: eval/tools/docstat.py _ASPECT_CENSUS_RX, DECISIONS.md the census trigger section, tasks/92
done_when: the finding is numbered in eval/findings/, indexed in eval/FINDINGS.md, and docstat.py --sweep is clean unpiped
established_by: 'FINDINGS #137 in eval/findings/certifies-nothing.md, indexed in eval/FINDINGS.md; re-measured against source with the pre-fix trigger recovered at 0db6ac9^ and substituted into the real _check_aspect_census - old trigger 4 of 15 planted censuses red and 0 of the 11 wordings it was not built from, quantifier repair 27 red over 53 live docs with 0 true positives, shipped predicate 15 of 15 and 0; two of the ticket''s numbers corrected - four days is 20 minutes of committed history 15a7129 to 0db6ac9, and 2 of 14 is 4 of 15 over the pins that ship; docstat.py --sweep exit 0 unpiped, --selftest 0 of 53 pins wrong, tasks.py check exit 0'
---

Task 92 measured the census gate task 79 shipped. It ran on every sweep for four days and could fire on 2 of 14 planted census claims, each false in exactly the way the check exists to catch. That is the project signature - a mechanism that runs, reports success, and measures almost nothing - and it is not numbered.

The numbers, re-measurable from eval/tools/docstat.py --selftest:
- old trigger, three alternations: 2 of 14 planted false censuses red
- quantifier-based widening: 10 of 14 red, and 26 correct live-corpus lines red, with 0 true positives among them
- predicate-scoped widening, shipped: 14 of 15 red, 0 red over the 152-document swept corpus, 6 over all 2090 markdown files and all 6 archive-exempt
- the structural bare-table trigger, rejected: 9 false positives on live docs

What earns a number rather than only a DECISIONS.md paragraph is the second line. The obvious repair - widen to the quantifier - is not merely imperfect, it is 100 percent false positives, and it is what anybody widening this would reach for first.

A number was deliberately NOT allocated by task 92: tasks 86, 91, 93 and 96 are all findings-numbering work, several in flight, and eleven finding-number collisions happened on 2026-08-23.
