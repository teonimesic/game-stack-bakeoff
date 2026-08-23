#!/usr/bin/env python3
"""Exercise every command that is run ONCE PER CAMPAIGN, and read its exit code.

WHY THIS EXISTS
---------------
`wholegame.py plan` is the command `PROTOCOL.md` tells you to run before authorising a
matrix. It had been dead since the no-cap regime was adopted — `MAX_BUDGET_USD` became
`None` and `cmd_plan` adds it to a float — and nobody found out, because the way you find
out is by running it, and it is run once per campaign (FINDINGS #56).

That is a whole class, and it is worse than this project's usual failure shape. A
mechanism that reports a false success is at least exercised; a gate that crashes is
caught the instant anyone uses it. The danger is the INTERVAL between the change that
broke it and the next use — here, an entire matrix and the whole subjective-layer
programme.

So the fix is not "remember to run plan". It is to run every member of the class on a
schedule that is not "once per campaign", and to read each exit code.

WHAT IT DOES NOT DO
-------------------
It does not check that the output is CORRECT — only that the command runs and exits 0.
A green here means "the gate is alive", never "the gate passed". `plan` printing a wrong
number is exactly what #56 also produced, and no smoke test catches that; only reading
the number does.

Usage, from eval/:
    python3 tools/precampaign_smoke.py            # every check
    python3 tools/precampaign_smoke.py --list
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
REPO = EVAL.parent


def check_frame_criteria_geometry_safe() -> tuple[int, str]:
    """No frame-derived criterion may depend on capture geometry.

    Submissions choose their own frame size - only one stack's `film` recipe passes an
    explicit resolution - and a portrait well for a falling-block game is a design choice,
    not a defect. So the harness does not normalise geometry; it guarantees that nothing it
    MEASURES varies with it. Densities and file counts survive a resize; raw pixel and
    colour counts do not, which is what #59 caught in a judge.
    """
    sys.path.insert(0, str(EVAL / "judge"))
    import static
    problems = static.assert_frame_criteria_geometry_safe()
    if problems:
        return 1, " | ".join(problems)[:400]
    return 0, (f"{len(static.FRAME_CRITERION_MEASURES)} frame criteria, "
               f"all geometry-invariant")


def check_every_game_verifies_its_end_condition() -> tuple[int, str]:
    """Every game must check that it can END, under whatever name it uses.

    The concept has two spellings: `gameover.triggers` in tetris, arena and platformer,
    and `match.ends` in pong, which is first-to-11 so its end condition is a match WIN.
    Both are correct. But a cross-game audit asking "does every game verify its own end
    condition?" greps for `gameover` and reports a false gap for pong - a mechanical sweep
    stating something untrue, which is #38's shape aimed at criteria instead of docs.

    So each bot DECLARES `end_condition`, and this asserts the declaration exists and
    names a criterion the bot actually has. A sweep reads the attribute; nobody greps.
    """
    sys.path.insert(0, str(EVAL / "judge"))
    import bot_pong, bot_tetris3d, bot_arena, bot_platformer
    bad = []
    seen = []
    for mod in (bot_pong, bot_tetris3d, bot_arena, bot_platformer):
        bot = mod.BOT
        name = type(bot).__name__
        cid = getattr(bot, "end_condition", None)
        if not cid:
            bad.append(f"{name} declares no end_condition")
            continue
        ids = {c for c, _ in bot.criteria}
        if cid not in ids:
            bad.append(f"{name}.end_condition={cid!r} is not one of its criteria")
        seen.append(f"{name}={cid}")
    if bad:
        return 1, " | ".join(bad)[:300]
    return 0, f"{len(seen)} games, each declaring an end-condition criterion"


def check_work_root_agreement() -> tuple[int, str]:
    """`runstat.WORK_ROOT` must be the SAME PATH as `wholegame.DEFAULT_WORK_ROOT`.

    THE DEFECT THIS EXISTS FOR, and it is the sharpest one this project has produced.

    The work root moved from `$TMPDIR` to `~/game-research-work` so that the artifact under
    measurement would outlive the measurement (#45). `tools/runstat.py` kept the old
    spelling. Its glob then matched **zero** directories and it printed

        work trees: no writes in last 10 min

    through an entire g4 build in which the agents wrote **2555 files in ten minutes**. The
    sentence is a statement about the glob and reads as a statement about the agents, and
    "found no trees" and "found trees, nothing moved" were the same sentence - fail-open, in
    the tool `AGENTS.md` designates as the only correct status check (#60).

    `runstat` carries "-mmin, never -newermt" and obeys it. **A correct method pointed at the
    wrong place produces a confident answer**, and every rule in this project about HOW to
    check was silent on WHERE.

    A comment is not a defence. This is.
    """
    import importlib.util as ilu
    spec = ilu.spec_from_file_location("_runstat", EVAL / "tools" / "runstat.py")
    rs = ilu.module_from_spec(spec)
    spec.loader.exec_module(rs)
    sys.path.insert(0, str(EVAL))
    import wholegame as wg
    a = Path(rs.WORK_ROOT).resolve()
    b = Path(wg.DEFAULT_WORK_ROOT).resolve()
    if a != b:
        return 1, (f"WORK ROOT MISMATCH: runstat.WORK_ROOT={a} but "
                   f"wholegame.DEFAULT_WORK_ROOT={b} - runstat will glob nothing and report "
                   f"a false quiet signal (#60)")
    return 0, f"runstat.WORK_ROOT == wholegame.DEFAULT_WORK_ROOT == {a}"


def _run(argv: list[str], cwd: Path) -> tuple[int, str]:
    """NO PIPE. A pipeline's exit status is the last stage's, and this file exists
    because an exit code was not read (AGENTS.md rule 3).

    check=False and NOT check=True: the code is the measurement this function returns,
    and every caller reports it per check. Raising would stop the smoke test at the
    first failing check and hide the rest.
    """
    p = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, timeout=900,
                       check=False)
    tail = (p.stdout or p.stderr or "").strip().splitlines()
    return p.returncode, (tail[-1] if tail else "")


def checks(tmp: Path) -> list[tuple[str, list[str], Path]]:
    """(name, argv, cwd). Everything here is run once per campaign or rarer."""
    out: list[tuple[str, list[str], Path]] = []
    # `plan` PER GAME. The break was a config value legal in one branch and illegal in
    # another, so exercising one game would not have found it if only one game had a cap.
    import sys as _s
    _s.path.insert(0, str(EVAL / "suites"))
    import wholegame_prompts as P  # noqa: E402
    for game in sorted(P.TASKS):
        out.append((f"plan {game}",
                    ["python3", "wholegame.py", "plan", "--games", game,
                     "--trials", "2"], EVAL))
    # LIVENESS ONLY, and it must SAY so. This writes to a scratch directory that is
    # deleted when the smoke run ends; it is NOT the launch artifact `PROTOCOL.md`
    # requires at `runs/<run>/prompts`. Both print the same "snapshot: N rendered
    # prompts -> ..." line, and on 2026-08-17 that similarity was enough for a green
    # row here to be read as "the launch snapshot was taken". It had not been, and a
    # snapshot that does not outlive the run cannot do the one job it has: proving
    # after the fact that the regime did not move (#45, #57).
    out.append(("prompt_guard --snapshot [LIVENESS ONLY - scratch, deleted; NOT the "
                "launch artifact]",
                ["python3", "tools/prompt_guard.py", "--snapshot",
                 str(tmp / "prompts-liveness-check-not-the-launch-artifact")], EVAL))
    out.append(("starter_parity",
                ["python3", "judge/starter_parity.py"], EVAL))
    # ~30s, and it is the control for the row above. `starter_parity`'s test axis printed
    # `0/0` for a stack whose toolchain was not installed and the tool still ended on "No
    # drift detected on any measured axis", exit 0 (#108). This runs the axis against a real
    # starter tree with its dependencies present AND with them absent, because only the
    # second direction can ask whether an unmeasured axis still reads as agreement. It needs
    # `starters/ts/node_modules`, and FAILS rather than skips without it - which is also why
    # both rows want a checkout, not an agent worktree.
    out.append(("parity_selftest (test axis: measured, unmeasurable, and opted out)",
                ["python3", "judge/parity_selftest.py"], EVAL))
    # It belongs to this file's class exactly: nothing ever ran a starter's OWN gate on a
    # PRISTINE copy, because the grader only ever runs it on submissions, where red is the
    # answer you are looking for. The godot template shipped `just check` exiting 1 on an
    # untouched tree for four months, handing that one arm build.compiles=False and
    # verify.green=False, both of them tier-1 gate failures and one of them blocking (#98).
    #
    # THE COST ROSE FROM ~160s TO ROUGHLY 15-20 MINUTES on 2026-08-23, because it now also
    # runs `just verify` twice per stack: `verify` is the recipe an agent and the Stop hook
    # actually run, `fmt` is its first dependency in all four stacks, and a starter that is
    # not format-clean therefore has its own gate rewrite a file the agent never opened
    # into the stored trial diff (#106). It is the right place to pay that: this file
    # runs once, immediately before a matrix that costs hours and hundreds of dollars and
    # whose diffs are the artifact the comparison rests on.
    #
    # It exits 3 when nothing failed but an arm could not be measured (a formatter its
    # `just warm` did not install). This file reads anything non-zero as FAILED, which is
    # the wanted behaviour: an unmeasured arm must not read green on the way into a
    # campaign (#61).
    out.append(("starter_gate_control (pristine green + planted red on 4 stacks, the "
                "plant-discriminates row on godot, and `just warm` / `just verify` "
                "leaving each pristine tree unchanged)",
                ["python3", "tools/starter_gate_control.py"], EVAL))
    # verify_blind on COPIES outside the repo: pointed at `starters/` in place it
    # reports RUBRIC REACHABLE from an ancestor, which is true and not the question.
    blind = tmp / "blind"
    blind.mkdir(parents=True, exist_ok=True)
    for s in sorted((EVAL / "starters").iterdir()):
        if s.is_dir():
            shutil.copytree(s, blind / s.name, dirs_exist_ok=True,
                            ignore=shutil.ignore_patterns("node_modules", "target",
                                                          "Library", ".godot", ".venv"))
    out.append(("verify_blind (starters, outside the repo)",
                ["python3", "judge/verify_blind.py",
                 *[str(p) for p in sorted(blind.iterdir())]], EVAL))
    out.append(("audio_selftest", ["python3", "judge/audio_selftest.py"], EVAL))
    # ~10s, and it guards the RECORD rather than a score: the stored capture keeps each
    # stream on its own budget, so a chatty test runner cannot discard the other stream
    # the way nextest discarded every Rust gate's completion line for four matrices
    # (#100). Cheap enough to run before every campaign, and it carries its own mutant.
    out.append(("capture_selftest", ["python3", "judge/capture_selftest.py"], EVAL))
    # The same policy through the other harness's entry point, plus the check that there is
    # only ONE policy: `judge/static.py` imports the sampler from `runner.py` rather than
    # keeping a second copy, and this asserts that every one of those names is still defined
    # in runner.py. Two truncation policies in one repository is how #100 recurred as #114.
    out.append(("runner_capture_selftest",
                ["python3", "runner_capture_selftest.py"], EVAL))
    out.append(("sequential_selftest",
                ["python3", "judge/sequential_selftest.py"], EVAL))
    out.append(("docstat --sweep", ["python3", "tools/docstat.py", "--sweep"], EVAL))
    # The reader of the agents' own closing messages, and its six mutants. Both need the
    # stored corpus: four of the six are caught only by a real message, and the selftest's
    # documented rows come from `runs/`. Run from the main checkout — in a worktree both
    # exit 2 saying the corpus is absent, which is the honest answer and a red row here.
    out.append(("disclosure --selftest (documented rows, both directions)",
                ["python3", "tools/disclosure.py", "--selftest"], EVAL))
    out.append(("disclosure_mutants (6 mutants, 4 caught only by real data)",
                ["python3", "tools/disclosure_mutants.py"], EVAL))
    # Liveness for the frame-parity guard: run it against a run known to be UNIFORM, so a
    # green row means the tool works rather than that some other run is clean.
    out.append(("frame_parity (liveness, on a known-uniform run)",
                ["python3", "tools/frame_parity.py", "--run",
                 "runs/wg-arena3d-2026-08-15T12-46-30"], EVAL))
    return out


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--list", action="store_true", help="name the checks and exit")
    a = ap.parse_args(argv)

    with tempfile.TemporaryDirectory(prefix="precampaign-") as td:
        tmp = Path(td)
        cs = checks(tmp)
        if a.list:
            for name, cmd, _ in cs:
                print(f"{name:44s} {' '.join(cmd)}")
            return 0
        rows, bad = [], []
        # An in-process assertion, not a subprocess: the thing being checked is that two
        # modules agree on a value, which no command-line exit code can express.
        rc, tail = check_work_root_agreement()
        rows.append(("runstat/wholegame work root agree", rc, 0.0, tail[:70]))
        if rc:
            bad.append(("runstat/wholegame work root agree", rc, tail))
        print(f"  {'runstat/wholegame work root agree':44s} exit={rc:<4d}    0.0s  "
              f"{'ok' if rc == 0 else 'FAILED'}", flush=True)
        rc3, tail3 = check_every_game_verifies_its_end_condition()
        rows.append(("every game verifies its end condition", rc3, 0.0, tail3[:70]))
        if rc3:
            bad.append(("every game verifies its end condition", rc3, tail3))
        print(f"  {'every game verifies its end condition':44s} exit={rc3:<4d}    0.0s  "
              f"{'ok' if rc3 == 0 else 'FAILED'}", flush=True)
        rc2, tail2 = check_frame_criteria_geometry_safe()
        rows.append(("frame criteria geometry-invariant", rc2, 0.0, tail2[:70]))
        if rc2:
            bad.append(("frame criteria geometry-invariant", rc2, tail2))
        print(f"  {'frame criteria geometry-invariant':44s} exit={rc2:<4d}    0.0s  "
              f"{'ok' if rc2 == 0 else 'FAILED'}", flush=True)
        for name, cmd, cwd in cs:
            t0 = time.monotonic()
            try:
                rc, tail = _run(cmd, cwd)
            except subprocess.TimeoutExpired:
                rc, tail = 124, "TIMEOUT"
            rows.append((name, rc, round(time.monotonic() - t0, 1), tail[:70]))
            if rc != 0:
                bad.append((name, rc, tail))
            print(f"  {name:44s} exit={rc:<4d} {rows[-1][2]:>6.1f}s  "
                  f"{'ok' if rc == 0 else 'FAILED'}", flush=True)

    w = max(len(r[0]) for r in rows)
    print(f"\n{'check':<{w}}  exit   secs  last line")
    print("-" * (w + 40))
    for name, rc, secs, tail in rows:
        print(f"{name:<{w}}  {rc:<4d} {secs:>6.1f}  {tail}")
    print(f"\n{len(rows)} once-per-campaign commands exercised, {len(bad)} FAILED")
    for name, rc, tail in bad:
        print(f"  FAIL {name} (exit {rc}): {tail}")
    print("\nA green row means the gate is ALIVE, never that it PASSED. `plan` printing a "
          "wrong\nnumber is what #56 also produced, and only reading the number catches that.")
    print("\nNOTHING HERE IS A LAUNCH ARTIFACT. Every path above is scratch and is now "
          "deleted.\nThe prompt snapshot a run needs lives at `runs/<run>/prompts` and is "
          "taken at launch;\nif you are about to build a matrix, take it there and diff "
          "against it afterwards.")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
