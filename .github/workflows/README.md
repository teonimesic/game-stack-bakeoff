# CI and git hooks

Two GitHub Actions workflows and two git hooks. Everything here runs the same checks the
repository already had; the workflows are what make them run without being remembered.

## The two workflows

| | `gates.yml` | `controls.yml` |
|---|---|---|
| runs on | every push and every pull request | every pull request, every push to `main`, nightly at 06:17 UTC, and on demand. On a pull request it **reports always** and **runs its suites only if the diff touches a filtered path** |
| checks | 45 documentation, queue and selftest gates | 7 mutant and control suites |
| needs | Python only | Python, `just` 1.58.0, `ffmpeg` |
| takes | **102s** | **685s** |

**Every number in that table has a producer, and none of them is remembered.** The check counts
come from `python3 eval/tools/ci_minutes.py --gates`, which reads the workflows and counts steps
invoking something under `eval/`; they are pinned in `ci_minutes --selftest`. The timings come
from `gh pr checks <n>`, which prints both for any pull request.

**Re-read a timing from a run rather than carrying it forward, and never estimate one by adding
step times.** A single timing is one sample of a noisy quantity, and the run-to-run spread on
unchanged content has measured larger than the cost of a step this repository adds. So a timing
that looks stale is not evidence that a step was added, and a step that was added is invisible
next to the variance — read the current pair rather than reasoning about the difference.

**`gates.yml`** covers the doc sweep and its pins, the findings and withdrawal producers,
`linkcheck`, the queue lint, syntax-only lint, the prompt guard with its snapshot diff and its
control, and every other `*_control.py`, `*_selftest.py` and mutant sweep that runs on Python
alone — `cost_census_mutants` and `pr_review_state_mutants` are both offline and about 1 second
each. `docstat --money` runs inside `--sweep`; `tokenvalue --selftest` and
`sweep_bounds_control` are the code-side half of the same question — no producer prints a money
sigil, and no sweep is bounded by a figure nobody is charged (#159). `field_ranks --selftest` and
`weight_sensitivity --selftest` run there too — both offline and under 0.1s locally.

**`controls.yml`** covers the suites that need a toolchain or take minutes: `bot_mutants`,
`scene_mutants` and its `--census-selftest`, `tasks_mutants`, `audio_selftest`,
`rusage_selftest`, `skill_layout_control`.

### Where `controls.yml`'s filter lives, and why it is not in `on:`

**The filter is a step, not a `paths:` trigger.** A workflow whose `paths:` do not match
produces **no check at all**, not a passing one — and `controls` is a required check, so a pull
request touching only `tasks/` or a root document waits on a check that can never arrive, and
updating the branch does not help. The measurement that established it is in
`ci_minutes.py --scope`'s docstring, beside the code it decided.

So `controls.yml` triggers on every pull request and asks the question inside the job. Its first
step runs `python3 eval/tools/ci_minutes.py --scope`, which diffs the pull request against its
base, matches the result against `FILTER_PREFIXES`/`FILTER_EXACT` — the **single** place the
filter is spelled — and writes `relevant=true|false`. Every step below it is guarded on that.

| | |
|---|---|
| the guard is `!= 'false'`, never `== 'true'` | an output the scope step never wrote reads as the empty string. `!= 'false'` runs the suites on it; `== 'true'` would skip them and report a green `controls` that executed no gate |
| every unknown runs the whole suite | an unreadable diff, an empty diff, and any event that is not `pull_request`. A state where the answer is unknown must never read as "nothing to do" |
| `push` to `main`, `schedule` and `workflow_dispatch` are never filtered | nothing is waiting on those, so latency is not a cost there — and running unconditionally is what **checks the filter's claim**. A filter that is wrong is wrong for at most one merge rather than indefinitely |
| the scope step prints what it read | the filter, the changed paths and the verdict go into the run log, so a skipped `controls` is auditable afterwards |

`python3 eval/tools/ci_minutes.py --selftest` pins the wiring in both directions, and **its
closing line is the producer for how many it carries.** The mutants are a `paths:` or
`paths-ignore:` filter back on either trigger, the scope step deleted, its id renamed, its command
replaced, one gate losing its guard, the guard flipped to `== 'true'`, the guard conjoined with a
constant false, a guarded step placed above the step whose output it reads, a second
`ubuntu-latest` job carrying an unguarded gate, a scalar `steps:`, a file that does not parse, and
4 ways off `ubuntu-latest`. The variants — inputs the check must
**not** redden — are a re-spaced and double-quoted guard, two gates swapped, an unguarded `uses:`
step, a comment in the job, and an extra flag on the scope step.

**The guard is matched WHOLE, against a closed set of 2 accepted expressions**, not by
containment. `${{ ... relevant != 'false' && false }}` contains the guard's exact text and skips
every gate, which is the outcome the guard exists to prevent. `success() && …` is what a setup
step carries and `!cancelled() && …` is what a gate carries; anything else has to be read.

**`controls.yml` must declare exactly 1 job, and the check refuses a second.** The guard is
per-job — `steps.scope.outputs.relevant` names a step in the same job — so a second job would run
unguarded, and it would also be a second check that can be absent, which is why `DECISIONS.md`
rejects the two-job form.

Both pin `ubuntu-latest`, run with `contents: read`, and check out with `fetch-depth: 0` —
several controls read historical blobs and report `NOT CHECKED` rows in a shallow clone.

## The two hooks

Not installed by default. `core.hooksPath` is shared configuration and arms every worktree at
once, so it is the operator's to enable:

```bash
git config core.hooksPath .githooks
```

| | runs | takes |
|---|---|---|
| `pre-commit` | the cheap gates on what you are about to commit | **~2s** |
| `pre-push` | the full `gates.yml` set | **~13s** |

Both are local wall clock and machine-dependent — re-time with `time .githooks/run-gates.sh
pre-commit` / `time .githooks/run-gates.sh pre-push` rather than trusting the column.

Bypass either with `git commit --no-verify` / `git push --no-verify`.

**The queue lint blocks in a real checkout and only warns in a linked worktree.** `tasks.py`
resolves the queue to the main checkout, so from a worktree it reads state your commit does not
contain — a peer's in-flight status change would block a commit that has nothing to do with it.

## Merging

The repository is **squash-only**: `allow_merge_commit` and `allow_rebase_merge` are off, and the
squashed commit takes its subject from the pull request **title** and its message from the pull
request **body**. A task branch lands as one commit; its review rounds stay on the pull request.

**A green pull request is not a mergeable one.** Run the gate before merging:

```bash
python3 eval/tools/mergeable.py <pr>     # exit 1 = do not merge
```

It refuses a required check that is red, still running, or **absent at the pull request's current
head**, and it refuses a branch that is **behind its base**. The second is why it exists: two
pull requests can each be green against a base containing neither, so merging one that is behind
lands a head no run has ever tested — which is how `main` can go red with every contributing
pull request green.

**GitHub now enforces both natively.** `main` is protected, and the settings are the two
questions above plus the ways round them:

| setting | what it stops |
|---|---|
| required checks `gates`, `controls` | merging with a red or missing check |
| `strict: true` | merging a branch behind `main` |
| `required_linear_history` | a merge commit on `main`, so squash is the only shape |
| `allow_force_pushes: false`, `allow_deletions: false` | rewriting or removing `main` |
| `required_conversation_resolution` | merging over an unresolved review thread |

**`enforce_admins` is OFF, deliberately.** With it on, every change to `main` needs a pull
request — including the queue commit the dispatch procedure pushes directly, which agents write
into the main checkout. So an admin can still push straight to `main`, and an admin merging with
`gh pr merge --admin` still bypasses the checks. The protection covers the ordinary path and not
the person who broke it last time; `mergeable.py` is what covers that, and it is a step someone
has to run.

## What is deliberately not in CI

| left out | why |
|---|---|
| trials, judge rounds, `field_sweep.py`, `precampaign_smoke.py` | they drive the `claude` CLI. The operator's call, every time |
| `starter_parity`, `parity_selftest`, `starter_gate_control` | need the four real toolchains. `starter_gate_control` is 325s; `parity_selftest` exits 1 without `eval/starters/ts/node_modules`, which is untracked |
| `evidence_set_control`, `disclosure_mutants` | both exit 2 `UNMEASURABLE` without `eval/runs/`, which is gitignored and never in a checkout |
| `judge/audit_criteria.py` | without a corpus it exits 0 printing `0 / 0 / 0` for every verdict line — a green run that means nothing |
| `docstat --renumbered` | never gates by design; its second half is undecidable. The half that does gate runs inside `--sweep` |
| `coderabbit_config.py --schema` | needs the network — it reads the published CodeRabbit schema. **Its offline half, `--constraints`, IS gated**: it walks scalar limits against a cached copy, which is what catches an over-long field voiding the file. Run `--schema` by hand when the schema may have moved; it refreshes that cache. Run it by hand when `reviews.tools` changes; it is the only thing that catches a misspelled tool key, because the schema does not close that object and the key is accepted silently |
| an external-link check | `research/` alone carries **85** `http(s)` URLs and nothing validates one. Deliberate: `linkcheck.py` skips those schemes because this repository is offline-gradeable and a network check is a different tool with a different failure mode. The consequence is that a rotted source still *looks* sourced — acceptable because `research/` is labelled a prior rather than evidence, and would not be if a measurement rested on one |
| `integrity_census.py` | a census, not a gate: it exits 0 on a historical hit by construction. Its control calls the two integrity pins `--sweep` already runs |
| `ci_minutes.py` without `--selftest` | it reads the Actions API once per run, and the run count grows with every push — gating it would make CI cost grow quadratically in its own history. The offline `--selftest` half IS gated |
| `tasks_control --live-squash-refs` | it grades PR #16's real squash pair, and `delete_branch_on_merge` removed that branch — only the checkout that performed the merge still holds the tip, so in CI it is NOT CHECKED (exit 3) rather than a pass. Direction 11c's own fixture squashes for real and **is** gated |
| the full `lint.py` rule set | 72 findings stand untriaged (`lint.py --counts`). CI gates syntax errors only — the subset at zero that can still go red. A gate that is red on day one gets skipped, and skipping is silent |
| `host_perf_probe.py --caps`, `--gpu`, `--spread`, `--drift` | they measure the darwin host they run on: `--caps` needs `taskpolicy`, the other three need a Metal device, and all 4 need the machine to themselves — on a shared runner they would report the runner's neighbours. Each refuses off darwin **by name** rather than passing vacantly. **Its offline half, `--selftest`, IS gated**: it pins the percentile, spread and drift arithmetic every arm reports through, with a mutant per row |

### Which gates read THIS file

Not all of them, and the gap is recorded rather than implied. `.github/` begins with a dot,
`glob("**")` does not descend into it, and until `github_docs()` existed this register was in
no document corpus at all — read by every session, checked by nothing.

| on this file | |
|---|---|
| `docstat --sweep`, unresolved references and structure | **reads it** |
| `docstat --sweep`, the backticked-flag half | **does not.** It is gated file-wide on 4 harness script names and this file names tools, not harnesses |
| `linkcheck.py` with no arguments | **does not** — `LIVE_DOCS` is the front door and what it links into. Pass the path to check this file |

**The obvious repair to the second row is measurably worse, which is why it is a recorded
exclusion and not a bug.** Widening that trigger from the 4 harness names to the closed class
*"names any script this repository owns"* admits far more documents and every row it adds is
another tool's flag — `gh`, `git`, Godot, Chrome — or a token a task file names as deliberately
fake.

```bash
python3 eval/tools/docstat.py --selftest    # prints the census, and the rows, on today's corpus
```

That is the producer, not a figure: it recounts against the live corpus every run rather than
restating what was true the day it was measured.

**It reports CANDIDATE rows, and they have to be read.** The census applies only the exclusions
the check itself applies and classifies nothing beyond them, so a genuinely unresolved flag of
ours would appear in that list exactly as a `gh` flag does. Adjudicate the rows before treating
the wider trigger as false-positive-only; the last adjudication was 2026-08-24 at 25 rows and
found none genuine.

The higher-damage shape is covered either way — a **bare** flag on a fenced command line, which
is the text a reader copies, is caught here, and the same `--selftest` plants one in this file's
own lines every run to prove it.

## Minutes

The repository is **public**, so Linux Actions minutes are **free and unlimited**. Nothing below
is a bill — it is wall-clock in front of a merge, which is what `gates` and `controls` being
required checks turned it into.

```bash
python3 eval/tools/ci_minutes.py     # billable minutes, per workflow and per job
```

**That producer answers the billing question, not the waiting one.** It counts per job, rounds
each up to the whole minute and excludes the queue wait, so it is the wrong instrument for
*"how long does this tier take"* — use `gh pr checks <n>`, which reports elapsed time, for that.

`controls.yml` is the slow tier and a required check, so it is what a merge waits on. Its filter
is evaluated against the **whole pull request diff**, not the latest push, so a branch that
touches `eval/` once pays the slow tier on every later push — including pushes that only edit
markdown. Narrowing it to the latest push was measured and rejected: a pull request run tests the
*merge*, and a latest-push filter would have skipped runs where `main` had moved underneath in a
filtered path. Moving the filter from `on: paths:` into a step kept that population identical —
the diff taken is the merge commit's first-parent diff, which is what `paths:` was matched
against.

**Do not read `billable.UBUNTU.total_ms` from the API.** It returns `0`. Use the producer above.

## Adding a gate

1. Add the step to `gates.yml` if it is Python-only and fast, to `controls.yml` otherwise.
2. Prove it can go **red**: break something on purpose, push, and confirm the run fails at your
   step — not merely that the job is not green.
3. Revert.
4. If you leave a gate out, add a row to the table above. A gate excluded and recorded is fine;
   one silently absent is not.

Every step uses `set -e`; a `run:` block reports only its last command's status otherwise.

**Verify a deliberate break locally before pushing it** — a plant in a file the check does not
read comes back green, and green is the reassuring answer when you are trying to prove a gate
works.

**A tier budget is a measurement, not a property of the tier**, and one merge can move it by
more than the run-to-run noise. Re-read it with `gh pr checks <n>` rather than trusting a number
written here — **not** with `ci_minutes.py`, which answers a different question: it reports
*billable* minutes, per job, rounded up to the whole minute and excluding the queue wait, while
what a merge waits on is elapsed wall clock.
