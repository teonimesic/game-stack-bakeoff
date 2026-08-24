"""s2_glass - frame renderer.

A GOOD control fixture. Draws the backdrop, the table, the floor and the glass, and the
glass DISPLACES what is behind it rather than tinting it - a cylinder of glass bends the
light through it, and that displacement is the only thing separating a rendered glass
from a rectangle with an alpha value.

    python3 film.py SEED TICKS SCRIPT OUTDIR

The camera lives in `game.py` (`world_to_screen`, `Scene.screen_box`) and is imported
here, so `glass.screen` and the pixels cannot disagree about where the glass was drawn.
A reference whose telemetry and image disagreed could not validate a criterion whose
whole job is to notice a submission whose do.
"""

from __future__ import annotations

import math
import os
import struct
import sys
import zlib

import game as g
from probe import load_script

WIDTH = g.VIEW_W
HEIGHT = g.VIEW_H
MAX_FRAMES = 12

WALL = (0.16, 0.17, 0.22)
TABLE = (0.40, 0.28, 0.19)
FLOOR = (0.21, 0.20, 0.23)
GLASS_TINT = (0.84, 0.93, 0.90)
GLASS_RIM = (0.92, 0.98, 1.00)
WATER_TINT = (0.55, 0.80, 0.92)
CAUSTIC = (1.00, 0.98, 0.80)
DRIP = (0.62, 0.86, 0.96)

#: How far, in pixels, the glass bends what is behind it at its edge. This is what
#: separates a refracting glass from an alpha rectangle: an alpha rectangle leaves the
#: horizontal gradient field behind it untouched, and `glass.refracts` reads exactly
#: that field.
CURVE_PX = 17.0

try:  # the judge ships a PNG writer; fall back to a local copy if it is absent
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__)))))
    from png import write_rgb  # type: ignore
except Exception:  # pragma: no cover - only used when run outside the judge tree
    def write_rgb(path, width, height, pixels):
        raw = bytearray()
        for y in range(height):
            raw.append(0)
            raw += pixels[y * width * 3:(y + 1) * width * 3]

        def chunk(tag, body):
            return (struct.pack(">I", len(body)) + tag + body
                    + struct.pack(">I", zlib.crc32(tag + body) & 0xFFFFFFFF))

        with open(path, "wb") as fh:
            fh.write(b"\x89PNG\r\n\x1a\n"
                     + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
                     + chunk(b"IDAT", zlib.compress(bytes(raw), 6))
                     + chunk(b"IEND", b""))


def _byte(v: float) -> int:
    n = int(v * 255.0 + 0.5)
    return 0 if n < 0 else (255 if n > 255 else n)


def _rgb(c) -> tuple:
    return (_byte(c[0]), _byte(c[1]), _byte(c[2]))


class Canvas:
    def __init__(self, width: int, height: int, background) -> None:
        self.w = width
        self.h = height
        self.buf = bytearray(bytes(background) * (width * height))

    def rect(self, x0: float, y0: float, x1: float, y1: float, colour) -> None:
        xa = max(0, int(min(x0, x1)))
        xb = min(self.w, int(max(x0, x1)) + 1)
        ya = max(0, int(min(y0, y1)))
        yb = min(self.h, int(max(y0, y1)) + 1)
        if xb <= xa or yb <= ya:
            return
        row = bytes(colour) * (xb - xa)
        for y in range(ya, yb):
            i = (y * self.w + xa) * 3
            self.buf[i:i + len(row)] = row

    def get(self, x: int, y: int) -> tuple:
        if x < 0:
            x = 0
        elif x >= self.w:
            x = self.w - 1
        if y < 0:
            y = 0
        elif y >= self.h:
            y = self.h - 1
        i = (y * self.w + x) * 3
        return self.buf[i], self.buf[i + 1], self.buf[i + 2]

    def put(self, x: int, y: int, colour) -> None:
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.buf[i] = colour[0]
            self.buf[i + 1] = colour[1]
            self.buf[i + 2] = colour[2]

    def to_bytes(self) -> bytes:
        return bytes(self.buf)


def draw_backdrop(c: Canvas, sim: g.Scene) -> None:
    """The patterned thing standing behind the glass, plus the table and the floor."""
    table_y = g.world_to_screen(0.0, g.TABLE_Y)[1] * HEIGHT
    floor_y = g.world_to_screen(0.0, g.FLOOR_Y)[1] * HEIGHT
    c.rect(0, 0, WIDTH, table_y, _rgb(WALL))
    cw = WIDTH / float(g.BACKDROP_COLS)
    ch = table_y / float(g.BACKDROP_ROWS)
    for row, tones in enumerate(sim.backdrop):
        for col, tone in enumerate(tones):
            c.rect(col * cw, row * ch, (col + 1) * cw - 1.0, (row + 1) * ch - 1.0,
                   _rgb((WALL[0] * (0.4 + tone * 2.6), WALL[1] * (0.4 + tone * 2.2),
                         WALL[2] * (0.4 + tone * 1.9))))
    c.rect(0, table_y, WIDTH, table_y + 10, _rgb(TABLE))
    c.rect(0, table_y + 10, WIDTH, floor_y, _rgb((TABLE[0] * 0.5, TABLE[1] * 0.5,
                                                  TABLE[2] * 0.5)))
    c.rect(0, floor_y, WIDTH, HEIGHT, _rgb(FLOOR))
    for k in range(9):
        c.rect(k * 74.0, floor_y, k * 74.0 + 5, HEIGHT,
               _rgb((FLOOR[0] * 1.6, FLOOR[1] * 1.6, FLOOR[2] * 1.7)))


def refract(c: Canvas, backdrop: Canvas, cx: float, cy: float,
            half_w: float, half_h: float, angle: float, tint) -> None:
    """Draw a body of glass: what is behind it, DISPLACED, then tinted.

    The displacement is what an alpha overlay does not do, and it is the only difference
    the image-side criterion can see.
    """
    ca, sa = math.cos(-angle), math.sin(-angle)
    x0, x1 = int(cx - half_w - 2), int(cx + half_w + 2)
    y0, y1 = int(cy - half_h - 2), int(cy + half_h + 2)
    for py in range(max(0, y0), min(HEIGHT, y1 + 1)):
        for px in range(max(0, x0), min(WIDTH, x1 + 1)):
            # into the glass's own frame
            dx, dy = px - cx, py - cy
            lx = dx * ca - dy * sa
            ly = dx * sa + dy * ca
            u = lx / half_w
            v = ly / half_h
            if u * u > 1.0 or v * v > 1.0:
                continue
            bend = CURVE_PX * u * (1.0 - 0.35 * v * v)
            src = backdrop.get(int(px + bend), int(py + 5.0 * u * u))
            edge = 1.0 if abs(u) < 0.86 else 1.45
            c.put(px, py, (_byte(src[0] / 255.0 * tint[0] * edge),
                           _byte(src[1] / 255.0 * tint[1] * edge),
                           _byte(src[2] / 255.0 * tint[2] * edge)))


def render(sim: g.Scene) -> bytes:
    st = sim.state()
    f = sim.forward(sim.forward_index(sim.tick))
    backdrop = Canvas(WIDTH, HEIGHT, _rgb(WALL))
    draw_backdrop(backdrop, sim)
    c = Canvas(WIDTH, HEIGHT, _rgb(WALL))
    c.buf[:] = backdrop.buf

    box = st["glass"]["screen"]
    if st["glass"]["intact"]:
        cx, cy = box["x"] * WIDTH, box["y"] * HEIGHT
        hw, hh = box["w"] * WIDTH * 0.5, box["h"] * HEIGHT * 0.5
        # light thrown onto the table beside the glass, moving with it
        caustic_y = g.world_to_screen(0.0, g.TABLE_Y)[1] * HEIGHT
        if f["gy"] >= g.TABLE_Y - 1.0:
            c.rect(cx - hw * 1.7, caustic_y, cx + hw * 1.7, caustic_y + 9,
                   _rgb((CAUSTIC[0] * 0.55, CAUSTIC[1] * 0.54, CAUSTIC[2] * 0.42)))
        refract(c, backdrop, cx, cy, hw, hh, f["angle"], GLASS_TINT)
        # the water inside it: its top surface is horizontal on screen, always
        vol = st["water"]["volume"]
        if vol > 0.005:
            top = cy + hh - 2.0 * hh * vol
            for py in range(int(max(0, top)), int(min(HEIGHT, cy + hh))):
                for px in range(int(max(0, cx - hw)), int(min(WIDTH, cx + hw + 1))):
                    dx, dy = px - cx, py - cy
                    ca, sa = math.cos(-f["angle"]), math.sin(-f["angle"])
                    u = (dx * ca - dy * sa) / hw
                    v = (dx * sa + dy * ca) / hh
                    if u * u > 0.82 or v * v > 1.0:
                        continue
                    src = c.get(px, py)
                    c.put(px, py, (_byte(src[0] / 255.0 * WATER_TINT[0]),
                                   _byte(src[1] / 255.0 * WATER_TINT[1]),
                                   _byte(src[2] / 255.0 * WATER_TINT[2])))
        c.rect(cx - hw, cy - hh, cx + hw, cy - hh + 3, _rgb(GLASS_RIM))
    else:
        for p in st["pieces"]:
            sx, sy = g.world_to_screen(p["x"], p["y"])
            px, py = sx * WIDTH, sy * HEIGHT
            r = 3.0 + 9.0 * abs(p["up"][0]) + 3.0
            refract(c, backdrop, px, py, r, r * 0.8,
                    math.atan2(p["up"][0], p["up"][1]), GLASS_TINT)

    # a drop or two on their way down, while the glass is still draining
    if st["phase"] == "draining" and st["glass"]["intact"]:
        cx = box["x"] * WIDTH
        base = (box["y"] + box["h"] * 0.5) * HEIGHT
        for k in range(2):
            dy = ((sim.tick * 3 + k * 17) % 26)
            c.rect(cx - 2, base + dy, cx + 2, base + dy + 5, _rgb(DRIP))
    return c.to_bytes()


def frame_ticks(ticks: int) -> list:
    """`floor(i * TICKS / 11)` for i in 0..11 - the four starters' capture schedule."""
    if ticks <= 0:
        return [0]
    return sorted({(i * ticks) // (MAX_FRAMES - 1) for i in range(MAX_FRAMES)})


def main(argv: list) -> int:
    if len(argv) < 4:
        print("usage: film.py SEED TICKS SCRIPT OUTDIR", file=sys.stderr)
        return 2
    seed, ticks, script, outdir = int(argv[0]), int(argv[1]), argv[2], argv[3]
    os.makedirs(outdir, exist_ok=True)
    scripted = load_script(script)
    wanted = frame_ticks(ticks)
    sim = g.Scene(seed)
    index = 0
    if 0 in wanted:
        write_rgb(os.path.join(outdir, "frame_%04d.png" % index), WIDTH, HEIGHT,
                  render(sim))
        index += 1
    for t in range(1, ticks + 1):
        sim.step(scripted[t - 1] if t - 1 < len(scripted) else {})
        if t in wanted:
            write_rgb(os.path.join(outdir, "frame_%04d.png" % index), WIDTH, HEIGHT,
                      render(sim))
            index += 1
    print("film: wrote %d frames to %s" % (index, outdir), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
