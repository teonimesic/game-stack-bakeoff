---
id: 123
title: README publishes a cost result with no producer, and it is the last such number in the file
status: todo
priority: 2
refs: 'README.md cost row, eval/findings/limits-and-cost.md #63, eval/tools/census.py, eval/runs/wg-g4c-2026-08-21T02-26-46, tasks/115'
done_when: a producer prints the cost result with the population it counted and a selftest that pins it in both directions; README cites the command beside the figure; and either the published figures are reproduced exactly or the differences are stated with which is right and why
---

Task 115's agent said this in as many words and did not file it: the cost row's figures - the between-stack range as a fraction of the within-cell noise floor, the correlation between cost and turns, and the turn spread - reproduce exactly from the stored trial records, but only via an ad-hoc script that was not shipped. README cites the finding for the field and the method rather than a command. By AGENTS.md's own rule that is the defect, not a shortfall: a quantity with no producer goes stale forever rather than for an hour, and FINDINGS 144 measured that failing twice in one day on a figure whose producer existed and simply was not run. It is now the ONLY number in README with no way to re-derive it.
