"""Pong - frame renderer.

A GOOD control fixture. Draws a schematic top-down view of the live simulation.

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

BG = (14, 18, 30)
NET = (52, 62, 88)
WALL = (96, 110, 150)
LEFT_COLOUR = (86, 200, 255)
RIGHT_COLOUR = (255, 138, 96)
BALL_COLOUR = (250, 232, 96)
TRAIL = (140, 128, 70)
GUIDE = (44, 54, 78)

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

    def disc(self, cx: float, cy: float, r: float, colour) -> None:
        rr = r * r
        for y in range(max(0, int(cy - r)), min(self.h, int(cy + r) + 1)):
            dy = y - cy
            span = rr - dy * dy
            if span < 0:
                continue
            dx = span ** 0.5
            self.rect(cx - dx, y, cx + dx, y, colour)

    def to_bytes(self) -> bytes:
        return bytes(self.buf)


SCALE = 0.75
CX = 320.0
CY = 200.0


def sx(x: float) -> float:
    return CX + x * SCALE


def sy(y: float) -> float:
    return CY - y * SCALE


def render(sim: g.Game) -> bytes:
    c = Canvas(WIDTH, HEIGHT, BG)
    # arena walls
    c.rect(sx(-g.ARENA_HALF_W), sy(g.ARENA_HALF_H) - 4, sx(g.ARENA_HALF_W), sy(g.ARENA_HALF_H), WALL)
    c.rect(sx(-g.ARENA_HALF_W), sy(-g.ARENA_HALF_H), sx(g.ARENA_HALF_W), sy(-g.ARENA_HALF_H) + 4, WALL)
    # net
    for k in range(12):
        top = g.ARENA_HALF_H - k * 40.0
        c.rect(CX - 2, sy(top), CX + 2, sy(top - 22.0), NET)
    # tracer guides - a schematic read-out of where the ball is right now
    c.rect(sx(sim.ball_x) - 1, sy(g.ARENA_HALF_H), sx(sim.ball_x) + 1, sy(-g.ARENA_HALF_H), GUIDE)
    c.rect(sx(-g.ARENA_HALF_W), sy(sim.ball_y) - 1, sx(g.ARENA_HALF_W), sy(sim.ball_y) + 1, GUIDE)
    # paddles
    for x, py, colour in ((-g.PADDLE_X, sim.left_y, LEFT_COLOUR),
                          (g.PADDLE_X, sim.right_y, RIGHT_COLOUR)):
        c.rect(sx(x - g.PADDLE_HALF_W), sy(py + g.PADDLE_HALF_H),
               sx(x + g.PADDLE_HALF_W), sy(py - g.PADDLE_HALF_H), colour)
    # velocity streak behind the ball, then the ball itself
    for k in range(1, 9):
        tx = sim.ball_x - sim.ball_vx * g.DT * k
        ty = sim.ball_y - sim.ball_vy * g.DT * k
        c.disc(sx(tx), sy(ty), 7.0 - 0.6 * k, TRAIL)
    c.disc(sx(sim.ball_x), sy(sim.ball_y), g.BALL_RADIUS * SCALE + 4.0, BALL_COLOUR)
    # score pips
    for i in range(sim.score_left):
        c.rect(20 + i * 12, 10, 28 + i * 12, 22, LEFT_COLOUR)
    for i in range(sim.score_right):
        c.rect(WIDTH - 28 - i * 12, 10, WIDTH - 20 - i * 12, 22, RIGHT_COLOUR)
    # rally meter
    c.rect(CX - 60, HEIGHT - 18, CX - 60 + min(120, sim.rally * 8), HEIGHT - 10, BALL_COLOUR)
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
