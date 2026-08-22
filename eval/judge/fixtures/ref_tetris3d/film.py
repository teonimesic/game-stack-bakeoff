"""3D Tetris - frame renderer.

A GOOD control fixture. Draws the well in an isometric projection: settled
cells, the falling piece, the column heights and the score read-out.

    python3 film.py SEED TICKS SCRIPT OUTDIR
"""

from __future__ import annotations

import os
import struct
import sys
import zlib

import game as g
from probe import load_script

WIDTH = 640
HEIGHT = 400
MAX_FRAMES = 12

BG = (12, 14, 22)
FLOOR = (62, 72, 100)
FLOOR_ALT = (44, 52, 76)
SHADOW = (110, 118, 150)
CAGE = (34, 40, 58)
PIECE_EDGE = (250, 250, 250)
HUD = (120, 200, 160)
HUD_DIM = (48, 70, 62)

KIND_COLOUR = {
    "I": (86, 200, 255),
    "O": (250, 210, 90),
    "L": (255, 148, 78),
    "T": (196, 120, 255),
    "S": (110, 230, 130),
    "Y": (255, 100, 140),
    "W": (120, 160, 255),
}

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
        row = bytes(colour) * max(0, xb - xa)
        for y in range(ya, yb):
            i = (y * self.w + xa) * 3
            self.buf[i:i + len(row)] = row

    def to_bytes(self) -> bytes:
        return bytes(self.buf)


CELL = 30.0
ORIGIN_X = 300.0
ORIGIN_Y = 348.0
Y_RISE = 20.0
DEPTH_RISE = 9.0


def project(x: float, y: float, z: float):
    return (ORIGIN_X + (x - z) * CELL * 0.5,
            ORIGIN_Y - y * Y_RISE - (x + z) * DEPTH_RISE)


def cube(c: Canvas, x: int, y: int, z: int, colour, outline=False) -> None:
    px, py = project(x, y, z)
    half = CELL * 0.42
    c.rect(px - half, py - half, px + half, py + half, colour)
    if outline:
        c.rect(px - half, py - half, px + half, py - half + 2, PIECE_EDGE)
        c.rect(px - half, py + half - 2, px + half, py + half, PIECE_EDGE)


def render(sim: g.Game) -> bytes:
    c = Canvas(WIDTH, HEIGHT, BG)
    # well cage: a faint post at each corner column so the volume reads
    for x in (0, g.WELL_W - 1):
        for z in (0, g.WELL_D - 1):
            x0, y0 = project(x, -1, z)
            _x1, y1 = project(x, g.WELL_H, z)
            c.rect(x0 - 1, y0, x0 + 1, y1, CAGE)
    # well floor, as a checkerboard so the two horizontal axes read apart,
    # with the falling piece's footprint highlighted
    footprint = {(cell[0], cell[2]) for cell in sim.piece_cells}
    for x in range(g.WELL_W):
        for z in range(g.WELL_D):
            if (x, z) in footprint:
                colour = SHADOW
            else:
                colour = FLOOR if (x + z) % 2 == 0 else FLOOR_ALT
            cube(c, x, -1, z, colour)
    # settled cells, painted back to front
    cells = sorted(sim.grid.items(), key=lambda kv: (kv[0][1], -(kv[0][0] + kv[0][2])))
    for (x, y, z), kind in cells:
        base = KIND_COLOUR.get(kind, (180, 180, 180))
        cube(c, x, y, z, (base[0] // 2, base[1] // 2, base[2] // 2))
    # falling piece, bright and outlined
    if sim.piece_kind is not None:
        colour = KIND_COLOUR.get(sim.piece_kind, (255, 255, 255))
        for x, y, z in sorted(sim.piece_cells, key=lambda p: (p[1], -(p[0] + p[2]))):
            cube(c, x, y, z, colour, outline=True)
    # HUD: column height bars, score bar, level pips
    heights = sim.heights()
    for x in range(g.WELL_W):
        for z in range(g.WELL_D):
            h = heights[x][z]
            bx = 20 + (x * g.WELL_D + z) * 9
            c.rect(bx, 380, bx + 6, 380 - h * 6, HUD if h else HUD_DIM)
    c.rect(20, 20, 20 + min(560, sim.score // 8), 30, HUD)
    for i in range(sim.level):
        c.rect(20 + i * 10, 38, 26 + i * 10, 46, HUD)
    for i in range(min(40, sim.layers_cleared)):
        c.rect(WIDTH - 26 - i * 6, 20, WIDTH - 22 - i * 6, 30, KIND_COLOUR["O"])
    if sim.game_over:
        c.rect(200, 180, 440, 220, (200, 40, 60))
    return c.to_bytes()


def frame_ticks(ticks: int) -> list:
    if ticks <= 0:
        return [0]
    n = min(MAX_FRAMES, ticks + 1)
    picked = sorted({round(i * ticks / (n - 1)) for i in range(n)})
    if picked[-1] != ticks:
        picked.append(ticks)
    return picked


def main(argv: list) -> int:
    if len(argv) < 4:
        print("usage: film.py SEED TICKS SCRIPT OUTDIR", file=sys.stderr)
        return 2
    seed, ticks, script, outdir = int(argv[0]), int(argv[1]), argv[2], argv[3]
    os.makedirs(outdir, exist_ok=True)
    scripted = load_script(script)
    wanted = frame_ticks(ticks)
    sim = g.Game(seed)
    index = 0
    if 0 in wanted:
        write_rgb(os.path.join(outdir, "frame_%04d.png" % index), WIDTH, HEIGHT, render(sim))
        index += 1
    for t in range(1, ticks + 1):
        sim.step(scripted[t - 1] if t - 1 < len(scripted) else {})
        if t in wanted:
            write_rgb(os.path.join(outdir, "frame_%04d.png" % index), WIDTH, HEIGHT, render(sim))
            index += 1
    print("film: wrote %d frames to %s" % (index, outdir), file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
