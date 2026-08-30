#!/usr/bin/env python3
"""Prove the building agents were blind to the rubric, rather than asserting it.

Three checks, each of which has to pass:

1. THE CANARY IS NOT IN THE TRIAL TREE. `RUBRIC.md` carries a GUID that appears nowhere
   else. If it turns up inside a trial working directory, or in an agent transcript,
   the run is contaminated. (Terminal-Bench puts canary GUIDs in task files for exactly
   this reason.)

2. THE RUBRIC IS NOT IN AN ANCESTOR OF THE TRIAL TREE. This is the one that actually
   bites. An agent's tools are scoped to its working directory, but an agent that runs
   `cat ../../judge/RUBRIC.md` is only blocked if the rubric is not up the path. So
   trial trees must live outside the repository, and this check walks every ancestor to
   the filesystem root looking for a `judge/` directory or a file containing the canary.

3. NO CRITERION VOCABULARY LEAKED. The criterion ids (`layer.clears`,
   `aim.independent`, ...) must not appear in the starter, the prompt or the trial tree.
   A prompt that names the thing being measured is teaching to the test even without
   the rubric file.

Exit code 0 means blind, 1 means contaminated. Fail closed: an unreadable path counts
as a failure, not as a pass.

`--selftest` is the can-fail proof for these three checks. It builds fixture trial
trees under a tempdir - no eval/runs, no network, no starter touched - one per shape
the checks exist for, and asserts each in the direction that makes it a check: every
contaminated shape exits 1 naming the offending file, the clean tree exits 0, and
the bare invocation is refused. It then rebuilds this file twice from its own source,
each mutant neutering one load-bearing line - the scan's hit append, and the
criterion vocabulary's assignment - and requires each neutering to turn a specific
row red while the rows the other checks own stay green. A verify_blind whose scan
reports nothing on contaminated input therefore fails this suite. Before task 226
nothing in the repository could make these checks fail: blurb_selftest.py exercises
only the --packs path, and #39 is what a check with no red half is worth.
"""

from __future__ import annotations

import argparse
import importlib.util
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
RUBRIC = HERE / "RUBRIC.md"

SKIP_DIRS = {".git", "target", "node_modules", "Library", "Temp", "obj", ".godot",
             ".venv", "__pycache__", "dist", "build"}
TEXT_EXT = {".rs", ".ts", ".tsx", ".js", ".mjs", ".cs", ".gd", ".md", ".toml", ".json",
             ".yaml", ".yml", ".txt", ".sh", ".py", ".cfg", ".jsonl", ".xml", ".shader",
             ".tscn", ".godot", ".asmdef", ".globalconfig", ""}


def canary() -> str:
    m = re.search(r"CANARY:\s*`([^`]+)`", RUBRIC.read_text())
    if not m:
        raise SystemExit("RUBRIC.md has no CANARY line - blinding cannot be verified")
    return m.group(1)


#: Tokens shaped like `word.word` that are FILE NAMES, not criterion ids. The rubric
#: names its own implementation files in backticks - `audio.py`, `static.py`,
#: `playbot.json` - and the scraper below cannot tell those from `audio.distinct`.
#:
#: MEASURED 2026-08-16: leaving them in produced **18 findings and a CONTAMINATED
#: verdict on a clean $1,727 matrix**. Every hit was the substring `audio.py` inside
#: the agents' own `tools/make_audio.py`, its justfile recipe, and the starter's
#: AGENTS.md. Not one real criterion id had leaked, the canary was absent, and the
#: rubric was unreachable. A scanner that cries contamination on a clean run gets
#: switched off, and then it is not protecting anything.
_NOT_VOCABULARY = (".py", ".json", ".md", ".sh", ".toml", ".gd", ".ts", ".cs",
                   ".rs", ".yml", ".yaml", ".txt", ".cfg", ".lock")


def criterion_ids() -> list[str]:
    """Every `id` in the rubric tables, as vocabulary that must not leak.

    File names are excluded: they are not rubric vocabulary, an agent may legitimately
    create a file whose name contains one, and matching them makes the real signal
    unreadable among the noise.
    """
    ids = set(re.findall(r"`([a-z]+\.[a-z_]+)`", RUBRIC.read_text()))  # SELFTEST-VOCAB-SOURCE
    return sorted(i for i in ids
                  if "." in i
                  and not i.startswith(("just.", "src."))
                  and not i.endswith(_NOT_VOCABULARY))


def _files(root: Path):
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        if any(part in SKIP_DIRS for part in p.relative_to(root).parts):
            continue
        if p.suffix.lower() not in TEXT_EXT:
            continue
        if p.stat().st_size > 4_000_000:
            continue
        yield p


def scan(root: Path, needles: dict[str, str]) -> list[str]:
    """Return 'label: path' for every needle found. Unreadable files fail closed."""
    hits: list[str] = []
    for p in _files(root):
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            hits.append(f"unreadable ({e}): {p}")
            continue
        for label, needle in needles.items():
            if needle in text:
                hits.append(f"{label}: {p}")  # SELFTEST-NEUTER-SCAN
    return hits


def check_pack_skill(pack_dirs: list[Path]) -> list[str]:
    """Stack tokens in anything the judge is handed inside a pack.

    A skill lives at `<pack>/.claude/skills/<name>/SKILL.md` because the judge runs with
    `cwd=pack` and `--setting-sources project`, so project settings resolve against the
    pack. That makes it EVIDENCE - text the judge reads - and evidence has to be blind.

    `anonymise.neutralise()` rewrites stack tokens in the submissions' code, and nothing
    was rewriting anything else in the pack. A skill, a brief or a README added later is a
    hand-written file on the same footing as the code, and no filter was watching it. This
    checks every text file in the pack that did NOT come from a submission.
    """
    sys.path.insert(0, str(HERE))
    import anonymise

    problems: list[str] = []
    for pack in pack_dirs:
        pack = pack.resolve()
        if not pack.exists():
            problems.append(f"pack path does not exist: {pack} (failing closed)")
            continue
        for p in _files(pack):
            rel = p.relative_to(pack)
            # `code/` is the anonymised submission text; it has already been through
            # neutralise(). Everything else in a pack is ours and is checked.
            # `code/` is exempt from the STACK-TOKEN scan because neutralise() has
            # already rewritten it. It is NOT exempt from the trial-id scan: that is
            # precisely where the leak was found, inside code/other/*.json.
            code_dir = bool(rel.parts) and rel.parts[0] == "code"
            try:
                text = p.read_text(encoding="utf-8", errors="replace")
            except OSError as e:
                problems.append(f"unreadable ({e}): {p} (failing closed)")
                continue
            # A TRIAL ID IS THE ANSWER KEY, not a hint. `.codex` hook scripts embedded
            # the absolute work-tree path, so 31 stored packs contained strings like
            # `g4_platformer__godot__t1` - naming the game, the stack AND the attempt.
            # #32 was this same defect in `MAPPING.json`. Checked FIRST because it is
            # categorically worse than a stack token.
            for m in anonymise._TRIAL_ID_RE.finditer(text):
                problems.append(
                    f"TRIAL ID {m.group(0)!r} in pack file {rel} - the judge is holding "
                    f"the answer key (#32, #83)")
                break
            m = anonymise._WORK_PATH_RE.search(text)
            if m:
                problems.append(
                    f"WORK-TREE PATH {m.group(0)[:60]!r} in pack file {rel} - it names "
                    f"the trial directory")
            if code_dir:
                continue
            # `find_stack_names` and not `_STACK_RE`: the regex list is now only the
            # residual literal forms, and iterating it here would scan for four patterns
            # while the rewriter knows 38 names. That is the #83 shape one level up - a
            # checker with a narrower vocabulary than the thing it checks reports clean
            # on exactly the leaks that motivated the repair (task 73).
            for tok in anonymise.find_stack_names(text)[:1]:
                problems.append(
                    f"STACK TOKEN {tok!r} in pack file {rel} - this text is "
                    f"shown to a blinded judge")
    return problems


def check(trial_dirs: list[Path], strict_vocab: bool = True) -> int:
    guid = canary()
    ids = criterion_ids()
    problems: list[str] = []

    for trial in trial_dirs:
        trial = trial.resolve()
        if not trial.exists():
            problems.append(f"trial path does not exist: {trial}")
            continue

        # 1. canary inside the tree
        problems += [f"[{trial.name}] {h}" for h in
                     scan(trial, {"CANARY IN TRIAL TREE": guid})]

        # 2. rubric reachable from an ancestor
        for anc in list(trial.parents):
            if anc == Path(anc.root):
                break
            try:
                for child in anc.iterdir():
                    if child.is_dir() and child.name == "judge" and \
                            (child / "RUBRIC.md").exists():
                        problems.append(
                            f"[{trial.name}] RUBRIC REACHABLE from ancestor {anc}: "
                            f"{child / 'RUBRIC.md'} - move trial trees outside the "
                            f"repository (see --work-root)")
                    if child.is_file() and child.name == "RUBRIC.md":
                        problems.append(
                            f"[{trial.name}] RUBRIC.md in ancestor {anc}")
            except PermissionError:
                problems.append(f"[{trial.name}] cannot inspect ancestor {anc} "
                                f"(failing closed)")

        # 3. criterion vocabulary
        if strict_vocab and ids:
            found = scan(trial, {f"CRITERION ID {i}": i for i in ids})
            problems += [f"[{trial.name}] {h}" for h in found]

    print(f"canary          : {guid}")
    print(f"criterion ids   : {len(ids)} checked")
    print(f"trial trees     : {len(trial_dirs)}")
    if problems:
        print(f"\nCONTAMINATED - {len(problems)} finding(s):")
        for p in problems[:60]:
            print(f"  {p}")
        if len(problems) > 60:
            print(f"  ... and {len(problems) - 60} more")
        return 1
    print("\nBLIND: the canary, the rubric and the criterion vocabulary are all "
          "absent from every trial tree and from every ancestor of one.")
    return 0


# --------------------------------------------------------------------------- #
# --selftest. The can-fail proof for the three trial-tree checks above.
#
# The two lines the mutants neuter carry a marker comment each, and the marker
# is spelled exactly twice in this file: once here, once on the line it marks.
# So a count over the shipped source reads 2 and a count over a correctly
# mutated copy reads 1, which is the structural half of each mutant row. The
# count is taken rather than a search for the mutation's effect, because the
# searcher's own source carries every string it would search for (task 113).
# --------------------------------------------------------------------------- #
_SCAN_MARK = "SELFTEST-NEUTER-SCAN"
_VOCAB_MARK = "SELFTEST-VOCAB-SOURCE"


class _Checks:
    def __init__(self) -> None:
        self.n = 0
        self.fails: list[str] = []

    def expect(self, name: str, cond: bool) -> None:
        self.n += 1
        if not cond:
            self.fails.append(name)


def _run(*args: str, script: Path | None = None) -> tuple[int, str, str]:
    p = subprocess.run(
        [sys.executable, str(script or Path(__file__).resolve()), *args],
        capture_output=True, text=True, timeout=120)
    return p.returncode, p.stdout, p.stderr


def _load(path: Path):
    """Import a copy of this tool by path, for its `criterion_ids()`/`canary()`."""
    spec = importlib.util.spec_from_file_location("_verify_blind_under_test", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def _rows(script: Path, fixtures: dict[str, Path], ids: list[str],
          tmp: Path) -> dict[str, bool]:
    """Run one copy of the tool over every fixture shape; did each row hold?

    All copies are evaluated over the SAME fixtures against the REAL imported
    vocabulary, so a mutant's row is red exactly when its behaviour left the
    shape the row is about.
    """

    def go(out: dict[str, bool], name: str, want_rc: int, want: tuple[str, ...],
           *args: str) -> None:
        rc, o, e = _run(*args, script=script)
        out[name] = rc == want_rc and all(w in o + e for w in want)

    out: dict[str, bool] = {}
    rc_clean, o_clean, _e = _run(str(fixtures["clean"]), script=script)
    out["clean tree exits 0 BLIND"] = rc_clean == 0 and "BLIND" in o_clean
    go(out, "canary plant exits 1 naming the file", 1,
       ("CANARY IN TRIAL TREE", "leak.py"), str(fixtures["canary"]))
    go(out, "criterion plant exits 1 naming the id and the file", 1,
       (f"CRITERION ID {ids[0]}", "leak.py"), str(fixtures["vocab"]))
    go(out, "ancestor RUBRIC.md file arm exits 1 naming the path", 1,
       ("RUBRIC.md in ancestor", str(tmp / "ancfile/work")),
       str(fixtures["ancfile"]))
    go(out, "ancestor judge/ arm exits 1 naming the path", 1,
       ("RUBRIC REACHABLE", str(tmp / "ancdir/work/judge/RUBRIC.md")),
       str(fixtures["ancdir"]))
    rc, o, e = _run(script=script)
    out["bare invocation refused at exit 2"] = (
        rc == 2 and "give trial directories" in e)
    # Two statements of one fact, kept apart: the count the tool prints about
    # itself, and the vocabulary imported from the file. They must agree.
    m = re.search(r"criterion ids\s*:\s*(\d+) checked", o_clean)
    out["printed criterion count is the imported vocabulary"] = (
        bool(m) and int(m.group(1)) == len(ids))
    return out


def _selftest() -> int:
    c = _Checks()
    here = Path(__file__).resolve()
    src = here.read_text()

    # THE FLOOR PINS, imported from this file rather than inferred from a run.
    # An empty vocabulary would leave check 3 silently passing on leaking trees
    # (`if strict_vocab and ids`), and a rubric without its canary line cannot
    # verify anything.
    mod = _load(here)
    ids = mod.criterion_ids()
    c.expect("vocabulary floor: criterion_ids() is nonempty", bool(ids))
    guid = mod.canary()
    c.expect("canary floor: the rubric carries a GUID", bool(guid))
    if not ids or not guid:
        print(f"\n{c.n - len(c.fails)}/{c.n} expectations held")
        print("FAILED: " + ", ".join(c.fails))
        return 1
    vocab_id = sorted(ids)[0]

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)

        # One subtree per shape, plants nested so no trial's ancestor walk
        # crosses another's. An ancestor of any of these holding a RUBRIC.md of
        # its own would redden the clean row loudly - fail closed, and named.
        def trial(rel: str) -> Path:
            d = tmp / rel
            d.mkdir(parents=True)
            (d / "justfile").write_text("run:\n\t@python3 game.py\n")
            (d / "game.py").write_text('print("the game")\n')
            return d

        fixtures = {"clean": trial("clean/trial"), "canary": trial("canary/trial"),
                    "vocab": trial("vocab/trial"), "ancfile": trial("ancfile/work/trial"),
                    "ancdir": trial("ancdir/work/trial")}
        (fixtures["canary"] / "leak.py").write_text(f'x = "{guid}"\n')
        (fixtures["vocab"] / "leak.py").write_text(f"assert {vocab_id}\n")
        (tmp / "ancfile/work/RUBRIC.md").write_text("# a planted rubric file\n")
        (tmp / "ancdir/work/judge").mkdir()
        (tmp / "ancdir/work/judge/RUBRIC.md").write_text("# the real rubric's shape\n")

        # The green half, against the shipped file: every row must hold.
        for name, held in _rows(here, fixtures, ids, tmp).items():
            c.expect(name, held)

        # THE MUTANTS. Each rebuilds this file with ONE marked line neutered,
        # and each must turn its own rows red while the rows the OTHER checks
        # own stay green - that separation is what makes them discriminating
        # rather than merely failing. The mutants are run over the fixtures
        # bare, never with --selftest: a selftest evaluating itself is the
        # recursion ci_minutes.py bounds GATES_DEPTH against.
        scan_mut_text = re.sub(
            r"^[ \t]*hits\.append\(f\"\{label\}: \{p\}\"\)[^\n]*" + _SCAN_MARK
            + r"[^\n]*\n",
            " " * 16 + "pass  # neutered: the scan can report nothing\n",
            src, flags=re.M)
        vocab_mut_text = re.sub(
            r"^[ \t]*ids = set\(re\.findall[^\n]*" + _VOCAB_MARK + r"[^\n]*\n",
            " " * 4 + "ids: set[str] = set()  # neutered: the vocabulary is empty\n",
            src, flags=re.M)

        scan_mut = tmp / "mutant_scan" / "verify_blind.py"
        scan_mut.parent.mkdir()
        scan_mut.write_text(scan_mut_text)
        vocab_mut = tmp / "mutant_vocab" / "verify_blind.py"
        vocab_mut.parent.mkdir()
        vocab_mut.write_text(vocab_mut_text)
        # A copy of this tool resolves RUBRIC.md against ITS OWN directory, so
        # each mutant needs the rubric beside it or `canary()` dies on every
        # run - a crash that would redden every mutant row for a reason that has
        # nothing to do with the neutering.
        for mut_dir in (scan_mut.parent, vocab_mut.parent):
            shutil.copy(HERE / "RUBRIC.md", mut_dir / "RUBRIC.md")

        c.expect("MUTANT scan-neutered: the mutation changed the source",
                 src.count(_SCAN_MARK) - 1 == scan_mut_text.count(_SCAN_MARK))
        rc, o, _e = _run(str(fixtures["canary"]), script=scan_mut)
        c.expect("MUTANT scan-neutered: the canary leak exits 0 and reads BLIND "
                 "(check can fail)",
                 rc == 0 and "BLIND" in o and "CONTAMINATED" not in o)
        rc, o, _e = _run(str(fixtures["vocab"]), script=scan_mut)
        c.expect("MUTANT scan-neutered: the criterion leak exits 0 and reads BLIND "
                 "(check can fail)",
                 rc == 0 and "BLIND" in o and "CONTAMINATED" not in o)
        scan_rows = _rows(scan_mut, fixtures, ids, tmp)
        c.expect("MUTANT scan-neutered: the ancestor file arm is STILL caught",
                 scan_rows["ancestor RUBRIC.md file arm exits 1 naming the path"])
        c.expect("MUTANT scan-neutered: the ancestor judge/ arm is STILL caught",
                 scan_rows["ancestor judge/ arm exits 1 naming the path"])
        c.expect("MUTANT scan-neutered: the clean tree is still BLIND",
                 scan_rows["clean tree exits 0 BLIND"])
        c.expect("MUTANT scan-neutered: bare invocation still refused",
                 scan_rows["bare invocation refused at exit 2"])
        c.expect("MUTANT scan-neutered: the printed criterion count still agrees",
                 scan_rows["printed criterion count is the imported vocabulary"])

        c.expect("MUTANT vocab-emptied: the mutation changed the source",
                 src.count(_VOCAB_MARK) - 1 == vocab_mut_text.count(_VOCAB_MARK))
        # The sibling defect in one row: check 3 is gated on the vocabulary being
        # non-empty, so emptying it does not error - the leak is passed as BLIND
        # with `0 checked`.
        rc, o, _e = _run(str(fixtures["vocab"]), script=vocab_mut)
        c.expect("MUTANT vocab-emptied: the criterion leak exits 0 and reads BLIND "
                 "with 0 checked (check can fail)",
                 rc == 0 and "BLIND" in o and "0 checked" in o
                 and "CONTAMINATED" not in o)
        c.expect("MUTANT vocab-emptied: the imported vocabulary is empty",
                 _load(vocab_mut).criterion_ids() == [])
        vocab_rows = _rows(vocab_mut, fixtures, ids, tmp)
        c.expect("MUTANT vocab-emptied: the canary plant is STILL caught",
                 vocab_rows["canary plant exits 1 naming the file"])
        c.expect("MUTANT vocab-emptied: the ancestor file arm is STILL caught",
                 vocab_rows["ancestor RUBRIC.md file arm exits 1 naming the path"])
        c.expect("MUTANT vocab-emptied: the ancestor judge/ arm is STILL caught",
                 vocab_rows["ancestor judge/ arm exits 1 naming the path"])
        c.expect("MUTANT vocab-emptied: the clean tree is still BLIND",
                 vocab_rows["clean tree exits 0 BLIND"])
        c.expect("MUTANT vocab-emptied: bare invocation still refused",
                 vocab_rows["bare invocation refused at exit 2"])

    print(f"\n{c.n - len(c.fails)}/{c.n} expectations held")
    if c.fails:
        print("FAILED: " + ", ".join(c.fails))
        return 1
    print("verify_blind selftest: every trial-tree check can fail - the canary, "
          "the vocabulary and both ancestor arms each turn their fixture red "
          "naming the offending file, and a scan-neutered copy and an "
          "empty-vocabulary copy each fail the rows they own.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="*", type=Path, default=[],
                    help="trial working directories (or a run dir's work/ folder)")
    ap.add_argument("--no-vocab", action="store_true",
                    help="skip the criterion-id vocabulary check")
    ap.add_argument("--packs", nargs="*", type=Path, default=[],
                    help="judge pack directories: scan every non-code file in them "
                         "(BRIEF.md, .claude/skills/**) for stack tokens, because those "
                         "are hand-written evidence the blinded judge reads")
    ap.add_argument("--selftest", action="store_true",
                    help="run the offline fixture suite over the three trial-tree "
                         "checks, including the scan-neutered and vocabulary-emptied "
                         "mutants of this file")
    a = ap.parse_args()
    if a.selftest:
        return _selftest()
    if not a.paths and not a.packs:
        ap.error("give trial directories, --packs, or both")
    if a.packs:
        pack_problems = check_pack_skill(list(a.packs))
        print(f"packs scanned   : {len(a.packs)}")
        if pack_problems:
            print(f"\nCONTAMINATED - {len(pack_problems)} finding(s) in pack text:")
            for p in pack_problems[:40]:
                print(f"  {p}")
            return 1
        print("pack text       : BLIND (no stack tokens outside code/)")
    targets: list[Path] = []
    for p in a.paths:
        p = p.resolve()
        # A run/work root holds one directory per trial; a trial holds a justfile.
        # Expand a root so the ancestor check runs against each trial individually.
        if p.is_dir() and not (p / "justfile").exists() and \
                any(c.is_dir() and (c / "justfile").exists() for c in p.iterdir()):
            targets += [c for c in p.iterdir() if c.is_dir()]
        else:
            targets.append(p)
    if not targets:
        return 0
    return check(targets, strict_vocab=not a.no_vocab)


if __name__ == "__main__":
    sys.exit(main())
