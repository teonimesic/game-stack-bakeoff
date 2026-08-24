---
id: 129
title: gates.yml takes 51.9s in the CI register and has no producer; the real figure moved
status: todo
priority: 3
refs: .github/workflows/README.md, eval/tools/ci_minutes.py
done_when: Either both duration figures in .github/workflows/README.md are produced by a command written beside them, stating the population it measured over (a mean over the last N successful runs of that workflow on main is a defensible population; one run is not, given the 54-78s spread), and the figures are re-read from it - or both figures are deleted and the register says what it does instead. A producer that reports per-STEP durations is worth more than one reporting run wall clock, because the step is what a change moves and the run is what the runner's noise moves. If the conclusion is that the numbers do not earn a producer, deleting them is a complete answer and closes this.
---

The register states gates.yml takes 51.9s and controls.yml 685s, with no command beside either. Task 126 added 14 mutants to cost_census_mutants, and the step is isolated on the CI runner at 2s on main (run 32665742872) against 12s on the task branch (run 32669818592) - so gates.yml gained about 10s and the register was not updated, because nobody can tell what population 51.9s was measured over. Run-level wall clock cannot settle it either: the last 10 successful gates runs on main span 54s to 78s, wider than the delta. ci_minutes.py reads the API and is the producer for BILLABLE MINUTES, which is a different quantity - billing rounds each job up to the whole minute, so it cannot report a 10s change at all. This is the shape AGENTS.md names as the defect rather than a shortfall: a count with a producer goes stale for an hour, a count with none goes stale forever.

## note 2026-08-23

## The gate this was filed from has itself grown — read this before sizing anything

Task 126 landed the ordering adjudication in `cost_census.py` and took
`cost_census_mutants.py` from **21 to 38 mutants**. Measured on the CI runner, per-step,
from `repos/.../actions/runs/<id>/jobs`:

| head | `cost_census_mutants` step |
|---|---|
| `main` (run 32665742872) | **2s** |
| task-126 first push (run 32669818592) | **12s** |
| task-126 review round 1 (run 32670527456) | **47s** |

Round 1's 47s was dominated by one mutant. `sample_never_exact` sets
`EXACT_ASSIGNMENT_LIMIT = 0`, so every fixture takes the sampled path at
`SAMPLE_DRAWS` draws, re-walked once per cluster by the fragility floor. Sizing
`SAMPLE_DRAWS` from the precision it needs (50,000; binomial SE 0.00097 at p=0.05)
rather than the round 200,000 it was, halved it: locally the whole sweep is **17.9s**,
of which `sample_never_exact` is **8.9s** and `limit_checked_after_allocation` is
**1.9s** (that one allocates ~2 GB by design, to prove the memory guard reddens).
Base `--selftest` is **0.19s**.

**So the tier placement is worth re-deciding, and it is not mine to decide inside
another task's PR.** `.github/workflows/README.md` splits the two workflows on cost:
`gates.yml` is "Python only", `controls.yml` is "the suites that need a toolchain or
take minutes". `cost_census_mutants` needs Python only, which is why it is in `gates`,
but it is now the most expensive single step there. **Whoever takes this task should
decide whether the split is by DEPENDENCY or by DURATION** — the register states both
and they now disagree for this one step — and record the answer, because the next
sweep to grow will hit the same question.

A duration producer would make this decidable rather than arguable, which is the
original point of this ticket.

## note 2026-08-23

## Correction — the tier question I raised above has mostly evaporated

The note above is written against a 47s measurement, and that figure did not survive the
review of the PR that produced it. Task 126's round 3 deleted the sampled permutation
path outright (three Major review findings against a code path no stored data exercises),
which removed the mutant that dominated the sweep.

Per-step, on the CI runner, `cost_census_mutants`:

| head | step | mutants |
|---|---|---|
| `main` (run 32665742872) | 2s | 21 |
| task-126 first push (run 32669818592) | 12s | 35 |
| task-126 round 1 (run 32670527456) | **47s** | 37 |
| task-126 round 3 (run 32671635310) | **10s** | 38 |

**So the final cost is +8s over `main` for 17 more mutants**, and `cost_census_mutants`
is NOT the most expensive step in `gates.yml`. **Disregard the tier argument in the note
above** — the dependency/duration split is not in tension at 10s, and moving the gate is
not warranted.

**What survives, and it is the whole ticket:** none of this was visible without reading
per-step timings out of the API by hand, and the register's `51.9s` and `685s` still have
no producer. The 47s figure was real when measured and wrong two hours later, which is
the argument for a producer rather than against it.

## note 2026-08-23

## Measured at triage 2026-08-23 — both published figures are outside the observed range

Taken here so it is not re-derived. `gh run list --workflow <wf> --branch main --status success
--limit 10`, duration as `updatedAt - startedAt`:

| workflow | published in the register | n | min | median | max |
|---|---|---|---|---|---|
| `gates` | **51.9s** | 10 | 54s | **60s** | 78s |
| `controls` | **685s** | 8 | 529s | **666s** | 673s |

**Neither published figure falls inside its own range.** 51.9s is below the minimum of ten runs;
685s is above the maximum of eight. They are not stale-but-close, they are wrong.

**Provenance, since the ticket asks what population 51.9s covered: none.** I copied both numbers
out of task 124's branch at merge and wrote them into the register with no command beside them.
That is #144's shape — and worse than the case #144 records, because there the producer existed
and was not run, while here there was no producer at all. The register's own row telling readers
to re-time with `ci_minutes.py` does not help: billing rounds each job up to a whole minute, so it
cannot report a 10s change and is a different quantity.

**This does not change the tier split**, which is what the register is for: gates is about a
minute and controls about eleven, and that is what decides which tier a check belongs in. Deleting
both figures and saying "about a minute" / "about eleven minutes" is a complete answer, and the
`done_when` already allows it.

**Do not edit `.github/workflows/README.md` until PR #13 lands** — it touches that file.

## note 2026-08-23

## Final figure for task 126's branch — 19s, not the 10s in the note above

The 10s reading was taken at task 126's round 3. Two more commits followed, and the final
merged-branch figure for `cost_census_mutants` is **19s** (gates run 32672293141,
23:00:48 -> 23:01:07), against **2s** on `main`.

The difference from 10s is not more mutants — it is that the memory pins now run their
subject in a **child process** (the fix for a `ru_maxrss` baseline that differed between
macOS and the Linux runner). Two pins x one subprocess each, across 39 mutants plus the
control, is ~80 extra interpreter starts.

**So the settled cost is +17s on `gates.yml` for 18 more mutants and two resource pins**,
and `cost_census_mutants` is still not the most expensive step there. The tier argument in
the first note stays withdrawn.

**Three figures for one step inside one day — 47s, 10s, 19s — all correct when read.**
That is the ticket's own subject, and the reason a producer beats a number in a file.

## note 2026-08-24

## BLOCKED behind task 131 — file conflict, not a dependency of reasoning

131 edits `eval/tools/ci_minutes.py` (moving `controls.yml`'s path filter out of `on:` and into a
step, which changes `filter_problems()`) and `.github/workflows/README.md`. Those are the two
files this ticket exists to change. Do not start until 131 has merged, then re-read both — the
register's structure and `ci_minutes.py`'s surface will have moved under this ticket's assumptions.

Also note: the repository went public on 2026-08-24, so the register's "Minutes" section no longer
describes a bill. If both duration figures survive, they are wall-clock in front of a merge, which
is a stronger reason to produce them properly than metering ever was.
