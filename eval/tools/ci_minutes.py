#!/usr/bin/env python3
"""The producer for how many GitHub Actions minutes this repository has consumed.

WHY THIS EXISTS. `.github/workflows/README.md` sized the CI design against an estimate:
"~30 fast runs/day ... ~5 slow runs/day ... that is ~2400 minutes a month". Every input to
that sentence was a guess, nothing in the repository produced any of it, and so nothing could
disagree with it. `AGENTS.md` says a count with no producer goes stale forever. This is the
producer, and the number it reports is read from an endpoint.

WHAT IS BILLED, AND WHY THE OBVIOUS FIELD IS NOT IT.

  * The billing unit is the **job**, not the run. GitHub rounds each job's wall clock up to
    the next whole minute; a 22-second job costs a minute.
  * `run_duration_ms` from `/actions/runs/{id}/timing` is the **run**, and it includes the
    queue wait before the job starts. Measured on run 32657248359: `run_duration_ms` is
    607000 while its one job ran 18:11:50 -> 18:21:38, which is 588s. Summing that field
    over-reports, and truncating it instead of rounding up under-reports.
  * `billable.UBUNTU.total_ms` is the field whose NAME says it is the answer. It read **0
    for 58 of 58 runs** this repository had on 2026-08-23, measured one run at a time. A
    census that returns one value across the population it exists to discriminate is
    reporting the instrument, not the population (`AGENTS.md` rule 12's corollary), so this
    tool REFUSES that field rather than reporting a confident zero. It still reads it, and
    prints what it saw, because what the instrument DID is the audit trail. Anything that
    had summed it would report "0 minutes consumed" -- confident, in range, and wrong.

So the quantity is `sum over completed jobs of ceil(job wall-clock / 60)`, at the Linux 1x
multiplier -- `runs-on: ubuntu-latest` in both workflows, asserted by `--selftest` against the
workflow files rather than remembered.

THREE VALUES, NOT TWO. A job with `completed_at: null` is in flight. It is not zero minutes
and it is not an error; it is unfinished, and it is reported in its own bucket rather than
folded into the total. Pooling it would make the total quietly low every time the tool runs
while something is building (`AGENTS.md` rule 4).

WHAT IT REFUSES. Any `gh api` failure exits 2 naming the endpoint. There is no `|| 0`
anywhere: an error must never become a plausible in-range number (rule 3).

THE WINDOW IS PART OF THE NUMBER. This repository's first workflow run is 2026-08-23, so a
figure from it is "minutes since CI existed", not a monthly rate, and the tool prints the
first and last job it counted so the total cannot be quoted without its population.

--path-filter answers a different question from the same data: for every `controls` run on a
pull request, did the LATEST PUSH touch one of the workflow's filter paths, or was the run
bought by the accumulated whole-PR diff? The reasoning it feeds is in
`.github/workflows/README.md`.

--scope IS `controls.yml`'s path filter, and it lives here rather than in `on: paths:`
because a workflow that does not match its filter produces NO check, not a passing one --
and `controls` is a required check, so a pull request touching only `tasks/` or a root
document waited on a check that could never arrive (measured at PR #14's head: 2 `gates`
check runs, 0 `controls`). The job now runs on every pull request and this decides,
inside it, whether the slow suites have anything to read. Its verdict is written as
`relevant=true|false` to `$GITHUB_OUTPUT`, and every step below the scope step is guarded
on `!= 'false'` -- never `== 'true'`, because an output nothing wrote reads as the empty
string, and skipping on it would report a green `controls` that executed no gate. Every
state in which the answer is unknown -- an unreadable diff, an empty one, a non-pull-request
event -- runs the whole suite.

--selftest pins both directions offline, in ~0.1s and without touching a file, and its
closing line is the producer for how many workflow mutants and variants it carries. What it
must catch: truncation instead of rounding up; a compare list at the endpoint's 300-file cap,
which must be refused rather than scored; the ways a workflow can leave `ubuntu-latest` while
the file still contains the string; a filter entry no pin depends on; and the ways the scope
guard can break -- a `paths:` or `paths-ignore:` filter back on either trigger, the scope step
deleted, its id renamed, its command replaced, one gate losing its guard, the guard flipped to
the fail-open `== 'true'`, the guard conjoined with a constant false, a guarded step placed
above the step whose output it reads, a second `ubuntu-latest` job carrying an unguarded gate,
a scalar `steps:`, and a file that does not parse at all. What must still
PASS: an in-flight job, a job of exactly 60s, a 22s job, a filename that merely starts with a
filtered directory's letters, a re-spaced and double-quoted guard, two gates swapped, an
unguarded `uses:` step, a comment in the job, and an extra flag on the scope step. The
variants are not decoration -- the substring check this replaced went red on a re-quote,
which is a gate firing where nothing is wrong.

Usage:
    python3 eval/tools/ci_minutes.py                 # the census, from the API
    python3 eval/tools/ci_minutes.py --path-filter   # the path-filter audit
    python3 eval/tools/ci_minutes.py --scope         # controls.yml's filter, in-job
    python3 eval/tools/ci_minutes.py --cache DIR     # also write the raw JSON it consumed
    python3 eval/tools/ci_minutes.py --selftest      # controls, both directions, offline

Exit 0 on success, 1 if --selftest fails, 2 if the data could not be read. Read it unpiped.
"""

from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import io
import json
import math
import os
import pathlib
import subprocess
import sys

REPO = "teonimesic/game-stack-bakeoff"
ROOT = pathlib.Path(__file__).resolve().parents[2]
WORKFLOW_DIR = ROOT / ".github" / "workflows"

# controls.yml's path filter, spelled here so --selftest can assert the two agree rather
# than promise it in a comment (AGENTS.md rule 12: the address is an input to the check).
FILTER_PREFIXES = ("eval/", ".agents/", ".claude/")
FILTER_EXACT = (".github/workflows/controls.yml",)

# `%z` and not a literal `Z`, so the parsed values are timezone-AWARE. This is not
# tidiness: the analysis behind task 124 first compared git's `%cI` (offset -03:00) against
# these stamps as naive values, and reported 0 `main` commits inside two windows that in
# fact held 4 and 7 -- the reassuring answer, and the opposite conclusion. Aware datetimes
# make that comparison either correct or a TypeError, never quietly wrong.
_TS = "%Y-%m-%dT%H:%M:%S%z"


class DataError(RuntimeError):
    """The data could not be read. Never downgraded to a number."""


# ---------------------------------------------------------------- the billing arithmetic


def job_seconds(job: dict) -> float | None:
    """Wall clock of one job, or None if it has not finished.

    None is a third value and callers must keep it out of the total.
    """
    if not job.get("completed_at") or not job.get("started_at"):
        return None
    started = dt.datetime.strptime(job["started_at"], _TS)
    completed = dt.datetime.strptime(job["completed_at"], _TS)
    return (completed - started).total_seconds()


def billable_minutes(seconds: float) -> int:
    """GitHub rounds each job UP to the next whole minute. 22s costs a whole minute."""
    return math.ceil(seconds / 60)


def census(jobs: list[dict], runs: list[dict]) -> dict:
    """Total billable minutes, partitioned. Never sums across the partitions blind."""
    by_run = {r["id"]: r for r in runs}
    finished, in_flight = [], []
    for j in jobs:
        secs = job_seconds(j)
        (in_flight if secs is None else finished).append((j, secs))

    per_workflow: dict[str, dict] = {}
    per_conclusion: dict[str, dict] = {}
    per_event: dict[str, dict] = {}
    for j, secs in finished:
        run = by_run.get(j["run_id"], {})
        wf = run.get("name", "unknown")
        concl = j.get("conclusion") or "unknown"
        # workflow x event, because the lever the register names -- dropping the slow
        # tier's pull_request trigger and keeping the nightly -- acts on exactly one cell
        # of that cross, and a total over either axis alone cannot price it.
        event = f"{wf}/{run.get('event', 'unknown')}"
        for bucket, key in ((per_workflow, wf), (per_conclusion, concl), (per_event, event)):
            slot = bucket.setdefault(key, {"jobs": 0, "minutes": 0, "seconds": 0.0})
            slot["jobs"] += 1
            slot["minutes"] += billable_minutes(secs)
            slot["seconds"] += secs

    stamps = sorted(j["started_at"] for j, _ in finished) if finished else []
    return {
        "total_minutes": sum(billable_minutes(s) for _, s in finished),
        "raw_seconds": sum(s for _, s in finished),
        "jobs_counted": len(finished),
        "jobs_in_flight": len(in_flight),
        "per_workflow": per_workflow,
        "per_conclusion": per_conclusion,
        "per_workflow_event": per_event,
        "first_job_started": stamps[0] if stamps else None,
        "last_job_started": stamps[-1] if stamps else None,
    }


# ---------------------------------------------------------------- the path-filter audit


def matches_filter(path: str,
                   prefixes: tuple[str, ...] = FILTER_PREFIXES,
                   exact: tuple[str, ...] = FILTER_EXACT) -> bool:
    """Does one changed path satisfy controls.yml's filter?

    The prefixes carry their trailing slash, so `evaluation.md` is not `eval/**` -- a
    filename that merely starts with a filtered directory's letters is the variant this
    would otherwise mishandle.

    `prefixes`/`exact` are parameters so `--selftest` can delete one entry and ask whether
    any pinned path notices. Nothing in production passes them.
    """
    return path.startswith(prefixes) or path in exact


# --------------------------------------------------------------------- the scope guard

# `controls.yml` declares NO `paths:` on its triggers. It runs on every pull request and
# decides INSIDE the job whether its suites have anything to look at, because a filtered
# workflow that does not match produces no check at all rather than a passing one -- and
# `controls` is a required check, so a pull request touching only `tasks/` or a root
# document waited on a check that could never arrive. Measured at PR #14's head: two
# `gates` check runs, 0 `controls`.
SCOPE_STEP_ID = "scope"
SCOPE_INVOCATION = "ci_minutes.py --scope"

# `!= 'false'` and NOT `== 'true'`, and that single choice is the safety argument for the
# whole shape. A step output that was never written reads as the empty string, so
# `== 'true'` would skip every suite and report a green `controls` that executed nothing --
# the one pattern this project exists to catch, and the recorded objection to step-gating.
# `!= 'false'` runs them instead: the only way to skip is for the scope step to have run
# and said so.
GUARD_EXPR = "steps.scope.outputs.relevant != 'false'"

# THE WHOLE GUARD, not a substring of it. Containment accepts
# `${{ steps.scope.outputs.relevant != 'false' && false }}`, which skips every gate and
# reports a green `controls` -- the very thing the guard exists to prevent, wearing the
# guard's own text. Raised by CodeRabbit on PR #16.
#
# An enumeration is the right shape HERE and the wrong shape as a trigger: this is the
# closed set of expressions a step may carry, so an unlisted one is a change to a
# load-bearing guard and should have to be read. AGENTS.md's warning is about triggers
# written as lists of the instances you happened to see; a whitelist is the other
# direction, and the error names the accepted set so the reader is not left guessing.
#
# `success()` is what a setup step carries -- it must not run after an earlier failure --
# and `!cancelled()` is what a gate carries, so one red gate cannot hide the verdict of
# the others. Compared after `_norm_expr`, so a re-spacing or a re-quote still passes.
ALLOWED_GUARDS = (
    f"${{{{ success() && {GUARD_EXPR} }}}}",
    f"${{{{ !cancelled() && {GUARD_EXPR} }}}}",
)


def _norm_expr(text: object) -> str:
    """Whitespace- and quote-insensitive form of a workflow `if:` expression.

    A re-spacing or a re-quote is a VARIANT, not a mutant. The substring form of the
    filter check this replaced went red on exactly that for `paths:`, and a gate firing
    where nothing is wrong spends the attention a real firing needs.
    """
    return "".join(str(text or "").split()).replace('"', "'")


_ALLOWED_GUARDS = frozenset(_norm_expr(g) for g in ALLOWED_GUARDS)


def scope_decision(event: str, changed: list[str] | None) -> tuple[bool, str]:
    """Do this event's changed paths give the slow suites anything to read?

    THREE INPUTS FOR `changed`, NOT TWO, and the third is what keeps this fail-closed.
    `None` means the set could not be determined, and an unknown must never read as
    "nothing to do" -- it runs the suites. An EMPTY list is treated the same way: no pull
    request changes zero files, so an empty diff is a broken computation wearing the shape
    of a result, which is the shape rule 12 is about.
    """
    if event != "pull_request":
        return True, (
            f"event={event or '(unset)'}: the filter narrows pull requests only. push, "
            f"schedule and workflow_dispatch run the whole suite, and that is what checks "
            f"the filter's claim")
    if changed is None:
        return True, ("the changed-path set could not be determined; running the whole "
                      "suite, because an unknown is not 'nothing to do'")
    if not changed:
        return True, ("the changed-path set came back EMPTY, which no pull request can be; "
                      "treating it as undetermined and running the whole suite")
    hit = sorted(p for p in changed if matches_filter(p))
    if hit:
        return True, (f"{len(hit)} of {len(changed)} changed paths are read by these "
                      f"suites, first few: {hit[:8]}")
    return False, f"0 of {len(changed)} changed paths are read by these suites"


def _git(*args: str) -> str:
    proc = subprocess.run(["git", *args], capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise DataError(
            f"git {' '.join(args)}: exit {proc.returncode}: {proc.stderr.strip()}")
    return proc.stdout


def pull_request_changed_paths(git=_git, base_ref: str | None = None) -> list[str] | None:
    """This pull request's accumulated diff against its base, or None if undeterminable.

    THE ACCUMULATED DIFF, deliberately. That is the population `on: paths:` was evaluated
    over, and task 124 measured that narrowing it to the latest push would have been
    fail-open on every opportunity it had -- `main` moves in a filtered path inside the
    window. Keeping the population identical is what makes this a move of the filter
    rather than a change to it.

    On a `pull_request` event GitHub checks out its own merge commit, whose FIRST parent is
    the base tip and whose second is the pull request head. `diff <parent1> HEAD` is that
    population exactly, with no extra fetch and no API call -- and so no 300-file compare
    cap to walk past. The `merge-base` arm is the fallback for a checkout that is not the
    merge commit.

    Returns None rather than raising: every failure here means "run everything"
    (`scope_decision`), never "nothing to do".
    """
    if base_ref is None:
        base_ref = os.environ.get("GITHUB_BASE_REF", "")
    try:
        fields = git("rev-list", "--parents", "-n", "1", "HEAD").split()
        if len(fields) >= 3:
            base = fields[1]
        elif base_ref:
            base = git("merge-base", f"origin/{base_ref}", "HEAD").strip()
        else:
            return None
        if not base:
            return None
        out = git("diff", "--name-only", base, "HEAD")
    except DataError:
        return None
    return [ln for ln in out.splitlines() if ln.strip()]


def emit_scope(event: str | None = None,
               changed: list[str] | None = None,
               output_path: str | None = None) -> int:
    """Decide, print what was read, and write `relevant=` where the workflow can see it.

    It prints the filter and the changed paths as well as the verdict, because what the
    instrument consumed is worth more than the verdict it produced -- a skipped `controls`
    run has to be auditable after the fact, or it is exactly the green-and-measured-nothing
    run the guard exists to avoid.
    """
    if event is None:
        event = os.environ.get("GITHUB_EVENT_NAME", "")
    if changed is None and event == "pull_request":
        changed = pull_request_changed_paths()
    relevant, why = scope_decision(event, changed)
    word = "true" if relevant else "false"
    print(f"controls scope: relevant={word}")
    print(f"  filter:  {' '.join(list(FILTER_PREFIXES) + list(FILTER_EXACT))}")
    print(f"  because: {why}")
    if changed is not None:
        print(f"  changed: {len(changed)} paths")
        for p in changed[:40]:
            print(f"    {p}")
        if len(changed) > 40:
            print(f"    ... and {len(changed) - 40} more")
    if output_path is None:
        output_path = os.environ.get("GITHUB_OUTPUT")
    if output_path:
        # Unwritable is an ERROR, not a false: an unwritten output reads as the empty
        # string, which the `!= 'false'` guard runs, and the non-zero exit reddens the job.
        with open(output_path, "a", encoding="utf-8") as fh:
            fh.write(f"relevant={word}\n")
    return 0


def _import_yaml():
    import yaml
    return yaml


def _parse_workflow(text: str, label: str, import_yaml=_import_yaml) -> tuple[dict, list[str]]:
    """Parse one workflow into a mapping. NEVER RAISES; returns what went wrong instead.

    Every caller here is a check, and a check that raises produces no verdict at all --
    its caller sees a traceback where it expected a list of problems, which is strictly
    worse than a red row. There are 4 ways the parse can fail to give a mapping and each
    used to raise from a different line: pyyaml not installed, unparseable YAML, an empty
    document, and a root that is a scalar or a list. The pyyaml one was handled in
    `filter_problems` and nowhere else, so `--gates` tracebacked past it -- the refusal
    belongs at the address the parse happens, not at one of its callers (rule 12).

    `import_yaml` is an injection point for the selftest and nothing in production passes
    it; it is a callable rather than a patched module attribute so the control states its
    own expectation instead of importing it from the subject.
    """
    try:
        yaml = import_yaml()
    except ImportError:
        return {}, [f"pyyaml is missing, so {label} could not be parsed. "
                    f"That is a refusal, not a passing check"]
    try:
        doc = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        return {}, [f"{label} does not parse as YAML: {exc.__class__.__name__}. "
                    f"Nothing that reads it could be checked"]
    if doc is None:
        return {}, [f"{label} is empty, so it declares no workflow at all"]
    if not isinstance(doc, dict):
        return {}, [f"{label}'s root is {type(doc).__name__}, not a mapping"]
    return doc, []


def _workflow_jobs(doc: dict) -> tuple[dict, str | None]:
    """(the jobs mapping, or a reason there is not one).

    IT RETURNS A REASON RATHER THAN AN EMPTY MAPPING, and that is the difference between a
    refusal and a confident zero. `jobs: 1`, `jobs: []` and a missing `jobs:` block all
    collapse to "no jobs" if you only ask `isinstance(..., dict)`, and a census over no
    jobs publishes `0 gates` at exit 0 -- a number, in range, and wrong, which is the one
    pattern this repository exists to catch. Raised by CodeRabbit on PR #16.
    """
    jobs = doc.get("jobs")
    if jobs is None:
        return {}, "declares no `jobs:` block at all"
    if not isinstance(jobs, dict):
        return {}, f"`jobs:` is {type(jobs).__name__}, not a mapping"
    if not jobs:
        return {}, "`jobs:` is an empty mapping"
    return jobs, None


def _job_steps(job: object) -> tuple[list[dict], str | None]:
    """(the step mappings of one job, or a reason the `steps:` block is unusable)."""
    if not isinstance(job, dict):
        return [], f"the job is {type(job).__name__}, not a mapping"
    raw = job.get("steps")
    if raw is None:
        return [], None
    if not isinstance(raw, list):
        return [], (f"`steps: {raw!r}` is {type(raw).__name__}, not a list. Iterating it "
                    f"raises instead of reporting")
    return [s for s in raw if isinstance(s, dict)], None


def filter_problems(controls_text: str, gates_text: str | None = None,
                    import_yaml=_import_yaml) -> list[str]:
    """Is `controls.yml` still wired so that it ALWAYS reports, and never runs nothing?

    Two properties, and they pull in opposite directions -- which is why both are gated:

      1. NEITHER `pull_request` NOR `push` MAY DECLARE `paths:`. A filtered workflow whose
         paths do not match produces no check rather than a passing one, and `controls` is
         required, so a trigger-level filter is a permanent merge block on any pull request
         touching none of those paths. This check used to assert the opposite.
      2. EVERY `run:` STEP AFTER THE SCOPE STEP CARRIES THE GUARD, spelled `!= 'false'`.
         That is what stops the fix from becoming the failure this project exists to catch:
         a green run that executed no gate. An output the scope step never wrote is the
         empty string, which `!= 'false'` runs and `== 'true'` would skip.

    PARSED, never substring-matched, for a reason the version this replaced measured: its
    first form asked `if "'.claude/**'" not in text` over the whole file, and the mutant
    deleting that path from one of two filters survived, because the string was still there
    under the other. Both halves of that lesson are still live -- the per-step walk is what
    sees WHICH step lost its guard, and `_norm_expr` is what keeps a re-spaced or re-quoted
    guard from reddening a correct file.

    The filter's CONTENT is no longer checked here, because it is no longer spelled here:
    `FILTER_PREFIXES`/`FILTER_EXACT` are the single address, and `--selftest` gates them by
    deleting each entry and asserting some pinned path notices.

    Pure so the mutants can be planted on a STRING. Planting them on the real workflow
    file works and is what `skill_layout_control.py` does, but a control that rewrites
    `.github/workflows/controls.yml` can leave it broken if it dies mid-run, and this one
    has no need to touch a file at all.
    """
    problems: list[str] = []
    # EVERY `jobs.*.runs-on`, not `"ubuntu-latest" in text`. The substring form passes a
    # workflow holding one ubuntu job and one macOS job -- and macOS bills at 10x, Windows
    # at 2x, so the whole 1x multiplier under this tool's total would be wrong while the
    # check stayed green. It also passes on a stale COMMENT mentioning ubuntu-latest next
    # to a `runs-on: macos-latest`. Raised by CodeRabbit on PR #10; it is the same
    # substring-versus-parse defect the filter check was repaired for, one field away.
    parsed: dict[str, dict] = {}
    for label, text in (("controls.yml", controls_text), ("gates.yml", gates_text)):
        if text is None:
            continue
        doc, bad = _parse_workflow(text, label, import_yaml)
        problems += bad
        if not bad:
            parsed[label] = doc
    if "controls.yml" not in parsed:
        return problems

    for label, wf in parsed.items():
        jobs, no_jobs = _workflow_jobs(wf)
        if no_jobs:
            problems.append(f"{label} {no_jobs}")
            continue
        for job_name, job in jobs.items():
            runs_on = job.get("runs-on") if isinstance(job, dict) else None
            labels = runs_on if isinstance(runs_on, list) else [runs_on]
            if [x for x in labels if x != "ubuntu-latest"]:
                problems.append(
                    f"{label}: job `{job_name}` runs on {runs_on!r}, not ubuntu-latest. "
                    f"macOS bills at 10x and Windows at 2x, so the 1x multiplier this tool "
                    f"applies would be wrong")

    doc = parsed["controls.yml"]
    # YAML 1.1 resolves a bare `on:` key to the boolean True, so `doc["on"]` is a KeyError
    # and `doc.get("on", {})` would silently check nothing at all.
    triggers = doc.get(True, doc.get("on"))
    if not isinstance(triggers, dict):
        return problems + ["controls.yml has no parseable `on:` block"]

    # BOTH KEYS. `paths-ignore:` is the same deadlock spelled the other way round -- a
    # pull request whose every changed path matches it dispatches nothing, and a required
    # check that never reports blocks the merge exactly as hard. Raised by CodeRabbit on
    # PR #16; checking only `paths:` was an enumeration of the instance that happened to
    # be there, which is the failure AGENTS.md's rule audit is about.
    for event in ("pull_request", "push"):
        cfg = triggers.get(event)
        if not isinstance(cfg, dict):
            continue
        for key in ("paths", "paths-ignore"):
            if cfg.get(key):
                problems.append(
                    f"controls.yml's `{event}` trigger declares `{key}: "
                    f"{sorted(cfg[key])}`. A workflow that does not dispatch produces NO "
                    f"check, not a passing one, and `controls` is a required check -- so "
                    f"this blocks every pull request the filter excludes (measured on "
                    f"PR #14). The filter belongs in the `{SCOPE_STEP_ID}` step")

    # ONE JOB, and the walk below is over ITS steps. Reading only the first of several
    # would be fail-open in the direction that matters: a second `ubuntu-latest` job
    # carrying an unguarded `run:` step passes every check here while executing controls
    # work with no scope output behind it. Raised by CodeRabbit on PR #16, and the same
    # first-entry defect the `runs-on` loop above was repaired for on PR #10.
    #
    # Refusing a second job rather than validating each is the stricter reading, and it is
    # the one the design supports: the guard is per-job -- `steps.scope.outputs.relevant`
    # names a step in the SAME job -- so a second job would need its own scope step, and it
    # would also be a second required check that can be absent, which is why `DECISIONS.md`
    # rejects the two-job form.
    jobs, no_jobs = _workflow_jobs(doc)
    if no_jobs:
        return problems + [f"controls.yml {no_jobs}"]
    if len(jobs) != 1:
        return problems + [
            f"controls.yml declares {len(jobs)} jobs, not 1. The scope guard is per-JOB -- "
            f"`steps.scope.outputs.relevant` reads a step in the same job -- so a second "
            f"job runs unguarded, and it is also a second check that can be absent"]
    steps, bad_steps = _job_steps(next(iter(jobs.values())))
    if bad_steps:
        return problems + [f"controls.yml's job: {bad_steps}"]
    scoped = [i for i, s in enumerate(steps) if s.get("id") == SCOPE_STEP_ID]
    if len(scoped) != 1:
        return problems + [
            f"controls.yml has {len(scoped)} steps with `id: {SCOPE_STEP_ID}`, not 1. "
            f"Without exactly one, every `if:` below references an output nothing writes "
            f"and the guard's meaning cannot be checked at all"]
    at = scoped[0]
    if SCOPE_INVOCATION not in " ".join(str(steps[at].get("run") or "").split()):
        problems.append(
            f"controls.yml's `{SCOPE_STEP_ID}` step does not run `{SCOPE_INVOCATION}`, so "
            f"whatever writes `relevant` is no longer this tool and is not gated by it")

    for i, step in enumerate(steps):
        if "run" not in step or i == at:
            continue
        label = step.get("name") or str(step["run"]).strip().splitlines()[0][:60]
        if i < at:
            problems.append(
                f"controls.yml step `{label}` runs BEFORE the `{SCOPE_STEP_ID}` step, so "
                f"its guard reads an output that does not exist yet")
        if _norm_expr(step.get("if")) not in _ALLOWED_GUARDS:
            problems.append(
                f"controls.yml step `{label}` carries `if: {step.get('if')!r}`, which is "
                f"not one of the {len(ALLOWED_GUARDS)} accepted guards: "
                f"{list(ALLOWED_GUARDS)}. Unguarded, it runs on a pull request whose "
                f"toolchain steps were skipped and fails there -- the merge block this "
                f"shape exists to remove. Guarded the other way round (`== 'true'`) it "
                f"skips on an unwritten output and reports a green `controls` that "
                f"executed nothing")
    return problems


def _read_workflow(label: str) -> str:
    return (ROOT / ".github" / "workflows" / label).read_text(encoding="utf-8")


def gate_census(texts: dict[str, str] | None = None,
                import_yaml=_import_yaml, read=_read_workflow) -> dict[str, dict]:
    """How many CHECKS each workflow runs, as a count with a producer behind it.

    `.github/workflows/README.md` opened with a hand-written "32 documentation, queue and
    selftest gates" that was stale by 3 and that nothing could disagree with, which is the
    shape AGENTS.md names: a count with a producer goes stale for an hour, a count with
    none goes stale forever.

    A step is a GATE if its `run:` invokes something under `eval/` - that is what makes it
    this repository's check rather than toolchain setup. Classifying on the step NAME would
    read "install ffmpeg (judge/audio.py's measuring instrument)" as a gate; it is apt-get.

    THE SCOPE STEP IS NEITHER, and it is excluded by its `id` rather than left to fall on
    one side. It runs `eval/tools/ci_minutes.py`, so the `eval/` test would score it a
    sixth gate in `controls.yml` while it checks nothing about the repository -- it decides
    whether the five below have anything to read. It is reported in its own bucket, because
    a step silently dropped from a census is how a count starts lying.

    EVERY job, not the first. Both workflows declare one today and `filter_problems`
    refuses a second in `controls.yml`, but a census that reads one job of several reports
    a count lower than the truth while staying green -- and a published count that can only
    go wrong downwards is the worst direction for this one.

    IT NEVER RAISES, and that is not tidiness either. `_selftest` calls this BEFORE
    `filter_problems`, so a live `controls.yml` that does not parse, or whose `steps:` is a
    scalar, used to produce a traceback here -- ahead of the diagnostics written for
    exactly those shapes, which never ran. What it cannot read it records in `malformed`
    and counts as nothing; `--gates` prints that list and `--selftest` asserts it is empty.
    Raised by CodeRabbit on PR #16, and it shares its loader with `filter_problems` so the
    two cannot disagree about what a workflow is.

    `texts` overrides the files, so the malformed shapes can be driven from a STRING and no
    control ever rewrites `.github/workflows/`.
    """
    out: dict[str, dict] = {}
    for wf in ("gates", "controls"):
        label = f"{wf}.yml"
        # THE READ IS PART OF THE CHECK. A deleted, renamed or unreadable workflow raised
        # `OSError` here, one line before the loader that exists so nothing raises -- so
        # the address that matters most (rule 12: a check aimed at a path nobody verified)
        # was the one place that could still traceback. Raised by CodeRabbit on PR #16.
        if texts is not None:
            text = texts.get(label, "")
        else:
            try:
                text = read(label)
            except OSError as exc:
                out[wf] = {"gates": 0, "setup": 0, "scope": 0, "names": [],
                           "malformed": [f"{label} could not be read: "
                                         f"{exc.__class__.__name__}: {exc}"]}
                continue
        doc, malformed = _parse_workflow(text, label, import_yaml)
        jobs, no_jobs = (({}, None) if malformed else _workflow_jobs(doc))
        if no_jobs:
            malformed.append(f"{label} {no_jobs}")
        run_steps: list[dict] = []
        for job_name, job in jobs.items():
            steps, bad = _job_steps(job)
            if bad:
                malformed.append(f"{label}: job `{job_name}`: {bad}")
            run_steps += [s for s in steps if "run" in s]
        scope = [s for s in run_steps if s.get("id") == SCOPE_STEP_ID]
        steps = [s for s in run_steps if s.get("id") != SCOPE_STEP_ID]
        gates = [s for s in steps if "eval/" in str(s["run"])]
        out[wf] = {
            "gates": len(gates),
            "setup": len(steps) - len(gates),
            "scope": len(scope),
            "malformed": malformed,
            "names": [(s.get("name") or str(s["run"]).strip().splitlines()[0])[:80]
                      for s in gates],
        }
    return out


def path_filter_audit(runs: list[dict], compare) -> dict:
    """For each `controls` PR run after the first on its branch, did the LATEST PUSH touch
    a filter path?

    `compare(base_sha, head_sha) -> list[str]` supplies the push's own diff. The first run
    on a branch has no predecessor, so its push range IS the whole-PR diff; it matches by
    construction and is reported in its own bucket rather than counted as evidence either
    way.

    IT REPORTS ONE MEASUREMENT AND NO LONGER DRAWS AN INFERENCE FROM IT. Until 2026-08-24
    a `no-match` row meant "this run was bought by the accumulated diff", and that reading
    rested on the run's mere existence: GitHub dispatched a `pull_request` workflow only
    when its `paths:` filter matched. **`controls.yml` declares no `paths:` any more** --
    it runs on every pull request and decides inside the job -- so the run existing says
    nothing about any diff, and the old conclusion would now be drawn from a premise that
    is false. What survives is exactly the half that was ever measured here: whether the
    LATEST PUSH touched a path the suites read.

    For runs from 2026-08-24 onward the question this was built to answer is answered
    directly by the run itself: the scope step prints the filter, the changed paths and
    its verdict into the log. This is the historical instrument, and its rows about earlier
    runs stand.

    THE RANGE IS ONE PUSH ONLY BECAUSE `controls` RAN ON EVERY PUSH, which is checked
    rather than assumed: `gates` carries no path filter, and its run count equals
    `controls`' on every branch measured (7/7, 1/1, 3/3, 3/3, 4/4 on 2026-08-23). Were
    that to stop holding, consecutive `controls` runs would bracket more than one push and
    a `no-match` row would understate rather than overstate -- it fails toward reporting
    fewer wasted runs, never more.
    """
    controls = [
        r for r in runs if r.get("name") == "controls" and r.get("event") == "pull_request"
    ]
    controls.sort(key=lambda r: r["created_at"])
    by_branch: dict[str, list] = {}
    for r in controls:
        by_branch.setdefault(r.get("head_branch") or "?", []).append(r)

    rows, first_on_branch = [], 0
    for branch, rs in by_branch.items():
        for i, r in enumerate(rs):
            if i == 0:
                first_on_branch += 1
                continue
            prev = rs[i - 1]
            if prev["head_sha"] == r["head_sha"]:
                rows.append(
                    {"run": r["id"], "branch": branch, "verdict": "same-sha", "files": []}
                )
                continue
            files = compare(prev["head_sha"], r["head_sha"])
            # The truncation guard lives HERE, at the point the verdict is decided, and
            # not only in the API adapter that happens to be today's `compare`. Truncation
            # only does damage by turning an unknown into `no-match`, and that conversion
            # happens on the next line -- so this is the address the check belongs at
            # (AGENTS.md rule 12), and any `compare` implementation is covered by it.
            if len(files) >= COMPARE_FILE_LIMIT:
                raise DataError(
                    f"run {r['id']}: the compare returned {len(files)} files, at or past the "
                    f"{COMPARE_FILE_LIMIT}-file cap the endpoint imposes. A truncated list is "
                    f"indistinguishable from a complete one and would score `no-match` -- a "
                    f"wrong answer, not a missing one. Refusing to classify this push.")
            hit = [f for f in files if matches_filter(f)]
            rows.append(
                {
                    "run": r["id"],
                    "branch": branch,
                    "verdict": "match" if hit else "no-match",
                    "files": files,
                }
            )
    return {
        "controls_pr_runs": len(controls),
        "first_on_branch": first_on_branch,
        "analysed": len(rows),
        "match": sum(1 for r in rows if r["verdict"] == "match"),
        "no_match": sum(1 for r in rows if r["verdict"] == "no-match"),
        "same_sha": sum(1 for r in rows if r["verdict"] == "same-sha"),
        "rows": rows,
    }


# ---------------------------------------------------------------- reading the endpoint


def _gh(endpoint: str, jq: str) -> list[str]:
    argv = ["gh", "api", "--paginate", endpoint, "--jq", jq]
    proc = subprocess.run(argv, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise DataError(f"{endpoint}: gh exited {proc.returncode}: {proc.stderr.strip()}")
    return [ln for ln in proc.stdout.splitlines() if ln.strip()]


def fetch_runs() -> list[dict]:
    lines = _gh(
        f"repos/{REPO}/actions/runs?per_page=100",
        ".workflow_runs[] | {id, name, event, head_branch, status, conclusion, "
        "created_at, run_started_at, head_sha}",
    )
    if not lines:
        raise DataError("the runs endpoint returned no runs -- a refusal, not 0 minutes")
    return [json.loads(ln) for ln in lines]


def fetch_jobs(run_ids: list[int]) -> list[dict]:
    out = []
    for rid in run_ids:
        lines = _gh(
            f"repos/{REPO}/actions/runs/{rid}/jobs?per_page=100",
            f".jobs[] | {{run_id: {rid}, job_id: .id, name, status, conclusion, "
            "started_at, completed_at}",
        )
        if not lines:
            raise DataError(f"run {rid} reported no jobs -- a refusal, not 0 minutes")
        out.extend(json.loads(ln) for ln in lines)
    return out


def fetch_billable_field(run_ids: list[int]) -> dict[int, int]:
    """Read `billable.UBUNTU.total_ms` for the audit trail. NOT used for the total.

    Recording what the instrument saw is the point: this is the field whose name says it is
    the answer, and stating that it was 0 across the whole population is what stops the next
    session trusting it (AGENTS.md, "capture what the instrument DID").
    """
    seen = {}
    for rid in run_ids:
        lines = _gh(
            f"repos/{REPO}/actions/runs/{rid}/timing", ".billable.UBUNTU.total_ms // -1"
        )
        seen[rid] = int(lines[0]) if lines else -1
    return seen


# GitHub's compare endpoint returns at most this many entries in `files`, and `--paginate`
# does NOT paginate that array -- it paginates commits. A push larger than this whose only
# filtered path sits past the cut would come back with no match and be scored `no-match`,
# which is a silent misclassification rather than an error. Raised by CodeRabbit on PR #10.
COMPARE_FILE_LIMIT = 300


def compare_via_api(base: str, head: str) -> list[str]:
    """The push's own changed files, or a refusal if the list may be truncated.

    FAILS CLOSED AT THE BOUNDARY. A truncated list cannot be distinguished from a complete
    one by its contents, so the only safe reading of `len(files) >= 300` is "I do not know".
    Measured over the 13 compares this audit performs on 2026-08-23, the largest returned
    **59** files, so no published figure here is affected -- but a check that is correct
    only for the data that happens to exist is the shape this repository exists to catch.
    """
    files = _gh(f"repos/{REPO}/compare/{base}...{head}", ".files[]?.filename")
    if len(files) >= COMPARE_FILE_LIMIT:
        raise DataError(
            f"compare {base[:12]}...{head[:12]} returned {len(files)} files, at or past the "
            f"{COMPARE_FILE_LIMIT}-file cap the endpoint imposes. The list may be truncated, "
            f"and a truncated list scores as `no-match` -- which is a wrong answer, not a "
            f"missing one. Refusing to classify this push.")
    return files


# ---------------------------------------------------------------- the controls


@contextlib.contextmanager
def contextlib_redirect_all():
    """Capture stdout and stderr together, and hand back a reader for what was written.

    `gates_report` writes its refusal to stderr and its payload to stdout, and a selftest
    that let either through would bury its own verdict under the fixtures' output.
    """
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        yield buf.getvalue


def _selftest() -> int:
    failures: list[str] = []
    # The producer for "how many mutants does this gate carry". `.github/workflows/README.md`
    # states those counts, and a count with no producer goes stale forever.
    counts = {"mutants": 0, "variants": 0}

    def check(name: str, got, want):
        if got != want:
            failures.append(f"{name}: got {got!r}, want {want!r}")

    # -- the boundary, and the mutant it exists to kill ---------------------------------
    # Truncation is the plausible wrong implementation, and it is what this tool was first
    # written with on purpose. The 22s and 61s rows are what separate it from ceil; a
    # fixture set of whole minutes only would let that mutant survive.
    # -- the gate census, and what it must not count ------------------------------------
    # The count `.github/workflows/README.md` publishes. Pinned so the register cannot
    # drift from the workflows again: it said 32 for long enough to be wrong by 3.
    _cen = gate_census()
    check("gates.yml gate count", _cen["gates"]["gates"], 39)
    check("controls.yml gate count", _cen["controls"]["gates"], 5)
    # Setup is not a gate. controls.yml installs just and ffmpeg; classifying on the step
    # NAME would score "install ffmpeg (judge/audio.py's measuring instrument)" as a check.
    check("controls.yml setup is not counted", _cen["controls"]["setup"], 5)
    check("gates.yml has one setup step", _cen["gates"]["setup"], 1)
    # VARIANT: a step whose NAME mentions eval/ but whose body is apt-get must not count.
    check("no gate name is an apt-get line",
          [n for n in _cen["controls"]["names"] if "apt-get" in n], [])
    # VARIANT: the scope step runs `eval/tools/ci_minutes.py`, so the `eval/` test would
    # score it a sixth gate. It is one step, in its own bucket, and in neither of the two.
    check("the scope step is counted as itself", _cen["controls"]["scope"], 1)
    check("and not as a gate", [n for n in _cen["controls"]["names"] if "scope" in n], [])
    check("gates.yml has no scope step", _cen["gates"]["scope"], 0)
    # The live files must be well-formed, and this is the check that says so rather than
    # the census raising on its way past. It runs BEFORE filter_problems, so without it a
    # malformed live workflow produces a traceback ahead of every diagnostic written for
    # that shape (CodeRabbit, PR #16).
    check("neither live workflow is malformed",
          _cen["gates"]["malformed"] + _cen["controls"]["malformed"], [])
    # And the census itself must REPORT each malformed shape rather than raise. A mutant
    # here is a whole workflow text, and the assertion is that the call returns at all.
    _malformed = {
        "unparseable YAML": "jobs:\n  controls:\n\tbad: [\n",
        "a scalar root": "just a string\n",
        "an empty document": "",
        "a list root": "- one\n- two\n",
        "steps: given as a scalar": "jobs:\n  controls:\n    steps: 1\n",
        "a job that is not a mapping": "jobs:\n  controls: 7\n",
        # The 3 shapes that used to collapse to "no jobs" and publish a confident 0.
        "jobs: given as a scalar": "name: x\njobs: 1\n",
        "jobs: given as a list": "name: x\njobs: []\n",
        "no jobs: block at all": "name: x\non:\n  push:\n",
    }
    for _name, _text in _malformed.items():
        try:
            _got = gate_census({"controls.yml": _text, "gates.yml": _text})
        except Exception as _exc:  # noqa: BLE001 - the point is that nothing escapes
            failures.append(f"gate_census RAISED on {_name}: {_exc!r}. A census that "
                            f"raises reports nothing, and it runs before every diagnostic")
            continue
        if not _got["controls"]["malformed"]:
            failures.append(f"gate_census did not report {_name} as malformed -- it "
                            f"published 0 gates at exit 0, which is a confident zero")
        if _got["controls"]["gates"]:
            failures.append(f"gate_census counted {_got['controls']['gates']} gates in a "
                            f"workflow it could not read ({_name})")
        # BOTH OUTPUT MODES. The refusal lived in the text branch alone, so `--json`
        # returned 0 over a census that had already said it could not read the file.
        for _as_json in (False, True):
            with contextlib_redirect_all() as _sink:
                _code = gates_report(_got, as_json=_as_json)
            if _code != 2:
                failures.append(f"gates_report(as_json={_as_json}) returned {_code} on "
                                f"{_name}; a malformed census must refuse in BOTH modes")
            if _as_json and "malformed" not in _sink():
                failures.append("the --json payload does not carry `malformed`, so a "
                                "consumer cannot see what was unreadable")
    # PYYAML NOT INSTALLED. It is the 4th way the parse fails to give a mapping, it was
    # handled in `filter_problems` and nowhere else, and `--gates` tracebacked straight
    # past it. `_no_yaml` is an independent statement of the failure, not the subject's own
    # (rule 12's addendum), and it is injected rather than patched onto the module.
    def _no_yaml():
        raise ImportError("No module named 'yaml'")

    try:
        _doc, _why = _parse_workflow("jobs:\n  controls:\n", "controls.yml", _no_yaml)
    except Exception as _exc:  # noqa: BLE001 - the point is that nothing escapes
        failures.append(f"_parse_workflow RAISED without pyyaml: {_exc!r}. The refusal "
                        f"belongs where the parse happens, not at one of its callers")
        _doc, _why = {}, []
    else:
        check("without pyyaml the parse refuses", (_doc, len(_why)), ({}, 1))
        check("and says pyyaml is what is missing",
              "pyyaml is missing" in (_why[0] if _why else ""), True)
    try:
        _cen_noyaml = gate_census({"controls.yml": "jobs:\n", "gates.yml": "jobs:\n"},
                                  _no_yaml)
    except Exception as _exc:  # noqa: BLE001 - the point is that nothing escapes
        failures.append(f"gate_census RAISED without pyyaml: {_exc!r}")
        _cen_noyaml = None
    if _cen_noyaml is not None:
        check("the census reports it rather than counting 0 gates",
              (bool(_cen_noyaml["controls"]["malformed"]), _cen_noyaml["controls"]["gates"]),
              (True, 0))
        for _as_json in (False, True):
            with contextlib_redirect_all():
                _code = gates_report(_cen_noyaml, as_json=_as_json)
            if _code != 2:
                failures.append(f"gates_report(as_json={_as_json}) returned {_code} with "
                                f"pyyaml missing; --gates must refuse, not traceback")
    try:
        _fp = filter_problems("jobs:\n  controls:\n", "jobs:\n", _no_yaml)
        check("filter_problems refuses without pyyaml too", len(_fp) >= 1, True)
    except Exception as _exc:  # noqa: BLE001
        failures.append(f"filter_problems RAISED without pyyaml: {_exc!r}")

    # THE READ ITSELF. A deleted, renamed or unreadable workflow raised `OSError` one line
    # before the loader that exists so nothing raises -- the address that matters most was
    # the one place left that could traceback.
    def _unreadable(_label):
        raise FileNotFoundError(2, "No such file or directory", "/nowhere/controls.yml")

    try:
        _cen_noread = gate_census(None, _import_yaml, _unreadable)
    except Exception as _exc:  # noqa: BLE001 - the point is that nothing escapes
        failures.append(f"gate_census RAISED on an unreadable workflow: {_exc!r}")
        _cen_noread = None
    if _cen_noread is not None:
        check("an unreadable workflow is reported, not counted",
              (bool(_cen_noread["controls"]["malformed"]),
               _cen_noread["controls"]["gates"], _cen_noread["gates"]["gates"]),
              (True, 0, 0))
        for _as_json in (False, True):
            with contextlib_redirect_all():
                _code = gates_report(_cen_noread, as_json=_as_json)
            if _code != 2:
                failures.append(f"gates_report(as_json={_as_json}) returned {_code} on an "
                                f"unreadable workflow; --gates must refuse, not traceback")
    # VARIANT: the injected reader must not have replaced the real one -- a default that
    # no longer reads the files would make every pin above vacuous.
    check("the default reader still reads the real workflows",
          gate_census(None, _import_yaml)["controls"]["gates"], 5)

    # VARIANT: a clean census must still be published, and exit 0, in both modes.
    for _as_json in (False, True):
        with contextlib_redirect_all():
            _code = gates_report(_cen, as_json=_as_json)
        if _code != 0:
            failures.append(f"gates_report(as_json={_as_json}) refused a CLEAN census "
                            f"({_code}) -- the refusal fires where nothing is wrong")
    # VARIANT: the real files must still come back with an empty `malformed` and the counts
    # above -- the tolerance must not have made the census tolerant of a real workflow.
    _live = {f"{w}.yml": (WORKFLOW_DIR / f"{w}.yml").read_text() for w in ("gates", "controls")}
    check("driving the census from text matches reading the files",
          gate_census(_live), _cen)

    check("22s bills a whole minute", billable_minutes(22), 1)
    check("60s is exactly 1", billable_minutes(60), 1)
    check("61s rounds up to 2", billable_minutes(61), 2)
    check("594s rounds up to 10", billable_minutes(594), 10)
    check("588s rounds up to 10", billable_minutes(588), 10)

    # -- the third value ----------------------------------------------------------------
    running = {"started_at": "2026-08-23T18:24:35Z", "completed_at": None}
    check("an in-flight job has no duration", job_seconds(running), None)
    done = {"started_at": "2026-08-23T18:11:50Z", "completed_at": "2026-08-23T18:21:38Z"}
    check("a finished job measures its wall clock", job_seconds(done), 588.0)
    # ruff reports DTZ007 twice against job_seconds and cannot see through the _TS
    # constant to the `%z` in it. This is the pin that settles which of us is right, and
    # it is the defect that made the whole timezone question worth gating.
    check("stamps are parsed timezone-AWARE, not naive",
          dt.datetime.strptime(done["started_at"], _TS).tzinfo, dt.timezone.utc)

    runs = [
        {"id": 1, "name": "gates", "event": "push"},
        {"id": 2, "name": "controls", "event": "push"},
        {"id": 3, "name": "gates", "event": "push"},
    ]
    jobs = [
        {"run_id": 1, "conclusion": "success", **done},          # 588s -> 10
        {"run_id": 2, "conclusion": "failure",
         "started_at": "2026-08-23T15:29:30Z",
         "completed_at": "2026-08-23T15:29:52Z"},                # 22s  -> 1
        {"run_id": 3, "conclusion": None, **running},            # in flight
    ]
    rep = census(jobs, runs)
    check("total is the sum of per-job ceilings", rep["total_minutes"], 11)
    check("the in-flight job is counted separately", rep["jobs_in_flight"], 1)
    check("and is NOT in the total's population", rep["jobs_counted"], 2)
    # The variant: an unfinished job must not silently read as zero minutes. Pooled, the
    # total would still be 11 and only the population would betray it -- which is why this
    # asserts the population and not just the sum.
    check("per-workflow keeps the two apart", rep["per_workflow"]["gates"]["minutes"], 10)
    check("gates' bucket holds one job, not two", rep["per_workflow"]["gates"]["jobs"], 1)
    check("controls' own bucket", rep["per_workflow"]["controls"]["minutes"], 1)
    check("a FAILED job is still billed", rep["per_conclusion"]["failure"]["minutes"], 1)
    check("the window is reported", rep["first_job_started"], "2026-08-23T15:29:30Z")
    check("workflow x event is the lever's cell",
          rep["per_workflow_event"]["controls/push"]["minutes"], 1)

    # -- the filter, read out of the workflow rather than remembered --------------------
    controls_yml = WORKFLOW_DIR / "controls.yml"
    gates_yml = WORKFLOW_DIR / "gates.yml"
    for wf in (controls_yml, gates_yml):
        if not wf.is_file():
            failures.append(f"{wf} does not exist -- the address is an input (rule 12)")
    if controls_yml.is_file() and gates_yml.is_file():
        live = controls_yml.read_text()
        failures += filter_problems(live, gates_yml.read_text())

        # BOTH HALVES, on strings rather than on the real file. A mutant asks whether the
        # check CAN fail; only a variant asks whether it can still PASS on an input it
        # mishandles (AGENTS.md rule 15). The re-quote variant is not decoration: the
        # substring version this replaced went red on it, which is a gate firing where
        # nothing is wrong.
        def drop(text, needle, count=1):
            return text.replace(needle, "", count)

        scope_block = (
            "      - name: scope (does this pull request touch anything these suites"
            " read?)\n        id: scope\n"
            "        run: python3 eval/tools/ci_minutes.py --scope\n")
        gate_guard = ("        if: ${{ !cancelled() && steps.scope.outputs.relevant"
                      " != 'false' }}\n")
        version_step = ("      - name: just --version\n"
                        "        if: ${{ success() && steps.scope.outputs.relevant"
                        " != 'false' }}\n        run: just --version\n")
        audio_block = ("      - name: judge/audio_selftest\n" + gate_guard
                       + "        run: python3 eval/judge/audio_selftest.py\n")
        rusage_block = ("      - name: judge/rusage_selftest\n" + gate_guard
                        + "        run: python3 eval/judge/rusage_selftest.py\n")
        for _needle in (scope_block, gate_guard, version_step, audio_block, rusage_block):
            if _needle not in live:
                failures.append(
                    "a mutant's needle is not in controls.yml, so every mutant built on "
                    f"it is void rather than caught: {_needle.strip().splitlines()[0]!r}")

        mutants = {
            # THE DEFECT THIS SHAPE EXISTS TO PREVENT, one trigger at a time. A `paths:`
            # filter that does not match produces no check, and `controls` is required.
            "a paths: filter back on pull_request":
                live.replace("  pull_request:\n",
                             "  pull_request:\n    paths:\n      - 'eval/**'\n", 1),
            # The SAME deadlock spelled the other way round: a `paths-ignore:` matching
            # every changed path dispatches nothing, and a required check that never
            # reports blocks the merge just as hard.
            "a paths-ignore: filter on pull_request":
                live.replace("  pull_request:\n",
                             "  pull_request:\n    paths-ignore:\n      - '**.md'\n", 1),
            "a paths-ignore: filter on push":
                live.replace("  push:\n    branches: [main, 'ci-control-**']\n",
                             "  push:\n    branches: [main, 'ci-control-**']\n"
                             "    paths-ignore:\n      - '**.md'\n", 1),
            # CONTAINMENT IS NOT VALIDATION: this carries the guard's exact text and
            # skips every gate, which is the outcome the guard exists to prevent.
            "the guard conjoined with a constant false":
                live.replace("steps.scope.outputs.relevant != 'false' }}",
                             "steps.scope.outputs.relevant != 'false' && false }}"),
            "a paths: filter back on push":
                live.replace("  push:\n    branches: [main, 'ci-control-**']\n",
                             "  push:\n    branches: [main, 'ci-control-**']\n"
                             "    paths:\n      - 'eval/**'\n", 1),
            # THE OPPOSITE DEFECT: the guard stops meaning anything, and the job reports
            # green having executed no gate.
            "the scope step deleted": drop(live, scope_block),
            "the scope step's id renamed": live.replace("        id: scope\n",
                                                        "        id: whence\n", 1),
            "the scope step no longer runs --scope":
                live.replace("        run: python3 eval/tools/ci_minutes.py --scope\n",
                             '        run: echo "relevant=false" >> "$GITHUB_OUTPUT"\n', 1),
            "one gate loses its guard": drop(live, gate_guard),
            # The fail-OPEN spelling: an output the scope step never wrote is the empty
            # string, so `== 'true'` skips every suite on a step that did not run.
            "the guard flipped to == 'true'":
                live.replace("steps.scope.outputs.relevant != 'false'",
                             "steps.scope.outputs.relevant == 'true'"),
            "a guarded run: step placed before the scope step":
                live.replace(scope_block, version_step + scope_block, 1),
            # The first-entry defect, and the runs-on check CANNOT see this one: the second
            # job is ubuntu, so only the job-count refusal catches it. Raised on PR #16.
            "a second UBUNTU job carrying an unguarded gate":
                live.replace("jobs:\n  controls:\n    runs-on: ubuntu-latest",
                             "jobs:\n  extra:\n    runs-on: ubuntu-latest\n    steps:\n"
                             "      - run: python3 eval/judge/audio_selftest.py\n"
                             "  controls:\n    runs-on: ubuntu-latest"),
            # A scalar `steps:` used to raise TypeError rather than report, and a file that
            # does not parse used to raise ScannerError. A check that RAISES has no verdict
            # at all, which is not the same as a check that says no.
            "steps: given as a scalar":
                live.split("    steps:\n")[0] + "    steps: 1\n",
            "controls.yml no longer parses as YAML":
                live.replace("jobs:\n  controls:\n", "jobs:\n  controls:\n\tbad: [\n", 1),
            "the runner moved off ubuntu-latest":
                live.replace("runs-on: ubuntu-latest", "runs-on: macos-latest"),
            # The two the substring form passed. A mixed workflow still CONTAINS
            # "ubuntu-latest"; so does a macOS job with a stale comment beside it.
            "a second job on macOS alongside the ubuntu one":
                live.replace("jobs:\n  controls:\n    runs-on: ubuntu-latest",
                             "jobs:\n  extra:\n    runs-on: macos-latest\n"
                             "  controls:\n    runs-on: ubuntu-latest"),
            "macOS with a stale ubuntu-latest comment beside it":
                live.replace("runs-on: ubuntu-latest",
                             "runs-on: macos-latest  # was ubuntu-latest"),
            "runs-on given as a list containing a non-ubuntu label":
                live.replace("runs-on: ubuntu-latest",
                             "runs-on: [ubuntu-latest, self-hosted]"),
        }
        variants = {
            # The re-spacing and re-quoting one is not decoration: the substring form of
            # the check this replaced went red on a re-quote, and a gate firing where
            # nothing is wrong spends exactly the attention a real firing needs.
            "the guard re-spaced and double-quoted": live.replace(
                "steps.scope.outputs.relevant != 'false'",
                'steps.scope.outputs.relevant   !=   "false"'),
            "two gates swapped": live.replace(audio_block + rusage_block,
                                              rusage_block + audio_block, 1),
            "an unguarded `uses:` step, which needs no guard": live.replace(
                "      - uses: actions/setup-python@v6\n",
                "      - uses: actions/checkout@v5\n      - uses: actions/setup-python@v6\n",
                1),
            "a comment inside the job": live.replace(
                "    steps:\n", "    steps:\n      # a note\n", 1),
            "the scope step given an extra flag": live.replace(
                "ci_minutes.py --scope\n", "ci_minutes.py --scope --json\n", 1),
        }
        counts["mutants"] = len(mutants)
        counts["variants"] = len(variants)
        # A RAISE IS NOT A VERDICT, and reporting it as one is the difference between
        # "MUTANT SURVIVED: x" and a traceback whose reader has to work out which row it
        # came from. Several of the mutants below are deliberately malformed workflows,
        # which is exactly the input a check is most likely to raise on.
        def problems_of(text, name):
            try:
                return filter_problems(text, gates_yml.read_text())
            except Exception as exc:  # noqa: BLE001 - the point is that nothing escapes
                failures.append(f"filter_problems RAISED on '{name}': {exc!r}. A check "
                                f"that raises returns no verdict at all")
                return ["raised"]

        for name, text in mutants.items():
            if text == live:
                failures.append(f"mutant '{name}' changed nothing; it is void, not caught")
            elif not problems_of(text, name):
                failures.append(f"MUTANT SURVIVED: {name}")
        for name, text in variants.items():
            if text == live:
                failures.append(f"variant '{name}' changed nothing; it is void, not passed")
            elif problems_of(text, name):
                failures.append(f"FALSE POSITIVE on variant: {name}")

    # -- the filter's CONTENT, now that it is spelled once, in this file ----------------
    # It used to be spelled twice -- here and in the workflow's `paths:` -- and the gate
    # was that the two agree. With the filter moved into the scope step there is one
    # address, so the check that replaces it asks the FACT instead of the spelling: does
    # this path match, and is every entry load-bearing for some pinned path?
    pinned = {
        "eval/tools/tasks.py": True,
        ".agents/skills/work/SKILL.md": True,
        ".claude/skills/work/SKILL.md": True,
        ".github/workflows/controls.yml": True,
        ".github/workflows/README.md": False,
        "tasks/124-ci-path-filter.md": False,
        "README.md": False,
        # The variant: a filename that merely begins with a filtered directory's letters.
        "evaluation.md": False,
    }
    for path, want in pinned.items():
        check(f"{path} matches the filter" if want else f"{path} does NOT match",
              matches_filter(path), want)

    # Deleting one entry from FILTER_* is the mutant the workflow-drift check used to
    # catch. It has to die somewhere, so: every entry must be the reason some pinned path
    # matches. An entry no pin depends on could be dropped with the suite still green,
    # and the suites would then skip a change that does affect them.
    for entry in list(FILTER_PREFIXES) + list(FILTER_EXACT):
        without_p = tuple(x for x in FILTER_PREFIXES if x != entry)
        without_e = tuple(x for x in FILTER_EXACT if x != entry)
        depends = [p for p, want in pinned.items()
                   if want and not matches_filter(p, without_p, without_e)]
        if not depends:
            failures.append(
                f"deleting {entry!r} from the filter reddens no pin above -- that entry "
                f"is ungated, and dropping it would silently skip the suites")

    # -- the scope decision, and the three ways it must refuse to say "nothing to do" ---
    check("a doc-only pull request skips the suites",
          scope_decision("pull_request", ["README.md", "tasks/9-x.md"])[0], False)
    check("one filtered path is enough to run them",
          scope_decision("pull_request", ["README.md", "eval/judge/bots.py"])[0], True)
    # The three fail-CLOSED arms. Each of these is a state in which the honest answer is
    # "I do not know", and the dangerous reading of it is "nothing to do".
    check("an undetermined diff runs everything",
          scope_decision("pull_request", None)[0], True)
    check("an EMPTY diff is undetermined, not empty",
          scope_decision("pull_request", [])[0], True)
    check("push runs everything", scope_decision("push", ["README.md"])[0], True)
    check("schedule runs everything", scope_decision("schedule", None)[0], True)
    check("an unset event runs everything", scope_decision("", ["README.md"])[0], True)

    # `pull_request_changed_paths` against a stubbed git, both arms and the refusal.
    merge_head = "m" * 40 + " " + "b" * 40 + " " + "h" * 40

    def git_merge(*args):
        if args[0] == "rev-list":
            return merge_head + "\n"
        if args[0] == "diff":
            check("the diff is taken against the merge's FIRST parent", args[2], "b" * 40)
            return "README.md\neval/x.py\n\n"
        raise AssertionError(args)

    check("a merge checkout diffs parent1..HEAD",
          pull_request_changed_paths(git_merge, "main"), ["README.md", "eval/x.py"])

    def git_plain(*args):
        if args[0] == "rev-list":
            return "s" * 40 + "\n"
        if args[0] == "merge-base":
            check("the fallback asks origin/<base>", args[1], "origin/main")
            return "b" * 40 + "\n"
        if args[0] == "diff":
            return "tasks/1.md\n"
        raise AssertionError(args)

    check("a non-merge checkout falls back to merge-base",
          pull_request_changed_paths(git_plain, "main"), ["tasks/1.md"])

    def git_broken(*args):
        raise DataError("no such ref")

    check("a git failure is None, never an empty list",
          pull_request_changed_paths(git_broken, "main"), None)
    check("and with no base ref either, still None",
          pull_request_changed_paths(git_plain, ""), None)

    # The output file is the whole interface to the workflow, so pin what lands in it --
    # and pin the LOG too, because a skipped `controls` run is only auditable afterwards
    # if the step said what it read.
    import tempfile
    with tempfile.TemporaryDirectory() as _d:
        _out = os.path.join(_d, "gh_output")
        _log = io.StringIO()
        with contextlib.redirect_stdout(_log):
            emit_scope("pull_request", ["README.md"], _out)
            emit_scope("pull_request", ["eval/x.py"], _out)
            emit_scope("schedule", None, _out)
        with open(_out, encoding="utf-8") as fh:
            wrote = fh.read().split()
        check("the output file carries one relevant= per call",
              wrote, ["relevant=false", "relevant=true", "relevant=true"])
        _text = _log.getvalue()
        check("the log names the filter it applied", "eval/ .agents/ .claude/" in _text, True)
        check("the log names the path it skipped on", "README.md" in _text, True)
        check("the log states the verdict", _text.count("controls scope: relevant="), 3)

    # -- the audit, both directions, with a stubbed compare ------------------------------
    audit_runs = [
        {"id": 10, "name": "controls", "event": "pull_request", "head_branch": "b",
         "created_at": "2026-08-23T15:00:00Z", "head_sha": "a" * 40},
        {"id": 11, "name": "controls", "event": "pull_request", "head_branch": "b",
         "created_at": "2026-08-23T15:10:00Z", "head_sha": "b" * 40},
        {"id": 12, "name": "controls", "event": "pull_request", "head_branch": "b",
         "created_at": "2026-08-23T15:20:00Z", "head_sha": "c" * 40},
        {"id": 13, "name": "gates", "event": "pull_request", "head_branch": "b",
         "created_at": "2026-08-23T15:30:00Z", "head_sha": "d" * 40},
        {"id": 14, "name": "controls", "event": "push", "head_branch": "main",
         "created_at": "2026-08-23T15:40:00Z", "head_sha": "e" * 40},
    ]
    diffs = {
        ("a" * 40, "b" * 40): [".github/workflows/README.md"],   # no-match
        ("b" * 40, "c" * 40): ["eval/tools/tasks.py"],           # match
    }

    def fake_compare(base, head):
        return diffs[(base, head)]

    # The truncation guard, both directions. A compare list at the endpoint's cap may be
    # short of its own tail, and a missing filtered path there scores `no-match` -- a wrong
    # answer wearing the shape of a right one. 299 must classify; 300 must refuse.
    def capped_compare(_base, _head):
        return [f"docs/f{i}.md" for i in range(COMPARE_FILE_LIMIT)]

    try:
        path_filter_audit(audit_runs[:3], capped_compare)
        failures.append("a compare list at the 300-file cap was classified, not refused")
    except DataError:
        pass

    def under_cap_compare(_base, _head):
        return [f"docs/f{i}.md" for i in range(COMPARE_FILE_LIMIT - 1)]

    try:
        under = path_filter_audit(audit_runs[:3], under_cap_compare)
        check("299 files still classify, as no-match", under["no_match"], 2)
    except DataError:
        failures.append("FALSE POSITIVE: a 299-file compare was refused as truncated")

    aud = path_filter_audit(audit_runs, fake_compare)
    check("only controls PR runs are in scope", aud["controls_pr_runs"], 3)
    check("the first run on a branch is not evidence", aud["first_on_branch"], 1)
    check("two runs analysed", aud["analysed"], 2)
    check("one bought by the whole-PR diff", aud["no_match"], 1)
    check("one genuinely needed", aud["match"], 1)

    if failures:
        print("ci_minutes --selftest: FAIL")
        for f in failures:
            print(f"  {f}")
        return 1
    print("ci_minutes --selftest: ok "
          "(billing arithmetic, the third value, the scope guard, the audit); "
          f"{counts['mutants']} mutants died, {counts['variants']} variants passed")
    return 0


# ---------------------------------------------------------------- reporting


def _print_census(rep: dict, billable_field: dict[int, int] | None) -> None:
    print("GitHub Actions minutes consumed, read from the API, not estimated")
    print(f"  repository : {REPO}  (PRIVATE -- these minutes are metered)")
    print("  runners    : ubuntu-latest, billed at the 1x Linux multiplier")
    print("  unit       : per JOB, wall clock rounded UP to the whole minute")
    print()
    print(f"  BILLABLE MINUTES TO DATE : {rep['total_minutes']}")
    print(f"  population               : {rep['jobs_counted']} completed jobs")
    print(f"  raw wall clock           : {rep['raw_seconds'] / 60:.1f} min "
          f"(rounding up costs {rep['total_minutes'] - rep['raw_seconds'] / 60:.1f})")
    print(f"  window                   : {rep['first_job_started']} .. "
          f"{rep['last_job_started']}")
    if rep["jobs_in_flight"]:
        print(f"  NOT counted              : {rep['jobs_in_flight']} job(s) still in flight")
    print()
    print("  by workflow:")
    for name, slot in sorted(rep["per_workflow"].items(), key=lambda kv: -kv[1]["minutes"]):
        print(f"    {name:10} {slot['minutes']:5} min over {slot['jobs']:3} jobs")
    print("  by workflow x event (the lever acts on one cell of this):")
    for name, slot in sorted(rep["per_workflow_event"].items(),
                             key=lambda kv: -kv[1]["minutes"]):
        print(f"    {name:26} {slot['minutes']:5} min over {slot['jobs']:3} jobs")
    print("  by conclusion:")
    for name, slot in sorted(rep["per_conclusion"].items(), key=lambda kv: -kv[1]["minutes"]):
        print(f"    {name:10} {slot['minutes']:5} min over {slot['jobs']:3} jobs")
    if billable_field is not None:
        zeros = sum(1 for v in billable_field.values() if v == 0)
        print()
        print(f"  audit trail: /timing's billable.UBUNTU.total_ms read 0 for "
              f"{zeros} of {len(billable_field)} runs.")
        print("  That field is NOT the source of the figure above, for exactly that reason.")
    print()
    print("  The allowance this draws on could not be read: "
          "`gh api /users/teonimesic/settings/billing/actions`")
    print("  is 404 and asks for the `user` token scope, which this token "
          "(gist, read:org, repo, workflow) lacks.")


def _print_audit(aud: dict) -> None:
    print("controls.yml runs: did the LATEST PUSH touch a path the slow suites read?")
    print("  HISTORICAL. controls.yml carried a trigger-level `paths:` filter until "
          "2026-08-24;")
    print("  since then it runs on every pull request and its scope step logs this "
          "verdict itself.")
    print(f"  controls runs on pull_request : {aud['controls_pr_runs']}")
    print("  first-on-branch (no predecessor push; matches by construction): "
          f"{aud['first_on_branch']}")
    print(f"  analysed                      : {aud['analysed']}")
    print(f"    latest push touched a filter path   : {aud['match']}")
    print(f"    latest push touched NOTHING filtered: {aud['no_match']}")
    print(f"    same sha as the previous run        : {aud['same_sha']}")
    print()
    for row in aud["rows"]:
        print(f"  {row['verdict']:9} {row['run']}  {row['branch']}")
        if row["verdict"] == "no-match":
            for f in row["files"]:
                print(f"              {f}")


def gates_report(cen: dict[str, dict], as_json: bool = False) -> int:
    """Print the gate census and decide the exit status. ONE decision, both output modes.

    The refusal used to live only in the text branch, so `--gates --json` returned 0 over a
    workflow the census could not read -- the same confident zero the census itself was
    repaired for, one branch away. Both modes now go through here, and `--selftest` drives
    it with a malformed census in each. Raised by CodeRabbit on PR #16.
    """
    bad = [m for got in cen.values() for m in got["malformed"]]
    if as_json:
        print(json.dumps(cen, indent=2))
    else:
        for wf, got in cen.items():
            print(f"{wf}.yml: {got['gates']} gates, {got['setup']} setup steps, "
                  f"{got['scope']} scope steps")
    for m in bad:
        print(f"  MALFORMED: {m}", file=sys.stderr)
    if bad:
        # Exit 2, the same refusal an unreadable endpoint gets. A count published over a
        # workflow this could not read is a number, in range, and wrong.
        print("ci_minutes: refusing to publish a gate count over a workflow it could "
              "not read.", file=sys.stderr)
        return 2
    if not as_json:
        print("\n  producer: python3 eval/tools/ci_minutes.py --gates")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    ap.add_argument("--selftest", action="store_true",
                    help="controls, both directions, offline")
    ap.add_argument("--path-filter", action="store_true", help="the path-filter audit")
    ap.add_argument("--scope", action="store_true",
                    help="controls.yml's own filter: decide whether the slow suites have "
                         "anything to read, and write `relevant=` to $GITHUB_OUTPUT")
    ap.add_argument("--gates", action="store_true",
                    help="how many checks each workflow runs (offline; no API)")
    ap.add_argument("--no-timing", action="store_true",
                    help="skip the per-run /timing read (one extra API call per run)")
    ap.add_argument("--cache", metavar="DIR",
                    help="write the raw JSON consumed, so the number is re-derivable offline")
    ap.add_argument("--json", action="store_true", help="machine-readable")
    args = ap.parse_args(argv)

    if args.selftest:
        return _selftest()

    if args.scope:
        return emit_scope()

    if args.gates:
        return gates_report(gate_census(), as_json=args.json)

    try:
        runs = fetch_runs()
        if args.path_filter:
            aud = path_filter_audit(runs, compare_via_api)
            if args.json:
                print(json.dumps(aud, indent=2))
            else:
                _print_audit(aud)
            payload = {"runs": runs, "audit": aud}
        else:
            ids = [r["id"] for r in runs]
            jobs = fetch_jobs(ids)
            timing = None if args.no_timing else fetch_billable_field(ids)
            rep = census(jobs, runs)
            if args.json:
                print(json.dumps(rep, indent=2))
            else:
                _print_census(rep, timing)
            payload = {"runs": runs, "jobs": jobs, "census": rep, "timing": timing}
    except DataError as exc:
        print(f"ci_minutes: {exc}", file=sys.stderr)
        print("ci_minutes: refusing to report a number. This is not 0 minutes.",
              file=sys.stderr)
        return 2

    if args.cache:
        # ONE WRITER PER PATH, AND AN ATOMIC PUBLISH. The name used to be a fixed
        # `minutes.json`, so two invocations sharing a --cache directory wrote the same
        # path and either could replace the other's evidence, while an interrupted write
        # left a half-file that parses as nothing. The snapshot is the record of what the
        # instrument consumed; it is worth less than nothing if it can be a blend of two
        # runs. The name now carries the reading's own instant, so each invocation owns
        # its artifact, and `os.replace` makes the publish all-or-nothing.
        d = pathlib.Path(args.cache)
        d.mkdir(parents=True, exist_ok=True)
        kind = "path_filter" if args.path_filter else "minutes"
        stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        target = d / f"{kind}-{stamp}-{os.getpid()}.json"
        tmp = target.with_suffix(".json.partial")
        tmp.write_text(json.dumps(payload, indent=2))
        os.replace(tmp, target)
        print(f"\n  raw JSON written to {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
