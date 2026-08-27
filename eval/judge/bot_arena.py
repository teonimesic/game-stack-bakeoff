#!/usr/bin/env python3
"""Scripted play-bot for the 3D twin-stick arena shooter task.

Rewritten 2026-08-15 for the 3D/analog spec. Three criteria are genre-defining and
none of them can be settled by looking at a screenshot:

* `aim.independent` - the firing direction is chosen separately from the movement
  direction, now in three axes rather than eight compass points;
* `move.analog` - a half-pushed control moves at half speed. An eight-way
  implementation looks identical in a frame and fails this in one tick;
* `enemy.materialises` - a newly spawned enemy can be neither hit nor hurt by, for a
  window. Driving it and firing into that window settles it.

EVERY CRITERION HERE ESTABLISHES ITS CONDITION AND THEN MEASURES. None waits for a
condition to arrive. Sixteen false negatives in this project came from criteria that
idled and hoped (FINDINGS #29, #34), and the repair for each was to make the bot cause
the thing it is asserting about.
"""

from __future__ import annotations

import math
from typing import Any

from checks import determinism_criteria, idle_tape
from probe import (Bot, Criterion, ProbeError, ProbeSession, Tick,
                   end_condition_holds, unusable_criteria)

Vec = tuple[float, float, float]


def _player(t: Tick) -> dict[str, Any]:
    p = t.state.get("player")
    return p if isinstance(p, dict) else {}


def _list(t: Tick, key: str) -> list[dict[str, Any]]:
    v = t.state.get(key)
    return [e for e in v if isinstance(e, dict)] if isinstance(v, list) else []


def _f(d: dict[str, Any], k: str, default: float | None = None) -> float | None:
    try:
        v = float(d[k])
    except (KeyError, TypeError, ValueError):
        return default
    return v if math.isfinite(v) else default


def _i(t: Tick, key: str, default: int = 0) -> int:
    try:
        return int(t.state.get(key, default))
    except (TypeError, ValueError):
        return default


def _xyz(d: dict[str, Any]) -> Vec:
    return (_f(d, "x", 0.0) or 0.0, _f(d, "y", 0.0) or 0.0, _f(d, "z", 0.0) or 0.0)


def _sub(a: Vec, b: Vec) -> Vec:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _norm(v: Vec) -> float:
    return math.sqrt(v[0] * v[0] + v[1] * v[1] + v[2] * v[2])


def _unit(v: Vec) -> Vec | None:
    n = _norm(v)
    return (v[0] / n, v[1] / n, v[2] / n) if n > 1e-6 else None


def _dot(a: Vec, b: Vec) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _dist(a: Vec, b: Vec) -> float:
    return _norm(_sub(a, b))


def _cross(a: Vec, b: Vec) -> Vec:
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])


def _perp(u: Vec) -> Vec:
    """Any unit vector perpendicular to `u`, chosen from the least-aligned world axis."""
    axis = min(((abs(u[0]), (1.0, 0.0, 0.0)), (abs(u[1]), (0.0, 1.0, 0.0)),
                (abs(u[2]), (0.0, 0.0, 1.0))), key=lambda p: p[0])[1]
    return _unit(_cross(u, axis)) or (0.0, 1.0, 0.0)


def _clampf(v: float, lo: float, hi: float) -> float:
    return lo if v < lo else (hi if v > hi else v)


def _leg(*, gone: bool, at, gap, hit: bool, cos: list[float], d0: float, p1: Vec,
         d1: float, trail: list[Vec], late_n: int, q1: Vec, over: bool
         ) -> dict[str, Any]:
    """One chase leg's result. ONE constructor, so every exit carries every key.

    `late` is the enemy's heading over the CLOSING ticks of the leg, not over the whole
    of it: a net displacement averages a turn away, and an enemy that spends half a leg
    going one way and half the other reads as though it never turned at all.
    """
    back = trail[max(0, len(trail) - 1 - late_n)]
    return {"gone": gone, "at": at, "gap": gap, "hit": hit, "cos": cos, "d0": d0,
            "p1": p1, "d1": d1, "over": over, "ticks": len(cos),
            "late": _unit(_sub(p1, back)), "want_late": _unit(_sub(q1, p1)),
            "align": (sum(cos) / len(cos)) if cos else None}


def _fmt(v: float | None) -> str:
    return "None" if v is None else f"{v:.2f}"


def _move(v: Vec) -> dict[str, float]:
    return {"move_x": v[0], "move_y": v[1], "move_z": v[2]}


def _aim(v: Vec) -> dict[str, float]:
    return {"aim_x": v[0], "aim_y": v[1], "aim_z": v[2]}


def _live(t: Tick) -> list[dict[str, Any]]:
    """Enemies that have finished materialising. A spawning enemy is not a target."""
    return [e for e in _list(t, "enemies") if e.get("spawning") is not True]


def _nearest(t: Tick, only_live: bool = True) -> dict[str, Any] | None:
    p = _xyz(_player(t))
    pool = _live(t) if only_live else _list(t, "enemies")
    best, bd = None, float("inf")
    for e in pool:
        d = _dist(_xyz(e), p)
        if d < bd:
            best, bd = e, d
    return best


#: How long the bot waits at the START of a session for the game to hand play over.
#: Eight seconds at 64 Hz covers an opening title card, a countdown and a pause, and a
#: game that has not handed control over by then is not withholding play for
#: presentation.
#:
#: ONE CONSTANT, 10 PLACES - the main session and every one of the 9 sibling sessions
#: this bot opens. A card gates the SIMULATION, so it gates each fresh session from that
#: session's own tick 0; a budget spent only on the criteria that happen to be shortest
#: leaves the rest red on the same card, which is `tasks/158`'s finding on
#: `bot_tetris3d` and the reason that repair reached 4 call sites rather than 2.
#:
#: What it was worth here, measured on `ref_arena` before the repair by lengthening a
#: card until each criterion broke (`tasks/173`): 30 ticks failed `player.moves` and
#: `move.analog`, 120 added `fire.spawns_bullets`, `fire.rate_limited` and
#: `aim.independent`, 300 added `enemy.materialises`, 360 `aim.three_axis`, 368
#: `enemies.chase`, 390 `enemies.spawn`, and by 800 `player.bounded` and `wall.graze`
#: took it to 11 of 22. 9 of those 11 break at or under this budget.
#:
#: `bot_pong.LIVE_BUDGET`, `bot_tetris3d.OPENING_BUDGET` and
#: `bot_platformer._CONTROL_TICKS` are this same 512, bought by a Godot submission that
#: held the ball for `OPENING_DELAY = 104` so its title card would be readable (#34).
OPENING_BUDGET = 512


class ArenaBot(Bot):
    game = "g3_arena"
    #: Long enough to meet several waves, so pacing is a property of the game rather
    #: than of how long the criteria happened to take (FINDINGS #52).
    play_ticks = 3000
    #: The criterion that checks THIS GAME'S END CONDITION, whatever it is called.
    #: Named explicitly because the concept has two spellings across the suite:
    #: `gameover.triggers` in three games and `match.ends` in pong, which is
    #: first-to-11, so its end condition is a WIN rather than a loss. This game
    #: ends when the player's health reaches zero.
    #: A cross-game audit asking "does every game verify its own end condition?"
    #: would grep for `gameover` and report a false gap for pong - a mechanical sweep
    #: reporting something untrue, which this project has lost time to before (#38).
    #: Read this attribute instead of guessing from the id.
    end_condition = "gameover.triggers"

    criteria = [
        ("state.shape", "Does the probe report the contracted state shape (a three-axis "
                        "arena, player, enemies with kind and spawning, bullets, wave, "
                        "score, multiplier, game_over)?"),
        ("player.moves", "Does holding a movement control move the player, on each of "
                         "the three axes?"),
        ("move.analog", "Is movement analog — does a half-pushed control move at about "
                        "half speed, and is an off-axis direction honoured rather than "
                        "snapped to a compass point?"),
        ("player.bounded", "Does the player stop at the arena boundary instead of "
                           "leaving the volume?"),
        ("wall.graze", "Does reaching the boundary raise a wall_graze?"),
        ("enemies.spawn", "Do enemies spawn, and is a wave announced?"),
        ("enemy.kinds", "Are there at least three distinct kinds of enemy?"),
        ("enemy.materialises", "Does a newly spawned enemy materialise — reported as "
                               "spawning, unhittable and harmless — before becoming "
                               "active?"),
        ("enemies.chase", "Do enemies move toward the player?"),
        ("fire.spawns_bullets", "Does holding fire create bullets that travel?"),
        ("fire.rate_limited", "Is there a minimum interval between shots rather than "
                              "one bullet per tick?"),
        ("aim.independent", "Can the firing direction be chosen independently of the "
                            "movement direction?"),
        ("aim.three_axis", "Can the player aim and fire along all three axes, including "
                           "the depth axis?"),
        ("bullets.kill", "Do bullets destroy enemies?"),
        ("score.on_kill", "Does destroying an enemy raise the score?"),
        ("multiplier.rises", "Does sustained killing raise the score multiplier?"),
        ("multiplier.falls", "Does taking damage drop the multiplier back?"),
        ("wave.advances", "Does clearing a wave start the next one?"),
        ("player.takes_damage", "Does the player lose health when an enemy reaches "
                                "them?"),
        ("gameover.triggers", "Does the game end at zero health and stop accepting "
                              "play?"),
        ("determinism.replay", "Does replaying the same seed and the same inputs "
                               "reproduce the same state hash at every tick?"),
        ("determinism.seed", "Do two different seeds produce different runs?"),
    ]

    def play_inputs(self, tick: Tick) -> dict[str, Any]:
        """Competent play for the representative pacing session: aim, fire, hold range."""
        arena = tick.state.get("arena")
        half = ((_f(arena, "half_x") or 400.0, _f(arena, "half_y") or 250.0,
                 _f(arena, "half_z") or 400.0) if isinstance(arena, dict)
                else (400.0, 250.0, 400.0))
        return self._play_inputs(tick, half)

    def run(self, s: ProbeSession) -> list[Criterion]:
        out: list[Criterion] = []
        add = out.append
        t0 = s.last
        p0 = _player(t0)

        arena = t0.state.get("arena")
        shape_ok = (
            isinstance(arena, dict)
            and all(_f(arena, k) is not None for k in ("half_x", "half_y", "half_z"))
            and all(_f(p0, k) is not None for k in ("x", "y", "z"))
            and isinstance(p0.get("hp"), (int, float))
            and isinstance(t0.state.get("enemies"), list)
            and isinstance(t0.state.get("bullets"), list)
            and isinstance(t0.state.get("multiplier"), (int, float))
            and isinstance(t0.state.get("game_over"), bool)
        )
        add(Criterion("state.shape", self._q("state.shape"), shape_ok,
                      f"tick 0 state keys: {sorted(t0.state)}; arena keys: "
                      f"{sorted(arena) if isinstance(arena, dict) else arena}"))
        if not shape_ok or not isinstance(arena, dict):
            for cid, q in self.criteria[1:]:
                add(Criterion(cid, q, False, "state shape contract not met"))
            return out
        half = (_f(arena, "half_x") or 400.0, _f(arena, "half_y") or 250.0,
                _f(arena, "half_z") or 400.0)

        # WAIT FOR PLAY TO BE HANDED OVER before anything is concluded. `state.shape` is
        # above this line because it reads tick 0, which a card answers as truthfully as
        # a running game does; everything below needs the simulation.
        live, _, note = self._take_control(s)
        if not live:
            for cid, q in self.criteria[1:]:
                add(Criterion(cid, q, False, note))
            return out

        # ORDER MATTERS. Standing around costs health, so everything that needs a LIVE
        # player runs first and briefly; the long walks into the wall run last, in
        # their own sessions. The first version of this bot did a 1200-tick walk up
        # front and then measured firing on a corpse.
        add(self._moves(s))

        # --- enemies -------------------------------------------------------- #
        wave_evt = any("wave_start" in t.events for t in s.history)
        n_enemies = len(_list(s.last, "enemies"))
        for _ in range(300):
            if n_enemies:
                break
            t = s.step_raw({})
            wave_evt = wave_evt or "wave_start" in t.events
            n_enemies = len(_list(t, "enemies"))
        add(Criterion("enemies.spawn", self._q("enemies.spawn"),
                      n_enemies > 0 and wave_evt,
                      f"{n_enemies} enemies present; wave_start seen: {wave_evt}"))

        # --- everything below opens a SIBLING session, which closes `s` ------- #
        # Sessions are serialised per repository (FINDINGS #29/#30): starting a second
        # one closes the first. So every measurement that uses `s` must already be
        # done. Putting `move.analog` above this line cost 22 criteria in one run -
        # all of them reported "closed because a sibling session started", which is the
        # guard working exactly as designed and is NOT a submission defect.
        repo, env = s.repo, s.env
        add(self._kinds(repo, env, half))
        add(self._chase(repo, env, half))
        add(self._analog(repo, env)[0])
        add(self._materialises(repo, env))
        fire_c, rate_c, aim_c, axis_c = self._firing(repo, env)
        add(fire_c)
        add(rate_c)
        add(aim_c)
        add(axis_c)
        for c in self._combat(repo, env):
            add(c)
        add(self._multiplier_falls(repo, env))
        for c in self._death(repo, env):
            add(c)
        for c in self._walls(repo, env, half):
            add(c)

        out.extend(determinism_criteria(repo, idle_tape(300), env=env))
        return out

    # ------------------------------------------------------------------ #

    def _q(self, cid: str) -> str:
        return next(q for c, q in self.criteria if c == cid)

    @staticmethod
    def _take_control(s: ProbeSession) -> tuple[bool, int, str]:
        """Step until the player actually answers a movement input.

        Not a fixed delay and not a flag: the property is "the game has handed control
        over", so that is what is measured. A title card, a countdown and a "press any
        key" screen all pass through here identically, and
        `bot_platformer._take_control` is the same check on the same budget.

        IT RETURNS ON THE FIRST ANSWERING TICK, which is what keeps it out of the
        measurements that follow. A game already playing pays one tick of movement -
        3.4 units on the reference, against a 400-unit half-extent - so `move.analog`
        still opens its two pushes from the same place, `_walls` still has the whole
        volume to cross, and `_death` still stands still for all but that tick. The
        displacement is bounded by the threshold rather than by the budget: a game that
        accelerates is past 1.0 unit while it is still barely moving.

        Any axis answers. The push is +x because that is the axis `player.moves` reads
        first, but the test is on the DISTANCE moved, so a game that maps the axes
        differently hands control over here and fails `player.moves` on its own account
        rather than through this.
        """
        p0 = _xyz(_player(s.last))
        for i in range(OPENING_BUDGET):
            t = s.step_raw(_move((1.0, 0.0, 0.0)))
            p1 = _xyz(_player(t))
            if _dist(p1, p0) > 1.0:
                return True, i + 1, (
                    f"the player answered a movement input after {i + 1} tick(s) "
                    f"({p0} -> {p1})")
        return False, OPENING_BUDGET, (
            f"the player never answered a movement input in {OPENING_BUDGET} ticks "
            f"({OPENING_BUDGET / 64:.1f}s), so play was never handed over "
            f"(it stayed at {p0})")

    # -- movement --------------------------------------------------------- #

    def _moves(self, s: ProbeSession) -> Criterion:
        """Push each axis in turn and require the player to answer on that axis."""
        moved: dict[str, float] = {}
        for name, vec in (("x", (1.0, 0.0, 0.0)), ("y", (0.0, 1.0, 0.0)),
                          ("z", (0.0, 0.0, 1.0))):
            before = _xyz(_player(s.last))
            for _ in range(30):
                s.step_raw(_move(vec))
            after = _xyz(_player(s.last))
            moved[name] = _dot(_sub(after, before), vec)
        ok = all(v > 2.0 for v in moved.values())
        return Criterion("player.moves", self._q("player.moves"), ok,
                         "displacement along each axis after 30 ticks of full push: "
                         + ", ".join(f"{k}={v:.1f}" for k, v in moved.items()))

    _ANALOG_TICKS = 30

    def _analog(self, repo, env) -> tuple[Criterion]:
        """Half a push must move about half as far, and an off-axis direction must
        survive as a direction.

        A fresh session per magnitude, from the identical start, so the two runs differ
        only in the input. Measuring both inside one session would compare a player at
        the origin with one already displaced - and, near a wall, with one that cannot
        move at all.

        `_take_control` runs first in each of them and it does not break that: it holds
        the same full push in all three, ends on the same tick against the same card,
        and the start is recorded AFTER it. What it costs is the one answering tick of
        displacement, which both magnitudes pay identically.
        """
        cid = "move.analog"
        note = ""
        try:
            def push(vec: Vec) -> Vec | None:
                nonlocal note
                with ProbeSession(repo=repo, env=env, seed=7) as s:
                    live, _, note = self._take_control(s)
                    if not live:
                        return None
                    start = _xyz(_player(s.last))
                    for _ in range(self._ANALOG_TICKS):
                        s.step_raw(_move(vec))
                    return _sub(_xyz(_player(s.last)), start)

            pushes = [push(v) for v in ((1.0, 0.0, 0.0), (0.5, 0.0, 0.0),
                                        (1.0, 0.0, 0.25))]
        except ProbeError as e:
            return (unusable_criteria([(cid, self._q(cid))], e, "the analog session")[0],)

        if any(p is None for p in pushes):
            return (Criterion(cid, self._q(cid), False, note),)
        full, half, skew = pushes

        d_full, d_half = full[0], half[0]
        if d_full <= 1.0:
            return (Criterion(cid, self._q(cid), False,
                              f"a full push moved only {d_full:.2f} units, so a "
                              f"proportional response cannot be measured"),)
        ratio = d_half / d_full
        # A half push should travel about half as far. The band is wide because
        # acceleration, friction and a speed cap are all legitimate designs; what it
        # excludes is 1.0 (the input was rounded up to a full push) and 0.0 (rounded
        # down to nothing) - which is exactly what eight-way movement does.
        prop = 0.25 <= ratio <= 0.75
        skew_ok = True
        skew_note = "not measured"
        if abs(skew[0]) > 1.0:
            got = skew[2] / skew[0]
            skew_ok = 0.10 <= got <= 0.45   # asked for 0.25
            skew_note = f"asked for z/x=0.25, got {got:.3f}"
        return (Criterion(
            cid, self._q(cid), prop and skew_ok,
            f"over {self._ANALOG_TICKS} ticks a full push moved {d_full:.2f} and a half "
            f"push moved {d_half:.2f} (ratio {ratio:.3f}, wants 0.25-0.75); "
            f"off-axis: {skew_note}"),)

    def _walls(self, repo, env, half: Vec) -> list[Criterion]:
        """Push into a corner of the volume from a fresh game.

        Two criteria share the session because they share the experiment: the player
        is driven into the boundary, which is the condition both need.
        """
        ids = ("player.bounded", "wall.graze")
        try:
            with ProbeSession(repo=repo, env=env, seed=7) as s:
                live, _, note = self._take_control(s)
                if not live:
                    return [Criterion(c, self._q(c), False, note) for c in ids]
                pts: list[Vec] = []
                grazed = False
                for _ in range(900):
                    t = s.step_raw(_move((1.0, 1.0, 1.0)))
                    grazed = grazed or "wall_graze" in t.events
                    pts.append(_xyz(_player(t)))
                inside = all(abs(p[i]) <= half[i] + 1e-3
                             for p in pts for i in range(3))
                reached = [max((abs(p[i]) for p in pts), default=0.0) >= half[i] * 0.5
                           for i in range(3)]
                bounded = Criterion(
                    "player.bounded", self._q("player.bounded"),
                    inside and all(reached),
                    f"900 ticks pushing into the corner: final {pts[-1] if pts else 'n/a'}, "
                    f"half-extents {half}; never left: {inside}; got at least halfway "
                    f"on each axis: {reached}")
                graze = Criterion(
                    "wall.graze", self._q("wall.graze"), grazed,
                    f"wall_graze seen while pressed against the boundary for 900 "
                    f"ticks: {grazed}")
                return [bounded, graze]
        except ProbeError as e:
            return list(unusable_criteria([(cid, self._q(cid)) for cid in ids], e,
                                          "the wall session"))

    # -- enemy variety and materialisation --------------------------------- #

    _KINDS_TICKS = 6000
    _KINDS_WANTED = 3
    _STANDOFF = 160.0       # the range the play policy tries to hold an enemy at

    def _play_inputs(self, t: Tick, half: Vec) -> dict[str, Any]:
        """One tick of competent play: aim at the nearest live enemy, fire, hold range.

        Two corrections on top of "run away", each measured rather than reasoned:

        * **bend back toward the middle** in proportion to how close the wall is. Kiting
          straight away from the threat - which is what `_combat` does - walks the
          player into a corner and pins it there, and a pinned player cannot retreat at
          all;
        * **close when the enemy is far.** See the standoff comment below.

        This policy has to keep the player ALIVE for thousands of ticks AND clear waves,
        which is a stronger requirement than anything `_combat` faces.
        """
        p = _xyz(_player(t))
        home = _unit(tuple(-p[i] / (half[i] or 1.0) for i in range(3)))
        e = _nearest(t)
        inputs: dict[str, Any] = {"fire": True}
        u = _unit(_sub(_xyz(e), p)) if e is not None else None
        if u is None:
            inputs.update(_aim((1.0, 0.0, 0.0)))
            if home:
                inputs.update(_move(home))
            return inputs
        inputs.update(_aim(u))
        # HOLD A STANDOFF, do not simply retreat. Retreating unconditionally is what
        # `_combat` does and it deadlocks: measured on `g3_arena__ts__t0`, the bot
        # cleared eleven enemies by tick 600 and then backed away from the twelfth for
        # 5,400 ticks at a steady 495 units, out of bullet range, one kill short of the
        # wave that would have unlocked the third enemy kind. A criterion that needs
        # waves cleared needs a policy that closes as well as one that runs.
        gap = _dist(_xyz(e), p)
        radial = _clampf((gap - self._STANDOFF) / self._STANDOFF, -1.0, 1.0)
        wall = max(abs(p[i]) / (half[i] or 1.0) for i in range(3))
        pull = 1.5 * wall * wall
        step = tuple(radial * u[i] for i in range(3))
        if home is not None:
            step = tuple(step[i] + pull * home[i] for i in range(3))
        inputs.update(_move(_unit(step) or (-u[0], -u[1], -u[2])))
        return inputs

    def _kinds(self, repo, env, half: Vec) -> Criterion:
        """PLAY until three kinds have been met, in a session of the bot's own.

        THE CRITERION ESTABLISHES ITS CONDITION. The version this replaces sampled
        whatever wandered past while the player stood still and did nothing, then gave
        "later waves a chance" by idling up to 600 more ticks. Standing still is fatal
        in this game - the reference and all six agent-built submissions kill an idle
        player between tick 362 and tick 844 - so the bot never left wave 1, and every
        one of the six submissions ships FOUR kinds gated behind `wave >= 2`,
        `wave >= 3` and `wave >= 4`. It reported `['drifter']` six times out of six
        with identical evidence, and the split looked like a property of the task.
        See FINDINGS #46.

        Meeting three kinds now requires clearing waves, which requires killing, which
        requires surviving. That is the experiment.
        """
        cid = "enemy.kinds"
        try:
            with ProbeSession(repo=repo, env=env, seed=7,
                              total_timeout_s=1200.0) as s:
                live, _, note = self._take_control(s)
                if not live:
                    return Criterion(cid, self._q(cid), False, note)
                first_wave: dict[str, int] = {}
                waves: list[int] = [_i(s.last, "wave", 1)]
                prev = s.last

                def harvest(t: Tick) -> None:
                    w = _i(t, "wave", 1)
                    for e in _list(t, "enemies"):
                        k = e.get("kind")
                        if isinstance(k, str) and k and k not in first_wave:
                            first_wave[k] = w

                harvest(prev)
                over = False
                for _ in range(self._KINDS_TICKS):
                    if len(first_wave) >= self._KINDS_WANTED:
                        break
                    t = s.step_raw(self._play_inputs(prev, half))
                    harvest(t)
                    waves.append(_i(t, "wave", 1))
                    prev = t
                    if t.state.get("game_over") is True:
                        over = True
                        break
                kills = _i(s.last, "kills")
                ticks = s.ticks_sent
        except ProbeError as e:
            return unusable_criteria([(cid, self._q(cid))], e, "the kinds session")[0]

        met = sorted(first_wave)
        # The wave reached is reported because it is what separates the two ways this
        # criterion can fail, and the old evidence string could not tell them apart:
        # "one kind after four waves" is a submission defect, "one kind and never left
        # wave 1" is the bot failing to establish the condition.
        return Criterion(
            cid, self._q(cid), len(met) >= self._KINDS_WANTED,
            f"distinct kinds observed: {met} (first seen in wave "
            f"{ {k: first_wave[k] for k in met} }); reached wave "
            f"{max(waves)} from wave {waves[0]} over {ticks} ticks of "
            f"aim-fire-and-hold-range with {kills} kills; game_over: {over}")

    _MATERIALISE_SHOTS = 240

    def _materialises(self, repo, env) -> Criterion:
        """Find an enemy on the tick it appears, and fire into its spawn window.

        This is the experiment: a criterion that merely checked `spawning` is ever true
        would pass a game that reports the flag and ignores it. What must hold is that
        the flag MEANS something - no hit lands on that enemy while it is set.
        """
        cid = "enemy.materialises"
        try:
            with ProbeSession(repo=repo, env=env, seed=7) as s:
                live, _, note = self._take_control(s)
                if not live:
                    return Criterion(cid, self._q(cid), False, note)
                # Step to the first wave and take the enemy that is spawning.
                target = None
                for _ in range(300):
                    t = s.step_raw({})
                    spawning = [e for e in _list(t, "enemies")
                                if e.get("spawning") is True]
                    if spawning:
                        target = spawning[0]
                        break
                if target is None:
                    seen_flag = any(e.get("spawning") is not None
                                    for t in s.history for e in _list(t, "enemies"))
                    return Criterion(
                        cid, self._q(cid), False,
                        "no enemy ever reported spawning=true in the first 300 ticks"
                        + ("" if seen_flag else "; the field was never present at all"))
                eid = target.get("id")
                # Fire at it for as long as it claims to be materialising.
                hits = 0
                ticks_spawning = 0
                p = _xyz(_player(s.last))
                aim = _unit(_sub(_xyz(target), p)) or (1.0, 0.0, 0.0)
                for _ in range(self._MATERIALISE_SHOTS):
                    t = s.step_raw({"fire": True, **_aim(aim)})
                    me = next((e for e in _list(t, "enemies")
                               if e.get("id") == eid), None)
                    if me is None:
                        break
                    if me.get("spawning") is True:
                        ticks_spawning += 1
                        hits += t.events.count("enemy_hit")
                        aim = _unit(_sub(_xyz(me), _xyz(_player(t)))) or aim
                    else:
                        break
                    if t.state.get("game_over") is True:
                        break
                ok = ticks_spawning >= 1 and hits == 0
                return Criterion(
                    cid, self._q(cid), ok,
                    f"enemy id={eid!r} reported spawning for {ticks_spawning} ticks "
                    f"while being fired at; enemy_hit events during that window: "
                    f"{hits} (wants 0)")
        except ProbeError as e:
            return unusable_criteria([(cid, self._q(cid))], e,
                                     "the materialisation session")[0]

    # -- enemies.chase: follow ONE enemy, and move its target ---------------- #

    _CHASE_LEG = 145        # about a half circle at _CHASE_RADIUS and full speed
    _CHASE_APPROACH = 260   # set-up ticks allowed to reach the working radius
    _CHASE_LATE = 30        # ticks at the close of a leg that define its heading
    _CHASE_MIN_SAMPLES = 20
    _CHASE_ALIGN = 0.5
    _CHASE_TURN_SHARE = 0.5
    _CHASE_TURN_MIN = 0.3   # below this the experiment demanded no turn to observe
    _CHASE_DODGE = 90.0
    _CHASE_RADIUS = 150.0   # the radius the player circles the enemy at

    @staticmethod
    def _follow(t: Tick, eid: Any, last: Vec) -> dict[str, Any] | None:
        """The SAME enemy at a later tick.

        By `id` when the game reports one: the version this replaces re-picked the
        NEAREST enemy at each end of the window, so an enemy that reached the player
        and was destroyed on contact - a chase that worked perfectly - showed up as the
        distance jumping to the next enemy out (FINDINGS #29).
        """
        enemies = _list(t, "enemies")
        if eid is not None:
            for e in enemies:
                if e.get("id") == eid:
                    return e
            return None
        best, bd = None, float("inf")
        for e in enemies:
            d = _dist(_xyz(e), last)
            if d < bd:
                best, bd = e, d
        return best if bd <= 40.0 else None

    def _orbit_step(self, here: Vec, enemy: Vec, normal: Vec | None) -> Vec | None:
        """One tick of circling the enemy at `_CHASE_RADIUS` about `normal`.

        With `normal` None it only corrects the radius; otherwise it also sweeps at a
        constant rotational sense, so the direction from the enemy to the player turns
        steadily through a half circle per leg. The player is over three times an
        enemy's speed, and this is what that speed is FOR: it is the only way to demand
        a large turn of a pursuer without either outrunning it (running corner to corner
        blew the gap out to 730 units and the geometry then stopped changing) or walking
        into it, which would let the criterion pass on a contact the PLAYER caused.

        Aiming at a fixed GOAL direction was tried first and is a saddle point: with the
        goal set to the antipode the tangential term is identically zero, the player
        never starts moving round, and the turn test reads 0.00 on a perfect chaser.
        """
        r_vec = _sub(here, enemy)
        r = _norm(r_vec)
        u = _unit(r_vec)
        if u is None:
            return None
        tu = (0.0, 0.0, 0.0) if normal is None else (_unit(_cross(normal, u))
                                                    or (0.0, 0.0, 0.0))
        err = _clampf((self._CHASE_RADIUS - r) / self._CHASE_RADIUS, -1.0, 1.0)
        return _unit(tuple(tu[i] + 2.0 * err * u[i] for i in range(3)))

    def _drive_leg(self, s: ProbeSession, eid: Any, pos: Vec, corner: Vec | None,
                   half: Vec, orbit_goal: Vec | None = None,
                   ticks: int | None = None,
                   hold_radius: bool = False) -> dict[str, Any]:
        """Walk the player toward `corner` while measuring the tracked enemy.

        The measurement is PER TICK: the cosine between the enemy's own step and the
        direction from that enemy to the player at the moment it took the step. A
        pursuer scores near 1 whatever the player does; something travelling a fixed
        heading averages near 0 as the player moves around it.

        That is why the player is kept moving. The version this replaces required the
        player to stand still so that a shrinking distance could be read as pursuit -
        and standing still is fatal in this game, so on every real submission the
        player was already dead when the window opened and the evidence read
        "distance went 0.4 -> 0.4" over a single tick (FINDINGS #46).
        """
        cos: list[float] = []
        trail: list[Vec] = [pos]
        cur = pos
        d0 = _dist(pos, _xyz(_player(s.last)))
        done = 0
        for i in range(ticks if ticks is not None else self._CHASE_LEG):
            here = _xyz(_player(s.last))
            if hold_radius:
                # Set-up, not measurement: back off (or close in) to the working radius
                # and stop as soon as it is reached.
                gap = _dist(here, cur)
                if abs(gap - self._CHASE_RADIUS) < 0.12 * self._CHASE_RADIUS:
                    done = i
                    break
                step = self._orbit_step(here, cur, None)
            elif orbit_goal is not None:
                step = self._orbit_step(here, cur, orbit_goal)
            else:
                step = _unit(_sub(corner or (0.0, 0.0, 0.0), here))
                if step is None or _norm(_sub(corner or here, here)) < 12.0:
                    step = _unit(_sub(here, cur))
            if step is None:
                step = (0.0, 0.0, 0.0)
            # Sidestep any OTHER enemy that is about to land on the player. The tracked
            # enemy is deliberately not dodged - following the player wherever it goes
            # is the thing under test - and nothing is ever fired, so the target can
            # only leave by reaching the player.
            for other in _live(s.last):
                if other.get("id") == eid:
                    continue
                away = _sub(here, _xyz(other))
                if _norm(away) < self._CHASE_DODGE:
                    u = _unit(away)
                    if u:
                        step = _unit(tuple(step[k] + 1.5 * u[k] for k in range(3))) or step
            t = s.step_raw(_move(step))
            e = self._follow(t, eid, cur)
            if e is None:
                # EVERY exit returns the SAME KEYS. The first version returned a short
                # dict here and the caller read `align` off it before testing `gone`,
                # so a submission whose enemy reached the player raised `KeyError` and
                # the fail-closed path scored all 23 criteria FALSE - a 0.000 that
                # would have read as a stack result. The reference never takes this
                # branch, so no mutant and no control could have found it; only a real
                # submission did.
                return _leg(gone=True, at=t.tick, gap=_dist(cur, here),
                            hit="player_hit" in t.events, cos=cos, d0=d0, p1=cur,
                            d1=_dist(cur, here), trail=trail, late_n=self._CHASE_LATE,
                            q1=here, over=t.state.get("game_over") is True)
            nxt = _xyz(e)
            stepv = _unit(_sub(nxt, cur))
            toward = _unit(_sub(here, cur))
            if stepv is not None and toward is not None:
                cos.append(_dot(stepv, toward))
            cur = nxt
            trail.append(cur)
            if t.state.get("game_over") is True:
                break
        q1 = _xyz(_player(s.last))
        return _leg(gone=False, at=None, gap=None, hit=False, cos=cos, d0=d0, p1=cur,
                    d1=_dist(cur, q1), trail=trail, late_n=self._CHASE_LATE, q1=q1,
                    over=s.last.state.get("game_over") is True)

    def _chase(self, repo, env, half: Vec) -> Criterion:
        """The player CIRCLES one enemy, in a session of its own.

        Two things have to hold for "enemies move toward the player" to mean anything,
        and each defeats a different impostor:

        * every step the enemy takes points at the player *now* - measured per tick, so
          something travelling a fixed heading cannot average above the floor;
        * the enemy TURNS when the player goes somewhere else - so something that
          happens to be travelling the right way at the start does not qualify.

        The player is over three times an enemy's speed, so it can hold a radius and
        walk a full circle around it. That demands a half turn of a pursuer on each leg
        while never closing to contact, which matters: a contact the PLAYER caused would
        otherwise read as a chase.

        Three designs were measured and discarded before this one, and all three are
        recorded because each looked correct:

        * standing still and watching a distance shrink (the version this replaces) -
          standing still is fatal in this game, so on all six real submissions the
          player was dead before the window opened and the evidence read "distance went
          0.4 -> 0.4" over what it claimed were 90 ticks (FINDINGS #46);
        * running to one far corner and then another - the player outruns the enemy, the
          gap blows out to 730 units, and the direction from the enemy to the player
          then swings 0.36 out of a possible 2.00. The turn test had nothing to read;
        * running to the corner that most CHANGES where the enemy has to look, instead
          of to the opposite one. This was the repair to the bullet above and it is
          worse, which is why it is written down: on the reference the player outran the
          enemy to corner A, then crossed back toward the far corner and approached the
          enemy head-on, so the direction from the enemy to the player never changed at
          all - mean per-tick alignment 1.00 on BOTH legs and a heading swing of exactly
          0.00. A second leg that creates no turn cannot distinguish a pursuer from
          anything, which is the whole job of the second leg.

        The third design shipped as `_corners`/`_far_corner`/`_turn_corner` and was
        never called from anywhere once the circle replaced it. Task 100 deleted the
        three methods and moved the measurement here; the code is at `03cdb90` if it is
        ever wanted, and `eval/tools/dead_private_control.py` uses that commit as its
        worked example of a cluster that is dead only as a whole.
        """
        cid, q = "enemies.chase", self._q("enemies.chase")
        try:
            with ProbeSession(repo=repo, env=env, seed=7,
                              total_timeout_s=900.0) as s:
                live, _, note = self._take_control(s)
                if not live:
                    return Criterion(cid, q, False, note)
                e0 = _nearest(s.last)
                for _ in range(400):
                    if e0 is not None:
                        break
                    t = s.step_raw({})
                    if t.state.get("game_over") is True:
                        break
                    e0 = _nearest(t)
                if e0 is None:
                    return Criterion(cid, q, False,
                                     f"no enemy finished materialising in "
                                     f"{s.ticks_sent} ticks, so nothing could be "
                                     f"observed chasing")
                eid = e0.get("id")
                pos = _xyz(e0)
                tag = (f"enemy id={eid!r}" if eid is not None
                       else "one enemy (no id reported)")

                # Close to the working radius. Measured like a leg, but it is set-up:
                # what it establishes is only that the criterion has something to watch.
                app = self._drive_leg(s, eid, pos, None, half, orbit_goal=None,
                                      ticks=self._CHASE_APPROACH, hold_radius=True)
                if app["gone"]:
                    return Criterion(
                        cid, q, True,
                        f"{tag} closed to contact at tick {app['at']} from "
                        f"{app['d0']:.1f} units while the player was backing off to "
                        f"{self._CHASE_RADIUS:.0f} (player_hit on that tick: "
                        f"{app['hit']}). An enemy that runs the player down HAS chased.")
                if app["over"]:
                    return Criterion(cid, q, False,
                                     f"{tag}: the player died during the {app['ticks']}"
                                     f"-tick approach, so no chase could be established")

                here = _xyz(_player(s.last))
                u0 = _unit(_sub(here, app["p1"])) or (1.0, 0.0, 0.0)
                normal = _perp(u0)
                legs = []
                for _leg in range(2):
                    start_pos = legs[-1]["p1"] if legs else app["p1"]
                    leg = self._drive_leg(s, eid, start_pos, None, half,
                                          orbit_goal=normal, ticks=self._CHASE_LEG)
                    legs.append(leg)
                    if leg["gone"] or leg["over"]:
                        break
                a = legs[0]
                head = (f"{tag}: closed from {app['d0']:.1f} to {app['d1']:.1f} units, "
                        f"then leg 1 of a circle round it - {a['ticks']} samples, mean "
                        f"step-toward-player {_fmt(a['align'])}, gap {a['d0']:.1f} -> "
                        f"{a['d1']:.1f}")
                if a["gone"]:
                    return Criterion(cid, q, self._caught(a),
                                     head.replace("gap", "gap so far")
                                     + f"; it closed to contact at tick {a['at']}")
                if len(a["cos"]) < self._CHASE_MIN_SAMPLES or a["over"]:
                    return Criterion(
                        cid, q, False,
                        head + f"; the leg ended early (game_over={a['over']}) with "
                               f"fewer than {self._CHASE_MIN_SAMPLES} usable samples, "
                               f"so the chase could not be established either way")
                if len(legs) < 2:
                    return Criterion(cid, q, False,
                                     head + "; the second leg never ran")
                b = legs[1]
                if b["gone"]:
                    return Criterion(
                        cid, q, self._caught(b),
                        head + f"; on the second half-circle it closed to contact at "
                               f"tick {b['at']} after {len(b['cos'])} samples averaging "
                               f"{_fmt(self._mean(b['cos']))} (a contact counts as a "
                               f"chase only if the enemy was moving at the player when "
                               f"it happened)")
                tail = (f"; leg 2, the other half of the circle - {b['ticks']} samples, "
                        f"mean {_fmt(b['align'])}, gap {b['d0']:.1f} -> {b['d1']:.1f}")
                if len(b["cos"]) < self._CHASE_MIN_SAMPLES:
                    return Criterion(
                        cid, q, False,
                        head + tail + f"; fewer than {self._CHASE_MIN_SAMPLES} usable "
                                      f"samples on the second leg")
                # Both terms are read at the CLOSE of each leg: where the enemy had to
                # look to see the player, and where it was actually travelling over its
                # last few ticks. A net displacement over a whole leg averages a turn
                # away and reads as though nothing turned.
                ua, ub = a["want_late"], b["want_late"]
                ha, hb = a["late"], b["late"]
                turn_wanted = 1.0 - _dot(ua, ub) if (ua and ub) else 0.0
                turn_seen = 1.0 - _dot(ha, hb) if (ha and hb) else 0.0
                aligned = ((a["align"] or 0.0) >= self._CHASE_ALIGN
                           and (b["align"] or 0.0) >= self._CHASE_ALIGN)
                turned = turn_seen >= self._CHASE_TURN_SHARE * turn_wanted
                # A turn that was never demanded cannot be evidence either way. Say so
                # rather than passing on a test that did not happen.
                weak = turn_wanted < self._CHASE_TURN_MIN
                note = ("; too small a swing was demanded for the turn to be evidence, "
                        "so only the alignment counted" if weak else "")
                return Criterion(
                    cid, q, aligned and (turned or weak),
                    head + tail + f"; between the close of the two legs the direction "
                                  f"from the enemy to the player swung {turn_wanted:.2f}"
                                  f" and the enemy's own heading swung {turn_seen:.2f} "
                                  f"(needs {self._CHASE_TURN_SHARE * turn_wanted:.2f})"
                                  f"{note}; wants mean >= {self._CHASE_ALIGN} on both "
                                  f"legs")
        except ProbeError as e:
            return unusable_criteria([(cid, self._q(cid))], e, "the chase session")[0]

    @staticmethod
    def _mean(v: list[float]) -> float | None:
        return (sum(v) / len(v)) if v else None

    def _caught(self, leg: dict[str, Any]) -> bool:
        """Contact counts as a chase only if the enemy was closing when it happened.

        The player is manoeuvring around the enemy here, so a collision is not
        self-evidently the enemy's doing - and "the enemy touched the player" is exactly
        the evidence a criterion would accept from a game where the PLAYER did the
        touching.
        """
        m = self._mean(leg["cos"])
        return (len(leg["cos"]) >= self._CHASE_MIN_SAMPLES and m is not None
                and m >= self._CHASE_ALIGN)

    # -- firing ------------------------------------------------------------- #

    def _firing(self, repo, env) -> tuple[Criterion, Criterion, Criterion, Criterion]:
        ids = ("fire.spawns_bullets", "fire.rate_limited", "aim.independent",
               "aim.three_axis")
        try:
            with ProbeSession(repo=repo, env=env, seed=7) as s:
                live, _, note = self._take_control(s)
                if not live:
                    a, b, c, d = (Criterion(x, self._q(x), False, note) for x in ids)
                    return a, b, c, d
                return self._firing_in(s)
        except ProbeError as e:
            a, b, c, d = unusable_criteria([(cid, self._q(cid)) for cid in ids], e,
                                           "the firing session")
            return a, b, c, d

    def _collect(self, s: ProbeSession, ticks: int, seen: set,
                 inputs: dict[str, Any]) -> list[Vec]:
        vels: list[Vec] = []
        for _ in range(ticks):
            t = s.step_raw(dict(inputs))
            for b in _list(t, "bullets"):
                if b.get("id") in seen:
                    continue
                seen.add(b.get("id"))
                vx, vy, vz = _f(b, "vx"), _f(b, "vy"), _f(b, "vz")
                if vx is not None and vy is not None and vz is not None:
                    vels.append((vx, vy, vz))
        return vels

    @staticmethod
    def _shot_ticks(phase: list[Tick], known_ids: set) -> tuple[int, int]:
        """How many of these ticks were SHOOTING ticks, by each of the two signals.

        `fire.rate_limited` asks about the interval between SHOTS, and a shot is a tick
        the game fired on - not a bullet. A weapon that puts a spread of three bullets
        in the world on one tick has taken one shot, and counting bullet ids scored it
        as three.

        Two independent signals say a tick was a shooting tick, and the caller takes the
        LARGER of the two counts:

          - the `fire` event, which the prompt defines as *the player fired a shot this
            tick*. A game may emit it on the rising edge of a held control and report
            one shot for the whole phase - the `edge-vs-level` shape.
          - a bullet id in the snapshot that was not in it before. A game whose spawn
            reaches the snapshot a tick late shifts every one of these off the event
            that caused it, and a game that reports no `id` at all yields at most 1.

        Each can UNDER-report, and under-reporting is the fail-open direction: the
        verdict fails on a HIGH count, so a criterion reading the smaller signal would
        pass a game that fires every tick. Neither over-reports a shot the game did not
        take, except by emitting `fire` on a tick the game's own cooldown refused -
        which contradicts the event's stated meaning, and is this criterion's recorded
        hazard in `judge/bot_mutants.py`.

        `known_ids` is consumed, not copied: pass a set the caller does not need.
        """
        events = spawns = 0
        for t in phase:
            if "fire" in t.events:
                events += 1
            ids = {b.get("id") for b in _list(t, "bullets")}
            if ids - known_ids:
                spawns += 1
            known_ids |= ids
        return events, spawns

    @staticmethod
    def _mean_dir(v: list[Vec]) -> Vec | None:
        if not v:
            return None
        n = len(v)
        return _unit((sum(a[0] for a in v) / n, sum(a[1] for a in v) / n,
                      sum(a[2] for a in v) / n))

    def _firing_in(self, s: ProbeSession
                   ) -> tuple[Criterion, Criterion, Criterion, Criterion]:
        seen = {b.get("id") for b in _list(s.last, "bullets")}
        # MOVE DOWNWARD IN EVERY PHASE. The aim under test is +x, then +y, then +z, and
        # a player parked against the wall it is firing at produces bullets that leave
        # the volume inside the tick they are created and never appear in any snapshot.
        # Measured once as "the game cannot aim upward" on a correct implementation.
        base = _move((0.0, -1.0, 0.0))
        # The phase is read by index rather than as `history[-120:]`: a session with
        # fewer than 120 ticks behind it would silently take the opening await's ticks
        # into the count (`AGENTS.md` rule 12 - the address is an input to the check).
        opening = len(s.history)
        ids_before = set(seen)
        vel_x = self._collect(s, 120, seen, {"fire": True, **base, **_aim((1.0, 0.0, 0.0))})
        evt_ticks, spawn_ticks = self._shot_ticks(s.history[opening:], ids_before)
        shots = max(evt_ticks, spawn_ticks)
        n_x = len(vel_x)
        fire_ok = n_x > 0 and any(_norm(v) > 1.0 for v in vel_x)
        fire_c = Criterion("fire.spawns_bullets", self._q("fire.spawns_bullets"),
                           fire_ok,
                           f"{n_x} bullets created over 120 ticks of holding fire; "
                           f"first velocities {[tuple(round(c, 1) for c in v) for v in vel_x[:3]]}")
        rate_c = Criterion("fire.rate_limited", self._q("fire.rate_limited"),
                           0 < shots <= 80,
                           f"{shots} shooting ticks out of 120 ticks of held fire "
                           f"({evt_ticks} carried a fire event, {spawn_ticks} put a "
                           f"new bullet id in the world), producing {n_x} bullets")

        vel_y = self._collect(s, 120, seen, {"fire": True, **base, **_aim((0.0, 1.0, 0.0))})
        vel_z = self._collect(s, 120, seen, {"fire": True, **base, **_aim((0.0, 0.0, 1.0))})
        dx, dy, dz = (self._mean_dir(vel_x), self._mean_dir(vel_y),
                      self._mean_dir(vel_z))
        indep = (dx is not None and dy is not None
                 and _norm(_sub(dx, dy)) > 0.5)
        aim_c = Criterion(
            "aim.independent", self._q("aim.independent"), indep,
            f"moving -y while aiming +x gave mean bullet direction {dx}; moving -y "
            f"while aiming +y gave {dy}")
        # The depth axis is the new one, and it is the one an implementation ported
        # from the 2D task would quietly drop: aiming along z would then fire along x.
        axis_ok = dz is not None and abs(dz[2]) > 0.7
        axis_c = Criterion(
            "aim.three_axis", self._q("aim.three_axis"), axis_ok,
            f"aiming along +z gave mean bullet direction {dz} (needs the z component "
            f"to dominate)")
        return fire_c, rate_c, aim_c, axis_c

    # -- combat: kills, score, multiplier, waves ---------------------------- #

    def _combat(self, repo, env) -> list[Criterion]:
        """A fresh game where the bot actually plays: aim at the nearest active enemy,
        fire, and back away from it."""
        ids = ("bullets.kill", "score.on_kill", "multiplier.rises", "wave.advances")
        try:
            with ProbeSession(repo=repo, env=env, seed=7,
                              total_timeout_s=1200.0) as s:
                live, _, note = self._take_control(s)
                if not live:
                    return [Criterion(c, self._q(c), False, note) for c in ids]
                kills_evt = 0
                score_pairs: list[tuple[int, int]] = []
                waves_seen: list[int] = [_i(s.last, "wave", 1)]
                mult_seen: list[int] = [_i(s.last, "multiplier", 1)]
                mult_evt = 0
                prev = s.last
                for _ in range(9000):
                    e = _nearest(prev)
                    inputs: dict[str, Any] = {"fire": True}
                    if e is not None:
                        p = _xyz(_player(prev))
                        to_e = _sub(_xyz(e), p)
                        u = _unit(to_e)
                        if u:
                            inputs.update(_aim(u))
                            inputs.update(_move((-u[0], -u[1], -u[2])))  # kite
                    else:
                        inputs.update(_aim((1.0, 0.0, 0.0)))
                    t = s.step_raw(inputs)
                    if "enemy_dead" in t.events:
                        kills_evt += t.events.count("enemy_dead")
                        score_pairs.append((_i(prev, "score"), _i(t, "score")))
                    if "wave_start" in t.events:
                        waves_seen.append(_i(t, "wave", 1))
                    mult_evt += t.events.count("multiplier")
                    mult_seen.append(_i(t, "multiplier", 1))
                    prev = t
                    if t.state.get("game_over") is True:
                        break
                    # Stop once BOTH things that need a long run have happened.
                    if (max(waves_seen) > waves_seen[0] and score_pairs
                            and max(mult_seen) > mult_seen[0]):
                        break
                kills_reported = _i(s.last, "kills")
                detail = (f"{s.ticks_sent} ticks of aim-and-fire: {kills_evt} "
                          f"enemy_dead events, reported kills {kills_reported}, waves "
                          f"{waves_seen}, multiplier range {min(mult_seen)}-"
                          f"{max(mult_seen)} with {mult_evt} multiplier events, score "
                          f"{_i(s.last, 'score')}")
        except ProbeError as e:
            return list(unusable_criteria([(cid, self._q(cid)) for cid in ids], e,
                                          "the combat session"))

        kill_c = Criterion("bullets.kill", self._q("bullets.kill"),
                           kills_evt > 0 and kills_reported > 0, detail)
        score_c = Criterion(
            "score.on_kill", self._q("score.on_kill"),
            bool(score_pairs) and any(b > a for a, b in score_pairs),
            (f"score across kill ticks: {score_pairs[:5]}" if score_pairs
             else "no kill was observed, so the reward could not be measured. " + detail))
        mult_c = Criterion(
            "multiplier.rises", self._q("multiplier.rises"),
            max(mult_seen) > mult_seen[0] and mult_evt > 0,
            f"multiplier went {mult_seen[0]} -> {max(mult_seen)} over {kills_evt} "
            f"kills, with {mult_evt} multiplier events. " + detail)
        wave_c = Criterion("wave.advances", self._q("wave.advances"),
                           max(waves_seen) > min(waves_seen), detail)
        return [kill_c, score_c, mult_c, wave_c]

    # -- the multiplier collapse, and dying --------------------------------- #

    #: HOW MANY TICKS AFTER the damage tick the collapse may still be published. The
    #: criterion reads the damage tick itself and then this many more, so the window is
    #: 9 observations wide and the drop is `_FALL_WINDOW` ticks late at the latest. THE G3
    #: CONTRACT DOES NOT FIX THE TICK, which is why a window exists at all: it says a
    #: multiplier "rises with sustained killing and falls when the player is hit", and
    #: it declares a `multiplier` event meaning "the score multiplier changed". One
    #: sentence governs both halves, and `multiplier.rises` reads its half over
    #: hundreds of ticks by any mechanism - so reading the fall to the exact tick was
    #: an asymmetry the contract does not license. `tasks/159` settled the pong case
    #: the other way and its reason does not carry: `rally` is DEFINED there as a count
    #: of the very events the tick line carries, so a line raising `paddle_hit` with a
    #: rally that excludes it contradicts itself. `multiplier` has no such definition.
    #:
    #: 8 admits the shape that motivates the window - a game that resolves the
    #: collision in one pass and applies the score change in a later one, landing the
    #: drop a tick after the event - and the first step of a ramp that walks the
    #: multiplier down over several ticks. It is 1.7% of the 459 idle ticks the
    #: reference takes to be hit for the first time, over which its multiplier does not
    #: move at all, so a change inside the window is a change around the damage rather
    #: than one on the game's own schedule.
    _FALL_WINDOW = 8

    def _multiplier_falls(self, repo, env) -> Criterion:
        """Raise the multiplier by killing, then stop and let the player be hit.

        Its OWN session, and that separation is load-bearing. Folding this into the
        idle death session meant six thousand ticks of play before the idle phase
        began, and the player was already dead when `player.takes_damage` read its
        starting health: hp 0.0 -> 0.0, zero hits, a false negative on a correct
        reference. A criterion that needs a long set-up must not share a session with
        one that needs a fresh player.

        The set-up is also why this criterion cannot be written the lazy way. Watching
        for a drop without first CAUSING a rise would pass a game whose multiplier
        never moves at all - it would simply never be in a position to fall.

        WHAT IS COMPARED WITH WHAT, and it is not the pair the first version used. The
        baseline is the multiplier on the tick BEFORE the damage, never the peak the
        killing phase reached: hundreds of idle ticks separate the two, and reading the
        stale peak passed any game whose multiplier drifted down during them for a
        reason that had nothing to do with being hit (`tasks/170`). A combo timer is a
        real arcade design and it is the constructed case - `MULT_DECAYS_ON_A_TIMER`
        in `judge/bot_mutants.py` is that game with the damage link taken out, and it
        PASSED the peak-versus-hit-tick reading.

        So the change is a widening in time and a tightening in what it compares, and
        both halves are pinned: `MULT_DEFERS_THE_DROP` is a correct game the old
        reading failed, `MULT_DECAYS_ON_A_TIMER` an incorrect one it passed.
        """
        cid = "multiplier.falls"
        try:
            with ProbeSession(repo=repo, env=env, seed=7,
                              total_timeout_s=1200.0) as s:
                live, _, note = self._take_control(s)
                if not live:
                    return Criterion(cid, self._q(cid), False, note)
                base = _i(s.last, "multiplier", 1)
                mult = base
                prev = s.last
                for _ in range(6000):
                    e = _nearest(prev)
                    inputs: dict[str, Any] = {"fire": True}
                    if e is not None:
                        u = _unit(_sub(_xyz(e), _xyz(_player(prev))))
                        if u:
                            inputs.update(_aim(u))
                            inputs.update(_move((-u[0], -u[1], -u[2])))
                    t = s.step_raw(inputs)
                    mult = _i(t, "multiplier", 1)
                    prev = t
                    if mult > base or t.state.get("game_over") is True:
                        break
                if mult <= base:
                    return Criterion(
                        cid, self._q(cid), False,
                        f"the multiplier never rose above {base} in {s.ticks_sent} "
                        f"ticks of play, so its collapse on damage could not be "
                        f"established")
                peak = mult
                # Idle until the first hit, carrying the multiplier forward tick by
                # tick. `before` ends up holding the value the tick BEFORE the hit.
                before = peak
                drifted = 0
                hit = None
                for _ in range(4000):
                    t = s.step_raw({})
                    if "player_hit" in t.events:
                        hit = t
                        break
                    if t.state.get("game_over") is True:
                        break
                    m = _i(t, "multiplier", 1)
                    if m != before:
                        drifted += 1
                    before = m
                drift = (f"; it moved {drifted} time(s) on its own while idling"
                         if drifted else "")
                if hit is None:
                    return Criterion(
                        cid, self._q(cid), False,
                        f"the multiplier reached {peak} but the player was never hit "
                        f"in the {s.ticks_sent} ticks that followed, so the drop could "
                        f"not be measured")
                if before <= base:
                    return Criterion(
                        cid, self._q(cid), False,
                        f"the multiplier peaked at {peak} and was already back to "
                        f"{before} on the tick before the first hit, so it had nothing "
                        f"left to lose to the damage{drift}")
                after, fell_at, ended = _i(hit, "multiplier", 1), 0, False
                while after == before and fell_at < self._FALL_WINDOW:
                    t = s.step_raw({})
                    fell_at += 1
                    after = _i(t, "multiplier", 1)
                    if t.state.get("game_over") is True:
                        ended = True
                        break
                lead = f"multiplier was {before} on the tick before damage; "
                if after == before:
                    # `fell_at`, never the window width: the game may have ended inside
                    # it, and a sentence naming ticks nobody stepped is a false one.
                    return Criterion(
                        cid, self._q(cid), False,
                        f"{lead}{fell_at} tick(s) after the first hit it still read "
                        f"{after}" + (" and the game was over" if ended else "") + drift)
                when = ("on the tick of the first hit" if fell_at == 0
                        else f"{fell_at} tick(s) after the first hit")
                return Criterion(
                    cid, self._q(cid), after < before,
                    f"{lead}{when} it read {after}{drift}")
        except ProbeError as e:
            return unusable_criteria([(cid, self._q(cid))], e,
                                     "the multiplier session")[0]

    def _death(self, repo, env) -> list[Criterion]:
        """Stand still and never fire, from a fresh game: the player is worn down."""
        ids = ("player.takes_damage", "gameover.triggers")
        try:
            with ProbeSession(repo=repo, env=env, seed=7,
                              total_timeout_s=900.0) as s:
                live, _, note = self._take_control(s)
                if not live:
                    return [Criterion(c, self._q(c), False, note) for c in ids]
                hp0 = _f(_player(s.last), "hp", 0.0) or 0.0
                hits = 0
                over_at = None
                for _ in range(9000):
                    t = s.step_raw({})
                    hits += t.events.count("player_hit")
                    if t.state.get("game_over") is True or "game_over" in t.events:
                        over_at = t.tick
                        break
                hp1 = _f(_player(s.last), "hp", 0.0) or 0.0
                dmg_c = Criterion(
                    "player.takes_damage", self._q("player.takes_damage"),
                    hits > 0 and hp1 < hp0,
                    f"standing still for {s.ticks_sent} ticks: {hits} player_hit "
                    f"events, hp {hp0} -> {hp1}")
                if over_at is None:
                    return [dmg_c, Criterion(
                        "gameover.triggers", self._q("gameover.triggers"), False,
                        f"the player never died in {s.ticks_sent} idle ticks "
                        f"(hp {hp1})")]
                # IDLE FIRST, THEN PRESS AND READ THROUGH THE RESET -
                # `probe.end_condition_holds` holds the reason, and holds it once for
                # all four bots. This loop used to press fire, aim and move straight
                # away, which pressed the restart control of a correct game that clears
                # its game-over card on any input, and then scored the fresh run's live
                # state as a failure to end (`tasks/157`).
                end = end_condition_holds(
                    s, idle_ticks=300, press_ticks=300,
                    inputs={"fire": True, **_aim((1.0, 0.0, 0.0)),
                            **_move((-1.0, 0.0, 0.0))},
                    # KILLS AS WELL AS SCORE. The score alone cannot express this game
                    # ending and carrying on: with the player dead there is nobody to
                    # earn points, so a simulation that keeps stepping leaves it at
                    # whatever it was. `kills` moves - measured on a reference with the
                    # step function's `game_over` early-out deleted, the last enemy dies
                    # inside the idle window - and both come back to their tick-0 values
                    # on a reset, which is what the pressed phase reads them against.
                    sample=lambda t: (_i(t, "score"), _i(t, "kills")))
                return [dmg_c, Criterion(
                    "gameover.triggers", self._q("gameover.triggers"), end.passed,
                    f"game over at tick {over_at}; {end.detail('(score, kills)')}")]
        except ProbeError as e:
            return list(unusable_criteria([(cid, self._q(cid)) for cid in ids], e,
                                          "the death session"))


BOT = ArenaBot()
