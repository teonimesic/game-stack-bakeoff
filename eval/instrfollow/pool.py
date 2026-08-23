#!/usr/bin/env python3
"""The instruction pool and its checkers, for the instruction-count experiment.

Read `eval/instrfollow/DESIGN.md` first. That file is the design; this one is the
apparatus, and if the two disagree the design wins and this file is the bug.

WHAT IS IN THE POOL
-------------------
16 instructions, each

  * derived from a rule this project's own always-loaded documentation states. The
    source is recorded per instruction in `Instruction.source`, quoting the original
    where the wording had to move to make the rule checkable on this task;
  * checkable by a DETERMINISTIC function of the artifact, with no model in the loop;
  * given an opportunity to be violated by the base task, so no checker passes
    vacuously (rule 1: a check that cannot fail is not a check);
  * INDEPENDENT of every other instruction, in both directions -- obeying one neither
    forces nor forbids obeying another. Pinned by the mutant sweep below, which requires
    each mutant to flip exactly one checker. An earlier draft had a `the file must have
    a module docstring` instruction; it was removed because three other instructions
    checked the docstring's CONTENTS and so could not be observed independently of it;
  * mutually satisfiable, pinned by `gold_probe.py`, which obeys all 16 at once. That
    matters beyond convenience: arXiv:2510.14842 identifies CONFLICT between
    instructions, not their number, as the mechanism behind compliance decay. This
    experiment is about count, so conflict is excluded by construction and the gold
    artifact is the proof that it was.

TWO CLASSES, DELIBERATELY
-------------------------
`F*` are format constraints on the source text. `B*` are behavioural, and seven of them
are checked by RUNNING the artifact against a fixture tree rather than by reading it.
The class is recorded per instruction because if a count effect appears in one class and
not the other, that is a more interesting result than the pooled number -- and pooling
across a population you have not shown is homogeneous is rule 4.

FAIL CLOSED
-----------
If the artifact does not parse, or crashes, every checker that needs to run it FAILS. It
is not excused and it is not skipped. `usable` is recorded separately so the analysis can
partition on it, but the default is failure: every reason not to count a failure is a
channel a bug can widen (rule 7).

    python3 eval/instrfollow/pool.py --selftest    # gold, 16 mutants, variant, fail-closed
    python3 eval/instrfollow/pool.py --list
    python3 eval/instrfollow/pool.py --check FILE
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

ARTIFACT = "probe.py"
SUMMARY = "summary.json"
RUN_TIMEOUT_S = 20
FIXTURES = Path(__file__).resolve().parent / "fixtures"

# --------------------------------------------------------------------------- #
# The base task. Held byte-identical across every trial and every arm: it is the
# constant, and the instruction block is the only thing that moves.
# --------------------------------------------------------------------------- #

BASE_TASK = f"""\
Write a single Python 3 file called `{ARTIFACT}` in the current directory.

`{ARTIFACT}` takes one command-line argument, the path of a directory. It reads every
`*.json` file directly inside that directory (not in subdirectories), takes the
top-level key `cost_usd` from each file that has one, and writes a JSON object to
`{SUMMARY}` in the current working directory holding the total and the mean of those
values.

Write only that one file. Do not create anything else, and do not run it.
"""


# --------------------------------------------------------------------------- #
# Fixture tree the behavioural checkers run the artifact against.
# --------------------------------------------------------------------------- #

def make_fixture(root: Path, malformed: bool = False) -> dict:
    """Three parseable `*.json` files directly inside, one non-JSON file, and one JSON
    file in a subdirectory that must NOT be read. With `malformed=True`, one additional
    file that does not parse.

    THE TWO FIXTURES EXIST BECAUSE THE PILOT PROVED ONE WAS NOT ENOUGH.
    The first version put the unparseable file in the single fixture every behavioural
    checker shared. An artifact told to name unparseable files (B8) handles it; an
    artifact NOT told to handle it has no reason to, and crashes -- so the ABSENCE of
    B8 failed B3, B4, B9, B10 and `usable` as collateral, and the run-based checkers
    were not independent after all.

    That defect is invisible to a mutant sweep, because every mutant is derived from an
    artifact that already obeys all sixteen. It is the rule-15 shape exactly: a mutant
    asks whether a check can fail, and only an input the check mishandles asks whether
    it can still pass. The input here was the ordinary, reasonable artifact of an agent
    that was never given B8.

    So B8 is now the ONLY checker that reads the malformed run. Everything else reads a
    fixture on which a straightforward implementation succeeds.
    """
    root.mkdir(parents=True, exist_ok=True)
    (root / "a.json").write_text(json.dumps({"cost_usd": 1.5, "note": "x"}))
    (root / "b.json").write_text(json.dumps({"cost_usd": 2.5}))
    (root / "c.json").write_text(json.dumps({"note": "no cost here"}))
    (root / "notjson.txt").write_text("ignored")
    sub = root / "sub"
    sub.mkdir(exist_ok=True)
    (sub / "d.json").write_text(json.dumps({"cost_usd": 99.0}))
    truth = {"seen": 3, "with_cost": 2, "total": 4.0, "mean": 2.0}
    if malformed:
        (root / "bad.json").write_text("{ this is not json")
        truth["bad"] = "bad.json"
    return truth


# --------------------------------------------------------------------------- #
# Running the artifact
# --------------------------------------------------------------------------- #

@dataclass
class RunResult:
    """What running the artifact actually did. The two streams are kept APART, per
    `eval/AGENTS.md` -- a merged buffer is a sampling policy, and here it would decide
    whether the `prints nothing to stdout` checker passes."""
    rc: int | None
    stdout: str
    stderr: str
    summary: dict | None
    crashed: bool


@dataclass
class Artifact:
    src: str
    tree: ast.Module | None
    parse_error: str | None
    ok_run: RunResult | None = None            # clean fixture, clean cwd
    missing_dir_run: RunResult | None = None   # a directory that does not exist
    second_run: RunResult | None = None        # summary.json already present
    malformed_run: RunResult | None = None     # fixture with an unparseable file
    fixture_truth: dict = field(default_factory=dict)

    @property
    def usable(self) -> bool:
        return (self.parse_error is None and self.ok_run is not None
                and not self.ok_run.crashed and self.ok_run.rc == 0
                and self.ok_run.summary is not None)

    def docstring(self) -> str:
        if self.tree is None:
            return ""
        try:
            return ast.get_docstring(self.tree) or ""
        except TypeError:
            return ""


def _run(cwd: Path, args: list[str]) -> RunResult:
    try:
        p = subprocess.run([sys.executable, ARTIFACT, *args], cwd=cwd,
                           capture_output=True, text=True, timeout=RUN_TIMEOUT_S,
                           check=False)
        rc, out, err, crashed = p.returncode, p.stdout, p.stderr, False
    except subprocess.TimeoutExpired:
        rc, out, err, crashed = None, "", "HARNESS TIMEOUT", True
    except OSError as exc:
        rc, out, err, crashed = None, "", f"OSError: {exc}", True
    summary = None
    sp = cwd / SUMMARY
    if sp.exists():
        try:
            summary = json.loads(sp.read_text())
        except (json.JSONDecodeError, UnicodeDecodeError, OSError):
            summary = None
    return RunResult(rc, out, err, summary, crashed)


def load(src: str) -> Artifact:
    """Parse the source, then execute it in FOUR fresh working directories.

    Four, because four checkers are about a path the happy case never touches: a
    directory that does not exist (B6), an output file that already exists (B7), and a
    file that does not parse (B8). A checker that only ever sees the happy path cannot
    see any of them -- and, as the pilot showed, putting all of them into one fixture
    makes the checkers dependent on each other instead.
    """
    try:
        tree, perr = ast.parse(src), None
    except (SyntaxError, ValueError) as exc:
        tree, perr = None, f"{exc.__class__.__name__}: {exc}"

    art = Artifact(src=src, tree=tree, parse_error=perr)
    if perr is not None:
        return art

    tmp = Path(tempfile.mkdtemp(prefix="instrfollow-"))
    try:
        w1 = tmp / "w1"
        w1.mkdir()
        (w1 / ARTIFACT).write_text(src)
        art.fixture_truth = make_fixture(w1 / "data")
        art.ok_run = _run(w1, ["data"])

        w2 = tmp / "w2"
        w2.mkdir()
        (w2 / ARTIFACT).write_text(src)
        art.missing_dir_run = _run(w2, ["no-such-directory"])

        w3 = tmp / "w3"
        w3.mkdir()
        (w3 / ARTIFACT).write_text(src)
        make_fixture(w3 / "data")
        (w3 / SUMMARY).write_text(json.dumps({"sentinel": "pre-existing"}))
        art.second_run = _run(w3, ["data"])

        w4 = tmp / "w4"
        w4.mkdir()
        (w4 / ARTIFACT).write_text(src)
        make_fixture(w4 / "data", malformed=True)
        art.malformed_run = _run(w4, ["data"])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    return art


def _calls(tree: ast.Module) -> list[str]:
    """Dotted names of every call in the tree."""
    out = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            f, parts = node.func, []
            while isinstance(f, ast.Attribute):
                parts.append(f.attr)
                f = f.value
            if isinstance(f, ast.Name):
                parts.append(f.id)
            if parts:
                out.append(".".join(reversed(parts)))
    return out


# --------------------------------------------------------------------------- #
# The 16 checkers. Each returns (passed, evidence).
# --------------------------------------------------------------------------- #

def c_f1(a: Artifact) -> tuple[bool, str]:
    m = re.search(r"\b\d{4}-\d{2}-\d{2}\b", a.docstring())
    return bool(m), f"date={m.group(0) if m else None}"


def c_f2(a: Artifact) -> tuple[bool, str]:
    hit = [ln for ln in a.docstring().splitlines()
           if ln.lstrip().startswith("UNVERIFIED:")]
    return bool(hit), f"unverified_lines={len(hit)}"


def c_f3(a: Artifact) -> tuple[bool, str]:
    d = a.docstring()
    cited = "eval/IMPROVEMENTS.md" in d
    bare = re.findall(r"(?<![\w/])IMPROVEMENTS\.md", d)
    return (cited and not bare), f"cited={cited} bare={len(bare)}"


def c_f4(a: Artifact) -> tuple[bool, str]:
    over = [i + 1 for i, ln in enumerate(a.src.splitlines()) if len(ln) > 88]
    return (not over), f"over88_lines={over[:5]} n={len(over)}"


def c_f5(a: Artifact) -> tuple[bool, str]:
    n = a.src.count(chr(9))
    return (n == 0), f"tabs={n}"


def c_f6(a: Artifact) -> tuple[bool, str]:
    flat = re.sub(r"\s+", chr(32), a.src)
    forms = ['if __name__ == "__main__": raise SystemExit(main())',
             "if __name__ == '__main__': raise SystemExit(main())"]
    ok = any(f in flat for f in forms)
    return ok, ("guard present" if ok else "guard absent")


def c_b1(a: Artifact) -> tuple[bool, str]:
    """No fallback that turns an error into a plausible in-range number."""
    if a.tree is None:
        return False, "unparseable"
    bad = []
    for node in ast.walk(a.tree):
        if isinstance(node, ast.ExceptHandler):
            if node.type is None:
                bad.append(f"bare-except@{node.lineno}")
                continue
            body = node.body
            if len(body) == 1 and isinstance(body[0], (ast.Pass, ast.Continue)):
                bad.append(f"swallowed@{node.lineno}")
    return (not bad), f"{bad[:3]} n={len(bad)}"


def c_b2(a: Artifact) -> tuple[bool, str]:
    """Atomic write. `os.replace`, or a `.replace(...)` on something whose name says it
    is the temporary file -- `str.replace` must not count as a pass."""
    if a.tree is None:
        return False, "unparseable"
    calls = _calls(a.tree)
    named_tmp = [c for c in calls if c.endswith(".replace")
                 and re.search(r"tmp|temp", c.rsplit(".", 1)[0], re.I)]
    ok = ("os.replace" in calls) or bool(named_tmp)
    return ok, f"replace_calls={[c for c in calls if 'replace' in c][:4]}"


def c_b3(a: Artifact) -> tuple[bool, str]:
    s = (a.ok_run.summary if a.ok_run else None) or {}
    v = s.get("n")
    return isinstance(v, int) and not isinstance(v, bool), f"n={v!r}"


def c_b4(a: Artifact) -> tuple[bool, str]:
    s = (a.ok_run.summary if a.ok_run else None) or {}
    v = s.get("source_dir")
    return (isinstance(v, str) and os.path.isabs(v)), f"source_dir={v!r}"


def c_b5(a: Artifact) -> tuple[bool, str]:
    if a.tree is None:
        return False, "unparseable"
    defs = [n for n in ast.walk(a.tree)
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    if not defs:
        return False, "no def at all"
    if not any(d.name == "main" for d in defs):
        return False, f"no main(); defs={[d.name for d in defs]}"
    missing = [d.name for d in defs if d.returns is None]
    return (not missing), f"unannotated={missing}"


def c_b6(a: Artifact) -> tuple[bool, str]:
    r = a.missing_dir_run
    if r is None:
        return False, "not run"
    loud = (r.rc is not None and r.rc != 0)
    return (loud and r.summary is None), \
        f"rc={r.rc} wrote_summary={r.summary is not None}"


def c_b7(a: Artifact) -> tuple[bool, str]:
    r = a.second_run
    if r is None:
        return False, "not run"
    refused = (r.rc is not None and r.rc != 0)
    kept = (r.summary or {}).get("sentinel") == "pre-existing"
    return (refused and kept), f"rc={r.rc} clobbered={not kept}"


def c_b8(a: Artifact) -> tuple[bool, str]:
    """The ONLY checker that reads the malformed-fixture run. See `make_fixture`."""
    s = (a.malformed_run.summary if a.malformed_run else None) or {}
    errs = s.get("errors")
    ok = isinstance(errs, list) and any("bad.json" in str(e) for e in errs)
    return ok, f"errors={errs!r}"


def c_b9(a: Artifact) -> tuple[bool, str]:
    s = (a.ok_run.summary if a.ok_run else None) or {}
    fr = s.get("files_read")
    if not isinstance(fr, list):
        return False, f"files_read={fr!r}"
    names = {os.path.basename(str(x)) for x in fr}
    ok = {"a.json", "b.json", "c.json"} <= names and "d.json" not in names
    return ok, f"files_read={sorted(names)}"


def c_b10(a: Artifact) -> tuple[bool, str]:
    r = a.ok_run
    if r is None:
        return False, "not run"
    return (r.stdout.strip() == ""), f"stdout={r.stdout[:60]!r}"


@dataclass(frozen=True)
class Instruction:
    id: str
    cls: str                 # "F" format, "B" behavioural
    text: str                # exactly what the agent is told
    source: str              # the rule in this repo's docs it comes from
    checker: object
    runs_artifact: bool


POOL: list[Instruction] = [
    Instruction(
        "F1", "F",
        "Date every claim. The module docstring must carry a date in ISO form, "
        "YYYY-MM-DD.",
        "research/AGENTS.md: 'Date every claim, and name the version it applies to.'",
        c_f1, False),
    Instruction(
        "F2", "F",
        "Label unverified claims as unverified. The module docstring must contain a "
        "line beginning `UNVERIFIED:` naming something about this script you did not "
        "check.",
        "research/AGENTS.md: 'Label unverified claims as unverified. An unlabelled "
        "guess is indistinguishable from a measured fact.'",
        c_f2, False),
    Instruction(
        "F3", "F",
        "Two files in this project are called `IMPROVEMENTS.md`, so cite the path and "
        "never the bare name. The docstring must refer to `eval/IMPROVEMENTS.md`, and "
        "must never write `IMPROVEMENTS.md` without a directory in front of it.",
        "AGENTS.md: 'Two files share a name; cite the path, never \"IMPROVEMENTS "
        "iteration 1b\".'",
        c_f3, False),
    Instruction(
        "F4", "F",
        "Keep every line of the file at 88 characters or fewer.",
        "house style; the repo's own Python holds a hard wrap",
        c_f4, False),
    Instruction(
        "F5", "F",
        "Indent with spaces only. The file must contain no tab character anywhere.",
        "house style",
        c_f5, False),
    Instruction(
        "F6", "F",
        'The file must end with `if __name__ == "__main__":` followed by '
        "`raise SystemExit(main())`.",
        "the convention every script in eval/tools/ follows",
        c_f6, False),
    Instruction(
        "B1", "B",
        "Never write a fallback that turns an error into a plausible in-range number. "
        "The file must contain no bare `except:`, and no `except` clause whose body is "
        "only `pass` or only `continue`.",
        "AGENTS.md rule 3: 'never write `cmd || echo 0` on anything you will read as a "
        "measurement. The fallback turns an error into a plausible in-range number, "
        "which is the most dangerous shape a broken check can take.'",
        c_b1, False),
    Instruction(
        "B2", "B",
        f"Write `{SUMMARY}` atomically: write a temporary file first, then `os.replace` "
        "it into position. A partly-written file must never be visible under the real "
        "name.",
        "eval/AGENTS.md: 'Write atomically - temp file plus `os.replace`.'",
        c_b2, False),
    Instruction(
        "B3", "B",
        "Never report a mean without the population it was taken over. The summary "
        "object must carry an integer key `n`, the number of values the mean was "
        "computed from.",
        "AGENTS.md rule 4: 'Report `n` per group alongside any aggregate.'",
        c_b3, True),
    Instruction(
        "B4", "B",
        "Record the address the measurement was taken at. The summary object must "
        "carry a key `source_dir` holding the absolute, resolved path of the directory "
        "that was read.",
        "AGENTS.md rule 12: 'The address is an input to the check.'",
        c_b4, True),
    Instruction(
        "B5", "B",
        "The file must define a function called `main`, and every `def` in the file "
        "must carry a return-type annotation.",
        "house style; every tool in eval/tools/ is annotated",
        c_b5, False),
    Instruction(
        "B6", "B",
        "If the directory named on the command line does not exist, fail loudly: exit "
        f"with a non-zero status and write no `{SUMMARY}` at all. Do not report zero.",
        "AGENTS.md rule 3 'let failures be visible', and rule 12, where a check aimed "
        "at a path that no longer existed reported no writes through 2555 of them.",
        c_b6, True),
    Instruction(
        "B7", "B",
        f"One writer per artifact path. If `{SUMMARY}` already exists, the script must "
        "refuse to run: exit non-zero and leave the existing file exactly as it was.",
        "eval/AGENTS.md: 'One writer per artifact path, always', and the O_EXCL "
        "manifest reservation that followed from it.",
        c_b7, True),
    Instruction(
        "B8", "B",
        "Capture what the instrument did, not only what it concluded. The summary "
        "object must carry a key `errors`, a list naming every file that could not be "
        "parsed.",
        "AGENTS.md: 'Record the inputs a component actually consumed, not merely the "
        "output it produced.'",
        c_b8, True),
    Instruction(
        "B9", "B",
        "The summary object must carry a key `files_read`, the list of every `*.json` "
        "file it opened, including any that carried no `cost_usd` value.",
        # TIGHTENED AFTER THE PILOT. The first wording was "the list of files actually
        # read", and a pilot artifact listed only the files it took a value FROM --
        # a defensible reading of that sentence. An ambiguous instruction produces
        # variance that is about the wording, not about the instruction count, and this
        # experiment cannot tell those apart. The fix belongs in the instruction, not
        # in a looser checker: loosening the checker would hide the ambiguity instead.
        "AGENTS.md: 'An audit trail of what a mechanism did is worth more than the "
        "confidence you had when you built it.'",
        c_b9, True),
    Instruction(
        "B10", "B",
        "On a successful run the script must print nothing at all to stdout.",
        "eval/AGENTS.md: stdout is what gets parsed, so it is not a scratch pad",
        c_b10, True),
]

BY_ID = {i.id: i for i in POOL}
assert len(BY_ID) == len(POOL) == 16, "pool must hold 16 distinct instructions"


def render(ids: list[str]) -> str:
    """The instruction block exactly as an agent sees it."""
    lines = ["Follow every one of these requirements:", ""]
    for n, iid in enumerate(ids, 1):
        lines.append(f"{n}. {BY_ID[iid].text}")
    return "\n".join(lines)


def evaluate(src: str, ids: list[str] | None = None) -> dict:
    """Run every named checker against one artifact. Fails closed."""
    art = load(src)
    ids = ids if ids is not None else [i.id for i in POOL]
    res = {}

    # THE PARSE GATE, AND WHY IT IS GLOBAL.
    # Two checkers -- line width and absence of tabs -- are satisfied by any short,
    # tab-free text, including text that is not Python at all. Left alone they credited
    # 2 of 16 to a source file reading `def main( :`. Crediting compliance to an
    # artifact that is not the artifact the instructions are about is a fail-OPEN
    # channel, and a fail-open defect costs you the result (rule 7). So a parse failure
    # zeroes everything. A RUNTIME crash deliberately does not: the file is still a
    # readable Python source, the format instructions are still observable on it, and
    # `usable` carries the distinction for the analysis to partition on.
    if art.parse_error is not None:
        return {
            "usable": False, "parse_error": art.parse_error, "rc": None,
            "checks": {iid: {"passed": False,
                             "evidence": f"artifact does not parse: {art.parse_error}",
                             "cls": BY_ID[iid].cls,
                             "runs_artifact": BY_ID[iid].runs_artifact}
                       for iid in ids},
        }

    for iid in ids:
        ins = BY_ID[iid]
        try:
            ok, ev = ins.checker(art)
        # BLE001 deliberately: a checker that raises on an artifact it did not expect
        # must score that instruction FAILED, not abort the run and not be skipped.
        # Narrowing this would let one unanticipated exception discard a whole paid-for
        # trial, and skipping would be the fail-open channel rule 7 names.
        except Exception as exc:  # noqa: BLE001
            ok, ev = False, f"checker raised {exc.__class__.__name__}: {exc}"
        res[iid] = {"passed": bool(ok), "evidence": str(ev)[:200], "cls": ins.cls,
                    "runs_artifact": ins.runs_artifact}
    return {
        "usable": art.usable,
        "parse_error": art.parse_error,
        "rc": art.ok_run.rc if art.ok_run else None,
        "checks": res,
    }


# --------------------------------------------------------------------------- #
# Controls
# --------------------------------------------------------------------------- #

def _mutate(src: str, iid: str) -> str:
    """`gold_probe.py` with exactly one instruction violated.

    Every mutation is chosen so that the OBSERVABLE consequence is confined to its own
    checker. That is why B1's mutant adds a dead swallowed `except` rather than emptying
    the real one -- emptying the real one would also stop `errors` being populated and
    would flip B8 as collateral, and a mutant that flips two checkers cannot tell you
    which of them was doing the work.
    """
    pad = chr(32) * 44
    table = {
        # "last August" and not "some time last August": the longer string pushed the
        # docstring line past 88 characters and flipped F4 as well, which is exactly
        # the collateral this sweep exists to catch. Caught by the sweep, not by review.
        "F1": ("2026-08-23", "last August"),
        "F2": ("UNVERIFIED:", "Note:"),
        "F3": ("eval/IMPROVEMENTS.md", "IMPROVEMENTS.md"),
        "F4": ("import json", "import json" + pad + "# a comment that runs past 88" + pad),
        "F5": ("# read every *.json", "#" + chr(9) + "read every *.json"),
        "F6": ("raise SystemExit(main())", "sys.exit(main())"),
        "B1": ("def main() -> int:",
               "def main() -> int:\n    try:\n        _dead = 1\n"
               "    except ValueError:\n        pass"),
        "B2": ("os.replace(tmp, dest)", "tmp.rename(dest)"),
        "B3": ('        "n": len(values),\n', ""),
        "B4": ('        "source_dir": str(root.resolve()),\n', ""),
        "B5": ("def main() -> int:", "def main():"),
        "B6": ('        raise SystemExit(f"no such directory: {root}")',
               '        root = Path(".")'),
        "B7": ('        raise SystemExit(f"refusing to overwrite {dest}")',
               "        pass"),
        "B8": ('        "errors": errors,\n', ""),
        "B9": ('        "files_read": names,\n', ""),
        "B10": ("def main() -> int:", 'def main() -> int:\n    print("starting")'),
    }
    old, new = table[iid]
    if old not in src:
        raise AssertionError(f"mutation {iid} does not apply: {old!r} not in gold")
    return src.replace(old, new, 1)


def selftest() -> int:
    """The three-way control this project requires of every grader, plus fail-closed.

    POSITIVE   the gold artifact obeys all 16 -> all 16 checkers pass. This doubles as
               the proof that the 16 are mutually satisfiable, i.e. that the pool holds
               no internal conflict.
    NEGATIVE   16 mutants, one per instruction -> that checker flips and NO OTHER
               checker moves. The second half is the half that matters: it establishes
               that a compliance count over this pool counts 16 things, rather than one
               thing measured 16 times (rule 9).
    VARIANT    an artifact obeying every instruction by a DIFFERENT legitimate route ->
               all 16 still pass. A mutant asks whether a check CAN FAIL; only a variant
               asks whether it can STILL PASS (rule 15), and every false negative
               adjudicated in this project has been of the second kind.
    """
    ok = True
    gold_src = (FIXTURES / "gold_probe.py").read_text()

    print("POSITIVE -- gold obeys all 16")
    g = evaluate(gold_src)
    if not g["usable"]:
        print(f"  FAIL  gold is not usable: parse_error={g['parse_error']} rc={g['rc']}")
        ok = False
    for iid, r in g["checks"].items():
        if not r["passed"]:
            print(f"  FAIL  {iid} does not pass on gold: {r['evidence']}")
            ok = False
    print(f"  {sum(r['passed'] for r in g['checks'].values())}/16 pass on gold")

    print("\nNEGATIVE -- one mutant per instruction, exactly one checker may flip")
    for iid in BY_ID:
        try:
            m = evaluate(_mutate(gold_src, iid))
        except AssertionError as exc:
            print(f"  FAIL  {iid}: {exc}")
            ok = False
            continue
        flipped = {k for k, r in m["checks"].items() if not r["passed"]}
        if flipped == {iid}:
            print(f"  PASS  {iid}")
        else:
            print(f"  FAIL  {iid}: flipped={sorted(flipped)} "
                  f"collateral={sorted(flipped - {iid})} missed={sorted({iid} - flipped)}"
                  f"  evidence={m['checks'][iid]['evidence']}")
            ok = False

    print("\nVARIANT -- a legitimately different artifact must still pass all 16")
    v = evaluate((FIXTURES / "variant_probe.py").read_text())
    if not v["usable"]:
        print(f"  FAIL  variant is not usable: {v['parse_error']} rc={v['rc']}")
        ok = False
    for iid, r in v["checks"].items():
        if not r["passed"]:
            print(f"  FAIL  {iid} false-negative on variant: {r['evidence']}")
            ok = False
    print(f"  {sum(r['passed'] for r in v['checks'].values())}/16 pass on variant")

    print("\nFAIL-CLOSED -- source that does not parse fails every checker")
    bad = evaluate("def main( :\n")
    n_pass = sum(r["passed"] for r in bad["checks"].values())
    if n_pass == 0 and bad["usable"] is False:
        print("  PASS  0/16 pass, usable=False")
    else:
        print(f"  FAIL  {n_pass}/16 passed on unparseable source")
        ok = False

    print("\npool selftest:", "clean" if ok else "FAILED")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--check", metavar="FILE")
    ap.add_argument("--render", metavar="IDS", help="comma-separated ids")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.check:
        print(json.dumps(evaluate(Path(a.check).read_text()), indent=2))
        return 0
    if a.render:
        print(render([s.strip() for s in a.render.split(",") if s.strip()]))
        return 0
    for i in POOL:
        print(f"{i.id:>4} [{i.cls}] runs={int(i.runs_artifact)}  {i.text}")
        print(f"      source: {i.source}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
