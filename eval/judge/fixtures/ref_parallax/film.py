"""s1_parallax - frame renderer.

A GOOD control fixture. Draws the scene the simulation describes, and draws it the way
the telemetry says it is drawn: each layer is tiled inside the band `game.BANDS` gives
it and displaced by that layer's own `offset`, so the image-side parallax check and the
telemetry-side one are looking at the same thing rather than at two independent claims.

    python3 film.py SEED TICKS SCRIPT OUTDIR

CAPTURE TICKS ARE `floor(i * TICKS / 11)` for i in 0..11, which is what all four
starters' `just film` recipes do (`eval/SCENES.md`). At the scene's 660 ticks that is
0, 60, 120 ... 660 exactly, so nothing here depends on a rounding convention.
"""

from __future__ import annotations

import math
import os
import struct
import sys
import zlib

import game as g
from probe import load_script

WIDTH = 640
HEIGHT = 360
MAX_FRAMES = 12

#: Pixels per world unit. Everything horizontal is drawn through this, so changing the
#: capture size zooms the picture instead of widening the window onto it - which is what
#: a camera does, and what makes `the same scene filmed 1.5x larger` a test of the
#: judge's geometry-independence rather than a different scene.
SCALE = WIDTH / 640.0

#: Where the car sits in the frame. The camera follows it, so the car is stationary on
#: screen and the world moves past - which is what makes a layer's on-screen shift a
#: measurement of that layer's scroll rate and nothing else.
CAR_SCREEN_X = 200.0
CAR_W = 76.0
CAR_TOP = 0.685
CAR_BOTTOM = 0.795
WHEEL_Y = 0.815
FRONT_TOP = 0.63
FRONT_BOTTOM = 0.90

#: Base colours per layer, before the key light is applied.
LAYER_BASE = {1: (0.55, 0.72, 1.00), 2: (0.34, 0.42, 0.55),
              3: (0.20, 0.34, 0.24), 4: (0.62, 0.60, 0.58)}

#: Ambient floor: how much of a surface's colour survives with the key light at zero.
#: A night road lit by nothing at all quantises to a flat block of near-black, and a
#: flat block carries no horizontal structure for anything to measure - so a scene that
#: is CORRECT about its parallax would be unmeasurable at night purely because 8-bit
#: colour ran out. Streetlight and moonlight are what a night road actually has.
AMBIENT = 0.28
CAR_BODY = (0.86, 0.22, 0.24)
CAR_CABIN = (0.72, 0.85, 0.95)
WHEEL = (0.10, 0.10, 0.12)
SPOKE = (0.85, 0.85, 0.88)
POLE = (0.14, 0.12, 0.14)
HEADLIGHT = (1.0, 0.95, 0.72)

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

        # Atomic, like the judge's own writer: a partial frame at the final path is
        # indistinguishable from a complete one until something opens it.
        tmp = path + ".part"
        try:
            with open(tmp, "wb") as fh:
                fh.write(b"\x89PNG\r\n\x1a\n"
                         + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
                         + chunk(b"IDAT", zlib.compress(bytes(raw), 6))
                         + chunk(b"IEND", b""))
            os.replace(tmp, path)
        except BaseException:
            if os.path.exists(tmp):
                os.remove(tmp)
            raise


def _byte(v: float) -> int:
    n = int(v * 255.0 + 0.5)
    return 0 if n < 0 else (255 if n > 255 else n)


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


def _lit(colour, key):
    k = [AMBIENT + (1.0 - AMBIENT) * key[i] for i in range(3)]
    return (_byte(colour[0] * k[0]), _byte(colour[1] * k[1]),
            _byte(colour[2] * k[2]))


def render(sim: g.Scene) -> bytes:
    st = sim.state()
    key = st["light"]["key"]
    sky = st["light"]["sky"]
    c = Canvas(WIDTH, HEIGHT, (_byte(sky[0]), _byte(sky[1]), _byte(sky[2])))

    for layer in st["layers"]:
        lid = layer["id"]
        span = layer["span"] * SCALE
        top = layer["top"] * HEIGHT
        bottom = layer["bottom"] * HEIGHT
        base = LAYER_BASE[lid]
        # The band's own ground tone, so a layer is visible even between its bars.
        c.rect(0, top, WIDTH, bottom, _lit((base[0] * 0.55, base[1] * 0.55,
                                            base[2] * 0.55), key))
        phase = (layer["offset"] * SCALE) % span
        first = -1
        last = int(WIDTH / span) + 2
        for k in range(first, last):
            tile_x = k * span - phase
            for pos, width, bright in sim.texture[lid]:
                x0 = tile_x + pos * span
                x1 = x0 + width * span
                colour = _lit((base[0] * bright, base[1] * bright, base[2] * bright),
                              key)
                # Bars of differing height inside the band, so the band carries
                # vertical structure as well as horizontal.
                y0 = top + (bottom - top) * (1.0 - 0.35 - 0.55 * bright)
                c.rect(x0, y0, x1, bottom, colour)

    car_x = st["car"]["x"]
    car_px = CAR_SCREEN_X * SCALE
    car_w = CAR_W * SCALE
    # Things drawn in front of the car, in world coordinates the camera follows.
    for f in sim.front:
        sx = (f["x"] - car_x) * SCALE + car_px
        half = f["span"] * 0.5 * SCALE
        if sx < -half - 4 or sx > WIDTH + half + 4:
            continue
        top = HEIGHT * (FRONT_BOTTOM - (FRONT_BOTTOM - FRONT_TOP) * f["height"])
        c.rect(sx - half, top, sx + half, HEIGHT * FRONT_BOTTOM, _lit(POLE, key))

    # Headlights reach down the road, and are worth more the darker it gets.
    dark = 1.0 - st["light"]["phase"]
    if st["light"]["phase"] > 0.15:
        beam = (HEADLIGHT[0] * (1.0 - dark * 0.5), HEADLIGHT[1] * (1.0 - dark * 0.5),
                HEADLIGHT[2] * (1.0 - dark * 0.5))
        c.rect(car_px + car_w * 0.5, HEIGHT * 0.76,
               car_px + car_w * 0.5 + 74 * SCALE, HEIGHT * 0.80,
               (_byte(beam[0]), _byte(beam[1]), _byte(beam[2])))

    c.rect(car_px - car_w * 0.5, HEIGHT * CAR_TOP,
           car_px + car_w * 0.5, HEIGHT * CAR_BOTTOM, _lit(CAR_BODY, key))
    c.rect(car_px - car_w * 0.22, HEIGHT * (CAR_TOP - 0.045),
           car_px + car_w * 0.24, HEIGHT * CAR_TOP, _lit(CAR_CABIN, key))
    for w in st["car"]["wheels"]:
        wx = car_px + (w["x"] - car_x) * SCALE
        wy = HEIGHT * WHEEL_Y
        c.disc(wx, wy, 13.0 * SCALE, _lit(WHEEL, key))
        # A spoke, so the wheel's rotation is visible in the frame as well as reported.
        a = w["angle"]
        c.rect(wx + (math.cos(a) * 3 - 2) * SCALE, wy + (math.sin(a) * 3 - 2) * SCALE,
               wx + (math.cos(a) * 9 + 2) * SCALE, wy + (math.sin(a) * 9 + 2) * SCALE,
               _lit(SPOKE, key))
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
