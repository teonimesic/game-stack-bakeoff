# Run ledger

Every agent run, what resource it used, and what it may be compared with. Read before pooling
any two runs — most of these are **not** comparable, and the reasons are specific.

> **THE UNIT, once, for every `$` figure in this file: `$n` is `tokval`** — the list price the
> tokens would carry at published API rates, on a subscription account where no money moves per
> token. It is `sum(modelUsage[*].costUSD)`, which the CLI computes from the token counts
> whatever the billing arrangement, and it is the only per-trial resource number the harness has.
> The token counts are real and every comparison below stands; the unit is a valuation, not a
> bill, and **no decision may rest on one as money** (FINDINGS #159).
>
> The figures stay in `$n` form rather than being annotated on each of the **130** lines that
> carries one (`grep -c '\$[0-9]' eval/RUNS.md`): per-run rows are what a reader compares runs
> by, and a note on every line would be worse than the defect.
> `python3 eval/tools/tokenvalue.py --definition` prints this, and every producer prints it
> beside its own output.

**Two columns, not one.** `records` is the valuation represented by the run's surviving trial
JSONs (`agent.cost_usd`); `built log` is the same quantity summed from the `[built]` lines of
every build log the run produced. They differ whenever a cell was retried, because a retry
**overwrites the record of the attempt it is retrying** (FINDINGS #36). Both were re-read from
disk on 2026-08-15; neither is carried forward from a previous version of this file.

| run | n | records | built log | terminal | games | task | limits |
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
| agent trials, **surviving records** | **$2,466.31** over 162 trials in 24 run directories, **161 of them priced** | `python3 eval/tools/census.py` — `agent.cost_usd` in every `runs/**/trials/*.json`, at any depth, **`claude`-harness records only**: the 162nd is the prime-agent probe and its vendor's USD is not addable to this figure |
| specialist-judge rounds | **$334.41** over 97 rounds in 12 sweep directories | `judge/judge_ledger.py --tree runs/` |

**Records, not totals, and the gap is real but not summed here.** A retry overwrites the record
of the attempt it replaces (#36), so the true figure is **at least** $2,466.31. It was measured
once, for the runs existing on 2026-08-15, at ~$21.61 of overwritten attempts. It is **not
re-derived above and must not be inferred from the `[built]` lines**: those sum to $2,262.17,
*less* than the records, because `wg-arena3d`'s retries ran under a second log this ledger already marks
`+ retries` and `wg-audio48`'s log carries `archive-arena2d`'s trials too. A number that is
smaller than its own lower bound is a reading of the wrong artifact, not a correction.

> ⚠️ **This line read "~$1,547" until 2026-08-23 and had done since 2026-08-15**, and it went
> stale **twice over, in two different ways**:
>
> | | |
> |---|---|
> | 3 runs that did not yet exist | `wg-g4`, `wg-g4b`, `wg-g4c` — **$698.21**, 29% of the project's agent-trial total |
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
>
> **A row for a live run is a moving number.** `wg-audio48` was still building its last four arena
> trials when this warning was written. An earlier version of this file recorded *$571.15, 19
> completed, 5 api_error* — read from disk correctly, describing a state that lasted minutes. Mark
> in-flight rows provisional; a run's total is final only when its terminal reasons are.
>
> **It then happened to the headline, twice, and the second time nobody noticed for eight days.**
> The row settled; the total above it did not, because the total had no producer and no read date.
> Both now have one.

## What may be compared with what

Five things break comparability. Four have bitten; the fifth is new, and it is the only one
that is a property of the *instrument* rather than of the configuration:

1. **The task changed — twice.** Audio, presentation and pacing entered every prompt on
   2026-08-14: tier 1 went from 9 criteria to 14, tier 2 gained one. Then on **2026-08-15 the
   arena task was rewritten**: a three-dimensional volume, analog input, three enemy kinds,
   materialisation before an enemy is dangerous, a score multiplier, gamepad and mouse support,
   and on-screen requirements for bursts, boundary reaction and depth. Tier 2 for `g3_arena` went
   from 15 criteria to 22.
2. **The permission allowlist changed.** Without it agents lose ~30% of turns to denials.
3. **The budget cap changed, and the cap is visible to the agent.** See FINDINGS #33. Token
   usage responds to the stated ceiling: Tetris ran **$23.20 at $25 and $35.66 at $48, 1.54×**.
   Every figure here is partly a measurement of the cap we set, so comparisons are valid only
   *within* a cap regime — and the capped arms were pacing themselves against a constraint that
   does not exist on this account (#159), so their records are short for nothing.
4. **The turn limit changed, and at $48 it had already become the binding one.**
   `g3_arena__rust__t1` stopped at 251 turns and $35.75 with $12 of its stated budget unused
   (FINDINGS #35). From 2026-08-15 the standing configuration is `--max-turns 1000` and **no
   budget cap** — a fourth regime, and the first in which nothing communicates a budget to the
   agent. **Its resource use is unmeasured**; calibrate before committing a matrix.

5. **The agent harness is a variable, from 2026-08-24.** Every record before that date was
   built by the `claude` CLI, and nothing said so — `python3 eval/tools/census.py` prints the
   partition, and its **whole-game** population read `harness claude 90, prime-agent 1` on
   2026-08-24. (The tree total a few rows above counts both populations, so the two figures
   are not the same denominator.) A harness change is not a configuration change; the arms
   differ in ways no flag can equalise, and the differences are listed in the section below.

Practically: `wg-matrix` (pre-audio, $25) and `wg-audio48` (audio, $48) are each internally
consistent and mutually incomparable. `wg-audio` at $25 is a partial third regime. Anything built
from 2026-08-15 onward is a fourth, and its arena trials answer a different question from every
arena trial before them.

**Those two runs are also barred from code-aspect judging**, which is a separate axis from the
regime boundaries above and applies within each of them: their packs cannot be re-packed and the
builder already refuses them. See the section on their stored packs, below.

## THE HARNESS IS AN ARM DIMENSION, and the two arms cannot be equalised — measured 2026-08-24

`wholegame.py --harness <name>` chooses the agent CLI; the standing arm is `claude` and
`prime-agent` 0.7.1 (`openai-codex`, `gpt-5.6-sol`) is the second. **Every difference below was
measured, not read off `--help`**, and each is a property of the CLIs rather than of a setting
either of them exposes. `eval/agent_harness.py` holds the evidence for each row and
`eval/tools/agent_harness_control.py` pins the readers.

| | `claude` | `prime-agent` |
|---|---|---|
| **money** | `cost_usd` is `tokval`, Anthropic list price | **`cost_usd` is `None`, always.** Its own USD is OpenAI list price and is stored as `vendor_cost_usd_not_comparable` |
| **tokens** | `modelUsage`, a running total, read once | `usage` per assistant message, **not cumulative** — summed |
| **turns** | the CLI's `num_turns`, every turn of its loop | assistant messages in `agent_end`. Different units; every record carries `turns_definition` |
| **turn ceiling** | `--max-turns 1000`, invisible to the agent | **none.** `--autonomous-max-turns` needs `--autonomous`, which adds continuations and gate re-runs the claude arm never sees. Bounded by the 4-hour harness timeout instead |
| **permission regime** | a command-pattern allowlist (`Bash(just *)`, …), which costs ~30% of turns to denials | **no equivalent.** `-t/--tools` filters tool NAMES; it runs arbitrary code in an IPython kernel and writes files unattended |
| **the Stop gate** | wired in every starter's `.claude/settings.json`; refuses to end a turn while `just verify` is red | **not run at all** — no other CLI reads that file. `stop_hook.harness_supports_stop_hook` says so in the record, because `log: absent` alone would read as a silent pass |
| **the starter's guide** | `CLAUDE.md`, which is `@AGENTS.md` | `AGENTS.md` directly — prime-agent takes the first of `AGENTS.md`, `AGENTS.MD`, `CLAUDE.md`. Same text both ways, confirmed in the probe below |
| **operator isolation** | `--setting-sources project` and `--strict-mcp-config` | **no flag does this.** It reads a context file from every ancestor of the trial tree to `/`, plus its agent directory; `-nc` stops that AND removes the starter's own `AGENTS.md`, so it cannot be used. The guard is an assertion in `preflight()`, whose findings go into every record |
| **free parameter** | — | `--thinking`, pinned to `high` on the argv. It has no claude counterpart, and `~/.prime/agent/settings.json` would otherwise choose it along with the model |

**Three token comparisons are safe and one is not.** Input, output and cache counts are real
on both arms; **prime-agent's system prompt floor is ~3,931-4,034 input tokens** on a one-line
prompt, measured, so subtract a floor before comparing per-trial input. Dollars are not
comparable at all and the tooling now refuses to pool them: `census.py` sums `claude` records
only and prints how many it excluded, and `cost_census.py` drops a foreign record before any
floor or range is computed.

### `wg-harness-probe-primeagent-2026-08-24` — the end-to-end probe. NOT a submission

| | |
|---|---|
| what | one trial, `g1_pong__rust__t0`, rust starter, **`--prompt-file`** — a 598-byte probe prompt, not the pong task. `prompt_override: true` in the record |
| result | `completed` (mapped from `stopReason: stop`), **2 turns, 8,342 in / 254 out / 6,656 cache-read**, 10.3s, 1 file changed, capture exit codes all 0 |
| money | **none recorded.** `cost_usd: null`; the vendor's own figure, 0.052658 USD of OpenAI list price, is stored under `vendor_cost_usd_not_comparable` and enters no total |
| what it establishes | the arm runs end to end through the real harness: preflight, argv, the CLI, the parse, the normalise, the artifacts and the stored record. The agent answered `verify command: just verify` and `crates: game, sim` — both true of the rust starter — so the **product channel reaches this arm** |

**Never pool this record with a game population.** It carries `game: g1_pong` because every
record does, and it was not asked to build pong.

## THE TWO CLOCKS THAT TIME A TRIAL, and they agree to a measured median 1.1 s — 2026-08-27

**Not a comparability break, and no figure in this file moves.**

**Use `wall_s` for every wall-clock figure**, and both harnesses record it on every trial. Where
the agent CLI reports a duration, `duration_ms` is stored separately — the CLI's own account of
the same trial. **6 stored records have no self-report**, enumerated at the end of this section.

**The two are not one quantity under two names. They are two stopwatches on nested intervals,
held by different parties:**

| | who holds the stopwatch | interval | clock |
|---|---|---|---|
| `wall_s`, `wholegame.py` | `wholegame.py` itself, around its own `run_agent()` | subprocess spawn, the CLI's whole life, reading its stdout, parsing it | `time.monotonic()` |
| `wall_s`, `runner.py` | `runner.py` itself, around the same call | the same span | `datetime.now()`, which an NTP step or a DST change moves under it |
| `duration_ms` | the `claude` CLI, in its own result object | its internal run alone | the CLI's own |

**The conversion.** Over **157** paired observations `wall_s - duration_ms/1000` is min
**0.9 s**, median **1.1 s**, max **6.5 s**, and **negative on none of them**. That difference is
the timing script's own spawn-and-parse overhead. `python3 eval/tools/wallclock.py` produces
every figure in this section, and it **fails on any negative delta**. It takes its tree walk and
its population partition from `census.py` rather than reimplementing them, so its record counts
cannot disagree with `python3 eval/tools/census.py`.

> **A negative delta has 2 possible causes and its magnitude separates them.** `wall_s` is
> stored rounded to 0.1 s and `duration_ms` is not, so a genuine overhead under 50 ms can read
> as a delta down to **-0.05 s** — an artefact, not a defect. **Anything larger is a clock that
> moved**, which `runner.py` is exposed to and `wholegame.py` is not: only the second brackets
> with `time.monotonic()`. The observed minimum is +0.9 s, so neither has happened yet.

> **The overhead is additive, not proportional**: ~1 s on a 1.6 s trial and ~1 s on a 4961 s
> one. **Report the distribution in seconds. Do not subtract the median from an individual
> trial, and do not report a ratio** — as a ratio it runs 0.2347 to 0.9998, and the 5 lowest are
> all `wg-g4b-2026-08-17T19-50-43`, whose 8 trials the API refused in under 2 seconds each. That
> range measures trial length, not the two clocks.

**The self-report is at two addresses, one per timing script**, so the producer reports which
one each record used rather than guessing. **The denominator is the writing script's own output,
not a task class**: `wholegame.py` wrote the 91 whole-game records and the 1 scene record
alike.

| address | written by | paired |
|---|---|---|
| `trials/<tid>.json` -> `agent.duration_ms` | `runner.py`, the retired spec-change suite | 71 of its 71 |
| `artifacts/<tid>/agent_result.json` -> `duration_ms` | `wholegame.py`, which stores the CLI's whole result object and lifts no duration out of it | 86 of its 92 |

**163 stored records, 157 paired, 6 with no self-report.**

**The 6 records with no self-report are explained, not a gap.** 4 are
`archive-arena2d-wg-audio48`'s wedged arena trials, whose `agent_result.json` is an empty
object; 1 is the prime-agent probe, whose CLI reports no such field at all; 1 is the scene
trial, killed externally before any result object was written. **Every trial whose agent
process terminated and reported carries both clocks.**

## THE FIRST SCENE EVER BUILT AND GRADED — `wg-scene-s1ts-2026-08-25`. INTERRUPTED, and NOT a submission

| | |
|---|---|
| what | 1 cell, `s1_parallax__ts__t0`, the ts starter, the rendered `s1_parallax` prompt. The first time anything in this project launched a scene |
| how it ended | **killed from outside at 3599s** by the session's background-task manager, mid-agent-turn — the transcript's last entry is `[Request interrupted by user]`. `terminal_reason` is **`harness_kill_external`**, a value outside the harness's own enumeration, because nothing in the trial ended it |
| resource | **not reconstructable.** `num_turns` and the token totals come off the CLI's terminal result event, which never arrived, so all of them and `cost_usd` are `null`. The transcript alone gives 198 assistant messages and 137 tool-use blocks, recorded in a field of their own as a scale rather than as the harness's counters |
| what was salvaged | the work tree survived the kill, so the submission was captured by hand — `diff.patch`, `diff.stat`, `status.txt`, `tree.txt`, `submission.tar.gz`, 24 files changed, all four capture exits 0 |
| tier 1 | **GATE FAIL, 4 of 9** as graded on the day: `verify.green`, `lint.clean`, `tests.green`, `render.nonempty`. Re-graded after the `tasks/163` repair it is **GATE FAIL, 3 of 9** — `render.nonempty` moves FAIL to PASS and the other 3 are the interruption. The verdict does not move |
| tier 2 | `scene_probe`, **5 of 6 scored = 0.833** as graded on the day; **6 of 7 = 0.857** after the `tasks/162` repair; **6 of 6 = 1.000** after `tasks/164`, which returned `layers.image_parallax` to `scored=False`, and unchanged at 6 of 6 after `tasks/174`. The stored `playbot.json` holds the first, this table holds all 4, and none is a completed trial |
| evaluate | 58s for the whole grading, tier 1 plus the probe's 3 traces and 3 films |

**Never pool this record with anything.** It is not `completed`, it is one cell, and `wholegame.py
report` already excludes it from every aggregate — the run prints `0 aggregated, 1 not completed`.
Its value is entirely in what the instrument did on first contact.

### What first contact found, and the headline is a FALSE NEGATIVE — since REPAIRED

**`layers.depth_ordered` failed, and the failure was the criterion's.** It computed
`abs(offset_last - offset_first)` per layer and asked whether that decreases with declared depth.
The submission reports `offset` wrapped into `[0, span)` — which `eval/SCENES.md` has now decided
is contracted, since the layer declares the `span` that converts one encoding into the other — so
what the criterion read was a modular residue. The evidence was decisive and is a property of the
numbers rather than a reading of the source: **all 7 layers returned a value below their own
declared span**, and 37 `wrap` events fired in the same trace.

| layer | declared depth | span | what it read | what the layer moved |
|---|---|---|---|---|
| road | 0 | 240 | 120.1 | 5160.1 |
| verge | 0.6 | 340 | 165.1 | 3225.1 |
| grove | 1.5 | 440 | 304.0 | 2064.0 |
| ridge | 4 | 400 | 232.0 | 1032.0 |
| range | 9 | 480 | 36.0 | 516.0 |
| clouds | 20 | 900 | 245.7 | 245.7 |
| sky | 60 | 1800 | 84.6 | 84.6 |

The right-hand column is the same trace unwrapped against each layer's own `span`, and it is
**strictly decreasing with depth by a factor of 1.56–2.90 at every step** — a scene whose layers
were ordered perfectly, scored FALSE. The submission's own convention agreed with the criterion's
all along — `layerFactor(depth) = 1/(1+depth)`, larger depth scrolling slower — so a
sign-convention reading never rescued the result either.

**A mutant could not have found this.** Only a submission that wraps could, which is rule 15 and
the shape of (#46), and it took the first real one. `tasks/162` carries the repair: `_walk`
unwraps the per-tick series, and `scene_mutants.py` gained the variant that was missing — the
reference scene reporting the other encoding, drawing the identical picture.

### The re-grade, and it moved a second criterion

    tar -xzf <run>/artifacts/s1_parallax__ts__t0/submission.tar.gz -C <tree>
    pnpm install --frozen-lockfile && pnpm exec playwright install chromium
    python3 eval/judge/scene_probe.py s1_parallax <tree>

| criterion | as graded | after `tasks/162` | after `tasks/164` | after `tasks/174` | why |
|---|---|---|---|---|---|
| `layers.depth_ordered` | FAIL scored | **PASS scored** | PASS scored | PASS scored | `_walk` unwraps the per-tick series |
| `layers.image_parallax` | `scored=False` | FAIL scored | **`scored=False`** | `scored=False`, true reason | the `162` FAIL was never trustworthy — below |
| everything else | — | unchanged | unchanged | unchanged | |

**The `layers.image_parallax` FAIL stood for 2 days and was never quotable.** The `162` repair also
fixed the offset change `_measure_shifts` hands the reliability filter, which promoted the road
band from unreadable to readable and let the criterion establish itself on 3 bands. It should not
have, and `tasks/164` establishes why in the band's own numbers: the road crosses **1.66–2.25 spans
between two captured frames**, so what the frames show is a residue of its repeat length and not a
rate. It passed `_reliable` on **8 of 8 pairs** only because that filter's agreement slack was a
floor **in ratio units** — 0.15 against a median ratio of −0.053, and 0.15 of this band's reported
offsets is ±60 to ±81 pixels inside a ±89px search window, so nearly every answer the estimator was
capable of returning agreed with every other. The 2 bands it was then
compared against, clouds and sky, move 19–26 and 6.5–8.8 reported units per captured pair and read
**0px on 11 of 11 and 9 of 11 pairs** — a sub-pixel band and a stationary one are the same reading.

`_reliable` now drops a pair its layer's own span cannot resolve, and measures agreement in pixels.
On this submission that leaves **2 of 7 layers readable**, below `MIN_LAYERS`, so the criterion is
back to `scored=False` — the verdict it had on the day. What each band did, re-measured:

| band | declared depth | span | spans crossed per captured pair | readable |
|---|---|---|---|---|
| road | 0 | 240 | 1.66–2.25 | no — 8 of 8 pairs unresolvable |
| verge | 0.6 | 340 | 0.76–0.99 | no — 6 of 6 pairs unresolvable |
| grove | 1.5 | 440 | 0.46–0.48 | no — only 2 pairs clear the confidence floor |
| ridge | 4 | 400 | 0.24–0.26 | no — only 2 pairs |
| range | 9 | 480 | 0.10 | no — only 1 pair |
| clouds | 20 | 900 | 0.02–0.03 | yes, 11 pairs, all 0px |
| sky | 60 | 1800 | 0.00 | yes, 9 pairs, all 0px |

**The bands were reading each other, and `tasks/174` found why.** The per-pair grid shows it
plainly: at frame pair 4 all 5 of range, ridge, grove, verge and road answer −9px, and at pairs
1, 3, 5 and 10 four of them answer −46, −19, −66 and +8. Five bands at five declared depths cannot
all have moved the same distance.

The cause is not the estimator. **A declared band is not a region of the frame that belongs to one
layer.** After removing the rows any other declared band covers, 6 of the 7 have fewer than the
10 rows a profile averages, and 5 of those 6 have 0.

| band | declared band, as frame fractions | rows of its own, of 400 |
|---|---|---|
| sky | 0.000–0.460 | 3 of 184 |
| clouds | 0.008–0.408 | 0 of 160 |
| range | 0.284–0.468 | 0 of 74 |
| ridge | 0.344–0.476 | 0 of 53 |
| grove | 0.292–0.492 | 0 of 80 |
| verge | 0.308–0.692 | 0 of 153 |
| road | 0.460–1.000 | 124 of 216 |

Every threshold in the estimator was set against `judge/fixtures/ref_parallax`, whose 4 bands
**tile** the frame and overlap nowhere. That is a choice its author made, not something the
contract asks for, and this submission — which declares its layers at their true screen extents,
sky from the top of the frame down to the horizon and the rest drawn inside that — is the ordinary
case. `eval/SCENES.md` carries the decision and `tasks/174` the repair: a layer is read only from
rows no other declared band contains, and one left too few is refused by name.

**The re-grade after `tasks/174` moves no verdict on this trial** — tier 2 stays at 6 of 6 = 1.000
and `layers.image_parallax` stays `scored=False`. What moves is the recorded reason, which was
false: the criterion used to say *"the bands carry too little horizontal structure, or too much of
one that does not move"* about bands that carry plenty of it, belonging to other layers.

### 2 of 8 criteria could not be set up at all

`layers.image_parallax` and `loop.seamless` came back `scored=False`: the image-side shift
estimator read **only 2 of 7 declared layers** after `tasks/164`, and **0 of 7** after `tasks/174`
withdrew the 2 whose readings belonged to their neighbours. `scene_probe.py`'s docstring predicted
the direction — *"expect the rate to be worse on a submission that fills its foreground"* — and
this submission's mean ink coverage is **0.966**. So `measured_twice` came back as 2 of the 3
criteria designed to have both halves.

**`loop.seamless` is `scored=False` under all 4 gradings.** It needs 1 band that both wrapped
between two captured frames and can be read there. The road wraps on **every one of the 11
captured pairs** — so it has no away-from-the-wrap
baseline even before its pairs are dropped as unresolvable — and the 2 bands that were readable
then, sky and clouds, never wrap at all. 12 frames over 660 ticks cannot see this scene's seam.

### `render.nonempty` was a game criterion applied to a scene — SINCE REPAIRED

Tier 1 failed it at **0.966 against a window of 0.001–0.85**. That window's ceiling was
calibrated on games, which draw a subject against a background; a scene that fills the frame
with sky, road and scenery exceeds it by drawing what it was asked to draw. Same shape as the
audio criteria, which `tasks/156` had already stopped asking of a scene.

`tasks/163` made the window per task class — a scene gets the floor and no ceiling — and re-graded
this trial offline from its stored frames:

    python3 eval/judge/ink_window_control.py --runs-root <main checkout>/eval/runs

| | as graded | re-graded |
|---|---|---|
| `render.nonempty` | FAIL (0.966 against 0.001–0.85) | **PASS** (0.966 against the floor 0.001, no ceiling) |
| gate | FAIL, 4 of 9 | **FAIL, 3 of 9** |

**The gate verdict does not move, and that is the result rather than a disappointment.** The
other 3 failures — `verify.green`, `lint.clean` and `tests.green` — come from the interruption,
not from the criterion. The stored `programmatic.json` still holds the FAIL; this table holds both,
and the trial is not `completed` either way.

**Since `tasks/168` the ceiling is gone for games as well, so this re-grade no longer depends on
the task class.** The section *`render.nonempty` lost its ink ceiling* holds what the ceiling did
over the 69 stored submissions, and the offline re-grade of the one game it refused.

**`verify.green`, `lint.clean` and `tests.green` are the interruption, not the submission.** 118
of 119 of its own tests pass and the lint finding is `'previous' is never reassigned. Use
'const'` — the agent was killed mid-polish, adjusting wheel proportions, with the gate red as it
always is between edits.

### Wall clock, and the figure is a FLOOR

Build **≥ 3599 s** — the kill landed at 3599 s with the cell still working, so that is what it
had used and not what it needed. **Stated in seconds because that is the measurement**: 3599 s is
59.98 min, and writing "≥ 60 min" rounds past the only evidence there is. Evaluation **58 s**,
complete.

**One cell is measured, so a matrix figure is CONDITIONAL and is written that way.** Only
`s1_parallax × ts × t0` has a lower bound; the other 3 stacks and the second scene are unmeasured,
and ts is the cheapest stack on the game table. *If* no other cell is cheaper, a 2-scene ×
4-stack × 2-trial matrix has a build floor of **≥ 57 584 s serial** and **≥ 14 396 s at
parallelism 4**. In seconds because 14 396 s is 3.999 h and "≥ 4.0 h" rounds above it — the same
error one unit down. **The condition is the load-bearing part**: this is 16 × one observation, not
a measurement of 16 cells.
`wholegame.py plan --scenes …` prints this beside the cost table, which is scaled from game
trials and says nothing about a scene.

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
- **14 of the 68 trials stored on the day the regime changed would move** if re-scored — 5 upward
  by 0.0221-0.0443, 9 downward by up to **0.2273** (`wg-matrix-2026-08-13`'s
  `g3_arena__unity__t0` and `g3_arena__unity__t1`, which the constant 0.31 was cushioning). That
  is a count of that date's corpus, not a live one.
  **They were not re-scored.** Nothing in `eval/runs/**` was rewritten for this change.
- **Never average a stored `overall` with a new one.** `wholegame.py report` marks pre-gate rows
  `w` in a `regime` column and refuses to pass over a mixed run silently;
  `judge/regrade_wholegame.py` will not rewrite a pre-gate record without
  `--accept-regime-change`, because converting part of a run leaves a directory half in each
  regime with nothing on disk saying which trial is which.

**Re-scoring a stored run into the gate regime is allowed, and it must be recorded here** — the
run row gains the date and the flag, because after it the run's numbers no longer match anything
published about it before. Nothing has been re-scored so far.

## THE CODE JUDGE WAS TOLD ITS PACK MIGHT BE TRUNCATED WHEN IT WAS NOT — 2026-08-23

A grader-side boundary, in the same place as the fifth above and deliberately **not given an
ordinal**: regime ordinals are one of the four hand-allocated namespaces in this repository and
every one of them has collided, twice on a single day (see the twelfth break below). It sits
beside the fifth. It is not in the builds and not in the scores, but in **what the judge was told
before it read anything**.

`field.EVIDENCE_BLURB["code"]` carried this sentence, verbatim, in every brief handed to a
code-reading judge:

> NOTE: the pack is filled until a size budget runs out, so it may not contain every file the
> author wrote - judge what is here and do not infer that an absent concern was neglected.

**The character budget was removed on 2026-08-22 (#69)** and `files_dropped_for_length` has been
0 by construction ever since, asserted by `field.pack_completeness`. The sentence was a constant,
not a function of the pack, so nothing made it move when the mechanism it described was deleted.

**The direction is the damaging one.** It does not overstate the evidence — it understates it. A
judge told the pack may be a subset will discount an absence that is in fact complete, which is
the opposite of the caution the sentence was written to induce, and absence is most of what a code
judge has to work with.

**Which rounds read it — measured, not assumed.** The producer, and do not quote these from
memory:

```
python3 eval/judge/blurb_selftest.py --stored-rounds <main checkout>/eval/runs
```

It rebuilds each round's brief from the aspect, game and geometry the round itself recorded, and
compares the hash against its stored `provenance.brief_sha256`. It infers nothing from a date. It
also prints **where** each counted round is and **what pack state** it was told about, because
those are the claims the prose beside a census makes and the ones that go stale first: three rows
of this table were overtaken by four later rounds while the producer sat printed directly above
them, and the population sentences beside them were true of a population that had grown (task 132).

| | n | the population it counts |
|---|---|---|
| stored judge rounds in `eval/runs/**` | 97 | every JSON record carrying an `aspect` and an `order_seed`, at any depth below the root |
| of those, code-seeing (`idiomatic`, `architecture`) | 40 | `provenance.sees` contains `code` — or, for a round stored before `provenance` existed, its aspect does |
| code-seeing rounds carrying a `provenance.brief_sha256` | **14** | 10 in `wg-aspect-reliability`, 4 in `wg-g4c-2026-08-21T02-26-46/judge-blind-2026-08-23`; every one `knowingly_truncated: false` |
| the other code-seeing rounds | **26 — no brief hash stored, permanently unassessable**, not "clean" | 14 under `wg-funframes-crossgame`, 8 under `wg-tetris-judge-2026-08-17`, 4 under `wg-g4c-capgate` — all three are wrappers, and the producer splits each into the sub-directories that really hold the rounds |

**The 14 fall on both sides of this boundary, and which side is an identity rather than a date.**

| directory | aspect | n | brief chars, stored → rebuilt here | reads |
|---|---|---|---|---|
| `wg-aspect-reliability` | `architecture` | 5 | 3536 → 3576 | `moved` |
| `wg-aspect-reliability` | `idiomatic` | 5 | 3928 → 4000 | `moved` |
| `wg-g4c-2026-08-21T02-26-46/judge-blind-2026-08-23` | `architecture` | 2 | 3576 → 3576 | `same` |
| `wg-g4c-2026-08-21T02-26-46/judge-blind-2026-08-23` | `idiomatic` | 2 | 4000 → 4000 | `same` |

**`moved` is the expected reading here and not a defect** — the brief was changed on purpose, so a
round that read the old one cannot match the new. What makes the 10 proof rather than inference is
that the old brief rebuilds as well: check out the commit before the repair, `bc9fb52~1`, and
`field._brief(aspects.ASPECTS[aid], "g4_platformer", None)` returns `6a94883e3dbe0eb2` at 3536
characters for `architecture` and `6fd7554b71a03f5e` at 3928 for `idiomatic` — the hashes and the
lengths those 10 rounds stored. They demonstrably read the sentence.

The 4 `same` rounds are the blind judge-field sweep held in that run's `judge-blind-2026-08-23/`,
and their hashes are the repaired brief's, so they demonstrably read the repaired text — a
complete pack told it is complete. They are the only stored code rounds that were told the truth,
which is why this section's claim is about the code judge and not about every round on disk.

The 26 predate `provenance`, and nothing on disk says what brief they were shown. Read them as
unmeasurable, the same as the 26 rounds with no `files_opened` log in #83.

**What changed, and what it costs.** The claim is now a function of the pack —
`field.COMPLETENESS_NOTE`, selected by `knowingly_truncated`, used by **both** judge-facing texts
(`BRIEF.md` and the sampling skill written into every pack). The pack skill had the same defect
pointing the other way: it asserted *"Every submission here is COMPLETE"* unconditionally, so a
field built on purpose with `--allow-truncated` would have been handed a skill and a brief that
contradicted each other.

**This moves the brief, so rounds either side are not strictly comparable** — the same shape as
the `FRAMES_BLIND_SPOT` paragraph above. **Rule 8 says enumerate what differs from the artifacts
rather than from what the edit intended**, so the producer rebuilds *every* hashed round, not
only the code ones. Over the 34 rounds that carry a hash:

| aspect | n | brief chars, stored → this checkout | moved by this change? |
|---|---|---|---|
| `architecture` | 7 | 3536 → 3576 for 5 rounds, 3576 → 3576 for 2 | **yes**, for the 5 stored before it |
| `idiomatic` | 7 | 3928 → 4000 for 5 rounds, 4000 → 4000 for 2 | **yes**, for the 5 stored before it |
| `audio` | 5 | 3459 → 3459, byte-identical | no |
| `fun` | 5 | 3821 → 4759 | **no** — the same 938 characters pre-repair; it is the `FRAMES_BLIND_SPOT` paragraph recorded above |
| `fun_frames` | 5 | 3275 → 4213 | **no** — as `fun` |
| `ux` | 5 | 3321 → 4259 | **no** — as `fun` |

Only the two code-seeing aspects moved for this reason, and the three frames aspects moved by
byte-identical amounts before and after the change, which is what makes the isolation a
measurement rather than an assertion. **The judge tier weighs 0.00, so no `overall` moves and
nothing was re-scored.**

**A second claim was wrong in the same constant and is repaired with it.** The brief told every
code judge to cite files as `` `sim/03.src` ``. Only `architecture` sets `blind_language`; under
`idiomatic` the packer keeps each file's **real** suffix, so half the code briefs named a path
shape no judge had. It cannot be repaired by printing the real suffix — one brief serves a field
of eight submissions from four stacks, and any real suffix names an arm — so the non-blind example
is suffix-free (`field.PACK_PATH_EXAMPLE`).

**The gate that now exists**: `python3 eval/judge/blurb_selftest.py`, unpiped. It builds real packs
in both completeness states and both blinding modes and asserts that every claim the judge-facing
text makes about the packer is true of the pack it accompanies.

## THE `claude -p` PROMPT TOLD EVERY NON-CODE JUDGE TO READ CODE — PRE-REGISTERED 2026-08-28

A grader-side boundary beside the 2026-08-23 one above, and deliberately **not given an
ordinal**, for the same reason recorded there. It sits in **the first text the judge reads**:
`claude -p` receives its prompt before the judge opens any pack file, and unlike `BRIEF.md` the
prompt is stored nowhere in the pack — it is the process argument, and no gate that walks a pack
directory can see it.

The pack-side half of this defect was repaired on 2026-08-23 with the `looked_at` map in
`field._brief`. The CLI prompt kept the hardcoded wording in both completeness states:
*"Read BRIEF.md, then read the code in A/ through H/"* — for every aspect, including the 6 whose
packs carry no code. A frames judge was told to read code by the first text it saw and to look at
every frame by the second.

**What changed.** `field.judge_prompt` is now keyed on the pack's `sees` through
`field.JUDGE_PROMPT_SEES` — `read the code`, `look at the frames`, `read the telemetry`,
`read the audio measurements` — joined with "and", the same keying `_brief`'s closing line uses.
For the 3 code-seeing aspects the rendered prompt is **byte-identical** to the pre-change text in
both completeness states (asserted against the old literals, 2026-08-28), so the boundary runs
through the non-code rounds only.

**Which stored rounds sit on the moved side.** The producer, and do not quote these from memory:

```
python3 eval/judge/prompt_capture_census.py --runs-root <main checkout>/eval/runs
```

| aspect | n | with a `files_opened` capture | key absent — unassessable | reads of un-carried evidence | malformed records | truncated targets |
|---|---|---|---|---|---|---|
| `audio` | 11 | 7 | 4 | **0** | 0 | 0 |
| `fun` | 11 | 7 | 4 | **0** | 0 | 0 |
| `fun_frames` | 22 | 16 | 6 | **0** | 0 | 0 |
| `ux` | 13 | 9 | 4 | **0** | 0 | 0 |
| total | 57 | 39 | 18 | **0** | 0 | 0 |

The classifier and every column of it are pinned on a fixture tree whose answers are written out
beside it (`prompt_capture_census.py --selftest`). Two rows discriminate the un-carried column: a
`.src` read inside a frames pack is counted un-carried, and a `.png` outside `frames/` lands in
`other` rather than being counted as a frames read. Two more pin the malformed column: a dict
where the list belongs, and a list holding a non-string. Each malformed shape is refused whole —
named `malformed`, never counted as null, never partially classified — and neither stops the
walk; the unit is the record. A target of exactly 200 characters is refused from classification
as well: the capture in `field.py` stores `str(target)[:200]`, so a stored target at that length
may have lost its tail — the filename — and classifying it would be a guess. Those count under
`truncated`, one per target, itemised in full, never as carried and never as a leak, while the
record's good targets still classify — a different unit from `malformed`, and the fixture holds
two truncated targets in one list to pin it.

**The defect is latent: 0 of the 39 captured non-code rounds read any evidence its pack did not
carry.** The captured rounds' reads name only their own bucket's files and `BRIEF.md` — the audio
rounds read their 8 `audio.json` files plus the brief, read directly off two of them as the
known-good rows. What the prompt told these judges to do and what they did diverged; nothing was
scored on the difference. The 18 others predate the `files_opened` capture (task 09,
2026-08-22) and are **permanently unassessable, not clean** — the #83 third value again.

**Why this is a pre-registration rather than a stored hash.** `provenance` hashes `BRIEF.md`
(`brief_sha256`) and the scene statement; it does not hash the prompt, because the prompt is the
process argument and lands on no disk the round stores. Which side of this boundary a stored
non-code round sits on is therefore carried by this dated section and by nothing in the round
itself — the same property that made the 2026-08-23 repair provable (a stored hash) is absent
here, and this entry is what stands in for it.

**What it costs.** The judge tier weighs 0.00, so no `overall` moves and nothing is re-scored.
The brief is untouched: the per-aspect same/moved table above still reproduces after this change,
and the non-code rows read `moved` for exactly the reasons already recorded there — not for this
one.

**The gate**: `python3 eval/judge/blurb_selftest.py`, check 3c — the prompt names exactly the
buckets the pack carries, per pack shape in both completeness states, over the whole aspect
registry, and on the argv `run_field` actually builds; with the pre-change hardcoded prompt, a
prompt naming no bucket, and a `run_field` that passes the pack to nothing, each pinned red.

## THE CAPTURE-GEOMETRY REFUSAL GATE NEVER EXISTED — corrected 2026-08-28, and the stored corpus measures clean against the property the path cannot see

From 2026-08-21 to 2026-08-28, `eval/judge/JUDGING.md` and `eval/tools/frame_parity.py`
described a refusing gate: `field.pack_parity` ran inside `build_pack` (it did not — no caller
at any committed revision) and refused a frames-reading aspect on a field with mixed capture
geometry (nothing refuses). `build_pack` measures each submission's geometry from its FIRST
frame, records it per blind label in the pack's `capture_geometry` mapping, and renders a note
into `BRIEF.md` when the sizes differ, stating that the variation is a presentation choice the
task left open. Why annotation is right here and was wrong in #62, and why refusing stays
rejected: `DECISIONS.md`, 2026-08-28. `pack_parity` is deleted (task 202).

**The measurement the correction rides on.** The property the first-frame read loses is a
submission holding frames of MORE THAN ONE SIZE — a mid-film capture change passes an inline
read as uniform. The producer, and do not quote these from memory:

```
python3 eval/tools/frame_parity.py --runs-root <main checkout>/eval/runs
```

Over the stored tree as of 2026-08-28: **67 submissions with frames across 7 run dirs, 804
frames, every one readable, and 0 submissions holding frames of more than one size.** The
corpus's 3 cross-submission divergences are uniform within themselves at a non-modal size, and
each is already recorded: 420x640 `g2_tetris3d__unity__t1` (`wg-matrix-2026-08-13`), 768x576
`g2_tetris3d__rust__t0` (`wg-audio48-2026-08-14`), 720x540 `g2_tetris3d__ts__t1`
(`wg-audio-2026-08-14`).

**The extraction was proved before the census was believed**, on rows whose answer was known in
advance: the two documented divergences come back divergent; the 804 frames match an
independent count of PNGs under `artifacts/*/eval/frames`; and the population agrees with task
182's record-based census — 69 records, 3 varied, 2 with no geometry because their own film
failed, which is 67 with frames — an instrument sharing no code with this one. The first
version of the walker keyed its population on directories NAMED `artifacts` and read 3147 of
Unity's `Library/artifacts` build-cache subdirectories as trial dirs; the population is now
keyed on the `eval/frames` layout, and the fixture carries both poison rows.

**What this does not establish.** The stored corpus is clean; no claim covers a future
submission, and the first-frame read stays a blind spot on the path — the tool is the way to
see past it, run before spending on a field whose filming this harness did not just do. The
fixture pins (`frame_parity.py --selftest`, in `gates.yml`) hold both directions: a mixed-size
submission is caught, an unreadable frame is a flag and never a clean bill, a wrapper run two
directories deep is found, a trial name shared by two intermediates of one run stays two rows
(the corpus key is the trial's full path relative to the root), and the first-frame read itself
is pinned as the defect the census exists to catch.

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

**Why it is declined, and the reason is not a price.** A starter edit is a regime boundary;
this would be the **fifteenth**, and it must land in all four arms in the same words with
`starter_parity.py` and `verify_blind.py` re-run. Because it breaks comparability, the
before-side cannot be an existing run: the most recent clean 8-cell field, `wg-g4c-2026-08-21`,
is **$421.00** of agent trials and sits behind four subsequent starter boundaries. So the
experiment is **2 fresh matrices** — days of wall clock and 2 matrices' worth of rate-limit
capacity, which is what is actually scarce (#159) — plus judge sweeps, to move a number that
`tasks/46` itself forbids reporting
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

`wg-audio48` is therefore now a **16-trial, two-game run**, and the reported tokval covers only
those 16 records. The arena tokval moved with the arena trials.

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

No agent trial was re-run and no tokval was generated. `bot_mutants.py`: 36 criteria pinned in
both directions, 2 variants, 3 session-lock controls, 0 expectations unmet, exit 0.
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
| `godot__t1` | 0.978 | 0.93 | 1.00 | `render.nonempty` — ink 0.881 vs a ceiling since retired. **Only the gate verdict was re-graded**, offline: PASS 14/14. The 0.978 and 0.93 in this row are as graded, under the pre-gate weighted scheme, and were not recomputed — see *`render.nonempty` lost its ink ceiling* |
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

> **"Clean" there means TRIAL-ID clean, and it is not the same as language-blind (#131).** The
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
>
> **⚠️ AN `architecture` ORDERING FROM THIS FIELD IS NOT LANGUAGE-BLIND (#131).** All 8 packs
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
> extensions**, whatever `neutralise` did or did not catch.
>
> **The same sentence is now true of the DIRECTORY names, for the same reason and with the same
> scope (task 95).** Every stored `architecture` round read a `CHANGED.txt` that was a verbatim
> `git diff --stat` of the real authored tree — `Assets/Sim/Grid.cs`, `crates/sim/src/world.rs`,
> `public/render/view.ts` — beside a directory whose every file had been renamed to
> `bucket/NN.src`. Rebuilding this run's field with the repaired packer takes it from **330
> arm-naming directory segments to 0**, with the other 199 files of the pack byte-identical, so
> the leak was entirely in the file the harness wrote. A round run from now on is blind on this
> channel; **no round already stored is.** The code-content half — 106 segments in the same
> rebuilt field — is open and its repair was declined with a measurement (`tasks/103`), so a new
> round is *more* blind than a stored one and is still not fully blind.

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
regime — refused under the harness since the seventh comparability break (2026-08-17,
`STARTER_NO_RAISE=1`), above — so whether 2.15x is a property of rust or of our gate is open,
and the number must not be quoted without it. It is also still **n=2 per cell**: what is
established is that the floor is far wider than the Aug-17 estimate, not that the stacks are
equal.

> ⚠️ **A number reported to the operator here was wrong and is corrected.** The rust agents were
> said to have "hit the refusal 5 and 3 times". They hit it **zero** times: `just run` was
> invoked 0 times in both rust trials, against 3/5/6 for ts/unity/godot. The count came from
> grepping transcripts for `STARTER_NO_RAISE`, which matched the agent **reading the justfile
> and `main.rs`** — both of which document the flag. Re-run against the refusal's actual stdout
> sentinel, and cross-checked against invocation counts, it is zero. *A matcher that counts
> mentions of a mechanism instead of firings of it will report the documentation as evidence*
> — #31's shape, in a measurement of a guard rather than in the guard.

**What the gate measures, corrected (FINDINGS #64).** The gate cost rust no refusal turns at
all: both agents read the justfile at record 17 of 1124 and 640, saw `run` was gated, and never
attempted it. What separates rust is not refusals but **how little feedback tooling it ran**:

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

## Specialist-judge calls — a separate ledger, because they consume account capacity too

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
> The 3 `g1_pong` calls are also the only judge rounds in this project with **no surviving
> artifact** — no `g1_pong__*__seed*.json` from 2026-08-16 exists anywhere. `python3
> judge/judge_ledger.py --tree runs/` reads 97 rounds over 12 directories and none of them is
> this field, so $13.16 is in this ledger and in no round file. Every other figure below is
> read from round files.
>
> **Task 04 did not recover them, and its 4 rounds are not these 3 calls.** It re-ran
> `idiomatic` alone — not `architecture` — on the stored `g1_pong` field as 4 ordered rounds
> under `wg-funframes-crossgame/pong/` for $17.66, and its own result is that the #53 pong row
> **reproduces as a RANKING and not as SCORES**: the ordering repeats exactly, every value
> lands ~0.6 lower. So those rounds are evidence about the ranking and recover neither the
> original calls nor their scores, and $13.16 stays unreadable.
>
> **This row defines the 3-call figure: $13.16, and its mean is $4.39.** Cents here round
> half-up and never truncate, so the mean is 13.16 / 3 = 4.386667 -> $4.39. `JUDGING.md`
> carried $13.15 and $4.38 until 2026-08-24 — withdrawn, `WR-g1pong-round1-13-15` — and that
> was a disagreement about the **sum**, not about rounding, because 13.15 / 3 rounds to 4.38
> just as cleanly. This table settles it without a preference: its `g2_tetris3d` rows sum to
> $33.63, which `judge_ledger.py` still re-derives to the cent from `pre/`, and
> $46.79 - $33.63 = $13.16 exactly, where $13.15 would need a day total of $46.78. That is
> coherence with a published total rather than a re-reading — $46.79 has no artifact either —
> but only $13.15 contradicts the table it was printed beside. The per-call range $2.82-$5.29
> discriminates neither.
>
> **$4.39 is a retrospective aggregate and nothing may be projected from it.** It averages
> `architecture` and `idiomatic` over 3 calls, and the rows above show what that hides: on
> `g2_tetris3d` a call costs $6.81 for `architecture` and $0.60 for `audio`, an 11x spread. So
> the mean is not a per-aspect rate, `judge_ledger.py` prints no per-call mean for that reason,
> and the 1 projection made from this one came out 1.84x low (below). **Price from a
> (game, aspect) row of this table**, and treat 2 calls as a lower bound rather than an
> estimate. `DECISIONS.md` holds the derivation and what would re-open it.

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
| `wg-g4c-2026-08-21T02-26-46/judge-blind-2026-08-23` | 4 | $27.68 | 27.68 |
| **all judge rounds on disk** | **97** | **$334.41** | |

> **These 97 rounds are 12 populations, not one.** They judge 4 different games with
> different aspect sets over packs from 10 KB to 3.3 MB, across the #95 re-pack boundary. The
> total is additive and safe because token counts add; a per-call mean over it is rule 4 and
> `judge_ledger.py` refuses to print one.
>
> **The right-hand column is not the field's figure and must never be read as one.** It is
> `charged_to_ceiling_usd` — what the last invocation generated, which is what the retired
> `--max-cost` ceiling was enforced against. A round already on disk contributes 0 on purpose so
> it cannot be counted twice, so on a **resumed** sweep the counter is smaller than the field
> figure by exactly the carried rounds. 5 directories here are resumes, $69.93 in total. It
> was stored under the name `measured_cost_usd`, and that name is why $21.05 reached print
> (FINDINGS #121). The ceiling it was enforced against no longer exists: `field_sweep.py` is
> bounded by `--max-rounds` and `--max-wall-min`, and writes both into the summary (#159).

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
>
> **Judge artifacts live in `runs/`, never in scratch.** Round 1 was written to a
> session-scoped directory under `/private/tmp` and moved out once it became the evidence for
> a finding. `field_sweep.assert_out_root_durable()` now refuses any ephemeral `--out`, pinned
> both directions — the trial-work-tree guard named a mechanism and did not cover the resource,
> which is any artifact a finding will cite (#45's shape, rule 6's form).

**The figure is per (game, aspect) and spans 13x** — $0.60 for an `audio` call, $8.08 for an
`architecture` call on the same game. It tracks pack size, not game difficulty, because what the
judge consumes is what it has to read. `build_pack` reports `evidence_counts` before a single
round runs; project from that.

2 projections made from the wrong basis, both recorded because both were acted on:

- 3 `g1_pong` calls (mean $4.39) projected a 5-aspect `--max-runs 6` sweep at ~$131; the
  first `g2_tetris3d` call measured **$8.08** and re-projected it at **~$256**, past the ceiling
  it was authorised under — a ceiling since retired, because it was denominated in a unit
  nobody is charged (#159);
- the same per-game mean averages a $0.60 aspect with an $8 one.

`--per-call-budget` was held at $12 throughout even though the measured figure never approached
it: it reaches the judge as `--max-budget-usd`, which is **visible to the callee and instructs
it** (FINDINGS #33), so changing it mid-sweep would make the rounds non-comparable. It is held at
12 for that reason alone and **no longer bounds the sweep** — see the comparability note on the
sweep bounds below.

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

**The hook itself is unchanged and wired identically in all four arms.**
`.claude/hooks/verify-gate.sh` is present in every starter and wired under `"Stop"` in every
`.claude/settings.json` — the four settings files are byte-identical — and `wholegame.py` passes
`--setting-sources project`, which loads them. So three arms have been running under a gate their
guide never mentioned. That is a difference between arms that nobody chose, and it is the reason
this is a repair rather than a wording change: the hook is **harness**, identical in all four
trees, not a stack-native fact like Bevy's API delta or Godot's headless limitation.

**Wired is not ran, and no stored artifact separates them — FINDINGS #130.** This section said
*"was already live in all four arms"* until 2026-08-23; that was inferred from the file being
present and wired, which is rule 2. A Stop hook that exits 0 leaves nothing behind anywhere, so
the exposure above is established for the **wiring** and unmeasured for the **running**.

Wording is stack-native, as `DECISIONS.md` requires; only the silence is removed. Unity's sentence
adds that each blocked attempt costs another batchmode editor launch; godot's adds that each one
opens the window its own guide already documents.

### What the stored trials can and cannot say about it

**Nothing, and the reason is that the outcome has no variance — not that the effect is small.
The measurement, its extraction control and its two live probe arms are FINDINGS #130.**

In the only population where the exposure is provable from artifacts rather than from today's
working tree — the 12 trials with a stored per-trial starter baseline that reached a stop — the
gate blocked **0 times in both arms**: 0 of 4 rust, 0 of 8 ts/unity/godot. Zero events in both
arms is a null with **n=0 outcomes**, not a measured no-difference.

**Do not read that as "the gate is dead", and do not read it as "the gate is working" either.**
#130 measured both directions live at the CLI version every stored transcript records: a blocking
Stop hook is visible in the transcript, and one that exits 0 leaves nothing anywhere. So "no
block" is equally consistent with *verify was green at every stop* and with *the hook did not
run*.

The one thing about the runs themselves that *is* established, and does not follow from #130:
each hook short-circuits on a per-stack warm guard, and none of those guards can have
short-circuited in `wg-g4c` — ts `node_modules`, unity `Library`, rust `CARGO_TARGET_DIR` and
`just` on `PATH` all held in the live work trees.

**What this ledger takes from it:** no before/after comparison across this break can be settled by
re-reading the stored trials, in either direction.

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

Task 80, FINDINGS #133. **No Godot `verify.green` result from before this date is comparable with
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

## ALL FOUR STOP HOOKS GAINED AN AUDIT TRAIL ON 2026-08-23 — an EIGHTEENTH comparability break

**Check the ordinal before citing it.** Fifteen and sixteen were allocated the same day by
sessions that could not see each other; this one was taken from `main` at the time of writing,
with several worktrees live. Cite the heading, not the number.

**What was wrong.** A Stop hook that exits 0 leaves no trace in the transcript, in
`agent_result.json`, or anywhere else — measured at CLI 2.1.220 with the harness's own flags in
two arms (`tasks/78`). A hook that BLOCKS writes a `user` entry with `isMeta: true` beginning
`"Stop hook feedback:"`; a hook that PASSES writes nothing. So across the whole stored archive,
19 transcripts carry a block and all 19 are dated 2026-08-11 or 2026-08-12, and that single
observation is equally consistent with *`just verify` was green at every stop* and with *the hook
never ran*. No stored artifact separates them. "The gate is live in all four arms" rested on the
file being present in the starter, which is `AGENTS.md` rule 2.

**The change.** `eval/starters/*/.claude/hooks/verify-gate.sh` in all four stacks now appends two
tab-separated lines per invocation — `invoked` with the project directory, then one of `pass`,
`block`, `skip` (with the guard that fired) or `no_project_dir` — to `$STARTER_HOOK_LOG`,
falling back to `$TMPDIR`. `eval/wholegame.py` sets that variable to
`runs/<run>/artifacts/<trial>/hook_log.tsv`, summarises it into `trials/<trial>.json` under
`stop_hook`, and records `leaked_into_tree` per trial.

**The log lands OUTSIDE the trial tree, and that is the whole difficulty.** The tree becomes the
graded diff, so a file written into the project directory would appear in `files_changed`,
`diff.stat`, `tree.txt` and `submission.tar.gz` — the shape of #106. `wholegame.hook_log_path`
refuses to launch a trial whose log address is inside the tree, and the per-trial
`leaked_into_tree` row asks the same question of the OUTCOME, because a hook is free to write
wherever it likes once it is running.

**`skip` is the value that did not exist before and matters most.** Every hook short-circuits on
a warm guard — `target/`, `node_modules/`, `Library/`, `just` on `PATH` — and a short-circuit
and a green gate were the same silence to everything downstream. Task 78 could establish only
that those four guards *held* in `wg-g4c`'s live work trees; it could not establish that the hook
ran at all.

**What it demonstrably does NOT change**, so an arm before and after is comparable on everything
graded — `judge/starter_parity.py --skip-tests`, all four stacks, exit 0, *no drift detected*:

| axis | before (task 78) | after |
|---|---|---|
| hash chain, seed 7, its own 400-input tape | 401 per stack | 401 per stack, rust ≡ godot, ts ≡ godot |
| `just --summary` recipe set | rust 19, ts 21, unity 20, godot 18 | unchanged |
| `AGENTS.md` | 2032 / 2267 / 2209 / 2273 words | unchanged — **no guide was edited** |
| `starter_parity.mechanism_findings` | Stop wired in 4, named in 4 | unchanged |
| shared launch discipline over 5 copies | `da9914ce2e54beaa` | unchanged |

**No `just` recipe reaches the hook.** `grep` over the four justfiles and `starters/_shared/` for
`verify-gate` and `STARTER_HOOK_LOG` returns nothing, which is why `just check` / `verify` /
`warm` cannot have moved: the two hits are an unrelated no-raise comment in each.

**The guides were deliberately NOT told about the log.** They are what a building agent reads; a
sentence saying its gate is being recorded is an observer effect on the thing being measured, and
it changes nothing an agent should do. The Stop hook itself is still named in all four guides
(the fifteenth break).

Gates re-run after the change:

| gate | result |
|---|---|
| `judge/verify_blind.py`, out-of-repo copies of all four | **BLIND**, 81 criterion ids, 4 trees, exit 0 — and **CONTAMINATED exit 1** with `layer.clears` planted in the edited hook itself, so the scanner was shown able to fail on this exact input |
| `judge/starter_parity.py --skip-tests` | exit 0, no drift on any measured axis |
| `judge/parity_selftest.py` | **60 expectations, 0 failed, exit 0** — its ts positive control really ran (67/67), the worktree's `node_modules` being a symlink to the main checkout's, whose `pnpm-lock.yaml` is byte-identical (`0a586958a7d4057fd06f25dee3c89804a270e3e4`) |
| `tools/starter_gate_control.py --skip-verify`, rust and ts | 4 measurements each, **0 FAILED**, exit 3 — 3 is the NOT-CHECKED status, here verify idempotence (skipped) and rust's absent scope repair, neither introduced by this change |
| `bash -n` on all four hooks | exit 0 |
| `tools/hook_audit_control.py` | **7 ok / 28 FAILED, exit 1 with the four hooks reverted; 39 ok / 0 FAILED, exit 0 after.** The 7 that pass in the red arm are its harness rows, which measure `wholegame.py` and were not reverted — a red direction in which everything fails is weaker evidence, not stronger |

**The live direction, which no offline control can supply.** Whether the CLI hands a custom
environment variable to a hook it spawns is a property of the `claude` binary. Two real sessions
with the harness's flags, `--live`: the log was written to the path set on the CLI's parent, one
invocation each, nothing new inside the project directory. Cost $0.045 for the run whose result
JSON was parsed; ~$0.09 for both. `CLAUDE_PROJECT_DIR` came through **resolved** —
`/private/var/...` where `/var/...` was passed — which matters only if something ever compares it
to an unresolved path.


## THE JUDGE SWEEP'S BOUND CHANGED ON 2026-08-23 — a NINETEENTH comparability break, and it changes no stored round

**Check the ordinal before citing it.** Fifteen and sixteen were allocated the same day by
sessions that could not see each other. Cite the heading, not the number.

**What was wrong.** `field_sweep.py` refused a call when `spent + --per-call-budget > --max-cost`,
defaults 12 and 60 — so a sweep truncated at about 48 of a **list-price valuation of tokens** on
an account where no money moves per token. A limit denominated in a unit that does not bind cannot
protect what is scarce, and when it fires it cuts real evidence short (FINDINGS #159).

**Did it ever fire? No — measured, not assumed.** No stored summary records the ceiling it ran
under, so the question was answered from what each sweep actually did: a truncated sweep is one
that did fewer rounds than it was configured for. Over all **12** stored summaries — `repeats`
against `--repeats`, `orders` against `games x aspects x orders`, `sequential` against its
configured pairs — **0 are short**. The extraction was pinned on two synthetic summaries whose
answer was stated in advance (2 runs of 5; 3 attempted of 4) and reports both as short, so the
zero is a reading and not a blind spot.

**The change.** `--max-cost` is deleted. `--max-rounds` and `--max-wall-min` replace it, both
optional because every mode is already finite by construction, and **both written into the summary
alongside `stopped_by`** — so the question above becomes a field to read rather than a
reconstruction. `eval/judge/sweep_bounds_control.py` pins it in both directions: the bounds stop a
sweep, a mutant that neuters `may_start` runs past them, and a variant reads the tokenised source
to assert no money quantity participates in any stop decision.

**What is deliberately NOT changed, and it is the reason this break is narrow.**
`--per-call-budget` still reaches each judge as `--max-budget-usd 12.0`. That flag is visible to
the callee and instructs it (FINDINGS #33), so removing it would change what every future judge
round is told and make it non-comparable with all **97** rounds on disk, which ran under 12.0.
That is a regime boundary worth a pre-registration and a paired control, not a side effect of a
relabelling. It no longer participates in any decision this sweep makes.

**So every stored round remains comparable with every round taken after this change**, on the
axes that were already comparable. What changed is what could stop a sweep, and nothing was ever
stopped.

## THE TIER-3 POOLED POPULATION CHANGED ON 2026-08-24 — a TWENTIETH comparability break, and it changes no stored round

**Check the ordinal before citing it.** Fifteen and sixteen were allocated the same day by
sessions that could not see each other. Cite the heading, not the number.

**No round moved. Every pooled figure over them did.** `idiomatic` has been barred from a
cross-stack ranking since #53 and has carried `Aspect.cross_stack_bar` since task 135, but
`field_ranks.py` kept pooling it into the between-stack figure — which *is* a cross-stack
ranking. `assert_poolable` now refuses a barred aspect exactly as it refuses a control
(`tasks/146`).

**A tier-3 separation figure quoted before 2026-08-24 is over a different population than one
quoted after**, so the two are not comparable, and the older one is not merely rounder — it is a
different quantity. Recomputed over the whole stored tree, unpiped:

| directory | before — **retired**, and stated here only to say what changed | after |
|---|---|---|
| `wg-tetris-judge-2026-08-17/pre` | 5 aspects, 10 rounds, `rank`/`pool` 1.9000 / 2.2750 — `WR-tier3-pool-pre` | 4 aspects, 8 rounds, **1.3125 / 2.5625** |
| `wg-tetris-judge-2026-08-17/post` | 5 aspects, 10 rounds, `rank`/`pool` 2.1000 / 1.9250 — `WR-tier3-pool-post` | 4 aspects, 8 rounds, **1.8750 / 2.0938** |
| `wg-aspect-reliability` | 5 aspects, 25 rounds, `score`/`pool` 0.4000 / 0.2400 | 4 aspects, 20 rounds, **0.5250 / 0.4000** |
| `wg-funframes-crossgame/arena` | 3 aspects, 8 rounds | 2 aspects, **4** rounds |
| `wg-funframes-crossgame/platformer` | 5 aspects, 10 rounds | 4 aspects, **8** rounds |
| `wg-g4c-.../judge-blind-2026-08-23` | 2 aspects, 4 rounds | 1 aspect, **2** rounds |
| `wg-funframes-crossgame/pong` | **1 aspect — `idiomatic` alone** | **UNMEASURABLE**, exit 1 |
| `wg-g4c-capgate/out/capped` | **1 aspect — `idiomatic` alone**, `rank`/`pool` 5.2500 / 1.7500 | **UNMEASURABLE**, exit 1 |
| `wg-g4c-capgate/out/uncapped` | **1 aspect — `idiomatic` alone** | **UNMEASURABLE**, exit 1 |

**3 of the 9 were the barred reading and nothing else**, printed as a four-row separation table
at exit 0. `capped` was the widest between-over-within the tool ever returned anywhere in the
stored tree: its between-stack range was **3 times** its within-stack gap. That was a ranking of
an aspect that may not be ranked. Those `before` figures are retired; the tool now answers
`UNMEASURABLE` on all 3 directories.

**The published result did not move; it got stronger.** On `wg-tetris-judge-2026-08-17`, **3 of
the 8** value/order readings flip, every one of them from *between exceeds within* to *no
separation*, and the maximum excess of between over within falls from **+22.6%** to **+14.3%**.
`README.md`'s tier-3 row states a null and quotes no figure, so it is unchanged.

## THE GAME TASK PROMPT CHANGED ON 2026-08-25 — a TWENTY-FIRST comparability break

**Check the ordinal before citing it.** Fifteen and sixteen were allocated the same day by
sessions that could not see each other. Cite the heading, not the number.

**One word left the game preamble's definition of done**, in `suites/wholegame_prompts.py`
`_preamble()`:

| | text |
|---|---|
| before | *looping background music, and a **distinct** sound effect for each of the events listed below* |
| after | *looping background music, and a sound effect for each of the events listed below* |

**Why:** the same prompt permitted the opposite 40 lines later. The audio-manifest section of
`_probe_section()` says *"Whether two events share a sound, and what the sounds are, is yours to
design"*, so a submission mapping three events to one clip satisfied the manifest contract and
failed the stated definition of done. `judge/` adjudicates for the manifest clause and against
the preamble — `audio.distinct` sets its floor at half the declared events *because the task
permits sharing*, `audio.manifest` asks for an entry per event and never for a distinct file,
`audio.triggered` asks only that each fired event have an audible cue, and the tier-3 `audio`
aspect prefers *"three well-chosen"* cues to *"five technically distinct clips that are all the
same bright square-wave blip"*. Nothing in `judge/` has ever scored one distinct sound per event
(`tasks/142`; found by review on PR 19, reviewable only because task 133 checked the rendered
prompts in).

**16 rendered prompts moved and no scene prompt did.** That was measured, not reasoned.
`python3 eval/tools/prompt_guard.py --diff eval/suites/rendered` exited 1 against the pre-edit
snapshot and named **16 of 24** files: 4 games x 4 stacks, 4 lines each. It named **0 of the 8**
scene prompts, because scenes render from `scene_prompts.py`'s own `_scene_preamble()`. The
snapshot is re-recorded in the same commit.

### What it invalidates, and what it does not

**Invalidated: pooling whole-game trials across this date on anything derived from the task
text.** The **91** stored whole-game trial records
(`python3 eval/tools/census.py`, population *stored trial records carrying a `game` field*, read
2026-08-25) were built from the old wording. A trial built after it was asked for something
weaker, and turns, cost and every audio score are downstream of what was asked.

**Not invalidated, and this is the larger half:**

- **No stored trial changes and no stored score changes.** No criterion, threshold or weight moved
  — `judge/audio.py` is untouched by this break, and the RUBRIC edit corrects a sentence that
  described the prompt, not a rule that scores one.
- **Re-grading a stored trial returns what it returned before.** This is a task-text boundary, not
  a grader-side one, so it is unlike the fifth and the nineteenth.
- **The scene suite is untouched**, and has no stored trials to be cross-regime with in any case.
- **The starters are untouched**, so every starter-keyed boundary above is unaffected.

**What it plausibly changes in a future run, stated as a prediction rather than a result:** less
agent effort spent synthesising one clip per event, and `audio.distinct` — already floored at half
the declared events — closer to its floor. Nothing here measures that; the first post-boundary run
is what would.

## THE AUDIO CRITERIA CHANGED ON 2026-08-25 — a TWENTY-SECOND comparability break, and it moves no stored verdict

**Check the ordinal before citing it.** Fifteen and sixteen were allocated the same day by
sessions that could not see each other. Cite the heading, not the number.

**Grader-side, unlike the twenty-first.** Two tier-1 criteria changed in `judge/audio.py`, and
tier 1 gates, so this is the kind of break that can move a stored gate outcome. It does not —
measured, below — but the instrument a future submission meets is not the one the stored ones met.

| | before | after |
|---|---|---|
| where the declared event list comes from | a hand-written `GAME_EVENTS` in `judge/audio.py` | read from `suites/wholegame_prompts.py`, the only place a task exists |
| `g3_arena` | **6** declared events | **9** — the transcription had lost `enemy_spawn`, `wall_graze`, `multiplier` |
| `g4_platformer` | **absent**, so `expected` was empty: `audio.manifest` could not fail, and `audio.distinct` floored on the submission's own clip count | **8** |
| a game with no declared events | scored, and passed | **refused** — all 5 fail, fail-closed |
| `audio.distinct`'s groups | counted over **every** `sfx` entry, while the floor came from the declared events | counted over the **declared events'** entries, the same set the floor comes from |

**Why the last row:** the two sets were purchasable apart. A Pong submission mapping all 5
declared events to one clip scored 1 group against a floor of 3 and failed; the same submission
plus 2 unique undeclared entries scored 3 and passed, on the exact failure the criterion exists to
catch (`tasks/152`, found by review on PR 27). An undeclared entry now counts for nothing in
either direction, and still does not fail `audio.manifest` — the prompt forbids no extra cue, and
failing one would be fail-closed.

### What it invalidates, and what it does not

**0 of 59 stored audio gradings move a verdict**, over **43** distinct submissions, with **0**
refusals — `python3 eval/judge/audio_regrade_census.py --runs-root <main checkout>/eval/runs`,
population *stored gradings carrying `programmatic.audio.applies`*, read 2026-08-25. The census
re-applies `audio.py`'s own `manifest_problems`, `distinct_floor` and `distinct_ok` to each stored
grading's recorded manifest and sound groups: it reruns no submission and decodes no audio, and
reconstructs the declared-event grouping from the stored `clips` and `distinct_sound_groups`. It
refuses rather than guesses where that reconstruction would not be exact.

**It IS an offline re-grading computation**, and calling it anything else would be false: it
applies current scoring to stored evidence and produces verdicts. What it is not is a re-grading
that **replaces** anything — it **writes nothing**, no stored record is rewritten, and it is the
rewriting that `eval/judge/AGENTS.md` reserves for its own decision. The distinction matters in
one direction only: a reader must not conclude that those rules do not apply here.

**The null is a fact about the corpus, and the corpus says why**, which is what separates it from
a broken extraction (rule 12). The same command reports **0** gradings whose manifest omits a
declared event and **0** carrying an undeclared `sfx` entry. Every submission that produced a
manifest at all shipped an entry for exactly the events its own prompt declares — 5 for Pong, 6
for Tetris, 9 for the arena, 8 for the platformer. **Neither hole was ever exercised**: every
"extra event" the old grader recorded was a real declared cue its transcription had lost, and no
submission ever shipped a junk entry. The remaining **2** gradings — `wg-arena3d`'s two Rust
trials — produced no manifest, failed all five before, and fail all five now.

**So no stored score, gate outcome or `overall` changes, and nothing above needs re-grading.**

**What is not comparable across this date** is what the criteria would say about work that
exercises either hole. A platformer submission omitting a declared cue passed `audio.manifest`
before this date and fails it after; an arena submission shipping 6 of its 9 cues did the same.
Both are hypothetical against the stored tree and neither is against a future run.

**The extraction was proven on a row whose answer was stated in advance** before the census was
believed: `wg-audio-2026-08-14T12-29-42/artifacts/g1_pong__godot__t0` — 5 declared events, 5
single-member groups, no extras, floor 3 — must be `PASS -> PASS` on both criteria, and is
(`--report <that report.json>`).

## THE ARENA AIM CONTRACT WAS WRITTEN DOWN ON 2026-08-25 — a TWENTY-THIRD comparability break, and it moves no stored verdict

**Check the ordinal before citing it.** Fifteen and sixteen were allocated the same day by
sessions that could not see each other. Cite the heading, not the number.

**`suites/wholegame_prompts.py` `_G3_INPUTS` gained a sentence.** The task said only *"the aim
fields describe a direction; only its orientation matters, not its length"*, and now adds what a
zero-length or absent aim vector does: the gun holds its last orientation, `fire` still fires
along it, and where it points before any aim has ever been given is the submission's choice.

**Why:** the case was unspecified and it is driven. Two honest submissions could read it
oppositely — *return the gun to +x*, or *no direction was chosen, so withhold the shot* — and
both were consistent with every word of the task and inconsistent with
`judge/fixtures/ref_arena/game.py`, which the play-bot's criteria were written against. Found by
review on PR 19.

**It is driven 4,636 times.** `python3 eval/judge/aim_contract_control.py`, population *every
tick the arena play-bot sends against the reference*: **7,540** ticks sent, **4,636** carrying a
zero or absent aim, **33** of those holding `fire` — all 33 from `_multiplier_falls`, which fires
through the gaps between waves with no live enemy to aim at. Nothing stores a per-tick trace, so
this is the only population there is: the 8 stored trials keep a prompt, a diff, frames and a
`playbot.json` of verdicts, and no record of what was sent.

### What it invalidates, and what it does not

**Invalidated: pooling `g3_arena` trials across this date on anything derived from the task
text.** The population is **8** — `wg-arena3d-2026-08-15T12-46-30`, the only run whose stored
prompts declare `aim_x` at all (the other **16** of the **24** stored `g3_arena` trials predate
the 2026-08-15 3D rewrite and have no aim fields). Counts read 2026-08-25 from
`python3 eval/tools/census.py`, and the split by `grep -l aim_x` over the stored `prompt.txt`
files.

**Not invalidated, and it is most of it:**

- **No stored score moves, and no criterion, threshold or weight changed.** `judge/` is untouched
  by the prompt edit; the reference already did what the sentence now says.
- **All 8 stored submissions already implement it.** Read from their stored source: every one
  holds the previous orientation on a zero aim — `AIM_DEADZONE`, `AIM_EPSILON`, `length_squared()
  > 0.001`, `aim != Vec3::ZERO`, `lengthSquared3(...) > 0`, `> 1e-6`, `LengthSquared > 0f`,
  `> 1e-6f`. **0 of 8** reset the gun and **0 of 8** withhold the shot. The wording was written
  to the behaviour the field had already converged on, not against it.
- **The free half is exercised and it is genuinely free.** **8 of 8** start the gun somewhere
  other than the reference's +x — `-z` in six, `Vec3.Forward` and `Vec3.UnitZ` in the two Unity
  trials. `aim_contract_control`'s `startz` arm moves the reference's starting orientation to
  `-z` and every criterion returns what it returned before, which is why the prompt leaves it
  open rather than pinning it.

**The defect was latent, and that is a measurement rather than a hope.** Driving the whole
play-bot against a reference patched to *return to +x*, and again against one patched to
*withhold the shot*, returns **the same verdict on all 22 criteria** in both cases. So no stored
score could have depended on the reading, and the exposure was to a future submission — one that
read the gap the other way and lost points for it. The control keeps both arms and goes red if a
criterion ever starts to discriminate them, at which point the question is whether that criterion
is legitimate now that the prompt specifies the case.

**The extraction was proven on rows whose answers were stated in advance** before the 4,636 was
believed (rule 12): `player.moves` opens the run with exactly **90** pure-movement ticks that
must read as zero-aim, and `aim.independent` sends **120** ticks aiming +x that must not. Both
are rows in the control.

## `render.nonempty` LOST ITS INK CEILING ON 2026-08-27 — a TWENTY-FOURTH comparability break, and one offline re-grade changes a derived GAME gate verdict

**Check the ordinal before citing it.** Fifteen and sixteen were allocated the same day by
sessions that could not see each other. Cite the heading, not the number.

`render.nonempty` scored mean ink coverage inside `0.001–0.85` for every task from this
repository's first commit until `tasks/163`, which removed the ceiling for **scenes** on
2026-08-26. `tasks/168` removes it for **every** task class and replaces it with a direct test.
**The criterion is now a floor of 0.001, plus a refusal of a frame set in which every frame is a
single colour.**

**The derivation is that `mean_ink` cannot carry a ceiling.** `ink_coverage` counts pixels
differing from **one** reference colour per frame — so the quantity is a property of the palette
rather than of how much was drawn:

| frames | measures | which half decides |
|---|---|---|
| solid white, magenta or black — "the render broke and filled the screen" | **0.0**, in any colour | the **floor** |
| a gradient with a subject drawn on it — a night platformer's sky | near 1.0 | neither; it passes |

**And the ceiling was not a blank-frame guard either.** 12 frames each holding one colour have
drawn nothing, and under the reference in force on this date — frame 0's mode applied to all 12 —
where they landed depended only on how the colours were *arranged* (`WR-ink-arrangement-0-91667`;
the next break took that dependence away and all 4 now read 0.0):

| 12 frames, each one colour | mean ink then, `WR-ink-arrangement-0-91667` | floor-only | old 0.001–0.85 |
|---|---|---|---|
| all one colour | 0.0 | FAIL | FAIL |
| frame 0, then 11 of another | 0.91667 | PASS | FAIL |
| alternating 2 colours | 0.5 | PASS | **PASS** |
| 6 of one, then 6 of another | 0.5 | PASS | **PASS** |

`0.001–0.85` admitted **2 of the 3** non-zero arrangements, so the bound was never what stood
between the grader and a blank render. `png.Image.is_flat` reads each frame against **its own**
mode and `analyse_frames` counts them as `flat_frames`; the criterion fails all 4 rows. **0 of the
67 stored frame sets contain a flat frame**, so the added half moves no stored verdict, and
`flat_frames` absent is a third value — a record written before this date is re-graded on the
floor alone and says so in its evidence.

Every number in both tables is a checked row in `eval/judge/ink_window_control.py`, so the derivation
goes red if `ink_coverage` ever changes rather than surviving as a paragraph.

**Every ink figure below is a frame-0 reading**, which is what the grader that wrote each record
computed and what each verdict was decided against. The break after this one moved the reference to
each frame's own mode; `--reference-shift` prints both readings for every stored set.

**Within the game class, the 68 game values are a continuum, not 2 populations.** The scene is the
69th stored submission and stays its own population — no aggregate crosses the task classes. The
split is **inferred**: `ink_window_control.py` prints `task_class` read from the record on 1 of the
69 and `_class_of`'s reading of the trial id on the other 68. The 6 highest are 0.679, 0.703, 0.736, 0.772, 0.828 and 0.881, every one of
them `g4_platformer` — the one game whose background scrolls across the whole frame — and the
largest gap among those 6 is 0.0555. **0.85 fell in a gap of 0.0536, between 2 trials of that same
game**, so what it separated was a **task**, not a quality. The 7th value down is `g3_arena__rust__t0` at 0.60285, 0.076 below the 6th.

**What the bounds had ever done**, from the producer, over the 69 stored submissions — the most
recent grading of each, from 85 on disk with 16 superseded and held out:

    python3 eval/judge/ink_window_control.py --runs-root <main checkout>/eval/runs

4 `render.nonempty` failures. The 2 **floor** firings are true positives: `wg-arena3d`'s rust
cells at **0 frames**, a fact `render.frames` reports in the same record. Among the 2 **ceiling**
firings: **0 true positives and 2 false negatives**, both submissions that drew what they were
asked to draw. Tier 1 GATES, so a false negative does not cost a fraction of a score — it stops a
correct submission being scored at all.

**THE ONE DERIVED GATE VERDICT THAT CHANGES.** The stored record is untouched and still holds the
FAIL; the right-hand column is an offline re-grade computed from the stored frames, and nothing
under `eval/runs/**` was rewritten:

| `wg-g4c` `g4_platformer__godot__t1` | as graded, and still stored | offline re-grade |
|---|---|---|
| `render.nonempty` | FAIL (0.881 against 0.001–0.85) | **PASS** (0.881 against the floor 0.001) |
| gate | FAIL, 1 of 14 — `render.nonempty` alone | **PASS, 14 of 14** |
| tier 2 | 1.000 | 1.000, unchanged |

It is the only gate verdict in the corpus this change re-grades. The scene's re-grade above is
unchanged by it: `s1_parallax__ts__t0` still fails 3 of 9 on `verify.green`, `lint.clean` and
`tests.green`.

**What does NOT move.** `judge/tier1_census.py` reads stored verdicts, so its `FLOOR-ONLY`
headline, its 0-reversed / 3-coarsened / 8-identical comparison and the gate decision they support
are untouched. Removing a tier-1 failure can only reduce tier-1 variance, so no group can gain a
`both_vary`.

**What re-opens it.** Re-open the ceiling decision only if `eval/judge/ink_window_control.py`
reports a ceiling firing that is a real defect. The frame set must contain no flat frames — every
frame drew something — and the play-bot or the scene probe must condemn the submission too. The
output recorded on 2026-08-27 holds 2 ceiling firings, and neither meets that test.

## `rally.counts` BECAME ALL-OR-NOTHING ON 2026-08-27 — a TWENTY-SIXTH comparability break, and no stored verdict can be re-read against it

`bot_pong._rally` returned `rose_on_hit > 0` — the rally counter had to rise on **one** paddle hit
of the drive. It now requires a rise on **every** non-scoring hit the drive can read, which is the
standard already used by `paddle.deflects`. The criterion's question did not change; the reading
of it did. `tasks/171`.

**A verdict written before 2026-08-27 is not comparable with one written on or after it**, and
unlike the twenty-fifth this break **cannot be checked against the stored corpus**. `python3
eval/judge/tier2_census.py --runs-root <checkout>/eval/runs` reads `rally.counts` at **25 gradings,
0 failures** before the change and the same after it — a stored verdict is a record, not a
re-derivation — and every one of the **50** stored evidence strings reads `rally counter
incremented on paddle hits (6 hits seen)`, the format that predates `tasks/159`. `grep -rl "rally
rose on" eval/runs/` returns **0** files, so the number the new reading needs was never written
down. Whether any of the 25 would fail it is answerable only by re-driving those submissions.

**What did not change.** The one-tick contract (`DECISIONS.md`, and `tasks/159`), the `rose_late`
diagnostic, and `rally.resets` beside it. The floor is **one countable hit**, not the six proposed
with the tightening, so a correct game with a short rally is not newly failed — pinned by the tape
row *a correct counter, one hit in the whole drive*, which passes `1 of 1`.

**Why it moved.** g1 defines `rally` as the number of consecutive paddle hits since the last point,
so a hit the counter skips makes a line publish a rally its own event history contradicts. Measured
on the reference before the change: a `ref_pong` counting only the left paddle's returns **PASSED**
with `rally rose on 3 of 6 paddle_hit ticks`. It is now a mutant, and it is red.

**What re-opens it.** A correct submission failing with `0 < rose_on_hit < countable`.

## `mean_ink` MOVED TO A PER-FRAME BACKGROUND ON 2026-08-27 — a TWENTY-FIFTH comparability break, and it moves no stored verdict

**Check the ordinal before citing it.** Fifteen and sixteen were allocated the same day by
sessions that could not see each other. Cite the heading, not the number.

`static.analyse_frames` took one background from **frame 0** and applied it to all 12 frames, so
`mean_ink` was departure from the first frame's palette. It now takes a background **per frame**,
and `mean_ink` is the fraction of a frame that is not its own background. `tasks/178`.

**A frame-0 reading, in any record written before 2026-08-27, is not comparable with a per-frame
reading, in any record written on or after it.** Nothing else about the criterion changed — the
floor is still 0.001, there is still no ceiling, and `flat_frames` is still counted — and **no
stored verdict moves**, because the lowest value in the corpus under either reference is 0.00811,
8x the floor.

**Why it moved.** A fixed reference cannot survive a submission changing its clear colour: every
pixel of a later frame then differs from it and the frame reads exactly **1.00000**. Over the
stored corpus that happened to **14 of 804 frames** in 3 sets. `g3_arena__rust__t0` flashes its
arena red at frame 5, and its last 7 frames each read 1.00000 against frame 0's mode while reading
0.04336 against their own — the same 4% of a frame those frames had been drawing all along. Under
the per-frame reference **0** of the 804 read 1.00000.

**And it was fail-open.** 12 frames of which frame 0 is uniform black and the other 11 uniform
white carrying a single 2x2 speck — 4 pixels of 256000 — read `mean_ink` **0.91665** and PASSED
`render.nonempty`, with `flat_frames` at 1 of 12 unable to see it either. Measured on the
pre-change code before it was changed; it now reads 0.00001 and fails.

**THE 10 STORED SETS WHOSE `mean_ink` MOVES.** Nothing under `eval/runs/**` was rewritten: each
record still holds its frame-0 reading, and the right-hand column is what the same PNGs read under
the reference in force from this date. The producer, which re-reads every stored PNG and refuses to
report a shift unless its frame-0 arm first reproduces all 67 stored values to the digit:

    python3 eval/judge/ink_window_control.py --runs-root <main checkout>/eval/runs --reference-shift

| submission | run | stored (frame 0) | per frame | move |
|---|---|---|---|---|
| `g3_arena__rust__t0` | `wg-matrix-2026-08-13` | 0.60285 | **0.04481** | −0.55804 |
| `g3_arena__ts__t0` | `wg-matrix-2026-08-13` | 0.51997 | **0.03886** | −0.48111 |
| `g4_platformer__godot__t1` | `wg-g4c-2026-08-21` | 0.88137 | **0.67869** | −0.20268 |
| `s1_parallax__ts__t0` | `wg-scene-s1ts-2026-08-25` | 0.96561 | **0.85042** | −0.11519 |
| `g3_arena__godot__t1` | `wg-arena3d-2026-08-15` | 0.39884 | **0.28533** | −0.11351 |
| `g4_platformer__godot__t0` | `wg-g4c-2026-08-21` | 0.67885 | **0.78194** | +0.10309 |
| `g3_arena__unity__t1` | `wg-arena3d-2026-08-15` | 0.18825 | **0.14218** | −0.04607 |
| `g3_arena__ts__t0` | `wg-arena3d-2026-08-15` | 0.23198 | **0.18738** | −0.04460 |
| `g3_arena__godot__t0` | `wg-arena3d-2026-08-15` | 0.39717 | **0.40062** | +0.00345 |
| `g3_arena__unity__t0` | `wg-arena3d-2026-08-15` | 0.14379 | **0.14601** | +0.00222 |

The other 57 sets read identically under both, because their clear colour never changes. The
population is `tier1_census`'s — 69 submissions, the most recent grading of each from 85 on disk,
of which **67** have readable frames on disk and 2 do not (`wg-arena3d`'s rust cells, at 0 frames).

**What the move does to the corpus shape**, over the **66** game sets with frames — the scene is
its own population and is never pooled with them. Under the frame-0 reference the 6 highest were
`g4_platformer` and the 7th and 8th were `g3_arena` submissions at 0.60285 and 0.51997, both of
them the saturation above rather than a property of the render. Under the per-frame reference the
**7 highest are all `g4_platformer`**, the one game whose background scrolls across the whole
frame, and the 8th is `g2_tetris3d__ts__t1` at 0.40621. The retired 0.85 ceiling would refuse 1 of
the 67 sets rather than 2, and the one it still refuses is the scene at 0.85042.

**What does NOT move.** No stored record, no stored verdict, no gate verdict, no tier-2 score.
`judge/tier1_census.py` reads stored verdicts and is untouched. The `wg-g4c
g4_platformer__godot__t1` re-grade recorded in the break above stands: it was decided by the
removal of the ceiling, and it passes the floor under either reference.

**What re-opens it.** A submission whose drawn subject reliably covers more of the frame than any
single background colour, so the per-frame mode tracks the subject. `--reference-shift` is the
producer to run: a set reading near 0 per frame and high against frame 0's, whose frames visibly
drew something, is the case this did not anticipate. Nothing in the 67 stored sets is one.

## THE END OF A GAME BECAME ONE SIGNAL ON 2026-08-27 — a TWENTY-SEVENTH comparability break, and it moves no stored verdict

**Both sides moved, which none of the breaks above did.** The task prompt gained a paragraph and
2 bots changed how they read a trace, and they are the same change: `state.game_over` is now the
authoritative end signal everywhere, and the `game_over` event announces it.

| where | before | after |
|---|---|---|
| `suites/wholegame_prompts.py` `_probe_section()` | the state field and the event were both listed, and nothing said which one *means* the game ended | 6 lines saying the field is the condition, the event is an announcement, and an announcement is not a state |
| `judge/bot_arena.py` `_death` | `flag is True or "game_over" in t.events` | the flag alone |
| `judge/bot_tetris3d.py` `_gameover_check` | the same disjunction, in **2** places — the post-drop scan and the no-falling-piece branch | the flag alone |
| `judge/probe.py` `end_condition_holds` | scored the flag whatever the caller located the end with | refuses a session whose flag is not `True` at the hand-over, and says so |

**Why:** the bots located the end with one signal and scored it with the other. `bot_pong` and
`bot_platformer` never read the event, so 2 of 4 already had the resolution this break adopts.

**What it fixes, measured on both fixtures before and after** (`judge/bot_mutants.py`, the two
`the end is announced ... state` subjects):

| subject | before | after |
|---|---|---|
| a **correct** game that announces the end and enters it 6 ticks later | **FAIL** — `BROKE at tick 537: game_over went False with nothing pressed` (arena), `BROKE at tick 54: …` (tetris) | **PASS** |
| a **broken** game that announces the end and never enters it | FAIL, with that same sentence about a flag that had never been True | FAIL — `the player never died in 9001 idle ticks (hp 0.0)`, `stacked into one corner for 169 ticks without the game ending; game_over=False` |
| each reference, untouched | PASS | PASS |

The false negative is the first row: a criterion that could not pass a correct game, which only a
variant asks about (`AGENTS.md` rule 15). The second row is what must still fail, and does.

**16 rendered prompts carry the paragraph and no scene prompt does**, measured rather than
reasoned, and re-measurable at any commit without one:

    grep -l 'A \*\*state field\*\* and an \*\*event\*\*' eval/suites/rendered/*.txt | wc -l   # 16
    ls eval/suites/rendered/*.txt | wc -l                                             # 24

4 games x 4 stacks. The 8 scene prompts render from `scene_prompts.py`'s own preamble and never
reach `_probe_section()`. `python3 eval/tools/prompt_guard.py --diff eval/suites/rendered` exited
1 against the pre-edit snapshot and named the same 16; the snapshot is re-recorded in the same
commit and `eval/tools/prompt_guard_control.py` is green on all 25 rows.

### What it invalidates, and what it does not

**Invalidated: pooling whole-game trials across this date on anything derived from the task text.**
The **91** stored whole-game trial records (`python3 eval/tools/census.py --runs-dir <main
checkout>/eval/runs`, population *stored trial records carrying a `game` field*, read 2026-08-27)
were built from a prompt that did not say which signal ends a game.

**Not invalidated:**

- **No stored verdict moves.** `python3 eval/judge/tier2_census.py --runs-root <main
  checkout>/eval/runs` is byte-identical before and after — **11 groups, 5 saturated, 10 selective
  failures over the whole corpus, VERDICT: SATURATED**. It reads stored verdicts, and re-grading
  tier 2 means re-running a bot against a submission tree, which nothing here did.
- **Nothing under `eval/runs/**` was rewritten.**
- **No stored submission is known to carry the shape this repairs.** Whether one does is not
  answerable from the stored tree: a trace is not kept, so what any submission published on its
  end tick cannot be read back. The 2 fixtures are the evidence.
- **The starters are untouched**, so every starter-keyed boundary above is unaffected.
- **The scene suite is untouched.**

**What re-opens it.** A correct game whose state flag lags its `game_over` event by more than the
window a bot spends looking for the end — 9000 idle ticks on the arena, 60 placements on tetris.
Nothing constructed here comes close, and a game that never sets the flag is refused by design
rather than by a budget.


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
- A run's token valuation is the sum of `agent.cost_usd`. The key is `cost_usd`, **not**
  `total_cost_usd` — the latter is absent and reads as zero, which silently produces a 0.00 total.
- **Cross-check the record sum against the build logs.** If the log has more `[built]` lines than
  there are records, the difference is retried cells whose first attempt was overwritten, and the
  record sum understates what the run used.
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
