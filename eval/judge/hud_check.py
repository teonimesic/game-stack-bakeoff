#!/usr/bin/env python3
"""Independent check that `just film` puts the HUD in the pixels.

    python3 judge/hud_check.py <frames-dir> [more dirs...]

Deliberately not the starters' own tests. Each starter now ships a rendering test that
asserts its own HUD is captured, and each of those was watched to go red with the HUD
removed - but a test written by the same author as the fix shares the author's
assumptions, and this project has been caught by that before (IMPROVEMENTS, iteration
1b). So this reads the PNGs `just film` actually wrote, from outside, knowing nothing
about how any stack draws.

The HUD box is the top-left corner, which is where all four starters put it. A frame
whose corner is entirely background is a frame with no HUD in it, whatever the stack's
own test says.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import png  # noqa: E402

BOX = (0, 0, 230, 64)     # x0, y0, x1, y1 - generous; all four HUDs sit inside it
TOLERANCE = 8
MIN_INK = 60              # a few glyphs' worth. Zero means "no HUD".


def corner_ink(path: Path) -> tuple[int, tuple[int, int, int]]:
    img = png.read(path)
    bg = img.dominant_background()
    x0, y0, x1, y1 = BOX
    lit = 0
    for y in range(y0, min(y1, img.height)):
        for x in range(x0, min(x1, img.width)):
            p = img.rgb(x, y)
            if any(abs(p[c] - bg[c]) > TOLERANCE for c in range(3)):
                lit += 1
    return lit, bg


def check(dirpath: Path) -> bool:
    frames = sorted(dirpath.glob("*.png"))
    if not frames:
        print(f"{dirpath}: NO FRAMES - `just film` produced nothing")
        return False
    counts = []
    for f in frames:
        lit, bg = corner_ink(f)
        counts.append((f.name, lit, bg))
    ok = all(c >= MIN_INK for _n, c, _b in counts)
    print(f"\n{dirpath}  ({len(frames)} frames)  "
          f"{'HUD PRESENT' if ok else 'HUD MISSING OR TOO FAINT'}")
    for name, lit, bg in counts:
        flag = " " if lit >= MIN_INK else "<-- below floor"
        print(f"   {name:<18} corner ink {lit:>6}  bg={bg} {flag}")
    return ok


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    results = {d: check(Path(d)) for d in sys.argv[1:]}
    print("\n=== summary ===")
    for d, ok in results.items():
        print(f"  {'PASS' if ok else 'FAIL'}  {d}")
    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
