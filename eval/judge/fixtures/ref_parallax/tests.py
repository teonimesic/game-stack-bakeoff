"""s1_parallax - behavioural tests. Run with `python3 tests.py`.

A GOOD control fixture. Real assertions about the scene's rules, in the three tiers the
starters use: simulation, replay/determinism, and rendering.
"""

from __future__ import annotations

import sys
import traceback

import film
import game as g
from probe import trace_line

TESTS = []


def test(fn):
    TESTS.append(fn)
    return fn


def run(seed: int, ticks: int) -> g.Scene:
    s = g.Scene(seed)
    for _ in range(ticks):
        s.step({})
    return s


# -- simulation ------------------------------------------------------------- #


@test
def car_travels_forward_and_never_stops():
    s = g.Scene(7)
    last = s.car_x
    for _ in range(660):
        s.step({})
        assert s.car_x > last, "the car must always be moving forward"
        last = s.car_x


@test
def layer_rates_are_ordered_by_depth():
    s = run(7, 300)
    st = s.state()
    rows = sorted(st["layers"], key=lambda r: r["depth"])
    rates = [r["offset"] / s.car_x for r in rows]
    assert all(rates[i] > rates[i + 1] for i in range(len(rates) - 1)), rates


@test
def wheels_roll_without_slipping():
    s = run(7, 400)
    st = s.state()
    w = st["car"]["wheels"][0]
    assert abs(w["angle"] * w["radius"] - st["car"]["x"]) < 1e-3


@test
def something_passes_in_front_of_the_car():
    s = g.Scene(7)
    enters = 0
    for _ in range(660):
        enters += s.step({}).count("front_enter")
    assert enters >= 3, enters


@test
def the_light_ramps_rather_than_cuts():
    s = g.Scene(7)
    seen = set()
    for _ in range(660):
        s.step({})
        seen.add(round(s.light_phase(), 3))
    inner = [v for v in seen if 0.0 < v < 1.0]
    assert len(inner) > 50, len(inner)


@test
def every_layer_wraps_seamlessly_in_state():
    s = g.Scene(7)
    wraps = 0
    for _ in range(660):
        wraps += s.step({}).count("wrap")
    assert wraps >= 2, wraps


# -- replay / determinism --------------------------------------------------- #


@test
def the_same_seed_reproduces_the_same_hash_chain():
    a = [trace_line(i, s, e) for i, s, e in _chain(7)]
    b = [trace_line(i, s, e) for i, s, e in _chain(7)]
    assert a == b


@test
def two_seeds_produce_different_runs():
    a = [line for line in (trace_line(i, s, e) for i, s, e in _chain(7))]
    b = [line for line in (trace_line(i, s, e) for i, s, e in _chain(99))]
    assert a != b


def _chain(seed: int):
    s = g.Scene(seed)
    yield 0, s, []
    for _ in range(120):
        ev = s.step({})
        yield s.tick, s, ev


# -- rendering -------------------------------------------------------------- #


@test
def the_capture_schedule_is_the_starters_schedule():
    assert film.frame_ticks(660) == [i * 60 for i in range(12)]


@test
def rendering_is_reproducible_across_runs():
    s1 = run(7, 180)
    s2 = run(7, 180)
    assert film.render(s1) == film.render(s2)


@test
def a_frame_is_not_empty():
    s = run(7, 180)
    buf = film.render(s)
    assert len(set(buf[i:i + 3] for i in range(0, len(buf), 3))) > 8


def main() -> int:
    failed = 0
    for fn in TESTS:
        try:
            fn()
            print("ok   %s" % fn.__name__)
        except Exception:
            failed += 1
            print("FAIL %s" % fn.__name__)
            traceback.print_exc()
    print("%d/%d passed" % (len(TESTS) - failed, len(TESTS)))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
