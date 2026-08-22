"""DELIBERATELY BROKEN CONTROL FIXTURE - do not treat this as a real game.

This is the BROKEN control for the evaluator. Everything here is *technically*
fine and completely useless:

  * `just check`, `just lint`, `just test` and `just verify` all exit 0;
  * `just film` emits twelve valid 640x400 PNGs that are a flat background
    colour with nothing drawn on them and no change between frames;
  * `just probe` exists as a recipe and fails - the protocol is not implemented.

There is no simulation here at all. If the evaluator gives this anything but
the floor, the evaluator is rewarding the presence of a build, not a game.
"""

from __future__ import annotations

BACKGROUND = (18, 18, 22)
WIDTH = 640
HEIGHT = 400
FRAME_COUNT = 12


class Game:
    """A placeholder. It has a tick counter and no world."""

    def __init__(self, seed: int = 0) -> None:
        self.seed = int(seed)
        self.tick = 0

    def reset(self) -> None:
        self.tick = 0

    def step(self, inputs: dict = None) -> list:
        self.tick += 1
        return []

    def state(self) -> dict:
        return {}

    def hash_hex(self) -> str:
        return "0x0000000000000000"
