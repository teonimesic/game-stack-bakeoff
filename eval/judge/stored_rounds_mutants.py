#!/usr/bin/env python3
"""Mutants and a variant for `blurb_selftest.py`'s stored-round census.

WHY THIS FILE EXISTS
--------------------
`--stored-rounds` reads `eval/runs/`, which is gitignored, so **no gate has ever been able
to see it**. Its output is the producer for a table in `eval/RUNS.md`, and that table went
stale on 3 rows of 4 with the producer's own command printed directly above it (task 132).

The repair was to make the census print the POPULATION - which directories the rounds it
counted are in, and what pack state each was told about - because the digits were not what
went stale. The prose beside them was: *all in `wg-aspect-reliability`, all
`knowingly_truncated: false`*, true of all 10 hashed code rounds when it was written and
left standing when a later sweep put 4 more in a different directory.

`blurb_selftest.py` now builds a fixture tree whose answer is written out as literals and
asserts the census against it. **A green selftest is the shape this repository distrusts**,
so this file removes each mechanism those expectations name and requires a red.

WHAT EACH MUTANT REMOVES, AND WHY ITS LOSS WOULD BE INVISIBLE
------------------------------------------------------------
Every one of these leaves a census that runs, exits 0 and prints a plausible table.

| mutant | what it deletes | what the census would then report |
|---|---|---|
| `population_leaf_directory` | the full relative parent of a round | `judge-blind-2026-08-23` where the run directory is `wg-g4c-2026-08-21T02-26-46/...` - the #127 wrapper shape, a population you cannot find on disk |
| `population_forgets_pack_state` | `knowingly_truncated` from the population key | two rounds told opposite things about their pack pooled into one row, which is the exact sentence that went stale |
| `population_pools_non_code` | the `sees` filter on the population block | the audio and frames rounds inside the CODE row - two denominators printed as one, `tasks/94`'s defect |
| `unassessable_directories_dropped` | the by-directory listing of the hash-less rounds | 26 rounds called *permanently unassessable* with no population named, so nothing says when that set grows |
| `rebuild_ignores_pack_state` | the recorded state passed to the rebuild | every round rebuilt in the complete state, so a truncated round reads `moved` - **a drift reported where none happened**. Only the VARIANT catches this |
| `census_walk_one_level` | the depth-independent walk | 4 of the 14 real hashed code rounds sit 2 levels down and would vanish from every count |
| `unbuildable_dropped_from_population` | the row for a round whose aspect no longer exists | a round the headline counts and the population omits, which is this file's own defect one level in. `n = same + moved + unbuildable` per row is what makes it visible |

THE VARIANT (rule 15)
---------------------
A mutant removes a mechanism; only a variant can manufacture an input the check mishandles.
The fixture's `alpha/nested/deeper/i1.json` is a round stored `knowingly_truncated: true`
whose hash is the TRUNCATED-state brief's, so it can only read `same` if the census honours
the state the round recorded.

`--variant-control` measures that it is load-bearing rather than asserting it: it removes
that round from the fixture and re-runs `rebuild_ignores_pack_state`, which must then
SURVIVE. Measured 2026-08-25 - survives without it, caught with it.

**Needs no corpus.** The fixture is built under `tempfile` by `blurb_selftest.py` itself,
so this runs anywhere, including an agent worktree with no `eval/runs/`.

    python3 eval/judge/stored_rounds_mutants.py                    # every mutant, ~4.3s
    python3 eval/judge/stored_rounds_mutants.py --list             # the count and names
    python3 eval/judge/stored_rounds_mutants.py --variant-control  # is the variant needed
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "blurb_selftest.py"

#: (name, exact span to replace, replacement). The span must be present VERBATIM: a mutant
#: whose search text has drifted is a no-op that reports a pass for a check that never
#: changed. Drift is a failure below, never a skip.
MUTANTS: dict[str, tuple[str, str]] = {
    "population_leaf_directory": (
        "            key = (str(p.parent.relative_to(runs_root)), aid,",
        "            key = (p.parent.name, aid,"),
    "population_forgets_pack_state": (
        '                   bool(prov.get("knowingly_truncated")))\n'
        "            pop = population",
        "                   False)\n"
        "            pop = population"),
    "population_pools_non_code": (
        '        if "code" in (sees or "").split("+"):',
        "        if True:"),
    "unassessable_directories_dropped": (
        "    for where, n in sorted(unassessable.items()):",
        "    for where, n in sorted({}.items()):"),
    "rebuild_ignores_pack_state": (
        '                               knowingly_truncated='
        'bool(prov.get("knowingly_truncated")))\n'
        "            h = hashlib.sha256",
        "                               knowingly_truncated=False)\n"
        "            h = hashlib.sha256"),
    "census_walk_one_level": (
        '    for p in sorted(runs_root.rglob("*.json")):',
        '    for p in sorted(runs_root.glob("*/*.json")):'),
    "unbuildable_dropped_from_population": (
        '            unbuildable.append(p.name)\n            verdict = "unbuildable"',
        "            unbuildable.append(p.name)\n            continue"),
}

#: Removes the variant round from the fixture, restoring the shape it had before rule 15
#: was applied to it. Used only by `--variant-control`.
DROP_VARIANT: tuple[tuple[str, str], ...] = (
    ('    write("alpha/nested/deeper/i1.json", "idiomatic", '
     "prov(idio, kt=True, real=True))\n", ""),
    ('("alpha/nested/deeper", "idiomatic", "True", 2, 1, 1, 0)',
     '("alpha/nested/deeper", "idiomatic", "True", 1, 0, 1, 0)'),
    ('("stored judge rounds", 9), ("code-seeing", 8),\n'
     '                            ("carrying provenance.brief_sha256", 5),',
     '("stored judge rounds", 8), ("code-seeing", 7),\n'
     '                            ("carrying provenance.brief_sha256", 4),'),
)


def apply(text: str, spans) -> str:
    """Replace each span exactly once, refusing a span that is not there VERBATIM."""
    for old, new in spans:
        if text.count(old) != 1:
            raise SystemExit(f"span occurs {text.count(old)} times in {SOURCE.name}, "
                             f"expected exactly 1 - a mutant that does not apply tests "
                             f"nothing:\n  {old[:120]!r}")
        text = text.replace(old, new, 1)
    return text


def mirror(tmp: Path, source_text: str) -> Path:
    """An `eval/` tree whose only real file is the mutated selftest.

    `blurb_selftest.py` resolves its imports and `verify_blind.py` off its OWN directory,
    so a copy alone in a temp directory dies on `ModuleNotFoundError` and every mutant is
    scored as caught - the harness failing dressed as a clean sweep. Everything except the
    file under mutation is symlinked, so the copy sees the real tree at the real relative
    addresses and the control below is what says so out loud.
    """
    evaldir, judge = tmp / "eval", tmp / "eval" / "judge"
    judge.mkdir(parents=True)
    for entry in HERE.parent.iterdir():
        if entry.name != "judge":
            (evaldir / entry.name).symlink_to(entry)
    for entry in HERE.iterdir():
        if entry.name != SOURCE.name:
            (judge / entry.name).symlink_to(entry)
    target = judge / SOURCE.name
    target.write_text(source_text)
    return target


def run(path: Path) -> tuple[int, list[str]]:
    proc = subprocess.run([sys.executable, str(path)], capture_output=True, text=True,
                          check=False)
    return proc.returncode, [ln for ln in proc.stdout.splitlines() if "FAIL census" in ln]


def variant_control(base: str) -> int:
    """Is the variant load-bearing, or would the mutants alone have caught it?"""
    name = "rebuild_ignores_pack_state"
    old, new = MUTANTS[name]
    with tempfile.TemporaryDirectory() as td:
        without = apply(base, DROP_VARIANT)
        rc, red = run(mirror(Path(td) / "a", without))
        if rc != 0:
            print(f"CONTROL FAILED - the fixture without the variant is not green "
                  f"(exit {rc}): {red}")
            return 1
        rc_no, red_no = run(mirror(Path(td) / "b", apply(without, [(old, new)])))
        rc_yes, red_yes = run(mirror(Path(td) / "c", apply(base, [(old, new)])))
    print(f"{name} against the fixture WITHOUT the variant: exit {rc_no}, "
          f"{len(red_no)} red -> {'SURVIVED' if not red_no else 'caught'}")
    print(f"{name} against the fixture WITH the variant:    exit {rc_yes}, "
          f"{len(red_yes)} red -> {'SURVIVED' if not red_yes else 'caught'}")
    if red_no or not red_yes:
        print("\nThe variant is NOT load-bearing as measured: it must be the only thing "
              "that catches this mutant, or it is decoration on a check a mutant "
              "already covers.")
        return 1
    print("\nthe variant is load-bearing: the mutant survives without it and is caught "
          "with it")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--list", action="store_true",
                    help="print the count and the mutant names, and run nothing")
    ap.add_argument("--variant-control", action="store_true",
                    help="measure that the variant catches what no mutant does")
    args = ap.parse_args()

    if args.list:
        print(f"{len(MUTANTS)} mutants of {SOURCE.name}'s stored-round census:")
        for name in MUTANTS:
            print(f"  {name}")
        return 0

    base = SOURCE.read_text()
    if args.variant_control:
        return variant_control(base)

    problems: list[str] = []
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        # THE CONTROL FIRST. An unmutated copy must go green from the same mirrored tree
        # and the same interpreter the mutants use - otherwise every mutant "failing"
        # could be the mirror failing, and this file would report a clean bill of health
        # for a selftest that cannot run at all.
        rc, red = run(mirror(tmp / "control", base))
        if rc != 0 or red:
            print(f"CONTROL FAILED - an unmutated copy does not pass (exit {rc}). Every "
                  f"mutant below would be 'caught' by the same breakage.")
            for line in red:
                print(f"    {line}")
            return 1
        print("control (unmutated): exit 0, no census failure")

        for i, (name, (old, new)) in enumerate(MUTANTS.items()):
            if base.count(old) != 1:
                # NOT a skip. A mutant whose search text has drifted tests nothing, and
                # counting it as caught is how a suite reports a pass for a check that no
                # longer exists.
                print(f"--- {name}: NOT APPLIED - its search text occurs "
                      f"{base.count(old)} times in {SOURCE.name}, expected 1")
                problems.append(f"{name} (not applied)")
                continue
            rc, red = run(mirror(tmp / f"m{i}", base.replace(old, new, 1)))
            print(f"--- {name}: "
                  + (f"caught (exit {rc}, {len(red)} red census row(s))" if red
                     else f"SURVIVED (exit {rc})"))
            for line in red:
                print(f"      {line[:160]}")
            if not red:
                # Exit non-zero via a traceback still fails, but it does not say WHAT
                # broke. A census that dies is not a census that disagreed.
                problems.append(name)

    if problems:
        print(f"\nPROBLEMS: {', '.join(problems)}")
        return 1
    print(f"\nall {len(MUTANTS)} mutants caught, each reddening a named census "
          f"expectation; control green. `--variant-control` measures the variant.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
