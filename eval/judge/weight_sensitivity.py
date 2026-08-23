#!/usr/bin/env python3
"""Is the 0.31/0.69 tier split load-bearing, or is it a free parameter?

`overall = 0.31*tier1 + 0.69*tier2`. Nothing in `RUBRIC.md`, `JUDGING.md`,
`DECISIONS.md` or `README.md` says where 0.31 came from, and no stored result
says whether anything would change if it were 0.20 or 0.50. A weight that has
never been varied is indistinguishable from a weight that does not matter -
and those two states call for opposite actions.

This sweeps w1 (the programmatic weight) across [0, 1] against STORED tier
scores and reports, per (run, game), every distinct ordering of stacks that
the sweep produces and the w1 at which each crossover happens. It costs
nothing, re-runs offline, and can come out either way.

WHAT THIS IS NOT. `DECISIONS.md` bars the deterministic tiers from ranking
stacks at any gap - 0 of 380 within-cell verdicts differ, so the instrument
has no within-cell resolution. This tool therefore does NOT publish a stack
ranking and its orderings are not results. It asks one narrower question:
*if someone did read an ordering off these numbers, would the tier weight
change which ordering they read?* A weight that cannot change the answer is
a weight that needs no defence. A weight that can change it needs one badly.

Three outcomes, all informative:

  UNIDENTIFIABLE  tier 1 has zero variance across the trials being compared,
                  so `overall` is an affine function of tier 2 alone and w1
                  cannot move anything. The number 0.31 is inert HERE.
  STABLE          tier 1 varies, and every w1 in (0,1) yields one ordering.
                  The choice of weight is defensible by not mattering.
  FLIPS           some crossover lies inside (0,1). The published `overall`
                  is then partly a statement about the weight, and the weight
                  has no stated derivation.

Usage:
    ./weight_sensitivity.py --selftest
    ./weight_sensitivity.py <run-dir> [<run-dir> ...]
    ./weight_sensitivity.py --all          # every run under eval/runs/

--selftest is not optional decoration. A sweep that reports STABLE on
everything is indistinguishable from a sweep that cannot detect a flip, which
is the exact failure mode this repository is built around. The self-test
feeds it a constructed crossover and requires it to be found.
"""
from __future__ import annotations

import argparse
import glob
import json
import sys
from pathlib import Path

# Step is fine enough that a crossover narrower than this is reported as a tie
# rather than missed: see `_orderings`, which records the bracketing w1 pair.
STEP = 0.005
EPS = 1e-9


# --------------------------------------------------------------------------- #
# loading
# --------------------------------------------------------------------------- #

def load_trials(run_dir: Path) -> list[dict]:
    """Stored per-trial tier scores, with the same exclusions `cmd_report` applies.

    A play-bot tier that measured nothing is excluded rather than folded in as
    0.0 - it can only happen on the stacks that take a project-wide lock, so
    counting it is bias and not noise (FINDINGS #25). Excluded trials are
    returned too, flagged, so the caller can report n per group instead of
    silently averaging over a population it never established (rule 4).
    """
    out = []
    for rep in sorted(run_dir.glob("artifacts/*/eval/report.json")):
        rec = json.loads(rep.read_text())
        tiers = rec.get("tier_scores") or {}
        if "programmatic" not in tiers or "playbot" not in tiers:
            continue
        starter = rec.get("starter") or ""
        out.append({
            "run": run_dir.name,
            "game": rec.get("game"),
            "stack": Path(str(starter)).name or "?",
            "t1": float(tiers["programmatic"]),
            "t2": float(tiers["playbot"]),
            # Absent in pre-2026-08-14 records; `evaluate.py` defaults it True.
            "usable": bool(rec.get("playbot_usable", True)),
        })
    return out


# --------------------------------------------------------------------------- #
# the sweep
# --------------------------------------------------------------------------- #

def _ordering(means: dict[str, float], tol: float = 1e-6) -> tuple[tuple[str, ...], ...]:
    """Stacks ranked high to low, ties grouped. Grouping ties matters: a tie
    that becomes a strict order is a real change, and a strict order that
    becomes a tie is not the same event as a reversal."""
    groups: list[list[str]] = []
    for name in sorted(means, key=lambda k: (-means[k], k)):
        if groups and abs(means[groups[-1][0]] - means[name]) <= tol:
            groups[-1].append(name)
        else:
            groups.append([name])
    return tuple(tuple(sorted(g)) for g in groups)


def sweep(trials: list[dict]) -> dict:
    """Sweep w1 over the OPEN interval (0,1) for one homogeneous group.

    The endpoints are excluded deliberately and this is not a rounding
    convenience. w1=0 discards tier 1 and w1=1 discards tier 2; neither is a
    candidate weighting, both collapse ties that no real weight collapses, and
    including them made the first version of this tool report FLIPS on three
    groups whose ordering is in fact identical at every weight anyone would
    choose. A check that fires where nothing is wrong burns exactly the
    attention that a check firing correctly needs.

    Endpoint orderings are still computed and reported separately, because
    "everything ties once tier 2 is dropped" is a fact about tier 1's
    discriminating power and worth seeing - it is just not a weight flip.
    """
    scored = [t for t in trials if t["usable"]]
    stacks = sorted({t["stack"] for t in scored})
    per_stack = {s: [t for t in scored if t["stack"] == s] for s in stacks}

    t1_vals = {round(t["t1"], 9) for t in scored}
    t2_vals = {round(t["t2"], 9) for t in scored}

    def means_at(w: float) -> dict[str, float]:
        return {
            s: sum(w * t["t1"] + (1.0 - w) * t["t2"] for t in ts) / len(ts)
            for s, ts in per_stack.items() if ts
        }

    seen: list[tuple[float, tuple]] = []
    w = STEP
    while w <= 1.0 - STEP + EPS:
        o = _ordering(means_at(w))
        if not seen or seen[-1][1] != o:
            seen.append((round(w, 6), o))
        w += STEP

    distinct = {o for _, o in seen}

    if len(t1_vals) <= 1:
        verdict = "UNIDENTIFIABLE"
    elif len(distinct) == 1:
        verdict = "STABLE"
    else:
        verdict = "FLIPS"

    return {
        "n_scored": len(scored),
        "n_excluded": len(trials) - len(scored),
        "stacks": stacks,
        "n_per_stack": {s: len(ts) for s, ts in per_stack.items()},
        "t1_distinct_values": len(t1_vals),
        "t2_distinct_values": len(t2_vals),
        "verdict": verdict,
        "transitions": seen,
        "n_distinct_orderings": len(distinct),
        "endpoint_w1_0": _ordering(means_at(0.0)),   # tier 2 alone
        "endpoint_w1_1": _ordering(means_at(1.0)),   # tier 1 alone
    }


def group_key(t: dict) -> tuple[str, str]:
    return (t["run"], str(t["game"]))


def analyse(trials: list[dict]) -> list[tuple[tuple[str, str], dict]]:
    """Partition by (run, game) BEFORE sweeping.

    Two games are not one population and a mean across them describes nothing
    (rule 4). The partition is the reason this reports a dozen small groups
    rather than one confident line.
    """
    keys = sorted({group_key(t) for t in trials})
    return [(k, sweep([t for t in trials if group_key(t) == k])) for k in keys]


def fmt_ordering(o: tuple) -> str:
    return " > ".join("=".join(g) for g in o)


def render(rows: list[tuple[tuple[str, str], dict]]) -> str:
    lines = []
    for (run, game), r in rows:
        head = f"{run}  {game}  n={r['n_scored']}"
        if r["n_excluded"]:
            head += f" (excluded {r['n_excluded']} unusable)"
        lines.append(head)
        lines.append(f"  per stack: {r['n_per_stack']}")
        lines.append(f"  distinct tier-1 values: {r['t1_distinct_values']}"
                     f"   tier-2: {r['t2_distinct_values']}")
        lines.append(f"  VERDICT: {r['verdict']}"
                     f"   orderings across w1 in (0,1): {r['n_distinct_orderings']}")
        for w, o in r["transitions"]:
            lines.append(f"    w1 >= {w:<6} : {fmt_ordering(o)}")
        lines.append(f"    [endpoint w1=0, tier 2 alone] {fmt_ordering(r['endpoint_w1_0'])}")
        lines.append(f"    [endpoint w1=1, tier 1 alone] {fmt_ordering(r['endpoint_w1_1'])}")
        lines.append("")
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# self-test: the sweep must be able to FIND a flip, not merely fail to find one
# --------------------------------------------------------------------------- #

def _mk(run, game, stack, t1, t2, usable=True):
    return {"run": run, "game": game, "stack": stack,
            "t1": t1, "t2": t2, "usable": usable}


def selftest() -> int:
    failures = []

    def check(name, cond, detail=""):
        if cond:
            print(f"  PASS  {name}")
        else:
            print(f"  FAIL  {name}  {detail}")
            failures.append(name)

    # POSITIVE CONTROL. Constructed so the two tiers disagree and the crossover
    # sits at w1 = 0.5 exactly: A is better on tier 2, B is better on tier 1, by
    # equal margins. If the sweep cannot find this, every STABLE it ever reports
    # is worthless.
    pc = [_mk("pc", "g", "A", 0.60, 1.00), _mk("pc", "g", "B", 1.00, 0.60)]
    r = sweep(pc)
    check("positive control: a real crossover is FOUND",
          r["verdict"] == "FLIPS", f"got {r['verdict']}")
    # A crossover passes THROUGH a tie, so a clean reversal is three orderings
    # and not two: A>B, then A=B at the crossing weight, then B>A. Asserting two
    # here was wrong about the geometry, and the sweep was right.
    check("positive control: three orderings (a reversal crosses a tie)",
          r["n_distinct_orderings"] == 3, f"got {r['n_distinct_orderings']}")
    seq = [o for _, o in r["transitions"]]
    check("positive control: the ordering actually reverses through a tie",
          seq == [(("A",), ("B",)), (("A", "B"),), (("B",), ("A",))],
          " -> ".join(fmt_ordering(o) for o in seq))
    tie_w = r["transitions"][1][0]
    check("positive control: crossover located near w1=0.5",
          abs(tie_w - 0.5) <= STEP + EPS, f"reported {tie_w}")

    # UNIDENTIFIABLE. Tier 1 constant is the shape every stored matrix run has.
    ui = [_mk("ui", "g", "A", 1.0, 0.9), _mk("ui", "g", "B", 1.0, 0.7)]
    r = sweep(ui)
    check("tier-1 constant is reported UNIDENTIFIABLE, not STABLE",
          r["verdict"] == "UNIDENTIFIABLE", f"got {r['verdict']}")

    # STABLE. Both tiers vary and they agree on the order: no weight can flip it.
    st = [_mk("st", "g", "A", 1.0, 1.0), _mk("st", "g", "B", 0.5, 0.5)]
    r = sweep(st)
    check("agreeing tiers with real variance are STABLE",
          r["verdict"] == "STABLE" and r["n_distinct_orderings"] == 1,
          f"got {r['verdict']} / {r['n_distinct_orderings']}")

    # A crossover that lands OUTSIDE (0,1) must not be reported as a flip. Here
    # A dominates B on both tiers, so the lines never meet in range.
    out = [_mk("o", "g", "A", 0.9, 1.0), _mk("o", "g", "B", 0.4, 0.5)]
    r = sweep(out)
    check("dominated pair does not manufacture a flip",
          r["verdict"] == "STABLE", f"got {r['verdict']}")

    # Exclusion: an unusable play-bot tier must not be averaged in as 0.0.
    ex = [_mk("e", "g", "A", 1.0, 1.0), _mk("e", "g", "A", 1.0, 0.0, usable=False),
          _mk("e", "g", "B", 1.0, 0.5)]
    r = sweep(ex)
    check("unusable trials are excluded and counted",
          r["n_scored"] == 2 and r["n_excluded"] == 1,
          f"scored={r['n_scored']} excluded={r['n_excluded']}")

    # Ties are grouped, not broken arbitrarily by name.
    tie = [_mk("t", "g", "A", 1.0, 1.0), _mk("t", "g", "B", 1.0, 1.0),
           _mk("t", "g", "C", 0.5, 0.4)]
    r = sweep(tie)
    check("equal stacks are reported as a tie group",
          r["transitions"][0][1][0] == ("A", "B"),
          f"got {fmt_ordering(r['transitions'][0][1])}")

    # REGRESSION GUARD for the endpoint false positive. A and B tie on tier 2
    # and differ on tier 1, so at w1=0 exactly they tie and at every w1>0 they
    # do not. The first version of this tool swept the closed interval and
    # called that a FLIP; it is not one, because w1=0 is not a candidate weight.
    # This is the shape of 3 of the 10 real stored groups.
    ep = [_mk("ep", "g", "A", 1.0, 1.0), _mk("ep", "g", "B", 0.5, 1.0)]
    r = sweep(ep)
    check("endpoint-only tie is NOT reported as a flip",
          r["verdict"] == "STABLE" and r["n_distinct_orderings"] == 1,
          f"got {r['verdict']} / {r['n_distinct_orderings']}")
    check("endpoint orderings are still reported",
          r["endpoint_w1_0"] == (("A", "B"),) and r["endpoint_w1_1"] == (("A",), ("B",)),
          f"w1=0 {fmt_ordering(r['endpoint_w1_0'])} / "
          f"w1=1 {fmt_ordering(r['endpoint_w1_1'])}")

    # Partitioning: two games must not be swept as one population.
    mixed = [_mk("m", "g1", "A", 1.0, 1.0), _mk("m", "g2", "A", 0.2, 0.2)]
    check("partitions by (run, game)", len(analyse(mixed)) == 2,
          f"got {len(analyse(mixed))} groups")

    print()
    if failures:
        print(f"SELFTEST FAILED: {len(failures)} check(s): {', '.join(failures)}")
        return 1
    print("SELFTEST PASSED")
    return 0


# --------------------------------------------------------------------------- #

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("run_dirs", nargs="*", type=Path)
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--all", action="store_true",
                    help="every run directory under eval/runs/")
    ap.add_argument("--runs-root", type=Path, default=None,
                    help="where eval/runs/ actually is. Needed inside a git "
                         "worktree: eval/runs/ is gitignored, so it exists only "
                         "in the main checkout and a worktree's copy of this "
                         "path is empty. The address is an input to the check "
                         "(FINDINGS #60) - this refuses to guess.")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    if a.selftest:
        return selftest()

    dirs = list(a.run_dirs)
    if a.all:
        root = a.runs_root or (Path(__file__).resolve().parents[1] / "runs")
        if not root.is_dir():
            print(f"--all: no run store at {root}\n"
                  f"eval/runs/ is gitignored (129G of evidence), so it is absent "
                  f"in a worktree.\nPass --runs-root pointing at the main "
                  f"checkout's eval/runs/.", file=sys.stderr)
            return 2
        dirs += [p for p in sorted(root.iterdir())
                 if p.is_dir() and (p / "artifacts").is_dir()]
    if not dirs:
        ap.error("give at least one run directory, or --all, or --selftest")

    trials: list[dict] = []
    for d in dirs:
        trials += load_trials(d)
    if not trials:
        print("no stored tier scores found in the given runs", file=sys.stderr)
        return 1

    rows = analyse(trials)
    if a.json:
        print(json.dumps([{"run": k[0], "game": k[1], **v} for k, v in rows],
                         indent=2, default=list))
    else:
        print(render(rows))
        verdicts = [v["verdict"] for _, v in rows]
        print(f"groups: {len(rows)}   "
              f"FLIPS={verdicts.count('FLIPS')}  "
              f"STABLE={verdicts.count('STABLE')}  "
              f"UNIDENTIFIABLE={verdicts.count('UNIDENTIFIABLE')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
