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

Byte-identical prompts are not neutral — they end up written in one stack's vocabulary and bias the
comparison. `--setting-sources project` is empirically verified: without it the operator's global
`~/.claude/CLAUDE.md` leaks into every arm.

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
| Programmatic — builds, gate green, lints, tests, frames render and animate | **0.31** |
| Play-bot — a scripted bot drives thousands of ticks and asserts the game plays | **0.69** |
| LLM judge — one specialist per aspect, each ranking a whole eight-submission field | **0.00** — diagnostic only |

**The judge is unweighted for two independent reasons, either sufficient:**

1. **It cannot reorder anything.** Bounded contribution 0.10 against a tightest adjacent gap of
   0.0622 on tiers 1+2 alone. Holds regardless of noise.
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

## Task set and judging protocol

| Decision | By |
|---|---|
| Add a **fourth game: a 2D sprite platformer with attacks** (Castlevania-style) | [user] |
| `stage.completes` is **diagnostic, not scored**, until it passes three awkward reference levels | [agent] |
| Subjective judges **run repeatedly until the decision resolves**, not a fixed number of times | [user] |
| The judging layer **stays in Python** — no Workflow port for now | [user] |

The platformer stresses machinery the other three games do not: sprite sheets and animation state
machines, attack hitboxes with active frames, knockback and invulnerability windows, platform
collision. Pong, Tetris and arena all tied; a game exercising different systems is the most
plausible remaining route to discrimination.

Repeated judging resolves per **pair** with a Wilson interval, not per score, and stops sampling a
pair once it resolves. Protocol and its limits are in `eval/judge/JUDGING.md` — including that at
affordable N the instrument can detect an ordering but **cannot statistically prove a tie**, which
is the outcome this project is most likely to reach.

## What the deterministic tiers may and may not be used for — decided 2026-08-16

**Decided [agent], on measurement, and it constrains every claim this project can make.**

Comparing the two independent trials in each of the twelve cells criterion by criterion:
**0 of 380 verdicts differ, while 219 of the 380 evidence strings do.** The two submissions in
a cell are different artifacts; the instrument returns the same grade on both.

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
- `agent.final_text` must be read before grading. Nothing in the harness reads it, and it
  contained the mechanism for a day.
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

---

## Open

- **The matrix result.** No stack ranking exists, and the deterministic tiers cannot produce
  one — see above. Tier 3 is the only remaining layer that could.
- **Statistical power.** With 2 trials per cell, if two stacks land within ~0.015 this design
  cannot separate them. The earlier spec-change suite already failed to separate four stacks that
  all scored 6/6.
- **The rubric ceiling.** A real agent-built TypeScript Pong scored 13/13 unanimously, six times.
  If matrix submissions cluster at 12–13/13 the tier is uninformative at the top end regardless of
  stability — not yet checked against matrix data.
- **Whether the subjective layer earns a weight — ANSWERED 2026-08-16, and the answer is no.**
  All five aspects were run over a full eight-submission field for $46.79. Three fail the
  ceiling gate on one presentation order; `fun` and `idiomatic` fail adjudication (#52, #53);
  `architecture` and `ux` are redundant with each other while sharing no evidence (#54). Its
  between-stack range (1.70 rank positions) is **smaller than its within-stack spread (2.05)**.
  **Tier 3 stays at weight 0.00**, now on measurement rather than on argument. All three
  prerequisites were then BUILT and the layer re-run (2026-08-17, $21.05): `fun` has a
  representative play session and its confound is gone by construction, `architecture` packs
  are extension-blind, `idiomatic` is accepted as within-stack only. **The verdict did not
  change** — only `ux` clears every gate, and gate 0 (reproducibility, added the same day)
  shows ceiling verdicts flipping on provably unchanged input in 3 of 6 clean repeats.
  Re-opening now requires repeats at a fixed order, not more aspects.
- **g4, the platformer, is designed and NOT launched.** Launching needs approval and at least
  two calibration trials in different cells; the honest cost range is $800-1,900 (#42).

---

## Keeping this current

Update in the same session a decision is made or changed. Replace superseded entries rather than
annotating them — this file states what is true now, not how it got here.
