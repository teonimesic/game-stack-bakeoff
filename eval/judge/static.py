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
        info.update(mean_ink=0.0, max_ink=0.0, mean_frame_delta=0.0, sizes=[])
        return info
    bg = imgs[0].dominant_background()
    inks = [im.ink_coverage(bg) for im in imgs]
    deltas = [imgs[i].differs_from(imgs[i - 1]) for i in range(1, len(imgs))]
    info.update(
        sizes=sorted({(im.width, im.height) for im in imgs}),
        background=bg,
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
# Aligned with the floor the four render harnesses already use in their own
# "renders a non-empty frame" test (>0.001). Measured: the starter's placeholder marker
# covers 0.0015 of a 640x400 frame, so a tighter floor would be measuring "the
# placeholder is small" rather than "something is drawn".
INK_MIN, INK_MAX = 0.001, 0.85
DELTA_MIN = 0.0005


def collect(repo: Path, seed: int = 7, film_ticks: int = 900,
            env: dict[str, str] | None = None,
            run_coverage: bool = False,
            frames_out: Path | None = None,
            audio_game: str | None = None) -> dict[str, Any]:
    """`audio_game` adds the five tier-1 audio criteria for that game.

    It is None by default and must stay that way for any submission built before audio
    entered the task set: scoring those against audio criteria would measure the task
    change rather than the work (RUBRIC.md).
    """
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
        INK_MIN <= float(frame_info.get("mean_ink", 0.0)) <= INK_MAX,
        f"mean ink coverage {frame_info.get('mean_ink')} over {len(frames)} frames "
        f"(window {INK_MIN}-{INK_MAX}); per frame {frame_info.get('per_frame_ink')}")
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
