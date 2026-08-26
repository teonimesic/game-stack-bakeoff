# Whole-game evaluation rubric

CANARY: `wholegame-rubric-4f2a91c8-7b3d-4e16-9a05-c1d8e37b6f20`

> The canary string above exists so blinding can be *tested* rather than asserted.
> `verify_blind.py` greps every trial working directory, every ancestor of it, and every
> agent transcript for that GUID. If it ever appears outside `eval/judge/`, the run is
> contaminated and must be discarded. (Borrowed from Terminal-Bench, which puts canary
> GUIDs in task files as a training-contamination tripwire.)

**This file must never be reachable from a trial working directory.** The building agent
gets the game spec and the full template; it does not get this. Everything here — the
criteria, the thresholds, the weights — is hidden. See `verify_blind.py`.

---

## Why the tiers are ordered this way

Four independent 2025–26 studies put VLM game-test oracles at **~50% accuracy, near
chance on temporal properties** (`research/09-game-testing-sota.md`). A vision model
asked "is this game fun" is a coin flip. So the evaluator is built the other way up:

| Tier | Answers | Weight | Method |
|---|---|---|---|
| 1. Programmatic | Does it build, gate, lint, test, render? | **GATE — not scored** | scripts only |
| 2. Scripted play-bot | Does it *behave* like the game it claims to be? | **1.00** | deterministic driving via the probe protocol |
| 3. LLM judge | Is the code any good; is the result coherent? | **0.00 — DIAGNOSTIC** | a different model, binary criteria, blind |

The play-bot tier carries the whole weight because it is the only tier that is both
*about gameplay* and *deterministic*.

**The judge tier scores ZERO. It still runs, and its per-criterion verdicts are
reported as a diagnostic, but its aggregate contributes nothing to `overall`.**

Two independent arguments led there. They are worth keeping separate because they fail
differently — if one were refuted the other would still stand.

**1. It cannot reorder anything.** Even at the 0.10 weight it briefly carried, the
judge's maximum contribution swing was 0.0154 against a tightest adjacent gap of
0.0622 between submissions on the deterministic tiers — a factor of four. The ordering
of every submission measured was identical with the judge at its minimum and at its
maximum. This holds *regardless of how noisy the judge is*.

**2. Its aggregate is noisiest exactly where it would matter.** Six judgings of one
unchanged submission, repeated on two different submissions:

| submission | score spread | instability | contested criteria |
|---|---|---|---|
| uncontested (a good agent-built Pong) | **0.000** | 0.000 | 0/13 |
| contested (the `broken` fixture) | **0.308** | up to **0.462** | 5/13 |

This holds *regardless of the weight*. See FINDINGS #21.

At 0.10 the judge cannot swing a verdict. It still has to be *measuring* something: if
it cannot separate a working game from blank frames it should be **dropped entirely**
rather than weighted down, because a small weight on pure noise looks like signal in the
final table.

Within each tier every criterion is **binary** and weighted equally. Binary criteria are
calibratable against human labels; 1–5 scales are not
(`research/05-eval-harness-design.md`). The tier score is `passed / total`. The overall
score is the weighted sum. **Per-criterion results are always reported**, so a single
criterion cannot dominate silently.

---

## Tier 1 is a GATE, and here is the measurement that made it one

**Decided 2026-08-23 (task 29). It used to carry 0.31 of `overall`.** That split appeared
in this repository's first commit, was quoted in four documents, and was derived in none
of them — not in the docs, not in a code comment, and not anywhere in 139 commits of
history. There was no derivation to state, so the question became what tier 1 is *for*.

Two offline sweeps answer it, both re-runnable and both able to come out the other way:

| tool | what it reports today |
|---|---|
| `weight_sensitivity.py --all --runs-root <main checkout>/eval/runs` | 10 groups, **FLIPS=0** at every weight in (0,1); **7 of 10 UNIDENTIFIABLE** — tier 1 returns a single value across the whole group, so the weight cannot act (#92) |
| `tier1_census.py --runs-root <main checkout>/eval/runs` | 69 stored submissions, **8 with any tier-1 failure**. In **0 of 11** groups do both tiers vary among the trials tier 2 could measure. Verdict **FLOOR-ONLY** |

**Read the caveat on the first before quoting it.** `weight_sensitivity.py` sweeps the
*open* interval, because w1=0 and w1=1 discard a tier outright and are not candidate
weightings. The gate regime **is** w1=0 — outside the interval it sweeps — so `FLIPS=0`
is not evidence that this change moves nothing. The question at that point is asked by
`tier1_census.py`, which compares the two schemes pairwise: **0 orderings reversed, 3
coarsened, 8 identical.** Every distinction the gate removes is one tier 1 made alone.

What the census found tier 1 actually doing, across every trial it has ever scored:

- **2 trials** failed a criterion tier 2 depends on — both the `syspolicyd` build failure
  of #49 — and both scored 0.00 on tier 2, which is the same fact told twice.
- **6 trials** failed only other criteria: one Godot lint finding, one Unity lint finding,
  three of a TypeScript submission's own unit tests, one frame whose ink coverage was
  0.881 against a window ending at 0.85, and the first scene, which failed three criteria
  to an interrupted build and `render.nonempty` to a ceiling that was a game's. The five
  games among them scored **1.000** on tier 2.
- Every one of the 14 criteria has failed at least once, so none is dead weight. What
  `render.nonempty` in particular has ever done is below, and it is not what it looks like
  from this count.

So tier 1 separates a submission that fails outright from one that does not, and has never
separated two submissions that the play-bot could tell apart. As 0.31 of a quality score
that made a lint finding read as a **4.4% worse game**. As a gate it reads as what it is.

### What the gate does, and what it deliberately does not do

```
gate = PASS iff every SCORED tier-1 criterion passed
     - an EMPTY tier is not a pass: `total=0 passed=0` is fail-closed (`usable: false`)
     - a `scored: false` criterion is excluded from the question, not counted as failed
       (the engine project-lock exception, FINDINGS #25)
```

- **A gate failure does not deduct.** Deducting is the scheme being removed.
- **A gate failure does not exclude the trial.** Every reason not to count a failure is a
  channel a bug can widen (rule 7). The trial is reported, with the failing ids named.
- **`build.compiles` and `probe.responds` are BLOCKING**, and the record says so in the gate's
  own blocking_failed field. The play-bot drives the submission through `just probe`, so a
  project that does not build or whose probe never answers cannot produce tier-2 evidence:
  `score_is_independent` goes false and its `overall` restates the gate rather than adding
  to it. Corroborated over the corpus — blocked trials have tier 2 = 0.00 (2 of 2), trials
  failing only other criteria have tier 2 > 0 (6 of 6). `render.frames` is **not** blocking:
  the bot drives the probe, not the film.

**What would re-open this.** `tier1_census.py` prints `DISCRIMINATES` on its **headline**
verdict the day any group has both tiers varying among measurable trials — which is what
adding a tier-1 criterion with real headroom would do. The decision then has to be re-made,
not inherited.

> **The headline, not the second line.** The tool also prints *"verdict if every grading
> were pooled instead"*, and that one already reads `DISCRIMINATES`. It is not a trigger: it
> pools 16 superseded `wg-g4c-capgate` gradings of 8 work trees `wg-g4c` already contributes.
> Those gradings are dated **2026-08-21**; `bot_platformer.py` was repaired four times on
> 2026-08-22 (#82, #89 and task 18). 14 of the 16 agree with the 2026-08-23 grading of the
> same work tree to the digit. The 2 that disagree are `ts__t0` at 0.70 and `unity__t0` at
> 0.85, both 1.00 after the repair. `unity__t0` lost exactly `attack.damages`,
> `score.on_kill` and `knockback.applied` — the three criterion ids those commits name;
> `ts__t0` lost those three and `enemy.damages_player`, `invuln.window`,
> `gameover.triggers`, which are the criteria the target-selection repair (#82) governs
> without naming. The headline counts one row per submission, most recent
> grading; the pooled line exists so the difference is visible rather than chosen quietly
> (task 75).

`gate_selftest.py`
pins the gate in both directions: mutants that make it unable to fail, and variants — the
lock exception, an audio-less task, a broken film recipe — that it must still pass.

**Stored scores were not rewritten.** 14 of 68 stored `overall` values would move under the
gate scheme (largest 0.2273, a submission whose tier 2 was 0.267 and which the 0.31 cushioned).
They stay as they were written; the regime boundary is recorded in `eval/RUNS.md` and every
new record carries `scoring_regime`.

---

## Tier 1 — Programmatic (9 criteria, script-answered)

Implemented in `static.py`. Never shown to the judge as a question. **Scored as a gate, not
as a fraction of `overall`** — see above.

| id | criterion |
|---|---|
| `build.compiles` | Does the project build / type-check cleanly? |
| `verify.green` | Does the repository's own gate, `just verify`, pass? |
| `lint.clean` | Does the linter pass with no findings? |
| `tests.exist` | Does the project ship more than a token number of its own tests? (floor: 8) |
| `tests.green` | Do all of the project's own tests pass, with none skipped? |
| `render.frames` | Does the game render frames at all? |
| `render.nonempty` | Do the frames contain something other than a blank background? Mean ink coverage inside a window that is **per task class** — see below |
| `render.animates` | Do consecutive frames of a played run differ? (>0.0005 of pixels) |
| `probe.responds` | Does the headless probe start and advance the simulation? |

Also collected, **reported but not scored** (they are diagnostics, not verdicts —
nobody in the open-source world hard-fails CI on wall-clock performance, and neither do
we): coverage percentages, code file and line counts by extension, the full output tail
of every command, and the nine **capture and performance fields** below.

### Which population each tier-1 bound was calibrated on

**Tier 1 GATES**, so a bound calibrated on one task class does not cost a correct member of
another a fraction of a score — it stops that submission being scored at all. The question
*is this bound a property of the artifact, or of games?* is therefore asked of every tier-1
criterion, and the answer is kept as code in `static.TIER1_BOUND_POPULATION` rather than in
a paragraph, so a criterion added without an answer fails
`static.assert_tier1_bounds_declared()`.

| population | criteria | why it transfers |
|---|---|---|
| `no_bound` | `build.compiles`, `verify.green`, `lint.clean`, `tests.green`, `render.frames`, `probe.responds`, `audio.manifest`, `audio.files_exist` | they read an exit status, a file count or a boolean. There is no number to calibrate |
| `starter` | `tests.exist` (floor 8) | every starter already ships more, and both classes are built from the same four starters |
| `capture_contract` | `render.animates` (>0.0005) | a property of `just film`, identical in both classes; a scene is a timed sequence and must move too |
| `audio_signal` | `audio.not_silent`, `audio.distinct`, `audio.music_loops` | dBFS floors and spectral similarity. Not asked of a scene at all |
| **`task_class`** | **`render.nonempty`** | the ceiling does not transfer — below |

### `render.nonempty`: the floor transfers, the ceiling does not

| task class | window (inclusive) |
|---|---|
| game | 0.001 – 0.85 |
| scene | 0.001 – 1.00, i.e. a floor and no ceiling |

**The floor is a property of the starter.** It is the floor the four render harnesses use in
their own `renders a non-empty frame` test, and the starter's placeholder marker covers 0.0015
of a 640x400 frame — anything tighter measures *the placeholder is small*. A **blank scene
frame still fails**, and `judge/ink_window_control.py` pins that row.

**The ceiling was a property of nothing.** 0.85 applied to every task from this repository's
first commit and is derived in no document, no comment and no commit message — the same shape
as the 0.31/0.69 split retired above. What it has done, from the producer:

```bash
python3 judge/ink_window_control.py --runs-root <main checkout>/eval/runs
```

The population is **69 submissions** — 68 games and 1 scene, the most recent grading of each,
from 85 on disk with 16 superseded and held out, which is `tier1_census`'s population and its
walker rather than a fifth glob. Among those 69, `render.nonempty` has fired **4** times:

| trial | mean ink | hit | what it was |
|---|---|---|---|
| `wg-arena3d` `g3_arena__rust__t0` / `t1` | 0.0 | floor | **0 frames** — `just check` exited 101 (#49). `render.frames` reports the same fact in the same record |
| `wg-g4c` `g4_platformer__godot__t1` | 0.881 | ceiling | a night platformer over a gradient sky. **Tier 2 = 1.000** |
| `wg-scene-s1ts` `s1_parallax__ts__t0` | 0.966 | ceiling | sky, road and scenery — the scene drawing what it was asked to draw |

So the ceiling has **0 true positives and 2 false negatives**, and the floor has never fired on
a frame that was rendered at all.

**For a scene the ceiling's sign is inverted**, which is why this is a per-class table rather
than a wider number. `eval/SCENES.md` contracts a scene to fill the frame — `s1_parallax` asks
for a layered background with real distance in it, `s2_glass` for a full 3D render — and a
large flat region is the naive implementation `scene_probe` exists to catch. There is no ink
level from which a scene can be inferred defective from above. That is read off the task
contract, not off the one submission that exists: 0.966 passes, and so would 0.87 or 0.999.

**The game ceiling is left where it is, and not because it is right.** Moving it changes a
stored *game* gate verdict and the figure three live documents quote, which is a re-scoring
event on the game population with a ticket of its own (`tasks/168`).

`judge/ink_window_control.py` pins both directions per class on real pixels, drives `collect`
end to end with the toolchain stubbed so the class it was handed is proved to reach the
criterion, and carries a mutant per mechanism.

### The performance fields — captured since 2026-08-23, scored by nothing

`judge/capability.py` is the contract: same names, same units, all four arms, measured
from **outside** the submission so no arm can fail to report one (#97, DECISIONS.md).
Read a stored run with `python3 judge/capability.py --runs eval/runs`.

| field | unit | from |
|---|---|---|
| `capture.width_px` / `height_px` / `megapixels` | pixels / Mpx | the frames' own PNG headers |
| `capture.frames` | count | PNGs `just film` wrote |
| `capture.wall_seconds` | s | `commands[film].seconds` |
| `capture.cpu_seconds` | s | user+system CPU of the whole `just film` tree |
| `capture.peak_rss_mb` | MiB | peak RSS of the largest process in that tree |
| `probe.ticks_per_second` | ticks/s | `just probe` answering over a pipe, headless |
| `probe.startup_seconds` | s | exec to the tick-0 line |

**None of these may be read across arms as a rendering result, and there is deliberately
no frametime or fps field.** The TypeScript arm films on SwiftShader, a CPU rasteriser,
while the other three film on the machine's M3 Max — so any render-timing figure would
report the backend, not the stack. `capability.DECLINED` records that and six other
candidates, each with what would move it back in.

`capability.no_stack_correlated_gap()` fails if a declared field is ever absent for a
reason other than the submission's own capture failing; its mutant and its variant are
in `capability_selftest.py`. `rusage_selftest.py` pins the two new figures against a
child of known size — `ru_maxrss` is bytes on macOS and kilobytes on Linux, and the
1024x error would still look like an answer.

---

## Tier 2 — Scripted play-bot (13–22 scored criteria per game, 14–23 with audio)

Implemented in `bot_pong.py`, `bot_tetris3d.py`, `bot_arena.py`, `bot_platformer.py`, driven
through
`just probe SEED` — a live stdin/stdout session, so the bot can *read the game's state
and react*, not merely replay a tape. Every criterion asserts on state the game itself
reports.

### Tier 2 is at its ceiling on half the corpus, and that is a task result

`tier2_census.py --runs-root <main checkout>/eval/runs` is the producer. Over 68 stored trials:
**5 of 10 (run, game) groups return a single tier-2 value** across every measurable trial — 35 of
68 trials — and of 11 trials that failed anything, 2 were whole-trial and **9 selective, all of
them from `wg-matrix-2026-08-13`**. Tier 2 has not separated two submissions in any later run.

**Do not respond to that by promoting a diagnostic or adding another criterion of the same kind.**
Both were measured (#128):

- The three withheld diagnostics take a single value, `False`, on all 7 group-criterion pairs
  where they are recorded. Scoring one lowers every submission in its group by the same amount;
  `tier2_census.py` prints that as a `spread?` column so it is a number, not a judgement.
- Four candidates built from requirements the g4 prompt states and no criterion checks — no
  re-trigger mid-swing, enemies patrol, the `land` event fires, replay determinism under a played
  900-tick tape instead of the idle 300 — were driven against all 8 `wg-g4c` submissions and
  **passed 8/8**. The reference passes them too, so they can go green and nothing goes red.

The reading is in `DECISIONS.md`: a binary criterion asks whether a mechanic exists, every
submission implements every mechanic, so the tier is right to return one number and the remedy is
a harder task. The census prints `SEPARATES` the day no group is flat.

Two criteria are common to all three games (`checks.py`):

| id | criterion |
|---|---|
| `determinism.replay` | Same seed + same inputs → same state hash at every tick? |
| `determinism.seed` | Do two different seeds produce different runs? |

`determinism.seed` exists because a game that ignores its seed passes every replay test
trivially. That is the failure mode a determinism check is supposed to catch.

### g1_pong (13)

**Its end-condition criterion is `match.ends`, not `gameover.triggers`.** Pong is first-to-11,
so the thing that ends it is a match WIN rather than a loss. The other three games use
`gameover.triggers`. Both are correct and neither is renamed — but a cross-game audit asking
*"does every game verify its own end condition?"* must read each bot's declared
`end_condition` attribute rather than grepping for `gameover`, which would report a false gap
here. `precampaign_smoke.py` asserts every bot declares one and that it names a real criterion.

`state.shape`, `ball.moves`, `ball.wall_bounce`, `paddle.moves`, `paddle.bounded`,
`paddle.deflects`, `rally.counts`, `rally.resets`, `score.increments`, `serve.resets`,
`match.ends`, + the two determinism criteria.

### g2_tetris3d (13 scored + 2 diagnostic)
Scored: `state.shape`, `well.dimensions`, `piece.spawns`, `piece.falls`, `piece.locks`,
`bounds.respected`, `move.translates`, `rotate.reorients`, `harddrop.locks`,
`piece.stacks`, `gameover.triggers`, + the two determinism criteria.

**Diagnostic only, NOT scored: `layer.clears`, `score.rewards_clears`.**

These are the criteria I most wanted, and they are the ones I could not validate.
`layer.clears` is load-bearing — a game can spawn, move and lock pieces forever and
never remove a layer — so the bot closes the loop over `heights` and the falling
piece's cells and plays greedily. Measured against a known-correct reference
implementation of this exact spec, it **failed to clear a single layer** across
3 seeds x 2 well geometries (5x5 and 4x4) x 5 placement cost functions, including
piece flattening and full `rotate_y` orientation enumeration. It reaches 40-51
placements and stacks out. A 5x5 layer is 25 cells and pieces are 4, so completing one
needs interlocking play a greedy surface heuristic does not achieve.

Scoring a criterion the instrument cannot pass on correct work would manufacture a
false negative for every honest submission, and once averaged a false negative is
indistinguishable from a real failure. So both are measured, both are reported in
`playbot.json` under `diagnostics`, and neither counts toward the score. This is the
mirror image of removing an assertion that could not fail (FINDINGS.md, the
`BALL_SPEEDUP` escape).

**To promote them back to scored:** strengthen the placement policy until it clears on
at least 3 seeds against the reference, or change the task's well geometry to one where
a scripted bot demonstrably can. Do not promote them on reasoning alone.

**And promoting them would not de-saturate anything.** Both are `False` on all 8 stored
`wg-audio48` and all 8 `wg-matrix` Tetris submissions, so scoring them lowers every score
in the group by the same amount and the ordering stays flat (#128). That is a reason to
fix the bot, not a reason to promote the criterion.

### g3_arena (22) — rewritten 2026-08-15 for the 3D/analog spec
`state.shape`, `player.moves`, `move.analog`, `player.bounded`, `wall.graze`,
`enemies.spawn`, `enemy.kinds`, `enemy.materialises`, `enemies.chase`,
`fire.spawns_bullets`, `fire.rate_limited`, `aim.independent`, `aim.three_axis`,
`bullets.kill`, `score.on_kill`, `multiplier.rises`, `multiplier.falls`,
`wave.advances`, `player.takes_damage`, `gameover.triggers`, + the two determinism
criteria.

Three are genre-defining and none can be settled from a frame:

- `aim.independent` — firing direction chosen separately from movement direction.
- `move.analog` — a half-pushed control moves at about half speed. An eight-way
  implementation is pixel-identical and fails this in thirty ticks. It caught a real
  defect on its first run: the reference fixture's own probe coerced every input to a
  boolean, so `0.5` arrived as a full push and `-1.0` arrived as a full push in the
  wrong direction.
- `enemy.materialises` — a newly spawned enemy is unhittable and harmless for a window.
  The bot finds an enemy on the tick it appears and fires into that window, so a game
  that reports the flag and ignores it fails.

**13 of the 22 are pinned by a mutant** (`bot_mutants.py`, 40 criteria across
4 games, 8 variants, 3 session-lock controls, 0 expectations unmet): snapped
analog input, enemies that appear fully formed, one kind wearing three names, a multiplier
that never rises, one that survives damage, a boundary that is never reported, a dropped
depth axis, a volume that does not hold, a bullet every tick, a kill worth nothing,
enemies that pass through the player, and a game that reports itself over and keeps
stepping. The unpinned 9 are `state.shape`, `player.moves`, `enemies.spawn`,
`fire.spawns_bullets`, `aim.independent`, `bullets.kill`, `wave.advances` and the 2
determinism criteria — those 2 are pinned on `ref_pong` over shared code.

**`enemy.kinds` and `enemies.chase` were rewritten on 2026-08-16 (FINDINGS #46).** Both had
failed 6 of 6 driveable submissions, and all six ship four enemy kinds unlocked over
successive waves. The old versions sampled while the player stood still — which is fatal in
this game, so the bot died in wave 1 and `enemies.chase` then measured a corpse. Each now
takes a session of its own:

- `enemy.kinds` **plays** — aim, fire, hold a standoff — so meeting three kinds requires
  clearing waves. Its evidence reports the wave reached, which separates "one kind after
  twelve waves" (a submission defect) from "one kind and never left wave 1" (the bot
  failing to establish its condition).
- `enemies.chase` **circles** one enemy at a fixed radius, measuring per tick whether the
  enemy's own step points at the player, and requiring it to turn when the player moves.
  Contact counts as a chase only when the enemy was already closing, so a collision the
  player caused cannot pass it.

**`ref_arena` was changed at the same time, and that is the load-bearing part.** It used to
spawn all three kinds in every wave — *"a single wave is enough to exhibit the variety the
task requires"* — so `enemy.kinds` was satisfied on the first tick by construction, and no
mutant could have found the defect: a mutant removes the mechanism a criterion names, it
cannot manufacture an input the criterion mishandles. Kinds now unlock at waves 1, 2 and 3,
matching the shape all six submissions chose, and the old criteria failed the repaired
reference with evidence identical to the six real failures.

**Not comparable to any earlier arena run.** The task changed: three dimensions, analog
input, three enemy kinds, materialisation and a multiplier. Tier 2 went from 15 criteria
to 22. See `RUNS.md`.

### g4_platformer (19 scored + 1 diagnostic) — built 2026-08-15, first run `wg-g4c` 2026-08-21
Scored: `state.shape`, `player.walks`, `player.bounded`, `player.falls`,
`platform.lands`, `jump.leaves_ground`, `jump.grounded_only`, `attack.active_frames`,
`attack.faces`, `attack.damages`, `enemy.damages_player`, `invuln.window`,
`knockback.applied`, `anim.states`, `anim.frames_advance`, `score.on_kill`,
`gameover.triggers`, + the two determinism criteria.

**Diagnostic only, NOT scored: `stage.completes`.** Same reasoning as `layer.clears`: it
requires the bot to TRAVERSE an unknown level layout, and a criterion the instrument
cannot satisfy on correct work manufactures a false negative for every honest
submission. It passes against the reference; that says the bot can walk one stage, not
eight. **To promote it:** show it passing against at least three deliberately awkward
reference levels (a pit, a staircase, a ceiling gap). Not by argument.

Its value is `False` on all 8 `wg-g4c` submissions — before the traversal repair and
after it — so promoting it would lower every score in the group by the same amount and
separate nothing (#128).

**The traversal loop was repaired anyway, and reading its FRACTION was the free pre-test
the harder-task decision was gated behind (#139; task 83, `DECISIONS.md`).** `_stage` was a
fourth copy of "walk right" that task 76's unification did not reach: it pressed
`move_right` every tick, jumped only after being stuck for 12, and never attacked. It now
walks toward `goal_x` through `_walk_toward`, stands off at swinging range and attacks
what is in the way, and **holds the jump control while the character is still rising.**
Each step was measured on all eight work trees:

| bot | fraction of goal reached, 8 submissions | what it added |
|---|---|---|
| as shipped | 0.143 – 0.290 | — |
| + `_walk_toward` | 0.143 – 0.327 | a one-tick edge jump |
| + swing while closing | 0.143 – 0.509 | attacks, but walks into the enemy |
| + stand off at 26 to swing | 0.143 – 0.510 | `_combat`'s own reach |
| **+ hold jump while rising** | **0.274 – 0.803** | the rest of the jump arc |

**The single biggest defect was the length of the key press, not the logic** (#139). A
variable-height jump answers *how long the control is held*; a one-tick press reaches
29.0 to 88.4 units across the eight submissions and holding reaches 93.5 to 141.8, against
a widest gap in any of the eight levels of 110. So no level was uncrossable and every one
of them stopped the bot.

**It still must not be promoted, and the reason is now measured rather than argued.** 8 of
8 runs end having taken exactly `hp0` hits with no victory, so the scalar is
`(health pool × distance per hit taken) ÷ goal_x` — the run length is set by the health
bar. And the ordering is not the submissions': Spearman ρ between the shipped bot's
ranking of the eight and the repaired bot's is **0.405**, exact permutation p = 0.163.
**Improving the instrument reordered the field**, which is what a scalar reporting the
instrument looks like (#139). To promote it, the three awkward reference levels above
**and** a bot that does not die of attrition on 8 of 8 real submissions.

**`platform.lands` was repaired after `wg-g4c`, for the same reason one level down.** It
walked off the opening ledge and asserted a landing, which requires a floor to be under
the ledge — level layout the bot has no knowledge of, and in a designed platformer that
is usually a pit. It failed **5 of 6** submissions on the first grading pass. It now
stages the fall by jumping from the platform underfoot, which is a fall onto a platform
in the criterion's own words and needs no level knowledge. Pinned by its existing mutant
*and* a new variant (*the opening ledge overlooks a bottomless pit*). It is now collateral
on the `jump.leaves_ground` mutant by construction, declared there, and its evidence
distinguishes the two failures. FINDINGS #65.

**The bot crosses a gap. That ceiling is gone, and it was two defects, not one** (task
76, 2026-08-23). Until then a level whose ground had pits made `attack.damages`,
`score.on_kill`, `enemy.damages_player`, `invuln.window`, `knockback.applied` and
`gameover.triggers` unmeasurable — the bot walked in and died — so **a submission was
penalised in proportion to how much real platforming it built**, and
`g4_platformer__ts__t0` scored the field's lowest having built the field's most
sophisticated level.

- The bot held **three** inline copies of "walk toward the target". Edge-jumping reached
  `_combat`; `_hurt`, whose whole experiment is making contact with an enemy, had none,
  which is why the two *reach* criteria passed on a pit level while the four *contact*
  criteria went red. All callers now build their inputs through one `_walk_toward`.
- The `PIT_UNDER_LEDGE` variant that declared the ceiling put the far side **680 units**
  away against a jump that clears ~148, so no bot could have crossed it; the six
  tolerances were partly a level-design error in the check. The pit is now the 100 units
  the real submissions shipped, still bottomless, and the variant **tolerates nothing**.

Pinned in both directions: reverting `_hurt` alone turns exactly the four contact
criteria red, and blinding `_edge_distance` turns all six red, while the repaired bot is
green on all 19 scored criteria of the pit level. **`wg-g4c` does not need re-grading**:
its eight stored `playbot.json` files already pass all six on all eight submissions after
the earlier repairs, the one exception being `unity__t0`'s `knockback.applied`, unscored
for the separate reason in #89. The repair matters for the next gapped submission.

**That "crosses a gap" was crossing the SMALLEST gap the submission would allow, and
nothing said so** (#139, task 83). `_walk_toward` presses `jump` on one tick and the character is
airborne on the next, so the guard never re-fires — and eight of eight `wg-g4c` submissions
implement a variable-height jump, where the arc is a function of how long the control is
held. Measured on all eight: a one-tick press reaches **29.0 to 88.4** units, holding
reaches **93.5 to 141.8**, and the widest gap in any of the eight levels is **110**. The
scored criteria are unaffected — `_combat` and `_hurt` walk to an enemy, not across a
level, and re-driving all eight with the traversal repair moves **0** scored verdicts — but
a stated ceiling that is really a ceiling on the key press is the shape #37 keeps
returning in: the check and its control shared the press.

Three are genre-defining and invisible in a still frame:

- `attack.active_frames` — the weapon damages during *part* of the swing. A permanently
  live hitbox renders identically.
- `attack.faces` — the hitbox is on the side `facing` reports, and flips when the
  character turns.
- `invuln.window` — hits are counted per tick *in contact*, so it measures the window
  rather than the size of the health pool.

**16 of the 20 are pinned by a mutant** (`bot_mutants.py`: 40 across 4 games,
0 expectations unmet); the 4 that are not are `state.shape`, `stage.completes` and the
2 determinism criteria, which are pinned on `ref_pong` over shared code. The suite
earned its place immediately — `player.falls`
originally accepted "grounded went false" as evidence of falling, and the zero-gravity
mutant **escaped**, because a character hanging in the air off a ledge is not grounded and
has not fallen. The criterion now asserts a loss of height, which is the property in its
own name (FINDINGS #34).

**Fail-closed.** A probe that will not start, dies, pollutes stdout, times out or emits
malformed lines scores every criterion in the tier FALSE with the reason recorded. It is
never "skipped". `total=0 passed=0` is indistinguishable from correct failure, and this
project has been burned by that exactly that way.

**One exception, and only one: an engine project-lock conflict.** It is the single
failure mode that says nothing whatsoever about the submission, and it can only occur on
the stacks that take a project-wide lock — so scoring it FALSE deducts from a strict
subset of arms, which is bias rather than noise (FINDINGS #25). Those criteria come back
`scored=False` — measured, reported, excluded from the denominator. Sessions are now
serialised per repository so the conflict should not arise at all; the exception exists
because it did.

When *every* criterion is unscored the tier reports `usable: false`. That is **not** a
score of zero and it is **not** renormalised away either — renormalising would let a
submission that cannot be driven inherit tier 1's score, which is the failure this tier
exists to prevent. The score stays fail-closed and `cmd_report` excludes the trial from
every aggregate, printing it for adjudication.

**Every repaired criterion is pinned in both directions, and a VARIANTS suite pins the
other direction still.** `bot_mutants.py` runs each criterion against the reference fixture
(must pass) and against a mutant with the behaviour removed (must fail): walls that do not reflect, paddles that do not deflect, a seed that is
ignored, a non-reproducible seed source, ignored move inputs, locked cells that never
settle, `game_over` never set, enemies on a fixed heading. Plus three session-lock
controls, one of which checks the other two are not vacuous by removing the serialisation
and confirming the criteria go red. Rewriting a criterion as an experiment makes it easier
to pass by construction; without the mutant, "no more false negatives" and "can no longer
fail" are indistinguishable.

It then runs **variants**: correct games the reference deliberately does not resemble, where
*every* criterion must still pass. A 104-tick opening title card, copied from a real Godot
submission; and enemies faster than the player, which is the only way to reach the contact
branch of `enemies.chase`. **A mutant asks whether a criterion can fail; only a variant asks
whether it can still pass**, and every false negative adjudicated in this project has been of
the second kind. The contact branch is the case in point: the reference never takes it, so the
reference, every mutant then shipped and the 3 lock controls were green while it raised
`KeyError` and scored a correct submission 0.000 (FINDINGS #46).

---

## Tier 3 — Subjective layer (specialist judges)

Implemented in `judge.py`. **Model: `sonnet` — deliberately not the model under
evaluation, which is `opus`.** Anthropic's own eval guidance is explicit: use a
different model to evaluate than the one being evaluated.

**Design and rationale live in `JUDGING.md`.** Read it before changing anything here.

### Why the previous rubric was replaced

Across 24 real submissions the 13-criterion generalist judge fired on **2 criteria**.
Ten of the thirteen asked about code quality; **the code dimension produced zero
information**. All apparent discrimination came from two visual criteria — and every
one of those firings was later adjudicated as a **frame-capture artifact**, not a
property of the games (`FINDINGS.md` §26).

So the old tier measured nothing, twice over: the questions it asked most were inert,
and the questions that appeared to work were reading a defect in the harness.

Two structural changes follow, neither of which is "add more criteria":

1. **One judge per aspect**, each holding one lens and going deep.
2. **Each judge scores the whole field.** A judge shown one submission can only ask
   *is this good?*, which saturated at 13/13 on 15 of 24. A judge shown all eight
   submissions for a game must place them relative to one another.

### The rebalance: experience over code

The old split was 10 code / 3 visual. That is backwards for the question being asked.
The deterministic tiers already prove the code works; what they cannot see is whether
the result is a game anyone would want to play.

**These 9 aspects exist.** The ids are the ones `aspects.py` defines and
`field_sweep.py --aspects` accepts; `ASPECTS` is the producer, and `docstat.py --sweep`
fails any live doc that claims to name them all and does not. Nothing else is runnable,
whatever any design table says. 6 are asked of games and 3 of scenes, and
`aspects.applicability()` refuses every other pairing — a scene has no player, so `fun` has
no referent, and a game field carries no scene to be faithful to.

| aspect id | class | judge asks | `sees` |
|---|---|---|---|
| `fun` | game | is this enjoyable, is it paced | `frames+telemetry` |
| `ux` | game | onboarding, presentation, can a newcomer tell what to do | `frames` |
| `audio` | game | does the music suit the game, are the effects readable | `audio` |
| `idiomatic` | game | was the stack used as that stack is meant to be used — **cross-stack barred** | `code` |
| `architecture` | game | could a second enemy type be added | `code` |
| `fun_frames` | game | **`fun`'s control, not a sixth opinion** — the same question, anchors and scale, with the telemetry withheld | `frames` |
| `fidelity` | scene | does this read as the scene it was asked for | `frames` |
| `motion` | scene | does what moves move as though it had mass, or slide at one rate | `frames` |
| `framework_fluency` | scene | did it reach for the engine's own facilities or hand-roll around them — **cross-stack barred, and UNBLINDABLE** | `code` |

**Five opinions and one control.** `fun_frames` is runnable exactly like the other five and
`--aspects fun_frames` is accepted, so a reader told there are five under-runs the layer and
never learns why. What differs is what its answer is *for*: against `fun` it asks whether the
telemetry contributes anything, and against `ux` whether the frames channel is contaminated.
Both were pre-registered before the packs were judged, and the result is in `JUDGING.md` —
neither equality holds, which is the reason `fun` still has a pacing claim. Its briefing is
byte-identical to `fun`'s **by design**, and `aspects_selftest.py` goes red if the two drift;
a control briefed differently from its treatment is not a control.

**It must never be pooled with the scored aspects, and since 2026-08-23 code enforces that.**
`aspects.py` marks it `control_for="fun"`, `field_ranks.assert_poolable` raises on any
population mixing a control with another aspect, and `field_ranks.report` prints the aspects
each pooled figure is over plus every round it excluded. Until then the rule lived in a prose
comment claiming an `Aspect.diagnostic_only` guard that was never set and read by no code, and
`runs/wg-aspect-reliability` pooled 30 rounds of which 5 were the control. That directory today
pools **20** rounds over 4 scored aspects, giving `score`/`pool` **0.5250/0.4000** with the
between-exceeds-within verdict unchanged in all 4 readings, and it names both the control and
`idiomatic` as excluded (task 90, `tasks/146`).

> **A control that does not declare itself to code is a control by convention.** The field
> that was supposed to say so shared a name — `diagnostic_only` — with an unrelated one on
> `probe.py` and the play bots holding criterion ids, so a `grep` for the guard returned
> twenty hits and every one of them belonged to the other mechanism. The field is now
> `control_for`, and `aspects_selftest.py` goes red if nothing sets it.

**Candidates, not built:** game feel, difficulty and tuning, visual coherence, code quality.
Do not name them in a command; `--aspects feel` is rejected by `choices=sorted(ASPECTS)`.

### Scenes: the same tier, three different questions, and one of them cannot be blinded

`eval/SCENES.md` is the authority for the scene class; this section is what a grader needs.
A scene is a timed sequence with no player, so `fun`, `fun_frames` and `audio` have nothing
to be about, and tier 2 is `scene_probe.py` rather than a play-bot. 3 aspects replace the
6, and they ask what the probe cannot compute:

| aspect id | asks | `sees` | may be ranked across stacks? |
|---|---|---|---|
| `fidelity` | does this read as the scene it was asked for | `frames` | yes |
| `motion` | does what moves move as though it had mass, or slide at one unchanging rate | `frames` | yes |
| `framework_fluency` | did it reach for the engine's own facilities, or hand-roll around them | `code` | **no — report per stack** |

**Scene tier 3 is at weight 0.00, like every other tier-3 aspect.** Scenes have an aesthetic
component the probe cannot reach, which makes them the first honest chance to ask whether
tier 3 should ever weigh anything — and that question is answered by a sweep over results,
not by an argument. **There are no scene results**: no scene has been built, so no scene field
has been packed and no round has been run.

**`framework_fluency` cannot be blinded, and that is a property of the question rather than an
unclosed leak.** What it asks *is* which of one engine's APIs appear in the source, so naming
the stack is the measurement. There is no rewrite that helps: `blind_language` here would
delete the evidence the aspect exists to read. It is therefore **reported per stack and never
entered into a cross-stack ranking**, and `Aspect.cross_stack_bar` is what says so to code —
`field_ranks.py` prints the reason and that aspect's per-stack means, alphabetically by stack,
beside every figure it produces for it. **The bar also decides what is pooled, since
2026-08-24**: `assert_poolable` refuses a barred aspect exactly as it refuses a control,
because a pooled figure is itself a between-stack range (`tasks/146`).

**`idiomatic` carries the same bar for the same reason, reached from the other side.** It keeps
its file extensions, because you cannot ask whether a language was written like itself with the
language taken out, and its per-stack means came back identical across 2 entirely different
games (#53).

**`architecture` is a third case and is not barred.** It is blinded, `verify_blind.py` and
`blind_ext_selftest.py` both hold, and a blind judge field still identified every stack from
code content alone — a measured weakness of the blinding rather than a question that names the
stack by construction. `JUDGING.md` holds it; it is not settled here.

**`fidelity` is read against a written statement of the scene, which every scene pack carries.**
"Does this look like the thing that was described" needs the description.
`field.SCENE_STATEMENTS` holds one per scene and `field.build_pack` writes it into a scene pack —
and only a scene pack — as `SCENE.md`. It is the same text for all 8 submissions, so it separates
nothing, and the brief names it. The rendered scene prompt is not a candidate: it exists per
stack, and handing a judge one would name the arm in the evidence.

Because the statement exists, a requirement **no** submission met is a finding about the field
rather than something the aspect cannot see, and `fidelity`'s notes ask for it in `field_note`.
Two gates decide what may be in the statement: `judge/verify_blind.py --packs` for stack tokens,
and `judge/blurb_selftest.py` for `tools/prompt_guard.py`'s criterion and threshold vocabulary,
because a tier-3 opinion told what tier 2 measures is a restatement of tier 2. Both carry a
mutant, and the packer refuses a scene it cannot state rather than packing one without.

**The weight question reads NOT ASKED rather than "no effect".** 2 independent reasons, either
sufficient:

```bash
python3 judge/weight_sensitivity.py --selftest    # SELFTEST PASSED, 12 controls
python3 judge/weight_sensitivity.py runs/*        # groups: 10  FLIPS=0  STABLE=3  UNIDENTIFIABLE=7
```

1. **The population is empty.** All 10 groups the sweep finds are games — 25 `g1_pong`,
   19 `g2_tetris3d`, 16 `g3_arena` and 24 `g4_platformer` stored gradings, and **0** scene
   gradings, because no scene has been built. A sweep over no scene is not a null result
   about scenes.
2. **It sweeps the wrong parameter for this question.** `weight_sensitivity.py` varies `w1`
   over the pair `(tier 1, tier 2)`. The scene tier-3 weight is `w3` over `(tier 2, tier 3)`,
   which this tool does not sweep and which no stored round could answer anyway.

The `--selftest` passing is what makes point 1 a statement about the population rather than
about the instrument: the tool can still find a constructed crossover.

Do not propose a non-zero scene tier-3 weight from an argument. And read #92 before acting on
a null when one does arrive: an inert weight is a question about what the tier has ever
*measured*, not an invitation to tune the weight. `tasks/145` asks it on real data once a scene
matrix exists.

Two of the five opinions read source and three read the played result, which is the intended
rebalance away from the retired rubric's 10-code-of-13. `idiomatic` is carried because it is the
only aspect whose subject is the variable under test — a four-stack comparison should ask whether
the agent used each stack *as that stack is meant to be used*.

Each judge returns a ranking of all 8 submissions in a game, per-submission grades with
reasons, and explicit best/worst calls. Ties are allowed but must be justified — a tie
is a finding, not an escape from deciding.

### Audio

Audio was a **total blind spot**: no task asked for it, no tier examined it, no
criterion mentioned it. The task prompts now require looping background music, a sound
effect for each declared event, and a `just audio-manifest` contract.

**The prompt does not ask for a distinct sound per event, and no criterion here scores
that.** The manifest section leaves sharing to the agent, `audio.distinct` asks only for
a floor (below), and the tier-3 `audio` aspect values well-chosen cues over uniqueness
for its own sake.

**The declared event list is read out of `eval/suites/wholegame_prompts.py`**, which is
where a task exists, rather than transcribed into `audio.py`. A game the suites declare
no events for is **refused**: all five criteria fail with that as the reason, because
nothing is missing when nothing is expected and five passes over no contract is a
mechanism that runs and measures nothing.

Deterministic checks come first, because most audio failures are mechanical:

| id | tier | criterion |
|---|---|---|
| `audio.manifest` | 1 | Does `just audio-manifest` emit valid JSON with an entry for every event the game declares? |
| `audio.files_exist` | 1 | Does every referenced file exist and decode? |
| `audio.not_silent` | 1 | Is each clip actually audible (RMS above a silence floor), rather than a silent file that satisfies the contract? |
| `audio.distinct` | 1 | Are the sound effects distinct from one another, rather than one beep reused under many names? |
| `audio.music_loops` | 1 | Is the music declared looping, and long enough not to be a click? |
| `audio.triggered` | 2 | During a driven run, does every event the game ACTUALLY EMITS have a cue that exists, decodes and is audible? |

`audio.triggered` is stated in terms of what it can observe, not what we would like it
to observe. **Nothing in the probe contract exposes audio playback, so no tier here can
prove a speaker made a sound.** What it does is stronger than `audio.manifest` and
weaker than hearing: the play-bot has already driven the game and made events fire, and
this asks whether each event *that fired* has a working cue — using the events the run
produced rather than the ones the task declared. A game that declares six events, emits
four, and ships cues for three fails this and passes nothing else.

`audio.distinct` compares **decoded samples**, never filenames and never file hashes,
so one beep re-encoded at five different sample rates is one sound. Its floor is
`max(2, ceil(n / 2))`, where `n` is the number of declared events — half of them rather
than all, because the task permits two events to share a sound. What must fail is one
clip reused everywhere.

**Numerator and denominator range over the same set.** Groups are counted over the
declared events' `sfx` entries and the floor comes from the declared events, so an
undeclared entry counts for nothing here in either direction. It does not fail
`audio.manifest` either: the prompt asks for an entry per declared event and forbids no
others, and failing a legitimate extra cue would be fail-closed and would cost trials.
Undeclared entries are still decoded and still answer `audio.files_exist` and
`audio.not_silent`, whose numerator and denominator are both the manifest — there an
extra can only hurt, never buy a pass.

Implemented in `audio.py`. `audio_selftest.py` pairs each criterion with a mutant that
makes it go red — a silent clip, one beep re-encoded under five names, a manifest missing
an event, a missing file, music that is a 0.2 s click, a manifest that is not JSON, no
recipe at all — and with the **variants** a mutant cannot construct, which are the half
this criterion set needs: all declared events on one clip *plus* unique undeclared
extras, and a manifest covering a strict subset of the declared events. It also pins
`audio.GAME_EVENTS` against a hand-transcribed list and against the rendered prompts,
because a check that reads its expectation from the grader goes green on both halves of
one mistake.

**After changing an audio criterion, re-score the stored corpus.** Run:

```shell
python3 eval/judge/audio_regrade_census.py --runs-root <main checkout>/eval/runs
```

It re-applies these criteria offline to every stored grading, names the verdicts that
move, and refuses the records it cannot compare. Record in `eval/RUNS.md` the population
it checked, how many verdicts moved and which — including zero.


Only what is left after those is asked of a judge: does the music suit this game, are
the effects readable and distinguishable in play, is anything harsh or fatiguing.

**`audio.*` criteria do not apply to submissions built before audio entered the task
set.** Scoring the existing 24 against them would measure the task change, not the
submissions.

### The visual criteria are quarantined pending a harness fix

`look.feedback` and `look.legible` are **withdrawn from scoring** until `just film`
captures everything the player sees. Unity draws its HUD with `OnGUI`, which never
reaches `camera.Render()`; TypeScript draws it into a DOM node outside the offscreen
canvas. Both were failed for *not having* a scoreboard they demonstrably had.

That is a **template** defect as much as a rubric one: an agent that builds a correct
scoreboard, films it, and sees no scoreboard may delete working code to chase the ghost.
The task prompts now state that everything the player sees must appear in the frames.

### Validation gates — none of these judges is scored until all pass

1. **Ceiling test.** No judge may give effectively the same grade to everything. Run
   over stored submissions first; it is free.
2. **Independence.** Correlate the specialists. If `fun`, `ux` and `idiomatic` produce
   the same ranking, there are not five judges — there is one judge with five names.
   This is the gate most likely to fail and the reason the aspects were split at all.
3. **Order-invariance.** Reshuffle presentation order; a ranking that moves is an
   artifact. This replaces `instability`, which only measured within-artifact order
   sensitivity and read 0.000 on 22 of 24 — consistent and uninformative.
4. **Adjudication.** Spot-check firings against the underlying evidence. Consistency is
   not correctness: three stack-specific instrument defects in this project were each
   perfectly consistent, and each looked like a result.

## Scoring

```
tier1 = GATE: PASS iff every scored criterion passed  -- NOT WEIGHTED
        (9 criteria + 5 audio criteria where audio is in the task)
        an empty tier is `usable: false`, which is NOT a pass
tier2 = passed/total  (13-22 SCORED criteria, per game, + audio.triggered;
                       diagnostic-only criteria are reported but excluded)
tier3 = per-aspect rankings and grades   -- DIAGNOSTIC ONLY, weight 0.00

overall = 1.00*tier2      # tier 1 gates, tier 3 diagnoses, neither is in the sum

Every record carries `gate` (verdict + failing ids + blocking ids) and
`scoring_regime`. Records written before 2026-08-23 have neither: their `overall`
is 0.31*tier1 + 0.69*tier2 and is NOT comparable with a gate-regime score.

If a tier is unusable (empty pack) or skipped it is EXCLUDED and the remaining
weights are renormalised - never folded in as a zero.
```

Reported per criterion, per tier, per game, per stack. A total on its own is not a
result.

**Tier 3 stays at 0.00 until it passes its validation gates.** It was demoted on two
independent grounds — a bounded contribution that could not reorder anything, and an
aggregate that was noisiest exactly where it mattered — and a third has since been
added: across 24 submissions it carried **no information at all**, and what looked like
information was a harness artifact.

The redesigned tier is aimed squarely at what the deterministic tiers cannot see, so it
is the layer most likely to earn a weight. It has not earned one yet. Bring the project
owner discrimination, independence and stability numbers; do not bring an argument.

**Audio criteria apply only to submissions built from a task that asked for audio.**
Applying them retroactively would score the task change rather than the work.

## Controls that must pass before any run is believed

1. **Broken submission** — the game-agnostic starter itself, submitted unchanged. It
   builds, gates green, lints clean and renders a frame, and has no game in it. It must
   score near zero on tier 2 and low overall. If it does not, the evaluator is not
   measuring gameplay.
2. **Known-good submission** — for `g1_pong`, the fine-tuned Pong template, which is a
   complete, correct implementation of that task. It must score high. If it does not,
   the evaluator cannot pass a good game and is worthless.
3. **Adversarial submission** — a game that reports plausible state but does not
   simulate (constant values, ignored input, ignored seed). It must fail
   `determinism.seed` and the behavioural criteria, catching the "reports confidently,
   measures nothing" failure this project has hit twelve times.

An evaluator that cannot fail (1) or pass (2) is not evidence.

### The last end-to-end reading of those three, and what it is not

Measured 2026-08-14 with audio in the tiers. **These are stored `overall` values under the
weighted scheme `0.31*tier1 + 0.69*tier2`, which was retired on 2026-08-23 when tier 1 became a
gate** (#123, `eval/RUNS.md`, the fifth comparability break). They are kept because what they
establish is monotonicity, not a level, and no re-measurement has been made under the current
scheme:

| fixture | overall, pre-2026-08-23 scheme |
|---|---|
| `ref_pong` (correct reference game) | **0.956** — tier 2 14/14, all six audio criteria pass |
| `ref_pong_detuned` | 0.796 |
| `ref_adversarial_pong` (reports state, does not simulate) | 0.401 |
| `broken` (the starter, no game in it) | **0.089** |

Monotone across the full range: the evaluator can pass a good game and fail a broken one.
**There is no producer that reprints this table** — it was assembled by hand from four
evaluations. Under `overall = tier2` the four would compress toward tier 2's own range, and any
new reading must be taken under the current scheme rather than compared with these.

Alongside them, the module selftests — each exits non-zero on its own mutants:
`audio_selftest.py`, `sequential_selftest.py`, `bot_mutants.py`, `capability_selftest.py`,
`rusage_selftest.py`, `gate_selftest.py`, `tier1_census.py --selftest`, and
`tier2_census.py --selftest`.
