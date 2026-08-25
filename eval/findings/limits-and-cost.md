# Limits, cost, and comparability

`--max-budget-usd` is visible to the agent and instructs it; `--max-turns` is not.
Every cost figure is partly a measurement of the ceiling that was set.

> Index and the distilled rules: `../FINDINGS.md`


## 33. The spending cap is an INPUT to the agent, not an external kill

`wholegame.py` passes `--max-budget-usd 25` to every trial. It was reasoned about
throughout this project as a safety stop — something that acts *on* a run from outside,
like a timeout. That was never checked.

### The measurement

Three sessions, identical but for the flag, each asked to state its spending limit exactly
or reply `NONE`:

| launched with | answered |
|---|---|
| `--max-budget-usd 7.31` | `EXACT=7.31` |
| `--max-budget-usd 41.77` | `EXACT=41.77` |
| *(flag absent)* | `EXACT=NONE` |

Three-way discrimination, including a correct negative. The agent is told its budget.

### Why this matters more than the truncations it was noticed through

The cap was raised because trials were hitting it. But a visible cap does not merely stop
a run — **it is part of the prompt.** Two consequences follow, and the second is the one
that damages evidence:

1. **Runs with different caps are not comparable on any cost or effort metric**, because
   the agents were given different instructions. A cap change is a task change.

2. **The clustering under the ceiling IS pacing.** Measured across both cap regimes,
   completed trials only:

   | game | cap $25 | cap $48 | ratio |
   |---|---|---|---|
   | Pong | $21.02 (n=7) | $25.13 (n=8) | 1.20x |
   | Tetris | $23.20 (n=3) | **$35.66 (n=8)** | **1.54x** |

   Nearly doubling a number the agent is told, and never enforcing it, raised spend on
   Tetris by more than half. **The cap is visible AND acted on.**

   > ### ⚠️ THE MECHANISM STATED BELOW WAS WRONG, AND IT WAS PUBLISHED
   >
   > This entry originally read the 1.54x as **pacing**: agents spend up to what they are
   > told they have. That claim was acted on — it is why the cap was removed rather than
   > merely raised — and it is now contradicted in part. **The superseded reading is kept
   > here rather than deleted, because it was published.** See "#33, corrected" at the end
   > of this entry.

### I retracted this hypothesis once, on a null from the wrong game

After one calibration trial I withdrew the pacing claim: the same Pong cell cost $23.75
at a $48 cap against $21.63 at $25, a 1.13x move, and I called the null explanation the
winner. That retraction was wrong, and the reason it was wrong is the more useful part.

**Pong has no headroom.** It costs ~$21 whether the ceiling is $25 or $48; the task is
too small to expand into the space. So Pong cannot show a cap effect *whatever the truth
is* — a null there is uninformative by construction. Tetris, which costs $23 under a $25
ceiling and $36 under a $48 one, had room and showed it plainly.

> **I tested the effect on the one game least able to exhibit it, and read the resulting
> null as evidence of absence.** A null measured on a saturated instrument is not a null.

This is the same error as FINDINGS #21 wearing different clothes: validating a judge on
uncontested fixtures reports high reliability because agreement is cheap where the answer
is obvious. Here, measuring a budget effect on a task with no budget headroom reports no
effect because there is no room for one. **Choose the case with the most room to move
before concluding that nothing moves.**

### The consequence for every cost number in this project

**Every cost figure here is partly a measurement of the cap we set**, not purely of what
the task requires. The previous matrix's $11.30 / $19.49 / $13.62 per game, the stopped
run's $21-24, this run's $25-36 — each is the cost of that task *under that ceiling*.

Cross-run cost comparisons are valid only **within a cap regime**. Anyone benchmarking
agents under a budget flag is measuring a joint property of the task and the flag, and
the effect here is over 50% on a task with headroom. It was found by accident, while
trying to control cost rather than study it.

Note what the previous matrix looks like under this reading. At the same $25 cap the old
task cost $11.30/$19.49/$13.62 per game — 45–78% of budget, never binding. The new task
pushed spend up to where the ceiling is in view. **A cap only becomes an instruction when
the work grows into it**, which is why three matrices passed before anyone asked.

### What is not yet established

Whether spend *tracks* the cap. Visibility makes it possible; it does not prove it. The
disambiguating experiment is one trial in a cell already measured twice at the old cap
(`g1_pong`/`ts`: $20.19 and $23.07), re-run at $48:

* ~$21 again → the cap is not driving spend, the work simply costs $21, and a 24-trial
  relaunch is ~$570.
* ~$35–45 → spend tracks the budget it is given, a relaunch is ~$1,000, and **every
  cost figure this project has published is a measurement of its own cap** rather than of
  the task.

One trial to resolve a $500 question. `cmd_plan` has told anyone reading it to do exactly
this since before the first matrix: *"Run one trial of one game on one stack first and
re-run `plan` with the measured number before committing to the full matrix."*

### The general form

> **Every parameter you pass an agent for your own operational reasons may be visible to
> it, and anything visible is an instruction.** Timeouts, turn limits, budgets, retry
> counts, model names, deadline strings — check which of them reach the context before
> treating any of them as a property of the harness rather than of the task.

### #33, CORRECTED — the cap was truncating, not pacing, and "completed" does not mean finished

The disambiguating trial was run on 2026-08-15 under the standing configuration
(`--max-turns 1000`, no budget cap), and read from its record rather than from a log line:

```
g3_arena__rust__t0   $72.83   369 turns   118.3 min   completed   31 files changed
```

369 turns is **118 past the 250-turn limit** every prior trial ran under, and it finished
normally. The nearest prior datum, `g3_arena__rust__t1`, was cut off at 251 turns having spent
$35.75 of a stated $48 — it did not choose to stop, it was stopped.

**The claim that survives, and it is the important one:**

> **`terminal_reason: completed` means the agent ended its turn, not that the work was
> finished.** Under a binding limit those are different events and nothing in the record
> distinguishes them. Every capped figure this project has published may be a measurement of
> where trials were cut off rather than of what the task costs.

That reframes every cost number here. $11.30, $19.49, $13.62, $21.02, $23.20, $25.13, $35.66 —
each is *the cost of that task under that ceiling*, and now also *possibly the cost of the
work that fitted inside it*.

**What this trial does NOT establish, and saying so is the point.**

The comparison is confounded three ways at once, and the project's own rule
(`RUNS.md`: a task change is a comparability break) forbids reading it as a clean 2.04x:

| changed between the two trials | old | new |
|---|---|---|
| budget cap | $48, visible | **absent** |
| turn limit | 250 | **1000** |
| **the task itself** | 2D arena | **3D arena** — a volume, analog input on three axes, three enemy kinds, materialisation, a multiplier, gamepad and mouse, and stated on-screen requirements |
| trial index | t1 | t0 |

The 3D task is substantially more work than the 2D one; tier 2 alone went from 15 criteria to
22. **A doubling across a task change plus two limit changes cannot be attributed to the cap.**

There is also a specific reason to doubt that truncation explains the *Tetris* figure it is
being used to reinterpret: those trials came back `completed`, not `budget_exhausted`. A cap
that truncates should produce the latter. Trials that stop short of a ceiling they never hit
look more like pacing than truncation.

**Honest summary of what is and is not known:**

* **Established:** trials were being truncated — `max_turns` at 251 and `budget_exhausted` at
  $25.06 are direct evidence, no inference required.
* **Established:** the uncapped 3D arena task on rust costs **$72.83 / 369 turns / 118 min**,
  at **$0.1974 per turn**.
* **Not established:** whether the *completed* trials under a cap were paced or truncated. The
  calibration changed the task at the same moment as the limits, so it cannot separate them.
* **The experiment that would separate them** is one trial of an *unchanged* task — `g2_tetris3d`
  on any stack — under the no-cap configuration. If Tetris comes back near $23 it was paced; if
  it comes back near $45 it was truncated. One trial, and it settles a claim that currently
  reframes every cost figure in this repository.

This is the second time this hypothesis has moved on new evidence, and both moves were caused
by comparing across a boundary the project's own rules say not to cross. The first retraction
tested the effect on the game with no headroom (Pong). This correction rests on a trial where
the task changed too. **Change one thing.**

### And you cannot reason by analogy — the sibling flag behaves differently

`--max-turns` was tested the same way, immediately, on the assumption it would also be
visible:

| launched with | answered |
|---|---|
| `--max-turns 9` | `TURNS=NONE` |
| `--max-turns 137` | `TURNS=NONE` |
| *(flag absent)* | `TURNS=NONE` |

**It is not visible.** The turn limit is a genuine external kill; the budget is an
instruction. Two limits, passed side by side in the same `argv`, by the same harness, for
the same operational reason — and they differ in kind.

That is the part worth carrying elsewhere. Having found one visible parameter, the
temptation is to assume the class is visible and adjust for all of them; having found one
invisible one, the temptation is to assume the harness is clean. **Both are wrong, and
each flag has to be measured separately.** The test costs pennies and takes two minutes:
launch with two distinct values and a control, and ask the agent to report the value.

### The design consequence: the visible cap was buying almost nothing

Measured over the 10 completed trials of the stopped run: **$0.1336 per turn** (range
$0.1133–$0.1612), 163 turns on average against a 250-turn limit. So a trial that ran to
the **invisible** `--max-turns 250` would cost about **$33 at the mean rate and $40 at the
worst rate observed.**

A visible `--max-budget-usd 48` therefore almost never binds before the invisible turn cap
does. It adds an instruction to the agent's context and, in exchange, protects against
almost nothing the turn cap was not already bounding.

**There is no neutral value for a visible parameter.** Raising it does not remove the
instruction, it changes it — "you have $48" is as much an instruction as "you have $25".
The only setting that carries no instruction is *absent*, which the control in the table
above confirms reports as `NONE`. So the clean design is to omit the budget flag and let
the invisible turn limit bound the run, rather than to pick a bigger number.

Whether that matters in practice depends on whether spend actually tracks the stated
budget, which the calibration trial is measuring. But the asymmetry stands regardless: one
option adds an instruction and buys nothing, the other adds no instruction and buys the
same bound.

---


## 35. The invisible limit became the binding one, and nothing announced the inversion

`g3_arena__rust__t1`, 2026-08-15, under `--max-budget-usd 48` and `--max-turns 250`:

```
terminal_reason: max_turns   turns: 251   cost: $35.75   wall: 3991s
```

**$12.25 of its stated budget was unspent.** The trial was not stopped by the limit the run
was configured around; it was stopped by the one nobody had thought about since it was set.

### It was predicted, in this file, the day before

FINDINGS #33 closed with the arithmetic: at the measured $0.1336/turn, "a trial that ran to the
**invisible** `--max-turns 250` would cost about **$33 at the mean rate and $40 at the worst rate
observed**", and therefore "a visible `--max-budget-usd 48` almost never binds before the
invisible turn cap does."

Observed the next day: $35.75 at 251 turns, $0.1424/turn. The prediction was right, it was
written down, and the configuration was left in place anyway — the run was launched with a cap
chosen so it "should never bind", which is exactly the condition under which the *other* limit
governs.

### Why the inversion is the finding, not the truncation

At $25 the visible cap bound first and `budget_exhausted` was the population to watch. At $48 the
invisible turn limit binds first. **Nothing in the harness changed to cause this** — the task got
harder, spend per trial rose, and the crossover point (~370 turns / ~$48 at this rate) moved past
the configured turn limit. A run can therefore change which of its two limits governs without any
edit, any warning, or any difference in how it reports.

The consequence for evidence is specific: **a run governed by the invisible flag looks unbounded
to its agents.** They are told $48, they pace to $48, and they are cut off at $35 by something
they were never told about. That is not the same experiment as either "you have $35" or "you have
$48", and it is not a truncation that can be reasoned about from the budget the trial was given.

Standing configuration is now `--max-turns 1000` and **no budget cap** (`PROTOCOL.md`,
`DECISIONS.md`). The pair must be chosen together; setting either alone hands the binding role to
the other silently.

### `max_turns` is its own population, n=1

It is not `completed` and not `budget_exhausted`. Per rule 4, it is partitioned out of every
aggregate for `wg-audio48` and reported separately. One trial is not a rate.

### You cannot tell from `num_turns` whether the turn limit bound

Two records from the same run, same `--max-turns 250`:

| trial | num_turns | terminal_reason |
|---|---|---|
| `g2_tetris3d__godot__t0` | **265** | `completed` |
| `g3_arena__rust__t1` | **251** | `max_turns` |

A trial finished normally with *more* turns than the limit while another was cut off with fewer.
So `num_turns` in the output JSON is not the counter `--max-turns` applies to, and the
relationship between them is not established here. **Only `terminal_reason` says which limit
bound.** Do not infer it from the turn count, and do not convert a turn limit into a cost estimate
via `num_turns` without checking that the two count the same events — the $130 estimate for 1000
turns is derived from cost-per-`num_turns` and inherits this uncertainty.

---

## 63. A noise floor estimated from one cell was wrong by a factor of seven

`wg-g4c` is the first matrix to measure within-cell cost spread on all four stacks at once:
eight trials, all `completed`, one `terminal_reason`, $421.00.

| stack | low | high | spread | gap | mean |
|---|---|---|---|---|---|
| unity | $48.23 | $54.00 | 1.12x | $5.76 | $51.12 |
| ts | $40.88 | $55.05 | 1.35x | $14.18 | $47.97 |
| godot | $42.92 | $66.16 | 1.54x | $23.24 | $54.54 |
| rust | $36.16 | $77.60 | **2.15x** | $41.43 | $56.88 |
| **mean within-cell gap** | | | | **$21.15** | ← the floor |
| between-stack range | | | | **$8.91** | |

**The between-stack range is 42% of its own noise floor. Cost does not separate these
stacks.** Read the floor first; a between-stack number quoted before its floor is a number
that will be believed.

### The general form, which matters more than the null

The 2026-08-17 reading (`RUNS.md`) is now **conclusively unsupported**: it assumed a floor of
$7.92 against a measured $21.15, and its direction reversed. But the interesting quantity is
not that it was wrong — it is *how* wrong a one-cell estimate can be.

**Cell spread itself ranges 1.12x to 2.15x — $5.76 to $41.43 in gap terms, a factor of 7.2.**
Aug-17 drew its floor from the two cells that happened to be tightest. Had it drawn from rust
it would have concluded the opposite, with identical confidence and identical arithmetic.

> **A noise floor is a property of the population, not of the cells you happened to sample.
> Estimating one from a single cell can be wrong by a factor of seven in either direction, and
> nothing about a tight cell announces that it is tight.**

This is #42 with a number attached. It was committed by someone who had cited #42 the same day,
which is the usual pattern here: the rule was known, and the cheap comparison was available.

### The mechanism, which is the real content of this finding

Across all 8 trials **cost tracks turns at r = 0.971** (cost~bash-commands r = 0.852), and turns
range **205-370 within a single stack**.

> **Cost is a proxy for turns taken. Turns are a per-agent choice. So cost cannot separate
> stacks, and no n would fix it.**

That is a stronger and more useful statement than "the range is 42% of the floor". The ratio is
a fact about one run and could in principle come out differently on the next; the mechanism says
why it will not. A quantity dominated by how many turns an agent chose to take is not measuring
the stack, and adding trials buys precision on the wrong estimand — it would narrow the interval
around a between-stack difference that is not the thing varying.

It also reframes the floor: the within-cell spread is not noise in the sense of measurement
error to be averaged away. It is real, reproducible variation in agent behaviour, and it is
the signal — just not a signal about stacks.

A second, independent line agrees: all four stacks author a ~300-line WAV synthesiser (ts 320,
rust 340, unity 305, godot 46 on an engine built-in), so the audio-capability asymmetry cannot
carry a cost difference either — the component most likely to differ by stack does not.

### The caveat stays attached to the widest cell

Rust's `just run` is gated in this regime (#17), so 2.15x may be rust or may be our gate; n=2
per cell either way. What is established is that the floor is far wider than anyone estimated,
**not** that the stacks are equal — a null from an instrument with this much noise is the
instrument's floor, not a measurement of equality.

## 64. The count that proved the gate was costly counted the documentation

Asked what rust's gated `just run` cost, the first measurement grepped the rust transcripts for
`STARTER_NO_RAISE` and reported the agents had hit the refusal **5 and 3 times**. That number
was reported to the operator and repeated into `RUNS.md`.

It is **zero**. Both hits were the agent *reading the justfile and `main.rs`* — the two files
that document the flag. `just run` was invoked 0 times in both rust trials, against 3, 5 and 6
for ts, unity and godot.

> **A matcher that counts mentions of a mechanism instead of firings of it will report the
> documentation as evidence.** The better the guard is documented, the more "evidence" of it
> firing there is — the error grows with the quality of the thing it is measuring.

This is #31's shape (a matcher and a log sharing a buffer) relocated: not in a guard, but in a
*measurement of* a guard. Re-derived against the refusal's actual stdout sentinel and
cross-checked against invocation counts, both go to zero.

**What #17 actually measures**, corrected: the gate cost rust no refusal turns at all — both
agents read the justfile at record 17 of 1124 and 640, saw `run` was gated, and never tried it.
What separates rust is how little feedback tooling it ran (48 `just` invocations against 86,
101, 140), with zero `probe`, `test-render` and `check` — all of which its starter defines, so
the zeros are behaviour and not capability. It does **not** show the gate made rust expensive:
rust's cheapest trial ($36.16, 8 `just` invocations) also scored the field's only 1.000.

## 87. A directory's size is not the size of the thing you are protecting

> ### ⚠️ THE SIZE HELD; THE CATEGORIES BELOW DID NOT — see **#90**
>
> The "build output" row silently contains 77 trial work trees that are the **only** copy of
> their agent's source, because the older `runner.py` stores no tarball. A backup scoped by this
> table would have lost them. The table is kept because it was published and acted on.

`eval/runs/` is **138 GB**, and a task was written to solve the problem of backing that up:
external disks, object storage, LFS. The figure was never decomposed. Decomposed:

| category | size | files |
|---|---|---|
| **build output** (`debug/deps`, `debug/incremental`) | **136.99 GB** | 328,402 |
| submission tarballs | 0.80 GB | 89 |
| diffs, logs, text | 0.16 GB | 5,895 |
| JSON records | 0.11 GB | 30,210 |
| frames (PNG) | 0.08 GB | 2,610 |
| judge packs (rebuildable) | 0.01 GB | 1,364 |

**99.2% is Cargo build output** from the old `t1_rally`/`t2_net`/`t3_powerup` spec-change trials.
The evidentiary core — every score, judge round, diff, tarball and frame — is **~1.15 GB**, which
fits in a second git repository and needs none of the machinery.

> **A measurement of the container was used as a measurement of the contents.** 138 GB is
> arithmetically correct and describes something other than the question it was cited for, which
> was *"how hard is it to preserve the evidence?"*.

This is the same family as the four unscoped statistics withdrawn from `README.md` in this
session (#78 and its neighbours): a number that is true of one population, quoted about another.
The difference is only where the mismatch sits — there, between fields; here, between a directory
and the subset of it that matters. **The tell is identical: nobody could state the population the
number described**, because nobody had decomposed it.

**The cost of not decomposing is not the wrong number, it is the wrong design.** The task built
around 138 GB reached for infrastructure. The task built around 1.15 GB is a second repository
and a rule for what belongs in it. One of those is a week and the other is an afternoon, and the
only thing separating them was six lines of `du`.

## 90. #87's decomposition fixed the number and got the boundary wrong, in the direction that loses evidence

#87 corrected a real error: `eval/runs/` is 138 GB, 99.2% of it build output, and the evidentiary
core is ~1 GB. Re-measured 2026-08-22 with a classifier rather than by category, the core is
**13,431 files, 1.100 GB** of **368,571 files, 138.146 GB** — and the two published figures, "129
GB" and "138 GB", are **the same measurement in different units**: 128.66 GiB = 138.15 GB. Neither
ever described the evidence.

The size held. The boundary did not.

#87's table put **136.99 GB into one row labelled "build output (`debug/deps`,
`debug/incremental`)"**. Inside that row sit 77 trial work trees, because the older `runner.py`
wrote `run_dir/work/<tid>` and `run_dir/targets/<tid>` *inside* `eval/runs/`, and — unlike
`wholegame.py` — it stores **no `submission.tar.gz` and no `diff.patch`**, only a 3,000-character
`diff_stat` tail in the trial JSON. For every spec-change trial the work tree is the only copy of
what the agent wrote. A backup scoped by that row would have copied the scores of those trials and
none of the code they were scores of.

The same shape, one directory over: `~/game-research-work` was to be excluded because "every
submission is archived as `submission.tar.gz`". Checked per tree rather than per run, **two of 22
are not** — `wg-g4`'s `g4_platformer__unity__t0` and `__t1` died before the harness archived them,
leaving `prompt.txt` and no trial record.

> **A category is a claim about provenance, and it was assigned by looking at the paths.** "Build
> output" was true of 99.2% of the bytes and false of the files that mattered most, and the two
> are indistinguishable from a `du` listing — which is what produced both the row and the
> exclusion.

What replaced it is not a better list. It is a burden of proof: **a file is evidence until
something in the tree itself proves it regenerable, and the proof must name a producer that
declared the file its own output** — `CACHEDIR.TAG` with its signature checked, or the work tree's
own `.gitignore`. Both are the toolchain speaking about its own output rather than an observer
inferring from a name, both fail closed, and a fifth stack updates the classifier for free.
`eval/tools/evidence_set.py`, and the rule in `eval/PROTOCOL.md`.

**#87's closing line said the difference was six lines of `du`. It was not** — `du` is what
produced the mislabelled row. The difference was asking, per file, *who wrote this and can they
write it again?*

## 104. The only record of the starter a run was given is a git commit no archive contains, and the reclamation rule says to delete it

Re-packing `wg-g4c` (task 42) needed one thing that is not a score: **the starter as the agent
actually received it.** `anonymise.build_pack` drops files byte-identical to the starter, and it
compares against the starter as it is *now*, so rebuilding an old pack against a moved starter
reclassifies template code as authored work (#77). `build_pack` takes an `exclude_origins` set for
this, and its docstring gives the formula — *(rebuilt origins) minus (stored manifest) minus
(files dropped for length)*.

**The formula returns an answer for any run, and nothing in it can say whether the answer is
right**, because both terms come out of the same packer. The independent record is
`wholegame.prepare`, which copies the starter into the work tree and commits it as
`starter baseline`. Checked against that commit, the exclusion set was three files, all
TypeScript, from a capture-page repair landed **3.5 hours earlier** — and the Godot starter, which
moved the same morning, correctly produced none, because both Godot agents had edited
`tools/check.gd` themselves.

**That commit is in no archive.** `submission.tar.gz` holds the submission and **no `.git/`** —
verified by listing one: 0 entries under `.git/`. `diff.patch` and `diff.stat` name which files
changed, not what the unchanged ones contained. The baseline exists in exactly one place, the live
work tree under `~/game-research-work/`, and `PROTOCOL.md` said:

> `~/game-research-work/<run>/<trial>/` — **only if that trial's `submission.tar.gz` exists**.

All eight `wg-g4c` trees have tarballs. **The rule declared every one of them safe to delete**, and
following it would have made this repair impossible — the rule was written the previous day, by a
session that had just established (#90) that a file is evidence until something proves it
regenerable.

The census, over every stored judge pack:

| | packs |
|---|---|
| stored judge packs on disk | 68 |
| carrying a `pack.manifest` at all (the formula's minuend) | 43 |
| with a recoverable `starter baseline` | **8** |

All eight are `wg-g4c`. **The 22 surviving work trees' baselines are now preserved** —
`eval/runs/<run>/starter-baselines/`, a `git archive` of the root commit plus its `ls-tree`, 7.5 MB
across `wg-g4`, `wg-g4b` and `wg-g4c` against the 55 GB those trees occupy. That is the whole
remaining population; for every earlier run the tree is already gone.

For the other 60 packs an exclusion set can be computed and never checked, and
`repack.py` refuses them rather than guessing — which is why the refusal is in the tool and not in
a paragraph. Two other refusal reasons fired on real data in the same sweep: 24 `wg-matrix` packs
have no manifest, and 8 `wg-arena3d` packs dropped 4–21 files each for length, so the formula's
third term is non-zero and those files are legitimately returning.

> **A preservation rule is only as good as the artifact it names.** "Keep the tree until its
> tarball exists" is a correct statement about the *submission* and a false one about the *trial*,
> and the two are indistinguishable from the tree's size. #90 replaced "is this build output?"
> with "who wrote this and can they write it again?"; this is the same question asked of a
> directory that the earlier answer had already cleared.

The starter is also recorded a second, weaker way: `report.json` stores the absolute starter
**path**, which is what `repack.py` now reads instead of deriving one. That mattered immediately —
a derived default resolved inside an agent's git worktree, where the Unity starter's untracked
`tools/analyzer/bin/` does not exist, and three Unity files then looked like authored work. The
corroboration check refused two submissions and was right about the symptom and wrong about the
cause, which is rule 12 with the address supplied by `__file__`.

---

## 121. A budget ceiling and a bill are different questions, and one variable answered both under the bill's name

Three numbers described one spend: the ten stored rounds of
`runs/wg-tetris-judge-2026-08-17/post/` sum to **$31.66**, the `SEQUENTIAL.json` beside them
records **21.05**, and `README.md`, `JUDGING.md` and `DECISIONS.md` published **$21.05** as the
cost of those ten calls. The `pre/` field had the same shape: **$33.63** stored, **25.55**
recorded, **$46.79** published.

**None of the three was a mistake in arithmetic.** Each is the correct answer to a different
question, and only one of them is a cost.

| number | what it actually is | right? |
|---|---|---|
| $33.63 / $31.66 | sum of each stored round's own `cost_usd` — the artifacts of record | **yes.** This is what `eval/RUNS.md`'s judge table already carried |
| 25.55 / 21.05 | `measured_cost_usd` in `SEQUENTIAL.json` | correct **as a ceiling counter**, and not a cost |
| $46.79 / $21.05 | what three live documents published | **both wrong as attributed** |

### The mechanism, and it is deliberate

`field_sweep._judge_round` charges a round to the invocation's spend **only if this invocation
created it**:

    cost = float(res.get("cost_usd") or 0.0) if fresh else 0.0

That is right, and the comment above it says why: `--max-cost` is enforced against measured
spend, and a round already on disk was paid for on an earlier day, so re-charging it would make
the ceiling refuse work that costs nothing. The ceiling has never failed. What the code then did
was persist that counter under the name **`measured_cost_usd`**, in a file a person reads when
they want to know what a field cost.

### How it was established, and the run said it out loud

The `post` sweep's own `sweep.log` prints the counter as it goes:

| after aspect | cumulative | fresh rounds so far |
|---|---|---|
| `architecture` | **$0.00** | none — both rounds already on disk |
| `audio` | **$0.00** | none — both rounds already on disk |
| `fun` | $3.96 | 1.9298 + 2.0315 |
| `idiomatic` | $16.76 | + 6.0266 + 6.7755 |
| `ux` | **$21.05** | + 2.3075 + 1.9778 |

Four rounds, $10.6056, charged $0.00 — and $31.6556 − $10.6056 = $21.05 to the cent. Their
mtimes are 06:53:09 against 07:01:40–07:35:05 for the six the invocation wrote, and they are
`architecture` and `audio`: **a prefix of the execution order**, which is what a resume looks
like and what a coincidence does not. The `pre` gap, $8.0805, is `architecture__seed0` — the
probe round of the first aspect, the single-element prefix.

**$46.79 is a different error with the same result.** `eval/RUNS.md`'s per-game table for
2026-08-16 reads $13.16 for three `g1_pong` calls and $33.63 for ten `g2_tetris3d` ones.
$46.79 is the day. It was published three times as the cost of *the* eight-submission tetris
field, which cost $33.63. And the $13.16 is the only judge spend in this project with no
surviving artifact — no `g1_pong` round from that day exists on disk (task 04).

### It is not one field, it is five of eleven

`judge/judge_ledger.py --tree runs/` over every stored sweep directory:

| | |
|---|---|
| sweep directories holding rounds | 11 |
| stored rounds | 93 |
| field cost, summed from the rounds | **$306.73** |
| directories whose stored counter under-reports | **5** |
| under-reported | **$69.93** |
| directories whose counter exceeds what is on disk | **0** |

`eval/RUNS.md`'s opening line said *"plus $46.79 of specialist-judge calls"*. The true figure is
$306.73, and the ledger's own tables 780 lines later already added to more than $46.79 — a
headline and its own detail disagreeing by 6.6x, inside one file.

### What was wrong was a NAME, so the fix is two names

Re-charging carried rounds would break the one mechanism here that works.
`field_sweep._record_cost` now writes both, and they cannot drift because the ledger tool
computes the second one:

    charged_to_ceiling_usd   what this invocation spent; what --max-cost is enforced against
    field_cost_usd           what the rounds stored here cost

> **A variable that is correct for one question will be read as the answer to a neighbouring
> one if its name does not say which.** `measured_cost_usd` is not ambiguous prose — it is the
> most specific-sounding name available, it carries the word this project uses for "read from
> reality rather than estimated", and it was still wrong, because the noun it omits is the one
> that varies. Rule 12 says the address is an input to the check; this is the same defect with
> a field name as the address.

### The method that was right by coincidence, caught inside the fix

`judge_ledger.explain_gap` first tried to demonstrate a resume from an mtime split: the carried
rounds are older than the written ones. On `post` that is a real boundary, eight minutes wide.
On `pre` it returned `architecture__seed0` — **the right answer, from no evidence at all.** All
ten of `pre`'s files were moved out of a `/private/tmp` sweep directory with `cp`, so their
mtimes are 0.0006 s apart in alphabetical order, which is also `--sequential`'s execution order.
A clean, ordered, meaningless split.

The check now requires the boundary to exceed 60 s — the shortest stored round ran 246 s — and
`pre` honestly reports AMBIGUOUS, because two subsets of its rounds sum to $8.08 and only
external evidence picks between them. **A tool changing its own answer when its method was
corrected is the whole reason to build the producer rather than quote the number**, and it is
rule 15's shape: the mtime split had a mutant that reddened it and no variant asking whether it
could still pass on input it mishandles.

---

## 159. Every dollar figure in this project is a list-price valuation of tokens, on an account where no money moves per token — and a research decision was declined on one

The harness records `agent.cost_usd` per trial and the documents report it as spend: *"$421.00"*
for a field, *"$2,466.31"* tree-wide, *"the $421-to-$698 spend"*.

**The account is a subscription. Per-token API charges do not apply, and none of those dollars
was ever paid.**

The field is exactly what the CLI computes from token counts at published API rates, verified on
a stored record:

    sum(modelUsage[*].costUSD) = 42.921086
    total_cost_usd             = 42.921086     identical

`modelUsage` carries `inputTokens`, `outputTokens`, `cacheReadInputTokens` and a `costUSD` derived
from them. The CLI reports that valuation **whatever the billing arrangement** — it is what these
tokens would list for, not what anything cost.

### What survives, and it is most of it

**The token counts are real.** Every comparison built on them stands: one trial used more of the
resource than another, and by how much. What is wrong is the **unit and the noun**. Writing `$`
and *spend* claims an expenditure, and expenditure is the thing that did not happen.

### One conclusion was already wrong for a second reason

The result table reports *cost tracks turns at r = 0.971* and concludes cost is "very nearly a
restatement of how many turns an agent chose to take."

That correlation is not a finding about stacks. **It is arithmetic**: the figure is computed from
token counts, and token counts scale with turns. The measurement was turns, reported twice, and
correlated with itself. A near-unity correlation was the only possible outcome.

The useful half is unchanged and should be stated in its own terms: **token usage does not
separate the four stacks**, and it varies more within one stack than between stacks.

### The decision that was acted on

> *"Nothing here justifies the $421-to-$698 spend."*

A harder task was **declined on a price**, and the price is not a price. The reasoning behind the
decline — that the pre-test's spread was the instrument's rather than the level's — is untouched
and still stands on its own. But the sentence that carried it appealed to money, and the money was
notional.

> **A figure nobody pays is still a figure people act on.** This one had a producer, was
> re-derived correctly all week, reproduced to the cent across independent tools, and was wrong
> about what it measured the entire time. Every check this project owns asks whether a number is
> *reproducible*. None asks what its **unit** means.

### What the real constraint is, and that it has never been measured

On a subscription the binding resources are **rate limits, session capacity and wall clock** —
the things `PROTOCOL.md` already tells you to probe before a run, and which killed trials in three
separate matrices. None of them is denominated in dollars, and none is recorded per trial beside
`cost_usd`. `wall_s` and `num_turns` are stored; the resource that actually stops a run is not.

**The repair is not to delete the figures.** They are a real proxy for token consumption and the
only per-trial resource number the harness has. They must be **named for what they are**, and no
decision may rest on them as money.

### The capped runs were paced against a constraint that does not exist

`wholegame.py` records a measurement worth re-reading under #159. `--max-budget-usd` is **visible
to the building agent and instructs it**, established by three-way discrimination: an agent
launched with 7.31 answers 7.31 when asked its limit, one launched with 41.77 answers 41.77, one
launched without the flag answers NONE. Usage rose **1.54×** when the stated ceiling moved 25 → 48,
and capped trials clustered just under their cap (23.07, 24.33, 24.34, 25.06).

The reading at the time was that runs under different caps are not comparable. That stands. **The
stronger reading is that a capped agent was told to conserve a resource that is not scarce** — it
paced itself, produced less, and the record of what it could have built at that task is
correspondingly short. The cap did not merely make those runs incomparable; it made them worse,
for nothing.

`MAX_BUDGET_USD = None` is already the standing configuration, and the reasoning that put it there
— any stated value is an instruction, so only an absent flag is neutral — was right for a reason
better than the one given.

**The judge path still carries hard money limits.** `field_sweep.py` defaults to `--max-cost 60`
with `--per-call-budget 12`, and refuses a call when `spent + 12 > 60`. A sweep is therefore
truncated at roughly $48 of *valuation* — a run stopped part-way through its evidence by a
threshold on a quantity nobody is charged for. Nothing in the stored record shows this having
bound yet; the blind field charged 27.68 against it and stopped because it was finished.

> **A limit denominated in a unit that does not bind is worse than no limit.** It cannot protect
> the resource that is actually scarce, it truncates real evidence when it fires, and where the
> figure is visible to the subject it instructs the subject to do less.

What should bound a run is what is actually finite: **turns, wall clock, and rate-limit capacity.**
Turns are already the build-side bound and are invisible to the agent, which is why that choice
was correct.

---

## 160. The smallest p-value a design can return is a property of its cluster structure, and here it rules the question out before any data is seen

Token usage put one stack cheapest in **5 of 7** groups. Chance for one arm to lead a four-way
group is 25%, so 5 of 7 looks like something. Adjudicating it produced a result about the
**design** rather than about the stacks.

The groups are not seven observations. **Three of the four games recur across runs**, so a
permutation test that treats each group as independent evidence counts the same trials twice. With
stack labels permuted *within a cluster* and held constant across every group in it:

| independent unit | clusters | p (post-hoc-safe) | smallest p this design **can** return |
|---|---|---|---|
| run directory | 4 | 0.0156 | **0.0156** |
| game | 4 | 0.0469 | 0.0156 |
| **connected component of run and game** | **2** | **0.2500** | **0.2500** |

Two readings, and both are about the instrument:

- At the run unit the observed p **is the floor** — `4 × (1/4)⁴`, the most extreme outcome the
  design can produce, with no margin. Anything short of a perfect sweep returns the next
  attainable value, which is above 0.05. Dropping any single run puts the floor at 0.0625, so **no
  subset of three runs could have reached α whatever it said** — measured over all four
  leave-one-out cases.
- **6 of the 7 groups form one connected component.** At that unit the floor is **0.25**, and no
  outcome available to this corpus could have reached α = 0.05.

> **The question is not answered no. It is unasked.** A design whose smallest attainable p exceeds
> α cannot produce evidence at that α no matter what the world does — and that is knowable from
> the cluster structure alone, before any data is read.
>
> **Report the floor beside the p, always.** A p-value at its design's floor and a p-value with
> room underneath it look identical and mean opposite things: one is the strongest signal the
> instrument can emit, the other is a measurement.

This generalises past cost. **Any adjudication over these run directories inherits the same
ceiling**, because the ceiling comes from how the corpus was built — three games reused across
runs — and not from what is being measured.

### The size question is separate and answers itself

Where the leading stack leads, its margin is **14.9% to 93.7% of that group's own within-cell
noise floor — above it in 0 of 5.** A consistent ordering and a lead that beats the noise are
different claims, and only the first was ever in question.

### What the adjudication cost, and what it caught

Five review rounds, the fifth clean, and rounds 1-4 each found a real defect in work built to
settle a question about rigour:

- A **tied** cheapest pair was resolved by alphabetical order, so the tool reported
  `groups_led=1` and `times_cheapest=0` in the same output.
- A sampling limit was **checked after the allocation it exists to prevent** — 2085 MB against a
  24 MB budget.
- Three findings landed on one sampled code path, which was **deleted rather than patched three
  ways**: it served a hypothetical and no stored data exercised it.
- The limit budgeted **time** while the thing that grew was **memory**.

Two are worth keeping for their shape:

- **`--selftest` was green while the renderer had never been called at all**, and it died on a
  `KeyError` the first time it ran. A producer and the report that prints it are two components,
  and a selftest over the first says nothing about the second.
- **A memory pin passed locally and let its mutant SURVIVE on Linux**, because it compared a
  *total* peak RSS carrying the interpreter's baseline rather than the growth. Only CI caught it —
  no local run could have.

## 172. No cap holds this machine, and the one flag that documents a memory limit accepts it and ignores it

The scene performance pass was designed around a **ramp** — raise complexity until frame time
exceeds a budget, report the level reached — which measures the stack only if the resources under
it are held. On this host (Apple M3 Max, Darwin 25.2.0) they cannot be:

| lever | result |
|---|---|
| `taskpolicy -b` | CPU throughput to **0.20x**, GPU frame time moves **under 0.1 ms** in every interleaved round |
| `taskpolicy -c utility` | GPU within **0.28 ms** |
| `RLIMIT_AS` / `DATA` / `RSS` | refuse outright — and they refuse when **lowering** the soft limit, which is always permitted |
| `RLIMIT_CPU` | the one enforceable rlimit; kills on **cumulative seconds**, not rate |
| Linux VM with cgroups | real caps (`--memory=512m` OOM-kills; `--cpus=2` gives 2.08 cores) and **no GPU device at all** |

**There is no GPU lever.** The CPU levers are real and do not touch GPU frame time, and the
container that has real caps has no GPU to cap — so every route either misses the resource or
removes it.

**The host also gives GPU work no isolation:** one competing GPU process costs **2.13x**. So the
quantity a ramp would report is a function of what else is running, and nothing available makes it
not be.

### The sharpest instance, and it is #61 again

**`taskpolicy -m` documents a MiB limit, accepts it, and ignores it.** Reproduced independently:
`taskpolicy -m 16 python3 …` allocated **1024 MiB and exited 0** — a 64x overshoot with no error
anywhere.

> **An accepted-but-ignored flag is worse than an unsupported one.** An unsupported flag fails
> loudly; this one is indistinguishable from a working cap by anything a script can see, and it is
> the second time this project has been handed one — Unity's standalone player takes
> `-disable-audio` and does nothing with it (#61).
>
> **The defence is the same both times: verify a cap by measuring that the process could not
> exceed it, never by observing that the command was accepted.**

The rlimit result needs its own control to mean anything, because a probe that refuses everything
proves nothing about the refusal. Lowering the soft limit — always permitted — separates them:
`RLIMIT_CPU` and `RLIMIT_NOFILE` accept, the four memory limits refuse.

### What replaces the cap is measured, and it is scheduling rather than bounding

The same fixed workload, spaced **25 s** apart, holds to **0.766–2.485%**. Back-to-back it swings
**1.975x**. In ramp levels: **0.04–0.11 spaced**, against **1.0–3.1 back-to-back** and **1.1–3.4
contended**.

> **Where a resource cannot be bounded, spacing the measurements can still make them comparable —
> and that is a design constraint on the RUN, not a property of the instrument.** A perf matrix
> that packs trials back-to-back to save wall-clock destroys the quantity it exists to collect.

**Frame timing is also not the same quantity across the four stacks.** Bevy on Metal records CPU
time only; the TypeScript capture path reaches no GPU at all (SwiftShader, with the starter's pin
*and* with no flags — only `--use-angle=metal` reaches hardware); Godot and Unity both expose a
real GPU timer. **A cross-stack ramp must read a harness-side wall clock**, because the stacks'
own timers measure different things.

### What is still unmeasured, stated because the numbers invite over-reading

Every figure above is **one fixed synthetic workload** and is therefore a **floor**. The ticket's
third measurement — the run-to-run spread of a *real* submission — could not be taken, because no
scene has been built. The drift is also **non-monotone**, so it is not simple heat and its cause is
unseparated.

---
