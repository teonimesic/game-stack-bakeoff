#!/usr/bin/env python3
"""Can the harness launch and grade a SCENE, and does it still refuse the wrong pairing?

    python3 eval/tools/scene_runner_control.py            # both directions, ~10s
    python3 eval/tools/scene_runner_control.py --paths    # list the guarded paths only

`eval/wholegame.py` had no knowledge of scenes until 2026-08-25: `TASKS` held four games,
`--games` defaulted to every key of it, and a scene registered there would have been
launched by the standing matrix command against a probe that did not exist. Wiring scenes
in makes the runner a new way to reach a grading instrument and a judge pack, and
`eval/SCENES.md` is explicit that an instrument run against the wrong task class returns
confident numbers about a question nobody asked.

WHY THIS FILE ENUMERATES PATHS RATHER THAN TESTING "the guard works". A guard is a
property of a call site, not of a function: `aspects.applicability` was already correct
and already called from three places, and not one of them was the runner. So each row in
`PATHS` NAMES one route from an operator's command to the resource, and the checks drive
that route. A route with no row is a route nobody checked, and adding a caller without
adding a row is the failure this file exists for (AGENTS.md rule 13).

THE CAPTURE PATH IS PINNED TOO, for a different reason. A scene's correctness criteria are
computed from tick-indexed frames with no wall-clock anywhere - that is what makes the
same-seed / different-seed pair a control rather than an opinion, and performance is a
SECOND pass (`eval/SCENES.md`). Two rows ask whether anything time-shaped has leaked into
the correctness pass: one reads the argv the capture recipe is actually invoked with, and
one drives the same submission twice and asks whether a single verdict moved.

Every group is pinned in both directions. A mutant asks whether a row can fail; a variant
asks whether it can still pass on an input it mishandles (AGENTS.md rule 15).
"""

from __future__ import annotations

import argparse
import contextlib
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Callable

HERE = Path(__file__).resolve().parent
EVAL = HERE.parent
sys.path.insert(0, str(EVAL))
sys.path.insert(0, str(EVAL / "judge"))
sys.path.insert(0, str(EVAL / "suites"))

import aspects  # noqa: E402
import evaluate as ev  # noqa: E402
import scene_probe  # noqa: E402
import static  # noqa: E402
import wholegame as wg  # noqa: E402

#: The scene every driving row runs against: `judge/fixtures/ref_parallax`, the reference
#: `scene_mutants.py` validates the probe with. A row red here is about the RUNNER, not
#: about the criteria, which have their own suite.
FIXTURE = EVAL / "judge" / "fixtures" / "ref_parallax"

#: A game id and a scene id, used as each other's wrong answer throughout.
GAME = "g1_pong"
SCENE = "s1_parallax"

PATHS = [
    ("P1", "wholegame.py build --games/--scenes",
     "the rendered prompt in wholegame.ALL_TASKS",
     "wholegame.select_tasks refuses an id no suite defines, and defaults to games"),
    ("P2", "wholegame.py evaluate -> evaluate.evaluate",
     "the per-submission judge pack (anonymise.build_pack)",
     "evaluate.resolve_instrument, via aspects.task_class"),
    ("P3", "wholegame.py evaluate -> evaluate.evaluate tier 2",
     "a play-bot, or the scene probe",
     "evaluate.TIER2_INSTRUMENT, checked by aspects.applicability"),
    ("P4", "wholegame.py evaluate --with-legacy-judge",
     "judge.judge - 13 criteria written about games",
     "evaluate.assert_legacy_judge_allowed -> aspects.applicability"),
    ("P5", "evaluate.py --game",
     "everything evaluate.evaluate reaches",
     "argparse choices = evaluate.TIER2_INSTRUMENT"),
    ("P6", "wholegame.py concurrency-check --game",
     "everything evaluate.evaluate reaches",
     "argparse choices = wholegame.ALL_TASKS"),
]

#: `anonymise.build_pack` gets no row of its own on purpose. It is class-AGNOSTIC - it
#: copies a submission's own files and asks nothing about the task - so what has to hold
#: before it runs is that the task has a class at all, which is P2. The pack is reachable
#: only through P2, and a row that restated P2 would look like a second guard.


# --------------------------------------------------------------------------- #


class Rows:
    """Verdicts, printed as they are decided, with a failure count."""

    def __init__(self) -> None:
        self.failures = 0
        self.n = 0

    def check(self, name: str, ok: bool, detail: str = "") -> None:
        self.n += 1
        self.failures += not ok
        print(f"  {'ok  ' if ok else 'FAIL'}  {name}")
        if detail and not ok:
            print(f"          {detail}")

    def mutant(self, name: str, caught: bool, detail: str = "") -> None:
        self.n += 1
        self.failures += not caught
        print(f"  {'ok  ' if caught else 'FAIL'}  {name}")
        if not caught:
            print(f"          SURVIVED - the rows above measure nothing. {detail}")


@contextlib.contextmanager
def patched(obj: Any, name: str, value: Any):
    """Swap one attribute for the duration of a block, and put it back."""
    old = getattr(obj, name)
    setattr(obj, name, value)
    try:
        yield
    finally:
        setattr(obj, name, old)


def refuses(fn: Callable[[], Any]) -> bool:
    """Did `fn` refuse? `SystemExit`, `ValueError` and `KeyError` all count."""
    try:
        fn()
    except (SystemExit, ValueError, KeyError):
        return True
    return False


class _Stop(Exception):
    """Abandon `evaluate` once a spy has read what it came for."""


def print_paths() -> None:
    width = max(len(p[1]) for p in PATHS)
    for pid, command, reaches, guard in PATHS:
        print(f"  {pid}  {command:<{width}}  ->  {reaches}")
        print(f"      guard: {guard}")


# --------------------------------------------------------------------------- #
# P1 - what the standing command launches
# --------------------------------------------------------------------------- #


def check_selection(rows: Rows) -> None:
    print("\nP1  wholegame.select_tasks - which tasks an invocation builds")

    default = wg.select_tasks(None, None)
    rows.check("the default selection is every game",
               default == list(wg.P.TASKS), f"got {default}")
    rows.check("no scene is in the default selection",
               not [t for t in default if aspects.task_class(t) == "scene"],
               f"scenes defaulted in: {default}")
    rows.check("a scene is built when it is named, and nothing else is",
               wg.select_tasks(None, [SCENE]) == [SCENE],
               f"got {wg.select_tasks(None, [SCENE])}")
    rows.check("both classes can be selected together, deliberately",
               wg.select_tasks([GAME], [SCENE]) == [GAME, SCENE])
    rows.check("an empty --games is refused, not read as `all`",
               refuses(lambda: wg.select_tasks([], None)),
               "a selection narrowed to nothing must not become the widest one there is")
    # AND IT IS REFUSED BEFORE THE SCENES ARE ADDED. A refusal that fires only when the
    # WHOLE selection comes out empty lets `--games --scenes s1_parallax` through, which
    # is the same operator error buying a paid trial instead of a retyped command.
    rows.check("an empty --games is refused even when --scenes fills the selection",
               refuses(lambda: wg.select_tasks([], [SCENE])),
               f"got {wg.select_tasks([], [SCENE]) if not refuses(lambda: wg.select_tasks([], [SCENE])) else ''}")
    rows.check("a task id no suite defines is refused",
               refuses(lambda: wg.select_tasks(["g9_nothing"], None)))

    # MUTANT: the default reads the COMBINED registry - the state task 133 refused to
    # create, in which registering a scene puts it in the standing matrix command.
    def mutant_default(games, scenes):
        if games is None and not scenes:
            return list(wg.ALL_TASKS)
        return list(games or []) + list(scenes or [])

    rows.mutant("MUTANT: --games defaults to every key of the combined registry",
                bool([t for t in mutant_default(None, None)
                      if aspects.task_class(t) == "scene"]))

    # VARIANT: the default is still game-only and `--scenes` falls back to it, so naming
    # one scene builds the scene AND four games. Nothing refuses, the trial count is
    # plausible, and the run is four game trials larger than anyone asked for.
    def variant_fallback(games, scenes):
        return (list(games or []) or list(wg.P.TASKS)) + list(scenes or [])

    rows.mutant("VARIANT: --scenes falls back to the game default and adds to it",
                variant_fallback(None, [SCENE]) != [SCENE],
                f"selection was {variant_fallback(None, [SCENE])}")


# --------------------------------------------------------------------------- #
# P2 and P3 - the class, and the tier-2 instrument
# --------------------------------------------------------------------------- #


def check_instrument_guards(rows: Rows) -> None:
    print("\nP2/P3  evaluate.resolve_instrument - the class, and the tier-2 instrument")

    rows.check("a game resolves to the play-bot",
               ev.resolve_instrument(GAME) == ("game", "playbot"))
    rows.check("a scene resolves to the scene probe",
               ev.resolve_instrument(SCENE) == ("scene", "scene_probe"))
    rows.check("a task id whose class cannot be established is refused",
               refuses(lambda: ev.resolve_instrument("an-id-no-suite-defines")))
    rows.check("a task id SHAPED like one but defined nowhere is refused",
               refuses(lambda: ev.resolve_instrument("s9_invented")),
               "aspects' id-shape fallback classifies it, so the tier-2 map is what "
               "must refuse it")
    rows.check("every launchable task has a tier-2 instrument",
               set(wg.ALL_TASKS) <= set(ev.TIER2_INSTRUMENT),
               f"launchable and ungradeable: "
               f"{sorted(set(wg.ALL_TASKS) - set(ev.TIER2_INSTRUMENT))}")
    rows.check("every task with a tier-2 instrument can be launched",
               set(ev.TIER2_INSTRUMENT) <= set(wg.ALL_TASKS),
               f"gradeable and unlaunchable: "
               f"{sorted(set(ev.TIER2_INSTRUMENT) - set(wg.ALL_TASKS))}")

    # MUTANT: the scene is mapped to the play-bot. Without this guard the refusal would
    # be `BOTS[game]` raising `KeyError` in the middle of tier 2, after tier 1 has run -
    # and a fifth `BOTS` key would make it not raise at all.
    mutated = dict(ev.TIER2_INSTRUMENT)
    mutated[SCENE] = "playbot"
    with patched(ev, "TIER2_INSTRUMENT", mutated):
        rows.mutant("MUTANT: the scene is mapped to the play-bot",
                    refuses(lambda: ev.resolve_instrument(SCENE)))

    # VARIANT: the map is DERIVED from the task class instead of written out per task.
    # Every pairing is then correct by construction, `applicability` compares a value
    # with itself, and the guard becomes a check that cannot fail - rule 12's corollary
    # (task 113). The row asks whether the same mutation is still caught.
    derived = {t: ("scene_probe" if aspects.task_class(t) == "scene" else "playbot")
               for t in wg.ALL_TASKS}
    derived[SCENE] = "playbot"
    with patched(ev, "TIER2_INSTRUMENT", derived):
        rows.check("VARIANT: a class-derived map is still caught by applicability",
                   refuses(lambda: ev.resolve_instrument(SCENE)),
                   "TIER2_INSTRUMENT and aspects.INSTRUMENTS must be two statements "
                   "about each task, not one statement read twice")


# --------------------------------------------------------------------------- #
# P4 - the retired generalist judge
# --------------------------------------------------------------------------- #


def check_legacy_judge_guard(rows: Rows) -> None:
    print("\nP4  evaluate.assert_legacy_judge_allowed - 13 criteria about games")

    rows.check("the legacy judge is admitted on a game",
               not refuses(lambda: ev.assert_legacy_judge_allowed(GAME)))
    rows.check("the legacy judge is refused on a scene",
               refuses(lambda: ev.assert_legacy_judge_allowed(SCENE)))

    # AND ON THE PATH, not merely available: `judge.py`'s own CLI refuses a scene by
    # `choices=sorted(GAME_BRIEF)`, and `evaluate()` never goes through the CLI.
    # The refusal must also arrive BEFORE tier 1, or it has spent what it protects.
    reached: list[str] = []

    def spy(repo, **kw):
        reached.append("tier1")
        raise _Stop()

    with patched(static, "collect", spy):
        refused = refuses(lambda: ev.evaluate(FIXTURE, FIXTURE, SCENE, _tmp("p4"),
                                              run_judge=True))
    rows.check("evaluate() refuses --with-legacy-judge on a scene before tier 1 runs",
               refused and not reached, f"refused={refused} tier1_reached={bool(reached)}")

    # MUTANT: the guard is a no-op. Tier 1 is then reached on a scene that was about to
    # be handed to a game judge.
    reached.clear()
    with patched(ev, "assert_legacy_judge_allowed", lambda task: None):
        with patched(static, "collect", spy):
            with contextlib.suppress(_Stop, Exception):
                ev.evaluate(FIXTURE, FIXTURE, SCENE, _tmp("p4m"), run_judge=True)
    rows.mutant("MUTANT: the legacy-judge guard is a no-op", bool(reached))


# --------------------------------------------------------------------------- #
# P5 and P6 - the two argparse surfaces
# --------------------------------------------------------------------------- #


def check_cli_choices(rows: Rows) -> None:
    print("\nP5/P6  the CLI surfaces - what an operator can type at all")

    base = ["--submission", "x", "--starter", "y", "--out", "z", "--game"]
    rows.check(f"P5 evaluate.py --game {SCENE} is accepted",
               cli_accepts(EVAL / "judge" / "evaluate.py", [*base, SCENE]))
    rows.check(f"P5 evaluate.py --game {GAME} is accepted",
               cli_accepts(EVAL / "judge" / "evaluate.py", [*base, GAME]))
    rows.check("P5 evaluate.py --game g9_nothing is refused",
               not cli_accepts(EVAL / "judge" / "evaluate.py", [*base, "g9_nothing"]))
    cc = ["concurrency-check", "--submission", "x", "--starter", "y", "--game"]
    rows.check(f"P6 concurrency-check --game {SCENE} is accepted",
               cli_accepts(EVAL / "wholegame.py", [*cc, SCENE]))
    rows.check("P6 concurrency-check --game g9_nothing is refused",
               not cli_accepts(EVAL / "wholegame.py", [*cc, "g9_nothing"]))


def cli_accepts(script: Path, argv: list[str]) -> bool:
    """Does `script`'s parser accept `argv`? Read as a subprocess exit status.

    `--help` is appended so an ACCEPTED argv exits 0 without running anything; a rejected
    choice is `SystemExit(2)` from argparse before `--help` is reached. The status is read
    off `returncode` and not through a pipe - a pipeline reports the last stage's status
    (AGENTS.md rule 3).
    """
    r = subprocess.run([sys.executable, str(script), *argv, "--help"],
                       capture_output=True, text=True, check=False)
    return r.returncode == 0


# --------------------------------------------------------------------------- #
# What the runner hands tier 1, per class
# --------------------------------------------------------------------------- #


def check_tier1_shape(rows: Rows) -> None:
    print("\nP2  what evaluate() hands tier 1, per task class")

    seen: dict[str, Any] = {}

    def spy(repo, **kw):
        seen.update(kw)
        raise _Stop()

    for task, want_audio, want_ticks in (
            (GAME, GAME, None),
            (SCENE, None, scene_probe.SCENES[SCENE].ticks)):
        seen.clear()
        with patched(static, "collect", spy):
            with contextlib.suppress(_Stop):
                ev.evaluate(FIXTURE, FIXTURE, task, _tmp("t1"), audio=True)
        # THE SCENE'S EXPECTED `audio_game` IS `None`, WHICH IS ALSO WHAT AN EMPTY `seen`
        # RETURNS. Without this row, a `static.collect` that was never reached - a
        # refusal before tier 1, an `evaluate` that bound `collect` by value - reads as a
        # pass on the two rows below. Today the game iteration happens to catch it; the
        # scene iteration cannot, and it is the one the change is about.
        rows.check(f"{task}: tier 1 was reached at all", bool(seen),
                   "static.collect was never called, so the rows below are comparing "
                   "absent values and passing for the wrong reason")
        rows.check(f"{task}: audio_game={want_audio!r}",
                   seen.get("audio_game") == want_audio,
                   f"got {seen.get('audio_game')!r}. Every rendered scene prompt says "
                   f"the scene has no sound, so scoring one against the five tier-1 "
                   f"audio criteria deducts for compliance")
        rows.check(f"{task}: film_ticks={want_ticks!r}",
                   seen.get("film_ticks") == want_ticks,
                   f"got {seen.get('film_ticks')!r}. A scene's length is contracted; "
                   f"the game default films 240 ticks past the end of it")

    # MUTANT: the class test is dropped and a scene is filmed at the game default. Those
    # frames are also what `fidelity` and `motion` read, and their brief says the last
    # frame is late in the run.
    seen.clear()
    with patched(ev, "resolve_instrument", lambda t: ("game", "playbot")):
        with patched(static, "collect", spy):
            with contextlib.suppress(_Stop):
                ev.evaluate(FIXTURE, FIXTURE, SCENE, _tmp("t1m"), audio=True)
    rows.mutant("MUTANT: a scene graded as a game films at the game's tick count",
                seen.get("film_ticks") is None and seen.get("audio_game") == SCENE)


# --------------------------------------------------------------------------- #
# The capture path stays deterministic
# --------------------------------------------------------------------------- #


def check_capture_is_timeless(rows: Rows) -> None:
    print("\nThe capture path - no wall clock reaches a criterion")

    calls: list[list[str]] = []
    real_run = subprocess.run

    def spy_run(argv, *a, **kw):
        if isinstance(argv, list) and list(argv[:2]) == ["just", "film"]:
            calls.append([str(x) for x in argv])
        return real_run(argv, *a, **kw)

    with patched(scene_probe.subprocess, "run", spy_run):
        first = scene_probe.drive(scene_probe.SCENES[SCENE](), FIXTURE)

    ticks = str(scene_probe.SCENES[SCENE].ticks)
    rows.check("`just film` was invoked at all", bool(calls))
    # THE ARGV IS THE CONTRACT: recipe, seed, ticks, script, outdir. Six elements and no
    # seventh, because a seventh is where a duration, a frame budget or a deadline goes.
    rows.check("every invocation is `just film SEED TICKS - OUTDIR` and nothing more",
               all(len(c) == 6 and c[:2] == ["just", "film"] and c[4] == "-"
                   for c in calls),
               f"argv seen: {calls[:2]}")
    rows.check("the tick count is the scene's contracted length every time",
               {c[3] for c in calls} == {ticks},
               f"tick counts seen: {sorted({c[3] for c in calls})}")
    rows.check("the seed is the only thing that varies between invocations",
               len({c[2] for c in calls}) == 2,
               f"seeds seen: {sorted({c[2] for c in calls})}")

    second = scene_probe.drive(scene_probe.SCENES[SCENE](), FIXTURE)
    moved = [a["id"] for a, b in zip(first["criteria"], second["criteria"], strict=True)
             if (a["passed"], a["scored"], a["evidence"])
             != (b["passed"], b["scored"], b["evidence"])]
    rows.check("two drives of one submission return identical per-criterion verdicts",
               not moved, f"moved between drives: {moved}")

    # VARIANT: a criterion whose evidence carries a clock reading. Nothing raises, the
    # criterion still returns a verdict, and only a second drive can see it - which is
    # why the row above drives twice instead of reading the argv alone.
    def timed_scene():
        scene = scene_probe.SCENES[SCENE]()
        inner = scene.run

        def run(r):
            crits = inner(r)
            crits[0].evidence = f"{crits[0].evidence} t={time.monotonic():.6f}"
            return crits

        scene.run = run
        return scene

    a_run = scene_probe.drive(timed_scene(), FIXTURE)
    b_run = scene_probe.drive(timed_scene(), FIXTURE)
    rows.mutant("VARIANT: a criterion whose evidence carries a wall-clock reading",
                any(x["evidence"] != y["evidence"] for x, y
                    in zip(a_run["criteria"], b_run["criteria"], strict=True)))


# --------------------------------------------------------------------------- #
# The runner path, end to end
# --------------------------------------------------------------------------- #


def check_end_to_end(rows: Rows) -> tuple[float, dict[str, Any]] | None:
    print("\nThe runner path end to end, against judge/fixtures/ref_parallax")

    work = Path(tempfile.mkdtemp(prefix="scene-e2e-"))
    sub = work / "submission"
    shutil.copytree(FIXTURE, sub)
    t0 = time.monotonic()
    try:
        rec = ev.evaluate(sub, sub, SCENE, work / "out")
    # noqa BLE001: `evaluate` runs graders over a tree, so the exception set is open. A
    # failure here is the row's answer, not a crash to propagate.
    except Exception as exc:  # noqa: BLE001
        rows.check("the runner grades the reference scene",
                   False, f"{type(exc).__name__}: {exc}"[:300])
        shutil.rmtree(work, ignore_errors=True)
        return None
    wall = time.monotonic() - t0

    tier2 = rec.get("playbot") or {}
    rows.check("the record names the task class", rec.get("task_class") == "scene",
               f"got {rec.get('task_class')!r}")
    rows.check("the record names the tier-2 instrument",
               rec.get("tier2_instrument") == "scene_probe")
    rows.check("the tier-2 slot holds scene-probe output and says so",
               tier2.get("tier") == "scene_probe", f"got {tier2.get('tier')!r}")
    rows.check("the reference scene passes every scored criterion",
               tier2.get("total", 0) > 0 and tier2.get("passed") == tier2.get("total"),
               f"{tier2.get('passed')}/{tier2.get('total')}")
    rows.check("no tier-1 audio criterion appears in a scene grading",
               not [c for c in rec["programmatic"]["criteria"]
                    if c["id"].startswith("audio.")])
    rows.check("all three tier files are on disk",
               rec.get("tiers_complete") is True, str(rec.get("missing_tiers")))
    print(f"        graded in {wall:.1f}s - tier 2 "
          f"{tier2.get('passed')}/{tier2.get('total')}, measured twice: "
          f"{tier2.get('measured_twice')}")
    shutil.rmtree(work, ignore_errors=True)
    return wall, rec


def _tmp(prefix: str) -> Path:
    return Path(tempfile.mkdtemp(prefix=f"scene-{prefix}-"))


# --------------------------------------------------------------------------- #


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--paths", action="store_true",
                    help="print the guarded paths and exit")
    args = ap.parse_args(argv)

    print(f"{len(PATHS)} guarded routes from an operator's command to a grading "
          f"instrument or a judge pack:\n")
    print_paths()
    if args.paths:
        return 0

    if shutil.which("just") is None:
        print("\n`just` is not on PATH; the driving rows cannot run", file=sys.stderr)
        return 2

    rows = Rows()
    check_selection(rows)
    check_instrument_guards(rows)
    check_legacy_judge_guard(rows)
    check_cli_choices(rows)
    check_tier1_shape(rows)
    check_capture_is_timeless(rows)
    check_end_to_end(rows)

    print(f"\n{rows.n} rows, {rows.failures} failure(s)")
    print("PASS" if not rows.failures else "BROKEN")
    return 1 if rows.failures else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
