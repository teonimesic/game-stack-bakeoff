"""3D twin-stick arena shooter - reference simulation.

A GOOD control fixture: a real, honest implementation of the g3_arena spec as it
stands after the 2026-08-15 rewrite (3D volume, analog input, three enemy kinds,
materialisation, score multiplier). Pure simulation, no I/O, no wall-clock time, no
`random` module, no physics engine - spheres and boxes on a fixed tick. Everything
random comes from a seeded SplitMix64.

WHY EACH OF THE NEW MECHANICS IS HERE, since a reference that does not exhibit a
behaviour cannot validate the criterion that measures it (FINDINGS #34):

* analog movement, honoured at partial magnitude, so `move.analog` can separate a
  proportional response from an eight-way one;
* three kinds whose MOVEMENT RULES differ, not merely their speed, so collapsing them
  to one kind is a mutant that changes behaviour rather than a label;
* a materialisation window in which an enemy can neither be hit nor hurt the player,
  so `enemy.materialises` has something to establish;
* a multiplier that rises on a kill streak and collapses on damage, so both halves of
  it can be driven.
"""

from __future__ import annotations

import math
import struct

TICK_HZ = 64
DT = 1.0 / TICK_HZ

ARENA_HALF_X = 400.0
ARENA_HALF_Y = 250.0
ARENA_HALF_Z = 400.0

PLAYER_RADIUS = 12.0
PLAYER_SPEED = 220.0
PLAYER_START_HP = 3
INVULN_TICKS = 64  # one second of grace after being hit

FIRE_INTERVAL = 10  # ticks between shots
BULLET_SPEED = 520.0
BULLET_RADIUS = 4.0
MUZZLE_OFFSET = PLAYER_RADIUS + 6.0

ENEMY_RADIUS = 14.0
ENEMY_BASE_SPEED = 60.0
ENEMY_SPEED_PER_WAVE = 8.0
ENEMY_MAX_SPEED = 200.0
WAVE_BASE_COUNT = 3
WAVE_GAP_TICKS = 48
SCORE_PER_KILL = 100

#: Ticks an enemy spends materialising. It is neither hittable nor dangerous during
#: this window, and `spawning` is true throughout it.
SPAWN_TICKS = 32

#: Kills without taking damage needed to raise the multiplier by one, and its ceiling.
KILLS_PER_MULT = 3
MULT_MAX = 8

# Kind-specific behaviour. The differences are in the MOVEMENT RULE, not just a speed
# scalar - "at least three kinds ... they must not merely differ in speed".
KIND_DRIFTER = "drifter"
KIND_WEAVER = "weaver"
KIND_CHARGER = "charger"
KINDS = (KIND_DRIFTER, KIND_WEAVER, KIND_CHARGER)

#: The first wave each kind can appear in. **This gating is the point, not flavour.**
#:
#: Until 2026-08-16 every wave here contained all three kinds, so `enemy.kinds` was
#: satisfied on the first tick of wave 1 and could not fail for the reason it actually
#: failed on six real submissions: all six unlock kinds over successive waves
#: (`wave >= 2`, `wave >= 3`, `wave >= 4` in the ts, unity and godot submissions), the
#: bot stood still, died in wave 1, and read one kind on games that ship four.
#:
#: A mutant cannot find that. It removes the mechanism the criterion names; it cannot
#: manufacture an input the criterion mishandles. Only a reference that exhibits the
#: behaviour the task rewards can (FINDINGS #34, #46).
KIND_FIRST_WAVE = {KIND_DRIFTER: 1, KIND_WEAVER: 2, KIND_CHARGER: 3}

WEAVE_AMPLITUDE = 0.55      # share of speed spent on the lateral swing
WEAVE_PERIOD = 48           # ticks per full weave cycle
CHARGE_WINDUP = 40          # ticks the charger holds still
CHARGE_DASH = 26            # ticks it dashes
CHARGE_SPEED_MULT = 2.6

INPUT_FIELDS = ("move_x", "move_y", "move_z", "aim_x", "aim_y", "aim_z", "fire")

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


def _axis(inputs: dict, name: str) -> float:
    """One analog axis, clamped to -1..1. Absent or unparseable reads as 0."""
    try:
        v = float(inputs.get(name) or 0.0)
    except (TypeError, ValueError):
        return 0.0
    if not math.isfinite(v):
        return 0.0
    return _clamp(v, -1.0, 1.0)


def _vector(inputs: dict, prefix: str) -> tuple[float, float, float]:
    """The analog vector, with magnitude preserved below 1 and clamped at 1.

    THIS IS THE POINT OF THE ANALOG CONTRACT: a half-pushed stick must move at half
    speed. Normalising unconditionally - the obvious implementation - destroys exactly
    that, and is one of the mutants.
    """
    x = _axis(inputs, f"{prefix}_x")
    y = _axis(inputs, f"{prefix}_y")
    z = _axis(inputs, f"{prefix}_z")
    mag = math.sqrt(x * x + y * y + z * z)
    if mag > 1.0:
        return x / mag, y / mag, z / mag
    return x, y, z


class Game:
    """The whole of the 3D arena shooter."""

    def __init__(self, seed: int) -> None:
        self.seed = int(seed) & _M64
        self.reset()

    # ---------------------------------------------------------------- setup

    def reset(self) -> None:
        self.rng = Rng(self.seed ^ 0x14057B7EF767814F)
        self.tick = 0
        self.px = 0.0
        self.py = 0.0
        self.pz = 0.0
        self.hp = PLAYER_START_HP
        self.alive = True
        self.aim_x = 1.0
        self.aim_y = 0.0
        self.aim_z = 0.0
        self.enemies = []
        self.bullets = []
        self.next_id = 1
        self.wave = 1
        self.enemy_speed = self.wave_speed(1)
        self.score = 0
        self.kills = 0
        self.multiplier = 1
        self.streak = 0
        self.game_over = False
        self.fire_cooldown = 0
        self.invuln = 0
        self.pending = 1  # ticks until the next wave spawns; 0 = wave in progress

    @staticmethod
    def wave_count(wave: int) -> int:
        return WAVE_BASE_COUNT + wave

    @staticmethod
    def wave_speed(wave: int) -> float:
        return min(ENEMY_MAX_SPEED, ENEMY_BASE_SPEED + ENEMY_SPEED_PER_WAVE * wave)

    @staticmethod
    def wave_hp(wave: int) -> int:
        return 1 + (wave - 1) // 3

    def _take_id(self) -> int:
        out = self.next_id
        self.next_id += 1
        return out

    def _spawn_wave(self, events: list) -> None:
        self.enemy_speed = self.wave_speed(self.wave)
        hp = self.wave_hp(self.wave)
        for i in range(self.wave_count(self.wave)):
            # A face of the box, then a point on it. Three axes, so six faces.
            face = self.rng.below(6)
            x = self.rng.between(-ARENA_HALF_X, ARENA_HALF_X)
            y = self.rng.between(-ARENA_HALF_Y, ARENA_HALF_Y)
            z = self.rng.between(-ARENA_HALF_Z, ARENA_HALF_Z)
            if face == 0:
                x = -ARENA_HALF_X + ENEMY_RADIUS
            elif face == 1:
                x = ARENA_HALF_X - ENEMY_RADIUS
            elif face == 2:
                y = -ARENA_HALF_Y + ENEMY_RADIUS
            elif face == 3:
                y = ARENA_HALF_Y - ENEMY_RADIUS
            elif face == 4:
                z = -ARENA_HALF_Z + ENEMY_RADIUS
            else:
                z = ARENA_HALF_Z - ENEMY_RADIUS
            # Kinds unlock one wave at a time, so meeting all three requires PLAYING —
            # clearing wave 1 and wave 2 — rather than looking at wave 1. The newest
            # unlocked kind takes the first slot, so the wave that unlocks a kind
            # actually shows it.
            available = [k for k in KINDS if KIND_FIRST_WAVE.get(k, 1) <= self.wave]
            if not available:
                available = [KINDS[0]]
            kind = available[-1] if i == 0 else available[self.rng.below(len(available))]
            self.enemies.append({
                "id": self._take_id(),
                "kind": kind,
                "x": _clamp(x, -ARENA_HALF_X + ENEMY_RADIUS, ARENA_HALF_X - ENEMY_RADIUS),
                "y": _clamp(y, -ARENA_HALF_Y + ENEMY_RADIUS, ARENA_HALF_Y - ENEMY_RADIUS),
                "z": _clamp(z, -ARENA_HALF_Z + ENEMY_RADIUS, ARENA_HALF_Z - ENEMY_RADIUS),
                "hp": hp,
                "spawn": SPAWN_TICKS,
                "phase": self.rng.below(WEAVE_PERIOD),
            })
            events.append("enemy_spawn")

    # ----------------------------------------------------------------- step

    def step(self, inputs: dict) -> list:
        """Advance exactly one tick. Returns the events raised this tick."""
        events: list = []
        self.tick += 1
        if self.game_over:
            return events

        grazed = self._move_player(inputs)
        self._update_aim(inputs)
        self._fire(inputs, events)
        grazed = self._move_bullets() or grazed
        self._materialise()
        self._move_enemies()
        self._bullets_hit_enemies(events)
        self._enemies_hit_player(events)
        self._advance_waves(events)
        if grazed:
            events.append("wall_graze")
        if self.invuln > 0:
            self.invuln -= 1
        return events

    def _move_player(self, inputs: dict) -> bool:
        """Analog movement on three axes. Returns whether the wall was reached."""
        dx, dy, dz = _vector(inputs, "move")
        nx = self.px + dx * PLAYER_SPEED * DT
        ny = self.py + dy * PLAYER_SPEED * DT
        nz = self.pz + dz * PLAYER_SPEED * DT
        cx = _clamp(nx, -ARENA_HALF_X + PLAYER_RADIUS, ARENA_HALF_X - PLAYER_RADIUS)
        cy = _clamp(ny, -ARENA_HALF_Y + PLAYER_RADIUS, ARENA_HALF_Y - PLAYER_RADIUS)
        cz = _clamp(nz, -ARENA_HALF_Z + PLAYER_RADIUS, ARENA_HALF_Z - PLAYER_RADIUS)
        grazed = (cx != nx) or (cy != ny) or (cz != nz)
        self.px, self.py, self.pz = cx, cy, cz
        return grazed

    def _update_aim(self, inputs: dict) -> None:
        ax, ay, az = _vector(inputs, "aim")
        mag = math.sqrt(ax * ax + ay * ay + az * az)
        if mag > 1e-6:  # no aim held: keep facing where we last aimed
            self.aim_x, self.aim_y, self.aim_z = ax / mag, ay / mag, az / mag

    def _fire(self, inputs: dict, events: list) -> None:
        if self.fire_cooldown > 0:
            self.fire_cooldown -= 1
        if not inputs.get("fire") or self.fire_cooldown > 0:
            return
        self.fire_cooldown = FIRE_INTERVAL
        self.bullets.append({
            "id": self._take_id(),
            "x": self.px + self.aim_x * MUZZLE_OFFSET,
            "y": self.py + self.aim_y * MUZZLE_OFFSET,
            "z": self.pz + self.aim_z * MUZZLE_OFFSET,
            "vx": self.aim_x * BULLET_SPEED,
            "vy": self.aim_y * BULLET_SPEED,
            "vz": self.aim_z * BULLET_SPEED,
        })
        events.append("fire")

    def _move_bullets(self) -> bool:
        alive = []
        left = False
        for b in self.bullets:
            b["x"] += b["vx"] * DT
            b["y"] += b["vy"] * DT
            b["z"] += b["vz"] * DT
            if (-ARENA_HALF_X <= b["x"] <= ARENA_HALF_X
                    and -ARENA_HALF_Y <= b["y"] <= ARENA_HALF_Y
                    and -ARENA_HALF_Z <= b["z"] <= ARENA_HALF_Z):
                alive.append(b)
            else:
                left = True
        self.bullets = alive
        return left

    def _materialise(self) -> None:
        for e in self.enemies:
            if e["spawn"] > 0:
                e["spawn"] -= 1

    def _move_enemies(self) -> None:
        for e in self.enemies:
            if e["spawn"] > 0:
                continue  # still materialising: it does not move
            dx = self.px - e["x"]
            dy = self.py - e["y"]
            dz = self.pz - e["z"]
            dist = math.sqrt(dx * dx + dy * dy + dz * dz)
            if dist <= 1e-9:
                continue
            ux, uy, uz = dx / dist, dy / dist, dz / dist
            speed = self.enemy_speed
            kind = e["kind"]
            if kind == KIND_WEAVER:
                # Chase, plus a lateral swing perpendicular to the approach. The
                # perpendicular is built from whichever world axis is least aligned
                # with the approach, so it is well-defined for every direction.
                axis = min(((abs(ux), (1.0, 0.0, 0.0)), (abs(uy), (0.0, 1.0, 0.0)),
                            (abs(uz), (0.0, 0.0, 1.0))), key=lambda p: p[0])[1]
                sx = uy * axis[2] - uz * axis[1]
                sy = uz * axis[0] - ux * axis[2]
                sz = ux * axis[1] - uy * axis[0]
                sn = math.sqrt(sx * sx + sy * sy + sz * sz) or 1.0
                swing = WEAVE_AMPLITUDE * math.sin(
                    2.0 * math.pi * ((self.tick + e["phase"]) % WEAVE_PERIOD) / WEAVE_PERIOD)
                ux += swing * sx / sn
                uy += swing * sy / sn
                uz += swing * sz / sn
                n = math.sqrt(ux * ux + uy * uy + uz * uz) or 1.0
                ux, uy, uz = ux / n, uy / n, uz / n
            elif kind == KIND_CHARGER:
                # Hold still, then burst. Not a speed difference: for most of its
                # cycle it does not move at all.
                cycle = (self.tick + e["phase"]) % (CHARGE_WINDUP + CHARGE_DASH)
                if cycle < CHARGE_WINDUP:
                    continue
                speed = self.enemy_speed * CHARGE_SPEED_MULT
            e["x"] += ux * speed * DT
            e["y"] += uy * speed * DT
            e["z"] += uz * speed * DT

    def _bullets_hit_enemies(self, events: list) -> None:
        survivors = []
        for b in self.bullets:
            struck = None
            for e in self.enemies:
                if e["spawn"] > 0:
                    continue  # materialising enemies cannot be hit
                reach = BULLET_RADIUS + ENEMY_RADIUS
                if ((b["x"] - e["x"]) ** 2 + (b["y"] - e["y"]) ** 2
                        + (b["z"] - e["z"]) ** 2) <= reach * reach:
                    struck = e
                    break
            if struck is None:
                survivors.append(b)
                continue
            struck["hp"] -= 1
            events.append("enemy_hit")
            if struck["hp"] <= 0:
                self.enemies.remove(struck)
                self.kills += 1
                self.score += SCORE_PER_KILL * self.wave * self.multiplier
                events.append("enemy_dead")
                self._reward_streak(events)
        self.bullets = survivors

    def _reward_streak(self, events: list) -> None:
        self.streak += 1
        if self.streak % KILLS_PER_MULT == 0 and self.multiplier < MULT_MAX:
            self.multiplier += 1
            events.append("multiplier")

    def _enemies_hit_player(self, events: list) -> None:
        if self.invuln > 0:
            return
        reach = PLAYER_RADIUS + ENEMY_RADIUS
        for e in list(self.enemies):
            if e["spawn"] > 0:
                continue  # materialising enemies are harmless
            if ((self.px - e["x"]) ** 2 + (self.py - e["y"]) ** 2
                    + (self.pz - e["z"]) ** 2) <= reach * reach:
                self.enemies.remove(e)
                self.kills += 1  # the collision destroys it, but it is worth no points
                events.append("enemy_dead")
                self.hp -= 1
                self.invuln = INVULN_TICKS
                events.append("player_hit")
                self.streak = 0
                if self.multiplier > 1:
                    self.multiplier = 1
                    events.append("multiplier")
                if self.hp <= 0:
                    self.hp = 0
                    self.alive = False
                    self.game_over = True
                    events.append("game_over")
                return

    def _advance_waves(self, events: list) -> None:
        if self.game_over:
            return
        if self.pending > 0:
            self.pending -= 1
            if self.pending == 0:
                self._spawn_wave(events)
                events.append("wave_start")
        elif not self.enemies:
            self.wave += 1
            self.pending = WAVE_GAP_TICKS

    # ---------------------------------------------------------------- views

    def state(self) -> dict:
        return {
            "arena": {"half_x": ARENA_HALF_X, "half_y": ARENA_HALF_Y,
                      "half_z": ARENA_HALF_Z},
            "player": {"x": _r(self.px), "y": _r(self.py), "z": _r(self.pz),
                       "hp": self.hp, "alive": self.alive},
            "enemies": [{"id": e["id"], "kind": e["kind"], "x": _r(e["x"]),
                         "y": _r(e["y"]), "z": _r(e["z"]), "hp": e["hp"],
                         "spawning": e["spawn"] > 0}
                        for e in sorted(self.enemies, key=lambda e: e["id"])],
            "bullets": [{"id": b["id"], "x": _r(b["x"]), "y": _r(b["y"]),
                         "z": _r(b["z"]), "vx": _r(b["vx"]), "vy": _r(b["vy"]),
                         "vz": _r(b["vz"])}
                        for b in sorted(self.bullets, key=lambda b: b["id"])],
            "wave": self.wave,
            "score": self.score,
            "kills": self.kills,
            "multiplier": self.multiplier,
            "game_over": self.game_over,
        }

    def hash_hex(self) -> str:
        h = Hasher()
        h.s("arena3d").u(self.tick)
        h.f(self.px).f(self.py).f(self.pz).i(self.hp).i(1 if self.alive else 0)
        h.f(self.aim_x).f(self.aim_y).f(self.aim_z)
        h.i(self.fire_cooldown).i(self.invuln)
        for e in sorted(self.enemies, key=lambda e: e["id"]):
            h.i(e["id"]).s(e["kind"]).f(e["x"]).f(e["y"]).f(e["z"])
            h.i(e["hp"]).i(e["spawn"]).i(e["phase"])
        for b in sorted(self.bullets, key=lambda b: b["id"]):
            h.i(b["id"]).f(b["x"]).f(b["y"]).f(b["z"])
            h.f(b["vx"]).f(b["vy"]).f(b["vz"])
        h.i(self.wave).i(self.score).i(self.kills).i(self.pending)
        h.i(self.multiplier).i(self.streak)
        h.f(self.enemy_speed).i(self.next_id).i(1 if self.game_over else 0)
        h.u(self.rng.state)
        return h.hex()
