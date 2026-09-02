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

    ./findings_control.py                   # the controls and every mutant - what CI runs
    ./findings_control.py --clean-only      # the controls alone, unmutated
    ./findings_control.py --mutate <name>   # ... one at a time
    ./findings_control.py --selftest        # the two refusals in `build`, pinned
    ./findings_control.py --list-mutants

Every mutant is applied to a COPY in a tempdir. This file never writes to the repository -
and the sweep ASSERTS that rather than trusting it: the repository's own `docstat.py` is
snapshotted before the first mutant and compared after every one, and a mismatch is restored
from the snapshot and reported as a survivor. Module-global leak checks do not apply here -
the mutants are text patches against a fresh copy per case, not rebindings in this process -
so the leak surface this suite actually has is the repository file, and that is the one the
leak check reads.

**The default runs the clean pass AND every mutant**, and is red if any of them survives -
the repair `corpus_control.sweep` records from PR 54, which this file had not received (its
old `--all-mutants` mode was the same loop minus the clean pass and minus the leak check, and
ran only when an operator asked; it is kept as an alias of the sweep rather than deleted, so
the pass-39 record in CLEANUP-LOG.md that names it still resolves). `docstat --findings`
above it in `gates.yml` makes the clean call over the live corpus already, so a gate that
only repeated it would duplicate a gate while the nine mutants - the reason this file exists -
ran nowhere.

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
  COUNT         `--count-triggers` publishes a false-positive cost per candidate trigger,
  TRIGGERS      so an incomplete corpus must stop it at exit 2 rather than be published one
                document smaller with nothing saying so. `--findings` merely RECORDS a
                missing range document, which is right for a gate whose exit code already
                means "something is wrong" and wrong for a producer whose exit code means
                nothing. Its VARIANT asserts the SHAPE of the output, not the exit code:
                shipped row at 0 and the rejected quantifier row above it, because an
                extractor that has stopped matching reports 0 on every row.
  HOSTILE       an inherited `GIT_DIR` outranks `cwd`, silently and at exit 0, so the
  GIT_DIR       fixture builder could `git add -A` into the CALLER's index. This row is
                about THIS file rather than about `docstat.py`, and carries its own red
                half: it reproduces the damage with the vulnerable shape before asserting
                `_git` is immune (#198).
"""

from __future__ import annotations

import argparse
import json
import os
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
#: The agreeing corpus the selftest builds around: a fixture the refusals never reach
#: (they fire before anything is written) but a real mutant must land inside.
CONSISTENT = list(range(KNOWN_LO, KNOWN_HI + 1))


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
    leave the corpus at 3 documents and every control would still pass.

    EVERY `GIT_*` VARIABLE IS DROPPED FROM THE CHILD. `cwd` does not decide which
    repository git uses - `GIT_DIR` and friends override it, silently and at exit 0, so
    `git init` creates nothing and `git add -A` stages the fixture into the CALLER's index
    (#198, which is exactly this and was measured leaving 6 fixture paths staged in a live
    worktree). ALL of `GIT_*` rather than the 4 that steer discovery: a list of names is an
    enumeration and the next reader meets `GIT_COMMON_DIR`. Nothing here needs any of them.

    This is written out rather than imported from `docstat._git_at`. A control that shares
    a mechanism with its subject is repaired by the same mutant that breaks it, and the
    whole point of this file is to be a second, independent reader.
    """
    child = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    p = subprocess.run(["git", *args], cwd=tmp, capture_output=True, text=True, env=child)
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
        n = src.count(old)
        if n == 0:
            raise SystemExit(f"mutant `{mutant}` does not apply: its anchor is not in "
                             f"{DOCSTAT}. The code moved and the mutant is inert - which "
                             f"is a defect in this file, not a pass.")
        if n > 1:
            # Measured rather than preferred (cleanup pass 39): `replace(old, new, 1)`
            # mutates whichever copy came first, and the controls then grade a mutation
            # this file did not name. Both sibling runners assert this -- the count
            # before injecting, `tasks_mutants._write_copy`; the needle before the
            # torn-write fault, `tasks_control` -- and the refusal wording is theirs.
            raise SystemExit(f"mutant `{mutant}` does not apply: its anchor occurs {n} "
                             f"times in {DOCSTAT}. An ambiguous one mutates whichever "
                             f"copy came first. Fix the anchor.")
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


def run(script: Path, *flags: str) -> tuple[int, str]:
    """The real command, real argparse, real exit status. Never through a pipe."""
    p = subprocess.run([sys.executable, str(script), *(flags or ("--findings", "--json"))],
                       capture_output=True, text=True)
    return p.returncode, p.stdout + p.stderr


def hostile_git_env(verbose: bool = True) -> list[str]:
    """Does an inherited `GIT_DIR` steer where this file's fixture git commands land?

    RED AND GREEN IN ONE FUNCTION, because the mutant machinery below patches `docstat.py`
    and this defect is in THIS file. The red half runs the vulnerable shape - `cwd=` with
    the environment inherited - and asserts it really does damage a decoy repository; the
    green half runs `_git` and asserts it does not. Without the red half the green one is
    a check that cannot fail, which is the pattern this repository keeps paying for.

    Raised by CodeRabbit on PR #58, and it is #198 in a new place: `cwd` names a directory
    and an inherited `GIT_DIR` outranks it silently, at exit 0.
    """
    problems = []
    with tempfile.TemporaryDirectory() as td:
        decoy, fixture, safe = Path(td) / "decoy", Path(td) / "hit", Path(td) / "safe"
        for p in (decoy, fixture, safe):
            p.mkdir()
        (fixture / "doc.md").write_text("# planted\n")
        (safe / "doc.md").write_text("# planted\n")
        subprocess.run(["git", "init", "-q"], cwd=decoy, check=True,
                       env={k: v for k, v in os.environ.items()
                            if not k.startswith("GIT_")})
        hostile = dict(os.environ, GIT_DIR=str(decoy / ".git"))

        # RED: the shape the review found, run deliberately.
        for args in (("init", "-q"), ("add", "-A")):
            subprocess.run(["git", *args], cwd=fixture, capture_output=True, env=hostile)
        staged = subprocess.run(["git", "ls-files"], cwd=decoy, capture_output=True,
                                text=True, env={k: v for k, v in os.environ.items()
                                                if not k.startswith("GIT_")}).stdout
        red_bit = (fixture / ".git").exists() or not staged.strip()
        if red_bit:
            problems.append(
                "the RED half of the hostile-GIT_DIR control did not reproduce: the "
                f"fixture got its own .git ({(fixture / '.git').exists()}) or the decoy's "
                f"index stayed empty ({staged.strip()!r}). Without a reproduction the "
                f"green half below is a check that cannot fail.")

        # GREEN: `_git`, under the same hostile environment.
        before = staged
        os.environ["GIT_DIR"] = str(decoy / ".git")
        try:
            _git(safe, "init", "-q")
            _git(safe, "add", "-A")
        finally:
            os.environ.pop("GIT_DIR", None)
        after = subprocess.run(["git", "ls-files"], cwd=decoy, capture_output=True,
                               text=True, env={k: v for k, v in os.environ.items()
                                               if not k.startswith("GIT_")}).stdout
        if not (safe / ".git").exists():
            problems.append("_git under an inherited GIT_DIR created no repository in the "
                            "fixture tree - the scrub is not working")
        if after != before:
            problems.append(f"_git under an inherited GIT_DIR wrote to the decoy's index: "
                            f"{before.split()} -> {after.split()}")
    if verbose:
        ok = not problems
        print(f"{'PASS' if ok else 'FAIL'}  HOSTILE GIT_DIR: the vulnerable shape stages "
              f"into a decoy repository and `_git` does not (red and green, #198)")
        for p in problems:
            print(f"        {p[:150]}")
    return problems


def controls(mutant: str | None = None) -> int:
    consistent = list(range(KNOWN_LO, KNOWN_HI + 1))
    added = consistent + [KNOWN_HI + 1]
    renumbered = consistent[:-1] + [KNOWN_HI + 5]

    # Every row runs `--findings --json` unless it names its own flags.
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
        ("COUNT TRIGGERS: a range document missing must be exit 2, not a candidate cost "
         "published over a corpus one document smaller with nothing saying so",
         dict(bodies=consistent, indexed=consistent, count=KNOWN_COUNT, high=KNOWN_HI,
              no_readme=True, _flags=("--count-triggers", "--json")), 2,
         "refusing to publish a candidate cost"),
        ("COUNT TRIGGERS VARIANT: the complete tree must publish, and the SHIPPED row must "
         "read 0 while the quantifier row reads more than 0 - a producer whose extractor "
         "has stopped matching reports 0 everywhere",
         dict(bodies=consistent, indexed=consistent, count=KNOWN_COUNT, high=KNOWN_HI,
              extra_docs={"eval/PROTOCOL.md": "# P\n\nLint reports 72 findings today.\n"},
              _flags=("--count-triggers", "--json")), 0, None),
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
        kw = dict(kw)
        flags = tuple(kw.pop("_flags", ()))
        with tempfile.TemporaryDirectory() as td:
            script = build(Path(td), mutant=mutant, **kw)
            rc, out = run(script, *flags)
        ok = rc == want_rc and (want_text is None or want_text in out)
        # On the green cases, also check the producer reports the answer stated above -
        # an exit code alone would pass on a tool that counted nothing and found nothing
        # to disagree with. Only `--findings` prints `bodies`; a row naming its own flags
        # asserts on its own output text instead.
        if ok and want_rc == 0 and flags[:1] == ("--count-triggers",):
            # An exit code proves the command ran. It does not prove the extractor still
            # matches, and an extractor that has stopped reports `red 0` on EVERY row -
            # which is also what a clean corpus reports. Assert the shape instead: the
            # shipped row at 0, and the rejected quantifier row above it.
            cands = json.loads(out[:out.rindex("}") + 1])["candidates"]
            shipped, quantifier = cands[-1]["red"], cands[-2]["red"]
            if shipped != 0 or quantifier < 1:
                ok = False
                name += (f" [SHIPPED row {shipped}, expected 0; quantifier row "
                         f"{quantifier}, expected at least 1]")
        if ok and want_rc == 0 and not flags:
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

    # This one asks about THIS file rather than about `docstat.py`, so it runs under a
    # mutant too - the fixture builder is the same either way.
    if hostile_git_env():
        failures.append("HOSTILE GIT_DIR")

    print(f"\n{len(cases) + 2} control(s), {len(failures)} failed")
    return 1 if failures else 0


def sweep() -> int:
    """The clean run and EVERY mutant, in one invocation.

    THIS IS WHAT THE CI STEP RUNS, and it is why the step exists at all - the repair
    `corpus_control.sweep` records from PR 54, which this file had not received: with the
    default at `controls()` alone, the gate duplicated the clean half `docstat --findings`
    already runs over the live corpus, and no mutant ever ran outside an operator's
    terminal. A suite whose mutants are opt-in is a suite whose mutants are the one thing
    nobody re-runs.

    THE LEAK CHECK IS THE REPOSITORY FILE ITSELF. The template's restore-between-mutants
    is a module-global snapshot here for no suite but `corpus_control` and
    `withdrawn_control`: this suite's mutants never rebind anything in the running
    process - each one is a text patch applied to a fresh COPY of `docstat.py` per case -
    so the only state a mutant could leak into is the repository's own file. That is the
    file `build()`'s docstring records losing an hour of uncommitted work to, which is
    why the snapshot is compared after every mutant and restored on a mismatch rather
    than trusted to never fire.
    """
    print(f"findings producer controls, {len(MUTANTS)} mutants, clean pass first\n")
    clean_failed = controls()
    print(f"\nCLEAN  {'FAILED' if clean_failed else 'passed'}, expected passed\n")

    pristine_docstat = DOCSTAT.read_bytes()
    killed: list[str] = []
    survived: list[str] = []
    for name in MUTANTS:
        rc = controls(mutant=name)
        if DOCSTAT.read_bytes() != pristine_docstat:
            DOCSTAT.write_bytes(pristine_docstat)
            survived.append(f"{name}: the mutant reached the repository's own "
                            f"{DOCSTAT} - restored from the snapshot; this is a defect "
                            f"in build(), never a pass")
            continue
        print(f"\nMUTANT {name:<26} "
              + ("SURVIVED  <- the controls cannot see the mechanism it names"
                 if rc == 0 else "went red, as it must"))
        (survived if rc == 0 else killed).append(name)

    print(f"\n{len(killed)} of {len(MUTANTS)} mutants died; "
          f"{len(survived)} survived"
          + ("" if not survived else ":\n  " + "\n  ".join(survived)))
    if clean_failed or survived:
        return 1
    print("A mutant run is EXPECTED to fail its controls; a mutant that survives means "
          "the controls no longer reach the mechanism they name, and the gate's green "
          "is once again the ambiguity this file exists to prevent.")
    return 0


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
        "    return {**live, **stated}, stated, absent + problems",
        "    return dict(stated), stated, absent + problems  # MUTANT: back to RANGE_DOCS"),
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


def _repeated_line() -> tuple[str, int] | None:
    """A string measured NOW to occur more than once in docstat.py, for `selftest`.

    THE TICKET'S CONSTRAINT, AND WHY IT IS ONE. A hardcoded ambiguous anchor is dead the
    day the code moves, and it dies in the dangerous direction: reading ZERO once the
    line is edited away, the ambiguous row would trip the ABSENT refusal and pass while
    naming a refusal it is not about - red, but for a reason it did not name, which the
    fixture table above was rebuilt to close. So the anchor is whatever non-blank line
    of the live file repeats, the count beside it is the count measured rather than one
    remembered, and `None` means the ambiguous refusal cannot be exercised at run time
    at all - itself a FAIL, never a skip.

    THE COUNT IS THE SUBSTRING COUNT, the same expression `build` computes - and that
    took a measurement to learn, not a preference. This function first counted LINES
    (`splitlines`), and its own first run went red on the gap: the docstring-closing
    fence, the file's first repeating line, occurs 86 times as a line and 190 times as
    a substring, and the refusal was correct at 190 while the assertion demanded 86.
    "Occurs" is two different measurements, and the one asserted has to be the one the
    refusal was computed from.
    """
    text = DOCSTAT.read_text()
    seen: set[str] = set()
    for ln in text.splitlines():
        if not ln.strip() or ln in seen:
            continue
        seen.add(ln)
        n = text.count(ln)
        if n > 1:
            return ln, n
    return None


def _refusal(mutant: str, old: str, new: str) -> tuple[bool, str]:
    """Inject `(old, new)` under `mutant`, call `build`, and report whether it refused.

    The entry under MUTANTS exists for the duration of the call and never afterwards,
    the way `tasks_mutants.selftest` brackets its drift probe. `(False, ...)` is the
    loud outcome: `build` returned a path, so a mutation this file did not intend was
    applied to a copy without a word.
    """
    MUTANTS[mutant] = (old, new)
    try:
        with tempfile.TemporaryDirectory() as td:
            build(Path(td), mutant=mutant, bodies=CONSISTENT, indexed=CONSISTENT,
                  count=KNOWN_COUNT, high=KNOWN_HI)
    except SystemExit as exc:
        return True, str(exc)
    finally:
        del MUTANTS[mutant]
    return False, "build() returned a path instead of raising SystemExit"


def selftest() -> int:
    """The runner's own pins: do `build`'s two refusals refuse, and does applying survive?

    Cleanup pass 39 added the ambiguity refusal beside the absent-anchor one and
    demonstrated both by ad-hoc invocation in that session only. A guard whose only
    verification is the session that wrote it is one edit away from silent removal, and
    the failure is invisible when it goes: a deleted refusal reports nothing, and the
    next ambiguous anchor mutates whichever copy came first while the controls grade a
    mutation this file did not name.

    The third row is rule 15's other half. A refusal "repaired" into refusing everything
    would keep rows one and two green, so a REAL mutant from the table above must still
    apply, and exactly once.
    """
    before = DOCSTAT.read_bytes()
    failures: list[str] = []
    seen = 0

    def row(ok: bool, name: str, detail: str = "") -> None:
        nonlocal seen
        seen += 1
        print(f"  {'ok  ' if ok else 'FAIL'} {name}")
        if not ok:
            failures.append(name)
            if detail:
                print(f"        {detail[:150]}")

    # (a) ABSENT. The precondition is measured, not assumed: if the sentinel ever turns
    # up in docstat.py this row would be grading the wrong refusal, and says so rather
    # than passing.
    absent = "A STRING THAT IS NOT IN docstat.py"
    n_absent = DOCSTAT.read_text().count(absent)
    if n_absent:
        row(False, "a mutant whose anchor is ABSENT from docstat.py REFUSES",
            f"the sentinel itself occurs {n_absent} times in {DOCSTAT}, so this row "
            f"would not name the refusal it claims to")
    else:
        refused, msg = _refusal("_selftest_absent", absent, "x")
        row(refused and "is not in" in msg and "_selftest_absent" in msg,
            "a mutant whose anchor is ABSENT from docstat.py REFUSES", msg)

    # (b) AMBIGUOUS, built at run time out of the live file - never a hardcoded line.
    measured = _repeated_line()
    if measured is None:
        row(False, "an anchor occurring more than once was MEASURED out of docstat.py",
            "no non-blank line of the live file occurs twice, so the ambiguous refusal "
            "cannot be exercised at run time")
    else:
        dup, n_dup = measured
        refused, msg = _refusal("_selftest_ambiguous", dup, "x  # MUTANT")
        row(refused and f"occurs {n_dup} times" in msg and "ambiguous" in msg,
            f"an anchor measured to occur {n_dup} times in docstat.py REFUSES", msg)

    # (c) and a REAL mutant must still apply, exactly once - the variant half, without
    # which rows (a) and (b) are also satisfied by a `build` that refuses everything.
    name = next(iter(MUTANTS))
    old, new = MUTANTS[name]
    try:
        with tempfile.TemporaryDirectory() as td:
            copy = build(Path(td), mutant=name, bodies=CONSISTENT, indexed=CONSISTENT,
                         count=KNOWN_COUNT, high=KNOWN_HI)
            text = copy.read_text()
        row(text.count(new) == 1 and text.count(old) == 0,
            f"a REAL mutant (`{name}`) still APPLIES, exactly once",
            f"the replacement landed {text.count(new)} time(s) and its anchor remains "
            f"{text.count(old)} time(s)")
    except SystemExit as exc:
        row(False, f"a REAL mutant (`{name}`) still APPLIES, exactly once", str(exc))

    row(DOCSTAT.read_bytes() == before,
        "docstat.py is byte-identical before and after - the mutants ran on copies")

    print(f"\n{seen} assertion(s), {len(failures)} failed")
    return 1 if failures else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--mutate", metavar="NAME",
                    help="run the controls against a MUTATED COPY of docstat.py in a "
                         "tempdir; the repository's own file is never written to")
    ap.add_argument("--all-mutants", action="store_true",
                    help="an alias of the default sweep, kept so the pass-39 record in "
                         "CLEANUP-LOG.md still resolves")
    ap.add_argument("--list-mutants", action="store_true")
    ap.add_argument("--clean-only", action="store_true",
                    help="the controls on the unmutated tool, without the mutant sweep")
    ap.add_argument("--selftest", action="store_true",
                    help="the two refusals in `build`, pinned: an anchor absent from "
                         "docstat.py must refuse, an anchor measured at run time to "
                         "occur more than once must refuse, and a real mutant must "
                         "still apply, exactly once")
    a = ap.parse_args()
    if a.list_mutants:
        for k, (old, _) in MUTANTS.items():
            print(f"{k:26} removes: {old.strip()[:70]}")
        return 0
    if a.selftest:
        return selftest()
    if a.mutate:
        if a.mutate not in MUTANTS:
            raise SystemExit(f"unknown mutant {a.mutate}; --list-mutants")
        print(f"MUTANT `{a.mutate}`, applied to a COPY. At least one control must FAIL.\n")
        rc = controls(mutant=a.mutate)
        print("\nthe mutant was CAUGHT" if rc else
              "\nTHE MUTANT SURVIVED - the controls above do not test what they name")
        return 0 if rc else 1
    if a.clean_only:
        return controls()
    return sweep()


if __name__ == "__main__":
    sys.exit(main())
