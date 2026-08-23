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

**Cumulative, re-read from disk on 2026-08-23. Two figures, because they count two things.**

| | | source |
|---|---|---|
| agent trials, **surviving records** | **$2,466.31** over 161 trials in 23 run directories | `python3 eval/tools/census.py` — `agent.cost_usd` in every `runs/**/trials/*.json`, at any depth |
| specialist-judge rounds | **$306.73** over 93 rounds in 11 sweep directories | `judge/judge_ledger.py --tree runs/` |

**Records, not spend, and the gap is real but not totalled here.** A retry overwrites the record
of the attempt it replaces (#36), so true spend is **at least** $2,466.31. It was measured once,
for the runs existing on 2026-08-15, at ~$21.61 of overwritten attempts. It is **not re-derived
above and must not be inferred from the `[built]` lines**: those sum to $2,262.17, *less* than the
records, because `wg-arena3d`'s retries ran under a second log this ledger already marks
`+ retries` and `wg-audio48`'s log carries `archive-arena2d`'s trials too. A number that is
smaller than its own lower bound is a reading of the wrong artifact, not a correction.

> ⚠️ **This line read "~$1,547" until 2026-08-23 and had done since 2026-08-15**, and it went
> stale **twice over, in two different ways**:
>
> | | |
> |---|---|
> | three runs that did not yet exist | `wg-g4`, `wg-g4b`, `wg-g4c` — **$698.21**, 29% of the project's agent spend |
> | one run that was still building | the `wg-*` rows summed to $1,433.84 that day and sum to **$1,614.27** now. `wg-audio48` was in flight and `archive-arena2d` was later split out of it — the moving-row hazard this file warns about a few paragraphs below, realised in this file's own headline |
>
> `README.md`'s "~$1,794" is the same figure at a later moment and is corrected there too. The
> judge half of the line said **$46.79**, which is one day's calls quoted as all of them and is
> separately wrong about *which* calls (FINDINGS #121). **A cumulative total is the one number in
> a ledger guaranteed to go stale**, and nothing re-derived either of these; `judge_ledger.py` is
> now the producer for the second row, and the first is one `agent.cost_usd` sweep away.

**The table below lists only the `wg-*` whole-game runs.** The remaining **$153.82 over 71
trials in 12 run directories** is the spec-change bake-off and core suites, which have never
been in this ledger despite its opening line claiming every run. Recorded rather than silently
corrected. It splits **$91.72 over 47 trials** in the eight top-level `bakeoff-*` / `core-*`
directories and **$62.09 over 24 trials** in the four nested inside
`archive-run1-byte-identical-prompts/`; this paragraph stated only the first figure, as though
it were the whole remainder, until 2026-08-23 (`WR-tree-census-one-level`, #127).
The `wg-audio48` and `archive-arena2d` rows together account for the $616.66 that run cost.

> **The two columns are read from different sources and will differ by pennies.** The archive
> row's records sum to $118.62 while its build log's `[built]` lines sum to $118.63: the log
> prints each trial rounded to the cent and the records carry full precision. Stated rather than
> reconciled — a figure quietly adjusted to match another figure is no longer a reading.

> **A row for a live run is a moving number.** `wg-audio48` was still building its last four arena
> trials when this warning was written. An earlier version of this file recorded *$571.15, 19
> completed, 5 api_error* — read from disk correctly, describing a state that lasted minutes. Mark
> in-flight rows provisional; a run's spend is final only when its terminal reasons are.
>
> **It then happened to the headline, twice, and the second time nobody noticed for eight days.**
> The row settled; the total above it did not, because the total had no producer and no read date.
> Both now have one.

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

**Those two runs are also barred from code-aspect judging**, which is a separate axis from the
regime boundaries above and applies within each of them: their packs cannot be re-packed and the
builder already refuses them. See the section on their stored packs, below.

## THE FRAMES CHANNEL IS NOT EQUIVALENT ACROSS ARMS, and it never has been — measured 2026-08-23

**This is not a boundary in time.** Nothing changed on this date; the asymmetry has been present
in every run this project has filmed, and it is recorded here because no document said so. It
constrains what a *cross-arm* comparison of frames evidence can mean, in every regime above and
below.

`just film` produces the 12 PNGs that `ux`, `fun` and `fun_frames` judge, and each arm implements
it in its own harness. **The four harnesses differ in what a filmed frame is able to contain.**

A probe was added to each arm's own view — one 8×8 cell painted per simulation tick the *renderer*
was actually shown — and each arm's own capture path was then run at five tick counts (task 68;
scratch trees, not the starters). `observed_run` is the count of consecutive ticks ending at the
captured tick that the renderer saw, capped at 32:

| capture at tick | godot | rust | ts | unity |
|---|---|---|---|---|
| 0 | 1 | 1 | 1 | 1 |
| 1 | 2 † | 2 | 1 | 1 |
| 8 | 1 | **9** | 1 | 1 |
| 60 | 1 | **32** (cap) | 1 | 1 |
| 240 | 1 | **32** (cap) | 1 | 1 |
| **positive control** — view handed ticks 0..60 by hand | **32** | n/a ‡ | **32** | **32** |

† Cross-capture leakage inside one process, not the capture path observing an intermediate tick: an
earlier capture in the same run had shown the view tick 0, and the consecutive-tick window happened
to reach back to it. It does not occur at any larger tick count.
‡ Uninformative **by construction**, and reported rather than omitted. Rust already observes every
tick, so pre-seeding its history changes nothing — the control cannot distinguish a working probe
from a broken one *in that arm*. The three arms where it can, it does.

**So the partition is 1 versus 3, not godot versus rust.** Rust/Bevy runs the whole `App` once per
tick with the view systems attached. Godot, TypeScript and Unity each advance the simulation to the
sampled tick with **no view attached** and draw once. Presentation state that accumulates over the
ticks in between — a trail, a particle burst, a shake, a decay, a tween — is structurally absent
from every filmed frame in three arms and present in the fourth.

The positive control is what makes the three 1s a measurement rather than a broken probe: the same
instrument, in the same arm, reaches 32 the moment the view is handed the history the capture path
withheld.

### A second axis: render frames, which partitions differently again

How many times the view gets to draw after the last state sync, and what clock those frames carry:

| arm | render frames per capture | the clock they carry | how established |
|---|---|---|---|
| **godot** | **3** | **24.7 / 27.7 / 28.5 ms of WALL CLOCK across three identical captures** — it varies run to run | measured |
| **rust** | ~9 normally; **238–239 when a frame-accumulating effect is present** | virtual: `TimeUpdateStrategy::FixedTimesteps(0)` during settle, so time does not advance | measured |
| **ts** | 1 — `capture()` steps, renders and reads back in one synchronous call | virtual: `__nowMs` set to `(ticks/TICK_HZ)*1000`, deterministic and advancing per filmed frame | read from `eval/starters/ts/src/view/capture.ts` and `harness.ts` |
| **unity** | 1 — one `camera.Render()`, no player loop | none: `Time` does not advance | read from `eval/starters/unity/Assets/View/RenderHarness.cs` |

Two consequences that are not obvious from the tick table:

- **Godot's three render frames carry real wall-clock time.** A `_process(delta)` tween there is
  *partly* visible — about 25–29 ms of it — and **non-reproducible**, because the delta is whatever
  the machine gave it. The starter's own `rendering is reproducible across runs` test would only
  catch that if the effect moved enough pixels in ~4 ms.
- **Rust's advantage costs it the settle criterion.** `capture_frame` settles on "two consecutive
  readbacks are byte-identical", which an effect that is still changing can never satisfy. With one
  present, the loop ran its full `MAX_SETTLE_FRAMES` budget (238–239 frames observed) and returned
  the `previous`-frame fallback — a deliberately *unsettled* frame. Bevy can show accumulating
  state; it cannot show it and settle at the same time.

### What was decided, and what was not

**Recorded, not equalised.** Changing any capture path is a regime boundary that invalidates frame
comparisons across it, and this project has eight stored runs of frames. Equalising downward would
also delete a real capability from one arm and interact with the settle criterion above. The
asymmetry is therefore documented and the graders are told about it:

- `eval/judge/aspects.py` defines `FRAMES_BLIND_SPOT`, carried by **all three** frames-reading
  aspects (`ux`, `fun`, `fun_frames`). It states the blind spot **without naming or counting the
  arms** — the judge is blinded to which submission is which (#32), and "three of the four" leaks
  the partition as surely as "Bevy" does.
- `eval/judge/aspects_selftest.py` pins that in both directions, including a **variant** that
  counts the arms without naming one.

**This changes the judge's prompt.** Every stored `ux`, `fun` and `fun_frames` round was produced
under a brief that did not carry the paragraph, so those rounds and any future ones are not
strictly comparable. The judge tier weighs **0.00**, so no `overall` moves and nothing was
re-scored.

**What this does NOT say:** that any arm's frames are worse. All four are internally valid, and
three are *more* deterministic for it — that determinism is exactly why they sync once. The defect
was that two arms differ in what a frame can contain and no document said so.

**Standing constraint:** do not read a cross-arm difference in `ux`, `fun` or `fun_frames` as a
statement about the submissions until you have asked whether it could be this. It sits alongside
#59 — palette depth, a 60× split by renderer — as the second measured way the frames channel
reports the arm rather than the work.

## A fifth boundary, and this one is in the GRADER, not the run

**On 2026-08-23 tier 1 stopped being 0.31 of `overall` and became a pass/fail gate** (task 29,
`eval/judge/RUBRIC.md`, FINDINGS #92 and #123). `overall` is now the play-bot tier alone.

Unlike the four above, this boundary does not run through the builds — the submissions and every
stored tier score are untouched. It runs through the **arithmetic that turns them into a number**,
which makes it easier to miss and no less disqualifying:

- **Every `report.json` written before that date holds `overall = 0.31*tier1 + 0.69*tier2`** and
  has no `gate` and no `scoring_regime` field. Records written after carry both, and their
  `overall` is `tier2`.
- **14 of the 68 stored trials would move** if re-scored — 5 upward by 0.0221-0.0443, 9 downward
  by up to **0.2273** (`wg-matrix-2026-08-13`'s `g3_arena__unity__t0` and `g3_arena__unity__t1`,
  which the constant 0.31 was cushioning).
  **They were not re-scored.** Nothing in `eval/runs/**` was rewritten for this change.
- **Never average a stored `overall` with a new one.** `wholegame.py report` marks pre-gate rows
  `w` in a `regime` column and refuses to pass over a mixed run silently;
  `judge/regrade_wholegame.py` will not rewrite a pre-gate record without
  `--accept-regime-change`, because converting part of a run leaves a directory half in each
  regime with nothing on disk saying which trial is which.

**Re-scoring a stored run into the gate regime is allowed, and it must be recorded here** — the
run row gains the date and the flag, because after it the run's numbers no longer match anything
published about it before. Nothing has been re-scored so far.

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
reading the agents' own closing messages, by hand, a day late. Since 2026-08-23 the harness
reads them: `wholegame.py report` on this run prints *"`just verify` has never run"* and
*"it was already broken before I made any changes"* beside the six trials that said so
(`eval/tools/disclosure.py`).

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

**Its `suite.json` records only the second wave.** `started_at` is `2026-08-16T13:47:06.522`,
which is `g3_arena__unity__t0`'s start to 2 ms and 22 hours after the directory name — the
16-August re-launch overwrote the manifest, so the directory's own record of what it was
configured to be omits the four trials the warning above is about. The trial count matches, so
nothing but that timestamp says so. `python3 tools/manifest.py audit` reports it; the directory
carries a `MANIFEST-DEFECT.json` and the manifest itself was left as found (#120).

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

## DECLINED: requiring a finish-report section in the starters (`tasks/46`)

The proposal was to make every starter demand a closing section — behaviour delivered, design
choices, exact commands and results, artefact paths personally inspected, remaining risks — the
way `game-research-gpt`'s template does, instead of hoping the agent volunteers one. The ticket
pre-registered three outcomes and required the **baseline to be measured offline first**. It was,
on 2026-08-23, and it decides the question without a matrix.

**The census.** All 90 stored `agent_result.json` under `runs/**`, reading `.result` (the whole
message) rather than `trials/*.json`'s tail-truncated `agent.final_text`. **15 store no message
the agent wrote** — 6 `null`, 9 holding the API's own quota-limit string — and the remaining
**75 are all `terminal_reason: completed`**. Each was read and hand-classified as disclosing, or
not, *something the agent could not verify or a residual risk it was leaving behind*. The
extraction was pinned first on rows whose answer the documents already state: the two `wg-g4c`
Godot trials of #98, and the four `wg-arena3d` trials of rule 11. All six came back as predicted.

| stack | n | disclosed | rate | in a headed section |
|---|---|---|---|---|
| godot | 15 | 3 | **20.0%** | 2 |
| rust | 21 | 13 | **61.9%** | 3 |
| ts | 23 | 4 | **17.4%** | 2 |
| unity | 16 | 11 | **68.8%** | 3 |
| **all** | **75** | **31** | **41.3%** | **10** |

Four rows are arguable either way; classifying all four as disclosures gives 35/75 = 46.7%. The
per-run spread is 0% (`archive-arena2d`, n=3) to 75% (`wg-arena3d` and `wg-g4c`, n=8 each).

**That is the pre-registered "low and stack-correlated" outcome, whose instruction was to
investigate the correlation before touching a starter. The investigation dissolves it.** Sorting
the 31 disclosures by what they are *about*:

| what could not be verified | godot | rust | ts | unity |
|---|---|---|---|---|
| the live path — window, keyboard, screenshot | 1 | 7 | 0 | **11** |
| the audio, by ear | 2 | 2 | 0 | 0 |
| the toolchain, which never ran (`wg-arena3d`, #49) | 0 | 2 | 2 | 0 |
| a test-coverage gap | 0 | 1 | 2 | 0 |

19 of 31 are the live path, and they are almost entirely Unity and Rust. The counter-check is
mechanical and unambiguous: messages claiming the agent **drove the running application** — a
real browser, a real keyboard, `just smoke` — number **15 of 23 for TypeScript and 0 of 52 across
the other three stacks.** TypeScript ships to a browser an agent can automate; Rust and Unity
ship a native window it cannot screenshot or type into. Godot sits between — its launch recipe
already returns on its own and opens no audio device — which is why its two disclosures are
about audio nobody could hear rather than a window nobody could see.

> **The arms do not differ in how much they disclose. They differ in how much is left for them to
> disclose.** Dropping `wg-arena3d` entirely, to control for the #49 machine defect, barely moves
> it — godot 23.1%, rust 57.9%, ts 9.5%, unity 64.3%.

**Why it is declined, in cost.** A starter edit is a regime boundary; this would be the
**fifteenth**, and it must land in all four arms in the same words with `starter_parity.py` and
`verify_blind.py` re-run. Because it breaks comparability, the before-side cannot be an existing
run: the most recent clean 8-cell field, `wg-g4c-2026-08-21`, is **$421.00** of agent trials and
sits behind four subsequent starter boundaries. So the experiment is **two fresh matrices, ≥$842
of agent spend** plus judge sweeps, to move a number that `tasks/46` itself forbids reporting
beside any tier-1 or tier-2 figure — because a higher disclosure rate is evidence the reporting
changed, not that the work did.

**What was done instead, and it was free.** The disclosures already exist in 31 of 75 completed
trials, 10 of them under a dedicated heading, and nothing in the grading pipeline read them —
four documents said to read the field and no code did. `tasks/71` built the reader:
`eval/tools/disclosure.py`, printed by `wholegame.py report` beside every score. It is a
**locator, not a classifier**, and its count is not this table's rate: over the same 75
messages it fires on **26** — godot 3/15, rust 12/21, ts 3/23, unity 8/16, against the hand
figures above. It under-reports in every arm and reproduces the same shape. Quote the hand
figure for a rate; quote the locator only as "trials with at least one located passage".

Its first pass found something this hand pass had not: **four Rust agents, in three different
runs, reporting the same broken starter recipe** (`tasks/81`). That is the class #98 belongs
to — a starter red on a pristine tree costs one arm and no other — and it is why the tool
locates *"the starter was already broken"* as a family of its own, which the disclosure
classification above does not count at all.

**Re-open it if** the harness gains a way for Rust and Unity agents to exercise their own live
path. That change would remove the mechanism behind the entire spread above, and only then does
a residual gap measure disclosure rather than verifiability.

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
- **Neither `wg-matrix` nor `wg-audio48` may have a code-aspect field built from it**, and neither
  can be re-packed — their stored packs carry #83's answer key and the `starter baseline` commits
  that would corroborate an exclusion set are destroyed. Next section.

## `wg-matrix` AND `wg-audio48` CARRY #83's ANSWER KEY IN THEIR STORED PACKS, CANNOT BE RE-PACKED, AND ARE BARRED FROM CODE RE-GRADING — 2026-08-23

`wg-g4c` was re-packed and verified clean (below). **Those two runs were not**, and they cannot
be: the evidence a computed exclusion set is checked against no longer exists on this machine.

### The radius, measured file by file

Every stored `judge_pack/code` in both runs, grepped for the trial id, `.codex` and the work
path. Where it is present it is always **exactly one file**, always `code/other/NN.json`, and it
is the `.codex` hooks configuration verbatim — for `wg-matrix`'s `g1_pong__godot__t0`:

```json
{"hooks": {"Stop": [{"hooks": [{"type": "command", "command":
  "'/private/var/folders/.../T/wholegame-work/g1_pong__godot__t0/.codex/hooks/verify-gate.sh'"}]}]}}
```

| run | packs carrying the key, per stack | total |
|---|---|---|
| `wg-matrix-2026-08-13T14-02-50` | godot 4/6, rust 5/6, **ts 6/6**, unity 2/6 | **18 of 24** |
| `wg-audio48-2026-08-14T19-55-47` | godot 3/4, ts 3/4, rust 0/4, unity 0/4 | **6 of 16** |

### They cannot be re-packed, and the reason is that the corroboration is destroyed

`python3 judge/repack.py runs/<run>` (dry run, unpiped) **refuses 24 of 24 and 16 of 16**:

| run | submissions | refusal |
|---|---|---|
| `wg-matrix` | 24 | no `pack.manifest` in `eval/report.json` — there is no stored set to subtract from, so the exclusion set is *unrecoverable*, not empty |
| `wg-audio48` | 12 | `files_dropped_for_length` is 1–11, not 0: those packs were built under the pre-#69 character cap and files are legitimately returning |
| `wg-audio48` | 4 (`g1_pong` godot t0/t1, ts t0/t1) | the work tree has no `starter baseline` root commit |

The last row is the one that closes the question, and it is not a tool artefact. The work trees
are still on disk under `$TMPDIR/wholegame-work/`, but `$TMPDIR`'s reaper has gutted them — the
same mechanism as #45, the outcome #104 predicted:

| | trials | work tree present | `.git` present | `.git/HEAD` present | loose objects |
|---|---|---|---|---|---|
| `wg-matrix` | 24 | 24 | 24 | **0** | **0** |
| `wg-audio48` | 16 | 16 | 16 | **0** | **0** |
| `wg-g4c` *(control)* | 8 | 8 | 8 | 8 | 87–211 |

`hooks/ info/ logs/ objects/ refs/` survive as empty directory skeletons; `HEAD`, `config`,
`index` and every object are gone. **The starter as the agent received it is unrecoverable for
all 40 submissions**, so a rebuilt pack would reclassify template code as authored work (#77) with
nothing able to say by how much. Re-packing them is therefore the wrong repair, not a deferred one.

### What is barred, and what already bars it

**No code-aspect field may be built from either run.** That is not only a rule here — it is
already enforced, and it was verified by calling the builder rather than by reading it.
`field.build_pack(..., sees="code")` on every game in both runs:

| field | result |
|---|---|
| `wg-matrix` / `g1_pong`, `g3_arena` | refused — pack/manifest parity UNMEASURABLE for 8 submissions each |
| `wg-matrix` / `g2_tetris3d` | refused — TRUNCATION HAS RETURNED, 5 of 8 dropped, max 3 |
| `wg-audio48` / `g1_pong` | refused — 4 of 8 dropped, max 7 |
| `wg-audio48` / `g2_tetris3d` | refused — 8 of 8 dropped, max 11 |
| `wg-g4c` / `g4_platformer` *(control)* | **built**, 199 files |

The control matters: the five refusals are properties of these two runs, not a builder that
refuses everything. `fun`, `fun_frames`, `ux` and `audio` never read `judge_pack/code` and are
unaffected; a *frames* or *telemetry* re-grade of either run remains available.

### What is NOT true, and the ticket said it was

The live exposure was described as armed — that an offline re-grade would hand a judge the key
again. **It would not.** `field.build_pack` writes `anonymise.neutralise(text)` rather than
copying, and `neutralise` rewrites any `g<n>_<game>__<stack>__t<n>` token to `SUBMISSION`.
Applying it to all 40 packs' code leaves **0 files in which the trial id survives**, and the
32 `telemetry.json`/`audio.json` evidence blobs those runs would produce carry no trial id, work
path or `.codex` string either.

So the two exposures separate cleanly: the **stored** packs carry the key and always will; **what
a judge would be handed does not.** The bar above rests on the destroyed baseline and the #62
truncation, which are independent of #83 and would bar these fields even if the key had never
existed.

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

A second defect found the same way capped this task's grades: the bot reached enemies by walking
right, so it could not cross a gap. `ts__t0`, whose ground is four segments with pits at
x 520-600, 1080-1180 and 1700-1790, walked into the first pit at x=588.8 and failed six combat
criteria as a result — **the lowest score in the field, for building the most sophisticated
level.** `unity__t0` is the same mechanism (its `Level.cs` says "Six pits to clear"; the bot
reached x=367.5 against a 300-wide start pad). **Repaired 2026-08-23 (task 76)**: `_hurt` was
the last of three inline movement loops with no edge jump, and the variant that declared the
ceiling had put the far side 680 units away — past any jump — so the tolerance was partly a
defect in the check. The four contact criteria are now measured on a pit level and the variant
tolerates nothing (`judge/RUBRIC.md`, g4 section). **The grades below are not affected and were
not re-run**: reading the eight stored `playbot.json` files, all six combat criteria already
pass on all eight submissions after the earlier repairs, the one exception being
`unity__t0`'s `knockback.applied`, which is *unscored* for the separate reason in #89. The
repair matters for the next gapped submission, not for this run.

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

### Four of its eight stored diffs credit the author with a hunk the template's own gate wrote

Measured 2026-08-23 under task 51, over all 90 stored `diff.patch` files in `runs/`. The
starters this run was built from were not format-clean, and `fmt` is the first dependency of
`just verify` in every stack, so the agent's first `verify` rewrote a file it had never opened
(#106). In `wg-g4c` that lands in `rust__t0`, `rust__t1`, `godot__t0` and `godot__t1` — and in
`wg-g4b`'s two rust trials, the only other run affected. It is visible in the judge packs as
`tools/no_raise.gd | 1 +` under *"Files this submission's author changed"*
(`runs/wg-aspect-reliability/packcheck/idiomatic/{B,E}/CHANGED.txt`).

**Nothing here is retracted and no re-grade is warranted.** The rust hunk is ~5 lines inside a
file whose authored change is 87 and 143 lines, adding no row; the godot hunk is one row of
`1 +` among 51-57 rows and ~4,500 insertions. #106 carries the full census and the reasoning.
Recorded here because it is a property of *these two runs' evidence*, and the stored per-trial
starter baselines date it precisely: `wg-g4` was format-clean and everything from `wg-g4b`
onward was not, which is the same starter edit as the seventh comparability break.

### THE CODE PACKS WERE RE-PACKED ON 2026-08-23. Every judge round stored before then read a field that no longer exists

**The packs are clean now.** `python3 judge/field.py packcheck --run runs/wg-g4c-2026-08-21T02-26-46`,
run unpiped after the re-pack, exit 0 — note the argument is the full directory name, and a
truncated one exits 2 rather than certifying anything (#96):

```
g4_platformer: submissions=8 files_on_disk=199 stale=0 missing=0
               by_stack={} unmeasurable=0 clean=True
```

They were not clean before. The run was evaluated nine times, straddling the #69 cap removal and
the #83 leak repair, and `anonymise.build_pack` did not clear its destination until 2026-08-23,
so each pass was written on top of the last: **222 files on disk, 23 of them under labels no
manifest listed** — unity 10, godot 8, ts 3, rust 2, uneven within a stack as well as across it
(#95). Seven of eight submissions held a `.codex` hooks config naming their own trial id, #83's
answer key, and the 23 files are kept verbatim under
`repack-2026-08-23-stale-files-removed/` so the removal is auditable rather than merely asserted.
A fresh grep of the re-packed code for the trial-id and `game-research-work` patterns returns 0
hits in all eight submissions.

> **"Clean" there means TRIAL-ID clean, and it is not the same as language-blind (#130).** The
> re-packed `wg-g4c` code still carried its stacks' toolchain names — `CARGO_MANIFEST_DIR`,
> `crates/sim`, `clippy.toml`, `WinitPlugin` — because `neutralise` matched a list of spellings
> and none of those spellings were on it. **All 8 of this field's packs carried at least one, and
> the two Rust submissions carried 13 and 10 leaking files against 2-3 for the other six.** That
> is the one field `architecture` is judged on with `blind_language=True`, so it bears directly
> on the ordering below. `neutralise` was repaired on 2026-08-23 and a re-sweep of all 84 stored
> packs now reports 0; **the stored packs are NOT repaired**, and every `architecture` round
> already run therefore read a language-identifiable field.

**The exclusion set was computed, not guessed, and it was not empty.** Re-packing an old run
against today's starter reclassifies template code as authored work (#77), so the drift was
recovered as *(origins in a pack rebuilt against the recorded starter) minus (origins in the
stored manifest) minus (files dropped for length, asserted 0 since #69)*, then checked file by
file against the `starter baseline` commit in each work tree — the starter as the agent actually
received it. Both methods returned the same three files:

| submission | excluded as starter drift |
|---|---|
| `ts__t0` | `src/view/capture.ts`, `src/view/harness.ts` |
| `ts__t1` | `src/view/harness.ts` |
| the other six | none |

All three come from the TS capture-page repair (task 31), landed **3.5 hours before the re-pack
and after the last pack was written**. The Godot starter also moved that morning, and correctly
produced no exclusion: both Godot agents had edited `tools/check.gd` themselves, so it was already
authored work in the stored manifest. Rebuilding with the three exclusions reproduces the stored
label → origin mapping exactly for all eight submissions, which is the check that the re-pack
removed the orphans and changed nothing the judge was shown. `judge/repack.py` does all of this
and refuses rather than guessing when the corroboration is unavailable.

> **The 30 stored `wg-aspect-reliability` rounds read the 222-file field, not this one.** Their
> reliability result stands — the pack was a deterministic function of a static input, so every
> repeat of one round read the identical field — but **no `idiomatic` or `architecture` ordering
> may be read from them**, and re-packing cannot retroactively repair a round. A code ordering
> from this field requires a *new* round. `fun`, `fun_frames`, `ux` and `audio` never read
> `judge_pack/code` and are unaffected either way.

> **⚠️ AN `architecture` ORDERING FROM THIS FIELD IS NOT LANGUAGE-BLIND (#130).** All 8 packs
> carried their stack's toolchain names, one-armed: 13 and 10 leaking files in the two Rust
> submissions against 2-3 in the other six. Every one of the 9 stored `architecture` rounds that
> left a file-open log opened at least one, in the Rust submissions specifically. `neutralise` is
> repaired and a re-sweep of all 84 stored packs reports 0, so **a round run from now on is
> blind; no round already stored is.** `idiomatic` is unaffected — it is not blinded to language
> by design.
>
> **A SECOND, INDEPENDENT REASON, and it is not confined to this field (task 87).** The
> `blind_language` rename covered the extension of the file the judge opens and none of the ones
> its content names — cross-file references in comments, import specifiers, and the `CHANGED.txt`
> the packer writes from `git diff --stat`, which lists every authored path with its true suffix.
> **2,083 arm-naming extension tokens across all 84 stored packs**, 0 after
> `field.blind_extensions` (2026-08-23). This one has no one-armed skew and no exception: **every
> `architecture` round stored in this repository read a field carrying its arms' file
> extensions**, whatever `neutralise` did or did not catch. The directory half of the leak —
> `public`, `Assets`, `res://` — is still open at 1,561 segments (task 95), so a new round is
> *more* blind than a stored one and is not yet fully blind.

**A code-aspect ordering is now available on this field, from a new round.** Before the re-pack
the `architecture` pack held 215 files against `idiomatic`'s 230, because stale copies collided
with live ones under `blind_language`'s `.src` rewrite and the stale copy won 7 collisions. Both
now hold **199, identical per submission** — each submission shown all of its own authored code
and the same amount in both aspects, which is the property a within-stack comparison needs.

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

**Its two rust diffs carry a template hunk** — the #106 formatting rewrite `just verify` performs
on a starter that is not format-clean, measured 2026-08-23 (see the `wg-g4c` entry above for the
census and why nothing is retracted). The six zero-turn rows produced 0-byte `diff.patch` files
and carry nothing. Neither observation changes the null: this run has no usable trials either way.

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

> ⚠️ **$46.79 IS TWO GAMES, AND IT WAS PUBLISHED AS ONE.** The `g2_tetris3d` rows above sum to
> **$33.63 over 10 calls** — the field stored in `pre/`. The remaining $13.16 is three `g1_pong`
> calls, a different game and a different field. `README.md`, `DECISIONS.md` and `JUDGING.md`
> each quoted $46.79 as the cost of *the* eight-submission tetris field; the cost of that field
> is $33.63. Corrected 2026-08-23, FINDINGS #121.
>
> The three `g1_pong` calls are also the only judge spend in this project with **no surviving
> artifact** — no `g1_pong__*__seed*.json` from 2026-08-16 exists anywhere (task 04, closed by
> re-running them into `wg-funframes-crossgame/pong/` for $17.66). So $13.16 is in this ledger
> and in no round file, and every other figure below is read from round files.

**Round 2 — the repaired instrument, 2026-08-17.** Same five aspects, same game, both orders,
after the `fun` telemetry repair, `architecture`'s extension-blind packs and the adjudicator
fixes. **10 calls, $31.66.** Artifacts in `runs/wg-tetris-judge-2026-08-17/post/`;
round 1 preserved beside it in `pre/` because the two together are the only clean
reproducibility evidence this project has.

**Every judge round on disk, 2026-08-23.** Read with `python3 judge/judge_ledger.py --tree
runs/`, which sums each round's own `cost_usd` and reports it against the invocation counter the
sweep stored beside it. The two are different questions and five of these directories disagree —
see the note after the table.

| sweep directory | rounds | field $ | counter stored beside it |
|---|---|---|---|
| `wg-tetris-judge-2026-08-17/pre` (round 1, un-repaired) | 10 | $33.63 | 25.55 |
| `wg-tetris-judge-2026-08-17/post` (round 2, repaired) | 10 | $31.66 | 21.05 |
| `wg-tetris-judge-2026-08-17/funframes` | 2 | $2.08 | 2.08 |
| `wg-tetris-judge-2026-08-17/repeats` | 4 | $8.12 | 8.12 |
| `wg-tetris-judge-2026-08-17/repeats7` | 7 | $10.12 | 10.12 |
| `wg-funframes-crossgame/pong` | 4 | $17.66 | 17.66 |
| `wg-funframes-crossgame/arena` | 10 | $39.53 | 14.04 |
| `wg-funframes-crossgame/platformer` | 12 | $35.79 | 30.50 |
| `wg-g4c-capgate/out/capped` | 2 | $12.06 | 12.06 |
| `wg-g4c-capgate/out/uncapped` | 2 | $15.24 | 15.24 |
| `wg-aspect-reliability` (round 3) | 30 | $100.84 | 80.37 |
| **all judge rounds on disk** | **93** | **$306.73** | |

> **These 93 rounds are eleven populations, not one.** They judge four different games with
> different aspect sets over packs from 10 KB to 3.3 MB, across the #95 re-pack boundary. The
> total is a **bill**, which is additive and safe; a per-call mean over it is rule 4 and
> `judge_ledger.py` refuses to print one.

> **The right-hand column is not a cost and must never be read as one.** It is
> `charged_to_ceiling_usd` — what the last invocation spent, which is what `--max-cost` is
> enforced against. A round already on disk is charged $0.00 on purpose so it cannot be
> double-charged, so on a **resumed** sweep the counter is smaller than the field cost by
> exactly the carried rounds. Five directories here are resumes, $69.93 in total. It was stored
> under the name `measured_cost_usd`, and that name is why $21.05 reached print. FINDINGS #121.

**Round 3 — `wg-aspect-reliability`, 2026-08-23. 30 calls, $100.84.** Task 23: six aspects x 5
repeats of ONE field in ONE presentation order, `--repeat-seed 0`, on
`wg-g4c-2026-08-21` / `g4_platformer` — the only field that supports all six aspects
(`wg-matrix` / `g3_arena` has no audio evidence for any submission, so `audio` builds a
zero-submission pack there). Artifacts and `REPRODUCIBILITY.json` in
`runs/wg-aspect-reliability/`. Result and its three caveats in `judge/JUDGING.md`.

| aspect | calls | $ | median wall | files opened |
|---|---|---|---|---|
| `audio` | 5 | $3.71 | 261 s | 9 |
| `fun_frames` | 5 | $9.70 | 372 s | 97 |
| `fun` | 5 | $9.82 | 435 s | 105 |
| `ux` | 5 | $10.78 | 347 s | 96 |
| `architecture` | 5 | $28.77 | 510 s | 86 |
| `idiomatic` | 5 | $38.07 | 559 s | 145 |
| **total** | **30** | **$100.84** | | |

**Comparability.** These 30 rounds may be compared *with each other* and with nothing else in
this ledger: they are the only rounds on this field, and the two code aspects read packs
carrying #95's stale files — a field that **no longer exists on disk**, re-packed on 2026-08-23
(see the `wg-g4c` entry above). A repeat run today reads 199 files where these read 222, so
these 30 may not be pooled with any round taken after the re-pack either. `--per-call-budget`
was held at $12 for all 30, unchanged from rounds 1 and 2, so that flag is not a variable (#33).
**Read as reliability, never as an ordering** — see `JUDGING.md`.

**Priced per aspect before launching, and that mattered.** The projection used the per-aspect
means already in this ledger ($18.55 a repeat, ~$93 at n=5) against $100.84 measured — 8% out.
A pooled per-call mean over all aspects would have priced `idiomatic` at a third of its cost.

> **A background task has a lifetime, and it is shorter than a sweep.** The first launch was
> killed at exactly 60 minutes with 10 of 30 rounds done — not a sweep failure, a harness cap on
> the *task*, and indistinguishable from a crash in the output directory. Relaunching with the
> same command cost **$0.00** for those 10 (every round is keyed by file and reused) and
> continued from round 11. Launch a sweep detached from a foreground call, not as a background
> task; `nohup` alone is enough, and `setsid` does not exist on macOS.

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


## THE TS CAPTURE PAGE CHANGED ON 2026-08-23 — a TENTH comparability break

**No TypeScript trial after this date is comparable with one before it on turns or cost**, and
the capture page's *capabilities* differ. `starters/ts/src/view/harness.ts` built the page with
`page.setContent`, which has three consequences that were all live in every TS trial to date:

| property | before | after |
|---|---|---|
| document origin | `"null"`, `baseURI` `about:blank` | `http://harness.localhost`, served from `public/` by `page.route` |
| relative asset URL | **`fetch` THROWS at URL parsing**; every three loader fails with a bare `error` | resolves as it does under `just run` |
| `DETERMINISM_SCRIPT` | **never ran** — `addInitScript` was registered against a page that was never navigated. `Math.random` unseeded, both clocks on wall time | runs; `addInitScript` now precedes `page.goto` |
| `performance.now()` / `Date.now()` | wall time (because the script was dead) | virtual: `(ticks / TICK_HZ) * 1000`, a pure function of the request |
| async assets | impossible | `window.__capturePreload`, awaited once per capture |

### What it invalidates, and what it does not

- **Not invalidated: any stored score.** Radius measured across **all 26 stored TS whole-game
  submissions** and it is **zero on every probe** — no three loader constructed in any
  capture-reachable view file, no `AnimationMixer` or `Clock`, no entropy or wall-clock read. The
  filmed frames agree: **206 of 216 TS frames are distinct**, with adjacent-frame diff and
  non-background fraction both second-highest of the four arms. **No published number rests on a
  TS submission's frames being static or empty** (FINDINGS #101).
- **Invalidated going forward:** a TS trial after this date can ship an asset pipeline. Before it,
  agents that tried had to discover the constraint and design around it — two of them did,
  explicitly, in `agent.final_text`. That cost is unmeasured, the same way #98's is.
- **Not affected:** the other three stacks. The change is confined to `starters/ts/`.
- **Still true, and now documented rather than silent:** `capture()` is synchronous and builds a
  fresh view per frame, so a loader must resolve in `__capturePreload` and `clock.getDelta()` has
  no history to measure. Recorded in the TS starter's `AGENTS.md`.

Gates re-run after the change, all green: `judge/verify_blind.py` on an out-of-repo copy (BLIND,
81 ids), `judge/starter_parity.py` ("No drift detected on any measured axis", ts now 67/67 tests),
and `tools/starter_gate_control.py --stack ts` green on pristine **and** still red on a planted
error. Pinned in both directions by `tests/render/capture-environment.test.ts` (8 tests) against
three mutants, each restoring one repaired defect — M1 `setContent` reddens 7, M2 the frozen clock
reddens the clock test, M3 an unawaited preload reddens 2. The golden frame is unchanged, so the
edit is rendering-neutral.


## ALL FOUR STARTER GUIDES GAINED A REPAIR RULE ON 2026-08-23 — an ELEVENTH comparability break

**No trial after this date is comparable with one before it on turns or cost, on any stack.** Each
`starters/*/AGENTS.md` gained a section, **byte-identical in all four**, headed *"When the gate
itself is wrong"*. The four `Boundaries` never-lists already forbade weakening the gate; they said
nothing about the case where the gate is wrong, which is what #98 was. An agent that meets a red
baseline has to do *something*, and the two things it can do are not equally safe.

What the section adds, in the order it is read: a red gate on an untouched tree is a defect in the
template, not in the work; say so in the final message, naming the recipe and the file; repairing
it is allowed; **and a repair must leave the check able to fail** — fix how the check handles the
input it got wrong, do not take that input out of what the check looks at. It closes with the
mechanical test: plant a real error in the thing the gate stopped complaining about, confirm it
goes red, then remove it.

It is stated as a **property of the repair**, not as the Godot incident. A rule whose trigger is
an enumeration has to be re-derived by every reader who meets an item not on the list, which is
this project's most-repeated documentation defect; and a rule naming one engine could not be
byte-identical across four arms without leaking that engine into three of them.

### What it invalidates, and what it does not

- **Not invalidated: any stored score.** No stored submission was written under this text, and the
  four `Boundaries` lists are unchanged, so nothing re-grades differently. The record is also
  clean on the behaviour the section governs: over all 90 stored submissions with a `diff.stat`,
  76 edited at least one file that decides their own tier-1 score and **not one weakened an
  oracle** (`eval/IMPROVEMENTS.md`, axis 2). This adds to the never-list; it does not license
  pruning it.
- **Invalidated going forward, on all four arms at once:** every agent now reads 218 more words,
  and one that meets a wrong gate takes a different path through it. Turn counts and costs before
  and after are not comparable. Unlike breaks nine and ten this one is **not one-arm** — the text
  is the same bytes in all four trees.
- **Not measurable from re-grading.** The doc half cannot be verified offline. What is verified is
  that the rule names a distinction the tooling can see.

Gates re-run after the change, all green: `judge/verify_blind.py` on an out-of-repo copy (BLIND,
81 ids, 5 trees) and `judge/starter_parity.py` ("No drift detected on any measured axis"; guide
sizes 1619–2036 words, a 1.26x spread inside the 1.35x limit, and narrower than before the edit).

`tools/starter_gate_control.py` now runs **three** directions on godot rather than two, all ok:

| direction | measured |
|---|---|
| GREEN on pristine — `just check` must exit 0 | exit 0, `CHECK scripts=18 failures=0` |
| RED on a parse error planted in the autoloaded `tools/no_raise.gd` | exit 1 |
| the plant DISCRIMINATES — `tools/check.gd` edited to skip the autoload instead of re-parsing it, **same plant**, must exit 0 | exit 0, engine reports the failed autoload and the gate does not |

Row three is the one that earns the section: it is `wg-g4c` t1's shipped repair reduced to its
mechanism, and it proves the RED row would have reported FAILED on that submission. Two controls
on row three itself, both reporting FAILED as required: a **safe** edit at the same anchor (a
comment, still re-parsing everything) leaves `just check` at exit 1, and an anchor that is not in
the file is refused rather than silently measuring the unrepaired gate. The other three stacks are
printed as **NOT PINNED IN THE THIRD DIRECTION**, reported and not failed: their `check` is a
compiler over a dependency graph and the plant sits in a root everything imports, so there is no
per-file scope for a bad repair to narrow at that address.
## THE RUST AND GODOT STARTERS CHANGED ON 2026-08-23 — a TWELFTH comparability break

**Renumbered 2026-08-23 (task 52). This section and the one above it were BOTH written as "an
eleventh comparability break" on the same day, by two sessions that could not see each other.**
Anything citing "RUNS.md's eleventh comparability break" — `tasks/26-*.md`, `tasks/47-*.md`,
FINDINGS #106 — means one of the two, and the way to tell them apart is by what changed: the
eleventh is the repair-rule section added to all four guides (task 47), the twelfth is this one,
the rust and godot capability change (task 26). Nothing about either run is altered; only the
ordinal is.

Task 26, the first instalment of `DECISIONS.md`'s "each template at its stack's best, not at a
common floor". **Two arms of four changed. `starters/ts/` and `starters/unity/` are untouched
apart from a comment in the shared launch file.**

**No Rust trial after this date is comparable with one before it, on turns, cost, or what the
submission was able to contain.** The `bevy` feature list went from `["2d", "png", "libm"]` to
Bevy's own default set plus `wav`/`png`/`libm`:

| property | before | after |
|---|---|---|
| lit 3D | **impossible.** `MeshMaterial3d` lives in `bevy_pbr`, which the `2d` bundle excludes — on a task set where two of four games are 3D | `Mesh3d` + `MeshMaterial3d<StandardMaterial>`, `DirectionalLight`, `PointLight`, real-time shadows |
| audio | **no `AudioPlayer` at all**, while `AUDIO_NOTE["rust"]` in the prompt said "Audio is Bevy's `AudioPlayer`" and audio is a **scored** criterion | `bevy_audio` + rodio, WAV decoder on |
| UI | `Text2d` and sprites only | `bevy_ui` |
| the pin change itself | the prompt told the agent to make it; every `AGENTS.md` marks a feature-list edit ⚠️ *ask first* | already made |
| cold `just verify` from an empty target dir | warm 129 s + verify 38 s = **167 s** | warm 248 s + verify 22 s = **270 s** |
| warm `just verify` | **2.7 s** | **4.2 s** (`just quick`, the documented inner loop, is unchanged at ~0.8 s) |
| audio device on the capture path | none could be opened — no audio feature | `AudioPlugin` **disabled** in `harness.rs`; measured, removing it took `just test-render` from 11.7 s to 8.5 s |

**No Godot trial after this date is comparable with one before it on what the submission was able
to contain, and its `just verify` now runs nine render assertions instead of six.**
`view/fx.gd` exposes `GPUParticles2D` as one call, `View` owns an idle `Fx`, and three render
tests pin it: the burst is drawn, the age drives it, two identical bursts are byte-identical.
**The golden frame is unchanged** — an unused `Fx` allocates nothing and lights no pixel — so the
edit is rendering-neutral on the pristine tree.

### What it invalidates, and what it does not

- **Not invalidated: any stored score.** Nothing here changes how anything is graded, and no
  stored submission is re-read. The rubric, the weights and the bot are untouched.
- **Invalidated going forward, and this is the point:** a Rust submission after this date can
  ship a lit 3D scene and sound without spending turns on a pin change it was told to ask about
  first. Before it, `g2_tetris3d` and `g3_arena` Rust agents had to do that work or build the
  game in orthographic 2D. That cost is unmeasured, the same way #98's and the TS capture page's
  are.
- **Cost direction is not obvious and should not be assumed.** Cold build is +103 s per trial;
  turns spent on the pin change and on hand-rolling menus out of `Text2d` are removed. Which
  dominates is an empirical question this note does not answer.
- **Two pristine-tree formatting defects were repaired in passing**, because `just verify` runs
  `fmt` and repairs them on the agent's first invocation whether anyone wants it or not:
  `crates/game/src/main.rs` (rustfmt) and `tools/no_raise.gd` (gdformat). See FINDINGS #106 —
  every stored Rust and Godot trial diff contains a hunk no agent wrote.
- **`starters/_shared/launch.just` changed in all four trees**, identically, because its Rust row
  asserted "no audio feature, so a pristine tree cannot open an audio device at all" and that
  stopped being true. Comment only; ts, unity and godot behaviour is unchanged.

Gates re-run after the change: `judge/verify_blind.py` on an out-of-repo copy of all four
starters (**BLIND**, 81 criterion ids, exit 0); `judge/starter_parity.py --skip-tests`
(**"No drift detected on any measured axis"**, hash chain 401 ticks with rust/ts/godot
byte-identical and unity's known 1-ULP divergence, shared launch file identical in all four at
`da9914ce2e54beaa`); `tools/starter_gate_control.py` green on pristine and red on the planted
error for every arm. The capability register in `starter_parity` now reports four capabilities
instead of one and states in its own output that divergence is the design, not drift.


## THE UNITY STARTER CHANGED ON 2026-08-23 — a THIRTEENTH comparability break

Task 52, the second and final instalment of the same decision. **One arm of four changed.**
`starters/rust/` and `starters/godot/` are untouched; `starters/ts/` gained documentation only —
one AGENTS.md section, no code, no pin, no recipe.

**No Unity trial after this date is comparable with one before it on what the submission was able
to contain, and its `just verify` now runs nine render assertions instead of six.**

| property | before | after |
|---|---|---|
| audio | **`AudioSource` and `AudioClip` did not compile.** Measured on the pristine tree: `error CS1069 … forwarded to assembly 'UnityEngine.AudioModule'`, four of them, `just check` exit 1. `AUDIO_NOTE["unity"]` in the prompt says *"Audio is `AudioSource`/`AudioClip`"* and audio is a **scored** criterion | `com.unity.modules.audio`, resolved `source: "builtin"` from the installed editor with the network irrelevant. `just check` exit 0 on the same probe file |
| particles | **`ParticleSystem` did not compile** (`CS1069`, `UnityEngine.ParticleSystemModule`) | `com.unity.modules.particlesystem`, also `builtin`; `Assets/View/Fx.cs` exposes it as one call and `GameView` owns an idle `Fx` |
| `just verify`, warm | ~12 s, 26 sim + 6 render assertions | **15.8 s**, 26 sim + **9** render assertions |
| the pin change itself | the prompt told the agent to ship sound; `AGENTS.md` marks a `Packages/manifest.json` edit ⚠️ *ask first*, so the arm was told to ask permission for the thing it had been told to do | already made |
| audio device on the capture path | *see below — unchanged, and not for the reason anyone assumed* | unchanged |
| audio device on the LAUNCH path | `StarterLaunchGuard`'s reflection found no `AudioListener` and logged *"this project has no audio module — nothing can play"* | the guard's **live** branch runs for the first time: *"SILENT LAUNCH ACTIVE — AudioListener.volume=0, pause=True"*, and the unguarded control logs *"silent launch NOT requested"* |

**The golden frame is unchanged.** An idle `Fx` builds no GameObject, no material and no emitter
until something asks for a burst, so the edit is rendering-neutral on the pristine tree — the
same property the Godot `Fx` has, and `MatchesGoldenFrame` is green without a re-bless.

**The three new render tests are pinned by a mutant.** Commenting out the single
`view.Fx.ShowBursts(bursts)` line in `RenderHarness` turns `ABurstIsDrawn` and `ABurstAges` red
with the numbers in their messages (`0.0000% added ink`; `0.0000% of pixels differ`) and leaves
the other seven green, which is what a criterion that measures its own mechanism looks like.

### The audio-device hazard that was checked, and what the check found

Bevy's audio capability opened a device on the capture path silently, so the same question was
asked of Unity, with the pristine manifest as the control. `sample` on a live batchmode editor,
counting `FMOD::OutputCoreAudio` frames on a CoreAudio IO thread:

| arm | frames |
|---|---|
| pristine manifest (no audio module), `-disable-audio` | **2** |
| audio module, `-disable-audio` | **1** |
| audio module, no `-disable-audio` | **1** |

**Unity's batchmode editor runs an FMOD CoreAudio output regardless of the manifest and
regardless of `-disable-audio`** — it did so on every matrix already graded, and the module adds
nothing. So there is no new hazard on the capture path and no new guard is needed. What is *not*
established is that `-disable-audio` achieves what `tools/unity-tests.sh` says it does (*"an
editor that opens an audio device also contends for one"*); it plainly does not close this one.
The flag is kept — it is harmless and the rationale is repaired rather than the code — and the
launch path, which is where a human would hear something, is guarded and measured above.

### What it invalidates, and what it does not

- **Not invalidated: any stored score.** Nothing here changes how anything is graded and no
  stored submission is re-read.
- **Invalidated going forward:** a Unity submission after this date can ship sound without a
  manifest edit it was told to ask permission for. Every Unity submission before it faced a
  scored criterion whose named API was a compile error. That cost is unmeasured, in the same way
  #98's and the TS capture page's are — and it is now the *only* difference of that shape left in
  the matrix, because the audio row of `starter_parity`'s capability register no longer varies.
- **The ts arm is NOT a regime boundary.** No file under `starters/ts/` other than `AGENTS.md`
  changed, `just verify` runs the same 67 tests, and the golden frame is untouched. It is
  recorded here only so that "ts changed on 2026-08-23" cannot later be inferred from silence.

Gates re-run after the change: `judge/verify_blind.py` on an out-of-repo copy of all four
starters (**BLIND**, 81 criterion ids, exit 0); `judge/starter_parity.py` with tests
(**"No drift detected on any measured axis"**, 4 of 4 stacks really ran their suites at
22/22 rust, 67/67 ts, 35/35 unity, 26/26 godot, hash chain 401 ticks, guides 2032-2249 words);
`tools/starter_gate_control.py` over all four, **29 measurements, 0 FAILED, 0 NOT CHECKED**,
including the verify-idempotence direction on the modified unity and ts trees.


## `template-ts/` CHANGED ON 2026-08-23 — a FOURTEENTH comparability break, and the first that is NOT about the starters

**This one bounds a different suite.** Every ordinal above is about `eval/starters/*/`, which is
what `wholegame.py` copies. This is about `template-ts/`, which only `eval/run-bakeoff.sh` ->
`runner.py --template` ever reads. **No whole-game number is affected, and that was verified
rather than assumed**: `STARTERS = HERE / "starters" / s` is the only starter address in
`wholegame.py`, and no `run` subcommand of it takes a template path.

Task 48. `template-ts/src/view/harness.ts` carried the pre-fix capture page that #101 repaired in
`eval/starters/ts/` a day earlier: a `null` document origin, an `addInitScript` registered against
a `setContent` that never navigates so the determinism script was dead, and the frozen clock that
the origin fix would otherwise have activated. All three are now repaired the same way — a
`page.route` origin served from `public/`, `addInitScript` before `goto`, and a **virtual** clock
at `ticks / TICK_HZ * 1000`.

**What it invalidates:** the four stored `bakeoff-*` runs (2026-08-10..12) were built on the
pre-fix templates. They are already outside this ledger — see its opening note about the $153.82 of
spec-change runs — and no spec-change run has happened since **2026-08-12**. Nothing
stored is re-read; a future spec-change run on `template-ts` is not comparable with those four on
what a captured frame could contain.

| property | before | after |
|---|---|---|
| `location.origin` in the capture page | `"null"` | `http://harness.localhost` |
| a relative `fetch` | **threw at URL parsing**, so every three loader was dead | `200`, served from `public/` |
| the determinism script | never ran; `Math.random` unseeded, both clocks on wall time (`performance.now()` 130.9 -> 194.4 over a 60 ms sleep) | runs; `__determinismApplied`, the injected LCG, virtual clocks |
| `just verify`, warm | green, 53 sim + 5 render | green, 53 sim + **13** render |
| `AGENTS.md` | said nothing about assets, preload or clock semantics | documents `__capturePreload` and virtual time, as the ts starter does |

**The golden frame is unchanged and was not re-blessed.**

Gates re-run after the change: `judge/verify_blind.py` on an out-of-repo copy of `template-ts`
(**BLIND**, 81 criterion ids, exit 0; **CONTAMINATED, exit 1** with the canary planted, so the
scanner was shown able to fail on this input). Four mutants against the ported
`tests/render/capture-environment.test.ts`: restoring `setContent` reddens 7 of 8, a constant
clock reddens the clock test, an unawaited preload reddens the failing-preload test, and removing
the document-root containment reddens the escape test. `judge/starter_parity.py` is **not**
applicable — it reads `eval/starters/` and compares stacks, never a stack against its own second
tree, which is the gap FINDINGS #112 is about.

### Superseded the same day: the tree this bounds no longer exists — 2026-08-23

`template*/` was deleted (`DECISIONS.md`, task 56, #122). **This is NOT a fifteenth comparability
boundary, and the reason is worth stating rather than leaving to inference: a boundary bounds
future comparisons, and there is no future spec-change run to bound.** The ordinal above stands as
written — it is the record of a change that really happened to a tree that really existed — and
its last paragraph is now unconditional: *a future spec-change run on `template-ts` is not
comparable with those four* becomes *there will be no future spec-change run without first
restoring the tree from git, at which point the restorer inherits this boundary and every starter
repair made after 2026-08-23 that never reached the fork.*

**Nothing in this ledger changes.** The 71 spec-change trials in 12 run directories and their
$153.82 were already outside it (opening note), they are still on disk, and what they were asked to
do is still in `eval/suites/` — which is why those files were kept when the trees went (#122).
Every whole-game figure in this file is `eval/starters/*`, untouched.


## THE TS, UNITY AND GODOT STARTER GUIDES CHANGED ON 2026-08-23 — a FIFTEENTH comparability break

**The ordinal is free.** The section above deletes `template*/` and says explicitly that doing so
is *not* a fifteenth boundary, because a boundary bounds future comparisons and there is no future
run to bound. This one does bound future runs.

**No trial after this date is comparable with one before it on turns or cost, on ts, unity or
godot.** Each of those three `starters/*/AGENTS.md` gained a sentence saying that a **Stop hook
re-runs `just verify` when you try to finish, so ending the turn red does not work.** The rust
guide has carried it since the hook was written; the other three never did. Task 78, found by
task 67.

**The hook itself is unchanged and was already live in all four arms.**
`.claude/hooks/verify-gate.sh` is present in every starter and wired under `"Stop"` in every
`.claude/settings.json` — the four settings files are byte-identical — and `wholegame.py` passes
`--setting-sources project`, which loads them. So three arms have been running under a gate their
guide never mentioned. That is a difference between arms that nobody chose, and it is the reason
this is a repair rather than a wording change: the hook is **harness**, identical in all four
trees, not a stack-native fact like Bevy's API delta or Godot's headless limitation.

Wording is stack-native, as `DECISIONS.md` requires; only the silence is removed. Unity's sentence
adds that each blocked attempt costs another batchmode editor launch; godot's adds that each one
opens the window its own guide already documents.

### What the stored trials can and cannot say about it

The obvious question — *does the sentence change what an agent does?* — **the stored evidence
cannot answer, and the reason is that the outcome has no variance, not that the effect is small.**

A Stop-hook block is recorded in the session transcript as a `user` entry with `isMeta: true`
whose content begins `"Stop hook feedback:"`. Counting those across every stored trial transcript:

| population | trials | Stop-gate blocks |
|---|---|---|
| trials with a stored per-trial starter baseline, guide **mentions** the hook (rust) | 4 | **0** |
| the same, guide **silent** (ts, unity, godot) | 8 | **0** |

The 20 stored baselines (`wg-g4`, `wg-g4b`, `wg-g4c`) are the only trials where the exposure is
provable from artifacts rather than from today's working tree, and 12 of them reached a stop at
all — the other 8 are `wg-g4b`'s `api_error` population, which never got there. Zero events in
both arms is a null with **n=0 outcomes**, not a measured no-difference.

Across the whole archive only **19 transcripts** carry any block, every one of them dated
2026-08-11 or 2026-08-12 (`bakeoff-*` and the first `wholegame-work` run). No transcript from
`wg-matrix` (2026-08-13) onward carries one.

**Do not read that as "the gate is dead", and do not read it as "the gate is working" either.**
Measured directly, at CLI 2.1.220 — the version every stored transcript records — with the
harness's own flags: a Stop hook that blocks produces a visible `Stop hook feedback` entry and the
agent acts on it; **a Stop hook that exits 0 leaves nothing in the transcript at all.** The two
arms of that control are in the task 78 record. So "no block" is consistent with *verify was green
at every stop* and with *the hook did not run*, and no stored artifact separates them. What is
established is that the guards cannot have short-circuited in `wg-g4c`: every arm's precondition
held in the live work trees (ts `node_modules`, unity `Library`, rust `CARGO_TARGET_DIR`, godot
`just` on `PATH`).

### What it invalidates, and what it does not

- **Not invalidated: any stored score.** No stored submission was written under this text, nothing
  is re-graded, and no criterion reads a guide.
- **Invalidated going forward, on three arms:** an agent told that ending the turn red does not
  work has a reason to run the gate before finishing. Turn counts and costs on ts, unity and godot
  before and after are not comparable. **Rust is unchanged**, so this is a three-arm break, the
  first of that shape.
- **Not measurable from re-grading.** Same as breaks eleven and thirteen: the doc half cannot be
  verified offline.

### The axis that now sees this shape

`starter_parity.py` could not have caught it and never could have: its near-miss heading check
fires only on a heading in every guide but one, and this was a **sentence** present in **one guide
of four**. `mechanism_findings()` replaces that blind spot with the resource rather than the
instance — *every hook event wired in every starter's `.claude/settings.json` must be named in
every `AGENTS.md`* — so a hook added tomorrow is covered by the same row. An event wired on some
stacks only is reported as a stack choice and never fails; an empty intersection says it compared
nothing rather than reporting agreement.

Pinned in both directions in `judge/parity_selftest.py` (**60 expectations, 0 failed**, up from
44): the mutant is the sentence removed from each of the four guides in turn, all four red; the
variants are a **different** event (`PreToolUse`) wired everywhere and named nowhere, which must
also go red or the check is an assertion about the word "Stop"; a guide containing both "stop" and
"hook" far apart, which must **not** count as a mention; and a reworded *"a hook on Stop"*, which
must still count.

Gates re-run after the change: `judge/starter_parity.py` — **red before the guide edits**, exit 1,
one finding naming exactly `['godot', 'ts', 'unity']`; **exit 0 after**, "No drift detected on any
measured axis", guides 2032–2273 words (1.12x, inside the 1.35x limit).
`judge/verify_blind.py` on an out-of-repo copy of all four starters: **BLIND**, 81 criterion ids,
4 trees, exit 0.

`tools/starter_gate_control.py` over all four: **29 measurements, 1 FAILED, 0 NOT CHECKED**,
exit 1. The one failure is `godot: GREEN on pristine (the same just verify must also exit 0)` —
`test-render` exit 1 on an untouched tree. **It is not caused here and it is not new:** task 67
measured the same row FAILED on 2026-08-23 before this task began, and filed it as `tasks/80`;
`git diff main -- eval/starters` is three markdown sentences in three `AGENTS.md` and nothing else,
and `starter_gate_control.py` reads none of them. The row that would have caught a defect from
*this* change is a different one, and it is green on all four: **UNCHANGED by its own `just verify`
on a pristine tree** — the ts arm runs prettier over the tree inside `verify`, so a reformatted
`AGENTS.md` would have shown up there as a modified path (the #106 shape). No tracked file changed
on any stack. Rust, ts and unity are green on every direction; the three NOT PINNED IN THE THIRD
DIRECTION rows are the standing report, unchanged.
## THE RUST STARTER GAINED `default-run` ON 2026-08-23 — a SIXTEENTH comparability break

**Check the ordinal before citing it.** Fifteen and sixteen were allocated the same day by
sessions that could not see each other, which is what produced the twelfth/eleventh collision
above. Cite the heading, not the number.

`eval/starters/rust/crates/game` ships two binaries — `src/main.rs` (target `game`) and
`src/bin/film.rs` — and the manifest had no `default-run`. That is cargo's documented
ambiguity condition, and `justfile:152` is the exact command it breaks:

```
$ cargo run -p game --release --offline          # pristine tree, cargo 1.97.1, 2026-08-23
error: `cargo run` could not determine which binary to run. Use the `--bin` option to
       specify a binary, or the `default-run` manifest key.
available binaries: film, game
$ echo $?
101
```

It lands in under a second, offline, having compiled nothing. `crates/game/Cargo.toml` now
carries `default-run = "game"`; the same command then enters compilation with no
target-selection error. Both directions were also pinned on a two-binary fixture that really
executes — exit 101 without the key, exit 0 printing `RAN=game` with it, and still `RAN=game`
after a third binary is added, which is the shape the agents below actually produced.

**Who paid for it: 12 Rust trials across 5 runs**, each diagnosing it and adding this same line
itself — `wg-matrix` (all six rust trials), `wg-audio` (g1_pong t0, t1), `wg-audio48` (g1_pong
t0, g2_tetris3d t1), `archive-arena2d-wg-audio48` (g3_arena t0), `wg-g4` (g4_platformer t1).
The producer is a grep of `runs/**/artifacts/*rust*/agent_result.json` → `.result`;
`eval/tools/disclosure.py` located 4 of them on the cue set it had then, which is why `tasks/81`
says four. It now locates **all 12** — the cue was matching the *complaint* ("`just run` was
broken in the starter") and 8 of the 12 state the same defect as the *repair* ("`crates/game`
gained `default-run`"), which no widening of the breakage vocabulary could reach (`tasks/94`).
Nothing else in ten days of stored evidence had noticed.

**What this boundary can and cannot have changed, stated because it is smaller than the heading
suggests.** `just run` has been REFUSED under the harness on rust since the seventh
comparability break (2026-08-17, `STARTER_NO_RAISE=1`), and the refusal branch returns 1 before
reaching cargo — verified on a pristine copy. So the recipe has not reached the ambiguity in any
trial from `wg-g4b` onward, and both `wg-g4c` rust agents wrote that they did not launch it. The
residual exposure after 2026-08-17 is an agent typing `cargo run -p game` directly, which the
Bash allowlist permits; no stored trial after that date is on record doing so. **The turns this
cost were spent in the five runs listed above, all of them before the refusal existed.**

**What it demonstrably does NOT change**, so a rust arm before and after is still comparable on
everything graded:

| axis | before | after |
|---|---|---|
| `starter_parity` hash chain, seed 7, its own 400-input tape | 401 hashes | 401, **byte-identical** — first `0x912e3a873849bcce`, last `0x9d53ded21eb09ce7` |
| `just --summary` recipe set | 19 | 19, same names |
| `AGENTS.md` | 2032 words | unchanged |
| hook, CI, harness files | present | unchanged |

The chain comparison was run through `starter_parity.hash_chain` itself rather than a
re-implementation, and its own control — perturbing one tick — reports a difference, so the
equality is not the instrument agreeing with itself.

Gates re-run after the change: `judge/verify_blind.py` on an out-of-repo copy of the repaired
starter — **BLIND**, 81 criterion ids, exit 0; and **CONTAMINATED, exit 1** with the canary
planted in the very file that changed, so the scanner was shown able to fail on this input.
`judge/starter_parity.py --skip-tests` over all four stacks with the repaired rust in place:
exit 0, *no drift detected*, all four chains 401. `judge/parity_selftest.py`: 60 expectations, 0
failed, exit 0 unpiped — run from the main checkout, because a worktree has no `node_modules`
and its ts positive control cannot run there (that is the one failure it reports in a worktree,
and it is environmental, not a regression).

**The fix is `default-run`, not `--bin game` in the recipe.** The thing that fails is the
command `cargo run -p game`, by whatever path it is typed, and agents type it directly; repairing
only `justfile:152` leaves every other caller broken and would be the enumeration failure this
project keeps paying for. `just film` and `just probe` already pass `--bin` and were never
affected.

## THE GODOT RENDER TESTS AND FOCUS GUARD CHANGED ON 2026-08-23 — a SEVENTEENTH comparability break

Task 80, FINDINGS #132. **No Godot `verify.green` result from before this date is comparable with
one after it, and the reason is that before it the result was not a constant.**

`starters/godot/tools/no_raise.gd` is an `[autoload]`, so it ran in every godot process rather
than only in `just run`. Its last-resort escalation MINIMISES the window; macOS then stops
producing frames and returns the last image drawn, so `capture_frame` handed the same stale
picture to every rendering test. Whether the escalation fires is a race with macOS activation.

Measured on fresh `wholegame.prepare` copies, harness uninvolved:

| tree | `just test-render` |
|---|---|
| pristine, before — every Godot trial since the autoload arrived on 2026-08-17 | **5 of 12 FAILED**, 3 passed / 6 failed each time |
| pristine, before, forced onto the minimise branch | **8 of 8 FAILED** |
| pristine, before, minimise removed (`NO_FOCUS` flag kept) | 0 of 12 failed |
| pristine, after | **16 of 16 green**, all 9 tests measured, 9 of the 16 on the minimise branch |

### What it invalidates, and what it does not

- **Not invalidated: any stored score, but only because the direction is known.** The defect can
  only turn a green `verify` red, never the reverse — a frozen frame fails six tests, it does not
  pass any that should fail. A stored Godot `verify.green` of **False** is therefore not safe to
  read as a statement about the submission; a **True** is.
- **Invalidated going forward:** a Godot trial after this date faces a `just verify` whose render
  half is stable, so its turn count is not comparable with one that may have spent turns chasing
  an arena transform that was never wrong.
- **Not affected: the other three stacks**, and this is measured rather than reasoned. Only godot
  opens a render window. In the same `starter_gate_control.py` run that failed this row before the
  repair, rust, ts and unity were green on **21 of 21** measurements.
- **The golden frame is unchanged and was not re-blessed.**

### The second change in the same file, which is not a scoring change at all

Under `--headless` there is no window, but the dummy `DisplayServer` answers
`window_is_focused()` with **true**, so `check`, `test-sim`, `probe` and `probe-file` each printed
*"window raised anyway; minimised to return focus"* — a claim to have minimised a window they
never had. It was the LAST line those recipes emitted, so it is what `starter_gate_control.py`
recorded as their evidence, and it landed on `just probe`'s **stdout**, documented as carrying
nothing but JSON trace lines. Pinned both ways by parsing every stdout line of `just probe`:
before, 4 lines of which 1 is not JSON; after, 3 lines of which 0 are.

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
- **Read the closing message before grading, and read it WHOLE.** Four agents wrote a
  paragraph headed *"What I could not verify — and why"* naming the exact mechanism that
  produced this run's entire spread, and it sat unread for a day. `wholegame.py report` now
  prints it; it reads `agent_result.json` → `.result`, because this run's `g3_arena__rust__t1`
  states the mechanism at character 0 of a 3912-character message and `agent.final_text` keeps
  only the last 3000.
