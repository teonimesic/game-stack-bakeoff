---
id: 128
title: 241 dollar figures across 6 live documents report token valuations as money
status: todo
priority: 1
refs: 'FINDINGS #159, eval/RUNS.md 132 figures, eval/judge/JUDGING.md 48, eval/PROTOCOL.md 28, DECISIONS.md 21, eval/AGENTS.md 9, AGENTS.md 3, eval/tools/census.py, eval/judge/judge_ledger.py, eval/tools/runstat.py'
done_when: each live document either states the figure as a token valuation with its unit named, or drops it; the producers print a label that cannot be read as expenditure; a check exists that would catch a new live document calling it spend, with its false-positive count on the live corpus measured and stated before it ships; and any conclusion resting on a dollar amount rather than on token counts is re-examined and the outcome recorded either way
---

The account is a subscription, so no per-token charge applies. agent.cost_usd is exactly sum(modelUsage[*].costUSD), a list-price valuation the CLI computes from token counts whatever the billing arrangement. README and DECISIONS.md were corrected at the point the misnaming had changed a decision; the other 241 figures and the 8 producers that print them still say dollars and spend. The token counts are real and every comparison built on them stands - what is wrong is the unit and the noun.
