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
- `eval/judge/tier1_census.py` — 68 stored trials, **7 with any tier-1 failure**, and in **0 of 10
  groups do both tiers vary among the trials tier 2 could measure**. Comparing the two schemes
  pairwise at w1=0: **0 orderings reversed, 3 coarsened, 7 identical** (#119).

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

### One authoritative path per skill — decided 2026-08-23

`.claude/skills/<name>/SKILL.md` is the **only** location for a skill. There is no per-CLI copy,
and `docstat.py --sweep` exits 1 on any `SKILL.md` outside that root.

`.agents/skills/` held a Codex-flavoured duplicate of the skills from the first commit until
2026-08-23, when it was deleted (task 27). The three measurements that decided it, in full in
#99: the only Codex-adjacent sibling — `game-research-gpt` — has no `.agents/`, no `SKILL.md`
and no root `AGENTS.md`, so it was never a reader; the mirror was **never once in sync**, with
`add-game` 39 lines short in the initial commit and `tasks` and `prune` absent entirely; and
after the initial import it took **0 edits that changed a procedure, against the authoritative
tree's 6**.

It was deleted rather than synchronised because a copy with no reader has nothing pulling it
back into line — three of six files were identical on the morning the ticket was read and four
of six differed by the afternoon.

**Cross-tool support was considered, not overlooked.** The repository is MIT and public and a
non-Claude agent reading it is not hypothetical. The judgement is that such a reader is better
served by `AGENTS.md` pointing at one tree than by a second tree that is confidently wrong: the
deleted `add-game` omitted the `prompt_guard.py` procedure entirely, and the deleted `audit-docs`
asserted that `--max-turns` and `--permission-mode` belong to the Codex CLI when
`eval/runner.py:510,519` passes both to `claude`. If cross-tool support is wanted, add a
**pointer** to `.claude/skills/`; a pointer cannot drift from content it does not hold.
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
| **structure** | does the file parse as the thing it is read as? | 5 of 7 skills had unparseable frontmatter; `AGENTS.md` rules 10-16 detached from their own list |

Two boundaries hold the structure half at 0 false positives, and both are the same rule — *a
gate that fails on correct input gets disabled*:

- It asks about a continuation under a **2+ digit** ordered marker, not about indented blocks in
  general. The general form fires on `tasks/` files where nothing is wrong.
- It does not read `eval/findings/`, `eval/FINDINGS.md` or `eval/RUNS.md`. The archive records
  what was true when it was written, including the broken shapes it is about; reformatting one to
  satisfy a gate edits evidence.

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
| **LIVE**, gated | every other tracked markdown — `README.md`, `DECISIONS.md`, `eval/RUNS.md`, `eval/judge/RUBRIC.md`, `eval/judge/JUDGING.md`, `eval/PROTOCOL.md`, `research/`, `template*/`, `eval/starters/`, `.claude/skills/` |

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
- **The rubric ceiling — MEASURED, and for tier 1 it is now RESOLVED; for tier 2 it is not.**
  Tier 1 returned **1.0 on all 24 submissions of `wg-matrix`** and on all 16 of `wg-audio48` —
  40 of 56 matrix trials at the ceiling with *zero* variance, not merely near it (#92). **What to
  do about it was decided on 2026-08-23: tier 1 became a gate** (see "Tier 1 gates, it does not
  score" above, and #119). The ceiling did not go away; it stopped being reported as a score.
  **Tier 2 is still at the ceiling on 24 of 56** — `wg-audio48` and `wg-g4c` entire — and tier 2
  now carries the whole weight, so **`overall` is a constant 1.000 for all 16 `wg-audio48` trials
  and all 8 of `wg-g4c`.** That is the open half, and it is the more serious one: an instrument
  whose only scored tier saturates on a whole run cannot rank anything in it. The remedy is harder
  play-bot criteria or harder tasks, not a weight.
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
Six stored directories hold a manifest that does not describe them (#93, #119). None was edited.

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
| `eval/suites/*.toml`, `eval/suites/prompts.py` | **The sole copy of what those 71 trials were asked to do.** A trial record stores `task: "t1_rally"` and no prompt text; 0 files under `eval/runs/` contain it (#119) |
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
| Separation figures reported under `rank`+`pool` | A field where the **ceiling gate passes on both orders**. The choice rests on scores saturating (6-7 of 8 on one modal value); on an unsaturated field a score-based figure loses its handicap and the comparison should be re-made. `field_ranks.py` prints all four either way |
| Code aspects are within-stack only | **Never on a better anonymiser.** The judge identifies the language from syntax, so only a change to what is being asked could re-open it |
| Deterministic tiers may not rank stacks | Any instrument change producing **non-zero within-cell verdict variance** — currently 0 of 380 |
| Tier 1 gates rather than scores | `tier1_census.py` reporting **DISCRIMINATES** — a group where both tiers vary among the trials tier 2 could measure. Currently 0 of 10. Adding a tier-1 criterion with real headroom is what would do it, and it would need a mutant *and* a variant before it counted |
| The play-bot tier carries 1.00 | `weight_sensitivity.py` reporting **FLIPS on a group whose variance is not a confound** — it needs a second scored tier to be worth re-running for that, so this re-opens only alongside the row above |
| No budget cap, `--max-turns 1000` | A trial **reaching 1000 turns**. The 250 limit became binding without anyone noticing (#35); the same failure at 1000 would mean the backstop has become an instruction |
| 2 trials per cell | A stack difference landing inside the ~0.015 the design cannot separate — at which point n=2 is the constraint, not the evidence |
| Performance fields are captured, not scored | `capability.py` reporting **real variance in `capture.megapixels`** across a run. At that point capture geometry is a choice submissions actually exercise and it is worth asking whether the judges should see it. Currently 62 of 68 sit on the starter default |
| No frametime or fps field | The TypeScript capture path getting a **real GPU backend**. Nothing else changes it: the asymmetry is the renderer, not the stack (§3 of the capability matrix) |
| Harness lint is a recipe, not a gate | `PLW1510` and `BLE001` **staying at 0 across a working week** without anyone tending them. At that point a gate costs nothing to add and would catch the next site before it is written; today it would fire on a backlog nobody has triaged and be disabled |
| The `template*/` trees and the spec-change suite are retired | A decision to **run spec-change trials again**. Then restore from git rather than re-forking: `git checkout <pre-retirement> -- template-ts/`. Note what re-opening costs — the trees are frozen at 2026-08-23 and every starter repair since then is missing from them, which is the drift that closed them in the first place |
| One authoritative path per skill | A **maintained** non-Claude consumer — a sibling that actually reads a skills tree and edits it. The 2026-08-23 measurement was 0 readers and 0 content-bearing edits in 3 commits; a copy that anyone maintains is a different object from the one that was deleted. Even then the first question is whether a pointer serves it, since a copy reintroduces the drift, not the reader |

The rows with no entry here are not exempt; they are decisions where the owner's judgement is the
input and no measurement would overturn them.

## Keeping this current

Update in the same session a decision is made or changed. Replace superseded entries rather than
annotating them — this file states what is true now, not how it got here.
