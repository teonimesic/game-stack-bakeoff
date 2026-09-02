#!/usr/bin/env python3
"""Pin `docstat.py`'s in-block duplicate-fragment check in BOTH directions (task 119).

The check finds a word window that occurs twice inside ONE paragraph, list item or
frontmatter key — the debris a rewrite applied to half of a claim leaves behind. Its one
known instance is `DECISIONS.md` at 75dde71, removed by hand under task 116 after every
gate in the repository read exit 0 over it.

Two halves, and the second is the one that matters (AGENTS.md rule 15):

  MUTANTS   remove a mechanism the controls name and assert the controls then FAIL. A mutant
            asks only whether the check CAN fail. Every mutant here is a plausible
            "simplification" of the shipped code, not an arbitrary corruption — `whole_line`
            in particular is the design that was tried first and measured as a complete false
            negative, so this control is what stops it being tried again silently.
  VARIANTS  inputs the check could plausibly MISHANDLE, which must keep coming out right.
            Correct markdown repeats itself constantly: tables repeat a stem down a column,
            an antithesis repeats a clause to carry an argument, a task file restates its
            `done_when` as its `established_by`. Each of those is a green row below, and each
            is a shape that occurs many times per document — a gate that reddens them is a
            gate that gets switched off.

Exit status is read UNPIPED (AGENTS.md rule 3). A mutant run is EXPECTED to fail, so this
script inverts it: exit 0 from a mutant run would mean the controls cannot see the mechanism
they name.

**The default runs the clean pass AND every mutant**, and is red if any of them survives -
the repair `corpus_control.sweep` records from PR 54, which this file had also not received.
The clean half is largely coverage `docstat --sweep` already buys: it runs this same check
over the same reference corpus and runs `_duplicate_fragment_pins` beside it, so a default
that only repeated it would gate what already gates while the mutants ran nowhere but an
operator's terminal. And `whole_line` is exactly the mutant a future reader has to be able
to watch die - it is the design measured at 0 true positives on the real defect, which makes
it the first thing a plausible "simplification" reaches for.

    python3 eval/tools/fragment_control.py                   # clean pass + every mutant - what CI runs
    python3 eval/tools/fragment_control.py --clean-only      # the controls alone, unmutated
    python3 eval/tools/fragment_control.py --list-mutants
    python3 eval/tools/fragment_control.py --mutate no_check
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import docstat as DS  # noqa: E402

#: The revision, and the line in it, whose answer is known in advance. Task 116 repaired
#: `DECISIONS.md` by hand, so HEAD cannot supply the defect and this is the only real
#: instance the project has. The expectation is stated HERE and never computed from the blob
#: by the code under test: a control that imports its expectation from its subject is not a
#: control (AGENTS.md rule 12's corollary).
RED_REV, RED_DOC, RED_LINE, RED_WINDOWS = "75dde71", "DECISIONS.md", 745, 4

MUTANTS = {
    "no_check": "the check is deleted - it returns no hits, whatever it is given",
    "whole_line": "only a whole repeated LINE counts, which is the design measured at 0 on "
                  "the real defect before the window was chosen",
    "one_block": "the whole document is one block, so any repeat anywhere in a file fires",
    "per_line": "words are not pooled across a block, so a duplicate that straddles a line "
                "break is invisible",
    "no_tables": "table rows are not excluded",
    "no_fence": "fenced lines are not excluded",
    "flat_frontmatter": "the frontmatter is one block rather than one block per key",
    "window_16": "the window is raised to 16, above the real defect's longest repeat",
}


# ---------------------------------------------------------------------------
# The fixtures. Built here rather than copied from a live file, so a control does not
# silently depend on today's wording of a document somebody may reword tomorrow. The one
# exception is the RED case, which is deliberately a real blob.
# ---------------------------------------------------------------------------

#: THE VARIANT THE TICKET NAMES: a rewrite applied to half of one bullet, wrapped so that the
#: duplicated span is broken at a DIFFERENT word in each copy. Nothing matches line-to-line
#: and no line of either copy is repeated whole, so only the block-level word sequence sees
#: it — and this is the shape the real defect had, in a list item with continuation lines.
SPLIT_ITEM = (
    "- **The rubric ceiling.** Tier 1 returned 1.0 on all 24 submissions and on all 16\n"
    "  of the audio run, 40 of 56 matrix trials at the ceiling with zero\n"
    "  variance, not merely near it. What to do about it was decided later.\n"
    "  The remedy is harder criteria, not a weight. 40 of 56 matrix trials at\n"
    "  the ceiling with zero variance, not merely near it, and it became a gate.\n")

#: The same defect in ordinary prose, with each copy COMPLETE within its own line - which is
#: how the real instance sat, at lines 737 and 745 of one bullet. Stated because the pair
#: brackets the two shapes rather than testing one twice: no mutant here separates them, and
#: claiming one did would be a control asserting more than it measures.
SAME_LINE = (
    "The gate reads the stored manifest and compares it with what the run actually wrote at "
    "the time of the upload, so a truncated one is visible.\n"
    "It then compares it with what the run actually wrote at the time of the upload, and "
    "became a gate rather than a score.\n")

#: An ANTITHESIS: deliberate parallel construction, the repetition carrying the argument.
#: Verbatim in shape from `DECISIONS.md`'s headroom blockquote, which is the single false
#: positive the corpus produced at window 10 and the reason the window is not 10.
ANTITHESIS = (
    "> **A criterion has headroom only if the quantity it observes lies on an axis the\n"
    "> prompt names a DIRECTION for.** A stated mechanic gives an axis with no direction\n"
    "> and every submission at the same point; a free parameter gives an axis with no\n"
    "> direction and every submission at a different point. Neither is a quality scale.\n")

#: Two paragraphs saying the same thing. Ordinary in a long document, and the reason the
#: block — not the file — is the unit.
TWO_PARAGRAPHS = (
    "A control shares the assumptions of the thing it controls unless you make it not,\n"
    "which is the failure this rule exists to prevent.\n\n"
    "A control shares the assumptions of the thing it controls unless you make it not,\n"
    "which is the failure this rule exists to prevent.\n")

TWO_ITEMS = (
    "- the judge reads the pack and scores the field on every criterion it was given\n"
    "- the judge reads the pack and scores the field on every criterion it was given\n")

FENCED = (
    "Sample output:\n\n```\n"
    "run the harness with the stored manifest and read the exit status unpiped\n"
    "run the harness with the stored manifest and read the exit status unpiped\n"
    "```\n")

TABLE = (
    "| what | why |\n|---|---|\n"
    "| the manifest of what the run dropped and why it dropped it, per file | kept |\n"
    "| the manifest of what the run dropped and why it dropped it, per file | kept |\n")

#: `tasks/42`: the goal restated as the result. The queue's designed workflow, and the only
#: hit the archive produced at window 12 before frontmatter keys were separated.
TASK_FRONTMATTER = (
    "---\n"
    "established_by: 'the block now states that every judge round stored before the re-pack "
    "read a field that no longer exists, and it does'\n"
    "id: 42\n"
    "done_when: the block states that every judge round stored before the re-pack read a "
    "field that no longer exists\n"
    "---\n\nSome prose that repeats nothing.\n")

#: ...and the half separating keys buys that masking the header outright would not:
#: `established_by` is routinely a paragraph on one line, and a rewrite can strand a fragment
#: inside it exactly as it can inside a bullet.
ONE_VALUE_FRONTMATTER = (
    "---\nid: 7\n"
    "established_by: 'the sweep reads the stored manifest and compares it with what the run "
    "wrote, so a truncated upload is visible; the sweep reads the stored manifest and "
    "compares it with what the run wrote'\n"
    "---\n\nProse.\n")


def run(text: str, rel: str = "pin.md") -> list[str]:
    return DS._check_duplicate_fragment(text, rel)


class Result:
    def __init__(self) -> None:
        self.rows: list[tuple[bool, str, str]] = []

    def check(self, ok: bool, name: str, detail: str = "") -> None:
        self.rows.append((ok, name, detail))

    def report(self) -> int:
        bad = [r for r in self.rows if not r[0]]
        for ok, name, detail in self.rows:
            print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"  -- {detail}" if detail else ""))
        print(f"\n{len(self.rows) - len(bad)}/{len(self.rows)} controls passed")
        return 1 if bad else 0


def controls() -> int:
    r = Result()

    # THE REAL DEFECT, from the tree that carried it. Everything else on this page is a
    # fixture somebody wrote; this row is the only one where the input was not designed by
    # the same person who designed the check.
    blob = DS._git("show", f"{RED_REV}:{RED_DOC}")
    if not blob.strip():
        # `_git` returns "" on a non-zero exit and never raises, so the failure mode to guard
        # is an empty string. Unproven is a FAIL, not a skip: a shallow clone reaches here,
        # and no hits with nothing to find is indistinguishable from a check that cannot fire.
        r.check(False, f"REAL: {RED_REV}:{RED_DOC} could not be read",
                "nothing here shows the check can fire at all")
    else:
        hits = run(blob, RED_DOC)
        at = [h for h in hits if h.startswith(f"{RED_DOC}:{RED_LINE}:")]
        r.check(len(hits) == RED_WINDOWS and len(at) == RED_WINDOWS,
                f"REAL: the half-applied rewrite at {RED_DOC}:{RED_LINE} in {RED_REV}",
                f"{len(hits)} hit(s), {len(at)} at line {RED_LINE}, expected "
                f"{RED_WINDOWS} and {RED_WINDOWS}")

    # ...and the same file at HEAD, which task 116 repaired by hand. The pair is what makes
    # the row above a measurement of the DEFECT rather than of the document.
    head = os.path.join(DS.ROOT, RED_DOC)
    hits = run(open(head, encoding="utf-8", errors="replace").read(), RED_DOC) \
        if os.path.exists(head) else ["missing"]
    r.check(not hits, f"REAL, repaired: {RED_DOC} at HEAD is clean", f"{len(hits)} hit(s)")

    r.check(len(run(SAME_LINE)) >= 1, "POSITIVE: a fragment duplicated inside one paragraph",
            f"{len(run(SAME_LINE))} hit(s)")

    # THE VARIANT THE TICKET NAMES. The shape the real defect had, wrapped one word
    # differently — the input a per-line implementation mishandles while passing every other
    # row on this page.
    r.check(len(run(SPLIT_ITEM)) >= 1,
            "VARIANT: a duplicated fragment split across a list-item line break",
            f"{len(run(SPLIT_ITEM))} hit(s)")

    r.check(len(run(ONE_VALUE_FRONTMATTER)) >= 1,
            "POSITIVE: a fragment duplicated inside ONE frontmatter value",
            f"{len(run(ONE_VALUE_FRONTMATTER))} hit(s)")

    # The greens. Every one occurs in correct markdown, most of them many times a document.
    for name, text in (
        ("VARIANT: an antithesis - parallel construction carrying an argument", ANTITHESIS),
        ("VARIANT: the same window in two different paragraphs", TWO_PARAGRAPHS),
        ("VARIANT: the same window in two top-level list items", TWO_ITEMS),
        ("VARIANT: a duplicated window inside a ``` fence", FENCED),
        ("VARIANT: two table rows repeating a long stem", TABLE),
        ("VARIANT: a task file restating done_when in established_by", TASK_FRONTMATTER),
    ):
        hits = run(text)
        r.check(not hits, name, f"{len(hits)} hit(s)" + (f": {hits[0][-60:]}" if hits else ""))

    # THE ADDRESS IS AN INPUT TO THE CHECK (#60). Finding nothing is the one result this
    # control cannot distinguish from being aimed at a corpus that is not there, so the
    # corpus-wide green states its population out loud.
    docs = DS.reference_docs()
    corpus_hits: list[str] = []
    for p in docs:
        corpus_hits += run(open(p, encoding="utf-8", errors="replace").read(),
                           os.path.relpath(p, DS.ROOT))
    r.check(bool(docs) and not corpus_hits,
            f"CORPUS: {len(docs)} reference docs, live AND archive, at window "
            f"{DS._DUP_FRAGMENT_WINDOW}",
            f"{len(corpus_hits)} hit(s)" + (f": {corpus_hits[0][:70]}" if corpus_hits else "")
            + ("; the corpus is EMPTY - this control is aimed at nothing" if not docs else ""))
    return r.report()


#: Every module attribute a mutant may rebind. `main` snapshots these before and after so a
#: mutant that silently changed nothing is a FAILURE rather than a run of green rows.
PATCHED = ("_check_duplicate_fragment", "_fragment_blocks", "_fence_mask",
           "_DUP_TABLE_RX", "_DUP_FRAGMENT_WINDOW")


def apply_mutant(name: str) -> None:
    """Remove one mechanism the controls name.

    PATCHING A CONSTANT IS SAFE HERE ONLY BECAUSE `_check_duplicate_fragment` READS BOTH OF
    ITS CONSTANTS AT CALL TIME, as module globals, rather than capturing them at import or
    as default arguments. A constant patched after import is otherwise a value that has
    already been read, which is how a lint control once linted the real tree while claiming
    a bad root (AGENTS.md rule 12). That property is not promised in a comment: `main`
    asserts every name in `PATCHED` before and after, and a mutant whose rows all pass is
    reported as testing nothing.
    """
    if name == "no_check":
        DS._check_duplicate_fragment = lambda text, rel: []
    elif name == "whole_line":
        def whole_line(text, rel):
            lines = text.split("\n")
            fenced = DS._fence_mask(lines)
            out, seen = [], {}
            for a, b in DS._fragment_blocks(lines):
                seen = {}
                for i in range(a, b):
                    if fenced[i] or not lines[i].strip():
                        continue
                    key = " ".join(DS._fragment_words(lines[i].strip()))
                    if key in seen:
                        out.append(f"{rel}:{i + 1}: repeated line")
                    seen[key] = i + 1
            return out
        DS._check_duplicate_fragment = whole_line
    elif name == "one_block":
        DS._fragment_blocks = lambda lines: [(0, len(lines))]
    elif name == "per_line":
        DS._fragment_blocks = lambda lines: [(i, i + 1) for i in range(len(lines))]
    elif name == "no_tables":
        DS._DUP_TABLE_RX = re.compile(r"^(?!)")  # matches nothing
    elif name == "no_fence":
        DS._fence_mask = lambda lines: [False] * len(lines)
    elif name == "flat_frontmatter":
        DS._fragment_blocks = DS._claim_blocks
    elif name == "window_16":
        DS._DUP_FRAGMENT_WINDOW = 16
    else:
        raise SystemExit(f"unknown mutant {name}; --list-mutants")


def sweep() -> int:
    """The clean run and EVERY mutant, in one invocation.

    THIS IS WHAT THE CI STEP RUNS, and it is why the step exists at all - the repair
    `corpus_control.sweep` records from PR 54, which this file had not received: with the
    default at `controls()` alone, the gate repeated the clean half `docstat --sweep`
    already runs over the same corpus, and no mutant ever ran outside an operator's
    terminal. A suite whose mutants are opt-in is a suite whose mutants are the one thing
    nobody re-runs - and `whole_line` is the recorded design that measured as a complete
    false negative, so its continued inability to pass is exactly what a bare clean run
    cannot assert.
    """
    print(f"duplicate-fragment controls, window {DS._DUP_FRAGMENT_WINDOW}\n")
    clean_failed = controls()
    print(f"\nCLEAN  {'FAILED' if clean_failed else 'passed'}, expected passed\n")

    pristine = {n: getattr(DS, n) for n in PATCHED}
    killed: list[str] = []
    survived: list[str] = []
    for name in MUTANTS:
        for n, v in pristine.items():  # a mutant must not leak into the next
            setattr(DS, n, v)
        apply_mutant(name)
        if all(getattr(DS, n) is pristine[n] for n in PATCHED):
            survived.append(f"{name}: rebound nothing - it is not testing anything")
            continue
        failed = controls()
        print(f"\nMUTANT {name:<18} "
              + ("SURVIVED  <- the controls cannot see the mechanism it names"
                 if not failed else "went red, as it must"))
        (survived if not failed else killed).append(name)
    for n, v in pristine.items():
        setattr(DS, n, v)

    print(f"\n{len(killed)} of {len(MUTANTS)} mutants died; "
          f"{len(survived)} survived"
          + ("" if not survived else ":\n  " + "\n  ".join(survived)))
    if clean_failed or survived:
        return 1
    print("A mutant run is EXPECTED to fail its controls; a mutant that survives means "
          "the controls no longer reach the mechanism they name, and the gate's green "
          "is once again the ambiguity this file exists to prevent.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    # One mode per invocation: `--clean-only --mutate NAME` used to run the mutation path
    # and silently ignore the other flag, and an accepted-but-ignored flag is worse than
    # an unsupported one (rule 13). argparse refuses the combination with exit 2.
    modes = ap.add_mutually_exclusive_group()
    modes.add_argument("--mutate", metavar="NAME")
    modes.add_argument("--list-mutants", action="store_true")
    modes.add_argument("--clean-only", action="store_true",
                       help="the controls on the unmutated tree, without the mutant sweep")
    a = ap.parse_args()
    if a.list_mutants:
        for k, v in MUTANTS.items():
            print(f"  {k:<18} {v}")
        return 0

    if a.mutate:
        before = tuple(getattr(DS, n) for n in PATCHED)
        apply_mutant(a.mutate)
        after = tuple(getattr(DS, n) for n in PATCHED)
        if before == after:
            print(f"MUTANT {a.mutate} changed nothing - it is not testing anything")
            return 1
        print(f"MUTANT {a.mutate}: {MUTANTS[a.mutate]}\n")
        rc = controls()
        print("\nA mutant run is EXPECTED to fail. Exit 0 here would mean the controls "
              "cannot see the mechanism they name.")
        return 0 if rc else 1

    if a.clean_only:
        print(f"duplicate-fragment controls, window {DS._DUP_FRAGMENT_WINDOW}\n")
        return controls()

    return sweep()


if __name__ == "__main__":
    sys.exit(main())
