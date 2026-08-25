---
id: 148
title: Three live sources say the repository is PRIVATE and its Actions minutes metered; it is public
status: in_testing
priority: 3
refs: DECISIONS.md, eval/tools/ci_minutes.py, .github/workflows/README.md, .github/workflows/gates.yml, tasks/147
done_when: DECISIONS.md and eval/tools/ci_minutes.py state the repository's visibility as it actually is, read from gh rather than remembered, and the metered-minutes rationale is either restated as history with the present fact stated or replaced by what is decided now; the tier timings live in .github/workflows/README.md only, with DECISIONS.md and .github/workflows/gates.yml pointing at it rather than copying it; ci_minutes --selftest, docstat.py --sweep and linkcheck.py are green
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/32
established_by: 'PR #32 at 314e22e, all three checks green (gates 1m43s, controls 12m57s, CodeRabbit clean on round 4); ci_minutes now reads repos/<repo> .private live (private=False) and the census runs end to end again at 2479 minutes over 463 jobs with run 32774427303 reported not-counted; 11 code mutants all killed by --selftest, one of which survived first attempt and added the render pins; needs a finding number for the dead-producer defect.'
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

## note 2026-08-25

Done on PR #32 (branch `task-148-ci-minutes-reads-visibility`). What the next agent should not
re-derive:

**The visibility is read now, and refuses rather than defaults.** `fetch_visibility(reader=_gh)`
in `eval/tools/ci_minutes.py` reads `repos/teonimesic/game-stack-bakeoff` `.private` on the
census path only, and accepts nothing but `true`/`false`. `visibility_line()` and
`allowance_lines()` are pure so both branches pin offline; `_print_census` takes `private` with
**no default** on purpose — a default is the remembered value this repair removed, one call site
later. The reader is an argument rather than a monkeypatched global, which is what keeps
`--selftest` offline.

**The census had been dead since 2026-08-24 and nothing knew.** Run **32774427303** (`controls`,
push to `main`, cancelled 2026-08-24T20:32:05Z) was cancelled before any job was created, so its
`jobs` array is empty permanently. `fetch_jobs` raised per run, so `python3
eval/tools/ci_minutes.py` exited 2 on **every** invocation from that moment — the producer two
live documents name for CI consumption could not report anything. It is invisible to CI because
only the offline `--selftest` half is gated, deliberately (`.github/workflows/README.md`, the
excluded-gates table).

Measured before changing anything, over all **464** runs one at a time: **1** run reports zero
jobs; **105 of the other 106** cancelled runs report jobs normally. So *cancelled* is not the
property and nothing tests for it. A jobless run is now the third value the tool already applies
to an in-flight job — excluded from the total, carried by id, printed. The only refusal left is
all-runs-empty, which is a dead endpoint rather than an idle repository.

**This needs a finding number — I did not allocate one.** The claim: *a refusal at the wrong
granularity is an outage.* Fail-closed cost the whole producer over 1 run in 464, silently, for a
day.

**Live figures after the fix** (2026-08-25, and they will move): 2479 minutes in GitHub's billing
unit over 463 completed jobs, window 2026-08-23T15:29:33Z .. 2026-08-25T10:52:07Z, 1 run not
counted.

**No document asserts the repository's visibility except `DECISIONS.md`.** The review's argument,
accepted: re-asserting it beside the command that reads it only shortens the staleness window,
which is how the tool's literal and three documents came to be wrong together. So
`.github/workflows/README.md`, `gates.yml` and `controls.yml` now state no present-tense
visibility — the register says the minutes are counted in the unit GitHub bills in, that whether
they are *also* a bill depends on visibility, and that the producer reads it and prints
`PUBLIC`/`PRIVATE` in its header. `DECISIONS.md` keeps the single statement with `gh repo view
teonimesic/game-stack-bakeoff --json isPrivate` beside it, because this ticket requires it there.

**The tier timings are the register's alone.** `gates.yml` (42s / 521s), `controls.yml` (685s and
a per-suite breakdown, plus `five steps` where `--gates` counts 7) and
`.agents/skills/dispatch/SKILL.md` (`controls is 685s`) all carried copies and all disagreed with
`.github/workflows/README.md`.

**The red half was run and is reproducible from PR #32's body**: 11 mutants applied to a copy of
`ci_minutes.py`, all 11 killed by `--selftest`. One of them — deleting the printed `NOT counted`
line — **survived the first attempt**, because the bucket was recorded and never rendered; that
is why the selftest now renders `_print_census` through `contextlib_redirect_all` and asserts the
run id and the PUBLIC/PRIVATE word in the output. No `ci_minutes_mutants.py` file was added; the
input-driven variants are carried in `--selftest`, the code mutants were session-scoped.
