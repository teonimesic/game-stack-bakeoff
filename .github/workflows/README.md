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
| `.github/workflows/controls.yml` | **281s** | the mutant suites | pull request and push touching `eval/**`; nightly; manual |

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

**Read this before installing:** the hooks are green on this branch and `docstat --sweep`
was **red on `main`** when this was written — nine `.agents/skills/**` files that task 114
is in the middle of moving. Installing pre-push before that lands means `--no-verify` on
every push, which is the habit these hooks exist to avoid.

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
| `judge/bot_mutants.py` | 0 | 226.3s | CI slow |
| `tools/tasks_mutants.py` | 0 | 39.0s | CI slow |
| `judge/audio_selftest.py` | 0 | 6.1s | CI slow |
| `judge/rusage_selftest.py` | 0 | 7.2s | CI slow |

## What is deliberately NOT in CI

| left out | why |
|---|---|
| `judge/starter_parity.py`, `judge/parity_selftest.py` | need the four real toolchains. `parity_selftest` is exit 1 in any tree without `eval/starters/ts/node_modules`, which is untracked |
| `tools/starter_gate_control.py` | **325s measured**, and it drives `godot`, `cargo`, `pnpm`, Unity and `just`. Toolchains are out of scope for CI by decision |
| `tools/evidence_set_control.py`, `tools/disclosure_mutants.py` | both exit 2 `UNMEASURABLE` without `eval/runs/`, which is gitignored (129G) and can never be in a checkout |
| `judge/audit_criteria.py` | **runs, exits 0, and measures nothing without a corpus**: it printed `0 / 0 / 0` for every line of its verdict in a tree with no `eval/runs/`. That is the shape this repository exists to catch, not a gate |
| `docstat.py --renumbered` | never gates, by design — its second half is explicitly undecidable. The half that does gate (the triage register) runs inside `--sweep` |
| `lint.py --gate` (the whole pinned set) | 64 findings with a standing untriaged backlog. See below |
| anything that spends money or drives the `claude` CLI | trials, judge rounds, `field_sweep.py`, `precampaign_smoke.py`. The operator's call, every time |

## `fetch-depth: 0` is measured, not cargo-culted

`actions/checkout` clones at depth 1 by default. Several gates read blobs at named
revisions, and a shallow clone has no history to measure — which is not the same as a
passing check.

Single-variable comparison, 2026-08-23: a full clone at `3d0c84e`, then `git clone --depth 1`
**of that clone**, so the two working trees are byte-identical (`diff -rq` empty) and the
only thing that differs is history.

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
- the 281s tier is behind a path filter and a nightly cron rather than on every event.

Rough arithmetic, with assumptions stated so they can be corrected: at ~30 fast runs/day
(~1.4 min each including setup) and ~5 slow runs/day (~5.4 min), that is **~2200 minutes a
month** — the same order as a Free-plan private allowance, not comfortably inside it. The
first lever if it binds is the slow tier's `pull_request` trigger, leaving the nightly.

**Making the repository public would remove the constraint entirely** — Actions is unlimited
for public repositories, and the whole 281s tier could run on every pull request. That is the
operator's call and nobody else's: the history contains every run, every cost figure and
every finding.

## Re-proving the push trigger

Pushing a branch named `ci-control-<anything>` runs both workflows on the `push` event. It
exists so the push path can be exercised without a merge to `main` and without paying for a
run on every agent branch. Delete the branch afterwards.
