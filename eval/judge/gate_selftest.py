#!/usr/bin/env python3
"""Can the tier-1 gate FAIL, and can a correct submission still PASS it?

Tier 1 stopped being 0.31 of the score on 2026-08-23 and became a gate (task 29,
RUBRIC.md). A gate is a check, and this repository's whole ledger of findings is
checks that ran, reported success and measured nothing - so the gate arrives with
both halves of the discipline rather than with an argument:

  MUTANTS   remove a mechanism the gate names and require an expectation to go red.
            A gate that cannot fail is worse than no gate: it looks like a pass.
  VARIANTS  correct inputs the implementation does not resemble, where the gate must
            still PASS. A mutant cannot manufacture the input a check mishandles, and
            every false negative adjudicated in this project has been of that kind
            (rule 15). Here they are the engine project-lock exception, an audio-less
            task, and a submission that fails only a criterion tier 2 does not need.

It also pins the property the change exists to create: `overall` no longer moves when
tier 1 moves, and still moves when tier 2 does. That is the one assertion which, if it
ever goes red, means the weighted sum has come back.

    python3 judge/gate_selftest.py        # exit 0 only if every expectation holds
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import evaluate  # noqa: E402

FAILS: list[str] = []
CHECKS = 0


def expect(name: str, cond: bool, detail: str = "") -> None:
    global CHECKS
    CHECKS += 1
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f"  -- {detail}" if detail else ""))
    if not cond:
        FAILS.append(name)


def tier1(*crits: tuple[str, bool, bool]) -> dict:
    """A tier-1 record: (id, passed, scored) triples."""
    scored = [c for c in crits if c[2]]
    return {
        "tier": "programmatic",
        "passed": sum(1 for c in scored if c[1]),
        "total": len(scored),
        "score": (sum(1 for c in scored if c[1]) / len(scored)) if scored else 0.0,
        "criteria": [{"id": i, "passed": p, "scored": s, "evidence": f"{i}: ev"}
                     for i, p, s in crits],
    }


NINE = ("build.compiles", "verify.green", "lint.clean", "tests.exist", "tests.green",
        "render.frames", "render.nonempty", "render.animates", "probe.responds")
ALL_PASS = tier1(*[(c, True, True) for c in NINE])


# --------------------------------------------------------------------------- #

def test_the_gate_decides() -> None:
    print("\n[the gate answers PASS/FAIL and names what failed]")
    g = evaluate.gate_verdict(ALL_PASS)
    expect("a clean tier 1 passes", g["passed"] and g["n_failed"] == 0, str(g["failed"]))
    expect("a clean tier 1 is independent evidence", g["score_is_independent"])

    g = evaluate.gate_verdict(tier1(*[(c, c != "lint.clean", True) for c in NINE]))
    expect("one lint finding fails the gate", not g["passed"])
    expect("and the gate names it", g["failed"] == ["lint.clean"], str(g["failed"]))
    expect("a lint finding is NOT blocking", g["blocking_failed"] == []
           and g["score_is_independent"], str(g))

    g = evaluate.gate_verdict(tier1(*[(c, c not in ("build.compiles", "probe.responds"),
                                       True) for c in NINE]))
    expect("a build failure is blocking", g["blocking_failed"]
           == ["build.compiles", "probe.responds"], str(g["blocking_failed"]))
    expect("and the record says the score is not independent evidence",
           not g["score_is_independent"])


def test_fail_closed() -> None:
    print("\n[fail-closed: an empty tier is not a pass]")
    g = evaluate.gate_verdict({"tier": "programmatic", "criteria": []})
    expect("no criteria at all -> not usable", not g["usable"], str(g))
    expect("no criteria at all -> NOT passed", not g["passed"], str(g))
    g = evaluate.gate_verdict({"tier": "programmatic"})
    expect("a tier record with no criteria key -> NOT passed", not g["passed"], str(g))
    expect("the summary line refuses to call an unusable gate a pass",
           "not a pass" in evaluate.gate_line(g).lower(), evaluate.gate_line(g))
    expect("the summary line says so when a record predates the regime",
           "predates" in evaluate.gate_line(None), evaluate.gate_line(None))


def test_variants_the_gate_must_still_pass() -> None:
    print("\n[variants: correct inputs the gate must NOT fail]")
    # The engine project-lock exception. Excluded from the denominator, not failed:
    # it can only arise on the stacks that take a project-wide lock (FINDINGS #25).
    locked = tier1(*[(c, c != "probe.responds", c != "probe.responds") for c in NINE])
    g = evaluate.gate_verdict(locked)
    expect("an unscored criterion does not fail the gate", g["passed"], str(g))
    expect("and it leaves the denominator at 8, not 9", g["n_scored"] == 8,
           str(g["n_scored"]))

    # A task that did not ask for sound has 9 criteria, not 14. Neither count is
    # special-cased anywhere; the gate reads the tier it was given.
    expect("a 9-criterion tier and a 14-criterion tier both pass cleanly",
           evaluate.gate_verdict(ALL_PASS)["passed"]
           and evaluate.gate_verdict(
               tier1(*[(c, True, True) for c in NINE + ("audio.manifest",
                                                        "audio.files_exist",
                                                        "audio.not_silent",
                                                        "audio.distinct",
                                                        "audio.music_loops")]))["passed"])

    # A submission whose capture recipe is broken is still measurable: the play-bot
    # drives the probe, not the film. The gate must fail it WITHOUT calling it blocking.
    g = evaluate.gate_verdict(tier1(*[(c, c != "render.frames", True) for c in NINE]))
    expect("a broken film recipe fails the gate but is not blocking",
           not g["passed"] and g["blocking_failed"] == [], str(g))


def test_the_score_no_longer_moves_with_tier_1() -> None:
    print("\n[the property the change exists to create]")
    hi = evaluate.overall_score({"programmatic": 1.0, "playbot": 0.75})
    lo = evaluate.overall_score({"programmatic": 0.0, "playbot": 0.75})
    expect("`overall` is identical at tier 1 = 1.00 and tier 1 = 0.00",
           hi == lo == 0.75, f"{hi} vs {lo}")
    expect("`overall` still moves with tier 2",
           evaluate.overall_score({"programmatic": 1.0, "playbot": 0.5}) == 0.5)
    expect("the gate tier carries no weight at all",
           evaluate.GATE_TIER not in evaluate.WEIGHTS, str(evaluate.WEIGHTS))
    expect("the scored weights sum to 1.0",
           abs(sum(evaluate.WEIGHTS.values()) - 1.0) < 1e-9, str(evaluate.WEIGHTS))
    expect("every record stamps the regime it was scored under",
           bool(evaluate.SCORING_REGIME), evaluate.SCORING_REGIME)


# --------------------------------------------------------------------------- #
# mutants
# --------------------------------------------------------------------------- #

def mutants() -> None:
    """Each removes one mechanism; the expectation it removes must go red."""
    print("\n[mutants: can these checks fail?]")
    one_bad = tier1(*[(c, c != "lint.clean", True) for c in NINE])

    original = evaluate.gate_verdict

    # 1. A gate that ignores `passed` - the shape a gate degenerates into.
    evaluate.gate_verdict = lambda t1: {**original(t1), "passed": True, "failed": []}
    caught = evaluate.gate_verdict(one_bad)["passed"] and not original(one_bad)["passed"]
    evaluate.gate_verdict = original
    expect("mutant 'the gate always passes' is caught by the lint-finding check", caught)

    # 2. A gate that treats an empty tier as clean. This is the failure the project has
    #    hit most often: total=0 passed=0 read as success.
    evaluate.gate_verdict = lambda t1: {**original(t1),
                                        "passed": not original(t1)["failed"]}
    empty = evaluate.gate_verdict({"tier": "programmatic", "criteria": []})
    caught = empty["passed"] and not original({"criteria": []})["passed"]
    evaluate.gate_verdict = original
    expect("mutant 'an empty tier is a pass' is caught by the fail-closed check", caught)

    # 3. A gate that counts the lock exception as a failure. Fail-closed in the wrong
    #    direction: it deducts from a strict subset of the arms (FINDINGS #25).
    def count_unscored(t1):
        crits = t1.get("criteria") or []
        failed = [c["id"] for c in crits if not c.get("passed")]
        return {**original(t1), "failed": failed, "passed": not failed}

    evaluate.gate_verdict = count_unscored
    locked = tier1(*[(c, c != "probe.responds", c != "probe.responds") for c in NINE])
    caught = not evaluate.gate_verdict(locked)["passed"] and original(locked)["passed"]
    evaluate.gate_verdict = original
    expect("mutant 'an unscored criterion is a failure' is caught by the variant", caught)

    # 4. THE WEIGHTED SUM, REINSTATED. The one mutant that matters: if the old scheme
    #    ever comes back - by a merge, by a revert, by someone restoring a constant -
    #    the score starts moving with tier 1 again and this must notice.
    original_w = evaluate.WEIGHTS
    evaluate.WEIGHTS = {"programmatic": 0.31, "playbot": 0.69}
    hi = evaluate.overall_score({"programmatic": 1.0, "playbot": 0.75})
    lo = evaluate.overall_score({"programmatic": 0.0, "playbot": 0.75})
    evaluate.WEIGHTS = original_w
    expect("mutant 'restore the 0.31/0.69 split' makes `overall` move with tier 1, "
           "and is caught", hi != lo, f"{hi} vs {lo}")


def main() -> int:
    test_the_gate_decides()
    test_fail_closed()
    test_variants_the_gate_must_still_pass()
    test_the_score_no_longer_moves_with_tier_1()
    mutants()
    print(f"\n{CHECKS - len(FAILS)}/{CHECKS} expectations held")
    if FAILS:
        print("FAILED: " + ", ".join(FAILS))
        return 1
    print("gate selftest: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
