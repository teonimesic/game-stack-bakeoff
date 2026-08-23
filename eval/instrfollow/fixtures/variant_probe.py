"""Cost summariser -- the VARIANT control for eval/instrfollow/DESIGN.md.

This obeys all sixteen pool instructions, and obeys almost every one of them by a
different legitimate route from gold_probe.py: single-quoted main guard, abspath
rather than resolve, explicit sys.exit codes rather than raise SystemExit, absolute
paths in the recorded lists, progress written to stderr, and the atomic replace
performed on str arguments. Measured on 2026-08-23.

A mutant asks whether a check can fail. Only a variant asks whether it can still
pass, and every false negative adjudicated in this project has been of that second
kind -- see eval/IMPROVEMENTS.md for the loop this feeds.

Usage: python3 probe.py DIRECTORY

    UNVERIFIED: whether stderr progress output is desirable at all here. It was
    chosen to exercise the stdout checker, not because anything measured it.
"""

from __future__ import annotations

import json
import os
import os.path
import sys


def collect(directory: str) -> dict:
    """Walk one directory level and pull `cost_usd` out of what parses."""
    read_paths: list[str] = []
    failed_paths: list[str] = []
    found: list[float] = []
    entries = sorted(os.listdir(directory))
    for entry in entries:
        if not entry.endswith(".json"):
            continue
        full = os.path.join(directory, entry)
        if not os.path.isfile(full):
            continue
        try:
            with open(full, encoding="utf-8") as handle:
                blob = json.load(handle)
        except (OSError, ValueError, UnicodeDecodeError) as exc:
            print(f"unparseable: {full} ({exc.__class__.__name__})", file=sys.stderr)
            failed_paths.append(full)
            continue
        read_paths.append(full)
        if isinstance(blob, dict):
            raw = blob.get("cost_usd")
            if isinstance(raw, (int, float)) and not isinstance(raw, bool):
                found.append(float(raw))
    return {"read": read_paths, "failed": failed_paths, "values": found}


def build_payload(directory: str, gathered: dict) -> dict:
    """Assemble the summary object. The population size travels with the mean."""
    values = gathered["values"]
    population = len(values)
    aggregate = math_sum(values)
    average = (aggregate / population) if population else 0.0
    return {
        "source_dir": os.path.abspath(directory),
        "total": round(aggregate, 6),
        "mean": round(average, 6),
        "n": population,
        "files_read": gathered["read"],
        "errors": gathered["failed"],
    }


def math_sum(values: list[float]) -> float:
    """Deliberately not the builtin, so the variant differs in shape as well."""
    running = 0.0
    for value in values:
        running += value
    return running


def store(payload: dict, target: str) -> None:
    """Temporary file first, then replace it into position."""
    tmp = target + ".partial"
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
    os.replace(str(tmp), str(target))


def main() -> int:
    argv = sys.argv[1:]
    if len(argv) != 1:
        print("usage: probe.py DIRECTORY", file=sys.stderr)
        sys.exit(64)
    directory = argv[0]
    if not os.path.isdir(directory):
        print(f"directory does not exist: {directory}", file=sys.stderr)
        sys.exit(2)
    target = os.path.join(os.getcwd(), "summary.json")
    if os.path.exists(target):
        print(f"summary.json is already here, refusing: {target}", file=sys.stderr)
        sys.exit(3)
    print("scanning", file=sys.stderr)
    store(build_payload(directory, collect(directory)), target)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
