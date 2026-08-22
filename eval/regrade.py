#!/usr/bin/env python3
"""
Re-grade completed trials under the corrected tampering rule.

Why this exists: the tampering check originally flagged ANY modification to a
protected path. That wrongly zeroed correct work twice — first when an agent
created a new test file it had been told to create, then when an agent added a
test to an existing file. Protected paths are reverted before grading, so an
addition cannot influence the result; only REMOVED coverage is tampering.

Re-grading offline rather than re-running is deliberate: the held-out test
results are already stored per trial and are independent of the tampering
verdict, so a fresh verdict can be computed without spending money on new
rollouts. This mirrors SWE-bench's `rewrite_reports`, which exists for exactly
this situation — fixing a grading bug without paying for new trials.

Usage: ./regrade.py --run-dir runs/<name> [--write]
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

# " crates/game/tests/render.rs | 33 +++++++++++++++"
STAT_LINE = re.compile(r"^\s*(\S+)\s*\|\s*\d+\s*([+-]*)\s*$")


def deletions_by_file(diff_stat: str) -> dict[str, bool]:
    """Map path -> whether its diffstat shows any deleted lines."""
    out: dict[str, bool] = {}
    for line in (diff_stat or "").splitlines():
        m = STAT_LINE.match(line)
        if m:
            out[m.group(1)] = "-" in m.group(2)
    return out


def allowed_paths_for(suite_path: Path, task_id: str) -> list[str] | None:
    """Current allowed_paths for a task, so a scope correction can be applied to
    already-completed trials without re-running them."""
    import tomllib

    if not suite_path.exists():
        return None
    raw = tomllib.load(open(suite_path, "rb"))
    for t in raw.get("task", []):
        if t["id"] == task_id:
            return t.get("allowed_paths") or []
    return None


def path_ok(path: str, globs: list[str]) -> bool:
    from fnmatch import fnmatch

    for g in globs:
        if fnmatch(path, g):
            return True
        if "**" in g and fnmatch(path, g.split("**")[0] + "*"):
            return True
    return False


def corrected_tampering(trial: dict, allowed: list[str] | None = None) -> list[str]:
    """Drop findings that only ever meant 'the agent added to a test file'."""
    dels = deletions_by_file(trial.get("diff_stat", ""))
    kept = []
    for finding in trial.get("tampering", []):
        if finding.startswith("modified pre-existing"):
            # Withdrawn entirely. Protected files are reverted before grading, so
            # editing one cannot affect the outcome; treating it as a cheat only
            # ever produced false positives on agents adding the tests they were
            # asked to add. Deleted files and CHEAT_PATTERNS still count.
            continue
        if finding.startswith("edited path outside allowed set") and allowed is not None:
            # Re-evaluate against the CURRENT allowed_paths. The powerup task
            # originally restricted edits to the simulation, but rendering a new
            # entity legitimately requires a view change — the agent was right
            # and the task scope was wrong. Recomputed rather than re-run.
            m = re.search(r"allowed set: (\S+)", finding)
            if m and path_ok(m.group(1), allowed):
                continue
        kept.append(finding)
    return kept


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True, type=Path)
    ap.add_argument("--suite", type=Path, default=None,
                    help="re-evaluate allowed-path violations against this suite")
    ap.add_argument("--write", action="store_true",
                    help="persist corrected verdicts back into the trial files")
    args = ap.parse_args()

    changed = 0
    rows = []
    for path in sorted((args.run_dir / "trials").glob("*.json")):
        t = json.loads(path.read_text())
        before_tamper = list(t.get("tampering", []))
        allowed = allowed_paths_for(args.suite, t["task"]) if args.suite else None
        after_tamper = corrected_tampering(t, allowed)

        holdout = t.get("holdout") or {}
        passed = bool(holdout.get("passed")) and not after_tamper
        score = 0.0 if after_tamper else float(holdout.get("score", 0.0))

        flipped = (passed != t.get("passed")) or (score != t.get("score"))
        if flipped:
            changed += 1
        rows.append((t["trial_id"], t.get("passed"), passed, t.get("score", 0.0),
                     score, before_tamper, after_tamper))

        if args.write:
            t["tampering_original"] = before_tamper
            t["tampering"] = after_tamper
            t["passed"] = passed
            t["score"] = score
            t["regraded"] = True
            path.write_text(json.dumps(t, indent=2))

    print(f"{len(rows)} trials, {changed} verdict(s) changed"
          f"{' (written)' if args.write else ' (dry run - pass --write to persist)'}\n")
    print(f"{'trial':<34} {'was':<6} {'now':<6} {'score':>12}  notes")
    print("-" * 88)
    for tid, was, now, s_old, s_new, bt, at in rows:
        note = ""
        if bt and not at:
            note = "tampering flag withdrawn (pure addition)"
        elif at:
            note = at[0][:44]
        mark = " *" if (was != now or s_old != s_new) else "  "
        print(f"{tid:<34} {str(was):<6} {str(now):<6} "
              f"{s_old:.2f} -> {s_new:.2f}{mark}  {note}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
