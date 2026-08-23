---
id: 88
title: 'README says thirty-seven numbered findings; the log runs to #129'
status: open
priority: 3
refs: README.md line 539 area, AGENTS.md 'Read before changing anything' table, eval/FINDINGS.md, eval/tools/census.py
done_when: census.py (or docstat.py) emits a findings count and a highest-number over eval/FINDINGS.md plus eval/findings/, README.md and AGENTS.md quote it with the command written beside it as the AGENTS.md rule requires, and a control shows the producer disagrees when a finding is added or renumbered
---

Found incidentally under task 78, not looked for. README.md's 'The one thing this project actually learned' section opens 'Thirty-seven numbered findings, and all but a few are instances of one pattern'. eval/FINDINGS.md cites up to #129 and AGENTS.md's own index table says #19-#126 - so the two live documents disagree with each other AND both disagree with the log. This is exactly the shape AGENTS.md names: a count with no producer goes stale forever, because nothing can disagree with it and every restatement agrees with the original to the digit. census.py produces trial, run, game, stack and cost counts and does NOT produce a findings count, which is why this one had nowhere to be checked against. The sentence that follows the number is still true - the pattern claim does not depend on the count - so this is a stale figure, not a wrong conclusion.
