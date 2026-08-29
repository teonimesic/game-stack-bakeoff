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
   12 of 140 - 8.57%, THREE times the 2.86% that is the highest rate any real cell pair
   shows. Whatever they are, they are not two independent trials, and pooling them would
   raise the floor with copies.

   This said "six times" until it was re-derived, and the error is refusal 2 above being
   broken by the sentence that explains refusal 3: six is 12 against 2, the largest
   verdict-diff COUNT elsewhere, over denominators of 140 and 88.

A criterion recorded by only ONE trial of a pair is not a difference and is not counted;
it is a suite change between the two gradings, reported as `unpaired-criteria`. A record
one trial made but could not score - `id` without `passed` - is still a record: it is
named on the skip list and does not read as a suite change.

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

A record the walk REACHES but cannot classify is not dropped silently either: a report
whose trial id is not a usable `game__stack__slot` (wrong number of parts, or a part
empty), a report that does not decode or is not a mapping, and a tier block or
criterion of the wrong shape or carrying `id` without `passed`, are counted as skips
and named beside the excluded cells - the rule `capability.no_stack_correlated_gap`
enforces elsewhere, that a record the module cannot name is a counted problem with
its name attached. None reaches `paired`, a cell, or a verdict or evidence
difference; the unpaired count stays about the suites. Both channels were empty over
the stored tree when measured (2026-08-29, 85 reports walked); this is the channel
closed before a future run directory - judge packs land inside run directories
(#83) - puts a differently-shaped directory under `artifacts/` and narrows the floor
in silence.
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


def load(runs_root: Path, only_run: str | None = None
         ) -> tuple[list[dict], list[tuple[str, str]]]:
    """Every stored report, with its criteria keyed by (tier, id).

    Returns `(rows, skips)`. A skip is a record the walk REACHED and could not
    classify, named so it cannot be dropped silently - the rule
    `capability.no_stack_correlated_gap` enforces elsewhere: a record the module
    cannot name is a counted problem with its name attached. The classes:

      - a report whose trial id is not a usable `game__stack__slot` - the wrong
        number of parts, or a part empty, so no cell can hold it: nothing can
        say which game and stack it belongs to;
      - a report that does not decode, or is not a mapping - no tier can be
        asked anything of it;
      - a tier block that is not a mapping with a `criteria` list - the tier
        is not read;
      - a criterion that is not a mapping, or carries `id` without `passed`
        (or the reverse) - it has no verdict to pair. A named one joins the
        row's `skipped_crits`, so `count_cell` can tell a malformed record
        from a suite change; one with no `id` has no key and lives only on
        this list.

    No class reaches `paired`, a cell, or a verdict or evidence difference.
    The unpaired count is about the SUITES, not the records: a criterion one
    trial recorded and the other never did stays a suite difference whatever
    became of the record, and the skip line classifies the record without
    editing that count. `render()` prints every skip beside the excluded
    cells.
    """
    rows: list[dict] = []
    skips: list[tuple[str, str]] = []
    for rep in sorted(runs_root.glob("**/artifacts/*/eval/report.json")):
        run_root = rep.parent.parent.parent.parent
        run = str(run_root.relative_to(runs_root))
        if only_run is not None and run != only_run:
            continue
        tid = rep.parent.parent.name
        parts = tid.split("__")
        if len(parts) != 3 or not all(parts):
            skips.append((run, f"{tid}: trial id is not 3 non-empty `__`-separated "
                          f"parts (game__stack__slot) - walked, reaches no cell"))
            continue
        game, stack, slot = parts
        try:
            rec = json.loads(rep.read_text())
        except (OSError, ValueError) as e:
            skips.append((run, f"{tid}: report.json does not decode: "
                          f"{type(e).__name__}: {str(e)[:100]} - walked, "
                          f"reaches no row"))
            continue
        if not isinstance(rec, dict):
            skips.append((run, f"{tid}: report.json is a `{type(rec).__name__}`, "
                          f"not a mapping - walked, reaches no row"))
            continue
        crits = {}
        skipped_crits: set[tuple[str, str]] = set()
        for tier in ALL_TIERS:
            block = rec.get(tier)
            if block is None:
                continue
            if not isinstance(block, dict):
                skips.append((run, f"{tid} {tier}: tier block is a "
                              f"`{type(block).__name__}`, not a mapping with "
                              f"`criteria` - tier not read"))
                continue
            criteria = block.get("criteria")
            if not isinstance(criteria, list):
                got = "absent or null" if criteria is None \
                    else f"a `{type(criteria).__name__}`"
                skips.append((run, f"{tid} {tier}: `criteria` is {got}, "
                              f"not a list - tier not read"))
                continue
            for c in criteria:
                if not isinstance(c, dict):
                    skips.append((run, f"{tid} {tier}: criterion is a "
                                  f"`{type(c).__name__}`, not a mapping - no "
                                  f"verdict to pair"))
                    continue
                if "id" in c and "passed" in c:
                    if not isinstance(c["id"], str):
                        # `true` and `1` hash the same, a list or dict hashes
                        # not at all: a non-string id must not key a pair.
                        skips.append((run, f"{tid} {tier}: criterion `id` is a "
                                      f"`{type(c['id']).__name__}`, not a "
                                      f"string - no verdict to pair"))
                        continue
                    crits[(tier, c["id"])] = (bool(c["passed"]), c.get("evidence", ""))
                else:
                    missing = [k for k in ("id", "passed") if k not in c]
                    label = c["id"] if "id" in c else "<no id>"
                    skips.append((run, f"{tid} {tier}:{label}: criterion carries no "
                                  f"`{'` and no `'.join(missing)}` - no verdict "
                                  f"to pair"))
                    if "id" in c and isinstance(c["id"], str):
                        skipped_crits.add((tier, c["id"]))
        rows.append({"run": run, "tid": tid, "game": game, "stack": stack, "slot": slot,
                     "terminal_reason": _terminal_reason(run_root, tid), "crits": crits,
                     "skipped_crits": skipped_crits})
    return rows, skips


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
    # `unpaired` means the two gradings recorded different suites - RECORDED,
    # not scoreable. A record one trial made but could not score - `id` without
    # `passed` - is still a record: it joins the key set for this comparison
    # (named on the skip list at load), so a criterion both trials recorded
    # never reads as a suite change just because one record is malformed. A
    # criterion the other trial never recorded at all stays a suite difference.
    ka_all = ka | {k for k in cell[0]["skipped_crits"] if k[0] in tiers}
    kb_all = kb | {k for k in cell[1]["skipped_crits"] if k[0] in tiers}
    c = Counts(unpaired_criteria=len(ka_all ^ kb_all))
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


def render(rows: list[dict], skips: list[tuple[str, str]]) -> str:
    out: list[str] = []
    for run in sorted({r["run"] for r in rows} | {s for s, _ in skips}):
        rs = [r for r in rows if r["run"] == run]
        run_skips = [d for s, d in skips if s == run]
        reasons: dict[str, int] = {}
        for r in rs:
            reasons[r["terminal_reason"]] = reasons.get(r["terminal_reason"], 0) + 1
        out.append(f"=== {run} ===")
        out.append(f"  {len(rs)} reports   terminal reasons "
                   f"{dict(sorted(reasons.items()))}")
        if run_skips:
            out.append(f"  SKIPPED AT LOAD (walked, not counted anywhere below): "
                       f"{len(run_skips)} record(s)")
            for d in run_skips:
                out.append(f"    {d}")
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


def _write_raw(root: Path, run: str, tid: str, rec: dict,
               reason: str | None) -> None:
    """A report written exactly as given - for fixtures that must be malformed."""
    d = root / run / "artifacts" / tid / "eval"
    d.mkdir(parents=True, exist_ok=True)
    (d / "report.json").write_text(json.dumps(rec))
    if reason is not None:
        td = root / run / "trials"
        td.mkdir(parents=True, exist_ok=True)
        (td / f"{tid}.json").write_text(
            json.dumps({"agent": {"terminal_reason": reason}}))


def _write(root: Path, run: str, game: str, stack: str, slot: str,
           tiers: dict[str, list[tuple[str, bool, str]]], reason: str | None) -> None:
    tid = f"{game}__{stack}__{slot}"
    _write_raw(root, run, tid,
               {t: {"criteria": [{"id": i, "passed": p, "evidence": e} for i, p, e in cs]}
                for t, cs in tiers.items()}, reason)


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
    # r7: reports the walk REACHES whose trial id is not a usable
    # game__stack__slot - a 1-part tid, and a 3-part tid whose game field is
    # empty. No trial JSON: load() must classify the tid before it ever reads a
    # reason.
    _write_raw(root, "r7", "weird-tid",
               {"playbot": {"criteria": [{"id": "a", "passed": True, "evidence": "E"}]}},
               None)
    _write_raw(root, "r7", "__s1__t0",
               {"playbot": {"criteria": [{"id": "a", "passed": True, "evidence": "E"}]}},
               None)
    # r8: one cell; `bad` carries `id` without `passed` on BOTH sides - named
    # twice on the skip list, in no denominator.
    _write_raw(root, "r8", "g1__s1__t0",
               {"playbot": {"criteria": [
                   {"id": "a", "passed": True, "evidence": "E"},
                   {"id": "bad", "evidence": "E"}]}}, "completed")
    _write_raw(root, "r8", "g1__s1__t1",
               {"playbot": {"criteria": [
                   {"id": "a", "passed": True, "evidence": "E"},
                   {"id": "bad", "evidence": "E"}]}}, "completed")
    # r9: `half` is well-formed on t0 and carries `id` without `passed` on t1 -
    # one named skip, and no suite change.
    _write_raw(root, "r9", "g1__s1__t0",
               {"playbot": {"criteria": [{"id": "half", "passed": False, "evidence": "E"}]}},
               "completed")
    _write_raw(root, "r9", "g1__s1__t1",
               {"playbot": {"criteria": [{"id": "half", "evidence": "E"}]}}, "completed")
    # r10: t0 recorded `solo` and a malformed `broken`; t1's grading recorded
    # neither. Both criteria sit in exactly one grading's suite - a suite
    # difference each - whatever became of the records; `broken`'s own
    # classification is the skip line, not an edit to this count.
    _write_raw(root, "r10", "g1__s1__t0",
               {"playbot": {"criteria": [
                   {"id": "solo", "passed": True, "evidence": "E"},
                   {"id": "broken", "evidence": "E"}]}}, "completed")
    _write_raw(root, "r10", "g1__s1__t1",
               {"playbot": {"criteria": []}}, "completed")
    # r11: three reports the walk reaches that no classification can save - a
    # file that does not decode, a top-level array, and a null inside a
    # readable report's criteria. Each is a named skip; none aborts the walk,
    # and the one readable criterion beside the null still lands.
    _bad = root / "r11" / "artifacts" / "g1__s1__t0" / "eval"
    _bad.mkdir(parents=True)
    (_bad / "report.json").write_text("{not json")
    _arr = root / "r11" / "artifacts" / "g2__s1__t0" / "eval"
    _arr.mkdir(parents=True)
    (_arr / "report.json").write_text("[]")
    _write_raw(root, "r11", "g3__s1__t0",
               {"playbot": {"criteria": [None, {"id": "ok", "passed": True, "evidence": "E"}]}},
               None)
    # r12: tier blocks and criterion ids the schema does not allow - `criteria`
    # missing, null, and a string; ids that are a list and the integer 1, which
    # would hash-collide with a boolean id. Each is a named skip; an empty
    # `criteria` list stays a silent no (pinned by r10's t1).
    _write_raw(root, "r12", "g1__s1__t0", {"playbot": {}}, "completed")
    _write_raw(root, "r12", "g2__s1__t0", {"playbot": {"criteria": None}}, "completed")
    _write_raw(root, "r12", "g3__s1__t0", {"playbot": {"criteria": "oops"}}, "completed")
    _write_raw(root, "r12", "g4__s1__t0",
               {"playbot": {"criteria": [{"id": ["a"], "passed": True},
                                         {"id": 1, "passed": True}]}}, "completed")


def _synthetic_checks(root: Path) -> None:
    per, exc = census(load(root, "r1")[0], DETERMINISTIC)
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
    c = census(load(root, "r2")[0], DETERMINISTIC)[0][("r2", "g1")]
    expect("VARIANT: a criterion recorded by only one trial is not a difference",
           c.paired == 1 and c.verdict_diff == 0,
           f"paired={c.paired} v={c.verdict_diff}")
    expect("...and it is reported as unpaired rather than dropped silently",
           c.unpaired_criteria == 1, f"{c.unpaired_criteria}")

    rows3 = load(root, "r3")[0]
    det = census(rows3, DETERMINISTIC)[0][("r3", "g1")]
    allt = census(rows3, ALL_TIERS)[0][("r3", "g1")]
    expect("MUTANT: a judge-only disagreement is invisible to the deterministic set",
           det.paired == 1 and det.verdict_diff == 0,
           f"paired={det.paired} v={det.verdict_diff}")
    expect("...and IS counted under ALL_TIERS - the tier set changes the answer",
           allt.paired == 2 and allt.verdict_diff == 1,
           f"paired={allt.paired} v={allt.verdict_diff}")

    per4, exc4 = census(load(root, "r4")[0], DETERMINISTIC)
    expect("MUTANT: a cell holding a max_turns trial is excluded, not counted",
           per4 == {} and len(exc4) == 2, f"per={per4} excluded={exc4}")
    expect("...and a missing trial JSON reads `unknown`, never `completed`",
           any("unknown" in why for _, why in exc4), f"{exc4}")

    per5, exc5 = census(load(root, "r5")[0], DETERMINISTIC)
    expect("MUTANT: a one-trial cell is excluded and the reason is reported",
           per5 == {} and exc5 and "1 trial" in exc5[0][1], f"{exc5}")

    # A report the walk REACHES but cannot classify - a trial id that is not
    # game__stack__slot - is counted and NAMED, never dropped silently. The 2-part
    # tid is red because it is COUNTED: were `rows == []` the only expectation, a
    # walker that stopped globbing would pass this fixture too.
    rows7, skips7 = load(root, "r7")
    expect("MUTANT: a trial id without a usable game__stack__slot reaches no cell",
           rows7 == [], f"{rows7}")
    expect("...and the walk names both: a 1-part tid and an empty game field",
           len(skips7) == 2 and all(s == "r7" for s, _ in skips7)
           and all("game__stack__slot" in d for _, d in skips7)
           and any("weird-tid" in d for _, d in skips7)
           and any("__s1__t0" in d for _, d in skips7),
           f"{skips7}")

    # A criterion carrying `id` without `passed` has no verdict to pair. On BOTH
    # sides of a cell it must land somewhere stated - it vanishes from paired AND
    # unpaired today. It reaches no denominator (there is no verdict to disagree
    # with) and it is NAMED, once per side, where the module reports.
    rows8, skips8 = load(root, "r8")
    c8 = census(rows8, DETERMINISTIC)[0][("r8", "g1")]
    expect("POSITIVE: the well-formed criterion beside the malformed one still pairs",
           c8.paired == 1 and c8.verdict_diff == 0,
           f"paired={c8.paired} v={c8.verdict_diff}")
    expect("MUTANT: a no-`passed` criterion on BOTH sides reaches no denominator",
           c8.unpaired_criteria == 0, f"unpaired={c8.unpaired_criteria}")
    expect("...and BOTH sides are named on the skip list, with tier and id",
           len(skips8) == 2
           and all("g1__s1__t" in d and "playbot:bad" in d for _, d in skips8),
           f"{skips8}")
    txt8 = render(rows8, skips8)
    expect("...and render() counts and names the skip beside the excluded cells",
           "SKIPPED AT LOAD" in txt8 and "playbot:bad" in txt8, "")

    # One well-formed side and one malformed side is NOT a suite change - the
    # grading suite did not change; one record of it cannot be scored. unpaired
    # goes back to 0 and the MALFORMED side is the side named.
    rows9, skips9 = load(root, "r9")
    c9 = census(rows9, DETERMINISTIC)[0][("r9", "g1")]
    expect("VARIANT: one malformed side is not mislabelled a suite change",
           c9.unpaired_criteria == 0 and c9.paired == 0,
           f"paired={c9.paired} unpaired={c9.unpaired_criteria}")
    expect("...and the malformed side is the one named",
           len(skips9) == 1 and "g1__s1__t1" in skips9[0][1]
           and "playbot:half" in skips9[0][1], f"{skips9}")

    # A criterion one grading recorded and the other never did is a suite
    # difference - RECORDED is the column's definition, and the malformed record
    # was still a record. Removing only the opposite-side skips from valid keys
    # here would return 1 and hide `broken` entirely; the stated answer is 2.
    rows10, skips10 = load(root, "r10")
    c10 = census(rows10, DETERMINISTIC)[0][("r10", "g1")]
    expect("POSITIVE: a suite difference stays counted when the one side that "
           "recorded it recorded it malformed",
           c10.unpaired_criteria == 2 and c10.paired == 0,
           f"paired={c10.paired} unpaired={c10.unpaired_criteria}")
    expect("...and the malformed record is named while the count stands",
           len(skips10) == 1 and "g1__s1__t0" in skips10[0][1]
           and "playbot:broken" in skips10[0][1], f"{skips10}")

    # One unreadable report must not abort the walk for every other run in the
    # tree - and must not vanish either: each is a named skip, the same rule as
    # every other record the module cannot classify.
    rows11, skips11 = load(root, "r11")
    expect("MUTANT: an undecodable report and a top-level array reach no row, "
           "the readable one beside them still lands",
           [r["tid"] for r in rows11] == ["g3__s1__t0"]
           and ("playbot", "ok") in rows11[0]["crits"], f"{rows11}")
    expect("...and all three are named: decode, shape, and the null criterion",
           len(skips11) == 3
           and any("g1__s1__t0" in d and "does not decode" in d for _, d in skips11)
           and any("g2__s1__t0" in d and "not a mapping" in d for _, d in skips11)
           and any("g3__s1__t0" in d and "NoneType" in d and "playbot" in d
                   for _, d in skips11), f"{skips11}")

    # A tier block whose `criteria` is absent or null is a broken record, not an
    # empty suite, and an id that is not a string cannot key a pair - `true`
    # and `1` hash the same, so counting either would let two different
    # records share one key. Named, each; the walk continues.
    rows12, skips12 = load(root, "r12")
    expect("MUTANT: four malformed tier blocks and ids reach no denominator",
           all(r["crits"] == {} for r in rows12) and len(rows12) == 4,
           f"{rows12}")
    expect("...and all five records are named",
           len(skips12) == 5
           and sum("absent or null" in d for _, d in skips12) == 2
           and any("g3__s1__t0" in d and "`str`" in d for _, d in skips12)
           and any("`list`" in d and "not a string" in d for _, d in skips12)
           and any("`int`" in d and "not a string" in d for _, d in skips12),
           f"{skips12}")

    rows_all, skips_all = load(root)
    found = {r["run"] for r in rows_all}
    expect("a run nested one level deeper is found, not skipped",
           "r6/armA" in found, f"{sorted(found)}")
    expect("the walk's own accounting states every skip it made: 14 over this tree",
           len(skips_all) == 14, f"{sorted(skips_all)}")
    txt_all = render(rows_all, skips_all)
    expect("a run holding ONLY a skipped report still gets its section",
           "=== r7 ===" in txt_all and "weird-tid" in txt_all, "")

    rows3r, skips3r = load(root, "r3")
    txt = render(rows3r, skips3r)
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
    rows, skips = load(runs_root)
    if skips:
        print(f"  note: the stored tree holds {len(skips)} skipped record(s):")
        for s, d in skips:
            print(f"    {s}: {d}")
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
    rows, skips = load(a.runs_root, a.run)
    if not rows and not skips:
        print(f"no report.json under {a.runs_root}"
              + (f" for run {a.run!r}" if a.run else ""), file=sys.stderr)
        return 2
    print(render(rows, skips))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
