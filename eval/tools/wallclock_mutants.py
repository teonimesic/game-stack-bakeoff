#!/usr/bin/env python3
"""Mutants of `wallclock.py`, each deleting one mechanism its selftest names.

`wallclock.py --selftest` returns `ok (0 failures)`, and a green selftest is the shape this
repository exists to distrust: `total=0 passed=0` is indistinguishable from a correctly
passing suite. The only thing that establishes a check can fail is removing the mechanism
it names and watching it go red. **The count is `len(MUTANTS)` and nothing else** — a count
with no producer goes stale forever rather than for an hour.

Every mutant below returns a plausible in-range number rather than a crash, which is what
makes it necessary rather than tidy:

| mutant | what it deletes | what the tool would then report |
|---|---|---|
| `ms_read_as_seconds` | the millisecond -> second conversion on the record address | a self-report 1000x the harness clock, so every spec-change delta is hugely negative and the exit code fails a corpus that is fine |
| `artifact_never_read` | the second address | **`0` paired whole-game records** — the live harness's whole population, reported as though the figure did not exist. This is the answer the ticket that filed the tool started from |
| `fall_through_on_unusable` | not looking up the artifact for a record whose own field is corrupt | `artifact_absent` for a defect in the trial record: a reason about the wrong file (rule 12) |
| `unreadable_is_absent` | the parse failure being its own reason | a capture that broke reads as a trial that was killed — the distinction the address exists to make |
| `bool_is_a_number` | `bool` being excluded | **`True` is an `int` in Python**, so `duration_ms: true` reads as a 1 ms agent run |
| `finite_guard` | `math.isfinite` | `json.loads` accepts the bare `NaN`, `Infinity`, `-Infinity` literals and all three are `float`. NaN propagates into the median and compares False against everything, so `negative_deltas` comes back 0 for a corpus whose numbers are not numbers — **a silent no, not a visible error** |
| `zero_is_a_duration` | the `<= 0` refusal | an agent that ran for no time contributes a delta equal to the whole harness clock, which is the largest overhead in the report |
| `negatives_uncounted` | the negative-delta detection | the assertion this tool exists to make, always green. Its exit code becomes structurally incapable of failing |
| `one_unpaired_counter` | `no_harness_clock` as its own axis | a record missing the harness clock reported as a record missing the self-report — the wrong file again, and it makes the two failures uncountable |
| `pool_populations` | the whole-game / scene / spec-change partition | a scene inside the game figures, which `eval/SCENES.md` forbids in as many words, and the retired suite's records inside the live harness's overhead |
| `empty_is_zero` | the refusal on a tree that cannot be read | `0 paired observations, 0 negative deltas` for a directory that does not exist — a green gate that read nothing, the shape `AGENTS.md` rule 3 forbids by name |
| `no_pair_is_agreement` | the refusal on a corpus where NOTHING pairs | the same `0 / 0` at exit 0, reached from a tree that reads perfectly — every record simply lacks a clock. A tree of prime-agent records alone does this, and the tool's only assertion goes vacuously green |
| `drop_field` | a field the selftest reads, renamed | the selftest dying on a `KeyError` instead of reddening a row. It is here because a suite that crashes and a suite that fails both exit non-zero, and only one of them says what broke |

**A mutant asks whether a check can fail. Only a variant asks whether it can still pass**
(`AGENTS.md` rule 15), and the variants live in `wallclock.selftest` because a variant must
**pass**. There are 4, each paired with the mutant that proves its rows can go red:

| variant, by what it plants | the input it must still handle | proved reddenable by |
|---|---|---|
| a run nested inside an archive wrapper | a run directory that is not a child of `runs/` (#126) | `pool_populations` reddens the same rows |
| a result object that exists and is EMPTY | the four wedged arena trials' stored shape — not the same as no object | `artifact_never_read` |
| a prime-agent record whose CLI reports no such field | a harness with no self-report at all | `artifact_never_read` |
| a scene record, which carries a `game` field like every other | a second population inside the same glob | `pool_populations` |

    python3 eval/tools/wallclock_mutants.py           # the sweep
    python3 eval/tools/wallclock_mutants.py --list    # the count and the names
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "wallclock.py"

# (name, exact span to replace, replacement). The span must be present VERBATIM: a mutant
# whose search text has drifted is a no-op that reports a pass for a check that never
# changed. Drift is a failure below, never a skip.
MUTANTS: dict[str, tuple[str, str]] = {
    "ms_read_as_seconds": (
        '        return (direct / 1000.0, "record") if direct is not None \\',
        '        return (direct, "record") if direct is not None \\'),
    "artifact_never_read": (
        '    artifact = runs_dir / run / "artifacts" / trial_id / ARTIFACT_NAME',
        '    artifact = runs_dir / run / "artifacts" / trial_id / "no_such_file.json"'),
    "fall_through_on_unusable": (
        '            else (None, "record_unusable")',
        "            else self_report_seconds(\n"
        "                runs_dir, run, {**record, \"agent\": {}})"),
    "unreadable_is_absent": (
        '    except (OSError, json.JSONDecodeError):\n'
        '        return None, "artifact_unreadable"',
        '    except (OSError, json.JSONDecodeError):\n'
        '        return None, "artifact_absent"'),
    "bool_is_a_number": (
        "    if isinstance(value, bool) or not isinstance(value, (int, float)):",
        "    if not isinstance(value, (int, float)):"),
    "finite_guard": (
        "    if not math.isfinite(value) or value <= 0:",
        "    if value <= 0:"),
    "zero_is_a_duration": (
        "    if not math.isfinite(value) or value <= 0:",
        "    if not math.isfinite(value) or value < 0:"),
    "negatives_uncounted": (
        "        if delta < 0:",
        "        if False:"),
    "one_unpaired_counter": (
        '        if harness_s is None:\n            pop["no_harness_clock"] += 1',
        "        if harness_s is None:\n            pass"),
    "pool_populations": (
        '    if WHOLEGAME_KEY not in record:\n        return "spec-change"',
        '    if False:\n        return "spec-change"'),
    "empty_is_zero": (
        "    records, _ = load_records(runs_dir)",
        "    try:\n        records, _ = load_records(runs_dir)\n"
        "    except CensusError:\n        records = []"),
    "no_pair_is_agreement": (
        "    if not all_deltas:\n        raise CensusError(",
        "    if False:\n        raise CensusError("),
    "drop_field": (
        '            "negative_deltas": len(negatives),',
        '            "negative_deltas_RENAMED": len(negatives),'),
}

#: Modules a copy of `wallclock.py` needs to import at all. A copy alone in a temp
#: directory dies on `ModuleNotFoundError`, every mutant is scored as caught, and the
#: sweep reports a clean bill of health for a file that cannot run — which is why the
#: control below runs an UNMUTATED copy from the same directory first.
DEPS_IN_TOOLS = ("census.py", "tokenvalue.py")
DEPS_IN_EVAL = ("agent_harness.py",)


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
        for dep in DEPS_IN_TOOLS:
            (Path(tmp) / dep).write_text((HERE / dep).read_text())
        # One directory UP, and copied from there rather than from `tools/`: a dep fetched
        # from the wrong directory is a ModuleNotFoundError that scores every mutant as
        # caught, and only the control says so.
        for dep in DEPS_IN_EVAL:
            (Path(tmp) / dep).write_text((HERE.parent / dep).read_text())

        # THE CONTROL FIRST. An unmutated copy must go GREEN from the same temp directory
        # and the same interpreter the mutants use.
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
                # Exit non-zero via a traceback still catches the mutant; it does not say
                # what broke. Diagnose, do not merely fail.
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
