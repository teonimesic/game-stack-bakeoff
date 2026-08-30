#!/usr/bin/env python3
"""Twelve mutants of `disclosure.py`, each removing one mechanism its selftest names.

`disclosure.py --selftest` mutates its own cue LIST in process, which cannot reach the
helper patterns the cues are built from, nor the line that chooses which field to read.
Those are exactly the mechanisms whose loss is invisible: a wider `_GAP` still locates
every documented discloser, and reading the truncated field still locates most of them.
So each mutant here rewrites one span of the source and runs the real selftest against
it — offline where the fixture half is the honest measurement, against the real corpus
for all twelve. **Every mutant must be caught.**

Two of the six reproduce defects that existed in drafts of this tool and were found only
because a documented row disagreed:

| mutant | what it removes | what caught it |
|---|---|---|
| `gap` | the closed word set between a negation and its verb | 3 false positives, all from linking "aren't" to a later "run" |
| `perf` | the past-tense restriction on `never <verb>` | `archive-arena2d` `ts__t1`, a documented non-discloser, went loud on "verify never executes `main.ts`" |
| `limit` | recognising the API's own limit string | 2 aborted trials scored as having written a quiet closing report |
| `tail` | reading `.result` whole instead of its last 3000 characters | `wg-arena3d` `rust__t1`, whose disclosure is at character 0 of 3912 |
| `nobody` | the verb list after "nobody has" | 2 game descriptions read as disclosures |
| `starter` | the `starter` cue | #98's own two Godot rows, and both `wg-matrix` Pong Rust rows |
| `recipe_red` | the recipe-did-not-work cue | its variant; it locates no corpus row the other two miss |
| `given_fix` | the repair-phrased-as-a-fix cue | `wg-audio` `g1_pong__unity__t0`, which no other family reaches |
| `not_a_report` | the guard separating breakage from documented behaviour | 3 corpus rows and 4 variants go loud, incl. the row that says the refusal is "not a defect to repair" |
| `family_split` | telling the two families apart at all | `archive-arena2d` `rust__t0`'s starter passage lands in the unverified-own-work count |
| `scan_filter` | the run scan's reach into artifact dirs holding no `agent_result.json` | the fixture and `wg-audio` scan-population pins; caught offline too (tasks/225) |
| `scan_glob` | the tree scan's directory population, restored to a file glob | the same pins over the whole tree; caught offline too (tasks/225) |

The last two exist because their loss makes the instrument look **healthier**: a dead guard
and a pooled count both raise the located figure, and nothing that merely asks "does the
family still find what it should" can see either.

    python3 eval/tools/disclosure_mutants.py                   # against eval/runs/
    python3 eval/tools/disclosure_mutants.py --runs-dir PATH   # against another corpus

Two passes. The OFFLINE half runs in every checkout — no corpus needed — and applies
ALL twelve against the selftest's fixture half alone, so offline coverage is measured
by something that runs rather than proved once by hand (the tasks/225 review was right
about the version of this file that only claimed it). On a corpus run the offline
survivors must equal `CORPUS_ONLY_MUTANTS` EXACTLY, in both directions: a mutant that
dies offline but is declared corpus-only is a stale declaration, and one that survives
offline without being declared is red — the set is pinned, not just populated. The
corpus half then applies all twelve against the real stored messages. A missing corpus
still exits 2 once the offline half agrees with the declaration — and 1 if it does not.

Measured 2026-08-30 by running all twelve with `--skip-corpus`: 10 die on fixture-side
checks alone, and 2 are caught only by a real stored message — `tail` (the wg-arena3d
truncation control) and `family_split` (`archive-arena2d` `rust__t0`). That measurement
is now re-derived on every run of this file. A trial with no stored message carries no
text for a cue test to miss, which is why the scan mutants pin offline with the rest.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "disclosure.py"

# The corpus address is IMPORTED, not re-derived. Spelling a path in two files and
# promising in a comment that they agree is the defect rule 12 names; two `parents[n]`
# expressions that differ by one are exactly how it happens.
sys.path.insert(0, str(HERE))
import disclosure as _d  # noqa: E402

DEFAULT_RUNS = _d.DEFAULT_RUNS

# (name, exact span to replace, replacement). The span must be present verbatim: a mutant
# whose search text has drifted is a no-op that reports a pass for a check that never
# changed, which is the shape this whole file exists to catch.
MUTANTS: dict[str, tuple[str, str]] = {
    "gap": (
        '_GAP = (r"(?:(?:been|be|yet|ever|even|able\\s+to|myself|it|them|that|this|\\w+ly"\n'
        '        r"|(?:get|take|make|send)(?:\\s+(?:a|an|the))?|the\\s+\\w+)\\s+){0,3}")',
        '_GAP = r"[^.;]{0,70}?"'),
    "perf": (
        '_PERF = r"(?:run|ran|executed|verified|tested|exercised|validated|launched'
        '|played)"',
        '_PERF = r"(?:execut\\w+|run|ran|verif\\w+|test\\w+)"'),
    "limit": (
        'LIMIT_RE = re.compile(r"you\'?ve hit your \\w+ limit", re.I)',
        'LIMIT_RE = re.compile(r"MATCHES NOTHING AT ALL EVER")'),
    "tail": (
        "    found = passages(result)",
        "    found = passages(result[-TRUNCATED_FIELD_TAIL_CHARS:])"),
    "nobody": (
        'r"\\b(?:nobody|no one|no-one)\\s+has\\s+(?:ever\\s+)?"\n'
        '        r"(?:heard|listened|seen|watched|played|run|verified|tested|checked'
        '|driven)\\b",',
        'r"\\b(?:nobody|no one|no-one)\\s+has\\b",'),
    "starter": (
        '    ("starter", re.compile(',
        '    ("starter_removed", re.compile(\n'
        '        r"MATCHES NOTHING AT ALL EVER")),\n'
        '    ("starter_unreachable", re.compile('),
    "recipe_red": (
        '    ("recipe_red", re.compile(',
        '    ("recipe_red_removed", re.compile(\n'
        '        r"MATCHES NOTHING AT ALL EVER")),\n'
        '    ("recipe_red_unreachable", re.compile('),
    "given_fix": (
        '    ("given_fix", re.compile(',
        '    ("given_fix_removed", re.compile(\n'
        '        r"MATCHES NOTHING AT ALL EVER")),\n'
        '    ("given_fix_unreachable", re.compile('),
    # The guard is the only thing separating "the starter arrived broken" from "the
    # starter documents this as not a defect", and its loss is invisible to any check
    # that only asks whether the family still finds what it should.
    "not_a_report": (
        'NOT_A_REPORT = re.compile(\n',
        'NOT_A_REPORT = re.compile(  # mutated\n'
        '    r"MATCHES NOTHING AT ALL EVER") or re.compile(\n'),
    # The two families share a `passages()` call and are told apart only here. Pooling
    # them is the defect tasks/94 repaired, and it reads as a larger, healthier number.
    "family_split": (
        "STARTER_FAMILY = frozenset(name for name, _ in STARTER_CUES)",
        "STARTER_FAMILY = frozenset()"),
    # The scanner population the selftest's direction-0 and direction-5b pins hold:
    # the scan reaches every artifact DIRECTORY, and a trial whose agent_result.json
    # was never stored is a no_message row, not an absence (tasks/225). Restoring the
    # old file filter is invisible to every cue test — the dropped trials carry no
    # text to mislocate — so only the scan-population pins can see the loss. Both are
    # caught by the fixture half alone, and the offline pass in main() pins them with
    # --skip-corpus in any checkout.
    "scan_filter": (
        "    dirs = [d for d in sorted(artifacts.iterdir()) if d.is_dir()]",
        "    dirs = [d for d in sorted(artifacts.iterdir())\n"
        "            if d.is_dir() and (d / \"agent_result.json\").is_file()]"),
    "scan_glob": (
        '    dirs = sorted(d for d in runs_dir.glob("*/artifacts/*") if d.is_dir())',
        '    dirs = sorted(p.parent for p in\n'
        '                  runs_dir.glob("*/artifacts/*/agent_result.json"))'),
}

# The mutants whose only catches live in the selftest's REAL-CORPUS rows (direction 5).
# Measured 2026-08-30 by running all twelve with --skip-corpus: exactly `tail` (the
# wg-arena3d truncation control) and `family_split` (archive-arena2d rust__t0, whose
# starter passage must land in the unverified-own-work count) survive without a corpus;
# the other ten die on fixture-side checks alone. The offline pass in main() re-derives
# that measurement on every run and requires the survivors to equal this set EXACTLY:
# an undeclared offline survivor is red (fail-closed default for new mutants), and a
# declared mutant that dies offline is a stale entry to trim. Declaring here is a
# recorded decision, never a silent gap.
CORPUS_ONLY_MUTANTS = frozenset({"tail", "family_split"})


def run_pass(base: str, tmp: Path, names: list[str], runs: Path | None,
             declared: frozenset[str] = frozenset()) -> list[str]:
    """Apply each named mutant and run the real selftest against it.

    `runs=None` runs the selftest with `--skip-corpus` — the fixture half alone,
    which is a measurement wherever this file lives. Survivors that are in
    `declared` are expected in that mode and labelled as such. A mutant whose
    search text has drifted is a survivor too, because a no-op mutant reports a
    pass for a check that never changed.
    """
    survivors: list[str] = []
    for name in names:
        old, new = MUTANTS[name]
        if old not in base:
            print(f"--- mutant {name}: NOT APPLIED — its search text is no longer in "
                  f"{SOURCE.name}. A no-op mutant reports a pass for a check that "
                  f"never changed.")
            survivors.append(f"{name} (not applied)")
            continue
        path = Path(tmp) / f"{name}.py"
        path.write_text(base.replace(old, new, 1))
        argv = [sys.executable, str(path), "--selftest"]
        argv += ["--skip-corpus"] if runs is None else ["--runs-dir", str(runs)]
        proc = subprocess.run(argv, capture_output=True, text=True)
        caught = proc.returncode != 0
        verdict = "CAUGHT (exit %d)" % proc.returncode if caught else (
            "SURVIVED (declared corpus-only — the corpus half holds it)"
            if runs is None and name in declared else "SURVIVED")
        print(f"--- mutant {name}: {verdict}")
        for line in proc.stdout.splitlines():
            print(f"    {line}")
        if not caught:
            survivors.append(name)
    return survivors


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--runs-dir", default=str(DEFAULT_RUNS))
    args = ap.parse_args()
    runs = Path(args.runs_dir).expanduser().resolve()

    base = SOURCE.read_text()
    with tempfile.TemporaryDirectory() as tmp:
        # THE OFFLINE HALF, ALWAYS RUN, OVER ALL TWELVE. In whatever checkout this runs
        # in — a worktree with no eval/runs/ included — it measures which mutants die on
        # fixture-side checks alone, and that measurement must equal CORPUS_ONLY_MUTANTS.
        # This pass is what makes the offline-coverage claim in the docstring a
        # measurement rather than prose: the tasks/225 review was right that a coverage
        # claim nothing runs is not a claim.
        offline_survivors = run_pass(base, tmp, list(MUTANTS), None,
                                     declared=CORPUS_ONLY_MUTANTS)
        if set(offline_survivors) != CORPUS_ONLY_MUTANTS:
            undeclared = [s for s in offline_survivors
                          if s not in CORPUS_ONLY_MUTANTS]
            stale = sorted(CORPUS_ONLY_MUTANTS - set(offline_survivors))
            print(f"\nOFFLINE-PIN MISMATCH: {len(offline_survivors)} of {len(MUTANTS)} "
                  f"mutants survive the fixture half, but CORPUS_ONLY_MUTANTS declares "
                  f"{{{', '.join(sorted(CORPUS_ONLY_MUTANTS))}}}. "
                  f"undeclared survivors (red — pin the mutant offline or declare it): "
                  f"{undeclared or 'none'}; stale declarations (trim): "
                  f"{stale or 'none'}.", file=sys.stderr)
            return 1
        if not runs.is_dir():
            print(f"UNMEASURABLE: no corpus at {runs}. "
                  f"{len(CORPUS_ONLY_MUTANTS)} of the {len(MUTANTS)} mutants are caught "
                  f"only by a real stored message "
                  f"({', '.join(sorted(CORPUS_ONLY_MUTANTS))}), so the corpus half "
                  f"cannot run here; the offline half above did, and agrees with the "
                  f"declaration. Run this in the main checkout.", file=sys.stderr)
            return 2
        survivors = run_pass(base, tmp, list(MUTANTS), runs)

    if survivors:
        print(f"\nSURVIVED: {', '.join(survivors)} — the selftest cannot see the loss of "
              f"that mechanism.")
        return 1
    print(f"\nall {len(MUTANTS)} mutants caught against {runs}; the offline half "
          f"re-measured {len(MUTANTS) - len(offline_survivors)} of them as "
          f"fixture-catchable, matching CORPUS_ONLY_MUTANTS "
          f"({', '.join(sorted(CORPUS_ONLY_MUTANTS))})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
