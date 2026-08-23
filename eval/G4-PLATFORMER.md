# g4 — 2D sprite platformer with attacks (BUILT, for review before launch)

**Status: the grader is built and pinned. Nothing has been launched.**

| piece | state |
|---|---|
| prompt (`suites/wholegame_prompts.py`, `g4_platformer`) | renders for all four stacks; no criterion id leaks into it |
| reference fixture (`judge/fixtures/ref_platformer/`) | `just verify` **exit 0**, 19/19 of its own tests |
| play-bot (`judge/bot_platformer.py`) | **19/19 scored criteria pass** against the reference; `stage.completes` also passes as a diagnostic |
| mutants (`judge/bot_mutants.py`) | **36 criteria pinned in both directions across four games, plus 2 variants and 3 session-lock controls, 0 expectations unmet** — 16 of the mutants are g4's |
| registration | `judge/evaluate.py` `BOTS["g4_platformer"]`, `RUBRIC.md` tier-2 section |

**One mutant escaped on the first run, and that is the result worth reporting.**
`player.falls` accepted "`grounded` became false" as evidence of falling. Against the
zero-gravity mutant the character walks off the ledge and *hangs in the air*: not
grounded, not falling — and the criterion passed. It now asserts a loss of height, which
is the property in its own name. This is FINDINGS #34 reproducing exactly: a proxy passes
every control built from the same assumption as the proxy. It was caught by the mutant and
by nothing else — the reference, the fixture's own 19 tests and the bot's own run all went
green with the defect in place.

A second, quieter one: `knockback.applied` originally asked whether `vx` *decreased* when
the enemy was on the right. Deleting the impulse entirely leaves `vx` at 0, which is a
decrease — the mutant would have passed. It now asserts the sign, i.e. *away*.

And a third, found in the bot rather than the criteria: `anim.states` sampled the walking
label while the character was airborne after being knocked back, and read `jump` for both
"walk" and "air". It still passed, on three distinct labels out of four — **a criterion
that passes for the wrong reason**. It now waits until the character is grounded before
sampling, and reads four distinct labels.

**Original design notes follow.** Where they disagree with the table above, the table is
what was built. Estimated cost is in "Cost" below and it is the
first matrix that would run under the new standing configuration (`--max-turns 1000`, no budget
cap), so its cost is **unmeasured** and a calibration trial comes first (`PROTOCOL.md`).

## Why this game and not another

Pong, 3D Tetris and the arena shooter have tied on the deterministic tiers across three games,
four stacks and two cap regimes. Every deviation found so far has been a grader defect, not a
submission defect. A fourth game is only worth $250–300 if it stresses machinery the other three
do **not**, because "the same four templates solve another task they all find easy" is a result
we already have three times.

| system | pong | tetris3d | arena | **g4** |
|---|---|---|---|---|
| continuous 2D collision against static geometry | — | grid only | — | **yes** |
| gravity and airborne state | — | fall only | — | **yes** |
| animation state machine with frames | — | — | — | **yes** |
| attack with *active frames* (a hitbox that exists for part of an action) | — | — | — | **yes** |
| invulnerability window | — | — | brief, incidental | **yes, load-bearing** |
| knockback / impulse on the player | — | — | — | **yes** |
| facing as a distinct state from movement | — | — | aim, decoupled | **yes** |

The two that matter most are **active frames** and the **animation state machine**. Both are
things a game either has or does not, both are invisible to a screenshot, and both are what
separates a platformer that feels like Castlevania from one that feels like a sprite sliding
around. They are also the g4 analogue of `aim.independent`: genre-defining, and settleable only by
driving the game.

## Contract

### Inputs

```
move_left   move_right      (walk)
jump                        (leave the ground)
attack                      (swing the weapon)
```

Four controls, deliberately. The starter's probe contract already states that a held control acts
on every tick and that cooldowns are a rule of the game — that covers "holding jump must not
re-jump in mid-air" without the prompt hinting that anything checks it.

### State

```json
{
  "level":  {"w": 2400.0, "h": 480.0, "goal_x": 2300.0},
  "player": {"x": 40.0, "y": 32.0, "vx": 0.0, "vy": 0.0,
             "hp": 4, "grounded": true, "facing": 1, "invuln": 0,
             "anim": "idle", "anim_frame": 0, "alive": true},
  "attack": {"active": false, "frame": 0,
             "hitbox": {"x": 0.0, "y": 0.0, "w": 0.0, "h": 0.0}},
  "platforms": [{"id": 1, "x": 0.0, "y": 0.0, "w": 640.0, "h": 16.0}],
  "enemies":   [{"id": 1, "x": 300.0, "y": 16.0, "hp": 2, "facing": -1}],
  "score": 0,
  "game_over": false,
  "victory": false
}
```

- `facing` is `1` for right, `-1` for left.
- `invuln` is the number of ticks remaining during which the player cannot be hit; `0` means
  hittable.
- `anim` is a short name the game chooses for what the player is doing; `anim_frame` is the frame
  index within it.
- `attack.hitbox` is the rectangle that damages enemies **this tick**, in world coordinates.
  `w`/`h` of `0` when nothing is active.
- `platforms` and `enemies` are sorted by `id`; `id` is never reused within a run.

Three of those fields exist so criteria can be **experiments rather than observations**, and each
is justified below rather than being contract surface for its own sake:

| field | which criterion could not be an experiment without it |
|---|---|
| `platforms` | the bot cannot *walk to a ledge* without knowing where the ledge is; without it `player.falls` degenerates into "wait and hope", which is exactly the `ball.wall_bounce` defect (#29) |
| `attack.hitbox` | `attack.faces` compares the hitbox's side against `facing`. Inferring the hitbox from which enemies died makes the criterion depend on enemy placement — ambient state, the `enemies.chase` defect (#29) |
| `invuln` | separates "took one hit" from "took eight hits and had eight hit points". Without it the criterion measures the health pool, not the window |

`goal_x` is exposed so stage completion is *drivable*; see the diagnostic note below.

### Events

```
"jump"         the player left the ground
"land"         the player landed on a platform
"attack"       the player swung
"enemy_hit"    the swing connected with an enemy
"enemy_dead"   an enemy was destroyed
"player_hit"   the player took damage
"stage_clear"  the player reached the end of the stage
"game_over"    the player ran out of health
```

Eight events, so eight `sfx` entries in `just audio-manifest`. `audio.distinct`'s floor is half the
declared events, so the task's existing permission for two events to share a sound still holds and
one beep under eight names still fails.

`"jump"`/`"land"` and `"attack"`/`"enemy_hit"` are deliberately separate: they are the pairs a game
is most likely to conflate, and conflating them is audible as mush in play. That is a judgement the
`audio` judge can make and no script can.

## Criteria — each written as an experiment, each with the mutant that reddens it

17 scored + 1 diagnostic. The **Establishes** column is the part that matters: it is what the bot
*causes* before it measures. A criterion that waits for a condition is the single defect behind
sixteen false negatives in this project (#29, #34).

| # | id | Establishes | Asserts | Mutant that turns it red |
|---|---|---|---|---|
| 1 | `state.shape` | — | every contracted key present and well-typed at tick 0 | drop `attack` from the state |
| 2 | `player.walks` | holds `move_right` 30 ticks from a known x | x increased, and `facing` is 1 | ignore move inputs |
| 3 | `player.bounded` | holds `move_left` 300 ticks against the level's left edge | x never goes below 0 | remove the clamp |
| 4 | `player.falls` | **walks to the edge of the starting platform**, derived from `platforms`, and steps off | `grounded` goes false and y decreases | gravity = 0 |
| 5 | `platform.lands` | the fall in #4 | `grounded` returns true, y stops changing, `land` fires | remove the landing resolve (falls through) |
| 6 | `jump.leaves_ground` | presses `jump` while grounded | y rises above the standing y, `grounded` false, `jump` fires | ignore the jump input |
| 7 | `jump.grounded_only` | **holds `jump` continuously for 240 ticks** | the player lands at least once, i.e. vy does not stay positive; no second `jump` event while airborne | allow jump when `grounded` is false (infinite jump) |
| 8 | `attack.active_frames` | presses `attack` once and steps 120 ticks | `attack.active` is true for **≥1 and <the whole window**, then false | hitbox permanently active |
| 9 | `attack.faces` | attacks facing right; walks left to flip `facing`; attacks again | the hitbox centre is on the +x side of the player the first time and the −x side the second | hitbox offset always +x |
| 10 | `attack.damages` | **walks to the nearest enemy**, stops within its own attack reach, attacks | that enemy's hp drops or it disappears, and `enemy_hit` fires | attack does no damage |
| 11 | `enemy.damages_player` | walks into the nearest enemy **without attacking** | hp drops and `player_hit` fires | contact does no damage |
| 12 | `invuln.window` | stands in contact with an enemy for 120 ticks | hp drops **fewer times than ticks in contact**, and `invuln` counts down after a hit | remove the window (damage every tick) |
| 13 | `knockback.applied` | takes the hit in #11 from a known side | the player's vx or vy changes away from the enemy on the hit tick | zero the impulse |
| 14 | `anim.states` | drives idle, walk, airborne and attack in turn | `anim` takes **≥3 distinct values** across those four states | `anim` always `"idle"` |
| 15 | `anim.frames_advance` | holds `move_right` 60 ticks | `anim_frame` takes ≥2 distinct values and repeats (it cycles) | `anim_frame` constant |
| 16 | `score.on_kill` | the kill in #10 | score strictly increased at the `enemy_dead` tick | score never changes |
| 17 | `gameover.triggers` | stands in an enemy until hp reaches 0 | `game_over` true, `alive` false, and **inputs no longer change the state hash** | `game_over` never set |
| — | `stage.completes` | walks toward `goal_x`, jumps the gaps in the ground **holding the control while still rising**, stands off at swinging range and attacks what is in the way, up to 4000 ticks | reaches `goal_x`, `victory` true, `stage_clear` fires | — |
| 18 | `determinism.replay` | same seed, same tape | identical hash every tick | unseeded source |
| 19 | `determinism.seed` | two seeds | traces differ | seed ignored |

### `stage.completes` is DIAGNOSTIC, not scored — and that is a decision, not an oversight

This is the `layer.clears` situation exactly (`RUBRIC.md`). A criterion is only scored if a
*scripted* bot demonstrably achieves it against a correct reference. "Walk right and jump when
blocked" traverses the reference by construction, because I will write the reference. It says
nothing about whether it traverses eight unknown level layouts built by four different agents, and
**a criterion the instrument cannot satisfy on correct work manufactures a false negative for every
honest submission** — which, once averaged, is indistinguishable from a real failure.

So it is measured, reported under `diagnostics`, and excluded from the denominator. **To promote
it:** show it passing against at least three deliberately awkward reference levels (a pit, a
staircase, a ceiling gap), not by argument.

**That paragraph's prediction was tested on 2026-08-23 and it was right, at both ends** (task 83).
The reference is traversed by construction — `stage.completes` passes on `ref_platformer` under the
broken bot *and* the repaired one, so it never carried information about traversal. On the eight
real `wg-g4c` levels the same bot reached 14.3% to 29.0% of the goal and died every time. Repairing
it — held jumps, standing off to swing — took the fractions to 27.4% to 80.3%, and **none reached
the goal**: 8 of 8 now end having taken exactly `hp0` hits. `DECISIONS.md` and `judge/RUBRIC.md`
carry the numbers and what they decided.

### Two traps this design is deliberately shaped around

**Assert the property in its own name (#34).** `attack.active_frames` asserts on `attack.active`
itself, not on "an enemy died", and `player.falls` asserts on y decreasing, not on `vy` going
negative. The first repair of `ball.moves` measured velocity as a proxy for movement, passed every
control built from the same assumption, and failed the first submission that separated the two.

**A reference cannot exhibit behaviour the task did not ask for (#34).** The reference is written
*after* the prompt is frozen and must include the things the new task rewards and the old
references lacked: an opening title card before control is handed over, a stage-clear card, a
reset. Every criterion below is written to tolerate a delay before it can act — none of them
measures from tick 0 unconditionally.

## Telemetry the `fun` judge reads

(There is no `tuning` judge. The five that exist are `fun`, `ux`, `audio`, `idiomatic` and
`architecture` — `aspects.py` is the authority, not any design table.)

`telemetry.py` is game-agnostic over `events`, so g4 needs only its event names added to the
interval list: `attack`, `land`, `jump`, `enemy_dead`, `player_hit`. That yields, for free:
seconds between kills, seconds between hits taken, longest quiet stretch, and time to first event.

Two g4-specific figures are worth adding because they are the pacing signature of the genre and
nothing else in the project measures anything like them:

- **whiff ratio** — `attack` events with no `enemy_hit` within the active window / all `attack`
  events. A game where every swing connects is trivially easy; one where almost none do is
  unresponsive.
- **airborne fraction** — ticks with `grounded` false / total. Distinguishes a floaty jump from a
  weighty one, which is the single most-discussed variable in platformer game feel.

Both are computed from the same driven session the play-bot scored, so the tiers cannot disagree
about what happened.

## A pre-launch gate this document did not have, added 2026-08-16

**MEASURE THAT THE MACHINE CAN BUILD BEFORE SPENDING FOUR FIGURES ON IT.**

`wg-arena3d` lost its rust and TypeScript arms — half the matrix, and every deduction in it —
to a system daemon (`syspolicyd`) pegged at ~100% CPU, which gates `execve` of freshly created
binaries. Both rust agents shipped code they had never compiled. Both TypeScript agents shipped
tests they had never run. All four said so in their final reports and none of it reached a gate.
See FINDINGS #49.

**Rust and TypeScript link or install new binaries on every build; Unity and Godot run
pre-existing ones.** So this failure mode is invisible on two of the four arms and looks exactly
like a stack difference on the other two.

Before launching g4, per stack, and reading the exit code unpiped:

| check | must show |
|---|---|
| `syspolicyd` CPU time and elapsed (`ps -Ao pid,etime,time,comm=`) | not pegged; CPU time far below elapsed |
| load average | at the machine's normal idle |
| compile-and-run a trivial NEW binary in each stack's toolchain | **it execs**, in under a second |
| `just verify` in each of the four **starters** | exit 0 |

The last two are the ones that matter and neither existed. A starter that cannot pass its own
gate on this machine, right now, is a matrix that will produce numbers about the machine.

**And read the closing message when each trial lands, before grading anything.** Four agents
wrote a paragraph headed *"What I could not verify — and why"* naming the exact mechanism.
`python3 tools/disclosure.py --run-dir runs/<run>` reads it now, from `agent_result.json` →
`.result` whole rather than from the truncated `agent.final_text`; `wholegame.py report` prints
the same passages beside each score.

## Controls before any of this is believed

Same three the project requires of every task (`eval/AGENTS.md`), plus the mutants above,
**plus a variant**:

1. **Negative** — the game-agnostic starter, unchanged. Must score near zero on tier 2.
2. **Positive** — `ref_platformer`, a correct implementation. Must score high. Without it,
   "the grader can go green" is an assumption.
3. **Adversarial** — reports a plausible state and does not simulate: fixed `anim`, hitbox always
   active, enemies that never move. Must fail the behavioural criteria.
4. **A variant** — a *correct* platformer the reference does not resemble, where every criterion
   must still pass. g4 has none yet and should have one before launch: the obvious candidate is
   a stage that opens with a held title card or a scripted intro, since that is the behaviour
   that produced false negatives on the other three games (#34, #46). Mutants ask whether a
   criterion can fail; only a variant asks whether it can still pass, and **every false negative
   adjudicated in this project has been of the second kind.**

## Cost — REPRICED 2026-08-16 FROM MEASURED DATA, per trial and per (game, aspect)

**The extrapolation rule has now failed twice** — once at **1.84x** (pricing tetris judge
calls from pong ones) and once at **13x** (pricing an `audio` call from an `architecture`
one). So every figure below is a measurement of the thing being priced, and the headline is
a **range**, never a point (FINDINGS #42).

### Agent trials — from the 8 measured trials in the only comparable regime

`wg-arena3d`, no budget cap, `--max-turns 1000`. That is how g4 would run, so it is the only
poolable evidence.

| | |
|---|---|
| min | **$34.27** |
| median | **$45.56** |
| mean | $46.76 |
| max | **$72.83** |
| spread across 8 | **2.13x** |
| spread **within one cell** (rust) | **1.62x** |

> ⚠️ **CORRECTED 2026-08-17: the g4 matrix is EIGHT trials, not 24.** `wholegame.py plan
> --games g4_platformer --trials 2` prints `1 games x 4 stacks x 2 trials = 8 trials`. The
> "24-trial" figure was inherited from the three-GAME matrices and repeated here and in
> `README.md` without being read off the planner - a 3x overstatement of the commitment, in a
> document whose whole job is to price it. Read the number from `plan`, never from the last
> matrix.

**An 8-trial g4 matrix: $274 to $583, median-priced at $364.**

Report the range. The point estimate is not honest at this spread — the same process produced
$34.27 and $72.83 for the same task, and $44.86 and $72.83 for the same *cell*.

**Two caveats that push the true figure up rather than down:**

- these eight are the **arena**; g4 is a bigger task in the dimension that costs turns (a
  sprite sheet, an animation state machine, attack frames, collision);
- four of the eight were built while `syspolicyd` was pegged (#49), and two of those never
  compiled anything — work not done is spend not incurred.

### The judge layer — measured per (game, aspect), because it spans 11x

| aspect | reads | measured $/call |
|---|---|---|
| `architecture` | code | **$6.80** |
| `idiomatic` | code | **$6.54** |
| `fun` | frames + telemetry | $1.50 |
| `ux` | frames | $1.36 |
| `audio` | audio | **$0.60** |

One round of all five aspects on one game: **$16.82**. At `--max-runs 2`: **$33.63**. At
`--max-runs 6`: **$100.89**.

**But do not budget for it.** All five aspects failed their gates on `g2_tetris3d` — three
ceiling on one presentation order, `fun` and `idiomatic` fail adjudication, and
`architecture~ux` are redundant while sharing no evidence. Tier 3 is weight 0.00 and running
it on g4 buys nothing until the repairs in `eval/IMPROVEMENTS.md` iteration 6 are made.

### Total, if g4 were authorised today

**$274-$583 for the eight trials.**

## Superseded cost note, kept — REVISED UPWARD 2026-08-15.** The earlier estimate of $250-300 was built from capped figures
and is superseded. The first uncapped measurement of any task — `g3_arena__rust__t0`, no budget
cap, `--max-turns 1000` — came in at **$72.83 over 369 turns**, against $27.60 mean for the same
game at a $48 cap. Capped numbers are not a basis for projecting uncapped ones.

At the measured **$0.1974/turn**, `--max-turns 1000` bounds a trial near **$197**, not the $130
assumed when that limit was chosen.

**A 24-trial g4 matrix is of the order of $800-1,900, not $250-300.** The point estimate is
~$1,160 and it is not worth quoting on its own: three further trials of the same task under the
identical configuration came in at $44.86, $34.27 and $41.66, so the calibration's $72.83 was the
**outlier**, 1.8x the mean of the others, and **within a single cell rust cost $72.83 and $44.86 —
1.62x** (FINDINGS #42). A process with that spread cannot be calibrated by one trial. The platformer
is also a *bigger* task than the arena in the dimension that costs turns — a sprite sheet to
generate, an animation state machine, attack frames, collision — so it is at least as likely to
sit above the arena figure as below it.

**Calibrate g4 with one trial before committing anything**, and re-cost from that number. The
launch decision belongs to the project owner and the figure it should be made against does not
exist yet.

## What would make this game worth its cost even if it ties

State it now, before the result is in, so the answer is not written to fit the outcome:

- If the four stacks tie again, that is the **fourth** game and the strongest available statement
  of the null: *four well-built templates on Opus solve every whole-game task put to them, and no
  task shape yet devised separates them.* Four games across four systems is a much harder null to
  dismiss than three.
- If the specialist judges separate anything here, it is most likely `fun` — the only built aspect
  that reads telemetry, and a genre defined by feel is where pacing evidence has the most to bite
  on. Registered in advance rather than found afterwards. (There is no `feel` judge; the five that
  exist are `fun`, `ux`, `audio`, `idiomatic`, `architecture`.)
- If a criterion fires, **adjudicate before believing it.** Every criterion firing in this project
  so far has been a grader defect. The prior is strong and it is against us.
