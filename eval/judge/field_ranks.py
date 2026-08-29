#!/usr/bin/env python3
"""Recompute the between-stack / within-stack figures a judge field is reported by.

WHY THIS EXISTS
---------------
Three live documents published "between-stack range of mean ranks 1.70, mean gap 2.05"
as the tier-3 separation result. Nothing in this repository could produce that pair, and
nothing ever had: the quantity was computed by hand, quoted forward, and then withdrawn in
one document while three others kept stating it. See FINDINGS #113.

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
A directory of rounds is not automatically one population, and three different things can put a
round outside it.

`fun_frames` is `fun`'s CONTROL - the same question with the telemetry withheld - and its
scores mean something only against `fun`'s. Pooling it with the scored aspects is rule 4
exactly: a mean over a population that is heterogeneous by construction. On
`runs/wg-aspect-reliability` that was 30 rounds of which 5 were the control, silently, and the
guard against it lived in a comment (task 90).

`idiomatic` and `framework_fluency` are CROSS-STACK BARRED (`Aspect.cross_stack_bar`). Their
scores are commensurable with everything else; what is meaningless is reading them ACROSS
stacks, because the judge is told which stack each submission is. A pooled figure here is a
between-stack range, so a barred round inside it is the barred reading with extra steps. The
bar has been in `JUDGING.md` and `RUBRIC.md` since #53 and in code since task 135; the pooled
figure ignored it until task 146.

So: `assert_poolable` refuses any population mixing a control or a barred aspect with another
aspect, an aspect id `aspects.py` does not define is UNMEASURABLE rather than assumed scored,
and every figure printed here names the aspects it is over.

The third property is the RUN. A submission id is a name WITHIN a run (#70) and so is a game
(#80), and `_by_stack` joins by submission id ACROSS rounds, so rounds from two runs in one
directory pool two different games' work into one per-submission mean. `assert_one_run`
refuses any directory whose rounds carry disagreeing `run` fields and lists the rounds that
carry none (they predate the provenance fields and cannot answer); `field_sweep.assert_out_run`
asks the same question at the sweep end, before anything is written or paired.

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
from field_sweep import warn_rounds_without_provenance  # noqa: E402

VALUES = ("score", "rank")
ORDERS = ("pool", "perround")

#: The four things a round's aspect id can be, and only the first may be pooled with others.
SCORED, CONTROL, BARRED, UNKNOWN = "scored", "control", "barred", "unknown"


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
    """`SCORED`, `CONTROL`, `BARRED` or `UNKNOWN` for one round's aspect id.

    Read from `aspects.ASPECTS`, never from a list here: a membership list in this file is
    a second source of truth that the next aspect silently falsifies (#38).

    `BARRED` is `Aspect.cross_stack_bar`, and it is a SEPARATE exclusion rather than a
    flavour of the control one. A control's scores are not commensurable with the aspect it
    controls. A barred aspect's scores are perfectly commensurable; what is meaningless is
    the BETWEEN-STACK reading of them, because the judge was told which stack it was looking
    at. Both land out of the pool and the reasons are printed separately, because a reader
    handed one reason for the other draws the wrong conclusion about what the aspect
    measures.

    `CONTROL` outranks `BARRED` on an aspect that is somehow both: a control is not a
    published opinion at all, so its own bar is moot. No aspect is both today.
    """
    aspect = ASPECTS.get(aspect_id or "")
    if aspect is None:
        return UNKNOWN
    if aspect.control_for:
        return CONTROL
    return BARRED if aspect.cross_stack_bar else SCORED


def partition(rounds: list[dict]) -> dict[str, list[dict]]:
    """Rounds split four ways by what their aspect is. Every key always present."""
    out: dict[str, list[dict]] = {SCORED: [], CONTROL: [], BARRED: [], UNKNOWN: []}
    for r in rounds:
        out[classify(r.get("aspect"))].append(r)
    return out


def assert_poolable(rounds: list[dict]) -> None:
    """Raise unless these rounds are one population. THIS IS THE GUARD, and it is here.

    Two shapes are legitimate and everything else is not:

      * every round shares ONE aspect id AND `aspects.py` defines it - the per-aspect case.
        A control alone is fine, and so is a barred aspect alone; reading either on its own
        is the entire point of having it. What neither may do is contribute to a figure over
        several aspects.
      * more than one aspect, ALL of them scored - the cross-aspect case a pooled figure
        is supposed to be.

    AN UNKNOWN ID IS REFUSED EVEN ALONE, and that is why the check on it comes first. The
    exemption for a lone aspect rests on knowing what that aspect is: a control's figure is
    read against its treatment, a barred aspect's per-stack means are read within a stack.
    For an id `aspects.py` does not define, neither is established - so there is no reading
    its figure has, and returning one would be the same defect the multi-aspect branch
    refuses, one aspect smaller.

    It lives in `figures()` rather than in `report()` on purpose. `report` is one caller;
    the resource being guarded is "a pooled figure", and a guard placed beside one caller
    is a guard the next caller does not have (rule 13).
    """
    ids = {r.get("aspect") for r in rounds}
    unknown = sorted(str(i) for i in ids if classify(i) == UNKNOWN)
    if unknown:
        raise ValueError(
            f"refusing to compute a figure for {unknown}: no such aspect in aspects.py, so "
            f"whether it is a control, a barred aspect or a scored opinion cannot be "
            f"established, and neither can what a figure over it would mean."
        )
    if len(ids) <= 1:
        return
    bad = sorted(str(i) for i in ids if classify(i) != SCORED)
    if bad:
        why = {CONTROL: "a control", BARRED: "cross-stack barred"}
        named = ", ".join(f"{i} is {why[classify(i)]}" for i in bad)
        raise ValueError(
            f"refusing to pool {len(ids)} aspects together: {named}. "
            f"A control's scores mean something only against the aspect it controls; and a "
            f"cross-stack-barred aspect's scores mean something only within a stack, while a "
            f"pooled figure is a between-stack reading. "
            f"Pool the scored aspects, or take one aspect at a time."
        )


def _round_label(r: dict) -> str:
    """One nameable line for a round: its file when it was loaded from disk."""
    p = r.get("_path")
    if p:
        return os.path.basename(str(p))
    return f"{r.get('aspect')}/seed{r.get('order_seed')}"


def assert_one_run(rounds: list[dict]) -> list[dict]:
    """Rounds CARRYING `run` must agree on it; rounds without are returned, to warn.

    #70: a submission id is a name WITHIN a run, and #80 the same for a game -
    `g2_tetris3d` alone is four stored fields in different states of repair. `_by_stack`
    joins by submission id ACROSS rounds, so two runs in one directory pool two
    different games' work into one per-submission mean, and every figure reads that as
    one population (rule 4). Every round written since 2026-08-22 carries `run` (#80's
    fix at the source); this is the analysis-side consumer of it, and it refuses the mix
    rather than trusting the operator to have noticed.

    A round carrying NO `run` is a THIRD value, not a disagreement: 10 of 10 rounds in
    `wg-tetris-judge-2026-08-17/pre` predate the field, and refusing them would make
    this tool unable to read the very corpus the withdrawn register points operators at
    (WR-tier3-pair's `replaced_by` names it). They are returned for the caller to list.
    Fail closed on what a round CAN answer and answers differently; warn on what it
    cannot answer at all (rule 7's direction, not its exception).

    Like `assert_poolable`, this lives at the resource rather than beside one caller:
    `figures()` refuses, so no future caller of a pooled figure re-derives the question.
    """
    carried: dict[str, list[dict]] = collections.defaultdict(list)
    absent: list[dict] = []
    for r in rounds:
        run = r.get("run")
        if run:
            carried[str(run)].append(r)
        else:
            absent.append(r)
    if len(carried) > 1:
        named = "; ".join(
            f"{run} <- {', '.join(_round_label(r) for r in rs)}"
            for run, rs in sorted(carried.items()))
        raise ValueError(
            f"refusing to pool rounds from {len(carried)} different runs: {named}. "
            f"A submission id names different work in each run (#70) and so does a "
            f"game (#80), and _by_stack joins by submission id across rounds, so this "
            f"directory is not one population and no figure over it has a reading. "
            f"Split the directory by run.")
    return absent


def _by_stack(rounds: list[dict], value: str) -> dict[str, list[float]]:
    """Each stack's submission means, keyed by stack, in ALPHABETICAL order.

    Deliberately not sorted by value: this is the shape a CROSS-STACK BARRED aspect is
    reported in, and sorting it by score would hand the reader the ranking the bar
    exists to withhold.
    """
    per_sub: dict[str, list[float]] = collections.defaultdict(list)
    stack_of: dict[str, str] = {}
    for r in rounds:
        for s in r["submissions"]:
            per_sub[s["submission"]].append(float(s[value]))
            stack_of[s["submission"]] = s["stack"]
    means = {k: statistics.mean(v) for k, v in per_sub.items()}
    out: dict[str, list[float]] = {}
    for sub in sorted(means):
        out.setdefault(stack_of[sub], []).append(means[sub])
    return {k: out[k] for k in sorted(out)}


def _round_stats(rounds: list[dict], value: str) -> tuple[float, float]:
    """between-stack range and mean within-stack gap over ONE pooled population.

    Every submission contributes its mean across the rounds given, then a stack is the mean
    of its submissions. `within` is defined only where a stack has exactly two submissions,
    which is this project's cell shape; a stack with one is skipped rather than counted as
    a zero gap, because a gap that cannot be measured is not a gap of zero (#102).
    """
    by_stack = _by_stack(rounds, value)
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
    assert_one_run(usable)
    if order == "pool":
        return _round_stats(usable, value)
    pairs = [_round_stats([r], value) for r in usable]
    return (statistics.mean(p[0] for p in pairs),
            statistics.mean(p[1] for p in pairs))


def _fmt(x: float) -> str:
    return "nan" if x != x else f"{x:.4f}"


def _ids(rounds: list[dict]) -> list[str]:
    return sorted({str(r.get("aspect")) for r in rounds})


def report(rounds: list[dict], per_aspect: bool, out_dir: Path | None = None) -> int:
    """Print the four readings over the SCORED aspects, naming what was and was not pooled.

    Returns 1 when nothing is poolable, because a directory whose every round is a control
    or an unrecognised aspect is unmeasurable by this tool, not zero-separation.

    `out_dir` is the directory the rounds were loaded from, when there was one: the
    provenance warning is then the existing `warn_rounds_without_provenance` listing
    (re-read from disk, so it covers the directory the OPERATOR named, not merely the
    rounds this call was handed). Without it, the rounds `assert_one_run` returned are
    named instead - the same warning from the loaded objects. Prints nothing when every
    round carries its provenance, which is why a fully-provenanced directory's report is
    byte-identical to what it was before the run guard existed.
    """
    usable = [r for r in rounds if r.get("usable", True)]
    dropped = len(rounds) - len(usable)
    # THE RUN GUARD, BEFORE ANY OUTPUT. A mixed-run directory refused here never
    # prints a half table, and the per-stack joins below never see one either.
    absent_run = assert_one_run(usable)
    parts = partition(usable)
    pooled = parts[SCORED]
    seeds = sorted({r.get("order_seed") for r in usable})
    subs = {s["submission"] for r in usable for s in r["submissions"]}
    print(f"rounds {len(usable)} usable, {dropped} dropped   "
          f"orders {seeds}   submissions {len(subs)}")

    # THE WARN-ABSENT HALF: rounds that predate the provenance fields cannot answer the
    # run question at all. Listed, never refused (#86) - the tetris-judge corpus the
    # withdrawn register cites is entirely of this kind. Silent when empty, so a
    # fully-provenanced directory reports byte-identically to before the guard existed.
    if out_dir is not None:
        missing = warn_rounds_without_provenance(out_dir)
    else:
        missing = [f"{_round_label(r)}: no run" for r in absent_run]
    for line in missing:
        print(f"NO PROVENANCE: {line}")
    if missing:
        print(f"NO PROVENANCE: {len(missing)} round(s) predate the provenance fields "
              f"(#86) and cannot say which run they judged; figures over them have no "
              f"nameable population.")

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
    for aspect_id in _ids(parts[BARRED]):
        n = sum(1 for r in parts[BARRED] if r.get("aspect") == aspect_id)
        print(f"NOT POOLED: {aspect_id} - cross-stack barred [{n} rounds]. A pooled figure "
              f"is a BETWEEN-STACK reading, which is the one reading this aspect's bar "
              f"withholds. Its per-stack means are below.")
    for aspect_id in _ids(parts[UNKNOWN]):
        n = sum(1 for r in parts[UNKNOWN] if r.get("aspect") == aspect_id)
        print(f"NOT POOLED: {aspect_id} - no such aspect in aspects.py [{n} rounds]. "
              f"Whether it is a control cannot be established, so it is unmeasurable here.")

    # A CROSS-STACK BARRED ASPECT IS REPORTED PER STACK, HERE, beside every figure this
    # tool prints for it. The bar is not a refusal to compute: the aspect's OWN `between`
    # and `within` are still shown under `--per-aspect`, because published tables reproduce
    # from them and JUDGING.md's per-aspect table quotes `idiomatic`'s pair with the bar
    # stated next to it. What it does refuse is a POOLED figure containing the aspect -
    # that figure is a between-stack reading and is exactly what the bar withholds
    # (task 146). Until 2026-08-24 the bar was printed here and the rounds were pooled
    # anyway, which documented the contradiction instead of removing it.
    #
    # The per-stack means are printed in ALPHABETICAL order, never sorted by value: a
    # sorted list is the ranking the bar exists to withhold.
    for aspect_id in _ids(usable):
        bar = ASPECTS[aspect_id].cross_stack_bar if aspect_id in ASPECTS else ""
        if not bar:
            continue
        rows = [r for r in usable if r.get("aspect") == aspect_id]
        print(f"CROSS-STACK BARRED: {aspect_id} - {bar}")
        for value in VALUES:
            means = {st: round(statistics.mean(v), 4)
                     for st, v in _by_stack(rows, value).items()}
            print(f"    per stack, {value}: " +
                  "  ".join(f"{st}={m}" for st, m in means.items()))

    # THE POOLED FIGURE AND THE PER-ASPECT TABLE ARE INDEPENDENT, and a directory that has
    # no poolable population still has per-aspect readings. Returning early here would have
    # thrown away the ONE reading a barred-only field legitimately has, which is the shape
    # this tool exists to protect (task 146). Exit 1 reports the missing pooled figure; it
    # does not mean nothing was measured.
    if pooled:
        print()
        print(f"{'value':<7} {'order':<9} {'between':>9} {'within':>9}   reads as "
              f"(over {', '.join(_ids(pooled))})")
        for value in VALUES:
            for order in ORDERS:
                b, w = figures(pooled, value, order)
                verdict = ("no separation" if not (b == b and w == w) or b <= w
                           else "between exceeds within")
                print(f"{value:<7} {order:<9} {_fmt(b):>9} {_fmt(w):>9}   {verdict}")
    else:
        print("\nUNMEASURABLE: no scored-aspect round to pool.")

    if per_aspect:
        for value in VALUES:
            for order in ORDERS:
                print(f"\nper aspect, value={value} order={order}")
                for a in _ids(usable):
                    # NO ROW OF NUMBERS FOR AN ID aspects.py DOES NOT DEFINE. A figure
                    # carrying a warning label is still a figure, and this table is where
                    # a reader comes for one number. `assert_poolable` refuses these, so
                    # the alternative to skipping the call is a traceback mid-table.
                    if classify(a) == UNKNOWN:
                        print(f"   {a:<18} between={'-':>8}  within={'-':>8}"
                              "  (unknown, unmeasurable)")
                        continue
                    b, w = figures([r for r in usable if r.get("aspect") == a],
                                   value, order)
                    tag = {CONTROL: "  (control, excluded above)"}.get(classify(a), "")
                    # The bar again, on the row itself. A reader who scrolls to this table
                    # for one number must not have to have read the header to know that
                    # this `between` is not a ranking.
                    if a in ASPECTS and ASPECTS[a].cross_stack_bar:
                        tag += "  (CROSS-STACK BARRED - excluded above, read per stack)"
                    print(f"   {a:<18} between={_fmt(b):>8}  within={_fmt(w):>8}{tag}")
    return 0 if pooled else 1


# ---------------------------------------------------------------- selftest


#: The synthetic rounds carry REAL aspect ids, read from `aspects.py` rather than spelled
#: here, so the classification path the guard depends on is the one under test. A fixture
#: with an invented id would exercise `UNKNOWN` for every check and prove nothing about the
#: split that matters (rule 12: the address is an input to the check).
#:
#: All three go through `classify`, not through the `Aspect` fields directly. Spelling the
#: predicate a second time here is what let `_A_SCORED` hold two BARRED aspects while the
#: guard was being written to exclude them - a fixture disagreeing with the function it is
#: testing agrees with every bug that function has.
_A_SCORED = sorted(i for i in ASPECTS if classify(i) == SCORED)
_A_CONTROL = sorted(i for i in ASPECTS if classify(i) == CONTROL)
_A_BARRED = sorted(i for i in ASPECTS if classify(i) == BARRED)


def _synth(seed: int, table: dict[str, list[float]], usable: bool = True,
           aspect: str | None = None, run: str | None = None) -> dict:
    subs = []
    for st, vals in table.items():
        for i, v in enumerate(vals):
            subs.append({"submission": f"{st}__t{i}", "stack": st,
                         "score": v, "rank": v})
    return {"aspect": aspect or _A_SCORED[0], "order_seed": seed, "usable": usable,
            "run": run, "submissions": subs}


def selftest(runs_root: Path | None = None) -> int:
    """Controls, in the order they can fail.

    The expectations below are computed BY HAND from the tables, before running anything,
    because a control whose expected value comes out of the code it is testing agrees with
    every bug that code has.

    `runs_root` names a stored `eval/runs/` tree for the CORPUS pins at the end. Without
    it they are skipped and the output says so (`NOT RUN`) - a skipped pin is a stated
    non-measurement, never a pass (rule 12: without the flag a worktree's gitignored,
    empty `eval/runs` would make every corpus row a confident zero).
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
    # AND IT IS REFUSED EVEN ALONE. The lone-aspect exemption rests on knowing what the
    # aspect is; for an id aspects.py does not define, nothing is established, so there is
    # no reading its figure has. Caught by review on PR #24: `--per-aspect` printed a row
    # of numbers for it three lines under the word UNMEASURABLE.
    try:
        figures([stranger], "score", "pool")
        unmet.append("figures() returned a figure for a lone unknown aspect id")
        print("  [FAIL] figures() computed a figure for a lone unknown aspect")
    except ValueError as exc:
        print(f"  [ok ] a lone unknown aspect is refused: {str(exc)[:60]}...")
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        report(rounds + [stranger], per_aspect=True)
    text = buf.getvalue()
    check("--per-aspect prints no numbers for it",
          "retired_aspect_id  between=       -  within=       -" in text, True)
    check("and the scored rows still carry theirs",
          f"{_A_SCORED[0]:<18} between=  3.0000" in text, True)

    print("14. a cross-stack barred aspect is reported PER STACK, with its reason")
    # `_A_BARRED[0]` is read from `aspects.py`, not spelled here, for the same reason
    # `_A_SCORED` is: a fixture with an invented id would exercise `UNKNOWN` and prove
    # nothing about the branch that matters (rule 12).
    barred_id = _A_BARRED[0]
    # Stack means 4, 2, 3, 1: distinct, so a per-stack line that printed the same number
    # for every stack, or dropped one, is visible rather than hidden by ties.
    barred = _synth(0, {"a": [4, 4], "b": [2, 2], "c": [3, 3], "d": [1, 1]},
                    aspect=barred_id)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        report([barred], per_aspect=True)
    text = buf.getvalue()
    check("the bar is named in the output",
          f"CROSS-STACK BARRED: {barred_id}" in text, True)
    check("and carries its reason, not just the label",
          ASPECTS[barred_id].cross_stack_bar[:40] in text, True)
    check("the per-stack means are printed, alphabetically",
          "per stack, score: a=4.0  b=2.0  c=3.0  d=1.0" in text, True)
    check("the per-aspect row carries the bar too",
          "(CROSS-STACK BARRED - excluded above, read per stack)" in text, True)

    # MUTANT. Clearing the declaration must remove the whole report, or the output was
    # not being driven by the field at all. This is the state `idiomatic` was in from
    # #53 until 2026-08-24: barred in two prose documents and in no line of any output.
    saved = ASPECTS[barred_id]
    ASPECTS[barred_id] = dataclasses.replace(saved, cross_stack_bar="")
    try:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            report([barred], per_aspect=True)
        check("MUTANT: with the bar cleared, nothing says so",
              "CROSS-STACK BARRED" in buf.getvalue(), False)
    finally:
        ASPECTS[barred_id] = saved
    check("the live declaration is restored",
          bool(ASPECTS[barred_id].cross_stack_bar), True)

    # VARIANT. Not a removal: a field where one stack has ONE submission rather than two.
    # `within` is undefined there (#102) and `_by_stack` must still report that stack's
    # mean, because the per-stack report is the thing a barred aspect is read by and
    # silently dropping an arm from it is worse than an unmeasurable gap.
    odd = _synth(0, {"a": [4, 4], "b": [2, 2], "c": [3, 3], "d": [1]}, aspect=barred_id)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        report([odd], per_aspect=False)
    check("VARIANT: a one-submission stack still appears in the per-stack line",
          "per stack, score: a=4.0  b=2.0  c=3.0  d=1.0" in buf.getvalue(), True)

    print("15. a cross-stack barred aspect is EXCLUDED FROM THE POOL, like a control")
    # The pooled figure is a BETWEEN-STACK reading, which is the one reading the bar
    # withholds. Printing the bar beside the figure while the barred rounds are inside it
    # documents the contradiction rather than removing it (task 146).
    #
    # The table is the loud one used for the control in check 10, so the two exclusions
    # are measured against the same hand-computed numbers: pooled, `between` moves off
    # 2.0000 to 2.3333.
    barred_loud = _synth(4, {"a": [0, 0], "b": [0, 0], "c": [0, 0], "d": [9, 9]},
                         aspect=barred_id)
    mixed_barred = rounds + [barred_loud]
    try:
        figures(mixed_barred, "score", "pool")
        unmet.append("figures() pooled a cross-stack-barred aspect with scored ones")
        print("  [FAIL] figures() pooled the barred aspect silently")
    except ValueError as exc:
        print(f"  [ok ] figures() raised: {str(exc)[:70]}...")
    # and the barred aspect ALONE is still measurable - that is the per-stack reading.
    try:
        figures([barred_loud], "score", "pool")
        print("  [ok ] the barred aspect on its own is still measurable")
    except ValueError:
        unmet.append("the barred aspect alone was refused: its per-stack reading is lost")
        print("  [FAIL] the barred aspect alone was refused")
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = report(mixed_barred, per_aspect=False)
    text = buf.getvalue()
    check("report exit code with a barred aspect present", rc, 0)
    check("report names it as excluded, with the reason",
          f"NOT POOLED: {barred_id} - cross-stack barred" in text, True)
    check("report pooled only the two scored aspects",
          f"POOLED over 2 scored aspect(s): {_A_SCORED[0]}, {_A_SCORED[1]}" in text, True)
    check("report printed the scored-only pool figures",
          "   2.0000    0.5000" in text, True)

    print("16. MUTANT - pooling the barred aspect changes the answer, so it acts")
    polluted = _round_stats([r for r in mixed_barred if r.get("usable", True)], "score")[0]
    check("pooling it moves `between` off 2.0", round(polluted, 4), 2.3333)

    print("17. MUTANT - with the bar cleared, the aspect is pooled and the guard stops")
    #     Patching `ASPECTS` rather than `classify`, for check 11's reason: it proves the
    #     verdict is read from `aspects.py` and not from a constant baked in here.
    saved = ASPECTS[barred_id]
    ASPECTS[barred_id] = dataclasses.replace(saved, cross_stack_bar="")
    try:
        moved = figures(mixed_barred, "score", "pool")[0]
        fired = False
    except ValueError:
        moved, fired = None, True
    finally:
        ASPECTS[barred_id] = saved
    if fired:
        unmet.append("mutant: the guard still fired with the bar cleared - it is not "
                     "reading cross_stack_bar")
        print("  [FAIL] the guard fired on a population with no barred aspect in it")
    else:
        check("the un-barred aspect is pooled, and the figure moves",
              round(moved, 4), 2.3333)
    check("the live classification is restored", classify(barred_id), BARRED)

    print("18. VARIANT - a directory holding ONLY barred aspects is unmeasurable, not 0")
    #     Rule 15. Not a removal: a real field that ran nothing but barred aspects has a
    #     per-stack reading and no pooled one, and the difference must be visible.
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc_barred_only = report([barred_loud], per_aspect=False)
    text = buf.getvalue()
    check("a barred-only directory exits 1, not 0", rc_barred_only, 1)
    check("and says so", "UNMEASURABLE" in text, True)
    check("while still printing the per-stack means the bar permits",
          "per stack, score: a=0.0  b=0.0  c=0.0  d=9.0" in text, True)

    # ---- the run guard (#70, #80, task 205) --------------------------------------
    #
    # `_by_stack` joins every round in the directory by SUBMISSION ID across all rounds.
    # A submission id is a name within a run (#70) and so is a game (#80: four stored
    # `g2_tetris3d` fields in different states of repair), so rounds from two runs in one
    # directory pool two different games' work into one per-submission mean. `run` has
    # been in every round since 2026-08-22; this is the consumer that reads it.
    #
    # THREE values, not two: carried-and-agreeing is measurable, carried-and-disagreeing
    # is refused, carrying nothing is a WARNING - 10 of 10 rounds in
    # `wg-tetris-judge-2026-08-17/pre` predate the field, and refusing them would make
    # this tool unable to read the very corpus the withdrawn register points operators
    # at (WR-tier3-pair's `replaced_by` names it).
    print("19. VARIANT - rounds carrying ONE run are measurable, exactly as before")
    same_run = [dict(a, run="wg-run-one"), dict(b, run="wg-run-one")]
    check("same-run pool between", figures(same_run, "score", "pool")[0], 2.0)
    check("same-run pool within", figures(same_run, "score", "pool")[1], 0.5)
    absent = assert_one_run(same_run)
    check("no round was treated as absent", absent, [])
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = report(same_run, per_aspect=False)
    check("same-run directory exits 0", rc, 0)
    check("and prints no provenance warning",
          "NO PROVENANCE" in buf.getvalue(), False)

    print("20. REFUSAL - rounds carrying DIFFERENT runs are refused, fail-closed")
    mixed_runs = [dict(a, run="wg-run-one"), dict(b, run="wg-run-other")]
    try:
        figures(mixed_runs, "score", "pool")
        unmet.append("figures() pooled two rounds naming different runs")
        print("  [FAIL] figures() pooled rounds from two runs silently")
    except ValueError as exc:
        print(f"  [ok ] figures() raised: {str(exc)[:70]}...")
        check("the refusal names both runs",
              "wg-run-one" in str(exc) and "wg-run-other" in str(exc), True)
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            report(mixed_runs, per_aspect=False)
        unmet.append("report() printed a table over rounds from two runs")
        print("  [FAIL] report() reported a mixed-run directory")
    except ValueError:
        check("report() refused before printing ANY output", buf.getvalue(), "")
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            report(mixed_runs, per_aspect=True)
        unmet.append("report(--per-aspect) reported a mixed-run directory")
        print("  [FAIL] --per-aspect reported a mixed-run directory")
    except ValueError:
        check("--per-aspect refuses too (the per-stack join has the same key)",
              buf.getvalue(), "")

    print("21. MUTANT - pooling the two runs would move the figure, so the guard acts")
    #     Hand-computed from the two tables (check 1's `pool` reading): the join puts
    #     a__t0 at (4+0)/2=2, so stacks land 3,2,3,1 -> between 2.0, within 0.5 -
    #     against 3.0/0.0 for round `a` alone. The numbers are the defect: a plausible
    #     table over two different games' work.
    polluted = _round_stats(mixed_runs, "score")
    check("the joined reading is a plausible-looking 2.0/0.5",
          (round(polluted[0], 4), round(polluted[1], 4)), (2.0, 0.5))
    # Neuter the guard the way a refactor would - quietly - and the mixed population
    # must come back with a figure. `figures` reads the module global, so patching it
    # here proves the refusal is this function's verdict and not a syntactic accident.
    live_guard = assert_one_run
    globals()["assert_one_run"] = lambda rounds: []
    try:
        unguarded = figures(mixed_runs, "score", "pool")
    finally:
        globals()["assert_one_run"] = live_guard
    check("MUTANT: the neutered guard lets the mixed figure through",
          (round(unguarded[0], 4), round(unguarded[1], 4)), (2.0, 0.5))
    check("the live guard is restored", globals()["assert_one_run"] is live_guard, True)

    print("22. VARIANT - a round carrying NO run is a third value, not a disagreement")
    one_carried = [dict(a, run="wg-run-one"), b]
    absent = assert_one_run(one_carried)
    check("the run-less round is returned as absent", len(absent), 1)
    check("it is round b", absent and absent[0] is b, True)
    check("one carried run + one absent is still measurable",
          figures(one_carried, "score", "pool")[0], 2.0)

    print("23. the warn listing is the existing warn_rounds_without_provenance listing")
    with tempfile.TemporaryDirectory() as d:
        json.dump(b, open(os.path.join(d, "g__fun__seed0.json"), "w"))
        loaded = load_rounds(d)
        absent = assert_one_run(loaded)
        check("the run-less stored round is absent, not refused", len(absent), 1)
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = report(loaded, per_aspect=False, out_dir=Path(d))
        text = buf.getvalue()
        check("report exits 0 on a run-less directory", rc, 0)
        check("the listing is the existing function's line",
              "NO PROVENANCE: g__fun__seed0.json: no run" in text, True)
    # and the library path (no directory given) names the loaded rounds themselves
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        report(one_carried, per_aspect=False)
    check("without a directory the loaded rounds are named",
          "NO PROVENANCE" in buf.getvalue(), True)

    print("24. CORPUS - the tetris-judge corpus stays readable (needs --runs-root)")
    if runs_root is None:
        print("  [NOT RUN] pass --runs-root <main checkout>/eval/runs; skipped is "
              "stated, never silently green")
    else:
        d = runs_root / "wg-tetris-judge-2026-08-17" / "pre"
        if not d.is_dir():
            unmet.append(f"corpus pin: {d} does not exist")
            print(f"  [FAIL] {d} does not exist")
        else:
            loaded = load_rounds(str(d))
            absent = assert_one_run(loaded)
            check("0 of its rounds carry run, none refused", len(absent), 10)
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                rc = report(loaded, per_aspect=False, out_dir=d)
            text = buf.getvalue()
            check("the corpus report exits 0", rc, 0)
            check("all 10 rounds are listed as without run",
                  sum(1 for ln in text.splitlines() if ": no run" in ln), 10)
            check("the published rank+pool pair still reproduces",
                  "   1.3125    2.5625" in text, True)

    print(f"\n{len(unmet)} expectations unmet")
    for u_ in unmet:
        print(f"   UNMET: {u_}")
    return 1 if unmet else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rounds", metavar="DIR", help="a directory of stored judge rounds")
    ap.add_argument("--per-aspect", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--runs-root", type=Path, default=None, metavar="DIR",
                    help="a stored eval/runs/ tree for the selftest's corpus pins; "
                         "without it they print NOT RUN rather than passing")
    args = ap.parse_args()
    if args.selftest:
        return selftest(args.runs_root)
    if not args.rounds:
        ap.error("--rounds DIR or --selftest")
    rounds = load_rounds(args.rounds)
    if not rounds:
        print(f"UNMEASURABLE: no judge rounds under {args.rounds}")
        return 1
    try:
        return report(rounds, args.per_aspect, out_dir=Path(args.rounds))
    except ValueError as exc:
        # The guards raise; the CLI reports. A traceback would still fail closed, but
        # a refusal that names its reason is one the operator can act on.
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
