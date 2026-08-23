#!/usr/bin/env python3
"""What has tier 1 ever DONE? Per criterion, per trial, over the stored corpus.

`weight_sensitivity.py` established that the 0.31/0.69 split moves no ordering at any
weight, and that in 7 of 10 stored groups it cannot, because tier 1 returns a single
value across the whole group (FINDINGS #92). That is an argument about the WEIGHT. It
does not say what tier 1 measured, which is the question that decides what tier 1
should BE.

This is the producer for that. It reads every stored `report.json`, and reports:

  1. per tier-1 criterion, how many trials it was scored on and how many it failed;
  2. every failing trial, with the criterion ids and the evidence string - the audit
     trail, not the conclusion;
  3. per (run, game) group, whether tier 1 and tier 2 vary AMONG THE TRIALS TIER 2
     COULD MEASURE, which is the one thing a weighted sum of the two exists to trade off.

THE HEADLINE IS (3), and it is falsifiable in one direction:

  FLOOR-ONLY     in no group do both tiers vary among trials that built and drove.
                 The weighted sum has never had to trade one tier against the other:
                 wherever tier 1 separated submissions, tier 2 did not, and vice versa.
  DISCRIMINATES  some group has both varying. Tier 1 is then separating submissions
                 that tier 2 also separates, the weight decides how they combine, and
                 a gate would be throwing information away.

The day a tier-1 criterion with real headroom is added, this flips to DISCRIMINATES
and the gate decision in RUBRIC.md has to be re-made. That is the point: the decision
carries the measurement that would retire it.

BLOCKING criteria are the ones tier 2 depends on by construction. Tier 2 drives the
submission through `just probe`, so a project that does not build (`build.compiles`)
or whose probe never answers (`probe.responds`) cannot produce tier-2 evidence at all:
its 0.00 there is a restatement of the tier-1 failure, not a second measurement. The
mechanism is the reason; the corpus is the corroboration, printed as a 2x2 below.

`render.frames` is deliberately NOT blocking. The play-bot drives the probe, not the
film, so a submission whose capture recipe is broken can still be measured playing.

Usage:
    ./tier1_census.py --selftest
    ./tier1_census.py --runs-root <main checkout>/eval/runs
    ./tier1_census.py --runs-root ... --json

`--runs-root` is not optional and is not guessed: `eval/runs/` is gitignored, so a
worktree's copy of that path is empty and a census run there would report zero
failures - a confident, wrong, uniform answer of exactly the shape rule 12 names.
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

#: Tier-1 criteria that tier 2 depends on. See the module docstring for the mechanism.
BLOCKING = ("build.compiles", "probe.responds")


# --------------------------------------------------------------------------- #
# loading
# --------------------------------------------------------------------------- #

def load(runs_root: Path) -> list[dict]:
    """Every stored trial that recorded tier-1 criteria.

    A trial with no tier-1 criteria is skipped rather than counted as all-passing:
    `total=0 passed=0` is indistinguishable from correct failure (rule 1), and the
    early single-stack runs predate the tier entirely.
    """
    rows = []
    for rep in sorted(runs_root.glob("*/artifacts/*/eval/report.json")):
        rec = json.loads(rep.read_text())
        crits = ((rec.get("programmatic") or {}).get("criteria")) or []
        if not crits:
            continue
        tiers = rec.get("tier_scores") or {}
        rows.append({
            "run": rep.parents[3].name,
            "trial": rep.parents[1].name,
            "game": rec.get("game"),
            "stack": Path(str(rec.get("starter") or "")).name or "?",
            "t1": tiers.get("programmatic"),
            "t2": tiers.get("playbot"),
            "playbot_usable": bool(rec.get("playbot_usable", True)),
            "criteria": [{"id": c.get("id"),
                          "passed": bool(c.get("passed")),
                          "scored": bool(c.get("scored", True)),
                          "evidence": (c.get("evidence") or "")}
                         for c in crits],
        })
    return rows


# --------------------------------------------------------------------------- #
# the three reports
# --------------------------------------------------------------------------- #

def per_criterion(rows: list[dict]) -> dict[str, dict[str, int]]:
    out: dict[str, dict[str, int]] = {}
    for r in rows:
        for c in r["criteria"]:
            d = out.setdefault(c["id"], {"scored_on": 0, "failed": 0, "unscored_on": 0})
            if not c["scored"]:
                d["unscored_on"] += 1
                continue
            d["scored_on"] += 1
            if not c["passed"]:
                d["failed"] += 1
    return out


def failures(rows: list[dict]) -> list[dict]:
    out = []
    for r in rows:
        bad = [c for c in r["criteria"] if c["scored"] and not c["passed"]]
        if not bad:
            continue
        out.append({
            "run": r["run"], "trial": r["trial"], "t1": r["t1"], "t2": r["t2"],
            "failed": [c["id"] for c in bad],
            "blocking": [c["id"] for c in bad if c["id"] in BLOCKING],
            "evidence": {c["id"]: c["evidence"][:160] for c in bad},
        })
    return out


def blocked(row: dict) -> bool:
    """Did this trial fail a criterion tier 2 depends on?"""
    return any(c["id"] in BLOCKING and c["scored"] and not c["passed"]
               for c in row["criteria"])


def groups(rows: list[dict]) -> list[dict]:
    """Per (run, game): does either tier vary among the trials tier 2 could measure?

    Blocked trials are held out of the variance question, not dropped from the
    report. Counting them would make tier 1 look discriminating for the one reason
    that says nothing about the submission's play: it never ran.
    """
    keys = sorted({(r["run"], str(r["game"])) for r in rows})
    out = []
    for run, game in keys:
        g = [r for r in rows if r["run"] == run and str(r["game"]) == game]
        live = [r for r in g if not blocked(r) and r["playbot_usable"]]
        t1 = {round(float(r["t1"]), 9) for r in live if r["t1"] is not None}
        t2 = {round(float(r["t2"]), 9) for r in live if r["t2"] is not None}
        out.append({
            "run": run, "game": game,
            "n": len(g), "n_blocked": len(g) - len(live),
            "t1_values": sorted(t1), "t2_values": sorted(t2),
            "both_vary": len(t1) > 1 and len(t2) > 1,
        })
    return out


def blocking_2x2(rows: list[dict]) -> dict[str, int]:
    """Does a blocking failure actually coincide with an unmeasurable tier 2?

    The mechanism says it must. This counts whether the corpus agrees, and it is
    reported as counts with n rather than as a claim: the cell that matters has been
    entered twice in the project's history.
    """
    out = {"blocked_t2_zero": 0, "blocked_t2_nonzero": 0,
           "unblocked_failed_t2_zero": 0, "unblocked_failed_t2_nonzero": 0}
    for r in rows:
        failed_any = any(c["scored"] and not c["passed"] for c in r["criteria"])
        if not failed_any:
            continue
        t2 = float(r["t2"] or 0.0)
        if blocked(r):
            out["blocked_t2_zero" if t2 == 0.0 else "blocked_t2_nonzero"] += 1
        else:
            out["unblocked_failed_t2_zero" if t2 == 0.0
                else "unblocked_failed_t2_nonzero"] += 1
    return out


def verdict(gs: list[dict]) -> str:
    return "DISCRIMINATES" if any(g["both_vary"] for g in gs) else "FLOOR-ONLY"


# --------------------------------------------------------------------------- #
# what moving to the gate would do to an ordering someone had already read
# --------------------------------------------------------------------------- #

#: The weighted-sum regime this replaces. Kept here as a NUMBER, not imported, because
#: its whole purpose is to reproduce what the old scheme said after the new one has
#: replaced it in `evaluate.py`.
OLD_W1 = 0.31


def _pairs(means: dict[str, float], tol: float = 1e-6) -> dict[tuple[str, str], str]:
    """Every ordered pair's relation: '>', '<' or '='."""
    out = {}
    names = sorted(means)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            d = means[a] - means[b]
            out[(a, b)] = "=" if abs(d) <= tol else (">" if d > 0 else "<")
    return out


def ordering_change(rows: list[dict]) -> list[dict]:
    """Per (run, game): does dropping tier 1 from the score REVERSE anything?

    `weight_sensitivity.py` answers a different question and says so: it sweeps the
    OPEN interval (0,1), because w1=0 discards a tier outright and is not a candidate
    weighting. The gate regime IS w1=0. So FLIPS=0 is not evidence that this change
    moves nothing, and quoting it that way would be reading a result off the one
    point the instrument excludes.

    This asks the question at that point, pairwise on per-stack means so it is
    comparable with that tool:

      IDENTICAL   every pair stands as it did
      COARSER     some pair that was strictly ordered is now tied - a distinction the
                  gate removes, which is the intended effect where the distinction
                  was a lint finding
      FINER       some pair that was tied is now strictly ordered
      REVERSED    some pair swapped sides. This is the outcome that would count
                  AGAINST the change, and it is why the check is here.
    """
    out = []
    for run, game in sorted({(r["run"], str(r["game"])) for r in rows}):
        g = [r for r in rows
             if r["run"] == run and str(r["game"]) == game and r["playbot_usable"]
             and r["t1"] is not None and r["t2"] is not None]
        stacks = sorted({r["stack"] for r in g})
        if not stacks:
            continue
        old, new = {}, {}
        for s in stacks:
            ts = [r for r in g if r["stack"] == s]
            old[s] = sum(OLD_W1 * float(r["t1"]) + (1 - OLD_W1) * float(r["t2"])
                         for r in ts) / len(ts)
            new[s] = sum(float(r["t2"]) for r in ts) / len(ts)
        po, pn = _pairs(old), _pairs(new)
        reversed_ = [k for k in po if po[k] != "=" and pn[k] != "=" and po[k] != pn[k]]
        coarser = [k for k in po if po[k] != "=" and pn[k] == "="]
        finer = [k for k in po if po[k] == "=" and pn[k] != "="]
        kind = ("REVERSED" if reversed_ else
                "COARSER" if coarser and not finer else
                "FINER" if finer and not coarser else
                "MIXED" if coarser and finer else "IDENTICAL")
        out.append({"run": run, "game": game, "kind": kind,
                    "reversed_pairs": ["".join(k) for k in reversed_],
                    "coarsened_pairs": [f"{a}/{b}" for a, b in coarser],
                    "refined_pairs": [f"{a}/{b}" for a, b in finer]})
    return out


# --------------------------------------------------------------------------- #
# rendering
# --------------------------------------------------------------------------- #

def render(rows: list[dict]) -> str:
    pc, fl, gs, b22 = per_criterion(rows), failures(rows), groups(rows), blocking_2x2(rows)
    L = [f"{len(rows)} stored trials carry tier-1 criteria", ""]

    L.append("--- per criterion ---")
    L.append(f"{'criterion':<24}{'scored on':>11}{'failed':>8}{'unscored on':>13}"
             f"{'blocking':>10}")
    for cid in sorted(pc, key=lambda c: (-pc[c]["failed"], c)):
        d = pc[cid]
        L.append(f"{cid:<24}{d['scored_on']:>11}{d['failed']:>8}{d['unscored_on']:>13}"
                 f"{('yes' if cid in BLOCKING else ''):>10}")
    never = sorted(c for c, d in pc.items() if d["failed"] == 0)
    L.append(f"\n{len(never)} of {len(pc)} criteria have never failed: {', '.join(never)}")

    L.append(f"\n--- every failing trial (n={len(fl)}) ---")
    for f in fl:
        tag = "BLOCKING" if f["blocking"] else "non-blocking"
        L.append(f"  {f['run']}/{f['trial']}  t1={f['t1']}  t2={f['t2']}  [{tag}]")
        for cid in f["failed"]:
            L.append(f"      {cid:<20} {f['evidence'][cid][:110]}")

    L.append("\n--- does a blocking failure coincide with an unmeasurable tier 2? ---")
    L.append(f"  blocked          : t2=0.00 on {b22['blocked_t2_zero']}, "
             f"t2>0 on {b22['blocked_t2_nonzero']}")
    L.append(f"  failed, unblocked: t2=0.00 on {b22['unblocked_failed_t2_zero']}, "
             f"t2>0 on {b22['unblocked_failed_t2_nonzero']}")

    L.append("\n--- per (run, game), among trials tier 2 could measure ---")
    L.append(f"{'run':<34}{'game':<14}{'n':>4}{'blocked':>9}{'t1 values':>11}"
             f"{'t2 values':>11}  both vary")
    for g in gs:
        L.append(f"{g['run']:<34}{g['game']:<14}{g['n']:>4}{g['n_blocked']:>9}"
                 f"{len(g['t1_values']):>11}{len(g['t2_values']):>11}  "
                 f"{'YES' if g['both_vary'] else 'no'}")
    oc = ordering_change(rows)
    L.append("\n--- dropping tier 1 from the score: what happens to each ordering? ---")
    L.append("(w1=0 is OUTSIDE the interval weight_sensitivity.py sweeps - see that "
             "tool's caveat)")
    L.append(f"{'run':<34}{'game':<14}{'change':<11}detail")
    for o in oc:
        detail = ""
        if o["coarsened_pairs"]:
            detail = "now tied: " + ", ".join(o["coarsened_pairs"])
        if o["reversed_pairs"]:
            detail = "REVERSED: " + ", ".join(o["reversed_pairs"])
        L.append(f"{o['run']:<34}{o['game']:<14}{o['kind']:<11}{detail}")
    n_rev = sum(1 for o in oc if o["kind"] == "REVERSED")
    n_coarse = sum(1 for o in oc if o["kind"] == "COARSER")
    L.append(f"\n  reversed: {n_rev}   coarsened: {n_coarse}   "
             f"identical: {sum(1 for o in oc if o['kind'] == 'IDENTICAL')}")

    n_both = sum(1 for g in gs if g["both_vary"])
    L.append(f"\ngroups: {len(gs)}   both tiers vary among measurable trials: {n_both}")
    L.append(f"VERDICT: {verdict(gs)}")
    if verdict(gs) == "FLOOR-ONLY":
        L.append("  Tier 1 has never separated submissions that tier 2 also separated.")
        L.append("  A weight in front of it has never had two signals to combine.")
    else:
        L.append("  Tier 1 IS separating submissions tier 2 also separates. RUBRIC.md's")
        L.append("  gate decision rests on this being FLOOR-ONLY - re-make it.")
    return "\n".join(L)


# --------------------------------------------------------------------------- #
# selftest: prove the extraction on cases whose answers are stated in advance
# --------------------------------------------------------------------------- #

FAILS: list[str] = []
CHECKS = 0


def expect(name: str, cond: bool, detail: str = "") -> None:
    global CHECKS
    CHECKS += 1
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f"  -- {detail}" if detail else ""))
    if not cond:
        FAILS.append(name)


def _write_trial(root: Path, run: str, trial: str, game: str, stack: str,
                 crits: list[tuple[str, bool, bool]], t2: float,
                 playbot_usable: bool = True) -> None:
    d = root / run / "artifacts" / trial / "eval"
    d.mkdir(parents=True, exist_ok=True)
    t1 = (sum(1 for _, p, s in crits if s and p) / max(1, sum(1 for _, _, s in crits if s)))
    (d / "report.json").write_text(json.dumps({
        "game": game, "starter": f"/somewhere/starters/{stack}",
        "tier_scores": {"programmatic": t1, "playbot": t2},
        "playbot_usable": playbot_usable,
        "programmatic": {"criteria": [
            {"id": i, "passed": p, "scored": s, "evidence": f"{i} ev"} for i, p, s in crits]},
    }))


def selftest() -> int:
    """A fixture whose census I can state before running it, then mutants.

    Rule 12's corollary: prove the extraction on one case whose true value you can
    state in advance. Every census defect this project has had returned the same
    wrong answer for every subject, which is what made them look like findings.
    """
    print("[fixture: 5 trials, answers stated before the tool runs]")
    ok = [("build.compiles", True, True), ("lint.clean", True, True),
          ("probe.responds", True, True)]
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        # g1: two clean trials, one with a lint nit -> t1 varies, t2 constant.
        _write_trial(root, "runA", "g1__a__t0", "g1", "a", ok, 1.0)
        _write_trial(root, "runA", "g1__b__t0", "g1", "b", ok, 1.0)
        _write_trial(root, "runA", "g1__c__t0", "g1", "c",
                     [("build.compiles", True, True), ("lint.clean", False, True),
                      ("probe.responds", True, True)], 1.0)
        # g2: one trial that never built -> blocked, held out of the variance question.
        _write_trial(root, "runA", "g2__a__t0", "g2", "a",
                     [("build.compiles", False, True), ("lint.clean", False, True),
                      ("probe.responds", False, True)], 0.0)
        _write_trial(root, "runA", "g2__b__t0", "g2", "b", ok, 0.5)
        rows = load(root)

        expect("loads every trial that carries criteria", len(rows) == 5, str(len(rows)))
        pc = per_criterion(rows)
        expect("lint.clean: scored on 5, failed 2",
               pc["lint.clean"] == {"scored_on": 5, "failed": 2, "unscored_on": 0},
               str(pc["lint.clean"]))
        expect("build.compiles: failed exactly 1",
               pc["build.compiles"]["failed"] == 1, str(pc["build.compiles"]))
        expect("two trials are reported as failing", len(failures(rows)) == 2,
               str(len(failures(rows))))
        expect("the build failure is tagged blocking, the lint nit is not",
               sorted(f["blocking"] for f in failures(rows))
               == [[], ["build.compiles", "probe.responds"]],
               str([f["blocking"] for f in failures(rows)]))
        gs = {g["game"]: g for g in groups(rows)}
        expect("g1: tier 1 varies, tier 2 does not -> both_vary false",
               len(gs["g1"]["t1_values"]) == 2 and len(gs["g1"]["t2_values"]) == 1
               and not gs["g1"]["both_vary"], str(gs["g1"]))
        expect("g2: the blocked trial is held out, leaving n=1 measurable",
               gs["g2"]["n_blocked"] == 1 and gs["g2"]["t1_values"] == [1.0],
               str(gs["g2"]))
        expect("fixture verdict is FLOOR-ONLY", verdict(groups(rows)) == "FLOOR-ONLY")
        expect("blocking 2x2 puts the build failure in the t2=0 cell",
               blocking_2x2(rows)["blocked_t2_zero"] == 1
               and blocking_2x2(rows)["unblocked_failed_t2_nonzero"] == 1,
               str(blocking_2x2(rows)))

        # POSITIVE CONTROL for the headline. A verdict that is always FLOOR-ONLY is
        # worth nothing; this is a group the tool MUST call DISCRIMINATES.
        print("\n[positive control: a group where both tiers vary must flip the verdict]")
        _write_trial(root, "runB", "g1__a__t0", "g1", "a", ok, 1.0)
        _write_trial(root, "runB", "g1__b__t0", "g1", "b",
                     [("build.compiles", True, True), ("lint.clean", False, True),
                      ("probe.responds", True, True)], 0.5)
        rows2 = load(root)
        gb = next(g for g in groups(rows2) if g["run"] == "runB")
        expect("the constructed group is found to vary on both tiers", gb["both_vary"],
               str(gb))
        expect("and the headline verdict flips to DISCRIMINATES",
               verdict(groups(rows2)) == "DISCRIMINATES")

        # An unscored criterion (the engine project-lock exception) is not a failure.
        print("\n[variant: a criterion excluded from the denominator is not a failure]")
        _write_trial(root, "runC", "g1__a__t0", "g1", "a",
                     [("build.compiles", True, True), ("lint.clean", False, False),
                      ("probe.responds", True, True)], 1.0)
        rowsC = [r for r in load(root) if r["run"] == "runC"]
        expect("scored=false does not count as a failure",
               failures(rowsC) == [] and per_criterion(rowsC)["lint.clean"]
               == {"scored_on": 0, "failed": 0, "unscored_on": 1},
               str(per_criterion(rowsC)["lint.clean"]))

        # The ordering question, at the point weight_sensitivity.py excludes.
        print("\n[dropping tier 1: a coarsening is not a reversal, and the tool "
              "must tell them apart]")
        oc = {o["game"]: o for o in ordering_change([r for r in rows if r["run"] == "runA"])}
        expect("g1: the lint nit's distinction disappears -> COARSER",
               oc["g1"]["kind"] == "COARSER" and oc["g1"]["coarsened_pairs"] != [],
               str(oc["g1"]))
        # POSITIVE CONTROL: a group built to reverse must be reported REVERSED.
        six = ["build.compiles", "probe.responds", "lint.clean", "tests.green",
               "verify.green", "render.nonempty"]
        _write_trial(root, "runD", "g1__a__t0", "g1", "a",
                     [(c, True, True) for c in six], 0.50)
        _write_trial(root, "runD", "g1__b__t0", "g1", "b",
                     [(c, c in ("build.compiles", "probe.responds"), True) for c in six],
                     0.62)
        rowsD = [r for r in load(root) if r["run"] == "runD"]
        expect("a constructed reversal is reported REVERSED, not COARSER",
               ordering_change(rowsD)[0]["kind"] == "REVERSED",
               str(ordering_change(rowsD)[0]))

        # MUTANTS. Each removes one mechanism; the expectation above must go red.
        print("\n[mutants: can these checks fail?]")
        g = globals()

        original_blocking = g["BLOCKING"]
        g["BLOCKING"] = ()
        caught = not blocked(rows[3]) and blocking_2x2(rows)["blocked_t2_zero"] == 0
        g["BLOCKING"] = original_blocking
        expect("mutant 'nothing is blocking' changes the 2x2 and is caught", caught)

        original_blocked = g["blocked"]
        g["blocked"] = lambda row: False
        gs_m = {x["game"]: x for x in groups(rows)}
        caught = gs_m["g2"]["n_blocked"] == 0 and len(gs_m["g2"]["t1_values"]) == 2
        g["blocked"] = original_blocked
        expect("mutant 'never hold out a blocked trial' makes tier 1 look varying, "
               "and is caught", caught, str(gs_m["g2"]))

        original_pc = g["per_criterion"]

        def ignore_scored(rs):
            out: dict[str, dict[str, int]] = {}
            for r in rs:
                for c in r["criteria"]:
                    d = out.setdefault(c["id"],
                                       {"scored_on": 0, "failed": 0, "unscored_on": 0})
                    d["scored_on"] += 1
                    if not c["passed"]:
                        d["failed"] += 1
            return out

        g["per_criterion"] = ignore_scored
        caught = per_criterion(rowsC)["lint.clean"]["failed"] == 1
        g["per_criterion"] = original_pc
        expect("mutant 'ignore the scored flag' turns the lock exception into a "
               "failure, and is caught", caught)

    print(f"\n{CHECKS - len(FAILS)}/{CHECKS} expectations held")
    if FAILS:
        print("FAILED: " + ", ".join(FAILS))
        return 1
    print("tier1_census selftest: OK")
    return 0


# --------------------------------------------------------------------------- #

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--runs-root", type=Path,
                    help="where eval/runs/ actually is. Required: it is gitignored, so "
                         "a worktree's copy is empty and the census would report zero "
                         "failures for every criterion (rule 12)")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    if a.selftest:
        return selftest()
    if not a.runs_root:
        ap.error("--runs-root is required (or --selftest)")
    if not a.runs_root.is_dir():
        print(f"no run store at {a.runs_root}", file=sys.stderr)
        return 2
    rows = load(a.runs_root)
    if not rows:
        print(f"no stored trials with tier-1 criteria under {a.runs_root}",
              file=sys.stderr)
        return 1
    if a.json:
        print(json.dumps({"n_trials": len(rows),
                          "per_criterion": per_criterion(rows),
                          "failures": failures(rows),
                          "blocking_2x2": blocking_2x2(rows),
                          "groups": groups(rows),
                          "verdict": verdict(groups(rows))}, indent=2))
    else:
        print(render(rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
