#!/usr/bin/env python3
"""Is each starter's OWN gate green on a pristine copy — and can it still go red?

WHY THIS EXISTS
---------------
`build.compiles` and `verify.green` are two of the fourteen tier-1 criteria, and both are
just the exit code of a recipe in the submission's own justfile (`judge/static.py`). So a
starter whose gate is RED BEFORE ANY AGENT TOUCHES IT hands every submission in that arm
two automatic failures in the tier weighted 0.31 — and the other three arms do not pay it.
That is not noise. It is one-arm bias, the shape of #25 and #49.

It happened. `eval/starters/godot/tools/check.gd` called `script.reload()` on every script,
`tools/no_raise.gd` is an `[autoload]` and therefore already instantiated, and Godot refuses
to reload a script with a live instance. `just check` exited 1 on the untouched template,
reporting `CHECK scripts=18 failures=1` for a file that compiles perfectly (#98).

Nothing in the harness ever ran a starter's gate on a pristine copy. The grader runs it on
SUBMISSIONS, where a red result is the answer you are looking for. The two Godot agents who
met it repaired the template themselves and said so in `agent.final_text`, which nothing
reads. So the defect was invisible to every mechanism the project had.

BOTH DIRECTIONS, AND WHY THE SECOND ONE IS NOT OPTIONAL
------------------------------------------------------
A gate that stops failing is worse than a gate that fails wrongly: it is indistinguishable
from a passing submission. The obvious repair for the Godot defect — skip instantiated
scripts — makes `just check` green by no longer checking the files the engine loads first.
One of the two agents shipped exactly that.

So each stack declares a PLANT: an edit that the gate MUST report. GREEN alone is a mutant's
answer ("can it fail?"); the plant is the variant ("can it still pass, on an input of the
shape it mishandled?") — AGENTS.md rule 15. Godot's plant goes into the AUTOLOADED script on
purpose, because that is the exact input the old loop got wrong.

A stack with no plant is printed as `RED NOT PINNED`, loudly, rather than omitted. Missing
coverage that looks like coverage is what this whole file is about.

THE THIRD DIRECTION: DOES THE PLANT TELL THE TWO REPAIRS APART?
--------------------------------------------------------------
The two directions above pin the GATE. They say nothing about whether the plant sits at an
address a bad repair can move out of scope — and that is the property the starters' own
`AGENTS.md` now asks a building agent for: *a repair must leave the check able to fail; fix
how the check handles the input it got wrong, do not take that input out of what the check
looks at.*

So a stack may also declare a SCOPE REPAIR: a one-anchor edit to the gate's own source that
narrows what it looks at instead of fixing how it looks. The tool applies it to a pristine
copy, re-applies the SAME plant, and requires `just check` to **exit 0**. That is not the
tool going green on a broken gate — it is the tool proving that the RED row above would have
reported FAILED had a submission shipped that repair. If this row went red instead, the plant
would not discriminate and the RED row would be measuring something weaker than it claims.

**It is pinned on godot only, and that is a property of the gates, not an oversight.** A
scope-narrowing repair needs a gate that carries a list of what to look at. `godot`'s
`tools/check.gd` is a hand-written per-file loop, which is why #98 happened there. The other
three `check` recipes are compilers over a dependency graph — `cargo check --workspace`,
`tsc --noEmit`, `tools/unity-compile.sh` — and every plant sits in a crate/module root that
everything else imports, so there is no per-file scope to narrow at that address. Stacks with
no scope repair are printed under NOT PINNED IN THE THIRD DIRECTION and do **not** fail the
run; extending them means planting a *boundary-guard* violation and adding an ignore entry,
which is a different plant, not a different flag.

Usage, from eval/:
    python3 tools/starter_gate_control.py                # every starter, all directions
    python3 tools/starter_gate_control.py --stack godot  # one
    python3 tools/starter_gate_control.py --green-only   # skip the plants (faster)
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

EVAL = Path(__file__).resolve().parent.parent
STARTERS = EVAL / "starters"

def _trial_ignore():
    """THE SAME OBJECT `wholegame.prepare()` uses, imported rather than restated.

    A pristine copy must carry no build output from the repo tree, or a warm cache answers
    the question instead of the template. Re-spelling the pattern list here would make this
    control measure a tree no trial ever gets the moment the two drift — a comment promising
    they match is not a defence (AGENTS.md rule 12), so there is only one spelling.
    """
    sys.path.insert(0, str(EVAL))
    import wholegame
    return wholegame.IGNORE

#: stack -> (relative file, text appended to make the gate fail).
#:
#: The plant must be a PARSE/COMPILE error, not a failing test: `just check` is a
#: compile-and-boundary gate in every stack, and a test failure would exercise a different
#: recipe. Each is a syntax error in a file the gate claims to cover.
PLANTS: dict[str, tuple[str, str]] = {
    # DELIBERATELY the autoload. `tools/no_raise.gd` is declared under `[autoload]` in
    # project.godot, so the engine has instantiated it before `check.gd` runs — the one
    # input the old `reload()` loop could not tell apart from a parse error (#98).
    "godot": ("tools/no_raise.gd",
              "\n\nfunc _planted_parse_error() -> void:\n\tvar broken = = 1\n"),
    "rust": ("crates/sim/src/lib.rs",
             "\n\npub fn planted_parse_error( -> { }\n"),
    "ts": ("src/sim/index.ts",
           "\n\nexport function plantedParseError(: {\n"),
    "unity": ("Assets/Sim/Sim.cs",
              "\n\npublic class PlantedParseError { void M( { } }\n"),
}

#: stack -> (gate source file, anchor text, replacement, what the repair does).
#:
#: A SCOPE-NARROWING repair of the gate itself, applied on top of the plant. The anchor
#: must appear EXACTLY ONCE or the row fails: the address is an input to the check
#: (AGENTS.md rule 12), and a substitution that silently matched nothing would make this
#: row report the unrepaired gate under the repaired gate's name.
#:
#: Godot's is `wg-g4c` t1's actual shipped repair, reduced to its mechanism: stop
#: re-parsing the autoloaded script rather than re-parse it correctly. `ResourceLoader.load`
#: returns the cached resource, so the `script == null` arm never fires either and the gate
#: goes green over an unparseable autoload (#98).
SCOPE_REPAIRS: dict[str, tuple[str, str, str, str]] = {
    "godot": ("tools/check.gd",
              "\t\tif path == SELF:\n\t\t\tcontinue\n",
              "\t\tif path == SELF or path == \"res://tools/no_raise.gd\":\n"
              "\t\t\tcontinue\n",
              "skip the autoloaded script instead of re-parsing it"),
}


def _run(argv: list[str], cwd: Path, timeout_s: int) -> tuple[int, str]:
    """NO PIPE, and no `|| echo`. The exit code is the measurement (AGENTS.md rule 3).

    check=False for the same reason: this control exists to observe a NON-ZERO exit
    from a deliberately broken starter. `check=True` would raise on exactly the outcome
    the control is looking for.
    """
    try:
        p = subprocess.run(argv, cwd=cwd, capture_output=True, text=True,
                           timeout=timeout_s, check=False)
    except subprocess.TimeoutExpired:
        return 124, "TIMEOUT"
    out = ((p.stdout or "") + (p.stderr or "")).strip().splitlines()
    return p.returncode, (out[-1][:160] if out else "")


def _pristine(stack: str, into: Path) -> Path:
    dest = into / stack
    shutil.copytree(STARTERS / stack, dest, ignore=_trial_ignore())
    return dest


def run_stack(stack: str, tmp: Path, green_only: bool,
              warm_timeout_s: int = 1800, gate_timeout_s: int = 1800
              ) -> tuple[list[tuple], list[str]]:
    """-> ([(direction, exit, seconds, expectation_met, tail)], [not-pinned note, ...])"""
    rows: list[tuple] = []
    unpinned: list[str] = []
    repo = _pristine(stack, tmp)

    t0 = time.monotonic()
    rc_w, tail_w = _run(["just", "warm"], repo, warm_timeout_s)
    rows.append((f"{stack}: warm", rc_w, round(time.monotonic() - t0, 1),
                 rc_w == 0, tail_w))

    t0 = time.monotonic()
    rc_g, tail_g = _run(["just", "check"], repo, gate_timeout_s)
    rows.append((f"{stack}: GREEN on pristine (`just check` must exit 0)", rc_g,
                 round(time.monotonic() - t0, 1), rc_g == 0, tail_g))

    if green_only:
        return rows, unpinned
    if stack not in PLANTS:
        rows.append((f"{stack}: RED NOT PINNED - no plant declared", -1, 0.0, False,
                     "add an entry to PLANTS; a gate nobody proved can fail is not a gate"))
        return rows, unpinned

    rel, text = PLANTS[stack]
    target = repo / rel
    if not target.exists():
        rows.append((f"{stack}: RED on a planted error", -1, 0.0, False,
                     f"plant target {rel} does not exist"))
        return rows, unpinned
    pristine_target = target.read_text()
    target.write_text(pristine_target + text)
    t0 = time.monotonic()
    rc_r, tail_r = _run(["just", "check"], repo, gate_timeout_s)
    rows.append((f"{stack}: RED on a planted error in {rel} (must NOT exit 0)", rc_r,
                 round(time.monotonic() - t0, 1), rc_r != 0, tail_r))

    # -- third direction: can the plant tell a safe repair from a scope-narrowing one? --
    if stack not in SCOPE_REPAIRS:
        unpinned.append(
            f"{stack}: NOT PINNED IN THE THIRD DIRECTION - no SCOPE_REPAIRS entry. This "
            f"stack's gate is proved able to fail, and nothing here shows its plant would "
            f"still catch a repair that narrows the gate's scope instead of fixing how it "
            f"reads its input. The module docstring says why only godot has one and what "
            f"pinning another would take.")
        return rows, unpinned

    gate_rel, anchor, replacement, what = SCOPE_REPAIRS[stack]
    gate = repo / gate_rel
    gate_src = gate.read_text() if gate.exists() else ""
    if gate_src.count(anchor) != 1:
        rows.append((f"{stack}: SCOPE REPAIR slips past the plant", -1, 0.0, False,
                     f"anchor found {gate_src.count(anchor)}x in {gate_rel}, expected 1 - "
                     f"the substitution addresses nothing, so this row would report the "
                     f"UNREPAIRED gate under the repaired gate's name"))
        return rows, unpinned

    target.write_text(pristine_target)                       # un-plant
    gate.write_text(gate_src.replace(anchor, replacement))   # narrow the gate's scope
    target.write_text(pristine_target + text)                # re-plant, same plant
    t0 = time.monotonic()
    rc_s, tail_s = _run(["just", "check"], repo, gate_timeout_s)
    rows.append((f"{stack}: the plant DISCRIMINATES - {gate_rel} edited to {what}, same "
                 f"plant, MUST exit 0", rc_s, round(time.monotonic() - t0, 1),
                 rc_s == 0, tail_s))
    return rows, unpinned


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--stack", action="append",
                    help="limit to this starter; repeatable. Default: all of them.")
    ap.add_argument("--green-only", action="store_true",
                    help="only the pristine-is-green direction; skip the plants.")
    a = ap.parse_args(argv)

    available = sorted(p.name for p in STARTERS.iterdir()
                       if p.is_dir() and (p / "justfile").exists())
    stacks = a.stack or available
    unknown = [s for s in stacks if s not in available]
    if unknown:
        print(f"no such starter: {unknown}; have {available}", file=sys.stderr)
        return 2

    rows: list[tuple] = []
    unpinned: list[str] = []
    with tempfile.TemporaryDirectory(prefix="starter-gate-") as td:
        for stack in stacks:
            stack_rows, stack_unpinned = run_stack(stack, Path(td), a.green_only)
            unpinned.extend(stack_unpinned)
            for row in stack_rows:
                rows.append(row)
                name, rc, secs, ok, tail = row
                print(f"  {name:64s} exit={rc:<4d} {secs:>6.1f}s  "
                      f"{'ok' if ok else 'FAILED'}", flush=True)

    bad = [r for r in rows if not r[3]]
    w = max(len(r[0]) for r in rows)
    print(f"\n{'direction':<{w}}  exit   secs  last line")
    print("-" * (w + 40))
    for name, rc, secs, ok, tail in rows:
        print(f"{name:<{w}}  {rc:<4d} {secs:>6.1f}  {tail}")
    print(f"\n{len(stacks)} starter(s), {len(rows)} measurements, {len(bad)} FAILED")
    for name, rc, secs, ok, tail in bad:
        print(f"  FAIL {name} (exit {rc}): {tail}")
    if unpinned:
        print(f"\nNOT PINNED IN THE THIRD DIRECTION - {len(unpinned)}, reported, not "
              f"failed:")
        for u in unpinned:
            print(f"  {u}")
    if not bad:
        print("\nEvery starter's own gate is green on an untouched copy, and every pinned "
              "gate\nstill reports a planted error. A stack listed as RED NOT PINNED is "
              "measured in one\ndirection only - green there means nothing about whether "
              "it can fail. A stack listed\nas NOT PINNED IN THE THIRD DIRECTION has a "
              "gate that can fail, but nothing proving\nits plant would catch a repair "
              "that narrows the gate's scope instead of fixing it.")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
