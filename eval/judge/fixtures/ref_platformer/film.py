"""Sprite platformer - frame renderer.

A GOOD control fixture. Draws a side-on view of the live simulation: the stage, the
platforms, the character with its facing and swing, the enemies and a small HUD.

The camera FOLLOWS the player, because a 2400-unit stage in a 640-pixel frame would
render the character four pixels wide and every frame would look the same - which is
exactly the kind of capture defect that cost this project three criteria (FINDINGS #26).

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
HITBOX = (255, 240, 120)
GOAL = (120, 255, 200)
PLATFORM = (90, 84, 130)
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



CAM_HALF = 320.0


def render(sim):
    c = Canvas(WIDTH, HEIGHT, BG)
    cam = min(max(sim.px, CAM_HALF), g.LEVEL_W - CAM_HALF)

    def sx(x):
        return (x - cam) + CAM_HALF

    def sy(y):
        return HEIGHT - 60 - y * 0.7

    for k in range(0, int(g.LEVEL_W), 100):
        c.rect(sx(k) - 1, 0, sx(k) + 1, HEIGHT, GRID)
    for p in g.PLATFORMS:
        c.rect(sx(p["x"] - p["w"] / 2), sy(p["y"] + p["h"] / 2),
               sx(p["x"] + p["w"] / 2), sy(p["y"] - p["h"] / 2), PLATFORM)
    c.rect(sx(g.GOAL_X) - 3, sy(200), sx(g.GOAL_X) + 3, sy(0), GOAL)

    for e in sim.enemies:
        col = ENEMY if e["hp"] <= 1 else ENEMY_TOUGH
        c.rect(sx(e["x"] - g.ENEMY_HW), sy(e["y"] + g.ENEMY_HH),
               sx(e["x"] + g.ENEMY_HW), sy(e["y"] - g.ENEMY_HH), col)

    hx, hy, hw, hh = sim.hitbox()
    if hw > 0.0:
        c.rect(sx(hx - hw / 2), sy(hy + hh / 2), sx(hx + hw / 2), sy(hy - hh / 2), HITBOX)

    if sim.alive:
        body = PLAYER_HURT if sim.invuln > 0 else PLAYER
        c.rect(sx(sim.px - g.PLAYER_HW), sy(sim.py + g.PLAYER_HH),
               sx(sim.px + g.PLAYER_HW), sy(sim.py - g.PLAYER_HH), body)
        # facing marker, so a still frame says which way the character is looking
        c.rect(sx(sim.px + sim.facing * g.PLAYER_HW) - 3, sy(sim.py + 8),
               sx(sim.px + sim.facing * g.PLAYER_HW) + 3, sy(sim.py), AIM)
    else:
        c.rect(sx(sim.px) - 12, sy(sim.py) - 6, sx(sim.px) + 12, sy(sim.py) + 6, DEAD)

    # HUD, drawn every frame so the capture always carries the score and health.
    for i in range(g.PLAYER_START_HP):
        c.rect(20 + i * 22, 18, 36 + i * 22, 30,
               HP_FULL if i < sim.hp else HP_EMPTY)
    c.rect(20, HEIGHT - 22, 20 + min(600, sim.score // 2), HEIGHT - 14, WAVE_PIP)
    # an anim-frame tick strip: the frames differ even when the character stands still
    c.rect(WIDTH - 40 - sim.anim_frame * 8, 18, WIDTH - 34 - sim.anim_frame * 8, 30, AIM)
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
