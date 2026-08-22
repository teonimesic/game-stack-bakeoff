"""Pong - behavioural tests.

A GOOD control fixture. Real assertions about the rules, not smoke tests.
Run with `python3 tests.py`; exits non-zero if anything fails.
"""

from __future__ import annotations

import math
import sys
import traceback

import game as g
from probe import trace_line

TESTS = []


def test(fn):
    TESTS.append(fn)
    return fn


AIM_BIAS = 18.0


def tracking_inputs(sim: g.Game) -> dict:
    """Both paddles chase the ball, each aiming slightly off centre so returns
    come off at an angle instead of settling into a flat horizontal rally."""
    out = {}
    left_target = sim.ball_y - AIM_BIAS
    right_target = sim.ball_y + AIM_BIAS
    if left_target > sim.left_y + 2:
        out["left_up"] = True
    elif left_target < sim.left_y - 2:
        out["left_down"] = True
    if right_target > sim.right_y + 2:
        out["right_up"] = True
    elif right_target < sim.right_y - 2:
        out["right_down"] = True
    return out


def play(seed: int, ticks: int, driver=tracking_inputs):
    sim = g.Game(seed)
    log = []
    for _ in range(ticks):
        events = sim.step(driver(sim))
        log.append((sim.tick, events, sim.state()))
    return sim, log


@test
def determinism_same_seed_same_run():
    a = [h for h in _hashes(9, 900)]
    b = [h for h in _hashes(9, 900)]
    assert a == b, "same seed produced different hash sequences"
    assert len(set(a)) > 500, "hashes barely change over 900 ticks"


def _hashes(seed, ticks):
    sim = g.Game(seed)
    out = [sim.hash_hex()]
    for _ in range(ticks):
        sim.step(tracking_inputs(sim))
        out.append(sim.hash_hex())
    return out


@test
def different_seeds_diverge():
    runs = {s: tuple(_hashes(s, 400)) for s in (1, 2, 3, 4, 5)}
    assert len(set(runs.values())) >= 4, "seeds barely affect the run: %r" % (
        len(set(runs.values())),)


@test
def serve_direction_depends_on_seed():
    signs = {1 if g.Game(s).ball_vx > 0 else -1 for s in range(24)}
    assert signs == {1, -1}, "serve direction never varies with the seed"


@test
def ball_stays_inside_the_walls():
    sim = g.Game(3)
    limit = g.ARENA_HALF_H - g.BALL_RADIUS + 1e-6
    for _ in range(4000):
        sim.step(tracking_inputs(sim))
        assert -limit <= sim.ball_y <= limit, "ball escaped vertically at y=%r" % sim.ball_y


@test
def wall_bounce_flips_vy_and_is_reported():
    sim = g.Game(11)
    seen = 0
    for _ in range(3000):
        before = sim.ball_vy
        events = sim.step(tracking_inputs(sim))
        if "wall_bounce" in events:
            seen += 1
            assert before * sim.ball_vy < 0 or "paddle_hit" in events, \
                "wall_bounce reported without reversing vy"
    assert seen > 0, "no wall bounce in 3000 ticks"


@test
def paddles_move_and_clamp():
    sim = g.Game(5)
    start = sim.left_y
    for _ in range(10):
        sim.step({"left_up": True})
    assert sim.left_y > start, "left_up did not raise the left paddle"
    for _ in range(400):
        sim.step({"left_up": True, "right_down": True})
    assert abs(sim.left_y - g.PADDLE_LIMIT) < 1e-9, "left paddle left the arena: %r" % sim.left_y
    assert abs(sim.right_y + g.PADDLE_LIMIT) < 1e-9, "right paddle left the arena: %r" % sim.right_y


@test
def paddle_speed_matches_the_constant():
    sim = g.Game(5)
    sim.step({"right_up": True})
    assert abs(sim.right_y - g.PADDLE_SPEED * g.DT) < 1e-9, "paddle moved at the wrong rate"


@test
def paddle_hit_reverses_the_ball_and_counts_the_rally():
    sim = g.Game(7)
    hits = 0
    for _ in range(2000):
        before = sim.ball_vx
        events = sim.step(tracking_inputs(sim))
        if "paddle_hit" in events:
            hits += 1
            assert before * sim.ball_vx < 0, "paddle_hit did not send the ball back"
            assert sim.rally == hits, "rally %d did not track hit %d" % (sim.rally, hits)
        if "score_left" in events or "score_right" in events:
            break
    assert hits >= 3, "only %d paddle hits with tracking paddles" % hits


@test
def hit_position_changes_the_outgoing_angle():
    angles = []
    for offset in (-30.0, 0.0, 30.0):
        sim = g.Game(1)
        sim.left_y = 0.0
        sim.ball_x = -g.PADDLE_X + g.PADDLE_HALF_W + g.BALL_RADIUS + 4.0
        sim.ball_y = offset
        sim.ball_vx = -300.0
        sim.ball_vy = 0.0
        events = sim.step({})
        assert "paddle_hit" in events, "no hit at offset %r" % offset
        angles.append(math.atan2(sim.ball_vy, sim.ball_vx))
    assert angles[0] < angles[1] < angles[2], "angle does not vary with hit position: %r" % angles
    assert abs(angles[1]) < 1e-9, "centre hit was not flat"


@test
def rally_speeds_the_ball_up_to_a_ceiling():
    sim = g.Game(2)
    speeds = []
    for _ in range(6000):
        events = sim.step(tracking_inputs(sim))
        if "paddle_hit" in events:
            speeds.append(math.hypot(sim.ball_vx, sim.ball_vy))
        if len(speeds) >= 30:
            break
    assert len(speeds) >= 4, "rally too short to measure speed"
    assert speeds[1] > speeds[0] + 1.0, "ball did not speed up: %r" % speeds[:2]
    for s in speeds:
        assert s <= g.BALL_SPEED_MAX + 1e-6, "ball exceeded the speed ceiling: %r" % s


@test
def missing_the_ball_scores_for_the_other_side():
    sim = g.Game(4)
    scored = None
    for _ in range(4000):
        events = sim.step({})  # nobody moves, so somebody must concede
        if "score_right" in events or "score_left" in events:
            scored = events
            break
    assert scored is not None, "nobody scored in 4000 idle ticks"
    total = sim.score_left + sim.score_right
    assert total == 1, "score bookkeeping is wrong: %r" % sim.state()["score"]
    assert sim.rally == 0, "rally was not reset by the point"
    assert abs(sim.ball_x) < 1e-9 and abs(sim.ball_y) < 1e-9, "ball was not served from the centre"


@test
def first_to_eleven_wins_and_play_stops():
    sim = g.Game(6)
    for _ in range(200000):
        sim.step({})
        if sim.over:
            break
    assert sim.over, "no winner after 200000 idle ticks"
    assert max(sim.score_left, sim.score_right) == g.WIN_SCORE, \
        "winner at the wrong score: %r" % sim.state()["score"]
    frozen = sim.state()
    for _ in range(100):
        events = sim.step({"left_up": True, "right_down": True})
        assert events == [], "events kept firing after the game was won"
    assert sim.state()["game_over"] is True, "game_over stayed false after the win"
    assert sim.state() == frozen, "the world kept changing after the game was won"
    st = sim.state()
    assert st["ball"] == {"x": 0.0, "y": 0.0, "vx": 0.0, "vy": 0.0}, "ball moved after the win"
    assert st["paddles"][0]["y"] == 0.0, "paddle moved after the win"


@test
def state_shape_is_exactly_the_contract():
    st = g.Game(1).state()
    assert set(st) == {"ball", "paddles", "score", "rally", "game_over"}, \
        "top-level keys: %r" % sorted(st)
    assert st["game_over"] is False, "a fresh game is not over"
    assert set(st["ball"]) == {"x", "y", "vx", "vy"}, "ball keys: %r" % sorted(st["ball"])
    assert [p["side"] for p in st["paddles"]] == ["left", "right"], "paddle order/sides"
    assert set(st["paddles"][0]) == {"side", "y"}, "paddle keys"
    assert set(st["score"]) == {"left", "right"}, "score keys"
    assert isinstance(st["rally"], int), "rally must be an integer"


@test
def every_number_is_finite_and_serialisable():
    sim = g.Game(8)
    for _ in range(3000):
        events = sim.step(tracking_inputs(sim))
        line = trace_line(sim.tick, sim, events)  # allow_nan=False, so this raises on NaN
        assert "NaN" not in line and "Infinity" not in line, line
        for name in events:
            assert name in ("paddle_hit", "wall_bounce", "score_left", "score_right"), name


@test
def hash_reflects_state_not_just_the_tick():
    a = g.Game(1)
    b = g.Game(1)
    for _ in range(50):
        a.step({})
        b.step({"left_up": True})
    assert a.hash_hex() != b.hash_hex(), "hash ignores the paddles"


def main() -> int:
    failures = []
    for fn in TESTS:
        try:
            fn()
        except Exception:
            failures.append((fn.__name__, traceback.format_exc()))
    for name, tb in failures:
        print("FAIL %s\n%s" % (name, tb), file=sys.stderr)
    print("tests: %d/%d passed" % (len(TESTS) - len(failures), len(TESTS)))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
