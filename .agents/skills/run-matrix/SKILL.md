---
name: run-matrix
description: Launch, watch, diagnose or stop a whole-game evaluation matrix in eval/. Covers the pre-launch checks, the standing turn/budget configuration, the 30-minute heartbeat, wedge diagnosis and safe stopping.
when_to_use: "Starting a matrix, a calibration trial, or a re-run of failed cells; a build looks stalled or wedged; choosing --max-turns or --max-budget-usd; killing a run safely. Trigger phrases: run the matrix, launch trials, is the run stuck, why is it hanging, stop the build, how many parallel."
argument-hint: [run-dir]
---

# Running a matrix

Authoritative reference: `eval/PROTOCOL.md`. This skill is the procedure; that file is
the reasoning and the evidence behind each step. **If they disagree, `PROTOCOL.md` wins
and this file is the bug.**

## 1. Pre-launch checks — all of them, every time

Each has cost trials at least once. Run from `eval/`.

```
python3 tools/runstat.py                     # nothing unexpected already running
blind=$(mktemp -d) && cp -R starters "$blind"/s && \
  python3 judge/verify_blind.py "$blind"/s/*/; ec=$?; rm -rf "$blind"; (exit $ec)   # UNPIPED, read its own exit code
python3 judge/bot_mutants.py                 # UNPIPED
python3 judge/audio_selftest.py              # UNPIPED
find starters -type f -mmin -1440 | wc -l    # starters untouched since last blind check
```

The blind check scans **copies** of the starters made outside the repository; the measured
reason is in `eval/judge/AGENTS.md` (Blinding), and `tools/precampaign_smoke.py` runs the
same scan. The command's exit code is `verify_blind.py`'s own — or that of the stage that
failed before it — and the copies are removed either way.

Then a real capacity probe — a session limit mid-run kills trials that were fine:

```
claude -p "Reply READY." --model haiku
```

**Never pipe a check whose exit code you intend to read.** A pipeline's status is the
last stage's.

## 2. Limits

**Standing configuration: `--max-turns 1000`, no `--max-budget-usd`.**

`--max-budget-usd` is *visible to the agent and instructs it*; `--max-turns` is invisible
and merely truncates. Any stated budget is an instruction — a large cap is still an
instruction, only an absent one is neutral. Measured rate is **0.197 tokval/turn** — read off
`g3_arena__rust__t0` in `wg-arena3d-2026-08-15T12-46-30`, the one uncapped 1000-turn trial:
72.83 over 369 turns, and `python3 eval/tools/runstat.py --run-dir runs/wg-arena3d-2026-08-15T12-46-30`
prints both. **n=1, one stack, one game** — so 1000 turns is a ~197 backstop of the same
uncertainty, not a ceiling.

**And no run here is bounded by a money figure.** A stated cap does two things — it terminates
the trial (`budget_exhausted`) and it instructs the agent — and neither of them protects
anything, because `agent.cost_usd` is a list-price valuation of tokens on a subscription
account (#159, `DECISIONS.md`). What bounds a run is turns, wall clock and rate-limit
capacity.

Do not raise the turn limit while leaving a low budget cap: that governs by the visible
flag while appearing to govern by the invisible one.

## 3. Launch

```
python3 wholegame.py build --run-dir runs/<name> --games <g> --trials N --parallel 2
```

- **`--parallel 2` for engine stacks.** Four concurrent heavy-stack trials wedged
  four-for-four; two has held.
- **Scope every retry with `--only <trial_id>`.** `cmd_build` never consults existing
  records and `prepare()` starts with `rmtree`, so a broad re-run destroys completed work.
- **A running driver holds the prompts it imported**, not the ones on disk. Verify from a
  live trial's `artifacts/<tid>/prompt.txt`, not the source that renders it.
- **`build` ends by printing the blinding check — run it unpiped:**
  `python3 judge/verify_blind.py <work-root>/*/` on the work root it printed. That root is
  outside the repository by design; a stored run directory or `starters/` in place reads
  RUBRIC REACHABLE — true about the path, not the question.
- Verify the flags in the **live process list**, not the config file.

## 4. Watch

Arm a persistent 30-minute heartbeat calling `runstat.py` — recipe in `PROTOCOL.md`. It
must report the tool's own non-zero exit loudly, emit every tick so silence means
"checked, nothing moved", and never reimplement the script's logic. Re-arm it when the
run directory changes.

## 5. Diagnose before killing

**Frozen CPU alone is not a wedge.** An agent inside a running tool consumes none.

The signature is **frozen CPU across two samples minutes apart AND zero descendants**.
Before terminating anything, capture: last tool call (and whether a result was written
after it), child list, engine scan by process *name* with ancestry checked, two CPU
samples. The first four occurrences were killed before anyone thought to look.

## 6. Stop

`pkill -f wholegame.py` stops the driver but **not** the trial agents — they keep
building and writing records. Kill both, verify zero of each, then sweep for engine
orphans by process name.

## 7. After

- Partition by `terminal_reason` before computing anything.
- Read spend from `agent.cost_usd`, never `total_cost_usd`.
- Cross-check the record sum against the build log's `[built]` lines; a retry overwrites
  the record it retried, so records can understate spend.
- Record the run in `eval/RUNS.md` with its limit regime and what it may be compared with.
