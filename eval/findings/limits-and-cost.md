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
