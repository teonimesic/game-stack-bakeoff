# What runs automatically, what does not, and why

Every gate in this repository used to run only when a person or an agent remembered to run
it. That is a check with a duty cycle, and the rate was measured above zero: a commit was
pushed while `docstat.py --findings` was exit 1, and the stale-citation rows in `--sweep`
stayed red across several merges because each merge checked the gate it expected to be red
and read past the rest.

Two workflows and two git hooks now run them. **This file is the register of what is
deliberately left out** — a gate excluded and recorded is fine; one silently absent is not.

## The split

| where | budget | what it checks | trigger |
|---|---|---|---|
| `.githooks/pre-commit` | **1.2s** | the findings log, the withdrawal register, the queue — the CONTENT you are about to commit | every commit, once installed |
| `.githooks/pre-push` | **12.0s** | the above plus `docstat --sweep` | every push, once installed |
| `.github/workflows/gates.yml` | **42s** | everything above, plus every control that checks a CHECKER | pull request; push to `main` |
| `.github/workflows/controls.yml` | **521s** | the mutant suites and the skill-layout control | pull request and push touching `eval/**`, `.agents/**` or `.claude/**`; nightly; manual |

The principle the hooks are drawn on: **a hook checks the content, CI additionally checks
the checkers.** A control over a tool changes only when the tool changes, and paying for it
on every commit is how a hook gets bypassed.

## The hooks

    install:  git config core.hooksPath .githooks
    bypass:   git commit --no-verify   /   git push --no-verify
    uninstall: git config --unset core.hooksPath

`.git/hooks/` is not version-controlled, so the hooks live in `.githooks/` where they are,
and `core.hooksPath` points git at them. **The setting lives in the shared git config, so
one `git config` installs it for the main checkout and for every agent worktree at once** —
which is the point, and also why installing it is a deliberate act rather than something a
script does behind you.

Both hooks are two-line wrappers around `.githooks/run-gates.sh`. Two hooks spelling the
same gate list would disagree eventually, and the disagreement would look like the
repository moving rather than like a bug (AGENTS.md rule 12).

**Installing is a live decision, so check the tree first.** While this was being built
`docstat --sweep` was red on `main` for nine `.agents/skills/**` files, and installing
pre-push then would have meant `--no-verify` on every push — the habit these hooks exist to
avoid. Task 114 has since landed and the merged tree is green. Run
`python3 eval/tools/docstat.py --sweep` before installing, not after.

### The queue gate blocks in a checkout and warns in a worktree

`tasks.py` resolves `tasks/` to the **main checkout** on purpose, so from an agent worktree
`tasks.py check` reads a queue your commit does not contain and that peers are writing to
concurrently. Measured while this was being built: it went red on `109: status 'in_review'
not in ('open', 'in_flight', 'done')` — a peer's in-flight edit — and would have blocked a
commit that touched no task file.

So `run-gates.sh` compares `git rev-parse --absolute-git-dir` with `--git-common-dir`: equal
means a real checkout and the gate **blocks**; different means a linked worktree and it
**warns**. CI blocks either way, because there the checkout root is the queue root and the
queue is the committed one.

Both directions are pinned. In a plain clone, `status: banana` in `tasks/99-*.md` makes
`pre-commit` exit 1 naming `tasks.py check`; reverting returns exit 0 and `111 task(s), all
well-formed`. In this worktree the same red queue prints the warning and exits 0.

## Measured, 2026-08-23

Wall clock on the operator's machine (Python 3.14.6, four agents running concurrently, so
an upper bound of unknown tightness) unless stated. Re-measure before relying on these.

| command | exit | time | tier |
|---|---|---|---|
| `docstat.py --selftest` | 0 | 0.1s | pre-commit |
| `docstat.py --findings` | 0 | 0.1s | pre-commit |
| `docstat.py --withdrawn` | 0 | 0.2s | pre-commit |
| `tasks.py check` | 0 | 0.8s | pre-commit |
| `docstat.py --sweep` | 0 | 10.9s | pre-push |
| `.githooks/pre-commit`, whole hook | 0 | 1.2s | — |
| `.githooks/pre-push`, whole hook | 0 | 12.0s | — |
| `lint.py --gate --rule invalid-syntax` | 0 | 0.1s | CI fast |
| `lint_coverage.py --selftest` | 0 | 0.1s | CI fast |
| `ci_minutes.py --selftest` | 0 | 0.04s | CI fast |
| `prompt_guard.py` | 0 | 0.1s | CI fast |
| `manifest_selftest.py` | 0 | 0.3s | CI fast |
| `findings_control.py` | 0 | 0.7s | CI fast |
| `withdrawn_control.py` | 0 | 3.8s | CI fast |
| `triage_control.py` | 0 | 8.4s | CI fast |
| `tasks_control.py` | 0 | 6.4s | CI fast |
| `dead_private_control.py` | 0 | 3.0s | CI fast |
| `backup_evidence_control.py` | 0 | 0.2s | CI fast |
| `hook_audit_control.py` | 0 | 5.7s | CI fast |
| nine `judge/*_selftest.py` | 0 | 3.4s total | CI fast |
| `linkcheck.py` | 0 | 0.1s | CI fast |
| `judge/bot_mutants.py` | 0 | 226.8s | CI slow |
| `tools/tasks_mutants.py` | 0 | 157.0s | CI slow |
| `tools/skill_layout_control.py` | 0 | 124.7s | CI slow |
| `judge/audio_selftest.py` | 0 | 6.1s | CI slow |
| `judge/rusage_selftest.py` | 0 | 7.2s | CI slow |

`tasks_mutants` was **39.0s** before task 109 landed and **157.0s** after it. A tier budget is
a measurement with a date on it, not a property of the tier.

## What is deliberately NOT in CI

| left out | why |
|---|---|
| `judge/starter_parity.py`, `judge/parity_selftest.py` | need the four real toolchains. `parity_selftest` is exit 1 in any tree without `eval/starters/ts/node_modules`, which is untracked |
| `tools/starter_gate_control.py` | **325s measured**, and it drives `godot`, `cargo`, `pnpm`, Unity and `just`. Toolchains are out of scope for CI by decision |
| `tools/evidence_set_control.py`, `tools/disclosure_mutants.py` | both exit 2 `UNMEASURABLE` without `eval/runs/`, which is gitignored (129G) and can never be in a checkout |
| `judge/audit_criteria.py` | **runs, exits 0, and measures nothing without a corpus**: it printed `0 / 0 / 0` for every line of its verdict in a tree with no `eval/runs/`. That is the shape this repository exists to catch, not a gate |
| `docstat.py --renumbered` | never gates, by design — its second half is explicitly undecidable. The half that does gate (the triage register) runs inside `--sweep` |
| `ci_minutes.py` without `--selftest` | it reads the Actions API — one call per run, and the count grows with every push, so gating it would make CI cost grow quadratically in its own history. Its `--selftest` half is offline and IS gated |
| `lint.py --gate` (the whole pinned set) | 64 findings with a standing untriaged backlog. See below |
| anything that spends money or drives the `claude` CLI | trials, judge rounds, `field_sweep.py`, `precampaign_smoke.py`. The operator's call, every time |

## The control: every run that established this

A green CI run establishes nothing on its own — `total=0 passed=0` is indistinguishable from
a correctly-passing suite. These are the runs, on
`https://github.com/teonimesic/game-stack-bakeoff/actions/runs/<id>`, from PR
[#3](https://github.com/teonimesic/game-stack-bakeoff/pull/3).

| run | trigger | workflow | result | what it establishes |
|---|---|---|---|---|
| `32648710508` | `pull_request` | gates | **success**, 50s | the fast tier is green on a clean tree |
| `32648710497` | `pull_request` | controls | **failure**, 31s | `bot_mutants` exit 2, `just` not on PATH |
| `32648869727` | `pull_request` | controls | **failure**, 5m39s | `just` fixed; `audio_selftest` exit 2, no ffmpeg |
| `32649208309` | `pull_request` | controls | **success**, 6m32s | the slow tier is green once both are installed |
| `32649208330` | `pull_request` | gates | **success**, 44s | unchanged by the slow tier's repairs |
| `32649591491` | **push** (`ci-control-green`) | gates | **success** | the push trigger fires and is green |
| `32649595405` | **push** (`ci-control-red`) | gates | **success — the control FAILED** | see below |
| `32651150690` / `32651150781` | `pull_request` | gates / controls | **success**, 46s / 7m02s | green again once `main` was merged in |
| `32651635991` / `32651635966` | `pull_request` | gates / controls | **success**, 52s / 8m40s | green after the CodeRabbit review was addressed |
| `32649678840` | **push** (`ci-control-red`) | gates | **failure** | `README.md: flag --zzqflag matches no argparse in eval/`, at the `docstat --sweep` step, with every other step still reported |

| `32649830893` | `pull_request` | gates | **failure** | `tasks.py check`: `109: status 'in_testing'`, `117: status 'todo'` — see below |
| `32649830894` | `pull_request` | controls | **success** | the slow tier is unaffected by that |

**The `pull_request` event runs against the MERGE of the head into the base, not against the
head.** That failure was not a defect in either branch on its own: `main` had landed task
109's five-status vocabulary (`todo`, `in_progress`, `in_review`, `in_testing`, `done`) while
this branch still carried the three-status `eval/tools/tasks.py` it was forked with. The merge
of the two is red, and nothing either side could run locally would have said so. Merging
`main` in fixed it.

That is the strongest argument in this file for CI existing: **a stale branch is a defect that
only exists in the merge, and only a check that runs on the merge can see it.**

**The first red attempt came out green, and that is the most useful row here.** The planted
phantom flag went into *this* file, and `_check_flags`' inline half only looks at a document
that matches `(wholegame|runner|judge/|evaluate|regrade)\.py`. This file matches it **0**
times; the root `README.md` matches it 8. So the break was invisible, the run was green, and a
green run is exactly what a working gate also produces. Re-planted in the root `README.md`,
the same phantom flag turned the sweep red locally *and* in CI.

That is AGENTS.md rule 12 with the roles swapped: the method was right and the **address** was
wrong, and the wrong answer was the reassuring one. **Verify a deliberate break locally before
pushing it** — `docstat.py --sweep` exit 1 in the working tree — rather than trusting that
breaking something breaks it.

Both control branches were deleted afterwards; the plant never touched `main` or the PR.

## The review

CodeRabbit reviewed PR #3 and posted **4 actionable comments**. All four were acted on; none
was waved away, and one of them was a real fail-open defect:

| finding | verdict |
|---|---|
| `run-gates.sh` never validated its tier argument | **real, and fail-open.** `run-gates.sh pre-pushx` matched neither branch of the `pre-push` equality test, so it silently ran the *pre-commit* set, skipped the 11s sweep and exited 0 — fewer gates and indistinguishable from a hook that worked. Now `exit 2` on an unknown tier, pinned both ways |
| the pre-push hook stated `12.8s` while this file stated `12.0s` | **real.** Two copies of one measurement, already disagreeing. The durations are now stated here only, and the hooks point at this file |
| no `permissions:` block, and the checkout credential persisted | **real.** Both workflows now declare `contents: read` and `persist-credentials: false`. Nothing here needs write access |
| the shallow-clone evidence did not prove the clone was shallow | **raised correctly, and the evidence holds.** `git` does ignore `--depth` on a plain local path; the clone used a `file://` URL. Now asserted with `rev-parse --is-shallow-repository` rather than inferred from a commit count |

## What CI found on its first run

The fast tier was green first time. The slow tier was **red, correctly**: `bot_mutants.py`
exited 2 with `` `just` is not on PATH; these tests cannot run ``.

That is worth recording rather than just fixing. `just` had never been named anywhere as a
dependency of the mutant suite, because on every machine that had ever run it `just` was
already installed for the four stacks. **`eval/judge/fixtures/*` are pure Python** — their
justfiles run `python3` and nothing else — so `just` here is a recipe runner, not a stack
toolchain, and installing it does not breach the no-toolchains rule. It is pinned to
**1.58.0**, the operator's version, and fetched to a file rather than piped into `tar`,
because a pipeline's exit status is the last stage's.

The suite refuses to run rather than reporting zero mutants, which is why this surfaced as a
red build instead of a green one over an empty population.

Two other things the first runs settled:

- `actions/checkout@v4` and `actions/setup-python@v5` annotate every run with a Node 20
  deprecation. Both are now `@v5`/`@v6`. An annotation on every run is how a reader learns to
  skip the output.
- `python-version: '3.14'` resolved to **3.14.7** on the runner against the operator's
  **3.14.6**. Same minor, and both workflows say `'3.14'` deliberately — pinning the patch
  would go stale silently and buy nothing these gates can see.

Every gate step carries `if: ${{ !cancelled() }}`, so one red gate does not hide the verdict
of the others. Without it a broken run reports one failure per push.

## `fetch-depth: 0` is measured, not cargo-culted

`actions/checkout` clones at depth 1 by default. Several gates read blobs at named
revisions, and a shallow clone has no history to measure — which is not the same as a
passing check.

Single-variable comparison, 2026-08-23: a full clone at `3d0c84e`, then
`git clone --depth 1 file:///.../full` **of that clone**, so the two working trees are
byte-identical (`diff -rq` empty) and the only thing that differs is history. The `file://`
matters — git ignores `--depth` on a plain local path — so the shallowness is asserted rather
than assumed:

| | `rev-parse --is-shallow-repository` | `rev-list --count HEAD` |
|---|---|---|
| full clone | `false` | 347 |
| depth-1 clone | `true` | 1 |

| gate | full (347 commits) | depth 1 |
|---|---|---|
| `tasks_control.py` | exit 0, 28 measurements | **exit 3**, 21 measurements, 5 `NOT CHECKED` |
| `withdrawn_control.py` | exit 0 | **exit 1** |
| `dead_private_control.py` | exit 0 | **exit 3** |
| `tasks_mutants.py` | exit 0 | **exit 2** |
| `lint_coverage.py --selftest` | exit 0 | fails — its pins are at `436bf64` |

Every one of them fails closed and says which rows it could not measure, which is the right
behaviour and would still have meant a permanently red CI. Hence `fetch-depth: 0`.

## The lint decision

`lint.py`'s docstring says `--gate` "exists so that whoever wires it into a check later does
not have to touch this file". Wiring the full set in today would mean CI is red on its first
run, and the first thing everyone would learn is how to skip CI.

So CI gates **`--rule invalid-syntax` only** — the subset that is at zero today and can still
go red. Pinned in both directions on 2026-08-23: a file containing `def broken(:` makes
`lint.py --gate --rule invalid-syntax` exit 1; removing it returns exit 0.

Two things a later session needs and should not re-derive:

- The syntax finding's code in ruff 0.16.4 is **`invalid-syntax`**, not `E999`. `--select E999`
  is rejected by this ruff with exit 2, which `lint.py` correctly refuses to read as clean.
- **`lint.py`'s "clean baseline" claim is stale.** Its docstring says every `subprocess.run`
  under `LINT_ROOT` carries an explicit `check=` and every blind `except Exception` carries a
  `# noqa: BLE001`, triaged 2026-08-23. Measured the same day: **10 `PLW1510` and 1 `BLE001`**
  live sites — `judge/blind_dir_selftest.py`, `judge/blind_ext_selftest.py`,
  `judge/starter_parity.py` (x2), `tools/disclosure_mutants.py`, `tools/findings_control.py`,
  `tools/tasks_control.py` (x3), `tools/tasks_mutants.py`, and `tools/tasks_control.py:497`.
  By the docstring's own reading each is "a site nobody has considered". Triaging them is what
  would let the two rules join the gate.

## Minutes: this repository is PRIVATE

`gh repo view --json visibility` returns `PRIVATE` (the MIT licence is a separate setting and
does not buy free minutes). Actions minutes on a private repository draw on a metered monthly
account allowance. **The allowance itself could not be read**: `gh api
/users/teonimesic/settings/billing/actions` returns 404 and asks for the `user` token scope,
which this token does not have.

So the design is lean rather than sized to a known budget:

- `ubuntu-latest` everywhere — Linux bills at 1x, Windows 2x, macOS 10x.
- the push trigger is narrowed to `main`, so agent branches cost nothing until a PR opens.
- `concurrency` with `cancel-in-progress`, so a superseded push stops its own run.
- the 521s tier is behind a path filter and a nightly cron rather than on every event.

### What it has actually cost — read from the API, not estimated

**The producer is `python3 eval/tools/ci_minutes.py`.** Run it rather than quoting the table;
the numbers below are one reading, and its window is part of the number.

| | measured 2026-08-23 |
|---|---|
| **billable minutes to date** | **220** |
| population | 59 completed jobs |
| window | `15:29:33Z .. 18:47:27Z` — 3h18m, the day CI was built |
| raw wall clock | 204.6 min; per-job rounding-up costs the other 15.4 |

| workflow × event | minutes | jobs |
|---|---|---|
| `controls` / `pull_request` | **141** (64%) | 18 |
| `controls` / `push` | 46 | 8 |
| `gates` / `pull_request` | 19 | 19 |
| `gates` / `push` | 14 | 14 |

**This table went from 207 to 220 in the three hours it took to write this section**, because
4 agents were pushing throughout. That is not a caveat on the number — it is the reason the
number needs a command rather than a paragraph, and the reason every figure here carries the
window it was read over.

**Do not turn 220 into a monthly rate, and do not restore the one this section used to
carry.** The window is three hours on the day CI was built, and it includes the CI's own
bring-up — 7 `controls` runs on `task-110-ci-and-hooks` alone. The projection that stood
here was arithmetic over 2 guessed run-rates; nothing produced either, and the copy of it
in `tasks/110`'s body disagreed with the copy in this file, which is what an unproduced
number does. **No monthly rate is derivable from three hours**, so the honest statement is a
measured total with its window and the command that re-derives it. If a rate is ever needed,
run the producer across a window that contains ordinary work rather than the CI's own
construction.

**The billing unit is the JOB, and the field named `billable` is not it.**
`/actions/runs/{id}/timing` exposes `billable.UBUNTU.total_ms`, which read **0 for 58 of 58
runs**. A census that returns one value across the population it exists to discriminate is
reporting the instrument, so `ci_minutes.py` refuses that field, reads job `started_at` /
`completed_at` instead, and rounds each job up to the whole minute. It still reads the field
and prints what it saw. `run_duration_ms` is the other trap: it is the *run*, including the
queue wait — 607000 against its one job's 588s on run `32657248359`.

`cancelled` runs cost **43 minutes over 10 jobs**. That is `cancel-in-progress` working, not
waste: those runs were superseded and stopped early. It is recorded because 21% of the bill
sitting under a conclusion nobody adds up is exactly the sort of figure that gets rediscovered.

### The path filter is evaluated over the whole PR diff, and that is correct

**A `pull_request` path filter matches the accumulated diff of the whole PR, not the latest
push.** Measured with `python3 eval/tools/ci_minutes.py --path-filter`: of 19 `controls` runs
on pull requests, 6 were the first on their branch (no predecessor push, so they match by
construction) and **2 of the remaining 13** were bought by the accumulated diff — both on
`task-110-ci-and-hooks`, both from a push touching only `.github/workflows/README.md`. And
`gates` — which has no path filter — ran exactly as many times as `controls` on all five
branches (7/7, 1/1, 3/3, 3/3, 4/4), so once a PR's diff matches, the slow tier does run on
every subsequent push.

**The audit measures the latest push's diff and never computes the accumulated one, which is
the point rather than a gap.** A `pull_request` workflow is dispatched only when its `paths:`
filter matches, and that filter is defined over the accumulated diff — so a run's *existence*
already establishes that the accumulated diff matched. The tool supplies the other half: that
the push which triggered it matched nothing. Computing the accumulated diff too would
re-derive what the run's existence states.

So the mechanism in the ticket is real. **The change was still rejected, on two measurements.**

**It would be fail-open, on 2 of 2 measured opportunities.** A `pull_request` run is evaluated
against the **merge** of head into base, so the question a filter must answer is not "did this
push touch `eval/`" but "has anything the slow tier reads changed since it last ran" — and the
base moves. In both windows a latest-push filter would have skipped:

| run it would have skipped | `main` commits in the window | touching a filtered path |
|---|---|---|
| `32649830894` | 4 | **3** — incl. `.agents/skills/work/SKILL.md`, `.claude/skills/dispatch/SKILL.md` |
| `32652152099` | 7 | **3** — incl. `eval/tools/tasks.py`, `eval/tools/docstat.py` |

Both would have skipped a run whose merge inputs had genuinely moved. `tasks_mutants.py`
mutates a copy of `eval/tools/tasks.py` and `skill_layout_control.py` reads exactly those
skill paths, so neither is a near-miss. Measured over `main`'s commits **on 2026-08-23**:
**270 of 438 touch a filtered path**. That is a reading of one day, and nothing here
establishes it as a rate — re-run the command below for any other window and use what it
returns rather than carrying 62% forward:

    #!/bin/bash
    set -eu
    REF="${1:-origin/main}"; SINCE="${2:-2026-08-23T00:00:00Z}"
    shas=$(git log "$REF" --since="$SINCE" --format=%H)
    total=$(printf '%s' "$shas" | grep -c '' || true)
    [ "$total" -gt 0 ] || { echo "empty window - refusing to print a ratio" >&2; exit 2; }
    hit=0
    for s in $shas; do
      files=$(git show --pretty= --name-only "$s")
      printf '%s\n' "$files" \
        | grep -qE '^(eval/|\.agents/|\.claude/|\.github/workflows/controls\.yml)' \
        && hit=$((hit+1))
    done
    echo "$hit of $total"

**Two things in that script are the point, and the version printed here until 2026-08-23 had
neither.** First, **ask per sha**: `grep -c` over the concatenated file list counts changed
*files* and silently answers a different question. Second, **fail closed**. The earlier form
ran `git log` in process substitution and let `grep`'s status stand for the pipeline's, so on
a bad ref and on an empty window it printed **`0 of 0` at exit 0** — measured both ways — a
plausible in-range ratio from a command that read nothing, which is the shape `AGENTS.md`
rule 3 exists to forbid. The version above exits 128 on a bad ref and 2 on an empty window,
and prints a ratio in neither case.

The merge-drift exposure is also the defect class this repository has already been bitten by
once: run `32649830893` went red on the merge alone, and the section above calls that the
strongest argument in this file for CI existing.

**And neither implementation is worth having, but for different reasons — one loses minutes,
the other loses the gate.** GitHub bills a minimum of one minute per job. Against a baseline
of **220 billable minutes**, of which `controls` is 187:

| design | minutes saved | minutes added | **net minutes** | what else it costs |
|---|---|---|---|---|
| a separate gating job, then `controls` | 16 (the 2 skipped runs) | +1 × 25 `controls` jobs = +25 | **+9 — spends more than it saves** | — |
| one job, `if:` on the 5 gate steps | ~14 (a skipped run still pays the 36s setup floor) | 0 | **−14, a real 6.4% saving** | a **green `controls` run that executed no gate** |

**The second row does save minutes, and it is still the wrong trade.** What it buys the
saving with is a run that reports success having verified nothing — the single pattern this
repository exists to catch — and, on top of that, both designs are fail-open on the merge
drift measured above. The 14 minutes are real; a `controls` check that cannot distinguish
"passed" from "did not run" is not worth 6.4% of an afternoon's bill.

The setup floor is measured on run `32657248359`: 36s of checkout, `setup-python`, pip, `just`
and ffmpeg against 549s of actual gates. A skipped run cannot cost less than a minute.

**What it would cost to change, if the constraint ever binds.** The `before`/`after` shas are
present in the `pull_request` payload only for `action: synchronize` — `opened` and `reopened`
would have to fall back to running everything — so the implementation is a step computing the
range plus a fallback, in a workflow whose current filter is 4 lines of YAML. The lever to
reach for first is not this one: **`controls` / `pull_request` is 141 of 220 minutes**, and
dropping that trigger for the nightly alone is a two-line change that saves 64% rather than
7.2%. It also trades away per-PR feedback, which is why it is a lever and not a decision.

**Making the repository public would remove the constraint entirely** — Actions is unlimited
for public repositories, and the whole 521s tier could run on every pull request. That is the
operator's call and nobody else's: the history contains every run, every cost figure and
every finding.

## Re-proving the push trigger

Pushing a branch named `ci-control-<anything>` runs both workflows on the `push` event. It
exists so the push path can be exercised without a merge to `main` and without paying for a
run on every agent branch. Delete the branch afterwards.
