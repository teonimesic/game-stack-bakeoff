#!/usr/bin/env python3
"""The SCENE PROBE - tier 2 for the scene task class.

A scene has no player, so the play-bot tier has no referent (`eval/SCENES.md`). Its
replacement is this: criteria computed deterministically from the per-tick telemetry the
scene's probe emits AND from the frames its `just film` recipe captures. It carries the
play-bot's weight, so it is built to the play-bot's standard - every criterion binary,
equally weighted, always reported per criterion, and pinned in BOTH directions by
`scene_mutants.py` (a mutant asks whether a check can fail; only a variant asks whether
it can still pass on an input it mishandles).

    python3 judge/scene_probe.py s1_parallax /path/to/submission
    python3 judge/scene_probe.py s2_glass    /path/to/submission --json out.json

MEASURE TWICE WHERE THE IMAGE ALLOWS IT. Telemetry is what the submission SAYS it did;
the frames are what it did. A criterion that reads only telemetry is satisfiable by a
submission that quietly lies, and the parallax and water-surface criteria are exactly
where that lie is cheapest to write by accident. Each criterion below declares which
halves it has, and `measured_twice` in the result says which ones actually ran.

WHAT AN ABSENT HALF MEANS, because the two cases are not the same and collapsing them is
how a gate goes fail-open (AGENTS.md rule 7):

| | |
|---|---|
| `just film` produced no frames, or not the contracted 12 | a fact about the SUBMISSION. An image-ONLY criterion scores FALSE. A criterion that also has a telemetry half is scored on it, and `image_half` records why - one broken recipe must not deduct once per criterion |
| the frames exist but no captured MOMENT satisfies the criterion's precondition - no frame lands inside the light ramp, no layer wrapped between two frames, the glass never left its opening position | an experiment that could not be set up. `Criterion(scored=False)`, reported, excluded from the score, and counted in `unscored` |

THE HONEST EXPECTATION, stated here because the results will be published: **1 submission
has met these criteria** (`eval/RUNS.md`), and every threshold below was still chosen
against fixtures written by the same hand. #46 is sixteen false negatives found in one
sweep of criteria that were green on their reference; the same is the reasonable prior
here, and first contact paid it immediately - `layers.depth_ordered` scored that
submission FALSE on a scene whose layers were ordered perfectly, because it subtracted two
reported `offset` values and the submission wrapped them (`tasks/162`). Read `_walk`
before adding a criterion that touches `offset`. `scene_mutants.py --census` is what
reports which criteria ever separated anything.

THE ONE INSTRUMENT ERROR ALREADY MEASURED, so the first real run does not have to
rediscover it: the image-side shift estimator misses **8 of the 132 frame pairs in the 3
parallax fixtures** - 1 of 44 on the reference, 5 of 44 on the `numbered nearest-first`
variant, 2 of 44 on the `1.5x larger` one - and every one of the 8 is the same shape, on
the band holding the car: a large object that is stationary on screen offers a competing
match at zero displacement. `ParallaxScene._reliable` and the wrap check's `blind` counter
both name it, and `DECISIONS.md` holds the 5-candidate comparison that decided the
estimator. Expect the rate to be worse on a submission that fills its foreground.
"""

from __future__ import annotations

import argparse
import json
import math
import shutil
import statistics
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Sequence

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import png  # noqa: E402
from probe import (Criterion, ProbeError, ProbeSession, Tick,  # noqa: E402
                   unusable_criteria)

#: How many frames every starter's `just film` captures, and at which ticks. Both are
#: `eval/SCENES.md`'s contract, not this file's choice; the four starters implement
#: `floor(i * TICKS / 11)` for i in 0..11.
CONTRACT_FRAMES = 12

WORLD_UP = (0.0, 1.0, 0.0)


def contract_frame_ticks(ticks: int) -> list[int]:
    return sorted({(i * ticks) // (CONTRACT_FRAMES - 1) for i in range(CONTRACT_FRAMES)})


# --------------------------------------------------------------------------- #
# Reading telemetry
# --------------------------------------------------------------------------- #


def num(d: Any, *path: Any) -> float | None:
    """A finite float at `path` inside nested dicts/lists, or None. Never raises."""
    cur = d
    for key in path:
        try:
            cur = cur[key]
        except (KeyError, IndexError, TypeError):
            return None
    try:
        v = float(cur)
    except (TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


def vec3(d: Any, *path: Any) -> tuple[float, float, float] | None:
    cur = d
    for key in path:
        try:
            cur = cur[key]
        except (KeyError, IndexError, TypeError):
            return None
    if not isinstance(cur, (list, tuple)) or len(cur) != 3:
        return None
    out = []
    for v in cur:
        try:
            f = float(v)
        except (TypeError, ValueError):
            return None
        if not math.isfinite(f):
            return None
        out.append(f)
    return (out[0], out[1], out[2])


def angle_to(v: Sequence[float], w: Sequence[float]) -> float | None:
    """Angle in degrees between two vectors, or None if either has no direction."""
    nv = math.sqrt(sum(c * c for c in v))
    nw = math.sqrt(sum(c * c for c in w))
    if nv < 1e-9 or nw < 1e-9:
        return None
    dot = sum(a * b for a, b in zip(v, w, strict=True)) / (nv * nw)
    return math.degrees(math.acos(max(-1.0, min(1.0, dot))))


# --------------------------------------------------------------------------- #
# Reading frames
#
# EVERYTHING HERE IS A DENSITY, A FRACTION OR A RATIO OF TWO MEASUREMENTS OF THE SAME
# FRAME. Submissions choose their own capture geometry - `judge/static.py`'s
# `FRAME_CRITERION_MEASURES` records why (#59) - so a raw pixel count would rank the
# resolution. The one quantity below in pixels, the estimated layer shift, is only ever
# compared against another shift measured in the same frames.
# --------------------------------------------------------------------------- #


def luminance(img: png.Image, x: int, y: int) -> float:
    r, g, b = img.rgb(x, y)
    return (r * 299 + g * 587 + b * 114) / 1000.0


def band_profile(img: png.Image, top: float, bottom: float,
                 rows: int = 10) -> list[float] | None:
    """A 1-D horizontal-gradient signature of one horizontal band of a frame.

    THE SIGNAL IS THE GRADIENT, NOT THE LEVEL, and normalised by its own mean magnitude.
    Both are load-bearing. A scene that ramps from day to night changes every level in
    the frame, so a level-based match reads the LIGHT and not the motion; measured
    against the reference, a level-based estimator got 4 of 11 frame pairs wrong on the
    band that darkens most, and this one gets 43 of 44 right across all 4 bands. A
    gradient is also blind to a large static object's INTERIOR - the car covers 12% of
    the road band's columns and contributes 2 of them here.

    Returns None when the band carries no horizontal structure at all, which is not a
    verdict: it is the one input this estimator cannot answer for.
    """
    h = img.height
    y0 = max(0, min(h - 1, int(top * h)))
    y1 = max(y0 + 1, min(h, int(bottom * h)))
    step = max(1, (y1 - y0) // max(1, rows))
    ys = list(range(y0, y1, step))
    if not ys:
        return None
    w = img.width
    acc = [0.0] * (w - 1)
    for y in ys:
        prev = luminance(img, 0, y)
        for x in range(1, w):
            cur = luminance(img, x, y)
            acc[x - 1] += cur - prev
            prev = cur
    n = float(len(ys))
    acc = [v / n for v in acc]
    mag = sum(abs(v) for v in acc) / max(1, len(acc))
    if mag <= 1e-6:
        return None
    return [v / mag for v in acc]


def best_shift(pa: list[float], pb: list[float],
               limit: int) -> tuple[int, float] | None:
    """How far right `pa`'s content moved to become `pb`, in whole pixels.

    Returns `(shift, confidence)`. Confidence is how much better the winning shift is
    than the average candidate - a flat scan means the band carries no usable signal,
    and the caller drops that pair rather than believing the argmin.
    """
    w = len(pa)
    if w != len(pb) or w < 32:
        return None
    scores: dict[int, float] = {}
    for s in range(-limit, limit + 1):
        x0, x1 = max(0, s), min(w, w + s)
        if x1 - x0 < w * 0.85:
            continue
        scores[s] = sum(abs(pa[x] - pb[x - s]) for x in range(x0, x1)) / (x1 - x0)
    if not scores:
        return None
    bs = min(scores, key=lambda k: scores[k])
    mean = sum(scores.values()) / len(scores)
    if mean <= 1e-9:
        return None
    return bs, 1.0 - scores[bs] / mean


def mean_luminance(img: png.Image) -> float:
    step = max(1, (img.width * img.height) // 6000)
    total, n = 0.0, 0
    for i in range(0, img.width * img.height, step):
        total += luminance(img, i % img.width, i // img.width)
        n += 1
    return total / max(1, n)


def clip_box(box: dict, img: png.Image, shrink: float = 1.0
             ) -> tuple[int, int, int, int] | None:
    """A fractional `{x, y, w, h}` centre-and-size box as whole pixels, or None."""
    for k in ("x", "y", "w", "h"):
        if num(box, k) is None:
            return None
    cx, cy = box["x"] * img.width, box["y"] * img.height
    hw = box["w"] * img.width * 0.5 * shrink
    hh = box["h"] * img.height * 0.5 * shrink
    x0, x1 = int(max(0, cx - hw)), int(min(img.width, cx + hw))
    y0, y1 = int(max(0, cy - hh)), int(min(img.height, cy + hh))
    if x1 - x0 < 6 or y1 - y0 < 6:
        return None
    return x0, y0, x1, y1


def overlap_fraction(a: tuple[int, int, int, int],
                     b: tuple[int, int, int, int]) -> float:
    ox = max(0, min(a[2], b[2]) - max(a[0], b[0]))
    oy = max(0, min(a[3], b[3]) - max(a[1], b[1]))
    area = (a[2] - a[0]) * (a[3] - a[1])
    return (ox * oy) / area if area else 1.0


def gradients(img: png.Image, box: tuple[int, int, int, int]) -> list[float]:
    x0, y0, x1, y1 = box
    return [luminance(img, x + 1, y) - luminance(img, x, y)
            for y in range(y0, y1) for x in range(x0, x1 - 1)]


def edge_density(g: list[float], threshold: float = 10.0) -> float:
    return sum(1 for v in g if abs(v) > threshold) / max(1, len(g))


def mean_abs(values: list[float]) -> float:
    return sum(abs(v) for v in values) / max(1, len(values))


# --------------------------------------------------------------------------- #
# Gathering one submission's evidence
# --------------------------------------------------------------------------- #


class SceneRun:
    """Everything read off one submission: three traces and three sets of frames."""

    def __init__(self) -> None:
        self.trace_a: list[Tick] = []
        self.hashes_a2: list[str] = []
        self.trace_b: list[Tick] = []
        self.frames_a: list[png.Image] = []
        self.bytes_a: list[bytes] = []
        self.bytes_a2: list[bytes] = []
        self.bytes_b: list[bytes] = []
        self.frame_ticks: list[int] = []
        self.film_notes: list[str] = []

    @property
    def frames_usable(self) -> bool:
        return (len(self.frames_a) == CONTRACT_FRAMES
                and len(self.frame_ticks) == CONTRACT_FRAMES
                and self.one_geometry)

    @property
    def one_geometry(self) -> bool:
        """Do all the captures share a size?

        Not tidiness. Every image measure here compares one rectangle of one frame with
        the same rectangle of another, and two frames of different sizes would be
        compared element by element up to the shorter of the two - a silently truncated
        answer rather than a refusal, which is the fail-open direction (rule 7).
        """
        return len({(im.width, im.height) for im in self.frames_a}) <= 1

    def why_frames_unusable(self) -> str:
        if self.frames_a and not self.one_geometry:
            sizes = sorted({(im.width, im.height) for im in self.frames_a})
            return (f"`just film` produced frames of {len(sizes)} different sizes "
                    f"({sizes}), so no two of them can be compared")
        return (f"`just film` produced {len(self.frames_a)} frames, not the contracted "
                f"{CONTRACT_FRAMES}, so no frame can be attached to a tick"
                + (f" ({'; '.join(self.film_notes)})" if self.film_notes else ""))

    def state_at(self, tick: int) -> dict[str, Any]:
        for t in self.trace_a:
            if t.tick == tick:
                return t.state
        return {}


def _idle_trace(repo: Path, seed: int, ticks: int,
                env: dict[str, str] | None) -> list[Tick]:
    """`ticks` empty input objects, one per tick. The scene ignores every one of them."""
    with ProbeSession(repo=repo, seed=seed, env=env,
                      total_timeout_s=2400.0) as s:
        for _ in range(ticks):
            s.step_raw({})
        return list(s.history)


def _film(repo: Path, seed: int, ticks: int, env: dict[str, str] | None,
          notes: list[str]) -> tuple[list[Path], Path]:
    outdir = Path(tempfile.mkdtemp(prefix="scene-film-"))
    try:
        r = subprocess.run(["just", "film", str(seed), str(ticks), "-", str(outdir)],
                           cwd=repo, capture_output=True, text=True, timeout=1800,
                           env=env, check=False)
        if r.returncode != 0:
            notes.append(f"seed {seed}: `just film` exit {r.returncode}: "
                         f"{(r.stderr or '')[-200:]}")
    except (OSError, subprocess.SubprocessError) as e:  # noqa: PERF203
        notes.append(f"seed {seed}: `just film` could not run: {e}")
    return sorted(outdir.glob("*.png")), outdir


def gather(scene: "Scene", repo: Path, seed_a: int, seed_b: int,
           env: dict[str, str] | None) -> SceneRun:
    """Drive the submission. Raises ProbeError if it cannot be driven at all."""
    run = SceneRun()
    ticks = scene.ticks
    run.trace_a = _idle_trace(repo, seed_a, ticks, env)
    run.hashes_a2 = [t.hash for t in _idle_trace(repo, seed_a, ticks, env)]
    run.trace_b = _idle_trace(repo, seed_b, ticks, env)

    dirs = []
    try:
        for seed, sink in ((seed_a, "bytes_a"), (seed_a, "bytes_a2"),
                           (seed_b, "bytes_b")):
            paths, outdir = _film(repo, seed, ticks, env, run.film_notes)
            dirs.append(outdir)
            setattr(run, sink, [p.read_bytes() for p in paths])
            if sink == "bytes_a":
                for p in paths:
                    try:
                        run.frames_a.append(png.read(p))
                    except png.PngError as e:
                        run.film_notes.append(f"{p.name}: {e}")
                        run.frames_a = []
                        break
        if len(run.frames_a) == CONTRACT_FRAMES:
            run.frame_ticks = contract_frame_ticks(ticks)
    finally:
        for d in dirs:
            shutil.rmtree(d, ignore_errors=True)
    return run


# --------------------------------------------------------------------------- #
# The scenes
# --------------------------------------------------------------------------- #


class Scene:
    """Base class for one scene's criteria. `criteria` is (id, question) pairs."""

    scene: str = ""
    ticks: int = 660
    criteria: list[tuple[str, str]] = []
    #: Which criteria read the image at all, and which read BOTH halves. Reported so a
    #: reader can see what was actually measured twice rather than take the design's
    #: word for it.
    image_only: frozenset[str] = frozenset()
    both_halves: frozenset[str] = frozenset()
    diagnostic_only: frozenset[str] = frozenset()

    def __init__(self) -> None:
        #: Which criteria's IMAGE half produced a measurement on this run. Recorded by
        #: the criterion that made it, never inferred from its evidence string: the
        #: first version of `measured_twice` matched a phrase only one of the three
        #: criteria writes, so an unscored `loop.seamless` was reported as measured
        #: twice while sitting in `unscored` at the same time. This is the one field a
        #: reader uses to check what was actually measured rather than designed.
        self.image_measured: set[str] = set()

    def image_ran(self, cid: str) -> None:
        self.image_measured.add(cid)

    def question(self, cid: str) -> str:
        for i, q in self.criteria:
            if i == cid:
                return q
        raise KeyError(cid)

    def run(self, r: SceneRun) -> list[Criterion]:
        raise NotImplementedError

    # -- shared verdict shapes ------------------------------------------- #

    def ok(self, cid: str, passed: bool, evidence: str) -> Criterion:
        return Criterion(cid, self.question(cid), bool(passed), evidence)

    def not_established(self, cid: str, why: str) -> Criterion:
        """The precondition the experiment needs is not in the captured material.

        Not a pass and not a fail. Distinct from a submission whose film recipe is
        broken, which fails - see the module docstring's table.
        """
        return Criterion(cid, self.question(cid), False,
                         f"NOT MEASURED - the experiment could not be set up: {why}",
                         scored=False)

    def all_false(self, reason: str) -> list[Criterion]:
        return [Criterion(cid, q, False, reason, cid not in self.diagnostic_only)
                for cid, q in self.criteria]

    def shape_failed(self, reason: str) -> list[Criterion]:
        return [Criterion(cid, q, False, reason, cid not in self.diagnostic_only)
                for cid, q in self.criteria[1:]]


# --------------------------------------------------------------------------- #


class ParallaxScene(Scene):
    """s1_parallax - a car on a looping road, day into night."""

    scene = "s1_parallax"
    ticks = 660

    #: Fewer than this many declared layers is not a layered background. The prompt asks
    #: for sky, something far, something nearer and the ground, so three is generous;
    #: the naive implementation this rejects is "one flat background scrolled as a unit".
    MIN_LAYERS = 3
    #: Two layers count as scrolling at DISTINCT rates when the slower is at most this
    #: share of the faster. Chosen so 8-bit quantisation of the image shift cannot
    #: manufacture an ordering, and reported in the evidence either way.
    RATE_SEPARATION = 0.95
    #: Adjacent layers' median image shifts must differ before the ordering is read as
    #: visible rather than as rounding: by this SHARE OF THE FRAME'S WIDTH, or by two
    #: whole pixels, whichever is larger. Both terms are needed and neither is
    #: decoration. A shift scales with the frame, so a fixed pixel figure would be a
    #: stricter test at 1920 than at 640 and would rank the capture geometry rather than
    #: the scene (#59); two pixels is where 8-bit quantisation stops meaning anything,
    #: and no share of a small frame can go below it.
    SHIFT_SEPARATION_SHARE = 0.003
    SHIFT_SEPARATION_FLOOR = 2.0
    MIN_CONFIDENCE = 0.15
    #: THE INSTRUMENT'S SELF-CHECK, and it is why the two image criteria below do not
    #: read a single frame pair.
    #:
    #: A band holding a large, bright object that is STATIONARY ON SCREEN - a car the
    #: camera follows, its headlights - offers `best_shift` a competing minimum at zero,
    #: and whether that minimum wins depends on how much contrast the band's own texture
    #: happens to carry. Measured over the reference and over the `numbered
    #: nearest-first` variant, which are the same scene with the seeded layer textures
    #: dealt to different bands: 43 of 44 frame pairs correct in the first, 39 of 44 in
    #: the second, and every miss in the bottom band, where the car is. 4 other
    #: estimators were measured against the same 88 pairs and none beat it, so the
    #: estimator stays and the ROBUSTNESS lives here instead. `DECISIONS.md` has the
    #: table; the one worth knowing without opening it is that clipping the profile at
    #: 3x its own mean - the textbook fix for one strong edge dominating a sum - came
    #: back 9 pairs WORSE than doing nothing.
    #:
    #: A layer is measurable when its per-pair ratio of drawn pixels to reported offset
    #: AGREES WITH ITSELF: at least this share of its pairs within `K_TOLERANCE` of the
    #: layer's own median. That is a statement about repeatability, derived from the
    #: measurements and not from the answer expected of them - a band whose estimates do
    #: not agree with each other cannot support a conclusion drawn from one of them.
    #: `DECISIONS.md` holds the 5-candidate comparison and the per-fixture miss counts.
    K_AGREEMENT = 0.8
    K_TOLERANCE = 0.15
    MIN_PAIRS_PER_LAYER = 4
    #: A layer's per-pair shift-to-offset ratio at a wrap must stay within this of its
    #: ratio away from wraps, or the loop is visibly jumping.
    WRAP_TOLERANCE = 0.25
    #: The same two terms, for the same reason.
    WRAP_FLOOR_SHARE = 0.005
    WRAP_PIXEL_FLOOR = 3.0
    #: Below this swing in `car.speed`, a wheel spun at the mean rate is indistinguish-
    #: able from one driven by the ground, so only the rolling ratio is asked.
    SPEED_VARIATION_FLOOR = 0.05

    criteria = [
        ("state.shape", "Does the probe report the contracted state shape (car, "
                        "layers, front, light) with finite numbers?"),
        ("layers.depth_ordered", "Do the background layers scroll at distinct rates, "
                                 "ordered by the depth each one declares?"),
        ("layers.image_parallax", "Is that same ordering visible IN THE FRAMES - do "
                                  "the bands at different heights shift at different "
                                  "rates?"),
        ("loop.seamless", "When a layer reaches the end of its span and repeats, does "
                          "the image carry on at the same rate instead of jumping?"),
        ("wheels.match_speed", "Does the wheels' angular velocity match the ground "
                               "speed rather than being spun at some unrelated rate?"),
        ("front.occludes", "Does something pass between the camera and the car and "
                           "cover part of it?"),
        ("light.monotonic", "Does the light ramp through every shade between day and "
                            "night rather than cutting between two palettes?"),
        ("seed.pair", "Same seed identical AND different seeds different - in the "
                      "hash chain and in the captured frames?"),
    ]
    image_only = frozenset({"layers.image_parallax"})
    both_halves = frozenset({"loop.seamless", "light.monotonic", "seed.pair"})

    # -- helpers --------------------------------------------------------- #

    @staticmethod
    def _layers(state: dict) -> list[dict]:
        rows = state.get("layers")
        return [r for r in rows if isinstance(r, dict)] if isinstance(rows, list) else []

    @staticmethod
    def _walk(r: SceneRun) -> tuple[dict[Any, dict[int, float]], list[Any]]:
        """Per layer id, its `offset` at every tick, UNWRAPPED against its own `span`,
        and the ids of the layers this could not be done for.

        NOTHING IN THIS CLASS MAY SUBTRACT TWO REPORTED `offset` VALUES. The trace
        contract says `offset` is how far a layer has been displaced so far and `span`
        is the width after which it repeats, and it does not say whether the number
        accumulates or stays inside `[0, span)` - `eval/SCENES.md` decides that both are
        contracted, because the layer declares the `span` that converts one into the
        other. A difference of two reported offsets is therefore a modular residue, not
        a distance, and reading it as a distance is what scored the first real
        submission's `layers.depth_ordered` FALSE on a scene whose layers were ordered
        perfectly (`tasks/162`): all 7 came back below their own declared span while 37
        `wrap` events fired in the same trace.

        The repair is per TICK, not per captured frame: each step is mapped into
        `(-span/2, span/2]` and accumulated, which is exact whenever a layer moves less
        than half a span in one tick and is a NO-OP on a submission that already
        accumulates - so a cumulative scene comes back bit-identical to what it got
        before. On the submission that provoked this the widest step is 4.0% of its
        layer's span; between two captured frames, 60 ticks apart, the same layer moves
        1.6-2.25 spans and no per-frame unwrap could recover it.

        THE UNWRAP IS ONLY DEFINED ACROSS CONSECUTIVE TRACE LINES, so a layer that stops
        being reported and comes back is DROPPED rather than bridged. Bridging is the
        fail-open direction and it is silent: with `span` 100, offsets `0`, missing,
        `120` unwrap to a step of 20 and the layer's real 120 units of travel disappear
        into a plausible number. `state.shape` reads tick 0 only, so nothing upstream
        catches it. The second return value names the dropped layers and every
        caller reports them - a layer the contract's one-record-per-tick was not held to
        cannot have a rate read off it, and it must not quietly acquire a smaller one.
        """
        walk: dict[Any, dict[int, float]] = {}
        prev: dict[Any, float] = {}
        acc: dict[Any, float] = {}
        last_seen: dict[Any, int] = {}
        holed: set[Any] = set()
        for line, t in enumerate(r.trace_a):
            for row in ParallaxScene._layers(t.state):
                lid = row.get("id")
                offset, span = num(row, "offset"), num(row, "span")
                if lid is None or offset is None:
                    continue
                if lid not in walk:
                    walk[lid], acc[lid] = {}, offset
                elif last_seen[lid] == line - 1:
                    step = offset - prev[lid]
                    if span is not None and span > 0:
                        step -= span * round(step / span)
                    acc[lid] += step
                else:
                    holed.add(lid)
                prev[lid], last_seen[lid] = offset, line
                walk[lid][t.tick] = acc[lid]
        for lid in holed:
            walk.pop(lid, None)
        return walk, sorted(holed, key=str)

    @staticmethod
    def _travelled(walk: dict[Any, dict[int, float]], lid: Any) -> float | None:
        """How far one layer moved from its first reported tick to its last."""
        one = walk.get(lid)
        if not one or len(one) < 2:
            return None
        ticks = sorted(one)
        return one[ticks[-1]] - one[ticks[0]]

    def _shift_limit(self, img: png.Image) -> int:
        return max(6, int(img.width * 0.14))

    def _separation(self, img: png.Image) -> float:
        return max(self.SHIFT_SEPARATION_FLOOR,
                   img.width * self.SHIFT_SEPARATION_SHARE)

    def _measure_shifts(self, r: SceneRun) -> dict[int, list[dict]]:
        """Per layer id, one record per consecutive frame pair.

        Each record carries the measured pixel shift, its confidence, and the telemetry
        change in that layer's own `offset` over the same ticks. The two are the point:
        one is what the renderer drew, the other is what the submission said it drew.

        The offset change and the wrap flag both come from `_walk`, never from the two
        reported values: 60 ticks separate two captures, so a layer whose span is small
        enough for `loop.seamless` to have anything to look at is exactly the layer
        whose reported offsets cannot be subtracted.
        """
        out: dict[int, list[dict]] = {}
        # A layer with a hole in its trace is absent from `walk`, so its `d_offset` is
        # None on every pair and `_reliable` reports it as unreadable. The hole itself is
        # FAILED by `layers.depth_ordered`, which is where the whole scene is judged.
        walk, _ = self._walk(r)
        limit = self._shift_limit(r.frames_a[0])
        for layer in self._layers(r.state_at(r.frame_ticks[0])):
            lid = layer.get("id")
            top, bottom = num(layer, "top"), num(layer, "bottom")
            if lid is None or top is None or bottom is None or bottom <= top:
                continue
            profiles = [band_profile(img, top, bottom) for img in r.frames_a]
            rows: list[dict] = []
            for i in range(len(r.frames_a) - 1):
                pa, pb = profiles[i], profiles[i + 1]
                if pa is None or pb is None:
                    continue
                got = best_shift(pa, pb, limit)
                if got is None:
                    continue
                shift, conf = got
                a = self._layer_by_id(r.state_at(r.frame_ticks[i]), lid)
                oa = walk.get(lid, {}).get(r.frame_ticks[i])
                ob = walk.get(lid, {}).get(r.frame_ticks[i + 1])
                span = num(a, "span")
                rows.append({"pair": i, "shift": shift, "confidence": conf,
                             "d_offset": None if oa is None or ob is None else ob - oa,
                             "span": span,
                             "wrapped": bool(span and oa is not None and ob is not None
                                             and span > 0
                                             and int(oa // span) != int(ob // span))})
            out[lid] = rows
        return out

    @staticmethod
    def _layer_by_id(state: dict, lid: Any) -> dict:
        for row in ParallaxScene._layers(state):
            if row.get("id") == lid:
                return row
        return {}

    def _reliable(self, shifts: dict[Any, list[dict]]) -> tuple[dict[Any, dict], list]:
        """Which layers the frames can be read for, and what each one measured.

        See `K_AGREEMENT`. Returns `{lid: {median_shift, k, pairs, agreement}}` for the
        layers whose estimates agree with themselves, and a note per layer that did not.

        A median of exactly zero is RELIABLE, not excluded: a renderer that draws a
        background it reports as moving produces zero on every pair, agreeing with
        itself perfectly, and that is the answer - excluding it would be a fail-open
        channel round the one thing this criterion exists to catch (rule 7).
        """
        good: dict[Any, dict] = {}
        notes: list[str] = []
        for lid, rows in shifts.items():
            usable = [x for x in rows
                      if x["confidence"] >= self.MIN_CONFIDENCE
                      and x["d_offset"] not in (None, 0.0)]
            if len(usable) < self.MIN_PAIRS_PER_LAYER:
                notes.append(f"layer {lid}: only {len(usable)} readable frame pairs")
                continue
            ks = [x["shift"] / x["d_offset"] for x in usable]
            med = statistics.median(ks)
            slack = max(abs(med) * self.K_TOLERANCE, self.K_TOLERANCE)
            agreement = sum(1 for k in ks if abs(k - med) <= slack) / len(ks)
            if agreement < self.K_AGREEMENT:
                notes.append(f"layer {lid}: its drawn-to-reported ratio agrees with "
                             f"itself on only {agreement:.0%} of {len(ks)} pairs")
                continue
            good[lid] = {"median_shift": statistics.median(abs(x["shift"])
                                                           for x in usable),
                         "k": med, "pairs": usable, "agreement": agreement}
        return good, notes

    # -- the criteria ---------------------------------------------------- #

    def run(self, r: SceneRun) -> list[Criterion]:
        out: list[Criterion] = []
        add = out.append
        if not r.trace_a:
            return self.all_false("the probe produced no trace lines")
        t0 = r.trace_a[0]
        layers = self._layers(t0.state)
        shape_ok = (
            num(t0.state, "car", "x") is not None
            and num(t0.state, "car", "speed") is not None
            and isinstance(t0.state.get("car", {}).get("wheels"), list)
            and all(num(w, "radius") is not None and num(w, "angle") is not None
                    for w in t0.state["car"]["wheels"])
            and bool(t0.state["car"]["wheels"])
            and bool(layers)
            and all(num(row, "depth") is not None and num(row, "offset") is not None
                    and num(row, "span") is not None for row in layers)
            and isinstance(t0.state.get("front"), list)
            and num(t0.state, "light", "phase") is not None
            and vec3(t0.state, "light", "sky") is not None
            and vec3(t0.state, "light", "key") is not None)
        add(self.ok("state.shape", shape_ok, f"tick 0 state: {str(t0.state)[:300]}"))
        if not shape_ok:
            return out + self.shape_failed("state shape contract not met")

        shifts = self._measure_shifts(r) if r.frames_usable else {}
        add(self._depth_ordered(r))
        add(self._image_parallax(r, shifts))
        add(self._seamless(r, shifts))
        add(self._wheels(r))
        add(self._front(r))
        add(self._light(r))
        add(self._seed_pair(r))
        return out

    def _depth_ordered(self, r: SceneRun) -> Criterion:
        walk, holed = self._walk(r)
        if holed:
            # FAIL, not unscored. The contract asks for one record per captured tick; a
            # layer that stops appearing and comes back has no readable displacement
            # across the hole, and excusing it is a channel a real bug widens (rule 7).
            return self.ok("layers.depth_ordered", False,
                           f"layer(s) {holed} vanish from the trace and return, so no "
                           f"displacement can be read across the gap; the contract asks "
                           f"for one telemetry record per captured tick")
        rows = []
        for row in self._layers(r.trace_a[0].state):
            depth = num(row, "depth")
            moved = self._travelled(walk, row.get("id"))
            if depth is None or moved is None:
                continue
            rows.append((depth, abs(moved), row.get("id")))
        if len(rows) < self.MIN_LAYERS:
            return self.ok("layers.depth_ordered", False,
                           f"{len(rows)} usable layers, fewer than the {self.MIN_LAYERS} "
                           f"a layered background needs; a background scrolled as one "
                           f"unit is what this criterion rejects")
        rows.sort(key=lambda t: t[0])
        travel = [t[1] for t in rows]
        pairs = [(travel[i], travel[i + 1]) for i in range(len(travel) - 1)]
        ordered = all(b < a * self.RATE_SEPARATION for a, b in pairs)
        detail = ", ".join(f"depth {d:g} moved {t:.1f}" for d, t, _ in rows)
        return self.ok("layers.depth_ordered", ordered,
                       f"over the whole run, unwrapped against each layer's own span, "
                       f"by increasing depth: {detail}"
                       + ("" if ordered else
                          f" - not strictly decreasing at separation "
                          f"{self.RATE_SEPARATION}"))

    def _image_parallax(self, r: SceneRun, shifts: dict[int, list[dict]]) -> Criterion:
        cid = "layers.image_parallax"
        if not r.frames_usable:
            return self.ok(cid, False, r.why_frames_unusable())
        good, notes = self._reliable(shifts)
        depths = {}
        for layer in self._layers(r.trace_a[0].state):
            d = num(layer, "depth")
            if d is not None and layer.get("id") in good:
                depths[layer["id"]] = d
        if len(depths) < self.MIN_LAYERS:
            return self.not_established(
                cid, f"only {len(depths)} of {len(shifts)} declared layers could be "
                     f"read in the frames at all: {notes}. The bands carry too little "
                     f"horizontal structure, or too much of one that does not move")
        order = sorted(depths, key=lambda k: depths[k])
        med = [good[lid]["median_shift"] for lid in order]
        sep = self._separation(r.frames_a[0])
        ok = all(med[i] - med[i + 1] >= sep for i in range(len(med) - 1))
        detail = ", ".join(f"depth {depths[lid]:g} shifted "
                           f"{good[lid]['median_shift']:.0f}px/frame" for lid in order)
        return self.ok(cid, ok,
                       f"median over each band's readable frame pairs, by increasing "
                       f"declared depth: {detail} (nearest must be fastest, by at least "
                       f"{sep:.1f}px in a {r.frames_a[0].width}px frame)"
                       + (f"; not read: {notes}" if notes else ""))

    def _seamless(self, r: SceneRun, shifts: dict[int, list[dict]]) -> Criterion:
        cid = "loop.seamless"
        wraps_fired = sum(t.events.count("wrap") for t in r.trace_a)
        if not r.frames_usable:
            # The telemetry half alone: a layer whose offset never crosses its span has
            # not looped at all, which the criterion CAN answer without the image.
            #
            # READ IT OUT OF THE TRACE, not out of `shifts`. `run` hands this method an
            # empty `shifts` whenever the frames are unusable, so a count taken from
            # there is 0 by construction - a number in the evidence that cannot be
            # anything else, which is this repository's most-repeated defect.
            walk, holed = self._walk(r)
            looped = 0
            for row in self._layers(r.trace_a[0].state):
                span = num(row, "span")
                moved = self._travelled(walk, row.get("id"))
                if span and span > 0 and moved is not None and abs(moved) >= span:
                    looped += 1
            return self.ok(cid, wraps_fired > 0,
                           f"{r.why_frames_unusable()}; scored on telemetry alone: "
                           f"{wraps_fired} `wrap` events, and {looped} layers whose "
                           f"offset passed their own span"
                           + (f"; layer(s) {holed} vanish from the trace and return, so "
                              f"no displacement can be read across the gap" if holed
                              else ""))
        reliable, skipped = self._reliable(shifts)
        width = r.frames_a[0].width
        bad, checked, blind, notes = 0, 0, 0, []
        for lid, info in reliable.items():
            straight = [x for x in info["pairs"] if not x["wrapped"]]
            wrapped = [x for x in info["pairs"] if x["wrapped"]]
            if len(straight) < 2 or not wrapped:
                continue
            k = statistics.median(x["shift"] / x["d_offset"] for x in straight)
            for x in wrapped:
                predicted = k * x["d_offset"]
                # THE ESTIMATOR'S ONE KNOWN FAILURE, EXCLUDED BY NAME. A band holding a
                # large stationary object offers a competing minimum at zero, and when
                # that minimum wins the answer is not "the band did not move" - it is
                # "this pair could not be read". Measured over 88 frame pairs of the
                # reference and its 1.5x variant: 3 misses, all of them exactly this
                # shape, all on the band holding the car. Counted and reported, because
                # every reason not to count a failure is a channel a bug can widen.
                #
                # What it costs: a seam whose jump happens to cancel that pair's scroll
                # exactly reads as unreadable rather than as a jump. Narrow, and the
                # other crossings of the same layer still carry it.
                if abs(x["shift"]) <= 1 and abs(predicted) > max(4.0, width * 0.01):
                    blind += 1
                    continue
                checked += 1
                slack = max(self.WRAP_PIXEL_FLOOR,
                            width * self.WRAP_FLOOR_SHARE,
                            abs(predicted) * self.WRAP_TOLERANCE)
                if abs(x["shift"] - predicted) > slack:
                    bad += 1
                    if len(notes) < 3:
                        notes.append(f"layer {lid} pair {x['pair']}: drew "
                                     f"{x['shift']}px where {predicted:.1f}px "
                                     f"continues the scroll")
        if not checked:
            return self.not_established(
                cid, f"no layer both wrapped between two captured frames and could be "
                     f"read reliably enough for the crossing to mean anything "
                     f"({wraps_fired} `wrap` events fired in the trace; {blind} "
                     f"crossings landed on a band that could not be read at that pair; "
                     f"{skipped})")
        self.image_ran(cid)
        return self.ok(cid, bad == 0 and wraps_fired > 0,
                       f"{checked} wrap crossings measured in the frames, {bad} of them "
                       f"a visible jump, {blind} unreadable; {wraps_fired} `wrap` "
                       f"events in the trace"
                       + (f"; {notes}" if notes else "")
                       + (f"; not read: {skipped}" if skipped else ""))

    def _wheels(self, r: SceneRun) -> Criterion:
        cid = "wheels.match_speed"
        samples = []
        speeds = []
        for a, b in zip(r.trace_a, r.trace_a[1:], strict=False):
            xa, xb = num(a.state, "car", "x"), num(b.state, "car", "x")
            wa = (a.state.get("car") or {}).get("wheels") or []
            wb = (b.state.get("car") or {}).get("wheels") or []
            sp = num(b.state, "car", "speed")
            if xa is None or xb is None or not wa or not wb or sp is None:
                continue
            radius = num(wa[0], "radius")
            aa, ab = num(wa[0], "angle"), num(wb[0], "angle")
            if radius is None or radius <= 0 or aa is None or ab is None:
                continue
            dx = xb - xa
            if abs(dx) < 1e-9:
                continue
            samples.append(abs(ab - aa) * radius / abs(dx))
            speeds.append(abs(sp))
        if len(samples) < 30:
            return self.not_established(
                cid, f"only {len(samples)} ticks reported a wheel radius, a wheel angle "
                     f"and a change in the car's position together")
        ratio = statistics.median(samples)
        rolls = 0.75 <= ratio <= 1.34
        lo, hi = min(speeds), max(speeds)
        swing = (hi - lo) / hi if hi > 0 else 0.0
        if swing < self.SPEED_VARIATION_FLOOR:
            return self.ok(cid, rolls,
                           f"arc/travel ratio {ratio:.3f} over {len(samples)} ticks; the "
                           f"car's speed varies by only {swing:.1%}, so a wheel spun at "
                           f"the mean rate is indistinguishable from a rolling one and "
                           f"only the ratio is asked")
        # BOTH HALVES ARE GUARDED, and not out of defensiveness. `speeds` can swing
        # widely and still hold nothing strictly below its own median - [1, 1, 1, 5]
        # swings 80% and its slow half is empty - so an unguarded `median` raises
        # `StatisticsError`, `drive` catches it, and one degenerate speed distribution
        # scores EVERY criterion false with an exception in the evidence. That is a
        # published wrong number rather than a crash, which is the worse of the 2.
        pairs = list(zip(samples, speeds, strict=True))
        mid = statistics.median(speeds)
        fast_half = [s for s, v in pairs if v >= mid]
        slow_half = [s for s, v in pairs if v < mid]
        if not fast_half or not slow_half:
            return self.ok(cid, rolls,
                           f"arc/travel ratio {ratio:.3f} over {len(samples)} ticks; the "
                           f"car's speed swings {swing:.1%} but nothing lies "
                           f"{'above' if not fast_half else 'below'} its median "
                           f"{mid:.3f}, so the fast/slow split could not be made and "
                           f"only the ratio is asked")
        fast, slow = statistics.median(fast_half), statistics.median(slow_half)
        tracks = abs(fast - slow) < 0.12
        return self.ok(cid, rolls and tracks,
                       f"arc/travel ratio {ratio:.3f} over {len(samples)} ticks "
                       f"(rolling: {rolls}); the car's speed swings {swing:.1%} and the "
                       f"ratio is {fast:.3f} on its fast half against {slow:.3f} on its "
                       f"slow half (tracks the ground: {tracks})")

    def _front(self, r: SceneRun) -> Criterion:
        cid = "front.occludes"
        # TELEMETRY ONLY, and deliberately so. The contract gives the car's world
        # position and the foreground things' world positions but no screen box for the
        # car, so there is no way to ask the pixels whether one covered the other. Said
        # here rather than left for a reader to notice from the absence.
        covered = []
        for t in r.trace_a:
            cx = num(t.state, "car", "x")
            if cx is None:
                continue
            for f in t.state.get("front") or []:
                fx, span = num(f, "x"), num(f, "span")
                if fx is None or span is None or span <= 0:
                    continue
                if abs(cx - fx) <= span * 0.5:
                    covered.append((t.tick, f.get("id")))
        enters = sum(t.events.count("front_enter") for t in r.trace_a)
        exits = sum(t.events.count("front_exit") for t in r.trace_a)
        ok = bool(covered) and enters > 0 and exits > 0
        return self.ok(cid, ok,
                       f"{len(covered)} ticks where a foreground thing's span covers the "
                       f"car's position (first {covered[:3]}), {enters} `front_enter` "
                       f"and {exits} `front_exit` events. Telemetry only: the contract "
                       f"reports no screen box for the car, so the pixels cannot be "
                       f"asked whether one covered the other")

    def _light(self, r: SceneRun) -> Criterion:
        cid = "light.monotonic"
        phases = [(t.tick, num(t.state, "light", "phase")) for t in r.trace_a]
        phases = [(k, v) for k, v in phases if v is not None]
        if len(phases) < 10:
            return self.ok(cid, False, "the trace reports no usable `light.phase`")
        vals = [v for _, v in phases]
        drops = sum(1 for a, b in zip(vals, vals[1:], strict=False) if b < a - 1e-6)
        inner = sorted({round(v, 3) for v in vals if 0.001 < v < 0.999})
        reaches = max(vals) >= 0.99 and min(vals) <= 0.01
        telemetry_ok = drops == 0 and len(inner) >= 8 and reaches
        detail = (f"`light.phase` never decreases ({drops} decreases), takes "
                  f"{len(inner)} distinct values strictly between 0 and 1, and spans "
                  f"{min(vals):.3f}..{max(vals):.3f}")
        if not r.frames_usable:
            return self.ok(cid, telemetry_ok,
                           f"{detail}. {r.why_frames_unusable()}, so this is the "
                           f"telemetry half alone")
        window = [k for k, v in phases if 0.0 < v < 1.0]
        if len(window) < 2:
            return self.ok(cid, telemetry_ok, f"{detail}. The ramp occupies no ticks, so "
                                              f"there is nothing for the frames to show")
        lo, hi = min(window), max(window)
        inside = [i for i, k in enumerate(r.frame_ticks) if lo <= k <= hi]
        if len(inside) < 3:
            return self.ok(cid, telemetry_ok,
                           f"{detail}. Only {len(inside)} captured frames land inside "
                           f"ticks {lo}..{hi}, so the image half was not established")
        lum = [mean_luminance(r.frames_a[i]) for i in inside]
        total = lum[-1] - lum[0]
        if abs(total) < 3.0:
            return self.ok(cid, False,
                           f"{detail}, but the frames inside the ramp change mean "
                           f"brightness by only {total:.2f} of 255 - the light the "
                           f"telemetry describes is not in the image")
        steps = [b - a for a, b in zip(lum, lum[1:], strict=False)]
        reversal = max((-s if total > 0 else s) for s in steps) / abs(total)
        intermediate = sum(1 for v in lum[1:-1]
                           if min(lum[0], lum[-1]) + abs(total) * 0.05 < v
                           < max(lum[0], lum[-1]) - abs(total) * 0.05)
        image_ok = intermediate >= 1 and reversal <= 0.20
        self.image_ran(cid)
        return self.ok(cid, telemetry_ok and image_ok,
                       f"{detail}. In the {len(inside)} frames inside ticks {lo}..{hi} "
                       f"mean brightness moves {total:+.1f} of 255 with {intermediate} "
                       f"frames strictly between the ends and a largest reversal of "
                       f"{reversal:.0%} (a cut has neither)")

    def _seed_pair(self, r: SceneRun) -> Criterion:
        return seed_pair_criterion(self, r, extra=None)


# --------------------------------------------------------------------------- #


class GlassScene(Scene):
    """s2_glass - a glass of water that empties, falls, breaks and un-breaks."""

    scene = "s2_glass"
    ticks = 660

    #: "many small irregular pieces" is what the prompt asks for; a number in the prompt
    #: would be a threshold, and thresholds are rubric (`eval/SCENES.md`). This is the
    #: rubric's number, and it rejects the naive implementation named there - a single
    #: mesh swapped for a "broken" texture.
    MIN_PIECES = 8
    #: The glass must lean at least this far before the water's surface is worth asking
    #: about, and the water's own surface must stay within this of world up while it does.
    TILT_FLOOR_DEG = 10.0
    WATER_LEVEL_DEG = 5.0
    #: Mass balance: what is in the glass plus what has left it, against its opening value.
    CONSERVATION = 0.02
    #: Settled fragments come to rest on a common surface: their heights must span no
    #: more than this share of the distance the glass fell, and a settled fragment must
    #: not descend further than this share afterwards.
    REST_BAND = 0.35
    REST_CREEP = 0.02
    #: The reversal must arrive back within this share of the drop height, and the
    #: closing frame within this fraction of pixels of the opening one.
    RETURN_TOLERANCE = 0.05
    RETURN_FRAME_DIFF = 0.15
    #: Refraction, measured against the same rectangle once the glass has left it.
    STRUCTURE_RATIO = 0.35
    DISPLACEMENT_RATIO = 0.60
    BACKDROP_DRIFT = 14.0

    criteria = [
        ("state.shape", "Does the probe report the contracted state shape (phase, "
                        "glass, water, drips, pieces, table) with finite numbers?"),
        ("water.level_under_tilt", "While the glass leans, does the water's surface "
                                   "stay world-horizontal instead of leaning with it?"),
        ("water.volume_conserved", "Does the water only ever go down, and does what "
                                   "left the glass account for what is missing?"),
        ("glass.refracts", "Is what is seen through the glass a DISTORTED version of "
                           "the backdrop rather than a flat tint or an unchanged view?"),
        ("shatter.pieces_rest", "Does the glass break into many fragments that come to "
                                "rest on a common surface instead of sinking through "
                                "it?"),
        ("reversal.inverts", "Does the sequence run backwards to exactly where it "
                             "started - in the telemetry AND in the frames?"),
        ("seed.pair", "Same seed identical AND different seeds different - in the "
                      "fragments' transforms and in the captured frames?"),
    ]
    image_only = frozenset({"glass.refracts"})
    both_halves = frozenset({"reversal.inverts", "seed.pair"})

    # -- helpers --------------------------------------------------------- #

    @staticmethod
    def _pieces(state: dict) -> list[dict]:
        rows = state.get("pieces")
        return [r for r in rows if isinstance(r, dict)] if isinstance(rows, list) else []

    def _drop_span(self, r: SceneRun) -> float:
        """How far the glass fell, in the submission's own world units.

        Every distance tolerance below is a share of this, so nothing here depends on
        the scale a submission chose.
        """
        table = num(r.trace_a[0].state, "table", "y") or 0.0
        ys = [num(t.state, "glass", "y") for t in r.trace_a]
        ys = [y for y in ys if y is not None]
        return max([abs(y - table) for y in ys] + [1e-6])

    def _forward_end(self, r: SceneRun) -> int:
        """The index in `trace_a` where the sequence turns round."""
        for i, t in enumerate(r.trace_a):
            if t.state.get("phase") in ("rewinding", "whole"):
                return i
        return len(r.trace_a)

    # -- the criteria ---------------------------------------------------- #

    def run(self, r: SceneRun) -> list[Criterion]:
        out: list[Criterion] = []
        add = out.append
        if not r.trace_a:
            return self.all_false("the probe produced no trace lines")
        t0 = r.trace_a[0]
        shape_ok = (
            isinstance(t0.state.get("phase"), str)
            and num(t0.state, "glass", "x") is not None
            and num(t0.state, "glass", "y") is not None
            and isinstance(t0.state.get("glass", {}).get("intact"), bool)
            and vec3(t0.state, "glass", "up") is not None
            and all(num(t0.state, "glass", "screen", k) is not None
                    for k in ("x", "y", "w", "h"))
            and num(t0.state, "water", "volume") is not None
            and vec3(t0.state, "water", "up") is not None
            and num(t0.state, "drips", "volume") is not None
            and num(t0.state, "drips", "count") is not None
            and isinstance(t0.state.get("pieces"), list)
            and num(t0.state, "table", "y") is not None)
        add(self.ok("state.shape", shape_ok, f"tick 0 state: {str(t0.state)[:300]}"))
        if not shape_ok:
            return out + self.shape_failed("state shape contract not met")

        add(self._tilt(r))
        add(self._volume(r))
        add(self._refracts(r))
        add(self._pieces_rest(r))
        add(self._reversal(r))
        add(self._seed_pair(r))
        return out

    def _tilt(self, r: SceneRun) -> Criterion:
        cid = "water.level_under_tilt"
        leaning, worst, worst_at = 0, 0.0, None
        max_lean = 0.0
        for t in r.trace_a:
            if t.state.get("phase") != "tilting":
                continue
            gu, wu = vec3(t.state, "glass", "up"), vec3(t.state, "water", "up")
            if gu is None or wu is None:
                continue
            lean = angle_to(gu, WORLD_UP)
            level = angle_to(wu, WORLD_UP)
            if lean is None or level is None:
                continue
            max_lean = max(max_lean, lean)
            if lean < self.TILT_FLOOR_DEG:
                continue
            leaning += 1
            if level > worst:
                worst, worst_at = level, t.tick
        if leaning < 5:
            return self.not_established(
                cid, f"the glass never leaned more than {max_lean:.1f} degrees away from "
                     f"world up during its `tilting` phase, so there was no tilt to hold "
                     f"the water level under")
        ok = worst <= self.WATER_LEVEL_DEG
        return self.ok(cid, ok,
                       f"over {leaning} `tilting` ticks with the glass at least "
                       f"{self.TILT_FLOOR_DEG:g} degrees off world up (reaching "
                       f"{max_lean:.1f}), the water's own surface normal was at worst "
                       f"{worst:.1f} degrees off world up, at tick {worst_at}. Water "
                       f"parented to the cup reads the glass's own angle here")

    def _volume(self, r: SceneRun) -> Criterion:
        cid = "water.volume_conserved"
        end = self._forward_end(r)
        rows = []
        for t in r.trace_a[:end]:
            v, d = num(t.state, "water", "volume"), num(t.state, "drips", "volume")
            c = num(t.state, "drips", "count")
            if v is None or d is None or c is None:
                continue
            rows.append((t.tick, v, d, c))
        if len(rows) < 20:
            return self.ok(cid, False,
                           f"only {len(rows)} forward ticks reported a water volume, a "
                           f"drip volume and a drip count together")
        opening = rows[0][1] + rows[0][2]
        if opening <= 1e-9:
            return self.ok(cid, False, "the glass reports no water at tick 0")
        rises = sum(1 for a, b in zip(rows, rows[1:], strict=False) if b[1] > a[1] + opening * 1e-6)
        drift = max(abs((v + d) - opening) for _, v, d, _ in rows) / opening
        counts = [c for _, _, _, c in rows]
        backwards = sum(1 for a, b in zip(counts, counts[1:], strict=False) if b < a)
        drips = counts[-1] - counts[0]
        emptied = (rows[0][1] - rows[-1][1]) / opening
        ok = (rises == 0 and drift <= self.CONSERVATION and backwards == 0
              and drips >= 1 and emptied > 0.25)
        return self.ok(cid, ok,
                       f"over {len(rows)} forward ticks the volume rose {rises} times "
                       f"and fell by {emptied:.0%}; `water.volume + drips.volume` drifts "
                       f"{drift:.2%} from its opening {opening:g} (allowed "
                       f"{self.CONSERVATION:.0%}); `drips.count` ran {counts[0]} to "
                       f"{counts[-1]} and went backwards {backwards} times. A water mesh "
                       f"merely scaled down leaves the drips at zero")

    def _refracts(self, r: SceneRun) -> Criterion:
        cid = "glass.refracts"
        if not r.frames_usable:
            return self.ok(cid, False, r.why_frames_unusable())
        img0 = r.frames_a[0]
        here = None
        for i, tick in enumerate(r.frame_ticks):
            st = r.state_at(tick)
            if st.get("glass", {}).get("intact") is True:
                # `.get`, not `[...]`: a trace that reports `glass` without `screen` on
                # some later tick would raise here, and `drive` turns that into every
                # criterion false. A missing field is one criterion's problem.
                screen = st.get("glass", {}).get("screen")
                if not isinstance(screen, dict):
                    continue
                box = clip_box(screen, r.frames_a[i], shrink=0.75)
                if box is not None:
                    here = (i, box)
                    break
        if here is None:
            return self.not_established(
                cid, "no captured frame shows the glass intact at a usable screen box")
        i_here, B = here
        # A rectangle of the same size beside the glass, holding backdrop in both frames.
        w = B[2] - B[0]
        gap = max(6, w // 6)
        left = (B[0] - w - gap, B[1], B[0] - gap, B[3])
        right = (B[2] + gap, B[1], B[2] + w + gap, B[3])
        C = next((c for c in (right, left) if c[0] >= 0 and c[2] <= img0.width), None)
        if C is None:
            return self.not_established(
                cid, "the glass fills the frame's width, so there is no strip of bare "
                     "backdrop beside it to measure it against")
        # A frame in which the glass has left that rectangle, so the backdrop behind it
        # is visible - the only way to ask what the glass was DOING to it.
        bare, best = None, -1.0
        for i, tick in enumerate(r.frame_ticks):
            st = r.state_at(tick)
            if st.get("glass", {}).get("intact") is not False:
                continue
            box = clip_box(st.get("glass", {}).get("screen", {}), r.frames_a[i])
            if box is None or overlap_fraction(B, box) > 0.15:
                continue
            d = abs(box[0] - B[0]) + abs(box[1] - B[1])
            if d > best:
                bare, best = i, d
        if bare is None:
            return self.not_established(
                cid, "no captured frame shows the glass gone from the rectangle it "
                     "started in, so what it was covering was never seen")
        Fg, Fb = r.frames_a[i_here], r.frames_a[bare]
        drift = mean_abs([luminance(Fg, x, y) - luminance(Fb, x, y)
                          for y in range(C[1], C[3]) for x in range(C[0], C[2])])
        if drift > self.BACKDROP_DRIFT:
            return self.not_established(
                cid, f"the bare backdrop beside the glass changed by {drift:.1f} of 255 "
                     f"between frames {i_here} and {bare}, so the two frames cannot be "
                     f"differenced - the light or the camera moved")
        gB_now, gB_bare = gradients(Fg, B), gradients(Fb, B)
        gC_now = gradients(Fg, C)
        structure = edge_density(gB_now) / max(1e-9, edge_density(gC_now))
        energy = mean_abs(gB_bare)
        change = mean_abs([a - b for a, b in zip(gB_now, gB_bare, strict=True)]) / max(0.5, energy)
        not_flat = structure >= self.STRUCTURE_RATIO
        displaced = change >= self.DISPLACEMENT_RATIO
        return self.ok(cid, not_flat and displaced,
                       f"frame {i_here} against frame {bare}, where the glass has gone: "
                       f"the region behind the glass keeps {structure:.2f}x the edge "
                       f"density of the bare backdrop beside it (a flat tint keeps ~0, "
                       f"floor {self.STRUCTURE_RATIO}), and the glass changes that "
                       f"region's gradient field by {change:.2f} of its own energy (an "
                       f"alpha overlay changes ~0, floor {self.DISPLACEMENT_RATIO}); "
                       f"the control strip drifted {drift:.1f} of 255")

    def _pieces_rest(self, r: SceneRun) -> Criterion:
        cid = "shatter.pieces_rest"
        end = self._forward_end(r)
        broken = [t for t in r.trace_a[:end] if t.state.get("phase") == "broken"]
        if not broken:
            broken = [t for t in r.trace_a[:end]
                      if t.state.get("glass", {}).get("intact") is False]
        if not broken:
            return self.ok(cid, False,
                           "the glass never reports itself broken, so it never came "
                           "apart at all")
        span = self._drop_span(r)
        final = self._pieces(broken[-1].state)
        settled_at: dict[Any, float] = {}
        creep = 0.0
        for t in broken:
            for p in self._pieces(t.state):
                y = num(p, "y")
                if y is None or p.get("settled") is not True:
                    continue
                pid = p.get("id")
                if pid in settled_at:
                    creep = max(creep, settled_at[pid] - y)
                else:
                    settled_at[pid] = y
        ys = [num(p, "y") for p in final]
        ys = [y for y in ys if y is not None]
        band = (max(ys) - min(ys)) / span if ys else 1.0
        all_settled = bool(final) and all(p.get("settled") is True for p in final)
        enough = len(final) >= self.MIN_PIECES
        rests = creep <= span * self.REST_CREEP
        on_a_plane = band <= self.REST_BAND
        return self.ok(cid, enough and all_settled and rests and on_a_plane,
                       f"{len(final)} fragments at the last broken tick (floor "
                       f"{self.MIN_PIECES}), all settled: {all_settled}; after settling "
                       f"the deepest a fragment sank further was {creep:.3g} of a "
                       f"{span:.3g} drop (allowed {self.REST_CREEP:.0%}); their resting "
                       f"heights span {band:.0%} of the drop (allowed "
                       f"{self.REST_BAND:.0%}). A single swapped mesh fails the count; "
                       f"fragments that sink fail the creep")

    def _reversal(self, r: SceneRun) -> Criterion:
        cid = "reversal.inverts"
        first, last = r.trace_a[0].state, r.trace_a[-1].state
        span = self._drop_span(r)
        opening = (num(first, "water", "volume") or 0.0) + \
                  (num(first, "drips", "volume") or 0.0)
        v0, v1 = num(first, "water", "volume"), num(last, "water", "volume")
        y0, y1 = num(first, "glass", "y"), num(last, "glass", "y")
        u0, u1 = vec3(first, "glass", "up"), vec3(last, "glass", "up")
        tilt = angle_to(u0, u1) if u0 and u1 else None
        events = {e for t in r.trace_a for e in t.events}
        checks = {
            "phase is `whole` at the end": last.get("phase") == "whole",
            "the glass is intact again": last.get("glass", {}).get("intact") is True,
            "no fragments remain": not self._pieces(last),
            "the water is back": v0 is not None and v1 is not None and opening > 0
            and abs(v1 - v0) <= opening * self.RETURN_TOLERANCE,
            "the glass is standing where it stood": y0 is not None and y1 is not None
            and abs(y1 - y0) <= span * self.RETURN_TOLERANCE,
            "it is standing the way up it stood": tilt is not None and tilt <= 5.0,
            "`rewind` and `whole` both fired": {"rewind", "whole"} <= events,
        }
        telemetry_ok = all(checks.values())
        failed = [k for k, v in checks.items() if not v]
        detail = ("telemetry: " + ("every return check holds" if telemetry_ok
                                   else f"failed {failed}"))
        if not r.frames_usable:
            return self.ok(cid, telemetry_ok,
                           f"{detail}. {r.why_frames_unusable()}, so this is the "
                           f"telemetry half alone")
        diff = r.frames_a[-1].differs_from(r.frames_a[0])
        self.image_ran(cid)
        image_ok = diff <= self.RETURN_FRAME_DIFF
        return self.ok(cid, telemetry_ok and image_ok,
                       f"{detail}; the closing frame differs from the opening one in "
                       f"{diff:.1%} of its pixels (allowed "
                       f"{self.RETURN_FRAME_DIFF:.0%}). A reversal that fades out "
                       f"instead of inverting fails both halves")

    def _seed_pair(self, r: SceneRun) -> Criterion:
        def piece_transforms(trace: list[Tick]) -> list[tuple]:
            out = []
            for t in trace:
                for p in self._pieces(t.state):
                    out.append((t.tick, p.get("id"), num(p, "x"), num(p, "y"),
                                num(p, "z"), tuple(vec3(p, "up") or ())))
            return out
        a, b = piece_transforms(r.trace_a), piece_transforms(r.trace_b)
        extra = None
        if a and b:
            extra = ("the fragments' transforms",
                     a != b,
                     f"{len(a)} fragment records on seed A against {len(b)} on seed B, "
                     f"{'differing' if a != b else 'IDENTICAL - a canned pre-fractured '
                                                   'mesh played back'}")
        elif not a:
            extra = ("the fragments' transforms", False,
                     "seed A never reported a fragment, so a canned fracture could not "
                     "be distinguished from a seeded one")
        return seed_pair_criterion(self, r, extra=extra)


# --------------------------------------------------------------------------- #
# The seed pair - ONE criterion, both sides, for both scenes
# --------------------------------------------------------------------------- #


def seed_pair_criterion(scene: Scene, r: SceneRun,
                        extra: tuple[str, bool, str] | None) -> Criterion:
    """Same seed identical AND different seeds different, scored as ONE criterion.

    Deliberately not two. *Different seeds differ* alone is satisfied by anything
    random, including a scene that ignores the seed and reads the wall clock; *same
    seed matches* alone is satisfied by a canned animation. Only the pair identifies a
    seeded procedural scene, so splitting it would hand half a mark to each of the two
    implementations it exists to reject (`eval/SCENES.md`).
    """
    cid = "seed.pair"
    ha = [t.hash for t in r.trace_a]
    parts: list[tuple[str, bool, str]] = []
    parts.append(("the hash chain on the same seed", bool(ha) and ha == r.hashes_a2,
                  f"{len(ha)} ticks against {len(r.hashes_a2)} on a second session"))
    hb = [t.hash for t in r.trace_b]
    parts.append(("the hash chain on a different seed", bool(hb) and hb != ha,
                  "differs" if hb != ha else "IDENTICAL - the seed is not being used"))
    if r.bytes_a and r.bytes_a2:
        parts.append(("the captured frames on the same seed", r.bytes_a == r.bytes_a2,
                      f"{len(r.bytes_a)} frames, "
                      f"{sum(1 for x, y in zip(r.bytes_a, r.bytes_a2, strict=False) if x != y)} of "
                      f"them differing between two films"))
    if r.bytes_a and r.bytes_b:
        parts.append(("the captured frames on a different seed", r.bytes_a != r.bytes_b,
                      "differ" if r.bytes_a != r.bytes_b
                      else "BYTE-IDENTICAL across two seeds"))
    # Both film comparisons, or neither: one of them alone is the half of the pair the
    # other half exists to reject, and reporting that as "measured twice" would name a
    # comparison this run did not make.
    if r.bytes_a and r.bytes_a2 and r.bytes_b:
        scene.image_ran(cid)
    if extra is not None:
        parts.append(extra)
    ok = all(p[1] for p in parts)
    return scene.ok(cid, ok, "; ".join(f"{name}: {detail}" for name, _, detail in parts))


SCENES: dict[str, type[Scene]] = {"s1_parallax": ParallaxScene, "s2_glass": GlassScene}


# --------------------------------------------------------------------------- #
# Driving one submission
# --------------------------------------------------------------------------- #


def drive(scene: Scene, repo: Path, seed_a: int = 7, seed_b: int = 99,
          env: dict[str, str] | None = None) -> dict[str, Any]:
    """Run one scene's criteria against one submission. Never raises.

    FAIL CLOSED, exactly as `probe.drive` does: every way of failing to read the
    submission scores the criteria FALSE with the reason recorded, except a project-lock
    conflict, which is a fact about the engine rather than about the submission and comes
    back unscored (FINDINGS #25).
    """
    t0 = time.monotonic()
    run = SceneRun()
    # PER CALL, not per instance. `Scene` is an ordinary object and nothing stops one
    # being driven twice; a set carried over from the previous run would report an image
    # half that this run's frames never supported, which is the exact claim
    # `measured_twice` exists to make honestly.
    scene.image_measured.clear()
    try:
        run = gather(scene, repo, seed_a, seed_b, env)
        crits = scene.run(run)
    except ProbeError as e:
        crits = unusable_criteria(scene.criteria, e, "the scene sessions",
                                  scene.diagnostic_only)
    # noqa BLE001, deliberately blind and FAIL-CLOSED: a scene's criteria are arbitrary
    # Python, so the exception set is open by construction. A bug here costs a trial,
    # never a false pass (AGENTS.md rule 7).
    except Exception as e:  # noqa: BLE001
        crits = scene.all_false(f"the scene probe raised {type(e).__name__}: {e}")

    for c in crits:
        if c.id in scene.diagnostic_only:
            c.scored = False
    scored = [c for c in crits if c.scored]
    passed = sum(1 for c in scored if c.passed)
    return {
        "tier": "scene_probe",
        "scene": scene.scene,
        "seeds": [seed_a, seed_b],
        "ticks": scene.ticks,
        "frames_captured": len(run.frames_a),
        "frames_usable": run.frames_usable,
        "film_notes": run.film_notes,
        "events_fired": sorted({e for t in run.trace_a for e in t.events}),
        "passed": passed,
        "total": len(scored),
        "usable": bool(scored),
        "score": passed / len(scored) if scored else 0.0,
        # WHICH CRITERIA WERE ACTUALLY MEASURED TWICE, not which ones the design says
        # have two halves. An image half that did not run is the difference between the
        # two, and it is the thing a reader must be able to see - so it is RECORDED by
        # the criterion that made the measurement, never inferred from its prose.
        "measured_twice": sorted(
            cid for cid in scene.both_halves
            if cid in scene.image_measured
            and next((c.scored for c in crits if c.id == cid), False)),
        "image_only": sorted(scene.image_only),
        "unscored": {c.id: c.evidence[:200] for c in crits if not c.scored},
        "wall_s": round(time.monotonic() - t0, 1),
        "criteria": [c.to_dict() for c in crits],
    }


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("scene", choices=sorted(SCENES))
    ap.add_argument("repo", type=Path)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--other-seed", type=int, default=99)
    ap.add_argument("--json", type=Path, default=None)
    args = ap.parse_args(argv)

    if shutil.which("just") is None:
        print("`just` is not on PATH; a submission cannot be driven", file=sys.stderr)
        return 2
    out = drive(SCENES[args.scene](), args.repo, args.seed, args.other_seed)
    w = max(len(c["id"]) for c in out["criteria"])
    for c in out["criteria"]:
        mark = "PASS" if c["passed"] else "FAIL"
        if not c["scored"]:
            mark += "/unscored"
        print(f"{c['id']:<{w}}  {mark:<14}  {c['evidence'][:150]}")
    print(f"\n{out['scene']}: {out['passed']}/{out['total']} "
          f"({out['score']:.3f}) in {out['wall_s']}s; "
          f"measured twice: {out['measured_twice'] or 'none'}")
    if args.json:
        args.json.write_text(json.dumps(out, indent=2))
    return 0 if out["usable"] else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
