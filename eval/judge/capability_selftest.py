#!/usr/bin/env python3
"""Controls for `capability.py`. Run: `python3 judge/capability_selftest.py`.

WHAT THIS FILE EXISTS TO PREVENT. `capability.py`'s whole claim is *"every field it
declares is reportable by all four arms"*. A claim like that is exactly the shape this
project keeps shipping and then retracting: a check that runs, reports success, and
could not have failed.

So the gate `no_stack_correlated_gap` gets all three controls, per criterion:

  positive     a field populated everywhere      -> GREEN
  MUTANT       the mechanism removed: one stack never reports the field -> RED
  VARIANT      an input the check could mishandle: the field is missing on
               individual submissions, spread across every stack, because their
               `film` failed                     -> GREEN, because that is data
               about a submission and not a gap in the field

The variant is the half that matters (AGENTS.md rule 15). A gate that flags every
absence is useless here: `film` genuinely fails on real submissions, and a gate that
cannot tell "this stack cannot report X" from "this submission did not get far enough
to have an X" would either fire constantly or be switched off.

Exit code is 0 only if every expectation holds.
"""

from __future__ import annotations

import json
import struct
import sys
import tempfile
import zlib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import capability  # noqa: E402

FAILURES: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  -- {detail}" if detail else ""))
    if not ok:
        FAILURES.append(name)


# --------------------------------------------------------------------------- #
# fixtures
# --------------------------------------------------------------------------- #

def png_bytes(width: int, height: int) -> bytes:
    """A minimal valid 8-bit RGB PNG. `capability` reads geometry from the header, but
    it must read a REAL file, so the fixture is a real file."""
    raw = b"".join(b"\x00" + b"\x20\x40\x60" * width for _ in range(height))
    def chunk(tag: bytes, data: bytes) -> bytes:
        return (struct.pack(">I", len(data)) + tag + data
                + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


def programmatic(*, film_exit: int = 0, sizes: list[list[int]] | None = None,
                 frames: int = 12, throughput_ok: bool = True,
                 peak_rss_mb: float | None = 812.5,
                 cpu_seconds: float | None = 6.25) -> dict:
    film_cmd: dict = {"name": "film", "argv": ["just", "film"], "exit": film_exit,
                      "seconds": 3.7, "tail": ""}
    if peak_rss_mb is not None:
        film_cmd["peak_rss_mb"] = peak_rss_mb
    if cpu_seconds is not None:
        film_cmd["cpu_seconds"] = cpu_seconds
    return {
        "tier": "programmatic",
        "commands": [{"name": "check", "argv": [], "exit": 0, "seconds": 1.0,
                      "tail": ""}, film_cmd],
        "frames": {"count": frames, "sizes": sizes if sizes is not None else [[640, 400]],
                   "errors": []},
        "throughput": ({"ok": True, "ticks": 400, "ticks_per_second": 25740.1,
                        "startup_s": 1.42}
                       if throughput_ok else {"ok": False, "error": "probe exited"}),
    }


def write_eval_dir(root: Path, trial: str, doc: dict, *, frame_px=(640, 400),
                   n_frames: int = 12) -> Path:
    d = root / trial / "eval"
    (d / "frames").mkdir(parents=True, exist_ok=True)
    (d / "programmatic.json").write_text(json.dumps(doc))
    for i in range(n_frames):
        (d / "frames" / f"frame_{i:04d}.png").write_bytes(png_bytes(*frame_px))
    return d


STACKS = ("rust", "ts", "unity", "godot")


def field_set(populated: bool = True, **kw) -> list[capability.Observation]:
    """Two trials per stack, one game."""
    out = []
    for stack in STACKS:
        for t in (0, 1):
            out.append(capability.observe_doc(
                programmatic(**kw), game="g2_tetris3d", stack=stack,
                trial=f"g2_tetris3d__{stack}__t{t}", run="fixture"))
    return out


# --------------------------------------------------------------------------- #
# 1. the record schema is the same for every stack
# --------------------------------------------------------------------------- #

def test_schema_is_stack_independent() -> None:
    print("\n[schema]")
    recs = field_set()
    keysets = {tuple(sorted(r.fields)) for r in recs}
    check("every stack emits exactly the same field names", len(keysets) == 1,
          f"{len(keysets)} distinct key sets")
    check("the emitted names are exactly the declared ones",
          keysets.pop() == tuple(sorted(capability.FIELDS)),
          "record keys must equal FIELDS")
    for f, unit in capability.FIELDS.items():
        check(f"{f} declares a unit", bool(unit))


# --------------------------------------------------------------------------- #
# 2. values are read, not invented
# --------------------------------------------------------------------------- #

def test_values() -> None:
    print("\n[values]")
    r = field_set()[0]
    check("capture.width_px", r.fields["capture.width_px"] == 640)
    check("capture.height_px", r.fields["capture.height_px"] == 400)
    check("capture.megapixels", r.fields["capture.megapixels"] == round(640 * 400 / 1e6, 4))
    check("capture.frames", r.fields["capture.frames"] == 12)
    check("capture.wall_seconds", r.fields["capture.wall_seconds"] == 3.7)
    check("capture.peak_rss_mb", r.fields["capture.peak_rss_mb"] == 812.5)
    check("capture.cpu_seconds", r.fields["capture.cpu_seconds"] == 6.25)
    check("probe.ticks_per_second", r.fields["probe.ticks_per_second"] == 25740.1)
    check("probe.startup_seconds", r.fields["probe.startup_seconds"] == 1.42)

    # A submission whose frames disagree about geometry has no single geometry, and
    # inventing one would be worse than reporting none.
    mixed = capability.observe_doc(
        programmatic(sizes=[[640, 400], [320, 200]]), game="g1_pong", stack="ts",
        trial="g1_pong__ts__t0", run="fixture")
    check("mixed geometry gives a null width, not a guess",
          mixed.fields["capture.width_px"] is None)
    check("...and says why", "geometr" in (mixed.why.get("capture.width_px") or ""),
          mixed.why.get("capture.width_px", ""))
    check("...classified as a submission property, not a stack gap",
          mixed.reason["capture.width_px"] == capability.SUBMISSION,
          mixed.reason["capture.width_px"])


# --------------------------------------------------------------------------- #
# 3. every null carries a reason, and the reason is one of the declared kinds
# --------------------------------------------------------------------------- #

def test_nulls_are_explained() -> None:
    print("\n[nulls]")
    r = capability.observe_doc(
        programmatic(film_exit=1, sizes=[], frames=0, throughput_ok=False,
                     peak_rss_mb=None, cpu_seconds=None),
        game="g1_pong", stack="rust", trial="g1_pong__rust__t0", run="fixture")
    nulls = [f for f, v in r.fields.items() if v is None]
    check("a failed capture yields nulls", len(nulls) >= 4, f"{len(nulls)} nulls")
    check("every null has a reason kind",
          all(r.reason.get(f) in capability.REASONS for f in nulls),
          str({f: r.reason.get(f) for f in nulls}))
    check("every null has prose saying why",
          all((r.why.get(f) or "").strip() for f in nulls))
    check("a film that exited non-zero is a submission failure, not a stack gap",
          r.reason["capture.frames"] == capability.SUBMISSION,
          r.reason["capture.frames"])
    check("rusage absent from an old record is 'not captured in this run'",
          r.reason["capture.peak_rss_mb"] == capability.NOT_CAPTURED,
          r.reason["capture.peak_rss_mb"])
    check("no value is ever both null and populated",
          all((r.fields[f] is None) == (f in r.reason) for f in r.fields))


# --------------------------------------------------------------------------- #
# 4. THE GATE. positive / mutant / variant.
# --------------------------------------------------------------------------- #

def test_gate_positive() -> None:
    print("\n[gate: positive control]")
    problems = capability.no_stack_correlated_gap(field_set())
    check("a healthy field set passes the gate", problems == [], str(problems))


def test_gate_mutant() -> None:
    print("\n[gate: MUTANT - one stack structurally cannot report a field]")
    recs = []
    for r in field_set():
        if r.stack == "godot":
            # The mechanism removed: this stack never reports rusage.
            r.fields["capture.peak_rss_mb"] = None
            r.reason["capture.peak_rss_mb"] = capability.STACK_CANNOT
            r.why["capture.peak_rss_mb"] = "no mechanism on this arm"
        recs.append(r)
    problems = capability.no_stack_correlated_gap(recs)
    check("the gate goes RED", problems != [], f"{len(problems)} problem(s)")
    check("...and names the field", any("capture.peak_rss_mb" in p for p in problems),
          str(problems))
    check("...and names the stack", any("godot" in p for p in problems), str(problems))


def test_gate_mutant_silent() -> None:
    print("\n[gate: MUTANT - a silent gap, null with no reason kind at all]")
    recs = []
    for r in field_set():
        if r.stack == "unity":
            r.fields["capture.cpu_seconds"] = None
            r.reason.pop("capture.cpu_seconds", None)
            r.why.pop("capture.cpu_seconds", None)
        recs.append(r)
    problems = capability.no_stack_correlated_gap(recs)
    check("an UNEXPLAINED null is a gate failure", problems != [], str(problems))
    check("...and is not silently forgiven as a submission failure",
          any("unity" in p for p in problems), str(problems))


def test_gate_variant() -> None:
    print("\n[gate: VARIANT - real absences that must NOT fire]")
    # Two submissions per stack, one of each pair had its `film` fail. Absences are
    # real and numerous; none of them is stack-correlated.
    recs = []
    for stack in STACKS:
        recs.append(capability.observe_doc(
            programmatic(), game="g3_arena", stack=stack,
            trial=f"g3_arena__{stack}__t0", run="fixture"))
        recs.append(capability.observe_doc(
            programmatic(film_exit=1, sizes=[], frames=0),
            game="g3_arena", stack=stack, trial=f"g3_arena__{stack}__t1", run="fixture"))
    problems = capability.no_stack_correlated_gap(recs)
    check("submission-level failures spread across stacks do NOT fire the gate",
          problems == [], str(problems))

    # And the sharper variant: the absence lands on ONE stack, but for a submission
    # reason. That is a real skew, so the gate must SAY SO without calling it a stack
    # gap - the distinction the whole file exists for.
    skew = []
    for stack in STACKS:
        for t in (0, 1):
            failed = stack == "rust"
            skew.append(capability.observe_doc(
                programmatic(film_exit=1 if failed else 0,
                             sizes=[] if failed else None,
                             frames=0 if failed else 12),
                game="g3_arena", stack=stack, trial=f"g3_arena__{stack}__t{t}",
                run="fixture"))
    problems = capability.no_stack_correlated_gap(skew)
    check("a one-stack SUBMISSION failure does not fire the gate", problems == [],
          str(problems))
    warn = capability.stack_skew_warnings(skew)
    check("...but it IS reported as skew", warn != [], str(warn))
    check("...naming rust", any("rust" in w for w in warn), str(warn))


def test_gate_needs_all_four() -> None:
    print("\n[gate: a field set missing a whole arm cannot be declared clean]")
    recs = [r for r in field_set() if r.stack != "ts"]
    problems = capability.no_stack_correlated_gap(recs)
    check("three arms is not four", problems != [], str(problems))
    check("...and it names the absent arm", any("ts" in p for p in problems),
          str(problems))


# --------------------------------------------------------------------------- #
# 5. reading a real directory on disk
# --------------------------------------------------------------------------- #

def test_reads_disk() -> None:
    print("\n[disk]")
    with tempfile.TemporaryDirectory(prefix="cap-selftest-") as td:
        root = Path(td)
        write_eval_dir(root, "g4_platformer__godot__t0", programmatic(),
                       frame_px=(420, 640))
        recs = capability.sweep(root)
        check("one record found", len(recs) == 1, f"{len(recs)}")
        r = recs[0]
        check("game parsed", r.game == "g4_platformer", r.game)
        check("stack parsed", r.stack == "godot", r.stack)
        # The PNG on disk disagrees with programmatic.json's `sizes`. The pixels win:
        # `sizes` is a summary written by an earlier version of the harness, the file
        # is the artifact. A record must never prefer a summary to the thing it
        # summarises.
        check("geometry comes from the PNG header, not the summary",
              r.fields["capture.width_px"] == 420 and r.fields["capture.height_px"] == 640,
              f"{r.fields['capture.width_px']}x{r.fields['capture.height_px']}")
        check("and the disagreement is recorded rather than hidden",
              "sizes" in json.dumps(r.notes), str(r.notes))


# --------------------------------------------------------------------------- #
# 6. the NOT-reportable register is real, not decorative
# --------------------------------------------------------------------------- #

def test_declined_register() -> None:
    print("\n[declined]")
    check("there is a register of fields deliberately NOT captured",
          len(capability.DECLINED) >= 5, str(len(capability.DECLINED)))
    for name, entry in capability.DECLINED.items():
        check(f"{name} says why", bool(entry.get("why")))
        check(f"{name} cites a source", bool(entry.get("source")))
        check(f"{name} says what would change the answer",
              bool(entry.get("would_change")))
    overlap = set(capability.DECLINED) & set(capability.FIELDS)
    check("nothing is both captured and declined", overlap == set(), str(overlap))


def main() -> int:
    test_schema_is_stack_independent()
    test_values()
    test_nulls_are_explained()
    test_gate_positive()
    test_gate_mutant()
    test_gate_mutant_silent()
    test_gate_variant()
    test_gate_needs_all_four()
    test_reads_disk()
    test_declined_register()
    print()
    if FAILURES:
        print(f"FAILED: {len(FAILURES)}")
        for f in FAILURES:
            print(f"  - {f}")
        return 1
    print("all controls hold")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
