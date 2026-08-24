"""s1_parallax - reference simulation. A car on a looping road, day into night.

A GOOD control fixture: an honest implementation of the `s1_parallax` scene contract as
`eval/suites/rendered/s1_parallax__*.txt` states it. Pure simulation, no I/O, no
wall-clock time, no `random` module. Everything that varies comes from a seeded
SplitMix64.

WHY EACH BEHAVIOUR IS HERE, since a reference that does not exhibit a behaviour cannot
validate the criterion that measures it (FINDINGS #34):

* four layers whose scroll RATES are ordered by declared depth, and whose rates are
  spread widely enough that the ordering survives being measured in whole pixels;
* a car speed that WOBBLES, so `wheels.match_speed` can separate a wheel driven by the
  ground speed from one spun at the mean rate. A constant-speed scene is legal and is
  the `constant car speed` variant, which every criterion must still pass;
* spans small enough that layers wrap between captured frames, so `loop.seamless` has a
  wrap to look at rather than a precondition it cannot establish;
* a light ramp 300 ticks wide, so at least three captured frames land strictly inside
  it and the image half of `light.monotonic` is establishable.
"""

from __future__ import annotations

import math
import struct

TICK_HZ = 60
DT = 1.0 / TICK_HZ

#: World units per second along +x. The car never stops and never reverses.
BASE_SPEED = 120.0
#: Fraction of BASE_SPEED the speed swings by. Non-zero on purpose - see the module
#: docstring. `SPEED_WOBBLE = 0.0` is the constant-speed variant.
SPEED_WOBBLE = 0.18
SPEED_PERIOD = 370.0        # ticks per full swing; not a divisor of the frame spacing

WHEEL_RADIUS = 14.0
WHEELS = ((1, -26.0), (2, 26.0))     # (id, offset from the car's centre along x)

#: (id, depth, span). Depth is "further from the camera"; the scroll rate is
#: 1 / (1 + depth), so the rates are 1/9, 1/5, 1/3, 1/2 - spread by more than 4x, which
#: is what keeps the ordering readable after the image shift is rounded to whole pixels.
LAYERS = ((1, 8.0, 120.0), (2, 4.0, 160.0), (3, 2.0, 220.0), (4, 1.0, 260.0))

#: Where each layer is drawn in the captured frame, as fractions of frame height.
#: film.py reads this and `state()` reports it, so the two cannot disagree.
BANDS = {1: (0.00, 0.30), 2: (0.30, 0.52), 3: (0.52, 0.66), 4: (0.66, 1.00)}

LIGHT_BEGIN = 240
LIGHT_END = 540

DAY_SKY = (0.42, 0.62, 0.94)
NIGHT_SKY = (0.03, 0.04, 0.13)
DAY_KEY = (1.00, 0.97, 0.90)
NIGHT_KEY = (0.15, 0.18, 0.32)

#: Things that pass between the camera and the car.
FRONT_COUNT = 6
FRONT_SPAN = 26.0

_M64 = 0xFFFFFFFFFFFFFFFF


class Rng:
    """SplitMix64 - small, seeded, deterministic."""

    def __init__(self, seed: int) -> None:
        self.state = seed & _M64

    def next_u64(self) -> int:
        self.state = (self.state + 0x9E3779B97F4A7C15) & _M64
        z = self.state
        z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & _M64
        z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & _M64
        return (z ^ (z >> 31)) & _M64

    def unit(self) -> float:
        return (self.next_u64() >> 11) * (1.0 / (1 << 53))

    def between(self, lo: float, hi: float) -> float:
        return lo + (hi - lo) * self.unit()


class Hasher:
    """FNV-1a 64 over a canonical encoding of the simulation state."""

    def __init__(self) -> None:
        self.h = 0xCBF29CE484222325

    def _raw(self, data: bytes) -> None:
        h = self.h
        for b in data:
            h = ((h ^ b) * 0x100000001B3) & _M64
        self.h = h

    def i(self, n: int) -> "Hasher":
        self._raw(struct.pack("<q", int(n)))
        return self

    def u(self, n: int) -> "Hasher":
        self._raw(struct.pack("<Q", int(n) & _M64))
        return self

    def f(self, x: float) -> "Hasher":
        v = float(x)
        if v == 0.0:
            v = 0.0
        self._raw(struct.pack("<d", v))
        return self

    def s(self, text: str) -> "Hasher":
        self._raw(text.encode("utf-8"))
        return self

    def hex(self) -> str:
        return "0x%016x" % self.h


def _r(v: float) -> float:
    out = round(float(v), 6)
    return 0.0 if out == 0.0 else out


def _lerp3(a, b, t):
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))


def rate_for(depth: float) -> float:
    """How fast a layer at `depth` scrolls, as a fraction of the car's travel."""
    return 1.0 / (1.0 + depth)


class Scene:
    """The whole of the parallax scene. `step` takes the (ignored) input object."""

    def __init__(self, seed: int) -> None:
        self.seed = int(seed) & _M64
        self.reset()

    def reset(self) -> None:
        self.tick = 0
        self.rng = Rng(self.seed ^ 0x5CE7E)
        self.car_x = 0.0
        self.speed = self.speed_at(0)
        self.wheel_angle = 0.0
        self.offsets = {lid: 0.0 for lid, _, _ in LAYERS}
        self.wraps = {lid: 0 for lid, _, _ in LAYERS}
        # Seeded placement: where the foreground things stand, and how tall each is.
        self.front = []
        x = 150.0
        for i in range(FRONT_COUNT):
            x += self.rng.between(140.0, 260.0)
            self.front.append({"id": i + 1, "x": x, "span": FRONT_SPAN,
                               "height": self.rng.between(0.55, 1.0)})
        self.covering = set()
        # Seeded layer texture: the tile pattern film.py draws, per layer.
        self.texture = {}
        for lid, _, _span in LAYERS:
            bars = []
            for _ in range(5):
                bars.append((self.rng.between(0.02, 0.98), self.rng.between(0.05, 0.22),
                             self.rng.between(0.25, 1.0)))
            self.texture[lid] = tuple(bars)
        self.light_started = False
        self.light_finished = False

    # ------------------------------------------------------------------ sim

    def speed_at(self, tick: int) -> float:
        return BASE_SPEED * (1.0 + SPEED_WOBBLE
                             * math.sin(2.0 * math.pi * tick / SPEED_PERIOD))

    def step(self, inputs: dict) -> list:
        """One tick. `inputs` is ignored - the scene has no player."""
        events: list = []
        self.tick += 1
        self.speed = self.speed_at(self.tick)
        travel = self.speed * DT
        self.car_x += travel
        # Rolling without slipping: the wheel turns by arc / radius.
        self.wheel_angle += travel / WHEEL_RADIUS

        for lid, depth, span in LAYERS:
            self.offsets[lid] = self.car_x * rate_for(depth)
            n = int(self.offsets[lid] // span)
            if n > self.wraps[lid]:
                self.wraps[lid] = n
                events.append("wrap")

        for f in self.front:
            covered = abs(self.car_x - f["x"]) <= f["span"] * 0.5
            if covered and f["id"] not in self.covering:
                self.covering.add(f["id"])
                events.append("front_enter")
            elif not covered and f["id"] in self.covering:
                self.covering.discard(f["id"])
                events.append("front_exit")

        ph = self.light_phase()
        if ph > 0.0 and not self.light_started:
            self.light_started = True
            events.append("light_begin")
        if ph >= 1.0 and not self.light_finished:
            self.light_finished = True
            events.append("light_end")
        return events

    def light_phase(self) -> float:
        if self.tick <= LIGHT_BEGIN:
            return 0.0
        if self.tick >= LIGHT_END:
            return 1.0
        u = (self.tick - LIGHT_BEGIN) / float(LIGHT_END - LIGHT_BEGIN)
        # smoothstep: still strictly increasing, so the ramp is monotonic either way
        return u * u * (3.0 - 2.0 * u)

    # ---------------------------------------------------------------- views

    def state(self) -> dict:
        ph = self.light_phase()
        return {
            "car": {
                "x": _r(self.car_x), "y": 0.0, "speed": _r(self.speed),
                "wheels": [{"id": wid, "x": _r(self.car_x + dx), "y": 0.0,
                            "radius": WHEEL_RADIUS, "angle": _r(self.wheel_angle)}
                           for wid, dx in WHEELS],
            },
            "layers": [{"id": lid, "depth": depth,
                        "offset": _r(self.offsets[lid]), "span": span,
                        "top": BANDS[lid][0], "bottom": BANDS[lid][1]}
                       for lid, depth, span in LAYERS],
            "front": [{"id": f["id"], "x": _r(f["x"]), "span": f["span"]}
                      for f in self.front],
            "light": {"phase": _r(ph),
                      "sky": [_r(c) for c in _lerp3(DAY_SKY, NIGHT_SKY, ph)],
                      "key": [_r(c) for c in _lerp3(DAY_KEY, NIGHT_KEY, ph)]},
        }

    def hash_hex(self) -> str:
        h = Hasher()
        h.s("parallax").u(self.tick)
        h.f(self.car_x).f(self.speed).f(self.wheel_angle)
        for lid, _, _ in LAYERS:
            h.i(lid).f(self.offsets[lid]).i(self.wraps[lid])
        for f in self.front:
            h.i(f["id"]).f(f["x"]).f(f["span"]).f(f["height"])
        h.f(self.light_phase()).u(self.rng.state)
        return h.hex()


#: The harness drives `Game`; the scene calls itself a Scene. One name, two spellings,
#: so probe.py and film.py can be copied between fixtures unchanged.
Game = Scene
