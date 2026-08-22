"""3D Tetris - reference simulation.

A GOOD control fixture: a real, honest implementation of the g2_tetris3d spec.
Pure simulation, no I/O, no wall-clock time, no `random` module. Everything
random comes from a seeded SplitMix64.

Axes: x and z are the two horizontal axes, y counts upward from 0 at the floor.
"""

from __future__ import annotations

import struct

TICK_HZ = 64
WELL_W = 5
WELL_D = 5
WELL_H = 12
LAYER_CELLS = WELL_W * WELL_D

BASE_FALL_TICKS = 48
FALL_TICKS_PER_LEVEL = 4
MIN_FALL_TICKS = 6
SOFT_DROP_TICKS = 4
LEVEL_EVERY = 5

DAS_DELAY = 10  # ticks a direction must be held before it auto-repeats
DAS_RATE = 4    # ticks between auto-repeats

LINE_SCORE = (0, 100, 300, 700, 1500)

INPUT_FIELDS = (
    "move_neg_x", "move_pos_x", "move_neg_z", "move_pos_z",
    "rotate_x", "rotate_y", "rotate_z", "soft_drop", "hard_drop",
)

# Polycubes of four cells. The first cell of each list is the rotation pivot and
# is chosen near the middle of the shape so quarter turns rarely leave the well.
# "Y" (a tripod) and "W" (a screw) are genuinely three dimensional - they occupy
# two distinct values on all three axes and cannot be flattened into a plane.
PIECES = {
    "I": ((1, 0, 0), (0, 0, 0), (2, 0, 0), (3, 0, 0)),
    "O": ((0, 0, 0), (1, 0, 0), (0, 0, 1), (1, 0, 1)),
    "L": ((0, 1, 0), (0, 0, 0), (0, 2, 0), (1, 0, 0)),
    "T": ((1, 0, 0), (0, 0, 0), (2, 0, 0), (1, 0, 1)),
    "S": ((1, 0, 0), (0, 0, 0), (1, 0, 1), (2, 0, 1)),
    "Y": ((0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1)),
    "W": ((1, 0, 0), (0, 0, 0), (1, 1, 0), (1, 1, 1)),
}
KINDS = tuple(sorted(PIECES))

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

    def s(self, text: str) -> "Hasher":
        self._raw(text.encode("utf-8"))
        return self

    def hex(self) -> str:
        return "0x%016x" % self.h


def rot_x(c):
    x, y, z = c
    return (x, -z, y)


def rot_y(c):
    x, y, z = c
    return (z, y, -x)


def rot_z(c):
    x, y, z = c
    return (-y, x, z)


class Game:
    """The whole of 3D Tetris."""

    def __init__(self, seed: int) -> None:
        self.seed = int(seed) & _M64
        self.reset()

    # ---------------------------------------------------------------- setup

    def reset(self) -> None:
        self.rng = Rng(self.seed ^ 0x2545F4914F6CDD1D)
        self.tick = 0
        self.grid = {}          # (x, y, z) -> kind of the piece that locked here
        self.piece_kind = None
        self.piece_cells = []   # absolute [x, y, z], pivot first
        self.next_kind = KINDS[self.rng.below(len(KINDS))]
        self.score = 0
        self.layers_cleared = 0
        self.level = 1
        self.game_over = False
        self.fall_timer = 0
        self.held = {f: 0 for f in INPUT_FIELDS}
        self._spawn()  # the first piece is already falling at tick 0

    # ------------------------------------------------------------- geometry

    def _valid(self, cells) -> bool:
        for x, y, z in cells:
            if not (0 <= x < WELL_W and 0 <= z < WELL_D and 0 <= y < WELL_H):
                return False
            if (x, y, z) in self.grid:
                return False
        return True

    def _spawned_cells(self, kind: str):
        base = PIECES[kind]
        xs = [c[0] for c in base]
        ys = [c[1] for c in base]
        zs = [c[2] for c in base]
        ox = (WELL_W - (max(xs) - min(xs) + 1)) // 2 - min(xs)
        oz = (WELL_D - (max(zs) - min(zs) + 1)) // 2 - min(zs)
        oy = (WELL_H - 1) - max(ys)
        return [[c[0] + ox, c[1] + oy, c[2] + oz] for c in base]

    def _spawn(self) -> list:
        kind = self.next_kind
        self.next_kind = KINDS[self.rng.below(len(KINDS))]
        cells = self._spawned_cells(kind)
        self.fall_timer = 0
        if not self._valid(cells):
            self.piece_kind = None
            self.piece_cells = []
            self.game_over = True
            return ["game_over"]
        self.piece_kind = kind
        self.piece_cells = cells
        return ["spawn"]

    # ----------------------------------------------------------------- step

    def step(self, inputs: dict) -> list:
        """Advance exactly one tick. Returns the events raised this tick."""
        events: list = []
        self.tick += 1
        for f in INPUT_FIELDS:
            self.held[f] = self.held[f] + 1 if inputs.get(f) else 0
        if self.game_over:
            return events

        if self._edge("rotate_x") and self._rotate(rot_x):
            events.append("rotate")
        elif self._edge("rotate_y") and self._rotate(rot_y):
            events.append("rotate")
        elif self._edge("rotate_z") and self._rotate(rot_z):
            events.append("rotate")

        moved = False
        for field, dx, dz in (("move_neg_x", -1, 0), ("move_pos_x", 1, 0),
                              ("move_neg_z", 0, -1), ("move_pos_z", 0, 1)):
            if self._repeat(field) and self._translate(dx, 0, dz):
                moved = True
        if moved:
            events.append("move")

        if self._edge("hard_drop"):
            while self._translate(0, -1, 0):
                pass
            self._lock(events)
            return events

        interval = self.fall_interval()
        if inputs.get("soft_drop"):
            interval = min(interval, SOFT_DROP_TICKS)
        self.fall_timer += 1
        if self.fall_timer >= interval:
            self.fall_timer = 0
            if not self._translate(0, -1, 0):
                self._lock(events)
        return events

    def fall_interval(self) -> int:
        return max(MIN_FALL_TICKS, BASE_FALL_TICKS - FALL_TICKS_PER_LEVEL * (self.level - 1))

    def _edge(self, field: str) -> bool:
        return self.held[field] == 1

    def _repeat(self, field: str) -> bool:
        n = self.held[field]
        return n == 1 or (n > DAS_DELAY and (n - DAS_DELAY) % DAS_RATE == 0)

    def _translate(self, dx: int, dy: int, dz: int) -> bool:
        if self.piece_kind is None:
            return False
        cells = [[c[0] + dx, c[1] + dy, c[2] + dz] for c in self.piece_cells]
        if not self._valid(cells):
            return False
        self.piece_cells = cells
        return True

    def _rotate(self, matrix) -> bool:
        if self.piece_kind is None:
            return False
        px, py, pz = self.piece_cells[0]
        cells = []
        for x, y, z in self.piece_cells:
            rx, ry, rz = matrix((x - px, y - py, z - pz))
            cells.append([px + rx, py + ry, pz + rz])
        if not self._valid(cells) or cells == self.piece_cells:
            return False
        self.piece_cells = cells
        return True

    # ---------------------------------------------------------- locking etc

    def _lock(self, events: list) -> None:
        for x, y, z in self.piece_cells:
            self.grid[(x, y, z)] = self.piece_kind
        self.piece_kind = None
        self.piece_cells = []
        events.append("lock")
        cleared = self._clear_layers()
        for _ in range(cleared):
            events.append("layer_clear")
        if cleared:
            self.score += self._layer_score(cleared) * self.level
            self.layers_cleared += cleared
            self.level = 1 + self.layers_cleared // LEVEL_EVERY
        events.extend(self._spawn())

    @staticmethod
    def _layer_score(n: int) -> int:
        if n < len(LINE_SCORE):
            return LINE_SCORE[n]
        return LINE_SCORE[-1] + (n - len(LINE_SCORE) + 1) * 400

    def _clear_layers(self) -> int:
        counts = {}
        for (_x, y, _z) in self.grid:
            counts[y] = counts.get(y, 0) + 1
        full = sorted(y for y, n in counts.items() if n == LAYER_CELLS)
        if not full:
            return 0
        full_set = set(full)
        moved = {}
        for (x, y, z), kind in self.grid.items():
            if y in full_set:
                continue
            drop = sum(1 for fy in full if fy < y)
            moved[(x, y - drop, z)] = kind
        self.grid = moved
        return len(full)

    def heights(self) -> list:
        cols = [[0] * WELL_D for _ in range(WELL_W)]
        for (x, y, z) in self.grid:
            if y + 1 > cols[x][z]:
                cols[x][z] = y + 1
        return cols

    # ---------------------------------------------------------------- views

    def state(self) -> dict:
        piece = None
        if self.piece_kind is not None:
            piece = {"kind": self.piece_kind,
                     "cells": [[int(c[0]), int(c[1]), int(c[2])] for c in self.piece_cells]}
        return {
            "well": {"w": WELL_W, "d": WELL_D, "h": WELL_H},
            "piece": piece,
            "next": self.next_kind,
            "settled": len(self.grid),
            "heights": self.heights(),
            "score": self.score,
            "layers_cleared": self.layers_cleared,
            "level": self.level,
            "game_over": self.game_over,
        }

    def hash_hex(self) -> str:
        h = Hasher()
        h.s("tetris3d").u(self.tick)
        h.s(self.piece_kind or "-")
        for c in self.piece_cells:
            h.i(c[0]).i(c[1]).i(c[2])
        h.s(self.next_kind)
        for key in sorted(self.grid):
            h.i(key[0]).i(key[1]).i(key[2]).s(self.grid[key])
        h.i(self.score).i(self.layers_cleared).i(self.level)
        h.i(self.fall_timer).i(1 if self.game_over else 0)
        h.u(self.rng.state)
        return h.hex()
