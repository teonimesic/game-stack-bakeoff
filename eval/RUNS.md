# Run ledger

Every agent run, what it cost, and what it may be compared with. Read before pooling any two
runs — most of these are **not** comparable, and the reasons are specific.

**Two numbers, not one.** `records` is the spend represented by the run's surviving trial JSONs
(`agent.cost_usd`); `spent` is the money the run actually cost, summed from the `[built]` lines of
every build log it produced. They differ whenever a cell was retried, because a retry **overwrites
the record of the attempt it is retrying** (FINDINGS #36). Both were re-read from disk on
2026-08-15; neither is carried forward from a previous version of this file.

| run | n | records | spent | terminal | games | task | limits |
|---|---|---|---|---|---|---|---|
| `wg-calib-2026-08-12T12-18-14` | 1 | $10.14 | $10.14 | 1 completed | pong | pre-audio | $25 / 250t |
| `wg-matrix-2026-08-13T14-02-50` | 24 | $355.28 | **$365.13** | 24 completed | all 3 | pre-audio | $25 / 250t |
| `wg-audio-2026-08-14T12-29-42` | 11 | $241.82 | $241.82 | 10 completed, 1 budget_exhausted | pong 8, tetris 3 | **audio** | $25 / 250t |
| `wg-cal48-2026-08-14T14-30-58` | 1 | $4.34 | $4.34 | 1 api_error (session limit) | pong | audio | $48 / 250t |
| `wg-cal48b-2026-08-14T18-53-25` | 1 | $23.75 | $23.75 | 1 completed | pong | audio | $48 / 250t |
| `wg-audio48-2026-08-14T19-55-47` | **16** | $486.27 | $486.27 | 16 completed | pong 8, tetris 8 | **audio** | $48 / 250t |
| `archive-arena2d-wg-audio48` *(superseded, kept)* | 8 | $118.62 | **$130.39** | 3 completed, 1 max_turns, 4 wedged/killed | arena **2D** | audio | $48 / 250t |
| `wg-arena3d-2026-08-15T12-46-30` ⚠️ **NOT COMPARABLE ACROSS STACKS** | 8 | **$374.05** | $374.05 + retries | **8 completed** | arena **3D** | audio + 3D arena | **no cap / 1000t** |

> ⚠️ **`wg-arena3d` IS NOT A FOUR-WAY RESULT.** Its eight cells were built on two different
> machines-in-effect: rust and ts on 15 Aug with `syspolicyd` pegged at ~100% CPU gating
> `execve` of freshly created binaries, unity and godot on 16 Aug after it was restarted.
> Rust and TypeScript link or install new binaries on every build; Unity and Godot run
> pre-existing ones. **Every deduction in the run is on the 15-August side.** The grades are
> correct about the artifacts and say nothing about the stacks. Detail and agent quotes below
> and in FINDINGS #49.

**Cumulative money spent: ~$1,547** (plus **$46.79** of specialist-judge calls on
2026-08-16 — see the judge ledger below), of which **$1,525.57** is represented by surviving records
(re-read from every `runs/*/trials/*.json` on 2026-08-15) and ~$21.61 is overwritten retry
attempts. **This table lists only the `wg-*` whole-game runs, which is $1,433.84 of that.** The
remaining $91.73 is the spec-change bake-off and core suites (`bakeoff-*`, `core-*`), which have
never been in this ledger despite its opening line claiming every run. Recorded here rather than
silently corrected.
The `wg-audio48` and `archive-arena2d` rows together account for the $616.66 that run cost.

> **The two columns are read from different sources and will differ by pennies.** The archive
> row's records sum to $118.62 while its build log's `[built]` lines sum to $118.63: the log
> prints each trial rounded to the cent and the records carry full precision. Stated rather than
> reconciled — a figure quietly adjusted to match another figure is no longer a reading.

> **A row for a live run is a moving number.** `wg-audio48` is still building its last four arena
> trials. An earlier version of this file recorded *$571.15, 19 completed, 5 api_error* — read from
> disk correctly, describing a state that lasted minutes. Mark in-flight rows provisional; a run's
> spend is final only when its terminal reasons are.

## What may be compared with what

Four things break comparability, and all four have bitten:

1. **The task changed — twice.** Audio, presentation and pacing entered every prompt on
   2026-08-14: tier 1 went from 9 criteria to 14, tier 2 gained one. Then on **2026-08-15 the
   arena task was rewritten**: a three-dimensional volume, analog input, three enemy kinds,
   materialisation before an enemy is dangerous, a score multiplier, gamepad and mouse support,
   and on-screen requirements for bursts, boundary reaction and depth. Tier 2 for `g3_arena` went
   from 15 criteria to 22.
2. **The permission allowlist changed.** Without it agents lose ~30% of turns to denials.
3. **The budget cap changed, and the cap is visible to the agent.** See FINDINGS #33. Spend
   responds to the stated ceiling: Tetris ran **$23.20 at $25 and $35.66 at $48, 1.54×**. Every
   cost figure here is partly a measurement of the cap we set, so cost comparisons are valid only
   *within* a cap regime.
4. **The turn limit changed, and at $48 it had already become the binding one.**
   `g3_arena__rust__t1` stopped at 251 turns and $35.75 with $12 of its stated budget unspent
   (FINDINGS #35). From 2026-08-15 the standing configuration is `--max-turns 1000` and **no
   budget cap** — a fourth regime, and the first in which nothing communicates a budget to the
   agent. **Its cost is unmeasured**; calibrate before committing a matrix.

Practically: `wg-matrix` (pre-audio, $25) and `wg-audio48` (audio, $48) are each internally
consistent and mutually incomparable. `wg-audio` at $25 is a partial third regime. Anything built
from 2026-08-15 onward is a fourth, and its arena trials answer a different question from every
arena trial before them.

## "completed" does not mean finished

The calibration trial for the no-cap regime came back at **$72.83 / 369 turns / 118 min**, and
369 turns is 118 past the limit every earlier trial ran under.

> **`terminal_reason: completed` means the agent ended its turn, not that the work was done.**
> Under a binding limit those are different events and the record does not distinguish them.

Every figure in the table below may therefore be a measurement of *where trials were cut off*
rather than of what the task costs. Read them as costs-under-that-ceiling, which is what
FINDINGS #33 already said, plus this: the ceiling may have been binding more often than the
`completed` counts suggest.

**What the calibration does not settle.** It changed the task (2D arena -> 3D arena, tier 2
from 15 criteria to 22) at the same time as both limits, so the 2.04x against
`g3_arena__rust__t1` cannot be attributed to the cap — this file's own first rule is that a
task change is a comparability break, and it applies to our own hypotheses too. Whether the
*completed* capped trials were paced or truncated is **open**; the trials being reinterpreted
came back `completed` rather than `budget_exhausted`, which fits pacing better than truncation.
The experiment that would settle it is one `g2_tetris3d` trial — an unchanged task — under the
no-cap configuration. See FINDINGS #33, corrected.

## ⚠️ THE 3D ARENA SET IS TWO POPULATIONS, DIVIDED BY A MACHINE REPAIR

**Read this before using any `wg-arena3d` number for anything.** Discovered 2026-08-16 by
reading the agents' own `final_text`, which no gate in this harness looks at.

The run's records say `8 completed`, one terminal reason, unremarkable wall clock. It is not
one population. Trial start times, read from the records:

| stack | built | `syspolicyd` | its own `just verify` | graded |
|---|---|---|---|---|
| rust t0, t1 | **15 Aug, 15:46-22:11 UTC** | pegged ~100% CPU for ten days | **never ran** | **0.000, 0.000** |
| ts t0, t1 | **15 Aug, 18:33-22:11 UTC** | pegged | **never ran** | **0.956, 0.956** |
| unity t0, t1 | **16 Aug, 13:47-15:08 UTC** | restarted | green, 0 skips | 1.000, 1.000 |
| godot t0, t1 | **16 Aug, 14:53-16:08 UTC** | restarted | green, 0 skips | 1.000, 1.000 |

`syspolicyd` gates `execve` of freshly created binaries. **Rust and TypeScript link or install
new binaries on every build; Unity and Godot run pre-existing ones.** All four 15-August agents
diagnosed it independently and named it in their reports — one quoting the daemon's CPU minutes
— and shipped work they had never been able to compile or run, saying so explicitly.

Every deduction in this matrix is on the 15-August side of that line.

- **The grading is correct.** The rust submissions do not compile (`E0502`), the ts submissions'
  own render tests fail. The grader reports that and must keep reporting it.
- **The comparison is void.** No stack claim can be drawn from `wg-arena3d` in either
  direction, and the cost table below inherits the same split.

Full mechanism and quotes: FINDINGS #49.

> **Partition by `terminal_reason`, and also by anything about the world that changed while the
> run was in flight.** A run is not a controlled experiment merely because it is one command.

## The 3D arena set, complete — and the cost result is a NULL

8 of 8 completed, no failed populations. Read with `tools/runstat.py`.

| stack | t0 | t1 | mean |
|---|---|---|---|
| ts | $34.27 (239t) | $41.66 (231t) | **$37.97** |
| godot | $46.26 (250t) | $40.48 (280t) | **$43.37** |
| unity | $46.42 (242t) | $47.27 (238t) | **$46.85** |
| rust | **$72.83 (369t)** | $44.86 (240t) | **$58.85** |
| **all** | | | **$46.76 (n=8)** |

**Do not read that as an ordering.** The four stack means span $37.97-$58.85. **Rust's
within-cell spread alone is $44.86-$72.83** — one cell varies more than the four stacks differ
from each other — and rust's mean is pulled up entirely by a single 369-turn outlier. Three of
the four cluster within $9. With n=2 per cell and a spread that wide, **the honest statement is
that cost does not separate these stacks.**

That is the same null the deterministic tiers have produced across three games, arriving
independently through a metric nobody designed as a discriminator.

### Unity is mid-pack, and that retires a story this project nearly told twice

Two earlier attempts to measure Unity on the arena task produced **zero usable data**, both to
harness defects (FINDINGS #43): a project-wide lock that deadlocked an agent's own background
shells, and before that a session limit. On both occasions the raw numbers would have read as a
large Unity deficit.

Measured on a healthy machine with the lock fix: **Unity $46.85, Godot $43.37** — indistinguishable.
Four for four now: every stack-correlated signal in this project has turned out to be an
instrument defect. See FINDINGS #40.

## PENDING: the one-variable experiment that settles paced-vs-truncated

Pre-registered before it runs, because a prediction written afterwards is not a prediction.

**Cell:** `g2_tetris3d__rust__t1` — chosen because it already carries two points, and the two
capped runs sent **byte-identical prompts** (sha256 `7a07f516aece1834`, 7525 bytes, verified).

| condition | cost | turns | terminal |
|---|---|---|---|
| $25 cap, 250 turns | $24.33 | 163 | completed — stopped at **97% of budget** |
| $48 cap, 250 turns | $42.62 | **232 of 250** | completed — neither ceiling bound |
| **no cap, 1000 turns** | ? | ? | the experiment |

**Held identical:** stack, game, cell, starter (verified unmodified), allowlist, model, settings.
The prompt is sent **verbatim from the stored file** via `--prompt-file`, because `_preamble()`
was edited for the arena rewrite and now differs from what those trials received (FINDINGS #41).

**The one variable is the budget flag.** The turn limit is deliberately RAISED, not held:
the $48 run used 232 of its 250 turns, so a 250-turn ceiling could truncate an uncapped run
that wants 300 and return ~$49, supporting *"the stated budget pulled work short"* when the turn
limit did. A ceiling that may be binding is not a control (AGENTS.md rule 8, qualifier) — raise
it and let the measurement report whether it bound.

**Report turns as prominently as dollars. The turn count is doing as much work here.**

| outcome | reading |
|---|---|
| **~$42, under 250 turns** | the cap was irrelevant once non-binding; the $25 row's stop at 97% of budget was **pacing** |
| **~$42, over 250 turns** | the $48 run was **turn-bound, not finished** — another instance of "ended its turn" ≠ "did the work", and it reinterprets the $42.62 row |
| **materially above $50** | the stated budget **was** pulling work short, and the truncation reading is right |

Runs **after** the seven arena trials, not alongside: `--parallel 2` was bought with wall clock
to reduce concurrency risk, and a third concurrent trial spends that protection to save an hour.

## Cost by game and regime

Completed trials only, per FINDINGS #22 — never pool across terminal reasons.

| game | pre-audio, $25 | audio, $25 | audio, $48 | no cap / 1000t |
|---|---|---|---|---|
| pong | $11.30 (n=8) | $21.02 (n=7) | $25.13 (n=8) | — |
| tetris3d | $19.49 (n=8) | $23.20 (n=3) | $35.66 (n=8) | — |
| arena (2D spec) | $13.62 (n=8) | — | $27.63 (n=3) + 1 `max_turns` at $35.75 | — |
| arena (3D spec) | — | — | — | **$46.76 (n=8)**, range $34.27-$72.83 (**2.13x**), turns 231-369 |

Adding audio roughly **doubled** Pong's cost at a fixed cap (1.86×), with turns up 1.53× — more
work, not costlier work.

## The 2D arena set is superseded evidence, and is kept — ARCHIVED 2026-08-15

Moved to `runs/archive-arena2d-wg-audio48/` with its records, artifacts and work trees, so
`cmd_report` cannot include it and no re-run can `rmtree` it. Verified: 16 records left in
`wg-audio48` (pong and tetris only), 0 arena records, 8 tarballs each opened and counted.
Full rationale in that directory's `README.md`.

`wg-audio48` is therefore now a **16-trial, two-game run**, and its spend line above is the
16 records only. The arena money moved with the arena trials.

## Two arena trials were killed, and their `terminal_reason` is `None`

`g3_arena__unity__t0` and `g3_arena__godot__t0` were `SIGKILL`ed on 2026-08-15 after 2h10m
and 2h04m elapsed against **5.13 s and 4.55 s of CPU time**, with no agent turn recorded for
94 and 97 minutes, no child processes, and a passing capacity probe. Both ignored `SIGTERM`.
They were wedged, not slow. Diagnostic method: `PROTOCOL.md`, "What to do instead".

Killing them cost nothing that will be graded — both are 2D-spec submissions bound for the
archive — but it exposed a gap worth naming: **a killed agent produces a record whose
`terminal_reason` is `None`**, printed as `$0.00 turns=None None`. `None` is not a population
label, and rule 4 says to partition by terminal reason before computing anything. Treat
`None` as its own population meaning *the harness never got a result document*, and do not
merge it with `api_error`.

## All FOUR heavy-stack arena trials wedged; rust and ts completed

The 2D arena retry launched eight trials. Measured outcome, and the split is not random:

| stack | outcome |
|---|---|
| ts t0, ts t1 | completed, $28.30 / $26.23 |
| rust t0 | completed, $28.35 |
| rust t1 | `max_turns` at 251 turns, $35.75 |
| **unity t0, unity t1, godot t0, godot t1** | **all four wedged** — alive, zero CPU accumulation, no agent turn for 60-97 minutes |

Four of four on the two stacks that launch a real engine (Unity opens an editor per verify,
Godot opens a window); zero of four on the two that are headless. **This project's prior for a
failure that lands on a strict subset of arms is that it is an instrument defect, not a
result** — that is FINDINGS #25, #26 and #28, three times over, each consistent enough to look
like a finding.

### What was captured before killing anything

The last recorded tool call of each of the two still-alive wedged agents:

| trial | last `tool_use` |
|---|---|
| unity t1 | `Bash: just bless 2>&1 \| tail -10` — regenerate the golden image |
| godot t1 | `Bash: just film 7 1400 - .scratch/frames 2>&1 \| tail -3` |

Both are engine-invoking recipes, on the two stacks that launch a real engine, which makes a
tidy story: concurrent editors and windows contending and deadlocking. **That story is not
supported.** Checked before writing it down:

- the wedged agents have **no child processes at all**;
- **no Godot or Unity binary is running anywhere on the machine**;
- neither agent has accumulated CPU in 40 minutes.

So nothing is blocked on an engine. The engine exited; the agent did not continue. Two
readings remain and the evidence does not separate them: the agent is stuck waiting on an API
response that never arrived and never retried, or it died in flight and the tool result was
never written. Both are consistent with everything measured.

**Recorded as an observation, not a diagnosis.** These are 2D-spec trials bound for the
archive, so nothing downstream depends on resolving it — and a mechanism invented to fit a
stack-correlated split is precisely what #25, #26 and #28 each turned out to be. The
"contending engines" story was one check away from being written here as fact.

**Watch for it in the 3D arena run.** It would land on the same two arms and silently cost
half the matrix. If it recurs: capture the last transcript entry, check for descendants and
for live engine binaries *before* killing anything, and record whether the last tool call had
returned.

## The Unity starter changed on 2026-08-16 — a fifth comparability break

`tools/unity-compile.sh` now compiles against a copy of the project, under a lock held only
for the copy, with a 900 s watchdog. Before this, two concurrent Unity commands in one trial
deadlocked silently and forever (FINDINGS #43); two now finish in 6.4 s.

**Trials built before and after this change are not strictly comparable**: the Unity arm
gained a guard whose absence destroyed two arena cells. The change is confined to
`starters/unity/tools/`; no game code, no prompt, no criterion moved.

Measured, idle machine: single 5.2 s · two concurrent 6.4 s · stale lock reclaimed 4.6 s ·
compile errors name the real tree, not the temp copy · clean run after 4.4 s.

The machine also changed: `syspolicyd` had been pegged at 102% CPU for ten days and was
restarted on 2026-08-16, dropping load from 6.28 to 3.87. Every wall-clock figure recorded
before that is suspect.

## The starters and the arena prompt changed on 2026-08-16 — a SIXTH comparability break

**Anything built from 2026-08-16 onward is not strictly comparable with anything before it.**
Three changes, in descending order of how much they matter.

### 1. The mouse-aiming clause moved out of `_preamble()` — the actual fix for #41

FINDINGS #41 recorded that a clause added for the 3D arena ("`just run` ... playable with a
mouse where the game calls for aiming") had been put in the **shared** preamble, so it entered
Pong, 3D Tetris and the platformer as well. The response at the time was a guard
(`tools/prompt_guard.py`) that would *detect* a recurrence. The clause itself was still there.

It is now removed from the preamble, and the arena body carries the requirement instead.
**Verified by diffing the RENDERED prompts, not the source that renders them**, which is what
#41 says to do:

| game | occurrences of "mouse" in the rendered prompt, before -> after |
|---|---|
| `g1_pong` | 1 -> **0** |
| `g2_tetris3d` | 1 -> **0** |
| `g4_platformer` | 1 -> **0** |
| `g3_arena` | 3 -> **3** (unchanged in substance; the clause moved into the body) |

All four games' prompts change on all four stacks, so **this is a task change and breaks
comparability with every previous run** — including, deliberately, the pre-registered
`g2_tetris3d` cost experiment, whose whole design was a byte-identical prompt. That experiment
must be run with `--prompt-file` against the stored prompt, which is exactly why the flag
exists.

### 2. Audio silenced on the two stacks that open an audio device

`godot`: `--audio-driver Dummy` on the windowed render recipes (the headless ones already imply
it). `unity`: `-disable-audio` on all five invocations.

**Premise verified before changing anything:** grading never plays audio. `judge/audio.py`
decodes each clip with `ffmpeg ... -f f32le -ac 1 -ar N -` **into a pipe** and analyses the
samples; a grep for every playback API (`afplay`, `aplay`, `sounddevice`, `pyaudio`,
`playsound`, `.play()`) across `judge/`, `tools/` and `wholegame.py` returns **nothing**. The
8-cell tetris field decodes 56 clips and plays zero. So silencing cannot change a criterion.

Rust and TypeScript need no change: the rust starter has no audio dependency at all
(`bevy_audio` appears only in the boundary test's **ban** list) and the ts render path is
headless Chromium with no `AudioContext`.

Verified after: godot `test-render` 6/6 exit 0, unity `test-render` 6/6 exit 0, unity `probe`
still emits its trace.

### 3. Godot render window set NO_FOCUS and moved offscreen — AN UNVERIFIED GUARD

`tests/render_test.gd` now calls `DisplayServer.window_set_flag(WINDOW_FLAG_NO_FOCUS, true)`
and moves the window to (-4000, -4000), skipped under the headless driver.

> ⚠️ **The behaviour it is meant to prevent could not be reproduced on this machine, and the
> verification asked for could not be performed.** Recorded as a guard, not a fix.

What was measured:

| check | result |
|---|---|
| two concurrent windowed godot render suites, with the change | **both 6/6, exit 0** — the change is harmless |
| the same, with the change removed (negative control) | **also no focus taken** |
| unity `test-render`, real graphics device | **no focus taken** |
| a Godot GUI process visible to `System Events` at 0.15 s sampling | **never appears at all** |
| **positive control: can the probe detect ANY focus change?** | **NO** — `osascript ... to activate` and `open -a TextEdit` both fail to move `System Events` frontmost or `lsappinfo front` |

The last row is the one that matters. **The probe cannot report a focus change, so every
"no focus taken" reading above certifies nothing** — the `-newermt`/`/tmp`-symlink trap
(`PROTOCOL.md`, Non-signals) in a third costume. What *is* established is that the change does
not break rendering. Whether it fixes anything is open, and no Unity equivalent was added
because there is nothing here to test one against.

## Known contamination

- A **Godot process orphaned to launchd on 2026-08-11** (2d 21h, 29 CPU-minutes), rooted in
  `runs/_control/` where no reaper looked, ran through both the first matrix and the stopped audio
  run. Wall-clock comparisons spanning that window are unsafe; API cost is unaffected.
- **Session limits were labelled `api_error`** until 2026-08-15, merging two populations under one
  `terminal_reason`. It cost four trials in the first matrix, one calibration trial and the whole
  first arena attempt. Now split as `session_limit`, both branches exercised.
- **`wg-audio48`'s arena trials were built twice.** The first attempt died on a session limit
  ($11.76 across 8 records, all `api_error`); the retry overwrote those records. The four
  `api_error` rows still showing are the retry's own — they are the cells that had not yet been
  relaunched when this table was read.
- **`wg-audio48`'s arena wall-clock is not comparable to its pong and tetris wall-clock.** The
  retry ran four trials at once against a different background load; the original ran within a
  24-trial schedule.

## Offline re-grade, 2026-08-16 — tier 2 only, tier 1 untouched

`enemy.kinds` and `enemies.chase` were repaired (FINDINGS #46) and the eight `g3_arena`
play-bot tiers re-driven against the stored work trees. Tier 1 was not re-run, so the delta
measures the bot change and nothing else. `judge/regrade_wholegame.py` rebuilt `report.json`
from the stored tier files.

| cell | before | after |
|---|---|---|
| godot t0, t1 | 0.940 | **1.000** |
| unity t0, t1 | 0.940 | **1.000** |
| ts t0, t1 | 0.8957 | **0.9557** |
| rust t0, t1 | 0.000 | **0.000** — unchanged, and required |

No agent trial was re-run and no money was spent. `bot_mutants.py`: 36 criteria pinned in both
directions, 2 variants, 3 session-lock controls, 0 expectations unmet, exit 0.
`verify_blind.py` re-run unpiped after the fixture change: **BLIND**, exit 0, 74 ids, 8 trees.

## `wg-g4c-2026-08-21` — the platformer, COMPLETE. 8/8 `completed`, $421.00

The relaunch of `wg-g4b` after the quota reset. **Same regime as `wg-g4b`** (repaired starters,
`--max-turns 1000`, no budget cap, `--parallel 2`, work root `~/game-research-work`), so it is
comparable with `wg-g4b`'s intent but with `wg-g4` — see the seventh comparability break below.

| trial | $ | turns | wall | terminal |
|---|---|---|---|---|
| `rust__t0` | 77.60 | 370 | 86.3 min | `completed` |
| `rust__t1` | 36.16 | 205 | 58.7 min | `completed` |
| `godot__t0` | 42.92 | 258 | 55.7 min | `completed` |
| `godot__t1` | 66.16 | 312 | 80.4 min | `completed` |
| `ts__t0` | 40.88 | 215 | 60.5 min | `completed` |
| `ts__t1` | 55.05 | 291 | 64.3 min | `completed` |
| `unity__t0` | 54.00 | 263 | 82.7 min | `completed` |
| `unity__t1` | 48.23 | 258 | 69.5 min | `completed` |

**A single `terminal_reason`, so this field pools legally** — the first g4 field of which that
is true. Pre-launch gates all green and read unpiped: `verify_blind` BLIND exit 0 (74 ids, 9
trees, run against the work-root trial trees, not the in-repo starters), smoke 12/0, prompt
snapshot 16/16 matching at grade time via `prompt_guard --diff`, exit 0.

The cost analysis is the superseded-Aug-17 block below; the short form is **mean within-cell gap
$21.15 against a between-stack range of $8.91 — no separation on cost** (FINDINGS #63).

### Grading: the play-bot had a criterion that failed correct work

The first grading pass failed `platform.lands` on **5 of 6** submissions then graded, with
near-identical evidence — rule 9's signature. Adjudicated against source: the criterion walked
off the opening ledge and hoped a floor was underneath, which in a designed platformer it
usually is not. Repaired to construct the landing by jumping, re-pinned with both a mutant and a
new variant, and the field re-graded. **FINDINGS #65.**

A second defect found the same way is **not** fixed and caps this task: the bot reaches enemies
by walking right, so it cannot cross a gap. `ts__t0`, whose ground is four segments with pits at
x 520-600, 1080-1180 and 1700-1790, walked into the first pit at x=588.8 and failed six combat
criteria as a result — **the lowest score in the field, for building the most sophisticated
level.** `unity__t0` is the same mechanism (its `Level.cs` says "Six pits to clear"; the bot
reached x=367.5 against a 300-wide start pad). Any combat criterion on a gapped level is
currently unmeasurable.

Two further grader defects were adjudicated and repaired, and one template defect was not:

| finding | what it was | disposition |
|---|---|---|
| #65 | `platform.lands` walked off a ledge and hoped | repaired, re-pinned, field re-graded |
| #67 | `attack.faces` read an empty hitbox's centre `(0,0)` as a position | repaired, new variant, re-graded |
| #66 | `unity__t1` `verify.green`/`lint.clean` | **NOT a submission defect** — the template's own gate told the agent it passed |

### Final grades, after three grading passes

| trial | overall | prog | bot | remaining failures |
|---|---|---|---|---|
| `godot__t0` | **1.000** | 1.00 | 1.00 | — |
| `godot__t1` | 0.978 | 0.93 | 1.00 | `render.nonempty` (ink 0.881 vs window 0.001-0.85) |
| `rust__t0` | **1.000** | 1.00 | 1.00 | — |
| `rust__t1` | **1.000** | 1.00 | 1.00 | — |
| `ts__t0` | **1.000** | 1.00 | 1.00 | — |
| `ts__t1` | **1.000** | 1.00 | 1.00 | — |
| `unity__t0` | **1.000** | 1.00 | 1.00 | — |
| `unity__t1` | 0.956 | 0.86 | 1.00 | `verify.green`, `lint.clean` — a **genuine submission defect** since #66's repair |

**Six of eight at exactly 1.000 as of 2026-08-22**, after four play-bot repairs (#82) and the
`knockback.applied` repair (#89). **Tier 2 is now 1.00 in all eight cells.** The two cells below
1.000 fail only on tier 1: `godot__t1` on `render.nonempty`, and `unity__t1` on `verify`/`lint`,
which is the project's third genuine submission defect.

> Earlier versions of this table read 4 of 8 and then 5 of 8. **Both were correct when written**
> — the cells moved because the *instrument* was repaired, not because the grading was wrong.
> See the superseded-versus-withdrawn distinction in `README.md`. ⚠️ **`unity__t1` was reclassified on 2026-08-22**: fixing
Unity's lint recipe (task 07) turned its `verify.green`/`lint.clean` failure from a template
defect into a genuine submission defect — the project's third. See the regime note below.

`stage.completes` fails in 8 of 8 and is `diagnostic_only` — excluded from the denominator by
design, for the same reason it was demoted (RUBRIC.md). It is not a failure and must not be
reported as one.

### ⚠️ THE STORED CODE PACKS CARRY 23 STALE FILES. Do not read a code ordering from this field

**This field's judge packs on disk are not what their manifests say** (FINDINGS #95). It was
evaluated nine times, straddling the #69 cap removal and the #83 leak repair, and
`anonymise.build_pack` did not clear its destination until 2026-08-23, so each pass was written
on top of the last. Measured with `python3 judge/field.py packcheck --run runs/wg-g4c-2026-08-21`
on 2026-08-23, unpiped, exit 1:

```
g4_platformer: submissions=8 files_on_disk=222 stale=23 missing=0
               by_stack={'godot': 8, 'rust': 2, 'ts': 3, 'unity': 10} clean=False
```

| stack | stale files | submissions |
|---|---|---|
| unity | 10 | `t0` 6, `t1` 4 |
| godot | 8 | `t0` 4, `t1` 4 |
| ts | 3 | `t0` 1, `t1` 2 |
| rust | 2 | `t0` 1, `t1` 1 |

Twelve are byte-identical to a live file; eleven carry content no manifest lists, and seven of
the eight submissions still hold a `.codex` hooks config naming their own trial id — #83's answer
key, in the pack on disk. Blinding is not broken: `field.build_pack` neutralises both the trial
id and the work path as it copies, and a freshly built pack contains neither pattern. For
`architecture`, which is `blind_language` and rewrites every file to `.src`, 15 of them collide
with a live file and **7 collisions are won by the stale copy**, so live authored code is
replaced: the `architecture` pack holds 215 files where `idiomatic`'s holds 230, unity losing 8,
godot 6, ts 1, rust 0.

> **`idiomatic` and `architecture` orderings from this field are not readable.** How much of
> itself each submission was shown is unequal and stack-correlated — #62's shape through a third
> mechanism. `fun`, `fun_frames`, `ux` and `audio` read frames, telemetry and audio, never
> `judge_pack/code`, and are unaffected.
>
> **Reliability measurements ARE readable, including for the two code aspects.** The pack is a
> deterministic function of a static input, so every repeat of one round reads the identical
> field — verified by rebuilding each of the six aspects' packs twice and comparing every file
> (0 differing entries), and against the rounds actually stored, whose provenance gives one
> distinct input signature across all five repeats.

**The files are deliberately left in place** while the `wg-aspect-reliability` sweep (task 23) is
reading this run: re-packing mid-sweep would change the field underneath its own repeats, which
is the one thing that would invalidate the measurement it is making. Re-pack after the sweep, and
note that re-packing against today's starter reclassifies template code as authored work (#77) —
the exclusion set has to be computed, not guessed.

The **#62 character-budget** gate no longer fires here. The packs were rebuilt on 2026-08-22
after #69 removed the cap, and `pack_completeness` now reads `complete: True, any_dropped: 0 of
8`. The earlier reading in this file — `any_dropped: 8 of 8, max_dropped: 16, spread: 10` — was
correct when written and describes packs that no longer exist.

## `wg-g4b-2026-08-17` — A NULL. Killed by an external quota limit, 8/8 `api_error`

**No usable trials. $65.57. Nothing about the stacks can be read from it.**

| trial | $ | turns | wall | terminal |
|---|---|---|---|---|
| `rust__t0` | 31.90 | 185 | 52.9 min | `api_error` — working, killed mid-build |
| `rust__t1` | 33.68 | 221 | 52.8 min | `api_error` — working, killed mid-build |
| godot, ts, unity (6) | 0.00 | 1 | 0.0 min | `api_error` — never got a turn |

**The cause is external and has nothing to do with the regime, the starters or the task:** a
weekly account quota was exhausted, which terminated the supervising session and every trial
with it. The starters under test were the repaired ones, and they behaved correctly for the
53 minutes they ran.

> **Do not read two 53-minute rust trials as evidence about rust.** They are a truncated
> sample of a build that never finished, and the six zero-turn rows are not trials at all.

### It also produced a rule-4 instance INSIDE the partition the tool already makes

`runstat.py` printed `api_error n=8 total $65.57 mean $8.20`. That mean is over two
populations under one label — two trials that worked for nearly an hour and six that never
started — and **$8.20 describes no trial that has ever run**.

Partitioning by `terminal_reason` is necessary and not sufficient: a single reason can hold
both. `runstat.py` now checks the cheapest available homogeneity test — did the trial take
more than one turn — and **suppresses the mean when a group contains both**, reporting the two
sub-populations instead:

```
api_error  n=8  total $65.57  MEAN SUPPRESSED - 2 trial(s) ran, 6 never got a turn
           ran:   n=2 total $65.57  mean $32.79
           never: n=6 total $ 0.00
```

## THE STARTERS CHANGED ON 2026-08-17 — a SEVENTH comparability break

**`wg-g4` and `wg-g4b` are NOT comparable.** The four trials in `wg-g4` were built under
starters whose `just run` opened a foreground window with audio on the default device; the
eight in `wg-g4b` were built under starters that do not. A starter edit is a regime boundary
this file already names, and this is the largest one yet — it changes what an agent can do,
not just how it is graded.

What changed, and why it is not cosmetic:

| stack | before | after |
|---|---|---|
| unity | `open build/Starter.app` — foreground, audio on the default device | `open -g -j` + a runtime hook zeroing the AudioListener |
| godot | `godot --path .` | `--audio-driver Dummy` + an autoload setting `WINDOW_FLAG_NO_FOCUS` |
| rust | `cargo run -p game --release` | **`just run` REFUSED under the harness** — Bevy on macOS cannot be prevented from taking keyboard focus |
| ts | dev server | unchanged; it opens no window and no audio device |

**The rust row is a capability change, not a guard.** An agent in `wg-g4b` cannot run its game
at all and is told to use `just film` / `just probe` / `just test-render` instead. Whether that
costs turns or changes what it builds is unmeasured, and pooling the two runs would hide it.

`wg-g4`'s four trials are kept: they are a valid cost dataset **within their own regime**, and
the ts/rust cost decomposition below stands on them. They must not be averaged with `wg-g4b`.

## `wg-g4-2026-08-17` — the platformer, SUPERSEDED, 4 of 8 built (STOPPED)

> **PROVISIONAL. A row for a live run is a moving number** (this file's own rule). Every
> figure below is 4 of 8 trials and will change.

Regime: `--max-turns 1000`, **no budget cap**, `--parallel 2`, work root
`~/game-research-work`. Same regime as `wg-arena3d`, so the two are cost-comparable — and
unlike `wg-arena3d` this run has **not** straddled a machine repair: `syspolicyd` was measured
at 1.7% CPU-to-elapsed before launch and the exec-a-fresh-binary gate passed on both toolchains
that link new binaries.

| trial | $ | turns | wall | terminal | denials |
|---|---|---|---|---|---|
| `rust__t0` | 40.89 | 224 | 58.4 min | completed | 19 |
| `rust__t1` | 49.54 | 291 | 65.0 min | completed | 25 |
| `ts__t0` | 64.20 | 307 | 78.4 min | completed | 16 |
| `ts__t1` | 57.01 | 273 | 80.4 min | completed | 14 |
| **4 of 8** | **$211.64** | | | **4 completed, 0 other** | |

Partitioned by `terminal_reason` before any aggregate, per the rules below: **all four
`completed`**, one population.

**Revised projection: $375-$468 for all 8** (median-priced $425), against a pre-launch estimate
of $274-$583 built from the arena trials. It lands in the upper-middle of that range. Godot and
Unity are unmeasured on this task, so the remaining four are priced from the observed
min and max rather than from a point.

Denials 14-25 sit inside the arena's 9-31 under the identical allowlist — no g4-specific
permission problem.

### ⚠️ CONCLUSIVELY UNSUPPORTED — superseded by the full `wg-g4c` field, 2026-08-21

The observation below was reported to the operator, so it stays, marked. **It does not hold.**

All eight `wg-g4c` cells landed `completed`, $421.00, a single `terminal_reason`, so the field
pools legally. **Read the floor first, then the range:**

| stack | low | high | spread | gap | mean |
|---|---|---|---|---|---|
| unity | $48.23 | $54.00 | 1.12x | $5.76 | $51.12 |
| ts | $40.88 | $55.05 | 1.35x | $14.18 | $47.97 |
| godot | $42.92 | $66.16 | 1.54x | $23.24 | $54.54 |
| rust | $36.16 | $77.60 | 2.15x | $41.43 | $56.88 |
| **mean within-cell gap** | | | | **$21.15** | ← the floor |
| between-stack range | | | | **$8.91** | |

**The between-stack range is 42% of the floor. There is no separation on cost.**

Against this, the Aug-17 finding assumed a floor of **$7.92** — a factor of 2.7 too tight — and
its direction reversed: rust is now the more expensive of the two cells it compared, where
Aug-17 had ts ahead by 1.34x. Both halves of it fail.

**The general form of that error is the finding here, and it is now measured rather than
argued.** Cell spread itself ranges **1.12x to 2.15x** across the four stacks — $5.76 to $41.43
in gap terms, a factor of **7.2**. A noise floor estimated from one cell can therefore be wrong
by a factor of seven, in either direction, and nothing about a tight cell announces that it is
tight. Aug-17 drew its floor from the two cells that happened to be tightest; had it drawn from
rust it would have concluded the opposite with the same confidence. See FINDINGS #63.

A second, independent line points the same way: measured from the stored diffs, all four stacks
author a ~300-line WAV synthesiser (ts 320, rust 340, unity 305, godot 46 on an engine
built-in), so the audio-capability asymmetry cannot carry a cost difference either, and the
component most likely to differ by stack does not.

**The caveat stays attached to the widest cell.** Rust's `just run` is **gated** in this
regime, so whether 2.15x is a property of rust or of our gate is open (#17) and the number must
not be quoted without it. It is also still **n=2 per cell**: what is established is that the
floor is far wider than the Aug-17 estimate, not that the stacks are equal.

> ⚠️ **A number reported to the operator here was wrong and is corrected.** The rust agents were
> said to have "hit the refusal 5 and 3 times". They hit it **zero** times: `just run` was
> invoked 0 times in both rust trials, against 3/5/6 for ts/unity/godot. The count came from
> grepping transcripts for `STARTER_NO_RAISE`, which matched the agent **reading the justfile
> and `main.rs`** — both of which document the flag. Re-run against the refusal's actual stdout
> sentinel, and cross-checked against invocation counts, it is zero. *A matcher that counts
> mentions of a mechanism instead of firings of it will report the documentation as evidence*
> — #31's shape, in a measurement of a guard rather than in the guard.

**What #17 measures, corrected.** The gate cost rust no refusal turns at all: both agents read
the justfile at record 17 of 1124 and 640, saw `run` was gated, and never attempted it. What
separates rust is not refusals but **how little feedback tooling it ran**:

| `just` recipe | rust | ts | unity | godot |
|---|---|---|---|---|
| `run` | **0** (gated) | 3 | 5 | 6 |
| `film` | 8 | 6 | 6 | 11 |
| `probe` | **0** | 2 | 2 | 4 |
| `test-render` | **0** | 5 | 11 | 8 |
| `check` | **0** | 4 | 7 | 18 |
| `verify` | 14 | 16 | 11 | 17 |
| **total** | **48** | 86 | 101 | 140 |

All four starters define every recipe above, so the zeros are behaviour, not capability. This
does **not** show the gate made rust expensive — the opposite, if anything: rust's **cheapest**
trial (`t1`, $36.16, 8 `just` invocations total) also scored the field's only **1.000**, and its
dearest (`t0`, $77.60) ran 40. Whether removing interactive `run` pushed rust toward fewer,
longer iterations is untested; n=2, and it cannot be told apart from agent-to-agent variation.

**The mechanism behind the whole null, measured:** across all 8 trials **cost tracks turns at
r = 0.971** (cost~bash-commands r = 0.852). Cost is a proxy for how many turns an agent chose to
take, and turns vary from 205 to 370 *within* the same stack. That is why there is no ordering
to find: the quantity being compared is dominated by a per-agent choice, not a per-stack one.

**The honest statement: cost does not separate these stacks, and the Aug-17 reading should not
be cited.**

### A provisional cost observation that has NOT held before

Applying the same discrimination test used on the judges — is the between-stack range larger
than the spread a stack shows against itself?

| | |
|---|---|
| rust mean | $45.22 (within-cell spread 1.21x) |
| ts mean | $60.61 (within-cell spread 1.13x) |
| between-stack range | **$15.39** |
| mean within-stack gap | **$7.92** |
| ratio | **1.94x** |

For the first time in this project a cost difference exceeds its own noise floor. **Treat it as
provisional and probably wrong**: n=2 per cell, half the stacks unmeasured, and the arena run's
within-cell spread was 1.62x where this run's is 1.13-1.21x — so the noise floor here may
simply be unusually tight rather than the gap unusually wide. Cost has failed to separate these
stacks in every previous run, and a stack-correlated signal in this project is an instrument
property until a mechanism is named (six for six). **Do not report an ordering from this.**
Re-read it when all eight land.

### The decomposition, because a cost ratio with no mechanism is not a finding

The 1.34x cost ratio splits almost evenly, so neither half explains it alone:

| | ts / rust |
|---|---|
| turns | **1.126x** |
| cost per turn | **1.190x** |
| product (= the observed cost ratio) | **1.340x** |

And the cost-per-turn half has a measurable cause. Per trial, averaged:

| | rust | ts | ratio |
|---|---|---|---|
| `cache_read` tokens | 69,507,356 | **95,121,004** | 1.37x |
| output tokens | 251,417 | **323,217** | 1.29x |
| `files_changed` | 40, 40 | **52, 48** | ~1.25x |
| fresh input tokens | 7,050 | 3,261 | 0.46x |

**The TypeScript trials re-read a larger working context every turn and emit more code.** More
files changed, more output, a bigger cache read on each turn. That is a property of the work
produced, not of the meter: nothing here is a harness defect, unlike the six stack-correlated
signals that came before it.

That does **not** make it a quality difference. "Wrote more code for the same game" is
compatible with a template that needs more scaffolding, an agent that chose to write more, and
a task the two stacks read differently — and this run cannot separate those. It also says
nothing about whether the result is better: both cells scored identically on every
deterministic tier in every previous matrix.

What it does establish is that the number has a **mechanism** rather than being an unexplained
split, which is the bar this project sets before a stack-correlated reading may be discussed at
all. Godot and Unity will either fit the pattern or break it.

## Specialist-judge calls — a separate ledger, because they spend money too

This file's opening line claims every run, and judge calls were never in it. Read from the
stored result files on 2026-08-16.

| game | aspect | sees | pack | calls | $ | mean wall |
|---|---|---|---|---|---|---|
| `g1_pong` | architecture, idiomatic | code | 1.2 MB | 3 | $13.16 | 499 s |
| `g2_tetris3d` | architecture | code | 1.3 MB | 2 | $13.61 | 600 s |
| `g2_tetris3d` | idiomatic | code | 1.3 MB | 2 | $13.08 | 571 s |
| `g2_tetris3d` | fun | frames+telemetry | 3.3 MB | 2 | $3.01 | 373 s |
| `g2_tetris3d` | ux | frames | 3.3 MB | 2 | $2.73 | 246 s |
| `g2_tetris3d` | audio | audio | 10 KB | 2 | $1.20 | 286 s |
| **total, round 1** | | | | **13** | **$46.79** | |

**Round 2 — the repaired instrument, 2026-08-17.** Same five aspects, same game, both orders,
after the `fun` telemetry repair, `architecture`'s extension-blind packs and the adjudicator
fixes. **10 calls, $31.66.** Artifacts in `runs/wg-tetris-judge-2026-08-17/post/`;
round 1 preserved beside it in `pre/` because the two together are the only clean
reproducibility evidence this project has.

| | calls | $ |
|---|---|---|
| `pre/` (round 1, un-repaired evidence) | 10 | $33.63 |
| `post/` (round 2, repaired evidence) | 10 | $31.66 |
| **all judge spend** | **23** | **$78.45** |

> **Judge artifacts live in `runs/`, never in scratch.** Round 1 was written to a
> session-scoped directory under `/private/tmp` and moved out once it became the evidence for
> a finding. `field_sweep.assert_out_root_durable()` now refuses any ephemeral `--out`, pinned
> both directions — the trial-work-tree guard named a mechanism and did not cover the resource,
> which is any artifact a finding will cite (#45's shape, rule 6's form).

**Cost is per (game, aspect) and spans 13x** — $0.60 for an `audio` call, $8.08 for an
`architecture` call on the same game. It tracks pack size, not game difficulty, because what
the judge pays for is what it has to read. `build_pack` reports `evidence_counts` before any
money is spent; price from that.

Two projections made from the wrong basis, both recorded because both were acted on:

- three `g1_pong` calls (mean $4.39) priced a five-aspect `--max-runs 6` sweep at ~$131; the
  first `g2_tetris3d` call measured **$8.08** and repriced it at **~$256**, over its ceiling;
- the same per-game mean averages a $0.60 aspect with an $8 one.

`--per-call-budget` was held at $12 throughout even though measured cost never approached it:
it reaches the judge as `--max-budget-usd`, which is **visible to the callee and instructs it**
(FINDINGS #33), so changing it mid-sweep would make the rounds non-comparable.

## THE UNITY LINT RECIPE CHANGED ON 2026-08-22 — an EIGHTH comparability break

**No Unity `lint.clean` or `verify.green` score from before this date is comparable with one
after it.** `starters/unity/tools/unity-compile.sh` compiled against a copy that inherited
`Library/`, so Unity re-used cached analyser results and a violation still present in the file
was never re-reported. The recipe now deletes `Library/` from that copy when `STRICT=warnings`.

Measured on `g4_platformer__unity__t1` (`wg-g4c-2026-08-21`), five real CA1861 violations:

| `Library/` state | `just lint` | wall |
|---|---|---|
| warm — every Unity trial to date | **exit 0**, "all assemblies compile clean" | 8.9s |
| `ScriptAssemblies` deleted only | **exit 0** — still wrong | 4.9s |
| whole `Library/` deleted — **now** | **exit 1**, all five reported | 10.9s |

Scoped to `STRICT=warnings`, so `just check` — the fast inner loop — keeps its warm cache at
~4.9s. The cold path costs about **two seconds**.

### What it invalidates, and what it does not

- **Invalidated:** every Unity `lint.clean` and `verify.green` PASS in `wg-matrix`, `wg-audio`,
  `wg-audio48`, `wg-arena3d`, `wg-g4` and `wg-g4c`. Those gates were reporting the build cache.
  A Unity pass on those runs means "no violation the cache chose to re-report", not "clean".
- **Not invalidated:** every other stack (the recipe is Unity-only), every Unity FAILURE (a
  failure was always real), and every tier-2 and tier-3 score (they never consulted `lint`).

### One score changes as a result

`g4_platformer__unity__t1` moves from a template defect to a **genuine submission defect**, the
project's third. **The code did not change; the gate stopped lying about it.** #66 remains
correct about what the agent was told at the time, which is why it was not a submission defect
*then* — the agent ran the command it was instructed to run and was told it passed.

Gates re-run after the change, both exit 0: `judge/verify_blind.py` (BLIND, 74 ids, 9 trees) and
`judge/starter_parity.py` ("No drift detected on any measured axis"). Pinned three ways: a warm
tree with violations flips exit 0 → exit 1 with all five; the clean starter stays exit 0 and does
**not** become a false failure; `just check` stays warm and green.

## THE GODOT CHECK RECIPE CHANGED ON 2026-08-23 — a NINTH comparability break

**No Godot `build.compiles` or `verify.green` score from before this date is comparable with one
after it.** `starters/godot/tools/check.gd` called `script.reload()` on every scanned `.gd` file;
`tools/no_raise.gd` is an `[autoload]` and therefore already instantiated, Godot refuses to
reload a script with a live instance, and the loop counted that refusal as a compile failure. The
pristine template's own gate exited 1. The call is now `script.reload(true)` (`keep_state`).

Measured on a fresh copy of the starter, harness uninvolved, before and after:

| tree | `just check` | `just verify` |
|---|---|---|
| pristine, before — every Godot trial since 2026-08-17 | **exit 1**, `CHECK scripts=18 failures=1` | **exit 1** |
| pristine, after | exit 0, `CHECK scripts=18 failures=0` | exit 0, 6/6 render tests pass |

### What it invalidates, and what it does not

- **Not invalidated: any stored score.** The autoload arrived with the seventh comparability
  break above (2026-08-17), so only 4 of the 20 stored Godot submissions carry the defect at all.
  `wg-g4b`'s two were never graded — that run holds zero `report.json` and both trials ended
  `api_error`. `wg-g4c`'s two **repaired the template themselves**, by two different mechanisms,
  and both scored `build.compiles` and `verify.green` True. `wg-g4c-capgate` re-grades those same
  work trees. **No published tier-1 Godot figure needs marking** (FINDINGS #98).
- **Invalidated going forward:** a Godot trial after this date starts from a green gate and no
  longer spends turns repairing its own harness, so its turn count and cost are not comparable
  with `wg-g4b`'s or `wg-g4c`'s. That cost is unmeasured — nothing counts a turn spent on the
  template.
- **Not affected:** the other three stacks. Measured the same day from pristine copies: rust, ts
  and unity are all exit 0 on both recipes, so the red baseline was one-arm.

Gates re-run after the change, both exit 0: `judge/verify_blind.py` (BLIND, 81 ids, 5 trees) and
`judge/starter_parity.py` ("No drift detected on any measured axis"). Pinned three ways by
`tools/starter_gate_control.py`, now part of `tools/precampaign_smoke.py`: the repaired starter is
green and still goes red on a parse error planted **in the autoloaded script**; restoring the
original defect makes the tool report FAILED; and the skip-list repair one `wg-g4c` agent actually
shipped passes the green direction while **failing the red one — `just check` exits 0 over an
unparseable autoload.**


## Rules

- **Never pool across a regime boundary.** Report per regime, with `n` per group.
- **Never pool tier-2 scores across GAMES, for a reason independent of the regime rule.** The
  play-bot has a different number of scored criteria per game — **pong 13, tetris 15, platformer
  20, arena 22** — and only `determinism`, `score` and `state` are shared by all four. A 1.000 on
  pong cleared 13 hurdles; a 1.000 on arena cleared 22. **They are not the same achievement**, so
  any average across games silently weights the easiest game equally with the hardest.

  This is stated separately *on purpose*. The regime rule above forbids the same pooling for a
  different reason — task, cap and starter changes — and **if the regime problem were ever fixed,
  this ban would look obsolete and it would not be.** Two independent reasons need two entries, or
  deleting one takes the other with it. See FINDINGS #72.

  Tier 1 is the exception and was checked: all 14 programmatic criteria apply to all four games,
  so its denominator really is constant across the suite.
- **Partition by `terminal_reason` before computing anything.** `completed`, `max_turns`,
  `budget_exhausted`, `session_limit` and `api_error` are different populations.
- A run's spend is the sum of `agent.cost_usd`. The key is `cost_usd`, **not** `total_cost_usd` —
  the latter is absent and reads as zero, which silently produces a $0.00 total.
- **Cross-check the record sum against the build logs.** If the log has more `[built]` lines than
  there are records, the difference is retried cells whose first attempt was overwritten, and the
  record sum understates what the run cost.
- **Scope every retry to the failed cells.** `cmd_build` never consults existing records and
  `prepare()` begins with `rmtree`, so re-running a selection that includes completed trials
  destroys them.
- **Record what changed about the MACHINE during a run, not only about the configuration.**
  `wg-arena3d` spans a system-daemon repair and nothing in the record says so; the split is
  invisible to every aggregate the harness computes (FINDINGS #49).
- **Read `agent.final_text` before grading.** Four agents wrote a paragraph headed *"What I
  could not verify — and why"* naming the exact mechanism that produced this run's entire
  spread, and it sat unread for a day. No gate looks at that field.
