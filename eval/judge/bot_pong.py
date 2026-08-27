#!/usr/bin/env python3
"""Scripted play-bot for the Pong task.

Every criterion here is an assertion about OBSERVABLE STATE reported by the game's own
probe, driven by inputs this bot chose. Nothing is inferred from pixels and nothing is
asked of a model. Per research/09, that is the difference between a signal and a coin
flip.
"""

from __future__ import annotations

import math
from typing import Any

from checks import determinism_criteria, idle_tape
from probe import (Bot, Criterion, ProbeError, ProbeSession, Tick,
                   end_condition_holds, unusable_criteria)


def _ball(t: Tick) -> dict[str, Any]:
    b = t.state.get("ball")
    return b if isinstance(b, dict) else {}


def _paddle_y(t: Tick, side: str) -> float | None:
    for p in t.state.get("paddles") or []:
        if isinstance(p, dict) and p.get("side") == side:
            try:
                return float(p["y"])
            except (KeyError, TypeError, ValueError):
                return None
    return None


def _score(t: Tick, side: str) -> int:
    s = t.state.get("score")
    if isinstance(s, dict):
        try:
            return int(s.get(side, 0))
        except (TypeError, ValueError):
            return 0
    return 0


def _f(d: dict[str, Any], k: str) -> float | None:
    try:
        v = float(d[k])
    except (KeyError, TypeError, ValueError):
        return None
    return v if math.isfinite(v) else None


#: How long to wait for the first serve before calling the ball dead. Generous on
#: purpose: 8 seconds at 64 Hz covers an opening title card, a countdown and a pause,
#: and a game that has not served by then is not withholding the ball for presentation.
LIVE_BUDGET = 512


class PongBot(Bot):
    #: A representative rally, long enough that pacing is a property of the game and
    #: not of how long the criteria drive happened to take (FINDINGS #52).
    play_ticks = 3000
    game = "g1_pong"
    #: The criterion that checks THIS GAME'S END CONDITION, whatever it is called.
    #: Named explicitly because the concept has two spellings across the suite:
    #: `gameover.triggers` in three games and `match.ends` in pong, which is
    #: first-to-11, so its end condition is a WIN rather than a loss. This game
    #: ends when one side reaches eleven points.
    #: A cross-game audit asking "does every game verify its own end condition?"
    #: would grep for `gameover` and report a false gap for pong - a mechanical sweep
    #: reporting something untrue, which this project has lost time to before (#38).
    #: Read this attribute instead of guessing from the id.
    end_condition = "match.ends"

    criteria = [
        ("state.shape", "Does the probe report the contracted state shape (ball, "
                        "paddles, score, rally) with finite numbers?"),
        ("ball.moves", "Does the ball move on its own?"),
        ("ball.wall_bounce", "Does the ball bounce off the top and bottom walls, "
                             "reversing its vertical velocity?"),
        ("paddle.moves", "Does holding a paddle control move that paddle?"),
        ("paddle.bounded", "Does the paddle stop at the arena edge instead of leaving "
                           "the play area?"),
        ("paddle.deflects", "Does a paddle deflect the ball back the other way?"),
        ("rally.counts", "Does the rally counter increase on each paddle hit?"),
        ("rally.resets", "Does the rally counter reset to zero when a point is "
                         "scored?"),
        ("score.increments", "Does a player score when the ball gets past the other "
                             "paddle?"),
        ("serve.resets", "Is the ball served again from near the centre after a "
                         "point?"),
        ("match.ends", "Does the match stop at eleven points instead of scoring "
                       "forever?"),
    ] + [
        ("determinism.replay", "Does replaying the same seed and the same inputs "
                               "reproduce the same state hash at every tick?"),
        ("determinism.seed", "Do two different seeds produce different runs?"),
    ]

    # ------------------------------------------------------------------ #

    def run(self, s: ProbeSession) -> list[Criterion]:
        out: list[Criterion] = []
        add = out.append

        t0 = s.last
        b0 = _ball(t0)
        shape_ok = (
            all(_f(b0, k) is not None for k in ("x", "y", "vx", "vy"))
            and _paddle_y(t0, "left") is not None
            and _paddle_y(t0, "right") is not None
            and isinstance(t0.state.get("score"), dict)
            and isinstance(t0.state.get("rally"), (int, float))
        )
        add(Criterion("state.shape", self._q("state.shape"), shape_ok,
                      f"tick 0 state: {str(t0.state)[:300]}"))
        if not shape_ok:
            # Without the contracted shape nothing else can be measured honestly.
            for cid, q in self.criteria[1:]:
                add(Criterion(cid, q, False, "state shape contract not met"))
            return out

        # --- ball moves ------------------------------------------------- #
        # WAIT FOR THE BALL TO BE LIVE, THEN MEASURE - do not assume it is live at
        # tick 0.
        #
        # MEASURED false negative: a Godot submission holds the ball for
        # `OPENING_DELAY = 104` ticks before the first serve, with the reason in its own
        # source - "so the title card is readable". Idling a fixed 60 ticks and asserting
        # movement therefore failed a correct game FOR DOING THE PRESENTATION WORK THE
        # TASK ASKS FOR. A serve countdown, a title card and a "get ready" beat are all
        # normal, and the task now explicitly rewards them.
        #
        # This is the sixteenth instance of the pattern behind every play-bot false
        # negative here: the criterion waited for a condition instead of establishing
        # one. What it must fail is a ball that NEVER moves, not one that starts late.
        # Watch the BALL'S POSITION, not its velocity.
        #
        # First repair of this criterion waited for a non-zero velocity and then measured
        # 60 ticks. That still failed a Unity submission which sets the serve velocity at
        # tick 1 but holds the ball in place during its countdown: "waited 1 ticks for the
        # serve ... travelled 0.0 units". Velocity was a PROXY for liveness, and different
        # submissions make it live at different moments. The criterion is named
        # `ball.moves`, so measure movement.
        moved = 0.0
        moved_at = None
        for _ in range(LIVE_BUDGET):
            t = s.step_raw({})
            b = _ball(t)
            moved = math.hypot((_f(b, "x") or 0) - (_f(b0, "x") or 0),
                               (_f(b, "y") or 0) - (_f(b0, "y") or 0))
            if moved > 1.0:
                moved_at = t.tick
                break
        add(Criterion(
            "ball.moves", self._q("ball.moves"), moved_at is not None,
            f"ball travelled {moved:.1f} units by tick {moved_at}"
            if moved_at is not None else
            f"the ball never moved more than 1.0 units in {LIVE_BUDGET} ticks "
            f"({LIVE_BUDGET / 64:.1f}s) - furthest it got was {moved:.2f}"))

        # --- wall bounce ------------------------------------------------ #
        add(self._wall_bounce(s))

        # --- a tracking rally: deflection, rally counter ----------------- #
        # ORDER MATTERS, and this is the second time this project has learned it (the
        # arena bot carries the same note). Everything from here to `match.ends` needs
        # a match that is still being played. The paddle-mechanics checks below hold
        # one control down for hundreds of ticks with nobody defending, which concedes
        # points, and a game that reaches eleven stops accepting play - so measuring
        # them first would leave every rally and scoring criterion looking at a frozen
        # 11-0 board. MEASURED: on a reference implementation reseeded to 0, doing the
        # paddle phases first cost `paddle.deflects`, `rally.counts`, `rally.resets`,
        # `score.increments` and `serve.resets` - five false negatives, all from the
        # bot's own play order rather than from the game.
        rally_ok, deflect_ok, rally_reset_ok, hits, rally_detail = self._rally(s)
        add(Criterion("paddle.deflects", self._q("paddle.deflects"), deflect_ok,
                      f"{hits} paddle_hit events, each accompanied by a horizontal "
                      f"velocity sign flip: {deflect_ok}"))
        # The evidence says which way it READ, not what it was looking for. Until
        # 2026-08-26 this printed "rally counter incremented on paddle hits (N hits
        # seen)" on a pass and on a fail alike, so a reader could not tell the verdict
        # from the sentence beside it - the shape #183 found in `fire.rate_limited`.
        add(Criterion("rally.counts", self._q("rally.counts"), rally_ok, rally_detail))

        # --- scoring, serve reset, rally reset --------------------------- #
        score_ok, serve_ok, reset_ok, detail = self._score_a_point(s)
        add(Criterion("rally.resets", self._q("rally.resets"),
                      rally_reset_ok or reset_ok, detail))
        add(Criterion("score.increments", self._q("score.increments"), score_ok, detail))
        add(Criterion("serve.resets", self._q("serve.resets"), serve_ok, detail))

        # --- match ends at eleven ---------------------------------------- #
        add(self._match_ends(s))

        # --- paddle mechanics, on a match nobody is trying to win --------- #
        moves_c, bounded_c = self._paddle_mechanics(s.repo, s.env)
        add(moves_c)
        add(bounded_c)

        out.extend(determinism_criteria(s.repo, idle_tape(400), env=s.env))
        return out

    # ------------------------------------------------------------------ #

    def _q(self, cid: str) -> str:
        return next(q for c, q in self.criteria if c == cid)

    @staticmethod
    def _track(t: Tick, side: str, dead: float = 3.0,
               offset: float = 0.0) -> dict[str, bool]:
        """Inputs that make one paddle chase the ball.

        `offset` parks the paddle CENTRE that far below the ball, so contact happens
        off-centre by `offset`. That is the whole mechanism behind `ball.wall_bounce`:
        the task spec says where the ball strikes the paddle sets its outgoing angle,
        so an off-centre return is how a bot CREATES vertical velocity instead of
        waiting to be handed some.
        """
        by = _f(_ball(t), "y")
        py = _paddle_y(t, side)
        if by is None or py is None:
            return {}
        target = by - offset
        if target > py + dead:
            return {f"{side}_up": True}
        if target < py - dead:
            return {f"{side}_down": True}
        return {}

    def play_inputs(self, tick: Tick) -> dict[str, Any]:
        """Both paddles chase the ball: a real rally, which is what pacing is about."""
        out: dict[str, Any] = {}
        out.update(self._track(tick, "left"))
        out.update(self._track(tick, "right"))
        return out

    #: Paddle-centre offsets tried when hunting for an off-centre return, smallest
    #: first. Too large an offset misses the ball entirely (a point is conceded, no
    #: harm done, and the offset is walked back); too small imparts no angle. The
    #: paddle's half-height is not in the state contract, so it is searched for.
    _STRIKE_OFFSETS = (10.0, 20.0, 30.0, 45.0, 65.0, 90.0)
    #: |vy| / |v| above which a return counts as steep enough to reach a wall.
    _STEEP_ENOUGH = 0.18

    def _wall_bounce(self, s: ProbeSession) -> Criterion:
        """CAUSE a wall bounce, then check for it.

        The version this replaces idled and hoped. It failed `g1_pong__godot__t0` and
        `g1_pong__unity__t1`, both adjudicated FALSE NEGATIVES: a shallow serve between
        two centred paddles ping-pongs along the middle of the arena and never reaches
        a wall, so the criterion was reporting the serve angle, not the wall collision.

        Here both paddles chase the ball with a deliberate vertical offset, so returns
        leave the paddle at an angle and the ball is driven into a wall. Only then is
        the bounce looked for, and only a `wall_bounce` event that coincides with a
        vertical velocity sign flip counts - the event alone could be decorative, and
        the flip alone could be a wall the game never announced.

        A FALSE here now means: the ball was steered into a wall and did not come back.
        """
        start = len(s.history)
        prev = s.last
        prev_vy = _f(_ball(prev), "vy") or 0.0
        base_l, base_r = _score(prev, "left"), _score(prev, "right")

        off_i = 0
        hits = 0
        misses = 0
        best_ratio = 0.0
        steep_at: int | None = None
        saw_event = False
        flip_on_event = False
        peak_y = abs(_f(_ball(prev), "y") or 0.0)

        for _ in range(3000):
            off = self._STRIKE_OFFSETS[off_i]
            inputs: dict[str, Any] = {}
            inputs.update(self._track(prev, "left", offset=off))
            inputs.update(self._track(prev, "right", offset=off))
            t = s.step_raw(inputs)
            b = _ball(t)
            vy = _f(b, "vy")
            vx = _f(b, "vx")
            y = _f(b, "y")
            if y is not None:
                peak_y = max(peak_y, abs(y))

            if "wall_bounce" in t.events:
                saw_event = True
                if vy is not None and prev_vy * vy < 0:
                    flip_on_event = True
            if vy is not None:
                prev_vy = vy

            if "paddle_hit" in t.events:
                hits += 1
                if vx is not None and vy is not None:
                    speed = math.hypot(vx, vy)
                    ratio = abs(vy) / speed if speed > 1e-9 else 0.0
                    best_ratio = max(best_ratio, ratio)
                    if ratio >= self._STEEP_ENOUGH:
                        if steep_at is None:
                            steep_at = t.tick
                    else:
                        # Flat return: aim further from the paddle's centre next time.
                        off_i = min(off_i + 1, len(self._STRIKE_OFFSETS) - 1)
            if "score_left" in t.events or "score_right" in t.events:
                # The offset overshot the paddle and the ball went past. Walk it back.
                misses += 1
                off_i = max(off_i - 1, 0)

            prev = t
            if flip_on_event:
                break
            # Stop before this experiment decides the match: `match.ends` is measured
            # later in this same session and needs points left to score.
            if (_score(t, "left") - base_l) + (_score(t, "right") - base_r) >= 4:
                break

        n_bounce = s.count_event("wall_bounce", start)
        detail = (f"drove {hits} off-centre returns (steepest |vy|/|v| "
                  f"{best_ratio:.2f}, first steep return at tick {steep_at}, "
                  f"{misses} conceded points while searching for the strike offset); "
                  f"ball reached |y|={peak_y:.1f}; {n_bounce} wall_bounce events; "
                  f"vertical velocity sign flip on a bounce tick: {flip_on_event}")
        if not saw_event and steep_at is None and hits == 0:
            # Nothing was established: no return was ever observed, so the ball was
            # never sent anywhere. Scoring a wall bounce off that would be scoring the
            # serve angle again.
            return self.not_established(
                "ball.wall_bounce", self._q("ball.wall_bounce"),
                "no paddle return happened at all, so the ball was never steered "
                "toward a wall. " + detail)
        return Criterion("ball.wall_bounce", self._q("ball.wall_bounce"),
                         saw_event and flip_on_event, detail)

    # -- paddle mechanics, measured where the score cannot matter ---------- #

    @staticmethod
    def _hold_until_still(s: ProbeSession, field: str, cap: int = 600,
                          still: int = 60) -> tuple[list[float], bool]:
        """Hold one control until the paddle stops moving, or until `cap` ticks.

        Waiting a FIXED number of ticks and hoping it was enough is the same mistake as
        waiting for a wall bounce: it measures the paddle's speed, not its behaviour. A
        slow paddle gets the ticks it needs; a fast one costs the run nothing.
        """
        ys: list[float] = []
        same = 0
        for _ in range(cap):
            s.step_raw({field: True})
            cur = _paddle_y(s.last, "left")
            if cur is None:
                break
            ys.append(cur)
            same = same + 1 if len(ys) >= 2 and abs(ys[-1] - ys[-2]) < 1e-9 else 0
            if same >= still:
                return ys, True
        return ys, False

    def _paddle_mechanics(self, repo, env) -> tuple[Criterion, Criterion]:
        """`paddle.moves` and `paddle.bounded`, on their OWN session.

        Both need one control held down for as long as it takes the paddle to reach its
        limit, with nobody defending that side. In the main session that concedes
        points, and enough of them ends the match and freezes every criterion measured
        afterwards. Neither of these two cares what the score is, so they get a fresh
        game and the coupling disappears instead of being budgeted around.
        """
        ids = [("paddle.moves", self._q("paddle.moves")),
               ("paddle.bounded", self._q("paddle.bounded"))]
        try:
            with ProbeSession(repo=repo, env=env, seed=7) as s:
                low, settled_low = self._hold_until_still(s, "left_down")
                high, settled_high = self._hold_until_still(s, "left_up")
                back, settled_back = self._hold_until_still(s, "left_down")
                if not (low and high and back):
                    return (Criterion("paddle.moves", ids[0][1], False,
                                      "the probe stopped reporting a left paddle"),
                            Criterion("paddle.bounded", ids[1][1], False,
                                      "the probe stopped reporting a left paddle"))
                y_low, y_high, y_back = low[-1], high[-1], back[-1]
                moves = y_high - y_low > 5.0 and y_high - y_back > 5.0
                moves_c = Criterion(
                    "paddle.moves", ids[0][1], moves,
                    f"held down to the bottom ({y_low}), up to the top ({y_high}) in "
                    f"{len(high)} ticks, back down ({y_back}) in {len(back)}")
                # Bounded means it STOPPED, at both ends, rather than sliding out of
                # the arena. Held against the limit, y must go constant and stay there.
                bounded = (settled_low and settled_high and settled_back
                           and max(abs(y_low), abs(y_high)) < 1e6)
                bounded_c = Criterion(
                    "paddle.bounded", ids[1][1], bounded,
                    f"holding a direction until movement stopped: top settled at "
                    f"{y_high} (converged: {settled_high}), bottom at {y_low} "
                    f"(converged: {settled_low}); still constant after holding again: "
                    f"{settled_back}")
                return moves_c, bounded_c
        except ProbeError as e:
            a, b = unusable_criteria(ids, e, "the paddle-mechanics session")
            return a, b

    def _rally(self, s: ProbeSession) -> tuple[bool, bool, bool, int, str]:
        """Both paddles track the ball, so rallies happen. Watch hits and the counter.

        `rally.counts` reads the counter ON the tick that raises `paddle_hit`, and that
        ONE-TICK CONTRACT IS THE TASK'S, not this bot's convenience. A counter that
        settles a tick later was proposed as a correct-but-unusual game and DECLINED
        (`tasks/159`), for a reason that is in the rendered prompt rather than in taste:

        - the trace line labelled tick `T` is emitted AFTER step `T` - all four starter
          guides say the probe prints a tick-0 line "before anything has been stepped",
          then steps exactly one tick per input line and prints one line per tick;
        - its `events` are what step `T` raised, and `"paddle_hit"` means "a paddle
          deflected the ball";
        - `rally` is defined by the task as "the number of consecutive paddle hits since
          the last point was scored" - a COUNT OF THOSE EVENTS, not a free variable.

        So a line carrying `paddle_hit` and a `rally` that excludes it states two facts
        about one instant that contradict each other. WHERE the sim increments is still
        free - a collision routine, an end-of-tick pass, a fold over history - as long as
        the value PUBLISHED in a tick's line counts that line's own hit.

        Widening this to a window was rejected on top of that: it is a reason not to
        count a failure (`AGENTS.md` rule 7), it would accept an increment caused by
        something else entirely, and it would change what 25 stored `g1_pong` gradings
        mean (`python3 judge/tier2_census.py --runs-root <checkout>/eval/runs`) to buy a
        pass this criterion has never once withheld.

        A late counter is therefore a FAILURE, and it is a failure the evidence names:
        `rose_late` counts hit ticks whose increment arrived on the following tick, so an
        adjudicator can tell "settles a tick late" from "never moves". It is DIAGNOSTIC
        ONLY and enters no verdict.

        THE VERDICT IS STILL `rose_on_hit > 0`, which passes a counter that moves once
        and stops — weaker than the question the criterion asks and weaker than
        `deflect_ok` beside it. Tightening it changes stored verdicts, which is a
        re-scoring event with its own `tier2_census.py` before-and-after (`tasks/171`),
        so it is not bundled in here.
        """
        start = len(s.history)
        prev = s.last
        hits = 0
        deflect_ok = True
        rose_on_hit = 0
        rose_late = 0
        rally_reset = False
        #: `rally` as of a hit tick that did not count its own hit; carried exactly one
        #: tick, so the lookahead cannot drift into an unrelated increment.
        late_watch: float | None = None
        for _ in range(3000):
            inputs: dict[str, Any] = {}
            inputs.update(self._track(prev, "left"))
            inputs.update(self._track(prev, "right"))
            t = s.step_raw(inputs)
            r_a, r_b = prev.state.get("rally"), t.state.get("rally")
            numeric = (isinstance(r_a, (int, float))
                       and isinstance(r_b, (int, float)))
            # Settle the outstanding watch FIRST, on every tick. Reading it only on a
            # hitless tick loses the observation whenever two hits land back to back,
            # and back-to-back is exactly the arrangement that hides a late counter:
            # the deferred increment arrives on the second hit's tick and gets read as
            # that hit's own.
            if late_watch is not None and numeric and r_b > late_watch:
                rose_late += 1
            late_watch = None
            if "paddle_hit" in t.events:
                hits += 1
                vx_a, vx_b = _f(_ball(prev), "vx"), _f(_ball(t), "vx")
                if not (vx_a is not None and vx_b is not None and vx_a * vx_b < 0):
                    deflect_ok = False
                if numeric and r_b > r_a:
                    rose_on_hit += 1
                else:
                    late_watch = r_b if numeric else None
            if "score_left" in t.events or "score_right" in t.events:
                if t.state.get("rally") == 0:
                    rally_reset = True
            prev = t
            if hits >= 6 and rose_on_hit:
                break
        if hits == 0:
            detail = (f"no paddle_hit in {len(s.history) - start} ticks of a tracking "
                      f"rally, so the counter was never read against a hit")
        else:
            detail = f"rally rose on {rose_on_hit} of {hits} paddle_hit ticks"
            if rose_late:
                detail += (f"; on {rose_late} of them it rose on the FOLLOWING tick "
                           f"instead, which is a counter a tick behind the hit its own "
                           f"trace line reports")
        return ((rose_on_hit > 0), (deflect_ok and hits > 0), rally_reset, hits, detail)

    def _score_a_point(self, s: ProbeSession) -> tuple[bool, bool, bool, str]:
        """Park the right paddle at an extreme; the left player should score."""
        before_l = _score(s.last, "left")
        before_r = _score(s.last, "right")
        prev = s.last
        scored = False
        serve_ok = False
        reset_ok = False
        for _ in range(4000):
            inputs: dict[str, Any] = {"right_up": True}
            inputs.update(self._track(prev, "left"))
            t = s.step_raw(inputs)
            if "score_left" in t.events or "score_right" in t.events:
                scored = True
                if t.state.get("rally") == 0:
                    reset_ok = True
                # The ball should be re-served from near the middle within a moment.
                for _ in range(6):
                    t = s.step_raw({"right_up": True})
                    bx = _f(_ball(t), "x")
                    if bx is not None and abs(bx) < 60.0:
                        serve_ok = True
                        break
                break
            prev = t
        after_l, after_r = _score(s.last, "left"), _score(s.last, "right")
        score_ok = scored and (after_l + after_r) > (before_l + before_r)
        return score_ok, serve_ok, reset_ok, (
            f"score {before_l}-{before_r} -> {after_l}-{after_r}; "
            f"score event seen: {scored}; ball re-centred after the point: {serve_ok}; "
            f"rally zeroed on the point: {reset_ok}")

    def _match_ends(self, s: ProbeSession) -> Criterion:
        """Let one side run away with it and check the score stops at eleven."""
        prev = s.last
        capped_at = None
        for _ in range(12_000):
            inputs: dict[str, Any] = {"right_up": True}
            inputs.update(self._track(prev, "left"))
            t = s.step_raw(inputs)
            prev = t
            if max(_score(t, "left"), _score(t, "right")) >= 11:
                capped_at = len(s.history)
                break
        if capped_at is None:
            return Criterion("match.ends", self._q("match.ends"), False,
                             f"nobody reached 11 within the budget; final score "
                             f"{_score(s.last, 'left')}-{_score(s.last, 'right')}")
        peak_l, peak_r = _score(s.last, "left"), _score(s.last, "right")
        # IDLE FIRST, THEN PRESS AND READ THROUGH THE RESET -
        # `probe.end_condition_holds` holds the reason, and holds it once for all four
        # bots. Pong is where the idle half was first paid for, by a Rust submission
        # that clears its game-over card on any control (`tasks/157`); the pressed half
        # is what keeps a match that ends and keeps playing from passing on the strength
        # of nobody touching it.
        end = end_condition_holds(
            s, idle_ticks=600, press_ticks=600,
            inputs={"left_up": True, "right_up": True},
            sample=lambda t: (_score(t, "left"), _score(t, "right")))
        end_l, end_r = end.after_idle
        stayed = end.passed and max(end_l, end_r) == 11
        return Criterion("match.ends", self._q("match.ends"), stayed,
                         f"reached {peak_l}-{peak_r} at tick {capped_at}; "
                         f"{end.detail('(left, right) score')}")


BOT = PongBot()
