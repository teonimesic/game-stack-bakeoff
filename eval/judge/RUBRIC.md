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
| 1. Programmatic | Does it build, gate, lint, test, render? | **0.31** | scripts only |
| 2. Scripted play-bot | Does it *behave* like the game it claims to be? | **0.69** | deterministic driving via the probe protocol |
| 3. LLM judge | Is the code any good; is the result coherent? | **0.00 — DIAGNOSTIC** | a different model, binary criteria, blind |

The play-bot tier carries the most weight because it is the only tier that is both
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

## Tier 1 — Programmatic (9 criteria, script-answered)

Implemented in `static.py`. Never shown to the judge as a question.

| id | criterion |
|---|---|
| `build.compiles` | Does the project build / type-check cleanly? |
| `verify.green` | Does the repository's own gate, `just verify`, pass? |
| `lint.clean` | Does the linter pass with no findings? |
| `tests.exist` | Does the project ship more than a token number of its own tests? (floor: 8) |
| `tests.green` | Do all of the project's own tests pass, with none skipped? |
| `render.frames` | Does the game render frames at all? |
| `render.nonempty` | Do the frames contain something other than a blank background? (ink coverage 0.001–0.85, matching the floor the four render harnesses already use) |
| `render.animates` | Do consecutive frames of a played run differ? (>0.0005 of pixels) |
| `probe.responds` | Does the headless probe start and advance the simulation? |

Also collected, **reported but not scored** (they are diagnostics, not verdicts —
nobody in the open-source world hard-fails CI on wall-clock performance, and neither do
we): coverage percentages, code file and line counts by extension, the full output tail
of every command, and the nine **capture and performance fields** below.

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

## Tier 2 — Scripted play-bot (11–15 criteria per game)

Implemented in `bot_pong.py`, `bot_tetris3d.py`, `bot_arena.py`, driven through
`just probe SEED` — a live stdin/stdout session, so the bot can *read the game's state
and react*, not merely replay a tape. Every criterion asserts on state the game itself
reports.

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

**Twelve of the twenty-two are pinned by a mutant** (`bot_mutants.py`, 36 criteria
across four games, 2 variants, 3 session-lock controls, 0 expectations unmet): snapped
analog input, enemies that appear fully formed, one kind wearing three names, a multiplier
that never rises, one that survives damage, a boundary that is never reported, a dropped
depth axis, a volume that does not hold, a bullet every tick, a kill worth nothing, and
enemies that pass through the player. The unpinned ten are `state.shape`, `player.moves`,
`enemies.spawn`, `fire.spawns_bullets`, `aim.independent`, `bullets.kill`, `wave.advances`,
`gameover.triggers` and the two determinism criteria — the last two are pinned on
`ref_pong` over shared code.

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

**`platform.lands` was repaired after `wg-g4c`, for the same reason one level down.** It
walked off the opening ledge and asserted a landing, which requires a floor to be under
the ledge — level layout the bot has no knowledge of, and in a designed platformer that
is usually a pit. It failed **5 of 6** submissions on the first grading pass. It now
stages the fall by jumping from the platform underfoot, which is a fall onto a platform
in the criterion's own words and needs no level knowledge. Pinned by its existing mutant
*and* a new variant (*the opening ledge overlooks a bottomless pit*). It is now collateral
on the `jump.leaves_ground` mutant by construction, declared there, and its evidence
distinguishes the two failures. FINDINGS #65.

> ⚠️ **A ceiling on this task, not yet fixed: the bot cannot cross a gap.** It reaches
> every enemy by walking right, so a level whose ground has pits makes
> `attack.damages`, `score.on_kill`, `enemy.damages_player`, `invuln.window`,
> `knockback.applied` and `gameover.triggers` unmeasurable — the bot falls in and dies.
> `g4_platformer__ts__t0` scored the field's lowest on exactly this, having built the
> field's most sophisticated level. **A submission is currently penalised in proportion
> to how much real platforming it builds.** Do not read a low g4 combat score as a
> property of the submission without checking its ground for gaps.

Three are genre-defining and invisible in a still frame:

- `attack.active_frames` — the weapon damages during *part* of the swing. A permanently
  live hitbox renders identically.
- `attack.faces` — the hitbox is on the side `facing` reports, and flips when the
  character turns.
- `invuln.window` — hits are counted per tick *in contact*, so it measures the window
  rather than the size of the health pool.

**All 17 non-determinism criteria are pinned by a mutant** (`bot_mutants.py`: 36 across
four games, 0 expectations unmet). The suite earned its place immediately — `player.falls`
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
reference, all 36 mutants and the three lock controls were green while it raised `KeyError`
and scored a correct submission 0.000 (FINDINGS #46).

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

**These five exist.** The ids are the ones `aspects.py` defines and `field_sweep.py --aspects`
accepts; verified against the code 2026-08-15. Nothing else is runnable, whatever any
design table says.

| aspect id | judge asks | `sees` |
|---|---|---|
| `fun` | is this enjoyable, is it paced | `frames+telemetry` |
| `ux` | onboarding, presentation, can a newcomer tell what to do | `frames` |
| `audio` | does the music suit the game, are the effects readable | `audio` |
| `idiomatic` | was the stack used as that stack is meant to be used | `code` |
| `architecture` | could a second enemy type be added | `code` |

**Candidates, not built:** game feel, difficulty and tuning, visual coherence, code quality.
Do not name them in a command; `--aspects feel` is rejected by `choices=sorted(ASPECTS)`.

Two of the five read source and three read the played result, which is the intended rebalance
away from the retired rubric's 10-code-of-13. `idiomatic` is carried because it is the only
aspect whose subject is the variable under test — a four-stack comparison should ask whether the
agent used each stack *as that stack is meant to be used*.

Each judge returns a ranking of all 8 submissions in a game, per-submission grades with
reasons, and explicit best/worst calls. Ties are allowed but must be justified — a tie
is a finding, not an escape from deciding.

### Audio

Audio was a **total blind spot**: no task asked for it, no tier examined it, no
criterion mentioned it. The task prompts now require looping background music and a
distinct sound effect per declared event, plus a `just audio-manifest` contract.

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

Implemented in `audio.py`; mutation-tested in `audio_selftest.py`, which pairs every one
of the six criteria with a fixture that makes it go red — a silent clip, one beep
re-encoded under five names, a manifest missing an event, a missing file, music that is
a 0.2 s click, a manifest that is not JSON, and no recipe at all.

Two decisions inside `audio.distinct` are worth stating because they bound what it can
claim. It compares **decoded samples**, not filenames and not file hashes, so the
mutant that defeats every cheaper comparison — one beep re-encoded at five different
sample rates — is caught. And its floor is half the declared events rather than all of
them, because the task explicitly permits two events to share a sound; what must fail is
one clip reused everywhere.

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
tier1 = passed/total  (9 criteria + 5 audio criteria where audio is in the task)
tier2 = passed/total  (13-15 SCORED criteria, per game, + audio.triggered;
                       diagnostic-only criteria are reported but excluded)
tier3 = per-aspect rankings and grades   -- DIAGNOSTIC ONLY, weight 0.00

overall = 0.31*tier1 + 0.69*tier2        # tier3 contributes NOTHING

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

Alongside them, the module selftests — each exits non-zero on its own mutants:
`audio_selftest.py`, `sequential_selftest.py`, `bot_mutants.py`, `capability_selftest.py`,
`rusage_selftest.py`.
