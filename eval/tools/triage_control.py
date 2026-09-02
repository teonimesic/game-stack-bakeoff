#!/usr/bin/env python3
"""Controls for the renumber-triage register in `docstat.py`.

The register was GREEN the moment it was written, because it was written from the rows it
adjudicates. A gate that has only ever been green cannot be distinguished from one that
cannot go red, so every property it claims is asserted here against an input built to
violate it.

    ./triage_control.py           # the controls; exit 1 if any fails

WHAT IS CONTROLLED, and why each exists rather than being obvious:

  UNMATCHED   an entry whose anchor no longer occurs in the file it names must FAIL. This
              is the whole gate: a verdict recorded against a sentence somebody has since
              rewritten no longer describes anything, and it resolves silently because
              nothing about it dangles.
  AMBIGUOUS   an anchor occurring twice must FAIL. Two matches means the entry does not say
              which row it adjudicated, and picking the first would make the verdict a
              coin flip that reads as a verdict.
  ABSENT      an entry naming a file that does not exist must FAIL.
  SELF        an anchor that does not contain the citation it claims to adjudicate must
              FAIL. It cannot have come from that row. This one is not hypothetical: it
              caught a bad key while the register was being written by hand (task 102).
  UNPARSEABLE a register that does not parse must be REPORTED, never read as an empty one.
              An empty register and an unreadable one produce the same silence, and the
              silence means a register of rows nobody has read - the vacuous pass this
              module exists to prevent.
  CLEAN       the real register over the real tree must be green, and must adjudicate the
              number of rows it claims. Without this the reds above could all be coming
              from a check that fails on everything.
  VARIANT     THE ONE THAT DECIDES WHETHER THE DESIGN IS RIGHT, and a variant rather than
              a mutant (AGENTS.md rule 15). Inserting lines ABOVE a citing sentence moves
              its line number and changes nothing about the citation. A register keyed by
              line number would unpair every entry below the insertion and report a wall
              of rows as untriaged, with no defect anywhere. Keyed by the citing text, it
              must still match. A mutant cannot ask this - only an input the check might
              mishandle can.
  TRUNCATION  the second variant, and the bug this shipped with. A citation past column 96
              of its line must still match: `_check_renumbered_citations` truncates the
              excerpt it PRINTS, and matching against that instead of against the line put
              4 adjudicated rows in the UNTRIAGED list, indistinguishable from 4 nobody
              had read. `established_by` lines run to thousands of characters, so this is
              the common case in `tasks/`, not the corner.
"""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import docstat  # noqa: E402

FAILURES: list[str] = []


def check(name: str, ok: bool, detail: str) -> None:
    print(f"  {'ok  ' if ok else 'FAIL'}  {name}: {detail}")
    if not ok:
        FAILURES.append(name)


class Tree:
    """A temp tree docstat's constants are pointed at, with the redirect PROVEN.

    AGENTS.md rule 12's fifth instance is a monkeypatched constant that had already been
    consumed at import, so the check linted the real tree while the control believed it
    was reading a planted one. The REDIRECT control in `register_controls` refuses to let
    the suite pass until an entry that is red ONLY in the temp tree comes back red.
    """

    def __init__(self) -> None:
        self.dir = Path(tempfile.mkdtemp(prefix="triage-control-"))
        self._root, self._path = docstat.ROOT, docstat.TRIAGE_PATH
        docstat.ROOT = str(self.dir)
        docstat.TRIAGE_PATH = str(self.dir / "renumber_triage.json")

    def write(self, rel: str, text: str) -> None:
        p = self.dir / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")

    def register(self, entries: list[dict] | str) -> None:
        p = self.dir / "renumber_triage.json"
        p.write_text(entries if isinstance(entries, str)
                     else json.dumps(entries), encoding="utf-8")

    def problems(self) -> list[str]:
        return docstat._check_triage_register()

    def close(self) -> None:
        docstat.ROOT, docstat.TRIAGE_PATH = self._root, self._path
        shutil.rmtree(self.dir, ignore_errors=True)


def entry(path="doc.md", cites=99, anchor="the measurement is #99",
          verdict="correct", note="n") -> dict:
    return {"path": path, "cites": cites, "anchor": anchor,
            "verdict": verdict, "note": note, "triaged": "control"}


def register_controls() -> None:
    print("\nTHE GATE (_check_triage_register)")
    t = Tree()
    try:
        # The redirect itself, proven before anything is concluded from it.
        t.write("doc.md", "nothing here\n")
        t.register([entry()])
        p = t.problems()
        check("REDIRECT", len(p) == 1 and "doc.md" in p[0],
              f"the temp tree is what is being read: {len(p)} problem(s)")

        check("UNMATCHED", any("no longer exists" in x for x in p),
              "an anchor that occurs nowhere in its file is named")

        t.write("doc.md", "a: the measurement is #99\nb: the measurement is #99\n")
        p = t.problems()
        check("AMBIGUOUS", len(p) == 1 and "occurs 2 times" in p[0],
              "an anchor matching two lines does not say which row it adjudicated")

        t.write("doc.md", "the measurement is #99\n")
        p = t.problems()
        check("CLEAN-1", p == [], "one entry matching exactly one line is green")

        t.register([entry(path="gone.md")])
        p = t.problems()
        check("ABSENT", len(p) == 1 and "does not exist" in p[0],
              "an entry naming a missing file is named")

        t.register([entry(cites=104)])
        p = t.problems()
        check("SELF", len(p) == 1 and "does not contain that citation" in p[0],
              "an anchor that does not contain #104 cannot have adjudicated #104")

        t.register("{not json")
        p = t.problems()
        check("UNPARSEABLE", len(p) == 1 and "not an empty one" in p[0],
              "a register that does not parse is reported, not read as empty")
    finally:
        t.close()


def matching_controls() -> None:
    """The other half: does a recorded verdict still PAIR with its row?

    The gate above asks whether an entry resolves. This asks whether the pairing survives
    the two things that move a citation without changing it.
    """
    print("\nTHE PAIRING (_triage_for over a row's real line)")
    t = Tree()
    try:
        idx = docstat._triage_index([entry()])
        # THE ADDRESS IS AN ARGUMENT AT THE MOMENT OF USE (AGENTS.md rule 12). The
        # monkeypatch below steers `docstat.ROOT` for callers that read the global at
        # call time, but `_History` takes its root as a parameter with the real root as
        # the default - bound at import, deaf to the patch. Passing it explicitly is what
        # makes `doc.md` below resolve to the temp tree's row; measured 2026-08-29 (task
        # 208) when threading `root` through `_History` turned these three controls red
        # while each still read the real repository and called it the fixture.
        hist = docstat._History("HEAD", root=str(t.dir))
        hist.worktree = True
        line = "prose prose the measurement is #99 more prose"
        t.write("doc.md", "\n".join(["header", line]))
        got = docstat._triage_for(idx, "doc.md:2", 99, docstat._row_line(hist, "doc.md:2"))
        check("PAIRS", got is not None, "a row whose line contains the anchor pairs")

        # VARIANT: the citation has not changed; only its line number has.
        t.write("doc.md", "\n".join(["x"] * 40 + [line]))
        got = docstat._triage_for(idx, "doc.md:41", 99,
                                  docstat._row_line(hist, "doc.md:41"))
        check("VARIANT line-number drift", got is not None,
              "40 lines inserted above it; a line-keyed register would unpair here")

        # VARIANT: the citation sits past the 96 characters the row's excerpt keeps.
        far = "z" * 300 + " the measurement is #99"
        t.write("doc.md", far + "\n")
        got = docstat._triage_for(idx, "doc.md:1", 99, docstat._row_line(hist, "doc.md:1"))
        check("VARIANT past column 96", got is not None,
              f"the citation is at column {far.index('the measurement')}, "
              f"beyond the printed excerpt")
        # ... and the negative that gives that variant its meaning.
        got = docstat._triage_for(idx, "doc.md:1", 99, far[:96])
        check("VARIANT control", got is None,
              "matched against the truncated excerpt it does NOT pair - which is the "
              "bug the variant exists to hold shut")

        t.write("doc.md", "prose with no anchor in it at all\n")
        got = docstat._triage_for(idx, "doc.md:1", 99, docstat._row_line(hist, "doc.md:1"))
        check("NEGATIVE", got is None, "a row the register does not cover stays untriaged")
    finally:
        t.close()


def live_controls() -> None:
    """The real register over the real tree. Reds above prove nothing if this is red too."""
    print("\nTHE REAL REGISTER")
    entries = docstat._load_triage()
    p = docstat._check_triage_register()
    check("CLEAN", p == [], f"{len(entries)} entries, {len(p)} problem(s)")

    _, undecided, _ = docstat._check_renumbered_citations()
    hist = docstat._History("HEAD")
    idx = docstat._triage_index(entries)
    unpaired = []
    for s in undecided:
        where, rest = s.split(": ", 1)
        num = int(rest.split("#", 1)[1].split(" ", 1)[0])
        if not docstat._triage_for(idx, where, num, docstat._row_line(hist, where)):
            unpaired.append(where)
    check("COVERAGE", not unpaired,
          f"{len(undecided)} undecidable row(s), {len(undecided) - len(unpaired)} paired"
          + (f"; UNPAIRED: {unpaired}" if unpaired else ""))


def main() -> int:
    register_controls()
    matching_controls()
    live_controls()
    print()
    if FAILURES:
        print(f"{len(FAILURES)} control(s) FAILED: {', '.join(FAILURES)}")
        return 1
    print("all controls passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
