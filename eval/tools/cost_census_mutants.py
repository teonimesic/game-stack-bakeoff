#!/usr/bin/env python3
"""Mutants of `cost_census.py`, each deleting one mechanism its selftest names.

WHY THIS FILE EXISTS AT ALL, AND WHY IT IS NOT OPTIONAL
------------------------------------------------------
`cost_census.py --selftest` returns `ok (0 failures)`, and a green selftest is exactly the
shape this repository exists to distrust: **`total=0 passed=0` is indistinguishable from a
correctly-passing suite.** The only thing that establishes a check can fail is removing the
mechanism it names and watching it go red.

That sweep was run by hand while `cost_census.py` was written, and `DECISIONS.md` published
the count. **A count with no producer goes stale forever rather than for an hour** — the
rule this whole task was filed under — and CodeRabbit's review of PR #9 duly read the
selftest's `# Direction` comments and reported the count as 11 against a published 14.
Neither number was checkable, because the mutants lived in a scratchpad that dies with the
session. This file is the producer. **The count is `len(MUTANTS)` and nothing else.**

WHAT EACH MUTANT REMOVES, AND WHY ITS LOSS WOULD BE INVISIBLE
-------------------------------------------------------------
Every one of these produces a plausible in-range number rather than a crash, which is what
makes a mutant necessary rather than merely tidy:

| mutant | what it deletes | what the tool would then report |
|---|---|---|
| `thin_cell` | the guard refusing a group with a 1-trial cell | that cell contributes a $0.00 gap, deflating the floor and inflating the ratio — **fail-open, in the direction that manufactures a difference between stacks** |
| `min_trials_guard` | the `--min-trials-per-cell >= 2` refusal | the same fail-open, reached by a flag instead of by data |
| `min_stacks_guard` | the `--min-stacks >= 2` refusal | a "between-stack range" over one stack, which is $0.00 by construction and reads as the stacks agreeing |
| `pool_terminal` | the `terminal_reason` partition | one mean over `completed`, `api_error` and `max_turns` together (rule 4) |
| `pool_specchange` | the whole-game / spec-change partition | the retired suite's trials inside a whole-game floor |
| `pool_games` | the game half of the group key | two games of one run averaged into a single floor |
| `min_gap_floor` | the floor being the MEAN of the cell gaps | the floor becomes the tightest cell — **the exact error #63 measured at 7.2x, and 33.0x over the stored corpus** |
| `first_two_only` | reading every trial in a cell | a 3-trial cell's gap taken off the first two |
| `r_zero` | Pearson returning `None` where undefined | `r = 0.0`, which reads as *no relationship* rather than *not computable* |
| `r_two_points` | Pearson's minimum point count | a "correlation" of exactly ±1 through two points |
| `spread_divides` | the `$0.00` low guard | a `ZeroDivisionError` where a spread of `None` belongs |
| `no_cost_guard` | excluding a record with no `agent.cost_usd` | a `TypeError` deep in the aggregation, or a record silently counted |
| `bad_record_guard` | validating `stack` and the cost's type | an uncaught `KeyError`/`TypeError` — `main()` catches only `CostCensusError`, so a traceback replaces a named, fail-closed error |
| `exceeds_off_ratio` | counting exceedance off the COMPARISON | a zero-floor group has no percentage, so it drops out of the exceedance count — **fail-open, understating how much the stacks disagree** |
| `empty_is_zero` | the refusal on an empty tree | `0 groups` for a tree that could not be read — the fallback shape rule 3 forbids by name |
| `count_agent_trees` | skipping agent-authored `work/` trees | an agent's own `trials/` counted as harness records |
| `one_level` | the depth-independent search | every run nested inside an archive wrapper silently dropped (#126) |
| `swallow_bad_json` | naming the file in a parse failure | a record vanishes from the population with nothing a reader can see |
| `drop_field` | a field the selftest reads, renamed | the selftest dying on a `KeyError` instead of reddening its row |

**`drop_field` is the one that is about the selftest rather than about the tool**, and it is
here because it already happened: a fixed placeholder dict inside `only_group()` drifted the
moment a field was added, and three mutants died on a `KeyError` instead of naming a failure.
A traceback and a FAIL row both exit non-zero, so the sweep called them caught — but only one
of them tells you what broke.

WHAT THIS DOES NOT DO
---------------------
A mutant asks whether a check **can** fail. Only a **variant** asks whether it can still
**pass** on an input it mishandles, and every false negative adjudicated in this project has
been of the second kind (`AGENTS.md` rule 15). The variants live in `cost_census.selftest`
itself — a `$0.00` trial, a record with no cost field, an uneven 3-trial cell — because they
must pass, and `spread_divides`, `no_cost_guard` and `first_two_only` above are the mutants
that prove those three rows can go red.

**Needs no corpus.** `cost_census.py --selftest` builds its own trees under `tempfile`, so
this runs anywhere, including an agent worktree with no `eval/runs/`.

    python3 eval/tools/cost_census_mutants.py          # every mutant, ~2s
    python3 eval/tools/cost_census_mutants.py --list   # the count and the names only
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "cost_census.py"

# (name, exact span to replace, replacement). The span must be present VERBATIM: a mutant
# whose search text has drifted is a no-op that reports a pass for a check that never
# changed, which is the shape this whole file exists to catch. Drift is a failure below,
# never a skip.
MUTANTS: dict[str, tuple[str, str]] = {
    # ---- the fail-open guards, in the direction that manufactures a difference
    "thin_cell": (
        "        thin = sorted(s for s, v in cells.items() if len(v) < min_trials_per_cell)",
        "        thin = []"),
    "min_trials_guard": (
        "    if min_trials_per_cell < 2:\n        raise CostCensusError(",
        "    if False:\n        raise CostCensusError("),
    "min_stacks_guard": (
        "    if min_stacks < 2:\n        raise CostCensusError(",
        "    if False:\n        raise CostCensusError("),
    "exceeds_off_ratio": (
        '        "range_exceeds_floor": between > floor,',
        '        "range_exceeds_floor": (100.0 * between / floor) > 100.0 if floor'
        ' else False,'),

    # ---- the partitions. Every one of these is AGENTS.md rule 4.
    "pool_terminal": (
        "        if _terminal(d) != terminal_reason:",
        "        if False:"),
    "pool_specchange": (
        "        if WHOLEGAME_KEY not in d:\n            continue",
        "        if False:\n            continue"),
    "pool_games": (
        '        by_group[(run, d["game"])][d["stack"]].append(d)',
        '        by_group[(run, "ALL")][d["stack"]].append(d)'),

    # ---- the measures themselves
    "min_gap_floor": (
        "    floor = sum(gaps) / len(gaps)",
        "    floor = min(gaps)"),
    "first_two_only": (
        '    costs = sorted(r["agent"]["cost_usd"] for r in records)',
        '    costs = sorted(r["agent"]["cost_usd"] for r in records)[:2]'),
    "r_zero": (
        "    if dx == 0 or dy == 0:\n        return None",
        "    if dx == 0 or dy == 0:\n        return 0.0"),
    "r_two_points": (
        "    if n < MIN_R_POINTS:\n        return None",
        "    if n < 0:\n        return None"),
    "spread_divides": (
        '        "spread": (costs[-1] / costs[0]) if costs[0] else None,',
        '        "spread": costs[-1] / costs[0] if costs[0] is not None else None,'),

    # ---- refuse rather than return a plausible number
    "no_cost_guard": (
        '        if d.get("agent", {}).get("cost_usd") is None:\n'
        '            excluded["no cost_usd"] += 1\n'
        "            continue",
        "        pass"),
    "bad_record_guard": (
        '        stack = d.get("stack")',
        '        stack = d.get("stack", "PRETEND")  # mutated\n'
        '        _unused = d.get("stack")'),
    "empty_is_zero": (
        "    if not out:\n        raise CostCensusError(",
        "    if False:\n        raise CostCensusError("),
    "swallow_bad_json": (
        "        except json.JSONDecodeError as exc:\n"
        '            raise CostCensusError(f"{path}: {exc}") from exc',
        "        except json.JSONDecodeError:\n            continue"),

    # ---- where the tool looks
    "count_agent_trees": (
        "        (skipped if NOT_A_RUN.intersection(stem) else counted).append(path)",
        "        counted.append(path)"),
    "one_level": (
        '    for path in sorted(runs_dir.rglob("trials/*.json")):',
        '    for path in sorted(runs_dir.glob("*/trials/*.json")):'),

    # ---- the selftest's own drift guard
    "drop_field": (
        '        "cell_gap_ratio": (max(gaps) / min(gaps)) if min(gaps) else None,',
        '        "cell_gap_ratio_RENAMED": (max(gaps) / min(gaps)) if min(gaps) else None,'),
}


def run_selftest(path: Path) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(path), "--selftest"],
                          capture_output=True, text=True, check=False)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--list", action="store_true",
                    help="print the count and the mutant names, and run nothing")
    args = ap.parse_args()

    if args.list:
        print(f"{len(MUTANTS)} mutants of {SOURCE.name}:")
        for name in MUTANTS:
            print(f"  {name}")
        return 0

    base = SOURCE.read_text()
    problems: list[str] = []

    with tempfile.TemporaryDirectory() as tmp:
        # THE CONTROL FIRST. An unmutated copy must go GREEN from the same temp directory
        # and the same interpreter the mutants use. Without it, every mutant "failing"
        # could be the harness failing, and the sweep would report a clean bill of health
        # for a file that cannot run at all.
        control = Path(tmp) / "control_unmutated.py"
        control.write_text(base)
        proc = run_selftest(control)
        if proc.returncode != 0:
            print("CONTROL FAILED — an unmutated copy does not pass its own selftest. "
                  "Every mutant below would be 'caught' by the same breakage.")
            for line in (proc.stdout + proc.stderr).splitlines():
                print(f"    {line}")
            return 1
        print(f"control (unmutated): exit 0, {proc.stdout.strip().splitlines()[-1]}")

        for name, (old, new) in MUTANTS.items():
            if old not in base:
                # NOT a skip. A mutant whose search text has drifted tests nothing, and
                # counting it as caught is how a suite reports a pass for a check that no
                # longer exists.
                print(f"--- {name}: NOT APPLIED — its search text is no longer in "
                      f"{SOURCE.name}")
                problems.append(f"{name} (not applied)")
                continue
            path = Path(tmp) / f"{name}.py"
            path.write_text(base.replace(old, new, 1))
            proc = run_selftest(path)
            caught = proc.returncode != 0
            named = proc.stdout.count("FAIL  ")
            print(f"--- {name}: "
                  + (f"caught (exit {proc.returncode}, {named} named failure(s))"
                     if caught else "SURVIVED"))
            if not caught:
                problems.append(name)
            elif named == 0:
                # Exit non-zero via a traceback still catches the mutant, but it does not
                # say what broke. This is the `drop_field` lesson: diagnose, do not merely
                # fail.
                print(f"    (no FAIL row — it died rather than reddening a check; "
                      f"the last line was: "
                      f"{(proc.stderr.strip().splitlines() or ['<no stderr>'])[-1][:100]})")
                problems.append(f"{name} (crashed instead of naming a failure)")

    if problems:
        print(f"\nPROBLEMS: {', '.join(problems)}")
        return 1
    print(f"\nall {len(MUTANTS)} mutants caught, each with at least one named failure; "
          f"control green")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
