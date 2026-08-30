#!/usr/bin/env python3
"""Recompute `overall` for already-evaluated trials from STORED tier data.

The judge tier's weight was ruled to zero after some evaluations had already been
written. Re-running them would cost money and, worse, would produce different judge
verdicts (the tier is stochastic - measured spread 0.308 on a contested submission),
so a re-run would silently change more than the weighting.

This reads the per-tier JSON that is already on disk and rebuilds `report.json` from
it. That is exactly what SWE-bench's `rewrite_reports` exists for, and what this
repository's own `regrade.py` does for the small-task suite: fix a grading rule
without paying for new rollouts.

Usage:
    ./regrade_wholegame.py <run-dir> [--write]
    ./regrade_wholegame.py --selftest

A run directory that does not exist, and one that holds no
`artifacts/*/eval/report.json`, must be REFUSED - nonzero exit, reason on stderr,
success line never printed. On 2026-08-30 both shapes printed the empty table plus
"0 report(s) inspected (dry run; pass --write)" and exited 0, so missing dir, empty
dir and real run dir were indistinguishable from the output and exit 0 read as
completion; under `--write` that is a regrade believed done that was not done.
`weight_sensitivity.py` (exit 1 on an empty population) and `tier1_census.py`
(exit 2 on a missing store) refuse the same input. `--selftest` pins the refusals,
the green path and the regime guard on fixtures, and carries the mutant that removes
the guards and must turn the refusal checks red.
"""
from __future__ import annotations

import argparse, json, os, re, subprocess, sys, tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from evaluate import (  # noqa: E402
    DIAGNOSTIC_TIERS, GATE_TIER, SCORING_REGIME, WEIGHTS, gate_verdict, overall_score,
)


def _atomic(path: Path, obj) -> None:
    tmp = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps(obj, indent=2))
    os.replace(tmp, path)


def regrade(run_dir: Path, write: bool, accept_regime_change: bool = False) -> int:
    # A path that cannot hold a run directory is refused the way tier1_census.py
    # refuses a missing store (exit 2); see the module docstring for what exit 0
    # read as on this input before 2026-08-30.
    if not run_dir.is_dir():  # GUARD-MISSING-DIR
        print(f"no run directory at {run_dir}", file=sys.stderr)
        return 2
    rows = []
    crossings = []
    for rep in sorted(run_dir.glob("artifacts/*/eval/report.json")):
        rec = json.loads(rep.read_text())
        # Rebuild tier scores from the tier files themselves, not from the embedded
        # copy - the embedded copy is what we are correcting.
        d = rep.parent
        tiers = {}
        for name, fn in (("programmatic", "programmatic.json"),
                         ("playbot", "playbot.json"), ("judge", "judge.json")):
            f = d / fn
            tiers[name] = json.loads(f.read_text()) if f.exists() and f.stat().st_size else {}
        scores = {k: float(tiers[k].get("score", 0.0)) for k in (GATE_TIER, *WEIGHTS)}
        new_overall = overall_score(scores)
        old_overall = rec.get("overall")
        rows.append((rep.parent.parent.name, old_overall, new_overall,
                     float(tiers["judge"].get("score", 0.0))))
        # A REGRADE ACROSS A REGIME BOUNDARY IS NOT A REGRADE, IT IS A RE-SCORING.
        #
        # Tier 1 stopped being 0.31 of `overall` on 2026-08-23 and became a gate. This
        # tool exists to fix a grading BUG without paying for new rollouts; run over a
        # record written under the old scheme it would silently convert it, leaving a
        # run directory whose trials are half one regime and half the other with
        # nothing on disk saying which is which. The regimes are recorded, not
        # rewritten (eval/RUNS.md), so this refuses unless told explicitly.
        if rec.get("scoring_regime") != SCORING_REGIME:
            crossings.append(rep.parent.parent.name)
            if not accept_regime_change:
                continue
        if write:
            for k, v in tiers.items():
                if v:
                    rec[k] = v
            rec["tier_scores"] = scores
            rec["diagnostic_scores"] = {k: float(tiers[k].get("score", 0.0))
                                        for k in DIAGNOSTIC_TIERS if tiers.get(k)}
            rec["weights"] = dict(WEIGHTS)
            rec["gate"] = gate_verdict(tiers.get(GATE_TIER) or {})
            rec["scoring_regime"] = SCORING_REGIME
            rec["judge_is_diagnostic_only"] = True
            # RECOMPUTE THE UNMEASURED-TIER GUARD, never inherit it.
            # `cmd_report` excludes a trial from every aggregate when its play-bot tier
            # measured nothing (usable=false), because a 0.00 on the only scored tier
            # that was never driven is not a score. Regrading rebuilds report.json, so a
            # report that predates the field - or one regraded from a run that had it -
            # would silently lose the flag and the guard would stop firing with no sign
            # that it had. That is a fail-open regression of exactly the class in
            # FINDINGS #31: it excuses a trial back into the aggregates.
            pb = tiers.get("playbot") or {}
            rec["playbot_usable"] = bool(pb.get("usable", True))
            rec["playbot_unscored"] = pb.get("unscored") or {}
            rec["overall"] = new_overall
            rec.pop("overall_no_judge", None)
            rec["regraded"] = (f"`overall` recomputed from stored tier data under "
                               f"{SCORING_REGIME}; nothing re-run")
            _atomic(rep, rec)
    # An empty population is refused the way weight_sensitivity.py refuses one
    # (exit 1): a directory holding nothing the glob reads must not reach the
    # table and the success line below.
    if not rows:  # GUARD-EMPTY-POPULATION
        print(f"no report(s) found under {run_dir} "
              f"(want artifacts/*/eval/report.json)", file=sys.stderr)
        return 1
    print(f"{'trial':<30}{'old overall':>12}{'new overall':>12}{'judge (diag)':>14}")
    for tid, o, n, j in rows:
        mark = "" if o is None or abs(o - n) < 1e-9 else "  *"
        print(f"{tid:<30}{(f'{o:.4f}' if o is not None else '-'):>12}{n:>12.4f}"
              f"{j:>14.3f}{mark}")
    if crossings:
        print(f"\n*** {len(crossings)} report(s) were scored under a DIFFERENT REGIME "
              f"than {SCORING_REGIME}.")
        print("    Tier 1 was 0.31 of `overall` before 2026-08-23 and is a gate after "
              "it, so\n    rewriting them changes the scheme, not a grading bug. "
              "They were LEFT ALONE.")
        print("    Pass --accept-regime-change to re-score them anyway, and record it "
              "in eval/RUNS.md.")
    print(f"\n{len(rows) - (0 if accept_regime_change else len(crossings))} report(s) "
          f"{'rewritten' if write else 'inspected (dry run; pass --write)'}"
          + (f"; {len(crossings)} held back at the regime boundary" if crossings
             and not accept_regime_change else ""))
    return 0


# --------------------------------------------------------------------------- #
# --selftest. Fixtures whose answers are stated before they run, plus the
# mutant that removes the refusal guards out of this file's own source and must
# turn them red. Offline, no corpus, no `just`, a couple of seconds.
# --------------------------------------------------------------------------- #

_SUCCESS_DRY = "report(s) inspected (dry run; pass --write)"
_SUCCESS_WRITE = "report(s) rewritten"


def _make_report(root: Path, trial: str,
                 regime: str | None = SCORING_REGIME) -> Path:
    """One minimal trial grading under `root`, in the layout the glob reads."""
    d = root / "artifacts" / trial / "eval"
    d.mkdir(parents=True)
    rec: dict = {"trial": trial, "overall": 0.5}
    if regime is not None:
        rec["scoring_regime"] = regime
    p = d / "report.json"
    p.write_text(json.dumps(rec, indent=2))
    return p


class _Checks:
    def __init__(self) -> None:
        self.n = 0
        self.fails: list[str] = []

    def expect(self, name: str, cond: bool) -> None:
        self.n += 1
        if not cond:
            self.fails.append(name)


def _run(*args: str, script: Path | None = None,
         pythonpath: str | None = None) -> tuple[int, str, str]:
    env = dict(os.environ)
    if pythonpath:
        env["PYTHONPATH"] = pythonpath + os.pathsep + env.get("PYTHONPATH", "")
    p = subprocess.run([sys.executable, str(script or Path(__file__).resolve()), *args],
                       capture_output=True, text=True, env=env, timeout=120)
    return p.returncode, p.stdout, p.stderr


def _selftest() -> int:
    c = _Checks()
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        # The two failing shapes the tool used to answer with the success line.
        missing = tmp / "no-such-run-dir"
        empty = tmp / "empty-run"
        empty.mkdir()
        # ...and the third: artifacts exist, but nothing the glob reads.
        noeval = tmp / "artifacts-only"
        (noeval / "artifacts" / "t0").mkdir(parents=True)
        # Positive controls: one current-regime report, dry run and --write.
        green = tmp / "green-run"
        green_report = _make_report(green, "g__ts__t0")
        green_before = green_report.read_bytes()
        wrote = tmp / "write-run"
        wrote_report = _make_report(wrote, "w__ts__t0")
        # The regime guard: a pre-gate record carries no scoring_regime.
        pregate = tmp / "pregate-run"
        pregate_report = _make_report(pregate, "p__ts__t0", regime=None)
        pregate_before = pregate_report.read_bytes()

        for name, target in (("missing dir", missing), ("report-free dir", empty),
                             ("artifacts-without-report dir", noeval)):
            rc, out, err = _run(str(target))
            c.expect(f"{name} exits nonzero", rc != 0)
            c.expect(f"{name} prints no success line",
                     _SUCCESS_DRY not in out and _SUCCESS_WRITE not in out)
        rc, out, err = _run(str(missing))
        c.expect("missing dir names the path on stderr", str(missing) in err)

        rc, out, err = _run(str(green))
        c.expect("green dry run exits 0", rc == 0)
        c.expect("green dry run prints the success line",
                 f"1 {_SUCCESS_DRY}" in out)
        c.expect("green dry run lists the trial", "g__ts__t0" in out)
        c.expect("green dry run writes nothing",
                 green_report.read_bytes() == green_before)

        rc, out, err = _run("--write", str(wrote))
        c.expect("green --write exits 0", rc == 0)
        c.expect("green --write prints the rewritten line",
                 f"1 {_SUCCESS_WRITE}" in out)
        rec = json.loads(wrote_report.read_text())
        c.expect("green --write rebuilt the record under the current regime",
                 rec.get("regraded") is not None
                 and rec.get("scoring_regime") == SCORING_REGIME)

        rc, out, err = _run(str(pregate))
        c.expect("pregate dry run exits 0", rc == 0)
        c.expect("pregate dry run LEFT ALONE", "LEFT ALONE" in out)
        c.expect("pregate dry run holds the report back",
                 "1 held back at the regime boundary" in out)
        c.expect("pregate dry run writes nothing",
                 pregate_report.read_bytes() == pregate_before)

        # THE MUTANT. Excise both guarded blocks from this file's own source and run
        # the mutated copy: the refusals must disappear, which is the check failing.
        # (A mutant asks whether a check CAN fail; the green rows above are the half
        # that asks whether it can still pass.)
        here = str(Path(__file__).resolve().parent)
        src = Path(__file__).read_text()
        for marker in ("GUARD-MISSING-DIR", "GUARD-EMPTY-POPULATION"):
            c.expect(f"guard marker {marker} present in source", marker in src)
        mut = re.sub(r"\n    if not [^\n]*# GUARD-MISSING-DIR\n(?:        [^\n]*\n)+",
                     "\n", src)
        mut = re.sub(r"\n    if not [^\n]*# GUARD-EMPTY-POPULATION\n"
                     r"(?:        [^\n]*\n)+", "\n", mut)
        # The structural half of the mutant row: the excision must have fired. The
        # behavioural rows below are what pins the refusals to the guard - this row
        # only says the mutated copy is not the shipped source. (The guard's own
        # strings cannot be searched for in `mut` from here: this selftest's code
        # carries them too, and the search would find the searcher - task 113's
        # shared-object trap, one level down.)
        c.expect("mutation changed the source", mut != src)
        mutpath = tmp / "mutant" / "regrade_wholegame.py"
        mutpath.parent.mkdir()
        mutpath.write_text(mut)
        rc, out, err = _run(str(green), script=mutpath, pythonpath=here)
        c.expect("mutant still passes the green fixture", rc == 0
                 and f"1 {_SUCCESS_DRY}" in out)
        for name, target in (("missing dir", missing), ("report-free dir", empty),
                             ("artifacts-without-report dir", noeval)):
            rc, out, err = _run(str(target), script=mutpath, pythonpath=here)
            c.expect(f"MUTANT: {name} no longer refused (check can fail)",
                     rc == 0 and _SUCCESS_DRY in out)
            c.expect(f"MUTANT: {name} reported as done",
                     "0 report(s) inspected" in out)

    print(f"\n{c.n - len(c.fails)}/{c.n} expectations held")
    if c.fails:
        print("FAILED: " + ", ".join(c.fails))
        return 1
    print("regrade_wholegame selftest: OK")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir", type=Path, nargs="?")
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--accept-regime-change", action="store_true",
                    help="re-score records written under the pre-2026-08-23 weighted "
                         "scheme into the gate regime. This is a RE-SCORING, not a "
                         "regrade: say so in eval/RUNS.md wherever the run is cited.")
    ap.add_argument("--selftest", action="store_true",
                    help="run the offline fixture suite, including the mutant that "
                         "removes the refusal guards")
    a = ap.parse_args()
    if a.selftest:
        raise SystemExit(_selftest())
    if a.run_dir is None:
        ap.error("run_dir is required (or --selftest)")
    raise SystemExit(regrade(a.run_dir.resolve(), a.write, a.accept_regime_change))
