#!/usr/bin/env python3
"""Twelve mutants of `disclosure.py`, each removing one mechanism its selftest names.

`disclosure.py --selftest` mutates its own cue LIST in process, which cannot reach the
helper patterns the cues are built from, nor the line that chooses which field to read.
Those are exactly the mechanisms whose loss is invisible: a wider `_GAP` still locates
every documented discloser, and reading the truncated field still locates most of them.
So each mutant here rewrites one span of the source and runs the real selftest against
the real corpus. **Every mutant must be caught.**

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

A missing corpus exits 2. These mutants are not meaningful against fixtures alone: six of
the twelve are caught only by a real stored message. The exception proves the rule the
other way — `scan_filter` and `scan_glob` are caught by the selftest's fixture half
alone, because a trial with no stored message carries no text for a cue test to miss.
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
    # text to mislocate — so only the scan-population pins can see the loss. These
    # two are caught by the fixture half alone, so they stay pinned with
    # --skip-corpus where the other ten are not.
    "scan_filter": (
        "    dirs = [d for d in sorted(artifacts.iterdir()) if d.is_dir()]",
        "    dirs = [d for d in sorted(artifacts.iterdir())\n"
        "            if d.is_dir() and (d / \"agent_result.json\").is_file()]"),
    "scan_glob": (
        '    dirs = sorted(d for d in runs_dir.glob("*/artifacts/*") if d.is_dir())',
        '    dirs = sorted(p.parent for p in\n'
        '                  runs_dir.glob("*/artifacts/*/agent_result.json"))'),
}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--runs-dir", default=str(DEFAULT_RUNS))
    args = ap.parse_args()
    runs = Path(args.runs_dir).expanduser().resolve()
    if not runs.is_dir():
        print(f"UNMEASURABLE: no corpus at {runs}. Four of these six mutants are caught "
              f"only by a real stored message; an agent worktree has no eval/runs/, so "
              f"run this in the main checkout.", file=sys.stderr)
        return 2

    base = SOURCE.read_text()
    survivors: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        for name, (old, new) in MUTANTS.items():
            if old not in base:
                print(f"--- mutant {name}: NOT APPLIED — its search text is no longer in "
                      f"{SOURCE.name}. A no-op mutant reports a pass for a check that "
                      f"never changed.")
                survivors.append(f"{name} (not applied)")
                continue
            path = Path(tmp) / f"{name}.py"
            path.write_text(base.replace(old, new, 1))
            proc = subprocess.run(
                [sys.executable, str(path), "--selftest", "--runs-dir", str(runs)],
                capture_output=True, text=True)
            caught = proc.returncode != 0
            print(f"--- mutant {name}: "
                  f"{'CAUGHT (exit %d)' % proc.returncode if caught else 'SURVIVED'}")
            for line in proc.stdout.splitlines():
                print(f"    {line}")
            if not caught:
                survivors.append(name)

    if survivors:
        print(f"\nSURVIVED: {', '.join(survivors)} — the selftest cannot see the loss of "
              f"that mechanism.")
        return 1
    print(f"\nall {len(MUTANTS)} mutants caught against {runs}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
