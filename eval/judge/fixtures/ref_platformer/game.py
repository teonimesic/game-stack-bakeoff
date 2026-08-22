"""2D sprite platformer with attacks - reference simulation.

A GOOD control fixture: an honest implementation of the g4_platformer spec in
`eval/G4-PLATFORMER.md`. Pure simulation, no I/O, no wall-clock time, no `random`
module, no physics engine - axis-aligned boxes on a fixed tick. Everything random comes
from a seeded SplitMix64.

The reference is written AFTER the prompt is frozen and deliberately exhibits the things
the task rewards and the older references could not (FINDINGS #34):

* an opening title card, so nothing is measurable at tick 0 and every criterion has to
  tolerate a delay before it can act;
* a clear end state in both directions - death and stage clear - and play stops at both;
* active frames: the weapon damages during PART of the swing, so a criterion asserting
  on `attack.active` has a window to find and a recovery to find the end of;
* an animation state machine with a frame index that actually advances.
"""

from __future__ import annotations

import struct

TICK_HZ = 64
DT = 1.0 / TICK_HZ

#: Ticks of title card before the player is handed control. Nothing moves during it.
#: The old references served immediately, which is exactly why `ball.moves` acquired a
#: false negative the moment a submission drew a title card.
OPENING_TICKS = 96

GRAVITY = -1500.0
WALK_SPEED = 180.0
JUMP_SPEED = 520.0
MAX_FALL = -900.0

PLAYER_HW = 12.0
PLAYER_HH = 20.0
PLAYER_START_HP = 4
INVULN_TICKS = 48
KNOCKBACK_X = 240.0
KNOCKBACK_Y = 240.0

# The swing: startup, then the window that damages, then recovery. `attack.active` is
# true ONLY during the middle phase, and a new attack is refused until the whole thing
# finishes.
ATTACK_STARTUP = 4
ATTACK_ACTIVE = 6
ATTACK_RECOVERY = 12
ATTACK_TOTAL = ATTACK_STARTUP + ATTACK_ACTIVE + ATTACK_RECOVERY
HITBOX_W = 34.0
HITBOX_H = 28.0
HITBOX_REACH = PLAYER_HW + HITBOX_W / 2.0

ENEMY_HW = 12.0
ENEMY_HH = 16.0
ENEMY_SPEED = 55.0
ENEMY_HP = 2
ENEMY_PATROL = 90.0
ENEMY_COUNT = 4
SCORE_PER_KILL = 100

ANIM_FRAME_TICKS = 8
ANIM_FRAMES = 4

_M64 = 0xFFFFFFFFFFFFFFFF

# The stage. `x`/`y` are the CENTRE of each box and `w`/`h` its full size, so a
# platform's top surface is `y + h / 2`. The player starts on a raised ledge whose
# right edge is a real ledge: walking off it is how `player.falls` and
# `platform.lands` establish their condition instead of waiting for one.
PLATFORMS = (
    {"id": 1, "x": 1200.0, "y": -8.0, "w": 2400.0, "h": 16.0},    # ground, top y=0
    {"id": 2, "x": 60.0, "y": 72.0, "w": 120.0, "h": 16.0},       # start ledge, top y=80
    {"id": 3, "x": 620.0, "y": 110.0, "w": 180.0, "h": 16.0},
    {"id": 4, "x": 1080.0, "y": 170.0, "w": 180.0, "h": 16.0},
    {"id": 5, "x": 1560.0, "y": 110.0, "w": 180.0, "h": 16.0},
)
LEVEL_W = 2400.0
LEVEL_H = 480.0
GOAL_X = 2300.0

ANIM_IDLE = "idle"
ANIM_WALK = "walk"
ANIM_JUMP = "jump"
ANIM_FALL = "fall"
ANIM_ATTACK = "attack"

INPUT_FIELDS = ("move_left", "move_right", "jump", "attack")


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


def _clamp(v: float, lo: float, hi: float) -> float:
    return lo if v < lo else (hi if v > hi else v)


def _r(v: float) -> float:
    out = round(float(v), 6)
    return 0.0 if out == 0.0 else out


def _overlap(ax: float, ay: float, ahw: float, ahh: float,
             bx: float, by: float, bhw: float, bhh: float) -> bool:
    return abs(ax - bx) <= ahw + bhw and abs(ay - by) <= ahh + bhh


class Game:
    """The whole of the platformer."""

    def __init__(self, seed: int) -> None:
        self.seed = int(seed) & _M64
        self.reset()

    # ---------------------------------------------------------------- setup

    def reset(self) -> None:
        self.rng = Rng(self.seed ^ 0x2545F4914F6CDD1D)
        self.tick = 0
        self.px = 40.0
        self.py = 80.0 + PLAYER_HH
        self.vx = 0.0
        self.vy = 0.0
        self.hp = PLAYER_START_HP
        self.alive = True
        self.grounded = True
        self.facing = 1
        self.invuln = 0
        self.anim = ANIM_IDLE
        self.anim_frame = 0
        self.anim_ticks = 0
        self.attack_t = 0          # 0 = no swing; counts UP through ATTACK_TOTAL
        self.score = 0
        self.game_over = False
        self.victory = False
        self.next_id = 1
        self.enemies = []
        for _ in range(ENEMY_COUNT):
            home = self.rng.between(320.0, 2050.0)
            self.enemies.append({
                "id": self._take_id(),
                "x": home,
                "y": ENEMY_HH,
                "home": home,
                "hp": ENEMY_HP,
                "facing": 1 if self.rng.below(2) else -1,
            })
        self.enemies.sort(key=lambda e: e["id"])

    def _take_id(self) -> int:
        out = self.next_id
        self.next_id += 1
        return out

    # ----------------------------------------------------------------- step

    def step(self, inputs: dict) -> list:
        """Advance exactly one tick. Returns the events raised this tick."""
        events: list = []
        self.tick += 1
        if self.game_over or self.victory:
            return events
        if self.tick <= OPENING_TICKS:
            # The title card. Control is not handed over yet, and nothing moves.
            self._set_anim(ANIM_IDLE)
            return events

        self._attack(inputs, events)
        self._walk(inputs)
        self._jump(inputs, events)
        self._integrate(events)
        self._enemies(events)
        self._hitbox_damage(events)
        self._contact_damage(events)
        self._goal(events)
        self._animate(inputs)
        if self.invuln > 0:
            self.invuln -= 1
        return events

    # -- the swing ------------------------------------------------------- #

    def _attack(self, inputs: dict, events: list) -> None:
        if self.attack_t > 0:
            self.attack_t += 1
            if self.attack_t > ATTACK_TOTAL:
                self.attack_t = 0
            return
        if inputs.get("attack"):
            self.attack_t = 1
            events.append("attack")

    @property
    def attack_active(self) -> bool:
        return ATTACK_STARTUP < self.attack_t <= ATTACK_STARTUP + ATTACK_ACTIVE

    def hitbox(self) -> tuple[float, float, float, float]:
        """(x, y, w, h) of the damaging rectangle, zero-sized when inactive."""
        if not self.attack_active:
            return 0.0, 0.0, 0.0, 0.0
        return (self.px + self.facing * HITBOX_REACH, self.py, HITBOX_W, HITBOX_H)

    # -- movement --------------------------------------------------------- #

    def _walk(self, inputs: dict) -> None:
        left = bool(inputs.get("move_left"))
        right = bool(inputs.get("move_right"))
        d = (1.0 if right else 0.0) - (1.0 if left else 0.0)
        # The recovery of a swing roots the character. That is a game-feel decision and
        # it is why the bot flips facing by WALKING rather than by attacking twice.
        if self.attack_t > 0:
            d = 0.0
        self.vx = d * WALK_SPEED
        if d > 0:
            self.facing = 1
        elif d < 0:
            self.facing = -1

    def _jump(self, inputs: dict, events: list) -> None:
        if inputs.get("jump") and self.grounded:
            self.vy = JUMP_SPEED
            self.grounded = False
            events.append("jump")

    def _integrate(self, events: list) -> None:
        self.px = _clamp(self.px + self.vx * DT, PLAYER_HW, LEVEL_W - PLAYER_HW)

        self.vy = max(MAX_FALL, self.vy + GRAVITY * DT)
        ny = self.py + self.vy * DT
        was_grounded = self.grounded
        self.grounded = False
        for p in PLATFORMS:
            top = p["y"] + p["h"] / 2.0
            bottom = p["y"] - p["h"] / 2.0
            hw = p["w"] / 2.0
            if abs(self.px - p["x"]) > hw + PLAYER_HW:
                continue
            if self.vy <= 0.0 and self.py - PLAYER_HH >= top - 1e-6 \
                    and ny - PLAYER_HH <= top:
                ny = top + PLAYER_HH
                self.vy = 0.0
                self.grounded = True
                if not was_grounded:
                    events.append("land")
            elif self.vy > 0.0 and self.py + PLAYER_HH <= bottom + 1e-6 \
                    and ny + PLAYER_HH >= bottom:
                ny = bottom - PLAYER_HH
                self.vy = 0.0
        self.py = ny
        if self.py < -200.0:      # fell out of the world: back to the start ledge
            self.px, self.py = 40.0, 80.0 + PLAYER_HH
            self.vy = 0.0

    # -- enemies ---------------------------------------------------------- #

    def _enemies(self, events: list) -> None:
        for e in self.enemies:
            e["x"] += e["facing"] * ENEMY_SPEED * DT
            if e["x"] > e["home"] + ENEMY_PATROL:
                e["x"] = e["home"] + ENEMY_PATROL
                e["facing"] = -1
            elif e["x"] < e["home"] - ENEMY_PATROL:
                e["x"] = e["home"] - ENEMY_PATROL
                e["facing"] = 1

    def _hitbox_damage(self, events: list) -> None:
        if not self.attack_active:
            return
        hx, hy, hw, hh = self.hitbox()
        for e in list(self.enemies):
            if _overlap(hx, hy, hw / 2.0, hh / 2.0,
                        e["x"], e["y"], ENEMY_HW, ENEMY_HH):
                e["hp"] -= 1
                events.append("enemy_hit")
                if e["hp"] <= 0:
                    self.enemies.remove(e)
                    self.score += SCORE_PER_KILL
                    events.append("enemy_dead")

    def _contact_damage(self, events: list) -> None:
        if self.invuln > 0:
            return
        for e in self.enemies:
            if _overlap(self.px, self.py, PLAYER_HW, PLAYER_HH,
                        e["x"], e["y"], ENEMY_HW, ENEMY_HH):
                self.hp -= 1
                self.invuln = INVULN_TICKS
                away = 1.0 if self.px >= e["x"] else -1.0
                self.vx = away * KNOCKBACK_X
                self.vy = KNOCKBACK_Y
                self.grounded = False
                self.px = _clamp(self.px + away * 2.0, PLAYER_HW, LEVEL_W - PLAYER_HW)
                events.append("player_hit")
                if self.hp <= 0:
                    self.hp = 0
                    self.alive = False
                    self.game_over = True
                    events.append("game_over")
                return

    def _goal(self, events: list) -> None:
        if self.px >= GOAL_X and not self.game_over:
            self.victory = True
            events.append("stage_clear")

    # -- the animation state machine -------------------------------------- #

    def _state_for(self, inputs: dict) -> str:
        if self.attack_t > 0:
            return ANIM_ATTACK
        if not self.grounded:
            return ANIM_JUMP if self.vy > 0.0 else ANIM_FALL
        if abs(self.vx) > 1e-6:
            return ANIM_WALK
        return ANIM_IDLE

    def _set_anim(self, name: str) -> None:
        if name != self.anim:
            self.anim = name
            self.anim_frame = 0
            self.anim_ticks = 0

    def _animate(self, inputs: dict) -> None:
        self._set_anim(self._state_for(inputs))
        self.anim_ticks += 1
        if self.anim_ticks >= ANIM_FRAME_TICKS:
            self.anim_ticks = 0
            self.anim_frame = (self.anim_frame + 1) % ANIM_FRAMES

    # ---------------------------------------------------------------- views

    def state(self) -> dict:
        hx, hy, hw, hh = self.hitbox()
        return {
            "level": {"w": LEVEL_W, "h": LEVEL_H, "goal_x": GOAL_X},
            "player": {"x": _r(self.px), "y": _r(self.py), "vx": _r(self.vx),
                       "vy": _r(self.vy), "hp": self.hp, "grounded": self.grounded,
                       "facing": self.facing, "invuln": self.invuln,
                       "anim": self.anim, "anim_frame": self.anim_frame,
                       "alive": self.alive},
            "attack": {"active": self.attack_active, "frame": self.attack_t,
                       "hitbox": {"x": _r(hx), "y": _r(hy), "w": _r(hw), "h": _r(hh)}},
            "platforms": [{"id": p["id"], "x": p["x"], "y": p["y"],
                           "w": p["w"], "h": p["h"]} for p in PLATFORMS],
            "enemies": [{"id": e["id"], "x": _r(e["x"]), "y": _r(e["y"]),
                         "hp": e["hp"], "facing": e["facing"]}
                        for e in sorted(self.enemies, key=lambda e: e["id"])],
            "score": self.score,
            "game_over": self.game_over,
            "victory": self.victory,
        }

    def hash_hex(self) -> str:
        h = Hasher()
        h.s("platformer").u(self.tick)
        h.f(self.px).f(self.py).f(self.vx).f(self.vy)
        h.i(self.hp).i(1 if self.alive else 0).i(1 if self.grounded else 0)
        h.i(self.facing).i(self.invuln).s(self.anim).i(self.anim_frame)
        h.i(self.anim_ticks).i(self.attack_t)
        for e in sorted(self.enemies, key=lambda e: e["id"]):
            h.i(e["id"]).f(e["x"]).f(e["y"]).f(e["home"]).i(e["hp"]).i(e["facing"])
        h.i(self.score).i(1 if self.game_over else 0).i(1 if self.victory else 0)
        h.i(self.next_id).u(self.rng.state)
        return h.hex()
