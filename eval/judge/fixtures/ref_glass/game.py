"""s2_glass - reference simulation. A glass of water empties, falls, breaks, un-breaks.

A GOOD control fixture: an honest implementation of the `s2_glass` scene contract as
`eval/suites/rendered/s2_glass__*.txt` states it. Pure simulation, no I/O, no wall-clock
time, no `random` module. Everything that varies comes from a seeded SplitMix64.

TWO STRUCTURAL CHOICES, both of which a criterion depends on:

* **The forward sequence is a pure function of one index**, `forward(u)`, and the rewind
  is that same function read backwards. A reversal built any other way is a second
  animation that happens to end where the first began, and `reversal.inverts` would then
  be measuring a coincidence. Here it measures an inverse.
* **`water.up` is computed independently of `glass.up`.** The wrong implementation - the
  one `water.level_under_tilt` exists to catch - parents the water to the cup, which is
  a one-line change and is the `water is parented to the cup` mutant.

WHY THE OTHER BEHAVIOURS ARE HERE, since a reference that does not exhibit a behaviour
cannot validate the criterion that measures it (FINDINGS #34):

* the drip volume and the remaining volume are the SAME water, so mass balance is a real
  constraint rather than two independent numbers that happen to move;
* the fragment count, their launch velocities and their resting places all come from the
  seed, so `seed.pair` can separate seeded fracture from a canned pre-fractured mesh;
* the backdrop is drawn behind the glass and re-drawn once the glass has left, so the
  image-side refraction check has a before and an after to compare.
"""

from __future__ import annotations

import math
import struct

TICK_HZ = 60
DT = 1.0 / TICK_HZ

#: The forward sequence, in forward-index units. The scene's own tick timeline is
#: longer, because the rewind replays this backwards.
DRAIN_END = 300      # forward indices [0, 300) - the long, slow part
TILT_END = 380       # [300, 380) - it leans
FALL_END = 410       # [380, 410) - it drops
FORWARD_END = 470    # [410, 470) - broken, pieces flying then at rest

#: Scene ticks. `REWIND_AT` is where the sequence turns round; `WHOLE_AT` is where it
#: arrives back at forward index 0.
REWIND_AT = 470
WHOLE_AT = 640
SCENE_TICKS = 660

TABLE_Y = 0.0        # the tabletop the glass stands on
FLOOR_Y = -70.0      # the surface it falls to and breaks on
GLASS_W = 26.0
GLASS_H = 46.0

FULL_VOLUME = 1.0
#: How much of the water has left by the time the glass starts to lean.
DRAINED_BY_TILT = 0.85
DRIP_UNIT = DRAINED_BY_TILT / 40.0

TILT_MAX = 1.05      # radians the glass leans before it goes over the edge
SLIDE_X = 18.0       # how far it slides while leaning

PIECES_MIN = 9
PIECES_MAX = 16

#: The patterned thing standing behind the glass, as a grid of seeded tones.
BACKDROP_COLS = 34
BACKDROP_ROWS = 12

_M64 = 0xFFFFFFFFFFFFFFFF
WORLD_UP = (0.0, 1.0, 0.0)

PHASES = ("draining", "tilting", "falling", "broken", "rewinding", "whole")


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

    def below(self, n: int) -> int:
        return self.next_u64() % n

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


def _clamp(v: float, lo: float, hi: float) -> float:
    return lo if v < lo else (hi if v > hi else v)


def _up_from_angle(a: float) -> tuple:
    """The direction the glass's own 'up' arrow points after leaning by `a` radians."""
    return (math.sin(a), math.cos(a), 0.0)


class Scene:
    """The whole of the glass scene. `step` takes the (ignored) input object."""

    def __init__(self, seed: int) -> None:
        self.seed = int(seed) & _M64
        self.reset()

    def reset(self) -> None:
        self.tick = 0
        rng = Rng(self.seed ^ 0x91A55)
        # THE FRACTURE IS DECIDED ONCE, FROM THE SEED, and the same seed therefore
        # produces the same fragments in the same places. `seed.pair` needs both halves.
        self.piece_count = PIECES_MIN + rng.below(PIECES_MAX - PIECES_MIN + 1)
        self.piece_plan = []
        for i in range(self.piece_count):
            self.piece_plan.append({
                "id": i + 1,
                "vx": rng.between(-52.0, 52.0),
                "vy": rng.between(24.0, 78.0),
                "vz": rng.between(-18.0, 18.0),
                "spin": rng.between(-7.0, 7.0),
                "size": rng.between(0.18, 0.44),
                "tumble": rng.between(0.6, 1.6),
                "phase0": rng.between(0.0, 6.28318),
            })
        # The backdrop's pattern, so the thing behind the glass is seeded too. It is a
        # DENSE grid rather than a few wide stripes, and that is not decoration: the
        # region seen through the glass can only be measured against the pattern it is
        # displacing, so a backdrop with nothing going on makes `glass.refracts`
        # unmeasurable on a scene that refracts perfectly well.
        self.backdrop = tuple(tuple(rng.between(0.25, 1.0) for _ in range(BACKDROP_COLS))
                              for _ in range(BACKDROP_ROWS))
        self.rng_state = rng.state
        self.fired = set()

    # -------------------------------------------------------- the sequence

    def forward_index(self, tick: int) -> int:
        """Which forward index this scene tick is showing.

        Before `REWIND_AT` it is the tick itself. Between `REWIND_AT` and `WHOLE_AT` it
        walks back down to 0 - a true inverse, not a second animation. After that it
        holds at 0, which is where the scene began.
        """
        if tick < REWIND_AT:
            return tick
        if tick >= WHOLE_AT:
            return 0
        span = WHOLE_AT - 1 - REWIND_AT
        u = (WHOLE_AT - 1 - tick) / float(span)
        return int(round(u * (FORWARD_END - 1)))

    def phase(self, tick: int) -> str:
        if tick >= WHOLE_AT:
            return "whole"
        if tick >= REWIND_AT:
            return "rewinding"
        u = self.forward_index(tick)
        if u < DRAIN_END:
            return "draining"
        if u < TILT_END:
            return "tilting"
        if u < FALL_END:
            return "falling"
        return "broken"

    def forward(self, u: int) -> dict:
        """Everything the scene is, at forward index `u`. Pure; no state is read."""
        u = int(_clamp(u, 0, FORWARD_END - 1))
        if u < DRAIN_END:
            drained = DRAINED_BY_TILT * (u / float(DRAIN_END))
            angle, gx, gy = 0.0, 0.0, TABLE_Y
            intact, pieces = True, []
        elif u < TILT_END:
            drained = DRAINED_BY_TILT
            t = (u - DRAIN_END) / float(TILT_END - DRAIN_END)
            angle = TILT_MAX * t
            gx, gy = SLIDE_X * (1.0 - math.cos(angle)), TABLE_Y
            intact, pieces = True, []
        elif u < FALL_END:
            t = (u - TILT_END) / float(FALL_END - TILT_END)
            drained = DRAINED_BY_TILT + (1.0 - DRAINED_BY_TILT) * t
            angle = TILT_MAX + 3.0 * t
            gx = SLIDE_X * (1.0 - math.cos(TILT_MAX)) + 26.0 * t
            gy = TABLE_Y + (FLOOR_Y - TABLE_Y) * t * t
            intact, pieces = True, []
        else:
            drained = 1.0
            t = (u - FALL_END) / float(FORWARD_END - FALL_END)
            angle = TILT_MAX + 3.0
            gx = SLIDE_X * (1.0 - math.cos(TILT_MAX)) + 26.0
            gy = FLOOR_Y
            intact = False
            pieces = [self._piece(p, t) for p in self.piece_plan]
        water = FULL_VOLUME - drained
        return {"u": u, "angle": angle, "gx": gx, "gy": gy,
                "intact": intact, "pieces": pieces,
                "water": water, "drained": drained}

    def _piece(self, plan: dict, t: float) -> dict:
        """One fragment, `t` of the way through the broken window (0..1).

        Ballistic until it reaches the floor, then still. `settled` is true from the
        moment it stops - THE SAME MOMENT its position stops changing, which is the
        whole content of the field. An earlier version held `settled` false for a few
        further ticks while the fragment was already stationary, so the reference itself
        reported a resting fragment as unsettled and `shatter.pieces_rest`, which reads
        exactly that field, was validated against a fixture that disagreed with it.
        """
        # Time in seconds since the impact, over the window's 60 ticks.
        s = t * ((FORWARD_END - FALL_END) * DT)
        g = 320.0
        # When this piece lands: solve vy*s - g*s^2/2 = 0 for s > 0, then it rests.
        land = 2.0 * plan["vy"] / g
        live = min(s, land)
        # A bigger fragment's centroid comes to rest higher above the floor, so the
        # settled pieces occupy a BAND rather than a single value - which is what a real
        # heap does, and what keeps `shatter.pieces_rest`'s band test from being
        # satisfied by a degenerate reference.
        rest_h = plan["size"] * 9.0
        y = FLOOR_Y + rest_h + plan["vy"] * live - 0.5 * g * live * live
        x = SLIDE_X * (1.0 - math.cos(TILT_MAX)) + 26.0 + plan["vx"] * live
        z = plan["vz"] * live
        settled = s >= land
        spin = plan["phase0"] + plan["spin"] * plan["tumble"] * live
        return {"id": plan["id"], "x": x, "y": y, "z": z,
                "up": _up_from_angle(spin), "settled": settled}

    # ------------------------------------------------------------------ sim

    def step(self, inputs: dict) -> list:
        """One tick. `inputs` is ignored - the scene has no player."""
        events: list = []
        prev_tick = self.tick
        self.tick += 1
        prev = self.forward(self.forward_index(prev_tick))
        cur = self.forward(self.forward_index(self.tick))

        if int(prev["drained"] / DRIP_UNIT) != int(cur["drained"] / DRIP_UNIT):
            events.append("drip")
        for name, at in (("tilt", DRAIN_END), ("fall", TILT_END),
                         ("impact", FALL_END), ("break", FALL_END)):
            if name not in self.fired and self.tick == at:
                self.fired.add(name)
                events.append(name)
        if "settle" not in self.fired and cur["pieces"] \
                and all(p["settled"] for p in cur["pieces"]):
            self.fired.add("settle")
            events.append("settle")
        if "rewind" not in self.fired and self.tick == REWIND_AT:
            self.fired.add("rewind")
            events.append("rewind")
        if "whole" not in self.fired and self.tick == WHOLE_AT:
            self.fired.add("whole")
            events.append("whole")
        return events

    # ---------------------------------------------------------------- views

    def screen_box(self, f: dict) -> dict:
        """Where the glass is in the captured frame, as fractions of frame size.

        film.py imports this rather than computing its own, so the telemetry and the
        image cannot disagree about where the glass was drawn.
        """
        from_x, from_y = f["gx"], f["gy"]
        if not f["intact"] and f["pieces"]:
            xs = [p["x"] for p in f["pieces"]]
            ys = [p["y"] for p in f["pieces"]]
            from_x = 0.5 * (min(xs) + max(xs))
            from_y = 0.5 * (min(ys) + max(ys))
            w = max(GLASS_W, max(xs) - min(xs) + 8.0)
            h = max(GLASS_H * 0.4, max(ys) - min(ys) + 8.0)
        else:
            w, h = GLASS_W, GLASS_H
            # `glass.y` is where the glass STANDS; the box is centred on its middle.
            from_y = from_y + GLASS_H * 0.5 * math.cos(f["angle"])
            from_x = from_x + GLASS_H * 0.5 * math.sin(f["angle"])
        sx, sy = world_to_screen(from_x, from_y)
        return {"x": _r(sx), "y": _r(sy),
                "w": _r(w * SCALE / VIEW_W), "h": _r(h * SCALE / VIEW_H)}

    def state(self) -> dict:
        f = self.forward(self.forward_index(self.tick))
        return {
            "phase": self.phase(self.tick),
            "glass": {"x": _r(f["gx"]), "y": _r(f["gy"]), "z": 0.0,
                      "intact": bool(f["intact"]),
                      "up": [_r(v) for v in _up_from_angle(f["angle"])],
                      "screen": self.screen_box(f)},
            # THE WATER'S SURFACE IS WORLD-HORIZONTAL, ALWAYS. It is computed from the
            # world, not from the glass, which is the whole point of the scene.
            "water": {"volume": _r(f["water"]), "up": [0.0, 1.0, 0.0],
                      "height": _r(GLASS_H * 0.82 * f["water"])},
            "drips": {"count": int(f["drained"] / DRIP_UNIT),
                      "volume": _r(f["drained"])},
            "pieces": [{"id": p["id"], "x": _r(p["x"]), "y": _r(p["y"]),
                        "z": _r(p["z"]), "up": [_r(v) for v in p["up"]],
                        "settled": bool(p["settled"])}
                       for p in f["pieces"]],
            "table": {"y": _r(TABLE_Y)},
        }

    def hash_hex(self) -> str:
        f = self.forward(self.forward_index(self.tick))
        h = Hasher()
        h.s("glass").u(self.tick).s(self.phase(self.tick))
        h.f(f["gx"]).f(f["gy"]).f(f["angle"]).f(f["water"]).f(f["drained"])
        h.i(1 if f["intact"] else 0).i(len(f["pieces"]))
        for p in f["pieces"]:
            h.i(p["id"]).f(p["x"]).f(p["y"]).f(p["z"])
            h.f(p["up"][0]).f(p["up"][1]).i(1 if p["settled"] else 0)
        h.u(self.rng_state)
        return h.hex()


# --------------------------------------------------------------------------- #
# The camera. Here rather than in film.py so `glass.screen` and the renderer cannot
# disagree about where the glass was drawn - a submission whose telemetry and pixels
# disagree is exactly what the image-side criteria are for, and a reference that had
# the same defect could not detect it.
# --------------------------------------------------------------------------- #

VIEW_W = 640
VIEW_H = 400
SCALE = 2.2
ORIGIN_X = 300.0
ORIGIN_Y = 210.0


def world_to_screen(x: float, y: float) -> tuple:
    """World coordinates to FRACTIONS of the frame, with (0, 0) the top-left corner."""
    return ((ORIGIN_X + x * SCALE) / VIEW_W, (ORIGIN_Y - y * SCALE) / VIEW_H)


Game = Scene
