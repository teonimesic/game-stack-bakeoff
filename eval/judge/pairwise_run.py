#!/usr/bin/env python3
"""Drive pairwise comparisons over stored submissions and measure the two noise rates.

ORDER DISAGREEMENT: every pair is judged twice, (A,B) and (B,A). A judge that is
consistent must reverse its verdict when the labels reverse. The disagreement rate is
self-consistency measured on contested pairs.

INTRANSITIVITY: over the resulting tournament, count triples where A>B, B>C, C>A. That
is a noise floor for the ranking itself, which no per-artifact metric can give.
"""
from __future__ import annotations

import argparse, json, os, shutil, sys, tempfile
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

import tokenvalue  # noqa: E402
from judge_pairwise import compare  # noqa: E402


def submissions(run_dir: Path, game: str, work: Path) -> list[dict]:
    out = []
    for tj in sorted((run_dir / "trials").glob(f"{game}__*.json")):
        tid = tj.stem
        art = run_dir / "artifacts" / tid
        frames = art / "eval" / "frames"
        code = work / tid
        if not (art / "submission.tar.gz").exists():
            continue
        code.mkdir(parents=True, exist_ok=True)
        os.system(f"tar -xzf {art/'submission.tar.gz'} -C {code} 2>/dev/null")
        out.append({"id": tid, "frames": frames if frames.exists() else None,
                    "telemetry": None, "code": code})
    return out


def analyse(results: list[dict]) -> dict:
    """Order disagreement + transitivity over `overall` verdicts."""
    fwd = {}
    for r in results:
        if not r.get("usable"):
            continue
        fwd[(r["a"], r["b"])] = r.get("overall")
    pairs = set()
    disagree = agree = 0
    wins = {}
    for (a, b), v in fwd.items():
        key = tuple(sorted((a, b)))
        if key in pairs:
            continue
        rev = fwd.get((b, a))
        if rev is None:
            continue
        pairs.add(key)
        # consistent = the verdict names the SAME submission both times
        f_winner = a if v == "A" else (b if v == "B" else None)
        r_winner = b if rev == "A" else (a if rev == "B" else None)
        if f_winner == r_winner:
            agree += 1
            if f_winner:
                wins.setdefault(f_winner, set()).add(b if f_winner == a else a)
        else:
            disagree += 1
    n = agree + disagree
    # intransitive triples among consistent verdicts
    beats = {k: set(v) for k, v in wins.items()}
    subs = sorted({s for p in pairs for s in p})
    tri = bad = 0
    for x, y, z in combinations(subs, 3):
        for a, b, c in ((x, y, z), (x, z, y), (y, x, z)):
            if b in beats.get(a, ()) and c in beats.get(b, ()):
                tri += 1
                if a in beats.get(c, ()):
                    bad += 1
    return {"pairs_judged_both_orders": n,
            "order_agreement": round(agree / n, 3) if n else None,
            "order_disagreement": round(disagree / n, 3) if n else None,
            "ties": sum(1 for v in fwd.values() if v == "indistinguishable"),
            "verdicts": len(fwd),
            "transitive_triples": tri, "intransitive_triples": bad,
            "intransitivity_rate": round(bad / tri, 3) if tri else None,
            "win_counts": {k: len(v) for k, v in sorted(beats.items())}}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-dir", required=True, type=Path)
    ap.add_argument("--game", required=True)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--max-pairs", type=int, default=0, help="0 = all pairs")
    a = ap.parse_args()
    work = Path(tempfile.mkdtemp(prefix="pairsrc-"))
    subs = submissions(a.run_dir.resolve(), a.game, work)
    print(f"{len(subs)} submissions for {a.game}")
    pairs = list(combinations(range(len(subs)), 2))
    if a.max_pairs:
        pairs = pairs[:a.max_pairs]
    a.out.mkdir(parents=True, exist_ok=True)
    results = []
    for i, j in pairs:
        for (x, y, tag) in ((i, j, "fwd"), (j, i, "rev")):
            f = a.out / f"{subs[x]['id']}__vs__{subs[y]['id']}.json"
            if f.exists() and f.stat().st_size > 0:
                results.append(json.loads(f.read_text())); continue
            r = compare(subs[x], subs[y], a.game)
            tmp = f.with_suffix(".tmp"); tmp.write_text(json.dumps(r, indent=2))
            os.replace(tmp, f)
            results.append(r)
            print(f"  {tag} {subs[x]['id']} vs {subs[y]['id']}: "
                  f"overall={r.get('overall')} "
                  f"{tokenvalue.tag(r.get('cost_usd', 0))}", flush=True)
    stats = analyse(results)
    (a.out / "_analysis.json").write_text(json.dumps(stats, indent=2))
    print(json.dumps(stats, indent=2))
    print(f"total {tokenvalue.tag(sum(r.get('cost_usd', 0) or 0 for r in results))}")
    print(tokenvalue.DEFINITION)
    shutil.rmtree(work, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
