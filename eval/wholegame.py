#!/usr/bin/env python3
"""Harness for the whole-game bake-off.

    ./wholegame.py plan     --trials 2                      # matrix + cost estimate
    ./wholegame.py build    --run-dir runs/wg-<stamp> --trials 2 [--parallel 4]
    ./wholegame.py evaluate --run-dir runs/wg-<stamp> [--eval-parallel 1]
    ./wholegame.py report   --run-dir runs/wg-<stamp>
    ./wholegame.py concurrency-check --submission <dir> --starter <dir> --game g1_pong

Two things here are different from `runner.py`, and both are deliberate.

1. TRIAL TREES LIVE OUTSIDE THE REPOSITORY. `runner.py` puts them in `eval/runs/`,
   whose ancestors include `eval/judge/` - so an agent that ran `cat ../../judge/*`
   would read the rubric. The default `--work-root` is therefore a directory under
   $TMPDIR with no eval material anywhere above it, and `judge/verify_blind.py` checks
   every ancestor to the filesystem root.

2. CONCURRENCY IS SPLIT BY PHASE. The build phase (agent sessions) runs in parallel;
   the evaluation phase, which renders, defaults to serial. The reasons are measured,
   not theoretical:
     * Cargo file-locks a target directory. Two trials sharing one blocked on each
       other badly enough that both agents gave up while reporting completion. Every
       trial gets its own copy-on-write clone of a warm target dir.
     * Bevy's own render tests are forced single-threaded because concurrent render
       Apps in one process produce flaky empty frames. Across processes this is
       untested, so it is not assumed safe.
     * Godot renders windowed - N parallel Godot trials open N real windows.
     * Unity needs a graphics device, and two Unity processes on one project corrupt
       the asset database. Separate project copies avoid that, but the per-stack cap
       stays low.
   `concurrency-check` exists to test the assumption rather than trust it: it evaluates
   the same submission serially and in parallel and diffs the per-criterion verdicts.
   If they differ, parallelism is not a speedup, it is a confound.
"""

from __future__ import annotations

import argparse
import concurrent.futures as futures
import datetime as dt
import json
import os
import shutil
import statistics
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
# HERE itself, so `agent_harness` resolves when this module is imported by a tool rather
# than run as a script - sys.path[0] is the CALLER's directory then, not this one.
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "suites"))
sys.path.insert(0, str(HERE / "judge"))
sys.path.insert(0, str(HERE / "tools"))

import tokenvalue  # noqa: E402

import agent_harness  # noqa: E402
import wholegame_prompts as P  # noqa: E402
import scene_prompts as SP  # noqa: E402
import aspects  # noqa: E402
import disclosure as _disclosure  # noqa: E402

STARTERS = {s: HERE / "starters" / s for s in P.STACKS}

#: EVERY TASK THIS HARNESS CAN RENDER A PROMPT FOR - both classes, one lookup.
#:
#: It is NOT what `--games` defaults to, and the two must not be conflated: see
#: `select_tasks()` for the default and the reason it stops here.
ALL_TASKS = {**P.TASKS, **SP.SCENES}
if len(ALL_TASKS) != len(P.TASKS) + len(SP.SCENES):
    raise SystemExit(
        f"a task id is defined in BOTH eval/suites/wholegame_prompts.py and "
        f"eval/suites/scene_prompts.py: "
        f"{sorted(set(P.TASKS) & set(SP.SCENES))}. Two prompts under one id means the "
        f"stored trial record cannot say which one the agent was sent.")


def select_tasks(games: list[str] | None, scenes: list[str] | None) -> list[str]:
    """The tasks one invocation builds, from `--games` and `--scenes`.

    THE STANDING MATRIX COMMAND DOES NOT LAUNCH SCENES, and this function is where that
    is decided. `--games` defaults to every game; `--scenes` defaults to NONE, so a scene
    is built only when it is named.

    IT IS A SEPARATE FLAG RATHER THAN A WIDER DEFAULT ON PURPOSE. `--games` defaulted to
    every key of the registry it read, so registering a scene in that registry would have
    put it in the standing command by construction - which is exactly why task 133 kept
    scenes out of it and left them unlaunchable. A default is a value somebody can widen
    without noticing; a second flag is a selection nobody makes by accident. A scene trial
    is not a cheap addition to a game run: `eval/SCENES.md` records that scenes and a
    second harness are two variables, and that a scene matrix packed back to back
    forecloses the performance question (#172).

    An EMPTY `--games` is refused, and it is refused BEFORE the scenes are added rather
    than only when the whole selection comes out empty. It used to read as "all", because
    `a.games or list(P.TASKS)` cannot tell `[]` from `None`; a selection the operator
    narrowed to nothing must not silently become the widest one there is, and it must not
    quietly become a paid scene trial either. `--games` with no values buys nothing that
    omitting it does not - omitting it alongside `--scenes` already selects scenes alone -
    so refusing costs one retyped command and accepting launches a trial nobody asked for.
    """
    if games == []:
        raise SystemExit(
            "`--games` was given with no values, which selects nothing. It is refused "
            "rather than read as every game, and rather than left to be filled in by "
            "`--scenes`. Name the games, or omit `--games` entirely - omitting it "
            "alongside `--scenes` already selects the scenes alone.")
    if games is None and not scenes:
        chosen = list(P.TASKS)
    else:
        chosen = list(games or []) + list(scenes or [])
    if not chosen:
        raise SystemExit(
            "no tasks selected. Name the games, name the scenes with `--scenes`, or "
            "pass neither for the standing game matrix.")
    unknown = [t for t in chosen if t not in ALL_TASKS]
    if unknown:
        raise SystemExit(f"unknown task ids: {unknown}. Known: {sorted(ALL_TASKS)}")
    return chosen


# Per-stack caps for the BUILD phase. Rust and TypeScript are headless enough to run
# several at once; Godot opens a real window for its render tests and Unity launches an
# editor per verify, so both stay low.
BUILD_CAP = {"rust": 4, "ts": 4, "godot": 2, "unity": 2}
# The evaluation phase renders. Default serial for everyone until measured otherwise.
EVAL_CAP = {"rust": 1, "ts": 1, "godot": 1, "unity": 1}

# Budget per trial. Whole-game builds are expensive; these are hard stops, and the
# harness records terminal_reason so a truncated trial is never confused with a failure.
# STANDING CONFIGURATION from 2026-08-15 (PROTOCOL.md, DECISIONS.md).
# 250 was the binding limit at a 48-tokval cap - `g3_arena__rust__t1` stopped at 251 turns
# with 12 of its stated budget unused (FINDINGS #35), so the run was governed by the flag the
# agent cannot see while appearing to be governed by the one it can.
MAX_TURNS = 1000
# RAISED FROM 25.0 ON 2026-08-14, and the reason is not only that trials were hitting it.
#
# MEASURED: `--max-budget-usd` is VISIBLE TO THE BUILDING AGENT. Asked "do you have a
# spending limit, state the exact figure", a session launched with 7.31 answers 7.31, one
# launched with 41.77 answers 41.77, and one launched without the flag answers NONE.
# Three-way discrimination, so this is not the model guessing.
#
# The cap is therefore an INPUT to the agent, not an external kill. Runs with different
# caps are not comparable, and the observed clustering just under 25 tokval (23.07, 24.33,
# 24.34, 25.06) is what an agent pacing itself to a budget it was told about looks like -
# not a coincidence of task size. On a subscription account it was pacing itself against a
# constraint that does not exist (#159).
# None means DO NOT PASS THE FLAG, and that is the point rather than a convenience.
# `--max-budget-usd` is VISIBLE TO THE AGENT and instructs it: token usage rose 1.54x on
# Tetris when the stated ceiling went 25 -> 48 (FINDINGS #33). Any stated value is an
# instruction, so there is no neutral number - only an absent flag is neutral. The run is
# bounded by the invisible turn limit instead.
MAX_BUDGET_USD = None

#: THE ONE SPELLING OF THE WORK ROOT. `tools/runstat.py` must resolve to this exact path,
#: and `tools/precampaign_smoke.py` asserts that it does.
#:
#: It was two spellings in two files with nothing tying them together. When the work root
#: moved here from $TMPDIR - a change made to stop the OS deleting the artifact under
#: measurement (#45) - `runstat.py` kept the old one, globbed zero directories, and printed
#: "work trees: no writes in last 10 min" through an entire build in which the agents wrote
#: 2555 files in ten minutes (#60). Import it; do not retype it.
DEFAULT_WORK_ROOT = Path.home() / "game-research-work"
TIMEOUT_S = 14_400  # 4 h

#: WHICH AGENT CLI BUILDS THE TRIALS. `--harness` overrides it for one build.
#:
#: This was a constant spelled into the argv until 2026-08-24, so every result this
#: project holds is a statement about the `claude` arm and nothing said so. It is a
#: recorded arm dimension in `eval/RUNS.md` now, and the two arms are NOT comparable on
#: dollars at all: see `agent_harness.py`.
HARNESS = "claude"

#: The builders' model, defined by the harness rather than beside it - two spellings of
#: one value is how `runstat.py` came to glob a work root that had moved (#60, rule 12).
#: The judge deliberately runs a different model.
MODEL = agent_harness.CLAUDE.model

#: TARGETED ALLOWLIST, user-ruled. Measured across the published 24-trial bake-off: 302
#: denials, 12.6 per trial, 29.8% of all turns lost, and the spread across the four stacks
#: was only 3 percentage points (28.1-31.1%) - a uniform tax rather than a per-stack bias.
#: In the whole-game calibration trial the agent was denied `just verify` itself and signed
#: off saying two checks were unrun, while the repo it left behind passed the gate in 5s.
#:
#: Deliberately NOT bypassPermissions and deliberately not a catch-all: the sandbox stays
#: meaningful, only the build and verification commands the template itself tells the agent
#: to run are permitted.
#:
#: IT HAS NO EQUIVALENT ON THE prime-agent ARM, which filters tool NAMES rather than
#: command patterns and runs arbitrary code through an IPython kernel with nothing to
#: pre-authorise. That is an uncontrolled difference between the arms, recorded in
#: `eval/RUNS.md` rather than papered over.
ALLOWED_TOOLS = ("Bash(just *)", "Bash(cargo *)", "Bash(pnpm *)", "Bash(git *)")


# --------------------------------------------------------------------------- #
# Trial plumbing
# --------------------------------------------------------------------------- #

IGNORE = shutil.ignore_patterns(
    ".git", "target", "node_modules", "dist", "runs", "__pycache__",
    "*.actual.png", "*.expected.png", "*.diff.png", "artifacts", "Library", "Temp",
    ".godot", ".eslintcache", "coverage")


def prepare(starter: Path, dest: Path) -> None:
    if dest.exists():
        shutil.rmtree(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    # NOTE: copytree FOLLOWS symlinks, so .venv/bin/python3.11 becomes a 17 MB copy of
    # the interpreter that cannot find its stdlib. It is never executed: every script in
    # .venv/bin keeps an absolute shebang pointing at the STARTER's working symlink, so
    # the copy is dead weight, not a defect. Do NOT "fix" the shebangs -- rewriting them
    # to point into the work tree aims them at the broken copy. See FINDINGS #43.
    shutil.copytree(starter, dest, ignore=IGNORE)
    subprocess.run(["git", "init", "-q"], cwd=dest, check=True)
    subprocess.run(["git", "add", "-A"], cwd=dest, check=True)
    subprocess.run(["git", "-c", "user.email=eval@local", "-c", "user.name=eval",
                    "commit", "-q", "-m", "starter baseline"], cwd=dest, check=True)


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=repo, capture_output=True,
                          text=True, check=False).stdout


def clone_target(pristine: Path, dest: Path) -> Path | None:
    """APFS copy-on-write clone of a warm cargo target dir: 8.8 GB in ~2.5 s."""
    if not pristine.exists():
        return None
    shutil.rmtree(dest, ignore_errors=True)
    dest.parent.mkdir(parents=True, exist_ok=True)
    for argv in (["cp", "-Rc", str(pristine), str(dest)],
                 ["cp", "-R", str(pristine), str(dest)]):
        # check=False: a failed CoW clone is the trigger for the plain-copy fallback,
        # and both failing means None -> cold build, which is slow but correct. The
        # status is read on this line.
        if subprocess.run(argv, capture_output=True, check=False).returncode == 0:
            return dest
    return None


#: Name of the Stop-hook audit trail, inside the trial's ARTIFACT directory.
#:
#: Every starter wires `.claude/hooks/verify-gate.sh` under `"Stop"`, and a Stop hook that
#: exits 0 leaves no trace in the transcript, in the result JSON or anywhere else -
#: measured at CLI 2.1.220 with these flags. "No block in the transcript" is therefore
#: equally consistent with `just verify` having been green at every stop and with the hook
#: never having run, and no stored artifact separated them. Task 67 recorded the gate as
#: live in all four arms on the strength of the file existing in the starter, which is
#: AGENTS.md rule 2.
#:
#: The hooks now append one `invoked` line and one verdict line per invocation to the path
#: named here. `tools/hook_audit_control.py` pins that in both directions, offline.
HOOK_LOG_NAME = "hook_log.tsv"


def hook_log_path(art: Path, work: Path) -> Path:
    """Where a trial's Stop hook writes, with the one property that matters asserted.

    THE TRIAL TREE BECOMES THE GRADED DIFF. Anything written under `work` lands in
    `files_changed`, `diff.stat`, `tree.txt` and `submission.tar.gz`, which is the shape
    of #106 - a gate that rewrote the tree it was measuring, and six stored diffs carrying
    a hunk no agent authored.

    So the address is checked here rather than promised by a comment (rule 12), and it
    fails the trial rather than degrading quietly: a log inside the tree is not a smaller
    problem than no log, it is a contaminated submission.
    """
    log = (art / HOOK_LOG_NAME).resolve()
    root = work.resolve()
    if log == root or root in log.parents:
        raise SystemExit(
            f"REFUSING TO LAUNCH: the Stop-hook log would be written to {log}, which is "
            f"inside the trial tree {root}. The tree becomes the graded diff (#106).")
    return log


def read_hook_log(p: Path) -> dict[str, Any]:
    """Summarise the audit trail into the trial record.

    THREE VALUES, not two. `absent` (the file was never created - the hook never ran, or
    the CLI never passed the variable through, or the starter predates this) is not
    `present with no invocations`, and neither is "the gate passed". A reader that tests
    for truthiness collapses exactly the distinction this log exists to make.
    """
    if not p.exists():
        return {"log": "absent", "path": str(p), "invocations": 0, "verdicts": {}}
    verdicts: dict[str, int] = {}
    invocations = 0
    malformed = 0
    for ln in p.read_text(errors="replace").splitlines():
        if not ln.strip():
            continue
        parts = ln.split("\t")
        if len(parts) != 4:
            malformed += 1
            continue
        event = parts[2]
        if event == "invoked":
            invocations += 1
        else:
            verdicts[event] = verdicts.get(event, 0) + 1
    return {"log": "present", "path": str(p), "invocations": invocations,
            "verdicts": verdicts, "malformed_lines": malformed}


def run_agent(work: Path, prompt: str, env: dict[str, str],
              turn_limit: int | None = None,
              harness: agent_harness.Harness | None = None) -> tuple[dict, str]:
    """Run one agent session under whichever harness this arm uses.

    Argv, parsing and normalisation live in `agent_harness.py`, one object per CLI. The
    claude arm's argv is unchanged and is pinned byte for byte by
    `tools/agent_harness_control.py`: a changed command line is a changed experiment, and
    it would be invisible in every stored artifact.
    """
    h = harness or agent_harness.get(HARNESS)
    sid = str(uuid.uuid4())
    turns = MAX_TURNS if turn_limit is None else int(turn_limit)
    argv = h.argv(prompt=prompt, turns=turns, session_id=sid, cwd=work,
                  allowed_tools=ALLOWED_TOOLS, budget_usd=MAX_BUDGET_USD)
    # check=False: an agent that stops on its budget or turn ceiling exits non-zero and
    # has still produced a submission worth grading. Raising here would throw away the
    # trial we paid for; the terminal reason comes out of the parsed result instead.
    try:
        p = subprocess.run(argv, cwd=work, capture_output=True, text=True,
                           timeout=TIMEOUT_S, env=env, check=False)
        return h.parse(p.stdout, p.returncode), p.stderr[-4000:]
    except subprocess.TimeoutExpired:
        return h.timeout_record(), ""


# --------------------------------------------------------------------------- #
# Build phase
# --------------------------------------------------------------------------- #


class Caps:
    """Per-stack concurrency limits, enforced with semaphores."""

    def __init__(self, caps: dict[str, int], overall: int):
        self.sem = {k: threading.Semaphore(max(1, v)) for k, v in caps.items()}
        self.overall = threading.Semaphore(max(1, overall))

    def hold(self, stack: str):
        class _Ctx:
            def __enter__(_s):
                self.overall.acquire()
                self.sem[stack].acquire()
                return _s

            def __exit__(_s, *_e):
                self.sem[stack].release()
                self.overall.release()
        return _Ctx()


def build_trial(run_dir: Path, work_root: Path, stack: str, game: str, trial: int,
                caps: Caps, pristine_target: Path | None,
                prompt_override: str | None = None,
                turn_limit: int | None = None,
                harness_name: str | None = None) -> dict[str, Any]:
    h = agent_harness.get(harness_name or HARNESS)
    tid = f"{game}__{stack}__t{trial}"
    # NAMESPACE THE WORK TREE BY RUN. Trial ids repeat across runs (`g1_pong__rust__t0`
    # is the first trial of every run that includes that cell), and `prepare()` starts
    # with `rmtree`. A later run therefore DELETES an earlier run's submission.
    # Measured: launching the 24-trial matrix silently destroyed the calibration
    # trial's work tree, and a variance study pointed at it produced six "empty pack"
    # records instead of six judgings. The empty-pack guard caught it; without that
    # guard it would have produced six confident zeros.
    work = work_root / run_dir.name / tid
    art = run_dir / "artifacts" / tid
    art.mkdir(parents=True, exist_ok=True)
    rec: dict[str, Any] = {"trial_id": tid, "stack": stack, "game": game,
                           # WHICH TASK CLASS, stamped at build time rather than left for
                           # a reader to infer from the id. A scene score is never pooled
                           # with a game score (`eval/SCENES.md`), and every aggregate
                           # downstream partitions on this field.
                           "task_class": aspects.task_class(game),
                           "trial": trial, "work": str(work),
                           "harness": {"name": h.name, "model": h.model,
                                       "supports_stop_hook": h.supports_stop_hook},
                           "started_at": dt.datetime.now(dt.timezone.utc).isoformat()}
    with caps.hold(stack):
        prepare(STARTERS[stack], work)
        env = dict(os.environ)
        if stack == "rust" and pristine_target:
            # KEYED BY RUN, like the work tree above it. `_targets/<tid>` alone
            # collides across matrices: `g1_pong__rust__t0` exists in every one, so two
            # runs shared and overwrote one cargo target directory. This is the same
            # collision that destroyed the calibration submission, surviving in a second
            # place because only the work tree was fixed.
            #
            # It gets WORSE with a durable work root: $TMPDIR was silently cleaning
            # `_targets` between runs, which masked the collision. Removing the reaping
            # removes the accident that hid it.
            #
            # A shared folder is only safe if EVERYTHING under it is namespaced, not
            # just the part that was noticed first.
            td = clone_target(pristine_target,
                              work_root / run_dir.name / "_targets" / tid)
            if td:
                env["CARGO_TARGET_DIR"] = str(td)
                rec["cargo_target_dir"] = str(td)
        # THE TRIAL ENVIRONMENT OWNS THE LAUNCH DISCIPLINE, not the starter's defaults.
        #
        # `starters/_shared/launch.just` defaults both of these OFF, so a human running
        # `just run` gets the game exactly as its author wrote it - it makes sound and it
        # raises. Nobody is watching a trial, and the operator's machine is doing other
        # work, so the harness turns them on here. A Unity player once appeared in the
        # foreground of that machine with audio playing because this was a property of
        # recipes rather than of the environment.
        env["STARTER_SILENT_LAUNCH"] = "1"
        env["STARTER_NO_RAISE"] = "1"

        # THE STOP GATE GETS AN AUDIT TRAIL, and it is addressed OUTSIDE the tree it
        # gates. `hook_log_path` refuses to launch if that ever stops being true.
        _hook_log = hook_log_path(art, work)
        env["STARTER_HOOK_LOG"] = str(_hook_log)

        prompt = (prompt_override if prompt_override is not None
                  else ALL_TASKS[game](stack))
        (art / "prompt.txt").write_text(prompt)
        # WHETHER THIS RECORD IS A SUBMISSION AT ALL. A `--prompt-file` trial carries a
        # `game` field like every other record and was not asked to build that game, so
        # anything counting the game population needs the flag in the record rather than
        # in the operator's memory. The prompt itself is in `artifacts/<tid>/prompt.txt`.
        rec["prompt_override"] = prompt_override is not None

        # THE ISOLATION THIS ARM NEEDS, ASSERTED ON THE PATH THAT HOLDS IT, and its audit
        # trail stored. The claude arm closes the operator's global instructions and MCP
        # servers off with two flags; prime-agent has no equivalent of either and reads
        # context files from every ancestor of the trial tree, so its guard is an
        # assertion over that tree. Recorded per trial rather than reasoned about once:
        # a check that leaves no trace cannot be told afterwards from one that never ran.
        rec["harness"]["isolation"] = h.preflight(work)
        env = agent_harness.env_for(h, env)

        t0 = time.monotonic()
        agent, stderr = run_agent(work, prompt, env, turn_limit, harness=h)
        rec["wall_s"] = round(time.monotonic() - t0, 1)

    # REAP PROCESSES THE AGENT LEFT BEHIND.
    # MEASURED: the Unity starter's `just run` ends in `open build/Starter.app`, which
    # launches the built game and never terminates it. Once `Bash(just *)` was
    # allowlisted, agents could reach that recipe, and every Unity trial leaked a GUI
    # process. Six were found still running, two of them for over sixteen hours -
    # through the entire remainder of the matrix.
    #
    # This matters beyond tidiness: wall clock and cost are COMPARISON METRICS, so a
    # trial that runs on a machine loaded by earlier trials' leftovers is not
    # comparable to one that ran on an idle machine, and the contamination is ordered
    # by build sequence.
    #
    # Fixed in the HARNESS, not the starter: `just run` leaving a window open is
    # reasonable behaviour for a "run the game" recipe, and editing a starter changes
    # the thing being measured. Cleaning up after the agent is the harness's job.
    # check=False: `pkill` exits 1 when it matched nothing, which is the GOOD case here.
    # The status is recorded on the next line rather than dropped.
    reaped = subprocess.run(["pkill", "-9", "-f", str(work)], capture_output=True,
                            check=False)
    rec["reaped_leftover_processes"] = reaped.returncode == 0

    # THE SHARED FIELD NAMES, and the per-harness readers behind them. Every mapping the
    # record depends on - a session limit that reports itself as an api_error, a token
    # count that is cumulative on one harness and per-message on another, a terminal
    # reason with no measured equivalent - is in `agent_harness.py` beside the evidence
    # for it. Read that module before trusting a field across two arms.
    rec["agent"] = h.normalise(agent, stderr)
    # Artifact capture: everything needed to re-judge offline without re-running agents.
    (art / "agent_result.json").write_text(json.dumps(agent, indent=2)[:2_000_000])
    # RE-JUDGEABILITY. `git diff HEAD` alone is NOT enough to reconstruct a submission:
    # it omits untracked files entirely and cannot represent binary changes without
    # --binary. Measured: the calibration trial's patch could not be applied back onto
    # the starter (a deleted golden PNG needed --binary) and was missing a whole test
    # file the agent had created but never staged. The submission was unrecoverable
    # once its work tree was overwritten.
    # Stage everything first so untracked files are included, and ask for binary.
    #
    # check=False on all three, but their EXIT CODES ARE RECORDED. Raising here would
    # abandon the trial record for a build that is already paid for, which is the wrong
    # trade -- but dropping the status silently is worse, and is what happened until
    # 2026-08-23. A failed `git add -A` yields an empty diff.patch and a failed `tar`
    # yields a truncated or absent submission.tar.gz, and BOTH are indistinguishable from
    # "the agent changed nothing" in every artifact stored afterwards. That is the exact
    # unrecoverable-submission failure the comment above this line was written for. The
    # codes go into the trial record so a re-judge can tell an empty submission from a
    # capture that broke.
    _cap: dict[str, int] = {}
    _cap["git_add"] = subprocess.run(["git", "add", "-A"], cwd=work,
                                     capture_output=True, check=False).returncode
    (art / "diff.patch").write_text(
        git(work, "diff", "--cached", "--binary", "HEAD")[:32_000_000])
    (art / "diff.stat").write_text(git(work, "diff", "--cached", "HEAD", "--stat"))
    # Belt and braces: a tarball of the tree itself. A patch can fail to apply; an
    # archive cannot. This is what makes offline re-judging actually possible.
    _cap["tar"] = subprocess.run(
        ["tar", "--exclude=./.git", "--exclude=./target", "--exclude=./node_modules",
         "--exclude=./Library", "--exclude=./Temp", "--exclude=./.godot",
         "--exclude=./.venv", "-czf", str(art / "submission.tar.gz"), "."],
        cwd=work, capture_output=True, check=False).returncode
    (art / "status.txt").write_text(git(work, "status", "--porcelain=v1",
                                        "--untracked-files=all"))
    _find = subprocess.run(
        ["find", ".", "-type", "f", "-not", "-path", "./.git/*",
         "-not", "-path", "./target/*", "-not", "-path", "./node_modules/*",
         "-not", "-path", "./Library/*", "-not", "-path", "./.godot/*"],
        cwd=work, capture_output=True, text=True, check=False)
    _cap["find"] = _find.returncode
    (art / "tree.txt").write_text(_find.stdout)
    rec["capture_exit_codes"] = _cap

    # WHAT THE STOP GATE DID, recorded beside what the agent produced.
    #
    # Three values, and `absent` is one of them: a trial whose log was never created did
    # not run a green gate, it ran an UNKNOWN gate, and that is the state every trial
    # before this change is permanently in.
    rec["stop_hook"] = read_hook_log(_hook_log)
    # A FOURTH THING `absent` CAN MEAN, once the harness is a variable: this CLI has no
    # hooks. The gate is wired in every starter's `.claude/settings.json`, which only the
    # claude CLI reads, so on any other arm `absent` is structural rather than a finding
    # about the trial. Stated at the address the reader is already at.
    rec["stop_hook"]["harness_supports_stop_hook"] = h.supports_stop_hook
    # AND THE CONTROL, run per trial rather than reasoned about once. `hook_log_path`
    # asserts the address before the launch; this asserts the OUTCOME after it, against
    # the same three artifacts a grader reads. They are different questions: a hook is
    # free to write wherever it likes once it is running, and the tree is what gets graded.
    _leak = sorted({ln for ln in _find.stdout.splitlines()
                    if HOOK_LOG_NAME in ln} |
                   {ln for ln in (art / "diff.stat").read_text().splitlines()
                    if HOOK_LOG_NAME in ln})
    rec["stop_hook"]["leaked_into_tree"] = _leak
    if _leak:
        print(f"  [hooklog] {tid} CONTAMINATION: the Stop-hook log is inside the graded "
              f"tree: {_leak}", flush=True)
    if any(v != 0 for v in _cap.values()):
        print(f"  [capture] {tid} NON-ZERO evidence capture: {_cap} — the stored "
              f"submission may be incomplete", flush=True)
    rec["files_changed"] = len([ln for ln in
                                git(work, "status", "--porcelain=v1",
                                    "--untracked-files=all").splitlines() if ln.strip()])
    rec["finished_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
    (run_dir / "trials").mkdir(parents=True, exist_ok=True)
    (run_dir / "trials" / f"{tid}.json").write_text(json.dumps(rec, indent=2))
    # The line carries the HARNESS and the TOKEN counts, not only the valuation: on any
    # arm but claude the valuation is `n/a` by construction (#159 with a second vendor),
    # and a line whose only resource figure is absent says nothing about the trial.
    _a = rec["agent"]
    print(f"  [built] {tid}  {rec['wall_s']}s  {_a['harness']}  "
          f"{tokenvalue.tag(_a['cost_usd'])}  "
          f"in={_a['input_tokens']} out={_a['output_tokens']}  "
          f"turns={_a['num_turns']}  {_a['terminal_reason']}",
          flush=True)
    return rec



def assert_work_root_usable(work_root: Path) -> None:
    """Refuse a work root that breaks blinding or that the OS will erode.

    Asserted at BUILD time only. Grading an existing run must still work against trees
    that were created under the old default, or a repaired re-grade would be impossible.
    """
    wr = work_root.resolve()
    repo = Path(__file__).resolve().parent.parent
    if wr == repo or repo in wr.parents:
        raise SystemExit(
            f"work root {wr} is INSIDE the repository ({repo}).\n"
            f"A trial tree there lets a building agent walk up its ancestors and read\n"
            f"RUBRIC.md. Blinding is verified by ancestor walk, so this is not\n"
            f"theoretical. Choose a path outside the repository.")
    ephemeral = (str(Path(tempfile.gettempdir()).resolve()), "/tmp", "/private/tmp",
                 "/private/var/folders", "/var/folders")
    if any(str(wr) == e or str(wr).startswith(e.rstrip("/") + "/") for e in ephemeral):
        raise SystemExit(
            f"work root {wr} is under a temporary directory the OS reaps.\n"
            f"MEASURED: six submissions lost ~80% of their installed toolchain between\n"
            f"building and grading, and each then scored an identical 6/14 that read as\n"
            f"a stack characteristic (FINDINGS #45). The artifact under measurement must\n"
            f"not live somewhere with a lifetime shorter than the measurement.")


def assert_run_scoped(work_root: Path, run_dir: Path) -> None:
    """Every per-run path must sit under `work_root/<run>/`.

    Trial ids repeat across matrices, so anything keyed by tid alone collides. Checked
    rather than assumed because the work tree was fixed and `_targets` was not, and the
    survivor went unnoticed for four matrices.
    """
    base = (work_root / run_dir.name).resolve()
    for path in (work_root / run_dir.name / "_targets",
                 work_root / run_dir.name / "trial"):
        if base not in path.resolve().parents and path.resolve() != base:
            raise SystemExit(
                f"per-run path {path} is not under {base}. Trial ids repeat across "
                f"runs; anything keyed by trial id alone will be overwritten by the "
                f"next matrix.")

def cmd_build(a: argparse.Namespace) -> int:
    run_dir = a.run_dir.resolve()
    run_dir.mkdir(parents=True, exist_ok=True)
    work_root = a.work_root.resolve()
    assert_work_root_usable(work_root)
    assert_run_scoped(work_root, run_dir)
    work_root.mkdir(parents=True, exist_ok=True)

    stacks = a.stacks or list(P.STACKS)
    games = select_tasks(a.games, getattr(a, "scenes", None))
    missing = [s for s in stacks if not STARTERS[s].exists()]
    if missing:
        print(f"missing starters: {missing} - build them first")
        return 1

    # SNAPSHOT THE RENDERED PROMPTS INTO THE RUN, ALWAYS, AS A MECHANISM.
    #
    # `PROTOCOL.md` has asked for this since #41, as an instruction. On 2026-08-17 a
    # readiness summary reported "prompt snapshot taken" on the strength of a green row
    # from the smoke suite, whose snapshot goes to scratch and is deleted; no launch
    # snapshot existed (#57). An instruction is a request. This is not.
    #
    # It is what the agents ACTUALLY received, and its only job is to be diffed after the
    # run - `prompt_guard.py --diff runs/<run>/prompts` - to prove the regime did not
    # move mid-run. A snapshot nobody can find later cannot do that job, and its absence
    # is indistinguishable from "no drift".
    prompts_dir = run_dir / "prompts"
    if prompts_dir.exists():
        print(f"prompt snapshot: already present at {prompts_dir} (kept, NOT overwritten "
              f"- it is the record of what was sent, and a rewrite would erase the very "
              f"drift it exists to catch)")
    else:
        import importlib.util as _ilu   # `tools/` is not a package; load by path.
        _spec = _ilu.spec_from_file_location(
            "_prompt_guard", Path(__file__).resolve().parent / "tools" / "prompt_guard.py")
        _pg = _ilu.module_from_spec(_spec)
        _spec.loader.exec_module(_pg)
        _pg.snapshot(str(prompts_dir))   # prints its own "snapshot: N ..." line
        if not (prompts_dir / "index.json").exists():
            print("REFUSING TO BUILD: the prompt snapshot did not write an index.")
            return 1

    # THE MANIFEST IS APPEND-ONLY, FOR THE SAME REASON THE SNAPSHOT ABOVE IS.
    #
    # The two guards were written eleven lines apart and only one of them existed. This
    # exact function protected `prompts/` and then overwrote `suite.json`, and
    # `runs/wg-g4-2026-08-17T09-38-32` records both halves to the millisecond:
    # `prompts/index.json` at 09:38:32.783 UTC, the directory name to the second, and
    # `suite.json` at 10:57:39.697 UTC - a second launch, 79 minutes later, whose
    # configuration is now the only one the directory admits to (#93).
    #
    # The reason the snapshot was guarded and this was not is that #57 was written about
    # PROMPTS. So the rule this now carries names the resource instead: **any durable
    # record of what a measurement was configured to be is append-only.** A second launch
    # adds `suite-<stamp>.json` and leaves `suite.json` byte-identical; `write_manifest`
    # reserves the name with O_EXCL, so it cannot lose the race with itself.
    _tools = Path(__file__).resolve().parent / "tools"
    import importlib.util as _ilu2      # `tools/` is not a package; load by path.
    import sys as _sys
    _mspec = _ilu2.spec_from_file_location("_manifest", _tools / "manifest.py")
    _manifest = _ilu2.module_from_spec(_mspec)
    # REGISTER BEFORE EXEC. `@dataclass` resolves its own annotations through
    # `sys.modules[cls.__module__]`, so a module loaded by path but never registered
    # raises `AttributeError: 'NoneType' object has no attribute '__dict__'` at import.
    # `prompt_guard.py` above gets away without this only because it defines no
    # dataclass - which is luck, not a difference in the loading.
    _sys.modules[_mspec.name] = _manifest
    _mspec.loader.exec_module(_manifest)
    # THE HARNESS IS PART OF WHAT THE RUN WAS CONFIGURED TO BE, so it goes in the record
    # that is append-only for exactly that reason. A run directory whose manifest does not
    # name its harness is a run nobody can place in the ledger's harness dimension.
    harness = agent_harness.get(getattr(a, "harness", None) or HARNESS)
    _manifest.write_manifest(run_dir, {
        "stacks": stacks, "games": games,
        # THE TASK CLASS OF EVERY SELECTED TASK, in the append-only record of what this
        # launch was configured to be. `games` alone does not say it: a directory holding
        # `s1_parallax` is a scene run whether or not anybody later remembers that an `s`
        # prefix means something.
        "task_classes": {t: aspects.task_class(t) for t in games},
        "trials": a.trials, "model": harness.model,
        "harness": harness.name,
        "max_turns": MAX_TURNS, "max_budget_usd": MAX_BUDGET_USD,
        "work_root": str(work_root),
        "started_at": dt.datetime.now(dt.timezone.utc).isoformat(),
    })

    caps = Caps(BUILD_CAP, a.parallel)
    # Prefer the starter's own warm target dir: it is compiled from exactly the source
    # each trial starts from, so an agent's first `just verify` is seconds rather than
    # a four-minute cold build. Falls back to the older shared cache. Each trial still
    # gets its OWN copy-on-write clone - sharing one target dir file-locks cargo, and
    # two trials once starved each other badly enough that both agents gave up while
    # reporting they had completed.
    pristine = STARTERS["rust"] / "target"
    if not pristine.exists():
        pristine = HERE / "runs" / "_cargo-target-pristine"
    prompt_override = None
    if getattr(a, "prompt_file", None):
        prompt_override = a.prompt_file.read_text()
        print(f"--prompt-file: sending {len(prompt_override)} bytes verbatim from "
              f"{a.prompt_file}")
    jobs = [(run_dir, work_root, s, g, i, caps, pristine if pristine.exists() else None,
             prompt_override, getattr(a, "turn_limit", None), harness.name)
            for g in games for s in stacks for i in range(a.trials)]

    # `--only` FILTERS, and refuses an id it cannot see. A filter that silently matches
    # nothing is the shape this project has been burned by twelve times: it would report
    # "0 trials" and look like a completed run.
    if getattr(a, "only", None):
        wanted = list(dict.fromkeys(a.only))
        # Index positionally, not by unpacking: the job tuple has gained fields twice
        # and a fixed-arity unpack breaks the moment it does. The filter below already
        # indexes by position for the same reason.
        available = {f"{j[3]}__{j[2]}__t{j[4]}" for j in jobs}
        unknown = [t for t in wanted if t not in available]
        if unknown:
            print(f"--only names trial ids outside the selection: {unknown}\n"
                  f"available here: {sorted(available)}")
            return 1
        jobs = [j for j in jobs if f"{j[3]}__{j[2]}__t{j[4]}" in wanted]
        print(f"--only: building {len(jobs)} of the selection's trials: {wanted}")

    print(f"{len(jobs)} trials = {len(games)} tasks x {len(stacks)} stacks x "
          f"{a.trials} trials, overall parallelism {a.parallel}, per-stack caps "
          f"{BUILD_CAP}\nwork root: {work_root}\n"
          f"harness: {harness.name} ({harness.model}) — an arm dimension; "
          f"eval/RUNS.md says what may be compared with what\n")

    # A verbatim prompt describes ONE trial's condition. Fanning it across a selection
    # would send one game's prompt to another game's cell and look like a normal run.
    if prompt_override is not None and len(jobs) != 1:
        print(f"--prompt-file requires a single-trial selection; this one has "
              f"{len(jobs)}")
        return 1

    with futures.ThreadPoolExecutor(max_workers=max(1, a.parallel)) as ex:
        list(ex.map(lambda j: build_trial(*j), jobs))
    print(f"\nrun dir: {run_dir}")
    print(f"now verify blinding:\n  judge/verify_blind.py {work_root}/*/")
    return 0


# --------------------------------------------------------------------------- #
# Evaluate phase
# --------------------------------------------------------------------------- #


def cmd_evaluate(a: argparse.Namespace) -> int:
    import evaluate as ev

    run_dir = a.run_dir.resolve()
    trials = [json.loads(p.read_text())
              for p in sorted((run_dir / "trials").glob("*.json"))]
    if not trials:
        print("no trials found")
        return 1
    caps = Caps(EVAL_CAP, a.eval_parallel)

    def one(rec: dict[str, Any]) -> None:
        tid, stack, game = rec["trial_id"], rec["stack"], rec["game"]
        work = Path(rec["work"])
        out = run_dir / "artifacts" / tid / "eval"
        if not work.exists():
            print(f"  [skip] {tid}: work tree gone ({work})")
            return
        env = dict(os.environ)
        if rec.get("cargo_target_dir"):
            env["CARGO_TARGET_DIR"] = rec["cargo_target_dir"]
        # One trial must not be able to abort the other twenty-three. A 24-trial
        # evaluation that dies on trial 3 loses the work already done and the work not
        # yet started; the completeness gate then correctly refuses to report, and the
        # whole run has to be repeated. Failures are recorded per trial instead.
        try:
            with caps.hold(stack):
                r = ev.evaluate(work, STARTERS[stack], game, out, seed=a.seed,
                                env=env,
                                run_judge=a.with_legacy_judge and not a.no_judge,
                                judge_model=a.judge_model,
                                audio=not a.no_audio)
        # noqa BLE001, deliberately blind: `evaluate` runs graders over a tree an agent
        # wrote, so the exception set is open. One submission that cannot be graded must
        # not take the other 23 down with it -- the build is already paid for. The
        # failure is written to `evaluation_error.txt` beside the artifacts and printed,
        # so a missing score has a reason on disk rather than being an absent row.
        except Exception as e:  # noqa: BLE001
            print(f"  [FAIL] {tid}: {type(e).__name__}: {e}", flush=True)
            (out / "evaluation_error.txt").parent.mkdir(parents=True, exist_ok=True)
            (out / "evaluation_error.txt").write_text(f"{type(e).__name__}: {e}\n")
            return
        jd = (r.get("diagnostic_scores") or {}).get("judge")
        jtxt = f"judge*={jd:.2f}" if jd is not None else "judge*=n/a"
        print(f"  [eval] {tid}  overall={r['overall']:.3f}  "
              f"prog={r['tier_scores']['programmatic']:.2f} "
              f"bot={r['tier_scores']['playbot']:.2f} "
              f"{jtxt}  {r['wall_s']}s", flush=True)

    with futures.ThreadPoolExecutor(max_workers=max(1, a.eval_parallel)) as ex:
        list(ex.map(one, trials))
    return cmd_report(a)


# --------------------------------------------------------------------------- #
# Concurrency confound check
# --------------------------------------------------------------------------- #


def cmd_concurrency_check(a: argparse.Namespace) -> int:
    """Evaluate the SAME submission serially and in parallel; diff the verdicts.

    A speedup that changes the answer is not a speedup.
    """
    import evaluate as ev

    # Unlike a trial copy, these must be RUNNABLE immediately - keep node_modules,
    # .venv and Library. Dropping them would make every copy fail identically in both
    # arms, and "no verdict changed" would then be vacuously true. That is precisely
    # the mechanism-reports-success-and-measures-nothing failure this project keeps
    # hitting, so it is worth the disk.
    cc_ignore = shutil.ignore_patterns(".git", "target", "runs", "__pycache__",
                                       "artifacts", "Temp", "coverage")
    tmp = Path(tempfile.mkdtemp(prefix="cc-"))
    copies = []
    for i in range(a.k):
        c = tmp / f"copy{i}"
        shutil.copytree(a.submission, c, ignore=cc_ignore, symlinks=True)
        copies.append(c)

    def run_one(idx: int) -> dict[str, Any]:
        return ev.evaluate(copies[idx], a.starter.resolve(), a.game,
                           tmp / f"out{idx}", run_judge=False)

    t0 = time.monotonic()
    serial = [run_one(i) for i in range(a.k)]
    serial_s = time.monotonic() - t0

    for i in range(a.k):
        shutil.rmtree(copies[i])
        shutil.copytree(a.submission, copies[i], ignore=cc_ignore, symlinks=True)
        shutil.rmtree(tmp / f"out{i}", ignore_errors=True)

    t0 = time.monotonic()
    with futures.ThreadPoolExecutor(max_workers=a.k) as ex:
        par = list(ex.map(run_one, range(a.k)))
    par_s = time.monotonic() - t0

    def verdicts(r: dict[str, Any]) -> dict[str, bool]:
        out = {}
        for tier in ("programmatic", "playbot"):
            for c in r[tier]["criteria"]:
                out[f"{tier}.{c['id']}"] = c["passed"]
        return out

    base = verdicts(serial[0])
    diffs: list[str] = []
    for label, runs in (("serial", serial), ("parallel", par)):
        for i, r in enumerate(runs):
            v = verdicts(r)
            for k in sorted(set(base) | set(v)):
                if base.get(k) != v.get(k):
                    diffs.append(f"{label}[{i}] {k}: {base.get(k)} -> {v.get(k)}")

    # A check where everything already fails cannot detect a change, and "no verdict
    # changed" would be vacuously true. Say so loudly rather than reporting a pass.
    baseline_pass = sum(1 for v in base.values() if v)
    if baseline_pass == 0:
        print("VACUOUS: every criterion already fails in the serial baseline, so this "
              "check can prove nothing. Give it a submission that passes something.")
        return 1

    print(f"serial   {a.k} evaluations in {serial_s:.0f}s  "
          f"scores {[round(r['overall'], 3) for r in serial]}")
    print(f"parallel {a.k} evaluations in {par_s:.0f}s  "
          f"scores {[round(r['overall'], 3) for r in par]}")
    if diffs:
        print(f"\nCONFOUND: {len(diffs)} criterion verdict(s) changed:")
        for d in diffs[:40]:
            print("  " + d)
        print("\nDo NOT raise --eval-parallel for this stack.")
        return 1
    print(f"\nNo criterion changed its verdict. Parallel evaluation at k={a.k} is a "
          f"speedup of {serial_s / par_s:.1f}x, not a confound.")
    shutil.rmtree(tmp, ignore_errors=True)
    return 0


# --------------------------------------------------------------------------- #
# Reporting
# --------------------------------------------------------------------------- #


def cmd_report(a: argparse.Namespace) -> int:
    run_dir = a.run_dir.resolve()
    rows: list[dict[str, Any]] = []
    for tp in sorted((run_dir / "trials").glob("*.json")):
        rec = json.loads(tp.read_text())
        ep = run_dir / "artifacts" / rec["trial_id"] / "eval" / "report.json"
        rec["eval"] = json.loads(ep.read_text()) if ep.exists() else None
        rows.append(rec)

    # Loud, before any number is printed. An incomplete trial is excluded from every
    # aggregate rather than quietly averaged in with a tier missing.
    # ZERO-EVALUATION GUARD. The completeness gate fires when a trial IS evaluated and
    # a tier file is missing; it cannot fire when evaluation never ran at all. That
    # gap let "evaluation is running" be reported when no evaluation process had ever
    # started and not one tier file existed.
    evaluated = [r for r in rows if r.get("eval")]
    if not evaluated:
        print(f"\n*** NOTHING HAS BEEN EVALUATED ***")
        print(f"{len(rows)} trial build record(s) exist but zero have evaluation "
              f"output. Run `evaluate` first; there is nothing to report.")
        return 1

    incomplete = [r for r in rows
                  if r.get("eval") and not r["eval"].get("tiers_complete", False)]
    unevaluated = [r for r in rows if not r.get("eval")]
    if incomplete or unevaluated:
        print("\n*** INCOMPLETE TRIALS - EXCLUDED FROM ALL AGGREGATES ***")
        for r in incomplete:
            print(f"  {r['trial_id']}: missing "
                  f"{r['eval'].get('missing_tiers')}")
        for r in unevaluated:
            print(f"  {r['trial_id']}: never evaluated")
        print("  Re-run `evaluate` for these before believing any number below.\n")
        bad = {r["trial_id"] for r in incomplete} | {r["trial_id"] for r in unevaluated}
        rows = [r for r in rows if r["trial_id"] not in bad]
        if not rows:
            print("no complete trials remain")
            return 1
    if not rows:
        print("no trials")
        return 1

    # PARTITION BY TERMINAL REASON BEFORE ANY AGGREGATE.
    # MEASURED (FINDINGS #22): a per-game mean computed across four real runs and four
    # trials that died at 25-27 turns produced 7.61 tokval for the arena game - a number that
    # described no trial that ever ran, was arithmetically correct, and manufactured the
    # finding "the arena task is too easy" that survived two rounds of scrutiny. The
    # completed-only mean was 13.62. `completed`, `max_turns`, `budget_exhausted`,
    # `api_error` and session-limit aborts are different populations and averaging
    # across them describes none of them.
    def _reason(r: dict[str, Any]) -> str:
        return str(r["agent"].get("terminal_reason"))

    # A trial whose play-bot tier measured NOTHING is a third population, distinct from
    # both "completed" and "truncated": the agent finished, the submission exists, and
    # the instrument never read it. Its 0.00 on the only scored tier says nothing about
    # the work, and it can only arise on the stacks that take a project-wide lock.
    unmeasured = [r for r in rows
                  if r.get("eval") and r["eval"].get("playbot_usable") is False]
    if unmeasured:
        print("\n*** PLAY-BOT TIER MEASURED NOTHING - EXCLUDED FROM EVERY AGGREGATE ***")
        for r in sorted(unmeasured, key=lambda r: r["trial_id"]):
            why = "; ".join(list((r["eval"].get("playbot_unscored") or {}).values())[:2])
            print(f"  {r['trial_id']:<26} {why[:150]}")
        print("  These are NOT scores of zero. Adjudicate them against the submission "
              "before\n  reporting anything about the stack they belong to.\n")

    unmeasured_ids = {r["trial_id"] for r in unmeasured}
    truncated = [r for r in rows if _reason(r) != "completed"]
    scored_rows = [r for r in rows if _reason(r) == "completed"
                   and r["trial_id"] not in unmeasured_ids]
    if truncated:
        print("\n*** NOT `completed` - EXCLUDED FROM EVERY AGGREGATE BELOW ***")
        for r in sorted(truncated, key=lambda r: r["trial_id"]):
            print(f"  {r['trial_id']:<26} {_reason(r):<20} "
                  f"turns={r['agent'].get('num_turns')} "
                  f"{tokenvalue.tag(r['agent'].get('cost_usd', 0))}")
        print(f"  n={len(truncated)} excluded, n={len(scored_rows)} aggregated.\n")
    if not scored_rows:
        print("no trial reached terminal_reason=completed; there is nothing to "
              "aggregate. The per-trial table below is the whole result.")

    print(f"\n=== {run_dir.name}: {len(rows)} trials ({len(scored_rows)} aggregated, "
          f"{len(truncated)} not completed, {len(unmeasured)} unmeasured) ===\n")

    # TWO TASK CLASSES, NEVER ONE MEAN. A scene has no player and is graded by a
    # different tier-2 instrument against different criteria (`eval/SCENES.md`), so a
    # per-stack figure averaged over both describes neither. The class comes off the
    # stored record where the harness wrote it, and off `aspects.task_class` for a record
    # written before that field existed - so an old directory still partitions.
    def _klass(r: dict[str, Any]) -> str:
        return str(r.get("task_class") or aspects.task_class(r["game"]))

    classes = sorted({_klass(r) for r in rows})
    if len(classes) > 1:
        print(f"*** {len(classes)} TASK CLASSES IN ONE RUN: {classes} ***")
        print("    Scene and game scores are never pooled. Every aggregate below is "
              "computed\n    PER CLASS and labelled with it.\n")
    pre_gate = [r for r in rows if r.get("eval") and not r["eval"].get("scoring_regime")]
    if pre_gate:
        print(f"*** {len(pre_gate)} of {len(rows)} stored `overall` values were written "
              f"under the PRE-GATE scheme\n    (0.31*prog + 0.69*bot). They are shown as "
              f"stored and are NOT rewritten here.\n    Read the `prog` and `bot` columns "
              f"for those rows, not `overall`.\n")
    print("`overall` = playbot. Tier 1 is a GATE and the judge is a DIAGNOSTIC; neither\n"
          "contributes to it - see RUBRIC.md, FINDINGS #21 and #92.\n"
          "The `gate` column is the tier-1 verdict: PASS, or the number of tier-1\n"
          "criteria that failed. A gate failure does not deduct and does not exclude;\n"
          "it is a fact about the submission that the score is not the place for.\n"
          "`regime` says which scheme wrote the stored `overall`: rows marked `w` predate\n"
          "2026-08-23 and are 0.31*prog + 0.69*bot. They are NOT comparable with gate rows.\n")
    hdr = (f"{'stack':<8} {'game':<13} {'overall':>8} {'gate':>7} {'rg':>3} {'prog':>6} "
           f"{'bot':>6} {'judge*':>7} {'turns':>6} {tokenvalue.UNIT:>7} {'wall':>7}")
    print(hdr)
    print("-" * len(hdr))
    for r in sorted(rows, key=lambda r: (r["game"], r["stack"], r["trial"])):
        e = r.get("eval")
        if not e:
            print(f"{r['stack']:<8} {r['game']:<13} {'(not evaluated)':>8}")
            continue
        ts = e["tier_scores"]
        jd = (e.get("diagnostic_scores") or {}).get("judge",
              (e.get("judge") or {}).get("score", 0.0))
        # A record with no `gate` is one written before the gate regime. It is shown as
        # `-`, never computed on the fly: deriving a new-regime verdict for an old
        # record would put a number in the column that nothing on disk supports.
        g = e.get("gate")
        if not g:
            gate_txt = "-"
        elif not g.get("usable"):
            gate_txt = "UNUSABLE"
        elif g.get("passed"):
            gate_txt = "PASS"
        else:
            # `!` marks a BLOCKING failure: tier 2 could not observe this submission,
            # so its `overall` restates the gate rather than adding to it.
            bang = "!" if g.get("blocking_failed") else ""
            gate_txt = f"FAIL{bang}:{g.get('n_failed')}"
        regime = "g" if e.get("scoring_regime") else "w"
        print(f"{r['stack']:<8} {r['game']:<13} {e['overall']:>8.3f} {gate_txt:>7} "
              f"{regime:>3} "
              f"{ts['programmatic']:>6.2f} {ts['playbot']:>6.2f} {jd:>7.2f} "
              f"{r['agent']['num_turns'] or 0:>6} "
              # `tokenvalue.fmt` rather than a format spec: `cost_usd` is `None` on every
              # arm whose figure is not tokval, and `:>7.2f` raises TypeError on it. A
              # report that dies on a valid record is a report nobody can read the run
              # with, and `0.00` in its place would be worse.
              f"{tokenvalue.fmt(r['agent'].get('cost_usd'), width=7)} "
              f"{r['wall_s']:>6.0f}s")

    # WHAT THE SUBJECT SAID ABOUT ITS OWN WORK, beside the score it was given.
    # Four documents say to read the agent's closing message before grading it - rule 11,
    # DECISIONS.md, PROTOCOL.md and RUNS.md - and until 2026-08-23 nothing did. 31 of 75
    # completed trials had written a disclosure; two of this project's more expensive
    # findings (#49, #98) were recovered from that field by hand, months late.
    # `tools/disclosure.py` reads the WHOLE message from artifacts/<trial>/
    # agent_result.json (.result), never `agent.final_text`, which is the last 3000
    # characters of it and a partial read of 43 of the 90 stored messages.
    try:
        disc_rows = _disclosure.scan_run(run_dir)
    except _disclosure.DisclosureError as exc:
        print(f"\n*** DISCLOSURES NOT READ: {exc} ***")
        print("    This is a non-measurement, not an absence of disclosures.")
    else:
        print(f"\n{_disclosure.BANNER}")
        print(_disclosure.CAVEAT)
        for line in _disclosure.render_rows(disc_rows, indent="  "):
            print(line)
        print(f"  {_disclosure.summarise(disc_rows)}")
        print(f"  Whole messages, no selection applied: python3 tools/disclosure.py "
              f"--run-dir {run_dir} --full")

    # A MEAN ACROSS TWO SCORING REGIMES DESCRIBES NEITHER (rule 4). Tier 1 was 0.31 of
    # `overall` before 2026-08-23 and is a gate after it, so a directory holding both -
    # which is what a partial re-evaluation produces - must say so before any average.
    regimes = {(r["eval"].get("scoring_regime") or "weighted-0.31/0.69 (pre-gate)")
               for r in scored_rows if r.get("eval")}
    if len(regimes) > 1:
        print(f"\n*** MIXED SCORING REGIMES IN ONE RUN: {sorted(regimes)} ***")
        print("    `overall` does not mean the same thing in every row above, so the "
              "per-stack\n    means below are computed over a population that is not "
              "homogeneous.\n    Re-evaluate the whole run, or report the tiers "
              "separately. Do not quote these.")

    for klass in classes:
        in_class = [r for r in scored_rows if _klass(r) == klass]
        print(f"\n--- {klass}s: per stack, averaged per task first then across tasks "
              f"(completed trials only, n={len(in_class)}) ---")
        if not in_class:
            print("no completed trials in this class")
            continue
        by_stack: dict[str, dict[str, list[float]]] = {}
        for r in in_class:
            if r.get("eval"):
                by_stack.setdefault(r["stack"], {}).setdefault(r["game"], []).append(
                    r["eval"]["overall"])
        for stack, per_game in sorted(by_stack.items()):
            means = [statistics.fmean(v) for v in per_game.values()]
            se = ((statistics.stdev(means) / len(means) ** 0.5)
                  if len(means) > 1 else float("nan"))
            se_txt = f"{se:.3f}" if se == se else "  -"
            print(f"{stack:<8} score {statistics.fmean(means):.3f} +-SE {se_txt}  "
                  f"(n={len(means)} {klass}s)")
        if klass == "scene":
            print("SCENE SCORES ARE FIXTURE-VALIDATED. Every scene_probe.py threshold was "
                  "chosen against\nfixtures written by the same hand as the criterion; "
                  "read `python3 judge/scene_mutants.py\n--census` before quoting any of "
                  "these (eval/SCENES.md).")
    print("\nScores are averaged PER TASK first, then across tasks. Pooling across all "
          "trials is inconsistent (Miller, arXiv:2411.00640 sec 3).")

    print("\n* judge = DIAGNOSTIC ONLY, contributes nothing to `overall`.")
    for klass in classes:
        in_class = [r for r in scored_rows if _klass(r) == klass]
        print(f"\n--- {klass}s: per criterion, across {len(in_class)} completed trials "
              "(judge rows are diagnostic, not scored) ---")
        tally: dict[str, dict[str, list[int]]] = {}
        for r in in_class:
            e = r.get("eval")
            if not e:
                continue
            for tier in ("programmatic", "playbot", "judge"):
                t = e.get(tier) or {}
                # THE INSTRUMENT, not the slot. `playbot` is the name of the weighted
                # tier-2 SLOT and a scene's slot holds `scene_probe` output; printing
                # the slot name over scene criterion ids would invite exactly the pooling
                # the class partition exists to prevent.
                label = str(t.get("tier") or tier)
                for c in t.get("criteria", []):
                    tally.setdefault(label, {}).setdefault(c["id"], []).append(
                        int(bool(c["passed"])))
        for tier, crits in tally.items():
            print(f"\n[{tier}{' - DIAGNOSTIC, NOT SCORED' if tier == 'judge' else ''}]")
            for cid, vals in sorted(crits.items(),
                                    key=lambda kv: sum(kv[1]) / len(kv[1])):
                print(f"  {sum(vals)}/{len(vals)}  {cid}")

    print("\n--- terminal reasons ---")
    reasons: dict[tuple[str, str], int] = {}
    for r in rows:
        key = (r["stack"], str(r["agent"].get("terminal_reason")))
        reasons[key] = reasons.get(key, 0) + 1
    for (stack, reason), n in sorted(reasons.items()):
        print(f"{stack:<8} {reason:<28} {n}")
    print(f"\n{tokenvalue.DEFINITION}")

    inst = [r["eval"]["judge"].get("instability") for r in scored_rows
            if r.get("eval") and r["eval"]["judge"].get("instability") is not None]
    if inst:
        print(f"\njudge instability (fraction of criteria where the two criteria "
              f"orders disagreed): mean {statistics.fmean(inst):.3f}, "
              f"max {max(inst):.3f}")
        print("Measured: instability is a property of the ARTIFACT, not the rubric - "
              "0.000 on an\nuncontested submission, up to 0.462 on a contested one. "
              "That is why this tier is\nreported but not scored.")
    return 0


# --------------------------------------------------------------------------- #
# Cost model
# --------------------------------------------------------------------------- #

# EVERY FIGURE BELOW IS `tokval`, NOT MONEY: the list price the tokens would carry at
# published API rates, on a subscription account where no money moves per token (#159,
# `tools/tokenvalue.py`). It is the only per-trial resource number the harness has, and it
# is kept for that - nothing here is a bill and no run is bounded by it.
#
# Measured on this repo: the small spec-conformance bake-off ran 24 Opus trials at a
# median of ~2.6 tokval and 32-49 turns for a task that changed a few dozen lines. A
# whole-game build is a different order of magnitude, so the estimate below is scaled
# from those numbers rather than guessed, and the range is deliberately wide.
COST_PER_TRIAL = {"low": 12.0, "mid": 20.0, "high": 25.0}
TURNS_PER_TRIAL = {"low": 90, "mid": 150, "high": 250}
BUILD_MIN_PER_TRIAL = {"rust": 95, "ts": 65, "unity": 80, "godot": 70}
EVAL_MIN_PER_TRIAL = {"rust": 14, "ts": 8, "unity": 16, "godot": 10}
#: WHAT A SCENE CELL COSTS IN WALL CLOCK, and the population it was measured over.
#:
#: ONE CELL, AND ITS BUILD FIGURE IS A FLOOR RATHER THAN A DURATION. `s1_parallax__ts__t0`
#: was still working at 3599s when it was killed from outside, so 60 min is what the cell
#: had used and not what it needed. Multiplying it up gives a lower bound and nothing
#: else - `eval/AGENTS.md` forbids projecting across a boundary nothing has been measured
#: across, and the unmeasured boundaries here are the other 3 stacks and the other scene.
SCENE_WALL_CLOCK_NOTE = """SCENE WALL CLOCK, from 1 cell (s1_parallax x ts, eval/RUNS.md):
  build     >= 60 min. The cell was KILLED at 3599s while still working, so this is a
            floor. ts is the cheapest stack on the game table; rust, unity and godot are
            unmeasured for scenes and the game table says nothing about a scene.
  evaluate  58s, complete: tier 1 plus the scene probe's 3 traces and 3 films.
  A full 2-scene x 4-stack x 2-trial matrix is 16 cells, so its build floor is >= 16 h
  serial and >= 4 h at parallelism 4. The floor is not an estimate of the run."""

JUDGE_COST_PER_TRIAL = 1.75   # MEASURED: two Sonnet-5 passes over a 95 KB pack plus 12
                              # frames came to 1.70 tokval and took 30-31 turns each. The
                              # first estimate here was 0.35 and was wrong by 5x - the
                              # judge reads files and images with tools, it does not get
                              # one big prompt.


def cmd_plan(a: argparse.Namespace) -> int:
    stacks = a.stacks or list(P.STACKS)
    games = select_tasks(a.games, getattr(a, "scenes", None))
    classes = {aspects.task_class(t) for t in games}
    n = len(stacks) * len(games) * a.trials
    print(f"matrix: {len(games)} tasks x {len(stacks)} stacks x {a.trials} trials "
          f"= {n} trials\n")
    if len(classes) > 1:
        print(f"*** {len(classes)} TASK CLASSES IN ONE SELECTION: {sorted(classes)} ***")
        print("Scene and game scores are never pooled (eval/SCENES.md), so the totals "
              "below are a\ncount of trials and not of a comparable population.\n")
    if "scene" in classes:
        # SCENE WALL CLOCK IS MEASURED, NOT SCALED FROM THE GAME TABLE. The cost table
        # below is scaled from game trials and says nothing about a scene.
        print(SCENE_WALL_CLOCK_NOTE + "\n")
    print(f"projected {tokenvalue.UNIT} (a token valuation, not a bill - see the "
          f"footnote)\n")
    print(f"{'':<14} {'low':>10} {'mid':>10} {'high':>10}")
    print(f"{'agent':<14} {n * COST_PER_TRIAL['low']:>10.0f} "
          f"{n * COST_PER_TRIAL['mid']:>10.0f} {n * COST_PER_TRIAL['high']:>10.0f}")
    print(f"{'judge':<14} {n * JUDGE_COST_PER_TRIAL:>10.0f} "
          f"{n * JUDGE_COST_PER_TRIAL:>10.0f} {n * JUDGE_COST_PER_TRIAL:>10.0f}")
    print(f"{'TOTAL':<14} {n * (COST_PER_TRIAL['low'] + JUDGE_COST_PER_TRIAL):>10.0f} "
          f"{n * (COST_PER_TRIAL['mid'] + JUDGE_COST_PER_TRIAL):>10.0f} "
          f"{n * (COST_PER_TRIAL['high'] + JUDGE_COST_PER_TRIAL):>10.0f}")

    build_min = sum(BUILD_MIN_PER_TRIAL[s] * len(games) * a.trials for s in stacks)
    eval_min = sum(EVAL_MIN_PER_TRIAL[s] * len(games) * a.trials for s in stacks)
    par_build = max(1, min(a.parallel, sum(BUILD_CAP[s] for s in stacks)))
    print(f"\nwall clock, serial     : build {build_min / 60:.1f} h + "
          f"evaluate {eval_min / 60:.1f} h = {(build_min + eval_min) / 60:.1f} h")
    print(f"wall clock, parallel {par_build:<2}: build ~{build_min / 60 / par_build:.1f} h "
          f"+ evaluate {eval_min / 60:.1f} h (evaluation is serial by default) "
          f"= ~{build_min / 60 / par_build + eval_min / 60:.1f} h")
    print("\nCaveats worth reading before authorising:")
    print(f"  * The per-trial band is scaled from measured small-task trials on this")
    print(f"    repo (2.6 {tokenvalue.UNIT} median, 32-49 turns) to a task perhaps 8-10x")
    print(f"    larger. It is an estimate, and it is not what bounds the run.")
    print(f"  * WHAT BOUNDS A TRIAL IS --max-turns {MAX_TURNS}, which the agent cannot")
    print(f"    see. --max-budget-usd is {MAX_BUDGET_USD}: a stated budget is visible to")
    print(f"    the agent and instructs it, and on a subscription it would be asking the")
    print(f"    agent to conserve something that is not scarce (#159).")
    # THE STANDING CONFIGURATION HAS NO BUDGET CAP, and this arithmetic used to add
    # `MAX_BUDGET_USD` to a float. `plan` therefore crashed with a TypeError for every
    # reader after the no-cap regime was adopted - the one command PROTOCOL.md tells you
    # to run before authorising a matrix. Nobody ran it, so nobody saw it.
    #
    # The turn limit priced at a MEASURED per-turn rate is the honest projection, stated
    # as a range because the measured rate varies 2.13x across cells (FINDINGS #42).
    lo, hi = 0.13, 0.20
    print(f"  * At a measured {lo:.2f}-{hi:.2f} {tokenvalue.UNIT}/turn, {MAX_TURNS} turns")
    print(f"    bounds ONE trial at {MAX_TURNS * lo:.0f}-{MAX_TURNS * hi:.0f}, so {n}")
    print(f"    trials project to {n * (MAX_TURNS * lo + JUDGE_COST_PER_TRIAL):.0f}-"
          f"{n * (MAX_TURNS * hi + JUDGE_COST_PER_TRIAL):.0f} {tokenvalue.UNIT}. No trial")
    print(f"    has come close: the largest measured is 72.83.")
    print("  * Run TWO trials in DIFFERENT cells first and re-run `plan` with the")
    print("    measured range - not one trial, and not a point estimate. Within-cell")
    print("    spread has been measured at 1.62x and across-cell at 2.13x (FINDINGS #42).")
    print(f"\n  {tokenvalue.DEFINITION}")
    return 0


# --------------------------------------------------------------------------- #


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    # THE WORK ROOT HAS TWO REQUIREMENTS AND MOST CANDIDATES SATISFY ONLY ONE.
    #
    # 1. OUTSIDE THE REPOSITORY, for blinding. `verify_blind.py` walks every ancestor
    #    of a trial tree looking for RUBRIC.md, because a tree inside the repo lets a
    #    building agent walk up and read the grading criteria. Demonstrated: pointing
    #    the checker at `starters/` yields 4 "RUBRIC REACHABLE from ancestor" findings.
    #
    # 2. DURABLE FOR LONGER THAN THE MEASUREMENT. $TMPDIR is reaped by macOS.
    #    MEASURED 2026-08-16: six TypeScript submissions lost ~80% of their installed
    #    toolchain between building and grading (node_modules 6,175 files -> 1,230;
    #    `three` 1,195 -> 2), and every one then scored exactly 6/14 - which read as a
    #    stack characteristic. See FINDINGS #45.
    #
    # $TMPDIR satisfies (1) and fails (2). It was chosen for (1) and nobody asked
    # about (2). BOTH reasons are stated here because a comment giving one of two
    # reasons is how the next person "simplifies" this back into /tmp.
    default_work = DEFAULT_WORK_ROOT

    for name in ("plan", "build", "evaluate", "report"):
        p = sub.add_parser(name)
        p.add_argument("--stacks", nargs="*", default=None, choices=list(P.STACKS))
        # THE DEFAULT IS EVERY GAME AND NO SCENE. `select_tasks()` holds the decision
        # and the reason; this is only where the two flags are declared.
        p.add_argument("--games", nargs="*", default=None, choices=list(P.TASKS),
                       help="which games to build (default: all of them)")
        p.add_argument("--scenes", nargs="*", default=None, choices=list(SP.SCENES),
                       help="which SCENES to build (default: NONE - a scene is built "
                            "only when it is named. eval/SCENES.md says why)")
        p.add_argument("--trials", type=int, default=2)
        p.add_argument("--parallel", type=int, default=4)
        p.add_argument("--eval-parallel", type=int, default=1)
        p.add_argument("--seed", type=int, default=7)
        # RETRY A SPECIFIC CELL, AND ONLY THAT CELL. `cmd_build` never consults
        # existing trial records and `prepare()` begins with `rmtree`, so re-running
        # a selection that includes completed trials DESTROYS them - sixteen
        # completed submissions worth 486 tokval were one unscoped rerun away on
        # 2026-08-15 (FINDINGS #36). `--stacks`/`--games`/`--trials` can only
        # express a product, so "rebuild rust t1 alone" was not expressible at all.
        # REPRODUCING AN EARLIER CONDITION. `_preamble()` is shared by every game, so an
        # edit aimed at one task silently changes the other three (FINDINGS #41). When
        # the point of a run is to differ from a stored trial in exactly ONE variable,
        # render nothing: send the bytes that were actually sent.
        p.add_argument("--prompt-file", type=Path, default=None,
                       help="send this file's contents as the prompt instead of "
                            "rendering it. Only valid with a single-trial selection.")
        # Override the turn limit for one build without editing the standing constant.
        #
        # DO NOT USE THIS TO "MATCH" AN EARLIER RUN'S LIMIT. A ceiling that may have been
        # binding is not a control - holding it constant can truncate the new run and
        # produce a confident answer to a question the experiment did not test
        # (AGENTS.md rule 8, qualifier). Raise ceilings and let the measurement say
        # whether they bound. The legitimate use is the opposite one: deliberately
        # REPRODUCING a truncation to study it.
        p.add_argument("--turn-limit", type=int, default=None,
                       help="override --max-turns for this build only. Not for matching "
                            "an earlier run's ceiling - see AGENTS.md rule 8.")
        p.add_argument("--only", nargs="+", default=None, metavar="TRIAL_ID",
                       help="build ONLY these trial ids (e.g. g3_arena__rust__t1). "
                            "Every id must be inside the --stacks/--games/--trials "
                            "selection; an id that is not is an error, not a "
                            "silent no-op.")
        # WHICH AGENT CLI BUILDS. A second harness is a second arm, never a second
        # reading of the same one: the two differ in permission regime, in the Stop gate,
        # in what a turn counts and in whose price list their tokens would carry. Never
        # cross a harness change with any other change in one run.
        p.add_argument("--harness", default=HARNESS,
                       choices=sorted(agent_harness.HARNESSES),
                       help="the agent CLI to build with (default: %(default)s). It is a "
                            "recorded arm dimension - see eval/RUNS.md.")
        p.add_argument("--no-judge", action="store_true")
        # The legacy 13-criterion judge is OPT-IN. It is weighted 0.00, cost a measured
        # 1.75 tokval per submission, and across 24 submissions its only firings were
        # adjudicated as a frame-capture artifact (FINDINGS #26). Running it by default
        # used ~42 tokval a matrix on a tier that carried no information.
        p.add_argument("--with-legacy-judge", action="store_true",
                       help="run the retired 13-criterion generalist judge as well")
        # Audio entered the task set on 2026-08-14. Scoring a submission built before
        # that against the audio criteria would measure the TASK CHANGE, not the work.
        p.add_argument("--no-audio", action="store_true",
                       help="omit the audio criteria - required when re-scoring a run "
                            "whose task did not ask for sound")
        p.add_argument("--judge-model", default="sonnet")
        p.add_argument("--work-root", type=Path, default=default_work,
                       help="MUST be outside this repository - see verify_blind.py")
        if name != "plan":
            p.add_argument("--run-dir", required=True, type=Path)

    cc = sub.add_parser("concurrency-check")
    cc.add_argument("--submission", required=True, type=Path)
    cc.add_argument("--starter", required=True, type=Path)
    cc.add_argument("--game", required=True, choices=sorted(ALL_TASKS))
    cc.add_argument("--k", type=int, default=3)

    a = ap.parse_args()
    return {
        "plan": cmd_plan, "build": cmd_build, "evaluate": cmd_evaluate,
        "report": cmd_report, "concurrency-check": cmd_concurrency_check,
    }[a.cmd](a)


if __name__ == "__main__":
    raise SystemExit(main())
