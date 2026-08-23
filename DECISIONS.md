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
- **The rubric ceiling — CHECKED against matrix data 2026-08-23 for the deterministic tiers, and
  it is worse than "clustering".** Tier 1 returned **1.0 on all 24 submissions of `wg-matrix`**
  and on all 16 of `wg-audio48` — 40 of 56 matrix trials at the ceiling with *zero* variance, not
  merely near it. Tier 2 is at the ceiling on 24 of 56 (`wg-audio48` and `wg-g4c` entire).
  `wg-audio48` returns **1.0 on both scored tiers for all 16 trials**: its whole deterministic
  grade is a constant. Measured by `eval/judge/weight_sensitivity.py`, FINDINGS #92.
  **Tier 1 is a floor test that works, weighted 0.31 as though it discriminated.** It still
  catches the submission that fails outright (`wg-arena3d` 0.0, `wg-g4c` 0.857), which is worth
  keeping — but it separates nothing among submissions that pass. What remains open is what to do
  about it: whether to keep the split, re-scope tier 1 explicitly as a gate, or add criteria with
  headroom. That is task 27, and it is a rubric change requiring mutants, not a doc edit.
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
> and on `wg-g4c-2026-08-21` they do not (#95).** That run carries 23 stale files in 222, and
> the loss is uneven *within* a stack as well as across one — `unity__t0` 6 against `unity__t1`
> 4, `ts__t0` 1 against `ts__t1` 2. Two submissions of the same stack were therefore shown
> different amounts of their own code, so **neither a cross-stack nor a within-stack code-aspect
> reading is available on that field.**
>
> Check before relying on this permission, at the run you are actually reading:
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

**This decision does not license showcasing what cannot be observed.** The evidence pipeline
currently captures no performance signal at all, and `ux` — the aspect most sensitive to visual
richness — was retired for correlating +0.53 to +0.73 with distinct-colour count (#59). Prettier
output moves that metric in the direction that looks like improvement, for the reason it was
retired. So capability work is gated on making capability observable by a signal that is not
palette-coupled (task 25), or it cannot be shown to have helped.

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

Measured on that rule: 14,192 files, 1.109 GB of 138.146 GB — 99.20% of `eval/runs/` is
regenerable. **Reclaiming the 137 GB remains task 10's call**, and nothing was deleted here.

**Where the copy goes is still open.** The current copy at `/Users/stefano/game-research-evidence`
is on the same physical disk as the original and is therefore not a backup — it survives `rm -rf`
and a bad `git clean`, and nothing else. This machine has no external disk, no `rclone`/`restic`
remote, and its only cloud target is the operator's personal iCloud Drive, which is not somewhere
project evidence belongs. Every evidence file is under 50 MB, so an external disk or a private
GitHub repo would each work without LFS; both need the operator's go-ahead.

---
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
| Code aspects are within-stack only | **Never on a better anonymiser.** The judge identifies the language from syntax, so only a change to what is being asked could re-open it |
| Deterministic tiers may not rank stacks | Any instrument change producing **non-zero within-cell verdict variance** — currently 0 of 380 |
| Tier weights 0.31/0.69 | `weight_sensitivity.py` reporting **FLIPS on a group whose variance is not a confound**. Currently 0 of 10 groups flip, and the one group with both tiers varying is `wg-arena3d`, which `eval/RUNS.md` declares void (#92) |
| No budget cap, `--max-turns 1000` | A trial **reaching 1000 turns**. The 250 limit became binding without anyone noticing (#35); the same failure at 1000 would mean the backstop has become an instruction |
| 2 trials per cell | A stack difference landing inside the ~0.015 the design cannot separate — at which point n=2 is the constraint, not the evidence |

The rows with no entry here are not exempt; they are decisions where the owner's judgement is the
input and no measurement would overturn them.

## Keeping this current

Update in the same session a decision is made or changed. Replace superseded entries rather than
annotating them — this file states what is true now, not how it got here.
