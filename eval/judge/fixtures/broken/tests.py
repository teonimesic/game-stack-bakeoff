"""DELIBERATELY BROKEN CONTROL FIXTURE - do not treat this as a real game.

One trivial test that passes, so `just test` and `just verify` are green while
nothing whatsoever is being verified.

Run with `python3 tests.py`.
"""

from __future__ import annotations

import sys
import traceback

import game as g

TESTS = []


def test(fn):
    TESTS.append(fn)
    return fn


@test
def the_tick_counter_counts():
    sim = g.Game(0)
    sim.step({})
    assert sim.tick == 1


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
