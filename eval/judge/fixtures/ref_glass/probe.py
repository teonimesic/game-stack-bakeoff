"""s2_glass - probe protocol driver.

A GOOD control fixture. stdout carries nothing but JSON trace lines; every diagnostic
goes to stderr. The scene ignores input entirely - the objects are still read, one per
tick, and they exist only to advance the clock.

    python3 probe.py SEED
    python3 probe.py SEED --file TICKS SCRIPT OUT
"""

from __future__ import annotations

import json
import os
import sys

from game import Game


def trace_line(tick: int, scene: Game, events: list) -> str:
    return json.dumps(
        {"tick": tick, "hash": scene.hash_hex(), "state": scene.state(),
         "events": events},
        separators=(",", ":"),
        allow_nan=False,
    )


def parse_inputs(raw: str) -> dict:
    raw = raw.strip()
    if not raw:
        return {}
    try:
        obj = json.loads(raw)
    except ValueError:
        print("probe: ignoring unparseable input line", file=sys.stderr)
        return {}
    if not isinstance(obj, dict):
        print("probe: input line was not an object", file=sys.stderr)
        return {}
    return obj


def load_script(path: str) -> list:
    if path == "-":
        return []
    with open(path, "r", encoding="utf-8") as fh:
        doc = json.load(fh)
    inputs = doc.get("inputs", []) if isinstance(doc, dict) else []
    return [item if isinstance(item, dict) else {} for item in inputs]


def run_interactive(seed: int) -> int:
    scene = Game(seed)
    out = sys.stdout
    out.write(trace_line(0, scene, []) + "\n")
    out.flush()
    while True:
        raw = sys.stdin.readline()
        if raw == "":
            return 0
        if raw.strip() == "quit":
            return 0
        events = scene.step(parse_inputs(raw))
        out.write(trace_line(scene.tick, scene, events) + "\n")
        out.flush()


def run_file(seed: int, ticks: int, script: str, dest: str) -> int:
    scene = Game(seed)
    scripted = load_script(script)
    lines = []
    for i in range(ticks):
        events = scene.step(scripted[i] if i < len(scripted) else {})
        lines.append(trace_line(scene.tick, scene, events))
    # Atomic: a partly written trace at `dest` parses as a shorter run rather than as a
    # failure, which is the shape a reader cannot tell from a real one.
    tmp = dest + ".part"
    try:
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write("\n".join(lines))
            if lines:
                fh.write("\n")
        os.replace(tmp, dest)
    except BaseException:
        # Suppress the removal's own failure: a cleanup that raises replaces the error
        # it was tidying up after with one about the tidying.
        try:
            os.remove(tmp)
        except OSError:
            pass
        raise
    return 0


def main(argv: list) -> int:
    if not argv:
        print("usage: probe.py SEED [--file TICKS SCRIPT OUT]", file=sys.stderr)
        return 2
    seed = int(argv[0])
    if len(argv) >= 2 and argv[1] == "--file":
        if len(argv) < 5:
            print("usage: probe.py SEED --file TICKS SCRIPT OUT", file=sys.stderr)
            return 2
        return run_file(seed, int(argv[2]), argv[3], argv[4])
    return run_interactive(seed)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
