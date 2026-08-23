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

THE FOURTH DIRECTION: DOES THE GATE REWRITE THE TREE IT IS MEASURING?
---------------------------------------------------------------------
Every direction above points at `just check`, which compiles and never writes. `just
verify` is a different address, and it is the one an agent and the Stop hook actually
run — and all four stacks put `fmt` FIRST in it, an auto-fixer, on purpose (see the
`# Note fmt, not fmt-check` block in every justfile).

So `just verify` is idempotent only on an already-formatted tree, and two of the four
were not one until task 26 repaired them: `crates/game/src/main.rs` under rustfmt and
`tools/no_raise.gd` under gdformat (#106). An agent's very first `verify` therefore
rewrote a file it had never opened, and `git diff HEAD` — the artifact that separates
authored work from template code — carried that hunk into six stored trial diffs. The
contamination was in the comparison, not in the game.

The measurement is the TREE, not the exit code. `_tree_state` hashes everything git
would consider tracked-or-untracked-not-ignored, before and after; any added, removed
or modified path fails the row and is named. The exit code is recorded beside it as a
separate row, because it answers a different question: `fmt` runs first in all four
recipes, so a RED `verify` has still exercised the formatter and the tree measurement
is valid either way.

`just warm` gets the same treatment, because the thing being guarded is the TREE THAT
BECOMES THE TRIAL DIFF and not one recipe (rule 13). Every starter's guide tells an
agent to run `warm` once, and the matrix's Bash allowlist lets it — so a `warm` that
rewrites a tracked file contaminates the diff exactly as `fmt` did. Unity's asset
import writing a `.meta` file, which is tracked, is the case with a name.

A GREEN row here is the same shape as `total=0 passed=0` (rule 1): a formatter that
never ran leaves the tree unchanged too. `just fmt` in the godot starter prints
`SKIP fmt: gdtoolkit is not installed` and exits 0; `pnpm exec prettier` on a tree with
no `node_modules/` fails inside `verify` without touching a file. Both are indis-
tinguishable from "clean" by anything that only looks at the tree.

So the green row is only reported at all once the RED half has run: a MIS-FORMATTING
planted in a real source file, which `verify` MUST rewrite. For rust and godot the
plant is the actual pre-repair text from #106, restored verbatim. If the plant survives
`verify`, the formatter did not run, and the arm is reported **NOT CHECKED** — never as
passing. An unmeasured arm reported green is #61, the flag Unity accepts and ignores.

Usage, from eval/:
    python3 tools/starter_gate_control.py                # every starter, all directions
    python3 tools/starter_gate_control.py --stack godot  # one
    python3 tools/starter_gate_control.py --green-only   # skip every plant, and the
                                                         # verify direction with them
    python3 tools/starter_gate_control.py --skip-verify  # gate directions only

Exit: 0 all directions measured and green; 1 a direction FAILED; 2 bad usage; 3 nothing
failed but an arm was NOT CHECKED. Never read 3 as a pass — a caller that treats any
non-1 status as success is the channel this whole file exists to close.
"""
from __future__ import annotations

import argparse
import hashlib
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

EVAL = Path(__file__).resolve().parent.parent
STARTERS = EVAL / "starters"


def _wholegame():
    """THE HARNESS ITSELF, imported rather than restated.

    A pristine copy must be the copy a trial gets: no build output from the repo tree (or a
    warm cache answers the question instead of the template), and a git baseline commit,
    because `git diff HEAD` against that commit is what every stored submission is. Copying
    by hand here would make this control measure a tree no trial ever gets the moment the
    two drift — a comment promising they match is not a defence (AGENTS.md rule 12), so
    there is only one spelling: `wholegame.prepare`.
    """
    sys.path.insert(0, str(EVAL))
    import wholegame
    return wholegame


#: THE LAUNCH DISCIPLINE IS A PROPERTY OF THE ENVIRONMENT, not of a recipe (#61), and this
#: control runs `just verify`, which renders. `wholegame.py` sets exactly these two before
#: every trial; `starters/_shared/launch.just` defaults both OFF so a human gets the game as
#: written. Nobody is watching this run and it happens on the operator's machine, so the
#: same two are set here, on every subprocess, not only on the ones known to raise today.
TRIAL_ENV = {"STARTER_SILENT_LAUNCH": "1", "STARTER_NO_RAISE": "1"}

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


#: stack -> (relative file, anchor, replacement, what the mis-formatting is).
#:
#: A MIS-FORMATTING that the stack's own `fmt` must undo, applied to a real source file.
#: It is the red half of the verify direction, and it is also the only thing that tells a
#: formatter which ran from one which was never installed: both leave the tree unchanged.
#:
#: WHITESPACE ONLY, in all four. `fmt` is the first dependency of `verify` everywhere, so a
#: plant that changed a token would be reformatted and then fail `lint` or a test, and the
#: row would go red for the wrong reason. Nothing here can alter a parse.
#:
#: rust and godot are the ACTUAL PRE-REPAIR TEXT from #106, restored verbatim from commit
#: 314de44 — the multi-line signature rustfmt collapses, and the blank line gdformat wants
#: before a top-level `func`. ts and unity never carried a defect, so theirs are the same
#: two mechanisms written by hand: spacing prettier normalises, trailing whitespace
#: `tools/fmt.mjs` strips. The anchor must appear EXACTLY ONCE or the row fails (rule 12).
FMT_PLANTS: dict[str, tuple[str, str, str, str]] = {
    "rust": ("crates/game/src/main.rs",
             "fn no_raise_correction(mut windows: Query<&mut Window>, "
             "mut done: Local<bool>) {",
             "fn no_raise_correction(\n"
             "    mut windows: Query<&mut Window>,\n"
             "    mut done: Local<bool>,\n"
             ") {",
             "the pre-#106 multi-line signature rustfmt collapses"),
    "godot": ("tools/no_raise.gd",
              "\n\n\nfunc _ready() -> void:",
              "\n\nfunc _ready() -> void:",
              "the pre-#106 single blank line before a top-level func"),
    "ts": ("src/sim/index.ts",
           "export const ARENA_HALF_WIDTH = 400;",
           "export const ARENA_HALF_WIDTH   =   400;",
           "padded spacing around `=` that prettier collapses"),
    "unity": ("Assets/Sim/Sim.cs",
              "        public const int TICK_HZ = 64;",
              "        public const int TICK_HZ = 64;   ",
              "trailing whitespace that tools/fmt.mjs strips"),
}


def _tree_state(repo: Path) -> dict[str, str]:
    """Every path git would carry, mapped to a content hash.

    `ls-files -c -o --exclude-standard` is tracked plus untracked-not-ignored, i.e. exactly
    what `git add -A` in `wholegame.py` would stage — so build output a starter's own
    .gitignore excludes (target/, node_modules/, Library/, .godot/, .venv/) is out, and it
    is out because THE STARTER says so, not because this file restated the list.

    check=True: an unreadable tree must not be reported as an unchanged one.
    """
    names = subprocess.run(["git", "ls-files", "-c", "-o", "--exclude-standard", "-z"],
                           cwd=repo, capture_output=True, text=True, check=True).stdout
    state: dict[str, str] = {}
    for rel in filter(None, names.split("\0")):
        p = repo / rel
        try:
            state[rel] = hashlib.sha256(p.read_bytes()).hexdigest()
        except (FileNotFoundError, IsADirectoryError, PermissionError) as exc:
            state[rel] = f"<unreadable: {type(exc).__name__}>"
    return state


def _tree_diff(before: dict[str, str], after: dict[str, str]
               ) -> tuple[list[str], list[str], list[str]]:
    """-> (added, removed, modified), each sorted. Empty everywhere means untouched."""
    added = sorted(set(after) - set(before))
    removed = sorted(set(before) - set(after))
    modified = sorted(k for k in set(before) & set(after) if before[k] != after[k])
    return added, removed, modified


def _describe(added: list[str], removed: list[str], modified: list[str],
              limit: int = 6) -> str:
    """Name the files. A count alone cannot be acted on."""
    parts = [f"{tag} {', '.join(names[:limit])}"
             f"{f' (+{len(names) - limit} more)' if len(names) > limit else ''}"
             for tag, names in (("+", added), ("-", removed), ("M", modified)) if names]
    return "; ".join(parts) if parts else "no tracked file changed"


def _run(argv: list[str], cwd: Path, timeout_s: int) -> tuple[int, str]:
    """NO PIPE, and no `|| echo`. The exit code is the measurement (AGENTS.md rule 3).

    check=False for the same reason: this control exists to observe a NON-ZERO exit
    from a deliberately broken starter. `check=True` would raise on exactly the outcome
    the control is looking for.
    """
    try:
        p = subprocess.run(argv, cwd=cwd, capture_output=True, text=True,
                           timeout=timeout_s, check=False, env={**os.environ, **TRIAL_ENV})
    except subprocess.TimeoutExpired:
        return 124, "TIMEOUT"
    out = ((p.stdout or "") + (p.stderr or "")).strip().splitlines()
    return p.returncode, (out[-1][:160] if out else "")


def _pristine(stack: str, into: Path) -> Path:
    dest = into / stack
    _wholegame().prepare(STARTERS / stack, dest)
    return dest


def verify_rows(stack: str, repo: Path, timeout_s: int
                ) -> tuple[list[tuple], list[str]]:
    """Does `just verify` rewrite the pristine tree, and could this notice if it did?

    -> ([row, ...], [not-checked note, ...]).

    THE MEASUREMENT RUNS FIRST AND THE PLANT SECOND, and the order is the whole design.
    The plant is anchored in the file's FORMATTED text, so it is read AFTER `verify` has
    had its chance to normalise. Anchoring it in the tree as found instead would make the
    red half unmeasurable on exactly the tree this direction exists to catch: on the
    pre-#106 godot starter the anchor (two blank lines before `func`) is the very thing
    that is missing, and the tool would have answered NOT CHECKED where the truth is
    FAILED. Measured, not reasoned - it is what the first run of this function did.
    """
    if stack not in FMT_PLANTS:
        return [], [f"{stack}: NOT CHECKED for verify idempotence - no FMT_PLANTS entry, "
                    f"so nothing here can tell a formatter that ran from one that is not "
                    f"installed. Add one; an unchanged tree is not evidence on its own."]
    rel, anchor, replacement, what = FMT_PLANTS[stack]
    target = repo / rel

    # -- GREEN: the pristine tree must survive its own `just verify` byte-for-byte. --
    before = _tree_state(repo)
    t0 = time.monotonic()
    rc_v, tail_v = _run(["just", "verify"], repo, timeout_s)
    green_secs = round(time.monotonic() - t0, 1)
    added, removed, modified = _tree_diff(before, _tree_state(repo))
    green_clean = not (added or removed or modified)
    green_row = (f"{stack}: UNCHANGED by its own `just verify` on a pristine tree",
                 rc_v, green_secs, green_clean, _describe(added, removed, modified))
    # Same invocation as the row above, reported separately because it answers a different
    # question. `fmt` is `verify`'s first dependency in all four stacks, so the tree
    # measurement is valid even when this row is red - a RED verify has still formatted.
    exit_row = (f"{stack}: GREEN on pristine (the same `just verify` must also exit 0)",
                rc_v, green_secs, rc_v == 0, tail_v)

    def unmeasured(why: str) -> tuple[list[tuple], list[str]]:
        """A green that proves nothing is dropped; a red that already fired is kept.

        Fail-closed (rule 7): a tree this DID see change is evidence whatever happens to
        the plant, so that row survives. Only the clean result is withheld, because a
        formatter which never ran leaves the tree clean too - #61's shape exactly.
        """
        keep = [] if green_clean else [green_row]
        return keep, [f"{stack}: NOT CHECKED for verify idempotence - {why}"
                      f"{'' if green_clean else ' (the FAILED row above stands on its own)'}"]

    if not target.exists():
        return unmeasured(f"plant target {rel} does not exist")
    formatted_text = target.read_text()
    if formatted_text.count(anchor) != 1:
        return unmeasured(
            f"anchor found {formatted_text.count(anchor)}x in {rel} after `just verify`, "
            f"expected 1. The substitution addresses nothing (rule 12), so planting it "
            f"would prove the formatter alive without ever having mis-formatted anything.")

    # -- RED: the same command MUST rewrite a mis-formatted file, and only that file. --
    target.write_text(formatted_text.replace(anchor, replacement))
    before = _tree_state(repo)
    t0 = time.monotonic()
    rc_r, tail_r = _run(["just", "verify"], repo, timeout_s)
    red_secs = round(time.monotonic() - t0, 1)
    added_r, removed_r, modified_r = _tree_diff(before, _tree_state(repo))
    restored = target.read_text() == formatted_text
    target.write_text(formatted_text)          # the plant never outlives its own row
    red_ok = modified_r == [rel] and not added_r and not removed_r
    red_row = (f"{stack}: the verify check CAN GO RED - {what} planted in {rel}, "
               f"`just verify` MUST rewrite it", rc_r, red_secs, red_ok,
               _describe(added_r, removed_r, modified_r)
               + ("; restored to the formatted bytes" if restored
                  else "; NOT restored to the formatted bytes")
               + (f"; {tail_r}" if tail_r else ""))
    if not red_ok:
        keep, notes = unmeasured(
            f"`just verify` left the planted mis-formatting in {rel} in place "
            f"({_describe(added_r, removed_r, modified_r)}), so this stack's formatter did "
            f"not run. Install what its `just warm` provides and re-run.")
        return [*keep, red_row], notes
    return [green_row, exit_row, red_row], []


def run_stack(stack: str, tmp: Path, green_only: bool, skip_verify: bool = False,
              warm_timeout_s: int = 1800, gate_timeout_s: int = 1800
              ) -> tuple[list[tuple], list[str], list[str]]:
    """-> ([(direction, exit, seconds, expectation_met, tail)], [not-pinned], [not-checked])
    """
    rows: list[tuple] = []
    unpinned: list[str] = []
    unchecked: list[str] = []
    repo = _pristine(stack, tmp)

    # `warm` is measured on the tree as well as on its exit code, and for the same reason
    # `verify` is: the guarded RESOURCE is the tree that becomes the trial diff, not one
    # recipe (rule 13). An agent runs `just warm` too - every starter's guide says to, and
    # it is in the matrix's Bash allowlist - so anything it rewrites is credited to the
    # author exactly as #106's `fmt` hunk was. Unity's asset import writing a missing
    # `.meta`, which IS tracked, is the concrete case this would catch. Baseline first,
    # THEN warm: taking it afterwards would hide whatever warm did behind the pristine row.
    baseline = _tree_state(repo)
    t0 = time.monotonic()
    rc_w, tail_w = _run(["just", "warm"], repo, warm_timeout_s)
    warm_secs = round(time.monotonic() - t0, 1)
    rows.append((f"{stack}: warm", rc_w, warm_secs, rc_w == 0, tail_w))
    w_added, w_removed, w_modified = _tree_diff(baseline, _tree_state(repo))
    rows.append((f"{stack}: UNCHANGED by its own `just warm` on a pristine tree",
                 rc_w, 0.0, not (w_added or w_removed or w_modified),
                 _describe(w_added, w_removed, w_modified)))

    t0 = time.monotonic()
    rc_g, tail_g = _run(["just", "check"], repo, gate_timeout_s)
    rows.append((f"{stack}: GREEN on pristine (`just check` must exit 0)", rc_g,
                 round(time.monotonic() - t0, 1), rc_g == 0, tail_g))

    # -- fourth direction: does `just verify` rewrite the tree it is measuring? (#106) --
    # It runs here, on a tree still pristine, because everything below deliberately breaks
    # it. `--green-only` skips it: its green half is only meaningful once its red half has
    # run, so there is no cheap version of this direction, only an unmeasured one.
    if green_only or skip_verify:
        unchecked.append(
            f"{stack}: NOT CHECKED for verify idempotence - "
            f"{'--green-only' if green_only else '--skip-verify'} was given. Nothing here "
            f"says whether `just verify` rewrites a file the agent never opened.")
    else:
        v_rows, v_unchecked = verify_rows(stack, repo, gate_timeout_s)
        rows.extend(v_rows)
        unchecked.extend(v_unchecked)

    if green_only:
        return rows, unpinned, unchecked
    if stack not in PLANTS:
        rows.append((f"{stack}: RED NOT PINNED - no plant declared", -1, 0.0, False,
                     "add an entry to PLANTS; a gate nobody proved can fail is not a gate"))
        return rows, unpinned, unchecked

    rel, text = PLANTS[stack]
    target = repo / rel
    if not target.exists():
        rows.append((f"{stack}: RED on a planted error", -1, 0.0, False,
                     f"plant target {rel} does not exist"))
        return rows, unpinned, unchecked
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
        return rows, unpinned, unchecked

    gate_rel, anchor, replacement, what = SCOPE_REPAIRS[stack]
    gate = repo / gate_rel
    gate_src = gate.read_text() if gate.exists() else ""
    if gate_src.count(anchor) != 1:
        rows.append((f"{stack}: SCOPE REPAIR slips past the plant", -1, 0.0, False,
                     f"anchor found {gate_src.count(anchor)}x in {gate_rel}, expected 1 - "
                     f"the substitution addresses nothing, so this row would report the "
                     f"UNREPAIRED gate under the repaired gate's name"))
        return rows, unpinned, unchecked

    target.write_text(pristine_target)                       # un-plant
    gate.write_text(gate_src.replace(anchor, replacement))   # narrow the gate's scope
    target.write_text(pristine_target + text)                # re-plant, same plant
    t0 = time.monotonic()
    rc_s, tail_s = _run(["just", "check"], repo, gate_timeout_s)
    rows.append((f"{stack}: the plant DISCRIMINATES - {gate_rel} edited to {what}, same "
                 f"plant, MUST exit 0", rc_s, round(time.monotonic() - t0, 1),
                 rc_s == 0, tail_s))
    return rows, unpinned, unchecked


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--stack", action="append",
                    help="limit to this starter; repeatable. Default: all of them.")
    ap.add_argument("--green-only", action="store_true",
                    help="only the pristine-is-green direction; skip the plants, and the "
                         "verify direction with them (its green half means nothing "
                         "without its red half).")
    ap.add_argument("--skip-verify", action="store_true",
                    help="gate directions only. The verify-idempotence direction runs "
                         "`just verify` twice per stack, which is the expensive part; "
                         "skipping it reports every arm as NOT CHECKED for it.")
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
    unchecked: list[str] = []
    with tempfile.TemporaryDirectory(prefix="starter-gate-") as td:
        for stack in stacks:
            stack_rows, stack_unpinned, stack_unchecked = run_stack(
                stack, Path(td), a.green_only, a.skip_verify)
            unpinned.extend(stack_unpinned)
            unchecked.extend(stack_unchecked)
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
    print(f"\n{len(stacks)} starter(s), {len(rows)} measurements, {len(bad)} FAILED, "
          f"{len(unchecked)} NOT CHECKED")
    for name, rc, secs, ok, tail in bad:
        print(f"  FAIL {name} (exit {rc}): {tail}")
    if unpinned:
        print(f"\nNOT PINNED IN THE THIRD DIRECTION - {len(unpinned)}, reported, not "
              f"failed:")
        for u in unpinned:
            print(f"  {u}")
    # NOT CHECKED IS NOT A PASS, and it is not a failure of the starter either. It is the
    # tool saying it did not measure this arm, which is the one thing #61 could not say.
    if unchecked:
        print(f"\nNOT CHECKED - {len(unchecked)}. These arms were NOT measured in the "
              f"direction named.\nDo not read the rows above as covering them:")
        for u in unchecked:
            print(f"  {u}")
    if not bad:
        measured = sorted({s for s in stacks
                           if not any(u.startswith(f"{s}:") for u in unchecked)})
        print("\nEvery starter's own gate is green on an untouched copy, and every pinned "
              "gate\nstill reports a planted error. A stack listed as RED NOT PINNED is "
              "measured in one\ndirection only - green there means nothing about whether "
              "it can fail. A stack listed\nas NOT PINNED IN THE THIRD DIRECTION has a "
              "gate that can fail, but nothing proving\nits plant would catch a repair "
              "that narrows the gate's scope instead of fixing it.")
        print(f"\nVerify idempotence - a pristine tree surviving its own `just verify` "
              f"byte for byte -\nis established for: {', '.join(measured) or 'NOTHING'}."
              f" Every other arm is listed above.")
    if bad:
        return 1
    return 3 if unchecked else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
