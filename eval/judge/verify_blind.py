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
"""

from __future__ import annotations

import argparse
import re
import sys
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
    ids = set(re.findall(r"`([a-z]+\.[a-z_]+)`", RUBRIC.read_text()))
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
                hits.append(f"{label}: {p}")
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
            for rx, _ in anonymise._STACK_RE:
                m = rx.search(text)
                if m:
                    problems.append(
                        f"STACK TOKEN {m.group(0)!r} in pack file {rel} - this text is "
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
    a = ap.parse_args()
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
