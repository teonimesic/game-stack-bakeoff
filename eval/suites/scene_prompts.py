"""Scene task prompts, expressed in each stack's own vocabulary.

A **scene** is a timed audiovisual sequence with no player. `eval/SCENES.md` is the
authority on the design, the criteria and the research questions; this file renders the
prompts and nothing else. If the two disagree, that file wins and this one is the bug.

WHY THIS IS A SEPARATE MODULE FROM `wholegame_prompts.py`
---------------------------------------------------------
`_preamble()` there is shared by every game, so an edit aimed at one task reaches all of
them -- correctly where aimed, invisibly everywhere else. That is FINDINGS #41, and it
contaminated the one experiment whose whole design was a single variable. A scene needs
preamble text a game does not (no player, no keyboard, no sound, a fixed-length run), so
it gets `_scene_preamble()` in a file the game templates do not import. The vocabulary
dicts are imported FROM `wholegame_prompts` rather than copied: one concept, said in four
languages, in one place.

Scenes are graded, stored and reported separately from games. A scene score is never
pooled with a game score.

THE THREE RULES, WHICH ARE THE SAME THREE
------------------------------------------
1. Semantically identical across stacks, natively worded. Byte-identical prompts are not
   neutral; they end up written in one stack's vocabulary.

2. NO TYPE WIDTHS. Say "a whole number count", never "a u32".

3. THE PROMPT IS NOT THE RUBRIC. It says what to render and what "done" means. It must
   NOT name a criterion, a threshold or a tolerance. `eval/SCENES.md` lists what each
   criterion catches; none of that vocabulary may appear here, and
   `tools/prompt_guard.py --rubric` greps the rendered text rather than trusting a
   reading of it.

   The sharp cases in this file, because they look like omissions:

   - s2 never says the water surface stays level while the glass tilts. That is the
     criterion the scene exists for, and the wrong implementation -- water parented to
     the cup -- is what a hurried agent reaches for. Saying it converts the measurement
     into an instruction.
   - s1 never says the layers scroll at rates ordered by depth. It asks for a background
     with real depth and lets the telemetry contract carry the field names.

WHAT IS LEGITIMATELY HERE
-------------------------
The capture *contract*: telemetry field names, event names, the run length, and how the
seed is handled. A field name is functional spec ("report the water's volume"); a
threshold is not ("the volume must fall by a fifth").

AMBITION: ASK FOR THE RESULT, NEVER THE TECHNIQUE
-------------------------------------------------
Scenes are meant to push a stack as far as it goes. "Use ray tracing" prescribes the
implementation and destroys the measurement worth having -- which facility the agent
reached for, which is what the `framework_fluency` aspect reads. "The light the glass
throws onto the table moves as the glass tilts" asks for something hard to fake and
leaves the method open. The same holds for quantities: "many small irregular pieces,
each moving on its own", never a number. A number here is a threshold, and thresholds
are rubric.

PERFORMANCE IS A SECOND PASS AND IS NOT IN THESE PROMPTS
--------------------------------------------------------
The correctness pass is deterministic and tick-indexed precisely so that no wall-clock
enters it. Nothing here asks for a frame rate, and nothing here should.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from wholegame_prompts import (  # noqa: E402
    SIM_HOME,
    STACKS,
    THREE_D_NOTE,
    VIEW_HOME,
)

__all__ = ["SCENES", "STACKS", "s1_parallax", "s2_glass"]

# --------------------------------------------------------------------------- #
# Scene vocabulary
# --------------------------------------------------------------------------- #
# Same rule as the game vocabulary: every entry is the SAME CONCEPT said in four
# languages. Anything stack-specific goes in a dict here, never inline in a scene body,
# because a scene body naming an engine hands that stack its own words.

# What the view layer is, in scene terms. `wholegame_prompts.RENDER_NOTE` says the same
# thing about a *game* and is left alone deliberately: editing a dict shared by both task
# classes to suit one of them is #41 with a different subject.
SCENE_RENDER_NOTE = {
    "rust": (
        "The view layer is Bevy. Draw the scene with sprites, meshes and materials as "
        "suits it, and keep the one-way `sim -> view` data flow the starter sets up."
    ),
    "ts": (
        "The view layer is three.js. Draw the scene with meshes and materials as suits "
        "it, and keep the one-way `sim -> view` data flow the starter sets up."
    ),
    "unity": (
        "The view layer is Unity. Draw the scene with meshes and materials as suits it, "
        "and keep the one-way `Sim -> View` data flow the starter sets up."
    ),
    "godot": (
        "The view layer is a Node2D/Node3D tree. Draw the scene as suits it, and keep "
        "the one-way `sim -> view` data flow the starter sets up."
    ),
}

# Where the frame ends up. Scenes are graded from the captured frames, so which camera
# draws what is load-bearing in a way it is not for a game's HUD.
CAPTURE_NOTE = {
    "rust": (
        "Everything the scene shows must be drawn by the camera that renders into the "
        "capture's render target. Anything drawn by some other camera appears in the "
        "window and in no captured frame at all."
    ),
    "ts": (
        "Everything the scene shows must go through the renderer the capture harness "
        "drives. Anything layered over the canvas in the document instead appears in "
        "the browser and in no captured frame at all."
    ),
    "unity": (
        "Everything the scene shows must be drawn through the camera the capture "
        "reads. Anything drawn by a screen-space overlay canvas appears in the player "
        "and in no captured frame at all."
    ),
    "godot": (
        "Everything the scene shows must be drawn through the viewport the capture "
        "reads. Anything added outside that viewport's tree appears in the window and "
        "in no captured frame at all."
    ),
}

# The scene advances on the fixed tick, so an animation must be driven from the tick
# rather than from whatever the stack's per-frame delta happens to be.
TIME_NOTE = {
    "rust": (
        "Every moving thing is positioned from the current tick, not from a frame "
        "delta and not from the wall clock. `Instant` and `SystemTime` are already "
        "banned in the simulation; keep animation in the view derived from the tick "
        "the simulation reports."
    ),
    "ts": (
        "Every moving thing is positioned from the current tick, not from "
        "`requestAnimationFrame` deltas, `Date.now()` or `performance.now()`. Keep "
        "animation in the view derived from the tick the simulation reports."
    ),
    "unity": (
        "Every moving thing is positioned from the current tick, not from "
        "`Time.deltaTime`, `Time.time` or `DateTime.Now`. Keep animation in the View "
        "assembly derived from the tick the Sim assembly reports."
    ),
    "godot": (
        "Every moving thing is positioned from the current tick, not from `_process` "
        "deltas, `Time.get_ticks_msec()` or an `AnimationPlayer` running on wall-clock "
        "time. Keep animation in `view/` derived from the tick `sim/` reports."
    ),
}

# 2D specifically, for s1. Three of the four starters are already configured for 2D; the
# note says so in each stack's own nouns so that none of them reads as an instruction to
# change the starter.
TWO_D_NOTE = {
    "rust": (
        "The starter's view is configured for 2D with a 2D camera, which is what this "
        "scene wants. Sprites, meshes and shader materials are all available to it."
    ),
    "ts": (
        "The starter's view uses an orthographic 2D setup, which is what this scene "
        "wants. Textured planes, sprites and shader materials are all available to it."
    ),
    "unity": (
        "The starter's view is configured for 2D, which is what this scene wants. "
        "Sprite renderers, quads and materials are all available to it."
    ),
    "godot": (
        "The starter's view is a 2D node tree, which is what this scene wants. "
        "Sprites, `TextureRect`s, `Polygon2D`s and shader materials are all available "
        "to it."
    ),
}


def _scene_preamble(stack: str) -> str:
    """Shared by the scenes and by NOTHING ELSE.

    Deliberately not `wholegame_prompts._preamble`: the two task classes want different
    things said, and one shared preamble editing four game prompts by accident is a
    failure this project has already paid for (#41).
    """
    return f"""You are building a timed audiovisual scene in this repository.

The repository is a starter, not a scene: it ships a verification harness, determinism
guards, a sim/view boundary, a rendering test harness and a capture protocol, plus a
placeholder entity that exists only so the tests have something to assert on. Replace
the placeholder with the scene described below. Keep the harness.

**There is no player and there are no controls.** The scene is a fixed-length sequence
that plays the same way every time it is run from the same seed. It is watched, not
played.

Where things go:
- Everything that decides what the scene is doing at a given moment lives in
  {SIM_HOME[stack]}. It stays free of rendering, wall-clock time and unseeded
  randomness -- the existing guards enforce this and you should not weaken them.
- All drawing lives in {VIEW_HOME[stack]}. {SCENE_RENDER_NOTE[stack]}
- `AGENTS.md` describes the conventions this repository expects. Read it first.

**The scene has no sound.** Do not spend effort on audio; spend it on what is on screen.

You are building something worth watching, not a demonstration that the parts move. Push
the stack as far as it will go on this scene: the quality of the light, the materials,
the way things ease into and out of motion, the small details that sell the moment. How
you achieve any of that is entirely yours to choose -- reach for whatever the engine
gives you, or build it yourself if the engine gives you nothing.

Definition of done:
- `just verify` passes.
- `just run` opens a window and plays the scene through.
- The capture protocol below works, because that is how the scene is looked at without a
  human.
- The scene is covered by tests you write, in the same three tiers the starter uses:
  simulation tests, replay/determinism tests, and rendering tests.
"""


def _capture_section(stack: str, ticks: int, state: str, events: str) -> str:
    """The capture contract. Field and event names are spec; nothing here is a threshold.

    The starters already make a frame a pure function of `(seed, tick, inputs)`; a scene
    is that contract with `inputs` dropped, so no starter change is needed for any of it.
    """
    return f"""
### Watching the scene without a human

The scene is **{ticks} ticks long**. Tick 0 is its first moment and tick {ticks} its
last.

The starter ships `just probe SEED` (a long-lived headless process: one JSON input
object per line on stdin, one JSON trace line per tick on stdout) and
`just probe-file SEED TICKS SCRIPT OUT`. Keep both working, and extend them so they
describe *this* scene. **The scene ignores input entirely** -- the input objects are
still read, one per tick, and every one of them is empty. They exist only to advance the
clock.

Each trace line stays `{{"tick": ..., "hash": ..., "state": {{...}}, "events": [...]}}`.
For this scene, `state` must be exactly this shape:

{state}

and `events` is a list of strings drawn from:

{events}

Field names and event names are a contract -- spell them exactly as written. Everything
else about the scene is yours to design.

`just film SEED TICKS SCRIPT OUTDIR` must keep producing frames of the running scene. It
captures twelve frames evenly spaced over the run, both ends included, so the frames
already land on fixed tick numbers rather than on wall-clock instants; nothing needs
changing there beyond making the scene render. {CAPTURE_NOTE[stack]}

The whole scene is deterministic: the same seed reproduces the same run exactly, tick
for tick, and the captured frames for a given seed are identical from one run to the
next. {TIME_NOTE[stack]}

Whatever the scene above says the seed chooses, it must really choose it: two different
seeds produce two visibly different runs of the same scene, and the same seed always
produces the same one.
"""


# --------------------------------------------------------------------------- #
# S1 - a car on a road, 2D
# --------------------------------------------------------------------------- #
# DESIGN AND RATIONALE: eval/SCENES.md. Read it before changing this prompt. Several
# fields exist so that a check can ESTABLISH the condition it tests rather than wait to
# observe one, and several things this prompt does NOT say are omitted on purpose.

_S1_TICKS = 660

_S1_STATE = """```json
{
  "car":    {"x": 0.0, "y": 0.0, "speed": 0.0,
             "wheels": [{"id": 1, "x": 0.0, "y": 0.0, "radius": 0.0, "angle": 0.0}]},
  "layers": [{"id": 1, "depth": 0.0, "offset": 0.0, "span": 0.0,
              "top": 0.0, "bottom": 0.0}],
  "front":  [{"id": 1, "x": 0.0, "span": 0.0}],
  "light":  {"phase": 0.0, "sky": [0.0, 0.0, 0.0], "key": [0.0, 0.0, 0.0]}
}
```
- Positions are world coordinates with `y` counting upward, and the car travels along
  increasing `x`. `car.speed` is how fast it is travelling along that axis right now.
- `car.wheels` lists the wheels sorted by `id`, with `radius` the wheel's radius in the
  same world units and `angle` how far it has turned since the run began, in radians,
  increasing as the car rolls forward.
- `layers` lists the background layers sorted by `id`. `depth` is how far away the layer
  is, larger meaning further from the camera; `offset` is how far that layer has been
  displaced sideways so far, in world units; `span` is the width after which the layer
  repeats itself.
- `layers[].top` and `layers[].bottom` say where the layer is drawn in the captured
  frame, as fractions of the frame's height, with `0.0` the top edge and `1.0` the
  bottom edge.
- `front` lists the things drawn in front of the car, sorted by `id`, with `x` the world
  position of the middle of the thing and `span` its full width.
- `light.phase` is how far the scene has travelled from its opening light to its closing
  light: `0.0` before the change begins, `1.0` once it is complete. `light.sky` and
  `light.key` are the colours of the sky and of the main light right now, each as three
  numbers from `0.0` to `1.0`."""

_S1_EVENTS = """```
"wrap"          a background layer reached the end of its span and repeated
"front_enter"   something in front of the car began to cover it
"front_exit"    that thing stopped covering it
"light_begin"   the change of light started
"light_end"     the change of light finished
```"""


def s1_parallax(stack: str) -> str:
    return _scene_preamble(stack) + f"""
## The scene: a car on a road

A car drives from left to right along a road that never ends, seen from the side, while
the light changes from day to night around it.

- The car drives the whole length of the run. It never stops, never leaves the frame,
  and its wheels turn as it goes.
- Behind it lies a world with real distance in it: sky, whatever is far away, whatever
  is nearer, and the ground the car is on. As the car travels, that world should read as
  genuinely deep rather than as a picture sliding past. Each part of it is one of the
  `layers` the trace below describes, and declares how far away it is.
- The world behind the car is endless, and it is endless because it repeats. When a
  layer reaches the end of its span it begins again, and a viewer watching the horizon
  should never be able to tell you the moment that happened.
- Things pass between the camera and the car -- signs, poles, whatever suits the road
  you have built -- and while one is passing it covers part of the car.
- The light changes from day to night over a stretch of the run, and it changes
  gradually: the scene passes through every shade between the two rather than switching
  from one to the other. Everything lit changes with it -- the sky, the ground, the car,
  and what the car itself casts.
- The run ends at night, and what a car at night looks like is worth the effort:
  headlights that reach down the road, the road surface picking them up, whatever the
  car's own lights do to the world beside it.
- The wheels, the dust or spray they throw up, whatever hangs in the air, and every
  other moving detail belong to the scene. Many small things each moving on their own
  read as alive; a handful of large ones do not.
- Where the scenery stands, what passes in front of the car, and every other placement
  that could vary comes from the seeded random source.

{TWO_D_NOTE[stack]}
{_capture_section(stack, _S1_TICKS, _S1_STATE, _S1_EVENTS)}
"""


# --------------------------------------------------------------------------- #
# S2 - a glass of water that falls, breaks and un-breaks, 3D
# --------------------------------------------------------------------------- #
# DESIGN AND RATIONALE: eval/SCENES.md. What this prompt does not say about the water
# during the tilt is the whole reason the scene exists -- do not add it.

_S2_TICKS = 660

_S2_STATE = """```json
{
  "phase":  "draining",
  "glass":  {"x": 0.0, "y": 0.0, "z": 0.0, "intact": true,
             "up": [0.0, 1.0, 0.0],
             "screen": {"x": 0.0, "y": 0.0, "w": 0.0, "h": 0.0}},
  "water":  {"volume": 0.0, "up": [0.0, 1.0, 0.0], "height": 0.0},
  "drips":  {"count": 0, "volume": 0.0},
  "pieces": [{"id": 1, "x": 0.0, "y": 0.0, "z": 0.0,
              "up": [0.0, 1.0, 0.0], "settled": false}],
  "table":  {"y": 0.0}
}
```
- Positions are world coordinates with `y` counting upward, and `table.y` is the height
  of the surface everything stands on.
- `phase` is one of `"draining"`, `"tilting"`, `"falling"`, `"broken"`, `"rewinding"`,
  `"whole"`, and says which part of the sequence the scene is in at this tick.
- `glass.up` is the direction that is "up" for the glass itself -- the way an arrow
  drawn on its side, pointing at its rim, points in world space right now. It is three
  numbers.
- `glass.screen` says where the glass is in the captured frame: `x` and `y` are the
  middle of it and `w` and `h` its full size, all as fractions of the frame's width and
  height, with `0.0, 0.0` the top-left corner.
- `water.volume` is how much water is still inside the glass and `water.height` how deep
  it is. `water.up` is the direction perpendicular to the top surface of that water,
  pointing away from the water, as three numbers in world space.
- `drips.count` is how many drops have left the glass so far and `drips.volume` is the
  total amount that has left it. What leaves the glass and what stays in it are the same
  water.
- `pieces` lists the fragments of the broken glass sorted by `id`. `up` is that
  fragment's own copy of `glass.up` -- the direction the whole glass's arrow points once
  it has been carried into this fragment -- so it reports how the fragment is oriented
  now. `settled` is true once the fragment has stopped moving. The list is empty while
  the glass is whole.
- `glass.intact` is true while the glass is one object and false once it is not."""

_S2_EVENTS = """```
"drip"        a drop left the glass
"tilt"        the glass began to lean
"fall"        the glass left the table
"impact"      the glass reached the surface below
"break"       the glass came apart
"settle"      the last fragment stopped moving
"rewind"      the sequence began to run backwards
"whole"       the scene arrived back where it started
```"""


def s2_glass(stack: str) -> str:
    return _scene_preamble(stack) + f"""
## The scene: a glass of water

A transparent glass, most of the way full of water, stands on a table. It empties, it
tips, it falls, it breaks -- and then the whole thing runs backwards until it is
standing full again.

The sequence, in order:

- **It empties.** Water leaves the glass a drop at a time and the level inside goes
  down. This is the long, slow part of the run, and it is where the viewer gets a good
  look at the glass: what the light does passing through it, what it does to whatever is
  behind it, and what it throws onto the table around it.
- **It leans.** The glass tips further and further over, slowly enough to watch, and
  what it was throwing onto the table moves with it.
- **It falls.** It goes over the edge and drops, and this part is quick.
- **It breaks.** It comes apart into many small irregular pieces that fly, tumble and
  come to rest on the surface below. Each piece moves on its own and each is a different
  shape. The pieces are still glass: whatever the whole glass did to the light, its
  pieces do too.
- **It rests**, for a moment, so the viewer can see what it has become.
- **It runs backwards.** Every part of the sequence plays in reverse, in order, until
  the glass is standing whole and full on the table exactly as it began. This is a true
  reversal, not a fade and not a cut.

Other things the scene needs:

- Something with a pattern to it stands behind the glass, in view of the camera and
  large enough to be seen past the glass on both sides. What it looks like is yours to
  choose, as long as it has enough going on that a viewer could tell one part of it from
  another.
- The camera is placed so that the glass, the table it stands on, the surface it falls
  to and the thing behind it are all in frame for the whole run. It may move, and if it
  does it moves smoothly.
- The lighting is the scene's other subject. A single flat light on a transparent object
  wastes the scene; give it something worth passing through.
- How the glass breaks -- how many pieces, what shape each is, where each one goes --
  comes from the seeded random source, as does anything else that could vary.

{THREE_D_NOTE[stack]}
{_capture_section(stack, _S2_TICKS, _S2_STATE, _S2_EVENTS)}
"""


SCENES = {
    "s1_parallax": s1_parallax,
    "s2_glass": s2_glass,
}


if __name__ == "__main__":  # `python scene_prompts.py s2_glass rust`
    scene = sys.argv[1] if len(sys.argv) > 1 else "s1_parallax"
    stack = sys.argv[2] if len(sys.argv) > 2 else "rust"
    print(SCENES[scene](stack))
