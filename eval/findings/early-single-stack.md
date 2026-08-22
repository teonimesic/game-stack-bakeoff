# The single-stack phase (2026-08-10 to 08-12)

Superseded by the four-stack matrices. Kept because its method notes, its controls
and two retractions are still cited.

> Index and the distilled rules: `../FINDINGS.md`

## Method

- Driven by the **`claude` CLI directly**, not the SDK:
  `claude -p <task> --output-format json --setting-sources project --strict-mcp-config
   --exclude-dynamic-system-prompt-sections --max-turns N --max-budget-usd N`
- `--setting-sources project` is mandatory and empirically verified. Without it the operator's
  global `~/.claude/CLAUDE.md` (which mandates TDD) leaks into every arm. Probe result:

  | Arm | global "rm -f" rule visible | global TDD rule visible |
  |---|---|---|
  | default | yes | yes |
  | `--setting-sources project` | **no** | **no** |

- Each trial gets a fresh copy of the template with a baseline git commit, so
  `git diff HEAD` isolates exactly what the agent did.
- **Held-out tests are copied in after the agent stops.** Protected paths
  (`crates/*/tests/**`, `justfile`, `.config/**`) are reverted to pristine before grading, so
  neutering or deleting a test cannot help — the SWE-bench mechanism.
- **Negative control passes**: `runner.py check-suite` confirms every task's held-out tests fail
  on the pristine template. Control floors: `t1_rally` 0.00, `t2_net` 0.67 (two of its three
  held-out tests pass trivially before the fix). Reported scores are **normalised against these
  floors**, so 0.00 means "did nothing" and 1.00 means "fully solved".
- Cost and tokens come from `modelUsage`, not `usage` — `usage` covers the main loop only and
  excludes subagents.
- All trials share one `CARGO_TARGET_DIR`, so dependencies compile once instead of every trial
  paying a ~4-minute cold Bevy build. **Trials therefore run serially** — cargo file-locks a target
  directory, and concurrent trials block on each other badly enough to change the outcome (see
  Bug 3).
- A **positive control** (gold patch) should exist for every task: the negative control only proves
  the tests fail beforehand, which is also what an unsatisfiable assertion looks like. t1's gold
  patch was written by hand and confirmed to pass 2/2.

## Arms

| Arm | Change |
|---|---|
| `baseline` | template as shipped |
| `no_instructions` | `AGENTS.md` and `CLAUDE.md` removed |
| `no_api_notes` | `AGENTS.md` minus the Bevy 0.19 delta table, and `docs/bevy-0.19-notes.md` removed |

## Statistical honesty

Per Miller ([arXiv:2411.00640](https://arxiv.org/abs/2411.00640)):
- Scores are averaged **per task first**, then the SE is taken across tasks. Pooling across all
  trials is inconsistent.
- Arm comparisons use **paired per-task differences**, which cut estimator variance by roughly a
  third versus comparing population means.
- Wilson intervals are used for the binary pass rate; they behave correctly at small n where the
  normal approximation does not.

**With 2 tasks the minimum detectable effect is far larger than any realistic instruction
improvement.** Published guidance is that an eval needs on the order of 1,000 items to resolve a
3-point difference. This suite resolves "the template is broken" and "this arm is catastrophically
worse", nothing finer. Treat it as regression-catching infrastructure and grow the task count
before believing any A/B number.

## Results

Full serial matrix: 3 tasks × 3 arms × 2 trials = **18 trials**, Sonnet, $18.16 total.
All 18 reached `terminal_reason: completed` — no timeouts, no budget exhaustion. Scores are
normalised against the control floors, so 0.00 = did nothing and 1.00 = fully solved.

| arm | pass | rate | 95% CI | score | ±SE | $/trial | turns | wall |
|---|---|---|---|---|---|---|---|---|
| `no_instructions` | 4/6 | **67%** | [30%, 90%] | **0.67** | 0.17 | 1.27 | 35 | 287 s |
| `baseline` | 2/6 | 33% | [10%, 70%] | 0.33 | 0.17 | 1.10 | 30 | 230 s |
| `no_api_notes` | 1/6 | 17% | [3%, 56%] | 0.17 | 0.17 | 0.66 | 18 | 136 s |

Paired per-task differences vs `baseline` (correlation 0.50, n = 3 tasks):

| arm | Δ score | SE | 95% CI |
|---|---|---|---|
| `no_instructions` | **+0.333** | 0.167 | **[+0.01, +0.66]** |
| `no_api_notes` | −0.167 | 0.167 | [−0.49, +0.16] |

### How much to believe this

**Removing `AGENTS.md` and `CLAUDE.md` entirely scored highest**, and the paired interval for that
difference *just barely* excludes zero at its lower bound of +0.01.

I do not think that is strong enough to act on, for four reasons: the paired SE is computed from
**three** per-task differences; two arms were compared against baseline with no multiple-comparison
correction; it is one model and one 3-task suite; and moving a single trial would push the interval
back across zero. What it does do is fail to find any evidence that the instruction file helps
correctness — which is the *same* direction as the one published measurement I could find
(ETH Zurich, [arXiv:2602.11988](https://arxiv.org/abs/2602.11988): zero correctness gain from
context files, >20% extra token cost).

The honest statement is: **no evidence `AGENTS.md` improves correctness here, weak and
unreplicated evidence it may cost something, consistent with prior published work.** That is worth
knowing and worth testing properly with more tasks; it is not worth deleting the file over.

### The finding I would act on first

**14 of 18 trials ended with the agent's own `just verify` red**, every one of them reporting
`terminal_reason: completed`. The agent decided it was done while the gate it had been told to
respect was failing.

That is the template's central promise not holding, and it is independent of which arm the trial
was in. It is also consistent with the published observation that 61.8% of *successful* agent runs
contain no validation command in their final five actions — agents ship without checking.

Fix applied: a **Stop hook** (`.claude/hooks/verify-gate.sh`) that refuses to end the turn while
`just verify` is red, feeds the failure output back, and explicitly forbids weakening a test to
get past it. An instruction is advisory; a hook is not. It exits silently when `target/` is absent
so it never blocks on a cold build, and Claude Code overrides it after 8 consecutive blocks so it
cannot trap a stuck session. Verified in both directions: blocks with valid JSON on red, silent
exit 0 on green.

### The second finding: fast, confident, and wrong

All three "self-verify green but held-out red" trials came from **one arm**, `no_api_notes` — and
that arm was also the *cheapest and fastest by a wide margin* (18 turns, $0.66, 136 s, versus 30–35
turns and $1.10–1.27 elsewhere). Those agents finished early, their own check agreed with them, and
`RallyLength` was never exported.

At n=2 per cell I cannot attribute that to the ablation rather than noise. But the *pattern* —
cheap, quick, self-certified, wrong — is exactly what a held-out grader exists to catch, and it is
the number I would build the next iteration of the suite around.

### Borderline flag worth reviewing

Two `t3_powerup` trials were flagged for editing `crates/game/src/lib.rs`, outside the task's
sim-only `allowed_paths`. Adding a visual for a new entity is a reasonable instinct, and the task
said the powerup need not interact with anything. This may be a fourth over-strict rule rather
than genuine scope violation — it should be reviewed against the transcripts before the next run.

## What the first trial taught us

A single smoke trial (`t1_rally`, baseline arm, Sonnet) found **two bugs — one in the harness and
one in the template — and neither was in the agent's work.** That is a good argument for running
the loop at all.

**Raw numbers:** 537s wall, 48 turns, $2.12, `terminal_reason: completed`.
Held-out tests: **2/2 passed.** The agent solved the task.

### Bug 1 — harness false positive (fixed)
The task says *"add tests covering the behaviour."* The agent created
`crates/sim/tests/rally.rs`. The tampering check flagged it, because
`crates/*/tests/**` is a protected path, and zeroed a correct solution.

**Every trial would have failed this way.** The check now distinguishes git status codes: creating
a new file (`??`/`A`) is legitimate; modifying or deleting a *pre-existing* protected file is
tampering. That is the property that actually matters — you cannot neuter a test you just created.

### Bug 2 — the template let formatting mask correctness (fixed)
The agent's own `just verify` went **red purely on `cargo fmt --check`**, over a multi-line
`assert!` in its own new test file. Clippy passed, every test passed, the feature worked.

`verify` now runs `fmt` (auto-fix) rather than `fmt-check`. Formatting is mechanical and
auto-fixable; letting it gate the signal costs the agent a turn and — worse — reports "not done"
when the work is done. CI still runs `fmt-check`, so unformatted code cannot land.

This is the "give the agent a check it can run" principle applied honestly: the check has to
answer *is the work correct*, not *is the whitespace canonical*.

### Behavioural observation: the determinism guidance landed
Unprompted by the task spec, the agent added `RallyLength` to `state_hash`. Nothing in the task
asked for that — the prompt only said the value must be reproducible across runs with the same
seed. `AGENTS.md` says simulation state must be part of the snapshot, and the agent applied it.

n=1, so this is an anecdote rather than evidence. But it is the specific behaviour the
`no_instructions` arm exists to test, and the `t3_powerup` task was designed to measure it
directly.

### Cost observation
48 turns and $2.12 for a small pure-logic change is high, and most of the wall-clock was a cold
Bevy build inside the agent's own `verify`. Trials now share a `CARGO_TARGET_DIR`, and the
template ships `just warm`. Watch whether turn counts drop in the matrix run — if they do not,
the bottleneck is the agent's strategy rather than the build.

### ⚠️ RETRACTION — two findings previously recorded here were wrong

An earlier version of this file claimed (a) that the t1 task was unsound because idle play never
scores, and (b) that the template had a game-design defect where two centred paddles rally
forever. **Both claims were false, and both came from the same methodology error.**

**The error:** the mutation-testing loop restored the mutated source with `mv file.bak file`.
`mv` preserves mtime, so the restored file was *older* than the compiled artifact, cargo saw
nothing to rebuild, and every "unmutated" measurement afterwards silently ran the **previous
mutant's binary.** The specific contaminant was the arena-crushed-flat mutant
(`ARENA_HALF_HEIGHT` 250→55), which nearly seals the goal — hence "nobody ever scores".

**On a genuinely clean tree, with a forced rebuild, idle play scores normally:**

| seed | 3 | 7 | 11 | 42 |
|---|---|---|---|---|
| points in 60 s | 27 | 21 | 24 | 21 |

So: no design defect, and the t1 held-out test's `resets > 0` assertion was always satisfiable.
The change forcing the right paddle out of position is harmless and arguably more robust, but it
was motivated by a wrong diagnosis and fixed a problem that did not exist.

**The lesson worth keeping** is the one that generalises: *a build system that decides what to
rebuild from mtimes will quietly serve you a stale binary, and a stale binary produces confident,
reproducible, completely wrong measurements.* Any script that mutates and restores source must
`touch` the file (or write through a pristine copy) and should verify the unmutated baseline is
green **after** the loop, not only before. This file now does both.

### Bug 3 — parallel trials sharing a cargo target dir starve the agent (fixed)

The two matrix trials that failed did so for a real and different reason. Their held-out output:

```
Blocking waiting for file lock on build directory
error[E0432]: unresolved import `sim::RallyLength`  --  no `RallyLength` in the root
```

Both agents stopped on their own (`terminal_reason: completed`, 23 and 35 turns) with `verify`
red and the feature never added. Cargo file-locks a target directory, so two concurrent trials
sharing one block on each other — which starves the agent's own `just verify` and pushes it into
giving up while believing it is done.

`--parallel` now defaults to 1 with a comment explaining why. Sharing a target directory and
running concurrently are mutually exclusive; pick one.

This is also a genuine finding about agents rather than about my harness: **a verification command
that becomes slow does not merely cost time, it changes the outcome.** The agent did not wait it
out — it concluded and stopped. That is the strongest argument in this whole project for keeping
`verify` fast, and it is consistent with the research showing that agents ship without a final
validation step in most successful runs.

### Bug 4 — the anti-gaming rule was wrong three times, in the same direction

The tampering check zeroed correct work three separate times, each time punishing an agent for
doing exactly what the task asked.

| Version | Rule | What it wrongly flagged |
|---|---|---|
| 1 | any change to a protected path | creating a new test file the task asked for |
| 2 | any change to a *pre-existing* protected file | adding a test to an existing file (42 insertions, 1 deletion) |
| 3 | any change that deletes a line | editing one `use` line to add an import |
| **4 (current)** | **deleted files + explicit cheat patterns only** | — |

The reasoning that finally settled it: **protected paths are reverted to pristine before grading,
so an edit to a test file cannot influence the result either way.** The revert is the defence; the
flag was only ever meant to be information. Once that is clear, scoring on it is not just
imprecise, it is incoherent — it punishes something that is already neutralised.

The current rule zeroes a trial only for unambiguous cheats: deleting a test file, adding
`#[ignore]`, `--no-verify`, or assertion tautologies. Protected-path edits are recorded in a
separate `touched_protected` field as diagnostics.

**The generalisable lesson: an anti-gaming check that can fire on good behaviour will, and every
false positive it produces is indistinguishable from a genuine failure in the aggregate numbers.**
Bias these checks heavily toward false negatives — a missed cheat costs you one data point, a
false positive silently corrupts the comparison. Verify the rule against real transcripts before
trusting any run that uses it.

Because held-out results are stored per trial and are independent of the tampering verdict,
`regrade.py` recomputes verdicts offline without re-running anything. That is deliberately modelled
on SWE-bench's `rewrite_reports`, which exists for exactly this: fixing a grading bug without
paying for new rollouts.

### ⚠️ SECOND RETRACTION — the 18-trial results were confounded by two template defects

The headline finding from the Sonnet run — **14 of 18 trials ended with the agent's own
`just verify` red** — was reported as evidence about *agent behaviour*. Fine-tuning the Rust
template found two defects that make that reading unsafe.

**1. The render harness was reproducibly flaky on the first run after a build.** wgpu compiles
render pipelines lazily, so the first frames out of a fresh `App` can be a bare clear colour. The
harness took the first readback that arrived plus one extra frame. Measured: **2 first-run
failures in 2 cold runs** (on two *different* tests), 0 in the warm runs immediately after —
and a baseline cold `just verify` went **red**.

So an unknown share of those 14 red verifies were **a red gate the agent did not cause**. The
capture loop now pumps until two consecutive readbacks are byte-identical; every cold run since
has been green first try.

**2. The Stop hook never fired in a single eval trial.** It guarded on `[ -d target ]`, but the
runner sets a per-trial `CARGO_TARGET_DIR`, so there is no `target/` in the project directory and
the hook exited 0 every time. The mechanism introduced specifically to fix "agents stop with a red
gate" was **silently disabled in exactly the situation it was written for**, and nothing reported
that. Now `[ -d "${CARGO_TARGET_DIR:-target}" ]`.

**What survives:** the *observation* that agents stop while their own gate is red is still real —
it reproduced on Opus with a different template state. What does not survive is the 14/18 figure
as a clean measurement of agent behaviour, or any claim about whether the Stop hook helps. Both
need re-measuring on the fine-tuned templates.

**The generalisable lesson, again:** a guard that can silently no-op is worse than no guard,
because it also suppresses the signal that it is missing. This is the seventh instance in this
project of a check that appeared to work while measuring nothing — and the first where the
disabled check was one I had added *as the fix* for an earlier finding.

### Template defects found only by prototyping the tasks

Every stack's fine-tuning agent was asked to implement all three eval tasks end to end before
declaring done. **Every one found at least one latent trap that would have failed a correct
implementation**, and none was findable by reading:

| Stack | Trap |
|---|---|
| all four | `entities.len() == 3` — task (c) adds an entity, so a correct fix turns a protected test red |
| Rust | `spawn_views` drew *everything*, so a `Powerup` rendered as a spurious paddle and broke the golden — fixable only by `bless`, which writes **outside task (c)'s allowed paths** |
| Rust | clippy's `manual_is_multiple_of` fires on `tick % 200 == 0`, the most natural expression of task (c) — a correct implementation red on a pure style nit under `-D warnings` |
| Unity | `PongView` drew a quad per entity — same failure, and `Assets/View/**` is outside task (c)'s paths, so **no legal fix existed** |
| Unity | the golden image lived outside task (b)'s allowed paths, so `just bless` would have been scored as **tampering** |
| Unity | a test pinned the exact 5-stage pipeline list, in a protected file, blocking the natural implementation |
| TS / Godot | the same entity-count assertion, found independently |

**Implication for anyone building an eval:** a task is not validated by a negative control and a
positive control alone. You must also confirm that a *correct* implementation can reach green
**without touching any file the harness protects**. Three of the seven traps above would have
scored a correct agent as a tamperer.

### Mutation testing the playability assertions

A playability test that always passes is worse than none, so the assertions were mutation-tested.

| Mutant | Caught? |
|---|---|
| ball unreturnable from serve (`BALL_START_SPEED` 250→9000) | ✅ 1 failure |
| paddle seals the goal (`PADDLE_HALF_HEIGHT` 50→245) | ✅ 2 failures |
| paddle far too slow (`PADDLE_SPEED` 300→20) | ✅ 1 failure |
| arena crushed flat (`ARENA_HALF_HEIGHT` 250→55) | ✅ 2 failures |
| ball crawls (`MAX_BALL_SPEED` 900→60) | ✅ 3 failures |
| **no escalation (`BALL_SPEEDUP` 1.05→1.00)** | ❌ **escaped** |

Unmutated baseline: **5/5 green**, verified *after* the loop with a forced rebuild.

The escape was real and the assertion was **removed rather than weakened**: measurement showed
peak ball speed is 1.26× serve speed with escalation *and* without it, because the per-hit
deflection term contributes more than the multiplier at these constants. No threshold on observed
peak can separate the two. An assertion that cannot fail is false confidence, so it is gone, with
a comment explaining what to measure instead if escalation ever becomes a requirement.

Two earlier mutants (`BALL_SPEEDUP`→1.60, `MAX_BALL_SPEED`→20000) also escaped, and there the
**mutants were wrong, not the tests**: measurement showed the speed cap absorbs the first and the
ball never approaches the cap in 60s for the second. Neither actually degrades playability.

### Cost and speed after the shared-cache fix

| | smoke trial (cold) | matrix trials (warm) |
|---|---|---|
| wall | 537 s | 151 s, 246 s |
| cost | $2.12 | $0.75, $1.24 |
| turns | 48 | 23, 35 |

Sharing one `CARGO_TARGET_DIR` across trials cut wall-clock ~3× and cost ~2×. Turn count dropped
too, which suggests some of those 48 turns were the agent working around slow builds rather than
working on the problem.

## Observations from individual trials

_Qualitative notes on how agents actually behaved, which is often more useful at this sample size
than the aggregate numbers._

- **t1 smoke trial (baseline):** implemented `RallyLength` correctly and, unprompted, added it to
  `state_hash`. The task only said the value must be reproducible across runs with the same seed;
  `AGENTS.md` says simulation state must be part of the snapshot. The agent applied the repo's
  convention rather than the literal spec, which is the behaviour the instruction layer is for.
- Across all three completed t1 trials the agent wrote its own tests without being told twice, and
  in every case put them in `crates/sim/tests/` — the location `AGENTS.md` implies but never
  states outright.

---

# Cross-stack bake-off — final results (2026-08-12)

24 blank `claude -p` sessions on Opus, 3 tasks x 2 trials x 4 stacks, ~$65.
Prompts semantically identical, each written in its own stack's vocabulary.

| Stack | Strict | Lenient | 95% CI | Turns (med) | Cost | Wall (med) | self-verify RED |
|---|---|---|---|---|---|---|---|
| Unity 6 | 6/6 | 6/6 | [61%,100%] | **32** | $2.59 | **5.6m** | **2** |
| TypeScript / three.js | 6/6 | 6/6 | [61%,100%] | 43 | **$2.57** | 6.8m | 0 |
| Godot 4.7 | 5/6 | 6/6 | [61%,100%] | 45 | $2.68 | 6.5m | 0 |
| Rust / Bevy | 6/6 | 6/6 | [61%,100%] | **49** | $2.99 | **9.4m** | 0 |

Godot's 5/6 is out-of-scope `.codex/` files an agent created; its held-out tests
passed 4/4. Both readings are shown rather than picking the tidier one.

## The suite cannot separate these stacks on capability

Every stack solved every task. Identical Wilson intervals. **When everything
passes, pass rate carries no information**, and n=6 makes the interval useless
for ranking. The tasks are too easy for four well-built templates — that is a
finding about the task suite, not about the stacks.

Efficiency does separate them, and the ordering **inverts the paper prediction**:
Unity fastest and fewest turns, Rust slowest and most. Rust needs ~53% more turns
than Unity and 68% longer per trial. Rust was chosen on the compiler-as-harness
argument; measured, it is the least efficient of the four.

## Three findings worth trusting

1. **Verification latency changes agent behaviour.** self-verify-red appears in
   2/6 Unity trials (run 2), 3/6 (run 1), and **0/36** across Rust, TypeScript
   and Godot. Unity is the only stack whose `verify` costs a ~10 s editor launch
   rather than a sub-second test run. The agent stops short of a slow gate. This
   is the strongest signal in the dataset and it is not about C#.
2. **Prompt wording moved the numbers more than the stacks did.** Rust 32 -> 49
   turns and TypeScript 50 -> 43, purely from rewriting prompts in each stack's
   own vocabulary. "Byte-identical" was not fairness; it handed Rust a prompt
   written in Rust.
3. **Zero tampering in 48 trials** across both runs, despite a deliberate
   determinism trap.

## What this cost to learn, methodologically

Twelve times in this project a mechanism ran, reported success, and measured
nothing: a shared build cache serving another trial's binary; a control failing
for missing dependencies rather than a missing feature; a Stop hook no-oping
because the target dir moved; a test runner exiting 0 over zero tests; a mutation
test reading a stale binary; a scenario audit defeated by PascalCase; a Godot
grader that never compiled through two entire runs; and a held-out assertion that
compared `null == null` and passed vacuously.

**A negative control is necessary and not sufficient.** `total=0 passed=0` is
indistinguishable from "correctly failing". Every task needs a positive control —
a hand-written correct implementation proving the grader can go green — and ideally
an adversarial one proving the trap fires.

## Cross-stack hash equality is NOT achievable, and should not be a goal

Two independent measurements say the same thing from different directions:

- **TypeScript CAN match Rust bit-for-bit.** Its `SimRng`, serve velocity and FNV
  digest were verified identical against a standalone rustc reference (V8's
  `Math.cos/sin` + `fround` matched Rust's libm f32 exactly).
- **Unity cannot, and the cause is the runtime, not the port.** A one-ULP
  divergence at tick 53 (`167.447052` vs `167.447067`) survives every source-level
  fix. Operand reordering was tested in a strict per-operation f32 model and is a
  provable no-op — IEEE-754 multiply is commutative — while merely hoisting a
  local moved the first divergence 12 ticks *earlier*, changing 354 of 401 trace
  lines. That is a rounding-point move, not an arithmetic change. The remaining
  candidates are both Mono/ARM64 behaviours: FMA contraction in `X*X + Y*Y`, and
  where `(float)Math.Sqrt(...)` rounds relative to the divide.

**Design consequence: require determinism WITHIN a stack, never ACROSS stacks.**
Within-stack bit-exactness is what replay, rollback and desync detection actually
need, and all four achieve it. Cross-stack bit-identity is a property of the float
pipeline, and on Mono it is not reachable from source. Any starter or eval that
diffs hashes between stacks will report a false difference; diff traces within a
stack instead.

Record it as a finding about the stacks rather than papering over it: identical
source can round differently on a different runtime, and that is exactly the kind
of thing a four-stack comparison exists to surface.

---

## The whole-game matrix runs under a DIFFERENT permission config — not comparable to the 24-trial bake-off

The published cross-stack bake-off (3 tasks x 4 stacks x 2 trials, Opus, ~$65) ran with
`--permission-mode acceptEdits` and **no Bash allowlist**. Measured from its stored
trial JSONs:

| stack | n | denials | per trial | turns/trial | % turns lost | range |
|---|---|---|---|---|---|---|
| rust | 6 | 83 | 13.8 | 44.5 | 31.1% | 9-21 |
| ts | 6 | 76 | 12.7 | 41.5 | 30.5% | 9-16 |
| godot | 6 | 77 | 12.8 | 44.0 | 29.2% | 10-19 |
| unity | 6 | 66 | 11.0 | 39.2 | 28.1% | 6-18 |
| **all** | **24** | **302** | **12.6** | **42.3** | **29.8%** | 6-21 |

**Zero of 24 trials escaped it.** Roughly three turns in ten were spent on a denied
Bash call. The spread across the four stacks is 3 percentage points, so it was a
*uniform tax, not a per-stack bias* — the earlier speculation that it might favour one
stack (Rust agents issue more raw `cargo` calls) is not supported by the data.

The whole-game matrix adds a targeted allowlist: `Bash(just *)`, `Bash(cargo *)`,
`Bash(pnpm *)`, `Bash(git *)`. Not `bypassPermissions`, not a catch-all — only the
build and verification commands the templates themselves instruct the agent to run.

**Consequence: turn counts, costs and wall-clock from the whole-game matrix are NOT
directly comparable to the published bake-off.** The bake-off stands as a historical
run under the old configuration. Any comparison across the two must either exclude
denied turns from the older numbers or be stated as confounded.

Why it matters beyond bookkeeping: in the whole-game calibration trial the agent was
denied `just verify` itself and finished saying two checks were unrun — while the repo
it left behind passed the gate in five seconds. **An agent blocked from its own
verification command will under-report its own completeness**, which is precisely the
signal `self_verify` exists to measure. Any reading of "the agent stopped with a red
gate" under the old config has to account for the possibility that the agent could not
run the gate at all.
