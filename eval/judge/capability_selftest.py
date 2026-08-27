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
import re
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


# --------------------------------------------------------------------------- #
# 7. a figure the register rests on is COUNTED, and the count tracks its population
# --------------------------------------------------------------------------- #

#: The shape of a corpus figure written into prose: "62 of 68". A DECLINED entry may
#: not carry one, because a literal cannot go stale visibly - and this one was printed
#: two screens under a computed header reading 69, which is worse than having no
#: producer at all, since it looked produced (tasks/182).
FROZEN_FIGURE = re.compile(r"\b\d+\s+of\s+\d+\b")


def resolution_fixture() -> list[capability.Observation]:
    """5 records whose census is stated in the test, not read back from the subject.

    2 at the starter default, 2 varied at 2 distinct geometries, 1 with no geometry
    because its own `film` failed.
    """
    return [
        capability.observe_doc(programmatic(), game="g1_pong", stack="rust",
                               trial="g1_pong__rust__t0", run="fx"),
        capability.observe_doc(programmatic(), game="g1_pong", stack="ts",
                               trial="g1_pong__ts__t0", run="fx"),
        capability.observe_doc(programmatic(sizes=[[800, 600]]), game="g1_pong",
                               stack="unity", trial="g1_pong__unity__t0", run="fx"),
        capability.observe_doc(programmatic(sizes=[[320, 200]]), game="g1_pong",
                               stack="godot", trial="g1_pong__godot__t0", run="fx"),
        capability.observe_doc(programmatic(film_exit=1, sizes=[], frames=0),
                               game="g1_pong", stack="rust",
                               trial="g1_pong__rust__t1", run="fx"),
    ]


def census_disagreements(recs: list[capability.Observation],
                         cen: capability.ResolutionCensus) -> list[str]:
    """Does this census describe THESE records? Re-derived here from the records.

    The expectation is a second, independent statement of the answer: it reads the
    input the census was handed, never the census's own buckets. A control that
    builds its expectation by calling its subject is not a control (AGENTS.md rule 12,
    task 113).
    """
    want_default = want_varied = want_absent = 0
    for r in recs:
        w, h = r.fields.get("capture.width_px"), r.fields.get("capture.height_px")
        if w is None or h is None:
            want_absent += 1
        elif (w, h) == capability.STARTER_DEFAULT_GEOMETRY:
            want_default += 1
        else:
            want_varied += 1
    bad = []
    if cen.total != len(recs):
        bad.append(f"total {cen.total} for {len(recs)} records")
    if len(cen.at_default) != want_default:
        bad.append(f"at_default {len(cen.at_default)} want {want_default}")
    if cen.n_varied != want_varied:
        bad.append(f"varied {cen.n_varied} want {want_varied}")
    if cen.n_absent != want_absent:
        bad.append(f"absent {cen.n_absent} want {want_absent}")
    if len(cen.at_default) + cen.n_varied + cen.n_absent != cen.total:
        bad.append("the three buckets do not partition the population")
    return bad


def test_declined_figures_are_produced() -> None:
    print("\n[declined: every corpus figure has a producer]")
    for name, entry in capability.DECLINED.items():
        prose = " ".join(str(entry.get(k, ""))
                         for k in ("why", "source", "would_change"))
        hit = FROZEN_FIGURE.search(prose)
        check(f"{name} states no frozen 'N of M' figure of its own", hit is None,
              hit.group(0) if hit else "")
    named = {e["measured_by"] for e in capability.DECLINED.values()
             if e.get("measured_by")}
    check("at least one entry names a producer", named != set(), str(named))
    for producer in sorted(named):
        check(f"{producer} resolves to a callable",
              callable(capability.CENSUSES.get(producer)), str(producer))
    check("a producer name that resolves to nothing would be RED",
          not callable(capability.CENSUSES.get("no_such_census")))

    # MUTANT and VARIANT for the rows above. Without them the sweep is green and
    # nothing shows it could ever have been red - the shape this whole file exists
    # to refuse.
    relapse = {"why": "Measured, not assumed: 62 of 68 stored submissions captured "
                      "at exactly the starter default.",
               "source": "swept on some date", "would_change": ""}
    check("MUTANT: the literal put back is caught",
          FROZEN_FIGURE.search(" ".join(relapse.values())) is not None)
    innocent = ("wgpu 29 sets BUFFER_BINDING_ARRAY only on Vulkan; `just film` writes "
                "12 frames at 640x400, and Three of four arms expose a counter.")
    check("VARIANT: digits that are not a corpus figure stay GREEN",
          FROZEN_FIGURE.search(innocent) is None,
          str(FROZEN_FIGURE.search(innocent)))


def test_resolution_census() -> None:
    print("\n[census: resolution - positive control]")
    recs = resolution_fixture()
    cen = capability.resolution_census(recs)
    # Stated here in literals, ahead of running it.
    check("the population is the one it was handed", cen.total == 5, str(cen.total))
    check("2 at the starter default", len(cen.at_default) == 2, str(cen.at_default))
    check("2 varied, in 2 distinct geometries",
          cen.n_varied == 2 and sorted(cen.varied) == ["320x200", "800x600"],
          str(cen.varied))
    check("1 with no geometry, classified as a submission failure",
          cen.n_absent == 1 and list(cen.absent) == [capability.SUBMISSION],
          str(cen.absent))
    check("the re-derived expectation agrees",
          census_disagreements(recs, cen) == [], str(census_disagreements(recs, cen)))
    s = cen.sentence()
    for want in ("2 of the 5", "640x400", "800x600", "320x200", capability.SUBMISSION):
        check(f"the sentence states {want!r}", want in s, s)
    # The denominator is the whole population: drop the record whose capture failed
    # and this reads "2 of the 4", which is the shape the ticket was filed against.
    check("the failed capture is accounted for, not dropped from the denominator",
          "2 of the 5" in s and "1 has no geometry to compare" in s, s)


def test_resolution_census_mutant() -> None:
    print("\n[census: MUTANT - the figure is frozen instead of counted]")
    recs = resolution_fixture()
    frozen = capability.ResolutionCensus(
        default=capability.STARTER_DEFAULT_GEOMETRY, total=68,
        at_default=[f"stale/t{i}" for i in range(62)],
        varied={"768x576": ["stale/a"], "720x540": ["stale/b"], "420x640": ["stale/c"]})
    bad = census_disagreements(recs, frozen)
    check("a census that ignores its records is RED", bad != [], str(bad))
    check("...and the disagreement names the population",
          any("total" in b for b in bad), str(bad))
    check("...while the real census over the same records is GREEN",
          census_disagreements(recs, capability.resolution_census(recs)) == [])


def test_resolution_census_variant() -> None:
    print("\n[census: VARIANT - populations a frozen figure would still 'pass' on]")
    # (a) every record at the default: no varied, no absent, and the sentence must
    #     still say so rather than omitting an empty bucket.
    uniform = [capability.observe_doc(programmatic(), game="g1_pong", stack=s,
                                      trial=f"g1_pong__{s}__t0", run="fx")
               for s in STACKS]
    cen = capability.resolution_census(uniform)
    check("all-default: 4 of 4 at the default",
          len(cen.at_default) == 4 and cen.n_varied == 0 and cen.n_absent == 0,
          cen.sentence())
    check("...and the empty buckets are stated, not omitted",
          "0 varied (none)" in cen.sentence(), cen.sentence())
    check("...and it re-derives", census_disagreements(uniform, cen) == [])

    # (b) the empty corpus. A ratio would divide by zero; a partition reports 0 of 0.
    empty = capability.resolution_census([])
    check("an empty sweep says 0 of the 0, and does not crash",
          "0 of the 0" in empty.sentence(), empty.sentence())

    # (c) a corpus where the default is NOT the majority. Nothing in the census may
    #     assume which way the answer comes out.
    odd = [capability.observe_doc(programmatic(sizes=[[1280, 720]]), game="g1_pong",
                                  stack=s, trial=f"g1_pong__{s}__t0", run="fx")
           for s in STACKS]
    cen = capability.resolution_census(odd)
    check("a corpus that varies reports 0 of 4 at the default",
          len(cen.at_default) == 0 and cen.n_varied == 4, cen.sentence())
    check("...and it re-derives", census_disagreements(odd, cen) == [])


def test_starter_default_is_what_the_starters_say() -> None:
    print("\n[starter default: the constant against the four starter sources]")
    # `STARTER_DEFAULT_GEOMETRY` names the starter default, so the starters are the
    # address that settles it. Spelled in two places and compared by a row here,
    # rather than shared as one object (AGENTS.md rule 12).
    starters = Path(__file__).resolve().parent.parent / "starters"
    sources = {
        "rust":  starters / "rust/crates/game/src/lib.rs",
        "ts":    starters / "ts/src/view/index.ts",
        "unity": starters / "unity/Assets/View/GameView.cs",
        "godot": starters / "godot/view/view.gd",
    }
    decl = re.compile(r"VIEW_(WIDTH|HEIGHT)\s*(?::\s*\w+\s*)?=\s*(\d+)")
    for arm, path in sources.items():
        if not path.is_file():
            check(f"{arm} view source is readable", False, str(path))
            continue
        seen: dict[str, int] = {}
        for line in path.read_text().splitlines():
            m = decl.search(line)
            if m and m.group(1) not in seen:
                seen[m.group(1)] = int(m.group(2))
        got = (seen.get("WIDTH"), seen.get("HEIGHT"))
        check(f"{arm} declares the geometry the constant claims",
              got == capability.STARTER_DEFAULT_GEOMETRY,
              f"{path.name} says {got}, constant says "
              f"{capability.STARTER_DEFAULT_GEOMETRY}")


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
    test_declined_figures_are_produced()
    test_resolution_census()
    test_resolution_census_mutant()
    test_resolution_census_variant()
    test_starter_default_is_what_the_starters_say()
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
