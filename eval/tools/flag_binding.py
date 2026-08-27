#!/usr/bin/env python3
"""Assert that every parsed flag `wholegame.py` reads is one its parser really produces.

WHAT IT PROTECTS
----------------
A command line binds the parser to the code by a **name**, and a name is not checked by
anything. `--harness` is a recorded arm dimension (`eval/RUNS.md`): if its `dest` moves and
`cmd_build` still reads the old one, the run does not crash and does not warn - it completes,
and the harness written into its manifest is the default rather than the one asked for. A
completed run whose recorded arm is wrong is the failure this project holds to be worse than
a crash.

Direct attribute access is the first half of the defence: `a.harness` raises AttributeError
where `getattr(a, "harness", None)` returned the default. This tool is the second half, and
it is the half that acts before a launch rather than during one:

    python3 eval/tools/flag_binding.py

WHAT IT CHECKS
--------------
  BIND        every `a.<name>` a command function reads is a dest the subparser that
              dispatches to it produces. Reads inside a function the command hands the same
              namespace to are checked under the CALLER's subparser as well.
  BY-STRING   no command function reaches the namespace through `getattr`, `setattr`,
              `hasattr`, `delattr` or `vars`. Those are the forms that bind by a string
              literal, which is the address a rename moves out from under - and with a
              default argument they do it silently.
  DISPATCH    `wholegame.DISPATCH` and the parser's subcommands are the same set. A third
              hand-kept name list, so it gets the same treatment.
  DELEGATES   every call that passes the namespace on is declared in `wholegame.DELEGATES_TO`.
              An undeclared edge would let a read escape the BIND rows entirely.
  SELFTEST    the dests derived from the parser's structure agree with `vars()` of a
              namespace it actually parsed. The derivation reads argparse internals, so it
              is proved against one case whose answer is known in advance before any row
              above is believed (AGENTS.md rule 12).

`tools/flag_binding_control.py` pins it in both directions.
"""
from __future__ import annotations

import argparse
import ast
import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
WHOLEGAME = HERE.parent / "wholegame.py"

#: The builtins that reach an attribute through a string rather than a name. Closed class:
#: these are every builtin that takes the attribute as a value, plus `vars`, which hands out
#: the whole `__dict__` and makes any read through it invisible to this tool.
BY_STRING = ("getattr", "setattr", "hasattr", "delattr", "vars")


def load_wholegame():
    """Import `wholegame.py` by path. `eval/` is not a package."""
    spec = importlib.util.spec_from_file_location("_flagbind_wholegame", WHOLEGAME)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def subcommand_dests(parser: argparse.ArgumentParser) -> dict[str, set[str]]:
    """Subcommand -> every attribute name a parse of it puts on the namespace.

    Reads `_actions` and `_SubParsersAction`, which are argparse internals. The SELFTEST
    row below compares the result against a namespace argparse actually produced.
    """
    subs = [a for a in parser._actions if isinstance(a, argparse._SubParsersAction)]
    if len(subs) != 1:
        raise SystemExit(f"expected exactly 1 subparsers action, found {len(subs)}")

    def lands(p: argparse.ArgumentParser) -> set[str]:
        # BOTH conditions, and the SELFTEST row is what established the second one:
        # `-h` has `dest="help"` and `default=SUPPRESS`, so argparse never puts it on the
        # namespace. Filtering on the dest alone over-reports by exactly that name.
        return {a.dest for a in p._actions
                if a.dest != argparse.SUPPRESS and a.default is not argparse.SUPPRESS}

    top = lands(parser)
    return {name: top | lands(sp) for name, sp in subs[0].choices.items()}


class _Reads(ast.NodeVisitor):
    """Attribute reads on one name, and every by-string reach for it."""

    def __init__(self, param: str) -> None:
        self.param = param
        self.attrs: set[str] = set()
        self.by_string: list[tuple[int, str]] = []
        self.passes_to: set[str] = set()

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if isinstance(node.value, ast.Name) and node.value.id == self.param:
            self.attrs.add(node.attr)
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        if isinstance(node.func, ast.Name):
            takes_param = any(
                isinstance(x, ast.Name) and x.id == self.param for x in node.args)
            if node.func.id in BY_STRING and takes_param:
                self.by_string.append((node.lineno, node.func.id))
            elif takes_param:
                self.passes_to.add(node.func.id)
        self.generic_visit(node)


def analyse(source: str) -> dict[str, _Reads]:
    """Function name -> what it does with its first parameter."""
    tree = ast.parse(source)
    out = {}
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.args.args:
            r = _Reads(node.args.args[0].arg)
            for stmt in node.body:
                r.visit(stmt)
            out[node.name] = r
    return out


def check(source: str | None = None, mod=None) -> tuple[int, list[str]]:
    """(failures, rows). `source` and `mod` override the shipped file, for the control."""
    mod = mod or load_wholegame()
    source = WHOLEGAME.read_text() if source is None else source
    funcs = analyse(source)
    dests = subcommand_dests(mod.build_parser())
    rows: list[str] = []
    bad = 0

    def row(ok: bool, tag: str, text: str) -> None:
        nonlocal bad
        if not ok:
            bad += 1
        rows.append(f"{'ok ' if ok else 'RED'}  {tag:<9} {text}")

    # SELFTEST FIRST: nothing below is worth reading if the derivation is wrong. `plan` is
    # the one subcommand with no required flags, so it can be parsed with no argument to
    # invent - which is what makes it the row whose answer is known in advance.
    parsed = set(vars(mod.build_parser().parse_args(["plan"])))
    row(parsed == dests.get("plan"), "SELFTEST",
        f"derived dests for 'plan' == vars() of a parsed namespace ({len(parsed)} names)"
        + ("" if parsed == dests.get("plan") else
           f"; derived-only={sorted(dests.get('plan', set()) - parsed)} "
           f"parsed-only={sorted(parsed - dests.get('plan', set()))}"))

    named = {name: fn.__name__ for name, fn in mod.DISPATCH.items()}
    row(set(named) == set(dests), "DISPATCH",
        f"DISPATCH covers exactly the parser's {len(dests)} subcommands"
        + ("" if set(named) == set(dests) else
           f"; dispatch-only={sorted(set(named) - set(dests))} "
           f"parser-only={sorted(set(dests) - set(named))}"))

    declared = set(mod.DELEGATES_TO.items())
    found = {(fname, callee)
             for fname in named.values()
             for callee in funcs.get(fname, _Reads("")).passes_to
             if callee in funcs}
    row(found <= declared, "DELEGATES",
        f"{len(found)} namespace-passing call(s) between command functions, all declared"
        + ("" if found <= declared else f"; undeclared={sorted(found - declared)}"))

    for sub in sorted(dests):
        fname = named.get(sub)
        if fname is None or fname not in funcs:
            continue
        chain = [fname]
        while chain[-1] in mod.DELEGATES_TO:
            nxt = mod.DELEGATES_TO[chain[-1]]
            if nxt in chain:
                break
            chain.append(nxt)
        reads: set[str] = set()
        strings: list[str] = []
        for f in chain:
            r = funcs.get(f)
            if r is None:
                continue
            reads |= r.attrs
            strings += [f"{f}:{ln} {call}()" for ln, call in r.by_string]
        unbound = sorted(reads - dests[sub])
        row(not unbound, "BIND",
            f"{sub} -> {' -> '.join(chain)}: {len(reads)} read(s) all bound"
            + ("" if not unbound else f"; UNBOUND {unbound}"))
        row(not strings, "BY-STRING",
            f"{sub} -> {' -> '.join(chain)}: no by-string reach for the namespace"
            + ("" if not strings else f"; {strings}"))

    return bad, rows


def main() -> int:
    bad, rows = check()
    print("\n".join(rows))
    print(f"\n{len(rows) - bad}/{len(rows)} rows green")
    if bad:
        print(f"\n{bad} RED. A flag's dest and the code that reads it have parted; a "
              f"launch would take the default and record it as the arm.")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
