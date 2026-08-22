#!/usr/bin/env python3
"""Does the stopping rule decide correctly, and can it fail? Simulated judges, no spend.

The branch this project will probably land on is the TIE, so it gets as much testing as
the ordering branch. The failure that would matter most is a tie being reported where the
truth is "we never decided" — those are different verdicts and this asserts they stay so.
"""
import random, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import sequential as sq

LABELS = list("ABCDEFGH")
FAILS = []

def sim(truth, noise, seed, max_runs=sq.MAX_RUNS):
    rng = random.Random(seed)
    s = sq.Sampler(LABELS, max_runs=max_runs)
    def once(_i):
        return {l: truth[l] + rng.gauss(0, noise) for l in LABELS}
    return s.run(once)

def expect(name, cond, detail):
    if not cond: FAILS.append(f"{name}: {detail}")

# 1. A clear ordering, little noise -> ORDERED, few runs
r = sim({l: i for i, l in enumerate(LABELS)}, 0.20, 1)
expect("clear-ordering", r["counts"]["ORDERED"] == 28 and r["counts"]["UNRESOLVED"] == 0,
       f"expected all 28 pairs ordered, got {r['counts']}")
expect("clear-ordering-cheap", r["runs"] <= 8, f"took {r['runs']} runs")
print(f"1 clear ordering        runs={r['runs']:<3} {r['counts']}  max_N={r['max_runs_to_resolve']}")

# 2. A true tie: every submission identical, judge is pure noise -> TIED, never ORDERED
r = sim({l: 0.0 for l in LABELS}, 1.0, 2)
expect("true-tie-few-false-orders", r["counts"]["ORDERED"] <= 6,
       f"a coin-flip field produced {r['counts']['ORDERED']} ORDERED pairs")
print(f"2 true tie              runs={r['runs']:<3} {r['counts']}  headline={r['headline'][:44]}")

# 3. A saturated judge: identical scores every run -> tie, and cheaply
r = sim({l: 2.0 for l in LABELS}, 0.0, 3)
expect("saturated-is-exact-tie", r["counts"]["TIED_EXACT"] == 28,
       f"a judge scoring everything identically must report TIED_EXACT, got {r['counts']}")
expect("saturated-is-cheap", r["runs"] <= sq.MIN_RUNS,
       f"a saturated judge should stop at MIN_RUNS, took {r['runs']}")
print(f"3 saturated judge       runs={r['runs']:<3} {r['counts']}")

# 4. A genuine near-tie with a slight edge: must NOT be called TIED, must run long
truth = {l: (0.12 if l < "E" else 0.0) for l in LABELS}
r = sim(truth, 1.0, 4)
cross = [p for p in r["pairs"] if (p["a"] < "E") != (p["b"] < "E")]
mislabelled = [p for p in cross if p["verdict"] == "TIED"]
expect("near-tie-not-called-tied", len(mislabelled) <= 4,
       f"{len(mislabelled)} of {len(cross)} genuinely-different pairs called TIED")
print(f"4 slight edge           runs={r['runs']:<3} {r['counts']}  "
      f"cross-pairs called TIED: {len(mislabelled)}/{len(cross)}")

# 5. THE CRITICAL DISTINCTION: budget exhausted with pairs still ambiguous must report
#    NOT RESOLVED, never a tie.
r = sim(truth, 1.0, 5, max_runs=5)
if r["counts"]["UNRESOLVED"]:
    expect("unresolved-not-tie", r["headline"].startswith("NOT RESOLVED"),
           f"headline was {r['headline'][:60]}")
    expect("unresolved-says-so", "not a tie" in r["headline"], "headline omits the warning")
print(f"5 budget cut short      runs={r['runs']:<3} {r['counts']}  "
      f"headline={r['headline'][:40]}")

# 6. A failed run must not count as an observation
s = sq.Sampler(LABELS)
s.run(lambda i: None)
expect("failed-runs-not-observed", s.runs == 0, f"failed runs recorded as {s.runs} observations")
print(f"6 all judge calls fail  runs={s.runs} (must be 0)")

print(f"\n{len(FAILS)} unmet expectation(s)")
for f in FAILS: print("  FAIL", f)
raise SystemExit(1 if FAILS else 0)
