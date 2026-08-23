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
from evaluate import overall_score  # noqa: E402


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
                    # RAW AND ADJUDICATED MUST BE COMPUTED THE SAME WAY, or their
                    # difference is not the adjudication. Tier 1 became a gate on
                    # 2026-08-23 (RUBRIC.md), so a stored `overall` from before then is
                    # in the old weighted regime; using it as RAW against a
                    # current-regime ADJUDICATED would report the scheme change as an
                    # adjudication effect. Both are recomputed here under the current
                    # scheme, and the stored figure is carried separately, labelled.
                    "overall_raw": overall_score({"programmatic": pr,
                                                  "playbot": r["tier_scores"]["playbot"]}),
                    "overall_adj": overall_score({"programmatic": pr,
                                                  "playbot": pb_adj}),
                    "overall_stored": r["overall"],
                    "regime": r.get("scoring_regime", "weighted-0.31/0.69 (pre-gate)"),
                    "gate": r.get("gate"),
                    # DERIVED, not read. Every stored record predates 2026-08-23 and
                    # carries `gate: None` (measured over all 90), so reading the field
                    # would gate nothing while looking like it gated. Tier 1 is a
                    # PASS/FAIL gate under the current scheme (RUBRIC.md), and green
                    # means every tier-1 criterion passed.
                    "gate_green": all(c["passed"] for c in r["programmatic"]["criteria"]),
                    "n_scored": len(scored),
                    "prog": pr, "bot_raw": r["tier_scores"]["playbot"], "bot_adj": pb_adj,
                    "fails": [c["id"] for c in scored if not c["passed"]],
                    "evidence_by_id": {c["id"]: c.get("evidence", "")
                                       for c in scored if not c["passed"]}})
    return out


def ranking_test(rows: list[dict]) -> str:
    """The re-open condition for the deterministic-tier ranking ban (`DECISIONS.md`).

    Two things separate this from the ADJUDICATED block above, and both come from
    decisions already made rather than from this test:

    1. GATE-GREEN ONLY. Tier 1 is a PASS/FAIL gate, so a submission that does not build
       has no tier-2 score to occupy a rank position - its 0.00, or its adjudicated
       near-1.00, is a restatement of the gate failure. `DECISIONS.md` already puts
       "it caught a game that does not compile" in the MAY column and "ranking stacks,
       at any gap" in the MAY NOT column; this keeps the two apart mechanically.

       It is not a way of hiding a stack difference. A gate failure is reported, loudly,
       as a gate failure. What it may not do is read as a small deduction, which is the
       exact misreading tier 1 stopped being weighted in order to prevent.

    2. THE GAP MUST EXCEED THE FLOOR BY ONE CRITERION. `JUDGING.md` pre-registered
       `range <= noise -> NO SEPARATION` on 2026-08-16. Tier 2 is a pass count over N
       criteria, so no gap smaller than 1/N is representable at all: below that the
       comparison is not a small effect, it is an unmeasurable one.

    `n=2` per cell is the standing limitation and this test does not repair it: the
    within-cell floor is one absolute difference per stack, averaged over stacks.
    CROSSES here means the ban is re-opened for that group and the mechanism behind the
    gap must then be named - not that a ranking has been established.
    """
    out = ["=== THE RANKING TEST: adjudicated, gate-green, completed (DECISIONS.md) ==="]
    by_game = defaultdict(list)
    for r in rows:
        by_game[r["game"]].append(r)
    for g, rs in sorted(by_game.items()):
        n_scored = max((r["n_scored"] for r in rs), default=0)
        quantum = 1.0 / n_scored if n_scored else 0.0
        by_stack = defaultdict(list)
        for r in rs:
            by_stack[r["stack"]].append(r)
        ok = {s: v for s, v in by_stack.items()
              if len(v) == 2 and all(x["gate_green"] for x in v)}
        gated = sorted(set(by_stack) - set(ok))
        head = (f"{g:<13} N={n_scored} criteria, one criterion = {quantum:.4f}; "
                f"gate-green stacks {sorted(ok) or '-'}")
        out.append(head)
        if gated:
            out.append(f"              gated out (tier-1 FAIL, or not a pair): {gated} "
                       f"- reported as a gate failure, never as a rank")
        if len(ok) < 2:
            out.append("              -> NOT ASKED: fewer than two gate-green stacks")
            continue
        w = st.fmean(abs(v[0]["overall_adj"] - v[1]["overall_adj"]) for v in ok.values())
        means = [st.fmean(x["overall_adj"] for x in v) for v in ok.values()]
        b = max(means) - min(means)
        # A gap of EXACTLY one criterion crosses, and both sides are k/N floats, so a
        # bare `>=` decides the boundary on rounding: 1.0 - 12/13 comes out 6e-17 below
        # 1/13. The selftest's BOUNDARY row caught that; the tolerance is what fixed it.
        crosses = (b - w) >= quantum - 1e-9
        note = "" if len(ok) == 4 else f" ({len(ok)} stacks - not a four-way comparison)"
        out.append(f"              within-cell floor={w:.4f}  between-stack range={b:.4f}"
                   f"  range-floor={b - w:.4f}  vs one criterion {quantum:.4f}")
        out.append(f"              -> {'CROSSES' if crosses else 'DOES NOT CROSS'}"
                   f" - the ban {'RE-OPENS' if crosses else 'stands'} for this group{note}")
    out.append("")
    return "\n".join(out)


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
    regimes = sorted({r["regime"] for r in rows})
    stale = [r for r in rows if abs((r["overall_stored"] or 0) - r["overall_raw"]) > 1e-9]
    print(f"scoring regime of the stored records: {', '.join(regimes)}")
    print("RAW and ADJUDICATED below are both computed under the CURRENT scheme "
          "(tier 1 is a gate,\n`overall` = play-bot), so their difference is the "
          "adjudication and nothing else.")
    if stale:
        print(f"{len(stale)} of {len(rows)} stored `overall` values differ from RAW "
              f"because they were written\nunder another regime. The stored numbers are "
              f"NOT rewritten; see eval/RUNS.md.")
    print()
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
    print(ranking_test(rows))
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


def _row(game: str, stack: str, trial: str, score: float, gate: bool, n: int) -> dict:
    return {"game": game, "stack": stack, "trial": trial, "overall_adj": score,
            "gate_green": gate, "n_scored": n}


def ranking_test_selftest() -> int:
    """Can `ranking_test` say CROSSES at all?

    Over every stored run it says DOES NOT CROSS nine times out of nine. That is the
    shape of a check that cannot fail (rule 1) and of a census reporting its instrument
    (rule 12), and the two are indistinguishable from outside without this.
    """
    failed = 0

    def check(name: str, cond: bool, detail: str = "") -> None:
        nonlocal failed
        if not cond:
            failed += 1
        print(f"  {'ok  ' if cond else 'FAIL'}  {name}" + (f"   [{detail}]" if detail else ""))

    # POSITIVE. Four gate-green stacks, zero within-cell noise, one stack two criteria
    # below the rest. 2/13 = 0.1538 > 1/13.
    rows = ([_row("g", s, t, 1.0, True, 13) for s in "abc" for t in "01"]
            + [_row("g", "d", t, 11 / 13, True, 13) for t in "01"])
    out = ranking_test(rows)
    check("POSITIVE: a two-criterion gap on a silent floor CROSSES", "CROSSES" in out
          and "DOES NOT CROSS" not in out, out.strip().splitlines()[-1].strip())

    # THE QUANTUM. Same shape, gap of exactly one criterion. range-floor == 1/N, so it
    # crosses on the >= boundary; at anything smaller it must not.
    rows = ([_row("g", s, t, 1.0, True, 13) for s in "abc" for t in "01"]
            + [_row("g", "d", t, 12 / 13, True, 13) for t in "01"])
    check("BOUNDARY: a gap of exactly one criterion crosses",
          "-> CROSSES" in ranking_test(rows))

    # VARIANT: the gap is real but the within-cell floor is just as large. This is the
    # pre-registered `range <= noise` rule and it must still refuse.
    rows = ([_row("g", s, t, 1.0, True, 13) for s in "abc" for t in "01"]
            + [_row("g", "d", "0", 1.0, True, 13), _row("g", "d", "1", 11 / 13, True, 13)])
    out = ranking_test(rows)
    check("VARIANT: a gap no larger than its own within-cell floor does NOT cross",
          "DOES NOT CROSS" in out, out.strip().splitlines()[-1].strip())

    # MUTANT: the same crossing gap, but the low stack failed the tier-1 gate. A gate
    # failure is not a rank, so the group must fall back to the three that are green -
    # and they are tied.
    rows = ([_row("g", s, t, 1.0, True, 13) for s in "abc" for t in "01"]
            + [_row("g", "d", t, 11 / 13, False, 13) for t in "01"])
    out = ranking_test(rows)
    check("MUTANT: a gate-FAIL stack is gated out, not ranked last",
          "DOES NOT CROSS" in out and "gated out" in out)
    check("...and it is named where it went, not silently dropped", "'d'" in out)

    # A group with one gate-green stack is not asked at all - never answered NO.
    rows = ([_row("g", "a", t, 1.0, True, 13) for t in "01"]
            + [_row("g", "b", t, 0.5, False, 13) for t in "01"])
    check("NOT ASKED beats a false negative when there is nothing to compare",
          "NOT ASKED" in ranking_test(rows))

    print(f"discrimination ranking_test selftest: {'FAILED' if failed else 'OK'}")
    return 1 if failed else 0


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--selftest":
        raise SystemExit(ranking_test_selftest())
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1
                          else "runs/wg-matrix-2026-08-13T14-02-50"))
