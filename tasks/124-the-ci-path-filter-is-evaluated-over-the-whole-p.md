---
id: 124
title: The CI path filter is evaluated over the whole pull request diff, so one touch of eval/ buys the slow tier for the life of the branch
status: in_review
priority: 2
refs: .github/workflows/controls.yml, .github/workflows/gates.yml, .github/workflows/README.md, tasks/110
done_when: either the workflow only runs the slow tier when the latest push touches its paths, with the before and after minute cost measured on a real branch, or the behaviour is judged correct and the reason is written in .github/workflows/README.md with what it would cost to change; and whichever way it goes, the actual minutes consumed to date are read from an endpoint or an artifact rather than estimated
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/10
---

Measured and recorded by task 110's agent, not fixed: a pull_request path filter matches against the accumulated diff of the whole PR, not the latest push. So a branch that touches eval/ once pays the 8m40s controls tier on EVERY subsequent push, including pushes that only edit a markdown file. The repository is private, so Actions minutes are metered against an allowance nobody has been able to read - the billing endpoint needs a scope this token lacks - and the estimate is the same order as a Free-plan allowance rather than comfortably inside it. Today six pull requests each ran controls two or three times.

## note 2026-08-23

## Measured, and the change was rejected on the measurement — 2026-08-23

**Both halves of `done_when` are answered below. The path filter is judged CORRECT; the
minutes are read from the Actions API by a new producer, `eval/tools/ci_minutes.py`.**

### The producer, and what it refuses

`python3 eval/tools/ci_minutes.py` reads the Actions API. Three traps it exists to walk past,
each measured rather than assumed:

- **`billable.UBUNTU.total_ms` — the field whose NAME says it is the answer — read `0` for
  58 of 58 runs.** A census returning one value across the population it exists to
  discriminate is reporting the instrument (AGENTS.md rule 12's corollary). The tool refuses
  it, and still prints what it saw, because that is the audit trail.
- **`run_duration_ms` is the RUN, including the queue wait.** On run `32657248359` it is
  `607000` while the single job ran `18:11:50 -> 18:21:38`, which is 588s. Summing it
  over-reports.
- **The billing unit is the JOB**, rounded UP to the whole minute. Truncation is the
  plausible wrong implementation and the tool was deliberately written with it first: the
  selftest went red on 8 assertions. Note that `60s -> 1` passes under BOTH, so a fixture set
  of whole minutes only would have let that mutant survive — the 22s and 61s rows are what
  kill it.

In-flight jobs are a **third value**: not zero minutes, not an error, kept out of the total
and reported separately.

### The measured figure

    python3 eval/tools/ci_minutes.py

**207 billable minutes**, 57 completed jobs, window `2026-08-23T15:29:33Z .. 18:33:59Z`.
Raw wall clock 192.8 min; per-job rounding costs the other 14.2.

| workflow x event | minutes | jobs |
|---|---|---|
| `controls` / `pull_request` | **129** | 17 |
| `controls` / `push` | 46 | 8 |
| `gates` / `pull_request` | 18 | 18 |
| `gates` / `push` | 14 | 14 |

`cancelled` accounts for 43 min over 10 jobs — that is `cancel-in-progress` working, not
waste.

**The retired estimate, for the register's anchor.** The section previously stated
**~2400 minutes a month**, derived from "~30 fast runs/day" and "~5 slow runs/day". Nothing
produced either rate; task 110's own ticket body says ~2200 min/month, so the two published
copies of this estimate already disagreed with each other. It is withdrawn as
`WR-ci-minutes-estimate`. **No monthly rate is derivable from a three-hour window**, and the
window that exists is the day CI was built, including its own bring-up.

### Why the path filter was NOT changed

    python3 eval/tools/ci_minutes.py --path-filter

Of 18 `controls` runs on pull requests, 5 were first-on-branch (no predecessor push, so they
match by construction) and **2 of the remaining 13** were bought by the accumulated whole-PR
diff — both on `task-110-ci-and-hooks`, both from a push touching only
`.github/workflows/README.md`. `gates`, which has no path filter, ran exactly as many times
as `controls` on all five branches, confirming the mechanism: once a PR's diff matches, the
slow tier runs on every subsequent push.

So the ticket's mechanism is real. Two measurements rejected the change anyway:

**1. It would be fail-open, on 2 of 2 measured opportunities.** A `pull_request` run is
evaluated against the MERGE of head into base, so the question is not "did this push touch
`eval/`" but "has anything the slow tier reads changed since it last ran" — and the base
moves underneath. In both windows a latest-push filter would have skipped:

| skipped run | `main` commits in window | touching a filtered path |
|---|---|---|
| `32649830894` | 4 | **3** — incl. `.agents/skills/work/SKILL.md` |
| `32652152099` | 7 | **3** — incl. `eval/tools/tasks.py`, `eval/tools/docstat.py` |

`tasks_mutants.py` mutates a copy of `eval/tools/tasks.py`; `skill_layout_control.py` reads
exactly those skill paths. Neither is a near-miss. Across the day **264 of 429 `main` commits
touch a filtered path**, so the exposure is continuous.

**2. The cheaper implementation costs more than it saves.** GitHub bills a minimum of one
minute per job:

| design | saves | costs | net |
|---|---|---|---|
| separate gating job | 16 min (the 2 runs) | +1 min x 25 `controls` jobs = +25 | **+9 min, worse than nothing** |
| one job, `if:` on the 5 gate steps | ~14 min | a **green `controls` run that executed no gate** | 6.8%, for a run that measures nothing |

Setup floor measured on run `32657248359`: 36s (checkout, setup-python, pip, `just`, ffmpeg)
against 549s of actual gates. A skipped run cannot cost less than a minute.

### A methodological trap the next agent should not re-enter

The first version of the `main`-moved measurement compared git's `%cI` (local, `-03:00`)
against the API's UTC `created_at` **as strings**, and reported **0 main commits in both
windows** — which supports the OPPOSITE conclusion. That is AGENTS.md rule 12 against its own
author: a correct method aimed at an address (a timezone) nobody verified, returning the
reassuring answer. Converting properly gives 4 and 7 commits, 3 filtered in each.

### For the orchestrator: one finding needs a number

**`billable.UBUNTU.total_ms` is a field named for the exact quantity, and it read 0 for 58 of
58 runs.** Anything that had summed it would have reported "0 minutes consumed" — a
confident, in-range, completely wrong number, from the endpoint's own answer to the question.
This is the project's central pattern (a mechanism that runs, reports success and measures
nothing) appearing in a third-party API rather than in our own code, and it is why
`ci_minutes.py` derives minutes from `started_at`/`completed_at` and keeps reading the
`billable` field only as an audit trail. No finding number was allocated, per the work skill.

### Not done, deliberately

The lever that would actually matter is **not** this one: `controls` / `pull_request` is 129
of 207 minutes. Dropping that trigger and keeping the nightly is a two-line change saving 62%
rather than 7.7% — but it trades away per-PR feedback, so it is recorded as a lever in
`.github/workflows/README.md` and left for the operator, not taken here.

## note 2026-08-23

## Review round 1, and a correction to the note above — 2026-08-23

**PR:** https://github.com/teonimesic/game-stack-bakeoff/pull/10

### Correction: the withdrawal-register entry was drafted and then REMOVED

The note above says the ~2400 estimate "is withdrawn as `WR-ci-minutes-estimate`". **It is
not.** I wrote the entry, `docstat.py --withdrawn` went exit 1, and I removed it. The reason
is worth recording because it is structural, not a mistake:

> **A withdrawal-register entry anchored to the agent's OWN ticket cannot go green on the
> agent's branch.** `tasks.py note` writes to the **shared** queue by design, so the anchor
> file in the worktree — and therefore in the branch, and therefore in CI — does not carry
> the retired figure. `docstat.py --withdrawn` reports *"its `match` patterns co-occur in no
> block of its anchor"* and gates the pull request red.

`tasks/` is the only `ARCHIVE_PATHS` entry an agent may write to (`eval/findings/` and
`eval/FINDINGS.md` are forbidden without the ticket saying so), so there is no other anchor
available from a worktree.

What I did instead: **replaced** the figure outright, per *"replace superseded content rather
than annotating it"*. No live document restates it, so nothing needs an exemption.

**The entry is ready to paste if the orchestrator disagrees** — and from the main checkout it
goes green immediately, because this note satisfies the anchor. Fields: id
`WR-ci-minutes-estimate`, kind `figure`, match `["(?<![0-9.])2,?400(?![0-9])", "minutes a
month"]`, anchor `tasks/124-the-ci-path-filter-is-evaluated-over-the-whole-p.md`, replaced_by
`python3 eval/tools/ci_minutes.py`.

### The review found 3 real defects, and 1 of them was mine twice over

6 comments. 4 acted on, 2 declined with replies in-thread.

**The one that matters: `runs-on` was still substring-matched.** I had already found and
fixed exactly this defect for the `paths:` filter — parse per event, do not grep the file as
one blob — and left the runner check four lines above it as `if "ubuntu-latest" not in text`.
That passes a workflow with one ubuntu job and one macOS job, and passes `runs-on:
macos-latest  # was ubuntu-latest`. macOS bills at **10x**, so the 1x multiplier under the
entire published total would have been wrong with the gate green.

> **Fixing an instance of a defect does not fix the defect.** The repair and the survivor were
> in the same function, and I wrote both in the same hour. When a check is repaired, sweep the
> file for the same shape rather than the same string.

Regressing the check to substring form makes all 3 new mutants SURVIVE — that is the control.

**The other two, both real, both fail-open:**

- The compare endpoint caps `files` at **300** and `--paginate` does not paginate that array.
  A push past the cap whose only filtered path sits beyond it scores `no-match`: a wrong
  answer, not a missing one. Now refuses at the boundary, and **the guard is at the
  classification point** in `path_filter_audit`, not only in the API adapter — that is where
  the unknown becomes a verdict. Pinned: 300 raises, 299 still classifies. **The published
  figures are unaffected**: the largest of the 13 compares returned 59 files.
- `--cache` wrote a fixed filename, so two invocations sharing a directory could blend or
  truncate each other's evidence. Now one artifact per invocation, `os.replace`-published.

### What I declined, and why

- **"The producer computes the latest-push diff, not the accumulated PR diff, so 2 of 13 is
  not established."** Declined. The inference has 2 halves and only 1 is a computation: the
  run's **existence** with `event: pull_request` establishes that the accumulated diff matched
  (GitHub dispatches only when the `paths:` filter matches, and that filter is defined over
  the accumulated diff); the tool measures that the latest push matched nothing. Computing the
  accumulated diff would re-derive half of what the run's existence already states.
  **But the docstring was under-explaining** — a careful reader reached the opposite
  conclusion from it — so both halves, and the one-push assumption, are now written out.
- **"Add reference-style links for the findings."** Declined: the section cites no findings.
  It cites Actions run ids, which live on `github.com` and which `linkcheck.py` deliberately
  skips, and a producer command, which re-derives rather than points.

### Do not re-derive these

- **Read all the review comments before answering any.** I acted on the first 3 of 6 because
  a `head -150` truncated the listing; the 3 I nearly missed were the 3 real defects.
- `gh api repos/O/R/pulls/N/comments/<id>` is **404**. The single-comment route is
  `repos/O/R/pulls/comments/<id>`; the reply route is `repos/O/R/pulls/N/comments/<id>/replies`.
- CodeRabbit's body embeds its whole analysis chain. The finding is the line starting `**`;
  everything above it is the shell it ran.

## note 2026-08-23

## The finding is stable as the corpus grows — 2026-08-23, after the round-1 push

Re-running `python3 eval/tools/ci_minutes.py --path-filter` a few hours after the first
reading, with 3 more agent branches having opened and merged in between:

| | first reading | later reading |
|---|---|---|
| `controls` runs on `pull_request` | 19 | **24** |
| first-on-branch | 6 | **8** |
| analysed (have a predecessor push) | 13 | **16** |
| latest push touched a filter path | 11 | **14** |
| **latest push touched NOTHING filtered** | **2** | **2** |

**The analysed population grew by 3 and the wasted-run count did not move.** Both instances
remain the 2 on `task-110-ci-and-hooks` — the branch that was editing
`.github/workflows/README.md` while `.github/workflows/controls.yml` sat in its diff.

This matters for the decision more than the original ratio did. A cost that grows with the
number of pull requests would eventually justify the fix whatever its risk; a cost that is a
**one-off from a single branch editing the CI's own documentation** does not. The saving stays
16 minutes while the denominator climbs, so the case for narrowing the filter gets *weaker*
over time, not stronger.

**Do not restate 2 of 13, or 2 of 16, as a rate.** Run the producer. The numerator has been
constant across 2 readings and the denominator has not, so any ratio quoted from this is a
snapshot of one afternoon.
