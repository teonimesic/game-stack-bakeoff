#!/usr/bin/env python3
"""Can this suite separate the four stacks? Framed as discrimination, not ranking.

Three questions, in order of what they can rule out:

  1. Per game, what is the SPREAD across submissions? A game whose scores are
     near-identical cannot rank stacks at any trial count.
  2. Does any single CRITERION separate stacks? A game can be uninformative overall
     while one criterion does real work.
  3. Is between-stack variance larger than WITHIN-CELL variance? If the two trials
     inside a cell differ by as much as the stacks differ from each other, there is no
     ranking to report - only noise with four labels on it.

Scores are reported both RAW and ADJUDICATED. Adjudicated removes deductions traced to
harness defects rather than submission defects; without that, a stack-specific harness
bug reads as a stack difference (FINDINGS #25).
"""
from __future__ import annotations

import json, glob, statistics as st, sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from audit_criteria import (ADJUDICATED, ADJUDICATED_RUN,  # noqa: E402
                            is_harness_failure)


def _evidence(row: dict, cid: str) -> str:
    return (row.get("evidence_by_id") or {}).get(cid, "")


def _terminal_reason(run_dir: str, tid: str) -> str:
    """Read the BUILD record, not the evaluation record.

    `report.json` says how a submission scored; only the trial JSON says whether the
    agent finished or was cut off at a budget or turn cap. Those are different
    populations and pooling them produces a number that describes no trial that ran
    (FINDINGS #22) - in the one tool whose whole job is to say whether the stacks
    differ.
    """
    f = Path(run_dir) / "trials" / f"{tid}.json"
    if not f.is_file():
        return "unknown"
    try:
        return str(json.loads(f.read_text())["agent"].get("terminal_reason"))
    except (OSError, ValueError, KeyError):
        return "unknown"


def load(run_dir: str, adjudications_apply: bool):
    out = []
    for p in sorted(glob.glob(f"{run_dir}/artifacts/*/eval/report.json")):
        r = json.loads(Path(p).read_text()); tid = p.split("/")[-3]
        game, stack, t = tid.split("__")
        pb = r["playbot"]
        scored = [c for c in pb["criteria"] if c.get("scored", True)]
        # adjudicated: treat known harness-caused failures as passes
        adj_pass = sum(1 for c in scored
                       if c["passed"] or is_harness_failure(
                           tid, c["id"], c.get("evidence", ""), adjudications_apply))
        pb_adj = adj_pass / len(scored) if scored else 0.0
        pr = r["tier_scores"]["programmatic"]
        out.append({"tid": tid, "game": game, "stack": stack, "trial": t,
                    "terminal_reason": _terminal_reason(run_dir, tid),
                    "playbot_usable": bool(r.get("playbot_usable", True)),
                    "overall_raw": r["overall"],
                    "overall_adj": round(0.31 * pr + 0.69 * pb_adj, 4),
                    "prog": pr, "bot_raw": r["tier_scores"]["playbot"], "bot_adj": pb_adj,
                    "fails": [c["id"] for c in scored if not c["passed"]],
                    "evidence_by_id": {c["id"]: c.get("evidence", "")
                                       for c in scored if not c["passed"]}})
    return out


def main(run_dir: str) -> int:
    # Hand adjudications belong to ONE run; trial ids repeat across runs, so importing
    # them into another would excuse that run's genuine failures (FINDINGS #31).
    adjudications_apply = Path(run_dir).name == ADJUDICATED_RUN
    if not adjudications_apply:
        print(f"NOTE: the hand adjudications belong to {ADJUDICATED_RUN!r} and are NOT "
              f"applied here.\n      RAW and ADJUDICATED will differ only where the "
              f"evidence itself shows a harness failure.\n")
    rows = load(run_dir, adjudications_apply)

    # PARTITION BEFORE ANY SPREAD IS COMPUTED. A spread across finished and cut-off
    # trials is not a spread between stacks; and a trial whose play-bot tier measured
    # nothing contributes a 0.00 that is not a score.
    by_reason: dict[str, int] = {}
    for r in rows:
        by_reason[r["terminal_reason"]] = by_reason.get(r["terminal_reason"], 0) + 1
    excluded = [r for r in rows
                if r["terminal_reason"] != "completed" or not r["playbot_usable"]]
    if excluded:
        print("=== EXCLUDED FROM EVERY NUMBER BELOW ===")
        for r in sorted(excluded, key=lambda r: r["tid"]):
            why = (r["terminal_reason"] if r["terminal_reason"] != "completed"
                   else "play-bot tier measured nothing")
            print(f"  {r['tid']:<26} {why}")
        print(f"  terminal reasons across all {len(rows)}: {dict(sorted(by_reason.items()))}")
        print(f"  {len(rows) - len(excluded)} of {len(rows)} trials are aggregated below.\n")
        rows = [r for r in rows if r not in excluded]
    if not rows:
        print("no trial is both completed and measured; there is no spread to report")
        return 1
    # Per game, say how many stacks and trials actually survived - a "spread of 0.000"
    # over two submissions is not the same claim as one over eight.
    surviving: dict[str, set] = {}
    for r in rows:
        surviving.setdefault(r["game"], set()).add(r["stack"])
    thin = {g: sorted(v) for g, v in surviving.items() if len(v) < 4}
    if thin:
        print(f"NOTE: these games no longer have all four stacks: {thin}\n"
              f"      A spread computed over fewer stacks is not a four-way comparison.\n")
    if not rows:
        print("nothing evaluated"); return 1
    print(f"{len(rows)} evaluated\n")
    for key, label in (("overall_raw", "RAW"), ("overall_adj", "ADJUDICATED")):
        print(f"=== {label} ===")
        by_game = defaultdict(list)
        for r in rows: by_game[r["game"]].append(r)
        for g, rs in sorted(by_game.items()):
            v = [r[key] for r in rs]
            print(f"{g:<13} n={len(v):<3} mean={st.fmean(v):.4f} min={min(v):.4f} "
                  f"max={max(v):.4f} spread={max(v)-min(v):.4f}")
            # per stack within this game
            by_stack = defaultdict(list)
            for r in rs: by_stack[r["stack"]].append(r[key])
            cells = {s: v2 for s, v2 in by_stack.items() if len(v2) >= 1}
            line = "  ".join(f"{s}={st.fmean(v2):.3f}" for s, v2 in sorted(cells.items()))
            print(f"              {line}")
            # within-cell vs between-stack
            within = [abs(v2[0] - v2[1]) for v2 in by_stack.values() if len(v2) == 2]
            means = [st.fmean(v2) for v2 in by_stack.values()]
            if within and len(means) > 1:
                w = st.fmean(within); b = max(means) - min(means)
                verdict = ("NO RANKING - within-cell differences are as large as "
                           "between-stack" if w >= b else
                           "between-stack exceeds within-cell")
                print(f"              mean within-cell diff={w:.4f}  "
                      f"between-stack range={b:.4f}  -> {verdict}")
        print()
    print("=== does any single criterion separate stacks? ===")
    per = defaultdict(lambda: defaultdict(int))
    stacks_seen = defaultdict(set)
    for r in rows:
        for c in r["fails"]:
            per[c][r["stack"]] += 1
        for c in per: pass
        stacks_seen["all"].add(r["stack"])
    if not per:
        print("  no criterion failed any submission - none can separate anything")
    for c, d in sorted(per.items()):
        # `all(... or True)` was here, which is `all(True)` - the label was printed
        # unconditionally, asserting that every failure of every criterion was a harness
        # defect no matter what the evidence said. A fail-open reporting bug: it excuses
        # real failures and shows no anomaly (FINDINGS #31). Now it asks the question.
        failing = [r for r in rows if c in r["fails"]]
        evidence_of = {r["tid"]: _evidence(r, c) for r in failing}
        adjudged = bool(failing) and all(
            is_harness_failure(tid, c, ev, adjudications_apply)
            for tid, ev in evidence_of.items())
        print(f"  {c:<26} fails on {dict(sorted(d.items()))}"
              f"{'   [all adjudicated harness defects]' if adjudged else ''}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1
                          else "runs/wg-matrix-2026-08-13T14-02-50"))
