#!/usr/bin/env python3
"""Assert that every path instruction in `.coderabbit.yaml` names an address that exists.

WHAT THIS PROTECTS. `.coderabbit.yaml` spells repository paths that are also spelled by the
tree, and `AGENTS.md` rule 12 says to assert a duplicated address in code rather than promise
it in a comment. A `path_instruction` aimed at a path no diff can contain is not a warning and
not a crash: the review simply stops carrying that rule, and every review afterwards looks
exactly like a review that had it.

That is not hypothetical. `.claude/skills/**/SKILL.md` carried the rule *"flag any change that
makes a skill restate a fact that belongs in its authoritative document"*, and PR #2 cited it
as the source of a true positive. Task 114 then moved the 10 real `SKILL.md` files to
`.agents/skills/` and left `.claude/skills` as a symlink, which git tracks as 1 mode-120000
blob — so the pattern matched 0 tracked files and the rule went quiet, with nothing to see it
(`tasks/117`).

WHY ONLY `path_instructions`, AND NOT `path_filters`. An instruction that matches nothing is a
rule that cannot fire. An *exclusion* that matches nothing is a guard held against a future
state, and `.coderabbit.yaml` ships one deliberately: `!eval/runs/**` matches 0 tracked files
because that tree is gitignored, and it is kept for the day `.gitignore` changes. Reddening it
would be firing where nothing is wrong.

WHAT THIS DOES NOT CHECK, and why it is not the path check `--sweep` deleted. `docstat.py`
removed its path check because paths in PROSE are legitimately relative to a context stated in
a sentence or a table cell — 0 true positives, 2 false. A `path_instructions[].path` has no
such context: it is a glob a machine matches against the repository root, so the extraction is
exact and the comparison is total.

The other half of a `.coderabbit.yaml` audit — that every key under `reviews.tools` is a tool
the published schema knows — needs the network, so it is not gated here. It matters, because
the schema does NOT set `additionalProperties: false` on that object: a typo is accepted and
silently ignored, which is the accepted-but-ignored-flag shape. Run it by hand against
https://storage.googleapis.com/coderabbit_public_assets/schema.v2.json when you edit that
block.

The audited repository is ONE input. `--root` selects it, and the config is that root's own
`.coderabbit.yaml` — there is deliberately no way to point the two at different trees, because a
config from one repository checked against another's file list returns a confident green.

Usage:
    python3 eval/tools/coderabbit_config.py            # gate: exit 1 if any instruction is dead
    python3 eval/tools/coderabbit_config.py --control  # pin it red and green; exit 1 if a pin fails
"""

import argparse
import copy
import fnmatch
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
CONFIG_NAME = ".coderabbit.yaml"

# ONE ADDRESS, NOT TWO. This took a `--config` alongside `--root` until PR #4's review: the
# config could then be read from one tree and the file list from another, and the audit would
# report green because the unrelated repository happened to satisfy the loaded patterns. That
# is rule 12 - the address is an input to the check - committed inside the gate written to
# enforce rule 12. The repair is structural rather than an equality assertion: with the config
# derived from the root there is no second address left to disagree.


def tracked_files(root: Path) -> list[str]:
    """Every git-tracked path, as git spells it. Unpiped: a failure here must be visible."""
    out = subprocess.run(
        ["git", "-C", str(root), "ls-files"], capture_output=True, text=True, check=False
    )
    if out.returncode != 0:
        raise SystemExit(f"git ls-files failed ({out.returncode}): {out.stderr.strip()}")
    return out.stdout.splitlines()


def matching(pattern: str, paths: list[str]) -> list[str]:
    """Paths a CodeRabbit glob covers.

    `fnmatch`'s `*` already spans `/`, so a `**` pattern behaves as CodeRabbit means it and a
    single-`*` pattern is treated more permissively than CodeRabbit would. That direction is
    the safe one: it can only make this check MORE forgiving, so a row that goes red here is
    red under any reading of the glob.
    """
    return [p for p in paths if fnmatch.fnmatch(p, pattern)]


def audit(config: dict, paths: list[str]) -> list[tuple[str, int]]:
    """(pattern, number of tracked files it covers) for each path instruction, in file order."""
    instructions = (config.get("reviews") or {}).get("path_instructions") or []
    return [(pi["path"], len(matching(pi["path"], paths))) for pi in instructions]


def run(config: dict, paths: list[str], quiet: bool = False) -> int:
    rows = audit(config, paths)
    dead = 0
    for pattern, n in rows:
        ok = n > 0
        dead += 0 if ok else 1
        if not quiet:
            detail = f"{n} tracked files" if ok else "MATCHES NOTHING TRACKED"
            print(f"  {'ok  ' if ok else 'RED '} {pattern:<34} {detail}")
    if not quiet:
        print(f"\n{len(rows)} path instructions, {dead} dead")
    return 1 if dead else 0


def control(config: dict, paths: list[str]) -> int:
    """Pin the gate in both directions.

    Green on the shipped config is necessary and not sufficient: a check over an empty list of
    instructions is also green. Each mutant kills exactly 1 address, and a different one, so a
    gate hard-coded to watch a single row cannot survive all of them.
    """
    mutants = [
        (
            "skills_instruction_back_to_the_symlink",
            ".agents/skills/**/SKILL.md",
            ".claude/skills/**/SKILL.md",
        ),
        ("starters_instruction_misspelled", "eval/starters/**", "eval/starter/**"),
        ("tasks_instruction_misspelled", "tasks/**", "task/**"),
    ]

    print("shipped config, expected GREEN")
    live = run(config, paths)
    rows = audit(config, paths)
    print(f"  -> exit {live}, over {len(rows)} instructions\n")
    failures = 0 if (live == 0 and rows) else 1
    if not rows:
        print("  PIN FAILED: 0 instructions read, so green means nothing")

    for name, real, broken in mutants:
        mutated = copy.deepcopy(config)
        hit = 0
        for pi in mutated["reviews"]["path_instructions"]:
            if pi["path"] == real:
                pi["path"] = broken
                hit += 1
        if hit != 1:
            print(f"{name}: PIN FAILED, expected 1 instruction on {real!r}, found {hit}")
            failures += 1
            continue
        got = run(mutated, paths, quiet=True)
        ok = got == 1
        failures += 0 if ok else 1
        print(f"{name}: {real} -> {broken}: exit {got} {'RED as required' if ok else 'SURVIVED'}")

    print(f"\n{len(mutants) + 1} pins, {failures} failed")
    return 1 if failures else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument(
        "--root",
        default=str(ROOT),
        help=f"repository to audit; its {CONFIG_NAME} and its git file list, never a mixed pair",
    )
    ap.add_argument("--control", action="store_true", help="pin the gate red and green")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    config_path = root / CONFIG_NAME
    if not config_path.is_file():
        raise SystemExit(f"no {CONFIG_NAME} in {root} - that is an error, not an empty audit")
    config = yaml.safe_load(config_path.read_text())
    paths = tracked_files(root)
    print(f"{config_path} against {len(paths)} tracked files in {root}\n")
    return control(config, paths) if args.control else run(config, paths)


if __name__ == "__main__":
    sys.exit(main())
