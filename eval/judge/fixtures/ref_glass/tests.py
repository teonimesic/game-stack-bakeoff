"""s2_glass - behavioural tests. Run with `python3 tests.py`.

A GOOD control fixture. Real assertions about the scene's rules, in the three tiers the
starters use: simulation, replay/determinism, and rendering.
"""

from __future__ import annotations

import math
import sys
import traceback

import film
import game as g
from probe import trace_line

TESTS = []


def test(fn):
    TESTS.append(fn)
    return fn


def trace(seed: int, ticks: int = g.SCENE_TICKS):
    s = g.Scene(seed)
    out = [(0, s.state(), [])]
    for _ in range(ticks):
        ev = s.step({})
        out.append((s.tick, s.state(), ev))
    return out


# -- simulation ------------------------------------------------------------- #


@test
def the_water_surface_stays_level_while_the_glass_leans():
    leaned = False
    for _, st, _ in trace(7):
        if st["phase"] != "tilting":
            continue
        gu = st["glass"]["up"]
        wu = st["water"]["up"]
        if abs(gu[1]) < 0.98:
            leaned = True
        assert abs(wu[1] - 1.0) < 1e-9, wu
    assert leaned, "the glass never leaned, so nothing was tested"


@test
def what_leaves_the_glass_and_what_stays_are_the_same_water():
    for _, st, _ in trace(7):
        total = st["water"]["volume"] + st["drips"]["volume"]
        assert abs(total - g.FULL_VOLUME) < 1e-6, total


@test
def the_water_only_ever_goes_down_before_the_rewind():
    last = None
    for tick, st, _ in trace(7):
        if tick >= g.REWIND_AT:
            break
        v = st["water"]["volume"]
        if last is not None:
            assert v <= last + 1e-9, (tick, v, last)
        last = v


@test
def the_glass_breaks_into_many_pieces_that_come_to_rest():
    final = None
    for tick, st, _ in trace(7):
        if st["phase"] == "broken":
            final = st
    assert final is not None
    assert len(final["pieces"]) >= 9, len(final["pieces"])
    assert all(p["settled"] for p in final["pieces"])


@test
def a_settled_piece_never_moves_again():
    seen = {}
    for tick, st, _ in trace(7):
        if tick >= g.REWIND_AT:
            break
        for p in st["pieces"]:
            if p["settled"]:
                if p["id"] in seen:
                    assert abs(p["y"] - seen[p["id"]]) < 1e-6, p
                else:
                    seen[p["id"]] = p["y"]
    assert seen


@test
def the_sequence_returns_to_exactly_where_it_started():
    rows = trace(7)
    first, last = rows[0][1], rows[-1][1]
    assert last["phase"] == "whole"
    assert last["glass"]["intact"] is True
    assert abs(last["water"]["volume"] - first["water"]["volume"]) < 1e-9
    assert last["glass"]["up"] == first["glass"]["up"]
    assert last["pieces"] == []


@test
def every_contracted_event_fires():
    fired = set()
    for _, _, ev in trace(7):
        fired.update(ev)
    assert fired == {"drip", "tilt", "fall", "impact", "break", "settle",
                     "rewind", "whole"}, sorted(fired)


@test
def the_fracture_comes_from_the_seed():
    a = [p["x"] for p in trace(7)[g.FORWARD_END - 1][1]["pieces"]]
    b = [p["x"] for p in trace(99)[g.FORWARD_END - 1][1]["pieces"]]
    assert a and b and a != b


# -- replay / determinism --------------------------------------------------- #


@test
def the_same_seed_reproduces_the_same_hash_chain():
    assert _chain(7, 200) == _chain(7, 200)


@test
def two_seeds_produce_different_runs():
    assert _chain(7, 460) != _chain(99, 460)


def _chain(seed: int, ticks: int):
    s = g.Scene(seed)
    out = [trace_line(0, s, [])]
    for _ in range(ticks):
        ev = s.step({})
        out.append(trace_line(s.tick, s, ev))
    return out


# -- rendering -------------------------------------------------------------- #


@test
def the_capture_schedule_is_the_starters_schedule():
    assert film.frame_ticks(660) == [i * 60 for i in range(12)]


@test
def rendering_is_reproducible_across_runs():
    def at(t):
        s = g.Scene(7)
        for _ in range(t):
            s.step({})
        return film.render(s)
    assert at(120) == at(120)


@test
def the_glass_is_drawn_where_the_telemetry_says_it_is():
    s = g.Scene(7)
    for _ in range(120):
        s.step({})
    box = s.state()["glass"]["screen"]
    f = s.forward(120)
    # the box is centred on the glass's middle, and `glass.y` is where it stands
    sx, sy = g.world_to_screen(f["gx"] + g.GLASS_H * 0.5 * math.sin(f["angle"]),
                               f["gy"] + g.GLASS_H * 0.5 * math.cos(f["angle"]))
    assert abs(box["x"] - sx) < 1e-6 and abs(box["y"] - sy) < 1e-6
    # and it is entirely above the tabletop it is standing on
    assert (box["y"] + box["h"] * 0.5) * film.HEIGHT <= \
        g.world_to_screen(0.0, g.TABLE_Y)[1] * film.HEIGHT + 1.0


@test
def a_frame_is_not_empty():
    s = g.Scene(7)
    for _ in range(120):
        s.step({})
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
