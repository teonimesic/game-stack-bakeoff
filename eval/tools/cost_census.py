#!/usr/bin/env python3
"""The producer for the cost result: does agent spend separate the four stacks?

`README.md` published this result with **no producer** — the only quantity left in the
file with no way to re-derive it. It cited a finding for the method and a table for the
figures, and `AGENTS.md` names that as the defect rather than a shortfall: *a count with a
producer goes stale for an hour; a count with none goes stale forever*. This is the
producer.

WHAT IT COMPUTES, AND OVER WHAT
-------------------------------
The question is whether the *between-stack* spread in cost is large against the spread
*within a single cell* — two trials of the same game on the same stack, which differ only
in what the agent chose to do. That within-cell spread is the noise floor, and a
between-stack number quoted before its floor is a number that will be believed (#63).

The unit is a **group**: one `(run directory, game)` pair, because a floor is a property
of a population and neither runs nor games may be pooled (`eval/RUNS.md`, `eval/AGENTS.md`
rule 4). A group qualifies only when every stack ran in it, with enough trials per cell to
have a within-cell gap at all, under **one** `terminal_reason`. Per group:

| quantity | how |
|---|---|
| per-stack low / high / spread / gap / mean | over `agent.cost_usd` |
| **within-cell noise floor** | the mean of the per-cell gaps |
| **between-stack range** | max stack mean minus min stack mean |
| **range as a percentage of the floor** | the headline ratio |
| `r(cost, turns)` | Pearson, over the trials carrying `agent.num_turns` |
| widest within-stack turn span | the mechanism: cost is a restatement of turns taken |
| cheapest-to-dearest stack order | a plain read of the stack means, not a test |

THE THING THIS TOOL FOUND ON ITS FIRST RUN
------------------------------------------
`README.md` introduced the ratio as *"on the one measure taken on all four stacks at
once"*. There are **7** such groups in the stored tree, and 42% is the lowest of them; the
seven run 42% to 254%, and in **5 of 7** the between-stack range is **larger** than the
within-cell floor. The figure was reproduced to the cent and its scope was wrong, which is
the failure a producer exists to make visible in one command rather than in a re-derivation
nobody performs.

That sentence read *"6 of 7"* until it was checked against the tool's own output, which is
this docstring committing the error it documents: one group sits at **96%**, below the line,
and eyeballing a rendered table is not running the producer. Any figure here that the tool
prints must be read from the tool.

WHAT WOULD MAKE THIS TOOL LIE
-----------------------------
Every guard below exists because its absence is a plausible in-range answer, not a crash:

- **A cell with one trial has no gap, and must not contribute a gap of $0.00.** That would
  drag the floor down and inflate the ratio — fail-open, in the direction that manufactures
  a difference. Such a group does not qualify, and the reason is printed.
- **A mixed `terminal_reason` population is not one population.** Only the requested reason
  enters; the rest are counted and reported, never silently dropped.
- **A spec-change record has no `game` field** and must never be pooled with a whole-game
  one, exactly as `census.py` partitions them.
- **Zero variance makes Pearson undefined**, and `0.0` is a plausible-looking answer for it.
  It is reported as `undefined`.
- **`agent.num_turns` is absent from some stored records.** `r` is computed over the subset
  that has it, with that subset's own `n` printed beside it, and is refused below n=3.
- **A missing or empty tree exits 2 rather than reporting 0** — an agent worktree has no
  `eval/runs/`, it is gitignored, so the honest answer there is a refusal.
- **A run directory is not always a child of `runs/`** (`eval/AGENTS.md`): the search is
  depth-independent, a run is identified by its path relative to `runs/`, and `trials/`
  directories inside agent-authored trees are skipped and the skip is counted.

IS ANY ONE STACK SYSTEMATICALLY CHEAPEST? `--ordering`
------------------------------------------------------
A separate question from the one above, and the rank table alone cannot answer it. `--ordering`
runs a permutation test on the usage ranks with the **stack labels** permuted *within a
cluster* and held constant across every group in that cluster, so groups sharing a run or a game
are not counted as independent evidence. It reports three units side by side — run, game, and the
connected component of both — because which of them is independent is a judgement and the three
disagree.

**It is exact only while `(k!)**m` stays under `EXACT_ASSIGNMENT_LIMIT`, and the result says
which mode it used.** At today's 4 stacks and 4 clusters that is 331,776, comfortably under. A
fifth stack takes m=4 to 207,360,000 and a fifth run takes k=4 to 7,962,624 — **both above the
limit, and both are recorded re-open conditions**, so the sampled path is what the next widening
of this corpus will select. `exact: false` means the p is a seeded sample of `SAMPLE_DRAWS`
draws; never quote one as an enumeration.

**Read `smallest p this design could return` before reading the p.** With k stacks and m clusters
an unbroken lead has probability `k * (1/k)**m`, whatever the data says. Over the stored tree the
run unit returns 0.0156 and its floor is *also* 0.0156 — the most extreme outcome available, with
no margin — while the component unit's floor is 0.25, so at that unit no outcome could reach 0.05
and the question is unasked rather than answered. `DECISIONS.md` holds the adjudication.

    python3 eval/tools/cost_census.py               # the result, human-readable
    python3 eval/tools/cost_census.py --json        # the same, machine-readable
    python3 eval/tools/cost_census.py --ordering    # the ordering adjudication
    python3 eval/tools/cost_census.py --selftest    # pins the extraction in both directions
"""

from __future__ import annotations

import argparse
import collections
import datetime as _dt
import itertools
import json
import math
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_RUNS = ROOT / "eval" / "runs"

# Presence of this field is what separates a whole-game record from a spec-change one.
# Same test as census.py, deliberately — two spellings of one partition disagree eventually.
WHOLEGAME_KEY = "game"

# Directories holding trees written by a building agent or a toolchain, not by a harness.
NOT_A_RUN = frozenset({"work", "artifacts", "targets"})

# Pearson over fewer than 3 points is not a correlation, it is a line through the points.
MIN_R_POINTS = 3


class CostCensusError(RuntimeError):
    """The tree could not be read. Never downgraded to a result of zero."""


# ------------------------------------------------------------------------------ reading

def trial_paths(runs_dir: Path) -> tuple[list[Path], list[Path]]:
    """(counted, skipped) trial-record paths, found at any depth under runs_dir."""
    counted, skipped = [], []
    for path in sorted(runs_dir.rglob("trials/*.json")):
        stem = path.relative_to(runs_dir).parts[:-2]
        (skipped if NOT_A_RUN.intersection(stem) else counted).append(path)
    return counted, skipped


def load_records(runs_dir: Path) -> tuple[list[tuple[str, Path, dict]], list[Path]]:
    """Every stored trial record as (run path relative to runs_dir, file, parsed), plus skips.

    The file path travels with the record because every downstream refusal has to name it:
    an error that says only "a record has no stack" is a bug report nobody can act on.
    """
    if not runs_dir.is_dir():
        raise CostCensusError(
            f"no runs directory at {runs_dir} (it is gitignored; an agent worktree does "
            f"not have one — read the main checkout)")
    counted, skipped = trial_paths(runs_dir)
    out = []
    for path in counted:
        try:
            data = json.loads(path.read_text())
        except json.JSONDecodeError as exc:
            raise CostCensusError(f"{path}: {exc}") from exc
        out.append((str(path.parent.parent.relative_to(runs_dir)), path, data))
    if not out:
        raise CostCensusError(
            f"{runs_dir} holds no **/trials/*.json — refusing to report 0 "
            f"({len(skipped)} paths skipped as agent-authored)")
    return out, skipped


def _terminal(record: dict) -> str:
    return record.get("agent", {}).get("terminal_reason") or "absent"


# ------------------------------------------------------------------------------ measures

def pearson(xs: list[float], ys: list[float]) -> float | None:
    """Pearson r, or None where it is undefined. Never 0.0 for 'no variance'."""
    n = len(xs)
    if n < MIN_R_POINTS:
        return None
    mx, my = sum(xs) / n, sum(ys) / n
    dx = sum((x - mx) ** 2 for x in xs)
    dy = sum((y - my) ** 2 for y in ys)
    if dx == 0 or dy == 0:
        return None
    # strict=True: a length mismatch here would silently truncate to the shorter series
    # and return a correlation over a population nobody chose.
    return sum((x - mx) * (y - my)
               for x, y in zip(xs, ys, strict=True)) / math.sqrt(dx * dy)


def _stack_row(stack: str, records: list[dict]) -> dict:
    costs = sorted(r["agent"]["cost_usd"] for r in records)
    turns = [r["agent"]["num_turns"] for r in records
             if r.get("agent", {}).get("num_turns") is not None]
    return {
        "stack": stack,
        "n": len(costs),
        "low": costs[0],
        "high": costs[-1],
        "spread": (costs[-1] / costs[0]) if costs[0] else None,
        "gap": costs[-1] - costs[0],
        "mean": sum(costs) / len(costs),
        "turn_low": min(turns) if turns else None,
        "turn_high": max(turns) if turns else None,
        "turn_span": (max(turns) - min(turns)) if turns else None,
    }


def group_result(run: str, game: str, cells: dict[str, list[dict]]) -> dict:
    """The cost result for one (run, game) group. Every cell already has >= 2 trials."""
    rows = [_stack_row(s, cells[s]) for s in sorted(cells)]
    gaps = [r["gap"] for r in rows]
    means = [r["mean"] for r in rows]
    floor = sum(gaps) / len(gaps)
    between = max(means) - min(means)

    flat = [r for recs in cells.values() for r in recs]
    paired = [(r["agent"]["cost_usd"], r["agent"]["num_turns"]) for r in flat
              if r.get("agent", {}).get("num_turns") is not None]
    r_cost_turns = pearson([p[0] for p in paired], [p[1] for p in paired])

    spans = [r for r in rows if r["turn_span"] is not None]
    widest = max(spans, key=lambda r: r["turn_span"]) if spans else None

    return {
        "run": run,
        "game": game,
        "trials": len(flat),
        "stacks": len(cells),
        "per_stack": rows,
        # The floor is the mean of the per-cell gaps. A cell with one trial has no gap and
        # never reaches here — a $0.00 gap would deflate the floor and inflate the ratio.
        "within_cell_floor_usd": floor,
        # How much the per-cell gaps disagree WITHIN this group. This is the quantity #63
        # is about — a floor drawn from one cell can be wrong by this factor — and it is
        # computed inside a group because gap sizes are not comparable across budget-cap
        # regimes. None when the tightest cell is exactly $0.00: the ratio is then a
        # division, not a large number.
        "cell_gap_ratio": (max(gaps) / min(gaps)) if min(gaps) else None,
        "between_stack_range_usd": between,
        "range_pct_of_floor": (100.0 * between / floor) if floor else None,
        # The RATIO is undefined at a zero floor; the COMPARISON is not. A group with a
        # $0.00 floor and a positive range exceeds its floor as completely as a group can,
        # and counting exceedance off the percentage silently dropped exactly those groups
        # — fail-open, in the direction that understates how much the stacks disagree.
        "range_exceeds_floor": between > floor,
        "r_cost_turns": r_cost_turns,
        "r_cost_turns_n": len(paired),
        "widest_turn_span": None if widest is None else {
            "stack": widest["stack"], "low": widest["turn_low"],
            "high": widest["turn_high"], "span": widest["turn_span"]},
        "cheapest_to_dearest": [r["stack"] for r in sorted(rows, key=lambda r: r["mean"])],
    }


# --------------------------------------------------------------------------- validation

def _is_number(value) -> bool:
    """A real, finite number. `bool` is not one, and neither is NaN or Infinity.

    Two traps, both of which pass `isinstance(v, (int, float))`:

    - **`True` is an `int`.** `cost_usd: true` would average as $1.00.
    - **`json.loads` accepts the bare literals `NaN`, `Infinity` and `-Infinity`**, and both
      are `float`. This is the dangerous one, because NaN does not raise and does not stop:
      it propagates through every mean, floor and ratio, and **every comparison against it
      is False** — so `range_exceeds_floor` would come back `False` for a group whose
      numbers are not numbers, which is a silent no rather than a visible error.
    """
    return (not isinstance(value, bool)
            and isinstance(value, (int, float))
            and math.isfinite(value))


def _validate_wholegame(path: Path, d: dict) -> None:
    """Refuse a record that parsed but cannot be grouped, naming the file and the field.

    `main()` catches only `CostCensusError`. Everything checked here otherwise surfaces as
    a traceback — `KeyError`, `AttributeError`, `TypeError` — or, for NaN, as no error at
    all. A measurement tool's answer to bad input is a named refusal, not a stack trace.
    """
    agent = d.get("agent")
    if agent is None or not isinstance(agent, dict):
        raise CostCensusError(
            f"{path}: `agent` is {agent!r}, not an object — nothing can be read from it")

    game = d.get(WHOLEGAME_KEY)
    if not isinstance(game, str) or not game:
        # An unhashable game (a list) is a TypeError on the group key, several frames away.
        raise CostCensusError(
            f"{path}: whole-game record has no usable `game` (got {game!r})")

    stack = d.get("stack")
    if not isinstance(stack, str) or not stack:
        raise CostCensusError(
            f"{path}: whole-game record has no usable `stack` (got {stack!r})")

    cost = agent.get("cost_usd")
    if cost is not None and not _is_number(cost):
        raise CostCensusError(
            f"{path}: `agent.cost_usd` is {cost!r}, which is not a finite number")

    turns = agent.get("num_turns")
    if turns is not None and (isinstance(turns, bool) or not isinstance(turns, int)):
        # A non-integer turn count reaches min()/max() against real ints and raises there.
        raise CostCensusError(
            f"{path}: `agent.num_turns` is {turns!r}, which is not an integer")


# ------------------------------------------------------------------------------- census

def cost_census(runs_dir: Path, terminal_reason: str = "completed",
                min_stacks: int = 4, min_trials_per_cell: int = 2) -> dict:
    # A threshold below 2 cannot define the measure this tool exists to compute, and both
    # are reachable from the CLI. `--min-trials-per-cell 1` admits a cell with no gap and
    # scores it $0.00 — the exact fail-open the thin-cell guard exists to prevent, reachable
    # by a flag; `--min-stacks 1` reports a "between-stack range" over one stack, which is
    # 0.00 by construction and reads as agreement. Refuse before measuring, not after.
    if min_stacks < 2:
        raise CostCensusError(
            f"--min-stacks {min_stacks}: a between-stack range needs at least 2 stacks; "
            f"over 1 it is $0.00 by construction and reads as the stacks agreeing")
    if min_trials_per_cell < 2:
        raise CostCensusError(
            f"--min-trials-per-cell {min_trials_per_cell}: a within-cell gap needs at "
            f"least 2 trials; a 1-trial cell has NO gap, and admitting it as $0.00 "
            f"deflates the floor and inflates the ratio")

    records, skipped = load_records(runs_dir)
    wholegame = []
    for run, path, d in records:
        if WHOLEGAME_KEY not in d:
            continue
        _validate_wholegame(path, d)
        wholegame.append((run, d))

    by_group: dict[tuple[str, str], dict[str, list[dict]]] = collections.defaultdict(
        lambda: collections.defaultdict(list))
    excluded: collections.Counter = collections.Counter()
    for run, d in wholegame:
        if _terminal(d) != terminal_reason:
            excluded[_terminal(d)] += 1
            continue
        if d.get("agent", {}).get("cost_usd") is None:
            excluded["no cost_usd"] += 1
            continue
        by_group[(run, d["game"])][d["stack"]].append(d)

    groups, rejected = [], []
    for (run, game), cells in sorted(by_group.items()):
        thin = sorted(s for s, v in cells.items() if len(v) < min_trials_per_cell)
        if len(cells) < min_stacks or thin:
            why = []
            if len(cells) < min_stacks:
                why.append(f"{len(cells)} of {min_stacks} stacks")
            if thin:
                why.append(f"< {min_trials_per_cell} trials in cell(s): {', '.join(thin)}")
            rejected.append({"run": run, "game": game, "why": "; ".join(why)})
            continue
        groups.append(group_result(run, game, cells))

    ratios = [g["range_pct_of_floor"] for g in groups
              if g["range_pct_of_floor"] is not None]
    gap_ratios = [g["cell_gap_ratio"] for g in groups if g["cell_gap_ratio"] is not None]
    spreads = [r["spread"] for g in groups for r in g["per_stack"]
               if r["spread"] is not None]
    rs = [g["r_cost_turns"] for g in groups if g["r_cost_turns"] is not None]
    spans = [g["widest_turn_span"] for g in groups if g["widest_turn_span"]]
    ranks: dict[str, list[int]] = collections.defaultdict(list)
    for g in groups:
        for i, stack in enumerate(g["cheapest_to_dearest"]):
            ranks[stack].append(i + 1)
    # NO MEAN RANK. The groups span 4 runs and 4 games under different budget-cap regimes
    # and are not a population anyone has shown homogeneous (AGENTS.md rule 4), and a mean
    # is the shape that gets re-quoted with its caveat stripped. The rank VECTOR and a count
    # of firsts carry the same information, cannot be mistaken for a statistic, and are what
    # the adjudication this feeds actually needs.
    rank_vectors = {s: v for s, v in sorted(ranks.items())}
    times_cheapest = {s: sum(1 for r in v if r == 1) for s, v in rank_vectors.items()}

    return {
        "read_on": _dt.date.today().isoformat(),
        "runs_dir": str(runs_dir),
        "population": (
            f"stored whole-game trial records with terminal_reason={terminal_reason}, "
            f"grouped by (run directory, game); a group qualifies with >= {min_stacks} "
            f"stacks and >= {min_trials_per_cell} trials in every cell"),
        "terminal_reason": terminal_reason,
        "min_stacks": min_stacks,
        "min_trials_per_cell": min_trials_per_cell,
        "wholegame_records": len(wholegame),
        "excluded_by_terminal_reason": dict(sorted(excluded.items())),
        "skipped_agent_authored": len(skipped),
        "groups": groups,
        "rejected_groups": rejected,
        "across_groups": {
            "n_groups": len(groups),
            "range_pct_of_floor_min": min(ratios) if ratios else None,
            "range_pct_of_floor_max": max(ratios) if ratios else None,
            # Counted off the COMPARISON, never off the percentage: a zero-floor group has
            # no percentage and still exceeds its floor.
            "groups_where_range_exceeds_floor": sum(
                1 for g in groups if g["range_exceeds_floor"]),
            "r_cost_turns_min": min(rs) if rs else None,
            "r_cost_turns_max": max(rs) if rs else None,
            "widest_turn_span_anywhere": max((s["span"] for s in spans), default=None),
            "cells": len(spreads),
            "cell_spread_min": min(spreads) if spreads else None,
            "cell_spread_max": max(spreads) if spreads else None,
            "cell_gap_ratio_max": max(gap_ratios) if gap_ratios else None,
            "cost_rank_per_group": rank_vectors,
            "times_cheapest": times_cheapest,
        },
    }


# -------------------------------------------------------------- ordering adjudication

# The level the adjudication is read at, named once. A threshold spelled in two places is
# a threshold that will eventually disagree with itself.
ALPHA = 0.05

# Above this many label assignments the exact enumeration is refused in favour of a seeded
# sample, and the result says which one it is. A sampled p reported as exact is a number
# that gets acted on. 4 stacks over 4 clusters is 331,776, comfortably under.
EXACT_ASSIGNMENT_LIMIT = 2_000_000

# Sized from the precision the answer needs, not picked round. The only decision taken from
# a p here is against ALPHA, and the binomial standard error of a sampled p at 0.05 is
# sqrt(0.05 * 0.95 / n) — 0.00097 at 50,000 draws, which is 50x finer than the distance
# between the attainable p-values this design produces (0.0156, 0.0625, 0.25). It was
# 200,000 for no stated reason, at 4x the cost, and the sampled path is walked m+1 times per
# clustering because the fragility floor re-runs it with one cluster dropped.
SAMPLE_DRAWS = 50_000
SAMPLE_SEED = 20260823


def group_ranks(group: dict) -> dict[str, float]:
    """Usage rank of each stack in one group, 1 = lowest stack mean. Ties share the average.

    Ties are not defensive padding. Two stacks with equal means would otherwise be ordered
    by the sort's stability, handing one of them rank 1 — a lead manufactured by the order
    of a list, in the exact quantity this adjudication is about.
    """
    ordered = sorted((r["mean"], r["stack"]) for r in group["per_stack"])
    ranks: dict[str, float] = {}
    i = 0
    while i < len(ordered):
        j = i
        while j + 1 < len(ordered) and ordered[j + 1][0] == ordered[i][0]:
            j += 1
        shared = (i + j) / 2.0 + 1.0
        for t in range(i, j + 1):
            ranks[ordered[t][1]] = shared
        i = j + 1
    return ranks


def _cluster_by(groups: list[dict], key: str) -> list[tuple[str, list[int]]]:
    out: dict[str, list[int]] = collections.defaultdict(list)
    for i, g in enumerate(groups):
        out[g[key]].append(i)
    return sorted(out.items())


def _cluster_components(groups: list[dict]) -> list[tuple[str, list[int]]]:
    """Connected components of "shares a run OR shares a game".

    The reason this clustering exists: treating the RUN as the independent unit assumes the
    runs are independent of one another, and they are not — the same games recur across
    runs, so a stack that is cheap on one game contributes the same evidence twice. This
    merges both channels and is the most conservative unit the stored tree admits.
    """
    parent = list(range(len(groups)))

    def find(a: int) -> int:
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    for key in ("run", "game"):
        for _, idx in _cluster_by(groups, key):
            for other in idx[1:]:
                ra, rb = find(idx[0]), find(other)
                if ra != rb:
                    parent[ra] = rb

    comp: dict[int, list[int]] = collections.defaultdict(list)
    for i in range(len(groups)):
        comp[find(i)].append(i)
    return [(f"component {n}", idx)
            for n, (_, idx) in enumerate(sorted(comp.items(), key=lambda kv: kv[1]), 1)]


# Three units, reported side by side and never reduced to one, because which of them is
# independent is a judgement and the three do not agree. `DECISIONS.md` records which one
# the published adjudication is read from, and why.
CLUSTERINGS = {
    "run": ("run directory", lambda gs: _cluster_by(gs, "run")),
    "game": ("game", lambda gs: _cluster_by(gs, "game")),
    "run+game": ("connected component of run and game", _cluster_components),
}


def _permutation_test(cols: list[list[float]], obs_leader: float,
                      k: int) -> dict:
    """Exact (or seeded-sampled) permutation over stack labels, permuted WITHIN a cluster.

    `cols[c][j]` is stack `j`'s summed rank over every group in cluster `c`. A label
    assignment picks one permutation per cluster and holds it across every group in that
    cluster, which is what preserves the dependence between groups that share a run or a
    game instead of counting them as independent evidence.

    Three counts come back, and the third is the one that decides anything:

    - `p_named`   — the leader's rank sum, had the leader been named in advance. It was not.
    - `p_any`     — the smallest rank sum any stack reaches. This is the honest one: the
                    leading stack was chosen because it looked lowest.
    - `p_floor`   — `p_any` at the smallest rank sum ANY assignment can produce. It is the
                    best this design could ever return, whatever the data said, and a
                    `p_any` equal to it is a test that returned its most extreme outcome
                    with no margin left.
    """
    # DECIDE THE MODE FROM ARITHMETIC, BEFORE ALLOCATING ANYTHING. The exact path
    # materialises k! vectors per cluster; at k=10 that is 3,628,800 of them, so a
    # limit checked after the build is a limit the process can run out of memory
    # reaching. The count is a factorial power — compute it, do not enumerate to find it.
    total = math.factorial(k) ** len(cols)
    exact = total <= EXACT_ASSIGNMENT_LIMIT

    # Permutations are chosen independently per cluster, so the smallest total any single
    # stack can be driven to is the sum of each cluster's smallest column. Computed in
    # closed form rather than read off the enumeration, so the two disagree if either is
    # wrong.
    attainable_min = sum(min(col) for col in cols)
    leader_idx = min(range(k), key=lambda j: sum(col[j] for col in cols))

    def relabel(perm, col: list[float]) -> tuple[float, ...]:
        """One cluster's column sums under one relabelling: column j goes to stack p[j]."""
        v = [0.0] * k
        for j in range(k):
            v[perm[j]] += col[j]
        return tuple(v)

    if exact:
        perms = list(itertools.permutations(range(k)))
        per_cluster = [[relabel(p, col) for p in perms] for col in cols]
        draws = itertools.product(*per_cluster)
        n_draws = total
    else:
        # Lazy: one shuffled label order per cluster per draw, nothing materialised.
        rng = random.Random(SAMPLE_SEED)
        n_draws = SAMPLE_DRAWS
        order = list(range(k))

        def sampled():
            for _ in range(n_draws):
                combo = []
                for col in cols:
                    rng.shuffle(order)
                    combo.append(relabel(order, col))
                yield combo

        draws = sampled()
    n_named = n_any = n_floor = 0
    for combo in draws:
        v = [0.0] * k
        for c in combo:
            for j in range(k):
                v[j] += c[j]
        if v[leader_idx] <= obs_leader:
            n_named += 1
        smallest = min(v)
        if smallest <= obs_leader:
            n_any += 1
        if smallest <= attainable_min:
            n_floor += 1

    return {
        "assignments": total,
        "exact": exact,
        "draws": n_draws,
        "attainable_min_rank_sum": attainable_min,
        "p_named": n_named / n_draws,
        "p_named_count": n_named,
        "p_any": n_any / n_draws,
        "p_any_count": n_any,
        "p_floor": n_floor / n_draws,
        "at_the_extreme": obs_leader <= attainable_min,
    }


def _floor_dropping_one(cols: list[list[float]], k: int) -> float | None:
    """The smallest post-hoc p the design could return with ONE cluster removed — the worst
    case over which one.

    This is the fragility measure, and it is a different question from `p_floor`. A result
    that clears alpha only with every cluster present is one no subset of the evidence
    could have produced, which is not corroboration. It is computed rather than taken from
    `k * (1/k)**(m-1)`, because that closed form assumes each cluster has a *unique*
    smallest column and ties break it.
    """
    if len(cols) < 2:
        return None
    worst = 0.0
    for i in range(len(cols)):
        sub = cols[:i] + cols[i + 1:]
        worst = max(worst, _permutation_test(sub, sum(min(c) for c in sub), k)["p_floor"])
    return worst


def ordering_test(census: dict) -> dict:
    """Does any stack use systematically fewer tokens than the others?

    The null is that stack LABELS are exchangeable within a cluster: whatever a group's
    four cells cost, which stack got which is arbitrary. Rejecting it is the only sense in
    which "the stacks are ordered" is a claim rather than a reading of a table.

    `cost_usd` is a list-price valuation of token counts on a subscription account (#159),
    so every quantity here is token usage. Nothing was spent per trial.
    """
    groups = census["groups"]
    if not groups:
        raise CostCensusError(
            "no qualifying groups — there is nothing to adjudicate, and reporting a "
            "p-value over an empty population would be a number with no measurement "
            "under it")

    stack_sets = {tuple(sorted(r["stack"] for r in g["per_stack"])) for g in groups}
    if len(stack_sets) != 1:
        raise CostCensusError(
            f"the groups do not carry one stack set ({sorted(stack_sets)}) — permuting "
            f"stack labels across groups that hold different stacks is undefined")
    stacks = list(stack_sets.pop())
    k = len(stacks)

    ranks = [group_ranks(g) for g in groups]
    observed = {s: sum(r[s] for r in ranks) for s in stacks}
    leader = min(stacks, key=lambda s: observed[s])

    results = []
    for name, (described, build) in CLUSTERINGS.items():
        clusters = build(groups)
        cols = [[sum(ranks[i][s] for i in idx) for s in stacks] for _, idx in clusters]
        test = _permutation_test(cols, observed[leader], k)
        results.append({
            "clustering": name,
            "unit": described,
            "n_clusters": len(clusters),
            "clusters": [{"label": label,
                          "groups": [f"{groups[i]['run']} / {groups[i]['game']}"
                                     for i in idx]}
                         for label, idx in clusters],
            **test,
            "resolves": test["p_any"] < ALPHA,
            "design_can_resolve": test["p_floor"] < ALPHA,
            "p_floor_dropping_one_cluster": _floor_dropping_one(cols, k),
        })

    # How big the lead is where it exists, against the group's own within-cell noise floor.
    # A consistent ordering and a lead that beats the noise are different claims, and the
    # permutation test above can only speak to the first.
    margins = []
    for g, r in zip(groups, ranks, strict=True):
        means = sorted((row["mean"], row["stack"]) for row in g["per_stack"])
        floor = g["within_cell_floor_usd"]
        # Every field is present on every row, including the ones only a leading group
        # fills in. A key that appears conditionally is a KeyError in whatever reads it,
        # several frames from the group that did not have it.
        row = {"run": g["run"], "game": g["game"], "leader_rank": r[leader],
               "cheapest": means[0][1], "leads": r[leader] == 1.0, "runner_up": None,
               "margin_usd": None, "floor_usd": floor, "margin_pct_of_floor": None,
               "margin_exceeds_floor": None}
        # The RANK decides who leads, never `means[0]`. `means` sorts on (mean, stack), so
        # two stacks at the same mean are separated by their NAME — and the one that wins
        # that tiebreak was recorded as leading the group by $0.00, while `times_cheapest`
        # counted the same group for nobody. One tied group made the tool say "leads 1 of 1"
        # and "cheapest in 0 of 1" at once.
        if row["leads"] and len(means) > 1:
            margin = means[1][0] - means[0][0]
            row.update(margin_usd=margin, runner_up=means[1][1],
                       margin_pct_of_floor=(100.0 * margin / floor) if floor else None,
                       margin_exceeds_floor=margin > floor)
        margins.append(row)

    return {
        "alpha": ALPHA,
        "stacks": stacks,
        "n_groups": len(groups),
        "rank_sum_per_stack": observed,
        "null_expectation_rank_sum": len(groups) * (k + 1) / 2.0,
        "leader": leader,
        "times_cheapest": {s: sum(1 for r in ranks if r[s] == 1.0) for s in stacks},
        "clusterings": results,
        "leader_margins": margins,
        "margins_exceeding_floor": sum(1 for m in margins if m["margin_exceeds_floor"]),
        "groups_led": sum(1 for m in margins if m["leads"]),
    }


# ------------------------------------------------------------------------------ render

def _fmt_r(value: float | None) -> str:
    return "undefined" if value is None else f"{value:.3f}"


def _fmt(value: float | None, spec: str, suffix: str = "") -> str:
    """Format a value that may legitimately be undefined.

    Every aggregate here can be `None` on a real population — a zero floor gives no ratio
    and no cell-gap ratio, and a population where every cell's cheapest trial cost $0.00
    gives no spread. Formatting `None` with `:.0f` is a TypeError, so the DATA path would
    be correct and the tool would still die on the way to the terminal.
    """
    return "undefined" if value is None else f"{value:{spec}}{suffix}"


def _fmt_interval(low: float | None, high: float | None, spec: str, suffix: str = "") -> str:
    if low is None or high is None:
        return "undefined"
    return f"{_fmt(low, spec, suffix)} - {_fmt(high, spec, suffix)}"


def render(c: dict) -> str:
    lines = [
        f"read on {c['read_on']} from {c['runs_dir']}",
        f"population: {c['population']}",
        f"  whole-game trial records read   {c['wholegame_records']}",
        "  excluded, other terminal_reason "
        + (", ".join(f"{k} {v}" for k, v in c["excluded_by_terminal_reason"].items())
           or "none"),
        f"  skipped, agent-authored trees   {c['skipped_agent_authored']}",
    ]
    for r in c["rejected_groups"]:
        lines.append(f"  not a qualifying group          {r['run']} / {r['game']} "
                     f"({r['why']})")

    for g in c["groups"]:
        lines += [
            "",
            f"GROUP  {g['run']} / {g['game']}   "
            f"{g['trials']} trials, {g['stacks']} stacks, "
            f"terminal_reason={c['terminal_reason']}",
            "  stack   n      low     high   spread      gap     mean    turns",
        ]
        for row in g["per_stack"]:
            turns = ("       -" if row["turn_low"] is None
                     else f"{row['turn_low']:4d}-{row['turn_high']:<4d}")
            spread = "     -" if row["spread"] is None else f"{row['spread']:5.2f}x"
            lines.append(
                f"  {row['stack']:6} {row['n']:<2} "
                f"{row['low']:8.2f} {row['high']:8.2f} {spread:>8} "
                f"{row['gap']:8.2f} {row['mean']:8.2f}  {turns}")
        ratio = g["range_pct_of_floor"]
        lines += [
            f"  within-cell noise floor (mean of {g['stacks']} per-cell gaps)"
            f"   ${g['within_cell_floor_usd']:8.2f}   <- read this first",
            f"  between-stack range (max stack mean - min stack mean)"
            f"   ${g['between_stack_range_usd']:8.2f}",
            f"  range as a percentage of the floor"
            f"                       {_fmt(ratio, '8.0f', '%'):>9}"
            # The MARKER comes off the comparison, not the percentage, so a zero-floor
            # group is still marked as exceeding its floor.
            + ("   (range EXCEEDS the floor)" if g["range_exceeds_floor"] else ""),
            f"  r(cost, turns)                                           "
            f"{_fmt_r(g['r_cost_turns']):>9}   (n={g['r_cost_turns_n']})",
            "  widest cell gap over tightest, inside this group          "
            + ("undefined ($0.00 tightest cell)" if g["cell_gap_ratio"] is None
               else f"{_fmt(g['cell_gap_ratio'], '.1f', 'x')}   <- how wrong a one-cell "
                    "floor could be here"),
        ]
        if g["widest_turn_span"]:
            w = g["widest_turn_span"]
            lines.append(f"  widest turn span inside one stack's cell                 "
                         f"{w['low']}-{w['high']} ({w['span']} turns, {w['stack']})")
        lines.append(f"  cheapest -> dearest by stack mean                         "
                     f"{', '.join(g['cheapest_to_dearest'])}")

    a = c["across_groups"]
    lines += ["", f"ACROSS {a['n_groups']} QUALIFYING GROUP(S) — reported side by side, "
                  f"never pooled (eval/RUNS.md)"]
    if a["n_groups"]:
        lines += [
            f"  range as a percentage of the floor   "
            f"{_fmt_interval(a['range_pct_of_floor_min'], a['range_pct_of_floor_max'], '.0f', '%')}"
            f"; the range EXCEEDS the floor in {a['groups_where_range_exceeds_floor']} "
            f"of {a['n_groups']}",
            f"  r(cost, turns)                       "
            f"{_fmt_r(a['r_cost_turns_min'])} - {_fmt_r(a['r_cost_turns_max'])}",
            f"  widest turn span in any one cell     "
            f"{a['widest_turn_span_anywhere']} turns",
            f"  per-cell spread, over {a['cells']} cells       "
            f"{_fmt_interval(a['cell_spread_min'], a['cell_spread_max'], '.2f', 'x')}",
            f"  worst one-cell floor error           "
            f"{_fmt(a['cell_gap_ratio_max'], '.1f', 'x')}, inside a single group "
            f"(never compared across groups — gap sizes are regime-bound)",
            "",
            "  cost rank per group (1 = cheapest in that group), in group order:",
        ]
        lines += [f"    {s:6} {v}   cheapest in {a['times_cheapest'][s]} of {a['n_groups']}"
                  for s, v in a["cost_rank_per_group"].items()]
        lines += [
            "",
            "  THOSE ROWS ARE A READ OF THE STACK MEANS, NOT A TEST, and there is "
            "deliberately no mean",
            "  rank: the groups span several runs and games under different budget caps and "
            "are not a",
            "  population anyone has shown homogeneous, so a mean over them would be the one "
            "number here",
            "  that could be re-quoted as a result. Every cell is n=2.",
        ]
    return "\n".join(lines)


def render_ordering(c: dict) -> str:
    o = c["ordering"]
    k = len(o["stacks"])
    lines = [
        f"read on {c['read_on']} from {c['runs_dir']}",
        f"population: {c['population']}",
        "",
        "THE QUESTION: does any stack use systematically fewer tokens than the others, or",
        "is the ordering a reading of a table? cost_usd is a list-price valuation of token",
        "counts on a subscription account (#159) — nothing was spent per trial.",
        "",
        f"  usage rank summed over {o['n_groups']} groups "
        f"(null expectation {o['null_expectation_rank_sum']:.1f}, "
        f"{o['n_groups']} = an unbroken lead):",
    ]
    for s in o["stacks"]:
        lines.append(f"    {s:6} {o['rank_sum_per_stack'][s]:6.1f}   cheapest in "
                     f"{o['times_cheapest'][s]} of {o['n_groups']}")
    lines += [
        f"  leading stack (chosen POST HOC, because it looked lowest): {o['leader']}",
        "",
        "THE TEST: stack labels are permuted WITHIN a cluster and held constant across every",
        "group in it, so groups that share a cluster are not counted as independent evidence.",
    ]
    for t in o["clusterings"]:
        mode = (f"exact over {t['assignments']} assignments" if t["exact"]
                else f"seeded sample, {t['draws']} draws of {t['assignments']}")
        lines += [
            "",
            f"  UNIT = {t['unit']}  ({t['n_clusters']} clusters, {mode})",
        ]
        for cl in t["clusters"]:
            lines.append(f"    {cl['label']:34} {len(cl['groups'])} group(s)")
        lines += [
            f"    p, had {o['leader']} been named in advance    {t['p_named']:.4f}"
            f"   ({t['p_named_count']}/{t['draws']})",
            f"    p, post-hoc-safe (any stack leading) {t['p_any']:.4f}"
            f"   ({t['p_any_count']}/{t['draws']})   "
            + ("< alpha" if t["resolves"] else ">= alpha"),
            f"    smallest p this design could return  {t['p_floor']:.4f}"
            + ("   <- the observed p IS the floor: the most extreme outcome available, "
               "no margin" if t["at_the_extreme"] else ""),
            f"    ... and with any one cluster dropped {_fmt(t['p_floor_dropping_one_cluster'], '.4f')}"
            + ("   <- no subset of the clusters could have reached alpha"
               if (t["p_floor_dropping_one_cluster"] is not None
                   and t["p_floor_dropping_one_cluster"] >= o["alpha"]) else ""),
        ]
        if not t["design_can_resolve"]:
            lines.append(f"    ** at this unit NO outcome could have reached alpha="
                         f"{o['alpha']}. The question is not answered no; it is unasked. **")
    lines += [
        "",
        f"HOW BIG THE LEAD IS, where {o['leader']} leads at all — against that group's own",
        "within-cell noise floor. A consistent ordering and a lead that beats the noise are",
        "different claims, and the permutation test above speaks only to the first.",
    ]
    for m in o["leader_margins"]:
        tag = f"{m['run']} / {m['game']}"
        if m["margin_usd"] is None:
            lines.append(f"    {tag:48} {o['leader']} is rank {m['leader_rank']:.1f} "
                         f"(cheapest: {m['cheapest']})")
        else:
            lines.append(
                f"    {tag:48} leads {m['runner_up']:6} by {m['margin_usd']:6.2f}, "
                f"floor {m['floor_usd']:6.2f} -> "
                f"{_fmt(m['margin_pct_of_floor'], '5.1f', '%')} of floor "
                + ("(ABOVE floor)" if m["margin_exceeds_floor"] else "(below floor)"))
    lines += [
        f"    {o['leader']} leads {o['groups_led']} of {o['n_groups']} groups, and its lead "
        f"beats that group's own noise floor in {o['margins_exceeding_floor']} of "
        f"{o['groups_led']}.",
        "",
        "WHAT THIS IS NOT. Rejecting label exchangeability says the ordering is unlikely to "
        "be",
        f"an accident of which arm drew which trials. It does not say the gap is large, it "
        f"does not",
        f"attribute it to the stack rather than to the starter or the task, and with {k} "
        f"stacks the",
        "p-values above are coarse: read the floor line before reading the p.",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------- selftest

def _write(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj))


def _round(value, digits: int):
    """round() that survives a None, so a broken build reports it instead of raising."""
    return None if value is None else round(value, digits)


def _rec(game: str, stack: str, cost: float, turns: int | None = None,
         reason: str = "completed") -> dict:
    agent: dict = {"cost_usd": cost, "terminal_reason": reason}
    if turns is not None:
        agent["num_turns"] = turns
    return {"game": game, "stack": stack, "agent": agent}


def selftest() -> int:  # noqa: PLR0915 - one pin per line is the point
    """Pin the extraction on a tree whose answer is stated before it is measured."""
    import shutil
    import tempfile

    failures: list[str] = []

    def check(label: str, got, want) -> None:
        if got != want:
            failures.append(f"{label}: got {got!r}, want {want!r}")

    # Every expected value below is written as a LITERAL, never derived by calling the code
    # under test — a control that imports its expectation from its subject is not a control
    # (AGENTS.md rule 12). `measure` exists only so that a broken build reports a NAMED
    # failure rather than a traceback: three of the eleven mutants this was pinned against
    # crashed the selftest instead of reddening a row, and a traceback is a worse diagnosis
    # than a FAIL line even though both exit non-zero.
    EMPTY: dict = {"groups": [], "rejected_groups": [], "excluded_by_terminal_reason": {},
                   "wholegame_records": None, "skipped_agent_authored": None,
                   "across_groups": {"groups_where_range_exceeds_floor": None}}

    # Every per-group field this selftest reads. Written out rather than derived from a
    # result, so dropping one from the producer is a named failure and not a KeyError.
    EXPECTED_GROUP_FIELDS = (
        "run", "game", "trials", "stacks", "per_stack", "within_cell_floor_usd",
        "cell_gap_ratio", "between_stack_range_usd", "range_pct_of_floor",
        "range_exceeds_floor", "r_cost_turns", "r_cost_turns_n", "widest_turn_span",
        "cheapest_to_dearest")

    def measure(label: str, runs_dir: Path, **kw) -> dict:
        try:
            return cost_census(runs_dir, **kw)
        except Exception as exc:  # noqa: BLE001 - anything raised here is a failure
            failures.append(f"{label}: raised {type(exc).__name__}: {exc}")
            return EMPTY

    class _Absent(dict):
        """A group that could not be produced. Every field reads as None, and reading one
        is not an error — the failure was already recorded where the group went missing.
        A fixed placeholder dict was tried and drifted the moment a field was added: a
        mutant then died on a KeyError instead of reddening its row."""

        def __missing__(self, key):
            return None

    # Every across-groups field this selftest reads. Same purpose as EXPECTED_GROUP_FIELDS,
    # and it exists because the group-level guard alone was not enough: the shipped mutant
    # suite caught two mutants dying on `across_groups["cost_rank_per_group"]` rather than
    # reddening a row, which is the drift the group-level guard was added for, one level up.
    EXPECTED_ACROSS_FIELDS = (
        "n_groups", "range_pct_of_floor_min", "range_pct_of_floor_max",
        "groups_where_range_exceeds_floor", "r_cost_turns_min", "r_cost_turns_max",
        "widest_turn_span_anywhere", "cells", "cell_spread_min", "cell_spread_max",
        "cell_gap_ratio_max", "cost_rank_per_group", "times_cheapest")

    def across(label: str, result: dict) -> dict:
        a = result.get("across_groups", {})
        missing = [k for k in EXPECTED_ACROSS_FIELDS if k not in a]
        if missing:
            failures.append(f"{label}: across_groups is missing field(s) {missing}")
            return _Absent(a)
        return a

    def only_group(label: str, result: dict) -> dict:
        groups = result["groups"]
        if len(groups) != 1:
            failures.append(f"{label}: expected exactly 1 group, got {len(groups)}")
            return _Absent(per_stack=[])
        group = groups[0]
        # A field this selftest names and the producer does not emit is a drift between
        # the two, and it must be a NAMED failure rather than a KeyError.
        missing = [k for k in EXPECTED_GROUP_FIELDS if k not in group]
        if missing:
            failures.append(f"{label}: group is missing field(s) {missing}")
            return _Absent(group, per_stack=group.get("per_stack", []))
        return group

    with tempfile.TemporaryDirectory() as tmp:
        runs = Path(tmp) / "runs"

        # Direction 1: a missing tree refuses rather than reporting a result of zero.
        try:
            cost_census(runs)
            failures.append("missing runs dir: returned a result instead of raising")
        except CostCensusError:
            pass

        # Direction 2: an existing but empty tree also refuses.
        runs.mkdir(parents=True)
        try:
            cost_census(runs)
            failures.append("empty runs dir: returned a result instead of raising")
        except CostCensusError:
            pass

        # ---- THE KNOWN-ANSWER GROUP, stated before it is measured.
        # gX on run-a: 4 stacks x 2 completed trials.
        #   costs  ts 10,20  unity 30,34  godot 40,50  rust 60,80
        #   gaps       10        4            10          20   -> floor 11.00
        #   means      15        32           45          70   -> range 55.00
        #   ratio 500%; cheapest->dearest ts, unity, godot, rust
        #   turns rise with cost monotonically -> r = 1.000 exactly; widest span rust 40
        costs = {"ts": (10.0, 20.0), "unity": (30.0, 34.0),
                 "godot": (40.0, 50.0), "rust": (60.0, 80.0)}
        turns = {"ts": (100, 120), "unity": (140, 148),
                 "godot": (160, 180), "rust": (200, 240)}
        for stack, (c0, c1) in costs.items():
            t0, t1 = turns[stack]
            _write(runs / "run-a" / "trials" / f"gX__{stack}__t0.json",
                   _rec("gX", stack, c0, t0))
            _write(runs / "run-a" / "trials" / f"gX__{stack}__t1.json",
                   _rec("gX", stack, c1, t1))

        # Direction 3: a record with a different terminal_reason must NOT enter, and must
        # be reported. Given a cost that would visibly move both the floor and the range.
        _write(runs / "run-a" / "trials" / "gX__ts__t2.json",
               _rec("gX", "ts", 999.0, 900, reason="max_turns"))
        # Direction 4: a spec-change record (no `game`) must never be pooled in.
        _write(runs / "run-a" / "trials" / "t1_rally__ts__t0.json",
               {"task": "t1_rally", "agent": {"cost_usd": 555.0,
                                              "terminal_reason": "completed"}})
        # Direction 5: a trials/ dir inside an agent-authored tree is skipped and counted.
        _write(runs / "run-a" / "work" / "someagent" / "trials" / "notours.json",
               _rec("gX", "rust", 777.0, 777))

        c = measure("known-answer tree", runs)
        check("one qualifying group", len(c["groups"]), 1)
        g = only_group("known-answer tree", c)
        check("group is run-a/gX", (g["run"], g["game"]), ("run-a", "gX"))
        check("trials in group", g["trials"], 8)
        check("floor", _round(g["within_cell_floor_usd"], 4), 11.0)
        check("between-stack range", _round(g["between_stack_range_usd"], 4), 55.0)
        check("ratio", _round(g["range_pct_of_floor"], 4), 500.0)
        check("r(cost,turns) is exactly 1 on monotone data",
              _round(g["r_cost_turns"], 6), 1.0)
        check("r used all 8 points", g["r_cost_turns_n"], 8)
        check("widest turn span", g["widest_turn_span"],
              {"stack": "rust", "low": 200, "high": 240, "span": 40})
        check("cheapest to dearest", g["cheapest_to_dearest"],
              ["ts", "unity", "godot", "rust"])
        # gaps are ts 10, unity 4, godot 10, rust 20 -> widest over tightest is 20/4
        check("cell gap ratio", _round(g["cell_gap_ratio"], 4), 5.0)
        check("max_turns record excluded and reported",
              c["excluded_by_terminal_reason"], {"max_turns": 1})
        check("spec-change record never entered", c["wholegame_records"], 9)
        check("agent-authored trials/ skipped", c["skipped_agent_authored"], 1)
        a = across("known-answer tree", c)
        check("range exceeds floor here", a["groups_where_range_exceeds_floor"], 1)
        check("and the per-group flag agrees", g["range_exceeds_floor"], True)
        # No mean rank is published. The rank VECTOR and a count of firsts say the same
        # thing and cannot be re-quoted as a statistic over a population nobody has shown
        # homogeneous (AGENTS.md rule 4).
        check("a mean rank is not published at all", "mean_cost_rank" in a, False)
        check("the rank vector is, in group order", a["cost_rank_per_group"],
              {"godot": [3], "rust": [4], "ts": [1], "unity": [2]})
        check("with a count of firsts", a["times_cheapest"],
              {"godot": 0, "rust": 0, "ts": 1, "unity": 0})

        # ---- THE THRESHOLDS. Both are CLI-reachable and both can be set to a value that
        # cannot define the measure. `--min-trials-per-cell 1` admits a cell with no gap and
        # scores it $0.00 — the thin-cell fail-open, reached by a flag instead of by data.
        for kwargs, want in (({"min_trials_per_cell": 1}, "min-trials-per-cell"),
                             ({"min_trials_per_cell": 0}, "min-trials-per-cell"),
                             ({"min_stacks": 1}, "min-stacks"),
                             ({"min_stacks": 0}, "min-stacks")):
            try:
                cost_census(runs, **kwargs)
                failures.append(f"{kwargs}: measured instead of refusing")
            except CostCensusError as exc:
                if want not in str(exc):
                    failures.append(f"{kwargs}: refusal does not name {want}: {exc}")
            except Exception as exc:  # noqa: BLE001 - wrong class is also a failure
                failures.append(f"{kwargs}: raised {type(exc).__name__}, not "
                                f"CostCensusError: {exc}")
        # The guard must not be so eager that it refuses a legitimate threshold. 2 is the
        # smallest value that CAN define the measure, and it must be accepted.
        c_two = measure("min_stacks=2, min_trials_per_cell=2", runs,
                        min_stacks=2, min_trials_per_cell=2)
        check("the smallest thresholds that define the measure are accepted",
              len(c_two["groups"]) >= 1, True)

        # Direction 3b, the VARIANT: had the max_turns record been let in, the answer
        # would have changed. Pin that it WOULD have — otherwise the exclusion above is
        # green for a reason that has nothing to do with the guard.
        c_mixed = measure("max_turns population", runs, terminal_reason="max_turns")
        check("the excluded record is real and is a different population",
              c_mixed["excluded_by_terminal_reason"], {"completed": 8})
        check("that population has no qualifying group", len(c_mixed["groups"]), 0)

        # ---- Direction 6, THE FAIL-OPEN ONE: a cell with a single trial has no gap.
        # Counting it as a gap of $0.00 would drag the floor from 11.00 to 8.25 and take
        # the ratio from 500% to 667% — a plausible in-range number, in the direction that
        # manufactures a difference. The group must be rejected instead, with the reason.
        _write(runs / "run-b" / "trials" / "gY__ts__t0.json", _rec("gY", "ts", 10.0, 100))
        _write(runs / "run-b" / "trials" / "gY__ts__t1.json", _rec("gY", "ts", 20.0, 120))
        _write(runs / "run-b" / "trials" / "gY__unity__t0.json",
               _rec("gY", "unity", 30.0, 140))
        _write(runs / "run-b" / "trials" / "gY__unity__t1.json",
               _rec("gY", "unity", 34.0, 148))
        _write(runs / "run-b" / "trials" / "gY__godot__t0.json",
               _rec("gY", "godot", 40.0, 160))
        _write(runs / "run-b" / "trials" / "gY__godot__t1.json",
               _rec("gY", "godot", 50.0, 180))
        _write(runs / "run-b" / "trials" / "gY__rust__t0.json",
               _rec("gY", "rust", 70.0, 220))   # ONE trial only
        c2 = measure("tree with a thin cell", runs)
        check("thin cell rejects the group",
              [grp["game"] for grp in c2["groups"]], ["gX"])
        rej = [r for r in c2["rejected_groups"] if r["game"] == "gY"]
        check("the rejection is reported once", len(rej), 1)
        check("the rejection names the thin cell",
              "rust" in (rej[0]["why"] if rej else ""), True)
        # And that a 1-trial cell would indeed have moved the answer, had it been counted.
        # Both sides written out as literals: gY's real gaps are ts 10, unity 4, godot 10,
        # and rust — the thin cell — would contribute 0.
        check("a $0.00 gap would have deflated gY's floor from 8.00 to 6.00",
              [(10.0 + 4.0 + 10.0) / 3, (10.0 + 4.0 + 10.0 + 0.0) / 4], [8.0, 6.0])

        # Direction 7: a group short of the stack count is rejected, not computed.
        _write(runs / "run-c" / "trials" / "gZ__ts__t0.json", _rec("gZ", "ts", 1.0, 10))
        _write(runs / "run-c" / "trials" / "gZ__ts__t1.json", _rec("gZ", "ts", 2.0, 20))
        _write(runs / "run-c" / "trials" / "gZ__rust__t0.json", _rec("gZ", "rust", 3.0, 30))
        _write(runs / "run-c" / "trials" / "gZ__rust__t1.json", _rec("gZ", "rust", 4.0, 40))
        c3 = measure("tree with a 2-stack group", runs)
        check("2-stack group rejected at min_stacks=4",
              [r["game"] for r in c3["rejected_groups"] if r["game"] == "gZ"], ["gZ"])
        c4 = measure("the same tree at min_stacks=2", runs, min_stacks=2)
        check("the same group qualifies at min_stacks=2",
              sorted(grp["game"] for grp in c4["groups"]), ["gX", "gZ"])

        # Direction 8: zero variance makes r undefined; 0.0 would be a plausible answer.
        # Four identical stacks: cost varies within every cell, turns do not vary at all.
        flat = Path(tmp) / "flat"
        for stack in ("ts", "unity", "godot", "rust"):
            _write(flat / "run-f" / "trials" / f"gF__{stack}__t0.json",
                   _rec("gF", stack, 10.0, 100))
            _write(flat / "run-f" / "trials" / f"gF__{stack}__t1.json",
                   _rec("gF", stack, 20.0, 100))
        gf = only_group("no-turn-variance tree", measure("no-turn-variance tree", flat))
        check("r is undefined, not 0.0, with no variance in turns",
              gf["r_cost_turns"], None)
        check("four identical stacks give a floor of 10 and a range of 0",
              [gf["within_cell_floor_usd"], gf["between_stack_range_usd"]], [10.0, 0.0])
        check("and therefore a ratio of 0%, not a division error",
              gf["range_pct_of_floor"], 0.0)

        # Direction 8b: a floor of exactly $0.00 — every cell internally identical — must
        # give NO ratio. Any number here is a division by zero dressed up as a result.
        zero = Path(tmp) / "zerofloor"
        for i, stack in enumerate(("ts", "unity", "godot", "rust")):
            for t in (0, 1):
                _write(zero / "run-z" / "trials" / f"gZf__{stack}__t{t}.json",
                       _rec("gZf", stack, 10.0 + i, 100 + i))
        gz = only_group("zero-floor tree", measure("zero-floor tree", zero))
        czero = measure("zero-floor tree", zero)
        check("a zero floor is reported as zero", gz["within_cell_floor_usd"], 0.0)
        check("a between-stack range still exists", gz["between_stack_range_usd"], 3.0)
        check("but the ratio is undefined, not a number", gz["range_pct_of_floor"], None)
        check("and so is the cell-gap ratio, whose divisor is also 0",
              gz["cell_gap_ratio"], None)
        # THE RATIO IS UNDEFINED; THE COMPARISON IS NOT. $3.00 of range over a $0.00 floor
        # exceeds it as completely as a group can. Counting exceedance off the percentage
        # dropped exactly these groups — fail-open, understating how much the stacks
        # disagree — so both the per-group flag and the across-groups count are pinned here.
        check("a zero-floor group still EXCEEDS its floor", gz["range_exceeds_floor"], True)
        check("and is counted as such across groups",
              across("zero-floor tree", czero)["groups_where_range_exceeds_floor"], 1)
        # And render() must survive it. The data path being right is not enough if the tool
        # dies formatting None with :.0f on the way to the terminal.
        rendered = ""
        try:
            rendered = render(czero)
        except Exception as exc:  # noqa: BLE001 - any failure rendering is a failure
            failures.append(f"render on a zero-floor tree raised "
                            f"{type(exc).__name__}: {exc}")
        check("render says undefined rather than crashing", "undefined" in rendered, True)
        check("render still marks the exceedance",
              "range EXCEEDS the floor" in rendered, True)

        # Direction 9: records with no num_turns give r over the subset, refused below 3.
        noturns = Path(tmp) / "noturns"
        for stack in ("ts", "unity", "godot", "rust"):
            _write(noturns / "run-n" / "trials" / f"gN__{stack}__t0.json",
                   _rec("gN", stack, 10.0))
            _write(noturns / "run-n" / "trials" / f"gN__{stack}__t1.json",
                   _rec("gN", stack, 20.0))
        _write(noturns / "run-n" / "trials" / "gN__ts__t2.json", _rec("gN", "ts", 30.0, 300))
        _write(noturns / "run-n" / "trials" / "gN__unity__t2.json",
               _rec("gN", "unity", 40.0, 400))
        gn = only_group("partial-turns tree", measure("partial-turns tree", noturns))
        check("r counts only the records carrying num_turns", gn["r_cost_turns_n"], 2)
        check("r is refused below 3 points", gn["r_cost_turns"], None)
        # A cell with NO turn record has span None; a cell with one has span 0. Those are
        # different facts and anything that renders them the same is the third-value error
        # this project keeps paying for. Stacks sort godot, rust, ts, unity.
        check("no turn record is None, one turn record is a span of 0 — not the same",
              [row["turn_span"] for row in gn["per_stack"]], [None, None, 0, 0])

        # Direction 10: a run nested inside an archive wrapper is found, at its own path.
        nested = Path(tmp) / "nested"
        for stack in ("ts", "unity", "godot", "rust"):
            _write(nested / "archive-w" / "run-d" / "trials" / f"gD__{stack}__t0.json",
                   _rec("gD", stack, 10.0, 100))
            _write(nested / "archive-w" / "run-d" / "trials" / f"gD__{stack}__t1.json",
                   _rec("gD", stack, 20.0, 200))
        cnest = measure("nested-run tree", nested)
        check("nested run found and named by its relative path",
              [(grp["run"], grp["game"]) for grp in cnest["groups"]],
              [("archive-w/run-d", "gD")])

        # ---- Direction 10b: A RECORD THAT PARSES IS NOT A RECORD THAT CAN BE GROUPED.
        # `main()` catches only CostCensusError, so a whole-game record with no `stack` was
        # an uncaught KeyError and a non-numeric cost an uncaught TypeError — a traceback
        # where a named, fail-closed measurement error belongs. Both must name the file.
        def ok_agent(**over):
            agent = {"cost_usd": 1.0, "terminal_reason": "completed"}
            agent.update(over)
            return agent

        malformed = [
            # `stack`: absent, empty, wrong type. Absent was an uncaught KeyError.
            ({"game": "gB", "agent": ok_agent()}, "stack"),
            ({"game": "gB", "stack": "", "agent": ok_agent()}, "stack"),
            ({"game": "gB", "stack": 7, "agent": ok_agent()}, "stack"),
            # `agent`: absent or not an object. `.get()` on a str is an AttributeError.
            ({"game": "gB", "stack": "ts"}, "agent"),
            ({"game": "gB", "stack": "ts", "agent": "nope"}, "agent"),
            ({"game": "gB", "stack": "ts", "agent": []}, "agent"),
            # `game`: an unhashable value is a TypeError on the group key, frames away.
            ({"game": ["gB"], "stack": "ts", "agent": ok_agent()}, "game"),
            ({"game": "", "stack": "ts", "agent": ok_agent()}, "game"),
            # `cost_usd`: a string, and a bool — `True` IS an int and would average as 1.0.
            ({"game": "gB", "stack": "ts", "agent": ok_agent(cost_usd="40.00")}, "cost_usd"),
            ({"game": "gB", "stack": "ts", "agent": ok_agent(cost_usd=True)}, "cost_usd"),
            # `num_turns`: a non-integer reaches min()/max() against real ints.
            ({"game": "gB", "stack": "ts", "agent": ok_agent(num_turns="many")},
             "num_turns"),
            ({"game": "gB", "stack": "ts", "agent": ok_agent(num_turns=3.5)}, "num_turns"),
        ]
        for bad, label in malformed:
            shaped = Path(tmp) / "shaped"
            if shaped.exists():
                shutil.rmtree(shaped)
            _write(shaped / "run-s" / "trials" / "bad_record.json", bad)
            try:
                cost_census(shaped)
                failures.append(f"malformed `{label}` {bad!r}: measured instead of raising")
            except CostCensusError as exc:
                if "bad_record.json" not in str(exc) or label not in str(exc):
                    failures.append(f"malformed `{label}`: refusal does not name the file "
                                    f"and the field: {exc}")
            except Exception as exc:  # noqa: BLE001 - wrong class is also a failure
                failures.append(f"malformed `{label}`: raised {type(exc).__name__}, not "
                                f"CostCensusError: {exc}")

        # ---- NaN AND INFINITY, and they are their own case because they do not RAISE.
        # `json.loads` accepts the bare literals, both are `float`, and NaN propagates
        # through every mean while comparing False against everything — so a group whose
        # numbers are not numbers would report `range_exceeds_floor: False` and print `nan`.
        # A type check alone passes all three; only `math.isfinite` refuses them.
        check("NaN, Infinity and True are not numbers to this tool",
              [_is_number(v) for v in (float("nan"), float("inf"), float("-inf"), True)],
              [False, False, False, False])
        check("but real numbers are", [_is_number(v) for v in (0, -1, 2.5, 1e9)],
              [True, True, True, True])
        for literal in ("NaN", "Infinity", "-Infinity"):
            nan_tree = Path(tmp) / "nan"
            if nan_tree.exists():
                shutil.rmtree(nan_tree)
            nan_tree.joinpath("run-x", "trials").mkdir(parents=True)
            # Written as TEXT, not through json.dumps: these arrive from a real file, and
            # the point is that the parser accepts them.
            (nan_tree / "run-x" / "trials" / "nan_record.json").write_text(
                '{"game": "gN", "stack": "ts", "agent": {"cost_usd": %s, '
                '"terminal_reason": "completed"}}' % literal)
            try:
                cost_census(nan_tree)
                failures.append(f"cost_usd: {literal} was accepted as a number")
            except CostCensusError as exc:
                if "nan_record.json" not in str(exc) or "cost_usd" not in str(exc):
                    failures.append(f"cost_usd: {literal}: refusal does not name the file "
                                    f"and the field: {exc}")
            except Exception as exc:  # noqa: BLE001 - wrong class is also a failure
                failures.append(f"cost_usd: {literal}: raised {type(exc).__name__}, not "
                                f"CostCensusError: {exc}")
        # A record with NO cost field at all is a different case and stays an exclusion,
        # not a refusal — it is absent, not wrong. Variant B above pins that.

        # Direction 11: a malformed record fails loudly, naming its file. Swallowing it
        # would drop a record from a population without changing anything a reader can see.
        (runs / "run-a" / "trials" / "broken.json").write_text("{not json")
        try:
            cost_census(runs)
            failures.append("malformed record: returned a result instead of raising")
        except CostCensusError as exc:
            if "broken.json" not in str(exc):
                failures.append(f"malformed record: error does not name the file: {exc}")
        except Exception as exc:  # noqa: BLE001 - any other class is also a failure
            failures.append(f"malformed record: raised {type(exc).__name__}, "
                            f"not CostCensusError: {exc}")

        # ---- VARIANTS. A mutant asks whether the check CAN fail; only a variant asks
        # whether it can still PASS on an input it mishandles (AGENTS.md rule 15). Every
        # false negative adjudicated in this project has been of the second kind.
        var = Path(tmp) / "variants"

        # Variant A: a $0.00 trial. `high / low` is a ZeroDivisionError, and a spread of
        # 0.0 or inf would both be plausible-looking. It must be reported as absent, and
        # the gap and the floor must still be computed — they do not need the ratio.
        for stack in ("ts", "unity", "godot"):
            _write(var / "run-v" / "trials" / f"gV__{stack}__t0.json",
                   _rec("gV", stack, 10.0, 100))
            _write(var / "run-v" / "trials" / f"gV__{stack}__t1.json",
                   _rec("gV", stack, 20.0, 200))
        _write(var / "run-v" / "trials" / "gV__rust__t0.json", _rec("gV", "rust", 0.0, 50))
        _write(var / "run-v" / "trials" / "gV__rust__t1.json", _rec("gV", "rust", 12.0, 150))
        gv = only_group("zero-cost variant", measure("zero-cost variant", var))
        rust_row = next((r for r in gv["per_stack"] if r["stack"] == "rust"), {})
        check("a $0.00 low gives no spread rather than a division",
              rust_row.get("spread", "missing row"), None)
        check("the gap is still measured across a $0.00 trial", rust_row.get("gap"), 12.0)
        check("and the floor still lands, over 4 cells",
              _round(gv["within_cell_floor_usd"], 4), _round((10 + 10 + 10 + 12) / 4, 4))

        # Variant B: a record with no `agent.cost_usd` at all. It has no cost to average,
        # so it must be excluded and COUNTED — dropping it silently would shrink a cell
        # without changing anything a reader of the output can see.
        _write(var / "run-v" / "trials" / "gV__ts__t2.json",
               {"game": "gV", "stack": "ts",
                "agent": {"terminal_reason": "completed", "num_turns": 999}})
        cv = measure("no-cost-field variant", var)
        check("a record with no cost is excluded under its own label",
              cv["excluded_by_terminal_reason"], {"no cost_usd": 1})
        check("and the group is otherwise unchanged",
              _round(only_group("no-cost-field variant", cv)["within_cell_floor_usd"], 4),
              _round((10 + 10 + 10 + 12) / 4, 4))

        # Variant C: an UNEVEN cell — 3 trials in one stack, 2 in the others. The gap is
        # still high minus low, the per-stack `n` must say 3, and nothing may crash on the
        # assumption that every cell is the same size.
        uneven = Path(tmp) / "uneven"
        for stack in ("ts", "unity", "godot", "rust"):
            _write(uneven / "run-u" / "trials" / f"gU__{stack}__t0.json",
                   _rec("gU", stack, 10.0, 100))
            _write(uneven / "run-u" / "trials" / f"gU__{stack}__t1.json",
                   _rec("gU", stack, 20.0, 200))
        _write(uneven / "run-u" / "trials" / "gU__rust__t2.json",
               _rec("gU", "rust", 50.0, 500))
        gu = only_group("uneven-cell variant", measure("uneven-cell variant", uneven))
        check("the uneven cell reports its own n",
              [(r["stack"], r["n"]) for r in gu["per_stack"]],
              [("godot", 2), ("rust", 3), ("ts", 2), ("unity", 2)])
        check("its gap spans all 3 trials, not the first 2",
              next((r["gap"] for r in gu["per_stack"] if r["stack"] == "rust"), None),
              40.0)
        check("the floor is the mean of 4 cell gaps, one of which came from 3 trials",
              _round(gu["within_cell_floor_usd"], 4), _round((10 + 10 + 10 + 40) / 4, 4))
        check("and r used all 9 trials", gu["r_cost_turns_n"], 9)

    # Direction 12: pearson's own contract, away from any tree.
    check("pearson of an exact negative line", _round(pearson([1, 2, 3], [3, 2, 1]), 6), -1.0)
    check("pearson refuses 2 points", pearson([1, 2], [1, 2]), None)
    check("pearson refuses a constant series", pearson([1, 1, 1], [1, 2, 3]), None)

    # ---- THE ORDERING ADJUDICATION.
    # Every p below is a closed form written down before the tool is run, not a number read
    # off it: with k stacks and m clusters, an unbroken lead has probability (1/k)**m for a
    # stack named in advance and k*(1/k)**m for whichever stack happens to lead. Fixtures
    # are kept small on purpose — the enumeration is (k!)**m, and the mutant sweep runs this
    # selftest once per mutant, so a 300,000-assignment fixture here is paid for many times.

    EXPECTED_ORDERING_FIELDS = (
        "alpha", "stacks", "n_groups", "rank_sum_per_stack", "null_expectation_rank_sum",
        "leader", "times_cheapest", "clusterings", "leader_margins",
        "margins_exceeding_floor", "groups_led")
    EXPECTED_MARGIN_FIELDS = (
        "run", "game", "leader_rank", "cheapest", "leads", "runner_up", "margin_usd",
        "floor_usd", "margin_pct_of_floor", "margin_exceeds_floor")
    EXPECTED_CLUSTERING_FIELDS = (
        "clustering", "unit", "n_clusters", "clusters", "assignments", "exact", "draws",
        "attainable_min_rank_sum", "p_named", "p_named_count", "p_any", "p_any_count",
        "p_floor", "at_the_extreme", "resolves", "design_can_resolve",
        "p_floor_dropping_one_cluster")

    def order(label: str, runs_dir: Path, **kw) -> dict:
        try:
            o = ordering_test(cost_census(runs_dir, **kw))
        except Exception as exc:  # noqa: BLE001 - anything raised here is a failure
            failures.append(f"{label}: raised {type(exc).__name__}: {exc}")
            return _Absent(clusterings=[])
        missing = [k for k in EXPECTED_ORDERING_FIELDS if k not in o]
        missing += [f"clusterings[].{k}" for k in EXPECTED_CLUSTERING_FIELDS
                    if o["clusterings"] and k not in o["clusterings"][0]]
        if missing:
            failures.append(f"{label}: ordering result is missing field(s) {missing}")
            return _Absent(o, clusterings=o.get("clusterings", []))
        return o

    def by_unit(o: dict, name: str) -> dict:
        return next((t for t in o["clusterings"] if t["clustering"] == name), _Absent())

    def first_margin(label: str, o: dict) -> dict:
        """The one margin row, or a NAMED failure. `o["leader_margins"][0]` is a TypeError
        when the ordering could not be produced, and a traceback loses every failure
        already collected — they are printed at the end. This is `drop_field`'s lesson one
        level down: it broke that mutant's diagnosis, not its verdict."""
        rows = o["leader_margins"]
        if not rows:
            failures.append(f"{label}: no leader margins were produced")
            return _Absent()
        missing = [k for k in EXPECTED_MARGIN_FIELDS if k not in rows[0]]
        if missing:
            failures.append(f"{label}: margin row is missing field(s) {missing}")
            return _Absent(rows[0])
        return rows[0]

    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)

        # ---- O1. k=4, m=2. Two runs, two games, no run and no game shared, so all three
        # clusterings are the same 2 clusters. ts is cheapest in both.
        #   p named in advance  (1/4)**2 = 1/16   = 36/576
        #   p post-hoc-safe   4*(1/4)**2 = 1/4    = 144/576
        # 0.25 is also the smallest p the design could return, so this fixture is a design
        # that CANNOT resolve holding data that is as extreme as it gets.
        o1 = base / "o1"
        costs = {"ts": (10.0, 20.0), "unity": (30.0, 34.0),
                 "godot": (40.0, 50.0), "rust": (60.0, 80.0)}
        for run, game in (("run-a", "gX"), ("run-b", "gY")):
            for stack, (lo, hi) in costs.items():
                _write(o1 / run / "trials" / f"{game}__{stack}__t0.json",
                       _rec(game, stack, lo, 100))
                _write(o1 / run / "trials" / f"{game}__{stack}__t1.json",
                       _rec(game, stack, hi, 200))
        got = order("O1 unbroken lead, k=4 m=2", o1)
        check("O1 leader", got["leader"], "ts")
        check("O1 rank sums", got["rank_sum_per_stack"],
              {"godot": 6.0, "rust": 8.0, "ts": 2.0, "unity": 4.0})
        check("O1 null expectation", got["null_expectation_rank_sum"], 5.0)
        check("O1 all three clusterings see the same 2 clusters",
              [t["n_clusters"] for t in got["clusterings"]], [2, 2, 2])
        run1 = by_unit(got, "run")
        check("O1 assignments enumerated exactly", (run1["assignments"], run1["exact"]),
              (576, True))
        check("O1 p named in advance is 1/16", (run1["p_named_count"], run1["draws"]),
              (36, 576))
        check("O1 p post-hoc-safe is 4/16", (run1["p_any_count"], run1["draws"]),
              (144, 576))
        check("O1 the lead is as extreme as the design allows",
              (run1["attainable_min_rank_sum"], run1["at_the_extreme"]), (2.0, True))
        check("O1 and the design still cannot resolve at alpha",
              (run1["resolves"], run1["design_can_resolve"]), (False, False))
        # Drop one of 2 clusters and 1 remains, where every assignment hands some stack the
        # smallest column: the floor is 1.0 and the test is vacuous.
        check("O1 dropping a cluster leaves a vacuous test",
              run1["p_floor_dropping_one_cluster"], 1.0)

        # ---- O2. k=2, m=7, unbroken lead. Seven runs, seven games, nothing shared.
        #   p named in advance  (1/2)**7 = 1/128 = 0.0078
        #   p post-hoc-safe   2*(1/2)**7 = 2/128 = 0.015625 -> resolves, and the design can
        #   floor dropping one cluster    2/64   = 0.03125  -> STILL below alpha
        # This is the direction O1 cannot reach: a p below alpha, so `resolves` is pinned
        # both true and false across the fixtures rather than only false — and a result
        # that does not depend on every cluster being present, which is the property the
        # stored corpus lacks.
        o2 = base / "o2"
        for n in range(7):
            _write(o2 / f"run-{n}" / "trials" / f"g{n}__ts__t0.json",
                   _rec(f"g{n}", "ts", 10.0, 100))
            _write(o2 / f"run-{n}" / "trials" / f"g{n}__ts__t1.json",
                   _rec(f"g{n}", "ts", 20.0, 200))
            _write(o2 / f"run-{n}" / "trials" / f"g{n}__rust__t0.json",
                   _rec(f"g{n}", "rust", 30.0, 300))
            _write(o2 / f"run-{n}" / "trials" / f"g{n}__rust__t1.json",
                   _rec(f"g{n}", "rust", 40.0, 400))
        got = order("O2 unbroken lead, k=2 m=7", o2, min_stacks=2)
        run2 = by_unit(got, "run")
        check("O2 rank sums", got["rank_sum_per_stack"], {"rust": 14.0, "ts": 7.0})
        check("O2 p named in advance is 1/128", (run2["p_named_count"], run2["draws"]),
              (1, 128))
        check("O2 p post-hoc-safe is 2/128", (run2["p_any_count"], run2["draws"]), (2, 128))
        check("O2 resolves, and the design could",
              (run2["resolves"], run2["design_can_resolve"]), (True, True))
        check("O2 lead beats the floor in every group it leads",
              (got["groups_led"], got["margins_exceeding_floor"]), (7, 7))
        # 7 clusters down to 6 is 2*(1/2)**6 = 1/32, still below alpha — so this result does
        # NOT depend on every cluster being present. The stored corpus is the other way.
        check("O2 survives losing a cluster",
              run2["p_floor_dropping_one_cluster"], 0.03125)

        # ---- O3. O2 with the lead broken in one run. This is the fixture that separates
        # `p_any` from `p_floor`: the design CAN resolve and the data does not.
        #   ts sums 1*6 + 2 = 8, rust 13; smallest attainable 7, so ts is NOT at the extreme
        #   p named in advance  P(at most 1 loss) = (1 + 7)/128 = 8/128 = 0.0625
        #   p post-hoc-safe     both tails, 16/128                      = 0.125
        #   p floor             2/128                                   = 0.015625 < alpha
        o3 = base / "o3"
        shutil.copytree(o2, o3)
        for t, cost in (("t0", 30.0), ("t1", 40.0)):
            _write(o3 / "run-6" / "trials" / f"g6__ts__{t}.json",
                   _rec("g6", "ts", cost + 30.0, 100))
        got = order("O3 lead broken in one cluster", o3, min_stacks=2)
        run3 = by_unit(got, "run")
        check("O3 leader is still ts", got["leader"], "ts")
        check("O3 rank sums", got["rank_sum_per_stack"], {"rust": 13.0, "ts": 8.0})
        check("O3 ts is no longer at the attainable extreme",
              (run3["attainable_min_rank_sum"], run3["at_the_extreme"]), (7.0, False))
        check("O3 p named in advance is 8/128", (run3["p_named_count"], run3["draws"]),
              (8, 128))
        check("O3 p post-hoc-safe is 16/128", (run3["p_any_count"], run3["draws"]),
              (16, 128))
        check("O3 the design could resolve; the data does not",
              (run3["resolves"], run3["design_can_resolve"]), (False, True))
        # The margin is measured only where the leader actually leads. Measuring it in the
        # run it lost would count that run's gap — 30, against a floor of 10 — as evidence
        # FOR the leader, which is the fail-open direction.
        check("O3 margins are read from the 6 groups ts leads, not all 7",
              (got["groups_led"], got["margins_exceeding_floor"]), (6, 6))

        # ---- O4. The three clusterings must be able to DISAGREE, or reporting three of
        # them is decoration. run-a holds two games and run-b repeats one of them, so
        # run and game each split it 2 ways and the components merge all three groups into
        # one. A single cluster makes the test vacuous — p = 1.0, by construction, because
        # whichever stack holds the smallest column holds it in every assignment.
        o4 = base / "o4"
        for run, game in (("run-a", "gX"), ("run-a", "gY"), ("run-b", "gX")):
            for stack, (lo, hi) in costs.items():
                _write(o4 / run / "trials" / f"{game}__{stack}__t0.json",
                       _rec(game, stack, lo, 100))
                _write(o4 / run / "trials" / f"{game}__{stack}__t1.json",
                       _rec(game, stack, hi, 200))
        got = order("O4 clusterings disagree", o4)
        check("O4 run splits 2, game splits 2, components merge to 1",
              [(t["clustering"], t["n_clusters"]) for t in got["clusterings"]],
              [("run", 2), ("game", 2), ("run+game", 1)])
        comp4 = by_unit(got, "run+game")
        check("O4 one cluster makes the test vacuous, and it says so",
              (comp4["p_any"], comp4["p_floor"], comp4["design_can_resolve"]),
              (1.0, 1.0, False))

        # ---- O5. Ties. Two stacks with the same mean must SHARE the average rank; handing
        # one of them rank 1 by the sort's stability manufactures a lead in the exact
        # quantity being adjudicated, and `times_cheapest` must then count neither.
        check("a tie shares the average rank",
              group_ranks({"per_stack": [{"stack": "a", "mean": 1.0},
                                         {"stack": "b", "mean": 1.0},
                                         {"stack": "c", "mean": 3.0},
                                         {"stack": "d", "mean": 4.0}]}),
              {"a": 1.5, "b": 1.5, "c": 3.0, "d": 4.0})
        check("a strict order ranks 1..k",
              group_ranks({"per_stack": [{"stack": "a", "mean": 4.0},
                                         {"stack": "b", "mean": 1.0},
                                         {"stack": "c", "mean": 3.0},
                                         {"stack": "d", "mean": 2.0}]}),
              {"b": 1.0, "d": 2.0, "c": 3.0, "a": 4.0})
        o5 = base / "o5"
        tied = {"ts": (10.0, 20.0), "unity": (10.0, 20.0),
                "godot": (40.0, 50.0), "rust": (60.0, 80.0)}
        for stack, (lo, hi) in tied.items():
            _write(o5 / "run-a" / "trials" / f"gX__{stack}__t0.json",
                   _rec("gX", stack, lo, 100))
            _write(o5 / "run-a" / "trials" / f"gX__{stack}__t1.json",
                   _rec("gX", stack, hi, 200))
        got = order("O5 tied cheapest", o5)
        check("O5 the tied pair shares rank 1.5",
              got["rank_sum_per_stack"],
              {"godot": 3.0, "rust": 4.0, "ts": 1.5, "unity": 1.5})
        check("O5 a tie is cheapest in nothing",
              got["times_cheapest"], {"godot": 0, "rust": 0, "ts": 0, "unity": 0})
        # ... and it leads nothing either. These two counts are the same claim, and they
        # disagreed: `means` sorts on (mean, stack), so `ts` won the tie on its NAME and was
        # recorded as leading the group by $0.00 while being cheapest in none of it.
        tied_margin = first_margin("O5 tied cheapest", got)
        check("O5 a tie leads nothing, by the same count",
              (got["groups_led"], tied_margin["leads"], tied_margin["margin_usd"]),
              (0, False, None))

        # ---- O6. The leader's MARGIN is a different claim from its consistency, and the
        # comparison is against the group's own floor, not against zero. Here ts leads by
        # $4.00 over a floor of $8.00: it is the cheapest arm and its lead is inside the
        # noise, which is the shape the stored corpus turns out to have.
        o6 = base / "o6"
        narrow = {"ts": (10.0, 30.0), "unity": (22.0, 26.0),
                  "godot": (40.0, 44.0), "rust": (60.0, 64.0)}
        for stack, (lo, hi) in narrow.items():
            _write(o6 / "run-a" / "trials" / f"gX__{stack}__t0.json",
                   _rec("gX", stack, lo, 100))
            _write(o6 / "run-a" / "trials" / f"gX__{stack}__t1.json",
                   _rec("gX", stack, hi, 200))
        got = order("O6 lead inside the noise", o6)
        margin = first_margin("O6 lead inside the noise", got)
        check("O6 the margin is over the RUNNER-UP, not the dearest stack",
              (margin["runner_up"], margin["margin_usd"]), ("unity", 4.0))
        check("O6 measured against the group's own floor",
              (margin["floor_usd"], margin["margin_pct_of_floor"]), (8.0, 50.0))
        check("O6 a lead inside the floor is not a lead that beats it",
              (got["groups_led"], got["margins_exceeding_floor"],
               margin["margin_exceeds_floor"]), (1, 0, False))

        # ---- O7. A cluster whose two smallest columns are TIED, which is where the design
        # floor stops being `k * (1/k)**m`. Two stacks at the same mean in run-c means
        # either of them reaches the smallest attainable total, so more assignments do:
        #   clusters   a, b -> columns (1, 2), unique minimum
        #              c    -> columns (1.5, 1.5), no unique minimum
        #   attainable minimum          1 + 1 + 1.5 = 3.5
        #   p floor      4 of 8 = 0.5, against a closed form of 2*(1/2)**3 = 0.25
        #   dropping one cluster        1.0, against a closed form of 0.5
        # Both figures are DOUBLE what the formula says, in the direction that makes a
        # design look sharper than it is.
        o7 = base / "o7"
        for run, game, rust_costs in (("run-a", "gA", (30.0, 40.0)),
                                      ("run-b", "gB", (30.0, 40.0)),
                                      ("run-c", "gC", (10.0, 20.0))):
            for t, cost in (("t0", 10.0), ("t1", 20.0)):
                _write(o7 / run / "trials" / f"{game}__ts__{t}.json",
                       _rec(game, "ts", cost, 100))
            for t, cost in (("t0", rust_costs[0]), ("t1", rust_costs[1])):
                _write(o7 / run / "trials" / f"{game}__rust__{t}.json",
                       _rec(game, "rust", cost, 200))
        got = order("O7 tied column minima", o7, min_stacks=2)
        run7 = by_unit(got, "run")
        check("O7 the tie is in the ranks", got["rank_sum_per_stack"],
              {"rust": 5.5, "ts": 3.5})
        check("O7 the floor is not k*(1/k)**m when a cluster's minimum is not unique",
              (run7["attainable_min_rank_sum"], run7["p_floor"]), (3.5, 0.5))
        check("O7 nor is the fragility floor",
              run7["p_floor_dropping_one_cluster"], 1.0)

        # ---- O7b. THE SAMPLED PATH MUST NOT ALLOCATE THE EXACT PATH FIRST. `k=10` over one
        # cluster is 3,628,800 assignments, which is above the limit and therefore sampled
        # — but only if the mode is decided before `k!` vectors per cluster are built.
        # Measured: deciding first peaks at 24 MB, building first at 2085 MB. This pins the
        # RESOURCE rather than the return value, because both structures return the same
        # numbers (rule 13: guard the resource, and verify on the path that holds it).
        import resource as _resource

        def _peak_mb() -> float:
            # ru_maxrss is BYTES on macOS and KILOBYTES on Linux. Reading it as one unit on
            # both makes this pin off by 1024x on one of them — passing vacuously on Linux.
            raw = _resource.getrusage(_resource.RUSAGE_SELF).ru_maxrss
            return raw / (1 << 20) if sys.platform == "darwin" else raw / 1024

        before = _peak_mb()
        big = _permutation_test([[float(j) for j in range(10)]], 0.0, 10)
        grew = _peak_mb() - before
        check("the sampled path reports the right size without enumerating it",
              (big["exact"], big["assignments"], big["draws"]),
              (False, 3628800, SAMPLE_DRAWS))
        if grew > 200:
            failures.append(
                f"sampled mode grew peak RSS by {grew:.0f} MB: it materialised the exact "
                f"path before checking the limit (deciding first measures ~2 MB here)")

        # ---- O8. Two refusals. Both would otherwise return a plausible in-range p, and
        # both must be a NAMED CostCensusError — a KeyError several frames down exits
        # non-zero too, and says nothing about what broke.
        o8 = base / "o8"

        # The MESSAGE is pinned, not merely the exception type. Two guards here refuse the
        # same empty population, so a type-only check is satisfied by whichever fires — and
        # a reader handed "the groups do not carry one stack set" for an empty tree has
        # been told something that is true and useless.
        def refuses(label: str, says: str, **kw) -> None:
            try:
                ordering_test(cost_census(o8, **kw))
            except CostCensusError as exc:
                if says not in str(exc):
                    failures.append(f"{label}: refused with {str(exc)!r}, which does not "
                                    f"say {says!r} — the wrong guard fired")
                return
            except Exception as exc:  # noqa: BLE001 - a refusal must be the named error
                failures.append(f"{label}: raised {type(exc).__name__}: {exc} — a refusal "
                                f"must be a named CostCensusError, not a traceback")
                return
            failures.append(f"{label}: returned a p instead of refusing")

        for stack in ("ts", "rust"):
            _write(o8 / "run-a" / "trials" / f"gX__{stack}__t0.json",
                   _rec("gX", stack, 10.0, 100))
            _write(o8 / "run-a" / "trials" / f"gX__{stack}__t1.json",
                   _rec("gX", stack, 20.0, 200))
        # 2 stacks against a default --min-stacks of 4: nothing qualifies, so there is no
        # population to put a p-value over.
        refuses("no qualifying group", "nothing to adjudicate")
        for stack in ("ts", "unity"):
            _write(o8 / "run-b" / "trials" / f"gY__{stack}__t0.json",
                   _rec("gY", stack, 10.0, 100))
            _write(o8 / "run-b" / "trials" / f"gY__{stack}__t1.json",
                   _rec("gY", stack, 20.0, 200))
        # Now both groups qualify at 2 stacks and they hold DIFFERENT stacks. Permuting a
        # label across them is undefined, and doing it anyway returns a p.
        refuses("mismatched stack sets", "do not carry one stack set", min_stacks=2)

    for f in failures:
        print(f"FAIL  {f}")
    print(f"cost_census selftest: {'FAILED' if failures else 'ok'} "
          f"({len(failures)} failures)")
    return 1 if failures else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--runs-dir", default=str(DEFAULT_RUNS),
                    help="tree to measure over (default: eval/runs/)")
    ap.add_argument("--terminal-reason", default="completed",
                    help="the single population to compute over (default: completed)")
    ap.add_argument("--min-stacks", type=int, default=4,
                    help="stacks a group must carry to qualify (default: 4)")
    ap.add_argument("--min-trials-per-cell", type=int, default=2,
                    help="trials every cell must carry to have a gap (default: 2)")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--ordering", action="store_true",
                    help="adjudicate whether any stack is systematically cheapest, by "
                         "permutation of the stack labels within a cluster, enumerated "
                         "exactly below the assignment limit and seeded-sampled above it")
    ap.add_argument("--selftest", action="store_true",
                    help="pin the extraction against a tree with a known answer")
    args = ap.parse_args()

    if args.selftest:
        return selftest()

    try:
        c = cost_census(Path(args.runs_dir).expanduser().resolve(),
                        terminal_reason=args.terminal_reason,
                        min_stacks=args.min_stacks,
                        min_trials_per_cell=args.min_trials_per_cell)
        if args.ordering:
            c["ordering"] = ordering_test(c)
    except CostCensusError as exc:
        print(f"cost_census: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(c, indent=2))
    else:
        print(render_ordering(c) if args.ordering else render(c))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
