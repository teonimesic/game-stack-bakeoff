#!/usr/bin/env python3
"""Scripted play-bot for the 2D sprite platformer task.

Design and rationale: `eval/G4-PLATFORMER.md`. Three criteria are genre-defining and
none can be settled from a screenshot:

* `attack.active_frames` - the weapon damages during PART of the swing. A hitbox that
  is always on and one with a real active window are pixel-identical in a still.
* `attack.faces` - the hitbox is on the side the character faces, and flips when it
  turns. Asserted against `facing`, not against which enemies happened to die.
* `invuln.window` - being hit grants a window in which it cannot happen again. Without
  it, standing in an enemy drains health every tick; with it, once per window. The
  criterion counts hits per tick in contact, so it measures the WINDOW and not the
  size of the health pool.

EVERY CRITERION HERE ESTABLISHES ITS CONDITION AND THEN MEASURES. The bot walks to a
ledge it located in `platforms` rather than waiting to fall; it walks to an enemy it
located in `enemies` rather than waiting to be hit. Sixteen false negatives in this
project came from criteria that idled and hoped (FINDINGS #29, #34).

THE TITLE CARD. The reference holds control for 96 ticks so an opening card can be
read, and the task explicitly asks for presentation. Nothing here measures from tick 0:
`_take_control` steps until the player actually answers an input, which is the property
in its own name rather than a fixed delay or a proxy for one (FINDINGS #34).
"""

from __future__ import annotations

from typing import Any

from checks import determinism_criteria, idle_tape
from probe import (Bot, Criterion, ProbeError, ProbeSession, Tick,
                   unusable_criteria)


def _player(t: Tick) -> dict[str, Any]:
    p = t.state.get("player")
    return p if isinstance(p, dict) else {}


def _attack(t: Tick) -> dict[str, Any]:
    a = t.state.get("attack")
    return a if isinstance(a, dict) else {}


def _hitbox(t: Tick) -> dict[str, Any]:
    h = _attack(t).get("hitbox")
    return h if isinstance(h, dict) else {}


def _list(t: Tick, key: str) -> list[dict[str, Any]]:
    v = t.state.get(key)
    return [e for e in v if isinstance(e, dict)] if isinstance(v, list) else []


def _f(d: dict[str, Any], k: str, default: float | None = None) -> float | None:
    try:
        v = float(d[k])
    except (KeyError, TypeError, ValueError):
        return default
    return v if v == v and abs(v) != float("inf") else default


def _i(t: Tick, key: str, default: int = 0) -> int:
    try:
        return int(t.state.get(key, default))
    except (TypeError, ValueError):
        return default


def _px(t: Tick) -> float:
    return _f(_player(t), "x", 0.0) or 0.0


def _py(t: Tick) -> float:
    return _f(_player(t), "y", 0.0) or 0.0


def _hp(t: Tick) -> float:
    return _f(_player(t), "hp", 0.0) or 0.0


class PlatformerBot(Bot):
    #: A representative run: walk, jump and swing at a natural cadence so that pacing
    #: is a property of the level rather than of the criteria drive (FINDINGS #52).
    play_ticks = 3000
    game = "g4_platformer"
    #: `stage.completes` needs the bot to TRAVERSE an unknown level layout, which is the
    #: `layer.clears` situation exactly (RUBRIC.md): a criterion the instrument cannot
    #: satisfy on correct work manufactures a false negative for every honest
    #: submission. Measured, reported, excluded from the denominator. To promote it,
    #: show it passing against at least three deliberately awkward reference levels -
    #: not by argument.
    diagnostic_only = frozenset({"stage.completes"})

    #: The criterion that checks THIS GAME'S END CONDITION, whatever it is called.
    #: Named explicitly because the concept has two spellings across the suite:
    #: `gameover.triggers` in three games and `match.ends` in pong, where the player's health reaches zero.
    #: A cross-game audit asking "does every game verify its own end condition?"
    #: would grep for `gameover` and report a false gap for pong - a mechanical sweep
    #: reporting something untrue, which this project has lost time to before (#38).
    #: Read this attribute instead of guessing from the id.
    end_condition = "gameover.triggers"

    criteria = [
        ("state.shape", "Does the probe report the contracted state shape (level, "
                        "player with grounded/facing/anim, attack with a hitbox, "
                        "platforms, enemies, score, game_over, victory)?"),
        ("player.walks", "Does holding a movement control walk the character, and set "
                         "its facing?"),
        ("player.bounded", "Does the character stop at the edge of the stage?"),
        ("player.falls", "Does walking off a ledge make the character fall?"),
        ("platform.lands", "Does falling onto a platform stop the fall and ground the "
                           "character?"),
        ("jump.leaves_ground", "Does jumping from the ground raise the character off "
                               "it?"),
        ("jump.grounded_only", "Is jumping refused in mid-air — does holding jump fail "
                               "to jump again before landing?"),
        ("attack.active_frames", "Does the swing damage for PART of its duration "
                                 "rather than permanently or not at all?"),
        ("attack.faces", "Is the hitbox on the side the character faces, and does it "
                         "flip when the character turns?"),
        ("attack.damages", "Does the swing damage an enemy it reaches?"),
        ("enemy.damages_player", "Does touching an enemy cost the player health?"),
        ("invuln.window", "Is there a window after being hit during which the player "
                          "cannot be hit again?"),
        ("knockback.applied", "Is the player knocked away from whatever hurt them?"),
        ("anim.states", "Does the reported animation distinguish standing, walking, "
                        "being airborne and swinging?"),
        ("anim.frames_advance", "Does the animation frame index advance and cycle "
                                "while walking?"),
        ("score.on_kill", "Does destroying an enemy raise the score?"),
        ("gameover.triggers", "Does the game end at zero health and stop accepting "
                              "play?"),
        ("stage.completes", "Can the stage be finished — does reaching the goal set "
                            "victory and stop play? (DIAGNOSTIC, not scored)"),
        ("determinism.replay", "Does replaying the same seed and the same inputs "
                               "reproduce the same state hash at every tick?"),
        ("determinism.seed", "Do two different seeds produce different runs?"),
    ]

    # ------------------------------------------------------------------ #

    _CONTROL_TICKS = 512          #: title card, countdown and a pause all fit inside
    _WALK_TICKS = 40

    def _q(self, cid: str) -> str:
        return next(q for c, q in self.criteria if c == cid)

    @staticmethod
    def _take_control(s: ProbeSession) -> tuple[bool, int, str]:
        """Step until the character actually answers an input.

        Not a fixed delay and not a flag: the property is "the game accepts input", so
        that is what is measured. A submission with a 96-tick title card, a countdown
        and a "press any key" screen all pass through here identically.
        """
        x0 = _px(s.last)
        for i in range(PlatformerBot._CONTROL_TICKS):
            t = s.step_raw({"move_right": True})
            if abs(_px(t) - x0) > 1.0:
                return True, i + 1, (f"the character answered input after {i + 1} "
                                     f"ticks (x {x0:.1f} -> {_px(t):.1f})")
        return False, PlatformerBot._CONTROL_TICKS, (
            f"the character never answered a movement input in "
            f"{PlatformerBot._CONTROL_TICKS} ticks (x stayed at {x0:.1f})")

    def play_inputs(self, tick: Tick) -> dict[str, Any]:
        """Walk right, jump periodically, swing periodically."""
        c = tick.tick % 96
        out: dict[str, Any] = {"move_right": True} if c < 72 else {"move_left": True}
        if c % 32 == 8:
            out["jump"] = True
        if c % 24 == 16:
            out["attack"] = True
        return out

    def run(self, s: ProbeSession) -> list[Criterion]:
        out: list[Criterion] = []
        add = out.append
        t0 = s.last
        p0 = _player(t0)
        lvl = t0.state.get("level")
        atk = _attack(t0)

        shape_ok = (
            isinstance(lvl, dict) and _f(lvl, "w") is not None
            and _f(lvl, "goal_x") is not None
            and _f(p0, "x") is not None and _f(p0, "y") is not None
            and isinstance(p0.get("grounded"), bool)
            and isinstance(p0.get("facing"), (int, float))
            and isinstance(p0.get("anim"), str)
            and isinstance(p0.get("anim_frame"), (int, float))
            and isinstance(p0.get("hp"), (int, float))
            and isinstance(atk.get("active"), bool)
            and isinstance(_hitbox(t0).get("w"), (int, float))
            and isinstance(t0.state.get("platforms"), list)
            and isinstance(t0.state.get("enemies"), list)
            and isinstance(t0.state.get("game_over"), bool)
            and isinstance(t0.state.get("victory"), bool)
        )
        add(Criterion("state.shape", self._q("state.shape"), shape_ok,
                      f"tick 0 state keys: {sorted(t0.state)}; player keys: "
                      f"{sorted(p0)}; attack keys: {sorted(atk)}"))
        if not shape_ok:
            for cid, q in self.criteria[1:]:
                add(Criterion(cid, q, False, "state shape contract not met",
                              cid not in self.diagnostic_only))
            return out

        live, ticks, note = self._take_control(s)
        if not live:
            for cid, q in self.criteria[1:]:
                add(Criterion(cid, q, False, note, cid not in self.diagnostic_only))
            return out

        add(self._walks(s, note))
        add(self._anim_frames(s))
        add(self._anim_states(s))

        # Everything below opens a SIBLING session, which closes `s` (FINDINGS #29/#30).
        repo, env = s.repo, s.env
        for c in self._falling(repo, env):
            add(c)
        for c in self._jumping(repo, env):
            add(c)
        for c in self._swing(repo, env):
            add(c)
        for c in self._combat(repo, env):
            add(c)
        for c in self._hurt(repo, env):
            add(c)
        add(self._bounded(repo, env))
        add(self._stage(repo, env))
        out.extend(determinism_criteria(repo, idle_tape(300), env=env))
        return out

    # -- walking and the animation state machine --------------------------- #

    def _walks(self, s: ProbeSession, note: str) -> Criterion:
        x0 = _px(s.last)
        for _ in range(self._WALK_TICKS):
            s.step_raw({"move_right": True})
        t_right = s.last
        x1, face_r = _px(t_right), _f(_player(t_right), "facing", 0.0)
        for _ in range(self._WALK_TICKS * 2):
            s.step_raw({"move_left": True})
        t_left = s.last
        x2, face_l = _px(t_left), _f(_player(t_left), "facing", 0.0)
        ok = (x1 - x0 > 2.0 and x2 < x1 - 2.0
              and face_r is not None and face_l is not None
              and face_r > 0 > face_l)
        return Criterion("player.walks", self._q("player.walks"), ok,
                         f"{note}; x {x0:.1f} -> {x1:.1f} holding right (facing "
                         f"{face_r}) -> {x2:.1f} holding left (facing {face_l})")

    def _anim_frames(self, s: ProbeSession) -> Criterion:
        frames: list[float] = []
        for _ in range(90):
            t = s.step_raw({"move_right": True})
            f = _f(_player(t), "anim_frame")
            if f is not None:
                frames.append(f)
        distinct = sorted(set(frames))
        cycled = len(frames) > 0 and frames.count(frames[0]) >= 2
        return Criterion("anim.frames_advance", self._q("anim.frames_advance"),
                         len(distinct) >= 2 and cycled,
                         f"anim_frame over 90 ticks of walking took values {distinct} "
                         f"and returned to its first value: {cycled}")

    def _anim_states(self, s: ProbeSession) -> Criterion:
        """Drive four distinct activities and require the labels to differ.

        Not "does `anim` ever change" - a game that flickers between two labels for one
        activity would pass that. Each activity is driven separately and its label
        recorded, so the criterion asks whether the STATE MACHINE distinguishes them.
        """
        seen: dict[str, str] = {}

        def settle(limit: int = 240) -> bool:
            """Wait until the character is standing on something.

            ESTABLISH, do not assume. The first version sampled "walk" while the
            character was still falling off the ledge an earlier criterion had walked
            it over, and read `jump` for both the walking and the airborne label. It
            passed - three distinct labels were still seen - which is worse than
            failing: a criterion that passes for the wrong reason measures nothing.
            """
            for _ in range(limit):
                if _player(s.last).get("grounded") is True:
                    return True
                s.step_raw({})
            return False

        def label(name: str, ticks: int, **inputs: Any) -> None:
            for _ in range(ticks):
                s.step_raw(dict(inputs))
            a = _player(s.last).get("anim")
            if isinstance(a, str):
                seen[name] = a

        def label_grounded(name: str, limit: int = 400, **inputs: Any) -> None:
            """Hold `inputs` until the character is BOTH grounded and answering, then
            read the label. Sampling blind read `jump` for the walking label, because
            the character had walked into an enemy and been knocked into the air - a
            true reading of the wrong moment. The criterion still passed, which is the
            failure worth avoiding."""
            for _ in range(limit):
                t = s.step_raw(dict(inputs))
                if _player(t).get("grounded") is True:
                    a = _player(t).get("anim")
                    if isinstance(a, str):
                        seen[name] = a
                    return
            a = _player(s.last).get("anim")
            if isinstance(a, str):
                seen[name] = a

        grounded = settle()
        label_grounded("idle", 200)
        label_grounded("walk", 400, move_right=True)
        label("air", 6, jump=True)
        settle()
        label("attack", 2, attack=True)
        distinct = set(seen.values())
        return Criterion("anim.states", self._q("anim.states"), len(distinct) >= 3,
                         f"animation reported per activity: {seen} "
                         f"({len(distinct)} distinct, wants at least 3; the character "
                         f"was successfully grounded before sampling: {grounded})")

    # -- falling and landing ------------------------------------------------ #

    @staticmethod
    def _ledge_x(t: Tick) -> float | None:
        """The right edge of the platform the character is standing on.

        Derived from `platforms`, which is why the contract carries them: without it
        this criterion would have to walk right and hope, which is the defect
        `ball.wall_bounce` and `enemies.chase` were both repaired out of.
        """
        px, py = _px(t), _py(t)
        best = None
        for p in _list(t, "platforms"):
            x, y = _f(p, "x"), _f(p, "y")
            w, h = _f(p, "w"), _f(p, "h")
            if None in (x, y, w, h):
                continue
            top = y + h / 2.0
            if abs(px - x) <= w / 2.0 + 4.0 and -4.0 <= py - top <= 80.0:
                right = x + w / 2.0
                if best is None or right < best:
                    best = right
        return best

    def _falling(self, repo, env) -> list[Criterion]:
        """`player.falls` walks off a located ledge. `platform.lands` does NOT reuse
        that fall, and the distinction is the whole repair.

        Walking off the first ledge establishes a FALL. It does not establish a fall
        ONTO A PLATFORM, because whether anything is underneath is level layout the bot
        has no knowledge of - and in a designed platformer the far side of the opening
        ledge is usually a pit, which is the point of it. Measured on `wg-g4c`: five of
        six submissions fell to y=-68..-136, straight past the stage floor, and were
        marked as having no landing collision. The sixth passed because its gap
        happened to have a floor eight units down.

        That is the `stage.completes` argument exactly - a criterion the instrument
        cannot satisfy on correct work manufactures a false negative for every honest
        submission - and it sat three lines below the docstring asserting that EVERY
        criterion here establishes its condition. The general claim is what stopped
        anyone checking the one member that did not.

        So the landing is now CONSTRUCTED: jump from the platform underfoot and assert
        that the descent ends on it. That is a fall onto a platform in the criterion's
        own words, and it is constructible on EVERY correct game without knowing
        anything about the level.

        The rejected alternative is worth recording, because it is the more obvious one
        and it is wrong: locate a lower platform in `platforms` and walk off aiming at
        it. A lower platform that is AHEAD can still be on the far side of the gap, so
        walking off lands in the pit and the criterion fails on a correct game exactly
        as before - the same hope, wearing the vocabulary of establishment. A condition
        is only established when the bot can bring it about unilaterally.
        """
        ids = ("player.falls", "platform.lands")
        try:
            with ProbeSession(repo=repo, env=env, seed=7) as s:
                live, _, note = self._take_control(s)
                if not live:
                    return [Criterion(c, self._q(c), False, note) for c in ids]
                edge = self._ledge_x(s.last)
                y_start = _py(s.last)
                fell_at = None
                low = y_start
                for i in range(600):
                    t = s.step_raw({"move_right": True})
                    y = _py(t)
                    low = min(low, y)
                    # DESCENT, not "grounded went False". The mutant that sets gravity
                    # to zero leaves the character hanging in the air off the end of the
                    # ledge: it is not grounded, it has not fallen, and reading the flag
                    # passed it. `player.falls` names a change in HEIGHT, so height is
                    # what is asserted (FINDINGS #34 - assert the property in its own
                    # name; a proxy passes every control built from the same assumption).
                    if fell_at is None and y < y_start - 2.0:
                        fell_at = t.tick
                        break
                falls = Criterion(
                    "player.falls", self._q("player.falls"), fell_at is not None,
                    f"walked right from y={y_start:.1f}"
                    + (f" (platform edge at x={edge:.1f})" if edge is not None else "")
                    + (f"; began descending at tick {fell_at}, lowest y {low:.1f}"
                       if fell_at is not None
                       else f"; never lost height in 600 ticks, lowest y {low:.1f} "
                            f"(grounded={_player(s.last).get('grounded')})"))
                return [falls, self._lands(repo, env)]
        except ProbeError as e:
            return list(unusable_criteria([(c, self._q(c)) for c in ids], e,
                                          "the falling session"))

    def _lands(self, repo, env) -> Criterion:
        """Fall onto a platform ON PURPOSE, then assert the fall stopped there."""
        cid = "platform.lands"
        try:
            with ProbeSession(repo=repo, env=env, seed=7) as s:
                live, _, note = self._take_control(s)
                if not live:
                    return Criterion(cid, self._q(cid), False, note)

                y_ground = _py(s.last)
                how = (f"jumped from the platform underfoot at y={y_ground:.1f} and "
                       f"rode the descent back down onto it")
                # Leave the ground. Holding jump for a bounded number of ticks rather
                # than one: a submission may require the press to be held, or may take
                # a frame to apply the impulse.
                apex = y_ground
                left = False
                for _ in range(30):
                    t = s.step_raw({"jump": True})
                    apex = max(apex, _py(t))
                    if _player(t).get("grounded") is False:
                        left = True
                        break
                if not left:
                    return Criterion(
                        cid, self._q(cid), False,
                        f"{how}; the character never left the ground, so no fall onto "
                        f"a platform could be staged (grounded stayed "
                        f"{_player(s.last).get('grounded')}, y={_py(s.last):.1f}) - "
                        f"this is a jump failure, not a landing failure")
                landed = None
                for _ in range(600):
                    t = s.step_raw({})
                    apex = max(apex, _py(t))
                    # Grounded AND below the apex: returning to ground after rising.
                    if _player(t).get("grounded") is True and _py(t) < apex - 2.0:
                        landed = t
                        break

                if landed is None:
                    return Criterion(cid, self._q(cid), False,
                                     f"{how}; the character never became grounded again "
                                     f"after descending (final y={_py(s.last):.1f}, "
                                     f"apex y={apex:.1f}, grounded="
                                     f"{_player(s.last).get('grounded')})")
                # Grounded is a flag; RESTING is the property. Assert the height stops
                # changing, so a submission that reports grounded while still sinking
                # cannot pass on the flag alone.
                after = [_py(s.step_raw({})) for _ in range(20)]
                settled = bool(after) and max(after) - min(after) < 1.0
                return Criterion(
                    cid, self._q(cid), settled,
                    f"{how}; landed at tick {landed.tick}, y={_py(landed):.1f}, and y "
                    f"varied by {(max(after) - min(after)):.3f} over the next 20 ticks"
                    + ("" if settled else " - grounded was reported but the character "
                                          "did not come to rest"))
        except ProbeError as e:
            return next(iter(unusable_criteria([(cid, self._q(cid))], e,
                                               "the landing session")))

    # -- jumping ------------------------------------------------------------ #

    def _jumping(self, repo, env) -> list[Criterion]:
        ids = ("jump.leaves_ground", "jump.grounded_only")
        try:
            with ProbeSession(repo=repo, env=env, seed=7) as s:
                live, _, note = self._take_control(s)
                if not live:
                    return [Criterion(c, self._q(c), False, note) for c in ids]
                # settle: stop walking so the character is standing on something
                for _ in range(20):
                    s.step_raw({})
                y0 = _py(s.last)
                grounded0 = _player(s.last).get("grounded")
                rose = 0.0
                jump_evt = 0
                for _ in range(8):
                    t = s.step_raw({"jump": True})
                    jump_evt += t.events.count("jump")
                    rose = max(rose, _py(t) - y0)
                left = _player(s.last).get("grounded") is False
                leaves = Criterion(
                    "jump.leaves_ground", self._q("jump.leaves_ground"),
                    rose > 2.0 and left,
                    f"standing at y={y0:.1f} (grounded={grounded0}); after 8 ticks of "
                    f"jump the character rose {rose:.1f} and grounded={not left and 'True' or 'False'}"
                    f", jump events {jump_evt}")

                # HOLD jump continuously. A game that allows a mid-air jump never comes
                # down; one that refuses it lands, and may hop again from the ground.
                airborne_jumps = 0
                landings = 0
                grounded_prev = False
                for _ in range(300):
                    t = s.step_raw({"jump": True})
                    g_now = _player(t).get("grounded") is True
                    if "jump" in t.events and not grounded_prev:
                        airborne_jumps += 1
                    if g_now and not grounded_prev:
                        landings += 1
                    grounded_prev = g_now
                only = Criterion(
                    "jump.grounded_only", self._q("jump.grounded_only"),
                    landings >= 1 and airborne_jumps == 0,
                    f"holding jump for 300 ticks: {landings} landings and "
                    f"{airborne_jumps} jumps raised while airborne (wants at least one "
                    f"landing and no airborne jump)")
                return [leaves, only]
        except ProbeError as e:
            return list(unusable_criteria([(c, self._q(c)) for c in ids], e,
                                          "the jumping session"))

    # -- the swing ---------------------------------------------------------- #

    @staticmethod
    def _live_hitbox_x(t: Tick) -> float | None:
        """The hitbox centre, but ONLY on ticks where a hitbox actually exists.

        `active` and `hitbox` answer different questions, and conflating them cost a
        correct submission a criterion. `attack.active_frames` REQUIRES the damaging
        window to be shorter than the swing, so on a submission that implements it
        properly there are ticks where the swing is active and the hitbox is empty. An
        empty rectangle reports centre (0, 0) - and (0, 0) is a perfectly plausible
        position, so reading it as one produced `hitbox centre relative to the character:
        facing right [-61.7, -61.7, -61.7]` on `g4_platformer__unity__t0`, which is not a
        hitbox on the wrong side but the origin, minus the player's x.

        The submission had written the distinction down, in its own probe:

            `active` means a swing is in progress. `hitbox` is only the rectangle that
            damages THIS TICK, so it is empty during the wind-up and the follow-through.

        Rule 11, one level out: the subject documented the mechanism and the grader did
        not read it. So the width is checked, and a degenerate box is skipped rather than
        having its sentinel centre treated as a measurement.
        """
        hb = _hitbox(t)
        w = _f(hb, "w")
        h = _f(hb, "h")
        if (w is not None and w <= 0.0) or (h is not None and h <= 0.0):
            return None
        return _f(hb, "x")

    def _swing(self, repo, env) -> list[Criterion]:
        ids = ("attack.active_frames", "attack.faces")
        try:
            with ProbeSession(repo=repo, env=env, seed=7) as s:
                live, _, note = self._take_control(s)
                if not live:
                    return [Criterion(c, self._q(c), False, note) for c in ids]
                for _ in range(20):
                    s.step_raw({})

                # ONE press, then watch. Holding attack would confuse "the hitbox never
                # turns off" with "a new swing started every tick".
                active: list[bool] = []
                right_side: list[float] = []
                s.step_raw({"attack": True})
                for _ in range(180):
                    t = s.step_raw({})
                    on = _attack(t).get("active") is True
                    active.append(on)
                    if on:
                        hx = self._live_hitbox_x(t)
                        if hx is not None:
                            right_side.append(hx - _px(t))
                n_on = sum(active)
                frames = Criterion(
                    "attack.active_frames", self._q("attack.active_frames"),
                    0 < n_on < len(active),
                    f"after one press, the hitbox was active on {n_on} of the next "
                    f"{len(active)} ticks (wants more than 0 and fewer than all)")

                # Turn around and swing again. The hitbox must follow `facing`.
                for _ in range(60):
                    s.step_raw({})
                for _ in range(30):
                    s.step_raw({"move_left": True})
                face_l = _f(_player(s.last), "facing", 0.0)
                left_side: list[float] = []
                s.step_raw({"attack": True})
                for _ in range(180):
                    t = s.step_raw({})
                    if _attack(t).get("active") is True:
                        hx = self._live_hitbox_x(t)
                        if hx is not None:
                            left_side.append(hx - _px(t))
                ok_faces = (bool(right_side) and bool(left_side)
                            and min(right_side) > 0.0 and max(left_side) < 0.0
                            and face_l is not None and face_l < 0)
                faces = Criterion(
                    "attack.faces", self._q("attack.faces"), ok_faces,
                    f"hitbox centre relative to the character: facing right "
                    f"{[round(v, 1) for v in right_side[:3]]}, then after turning "
                    f"(facing={face_l}) {[round(v, 1) for v in left_side[:3]]}")
                return [frames, faces]
        except ProbeError as e:
            return list(unusable_criteria([(c, self._q(c)) for c in ids], e,
                                          "the swing session"))

    # -- reaching an enemy, killing it, scoring ----------------------------- #

    #: How far above or below the character an enemy may be and still count as reachable
    #: by walking and swinging. A little over one jump.
    _REACH_DY = 40.0

    @staticmethod
    def _nearest(t: Tick) -> dict[str, Any] | None:
        """The nearest enemy AT A HEIGHT THE CHARACTER CAN HIT, falling back to any.

        THE DEFECT THIS REPAIRS, and it is not the one anyone predicted. This ranked
        enemies by horizontal distance alone. On a level with platforms at several
        heights that picks an enemy standing 80 units up on a ledge, and the bot then
        walks underneath it and swings at nothing for the rest of the session.

        Measured on `g4_platformer__ts__t0` (`wg-g4c-2026-08-21`): player at y=17, nearest
        by x is enemy 16 at x=174 **y=97**, while enemy 15 sits at x=357 **y=13** - same
        height, plainly walkable. The bot chose the unreachable one and reported
        "3002 ticks of walk-and-swing: 0 enemy_hit". Six combat criteria failed on a
        submission that works.

        The failure was blamed on the level's PITS, by two people, because the same
        submission also has gaps in its ground and the evidence string mentions a
        position inside one. **The gaps were real and were not the cause** - the target
        was on the same ground segment, 133 units away, the whole time.

        Fall back to nearest-by-x when nothing is at a reachable height, so a level whose
        enemies are all on ledges still produces a measurement rather than None.
        """
        px, py = _px(t), _py(t)
        best, bd = None, float("inf")
        any_best, any_bd = None, float("inf")
        for e in _list(t, "enemies"):
            x, y = _f(e, "x"), _f(e, "y")
            if x is None:
                continue
            d = abs(x - px)
            if d < any_bd:
                any_best, any_bd = e, d
            if y is not None and abs(y - py) > PlatformerBot._REACH_DY:
                continue
            if d < bd:
                best, bd = e, d
        return best if best is not None else any_best

    @staticmethod
    def _edge_distance(t: Tick, moving_right: bool) -> float | None:
        """How far ahead the ground under the character ends, or None if unknown.

        Derived from `platforms`, like `_ledge_x`, because the alternative is to walk
        forward and find out by dying - which is exactly what this repairs.
        """
        px, py = _px(t), _py(t)
        best = None
        for p in _list(t, "platforms"):
            x, y = _f(p, "x"), _f(p, "y")
            w, h = _f(p, "w"), _f(p, "h")
            if None in (x, y, w, h):
                continue
            top = y + h / 2.0
            # the surface the character is standing on, within a small tolerance
            if not (-6.0 <= py - top <= 80.0):
                continue
            if not (x - w / 2.0 - 4.0 <= px <= x + w / 2.0 + 4.0):
                continue
            edge = (x + w / 2.0) if moving_right else (x - w / 2.0)
            d = (edge - px) if moving_right else (px - edge)
            if best is None or d < best:
                best = d
        return best

    #: How close to the edge of the ground to start a crossing jump.
    #:
    #: MEASURED, and the first value was wrong in the direction that looks safe. At 48.0
    #: the bot jumps early, spends its airtime over solid ground and lands in the gap:
    #: on `g4_platformer__unity__t0` (`wg-g4c-2026-08-21`), whose ground ends at x=300 and
    #: resumes at x=378.5, it reached x=366.6 and lost 4 of 5 hp to repeated falls. At
    #: 24.0, 12.0 and 6.0 it clears the same 78.5-unit gap and arrives with FULL health.
    #:
    #: Set to 20.0: inside the measured working band with margin, and far enough from the
    #: edge that a character moving ~3 units per tick still gets several ticks of warning.
    #: **Jumping earlier is not safer.** A margin intuitively reads as caution, and here it
    #: spent the only resource that mattered - horizontal distance remaining - before the
    #: obstacle began.
    _EDGE_JUMP_WITHIN = 20.0

    def _approach(self, s: ProbeSession, stop_at: float, ticks: int,
                  attack: bool) -> dict[str, Any] | None:
        """Walk toward the nearest enemy, JUMPING GAPS and jumping when progress stalls.

        THE DEFECT THIS REPAIRS, measured on `wg-g4c-2026-08-21`. The bot reached every
        enemy by walking, so a level whose ground has pits stopped it: it walked into the
        first gap and died, and six combat criteria failed on submissions that worked.
        `g4_platformer__ts__t0` has pits at x 520-600, 1080-1180, 1700-1790 and its own
        evidence reads "reached x=588.8" - inside the first one. It scored the field's
        lowest. `g4_platformer__unity__t0` is the same, on a level whose source says
        "Six pits to clear".

        **The penalty was indexed to how good the level was**: a submission that builds
        real platforming lost criteria that a flat corridor scores full marks on. That is
        not a measurement error, it is a measurement that rewards the wrong thing.

        The stall detector already here does not help - falling into a pit is not a stall,
        because x keeps changing all the way down. The gap has to be seen BEFORE it is
        entered, which is what `_edge_distance` is for (FINDINGS #65: establish the
        condition, never walk forward and hope).
        """
        last_x = _px(s.last)
        stalled = 0
        for i in range(ticks):
            e = self._nearest(s.last)
            if e is None:
                return None
            ex = _f(e, "x")
            px = _px(s.last)
            if ex is None:
                return None
            gap = ex - px
            inputs: dict[str, Any] = {}
            if abs(gap) > stop_at:
                inputs["move_right" if gap > 0 else "move_left"] = True
            if attack and abs(gap) <= stop_at * 1.6:
                inputs["attack"] = True
            moving = "move_right" in inputs or "move_left" in inputs
            if moving and _player(s.last).get("grounded") is True:
                d = self._edge_distance(s.last, gap > 0)
                if d is not None and d <= self._EDGE_JUMP_WITHIN:
                    inputs["jump"] = True
            if stalled > 20:
                inputs["jump"] = True
                stalled = 0
            t = s.step_raw(inputs)
            if abs(_px(t) - last_x) < 0.5 and abs(gap) > stop_at:
                stalled += 1
            else:
                stalled = 0
            last_x = _px(t)
            if t.state.get("game_over") is True:
                return None
        return self._nearest(s.last)

    def _combat(self, repo, env) -> list[Criterion]:
        ids = ("attack.damages", "score.on_kill")
        try:
            with ProbeSession(repo=repo, env=env, seed=7,
                              total_timeout_s=900.0) as s:
                live, _, note = self._take_control(s)
                if not live:
                    return [Criterion(c, self._q(c), False, note) for c in ids]
                target = self._nearest(s.last)
                tid = target.get("id") if target else None
                hp_before = _f(target, "hp") if target else None
                hits = 0
                deaths = 0
                score_pairs: list[tuple[int, int]] = []
                prev = s.last
                for _ in range(3000):
                    e = self._nearest(prev)
                    inputs: dict[str, Any] = {"attack": True}
                    if e is not None:
                        gap = (_f(e, "x") or 0.0) - _px(prev)
                        if abs(gap) > 26.0:
                            inputs["move_right" if gap > 0 else "move_left"] = True
                            # SAME EDGE-CROSSING LOGIC AS `_approach`, because this loop
                            # is a SECOND implementation of "walk toward the target" and
                            # the first fix reached only the other one. `_approach` gained
                            # gap handling and `attack.damages` did not move at all -
                            # byte-identical evidence - which is what exposed the
                            # duplication. Two loops doing the same job is a defect that
                            # presents as a fix not working.
                            if _player(prev).get("grounded") is True:
                                d = self._edge_distance(prev, gap > 0)
                                if d is not None and d <= self._EDGE_JUMP_WITHIN:
                                    inputs["jump"] = True
                    t = s.step_raw(inputs)
                    hits += t.events.count("enemy_hit")
                    if "enemy_dead" in t.events:
                        deaths += t.events.count("enemy_dead")
                        score_pairs.append((_i(prev, "score"), _i(t, "score")))
                    prev = t
                    if deaths and score_pairs:
                        break
                    if t.state.get("game_over") is True:
                        break
                detail = (f"{s.ticks_sent} ticks of walk-and-swing: {hits} enemy_hit, "
                          f"{deaths} enemy_dead, first target id={tid!r} hp={hp_before}")
                dmg = Criterion("attack.damages", self._q("attack.damages"),
                                hits > 0, detail)
                sc = Criterion(
                    "score.on_kill", self._q("score.on_kill"),
                    bool(score_pairs) and any(b > a for a, b in score_pairs),
                    (f"score across kill ticks: {score_pairs[:5]}" if score_pairs
                     else "no kill was observed, so the reward could not be measured. "
                          + detail))
                return [dmg, sc]
        except ProbeError as e:
            return list(unusable_criteria([(c, self._q(c)) for c in ids], e,
                                          "the combat session"))

    # -- taking damage: contact, the window, knockback, dying --------------- #

    def _hurt(self, repo, env) -> list[Criterion]:
        ids = ("enemy.damages_player", "invuln.window", "knockback.applied",
               "gameover.triggers")
        try:
            with ProbeSession(repo=repo, env=env, seed=7,
                              total_timeout_s=900.0) as s:
                live, _, note = self._take_control(s)
                if not live:
                    return [Criterion(c, self._q(c), False, note) for c in ids]
                # WALK INTO the nearest enemy and never attack. Establishing contact is
                # the whole experiment; idling next to one measures nothing.
                hp0 = _hp(s.last)
                hit_ticks: list[int] = []
                contact_ticks = 0
                vx_before = None
                vx_after = None
                side = None
                prev = s.last
                for _ in range(4000):
                    e = self._nearest(prev)
                    inputs: dict[str, Any] = {}
                    if e is not None:
                        gap = (_f(e, "x") or 0.0) - _px(prev)
                        if abs(gap) > 2.0:
                            inputs["move_right" if gap > 0 else "move_left"] = True
                        if abs(gap) < 40.0:
                            contact_ticks += 1
                    t = s.step_raw(inputs)
                    if "player_hit" in t.events:
                        if not hit_ticks:
                            vx_before = _f(_player(prev), "vx")
                            vx_after = _f(_player(t), "vx")
                            side = (_f(e, "x") or 0.0) - _px(prev) if e else None
                        hit_ticks.append(t.tick)
                    prev = t
                    if t.state.get("game_over") is True:
                        break
                hp1 = _hp(s.last)
                dmg = Criterion(
                    "enemy.damages_player", self._q("enemy.damages_player"),
                    len(hit_ticks) > 0 and hp1 < hp0,
                    f"walked into the nearest enemy: {len(hit_ticks)} player_hit "
                    f"events over {s.ticks_sent} ticks, hp {hp0} -> {hp1}")

                gaps = [b - a for a, b in zip(hit_ticks, hit_ticks[1:])]
                # The window is what is being measured, not the health pool: with no
                # window, contact damages every tick and consecutive hits are 1 apart.
                window_ok = len(hit_ticks) >= 2 and min(gaps) > 1
                invuln = Criterion(
                    "invuln.window", self._q("invuln.window"), window_ok,
                    (f"hits landed at ticks {hit_ticks[:6]}; the smallest gap between "
                     f"consecutive hits was {min(gaps)} ticks (wants more than 1)"
                     if gaps else
                     f"only {len(hit_ticks)} hit(s) landed in {s.ticks_sent} ticks of "
                     f"walking into enemies, so the window could not be measured"))

                # AWAY, not merely "changed". Requiring vx to decrease when the enemy
                # is on the right is satisfied by knockback of ZERO (180 -> 0 is a
                # decrease), so a mutant that deletes the impulse would have passed.
                # The named property is "knocked away from it", so that is asserted.
                moved_away = (vx_before is not None and vx_after is not None
                              and side is not None
                              and (vx_after < -1.0 if side > 0 else vx_after > 1.0))
                knock = Criterion(
                    "knockback.applied", self._q("knockback.applied"), moved_away,
                    f"on the first hit the enemy was on the "
                    f"{'right' if (side or 0) > 0 else 'left'} and the player's vx went "
                    f"{vx_before} -> {vx_after}")

                if s.last.state.get("game_over") is not True:
                    over = Criterion(
                        "gameover.triggers", self._q("gameover.triggers"), False,
                        f"the player never died in {s.ticks_sent} ticks of walking "
                        f"into enemies (hp {hp1})")
                    return [dmg, invuln, knock, over]
                over_at = s.last.tick
                score_at_death = _i(s.last, "score")
                for _ in range(200):
                    s.step_raw({"move_right": True, "jump": True, "attack": True})
                still = s.last.state.get("game_over") is True
                frozen = _i(s.last, "score") == score_at_death
                alive = _player(s.last).get("alive")
                over = Criterion(
                    "gameover.triggers", self._q("gameover.triggers"),
                    still and frozen and alive is not True,
                    f"game over at tick {over_at}; after 200 more ticks of input: "
                    f"game_over={still}, alive={alive}, score frozen: {frozen}")
                return [dmg, invuln, knock, over]
        except ProbeError as e:
            return list(unusable_criteria([(c, self._q(c)) for c in ids], e,
                                          "the damage session"))

    # -- the edges of the stage --------------------------------------------- #

    def _bounded(self, repo, env) -> Criterion:
        cid = "player.bounded"
        try:
            with ProbeSession(repo=repo, env=env, seed=7) as s:
                live, _, note = self._take_control(s)
                if not live:
                    return Criterion(cid, self._q(cid), False, note)
                lvl = s.last.state.get("level") or {}
                w = _f(lvl, "w", 0.0) or 0.0
                xs = []
                for _ in range(900):
                    xs.append(_px(s.step_raw({"move_left": True})))
                inside = all(-1e-3 <= x <= w + 1e-3 for x in xs)
                reached = min(xs) <= w * 0.2
                return Criterion(
                    cid, self._q(cid), inside and reached,
                    f"900 ticks walking left on a stage {w:.0f} wide: reached "
                    f"x={min(xs):.1f}, never left the stage: {inside}")
        except ProbeError as e:
            return unusable_criteria([(cid, self._q(cid))], e, "the bounds session")[0]

    def _stage(self, repo, env) -> Criterion:
        """DIAGNOSTIC. Walk right, jump when stuck, and see whether the stage ends."""
        cid = "stage.completes"
        try:
            with ProbeSession(repo=repo, env=env, seed=7,
                              total_timeout_s=900.0) as s:
                live, _, note = self._take_control(s)
                if not live:
                    return Criterion(cid, self._q(cid), False, note, scored=False)
                lvl = s.last.state.get("level") or {}
                goal = _f(lvl, "goal_x")
                best = _px(s.last)
                last_x = best
                stalled = 0
                cleared = False
                for _ in range(4000):
                    inputs: dict[str, Any] = {"move_right": True}
                    if stalled > 12:
                        inputs["jump"] = True
                    t = s.step_raw(inputs)
                    x = _px(t)
                    best = max(best, x)
                    stalled = stalled + 1 if x - last_x < 0.3 else 0
                    last_x = x
                    if "stage_clear" in t.events or t.state.get("victory") is True:
                        cleared = True
                        break
                    if t.state.get("game_over") is True:
                        break
                return Criterion(
                    cid, self._q(cid), cleared,
                    f"walked right for {s.ticks_sent} ticks, reached x={best:.1f} of a "
                    f"goal at {goal}; victory={s.last.state.get('victory')}",
                    scored=False)
        except ProbeError as e:
            return unusable_criteria([(cid, self._q(cid))], e, "the traversal session",
                                     self.diagnostic_only)[0]


BOT = PlatformerBot()
