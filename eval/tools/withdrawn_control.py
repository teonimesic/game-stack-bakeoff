#!/usr/bin/env python3
"""Controls for the withdrawal register in `docstat.py`.

The register is a gate that was GREEN the moment its first two customers were repaired.
A gate that has only ever been green is indistinguishable from a gate that cannot go red,
and that shape - a mechanism that runs, reports success and measures nothing - is behind
most findings in this repository. So every property the register claims is asserted here
against an input built to violate it.

    ./withdrawn_control.py                  # the controls
    ./withdrawn_control.py --mutate any_of  # prove they can go red
    ./withdrawn_control.py --list-mutants

WHAT IS CONTROLLED, and why each one exists rather than being obvious:

  POSITIVE      a retired figure planted as a current claim in a live document must be
                found. This is the whole point and it is the one thing a green register
                cannot demonstrate about itself.
  EXEMPTION     the same plant, with the entry id inside the block, must be green -
                otherwise the archive cannot state what it exists to record.
  WINDOW SCOPE  the id in a DIFFERENT block of the same file must NOT excuse the plant.
                Document-scope exemptions are how the aspect check next door once went
                vacuous: one legitimate disclaimer silenced every check in its file.
  CONJUNCTION   one of two patterns is not a statement. `1.70` alone is a cost, a version
                or a tau; the pair is the figure.
  ARCHIVE       `eval/findings/` states the retired pair repeatedly and correctly and must
                stay green, and the live/archive partition itself is asserted here rather
                than described in prose (AGENTS.md rule 12: when a path is spelled twice,
                assert the two spellings equal in code).
  ANCHOR        an entry whose patterns match nothing in its own anchor must FAIL. It is
                the register proving its extraction on a case whose answer is known in
                advance, before anyone believes the census.
  EMPTY         an empty corpus and an empty register must be reported, never returned as
                clean. Finding nothing is the one result a misaimed check shares with a
                clean repository.
  FENCE         a plant inside ``` is invisible. That is a documented LIMIT, and it is
                asserted so it stays measured: if fence handling changes, this control
                fails and the docstring gets corrected instead of quietly becoming false.
  HISTORICAL    the real repository at `25fe630`, the commit before task 54 ran, where the
                withdrawn pair really was published in three live documents. Real corpus,
                real enumeration, known answer.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import docstat as DS  # noqa: E402

#: The revision before task 54 retired the pair, and the three live documents #113 names
#: as publishing it there. This is the one control running over a real corpus with a real
#: answer stated in advance.
PRE_TASK_54 = "25fe630"
PRE_TASK_54_SITES = ("DECISIONS.md", "README.md", "eval/judge/JUDGING.md")

MUTANTS = {
    "any_of": "a block states an entry if ANY match pattern occurs, not all of them",
    "file_scope": "the entry id anywhere in the FILE exempts the file, not just the block",
    "one_block": "the whole document is one block",
    "no_archive": "nothing is classified as archive, so the log is gated like a live doc",
    "no_anchor": "the anchor proof is skipped",
}


# ---------------------------------------------------------------------------
# The fixture. A minimal live document, built rather than copied, so the control
# does not silently depend on the current wording of a real file.
# ---------------------------------------------------------------------------

HEAD = "# A live document\n\nSome prose that states nothing retired.\n\n"

CLAIM = ("| between-stack range of mean ranks (0-7) | **1.70** |\n"
         "| mean gap between a stack's OWN two trials | **2.05** |\n")


def doc(*parts: str) -> str:
    return HEAD + "\n".join(parts)


def run(corpus: dict[str, str], entries=None) -> list[str]:
    return DS.scan_withdrawn(entries if entries is not None else ENTRIES, corpus)


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

    # POSITIVE. The figure planted as a current claim, in its own block, no id anywhere.
    hits = run({"README.md": doc(CLAIM)})
    r.check(len(hits) == 1 and "WR-tier3-pair" in hits[0],
            "POSITIVE: a planted retired figure is found",
            f"{len(hits)} hit(s)" + (f": {hits[0][:70]}" if hits else ""))

    # EXEMPTION. Same plant, id inside the block. This is what every archive-style
    # withdrawal notice in a live document looks like once it adopts the convention.
    hits = run({"README.md": doc(CLAIM + "A previous version read this; WR-tier3-pair.\n")})
    r.check(not hits, "EXEMPTION: the id inside the block clears it", f"{len(hits)} hit(s)")

    # WINDOW SCOPE. The id present in the file, but in a DIFFERENT block. Must still fire:
    # a document-scope exemption is how a check becomes vacuous while reporting clean.
    hits = run({"README.md": doc("Elsewhere in this file: WR-tier3-pair.\n", CLAIM)})
    r.check(len(hits) == 1,
            "WINDOW SCOPE: the id in another block does NOT excuse the claim",
            f"{len(hits)} hit(s)")

    # ...and the mirror of it: adjacent blocks must not bleed into one another either way.
    hits = run({"README.md": doc(CLAIM, "WR-tier3-pair is declared in the next paragraph.\n")})
    r.check(len(hits) == 1,
            "WINDOW SCOPE: an id in the FOLLOWING block does not reach backwards",
            f"{len(hits)} hit(s)")

    # CONJUNCTION. Half the signature is not the signature.
    hits = run({"README.md": doc("The cheapest trial cost 1.70 dollars.\n")})
    r.check(not hits, "CONJUNCTION: one of two patterns is not a statement",
            f"{len(hits)} hit(s)")
    hits = run({"README.md": doc("Version 2.05 of the harness.\n")})
    r.check(not hits, "CONJUNCTION: the other pattern alone is not one either",
            f"{len(hits)} hit(s)")

    # FENCE. A documented limit, asserted so it cannot stop being true unnoticed.
    hits = run({"README.md": doc("```\n" + CLAIM + "```\n")})
    r.check(not hits, "FENCE (a known LIMIT, not a feature): a plant inside ``` is invisible",
            f"{len(hits)} hit(s)")

    # ARCHIVE. The partition, asserted in code. `eval/findings/certifies-nothing.md` states
    # the retired pair a dozen times and cites no id; it must be out of scope, and the
    # documents the ticket names as live must be in it.
    for live in ("README.md", "DECISIONS.md", "eval/RUNS.md", "eval/judge/RUBRIC.md",
                 "eval/judge/JUDGING.md", "eval/PROTOCOL.md", "research/11-x.md",
                 ".claude/skills/refine/SKILL.md"):
        r.check(not DS.is_archive(live), f"ARCHIVE: {live} is LIVE")
    for arch in ("eval/findings/certifies-nothing.md", "eval/FINDINGS.md",
                 "eval/IMPROVEMENTS.md", "IMPROVEMENTS.md", "CLEANUP-LOG.md",
                 "tasks/54-x.md", "eval/runs/wg-x/y.md"):
        r.check(DS.is_archive(arch), f"ARCHIVE: {arch} is exempt")

    # ...and the archive is only useful if it really does state the thing unmarked.
    anchor = os.path.join(DS.ROOT, "eval", "findings", "certifies-nothing.md")
    lines = open(anchor, encoding="utf-8", errors="replace").read().split("\n")
    e = next(x for x in ENTRIES if x["id"] == "WR-tier3-pair")
    unmarked = [(a, b) for a, b in DS._claim_blocks(lines)
                if DS._states(e, "\n".join(lines[a:b])) and e["id"] not in "\n".join(lines[a:b])]
    r.check(len(unmarked) >= 1,
            "ARCHIVE: the log really does state the retired pair with no id",
            f"{len(unmarked)} unmarked block(s) in certifies-nothing.md")

    # ANCHOR. An entry that matches nothing where it is known to be stated is silence.
    broken = [dict(e, match=["a-string-that-occurs-nowhere-in-this-repository"])]
    lines_ok = any(DS._states(broken[0], "\n".join(lines[a:b]))
                   for a, b in DS._claim_blocks(lines))
    r.check(not lines_ok, "ANCHOR: a mismatching entry does not match its anchor")
    problems, _ = _register_problems(broken)
    r.check(any("anchor" in p for p in problems),
            "ANCHOR: and the check reports it as a failure, not a pass",
            f"{len(problems)} problem(s)")

    # EMPTY. Both directions of the address question.
    corpus, corpus_problems = DS._live_corpus()
    r.check(len(corpus) > 30 and not corpus_problems,
            "ADDRESS: the live corpus at HEAD is non-empty", f"{len(corpus)} live docs")
    r.check("README.md" in corpus and "eval/FINDINGS.md" not in corpus,
            "ADDRESS: the corpus contains README.md and not the findings index")
    with tempfile.TemporaryDirectory() as td:
        p = os.path.join(td, "empty.json")
        open(p, "w").write('{"entries": []}')
        _, probs = DS.load_register(p)
        r.check(any("no entries" in x for x in probs),
                "EMPTY: a register with no entries is reported, not green")
        _, probs = DS.load_register(os.path.join(td, "absent.json"))
        r.check(any("missing" in x for x in probs),
                "EMPTY: a missing register is reported, not green")

    # HISTORICAL. Real corpus, real enumeration, answer known in advance: at the commit
    # before task 54 ran, the withdrawn pair was published in exactly the three live
    # documents #113 names.
    hist, hist_problems = DS._live_corpus(PRE_TASK_54)
    if hist_problems or not hist:
        r.check(False, f"HISTORICAL: could not read the tree at {PRE_TASK_54}",
                "; ".join(hist_problems)[:120])
    else:
        hits = run(hist)
        pair = {h.split(":")[0] for h in hits if "WR-tier3-pair" in h}
        for site in PRE_TASK_54_SITES:
            r.check(site in pair,
                    f"HISTORICAL: {site} published the pair at {PRE_TASK_54}")
        now, _ = DS._live_corpus()
        pair_now = {h.split(":")[0] for h in run(now) if "WR-tier3-pair" in h}
        r.check(not pair_now,
                "HISTORICAL: and no live document publishes it today", f"{sorted(pair_now)}")

    return r.report()


def _register_problems(entries: list[dict]) -> tuple[list[str], str]:
    """The anchor half of `_check_withdrawal_register`, for a hand-built entry list."""
    problems: list[str] = []
    for e in entries:
        anchor = os.path.join(DS.ROOT, e.get("anchor", ""))
        if not os.path.exists(anchor):
            problems.append(f"{e['id']}: anchor missing")
            continue
        lines = open(anchor, encoding="utf-8", errors="replace").read().split("\n")
        if not any(DS._states(e, "\n".join(lines[a:b])) for a, b in DS._claim_blocks(lines)):
            problems.append(f"{e['id']}: matches nothing in its anchor")
    return problems, ""


def apply_mutant(name: str) -> None:
    """Remove one mechanism the controls name. Patches FUNCTIONS, never constants.

    A constant patched after import is a value that has usually already been read - which
    is how a lint control once claimed a bad root while linting the real tree (#12's
    corollary). Every patch below is verified to have taken effect before the controls run.
    """
    if name == "any_of":
        DS._states = lambda e, t: any(re.search(p, t) for p in e.get("match") or [])
    elif name == "file_scope":
        orig = DS.scan_withdrawn

        def file_scope(entries, corpus):
            keep = {r: t for r, t in corpus.items()
                    if not any(e["id"] in t for e in entries)}
            return orig(entries, keep)
        DS.scan_withdrawn = file_scope
    elif name == "one_block":
        DS._claim_blocks = lambda lines: [(0, len(lines))]
    elif name == "no_archive":
        DS.is_archive = lambda rel: False
    elif name == "no_anchor":
        globals()["_register_problems"] = lambda entries: ([], "")
    else:
        raise SystemExit(f"unknown mutant {name}; --list-mutants")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mutate", metavar="NAME")
    ap.add_argument("--list-mutants", action="store_true")
    a = ap.parse_args()
    if a.list_mutants:
        for k, v in MUTANTS.items():
            print(f"  {k:<12} {v}")
        return 0

    global ENTRIES
    ENTRIES, problems = DS.load_register()
    if problems:
        print("the register itself does not load:")
        for p in problems:
            print(f"  {p}")
        return 1

    if a.mutate:
        before = (DS._states, DS._claim_blocks, DS.is_archive, DS.scan_withdrawn)
        apply_mutant(a.mutate)
        after = (DS._states, DS._claim_blocks, DS.is_archive, DS.scan_withdrawn)
        if before == after and a.mutate != "no_anchor":
            print(f"MUTANT {a.mutate} changed nothing - it is not testing anything")
            return 1
        print(f"MUTANT {a.mutate}: {MUTANTS[a.mutate]}\n")
        rc = controls()
        print("\nA mutant run is EXPECTED to fail. Exit 0 here would mean the controls "
              "cannot see the mechanism they name.")
        return 0 if rc else 1

    print(f"withdrawal register controls, {len(ENTRIES)} entries\n")
    return controls()


ENTRIES: list[dict] = []

if __name__ == "__main__":
    sys.exit(main())
