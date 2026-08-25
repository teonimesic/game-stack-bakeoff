#!/usr/bin/env python3
"""Count what the stored tree actually holds, so no document has to remember.

`README.md`'s opening sentence used to assert "24 whole-game submissions, three games,
four stacks, two independent trials per cell". Every one of those was true of a single
run in August 2026 and none of them was true of the tree; nothing in the repository
produced any of them, so nothing could notice when they stopped being true. This is the
producer. It reports the counts and, with every one, the **population** it counted over —
an aggregate without its scope is unfalsifiable (#113).

Three populations live under `eval/runs/**/trials/*.json` and must never be summed blind:

| population | test | what it is |
|---|---|---|
| whole-game | `task_class` is `game`, or the key is ABSENT | `wholegame.py` game submissions — the bake-off |
| scene | `task_class` is `scene` | a timed sequence with no player (`eval/SCENES.md`) |
| spec-change | record has no `game` field | the retired `runner.py` suite (`eval/AGENTS.md`) |

Any other `task_class` is **refused by name**, not read as a game — including `null`,
which is a present value rather than an absence: a partition keyed on one recognised value
puts every unrecognised one inside the published bake-off figure.

**A scene record carries a `game` field like every other**, so the `game`-field test alone
put it in the whole-game count — one population's trials inside another population's
figure, which is the pooling `eval/SCENES.md` forbids in as many words. The class is read
off `task_class`, which `wholegame.py` writes into every record. **Absent reads as `game`,
and that is a fact rather than a default**: the field arrived in the same change that made
a scene launchable at all, so no record without it can be a scene.

Within the whole-game population, partition by `agent.terminal_reason` before computing
anything (`eval/AGENTS.md`, rule 4). Four `archive-arena2d` records predate the field and
are reported as `absent`, not folded into any other bucket.

**A run directory is not always a child of `runs/`.** `archive-run1-byte-identical-prompts/`
is a wrapper holding four run directories one level deeper, and the `*/trials/*.json` glob
this tool shipped with dropped all 24 of their records without saying so — reporting 47
spec-change records against a tree holding 71, and 137 tree-wide against 161 (#126). The
search is now depth-independent and a run is identified by its path relative to `runs/`, so
the count cannot be wrong about where it looked. Directories holding agent-authored trees
(`work/`, `artifacts/`, `targets/`) are excluded and the number excluded is reported, because
a skip nobody counts is the defect this replaces.

**A THIRD partition, and it is a partition of the UNIT: which agent CLI built the record.**
`agent.harness` names it, and every record stored before 2026-08-24 has no such field
because there was only one — so an absent field reads as `claude`. The record COUNTS are
over every harness; the `agent.cost_usd` sums are over `claude` alone, and each prints how
many records it could not price. tokval is a list price for one vendor's tokens (#159);
adding another vendor's figure to it produces a number in no unit at all.

**This tool fails rather than returning zero.** A missing runs directory and an empty one
both exit 2. An agent worktree has no `eval/runs/` — it is gitignored — so the honest
answer there is a refusal, not `0 records`, which is the shape rule 3 forbids. The
resolved absolute path is printed with the counts, because the address is an input to the
check (#60, rule 12).

Judge-round cost is **not** counted here: its producer is
`python3 eval/judge/judge_ledger.py --tree eval/runs/`, which is what `eval/RUNS.md`
quotes. Two producers, two figures, neither carried forward from a document.

    python3 eval/tools/census.py               # the counts, human-readable
    python3 eval/tools/census.py --json        # the same, machine-readable
    python3 eval/tools/census.py --selftest    # pins the extraction in both directions
"""

from __future__ import annotations

import argparse
import collections
import datetime as _dt
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import tokenvalue  # noqa: E402

# ONE definition of which harness a record came from and which one is priced in tokval,
# imported rather than restated. It was spelled out here and again in `cost_census.py` —
# the two producers that decide which records may be summed — with nothing asserting the
# two agreed, which is rule 12 with a dollar figure attached.
from agent_harness import TOKVAL_HARNESS, harness_of  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RUNS = ROOT / "eval" / "runs"

# The field whose presence separates the two populations. A whole-game record is written
# by wholegame.py, which always sets it; a spec-change record is written by runner.py,
# which never does.
WHOLEGAME_KEY = "game"

#: Which task class a stored record belongs to. Written by `wholegame.py build`.
TASK_CLASS_KEY = "task_class"


#: Every class this census knows how to partition. A PRESENT value outside it is refused.
TASK_CLASSES = frozenset({"game", "scene"})

#: Distinguishes an ABSENT `task_class` from one stored as `null`.
#:
#: `record.get(KEY)` returns `None` for both, and they are opposite claims: absent means
#: "written by a harness that could not launch a scene" and is read as `game`; `null` is a
#: record that HAS the field and did not say what it holds. `dict.get`'s second argument
#: is the only thing that separates them, and it has to be a value no stored record can
#: carry - `None` cannot be, which is exactly the collision.
_ABSENT = object()


def task_class_of(record: dict) -> str:
    """`"game"` or `"scene"` for one stored record. Raises on a class it does not know.

    ABSENT READS AS `game` BY CONSTRUCTION, not by convenience. `wholegame.py` gained
    `--scenes` and this field in one change, so a record written without the field was
    written by a harness that could not launch a scene. Reading it as `game` is therefore
    a statement about the corpus, and it is one a scene record cannot slip past: any
    record a scene run produces carries the field.

    A PRESENT VALUE THIS DOES NOT KNOW IS REFUSED, and that is a different question from
    the absent one. `== "scene" else "game"` tests one instance of an open class: a third
    task class, or `"Scene"` off a typo, would land inside the published bake-off count
    and its tokval total with nothing saying so. A partition whose trigger enumerates the
    values it happened to know about is the failure this repository has a rule for.

    `null` IS A PRESENT VALUE AND IS REFUSED WITH THE REST. `record.get(KEY)` answers
    `None` for an absent key and for `"task_class": null`, so the default that makes the
    absent case a `game` would silently make the null case one too - a record that has
    the field and did not say what it holds, counted inside the bake-off figure. The
    sentinel is what separates them.
    """
    klass = record.get(TASK_CLASS_KEY, _ABSENT)
    if klass is _ABSENT:
        return "game"
    if klass not in TASK_CLASSES:
        raise CensusError(f"`{TASK_CLASS_KEY}` is {klass!r}, which is not one of "
                          f"{sorted(TASK_CLASSES)} — refusing to pool it into a "
                          f"population it may not belong to")
    return klass

# Directories that hold trees written by a building agent or by a toolchain, not by a
# harness. A `trials/` directory appearing under one of these is not ours; counting it
# would be fail-open. Every skip is counted and reported.
NOT_A_RUN = frozenset({"work", "artifacts", "targets"})


class CensusError(RuntimeError):
    """The tree could not be read. Never downgraded to a count of zero."""


def trial_paths(runs_dir: Path) -> tuple[list[Path], list[Path]]:
    """(counted, skipped) trial-record paths, found at any depth under runs_dir.

    Depth-independent because `archive-run1-byte-identical-prompts/` wraps four run
    directories and a one-level glob silently lost all 24 of their records (#126).
    """
    counted, skipped = [], []
    for path in sorted(runs_dir.rglob("trials/*.json")):
        # parts between runs_dir and the `trials/` component
        stem = path.relative_to(runs_dir).parts[:-2]
        (skipped if NOT_A_RUN.intersection(stem) else counted).append(path)
    return counted, skipped


def load_records(runs_dir: Path) -> tuple[list[tuple[str, str, dict]], list[Path]]:
    """Every stored trial record as (run_directory, filename, parsed), plus the skips.

    `run_directory` is the run's path RELATIVE to runs_dir, so a nested archive is
    distinguishable from a top-level run of the same name and the identifier says where
    the record was read from (rule 12).

    Raises CensusError if the directory is missing or holds no trial records, and lets a
    JSONDecodeError escape naming its file. Returning an empty list for any of those
    would be indistinguishable from a tree that is genuinely empty.
    """
    if not runs_dir.is_dir():
        raise CensusError(f"no runs directory at {runs_dir} (it is gitignored; an agent "
                          f"worktree does not have one — read the main checkout)")
    counted, skipped = trial_paths(runs_dir)
    out = []
    for path in counted:
        try:
            data = json.loads(path.read_text())
        except json.JSONDecodeError as exc:
            raise CensusError(f"{path}: {exc}") from exc
        # A TRIAL FILE THAT IS NOT AN OBJECT FAILS BY NAME TOO, and it must be asked
        # FIRST: `"agent" in data` on a JSON string is a SUBSTRING test, so a file
        # holding `"agent"` answers True and `data["agent"]` then raises `TypeError`
        # naming no path. Every reader below assumes a mapping.
        if not isinstance(data, dict):
            raise CensusError(f"{path}: the record is {type(data).__name__}, not an "
                              f"object — a trial file is a JSON object")
        # A RECORD WHOSE `agent` BLOCK IS PRESENT AND IS NOT AN OBJECT FAILS BY NAME.
        # `_terminal` and `_cost` both call `.get` on it, so `"agent": null` used to end
        # the census with an `AttributeError` several frames away, naming no file — loud,
        # and useless. This is the same refusal `cost_census._validate_wholegame` already
        # makes, and it keeps the promise this module's docstring makes about failing
        # rather than reporting a count it cannot stand behind. An ABSENT `agent` key is
        # not this: it reads as `absent` and always has.
        if "agent" in data and not isinstance(data["agent"], dict):
            raise CensusError(f"{path}: `agent` is {data['agent']!r}, not an object — "
                              f"nothing can be read from it")
        # A TASK CLASS NOBODY HERE PARTITIONS FAILS BY NAME, here rather than at the
        # point of use, because `task_class_of` is called from inside a comprehension
        # over every record and has no path to name.
        try:
            task_class_of(data)
        except CensusError as exc:
            raise CensusError(f"{path}: {exc}") from exc
        out.append((str(path.parent.parent.relative_to(runs_dir)), path.name, data))
    if not out:
        raise CensusError(f"{runs_dir} holds no **/trials/*.json — refusing to report 0 "
                          f"({len(skipped)} paths skipped as agent-authored)")
    return out, skipped


def _cost(record: dict) -> float:
    """A record's tokval, or 0 for a record that HAS no tokval.

    Callers must filter with `_priced` first; this returns 0 for an unpriced record so a
    partial sum cannot raise, and `cost_unpriced_records` reports how many were left out.
    """
    return record.get("agent", {}).get("cost_usd") or 0.0


def _priced(record: dict) -> bool:
    """Whether this record's cost may enter a tokval sum. TWO ways to fail it.

    **A dollar figure is per harness and the harnesses are not addable.** `tokval` is a
    list price for Anthropic tokens; prime-agent's figure is OpenAI's list price for
    OpenAI tokens, and neither was paid (#159). Summing them adds two vendors' price
    lists.

    **And a record of the right harness with no USABLE figure is unpriced too.** It used
    to pass this test on the harness alone, contribute `0.0` through `_cost`, and appear
    in no exclusion count — so the note beside the total understated what the total left
    out. A `claude` record with no `cost_usd` is not hypothetical:
    `ClaudeHarness.timeout_record` produces one. An absent count is reported, never summed
    as zero (#36).

    Three shapes are refused rather than summed, and each turns a total into a number that
    looks like a measurement:

    | | |
    |---|---|
    | `None`, or absent | the figure was never measured |
    | `True` | a bool IS an `int` in Python, so it would average as 1.00 |
    | `NaN`, `inf`, `-inf` | `json.loads` produces all three, and **one of them makes the whole total `NaN`** — an aggregate that is wrong about every record because of one |
    """
    if harness_of(record) != TOKVAL_HARNESS:
        return False
    cost = record.get("agent", {}).get("cost_usd")
    if isinstance(cost, bool) or not isinstance(cost, (int, float)):
        return False
    return math.isfinite(cost)


def _terminal(record: dict) -> str:
    return record.get("agent", {}).get("terminal_reason") or "absent"


def census(runs_dir: Path) -> dict:
    records, skipped = load_records(runs_dir)
    tasks = [r for r in records if WHOLEGAME_KEY in r[2]]
    wholegame = [r for r in tasks if task_class_of(r[2]) == "game"]
    scenes = [r for r in tasks if task_class_of(r[2]) == "scene"]
    specchange = [r for r in records if WHOLEGAME_KEY not in r[2]]

    cells = collections.Counter((d["game"], d["stack"]) for _, _, d in wholegame)
    per_run = {}
    for run in sorted({r for r, _, _ in wholegame}):
        rows = [d for r, _, d in wholegame if r == run]
        per_run[run] = {
            "records": len(rows),
            "games": sorted({d["game"] for d in rows}),
            "stacks": sorted({d["stack"] for d in rows}),
            "trials_per_cell": sorted(
                set(collections.Counter((d["game"], d["stack"]) for d in rows).values())),
            "terminal_reason": dict(
                sorted(collections.Counter(_terminal(d) for d in rows).items())),
            "harness": dict(
                sorted(collections.Counter(harness_of(d) for d in rows).items())),
        }

    return {
        "read_on": _dt.date.today().isoformat(),
        "runs_dir": str(runs_dir),
        "tree": {
            "trial_records": len(records),
            "run_directories": len({r for r, _, _ in records}),
            "agent_cost_usd": round(
                sum(_cost(d) for _, _, d in records if _priced(d)), 2),
            "cost_unpriced_records": sum(
                1 for _, _, d in records if not _priced(d)),
            "harness": dict(sorted(collections.Counter(
                harness_of(d) for _, _, d in records).items())),
            "skipped_agent_authored": len(skipped),
        },
        "wholegame": {
            "population": "stored trial records carrying a `game` field",
            "trial_records": len(wholegame),
            "run_directories": len({r for r, _, _ in wholegame}),
            "games": dict(sorted(collections.Counter(
                d["game"] for _, _, d in wholegame).items())),
            "stacks": dict(sorted(collections.Counter(
                d["stack"] for _, _, d in wholegame).items())),
            "cells": len(cells),
            "trials_per_cell_min": min(cells.values()) if cells else 0,
            "trials_per_cell_max": max(cells.values()) if cells else 0,
            "terminal_reason": dict(sorted(collections.Counter(
                _terminal(d) for _, _, d in wholegame).items())),
            "agent_cost_usd": round(
                sum(_cost(d) for _, _, d in wholegame if _priced(d)), 2),
            "cost_unpriced_records": sum(
                1 for _, _, d in wholegame if not _priced(d)),
            "harness": dict(sorted(collections.Counter(
                harness_of(d) for _, _, d in wholegame).items())),
            "per_run": per_run,
        },
        "scene": {
            "population": "stored trial records whose `task_class` is `scene`",
            "trial_records": len(scenes),
            "run_directories": len({r for r, _, _ in scenes}),
            "scenes": dict(sorted(collections.Counter(
                d["game"] for _, _, d in scenes).items())),
            "stacks": dict(sorted(collections.Counter(
                d["stack"] for _, _, d in scenes).items())),
            "terminal_reason": dict(sorted(collections.Counter(
                _terminal(d) for _, _, d in scenes).items())),
            "agent_cost_usd": round(
                sum(_cost(d) for _, _, d in scenes if _priced(d)), 2),
            "cost_unpriced_records": sum(
                1 for _, _, d in scenes if not _priced(d)),
            "harness": dict(sorted(collections.Counter(
                harness_of(d) for _, _, d in scenes).items())),
        },
        "specchange": {
            "population": "stored trial records with no `game` field — the retired suite",
            "trial_records": len(specchange),
            "run_directories": len({r for r, _, _ in specchange}),
            "agent_cost_usd": round(
                sum(_cost(d) for _, _, d in specchange if _priced(d)), 2),
            "cost_unpriced_records": sum(
                1 for _, _, d in specchange if not _priced(d)),
        },
    }


def _fmt_counter(counter: dict) -> str:
    return ", ".join(f"{k} {v}" for k, v in counter.items())


def _unpriced_note(n: int) -> str:
    """What the tokval line LEFT OUT, printed on the line itself.

    A sum over one harness, presented beside a record count over all of them, is a
    figure whose population is not the one the reader is looking at. The two vendors'
    price lists are not addable and neither was paid (#159), so the sum stays
    single-harness and says how many records it could not price.
    """
    if not n:
        return ""
    return (f"  ({n} record(s) EXCLUDED: another harness, whose USD figure is "
            f"another vendor's price list and is not addable to this one — or a "
            f"record of this harness carrying no readable cost_usd)")


def render(c: dict) -> str:
    wg, sc, tree, scn = (c["wholegame"], c["specchange"], c["tree"], c["scene"])
    biggest = max(wg["per_run"].items(), key=lambda kv: kv[1]["records"], default=None)
    lines = [
        f"read on {c['read_on']} from {c['runs_dir']}",
        "",
        f"WHOLE-GAME — population: {wg['population']}",
        f"  trial records      {wg['trial_records']}",
        f"  run directories    {wg['run_directories']}",
        f"  games              {len(wg['games'])}   {_fmt_counter(wg['games'])}",
        f"  stacks             {len(wg['stacks'])}   {_fmt_counter(wg['stacks'])}",
        f"  game x stack cells {wg['cells']}  "
        f"({wg['trials_per_cell_min']}-{wg['trials_per_cell_max']} trials each, pooled "
        f"across runs — NOT a per-cell replicate count)",
        f"  terminal_reason    {_fmt_counter(wg['terminal_reason'])}",
        f"  harness            {_fmt_counter(wg['harness'])}",
        f"  agent.cost_usd     {wg['agent_cost_usd']:,.2f} {tokenvalue.UNIT}"
        + _unpriced_note(wg['cost_unpriced_records']),
    ]
    if biggest:
        name, info = biggest
        lines += [
            "",
            f"LARGEST SINGLE MATRIX — {name}",
            f"  {info['records']} records = {len(info['games'])} games x "
            f"{len(info['stacks'])} stacks x {info['trials_per_cell']} trials per cell",
            f"  terminal_reason    {_fmt_counter(info['terminal_reason'])}",
        ]
    lines += [
        "",
        f"SCENE — population: {scn['population']}",
        f"  trial records      {scn['trial_records']}",
    ]
    if scn["trial_records"]:
        lines += [
            f"  run directories    {scn['run_directories']}",
            f"  scenes             {len(scn['scenes'])}   {_fmt_counter(scn['scenes'])}",
            f"  stacks             {len(scn['stacks'])}   {_fmt_counter(scn['stacks'])}",
            f"  terminal_reason    {_fmt_counter(scn['terminal_reason'])}",
            f"  harness            {_fmt_counter(scn['harness'])}",
            f"  agent.cost_usd     {scn['agent_cost_usd']:,.2f} {tokenvalue.UNIT}"
            + _unpriced_note(scn['cost_unpriced_records']),
        ]
    lines += [
        "  NEVER pooled with the whole-game figures above — different task class, "
        "different tier-2",
        "  instrument, different criteria (eval/SCENES.md).",
        "",
        f"SPEC-CHANGE — population: {sc['population']}",
        f"  trial records      {sc['trial_records']}",
        f"  run directories    {sc['run_directories']}",
        f"  agent.cost_usd     {sc['agent_cost_usd']:,.2f} {tokenvalue.UNIT}"
        + _unpriced_note(sc['cost_unpriced_records']),
        "",
        "WHOLE TREE — both populations, summed only where a sum is meaningful",
        f"  trial records      {tree['trial_records']} across "
        f"{tree['run_directories']} run directories, found at any depth",
        f"  agent.cost_usd     {tree['agent_cost_usd']:,.2f} {tokenvalue.UNIT}"
        + _unpriced_note(tree['cost_unpriced_records']),
        f"  skipped            {tree['skipped_agent_authored']} trials/*.json under "
        f"{'/, '.join(sorted(NOT_A_RUN))}/ — agent-authored, not harness records",
        "",
        "judge-round token valuation is a different producer: "
        "python3 eval/judge/judge_ledger.py --tree eval/runs/",
        "",
        tokenvalue.DEFINITION,
    ]
    return "\n".join(lines)


# --------------------------------------------------------------------------- selftest

def _write(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj))


def selftest() -> int:
    """Pin the extraction in both directions on a tree whose answer is stated first."""
    import tempfile

    failures: list[str] = []

    def check(label: str, got, want) -> None:
        if got != want:
            failures.append(f"{label}: got {got!r}, want {want!r}")

    with tempfile.TemporaryDirectory() as tmp:
        runs = Path(tmp) / "runs"

        # Direction 1: a missing tree must refuse, not report zero.
        try:
            census(runs)
            failures.append("missing runs dir: returned a census instead of raising")
        except CensusError:
            pass

        # Direction 2: an existing but empty tree must also refuse.
        runs.mkdir(parents=True)
        try:
            census(runs)
            failures.append("empty runs dir: returned a census instead of raising")
        except CensusError:
            pass

        # The known-answer tree, stated before it is measured:
        #   2 scene records over 1 run dir, 1 scene, 1 stack, 40.00 tokval, in NONE of
        #     the whole-game figures;
        #   3 whole-game records over 2 run dirs, 2 games, 2 stacks, 3 cells,
        #   terminal completed 1 / api_error 1 / absent 1, 6.00 tokval;
        #   2 spec-change records over 2 run dirs, 9.00 tokval — ONE OF THEM NESTED inside an
        #   archive wrapper, which is the case a one-level glob lost (#126);
        #   tree 5 records, 4 dirs, 15.00 tokval, 1 skipped as agent-authored.
        _write(runs / "wg-a" / "trials" / "g1__rust__t0.json",
               {"game": "g1", "stack": "rust", "trial": 0,
                "agent": {"cost_usd": 1.0, "terminal_reason": "completed"}})
        _write(runs / "wg-a" / "trials" / "g1__ts__t0.json",
               {"game": "g1", "stack": "ts", "trial": 0,
                "agent": {"cost_usd": 2.0, "terminal_reason": "api_error"}})
        _write(runs / "wg-b" / "trials" / "g2__rust__t0.json",
               {"game": "g2", "stack": "rust", "trial": 0, "agent": {"cost_usd": 3.0}})
        _write(runs / "core-x" / "trials" / "t1_rally__rust__t0.json",
               {"task": "t1_rally", "agent": {"cost_usd": 1.0,
                                              "terminal_reason": "completed"}})
        # Direction 4a: a run nested inside an archive wrapper MUST be counted, as its
        # own run directory, identified by its path relative to runs/.
        _write(runs / "archive-x" / "core-y" / "trials" / "t2_net__ts__t0.json",
               {"task": "t2_net", "agent": {"cost_usd": 8.0,
                                            "terminal_reason": "completed"}})
        # Direction 4b: a trials/ directory inside an agent-authored tree must NOT be
        # counted, and the skip must be reported rather than silent.
        _write(runs / "wg-a" / "work" / "someagent" / "trials" / "notours.json",
               {"game": "g9", "stack": "rust", "agent": {"cost_usd": 999.0}})
        # Direction 5: a record from ANOTHER HARNESS is counted as a record and excluded
        # from the tokval sums. Its own vendor's USD figure is carried in the record - the
        # row below proves a sum cannot reach it even when it is right there, because the
        # danger is not an absent number, it is a plausible one.
        _write(runs / "wg-c" / "trials" / "g1__rust__t0.json",
               {"game": "g1", "stack": "rust", "trial": 0,
                "harness": {"name": "prime-agent"},
                # `cost_usd` POPULATED, deliberately. The shipped normaliser writes
                # `None` here, and a guard that only works because the other harness
                # behaved is not a guard - it is the same check twice. This row asks
                # whether the SUM can reach a foreign figure that is sitting in the field
                # it reads.
                "agent": {"harness": "prime-agent", "terminal_reason": "completed",
                          "cost_usd": 77.0, "input_tokens": 4573}})

        # Direction 6: a record of OUR harness carrying no `cost_usd`. It passed the
        # harness test, contributed 0.0 to the total and appeared in no exclusion count
        # until pull request 21 — a figure that was never measured, summed as though it
        # were zero, with the note beside the total understating what it left out (#36).
        # `ClaudeHarness.timeout_record` produces exactly this shape.
        _write(runs / "wg-b" / "trials" / "g2__ts__t0.json",
               {"game": "g2", "stack": "ts", "trial": 0,
                "agent": {"terminal_reason": "harness_timeout", "cost_usd": None}})

        # Direction 7: THREE cost shapes that are numbers to a reader and not to an
        # aggregate. `json.loads` produces all three of NaN/Infinity/-Infinity from a
        # stored record, and ONE NaN makes the whole total NaN — an aggregate that is
        # wrong about every record because of one. A bool passes `isinstance(x, int)` and
        # would average as 1.00. Each must be excluded AND counted.
        # Through `_write`, the one fixture writer, rather than a second one alongside it.
        # `json.dumps` emits the bare tokens `NaN`, `Infinity` and `-Infinity` for these
        # floats, so the bytes on disk — and therefore the parse path `load_records`
        # takes — are exactly a stored record's.
        for i, value in enumerate((float("nan"), float("inf"), float("-inf"), True)):
            _write(runs / "wg-a" / "trials" / f"g1__rust__t{i + 5}.json",
                   {"game": "g1", "stack": "rust",
                    "agent": {"terminal_reason": "completed", "cost_usd": value}})

        # Direction 8: A SCENE RECORD. It carries a `game` field like every other record,
        # so the field test alone counts it as a whole-game trial - one population's
        # trial inside another population's figure, which is what `eval/SCENES.md`
        # forbids. Two of them, in their own run directory, with a distinct cost so the
        # sums can be told apart by a number and not only by a count.
        for i in range(2):
            _write(runs / "wg-scene" / "trials" / f"s1_parallax__ts__t{i}.json",
                   {"game": "s1_parallax", "task_class": "scene", "stack": "ts",
                    "trial": i,
                    "agent": {"cost_usd": 20.0, "terminal_reason": "completed"}})

        c = census(runs)
        wg, sc, tree, scn = (c["wholegame"], c["specchange"], c["tree"], c["scene"])

        # Direction 8c: A CLASS THIS CENSUS DOES NOT PARTITION. Not the absent case and
        # not the scene case - a present value nobody here recognises, which a
        # `== "scene" else "game"` test folds into the bake-off figure in silence. It is
        # written into its OWN tree, so the census above is measured over the corpus the
        # rows below state.
        with tempfile.TemporaryDirectory() as tmp2:
            other = Path(tmp2) / "runs"
            _write(other / "wg-x" / "trials" / "c1__ts__t0.json",
                   {"game": "c1_cutscene", "task_class": "cutscene", "stack": "ts",
                    "agent": {"cost_usd": 5.0, "terminal_reason": "completed"}})
            try:
                census(other)
                failures.append("a task_class nobody partitions was accepted, and its "
                                "record landed in a population it may not belong to")
            except CensusError as exc:
                check("the refusal names the file",
                      "c1__ts__t0.json" in str(exc), True)
                check("and names the class it could not place",
                      "'cutscene'" in str(exc), True)

        # Direction 8d: `"task_class": null` is a PRESENT value, not an absence.
        # `record.get(KEY)` answers `None` to both, so the default that reads an absent
        # field as `game` reads a null one as `game` too - a record that has the field
        # and did not say what it holds, inside the published bake-off figure.
        with tempfile.TemporaryDirectory() as tmp3:
            nulled = Path(tmp3) / "runs"
            _write(nulled / "wg-n" / "trials" / "n1__ts__t0.json",
                   {"game": "g1", "task_class": None, "stack": "ts",
                    "agent": {"cost_usd": 5.0, "terminal_reason": "completed"}})
            try:
                census(nulled)
                failures.append("an explicit `task_class: null` was read as a game - "
                                "`.get(KEY)` cannot tell it from an absent field")
            except CensusError:
                pass
        check("an ABSENT task_class still reads as a game",
              task_class_of({"game": "g1_pong"}), "game")
        check("wholegame.trial_records", wg["trial_records"], 9)
        check("wholegame.run_directories", wg["run_directories"], 3)
        check("wholegame.games", wg["games"], {"g1": 7, "g2": 2})
        check("wholegame.stacks", wg["stacks"], {"rust": 7, "ts": 2})
        check("wholegame.cells", wg["cells"], 4)
        check("wholegame.terminal_reason", wg["terminal_reason"],
              {"absent": 1, "api_error": 1, "completed": 6, "harness_timeout": 1})
        check("wholegame.agent_cost_usd", wg["agent_cost_usd"], 6.0)
        # Direction 5, both halves: the other harness's record is COUNTED as a record and
        # its vendor USD reaches no total. A partition that silently dropped the record
        # and a sum that silently included 77.0 are both wrong, and only asking for both
        # numbers separates them.
        check("wholegame.harness", wg["harness"], {"claude": 8, "prime-agent": 1})
        # 6 unpriced for 3 different reasons — a foreign harness, our own harness with no
        # readable figure, and 4 figures that are numbers to a reader but not to an
        # aggregate. One counter, because the question a reader asks of the note is "how
        # many records is this total NOT over".
        check("wholegame.cost_unpriced_records", wg["cost_unpriced_records"], 6)
        # THE TOTAL IS UNMOVED AND STILL FINITE. A single NaN admitted here would make it
        # NaN, and `6.0 != nan` would be the only way anyone found out.
        check("no unusable figure reached the total", wg["agent_cost_usd"], 6.0)
        check("the total is finite", math.isfinite(wg["agent_cost_usd"]), True)
        check("tree.harness", tree["harness"], {"claude": 12, "prime-agent": 1})
        # A record whose two provenance fields DISAGREE is neither of them: it is excluded
        # from every priced sum by the same test that excludes a foreign harness, and it
        # shows up in the partition where a reader cannot miss it. Picking one silently is
        # what must not happen — the record would land in the tokval sum on the strength
        # of a field the other one contradicts.
        check("a conflicting record is neither harness",
              harness_of({"agent": {"harness": "claude"},
                          "harness": {"name": "prime-agent"}}),
              "conflict:claude|prime-agent")
        check("and it is therefore unpriced",
              _priced({"agent": {"harness": "claude", "cost_usd": 5.0},
                       "harness": {"name": "prime-agent"}}), False)
        check("prime-agent vendor USD reached no total",
              77.0 not in (wg["agent_cost_usd"], tree["agent_cost_usd"],
                           sc["agent_cost_usd"]), True)
        check("an unstamped record is read as claude",
              harness_of({"agent": {"cost_usd": 1.0}}), "claude")
        # The spec-change records must NOT be counted as whole-game, and must be counted
        # — including the one nested inside the archive wrapper.
        # Direction 8, both halves. The scene records are counted as scenes and reach no
        # whole-game figure: not the record count, not the game counter, not the cost.
        # Asking only "is the scene count 2" would pass on an implementation that counted
        # them TWICE, which is the shape that puts a scene inside a published game total.
        check("scene.trial_records", scn["trial_records"], 2)
        check("scene.run_directories", scn["run_directories"], 1)
        check("scene.scenes", scn["scenes"], {"s1_parallax": 2})
        check("scene.agent_cost_usd", scn["agent_cost_usd"], 40.0)
        check("no scene record is in the whole-game count", wg["trial_records"], 9)
        check("no scene id is in the whole-game games counter",
              "s1_parallax" in wg["games"], False)
        check("no scene tokval reached the whole-game total", wg["agent_cost_usd"], 6.0)
        check("the scene run directory is not a whole-game one",
              wg["run_directories"], 3)
        # And the whole TREE still counts every record once - a partition that drops a
        # population is as wrong as one that pools it.
        check("a record with no task_class is read as a game",
              task_class_of({"game": "g1_pong"}), "game")
        check("a scene record is read as a scene",
              task_class_of({"game": "s1_parallax", "task_class": "scene"}), "scene")
        check("specchange.trial_records", sc["trial_records"], 2)
        check("specchange.run_directories", sc["run_directories"], 2)
        check("specchange.agent_cost_usd", sc["agent_cost_usd"], 9.0)
        # The WHOLE TREE still counts every record once: 9 game + 2 scene + 2
        # spec-change. A partition that drops a population is as wrong as one that
        # pools it, and only asking both questions separates the two.
        check("tree.trial_records", tree["trial_records"], 13)
        check("tree.run_directories", tree["run_directories"], 6)
        check("tree.agent_cost_usd", tree["agent_cost_usd"], 55.0)
        check("largest matrix is wg-a", max(
            wg["per_run"].items(), key=lambda kv: kv[1]["records"])[0], "wg-a")
        # The nested run is identified by its path, not by its bare name.
        counted, skipped = trial_paths(runs)
        check("nested run identified by relative path",
              sorted({str(Path(p).parent.parent.relative_to(runs)) for p in counted}),
              ["archive-x/core-y", "core-x", "wg-a", "wg-b", "wg-c", "wg-scene"])
        # 4b, both halves: excluded from the counts AND reported.
        check("agent-authored trials/ skipped", len(skipped), 1)
        check("skip is reported", tree["skipped_agent_authored"], 1)
        check("agent-authored record did not reach the cost total",
              999.0 not in [_cost(d) for _, _, d in load_records(runs)[0]], True)

        # Direction 8, both halves: a record whose provenance is present and unreadable
        # is EXCLUDED from the priced total and VISIBLE in the partition — never quietly
        # inside the claude bucket, which is where the default used to put it.
        _write(runs / "wg-a" / "trials" / "g1__ts__t9.json",
               {"game": "g1", "stack": "ts",
                "agent": {"terminal_reason": "completed", "harness": [],
                          "cost_usd": 500.0}})
        c8 = census(runs)["wholegame"]
        check("a record with unreadable provenance is not claude",
              c8["harness"].get("invalid-provenance"), 1)
        check("and its cost reached no total", c8["agent_cost_usd"], 6.0)

        # Direction 9a: a trial file that is not an object at all. `"agent" in data` is
        # a SUBSTRING test on a string, so this file answers True to it and used to raise
        # `TypeError` naming nothing.
        (runs / "wg-a" / "trials" / "g1__ts__t11.json").write_text('"agent"')
        try:
            census(runs)
            failures.append("a non-object record: returned a census instead of raising")
        except CensusError as exc:
            if "g1__ts__t11.json" not in str(exc):
                failures.append(f"the non-object refusal does not name its file: {exc}")
        (runs / "wg-a" / "trials" / "g1__ts__t11.json").unlink()

        # Direction 9: an `agent` block that is present and is not an object fails by
        # NAME. `_terminal` and `_cost` both call `.get` on it, so this used to end the
        # census with an AttributeError several frames away, naming no file.
        _write(runs / "wg-a" / "trials" / "g1__ts__t10.json",
               {"game": "g1", "stack": "ts", "agent": None})
        try:
            census(runs)
            failures.append("a null `agent` block: returned a census instead of raising")
        except CensusError as exc:
            if "g1__ts__t10.json" not in str(exc):
                failures.append(f"the null-`agent` refusal does not name its file: {exc}")
        (runs / "wg-a" / "trials" / "g1__ts__t10.json").unlink()

        # Direction 3: a record that is malformed must fail loudly, naming its file.
        (runs / "wg-b" / "trials" / "broken.json").write_text("{not json")
        try:
            census(runs)
            failures.append("malformed record: returned a census instead of raising")
        except CensusError as exc:
            if "broken.json" not in str(exc):
                failures.append(f"malformed record: error does not name the file: {exc}")

    for f in failures:
        print(f"FAIL  {f}")
    print(f"census selftest: {'FAILED' if failures else 'ok'} "
          f"({len(failures)} failures)")
    return 1 if failures else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--runs-dir", default=str(DEFAULT_RUNS),
                    help="tree to count over (default: eval/runs/)")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--selftest", action="store_true",
                    help="pin the extraction against a tree with a known answer")
    args = ap.parse_args()

    if args.selftest:
        return selftest()

    try:
        c = census(Path(args.runs_dir).expanduser().resolve())
    except CensusError as exc:
        print(f"census: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(c, indent=2) if args.json else render(c))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
