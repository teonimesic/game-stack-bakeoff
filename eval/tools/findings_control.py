#!/usr/bin/env python3
"""End-to-end controls for `docstat.py --findings`, the producer for the findings count.

WHY THIS EXISTS BESIDE THE IN-TOOL PINS. `_findings_census_pins` calls `findings_census`
directly, in the running process, on the real corpus. That proves the FUNCTION. It cannot
prove the COMMAND: not the argparse wiring, not the exit code a shell reads, and above all
not the address — every path the tool opens is derived from `__file__`, and `runstat.py`
once obeyed a correct method against a directory that no longer existed and reported "no
writes" through a build writing 2555 files (#60, AGENTS.md rule 12).

So this builds a tree whose answer is STATED BEFORE IT IS MEASURED, drops a copy of
`docstat.py` into it, and runs the real command as a subprocess, reading the real exit
status unpiped.

    ./findings_control.py                   # the controls
    ./findings_control.py --all-mutants     # prove every one of them can go red
    ./findings_control.py --mutate <name>   # ... one at a time
    ./findings_control.py --list-mutants

Every mutant is applied to a COPY in a tempdir. This file never writes to the repository.

WHAT IS CONTROLLED, and why each one is here rather than obvious:

  KNOWN ANSWER  a tree of exactly 3 findings, #19-#21, stated in this file before the tool
                sees it. A census that agrees with itself is not evidence; one that agrees
                with a number written down in advance is.
  ADDED         a finding written into `eval/findings/` must move the count. This is the
                thing the range gate could not see: `#19-#131` is equally true of 113
                findings and of 40, which is how "Thirty-seven numbered findings" survived
                to #131 past a gate that was green.
  DRIFT         the same finding indexed but with the documents left behind must still be
                red. The two halves fail independently and both are reported.
  RENUMBERED    a number changed in the bodies alone must be red — renumbering is what
                CREATES a dangling citation (#118).
  GAP ONLY      the same renumber applied CONSISTENTLY everywhere. Sets agree, count
                agrees, range agrees, and the numbering has a hole. Without this row the
                gap check could be deleted and every other control stayed green.
  COUNTED TWICE one number on two index rows, same set of numbers. Invisible to both set
                differences; only counting sees it, and only counting the BODIES. Without
                this row, two mutants survived — one deleting the reconciliation, one
                taking the count from the index and cross-checking it against itself.
  VARIANT       a finding added CORRECTLY everywhere must go back to green. A mutant asks
                whether the producer can disagree; only this asks whether it can still
                agree (AGENTS.md rule 15). If it cannot, the gate is unusable and gets
                switched off by the first person who writes finding #132.
  WORDS         a count spelled as a cardinal in words must be reported as ungateable. The
                one real instance was `Thirty-seven`, and a digits-only check would let the
                next one walk past by being written out in full.
  DUPLICATED    a live document stating the range twice must be red. `_check_range_in`
                validates every occurrence, so N correct copies are N passes — and an evil
                merge duplicated the sentence in `AGENTS.md` and `README.md` on the same
                day with `--sweep` green on both.
  REFUSES       an empty findings directory, a missing one, and a tree `git` cannot list
                must all exit 2. `0 findings` is in range, plausible, and
                indistinguishable from a corpus nobody read; `census.py` refuses for the
                same reason and this is the same rule. The exit code is 2 rather than 1
                because 1 means the sources DISAGREE, and a broken address reported as a
                disagreement is the same fail-open shape one step later.
  ADDRESS       a document named in `RANGE_DOCS` and absent must be REPORTED. Skipping it
                shrinks the corpus by one and the census goes on agreeing with itself.
  ENTRIES       the count one short in the `entries` wording, beside the producer. This is
                `README.md` line 187 as it stood on 2026-08-27 — `143 entries` against a
                measured 171 — which the `N numbered findings` trigger read as clean while
                reddening the same fact, in the same file, phrased its way. Its VARIANT
                pairs it: the same wording stating the count correctly must go back green.
  WIDER CORPUS  a stale count in a live document that is in neither `RANGE_DOCS` nor the
                archive. The count was reconciled in three documents until task 179, so a
                figure anywhere else was unreachable by a gate that reported itself clean.
                Its VARIANT is the half that matters: a live document naming the log with
                a line number, a singular noun, a date and a fenced example must stay green.
  REAL TREE     the same subprocess path over THIS repository must exit 0. The synthetic
                cases prove the logic; this one proves the tool is pointed at the project.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
DOCSTAT = HERE / "docstat.py"

# The answer, written down before anything measures it (AGENTS.md rule 12).
KNOWN_COUNT = 3
KNOWN_LO, KNOWN_HI = 19, 21


def _index(numbers: list[int]) -> str:
    rows = "".join(f"| **{n}** | claim {n} | [a](findings/a.md) |\n" for n in numbers)
    return ("# Eval findings\n\n"
            f"Findings #{KNOWN_LO}-#{max(numbers)} from building this evaluator.\n\n"
            "## Every finding\n\n| # | claim | in |\n|---|---|---|\n" + rows + "\n")


def _bodies(numbers: list[int]) -> str:
    return "# a\n\n" + "".join(f"## #{n} - claim {n}\n\nbody.\n\n" for n in numbers)


def _live(count: int, high: int, *, words: bool = False, twice: bool = False) -> str:
    line = f"| `eval/FINDINGS.md` | Findings #{KNOWN_LO}-#{high} | the log |\n"
    said = "Thirty-seven numbered findings" if words else f"{count} numbered findings"
    return ("# Doc\n\n| file | why |\n|---|---|\n" + line + (line if twice else "") +
            f"\n{said}, and all but a few are instances of one pattern.\n")


def _entries(count: int, high: int) -> str:
    """README.md's real line 187 shape: the count in the `entries` wording, the range and
    the producer all in one sentence. The wording the gate could not read until task 179."""
    return ("# Doc\n\n| question | where |\n|---|---|\n"
            f"| What went wrong? | [`eval/FINDINGS.md`](eval/FINDINGS.md) - {count} "
            f"entries. Findings #{KNOWN_LO}-#{high}, count and range from "
            f"`python3 eval/tools/docstat.py --findings` |\n")


def _git(tmp: Path, *args: str) -> None:
    """Run one git command in the fixture tree, and refuse to continue if it fails.

    The tree has to BE a repository: `_live_corpus` lists the index rather than globbing
    the disk (#198), and the count corpus is read from it. A silent failure here would
    leave the corpus at three documents and every control would still pass.
    """
    p = subprocess.run(["git", *args], cwd=tmp, capture_output=True, text=True)
    if p.returncode != 0:
        raise SystemExit(f"the fixture tree could not be made a git repository: "
                         f"`git {' '.join(args)}` exited {p.returncode} in {tmp}: "
                         f"{(p.stderr or p.stdout).strip()[:200]}")


def build(tmp: Path, *, bodies: list[int], indexed: list[int], count: int, high: int,
          words: bool = False, twice: bool = False, empty_bodies: bool = False,
          no_dir: bool = False, no_readme: bool = False, mutant: str | None = None,
          extra_docs: dict[str, str] | None = None,
          readme_entries: int | None = None, no_git: bool = False) -> Path:
    """A whole repository root, with docstat.py inside it so ROOT resolves to `tmp`.

    THE MUTANT IS APPLIED HERE, to the COPY. An earlier version of this file patched the
    repository's own `eval/tools/docstat.py` in place and told the operator to
    `git checkout` afterwards; that instruction was followed and it discarded an hour of
    uncommitted work on the same file. A control must not be able to damage the thing it
    controls, and "remember to restore it" is not a mechanism.
    """
    (tmp / "eval" / "tools").mkdir(parents=True, exist_ok=True)
    src = DOCSTAT.read_text()
    if mutant:
        old, new = MUTANTS[mutant]
        if old not in src:
            raise SystemExit(f"mutant `{mutant}` does not apply: its anchor is not in "
                             f"{DOCSTAT}. The code moved and the mutant is inert - which "
                             f"is a defect in this file, not a pass.")
        src = src.replace(old, new, 1)
    (tmp / "eval" / "tools" / "docstat.py").write_text(src)
    if not no_dir:
        (tmp / "eval" / "findings").mkdir(parents=True, exist_ok=True)
        (tmp / "eval" / "findings" / "a.md").write_text(
            "# a\n\nprose only, no numbered heading.\n" if empty_bodies
            else _bodies(bodies))
    (tmp / "eval" / "FINDINGS.md").write_text(_index(indexed or [KNOWN_LO]))
    (tmp / "AGENTS.md").write_text(_live(count, high, words=words, twice=twice))
    if not no_readme:
        (tmp / "README.md").write_text(
            _live(count, high) if readme_entries is None
            else _entries(readme_entries, high))
    for rel, text in (extra_docs or {}).items():
        p = tmp / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
    if not no_git:
        _git(tmp, "init", "-q")
        _git(tmp, "add", "-A")
    return tmp / "eval" / "tools" / "docstat.py"


def run(script: Path) -> tuple[int, str]:
    """The real command, real argparse, real exit status. Never through a pipe."""
    p = subprocess.run([sys.executable, str(script), "--findings", "--json"],
                       capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


def controls(mutant: str | None = None) -> int:
    consistent = list(range(KNOWN_LO, KNOWN_HI + 1))
    added = consistent + [KNOWN_HI + 1]
    renumbered = consistent[:-1] + [KNOWN_HI + 5]

    cases: list[tuple[str, dict, int, str | None]] = [
        ("KNOWN ANSWER: 3 findings #19-#21, index and documents agreeing",
         dict(bodies=consistent, indexed=consistent, count=KNOWN_COUNT, high=KNOWN_HI),
         0, None),
        ("ADDED: #22 written into eval/findings/ and nowhere else",
         dict(bodies=added, indexed=consistent, count=KNOWN_COUNT, high=KNOWN_HI),
         1, "has a body and no index row"),
        ("DRIFT: #22 in the bodies and the index, documents left behind",
         dict(bodies=added, indexed=added, count=KNOWN_COUNT, high=KNOWN_HI),
         1, "numbered findings"),
        ("VARIANT: #22 added correctly everywhere - must go back to green",
         dict(bodies=added, indexed=added, count=KNOWN_COUNT + 1, high=KNOWN_HI + 1),
         0, None),
        ("RENUMBERED: #21 becomes #26 in the bodies alone",
         dict(bodies=renumbered, indexed=consistent, count=KNOWN_COUNT, high=KNOWN_HI),
         1, "has a body and no index row"),
        # The two cases below exist because three mutants survived without them, and each
        # survived for the same reason: another check happened to fire on the same input.
        # A control that is red for a reason it did not name is not controlling that reason.
        ("GAP ONLY: #21 renumbered to #26 consistently everywhere - sets, count and range "
         "all agree and the numbering still has a hole",
         dict(bodies=renumbered, indexed=renumbered, count=KNOWN_COUNT,
              high=KNOWN_HI + 5), 1, "gap(s) - #21"),
        ("COUNTED TWICE: the same set of numbers, one indexed on two rows - invisible to "
         "every set difference, and the count must come from the BODIES",
         dict(bodies=consistent, indexed=consistent + [KNOWN_HI], count=KNOWN_COUNT,
              high=KNOWN_HI), 1, "The two sources of the count disagree by 1"),
        ("WORDS: a document stating its count as a cardinal in words",
         dict(bodies=consistent, indexed=consistent, count=KNOWN_COUNT, high=KNOWN_HI,
              words=True), 1, "in words"),
        ("DUPLICATED: a document stating the range on two lines",
         dict(bodies=consistent, indexed=consistent, count=KNOWN_COUNT, high=KNOWN_HI,
              twice=True), 1, "on 2 lines"),
        ("REFUSES: a findings directory with no numbered heading is exit 2, not 0 findings",
         dict(bodies=consistent, indexed=consistent, count=KNOWN_COUNT, high=KNOWN_HI,
              empty_bodies=True), 2, "would report 0 findings"),
        ("REFUSES: no findings directory at all is exit 2",
         dict(bodies=consistent, indexed=consistent, count=KNOWN_COUNT, high=KNOWN_HI,
              no_dir=True), 2, "refusing"),
        ("ADDRESS: a document named in RANGE_DOCS and absent must be reported, not skipped",
         dict(bodies=consistent, indexed=consistent, count=KNOWN_COUNT, high=KNOWN_HI,
              no_readme=True), 1, "one document fewer than it claims"),
        ("REFUSES: a tree git cannot list is exit 2, not exit 1 - a broken address must "
         "not be reported in the same code as a real disagreement",
         dict(bodies=consistent, indexed=consistent, count=KNOWN_COUNT, high=KNOWN_HI,
              no_git=True), 2, "git ls-files failed"),
        ("ENTRIES: the count one short in the `entries` wording, beside the producer - the "
         "real README.md line 187, which the `N numbered findings` trigger read as clean",
         dict(bodies=consistent, indexed=consistent, count=KNOWN_COUNT, high=KNOWN_HI,
              readme_entries=KNOWN_COUNT - 1), 1,
         "names the findings log and states `2 entries`"),
        ("ENTRIES VARIANT: the same wording stating the count CORRECTLY must go back to "
         "green - a gate that cannot accept the repair is a gate that gets switched off",
         dict(bodies=consistent, indexed=consistent, count=KNOWN_COUNT, high=KNOWN_HI,
              readme_entries=KNOWN_COUNT), 0, None),
        ("WIDER CORPUS: a stale count in a live document that is in neither RANGE_DOCS nor "
         "the archive - unreachable by this gate until task 179 widened what it reads",
         dict(bodies=consistent, indexed=consistent, count=KNOWN_COUNT, high=KNOWN_HI,
              extra_docs={"eval/PROTOCOL.md":
                          f"# Protocol\n\nThe log holds {KNOWN_COUNT + 4} separate "
                          f"numbered entries (`docstat.py --findings`).\n"}), 1,
         "eval/PROTOCOL.md:3 names the findings log and states `7 separate numbered "
         "entries`"),
        ("WIDER CORPUS VARIANT: a live document naming the log with a number that is NOT a "
         "count - a line number, a singular noun, a date, and a fenced example",
         dict(bodies=consistent, indexed=consistent, count=KNOWN_COUNT, high=KNOWN_HI,
              extra_docs={"eval/PROTOCOL.md":
                          "# Protocol\n\nAn edit left a line stranded at line 6 of "
                          "`eval/FINDINGS.md`, decided 2026-08-23, and `1 hit` remained.\n"
                          "\n```\n99 entries. Findings #19-#21\n```\n"}), 0, None),
    ]

    failures: list[str] = []
    for name, kw, want_rc, want_text in cases:
        with tempfile.TemporaryDirectory() as td:
            script = build(Path(td), mutant=mutant, **kw)
            rc, out = run(script)
        ok = rc == want_rc and (want_text is None or want_text in out)
        # On the green cases, also check the producer reports the answer stated above -
        # an exit code alone would pass on a tool that counted nothing and found nothing
        # to disagree with.
        if ok and want_rc == 0:
            # Let a malformed payload raise. A `.get` chain with a default would turn an
            # unparseable output into `None != 3`, which is a failure with the wrong
            # reason, or into a pass if the default happened to match (rule 3's sibling).
            b = json.loads(out[:out.rindex("}") + 1])["bodies"]
            want_n = kw["count"]
            if b["count"] != want_n or b["highest"] != kw["high"]:
                ok = False
                name += (f" [reported {b['count']} findings up to #{b['highest']}, "
                         f"stated {want_n} up to #{kw['high']}]")
        print(f"{'PASS' if ok else 'FAIL'}  {name} -> exit {rc}, expected {want_rc}")
        if not ok:
            failures.append(name)
            for ln in out.strip().split("\n")[-6:]:
                print(f"        {ln[:150]}")

    # The real repository, through the same subprocess path. Skipped under a mutant: the
    # copy under test is in a tempdir and the repository's own file is deliberately
    # untouched, so this row would be measuring the unmutated tool and reporting a pass.
    if mutant:
        print("SKIP  REAL TREE: not run under a mutant - the repository's docstat.py "
              "is deliberately never patched, so this row would test the wrong binary")
    else:
        rc, out = run(DOCSTAT)
        real_ok = rc == 0
        print(f"{'PASS' if real_ok else 'FAIL'}  REAL TREE: {DOCSTAT} over this repository "
              f"-> exit {rc}, expected 0")
        if not real_ok:
            failures.append("REAL TREE")
            for ln in out.strip().split("\n")[-8:]:
                print(f"        {ln[:150]}")

    print(f"\n{len(cases) + 1} control(s), {len(failures)} failed")
    return 1 if failures else 0


#: Each mutant deletes ONE mechanism the controls above name. A control that survives its
#: own mutant is testing something else. Applied to the COPY under test, never to the
#: repository's `docstat.py`.
MUTANTS: dict[str, tuple[str, str]] = {
    "no_count_check": (
        "        disagreements += _stated_counts(rel, text, count)",
        "        disagreements += []  # MUTANT"),
    "no_word_form": (
        "        m = _COUNT_WORD_RX.search(ln)",
        "        m = None  # MUTANT: only digits are read"),
    "no_scoped_count": (
        "        if _LOGREF_RX.search(ln):",
        "        if False:  # MUTANT: only the `N numbered findings` wording is read"),
    "count_corpus_is_range_docs": (
        "    counted = {**live, **stated}",
        "    counted = dict(stated)  # MUTANT: back to the three range documents"),
    "no_index_reconciliation": (
        "    if len(rows) != count:",
        "    if False:  # MUTANT"),
    "no_gap_check": (
        "    if gaps:",
        "    if False:  # MUTANT"),
    "no_duplicate_range": (
        "        if len(occurrences[rel]) > 1:",
        "        if False:  # MUTANT"),
    "count_from_the_index": (
        "    count = len(bodies)",
        "    count = len(rows)  # MUTANT: one source, cross-checked against itself"),
    "never_disagrees": (
        "    return {\n        \"bodies\": {",
        "    disagreements = []  # MUTANT\n    return {\n        \"bodies\": {"),
}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--mutate", metavar="NAME",
                    help="run the controls against a MUTATED COPY of docstat.py in a "
                         "tempdir; the repository's own file is never written to")
    ap.add_argument("--all-mutants", action="store_true",
                    help="every mutant in turn; exit 1 if any survives")
    ap.add_argument("--list-mutants", action="store_true")
    a = ap.parse_args()
    if a.list_mutants:
        for k, (old, _) in MUTANTS.items():
            print(f"{k:26} removes: {old.strip()[:70]}")
        return 0
    if a.all_mutants:
        survived = []
        for name in MUTANTS:
            print(f"\n=== MUTANT {name}")
            if controls(mutant=name) == 0:
                survived.append(name)
        print(f"\n{len(MUTANTS)} mutant(s), {len(survived)} survived"
              + (f": {', '.join(survived)}" if survived else " - all caught"))
        return 1 if survived else 0
    if a.mutate:
        if a.mutate not in MUTANTS:
            raise SystemExit(f"unknown mutant {a.mutate}; --list-mutants")
        print(f"MUTANT `{a.mutate}`, applied to a COPY. At least one control must FAIL.\n")
        rc = controls(mutant=a.mutate)
        print("\nthe mutant was CAUGHT" if rc else
              "\nTHE MUTANT SURVIVED - the controls above do not test what they name")
        return 0 if rc else 1
    return controls()


if __name__ == "__main__":
    sys.exit(main())
