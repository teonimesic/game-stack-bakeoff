#!/usr/bin/env python3
"""Within-cell agreement: how often do a cell's two trials return DIFFERENT verdicts?

This is the producer for a figure four live documents quote and nothing computed. The
2026-08-22 recount behind `WR-paired-verdict-tie` was done by hand; reproducing its
`436 paired criteria` a day later took reverse-engineering the tier set it had summed
over, because no command in the repository printed it. A number with no producer is a
number the next reader has to guess at, and this one is load-bearing: it is the noise
floor the deterministic-tier ranking ban in `DECISIONS.md` rests on.

WHAT IT COUNTS. A cell is (run, game, stack); it holds two independent trials. A
criterion is PAIRED when both trials of a cell recorded it. Per (run, game, tier set):

  paired          how many paired criteria there are
  verdict-diff    on how many the two trials disagree on `passed`
  evidence-diff   on how many the two `evidence` strings differ

Verdict-diff over paired is the WITHIN-CELL NOISE FLOOR in verdict units. Evidence-diff
is the control that the two submissions are different artifacts at all - without it, a
verdict tie is equally consistent with the grader having read the same file twice.

THREE THINGS IT REFUSES TO SMOOTH OVER, each of which produced a wrong published number:

1. THE TIER SET IS PART OF THE FIGURE. `436` for `wg-matrix` sums all three tiers, of
   which 156 (35.8%) are LLM-judge criteria at weight 0.00 - not deterministic, and not
   what a claim about the deterministic tiers may be computed over. `232` for
   `wg-audio48` contains no judge criteria at all, because that run was never judged.
   The two figures were quoted side by side as one measurement; they are two. Every
   number below carries its tier set.

2. A CROSS-GAME SUM IS A COUNT, NEVER A RATE. `eval/RUNS.md` bans pooling tier-2 scores
   across games because the criterion count differs per game. `5 of 436` is a rate over
   three such games. The pooled row is printed - it is what the published figures are -
   and labelled as a count, with the per-game rates above it.

3. A CELL WHOSE TRIALS DID NOT BOTH COMPLETE IS NOT A CELL. Terminal reason comes from
   `trials/<tid>.json`, not from the report, and a cell with an unknown or non-completed
   reason is excluded and listed. `wg-g4c-capgate` is the case that matters: its two
   arms have no trial JSONs, return byte-identical diff lists to each other, and read
   12 of 140 - six times the floor anything else shows. Whatever they are, they are not
   two independent trials, and pooling them would raise the floor with copies.

A criterion recorded by only ONE trial of a pair is not a difference and is not counted;
it is a suite change between the two gradings, reported as `unpaired-criteria`.

Usage:
    ./paired_verdicts.py --selftest
    ./paired_verdicts.py --selftest --runs-root <main checkout>/eval/runs
    ./paired_verdicts.py --runs-root <main checkout>/eval/runs
    ./paired_verdicts.py --runs-root ... --run wg-matrix-2026-08-13T14-02-50

`--runs-root` is not optional and is not guessed. `eval/runs/` is gitignored, so an
agent worktree's copy of that path is empty and a census run there would report zero
differences - a confident, wrong, uniform answer of exactly the shape rule 12 names.

The walk is `**/artifacts/*/eval/report.json`. A single `*/` misses every run nested one
level deeper - `wg-g4c-capgate/capped` and `/uncapped` are two such - and a walker that
silently skips runs reports a floor over a population it did not describe.
"""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

#: The tiers that gate or score. `judge` is weight 0.00 and is not deterministic.
DETERMINISTIC = ("programmatic", "playbot")
ALL_TIERS = ("programmatic", "playbot", "judge")


@dataclass
class Counts:
    paired: int = 0
    verdict_diff: int = 0
    evidence_diff: int = 0
    unpaired_criteria: int = 0
    diffs: list = field(default_factory=list)

    @property
    def rate(self) -> float | None:
        return self.verdict_diff / self.paired if self.paired else None

    def add(self, other: "Counts") -> "Counts":
        return Counts(self.paired + other.paired,
                      self.verdict_diff + other.verdict_diff,
                      self.evidence_diff + other.evidence_diff,
                      self.unpaired_criteria + other.unpaired_criteria,
                      self.diffs + other.diffs)


# --------------------------------------------------------------------------- #
# loading
# --------------------------------------------------------------------------- #

def _terminal_reason(run_root: Path, tid: str) -> str:
    """Read the BUILD record, not the evaluation record.

    `report.json` says how a submission scored; only the trial JSON says whether the
    agent finished. Same reasoning as `discrimination._terminal_reason` (FINDINGS #22).
    A missing trial JSON is `unknown`, never `completed`: a cell we cannot partition is
    a cell we may not pool (rule 4).
    """
    f = run_root / "trials" / f"{tid}.json"
    if not f.is_file():
        return "unknown"
    try:
        return str(json.loads(f.read_text())["agent"].get("terminal_reason"))
    except (OSError, ValueError, KeyError, TypeError):
        return "unknown"


def load(runs_root: Path, only_run: str | None = None) -> list[dict]:
    """Every stored report, with its criteria keyed by (tier, id)."""
    rows = []
    for rep in sorted(runs_root.glob("**/artifacts/*/eval/report.json")):
        run_root = rep.parent.parent.parent.parent
        run = str(run_root.relative_to(runs_root))
        if only_run is not None and run != only_run:
            continue
        tid = rep.parent.parent.name
        parts = tid.split("__")
        if len(parts) != 3:
            continue
        game, stack, slot = parts
        rec = json.loads(rep.read_text())
        crits = {}
        for tier in ALL_TIERS:
            for c in ((rec.get(tier) or {}).get("criteria")) or []:
                if "id" in c and "passed" in c:
                    crits[(tier, c["id"])] = (bool(c["passed"]), c.get("evidence", ""))
        rows.append({"run": run, "tid": tid, "game": game, "stack": stack, "slot": slot,
                     "terminal_reason": _terminal_reason(run_root, tid), "crits": crits})
    return rows


# --------------------------------------------------------------------------- #
# counting
# --------------------------------------------------------------------------- #

def cells(rows: list[dict]) -> dict[tuple[str, str, str], list[dict]]:
    out: dict[tuple[str, str, str], list[dict]] = {}
    for r in rows:
        out.setdefault((r["run"], r["game"], r["stack"]), []).append(r)
    for v in out.values():
        v.sort(key=lambda r: r["slot"])
    return out


def usable(cell: list[dict]) -> tuple[bool, str]:
    """A cell is usable when it holds exactly two trials and both completed."""
    if len(cell) != 2:
        return False, f"{len(cell)} trial(s), not 2"
    bad = sorted({r["terminal_reason"] for r in cell} - {"completed"})
    if bad:
        return False, "terminal reason " + ",".join(bad)
    return True, "completed"


def count_cell(cell: list[dict], tiers: tuple[str, ...]) -> Counts:
    a, b = (r["crits"] for r in cell)
    ka = {k for k in a if k[0] in tiers}
    kb = {k for k in b if k[0] in tiers}
    c = Counts(unpaired_criteria=len(ka ^ kb))
    for k in sorted(ka & kb):
        c.paired += 1
        if a[k][0] != b[k][0]:
            c.verdict_diff += 1
            c.diffs.append((cell[0]["run"], cell[0]["game"], cell[0]["stack"],
                            k[0], k[1]))
        if a[k][1] != b[k][1]:
            c.evidence_diff += 1
    return c


def census(rows: list[dict], tiers: tuple[str, ...]
           ) -> tuple[dict[tuple[str, str], Counts],
                      list[tuple[tuple[str, str, str], str]]]:
    """Per (run, game) counts over usable cells, plus the cells that were excluded."""
    per: dict[tuple[str, str], Counts] = {}
    excluded: list[tuple[tuple[str, str, str], str]] = []
    for key, cell in sorted(cells(rows).items()):
        ok, why = usable(cell)
        if not ok:
            excluded.append((key, why))
            continue
        run, game, _ = key
        per[(run, game)] = per.get((run, game), Counts()).add(count_cell(cell, tiers))
    return per, excluded


# --------------------------------------------------------------------------- #
# rendering
# --------------------------------------------------------------------------- #

def _pct(c: Counts) -> str:
    return "    n/a" if c.rate is None else f"{c.rate * 100:6.2f}%"


def render(rows: list[dict]) -> str:
    out: list[str] = []
    for run in sorted({r["run"] for r in rows}):
        rs = [r for r in rows if r["run"] == run]
        reasons: dict[str, int] = {}
        for r in rs:
            reasons[r["terminal_reason"]] = reasons.get(r["terminal_reason"], 0) + 1
        out.append(f"=== {run} ===")
        out.append(f"  {len(rs)} reports   terminal reasons "
                   f"{dict(sorted(reasons.items()))}")
        _, excluded = census(rs, ALL_TIERS)
        if excluded:
            out.append("  EXCLUDED CELLS (not counted anywhere below):")
            for (_, g, s), why in excluded:
                out.append(f"    {g}__{s}: {why}")
        out.append("")
        out.append(f"  {'game':<15}{'tier set':<24}{'paired':>7}{'v-diff':>8}"
                   f"{'rate':>9}{'e-diff':>8}{'unpaired':>10}")
        for tiers, label in ((("programmatic",), "programmatic"),
                             (("playbot",), "playbot"),
                             (("judge",), "judge (weight 0.00)"),
                             (DETERMINISTIC, "DETERMINISTIC")):
            per, _ = census(rs, tiers)
            for (_, g), c in sorted(per.items()):
                out.append(f"  {g:<15}{label:<24}{c.paired:>7}{c.verdict_diff:>8}"
                           f"{_pct(c)}{c.evidence_diff:>8}{c.unpaired_criteria:>10}")
            out.append("")
        for tiers, label in ((DETERMINISTIC, "DETERMINISTIC (programmatic+playbot)"),
                             (ALL_TIERS, "ALL TIERS (incl. judge, weight 0.00)")):
            per, _ = census(rs, tiers)
            tot = Counts()
            for c in per.values():
                tot = tot.add(c)
            out.append(f"  POOLED ACROSS {len(per)} GAME(S), {label}: "
                       f"{tot.paired} paired, {tot.verdict_diff} verdict differences, "
                       f"{tot.evidence_diff} evidence differences")
        out.append("    ^ a COUNT, not a rate. eval/RUNS.md bans pooling across games:")
        out.append("      the criterion count differs per game, so a pooled rate weights")
        out.append("      the game with most criteria hardest. Quote the per-game rows.")
        det, _ = census(rs, DETERMINISTIC)
        alt, _ = census(rs, ALL_TIERS)
        dp = sum(c.paired for c in det.values())
        ap = sum(c.paired for c in alt.values())
        if ap:
            out.append(f"    ^ {ap - dp} of those {ap} paired criteria "
                       f"({(ap - dp) / ap * 100:.1f}%) are LLM-judge criteria at "
                       f"weight 0.00.")
        out.append("")
        for d in sorted(c for cs in det.values() for c in cs.diffs):
            out.append(f"    DETERMINISTIC verdict difference: {d[1]}__{d[2]}  "
                       f"{d[3]}:{d[4]}")
        out.append("")
    return "\n".join(out)


# --------------------------------------------------------------------------- #
# selftest: prove the extraction on cases whose answers are stated in advance
# --------------------------------------------------------------------------- #

_FAILED = 0
_RUN = 0


def expect(name: str, cond: bool, detail: str = "") -> None:
    global _FAILED, _RUN
    _RUN += 1
    if not cond:
        _FAILED += 1
    print(f"  {'ok  ' if cond else 'FAIL'}  {name}" + (f"   [{detail}]" if detail else ""))


def _write(root: Path, run: str, game: str, stack: str, slot: str,
           tiers: dict[str, list[tuple[str, bool, str]]], reason: str | None) -> None:
    tid = f"{game}__{stack}__{slot}"
    d = root / run / "artifacts" / tid / "eval"
    d.mkdir(parents=True, exist_ok=True)
    rec = {t: {"criteria": [{"id": i, "passed": p, "evidence": e} for i, p, e in cs]}
           for t, cs in tiers.items()}
    (d / "report.json").write_text(json.dumps(rec))
    if reason is not None:
        td = root / run / "trials"
        td.mkdir(parents=True, exist_ok=True)
        (td / f"{tid}.json").write_text(
            json.dumps({"agent": {"terminal_reason": reason}}))


def _synthetic(root: Path) -> None:
    """Every fixture below has its answer stated in the expectation that reads it."""
    # r1: one cell, four playbot criteria - one agreeing pass, one agreeing fail, one
    # verdict difference, one same-verdict-different-evidence.
    _write(root, "r1", "g1", "s1", "t0", {"playbot": [
        ("a", True, "E"), ("b", False, "E"), ("c", True, "E"), ("d", True, "X")]},
        "completed")
    _write(root, "r1", "g1", "s1", "t1", {"playbot": [
        ("a", True, "E"), ("b", False, "E"), ("c", False, "E"), ("d", True, "Y")]},
        "completed")
    # r2: a criterion only ONE trial recorded.
    _write(root, "r2", "g1", "s1", "t0", {"playbot": [("a", True, "E")]}, "completed")
    _write(root, "r2", "g1", "s1", "t1", {"playbot": [
        ("a", True, "E"), ("newcrit", False, "E")]}, "completed")
    # r3: the disagreement lives in the judge tier only.
    _write(root, "r3", "g1", "s1", "t0",
           {"playbot": [("a", True, "E")], "judge": [("j", True, "E")]}, "completed")
    _write(root, "r3", "g1", "s1", "t1",
           {"playbot": [("a", True, "E")], "judge": [("j", False, "E")]}, "completed")
    # r4: one cell cut off at max_turns, one with no trial JSON at all.
    _write(root, "r4", "g1", "s1", "t0", {"playbot": [("a", True, "E")]}, "completed")
    _write(root, "r4", "g1", "s1", "t1", {"playbot": [("a", False, "E")]}, "max_turns")
    _write(root, "r4", "g1", "s2", "t0", {"playbot": [("a", True, "E")]}, None)
    _write(root, "r4", "g1", "s2", "t1", {"playbot": [("a", False, "E")]}, None)
    # r5: one trial is not a pair.
    _write(root, "r5", "g1", "s1", "t0", {"playbot": [("a", True, "E")]}, "completed")
    # r6/armA: a run nested one level deeper, like wg-g4c-capgate's arms.
    _write(root, "r6/armA", "g1", "s1", "t0", {"playbot": [("a", True, "E")]},
           "completed")
    _write(root, "r6/armA", "g1", "s1", "t1", {"playbot": [("a", False, "E")]},
           "completed")


def _synthetic_checks(root: Path) -> None:
    per, exc = census(load(root, "r1"), DETERMINISTIC)
    c = per[("r1", "g1")]
    expect("POSITIVE: 4 paired criteria are found", c.paired == 4, f"{c.paired}")
    expect("MUTANT: the flipped verdict is counted, exactly once",
           c.verdict_diff == 1, f"{c.verdict_diff}")
    expect("VARIANT: same verdict, different evidence is NOT a verdict difference",
           c.evidence_diff == 1
           and ("r1", "g1", "s1", "playbot", "d") not in c.diffs,
           f"evidence_diff={c.evidence_diff} diffs={c.diffs}")
    expect("the differing criterion is NAMED, not only counted",
           c.diffs == [("r1", "g1", "s1", "playbot", "c")], f"{c.diffs}")
    expect("no cell is excluded when both trials completed", exc == [], f"{exc}")

    # Counting an unpaired criterion would report a SUITE CHANGE as a verdict
    # difference - the failure that inflates the floor whenever a criterion is added
    # between the two gradings of a cell.
    c = census(load(root, "r2"), DETERMINISTIC)[0][("r2", "g1")]
    expect("VARIANT: a criterion recorded by only one trial is not a difference",
           c.paired == 1 and c.verdict_diff == 0,
           f"paired={c.paired} v={c.verdict_diff}")
    expect("...and it is reported as unpaired rather than dropped silently",
           c.unpaired_criteria == 1, f"{c.unpaired_criteria}")

    rows3 = load(root, "r3")
    det = census(rows3, DETERMINISTIC)[0][("r3", "g1")]
    allt = census(rows3, ALL_TIERS)[0][("r3", "g1")]
    expect("MUTANT: a judge-only disagreement is invisible to the deterministic set",
           det.paired == 1 and det.verdict_diff == 0,
           f"paired={det.paired} v={det.verdict_diff}")
    expect("...and IS counted under ALL_TIERS - the tier set changes the answer",
           allt.paired == 2 and allt.verdict_diff == 1,
           f"paired={allt.paired} v={allt.verdict_diff}")

    per4, exc4 = census(load(root, "r4"), DETERMINISTIC)
    expect("MUTANT: a cell holding a max_turns trial is excluded, not counted",
           per4 == {} and len(exc4) == 2, f"per={per4} excluded={exc4}")
    expect("...and a missing trial JSON reads `unknown`, never `completed`",
           any("unknown" in why for _, why in exc4), f"{exc4}")

    per5, exc5 = census(load(root, "r5"), DETERMINISTIC)
    expect("MUTANT: a one-trial cell is excluded and the reason is reported",
           per5 == {} and exc5 and "1 trial" in exc5[0][1], f"{exc5}")

    found = {r["run"] for r in load(root)}
    expect("a run nested one level deeper is found, not skipped",
           "r6/armA" in found, f"{sorted(found)}")

    txt = render(load(root, "r3"))
    expect("the pooled row is labelled a COUNT, not a rate",
           "a COUNT, not a rate" in txt)
    expect("the judge share of the ALL_TIERS denominator is stated",
           "are LLM-judge criteria at weight 0.00" in txt)


#: The published figures, and the tier set each is actually computed over. These pin the
#: reverse-engineering this module exists to retire: `436` reproduces ONLY by summing all
#: three tiers, and the deterministic-only recount of the same run is 280/4.
PINS = (
    ("wg-matrix-2026-08-13T14-02-50", ALL_TIERS, (436, 5, 332)),
    ("wg-audio48-2026-08-14T19-55-47", ALL_TIERS, (232, 0, 120)),
    ("wg-matrix-2026-08-13T14-02-50", DETERMINISTIC, (280, 4, 176)),
    ("wg-audio48-2026-08-14T19-55-47", DETERMINISTIC, (232, 0, 120)),
)


def _corpus_pins(runs_root: Path) -> int:
    rows = load(runs_root)
    if not rows:
        expect("--runs-root holds at least one report.json", False,
               f"{runs_root} is empty; the pins measured nothing")
        return 0
    pins = 0
    for run, tiers, want in PINS:
        rs = [r for r in rows if r["run"] == run]
        name = "ALL_TIERS" if tiers == ALL_TIERS else "DETERMINISTIC"
        if not rs:
            expect(f"PIN {run} {name}", False, "run not present under --runs-root")
            continue
        per, _ = census(rs, tiers)
        tot = Counts()
        for c in per.values():
            tot = tot.add(c)
        got = (tot.paired, tot.verdict_diff, tot.evidence_diff)
        pins += 1
        expect(f"PIN {run} {name} == {want}", got == want, f"got {got}")
    # The discriminating pin. Were these equal, the tier set would not matter and the
    # first refusal in this module's docstring would be decoration.
    m = [r for r in rows if r["run"] == "wg-matrix-2026-08-13T14-02-50"]
    if m:
        a = sum(c.paired for c in census(m, ALL_TIERS)[0].values())
        d = sum(c.paired for c in census(m, DETERMINISTIC)[0].values())
        pins += 1
        expect("PIN the tier set changes wg-matrix's denominator by 156 criteria",
               a - d == 156, f"all={a} det={d} delta={a - d}")
    return pins


def selftest(runs_root: Path | None) -> int:
    print("paired_verdicts selftest")
    print(" SYNTHETIC: every answer stated in the expectation that reads it")
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        _synthetic(root)
        _synthetic_checks(root)
    if runs_root is None:
        pins = 0
        print(" CORPUS PINS: NOT RUN - pass --runs-root to run them")
    else:
        print(f" CORPUS PINS against {runs_root}")
        pins = _corpus_pins(runs_root)
    print(f"paired_verdicts selftest: {_RUN - _FAILED}/{_RUN} checks passed, "
          f"{pins} corpus pins")
    return 1 if _FAILED else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--runs-root", type=Path,
                    help="the MAIN CHECKOUT's eval/runs. Never guessed: see the docstring")
    ap.add_argument("--run", help="limit to one run directory name")
    a = ap.parse_args()
    if a.selftest:
        return selftest(a.runs_root)
    if a.runs_root is None:
        ap.error("--runs-root is required (or --selftest)")
    rows = load(a.runs_root, a.run)
    if not rows:
        print(f"no report.json under {a.runs_root}"
              + (f" for run {a.run!r}" if a.run else ""), file=sys.stderr)
        return 2
    print(render(rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
