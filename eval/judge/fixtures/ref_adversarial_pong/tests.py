"""DELIBERATELY FAKE CONTROL FIXTURE - do not treat this as a real game.

These tests are exactly the kind a fake submission ships: they check shapes,
ranges and the fact that numbers move, and they never once check a rule. They
all pass, so `just verify` is green while the game underneath is an animation.

Run with `python3 tests.py`.
"""

from __future__ import annotations

import sys
import traceback

import game as g
from probe import trace_line

TESTS = []


def test(fn):
    TESTS.append(fn)
    return fn


@test
def state_shape_is_exactly_the_contract():
    st = g.Game(1).state()
    assert set(st) == {"ball", "paddles", "score", "rally"}, sorted(st)
    assert set(st["ball"]) == {"x", "y", "vx", "vy"}, sorted(st["ball"])
    assert [p["side"] for p in st["paddles"]] == ["left", "right"]
    assert set(st["score"]) == {"left", "right"}


@test
def the_ball_stays_inside_the_arena():
    sim = g.Game(1)
    for _ in range(4000):
        sim.step({})
        st = sim.state()
        assert abs(st["ball"]["x"]) <= g.ARENA_HALF_W
        assert abs(st["ball"]["y"]) <= g.ARENA_HALF_H


@test
def the_paddles_stay_inside_the_arena():
    sim = g.Game(2)
    for _ in range(4000):
        sim.step({})
        for p in sim.state()["paddles"]:
            assert abs(p["y"]) <= g.PADDLE_LIMIT + 1e-9


@test
def the_ball_actually_moves():
    sim = g.Game(3)
    first = sim.state()["ball"]["x"]
    for _ in range(30):
        sim.step({})
    assert sim.state()["ball"]["x"] != first, "the ball never moved"


@test
def the_tick_advances_one_at_a_time():
    sim = g.Game(4)
    for expected in range(1, 200):
        sim.step({})
        assert sim.tick == expected


@test
def paddle_hits_are_reported():
    sim = g.Game(5)
    seen = 0
    for _ in range(500):
        seen += sim.step({}).count("paddle_hit")
    assert seen > 0, "no paddle hits in 500 ticks"


@test
def wall_bounces_are_reported():
    sim = g.Game(5)
    seen = 0
    for _ in range(500):
        seen += sim.step({}).count("wall_bounce")
    assert seen > 0, "no wall bounces in 500 ticks"


@test
def the_score_only_ever_goes_up():
    sim = g.Game(6)
    last = (0, 0)
    for _ in range(9000):
        sim.step({})
        st = sim.state()["score"]
        now = (st["left"], st["right"])
        assert now[0] >= last[0] and now[1] >= last[1], "score went backwards"
        last = now
    assert last != (0, 0), "nobody ever scored"


@test
def nobody_scores_more_than_eleven():
    sim = g.Game(7)
    for _ in range(20000):
        sim.step({})
    st = sim.state()["score"]
    assert st["left"] <= g.WIN_SCORE and st["right"] <= g.WIN_SCORE, st


@test
def only_contracted_events_are_emitted():
    allowed = {"paddle_hit", "wall_bounce", "score_left", "score_right"}
    sim = g.Game(8)
    for _ in range(3000):
        for name in sim.step({}):
            assert name in allowed, name


@test
def every_trace_line_is_finite():
    sim = g.Game(9)
    for _ in range(1000):
        events = sim.step({})
        line = trace_line(sim.tick, sim, events)
        assert "NaN" not in line and "Infinity" not in line, line


@test
def the_hash_changes_every_tick():
    sim = g.Game(10)
    seen = set()
    for _ in range(500):
        sim.step({})
        seen.add(sim.hash_hex())
    assert len(seen) == 500, "the hash repeated"


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
