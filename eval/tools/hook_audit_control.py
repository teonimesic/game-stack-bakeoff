#!/usr/bin/env python3
"""Can a stored trial tell a Stop gate that PASSED from a Stop gate that NEVER RAN?

WHY THIS EXISTS
---------------
Measured under task 78 at CLI 2.1.220, with the harness's own flags, in two arms costing
$0.03: a Stop hook that BLOCKS writes a `user` entry with `isMeta: true` beginning
`"Stop hook feedback:"` into the transcript, and the agent complies. A Stop hook that
EXITS 0 writes **nothing, anywhere**.

So across the whole stored archive, 19 transcripts carry a block and every one is dated
2026-08-11 or 2026-08-12. That single observation is equally consistent with

  * `just verify` was green at every stop, in every trial, in every run since; and
  * the hook never ran at all.

and no stored artifact separates them. Task 67 recorded the gate as "live in all four
arms" on the strength of the file being present in the starter — which is AGENTS.md
rule 2, never infer a process's state from its artifact's state.

The fix is an audit trail: `AGENTS.md`, *record the inputs a component actually consumed,
not merely the output it produced*. Each `verify-gate.sh` now appends one line per
invocation and one line per verdict to `$STARTER_HOOK_LOG`.

THE CONSTRAINT THAT MAKES THIS NON-TRIVIAL
------------------------------------------
**The trial tree BECOMES the graded diff.** A log written into the project directory
lands in `files_changed`, `diff.stat`, `tree.txt` and `submission.tar.gz` — which is the
shape of #106, a gate that rewrote the tree it was measuring. So the log has to land
outside the tree, the harness passes an absolute path there, and *that the log stays out
of the tree is itself a row here*, run in every arm rather than reasoned about.

THE DIRECTIONS, AND WHY EACH ONE IS NOT OPTIONAL
------------------------------------------------
| direction | asks | fails when |
|---|---|---|
| **green** | a passing gate records `pass` | the hook logs only when it blocks — the state task 78 was already in |
| **blocked** | a blocking gate records `block`, and still emits its JSON | logging broke the output contract |
| **cold** | a gate that SHORT-CIRCUITS on its warm guard records `skip` | the guard arm is the one no artifact could ever see |
| **distinct** | the three arms' logs differ pairwise | a log that says the same thing whatever happened is #45's shape: an instrument reporting itself |
| **clean** | no file appears in the project dir in ANY arm | the audit trail contaminates the thing it audits (#106) |
| **append** | a second invocation adds to the log, keeping the first | `>` instead of `>>` passes every single-run check above |
| **unset** | with no `$STARTER_HOOK_LOG`, still nothing in the project dir | the fallback address is the one nobody checks (rule 12) |
| **mutant** | with the log line deleted, `green` MUST fail | otherwise this file is `total=0 passed=0` |

`green`/`blocked`/`cold`/`distinct` are the mutant's half — can the check fail? `append`
and `unset` are the variant's half — can it still pass on an input it mishandles? Rule 15:
every false negative adjudicated in this project has been of the second kind.

The stack toolchains are NOT needed and are deliberately not used: `just` is a shim on
PATH that exits 0 or 1 on demand. This control is about the hook's bookkeeping, not about
whether `just verify` is right, and a real `verify` would make it a 20-minute test nobody
runs.

WHAT THIS FILE CANNOT ESTABLISH
-------------------------------
That the CLI passes `$STARTER_HOOK_LOG` through to a hook it spawns. That is a property
of the `claude` binary, it cannot be faked with a shim, and it is measured live once:
`--live` runs the real CLI against a throwaway project with the harness's own flags. It
costs about $0.02. Without it, every row below is a statement about bash.

Usage, from eval/:
    python3 tools/hook_audit_control.py                 # every starter, offline
    python3 tools/hook_audit_control.py --stack rust
    python3 tools/hook_audit_control.py --live          # + one real `claude` session

Exit: 0 every direction measured and green; 1 a direction FAILED; 2 bad usage.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

EVAL = Path(__file__).resolve().parent.parent
STARTERS = EVAL / "starters"
STACKS = ("rust", "ts", "unity", "godot")

#: stack -> directory the hook's warm guard tests for. `godot` guards on `just` being on
#: PATH instead, which is why its cold arm is a PATH change rather than a missing dir.
WARM_GUARD_DIR = {"rust": "target", "ts": "node_modules", "unity": "Library",
                  "godot": None}

#: The log line, spelled once. Tab-separated on purpose: every one of these hooks carries
#: a comment saying that building JSON by shell interpolation produced invalid JSON the
#: first time it was tried, and a malformed hook response is indistinguishable from no
#: hook at all. A path with a quote in it would do the same to a JSONL log.
FIELDS = 4  # ts, stack, event, detail


class Failure(Exception):
    pass


def _read_log(p: Path) -> list[list[str]]:
    if not p.exists():
        return []
    rows = []
    for ln in p.read_text().splitlines():
        if not ln.strip():
            continue
        parts = ln.split("\t")
        if len(parts) != FIELDS:
            raise Failure(f"log line has {len(parts)} fields, expected {FIELDS}: {ln!r}")
        rows.append(parts)
    return rows


def _events(rows: list[list[str]]) -> list[str]:
    return [r[2] for r in rows]


def _make_shim(d: Path, verify_rc: int) -> Path:
    """A `just` that exits `verify_rc` and prints something a block reason can carry."""
    d.mkdir(parents=True, exist_ok=True)
    j = d / "just"
    j.write_text("#!/bin/sh\n"
                 "echo \"SHIM just $*\"\n"
                 f"exit {verify_rc}\n")
    j.chmod(0o755)
    return d


def _project(root: Path, stack: str, warm: bool) -> Path:
    """A minimal git repo standing in for the trial tree.

    It is a git repo because the property under test is stated in git's terms: the trial
    tree becomes `git diff --cached HEAD`, so `git status --porcelain` answering empty is
    the same question the harness asks when it writes `files_changed`.
    """
    proj = root / "proj"
    proj.mkdir(parents=True, exist_ok=True)
    (proj / "justfile").write_text("verify:\n\t@true\n")
    guard = WARM_GUARD_DIR[stack]
    if warm and guard:
        (proj / guard).mkdir(exist_ok=True)
    subprocess.run(["git", "init", "-q"], cwd=proj, check=True)
    subprocess.run(["git", "add", "-A"], cwd=proj, check=True)
    subprocess.run(["git", "-c", "user.email=e@l", "-c", "user.name=e",
                    "commit", "-q", "-m", "baseline"], cwd=proj, check=True)
    return proj


def _run_hook(hook: Path, proj: Path, path_env: str, log: Path | None,
              extra_env: dict[str, str] | None = None) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env["PATH"] = path_env
    env["CLAUDE_PROJECT_DIR"] = str(proj)
    env.pop("STARTER_HOOK_LOG", None)
    if log is not None:
        env["STARTER_HOOK_LOG"] = str(log)
    env.update(extra_env or {})
    # check=False and the code is READ on the next lines: a hook that exits non-zero is
    # a finding, not an exception to swallow.
    return subprocess.run(["bash", str(hook)], cwd=proj, capture_output=True, text=True,
                          env=env, stdin=subprocess.DEVNULL, check=False)


def _tree_files(proj: Path) -> set[str]:
    return {str(p.relative_to(proj)) for p in proj.rglob("*")
            if p.is_file() and ".git/" not in str(p.relative_to(proj))}


def _assert_clean(proj: Path, before: set[str], arm: str) -> None:
    after = _tree_files(proj)
    new = after - before
    if new:
        raise Failure(f"{arm}: the hook wrote {sorted(new)} INSIDE the project dir - "
                      f"that lands in files_changed, diff.stat, tree.txt and the "
                      f"submission tarball (#106)")
    st = subprocess.run(["git", "status", "--porcelain=v1", "--untracked-files=all"],
                        cwd=proj, capture_output=True, text=True, check=True)
    if st.stdout.strip():
        raise Failure(f"{arm}: git sees changes after the hook ran:\n{st.stdout}")


def _arm(stack: str, hook: Path, arm: str, verify_rc: int, warm: bool,
         log_name: str | None = "hook_log.tsv") -> tuple[subprocess.CompletedProcess,
                                                         list[list[str]], Path]:
    """One hook invocation in a throwaway tree. Returns (proc, log rows, tmp root)."""
    root = Path(tempfile.mkdtemp(prefix=f"hookaudit-{stack}-{arm}-"))
    proj = _project(root, stack, warm)
    bindir = _make_shim(root / "bin", verify_rc)
    if stack == "godot" and not warm:
        # godot's warm guard is `command -v just`, so its cold arm is a PATH with no
        # `just` on it. /usr/bin:/bin still has date, and the cold path needs nothing else.
        path_env = "/usr/bin:/bin"
    else:
        path_env = f"{bindir}:{os.environ['PATH']}"
    log = (root / log_name) if log_name else None
    before = _tree_files(proj)
    proc = _run_hook(hook, proj, path_env, log)
    _assert_clean(proj, before, f"{stack}/{arm}")
    return proc, (_read_log(log) if log else []), root


def _check_green(stack: str, hook: Path) -> str:
    proc, rows, root = _arm(stack, hook, "green", 0, warm=True)
    try:
        if proc.returncode != 0:
            raise Failure(f"green: hook exited {proc.returncode}, expected 0")
        if proc.stdout.strip():
            raise Failure(f"green: hook printed {proc.stdout!r}; a passing Stop hook must "
                          f"be silent or the turn is blocked")
        ev = _events(rows)
        if ev != ["invoked", "pass"]:
            raise Failure(f"green: log events {ev}, expected ['invoked', 'pass'] - "
                          f"a green gate that records nothing is exactly the state "
                          f"task 78 measured and could not resolve")
        if rows[0][1] != stack:
            raise Failure(f"green: log names stack {rows[0][1]!r}, expected {stack!r}")
        # The address is an input to the check (rule 12): the log has to name WHICH
        # tree the gate ran in, or a trial cannot tell its own gate's log from a
        # neighbour's. Compared unresolved because that is exactly the string the
        # harness puts in CLAUDE_PROJECT_DIR - on macOS $TMPDIR resolves through
        # /private, and asserting the resolved form would fail a correct hook.
        if rows[0][3] != str(root / "proj"):
            raise Failure(f"green: log names project {rows[0][3]!r}, expected "
                          f"{str(root / 'proj')!r} - the address is an input to the check")
        return "\n".join("\t".join(r[1:]) for r in rows)
    finally:
        shutil.rmtree(root, ignore_errors=True)


def _check_blocked(stack: str, hook: Path) -> str:
    proc, rows, root = _arm(stack, hook, "blocked", 1, warm=True)
    try:
        if proc.returncode != 0:
            raise Failure(f"blocked: hook exited {proc.returncode}, expected 0")
        try:
            payload = json.loads(proc.stdout)
        except json.JSONDecodeError as e:
            raise Failure(f"blocked: stdout is not JSON ({e}); a malformed hook response "
                          f"is indistinguishable from no hook at all. Got: "
                          f"{proc.stdout[:200]!r}")
        if payload.get("decision") != "block":
            raise Failure(f"blocked: decision={payload.get('decision')!r}, expected 'block'")
        ev = _events(rows)
        if ev != ["invoked", "block"]:
            raise Failure(f"blocked: log events {ev}, expected ['invoked', 'block']")
        return "\n".join("\t".join(r[1:]) for r in rows)
    finally:
        shutil.rmtree(root, ignore_errors=True)


def _check_cold(stack: str, hook: Path) -> str:
    proc, rows, root = _arm(stack, hook, "cold", 0, warm=False)
    try:
        if proc.returncode != 0:
            raise Failure(f"cold: hook exited {proc.returncode}, expected 0")
        if proc.stdout.strip():
            raise Failure(f"cold: hook printed {proc.stdout!r}, expected silence")
        ev = _events(rows)
        if ev != ["invoked", "skip"]:
            raise Failure(f"cold: log events {ev}, expected ['invoked', 'skip'] - the "
                          f"warm guard short-circuiting is the arm NO stored artifact "
                          f"could ever see, and the one that would look like a green gate")
        if rows[1][3] in ("", "-"):
            raise Failure("cold: skip row names no guard; 'it skipped' without 'why' "
                          "cannot tell a cold build from a broken PATH")
        return "\n".join("\t".join(r[1:]) for r in rows)
    finally:
        shutil.rmtree(root, ignore_errors=True)


def _check_append(stack: str, hook: Path) -> None:
    """VARIANT. A hook using `>` passes every single-invocation row above.

    Two invocations in one tree, over a pre-seeded log. If the seed line or the first
    invocation is gone, the log is a last-write-wins snapshot and cannot count anything.
    """
    root = Path(tempfile.mkdtemp(prefix=f"hookaudit-{stack}-append-"))
    try:
        proj = _project(root, stack, warm=True)
        bindir = _make_shim(root / "bin", 0)
        log = root / "hook_log.tsv"
        seed = "SEED\tseed\tseed\tseed"
        log.write_text(seed + "\n")
        before = _tree_files(proj)
        path_env = f"{bindir}:{os.environ['PATH']}"
        for _ in range(2):
            p = _run_hook(hook, proj, path_env, log)
            if p.returncode != 0:
                raise Failure(f"append: hook exited {p.returncode}")
        _assert_clean(proj, before, f"{stack}/append")
        rows = _read_log(log)
        ev = _events(rows)
        if ev != ["seed", "invoked", "pass", "invoked", "pass"]:
            raise Failure(f"append: log events {ev}, expected the seed plus two "
                          f"invocations - the log is being overwritten, not appended, "
                          f"so it can never count how many times the gate ran")
    finally:
        shutil.rmtree(root, ignore_errors=True)


def _check_unset(stack: str, hook: Path) -> None:
    """VARIANT. With no `$STARTER_HOOK_LOG` the fallback address must still be outside
    the tree. A fallback of `.` or `$CLAUDE_PROJECT_DIR` contaminates every human run of
    the starter and every trial where the harness forgot to set the variable."""
    root = Path(tempfile.mkdtemp(prefix=f"hookaudit-{stack}-unset-"))
    try:
        proj = _project(root, stack, warm=True)
        bindir = _make_shim(root / "bin", 0)
        before = _tree_files(proj)
        p = _run_hook(hook, proj, f"{bindir}:{os.environ['PATH']}", None,
                      extra_env={"TMPDIR": str(root / "fallback") + os.sep})
        (root / "fallback").mkdir(exist_ok=True)
        p = _run_hook(hook, proj, f"{bindir}:{os.environ['PATH']}", None,
                      extra_env={"TMPDIR": str(root / "fallback") + os.sep})
        if p.returncode != 0:
            raise Failure(f"unset: hook exited {p.returncode}")
        _assert_clean(proj, before, f"{stack}/unset")
        fallback = list((root / "fallback").glob("*"))
        if not fallback:
            raise Failure("unset: nothing written to the TMPDIR fallback either - with "
                          "no log at all this hook is back to leaving no trace")
    finally:
        shutil.rmtree(root, ignore_errors=True)


def _check_mutant(stack: str, hook: Path) -> None:
    """Delete the logging and require `green` to go RED. Without this row, every row
    above could be passing for a reason that has nothing to do with the hook."""
    root = Path(tempfile.mkdtemp(prefix=f"hookaudit-{stack}-mutant-"))
    try:
        src = hook.read_text()
        lines = [ln for ln in src.splitlines(keepends=True)
                 if not ln.strip().startswith("hook_log ")]
        if len(lines) == len(src.splitlines(keepends=True)):
            raise Failure("mutant: found no `hook_log ` call to remove - the mutation "
                          "did not apply, so the row below would pass for the wrong "
                          "reason (this is the control that failed in task 78's set)")
        mutant = root / "verify-gate.sh"
        mutant.write_text("".join(lines))
        try:
            _check_green(stack, mutant)
        except Failure:
            return
        raise Failure("mutant: `green` still PASSED with every hook_log call deleted - "
                      "this control cannot fail and measures nothing (rule 1)")
    finally:
        shutil.rmtree(root, ignore_errors=True)


def check_stack(stack: str) -> list[str]:
    hook = STARTERS / stack / ".claude" / "hooks" / "verify-gate.sh"
    if not hook.exists():
        return [f"{stack:6s} FAILED  no verify-gate.sh at {hook}"]
    out: list[str] = []
    logs: dict[str, str] = {}
    for name, fn in (("green", _check_green), ("blocked", _check_blocked),
                     ("cold", _check_cold)):
        try:
            logs[name] = fn(stack, hook)
            out.append(f"{stack:6s} {name:8s} ok")
        except Failure as e:
            out.append(f"{stack:6s} {name:8s} FAILED  {e}")
    if len(logs) == 3:
        if len(set(logs.values())) != 3:
            same = [k for k in logs if list(logs.values()).count(logs[k]) > 1]
            out.append(f"{stack:6s} distinct FAILED  arms {sorted(same)} left "
                       f"IDENTICAL logs - a trail that says the same thing whatever "
                       f"happened is reporting the instrument, not the run (rule 9)")
        else:
            out.append(f"{stack:6s} distinct ok      three arms, three distinct logs")
    for name, fn in (("append", _check_append), ("unset", _check_unset),
                     ("mutant", _check_mutant)):
        try:
            fn(stack, hook)
            out.append(f"{stack:6s} {name:8s} ok")
        except Failure as e:
            out.append(f"{stack:6s} {name:8s} FAILED  {e}")
    return out


# --------------------------------------------------------------------------- #
# The harness half: the address it chooses, and what a grader would see
# --------------------------------------------------------------------------- #


def _wholegame():
    """THE HARNESS ITSELF, imported rather than restated. A second spelling of the log's
    name or of the guard is how the address and the check drift apart (rule 12)."""
    sys.path.insert(0, str(EVAL))
    import wholegame
    return wholegame


def check_harness() -> list[str]:
    wg = _wholegame()
    out: list[str] = []
    root = Path(tempfile.mkdtemp(prefix="hookaudit-harness-"))
    try:
        work = root / "work"
        art = root / "art"
        work.mkdir()
        art.mkdir()
        # GREEN: an artifact dir beside the tree is accepted, and names the log.
        p = wg.hook_log_path(art, work)
        if p != (art / wg.HOOK_LOG_NAME).resolve():
            out.append(f"harness path     FAILED  got {p}")
        else:
            out.append("harness path     ok      log addressed outside the trial tree")
        # RED: the same call with the artifact dir INSIDE the tree must refuse to launch.
        inside = work / "artifacts"
        inside.mkdir()
        try:
            wg.hook_log_path(inside, work)
            out.append("harness guard    FAILED  accepted a log path INSIDE the trial "
                       "tree - the tree becomes the graded diff (#106), so this must "
                       "refuse to launch rather than contaminate a submission")
        except SystemExit:
            out.append("harness guard    ok      refuses a log path inside the tree")
        # THREE VALUES. `absent` is not `no invocations` and neither is `passed`.
        missing = wg.read_hook_log(art / "nope.tsv")
        seeded = art / "seed.tsv"
        seeded.write_text("T\trust\tinvoked\t/w\nT\trust\tpass\t-\n"
                          "T\trust\tinvoked\t/w\nT\trust\tblock\t-\nbroken line\n")
        got = wg.read_hook_log(seeded)
        if missing["log"] != "absent":
            out.append(f"harness absent   FAILED  {missing}")
        elif got != {"log": "present", "path": str(seeded), "invocations": 2,
                     "verdicts": {"pass": 1, "block": 1}, "malformed_lines": 1}:
            out.append(f"harness summary  FAILED  {got}")
        else:
            out.append("harness summary  ok      absent / 2 invocations / pass+block / "
                       "1 malformed all reported separately")
    finally:
        shutil.rmtree(root, ignore_errors=True)
    return out


def check_grader_view(stack: str) -> list[str]:
    """The ticket's literal question: would a GRADER see the log?

    `diff.stat`, `tree.txt` and `submission.tar.gz` are the three artifacts a stored
    submission is read through, and they are produced here by the same three commands
    `wholegame.build_trial` runs. The hook is invoked with the harness's own chosen
    address in between.
    """
    wg = _wholegame()
    hook = STARTERS / stack / ".claude" / "hooks" / "verify-gate.sh"
    root = Path(tempfile.mkdtemp(prefix=f"hookaudit-grader-{stack}-"))
    try:
        proj = _project(root, stack, warm=True)
        art = root / "art"
        art.mkdir()
        log = wg.hook_log_path(art, proj)
        bindir = _make_shim(root / "bin", 0)
        p = _run_hook(hook, proj, f"{bindir}:{os.environ['PATH']}", Path(log))
        if p.returncode != 0:
            return [f"{stack:6s} grader   FAILED  hook exited {p.returncode}"]
        if not Path(log).exists():
            return [f"{stack:6s} grader   FAILED  no log at {log}; the row below would "
                    f"pass because nothing was written, not because nothing leaked"]
        subprocess.run(["git", "add", "-A"], cwd=proj, capture_output=True, check=True)
        stat = subprocess.run(["git", "diff", "--cached", "HEAD", "--stat"], cwd=proj,
                              capture_output=True, text=True, check=True).stdout
        tar = root / "submission.tar.gz"
        subprocess.run(["tar", "--exclude=./.git", "-czf", str(tar), "."], cwd=proj,
                       capture_output=True, check=True)
        names = subprocess.run(["tar", "-tzf", str(tar)], capture_output=True, text=True,
                               check=True).stdout
        tree = subprocess.run(["find", ".", "-type", "f", "-not", "-path", "./.git/*"],
                              cwd=proj, capture_output=True, text=True, check=True).stdout
        hit = [n for n, blob in (("diff.stat", stat), ("submission.tar.gz", names),
                                 ("tree.txt", tree)) if wg.HOOK_LOG_NAME in blob]
        if hit:
            return [f"{stack:6s} grader   FAILED  the Stop-hook log appears in {hit}"]
        return [f"{stack:6s} grader   ok      log written, and absent from diff.stat, "
                f"tree.txt and submission.tar.gz"]
    finally:
        shutil.rmtree(root, ignore_errors=True)


def check_build_trial() -> list[str]:
    """THE WIRING, through `wholegame.build_trial` itself rather than around it.

    Everything above tests the hook and the two helper functions. None of it touches the
    line that actually puts `STARTER_HOOK_LOG` into the trial environment, the line that
    summarises the log into the record, or the leak row - and a helper that works, called
    from nowhere, is #133's shape.

    `run_agent` is replaced by a stand-in that writes the lines a hook would have written,
    because the real one costs $11-73. The substitution is ASSERTED to have taken effect
    before anything is concluded from it: a monkeypatch that silently missed is on this
    project's list of five same-day rule-12 failures, and it looks exactly like a result.
    """
    wg = _wholegame()
    out: list[str] = []
    root = Path(tempfile.mkdtemp(prefix="hookaudit-buildtrial-"))
    try:
        starter = root / "starter"
        starter.mkdir()
        (starter / "MARKER.txt").write_text("fake starter\n")
        run_dir = root / "run"
        work_root = root / "work"

        seen: dict[str, str] = {}

        def fake_run_agent(work, prompt, env, turn_limit=None):
            seen["log"] = env.get("STARTER_HOOK_LOG", "")
            seen["marker"] = str((work / "MARKER.txt").exists())
            if seen["log"]:
                with open(seen["log"], "a") as fh:
                    fh.write("T\trust\tinvoked\t%s\n" % work)
                    fh.write("T\trust\tskip\tcold_build_no_target_dir\n")
                    fh.write("T\trust\tinvoked\t%s\n" % work)
                    fh.write("T\trust\tpass\t-\n")
            (work / "authored.txt").write_text("the agent's work\n")
            return {"type": "result", "result": "done", "num_turns": 1,
                    "terminal_reason": "completed", "modelUsage": {}}, ""

        real_run_agent, real_starter = wg.run_agent, wg.STARTERS["rust"]
        wg.run_agent, wg.STARTERS["rust"] = fake_run_agent, starter
        try:
            rec = wg.build_trial(run_dir, work_root, "rust", "g1_pong", 0,
                                 wg.Caps({"rust": 1}, 1), None,
                                 prompt_override="unused", turn_limit=1)
        finally:
            wg.run_agent, wg.STARTERS["rust"] = real_run_agent, real_starter

        if seen.get("marker") != "True":
            return ["harness trial   FAILED  the starter substitution did not take effect "
                    f"(MARKER.txt present in the work tree: {seen.get('marker')}), so "
                    f"nothing below would be measuring what it names"]
        out.append("harness trial   ok      substitution took effect (fake starter in the "
                   "work tree)")
        if not seen.get("log"):
            out.append("harness env     FAILED  build_trial did not put STARTER_HOOK_LOG "
                       "into the trial environment - the hook would write to $TMPDIR and "
                       "no run directory would ever collect it")
        else:
            out.append(f"harness env     ok      STARTER_HOOK_LOG set to "
                       f"...{seen['log'][-40:]}")
        sh = rec.get("stop_hook", {})
        want = {"log": "present", "invocations": 2,
                "verdicts": {"skip": 1, "pass": 1}, "malformed_lines": 0,
                "leaked_into_tree": []}
        got = {k: sh.get(k) for k in want}
        if got != want:
            out.append(f"harness record  FAILED  trials/*.json stop_hook is {got}, "
                       f"expected {want}")
        else:
            out.append("harness record  ok      stop_hook: 2 invocations, skip+pass, "
                       "nothing leaked")
        # RED for the leak row. Nothing above could distinguish "no leak" from "the row is
        # incapable of reporting one" - rule 1.
        tid = rec["trial_id"]
        art = run_dir / "artifacts" / tid
        planted = f"./{wg.HOOK_LOG_NAME}"
        blob = (art / "tree.txt").read_text() + planted + "\n"
        leak = sorted({ln for ln in blob.splitlines() if wg.HOOK_LOG_NAME in ln})
        if leak != [planted]:
            out.append(f"harness leakred FAILED  the leak matcher found {leak} in a tree "
                       f"listing that contains {planted}; it cannot report a real one")
        else:
            out.append("harness leakred ok      the leak matcher reports a planted "
                       "hook_log.tsv in the tree listing")
    finally:
        shutil.rmtree(root, ignore_errors=True)
    return out


# --------------------------------------------------------------------------- #
# The live direction: does the CLI hand $STARTER_HOOK_LOG to a hook it spawns?
# --------------------------------------------------------------------------- #

LIVE_FLAGS = ["--setting-sources", "project", "--strict-mcp-config",
              "--exclude-dynamic-system-prompt-sections",
              "--permission-mode", "acceptEdits"]


def live_check() -> list[str]:
    """One real `claude` session, harness flags, throwaway project. ~$0.02.

    A shim cannot answer this: whether a custom environment variable set on the CLI's
    parent reaches a Stop hook the CLI spawns is a property of the CLI binary. Every
    offline row above is a statement about bash until this one runs.
    """
    root = Path(tempfile.mkdtemp(prefix="hookaudit-live-"))
    try:
        proj = root / "proj"
        (proj / ".claude" / "hooks").mkdir(parents=True)
        log = root / "outside.tsv"
        hook = proj / ".claude" / "hooks" / "verify-gate.sh"
        hook.write_text(
            "#!/usr/bin/env bash\n"
            "set -uo pipefail\n"
            'printf "%s\\t%s\\t%s\\t%s\\n" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" live '
            'invoked "${CLAUDE_PROJECT_DIR:-unset}" '
            '>> "${STARTER_HOOK_LOG:-${TMPDIR:-/tmp}/starter-verify-gate.tsv}"\n'
            "exit 0\n")
        hook.chmod(0o755)
        (proj / ".claude" / "settings.json").write_text(json.dumps(
            {"hooks": {"Stop": [{"matcher": "", "hooks": [
                {"type": "command",
                 "command": "$CLAUDE_PROJECT_DIR/.claude/hooks/verify-gate.sh"}]}]}}))
        env = dict(os.environ)
        env["STARTER_HOOK_LOG"] = str(log)
        before = {p.name for p in proj.rglob("*") if p.is_file()}
        p = subprocess.run(
            ["claude", "-p", "Reply with the single word: ok", "--output-format", "json",
             "--max-turns", "2", "--session-id", str(uuid.uuid4()), *LIVE_FLAGS],
            cwd=proj, capture_output=True, text=True, env=env, check=False, timeout=600)
        out = [f"live   cli exit {p.returncode}"]
        rows = _read_log(log)
        if not rows:
            out.append("live   env      FAILED  $STARTER_HOOK_LOG did NOT reach the "
                       "hook - nothing was written to the path the harness set. Every "
                       "offline row above is about bash, not about a trial.")
        else:
            out.append(f"live   env      ok      {len(rows)} invocation(s) logged "
                       f"outside the tree; project={rows[0][3]}")
        after = {q.name for q in proj.rglob("*") if q.is_file()}
        if after - before:
            out.append(f"live   clean    FAILED  new files in the project dir: "
                       f"{sorted(after - before)}")
        else:
            out.append("live   clean    ok      nothing new inside the project dir")
        # `--output-format json` returns a STREAM of typed events, not one object, so
        # `json.loads(...).get("total_cost_usd")` reads an array and comes back with
        # nothing. The harness already owns the one correct reader; do not write a second.
        try:
            out.append(f"live   cost     "
                       f"${_wholegame().parse_agent(p.stdout).get('total_cost_usd')}")
        except Exception as e:  # noqa: BLE001 - a cost we cannot read is reported, not hidden
            out.append(f"live   cost     UNREAD ({e}); stdout head: {p.stdout[:120]!r}")
        return out
    finally:
        shutil.rmtree(root, ignore_errors=True)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--stack", choices=STACKS, action="append",
                    help="limit to one stack; repeatable")
    ap.add_argument("--live", action="store_true",
                    help="also run one real `claude` session (~$0.02)")
    args = ap.parse_args(argv)

    lines: list[str] = []
    for s in (args.stack or list(STACKS)):
        lines += check_stack(s)
        lines += check_grader_view(s)
    lines += check_harness()
    lines += check_build_trial()
    if args.live:
        lines += live_check()
    for ln in lines:
        print(ln)
    failed = [ln for ln in lines if "FAILED" in ln]
    print(f"\n{len(lines) - len(failed)} ok, {len(failed)} FAILED")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
