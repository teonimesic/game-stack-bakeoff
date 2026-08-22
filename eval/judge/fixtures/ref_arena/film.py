"""Twin-stick arena shooter - frame renderer.

A GOOD control fixture. Draws a top-down schematic of the live simulation:
arena bounds, the player and its aim, enemies, bullets and a small HUD.

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

BG = (16, 14, 24)
FLOOR = (26, 24, 40)
WALL = (110, 100, 160)
GRID = (34, 32, 52)
PLAYER = (110, 240, 150)
PLAYER_HURT = (250, 240, 120)
AIM = (240, 250, 200)
ENEMY = (240, 80, 90)
ENEMY_TOUGH = (255, 160, 60)
SPAWNING = (120, 90, 200)   # materialising, and deliberately unlike either
BULLET = (250, 240, 140)
HP_FULL = (110, 240, 150)
HP_EMPTY = (60, 50, 60)
WAVE_PIP = (150, 160, 255)
DEAD = (200, 40, 60)

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

    def line(self, x0: float, y0: float, x1: float, y1: float, colour, width: float = 2.0):
        steps = int(max(abs(x1 - x0), abs(y1 - y0))) + 1
        for i in range(steps + 1):
            t = i / steps
            self.rect(x0 + (x1 - x0) * t - width, y0 + (y1 - y0) * t - width,
                      x0 + (x1 - x0) * t + width, y0 + (y1 - y0) * t + width, colour)

    def to_bytes(self) -> bytes:
        return bytes(self.buf)


SCALE = 0.76
CX = 320.0
CY = 200.0


def sx(x: float) -> float:
    return CX + x * SCALE


def sy(y: float) -> float:
    return CY - y * SCALE


def render(sim: g.Game) -> bytes:
    c = Canvas(WIDTH, HEIGHT, BG)
    c.rect(sx(-g.ARENA_HALF_X), sy(g.ARENA_HALF_Y), sx(g.ARENA_HALF_X), sy(-g.ARENA_HALF_Y), FLOOR)
    for k in range(-3, 4):
        c.rect(sx(k * 100.0) - 1, sy(g.ARENA_HALF_Y), sx(k * 100.0) + 1, sy(-g.ARENA_HALF_Y), GRID)
        c.rect(sx(-g.ARENA_HALF_X), sy(k * 100.0) - 1, sx(g.ARENA_HALF_X), sy(k * 100.0) + 1, GRID)
    # arena walls
    c.rect(sx(-g.ARENA_HALF_X) - 4, sy(g.ARENA_HALF_Y) - 4, sx(g.ARENA_HALF_X) + 4, sy(g.ARENA_HALF_Y), WALL)
    c.rect(sx(-g.ARENA_HALF_X) - 4, sy(-g.ARENA_HALF_Y), sx(g.ARENA_HALF_X) + 4, sy(-g.ARENA_HALF_Y) + 4, WALL)
    c.rect(sx(-g.ARENA_HALF_X) - 4, sy(g.ARENA_HALF_Y), sx(-g.ARENA_HALF_X), sy(-g.ARENA_HALF_Y), WALL)
    c.rect(sx(g.ARENA_HALF_X), sy(g.ARENA_HALF_Y), sx(g.ARENA_HALF_X) + 4, sy(-g.ARENA_HALF_Y), WALL)
    # enemies
    for e in sim.enemies:
        colour = ENEMY if e["hp"] <= 1 else ENEMY_TOUGH
        if e["spawn"] > 0:
            colour = SPAWNING          # materialising: visibly distinct, not yet solid
        # DEPTH CUE. The view is the x-y plane, so z has to be carried by size or it
        # is invisible: an enemy at the far wall must not look like one at the near.
        depth = 1.0 + 0.6 * (-e["z"] / g.ARENA_HALF_Z)
        c.disc(sx(e["x"]), sy(e["y"]), g.ENEMY_RADIUS * SCALE * depth, colour)
        c.rect(sx(e["x"]) - 3, sy(e["y"]) - 3, sx(e["x"]) + 3, sy(e["y"]) + 3, (20, 10, 14))
    # bullets, drawn as short tracers along their velocity
    for b in sim.bullets:
        tx = b["x"] - b["vx"] * g.DT * 3.0
        ty = b["y"] - b["vy"] * g.DT * 3.0
        c.line(sx(tx), sy(ty), sx(b["x"]), sy(b["y"]), BULLET, 2.0)
    # player and aim
    if sim.alive:
        body = PLAYER_HURT if sim.invuln > 0 else PLAYER
        c.disc(sx(sim.px), sy(sim.py), g.PLAYER_RADIUS * SCALE, body)
        c.line(sx(sim.px), sy(sim.py),
               sx(sim.px + sim.aim_x * 40.0), sy(sim.py + sim.aim_y * 40.0), AIM, 2.0)
    else:
        c.rect(sx(sim.px) - 12, sy(sim.py) - 12, sx(sim.px) + 12, sy(sim.py) + 12, DEAD)
    # HUD: health, wave pips, score bar
    for i in range(g.PLAYER_START_HP):
        c.rect(20 + i * 22, 10, 36 + i * 22, 24, HP_FULL if i < sim.hp else HP_EMPTY)
    for i in range(min(30, sim.wave)):
        c.rect(WIDTH - 26 - i * 8, 10, WIDTH - 21 - i * 8, 24, WAVE_PIP)
    c.rect(20, HEIGHT - 22, 20 + min(600, sim.score // 5), HEIGHT - 14, BULLET)
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
