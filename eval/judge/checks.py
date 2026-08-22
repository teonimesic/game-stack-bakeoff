#!/usr/bin/env python3
"""Assertions shared by every game's play-bot.

Determinism and seed-sensitivity are game-independent: they only need a fixed input
tape and the hash chain the probe already emits. Keeping them here means all three
games are held to the identical standard.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from probe import Criterion, ProbeError, ProbeSession, unusable_criteria


def hash_chain(repo: Path, seed: int, tape: list[dict[str, Any]],
               env: dict[str, str] | None = None) -> list[str]:
    """Replay a fixed input tape and return the per-tick hashes (including tick 0).

    Each call opens its OWN session, which is the whole point - reproducibility that
    only holds inside one process is not reproducibility. `ProbeSession` serialises
    sessions per repository so this cannot collide with the session the bot is already
    holding; before that it always did, on every engine that locks its project, and it
    cost Unity both of these criteria on every trial (FINDINGS #25).
    """
    with ProbeSession(repo=repo, seed=seed, env=env) as s:
        for inputs in tape:
            s.step_raw(inputs)
        return [t.hash for t in s.history]


DETERMINISM_CRITERIA = [
    ("determinism.replay",
     "Does replaying the same seed and the same inputs reproduce the same state hash "
     "at every tick?"),
    ("determinism.seed",
     "Do two different seeds produce different runs?"),
]


def determinism_criteria(repo: Path, tape: list[dict[str, Any]],
                         seed_a: int = 7, seed_b: int = 99,
                         env: dict[str, str] | None = None) -> list[Criterion]:
    """Two binary checks: replay reproducibility, and that the seed actually matters.

    The second one is not pedantry. A game that ignores its seed passes every replay
    test trivially, which is exactly what a determinism check is supposed to fail.
    """
    out: list[Criterion] = []
    try:
        a1 = hash_chain(repo, seed_a, tape, env)
        a2 = hash_chain(repo, seed_a, tape, env)
    except ProbeError as e:
        return unusable_criteria(DETERMINISM_CRITERIA, e,
                                 f"the two replay sessions on seed {seed_a}")

    if len(a1) < 2:
        out.append(Criterion(DETERMINISM_CRITERIA[0][0], DETERMINISM_CRITERIA[0][1],
                             False, f"only {len(a1)} trace lines produced"))
    else:
        first_div = next((i for i, (x, y) in enumerate(zip(a1, a2)) if x != y), None)
        out.append(Criterion(
            DETERMINISM_CRITERIA[0][0], DETERMINISM_CRITERIA[0][1],
            first_div is None and len(a1) == len(a2),
            f"{len(a1)} ticks; " + ("identical hash chains across two runs"
                                    if first_div is None
                                    else f"diverged at tick {first_div}: "
                                         f"{a1[first_div]} vs {a2[first_div]}")))

    try:
        b = hash_chain(repo, seed_b, tape, env)
    except ProbeError as e:
        out.extend(unusable_criteria([DETERMINISM_CRITERIA[1]], e,
                                     f"the session on seed {seed_b}"))
        return out

    differs = any(x != y for x, y in zip(a1, b)) or len(a1) != len(b)
    out.append(Criterion(
        DETERMINISM_CRITERIA[1][0], DETERMINISM_CRITERIA[1][1], differs,
        f"seed {seed_a} vs {seed_b}: " +
        ("hash chains differ" if differs
         else "IDENTICAL hash chains - the seed is not being used")))
    return out


def idle_tape(n: int) -> list[dict[str, Any]]:
    return [{} for _ in range(n)]
