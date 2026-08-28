#!/usr/bin/env python3
"""Capture geometry across a run's submissions. Run BEFORE reading any frame-derived number.

WHAT THE PACK PATH ACTUALLY DOES (2026-08-28; corrects this header and JUDGING.md,
which described a refuse gate here from 2026-08-21 to 2026-08-28)
----------------------------------------------------------------
`judge/field.py::build_pack` measures each submission's geometry from its FIRST
frame, records it per blind label in the pack's `capture_geometry` mapping, and
when the sizes differ `_brief` renders a note into `BRIEF.md` naming each
label's size and telling the judge the variation is a presentation choice the
task left open - only godot's film recipe passes `--resolution`, so the other
three capture at whatever their render target defaults to. It NEVER refuses.

Refusing was rejected on purpose, and the reason is recorded in the code
comment beside the measurement: geometry is a DESIGN CHOICE THE TASK LEFT OPEN.
`g2_tetris3d__unity__t1` filmed 420x640 - a portrait well for a falling-block
game, a perfectly sensible thing to build - and refusing the field treated
variation as corruption, while re-filming at 640x400 would erase a real
difference between submissions and call the erasure normalisation: the harness
overwriting the thing it exists to measure.

Why annotation is right HERE and was wrong in #62, since they look identical:
#62's caveat was `files_dropped_for_length`, a JSON field no code read and no
human opened - annotation into a void. The geometry note goes into `BRIEF.md`,
read by an agent whose whole task is to read it. The test is not "annotate vs
refuse", it is WHETHER ANYTHING IS ON THE OTHER END.

`judge/field.py::pack_parity`, whose docstring claimed to be this gate running
on the path, had no caller at any committed revision and was deleted 2026-08-28
(task 202). It had called `geometry()` below; nothing on the path does.

WHAT THIS TOOL READS THAT THE PATH CANNOT
-----------------------------------------
The inline read is the FIRST frame only, so a submission whose frame size
changes mid-film has no reader in `build_pack`. `geometry()` reads every frame
and reports `uniform_within_submission` - run it before spending on a field you
did not film yourself. `--runs-root` measures the whole stored corpus against
the same property; its figures live in `eval/RUNS.md`.

WHY THIS EXISTS
---------------
`g2_tetris3d__rust__t0` filmed at **768x576** while the other 21 submissions across two runs
filmed at **640x400**. Nothing reported it. It was found by hand, while adjudicating a judge
whose scores turned out to track distinct-colour counts (FINDINGS #59), and the first question
anyone sensible asks about that result is "were the frames the same size?".

More pixels is more opportunity for distinct colours, so **every frame-derived measure is
confounded by capture geometry unless the frames are the same size or the measure is a
density**. That includes `render.nonempty` (ink coverage - already a density, so safe),
`render.animates` (a fraction - safe), and the `fun` and `ux` judges (NOT safe: they are shown
raw PNGs).

`starter_parity.py` cannot catch this. It compares the four STARTERS, and the capture size
lives in each stack's own source - `film.rs`, `film.ts`, `Probe.Film` - which an agent may
change. This is a property of a SUBMISSION, so it has to be measured on the artifacts.

That is rule 6 again in its general form: the parity guard names the axes someone thought of
(recipes, hash chains, AGENTS.md, hooks, CI) and capture geometry was not one of them.

It was run **after** a 10.20-tokval judge round once (2026-08-21) - whereupon it reported
`g2_tetris3d__unity__t1` at **420x640** against the field's 640x400. The result happened to
survive (all aspects saw identical frames, so a shared anomaly cancels between them), which
is luck and not method. **A gate that fires only when someone remembers it has a
person-shaped hole in it.** FINDINGS #68.

WHAT IT DOES NOT DO
-------------------
It does not say which size is right. A submission may legitimately film larger. It says the
field is not uniform, so a frame-derived comparison across it needs normalising or dropping.

Usage:
    python3 tools/frame_parity.py --run runs/<name>          # one run, hand inspection
    python3 tools/frame_parity.py --run runs/<name> --json
    python3 tools/frame_parity.py --runs-root <main checkout>/eval/runs   # the corpus
    python3 tools/frame_parity.py --selftest                 # fixture pins, no corpus
"""
from __future__ import annotations

import argparse
import json
import struct
import sys
import zlib
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "judge"))
import png  # noqa: E402

#: What a frame read can fail with, all of it documented: `png.read` raises
#: `PngError` for every malformed shape it names, `OSError` for an unreadable
#: file, and `struct.error`/`zlib.error` for bytes that pass the magic check
#: and no further check. Anything else is a defect in this walker and
#: propagates - a crash is visible, a silent skip is not.
_FRAME_ERRORS = (png.PngError, OSError, struct.error, zlib.error)


def frame_sizes(frames: list[Path], read=png.read) -> tuple[Counter, list[str]]:
    """Sizes of every frame handed in, plus the names that could not be read.

    An unreadable frame is a frame of UNKNOWN SIZE, so it is returned beside
    the sizes rather than folded into them - the caller decides what that does
    to the verdict, and the shipped decision is below.
    """
    sizes: Counter = Counter()
    unreadable: list[str] = []
    for f in frames:
        try:
            im = read(f)
        except _FRAME_ERRORS:
            unreadable.append(f.name)
            continue
        sizes[f"{im.width}x{im.height}"] += 1
    return sizes, unreadable


def geometry(run: Path) -> dict[str, dict]:
    """Per-submission geometry inside ONE run directory (the hand-inspection shape)."""
    out: dict[str, dict] = {}
    for d in sorted((run / "artifacts").glob("*")):
        frames = sorted((d / "eval" / "frames").glob("*.png"))
        if not frames:
            continue
        sizes, unreadable = frame_sizes(frames)
        out[d.name] = {"sizes": dict(sizes), "n_frames": len(frames),
                       "unreadable": unreadable,
                       "uniform_within_submission": len(sizes) == 1 and not unreadable}
    return out


def corpus(runs_root: Path) -> dict:
    """Every submission's frame geometry at any depth under a runs root.

    The population is every `eval/frames` directory holding at least one PNG,
    keyed on the LAYOUT and not on a directory name: the stored tree's archived
    work trees carry Unity's `Library/artifacts` and `Library/Bee/artifacts`
    build caches, and an `artifacts`-name walk reads 3147 cache subdirectories
    as trials. It makes no claim about trials without frames - the stored-tree
    trial count is `census.py`'s producer, not this one. Depth-independence is
    the point - the tree holds wrapper run directories
    (`wg-g4c-capgate/capped/...`) at depths a `runs/*/artifacts` glob misses.
    """
    by_trial: dict[Path, list[Path]] = {}
    for f in runs_root.rglob("*.png"):
        if f.parent.name == "frames" and f.parent.parent.name == "eval":
            by_trial.setdefault(f.parent.parent.parent, []).append(f)
    subs: dict[str, dict] = {}
    for trial in sorted(by_trial):
        frames = sorted(by_trial[trial])
        run_label = str(trial.parent.parent.relative_to(runs_root))
        sizes, unreadable = frame_sizes(frames)
        subs[f"{run_label}/artifacts/{trial.name}"] = {
            "run": run_label,
            "n_frames": len(frames),
            "sizes": dict(sizes),
            "unreadable": unreadable,
            "nonuniform": len(sizes) >= 2,
            "uniform": len(sizes) == 1 and not unreadable,
        }
    return {"submissions": subs}


def run_divergent(subs: dict[str, dict], members: list[str]) -> list[str]:
    """Which of one run's submissions diverge from the run's modal geometry.

    The rule is `geometry()`'s, lifted here so the corpus report and the
    selftest read one copy of it: a submission diverges when its size list is
    not the run's modal size list, or when it is not uniform within itself, or
    when any frame's size is unknown.
    """
    per: Counter = Counter()
    for k in members:
        per.update(subs[k]["sizes"])
    if not per:
        return []
    modal = per.most_common(1)[0][0]
    return sorted(k for k in members
                  if list(subs[k]["sizes"]) != [modal] or subs[k]["nonuniform"]
                  or subs[k]["unreadable"])


def census(runs_root: Path) -> tuple[int, dict]:
    """The corpus measurement: does any stored submission hold frames of >1 size?"""
    c = corpus(runs_root)
    subs = c["submissions"]
    if not subs:
        print(f"no submissions with frames under {runs_root} - UNMEASURED, not clean",
              file=sys.stderr)
        return 2, c
    runs: dict[str, list[str]] = {}
    for key, rec in subs.items():
        runs.setdefault(rec["run"], []).append(key)
    mixed = {k: v for k, v in subs.items() if v["nonuniform"]}
    flagged = {k: v for k, v in subs.items() if v["unreadable"]}
    uniform = [k for k, v in subs.items() if v["uniform"]]
    all_sizes: Counter = Counter()
    for v in subs.values():
        all_sizes.update(v["sizes"])

    print(f"frames under {runs_root}: {len(subs)} submissions with frames "
          f"in {len(runs)} run dirs")
    print(f"  uniform within submission: {len(uniform)}")
    print(f"  NON-UNIFORM (frames of more than one size): {len(mixed)}")
    for k in sorted(mixed):
        print(f"    {k}: {mixed[k]['sizes']}")
    print(f"  submissions with unreadable frames (size unknown, never counted "
          f"uniform): {len(flagged)}")
    for k in sorted(flagged):
        print(f"    {k}: unreadable {flagged[k]['unreadable']}, "
              f"readable {flagged[k]['sizes']}")
    print(f"  corpus frame sizes: {dict(sorted(all_sizes.items()))}")
    for run in sorted(runs):
        members = runs[run]
        per: Counter = Counter()
        for k in members:
            per.update(subs[k]["sizes"])
        if not per:
            continue
        modal = per.most_common(1)[0][0]
        odd = run_divergent(subs, members)
        print(f"  run {run}: {len(members)} submissions, modal {modal}, "
              f"divergent: {odd if odd else 'none'}")
        for k in odd:
            print(f"    {k}: {subs[k]['sizes']}"
                  + (f" unreadable {subs[k]['unreadable']}" if subs[k]["unreadable"] else ""))
    return 0, c


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", type=Path, help="one run directory (hand inspection)")
    ap.add_argument("--runs-root", type=Path,
                    help="a runs tree to measure the whole corpus over; the MAIN "
                         "checkout's eval/runs - a worktree's is gitignored and "
                         "empty, which reads as UNMEASURED")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true",
                    help="run the fixture pins instead of any corpus")
    a = ap.parse_args(argv)
    if a.selftest:
        return selftest()
    if a.run and a.runs_root:
        ap.error("--run and --runs-root are different questions; pass one")
    if a.runs_root:
        rc, _ = census(a.runs_root)
        return rc
    if not a.run:
        ap.error("one of --run, --runs-root or --selftest is required")

    g = geometry(a.run)
    if not g:
        print(f"no frames under {a.run}/artifacts/*/eval/frames")
        return 0
    all_sizes: Counter = Counter()
    for rec in g.values():
        for s, n in rec["sizes"].items():
            all_sizes[s] += n
    modal = all_sizes.most_common(1)[0][0]
    odd = {k: v for k, v in g.items()
           if list(v["sizes"]) != [modal] or not v["uniform_within_submission"]}

    if a.json:
        print(json.dumps({"per_submission": g, "modal_size": modal,
                          "divergent": sorted(odd)}, indent=2))
        return 1 if odd else 0

    w = max(len(k) for k in g)
    print(f"{'submission':<{w}}  frames  capture geometry")
    for k, v in g.items():
        flag = "" if list(v["sizes"]) == [modal] and v["uniform_within_submission"] else "   <-- DIVERGES"
        print(f"{k:<{w}}  {v['n_frames']:>6}  {v['sizes']}{flag}")
    print(f"\nmodal capture geometry: {modal}")
    if not odd:
        print("PARITY: every submission filmed at the same size; frame-derived measures are "
              "comparable across this field.")
        return 0
    print(f"\nDIVERGENT - {len(odd)} submission(s): {sorted(odd)}")
    print("Frame-derived measures are NOT comparable across this field without normalising.\n"
          "More pixels is more opportunity for distinct colours, more ink and more change;\n"
          "densities (ink_coverage, fraction-of-pixels-changed) are safe, raw counts are not,\n"
          "and a judge shown the PNGs directly is shown the difference (FINDINGS #59).")
    return 1


def _fixture(root: Path) -> dict[str, dict]:
    """A runs tree whose every census answer is written out beside it.

    `t_mixed` is the row the ticket exists for: a submission whose frame size
    changes mid-film, which the pack path's first-frame read reports uniform.
    `t_unread` pins that an unreadable frame is a size nobody knows, not a
    clean bill. `run-n/capped` is a wrapper run two directories deep, which a
    `runs/*/artifacts` glob would miss.
    """

    def frames(rel: str, shapes: list[tuple[int, int]]) -> None:
        d = root / rel
        d.mkdir(parents=True, exist_ok=True)
        for i, (w, h) in enumerate(shapes):
            png.write_rgb(d / f"f{i}.png", w, h, bytes([200, 10, 10]) * (w * h))

    frames("run-a/artifacts/t_uni/eval/frames", [(4, 2)] * 3)          # uniform
    frames("run-a/artifacts/t_mixed/eval/frames",
           [(4, 2), (2, 4), (4, 2)])                                   # NON-UNIFORM
    frames("run-a/artifacts/t_odd/eval/frames", [(6, 6)])              # diverges across run-a
    frames("run-b/artifacts/t_unread/eval/frames", [(4, 2)])
    (root / "run-b/artifacts/t_unread/eval/frames/bad.png").write_bytes(b"\x89PNG\r\n\x1a\nxx")
    # Two poison rows for the population predicate, both present in the real
    # tree: a png under Unity's Library/artifacts build cache (an
    # artifacts-name walk reads 3147 of these as trials) and a frames dir
    # holding no pngs. Neither is a submission.
    frames("run-a/artifacts/t_lib/Library/artifacts/256", [(4, 4)])
    (root / "run-a/artifacts/t_empty/eval/frames").mkdir(parents=True)
    frames("run-n/capped/artifacts/t_deep/eval/frames", [(8, 3)] * 2)  # nested run
    return {
        "run-a/artifacts/t_uni": {"n_frames": 3, "sizes": {"4x2": 3},
                                  "nonuniform": False, "uniform": True},
        "run-a/artifacts/t_mixed": {"n_frames": 3, "sizes": {"2x4": 1, "4x2": 2},
                                    "nonuniform": True, "uniform": False},
        "run-a/artifacts/t_odd": {"n_frames": 1, "sizes": {"6x6": 1},
                                  "nonuniform": False, "uniform": True},
        "run-b/artifacts/t_unread": {"n_frames": 2, "sizes": {"4x2": 1},
                                     "nonuniform": False, "uniform": False},
        "run-n/capped/artifacts/t_deep": {"n_frames": 2, "sizes": {"8x3": 2},
                                          "nonuniform": False, "uniform": True},
    }


def selftest() -> int:
    import tempfile
    failures: list[str] = []

    def expect(name: str, cond: bool, detail: str) -> None:
        if not cond:
            failures.append(f"{name}: {detail}")

    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        want = _fixture(root)
        rc, c = census(root)
        got = c["submissions"]
        expect("census-runs", rc == 0, f"census returned {rc}")
        expect("population", set(got) == set(want),
               f"population is {sorted(got)}, expected {sorted(want)} - "
               f"the Library/artifacts cache png and the empty frames dir "
               f"must both stay out")
        for key, rec in want.items():
            g = got.get(key, {})
            for field in ("n_frames", "sizes", "nonuniform", "uniform"):
                expect(f"{key}.{field}", g.get(field) == rec[field],
                       f"reads {g.get(field)!r}, expected {rec[field]!r}")
        # The unreadable frame is itemised, not folded away.
        expect("unreadable-itemised",
               got["run-b/artifacts/t_unread"]["unreadable"] == ["bad.png"],
               f"bad.png must be named, got "
               f"{got['run-b/artifacts/t_unread']['unreadable']}")
        # MUTANT 1: the pack path's first-frame read, over the same fixture.
        # t_mixed's first frame is 4x2, so the on-path read reports one size -
        # this is the property `build_pack` cannot see and this tool must.
        first = {}
        for key, rec in got.items():
            d = root / key / "eval" / "frames"
            sizes, _ = frame_sizes(sorted(d.glob("*.png"))[:1])
            first[key] = dict(sizes)
        expect("mutant-first-frame-read",
               len(first["run-a/artifacts/t_mixed"]) == 1
               and len(got["run-a/artifacts/t_mixed"]["sizes"]) == 2,
               f"the first-frame read sees {first['run-a/artifacts/t_mixed']} "
               f"where the census sees {got['run-a/artifacts/t_mixed']['sizes']} - "
               f"the fixture no longer discriminates the two readers")
        # MUTANT 2: folding the unreadable frame into the verdict. A reader
        # that skips unreadables and judges on sizes alone calls t_unread
        # uniform; the shipped verdict must not.
        folded = len(got["run-b/artifacts/t_unread"]["sizes"]) == 1
        expect("mutant-unreadable-folded",
               folded and not got["run-b/artifacts/t_unread"]["uniform"],
               "t_unread must stay out of the uniform column while a frame's "
               "size is unknown")
        # The corpus answer, stated in advance: 1 non-uniform submission, 2
        # uniform, 1 unreadable-flagged, and run-a's cross-submission
        # divergence is t_odd (modal 4x2, five frames) not t_mixed (2 frames
        # at the modal size but not uniform within itself).
        expect("mixed-total",
               sum(1 for r in got.values() if r["nonuniform"]) == 1,
               f"exactly t_mixed is non-uniform, got "
               f"{sum(1 for r in got.values() if r['nonuniform'])}")
        expect("uniform-total",
               sum(1 for r in got.values() if r["uniform"]) == 3,
               f"t_uni, t_odd and t_deep are uniform WITHIN themselves "
               f"(t_odd holds one frame, one size), got "
               f"{sum(1 for r in got.values() if r['uniform'])}")
        # ...while t_odd still diverges from run-a's modal: within-submission
        # uniformity and cross-submission parity are different properties, and
        # this row carries both verdicts at once.
        run_a = [k for k, r in got.items() if r["run"] == "run-a"]
        expect("within-vs-cross-uniform",
               got["run-a/artifacts/t_odd"]["uniform"]
               and run_divergent(got, run_a) == ["run-a/artifacts/t_mixed",
                                                 "run-a/artifacts/t_odd"],
               f"t_odd is uniform within itself and divergent across run-a; "
               f"run-a's divergent list reads {run_divergent(got, run_a)}")

    if failures:
        print(f"FRAME PARITY SELFTEST: {len(failures)} unmet\n")
        for f in failures:
            print(f"  FAIL {f}")
        return 1
    print("FRAME PARITY SELFTEST: the fixture answers every row as written - the "
          "mixed-size submission is caught, the unreadable frame is a flag and "
          "not a clean bill, the nested run is found, and the first-frame read "
          "the pack path uses is pinned as the thing this tool exists to catch.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
