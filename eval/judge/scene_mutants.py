#!/usr/bin/env python3
"""Mutation and variant tests for the scene probe. Run: `python3 judge/scene_mutants.py`.

THE POINT OF THIS FILE, and it is the same point as `bot_mutants.py` and
`audio_selftest.py`: a criterion validated only against good input is indistinguishable
from a criterion that cannot fail, and it reads as success in every report.

So every criterion in `scene_probe.py` is pinned in BOTH directions:

    the healthy reference fixture                  -> must PASS, and PASS SCORED
    the fixture with that behaviour removed        -> must FAIL, and FAIL SCORED
    a CORRECT fixture the reference does not resemble -> must still PASS

The third is not decoration. **A mutant asks whether a check can fail; only a variant
asks whether it can still pass on an input it mishandles**, and every false negative ever
adjudicated in this project has been of the second kind - sixteen in one sweep (#46).
A mutant removes the mechanism the criterion names; it cannot manufacture an input the
criterion gets wrong.

A mutant that comes back UNSCORED has escaped, not been caught: `scored=False` is the
honest verdict for "the instrument could not measure this", and the scene probe has two
ways to reach it (a lock conflict, and a precondition the captured material does not
contain). Both are reported as unmet expectations.

Mutants are made by copying a fixture to a temp directory and patching one file by exact
string replacement, so nothing here modifies a fixture in place and every patch asserts
its target appears exactly once - a mutation test that silently fails to mutate is worse
than none.

    python3 judge/scene_mutants.py                 # both scenes, both directions
    python3 judge/scene_mutants.py --only s2_glass
    python3 judge/scene_mutants.py --census        # what each criterion separated
    python3 judge/scene_mutants.py --census --runs-root <main checkout>/eval/runs
    python3 judge/scene_mutants.py --reliability-selftest
    python3 judge/scene_mutants.py --attribution-selftest

The last one is the exception to everything above, and it says why in `RELIABILITY_CASES`:
`ParallaxScene._reliable` asks two questions no single scene can put to it at once, so its
subjects are layer records written here rather than fixtures, and its mutants edit the
shipped `scene_probe.py` rather than a copied fixture.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import scene_probe  # noqa: E402

FIXTURES = HERE / "fixtures"
FIXTURE_FOR = {"s1_parallax": "ref_parallax", "s2_glass": "ref_glass"}


@dataclass(frozen=True)
class Patch:
    file: str
    old: str
    new: str


@dataclass(frozen=True)
class Mutant:
    criterion: str
    scene: str
    label: str
    patches: tuple[Patch, ...]
    #: other criteria this mutant is EXPECTED to disturb, so the report can separate
    #: "the mutant worked" from "the mutant broke the whole scene".
    collateral: tuple[str, ...] = ()
    notes: str = ""


@dataclass(frozen=True)
class Variant:
    scene: str
    label: str
    patches: tuple[Patch, ...]
    #: the criteria this variant exists to exercise; ALL criteria must still pass.
    exercises: tuple[str, ...]
    #: Criteria this variant legitimately makes UNMEASURABLE, with the reason in
    #: `notes`. This is the one field in the suite where a failure is allowed not to
    #: count, and AGENTS.md rule 7 says every such channel is one a real bug can widen -
    #: so a tolerance that never fires is reported as dead.
    tolerates: tuple[str, ...] = ()
    notes: str = ""


# --------------------------------------------------------------------------- #
# s1_parallax
# --------------------------------------------------------------------------- #

P_SHAPE = Patch("game.py",
                '            "light": {"phase": _r(ph),',
                '            "lighting": {"phase": _r(ph),  # MUTANT: the contracted '
                'key is misspelled')

P_FLAT = Patch("game.py",
               '    """How fast a layer at `depth` scrolls, as a fraction of the car\'s '
               'travel."""\n    return 1.0 / (1.0 + depth)',
               '    """How fast a layer at `depth` scrolls, as a fraction of the car\'s '
               'travel."""\n    return 0.5  # MUTANT: one flat background, scrolled as '
               'a unit')

#: The telemetry keeps four distinct offsets; the renderer draws every band with the
#: nearest one. This is the mutant no telemetry-side check can find, and it is why the
#: image half exists.
P_DRAWN_FLAT = Patch("film.py",
                     '        phase = (layer["offset"] * SCALE) % span',
                     '        phase = (st["layers"][-1]["offset"] * SCALE) % span'
                     '  # MUTANT: every band is drawn at the nearest layer\'s offset')

#: A HOLE IN THE TELEMETRY, and it is invisible to every frame. The sky layer stops being
#: reported for ticks 101-119 - a window holding no captured frame, so the picture is
#: untouched and the only thing removed is the contract's one record per tick. An unwrap
#: that bridged the hole would return a plausible smaller travel for that layer instead of
#: refusing, which is the fail-open direction `_walk` names.
P_LAYER_GAP = Patch("game.py",
                    "                       for lid, depth, span in LAYERS],",
                    "                       for lid, depth, span in LAYERS\n"
                    "                       if not (lid == 1 and 101 <= self.tick <= 119)"
                    "],  # MUTANT: the sky stops being reported")

#: The same layer, gone for good from tick 501 on. Distinct from the hole above and it
#: needs its own subject: a walk built from the prefix looks perfectly continuous, so only
#: counting a layer's rows against the trace's own length refuses it.
P_LAYER_TRUNCATED = Patch(
    "game.py",
    "                       for lid, depth, span in LAYERS],",
    "                       for lid, depth, span in LAYERS\n"
    "                       if not (lid == 1 and self.tick > 500)"
    "],  # MUTANT: the sky stops being reported for good")

#: `span` declared only at tick 0. `state.shape` reads tick 0, so the layer looks
#: contracted; without a `span` there is nothing to unwrap against, and accumulating the
#: raw difference is the modular residue `_walk` exists to avoid. Same 19-tick window as
#: the hole mutant, so the picture is untouched.
P_SPAN_DROPPED = Patch(
    "game.py",
    '                        "offset": _r(self.offsets[lid]), "span": span,',
    '                        "offset": _r(self.offsets[lid]),\n'
    '                        "span": (0.0 if (lid == 1 and 101 <= self.tick <= 119)\n'
    "                                 else span),  # MUTANT: the sky stops declaring one")

P_JUMPY_WRAP = Patch("film.py",
                     '        phase = (layer["offset"] * SCALE) % span',
                     '        _o = layer["offset"] * SCALE  # MUTANT: the loop jumps\n'
                     '        phase = (_o % span) - 26.0 * SCALE * int(_o // span)')

P_FREE_WHEELS = Patch("game.py",
                      "        self.wheel_angle += travel / WHEEL_RADIUS",
                      "        self.wheel_angle += BASE_SPEED * DT / WHEEL_RADIUS  "
                      "# MUTANT: spun at the mean rate, not by the ground")

P_NOTHING_IN_FRONT = Patch("game.py",
                           "            x += self.rng.between(140.0, 260.0)",
                           "            x += self.rng.between(2140.0, 2260.0)  # MUTANT:"
                           " nothing the car reaches, so nothing covers it")

P_LIGHT_CUT = Patch(
    "game.py",
    """        if self.tick <= LIGHT_BEGIN:
            return 0.0
        if self.tick >= LIGHT_END:
            return 1.0
        u = (self.tick - LIGHT_BEGIN) / float(LIGHT_END - LIGHT_BEGIN)
        # smoothstep: still strictly increasing, so the ramp is monotonic either way
        return u * u * (3.0 - 2.0 * u)""",
    """        return 0.0 if self.tick < LIGHT_END else 1.0  # MUTANT: an instant cut""")

#: The capture geometry changes half way through the run. Nothing in the trace notices,
#: and every image measure compares one rectangle of one frame against the same rectangle
#: of another - so without `SceneRun.one_geometry` the comparison would run to the shorter
#: of two lists and return a truncated answer instead of refusing. Exercises the
#: fail-CLOSED half of the docstring's table: broken capture is a fact about the
#: submission, so an image-only criterion goes red rather than unscored.
P_MIXED_SIZES = (
    Patch("film.py",
          "def main(argv: list) -> int:\n    if len(argv) < 4:",
          "def main(argv: list) -> int:\n    global WIDTH, HEIGHT  # MUTANT\n"
          "    if len(argv) < 4:"),
    Patch("film.py",
          """        if t in wanted:
            write_rgb(os.path.join(outdir, "frame_%04d.png" % index), WIDTH, HEIGHT,
                      render(sim))
            index += 1""",
          """        if t in wanted:
            write_rgb(os.path.join(outdir, "frame_%04d.png" % index), WIDTH, HEIGHT,
                      render(sim))
            index += 1
            if index == 6:  # MUTANT: the capture geometry changes mid-run
                WIDTH, HEIGHT = 520, 300"""),
)

P_SEED_IGNORED = Patch("game.py",
                       "        self.rng = Rng(self.seed ^ 0x5CE7E)",
                       "        self.rng = Rng(0x5CE7E)  # MUTANT: the seed is ignored")

P_WALLCLOCK = Patch("game.py", "import math\nimport struct",
                    "import math\nimport os\nimport struct\nimport time")
P_WALLCLOCK_SEED = Patch("game.py",
                         "        self.seed = int(seed) & _M64",
                         "        self.seed = (int(seed) ^ os.getpid()\n"
                         "                     ^ time.time_ns()) & _M64  # MUTANT")

# -- variants: correct scenes the reference does not resemble ---------------- #

V_CONSTANT_SPEED = Patch("game.py", "SPEED_WOBBLE = 0.18",
                         "SPEED_WOBBLE = 0.0  # VARIANT: a car that holds one speed")

#: The reference numbers its layers from the furthest to the nearest, so a criterion
#: that read `layers[0]` as "the sky" would agree with it by accident. Here the ids run
#: the other way and the scene is otherwise identical - still sorted by id, as the
#: contract requires.
V_REVERSED_IDS = (
    Patch("game.py",
          "LAYERS = ((1, 8.0, 120.0), (2, 4.0, 160.0), (3, 2.0, 220.0), "
          "(4, 1.0, 260.0))",
          "LAYERS = ((1, 1.0, 260.0), (2, 2.0, 220.0), (3, 4.0, 160.0), "
          "(4, 8.0, 120.0))  # VARIANT: id 1 is the NEAREST layer"),
    Patch("game.py",
          "BANDS = {1: (0.00, 0.30), 2: (0.30, 0.52), 3: (0.52, 0.66), "
          "4: (0.66, 1.00)}",
          "BANDS = {4: (0.00, 0.30), 3: (0.30, 0.52), 2: (0.52, 0.66), "
          "1: (0.66, 1.00)}"),
)

#: A 30-tick ramp is a hasty but legal reading of "it changes gradually" - every shade
#: is still passed through, tick by tick. What it removes is the IMAGE half: at most one
#: captured frame lands inside a ramp that short, so `light.monotonic` must fall back to
#: telemetry and still pass rather than failing a correct scene for being quick.
V_SHORT_RAMP = (Patch("game.py", "LIGHT_BEGIN = 240", "LIGHT_BEGIN = 590  # VARIANT"),
                Patch("game.py", "LIGHT_END = 540", "LIGHT_END = 620  # VARIANT"))

#: THE GEOMETRY VARIANT, and it is a measurement rather than a promise. Submissions
#: choose their own capture size - only one starter's `film` recipe passes an explicit
#: resolution - so a criterion that counted raw pixels would rank the resolution (#59).
#: `judge/static.py` states that rule for the game tiers and gates it by registry; here
#: the same claim is checked by filming the identical scene 1.5x larger and requiring
#: every verdict to be unchanged.
V_BIGGER_FRAMES = (Patch("film.py", "WIDTH = 640", "WIDTH = 960  # VARIANT"),
                   Patch("film.py", "HEIGHT = 360", "HEIGHT = 540  # VARIANT"))

#: THE VARIANT THAT WAS NOT HERE WHEN THE FIRST REAL SUBMISSION ARRIVED, and the reason
#: three criteria misread it (`tasks/162`). The reference lets `offset` accumulate
#: forever; `eval/SCENES.md` decides that reporting it inside `[0, span)` is equally
#: contracted, and that is what a renderer wants, so it is what the first submission
#: did. The picture is unchanged - `film.py` already draws `offset % span` - so every
#: verdict must be unchanged too.
#:
#: NO MUTANT COULD HAVE FOUND THIS. A mutant removes the mechanism a criterion names;
#: what was needed was an INPUT the criterion mishandles, and only a scene that wraps is
#: one (rule 15, #46's shape).
V_WRAPPED_OFFSET = Patch(
    "game.py",
    '                        "offset": _r(self.offsets[lid]), "span": span,',
    '                        "offset": _r(self.offsets[lid] % span), "span": span,'
    '  # VARIANT: reported inside its own span')

#: THE NEAR LAYER REPEATS TWICE BETWEEN TWO CAPTURED FRAMES, and the frames therefore
#: cannot say how fast it went. A tight repeat in the foreground - sleepers, kerbstones,
#: a picket fence - is an ordinary thing to draw, and the scene is correct: the telemetry
#: has that layer moving furthest of the four, and `layers.depth_ordered` reads it that
#: way. Only the image half is blind, and it is blind for a reason no agreement test can
#: reach: the band's picture at tick t and at tick t+60 is the SAME PICTURE.
#:
#: The constant speed is what makes it exact rather than approximate. At 120 units/s the
#: car covers 120 units between captures and the nearest layer 60; a span of 30 is
#: crossed exactly twice, so `best_shift` answers 0px on 11 of 11 pairs at confidence
#: 0.83-0.92 and those 11 zeroes agree with each other perfectly. Before `tasks/164` the
#: probe called the band readable, published `0px/frame` for the FASTEST layer in the
#: scene, and failed `layers.image_parallax` on a correct submission.
#:
#: NO MUTANT COULD HAVE FOUND THIS either - it needs an input, not a missing mechanism.
V_ALIASED_NEAR_LAYER = (
    Patch("game.py", "SPEED_WOBBLE = 0.18",
          "SPEED_WOBBLE = 0.0  # VARIANT: so the near layer's repeat is crossed an "
          "exact whole number of times between captures"),
    Patch("game.py",
          "LAYERS = ((1, 8.0, 120.0), (2, 4.0, 160.0), (3, 2.0, 220.0), "
          "(4, 1.0, 260.0))",
          "LAYERS = ((1, 8.0, 120.0), (2, 4.0, 160.0), (3, 2.0, 220.0), "
          "(4, 1.0, 30.0))  # VARIANT: the nearest layer repeats every 30 units, and "
          "moves 60 between captures"),
)

#: THE FAR LAYER IS DECLARED AT ITS FULL EXTENT, and the nearer ones are drawn inside
#: it. Sky from the top of the frame down to the horizon, hills inside that, trees
#: inside those: `layers[].top`/`bottom` say where a layer is DRAWN, and a background
#: layer really is drawn behind everything above the horizon. Nothing else moves - the
#: simulation, the scroll rates and the painter's order are the reference's, and
#: `film.py` still paints back to front, so the picture is a correct parallax scene.
#:
#: NO MUTANT COULD HAVE FOUND THIS: it needs an input, not a missing mechanism (rule 15,
#: #46's shape). Before `tasks/174` the probe read each band's whole declared extent, so
#: the sky's band held the hills and the trees as well; it published 25px/frame for a
#: band whose drawn shift is 13.5px - the rate of a layer two steps nearer - and FAILED
#: `layers.image_parallax` on this scene.
V_NESTED_BANDS = Patch(
    "game.py",
    "BANDS = {1: (0.00, 0.30), 2: (0.30, 0.52), 3: (0.52, 0.66), 4: (0.66, 1.00)}",
    "BANDS = {1: (0.00, 0.66), 2: (0.30, 0.66), 3: (0.52, 0.66), 4: (0.66, 1.00)}"
    "  # VARIANT: each layer declared at its full extent, the nearer ones inside it")


# --------------------------------------------------------------------------- #
# s2_glass
# --------------------------------------------------------------------------- #

G_SHAPE = Patch("game.py",
                '            "water": {"volume": _r(f["water"]), "up": [0.0, 1.0, 0.0],',
                '            "liquid": {"volume": _r(f["water"]), "up": [0.0, 1.0, 0.0],'
                '  # MUTANT: the contracted key is renamed')

#: THE ONE-LINE CHANGE THE WHOLE SCENE EXISTS TO CATCH. Parenting the water to the cup
#: is what a hurried agent reaches for first, and it is invisible to anything that does
#: not compare the water's own surface normal against world up.
G_WATER_PARENTED = Patch(
    "game.py",
    '            "water": {"volume": _r(f["water"]), "up": [0.0, 1.0, 0.0],',
    '            "water": {"volume": _r(f["water"]),\n'
    '                      "up": [_r(v) for v in _up_from_angle(f["angle"])],  # MUTANT:'
    ' the water is a child of the cup')

G_SCALED_MESH = Patch(
    "game.py",
    '            "drips": {"count": int(f["drained"] / DRIP_UNIT),\n'
    '                      "volume": _r(f["drained"])},',
    '            "drips": {"count": 0, "volume": 0.0},  # MUTANT: the water mesh is '
    'merely scaled down; nothing ever leaves')

G_ALPHA_ONLY = Patch(
    "film.py",
    """            bend = CURVE_PX * u * (1.0 - 0.35 * v * v)
            src = backdrop.get(int(px + bend), int(py + 5.0 * u * u))""",
    """            src = backdrop.get(px, py)  # MUTANT: alpha transparency, no """
    """refraction""")

#: Half the contracted captures. Every starter's `just film` writes 12 evenly spaced
#: frames, so with any other count no frame can be attached to a tick and every image
#: measure loses its clock. The image-only criterion goes red; the criteria with a
#: telemetry half fall back to it, which is the row above this one in the docstring's
#: table and the one a variant cannot reach.
G_HALF_THE_FRAMES = Patch("film.py", "MAX_FRAMES = 12",
                          "MAX_FRAMES = 6  # MUTANT: half the contracted captures")

G_FLAT_TINT = Patch(
    "film.py",
    """            bend = CURVE_PX * u * (1.0 - 0.35 * v * v)
            src = backdrop.get(int(px + bend), int(py + 5.0 * u * u))""",
    """            src = (150, 168, 172)  # MUTANT: a flat tint; nothing is seen """
    """through it""")

G_ONE_PIECE = (Patch("game.py", "PIECES_MIN = 9", "PIECES_MIN = 1  # MUTANT"),
               Patch("game.py", "PIECES_MAX = 16", "PIECES_MAX = 1  # MUTANT: a single "
                                                   "mesh swapped for a broken one"))

G_PIECES_SINK = Patch(
    "game.py",
    "        settled = s >= land\n",
    "        settled = s >= land\n"
    "        if settled:\n"
    "            y -= 40.0 * (s - land)  # MUTANT: settled pieces go on sinking through "
    "the floor\n")

#: THE FIRST VERSION OF THIS MUTANT DID NOT BITE, and that is worth keeping. It replaced
#: only the rewind window's index arithmetic and left `if tick >= WHOLE_AT: return 0`
#: standing, so the scene still snapped back to its opening state for the closing 20
#: ticks - and the criterion, which reads the LAST tick, correctly passed. A mutant must
#: remove the mechanism the criterion names, not a mechanism next to it.
G_NO_REVERSAL = Patch(
    "game.py",
    """        if tick >= WHOLE_AT:
            return 0
        span = WHOLE_AT - 1 - REWIND_AT
        u = (WHOLE_AT - 1 - tick) / float(span)
        return int(round(u * (FORWARD_END - 1)))""",
    """        return FORWARD_END - 1  # MUTANT: the rewind holds on the broken state""")

#: The backdrop stays seeded, so the hash chains and the frames still differ between
#: seeds - only the FRAGMENTS are canned. That is the point: *different seeds differ*
#: alone is satisfied by anything random, and this mutant satisfies it.
G_CANNED_FRACTURE = Patch(
    "game.py",
    """        self.piece_count = PIECES_MIN + rng.below(PIECES_MAX - PIECES_MIN + 1)
        self.piece_plan = []
        for i in range(self.piece_count):
            self.piece_plan.append({
                "id": i + 1,
                "vx": rng.between(-52.0, 52.0),
                "vy": rng.between(24.0, 78.0),
                "vz": rng.between(-18.0, 18.0),
                "spin": rng.between(-7.0, 7.0),
                "size": rng.between(0.18, 0.44),
                "tumble": rng.between(0.6, 1.6),
                "phase0": rng.between(0.0, 6.28318),
            })""",
    """        canned = Rng(0x91A55)  # MUTANT: a canned pre-fractured mesh
        self.piece_count = PIECES_MIN + canned.below(PIECES_MAX - PIECES_MIN + 1)
        self.piece_plan = []
        for i in range(self.piece_count):
            self.piece_plan.append({
                "id": i + 1,
                "vx": canned.between(-52.0, 52.0),
                "vy": canned.between(24.0, 78.0),
                "vz": canned.between(-18.0, 18.0),
                "spin": canned.between(-7.0, 7.0),
                "size": canned.between(0.18, 0.44),
                "tumble": canned.between(0.6, 1.6),
                "phase0": canned.between(0.0, 6.28318),
            })""")

# -- variants ---------------------------------------------------------------- #

#: The reference leans one way. Nothing in the criteria may depend on which - an angle
#: to world up is unsigned, and a check that compared a component instead of an angle
#: would pass the reference and fail this.
V_TIPS_THE_OTHER_WAY = Patch("game.py", "TILT_MAX = 1.05",
                             "TILT_MAX = -1.05  # VARIANT: it tips the other way")

#: `up` is "the direction the arrow points" and the contract never says it is unit
#: length. A check that read `up[1]` as a cosine would pass the reference and fail this.
V_UNNORMALISED_UP = Patch(
    "game.py",
    """def _up_from_angle(a: float) -> tuple:
    \"\"\"The direction the glass's own 'up' arrow points after leaning by `a` radians.\"\"\"
    return (math.sin(a), math.cos(a), 0.0)""",
    """def _up_from_angle(a: float) -> tuple:
    \"\"\"The direction the glass's own 'up' arrow points after leaning by `a` radians.\"\"\"
    return (3.0 * math.sin(a), 3.0 * math.cos(a), 0.0)  # VARIANT: not unit length""")

#: The glass empties COMPLETELY before it leans. Legal - the prompt says it empties -
#: and it drives the remaining volume to exactly zero, which is where a check that
#: divides by the current volume rather than the opening one comes apart.
V_EMPTIES_FULLY = Patch("game.py", "DRAINED_BY_TILT = 0.85",
                        "DRAINED_BY_TILT = 1.0  # VARIANT: it empties completely")

#: The same geometry variant for the glass. Its camera lives in `game.py` so that
#: `glass.screen` and the renderer cannot disagree, which means the view size, the scale
#: and the origin move together - the scene is pixel-for-pixel the same picture, 1.5x
#: larger, and every verdict must be unchanged.
V_BIGGER_VIEW = (Patch("game.py", "VIEW_W = 640", "VIEW_W = 960  # VARIANT"),
                 Patch("game.py", "VIEW_H = 400", "VIEW_H = 600  # VARIANT"),
                 Patch("game.py", "SCALE = 2.2", "SCALE = 3.3  # VARIANT"),
                 Patch("game.py", "ORIGIN_X = 300.0", "ORIGIN_X = 450.0  # VARIANT"),
                 Patch("game.py", "ORIGIN_Y = 210.0", "ORIGIN_Y = 315.0  # VARIANT"))


MUTANTS: list[Mutant] = [
    Mutant("state.shape", "s1_parallax", "the `light` block is renamed", (P_SHAPE,),
           collateral=("layers.depth_ordered", "layers.image_parallax",
                       "loop.seamless", "wheels.match_speed", "front.occludes",
                       "light.monotonic", "seed.pair"),
           notes="the shape gate fails closed and everything downstream reports why"),
    Mutant("layers.depth_ordered", "s1_parallax",
           "every layer scrolls at the same rate", (P_FLAT,),
           collateral=("layers.image_parallax",),
           notes="one flat background scrolled as a unit - the naive implementation "
                 "`eval/SCENES.md` names"),
    Mutant("layers.depth_ordered", "s1_parallax",
           "the sky stops being reported for 19 ticks", (P_LAYER_GAP,),
           notes="the other half of reading `offset` through an unwrap: the window holds "
                 "no captured frame, so nothing in the picture changes and only the "
                 "contract's one record per tick is gone. Bridging the hole would return "
                 "a smaller travel for that layer and pass"),
    Mutant("layers.depth_ordered", "s1_parallax",
           "the sky stops being reported for good after tick 500", (P_LAYER_TRUNCATED,),
           notes="a hole is visible as a resumption; this one never resumes, so a walk "
                 "built from the prefix is perfectly continuous and reads a travel off "
                 "it. Measured: no other criterion flips, so the band going unpainted "
                 "in the last 3 frames costs the image side nothing here"),
    Mutant("layers.depth_ordered", "s1_parallax",
           "the sky declares no span for 19 ticks", (P_SPAN_DROPPED,),
           notes="`state.shape` reads tick 0, where the span is still there. Without one "
                 "there is nothing to unwrap against, and accumulating the raw "
                 "difference is exactly the residue this criterion was scored on"),
    Mutant("layers.image_parallax", "s1_parallax",
           "the telemetry reports parallax the renderer does not draw", (P_DRAWN_FLAT,),
           notes="THE MUTANT NO TELEMETRY-SIDE CHECK CAN FIND. Every offset the "
                 "submission reports is still distinct and still ordered by depth; only "
                 "the pixels disagree"),
    Mutant("layers.image_parallax", "s1_parallax",
           "the capture geometry changes half way through the run", P_MIXED_SIZES,
           notes="the fail-CLOSED half of the module docstring's table: a broken capture "
                 "is a fact about the submission, so the image-only criterion goes red "
                 "rather than unscored. Without `SceneRun.one_geometry` the two frames "
                 "would be compared to the shorter of the two"),
    Mutant("loop.seamless", "s1_parallax",
           "the background jumps 26px every time it repeats", (P_JUMPY_WRAP,),
           collateral=("layers.image_parallax",),
           notes="the wrap ticks are unchanged in the telemetry, so only comparing the "
                 "drawn shift against the reported offset finds it"),
    Mutant("wheels.match_speed", "s1_parallax",
           "the wheels are spun at the mean rate", (P_FREE_WHEELS,),
           notes="chosen to be the MEAN rate on purpose: the arc-to-travel ratio still "
                 "sits at 1.0 across the run, so only splitting the run by the car's "
                 "own speed separates a rolling wheel from a spun one"),
    Mutant("front.occludes", "s1_parallax",
           "nothing the car reaches passes in front of it", (P_NOTHING_IN_FRONT,)),
    Mutant("light.monotonic", "s1_parallax",
           "the light cuts between two palettes", (P_LIGHT_CUT,),
           notes="an instant cut has no shade between the two and no frame between "
                 "them either, so both halves see it"),
    Mutant("seed.pair", "s1_parallax", "the seed argument is ignored",
           (P_SEED_IGNORED,),
           notes="satisfies *same seed matches* perfectly; only the other side of the "
                 "pair rejects it"),
    Mutant("seed.pair", "s1_parallax", "the scene is seeded from the wall clock",
           (P_WALLCLOCK, P_WALLCLOCK_SEED),
           notes="satisfies *different seeds differ* perfectly; only the other side of "
                 "the pair rejects it"),

    Mutant("state.shape", "s2_glass", "the `water` block is renamed", (G_SHAPE,),
           collateral=("water.level_under_tilt", "water.volume_conserved",
                       "glass.refracts", "shatter.pieces_rest", "reversal.inverts",
                       "seed.pair")),
    Mutant("water.level_under_tilt", "s2_glass",
           "the water is parented to the cup", (G_WATER_PARENTED,)),
    Mutant("water.volume_conserved", "s2_glass",
           "the water mesh is merely scaled down", (G_SCALED_MESH,)),
    Mutant("glass.refracts", "s2_glass",
           "alpha transparency with no refraction", (G_ALPHA_ONLY,),
           notes="the backdrop is still visible through the glass and still tinted; "
                 "what is missing is the displacement"),
    Mutant("glass.refracts", "s2_glass", "a flat tint, nothing seen through it",
           (G_FLAT_TINT,),
           notes="the other half of the same criterion: this one keeps no structure "
                 "at all, where the alpha mutant keeps all of it"),
    Mutant("glass.refracts", "s2_glass", "half the contracted captures",
           (G_HALF_THE_FRAMES,),
           notes="the image-only criterion goes red while `reversal.inverts` and "
                 "`seed.pair` fall back to their telemetry halves and stay green - one "
                 "broken recipe deducting once rather than once per criterion"),
    Mutant("shatter.pieces_rest", "s2_glass",
           "a single mesh swapped for a broken one", G_ONE_PIECE),
    Mutant("shatter.pieces_rest", "s2_glass",
           "settled fragments go on sinking through the floor", (G_PIECES_SINK,),
           notes="`settled` is reported true throughout, so only tracking each "
                 "fragment's height after it settles finds it"),
    Mutant("reversal.inverts", "s2_glass",
           "the rewind holds on the broken state", (G_NO_REVERSAL,),
           collateral=("seed.pair",),
           notes="`phase` still reaches `whole` and both events still fire"),
    Mutant("seed.pair", "s2_glass", "a canned pre-fractured mesh", (G_CANNED_FRACTURE,),
           notes="the backdrop stays seeded, so the hash chains and the frames still "
                 "differ between seeds. Only the fragments are canned, which is exactly "
                 "the implementation *different seeds differ* alone would accept"),
]


VARIANTS: list[Variant] = [
    Variant("s1_parallax", "the car holds one speed for the whole run",
            (V_CONSTANT_SPEED,), ("wheels.match_speed",),
            notes="a constant speed is a legal reading of `it never stops`, and it is "
                  "the input on which a wheel spun at a constant rate and a wheel "
                  "driven by the ground are the same thing. The criterion must ask the "
                  "rolling ratio and say it could not ask the rest"),
    Variant("s1_parallax", "the layers are numbered nearest-first",
            V_REVERSED_IDS, ("layers.depth_ordered", "layers.image_parallax",
                             "loop.seamless"),
            notes="the same scene with its ids the other way round. A criterion that "
                  "read layer order out of the id instead of out of the declared depth "
                  "would pass the reference and fail this"),
    Variant("s1_parallax", "the light ramps over 30 ticks instead of 300",
            V_SHORT_RAMP, ("light.monotonic",),
            notes="hasty but legal: every shade is still passed through. At most one "
                  "captured frame lands inside a ramp that short, so the image half "
                  "cannot be established and the criterion must fall back rather than "
                  "fail a correct scene for being quick"),
    Variant("s1_parallax", "`offset` is reported inside its own span",
            (V_WRAPPED_OFFSET,), ("layers.depth_ordered", "layers.image_parallax",
                                  "loop.seamless"),
            notes="the same scene, the same picture, `offset` wrapped into `[0, span)` "
                  "instead of accumulating. A criterion that subtracts two reported "
                  "offsets reads a modular residue rather than a scroll rate, which is "
                  "what the first real submission was scored on (`tasks/162`)"),
    Variant("s1_parallax", "the near layer repeats twice between captures",
            V_ALIASED_NEAR_LAYER, ("layers.image_parallax", "layers.depth_ordered"),
            notes="a correct scene whose nearest band the 12 contracted frames cannot "
                  "resolve: it crosses its own span exactly twice between two of them, "
                  "so every pair draws the same picture and reads 0px. The telemetry "
                  "half still has it moving furthest. `layers.image_parallax` must "
                  "decline to read that band rather than publish 0px/frame for the "
                  "fastest layer in the scene (`tasks/164`)"),
    Variant("s1_parallax", "the layers are declared at their full extent",
            (V_NESTED_BANDS,), ("layers.image_parallax", "loop.seamless"),
            tolerates=("layers.image_parallax",),
            notes="a correct parallax scene whose far bands contain the nearer ones, "
                  "which is what `top`/`bottom` mean when a sky is drawn behind "
                  "everything above the horizon. 2 of its 4 layers then have no row of "
                  "the frame that is theirs alone, so the criterion must decline rather "
                  "than read a nearer layer's motion off a far layer's band - which is "
                  "what it did before `tasks/174`, at 25px/frame against a true 13.5. "
                  "THE TOLERANCE IS WHY THIS PIN LIVES IN `--attribution-selftest` AS "
                  "WELL: it waives a FAIL here as readily as an unscored, so the repair "
                  "it exists for is pinned where a mutant can still turn a row red"),
    Variant("s1_parallax", "the same scene filmed 1.5x larger", V_BIGGER_FRAMES,
            ("layers.image_parallax", "loop.seamless", "light.monotonic"),
            notes="submissions choose their own capture geometry, so every image-side "
                  "measure has to be a density, a fraction or a ratio of two "
                  "measurements of the same frame (#59). This checks that claim rather "
                  "than restating it: the identical scene, 960x540 instead of 640x360, "
                  "every verdict unchanged"),
    Variant("s2_glass", "the glass tips the other way",
            (V_TIPS_THE_OTHER_WAY,), ("water.level_under_tilt",),
            notes="a check that compared a vector COMPONENT instead of an angle would "
                  "pass the reference and fail this"),
    Variant("s2_glass", "`up` is reported at three times unit length",
            (V_UNNORMALISED_UP,), ("water.level_under_tilt", "reversal.inverts"),
            notes="the contract says `up` is a direction and never says it is unit "
                  "length. A check that read `up[1]` as a cosine would pass the "
                  "reference and fail this"),
    Variant("s2_glass", "the glass empties completely before it leans",
            (V_EMPTIES_FULLY,), ("water.volume_conserved",),
            notes="drives the remaining volume to exactly zero, which is where a mass "
                  "balance that divides by the CURRENT volume rather than the opening "
                  "one comes apart"),
    Variant("s2_glass", "the same scene rendered 1.5x larger", V_BIGGER_VIEW,
            ("glass.refracts", "reversal.inverts"),
            notes="the geometry half of #59 for the glass: `glass.refracts` locates its "
                  "two rectangles from fractions and compares densities, so 960x600 "
                  "must return the same verdicts as 640x400"),
]


# --------------------------------------------------------------------------- #


@dataclass
class Verdicts:
    passed: dict[str, bool] = field(default_factory=dict)
    scored: dict[str, bool] = field(default_factory=dict)
    evidence: dict[str, str] = field(default_factory=dict)
    wall_s: float = 0.0


def copy_fixture(scene: str, dest: Path) -> Path:
    shutil.copytree(FIXTURES / FIXTURE_FOR[scene], dest,
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    return dest


def apply_patches(repo: Path, patches: tuple[Patch, ...], label: str) -> None:
    for p in patches:
        target = repo / p.file
        text = target.read_text()
        n = text.count(p.old)
        if n != 1:
            raise SystemExit(
                f"{label!r}: its target appears {n} times in {target}, expected exactly "
                f"1. The fixture has changed and this patch no longer bites; a mutation "
                f"test that silently fails to mutate is worse than none.\n"
                f"--- target ---\n{p.old}")
        target.write_text(text.replace(p.old, p.new))


def run_probe(repo: Path, scene: str) -> Verdicts:
    t0 = time.monotonic()
    out = scene_probe.drive(scene_probe.SCENES[scene](), repo)
    v = Verdicts(wall_s=round(time.monotonic() - t0, 1))
    for c in out["criteria"]:
        v.passed[c["id"]] = bool(c["passed"])
        v.scored[c["id"]] = bool(c["scored"])
        v.evidence[c["id"]] = c.get("evidence", "")
    return v


def _cell(passed: bool | None, scored: bool | None) -> str:
    if passed is None:
        return "absent"
    if not scored:
        return ("PASS" if passed else "FAIL") + "/unscored"
    return "PASS" if passed else "FAIL"


# --------------------------------------------------------------------------- #
# The census
# --------------------------------------------------------------------------- #


# --------------------------------------------------------------------------- #
# The stored corpus: every scene grading on disk, read or refused
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class StoredGrading:
    """One stored scene grading, read. `passed`/`scored` carry every criterion of
    the record's scene - the shape check below refuses anything less."""

    path: str
    scene: str
    passed: dict[str, bool]
    scored: dict[str, bool]
    total_passed: int
    total: int
    score: float


@dataclass(frozen=True)
class StoredRefusal:
    """A record that exists on disk and cannot be read exactly. Named, counted,
    and entered into no count: an assumed verdict is a verdict about a submission
    nobody measured (`audio_regrade_census.py`'s discipline, rule 7)."""

    path: str
    reason: str


def read_stored_grading(rec: Any, path: str) -> StoredGrading | StoredRefusal:
    """One parsed candidate record -> a grading, or a refusal naming its defect.

    The record carries exactly the shape `scene_probe.drive` writes - `tier`,
    `scene`, `criteria[]` with `id`/`passed`/`scored`, `unscored{}`, `score`,
    `usable` - and every field is cross-checked against the criteria list, so a
    corrupted or hand-edited record cannot enter the counts half-read. `bool` is a
    subclass of `int` in Python, so every numeric field refuses a bool explicitly,
    and `passed`/`scored` read as strict bools because `bool("false")` is True
    (rule 7). A scene the registry does not hold is refused rather than mapped: its
    criteria were defined against a registry this checkout may no longer agree with.
    """
    if not isinstance(rec, dict):
        return StoredRefusal(
            path, "NOT_AN_OBJECT - a grading must be a JSON object carrying tier, "
                  "scene and criteria")
    scene_name = rec.get("scene")
    if not isinstance(scene_name, str) or scene_name not in scene_probe.SCENES:
        return StoredRefusal(
            path, f"UNKNOWN_SCENE - {scene_name!r} is not a scene this instrument "
                  f"registers; no criteria registry can be chosen for it without "
                  f"guessing")
    want = [cid for cid, _q in scene_probe.SCENES[scene_name].criteria]
    crits = rec.get("criteria")
    if not isinstance(crits, list):
        return StoredRefusal(
            path, "NO_CRITERIA_LIST - the record carries no list of criteria, so "
                  "there is nothing to count")
    passed: dict[str, bool] = {}
    scored: dict[str, bool] = {}
    seen: set[str] = set()
    for c in crits:
        if not isinstance(c, dict):
            return StoredRefusal(
                path, "MALFORMED_CRITERION - a criteria entry is not an object")
        cid = c.get("id")
        if not isinstance(cid, str):
            return StoredRefusal(
                path, "MALFORMED_CRITERION - a criterion id is not a string")
        if cid in seen:
            return StoredRefusal(
                path, f"DUPLICATE_CRITERION - {cid!r} appears more than once; "
                      f"counting it twice would count the measurement twice")
        p, s = c.get("passed"), c.get("scored")
        if not isinstance(p, bool) or not isinstance(s, bool):
            return StoredRefusal(
                path, f"MALFORMED_CRITERION - {cid!r} carries passed={p!r} "
                      f"scored={s!r}; a verdict that is not a boolean would compare "
                      f"as a pass (bool(\"false\") is True)")
        if cid not in want:
            return StoredRefusal(
                path, f"UNDECLARED_CRITERION - {cid!r} is not one of "
                      f"{scene_name}'s criteria; the record was graded against a "
                      f"registry this checkout does not hold")
        seen.add(cid)
        passed[cid] = p
        scored[cid] = s
    if seen != set(want):
        missing = sorted(set(want) - seen)
        return StoredRefusal(
            path, f"INCOMPLETE_CRITERIA - the record carries no verdict for "
                  f"{missing}; the missing criteria would silently leave the counts")
    unscored = rec.get("unscored")
    if not isinstance(unscored, dict):
        return StoredRefusal(
            path, "UNSCORED_DISAGREEMENT - unscored is not an object of reasons")
    if set(unscored) != {cid for cid in want if not scored[cid]}:
        return StoredRefusal(
            path, "UNSCORED_DISAGREEMENT - unscored's keys are not exactly the "
                  "criteria the record scored False; the record disagrees with "
                  "itself about what it measured")
    total, n_passed = rec.get("total"), rec.get("passed")
    n_scored = sum(1 for cid in want if scored[cid])
    n_scored_passed = sum(1 for cid in want if scored[cid] and passed[cid])
    if (not isinstance(total, int) or isinstance(total, bool) or total < 0
            or not isinstance(n_passed, int) or isinstance(n_passed, bool)
            or n_passed < 0 or n_passed > total):
        return StoredRefusal(
            path, f"TOTALS_DISAGREEMENT - passed={n_passed!r} total={total!r} is "
                  f"not a pair of counts")
    if total != n_scored or n_passed != n_scored_passed:
        return StoredRefusal(
            path, f"TOTALS_DISAGREEMENT - the record says {n_passed}/{total} but "
                  f"its criteria list holds {n_scored_passed}/{n_scored} scored; "
                  f"the score and the verdicts disagree")
    usable = rec.get("usable")
    if not isinstance(usable, bool) or usable != (total > 0):
        return StoredRefusal(
            path, f"USABLE_DISAGREEMENT - usable={usable!r} against a record that "
                  f"scored {total} criteria; `usable` is bool(scored) by contract")
    score = rec.get("score")
    want_score = n_passed / total if total else 0.0
    if isinstance(score, bool) or not isinstance(score, (int, float)) \
            or score != want_score:
        return StoredRefusal(
            path, f"SCORE_DISAGREEMENT - score={score!r} against "
                  f"{n_passed}/{total}; the stored score is not its own record's "
                  f"division")
    return StoredGrading(path, scene_name, passed, scored, n_passed, total,
                         float(score))


def stored_scene_records(runs_root: Path
                         ) -> tuple[list[StoredGrading], list[StoredRefusal], int]:
    """Every stored scene grading under `runs_root`: read, or refused by name.

    Two nets over one walk, because unreadable and absent are different claims
    (rule 12):

    - every `playbot.json` - the one address `evaluate.py` writes a tier-2 grading
      to, scene or game alike - is a candidate whatever it holds, so an unparseable
      one or one naming a tier neither instrument writes is a REFUSAL, never a
      silent zero;
    - every other `*.json` whose CONTENT parses to `tier == "scene_probe"` is a
      candidate too, so a grading stored under another name is still found.

    The content match parses rather than spells out serialisations, and it can
    only under-count: a non-playbot json that fails to parse cannot name its tier,
    and stays out. A game-tier playbot.json is not a refusal - it is another task
    class's record, out of this population by construction - and is returned as
    the third value so a "nothing found" can say what the walk DID see.
    """
    gradings: list[StoredGrading] = []
    refusals: list[StoredRefusal] = []
    n_playbot = 0
    for path in sorted(runs_root.rglob("*.json")):
        is_slot = path.name == "playbot.json"
        try:
            rec = json.loads(path.read_text())
        except (OSError, ValueError) as exc:
            if is_slot:
                refusals.append(StoredRefusal(
                    str(path), f"UNREADABLE_JSON - the tier-2 slot holds an "
                               f"unreadable record: {exc}"))
            continue
        if not isinstance(rec, dict):
            if is_slot:
                refusals.append(StoredRefusal(
                    str(path), "NOT_AN_OBJECT - the tier-2 slot holds a JSON "
                               "array or scalar, not a record"))
            continue
        tier = rec.get("tier")
        if tier == "scene_probe":
            out = read_stored_grading(rec, str(path))
            if isinstance(out, StoredGrading):
                gradings.append(out)
            else:
                refusals.append(out)
        elif is_slot:
            if tier == "playbot":
                n_playbot += 1
            else:
                refusals.append(StoredRefusal(
                    str(path), f"UNCLAIMED_SLOT - the tier-2 record names tier "
                               f"{tier!r}, which is neither scene_probe nor "
                               f"playbot, so no reader owns it"))
    return gradings, refusals, n_playbot


def _census_stored(runs_root: Path | None) -> None:
    """The stored-corpus half of `--census`: per-criterion counts over every
    stored scene grading, every file named, refusals loud. Printed under its own
    banner so no reader can mistake it for the fixture tables above."""
    if runs_root is None:
        print("Stored scene gradings: NOT ASKED - pass --runs-root <main checkout>/"
              "eval/runs to look.")
        return
    if not runs_root.is_dir():
        print(f"Stored scene gradings: {runs_root} is not a directory")
        return
    gradings, refusals, n_playbot = stored_scene_records(runs_root)
    if not gradings and not refusals:
        if n_playbot:
            print(f"Stored scene gradings: NOT ASKED - 0 scene gradings on disk. "
                  f"{n_playbot} playbot.json record(s) under the root, all "
                  f"game-tier: no scene has been built or graded. This is not "
                  f"'separated nothing'; it is a question that has not been put.")
        else:
            print("Stored scene gradings: NOT ASKED - 0 scene gradings on disk, "
                  "and no tier-2 record at all. No scene has been built or "
                  "graded. This is not 'separated nothing'; it is a question "
                  "that has not been put.")
        return
    bar = "=" * 78
    print(f"\n{bar}")
    print(f"STORED SCENE GRADINGS - the corpus: {len(gradings)} record(s) under "
          f"{runs_root}, {len(refusals)} refused.")
    print("Every file is named; a refused record is named and enters no count "
          "below. This")
    print("population is work an agent produced; the tables above are fixtures "
          "written by")
    print("this repository, and neither population is the other.")
    print(bar)
    by_scene: dict[str, list[StoredGrading]] = {}
    for g in gradings:
        by_scene.setdefault(g.scene, []).append(g)
    for scene in sorted(by_scene):
        gs = by_scene[scene]
        cls = scene_probe.SCENES[scene]
        print(f"\n{scene}: {len(gs)} stored grading(s)")
        for g in gs:
            print(f"  {g.path}   {g.total_passed}/{g.total} scored "
                  f"(score {g.score:.3f})")
        w = max(len(cid) for cid, _ in cls.criteria)
        print(f"{'criterion':<{w}}  {'pass':>5} {'fail':>5} {'unsc':>5}  separated")
        print("-" * (w + 40))
        for cid, _ in cls.criteria:
            p = sum(1 for g in gs if g.scored[cid] and g.passed[cid])
            f = sum(1 for g in gs if g.scored[cid] and not g.passed[cid])
            u = sum(1 for g in gs if not g.scored[cid])
            if p and f:
                sep = "yes"
            elif u == len(gs):
                # The probe's scored=False means the experiment could not be set
                # up - a different claim from `measured, one value only`.
                sep = "NO - UNSCORED ON EVERY STORED GRADING"
            else:
                sep = "NO - AN OPEN QUESTION"
            print(f"{cid:<{w}}  {p:>5} {f:>5} {u:>5}  {sep}")
    if refusals:
        print("\nREFUSED - in the population, readable by nobody, in no count "
              "above:")
        for r in refusals:
            print(f"  {r.path}\n    {r.reason}")


def census(rows: list[tuple[str, str, str, dict[str, bool], dict[str, bool]]],
           runs_root: Path | None) -> int:
    """What each criterion separated, over each population that exists.

    **The tables here are FIXTURES, not submissions**, and they answer *can this
    criterion take both values on material this repository wrote, and on what* -
    never *does it separate real work*. Beside them, when `--runs-root` is passed,
    `_census_stored` reads every stored scene grading on disk and reports the same
    question over the corpus. The two populations are printed under different
    banners and are never pooled: a fixture is written by the same hand as the
    criterion, a grading is not.
    """
    by_scene: dict[str, list] = {}
    for scene, kind, label, passed, scored in rows:
        by_scene.setdefault(scene, []).append((kind, label, passed, scored))
    problems = 0
    for scene in sorted(by_scene):
        pop = by_scene[scene]
        cls = scene_probe.SCENES[scene]
        print(f"\n{scene}: {len(pop)} fixture-derived subjects "
              f"(1 reference, {sum(1 for k, *_ in pop if k == 'mutant')} mutants, "
              f"{sum(1 for k, *_ in pop if k == 'variant')} variants)")
        w = max(len(cid) for cid, _ in cls.criteria)
        print(f"{'criterion':<{w}}  {'pass':>5} {'fail':>5} {'unsc':>5}  separated")
        print("-" * (w + 40))
        for cid, _ in cls.criteria:
            p = sum(1 for _, _, ps, sc in pop if sc.get(cid) and ps.get(cid) is True)
            f = sum(1 for _, _, ps, sc in pop if sc.get(cid) and ps.get(cid) is False)
            u = sum(1 for _, _, _, sc in pop if sc.get(cid) is False)
            sep = "yes" if p and f else "NO - AN OPEN QUESTION"
            if not (p and f):
                problems += 1
            print(f"{cid:<{w}}  {p:>5} {f:>5} {u:>5}  {sep}")
    print("\nTHE POPULATION ABOVE IS FIXTURES, NOT SUBMISSIONS. It answers whether a "
          "criterion\nCAN take both values on material this repository wrote, which is "
          "not the same question\nas whether it separates work an agent produced.")
    _census_stored(runs_root)
    if problems:
        print(f"\n{problems} criterion/scene rows separated nothing in the fixture "
              f"population. Each is\nan open question about the CRITERION: it is either "
              f"pinned in only one direction or\nmeasuring something the fixtures cannot "
              f"vary (#92, #123).")
    return problems


# --------------------------------------------------------------------------- #
# The reliability filter, pinned offline
# --------------------------------------------------------------------------- #

#: WHY THIS IS NOT A VARIANT. `ParallaxScene._reliable` asks two separable questions of a
#: layer - is each pair a measurement at all, and do the measurements agree - and the two
#: answer differently on inputs no fixture can hold at once. The `near layer repeats twice
#: between captures` variant reaches the first and goes green through it whatever the
#: second does; a fixture that isolated the second would have to report offsets so large
#: that the estimator's whole search window fits inside a ratio-unit slack, which is a
#: property of the reported UNITS and not of any scene worth filming.
#:
#: So the layer records go in by hand, with the answer stated before anything runs, and
#: the mutants below are the shipped file with one line put back the way it was.
@dataclass(frozen=True)
class ReliabilityCase:
    label: str
    #: what `best_shift` answered, per consecutive frame pair, in whole pixels
    shifts: tuple[int, ...]
    #: what the submission reported the layer's offset changing by over the same ticks
    d_offset: float | tuple[float, ...]
    #: the repeat length it declared, or None for a layer that declared none
    span: float | None
    #: can the frames be read for this layer? STATED HERE, never computed
    readable: bool
    why: str
    #: which key of `ParallaxScene.UNRESOLVED_REASONS` the note must give, or None when
    #: the layer was not refused for resolvability at all. The VERDICT is not the whole
    #: answer: a note that says a layer moved half its span, about a layer that simply
    #: declared no span, is a false sentence in a durable record and no pass/fail check
    #: can see it. Whichever key is named, the others' text must be ABSENT.
    reason: str | None = None


RELIABILITY_CASES: list[ReliabilityCase] = [
    ReliabilityCase(
        "the reference fixture's second band, measured",
        (14, 16, 15, 12, 11, 12, 14, 16, 15, 13, 11),
        (14.47, 15.63, 14.60, 12.37, 11.05, 11.91, 14.12, 15.58, 14.91, 12.74, 11.13),
        120.0, True,
        "the real numbers `judge/fixtures/ref_parallax` produces. Every pair is within "
        "0.56px of what the band's own median ratio predicts, and the band moves at "
        "most 0.13 of its span between captures"),
    ReliabilityCase(
        "a band drawn wherever the search window allowed, reported at 600 units a pair",
        (-60, -30, 0, 20, 45, 60, -45, 15, 30, -15, 5),
        600.0, 10000.0, False,
        "the shape the first real submission's road band had, with the aliasing taken "
        "out so the SLACK is what decides. The drawn displacement is unrelated to the "
        "reported one, and a slack of 0.15 in RATIO units is 90px at 600 units a pair - "
        "wider than the +/-89px the estimator can answer with, so every measurement it "
        "is capable of returning agrees with every other"),
    ReliabilityCase(
        "a slow band whose only spread is whole-pixel rounding",
        (5, 6, 5, 6, 5, 6, 5, 6, 5, 6, 5), 5.0, 400.0, True,
        "a true 5.5px shift answered 5 on 6 pairs and 6 on 5. This is the direction a "
        "tighter floor fails in: the band is correct and the estimator is doing the "
        "best a whole-pixel answer can do"),
    ReliabilityCase(
        "a layer that reports no offset change at all",
        (0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0), 0.0, 400.0, False,
        "a layer whose reported offset never moves. It is UNREADABLE for the same "
        "reason an aliased one is - there is no reported rate to compare the drawn "
        "shift against - and it must say so. Before 2026-08-27 `_reliable` dropped "
        "these rows at the confidence filter, one line ABOVE the classifier, so "
        "`no_offset` was a declared key of UNRESOLVED_REASONS that no evidence string "
        "could ever contain and the layer was reported as `only 0 readable frame "
        "pairs` with no reason attached. Note the ratio is also undefined here, which "
        "is why the classifier has to run before `usable` rather than after",
        reason="no_offset"),
    ReliabilityCase(
        "a background reported as moving and drawn stationary",
        (0,) * 11, 8.0, 900.0, True,
        "READABLE on purpose, and the one thing `layers.image_parallax` exists to catch. "
        "A renderer that never draws the scroll it reports agrees with itself perfectly, "
        "and excluding it here would be a fail-open channel round the criterion (rule 7)"),
    ReliabilityCase(
        "the near layer of `the near layer repeats twice between captures`",
        (0,) * 11, 60.0, 30.0, False,
        "the variant's band, as records. It reads 0px on every pair and agrees with "
        "itself perfectly, exactly as the row above does - the reported offset is the "
        "only thing that separates a band the frames cannot resolve from a background "
        "that never moved", "aliased"),
    ReliabilityCase(
        "a layer that declares no repeat length",
        (14, 16, 15, 12, 11, 12, 14, 16, 15, 13, 11),
        (14.47, 15.63, 14.60, 12.37, 11.05, 11.91, 14.12, 15.58, 14.91, 12.74, 11.13),
        None, False,
        "nothing bounds the residue, so nothing establishes that the drawn displacement "
        "is the reported one. Fail closed: the pairs are as agreeable as the first "
        "row's and the frames still cannot say what they show", "no_span"),
    ReliabilityCase(
        "three frame pairs", (14, 16, 15), (14.47, 15.63, 14.60), 120.0, False,
        f"under MIN_PAIRS_PER_LAYER; a median over 3 numbers is not a repeatability "
        f"claim"),
]

#: Each is the shipped `scene_probe.py` with ONE line changed - the first 2 put back the
#: way they were before `tasks/164`, the third a wrong answer that moves no verdict at
#: all. A mutant that leaves every row of the table where it was has removed nothing the
#: table can see.
RELIABILITY_MUTANTS: dict[str, tuple[Patch, ...]] = {
    "the agreement slack is a floor in RATIO units again": (
        Patch("scene_probe.py",
              '                slack = max(abs(predicted) * self.K_TOLERANCE, '
              'self.K_PIXEL_FLOOR)\n'
              '                if abs(x["shift"] - predicted) <= slack:',
              '                slack = max(abs(med) * self.K_TOLERANCE, '
              'self.K_TOLERANCE)  # MUTANT\n'
              '                if abs(x["shift"] / x["d_offset"] - med) <= slack:'),),
    "a pair is usable whether or not its span resolves it": (
        Patch("scene_probe.py",
              "            usable = [x for x, w in zip(read, why, strict=True) "
              "if w is None]",
              "            usable = list(read)  # MUTANT"),),
    #: THE ONE THAT MOVES NO VERDICT. Every unresolvable pair reported as aliasing is
    #: what the note said until this suite started reading it, and it is a false sentence
    #: about a layer that merely declared no span - invisible to any pass/fail check.
    "every unresolvable pair is reported as aliasing": (
        Patch("scene_probe.py",
              '        if span is None or not math.isfinite(span) or span <= 0:\n'
              '            return "no_span"',
              '        if span is None or not math.isfinite(span) or span <= 0:\n'
              '            return "aliased"  # MUTANT'),),
}


# --------------------------------------------------------------------------- #
# Band attribution, pinned offline
# --------------------------------------------------------------------------- #

#: WHY THIS IS NOT A VARIANT EITHER, and it is a sharper reason than the one above.
#: `ParallaxScene._own_band` decides which rows of a frame a layer can be measured from,
#: and the geometries that break it are exactly the geometries where the criterion then
#: declines to be scored - so the variant that carries such a scene has to `tolerate`
#: `layers.image_parallax`, and a tolerated criterion can never go red. The pin would be
#: dead on arrival (rule 7).
#:
#: The function is pure - declared bands in, a window out - so the table goes in by hand
#: with the row counts written down before anything runs, at HEIGHT below.
ATTRIBUTION_HEIGHT = 360


@dataclass(frozen=True)
class AttributionCase:
    label: str
    #: every declared band, as `(id, top, bottom)`, in declaration order
    bands: tuple[tuple[Any, float, float], ...]
    #: the layer this row asks about
    lid: Any
    #: the window `_own_band` must return at `ATTRIBUTION_HEIGHT`, and how many whole
    #: pixel rows it holds. STATED HERE, never computed from the subject.
    window: tuple[float, float] | None
    rows: int
    #: can that layer be measured at all? Stated, and compared against the shipped
    #: `MIN_OWN_ROWS` rather than derived from it.
    readable: bool
    why: str


ATTRIBUTION_CASES: list[AttributionCase] = [
    AttributionCase(
        "the reference fixture's bands, which tile the frame",
        ((1, 0.00, 0.30), (2, 0.30, 0.52), (3, 0.52, 0.66), (4, 0.66, 1.00)),
        3, (0.52, 0.66), 50, True,
        "`judge/fixtures/ref_parallax` declares four disjoint bands, so every layer's "
        "own rows ARE its declared band and this repair must be a no-op on it"),
    AttributionCase(
        "a far band that contains every nearer one - the far layer",
        ((1, 0.00, 0.66), (2, 0.30, 0.66), (3, 0.52, 0.66), (4, 0.66, 1.00)),
        1, (0.00, 0.30), 108, True,
        "the shape of the first real submission, where the sky is declared from the top "
        "of the frame to the horizon and everything else is drawn inside that. The far "
        "layer keeps the strip above the nearest band that starts inside it"),
    AttributionCase(
        "a far band that contains every nearer one - a contained layer",
        ((1, 0.00, 0.66), (2, 0.30, 0.66), (3, 0.52, 0.66), (4, 0.66, 1.00)),
        2, None, 0, False,
        "every row layer 2 declares is also inside layer 1's, so nothing drawn there "
        "can be attributed to one rather than the other. It is refused, not guessed"),
    AttributionCase(
        "a staircase of overlapping bands",
        ((1, 0.00, 0.36), (2, 0.24, 0.62), (3, 0.50, 0.86), (4, 0.74, 1.00)),
        2, (0.36, 0.50), 51, True,
        "overlap on both sides is not containment: a layer whose neighbours only cut "
        "into its ends keeps the middle, and that middle is what it must be read from"),
    AttributionCase(
        "two layers declaring the same band",
        ((1, 0.00, 0.50), (2, 0.00, 0.50)), 1, None, 0, False,
        "the degenerate case of containment, and the one where guessing is most "
        "tempting: the bands are identical, so neither layer has a row of its own"),
    AttributionCase(
        "a band split in two by a nearer one",
        ((1, 0.00, 1.00), (2, 0.30, 0.40)), 1, (0.40, 1.00), 216, True,
        "a profile is one contiguous window, so the taller of the two halves is the "
        "answer - 216 rows below the cut against 108 above it"),
    AttributionCase(
        "a band left a sliver of its own",
        ((1, 0.000, 0.460), (2, 0.008, 0.460)), 1, (0.000, 0.008), 2, False,
        "the first real submission's sky, to the digit. 2 rows is a window, and it is "
        "not one `band_profile`'s ten-row average was ever calibrated on - measured on "
        "that submission it answered -85px for a band whose drawn shift is 6px, at "
        "confidences 0.07 to 0.27 (`tasks/174`)"),
    AttributionCase(
        "a band that runs off the top of the frame",
        ((1, -1.000, 0.010), (2, 0.500, 1.000)), 1, (0.000, 0.010), 3, False,
        "`top`/`bottom` are fractions of the frame's height and nothing stops a "
        "submission reporting one outside it. Counted raw this band holds 363 rows of a "
        "360-row frame and clears the floor; `band_profile` clamps to the image and "
        "would profile the 3 rows that exist"),
    AttributionCase(
        "a band declared entirely off the frame",
        ((1, 1.200, 1.500), (2, 0.000, 1.000)), 1, None, 0, False,
        "clipped it collapses to a single edge, which is no band at all. Counted raw it "
        "is 108 rows that overlap nothing, so it would read as the most attributable "
        "layer in the scene"),
]

#: The shipped `scene_probe.py` with ONE line changed. Each removes a different half of
#: the attribution: that other bands are subtracted at all, that the tallest surviving
#: run is the one read, and that a window too thin for a profile is refused.
ATTRIBUTION_MUTANTS: dict[str, tuple[Patch, ...]] = {
    "no other band is subtracted, so a layer keeps its whole declared band": (
        Patch("scene_probe.py",
              "        for other, ot, ob in bands:\n"
              "            if other == lid:\n"
              "                continue",
              "        for other, ot, ob in bands:\n"
              "            if True:  # MUTANT: nothing is subtracted\n"
              "                continue"),),
    "the first surviving run is read rather than the tallest": (
        Patch("scene_probe.py",
              "        best = max(segs, key=pixel_rows)",
              "        best = segs[0]  # MUTANT"),),
    "a window of any height at all is enough to measure from": (
        Patch("scene_probe.py",
              "    MIN_OWN_ROWS = PROFILE_ROWS",
              "    MIN_OWN_ROWS = 0  # MUTANT"),),
    "a band is counted where it was declared rather than where the frame is": (
        Patch("scene_probe.py",
              "            top, bottom = max(0.0, min(1.0, top)), "
              "max(0.0, min(1.0, bottom))",
              "            top, bottom = float(top), float(bottom)  # MUTANT: not "
              "clipped to the frame"),),
}


def _attribution_verdicts(mod) -> dict[str, tuple]:
    """Per case: the window, its row count, and whether the layer can be measured.

    THE TABLE GOES IN AS LAYER RECORDS AND THROUGH `_bands`, not straight into
    `_own_band`. `_bands` is where a band running off the frame is clipped, and
    `band_profile` clamps to the image whatever it is handed - so a table that skipped
    it would count rows the profile can never sample and the bypass would be invisible.
    """
    scene = mod.ParallaxScene
    out = {}
    for case in ATTRIBUTION_CASES:
        try:
            bands = scene._bands([{"id": i, "top": t, "bottom": b}
                                  for i, t, b in case.bands])
            window, rows = scene._own_band(bands, case.lid, ATTRIBUTION_HEIGHT)
        except Exception as e:  # noqa: BLE001 - the verdict IS "it raised"
            out[case.label] = (f"RAISED {type(e).__name__}: {e}", -1, False)
            continue
        out[case.label] = (window, rows, rows >= scene.MIN_OWN_ROWS)
    return out


def attribution_selftest() -> int:
    """Which rows of a frame can be attributed to one layer, and can the answer be `none`?

    Reads no fixture and needs no toolchain.
    """
    print("band attribution - `the rows no other declared band contains`\n")
    shipped = _attribution_verdicts(scene_probe)
    problems = []
    w = max(len(c.label) for c in ATTRIBUTION_CASES)
    for case in ATTRIBUTION_CASES:
        window, rows, readable = shipped[case.label]
        ok = (window == case.window and rows == case.rows
              and readable == case.readable)
        print(f"  {case.label:<{w}}  stated {str(case.window):<14} {case.rows:>4}rows "
              f"{'readable' if case.readable else 'refused ':<8}  "
              f"got {str(window):<14} {rows:>4}rows "
              f"{'readable' if readable else 'refused ':<8}  "
              f"{'ok' if ok else '<-- UNMET'}")
        if not ok:
            problems.append(
                f"{case.label}: stated {case.window} / {case.rows} rows / "
                f"{'readable' if case.readable else 'refused'}, got {window} / {rows} "
                f"rows / {'readable' if readable else 'refused'} -- {case.why}")

    print("\nmutants - the shipped file with one line changed:")
    for label, patches in ATTRIBUTION_MUTANTS.items():
        got = _attribution_verdicts(_probe_with(patches, label))
        moved = sorted(c.label for c in ATTRIBUTION_CASES
                       if got[c.label] != shipped[c.label])
        print(f"  {label}\n    moves {moved or 'NOTHING'}")
        if not moved:
            problems.append(f"mutant {label!r} SURVIVED: every row of the table sits "
                            f"where the shipped file leaves it, so the table does not "
                            f"pin the line this mutant removed")

    print(f"\n{len(ATTRIBUTION_CASES)} band tables, "
          f"{len(ATTRIBUTION_MUTANTS)} mutants, {len(problems)} expectation(s) unmet")
    for p in problems:
        print(f"  FAIL {p}")
    return 1 if problems else 0


def _reliability_rows(case: ReliabilityCase) -> list[dict]:
    """One `_measure_shifts` record per frame pair. Confidence is well over
    `MIN_CONFIDENCE` throughout: this table is about what the filter does with
    measurements it accepts, not about which ones it accepts."""
    n = len(case.shifts)
    offs = (case.d_offset if isinstance(case.d_offset, tuple)
            else (case.d_offset,) * n)
    return [{"pair": i, "shift": s, "confidence": 0.9, "d_offset": offs[i],
             "span": case.span, "wrapped": False}
            for i, s in enumerate(case.shifts)]


def _probe_with(patches: tuple[Patch, ...], label: str):
    """`scene_probe.py`'s own source with `patches` applied, loaded as a fresh module.

    The SUBJECT is edited, never the table - a control whose expectation moves with the
    thing it is checking is not a control (AGENTS.md rule 12). Every patch asserts its
    target appears exactly once, for the reason `apply_patches` does.
    """
    path = HERE / "scene_probe.py"
    src = path.read_text()
    for p in patches:
        if src.count(p.old) != 1:
            raise SystemExit(
                f"{label!r}: its target appears {src.count(p.old)} times in {path}, "
                f"expected exactly 1. The file has changed and this patch no longer "
                f"bites.\n--- target ---\n{p.old}")
        src = src.replace(p.old, p.new)
    spec = importlib.util.spec_from_loader(f"scene_probe__{abs(hash(label))}",
                                           loader=None)
    mod = importlib.util.module_from_spec(spec)
    mod.__file__ = str(path)
    exec(compile(src, str(path), "exec"), mod.__dict__)  # noqa: S102
    return mod


def _reliability_verdicts(mod) -> dict[str, tuple[bool, str]]:
    """Per case: was the layer readable, and what did the note say about it."""
    scene = mod.SCENES["s1_parallax"]()
    out = {}
    for case in RELIABILITY_CASES:
        # A MUTANT THAT RAISES IS CAUGHT, NOT A HARNESS FAILURE. The `usable = list(read)`
        # mutant drops the resolvability filter, and since 2026-08-27 `read` carries the
        # rows with no reported offset - so that mutant now divides by zero instead of
        # returning a wrong verdict. Letting the exception escape would take the whole
        # selftest down at exit 1 with a traceback, which is indistinguishable from the
        # suite being broken. It is recorded as a distinct verdict instead, which differs
        # from every real one and so reads as caught.
        try:
            good, notes = scene._reliable({"L": _reliability_rows(case)})
        except Exception as e:  # noqa: BLE001 - the verdict IS "it raised"
            out[case.label] = (False, f"RAISED {type(e).__name__}: {e}")
            continue
        out[case.label] = ("L" in good, " ".join(notes))
    return out


def reliability_selftest() -> int:
    """Can the reliability filter refuse a layer, can it still accept one, and does it
    say the right thing about the one it refused?

    Reads no fixture and needs no toolchain, so it runs where the suite above cannot.
    """
    print("the reliability filter - `which layers the frames can be read for`\n")
    shipped = _reliability_verdicts(scene_probe)
    reasons = scene_probe.ParallaxScene.UNRESOLVED_REASONS
    problems = []
    w = max(len(c.label) for c in RELIABILITY_CASES)
    for case in RELIABILITY_CASES:
        readable, note = shipped[case.label]
        stated = "readable" if case.readable else "unreadable"
        answered = "readable" if readable else "unreadable"
        ok = readable == case.readable
        # The verdict is half the answer. A note naming a reason the record does not
        # have is a false sentence in evidence, and it passes any pass/fail check.
        said = sorted(k for k, text in reasons.items() if text in note)
        want = [case.reason] if case.reason else []
        reason_ok = said == want
        print(f"  {case.label:<{w}}  stated {stated:<10}  got {answered:<10}  "
              f"reason {str(want or ['-']):<12} said {str(said or ['-']):<12}  "
              f"{'ok' if ok and reason_ok else '<-- UNMET'}")
        if not ok:
            problems.append(f"{case.label}: stated {stated}, got {answered} "
                            f"-- {case.why}")
        if not reason_ok:
            problems.append(f"{case.label}: the note gives {said or 'no reason'} where "
                            f"the record has {want or 'none'} -- {note!r}")

    print("\nmutants - the shipped file with one line changed:")
    for label, patches in RELIABILITY_MUTANTS.items():
        got = _reliability_verdicts(_probe_with(patches, label))
        moved = sorted(
            f"{c.label} ({'verdict' if got[c.label][0] != shipped[c.label][0] else 'note'})"
            for c in RELIABILITY_CASES if got[c.label] != shipped[c.label])
        print(f"  {label}\n    moves {moved or 'NOTHING'}")
        if not moved:
            problems.append(f"mutant {label!r} SURVIVED: every row of the table sits "
                            f"where the shipped file leaves it, so the table does not "
                            f"pin the line this mutant removed")

    print(f"\n{len(RELIABILITY_CASES)} layer records, "
          f"{len(RELIABILITY_MUTANTS)} mutants, {len(problems)} expectation(s) unmet")
    for p in problems:
        print(f"  FAIL {p}")
    return 1 if problems else 0


# --------------------------------------------------------------------------- #


def _scene_record(scene: str, passed: dict[str, bool],
                  scored: dict[str, bool]) -> dict:
    """A stored-shaped scene grading, in exactly the shape `scene_probe.drive` writes.

    The ANSWERS are the caller's stated table, and the selftest's checks assert those
    stated numbers as literals - never what the reader returns for the record - so the
    fixture does not import its expectation from the code it checks. The writer here is
    a fixture, not `drive` itself, which would need a submission.
    """
    crits = [{"id": cid, "question": q, "passed": passed[cid],
              "evidence": f"evidence for {cid}", "scored": scored[cid]}
             for cid, q in scene_probe.SCENES[scene].criteria]
    tot = sum(1 for c in crits if c["scored"])
    p = sum(1 for c in crits if c["scored"] and c["passed"])
    return {"tier": "scene_probe", "scene": scene, "seeds": [7, 99], "ticks": 660,
            "frames_captured": 12, "frames_usable": True, "film_notes": [],
            "events_fired": [], "passed": p, "total": tot,
            "usable": bool(tot), "score": p / tot if tot else 0.0,
            "measured_twice": [], "image_only": [],
            "unscored": {c["id"]: c["evidence"] for c in crits if not c["scored"]},
            "wall_s": 1.0, "criteria": crits}


def census_selftest() -> int:
    """Can the census say NO?

    A census that reports `yes` on every row it has ever been shown is indistinguishable
    from one that cannot report anything else, and it would read as a clean bill of
    health for a criterion that never fired. So drive it over a population built here,
    where the answers are stated before it runs.

    The STORED half does the same over a runs tree built here, for the reading of
    stored scene gradings: per-criterion counts stated as literals, every file named,
    every malformed record refused by a named reason and entering no count, a game-tier
    record invisible to the section, and an empty tree still reading NOT ASKED. The
    refusals are the mutant half - each is an input the reading must go red on - and
    the well-formed records counted beside them are the variant half: noise must not
    refuse the corpus.
    """
    scene = "s2_glass"
    ids = [cid for cid, _ in scene_probe.SCENES[scene].criteria]
    stuck, varies = ids[0], ids[1]
    pop = []
    for i in range(4):
        passed = {cid: True for cid in ids}
        scored = {cid: True for cid in ids}
        passed[varies] = i % 2 == 0          # this one takes both values
        pop.append((scene, "mutant", f"synthetic {i}", passed, scored))
    # A third criterion is measured on nothing at all: always unscored.
    for _scene, _kind, _label, _passed, scored in pop:
        scored[ids[2]] = False

    import contextlib
    import io
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        problems = census(pop, None)
    text = buf.getvalue()
    checks = [
        # PER LINE, like the other two. `stuck in text and "NO ..." in text` is two
        # independent whole-text searches - `stuck` is in the table by construction and
        # the third criterion's row supplies the verdict string - so it stayed green
        # even when `stuck`'s own row read `yes`.
        (f"`{stuck}` never fails and is named an open question",
         any(line.startswith(stuck) and "NO - AN OPEN QUESTION" in line
             for line in text.splitlines())),
        (f"`{varies}` takes both values and is named separated",
         any(line.startswith(varies) and line.rstrip().endswith("yes")
             for line in text.splitlines())),
        (f"`{ids[2]}` is unscored on every subject and is not called separated",
         any(line.startswith(ids[2]) and "NO - AN OPEN QUESTION" in line
             for line in text.splitlines())),
        ("an all-yes population is not what this returns",
         problems >= 2),
        ("a missing --runs-root reads as NOT ASKED, never as zero",
         "NOT ASKED" in text and "0 submissions" not in text),
    ]
    bad = [name for name, ok in checks if not ok]
    for name, ok in checks:
        print(f"  {'ok  ' if ok else 'FAIL'} {name}")
    if bad:
        print(f"census selftest: {len(bad)} unmet -- the census cannot be trusted to "
              f"report a criterion that separated nothing")
        print(text)
        return 1

    # -- the STORED half: a runs tree whose answers are stated first --------- #
    #
    # Two s1 gradings that disagree on 2 criteria and agree everywhere else, an s2
    # grading under a NON-playbot name (the content net must still find it), a
    # game-tier playbot.json (another task class: neither counted nor refused), a
    # scene record with a verdict stored as a string, an unparseable playbot.json,
    # and a playbot.json naming a tier neither instrument writes. Every count and
    # every refusal below is a literal written before the census ran.
    s1 = [cid for cid, _ in scene_probe.SCENES["s1_parallax"].criteria]
    s2 = [cid for cid, _ in scene_probe.SCENES["s2_glass"].criteria]
    base_pass = {cid: True for cid in s1}
    base_score = {cid: True for cid in s1}
    base_pass["layers.depth_ordered"] = False
    base_score["layers.image_parallax"] = False
    base_score["loop.seamless"] = False
    a_pass = dict(base_pass)                       # state.shape PASS
    b_pass = dict(base_pass, **{"state.shape": False, "layers.depth_ordered": True})
    c_pass = {cid: True for cid in s2}
    c_score = {cid: True for cid in s2}
    e_record = _scene_record("s1_parallax", a_pass, base_score)
    e_record["criteria"][0]["scored"] = "false"    # a verdict stored as a string

    with tempfile.TemporaryDirectory(prefix="scene-census-stored-") as td:
        root = Path(td)
        files = {
            "run-a/artifacts/s1_parallax__ts__t0/eval/playbot.json":
                _scene_record("s1_parallax", a_pass, base_score),
            "run-a/artifacts/s1_parallax__ts__t1/eval/playbot.json":
                _scene_record("s1_parallax", b_pass, base_score),
            # Net B: right content, a name the tier-2 slot never uses.
            "run-b/artifacts/s2_glass__rs__t0/eval/scene_regrade.json":
                _scene_record("s2_glass", c_pass, c_score),
            # Another task class: in the slot, out of this population.
            "run-c/artifacts/g1_pong__gd__t0/eval/playbot.json":
                {"tier": "playbot", "total": 4, "usable": True, "criteria": []},
            "run-d/artifacts/s1_parallax__ts__t2/eval/playbot.json": e_record,
            "run-e/artifacts/s1_parallax__ts__t3/eval/playbot.json": "{not json",
            "run-f/artifacts/s2_glass__gd__t0/eval/playbot.json":
                {"tier": "legacy_judge", "criteria": []},
        }
        for rel, doc in files.items():
            p = root / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(doc if isinstance(doc, str) else json.dumps(doc))

        import contextlib
        import io
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            census([], root)
        stored = buf.getvalue()
        lines = stored.splitlines()
        abs_paths = {rel: str(root / rel) for rel in files}
        # The census prints a refusal as the record's path line followed by its
        # reason line, so a match needs BOTH lines, never one.
        def refused_as(rel: str, token: str) -> bool:
            return any(abs_paths[rel] in ln and token in nxt
                       for ln, nxt in zip(lines, lines[1:]))
        checks = [
            ("the stored section is its own, named apart from the fixture tables",
             "STORED SCENE GRADINGS" in stored and "the corpus" in stored),
            ("3 scene gradings and 3 refusals are counted",
             "3 record(s)" in stored and "3 refused" in stored),
            ("every scene grading's file is named",
             all(abs_paths[rel] in stored
                 for rel in files if rel.startswith(("run-a", "run-b")))),
            ("a game-tier playbot.json is neither counted nor refused",
             "g1_pong" not in stored),
            ("the string verdict is refused by name",
             refused_as("run-d/artifacts/s1_parallax__ts__t2/eval/playbot.json",
                        "MALFORMED_CRITERION")),
            ("the unparseable record is refused by name",
             refused_as("run-e/artifacts/s1_parallax__ts__t3/eval/playbot.json",
                        "UNREADABLE_JSON")),
            ("a slot record naming a third tier is refused by name",
             refused_as("run-f/artifacts/s2_glass__gd__t0/eval/playbot.json",
                        "UNCLAIMED_SLOT")),
            ("the per-scene header states its population",
             "s1_parallax: 2 stored grading(s)" in stored
             and "s2_glass: 1 stored grading(s)" in stored),
            # STATED COUNTS. `state.shape` passes on record a and fails on record b;
            # `layers.depth_ordered` the other way round; the 2 unscored criteria are
            # unscored on both; everything else passes twice.
            ("state.shape 1 pass 1 fail, separated",
             any(ln.startswith("state.shape") and ln.rstrip().endswith("yes")
                 and ln.split()[1:3] == ["1", "1"] for ln in lines)),
            ("layers.depth_ordered 1 pass 1 fail, separated",
             any(ln.startswith("layers.depth_ordered")
                 and ln.split()[1:3] == ["1", "1"] and ln.rstrip().endswith("yes")
                 for ln in lines)),
            ("layers.image_parallax unscored on both and named as never measured",
             any(ln.startswith("layers.image_parallax")
                 and ln.split()[1:4] == ["0", "0", "2"]
                 and "UNSCORED ON EVERY STORED GRADING" in ln for ln in lines)),
            ("wheels.match_speed passes twice and is not called separated",
             any(ln.startswith("wheels.match_speed")
                 and ln.split()[1:4] == ["2", "0", "0"]
                 and "NO - AN OPEN QUESTION" in ln for ln in lines)),
            ("the s2 content-net row passes on its single grading",
             any(ln.startswith("glass.refracts") and ln.split()[1:4] == ["1", "0", "0"]
                 and "NO - AN OPEN QUESTION" in ln for ln in lines)),
        ]
        # THE MUTANTS OF THE READER: every refusal kind, driven directly, each an
        # input the shape check must go red on. A record that exists cannot be
        # silently skipped, so each malformed shape has its own named answer.
        good = _scene_record("s1_parallax", a_pass, base_score)
        n_unit = len(checks)

        def refuses(label: str, rec: object, token: str) -> None:
            got = read_stored_grading(rec, "p")
            ok = (isinstance(got, StoredRefusal) and token in got.reason)
            checks.append((label, ok))

        def mutate(**kw: object) -> dict:
            d = json.loads(json.dumps(good))
            for k, v in kw.items():
                d[k] = v
            return d

        refuses("a scene the registry does not hold is UNKNOWN_SCENE",
                mutate(scene="s9_nowhere"), "UNKNOWN_SCENE")
        refuses("a record with no criteria list is refused",
                mutate(criteria={}), "NO_CRITERIA_LIST")
        refuses("a criteria entry that is not an object is refused",
                mutate(criteria=good["criteria"] + ["state.shape"]),
                "MALFORMED_CRITERION")
        refuses("an id that is not a string is refused",
                mutate(criteria=good["criteria"][:-1]
                       + [{"id": 7, "passed": True, "scored": True}]),
                "MALFORMED_CRITERION")
        refuses("a duplicate criterion is refused",
                mutate(criteria=good["criteria"] + [good["criteria"][0]]),
                "DUPLICATE_CRITERION")
        refuses("an id outside the scene's registry is refused",
                mutate(criteria=good["criteria"][:-1]
                       + [{"id": "water.level_under_tilt", "passed": True,
                           "scored": True}]),
                "UNDECLARED_CRITERION")
        refuses("a missing registry criterion is refused",
                mutate(criteria=good["criteria"][:-1]), "INCOMPLETE_CRITERIA")
        refuses("unscored keys that disagree with the criteria are refused",
                mutate(unscored={}), "UNSCORED_DISAGREEMENT")
        refuses("a total that disagrees with the criteria is refused",
                mutate(total=7), "TOTALS_DISAGREEMENT")
        refuses("a non-integer passed count is refused",
                mutate(passed="5"), "TOTALS_DISAGREEMENT")
        refuses("usable that disagrees with the totals is refused",
                mutate(usable=True, total=0, passed=0, score=0.0,
                       criteria=[dict(c, scored=False) for c in good["criteria"]],
                       unscored={c["id"]: "x" for c in good["criteria"]}),
                "USABLE_DISAGREEMENT")
        refuses("a score that disagrees with the counts is refused",
                mutate(score=0.5), "SCORE_DISAGREEMENT")
        refuses("a score stored as a string is refused",
                mutate(score="0.833"), "SCORE_DISAGREEMENT")
        refuses("not an object at all is refused", [1, 2], "NOT_AN_OBJECT")
        # The GREEN half: the well-formed record reads as a grading, not a refusal.
        checks.append(("the well-formed record reads as a grading",
                       isinstance(read_stored_grading(good, "p"), StoredGrading)))

        # EVERY stored check is asserted and printed. An earlier version sliced
        # `checks[n_unit:]`, which skipped the 13 in-situ checks above entirely - they
        # were computed and discarded while this line still reported them met, and the
        # stored half of the selftest could not say NO (found by review on task 232).
        bad += [name for name, ok in checks if not ok]
        for name, ok in checks:
            print(f"  {'ok  ' if ok else 'FAIL'} {name}")

        # An empty tree and a game-only tree are NOT ASKED, never a zero result.
        with tempfile.TemporaryDirectory(prefix="scene-census-empty-") as td2:
            buf2 = io.StringIO()
            with contextlib.redirect_stdout(buf2):
                census([], Path(td2))
            empty = buf2.getvalue()
        buf3 = io.StringIO()
        with contextlib.redirect_stdout(buf3):
            census([], root / "run-c")          # holds only the g1_pong record
        games = buf3.getvalue()
        for name, ok in (
                ("an empty tree reads NOT ASKED, never 0 separated",
                 "NOT ASKED" in empty and "0 scene gradings on disk" in empty),
                ("a game-only tree reads NOT ASKED and says what it did see",
                 "NOT ASKED" in games and "game-tier" in games
                 and "1 playbot.json" in games)):
            checks.append((name, ok))
            if not ok:
                bad.append(name)
            print(f"  {'ok  ' if ok else 'FAIL'} {name}")

    if bad:
        print(f"census selftest: {len(bad)} unmet -- the census cannot be trusted to "
              f"report a criterion that separated nothing")
        print(text)
        try:
            print(stored)
        except NameError:
            pass
        return 1
    print(f"census selftest: {len(checks)} expectations met")
    return 0


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--verbose", "-v", action="store_true",
                    help="print the evidence behind every verdict")
    ap.add_argument("--only", default=None,
                    help="run only this scene, or only mutants for this criterion id")
    ap.add_argument("--census", action="store_true",
                    help="report what each criterion separated in this population")
    ap.add_argument("--runs-root", type=Path, default=None,
                    help="a main checkout's eval/runs, for the stored-grading census")
    ap.add_argument("--census-selftest", action="store_true",
                    help="prove the census can report a criterion that separated "
                         "nothing; needs no fixtures and no toolchain")
    ap.add_argument("--reliability-selftest", action="store_true",
                    help="drive ParallaxScene._reliable over hand-written layer records "
                         "and its own mutants; needs no fixtures and no toolchain")
    ap.add_argument("--attribution-selftest", action="store_true",
                    help="drive ParallaxScene._own_band over hand-written band tables "
                         "and its own mutants; needs no fixtures and no toolchain")
    args = ap.parse_args(argv)

    if args.census_selftest:
        return census_selftest()
    if args.reliability_selftest:
        return reliability_selftest()
    if args.attribution_selftest:
        return attribution_selftest()

    wanted = [m for m in MUTANTS
              if args.only in (None, m.scene, m.criterion)]
    variants = [v for v in VARIANTS if args.only in (None, v.scene)]
    if not wanted:
        print(f"no mutant for {args.only!r}", file=sys.stderr)
        return 2
    if shutil.which("just") is None:
        print("`just` is not on PATH; these tests cannot run", file=sys.stderr)
        return 2

    rows: list[tuple[str, str, str, str, str, bool]] = []
    variant_rows: list[tuple[str, str, str]] = []
    census_rows: list[tuple[str, str, str, dict[str, bool], dict[str, bool]]] = []
    problems: list[str] = []

    with tempfile.TemporaryDirectory(prefix="scene-mutants-") as td:
        tmp = Path(td)

        # -- POSITIVE CONTROL: one healthy run per scene --------------------- #
        healthy: dict[str, Verdicts] = {}
        for scene in sorted({m.scene for m in wanted} | {v.scene for v in variants}):
            repo = copy_fixture(scene, tmp / f"healthy-{scene}")
            healthy[scene] = run_probe(repo, scene)
            census_rows.append((scene, "reference", "the reference fixture",
                                healthy[scene].passed, healthy[scene].scored))
            red = sorted(c for c, ok in healthy[scene].passed.items() if not ok)
            print(f"healthy {scene:<12} {healthy[scene].wall_s:>5.1f}s"
                  f"{'' if not red else '   RED: ' + str(red)}", flush=True)
            if red:
                problems.append(
                    f"{scene}: the HEALTHY reference failed {red} -- "
                    f"{'; '.join(healthy[scene].evidence[c][:200] for c in red[:2])}")

        # -- one mutant per criterion ---------------------------------------- #
        for i, m in enumerate(wanted):
            repo = copy_fixture(m.scene, tmp / f"mutant-{i}")
            apply_patches(repo, m.patches, m.label)
            got = run_probe(repo, m.scene)
            h = healthy[m.scene]
            census_rows.append((m.scene, "mutant", m.label, got.passed, got.scored))

            h_pass, h_scored = h.passed.get(m.criterion), h.scored.get(m.criterion)
            g_pass, g_scored = got.passed.get(m.criterion), got.scored.get(m.criterion)
            ok = (h_pass is True and h_scored is True
                  and g_pass is False and g_scored is True)
            if h_pass is not True:
                problems.append(f"{m.criterion}: HEALTHY {m.scene} did not pass "
                                f"(passed={h_pass}) -- "
                                f"{h.evidence.get(m.criterion, '')[:300]}")
            elif h_scored is not True:
                problems.append(f"{m.criterion}: HEALTHY {m.scene} passed but was not "
                                f"scored -- {h.evidence.get(m.criterion, '')[:300]}")
            if g_pass is not False:
                problems.append(f"{m.criterion}: MUTANT '{m.label}' did not go red "
                                f"(passed={g_pass}) -- "
                                f"{got.evidence.get(m.criterion, '')[:300]}")
            elif g_scored is not True:
                problems.append(
                    f"{m.criterion}: MUTANT '{m.label}' came back UNSCORED rather than "
                    f"failed. An excluded criterion is not a caught defect -- "
                    f"{got.evidence.get(m.criterion, '')[:300]}")

            rows.append((m.criterion, m.scene, m.label,
                         _cell(h_pass, h_scored), _cell(g_pass, g_scored), ok))
            extra = sorted(cid for cid in got.passed
                           if cid != m.criterion
                           and got.passed[cid] != h.passed.get(cid)
                           and cid not in m.collateral)
            if extra:
                print(f"  note: mutant '{m.label}' also flipped {extra}", flush=True)
            if args.verbose:
                print(f"  healthy: {h.evidence.get(m.criterion, '')[:400]}")
                print(f"  mutant : {got.evidence.get(m.criterion, '')[:400]}")
            print(f"  {m.criterion:<24} {got.wall_s:>5.1f}s "
                  f"{'ok' if ok else 'UNMET'}", flush=True)

        # -- VARIANTS: correct scenes the reference does not resemble --------- #
        for i, v in enumerate(variants):
            repo = copy_fixture(v.scene, tmp / f"variant-{i}")
            apply_patches(repo, v.patches, v.label)
            got = run_probe(repo, v.scene)
            census_rows.append((v.scene, "variant", v.label, got.passed, got.scored))
            # A criterion the scene declares `diagnostic_only` reports scored=False BY
            # DESIGN. Read the design intent out of the scene rather than letting a
            # variant waive it, or the one field allowed to excuse failures starts
            # hiding harness bugs (rule 7).
            diagnostic = scene_probe.SCENES[v.scene].diagnostic_only
            waived = set(v.tolerates) | set(diagnostic)
            failed = sorted(c for c, ok in got.passed.items()
                            if not ok and c not in waived)
            unscored = sorted(c for c, sc in got.scored.items()
                              if not sc and c not in waived)
            bad = failed + unscored
            used = sorted(c for c in v.tolerates
                          if not got.passed.get(c, True) or not got.scored.get(c, True))
            if v.tolerates:
                print(f"  note: variant '{v.label}' tolerates {list(v.tolerates)}; "
                      f"fired for {used or 'NOTHING - the tolerance is dead'}",
                      flush=True)
            variant_rows.append((v.label, ", ".join(v.exercises),
                                 "ok" if not bad else f"UNMET: {bad}"))
            if bad:
                problems.append(
                    f"variant '{v.label}' is a CORRECT scene and the probe failed "
                    f"{bad} on it -- "
                    f"{'; '.join(got.evidence.get(c, '')[:200] for c in bad[:2])}")
            print(f"  variant {v.label[:46]:<46} {got.wall_s:>5.1f}s "
                  f"{'ok' if not bad else 'UNMET'}", flush=True)

    w = max(len(r[0]) for r in rows)
    print(f"\n{'criterion':<{w}}  {'scene':<12}  {'healthy':<9}  {'mutant':<9}  "
          f"mutant applied")
    print("-" * (w + 64))
    for cid, scene, label, hcell, gcell, ok in rows:
        print(f"{cid:<{w}}  {scene:<12}  {hcell:<9}  {gcell:<9}  "
              f"{label}{'' if ok else '   <-- UNMET'}")
    if variant_rows:
        n = max(len(r[0]) for r in variant_rows)
        print(f"\nvariants - CORRECT scenes the reference does not resemble; every "
              f"criterion must still pass\n{'variant':<{n}}  exercises")
        print("-" * (n + 44))
        for label, exercises, verdict in variant_rows:
            print(f"{label:<{n}}  {exercises:<46}  {verdict}")

    covered = {(m.scene, m.criterion) for m in wanted}
    missing = sorted((s, cid) for s in {m.scene for m in wanted}
                     for cid, _ in scene_probe.SCENES[s].criteria
                     if (s, cid) not in covered)
    if missing and args.only is None:
        problems.append(f"no mutant pins {missing} - a criterion with no mutant has "
                        f"never been shown able to fail")
    print(f"\n{len(rows)} mutants over {len(covered)} criteria, "
          f"{len(variant_rows)} variants, {len(problems)} expectation(s) unmet")
    for p in problems:
        print(f"  FAIL {p}")

    if args.census:
        census(census_rows, args.runs_root)
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
