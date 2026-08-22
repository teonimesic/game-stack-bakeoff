"""Pong - reference simulation.

A GOOD control fixture: a real, honest implementation of the g1_pong spec.
Pure simulation, no I/O, no wall-clock time, no `random` module. Everything
random comes from a seeded SplitMix64.
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
PADDLE_SPEED = 320.0

BALL_RADIUS = 6.0
BALL_SPEED_START = 780.0
BALL_SPEED_STEP = 18.0
BALL_SPEED_MAX = 1400.0
MAX_BOUNCE_ANGLE = 0.9  # radians, at the very edge of the paddle
SERVE_SPREAD = 0.45

WIN_SCORE = 11

INPUT_FIELDS = ("left_up", "left_down", "right_up", "right_down")

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
            v = 0.0  # collapse -0.0
        self._raw(struct.pack("<d", v))
        return self

    def s(self, text: str) -> "Hasher":
        self._raw(text.encode("utf-8"))
        return self

    def hex(self) -> str:
        return "0x%016x" % self.h


def _clamp(v: float, lo: float, hi: float) -> float:
    return lo if v < lo else (hi if v > hi else v)


def _r(v: float) -> float:
    out = round(float(v), 6)
    return 0.0 if out == 0.0 else out


class Game:
    """The whole of Pong."""

    def __init__(self, seed: int) -> None:
        self.seed = int(seed) & _M64
        self.reset()

    # ---------------------------------------------------------------- setup

    def reset(self) -> None:
        self.rng = Rng(self.seed ^ 0x5851F42D4C957F2D)
        self.tick = 0
        self.left_y = 0.0
        self.right_y = 0.0
        self.score_left = 0
        self.score_right = 0
        self.rally = 0
        self.over = False
        self.speed = BALL_SPEED_START
        self.ball_x = 0.0
        self.ball_y = 0.0
        self.ball_vx = 0.0
        self.ball_vy = 0.0
        self._serve(1 if self.rng.below(2) == 1 else -1)

    def _serve(self, direction: int) -> None:
        angle = self.rng.between(-SERVE_SPREAD, SERVE_SPREAD)
        self.speed = BALL_SPEED_START
        self.ball_x = 0.0
        self.ball_y = 0.0
        self.ball_vx = direction * self.speed * math.cos(angle)
        self.ball_vy = self.speed * math.sin(angle)

    # ----------------------------------------------------------------- step

    def step(self, inputs: dict) -> list:
        """Advance exactly one tick. Returns the events raised this tick."""
        events: list = []
        self.tick += 1
        if self.over:
            # First to WIN_SCORE has won: no more play until reset().
            return events

        self._move_paddles(inputs)
        nx = self.ball_x + self.ball_vx * DT
        ny = self.ball_y + self.ball_vy * DT

        top = ARENA_HALF_H - BALL_RADIUS
        if ny > top:
            ny = 2.0 * top - ny
            self.ball_vy = -self.ball_vy
            events.append("wall_bounce")
        elif ny < -top:
            ny = -2.0 * top - ny
            self.ball_vy = -self.ball_vy
            events.append("wall_bounce")

        if self.ball_vx < 0.0 and self._overlaps_paddle(nx, ny, -PADDLE_X, self.left_y):
            nx, ny = self._deflect(1, ny, self.left_y)
            events.append("paddle_hit")
        elif self.ball_vx > 0.0 and self._overlaps_paddle(nx, ny, PADDLE_X, self.right_y):
            nx, ny = self._deflect(-1, ny, self.right_y)
            events.append("paddle_hit")

        self.ball_x = nx
        self.ball_y = ny

        if self.ball_x < -ARENA_HALF_W:
            self.score_right += 1
            self.rally = 0
            events.append("score_right")
            self._after_point(-1, events)
        elif self.ball_x > ARENA_HALF_W:
            self.score_left += 1
            self.rally = 0
            events.append("score_left")
            self._after_point(1, events)
        return events

    def _move_paddles(self, inputs: dict) -> None:
        ld = (1.0 if inputs.get("left_up") else 0.0) - (1.0 if inputs.get("left_down") else 0.0)
        rd = (1.0 if inputs.get("right_up") else 0.0) - (1.0 if inputs.get("right_down") else 0.0)
        self.left_y = _clamp(self.left_y + ld * PADDLE_SPEED * DT, -PADDLE_LIMIT, PADDLE_LIMIT)
        self.right_y = _clamp(self.right_y + rd * PADDLE_SPEED * DT, -PADDLE_LIMIT, PADDLE_LIMIT)

    @staticmethod
    def _overlaps_paddle(bx: float, by: float, px: float, py: float) -> bool:
        cx = _clamp(bx, px - PADDLE_HALF_W, px + PADDLE_HALF_W)
        cy = _clamp(by, py - PADDLE_HALF_H, py + PADDLE_HALF_H)
        dx = bx - cx
        dy = by - cy
        return dx * dx + dy * dy <= BALL_RADIUS * BALL_RADIUS

    def _deflect(self, sign: int, by: float, paddle_y: float):
        offset = _clamp((by - paddle_y) / PADDLE_HALF_H, -1.0, 1.0)
        angle = offset * MAX_BOUNCE_ANGLE
        self.speed = min(BALL_SPEED_MAX, self.speed + BALL_SPEED_STEP)
        self.ball_vx = sign * self.speed * math.cos(angle)
        self.ball_vy = self.speed * math.sin(angle)
        self.rally += 1
        edge = PADDLE_X - PADDLE_HALF_W - BALL_RADIUS
        nx = -edge if sign > 0 else edge
        return nx, by

    def _after_point(self, serve_dir: int, events: list) -> None:
        if self.score_left >= WIN_SCORE or self.score_right >= WIN_SCORE:
            if not self.over:
                events.append("game_over")
            self.over = True
            self.ball_x = 0.0
            self.ball_y = 0.0
            self.ball_vx = 0.0
            self.ball_vy = 0.0
            self.speed = BALL_SPEED_START
        else:
            self._serve(serve_dir)

    # ---------------------------------------------------------------- views

    def state(self) -> dict:
        return {
            "ball": {
                "x": _r(self.ball_x),
                "y": _r(self.ball_y),
                "vx": _r(self.ball_vx),
                "vy": _r(self.ball_vy),
            },
            "paddles": [
                {"side": "left", "y": _r(self.left_y)},
                {"side": "right", "y": _r(self.right_y)},
            ],
            "score": {"left": self.score_left, "right": self.score_right},
            "rally": self.rally,
            "game_over": self.over,
        }

    def hash_hex(self) -> str:
        h = Hasher()
        h.s("pong").u(self.tick)
        h.f(self.ball_x).f(self.ball_y).f(self.ball_vx).f(self.ball_vy)
        h.f(self.left_y).f(self.right_y).f(self.speed)
        h.i(self.score_left).i(self.score_right).i(self.rally)
        h.i(1 if self.over else 0)
        h.u(self.rng.state)
        return h.hex()
