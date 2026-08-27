#!/usr/bin/env python3
"""The programmatic tier: everything a script can answer, answered by a script.

Design rule, from research/09 and from twelve separate occasions in this project where
a mechanism reported success and measured nothing: never ask a model something a script
can answer. Build status, gate status, lint, test counts, whether a frame is non-empty,
whether consecutive frames differ, simulation throughput and repository size are all
mechanical. They are collected here, before the judge is ever invoked, and the judge is
never shown them as a question.

Every check is fail-closed: a command that does not run scores FALSE, never "skipped".
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import png
from probe import Criterion, ProbeError, ProbeSession

# Reuse the battle-tested multi-runner parsers from the existing harness rather than
# writing a fifth set of regexes that can silently return (0, 0).
import importlib.util as _ilu

_RUNNER = Path(__file__).resolve().parent.parent / "runner.py"
_spec = _ilu.spec_from_file_location("_eval_runner", _RUNNER)
_runner = _ilu.module_from_spec(_spec)  # type: ignore[arg-type]
assert _spec and _spec.loader
# Register before exec: @dataclass resolves annotations via sys.modules, and a module
# that is mid-exec and unregistered makes it fail with a confusing AttributeError.
import sys as _sys  # noqa: E402

_sys.modules["_eval_runner"] = _runner
_spec.loader.exec_module(_runner)  # type: ignore[union-attr]
parse_test_counts = _runner.parse_test_counts
parse_skipped = _runner.parse_skipped

#: WHAT THE STORED CAPTURE SAMPLES, AND WHAT IT DROPS - defined ONCE, in `runner.py`, and
#: imported here. Both harnesses store command output: this one records what the GRADER ran,
#: `runner.py` records what the AGENT's own gate said. They had the same merged-buffer defect
#: (#100, then #114), and two truncation policies in one repository is how it recurred. The
#: rationale, the budgets and the measurement live in `runner.py` beside the function.
#:
#: These are aliases, not copies, and `runner_capture_selftest.py` asserts they are the same
#: function object. `_sample_stream` stays a module-level name here because `to_dict` looks it
#: up at call time, which is the seam `judge/capture_selftest.py`'s mutant replaces.
STREAM_HEAD_CHARS = _runner.STREAM_HEAD_CHARS
STREAM_TAIL_CHARS = _runner.STREAM_TAIL_CHARS
_sample_stream = _runner._sample_stream
capture_fields = _runner.capture_fields
stored_stdout = _runner.stored_stdout
stored_output = _runner.stored_output


@dataclass
class Cmd:
    name: str
    argv: list[str]
    code: int
    seconds: float
    #: EXACTLY what the child wrote, per stream. Which stream a line came from is a
    #: recorded fact here, not something a reader has to infer from a merged buffer.
    out: str = ""
    err: str = ""
    #: The HARNESS's own words - a timeout, or a binary that could not be spawned. Kept
    #: apart from the two streams so nothing the harness says is ever attributed to the
    #: command, and so a timeout no longer erases what the command had already printed.
    note: str = ""
    #: Peak resident set of the largest process in the command's tree, in MiB, and the
    #: user+system CPU the whole tree consumed, in seconds. `None` when the command
    #: could not be spawned at all - never 0.0, because a zero here is indistinguishable
    #: from a process that really used nothing (AGENTS.md rule 3's sibling).
    peak_rss_mb: float | None = None
    cpu_seconds: float | None = None

    @property
    def tail(self) -> str:
        """The pre-#100 in-memory view: stdout then stderr, or the harness's note alone.

        The test-count and coverage parsers read this, and `verify.green`'s evidence is cut
        from it. It is preserved BYTE FOR BYTE - including a timeout replacing the output
        rather than appending to it - so that repairing the stored record cannot move a
        single criterion. The separated streams are what gets STORED; this is what gets
        PARSED.
        """
        return self.note if self.note else self.out + self.err

    def to_dict(self) -> dict[str, Any]:
        # `sample=_sample_stream` is a call-time lookup of this module's global, so a mutant
        # replacing `static._sample_stream` is still caught. The keys and the recorded
        # lengths come from `runner.capture_fields`, so a grader record and a spec-change
        # record are the same shape by construction rather than by agreement.
        return {"name": self.name, "argv": self.argv, "exit": self.code,
                "seconds": round(self.seconds, 1),
                **capture_fields(self.out, self.err, self.note, sample=_sample_stream),
                "peak_rss_mb": self.peak_rss_mb, "cpu_seconds": self.cpu_seconds}


#: `ru_maxrss` is BYTES on macOS/BSD and KILOBYTES on Linux. There is no portable
#: constant for this, and getting it wrong is a factor of 1024 that still produces a
#: number in a believable range - the most dangerous shape a broken measurement takes.
#: `judge/rusage_selftest.py` asserts the resulting figure against a child that
#: allocates a known 400 MiB, so this is checked rather than trusted.
_MAXRSS_TO_MIB = 1.0 / (1024 * 1024) if sys.platform == "darwin" else 1.0 / 1024


def run(repo: Path, name: str, argv: list[str], timeout_s: int = 1800,
        env: dict[str, str] | None = None) -> Cmd:
    """Run one command and record what it COST as well as what it said.

    `subprocess.run` cannot report resource usage, so the wait is done with `os.wait4`.
    That matters for scope, not for tidiness: `just film` is never the process that
    renders anything - it is `just`, then a shell, then cargo/node/Unity/godot - and
    BSD `wait4` folds a reaped descendant's usage into its parent's, so the figure
    covers the tree. A measurement of `just` alone would be a near-constant on all four
    arms and would look exactly like a working one. `judge/rusage_selftest.py` proves
    the grandchild case rather than asserting it.

    Everything the previous implementation guaranteed is preserved: the child's exit
    code, `Cmd.tail` reading stdout followed by stderr, 124 on timeout, 127 when the
    binary is not there. What changed with #100 is that the two streams are kept APART
    in the record instead of being concatenated and truncated as one buffer.
    """
    import os
    import queue as _queue
    import signal
    import threading as _th

    e = dict(os.environ)
    if env:
        e.update(env)
    t0 = time.monotonic()
    try:
        p = subprocess.Popen(argv, cwd=repo, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, text=True, env=e,
                             start_new_session=True)   # its own group, so it can be killed whole
    except OSError as ex:
        return Cmd(name, argv, 127, time.monotonic() - t0, note=f"could not run: {ex}")

    bufs: dict[str, str] = {"out": "", "err": ""}

    def drain(key: str, stream: Any) -> None:
        try:
            bufs[key] = stream.read() or ""
        except (OSError, ValueError):        # the pipe died with the process
            pass

    readers = [_th.Thread(target=drain, args=("out", p.stdout), daemon=True),
               _th.Thread(target=drain, args=("err", p.stderr), daemon=True)]
    for r in readers:
        r.start()

    reaped: "_queue.Queue[tuple[int, Any]]" = _queue.Queue()

    def waiter() -> None:
        try:
            _pid, status, ru = os.wait4(p.pid, 0)
            reaped.put((status, ru))
        except (ChildProcessError, OSError):
            reaped.put((0, None))

    _th.Thread(target=waiter, daemon=True).start()

    timed_out = False
    try:
        status, ru = reaped.get(timeout=timeout_s)
    except _queue.Empty:
        timed_out = True
        try:
            os.killpg(p.pid, signal.SIGKILL)   # the whole group, not just `just`
        except OSError:
            pass
        try:
            status, ru = reaped.get(timeout=60)
        except _queue.Empty:
            status, ru = 0, None

    # Tell Popen the child is already reaped, so its own waitpid never runs and cannot
    # raise or hang in __del__.
    try:
        p.returncode = os.waitstatus_to_exitcode(status)
    except ValueError:
        p.returncode = -1
    for r in readers:
        r.join(timeout=30)
    for s in (p.stdout, p.stderr):
        try:
            if s:
                s.close()
        except OSError:
            pass

    # A timeout is the HARNESS speaking, so it goes in `note`. Whatever the child managed
    # to print before it hung stays in the streams: it is the only account of where the
    # command got to, and the old capture threw it away in favour of one sentence. The
    # parsers are unaffected - `Cmd.tail` still returns the note alone in this case.
    code = 124 if timed_out else p.returncode
    note = f"TIMEOUT after {timeout_s}s" if timed_out else ""

    peak = cpu = None
    if ru is not None:
        peak = round(ru.ru_maxrss * _MAXRSS_TO_MIB, 1)
        cpu = round(ru.ru_utime + ru.ru_stime, 2)
    return Cmd(name, argv, code, time.monotonic() - t0,
               out=bufs["out"], err=bufs["err"], note=note,
               peak_rss_mb=peak, cpu_seconds=cpu)


# --------------------------------------------------------------------------- #

CODE_EXT = {".rs", ".ts", ".tsx", ".js", ".mjs", ".cs", ".gd", ".shader", ".wgsl"}
SKIP_DIRS = {".git", "target", "node_modules", "dist", "Library", "Temp", "obj",
             ".godot", ".venv", "coverage", "artifacts", "build", "__pycache__"}


def repo_stats(repo: Path) -> dict[str, Any]:
    by_ext: dict[str, dict[str, int]] = {}
    total_files = total_lines = 0
    for p in repo.rglob("*"):
        if not p.is_file():
            continue
        if any(part in SKIP_DIRS for part in p.relative_to(repo).parts):
            continue
        ext = p.suffix.lower()
        if ext not in CODE_EXT:
            continue
        try:
            n = sum(1 for _ in p.open("rb"))
        except OSError:
            continue
        d = by_ext.setdefault(ext, {"files": 0, "lines": 0})
        d["files"] += 1
        d["lines"] += n
        total_files += 1
        total_lines += n
    return {"code_files": total_files, "code_lines": total_lines, "by_ext": by_ext}


def film(repo: Path, seed: int, ticks: int, env: dict[str, str] | None = None
         ) -> tuple[Cmd, list[Path], Path]:
    outdir = Path(tempfile.mkdtemp(prefix="film-"))
    cmd = run(repo, "film", ["just", "film", str(seed), str(ticks), "-", str(outdir)],
              timeout_s=900, env=env)
    frames = sorted(outdir.glob("*.png"))
    return cmd, frames, outdir


#: Every criterion computed from the pixels, and WHY it survives a change of frame size.
#:
#: #59 established the boundary: more pixels is more opportunity for distinct colours,
#: more ink and more change, so a RAW COUNT is not comparable across geometries and a
#: DENSITY is. Submissions choose their own frame size - only one stack's `film` recipe
#: passes an explicit resolution, and a portrait well for a falling-block game is a
#: legitimate design choice, not a defect. So the harness does not force a geometry; it
#: guarantees instead that nothing it MEASURES depends on one.
#:
#: The gate is `assert_frame_criteria_geometry_safe()`. It discovers frame-derived
#: criteria from this module's own source rather than from this dict, so a new one that
#: nobody registers FAILS rather than passing unnoticed.
FRAME_CRITERION_MEASURES = {
    "render.frames": "count_of_files",   # counts PNGs on disk, not pixels
    "render.nonempty": "density",        # ink_coverage = lit pixels / total pixels
    "render.animates": "density",        # fraction of pixels differing between frames
}
GEOMETRY_SAFE_MEASURES = {"density", "count_of_files"}


def assert_frame_criteria_geometry_safe() -> list[str]:
    """Refuse UNSOUND MEASURES rather than unusual submissions.

    Returns a list of problems; empty means every frame-derived criterion is invariant to
    capture geometry. Discovery is mechanical: it reads this module's source for `add(...)`
    calls whose condition touches `frame_info` or `frames`, so the registry above cannot
    silently fall out of date - the failure mode of every hand-maintained list.
    """
    import inspect
    import re as _re
    src = inspect.getsource(sys.modules[__name__])
    body = src[src.index("def deterministic("):] if "def deterministic(" in src else src
    found = set()
    for m in _re.finditer(r'add\(\s*"([a-z]+\.[a-z_]+)"\s*,(.{0,240}?)\)\s*\n', body,
                          _re.S):
        cid, expr = m.group(1), m.group(2)
        if "frame_info" in expr or _re.search(r"\bframes\b", expr):
            found.add(cid)
    problems = []
    for cid in sorted(found):
        kind = FRAME_CRITERION_MEASURES.get(cid)
        if kind is None:
            problems.append(
                f"{cid} is computed from frames but is not in FRAME_CRITERION_MEASURES. "
                f"Declare how it behaves when the frame size changes: a density or a "
                f"file count is safe, a raw pixel/colour count is not (#59).")
        elif kind not in GEOMETRY_SAFE_MEASURES:
            problems.append(
                f"{cid} is declared {kind!r}, which is geometry-sensitive. Submissions "
                f"choose their own frame size, so this criterion would score shape "
                f"rather than content (#59).")
    for cid in sorted(set(FRAME_CRITERION_MEASURES) - found):
        problems.append(
            f"{cid} is registered as frame-derived but no longer appears to be. Remove "
            f"it, or the registry is describing code that does not exist (#38).")
    return problems


def analyse_frames(frames: list[Path]) -> dict[str, Any]:
    """Non-empty and animating - the two things pixels can prove without a model."""
    info: dict[str, Any] = {"count": len(frames), "errors": []}
    imgs: list[png.Image] = []
    for f in frames:
        try:
            imgs.append(png.read(f))
        # noqa BLE001, deliberately blind: these frames were produced by a submission,
        # so "what can go wrong reading one" is not a set this file gets to enumerate.
        # A corrupt PNG is a real finding about the submission, not a crash of the
        # grader -- and it is RECORDED per frame in `errors`, then `if not imgs` turns a
        # whole unreadable set into zeros with the reasons attached rather than silence.
        except Exception as e:  # noqa: BLE001
            info["errors"].append(f"{f.name}: {e}")
    if not imgs:
        info.update(mean_ink=0.0, max_ink=0.0, mean_frame_delta=0.0, sizes=[],
                    flat_frames=0)
        return info
    # ONE background for every frame, taken from FRAME 0. That is what `mean_ink` has
    # always measured and it is not changed here: switching to a per-frame background
    # moves 8 of the 67 stored frame sets, one of them 0.60285 -> 0.04481, which is a
    # re-measurement of the corpus and needs its own derivation (`tasks/169`).
    bg = imgs[0].dominant_background()
    inks = [im.ink_coverage(bg) for im in imgs]
    # WHICH FRAMES HOLD ONE COLOUR AND NOTHING ELSE, asked per frame against each
    # frame's OWN mode - the question `mean_ink` structurally cannot answer, and the
    # one `render.nonempty` is actually about. 0 of the 67 stored frame sets contain a
    # flat frame, and the worst-case cost over those sets is 0.46 s.
    flat = sum(1 for im in imgs if im.is_flat())
    deltas = [imgs[i].differs_from(imgs[i - 1]) for i in range(1, len(imgs))]
    info.update(
        sizes=sorted({(im.width, im.height) for im in imgs}),
        background=bg,
        flat_frames=flat,
        mean_ink=round(sum(inks) / len(inks), 5),
        max_ink=round(max(inks), 5),
        per_frame_ink=[round(v, 5) for v in inks],
        mean_frame_delta=round(sum(deltas) / len(deltas), 5) if deltas else 0.0,
        per_frame_delta=[round(v, 5) for v in deltas],
    )
    return info


def probe_throughput(repo: Path, env: dict[str, str] | None = None,
                     ticks: int = 400) -> dict[str, Any]:
    try:
        t0 = time.monotonic()
        with ProbeSession(repo=repo, seed=7, env=env) as s:
            start = time.monotonic()
            s.idle(ticks)
            elapsed = time.monotonic() - start
        return {"ok": True, "ticks": ticks,
                "ticks_per_second": round(ticks / elapsed, 1) if elapsed else None,
                "startup_s": round(start - t0, 2)}
    except ProbeError as e:
        return {"ok": False, "error": str(e)[:400]}


# --------------------------------------------------------------------------- #

CRITERIA = [
    ("build.compiles", "Does the project build / type-check cleanly?"),
    ("verify.green", "Does the repository's own gate, `just verify`, pass?"),
    ("lint.clean", "Does the linter pass with no findings?"),
    ("tests.exist", "Does the project ship more than a token number of its own tests?"),
    ("tests.green", "Do all of the project's own tests pass, with none skipped?"),
    ("render.frames", "Does the game render frames at all?"),
    ("render.nonempty", "Do the rendered frames contain something other than a blank "
                        "background?"),
    ("render.animates", "Do consecutive frames of a played run differ, i.e. is "
                        "something actually moving?"),
    ("probe.responds", "Does the headless probe start and advance the simulation?"),
]

MIN_OWN_TESTS = 8          # the starter already ships more than this
DELTA_MIN = 0.0005

#: `render.nonempty`'s FLOOR, and the derivation for why there is NO ceiling.
#:
#: THE FLOOR IS A PROPERTY OF THE STARTER. It is the floor the 4 render harnesses
#: already use in their own `renders a non-empty frame` test, and the starter's
#: placeholder marker covers 0.0015 of a 640x400 frame, so anything tighter measures
#: "the placeholder is small" rather than "something is drawn". Every task class is
#: built from those same 4 starters, so it transfers - which is why
#: `TIER1_BOUND_POPULATION` files this criterion under `starter`.
#:
#: THERE IS NO CEILING, AND THE REASON IS THAT `mean_ink` CANNOT CARRY ONE.
#: `ink_coverage` counts pixels differing from ONE reference colour, and
#: `analyse_frames` takes that colour from FRAME 0's mode. So the quantity is departure
#: from the first frame's modal colour - a property of the PALETTE, not of how much was
#: drawn - and it runs backwards from what a ceiling would want:
#:
#:   - a solid flood in frame 0's own colour, the archetypal "the render broke and
#:     filled the screen", measures 0.0. Measured on solid white, magenta and black:
#:     0.0 each. Every one hits the FLOOR.
#:   - what drives the number toward 1.0 is the ABSENCE of a modal region - a gradient,
#:     a dither, a wide palette. A night platformer over a gradient sky reads 0.881
#:     with its subject drawn correctly on top.
#:
#: AND THE CEILING WAS NOT A BLANK-FRAME GUARD EITHER, which is the measurement that
#: settles it rather than the argument. 12 frames each holding a single colour have
#: drawn nothing, and `mean_ink` reads:
#:
#:   all one colour                  0.0       floor FAIL   0.001-0.85 FAIL
#:   frame 0, then 11 of another     0.91667   floor PASS   0.001-0.85 FAIL
#:   alternating 2 colours           0.5       floor PASS   0.001-0.85 PASS
#:   6 of one, then 6 of another     0.5       floor PASS   0.001-0.85 PASS
#:
#: The same blank render lands anywhere on the scale depending only on how its colours
#: are ARRANGED, and 0.001-0.85 admitted 2 of the 3 non-zero arrangements. A bound on
#: this quantity was never the guard, so removing the ceiling is not what opens that
#: door - `nonempty_verdict` asks the question directly instead, via `flat_frames`, and
#: fails all 4 rows above. 0 of the 67 stored frame sets contain a flat frame, so the
#: added half moves no stored verdict.
#:
#: WHAT 0.85 DID, over every grading this project has stored:
#:
#:   python3 judge/ink_window_control.py --runs-root <main checkout>/eval/runs
#:
#: 69 submissions, the most recent grading of each from 85 on disk. 4 `render.nonempty`
#: failures. The 2 floor firings are `wg-arena3d`'s rust cells at **0 frames**, which
#: `render.frames` reports in the same record. Among the 2 CEILING firings: 0 true
#: positives and 2 false negatives, both submissions that drew what they were asked to
#: draw - `wg-scene-s1ts` `s1_parallax__ts__t0` at 0.966 (repaired by `tasks/163`) and
#: `wg-g4c` `g4_platformer__godot__t1` at 0.881, which scored 1.000 on tier 2 (#123).
#: Tier 1 GATES, so a false negative here does not cost a fraction of a score, it stops
#: a correct submission being scored at all.
#:
#: AND THE 68 GAME VALUES ARE A CONTINUUM, not 2 populations with a gap between them:
#: 0.679, 0.703, 0.736, 0.772, 0.828, 0.881 are the top 6, the largest gap among them
#: is 0.053, and all 7 of the highest are `g4_platformer` - the one game whose
#: background scrolls across the whole frame. 0.85 landed inside that continuum, so what
#: it separated was a TASK, not a quality.
#:
#: 0.85 was not moved to admit the submission that exposed it; it was removed, because
#: no number on this measure means "too full". `judge/ink_window_control.py` keeps the
#: 4 blank-render arrangements as rows and the restored 0.85 as a mutant.
INK_FLOOR = 0.001
INK_FLOOR_WHY = ("the 4 render harnesses' own `renders a non-empty frame` floor; "
                 "the starter's placeholder marker covers 0.0015 of a 640x400 frame")

#: The task classes tier 1 will grade, closed. `collect` refuses anything else BEFORE
#: spending a toolchain: the class chooses the tick count and the audio criterion set as
#: well as reaching the stored record, so a class nobody registered has already made
#: those wrong by the time a criterion is evaluated. `judge/ink_window_control.py`
#: asserts this set equals the one `judge/aspects.py` recognises rather than promising
#: it in a comment (rule 12).
TASK_CLASSES = ("game", "scene")


def assert_task_class(task_class: str) -> str:
    """Return `task_class`, or raise if tier 1 does not grade that class.

    FAILS CLOSED on a class it cannot place rather than falling back to `"game"`. A
    fallback here is invisible: it grades on somebody else's contract and reports a
    plausible verdict, at a tier that GATES.
    """
    if task_class not in TASK_CLASSES:
        raise ValueError(
            f"{task_class!r} is not a task class tier 1 grades. "
            f"Known: {list(TASK_CLASSES)}. Refusing rather than grading it as a game: "
            f"the class picks the capture length and the audio criterion set, and a "
            f"wrong one fails a correct submission at a tier that GATES.")
    return task_class


def nonempty_verdict(frame_info: dict[str, Any],
                     n_frames: int) -> tuple[bool, str]:
    """`(passed, evidence)` for `render.nonempty`: a FLOOR and an ALL-FLAT test.

    Separate from `collect` so the decision can be driven without a toolchain -
    `judge/ink_window_control.py` pins it in both directions on real pixels.

    It takes no task class, and that is the change `tasks/168` made: both halves are
    properties of the four starters, so they are the same for every class. The evidence
    names the floor rather than a window, because a reader who sees a range printed will
    look for the number that closed it.

    TWO HALVES, because `mean_ink` alone cannot answer the criterion's own question.
    A frame set every one of whose frames holds a single colour has drawn nothing, and
    its `mean_ink` is 0.0, 0.5 or 0.91667 depending only on how those colours are
    arranged against frame 0's - so it is asked directly instead.

    `flat_frames` ABSENT IS A THIRD VALUE and is not zero: every record written before
    2026-08-27 lacks it, and for those the verdict is the floor alone. Re-grading a
    stored record therefore asks the half its record can answer and says so, rather than
    reading a missing count as "none were flat".
    """
    mean_ink = float(frame_info.get("mean_ink", 0.0))
    flat = frame_info.get("flat_frames")
    all_flat = flat is not None and n_frames > 0 and flat >= n_frames
    where = (f"{flat} of {n_frames} frames hold one colour and nothing else"
             if flat is not None else
             "flat_frames not measured on this record (pre-2026-08-27), so the "
             "all-flat half was not asked")
    return (mean_ink >= INK_FLOOR and not all_flat), (
        f"mean ink coverage {frame_info.get('mean_ink')} over {n_frames} frames "
        f"(floor {INK_FLOOR}, no ceiling: {INK_FLOOR_WHY}); {where}; "
        f"per frame {frame_info.get('per_frame_ink')}")


#: Every tier-1 criterion, and the POPULATION the bound it applies was calibrated on.
#:
#: THE CENSUS `tasks/163` ASKED FOR, kept as code so it is answered again every time a
#: criterion is added rather than once by whoever happened to look. The question is
#: *is this bound a property of the artifact, or of games?* - and it is worth asking of
#: all 14, because the one criterion whose answer was "of games" had gone 69 gradings
#: without anybody asking.
#:
#: The 5 values are a CLOSED class, and `no_bound` is a real answer rather than a gap:
#: a criterion that reads an exit status has nothing to calibrate and cannot acquire a
#: class-dependence later without acquiring a number first.
#:
#:   no_bound          reads an exit status, a count of files or a boolean. No number.
#:   starter           a property of the 4 starters, which BOTH classes are built from.
#:   capture_contract  a property of `just film`, which is identical in both classes.
#:   audio_signal      a property of digital audio (dBFS, spectral similarity). The
#:                     audio criteria are not asked of a scene at all (`tasks/156`).
#:   task_class        differs by class. The bound lives in a per-class table, and
#:                     `TASK_CLASS_BOUND_TABLES` names it.
#:
#: The answer today: 8 carry no bound and 6 carry one that transfers. NOTHING is
#: class-dependent, and `task_class` stays in the closed list with 0 members on purpose
#: - it is the value a future bound declares, and the gate below is what makes declaring
#: it safe. `render.nonempty` held it until `tasks/168` removed the ink ceiling: the
#: ceiling was the class-dependent half, and the floor it left behind is a property of
#: the same 4 starters both classes are built from, exactly like `tests.exist`.
BOUND_POPULATIONS = ("no_bound", "starter", "capture_contract", "audio_signal",
                     "task_class")

TIER1_BOUND_POPULATION: dict[str, str] = {
    "build.compiles": "no_bound",       # `just check` exit status
    "verify.green": "no_bound",         # `just verify` exit status
    "lint.clean": "no_bound",           # `just lint` exit status
    "tests.exist": "starter",           # MIN_OWN_TESTS; every starter ships more
    "tests.green": "no_bound",          # exit status plus its own reported counts
    "render.frames": "no_bound",        # PNGs on disk, floor 0
    "render.nonempty": "starter",       # INK_FLOOR; the same 4 render harnesses' floor
    "render.animates": "capture_contract",   # DELTA_MIN; a scene is a timed sequence
    "probe.responds": "no_bound",       # the probe answered, or it did not
    "audio.manifest": "no_bound",       # `just audio-manifest` exit status plus JSON
    "audio.files_exist": "no_bound",    # the file decoded, or it did not
    "audio.not_silent": "audio_signal",     # SILENCE_RMS / SILENCE_PEAK, in dBFS
    "audio.distinct": "audio_signal",       # SAME_SOUND_COSINE over spectra
    "audio.music_loops": "audio_signal",    # MUSIC_MIN_SECONDS
}

#: The per-class tables, keyed by the criterion that reads them. Every id declared
#: `task_class` above must appear here and nothing else may, so the registry cannot
#: claim a class-dependence that no table implements.
#:
#: EMPTY since `tasks/168`, which is a state and not a gap: no tier-1 bound differs by
#: class today. The gate below still asks the question of both directions, so the first
#: criterion to declare `task_class` without a table fails rather than promising one.
TASK_CLASS_BOUND_TABLES: dict[str, dict[str, Any]] = {}


def assert_tier1_bounds_declared() -> list[str]:
    """Refuse an UNDECLARED BOUND rather than an unusual task class.

    Returns a list of problems; empty means every tier-1 criterion has answered
    *which population was your bound calibrated on?* Discovery is mechanical and comes
    from the two `CRITERIA` lists that define the tier, so a criterion added without an
    answer FAILS - the failure mode of every hand-maintained list.

    The audio half is imported lazily: `audio` decodes with `ffmpeg` and this function
    is called from `precampaign_smoke.py`, where dragging a decoder in to read a list
    of strings would make a documentation gate depend on a media toolchain.
    """
    ids = [cid for cid, _ in CRITERIA]
    try:
        import audio as _audio
        ids += [cid for cid, _ in _audio.CRITERIA]
    except Exception as e:  # noqa: BLE001 - see the docstring; an import is not a verdict
        return [f"judge/audio.py could not be imported, so 5 of the 14 tier-1 criteria "
                f"were not asked the question: {type(e).__name__}: {e}"]
    problems = []
    for cid in ids:
        pop = TIER1_BOUND_POPULATION.get(cid)
        if pop is None:
            problems.append(
                f"{cid} is a tier-1 criterion and is not in TIER1_BOUND_POPULATION. "
                f"State which population its bound was calibrated on, one of "
                f"{list(BOUND_POPULATIONS)}. Tier 1 GATES, so a bound calibrated on "
                f"one task class refuses a correct member of another (tasks/163).")
        elif pop not in BOUND_POPULATIONS:
            problems.append(
                f"{cid} declares population {pop!r}, which is not one of "
                f"{list(BOUND_POPULATIONS)}. The list is closed on purpose: an open "
                f"vocabulary is an enumeration in disguise.")
    for cid in sorted(set(TIER1_BOUND_POPULATION) - set(ids)):
        problems.append(
            f"{cid} is registered in TIER1_BOUND_POPULATION and is no longer a tier-1 "
            f"criterion. Remove it, or the registry describes code that does not "
            f"exist (#38).")
    declared = {c for c, p in TIER1_BOUND_POPULATION.items() if p == "task_class"}
    if declared != set(TASK_CLASS_BOUND_TABLES):
        problems.append(
            f"the criteria declared 'task_class' are {sorted(declared)} but the "
            f"per-class tables are {sorted(TASK_CLASS_BOUND_TABLES)}. A declared "
            f"class-dependence with no table is a promise nothing keeps.")
    for cid, table in TASK_CLASS_BOUND_TABLES.items():
        missing = sorted(set(TASK_CLASSES) - set(table))
        if missing:
            problems.append(
                f"{cid}'s per-class table has no entry for {missing}. Both task "
                f"classes are graded by tier 1 (eval/SCENES.md).")
    return problems


def collect(repo: Path, seed: int = 7, film_ticks: int = 900,
            env: dict[str, str] | None = None,
            run_coverage: bool = False,
            frames_out: Path | None = None,
            audio_game: str | None = None,
            task_class: str = "game") -> dict[str, Any]:
    """`audio_game` adds the five tier-1 audio criteria for that game.

    It is None by default and must stay that way for any submission built before audio
    entered the task set: scoring those against audio criteria would measure the task
    change rather than the work (RUBRIC.md).

    `task_class` is the runner's fact, handed over the way `film_ticks` and
    `audio_game` already are - and it governs both of those: a scene is filmed at its
    own contracted tick count and is asked none of the audio criteria. A tier that
    re-derived the class from a task id would be a second place for the two to
    disagree. `eval/tools/scene_runner_control.py` pins that the runner passes all
    three, and it is the only thing that can: since `tasks/168` NO tier-1 bound differs
    by class, so nothing downstream of here would read differently if the class were
    wrong. That is exactly why the refusal is at the door.
    """
    # Refuse an unplaceable class BEFORE spending a toolchain. Fail-closed: by the time
    # a criterion is evaluated, a class nobody registered has already chosen the wrong
    # capture length and the wrong audio criterion set.
    assert_task_class(task_class)
    cmds: list[Cmd] = []

    c_check = run(repo, "check", ["just", "check"], timeout_s=1800, env=env)
    cmds.append(c_check)
    c_verify = run(repo, "verify", ["just", "verify"], timeout_s=2400, env=env)
    cmds.append(c_verify)
    c_lint = run(repo, "lint", ["just", "lint"], timeout_s=1800, env=env)
    cmds.append(c_lint)
    c_test = run(repo, "test", ["just", "test"], timeout_s=2400, env=env)
    cmds.append(c_test)

    passed_n, total_n = parse_test_counts(c_test.tail)
    skipped_n = parse_skipped(c_test.tail)

    cov: dict[str, Any] = {"run": False}
    if run_coverage:
        c_cov = run(repo, "coverage", ["just", "coverage"], timeout_s=2400, env=env)
        cmds.append(c_cov)
        m = re.findall(r"(\d+(?:\.\d+)?)\s*%", c_cov.tail)
        cov = {"run": True, "exit": c_cov.code,
               "percentages_seen": [float(x) for x in m[-5:]]}

    c_film, frames, outdir = film(repo, seed, film_ticks, env)
    cmds.append(c_film)
    frame_info = analyse_frames(frames)
    thru = probe_throughput(repo, env)

    crit: list[Criterion] = []

    def add(cid: str, ok: bool, ev: str) -> None:
        crit.append(Criterion(cid, dict(CRITERIA)[cid], ok, ev))

    add("build.compiles", c_check.code == 0,
        f"`just check` exit {c_check.code} in {c_check.seconds:.0f}s")
    # Both stream ends, labelled. One merged tail meant this criterion's justification
    # ended with the gate's own verdict on the arms whose gates are quiet and mid-listing
    # on the one whose test runner is loud - a difference in KIND of evidence, by stack,
    # that nobody chose (#100).
    add("verify.green", c_verify.code == 0,
        f"`just verify` exit {c_verify.code} in {c_verify.seconds:.0f}s; "
        f"stdout tail: {c_verify.out[-200:].strip()!r}; "
        f"stderr tail: {c_verify.err[-200:].strip()!r}")
    add("lint.clean", c_lint.code == 0,
        f"`just lint` exit {c_lint.code}")
    add("tests.exist", total_n >= MIN_OWN_TESTS,
        f"{total_n} tests discovered by `just test` (floor {MIN_OWN_TESTS})")
    add("tests.green", c_test.code == 0 and total_n > 0 and skipped_n == 0
        and passed_n == total_n,
        f"`just test` exit {c_test.code}: {passed_n}/{total_n} passed, "
        f"{skipped_n} skipped")
    add("render.frames", len(frames) > 0 and not frame_info.get("errors"),
        f"`just film` exit {c_film.code}, produced {len(frames)} PNGs; "
        f"decode errors: {frame_info.get('errors') or 'none'}")
    add("render.nonempty",
        *nonempty_verdict(frame_info, len(frames)))
    add("render.animates", float(frame_info.get("mean_frame_delta", 0.0)) > DELTA_MIN,
        f"mean fraction of pixels changing between consecutive frames "
        f"{frame_info.get('mean_frame_delta')} (floor {DELTA_MIN})")
    add("probe.responds", bool(thru.get("ok")),
        f"probe throughput: {thru}")

    audio_info: dict[str, Any] = {"applies": False}
    if audio_game is not None:
        import audio as audio_mod

        audio_info = audio_mod.collect(repo, audio_game, env)
        audio_info["applies"] = True
        for c in audio_info["criteria"]:
            crit.append(Criterion(c["id"], c["question"], c["passed"], c["evidence"]))

    if frames_out is not None:
        # The judge sees the same frames the pixel checks saw - one capture, two
        # consumers, so the tiers cannot disagree about what was on screen.
        shutil.rmtree(frames_out, ignore_errors=True)
        frames_out.mkdir(parents=True, exist_ok=True)
        for f in frames:
            shutil.copy(f, frames_out / f.name)
    shutil.rmtree(outdir, ignore_errors=True)
    npass = sum(1 for c in crit if c.passed)
    return {
        "tier": "programmatic",
        "passed": npass,
        "total": len(crit),
        "score": npass / len(crit),
        "criteria": [c.to_dict() for c in crit],
        "commands": [c.to_dict() for c in cmds],
        "tests": {"passed": passed_n, "total": total_n, "skipped": skipped_n},
        "coverage": cov,
        "audio": audio_info,
        "frames": frame_info,
        "throughput": thru,
        "repo": repo_stats(repo),
    }


if __name__ == "__main__":
    import sys
    print(json.dumps(collect(Path(sys.argv[1]).resolve()), indent=2))
