#!/usr/bin/env python3
"""Reconcile the two clocks that time a trial, and read the one nothing read.

`eval/RUNS.md` treats wall clock as a COMPARISON METRIC, and two harnesses time a trial.
Until this tool there was no producer saying whether their figures were the same
quantity — not the field names, not the docs. `tasks/186`.

## The two clocks, and they are NOT two names for one thing

| | who holds the stopwatch | interval |
|---|---|---|
| **harness clock**, `wall_s` | the harness, around its own `run_agent()` | subprocess spawn, the agent CLI's whole life, reading its stdout, parsing it |
| **self-report**, `duration_ms` | the agent CLI, in its own result object | the CLI's internal run |

The second is nested inside the first, so `wall_s - duration_ms/1000` is the harness's own
overhead and can never be negative unless a clock moved. That is the assertion this tool
makes: `agreement.negative_deltas` must be 0, and a non-zero exit says which trial.

**The overhead is reported in SECONDS and never as a fraction, because it is a constant.** It
is ~1 s on a 1.6 s trial and ~1 s on a 4961 s one, so the ratio of the two clocks is a
measurement of trial LENGTH: over the stored corpus it runs 0.2347 to 0.9998, and the 5 lowest
belong to one run whose trials the API refused in under 2 seconds each. A percentage here pools
those with real builds and describes neither (`AGENTS.md` rule 4).

**It is not a vacuous assertion, because one of the two harnesses does not use a monotonic
clock.** `wholegame.py` brackets with `time.monotonic()`; `runner.py` brackets with
`datetime.now()`, which an NTP step or a DST transition moves under it. A negative delta is
how that would first become visible, and it would be visible in the harness figure every
document quotes.

## Three addresses, and which one a record uses is part of the answer

The self-report is stored by both harnesses and at different addresses, so the address is
an input to the check (rule 12) and is reported per record rather than assumed:

| address | written by |
|---|---|
| `trials/<tid>.json` -> `agent.duration_ms` | `runner.py`, the retired spec-change suite |
| `artifacts/<tid>/agent_result.json` -> `duration_ms` | `wholegame.py`, which stores the CLI's raw result object and does not lift this field into the record |

A record whose self-report is at neither is `unpaired`, with the reason kept — a trial the
harness killed has no result object at all, and that is not the same as a clock that read
zero. **`0` is never a duration here**; an absent figure is reported absent (#36).

## What this is NOT

It is not a cost or a count producer. `python3 eval/tools/census.py` counts the tree and
`python3 eval/tools/cost_census.py` answers whether cost separates the stacks. This tool
adds no walker of its own: it takes `census.load_records`, so the archive wrappers that a
one-level glob loses are found here by construction (#126).

    python3 eval/tools/wallclock.py             # the reconciliation, human-readable
    python3 eval/tools/wallclock.py --json      # the same, machine-readable
    python3 eval/tools/wallclock.py --selftest  # pins the extraction in both directions
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from census import (  # noqa: E402
    DEFAULT_RUNS, WHOLEGAME_KEY, CensusError, load_records, task_class_of,
)

#: The agent CLI's own duration, in milliseconds, wherever it is stored.
SELF_REPORT_KEY = "duration_ms"

#: Where `wholegame.py` puts the CLI's raw result object, relative to the run directory.
ARTIFACT_NAME = "agent_result.json"


def _positive(value: object) -> float | None:
    """A stored figure as a positive finite number, or `None` for one that is not.

    Five shapes are refused rather than read, and every one of them would otherwise
    become a plausible in-range measurement:

    | | |
    |---|---|
    | absent, or `null` | never measured |
    | `True` | a bool IS an `int` in Python and would read as 1 |
    | `NaN`, `inf`, `-inf` | `json.loads` produces all three, and one `NaN` makes a median `NaN` |
    | `0` or negative | no interval this tool times can be either |
    """
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    if not math.isfinite(value) or value <= 0:
        return None
    return float(value)


def self_report_seconds(runs_dir: Path, run: str, record: dict) -> tuple[float | None,
                                                                        str]:
    """The agent CLI's self-reported duration, in SECONDS, and WHERE it was read.

    `duration_ms` is milliseconds at both addresses and `wall_s` is seconds, so the
    conversion happens here, once, rather than at each comparison.

    Returns `(seconds, address)`. The address is `record` or `artifact` when a figure was
    read, and otherwise the reason it was not:

    | reason | what it means |
    |---|---|
    | `record_unusable` | the record HAS the field and it is not a duration |
    | `artifact_absent` | no result object — the harness killed the trial before one was written |
    | `artifact_unreadable` | a result object that will not parse: the capture broke |
    | `artifact_unusable` | it parsed, and the field is not a duration |
    | `no_self_report` | it parsed and this CLI reports no such field. prime-agent does not |
    | `no_trial_id` | the record names no trial, so the artifact has no address to look at |

    The address is RETURNED rather than inferred by the caller, because a whole-game
    record and a spec-change record keep this figure in different places and a reader
    that guessed would report the same wrong answer for a whole population.

    **A record whose own field is present and unusable is not looked up in the artifact.**
    Falling through would answer `artifact_absent` for a corrupt stored figure — a reason
    about the wrong file.
    """
    agent = record.get("agent") or {}
    if SELF_REPORT_KEY in agent:
        direct = _positive(agent[SELF_REPORT_KEY])
        return (direct / 1000.0, "record") if direct is not None \
            else (None, "record_unusable")

    trial_id = record.get("trial_id")
    if not isinstance(trial_id, str) or not trial_id:
        return None, "no_trial_id"
    artifact = runs_dir / run / "artifacts" / trial_id / ARTIFACT_NAME
    if not artifact.is_file():
        return None, "artifact_absent"
    try:
        parsed = json.loads(artifact.read_text())
    except (OSError, json.JSONDecodeError):
        return None, "artifact_unreadable"
    if not isinstance(parsed, dict):
        return None, "artifact_unreadable"
    if SELF_REPORT_KEY not in parsed:
        return None, "no_self_report"
    got = _positive(parsed[SELF_REPORT_KEY])
    return (got / 1000.0, "artifact") if got is not None \
        else (None, "artifact_unusable")


def _population(record: dict) -> str:
    """`whole-game`, `scene` or `spec-change`, by `census`'s own partition."""
    if WHOLEGAME_KEY not in record:
        return "spec-change"
    return "whole-game" if task_class_of(record) == "game" else "scene"


def _stats(values: list[float]) -> dict:
    """min / p25 / median / p75 / max over a non-empty list, or all `None`."""
    if not values:
        return {k: None for k in ("min", "p25", "median", "p75", "max")}
    s = sorted(values)
    return {
        "min": round(s[0], 1),
        "p25": round(s[len(s) // 4], 1),
        "median": round(statistics.median(s), 1),
        "p75": round(s[(3 * len(s)) // 4], 1),
        "max": round(s[-1], 1),
    }


def reconcile(runs_dir: Path) -> dict:
    """Pair the two clocks over every stored trial record.

    Raises `CensusError` on a tree that cannot be read — never a report of zero, which
    is what an agent worktree with no `eval/runs/` would otherwise produce.
    """
    records, _ = load_records(runs_dir)

    pops: dict[str, dict] = {}
    negatives: list[dict] = []
    for run, _name, data in records:
        pop = pops.setdefault(_population(data), {
            "records": 0, "paired": 0, "no_harness_clock": 0,
            "harness_clock_hours": 0.0, "self_report_hours": 0.0,
            "deltas": [], "addresses": {},
        })
        pop["records"] += 1
        harness_s = _positive(data.get("wall_s"))
        self_s, address = self_report_seconds(runs_dir, run, data)
        # TWO COUNTERS, because there are two ways to be unpaired and they are different
        # defects. `addresses` always answers "where did the self-report come from, or
        # why not"; `no_harness_clock` answers "was the harness's own figure readable".
        # One counter would report a trial with neither as a missing self-report alone.
        pop["addresses"][address] = pop["addresses"].get(address, 0) + 1
        if harness_s is None:
            pop["no_harness_clock"] += 1
        if harness_s is None or self_s is None:
            continue
        pop["paired"] += 1
        pop["harness_clock_hours"] += harness_s / 3600.0
        pop["self_report_hours"] += self_s / 3600.0
        delta = harness_s - self_s
        pop["deltas"].append(delta)
        if delta < 0:
            negatives.append({"run": run, "trial_id": data.get("trial_id"),
                              "wall_s": harness_s, "self_report_s": self_s,
                              "delta_s": round(delta, 1)})

    all_deltas: list[float] = []
    for pop in pops.values():
        all_deltas += pop["deltas"]
        pop["harness_overhead_s"] = _stats(pop["deltas"])
        pop["harness_clock_hours"] = round(pop["harness_clock_hours"], 2)
        pop["self_report_hours"] = round(pop["self_report_hours"], 2)
        pop["addresses"] = dict(sorted(pop["addresses"].items()))
        del pop["deltas"]

    # A CORPUS WHERE NOTHING PAIRS IS A REFUSAL, NOT AN AGREEMENT. Without this,
    # `paired_observations: 0, negative_deltas: 0` and exit 0 — `total=0 passed=0`, which
    # `AGENTS.md` rule 1 says is indistinguishable from a correct pass. It is reachable:
    # a tree of prime-agent records alone has no self-report anywhere, and so does one
    # whose `artifacts/` was never synced. The message names the addresses so the two are
    # told apart at a glance rather than by re-deriving them.
    if not all_deltas:
        raise CensusError(
            f"{runs_dir} holds {sum(p['records'] for p in pops.values())} trial record(s) "
            f"and not one carries both clocks — refusing to report agreement over 0 "
            f"observations. Where the self-report was looked for, per population: "
            + "; ".join(f"{n} {p['addresses']}" for n, p in sorted(pops.items())))

    return {
        "runs_dir": str(runs_dir),
        "populations": dict(sorted(pops.items())),
        "agreement": {
            "paired_observations": len(all_deltas),
            "harness_overhead_s": _stats(all_deltas),
            "negative_deltas": len(negatives),
            "negative_examples": negatives[:5],
        },
    }


def render(r: dict) -> str:
    a = r["agreement"]
    o = a["harness_overhead_s"]
    lines = [
        f"read from {r['runs_dir']}",
        "",
        "TWO CLOCKS PER TRIAL, and they are nested rather than alternative:",
        "  harness clock  `wall_s`       the harness, around its own run_agent()",
        f"  self-report    `{SELF_REPORT_KEY}`  the agent CLI, in its own result object",
        "",
    ]
    for name, p in r["populations"].items():
        lines += [
            f"{name.upper()} — {p['records']} record"
            f"{'' if p['records'] == 1 else 's'}, {p['paired']} with both clocks",
            f"  harness clock      {p['harness_clock_hours']:.2f} h over the paired "
            f"records",
            f"  self-report        {p['self_report_hours']:.2f} h over the same records",
            f"  harness overhead   {_fmt_stats(p['harness_overhead_s'])}",
            "  self-report from   " + ", ".join(
                f"{k} {v}" for k, v in p["addresses"].items()),
            f"  no harness clock   {p['no_harness_clock']}",
            "",
        ]
    lines += [
        f"AGREEMENT over {a['paired_observations']} paired observations",
        f"  wall_s - {SELF_REPORT_KEY}/1000   {_fmt_stats(o)}",
        f"  negative deltas    {a['negative_deltas']}  "
        f"(the self-report is nested inside the harness clock; a negative one means a "
        f"clock moved)",
    ]
    for ex in a["negative_examples"]:
        lines.append(f"    NEGATIVE  {ex['run']}/{ex['trial_id']}  "
                     f"wall_s={ex['wall_s']} self={ex['self_report_s']} "
                     f"delta={ex['delta_s']}")
    return "\n".join(lines)


def _fmt_stats(s: dict) -> str:
    if s["median"] is None:
        return "no paired records"
    return (f"min {s['min']}s  p25 {s['p25']}s  median {s['median']}s  "
            f"p75 {s['p75']}s  max {s['max']}s")


# --------------------------------------------------------------------------- selftest

def _write(path: Path, obj: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj))


def _finite(value) -> bool:
    """`math.isfinite`, answering False for anything that is not a number.

    `math.isfinite(None)` raises, and a selftest row that raises is a row that
    cannot go red — the same defect `_dig` exists for, one type down.
    """
    return isinstance(value, (int, float)) and not isinstance(value, bool) \
        and math.isfinite(value)


def _dig(obj, *keys):
    """`obj[k1][k2]...`, or `None` the moment a key or index is not there.

    THE SELFTEST READS THROUGH THIS AND NEVER SUBSCRIPTS DIRECTLY, because a suite that
    dies on a `KeyError` and a suite that reddens a row both exit non-zero, and only one
    of them says what broke. A renamed field, a population that vanished and an empty
    example list each used to end the run several frames from the check that cared
    (`wallclock_mutants.drop_field`).
    """
    for key in keys:
        try:
            obj = obj[key]
        except (KeyError, IndexError, TypeError):
            return None
    return obj


def selftest() -> int:
    """Pin the extraction against a tree whose answer is stated before it is measured."""
    import tempfile

    failures: list[str] = []

    def check(label: str, got, want) -> None:
        if got != want:
            failures.append(f"{label}: got {got!r}, want {want!r}")

    with tempfile.TemporaryDirectory() as tmp:
        runs = Path(tmp) / "runs"

        # Direction 1: a missing tree refuses. An agent worktree has no eval/runs/, and
        # "0 paired observations, no negatives" is the shape of a green gate that read
        # nothing.
        #
        # THE MESSAGE IS ASSERTED, NOT ONLY THE EXCEPTION TYPE, and the mutant sweep is
        # what forced that. There are now TWO refusals raising `CensusError` - the tree
        # could not be read, and the tree read fine and nothing paired - so a type-only
        # check passes on either, and `empty_is_zero` (which deletes the first) survived
        # by falling into the second. Both exits are correct; only one is the right
        # DIAGNOSIS, and a reader handed the wrong one goes looking in the wrong place.
        try:
            reconcile(runs)
            failures.append("missing runs dir: returned a report instead of raising")
        except CensusError as exc:
            check("the missing-tree refusal names the tree, not the pairing",
                  "no runs directory at" in str(exc), True)

        # Direction 1a: an existing but EMPTY tree refuses too, and for its own reason.
        runs.mkdir(parents=True)
        try:
            reconcile(runs)
            failures.append("empty runs dir: returned a report instead of raising")
        except CensusError as exc:
            check("the empty-tree refusal names what it did not find",
                  "holds no **/trials/*.json" in str(exc), True)

        # Direction 1b: A CORPUS WHERE NOTHING PAIRS IS ALSO A REFUSAL. This one is not
        # about a tree that cannot be read - the records are here, they parse, and the
        # census is happy. Every one of them simply lacks a clock, which is reachable for
        # real: a tree of prime-agent records alone, or one whose `artifacts/` was never
        # synced. Without the guard this is `paired_observations: 0, negative_deltas: 0`
        # at exit 0 - `total=0 passed=0`, the shape rule 1 forbids, and the ONLY assertion
        # this tool makes would be vacuously green.
        with tempfile.TemporaryDirectory() as tmp0:
            unpaired = Path(tmp0) / "runs"
            _write(unpaired / "wg-p" / "trials" / "g1__rust__t0.json",
                   {"trial_id": "g1__rust__t0", "game": "g1", "stack": "rust",
                    "wall_s": 10.3, "harness": {"name": "prime-agent"},
                    "agent": {"harness": "prime-agent",
                              "terminal_reason": "completed"}})
            _write(unpaired / "wg-p" / "artifacts" / "g1__rust__t0" / ARTIFACT_NAME,
                   {"harness": "prime-agent", "exit_code": 0, "messages": []})
            try:
                reconcile(unpaired)
                failures.append("a corpus where nothing pairs: reported agreement over "
                                "0 observations instead of raising")
            except CensusError as exc:
                # The refusal has to be diagnosable, or the next reader re-derives WHY
                # nothing paired from the tree by hand.
                check("the no-pair refusal names where it looked",
                      "no_self_report" in str(exc), True)

        # THE KNOWN-ANSWER TREE, stated first.
        #
        # spec-change: 2 records, both paired FROM THE RECORD, deltas 1.0 and 2.0.
        #   One of them is NESTED inside an archive wrapper, which is the case a
        #   one-level glob loses (#126) — if the walker regressed, `paired` reads 1.
        _write(runs / "core-x" / "trials" / "t1_rally__rust__t0.json",
               {"trial_id": "t1_rally__rust__t0", "task": "t1_rally", "wall_s": 101.0,
                "agent": {"duration_ms": 100000}})
        _write(runs / "archive-x" / "core-y" / "trials" / "t2_net__ts__t0.json",
               {"trial_id": "t2_net__ts__t0", "task": "t2_net", "wall_s": 202.0,
                "agent": {"duration_ms": 200000}})

        # whole-game: 5 records, 2 paired FROM THE ARTIFACT with deltas 3.0 and 4.0, and
        #   3 unpaired for three DIFFERENT reasons that must not collapse into one.
        _write(runs / "wg-a" / "trials" / "g1__rust__t0.json",
               {"trial_id": "g1__rust__t0", "game": "g1", "stack": "rust",
                "wall_s": 303.0, "agent": {"terminal_reason": "completed"}})
        _write(runs / "wg-a" / "artifacts" / "g1__rust__t0" / ARTIFACT_NAME,
               {"duration_ms": 300000, "result": "done"})
        _write(runs / "wg-a" / "trials" / "g1__ts__t0.json",
               {"trial_id": "g1__ts__t0", "game": "g1", "stack": "ts", "wall_s": 404.0,
                "agent": {"terminal_reason": "completed"}})
        _write(runs / "wg-a" / "artifacts" / "g1__ts__t0" / ARTIFACT_NAME,
               {"duration_ms": 400000})
        # 1: killed mid-trial — no result object was ever written.
        _write(runs / "wg-a" / "trials" / "g1__godot__t0.json",
               {"trial_id": "g1__godot__t0", "game": "g1", "stack": "godot",
                "wall_s": 500.0, "agent": {"terminal_reason": None}})
        # 2: a result object that exists and is EMPTY. This is the shape the four wedged
        #    arena trials stored, and it is not the same as no object at all.
        _write(runs / "wg-a" / "trials" / "g1__unity__t0.json",
               {"trial_id": "g1__unity__t0", "game": "g1", "stack": "unity",
                "wall_s": 600.0, "agent": {"terminal_reason": None}})
        _write(runs / "wg-a" / "artifacts" / "g1__unity__t0" / ARTIFACT_NAME, {})
        # 3: another harness, whose CLI reports no such field at all.
        _write(runs / "wg-b" / "trials" / "g1__rust__t9.json",
               {"trial_id": "g1__rust__t9", "game": "g1", "stack": "rust",
                "wall_s": 10.3, "harness": {"name": "prime-agent"},
                "agent": {"harness": "prime-agent", "terminal_reason": "completed"}})
        _write(runs / "wg-b" / "artifacts" / "g1__rust__t9" / ARTIFACT_NAME,
               {"harness": "prime-agent", "exit_code": 0, "messages": []})

        # scene: 1 record, paired from the artifact, delta 5.0. Kept OUT of the
        #   whole-game figures — `eval/SCENES.md` forbids pooling the two.
        _write(runs / "wg-scene" / "trials" / "s1_parallax__ts__t0.json",
               {"trial_id": "s1_parallax__ts__t0", "game": "s1_parallax",
                "task_class": "scene", "stack": "ts", "wall_s": 705.0,
                "agent": {"terminal_reason": "completed"}})
        _write(runs / "wg-scene" / "artifacts" / "s1_parallax__ts__t0" / ARTIFACT_NAME,
               {"duration_ms": 700000})

        r = reconcile(runs)
        pops, agree = r["populations"], r["agreement"]

        check("three populations", sorted(pops), ["scene", "spec-change", "whole-game"])
        check("spec-change records", _dig(pops, "spec-change", "records"), 2)
        # If the nested run were lost this reads 1, with every other row still green.
        check("spec-change paired (the nested run is found)",
              _dig(pops, "spec-change", "paired"), 2)
        check("spec-change read from the record only",
              _dig(pops, "spec-change", "addresses"), {"record": 2})
        check("whole-game records", _dig(pops, "whole-game", "records"), 5)
        check("whole-game paired", _dig(pops, "whole-game", "paired"), 2)
        # THREE UNPAIRED REASONS, KEPT APART. Collapsing them into one counter is what
        # makes "the field is missing" indistinguishable from "the trial was killed".
        check("whole-game addresses", _dig(pops, "whole-game", "addresses"),
              {"artifact": 2, "artifact_absent": 1, "no_self_report": 2})
        check("scene records", _dig(pops, "scene", "records"), 1)
        check("scene paired", _dig(pops, "scene", "paired"), 1)
        check("no scene record reached the whole-game count",
              _dig(pops, "whole-game", "records"), 5)

        check("paired observations", _dig(agree, "paired_observations"), 5)
        check("overhead min", _dig(agree, "harness_overhead_s", "min"), 1.0)
        check("overhead median", _dig(agree, "harness_overhead_s", "median"), 3.0)
        check("overhead max", _dig(agree, "harness_overhead_s", "max"), 5.0)
        check("no negative deltas", _dig(agree, "negative_deltas"), 0)
        # The hour totals are over the PAIRED records only, and both clocks are summed
        # over the same rows — a total over one clock's population and the other's would
        # differ by whatever the unpaired records held.
        check("whole-game harness hours",
              _dig(pops, "whole-game", "harness_clock_hours"),
              round(707.0 / 3600, 2))
        check("whole-game self-report hours",
              _dig(pops, "whole-game", "self_report_hours"),
              round(700.0 / 3600, 2))

        # Direction 2: A NEGATIVE DELTA IS SEEN AND NAMED. The self-report is nested
        # inside the harness clock, so this cannot happen unless a clock moved — and
        # `runner.py` times with `datetime.now()`, which an NTP step moves. A tool that
        # only ever printed a median would report this trial as a 0.0s overhead.
        _write(runs / "core-x" / "trials" / "t3_skew__rust__t0.json",
               {"trial_id": "t3_skew__rust__t0", "task": "t3_skew", "wall_s": 90.0,
                "agent": {"duration_ms": 100000}})
        neg = reconcile(runs)["agreement"]
        check("the negative delta is counted", _dig(neg, "negative_deltas"), 1)
        check("and the trial is named",
              _dig(neg, "negative_examples", 0, "trial_id"), "t3_skew__rust__t0")
        check("and it is signed",
              _dig(neg, "negative_examples", 0, "delta_s"), -10.0)
        (runs / "core-x" / "trials" / "t3_skew__rust__t0.json").unlink()

        # Direction 3: FOUR FIGURES THAT ARE NUMBERS TO A READER AND NOT TO A CLOCK.
        # `json.dumps` emits the bare NaN/Infinity/-Infinity tokens, so the bytes on disk
        # are a stored record's. `true` passes `isinstance(x, int)` and would read as
        # 1 ms; `0` would read as an instantaneous agent. Each must leave the record
        # UNPAIRED rather than contribute a plausible delta.
        for i, value in enumerate((float("nan"), float("inf"), float("-inf"), True, 0)):
            _write(runs / "core-x" / "trials" / f"t4_bad__rust__t{i}.json",
                   {"trial_id": f"t4_bad__rust__t{i}", "task": "t4_bad",
                    "wall_s": 100.0, "agent": {"duration_ms": value}})
        bad = reconcile(runs)
        check("no unusable figure was paired",
              _dig(bad, "populations", "spec-change", "paired"), 2)
        # `record_unusable`, NOT `artifact_absent`: the record has the field and it is
        # corrupt, which is a fact about this file and not about a file that was never
        # written. Falling through to the artifact would answer about the wrong one.
        check("and each is reported against the file that holds it",
              _dig(bad, "populations", "spec-change", "addresses",
                   "record_unusable"), 5)
        check("the overall median is unmoved",
              _dig(bad, "agreement", "harness_overhead_s", "median"), 3.0)
        check("the median is finite",
              _finite(_dig(bad, "agreement", "harness_overhead_s", "median")),
              True)
        for i in range(5):
            (runs / "core-x" / "trials" / f"t4_bad__rust__t{i}.json").unlink()

        # Direction 4: THE SAME FOUR SHAPES IN `wall_s`. A record with an unusable
        # harness clock is unpaired too, and it is reported as `no_harness_clock` rather
        # than as a missing self-report — the two are different defects.
        _write(runs / "core-x" / "trials" / "t5_noclock__rust__t0.json",
               {"trial_id": "t5_noclock__rust__t0", "task": "t5_noclock",
                "wall_s": None, "agent": {"duration_ms": 100000}})
        nc = _dig(reconcile(runs), "populations", "spec-change")
        check("an unusable wall_s is unpaired", _dig(nc, "paired"), 2)
        check("its self-report was still read, and from the record",
              _dig(nc, "addresses"), {"record": 3})
        check("and the missing clock is counted on its own axis",
              _dig(nc, "no_harness_clock"), 1)
        (runs / "core-x" / "trials" / "t5_noclock__rust__t0.json").unlink()

        # Direction 5: an UNREADABLE artifact is not an absent one. A truncated result
        # object is evidence the capture broke; a missing one is evidence the trial was
        # killed. Reading both as "no figure" loses the distinction the address exists
        # to make.
        _write(runs / "wg-a" / "trials" / "g1__godot__t9.json",
               {"trial_id": "g1__godot__t9", "game": "g1", "stack": "godot",
                "wall_s": 800.0, "agent": {"terminal_reason": "completed"}})
        art = runs / "wg-a" / "artifacts" / "g1__godot__t9" / ARTIFACT_NAME
        art.parent.mkdir(parents=True, exist_ok=True)
        art.write_text('{"duration_ms": 80')
        ur = _dig(reconcile(runs), "populations", "whole-game")
        check("an unreadable artifact is named as such",
              _dig(ur, "addresses", "artifact_unreadable"), 1)
        check("and it did not pair", _dig(ur, "paired"), 2)
        (runs / "wg-a" / "trials" / "g1__godot__t9.json").unlink()

    for f in failures:
        print(f"FAIL  {f}")
    print(f"wallclock selftest: {'FAILED' if failures else 'ok'} "
          f"({len(failures)} failures)")
    return 1 if failures else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--runs-dir", default=str(DEFAULT_RUNS),
                    help="tree to reconcile over (default: eval/runs/)")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--selftest", action="store_true",
                    help="pin the extraction against a tree with a known answer")
    args = ap.parse_args()

    if args.selftest:
        return selftest()

    try:
        r = reconcile(Path(args.runs_dir).expanduser().resolve())
    except CensusError as exc:
        print(f"wallclock: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(r, indent=2) if args.json else render(r))
    # THE ASSERTION, not just the report. The self-report is nested inside the harness
    # clock, so a negative delta means a clock moved during a trial — and `runner.py`
    # brackets with a non-monotonic `datetime.now()`, so that is a real hazard rather
    # than an impossible one. Exit non-zero so it cannot be read past.
    return 1 if r["agreement"]["negative_deltas"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
