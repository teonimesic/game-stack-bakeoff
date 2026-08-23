#!/usr/bin/env python3
"""
The spec-change harness. RETIRED as a way to LAUNCH trials on 2026-08-23; still
the way to READ the ones it launched, and still the home of the capture policy.

WHAT IS GONE AND WHAT IS NOT
  * The four trees this drove - `template/`, `template-ts/`, `template-unity/`,
    `template-godot/` - were deleted on 2026-08-23. `run` and `check-suite`
    therefore have no `--template` to point at and refuse to start; `main()`
    says so rather than letting `copytree` raise. The trees are recoverable from
    git (`git log -- template-ts`), which is why deleting them was safe.
  * `report` still reads `runs/<name>/`, and `regrade.py` still recomputes
    verdicts over the 71 stored trials in 12 spec-change run directories.
  * `judge/static.py` imports this module's capture policy by path. That is a
    LIVE dependency of the whole-game grader and the reason this file stays
    whole: two truncation policies in one repository is #100, which came back
    as #114.
  * The task text the 71 trials were given is NOT in any of them - the record
    stores `task: "t1_rally"` and nothing else. `suites/*.toml` and
    `suites/prompts.py` are the sole copy, so they stay (#119).

Measures how well a blank Claude Code session performs game-dev tasks inside a
template, so the template and its instructions can be iterated on empirically.

Design decisions, each traceable to research/05-eval-harness-design.md:

  * `--setting-sources project` is MANDATORY. Verified empirically: without it
    the user's global ~/.claude/CLAUDE.md leaks into every run. Since that file
    mandates TDD, it would mask the effect of any TDD guidance in the template.

  * Cost/tokens come from `modelUsage`, NOT `usage`. The SDK type docs say
    `usage` is "MAIN AGENT LOOP ONLY - excludes Task subagent, sidechain, and
    auxiliary model calls" and explicitly say to prefer `modelUsage`.

  * `terminal_reason` is recorded and reported separately. It distinguishes
    "agent finished" (completed) from "we cut it off" (max_turns,
    budget_exhausted) from "it broke" (model_error, api_error). A naive
    pass/fail harness merges four outcomes into "fail" and turns the A/B into
    noise.

  * Held-out tests are copied in AFTER the agent finishes, and any agent edit to
    a protected path is reverted before grading (SWE-bench's approach: the
    agent's edits to tests are discarded by construction, and a missing test
    counts as failed).

  * Scores are CONTINUOUS (fraction of held-out tests passing) as well as
    binary. With realistic task counts a binary score has a minimum detectable
    effect of 15-25pp; continuous scores have far lower variance.

  * `check-suite` runs every task's held-out tests against the pristine template
    and FAILS if they already pass. SWE-smith's rule: a task is only a task if
    you can prove the target tests fail before the fix.

Usage:
    ./runner.py report --run-dir runs/<name>          # still works

    ./runner.py check-suite --suite ... --template ...   # needs a template tree
    ./runner.py run         --suite ... --template ...   # there is no longer one
"""

from __future__ import annotations

import argparse
import concurrent.futures as futures
import dataclasses
import datetime as dt
import json
import math
import re
import shutil
import statistics
import subprocess
import sys
import tomllib
import uuid
from pathlib import Path
from typing import Any

# --------------------------------------------------------------------------- #
# Task / suite model
# --------------------------------------------------------------------------- #


@dataclasses.dataclass
class Task:
    id: str
    prompt: str
    # Held-out grading: files copied into the repo AFTER the agent stops, and the
    # command that runs them. The agent never sees these.
    holdout_src: str
    holdout_cmd: str
    # Paths the agent may modify. A change outside this set is tampering.
    allowed_paths: list[str] = dataclasses.field(default_factory=list)
    # Paths reverted to pristine before grading, no matter what the agent did.
    protected_paths: list[str] = dataclasses.field(
        default_factory=lambda: ["crates/*/tests/**", ".config/**", "justfile"]
    )
    # The command the agent is told to use. Run before grading to capture what
    # the agent itself believed.
    verify_cmd: str = "just verify"
    # Run once in a fresh copy before the agent starts, and before the negative
    # control. Needed for stacks whose dependencies are not vendored into the
    # repo (e.g. `pnpm install`). Without it a TypeScript control "fails" because
    # the test runner is missing, not because the feature is missing - which
    # looks identical in the report and is exactly the false confidence this
    # harness exists to prevent.
    setup_cmd: str | None = None
    max_turns: int = 60
    max_budget_usd: float = 4.0
    model: str = "fable"
    timeout_s: int = 2400
    notes: str = ""


@dataclasses.dataclass
class Suite:
    name: str
    tasks: list[Task]
    arms: dict[str, dict[str, Any]]


def load_suite(path: Path) -> Suite:
    with path.open("rb") as fh:
        raw = tomllib.load(fh)
    tasks = [Task(**t) for t in raw.get("task", [])]
    arms = raw.get("arms") or {"baseline": {}}
    return Suite(name=raw.get("name", path.stem), tasks=tasks, arms=arms)


# --------------------------------------------------------------------------- #
# Shell helpers
# --------------------------------------------------------------------------- #


# A shared cargo target directory across trials. Without it every trial pays a
# full cold Bevy build (~4 minutes measured), which dwarfs the agent's own time.
#
# MEASURED HAZARD: cargo file-locks this directory, so CONCURRENT trials block
# on each other with "Blocking waiting for file lock on build directory". That
# starves the agent's own `just verify`, and it gives up with the work
# unfinished while still reporting terminal_reason=completed. Two trials failed
# exactly this way before it was diagnosed.
#
# => Run trials SERIALLY when sharing a target dir (--parallel 1, the default).
# If you want parallelism, give each trial its own CARGO_TARGET_DIR and accept
# the cold-build cost.
PRISTINE_TARGET = Path(__file__).parent.resolve() / "runs" / "_cargo-target-pristine"


def trial_env(target_dir: Path | None = None) -> dict[str, str]:
    """Environment for a trial, with an ISOLATED cargo target directory.

    MEASURED HAZARD (this cost a false negative-control pass): sharing one target
    directory across trials lets cargo serve a test binary compiled against a
    DIFFERENT trial's source. The `t3_powerup` held-out tests reported 4/4
    passing on a pristine template that does not define `Powerup` at all — the
    binary came from an earlier trial where an agent had implemented it. A
    grader that can read another trial's artifacts is not a grader.

    So every trial gets its own target dir, cloned from a pristine warm cache.
    On APFS `cp -Rc` is a copy-on-write clone: 8.8 GB in ~2.5 s, near-zero extra
    disk. Isolation at the price of a rounding error.
    """
    import os

    env = dict(os.environ)
    if target_dir is not None:
        env["CARGO_TARGET_DIR"] = str(target_dir)
    return env


def clone_pristine_target(dest: Path) -> Path | None:
    """Copy-on-write clone of the warm cache. Returns None if unavailable, in
    which case the trial just pays a cold build - slow but still correct."""
    if not PRISTINE_TARGET.exists():
        return None
    if dest.exists():
        shutil.rmtree(dest, ignore_errors=True)
    dest.parent.mkdir(parents=True, exist_ok=True)
    # check=False on both: a failed clone is a documented outcome (None -> cold build),
    # and the first call's non-zero status is the trigger for the non-CoW fallback.
    # Both statuses are read on the lines below.
    r = subprocess.run(["cp", "-Rc", str(PRISTINE_TARGET), str(dest)],
                       capture_output=True, text=True, check=False)
    if r.returncode != 0:  # non-APFS filesystem, or out of space
        r = subprocess.run(["cp", "-R", str(PRISTINE_TARGET), str(dest)],
                           capture_output=True, text=True, check=False)
    return dest if r.returncode == 0 else None


#: WHAT A STORED COMMAND CAPTURE SAMPLES, AND WHAT IT DROPS.
#:
#: A truncation policy is a sampling policy, so this one states what it takes. Per stream,
#: independently: the FIRST `STREAM_HEAD_CHARS` characters and the LAST `STREAM_TAIL_CHARS`.
#: What is dropped is the MIDDLE of a stream that exceeds the two together, replaced by a
#: marker naming exactly how many characters and lines went. The full length of each stream
#: is stored beside the sample, so "what was dropped" is a recorded number rather than an
#: inference from a string that happens to be 4000 long.
#:
#: The head, because a compiler's first diagnostic and a runner's banner are there. The tail,
#: weighted heavier, because verdicts are: `Summary [...] 41 tests run`, the last failing
#: assertion, and every template's `✅ verify passed`.
#:
#: The budget is PER STREAM and that is the point of #100/#114. Before this, `sh` merged
#: `stdout + stderr` into ONE buffer and `run_trial` kept its last 4000 (`self_verify`) or
#: 5000 (`holdout`) characters, so a command that floods one stream discarded the whole of
#: the other. Of 26 stored spec-change records with `self_verify` exit 0, the 2 missing the
#: recipe's own completion line are exactly the 2 that hit the 4000 cap, both on the Rust
#: template, because `cargo-nextest` writes its progress to stderr. Raising a cap would only
#: move that boundary - the rule that stdout is sacrificed first would survive it, still
#: correlated with a stack by a property nobody chose.
#:
#: THIS IS THE ONE COPY. `judge/static.py` imports these three names rather than defining its
#: own, so the grader's records and this harness's records cannot drift apart; two truncation
#: policies in one repository is the defect that produced #100 in the first place.
#: `runner_capture_selftest.py` and `judge/capture_selftest.py` pin the two entry points, and
#: the former asserts they are the SAME function object.
STREAM_HEAD_CHARS = 1000
STREAM_TAIL_CHARS = 3000

#: The keys a capture contributes to a stored record. Named so a reader can separate the
#: capture from whatever else the record carries (`passed`, `score`, test counts).
CAPTURE_FIELDS = ("stdout", "stderr", "stdout_chars", "stderr_chars", "note")


def _sample_stream(text: str, head: int = STREAM_HEAD_CHARS,
                   tail: int = STREAM_TAIL_CHARS) -> str:
    if len(text) <= head + tail:
        return text
    middle = text[head:len(text) - tail]
    return (f"{text[:head]}\n"
            f"... [{len(middle)} characters, {middle.count(chr(10))} lines elided from the "
            f"middle of this stream] ...\n"
            f"{text[len(text) - tail:]}")


def capture_fields(out: str, err: str, note: str = "",
                   sample: Any = None) -> dict[str, Any]:
    """The five capture keys, for either harness.

    `sample` exists as a seam: `judge/static.py` passes its own module-level alias so a
    mutant can replace the sampler there and still be caught. Nothing else should pass it.
    """
    s = sample or _sample_stream
    return {"stdout": s(out), "stderr": s(err),
            "stdout_chars": len(out), "stderr_chars": len(err),
            "note": note or None}


def stored_stdout(rec: dict[str, Any]) -> str | None:
    """The stdout sample of a stored command record, or None if it cannot be known.

    None for a record written before the repair: those merged the two streams before
    truncating, so a missing line there is not evidence the command did not print it. Any
    check over the stored corpus has to treat those as UNMEASURABLE rather than as empty -
    the same distinction `pack_completeness` draws, and for the same reason. Stored records
    cannot be repaired, because the discarded stdout was never written down.
    """
    return rec.get("stdout") if "stdout_chars" in rec else None


def stored_output(rec: dict[str, Any]) -> str:
    """Everything textual in a stored command record, either shape, for a human or a grep."""
    if "stdout_chars" in rec:
        return "".join(p for p in (rec.get("stdout") or "", rec.get("stderr") or "",
                                   rec.get("note") or "") if p)
    return rec.get("tail") or ""


@dataclasses.dataclass
class Sh:
    """One command run by the spec-change harness: its status, and both its streams.

    Which stream a line came from is a recorded fact here, not something a reader has to
    infer from a merged buffer.
    """
    code: int
    #: EXACTLY what the child wrote, per stream.
    out: str = ""
    err: str = ""
    #: The HARNESS's own words - so far only a timeout. Kept apart from the two streams so
    #: nothing the harness says is ever attributed to the command, and so a timeout no
    #: longer erases what the command had already printed.
    note: str = ""

    @property
    def text(self) -> str:
        """The pre-#114 view: stdout then stderr, or the harness's note alone.

        `parse_test_counts`, `parse_skipped` and every diagnostic print read this, and it is
        preserved BYTE FOR BYTE - including a timeout replacing the output rather than
        appending to it - so that repairing the stored record cannot move a single score.
        The separated streams are what gets STORED; this is what gets PARSED.
        """
        return self.note if self.note else self.out + self.err

    def record(self, **extra: Any) -> dict[str, Any]:
        """What `run_trial` stores: the exit code, the capture, and the caller's own fields."""
        return {"exit": self.code, **capture_fields(self.out, self.err, self.note), **extra}


def _as_text(x: Any) -> str:
    """`TimeoutExpired.stdout` is bytes on POSIX even in text mode, and None on Windows."""
    if x is None:
        return ""
    return x.decode("utf-8", "replace") if isinstance(x, bytes) else str(x)


def sh(cmd: str, cwd: Path, timeout_s: int = 1800,
       target_dir: Path | None = None) -> Sh:
    # check=False: this function's whole contract is to HAND BACK the exit code. A
    # non-zero build or test is the measurement, not an error.
    try:
        p = subprocess.run(
            cmd, cwd=cwd, shell=True, capture_output=True, text=True,
            timeout=timeout_s, env=trial_env(target_dir), check=False,
        )
        return Sh(p.returncode, p.stdout, p.stderr)
    except subprocess.TimeoutExpired as ex:
        # Whatever the child had already printed is kept; `text` is still the note alone.
        return Sh(124, _as_text(ex.stdout), _as_text(ex.stderr),
                  note=f"TIMEOUT after {timeout_s}s")


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=repo, capture_output=True, text=True, check=False
    ).stdout


# --------------------------------------------------------------------------- #
# Test-count parsing -> continuous score
# --------------------------------------------------------------------------- #

# cargo-nextest: "Summary [   0.017s] 7 tests run: 7 passed, 0 skipped"
#                "Summary [   0.02s] 8 tests run: 6 passed, 2 failed, 0 skipped"
NEXTEST_SUMMARY = re.compile(
    r"Summary\s*\[[^\]]*\]\s*(\d+)\s+tests?\s+run:\s*(\d+)\s+passed"
    r"(?:,\s*(\d+)\s+failed)?"
)
# libtest: "test result: ok. 7 passed; 0 failed; 0 ignored"
LIBTEST_SUMMARY = re.compile(
    r"test result:\s*\w+\.\s*(\d+)\s+passed;\s*(\d+)\s+failed"
)
# vitest: "Tests  1 failed | 2 passed (3)" or "Tests  3 passed (3)"
VITEST_SUMMARY = re.compile(r"Tests\s+(?:(\d+)\s+failed\s*\|\s*)?(\d+)\s+passed\s*\((\d+)\)")
# NUnit / Unity results.xml attributes
NUNIT_SUMMARY = re.compile(r'total="(\d+)"\s+passed="(\d+)"\s+failed="(\d+)"')
# Godot template's own summary: "TESTS total=18 passed=18 failed=0"
GODOT_SUMMARY = re.compile(r"TESTS\s+total=(\d+)\s+passed=(\d+)\s+failed=(\d+)")
# Unity template's own summary: "holdout: 2 passed, 1 failed, 0 skipped (of 3, 0.1s)"
UNITY_SUMMARY = re.compile(r"(\d+)\s+passed,\s*(\d+)\s+failed,\s*(\d+)\s+skipped\s*\(of\s+(\d+)")


SKIP_PATTERNS = [
    re.compile(r"skipped=(\d+)"),                      # Godot template summary
    re.compile(r"(\d+)\s+skipped"),                    # nextest / vitest / Unity
    re.compile(r"(\d+)\s+ignored"),                    # libtest
]


def parse_skipped(output: str) -> int:
    """Held-out tests that SKIPPED rather than ran.

    A skip is zero coverage, not a pass. The rendering layer in every stack can
    skip when no GPU adapter or display is available, and counting that as
    success would let a trial score full marks having verified nothing. Any
    skip in a graded run is treated as a grading failure, not an agent failure.
    """
    for pat in SKIP_PATTERNS:
        hits = [int(m.group(1)) for m in pat.finditer(output)]
        if hits:
            return max(hits)
    return 0


def parse_test_counts(output: str) -> tuple[int, int]:
    """Return (passed, total). (0, 0) when nothing could be parsed."""
    passed = total = 0
    for m in NEXTEST_SUMMARY.finditer(output):
        total += int(m.group(1))
        passed += int(m.group(2))
    if total:
        return passed, total
    for m in LIBTEST_SUMMARY.finditer(output):
        p, f = int(m.group(1)), int(m.group(2))
        passed += p
        total += p + f
    if total:
        return passed, total
    for m in VITEST_SUMMARY.finditer(output):
        passed += int(m.group(2))
        total += int(m.group(3))
    if total:
        return passed, total
    for m in GODOT_SUMMARY.finditer(output):
        total += int(m.group(1))
        passed += int(m.group(2))
    if total:
        return passed, total
    for m in UNITY_SUMMARY.finditer(output):
        passed += int(m.group(1))
        total += int(m.group(4))
    if total:
        return passed, total
    for m in NUNIT_SUMMARY.finditer(output):
        total += int(m.group(1))
        passed += int(m.group(2))
    return passed, total


# --------------------------------------------------------------------------- #
# Anti-gaming
# --------------------------------------------------------------------------- #

CHEAT_PATTERNS: list[tuple[str, str]] = [
    (r"#\[ignore\]", "added #[ignore] to a Rust test"),
    (r"#\[cfg\(ignore\)\]", "cfg-ignored a test"),
    (r"--no-verify", "attempted to bypass git hooks"),
    (r"assert!\(\s*true\s*\)", "replaced an assertion with a tautology"),
    (r"assert_eq!\(\s*(\w+)\s*,\s*\1\s*\)", "self-comparing assertion"),
    (r"\bunimplemented!\(|\btodo!\(", "left a todo!/unimplemented! in place"),
    (r"return\s+Ok\(\(\)\);\s*//\s*(TODO|FIXME|skip)", "stubbed a check to pass"),
]


def path_matches(path: str, globs: list[str]) -> bool:
    from fnmatch import fnmatch

    for g in globs:
        if fnmatch(path, g):
            return True
        if g.endswith("/**") and path.startswith(g[:-2]):
            return True
        # "crates/*/tests/**" should match "crates/sim/tests/determinism.rs"
        if "**" in g:
            prefix = g.split("**")[0]
            if fnmatch(path, prefix + "*"):
                return True
    return False


def changed_entries(repo: Path) -> list[tuple[str, str]]:
    """(status, path) pairs. Status is the two-char git porcelain code."""
    out = git(repo, "status", "--porcelain=v1", "--untracked-files=all")
    entries = []
    for line in out.splitlines():
        if not line.strip():
            continue
        status, path = line[:2], line[3:].strip()
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        entries.append((status, path.strip('"')))
    return entries


def changed_files(repo: Path) -> list[str]:
    return [p for _, p in changed_entries(repo)]


def is_new_file(status: str) -> bool:
    """Untracked or freshly added. Creating a file is not tampering, even inside
    a protected directory - the tasks explicitly ask the agent to add tests."""
    return status.strip() in {"??", "A", "AM"}


def revert_protected(repo: Path, task: Task) -> list[str]:
    """Restore protected paths to their pristine state before grading.

    This is SWE-bench's mechanism: the agent's edits to tests are discarded by
    construction, so neutering a test cannot help it. Returns what was reverted.
    """
    reverted = []
    for status, f in changed_entries(repo):
        if is_new_file(status):
            continue  # a brand-new file cannot have neutered an existing test
        if path_matches(f, task.protected_paths):
            reverted.append(f)
            # Tracked file: restore from the baseline commit. Untracked: delete.
            if git(repo, "ls-files", "--error-unmatch", f).strip() or True:
                # check=False: a non-zero checkout means the path is untracked, and
                # the unlink below IS the handler. The status is read on the next line.
                r = subprocess.run(
                    ["git", "checkout", "HEAD", "--", f],
                    cwd=repo,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                if r.returncode != 0:
                    (repo / f).unlink(missing_ok=True)
    return reverted


def removes_lines(repo: Path, path: str) -> bool:
    """True if the agent's diff for `path` deletes any pre-existing line.

    A pure-addition diff leaves every existing assertion intact and is therefore
    not a weakening of the suite."""
    diff = git(repo, "diff", "HEAD", "--numstat", "--", path)
    for line in diff.splitlines():
        parts = line.split("\t")
        if len(parts) >= 3:
            try:
                return int(parts[1]) > 0  # deletions column
            except ValueError:
                return True  # binary or unparseable - be conservative
    return False


def detect_tampering(repo: Path, task: Task) -> list[str]:
    findings: list[str] = []
    for status, f in changed_entries(repo):
        if path_matches(f, task.protected_paths):
            # Creating a new test, or ADDING to an existing one, is exactly what
            # the tasks ask for. Protected paths are reverted before grading, so
            # an addition cannot help the agent anyway - flagging it would be
            # double-punishment, and it wrongly zeroed correct work twice during
            # development.
            #
            # What actually constitutes tampering is REMOVING existing coverage:
            # deleting the file, or deleting/rewriting lines inside it.
            # Only an unambiguous cheat scores zero. Editing a protected test
            # file is recorded (see `touched_protected`) but does NOT zero the
            # trial, because those files are reverted to pristine before grading
            # - the edit cannot influence the result either way. Penalising it
            # produced three false positives during development, each time on an
            # agent doing exactly what the task asked.
            if status.strip() == "D":
                findings.append(f"deleted a protected file: {f}")
        elif task.allowed_paths and not path_matches(f, task.allowed_paths):
            findings.append(f"edited path outside allowed set: {f}")

    diff = git(repo, "diff", "HEAD", "--unified=0")
    added = "\n".join(
        ln[1:] for ln in diff.splitlines() if ln.startswith("+") and not ln.startswith("+++")
    )
    for pattern, desc in CHEAT_PATTERNS:
        if re.search(pattern, added):
            findings.append(f"suspicious added code - {desc}")

    for ln in git(repo, "diff", "HEAD", "--name-status").splitlines():
        if ln.startswith("D"):
            name = ln[1:].strip()
            if "test" in name.lower():
                findings.append(f"deleted a test file: {name}")
    return findings


# --------------------------------------------------------------------------- #
# Repo setup
# --------------------------------------------------------------------------- #

IGNORE = shutil.ignore_patterns(
    ".git", "target", "node_modules", "dist", "runs", "__pycache__",
    "*.actual.png", "*.expected.png", "*.diff.png", "artifacts", "Library", "Temp",
    ".godot", ".eslintcache"
)


def prepare_repo(template: Path, dest: Path, arm: dict[str, Any]) -> None:
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(template, dest, ignore=IGNORE)

    for rel in arm.get("remove_files", []):
        (dest / rel).unlink(missing_ok=True)
    for rel, src in (arm.get("replace_files") or {}).items():
        shutil.copy(Path(src).resolve(), dest / rel)

    subprocess.run(["git", "init", "-q"], cwd=dest, check=True)
    subprocess.run(["git", "add", "-A"], cwd=dest, check=True)
    subprocess.run(
        ["git", "-c", "user.email=eval@local", "-c", "user.name=eval",
         "commit", "-q", "-m", "baseline"],
        cwd=dest, check=True,
    )


def apply_holdout(repo: Path, template: Path, task: Task) -> None:
    src = (template.parent / task.holdout_src).resolve()
    if not src.exists():
        src = Path(task.holdout_src).resolve()
    if not src.exists():
        raise FileNotFoundError(f"holdout source not found: {task.holdout_src}")
    for item in src.iterdir():
        dst = repo / item.name
        if item.is_dir():
            shutil.copytree(item, dst, dirs_exist_ok=True)
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(item, dst)


# --------------------------------------------------------------------------- #
# Agent invocation
# --------------------------------------------------------------------------- #


def parse_agent_result(stdout: str) -> dict[str, Any]:
    """`--output-format json` emits a JSON array; the summary is the last element
    with type == 'result'. Parse defensively."""
    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        data = []
        for line in stdout.splitlines():
            line = line.strip()
            if line.startswith("{"):
                try:
                    data.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    if isinstance(data, dict):
        data = [data]
    if not isinstance(data, list) or not data:
        return {"is_error": True, "result": stdout[-3000:], "parse_error": True}
    results = [x for x in data if isinstance(x, dict) and x.get("type") == "result"]
    return results[-1] if results else data[-1]


def agent_metrics(agent: dict[str, Any]) -> dict[str, Any]:
    """Cost and tokens from modelUsage - the field the SDK docs say to use.

    `usage` covers the main loop only and excludes subagents; `modelUsage` is
    cumulative across every model call in the query pipeline. It is already a
    running total, so read the latest result rather than summing.
    """
    model_usage = agent.get("modelUsage") or {}
    cost = sum((m or {}).get("costUSD", 0) or 0 for m in model_usage.values())
    inp = sum((m or {}).get("inputTokens", 0) or 0 for m in model_usage.values())
    out = sum((m or {}).get("outputTokens", 0) or 0 for m in model_usage.values())
    cache = sum(
        (m or {}).get("cacheReadInputTokens", 0) or 0 for m in model_usage.values()
    )
    if not model_usage:  # fall back only if modelUsage is genuinely absent
        cost = agent.get("total_cost_usd") or 0
        u = agent.get("usage") or {}
        inp, out = u.get("input_tokens", 0), u.get("output_tokens", 0)
        cache = u.get("cache_read_input_tokens", 0)
    return {
        "cost_usd": round(cost, 4),
        "input_tokens": inp,
        "output_tokens": out,
        "cache_read": cache,
        "models": sorted(model_usage.keys()),
    }


def run_agent(work: Path, task: Task, arm: dict[str, Any], session_id: str,
              target_dir: Path | None = None):
    cmd = [
        "claude", "-p", task.prompt,
        "--output-format", "json",
        "--model", arm.get("model", task.model),
        "--max-turns", str(task.max_turns),
        "--max-budget-usd", str(task.max_budget_usd),
        # Isolates the user's global CLAUDE.md. Verified necessary.
        "--setting-sources", "project",
        # Don't let the operator's MCP servers into the experiment.
        "--strict-mcp-config",
        # Keeps the system prompt free of machine-specific sections so prompt
        # caching behaves the same regardless of who runs the eval.
        "--exclude-dynamic-system-prompt-sections",
        "--permission-mode", "acceptEdits",
        "--session-id", session_id,
    ]
    if arm.get("append_system_prompt"):
        cmd += ["--append-system-prompt", arm["append_system_prompt"]]
    if arm.get("allowed_tools"):
        cmd += ["--allowedTools", *arm["allowed_tools"]]
    if arm.get("disallowed_tools"):
        cmd += ["--disallowedTools", *arm["disallowed_tools"]]
    # check=False: an agent that stops on its budget or turn ceiling exits non-zero and
    # has still produced a submission worth grading. Raising here would throw away the
    # trial we paid for; the terminal reason comes out of the parsed result instead.
    try:
        p = subprocess.run(
            cmd, cwd=work, capture_output=True, text=True, timeout=task.timeout_s,
            env=trial_env(target_dir), check=False,
        )
        return parse_agent_result(p.stdout), p.stderr[-3000:]
    except subprocess.TimeoutExpired:
        return {"is_error": True, "result": "HARNESS TIMEOUT",
                "terminal_reason": "harness_timeout"}, ""


# --------------------------------------------------------------------------- #
# One trial
# --------------------------------------------------------------------------- #


def run_trial(template: Path, task: Task, arm_name: str, arm: dict[str, Any],
              trial: int, run_dir: Path) -> dict[str, Any]:
    trial_id = f"{task.id}__{arm_name}__t{trial}"
    work = run_dir / "work" / trial_id
    work.parent.mkdir(parents=True, exist_ok=True)
    prepare_repo(template, work, arm)
    target_dir = clone_pristine_target(run_dir / "targets" / trial_id)
    if task.setup_cmd:
        setup = sh(task.setup_cmd, work, timeout_s=1200, target_dir=target_dir)
        if setup.code != 0:
            print(f"  [SETUP FAILED] {trial_id}: {task.setup_cmd}\n{setup.text[-800:]}")

    rec: dict[str, Any] = {
        "trial_id": trial_id, "task": task.id, "arm": arm_name, "trial": trial,
        "started_at": dt.datetime.now(dt.timezone.utc).isoformat(),
    }
    session_id = str(uuid.uuid4())
    rec["session_id"] = session_id

    t0 = dt.datetime.now()
    agent, stderr = run_agent(work, task, arm, session_id, target_dir)
    rec["wall_s"] = round((dt.datetime.now() - t0).total_seconds(), 1)

    rec["agent"] = {
        "is_error": bool(agent.get("is_error")),
        "subtype": agent.get("subtype"),
        "terminal_reason": agent.get("terminal_reason"),
        "num_turns": agent.get("num_turns"),
        "duration_ms": agent.get("duration_ms"),
        "permission_denials": len(agent.get("permission_denials") or []),
        "final_text": (agent.get("result") or "")[-1500:],
        "stderr": stderr[-1500:],
        **agent_metrics(agent),
    }

    # Snapshot the diff BEFORE any grading mutation, for later forensics.
    rec["diff_stat"] = git(work, "diff", "HEAD", "--stat")[-3000:]
    rec["changed_files"] = changed_files(work)
    rec["tampering"] = detect_tampering(work, task)
    # Diagnostic only: which protected files the agent touched. Reverted before
    # grading, so this never affects pass/score.
    rec["touched_protected"] = [
        f for st, f in changed_entries(work)
        if path_matches(f, task.protected_paths) and not is_new_file(st)
    ]

    # The agent's own advertised check, run on the repo as the agent left it.
    verify = sh(task.verify_cmd, work, timeout_s=1800, target_dir=target_dir)
    # Both streams, each on its own budget. This record is the only place a later check can
    # ask whether the agent ran its own gate to completion, and a merged buffer answered
    # that question with whichever stream the toolchain happened to write second (#100/#114).
    rec["self_verify"] = verify.record(passed=verify.code == 0)

    # Now revert protected paths and layer in held-out tests.
    rec["reverted"] = revert_protected(work, task)
    try:
        apply_holdout(work, template, task)
    except FileNotFoundError as e:
        rec["holdout"] = {"error": str(e), "passed": False, "score": 0.0}
        rec["passed"] = False
        _persist(run_dir, rec)
        return rec

    holdout = sh(task.holdout_cmd, work, timeout_s=1800, target_dir=target_dir)
    # `.text` is stdout-then-stderr, byte for byte what these parsers were handed before
    # the capture was split, so no score can move with the record's shape.
    passed_n, total_n = parse_test_counts(holdout.text)
    skipped_n = parse_skipped(holdout.text)
    rec["holdout"] = holdout.record(
        # A skipped held-out test verified nothing, so it cannot count toward a
        # pass. This invalidates the TRIAL (an environment problem), rather than
        # scoring the agent as having failed.
        # Exit 0 having run ZERO tests is not a pass — it is a broken command.
        # Godot exited 0 with 0/0 when newly-added class_name files had not been
        # re-imported, which check-suite reported as "the task is already done".
        passed=holdout.code == 0 and skipped_n == 0 and total_n > 0,
        skipped=skipped_n,
        tests_passed=passed_n,
        tests_total=total_n,
        # Continuous score. Falls back to the binary outcome when the runner
        # produced no parseable counts (e.g. a compile failure).
        score=(passed_n / total_n) if total_n else (1.0 if holdout.code == 0 else 0.0),
    )

    rec["passed"] = bool(rec["holdout"]["passed"]) and not rec["tampering"]
    rec["score"] = 0.0 if rec["tampering"] else rec["holdout"]["score"]
    rec["finished_at"] = dt.datetime.now(dt.timezone.utc).isoformat()

    _persist(run_dir, rec)
    flag = "PASS" if rec["passed"] else "FAIL"
    if rec["tampering"]:
        flag += " TAMPERED"
    print(
        f"  [{flag}] {trial_id}  score={rec['score']:.2f}  {rec['wall_s']}s  "
        f"${rec['agent']['cost_usd']:.2f}  turns={rec['agent']['num_turns']}  "
        f"{rec['agent']['terminal_reason']}",
        flush=True,
    )
    return rec


def _persist(run_dir: Path, rec: dict[str, Any]) -> None:
    (run_dir / "trials").mkdir(parents=True, exist_ok=True)
    (run_dir / "trials" / f"{rec['trial_id']}.json").write_text(json.dumps(rec, indent=2))


# --------------------------------------------------------------------------- #
# Negative control
# --------------------------------------------------------------------------- #


def check_suite(suite: Suite, template: Path, scratch: Path) -> int:
    """A task is only a task if its held-out tests FAIL on the pristine template.

    Without this, a task can silently grade every agent as successful and
    contribute nothing but noise.
    """
    scratch.mkdir(parents=True, exist_ok=True)
    bad = 0
    floors: dict[str, float] = {}
    for task in suite.tasks:
        work = scratch / f"control__{task.id}"
        prepare_repo(template, work, {})
        if task.setup_cmd:
            setup = sh(task.setup_cmd, work, timeout_s=1200)
            if setup.code != 0:
                print(f"  [BROKEN] {task.id}: setup_cmd failed: {setup.text[-400:]}")
                bad += 1
                continue
        try:
            apply_holdout(work, template, task)
        except FileNotFoundError as e:
            print(f"  [BROKEN] {task.id}: {e}")
            bad += 1
            continue
        td = clone_pristine_target(scratch / f"target__{task.id}")
        control = sh(task.holdout_cmd, work, timeout_s=1800, target_dir=td)
        code = control.code
        passed_n, total_n = parse_test_counts(control.text)
        # Record the floor: some held-out tests (e.g. "the paddles still render")
        # pass trivially before the fix. Without subtracting this, doing nothing
        # scores 0.67 on a 3-test task and every arm looks better than it is.
        floors[task.id] = (passed_n / total_n) if total_n else 0.0
        if code == 0 and total_n == 0:
            print(f"  [BROKEN] {task.id}: command exited 0 but ran ZERO tests — "
                  f"the holdout command is wrong, not the task.")
            bad += 1
            continue
        if code == 0:
            print(f"  [BROKEN] {task.id}: held-out tests PASS on the pristine "
                  f"template ({passed_n}/{total_n}). The task is already done; "
                  f"it cannot measure anything.")
            bad += 1
        else:
            print(f"  [ok]     {task.id}: held-out tests fail as expected "
                  f"({passed_n}/{total_n} passing before the fix)")
    (scratch / "floors.json").write_text(json.dumps(floors, indent=2))
    print(f"\n{len(suite.tasks) - bad}/{len(suite.tasks)} tasks are well-formed")
    print(f"control floors written to {scratch / 'floors.json'}: {floors}")
    return 1 if bad else 0


def load_floors(run_dir: Path) -> dict[str, float]:
    for candidate in (run_dir / "floors.json", run_dir.parent / "_control" / "floors.json"):
        if candidate.exists():
            return json.loads(candidate.read_text())
    return {}


def normalise(score: float, floor: float) -> float:
    """Rescale so 'did nothing' is 0.0 and 'fully solved' is 1.0."""
    if floor >= 1.0:
        return 0.0
    return max(0.0, (score - floor) / (1.0 - floor))


# --------------------------------------------------------------------------- #
# Statistics
# --------------------------------------------------------------------------- #


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """Wilson score interval - correct at small n, unlike the normal approx."""
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    d = 1 + z * z / n
    c = p + z * z / (2 * n)
    m = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n))
    return (max(0.0, (c - m) / d), min(1.0, (c + m) / d))


def sem(values: list[float]) -> float:
    """SE of the mean via the CLT. Miller (arXiv:2411.00640) sec 2: bootstrap is
    unnecessary for a simple sampling scheme."""
    n = len(values)
    if n < 2:
        return float("nan")
    return statistics.stdev(values) / math.sqrt(n)


def paired_delta(a_by_task: dict[str, float], b_by_task: dict[str, float]):
    """Per-task paired difference. Miller sec 4: run both arms on the same tasks
    and take the SE of the differences - roughly a third less estimator variance
    than comparing population means, for free."""
    common = sorted(set(a_by_task) & set(b_by_task))
    diffs = [a_by_task[t] - b_by_task[t] for t in common]
    if not diffs:
        return None
    mean = statistics.fmean(diffs)
    se = sem(diffs) if len(diffs) > 1 else float("nan")
    corr = float("nan")
    if len(common) > 1:
        xs = [a_by_task[t] for t in common]
        ys = [b_by_task[t] for t in common]
        try:
            corr = statistics.correlation(xs, ys)
        except statistics.StatisticsError:
            pass
    return {"n_tasks": len(common), "mean": mean, "se": se,
            "ci95": (mean - 1.96 * se, mean + 1.96 * se) if se == se else None,
            "corr": corr}


# --------------------------------------------------------------------------- #
# Reporting
# --------------------------------------------------------------------------- #


def report(run_dir: Path) -> None:
    trials = [json.loads(p.read_text()) for p in sorted((run_dir / "trials").glob("*.json"))]
    if not trials:
        print("no trials found")
        return

    floors = load_floors(run_dir)
    for t in trials:
        t["score_norm"] = normalise(t.get("score", 0.0), floors.get(t["task"], 0.0))

    by_arm: dict[str, list[dict]] = {}
    for t in trials:
        by_arm.setdefault(t["arm"], []).append(t)

    print(f"\n=== {run_dir.name} - {len(trials)} trials ===")
    if floors:
        print(f"control floors (score for doing nothing): {floors}")
        print("'score' below is normalised: 0.00 = did nothing, 1.00 = fully solved\n")
    else:
        print("WARNING: no floors.json - run `check-suite` first or scores are inflated\n")
    hdr = f"{'arm':<20} {'pass':>7} {'rate':>6} {'95% CI':>14} {'score':>7} {'±SE':>6} {'$':>7} {'turns':>6} {'wall':>7}"
    print(hdr)
    print("-" * len(hdr))
    for arm, ts in sorted(by_arm.items()):
        n = len(ts)
        k = sum(1 for t in ts if t.get("passed"))
        lo, hi = wilson(k, n)
        # Average to a per-task score first, THEN take SE across tasks. Pooling
        # across all trials is inconsistent (Miller sec 3).
        per_task: dict[str, list[float]] = {}
        for t in ts:
            per_task.setdefault(t["task"], []).append(t.get("score_norm", t.get("score", 0.0)))
        task_means = [statistics.fmean(v) for v in per_task.values()]
        s_mean = statistics.fmean(task_means) if task_means else 0.0
        s_se = sem(task_means)
        cost = statistics.fmean([t["agent"]["cost_usd"] or 0 for t in ts])
        turns = statistics.fmean([t["agent"]["num_turns"] or 0 for t in ts])
        wall = statistics.fmean([t["wall_s"] for t in ts])
        se_txt = f"{s_se:.2f}" if s_se == s_se else "  -"
        print(f"{arm:<20} {k:>3}/{n:<3} {k/n:>5.0%} {f'[{lo:.0%},{hi:.0%}]':>14} "
              f"{s_mean:>7.2f} {se_txt:>6} {cost:>7.2f} {turns:>6.0f} {wall:>6.0f}s")

    # Paired comparison against the first arm alphabetically (usually baseline).
    arms = sorted(by_arm)
    if len(arms) > 1:
        base = "baseline" if "baseline" in by_arm else arms[0]
        print(f"\n--- paired vs '{base}' (per-task differences) ---")
        base_scores = _mean_scores_by_task(by_arm[base])
        for arm in arms:
            if arm == base:
                continue
            d = paired_delta(_mean_scores_by_task(by_arm[arm]), base_scores)
            if not d:
                continue
            ci = f"[{d['ci95'][0]:+.2f},{d['ci95'][1]:+.2f}]" if d["ci95"] else "n/a"
            print(f"{arm:<20} Δscore={d['mean']:+.3f}  SE={d['se']:.3f}  "
                  f"95%CI={ci}  corr={d['corr']:.2f}  n={d['n_tasks']} tasks")
        print("\nNote: with few tasks x few trials the minimum detectable effect is")
        print("large (~15-25pp on a binary outcome). Treat overlapping intervals as")
        print("'not resolved', never as 'no difference'.")

    print("\n--- terminal reasons (did the agent finish, or did we cut it off?) ---")
    reasons: dict[tuple[str, str], int] = {}
    for t in trials:
        reasons[(t["arm"], str(t["agent"].get("terminal_reason")))] = (
            reasons.get((t["arm"], str(t["agent"].get("terminal_reason"))), 0) + 1
        )
    for (arm, reason), n in sorted(reasons.items()):
        print(f"{arm:<20} {reason:<28} {n}")

    tampered = [t for t in trials if t.get("tampering")]
    if tampered:
        print(f"\n--- TAMPERING ({len(tampered)}) ---")
        for t in tampered:
            print(f"{t['trial_id']}: {'; '.join(t['tampering'][:3])}")

    # The most diagnostic number for template design: the agent believed it was
    # done, and it was not.
    fooled = [
        t for t in trials
        if t.get("self_verify", {}).get("passed") and not t.get("passed")
    ]
    if fooled:
        print(f"\n--- SELF-VERIFY PASSED BUT HELD-OUT FAILED ({len(fooled)}) ---")
        print("The agent's own check was green while the real check was red.")
        print("Every one of these is a gap in what `verify` actually covers.")
        for t in fooled:
            print(f"  {t['trial_id']}  holdout={t['holdout'].get('tests_passed')}/"
                  f"{t['holdout'].get('tests_total')}")


def _mean_scores_by_task(trials: list[dict]) -> dict[str, float]:
    per: dict[str, list[float]] = {}
    for t in trials:
        per.setdefault(t["task"], []).append(t.get("score_norm", t.get("score", 0.0)))
    return {k: statistics.fmean(v) for k, v in per.items()}


# --------------------------------------------------------------------------- #


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("run")
    r.add_argument("--suite", required=True, type=Path)
    r.add_argument("--template", required=True, type=Path)
    r.add_argument("--trials", type=int, default=3)
    r.add_argument("--arms", nargs="*", default=None)
    r.add_argument("--tasks", nargs="*", default=None)
    r.add_argument("--parallel", type=int, default=1,
                   help="Keep at 1 while trials share a CARGO_TARGET_DIR; "
                        "concurrent cargo builds block on the same file lock.")
    r.add_argument("--out", type=Path, default=Path("runs"))

    c = sub.add_parser("check-suite")
    c.add_argument("--suite", required=True, type=Path)
    c.add_argument("--template", required=True, type=Path)
    c.add_argument("--scratch", type=Path, default=Path("runs/_control"))

    p = sub.add_parser("report")
    p.add_argument("--run-dir", required=True, type=Path)

    args = ap.parse_args()

    if args.cmd == "report":
        report(args.run_dir)
        return 0

    suite = load_suite(args.suite)
    template = args.template.resolve()

    # The four trees this harness was built to drive were deleted on 2026-08-23
    # (DECISIONS.md, #119). Without this, `prepare_repo`'s `copytree` raises a
    # bare FileNotFoundError three frames down and a reader has to guess whether
    # they mistyped a path or the suite no longer exists. Say which.
    if not template.is_dir():
        print(f"no template tree at {template}\n\n"
              "The spec-change suite was retired on 2026-08-23: template/, "
              "template-ts/, template-unity/ and template-godot/ were deleted, "
              "and nothing else in this repository is a --template tree. "
              "eval/starters/*/ are NOT substitutes - they are the whole-game "
              "product and carry no finished game for a spec change to modify.\n"
              "To restore a tree: git checkout <commit-before-retirement> -- "
              "template-ts/ (139 commits of history; the trees are pushed).\n"
              "To read what this harness already produced: runner.py report "
              "--run-dir runs/<name>, or regrade.py.", file=sys.stderr)
        return 2

    if args.cmd == "check-suite":
        print(f"negative control for '{suite.name}' - held-out tests must FAIL "
              f"on the pristine template\n")
        return check_suite(suite, template, args.scratch.resolve())

    stamp = dt.datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
    run_dir = (args.out / f"{suite.name}-{stamp}").resolve()
    run_dir.mkdir(parents=True, exist_ok=True)
    # Append-only, through the SAME writer `wholegame.py` uses. This harness stamps its
    # own run directory to the second, so a collision is unlikely rather than impossible -
    # and the reason to route it here is not this call site's risk. Giving the two
    # harnesses two similar manifest policies is how #100 came back, and it is how
    # `suite.json` came to be guarded in one file and overwritten in the other (#119).
    _tools = Path(__file__).resolve().parent / "tools"
    import importlib.util as _ilu
    _mspec = _ilu.spec_from_file_location("_manifest", _tools / "manifest.py")
    _manifest = _ilu.module_from_spec(_mspec)
    sys.modules[_mspec.name] = _manifest   # `@dataclass` resolves via sys.modules
    _mspec.loader.exec_module(_manifest)
    _manifest.write_manifest(run_dir, {
        "suite": suite.name, "template": str(template), "trials": args.trials,
        "started_at": dt.datetime.now(dt.timezone.utc).isoformat()})
    # Snapshot the control floors INTO this run. They are per-suite: the same
    # task can have a different floor on a different stack (a Rust holdout that
    # fails to compile scores 0/0, while the TypeScript equivalent runs and
    # passes the trivially-true assertions). A shared floors.json would apply one
    # stack's baseline to another's results.
    src_floors = Path("runs/_control/floors.json")
    if src_floors.exists():
        shutil.copy(src_floors, run_dir / "floors.json")
    else:
        print("WARNING: no control floors found - run `check-suite` first, "
              "or scores will be inflated")

    arms = {k: v for k, v in suite.arms.items() if not args.arms or k in args.arms}
    tasks = [t for t in suite.tasks if not args.tasks or t.id in args.tasks]
    jobs = [(template, task, an, av, i, run_dir)
            for task in tasks for an, av in arms.items() for i in range(args.trials)]
    print(f"{len(jobs)} trials = {len(tasks)} tasks x {len(arms)} arms x {args.trials}\n")

    if args.parallel <= 1:
        for j in jobs:
            run_trial(*j)
    else:
        with futures.ThreadPoolExecutor(max_workers=args.parallel) as ex:
            list(ex.map(lambda j: run_trial(*j), jobs))

    report(run_dir)
    print(f"\nrun dir: {run_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
