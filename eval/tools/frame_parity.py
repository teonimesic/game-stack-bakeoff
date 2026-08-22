#!/usr/bin/env python3
"""Capture geometry across a run's submissions. Run BEFORE reading any frame-derived number.

YOU NO LONGER HAVE TO REMEMBER THAT
-----------------------------------
`judge/field.py::pack_parity` calls `geometry()` below, and `build_pack` REFUSES any
frames-reading aspect on a field whose submissions were not all filmed at one size. This
CLI remains for inspecting a field by hand; it is no longer the only thing standing
between a divergence and a judge.

That change was bought. This tool existed, its docstring said to run it first, and on
2026-08-21 it was run **after** a $10.20 judge round - whereupon it reported
`g2_tetris3d__unity__t1` at **420x640** against the field's 640x400, a portrait/landscape
flip that both frames-only aspects had been shown directly. The result happened to survive
(all aspects saw identical frames, so a shared anomaly cancels between them), which is luck
and not method. **A gate that fires only when someone remembers it has a person-shaped hole
in it.** FINDINGS #68.

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

WHAT IT DOES NOT DO
-------------------
It does not say which size is right. A submission may legitimately film larger. It says the
field is not uniform, so a frame-derived comparison across it needs normalising or dropping.

Usage:
    python3 tools/frame_parity.py --run runs/<name>
    python3 tools/frame_parity.py --run runs/<name> --json
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "judge"))
import png  # noqa: E402


def geometry(run: Path) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for d in sorted((run / "artifacts").glob("*")):
        frames = sorted((d / "eval" / "frames").glob("*.png"))
        if not frames:
            continue
        sizes: Counter = Counter()
        for f in frames:
            im = png.read(f)
            sizes[f"{im.width}x{im.height}"] += 1
        out[d.name] = {"sizes": dict(sizes), "n_frames": len(frames),
                       "uniform_within_submission": len(sizes) == 1}
    return out


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run", type=Path, required=True)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)

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


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
