# Decisions

What is decided and why. Current state only.

**[user]** = decided by the project owner. **[agent]** = routine judgement call made in the work.

---

## Scope

| Decision | By |
|---|---|
| 2D **and** 3D, local **and** multiplayer, macOS/iOS/Windows | [user] |
| Console support is **aspirational**, not gating | [user] |
| Open source preferred, not mandated | [user] |
| No stack is mandated — everything is compared empirically | [user] |
| Deliverable is the **full loop, run autonomously** | [user] |
| Netcode: **Elixir for meta-services, Rust for realtime** | [user] |
| Determinism is **enforced**, not encouraged | [user] |

Determinism drives the clippy bans, the boundary tests, and the replay hash chains. The requirement
is **within-stack** determinism only — cross-stack hash equality is not achievable and is not a
goal. Unity's 1-ULP divergence is a Mono/ARM64 property (FMA contraction) not reachable from source.

## Stacks under measurement

Four, each with its own fine-tuned template: **Rust + Bevy 0.19**, **TypeScript + three.js**,
**Unity 6**, **Godot 4.7**.

Each template is tuned to its own stack's strengths rather than parity-ported, so agents get the
best chance of success on their stack's own terms. Tasks are held similar across stacks so the
comparison stays fair.

Eliminated: Unreal (binary assets an agent cannot diff, multi-minute compiles), Zig/Stride/Flax/
KorGE/O3DE (pre-1.0 churn, near-zero training density). See `research/DECISION.md`.

Godot needs a display server for render verification — `--headless` genuinely cannot capture, but
windowed capture works. Material, not disqualifying.

## How measurement works

| Decision | By |
|---|---|
| Evals run the **`claude` CLI directly**, not the SDK | [user] |
| Building agents run on **Opus** | [user] |
| Tasks are **whole-game builds** ("build 3D Tetris"), not spec changes | [user] |
| A **hidden judge** grades gameplay and codebase quality; building agents must not know how they will be graded | [user] |
| The **template layer and judge layer are distinct** | [user] |
| Tasks are **independent**, run in **parallel**, in the **background** | [user] |
| Prompts are **semantically identical but stack-native**, not byte-identical | [user] |
| `--setting-sources project` is mandatory | [agent] |
| **Stack-native covers stack facts, never harness facts.** A mechanism wired identically in all four starters must be described in all four guides | [agent] |

Byte-identical prompts are not neutral — they end up written in one stack's vocabulary and bias the
comparison. `--setting-sources project` is empirically verified: without it the operator's global
`~/.claude/CLAUDE.md` leaks into every arm.

The third row is where that principle was being over-applied. "Stack-native" is what licenses four
different Bevy/three/Unity/Godot API sections and Godot's headless limitation — things true of one
stack. It does **not** license one arm knowing about the Stop hook while three do not, which is
what happened for as long as the hook existed (task 78): `.claude/hooks/verify-gate.sh` and the
`"Stop"` wiring are byte-identical across the four trees, and only `starters/rust/AGENTS.md` said
so. Wording still differs per stack; silence is the thing forbidden. Enforced as an axis rather
than a habit — `judge/starter_parity.py::mechanism_findings`, keyed on **every event wired in
every starter**, so the next hook is covered by the rule that caught this one.

**A harness mechanism whose success path is silent records what it DID, outside the tree it
acts on.** The Stop gate was the case: exit 0 leaves nothing in the transcript, so "the gate is
live in all four arms" had only ever been established from the file existing (task 78). The four
hooks now append `invoked` plus a verdict to `$STARTER_HOOK_LOG`, which `wholegame.py` addresses
into the trial's **artifact** directory and never into the trial tree — the tree becomes the
graded diff, and a log written there is #106's contamination wearing an audit trail's clothes.
The address is asserted in code before launch and the outcome re-measured per trial, because
those are two different questions. The guides were deliberately not told: it changes nothing an
agent should do, and telling it would be an observer effect on the thing being measured.

## What the task asks for

| Decision | By |
|---|---|
| **The arena task is 3D, analog and spectacular** — a bounded volume, movement and aim on all three axes, continuous −1..1 input, gamepad and mouse, three behaviourally distinct enemy kinds, materialisation before an enemy is dangerous, a score multiplier, and stated on-screen requirements | [user] |
| Tasks require **audio** — looping music, a distinct effect per declared event, a `just audio-manifest` contract | [user] |
| Tasks require **presentation and experience** — a game someone would want to play, not a demonstration that the mechanics exist | [user] |
| Everything the player sees **must appear in `just film` frames** | [user] |

The first matrix produced an exact 24-way tie: four well-built templates on Opus solved
everything put in front of them, so there was no variance left to resolve. Audio and
presentation are added because they are work the templates do **not** pre-solve — no
starter ships a single sound, and none shipped a HUD example that reached the frame
capture until 2026-08-14.

**Runs before and after this change are not comparable on any tier.** The task is
different, tier 1 has 14 criteria instead of 9, and tier 2 has one more. Same treatment
as the allowlist change.

The **arena rewrite of 2026-08-15** is a second, narrower break and applies to `g3_arena`
alone: tier 2 goes from 15 criteria to 22, and the eight arena submissions built before it
answer a different question. They are archived rather than discarded — they are the only
arena data under the $48 regime — and the 3D set is graded separately. Its play-bot is
rewritten and twelve of the new criteria are pinned by mutants; the analog criterion caught
a real defect on its first run, in the reference fixture's own probe.

## Matrix configuration

| Decision | By |
|---|---|
| **Targeted Bash allowlist** — `just`, `cargo`, `pnpm`, `git`. Not `bypassPermissions` | [user] |
| **2 trials per cell — 24 trials** | [user] |
| Engine-heavy selections (godot/unity) build at **`--parallel 2`**, not 4 | [agent] |
| **`--max-turns 1000`, and NO budget cap** | [user] |

`--max-budget-usd` is **visible to the agent and instructs it** — spend rose 1.54× on Tetris when
the stated ceiling went from $25 to $48. `--max-turns` is invisible and merely truncates. Any
stated budget is an instruction, so only an absent one is neutral; 1000 turns bounds a trial near
$130, which is a runaway backstop rather than a ceiling.

Cost under this configuration is **unmeasured** — every prior figure was taken with a budget
instruction in force. Calibrate before committing a matrix. See `eval/PROTOCOL.md`.

**Runs under different caps are not comparable** on cost, turns, or anything downstream of how
much work the agent chose to do, and every cost figure this project has published is partly a
measurement of its own cap. Treat any change to the pair as a task change. The regimes so far are
$25, $48, and (from now) none.

**The 250-turn limit had already become the binding constraint at $48**, which is what prompted
raising it: `g3_arena__rust__t1` stopped at 251 turns and $35.75 with $12 of its stated budget
unspent (FINDINGS #35). At that point the run was governed by the invisible flag while appearing
to be governed by the visible one — the inverse of the regime the $48 cap was chosen for.

Without an allowlist, agents lose ~30% of turns to denials — including being blocked from running
their own verify gate, which makes them under-report their own completeness. The allowlist cuts
that to 9.8%. It does **not** reduce cost: per-trial spend is unchanged, so it buys better-verified
output rather than cheaper output.

Runs with and without the allowlist are **not directly comparable**.

## Grading

Three tiers. Blinding is verified mechanically by `eval/judge/verify_blind.py`.

| Tier | Weight |
|---|---|
| Programmatic — builds, gate green, lints, tests, frames render and animate | **GATE** — pass/fail, not scored |
| Play-bot — a scripted bot drives thousands of ticks and asserts the game plays | **1.00** |
| LLM judge — one specialist per aspect, each ranking a whole eight-submission field | **0.00** — diagnostic only |

### Tier 1 gates, it does not score — decided 2026-08-23

`overall = tier2`. Tier 1 held **0.31** from this repository's first commit until then, quoted in
four documents and derived in none of them; git history holds no derivation either, so there was
nothing to state and the question became what the tier is for. Two offline sweeps, both able to
come out the other way, and both re-runnable:

- `eval/judge/weight_sensitivity.py --all` — **FLIPS=0** at every weight in (0,1), but **7 of 10
  groups UNIDENTIFIABLE**: tier 1 returns one value across the whole group, so the weight is inert
  for the reason that matters least (#92). It sweeps the *open* interval, and the gate regime is
  w1=0, so this tool cannot settle what the change does — see the next one.
- `eval/judge/tier1_census.py` — 68 stored submissions, **7 with any tier-1 failure**, and in **0 of 10
  groups do both tiers vary among the trials tier 2 could measure**. Comparing the two schemes
  pairwise at w1=0: **0 orderings reversed, 3 coarsened, 7 identical** (#123).

Five of those seven failures were a lint finding, three of a submission's own unit tests, and one
ink-coverage window, on games that all scored **1.000** on tier 2; the other two were the #49 build
failure, whose tier-2 zero is the same fact told twice. Tier 1 is a floor test and is now reported
as one: `gate: PASS`, or `FAIL` with the failing ids. **A gate failure does not deduct and does not
exclude the trial** — deducting restores what was removed, excluding is a reason not to count a
failure (rule 7). `build.compiles` and `probe.responds` are marked *blocking*, because the play-bot
drives through `just probe` and cannot produce independent evidence without them.

`RUBRIC.md` carries the full derivation and the condition that re-opens it: the census prints
`DISCRIMINATES` the moment a tier-1 criterion with real headroom exists. **Stored scores were not
rewritten** — 14 of 68 would move, largest 0.2273 — and the regime boundary is in `eval/RUNS.md`.

**The judge is unweighted for two independent reasons, either sufficient:**

1. **It cannot reorder anything.** Bounded contribution 0.0154 against a tightest adjacent gap of
   **0.0667** — recomputed on tier 2 alone after tier 1 left the score, per game over the 24
   `wg-matrix` records; dropping tier 1 widens every gap. Holds regardless of noise. (The older
   0.0622 is not reproduced by that method and its own method is unrecorded; `JUDGING.md` has the
   table.)
2. **It is noisiest exactly where it would matter.** Score spread 0.308 and instability up to 0.462
   on a contested submission, against 0.000 on an uncontested one. Holds regardless of weight.

Its per-criterion verdicts are still reported and are genuinely useful — it catches surviving
placeholders, tautological tests, and pixel-identical frames that no deterministic tier sees.

**The general result behind this** (FINDINGS #21): *an LLM judge's verdict stability is a property
of the artifact, not of the rubric.* Criteria agree when the answer is obvious and diverge when it
is borderline — so validating a judge on clear-cut fixtures systematically overstates its
reliability, and the reliability you measure is highest exactly where you need the judge least.
Rewriting the three unstable criteria did not fix it; the rewrite made a contested submission
*less* stable.

### A saturated tier 2 is reported as a completion certificate, not repaired — decided 2026-08-23

Tier 1 becoming a gate left `overall = tier2`, and tier 2 is itself at the ceiling. **This is
accepted as a property of the current task set rather than treated as a rubric defect**, because
both repairs available inside the rubric were measured and neither works.

`eval/judge/tier2_census.py` is the producer — the analogue of `tier1_census.py`, 17 expectations
including a positive control, a variant and three mutants. Over 68 stored trials:

- **5 of 10 (run, game) groups return a single tier-2 value** across every measurable trial:
  `wg-audio` g1/g2, `wg-audio48` g1/g2, `wg-g4c` g4 — **35 of 68 trials**.
- 11 trials failed anything; **2** were whole-trial (the #49 build failure, one fact recorded N
  times) and **9** were selective. **All 9 selective failures are from `wg-matrix-2026-08-13`.**
  Tier 2 has not separated two submissions in any run since.
- **Promoting a withheld diagnostic cannot help.** `layer.clears`, `score.rewards_clears` and
  `stage.completes` take a single value — `False` — on all 7 group-criterion pairs where they are
  recorded, so scoring one lowers every submission in its group by the same amount and leaves the
  ordering as flat as it was.
- **Nor can more criteria of the same kind.** Four candidates, each drawn from a requirement the
  g4 prompt states and no criterion checks, were driven against all 8 `wg-g4c` submissions:
  attack cannot be re-triggered mid-swing, enemies patrol, the `land` event fires, and replay
  determinism under a played 900-tick tape instead of the idle 300. **8/8 pass on every one**, and
  the reference passes them too, so they can go green and nothing goes red (#128).

> A binary criterion asks whether a mechanic exists. When every submission implements every
> mechanic, a tier made of them returns one number — and it is right to.

**So on a saturated group `overall` certifies completion; it does not rank.** No stack ordering may
be drawn from one at any gap, which is the same bar the within-cell result already sets below —
this is a second, independent reason for it, arrived at from the tier rather than from cell
agreement. Trials in a saturated group are still reported, still gated, and still judged.

**What it costs, named.** 35 of 68 stored trials — including all 16 of `wg-audio48` and all 8 of
`wg-g4c` — bought a certificate rather than a ranking, at trial prices in `eval/RUNS.md`. The
fourth game is the sharpest instance: `g4_platformer` was added because *"Pong, Tetris and arena
all tied; a game exercising different systems is the most plausible remaining route to
discrimination"* (below), and **20 of its 20 scored criteria have never failed**. The route was
plausible and it is now measured closed.

**What re-opens this**, in the tool rather than in prose: `tier2_census.py` prints `SEPARATES` the
day no group is flat. The remedy it points at is a **harder task**, not a longer rubric, and that
is a separate decision with its own spend — filed, not taken here.

### The tier-3 separation figure is reported under `rank` + `pool` — decided 2026-08-23

*"Does an aspect separate the stacks?"* is answered by a between-stack range against a
within-stack gap. **That quantity has two free parameters, not none.** `value` is what a round
asserts about a submission — its `score`, or its `rank` in the field. `order` is whether the
rounds are averaged before the spread is taken (`pool`) or after (`perround`). Four
combinations, four different numbers, and they disagree about the sign.

`eval/judge/field_ranks.py` is the producer. **Every published figure for this quantity must
come out of it and must be quoted with the field, the `value` and the `order`** — a pair quoted
without its method names one of four quantities, which is how a pair matching none of them came
to be published in four documents at once (#113).

**There is a third parameter and it is the POPULATION.** A directory of rounds is not one
population: `fun_frames` is `fun`'s control, its scores mean something only against `fun`'s, and
pooling it is rule 4. Decided 2026-08-23 (task 90): a control **declares itself to code** —
`Aspect.control_for` in `eval/judge/aspects.py` — a pooled figure covers the **scored aspects
only**, and `field_ranks` names the aspects each figure is over in its own output. The guard is
`field_ranks.assert_poolable`, which raises rather than silently dropping, and an aspect id
`aspects.py` does not define is treated as **unmeasurable rather than scored**. Before this the
rule was a prose comment naming a field that was never set and read by nothing;
`runs/wg-aspect-reliability` pooled 30 rounds of which 5 were the control. No published figure
moved — `wg-tetris-judge-2026-08-17/pre` and `/post` hold no control rounds, and both reproduce
to the digit.

**When one pair is quoted, it is `rank` + `pool`.** Three grounds:

1. The tier's output is an **ordering** — each specialist ranks a whole eight-submission field.
   Ranks are the units the layer asserts; the scores are an intermediate.
2. The scores **ceiling**. On seed 1, `architecture` puts 7 of 8 submissions on one score and
   `audio` and `idiomatic` put 6 of 8 (`JUDGING.md`, gate 1). A between/within comparison on a
   saturated scale is compressed by the saturation; a rank comparison is not.
3. `pool` is the population the documents already meant. The withdrawn line's own words were
   *"pooled over five aspects and both orders"*, and `README.md`'s replacement is pooled.

`JUDGING.md`'s two per-aspect tables stay under `score` + `perround`, which is the only method
that reproduces them, and are now labelled with it. **Mixing methods in one section is
acceptable; mixing them unlabelled is not** — and note that a `pool` figure is *not* the mean of
any per-aspect table, so the two must never be presented as summarising one another.

### A harder task is PRICED here, and gated behind a free pre-test — decided 2026-08-23

Tier 2 is the only scored tier and it saturates, so the remedy proposed has been a harder task.
**A harder task costs a matrix, so this entry brings the price and the one measurement that
decides whether the money would buy anything. The spend itself is the operator's call and is not
taken here.**

**First, the corpus is flatter than the group count says.** Tier 2 has produced **no selective
failure anywhere in the 68-trial corpus that survives adjudication.** `wg-matrix-2026-08-13` is
the only run where tier 2 ever separated submissions, and its 9 selective-failure trials carry
**38 criterion-failures**: 22 are a probe that died before tick 0 (both Unity arena trials,
detected by signature), and the other **16 are every entry in `ADJUDICATED` in
`eval/judge/audit_criteria.py`, all 16 marked `false_negative`** — the criterion fired on correct
work. The **7 distinct criteria** involved (`ball.wall_bounce`, `move.translates`,
`piece.stacks`, `gameover.triggers`, `determinism.replay`, `determinism.seed`, `enemies.chase`)
are each marked `REPAIRED` in `CONSTRUCTIBLE_FAILURE` in the same file, for that reason.
`python3 eval/judge/discrimination.py eval/runs/wg-matrix-2026-08-13T14-02-50` prints an
**ADJUDICATED spread of 0.0000 in all three games**, against a raw 0.2308 / 0.3077 / 0.7333.

The same thing is visible without adjudication, on one field, across one day: `wg-g4c-capgate`
re-grades the eight `wg-g4c` work trees, and `g4_platformer__ts__t0` scores **14 of 20 on
2026-08-22 and 20 of 20 on 2026-08-23** — the same submission, the same 20 criteria, the
play-bot repaired in between. **Observed tier-2 spread has tracked the play-bot's false-negative
rate, not the submissions.**

**Second, the reason it saturates is structural, and it constrains what a harder task must be.**
Every tier-2 criterion is derived from a bullet the prompt states; agents build to the prompt; so
the tier returns one value by construction. **The prompt is tier 2's answer key.** Four more
criteria of that family were measured against the `wg-g4c` trees and passed 8/8 (task 65). It is
not a shortage of criteria.

**Third — and this is what decides the design — the criteria are not short of resolution.** Over
the eight `wg-g4c` submissions, **16 of the 20 scored criteria already record more than one
distinct numeric evidence vector, and 8 of them record eight distinct vectors on eight
submissions.** The underlying measurements discriminate perfectly. What they discriminate on is
the problem:

| criterion | what its numbers vary over, across the 8 submissions |
|---|---|
| `attack.faces` | hitbox offset, 22.0 to 32.0 px |
| `jump.leaves_ground` | rise in 8 ticks, 44.6 to 66.8 |
| `invuln.window` | i-frame gap, 43 to 80 ticks |
| `enemy.damages_player` | starting health, 4 or 5 |
| `player.falls` | first platform edge, x=300.0 to x=560.0 |
| `player.walks` | walk distance in the window, 143.2 to 182.5 |

Every one is a **free design parameter the prompt does not give a direction for.** Scoring any of
them ranks the four stacks on jump height and hitbox width.

> **A criterion has headroom only if the quantity it observes lies on an axis the prompt names a
> DIRECTION for.** A stated mechanic gives an axis with no direction and every submission at the
> same point; a free parameter gives an axis with no direction and every submission at a
> different point. Neither is a quality scale. Adding resolution to a criterion on an
> undirected axis manufactures a ranking out of design freedom.

**The one criterion with headroom is `stage.completes`, made graded rather than binary** — the
fraction of the stage the bot reaches. Three tier-2 criteria sit at the **floor** rather than the
ceiling, and all three are `diagnostic_only` for the same reason, that the bot cannot play well
enough: `layer.clears` and `score.rewards_clears` (tetris, `False` on all 19 trials where
recorded) and `stage.completes` (platformer, `False` on all 8). **`stage.completes` is the only
one of the three whose underlying quantity is a fraction on a directed axis.** A line was either
cleared or not; there is no meaningful "how far towards a line". The stage has a length, the goal
is at the end of it, and the prompt states the direction — *"Reaching the far end of the stage
clears it."*

**The free pre-test has run — task 83, 2026-08-23, published as #139 — and it answers both
questions: do not buy the harder task, and do not promote the criterion.** It cost no trials: the
eight `wg-g4c` work trees survive under `~/game-research-work/` and were re-driven offline.

The bot was first repaired until it could actually pursue the goal — cross the pits with a **held**
jump, stop at swinging range and kill what stands in the way — in four steps, each measured on all
eight. `stage.completes` remains `False` on all eight; these are the fractions of the goal reached:

| | `godot t0` | `godot t1` | `rust t0` | `rust t1` | `ts t0` | `ts t1` | `unity t0` | `unity t1` |
|---|---|---|---|---|---|---|---|---|
| bot as shipped | 0.225 | 0.143 | 0.206 | 0.290 | 0.256 | 0.178 | 0.158 | 0.203 |
| **bot repaired** | **0.803** | **0.591** | **0.417** | **0.609** | **0.686** | **0.274** | **0.617** | **0.401** |

**Not all eight at 1.000 — none of them reaches it — so the goal is not too easy, and a harder
task is not justified on this evidence.** The numbers are spread, and the spread is nonetheless
**not** the discrimination the old first row promised, for two measured reasons:

- **The ordering is not stable under a change to the instrument.** Spearman ρ between the shipped
  bot's ranking of the eight and the repaired bot's is **0.405**, exact permutation p = 0.163 over
  all 8! orderings — at n=8 the old ranking carries no demonstrable information about the new one.
  `godot t0` moves 6th → 8th, `unity t0` 2nd → 6th, `godot t1` 1st → 4th.
- **8 of 8 runs end having taken exactly `hp0` hits, with no victory.** The run length is set by
  the health pool, so the scalar is `(health pool × distance travelled per hit taken) ÷ goal_x`.
  Health pool is 4 or 5, `goal_x` is 2300 to 3500, distance-per-hit is set jointly by enemy spacing
  and by how badly the bot fights. **Two free design parameters over a third** — the fraction is on
  a directed axis, but the quantity that terminates the run is not.

> **The three-way pre-test was missing a cell, and it is the cell the measurement landed in: a
> spread that moves when the instrument does.** *Spread ⇒ the tier can discriminate* is sound only
> if the spread is a property of the subjects. Ask of any new scalar not merely whether it
> separates, but whether **improving the instrument reorders it**. That check is free, it runs
> offline, and here it came out against the hypothesis it was built to support.

Two things the repair does establish, and both are worth keeping:

- **The levels were never the constraint** (#139). Every gap in all eight is crossable by the submission's
  own physics: measured jump reach with the control **held** is 93.5 to 141.8 units against a
  widest gap of 110, while a one-tick press reaches 29.0 to 88.4. A variable-height jump is
  answered by how long the control is held, and the bot had been asking every submission for its
  shortest possible arc.
- **`ref_platformer` could not have caught that.** `stage.completes` passes on the reference under
  the broken bot *and* the repaired one, because the reference is a level the shipped bot clears by
  construction. `eval/G4-PLATFORMER.md` predicted this in writing — "it says nothing about whether
  it traverses eight unknown level layouts" — and the numbers now confirm it. A control that shares
  the assumption it is controlling for (#37).

**To re-open promotion:** the three awkward reference levels the rubric already demands, **and** a
bot that does not terminate on health exhaustion in 8 of 8. Until then the criterion measures how
long the instrument survives, not how much stage there is.

**The price of the alternative, read from `eval/RUNS.md` on 2026-08-23.** Judge spend is **$0** —
tier 2 is deterministic and tier 3 carries no weight — so this is agent trials only:

| | |
|---|---|
| one clean 8-cell field, standing regime (no cap, `--max-turns 1000`, `--parallel 2`) | **`wg-g4c` — $421.00**, 8/8 `completed`, per trial $36.16 to $77.60, wall 55.7 to 86.3 min |
| the last game actually added, all in | **$698.21** — `wg-g4` $211.64 (stopped at 4 of 8) + `wg-g4b` $65.57 (8/8 `api_error`, a null) + `wg-g4c` $421.00. **Two of the three runs produced nothing gradeable** |
| raising the bar on an existing game instead | the same order. The arena rewrite's field, `wg-arena3d`, was $374.05 for 8 `completed` — but that run straddled the #49 machine repair, so its *cost* is contaminated as well as its grades and it is not a clean price |

**So a fifth game, or a raised bar, is $421 if the first field lands clean and $698 at the only
precedent we have, n=1.** Engineering cost — prompt, play-bot, mutants and variants — is on top
and is unmeasured; nothing in this project counts it.

**The ordering was the decision, and it paid for itself.** The pre-test ran first because a matrix
bought before it would have been bought on the assumption that a graded criterion discriminates —
and that is precisely the assumption the pre-test refuted, for $0 and one afternoon, against a
$421-to-$698 alternative.

## Task set and judging protocol

| Decision | By |
|---|---|
| Add a **fourth game: a 2D sprite platformer with attacks** (Castlevania-style) | [user] |
| `stage.completes` is **diagnostic, not scored**, until it passes three awkward reference levels | [agent] |
| Subjective judges **run repeatedly until the decision resolves**, not a fixed number of times | [user] |
| The judging layer **stays in Python** — no Workflow port for now | [user] |

The platformer stresses machinery the other three games do not: sprite sheets and animation state
machines, attack hitboxes with active frames, knockback and invulnerability windows, platform
collision. Pong, Tetris and arena all tied; a game exercising different systems was the most
plausible remaining route to discrimination. **It has now been run once and it tied too** — all 8
`wg-g4c` submissions score 1.000, and 20 of its 20 scored criteria have never failed (#128). The
hypothesis was worth testing and is answered: different systems do not separate these stacks.

Repeated judging resolves per **pair** with a Wilson interval, not per score, and stops sampling a
pair once it resolves. Protocol and its limits are in `eval/judge/JUDGING.md` — including that at
affordable N the instrument can detect an ordering but **cannot statistically prove a tie**, which
is the outcome this project is most likely to reach.

## What the deterministic tiers may and may not be used for — decided 2026-08-16

**Decided [agent], on measurement, and it constrains every claim this project can make.**

Comparing the two independent trials in each cell criterion by criterion, **per run and never
pooled**: `wg-matrix` (3 games, 436 paired criteria) differs on **5** verdicts against **332**
differing evidence strings; `wg-audio48` (232 paired) on **0** verdicts against **120**. The two
submissions in a cell are different artifacts and the instrument mostly returns the same grade on
both — "mostly", not "never".

| may be used for | may not be used for |
|---|---|
| establishing that a submission works — it caught a game that does not compile and two whose own gate is red | ranking stacks, at any gap |
| catching a criterion that cannot fail (mutants) or one that fails correct work (variants) | claiming two stacks are equal — a null on an instrument with no within-cell resolution is not evidence of equality |

**A stack-correlated pattern remains an instrument defect until a mechanism is named in the
code. That is now five for five** (#25, #26, #28, #43, #49), and the fifth is the entire
spread of the arena matrix.

Consequences already applied:

- `wg-arena3d`'s numbers are **not comparable across stacks** — the run straddles a machine
  repair whose split is exactly the stack split. `eval/RUNS.md` carries the detail.
- The agent's closing message must be read before grading, and since 2026-08-23 the harness
  reads it: `wholegame.py report` prints each trial's located passages beside its score, via
  `eval/tools/disclosure.py`. It reads `artifacts/<trial>/agent_result.json` → `.result`
  **whole**, never `agent.final_text`, which is that message's last 3000 characters — and
  `wg-arena3d`'s own disclosure of this mechanism sits at character 0 of 3912, where the
  truncated field cannot see it. It is a locator, not a classifier; `quiet` is not a verdict
  and `no message` is a third value, not silence.
- The work root is no longer under `$TMPDIR`, which reaped the artifact under measurement
  (#45), and `assert_work_root_sane()` refuses any ephemeral path.

## Where instructions live

Instructions to agents are **written in files, not delivered in messages**, so they can be improved
across sessions rather than re-invented each time. See `AGENTS.md`.

| Instruction | File |
|---|---|
| Launching, watching and stopping a run | `eval/PROTOCOL.md` |
| The subjective layer and its gates | `eval/judge/JUDGING.md` |
| Criteria, tiers and weights | `eval/judge/RUBRIC.md` |
| Every run's cost and comparability | `eval/RUNS.md` |

### One real copy of each skill, at `.agents/skills/`, reached by symlink — decided 2026-08-23

`.agents/skills/<name>/SKILL.md` holds the **only real copy** of each skill. `.claude/skills` is
a **symlink** to that directory. `docstat.py --sweep` exits 1 on any real `SKILL.md` outside the
authoritative root, and also on a `.claude/skills` that is missing, dangling, or a real directory.

`.agents/` is the cross-tool convention — the same one that makes a root `AGENTS.md` readable by
several agent CLIs — so Codex, Claude and anything else read one source rather than a copy each.
**No `.codex/skills` or `.Codex/skills` exists as a real folder**; a second path to the skills is
a symlink or it is nothing.

**This is not a reversal of #99, it is that finding's own escape clause.** #99's objection was
never to a location. It was to a **copy**, and its three measurements still stand: the only
Codex-adjacent sibling — `game-research-gpt` — has no `.agents/`, no `SKILL.md` and no root
`AGENTS.md`, so it was never a reader; the mirror was **never once in sync**, with `add-game` 39
lines short in the initial commit and `tasks` and `prune` absent entirely; and after the initial
import it took **0 edits that changed a procedure, against the authoritative tree's 6**. The
finding closed by saying *add a pointer, never a copy*. This inverts which end holds the pointer
and leaves the count of copies at exactly one. A symlink has no second file to get edited.

**Which end holds the real files was decided by measurement, not by preference.** Against
`claude` 2.1.220, one uniquely-named probe skill per layout, every tool but `Skill` denied so the
content could not arrive by reading the file:

| layout | skill loads? |
|---|---|
| real `.claude/skills/<n>/SKILL.md` (the old layout, positive control) | yes |
| real `.agents/skills/`, `.claude/skills` a symlink to it — **shipped** | yes |
| real `.agents/skills/`, `.claude/skills/<n>` each a symlink | yes |
| real `.agents/skills/` only, no `.claude/skills` (negative control) | **no** |
| real `.claude/skills/`, `.agents/skills` a symlink to it | yes |

The whole-directory symlink was chosen over the per-entry one because it needs no upkeep: a new
skill is one new directory, where the per-entry layout would need a matching symlink added by
hand every time, and a rule you have to remember is a rule that will fail.

**The negative control is why the gate checks the pointer.** Claude Code does not discover
`.agents/skills` on its own. With the symlink deleted the nine skills are still present, still at
the authoritative address, and every file-counting check reads clean — while no agent can load
one. `eval/tools/skill_layout_control.py` pins the gate red on all five ways this breaks: a real
copy elsewhere, a copy at the wrong nesting depth inside the authoritative root, the pointer
deleted, the pointer dangling, and the pointer replaced by a real directory of copies.

**The mirror came back by a git merge, not by outside tooling.** After the 2026-08-23 deletion,
`.agents/skills` reappeared, tracked, as nine pure additions in the commit merging task 101 —
a branch forked before the deletion, so the merge restored what it had never seen removed. It is
worth knowing because the diagnosis on sight was "some tool outside the repository regenerates
this", which would have been unfixable from inside the repo; the true cause is ordinary and the
layout is now merge-safe, because a branch carrying a real `.claude/skills/` directory conflicts
with the symlink rather than silently shadowing it.
### The documentation is gated on structure and on names, never on prose — decided 2026-08-23

Eleven documentation linters were measured against this repository and produced **over 14,000
alerts and two defects**. Both defects came from tools that check *structure or schema*; every
prose rule that fired was house style, a false positive on this project's vocabulary, or a
readability score. `research/11-doc-linting-for-agents.md` has the per-tool numbers.

So no prose linter, no readability gate, no `markdownlint` config. `eval/tools/docstat.py
--sweep` is the whole gate, and it asks only two things:

| | question | bought with |
|---|---|---|
| **references** | does a flag, aspect or criterion a doc names exist? | `RUBRIC.md` named five judges that do not (#38) |
| **census** | does a doc claiming to name every aspect name every aspect? | `RUBRIC.md` and the `evaluate-run` skill said five while `ASPECTS` held six and `--aspects fun_frames` was accepted (task 79) |
| **structure** | does the file parse as the thing it is read as? | 5 of 7 skills had unparseable frontmatter; `AGENTS.md` rules 10-16 detached from their own list |

**References and census are the two directions of one question, and the second is the one that
hides.** A doc naming a judge that does not exist is caught the moment anyone looks for the
name. A doc *denying* a judge that does exist resolves perfectly, reads as authoritative, and
costs the reader the control they never ran — `--sweep` printed `6 aspects known` and exit 0
for as long as two documents said five. A census claim is only visible because somebody
**declared** it exhaustive, which is the same mechanism the withdrawal register rests on.

**The census trigger is scoped to the PREDICATE, not to the quantifier, and that is a measured
choice rather than a stylistic one (task 92, #140).** It shipped as three alternations — the three
wordings the two defective documents happened to use — and of 14 planted census claims, each
false in exactly the way the check exists to catch, it fired on **2**. These two passed:

```
The five judge aspects are `architecture`, `audio`, `fun`, `idiomatic` and `ux`.
There are five aspects: `architecture`, `audio`, `fun`, `idiomatic`, `ux`.
```

The obvious repair fails harder: a trigger built on the quantifier, a cardinal or `all`
governing `aspects`, caught 10 of the 14 and turned **26 correct live lines red, with no true
positive among them** — in this corpus a counted plural `aspects` almost always describes what
*ran*, *cost* or *failed*, as in DECISIONS.md's own `All five aspects were run over a full
eight-submission field`. What a census has and a run description does not is an existence,
identity or definition predicate in the present tense with the enumeration adjacent, and
copula / existential / `define` are closed classes, which is what makes that statable as a
property instead of a growing wordlist. **Measured after the change: 14 of 15 plants red, 0 red
across the 152-document swept corpus, and 6 across all 2090 markdown files in the checkout —
all 6 archive-exempt and all 6 true statements of a superseded census.**

> **The fence above is load-bearing, and the widened trigger's first live firing proved it.**
> This paragraph quotes two false censuses as examples, `--sweep` went red on it, and that is
> the check working: a live document may not state a census it does not mean, and the declared
> way to show one is inside a ``` fence, where a line is an example rather than a claim. The
> same exemption is why the archive may quote the superseded five freely.

**What it deliberately still misses, with the price of closing it.** A bare `aspect`-headed
table listing five ids with no sentence above it is invisible. The structural trigger for that
was written and measured at **9 false positives** on live docs — every one a legitimate
per-aspect results table over the subset a particular round ran. Nine false positives to close
a gap that has never occurred is the trade this file already refused when the path check was
deleted rather than tuned quiet.

Two boundaries hold the structure half at 0 false positives, and both are the same rule — *a
gate that fails on correct input gets disabled*:

- It asks about a continuation under a **2+ digit** ordered marker, not about indented blocks in
  general. The general form fires on `tasks/` files where nothing is wrong.
- The **formatting** rules do not read `eval/findings/`, `eval/FINDINGS.md` or `eval/RUNS.md`.
  The archive records what was true when it was written, including the broken shapes it is
  about; reformatting one to satisfy a gate edits evidence.

  This exempts the archive from **house style, not from being findable.** Five checks do read
  it, and each asks whether a citation still resolves rather than whether the prose is tidy:
  a finding number is defined once; every number has exactly one row in the `eval/FINDINGS.md`
  index and vice versa; that index renders as **one table**; every live statement of the
  range — `AGENTS.md`, `README.md` and the index's own opening line — names the same highest
  number; and every live statement of **how many there are** matches how many there are.

  Three of those are ones the others could not see. A blank line between two rows ends the
  table under CommonMark, so the rows below become a second, headerless table that no renderer
  shows as part of the index — while the row count, the set reconciliation and `grep` are all
  unchanged. The range was spelled in three files with only one of them checked, so the
  index was repaired while `AGENTS.md` went on saying `#19-#110`. And **a range is not a
  count**: `#19-#132` is equally true of 114 findings and of 40, which is how `README.md`
  carried a count of *thirty-seven* for eleven days past a green range gate (#134,
  `WR-readme-findings-count`). Each was green on a real defect, so each now carries a red
  control: **`--sweep` runs the pins itself** on every invocation, `docstat.py --selftest`
  prints them, and `eval/tools/findings_control.py` runs the command out of process against a
  tree whose answer is written down first.

### The producer for the findings count is `docstat.py --findings` — decided 2026-08-23

`census.py` counts the stored tree and refuses in an agent worktree, where `eval/runs/` is
gitignored — which is exactly where documents get edited. The findings log is a corpus of
markdown, so its producer lives in the tool that already parses it.

**The gate and the producer are one function.** `_check_findings_integrity` returns
`findings_census(...)["disagreements"]` plus the two things a census does not express: the
index's *structure*, and which lines an over-indexed number sits on. The first draft had two
implementations of the same reconciliation, one gating and one producing;
`findings_control.py --mutate no_count_check` deleted one of them and all ten controls stayed
green. A duplicated mechanism buys half a gate and no way to tell which half was removed.

**A count in a live document must be written in digits.** A cardinal spelled in words is
reported as ungateable rather than ignored, because a digits-only check would let the next
stale figure past by being written out in full — which is what the one real instance did.

**A live document states the range once.** `_check_range_in` validates every occurrence it
finds, so N identical correct copies are N passes: an evil merge duplicated the row in
`AGENTS.md` and `README.md` on 2026-08-23 and `--sweep` was green on both, and the same merge
shape recurred while task 88 was in flight. The cost of the rule is that a document wanting to
state the range in two places must instead point at the one that does.

### A citation of a renumbered finding is reported, never gated — decided 2026-08-23

`docstat.py --renumbered` asks the one question the two above cannot: does a name still *mean* what
its author meant? A finding number reassigned at merge leaves every earlier citation pointing at a
stranger and **still resolving**, so no reference check can see it (#118).

It is a warning in `--sweep` and a command of its own, on the same footing as `tasks.py check`'s
reachability warning. Three reasons, and the first two are why it could not be a gate even if
someone wanted it to be:

- **Only about a third of what it reports is decidable.** The merge that renumbers writes the new
  heading and the closing task's evidence string in one commit, and a commit has no internal order.
  Where the citing author's tree was never committed at all — a collision live in two worktrees —
  history holds no answer of any kind.
- **Its evidence is `git blame`**, which dates the last edit of a line, not the writing of a
  citation. `-w` closes the reformat case. Any other content edit that leaves the stale number in
  place launders it, so the check fails closed: it loses recall, never accuses falsely.
- The undecidable list **contains correct citations by construction** and can never reach zero. A
  permanent block of output that cannot be cleared is how a reader learns to skip a command.

**Never renumber a finding to make it green.** The number in `eval/findings/` is the published one;
the citation is what is wrong. The renumber map is derived from git on every run and is not written
down anywhere — a hand-kept list of moved numbers would go stale exactly like the citations it
describes.

### The undecidable half's verdicts are recorded, because they cannot be derived — decided 2026-08-23

The list that can never reach zero has a second cost: it gives the reader no way to tell a row
somebody has already adjudicated from one nobody has ever looked at. Task 102 read all **51** rows
at that revision — **15 were wrong**, and the other **36** cost a full pass to establish and were
about to cost the next reader the same pass. `_check_renumbered_citations` already exhausts what
history can say about them; what decides a row is reading its sentence against the heading in
`eval/findings/`. So the verdict is **recorded**, in `eval/renumber_triage.json`, on the same
principle as the withdrawal register above: *the only detectable property of an adjudication is
that somebody wrote it down.* `--renumbered` prints `UNTRIAGED` first and the recorded verdicts
after, so what a reader must read is what is new.

**Keyed by the citing text, never by a line number.** A line number is invalidated by any edit
above it, which would unpair every entry in a document and present 36 adjudicated rows as
untouched — a wall of false work, indistinguishable from real work. The anchor must itself contain
the citation, so it cannot drift onto a neighbouring sentence.

**The register gates inside `--sweep`, and only on whether an entry still resolves** — its file
exists, its anchor matches exactly one line, and that anchor contains the citation it claims. The
*verdict* is a judgement and is never re-checked. `eval/tools/triage_control.py` runs 14 controls,
each red demonstrated before the green was believed, plus the two variants that decide the design:
a citation whose line number moved by 40 lines still pairs, and so does one sitting past column
96 — the excerpt `--renumbered` prints is truncated there, and matching against it instead of
against the line put 4 adjudicated rows in the untriaged list on the first run.

### A withdrawal is declared in a register, and the live/archive split is a decision — decided 2026-08-23

A retired figure cannot be found by comparing documents. Its restatements **agree**, with each
other and with the original, to the digit — a cross-document figure-agreement check over the six
live documents found 52 labelled figures, 1 disagreement, and that one a false positive, and it
could not see the withdrawn tier-3 pair it was built to catch (#113). Propagation and consistency
are the same observation. So a withdrawal is **declared**: `eval/withdrawn.json`, one entry per
retired figure or claim, append-only, imported from `game-research-gpt`'s `FINAL-CORRECTIONS.json`
(`eval/IMPROVEMENTS.md`, axis 3). `docstat.py --withdrawn` gates on it.

**The exemption is the entry id and nothing else.** Not a file, not a line — lines move. Not a
marker word: `withdrawn`/`superseded`/`retracted` is an enumeration, and an enumeration already
failed here on one inflection of one verb, where the aspect check exempted `planted` and went red
on `planting`. A live document that needs to state a retired figure cites the id in the same
block, and that is the only way to be green.

**This does not distinguish stating from asserting as current, and nothing mechanical can** — they
are the same characters. It makes the author declare which, in place, for one parenthetical. Three
of the six hits on the day it was installed were legitimate historical prose in a live document,
including `JUDGING.md`'s own withdrawal notice; all three were repaired by adding the id, which
also warns the reader who lands on that line instead of the one who reads 114 lines further down.

**LIVE and ARCHIVE, decided here because a gate with an undeclared scope is a gate whose scope
drifts.** The archive records what was believed when it was written and may state a retired figure
freely; everything else is live.

| | documents |
|---|---|
| **ARCHIVE**, exempt | `eval/findings/`, `eval/FINDINGS.md`, `eval/IMPROVEMENTS.md`, `IMPROVEMENTS.md`, `CLEANUP-LOG.md`, `tasks/`, `eval/runs/` |
| **LIVE**, gated | every other tracked markdown — `README.md`, `DECISIONS.md`, `eval/RUNS.md`, `eval/judge/RUBRIC.md`, `eval/judge/JUDGING.md`, `eval/PROTOCOL.md`, `research/`, `eval/starters/`, `.agents/skills/` |

`tasks/` is archive because a retired figure can be a task's whole subject — task 54's `done_when`
states the pair three times, correctly. The list lives in `ARCHIVE_PATHS` in `eval/tools/docstat.py`
and is asserted against this table by `eval/tools/withdrawn_control.py`, so the two spellings cannot
drift apart silently (rule 12).

**The whole-file archive exemption is the one document-scope exemption in the sweep, and it is
deliberate.** Document-scope is how the aspect check next door once went vacuous — a single
legitimate disclaimer silenced every check in its file. Inside a live document nothing is exempt by
file: the only exemption is an id inside the block, and the block ends at a blank line, at a
blockquote's own blank line, at a fence, or at the next top-level list item.

---

## Open

- **The matrix result.** No stack ranking exists, and the deterministic tiers cannot produce
  one — see above. Tier 3 is the only remaining layer that could.
- **Statistical power.** With 2 trials per cell, if two stacks land within ~0.015 this design
  cannot separate them. The earlier spec-change suite already failed to separate four stacks that
  all scored 6/6.
- **The rubric ceiling — MEASURED and now DECIDED on both tiers, but only one of them is fixed.**
  Tier 1 returned **1.0 on all 24 submissions of `wg-matrix`** and on all 16 of `wg-audio48` —
  40 of 56 matrix trials at the ceiling with *zero* variance, not merely near it (#92). **What to
  do about it was decided on 2026-08-23: tier 1 became a gate** (see "Tier 1 gates, it does not
  score" above, and #123). The ceiling did not go away; it stopped being reported as a score.
  **Tier 2 is still at the ceiling on 24 of 56** — `wg-audio48` and `wg-g4c` entire — and tier 2
  now carries the whole weight, so **`overall` is a constant 1.000 for all 16 `wg-audio48` trials
  and all 8 of `wg-g4c`.** That is the open half, and it is the more serious one: an instrument
  whose only scored tier saturates on a whole run cannot rank anything in it. The remedy is harder
  play-bot criteria or harder tasks, not a weight.
  40 of 56 matrix trials at the ceiling with *zero* variance, not merely near it (#92) — and
  became a gate on 2026-08-23. **Tier 2 is at the ceiling on 5 of 10 groups, 35 of 68 trials**,
  and it now carries the whole weight. That half is not fixed and will not be fixed inside the
  rubric: both in-rubric repairs were measured and neither works (#128), so a saturated group is
  reported as a completion certificate (see "A saturated tier 2 is reported as a completion
  certificate" above). **What stays open is the task**, priced by task 74 — not the criteria and
  not the weights.
- **Whether the subjective layer earns a weight — ANSWERED 2026-08-16, and the answer is no.**
  All five aspects were run over a full eight-submission field for **$33.63** — the sum of that field's own stored rounds. The $46.79 previously here was the whole of 2026-08-16 across two games (#121). Three fail the
  ceiling gate on one presentation order; `fun` and `idiomatic` fail adjudication (#52, #53).
  The redundancy reading — `architecture` and `ux` ranking the field identically while sharing
  no evidence — **carries no weight here and is withdrawn**: it did not replicate, and the
  decision never rested on it (#54, register `WR-arch-ux-redundancy`). And
  **no aspect separates the stacks at a magnitude that could matter**: recomputed by
  `eval/judge/field_ranks.py` over both stored fields of `wg-tetris-judge-2026-08-17`, the
  between-stack range **never exceeds the within-stack gap by more than 23%** across the eight
  readings, on a field the deterministic tiers score identically. Reported pair, `rank`+`pool`:
  **1.900 against 2.275** pre-repair, **2.100 against 1.925** post-repair.
  **This is a magnitude, not a direction, and the change matters.** The bullet used to read
  *"its between-stack range is smaller than its within-stack spread"* — an inequality that
  **reverses in four of the eight readings**, including under the one method that reproduces
  `JUDGING.md`'s own per-aspect table. That argument is retired rather than restated with better
  numbers: a comparison whose sign is decided by a free method parameter cannot license a
  conclusion in either direction. **The weight is unchanged; only its stated reason is.** The
  two grounds under "Grading" above never depended on this field at all — a bounded contribution
  of 0.10 against a tightest adjacent gap of 0.0622, and an aggregate noisiest exactly where it
  would matter — and #83 means neither round is defensible as blind regardless. The withdrawn
  pair is FINDINGS #113; the "within ~10% in both" reading that briefly stood in for it is wrong
  on one of the two fields and is #115. Both stay in the log and appear in no live document as a
  measurement.
  **Tier 3 stays at weight 0.00**, now on measurement rather than on argument. All three
  prerequisites were then BUILT and the layer re-run (2026-08-17, $31.66): `fun` has a
  representative play session and its confound is gone by construction, `architecture` packs
  are extension-blind, `idiomatic` is accepted as within-stack only. **The verdict did not
  change** — only `ux` clears every gate, and gate 0 (reproducibility, added the same day)
  shows ceiling verdicts flipping on provably unchanged input in 3 of 6 clean repeats.
  Re-opening now requires repeats at a fixed order, not more aspects.
  **Verified 2026-08-22 by fingerprint, after a false alarm.** The `fun` rounds were briefly
  reported as having read pre-repair telemetry. They did not. `g2_tetris3d` exists as four stored
  fields in different states of repair, and the wrong one was inspected: `wg-matrix-2026-08-13` is
  `representative` on 0 of 8, but the rounds read **`wg-audio48-2026-08-14`**, which is 8 of 8 and
  was re-driven on 2026-08-17 for precisely this reason. Matched on values rather than on
  reasoning: all **7 of 7** `quiet_fraction_of_run` figures and **4 of 4** `events_per_second`
  figures quoted in #68's evidence appear in `wg-audio48`'s stored telemetry and **none** appears
  in `wg-matrix`'s. **#68 stands as reported.**
- **g4, the platformer, is designed and NOT launched.** Launching needs approval and at least
  two calibration trials in different cells; the honest cost range is $800-1,900 (#42).

## Code-reading aspects are within-stack only — permanently, not pending a better anonymiser

**Decided 2026-08-22, on measurement.** `idiomatic` and `architecture` may be used to compare
submissions **within one stack**. They may never contribute to a cross-stack claim, and this is
not a defect awaiting repair.

> **The within-stack permission is conditional on the field's packs matching their manifests,
> and the condition is a property of the pack ON DISK NOW — not of the run, and not of a round
> already taken.** `wg-g4c-2026-08-21T02-26-46` failed it with 23 stale files in 222 (#95) and
> **passes it since the 2026-08-23 re-pack**: 199 files, `stale=0`, `clean=True`, with the
> starter-drift exclusion set computed and corroborated rather than guessed (`eval/RUNS.md`).
>
> **A re-pack licenses new rounds, never stored ones.** The 30 `wg-aspect-reliability` rounds
> read the 222-file field; nothing can re-run their reading, so their `idiomatic` and
> `architecture` orderings stay unreadable. Within-stack code comparison on this field means a
> round taken after the re-pack.
>
> Check before relying on this permission, at the run you are actually reading, and check it
> again if anything re-packed since:
> `python3 eval/judge/field.py packcheck --run eval/runs/<run>` — exit 0 clean, 1 dirty, 2 if it
> could not evaluate the address you gave it (#96). It takes a **path**, not a run name.

### The measurement

Across 26 stored code-aspect rounds, 208 evidence strings, counting strings that name their own
stack's real tokens (`Bevy`, `MonoBehaviour`, `Godot`, `THREE`, `@export`, `InputMap`):

| aspect | blinding | strings naming the real stack |
|---|---|---|
| `idiomatic` | real extensions, by design | **134 of 144 (93%)** |
| `architecture` | `blind_language=True`, `.src` paths | **13 of 64 (20%)** |

**The substitution works and is worth keeping** — 93% → 20% is not nothing, and an earlier
reading that "no anonymiser helps" was wrong. But the residual 20% is unfixable, and the reason
is decisive: `Godot`, `GDScript`, `MonoBehaviour`, `UnityEngine`, `THREE` are **absent from the
architecture pack**, verified over 2.2M characters — yet the judge writes *"Rust/Bevy."*,
*"Unity/C#."*, *"Godot/GDScript."* anyway. It is not copying a token that slipped through. **It is
identifying the language from the syntax and naming the engine itself**, and on one occasion
wrote *"EngineBehaviour = renamed MonoBehaviour"* — decoding the substitution and reporting what
had been replaced.

### Why no better anonymiser exists

Syntax cannot be removed without paraphrasing the code, and paraphrasing changes the thing being
judged. A stronger cipher is still a cipher against a reader that breaks it. For `idiomatic` the
point is sharper still: the aspect asks whether the code is written the way its language is
normally written, so **the aspect whose subject is the variable under test cannot be blinded to
that variable.** Blinding it would not make it fair; it would make it meaningless.

### What follows, and what does not

- **Barred: any cross-stack ordering from a code aspect.** Not because the judgement is
  necessarily wrong — it may be a real reading of the work — but because it can never again be
  *defended* with "it cannot be a prior, the judge is blind". That defence is unavailable
  permanently.
- **Permitted: within-stack A/B** — template v1 against v2, same stack, same task. A per-stack
  prior is constant on both sides and cancels. This is the same argument that licenses the
  repeats work, and it is what the template improvement loop actually needs.
- **`architecture`'s `blind_language=True` stays**, because 20% is better than 93% and the
  cost is zero. Keeping a partial defence is not the same as trusting it.

### The question this retires

#53 asked whether `idiomatic`'s stack ordering is "a language prior rather than a judgement of
the work". **That question was mis-posed**: it assumed the judge did not know the stack. It does,
in 93% of strings, by its own account. The ordering may still be a real judgement — #79 found it
reproduces across four games with zero contradictions — but "blind, therefore not a prior" was
never available as an argument, and no experiment can restore it.

**A limit that cannot be removed is a decision, not a finding.** #53 and #83 record how it was
discovered; this records what is now done about it.

---

---

## The templates are measured at each stack's best, not at a common floor — decided 2026-08-22

**Every template showcases the best its own stack can do. It is not held to a capability floor
shared by all four.**

The alternative was a common floor: every template exposes only what all four stacks can do,
which keeps the comparison tightly controlled and measures the stacks on shared ground. That was
rejected. It answers a question nobody is asking — *how do four engines compare when each is
restricted to what the weakest can do* — and the headline it produces ("these four are
indistinguishable") is then partly an artifact of the restriction.

**What is now being measured: what a competent agent can build in each stack when the template
does not hold it back.** That asymmetry is the subject, not a confound to be designed away.

**The survey it was decided ahead of has now run** (`research/10-stack-capability-matrix.md`,
2026-08-23), and it corrects two of the examples this decision was originally stated with:

- **Ray tracing is not reachable in any arm on the measurement machine.** Bevy has the Metal
  ray-query feature and `bevy_solari` still cannot initialise (it needs `BUFFER_BINDING_ARRAY`,
  which wgpu 29 sets only on Vulkan) — and it fails open with a `warn!`. Unity measures
  `supportsRayTracing = False` and ships no Metal acceleration-structure path. three.js has no
  WebGPU under the capture harness. Godot has the API but no scene-renderer integration. The
  clause "ray tracing where the platform supports it" therefore selects nothing.
- **Native physics is the inverse of how it reads.** Godot ships Jolt in-tree but Godot Physics
  is the default; Unity ships PhysX. Both are one pin change away — and **neither can be used
  where game rules must live**, because `Sim.asmdef`'s `noEngineReferences` and
  `tools/boundary.gd` forbid it. Bevy and three.js, which ship no physics, are the two that
  *could* pin a deterministic solver inside `sim`.

Native particle systems remain a real and large asymmetry: Godot ships them, Unity's is one
manifest line, Bevy and three.js have none at any effort below writing one.

**What this costs, stated plainly so it is not discovered later:**

- A cross-stack difference is no longer attributable to the stack alone. It is attributable to
  *the stack as exercised by this template* — and the template author's judgement about what
  "best" means becomes a variable. This was always partly true; deliberately diverging templates
  make it matter more.
- The defence is that "best" must be **sourced, not asserted** — see
  `research/10-stack-capability-matrix.md` and `research/AGENTS.md`'s sourcing rules. A capability
  included because it is documented and reachable is defensible; one included because it seemed
  impressive is not. The survey also lists ten cells it could **not** establish; those are not
  available for "best" until someone settles them.
- `judge/starter_parity.py` must continue to REPORT capability divergence rather than fail on it.
  Under this decision, divergence is the design; a guard that reads it as drift would be wrong
  and would be switched off, which is worse.

**This decision does not license showcasing what cannot be observed.** `ux` — the aspect most
sensitive to visual richness — was retired for correlating +0.53 to +0.73 with distinct-colour
count (#59), so prettier output moves that metric in the direction that looks like improvement,
for the reason it was retired. What the pipeline *can* now see about capture cost and capture
geometry is the next section; what it still cannot see, and why, is the `DECLINED` register in
`judge/capability.py`. **A capability change must name the field that would move if it worked**,
and if the only candidate is a palette-coupled one, it cannot be shown to have helped.

**Implemented, 2026-08-23, in all four arms.** Rust is on Bevy's own default feature set, so
the arm can render a lit 3D mesh and open an audio device — neither of which it could do at the
old pin, on a task set where two of four games are 3D and audio is a scored criterion. Godot
exposes `GPUParticles2D` through `view/fx.gd`. Unity carries `com.unity.modules.audio` and
`com.unity.modules.particlesystem` and exposes Shuriken through `Assets/View/Fx.cs`, so the two
engines that ship a native particle system both expose it and `AudioSource` compiles for the
first time — it was a hard compile error (`CS1069`) through every matrix graded before this
date, on a criterion that is scored. TypeScript adopts nothing: three 0.185 ships no emitter,
and its batching primitives are documented with the measurement instead, because on the
rasteriser the harness actually uses `InstancedMesh` buys ~6% and `Points` is already five lines
away.

The regime notes and the measured costs are in `eval/RUNS.md` (twelfth and thirteenth
comparability breaks); the hypotheses, the falsifiers and **the register of capabilities
surveyed as available and deliberately not adopted** are the task-26 and task-52 iterations in
the root `IMPROVEMENTS.md`.

**One operating rule came out of doing it, and it decides the cases the survey does not.**

> **A template exposes what its stack SHIPS. It does not implement what its stack lacks.**

Lowering a capability from E2/E3 to E1 for something the engine already contains is exposing it;
writing the subsystem is manufacturing one, and it would erase the asymmetry this decision exists
to measure. It is why Godot and Unity get a particle helper and Rust and three.js do not: neither
ships a particle system at any effort below writing one, and a template that wrote one for them
would be reporting a fact about four template authors.

**Its corollary, learned in task 52: a capability the stack already ships in one line is
documentation, not scaffolding.** Exposing means removing the cost of discovering something; it
does not mean wrapping something that has no cost to discover. `Points`, `InstancedMesh` and
sprite atlasing are all E1 in their arms, so what the template owes an agent about them is the
number that tells it which to pick — for ts, that one batched `InstancedMesh` is 6% cheaper than
N separate meshes on SwiftShader and one `Points` is 10x, at the geometry counts this task set
actually reaches. A wrapper would add surface without adding reach.

---

## Performance is measured from outside the submission, and none of it is scored — decided 2026-08-23

**The harness measures the cost of the evidence it collects. The submission is never asked to
report a number about itself.**

Task 25 proposed extending the probe contract in `starters/_shared/` so each stack reports its own
performance fields. Rejected, and the reason generalises past this case:

> **A field the subject reports is a field the subject can fail to report, and that failure
> correlates with stack** — #62, #72, #77, this project's most repeated defect. A field measured
> by a mechanism identical for all four arms cannot produce a stack-correlated gap; the gap would
> have to be in the harness, where one repair covers every arm. **Uniformity by construction beats
> uniformity by instruction.**

Two consequences that made the choice cheap as well as right: no starter changes, so this is **not
a regime boundary** and every stored run stays in the comparison; and four of the nine fields turn
out to have been recorded on all 68 stored submissions already, unread (#97).

`judge/capability.py` holds the contract — nine fields, each with its unit — plus the gate
`no_stack_correlated_gap()`, which fails if a declared field is ever absent for any reason other
than the submission's own capture failing. `judge/capability_selftest.py` carries its mutant and
its variant.

**No frametime and no fps field, at any point.** The four arms do not render the judged frames on
comparable hardware: Rust, Unity and Godot draw on the M3 Max, the TypeScript arm draws on
**SwiftShader, a CPU rasteriser** (`research/10-stack-capability-matrix.md` §3). A frametime field
would report the renderer backend wearing the costume of a stack result. `just film` is also not a
real-time loop in any arm — twelve single frames of a deterministic replay — so there is nothing
steady to time. `DECLINED` in that module records this and the other six candidates, each with the
measurement that would move it back in.

**Nothing here is a criterion, and `judge/RUBRIC.md` weighs none of it.** Capture is cheap and
reversible; scoring changes what agents optimise for and is a regime boundary. A criterion
introduced alongside its own measurement has no baseline to be calibrated against.

Its reversal condition is in the table at the end of this file.

---

## What in `eval/runs/` is evidence — decided 2026-08-22

**A file under `eval/runs/` is evidence until something in the tree itself proves it can be
regenerated, and the proof must name a producer that declared the file its own output.**

Two proofs are accepted, both being the toolchain speaking about its own output: a `CACHEDIR.TAG`
with a valid signature at a directory root, and the work tree's own `.gitignore`. Anything no
proof reaches is copied.

Stated as a rule rather than a list of directories because an enumeration misses the next stack
and fails in the direction that loses evidence. It is applied by `eval/tools/evidence_set.py`;
`eval/PROTOCOL.md` says when to re-sync and `#90` says what this replaced.

Measured on that rule: 14,270 files, 1.118 GB of 138.164 GB — 99.19% of `eval/runs/` is
regenerable. **Reclaiming the 137 GB remains task 10's call**, and nothing was deleted here.

**When to re-sync is decided by the resource, not by an activity — revised 2026-08-23.** The rule
was *"after any run completes"*, and the starter baselines (7.5 MB, the only record of what
starter each agent was given, #104) were created by a **repair**, so the copy verified complete at
00:08 did not contain them at 04:24 (#116). The trigger is now *the evidence set has grown or
changed, whatever made it move*, with `backup_evidence.py --verify-only` as the mechanical form —
it re-classifies and a non-zero missing count is the signal, so nobody has to judge what counts.

**The copy is deliberately additive.** `rsync` runs without `--delete` and nothing removes from
the destination, because a mirror that faithfully reproduces an `rm -rf` protects against nothing.
The cost is that it becomes a superset; `DEST_ONLY.txt` at the destination lists every such path
so a stale file cannot pass for a current one, and reconciliation happens at the source or not at
all.

**Where the copy goes is still open.** The current copy at `/Users/stefano/game-research-evidence`
is on the same physical disk as the original and is therefore not a backup — it survives `rm -rf`
and a bad `git clean`, and nothing else. This machine has no external disk, no `rclone`/`restic`
remote, and its only cloud target is the operator's personal iCloud Drive, which is not somewhere
project evidence belongs. Every evidence file is under 50 MB, so an external disk or a private
GitHub repo would each work without LFS; both need the operator's go-ahead.

---
## A wrong stored manifest is marked, never repaired — decided 2026-08-23

**Configuration records in `eval/runs/` are append-only when written and read-only afterwards.**
Six stored directories hold a manifest that does not describe them (#93, #120). None was edited.

**Why not repair.** For `wg-matrix`, `wg-arena3d` and `wg-g4` the original was destroyed and no
honest replacement exists — a manifest reconstructed today is an inference wearing the name of a
contemporaneous record, and every later reader would take it at face value. For `wg-audio48` the
original *does* survive as `suite-full-matrix.json`, and it was still not promoted: renaming it
over `suite.json` would leave the directory looking as though nothing had ever gone wrong, which
is the state the audit exists to distinguish from a healthy one.

**What replaces the repair.** Each carries a `MANIFEST-DEFECT.json` written by
`eval/tools/manifest.py mark`, holding what was measured, what survives, and — only under
`reconstructed_*` keys, never under a `suite*.json` name — what the reports say the run was. The
marker stores the exact issue list it acknowledges and the audit re-measures and compares every
run, so it can acknowledge an unchanged known state and cannot hide a change. That is what keeps
it from being a suppression list.

**What would re-open it.** A stored manifest whose original is recoverable *byte for byte* from
something written at run time — a build log quoting it, or a copy in the evidence set predating
the overwrite. Then promoting it is a restoration rather than a reconstruction, and the
distinction this decision rests on disappears.

---
## Append-only has two shapes, and the directory decides which — decided 2026-08-23

The guard from the decision above is stated as a resource: *any durable record of what a
measurement was configured to be, or of what it measured, is append-only.* Two more writers had
the overwriting shape and are now covered — judge-sweep summaries (`GATES.json`,
`SEQUENTIAL.json`, `REPRODUCIBILITY.json`) and the three records at the evidence destination
(`MANIFEST.sha256`, `DEST_ONLY.txt`, `MEASURED.json`). **Neither is regenerable in practice: the
inputs move.** A sweep's gate-0 verdict belongs to the rounds that existed when it ran, and what
the copy held last week cannot be recomputed from what it holds today.

**They do NOT take the same layout as `suite.json`, and that is the decision.** `write_manifest`
pins the canonical name to the *first* record. Applied here it would have been a defect wearing
the shape of a fix:

| | pinning would have done | consequence |
|---|---|---|
| `MEASURED.json` | canonical = the first sync ever | `PROTOCOL.md` instructs a reader to take the evidence count from that name; it would hand back a stale number, and nothing would disagree with it |
| sweep summaries | canonical = the first invocation's ceiling counter | `judge_ledger.explain_gap` looks for the carried-over rounds at the *head*; against a first-invocation counter the gap is the *suffix*, so every resumed sweep returns `UNEXPLAINED` and exits 1 |

So `tools/manifest.py` carries both, in one file, with the criterion written next to them:
**pinned where the directory has an identity the record is named for** (a run directory is named
for one launch, and a later launch must not take the name); **rolling where the directory
accumulates** and its record states the position as of the last invocation. Nothing is destroyed
under either.

Two consequences worth stating because they are the ones that would otherwise be re-derived. An
**identical restatement is not a new record** — `write_rolling` compares the bytes and writes
nothing when they match, which is what keeps `--verify-only` from adding a 1.1 MB checksum
manifest every time it is run against an unchanged set. And the kept copy is stamped from a
timestamp **inside** the record where there is one, falling back to mtime only for plain text: a
`cp` rewrites every mtime in glob order and produces a clean, ordered, meaningless chronology,
which is the defect `judge_ledger.MIN_SPLIT_S` exists for.

**What this does not do.** Stored records written before the repair are untouched — no sweep
directory was given a reconstructed history, for the same reason no stored manifest was repaired.
The guard is forward-only.

---
## The harness lint baseline is a recipe, not a gate — decided 2026-08-23

**`python3 eval/tools/lint.py` is the recipe.** It runs the pinned rule set over the harness and
prints every site with its file and line. `prune_scan.py --only lint` still gives the per-rule
totals; both call the same `run_ruff()` in `prune_scan.py`, and `LINT_SELECT`, `LINT_ROOT` and
`LINT_EXCLUDE` are spelled once, there.

**It exits 0 with findings.** A gate added while the codebase still violates it is a gate that
gets switched off, and switching it off is silent. `--gate` exists so whoever wires one later
need not edit the tool; nothing calls it.

**What the baseline means, and what it does not.** `PLW1510` and `BLE001` are at **0** and are a
real baseline: every `subprocess.run` under the lint root states its `check=`, and every blind
`except Exception` that remains carries a `# noqa: BLE001` naming why the exception set is open
there. A new hit from either rule is therefore a site nobody has considered. The other 44
findings — `B905`, `F401`, `F541`, `B007`, `B023`, `F841` — were **not** triaged and are a
standing backlog, not a clean baseline. The reasoning is in #105 and in `eval/tools/lint.py`.

**`eval/judge/fixtures/` is out of scope**, alongside `eval/runs/`. Those are stand-in
*submissions* — the same class of artifact as `eval/starters/*/`, one of them deliberately
defective — and linting the object of measurement is measuring the thing being measured. They
contributed 14 of the 30 `BLE001` and 3 of the 11 `B905`, every one of them an idiom a fixture
needs.

---
## The four `template*/` trees and the spec-change suite are retired — decided 2026-08-23 [user]

**The four original trees — `template/`, `template-ts/`, `template-unity/`, `template-godot/` —
are deleted, and with them `eval/run-bakeoff.sh` and `eval/archive-and-rerun.sh`, the only two
things that could launch a spec-change trial.**

**Why, and it is not tidiness.** They were a *fork*, not a copy: a finished Pong per stack,
diverged from `eval/starters/*` in every source file. A copy can be gated on equality; a fork
cannot, so nothing compared them and nothing could. Measured: **0 of the 105 commits since the
repo import touched any `template*/` directory, against 6 that touched `eval/starters/`** (#112).
The consequence was not hypothetical — a capture-page defect repaired in `eval/starters/ts` on
2026-08-22 was still live in `template-ts` a day later, and was found by hand, not by a gate
(#112, task 48). **A second tree with a dormant consumer has nothing pulling it back into line,
and the cost of keeping it is paid every time the live tree is repaired.**

The suite they fed was already answered: it **failed to separate four stacks that all scored
6/6**, it has not run since 2026-08-12, and the programme decision that tasks are whole-game
builds rather than spec changes was taken before that. Keeping a fork alive for an experiment
that returned a null and is not being repeated is paying maintenance for nothing.

**What was deliberately KEPT, and why each.** Retiring a suite is not the same as deleting its
evidence, and the two look identical from a file listing:

| Kept | Because |
|---|---|
| `eval/runs/bakeoff-*`, `core-*`, `archive-run1-*` | 71 trials in 12 run directories. The results |
| `eval/suites/*.toml`, `eval/suites/prompts.py` | **The sole copy of what those 71 trials were asked to do.** A trial record stores `task: "t1_rally"` and no prompt text; 0 files under `eval/runs/` contain it (#122) |
| `eval/holdout*/`, `eval/variants/` | The answer key and the ablation arm — what "score 1.00" and "arm no_api_notes" meant |
| `eval/runner.py`, whole | `judge/static.py` imports its capture policy by path. Two truncation policies in one repository is #100, which came back as #114. It is also the definition of the measurement the 71 stored verdicts report, and `report` / `regrade.py` still read them. `run` and `check-suite` now exit 2 naming the retirement instead of raising three frames down |
| `eval/BAKEOFF.md`, `eval/FINE-TUNING-BRIEF.md` | The suite's design, which is the context those results are read in |

**`eval/starters/*/` are untouched and are not substitutes.** They are the whole-game product and
the subject of the comparison; they carry no finished game for a spec change to modify.

**Deletion here is recoverable and that is load-bearing.** The trees are in git across 139 commits
and pushed to `origin/main` — `git log -- template-ts` resolves, and `a3d0fd1` and `ee8625f` are
both on the remote. This is the property #104 did not have, where the only record of a starter was
a commit no archive contained. **A deletion whose recovery you have verified is a different act
from one whose recovery you assume.**

**Known cost, stated rather than discovered later:** `template-ts` received the capture-page
repair on 2026-08-23 (#112, task 48, commit `ee8625f`) — about 500 lines of porting, six hours
before this. That work is discarded. It was correct to do and correct to discard: it closed the
instance, and this closes the shape.

**The deletion did not survive its own merge, and the mechanism is worth keeping (task 111).**
The retirement commit `e86e09d` was complete: `git ls-tree -r e86e09d` matches **0** paths under
`template*/`. So does its other merge parent, `5afeb31`. The merge `f315f7e` nonetheless carried
**5** — `template-ts/.eslintcache`, `template-ts/public/main.js` and three build outputs under
`template-unity/tools/analyzer/bin/`. They came from neither parent; they came off the disk.
**Each tree carried its own `.gitignore`, and deleting the tree deleted the ignore rules that
had been hiding its build output** — `template-ts/.gitignore` listed `public/main.js` and
`.eslintcache`, `template-unity/.gitignore` listed `/tools/analyzer/bin/` — so a `git add -A`
at merge time saw an eslint cache, a 1.2M bundle and a compiled analyzer with its `.pdb` for the
first time, and staged them. From `f315f7e` (2026-08-23 08:35 -0300) until this repair the same
day, `AGENTS.md` stated `template*/` is deleted while 5 paths were tracked on `origin/main`, and
nothing could disagree: **no gate reads the tree for a claim a document makes about it.** It was
caught by a person configuring a code reviewer, not by a check. The 5 are now removed, and the
root `.gitignore` carries
`template*/` so a leftover build tree in an old checkout cannot be re-committed. Reproduced in
both directions on 2026-08-23: with the entry, `git add -A` over three replanted artefacts stages
nothing; without it, the same command un-deletes all three.

> **Deleting a directory deletes its `.gitignore`, which un-ignores every build artefact still
> on disk beneath it.** The removal and the loss of the guard land in the same commit, and the
> re-add lands in the next one — where it reads as an unrelated file, not as a botched deletion.

---
## A blind pack's `CHANGED.txt` is rebuilt from the manifest; the code half is not rewritten — decided 2026-08-23

**The question the ticket left open (task 95): map `CHANGED.txt` through the pack's own manifest,
drop it for blind aspects, or rewrite its text?** The measurement that chose is a partition, not a
total. Of the 1,561 arm-naming directory tokens surviving `blind_extensions` in the 8 stored
`architecture` packs, **182 sit in `CHANGED.txt` and every one is a real path segment**, while
1,379 sit in agent-authored code of which only 149 are paths — `public` is the C# access modifier
1,129 times.

**Mapped, not dropped and not rewritten.** `CHANGED.txt` is the one channel where the harness
holds ground truth: `pack.manifest` is an origin → label table the packer wrote, so every row can
be restated as ` sim/01.src | 42 ++--` with no vocabulary and no regex. Dropping the file instead
would discard per-file churn for the 196 of 424 rows that name files the judge can open, on the
aspect — `architecture` — that most needs to know which structure is authored. Rewriting the text
would need a vocabulary that is complete over a tree the pack cannot see.

**Rows that map to nothing are omitted and their count is not shown.** 228 of 424 rows name files
outside the pack. That count runs 53 and 43 for the two Unity submissions against 15 and 15 for
the two TypeScript ones, so reporting it — like reporting the `git diff --stat` summary tail — hands the
judge a partition of the field nobody chose to measure (#62). It is recorded beside the pack as
`changed_rows_dropped`, and zero mapped rows is a refusal rather than an empty file.

**The code-content half is NOT repaired. Feasibility was not the reason, and neither — it turns
out — is the per-arm density the decision was first written against (task 103).** Four candidates
were measured over the 9 independent stored fields:

| candidate | godot | rust | ts | unity | per-arm density | isolates an arm |
|---|---|---|---|---|---|---|
| arm-exclusive vocabulary from `git ls-files` | 0 | 43 | 265 | 228 | infinite | 6 of 9 fields |
| every starter directory, shared included | 271 | 102 | 830 | 273 | 8.9x | 9 of 9 |
| vocabulary-free: every path component | 831 | 927 | 1701 | 668 | 2.8x | 9 of 9 |
| the same, minus the four bucket labels | 428 | 690 | 1021 | 668 | 2.1x | 9 of 9 |

*Isolates* means a **strict** threshold on one pack's redaction count separates a whole arm from
the other six, measured per field, against **7.1%** by chance. Nothing measured comes near it.

> **The statistic the first version of this decision named was one no judge can see.** Per-arm
> density is an aggregate over the whole corpus; a judge is shown eight packs and how redacted
> each one looks. A vocabulary-free rewrite drives the aggregate from infinite to **2.1x** and
> leaves no arm at zero — satisfying the reversal condition exactly as it was written — while
> making the per-field figure **worse**, 9 of 9 against 6 of 9. It does not close the channel; it
> moves the leak from Godot's zero to TypeScript's extreme, where it is just as readable and
> costs 2,807 redactions instead of 536. **Optimising a proxy that the protected party never
> observes is the shape of a fix that measures nothing.**

The census is part 6 of `judge/blind_dir_selftest.py`, run with `--runs-root`, so the decision has
a producer; it pins the published table and refuses a `--runs-root` that is not the corpus. The
table **excludes `bin`**, the one arm-exclusive segment that fires in all four arms, because 19 of
its 26 hits are `#!/usr/bin/env` shebangs rather than the Rust starter's `src/bin/`; with it the
table reads 9/50/265/238. `tasks/103` holds the working.

**What is left unblinded is smaller than it looks.** Code aspects are already barred from every
cross-stack claim (below), and the judge names the engine correctly in 20% of `architecture`
evidence strings from **syntax alone**, with the tokens verifiably absent. The residue this would
have removed sits underneath a signal that is unremovable and already conceded.

**Scope, stated because it is easy to assume otherwise:** this licenses new rounds and repairs
none. Every `architecture` round stored in this repository read a `CHANGED.txt` listing the real
authored tree.

---
## Pull requests are reviewed by CodeRabbit, and the config is exclusion-only — decided 2026-08-23

**[user]** that agent work should be reviewed before it is merged. **[agent]** everything below
about how. `.coderabbit.yaml` at the repository root is the whole in-repository half; the other
half is a GitHub App authorisation that only the operator can perform, and `tasks/108` holds the
steps.

**`path_filters` carries exclusions and never an inclusion.** Per the schema those patterns also
drive a sparse checkout, so 1 positive pattern turns the list into an allowlist and blinds the
reviewer to everything not named — including `.coderabbit.yaml` itself. An exclusion-only list
cannot do that.

What is excluded, and the population each pattern covers (`git ls-files`, 673 tracked files,
2026-08-23 — re-run it, this tree moves daily):

| pattern | files | why |
|---|---|---|
| `!eval/instrfollow/runs/**` | 115 | committed stored evidence — 1 JSON record per trial. Data, not source |
| `!eval/findings/**`, `!eval/FINDINGS.md`, `!eval/IMPROVEMENTS.md`, `!IMPROVEMENTS.md`, `!CLEANUP-LOG.md` | 10 | archives. A figure published and later proven wrong **stays** there, so a comment flagging one is a false positive with certainty, not with probability |
| `!eval/runs/**` | **0** | gitignored, so it matches nothing today. Kept as a second guard, and the firing case is constructible: `.gitignore` changes, or 1 record is committed as a fixture |

**`eval/instrfollow/runs/` is the stored evidence that can actually reach a diff, and `eval/runs/`
is not** — the opposite of what is easy to assume. `eval/runs/` is 129G and gitignored;
`git ls-files eval/runs` returns 0. Rule 12: the address is an input to the check.

**`tasks/` is reviewed, against the archive list.** It is an archive by `ARCHIVE_PATHS` in
`eval/tools/docstat.py`, and excluding it would also drop it from the sparse checkout — leaving
the reviewer assessing a one-task branch with no access to its brief. The ticket is the only
written statement of what the diff was supposed to do. The false-positive risk is handled by a
`path_instruction` telling the reviewer not to correct figures there.

**`eval/starters/*/` is reviewed too, not excluded, and its instruction redirects what is asked.**
It is the experimental material, so "this could be better" is out of scope by construction. What a
reviewer *can* do there is procedural and valuable: ask whether a change to 1 of the 4 stack trees
was made to the other 3, and whether the regime-boundary gates named in `AGENTS.md` were run.

**`reviews.review_details: true`** is the only setting changed for a reason particular to this
project rather than to code review: it makes each review state which files it ignored, so *"did
our own filters swallow the change?"* is answerable from the artifact. That is `AGENTS.md`,
"capture what the instrument DID".

**`knowledge_base.{learnings,issues,pull_requests}.scope: local`.** All three default to `auto`,
which resolves to **global** on a private repository — what CodeRabbit learns here would be
applied to unrelated repositories on the same account. Same reason skills may not live in
`~/.claude`.

**`code_guidelines.filePatterns` enumerates 6 files rather than globbing `**/AGENTS.md`.** That
glob matches 8, and 4 of them are `eval/starters/{rust,ts,unity,godot}/AGENTS.md` — the product,
not standards this repository holds itself to. It is an enumeration, which is normally the wrong
shape, and it goes stale in exactly 1 way: **a new folder-scoped `AGENTS.md` outside
`eval/starters/` has to be added to it.**

**`reviews.tools` is deliberately empty.** Disabling `markdownlint` and `languagetool` over 173
markdown files is the obvious edit and it is a guess. The first reviews are the measurement.

**What the first review actually did, on PR #1, 2026-08-23 — because a configuration that has
never caused a review is a mechanism that runs and measures nothing.** It posted 1 actionable
comment across a 2-file diff, and the comment was a **true positive against this repository's own
rules, not against a style guide**: the section you are reading spelled its counts as *single*,
*one*, *three* and *six*, and `AGENTS.md` requires a count in a live document to be written in
digits, because no check can read a cardinal spelled in words — the failure that let a stale
findings figure survive 11 days. The reviewer derived that rule from `DECISIONS.md` through
`code_guidelines.filePatterns` and cited it as its source. The counts are now digits.

**The boundary applied when fixing it, because the rule does not state one:** digits wherever the
number is a quantity of something in this repository that could change; words where the word is an
indefinite article or a compound modifier naming no population — *a one-task branch* stays.

`profile: chill` produced no prose comments on the markdown files, which is weak evidence against
the guess that `markdownlint` and `languagetool` need disabling, and not enough to act on.
`review_details: true` worked as intended: each review listed which path instructions and which
learnings it used, so what the reviewer consumed is on the record.

**Over 3 rounds on PR #1 the reviewer posted 2 actionable comments, both true positives, and 0
false positives — and the 2 came through the 2 different mechanisms configured here.** The first
was sourced from `Coding guidelines`, i.e. `code_guidelines.filePatterns`, and applied the digits
rule. The second was sourced from `Path instructions` and applied the `**/*.md` rule — *comment
only when a document states something FALSE* — to catch `README.md` saying `.coderabbit.yaml`
"drops the archives" when `tasks/` is an archive this config deliberately keeps reviewable. A
reviewer with the default configuration would have had neither rule available.

**The rate limit is a real constraint on a parallel queue and belongs in `tasks/109`:** the plan
allows **10 included reviews per hour**, and each review round reports what is left. Across 3
rounds on this 1 pull request the counter read **9, then 8, then 6** — so 4 of the hour's 10 went
on 1 PR, and the third round consumed 2. **The cost is per review round, not per pull request,
and it is not 1 per push**; anything that assumes a fixed rate should read the counter instead.

---
## An unreachable private method in `eval/judge/` is deleted, never exempted — decided 2026-08-23

`eval/tools/dead_private_control.py` is a gate over `eval/judge/`: 0 unreachable private methods
out of 118. The reason it is a gate rather than a report is #136 — a repair to
`PlatformerBot._approach`, which no tree that defined it ever called, produced a byte-identical
re-grade that was then read as evidence against the pit hypothesis for #82. The check goes red on
`9fc044a`, the commit that published #82.

Three choices inside it, each with the alternative that was measured and rejected:

| Decided | Rejected, and why |
|---|---|
| It lives in a `*_control.py`, not in `lint.py` | `lint.py` exits 0 with findings by deliberate decision (the row below), and its `--gate` flag has no caller. A check that must go red does not belong behind one that must not. The control shape also carries the red pin and the green pin in one run, which is what the task asked for |
| **Reachability** from roots outside any private method's body, not "is this name referenced anywhere" | #136's per-method census names a cluster's tip and calls the rest live. Measured on the real `ArenaBot` corner cluster at `03cdb90`: shallow names 1 of 3, reachability 3 of 3 |
| The two hits were **deleted**. No allowlist, no marker, no exemption of any kind | An allowlist is a fail-open channel (AGENTS.md rule 7) and it would have been the check's entire content on day one. `Bot._num` was an unused base-class helper with no reference anywhere in the repository. The corner cluster's docstring was the only record of a measured-and-discarded design, so **the measurement moved into `_chase`'s docstring** — which already archives two other discarded designs — before the code went. Evidence lands somewhere first; then the code goes |

The census population **includes `eval/judge/fixtures/`, which `lint.py` excludes.** Deliberate:
#136's published figure of 121 methods at `9fc044a` counts them, and direction 1b asserts against
that figure, so a narrower population would make the two numbers incomparable for nothing. The
fixtures contribute 0 dead methods in all three trees measured (`9fc044a`, `03cdb90`, HEAD), both
modes.

**What it gets wrong is pinned, not hidden.** A name assembled at runtime reads dead — fail-closed
noise, and no such site exists in `eval/judge/`. A method named only in another method's docstring
reads live — a genuine miss, and the price of the rule that keeps `getattr(self, "_step_once")`
alive. Both are variant rows, so widening the string handling cannot lose either silently.

---
## What the judge is told about the pack is a function of the pack, and both wordings are kept — decided 2026-08-23

**The question (task 104): the brief told every code judge the pack "may not contain every file
the author wrote" and the size budget that made that true was removed on 2026-08-22 (#69).
Correct the sentence, or delete it?**

**Neither on its own. The claim is now selected by the pack's state** —
`field.COMPLETENESS_NOTE[knowingly_truncated]`, read by both judge-facing texts. Deleting it was
the obvious repair and is wrong in the same way the original was: an unstated completeness leaves
a judge to decide for itself how much of a submission it is holding, and discounting absences is
what it does by default. Hard-coding "this pack is complete" is wrong too — `--allow-truncated`
still exists for the capped-vs-uncapped control, and a field built that way *is* incomplete.

**The general form, and it is why this is a decision rather than a bug fix: a claim with only one
possible value is not a claim, it is a decoration, and nothing can check it.** The constant
survived a mechanism's deletion precisely because no input could ever have made it read
differently. The same property put the opposite error in the pack skill, which asserted
completeness unconditionally — so a deliberately truncated field would have carried a skill and a
brief that contradicted each other.

**A pack with no recorded state is refused, not assumed complete.** `run_field` returns
`usable: false` when `knowingly_truncated` is absent from the mapping. Reading a missing key as
falsy would state completeness about a pack nothing on disk describes, which is #62's direction
(rule 7).

**Scope:** this licenses new rounds and repairs none. The 10 stored code rounds that recorded a
brief hash demonstrably read the stale sentence and cannot be re-run for it; `eval/RUNS.md`
records that, and the other 26 code rounds stored no hash and are unassessable.

---
## A ticket's body is appended to by `tasks.py note`, and a control never imports its expectation — decided 2026-08-23

`.claude/skills/work/SKILL.md` has told every dispatched agent to *write back what the next one
would otherwise re-derive* since the skill existed, and until now no agent could. Measured from a
real agent worktree (task 113): `Write`/`Edit` aimed at the shared checkout is **refused** by
worktree isolation; the worktree's own copy of `tasks/NNN-*.md` is a tracked file whose
main-checkout twin `start`/`done` rewrite, so a committed edit offers the merge a conflict in a
file the merge is already rewriting; and `tasks.py` had no subcommand that touched a body. Tasks
105 and 106 each emptied a session's findings into `established_by` — one unbroken line of YAML
prose that cannot carry a backtick (#80) and is not where the next agent looks.

**The decision is the subcommand, not a relaxation of the isolation.** The queue resolving to the
main checkout is #94's decision and stays; `note` writes there by the mechanism `add`, `start` and
`done` already use, and resolves the file **by id** rather than by a filename anyone typed —
which is the difference between it and the `>>` an agent would otherwise reach for, nothing
having ever blocked one. It appends through `open(p, "a")` and rewrites nothing, so *the rest of
the ticket is unchanged* is true by construction rather than by a round-trip that happened to
hold, and `-` reads the section from stdin because a backtick in argv is command substitution
before the program runs.

**The general rule this bought, and it is a refinement of AGENTS.md rule 12 rather than an
instance of it.** The first version of the control built its expected suffix by calling
`tasks.py`'s own `_note_block` — one value at one address, which is what rule 12 asks for, and
here it made the rows structurally incapable of failing: the mutant that deletes the newline
separating a section from the body came back **SURVIVED with 0 red rows of 48**, because the
mutant had edited the check. Rule 12 is about one **fact** at one address. **An expectation is
not the fact; it is the second, independent statement of it**, and a control that imports its
expectation from its subject is not a control. Where the two must be kept in step, do it with a
row that compares them — never by making them the same object.

---
## A finding cited in a live document is a reference-style link, gated by `linkcheck.py` — decided 2026-08-23

A bare `(#68)` is honest and useless: a reader who cannot click it has been told nothing. Making
it a link is not free, because **`docstat.py --sweep` does not check file paths** — a phantom
`eval/RUBRIC.md` passed a green sweep — so a link is a stronger claim than a number with no gate
behind it. **A link that resolves to the wrong place is worse than a bare number, because it looks
checked.**

Three shapes were available and the choice was made on what each fails at, not on which reads best:

| shape | why not |
|---|---|
| bare `(#68)` | unclickable; the objection that opened task 115 |
| inline `[#68](eval/findings/...#68-the-subjective-layers-first-...)` | a ~150-character URL inside every sentence, in a file whose stated defect was that it was hard to read |
| link to `eval/FINDINGS.md` with no fragment | always resolves and never lands on the finding. The index is a **table**, and GitHub generates no anchors for table rows, so there is nothing to aim at |

**Shipped: reference-style.** `[#68]` in the prose, and one definition block at the foot of the
file carrying the group file and the GitHub heading anchor. Prose stays as short as the bare form
and the machinery is in one place a checker can read.

**The fragment is the risk and `eval/tools/linkcheck.py` is the answer to it.** A reworded heading
kills an anchor silently. The tool derives the anchors from the target file's own headings rather
than assuming the rule, so a rewording turns a gate red instead of turning a link into a lie. It
checks inline links, reference definitions and `[#NN]` shortcuts with no definition, skips fenced
blocks and external schemes by design, and `--selftest` plants a known-good and a known-bad of
each of the three shapes — rule 12's corollary, prove the extraction on a case whose answer you
can state in advance. Both directions were exercised on `README.md` itself before the count over it
was believed: a phantom `eval/RUBRIC.md`, a truncated anchor and a dangling `[#999]` each went red.

**To re-open:** GitHub changing its heading-anchor rule, or a second consumer of these documents
that does not render Markdown links.

## Reversal conditions — what would re-open a decision

**Adopted 2026-08-23 from `game-research-gpt`, whose ADRs each end with one (task 11).
Labelled honestly: this is UNVERIFIED as an improvement.** No finding in `eval/FINDINGS.md` is
known to have been caused by a decision outliving its basis, so the case for it is an argument,
not a measurement. It is adopted narrowly — only where a decision rests on a measurement that
could plausibly move — rather than on every row, because a reversal condition attached to a
settled question is noise that makes the live ones harder to find.

| Decision | Re-open when |
|---|---|
| Tier 3 weight stays 0.00 | Repeats at a **fixed presentation order** clear gate 0. More aspects do not count — already tried, verdict unchanged |
| Separation figures reported under `rank`+`pool` | A field where the **ceiling gate passes on both orders**. The choice rests on scores saturating (6-7 of 8 on one modal value); on an unsaturated field a score-based figure loses its handicap and the comparison should be re-made. `field_ranks.py` prints all four either way |
| Code aspects are within-stack only | **Never on a better anonymiser.** The judge identifies the language from syntax, so only a change to what is being asked could re-open it |
| The code half of the directory leak stays unrepaired | A rewrite that **stops isolating an arm per field** — a strict threshold on one pack's redaction count naming a whole arm in fewer than a third of the stored fields. Currently 6 of 9 for the arm-exclusive vocabulary and 9 of 9 for all three alternatives, against 7.1% by chance. **This row asked for a uniform per-arm density until 2026-08-23, and that was the wrong quantity**: a vocabulary-free rewrite satisfies it at 2.1x with no arm at zero and is *worse* on the per-field figure, because per-arm density is an aggregate the judge never sees. `judge/blind_dir_selftest.py --runs-root` reports both and fails if any candidate stops partitioning |
| Deterministic tiers may not rank stacks | Within-cell verdict variance **large enough to resolve a between-stack gap** — currently **5 of 436** paired criteria in `wg-matrix` and **0 of 232** in `wg-audio48`, i.e. 1.1% and 0%, against a between-stack gap of zero. This row read *non-zero* until 2026-08-23, when the unscoped figure it rested on was withdrawn and the scoped recount came back **not zero**; a sign is not a threshold, and what size counts is unsettled (task 70) |
| Tier 1 gates rather than scores | `tier1_census.py` reporting **DISCRIMINATES** on its **headline** verdict — a group where both tiers vary among the trials tier 2 could measure. Currently 0 of 10. Its *"if every grading were pooled"* line already reads DISCRIMINATES and is **not** a trigger: it counts 16 superseded re-gradings of 8 work trees `wg-g4c` already contributes (task 75). Adding a tier-1 criterion with real headroom is what would do it, and it would need a mutant *and* a variant before it counted |
| A saturated tier-2 group certifies rather than ranks | `tier2_census.py` reporting **SEPARATES** — no group flat. Currently 5 of 10 are. It will not be moved by promoting a withheld diagnostic (single-valued wherever recorded) or by another existence-of-mechanic criterion (four measured, 8/8 on `wg-g4c`); it moves on a harder task |
| The play-bot tier carries 1.00 | `weight_sensitivity.py` reporting **FLIPS on a group whose variance is not a confound** — it needs a second scored tier to be worth re-running for that, so this re-opens only alongside the row above |
| No budget cap, `--max-turns 1000` | A trial **reaching 1000 turns**. The 250 limit became binding without anyone noticing (#35); the same failure at 1000 would mean the backstop has become an instruction |
| 2 trials per cell | A stack difference landing inside the ~0.015 the design cannot separate — at which point n=2 is the constraint, not the evidence |
| Performance fields are captured, not scored | `capability.py` reporting **real variance in `capture.megapixels`** across a run. At that point capture geometry is a choice submissions actually exercise and it is worth asking whether the judges should see it. Currently 62 of 68 sit on the starter default |
| No frametime or fps field | The TypeScript capture path getting a **real GPU backend**. Nothing else changes it: the asymmetry is the renderer, not the stack (§3 of the capability matrix) |
| An unreachable private method is deleted, never exempted | A hit that is genuinely reachable and cannot be made visible to the census — in practice a `getattr(self, ...)` whose name is assembled at runtime, the known false positive, appearing in real `eval/judge/` code. There are **0** such sites today: all three `getattr(` calls there take a literal or a non-private attribute. If one appears, the repair is a marker the census reads that names *why*, never a bare name list — an exemption that does not state its reason is indistinguishable from a mistake |
| Harness lint is a recipe, not a gate | `PLW1510` and `BLE001` **staying at 0 across a working week** without anyone tending them. At that point a gate costs nothing to add and would catch the next site before it is written; today it would fire on a backlog nobody has triaged and be disabled |
| The `template*/` trees and the spec-change suite are retired | A decision to **run spec-change trials again**. Then restore from git rather than re-forking: `git checkout <pre-retirement> -- template-ts/`. Note what re-opening costs — the trees are frozen at 2026-08-23 and every starter repair since then is missing from them, which is the drift that closed them in the first place |
| A harder task is priced, not bought | **A play-bot that reaches the goal.** The pre-test ran (task 83, #139) and came back spread — 0.274 to 0.803 — but 8 of 8 runs end on health exhaustion, and improving the bot reordered the field (ρ=0.405, p=0.163), so the spread is the instrument's. Nothing here justifies the $421-to-$698 spend: all-eight-at-1.000 would, and none of the eight reaches 1.000. Re-opens when a bot clears a real submission's stage without dying — at which point the fraction is about the level and the question is live again |
| Compliance with the always-loaded rules is measured, not assumed, and the measurement stops at k=16 | A pool **larger than 32 live instructions** exists. `eval/instrfollow/RESULT.md` bounds the count effect at 3.3pp up to 16, and `python3 eval/tools/instruction_census.py` puts the always-loaded set at 112-155 (read 2026-08-23) — so the open question is the gap, and closing it needs instructions, not trials. Cost rises steeply with k ($0.056 at k1, $0.273 at k16), so price a k32 pilot before sizing anything. Conflict is the cheaper subject: arXiv:2510.14842 puts the mechanism there, and two contradictions already sit in the always-loaded set (tasks 77, 79) |
| Both completeness wordings are kept in `COMPLETENESS_NOTE` | `--allow-truncated` being **removed from `field_sweep.py`**. While a deliberately capped field can be built, the truncated wording is reachable and the claim is checkable; delete the escape and the note collapses back to a constant, at which point the honest move is to delete the claim from the brief too rather than leave an uncheckable sentence in it |
| `tasks/` is reviewed by CodeRabbit rather than excluded with the other archives | A review comment **correcting a figure, a number or the prose** in a `tasks/` file. The exclusion is then 1 line — move the pattern into the archive block in `.coderabbit.yaml`. Nothing else re-opens it: noise about a ticket's *content* is the cost being accepted for the reviewer having the brief |
| `reviews.tools` left empty | The **first reviews naming which tool produced a comment nobody wanted**. Disable that tool and cite the review; do not pre-emptively disable `markdownlint` or `languagetool` on the argument that 173 markdown files must be noisy — that argument is available now and is not evidence |
| One authoritative path per skill | A **maintained** non-Claude consumer — a sibling that actually reads a skills tree and edits it. The 2026-08-23 measurement was 0 readers and 0 content-bearing edits in 3 commits; a copy that anyone maintains is a different object from the one that was deleted. Even then the first question is whether a pointer serves it, since a copy reintroduces the drift, not the reader |

The rows with no entry here are not exempt; they are decisions where the owner's judgement is the
input and no measurement would overturn them.

## Keeping this current

Update in the same session a decision is made or changed. Replace superseded entries rather than
annotating them — this file states what is true now, not how it got here.
