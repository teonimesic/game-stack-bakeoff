"""DELIBERATELY FAKE CONTROL FIXTURE - do not treat this as a real game.

This is the ADVERSARIAL control for the evaluator. It is built to look like a
working Pong submission and to be wrong in every way that matters:

  * the ball position is a closed-form function of the tick number - nothing is
    integrated, nothing collides;
  * inputs are read and then thrown away;
  * the seed is ignored entirely, so every seed produces an identical run;
  * the score advances on a fixed timetable rather than from play;
  * events are emitted on a fixed timetable rather than from collisions.

If the evaluator scores this anywhere near the honest reference, the evaluator
is not measuring what it claims to measure.
"""

from __future__ import annotations

import math
import struct

TICK_HZ = 64
DT = 1.0 / TICK_HZ

ARENA_HALF_W = 400.0
ARENA_HALF_H = 240.0
PADDLE_X = 370.0
PADDLE_HALF_W = 8.0
PADDLE_HALF_H = 40.0
PADDLE_LIMIT = ARENA_HALF_H - PADDLE_HALF_H
BALL_RADIUS = 6.0
WIN_SCORE = 11

INPUT_FIELDS = ("left_up", "left_down", "right_up", "right_down")

# The "timetable" the fake run is choreographed against.
HIT_PERIOD = 37
BOUNCE_PERIOD = 53
LEFT_POINT_PERIOD = 640
RIGHT_POINT_PERIOD = 880

_M64 = 0xFFFFFFFFFFFFFFFF


class Hasher:
    """Looks like a state hash. It only ever sees the tick number."""

    def __init__(self) -> None:
        self.h = 0xCBF29CE484222325

    def _raw(self, data: bytes) -> None:
        h = self.h
        for b in data:
            h = ((h ^ b) * 0x100000001B3) & _M64
        self.h = h

    def u(self, n: int) -> "Hasher":
        self._raw(struct.pack("<Q", int(n) & _M64))
        return self

    def hex(self) -> str:
        return "0x%016x" % self.h


def _r(v: float) -> float:
    out = round(float(v), 6)
    return 0.0 if out == 0.0 else out


class Game:
    """A Pong-shaped animation. FAKE - see the module docstring."""

    def __init__(self, seed: int) -> None:
        self.seed = int(seed)  # stored so it looks used; never read again
        self.reset()

    def reset(self) -> None:
        self.tick = 0

    # The ball is a Lissajous figure of the tick, not an integrated body.
    def ball(self):
        t = self.tick
        x = (ARENA_HALF_W - 40.0) * math.sin(t * 0.026)
        y = (ARENA_HALF_H - 30.0) * math.sin(t * 0.0177 + 0.6)
        vx = (ARENA_HALF_W - 40.0) * 0.026 * math.cos(t * 0.026) * TICK_HZ
        vy = (ARENA_HALF_H - 30.0) * 0.0177 * math.cos(t * 0.0177 + 0.6) * TICK_HZ
        return x, y, vx, vy

    def paddles(self):
        t = self.tick
        return (PADDLE_LIMIT * math.sin(t * 0.021),
                PADDLE_LIMIT * math.sin(t * 0.021 + 1.1))

    def score(self):
        t = self.tick
        return (min(WIN_SCORE, t // LEFT_POINT_PERIOD),
                min(WIN_SCORE, t // RIGHT_POINT_PERIOD))

    def rally(self) -> int:
        return (self.tick % (HIT_PERIOD * 6)) // HIT_PERIOD

    def step(self, inputs: dict) -> list:
        # Inputs are read - and discarded.
        _ignored = [bool(inputs.get(field)) for field in INPUT_FIELDS]
        self.tick += 1
        t = self.tick
        events = []
        if t % HIT_PERIOD == 0:
            events.append("paddle_hit")
        if t % BOUNCE_PERIOD == 0:
            events.append("wall_bounce")
        if t % LEFT_POINT_PERIOD == 0 and t // LEFT_POINT_PERIOD <= WIN_SCORE:
            events.append("score_left")
        if t % RIGHT_POINT_PERIOD == 0 and t // RIGHT_POINT_PERIOD <= WIN_SCORE:
            events.append("score_right")
        return events

    def state(self) -> dict:
        x, y, vx, vy = self.ball()
        left, right = self.paddles()
        sl, sr = self.score()
        return {
            "ball": {"x": _r(x), "y": _r(y), "vx": _r(vx), "vy": _r(vy)},
            "paddles": [{"side": "left", "y": _r(left)},
                        {"side": "right", "y": _r(right)}],
            "score": {"left": sl, "right": sr},
            "rally": self.rally(),
        }

    def hash_hex(self) -> str:
        # Note what is missing: the seed, the inputs, and the world.
        return Hasher().u(self.tick).hex()
