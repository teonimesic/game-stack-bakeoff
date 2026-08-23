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
sys.path.insert(0, str(HERE / "suites"))
sys.path.insert(0, str(HERE / "judge"))

import wholegame_prompts as P  # noqa: E402

STARTERS = {s: HERE / "starters" / s for s in P.STACKS}

# Per-stack caps for the BUILD phase. Rust and TypeScript are headless enough to run
# several at once; Godot opens a real window for its render tests and Unity launches an
# editor per verify, so both stay low.
BUILD_CAP = {"rust": 4, "ts": 4, "godot": 2, "unity": 2}
# The evaluation phase renders. Default serial for everyone until measured otherwise.
EVAL_CAP = {"rust": 1, "ts": 1, "godot": 1, "unity": 1}

# Budget per trial. Whole-game builds are expensive; these are hard stops, and the
# harness records terminal_reason so a truncated trial is never confused with a failure.
# STANDING CONFIGURATION from 2026-08-15 (PROTOCOL.md, DECISIONS.md).
# 250 was the binding limit at a $48 cap - `g3_arena__rust__t1` stopped at 251 turns with
# $12 of its stated budget unspent (FINDINGS #35), so the run was governed by the flag the
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
# caps are not comparable, and the observed clustering just under $25 (23.07, 24.33,
# 24.34, 25.06) is what an agent pacing itself to a budget it was told about looks like -
# not a coincidence of task size.
# None means DO NOT PASS THE FLAG, and that is the point rather than a convenience.
# `--max-budget-usd` is VISIBLE TO THE AGENT and instructs it: spend rose 1.54x on Tetris
# when the stated ceiling went 25 -> 48 (FINDINGS #33). Any stated value is an
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

MODEL = "opus"       # builders. The judge deliberately runs a different model.


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


def agent_metrics(agent: dict[str, Any]) -> dict[str, Any]:
    """Cost and tokens from `modelUsage`, which the SDK docs say to prefer over
    `usage` - `usage` is the main loop only and excludes subagents."""
    mu = agent.get("modelUsage") or {}
    if mu:
        return {
            "cost_usd": round(sum((m or {}).get("costUSD", 0) or 0
                                  for m in mu.values()), 4),
            "input_tokens": sum((m or {}).get("inputTokens", 0) or 0
                                for m in mu.values()),
            "output_tokens": sum((m or {}).get("outputTokens", 0) or 0
                                 for m in mu.values()),
            "cache_read": sum((m or {}).get("cacheReadInputTokens", 0) or 0
                              for m in mu.values()),
            "models": sorted(mu),
        }
    u = agent.get("usage") or {}
    return {"cost_usd": agent.get("total_cost_usd") or 0,
            "input_tokens": u.get("input_tokens", 0),
            "output_tokens": u.get("output_tokens", 0),
            "cache_read": u.get("cache_read_input_tokens", 0), "models": []}


def parse_agent(stdout: str) -> dict[str, Any]:
    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        data = [json.loads(ln) for ln in stdout.splitlines()
                if ln.strip().startswith("{")] or [{}]
    if isinstance(data, dict):
        data = [data]
    results = [d for d in data if isinstance(d, dict) and d.get("type") == "result"]
    return results[-1] if results else (data[-1] if data else {})


def run_agent(work: Path, prompt: str, env: dict[str, str],
              turn_limit: int | None = None) -> tuple[dict, str]:
    sid = str(uuid.uuid4())
    turns = MAX_TURNS if turn_limit is None else int(turn_limit)
    argv = [
        "claude", "-p", prompt,
        "--output-format", "json",
        "--model", MODEL,
        "--max-turns", str(turns),
        # Verified necessary: without it the operator's global CLAUDE.md leaks in.
        "--setting-sources", "project",
        "--strict-mcp-config",
        "--exclude-dynamic-system-prompt-sections",
        "--permission-mode", "acceptEdits",
        # TARGETED ALLOWLIST, user-ruled. Measured across the published 24-trial
        # bake-off: 302 denials, 12.6 per trial, 29.8% of all turns lost, and the
        # spread across the four stacks was only 3 percentage points (28.1-31.1%) -
        # a uniform tax rather than a per-stack bias. In the whole-game calibration
        # trial the agent was denied `just verify` itself and signed off saying two
        # checks were unrun, while the repo it left behind passed the gate in 5s.
        #
        # Deliberately NOT bypassPermissions and deliberately not a catch-all: the
        # sandbox stays meaningful, only the build and verification commands the
        # template itself tells the agent to run are permitted.
        "--allowedTools", "Bash(just *)", "Bash(cargo *)", "Bash(pnpm *)",
        "Bash(git *)",
        "--session-id", sid,
    ]
    # Appended only when set. A budget cap is an instruction to the agent, so the
    # no-cap regime has to actually OMIT the flag rather than pass a large number.
    if MAX_BUDGET_USD is not None:
        argv += ["--max-budget-usd", str(MAX_BUDGET_USD)]
    # check=False: an agent that stops on its budget or turn ceiling exits non-zero and
    # has still produced a submission worth grading. Raising here would throw away the
    # trial we paid for; the terminal reason comes out of the parsed result instead.
    try:
        p = subprocess.run(argv, cwd=work, capture_output=True, text=True,
                           timeout=TIMEOUT_S, env=env, check=False)
        return parse_agent(p.stdout), p.stderr[-4000:]
    except subprocess.TimeoutExpired:
        return {"is_error": True, "result": "HARNESS TIMEOUT",
                "terminal_reason": "harness_timeout"}, ""


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
                turn_limit: int | None = None) -> dict[str, Any]:
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
                           "trial": trial, "work": str(work),
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

        prompt = (prompt_override if prompt_override is not None
                  else P.TASKS[game](stack))
        (art / "prompt.txt").write_text(prompt)

        t0 = time.monotonic()
        agent, stderr = run_agent(work, prompt, env, turn_limit)
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

    # A SESSION LIMIT IS NOT AN API ERROR.
    # MEASURED, twice: the CLI reports an account session limit as
    # terminal_reason="api_error" with the real cause only in the result text
    # ("You've hit your session limit - resets 11:50pm"). They are different
    # populations - a genuine API error is a property of the run, a session limit is a
    # property of the account's day and is RETRYABLE - and merging them means a
    # partition by terminal_reason cannot tell "this trial failed" from "we ran out of
    # quota". It cost four trials in the first matrix, the whole 8-trial arena set in
    # this one, and a calibration trial in between.
    _final = (agent.get("result") or "")
    _reason = agent.get("terminal_reason")
    if _reason == "api_error" and "session limit" in _final.lower():
        _reason = "session_limit"
    rec["agent"] = {
        "is_error": bool(agent.get("is_error")),
        "subtype": agent.get("subtype"),
        "terminal_reason": _reason,
        "terminal_reason_raw": agent.get("terminal_reason"),
        "num_turns": agent.get("num_turns"),
        "permission_denials": len(agent.get("permission_denials") or []),
        "final_text": (agent.get("result") or "")[-3000:],
        "stderr": stderr[-2000:],
        **agent_metrics(agent),
    }
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
    if any(v != 0 for v in _cap.values()):
        print(f"  [capture] {tid} NON-ZERO evidence capture: {_cap} — the stored "
              f"submission may be incomplete", flush=True)
    rec["files_changed"] = len([ln for ln in
                                git(work, "status", "--porcelain=v1",
                                    "--untracked-files=all").splitlines() if ln.strip()])
    rec["finished_at"] = dt.datetime.now(dt.timezone.utc).isoformat()
    (run_dir / "trials").mkdir(parents=True, exist_ok=True)
    (run_dir / "trials" / f"{tid}.json").write_text(json.dumps(rec, indent=2))
    print(f"  [built] {tid}  {rec['wall_s']}s  ${rec['agent']['cost_usd']:.2f}  "
          f"turns={rec['agent']['num_turns']}  {rec['agent']['terminal_reason']}",
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
    games = a.games or list(P.TASKS)
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
    _manifest.write_manifest(run_dir, {
        "stacks": stacks, "games": games, "trials": a.trials, "model": MODEL,
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
             prompt_override, getattr(a, "turn_limit", None))
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

    print(f"{len(jobs)} trials = {len(games)} games x {len(stacks)} stacks x "
          f"{a.trials} trials, overall parallelism {a.parallel}, per-stack caps "
          f"{BUILD_CAP}\nwork root: {work_root}\n")

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
    # trials that died at 25-27 turns produced $7.61 for the arena game - a number that
    # described no trial that ever ran, was arithmetically correct, and manufactured the
    # finding "the arena task is too easy" that survived two rounds of scrutiny. The
    # completed-only mean was $13.62. `completed`, `max_turns`, `budget_exhausted`,
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
                  f"${r['agent'].get('cost_usd', 0):.2f}")
        print(f"  n={len(truncated)} excluded, n={len(scored_rows)} aggregated.\n")
    if not scored_rows:
        print("no trial reached terminal_reason=completed; there is nothing to "
              "aggregate. The per-trial table below is the whole result.")

    print(f"\n=== {run_dir.name}: {len(rows)} trials ({len(scored_rows)} aggregated, "
          f"{len(truncated)} not completed, {len(unmeasured)} unmeasured) ===\n")
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
           f"{'bot':>6} {'judge*':>7} {'turns':>6} {'$':>7} {'wall':>7}")
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
              f"{r['agent']['num_turns'] or 0:>6} {r['agent']['cost_usd']:>7.2f} "
              f"{r['wall_s']:>6.0f}s")

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

    print("\n--- per stack, averaged per game first then across games "
          f"(completed trials only, n={len(scored_rows)}) ---")
    by_stack: dict[str, dict[str, list[float]]] = {}
    for r in scored_rows:
        if r.get("eval"):
            by_stack.setdefault(r["stack"], {}).setdefault(r["game"], []).append(
                r["eval"]["overall"])
    for stack, per_game in sorted(by_stack.items()):
        means = [statistics.fmean(v) for v in per_game.values()]
        se = (statistics.stdev(means) / len(means) ** 0.5) if len(means) > 1 else float("nan")
        se_txt = f"{se:.3f}" if se == se else "  -"
        print(f"{stack:<8} score {statistics.fmean(means):.3f} +-SE {se_txt}  "
              f"(n={len(means)} games)")
    print("\nScores are averaged PER GAME first, then across games. Pooling across all "
          "trials is inconsistent (Miller, arXiv:2411.00640 sec 3).")

    print("\n* judge = DIAGNOSTIC ONLY, contributes nothing to `overall`.")
    print(f"\n--- per criterion, across {len(scored_rows)} completed trials "
          "(judge rows are diagnostic, not scored) ---")
    tally: dict[str, dict[str, list[int]]] = {}
    for r in scored_rows:
        e = r.get("eval")
        if not e:
            continue
        for tier in ("programmatic", "playbot", "judge"):
            for c in (e[tier] or {}).get("criteria", []):
                tally.setdefault(tier, {}).setdefault(c["id"], []).append(
                    int(bool(c["passed"])))
    for tier, crits in tally.items():
        print(f"\n[{tier}{' - DIAGNOSTIC, NOT SCORED' if tier == 'judge' else ''}]")
        for cid, vals in sorted(crits.items(), key=lambda kv: sum(kv[1]) / len(kv[1])):
            print(f"  {sum(vals)}/{len(vals)}  {cid}")

    print("\n--- terminal reasons ---")
    reasons: dict[tuple[str, str], int] = {}
    for r in rows:
        key = (r["stack"], str(r["agent"].get("terminal_reason")))
        reasons[key] = reasons.get(key, 0) + 1
    for (stack, reason), n in sorted(reasons.items()):
        print(f"{stack:<8} {reason:<28} {n}")

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

# Measured on this repo: the small spec-conformance bake-off ran 24 Opus trials at a
# median of ~$2.6 and 32-49 turns for a task that changed a few dozen lines. A
# whole-game build is a different order of magnitude, so the estimate below is scaled
# from those numbers rather than guessed, and the range is deliberately wide.
COST_PER_TRIAL = {"low": 12.0, "mid": 20.0, "high": 25.0}   # high == the hard cap
TURNS_PER_TRIAL = {"low": 90, "mid": 150, "high": 250}
BUILD_MIN_PER_TRIAL = {"rust": 95, "ts": 65, "unity": 80, "godot": 70}
EVAL_MIN_PER_TRIAL = {"rust": 14, "ts": 8, "unity": 16, "godot": 10}
JUDGE_COST_PER_TRIAL = 1.75   # MEASURED: two Sonnet-5 passes over a 95 KB pack plus 12
                              # frames cost $1.70 and took 30-31 turns each. The first
                              # estimate here was $0.35 and was wrong by 5x - the judge
                              # reads files and images with tools, it does not get one
                              # big prompt.


def cmd_plan(a: argparse.Namespace) -> int:
    stacks = a.stacks or list(P.STACKS)
    games = a.games or list(P.TASKS)
    n = len(stacks) * len(games) * a.trials
    print(f"matrix: {len(games)} games x {len(stacks)} stacks x {a.trials} trials "
          f"= {n} trials\n")
    print(f"{'':<10} {'low':>10} {'mid':>10} {'cap':>10}")
    print(f"{'agent $':<10} {n * COST_PER_TRIAL['low']:>10.0f} "
          f"{n * COST_PER_TRIAL['mid']:>10.0f} {n * COST_PER_TRIAL['high']:>10.0f}")
    print(f"{'judge $':<10} {n * JUDGE_COST_PER_TRIAL:>10.0f} "
          f"{n * JUDGE_COST_PER_TRIAL:>10.0f} {n * JUDGE_COST_PER_TRIAL:>10.0f}")
    print(f"{'TOTAL $':<10} {n * (COST_PER_TRIAL['low'] + JUDGE_COST_PER_TRIAL):>10.0f} "
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
    print("  * The per-trial cost band is scaled from measured small-task trials on")
    print("    this repo ($2.6 median, 32-49 turns) to a task perhaps 8-10x larger.")
    print("    It is an estimate. The hard caps are what actually bound the spend:")
    print(f"    --max-budget-usd {MAX_BUDGET_USD} and --max-turns {MAX_TURNS} per trial,")
    if MAX_BUDGET_USD is None:
        # THE STANDING CONFIGURATION HAS NO BUDGET CAP, and this line used to add it to
        # a float. `plan` therefore crashed with a TypeError for every reader after the
        # no-cap regime was adopted - the one command PROTOCOL.md tells you to run
        # before authorising a matrix. Nobody ran it, so nobody saw it.
        #
        # There is no dollar worst case without a cap. The honest bound is the turn
        # limit priced at a MEASURED per-turn rate, and it is stated as a range because
        # the measured rate varies 2.13x across cells (FINDINGS #42).
        lo, hi = 0.13, 0.20
        print(f"    and with NO budget cap the dollar worst case is not defined by a "
              f"flag.")
        print(f"    Priced from measured per-turn cost ({lo:.2f}-{hi:.2f} $/turn), "
              f"{MAX_TURNS} turns bounds ONE trial at ${MAX_TURNS * lo:.0f}-"
              f"${MAX_TURNS * hi:.0f},")
        print(f"    so the worst case for {n} trials is "
              f"${n * (MAX_TURNS * lo + JUDGE_COST_PER_TRIAL):.0f}-"
              f"${n * (MAX_TURNS * hi + JUDGE_COST_PER_TRIAL):.0f}. "
              f"No trial has ever come close: the most expensive measured is $72.83.")
    else:
        print(f"    so the WORST CASE for {n} trials is "
              f"${n * (MAX_BUDGET_USD + JUDGE_COST_PER_TRIAL):.0f}.")
    print("  * Run TWO trials in DIFFERENT cells first and re-run `plan` with the")
    print("    measured range - not one trial, and not a point estimate. Within-cell")
    print("    spread has been measured at 1.62x and across-cell at 2.13x (FINDINGS #42).")
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
        p.add_argument("--games", nargs="*", default=None, choices=list(P.TASKS))
        p.add_argument("--trials", type=int, default=2)
        p.add_argument("--parallel", type=int, default=4)
        p.add_argument("--eval-parallel", type=int, default=1)
        p.add_argument("--seed", type=int, default=7)
        # RETRY A SPECIFIC CELL, AND ONLY THAT CELL. `cmd_build` never consults
        # existing trial records and `prepare()` begins with `rmtree`, so re-running
        # a selection that includes completed trials DESTROYS them - sixteen
        # completed submissions worth $486 were one unscoped rerun away on
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
        p.add_argument("--no-judge", action="store_true")
        # The legacy 13-criterion judge is OPT-IN. It is weighted 0.00, cost a measured
        # $1.75 per submission, and across 24 submissions its only firings were
        # adjudicated as a frame-capture artifact (FINDINGS #26). Running it by default
        # spent ~$42 a matrix on a tier that carried no information.
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
    cc.add_argument("--game", required=True, choices=list(P.TASKS))
    cc.add_argument("--k", type=int, default=3)

    a = ap.parse_args()
    return {
        "plan": cmd_plan, "build": cmd_build, "evaluate": cmd_evaluate,
        "report": cmd_report, "concurrency-check": cmd_concurrency_check,
    }[a.cmd](a)


if __name__ == "__main__":
    raise SystemExit(main())
