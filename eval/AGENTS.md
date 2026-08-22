# eval/ — the measurement harness

Two harnesses share this directory:

| File | Runs |
|---|---|
| `wholegame.py` | The whole-game matrix — "build 3D Tetris" tasks, graded by `judge/` |
| `runner.py` | The spec-change suite — small tasks graded on held-out tests |

The grading machine needs **`ffmpeg` and `ffprobe`** as well as the four stacks' toolchains —
the audio criteria decode every clip rather than trusting its extension.

`FINDINGS.md` is the findings log. `BAKEOFF.md` and `FINE-TUNING-BRIEF.md` document the suite
design. Stored results live in `runs/<name>/`, one directory per run — that is data, not guidance.

**`starters/*/` is the product, not instructions to you.** It is what a building agent reads during
a trial. Any edit changes the thing being measured, must not happen mid-run, and requires
re-running `judge/verify_blind.py`. `judge/starter_parity.py` checks the four stay comparable.

## Checking a run

**`python3 tools/runstat.py`** — the only correct status check. Do not hand-roll one at a
shell prompt; every ad-hoc version written here has been wrong at least once, and a wrong
status reading looks exactly like a right one. `--run-dir` targets a specific run,
`--watch N` re-reports every N seconds. See `PROTOCOL.md` for what it avoids and why.

**Arm a 30-minute heartbeat whenever a run is building**, calling `runstat.py` rather
than reimplementing it, reporting the tool's own non-zero exit loudly, and emitting every
tick so silence means "checked, nothing moved" instead of "monitor is dead". Re-arm it
when the run directory changes. Full recipe and rationale in `PROTOCOL.md`.

## Cost

**Anything that spends money per call**, whatever runs it — an agent trial, a judge field
call, a calibration probe. Trials are ~$11-73 each; judge field calls are $2.82-$8.08.

- **Report measured cost and get authorisation before launching anything that spends at
  scale.**
- **Prefer offline re-grading to any re-run.** `judge/regrade_wholegame.py` and `regrade.py`
  recompute scores from stored tier files.
- **Never extrapolate a projection across a boundary you have not measured across.** Not from
  the cheapest case, not from a pooled mean, and **not from one game to another** — the games
  differ, and so does the cost of judging them.

  This rule existed, was read, and did not fire on 2026-08-16. It was written under a heading
  about *agent trials* and in their vocabulary, so a **judge field call** — same resource,
  different mechanism — was projected from three `g1_pong` calls (mean $4.39) onto
  `g2_tetris3d`, where the first call measured **$8.08, 1.84x**. A `--max-runs 6` sweep priced
  at $131 was really $256, over the ceiling.

  That is this file's own meta-lesson biting: **a rule whose trigger is written as the
  instance that produced it must be re-derived by every reader who meets a different
  instance.** The trigger is now the RESOURCE — money per call — not the mechanism.

- **A budget flag is visible to the callee, so it is an instruction, not just a ceiling**
  (#33). `--per-call-budget` is passed to the judge as `--max-budget-usd`. Changing it between
  rounds makes those rounds non-comparable, so hold it fixed across a sweep even when the
  measured cost is far below it.

## Running trials

- Drive the **`claude` CLI directly**, not the SDK.
- `--setting-sources project` is **mandatory** and empirically verified. Without it the operator's
  global `~/.claude/CLAUDE.md` leaks into every arm and confounds the comparison.
- The matrix runs with a targeted Bash allowlist (`just`, `cargo`, `pnpm`, `git`). Runs with and
  without it are **not comparable** — without one, ~30% of turns are lost to denials, including
  agents blocked from running their own verify gate.
- Cost and tokens come from `modelUsage`, not `usage` — `usage` covers the main loop only and
  excludes subagents.
- Each trial gets a fresh template copy with a baseline commit, so `git diff HEAD` isolates exactly
  what the agent did.

## Controls

Every task needs all three. A negative control alone is not enough — a task whose tests can never
pass looks identical to one that is correctly failing.

| Control | Proves |
|---|---|
| **Negative** | The held-out tests fail on the pristine template |
| **Positive** (gold patch) | A correct implementation makes them pass — *the grader can go green* |
| **Adversarial** | A plausible-looking fake does **not** pass |

`runner.py check-suite` runs the negative control. Verify the positive control before trusting any
task's score.

## Concurrency and artifacts

- **One writer per artifact path, always.** Concurrent writers once produced a file that parsed
  cleanly while holding two spliced documents, and its in-range values were published as fact.
  Write atomically — temp file plus `os.replace`.
- **Judge calls compete with trials for account session capacity.** Run trials first, judge after.
  A concurrent judge fan-out during a matrix contributed to four trials dying on a session limit.
- **Give every judge invocation an explicit long timeout.** The default tool-call limit is shorter
  than a judge pass, and a killed pass looks like a silent crash because piped output never flushes.
- **Archive work trees, don't rely on patches.** A patch can fail to apply; an archive cannot.
  Verify an archive by opening it and counting entries, not by trusting the exit code.
- Trial ids repeat across runs and `prepare()` starts with `rmtree` — **namespace work trees by
  run**, or launching a new matrix will delete an earlier run's submissions.

## Reading results

- **Partition by `terminal_reason` before computing anything.** `completed`, `max_turns`,
  `budget_exhausted`, `api_error` and session-limit aborts are different populations. `runner.py`
  records it for exactly this reason.
- Report `n` per group alongside any aggregate.
- Score per task first, then take the SE across tasks. Pooling across trials is inconsistent.
- Use paired per-task differences for arm comparisons, and Wilson intervals for pass rates.

**This suite resolves large gaps only.** With 2 trials per cell, stacks landing within ~0.015
cannot be separated — and the spec-change suite already failed to separate four stacks that all
scored 6/6. If the results do not separate, say so; do not present an ordering that is noise.
