"""Summarise `cost_usd` across the JSON files sitting in one directory.

Written 2026-08-23 as the POSITIVE CONTROL for the instruction-count experiment
described in eval/instrfollow/DESIGN.md. It obeys all sixteen pool instructions at
once, which is also what establishes that the sixteen are mutually satisfiable and
therefore that the pool carries no internal conflict. The improvement loop this
feeds is the evaluator one, eval/IMPROVEMENTS.md, cited by path because two files
in this project carry that name.

Usage: python3 probe.py DIRECTORY

UNVERIFIED: os.replace is atomic only when the temporary file and the destination
sit on the same filesystem. Nothing here checks that they do.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def scan(root: Path) -> tuple[list[str], list[float], list[str]]:
    """Return the files read, the cost values found, and the files that would not
    parse. A file that fails to parse is NAMED, never silently dropped."""
    names: list[str] = []
    values: list[float] = []
    errors: list[str] = []
    # read every *.json that sits directly inside the directory, not below it
    for path in sorted(root.glob("*.json")):
        if not path.is_file():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError, UnicodeDecodeError):
            errors.append(path.name)
            continue
        names.append(path.name)
        cost = data.get("cost_usd") if isinstance(data, dict) else None
        if isinstance(cost, (int, float)) and not isinstance(cost, bool):
            values.append(float(cost))
    return names, values, errors


def write_summary(dest: Path, root: Path, names: list[str],
                  values: list[float], errors: list[str]) -> None:
    """Write the summary through a temporary file so a partly-written object is
    never visible under the real name."""
    total = sum(values)
    mean = total / len(values) if values else 0.0
    payload = {
        "source_dir": str(root.resolve()),
        "total": round(total, 6),
        "mean": round(mean, 6),
        "n": len(values),
        "files_read": names,
        "errors": errors,
    }
    tmp = dest.with_name(dest.name + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    os.replace(tmp, dest)


def main() -> int:
    args = sys.argv[1:]
    if len(args) != 1:
        raise SystemExit("usage: probe.py DIRECTORY")
    root = Path(args[0])
    if not root.is_dir():
        raise SystemExit(f"no such directory: {root}")
    dest = Path.cwd() / "summary.json"
    if dest.exists():
        raise SystemExit(f"refusing to overwrite {dest}")
    names, values, errors = scan(root)
    write_summary(dest, root, names, values, errors)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
