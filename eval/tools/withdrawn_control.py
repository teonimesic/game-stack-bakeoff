#!/usr/bin/env python3
"""Controls for the withdrawal register in `docstat.py`.

The register is a gate that was GREEN the moment its first two customers were repaired.
A gate that has only ever been green is indistinguishable from a gate that cannot go red,
and that shape - a mechanism that runs, reports success and measures nothing - is behind
most findings in this repository. So every property the register claims is asserted here
against an input built to violate it.

    ./withdrawn_control.py                  # the controls and every mutant - what CI runs
    ./withdrawn_control.py --clean-only     # the controls alone, unmutated
    ./withdrawn_control.py --mutate any_of  # one mutant, prove it goes red
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
  HISTORICAL    the real repository at a revision BEFORE each withdrawal landed, where the
                retired figure really was published in named live documents. Real corpus,
                real enumeration, known answer. See `HISTORICAL` for the one entry whose
                withdrawal predates the first commit and what its row does and does not prove.
  VARIANT       the REPLACEMENT wording - what every repaired document now says - must stay
                green. A mutant asks whether the check can fail; only a variant asks whether
                it can still pass on an input it might mishandle (AGENTS.md rule 15), and
                here that input is the sentence the repair produced. If `436 paired criteria,
                5 verdict differences` tripped the register, no document could be repaired at
                all and the only way to green would be to cite an id over a live figure.
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

#: (revision, entry id, live documents that published it there). The controls running over a
#: real corpus with the answer stated in advance. Each revision is the commit BEFORE that
#: entry's withdrawal landed, so the hit is a figure the project was really asserting:
#: `25fe630` precedes task 54 and `727759d` precedes the 380-paired-criteria withdrawal
#: (`307c957`), whose README headline row stated both halves of it as current evidence.
#:
#: `WR-20-of-24` IS THE EXCEPTION AND THE LIMIT IS STATED RATHER THAN SMOOTHED OVER. Its
#: withdrawal predates this repository's first commit, so no revision here states it as a
#: current claim and none ever will. `a3d0fd1` is the earliest tree that exists, and what
#: its row proves is narrower: the patterns fire on the real README wording, in a block that
#: at the time carried no marking a machine could read. The claim-as-current case for that
#: entry is covered by the planted POSITIVE controls instead, which is weaker evidence and
#: is named here so nobody reads the green as more than it is.
HISTORICAL = (
    ("25fe630", "WR-tier3-pair", ("DECISIONS.md", "README.md", "eval/judge/JUDGING.md")),
    ("727759d", "WR-paired-verdict-tie",
     ("README.md", "DECISIONS.md", "eval/judge/JUDGING.md")),
    ("727759d", "WR-paired-evidence-diff", ("README.md", "DECISIONS.md")),
    ("a3d0fd1", "WR-20-of-24", ("README.md",)),
)

MUTANTS = {
    "any_of": "a block states an entry if ANY match pattern occurs, not all of them",
    "file_scope": "the entry id anywhere in the FILE exempts the file, not just the block",
    "one_block": "the whole document is one block",
    "no_archive": "nothing is classified as archive, so the log is gated like a live doc",
    "no_anchor": "the anchor proof is skipped",
}

#: The `docstat` attributes `apply_mutant` may rebind - the before/after set for both the
#: single-mutant guard and the sweep's leak check. `no_anchor` patches this module's own
#: `_register_problems` and is invisible here, which is why the sweep checks it separately.
PATCHED = ("_states", "_claim_blocks", "is_archive", "scan_withdrawn")

#: Historical corpora, read once per PROCESS rather than once per `controls()` call. The
#: sweep runs the controls 6 times, and the `git show` behind each revision dominates the
#: step's cost - without this the sweep would pay it 6 times for one answer.
_CORPUS_CACHE: dict[str, dict[str, str]] = {}


# ---------------------------------------------------------------------------
# The fixture. A minimal live document, built rather than copied, so the control
# does not silently depend on the current wording of a real file.
# ---------------------------------------------------------------------------

HEAD = "# A live document\n\nSome prose that states nothing retired.\n\n"

CLAIM = ("| between-stack range of mean ranks (0-7) | **1.70** |\n"
         "| mean gap between a stack's OWN two trials | **2.05** |\n")

#: The three forms the retired ceiling count is written in. The numeric two are how README
#: stated it; the third is how the findings log states it, and it is the only one the anchor
#: proof exercises - so both branches of that entry's first pattern are proved, not one.
CLAIM_2024 = {
    "numeric": "The deterministic tiers: 20 of 24 cells score exactly 1.000.\n",
    "slash": "Eight combinations of three 8-cell groups give exactly 20/24 at 1.000.\n",
    "words": "Twenty of the twenty-four cells now sit at exactly 1.000.\n",
}

#: The 380 pair as README's headline row stated it at 727759d, on one line, since the
#: conjunction is what makes each entry a signature rather than a loose number.
CLAIM_380 = ("| **0 verdict differences across 380 paired criteria** | while **219 of 380 "
             "evidence strings do** differ |\n")

#: WHAT THE REPAIR PRODUCED. Every document repaired under task 62 now reads like this, and
#: the register must be green on it. Copied in wording, not in spirit, from README.md's
#: evidence table, DECISIONS.md's deterministic-tier section and JUDGING.md.
REPLACEMENT = (
    "`wg-matrix` (3 games, 436 paired criteria): **5** verdict differences against **332**\n"
    "differing evidence strings. `wg-audio48` (232 paired): **0** verdict differences,\n"
    "**120** differing evidence strings.\n"
    "Per game, never summed: pong **5/8**, tetris **5/8**, arena **5/8** at exactly 1.000.\n")


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

    # POSITIVE, per form, for the entries added under task 62. `WR-20-of-24`'s first pattern
    # is an alternation because README wrote the figure in digits and the findings log writes
    # it in words; the anchor proof only ever exercises the words branch, so each branch is
    # planted here separately. An alternation with an unproved branch is a pattern that has
    # been read, not measured.
    for form, text in CLAIM_2024.items():
        hits = run({"README.md": doc(text)})
        r.check(len(hits) == 1 and "WR-20-of-24" in hits[0],
                f"POSITIVE: the retired ceiling count is found in its {form} form",
                f"{len(hits)} hit(s)")

    hits = run({"README.md": doc(CLAIM_380)})
    found = {h.split("states `")[1].split("`")[0] for h in hits}
    r.check(found == {"WR-paired-verdict-tie", "WR-paired-evidence-diff"},
            "POSITIVE: the 380 row trips BOTH of its entries, separately",
            f"{sorted(found)}")

    # ...and each of those two is independently detectable, which is why they are two entries
    # and not one. A single entry over all three patterns would go quiet on a document that
    # restated only one half.
    hits = run({"README.md": doc("0 verdict differences across 380 paired criteria.\n")})
    found = {h.split("states `")[1].split("`")[0] for h in hits}
    r.check(found == {"WR-paired-verdict-tie"},
            "POSITIVE: the verdict half alone still fires, without the evidence half",
            f"{sorted(found)}")
    hits = run({"README.md": doc("219 of 380 evidence strings differ (58%).\n")})
    found = {h.split("states `")[1].split("`")[0] for h in hits}
    r.check(found == {"WR-paired-evidence-diff"},
            "POSITIVE: the evidence half alone still fires, without the verdict half",
            f"{sorted(found)}")

    # CONJUNCTION for the same three. A bare count is a number, not a claim.
    for label, text in (("20 of 24 with no score", "20 of 24 trials completed.\n"),
                        ("a lone 1.000", "godot scored 1.000 on tier 2.\n"),
                        ("a lone 380", "judge/static.py:380 raises on a missing recipe.\n"),
                        ("a lone 219", "the pack is 219 files.\n"),
                        ("380 without the verdict claim", "380 paired criteria were read.\n")):
        hits = run({"README.md": doc(text)})
        r.check(not hits, f"CONJUNCTION: {label} is not a statement", f"{len(hits)} hit(s)")

    # VARIANT (rule 15). The repaired wording - what the live documents say now - must stay
    # green. A check that fired on the replacement would make repair impossible: the only
    # route to green would be citing a withdrawal id over a figure that is current and true.
    hits = run({"README.md": doc(REPLACEMENT)})
    r.check(not hits, "VARIANT: the per-scope replacement wording stays green",
            f"{len(hits)} hit(s)" + (f": {hits[0][:70]}" if hits else ""))

    # FENCE. A documented limit, asserted so it cannot stop being true unnoticed.
    hits = run({"README.md": doc("```\n" + CLAIM + "```\n")})
    r.check(not hits, "FENCE (a known LIMIT, not a feature): a plant inside ``` is invisible",
            f"{len(hits)} hit(s)")

    # ARCHIVE. The partition, asserted in code. `eval/findings/certifies-nothing.md` states
    # the retired pair a dozen times and cites no id; it must be out of scope, and the
    # documents the ticket names as live must be in it.
    for live in ("README.md", "DECISIONS.md", "eval/RUNS.md", "eval/judge/RUBRIC.md",
                 "eval/judge/JUDGING.md", "eval/PROTOCOL.md", "research/11-x.md",
                 f"{DS.SKILLS_REAL}/refine/SKILL.md"):
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
    # before each withdrawal landed, the retired figure was published in exactly these live
    # documents. Corpora are read once per revision - `git show` per file is the expensive
    # part and three of these rows share a tree.
    if "_now_" not in _CORPUS_CACHE:
        _CORPUS_CACHE["_now_"], _ = DS._live_corpus()
    now = _CORPUS_CACHE["_now_"]
    for rev, eid, sites in HISTORICAL:
        if rev not in _CORPUS_CACHE:
            hist, hist_problems = DS._live_corpus(rev)
            if hist_problems or not hist:
                r.check(False, f"HISTORICAL: could not read the tree at {rev}",
                        "; ".join(hist_problems)[:120])
                hist = {}
            _CORPUS_CACHE[rev] = hist
        hist = _CORPUS_CACHE[rev]
        if not hist:
            continue
        published = {h.split(":")[0] for h in run(hist) if f"`{eid}`" in h}
        for site in sites:
            r.check(site in published, f"HISTORICAL: {site} published {eid} at {rev}",
                    "" if site in published else f"found in {sorted(published)}")
        r.check(not {h.split(":")[0] for h in run(now) if f"`{eid}`" in h},
                f"HISTORICAL: and no live document publishes {eid} today")

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


def sweep(verbose: bool = False) -> int:
    """The clean run and EVERY mutant, in one invocation.

    THIS IS WHAT THE CI STEP RUNS, and it is why the step exists at all - the repair
    `corpus_control.sweep` records from PR #54, which this file had not received: with
    the default at `controls()` alone, the gate duplicated the clean half `docstat
    --withdrawn` already runs, and no mutant ever ran outside an operator's terminal.
    A suite whose mutants are opt-in is a suite whose mutants are the one thing nobody
    re-runs - and these five flips are the recorded justification for the register
    gating at all (docstat.py's wiring note credits them), so their continued ability
    to fire is exactly what a bare clean run cannot assert.
    """
    print(f"withdrawal register controls, {len(ENTRIES)} entries\n")
    clean_failed = controls()
    print(f"\nCLEAN  {'FAILED' if clean_failed else 'passed'}, expected passed\n")

    pristine = {n: getattr(DS, n) for n in PATCHED}
    pristine_anchor_half = _register_problems
    killed: list[str] = []
    survived: list[str] = []
    for name in MUTANTS:
        for n, v in pristine.items():  # a mutant must not leak into the next
            setattr(DS, n, v)
        globals()["_register_problems"] = pristine_anchor_half
        apply_mutant(name)
        rebound = (any(getattr(DS, n) is not pristine[n] for n in PATCHED)
                   or globals()["_register_problems"] is not pristine_anchor_half)
        if not rebound:
            survived.append(f"{name}: rebound nothing - it is not testing anything")
            continue
        failed = controls()
        print(f"\nMUTANT {name:<12} "
              + ("SURVIVED  <- the controls cannot see the mechanism it names"
                 if not failed else "went red, as it must"))
        (survived if not failed else killed).append(name)
    for n, v in pristine.items():
        setattr(DS, n, v)
    globals()["_register_problems"] = pristine_anchor_half

    print(f"\n{len(killed)} of {len(MUTANTS)} mutants died; "
          f"{len(survived)} survived"
          + ("" if not survived else ":\n  " + "\n  ".join(survived)))
    if clean_failed or survived:
        return 1
    print("A mutant run is EXPECTED to fail its controls; a mutant that survives means "
          "the controls no longer reach the mechanism they name, and the gate's green "
          "is once again the ambiguity this file exists to prevent.")
    return 0


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
    ap.add_argument("--clean-only", action="store_true",
                    help="the controls on the unmutated tree, without the mutant sweep")
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
        before = tuple(getattr(DS, n) for n in PATCHED)
        apply_mutant(a.mutate)
        after = tuple(getattr(DS, n) for n in PATCHED)
        if before == after and a.mutate != "no_anchor":
            print(f"MUTANT {a.mutate} changed nothing - it is not testing anything")
            return 1
        print(f"MUTANT {a.mutate}: {MUTANTS[a.mutate]}\n")
        rc = controls()
        print("\nA mutant run is EXPECTED to fail. Exit 0 here would mean the controls "
              "cannot see the mechanism they name.")
        return 0 if rc else 1

    if a.clean_only:
        print(f"withdrawal register controls, {len(ENTRIES)} entries\n")
        return controls()

    return sweep()


ENTRIES: list[dict] = []

if __name__ == "__main__":
    sys.exit(main())
