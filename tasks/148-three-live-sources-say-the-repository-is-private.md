---
id: 148
title: Three live sources say the repository is PRIVATE and its Actions minutes metered; it is public
status: todo
priority: 3
refs: DECISIONS.md, eval/tools/ci_minutes.py, .github/workflows/README.md, .github/workflows/gates.yml, tasks/147
done_when: DECISIONS.md and eval/tools/ci_minutes.py state the repository's visibility as it actually is, read from gh rather than remembered, and the metered-minutes rationale is either restated as history with the present fact stated or replaced by what is decided now; the tier timings live in .github/workflows/README.md only, with DECISIONS.md and .github/workflows/gates.yml pointing at it rather than copying it; ci_minutes --selftest, docstat.py --sweep and linkcheck.py are green
---

gh repo view teonimesic/game-stack-bakeoff --json isPrivate returns isPrivate:false, and .github/workflows/README.md states the repository is public and Linux minutes free and unlimited. Two live sources still say the opposite in the present tense: DECISIONS.md's CI-tier section opens 'The repository is PRIVATE, so Actions minutes are metered' and sizes the whole lean-design rationale on it, and eval/tools/ci_minutes.py prints 'repository : <repo>  (PRIVATE -- these minutes are metered)' on every census. A confidently wrong statement is worse than none, and this one is what a reader consults before deciding whether CI cost is a constraint. The same section also restates the tier timings (pre-commit 1.2s, pre-push 12.0s, gates 42s, controls 521s) that .github/workflows/README.md is the single source for and that DECISIONS.md itself says are not restated there; gates.yml's header comment carries a third copy (42s / 521s). Every one of the four disagrees with the register as of task 147.
