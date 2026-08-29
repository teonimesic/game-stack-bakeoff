#!/usr/bin/env python3
"""What a judge sweep COST, against what its own summary file says it cost.

WHY THIS EXISTS
---------------
`field_sweep.py` writes one number, `measured_cost_usd`, into `SEQUENTIAL.json`,
`GATES.json` and `REPRODUCIBILITY.json`. That number is a **ceiling counter for one
invocation**, not the cost of the field: a round already on disk was paid for by an
earlier invocation and deliberately contributes 0 so it cannot be counted twice
against today's `--max-cost`. The behaviour is correct. The name is not, and three live
documents read it as spend.

Measured 2026-08-29 by `python3 judge/judge_ledger.py --tree runs/` from `eval/`: 12
sweep directories, 5 of whose summary counters under-report, by 69.93 tokval in total.
The
`wg-tetris-judge-2026-08-17` field is the worst case and the one that reached print - see
FINDINGS #121.

So this module reports **two numbers that are not the same question**, and never one:

  field_cost_usd          what the rounds stored in this directory cost, summed from
                          each round's own `cost_usd`. The artifacts of record.
  charged_to_ceiling_usd  what the last invocation spent, i.e. the counter that
                          `--max-cost` is enforced against.

THE GAP IS THE INTERESTING PART, AND IT HAS A SIGN
--------------------------------------------------
  gap > 0   the sweep was resumed: rounds already on disk cost money on some earlier day
            and are not in this invocation's counter. Expected, benign, and it must be
            EXPLAINED - the carried-over rounds are a prefix of the execution order, so
            some subset of the stored rounds must sum to the gap. A gap that matches no
            subset is spend nobody can attribute.

  gap < 0   the counter saw money that no stored round accounts for. That is not an
            accounting quirk, it is a MISSING ARTIFACT: a round was paid for and its file
            is gone. It has happened - 13.16 tokval of `g1_pong` round-1 calls are recorded in
            `eval/RUNS.md` and exist nowhere on disk (task 04, closed by re-running them).

A ROUND WITH NO COST IS NOT A ZERO
----------------------------------
`cost_usd` absent or null on a stored round is carried as None, counted in `n_rounds`,
excluded from `field_cost_usd`, and NAMED - per directory by `audit`/`report`. The
total is the sum of the rounds that state a cost and is low by an unknown amount
wherever the warning prints; the alternative, folding the absence in as 0.0, is how a
ledger under-reports (FINDINGS #121). Warned, never refused: the corpus stays readable
and no exit code turns on the absence alone. Measured 2026-08-29: 0 of 97 stored
rounds affected, so latent.

AND THE SUBSET SEARCH IS BOUNDED
--------------------------------
`explain_gap`'s fallback enumerates all 2^n subsets, and `--tree` reaches it on any
directory with a positive gap and no clean mtime split. Past `SUBSET_SEARCH_MAX` rounds
the search is refused and the directory reports UNSEARCHED - red, naming the gap as
unattributed and the search as not run - instead of hanging the cited producer. The
mtime split, which is O(n^2) and the method that means something, still runs first and
is still preferred where it separates.

Usage, from eval/:
    python3 judge/judge_ledger.py --tree runs/
    python3 judge/judge_ledger.py --dir runs/wg-tetris-judge-2026-08-17/post
    python3 judge/judge_ledger.py --selftest

Exit code is 1 if any directory is MISSING ARTIFACT, UNEXPLAINED or UNSEARCHED, or if
--selftest finds an expectation unmet. A resumed sweep is not an error and does not set
it.
"""

from __future__ import annotations

import argparse
import contextlib
import glob
import io
import itertools
import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

import tokenvalue  # noqa: E402

#: Summary files a sweep writes beside its rounds. These are NOT rounds and must never be
#: counted as ones - each mode writes a different name, which is why this is a set rather
#: than the one filename whichever mode you happened to be looking at wrote.
SUMMARY_STEMS = ("SEQUENTIAL", "GATES", "REPRODUCIBILITY")
SUMMARIES = tuple(f"{s}.json" for s in SUMMARY_STEMS)


def is_summary(basename: str) -> bool:
    """Is this a sweep summary - canonical, or a superseded copy of one?

    A summary is append-only from 2026-08-23 (task 63): re-running a sweep into a
    directory keeps the record it replaces as `REPRODUCIBILITY-<stamp>.json` rather than
    destroying it. Those siblings are summaries too, and a name test that knew only the
    three canonical names would hand every one of them to `load_rounds` as a candidate
    round.

    It would survive that today only because `load_rounds` ALSO tests the shape. A check
    that is correct because a second, unrelated check happens to cover it is one edit away
    from being wrong, and the edit would show up as a widened denominator rather than as
    an error.
    """
    if not basename.endswith(".json"):
        return False
    stem = basename[: -len(".json")]
    return any(stem == s or stem.startswith(s + "-") for s in SUMMARY_STEMS)

#: Keys under which a summary may carry the invocation counter. The old name is read
#: because every stored summary uses it; the new one is written from 2026-08-23.
COUNTER_KEYS = ("charged_to_ceiling_usd", "measured_cost_usd")

#: Cent-level. Summaries store `round(spent, 2)`, so an exact match cannot be demanded of
#: a sum carrying full float precision.
EPS = 0.005

#: Seconds of mtime separation below which an "older/newer" split is not evidence of
#: anything. `wg-tetris-judge-2026-08-17/pre` was moved out of a `/private/tmp` sweep
#: directory with `cp`, so its ten rounds carry mtimes 0.0006 s apart IN ALPHABETICAL
#: ORDER - a perfectly clean split that reports the copy, not the run. The shortest judge
#: round in the stored tree ran 246 s (`eval/RUNS.md`), so any real boundary between a
#: carried-over round and a freshly written one is minutes wide.
MIN_SPLIT_S = 60.0

#: Rounds at which the exact subset-sum fallback REFUSES instead of running. The search
#: enumerates all 2^n subsets and `--tree` walks every round-holding directory, so this
#: bound is what stands between a future ~30-round directory and a hang. Measured 2026-08-29
#: on the worst case - a gap no subset fits, so the enumeration runs to completion:
#: 0.09 s at 18 rounds, 0.39 s at 20, 1.64 s at 22, 6.82 s at 24, doubling per +2 rounds;
#: ~30 rounds projects to minutes and past ~32 to hours. 24 caps the worst case near 7 s
#: per directory, and the largest real sweep the corpus holds is 11 rounds. A directory
#: over the bound reports UNSEARCHED - red, because an unattributed gap is what this
#: module exists to name - and the mtime split, O(n^2) and unbounded, still runs first
#: and still answers where it separates.
SUBSET_SEARCH_MAX = 24


def load_rounds(d: str) -> list[dict]:
    """Every stored judge round in one directory, identified by SHAPE.

    A round carries `submissions` and `aspect`; a summary does not. Globbing `*.json` and
    trusting the filename is how `GATES.json` gets read as a field with zero submissions -
    the same defect `field_ranks.load_rounds` was written to avoid.

    AN UNUSABLE ROUND IS STILL COUNTED. `usable: false` means the judge returned something
    the gates reject; the call was made and the money left the account. A cost ledger that
    drops failures reports the bill it wishes it had.

    SO IS A CONTROL ASPECT'S ROUND, for the same reason and it is not an oversight.
    `field_ranks` excludes `fun_frames` from every pooled SCORE because a control's scores
    are only meaningful against its treatment's (task 90). A dollar is a dollar whatever the
    aspect asked, so do not carry that exclusion across to here.

    AND SO IS A ROUND WHOSE cost_usd IS ABSENT OR NULL - but not as 0.0. The `or 0.0`
    this carried until 2026-08-29 read every such round as free: exactly the fallback
    shape `read_counter`'s docstring refuses one function up ("Returns None rather than
    0.0 ... 0.0 would read as agreement"), applied to the other number, and an
    under-reporting ledger is worse than none (FINDINGS #121). The absence is carried
    as None, named by `audit`/`report`, and excluded from the total there - a stated
    non-measurement, not a zero. A recorded 0.0 is a measurement and stays 0.0.
    Measured 2026-08-29: 0 of 97 stored rounds are affected, so latent.
    """
    out = []
    for f in sorted(glob.glob(os.path.join(d, "*.json"))):
        if is_summary(os.path.basename(f)):
            continue
        try:
            j = json.load(open(f, errors="replace"))
        except (OSError, json.JSONDecodeError):
            continue
        if isinstance(j, dict) and "submissions" in j and "aspect" in j:
            j["_path"] = f
            j["_mtime"] = os.path.getmtime(f)
            c = j.get("cost_usd")
            j["_cost"] = float(c) if isinstance(c, (int, float)) else None
            out.append(j)
    return out


def _split_costs(rounds: list[dict]) -> tuple[float, list[str]]:
    """`(total, no_cost_names)` over one directory's rounds - the ONE copy of the sum.

    The total is over the rounds that STATE a `cost_usd`; `no_cost_names` names the
    rounds that state none, absent key and null value alike, so the caller can print
    the exclusion instead of folding it in. A recorded 0.0 is a stated zero: summed,
    and not in the names.
    """
    total = sum(r["_cost"] for r in rounds if r["_cost"] is not None)
    no_cost = [os.path.basename(r["_path"]) for r in rounds if r["_cost"] is None]
    return total, no_cost


def field_cost(d: str) -> tuple[int, float, list[str]]:
    """`(n_rounds, total, no_cost_names)` for a directory."""
    rounds = load_rounds(d)
    total, no_cost = _split_costs(rounds)
    return len(rounds), total, no_cost


def field_cost_usd(d: str) -> tuple[int, float]:
    """`(n_rounds, total)` for a directory. The write path in `field_sweep` calls this.

    Deliberately shared rather than reimplemented: a ledger tool that computes the number
    one way and a harness that records it another way is two accountings again, which is
    the entire defect this module exists for.

    The total is `_split_costs`' - over the rounds that state a cost. A round whose
    cost_usd is absent or null is counted in `n_rounds`, excluded from `total`, and
    named by `audit`/`report` when the directory is read back.
    """
    rounds = load_rounds(d)
    total, _names = _split_costs(rounds)
    return len(rounds), total


def read_counter(d: str) -> tuple[str | None, float | None]:
    """The invocation counter and which file carried it, or `(None, None)`.

    Returns None rather than 0.0 when no summary exists. A directory of rounds with no
    summary is unjudged, not free, and `0.0` would read as agreement - rule 3's sibling,
    a fallback that turns an absence into a plausible in-range number.

    ONLY THE CANONICAL NAMES ARE READ, and that is the whole reason the summaries take
    the ROLLING append-only shape rather than the pinned one `suite.json` uses. This
    function's question is "what did the LAST invocation charge to its ceiling", against
    which the gap to `field_cost_usd` is the carried-over prefix. Pin the canonical name
    to the FIRST invocation instead and the gap becomes the SUFFIX, which `explain_gap`
    looks for at the head and cannot find - every resumed sweep would come back
    UNEXPLAINED and exit 1. See `tools/manifest.py` for the two shapes.
    """
    for name in SUMMARIES:
        p = os.path.join(d, name)
        if not os.path.exists(p):
            continue
        try:
            j = json.load(open(p, errors="replace"))
        except (OSError, json.JSONDecodeError):
            continue
        for k in COUNTER_KEYS:
            if isinstance(j, dict) and isinstance(j.get(k), (int, float)):
                return name, float(j[k])
    return None, None


def explain_gap(rounds: list[dict], gap: float) -> tuple[str, list[str]]:
    """Which stored rounds account for a positive gap.

    TWO METHODS, IN THIS ORDER, BECAUSE THE FIRST IS THE ONE THAT MEANS SOMETHING.

    1. An mtime split SEPARATED BY MORE THAN `MIN_SPLIT_S`. Carried-over rounds are
       minutes older than the ones this invocation wrote, so if the k oldest rounds sum to
       the gap and there is a real time boundary after them, that is the resume,
       demonstrated rather than fitted.

       THE SEPARATION IS THE WHOLE CHECK, AND THE FIRST VERSION DID NOT HAVE IT. A `cp`
       of a sweep directory rewrites every mtime, sub-millisecond apart, in the order the
       shell expanded the glob - which is alphabetical, which is also the execution order
       of `--sequential`. That produces a clean, ordered, entirely meaningless split, and
       on `wg-tetris-judge-2026-08-17/pre` it produced the RIGHT ANSWER for the wrong
       reason. A method that is correct by coincidence on the case you built it for is
       rule 12 with the address being a timestamp.

    2. Exact subset sum, when mtimes cannot separate them. Weaker evidence: a subset can
       fit by coincidence, so more than one fit is reported as AMBIGUOUS rather than
       resolved.

       BOUNDED at `SUBSET_SEARCH_MAX` rounds, past which the search is refused and the
       directory reports UNSEARCHED: the enumeration is 2^n, `--tree` reaches it on any
       directory with a positive gap and no clean mtime split, and a tool that hangs
       names nothing. A cost that states None cannot claim the gap either way, so both
       methods run over the rounds that state a cost only - which changes nothing where
       every round states one.
    """
    searchable = [r for r in rounds if r["_cost"] is not None]
    by_t = sorted(searchable, key=lambda r: (r["_mtime"], r["_path"]))
    for k in range(1, len(by_t)):
        head, tail = by_t[:k], by_t[k:]
        if abs(sum(r["_cost"] for r in head) - gap) > EPS:
            continue
        if min(r["_mtime"] for r in tail) - max(r["_mtime"] for r in head) > MIN_SPLIT_S:
            return "RESUMED", [os.path.basename(r["_path"]) for r in head]
    if len(searchable) > SUBSET_SEARCH_MAX:
        return "UNSEARCHED", []
    hits = []
    for k in range(1, len(searchable) + 1):
        for combo in itertools.combinations(searchable, k):
            if abs(sum(r["_cost"] for r in combo) - gap) <= EPS:
                hits.append([os.path.basename(r["_path"]) for r in combo])
                if len(hits) > 1:
                    break
        if len(hits) > 1:
            break
    if len(hits) == 1:
        return "RESUMED", hits[0]
    if hits:
        return "AMBIGUOUS", hits[0]
    return "UNEXPLAINED", []


def audit(d: str) -> dict:
    """One directory's two numbers, their gap, what the gap is, and what the sum left out.

    The no-cost count is carried on EVERY verdict, `NO SUMMARY` included - a directory
    nobody charged is still a directory whose field total may be low.
    """
    rounds = load_rounds(d)
    cost, no_cost = _split_costs(rounds)
    n = len(rounds)
    src, counter = read_counter(d)
    rec: dict = {"dir": d, "n_rounds": n, "field_cost_usd": round(cost, 4),
                 "n_no_cost": len(no_cost), "no_cost": no_cost,
                 "summary": src, "charged_to_ceiling_usd": counter}
    if counter is None:
        rec["verdict"] = "NO SUMMARY"
        rec["gap_usd"] = None
        return rec
    gap = cost - counter
    rec["gap_usd"] = round(gap, 4)
    if gap < -EPS:
        rec["verdict"] = "MISSING ARTIFACT"
        rec["carried"] = []
    elif abs(gap) <= EPS:
        rec["verdict"] = "AGREES"
        rec["carried"] = []
    else:
        rec["verdict"], rec["carried"] = explain_gap(rounds, gap)
    return rec


def walk(root: str) -> list[dict]:
    """Every directory under `root` that holds at least one stored round."""
    out = []
    for dirpath, _dirnames, _filenames in os.walk(root):
        if load_rounds(dirpath):
            out.append(audit(dirpath))
    return sorted(out, key=lambda r: r["dir"])


BAD = ("MISSING ARTIFACT", "UNEXPLAINED", "UNSEARCHED")


def report(recs: list[dict], root: str | None = None) -> int:
    print(f"{'directory':46} {'n':>3} {'field':>9} {'ceiling':>10} "
          f"{'gap':>8}  verdict          (all three in {tokenvalue.UNIT})")
    total = 0.0
    for r in recs:
        d = os.path.relpath(r["dir"], root) if root else r["dir"]
        c = "-" if r["charged_to_ceiling_usd"] is None else f"{r['charged_to_ceiling_usd']:.2f}"
        g = "-" if r["gap_usd"] is None else f"{r['gap_usd']:.2f}"
        print(f"{d[-46:]:46} {r['n_rounds']:3} {r['field_cost_usd']:9.2f} {c:>10} "
              f"{g:>8}  {r['verdict']}")
        if r.get("carried"):
            print(f"{'':46} carried over: {', '.join(r['carried'])}")
        if r.get("no_cost"):
            print(f"{'':46} no cost_usd on {len(r['no_cost'])} round(s): "
                  f"{', '.join(r['no_cost'])} - excluded from the field column")
        total += r["field_cost_usd"]
    print(f"\n{len(recs)} sweep director(ies), {sum(r['n_rounds'] for r in recs)} stored "
          f"rounds, field {tokenvalue.tag(total)}")
    absent = sorted(name for r in recs for name in r.get("no_cost", []))
    if absent:
        print(f"the field total EXCLUDES {len(absent)} stored round(s) whose cost_usd is "
              f"absent or null, named above - a stated non-measurement, not a zero. "
              f"It is the sum of the rounds that state a cost, and is low by an unknown "
              f"amount.")
    under = [r for r in recs if r["verdict"] in ("RESUMED", "AMBIGUOUS")]
    if under:
        print(f"{len(under)} summary counter(s) under-report by "
              f"{tokenvalue.tag(sum(r['gap_usd'] for r in under))} in total - resumed "
              f"sweeps. Read the FIELD column, never the CEILING column, as the token "
              f"valuation of a field.")
    bad = [r for r in recs if r["verdict"] in BAD]
    for r in bad:
        print(f"  ** {r['dir']}: {r['verdict']}")
    print("\nNO PER-CALL MEAN IS PRINTED. These directories judge different games with "
          "different aspects\nover packs from 10 KB to 3.3 MB; a mean across them is "
          "rule 4's own example (JUDGING.md).")
    print(f"\n{tokenvalue.DEFINITION}")
    return 1 if bad else 0


# --------------------------------------------------------------------------- selftest

def _round(cost: float, aspect: str = "architecture", usable: bool = True) -> dict:
    return {"submissions": [{"submission": "x", "score": 1.0}], "aspect": aspect,
            "game": "g", "order_seed": 0, "cost_usd": cost, "usable": usable}


def _write(d: str, name: str, obj: dict, mtime: float | None = None) -> None:
    p = os.path.join(d, name)
    with open(p, "w") as fh:
        json.dump(obj, fh)
    if mtime is not None:
        os.utime(p, (mtime, mtime))


def selftest() -> int:
    fails: list[str] = []
    ran = [0]

    def check(label: str, got, want) -> None:
        ran[0] += 1
        if got != want:
            fails.append(f"{label}: got {got!r}, want {want!r}")

    with tempfile.TemporaryDirectory() as td:
        # 1. POSITIVE CONTROL - the counter agrees, and the tool says so.
        a = os.path.join(td, "agrees"); os.makedirs(a)
        _write(a, "r0.json", _round(1.00), 1000)
        _write(a, "r1.json", _round(2.00), 1001)
        _write(a, "SEQUENTIAL.json", {"mode": "sequential", "measured_cost_usd": 3.00})
        r = audit(a)
        check("agrees.verdict", r["verdict"], "AGREES")
        check("agrees.cost", round(r["field_cost_usd"], 2), 3.00)

        # 2. A RESUME, DEMONSTRATED BY MTIME - the oldest round is strictly older than
        #    the two the invocation wrote, and its cost is exactly the gap.
        b = os.path.join(td, "resumed"); os.makedirs(b)
        _write(b, "old.json", _round(1.00), 1000)
        _write(b, "new0.json", _round(2.00), 2000)
        _write(b, "new1.json", _round(4.00), 2001)
        _write(b, "SEQUENTIAL.json", {"measured_cost_usd": 6.00})
        r = audit(b)
        check("resumed.verdict", r["verdict"], "RESUMED")
        check("resumed.carried", r["carried"], ["old.json"])
        check("resumed.gap", round(r["gap_usd"], 2), 1.00)

        # 3. NEGATIVE CONTROL, AND THE ONE THAT MATTERS - the counter exceeds what is on
        #    disk, so a paid round has no file. The tool must go RED, not round it away.
        c = os.path.join(td, "missing"); os.makedirs(c)
        _write(c, "r0.json", _round(3.00), 1000)
        _write(c, "GATES.json", {"measured_cost_usd": 5.00})
        r = audit(c)
        check("missing.verdict", r["verdict"], "MISSING ARTIFACT")
        check("missing.gap", round(r["gap_usd"], 2), -2.00)
        check("missing.exit", report([r]), 1)

        # 4. A GAP NO SUBSET EXPLAINS is spend nobody can attribute, and is also RED.
        e = os.path.join(td, "unexplained"); os.makedirs(e)
        _write(e, "r0.json", _round(1.00), 1000)
        _write(e, "r1.json", _round(2.00), 1000)
        _write(e, "SEQUENTIAL.json", {"measured_cost_usd": 0.50})
        check("unexplained.verdict", audit(e)["verdict"], "UNEXPLAINED")

        # 5. NO SUMMARY IS NOT ZERO. The counter must come back None, so nothing can
        #    read an absent file as a sweep that agreed.
        f = os.path.join(td, "nosummary"); os.makedirs(f)
        _write(f, "r0.json", _round(7.00), 1000)
        r = audit(f)
        check("nosummary.verdict", r["verdict"], "NO SUMMARY")
        check("nosummary.counter", r["charged_to_ceiling_usd"], None)
        check("nosummary.cost", round(r["field_cost_usd"], 2), 7.00)

        # 6. A SUMMARY IS NOT A ROUND even when it carries a cost-shaped key, and an
        #    UNUSABLE round IS one. Both are shape decisions and both change the total.
        g = os.path.join(td, "shape"); os.makedirs(g)
        _write(g, "r0.json", _round(1.00), 1000)
        _write(g, "r1.json", _round(2.00, usable=False), 1001)
        _write(g, "GATES.json", {"measured_cost_usd": 3.00, "cost_usd": 99.0})
        r = audit(g)
        check("shape.n", r["n_rounds"], 2)
        check("shape.cost", round(r["field_cost_usd"], 2), 3.00)

        # 7. REGRESSION GUARD ON THE REAL CASE. The ten stored `post` rounds and the
        #    21.05 its own sweep.log printed. Hand-entered from the files so the guard
        #    survives the evidence tree being unavailable. FINDINGS #121.
        h = os.path.join(td, "post"); os.makedirs(h)
        carried = [("architecture__seed0", 5.0382153), ("architecture__seed1", 4.26154165),
                   ("audio__seed0", 0.7371495), ("audio__seed1", 0.5698161)]
        fresh = [("fun__seed0", 1.9298439), ("fun__seed1", 2.0314596),
                 ("idiomatic__seed0", 6.02663225), ("idiomatic__seed1", 6.7755465),
                 ("ux__seed0", 2.3075442), ("ux__seed1", 1.97783695)]
        for name, cost in carried:
            _write(h, name + ".json", _round(cost), 1_755_000_000)
        for i, (name, cost) in enumerate(fresh):
            _write(h, name + ".json", _round(cost), 1_755_000_500 + i)
        _write(h, "SEQUENTIAL.json", {"mode": "sequential", "measured_cost_usd": 21.05})
        r = audit(h)
        check("post.cost", round(r["field_cost_usd"], 2), 31.66)
        check("post.gap", round(r["gap_usd"], 2), 10.61)
        check("post.verdict", r["verdict"], "RESUMED")
        check("post.carried", sorted(r["carried"]),
              sorted(n + ".json" for n, _ in carried))

        # 8. THE MUTANT FOR THE MTIME SPLIT. Identical costs and an identical ordering to
        #    case 2, with the boundary compressed to a millisecond - what `cp` leaves
        #    behind. The split must stop being evidence, and the answer must fall through
        #    to subset sum. Here two subsets fit (1.00, and 3.00 alone is absent) so the
        #    honest verdict is the one that names its own weakness.
        m = os.path.join(td, "copied"); os.makedirs(m)
        _write(m, "a.json", _round(1.00), 1000.000)
        _write(m, "b.json", _round(2.00), 1000.001)
        _write(m, "c.json", _round(1.00), 1000.002)
        _write(m, "SEQUENTIAL.json", {"measured_cost_usd": 3.00})
        r = audit(m)
        check("copied.gap", round(r["gap_usd"], 2), 1.00)
        check("copied.verdict", r["verdict"], "AMBIGUOUS")

        # 9. A SUPERSEDED SUMMARY IS STILL A SUMMARY. Sweep summaries became append-only
        #    on 2026-08-23, so a re-run leaves `REPRODUCIBILITY-<stamp>.json` beside the
        #    canonical one. Neither may be counted as a round, and the counter must come
        #    from the canonical file - the LATEST invocation - not from the sibling.
        #    Without `is_summary` the sibling reaches the shape test, which is a second
        #    check doing this one's job.
        s = os.path.join(td, "superseded"); os.makedirs(s)
        _write(s, "r0.json", _round(4.00), 1000)
        _write(s, "REPRODUCIBILITY-20260820T100000Z.json",
               {"mode": "repeats", "measured_cost_usd": 1.00})
        _write(s, "REPRODUCIBILITY.json",
               {"mode": "repeats", "charged_to_ceiling_usd": 4.00,
                "superseded_record": "REPRODUCIBILITY-20260820T100000Z.json"})
        r = audit(s)
        check("superseded.n", r["n_rounds"], 1)
        check("superseded.summary", r["summary"], "REPRODUCIBILITY.json")
        check("superseded.counter", r["charged_to_ceiling_usd"], 4.00)
        check("superseded.verdict", r["verdict"], "AGREES")
        check("is_summary.canonical", is_summary("GATES.json"), True)
        check("is_summary.sibling", is_summary("GATES-20260820T100000Z-2.json"), True)
        # And it must NOT swallow a round whose name merely starts the same way.
        check("is_summary.round", is_summary("g1_pong__fun__seed0.json"), False)
        check("is_summary.notjson", is_summary("GATES.txt"), False)

        # 11. A ROUND WITH NO cost_usd IS NOT A ZERO. Absent key and null value are the
        #     two shapes of the absence; both must reach the audit record as a NAMED
        #     count, be counted in n_rounds, and be excluded from the total with the
        #     exclusion printed - never folded in as 0.0, the fallback `read_counter`
        #     refuses one function up. A recorded 0.0 is a stated zero: counted,
        #     summed, and NOT in the no-cost list. Warned, never refused: the report
        #     stays exit 0.
        n_ = os.path.join(td, "nocost"); os.makedirs(n_)
        _write(n_, "paid.json", _round(3.00), 1000)
        _write(n_, "absent.json",
               {k: v for k, v in _round(0.0).items() if k != "cost_usd"}, 1001)
        _write(n_, "null.json", _round(None), 1002)
        _write(n_, "zero.json", _round(0.0), 1003)
        r = audit(n_)
        check("nocost.n", r["n_rounds"], 4)
        check("nocost.cost", round(r["field_cost_usd"], 2), 3.00)
        check("nocost.n_no_cost", r["n_no_cost"], 2)
        check("nocost.names", sorted(r["no_cost"]), ["absent.json", "null.json"])
        check("nocost.verdict", r["verdict"], "NO SUMMARY")
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = report([r])
        out = buf.getvalue()
        check("nocost.exit", rc, 0)
        check("nocost.report.names",
              "absent.json" in out and "null.json" in out, True)
        check("nocost.report.label", "EXCLUDES 2 stored round(s)" in out, True)
        check("nocost.report.notzero", "a stated non-measurement, not a zero" in out,
              True)

        # 12. THE MTIME SPLIT IS STILL PREFERRED WHERE IT SEPARATES, ON A DIRECTORY OVER
        #     THE SUBSET BOUND. The split is O(n^2) and unbounded; if the bound checked
        #     first, an over-bound directory with a clean resume in it would come back
        #     UNSEARCHED instead of the demonstrated answer.
        o = os.path.join(td, "overbound_split"); os.makedirs(o)
        _write(o, "old.json", _round(1.00), 1000)
        for i in range(SUBSET_SEARCH_MAX + 1):
            _write(o, f"new{i}.json", _round(2.00), 2000 + i)
        _write(o, "SEQUENTIAL.json", {"measured_cost_usd": 2.00 * (SUBSET_SEARCH_MAX + 1)})
        r = audit(o)
        check("overbound_split.verdict", r["verdict"], "RESUMED")
        check("overbound_split.carried", r["carried"], ["old.json"])

        # 13. OVER THE BOUND WITH NOTHING THAT SEPARATES, the directory reports
        #     UNSEARCHED - red, and fast, instead of a 2^n hang. Every round costs the
        #     same and the gap is one round's worth, so a mutant that removes the bound
        #     fails FAST: the k=1 subset pass finds two singleton hits in microseconds
        #     and answers AMBIGUOUS, not UNSEARCHED.
        u = os.path.join(td, "overbound"); os.makedirs(u)
        for i in range(SUBSET_SEARCH_MAX + 2):
            _write(u, f"r{i}.json", _round(1.00), 1000 + i * 0.001)
        _write(u, "SEQUENTIAL.json", {"measured_cost_usd": SUBSET_SEARCH_MAX + 1})
        r = audit(u)
        check("overbound.verdict", r["verdict"], "UNSEARCHED")
        check("overbound.carried", r.get("carried"), [])
        check("overbound.bad", report([r]), 1)

        # 14. A ROUND THAT STATES NO COST CANNOT CLAIM THE GAP. Both attribution methods
        #     run over the rounds that state a cost only. A repair that kept the None
        #     round inside the search would carry it alongside the round that does -
        #     a subset containing a cost nobody recorded "summing" to the gap.
        p = os.path.join(td, "gapnocost"); os.makedirs(p)
        _write(p, "silent.json",
               {k: v for k, v in _round(0.0).items() if k != "cost_usd"}, 1000)
        _write(p, "paid_old.json", _round(1.00), 1001)
        _write(p, "new.json", _round(2.00), 2000)
        _write(p, "SEQUENTIAL.json", {"measured_cost_usd": 2.00})
        r = audit(p)
        check("gapnocost.n_no_cost", r["n_no_cost"], 1)
        check("gapnocost.verdict", r["verdict"], "RESUMED")
        check("gapnocost.carried", r["carried"], ["paid_old.json"])

        # 10. A CLEAN TREE WALK finds every directory holding rounds and no others - the
        #    parent `td` holds only subdirectories and must not appear. Kept after the
        #    cases above: it walks the tree they have just finished building.
        found = {os.path.basename(x["dir"]) for x in walk(td)}
        check("walk.dirs", found,
              {"agrees", "resumed", "missing", "unexplained", "nosummary", "shape",
               "post", "copied", "superseded", "nocost", "overbound", "overbound_split",
               "gapnocost"})

    for f in fails:
        print(f"  FAIL {f}")
    # The count is of EXPECTATIONS, not of cases. "7 of 8 cases pass" would need a case
    # to be a unit the code knows about; it is not, and inventing one would be a number
    # with no producer in the module written about numbers with no producer.
    print(f"\nselftest: {ran[0]} expectations checked, {len(fails)} unmet")
    return 1 if fails else 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tree", help="walk every sweep directory under this root")
    ap.add_argument("--dir", help="audit one sweep directory")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.dir:
        recs, root = [audit(a.dir)], None
    elif a.tree:
        recs, root = walk(a.tree), a.tree
    else:
        ap.error("one of --tree, --dir or --selftest")
    if a.json:
        json.dump(recs, sys.stdout, indent=2)
        print()
        return 1 if any(r["verdict"] in BAD for r in recs) else 0
    return report(recs, root)


if __name__ == "__main__":
    raise SystemExit(main())
