---
id: 110
title: Run the gates in GitHub Actions CI and in local pre-commit / pre-push hooks
status: in_progress
priority: 2
refs: .github/workflows/ (does not exist), .git/hooks/, eval/tools/docstat.py, eval/tools/tasks.py check, eval/tools/lint.py, the seven *_control.py files, tasks/108
done_when: a GitHub Actions workflow runs on push and on pull request, goes GREEN on a clean tree and RED on a deliberately broken one with both runs linked in the report; local hooks exist with a documented install step and a documented bypass; the wall-clock cost of each hook is measured and stated; and any gate deliberately left out of CI is named with the reason
---

The operator asked for it on 2026-08-23: now that the work is on GitHub, CI can run the linter and the other verification commands, and local pre-commit/pre-push hooks can catch the same things without waiting for GitHub. The repository is MIT/open source, so GitHub Actions is free for public repositories. Today every gate runs only when a person or an agent remembers to run it, which is the exact shape this project calls a mechanism nobody invokes - and it has already failed at least twice this session: a commit was pushed while docstat --findings was exit 1, and a citation gate stayed red across several merges because nothing ran it automatically.

WHAT THIS IS

This repository has **eleven verification commands** and nothing runs any of them automatically.
They are invoked when a person or an agent remembers to. The skills say to run them; that is a
discipline with a failure rate, and this session measured the rate above zero twice.

WHAT IS WRONG, WITH THE EVIDENCE

- A commit was **pushed while `docstat.py --findings` was exit 1** — a finding body with no index
  row. Caught two commits later, by hand.
- The stale-citation rows in `--sweep` stayed red **across several merges**, because each merge
  checked the gate it expected to be red and read past the rest.
- `main` was **red on itself** for a window when a finding body merged without its index row.

None of these is carelessness that a rule fixes. `AGENTS.md` already says to run the gates
unpiped; the rule fired, was read, and the failures happened anyway. **A check that depends on
being remembered is a check with a duty cycle.**

MEASURED COST, 2026-08-23, on the operator's machine, wall clock

| command | exit | time |
|---|---|---|
| `python3 eval/tools/docstat.py --sweep` | 0 | **21s** |
| `python3 eval/tools/docstat.py --selftest` | 0 | 2s |
| `python3 eval/tools/docstat.py --findings` | 0 | 1s |
| `python3 eval/tools/docstat.py --withdrawn` | 0 | 0s |
| `python3 eval/tools/tasks.py check` | 0 | 1s |
| `python3 eval/tools/lint.py --gate` | **1** | 0s |
| `python3 eval/tools/findings_control.py` | 0 | 1s |
| `python3 eval/tools/withdrawn_control.py` | 0 | 4s |
| `python3 eval/tools/tasks_control.py` | 0 | 7s |

**Re-measure these before you rely on them** — they were taken with four agents running on the
same machine, so they are an upper bound of unknown tightness, and CI hardware is different
anyway.

**`lint.py --gate` is exit 1 today and that is not a bug.** Read `eval/tools/lint.py`'s docstring:
it exits 0 with findings by deliberate decision, `--gate` exists for whoever wires it in later,
and there is a standing untriaged backlog (`B905`/`F401`/`F541`/`B007`/`B023`/`F841`). **You are
that whoever.** Wiring a red gate into CI on day one means the first thing everyone learns is how
to skip CI. Decide: fix the backlog first, gate only the triaged rule set, or leave `lint.py`
advisory and say so. **A gate switched off is worse than a gate never added**, and switching off
is silent.

THE SPLIT THAT MATTERS: WHAT IS FAST ENOUGH TO BLOCK A COMMIT

A pre-commit hook that costs 30 seconds gets bypassed within a day, and `--no-verify` is one flag.
Design for the budget, not for coverage:

- **pre-commit** — only what is nearly free and only on what changed. `tasks.py check` is the
  obvious one: it is 1s and it catches the misfiled-ticket defect that has now happened three
  times. A cheap subset of the doc gates if you can scope them to changed files.
- **pre-push** — the middle tier. Seconds are acceptable here because pushes are rarer.
- **CI** — everything, including the 21s sweep and all seven controls. This is where completeness
  belongs, because nothing is waiting on it.

**State the budget you chose and why.** A hook nobody bypasses is worth more than a hook that
covers everything.

GITHUB ACTIONS

Free for public repositories. Confirm this repository is public before relying on that — if it is
private, minutes are metered and the design changes. `gh repo view --json visibility` answers it.

Requirements:

- **Trigger on `push` and on `pull_request`.** `tasks/108` and `tasks/109` are moving this
  project to a PR-based flow; a workflow that only runs on push would miss exactly the moment a
  review is happening.
- **Python only** — every gate above is `python3` against files in the repo. Do **not** attempt to
  run trials, judges, or anything that spends money or drives the `claude` CLI. See below.
- **Pin the runner and the Python version**, and say which. A gate whose result depends on an
  unpinned toolchain is a gate that will disagree with the operator's machine and be blamed for it.

WHAT MUST NOT GO IN CI

- **Anything that spends money.** Trials, judge rounds, `field_sweep.py`. These cost hundreds of
  dollars and are the operator's call every time.
- **Anything needing the `claude` CLI or an API key.**
- **Anything touching `eval/runs/**`** as anything but read-only. That is stored evidence.
- **Anything needing Unity, Godot, Rust or Node toolchains.** The starter `just verify` recipes
  need real toolchains and are not CI's job here. If you think one belongs, that is a separate
  ticket with its own justification.

THE CONTROL — this is the `done_when` and it is not optional

**A green CI run establishes nothing on its own.** `total=0 passed=0` is indistinguishable from a
correctly-passing suite, and a workflow with a broken step name, a bad path, or a swallowed exit
code goes green forever. Rule 3 applies directly: a shell step's exit status is its last command's,
and `run: |` blocks with several lines report only the last unless you set `set -e` or `-o
pipefail`.

So:

1. Get it green on a clean tree. **Link the run.**
2. **Break something on purpose** — the cheapest is a task file with a bad `status`, which
   `tasks.py check` fails in 1s — push it to a branch, and **link the red run**.
3. Revert.

Do the same for each hook: prove it blocks, then prove it allows.

**Prove each step individually, not just the job.** A job that is green because step 4 silently
did nothing is the failure this whole repository is about.

DOCUMENT THE BYPASS

Hooks need `--no-verify` sometimes, and agents work in worktrees where `.git/hooks` may not be
shared. Say how a hook is installed, whether it is installed automatically, and how to skip it —
**an undocumented bypass gets discovered and used silently; a documented one gets used and
mentioned.** Note that `.git/hooks/` is not version-controlled, so a hook nobody installs is a
hook nobody runs: name the install step and where it is recorded.

WHAT EACH OUTCOME MEANS

- **CI green and red, both linked, hooks installed and measured** — done.
- **A gate turns out to be unrunnable in CI** (needs the operator's machine, needs history a
  shallow clone lacks, is too slow) — name it, say why, and leave it out explicitly. A gate
  deliberately excluded and recorded is fine; one silently absent is not.
- **The repository is private and minutes are metered** — report that, and propose the reduced set
  that fits. Do not enable billing.

## Measured at dispatch, 2026-08-23 — the repository is PRIVATE, and the ticket above assumed otherwise

    gh repo view --json visibility,licenseInfo
    {"licenseInfo":{"key":"mit","name":"MIT License"},"visibility":"PRIVATE"}

**The licence is MIT and the repository is private.** Those are independent settings, and the
free-tier reasoning above rests on the second, not the first. GitHub Actions is unlimited for
*public* repositories; a private repository on the Free plan draws on a **metered monthly
minute allowance** shared across the account.

What this changes:

- **Minutes are a budget.** The 21s sweep plus the seven controls is roughly a minute a run, and
  a workflow on every push to every agent branch multiplies that by the number of agents. Design
  for it: `paths-ignore` for `eval/runs/**`, `concurrency` with `cancel-in-progress` so
  superseded pushes stop, and consider whether every gate needs to run on every push or only on
  the pull request.
- **macOS and Windows runners cost a multiple of Linux minutes.** Use `ubuntu-latest` unless you
  can say why not.
- **Report the actual allowance before designing around it** rather than trusting this paragraph:
  `gh api /users/teonimesic/settings/billing/actions` if the token permits it, and say plainly if
  it does not.

**Making the repository public is NOT yours to decide.** It is outward-facing and irreversible in
the way that matters — the history contains every run, every cost figure and every finding. If the
metered budget turns out to be the binding constraint, **say so and say what public would buy**;
the operator decides.

## What was built, and what the next agent must not re-derive — 2026-08-23

Branch `task-110-ci-and-hooks`, PR
https://github.com/teonimesic/game-stack-bakeoff/pull/3

**`.github/workflows/README.md` is the register.** It holds the tier split, the measured cost
of every gate, every gate deliberately left out with its reason, the run table for the
control, and the minutes arithmetic. Read it rather than this section; this section says only
what a future ticket needs.

**Answers to the questions this ticket asked:**

- The repository is **PRIVATE** and the **allowance could not be read**: `gh api
  /users/teonimesic/settings/billing/actions` returns 404 and asks for the `user` token scope,
  which the `gho_` token does not carry. The design is lean rather than sized, and the
  arithmetic (~2200 min/month, same order as a Free-plan allowance) is in the register with
  its assumptions. Making the repository public was NOT decided here.
- **The lint decision:** CI gates `lint.py --gate --rule invalid-syntax` only. The full pinned
  set stands at 64 findings. The syntax finding's ruff 0.16.4 code is `invalid-syntax`, NOT
  `E999` — `--select E999` is rejected with exit 2.
- **`lint.py`'s "clean baseline" claim was stale the same day it was written**: `PLW1510` and
  `BLE001`, triaged to 0 on 2026-08-23, measured **10 and 1** hours later. `DECISIONS.md` is
  corrected. Triaging those 11 sites is what would widen the CI lint gate.

**Three things that cost time and should not cost it twice:**

1. **A deliberate break that does not break is indistinguishable from a working gate.** The
   first red control run came out GREEN (run `32649595405`). The planted phantom flag went
   into `.github/workflows/README.md`, and `docstat`'s inline-flag half only inspects a
   document matching `(wholegame|runner|judge/|evaluate|regrade)\.py` — that file matches it
   0 times, the root `README.md` 8. **Verify a break is red locally before pushing it.**
2. **`docstat`'s `_DELIBERATELY_FAKE` exempts any line containing `phantom`, `plant`, `does
   not exist` or `do not name them`.** A control flag named `--phantomflag` silently exempts
   its own line. Use a neutral name; `--zzqflag` works.
3. **Two controls had undeclared external dependencies that only a clean machine reveals**:
   `judge/bot_mutants.py` needs `just` (its fixtures are pure Python; `just` is only the
   recipe runner) and `judge/audio_selftest.py` needs `ffmpeg`. Both exit 2 rather than
   reporting an empty population, which is why CI found them instead of passing over them.

**Not done, deliberately:** the hooks are NOT installed. `git config core.hooksPath .githooks`
is shared git config and arms every concurrent agent worktree at once, and `docstat --sweep`
was red on `main` at the time of writing (nine `.agents/skills/**` files, task 114 in flight),
so installing pre-push before 114 lands means `--no-verify` on every push.
