#!/usr/bin/env python3
"""The mutants of `tasks.py` that `tasks_control.py`'s rows are supposed to catch.

WHY THIS EXISTS. Task 82 built direction 5 of `tasks_control.py` and killed five mutants
with it -- by hand, in one session. What it left behind was a SENTENCE in a closed ticket's
`established_by` field saying they had died. Nothing in the repository could run one, so
from the moment that session ended the claim "these rows can go red" was unfalsifiable, and
the rows could be weakened, or the mechanisms they name deleted, with `tasks_control.py`
still printing `28 measurements, 0 FAILED`. AGENTS.md rule 15 says both halves run in
`judge/bot_mutants.py` BECAUSE a discipline you have to remember is one that will fail;
this is the same shape one directory over (#132: a claim that survived every grep because
it was a comment rather than a reader).

WHAT IT DOES. For each mutant: copy `tasks.py` into a tempdir, apply ONE replacement to the
COPY, run the real `tasks_control.py` against it via `--tasks-py`, and read which rows went
red. A mutant is CAUGHT only if the row NAMING ITS MECHANISM is among them -- not merely if
something, somewhere, failed. A control that is red for a reason it did not name is not
controlling that reason (`findings_control.py` learned this with three surviving mutants).

    python3 eval/tools/tasks_mutants.py                 # baseline, then every mutant
    python3 eval/tools/tasks_mutants.py --mutate NAME   # one
    python3 eval/tools/tasks_mutants.py --list

THE COPY IS THE POINT, and it is #134's constraint: the first version of the equivalent
file for `docstat.py` patched the repository's own tool in place and told the operator to
`git checkout` afterwards. That instruction was followed and it discarded an hour of
uncommitted work. Nothing here writes to `eval/tools/tasks.py`, and the run is a no-op on
the shared queue -- `<tmp>/tasks` is a SYMLINK to it so that direction 1 and the task-32 pin
still have a corpus, and every row that touches it only reads.

THE BASELINE RUNS FIRST AND IS NOT DECORATION. It grades an UNMUTATED copy through the same
tempdir, the same symlink and the same `--tasks-py` path, and it must be green. Without it,
a red row under a mutant is equally well explained by the harness: this is the variant half
(AGENTS.md rule 15) applied to the mutant runner itself. It also pins the row NAMES, which
are what every `kills` entry below is matched against.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "tasks.py"
CONTROL = HERE / "tasks_control.py"

# The queue address is IMPORTED from the subject, not re-derived here. Two `parents[n]`
# expressions that differ by one is exactly how rule 12 gets paid for a second time.
sys.path.insert(0, str(HERE))
import tasks as _t  # noqa: E402

QUEUE = _t.TASKS

#: name -> (anchor, replacement, rows that MUST go red).
#:
#: Each `kills` entry is a substring of a row name printed by `tasks_control.py`. The
#: baseline run asserts every one of them exists, so a row renamed or deleted out from under
#: a mutant is a failure here rather than a silent pass -- the failure mode this whole file
#: is about.
#:
#: The counts in the comments are what task 82 recorded by hand on 2026-08-23 and what this
#: file measures now. Where they differ, the measurement is in the ticket.
MUTANTS: dict[str, tuple[str, str, tuple[str, ...]]] = {
    # The half that actually hurt. `check` read commit 436bf64 as clean for 25m48s (#141) while
    # task 71's agent worked from a body of "\n\n"; containment cannot see an empty body,
    # because an empty body resembles nothing.
    "no_empty_body": (
        '        if not (t.get("body") or "").strip():',
        '        if False:  # MUTANT: the empty-body branch is gone',
        ("`check` on empty body", "FAILS on the real 436bf64 pair")),
    # The threshold, upper side: raise it past the one true positive the corpus contains and
    # the defect walks through. 0.50 is above 0.3615.
    "margin_up": (
        "MISFILED_MARGIN = 0.25",
        "MISFILED_MARGIN = 0.50  # MUTANT: above the 0.3615 true positive",
        ("FAILS on the real 436bf64 pair", "threshold, upper side")),
    # The threshold, lower side, and the only mutant here that is a VARIANT in disguise: it
    # asks whether the check can still stay QUIET. 0.13 is below the worst real non-defect
    # at 0.1399, so task 62 -- correctly filed, genuinely about task 70's subject -- gets
    # accused. A repair that "fixes" a miss by lowering the threshold dies on this row.
    "margin_down": (
        "MISFILED_MARGIN = 0.25",
        "MISFILED_MARGIN = 0.13  # MUTANT: below the 0.1399 worst false positive",
        ("threshold, lower side",)),
    # The floor under how short a brief may be before it can accuse anyone. Its row survived
    # this mutant on the first attempt in task 82, because the row's premise was vacuous --
    # see the comment on 5d in tasks_control.py. It is the reason that row now asserts its
    # own precondition, and the reason this mutant is worth keeping rather than assuming.
    "min_brief_zero": (
        "MISFILED_MIN_BRIEF = 8",
        "MISFILED_MIN_BRIEF = 0  # MUTANT: two coincident shingles may now accuse",
        ("MISFILED_MIN_BRIEF",)),
    # What a body is compared AGAINST. Comparing bodies to bodies is precisely what a
    # misfiling makes identical, so this is the change that would make the check agree with
    # the defect. `brief` is a module-level function so this mutant can exist.
    "brief_reads_body": (
        "    return f\"{_scalar(meta_or_fm.get('title'))} "
        "{_scalar(meta_or_fm.get('done_when'))}\"",
        "    return _scalar(meta_or_fm.get('body'))  # MUTANT: body, not title+done_when",
        ("FAILS on the real 436bf64 pair", "threshold, upper side")),
    # The REPORTING of the reachability warning, as distinct from the predicate behind it.
    # This mutation was this file's own inert mutation until `tasks/106`: direction 4 called
    # `reachability_warning` in process over 12 wordings and no row ran `check` end to end,
    # so `tasks.py` computed every warning, printed none, and the 34 rows that file then had
    # all stayed green -- exit 0, 0 FAILED. It
    # is a real mutant now because direction 4c reads `check`'s stdout on a scratch queue.
    "warn_never_printed": (
        "    if warn:",
        "    if False:  # MUTANT: warnings computed, never printed",
        ("end to end on an UNREACHABLE done_when",)),
    # The other half of direction 4c: its QUIET rows must be able to go red too, or they are
    # a negative control that cannot fail. Dropping the escape class accuses every done_when
    # that carries a universal, which is what task 38 was filed about -- so the row that must
    # notice is the one whose wording has both a universal and an escape (task 32's).
    "escape_ignored": (
        "    if not risky or _words(prose, HYPOTHETICAL):",
        "    if not risky:  # MUTANT: an escape branch no longer silences anything",
        ("end to end on a universal WITH an escape branch",)),
    # THE STATUS VOCABULARY. Dropping a value is the shape a half-landed rename takes, and it
    # is invisible to every row that only asks whether a WRONG status fails: `wip` is still
    # rejected with 4 values, or with 1. Two rows must notice -- the one that puts a file in
    # each state, and the one asserting heartbeat's map equals STATUSES.
    "status_dropped": (
        'STATUSES = ("todo", "in_progress", "in_review", "in_testing", "done")',
        'STATUSES = ("todo", "in_progress", "in_testing", "done")  # MUTANT: in_review gone',
        ("every one of the 5 statuses", "covers EXACTLY")),
    # THE LEGACY ALIASES, and this one is a VARIANT rather than a mutant (AGENTS.md rule 15):
    # it does not remove a mechanism a row names, it feeds the queue an input the check must
    # still stay QUIET on. Losing it turns every peer's `check` red on a file written by an
    # agent whose worktree forked before 2026-08-23.
    "legacy_dropped": (
        'LEGACY_STATUSES = {"open": "todo", "in_flight": "in_progress"}',
        "LEGACY_STATUSES = {}  # MUTANT: a stale worktree's `in_flight` now fails the lint",
        ("legacy `open` and `in_flight` still lint clean",
         "maps the legacy names onto the canonical states")),
    # A TRANSITION WIRED TO THE WRONG CONSTANT. `check` cannot see this: the queue lints clean
    # either way and reports a state nobody chose. Only direction 7, which reads the file back
    # after running the command, can.
    "start_writes_todo": (
        '        return _set(a.id, status="in_progress")',
        '        return _set(a.id, status="todo")  # MUTANT: `start` claims nobody has it',
        ("`start` writes status in_progress",)),
    # The `in_review`-without-a-pull-request branch. Without it the state stops being a
    # locator and the orchestrator is back to opening every PR to find which is its turn.
    "review_needs_no_pr": (
        '        if t.get("status") == "in_review" and not (t.get("pr") or "").strip():',
        "        if False:  # MUTANT: in_review no longer has to name its pull request",
        ("`in_review` with no `pr`",)),
}

#: THIS RUNNER'S OWN POSITIVE CONTROL: a mutation that must SURVIVE. `--selftest` runs it
#: and requires the control to come back FULLY GREEN -- exit 0, no red row at all -- because
#: "every mutant caught" from a harness structurally incapable of saying anything else is
#: rule 1's `total=0 passed=0`, and every mutant above is a NEGATIVE control.
#:
#: IT IS INERT BY CONSTRUCTION, AND THAT IS THE CHANGE `tasks/106` PAID FOR. Until then this
#: was a real coverage gap -- `if warn:` -> `if False:`, warnings computed and never printed
#: -- on the argument that a measured gap beats a synthetic no-op. The argument is wrong for
#: a POSITIVE control, because it couples the runner's own control to a defect somebody is
#: supposed to fix: closing the gap (direction 4c) turned the inert mutation into a caught
#: one and broke `--selftest` by design, and the work of closing it then had to carry a
#: second, unrelated repair. A positive control must not have an expiry date.
#:
#: A TRAILING COMMENT ON `MISFILED_MARGIN`'s LINE cannot expire: it changes no value, so no
#: behavioural row can ever go red on it, and no future row can "cover" it. The line is
#: chosen deliberately: `margin_up` and `margin_down` mutate THE SAME LINE and are both
#: caught, so SURVIVED here cannot be read as "nothing tests that line". It separates the
#: two claims the old design conflated -- *the runner can report a survivor* (here) and
#: *tasks.py has an untested mechanism* (a task in `tasks/`, where it can be fixed).
SELFTEST_MUTANT = (
    "MISFILED_MARGIN = 0.25",
    "MISFILED_MARGIN = 0.25  # INERT: a comment changes no value. margin_up and "
    "margin_down mutate this same line and are both caught.")

#: `  FAIL <row name>: <detail>` in tasks_control.py's summary block. Anchored at the line
#: start so a detail string containing the word FAIL cannot manufacture a row.
_FAIL_RE = re.compile(r"^  FAIL (.+?): ", re.M)
_ROW_RE = re.compile(r"^(\S.*?)\s{2,}\d+\s+(ok  |FAIL)\s", re.M)


def _write_copy(tmp: Path, name: str, mutant: str | None) -> Path:
    """A tempdir holding the copy under test, and a symlink to the real queue.

    The layout matters: `tasks.py` derives its queue from `git worktree list` and falls back
    to `parents[2]` when that fails, and a tempdir is not a checkout. So the copy goes at
    `<tmp>/<name>/eval/tools/tasks.py`, making the fallback root `<tmp>/<name>`, and
    `<tmp>/<name>/tasks` points at the real queue. Every row that reads it only reads.
    """
    root = tmp / name
    (root / "eval" / "tools").mkdir(parents=True)
    src = SOURCE.read_text()
    if mutant is not None:
        old, new, _ = MUTANTS[mutant]
        n = src.count(old)
        if n != 1:
            raise SystemExit(
                f"mutant `{mutant}` does not apply: its anchor occurs {n} times in "
                f"{SOURCE}. A no-op mutant reports a pass for a check that never changed, "
                f"and an ambiguous one mutates whichever copy came first. Fix the anchor.")
        src = src.replace(old, new, 1)
    (root / "eval" / "tools" / "tasks.py").write_text(src)
    if QUEUE.is_dir():
        (root / "tasks").symlink_to(QUEUE)
    return root / "eval" / "tools" / "tasks.py"


def _grade(copy: Path) -> tuple[int, str, list[str], list[str]]:
    """Run the REAL tasks_control.py against `copy`. Unpiped; the exit code is read as-is."""
    p = subprocess.run([sys.executable, str(CONTROL), "--tasks-py", str(copy)],
                       capture_output=True, text=True)
    out = (p.stdout or "") + (p.stderr or "")
    return p.returncode, out, _FAIL_RE.findall(out), [m[0] for m in _ROW_RE.findall(out)]


def _report(out: str, limit: int = 4) -> None:
    for line in out.strip().split("\n")[-limit:]:
        print(f"        {line[:150]}")


def _cycle(tmp: Path, name: str) -> bool:
    """One mutant, graded and reported. Returns whether the row naming it went red."""
    old, _new, kills = MUTANTS[name]
    rc, out, failed, rows = _grade(_write_copy(tmp, name, name))
    unnamed = [f for f in failed if not any(k in f for k in kills)]
    missed = [k for k in kills if not any(k in f for f in failed)]
    caught = rc == 1 and not missed
    print(f"\n=== MUTANT {name}: {'CAUGHT' if caught else 'SURVIVED'} "
          f"(exit {rc}, {len(failed)} red of {len(rows)})")
    print(f"    removes: {old.strip()[:100]}")
    for f in failed:
        print(f"    red{'  ' if any(k in f for k in kills) else '? '} {f}")
    if missed:
        print(f"    NO ROW NAMING ITS MECHANISM WENT RED: {missed}")
        _report(out)
    if unnamed:
        print(f"    also red, not named by this mutant: {len(unnamed)}")
    return caught


def selftest(tmp: Path) -> int:
    """Can this runner report a SURVIVOR, and does it refuse a mutant that has drifted?

    Both are asked of the runner, not of `tasks.py`. A file that can only print CAUGHT
    proves nothing by printing CAUGHT six times.

    INERT IS A PROPERTY OF THE WHOLE REPORT, NOT OF ONE ROW NAME. This used to ask "did the
    row I named go red?", which is the enumeration failure AGENTS.md's rule audit describes.
    Measured while closing `tasks/106`: the new end-to-end row DID go red under the old
    inert mutation, the row it named did not, and `--selftest` printed `ok` over a mutation
    that had stopped being inert. The question is whether ANY row went red.
    """
    bad = []
    old, new = SELFTEST_MUTANT
    MUTANTS["_selftest_inert"] = (old, new, ())
    try:
        copy = _write_copy(tmp, "_selftest_inert", "_selftest_inert")
    finally:
        del MUTANTS["_selftest_inert"]
    rc, out, failed, rows = _grade(copy)
    inert = rc == 0 and not failed
    print(f"\n=== INERT MUTATION: {'SURVIVED' if inert else 'CAUGHT'} "
          f"(exit {rc}, {len(failed)} red of {len(rows)})")
    print(f"    adds: {new.strip()[:110]}")
    for f in failed:
        print(f"    red   {f}")
    if not inert:
        _report(out)
    print(f"\n  {'ok  ' if inert else 'FAIL'} the INERT mutation leaves EVERY row green")
    if not inert:
        bad.append("the inert mutation was CAUGHT. It changes no value, so this is the "
                   "harness or the anchor, not a gap somebody closed: read the red rows "
                   "above before picking a different mutation.")

    # A mutant whose anchor has drifted must REFUSE, not quietly apply nothing. A no-op
    # mutant reports a pass for a check that never changed.
    MUTANTS["_selftest_drift"] = ("A STRING THAT IS NOT IN tasks.py", "x", ("anything",))
    try:
        _write_copy(tmp, "_selftest_drift", "_selftest_drift")
        drifted_ok = False
    except SystemExit:
        drifted_ok = True
    finally:
        del MUTANTS["_selftest_drift"]
    print(f"  {'ok  ' if drifted_ok else 'FAIL'} a mutant whose anchor is absent REFUSES "
          f"rather than applying nothing")
    if not drifted_ok:
        bad.append("a drifted anchor applied silently")

    for b in bad:
        print(f"  FAIL {b}")
    return 1 if bad else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--mutate", metavar="NAME", help="one mutant instead of every one")
    ap.add_argument("--list", action="store_true", dest="list_mutants")
    ap.add_argument("--selftest", action="store_true",
                    help="this runner's own two controls: an INERT mutation must be "
                         "reported as SURVIVED, and a drifted anchor must refuse")
    a = ap.parse_args()

    if a.list_mutants:
        for name, (old, _, kills) in MUTANTS.items():
            print(f"{name:18} removes: {old.strip()[:60]}\n{'':18} killed by: "
                  f"{', '.join(kills)}")
        return 0
    if a.mutate and a.mutate not in MUTANTS:
        raise SystemExit(f"unknown mutant {a.mutate}; --list")

    names = [a.mutate] if a.mutate else list(MUTANTS)
    before = SOURCE.read_bytes()
    if not QUEUE.is_dir():
        print(f"WARNING: no queue at {QUEUE} - direction 1 and the task-32 pin will report "
              f"NOT CHECKED in every run below, including the baseline.", file=sys.stderr)

    # THREE ADDRESSES, PRINTED. What is mutated, what grades it, and what corpus it reads --
    # a correct method aimed at an unverified address is this project's commonest wrong
    # answer, and it always looks like a result (AGENTS.md rule 12).
    print(f"subject:  {SOURCE}\ncontrol:  {CONTROL}\nqueue:    {QUEUE}")

    with tempfile.TemporaryDirectory(prefix="tasks-mutants-") as td:
        tmp = Path(td)

        # THE BASELINE. Same tempdir, same symlink, same --tasks-py path, no mutation.
        print("=== BASELINE: an UNMUTATED copy, graded through the same path")
        rc, out, failed, rows = _grade(_write_copy(tmp, "_baseline", None))
        print(f"    exit {rc}, {len(rows)} rows, {len(failed)} FAILED")
        if rc != 0 or failed:
            print("    THE BASELINE IS NOT GREEN. Every result below is uninterpretable: a "
                  "red row under a mutant would be equally well explained by the harness.")
            _report(out, 12)
            return 2
        # The row names every `kills` entry is matched against must EXIST. A renamed row
        # would otherwise turn into "the mutant survived", which reads as a defect in
        # tasks.py rather than in this file.
        named = {k for _, _, kills in MUTANTS.values() for k in kills}
        missing = sorted(k for k in named if not any(k in r for r in rows))
        if missing:
            print(f"    ROW NAMES NOT FOUND in the baseline: {missing}. These are what "
                  f"`kills` is matched against; the rows were renamed or deleted.")
            return 2
        print(f"    baseline green, and all {len(named)} named rows are present")

        survivors = [name for name in names if not _cycle(tmp, name)]
        rc_self = selftest(tmp) if a.selftest else 0

    print(f"\n{len(names)} mutant(s), {len(survivors)} survived"
          + (f": {', '.join(survivors)} - tasks_control.py does not test what those rows "
             f"name" if survivors else " - every one killed by the row naming its "
             f"mechanism"))

    # #134: the constraint this file is built around. Asserted, not promised in a comment.
    if SOURCE.read_bytes() != before:
        print(f"\nFAIL {SOURCE} CHANGED during this run. A control must not be able to "
              f"damage the thing it controls; recover it with git before doing anything "
              f"else.")
        return 2
    print(f"{SOURCE.name} byte-identical before and after; the shared queue is read-only "
          f"here.")
    return 1 if (survivors or rc_self) else 0


if __name__ == "__main__":
    raise SystemExit(main())
