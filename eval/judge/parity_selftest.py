#!/usr/bin/env python3
"""Can `starter_parity` still tell a measured test count from an unmeasured one?

THE INPUT THAT PRODUCES THE DEFECT IS A TREE WHOSE TOOLCHAIN IS NOT INSTALLED.

`test_counts` has always collected `just test`'s exit code, and until 2026-08-23 nothing
read it. `main` printed `passed/total` and drew no conclusion from `0/0`, so a stack whose
runner could not start printed two zeros and the tool still ended on *"No drift detected on
any measured axis"* and exited 0 - a live pre-campaign gate reporting success while
measuring nothing (AGENTS.md rule 1). Measured before the repair, in this repo, on the ts
starter with `node_modules` absent: `{"exit": 254, "passed": 0, "total": 0}`, tool exit 0.

That input is not exotic. `node_modules` is untracked, so it exists only in the checkout it
was installed in - every agent worktree is a tree where the ts arm cannot run its tests.

**A mutant cannot produce that input.** Deleting the status check leaves a tool that is
green on a healthy tree, which is what the tool was already doing wrong. Only a VARIANT -
a real starter tree with its dependencies genuinely absent - asks the question (rule 15),
and the two directions have to be pinned together or the "fix" of failing on everything
would pass:

    positive   a tree whose toolchain IS installed reports its real count and stays green
    variant    the same tree with the toolchain absent must NOT read as agreement
    opt-out    `--skip-tests` stays green, and says the axis was not measured

Run:

    python3 judge/parity_selftest.py                 # synthetic trees + the ts variant
    python3 judge/parity_selftest.py --no-e2e        # synthetic trees only, ~2 s

The positive control needs `eval/starters/ts/node_modules`. If it is absent this file FAILS
rather than skipping, because "the control could not run" and "the control passed" are the
two things this whole exercise exists to keep apart. Install with `just -f starters/ts/
justfile warm`, or run from the checkout that has it.

Exit code is 0 only if every expectation holds.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import starter_parity as sp  # noqa: E402

HERE = Path(__file__).resolve().parent
STARTERS = HERE.parent / "starters"

FAILS: list[str] = []
CHECKS = 0


def expect(name: str, cond: bool, detail: str = "") -> None:
    global CHECKS
    CHECKS += 1
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f"  -- {detail}" if detail else ""))
    if not cond:
        FAILS.append(name)


# --------------------------------------------------------------------------- #
# Synthetic trees: three ways `just test` can end, one `justfile` each.
#
# These are not a substitute for the real variant below - they are the fast half, and
# they cover the one shape no real tree here produces on demand: a recipe that exits 0
# having run nothing. An exit-code-only check calls that green, which is why the status
# is not simply `c.code == 0`.
# --------------------------------------------------------------------------- #

TREES: dict[str, str] = {
    # A summary in a shape `runner.parse_test_counts` knows (vitest).
    "green": 'test:\n    @echo "Tests  9 passed (11)"\n    @echo "  9 passed | 2 failed"\n',
    # The toolchain-absent shape: the runner is not there, so the recipe dies.
    "toolchain_absent": 'test:\n    @echo "vitest: command not found" >&2\n    @exit 127\n',
    # THE ADVERSARIAL ONE. Exit 0, nothing to count.
    "vacuous": 'test:\n    @echo "nothing to do here"\n',
}


def synthetic(root: Path, name: str) -> Path:
    d = root / name
    d.mkdir(parents=True, exist_ok=True)
    (d / "justfile").write_text(TREES[name], encoding="utf-8")
    return d


def test_status_classification(root: Path) -> None:
    print("\n[test_counts must say WHETHER it measured, not only what it counted]")

    g = sp.test_counts(synthetic(root, "green"), timeout_s=120)
    expect("a runner that ran and reported is `ran`", g["status"] == sp.TESTS_RAN, str(g))
    expect("...and its numbers are the runner's", (g["passed"], g["total"]) == (9, 11),
           f"{g['passed']}/{g['total']}")
    expect("...and it prints as a pair of numbers", sp.tests_cell(g) == "9/11",
           sp.tests_cell(g))

    a = sp.test_counts(synthetic(root, "toolchain_absent"), timeout_s=120)
    expect("a runner that could not start is UNMEASURABLE",
           a["status"] == sp.TESTS_UNMEASURABLE, str({k: a[k] for k in ("exit", "status")}))
    expect("...and this is exactly the pre-repair input: the old code saw 0/0",
           (a["passed"], a["total"]) == (0, 0),
           "if this is not 0/0 the variant is not reproducing the defect and proves nothing")
    expect("...and it never prints as a pair of numbers",
           "/" not in sp.tests_cell(a), sp.tests_cell(a))
    expect("...and the reason is carried, not just the verdict",
           "exited 127" in a["why_unmeasurable"], a["why_unmeasurable"])

    v = sp.test_counts(synthetic(root, "vacuous"), timeout_s=120)
    expect("a recipe that exits 0 having counted nothing is UNMEASURABLE too",
           v["status"] == sp.TESTS_UNMEASURABLE, str({k: v[k] for k in ("exit", "status")}))
    expect("...and THIS is the half an exit-code-only check would call green",
           v["exit"] == 0 and v["status"] != sp.TESTS_RAN,
           "exit 0 with no parseable summary")

    expect("`not_measured` is a third answer, distinct from both",
           len({sp.TESTS_RAN, sp.TESTS_UNMEASURABLE, sp.TESTS_NOT_MEASURED}) == 3)


# --------------------------------------------------------------------------- #
# HEADING ADJUDICATION. Pure inputs, so this half always runs - including under
# `--no-e2e`, where no toolchain is needed.
#
# The near-miss heading note keys on heading TEXT, and heading text is the one thing
# `starter_parity`'s own comment says equality may NOT be demanded of. Both rows it
# reported on 2026-08-23 were wording divergences whose substance is present in all four
# guides, so the note asked "is this a section one guide never got?" twice and the answer
# was no twice - a question the tool re-asks every run and cannot answer.
#
# The direction that matters is the VARIANT (rule 15): a real forgotten copy, where the
# heading is absent AND so is the guidance. The pre-2026-08-23 code cannot produce that
# reading at all - it prints the same note either way - so a mutant of it proves nothing.
# --------------------------------------------------------------------------- #

def _real_guides() -> tuple[dict[str, set[str]], dict[str, str]]:
    """Heading sets and lowercased bodies of the four guides actually shipped."""
    hsets, texts = {}, {}
    for s in sp.STACKS:
        hsets[s] = set(sp.agents_md(STARTERS / s)["headings"])
        texts[s] = sp.guide_text(STARTERS / s).lower()
    return hsets, texts


def test_heading_adjudication() -> None:
    print("\n[a near-miss heading must be adjudicated against the GUIDE, not left as a "
          "question]")
    hsets, texts = _real_guides()
    expect("all four guides were read", len(hsets) == 4 and all(texts.values()))

    # -- POSITIVE: the two rows on the real starters are both wording, and say so ------ #
    problems, notes = sp.heading_findings(hsets, texts)
    expect("the shipped starters raise NO heading problem", problems == [], str(problems))
    for h, without in (("The one command", "ts"), ("Gameplay is not correctness", "unity")):
        line = next((n for n in notes if h in n), "")
        expect(f"{h!r} is reported as adjudicated", "ADJUDICATED" in line
               and "NOT ADJUDICATED" not in line, line)
        expect(f"...naming {without}, and the evidence that the guidance reached it",
               without in line and sp.ADJUDICATED_HEADINGS[(h, without)]["substance"]
               in line, line)

    # -- VARIANT: the same shape, but the guidance really is absent -------------------- #
    # This is a forgotten copy: ts has neither the heading nor the contract sentence.
    phrase = sp.ADJUDICATED_HEADINGS[("The one command", "ts")]["substance"]
    gutted = dict(texts)
    gutted["ts"] = texts["ts"].replace(phrase, "")
    expect("the variant really removed the sentence", phrase not in gutted["ts"])
    problems, notes = sp.heading_findings(hsets, gutted)
    expect("a heading AND its guidance both absent is a PROBLEM, not a note",
           any(phrase in p and "ts" in p for p in problems), str(problems))

    # -- MIS-SPECIFIED: the phrase is not the substance of the section it claims ------- #
    wrong = dict(texts)
    wrong["rust"] = texts["rust"].replace(phrase, "")
    problems, _ = sp.heading_findings(hsets, wrong)
    expect("a register entry whose phrase is absent from a guide that HAS the heading "
           "is a problem", any("rust" in p for p in problems), str(problems))

    # -- UNADJUDICATED: a new near-miss stays a note, so a rename cannot go red -------- #
    h2 = {s: set(v) for s, v in hsets.items()}
    for s in ("rust", "unity", "godot"):
        h2[s].add("Some New Section")
    problems, notes = sp.heading_findings(h2, texts)
    expect("a near-miss heading nobody has adjudicated is still only a note",
           problems == [], str(problems))
    expect("...and it is labelled NOT ADJUDICATED so it is distinguishable",
           any("Some New Section" in n and "NOT ADJUDICATED" in n for n in notes),
           str([n for n in notes if "Some New Section" in n]))

    # -- DEAD ENTRY: an adjudication that no longer fires must not rot silently -------- #
    h3 = {s: set(v) for s, v in hsets.items()}
    h3["ts"].add("The one command")
    _, notes = sp.heading_findings(h3, texts)
    expect("a register entry whose row no longer fires is reported as removable",
           any("no longer fires" in n and "The one command" in n for n in notes),
           str([n for n in notes if "The one command" in n]))

    # -- and a heading everybody shares says nothing at all ---------------------------- #
    h4 = {s: {"Layout", "Testing"} for s in sp.STACKS}
    problems, notes = sp.heading_findings(h4, texts)
    expect("a heading present in every guide raises nothing",
           problems == [] and not any("Layout" in n for n in notes), str(notes))


# --------------------------------------------------------------------------- #
# The real variant: the ts starter with and without its dependency tree.
# --------------------------------------------------------------------------- #

IGNORE = shutil.ignore_patterns("node_modules", "target", "Library", ".godot", ".venv",
                                "coverage", ".git", "__pycache__")


def parity(starters: Path, out: Path, extra: list[str] | None = None) -> tuple[int, str,
                                                                              dict[str, Any]]:
    """Run the tool as a process - NO PIPE, the exit code is the measurement (rule 3)."""
    argv = ["python3", str(HERE / "starter_parity.py"), "--starters", str(starters),
            "--stacks", "ts", "--json", str(out), *(extra or [])]
    p = subprocess.run(argv, capture_output=True, text=True, timeout=1800, check=False)
    rep = json.loads(out.read_text()) if out.exists() else {}
    return p.returncode, p.stdout + p.stderr, rep


def ts_problems(rep: dict[str, Any]) -> list[str]:
    return [p for p in rep.get("problems", []) if "test-count axis" in p]


def test_variant_toolchain_absent(root: Path) -> None:
    """A copy of the real ts starter WITHOUT node_modules. Everything else about the tree
    is healthy - the probe still runs, because `just probe` is plain node - so the only
    thing this control can be reporting is the test axis."""
    print("\n[VARIANT: the real ts starter, dependencies genuinely absent]")
    st = root / "starters-no-deps"
    st.mkdir(parents=True, exist_ok=True)
    shutil.copytree(STARTERS / "ts", st / "ts", ignore=IGNORE, dirs_exist_ok=True)
    if (STARTERS / "_shared").is_dir():
        shutil.copytree(STARTERS / "_shared", st / "_shared", ignore=IGNORE,
                        dirs_exist_ok=True)
    expect("the copy really has no node_modules", not (st / "ts" / "node_modules").exists())

    code, out, rep = parity(st, root / "variant.json")
    t = rep.get("stacks", {}).get("ts", {}).get("tests", {})
    expect("the tool goes RED when a stack's `just test` cannot run", code == 1,
           f"exit {code}")
    expect("...for the test axis specifically, not something else that broke",
           len(ts_problems(rep)) == 1, f"problems: {rep.get('problems')}")
    expect("...and the word is UNMEASURABLE, not drift",
           any("UNMEASURABLE" in p and "NOT the same as agreement" in p
               for p in ts_problems(rep)))
    expect("...and it does not end on `No drift detected`",
           "No drift detected" not in out)
    # The TABLE ROW, not the whole output: the problem text quotes `0/0` on purpose, to
    # say what the row would have read, and a search over all of stdout would match that.
    row = next((ln for ln in out.splitlines() if ln.split()[:1] == ["ts"]), "")
    expect("...and the printed row is not a pair of numbers",
           "UNMEASURABLE" in row and "0/0" not in row, row)
    # WHAT MAKES THIS CONTROL DISCRIMINATING: the same tree is fine on every other axis.
    # 401 = tick 0 plus one per tape entry; `just probe` is plain node and needs no
    # dependency tree, which is why this control isolates the test axis at all.
    expect("the tree is otherwise healthy - the hash chain still ran",
           rep.get("stacks", {}).get("ts", {}).get("hash_chain_len") == len(sp.TAPE) + 1,
           str(rep.get("stacks", {}).get("ts", {}).get("hash_chain_len")))
    expect("...and the test axis is the ONLY thing the tool complains about",
           len(rep.get("problems", [])) == 1, str(rep.get("problems")))
    expect("THE OLD READING OF THIS EXACT REPORT WAS `0/0`",
           (t.get("passed"), t.get("total")) == (0, 0),
           "the pre-repair printer read these two fields and nothing else")


def test_positive_control(root: Path) -> None:
    """The direction a mutant cannot ask about: can it still pass? Against the real
    starter, with the toolchain installed."""
    print("\n[POSITIVE: the real ts starter, toolchain installed]")
    have = (STARTERS / "ts" / "node_modules").exists()
    expect("eval/starters/ts/node_modules is present (the control cannot run without it)",
           have, "run `just warm` in starters/ts, or run this from the checkout that has it")
    if not have:
        return
    code, out, rep = parity(STARTERS, root / "positive.json")
    t = rep.get("stacks", {}).get("ts", {}).get("tests", {})
    expect("the tool is GREEN on a tree whose tests really run", code == 0, f"exit {code}")
    expect("...the axis reports `ran`", t.get("status") == sp.TESTS_RAN, str(t))
    expect("...with a real count, all passing",
           bool(t.get("total")) and t.get("passed") == t.get("total"),
           f"{t.get('passed')}/{t.get('total')}")
    expect("...and the count is printed as a pair of numbers",
           f"{t.get('passed')}/{t.get('total')}" in out)
    expect("...and the tool still says so", "No drift detected" in out)
    expect("...and it says HOW MANY stacks really measured the axis",
           "test counts really ran on 1 of 1" in out,
           "the green sentence must carry its own scope")


def test_skip_tests_opt_out(root: Path) -> None:
    """The opt-out has to stay usable, or the honest path costs more than the dishonest
    one and nobody takes it."""
    print("\n[OPT-OUT: --skip-tests is a declared non-measurement, not a failure]")
    st = root / "starters-no-deps"          # the same dependency-less tree as the variant
    code, out, rep = parity(st, root / "skip.json", ["--skip-tests"])
    t = rep.get("stacks", {}).get("ts", {}).get("tests", {})
    expect("--skip-tests is GREEN even where the tests could not have run", code == 0,
           f"exit {code}")
    expect("...the axis is in the report as an explicit non-measurement",
           t.get("status") == sp.TESTS_NOT_MEASURED, str(t))
    expect("...it is not rendered as 0/0", "0/0" not in out)
    expect("...and the output says the axis was not measured",
           "NOT MEASURED" in out and "NOT evidence that those starters agree" in out)
    expect("...and the green sentence says no stack measured it",
           "test counts really ran on 0 of 1" in out)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-e2e", action="store_true",
                    help="synthetic trees only: skip the real ts starter copies")
    a = ap.parse_args()

    with tempfile.TemporaryDirectory(prefix="parity-selftest-") as td:
        root = Path(td)
        test_status_classification(root)
        test_heading_adjudication()
        if not a.no_e2e:
            test_variant_toolchain_absent(root)
            test_skip_tests_opt_out(root)
            test_positive_control(root)

    print(f"\n{CHECKS} expectation(s), {len(FAILS)} failed")
    for f in FAILS:
        print(f"  FAILED: {f}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    raise SystemExit(main())
