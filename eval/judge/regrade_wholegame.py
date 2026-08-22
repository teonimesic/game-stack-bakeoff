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

Usage: ./regrade_wholegame.py <run-dir> [--write]
"""
from __future__ import annotations

import argparse, json, os, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from evaluate import WEIGHTS, DIAGNOSTIC_TIERS  # noqa: E402


def _atomic(path: Path, obj) -> None:
    tmp = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps(obj, indent=2))
    os.replace(tmp, path)


def regrade(run_dir: Path, write: bool) -> int:
    rows = []
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
        scores = {k: float(tiers[k].get("score", 0.0)) for k in WEIGHTS}
        new_overall = round(sum(WEIGHTS[k] * scores[k] for k in WEIGHTS), 4)
        old_overall = rec.get("overall")
        rows.append((rep.parent.parent.name, old_overall, new_overall,
                     float(tiers["judge"].get("score", 0.0))))
        if write:
            for k, v in tiers.items():
                if v:
                    rec[k] = v
            rec["tier_scores"] = scores
            rec["diagnostic_scores"] = {k: float(tiers[k].get("score", 0.0))
                                        for k in DIAGNOSTIC_TIERS if tiers.get(k)}
            rec["weights"] = dict(WEIGHTS)
            rec["judge_is_diagnostic_only"] = True
            # RECOMPUTE THE UNMEASURED-TIER GUARD, never inherit it.
            # `cmd_report` excludes a trial from every aggregate when its play-bot tier
            # measured nothing (usable=false), because a 0.00 on a 0.69-weighted tier
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
            rec["regraded"] = ("judge weight set to zero by user ruling; `overall` "
                               "recomputed from stored tier data, nothing re-run")
            _atomic(rep, rec)
    print(f"{'trial':<30}{'old overall':>12}{'new overall':>12}{'judge (diag)':>14}")
    for tid, o, n, j in rows:
        mark = "" if o is None or abs(o - n) < 1e-9 else "  *"
        print(f"{tid:<30}{(f'{o:.4f}' if o is not None else '-'):>12}{n:>12.4f}"
              f"{j:>14.3f}{mark}")
    print(f"\n{len(rows)} report(s) "
          f"{'rewritten' if write else 'inspected (dry run; pass --write)'}")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir", type=Path)
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()
    raise SystemExit(regrade(a.run_dir.resolve(), a.write))
