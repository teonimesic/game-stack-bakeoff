"""DELIBERATELY FAKE CONTROL FIXTURE - do not treat this as a real game.

The probe protocol here is genuine: it speaks the exact wire format, one JSON
line per tick, diagnostics on stderr. What it is driving is not - see game.py.
The seed is parsed and then ignored, and the input lines are parsed and then
ignored.

    python3 probe.py SEED
    python3 probe.py SEED --file TICKS SCRIPT OUT
"""

from __future__ import annotations

import json
import sys

from game import Game


def trace_line(tick: int, game: Game, events: list) -> str:
    return json.dumps(
        {"tick": tick, "hash": game.hash_hex(), "state": game.state(), "events": events},
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
    return {k: bool(v) for k, v in obj.items()}


def load_script(path: str) -> list:
    if path == "-":
        return []
    with open(path, "r", encoding="utf-8") as fh:
        doc = json.load(fh)
    inputs = doc.get("inputs", []) if isinstance(doc, dict) else []
    out = []
    for item in inputs:
        out.append({k: bool(v) for k, v in item.items()} if isinstance(item, dict) else {})
    return out


def run_interactive(seed: int) -> int:
    game = Game(seed)
    out = sys.stdout
    out.write(trace_line(0, game, []) + "\n")
    out.flush()
    while True:
        raw = sys.stdin.readline()
        if raw == "":
            return 0
        if raw.strip() == "quit":
            return 0
        events = game.step(parse_inputs(raw))
        out.write(trace_line(game.tick, game, events) + "\n")
        out.flush()


def run_file(seed: int, ticks: int, script: str, dest: str) -> int:
    game = Game(seed)
    scripted = load_script(script)
    lines = []
    for i in range(ticks):
        inputs = scripted[i] if i < len(scripted) else {}
        events = game.step(inputs)
        lines.append(trace_line(game.tick, game, events))
    with open(dest, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
        if lines:
            fh.write("\n")
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
