# Agent-oriented game development template — research, build, and bake-off

**Goal:** find the stack in which a coding agent, given a well-designed template, builds the best
game — and prove it by measurement rather than argument.

Four templates, one per candidate stack, each tuned to its own stack's strengths. Blank
`claude -p` sessions build whole games in each; a harness the building agents cannot see grades
the result. 24 whole-game submissions, ~$1,794, three games, four stacks, two independent trials
per cell.

Last updated **2026-08-21**.

---

# THE RESULT: there is no best stack, and the finding is that the question does not resolve

**Four well-built templates on Opus are indistinguishable on every task put to them.**

| evidence | reading |
|---|---|
| **the deterministic tiers sit at their ceiling, reported per game** | `wg-matrix-2026-08-13`, the one field where three games ran in a single regime: pong **5/8**, tetris **5/8**, arena **5/8** at exactly 1.000. `wg-audio48`: pong **8/8**, tetris **8/8**. `wg-g4c` platformer: **6/8** as of 2026-08-22, and **tier 2 is 1.00 in all eight cells**. It read 4/8 and then 5/8 before that, and **both were correct when written** — the cells moved as the play-bot was repaired (#82) and then `knockback.applied` (#89). The two still below 1.000 fail only on tier 1: one is a genuine submission defect (#66), one is `render.nonempty`. **Not summed** — see below |
| **the two trials of a cell agree on verdicts far more often than on evidence** | reported per scope, never pooled. `wg-matrix` (3 games, 436 paired criteria): **5** verdict differences against **332** differing evidence strings. `wg-audio48` (232 paired): **0** verdict differences, **120** differing evidence strings. So the submissions are genuinely different artifacts that the instrument mostly cannot separate — but "mostly", not "never" |
| **cost: the between-stack range is 42% of its own noise floor** | measured on all four stacks at once (`wg-g4c`, 8/8 `completed`, $421.00): mean within-cell gap **$21.15**, between-stack range **$8.91** |
| **no subjective aspect separates the stacks** | `wg-tetris-judge-2026-08-17`, 5 aspects × 2 orders, `g2_tetris3d` only — the sole field tier 3 had judged when this was measured (#71). Post-repair round: between-stack range of mean ranks **2.10** against a mean within-stack gap of **1.93**; pre-repair **1.90** against **2.27** — `judge/field_ranks.py`, `value=rank` `order=pool`, the pair this project quotes (`DECISIONS.md`). The quantity can be computed four ways and on **none** of the eight readings does the between-stack range exceed the within-stack gap by more than 23%, while on four it is smaller — no method separates these stacks, and the direction of the comparison is not stable enough to argue from. ⚠️ Both rounds are among those later shown to have opened pack files naming the submissions (#83), so this is **not** defensible as a blind result |
| **a fourth game, unseen by the templates, changes nothing** | `g4_platformer` was added after all four templates were fixed; it reproduces the null |

**Five instruments, five different routes, the same null.** Tier 1 (builds, lints, tests,
frames, audio), tier 2 (a scripted bot driving thousands of ticks), cost, the five-aspect LLM
judge layer, and now a **fourth game none of the templates had seen** each reach it
independently. None was designed as a check on the others.

**The headline result survived a new task.** Every earlier null could be read as the three games
having been, however unintentionally, shaped around what the templates already did well.
`g4_platformer` was written afterwards and is the first task with no such history, and it lands
in the same place — which is the single strongest thing that can be said for the null here.

On cost specifically, read the **floor before the range**. Cell spread itself ranges 1.12x
(unity) to 2.15x (rust) — a factor of **7.2** in gap terms — so a noise floor estimated from one
cell can be wrong sevenfold, which is how the retracted 2026-08-17 cost reading happened
(FINDINGS #63). Across all 8 trials **cost tracks turns at r = 0.971**: cost is very nearly a
restatement of how many turns an agent chose to take, and turns vary 205–370 *within* one stack.

> **Two kinds of change appear below and they must not be read as one.** A figure **withdrawn**
> was never reproducible — it named no population, and no repair will resurrect it. A figure
> **superseded** was correct when written and moved because the *instrument* was repaired: g4c's
> 4/8 → 5/8 is a play-bot fix (#82), not an erratum, and the earlier grading was an honest
> measurement of a worse instrument. **Treating a repair as an erratum discredits work that was
> right**, and treating an erratum as a repair hides a defect. The markings below say which.
>
> ⚠️ **A previous version of this table read "between-stack range of mean ranks 1.70, mean gap
> 2.05" with no scope at all — no run, no game, no aspect set, no date.** Registered as
> `WR-tier3-pair` in `eval/withdrawn.json`, which is what lets `docstat.py --withdrawn` tell
> this notice apart from a document still publishing the pair. It does not reproduce:
> the only field tier 3 had judged gives 2.10/1.93 post-repair and 1.90/2.27 pre-repair. Replaced
> above with both, scoped. **That is the fourth summary statistic in this table found
> unreproducible for the same reason**, after 20-of-24, 380-paired-criteria and
> 0-verdict-differences. Every one stated a number and omitted the population it was computed
> over. **An aggregate without its scope is not a weak claim, it is an unfalsifiable one** — it
> cannot be checked, so it survives indefinitely and gets quoted as established.
>
> ⚠️ **A previous version of this table read "0 verdict differences across 380 paired criteria"
> and "219 of 380 evidence strings differ". Both are withdrawn: neither reproduces.** A
> 2026-08-22 recount searched every coherent scope — all runs (1098 paired), `wg-matrix` alone
> (436), `wg-matrix`+`wg-arena3d` (584), `wg-audio48` (232), everything except g4 (958) — and by
> tier (playbot 540, programmatic 402). **None gives 380.** Six *arbitrary* subsets do, but each
> mixes runs and games incoherently, e.g. `wg-audio` pong + `wg-matrix` arena + `wg-audio48`
> tetris — the same "many combinations reach it, none is principled" signature as the 20-of-24
> figure below. And **"0 verdict differences" is false in every scope with a plausible count**:
> the number is 5 for `wg-matrix`, 13 across all runs. Some of that drift is this session's own
> criterion repairs re-grading cells, so the figure may well have been true when written — which
> is exactly why an aggregate must record its scope *and* its date. Replaced above with per-scope
> figures.
>
> ⚠️ **A previous version of this table read "20 of 24 cells score exactly 1.000". That number is
> withdrawn: it cannot be reproduced from the record, because it never said which 24 cells it
> counted.** Searching the stored reports, **eight different combinations** of three 8-cell groups
> give exactly 20/24 — and they disagree about which games and which runs are included, with some
> spanning regime boundaries this file elsewhere declares void. It is replaced by per-game figures
> above rather than corrected, because summing across games is itself barred: the play-bot scores
> **13 criteria on pong and 22 on arena**, so a 1.000 is a different achievement in each column
> (FINDINGS #72, `eval/RUNS.md`).

### Tier 3's first positive result — and it is not a stack result

Measured 2026-08-21 for $10.20, against a pre-registration written before the numbers existed
(`eval/judge/JUDGING.md`, FINDINGS #68). Gate 0 finally measured the instrument's own noise by
judging the same field four times in the same order: **absolute scores move (5 of 8 submissions,
mean 0.75) but rank order is stable — mean self-tau +0.853.**

Against that floor, `fun` and `fun_frames` — the same question, anchors and scale, differing
only in whether the telemetry is shown — rank the field at tau **+0.043** over 23 comparable
pairs. **The telemetry is doing work**: the submissions that move are exactly those whose
telemetry was extreme. It is the first evidence here that a judge read its evidence rather than
the packaging.

Two things it does **not** mean. It licenses **no cross-stack ranking** — that was pre-registered
too — and **tier 3 stays at weight 0.00**. And the outcome named in advance as most damaging to
the layer (which would have closed tier 3 entirely) **did not occur**, which is reported here for
the same reason it would have been had it landed.

### Three genuine submission defects in the entire project

Across four matrices and every criterion failure ever adjudicated, exactly three are properties
of the work. All runs cited are `wg-arena3d-2026-08-15` and `wg-g4c-2026-08-21`:

1. **`g3_arena__rust__t0/t1`** — `E0502` borrow-checker error in agent-written
   `crates/sim/src/lib.rs`. It does not compile. Score 0.000, and it has survived four harness
   repairs and a full offline re-grade.
2. **`g3_arena__ts__t0/t1`** — the submissions' own render tests fail, reproducibly (100/103
   and 106/109), on assertions the agents wrote themselves.
3. **`g4_platformer__unity__t1`** — **reclassified 2026-08-22, and the reclassification is the
   point.** It ships five `CA1861` analyzer violations in 602 lines of agent-written
   `Assets/Editor/AssetGen.cs`, failing the template's own strict gate. It was previously
   recorded as a *template* defect (#66), because the agent ran `just lint`, was told
   "all assemblies compile clean", and believed it. That was true: Unity's lint recipe was
   answering from its build cache. **Fixing the recipe (#66, task 07) moved the defect from the
   harness to the work** — the code was always wrong; only the gate was lying. It is a genuine
   defect *now* and was an honest pass *then*, and both halves matter.

**Everything else traced to the grader.** Sixteen play-bot false negatives in one sweep, three
more under the audio task, two more in the arena set, a withdrawn stack ranking that was a
screenshot artifact, and five stack-correlated signals that were all the instrument.

### ⚠️ The arena set is NOT comparable across stacks

`wg-arena3d` straddles a machine repair. Rust and TypeScript were built on 15 Aug while
`syspolicyd` was pegged at ~100% CPU — which gates `execve` of freshly created binaries, and
those two stacks link or install new binaries on every build. Unity and Godot were built on
16 Aug after it was restarted. **Both defects above are on the 15-August side of that line**, and
all four agents there reported, independently and by name, that they could not run a single
command that would have told them their work was broken.

The grading is correct; the comparison is void. **Label those eight cells wherever they appear.**
FINDINGS #49, and the mechanism is in `eval/RUNS.md`.

### What this does and does not license

- **It does not say the stacks are equal.** A null from an instrument with zero within-cell
  resolution is the instrument's noise floor, not a measurement of equality. Proving a tie needs
  ~96 judge rounds per aspect and the deterministic tiers cannot do it at any n.
- **It does say no ordering here is reportable.** The subjective ordering flips depending on
  which aspects are counted; the deterministic tiers are saturated; cost is noise.
- **It says the templates work.** Four independent stacks, three games, agents completing every
  task to a standard that saturates every mechanical check built to catch them failing.

---

## Where things live

| Directory | What it is |
|---|---|
| `research/` | Eleven briefs answering the original questions, plus `DECISION.md`. Every claim dated and sourced; unverified claims labelled. `DECISION.md` opens with a retraction — it decided on paper, and two of its eliminations were wrong. `10-stack-capability-matrix.md` is what each stack can do **at its pinned version**. |
| `eval/starters/<stack>/` | **What a whole-game trial actually copies**, one per stack. `wholegame.py` reads only this directory. Game-agnostic: a placeholder, the harness, the boundary and the `verify` gate. This is the product that every run since 2026-08-12 has measured. |
| `template/`, `template-ts/`, `template-unity/`, `template-godot/` | The **original four templates** — a finished Pong per stack, forked from before the starters existed. **Read only by `eval/run-bakeoff.sh` → `runner.py --template`**, the spec-change suite, which has not run since 2026-08-12. Rust + Bevy 0.19, TypeScript + three.js, Unity 6 (`noEngineReferences: true`), Godot 4.7 (a 65-rule `tools/boundary.gd`). Whether these should still exist as a second tree is open — FINDINGS #112. |
| `eval/` | The measurement harness, its findings, and every run's stored results. |
| `eval/judge/` | Three-tier evaluation: deterministic checks, scripted play-bots, and an LLM judge. |
| `DECISIONS.md` | Every decision that shaped this work, who made it, and why. **Read this before changing anything methodological.** |
| `eval/FINDINGS.md` | Findings #19-#118, including retractions. **Read this before trusting any number anywhere.** |

## Start here

- **What was decided and why?** → `DECISIONS.md`
- **What went wrong and what it taught?** → `eval/FINDINGS.md`
- **Why this stack?** → `research/DECISION.md` (the *prior*; the bake-off is the evidence)
- **What can each stack actually do at its pinned version?** → `research/10-stack-capability-matrix.md`
- **What does a building agent read?** → `eval/starters/<stack>/AGENTS.md` for a whole-game trial, which is every run since 2026-08-12; `template*/AGENTS.md` only for the spec-change suite
- **How is a submission graded?** → `eval/judge/RUBRIC.md`
- **How does subjective judging work, and what is being changed?** → `eval/judge/JUDGING.md`

---

## Status

### Done

**Four templates, one per stack.** Each is game-agnostic: a hexagonal split between simulation and
view, a determinism guard, a headless render-and-verify harness, and a single `verify` gate.
`eval/judge/starter_parity.py` proves Rust, TS and Godot are byte-identical on 401 lines of shared
scaffolding; Unity matches on 400 of 401.

**Spec-change bake-off, 24 trials, 2026-08-12, ~$65.** 3 tasks × 2 trials × 4 stacks. Prompts
semantically identical, each written in its own stack's vocabulary — an earlier byte-identical
version was Rust-flavoured and biased the comparison.

> **Result: the suite could not separate the four stacks.** All four scored 6/6. That is a finding
> about the suite, not about the stacks — small spec-change tasks are too easy to discriminate.
> It is why the whole-game matrix exists.

**Three-tier evaluation harness**, validated against fixtures with known quality, including a
discrimination gate that a bad implementation must fail.

**Whole-game matrix #1 (`wg-matrix-2026-08-13`): 24/24 trials built, $355.28 measured.**
3 games (Pong, 3D Tetris, arena shooter) × 4 stacks × 2 trials, all `terminal_reason=completed`.

| game | n | mean cost | mean turns | mean wall |
|---|---|---|---|---|
| `g1_pong` | 8 | $11.30 | 109 | 23.6 min |
| `g2_tetris3d` | 8 | $19.49 | 139 | 37.6 min |
| `g3_arena` | 8 | $13.62 | 112 | 27.4 min |

> **Result: an exact 24-way tie.** Every stack, every game, 1.000 on the deterministic tiers
> once harness defects were adjudicated out. All 15 criterion failures it produced were defects
> in the grader, not the submissions, and 14 of 15 fired on a single stack — which would have
> manufactured a false "Unity is worse" ranking. See FINDINGS #25 and #26.

**`just film` no longer omits the HUD.** It did on two of four stacks, and it is a defect in
the *product*, not only the grader: an agent that films a correct scoreboard and sees nothing
may delete working code. All four starters now draw the HUD through the captured render path,
each with a rendering test that goes red if it leaves that path. FINDINGS #27.

**All four templates are now at their own stack's best, not at a common floor** (DECISIONS.md,
2026-08-22; tasks 26 and 52). Rust runs Bevy's own default feature set, Godot and Unity expose
their native particle systems through `view/fx.gd` and `Assets/View/Fx.cs`, and **Unity can
compile `AudioSource` for the first time** — until 2026-08-23 it was a hard `CS1069`, on a
criterion that is scored, while the prompt told every agent to use it. TypeScript adopts
nothing and says why: on the rasteriser its harness actually uses, `InstancedMesh` buys 5-6%
and `Points` is already five lines away (FINDINGS #110). Divergence between the four is the
subject of the comparison, so `eval/judge/starter_parity.py` **reports** the capability
register and can never fail on it. Regime notes: `eval/RUNS.md`, twelfth and thirteenth
comparability breaks.

**Audio is measured.** Six criteria — five deterministic in tier 1, one in tier 2 — each paired
with a mutant that makes it go red (`eval/judge/audio_selftest.py`, 37 expectations).
`audio.distinct` compares *decoded samples*, so one beep re-encoded under five names is caught
where a filename or file-hash comparison would pass it.

**The 15 criteria that only ever fired wrongly are repaired**, each rewritten from waiting for a
condition to establishing one, and each pinned in both directions by a mutant
(`eval/judge/bot_mutants.py`). Repairing them uncovered two latent defects that would have made
the harness fail *open* — see FINDINGS #29.

**`bot_mutants.py` now runs a VARIANTS suite as well as mutants** — correct games the
reference deliberately does not resemble, where every criterion must still pass. Current
totals: **36 criteria pinned in both directions, 2 variants, 3 session-lock controls, 0
expectations unmet.** Mutants ask whether a criterion *can fail*; only a variant asks whether
it *can still pass*, and every false negative this project has adjudicated was of the second
kind (FINDINGS #46, #48).

**The cost of the capture is now recorded, and nothing scores it.** Nine fields — frame
geometry, frame count, and the wall/CPU/peak-RSS cost of `just film`, plus the headless probe's
throughput and start-up — with the same names and units on all four arms, measured from *outside*
the submission so no arm can fail to fill one (`eval/judge/capability.py`, DECISIONS.md). Swept
over the 68 stored submissions the gate is clean, and **62 of them captured at exactly the starter
default of 640x400**. Four of the nine fields turned out to have been written on every submission
since the first matrix with no reader at all (FINDINGS #97). **There is deliberately no frametime
or fps field:** the TypeScript arm films on SwiftShader while the other three film on the M3 Max,
so any render timing would report the backend rather than the stack.

**End-to-end controls, measured 2026-08-14 with audio in the tiers:**

| fixture | overall |
|---|---|
| `ref_pong` (correct reference game) | **0.956** — tier 2 14/14, all six audio criteria pass |
| `ref_pong_detuned` | 0.796 |
| `ref_adversarial_pong` (reports state, does not simulate) | 0.401 |
| `broken` (the starter, no game in it) | **0.089** |

Monotone across the full range: the evaluator can pass a good game and fail a broken one.

### The measured numbers behind the result above

Full per-cell table, per-criterion comparison and the `syspolicyd` straddle: **`eval/RUNS.md`**
(run ledger and comparability), **`eval/FINDINGS.md`** #49, #50 (the null and the straddle), and
`eval/judge/JUDGING.md` (the five-aspect gate results).

| | pong | tetris3d | arena 3D |
|---|---|---|---|
| cells at exactly 1.000 | 8 of 8 | 8 of 8 | 4 of 8 |
| comparable across stacks? | yes | yes | **NO — see above** |

### In flight

- **Specialist judges, first full field: 13 calls, $46.79 — and the subjective layer produces
  the same null.** Five aspects x two presentation orders on `g2_tetris3d`, whose eight
  submissions the deterministic tiers score identically.

  | | reported (`rank`/`pool`) | range across all four methods |
  |---|---|---|
  | between-stack range of mean ranks (0-7) | **1.900** | 0.350 – 3.300 |
  | mean gap between a stack's OWN two trials | **2.275** | 0.725 – 2.825 |

  Reproduce with `judge/field_ranks.py --rounds runs/wg-tetris-judge-2026-08-17/pre`. The
  quantity has two free parameters — `score` or `rank`, spread taken before or after averaging
  the rounds — so the right-hand column is **the same field read four ways**, not four fields.
  `rank`/`pool` is what the project quotes (`DECISIONS.md`). On **none** of the four does the
  between-stack range exceed the within-stack gap by more than 23%, and on two it is smaller:
  no method makes these four stacks separate. The ordering is also unstable to which aspects
  are counted: the top two swap and `ts` moves from third to last. **There is no ordering here
  to report.**

  Three of five aspects **ceiling on one presentation order and separate on the other** — the
  judge saturates on the same field the deterministic tiers cannot separate, and does so
  unstably. Two aspects were withdrawn on adjudication: `fun` scores track how long the
  play-bot happened to run (#52), and `idiomatic` reads the stack off the file extension and
  returns per-stack means identical across two different games (#53). `architecture` and `ux` —
  which share **no evidence at all**, one reading only source and the other only frames — ranked
  the field identically on both orders of that round, which was read as a shared prior and is
  **withdrawn**: the repeat gives tau 0.385 and 0.667, and two orders of one round were never
  two observations (#54, register `WR-arch-ux-redundancy`).

  **Re-run 2026-08-17 on a repaired instrument — 10 more calls, $21.05 — and the answer holds.**
  `fun`'s confound is gone by construction (run length is now *constant* across the field, and
  its scores track quiet-stretch at -0.63 and events/second at +0.51..+0.77 across both
  orders); `architecture` is partially blinded; `idiomatic` remains cross-stack-barred. Of the
  five, **only `ux`** clears every gate with a between-stack range above its within-stack
  noise, and it is not reported as a signal because its own scores moved 5 of 8 and 3 of 8
  between identical rounds.

  Tier 3 stays at **weight 0.00**. It has now failed to earn one on evidence rather than on
  argument, twice — once broken, once repaired — which is the outcome the gates exist to
  produce.

- **Superseded, kept: the first partial sweep — 3 calls, $13.15 on `g1_pong`.**
  `g1_pong`. Calls cost **$2.82-$5.29** each (mean $4.38, 450-572 s). Two aspects were
  measured before it was stopped so the deterministic result could be read on its own:

  | aspect | ceiling gate | order-invariance gate |
  |---|---|---|
  | `idiomatic`, seed 0 | scores `[3,3,4,4,3,4,3,3]`, modal 0.625 — **passes** | not measured (only one order ran) |
  | `architecture`, seeds 0 and 1 | modal 0.625 in both — **passes** | **FAILS**: Kendall tau **0.143** over 7 comparable pairs, against a pre-registered floor of 0.5; 4 of 8 submissions changed score between orders |

  The order-invariance failure is a pre-registered falsifier firing, and the metric behind it
  was repaired before the number was reported: it had been computing tau tie-blind, where its
  sibling `independence()` had already been fixed not to. Both readings agree. Nothing is
  scored: tier 3 remains weight 0.00.

- **Whole-game matrix #3 (`wg-audio48-2026-08-14`) — complete, 16 trials, $486.27, all
  `completed`.** Pong mean $25.13 (n=8), Tetris $35.66 (n=8). Its eight 2D-spec arena trials
  are archived separately. **At the $48 cap the invisible 250-turn limit became the binding
  constraint** — one trial stopped at 251 turns with $12 of its budget unspent (FINDINGS #35),
  and the standing configuration is now `--max-turns 1000` with **no budget cap**.

- **g4, the 2D sprite platformer, is built but NOT launched.** Prompt, reference fixture
  (`just verify` exit 0, 19/19 own tests), play-bot (19/19 scored criteria against the
  reference) and 16 mutants. `bot_mutants.py` now pins **36 criteria in both directions
  across four games, plus 2 variants and 3 session-lock controls, 0 expectations unmet.**
  **A pre-launch gate was added on 2026-08-16 and must be run:** measure that the machine can
  build, per stack, before spending four figures on it — half of `wg-arena3d` was lost to a
  system daemon that blocked `execve` of freshly created binaries (FINDINGS #49). One mutant escaped on the first run:
  `player.falls` read "grounded became false" as falling, and a zero-gravity character
  hanging off a ledge passed it. Design, contract and results: `eval/G4-PLATFORMER.md`.
  Launching it is **$274-$583 for its eight trials** (1 game x 4 stacks x 2 — read from
  `wholegame.py plan`, not from the three-game matrices), priced from the 8 measured no-cap
  trials at $34.27-$72.83 each. The range is wide on purpose: uncapped trials of one task vary **2.13x**
  across cells and **1.62x within a single cell**, so no point estimate is honest (FINDINGS #42).
  Needs approval and at least two calibration trials in different cells.

- **The arena task was rewritten on 2026-08-15** — 3D volume, analog input, three enemy kinds,
  materialisation, a score multiplier, gamepad and mouse. The eight arena submissions in this run
  were built against the superseded 2D spec (verified from each trial's own stored prompt) and are
  archived rather than graded alongside the 3D set. `bot_arena.py` is rewritten to 22 criteria,
  12 of them pinned by mutants; `bot_mutants.py` reports 20 criteria pinned across three games,
  0 expectations unmet, and `audio_selftest.py` 37 expectations, 0 unmet.

- **Whole-game matrix #2 (`wg-audio-2026-08-14`) — STOPPED at 11 trials, $241.82.** The task
  now requires looping music, a distinct effect per declared event, and explicit attention to
  presentation and pacing. **Not comparable to matrix #1 on any tier** — the task changed and
  tier 1 went from 9 criteria to 14.

  Measured: 10 `completed`, 1 `budget_exhausted`. `g1_pong` mean $21.02 (n=7), `g2_tetris3d`
  mean $23.20 (n=3) — a 1.10× ratio, not the 1.72× the previous matrix showed, because the audio
  and presentation work is roughly a fixed addition rather than one scaling with game complexity.
  Costs had risen to sit just under the $25 per-trial cap, so it was stopped and relaunched with
  a higher one. Its 8 `g1_pong` trials are the first complete four-stack set under the audio task
  and remain valid evidence **within** that run.

  **The cap turned out to be visible to the building agent** (FINDINGS #33) — a session told
  `--max-budget-usd 7.31` reports exactly 7.31; `--max-turns` tested identically is *not*
  visible. A budget cap is therefore an instruction, not an external kill, so **runs under
  different caps cannot be pooled** and the clustering under $25 is consistent with agents pacing
  to a stated budget. Whether spend actually tracks the cap is being measured by a single
  calibration trial before any full relaunch is committed.

- **The subjective layer's specialist judges.** Six aspects exist and are runnable —
  `fun`, `ux`, `audio`, `idiomatic`, `architecture`, and `fun_frames` (the `diagnostic_only`
  control for `fun`). None is scored. They run separately from `wholegame.py evaluate`, via
  `judge/field_sweep.py`, under a cost ceiling.

  **Reliability is no longer the blocker, for any of them.** Measured 2026-08-23 for $100.84
  (`runs/wg-aspect-reliability`, task 23): six aspects x 5 repeats of one field in one
  presentation order on `wg-g4c` / `g4_platformer`, the only field carrying evidence for all
  six. **All six separate the field** — within-submission SD 0.418 (`audio`) to 0.536 (`fun`),
  resolving 10 to 23 of 28 pairs. **None is in the "cannot ever resolve" branch.** Before this,
  `separation()` had been run on one aspect and one field, so five of six had no measured
  reliability at all. It also refutes #74's reading of `idiomatic` as saturated: bunching within
  a round is not indistinguishability across rounds, because a mean over five rounds lands on
  fifths. Three caveats that cut against it — zero-SE submissions, a non-monotone pair count,
  and gate 0 failing on four of six — are in `judge/JUDGING.md` and FINDINGS #102.

  **This says nothing about the stacks.** Separation is a property of the instrument, not an
  ordering, and **tier 3 stays at weight 0.00**.

  **Verified before spending anything: 12 of the 15 (game, aspect) combinations build a
  non-empty pack.** The three that do not are `g3_arena` × `fun`, `ux` and `audio`, because
  two of that game's eight submissions do not compile and so produce no frames and no sound —
  the fail-closed refusal working as designed. Finding that required fixing a hole in the
  guard itself: it counted the evidence *file* rather than its contents, so a submission
  shipping `{"clips": {}}` sailed through a check whose entire purpose is to stop a judge
  scoring a blank field.

### Not done

- **A stack ranking, and on this evidence there is no honest one to give.** Four independent
  routes have now produced the same null: the spec-change suite (all four 6/6), three
  whole-game matrices on the deterministic tiers, cost (four stack means spanning
  $37.97-$58.85 while one cell alone spans $44.86-$72.83), and the per-criterion within-cell
  comparison above. The only layer left that could separate anything is tier 3.
- **Confidence that the criteria have no false negatives left.** They are pinned in both
  directions — `judge/bot_mutants.py` currently reports **36 criteria across four games, 2
  variants, 3 session-lock controls, 0 expectations unmet** — and that has never yet been
  enough. Three false negatives were found in the first evaluation under the audio task
  (`ball.moves`, `gameover.triggers`, `match.ends` — FINDINGS #34), the first repair of
  `ball.moves` was itself wrong (a proxy, not the property), and two more were found in the
  arena set on 2026-08-16 (FINDINGS #46). Each was found by **adjudicating a failure against
  source**, never by the suite. Assume the next one is there.
- Netcode, multiplayer, and console portability. Researched, not built.
- Statistical power. 2 trials per cell detects large gaps only. If two stacks land close, this
  design cannot separate them — and the spec-change suite already failed to separate four stacks
  that all scored 6/6.

---

## How a submission is graded

Three tiers. The building agent sees none of them — blinding is verified mechanically by
`eval/judge/verify_blind.py`, which scans for the rubric's canary GUID, its reachability from every
ancestor directory, and every criterion id the rubric defines.

| Tier | Weight | What it measures |
|---|---|---|
| **1. Programmatic** | **0.31** | Builds, gate green, lints clean, tests pass, frames render and animate, performance probe — plus, where the task asks for sound, five audio criteria (manifest complete, files decode, nothing silent, effects genuinely distinct by decoded content, music loops and is long enough). 9 criteria, or 14 with audio. |
| **2. Play-bot** | **0.69** | A scripted bot drives thousands of ticks and asserts the game actually plays: collisions resolve, scoring works, the match ends, replays reproduce. Where the task asks for sound, it also asserts every event the run *actually emitted* has a working cue. |
| **3. LLM judge** | **0.00** | One specialist per aspect, each ranking the whole eight-submission field for a game rather than scoring one at a time. **Diagnostic only — contributes nothing to the score, and stays at 0.00 until it passes its validation gates.** |

**Why the judge is unweighted** (see `DECISIONS.md` and FINDINGS #21) — two independent arguments,
which fail differently:

1. **It cannot reorder anything.** Bounded contribution 0.10 against a tightest adjacent gap of
   0.0622 on tiers 1+2 alone. True regardless of noise.
2. **It is noisiest exactly where it would matter.** Score spread 0.308 and instability 0.462 on a
   contested submission, against 0.000 on an uncontested one. True regardless of weight.

Its per-criterion verdicts are genuinely useful and are still reported — it catches surviving
placeholders, tautological tests, and pixel-identical frames that no deterministic tier sees.

---

## Running things

```bash
cd template && just verify            # the one gate (any template)

cd eval
# whole-game matrix
python3 wholegame.py run    --stacks rust,ts,unity,godot --games g1_pong --trials 1
python3 wholegame.py evaluate --run-dir runs/<name> --eval-parallel 1
python3 wholegame.py report   --run-dir runs/<name>

# spec-change bake-off
python3 runner.py check-suite --suite suites/core.toml --template ../template
python3 runner.py run         --suite suites/core.toml --template ../template --trials 3

# the subjective layer runs SEPARATELY, after the deterministic tiers, under a ceiling
python3 judge/field_sweep.py --run runs/<name> --games g1_pong \
    --aspects idiomatic fun --orders 2 --max-cost 60 --out runs/<name>/judge-sweep

# controls - run these before believing any score
python3 judge/audio_selftest.py       # 6 audio criteria vs 9 mutants
python3 judge/bot_mutants.py          # 9 play-bot criteria pinned in both directions
python3 judge/capability_selftest.py  # the no-stack-gap gate, its mutant and its variant
python3 judge/rusage_selftest.py      # peak RSS / CPU against a child of known size
python3 judge/capture_selftest.py     # a flood on either stream keeps the other (#100, #103)
python3 runner_capture_selftest.py    # the same, through runner.py, and that it is ONE policy (#114)

# what the pipeline can see about capture cost - reported, scored by nothing
python3 judge/capability.py --runs runs

# re-grade stored results offline, without re-running agents
python3 judge/regrade_wholegame.py --run-dir runs/<name>
python3 judge/verify_blind.py      --run-dir runs/<name>
```

The eval drives the `claude` CLI directly, not the SDK. `--setting-sources project` is mandatory
and empirically verified: without it the operator's global `~/.claude/CLAUDE.md` leaks into every
arm and confounds the comparison.

**The matrix runs with a targeted Bash allowlist** (`just`, `cargo`, `pnpm`, `git`). The 2026-08-12
bake-off ran without one and lost **29.8% of all turns to denials**, so the two runs are **not
directly comparable**. Recorded in FINDINGS.

---

## The one thing this project actually learned

Thirty-seven numbered findings, and all but a few are instances of one pattern:

> **A mechanism that runs, reports success, and measures nothing.**

Held-out tests that never compiled. A Stop hook silently disabled in every trial. A judge scoring
empty file packs. A criterion asking about file layout the anonymiser had already destroyed. A
`verify_blind` "pass" read from `tail`'s exit code rather than the scanner's.

Four later findings are worse than that shape and worth separating:

- **#19** — a mechanism that measures something and hands you a number *that is wrong*. A corrupted
  artifact produced plausible, in-range readings that were published as fact before the guard
  caught them. Indistinguishable from a real result at the moment you act on it.
- **#22** — a summary statistic that was arithmetically correct and referentially empty. A mean
  computed across four real runs and four non-events described no trial that ever ran, and
  manufactured a finding that survived scrutiny until the population was split.
- **#30** — a guard whose trigger condition named an *external* cause, applied to a failure with an
  *internal* one. It ran, matched, retried and reported, and could never have fired: the lock it
  waited for was held by its own caller. A correct diagnosis with the remedy addressed to the wrong
  agent.
- **#31** — the first defects here that would have failed **open**. Everything above fails closed:
  wrong, but reported. A harness that excuses a real failure because a log note contained the word
  "lock" reports nothing at all, and produces a *higher* score than the truth on work that did not
  earn it. **A fail-closed defect costs you trials; a fail-open defect costs you the result.**

The distilled rules, in order of how much they would have saved:

1. **A negative control is necessary and not sufficient.** `total=0 passed=0` is indistinguishable
   from "correctly failing". Every task needs a positive control that proves the grader can go
   green, and ideally an adversarial one.
2. **Never infer a process's state from its artifact's state.** An artifact mid-write is
   indistinguishable from one never written. Check the exit code the process reported.
3. **A pipeline's exit status is the last stage's.** `cmd | tail` reports `tail`.
4. **Never compute a mean over a population you have not established is homogeneous.** Partition by
   terminal status first; report `n` per group.
5. **LLM judge stability is a property of the artifact, not the rubric.** Validating a judge on
   clear-cut fixtures systematically overstates its reliability, because criteria agree when the
   answer is obvious and diverge when it is borderline — which is exactly when you need them.
6. **An artifact is MORE order-invariant than a judgement, not less.** Three of the subjective
   layer's four gates are statistical, and all three passed the one aspect that turned out to be
   ranking a harness quantity. Two judges with *no evidence in common* ranked the field
   identically, twice. **Statistical validation cannot distinguish a judge that reads its
   evidence from one that does not** — only reading the evidence can (#55).
7. **A repeated identical measurement across independent subjects is not corroboration.** It is
   the signature of a shared cause, and the shared cause is usually the instrument: six
   submissions scoring an identical 6/14 was `$TMPDIR` deleting their toolchains (#45); six
   failing two criteria with byte-identical evidence was a bot that stood still until it died
   (#46).

---

## Keeping this current

`README.md`, `DECISIONS.md` and `eval/FINDINGS.md` must not go stale. Update them in the same
working session as the change, not later:

| When | Update |
|---|---|
| A decision is made or changed | `DECISIONS.md` |
| A run completes, or its results change | `README.md` status section, with real numbers |
| Something ran and measured nothing | `eval/FINDINGS.md` — a new numbered finding |
| A published number turns out wrong | Correct it, and mark it in `eval/FINDINGS.md` if it was acted on |
| Weights, rubric, or grading change | `eval/judge/RUBRIC.md` **and** the grading table above |

These documents state what is true now. Replace superseded content rather than annotating it. The
exception is a published number that turned out wrong — that gets marked, because someone may have
acted on it.

**Quote numbers you have just re-read from their source**, not from memory. Several figures in
earlier versions of these documents were quoted after the underlying evaluator had changed.
