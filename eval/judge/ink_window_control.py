#!/usr/bin/env python3
"""Can `render.nonempty` fail - and can it still pass everything it should?

`render.nonempty` is TIER 1, and tier 1 is a GATE rather than a weighted term
(`RUBRIC.md`). A false negative here does not cost a fraction of a score; it stops a
correct submission being scored at all. The criterion is a FLOOR with no ceiling: it was
`0.001-0.85` for every task from this repository's first commit, `tasks/163` took the
ceiling off scenes, and `tasks/168` took it off entirely.

**The derivation is a measurement in this file, not a paragraph elsewhere**, because it
is what the removal rests on. `png.Image.ink_coverage` counts pixels differing from
`dominant_background()` - the frame's OWN modal quantised colour - so the quantity runs
backwards from what a ceiling wants: a solid flood, the "the render broke and filled the
screen" defect, measures 0.0 and lands on the FLOOR, while what reads near 1.0 is the
absence of a modal region, which is a gradient. `MECHANISM_ROWS` states both before
anything runs.

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


def placeholder() -> bytes:
    """The starter's own placeholder marker: 0.0015 of a 640x400 frame."""
    return bytes(_rect(_flat(), 24, 16))


def sparse() -> bytes:
    """A subject against a background - what a game frame looks like."""
    return bytes(_rect(_flat(), 80, 64))


def filled() -> bytes:
    """A frame with no flat region at all: a gradient, which reads near 1.0.

    What a scene is contracted to draw, and also what a night game's sky looks like -
    `wg-g4c` `g4_platformer__godot__t1` measured 0.881 with its subject drawn on top.
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

    It measures 0.0, not 1.0, because `dominant_background()` returns the frame's own
    modal colour and here that is the flood. So this fixture fails on the FLOOR, and
    removing the ceiling opened no hole for it - which is the whole reason the fixture
    is here rather than in a comment.
    """
    return bytes(bytes((255, 0, 255)) * (W * H))


#: `(name, pixels, low, high)` - the coverage each fixture must measure at, STATED
#: HERE rather than read off the run. A fixture whose measured ink drifts out of its
#: stated band means the reader moved, and every row below would then be asking its
#: question of a different picture.
FIXTURES: list[tuple[str, Any, float, float]] = [
    ("blank", blank, 0.0, 0.0),
    ("flood", flood, 0.0, 0.0),
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
     "a frame that is entirely one colour reads 0.0, because that colour IS the modal "
     "colour - so 'the render filled the screen' hits the FLOOR, never a ceiling"),
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
def stubbed_toolchain(mean_ink: float, ran_commands: list[str]):
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
                  "per_frame_ink": [mean_ink], "mean_frame_delta": 0.5}
    with contextlib.ExitStack() as st:
        st.enter_context(patched(static, "run", record))
        st.enter_context(patched(static, "film",
                                 lambda *a, **k: (cmd, [], Path(tempfile.mkdtemp()))))
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


def drive_collect(task_class: str, mean_ink: float) -> dict[str, Any]:
    """The real `collect`, offline: every subprocess it makes is replaced.

    Driving the decision function alone leaves a `collect` that never calls it - or
    calls something else - entirely green, so the wiring gets its own rows.
    """
    with stubbed_toolchain(mean_ink, []):
        rec = static.collect(Path("/nonexistent"), task_class=task_class)
    return next(c for c in rec["criteria"] if c["id"] == "render.nonempty")


def test_collect_reaches_the_criterion() -> None:
    """Does `collect` decide `render.nonempty` with `nonempty_verdict`, in both classes?

    The rows above call the decision function directly and stay green against a
    `collect` that inlined its own comparison. These are the only ones that would not,
    and both stored ceiling firings are used as the input - 0.96561 and 0.88137, the two
    coverages the retired 0.85 refused.
    """
    print("\n[collect decides the criterion with the same floor, in both classes]")
    for klass, ink, label in (("scene", 0.96561, "the stored scene's"),
                              ("game", 0.88137, "the stored platformer's")):
        got = drive_collect(klass, ink)
        expect(f"collect({klass}) passes {label} {ink}", got["passed"] is True,
               got["evidence"][:120])
    expect("collect(game) still fails a blank frame",
           drive_collect("game", 0.0)["passed"] is False)
    expect("collect(scene) still fails a blank frame",
           drive_collect("scene", 0.0)["passed"] is False)


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

def mutants(inks: dict[str, dict[str, Any]]) -> None:
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
        caught = static.nonempty_verdict(blank_ink, 2)[0] is True
    expect("mutant 'the floor is removed' is caught by the blank row", caught)

    # THE FLOOD, AND IT IS THE VARIANT'S MUTANT. Removing the floor is what would let
    # "the render filled the screen" through, and this row proves the flood fixture is
    # the input that catches it rather than a picture nothing looks at.
    with patched(static, "INK_FLOOR", 0.0):
        caught = static.nonempty_verdict(inks["flood"], 2)[0] is True
    expect("mutant 'the floor is removed' is caught by the flood row too", caught)

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

def phases(inks: dict[str, dict[str, Any]]) -> list[tuple[str, Any, int]]:
    """Every mandatory phase and **how many expectations it must contribute**.

    A single total cannot see a phase that stopped running: drop the mutant sweep and
    the remaining 25 still print as a clean pass. Counts derived from a table move with
    it; the rest are written out, because an expectation taken from its subject is not
    an expectation.
    """
    return [
        ("fixtures", lambda: test_fixtures_measure_what_they_claim(inks),
         len(FIXTURES) + 1),
        ("criterion", lambda: test_the_criterion(inks),
         len(CRITERION_ROWS) + 1 + len(MECHANISM_ROWS)),
        ("class refusal", test_an_unplaceable_class_is_refused, 3),
        ("collect wiring", test_collect_reaches_the_criterion, 4),
        ("bound census", test_bound_census, 6),
        ("mutants", lambda: mutants(inks), 11),
    ]


def main() -> int:
    """Run every phase, then the corpus arm if a runs-root was given. Exit 0 only if
    every phase contributed the count it declares and every expectation held.
    """
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--runs-root", type=Path,
                    help="a main checkout's eval/runs, for the corpus arm")
    args = ap.parse_args()

    tmp = Path(tempfile.mkdtemp(prefix="inkwin-"))
    short: list[str] = []
    try:
        inks = {name: measure(make, tmp) for name, make, _lo, _hi in FIXTURES}
        for name, phase, want in phases(inks):
            before = CHECKS
            phase()
            got = CHECKS - before
            if got != want:
                short.append(f"{name}: {got} of {want}")
        if args.runs_root:
            corpus(args.runs_root)
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
