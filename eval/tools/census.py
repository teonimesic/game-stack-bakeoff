#!/usr/bin/env python3
"""Count what the stored tree actually holds, so no document has to remember.

`README.md`'s opening sentence used to assert "24 whole-game submissions, three games,
four stacks, two independent trials per cell". Every one of those was true of a single
run in August 2026 and none of them was true of the tree; nothing in the repository
produced any of them, so nothing could notice when they stopped being true. This is the
producer. It reports the counts and, with every one, the **population** it counted over —
an aggregate without its scope is unfalsifiable (#113).

Two populations live under `eval/runs/**/trials/*.json` and must never be summed blind:

| population | test | what it is |
|---|---|---|
| whole-game | record has a `game` field | `wholegame.py` submissions — the bake-off |
| spec-change | record has no `game` field | the retired `runner.py` suite (`eval/AGENTS.md`) |

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
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RUNS = ROOT / "eval" / "runs"

# The field whose presence separates the two populations. A whole-game record is written
# by wholegame.py, which always sets it; a spec-change record is written by runner.py,
# which never does.
WHOLEGAME_KEY = "game"

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
        out.append((str(path.parent.parent.relative_to(runs_dir)), path.name, data))
    if not out:
        raise CensusError(f"{runs_dir} holds no **/trials/*.json — refusing to report 0 "
                          f"({len(skipped)} paths skipped as agent-authored)")
    return out, skipped


def _cost(record: dict) -> float:
    return record.get("agent", {}).get("cost_usd") or 0.0


def _terminal(record: dict) -> str:
    return record.get("agent", {}).get("terminal_reason") or "absent"


def census(runs_dir: Path) -> dict:
    records, skipped = load_records(runs_dir)
    wholegame = [r for r in records if WHOLEGAME_KEY in r[2]]
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
        }

    return {
        "read_on": _dt.date.today().isoformat(),
        "runs_dir": str(runs_dir),
        "tree": {
            "trial_records": len(records),
            "run_directories": len({r for r, _, _ in records}),
            "agent_cost_usd": round(sum(_cost(d) for _, _, d in records), 2),
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
            "agent_cost_usd": round(sum(_cost(d) for _, _, d in wholegame), 2),
            "per_run": per_run,
        },
        "specchange": {
            "population": "stored trial records with no `game` field — the retired suite",
            "trial_records": len(specchange),
            "run_directories": len({r for r, _, _ in specchange}),
            "agent_cost_usd": round(sum(_cost(d) for _, _, d in specchange), 2),
        },
    }


def _fmt_counter(counter: dict) -> str:
    return ", ".join(f"{k} {v}" for k, v in counter.items())


def render(c: dict) -> str:
    wg, sc, tree = c["wholegame"], c["specchange"], c["tree"]
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
        f"  agent.cost_usd     ${wg['agent_cost_usd']:,.2f}",
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
        f"SPEC-CHANGE — population: {sc['population']}",
        f"  trial records      {sc['trial_records']}",
        f"  run directories    {sc['run_directories']}",
        f"  agent.cost_usd     ${sc['agent_cost_usd']:,.2f}",
        "",
        "WHOLE TREE — both populations, summed only where a sum is meaningful",
        f"  trial records      {tree['trial_records']} across "
        f"{tree['run_directories']} run directories, found at any depth",
        f"  agent.cost_usd     ${tree['agent_cost_usd']:,.2f}",
        f"  skipped            {tree['skipped_agent_authored']} trials/*.json under "
        f"{'/, '.join(sorted(NOT_A_RUN))}/ — agent-authored, not harness records",
        "",
        "judge-round cost is a different producer: "
        "python3 eval/judge/judge_ledger.py --tree eval/runs/",
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
        #   3 whole-game records over 2 run dirs, 2 games, 2 stacks, 3 cells,
        #   terminal completed 1 / api_error 1 / absent 1, $6.00;
        #   2 spec-change records over 2 run dirs, $9.00 — ONE OF THEM NESTED inside an
        #   archive wrapper, which is the case a one-level glob lost (#126);
        #   tree 5 records, 4 dirs, $15.00, 1 skipped as agent-authored.
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

        c = census(runs)
        wg, sc, tree = c["wholegame"], c["specchange"], c["tree"]
        check("wholegame.trial_records", wg["trial_records"], 3)
        check("wholegame.run_directories", wg["run_directories"], 2)
        check("wholegame.games", wg["games"], {"g1": 2, "g2": 1})
        check("wholegame.stacks", wg["stacks"], {"rust": 2, "ts": 1})
        check("wholegame.cells", wg["cells"], 3)
        check("wholegame.terminal_reason", wg["terminal_reason"],
              {"absent": 1, "api_error": 1, "completed": 1})
        check("wholegame.agent_cost_usd", wg["agent_cost_usd"], 6.0)
        # The spec-change records must NOT be counted as whole-game, and must be counted
        # — including the one nested inside the archive wrapper.
        check("specchange.trial_records", sc["trial_records"], 2)
        check("specchange.run_directories", sc["run_directories"], 2)
        check("specchange.agent_cost_usd", sc["agent_cost_usd"], 9.0)
        check("tree.trial_records", tree["trial_records"], 5)
        check("tree.run_directories", tree["run_directories"], 4)
        check("tree.agent_cost_usd", tree["agent_cost_usd"], 15.0)
        check("largest matrix is wg-a", max(
            wg["per_run"].items(), key=lambda kv: kv[1]["records"])[0], "wg-a")
        # The nested run is identified by its path, not by its bare name.
        counted, skipped = trial_paths(runs)
        check("nested run identified by relative path",
              sorted({str(Path(p).parent.parent.relative_to(runs)) for p in counted}),
              ["archive-x/core-y", "core-x", "wg-a", "wg-b"])
        # 4b, both halves: excluded from the counts AND reported.
        check("agent-authored trials/ skipped", len(skipped), 1)
        check("skip is reported", tree["skipped_agent_authored"], 1)
        check("agent-authored record did not reach the cost total",
              999.0 not in [_cost(d) for _, _, d in load_records(runs)[0]], True)

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
