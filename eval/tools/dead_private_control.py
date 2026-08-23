#!/usr/bin/env python3
"""Is there a private method in `eval/judge/` that nothing can reach?

WHY THIS EXISTS
---------------
FINDINGS #136. `PlatformerBot._approach` was defined in five of the six commits that ever
touched `eval/judge/bot_platformer.py` and called from none of them. Two conclusions in the
archive rest on repairs made to it: row 5 of the `g4_platformer__unity__t0` chain, and the
sentence that falsified the pit hypothesis for #82 by re-grading and getting a byte-identical
0.793. Against that tree byte-identical was the only obtainable result, because the code the
repair touched never ran.

> **A second copy of a loop and an unreachable copy of a loop are indistinguishable by a score
> diff.** Separating them costs a call counter, or -- offline, before anything is interpreted --
> this census.

`9fc044a` is the commit that published #82. The census below names `_approach` in that tree.
That is the whole claim, and direction 1 runs it.

WHAT THE CENSUS IS
------------------
Every `def _name` (not `__dunder__`) lexically inside a `class` body, minus every name the tree
can reach. A reference is an `ast.Attribute.attr`, an `ast.Name.id`, or a whitespace-delimited
token inside a string constant. Two consequences, both deliberate:

  * **a string mention counts as a use**, so `getattr(self, "_step_once")` and a
    `{"key": "_handler"}` dispatch table do not go dead spuriously (variants `str_getattr`,
    `str_table`);
  * **a comment does not**, because a comment is not in the AST. This is not an oversight --
    it is the property that makes the check fire at all. In every one of the five trees that
    defined it, `_approach` appeared as its own `def` line and as two *comments*. A census that
    read comments would have been green on the tree that published #82.

TWO MODES, AND WHY THE SECOND ONE HAD TO EXIST
----------------------------------------------
`--shallow` is #136's census exactly: a name is live if it is referenced anywhere. It cannot see
a cluster that is dead as a whole, and the repository contained one -- `ArenaBot._corners`,
`_far_corner` and `_turn_corner`, where `_far_corner` is called only by `_turn_corner` and
`_corners` only by the other two. Shallow named one of the three; the other two look live because
their only caller is dead code.

The default is REACHABILITY: live means reachable from a root, where a root is a reference made
from outside any private method's body -- module level, a class body, a public method, a
decorator, a default argument. Then the closure forward through the bodies of live methods. Self
recursion and mutual recursion do not keep anything alive, which is the whole difference.
Direction 3 pins both modes against the real cluster as committed at `03cdb90`.

WHAT IT GETS WRONG, MEASURED RATHER THAN ASSUMED
------------------------------------------------
Direction 4 constructs nine inputs and asserts what the census says about each, including the
two it gets wrong. They are pinned as *what it does*, not hidden:

  * FALSE POSITIVE -- a name assembled at runtime (`getattr(self, "_han" + suffix)`) is reported
    dead. Fail-closed: it costs a reader's minute, it cannot excuse a real one. There is no such
    dispatch in `eval/judge/` today; the three `getattr(` sites there all take a literal or a
    non-private attribute.
  * FALSE NEGATIVE -- a method named only in another method's *docstring* is reported live. This
    is the price of the string rule above, and it is the direction anyone widening the string
    handling must not quietly lose.

A method name defined in two classes is live for both if either is reached. Conservative in the
direction that matters for a gate: it under-reports rather than crying wolf.

THE POPULATION INCLUDES `eval/judge/fixtures/`, WHICH `lint.py` EXCLUDES. That is a deliberate
disagreement, not drift: #136's published figure of 121 private methods at `9fc044a` counts the
fixtures, direction 1b asserts against it, and a census whose population silently differed from
the archive's would make the two numbers incomparable for no gain. The fixtures contribute 0 dead
methods in every tree measured so far.

Usage, from anywhere:
    python3 eval/tools/dead_private_control.py            # the four directions
    python3 eval/tools/dead_private_control.py --census   # just name what is dead in eval/judge/
    python3 eval/tools/dead_private_control.py --census --shallow
    python3 eval/tools/dead_private_control.py --census --root some/other/dir

Exit: 0 every direction measured and green; 1 a direction FAILED; 3 nothing failed but a
direction was NOT CHECKED. Never read 3 as a pass -- a shallow clone with no `9fc044a` reaches
direction 1 and can say nothing about it.
"""
from __future__ import annotations

import argparse
import ast
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parents[1]

#: The tree the census covers. Spelled ONCE; direction 2 asserts it exists before reading a
#: verdict off it, because a correct method aimed at a path that is not there returns a
#: confident clean (AGENTS.md rule 12, #60).
CENSUS_ROOT = "eval/judge"

#: The commit that published #82 and defined `PlatformerBot._approach`. Direction 1's red pin.
#: Read as blobs through `git cat-file`; nothing is checked out and nothing is retyped.
APPROACH_COMMIT = "9fc044a"
APPROACH_METHOD = "_approach"
APPROACH_CLASS = "PlatformerBot"

#: #136's published figure for the same tree, under `--shallow`. Pinned so that a change to the
#: extraction shows up as a disagreement with the archive rather than as a new number.
APPROACH_TREE_METHODS = 121
APPROACH_TREE_DEAD = ("_approach", "_num", "_turn_corner")

#: The last commit containing the `ArenaBot` corner cluster, deleted by task 100. Direction 3
#: uses it as a REAL instance of a cluster that is dead only as a whole -- shallow sees one of
#: the three, reachability sees all three.
CLUSTER_COMMIT = "03cdb90"
CLUSTER = ("_corners", "_far_corner", "_turn_corner")
CLUSTER_SHALLOW = ("_turn_corner",)


# --------------------------------------------------------------------------- the census #

@dataclass
class Method:
    name: str
    cls: str
    where: str
    line: int

    @property
    def qual(self) -> str:
        return f"{self.cls}.{self.name}"

    def __str__(self) -> str:
        return f"{self.qual}  ({self.where}:{self.line})"


@dataclass
class Census:
    methods: list[Method] = field(default_factory=list)
    dead: list[Method] = field(default_factory=list)
    files: int = 0
    unparsed: list[str] = field(default_factory=list)

    @property
    def dead_names(self) -> set[str]:
        return {m.name for m in self.dead}


def _is_private(name: str) -> bool:
    return name.startswith("_") and not name.startswith("__") and name != "_"


def _string_tokens(text: str) -> set[str]:
    """Names a string could be naming. Split on whitespace and on `.` and `(`, so
    `self._x(` in a docstring and a bare `"_step_once"` both land."""
    out: set[str] = set()
    for tok in text.replace("(", " ").replace(")", " ").replace(".", " ").split():
        out.add(tok.strip("`'\",:;!?"))
    return out


def _refs_of(node: ast.AST) -> set[str]:
    """Every name this subtree references, NOT descending into a private method's body."""
    out: set[str] = set()
    _walk_refs(node, out, set())
    return out


def _walk_refs(node: ast.AST, out: set[str], _skip: set[int]) -> None:
    for child in ast.iter_child_nodes(node):
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)) and _is_private(child.name):
            # The def-site itself is not a use. Its decorators, annotations and defaults ARE:
            # they evaluate where the class is built, so they are roots.
            for dec in child.decorator_list:
                _walk_refs_all(dec, out)
            for sub in (child.args, child.returns):
                if sub is not None:
                    _walk_refs_all(sub, out)
            continue
        if isinstance(child, ast.Attribute):
            out.add(child.attr)
        elif isinstance(child, ast.Name):
            out.add(child.id)
        elif isinstance(child, ast.Constant) and isinstance(child.value, str):
            out |= _string_tokens(child.value)
        _walk_refs(child, out, _skip)


def _walk_refs_all(node: ast.AST, out: set[str]) -> None:
    """Every reference in a subtree, private method bodies included."""
    for child in ast.walk(node):
        if isinstance(child, ast.Attribute):
            out.add(child.attr)
        elif isinstance(child, ast.Name):
            out.add(child.id)
        elif isinstance(child, ast.Constant) and isinstance(child.value, str):
            out |= _string_tokens(child.value)


def _body_refs(fn: ast.AST) -> set[str]:
    out: set[str] = set()
    for stmt in fn.body:                                    # type: ignore[attr-defined]
        _walk_refs_all(stmt, out)
    return out


def census(sources: dict[str, str], *, shallow: bool = False) -> Census:
    """`sources` maps a display label to Python source text."""
    c = Census(files=len(sources))
    roots: set[str] = set()
    bodies: dict[str, set[str]] = {}                        # method name -> refs from its body

    for label, text in sorted(sources.items()):
        try:
            tree = ast.parse(text)
        except SyntaxError:
            c.unparsed.append(label)
            continue
        roots |= _refs_of(tree)
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            for item in node.body:
                if not isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                if not _is_private(item.name):
                    continue
                c.methods.append(Method(item.name, node.name, label, item.lineno))
                bodies.setdefault(item.name, set()).update(_body_refs(item))

    if shallow:
        seen = set(roots)
        for refs in bodies.values():
            seen |= refs
        c.dead = [m for m in c.methods if m.name not in seen]
        return c

    live = {n for n in bodies if n in roots}
    while True:
        reach: set[str] = set()
        for n in live:
            reach |= bodies[n]
        new = {n for n in bodies if n not in live and n in reach}
        if not new:
            break
        live |= new
    c.dead = [m for m in c.methods if m.name not in live]
    return c


# ------------------------------------------------------------------------- reading trees #

def _git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(ROOT), *args],
                          capture_output=True, text=True, check=False)


def sources_from_disk(root: Path) -> dict[str, str]:
    return {str(p.relative_to(ROOT)): p.read_text(encoding="utf-8", errors="replace")
            for p in sorted(root.rglob("*.py"))}


def sources_from_commit(sha: str, subdir: str) -> dict[str, str] | None:
    """The `.py` blobs under `subdir` at `sha`. `None` if the commit is not in this clone."""
    if _git("cat-file", "-e", f"{sha}^{{commit}}").returncode != 0:
        return None
    listing = _git("ls-tree", "-r", "--name-only", sha, "--", subdir)
    if listing.returncode != 0:
        return None
    out: dict[str, str] = {}
    for path in listing.stdout.splitlines():
        if not path.endswith(".py"):
            continue
        blob = _git("cat-file", "blob", f"{sha}:{path}")
        if blob.returncode != 0:
            return None
        out[path] = blob.stdout
    return out or None


# ----------------------------------------------------------------------------- variants #

#: (label, source, expected-dead-under-reachability, what the row is asking).
#:
#: Rule 15: red-on-`9fc044a` / green-on-HEAD asks only whether the check CAN fail. These ask
#: whether it can still PASS on an input it mishandles, and TWO OF THEM SAY IT CANNOT. Both are
#: pinned as what the census does, so widening the string rule cannot quietly lose either.
VARIANTS: list[tuple[str, str, tuple[str, ...], str]] = [
    ("plain_live", """
class C:
    def go(self):
        return self._helper()
    def _helper(self):
        return 1
""", (), "the ordinary case -- a called method is live"),

    ("plain_dead", """
class C:
    def go(self):
        return 1
    def _helper(self):
        return 2
""", ("_helper",), "TRUE POSITIVE -- without this row the variant harness is vacuous"),

    ("str_getattr", """
class C:
    def go(self):
        return getattr(self, "_step_once")()
    def _step_once(self):
        return 1
""", (), "a literal string dispatch must NOT go dead (#136's own requirement)"),

    ("str_table", """
class C:
    TABLE = {"tick": "_handler"}
    def go(self, k):
        return getattr(self, self.TABLE[k])()
    def _handler(self):
        return 1
""", (), "a dispatch table of literal names must NOT go dead"),

    ("alias", """
class C:
    def go(self):
        f = self._helper
        return f
    def _helper(self):
        return 1
""", (), "referenced by alias, never called -- must NOT go dead"),

    ("class_body_ref", """
class C:
    def _handler(self):
        return 1
    KEYS = {"a": _handler}
""", (), "referenced from the class body as a bare name -- must NOT go dead"),

    ("self_recursive", """
class C:
    def go(self):
        return 1
    def _loop(self, n):
        return self._loop(n - 1) if n else 0
""", ("_loop",), "its only caller is ITSELF -- shallow calls this live, reachability does not"),

    ("mutual_cluster", """
class C:
    def go(self):
        return 1
    def _a(self):
        return self._b()
    def _b(self):
        return self._a()
""", ("_a", "_b"), "dead only as a WHOLE -- the shape the real corner cluster had"),

    ("runtime_name", """
class C:
    def go(self, suffix):
        return getattr(self, "_han" + suffix)()
    def _handler(self):
        return 1
""", ("_handler",), "KNOWN FALSE POSITIVE -- a name assembled at runtime reads dead. "
                    "Fail-closed: noise, never an excused failure"),

    ("docstring_only", """
class C:
    def go(self):
        '''Superseded by self._helper, which is not called from anywhere.'''
        return 1
    def _helper(self):
        return 2
""", (), "KNOWN FALSE NEGATIVE -- a docstring mention reads as a use. The price of str_getattr"),
]


# --------------------------------------------------------------------------- directions #

class Report:
    def __init__(self) -> None:
        self.rows: list[tuple[str, str, str]] = []

    def ok(self, name: str, detail: str) -> None:
        self.rows.append(("ok", name, detail))

    def fail(self, name: str, detail: str) -> None:
        self.rows.append(("FAILED", name, detail))

    def skip(self, name: str, detail: str) -> None:
        self.rows.append(("NOT CHECKED", name, detail))

    def check(self, name: str, cond: bool, detail: str) -> None:
        (self.ok if cond else self.fail)(name, detail)


def direction_1(r: Report) -> None:
    """RED. The census names `PlatformerBot._approach` in the tree that published #82."""
    src = sources_from_commit(APPROACH_COMMIT, CENSUS_ROOT)
    if src is None:
        r.skip("1 red pin: _approach at " + APPROACH_COMMIT,
               f"{APPROACH_COMMIT} is not in this clone -- nothing can be said about it. "
               f"NOT A PASS")
        return
    c = census(src, shallow=True)
    got = sorted(c.dead_names)
    r.check(f"1a red pin: {APPROACH_CLASS}.{APPROACH_METHOD} dead at {APPROACH_COMMIT}",
            APPROACH_METHOD in c.dead_names,
            f"{len(src)} files, {len(c.methods)} private methods, dead={got}")
    r.check("1b the same tree's whole verdict, against #136's published figure",
            len(c.methods) == APPROACH_TREE_METHODS and tuple(got) == APPROACH_TREE_DEAD,
            f"{len(c.methods)} methods (#136 says {APPROACH_TREE_METHODS}), "
            f"dead={got} (#136 says {list(APPROACH_TREE_DEAD)})")
    hit = [m for m in c.dead if m.name == APPROACH_METHOD]
    r.check("1c and it is the method #136 means, not a namesake",
            any(m.cls == APPROACH_CLASS for m in hit),
            f"{[str(m) for m in hit] or 'no _approach in the census at all'}")


def direction_2(r: Report) -> None:
    """GREEN, and the gate. Nothing in `eval/judge/` is unreachable today."""
    root = ROOT / CENSUS_ROOT
    if not root.is_dir():
        r.skip("2 the gate: eval/judge/ is clean",
               f"{root} does not exist -- a verdict read off a missing path is the #60 defect")
        return
    src = sources_from_disk(root)
    c = census(src)
    r.check("2 the gate: no unreachable private method in " + CENSUS_ROOT,
            not c.dead,
            f"{len(src)} files, {len(c.methods)} private methods, "
            + (f"dead={[str(m) for m in c.dead]}" if c.dead else "0 dead"))
    if c.unparsed:
        r.fail("2b every file parsed", f"unparsed: {c.unparsed}")


def direction_3(r: Report) -> None:
    """The cluster, both modes, on the real tree that last contained it."""
    src = sources_from_commit(CLUSTER_COMMIT, CENSUS_ROOT)
    if src is None:
        r.skip("3 the corner cluster at " + CLUSTER_COMMIT,
               f"{CLUSTER_COMMIT} is not in this clone. NOT A PASS")
        return
    shallow = sorted(n for n in census(src, shallow=True).dead_names if n in CLUSTER)
    deep = sorted(n for n in census(src).dead_names if n in CLUSTER)
    r.check("3a shallow sees only the tip of the cluster",
            tuple(shallow) == CLUSTER_SHALLOW,
            f"shallow names {shallow} of {list(CLUSTER)} -- this is why the mode exists")
    r.check("3b reachability sees the whole cluster",
            tuple(deep) == CLUSTER,
            f"reachability names {deep} of {list(CLUSTER)}")


def direction_4(r: Report) -> None:
    """Rule 15. Nine constructed inputs, including the two the census gets wrong."""
    for label, source, expected, why in VARIANTS:
        for mode in ("shallow", "reach"):
            if mode == "shallow" and label not in ("self_recursive", "mutual_cluster"):
                continue                       # only these two separate the modes
            c = census({f"{label}.py": source}, shallow=(mode == "shallow"))
            got = tuple(sorted(c.dead_names))
            if mode == "shallow":
                r.check(f"4 variant {label} [shallow]", got == (),
                        f"shallow says dead={list(got)}; reachability is what catches it")
                continue
            r.check(f"4 variant {label}", got == tuple(sorted(expected)),
                    f"dead={list(got)}, expected {list(expected)} -- {why}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--census", action="store_true",
                    help="just run the census over --root and name what is dead")
    ap.add_argument("--root", default=CENSUS_ROOT, help=f"default {CENSUS_ROOT}")
    ap.add_argument("--shallow", action="store_true",
                    help="#136's mode: a name referenced anywhere is live")
    args = ap.parse_args()

    if args.census:
        root = (ROOT / args.root).resolve()
        if not root.is_dir():
            print(f"no such directory: {root}", file=sys.stderr)
            return 2
        c = census(sources_from_disk(root), shallow=args.shallow)
        mode = "shallow" if args.shallow else "reachability"
        print(f"{args.root}: {c.files} files, {len(c.methods)} private methods, "
              f"{len(c.dead)} unreachable ({mode})")
        for m in sorted(c.dead, key=lambda m: (m.where, m.line)):
            print(f"  DEAD  {m}")
        if c.unparsed:
            print(f"  unparsed: {c.unparsed}")
        return 1 if c.dead else 0

    r = Report()
    direction_1(r)
    direction_2(r)
    direction_3(r)
    direction_4(r)

    for status, name, detail in r.rows:
        print(f"[{status:>11}] {name}\n              {detail}")
    failed = sum(1 for s, _, _ in r.rows if s == "FAILED")
    skipped = sum(1 for s, _, _ in r.rows if s == "NOT CHECKED")
    print(f"\n{len(r.rows)} measurements, {failed} FAILED, {skipped} NOT CHECKED")
    if failed:
        return 1
    return 3 if skipped else 0


if __name__ == "__main__":
    raise SystemExit(main())
