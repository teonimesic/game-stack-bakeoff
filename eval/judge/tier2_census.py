#!/usr/bin/env python3
"""What has tier 2 ever DONE? Per criterion, per trial, over the stored corpus.

`tier1_census.py` asked this of tier 1 and the answer retired its weight: it was a
floor test, so it became a gate (FINDINGS #123). That left `overall = tier2`, and the
same question is now due of the only tier that scores. It has never been asked.

The headline is the one thing a scoring tier exists to do:

  SEPARATES   in every (run, game) group, tier 2 returns more than one value among the
              trials it could measure.
  SATURATED   some group returns a SINGLE value across every submission in it. Nothing
              in that group is ranked, and no weight can help - there is one number.

Three sub-reports, because "saturated" has three different causes and they call for
opposite repairs:

  1. PER CRITERION, per game: scored on, failed, never failed. A criterion that has
     never failed is not thereby bad - it may be an invariant nothing has violated -
     but a tier made entirely of them cannot separate anything.

  2. WHOLE-TRIAL vs SELECTIVE failures. Most tier-2 failures in this corpus are not a
     criterion disagreeing with its siblings; they are a submission that never drove at
     all, failing every criterion at once with the same reason. Those produce a 0.00
     against a field of 1.00, which is a floor test wearing a score's clothes - exactly
     what tier 1 turned out to be. `selective_failures` counts the other kind, and it
     is the number that says whether tier 2 discriminates or merely detects.

  3. THE DIAGNOSTIC-ONLY PROMOTION QUESTION. `layer.clears`, `score.rewards_clears` and
     `stage.completes` are measured and excluded, and promoting one is the obvious move
     when tier 2 saturates. It is answerable from disk and the answer is a number: a
     diagnostic whose stored value is the SAME on every submission of a group would
     move that group's score DOWN BY A CONSTANT and leave the spread at zero. Promoting
     it would look like a repair and change nothing measurable.

Usage:
    ./tier2_census.py --selftest
    ./tier2_census.py --runs-root <main checkout>/eval/runs
    ./tier2_census.py --runs-root ... --json

`--runs-root` is not optional and is not guessed, for the reason `tier1_census.py` gives:
`eval/runs/` is gitignored, so a worktree's copy is empty and the census would report a
confident, uniform "nothing ever failed" (rule 12).
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path


# --------------------------------------------------------------------------- #
# loading
# --------------------------------------------------------------------------- #

def load(runs_root: Path) -> list[dict]:
    """Every stored trial that recorded tier-2 criteria.

    A trial with no play-bot criteria is skipped rather than counted as all-passing.
    `total=0 passed=0` is indistinguishable from correct failure (rule 1), and the
    early single-stack runs predate the tier.

    `diagnostics` is read from the STORED playbot record rather than recomputed. The
    point of the promotion question is what the instrument actually recorded at the
    time, not what today's bot would say about a submission it has not driven.
    """
    rows = []
    for rep in sorted(runs_root.glob("*/artifacts/*/eval/report.json")):
        rec = json.loads(rep.read_text())
        pb = rec.get("playbot") or {}
        crits = pb.get("criteria") or []
        if not crits:
            continue
        rows.append({
            "run": rep.parents[3].name,
            "trial": rep.parents[1].name,
            "game": str(rec.get("game")),
            "stack": Path(str(rec.get("starter") or "")).name or "?",
            "t2": (rec.get("tier_scores") or {}).get("playbot"),
            "usable": bool(rec.get("playbot_usable", pb.get("usable", True))),
            "criteria": [{"id": c.get("id"),
                          "passed": bool(c.get("passed")),
                          "scored": bool(c.get("scored", True)),
                          "evidence": (c.get("evidence") or "")}
                         for c in crits],
            "diagnostics": dict(pb.get("diagnostics") or {}),
            "diagnostic_only": list(pb.get("diagnostic_only") or []),
        })
    return rows


# --------------------------------------------------------------------------- #
# 1. per criterion
# --------------------------------------------------------------------------- #

def per_criterion(rows: list[dict]) -> dict[tuple[str, str], dict]:
    """Keyed by (game, criterion id). NEVER pooled across games.

    The four games do not share a criterion set - `ball.moves` exists in one game and
    `piece.locks` in another - so a pooled table would report a criterion as scored on
    a fraction of the corpus and invite the reader to divide by the wrong n. It is the
    same reason `audit_criteria.py` insists on per-stack.
    """
    out: dict[tuple[str, str], dict] = {}
    for r in rows:
        for c in r["criteria"]:
            d = out.setdefault((r["game"], str(c["id"])),
                               {"scored_on": 0, "failed": 0, "unscored_on": 0,
                                "failed_trials": []})
            if not c["scored"]:
                d["unscored_on"] += 1
                continue
            d["scored_on"] += 1
            if not c["passed"]:
                d["failed"] += 1
                d["failed_trials"].append(f"{r['run']}/{r['trial']}")
    return out


# --------------------------------------------------------------------------- #
# 2. whole-trial vs selective
# --------------------------------------------------------------------------- #

def trial_failures(rows: list[dict]) -> list[dict]:
    """Per trial: how many scored criteria failed, and was it ALL of them?

    A trial that fails every criterion has not been discriminated by any of them - the
    probe never answered, or the state contract was not met, and one fact was recorded
    N times. Counting those as N criterion firings is how a tier that only DETECTS
    looks like a tier that RANKS.
    """
    out = []
    for r in rows:
        scored = [c for c in r["criteria"] if c["scored"]]
        bad = [c for c in scored if not c["passed"]]
        if not bad:
            continue
        out.append({
            "run": r["run"], "trial": r["trial"], "game": r["game"], "t2": r["t2"],
            "n_scored": len(scored), "n_failed": len(bad),
            "whole_trial": len(bad) == len(scored),
            "failed": [c["id"] for c in bad],
            "evidence": {c["id"]: c["evidence"][:160] for c in bad[:4]},
        })
    return out


def selective_failures(rows: list[dict]) -> list[dict]:
    return [t for t in trial_failures(rows) if not t["whole_trial"]]


# --------------------------------------------------------------------------- #
# 3. the groups, and the headline
# --------------------------------------------------------------------------- #

def groups(rows: list[dict]) -> list[dict]:
    """Per (run, game): how many distinct tier-2 values, among measurable trials.

    A trial whose play-bot tier is `usable: false` measured nothing, and `cmd_report`
    already excludes it from every aggregate. Including it here would let a submission
    that could not be driven manufacture the spread this tool exists to look for -
    fail-open, and the most flattering possible defect.
    """
    out = []
    for run, game in sorted({(r["run"], r["game"]) for r in rows}):
        g = [r for r in rows if r["run"] == run and r["game"] == game]
        live = [r for r in g if r["usable"] and r["t2"] is not None]
        vals = sorted({round(float(r["t2"]), 9) for r in live})
        # Which criteria actually differ across the group? That is the spread's cause.
        differing = []
        ids = {str(c["id"]) for r in live for c in r["criteria"] if c["scored"]}
        for cid in sorted(ids):
            seen = {c["passed"] for r in live for c in r["criteria"]
                    if str(c["id"]) == cid and c["scored"]}
            if len(seen) > 1:
                differing.append(cid)
        out.append({
            "run": run, "game": game, "n": len(g), "n_unmeasurable": len(g) - len(live),
            "t2_values": vals, "saturated": len(vals) <= 1 and len(live) > 1,
            "n_live": len(live), "differing_criteria": differing,
        })
    return out


def verdict(gs: list[dict]) -> str:
    return "SATURATED" if any(g["saturated"] for g in gs) else "SEPARATES"


# --------------------------------------------------------------------------- #
# 4. what promoting a diagnostic-only criterion would do
# --------------------------------------------------------------------------- #

def promotion_effect(rows: list[dict]) -> list[dict]:
    """For each (run, game, diagnostic criterion): would scoring it create SPREAD?

    Scoring an extra criterion changes each submission's score from p/n to
    (p+v)/(n+1). If `v` is the same for every submission in the group, the group's
    scores all move together: an ordering that was flat stays flat. The tool reports
    the distinct values, not a verdict about the criterion's worth - a diagnostic that
    is uniformly false may still be the right thing to fix, but fixing the RUBRIC by
    promoting it would not change what the group can rank.
    """
    out = []
    for run, game in sorted({(r["run"], r["game"]) for r in rows}):
        g = [r for r in rows if r["run"] == run and r["game"] == game and r["usable"]]
        if len(g) < 2:
            continue
        dids = sorted({d for r in g for d in r["diagnostic_only"]})
        for cid in dids:
            vals = [r["diagnostics"].get(cid) for r in g]
            present = [v for v in vals if v is not None]
            distinct = sorted({str(v) for v in present})
            out.append({
                "run": run, "game": game, "criterion": cid,
                "n": len(g), "n_recorded": len(present), "values": distinct,
                "creates_spread": len(distinct) > 1,
            })
    return out


# --------------------------------------------------------------------------- #
# rendering
# --------------------------------------------------------------------------- #

def render(rows: list[dict]) -> str:
    pc, gs = per_criterion(rows), groups(rows)
    tf, sf = trial_failures(rows), selective_failures(rows)
    L = [f"{len(rows)} stored trials carry tier-2 criteria", ""]

    L.append("--- per criterion, per game (never pooled across games) ---")
    for game in sorted({g for g, _ in pc}):
        ks = [k for k in pc if k[0] == game]
        L.append(f"\n  {game}")
        L.append(f"    {'criterion':<26}{'scored on':>11}{'failed':>8}"
                 f"{'unscored on':>13}")
        for k in sorted(ks, key=lambda k: (-pc[k]["failed"], k[1])):
            d = pc[k]
            L.append(f"    {k[1]:<26}{d['scored_on']:>11}{d['failed']:>8}"
                     f"{d['unscored_on']:>13}")
        never = [k[1] for k in ks if pc[k]["failed"] == 0 and pc[k]["scored_on"] > 0]
        L.append(f"    never failed: {len(never)} of "
                 f"{sum(1 for k in ks if pc[k]['scored_on'] > 0)} scored criteria")

    L.append("\n--- whole-trial vs selective failures ---")
    L.append("(a trial failing EVERY criterion recorded one fact N times; it was "
             "detected, not ranked)")
    L.append(f"  trials with any tier-2 failure : {len(tf)}")
    L.append(f"  of those, WHOLE-TRIAL          : {sum(1 for t in tf if t['whole_trial'])}")
    L.append(f"  of those, SELECTIVE            : {len(sf)}")
    for t in sf:
        L.append(f"    {t['run']}/{t['trial']}  t2={t['t2']}  "
                 f"{t['n_failed']}/{t['n_scored']} failed: {', '.join(t['failed'])}")

    L.append("\n--- per (run, game), among trials tier 2 could measure ---")
    L.append(f"{'run':<34}{'game':<15}{'n':>3}{'live':>5}{'t2 values':>11}  "
             f"saturated  criteria that differ")
    for g in gs:
        L.append(f"{g['run']:<34}{g['game']:<15}{g['n']:>3}{g['n_live']:>5}"
                 f"{len(g['t2_values']):>11}  {'YES' if g['saturated'] else 'no':<10} "
                 f"{', '.join(g['differing_criteria']) or '-'}")

    pe = promotion_effect(rows)
    L.append("\n--- would promoting a diagnostic-only criterion create SPREAD? ---")
    if not pe:
        L.append("  no group carries a diagnostic-only criterion")
    L.append(f"{'run':<34}{'game':<15}{'criterion':<22}{'n':>3}{'recorded':>10}"
             f"  values           spread?")
    for p in pe:
        L.append(f"{p['run']:<34}{p['game']:<15}{p['criterion']:<22}{p['n']:>3}"
                 f"{p['n_recorded']:>10}  {str(p['values']):<17}"
                 f"{'YES' if p['creates_spread'] else 'no'}")

    n_sat = sum(1 for g in gs if g["saturated"])
    L.append(f"\ngroups: {len(gs)}   saturated: {n_sat}   "
             f"selective failures over the whole corpus: {len(sf)}")
    L.append(f"VERDICT: {verdict(gs)}")
    if verdict(gs) == "SATURATED":
        L.append("  At least one group's only scored tier returns one number for every")
        L.append("  submission in it. That group ranks nothing, at any weight.")
    else:
        L.append("  Every group's scored tier takes more than one value.")
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
                 crits: list[tuple[str, bool, bool]],
                 diagnostics: dict | None = None,
                 usable: bool = True) -> None:
    d = root / run / "artifacts" / trial / "eval"
    d.mkdir(parents=True, exist_ok=True)
    scored = [(i, p) for i, p, s in crits if s]
    t2 = (sum(1 for _, p in scored if p) / len(scored)) if scored else 0.0
    pb = {
        "usable": usable, "score": t2,
        "diagnostic_only": sorted(diagnostics or {}),
        "diagnostics": dict(diagnostics or {}),
        "criteria": [{"id": i, "passed": p, "scored": s, "evidence": f"{i} ev"}
                     for i, p, s in crits],
    }
    (d / "report.json").write_text(json.dumps({
        "game": game, "starter": f"/somewhere/starters/{stack}",
        "tier_scores": {"programmatic": 1.0, "playbot": t2},
        "playbot_usable": usable, "playbot": pb,
    }))


def selftest() -> int:
    """A fixture whose census I can state before running it, then mutants.

    Rule 12's corollary: prove the extraction on one case whose true value you can
    state in advance. Every census defect this project has had returned the same wrong
    answer for every subject, which is what made them look like findings.
    """
    print("[fixture: 6 trials, answers stated before the tool runs]")
    ok3 = [("state.shape", True, True), ("ball.moves", True, True),
           ("match.ends", True, True)]
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        # gSat: three identical perfect trials + one diagnostic that is false on all
        # three. Saturated, and promoting the diagnostic cannot help.
        for st in ("a", "b", "c"):
            _write_trial(root, "runA", f"gSat__{st}__t0", "gSat", st, ok3,
                         diagnostics={"stage.completes": False})
        # gSel: one trial fails ONE criterion; one fails EVERY criterion.
        _write_trial(root, "runA", "gSel__a__t0", "gSel", "a", ok3)
        _write_trial(root, "runA", "gSel__b__t0", "gSel", "b",
                     [("state.shape", True, True), ("ball.moves", False, True),
                      ("match.ends", True, True)])
        _write_trial(root, "runA", "gSel__c__t0", "gSel", "c",
                     [(i, False, True) for i, _, _ in ok3])
        rows = load(root)

        expect("loads every trial that carries tier-2 criteria", len(rows) == 6,
               str(len(rows)))
        pc = per_criterion(rows)
        expect("ball.moves in gSel: scored on 3, failed 2",
               (pc[("gSel", "ball.moves")]["scored_on"],
                pc[("gSel", "ball.moves")]["failed"]) == (3, 2),
               str(pc[("gSel", "ball.moves")]))
        expect("the same id in gSat is counted SEPARATELY, never pooled",
               pc[("gSat", "ball.moves")]["failed"] == 0,
               str(pc[("gSat", "ball.moves")]))
        tf = trial_failures(rows)
        expect("two trials failed something", len(tf) == 2, str(len(tf)))
        expect("exactly one of them is whole-trial",
               sum(1 for t in tf if t["whole_trial"]) == 1, str(tf))
        expect("exactly one SELECTIVE failure - the number that says tier 2 ranked",
               len(selective_failures(rows)) == 1, str(selective_failures(rows)))
        gs = {g["game"]: g for g in groups(rows)}
        expect("gSat has one tier-2 value and is reported saturated",
               gs["gSat"]["t2_values"] == [1.0] and gs["gSat"]["saturated"],
               str(gs["gSat"]))
        expect("gSel varies and is not",
               len(gs["gSel"]["t2_values"]) == 3 and not gs["gSel"]["saturated"],
               str(gs["gSel"]))
        expect("the criterion behind gSel's spread is named",
               gs["gSel"]["differing_criteria"] == ["ball.moves", "match.ends",
                                                    "state.shape"],
               str(gs["gSel"]["differing_criteria"]))
        expect("fixture verdict is SATURATED", verdict(groups(rows)) == "SATURATED")
        pe = {(p["game"], p["criterion"]): p for p in promotion_effect(rows)}
        expect("promoting a uniformly-false diagnostic creates NO spread",
               pe[("gSat", "stage.completes")]["values"] == ["False"]
               and not pe[("gSat", "stage.completes")]["creates_spread"],
               str(pe[("gSat", "stage.completes")]))

        # POSITIVE CONTROL for the headline. A verdict that is always SATURATED is
        # worth nothing, and neither is a promotion check that always says "no".
        print("\n[positive control: a group that varies, and a diagnostic that would "
              "create spread]")
        _write_trial(root, "runB", "gVar__a__t0", "gVar", "a", ok3,
                     diagnostics={"stage.completes": True})
        _write_trial(root, "runB", "gVar__b__t0", "gVar", "b",
                     [("state.shape", True, True), ("ball.moves", False, True),
                      ("match.ends", True, True)],
                     diagnostics={"stage.completes": False})
        rows2 = [r for r in load(root) if r["run"] == "runB"]
        expect("the tool reports SEPARATES when no group is flat",
               verdict(groups(rows2)) == "SEPARATES", str(groups(rows2)))
        pe2 = promotion_effect(rows2)[0]
        expect("and reports that promoting THIS diagnostic would create spread",
               pe2["creates_spread"] and pe2["values"] == ["False", "True"], str(pe2))

        # VARIANT: an unmeasurable trial must not manufacture the spread.
        print("\n[variant: a trial that measured nothing is not a low score]")
        _write_trial(root, "runC", "gU__a__t0", "gU", "a", ok3)
        _write_trial(root, "runC", "gU__b__t0", "gU", "b", ok3)
        _write_trial(root, "runC", "gU__c__t0", "gU", "c",
                     [(i, False, True) for i, _, _ in ok3], usable=False)
        rowsC = [r for r in load(root) if r["run"] == "runC"]
        gU = groups(rowsC)[0]
        expect("the unusable trial is held out, and the group is still saturated",
               gU["n_unmeasurable"] == 1 and gU["t2_values"] == [1.0]
               and gU["saturated"], str(gU))

        # MUTANTS. Each removes one mechanism; the expectation above must go red.
        print("\n[mutants: can these checks fail?]")
        g = globals()

        original_groups = g["groups"]

        def ignore_usable(rs):
            out = []
            for run, game in sorted({(r["run"], r["game"]) for r in rs}):
                grp = [r for r in rs if r["run"] == run and r["game"] == game
                       and r["t2"] is not None]
                vals = sorted({round(float(r["t2"]), 9) for r in grp})
                out.append({"run": run, "game": game, "n": len(grp),
                            "n_unmeasurable": 0, "t2_values": vals,
                            "saturated": len(vals) <= 1 and len(grp) > 1,
                            "n_live": len(grp), "differing_criteria": []})
            return out

        g["groups"] = ignore_usable
        caught = not groups(rowsC)[0]["saturated"]
        g["groups"] = original_groups
        expect("mutant 'count unmeasurable trials' fabricates a spread, and is caught",
               caught)

        original_sel = g["selective_failures"]
        g["selective_failures"] = lambda rs: trial_failures(rs)
        caught = len(selective_failures(rows)) == 2
        g["selective_failures"] = original_sel
        expect("mutant 'a whole-trial failure counts as discrimination' is caught",
               caught)

        original_pc = g["per_criterion"]

        def pool_games(rs):
            out: dict = {}
            for r in rs:
                for c in r["criteria"]:
                    d = out.setdefault(("*", str(c["id"])),
                                       {"scored_on": 0, "failed": 0, "unscored_on": 0,
                                        "failed_trials": []})
                    d["scored_on"] += 1
                    if not c["passed"]:
                        d["failed"] += 1
            return out

        g["per_criterion"] = pool_games
        caught = ("gSel", "ball.moves") not in per_criterion(rows)
        g["per_criterion"] = original_pc
        expect("mutant 'pool the games' loses the per-game split, and is caught", caught)

    print(f"\n{CHECKS - len(FAILS)}/{CHECKS} expectations held")
    if FAILS:
        print("FAILED: " + ", ".join(FAILS))
        return 1
    print("tier2_census selftest: OK")
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
        print(f"no stored trials with tier-2 criteria under {a.runs_root}",
              file=sys.stderr)
        return 1
    if a.json:
        print(json.dumps({
            "n_trials": len(rows),
            "per_criterion": {f"{g}/{c}": v for (g, c), v in per_criterion(rows).items()},
            "trial_failures": trial_failures(rows),
            "selective_failures": selective_failures(rows),
            "groups": groups(rows),
            "promotion_effect": promotion_effect(rows),
            "verdict": verdict(groups(rows))}, indent=2))
    else:
        print(render(rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
