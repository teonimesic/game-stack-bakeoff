#!/usr/bin/env python3
"""Recompute the between-stack / within-stack figures a judge field is reported by.

WHY THIS EXISTS
---------------
Three live documents published "between-stack range of mean ranks 1.70, mean gap 2.05"
as the tier-3 separation result. Nothing in this repository could produce that pair, and
nothing ever had: the quantity was computed by hand, quoted forward, and then withdrawn in
one document while three others kept stating it. See FINDINGS #112.

A number with no producer cannot be re-derived, so it cannot be checked, so it survives.
This module is the producer. It is offline, free, and reads only stored judge rounds.

THE METHOD IS A PARAMETER, NOT A DETAIL
---------------------------------------
Two independent choices, and the four combinations disagree by more than the effect being
reported:

  value  score | rank      what a round asserts about a submission
  order  pool  | perround  average the rounds first, or take the spread first

`JUDGING.md`'s per-aspect table reproduces on `score` + `perround` and on nothing else,
which is how the method was identified at all. A figure quoted without its method names
one of four different quantities.

Usage, from eval/:
    python3 judge/field_ranks.py --rounds runs/<field-dir>
    python3 judge/field_ranks.py --rounds runs/<field-dir> --per-aspect
    python3 judge/field_ranks.py --selftest

Exit code is 1 if --selftest finds an expectation unmet.
"""

from __future__ import annotations

import argparse
import collections
import glob
import json
import os
import statistics
import sys
import tempfile

VALUES = ("score", "rank")
ORDERS = ("pool", "perround")


def load_rounds(d: str) -> list[dict]:
    """Every judge round in a directory, unusable ones dropped and counted by the caller.

    A round file is identified by SHAPE - it carries `submissions` and `aspect` - rather
    than by a filename pattern. Sibling files in these directories include SEQUENTIAL.json
    and GATES.json, which are summaries, not rounds; a glob on `*.json` would read them as
    fields with zero submissions and quietly widen every denominator.
    """
    out = []
    for f in sorted(glob.glob(os.path.join(d, "*.json"))):
        try:
            j = json.load(open(f, errors="replace"))
        except (json.JSONDecodeError, OSError):
            continue
        if not isinstance(j, dict) or "submissions" not in j or "aspect" not in j:
            continue
        j["_path"] = f
        out.append(j)
    return out


def _round_stats(rounds: list[dict], value: str) -> tuple[float, float]:
    """between-stack range and mean within-stack gap over ONE pooled population.

    Every submission contributes its mean across the rounds given, then a stack is the mean
    of its submissions. `within` is defined only where a stack has exactly two submissions,
    which is this project's cell shape; a stack with one is skipped rather than counted as
    a zero gap, because a gap that cannot be measured is not a gap of zero (#102).
    """
    per_sub: dict[str, list[float]] = collections.defaultdict(list)
    stack_of: dict[str, str] = {}
    for r in rounds:
        for s in r["submissions"]:
            per_sub[s["submission"]].append(float(s[value]))
            stack_of[s["submission"]] = s["stack"]
    means = {k: statistics.mean(v) for k, v in per_sub.items()}
    by_stack: dict[str, list[float]] = collections.defaultdict(list)
    for sub, m in means.items():
        by_stack[stack_of[sub]].append(m)
    stack_mean = {st: statistics.mean(v) for st, v in by_stack.items()}
    between = max(stack_mean.values()) - min(stack_mean.values())
    gaps = [abs(v[0] - v[1]) for v in by_stack.values() if len(v) == 2]
    within = statistics.mean(gaps) if gaps else float("nan")
    return between, within


def figures(rounds: list[dict], value: str, order: str) -> tuple[float, float]:
    """The reported pair under one of the four methods.

    `pool` averages every round into one population and takes the spread once. `perround`
    takes the spread inside each round and averages the spreads. They are not the same
    statistic and neither is a refinement of the other: `pool` asks how far apart the
    stacks ended up, `perround` asks how far apart a single round puts them.
    """
    usable = [r for r in rounds if r.get("usable", True)]
    if not usable:
        return float("nan"), float("nan")
    if order == "pool":
        return _round_stats(usable, value)
    pairs = [_round_stats([r], value) for r in usable]
    return (statistics.mean(p[0] for p in pairs),
            statistics.mean(p[1] for p in pairs))


def _fmt(x: float) -> str:
    return "nan" if x != x else f"{x:.4f}"


def report(rounds: list[dict], per_aspect: bool) -> None:
    usable = [r for r in rounds if r.get("usable", True)]
    dropped = len(rounds) - len(usable)
    aspects = sorted({r["aspect"] for r in usable})
    seeds = sorted({r.get("order_seed") for r in usable})
    subs = {s["submission"] for r in usable for s in r["submissions"]}
    print(f"rounds {len(usable)} usable, {dropped} dropped   "
          f"aspects {aspects}   orders {seeds}   submissions {len(subs)}")
    print()
    print(f"{'value':<7} {'order':<9} {'between':>9} {'within':>9}   reads as")
    for value in VALUES:
        for order in ORDERS:
            b, w = figures(usable, value, order)
            verdict = ("no separation" if not (b == b and w == w) or b <= w
                       else "between exceeds within")
            print(f"{value:<7} {order:<9} {_fmt(b):>9} {_fmt(w):>9}   {verdict}")
    if not per_aspect:
        return
    for value in VALUES:
        for order in ORDERS:
            print(f"\nper aspect, value={value} order={order}")
            for a in aspects:
                b, w = figures([r for r in usable if r["aspect"] == a], value, order)
                print(f"   {a:<14} between={_fmt(b):>8}  within={_fmt(w):>8}")


# ---------------------------------------------------------------- selftest


def _synth(seed: int, table: dict[str, list[float]], usable: bool = True) -> dict:
    subs = []
    for st, vals in table.items():
        for i, v in enumerate(vals):
            subs.append({"submission": f"{st}__t{i}", "stack": st,
                         "score": v, "rank": v})
    return {"aspect": "synthetic", "order_seed": seed, "usable": usable,
            "submissions": subs}


def selftest() -> int:
    """Controls, in the order they can fail.

    The expectations below are computed BY HAND from the tables, before running anything,
    because a control whose expected value comes out of the code it is testing agrees with
    every bug that code has.
    """
    unmet: list[str] = []

    def check(name: str, got, want) -> None:
        ok = (abs(got - want) < 1e-9) if isinstance(want, float) else got == want
        print(f"  [{'ok ' if ok else 'FAIL'}] {name}: got {got!r} want {want!r}")
        if not ok:
            unmet.append(name)

    # Round A stack means 4,2,3,1 -> range 3, gaps all 0 -> within 0.
    # Round B stack means 2,2,3,1 -> range 2, gaps 4,0,0,0 -> within 1.
    a = _synth(0, {"a": [4, 4], "b": [2, 2], "c": [3, 3], "d": [1, 1]})
    b = _synth(1, {"a": [0, 4], "b": [2, 2], "c": [3, 3], "d": [1, 1]})
    rounds = [a, b]

    print("1. the two orders are different statistics on the same data")
    # perround: between (3+2)/2 = 2.5 ; within (0+1)/2 = 0.5
    check("perround between", figures(rounds, "score", "perround")[0], 2.5)
    check("perround within", figures(rounds, "score", "perround")[1], 0.5)
    # pool: submission means a=2,4 b=2,2 c=3,3 d=1,1 -> stacks 3,2,3,1 -> range 2
    #       gaps 2,0,0,0 -> within 0.5
    check("pool between", figures(rounds, "score", "pool")[0], 2.0)
    check("pool within", figures(rounds, "score", "pool")[1], 0.5)
    if figures(rounds, "score", "pool")[0] == figures(rounds, "score", "perround")[0]:
        unmet.append("the two orders returned the same value on data built to separate them")

    print("2. MUTANT - a changed score must move a figure")
    m = json.loads(json.dumps(rounds))
    m[0]["submissions"][0]["score"] = 0
    if figures(m, "score", "perround") == figures(rounds, "score", "perround"):
        unmet.append("mutant: perturbing one score changed nothing")
        print("  [FAIL] mutant: perturbing one score changed nothing")
    else:
        print("  [ok ] mutant: perturbing one score moved the figures")

    print("3. VARIANT - a field statistic must not depend on submission order")
    v = json.loads(json.dumps(rounds))
    for r in v:
        r["submissions"].reverse()
    moved = [f"{value}/{order}" for value in VALUES for order in ORDERS
             if figures(v, value, order) != figures(rounds, value, order)]
    unmet += [f"variant: {m} moved when the field was permuted" for m in moved]
    print(f"  [{'FAIL' if moved else 'ok '}] "
          f"permuting the submissions left {4 - len(moved)} of 4 methods unchanged")

    print("4. an unusable round must not enter any figure")
    u = rounds + [_synth(2, {"a": [99, 99], "b": [0, 0], "c": [0, 0], "d": [0, 0]},
                         usable=False)]
    if figures(u, "score", "perround") != figures(rounds, "score", "perround"):
        unmet.append("an unusable round changed the figures")
        print("  [FAIL] an unusable round changed the figures")
    else:
        print("  [ok ] an unusable round changed nothing")

    print("5. NEGATIVE CONTROL - check 4 can fail, so its pass means something")
    u2 = json.loads(json.dumps(u))
    u2[-1]["usable"] = True
    if figures(u2, "score", "perround") == figures(rounds, "score", "perround"):
        unmet.append("marking the outlier usable changed nothing: the filter is untested")
        print("  [FAIL] marking the outlier usable changed nothing")
    else:
        print("  [ok ] marking the outlier usable moved the figures")

    print("6. load_rounds reads rounds by shape, not by filename")
    with tempfile.TemporaryDirectory() as d:
        json.dump(a, open(os.path.join(d, "g__x__seed0.json"), "w"))
        json.dump({"mode": "sequential", "measured_cost_usd": 25.55},
                  open(os.path.join(d, "SEQUENTIAL.json"), "w"))
        open(os.path.join(d, "broken.json"), "w").write("{not json")
        check("rounds loaded from a directory of mixed json", len(load_rounds(d)), 1)

    print(f"\n{len(unmet)} expectations unmet")
    for u_ in unmet:
        print(f"   UNMET: {u_}")
    return 1 if unmet else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rounds", metavar="DIR", help="a directory of stored judge rounds")
    ap.add_argument("--per-aspect", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    if not args.rounds:
        ap.error("--rounds DIR or --selftest")
    rounds = load_rounds(args.rounds)
    if not rounds:
        print(f"UNMEASURABLE: no judge rounds under {args.rounds}")
        return 1
    report(rounds, args.per_aspect)
    return 0


if __name__ == "__main__":
    sys.exit(main())
