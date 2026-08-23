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

THE POPULATION IS ALSO A PARAMETER
----------------------------------
A directory of rounds is not automatically one population. `fun_frames` is `fun`'s CONTROL
- the same question with the telemetry withheld - and its scores mean something only against
`fun`'s. Pooling it with the scored aspects is rule 4 exactly: a mean over a population that
is heterogeneous by construction. On `runs/wg-aspect-reliability` that was 30 rounds of which
5 were the control, silently, and the guard against it lived in a comment (task 90).

So: `assert_poolable` refuses any population mixing a control with another aspect, an aspect
id `aspects.py` does not define is UNMEASURABLE rather than assumed scored, and every figure
printed here names the aspects it is over.

Usage, from eval/:
    python3 judge/field_ranks.py --rounds runs/<field-dir>
    python3 judge/field_ranks.py --rounds runs/<field-dir> --per-aspect
    python3 judge/field_ranks.py --selftest

Exit code is 1 if --selftest finds an expectation unmet, and 1 if a directory holds no
round this tool is willing to pool.
"""

from __future__ import annotations

import argparse
import collections
import contextlib
import dataclasses
import glob
import io
import json
import os
import statistics
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from aspects import ASPECTS  # noqa: E402

VALUES = ("score", "rank")
ORDERS = ("pool", "perround")

#: The three things a round's aspect id can be, and only the first may be pooled with others.
SCORED, CONTROL, UNKNOWN = "scored", "control", "unknown"


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


def classify(aspect_id: str | None) -> str:
    """`SCORED`, `CONTROL` or `UNKNOWN` for one round's aspect id.

    Read from `aspects.ASPECTS`, never from a list here: a membership list in this file is
    a second source of truth that the next aspect silently falsifies (#38).
    """
    aspect = ASPECTS.get(aspect_id or "")
    if aspect is None:
        return UNKNOWN
    return CONTROL if aspect.control_for else SCORED


def partition(rounds: list[dict]) -> dict[str, list[dict]]:
    """Rounds split three ways by what their aspect is. Every key always present."""
    out: dict[str, list[dict]] = {SCORED: [], CONTROL: [], UNKNOWN: []}
    for r in rounds:
        out[classify(r.get("aspect"))].append(r)
    return out


def assert_poolable(rounds: list[dict]) -> None:
    """Raise unless these rounds are one population. THIS IS THE GUARD, and it is here.

    Two shapes are legitimate and everything else is not:

      * every round shares ONE aspect id - the per-aspect case. A control alone is fine;
        judging it against its treatment is the entire point of having one.
      * more than one aspect, ALL of them scored - the cross-aspect case a pooled figure
        is supposed to be.

    It lives in `figures()` rather than in `report()` on purpose. `report` is one caller;
    the resource being guarded is "a pooled figure", and a guard placed beside one caller
    is a guard the next caller does not have (rule 13).
    """
    ids = {r.get("aspect") for r in rounds}
    if len(ids) <= 1:
        return
    bad = sorted(str(i) for i in ids if classify(i) != SCORED)
    if bad:
        raise ValueError(
            f"refusing to pool {len(ids)} aspects together: {bad} "
            f"{'is a control or unknown' if len(bad) == 1 else 'are controls or unknown'}. "
            f"A control's scores mean something only against the aspect it controls, and an "
            f"aspect id aspects.py does not define cannot be shown to be either. "
            f"Pool the scored aspects, or take one aspect at a time."
        )


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
    assert_poolable(usable)
    if order == "pool":
        return _round_stats(usable, value)
    pairs = [_round_stats([r], value) for r in usable]
    return (statistics.mean(p[0] for p in pairs),
            statistics.mean(p[1] for p in pairs))


def _fmt(x: float) -> str:
    return "nan" if x != x else f"{x:.4f}"


def _ids(rounds: list[dict]) -> list[str]:
    return sorted({str(r.get("aspect")) for r in rounds})


def report(rounds: list[dict], per_aspect: bool) -> int:
    """Print the four readings over the SCORED aspects, naming what was and was not pooled.

    Returns 1 when nothing is poolable, because a directory whose every round is a control
    or an unrecognised aspect is unmeasurable by this tool, not zero-separation.
    """
    usable = [r for r in rounds if r.get("usable", True)]
    dropped = len(rounds) - len(usable)
    parts = partition(usable)
    pooled = parts[SCORED]
    seeds = sorted({r.get("order_seed") for r in usable})
    subs = {s["submission"] for r in usable for s in r["submissions"]}
    print(f"rounds {len(usable)} usable, {dropped} dropped   "
          f"orders {seeds}   submissions {len(subs)}")

    # WHICH ASPECTS A POOLED FIGURE IS OVER, printed whether or not anything was excluded.
    # Stating it only when something is dropped makes its absence ambiguous between "nothing
    # was excluded" and "this build does not check".
    print(f"POOLED over {len(_ids(pooled))} scored aspect(s): "
          f"{', '.join(_ids(pooled)) or '(none)'}   [{len(pooled)} rounds]")
    for aspect_id in _ids(parts[CONTROL]):
        n = sum(1 for r in parts[CONTROL] if r.get("aspect") == aspect_id)
        print(f"NOT POOLED: {aspect_id} - control for {ASPECTS[aspect_id].control_for} "
              f"[{n} rounds]. Read it against {ASPECTS[aspect_id].control_for}, "
              f"never added to it.")
    for aspect_id in _ids(parts[UNKNOWN]):
        n = sum(1 for r in parts[UNKNOWN] if r.get("aspect") == aspect_id)
        print(f"NOT POOLED: {aspect_id} - no such aspect in aspects.py [{n} rounds]. "
              f"Whether it is a control cannot be established, so it is unmeasurable here.")

    if not pooled:
        print("\nUNMEASURABLE: no scored-aspect round to pool.")
        return 1

    print()
    print(f"{'value':<7} {'order':<9} {'between':>9} {'within':>9}   reads as "
          f"(over {', '.join(_ids(pooled))})")
    for value in VALUES:
        for order in ORDERS:
            b, w = figures(pooled, value, order)
            verdict = ("no separation" if not (b == b and w == w) or b <= w
                       else "between exceeds within")
            print(f"{value:<7} {order:<9} {_fmt(b):>9} {_fmt(w):>9}   {verdict}")
    if not per_aspect:
        return 0
    for value in VALUES:
        for order in ORDERS:
            print(f"\nper aspect, value={value} order={order}")
            for a in _ids(usable):
                b, w = figures([r for r in usable if r.get("aspect") == a], value, order)
                tag = {CONTROL: "  (control, excluded above)",
                       UNKNOWN: "  (unknown, excluded above)"}.get(classify(a), "")
                print(f"   {a:<14} between={_fmt(b):>8}  within={_fmt(w):>8}{tag}")
    return 0


# ---------------------------------------------------------------- selftest


#: The synthetic rounds carry REAL aspect ids, read from `aspects.py` rather than spelled
#: here, so the classification path the guard depends on is the one under test. A fixture
#: with an invented id would exercise `UNKNOWN` for every check and prove nothing about the
#: split that matters (rule 12: the address is an input to the check).
_A_SCORED = sorted(i for i in ASPECTS if not ASPECTS[i].control_for)
_A_CONTROL = sorted(i for i in ASPECTS if ASPECTS[i].control_for)


def _synth(seed: int, table: dict[str, list[float]], usable: bool = True,
           aspect: str | None = None) -> dict:
    subs = []
    for st, vals in table.items():
        for i, v in enumerate(vals):
            subs.append({"submission": f"{st}__t{i}", "stack": st,
                         "score": v, "rank": v})
    return {"aspect": aspect or _A_SCORED[0], "order_seed": seed, "usable": usable,
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
    # Two DIFFERENT scored aspects, so checks 1-5 run down the cross-aspect branch of
    # `assert_poolable` rather than the single-aspect early return.
    a = _synth(0, {"a": [4, 4], "b": [2, 2], "c": [3, 3], "d": [1, 1]}, aspect=_A_SCORED[0])
    b = _synth(1, {"a": [0, 4], "b": [2, 2], "c": [3, 3], "d": [1, 1]}, aspect=_A_SCORED[1])
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

    # ---- the control must not be absorbed by a pooled figure (task 90) ----------------
    #
    # THE FIRST CHECK IS THAT THERE IS A CONTROL AT ALL, and it is stated rather than
    # assumed. Everything from here down is built out of `_A_CONTROL[0]`; if `aspects.py`
    # marks nothing, an `IndexError` would end the run with a traceback that reads as a
    # broken selftest instead of as the defect this task exists for - which is exactly
    # what it did when run against the pre-task tree.
    print("7. aspects.py marks at least one aspect as a control")
    check("controls declared in ASPECTS", len(_A_CONTROL) >= 1, True)
    if not _A_CONTROL:
        unmet.append("NO ASPECT SETS control_for: nothing can be excluded from a pooled "
                     "figure, and checks 8-11 below did not run")
        print("  [FAIL] no aspect sets control_for - the guard has nothing to read. "
              "This is the task-90 defect: the exclusion is a comment again.")
        print(f"\n{len(unmet)} expectations unmet")
        for u_ in unmet:
            print(f"   UNMET: {u_}")
        return 1

    # The control round is built to be LOUD: stack d at 9 where every other round puts it
    # last. If the exclusion were decorative the figures would move visibly, which is what
    # check 10 measures rather than assumes.
    control = _synth(3, {"a": [0, 0], "b": [0, 0], "c": [0, 0], "d": [9, 9]},
                     aspect=_A_CONTROL[0])
    mixed = rounds + [control]

    print("8. the guard refuses a population mixing a control with a scored aspect")
    try:
        figures(mixed, "score", "pool")
        unmet.append("figures() pooled a control with scored aspects without complaint")
        print("  [FAIL] figures() pooled the control silently")
    except ValueError as exc:
        print(f"  [ok ] figures() raised: {str(exc)[:70]}...")
    # and a control ALONE is legitimate - it is what `--per-aspect` asks for.
    try:
        figures([control], "score", "pool")
        print("  [ok ] the control on its own is still measurable")
    except ValueError:
        unmet.append("the control alone was refused: --per-aspect cannot report it")
        print("  [FAIL] the control alone was refused")

    print("9. report() drops the control, and SAYS which aspects it pooled")
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = report(mixed, per_aspect=False)
    text = buf.getvalue()
    check("report exit code with a control present", rc, 0)
    check("report pooled only the scored rounds",
          len(partition(mixed)[SCORED]), 2)
    check("report names the pooled aspects",
          f"POOLED over 2 scored aspect(s): {_A_SCORED[0]}, {_A_SCORED[1]}" in text, True)
    check("report names the excluded control",
          f"NOT POOLED: {_A_CONTROL[0]} - control for "
          f"{ASPECTS[_A_CONTROL[0]].control_for}" in text, True)
    # the printed pair must be the scored-only pair, hand-computed above as 2.0 / 0.5
    check("report printed the scored-only pool figures",
          ("   2.0000    0.5000" in text), True)

    print("10. MUTANT - pooling the control changes the answer, so the exclusion acts")
    #    stack means with the control pooled: a=2.0 b=1.3333 c=2.0 d=3.6667 -> between
    #    2.3333, against 2.0000 without it. Computed by hand from the three tables.
    polluted = _round_stats([r for r in mixed if r.get("usable", True)], "score")[0]
    check("pooling the control moves `between` off 2.0", round(polluted, 4), 2.3333)
    if abs(polluted - 2.0) < 1e-9:
        unmet.append("mutant: pooling the control changed nothing - the exclusion is inert")

    print("11. MUTANT - with the control reclassified as scored, the guard stops firing")
    #     Patching `ASPECTS` rather than `classify` on purpose: `classify` reads the dict
    #     at call time, so this proves the guard's verdict comes from `aspects.py` and not
    #     from a constant baked in here.
    saved = ASPECTS[_A_CONTROL[0]]
    ASPECTS[_A_CONTROL[0]] = dataclasses.replace(saved, control_for="")
    try:
        moved = figures(mixed, "score", "pool")[0]
        fired = False
    except ValueError:
        moved, fired = None, True
    finally:
        ASPECTS[_A_CONTROL[0]] = saved
    if fired:
        unmet.append("mutant: the guard still fired with nothing marked as a control - "
                     "it is not reading control_for")
        print("  [FAIL] the guard fired on a population with no control in it")
    else:
        check("the un-marked control is pooled, and the figure moves",
              round(moved, 4), 2.3333)
    check("the live classification is restored", classify(_A_CONTROL[0]), CONTROL)

    print("12. VARIANT - one scored aspect absent must stay green, not look like a control")
    #     Rule 15: the mutants above remove the mechanism. This is an input the check was
    #     not built for - a field that simply never ran one of its aspects. Four rounds,
    #     four different scored aspects, identical tables: stack means 4,2,3,1 -> between
    #     3.0, gaps all 0 -> within 0.0.
    present = [i for i in _A_SCORED if i != _A_SCORED[2]]
    partial = [_synth(i, {"a": [4, 4], "b": [2, 2], "c": [3, 3], "d": [1, 1]}, aspect=aid)
               for i, aid in enumerate(present)]
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = report(partial, per_aspect=False)
    text = buf.getvalue()
    check("a field missing one scored aspect still reports", rc, 0)
    check("it pools exactly the aspects present",
          f"POOLED over {len(present)} scored aspect(s): {', '.join(sorted(present))}"
          in text, True)
    check("no aspect was reported as excluded", "NOT POOLED" in text, False)
    check("partial-field between", figures(partial, "score", "pool")[0], 3.0)
    check("partial-field within", figures(partial, "score", "pool")[1], 0.0)

    print("13. an aspect id aspects.py does not define is unmeasurable, not scored")
    stranger = _synth(9, {"a": [9, 9], "b": [0, 0], "c": [0, 0], "d": [0, 0]},
                      aspect="retired_aspect_id")
    check("classified as unknown", classify("retired_aspect_id"), UNKNOWN)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = report(rounds + [stranger], per_aspect=False)
    text = buf.getvalue()
    check("the unknown aspect is named and excluded",
          "NOT POOLED: retired_aspect_id - no such aspect" in text, True)
    check("its scores did not enter the pool", "   2.0000    0.5000" in text, True)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc_only = report([stranger], per_aspect=False)
    check("a directory of nothing poolable exits 1, not 0", rc_only, 1)
    check("and says so", "UNMEASURABLE" in buf.getvalue(), True)

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
    return report(rounds, args.per_aspect)


if __name__ == "__main__":
    sys.exit(main())
