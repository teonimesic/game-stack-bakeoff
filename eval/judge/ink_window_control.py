#!/usr/bin/env python3
"""Can `render.nonempty` fail - and can it still pass everything it should?

`render.nonempty` is TIER 1, and tier 1 is a GATE rather than a weighted term
(`RUBRIC.md`). A false negative here does not cost a fraction of a score; it stops a
correct submission being scored at all. The criterion is a FLOOR with no ceiling: it was
`0.001-0.85` for every task from this repository's first commit, `tasks/163` took the
ceiling off scenes, and `tasks/168` took it off entirely.

**The derivation is a measurement in this file, not a paragraph elsewhere**, because it
is what the removal rests on. `png.Image.ink_coverage` counts pixels differing from one
reference colour, and since `tasks/178` `analyse_frames` takes that colour from EACH
FRAME'S OWN mode. So `mean_ink` is the fraction of a frame that is not its background,
and it runs backwards from what a ceiling wants: a solid flood, the "the render broke
and filled the screen" defect, measures 0.0 in any colour and lands on the FLOOR, while
what reads near 1.0 is the absence of a modal region, which is a gradient.
`MECHANISM_ROWS` states both before anything runs.

**The reference itself is pinned here too**, because the fixed one was fail-open.
Frame 0's mode applied to all 12 frames saturates at exactly 1.00000 the moment a
submission changes its clear colour, so `COLOUR_DRIFT` - 11 uniform frames carrying a
single 2x2 speck, after a frame 0 of another colour - read 0.91665 and PASSED, with
`flat_frames` unable to see it because only frame 0 was flat. Per frame it reads
0.00001 and fails. The mutant that restores the fixed reference turns that row red.

Three halves, because a gate needs all three:

  FIXTURES   real PNGs through the real reader and `analyse_frames`, so the ink numbers
             are measured rather than asserted. Each fixture's expected coverage is
             stated in `FIXTURES` before anything runs - the one known-good row rule 12
             asks for, since a census that returns one value for every subject is
             reporting the instrument.
  MUTANTS    remove a mechanism the criterion names and require a named expectation to
             go red - including RESTORING the 0.85 ceiling, which is literally the
             pre-change code. A bound that cannot fail is worse than none: it looks
             like a pass.
  VARIANTS   correct inputs the implementation does not resemble, where the criterion
             must still PASS - a scene that fills the frame, a night game over a
             gradient, the starter's own placeholder marker. Every false negative
             adjudicated in this project has been of that kind (rule 15), and the two
             this file exists for were too.

    python3 judge/ink_window_control.py
    python3 judge/ink_window_control.py --runs-root <main checkout>/eval/runs

`--runs-root` adds the corpus arm, which is also the PRODUCER for every ink figure the
documents quote: the per-class distribution of `mean_ink`, every `render.nonempty`
firing with the bound it hit, and the re-grade of each firing under the floor - the gate
verdict before and after included. `eval/runs` is gitignored, so a worktree's copy is
empty and the arm prints `NOT ASKED` rather than `0 firings`; the two are different
claims.

`--reference-shift` adds a second, slower corpus pass that RE-READS the stored PNGs and
reports every set whose `mean_ink` moves between the two references, which is the
producer for the table in `eval/RUNS.md`. It is separate because it decodes ~800 frames
in pure Python and takes about 80 s, and because it proves its extraction first: the
frame-0 arm must reproduce each stored record's own `mean_ink` to the digit before any
per-frame figure it prints means anything (rule 12).
"""
from __future__ import annotations

import argparse
import collections
import contextlib
import json
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import evaluate  # noqa: E402
import png  # noqa: E402
import static  # noqa: E402

FAILS: list[str] = []
CHECKS = 0
BG = (56, 56, 48)          # the background the first stored scene actually reported
W, H = 640, 400            # the geometry every stored grading was captured at

#: The bound `tasks/168` removed. Used ONLY to explain the historical firings in the
#: corpus report and by the mutant that restores it - never by a verdict. A record
#: graded before 2026-08-27 was decided against it, so a report that printed only
#: today's floor would call those firings unexplained.
RETIRED_GAME_CEILING = 0.85


def expect(name: str, cond: bool, detail: str = "") -> None:
    """Record one expectation and print it. `detail` is what a reader needs to adjudicate.

    `CHECKS` is what `phases()` reads to prove a phase ran at all, so every row must go
    through here rather than being asserted inline.
    """
    global CHECKS
    CHECKS += 1
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f"  -- {detail}" if detail else ""))
    if not cond:
        FAILS.append(name)


@contextlib.contextmanager
def patched(obj: Any, name: str, value: Any):
    """Replace one module attribute for the duration of the block, then restore it.

    Restoration is in a `finally`, because a mutant that raises would otherwise leave the
    module broken for every row after it and turn one red into a cascade.
    """
    old = getattr(obj, name)
    setattr(obj, name, value)
    try:
        yield
    finally:
        setattr(obj, name, old)


# --------------------------------------------------------------------------- #
# fixtures - real pixels, expected coverage stated before anything runs
# --------------------------------------------------------------------------- #

def _flat() -> bytearray:
    """A frame of nothing but the background colour: ink coverage 0.0 by construction."""
    return bytearray(bytes(BG) * (W * H))


def _rect(px: bytearray, w: int, h: int) -> bytearray:
    """A filled block in the top-left, in a colour far from the background."""
    for y in range(h):
        for x in range(w):
            i = (y * W + x) * 3
            px[i:i + 3] = b"\xf0\xe0\xc0"
    return px


def blank() -> bytes:
    """What a submission that rendered nothing produces. It must fail in BOTH classes."""
    return bytes(_flat())


def whisper() -> bytes:
    """An 8x8 mark: 0.00025 of a 640x400 frame, and the only fixture BELOW the floor.

    The floor's subject. `blank` and `flood` are below it too, but they are also
    entirely flat, so they fail on BOTH halves and cannot tell which one acted - a
    mutant that deletes the floor leaves them red for the other reason, which is a
    control that passes for the wrong reason (#37).
    """
    return bytes(_rect(_flat(), 8, 8))


def placeholder() -> bytes:
    """The starter's own placeholder marker: 0.0015 of a 640x400 frame."""
    return bytes(_rect(_flat(), 24, 16))


def sparse() -> bytes:
    """A subject against a background - what a game frame looks like."""
    return bytes(_rect(_flat(), 80, 64))


def filled() -> bytes:
    """A frame with no flat region at all: a gradient, which reads near 1.0.

    What a scene is contracted to draw, and also what a night game's sky looks like -
    `wg-g4c` `g4_platformer__godot__t1` reads 0.67869 with its subject drawn on top.
    """
    px = bytearray(W * H * 3)
    for y in range(H):
        for x in range(W):
            i = (y * W + x) * 3
            px[i] = (x * 255) // W
            px[i + 1] = (y * 255) // H
            px[i + 2] = 128
    return bytes(px)


def flood() -> bytes:
    """THE DEFECT A CEILING WOULD NAME: every pixel one colour that is not the clear
    colour, i.e. the render broke and filled the screen.

    It measures 0.0, not 1.0, because a uniform frame is entirely its own modal colour.
    So this fails on the FLOOR, and removing the ceiling opened no hole for it.
    `BLANK_RENDERS` below asks the version that used to be harder, where the frames are
    uniform in DIFFERENT colours.
    """
    return bytes(bytes((255, 0, 255)) * (W * H))


def _uniform(rgb: tuple[int, int, int]) -> bytes:
    return bytes(bytes(rgb) * (W * H))


BLACK, WHITE = (0, 0, 0), (255, 255, 255)


def colour_drift(i: int) -> bytes:
    """Frame `i` of `COLOUR_DRIFT`: uniform black at 0, else white with a 2x2 speck.

    The speck is what defeats the all-flat half - a frame with 4 non-background pixels
    is not flat - so the whole verdict falls to the floor, and the floor is only able to
    see it when the reference is the frame's own mode.
    """
    if i == 0:
        return _uniform(BLACK)
    px = bytearray(_uniform(WHITE))
    for y in range(2):
        for x in range(2):
            j = (y * W + x) * 3
            px[j:j + 3] = bytes(BLACK)
    return bytes(px)

#: A RENDER THAT DREW NOTHING, in the 4 ways 12 uniform frames can be arranged, with
#: `(name, per-frame pixels, mean_ink stated in advance, mean_ink under the retired
#: frame-0 reference)`.
#:
#: RE-DERIVED FOR THE PER-FRAME REFERENCE, not re-recorded. Every row has drawn nothing
#: and every row now reads **0.0**, because a uniform frame is entirely its own mode
#: whatever that colour is - so the arrangement, which used to decide the number, no
#: longer changes it at all. The fourth column is what the same 4 sets read against
#: frame 0's mode, and it is the reason the reference moved: the same blank render
#: landed anywhere from 0.0 to 0.91667, and the retired 0.001-0.85 window admitted 2 of
#: the 3 non-zero arrangements. Every row must FAIL today, and `test_the_two_halves`
#: establishes that each half of the criterion refuses all 4 on its own.
BLANK_RENDERS: list[tuple[str, Any, float, float]] = [
    ("all one colour", lambda i: _uniform(BLACK), 0.0, 0.0),
    ("frame 0, then 11 of another", lambda i: _uniform(BLACK if i == 0 else WHITE),
     0.0, 0.91667),
    ("alternating 2 colours", lambda i: _uniform(BLACK if i % 2 == 0 else WHITE),
     0.0, 0.5),
    ("6 of one, then 6 of another", lambda i: _uniform(BLACK if i < 6 else WHITE),
     0.0, 0.5),
]

#: THE ROW THE REFERENCE TURNS ON, and it is a VARIANT rather than a mutant: correct-
#: looking input the fixed reference mishandled. 12 frames of which frame 0 is uniform
#: black and the other 11 are uniform white carrying a single 2x2 speck.
#:
#: Nothing was drawn worth the name - 4 pixels of 256000 - and both halves of the
#: pre-`tasks/178` criterion admitted it: `flat_frames` counts 1 of 12, because the 11
#: speck-bearing frames are not flat, and against frame 0's mode those 11 frames read
#: 0.99998 each for a `mean_ink` of 0.91665, well clear of the floor. Measured on the
#: pre-change code before it was changed. Against their own modes the same 11 frames
#: read 0.00002 and the set reads 0.00001, which fails.
COLOUR_DRIFT_INK = 0.00001
COLOUR_DRIFT_UNDER_FRAME0 = 0.91665


#: `(name, pixels, low, high)` - the coverage each fixture must measure at, STATED
#: HERE rather than read off the run. A fixture whose measured ink drifts out of its
#: stated band means the reader moved, and every row below would then be asking its
#: question of a different picture.
FIXTURES: list[tuple[str, Any, float, float]] = [
    ("blank", blank, 0.0, 0.0),
    ("flood", flood, 0.0, 0.0),
    ("whisper", whisper, 0.0002, 0.0003),
    ("placeholder", placeholder, 0.001, 0.005),
    ("sparse", sparse, 0.015, 0.030),
    ("filled", filled, 0.950, 1.000),
]

#: The derivation, as two rows that are checked rather than asserted: what the measure
#: does to a frame that is entirely full, and what it does to a frame with no modal
#: region. `(fixture, at most / at least, bound, what it establishes)`.
#:
#: These are the sentences `static.INK_FLOOR`'s comment, `judge/RUBRIC.md` and
#: `DECISIONS.md` all rest on. Written out here so that a change to `ink_coverage`
#: turns the derivation red instead of leaving three documents confidently wrong.
MECHANISM_ROWS = [
    ("flood", "at most", 0.001,
     "a frame that is entirely one colour reads 0.0, whatever that colour is - so 'the "
     "render filled the screen' hits the FLOOR, never a ceiling"),
    ("filled", "at least", 0.950,
     "a frame with no modal region reads near 1.0 whatever is drawn on it - so a high "
     "reading is a property of the palette, not of how much was drawn"),
]


def measure(make: Any, tmp: Path) -> dict[str, Any]:
    """Two identical frames through `png.write_rgb` -> `png.read` -> `analyse_frames`."""
    d = tmp / "frames"
    shutil.rmtree(d, ignore_errors=True)
    d.mkdir(parents=True, exist_ok=True)
    pixels = make()
    for i in range(2):
        png.write_rgb(d / f"frame_{i:04d}.png", W, H, pixels)
    return static.analyse_frames(sorted(d.glob("*.png")))


def measure_sequence(per_frame: Any, tmp: Path, n: int = 12) -> dict[str, Any]:
    """`n` frames whose pixels come from `per_frame(i)`, through the real reader.

    Separate from `measure` because the arrangement across frames is the whole subject
    of `BLANK_RENDERS`: a set of identical frames cannot express it, and `analyse_frames`
    takes its reference colour from frame 0.
    """
    d = tmp / "seq"
    shutil.rmtree(d, ignore_errors=True)
    d.mkdir(parents=True, exist_ok=True)
    for i in range(n):
        png.write_rgb(d / f"frame_{i:04d}.png", W, H, per_frame(i))
    return static.analyse_frames(sorted(d.glob("*.png")))


def test_a_blank_render_fails_however_its_colours_are_arranged(tmp: Path) -> None:
    """12 frames, each one colour, in the 4 ways they can be arranged. All must FAIL.

    Each row also measures what the SAME set reads under the retired frame-0 reference,
    which is what the reference decision rests on: the arrangement moved that number
    from 0.0 to 0.91667 while the render was equally blank in all 4. The last row asks
    the positive form - that the 4 no longer differ at all.
    """
    print("\n[a render that drew nothing, in the 4 ways 12 uniform frames arrange]")
    measured = []
    for name, per_frame, want_ink, want_under_frame0 in BLANK_RENDERS:
        info = measure_sequence(per_frame, tmp)
        got = info["mean_ink"]
        n = info["count"]
        measured.append(got)
        passed, ev = static.nonempty_verdict(info, n)
        then = round(sum(_frame0_inks(per_frame, tmp)) / n, 5)
        expect(f"{name}: mean_ink {want_ink}, and render.nonempty FAILS",
               got == want_ink and passed is False and info["flat_frames"] == n,
               f"mean_ink={got} flat_frames={info['flat_frames']}/{n} -- {ev[:60]}")
        expect(f"{name}: and under the retired frame-0 reference it read "
               f"{want_under_frame0}",
               then == want_under_frame0,
               f"measured {then}; that window "
               f"{'caught' if not (static.INK_FLOOR <= then <= RETIRED_GAME_CEILING) else 'ADMITTED'}"
               f" it")
    # THE POSITIVE FORM. Four rows each reading 0.0 could also be four rows of a reader
    # that stopped discriminating, so this is stated as *the arrangement no longer
    # moves the number* rather than as a fourth repetition of 0.0 - and the fixture
    # phase separately proves the reader still tells 5 pictures apart.
    expect("the arrangement no longer moves the number at all",
           len(set(measured)) == 1, f"{measured}")


def _frame0_inks(per_frame: Any, tmp: Path, n: int = 12) -> list[float]:
    """The same `n` frames read against FRAME 0's mode - the retired reference.

    Measured rather than remembered, because `BLANK_RENDERS`' fourth column is the
    evidence the reference moved and a column nobody recomputes is a column that was
    copied.
    """
    d = tmp / "ref0"
    shutil.rmtree(d, ignore_errors=True)
    d.mkdir(parents=True, exist_ok=True)
    for i in range(n):
        png.write_rgb(d / f"frame_{i:04d}.png", W, H, per_frame(i))
    imgs = [png.read(p) for p in sorted(d.glob("*.png"))]
    bg0 = imgs[0].dominant_background()
    return [im.ink_coverage(bg0) for im in imgs]


def test_a_colour_drift_that_drew_nothing_fails(tmp: Path) -> None:
    """`COLOUR_DRIFT`, the variant the fixed reference admitted. It must FAIL now.

    Both halves of the pre-`tasks/178` criterion passed this set. It is the one row a
    mutant restoring the frame-0 reference turns red, so it is also what keeps that
    mutant honest.
    """
    print("\n[a colour drift carrying a 2x2 speck: 4 pixels of 256000 were drawn]")
    info = measure_sequence(colour_drift, tmp)
    n = info["count"]
    passed, ev = static.nonempty_verdict(info, n)
    then = round(sum(_frame0_inks(colour_drift, tmp)) / n, 5)
    expect(f"mean_ink {COLOUR_DRIFT_INK}, flat_frames 1 of {n}, and it FAILS",
           info["mean_ink"] == COLOUR_DRIFT_INK and info["flat_frames"] == 1
           and passed is False and then == COLOUR_DRIFT_UNDER_FRAME0,
           f"mean_ink={info['mean_ink']} flat_frames={info['flat_frames']}/{n} "
           f"under frame 0 it read {then} (stated {COLOUR_DRIFT_UNDER_FRAME0}, which "
           f"PASSED) -- {ev[:60]}")


def test_the_two_halves(inks: dict[str, dict[str, Any]], tmp: Path) -> None:
    """Which half of `render.nonempty` refuses a blank render, now that both do?

    `tasks/168` made the all-flat half INDEPENDENT of the floor, because under the
    frame-0 reference a blank render could read 0.91667. `tasks/178` makes it
    REDUNDANT: `png.Image.is_flat` is `ink_coverage(own mode) == 0.0`, which is exactly
    `mean_ink`'s per-frame term, so all-flat implies `mean_ink` 0.0 implies below the
    floor. The redundancy is kept as the fail-closed direction, and it is asserted here
    rather than promised in a comment, because the two live at different addresses
    (rule 12).
    """
    print("\n[the two halves: each refuses every blank render on its own]")
    disagreed = []
    for name, per_frame, _ink, _then in BLANK_RENDERS:
        info = measure_sequence(per_frame, tmp)
        if (info["flat_frames"] == info["count"]) != (info["mean_ink"] == 0.0):
            disagreed.append(name)
    for name, _make, _lo, _hi in FIXTURES:
        if (inks[name]["flat_frames"] == inks[name]["count"]) != \
                (inks[name]["mean_ink"] == 0.0):
            disagreed.append(name)
    expect("png.Image.is_flat agrees with mean_ink's per-frame term on every fixture "
           "and every arrangement", disagreed == [], str(disagreed))

    with patched(static, "INK_FLOOR", 0.0):
        survived = [name for name, per_frame, _i, _t in BLANK_RENDERS
                    if static.nonempty_verdict(
                        (info := measure_sequence(per_frame, tmp)), info["count"])[0]]
    expect("with no floor at all, the all-flat half still refuses all 4",
           survived == [], str(survived))

    with patched(png.Image, "is_flat", lambda self, tolerance=8: False):
        survived = [name for name, per_frame, _i, _t in BLANK_RENDERS
                    if static.nonempty_verdict(
                        (info := measure_sequence(per_frame, tmp)), info["count"])[0]]
    expect("with no frame ever flat, the floor still refuses all 4 - which is what "
           "makes the all-flat half redundant rather than independent",
           survived == [], str(survived))


def test_fixtures_measure_what_they_claim(inks: dict[str, dict[str, Any]]) -> None:
    """Does the reader still see the picture each fixture was written to be?

    Every row below asks its question of these numbers, so a fixture that drifted out of
    its stated band would leave the whole file measuring something else while staying
    green. The last row refuses a set that collapsed to one value (rule 12).
    """
    print("\n[the fixtures measure what they are stated to measure]")
    for name, _make, lo, hi in FIXTURES:
        got = inks[name]["mean_ink"]
        expect(f"{name} measures {lo}-{hi}", lo <= got <= hi, f"mean_ink={got}")
    # `blank` and `flood` coincide at 0.0 BY CONSTRUCTION and that coincidence is the
    # derivation, so the row asks for one collision and no more - a set that collapsed
    # further would mean the reader stopped discriminating (rule 12).
    seen = {round(inks[n]["mean_ink"], 5) for n, *_ in FIXTURES}
    expect("the fixtures separate, except blank and flood which coincide at 0.0",
           len(seen) == len(FIXTURES) - 1
           and inks["blank"]["mean_ink"] == inks["flood"]["mean_ink"] == 0.0,
           f"{len(seen)} distinct of {len(FIXTURES)}: {sorted(seen)}")


# --------------------------------------------------------------------------- #
# the criterion itself, both directions
# --------------------------------------------------------------------------- #

#: `(fixture, must pass)`. One table, no task class: since `tasks/168` the bound is a
#: property of the four starters and is the same number for every class.
#:
#: The two rows that carry the change are `flood` and `filled`. `flood` is the defect a
#: ceiling would have been for and it FAILS, on the floor. `filled` is a frame with no
#: modal region - a scene filling the frame, or a night game over a gradient sky - and
#: it PASSES, which is what the 0.85 ceiling refused twice.
CRITERION_ROWS = [
    ("blank", False),          # nothing drawn
    ("flood", False),          # VARIANT: the screen is full, and the floor catches it
    ("whisper", False),        # below the floor, and the only row the floor decides
    ("placeholder", True),     # the starter's own marker
    ("sparse", True),          # a subject against a background
    ("filled", True),          # VARIANT: no modal region (tasks/163, tasks/168)
]


def test_the_criterion(inks: dict[str, dict[str, Any]]) -> None:
    """`CRITERION_ROWS` both ways, then the evidence, then the mechanism it rests on."""
    print("\n[the criterion, both directions]")
    for fixture, want in CRITERION_ROWS:
        ok, ev = static.nonempty_verdict(inks[fixture], 2)
        expect(f"{fixture}: {'PASS' if want else 'FAIL'}", ok is want, ev[:150])

    print("\n[the evidence names the floor and says there is no ceiling]")
    _ok, ev = static.nonempty_verdict(inks["sparse"], 2)
    expect("the stored evidence names the floor, not a window",
           f"floor {static.INK_FLOOR}, no ceiling" in ev
           and static.INK_FLOOR_WHY in ev, ev[:160])

    # THE DERIVATION, MEASURED. Without these two rows the removal of the ceiling is an
    # argument in a comment; with them, a change to `ink_coverage` that made a flood
    # read high turns this file red rather than leaving three documents wrong.
    print("\n[the mechanism the removal rests on]")
    for fixture, direction, bound, why in MECHANISM_ROWS:
        got = inks[fixture]["mean_ink"]
        ok = got <= bound if direction == "at most" else got >= bound
        expect(f"{fixture} measures {direction} {bound}", ok, f"{got} - {why}")


def test_an_unplaceable_class_is_refused() -> None:
    """Tier 1 refuses a task class it does not grade, before spending a toolchain.

    No tier-1 BOUND differs by class any more, which is exactly why this row matters:
    nothing downstream would read differently if the class were wrong, so the only
    place it can be caught is the door. The class still picks the capture length and
    the audio criterion set (`judge/evaluate.py`), and
    `eval/tools/scene_runner_control.py` pins that the runner hands all three over.
    """
    print("\n[an unknown class is refused, not defaulted]")
    try:
        static.assert_task_class("film")
        expect("assert_task_class refuses a class tier 1 does not grade", False,
               "it returned")
    except ValueError as e:
        expect("assert_task_class refuses a class tier 1 does not grade", True,
               str(e)[:90])
    # COUNT THE COMMANDS, do not merely catch the exception. `except ValueError` accepts
    # one raised from anywhere in `collect`, including after `just check` has run - so
    # the row would report "refused before spending" about a refusal that spent one.
    ok, ran_commands = refuses_before_spending("film")
    expect("collect refuses before spending a toolchain", ok,
           f"{len(ran_commands)} command(s) ran first: {ran_commands}")

    # THE ADDRESS IS AN INPUT TO THE CHECK (rule 12). `static.TASK_CLASSES` and the
    # classes `judge/aspects.py` recognises are the same fact in two files; asserted
    # equal here rather than promised equal in a comment.
    import aspects
    from_aspects = ({a.task_class for a in aspects.ASPECTS.values()}
                    | set(aspects.INSTRUMENTS.values()))
    expect("static.TASK_CLASSES is the set judge/aspects.py recognises",
           set(static.TASK_CLASSES) == from_aspects,
           f"{sorted(static.TASK_CLASSES)} vs {sorted(from_aspects)}")


# --------------------------------------------------------------------------- #
# collect() end to end, with the toolchain stubbed
# --------------------------------------------------------------------------- #

@contextlib.contextmanager
def stubbed_toolchain(mean_ink: float, ran_commands: list[str],
                      flat_frames: int = 0):
    """Everything `collect` would spawn, replaced - and every command it ran, recorded.

    `ran_commands` is what separates *refused before spending a toolchain* from *refused
    after it*: an exception alone cannot tell those apart, and the stronger one is the
    claim worth making.

    NOT NAMED `spent`. `tools/tokenvalue.py`'s `_VALUE` reads that word as a token
    valuation, so the name alone made this module a money PRODUCER that was not in
    `PRODUCERS` and turned `tokenvalue --selftest` red. The gate is right and the name
    was wrong: what is spent here is a toolchain, and #159 reserves the vocabulary.
    """
    cmd = static.Cmd(name="x", argv=["x"], code=0, seconds=0.0,
                     out="12 passed, 12 total", err="")

    def record(repo, name, argv, *a, **k):
        """Stand in for `static.run`, recording the recipe name instead of spawning it."""
        ran_commands.append(name)
        return cmd

    frame_info = {"count": 12, "errors": [], "mean_ink": mean_ink,
                  "flat_frames": flat_frames,
                  "per_frame_ink": [mean_ink], "mean_frame_delta": 0.5}
    with contextlib.ExitStack() as st:
        st.enter_context(patched(static, "run", record))
        # 12 frame PATHS, never read: `analyse_frames` is stubbed below. `collect`
        # passes `len(frames)` to `nonempty_verdict` as `n_frames`, and the all-flat
        # half is a comparison against that count - returning `[]` here would make it
        # unaskable and the row would pass for the wrong reason.
        st.enter_context(patched(static, "film",
                                 lambda *a, **k: (cmd,
                                                  [Path(f"frame_{i:04d}.png")
                                                   for i in range(12)],
                                                  Path(tempfile.mkdtemp()))))
        st.enter_context(patched(static, "analyse_frames", lambda frames: frame_info))
        st.enter_context(patched(static, "probe_throughput",
                                 lambda *a, **k: {"ok": True}))
        st.enter_context(patched(static, "repo_stats", lambda repo: {}))
        yield


def refuses_before_spending(task_class: str) -> tuple[bool, list[str]]:
    """`(refused with nothing run, the commands it ran)` for one unplaceable class."""
    ran_commands: list[str] = []
    refused = False
    with stubbed_toolchain(0.5, ran_commands):
        try:
            static.collect(Path("/nonexistent"), task_class=task_class)
        except ValueError as e:
            refused = task_class in str(e)
    return refused and not ran_commands, ran_commands


def drive_collect(task_class: str, mean_ink: float,
                  flat_frames: int = 0) -> dict[str, Any]:
    """The real `collect`, offline: every subprocess it makes is replaced.

    Driving the decision function alone leaves a `collect` that never calls it - or
    calls something else - entirely green, so the wiring gets its own rows.
    """
    with stubbed_toolchain(mean_ink, [], flat_frames):
        rec = static.collect(Path("/nonexistent"), task_class=task_class)
    return next(c for c in rec["criteria"] if c["id"] == "render.nonempty")


def test_collect_reaches_the_criterion() -> None:
    """Does `collect` decide `render.nonempty` with `nonempty_verdict`, in both classes?

    The rows above call the decision function directly and stay green against a
    `collect` that inlined its own comparison. These are the only ones that would not,
    and both stored ceiling firings are used as the input - 0.85042 and 0.67869, what
    those two submissions' frames read under today's reference. Their records hold the
    frame-0 readings 0.96561 and 0.88137, which the retired 0.85 refused.
    """
    print("\n[collect decides the criterion with the same floor, in both classes]")
    for klass, ink, label in (("scene", 0.85042, "the stored scene's"),
                              ("game", 0.67869, "the stored platformer's")):
        got = drive_collect(klass, ink)
        expect(f"collect({klass}) passes {label} {ink}", got["passed"] is True,
               got["evidence"][:120])
    expect("collect(game) still fails a blank frame",
           drive_collect("game", 0.0)["passed"] is False)
    expect("collect(scene) still fails a blank frame",
           drive_collect("scene", 0.0)["passed"] is False)
    # THE ALL-FLAT HALF, THROUGH `collect`, on a CONSTRUCTED record: ink 0.91667 with
    # every frame flat is a pair today's `analyse_frames` cannot produce, since all-flat
    # now implies 0.0. It is kept because this row is about `collect` carrying
    # `flat_frames` through to the verdict at all, which no other row would notice, and
    # because the half must keep working for any record that presents that shape.
    flat = drive_collect("game", 0.91667, flat_frames=12)
    expect("collect fails 12 frames that each hold one colour, at ink 0.91667",
           flat["passed"] is False, flat["evidence"][:150])
    # A RECORD THAT NEVER MEASURED IT is not a record of zero flat frames. Same ink,
    # `flat_frames` absent: the floor alone decides and the evidence says so.
    absent = static.nonempty_verdict({"mean_ink": 0.91667, "per_frame_ink": []}, 12)
    expect("a record with no flat_frames is graded on the floor alone, and says so",
           absent[0] is True and "not measured on this record" in absent[1],
           absent[1][:150])


# --------------------------------------------------------------------------- #
# the bound census - every tier-1 criterion answers where its bound came from
# --------------------------------------------------------------------------- #

#: What `static.TIER1_BOUND_POPULATION` must tally to, written out INDEPENDENTLY of it.
#: This is the 8-carry-none / 6-that-transfer / 0-that-do-not that `judge/RUBRIC.md`,
#: `DECISIONS.md` and `eval/judge/AGENTS.md` state in prose, and it is the only place
#: that count is checked rather than repeated.
EXPECTED_TALLY = {"no_bound": 8, "starter": 2, "capture_contract": 1,
                  "audio_signal": 3, "task_class": 0}


def _tally(pops: dict[str, str]) -> tuple[dict[str, int], list[str]]:
    """`(one count per population EXPECTED_TALLY names, populations it does not)`.

    `Counter` omits a population with no members, so a raw comparison would report
    `task_class: 0` as a MISSING KEY and go red for the wrong reason - and would then
    also go red the day the count legitimately returned to 0. The zero is part of the
    expectation, so it is filled in here; anything outside the expected vocabulary is
    returned separately rather than quietly dropped.
    """
    counted = collections.Counter(pops.values())
    return ({k: counted.get(k, 0) for k in EXPECTED_TALLY},
            sorted(set(counted) - set(EXPECTED_TALLY)))


def test_bound_census() -> None:
    """Has every tier-1 criterion answered *which population was your bound calibrated on?*

    The tally is both printed (the documents state it in prose and a prose count with no
    producer goes stale forever) and pinned against `EXPECTED_TALLY`.
    """
    print("\n[TIER1_BOUND_POPULATION: every tier-1 criterion answers the question]")
    problems = static.assert_tier1_bounds_declared()
    expect("the live registry is clean", problems == [], "; ".join(problems)[:200])
    pops = static.TIER1_BOUND_POPULATION
    # THE TALLY IS PRINTED, because the documents state it in prose and a prose count
    # with no producer goes stale forever. This is the producer.
    tally = collections.Counter(pops.values())
    print("       tally: " + ", ".join(f"{k}={tally[k]}"
                                       for k in static.BOUND_POPULATIONS))
    expect("all 14 tier-1 criteria are declared", len(pops) == 14, str(len(pops)))
    expect("the tally partitions every one of them", sum(tally.values()) == len(pops),
           f"{sum(tally.values())} vs {len(pops)}")
    # THE WHOLE TALLY, not just its total. Reclassifying `tests.exist` from `starter`
    # to `no_bound` leaves the total green while the policy moves, and this row is
    # where the documents' breakdown is actually checked. It is written out rather than
    # derived from `pops`: an expectation imported from its subject is not an
    # expectation (AGENTS.md rule 12's corollary).
    #
    # `EXPECTED_TALLY` carries `task_class: 0` explicitly. A tally written as "the
    # populations that have members" would go green the moment a criterion quietly
    # acquired a class-dependence, which is the state `tasks/168` removed.
    got, unexpected = _tally(pops)
    expect(f"the tally is exactly {EXPECTED_TALLY}",
           got == EXPECTED_TALLY and not unexpected,
           f"{got}; populations outside the expectation: {unexpected}")
    class_dep = sorted(c for c, p in pops.items() if p == "task_class")
    expect("no tier-1 bound is class-dependent", class_dep == [], str(class_dep))
    expect("and no per-class table is left behind claiming otherwise",
           static.TASK_CLASS_BOUND_TABLES == {},
           str(sorted(static.TASK_CLASS_BOUND_TABLES)))


# --------------------------------------------------------------------------- #
# mutants
# --------------------------------------------------------------------------- #

def mutants(inks: dict[str, dict[str, Any]], mutant_tmp: Path) -> None:
    """Each removes one mechanism a row above names; that row must go red.

    A bound that cannot fail is worse than none, because it looks like a pass. Each
    block states which row it is aimed at, so a mutant that stops being load-bearing is
    readable rather than merely green.
    """
    print("\n[mutants: can these checks fail?]")
    filled_ink, blank_ink = inks["filled"], inks["blank"]

    # THE PRE-CHANGE CODE, restored verbatim. This is the mutant the whole file turns
    # on: if `tasks/168` had widened the ceiling to admit the subject that exposed it
    # rather than removing it, this row would still be green at some larger number.
    with patched(static, "nonempty_verdict",
                 lambda fi, n: (static.INK_FLOOR
                                <= float(fi.get("mean_ink", 0.0))
                                <= RETIRED_GAME_CEILING, "mutant: the 0.85 ceiling")):
        caught = drive_collect("game", filled_ink["mean_ink"])["passed"] is False
    expect(f"mutant 'the {RETIRED_GAME_CEILING} ceiling is restored' is caught by the "
           "filled row", caught)

    with patched(static, "INK_FLOOR", 0.0):
        caught = static.nonempty_verdict(inks["whisper"], 2)[0] is True
    expect("mutant 'the floor is removed' is caught by the whisper row", caught)

    # THE TWO HALVES ARE INDEPENDENTLY LOAD-BEARING, which is what makes the row above
    # a fair test of the floor. With the floor gone, `blank` and `flood` are still
    # refused - by the all-flat half - so neither of them could have told you which
    # half acted (#37: a control that shares its subject's assumptions).
    with patched(static, "INK_FLOOR", 0.0):
        still = [n for n in ("blank", "flood")
                 if static.nonempty_verdict(inks[n], 2)[0] is False]
    expect("with no floor at all, blank and flood are still refused by the all-flat "
           "half", still == ["blank", "flood"], str(still))

    # THE REFERENCE ITSELF. `analyse_frames` measures each frame against its own mode;
    # this restores the pre-`tasks/178` code, one background taken from frame 0 and
    # applied to all 12. `COLOUR_DRIFT` is the only row that can see it - every fixture
    # holds identical frames, so frame 0's mode IS each frame's own mode there, and the
    # blank arrangements still fail on the all-flat half.
    #
    # THE MUTANT IS THE REAL BODY, not a stub returning a number: a lambda that simply
    # reported 0.91665 would prove the row reads its argument and nothing about where
    # `analyse_frames` gets its reference colour.
    def frame0_reference(frames: list[Path]) -> dict[str, Any]:
        imgs = [png.read(f) for f in frames]
        bg = imgs[0].dominant_background()
        inks = [im.ink_coverage(bg) for im in imgs]
        return {"count": len(imgs), "errors": [],
                "flat_frames": sum(1 for im in imgs if im.is_flat()),
                "mean_ink": round(sum(inks) / len(inks), 5),
                "per_frame_ink": [round(v, 5) for v in inks]}

    with patched(static, "analyse_frames", frame0_reference):
        info = measure_sequence(colour_drift, mutant_tmp)
        admitted, _ev = static.nonempty_verdict(info, info["count"])
    expect("mutant 'the reference is frame 0's mode again' is caught by the "
           "colour-drift row",
           admitted is True and info["mean_ink"] == COLOUR_DRIFT_UNDER_FRAME0,
           f"it would read mean_ink={info['mean_ink']} with "
           f"flat_frames={info['flat_frames']}/{info['count']} and PASS")

    # The mutant installs the fallback and the row RE-RUNS `collect`'s pre-flight - the
    # only caller that spends anything. Asserting that the patched lambda does not raise
    # would be true for every input and would exercise no check in this file.
    with patched(static, "assert_task_class", lambda k: "game"):
        ok, ran_commands = refuses_before_spending("film")
    expect("mutant 'an unknown class falls back to game' is caught by the refusal row",
           not ok, f"it graded an unplaceable class, running {ran_commands}")

    # THE WIRING, NOT THE CONSTANT. A `collect` that inlined its own comparison instead
    # of calling `nonempty_verdict` leaves every direct row above green.
    with patched(static, "nonempty_verdict",
                 lambda fi, n: (False, "mutant: the criterion always fails")):
        caught = drive_collect("game", 0.5)["passed"] is False
    expect("mutant 'collect stops using nonempty_verdict' is caught by the collect "
           "drive", caught)

    print("\n[mutants: can the bound census fail?]")
    without = {k: v for k, v in static.TIER1_BOUND_POPULATION.items()
               if k != "render.animates"}
    with patched(static, "TIER1_BOUND_POPULATION", without):
        caught = any("render.animates" in p
                     for p in static.assert_tier1_bounds_declared())
    expect("mutant 'a criterion is added with no declared population' is caught",
           caught)

    with patched(static, "TIER1_BOUND_POPULATION",
                 {**static.TIER1_BOUND_POPULATION, "lint.clean": "vibes"}):
        caught = any("vibes" in p for p in static.assert_tier1_bounds_declared())
    expect("mutant 'a population outside the closed list' is caught", caught)

    with patched(static, "TIER1_BOUND_POPULATION",
                 {**static.TIER1_BOUND_POPULATION, "lint.clean": "task_class"}):
        caught = any("per-class tables" in p
                     for p in static.assert_tier1_bounds_declared())
    expect("mutant 'a declared class-dependence with no table' is caught", caught)

    # The table is empty today, so the mutant has to CONSTRUCT the shape it guards
    # against: a criterion declaring `task_class` with a table that names one class.
    with patched(static, "TIER1_BOUND_POPULATION",
                 {**static.TIER1_BOUND_POPULATION, "lint.clean": "task_class"}):
        with patched(static, "TASK_CLASS_BOUND_TABLES",
                     {"lint.clean": {"game": (0.0, 1.0, "game only")}}):
            caught = any("no entry for ['scene']" in p
                         for p in static.assert_tier1_bounds_declared())
    expect("mutant 'a per-class table that forgot a class' is caught", caught)

    with patched(static, "TIER1_BOUND_POPULATION",
                 {**static.TIER1_BOUND_POPULATION, "render.frames_OLD": "no_bound"}):
        caught = any("no longer a tier-1 criterion" in p
                     for p in static.assert_tier1_bounds_declared())
    expect("mutant 'the registry describes a criterion that does not exist' is caught",
           caught)

    # THE POLICY MOVING WITHOUT THE COUNT MOVING. `tests.exist` reclassified from
    # `starter` to `no_bound` keeps the registry legal, keeps the total at 14 and keeps
    # nothing class-dependent - everything except the tally.
    moved = {**static.TIER1_BOUND_POPULATION, "tests.exist": "no_bound"}
    with patched(static, "TIER1_BOUND_POPULATION", moved):
        legal = static.assert_tier1_bounds_declared() == []
        tally, _unexpected = _tally(moved)
    expect("mutant 'a bound is silently reclassified' is caught by the exact tally",
           legal and len(moved) == 14 and tally != EXPECTED_TALLY, str(tally))


# --------------------------------------------------------------------------- #
# the corpus arm - the producer for every ink figure the documents quote
# --------------------------------------------------------------------------- #

def corpus(runs_root: Path) -> None:
    """One row per submission, most recent grading - `tier1_census`'s population.

    IT DOES NOT WALK THE TREE ITSELF. `judge/tier1_census.py` already owns the walker
    and the dedup policy, both bought by task 75: reports live at any depth, two run
    directories are wrappers holding others, and the same work tree has been graded
    three times. A second walker here would be a second policy, which is how #100
    recurred - and the obvious `**/programmatic.json` glob is measurably wrong, because
    the 16 `wg-g4c-capgate` gradings store their tier-1 record inside `report.json` and
    have no such file.
    """
    print(f"\n[corpus: every stored grading under {runs_root}]")
    import tier1_census

    gradings, skipped_paths = tier1_census.load_gradings(runs_root)
    if not gradings:
        print("  NOT ASKED - no stored grading under that root. `eval/runs` is "
              "gitignored, so a worktree's copy is empty; this is not `0 firings`.")
        return
    kept, superseded = tier1_census.latest_per_submission(gradings)

    rows, skipped = [], []
    stored_class = inferred_class = 0
    for r in kept:
        rec = json.loads(Path(r["report"]).read_text(encoding="utf-8"))
        # `task_class` is stamped only on records written since 2026-08-23. The id shape
        # is a SECOND channel and not the same fact, so a record neither can place is
        # counted out loud rather than read as a game.
        #
        # A record placed by INFERENCE is counted out loud too. Reporting `game: n=68`
        # without saying how many of the 68 were read and how many were guessed makes
        # `_class_of` unfalsifiable from this output: if the id shape ever places a
        # record wrongly, every figure below moves and nothing here would disagree.
        klass = rec.get("task_class")
        if klass:
            stored_class += 1
        else:
            klass = _class_of(str(rec.get("game")))
            inferred_class += 1
        crit = next((c for c in r["criteria"] if c["id"] == "render.nonempty"), None)
        if crit is None or klass not in static.TASK_CLASSES:
            skipped.append((r["trial"], "no render.nonempty" if crit is None
                            else f"unplaceable class {klass!r}"))
            continue
        rows.append((klass, r, rec.get("programmatic") or {}, crit))

    print(f"  {len(gradings)} gradings over {len(kept)} submissions "
          f"({len(superseded)} superseded, {len(skipped_paths)} paths not a run); "
          f"{len(rows)} carry render.nonempty, {len(skipped)} skipped")
    print(f"  task_class read from the record on {stored_class}, inferred from the id "
          f"shape by _class_of on {inferred_class} (of {len(kept)} submissions examined)")
    print("  every mean_ink below is a FRAME-0 reading: it is what the grader that wrote "
          "the record computed, and `tasks/178` moved the reference to each frame's own "
          "mode. `--reference-shift` reports both.")
    for name, why in skipped:
        print(f"    skipped {name}: {why}")
    # A record with no `frames.mean_ink` is PARTITIONED OUT and counted, never sorted
    # among the floats: `sorted()` over a mix of None and numbers raises, so the arm that
    # produces every published ink figure would die rather than report.
    for klass in sorted({r[0] for r in rows}):
        have = [r for r in rows if r[0] == klass]
        inks = sorted(v for r in have
                      if (v := r[2].get("frames", {}).get("mean_ink")) is not None)
        missing = len(have) - len(inks)
        if not inks:
            print(f"  {klass}: 0 of {len(have)} record(s) carry frames.mean_ink - "
                  f"NO RANGE, which is not a range of 0")
            continue
        print(f"  {klass}: n={len(inks)}  mean_ink min={inks[0]} max={inks[-1]}"
              + (f"  ({missing} carry no mean_ink)" if missing else ""))

    print("\n  every render.nonempty FAILURE on record, and what it hit:")
    fired = [r for r in rows if not r[3]["passed"]]
    if not fired:
        print("    none")
    for klass, r, tier1, _crit in fired:
        f = tier1.get("frames", {})
        ink, n = f.get("mean_ink"), f.get("count")
        # NOT REGRADABLE is a third value, and it is not a FAIL. `nonempty_verdict`
        # would raise on `float(None)` and take the whole report with it; inventing a
        # 0.0 would be worse, because a fabricated floor failure is indistinguishable
        # from a measured one.
        if ink is None:
            print(f"    {r['run']}/{r['trial']}  class={klass}  mean_ink=absent  "
                  f"frames={n}  NOT REGRADABLE - the stored record carries no "
                  f"frames.mean_ink, so which bound it hit cannot be established")
            continue
        # WHICH BOUND THE STORED VERDICT HIT is a question about the bound that was in
        # force when it was graded, not about today's. Every stored record predates
        # `tasks/168`, so a firing above the floor hit the ceiling that has since been
        # retired - and printing only today's floor would leave it unexplained.
        which = "floor" if ink < static.INK_FLOOR \
            else f"the retired {RETIRED_GAME_CEILING} ceiling"
        now, _ev = static.nonempty_verdict(f, n or 0)
        before = evaluate.gate_verdict(tier1)
        after = evaluate.gate_verdict(_with_verdict(tier1, now))
        print(f"    {r['run']}/{r['trial']}  class={klass}  mean_ink={ink}  "
              f"frames={n}  hit={which}  tier2={r['t2']}")
        print(f"      re-graded under the floor {static.INK_FLOOR}, no ceiling: "
              f"{'PASS' if now else 'FAIL'}")
        print(f"      gate: {_gate(before)}  ->  {_gate(after)}")


def reference_shift(runs_root: Path) -> int:
    """Every stored frame set under BOTH references. The producer for `eval/RUNS.md`.

    Slow on purpose: it decodes every stored PNG in pure Python rather than trusting the
    record, because the record only holds one of the two readings.

    IT PROVES ITS OWN EXTRACTION FIRST. The frame-0 arm recomputes what the grader that
    wrote each record computed, so it must reproduce every stored `mean_ink` to the
    digit; any disagreement is printed and the arm refuses to report a shift, since a
    per-frame figure from a reader that cannot reproduce the known value means nothing
    (rule 12). Returns the number of sets whose `mean_ink` moves.
    """
    print(f"\n[reference shift: every stored frame set under both references, "
          f"{runs_root}]")
    import tier1_census

    kept, _superseded = tier1_census.latest_per_submission(
        tier1_census.load_gradings(runs_root)[0])
    if not kept:
        print("  NOT ASKED - no stored grading under that root. `eval/runs` is "
              "gitignored, so a worktree's copy is empty; this is not `0 sets move`.")
        return 0
    rows, mismatches, no_frames = [], [], 0
    for r in kept:
        rep = Path(r["report"])
        frames = sorted((rep.parent / "frames").glob("*.png"))
        if not frames:
            no_frames += 1
            continue
        imgs, unreadable = [], 0
        for f in frames:
            try:
                imgs.append(png.read(f))
            except png.PngError:
                unreadable += 1
        if not imgs:
            no_frames += 1
            continue
        bg0 = imgs[0].dominant_background()
        f0 = round(sum(im.ink_coverage(bg0) for im in imgs) / len(imgs), 5)
        pf = round(sum(im.ink_coverage(im.dominant_background())
                       for im in imgs) / len(imgs), 5)
        stored = (json.loads(rep.read_text(encoding="utf-8"))
                  .get("programmatic", {}).get("frames", {}).get("mean_ink"))
        if stored is not None and stored != f0:
            mismatches.append((r["trial"], stored, f0))
        rows.append((r["run"], r["trial"], f0, pf, unreadable))

    print(f"  {len(rows)} frame sets read, {no_frames} submission(s) with no readable "
          f"frame on disk, of {len(kept)} submissions")
    if mismatches:
        print(f"  EXTRACTION NOT PROVED: the frame-0 arm disagrees with {len(mismatches)}"
              f" stored record(s) it should reproduce exactly. No shift is reported.")
        for trial, stored, got in mismatches:
            print(f"    {trial}: stored {stored}, recomputed {got}")
        return -1
    print(f"  extraction proved: the frame-0 arm reproduces all {len(rows)} stored "
          f"mean_ink values to the digit")
    moved = [x for x in rows if x[2] != x[3]]
    print(f"  {len(moved)} of {len(rows)} sets move:")
    for run, trial, f0, pf, _u in sorted(moved, key=lambda x: -abs(x[2] - x[3])):
        print(f"    {trial:32s} {f0:>9} -> {pf:<9} ({pf - f0:+.5f})  {run}")
    below = [(t, f0, pf) for _r, t, f0, pf, _u in rows
             if min(f0, pf) < static.INK_FLOOR]
    print(f"  sets below the floor {static.INK_FLOOR} under either reference: "
          f"{len(below)} {below}")
    lo = min(min(x[2], x[3]) for x in rows)
    print(f"  lowest value under either reference: {lo}")
    return len(moved)


def _class_of(game: str) -> str:
    """The id-shape fallback for a stored record written before `task_class` was stamped.

    A SECOND channel and not the same fact as the stored field, which is why the caller
    counts what it had to fall back on rather than silently reading it as a game.
    """
    import aspects
    return aspects.task_class(game)


def _with_verdict(tier1: dict[str, Any], passed: bool) -> dict[str, Any]:
    """A COPY of one stored tier-1 record with `render.nonempty` re-decided.

    Nothing under `eval/runs` is written: the re-grade is computed for the report and the
    stored record keeps the verdict it was given (`eval/RUNS.md` holds both).
    """
    crits = [{**c, "passed": passed} if c["id"] == "render.nonempty" else c
             for c in tier1.get("criteria", [])]
    return {**tier1, "criteria": crits}


def _gate(g: dict[str, Any]) -> str:
    """One gate verdict as a line. `NOT USABLE` is a third value and is never a pass."""
    if not g.get("usable"):
        return "NOT USABLE"
    if g.get("passed"):
        return f"PASS ({g['n_scored']}/{g['n_scored']})"
    ids = g.get("failed") or []
    shown = ids if len(ids) <= 5 else ids[:5] + [f"+{len(ids) - 5} more"]
    return f"FAIL {g['n_failed']}/{g['n_scored']} {shown}"


# --------------------------------------------------------------------------- #

def phases(inks: dict[str, dict[str, Any]],
           tmp: Path) -> list[tuple[str, Any, int]]:
    """Every mandatory phase and **how many expectations it must contribute**.

    A single total cannot see a phase that stopped running: drop the mutant sweep and
    the rest still print as a clean pass. Counts derived from a table move with it; the
    rest are written out, because an expectation taken from its subject is not an
    expectation.
    """
    return [
        ("fixtures", lambda: test_fixtures_measure_what_they_claim(inks),
         len(FIXTURES) + 1),
        ("criterion", lambda: test_the_criterion(inks),
         len(CRITERION_ROWS) + 1 + len(MECHANISM_ROWS)),
        ("blank renders",
         lambda: test_a_blank_render_fails_however_its_colours_are_arranged(tmp),
         2 * len(BLANK_RENDERS) + 1),
        ("colour drift", lambda: test_a_colour_drift_that_drew_nothing_fails(tmp), 1),
        ("the two halves", lambda: test_the_two_halves(inks, tmp), 3),
        ("class refusal", test_an_unplaceable_class_is_refused, 3),
        ("collect wiring", test_collect_reaches_the_criterion, 6),
        ("bound census", test_bound_census, 6),
        ("mutants", lambda: mutants(inks, tmp), 12),
    ]


def main() -> int:
    """Run every phase, then the corpus arm if a runs-root was given. Exit 0 only if
    every phase contributed the count it declares and every expectation held.
    """
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--runs-root", type=Path,
                    help="a main checkout's eval/runs, for the corpus arm")
    ap.add_argument("--reference-shift", action="store_true",
                    help="with --runs-root: re-read every stored PNG and report which "
                         "sets move between the two references (~80 s)")
    args = ap.parse_args()
    if args.reference_shift and not args.runs_root:
        ap.error("--reference-shift needs --runs-root: it reads stored PNGs, and a "
                 "worktree's eval/runs is empty")

    tmp = Path(tempfile.mkdtemp(prefix="inkwin-"))
    short: list[str] = []
    try:
        inks = {name: measure(make, tmp) for name, make, _lo, _hi in FIXTURES}
        for name, phase, want in phases(inks, tmp):
            before = CHECKS
            phase()
            got = CHECKS - before
            if got != want:
                short.append(f"{name}: {got} of {want}")
        if args.runs_root:
            corpus(args.runs_root)
            if args.reference_shift:
                if reference_shift(args.runs_root) < 0:
                    short.append("reference shift: extraction not proved")
            else:
                print("\n[reference shift: NOT RUN - add --reference-shift]")
        else:
            print("\n[corpus: NOT RUN - pass --runs-root <main checkout>/eval/runs]")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    # A CONTROL THAT ASKED NOTHING IS NOT A CONTROL THAT PASSED. `0/0 expectations held`
    # reads exactly like a clean run, which is the shape this file exists to refuse -
    # and so does a run where one PHASE stopped executing, which a single total cannot
    # see. Every phase declares its own count in `phases()`, so a mutant that removes
    # the whole mutant sweep is caught as loudly as one that empties the file.
    if short:
        print(f"\nPHASES SHORT: {'; '.join(short)}. A check that was not asked is not a "
              f"check that held.")
        return 1
    print(f"\n{CHECKS - len(FAILS)}/{CHECKS} expectations held")
    if FAILS:
        print("FAILED: " + ", ".join(FAILS))
        return 1
    print("ink window control: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
