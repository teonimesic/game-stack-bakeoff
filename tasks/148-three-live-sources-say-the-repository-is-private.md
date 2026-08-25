---
id: 148
title: Three live sources say the repository is PRIVATE and its Actions minutes metered; it is public
status: todo
priority: 3
refs: DECISIONS.md, eval/tools/ci_minutes.py, .github/workflows/README.md, .github/workflows/gates.yml, tasks/147
done_when: DECISIONS.md and eval/tools/ci_minutes.py state the repository's visibility as it actually is, read from gh rather than remembered, and the metered-minutes rationale is either restated as history with the present fact stated or replaced by what is decided now; the tier timings live in .github/workflows/README.md only, with DECISIONS.md and .github/workflows/gates.yml pointing at it rather than copying it; ci_minutes --selftest, docstat.py --sweep and linkcheck.py are green
---

gh repo view teonimesic/game-stack-bakeoff --json isPrivate returns isPrivate:false, and .github/workflows/README.md states the repository is public and Linux minutes free and unlimited. Two live sources still say the opposite in the present tense: DECISIONS.md's CI-tier section opens 'The repository is PRIVATE, so Actions minutes are metered' and sizes the whole lean-design rationale on it, and eval/tools/ci_minutes.py prints 'repository : <repo>  (PRIVATE -- these minutes are metered)' on every census. A confidently wrong statement is worse than none, and this one is what a reader consults before deciding whether CI cost is a constraint. The same section also restates the tier timings (pre-commit 1.2s, pre-push 12.0s, gates 42s, controls 521s) that .github/workflows/README.md is the single source for and that DECISIONS.md itself says are not restated there; gates.yml's header comment carries a third copy (42s / 521s). Every one of the four disagrees with the register as of task 147.

## note 2026-08-24

Narrowed by task 147's review round 1. `DECISIONS.md` is already repaired on PR #25: its CI
section now opens *"The repository is PUBLIC, so Linux Actions minutes are free and unlimited"*
with `gh repo view teonimesic/game-stack-bakeoff --json isPrivate` named beside it, the stale
tier timings (1.2s / 12.0s / 42s / 521s) are gone in favour of the register, and the
141-of-220 / 7% snapshot is replaced by the `ci_minutes.py` producer.

**What is left for this ticket** is the one that needs care rather than a sentence:

- `eval/tools/ci_minutes.py` line ~1338 prints `repository : <repo>  (PRIVATE -- these minutes
  are metered)` on every census, and line ~1368 prints that the allowance could not be read.
  Both are remembered facts in a tool whose whole doctrine is that a number must be read from
  an endpoint. Hardcoding `PUBLIC` is the same defect one value later - the fix is to READ the
  visibility (`gh api repos/{REPO} --jq .private` or `gh repo view --json isPrivate`), with the
  refusal path the rest of the tool already has: any `gh` failure exits 2 naming the endpoint,
  never `|| false`. That is an extra API call on the census path and needs `--selftest` (which
  is offline) left offline.
- `.github/workflows/gates.yml`'s header comment still carries `42s of gates` and `521s of
  mutant suites` - a third copy of a measurement the register is the single source for.
