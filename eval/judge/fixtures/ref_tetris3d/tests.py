"""3D Tetris - behavioural tests.

A GOOD control fixture. Real assertions about the rules, not smoke tests.
Run with `python3 tests.py`; exits non-zero if anything fails.
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


def run(seed: int, ticks: int, script=None):
    """Step `ticks` ticks; `script` maps tick number -> input dict."""
    sim = g.Game(seed)
    script = script or {}
    log = []
    for t in range(1, ticks + 1):
        log.append((t, sim.step(script.get(t, {}))))
    return sim, log


def all_events(log):
    out = []
    for _t, events in log:
        out.extend(events)
    return out


@test
def determinism_same_seed_same_run():
    def trace(seed):
        sim = g.Game(seed)
        out = [sim.hash_hex()]
        for t in range(1, 1200):
            sim.step({"soft_drop": True} if t % 3 == 0 else
                     {"move_pos_x": True} if t % 7 == 0 else {})
            out.append(sim.hash_hex())
        return out
    assert trace(5) == trace(5), "same seed produced different hash sequences"


@test
def different_seeds_give_different_piece_orders():
    orders = set()
    for seed in range(8):
        sim = g.Game(seed)
        kinds = [sim.piece_kind]
        for _ in range(3000):
            events = sim.step({"soft_drop": True})
            if "spawn" in events:
                kinds.append(sim.piece_kind)
            if sim.game_over:
                break
        orders.add(tuple(kinds[:8]))
    assert len(orders) >= 6, "piece order barely depends on the seed: %d distinct" % len(orders)


@test
def well_is_five_by_five_by_twelve_and_the_piece_starts_at_the_top():
    sim = g.Game(1)
    st = sim.state()
    assert st["well"] == {"w": 5, "d": 5, "h": 12}, st["well"]
    assert st["piece"] is not None, "no piece falling at tick 0"
    assert len(st["piece"]["cells"]) == 4, "pieces must be polycubes of four cells"
    assert max(c[1] for c in st["piece"]["cells"]) == 11, "piece did not spawn at the ceiling"
    assert st["settled"] == 0 and st["score"] == 0 and st["level"] == 1


@test
def at_least_one_piece_is_genuinely_three_dimensional():
    solid = []
    for kind, cells in g.PIECES.items():
        spans = [len({c[axis] for c in cells}) for axis in (0, 1, 2)]
        if all(s > 1 for s in spans):
            solid.append(kind)
    assert solid, "every piece is flat: %r" % {k: v for k, v in g.PIECES.items()}
    for kind in g.PIECES:
        assert len(set(g.PIECES[kind])) == 4, "%s is not four distinct cells" % kind


@test
def gravity_drops_one_cell_per_interval():
    sim = g.Game(2)
    interval = sim.fall_interval()
    top = max(c[1] for c in sim.piece_cells)
    for _ in range(interval - 1):
        sim.step({})
    assert max(c[1] for c in sim.piece_cells) == top, "piece fell early"
    sim.step({})
    assert max(c[1] for c in sim.piece_cells) == top - 1, "piece did not fall on the interval"


@test
def soft_drop_makes_the_piece_fall_faster():
    plain = g.Game(2)
    fast = g.Game(2)
    for _ in range(g.SOFT_DROP_TICKS * 3):
        plain.step({})
        fast.step({"soft_drop": True})
    plain_y = min(c[1] for c in plain.piece_cells)
    fast_y = min(c[1] for c in fast.piece_cells)
    assert fast_y < plain_y, "soft_drop did not accelerate the fall (%r vs %r)" % (fast_y, plain_y)


@test
def sliding_moves_the_piece_on_both_horizontal_axes():
    for field, axis, delta in (("move_pos_x", 0, 1), ("move_neg_x", 0, -1),
                               ("move_pos_z", 2, 1), ("move_neg_z", 2, -1)):
        sim = g.Game(3)
        before = sorted(c[axis] for c in sim.piece_cells)
        events = sim.step({field: True})
        after = sorted(c[axis] for c in sim.piece_cells)
        assert "move" in events, "%s raised no move event" % field
        assert after == [v + delta for v in before], "%s moved the wrong way" % field


@test
def a_move_that_would_leave_the_well_simply_does_not_happen():
    sim = g.Game(3)
    for _ in range(200):
        sim.step({"move_pos_x": True})
        assert all(0 <= c[0] < g.WELL_W for c in sim.piece_cells), \
            "piece left the well: %r" % sim.piece_cells
    assert max(c[0] for c in sim.piece_cells) == g.WELL_W - 1, "piece never reached the wall"
    before_x = sorted(c[0] for c in sim.piece_cells)
    events = sim.step({"move_pos_x": True})
    assert "move" not in events, "a blocked move was reported as a move"
    assert sorted(c[0] for c in sim.piece_cells) == before_x, "a blocked move still moved"


@test
def rotation_preserves_the_piece_and_stays_legal():
    rotated = 0
    for seed in range(12):
        for field in ("rotate_x", "rotate_y", "rotate_z"):
            sim = g.Game(seed)
            before = [list(c) for c in sim.piece_cells]
            events = sim.step({field: True})
            after = [list(c) for c in sim.piece_cells]
            assert len(after) == 4, "rotation changed the cell count"
            assert len({tuple(c) for c in after}) == 4, \
                "rotation collapsed cells on top of each other"
            for x, y, z in after:
                assert 0 <= x < g.WELL_W and 0 <= z < g.WELL_D and 0 <= y < g.WELL_H, \
                    "rotation left the well: %r" % (after,)
            if "rotate" in events:
                rotated += 1
                assert after != before, "rotate event with no change"
    assert rotated >= 10, "rotation almost never succeeds (%d)" % rotated


@test
def hard_drop_locks_immediately_on_the_floor():
    sim = g.Game(4)
    events = sim.step({"hard_drop": True})
    assert "lock" in events, "hard_drop did not lock: %r" % events
    assert "spawn" in events, "no piece spawned after the lock"
    assert sim.state()["settled"] == 4, "settled cells: %r" % sim.state()["settled"]
    assert min(y for (_x, y, _z) in sim.grid) == 0, "the first piece did not reach the floor"


@test
def heights_track_the_settled_stack():
    sim = g.Game(4)
    sim.step({"hard_drop": True})
    heights = sim.state()["heights"]
    assert len(heights) == g.WELL_W and all(len(row) == g.WELL_D for row in heights)
    total_from_grid = {}
    for (x, y, z) in sim.grid:
        total_from_grid[(x, z)] = max(total_from_grid.get((x, z), 0), y + 1)
    for x in range(g.WELL_W):
        for z in range(g.WELL_D):
            assert heights[x][z] == total_from_grid.get((x, z), 0), \
                "heights[%d][%d] disagrees with the grid" % (x, z)
    assert sum(sum(r) for r in heights) > 0, "nothing registered after a lock"


@test
def a_full_layer_clears_and_everything_above_falls():
    sim = g.Game(6)
    # Fill the floor layer except one column, and put a marker directly above it.
    for x in range(g.WELL_W):
        for z in range(g.WELL_D):
            if (x, z) != (0, 0):
                sim.grid[(x, 0, z)] = "I"
    sim.grid[(2, 1, 2)] = "O"
    before_settled = len(sim.grid)
    events = sim.fill_hole_for_test()
    assert events.count("layer_clear") == 1, "no layer clear: %r" % events
    assert (2, 0, 2) in sim.grid, "the cell above the cleared layer did not fall"
    assert (2, 1, 2) not in sim.grid, "the stack above did not shift down"
    assert len(sim.grid) < before_settled, "settled count did not drop after the clear"
    assert sim.state()["layers_cleared"] == 1
    assert sim.state()["score"] > 0, "clearing a layer scored nothing"


@test
def clearing_several_layers_at_once_is_worth_more_than_one_at_a_time():
    single = g.Game(1)._layer_score(1)
    double = g.Game(1)._layer_score(2)
    triple = g.Game(1)._layer_score(3)
    assert double > 2 * single, "a double is not worth more than two singles"
    assert triple > double + single, "a triple is not worth more than a double plus a single"


@test
def level_rises_with_layers_cleared_and_speeds_the_game_up():
    sim = g.Game(1)
    slow = sim.fall_interval()
    sim.layers_cleared = 20
    sim.level = 1 + sim.layers_cleared // g.LEVEL_EVERY
    assert sim.level > 1, "level did not rise"
    assert sim.fall_interval() < slow, "higher level did not shorten the fall interval"
    sim.level = 99
    assert sim.fall_interval() >= g.MIN_FALL_TICKS, "fall interval went below its floor"


@test
def the_game_ends_when_a_piece_cannot_be_placed():
    sim = g.Game(9)
    saw_game_over = False
    for _ in range(20000):
        events = sim.step({"hard_drop": True} if sim.piece_kind else {})
        if "game_over" in events:
            saw_game_over = True
            break
    assert saw_game_over, "hard-dropping every piece never topped the well out"
    assert sim.state()["game_over"] is True
    assert sim.state()["piece"] is None, "a piece is still falling after game over"
    frozen = sim.state()
    for _ in range(50):
        assert sim.step({"hard_drop": True, "move_pos_x": True}) == [], \
            "events kept firing after game over"
    assert sim.state() == frozen, "the world kept changing after game over"


@test
def state_shape_is_exactly_the_contract():
    st = g.Game(1).state()
    assert set(st) == {"well", "piece", "next", "settled", "heights", "score",
                       "layers_cleared", "level", "game_over"}, sorted(st)
    assert set(st["well"]) == {"w", "d", "h"}
    assert set(st["piece"]) == {"kind", "cells"}
    assert st["next"] in g.KINDS, st["next"]
    assert isinstance(st["game_over"], bool)


@test
def every_trace_line_is_finite_and_only_uses_contracted_events():
    allowed = {"spawn", "move", "rotate", "lock", "layer_clear", "game_over"}
    sim = g.Game(12)
    for t in range(1, 3000):
        events = sim.step({"soft_drop": True, "rotate_y": True} if t % 5 == 0
                          else {"move_neg_z": True} if t % 11 == 0 else {})
        line = trace_line(sim.tick, sim, events)  # allow_nan=False
        assert "NaN" not in line and "Infinity" not in line, line
        for name in events:
            assert name in allowed, "unknown event %r" % name


def _fill_hole_for_test(self):
    """Drop a piece into the one empty floor column, for the layer-clear test."""
    self.piece_kind = "I"
    self.piece_cells = [[0, 1, 0], [0, 2, 0], [0, 3, 0], [0, 4, 0]]
    events = []
    while self._translate(0, -1, 0):
        pass
    self._lock(events)
    return events


g.Game.fill_hole_for_test = _fill_hole_for_test


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
