#!/usr/bin/env python3
"""Can `flag_binding.py` fail - and can it still pass on the code it must not flag?

WHY THIS EXISTS
---------------
`flag_binding.py` prints thirteen green rows against the shipped harness, which on its own
establishes nothing: a checker that has only ever agreed has not been shown capable of
disagreeing. The defect it was written for is silent by construction - a `dest` moves, the
code keeps reading the old name through a string, the run completes and records the wrong
arm - so "it went green" is exactly what the defect looks like.

THE KINDS OF ROW
----------------
  PRISTINE    the shipped source and the shipped parser, unedited: 0 red. Not a result on
              its own; it makes a red row below attributable to the plant.

  MUTANT      one edit the checker MUST report, named row by row. "Can it fail?"

  VARIANT     code the checker must still PASS on. AGENTS.md rule 15: a mutant asks whether
              a check can fail, and only a variant asks whether it can still pass on an
              input it mishandles - which is the kind every false negative here has been.
              A `getattr` on something that is not the namespace, and a newly added flag,
              are both legitimate and both within a careless trigger's reach.

  DISARMED    the checker's own mechanism removed with a MUTANT plant still in place,
              asserting the row goes green again. This is what shows a red row was caused by
              the mechanism it names and not by something else the edit disturbed.

  BEHAVIOUR   the runtime half, on the real module. Renaming a dest and calling the real
              `cmd_plan` must raise `AttributeError`; the same rename against the same
              function with the `getattr(a, "scenes", None)` form restored must NOT raise.
              That pair is the whole argument for both halves of task 183: direct access
              turns a rename into a crash, and the crash is still late - the static rows
              above are what act before a launch.

Run it unpiped and read its own exit code:

    python3 eval/tools/flag_binding_control.py
"""
from __future__ import annotations

import argparse
import ast
import contextlib
import importlib.util
import io
import sys
import types
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import flag_binding as fb  # noqa: E402

WHOLEGAME = fb.WHOLEGAME
PRISTINE_SOURCE = WHOLEGAME.read_text()

_seq = 0


def module_from(source: str):
    """Exec `source` as a module whose `__file__` is the real `wholegame.py`.

    The file path matters: `wholegame` derives `HERE` from `__file__` and puts `suites/`,
    `judge/` and `tools/` on `sys.path` from it, so a copy exec'd under any other path
    would fail to import for a reason that has nothing to do with the plant.
    """
    global _seq
    _seq += 1
    name = f"_flagbind_variant_{_seq}"
    mod = types.ModuleType(name)
    mod.__file__ = str(WHOLEGAME)
    sys.modules[name] = mod
    exec(compile(source, str(WHOLEGAME), "exec"), mod.__dict__)
    return mod


def edit(source: str, old: str, new: str) -> str:
    n = source.count(old)
    if n != 1:
        raise SystemExit(
            f"PLANT DOES NOT APPLY: {old!r} occurs {n} times in wholegame.py. The control "
            f"is aimed at text that is no longer there, so every row below would be "
            f"measuring the plant rather than the checker (AGENTS.md rule 12).")
    return source.replace(old, new)


def run_check(source: str) -> tuple[int, dict[str, list[str]]]:
    """(failures, tag -> the red rows carrying that tag)."""
    bad, rows = fb.check(source=source, mod=module_from(source))
    red: dict[str, list[str]] = {}
    for r in rows:
        if r.startswith("RED"):
            red.setdefault(r.split()[1], []).append(r)
    return bad, red


# --------------------------------------------------------------------------- #
# the plants
# --------------------------------------------------------------------------- #

RENAME_DEST = ('p.add_argument("--harness", default=HARNESS,',
               'p.add_argument("--harness", dest="harness_cli", default=HARNESS,')
RESTORE_GETATTR = ("harness = agent_harness.get(a.harness)",
                   'harness = agent_harness.get(getattr(a, "harness", None) or HARNESS)')
DROP_DISPATCH = ('"plan": cmd_plan, "build": cmd_build,', '"build": cmd_build,')
DROP_DELEGATION = ('DELEGATES_TO = {"cmd_evaluate": "cmd_report"}', "DELEGATES_TO = {}")
GETATTR_ELSEWHERE = ("harness = agent_harness.get(a.harness)",
                     "harness = agent_harness.get(a.harness)\n"
                     '    _ = getattr(harness, "name", "")')
NEW_FLAG = ('p.add_argument("--trials", type=int, default=2)',
            'p.add_argument("--trials", type=int, default=2)\n'
            '        p.add_argument("--probe-x", default=None)')
READ_NEW_FLAG = ("    stacks = a.stacks or list(P.STACKS)\n"
                 "    games = select_tasks(a.games, a.scenes)\n"
                 "    classes = {aspects.task_class(t) for t in games}",
                 "    stacks = a.stacks or list(P.STACKS)\n"
                 "    games = select_tasks(a.games, a.scenes)\n"
                 "    _ = a.probe_x\n"
                 "    classes = {aspects.task_class(t) for t in games}")
PLAN_GETATTR = ("    games = select_tasks(a.games, a.scenes)\n"
                "    classes = {aspects.task_class(t) for t in games}",
                '    games = select_tasks(a.games, getattr(a, "scenes", None))\n'
                "    classes = {aspects.task_class(t) for t in games}")


def rename_plan_scenes(mod) -> argparse.Namespace:
    """Move `--scenes`'s dest on `plan`, then parse. The rename is asserted, not assumed."""
    parser = mod.build_parser()
    subs = [x for x in parser._actions if isinstance(x, argparse._SubParsersAction)][0]
    act = [x for x in subs.choices["plan"]._actions if x.dest == "scenes"][0]
    act.dest = "scenes_cli"
    ns = parser.parse_args(["plan", "--trials", "1"])
    if hasattr(ns, "scenes") or not hasattr(ns, "scenes_cli"):
        raise SystemExit(
            "THE RENAME DID NOT TAKE: the namespace still carries `scenes`, so a green "
            "behaviour row below would say nothing about a renamed dest.")
    return ns


# --------------------------------------------------------------------------- #


def rows() -> list[tuple[bool, str, str, str]]:
    out: list[tuple[bool, str, str, str]] = []

    def add(ok: bool, kind: str, name: str, detail: str) -> None:
        out.append((ok, kind, name, detail))

    bad, red = run_check(PRISTINE_SOURCE)
    add(bad == 0, "PRISTINE", "shipped harness",
        f"{bad} red rows" + ("" if bad == 0 else f": {red}"))

    # --- MUTANT ------------------------------------------------------------ #
    bad, red = run_check(edit(PRISTINE_SOURCE, *RENAME_DEST))
    add("BIND" in red, "MUTANT", "--harness dest renamed",
        f"BIND red: {'BIND' in red}; rows={sum(red.values(), [])}")

    bad, red = run_check(edit(PRISTINE_SOURCE, *RESTORE_GETATTR))
    add("BY-STRING" in red, "MUTANT", "getattr form restored",
        f"BY-STRING red: {'BY-STRING' in red}")

    both = edit(edit(PRISTINE_SOURCE, *RESTORE_GETATTR), *RENAME_DEST)
    bad, red = run_check(both)
    add("BY-STRING" in red and "BIND" not in red, "MUTANT",
        "both: the historical silent state",
        "BY-STRING red and BIND GREEN - the read vanished from the AST with the dest "
        "renamed, which is the silence BY-STRING exists for")

    bad, red = run_check(edit(PRISTINE_SOURCE, *DROP_DISPATCH))
    add("DISPATCH" in red, "MUTANT", "a subcommand dropped from DISPATCH",
        f"DISPATCH red: {'DISPATCH' in red}")

    bad, red = run_check(edit(PRISTINE_SOURCE, *DROP_DELEGATION))
    add("DELEGATES" in red, "MUTANT", "cmd_evaluate -> cmd_report undeclared",
        f"DELEGATES red: {'DELEGATES' in red}")

    # The SELFTEST row's own mechanism: the `default is not SUPPRESS` filter. Without it
    # the derivation over-reports `-h`'s dest, which is the defect this row caught when
    # the checker was first run.
    keep = fb.subcommand_dests
    try:
        def dest_only(parser: argparse.ArgumentParser) -> dict[str, set[str]]:
            subs = [a for a in parser._actions
                    if isinstance(a, argparse._SubParsersAction)][0]
            top = {a.dest for a in parser._actions if a.dest != argparse.SUPPRESS}
            return {n: top | {a.dest for a in sp._actions if a.dest != argparse.SUPPRESS}
                    for n, sp in subs.choices.items()}
        fb.subcommand_dests = dest_only
        bad, red = run_check(PRISTINE_SOURCE)
        add("SELFTEST" in red, "MUTANT", "derivation filters on dest alone",
            f"SELFTEST red: {'SELFTEST' in red}")
    finally:
        fb.subcommand_dests = keep

    # --- VARIANT ----------------------------------------------------------- #
    bad, red = run_check(edit(PRISTINE_SOURCE, *GETATTR_ELSEWHERE))
    add(bad == 0, "VARIANT", "getattr on a non-namespace object",
        f"{bad} red rows - BY-STRING keys on the argument, not on the builtin's name")

    added = edit(edit(PRISTINE_SOURCE, *NEW_FLAG), *READ_NEW_FLAG)
    bad, red = run_check(added)
    add(bad == 0, "VARIANT", "a new flag declared and read directly",
        f"{bad} red rows - adding a bound flag must not redden")

    # --- DISARMED ---------------------------------------------------------- #
    keep_visit = fb._Reads.visit_Attribute
    try:
        fb._Reads.visit_Attribute = lambda self, node: fb.ast.NodeVisitor.generic_visit(
            self, node)
        bad, red = run_check(edit(PRISTINE_SOURCE, *RENAME_DEST))
        add("BIND" not in red, "DISARMED", "attribute collection removed",
            "the renamed-dest plant is still in place and BIND is green, so its red row "
            "above came from the collection")
    finally:
        fb._Reads.visit_Attribute = keep_visit

    keep_bs = fb.BY_STRING
    try:
        fb.BY_STRING = ()
        bad, red = run_check(edit(PRISTINE_SOURCE, *RESTORE_GETATTR))
        add("BY-STRING" not in red, "DISARMED", "the by-string builtin list emptied",
            "the restored-getattr plant is still in place and BY-STRING is green")
    finally:
        fb.BY_STRING = keep_bs

    # --- BEHAVIOUR --------------------------------------------------------- #
    shipped = module_from(PRISTINE_SOURCE)
    buf = io.StringIO()
    try:
        with contextlib.redirect_stdout(buf):
            rc = shipped.cmd_plan(shipped.build_parser().parse_args(
                ["plan", "--trials", "1"]))
        add(rc == 0, "BEHAVIOUR", "cmd_plan on an unrenamed namespace",
            f"returned {rc}")
    except Exception as e:                              # noqa: BLE001
        add(False, "BEHAVIOUR", "cmd_plan on an unrenamed namespace",
            f"raised {type(e).__name__}: {e}")

    ns = rename_plan_scenes(shipped)
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            rc = shipped.cmd_plan(ns)
        add(False, "BEHAVIOUR", "renamed dest, direct access",
            f"returned {rc} - a moved dest went UNNOTICED")
    except AttributeError as e:
        add("scenes" in str(e), "BEHAVIOUR", "renamed dest, direct access",
            f"AttributeError: {e}")

    silent = module_from(edit(PRISTINE_SOURCE, *PLAN_GETATTR))
    ns2 = rename_plan_scenes(silent)
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            rc = silent.cmd_plan(ns2)
        add(rc == 0, "BEHAVIOUR", "renamed dest, getattr form",
            f"returned {rc} with NO exception - this is the defect: the runtime cannot "
            f"see a moved dest through a string with a default")
    except Exception as e:                              # noqa: BLE001
        add(False, "BEHAVIOUR", "renamed dest, getattr form",
            f"raised {type(e).__name__}: {e} - expected silence")

    return out


def main() -> int:
    results = rows()
    for ok, kind, name, detail in results:
        print(f"{'ok ' if ok else 'RED'}  {kind:<9} {name:<44} {detail}")
    bad = sum(1 for ok, *_ in results if not ok)
    print(f"\n{len(results) - bad}/{len(results)} rows as declared")
    if bad:
        print(f"{bad} row(s) did NOT behave as declared - flag_binding.py is not pinned.")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
