#!/usr/bin/env python3
"""Can `render.nonempty` fail, per task class - and can it still pass what it should?

`render.nonempty` is TIER 1, and tier 1 is a GATE rather than a weighted term
(`RUBRIC.md`). A false negative here does not cost a fraction of a score; it stops a
correct submission being scored at all. Its window was `0.001-0.85` for every task from
this repository's first commit, and the ceiling is calibrated on games - a subject drawn
against a background. A scene is contracted to FILL the frame, so the ceiling's sign is
inverted there (`tasks/163`).

Three halves, because a gate needs all three:

  FIXTURES   real PNGs through the real reader and `analyse_frames`, so the ink numbers
             are measured rather than asserted. Each fixture's expected coverage is
             stated in `FIXTURES` before anything runs - the one known-good row rule 12
             asks for, since a census that returns one value for every subject is
             reporting the instrument.
  MUTANTS    remove a mechanism the window names and require a named expectation to go
             red. A window that cannot fail is worse than none: it looks like a pass.
  VARIANTS   correct inputs the implementation does not resemble, where the criterion
             must still PASS - a dark scene that does NOT fill the frame, the starter's
             own placeholder marker, and an ordinary game. Every false negative
             adjudicated in this project has been of that kind (rule 15), and the one
             this file exists for was too.

    python3 judge/ink_window_control.py
    python3 judge/ink_window_control.py --runs-root <main checkout>/eval/runs

`--runs-root` adds the corpus arm, which is also the PRODUCER for every ink figure the
documents quote: the per-class distribution of `mean_ink`, every `render.nonempty`
firing with the bound it hit, and the re-grade of each firing under the per-class
window - including the gate verdict before and after. `eval/runs` is gitignored, so a
worktree's copy is empty and the arm prints `NOT ASKED` rather than `0 firings`; the two
are different claims.
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
    """A frame with no flat region at all: what a scene is contracted to draw."""
    px = bytearray(W * H * 3)
    for y in range(H):
        for x in range(W):
            i = (y * W + x) * 3
            px[i] = (x * 255) // W
            px[i + 1] = (y * 255) // H
            px[i + 2] = 128
    return bytes(px)


#: `(name, pixels, low, high)` - the coverage each fixture must measure at, STATED
#: HERE rather than read off the run. A fixture whose measured ink drifts out of its
#: stated band means the reader moved, and every row below would then be asking its
#: question of a different picture.
FIXTURES: list[tuple[str, Any, float, float]] = [
    ("blank", blank, 0.0, 0.0),
    ("placeholder", placeholder, 0.001, 0.005),
    ("sparse", sparse, 0.015, 0.030),
    ("filled", filled, 0.950, 1.000),
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
    expect("the fixtures are not all one value",
           len({round(inks[n]["mean_ink"], 5) for n, *_ in FIXTURES}) == len(FIXTURES),
           "a census returning one value across a population it exists to "
           "discriminate is reporting the instrument (rule 12)")


# --------------------------------------------------------------------------- #
# the window itself, both directions, per class
# --------------------------------------------------------------------------- #

#: `(fixture, task class, must pass)`. The FLOOR is asked of both classes and the
#: CEILING of one, which is the whole content of the change.
WINDOW_ROWS = [
    ("blank", "game", False),
    ("blank", "scene", False),          # a BLANK scene frame still fails
    ("placeholder", "game", True),
    ("placeholder", "scene", True),
    ("sparse", "game", True),
    ("sparse", "scene", True),          # VARIANT: a scene that does not fill the frame
    ("filled", "game", False),
    ("filled", "scene", True),          # what the game ceiling refused (tasks/163)
]


def test_the_window(inks: dict[str, dict[str, Any]]) -> None:
    """The criterion itself: `WINDOW_ROWS` both ways per class, then the two refusals.

    The floor is asked of both classes and the ceiling of one, which is the entire content
    of the change - so a row that moved would be visible here before anywhere else.
    """
    print("\n[the window, both directions, per task class]")
    for fixture, klass, want in WINDOW_ROWS:
        ok, ev = static.nonempty_verdict(inks[fixture], klass, 2)
        expect(f"{fixture} on a {klass}: {'PASS' if want else 'FAIL'}", ok is want,
               ev[:150])
    print("\n[the class reaches the stored evidence, not just the verdict]")
    for klass in ("game", "scene"):
        _ok, ev = static.nonempty_verdict(inks["sparse"], klass, 2)
        lo, hi, why = static.ink_window(klass)
        expect(f"a {klass}'s evidence names its class and its window",
               f"{klass} window {lo}-{hi}" in ev and why in ev, ev[:120])

    print("\n[an unknown class is refused, not defaulted]")
    try:
        static.ink_window("film")
        expect("ink_window refuses a class it cannot place", False, "it returned")
    except ValueError as e:
        expect("ink_window refuses a class it cannot place", True, str(e)[:90])
    # COUNT THE COMMANDS, do not merely catch the exception. `except ValueError` accepts
    # one raised from anywhere in `collect`, including after `just check` has run - so
    # the row would report "refused before spending" about a refusal that spent one.
    ok, ran_commands = refuses_before_spending("film")
    expect("collect refuses before spending a toolchain", ok,
           f"{len(ran_commands)} command(s) ran first: {ran_commands}")


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

    Driving the decision function alone would not answer whether `collect` PASSES ITS
    ARGUMENT ON, which is the edge the change adds and the edge a mutant can remove.
    """
    with stubbed_toolchain(mean_ink, []):
        rec = static.collect(Path("/nonexistent"), task_class=task_class)
    return next(c for c in rec["criteria"] if c["id"] == "render.nonempty")


def test_collect_uses_the_class_it_was_given() -> None:
    """Does the class the runner handed down actually reach the criterion?

    `test_the_window` passes the class explicitly, so it stays green against a `collect`
    that ignores its argument entirely. This phase is the only one that would not.
    """
    print("\n[collect passes its task_class through to the criterion]")
    scene = drive_collect("scene", 0.96561)
    game = drive_collect("game", 0.96561)
    expect("collect(scene) passes the first stored scene's 0.96561",
           scene["passed"] is True, scene["evidence"][:120])
    expect("collect(game) fails the same coverage", game["passed"] is False,
           game["evidence"][:120])
    expect("collect(scene) still fails a blank frame",
           drive_collect("scene", 0.0)["passed"] is False)


# --------------------------------------------------------------------------- #
# the bound census - every tier-1 criterion answers where its bound came from
# --------------------------------------------------------------------------- #

#: What `static.TIER1_BOUND_POPULATION` must tally to, written out INDEPENDENTLY of it.
#: This is the 8/5/1 that `judge/RUBRIC.md`, `DECISIONS.md` and `eval/judge/AGENTS.md`
#: state in prose, and it is the only place that count is checked rather than repeated.
EXPECTED_TALLY = {"no_bound": 8, "starter": 1, "capture_contract": 1,
                  "audio_signal": 3, "task_class": 1}


def test_bound_census() -> None:
    """Has every tier-1 criterion answered *which population was your bound calibrated on?*

    The tally is both printed (the documents state 8/5/1 in prose and a prose count with no
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
    # THE WHOLE TALLY, not just its total and its class-dependent entry. Reclassifying
    # `tests.exist` from `starter` to `no_bound` leaves both of those green while the
    # policy moves, and this row is where the documents' 8/5/1 is actually checked.
    # It is written out here rather than derived from `pops`: an expectation imported
    # from its subject is not an expectation (AGENTS.md rule 12's corollary).
    expect(f"the tally is exactly {EXPECTED_TALLY}", dict(tally) == EXPECTED_TALLY,
           str(dict(tally)))
    class_dep = sorted(c for c, p in pops.items() if p == "task_class")
    expect("exactly one criterion's bound is class-dependent, and it is this one",
           class_dep == ["render.nonempty"], str(class_dep))
    for cid, table in static.TASK_CLASS_BOUND_TABLES.items():
        expect(f"{cid}'s table covers both classes",
               {"game", "scene"} <= set(table), str(sorted(table)))


# --------------------------------------------------------------------------- #
# mutants
# --------------------------------------------------------------------------- #

def mutants(inks: dict[str, dict[str, Any]]) -> None:
    """Each removes one mechanism a row above names; that row must go red.

    A window that cannot fail is worse than no window, because it looks like a pass. Each
    block states which row it is aimed at, so a mutant that stops being load-bearing is
    readable rather than merely green.
    """
    print("\n[mutants: can these checks fail?]")
    filled_ink, blank_ink = inks["filled"], inks["blank"]

    with patched(static, "INK_WINDOW",
                 {**static.INK_WINDOW, "scene": static.INK_WINDOW["game"]}):
        caught = static.nonempty_verdict(filled_ink, "scene", 2)[0] is False
    expect("mutant 'the scene window is the game window again' is caught by the "
           "filled-scene row", caught)

    with patched(static, "INK_WINDOW",
                 {**static.INK_WINDOW, "scene": (0.0, 1.0, "no floor")}):
        caught = static.nonempty_verdict(blank_ink, "scene", 2)[0] is True
    expect("mutant 'the scene floor is removed' is caught by the blank-scene row",
           caught)

    # The mutant installs the fallback and the row RE-RUNS `collect`'s pre-flight - the
    # only caller that spends anything. Asserting that the patched lambda does not raise
    # would be true for every input and would exercise no check in this file.
    with patched(static, "ink_window", lambda k: static.INK_WINDOW["game"]):
        ok, ran_commands = refuses_before_spending("film")
    expect("mutant 'an unknown class falls back to the game window' is caught by the "
           "refusal row", not ok,
           f"it graded an unplaceable class, running {ran_commands}")

    # THE WIRING, NOT THE TABLE. This one is only reachable through `collect`: a
    # `nonempty_verdict` that ignores the class it was handed leaves every row above
    # green, because they all pass the class explicitly.
    with patched(static, "nonempty_verdict",
                 lambda fi, tc, n: (0.001 <= float(fi.get("mean_ink", 0.0)) <= 0.85,
                                    "mutant: the class argument is ignored")):
        caught = drive_collect("scene", 0.96561)["passed"] is False
    expect("mutant 'the criterion ignores the class collect handed it' is caught by "
           "the collect drive", caught)

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

    with patched(static, "TASK_CLASS_BOUND_TABLES",
                 {"render.nonempty": {"game": static.INK_WINDOW["game"]}}):
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
    # exactly one class-dependent entry - everything except the tally.
    moved = {**static.TIER1_BOUND_POPULATION, "tests.exist": "no_bound"}
    with patched(static, "TIER1_BOUND_POPULATION", moved):
        legal = static.assert_tier1_bounds_declared() == []
        tally = dict(collections.Counter(moved.values()))
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
        if crit is None or klass not in static.INK_WINDOW:
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
        lo, hi, _why = static.ink_window(klass)
        # NOT REGRADABLE is a third value, and it is not a FAIL. `nonempty_verdict`
        # would raise on `float(None)` and take the whole report with it; inventing a
        # 0.0 would be worse, because a fabricated floor failure is indistinguishable
        # from a measured one.
        if ink is None:
            print(f"    {r['run']}/{r['trial']}  class={klass}  mean_ink=absent  "
                  f"frames={n}  NOT REGRADABLE - the stored record carries no "
                  f"frames.mean_ink, so which bound it hit cannot be established")
            continue
        which = "floor" if ink < lo else "ceiling"
        now, _ev = static.nonempty_verdict(f, klass, n or 0)
        before = evaluate.gate_verdict(tier1)
        after = evaluate.gate_verdict(_with_verdict(tier1, now))
        print(f"    {r['run']}/{r['trial']}  class={klass}  mean_ink={ink}  "
              f"frames={n}  hit={which}  tier2={r['t2']}")
        print(f"      re-graded under the {klass} window {lo}-{hi}: "
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
        ("window", lambda: test_the_window(inks), len(WINDOW_ROWS) + 4),
        ("collect propagation", test_collect_uses_the_class_it_was_given, 3),
        ("bound census", test_bound_census, 5 + len(static.TASK_CLASS_BOUND_TABLES)),
        ("mutants", lambda: mutants(inks), 10),
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
