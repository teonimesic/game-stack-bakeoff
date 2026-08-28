# CI and git hooks

Two GitHub Actions workflows and two git hooks. Everything here runs the same checks the
repository already had; the workflows are what make them run without being remembered.

## The two workflows

| | `gates.yml` | `controls.yml` |
|---|---|---|
| runs on | every push and every pull request | every pull request, every push to `main`, nightly at 06:17 UTC, and on demand. On a pull request it **reports always** and **runs its suites only if the diff touches a filtered path** |
| checks | 60 documentation, queue and selftest gates | 11 mutant and control suites |
| needs | Python only | Python, `just` 1.58.0, `ffmpeg` |
| takes | **127–208s** | **706–970s** |

**Every number in that table has a producer, and none of them is remembered.** The check counts
come from `python3 eval/tools/ci_minutes.py --gates`, which reads the workflows and counts steps
invoking something under `eval/`; they are pinned in `ci_minutes --selftest`.

**The `takes` row is a SPREAD, and it is a spread because a point figure there cannot be right.**
It is the full range of the last 12 successful runs of each workflow on `main`, read
2026-08-27 with:

```bash
gh run list --workflow gates.yml --branch main --status success --limit 12 \
  --json startedAt,updatedAt --jq '.[] | ((.updatedAt|fromdate) - (.startedAt|fromdate))'
```

`gates` spans 81s across those 12 runs and `controls` 264s, on content that differs by far less
than that — so a single reading is one draw from a wide band, and the difference between two of
them says nothing about a step. **A timing that looks stale is not evidence that a step was
added, and a step that was added is invisible next to the variance.** **And the band itself is a
reading, not a property of the tier**: both moved clear of the range published two days earlier,
every one of the 24 runs behind this row landing outside it, so re-read the row rather than
trusting the digits in it. For the pull request in
front of you, read the current pair with `gh pr checks <n>`; to size a step, read it per-step out
of `repos/<owner>/<repo>/actions/runs/<id>/jobs`, because the step is what a change moves and the
run is what the runner's noise moves.

**`gates.yml`** covers the doc sweep and its pins, the findings and withdrawal producers,
`linkcheck`, the queue lint, syntax-only lint, the prompt guard with its snapshot diff and its
control, and every other `*_control.py`, `*_selftest.py` and mutant sweep that runs on Python
alone — `cost_census_mutants`, `pr_review_state_mutants` and `mergeable_mutants` are all offline
and about 1 second each. `judge/stored_rounds_mutants` is offline at about 4.3s — it drives a 0.6s selftest 8 times
over a symlinked mirror of `eval/`, once as the control and once per mutant — and its
`--variant-control` is a further 1.7s over 3 more runs.
`docstat --money` runs inside `--sweep`; `tokenvalue --selftest` and
`sweep_bounds_control` are the code-side half of the same question — no producer prints a money
sigil, and no sweep is bounded by a figure nobody is charged (#159). `field_ranks --selftest` and
`weight_sensitivity --selftest` run there too — both offline and under 0.1s locally, as does
`audio_regrade_census --selftest`, whose fixtures are dicts rather than decoded audio and so
needs neither `ffmpeg` nor `just`.
`skill_layout_selftest` is there rather than beside `skill_layout_control` because it needs
no document corpus: it kills a child mid-plant in a throwaway git repository and asks whether
the working tree survives.
`heartbeat_control` runs in about 1s — `time python3 eval/tools/heartbeat_control.py` is
the reading — and asks whether the hourly heartbeat still refuses to report a
count when the **main checkout is not a work tree**. Its red cases are `core.bare=true` read
from the main checkout, the same read from a linked worktree, a `core.worktree` pointing at a
directory that does not exist, and a root that is no repository at all. Its green cases are
`core.bare=false`, `core.bare` absent, and a healthy checkout read from a linked worktree. It
works on throwaway repositories under `$TMPDIR`, restores the configuration in a `finally`, and
carries 1 mutant: the guard removed.
`fragment_control` is 0.42s locally and pins `docstat`'s duplicate-fragment check in both
directions; its `whole_line` mutant is the design measured as a complete false negative, so it
is what stops that being tried again. Its REAL row reads a historical blob, which needs the
`fetch-depth: 0` checkout — in a shallow clone it goes red rather than skipping.
`python3 eval/tools/findings_control.py` prints its own row count and takes about 2.3s locally.
It needs `git` and no history: the count corpus is read from the index rather than from the disk
(#198), so its fixture trees are repositories. One is deliberately left un-`init`ed and must exit
**2** rather than 1, because a tree git cannot list has to stop the producer rather than shrink
its corpus to `RANGE_DOCS` and read clean. Its last row is about the control itself — an
inherited `GIT_DIR` outranks `cwd` silently — so it reproduces that against a decoy repository
before asserting the fixture builder is immune.
`corpus_control` asks which files the sweep reads at all, and its default runs the clean
pass **and all 7 mutants** — 3.9s locally, most of it the 8 fixture repositories. `docstat
--selftest` makes the same clean call, so a gate that only repeated it would duplicate a gate;
the mutants are the reason this one exists, because a clean checkout cannot tell the filesystem
from the index and the glob it replaced passes every live row. It builds throwaway git
repositories under `$TMPDIR` holding markdown that is not in them, so it needs `git` and no
history.
`runner_capture_selftest` is `judge/capture_selftest` pointed at the agent harness: 2.26s
locally, of which 2.0 is a deliberate child timeout, so it spends wall clock rather than CPU and
does not move with the runner.
`judge/ink_window_control` is there rather than in `controls.yml` despite being about frames:
it writes its own PNGs through `judge/png.py` and stubs every subprocess `static.collect`
makes, so it needs neither `just` nor a stack toolchain — 0.6s. It carries `render.nonempty`'s
floor in both directions and the measured derivation for having no ceiling. Its corpus arm reads
`eval/runs`, which is gitignored, and prints `NOT ASKED` in CI rather than a count.
`flag_binding` and `flag_binding_control` are 0.10s and 0.27s locally and read the whole-game
harness alone — its parser as a value and its command functions as an AST, no run directory and
no toolchain. They are here rather than in `controls.yml` for that reason, and they are the only
gate that asks whether a `dest` and the code reading it are still the same name.

**`controls.yml`** covers the suites that need a toolchain or take minutes: `bot_mutants`,
`aim_contract_control`, `scene_mutants` with its `--census-selftest`, its
`--reliability-selftest` and its `--attribution-selftest`,
`scene_runner_control`, `tasks_mutants`, `audio_selftest`,
`rusage_selftest`, `skill_layout_control`.
`scene_runner_control` is the runner's half of the scene question. It names 6 routes from an
operator's command to a grading instrument or a judge pack and drives each one. Every group of
rows carries a mutant or a variant. It grades `judge/fixtures/ref_parallax` through `just`, which
is why it is here rather than in `gates.yml`, and takes about 10s. `aim_contract_control` is there
for the toolchain reason rather than the wall-clock one — 11s, and it drives the arena
fixture through `just probe`.

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
closing line is the producer for how many mutants and variants it carries**, across the workflow
and the tool's own command line.

#### What the scope step must be

The gate reads the step's `run:` line as a command rather than as text, and asks 3 things of it.

| | |
|---|---|
| the shell must run **this** script | the token is resolved against the repository root and compared with `eval/tools/ci_minutes.py`. A suffix is not enough: `nested/eval/tools/ci_minutes.py` is a file a branch can add, and it can write `relevant=false` and exit 0 |
| in front of it, nothing or one interpreter | the shell runs a path containing a slash on its own; otherwise `python` or `python3`, named alone or absolutely. A repository-relative `nested/python3` is the same substitution with the roles swapped |
| the arguments must produce a scope decision | `--scope` must be there, and every other flag must be one `--scope` reads. `--help` parses, is not an error, and would print a help screen and write no `relevant`, so it gets its own answer |

The line is tokenised the way a shell tokenises it, **newlines included** — a `#` comment ends at
its line, so flattening a multi-line block first would let one hide the second command that
overwrites `relevant`. Text that does not tokenise is reported rather than guessed at.

**Each mode of the tool declares which of `--json`, `--cache` and `--no-timing` it reads and
refuses anything else with exit 2.** An accepted-but-ignored flag is worse than an unsupported one
(`AGENTS.md` rule 13): exit 0 is indistinguishable from having done what was asked.

#### Mutants — inputs the check must redden

- a `paths:` or `paths-ignore:` filter back on either trigger
- the scope step deleted, or its `id` renamed
- its command replaced, echoed, or wrapped in `sh -c`
- its command pointed at a same-named script elsewhere, at a different mode, or run under a
  repository-relative interpreter
- its command given a flag `--scope` does not read, a second mode, `--help`, a pipeline, or an
  unbalanced quote
- a second command hidden behind a comment on a multi-line step
- a gate losing its guard, the guard flipped to `== 'true'`, or conjoined with a constant false
- a guarded step placed above the step whose output it reads
- a second `ubuntu-latest` job carrying an unguarded gate, and 4 ways off `ubuntu-latest`
- a scalar `steps:`, and a file that does not parse

#### Variants — inputs it must not redden

- a re-spaced and double-quoted guard, two gates swapped, an unguarded `uses:` step, a comment in
  the job
- the scope step re-spaced, given a quoted script path, or carrying a trailing shell comment
- the scope step run under `python`, under an absolute interpreter path, or executed directly

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

Each tier runs a fixed list, and this is it — not a description of it:

| command | `pre-commit` | `pre-push` |
|---|---|---|
| `python3 eval/tools/docstat.py --selftest` | yes | yes |
| `python3 eval/tools/docstat.py --findings` | yes | yes |
| `python3 eval/tools/docstat.py --withdrawn` | yes | yes |
| `python3 eval/tools/tasks.py check` | yes | yes |
| `python3 eval/tools/ci_minutes.py --selftest` | — | yes |
| `python3 eval/tools/docstat.py --sweep` | — | yes |

`pre-push` runs **6** of `gates.yml`'s **60** checks; `pre-commit` runs **4**.

```bash
python3 eval/tools/ci_minutes.py --hooks
```

**That producer reads the hook by RUNNING it**, not by re-reading the file: `GATES_LIST_ONLY=1
.githooks/run-gates.sh <tier>` prints each gate's argv and executes none of them, so the list
comes out of the same control flow the hook takes. `ci_minutes --selftest` asserts the table
above equals what came back, and goes red if either moves without the other — which is what keeps
a description of a script true (`AGENTS.md` rule 12).

**What the hooks do NOT cover is most of it, and that is the direction that costs you.** No
mutant suite runs before a push and no `*_control.py` does either; the only checkers in either
tier are the two `--selftest` modes above, `docstat`'s and this file's. **A green `pre-push`
confirms those 6 commands and predicts nothing about CI.** The hooks are a cheap filter on the
failures that recur here — stale citations, a malformed queue, and a register overtaken by the
workflow edit in the same commit; the workflows are the gate.

**`ci_minutes --selftest` is in `pre-push` and not in `pre-commit`, and the reason is its duty
cycle rather than its cost.** Its inputs are the two workflows, `.githooks/run-gates.sh`, this
file, the *set* of gate scripts under `eval/`, and the tool itself. Read 2026-08-27, **79** of
`main`'s **678** commits touch one of those, so 88% of commits cannot move its verdict while
every one of them would pay for it — and what it is worth is that a stale register never reaches
CI, which makes a push the last moment it can act:

```bash
{ git log --format=%H main -- .github/ .githooks/ eval/tools/ci_minutes.py
  git log --format=%H --diff-filter=ADR main -- \
      'eval/**/*_control.py' 'eval/**/*_mutants.py' 'eval/**/*_selftest.py'; } | sort -u | wc -l
git log --format=%H main | wc -l
```

**The work-tree guard is in the heartbeat and in NO hook tier, and that is reachability
rather than duty cycle.** When the main checkout is not a work tree, `git commit` there exits
128 **before any hook runs**, so no hook can reach the check. The one place a hook does still
run is a linked worktree, and that is where the state is invisible: `status`, `commit` and
`ls-files` all succeed there. The heartbeat fires hourly whether or not anyone is committing.
`eval/tools/heartbeat_control.py` gates it.

Two things about that population. Editing a gate script is **not** in it — the census reads the
*set* of them, so only an add, a delete or a rename moves the verdict, which is why the second
command filters on `ADR`. And `.github/` is a superset of the three files that matter, taken as
a directory so a fourth workflow needs no edit here; over-counting is the safe direction,
because it can only weaken the case for `pre-push`.
The pair it guards is self-referential — the hook runs the gate, the gate runs the hook in
list-only mode and asserts the table above equals what came back — so `run-gates.sh` counts
`GATES_DEPTH` and refuses past 2 rather than recursing if that control's `python3` shim ever
stops intercepting.

**No hook timing is published.** Both tiers are local wall clock on one machine, and two readings
of `pre-push` on the same host minutes apart have differed by more than the whole `pre-commit`
tier costs. Time the one you care about:

```bash
time .githooks/run-gates.sh pre-commit
time .githooks/run-gates.sh pre-push
```

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

It also prints a **REVIEW STATE** block. That block lists the non-required rollup rows, keeps
their commit-status descriptions, and names the head where the reviewer last wrote. A `CodeRabbit`
row reading `pass` shows only that a round was attempted, not that the current head was reviewed.
The block is informational and gates nothing; `DECISIONS.md`, *A review is reported against the
head it was written at, and never gated*, holds the evidence.

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

**This table is checked, and it is checked for the direction that costs you — a control absent
from it and from every tier.**

```bash
python3 eval/tools/ci_minutes.py --controls
```

It censuses every git-tracked script under `eval/` whose stem ends `_control`, `_mutants` or
`_selftest` — the closed class of scripts whose whole purpose is to be run as a gate — asks
which of them no workflow step and no git hook **names**, and requires each of those to appear
in the `left out` column below. Exit 1 names any that does not, and `ci_minutes --selftest`
runs the live census, so the gate is CI's rather than a command someone has to remember.

**An exclusion is a name AND a reason**, so a row whose `why` cell is blank records that
somebody noticed and goes red — that half is the whole promise this table makes.

Three things it deliberately does not do. It reads the **`left out` column only**, because a
name appearing in a neighbouring row's reason excuses nothing. A span carrying a flag —
`tasks_control --live-squash-refs` — excuses **that mode**, never the script, so a bare row is
the only thing that answers for a script nothing runs. And **gated means NAMED**: a control
reached only through another script is ungated here, which is why `starter_gate_control` and
`disclosure_mutants` need rows despite `precampaign_smoke.py` driving both.

**A bare name excuses a control only while one control answers to it.** `eval/tools/` and
`eval/judge/` share the naming convention, so two controls can come to share a stem — and one
row would then excuse both, so an ungated newcomer would read as recorded. Such a row goes red
naming the candidates; write the repository-relative path, which this reads too.

The reverse direction goes red too: a row here naming a control that a tier **does** run is a
row that outlived its exclusion, and a reader trusting it concludes a live check is not running.

**A gate command is read the way a shell reads it: tokenised, and the token it RUNS matched as a
path resolved against the repository root.** So a quote, a trailing comment, a `./` prefix or an
absolute path all name the same script, while three things name nothing — a different address
(`nested/eval/tools/x_control.py`), a path that is merely an argument (`echo <control>`), and a
repository-relative interpreter in front of it. What the shell runs is the script alone or one of
`python`/`python3` ahead of it, which is the rule the scope step is already held to. Text that
will not tokenise is reported rather than split on whitespace and answered anyway.

**And when an input cannot be read at all — an unparseable workflow, a hook tier that lists
nothing, this file missing or not UTF-8 — both `--controls` and `--hooks` exit 2 naming the
cause**, because reading a producer for its output alone turns one broken file into a report that
every control in the repository is ungated.

| left out | why |
|---|---|
| trials, judge rounds, `field_sweep.py`, `precampaign_smoke.py` | they drive the `claude` CLI. The operator's call, every time |
| `starter_parity`, `parity_selftest`, `starter_gate_control` | need the four real toolchains. `starter_gate_control` is 325s; `parity_selftest` exits 1 without `eval/starters/ts/node_modules`, which is untracked |
| `evidence_set_control`, `disclosure_mutants` | both exit 2 `UNMEASURABLE` without `eval/runs/`, which is gitignored and never in a checkout |
| `wallclock.py` without `--selftest` | it reconciles the two stored clocks over `eval/runs/`, and exits 2 there rather than reporting `0 paired observations`. **Both offline halves ARE gated**: `--selftest` and `wallclock_mutants.py` build their own trees under `tempfile` |
| `judge/audit_criteria.py` | without a corpus it exits 0 printing `0 / 0 / 0` for every verdict line — a green run that means nothing |
| `docstat --renumbered` | never gates by design; its second half is undecidable. The half that does gate runs inside `--sweep` |
| `coderabbit_config.py --schema` | needs the network — it reads the published CodeRabbit schema. **Its offline half, `--constraints`, IS gated**: it walks scalar limits against a cached copy, which is what catches an over-long field voiding the file. Run `--schema` by hand when the schema may have moved; it refreshes that cache. Run it by hand when `reviews.tools` changes; it is the only thing that catches a misspelled tool key, because the schema does not close that object and the key is accepted silently |
| an external-link check | `linkcheck.py` skips `http(s)` schemes: this repository is offline-gradeable and a network check is a different tool with a different failure mode. So a rotted source in `research/` still *looks* sourced. That is acceptable only while `research/` is a prior rather than evidence — **run an external link checker before any measurement rests on an external source** |
| `docstat --count-triggers` | a census, not a gate: it publishes what each REJECTED candidate findings-count trigger would cost, and those rows are meant to be non-zero. Its shipped row is the fact `--findings` already gates on, and `_count_trigger_pins` — run inside `--sweep` — pins every row against a known answer, and compares the SHIPPED row alone against `_stated_counts` |
| `integrity_census.py` | a census, not a gate: it exits 0 on a historical hit by construction. Its control calls the two integrity pins `--sweep` already runs |
| `ci_minutes.py` without `--selftest` | it reads the Actions API once per run, and the run count grows with every push — gating it would make CI cost grow quadratically in its own history. The offline `--selftest` half IS gated |
| `tasks_control --live-squash-refs` | it grades PR #16's real squash pair, and `delete_branch_on_merge` removed that branch — only the checkout that performed the merge still holds the tip, so in CI it is NOT CHECKED (exit 3) rather than a pass. Direction 11c's own fixture squashes for real and **is** gated |
| the full `lint.py` rule set | 100 findings stand untriaged (`lint.py --counts`). CI gates syntax errors only — the subset at zero that can still go red. A gate that is red on day one gets skipped, and skipping is silent |
| `host_perf_probe.py --caps`, `--gpu`, `--spread`, `--drift` | they measure the darwin host they run on: `--caps` needs `taskpolicy`, the other three need a Metal device, and all 4 need the machine to themselves — on a shared runner they would report the runner's neighbours. Each refuses off darwin **by name** rather than passing vacantly. **Its offline half, `--selftest`, IS gated**: it pins the percentile, spread and drift arithmetic every arm reports through, with a mutant per row |

### Which gates read THIS file

Not all of them, and the gap is recorded rather than implied. `.github/` begins with a dot,
`glob("**")` does not descend into it, and until `github_docs()` existed this register was in
no document corpus at all — read by every session, checked by nothing.

| on this file | |
|---|---|
| `docstat --sweep`, unresolved references and structure | **reads it** |
| `ci_minutes --selftest`, the hook table and the coverage sentence | **reads them**, and nothing else does. Reword either and that gate goes red naming the form it needs |
| `ci_minutes --selftest`, the exclusion table | **reads it**, through the live `--controls` census. The table is found by its own header cells, so it may move; delete it, duplicate it, or strip its `\|---\|` row and the gate goes red rather than reading an empty excuse list as a full one |
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

The minutes below are counted in **the unit GitHub bills in** — per job, rounded up to the
whole minute. Whether they are **also a bill** depends on the repository's visibility, and that
is not asserted here.

```bash
python3 eval/tools/ci_minutes.py     # minutes in GitHub's billing UNIT, per workflow and job
```

**The producer reads the visibility itself** — `repos/<owner>/<repo>` `.private`, on every
census — and prints `PUBLIC` or `PRIVATE` in its header, refusing anything that is not `true`
or `false` rather than assuming either. Read it from there, or from `gh repo view
teonimesic/game-stack-bakeoff --json isPrivate`. A sentence here saying which one it is would
be a fourth copy of a fact that changes without telling anyone: the tool went on printing
`PRIVATE -- these minutes are metered` for a day after the repository was made public, and
three documents said the same. `DECISIONS.md` is the one live document that states it, with
that command beside it.

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

**A run the jobs endpoint has nothing for is a third value.** It is printed with its run id and
left out of the total, never folded in as zero. Refusing per run instead would end the census
altogether: such a run stays in the run list for good, and 1 exists — 32774427303, cancelled
before a job was created. The refusal that remains is the one an empty bucket cannot express:
if *no* run yields a job, the endpoint is not answering and the tool reports nothing.

## Adding a gate

1. Add the step to `gates.yml` if it is Python-only and fast, to `controls.yml` otherwise.
2. Prove it can go **red**: break something on purpose, push, and confirm the run fails at your
   step — not merely that the job is not green.
3. Revert.
4. If you leave a gate out, add a row to the table above. A gate excluded and recorded is fine;
   one silently absent is not.

**Writing a new `*_control.py`, `*_mutants.py` or `*_selftest.py` is step 1 of the same list, not
a separate activity**, and `ci_minutes --selftest` is red until it is finished: the script is
either named by a tier or named in the exclusion table. Run `ci_minutes --controls` to see which
side it is on.

**Adding one to a git hook takes 3 edits**: the command goes into `.githooks/run-gates.sh`, a
row goes into the hook table, and the coverage sentence under it gets the new counts.
`ci_minutes --selftest` is red until all 3 are done, and it names which one is missing. That
is deliberate — the hooks are what someone trusts instead of reading the workflows, so their
published list has to be the list.

Every step uses `set -e`; a `run:` block reports only its last command's status otherwise.

**Verify a deliberate break locally before pushing it** — a plant in a file the check does not
read comes back green, and green is the reassuring answer when you are trying to prove a gate
works.

**A tier budget is a measurement, not a property of the tier**, and one merge can move it by
more than the run-to-run noise. Re-read it with `gh pr checks <n>` rather than trusting a number
written here — **not** with `ci_minutes.py`, which answers a different question: it reports
*billable* minutes, per job, rounded up to the whole minute and excluding the queue wait, while
what a merge waits on is elapsed wall clock.
