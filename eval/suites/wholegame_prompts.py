"""Whole-game task prompts, expressed in each stack's own vocabulary.

Companion to `prompts.py`, which holds the small spec-conformance tasks. These are
different in kind: greenfield "build a whole game of X" tasks, several hours of agent
work each, starting from the game-agnostic starter (`eval/starters/<stack>`).

THREE RULES THIS FILE EXISTS TO ENFORCE
---------------------------------------
1. Semantically identical across stacks, natively worded. The first bake-off used
   BYTE-identical prompts, which handed Rust a prompt written in Rust and cost a whole
   run (see prompts.py). Same behaviour, same acceptance criteria, same constraints,
   each written in the stack's own nouns.

2. NO TYPE WIDTHS. `u32` has no C# equivalent; the last time a prompt named one, an
   NUnit assertion failed with the baffling "Expected: 0, But was: 0". Say "a whole
   number count", never "a u32".

3. THE PROMPT IS NOT THE RUBRIC. It says what game to build and what "done" means
   functionally. It must NOT enumerate judging criteria, thresholds, weights, or
   anything about how the result will be scored. The rubric lives in `eval/judge/`,
   outside every trial's working directory. If you find yourself writing "make sure
   line clears work well" here because the rubric checks line clears, stop: that is
   teaching to the test and it invalidates the comparison.

WHAT IS LEGITIMATELY IN THE PROMPT
----------------------------------
The probe *contract* is. The held-out play-bot drives every stack through the same
JSON protocol, so it has to know the field names. Naming a field is functional spec
("the game must report its score"), not a rubric item ("the score must exceed 500").
Thresholds stay hidden; field names cannot.
"""

from __future__ import annotations

# --------------------------------------------------------------------------- #
# Stack vocabulary
# --------------------------------------------------------------------------- #
# Every entry is the SAME CONCEPT said in four languages. When adding a game,
# add its nouns here rather than inlining stack conditionals in the prose.

SIM_HOME = {
    "rust": "the `sim` crate",
    "ts": "the `src/sim` module",
    "unity": "the `Sim` assembly",
    "godot": "`sim/`",
}

VIEW_HOME = {
    "rust": "the `game` crate",
    "ts": "the `src/view` module",
    "unity": "the `View` assembly",
    "godot": "`view/`",
}

INPUT_TYPE = {
    "rust": "the input struct the starter already threads through the simulation",
    "ts": "the input interface the starter already threads through the simulation",
    "unity": "the input struct the starter already threads through the simulation",
    "godot": "the input class the starter already threads through the simulation",
}

STATE_HOME = {
    "rust": "the simulation world",
    "ts": "the simulation world object",
    "unity": "`SimState`",
    "godot": "the `World` class",
}

RENDER_NOTE = {
    "rust": (
        "The view layer is Bevy. Draw the game with sprites or meshes as suits it, "
        "and keep the one-way `sim -> view` data flow the starter sets up."
    ),
    "ts": (
        "The view layer is three.js. Draw the game with meshes and materials as suits "
        "it, and keep the one-way `sim -> view` data flow the starter sets up."
    ),
    "unity": (
        "The view layer is Unity. Draw the game with meshes and materials as suits it, "
        "and keep the one-way `Sim -> View` data flow the starter sets up."
    ),
    "godot": (
        "The view layer is a Node2D/Node3D tree. Draw the game as suits it, and keep "
        "the one-way `sim -> view` data flow the starter sets up."
    ),
}

AUDIO_NOTE = {
    "rust": (
        "Audio is Bevy's `AudioPlayer`. Put the asset files under `assets/audio/` and "
        "trigger playback from the view layer only — the simulation must not know that "
        "sound exists."
    ),
    "ts": (
        "Audio is the Web Audio API or an `<audio>` element, whichever suits. Put the "
        "asset files under `public/audio/` and trigger playback from the view module "
        "only — the simulation must not know that sound exists."
    ),
    "unity": (
        "Audio is `AudioSource`/`AudioClip`. Put the asset files under "
        "`Assets/Audio/` and trigger playback from the View assembly only — the Sim "
        "assembly must not know that sound exists."
    ),
    "godot": (
        "Audio is `AudioStreamPlayer`. Put the asset files under `audio/` and trigger "
        "playback from `view/` only — `sim/` must not know that sound exists."
    ),
}

# Sprite animation, for g4. The point of the game is machinery none of the other three
# tasks exercise - an animation state machine and a frame-indexed sprite - so each stack
# is told its own native way of drawing one, and nothing more.
SPRITE_NOTE = {
    "rust": (
        "Draw the character from a sprite sheet: a `Sprite` with a `TextureAtlas`, "
        "advancing the atlas index to animate. Generate the sheet as an asset in the "
        "repository rather than fetching one."
    ),
    "ts": (
        "Draw the character from a sprite sheet: one texture with the frames laid out "
        "in a grid, animated by moving the texture's UV offset. Generate the sheet as "
        "an asset in the repository rather than fetching one."
    ),
    "unity": (
        "Draw the character from a sprite sheet: a `SpriteRenderer` fed from a sliced "
        "multi-sprite texture, animated by swapping the sprite. Generate the sheet as "
        "an asset in the repository rather than fetching one."
    ),
    "godot": (
        "Draw the character from a sprite sheet: `AnimatedSprite2D`, or a `Sprite2D` "
        "with `hframes`/`vframes` and a moving `frame`. Generate the sheet as an asset "
        "in the repository rather than fetching one."
    ),
}

# 3D specifically: three of the four stacks default to 2D in the starter.
THREE_D_NOTE = {
    "rust": (
        "The starter's view is configured for 2D. Building in 3D means enabling Bevy's "
        "3D feature and using a 3D camera; building in 2D with an isometric or layered "
        "projection is also acceptable as long as the three spatial axes are real and "
        "independent in the simulation."
    ),
    "ts": (
        "The starter's view uses an orthographic 2D setup. Building in 3D means using a "
        "perspective or orthographic 3D camera; a 2D isometric or layered projection is "
        "also acceptable as long as the three spatial axes are real and independent in "
        "the simulation."
    ),
    "unity": (
        "The starter's view is configured for 2D. Building in 3D means using a 3D "
        "camera and meshes; a 2D isometric or layered projection is also acceptable as "
        "long as the three spatial axes are real and independent in the simulation."
    ),
    "godot": (
        "The starter's view is a 2D node tree. Building in 3D means switching to 3D "
        "nodes and a Camera3D; a 2D isometric or layered projection is also acceptable "
        "as long as the three spatial axes are real and independent in the simulation."
    ),
}


def _preamble(stack: str) -> str:
    return f"""You are building a complete, playable game in this repository.

The repository is a starter, not a game: it ships a verification harness, determinism
guards, a sim/view boundary, a rendering test harness and a probe protocol, plus a
placeholder entity that exists only so the tests have something to assert on. Replace
the placeholder with the game described below. Keep the harness.

Where things go:
- All game rules and state live in {SIM_HOME[stack]}. It stays free of rendering,
  wall-clock time and unseeded randomness — the existing guards enforce this and you
  should not weaken them.
- All drawing, device input and sound live in {VIEW_HOME[stack]}. {RENDER_NOTE[stack]}
  {AUDIO_NOTE[stack]}
- `AGENTS.md` describes the conventions this repository expects. Read it first.

You are building a game someone would want to play, not a demonstration that the
mechanics are implemented. A correct game that is dull, silent, unreadable or badly
paced has not met the bar. Spend real effort on how it feels to play: the pacing, the
difficulty, the responsiveness of the controls, and the way the game tells the player
what just happened.

Definition of done:
- `just verify` passes.
- `just run` opens a window and the game is actually playable with a keyboard.
- The game presents itself: a player who has never seen it can tell what to do, can
  see their progress while playing, and reaches a clear end state.
- The game has sound — looping background music, and a sound effect for each of the
  events listed below.
- The game is covered by tests you write, in the same three tiers the starter uses:
  simulation tests, replay/determinism tests, and rendering tests.
- The probe protocol below works, because that is how the game is driven without a
  human.
"""


_BOOLEAN_INPUTS = """Input objects have these fields, all booleans, all optional (absent means false), all
meaning "this control is held during this tick":"""

_ANALOG_INPUTS = """Input objects have these fields, all optional (absent means zero or false). The axis
fields are **continuous values from -1.0 to 1.0**, not switches — a magnitude of 0.4
means the control is pushed four tenths of the way, and the game must honour that
rather than rounding it to a direction. `fire` is a boolean meaning "held this tick":"""


def _probe_section(stack: str, inputs: str, state: str, events: str,
                   input_kind: str = _BOOLEAN_INPUTS) -> str:
    return f"""
### Driving the game without a human

The starter ships `just probe SEED` (a long-lived headless process: one JSON input
object per line on stdin, one JSON trace line per tick on stdout) and
`just probe-file SEED TICKS SCRIPT OUT`. Keep both working, and extend them so they
describe *this* game.

{input_kind}

{inputs}

A control that is held across consecutive ticks takes effect on **every** one of those
ticks. The player is never required to release and re-press it to act again. Where the
game defines a cooldown or a repeat rate, that is a rule of the game and is separate
from this.

Each trace line stays `{{"tick": ..., "hash": ..., "state": {{...}}, "events": [...]}}`.
For this game, `state` must be exactly this shape:

{state}

and `events` is a list of strings drawn from:

{events}

Field names and event names are a contract — spell them exactly as written. Everything
else about the game is yours to design.

`just film SEED TICKS SCRIPT OUTDIR` must keep producing frames of the running game.
**Everything the player sees on screen must appear in those frames**, including the
score, any HUD, menus and end-of-game screens. If your platform draws some of that
through a path the frame capture does not read, route it so that it does — a frame that
omits the scoreboard is not a frame of your game.

### Declaring your audio

`just audio-manifest` must print one JSON object describing the sound the game ships:

```json
{{
  "music": {{"file": "<path>", "loops": true}},
  "sfx": {{"<event_name>": {{"file": "<path>"}}}}
}}
```

`sfx` must have an entry for every event name listed above, and the files must exist
at the paths given. The same contract applies as to the trace: event names are spelled
exactly as written. Whether two events share a sound, and what the sounds are, is yours
to design.
"""


# --------------------------------------------------------------------------- #
# G1 - Pong
# --------------------------------------------------------------------------- #

_G1_INPUTS = """```
left_up      left_down       (the left player's paddle)
right_up     right_down      (the right player's paddle)
```"""

_G1_STATE = """```json
{
  "ball":      {"x": 0.0, "y": 0.0, "vx": 0.0, "vy": 0.0},
  "paddles":   [{"side": "left", "y": 0.0}, {"side": "right", "y": 0.0}],
  "score":     {"left": 0, "right": 0},
  "rally":     0,
  "game_over": false
}
```
`rally` is the number of consecutive paddle hits since the last point was scored.
`game_over` is true once a player has won and the match has stopped accepting play."""

_G1_EVENTS = """```
"paddle_hit"    a paddle deflected the ball
"wall_bounce"   the ball bounced off the top or bottom wall
"score_left"    the left player scored
"score_right"   the right player scored
"game_over"     a player reached eleven and won the match
```"""


def g1_pong(stack: str) -> str:
    return _preamble(stack) + f"""
## The game: Pong

Two paddles, one ball, a rectangular arena.

- A paddle sits near each end of the arena and moves only along the arena's short axis.
  It cannot leave the arena.
- The ball travels in a straight line and reflects off the top and bottom walls.
- When the ball meets a paddle it is deflected back the other way. Where it hits the
  paddle changes the angle it comes off at, so a player can aim.
- The ball speeds up as a rally goes on, up to a ceiling.
- When the ball passes behind a paddle, the other player scores a point and the ball is
  served again from the centre in a direction chosen from the seeded random source.
- First to eleven points wins; the game then stops accepting play until it is reset.
- The whole simulation is deterministic: the same seed and the same sequence of inputs
  reproduce the same run exactly, tick for tick.
{_probe_section(stack, _G1_INPUTS, _G1_STATE, _G1_EVENTS)}
"""


# --------------------------------------------------------------------------- #
# G2 - 3D Tetris
# --------------------------------------------------------------------------- #

_G2_INPUTS = """```
move_neg_x   move_pos_x      (slide the falling piece along one horizontal axis)
move_neg_z   move_pos_z      (slide it along the other horizontal axis)
rotate_x     rotate_y     rotate_z   (rotate a quarter turn about each axis)
soft_drop                    (fall faster this tick)
hard_drop                    (drop straight down and lock immediately)
```"""

_G2_STATE = """```json
{
  "well":   {"w": 5, "d": 5, "h": 12},
  "piece":  {"kind": "L", "cells": [[2, 11, 2], [2, 10, 2], [2, 9, 2], [3, 9, 2]]},
  "next":   "T",
  "settled":       0,
  "heights":       [[0, 0, 0, 0, 0], [0, 0, 0, 0, 0], [0, 0, 0, 0, 0],
                    [0, 0, 0, 0, 0], [0, 0, 0, 0, 0]],
  "score":         0,
  "layers_cleared": 0,
  "level":         1,
  "game_over":     false
}
```
- `well` is the playfield size in cells: `w` and `d` are the two horizontal axes, `h` is
  height. Use 5 x 5 x 12.
- `piece.cells` are the integer cell coordinates `[x, y, z]` currently occupied by the
  falling piece, with `y` counting upward from 0 at the floor. `piece` is `null` when no
  piece is falling.
- `piece.kind` and `next` are short names you choose for the piece shapes.
- `settled` is how many cells are occupied by locked pieces.
- `heights[x][z]` is the height of the settled stack in that column: 0 for empty, `h` for
  full to the ceiling.
- `layers_cleared` counts horizontal layers cleared over the whole game."""

_G2_EVENTS = """```
"spawn"         a new piece appeared at the top of the well
"move"          the falling piece moved horizontally this tick
"rotate"        the falling piece rotated this tick
"lock"          the falling piece came to rest and became part of the stack
"layer_clear"   a full horizontal layer was removed
"game_over"     a new piece could not be placed
```
Emit one `"layer_clear"` per layer removed, so clearing two at once emits it twice."""


def g2_tetris3d(stack: str) -> str:
    return _preamble(stack) + f"""
## The game: 3D Tetris

Tetris in a rectangular well with depth as well as width: pieces fall down a 5 x 5 x 12
shaft, and a *horizontal layer* clears when all 25 cells at that height are filled.

- A piece appears at the top of the well and falls one cell at a time on a fixed
  interval. The interval shortens as the level rises.
- The player can slide the piece along either horizontal axis, rotate it a quarter turn
  about any of the three axes, make it fall faster, or drop it straight to rest.
- A piece may never overlap a settled cell or leave the well. A move or rotation that
  would do either simply does not happen.
- When a piece cannot fall any further it locks in place and becomes part of the stack,
  and the next piece spawns.
- When every cell of a horizontal layer is filled, that layer is removed and everything
  above it falls down one.
- Pieces are polycubes of four cells. Choose the set yourself, but it must include at
  least one piece that is genuinely three-dimensional — not merely a flat shape sitting
  in a plane. Which piece comes next is drawn from the seeded random source.
- Scoring rewards clearing layers, and rewards clearing several at once more than
  clearing them one at a time. The level rises as more layers are cleared.
- The game ends when a newly spawned piece has nowhere to go.
- The whole simulation is deterministic: the same seed and the same sequence of inputs
  reproduce the same run exactly, tick for tick.

{THREE_D_NOTE[stack]}
{_probe_section(stack, _G2_INPUTS, _G2_STATE, _G2_EVENTS)}
"""


# --------------------------------------------------------------------------- #
# G3 - Twin-stick arena shooter
# --------------------------------------------------------------------------- #

_G3_INPUTS = """```
move_x   move_y   move_z    -1.0 .. 1.0   the movement vector this tick
aim_x    aim_y    aim_z     -1.0 .. 1.0   the direction the gun points this tick
fire                        boolean       fire while held
```
A movement vector of any magnitude and any direction is valid — the player is not
restricted to eight directions, and a half-pushed stick moves at half speed. Magnitudes
above 1.0 are clamped to 1.0. The aim fields describe a direction; only its orientation
matters, not its length."""

_G3_STATE = """```json
{
  "arena":  {"half_x": 400.0, "half_y": 250.0, "half_z": 400.0},
  "player": {"x": 0.0, "y": 0.0, "z": 0.0, "hp": 3, "alive": true},
  "enemies": [{"id": 1, "kind": "drifter", "x": 100.0, "y": 50.0, "z": -20.0, "hp": 1,
               "spawning": false}],
  "bullets": [{"id": 7, "x": 20.0, "y": 0.0, "z": 0.0,
               "vx": 500.0, "vy": 0.0, "vz": 0.0}],
  "wave":       1,
  "score":      0,
  "kills":      0,
  "multiplier": 1,
  "game_over":  false
}
```
`enemies` and `bullets` are sorted by `id` ascending. `id` is a whole number that is
never reused within a run. `kind` is one of the enemy kinds you define. `spawning` is
true while an enemy is materialising and cannot yet be hit or hurt the player."""

_G3_EVENTS = """```
"fire"         the player fired a shot this tick
"enemy_spawn"  an enemy began materialising
"enemy_hit"    a bullet connected with an enemy
"enemy_dead"   an enemy was destroyed
"player_hit"   the player took damage
"wall_graze"   something touched the arena boundary
"multiplier"   the score multiplier changed
"wave_start"   a new wave began
"game_over"    the player ran out of health
```"""


def g3_arena(stack: str) -> str:
    return _preamble(stack) + f"""
## The game: a 3D twin-stick arena shooter

One player inside a closed three-dimensional arena, waves of enemies converging from
every direction, and a gun that fires wherever the player is aiming — independently of
the direction they are moving. That independence is the point of the genre.

Think neon and spectacle: a game that is loud, fast and readable at a glance, where
destroying something is satisfying to watch. The reference point is the arcade
twin-stick lineage — Geometry Wars and its descendants.

**Rules**

- The arena is a bounded three-dimensional volume. The player moves through all three
  axes and cannot leave it.
- Aim is chosen separately from movement, in three dimensions, and the gun fires while
  the fire control is held. There is a minimum interval between shots.
- **Movement is analog and unrestricted in direction.** The player moves at any angle,
  and partial input produces proportionally slower movement. Eight-way movement is not
  acceptable.
- **The game must be playable with mouse and keyboard, and with a gamepad**, and
  `just run` must be actually playable with the mouse aiming. The mouse
  aims — it does not move the player. On a gamepad the sticks are analog in both
  movement and aim. Whichever device is in use, the simulation receives the same vectors
  described below.
- Bullets travel in a straight line at constant speed and disappear when they leave the
  arena or hit an enemy.
- **At least three kinds of enemy**, each visually distinct and each behaving
  differently — they must not merely differ in speed. Spawn positions come from the
  seeded random source.
- An enemy **materialises before it becomes dangerous**: for a short period after
  spawning it can neither be hit nor hurt the player, and this state is visible on
  screen. Enemies that simply appear are not acceptable.
- Touching the player costs health and destroys the enemy. There is a brief window
  after being hit during which the player cannot be hit again.
- A wave ends when every enemy in it is destroyed; the next begins, larger or faster.
- Destroying enemies raises the score, and a **multiplier** rises with sustained
  killing and falls when the player is hit.
- The player starts with three health. At zero the game is over and stops accepting
  play until reset.

**What the game must look like**

The visual result is part of the task, not decoration on top of it.

- Destroying an enemy produces a **burst that persists and dissipates over several
  frames** — not an object that vanishes on the tick it dies.
- Enemy materialisation, player damage, wave transitions and multiplier changes are each
  **visibly distinct on screen**. A player watching without sound should be able to tell
  which just happened.
- The arena boundary **reacts visibly** when something reaches it.
- The camera frames the action in three dimensions and conveys depth — the player should
  be able to judge where an enemy is along every axis.

These are effects, so they belong in the view layer. The simulation stays free of
rendering and emits the events the view animates from.

- Use no physics engine: collisions are spheres and boxes, and everything advances on the
  fixed simulation tick.
- The whole simulation is deterministic: the same seed and the same sequence of inputs
  reproduce the same run exactly, tick for tick.
{_probe_section(stack, _G3_INPUTS, _G3_STATE, _G3_EVENTS, _ANALOG_INPUTS)}
"""


# --------------------------------------------------------------------------- #
# G4 - 2D sprite platformer with attacks
# --------------------------------------------------------------------------- #
# DESIGN AND RATIONALE: eval/G4-PLATFORMER.md. Read it before changing this prompt -
# several fields exist so a criterion can ESTABLISH a condition rather than wait for
# one, which is the single defect behind sixteen false negatives in this project.

_G4_INPUTS = """```
move_left    move_right     (walk)
jump                        (leave the ground)
attack                      (swing the weapon)
```"""

_G4_STATE = """```json
{
  "level":  {"w": 2400.0, "h": 480.0, "goal_x": 2300.0},
  "player": {"x": 40.0, "y": 32.0, "vx": 0.0, "vy": 0.0,
             "hp": 4, "grounded": true, "facing": 1, "invuln": 0,
             "anim": "idle", "anim_frame": 0, "alive": true},
  "attack": {"active": false, "frame": 0,
             "hitbox": {"x": 0.0, "y": 0.0, "w": 0.0, "h": 0.0}},
  "platforms": [{"id": 1, "x": 320.0, "y": 8.0, "w": 640.0, "h": 16.0}],
  "enemies":   [{"id": 1, "x": 300.0, "y": 24.0, "hp": 2, "facing": -1}],
  "score":     0,
  "game_over": false,
  "victory":   false
}
```
- Positions are world coordinates with `y` counting upward. For every rectangle -
  platforms and the attack hitbox alike - `x` and `y` are its **centre** and `w`/`h`
  its full width and height, so a platform's top surface is at `y + h / 2`.
- `facing` is `1` when the character faces right and `-1` when it faces left.
- `invuln` is how many ticks remain during which the player cannot be hit; `0` means
  hittable now.
- `anim` is a short name you choose for what the character is currently doing, and
  `anim_frame` is the frame index within that animation.
- `attack.hitbox` is the rectangle that damages enemies **on this tick**. Its `w` and
  `h` are `0` while no attack is active.
- `platforms` and `enemies` are sorted by `id` ascending. `id` is a whole number that
  is never reused within a run.
- `game_over` is true once the player is out of health; `victory` is true once the
  player has reached the end of the stage. Either way the game stops accepting play
  until it is reset."""

_G4_EVENTS = """```
"jump"          the player left the ground
"land"          the player landed on a platform
"attack"        the player swung the weapon
"enemy_hit"     the swing connected with an enemy
"enemy_dead"    an enemy was destroyed
"player_hit"    the player took damage
"stage_clear"   the player reached the end of the stage
"game_over"     the player ran out of health
```"""


def g4_platformer(stack: str) -> str:
    return _preamble(stack) + f"""
## The game: a side-scrolling platformer with a weapon

One character, a stage built of platforms, enemies between here and the far end, and a
weapon that swings in front of the character. The feel of the jump and the weight of the
swing are the game.

- The character walks left and right, faces the way it last walked, and cannot leave
  the stage.
- Gravity pulls the character down. Walking off a ledge means falling; landing on a
  platform stops the fall. The character stands on the top surface of a platform and
  cannot pass up through one from below.
- Jumping is only possible from the ground. Holding the jump control does not jump
  again in mid-air — the character must land first.
- Attacking swings the weapon in front of the character, on the side it is facing. The
  swing has a beginning, a middle and an end: the weapon damages enemies during part of
  the swing, not for the whole of it, and not forever. Attacking again before the swing
  finishes does nothing.
- Enemies patrol the stage and hurt the character on contact. Hitting an enemy with the
  weapon damages it; enough damage destroys it and raises the score.
- Being hurt costs health, knocks the character back away from whatever hurt it, and
  leaves it briefly unable to be hurt again. At zero health the game is over.
- Reaching the far end of the stage clears it.
- Which enemies stand where, and where they are in their patrols, is drawn from the
  seeded random source.
- The character is animated from a sprite sheet, and the animation reflects what it is
  doing — standing, walking, in the air, swinging. {SPRITE_NOTE[stack]}
- Use no physics engine: gravity is a constant, collisions are rectangles, and
  everything advances on the fixed simulation tick.
- The whole simulation is deterministic: the same seed and the same sequence of inputs
  reproduce the same run exactly, tick for tick.
{_probe_section(stack, _G4_INPUTS, _G4_STATE, _G4_EVENTS)}
"""


TASKS = {
    "g1_pong": g1_pong,
    "g2_tetris3d": g2_tetris3d,
    "g3_arena": g3_arena,
    "g4_platformer": g4_platformer,
}

STACKS = ("rust", "ts", "unity", "godot")


if __name__ == "__main__":  # `python wholegame_prompts.py g2_tetris3d rust`
    import sys

    task = sys.argv[1] if len(sys.argv) > 1 else "g1_pong"
    stack = sys.argv[2] if len(sys.argv) > 2 else "rust"
    print(TASKS[task](stack))
