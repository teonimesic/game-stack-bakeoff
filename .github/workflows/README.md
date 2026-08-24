# CI and git hooks

Two GitHub Actions workflows and two git hooks. Everything here runs the same checks the
repository already had; the workflows are what make them run without being remembered.

## The two workflows

| | `gates.yml` | `controls.yml` |
|---|---|---|
| runs on | every push and every pull request | pushes and pull requests **touching `eval/`, `.agents/`, `.github/`**, plus nightly at 06:17 UTC and on demand |
| checks | 36 documentation, queue and selftest gates | 5 mutant and control suites |
| needs | Python only | Python, `just` 1.58.0, `ffmpeg` |
| takes | **57s** | **669s** |

**Both counts have a producer** — `python3 eval/tools/ci_minutes.py --gates`, which reads the
workflows and counts steps invoking something under `eval/`. It is pinned in
`ci_minutes --selftest`, because this row said **32** for long enough to be wrong by three.

**The two timings are read from a run, not remembered.** Both are from the pull-request runs of
`41488aa` on 2026-08-23 — `gates` [run 32670423986](https://github.com/teonimesic/game-stack-bakeoff/actions/runs/32670423986),
`controls` [run 32670423981](https://github.com/teonimesic/game-stack-bakeoff/actions/runs/32670423981) —
and `gh pr checks <n>` prints them for any pull request. They move whenever a step is added, so
re-read them rather than carrying them forward.

**`gates.yml`** covers the doc sweep and its pins, the findings and withdrawal producers,
`linkcheck`, the queue lint, syntax-only lint, and every `*_control.py` and `*_selftest.py` that
runs on Python alone. `docstat --money` runs inside `--sweep`; `tokenvalue --selftest` and
`sweep_bounds_control` are the code-side half of the same question — no producer prints a money
sigil, and no sweep is bounded by a figure nobody is charged (#159).

**`controls.yml`** covers the suites that need a toolchain or take minutes: `bot_mutants`,
`tasks_mutants`, `audio_selftest`, `rusage_selftest`, `skill_layout_control`.

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
| `pre-commit` | the cheap gates on what you are about to commit | **1.7s** |
| `pre-push` | the full `gates.yml` set | **14.3s** |

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
head**, and it refuses a branch that is **behind its base**. The second is why it exists: on
2026-08-23 `main` went red on a merge where both contributing pull requests were green, because
each had been tested against a base containing neither and one merged 12 commits behind with no
run at its final head.

**GitHub now enforces both natively.** `main` is protected, and the settings are the two
questions above plus the ways round them:

| setting | what it stops |
|---|---|
| required checks `gates`, `controls` | merging with a red or missing check |
| `strict: true` | merging a branch behind `main` — the #12/#13 failure |
| `required_linear_history` | a merge commit on `main`, so squash is the only shape |
| `allow_force_pushes: false`, `allow_deletions: false` | rewriting or removing `main` |
| `required_conversation_resolution` | merging over an unresolved review thread |

**`enforce_admins` is OFF, deliberately.** With it on, every change to `main` needs a pull
request — including the queue commit the dispatch procedure pushes directly, which agents write
into the main checkout. So an admin can still push straight to `main`, and an admin merging with
`gh pr merge --admin` still bypasses the checks. The protection covers the ordinary path and not
the person who broke it last time; `mergeable.py` is what covers that, and it is a step someone
has to run.

This was gated behind a paid plan while the repository was private (403 *"Upgrade to GitHub Pro
or make this repository public"*) — going public is what made it available.

## What is deliberately not in CI

| left out | why |
|---|---|
| trials, judge rounds, `field_sweep.py`, `precampaign_smoke.py` | they drive the `claude` CLI. The operator's call, every time |
| `starter_parity`, `parity_selftest`, `starter_gate_control` | need the four real toolchains. `starter_gate_control` is 325s; `parity_selftest` exits 1 without `eval/starters/ts/node_modules`, which is untracked |
| `evidence_set_control`, `disclosure_mutants` | both exit 2 `UNMEASURABLE` without `eval/runs/`, which is gitignored and never in a checkout |
| `judge/audit_criteria.py` | without a corpus it exits 0 printing `0 / 0 / 0` for every verdict line — a green run that means nothing |
| `docstat --renumbered` | never gates by design; its second half is undecidable. The half that does gate runs inside `--sweep` |
| `coderabbit_config.py --schema` | needs the network — it reads the published CodeRabbit schema. Run it by hand when `reviews.tools` changes; it is the only thing that catches a misspelled tool key, because the schema does not close that object and the key is accepted silently |
| `integrity_census.py` | a census, not a gate: it exits 0 on a historical hit by construction. Its control calls the two integrity pins `--sweep` already runs |
| `ci_minutes.py` without `--selftest` | it reads the Actions API once per run, and the run count grows with every push — gating it would make CI cost grow quadratically in its own history. The offline `--selftest` half IS gated |
| the full `lint.py` rule set | 72 findings stand untriaged (`lint.py --counts`). CI gates syntax errors only — the subset at zero that can still go red. A gate that is red on day one gets skipped, and skipping is silent |

## Minutes

The repository is **public** since 2026-08-24, so Linux Actions minutes are **free and
unlimited**. Nothing below is a bill — it is wall-clock in front of a merge, which is what
`gates` and `controls` being required checks turned it into.

```bash
python3 eval/tools/ci_minutes.py     # billable minutes, per workflow and per job
```

`controls.yml` is the slow tier and a required check, so it is what a merge waits on. Its path
filter is evaluated
against the **whole pull request diff**, not the latest push, so a branch that touches `eval/`
once pays the slow tier on every later push — including pushes that only edit markdown. Narrowing
it was measured and rejected: a pull request run tests the *merge*, and a latest-push filter would
have skipped runs where `main` had moved underneath in a filtered path.

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

**A tier budget is a measurement with a date on it, not a property of the tier.** One control
suite went 39s to 157s when a task landed. Re-time with `ci_minutes.py` rather than trusting a
number written here.
