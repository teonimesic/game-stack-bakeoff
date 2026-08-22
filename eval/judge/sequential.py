#!/usr/bin/env python3
"""Sequential sampling on the DECISION, not the score.

The old reliability metric, `instability`, measured forward-vs-reverse disagreement
*within* one run. It read 0.000 on 22 of 24 submissions — consistent and uninformative,
because it was measuring presentation-order sensitivity on artifacts whose answer was
obvious. This replaces it with the quantity that actually decides anything: **across
repeated runs with the order reshuffled, how often does A beat B?**

The unit is a PAIR, not a submission and not a score.

    resolved ORDERED : the Wilson interval on the pair's win rate excludes 0.5
    resolved TIED    : the interval lies entirely inside 0.5 +- TIE_MARGIN
    unresolved       : neither — keep sampling this pair

Each aspect keeps sampling only while some pair is unresolved, up to a hard maximum.
Pairs that resolve early stop consuming budget.

TWO THINGS THIS IS BUILT TO GET RIGHT
-------------------------------------

**A converged tie is a result.** Three games have already tied on the deterministic
tiers, so "indistinguishable" is the likely landing place, not a failure to decide. The
tie rule is a first-class stopping condition with an interval attached — not the state of
having run out of budget. `TIED` and `UNRESOLVED` are different verdicts and must never
be reported as the same thing.

**The N is part of the answer.** A ranking that takes 20 runs to stabilise is weak
evidence even when it converges. `runs_to_resolve` is reported per pair, and the maximum
across pairs is reported for the aspect.

Aggregate scores remain weight 0.00. This changes how confidently the diagnostic speaks,
not whether it counts.
"""

from __future__ import annotations

import json
import math
import sys
from dataclasses import dataclass, field
from itertools import combinations
from pathlib import Path
from typing import Any, Callable

sys.path.insert(0, str(Path(__file__).resolve().parent))

#: Wilson confidence level. 95%.
Z = 1.959963985
#: A pair whose interval sits inside 0.5 +- this is called a STATISTICAL tie.
#:
#: COSTED BEFORE USE, because the first version of this file made a tie unreachable and
#: nobody would have noticed until a run reported "unresolved" forever. A Wilson 95%
#: half-width at p=0.5 is 0.285 at n=8, 0.186 at n=24, 0.136 at n=48, 0.098 at n=96. So
#: a +-0.10 statistical tie claim costs ~96 judge runs per aspect, which at ~$12 a run is
#: not affordable. At the affordable n=24 the tightest honest claim is +-0.19.
#:
#: Two consequences, both stated rather than hidden: the statistical tie is left at 0.10
#: so the number means something, and it will simply not fire at affordable N — instead
#: the EXACT tie below carries the realistic case, and `n_for_statistical_tie` is
#: reported so the cost of the stronger claim is visible.
TIE_MARGIN = 0.10
#: Never sample one aspect more than this many times, whatever remains unresolved.
MAX_RUNS = 24
#: Never fewer than this, so a pair cannot "resolve" off two lucky runs.
MIN_RUNS = 4


def wilson(wins: float, n: int, z: float = Z) -> tuple[float, float]:
    """Wilson score interval for a proportion. Correct at small n, unlike normal
    approximation, which is the whole reason to use it here — the point of sequential
    sampling is to stop while n is still small."""
    if n == 0:
        return (0.0, 1.0)
    p = wins / n
    d = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = (z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))) / d
    return (max(0.0, centre - half), min(1.0, centre + half))


@dataclass
class Pair:
    a: str
    b: str
    #: A tie within a single run counts half a win to each side — the standard
    #: continuity treatment. Without it, a judge that ties a pair every time would
    #: never accumulate evidence and would look unresolved forever rather than tied.
    wins_a: float = 0.0
    n: int = 0
    #: Runs in which the judge gave these two the SAME score. All-exact-ties is not
    #: statistical ambiguity — it is the judge never separating them, which at n=24
    #: would otherwise present identically to "we could not decide". That collapse is
    #: how a saturated instrument gets mistaken for a hard question.
    exact_ties: int = 0
    resolved_at: int | None = None
    verdict: str = "UNRESOLVED"

    def observe(self, score_a: float, score_b: float) -> None:
        if self.resolved_at is not None:
            return
        self.n += 1
        if score_a > score_b:
            self.wins_a += 1.0
        elif score_a == score_b:
            self.wins_a += 0.5
            self.exact_ties += 1

    def interval(self) -> tuple[float, float]:
        return wilson(self.wins_a, self.n)

    def check(self) -> str:
        if self.n < MIN_RUNS:
            return "UNRESOLVED"
        if self.exact_ties == self.n:
            # The judge gave them the same score every single time. There is nothing
            # left to sample: more runs cannot separate what the instrument does not
            # distinguish. Reported as its own verdict so it can never be read as
            # either an ordering or a failure to decide.
            return "TIED_EXACT"
        lo, hi = self.interval()
        if lo > 0.5:
            return "ORDERED"          # a beats b
        if hi < 0.5:
            return "ORDERED"          # b beats a
        if lo >= 0.5 - TIE_MARGIN and hi <= 0.5 + TIE_MARGIN:
            return "TIED"
        return "UNRESOLVED"

    def to_dict(self) -> dict[str, Any]:
        lo, hi = self.interval()
        rate = self.wins_a / self.n if self.n else None
        return {
            "a": self.a, "b": self.b, "n": self.n,
            "win_rate_a": round(rate, 3) if rate is not None else None,
            "wilson_95": [round(lo, 3), round(hi, 3)],
            "verdict": self.verdict,
            "exact_ties": self.exact_ties,
            "runs_to_resolve": self.resolved_at,
            "winner": (None if self.verdict != "ORDERED"
                       else self.a if (rate or 0) > 0.5 else self.b),
        }


@dataclass
class Sampler:
    """Drives repeated judgements of one aspect until every pair resolves or MAX_RUNS."""

    labels: list[str]
    max_runs: int = MAX_RUNS
    pairs: dict[tuple[str, str], Pair] = field(default_factory=dict)
    runs: int = 0
    scores_seen: list[dict[str, float]] = field(default_factory=list)

    def __post_init__(self) -> None:
        for a, b in combinations(sorted(self.labels), 2):
            self.pairs[(a, b)] = Pair(a, b)

    def unresolved(self) -> list[Pair]:
        return [p for p in self.pairs.values() if p.resolved_at is None]

    def observe_run(self, scores: dict[str, float]) -> None:
        self.runs += 1
        self.scores_seen.append(dict(scores))
        for (a, b), pair in self.pairs.items():
            if a in scores and b in scores:
                pair.observe(scores[a], scores[b])
                v = pair.check()
                if v != "UNRESOLVED":
                    pair.verdict = v
                    pair.resolved_at = pair.n

    def done(self) -> bool:
        return not self.unresolved() or self.runs >= self.max_runs

    def run(self, judge_once: Callable[[int], dict[str, float] | None]) -> dict[str, Any]:
        """`judge_once(run_index)` returns {label: score}, or None if that run failed.

        A failed run is NOT an observation. Counting it would let an API error look like
        a tie, which is the "measures nothing but reports something" shape this project
        keeps hitting.
        """
        failures = 0
        while not self.done():
            scores = judge_once(self.runs)
            if scores is None:
                failures += 1
                if failures >= 3:
                    break
                continue
            self.observe_run(scores)
        return self.report(failures)

    def report(self, failures: int = 0) -> dict[str, Any]:
        pairs = [p.to_dict() for p in self.pairs.values()]
        by = {v: [p for p in pairs if p["verdict"] == v]
              for v in ("ORDERED", "TIED", "TIED_EXACT", "UNRESOLVED")}
        resolved_ns = [p["runs_to_resolve"] for p in pairs
                       if p["runs_to_resolve"] is not None]
        # THE HEADLINE MUST DISTINGUISH THESE THREE.
        if by["UNRESOLVED"]:
            headline = (f"NOT RESOLVED after {self.runs} runs: "
                        f"{len(by['UNRESOLVED'])} of {len(pairs)} pairs still ambiguous. "
                        f"This is not a tie — it is a failure to decide, and the two must "
                        f"not be reported as the same thing.")
        elif not by["ORDERED"]:
            headline = (
                f"CONVERGED TIE: all {len(pairs)} pairs indistinguishable "
                f"({len(by['TIED_EXACT'])} because the judge scored them identically in "
                f"every run, {len(by['TIED'])} by interval). That is a positive finding "
                f"about the field, not a failure of the judge.")
        else:
            headline = (f"RESOLVED: {len(by['ORDERED'])} of {len(pairs)} pairs ordered, "
                        f"{len(by['TIED'])} genuinely tied.")
        return {
            "runs": self.runs,
            "failed_runs": failures,
            "max_runs": self.max_runs,
            "tie_margin": TIE_MARGIN,
            "pairs": pairs,
            "counts": {k: len(v) for k, v in by.items()},
            "n_for_statistical_tie": 96,
            "note_on_n": ("a +-0.10 statistical tie needs ~96 runs per aspect; at the "
                          "affordable n<=24 the tightest honest interval is +-0.19, so "
                          "TIED_EXACT carries the realistic tie case"),
            "max_runs_to_resolve": max(resolved_ns) if resolved_ns else None,
            "median_runs_to_resolve": (sorted(resolved_ns)[len(resolved_ns) // 2]
                                       if resolved_ns else None),
            "headline": headline,
        }


if __name__ == "__main__":
    print(json.dumps({"tie_margin": TIE_MARGIN, "max_runs": MAX_RUNS,
                      "min_runs": MIN_RUNS, "z": Z}, indent=2))
