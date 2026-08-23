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
the published schema knows — needs the network, so it is `--schema` and not part of the gate.
It matters, and the schema was read on 2026-08-23 to find out how much:

    (root).additionalProperties          False   <- a misspelled TOP-LEVEL key is rejected
    reviews.additionalProperties       absent
    reviews.tools.additionalProperties absent    <- a misspelled TOOL key is accepted

Draft 2020-12 permits unknown properties wherever the keyword is absent, so the closure is
exactly one level deep: `reviws:` fails, `reviews.tools.skillspecter:` passes and is then
silently ignored. That is the accepted-but-ignored-flag shape (`AGENTS.md` rule 13) — an
unsupported key that fails loudly is safer than one indistinguishable from a working setting.
`--schema` is what turns "run it by hand" into a command; run it when you edit that block.

WHY IT IS NOT IN CI. It needs the network, and a gate that fails when a third party's bucket
is unreachable trains the reader to ignore it. Recorded as a deliberate exclusion in
`.github/workflows/README.md` rather than left silently absent.

The audited repository is ONE input. `--root` selects it, and the config is that root's own
`.coderabbit.yaml` — there is deliberately no way to point the two at different trees, because a
config from one repository checked against another's file list returns a confident green.

Usage:
    python3 eval/tools/coderabbit_config.py            # gate: exit 1 if any instruction is dead
    python3 eval/tools/coderabbit_config.py --control  # pin it red and green; exit 1 if a pin fails
    python3 eval/tools/coderabbit_config.py --schema   # NETWORK: are our tool keys real tools?
"""

import argparse
import copy
import fnmatch
import json
import subprocess
import sys
import urllib.request
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
CONFIG_NAME = ".coderabbit.yaml"
SCHEMA_URL = "https://storage.googleapis.com/coderabbit_public_assets/schema.v2.json"

#: Tools this repository's config names in prose or in a key, whose presence in the published
#: schema is known in advance. `--schema` checks these BEFORE reporting on anything else: a
#: census that returns one value across a population it exists to discriminate is reporting
#: the instrument, and an extraction aimed at the wrong node would call every key unknown.
#: `markdownlint` and `languagetool` are recorded in `.coderabbit.yaml` as having produced
#: findings on PR #2; `skillspector` is the key the same file sets.
SCHEMA_CONTROL_TOOLS = ("markdownlint", "languagetool", "skillspector")

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
    """Red if any instruction is dead, and red if there are no instructions to audit.

    The empty case is not a clean bill of health, it is `total=0 passed=0` — the shape this
    project calls a mechanism that runs, reports success and measures nothing. It arrives by
    a typo in `reviews:` or `path_instructions:` deleting the whole block, which is precisely
    when a green audit is most misleading.
    """
    rows = audit(config, paths)
    dead = 0
    for pattern, n in rows:
        ok = n > 0
        dead += 0 if ok else 1
        if not quiet:
            detail = f"{n} tracked files" if ok else "MATCHES NOTHING TRACKED"
            print(f"  {'ok  ' if ok else 'RED '} {pattern:<34} {detail}")
    if not rows:
        if not quiet:
            print("  RED  no reviews.path_instructions at all - nothing was audited")
        return 1
    if not quiet:
        print(f"\n{len(rows)} path instructions, {dead} dead")
    return 1 if dead else 0


def _rename(real: str, broken: str):
    """Mutant: point one existing instruction at an address the tree does not have.

    Raises if it does not hit exactly 1 instruction, so a mutant that has quietly stopped
    describing the config fails the pin instead of passing it by not applying.
    """

    def apply(cfg: dict) -> None:
        hit = [pi for pi in cfg["reviews"]["path_instructions"] if pi["path"] == real]
        if len(hit) != 1:
            raise ValueError(f"expected 1 instruction on {real!r}, found {len(hit)}")
        hit[0]["path"] = broken

    return apply


def _drop_all(cfg: dict) -> None:
    """Mutant: delete the whole block, which is how a green audit comes to measure nothing."""
    cfg["reviews"]["path_instructions"] = []


def control(config: dict, paths: list[str]) -> int:
    """Pin the gate in both directions.

    Green on the shipped config is necessary and not sufficient, so the pins cover both ways
    it could be hollow. Each rename kills exactly 1 address, and a different one, so a gate
    hard-coded to watch a single row cannot survive them all; `no_path_instructions_at_all`
    is the `total=0 passed=0` case, and it is here because the gate returned success on it
    until PR #4's review said so.
    """
    mutants = [
        (
            "skills_instruction_back_to_the_symlink",
            _rename(".agents/skills/**/SKILL.md", ".claude/skills/**/SKILL.md"),
        ),
        ("starters_instruction_misspelled", _rename("eval/starters/**", "eval/starter/**")),
        ("tasks_instruction_misspelled", _rename("tasks/**", "task/**")),
        ("no_path_instructions_at_all", _drop_all),
    ]

    print("shipped config, expected GREEN")
    live = run(config, paths)
    rows = audit(config, paths)
    print(f"  -> exit {live}, over {len(rows)} instructions\n")
    failures = 0 if (live == 0 and rows) else 1
    if not rows:
        print("  PIN FAILED: 0 instructions read, so green means nothing")

    for name, apply in mutants:
        mutated = copy.deepcopy(config)
        try:
            apply(mutated)
        except (KeyError, TypeError, ValueError) as exc:
            print(f"{name}: PIN FAILED, mutant would not apply: {exc}")
            failures += 1
            continue
        got = run(mutated, paths, quiet=True)
        ok = got == 1
        failures += 0 if ok else 1
        print(f"{name}: exit {got} {'RED as required' if ok else 'SURVIVED'}")

    print(f"\n{len(mutants) + 1} pins, {failures} failed")
    return 1 if failures else 0


def schema_audit(config: dict) -> int:
    """Every key under `reviews.tools` against the published schema. NETWORK.

    The schema does not close that object, so nothing upstream will ever tell us a key is
    misspelled - the review simply runs without the setting, which is indistinguishable from
    a setting that is being honoured. This is the only thing that can ask.

    Red on: a tool key the schema does not declare; a per-tool sub-key it does not declare
    (`skillspector` offers `enabled` and nothing else, so `severity: off` would be silently
    dropped the same way); an empty tools block read as a clean bill of health; or the control
    tools missing, which means the extraction is aimed at the wrong node.
    """
    print(f"fetching {SCHEMA_URL}")
    try:
        with urllib.request.urlopen(SCHEMA_URL, timeout=30) as r:
            body = r.read()
    except (OSError, ValueError) as exc:
        # An unreachable schema is an ERROR, not an empty audit. Returning 0 here would be
        # `cmd || echo 0` on a measurement (AGENTS.md rule 3).
        print(f"  RED  could not read the schema: {exc}")
        return 1
    schema = json.loads(body)
    print(f"  ok   {len(body)} bytes, {schema.get('$schema')}")

    try:
        tools_node = schema["properties"]["reviews"]["properties"]["tools"]
    except (KeyError, TypeError) as exc:
        print(f"  RED  the schema has no reviews.tools node ({exc}) - the shape moved, and "
              f"this audit is aimed at an address that no longer exists")
        return 1
    declared = tools_node.get("properties") or {}

    missing = [t for t in SCHEMA_CONTROL_TOOLS if t not in declared]
    if missing:
        print(f"  RED  CONTROL: {missing} absent from reviews.tools.properties, which "
              f"{'.coderabbit.yaml'} records as real tools - this extraction is reading the "
              f"wrong node and every verdict below it would be wrong")
        return 1
    print(f"  ok   control: {list(SCHEMA_CONTROL_TOOLS)} all declared, "
          f"of {len(declared)} tools the schema knows")

    # Draft 2020-12 permits unknown properties unless the keyword says otherwise, so "absent"
    # and `True` both mean open. Only an explicit `False` closes the object.
    closed = tools_node.get("additionalProperties", "absent")
    note = "" if closed is False else "  <- unknown keys are ACCEPTED and silently ignored"
    print(f"\n  reviews.tools.additionalProperties = {closed!r}{note}")

    ours = ((config.get("reviews") or {}).get("tools")) or {}
    if not ours:
        print("\n  RED  no reviews.tools block - nothing was audited, which is not the same "
              "as nothing being wrong")
        return 1

    bad = 0
    for key, value in sorted(ours.items()):
        if key not in declared:
            near = [d for d in declared if d.startswith(key[:4]) or key.startswith(d[:4])]
            print(f"  RED  {key:<22} not a tool the schema declares"
                  + (f" - did you mean {near}?" if near else ""))
            bad += 1
            continue
        sub = (declared[key].get("properties") or {})
        unknown = [k for k in (value or {}) if k not in sub]
        if unknown:
            print(f"  RED  {key:<22} sets {unknown}, which it does not declare "
                  f"(it offers {sorted(sub)})")
            bad += 1
        else:
            print(f"  ok   {key:<22} {dict(value or {})}")

    print(f"\n{len(ours)} tool keys configured, {bad} the schema does not know")
    return 1 if bad else 0


def schema_control(config: dict) -> int:
    """Pin `--schema` red on a misspelling, since green on the shipped config proves nothing.

    The audit's whole subject is a key nothing upstream rejects, so `total=0 passed=0` is its
    natural resting state and the only way to know it can fire is to make it.
    """
    typo = copy.deepcopy(config)
    tools = typo.setdefault("reviews", {}).setdefault("tools", {})
    if "skillspector" not in tools:
        print("PIN FAILED: the shipped config sets no `skillspector` key, so this mutant "
              "does not describe it any more")
        return 1
    tools["skillspecter"] = tools.pop("skillspector")

    print("shipped config, expected GREEN")
    live = schema_audit(config)
    print(f"  -> exit {live}\n")
    print("MUTANT: `skillspector` misspelled as `skillspecter`, expected RED")
    got = schema_audit(typo)
    print(f"  -> exit {got}\n")
    failures = (0 if live == 0 else 1) + (0 if got == 1 else 1)
    print(f"2 pins, {failures} failed")
    return 1 if failures else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument(
        "--root",
        default=str(ROOT),
        help=f"repository to audit; its {CONFIG_NAME} and its git file list, never a mixed pair",
    )
    ap.add_argument("--control", action="store_true", help="pin the gate red and green")
    ap.add_argument("--schema", action="store_true",
                    help="NETWORK: audit reviews.tools keys against the published schema")
    args = ap.parse_args()

    root = Path(args.root).resolve()
    config_path = root / CONFIG_NAME
    if not config_path.is_file():
        raise SystemExit(f"no {CONFIG_NAME} in {root} - that is an error, not an empty audit")
    config = yaml.safe_load(config_path.read_text())

    if args.schema:
        print(f"{config_path}\n")
        return schema_control(config) if args.control else schema_audit(config)

    paths = tracked_files(root)
    print(f"{config_path} against {len(paths)} tracked files in {root}\n")
    return control(config, paths) if args.control else run(config, paths)


if __name__ == "__main__":
    sys.exit(main())
