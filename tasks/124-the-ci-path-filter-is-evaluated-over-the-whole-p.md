---
id: 124
title: The CI path filter is evaluated over the whole pull request diff, so one touch of eval/ buys the slow tier for the life of the branch
status: todo
priority: 2
refs: .github/workflows/controls.yml, .github/workflows/gates.yml, .github/workflows/README.md, tasks/110
done_when: either the workflow only runs the slow tier when the latest push touches its paths, with the before and after minute cost measured on a real branch, or the behaviour is judged correct and the reason is written in .github/workflows/README.md with what it would cost to change; and whichever way it goes, the actual minutes consumed to date are read from an endpoint or an artifact rather than estimated
---

Measured and recorded by task 110's agent, not fixed: a pull_request path filter matches against the accumulated diff of the whole PR, not the latest push. So a branch that touches eval/ once pays the 8m40s controls tier on EVERY subsequent push, including pushes that only edit a markdown file. The repository is private, so Actions minutes are metered against an allowance nobody has been able to read - the billing endpoint needs a scope this token lacks - and the estimate is the same order as a Free-plan allowance rather than comfortably inside it. Today six pull requests each ran controls two or three times.
