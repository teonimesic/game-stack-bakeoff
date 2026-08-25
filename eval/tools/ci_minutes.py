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
while something is building (`AGENTS.md` rule 4). A run the jobs endpoint has nothing for is
the same shape and gets the same treatment -- see `fetch_jobs`, where refusing it instead
made the whole producer exit 2 over 1 run in 464.

WHAT IT REFUSES. Any `gh api` failure exits 2 naming the endpoint. There is no `|| 0`
anywhere: an error must never become a plausible in-range number (rule 3).

WHETHER THE MINUTES ARE BILLED IS READ, NOT REMEMBERED. Whether a minute costs anything is
a property of the repository, and this tool printed `PRIVATE -- these minutes are metered`
as a literal for a day after the repository was made public. A hardcoded `PUBLIC` is the
same defect one value later, so `fetch_visibility` reads `repos/{REPO}` `.private` and
refuses anything that is not `true` or `false` -- the wrong guess says minutes are free
while they are being billed. It is one extra API call, on the census path only.

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

EVERY MODE REFUSES THE FLAGS IT DOES NOT READ. Each mode above is a different report and each
reads a different subset of `--json`, `--cache` and `--no-timing`; `MODE_ACCEPTS` is that
subset, and `main` checks the invocation against it before dispatching. `--scope --json` used
to exit 0 having ignored `--json`, and `--scope --gates` to exit 0 having ignored `--gates`,
which is the shape AGENTS.md rule 13 names -- an accepted-but-ignored flag is indistinguishable
from a working one, where an unsupported flag fails loudly. The workflow's scope step is held
to the same contract: the gate asks whether its `run:` line is an invocation this tool honours,
not whether the line contains the word `--scope`.

--selftest pins both directions offline, in ~0.1s and without touching a file, and its
closing line is the producer for how many mutants and variants it carries. What it
must catch: truncation instead of rounding up; a compare list at the endpoint's 300-file cap,
which must be refused rather than scored; the ways a workflow can leave `ubuntu-latest` while
the file still contains the string; a filter entry no pin depends on; every mode reached with
a flag it does not read; and the ways the scope
guard can break -- a `paths:` or `paths-ignore:` filter back on either trigger, the scope step
deleted, its id renamed, its command replaced, its command given a flag `--scope` does not read
or a second mode or `--help` or a pipeline, its command echoed or wrapped in `sh -c` instead of
run, its command pointed at another script whose name ends the same way or at another mode of
this one, its command left with an unbalanced quote, a second command hidden behind a comment
on a multi-line step, one gate losing its guard, the guard
flipped to the
fail-open `== 'true'`, the guard conjoined with a constant false, a guarded step placed above
the step whose output it reads, a second `ubuntu-latest` job carrying an unguarded gate, a
scalar `steps:`, and a file that does not parse at all. What must still
PASS: an in-flight job, a job of exactly 60s, a 22s job, a filename that merely starts with a
filtered directory's letters, a re-spaced and double-quoted guard, two gates swapped, an
unguarded `uses:` step, a comment in the job, the scope step re-spaced, run under another
interpreter path, run under `python`, executed directly with no interpreter named, given a
quoted script path, or carrying a trailing shell comment, every
mode reached with a flag it does read, and `-h`. The variants
are not decoration -- the substring check this replaced went red on a re-quote, which is a
gate firing where nothing is wrong.

Usage:
    python3 eval/tools/ci_minutes.py                 # the census, from the API
    python3 eval/tools/ci_minutes.py --path-filter   # the path-filter audit
    python3 eval/tools/ci_minutes.py --scope         # controls.yml's filter, in-job
    python3 eval/tools/ci_minutes.py --cache DIR     # also write the raw JSON it consumed
    python3 eval/tools/ci_minutes.py --selftest      # controls, both directions, offline

Exit 0 on success, 1 if --selftest fails, 2 if the data could not be read or the flags given
name a report this tool would not have produced. Read it unpiped.
"""

from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import inspect
import io
import json
import math
import os
import pathlib
import re
import shlex
import subprocess
import sys
import tempfile

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


def census(jobs: list[dict], runs: list[dict],
           runs_without_jobs: list[int] | None = None) -> dict:
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
        # The third value's third case: runs the jobs endpoint had nothing for. Excluded
        # from the total and carried by id, never folded in as zero.
        "runs_without_jobs": list(runs_without_jobs or []),
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

# THE SCRIPT AS A PATH, and the closed set of ways a `run:` line may EXECUTE it. A step
# only decides the scope if the shell runs this file; `echo eval/tools/ci_minutes.py
# --scope` mentions it as an argument to `echo`, writes no `relevant`, and read as a
# substring is indistinguishable from the real thing. Raised by CodeRabbit on PR #35 --
# the same substring-versus-parse defect the guard and the `runs-on` census were repaired
# for, one field away.
#
# What the shell accepts, and therefore what this does: an interpreter followed by the
# script, or the script alone -- which the shell executes because the path contains a
# slash. Anything else in front of it (`echo`, `sh -c`, `xargs`, an env prefix) is a
# different program, and a different program is not this gate's subject.
SCOPE_SCRIPT = "eval/tools/ci_minutes.py"
SCOPE_INTERPRETERS = ("python3", "python")

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


# ----------------------------------------------------------------- the CLI contract

# WHICH MODE READS WHICH FLAG, spelled once so nothing has to remember it. `main` used to
# dispatch on the first mode flag it found and then read `args.json` in only some of the
# branches, so `--scope --json` exited 0 having ignored `--json`, and `--scope --gates`
# exited 0 having ignored `--gates`. That is the shape AGENTS.md rule 13 names: an
# accepted-but-ignored flag is worse than an unsupported one, because exit 0 is
# indistinguishable from "it did what I asked". An unsupported one fails loudly.
#
# The property, not the instance: the defect is not `--scope --json`, it is that every mode
# accepts the whole flag surface and honours a subset of it. This table IS that subset, and
# `main` refuses anything outside it before dispatching, so a combination added later is
# refused by construction rather than by somebody noticing.
#
# The empty key is the census -- the mode you get by naming none.
MODES = ("selftest", "scope", "gates", "hooks", "path_filter")
MODIFIERS = ("json", "cache", "no_timing")
MODE_ACCEPTS: dict[str, frozenset[str]] = {
    # --scope's machine-readable channel is `relevant=` in $GITHUB_OUTPUT, which is what
    # the workflow reads; its stdout is the audit trail a person reads in the job log.
    "scope": frozenset(),
    "selftest": frozenset(),
    "gates": frozenset({"json"}),
    "hooks": frozenset({"json"}),
    "path_filter": frozenset({"json", "cache"}),
    "": frozenset({"json", "cache", "no_timing"}),
}


def _flag(dest: str) -> str:
    """The CLI spelling of an argparse dest, derived rather than listed twice."""
    return "--" + dest.replace("_", "-") if dest else "(the census, no mode flag)"


class _ArgError(Exception):
    """argparse's usage error, raised instead of exiting.

    `ArgumentParser.error` calls `sys.exit(2)`, which is right for a command line and wrong
    for `filter_problems`, which has to ask whether a workflow's `run:` line is an
    invocation this tool honours and get an answer back rather than have the process die
    under it.
    """


class _ArgExit(Exception):
    """argparse's CLEAN exit -- `--help` -- raised instead of taken.

    ARGPARSE HAS TWO EXIT PATHS AND ONLY ONE OF THEM IS `error`. `--help` runs
    `print_help()` then `exit(0)` without ever going through `error`, so a parser that
    overrides `error` alone still dies under its caller. Raised by CodeRabbit on PR #35,
    and measured: `filter_problems` on a `--scope --help` scope step printed the whole
    help screen and raised `SystemExit(0)` where a list of problems was expected.
    """

    def __init__(self, status: int):
        super().__init__(f"argparse exited with status {status}")
        self.status = status


class _Parser(argparse.ArgumentParser):
    """The parser with both of argparse's exits re-routed, and its printing optional.

    `quiet` is what the workflow check passes. argparse writes usage and help straight to
    a stream, and a gate reporting on a `run:` line must not spray a help screen into the
    log it is being read from.
    """

    def __init__(self, *args, quiet: bool = False, **kwargs):
        self.quiet = quiet
        super().__init__(*args, **kwargs)

    def _print_message(self, message, file=None):
        if not self.quiet:
            super()._print_message(message, file)

    def error(self, message):
        raise _ArgError(message)

    def exit(self, status=0, message=None):
        if message:
            self._print_message(message, sys.stderr)
        raise _ArgExit(status)


def _build_parser(quiet: bool = False) -> _Parser:
    """The one parser. Both `main` and the workflow check parse with this object.

    ONE ADDRESS FOR THE FLAG SURFACE (AGENTS.md rule 12). The alternative -- a second list
    of flags inside the workflow check -- is two spellings of the same fact that agree only
    until one is edited, and the one that would be edited is this one. `quiet` changes
    where the messages go, never which flags exist.
    """
    ap = _Parser(description=(__doc__ or "").splitlines()[0], quiet=quiet)
    ap.add_argument("--selftest", action="store_true",
                    help="controls, both directions, offline")
    ap.add_argument("--path-filter", action="store_true", help="the path-filter audit")
    ap.add_argument("--scope", action="store_true",
                    help="controls.yml's own filter: decide whether the slow suites have "
                         "anything to read, and write `relevant=` to $GITHUB_OUTPUT")
    ap.add_argument("--gates", action="store_true",
                    help="how many checks each workflow runs (offline; no API)")
    ap.add_argument("--hooks", action="store_true",
                    help="what each git hook tier runs, and whether the register says so "
                         "(offline; no API)")
    ap.add_argument("--no-timing", action="store_true",
                    help="skip the per-run /timing read (one extra API call per run)")
    ap.add_argument("--cache", metavar="DIR",
                    help="write the raw JSON consumed, so the number is re-derivable offline")
    ap.add_argument("--json", action="store_true", help="machine-readable")
    return ap


def invocation_problems(args: object) -> list[str]:
    """Which of this invocation's flags would be silently ignored, if any.

    Pure, and it takes the PARSED arguments rather than a string, so the same answer serves
    the command line and the workflow check. Empty means every flag given is one the
    selected mode reads.
    """
    d = args if isinstance(args, dict) else vars(args)
    on = [m for m in MODES if d.get(m)]
    if len(on) > 1:
        return [f"{', '.join(_flag(m) for m in on)} each name a different report, and only "
                f"`{_flag(on[0])}` would run. Exiting 0 having produced one of them is "
                f"indistinguishable from having produced the one you asked for"]
    mode = on[0] if on else ""
    accepted = MODE_ACCEPTS[mode]
    reads = ", ".join(f"`{_flag(m)}`" for m in MODIFIERS if m in accepted) or "no modifiers"
    return [f"`{_flag(mode)}` does not read `{_flag(m)}`, so accepting it would exit 0 "
            f"having ignored what you asked for. It reads: {reads}"
            for m in MODIFIERS if d.get(m) and m not in accepted]


def scope_invocation_problems(run: object) -> list[str]:
    """Is one workflow `run:` line an invocation of `--scope` that this tool HONOURS?

    Containment of `ci_minutes.py --scope` was the whole test until 2026-08-25, and it is
    satisfied by two commands that do something else. `--scope --json` contains it and
    exited 0 having discarded `--json`, so the selftest carried that command as a VARIANT
    -- an input the gate must not redden -- and a workflow edited to it passed every pin.
    `echo eval/tools/ci_minutes.py --scope` contains it and runs `echo`. This asks the
    question the substring was standing in for: does the shell run THIS script, with
    arguments that produce a scope decision?

    THREE OUTCOMES, and the third is why `--help` needs naming. Arguments argparse rejects
    -- a shell operator, a second command, a flag that does not exist -- are reported and
    not skipped, because a step whose command this tool cannot read is one whose behaviour
    it cannot pin. `--help` is neither an error nor a decision: it parses, exits 0, prints a
    help screen and writes no `relevant`.
    """
    raw = str(run or "")
    text = " ".join(raw.split())
    # SPLIT THE WAY THE SHELL DOES, not on whitespace. `str.split` keeps the quote
    # characters, so `python3 "eval/tools/ci_minutes.py" --scope` -- a command that runs
    # exactly what the live step runs -- did not match the script and was reddened, and a
    # trailing `# note` became 2 unrecognised arguments. A gate firing where nothing is
    # wrong spends the attention a real firing needs. Raised by CodeRabbit on PR #35.
    #
    # ON `raw`, NOT ON `text`, AND THAT IS THE FAIL-OPEN HALF. A shell comment runs to the
    # end of its LINE, so flattening a multi-line `run:` first lets a `#` on the first line
    # swallow every line after it -- and the line after it is where a second command
    # overwrites `relevant`. Splitting the flattened form accepted that step at 0 problems.
    # `text` is for the message; the verdict is read off the text the shell would see.
    try:
        argv = shlex.split(raw, comments=True)
    except ValueError as exc:
        return [f"runs `{text}`, which does not tokenise as a shell command ({exc}), so "
                f"what it would run cannot be established"]
    at = next((i for i, t in enumerate(argv)
               if t == SCOPE_SCRIPT or t.endswith("/" + SCOPE_SCRIPT)), None)
    if at is None:
        return [f"does not run `{SCOPE_SCRIPT}`, so whatever writes `relevant` is no "
                f"longer this tool and is not gated by it"]
    # WHAT IS IN FRONT OF THE SCRIPT DECIDES WHETHER IT RUNS AT ALL. Nothing means the
    # shell executes the path itself; one interpreter means the interpreter runs it;
    # anything else is a different program holding this path as an argument.
    head = argv[:at]
    if head and (len(head) > 1 or os.path.basename(head[0]) not in SCOPE_INTERPRETERS):
        return [f"runs `{text}`, in which `{argv[at]}` is an ARGUMENT to "
                f"`{' '.join(head)}` rather than the program being run. Accepted forms are "
                f"the script alone or one of {list(SCOPE_INTERPRETERS)} in front of it"]
    rest = argv[at + 1:]
    try:
        parsed = _build_parser(quiet=True).parse_args(rest)
    except _ArgError as exc:
        return [f"runs `{text}`, whose arguments this tool does not accept: {exc}"]
    except _ArgExit as exc:
        return [f"runs `{text}`, which prints a help screen and exits {exc.status} without "
                f"deciding anything or writing `relevant`"]
    if not parsed.scope:
        return [f"runs `{text}`, which does not pass `--scope`, so it produces some other "
                f"report and writes no `relevant` at all"]
    return [f"runs `{text}`, and {p}" for p in invocation_problems(parsed)]


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
    problems += [f"controls.yml's `{SCOPE_STEP_ID}` step {p}"
                 for p in scope_invocation_problems(steps[at].get("run"))]

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
            # The COMMAND, not the step name. `hook_census` asks whether a command the git
            # hook runs is one of these, and a step name is prose that says nothing about
            # what was invoked. Every line of a multi-line `run:` block, because a step is
            # allowed to hold more than one and the hook's command could be any of them.
            "commands": sorted({norm for s in gates
                                for norm in (_norm_command(ln)
                                             for ln in str(s["run"]).splitlines())
                                if norm}),
        }
    return out


def _norm_command(text: object) -> str:
    """One command line, whitespace-collapsed, for comparing two spellings of the same call.

    A workflow writes `run: python3 eval/tools/docstat.py --sweep` and the hook prints
    `python3 eval/tools/docstat.py --sweep`; only the run of spaces between them is free to
    differ, so that is the only thing normalised. Nothing is lowercased and no flag is
    dropped -- `--findings` and `--withdrawn` are different gates and must not collapse.
    """
    return " ".join(str(text).split())


# ---------------------------------------------------------------- the git hooks

HOOK_RUNNER = ROOT / ".githooks" / "run-gates.sh"
REGISTER = WORKFLOW_DIR / "README.md"
HOOK_TIERS = ("pre-commit", "pre-push")

# The header the hook table must carry, and the only one this reads. A table found by
# position would move the moment a section is added above it (rule 12: the address is an
# input to the check), so it is found by its own header cells.
HOOK_TABLE_HEADER = ["command", "`pre-commit`", "`pre-push`"]

# A cell means "this tier runs it" only if it says exactly this. Everything else has to be
# in the closed set below or the row is REPORTED rather than read as a no -- an unrecognised
# cell silently meaning "no" is how a gate quietly leaves the published list.
HOOK_YES = "yes"
HOOK_NO = {"", "-", "--", "–", "—", "no", "n/a"}

_MD_DELIM = re.compile(r"^:?-{3,}:?$")

# The register states the coverage as digits, and this is the shape it must state it in.
# A looser read would let the sentence be reworded into something the check no longer sees,
# which fails OPEN: the numbers would go stale with the gate still green. Reword it and this
# goes red naming the required form, which is the direction a documentation gate must fail.
COVERAGE_RE = re.compile(
    r"`pre-push`\s+runs\s+\*\*(\d+)\*\*\s+of\s+`gates\.yml`'s\s+\*\*(\d+)\*\*\s+checks;"
    r"\s+`pre-commit`\s+runs\s+\*\*(\d+)\*\*")


def _md_cells(line: str) -> list[str] | None:
    """The cells of a markdown table row, or None if this line is not one."""
    s = line.strip()
    if not (s.startswith("|") and s.endswith("|") and len(s) > 1):
        return None
    return [c.strip() for c in s[1:-1].split("|")]


def _list_hook(tier: str) -> tuple[int, str, str]:
    """Ask `.githooks/run-gates.sh` what it runs, by RUNNING it in list-only mode."""
    proc = subprocess.run(
        ["sh", str(HOOK_RUNNER), tier], cwd=str(ROOT),
        capture_output=True, text=True, check=False,
        env={**os.environ, "GATES_LIST_ONLY": "1"},
    )
    return proc.returncode, proc.stdout, proc.stderr


def register_hook_table(text: str) -> tuple[dict[str, list[str]], list[str]]:
    """What `.github/workflows/README.md` DECLARES each hook tier runs.

    This is the second, independent statement of the fact `_list_hook` reads from the
    script -- and it has to stay independent. A check that built its expectation by calling
    its subject is not a check (`AGENTS.md` rule 12's addendum, task 113), so nothing here
    imports anything from the hook: it reads the document a human wrote.
    """
    declared: dict[str, list[str]] = {t: [] for t in HOOK_TIERS}
    problems: list[str] = []
    lines = text.splitlines()
    heads = [i for i, ln in enumerate(lines) if _md_cells(ln) == HOOK_TABLE_HEADER]
    if not heads:
        problems.append(
            f"{REGISTER.relative_to(ROOT)} carries no hook table. It must hold one whose "
            f"header row is `| {' | '.join(HOOK_TABLE_HEADER)} |`, naming every command "
            f"each tier runs -- that table is what `run-gates.sh` is checked against")
        return declared, problems
    if len(heads) > 1:
        problems.append(
            f"{REGISTER.relative_to(ROOT)} carries {len(heads)} hook tables (lines "
            f"{', '.join(str(h + 1) for h in heads)}). Two would disagree eventually and "
            f"a reader could not tell which is the register")
        return declared, problems
    i = heads[0] + 1
    delim = _md_cells(lines[i]) if i < len(lines) else None
    if not delim or not all(_MD_DELIM.match(c) for c in delim):
        problems.append(f"{REGISTER.relative_to(ROOT)} line {i + 1}: the hook table's "
                        f"header has no `|---|---|---|` row under it, so it is not a table")
        return declared, problems
    i += 1
    seen: list[str] = []
    while i < len(lines):
        cells = _md_cells(lines[i])
        if cells is None:
            break
        if len(cells) != len(HOOK_TABLE_HEADER):
            problems.append(f"{REGISTER.relative_to(ROOT)} line {i + 1}: the hook table "
                            f"row has {len(cells)} cells, want {len(HOOK_TABLE_HEADER)}")
            i += 1
            continue
        cmd = cells[0]
        if not (cmd.startswith("`") and cmd.endswith("`") and len(cmd) > 2):
            problems.append(f"{REGISTER.relative_to(ROOT)} line {i + 1}: the command cell "
                            f"{cmd!r} is not a backticked command")
            i += 1
            continue
        cmd = _norm_command(cmd[1:-1])
        if cmd in seen:
            problems.append(f"{REGISTER.relative_to(ROOT)} line {i + 1}: `{cmd}` is listed "
                            f"twice; a duplicated row makes the coverage count wrong")
        seen.append(cmd)
        for tier, cell in zip(HOOK_TIERS, cells[1:]):
            low = cell.lower()
            if low == HOOK_YES:
                declared[tier].append(cmd)
            elif low not in HOOK_NO:
                problems.append(
                    f"{REGISTER.relative_to(ROOT)} line {i + 1}: the `{tier}` cell for "
                    f"`{cmd}` reads {cell!r}, which is neither `{HOOK_YES}` nor one of "
                    f"{sorted(HOOK_NO)}. Reading it as a no would drop a gate from the "
                    f"published list without anything going red")
        i += 1
    if not seen:
        problems.append(f"{REGISTER.relative_to(ROOT)}: the hook table has no rows")
    return declared, problems


def hook_census(list_hook=_list_hook, register_text: str | None = None,
                census: dict[str, dict] | None = None) -> dict:
    """Does `.github/workflows/README.md` state what the git hooks actually run?

    WHY THIS EXISTS. The register said `pre-push` runs "the full `gates.yml` set". It ran
    5 of 47, all of them documentation and queue checks, and the sentence had been true of
    nothing since it was written -- so someone pushing on a green hook believed they had
    run what CI runs and had run about a ninth of it (task 153). The failure is the shape
    `AGENTS.md` names twice over: a description by ADJECTIVE, which no check can read, and
    one fact spelled in two files with a comment promising they agree.

    Both halves are repaired here. The register names the commands in a table; this reads
    that table and reads the script, and they must be equal.

    THE SCRIPT IS RUN, NOT PARSED. `GATES_LIST_ONLY=1` makes `run()` print its argv instead
    of executing it, so the list comes out of the hook's own control flow -- including the
    `pre-push`-only branch and the worktree branch, which a regex over the file would have
    had to re-derive and could get wrong in a way that looked like the register being right.

    IT ALSO ASKS WHAT THE HOOKS DO NOT COVER, because that is the dangerous direction. Every
    hook command must be one of `gates.yml`'s gates: if it is not, the register's "N of M"
    is arithmetic over two different populations and cannot be repaired by re-reading it.
    """
    problems: list[str] = []
    tiers: dict[str, list[str]] = {}
    for tier in HOOK_TIERS:
        rc, out, err = list_hook(tier)
        if rc != 0:
            problems.append(f"`GATES_LIST_ONLY=1 {HOOK_RUNNER.relative_to(ROOT)} {tier}` "
                            f"exited {rc}: {(err or out).strip()[:300]}")
            tiers[tier] = []
            continue
        cmds = [_norm_command(ln) for ln in out.splitlines() if ln.strip()]
        stray = [c for c in cmds if not c.startswith("python3 eval/")]
        if stray:
            problems.append(
                f"{HOOK_RUNNER.relative_to(ROOT)} {tier} printed {stray!r} in list-only "
                f"mode. Every line there must be a `python3 eval/...` gate; anything else "
                f"means the mode is emitting diagnostics and the list cannot be trusted")
        if not cmds:
            problems.append(f"{HOOK_RUNNER.relative_to(ROOT)} {tier} printed no commands "
                            f"in list-only mode -- a hook that runs nothing reads here as "
                            f"a hook that agrees with an empty table")
        tiers[tier] = cmds

    text = REGISTER.read_text(encoding="utf-8") if register_text is None else register_text
    declared, dec_problems = register_hook_table(text)
    problems += dec_problems

    for tier in HOOK_TIERS:
        # MEMBERSHIP, not sequence. The register claims a fixed LIST per tier and says
        # nothing about the order of its rows, so comparing ordered would redden the gate on
        # a table reshuffle that changes nothing a reader acts on -- and a check that fires
        # where nothing is wrong spends exactly the attention a real firing needs. Sorting
        # keeps duplicates visible, which is the one ordering-free way the two can differ in
        # length; the register's own duplicate row is reported separately.
        if sorted(declared[tier]) != sorted(tiers[tier]) and not dec_problems:
            problems.append(
                f"the register and {HOOK_RUNNER.relative_to(ROOT)} disagree about `{tier}`."
                f"\n      register : {declared[tier]}"
                f"\n      the hook : {tiers[tier]}")

    cen = gate_census() if census is None else census
    # A CENSUS THAT COULD NOT READ `gates.yml` HAS NO TOTAL, and reporting one anyway
    # misattributes the cause: it comes back `gates: 0, commands: []`, which reads here as
    # "the hooks run 5 commands gates.yml does not" and "claims 5 of 47, measured 5 of 0".
    # The exit status would be right and every word of the diagnosis wrong. Raised by
    # CodeRabbit on PR #33.
    if cen["gates"].get("malformed"):
        problems.append(
            f"`gates.yml` could not be read, so there is no total to count the hooks "
            f"against: {cen['gates']['malformed']}. The coverage sentence is arithmetic "
            f"over two populations and one of them is missing")
        return {"tiers": tiers, "declared": declared, "gate_count": 0,
                "coverage_claim": None, "orphans": [], "problems": problems}
    gate_cmds = set(cen["gates"]["commands"])
    gate_count = cen["gates"]["gates"]
    orphans = sorted({c for t in HOOK_TIERS for c in tiers[t]} - gate_cmds)
    if orphans:
        problems.append(
            f"the hooks run {orphans!r}, which `gates.yml` does not. The register counts "
            f"the hook's commands against gates.yml's total, and that count is only "
            f"meaningful while every hook command is one of them")

    claim = COVERAGE_RE.search(text)
    coverage: tuple[int, int, int] | None = None
    if not claim:
        problems.append(
            f"{REGISTER.relative_to(ROOT)} states no hook coverage. It must carry, "
            f"verbatim: ``pre-push` runs **N** of `gates.yml`'s **M** checks; `pre-commit` "
            f"runs **K**.` -- the numbers are what a reader acts on, and a sentence no "
            f"check can find is a sentence that goes stale silently")
    else:
        coverage = (int(claim.group(1)), int(claim.group(2)), int(claim.group(3)))
        want = (len(tiers["pre-push"]), gate_count, len(tiers["pre-commit"]))
        if coverage != want:
            problems.append(
                f"{REGISTER.relative_to(ROOT)} claims pre-push {coverage[0]} of "
                f"{coverage[1]} and pre-commit {coverage[2]}; measured "
                f"{want[0]} of {want[1]} and {want[2]}")

    return {"tiers": tiers, "declared": declared, "gate_count": gate_count,
            "coverage_claim": coverage, "orphans": orphans, "problems": problems}


def hooks_report(cen: dict, as_json: bool = False) -> int:
    """Print the hook census and decide the exit status. ONE decision, both output modes."""
    if as_json:
        print(json.dumps(cen, indent=2))
    else:
        for tier in HOOK_TIERS:
            cmds = cen["tiers"][tier]
            print(f"{tier}: {len(cmds)} of gates.yml's {cen['gate_count']} checks")
            for c in cmds:
                print(f"    {c}")
        print("\n  producer: python3 eval/tools/ci_minutes.py --hooks")
        print("  the list is read by RUNNING the hook: "
              "GATES_LIST_ONLY=1 .githooks/run-gates.sh <tier>")
    for p in cen["problems"]:
        print(f"  DISAGREEMENT: {p}", file=sys.stderr)
    if cen["problems"]:
        print("ci_minutes: the CI register does not describe the git hooks it documents.",
              file=sys.stderr)
        return 1
    return 0


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


def fetch_visibility(reader=_gh) -> bool:
    """True if the repository is private. READ from the endpoint, never remembered.

    The reader is injected so `--selftest` can pin both answers and every refusal offline,
    rather than monkeypatching a module global. There is no default answer: a repository
    whose visibility could not be read is one whose minutes may or may not be billed, and
    guessing either way produces a confident sentence about money.
    """
    lines = reader(f"repos/{REPO}", ".private")
    values = [ln.strip() for ln in lines if ln.strip()]
    if values != ["true"] and values != ["false"]:
        raise DataError(
            f"repos/{REPO}: `.private` read {lines!r}, which is neither `true` nor "
            f"`false`. Refusing to say whether these minutes are billed.")
    return values == ["true"]


def visibility_line(private: bool) -> str:
    """The census's repository line. Pure, so both branches are pinned offline."""
    if private:
        return f"  repository : {REPO}  (PRIVATE -- these minutes are metered)"
    return f"  repository : {REPO}  (PUBLIC -- Linux minutes are free and unlimited)"


def allowance_lines(private: bool) -> list[str]:
    """What the figure draws on. Pure, and it says nothing about a bill when there is none."""
    if private:
        return [
            "  These minutes are metered. This tool does not read the allowance they draw",
            "  on: `gh api /users/<owner>/settings/billing/actions` needs the `user` token",
            "  scope, which the token here is not required to carry.",
        ]
    return [
        "  No allowance is drawn on: Linux minutes on a public repository are free and",
        "  unlimited. The figure above is wall clock in front of a merge, not a bill.",
    ]


def fetch_runs() -> list[dict]:
    lines = _gh(
        f"repos/{REPO}/actions/runs?per_page=100",
        ".workflow_runs[] | {id, name, event, head_branch, status, conclusion, "
        "created_at, run_started_at, head_sha}",
    )
    if not lines:
        raise DataError("the runs endpoint returned no runs -- a refusal, not 0 minutes")
    return [json.loads(ln) for ln in lines]


def fetch_jobs(run_ids: list[int], reader=_gh) -> tuple[list[dict], list[int]]:
    """Every run's jobs, and the ids of the runs that reported none.

    A SINGLE RUN WITH NO JOBS USED TO KILL THE WHOLE CENSUS. Run 32774427303 was cancelled
    at 2026-08-24T20:32:05Z before any job was created, so its `jobs` array is empty and
    always will be; the tool raised on it and exited 2, which made the producer that
    `DECISIONS.md` and `.github/workflows/README.md` both name for CI consumption unable to
    report anything at all, permanently, over one run in 464.

    Refusing was the right instinct and the wrong shape. A run with no jobs is the same
    THIRD VALUE as a job in flight: it is not zero minutes and it is not an error, so it
    goes in its own bucket, is excluded from the total, and is PRINTED with its run id --
    the total is qualified rather than quietly low. Measured over the 464 runs this
    repository had on 2026-08-25: 1 run reports no jobs, and 105 of the other 106 cancelled
    runs report jobs normally, so "cancelled" is not the property and is not tested here.

    The refusal that remains is the one an empty bucket cannot express: if NO run yields a
    job, the endpoint is not answering and the census is a confident zero, so it raises.
    """
    out: list[dict] = []
    empty: list[int] = []
    for rid in run_ids:
        lines = reader(
            f"repos/{REPO}/actions/runs/{rid}/jobs?per_page=100",
            f".jobs[] | {{run_id: {rid}, job_id: .id, name, status, conclusion, "
            "started_at, completed_at}",
        )
        if not lines:
            empty.append(rid)
            continue
        out.extend(json.loads(ln) for ln in lines)
    if run_ids and not out:
        raise DataError(
            f"all {len(run_ids)} runs reported no jobs -- a refusal, not 0 minutes")
    return out, empty


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
    check("gates.yml gate count", _cen["gates"]["gates"], 47)
    check("controls.yml gate count", _cen["controls"]["gates"], 8)
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
    # -- the git hooks, and whether the register describes them --------------------------
    # THE LIVE PAIR FIRST, because this is the row that has to be true of the repository
    # rather than of a fixture: the register's table and coverage sentence against what
    # `.githooks/run-gates.sh` prints when it is run.
    _live_hooks = hook_census()
    check("the register describes the git hooks it documents", _live_hooks["problems"], [])
    check("pre-commit's list is not empty", bool(_live_hooks["tiers"]["pre-commit"]), True)
    check("pre-push's list is not empty", bool(_live_hooks["tiers"]["pre-push"]), True)
    # And the published coverage is what the two producers say, not what it says of itself.
    check("the coverage sentence counts the hook and the workflow",
          _live_hooks["coverage_claim"],
          (len(_live_hooks["tiers"]["pre-push"]), _cen["gates"]["gates"],
           len(_live_hooks["tiers"]["pre-commit"])))
    # LIST-ONLY MUST NOT EXECUTE, and the control runs in BOTH directions. A mode that
    # listed AND ran would be green on every row above while costing a full sweep, and a
    # shim that never fires would make the "did not execute" half vacuous -- so the same
    # shim is asked to fire with the flag off. `python3` is shadowed on PATH rather than
    # trusted to be slow: absence of output is not absence of execution.
    with tempfile.TemporaryDirectory() as _td:
        _shim_dir, _marker = pathlib.Path(_td) / "bin", pathlib.Path(_td) / "fired"
        _shim_dir.mkdir()
        _shim = _shim_dir / "python3"
        _shim.write_text(f'#!/bin/sh\nprintf x >> "{_marker}"\nexit 0\n')
        _shim.chmod(0o755)
        _env = {**os.environ, "PATH": f"{_shim_dir}:{os.environ.get('PATH', '')}"}

        def _run_hook_shimmed(listing: bool):
            env = {**_env, "GATES_LIST_ONLY": "1"} if listing else _env
            return subprocess.run(["sh", str(HOOK_RUNNER), "pre-push"], cwd=str(ROOT),
                                  capture_output=True, text=True, check=False, env=env)

        _listed = _run_hook_shimmed(True)
        check("list-only exits 0", _listed.returncode, 0)
        check("list-only executed no gate", _marker.exists(), False)
        check("list-only printed every pre-push gate",
              [_norm_command(ln) for ln in _listed.stdout.splitlines() if ln.strip()],
              _live_hooks["tiers"]["pre-push"])
        counts["mutants"] += 1
        # The variant half: with the flag off, the very same shim IS invoked. Without this
        # row, a shim that could never run would report "executed nothing" for free.
        _ran = _run_hook_shimmed(False)
        check("without the flag the hook really executes its gates",
              (_ran.returncode, _marker.exists(), len(_marker.read_text())
               if _marker.exists() else 0),
              (0, True, len(_live_hooks["tiers"]["pre-push"])))
        counts["variants"] += 1

    # The fixture pair the mutants below are edits of. It is deliberately NOT the live one:
    # a mutant of the live register would have to be a string replacement that keeps working
    # as the document is rewritten, and the property under test is the reader, not the text.
    _hook_cmds = ["python3 eval/tools/docstat.py --selftest",
                  "python3 eval/tools/tasks.py check",
                  "python3 eval/tools/docstat.py --sweep"]
    _hook_tiers = {"pre-commit": _hook_cmds[:2], "pre-push": _hook_cmds}
    _hook_gates = {"gates": {"gates": 3, "commands": sorted(_hook_cmds), "malformed": []}}

    def _fake_register(rows, cover=(3, 3, 2), header=None, delim=True, tail=""):
        head = HOOK_TABLE_HEADER if header is None else header
        out = ["# fixture", "", "| " + " | ".join(head) + " |"]
        if delim:
            out.append("|" + "|".join(["---"] * len(head)) + "|")
        out += [f"| {c} | {a} | {b} |" for c, a, b in rows]
        out += ["", tail, ""]
        if cover:
            out.append(f"`pre-push` runs **{cover[0]}** of `gates.yml`'s **{cover[1]}** "
                       f"checks; `pre-commit` runs **{cover[2]}**.")
        return "\n".join(out) + "\n"

    def _lister(tiers, rc=0, text=None):
        def _f(tier):
            if text is not None:
                return rc, text, ""
            return rc, "".join(f"{c}\n" for c in tiers[tier]), ""
        return _f

    _ok_rows = [("`python3 eval/tools/docstat.py --selftest`", "yes", "yes"),
                ("`python3 eval/tools/tasks.py check`", "yes", "yes"),
                ("`python3 eval/tools/docstat.py --sweep`", "—", "yes")]
    _hook_mutants = {
        "a gate the hook runs is missing from the table":
            (_fake_register(_ok_rows[:2], cover=(3, 3, 2)), _lister(_hook_tiers)),
        "a row for a gate the hook does not run":
            (_fake_register(_ok_rows + [("`python3 eval/tools/linkcheck.py`", "yes", "yes")],
                            cover=(3, 3, 2)), _lister(_hook_tiers)),
        "the sweep marked as running pre-commit too":
            (_fake_register([_ok_rows[0], _ok_rows[1],
                             ("`python3 eval/tools/docstat.py --sweep`", "yes", "yes")]),
             _lister(_hook_tiers)),
        "no table at all":
            ("# fixture\n\n`pre-push` runs **3** of `gates.yml`'s **3** checks; "
             "`pre-commit` runs **2**.\n", _lister(_hook_tiers)),
        "two hook tables, which a reader cannot choose between":
            (_fake_register(_ok_rows) + "\n" + _fake_register(_ok_rows[:1], cover=None),
             _lister(_hook_tiers)),
        "the header with no delimiter row under it":
            (_fake_register(_ok_rows, delim=False), _lister(_hook_tiers)),
        "a cell that is neither yes nor a no-marker":
            (_fake_register([_ok_rows[0], _ok_rows[1],
                             ("`python3 eval/tools/docstat.py --sweep`", "sometimes",
                              "yes")]), _lister(_hook_tiers)),
        "the same command on two rows":
            (_fake_register(_ok_rows + [_ok_rows[0]], cover=(3, 3, 2)),
             _lister(_hook_tiers)),
        "a command cell that is not backticked":
            (_fake_register([("python3 eval/tools/docstat.py --selftest", "yes", "yes")]
                            + _ok_rows[1:]), _lister(_hook_tiers)),
        "no coverage sentence":
            (_fake_register(_ok_rows, cover=None), _lister(_hook_tiers)),
        "the coverage sentence off by one":
            (_fake_register(_ok_rows, cover=(4, 3, 2)), _lister(_hook_tiers)),
        "the coverage sentence naming the wrong workflow total":
            (_fake_register(_ok_rows, cover=(3, 47, 2)), _lister(_hook_tiers)),
        # THE HOOK'S HALF. The table can be right and the script wrong, and that direction
        # is the one that matters: the register is what a person reads before pushing.
        "the runner refusing in list-only mode":
            (_fake_register(_ok_rows), _lister(_hook_tiers, rc=2)),
        "the runner printing nothing":
            (_fake_register(_ok_rows), _lister(_hook_tiers, text="")),
        "the runner printing a diagnostic instead of a gate":
            (_fake_register(_ok_rows), _lister(_hook_tiers, text="warning: no git\n")),
        "the hook running something gates.yml does not":
            (_fake_register(_ok_rows + [("`python3 eval/tools/nope.py`", "yes", "yes")],
                            cover=(4, 3, 3)),
             _lister({t: c + ["python3 eval/tools/nope.py"]
                      for t, c in _hook_tiers.items()})),
        "the hook silently dropping a gate the table still lists":
            (_fake_register(_ok_rows), _lister({"pre-commit": _hook_cmds[:1],
                                                "pre-push": _hook_cmds[:2]})),
    }
    _hook_variants = {
        "the live pair": (None, None),
        "cells padded and the pipes re-spaced":
            (_fake_register(_ok_rows).replace("| yes |", "|   yes   |"),
             _lister(_hook_tiers)),
        "a plain hyphen rather than an em dash for no":
            (_fake_register([_ok_rows[0], _ok_rows[1],
                             ("`python3 eval/tools/docstat.py --sweep`", "-", "yes")]),
             _lister(_hook_tiers)),
        "an empty cell for no":
            (_fake_register([_ok_rows[0], _ok_rows[1],
                             ("`python3 eval/tools/docstat.py --sweep`", "", "yes")]),
             _lister(_hook_tiers)),
        "YES in capitals":
            (_fake_register([("`python3 eval/tools/docstat.py --selftest`", "YES", "Yes")]
                            + _ok_rows[1:]), _lister(_hook_tiers)),
        "prose between the table and the coverage sentence":
            (_fake_register(_ok_rows, tail="Some explanation of why these five.\n"),
             _lister(_hook_tiers)),
        "the coverage sentence wrapped across two lines":
            (_fake_register(_ok_rows, cover=None)
             + "`pre-push` runs **3** of `gates.yml`'s\n**3** checks; `pre-commit` runs "
               "**2**.\n", _lister(_hook_tiers)),
        # The table's rows are a SET. The register claims a fixed list per tier and no
        # order, so a reshuffle changes nothing a reader acts on and must not redden.
        "the table's rows reordered":
            (_fake_register([_ok_rows[1], _ok_rows[0], _ok_rows[2]]), _lister(_hook_tiers)),
    }
    for _name, (_text, _lh) in {**_hook_mutants, **_hook_variants}.items():
        _want_red = _name in _hook_mutants
        try:
            _got = (hook_census() if _text is None
                    else hook_census(_lh, register_text=_text, census=_hook_gates))
        except Exception as _exc:  # noqa: BLE001 - a raise is not a verdict
            failures.append(f"hook_census RAISED on {_name}: {_exc!r}")
            continue
        if bool(_got["problems"]) != _want_red:
            failures.append(
                f"hook_census {'SURVIVED' if _want_red else 'reddened on'} {_name}: "
                f"{_got['problems'] or 'no problems'}")
        # BOTH OUTPUT MODES, for the reason gates_report carries: the refusal lived in one
        # branch there and `--json` returned 0 over a census that had already refused.
        for _as_json in (False, True):
            with contextlib_redirect_all():
                _code = hooks_report(_got, as_json=_as_json)
            if (_code != 0) != _want_red:
                failures.append(f"hooks_report(as_json={_as_json}) returned {_code} on "
                                f"{_name}; want {'nonzero' if _want_red else '0'}")
    counts["mutants"] += len(_hook_mutants)
    counts["variants"] += len(_hook_variants)
    # AN UNREADABLE `gates.yml` MUST BE NAMED AS ITSELF. It is its own row rather than one
    # of the mutants above because the assertion is on the DIAGNOSIS, not on the exit
    # status: without the refusal the run is still red, and every word of why is wrong --
    # an orphan list and a coverage sentence "measured 5 of 0". Raised by CodeRabbit, PR #33.
    _bad_gates = {"gates": {"gates": 0, "commands": [],
                            "malformed": ["gates.yml: pyyaml is missing"]}}
    _got = hook_census(_lister(_hook_tiers), register_text=_fake_register(_ok_rows),
                       census=_bad_gates)
    check("an unreadable gates.yml is refused rather than counted",
          [p for p in _got["problems"] if "could not be read" in p] != [], True)
    check("and nothing is blamed on the hooks for it",
          [p for p in _got["problems"] if "which `gates.yml` does not" in p or
           "claims pre-push" in p], [])
    check("and no coverage claim is published over a missing total",
          (_got["coverage_claim"], _got["gate_count"]), (None, 0))
    counts["mutants"] += 1

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
          gate_census(None, _import_yaml)["controls"]["gates"], 8)

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
            # THIS ROW WAS A VARIANT UNTIL 2026-08-25 -- an input the gate asserted it must
            # NOT redden. `--scope --json` contains `--scope`, so the substring check passed
            # it and `main` ran it at exit 0 having ignored `--json`, which made the gate a
            # statement that a scope step invoked with a flag the tool does not honour is a
            # correct scope step. Both halves are repaired: `main` refuses the invocation,
            # and the gate reddens a workflow that carries it.
            "the scope step given a flag --scope does not honour":
                live.replace("ci_minutes.py --scope\n",
                             "ci_minutes.py --scope --json\n", 1),
            # The same defect one flag over, and it is not the same string: `--cache DIR`
            # takes a value, so a check written against `--json` alone would miss it.
            "the scope step given --cache, which --scope also does not read":
                live.replace("ci_minutes.py --scope\n",
                             "ci_minutes.py --scope --cache /tmp/ci\n", 1),
            # A second mode on the scope step. It would report the gate census and write
            # no `relevant` at all, which the `!= 'false'` guard then runs blind.
            "the scope step given a second mode flag":
                live.replace("ci_minutes.py --scope\n",
                             "ci_minutes.py --scope --gates\n", 1),
            # Not a flag at all: a shell operator turns the step's exit status into the
            # last stage's (AGENTS.md rule 3), and the arguments stop being parseable.
            "the scope step's exit status swallowed by a pipeline":
                live.replace("ci_minutes.py --scope\n",
                             "ci_minutes.py --scope | tail -1\n", 1),
            # ARGPARSE'S OTHER EXIT. `--help` never reaches `error()`, so the step would
            # print a help screen, exit 0, write no `relevant`, and -- until PR #35 --
            # raise `SystemExit(0)` straight out of `filter_problems`, which is a check
            # with no verdict rather than a check that says no.
            "the scope step given --help, which decides nothing":
                live.replace("ci_minutes.py --scope\n",
                             "ci_minutes.py --scope --help\n", 1),
            # THE SCRIPT AS AN ARGUMENT TO SOMETHING ELSE. Both of these CONTAIN
            # `ci_minutes.py --scope` and neither runs it, which is what a substring test
            # cannot see. Raised by CodeRabbit on PR #35.
            "the scope step echoing the command instead of running it":
                live.replace("run: python3 eval/tools/ci_minutes.py --scope\n",
                             "run: echo eval/tools/ci_minutes.py --scope\n", 1),
            "the scope step's command wrapped in sh -c":
                live.replace("run: python3 eval/tools/ci_minutes.py --scope\n",
                             "run: sh -c python3 eval/tools/ci_minutes.py --scope\n", 1),
            # A DIFFERENT SCRIPT whose name ends the same way. This is what separates the
            # path match from a suffix test: `endswith("ci_minutes.py")` accepts it, and
            # then every flag check below is being run against a file nobody here wrote.
            "the scope step running another script named ...ci_minutes.py":
                live.replace("run: python3 eval/tools/ci_minutes.py --scope\n",
                             "run: python3 tools/vendor_ci_minutes.py --scope\n", 1),
            # Parses cleanly, names a real mode, and is not the one that writes `relevant`.
            "the scope step running a different mode of this same tool":
                live.replace("run: python3 eval/tools/ci_minutes.py --scope\n",
                             "run: python3 eval/tools/ci_minutes.py --gates\n", 1),
            # An unbalanced quote is not a command at all. It must be REPORTED -- a step
            # whose text does not tokenise is one whose behaviour cannot be established,
            # and `shlex` raises rather than guessing.
            "the scope step's command with an unbalanced quote":
                live.replace("run: python3 eval/tools/ci_minutes.py --scope\n",
                             'run: python3 "eval/tools/ci_minutes.py --scope\n', 1),
            # THE FAIL-OPEN ONE. A shell comment ends at its LINE, so a checker that
            # flattens the block first lets `#` on line 1 hide line 2 -- and line 2 is
            # where `relevant` gets overwritten by something that is not this tool.
            "a second command hidden behind a comment on a multi-line scope step":
                live.replace(
                    "        run: python3 eval/tools/ci_minutes.py --scope\n",
                    "        run: |\n"
                    "          python3 eval/tools/ci_minutes.py --scope # the filter\n"
                    '          echo "relevant=false" >> "$GITHUB_OUTPUT"\n', 1),
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
            # The variant the mutants above must not swallow: the scope step is still free
            # to be re-spelled in ways that change nothing this tool honours. Refusing an
            # invocation because it is unfamiliar rather than because it is ignored would
            # be a gate firing where nothing is wrong.
            "the scope step run under a different interpreter path": live.replace(
                "run: python3 eval/tools/ci_minutes.py --scope\n",
                "run: /usr/bin/python3 eval/tools/ci_minutes.py --scope\n", 1),
            "the scope step's command re-spaced": live.replace(
                "run: python3 eval/tools/ci_minutes.py --scope\n",
                "run: python3   eval/tools/ci_minutes.py   --scope\n", 1),
            # The other two forms a shell really runs: the second interpreter name, and
            # the script executed directly because its path contains a slash. Rejecting a
            # command the shell would run is the gate firing where nothing is wrong.
            "the scope step run under `python` rather than `python3`": live.replace(
                "run: python3 eval/tools/ci_minutes.py --scope\n",
                "run: python eval/tools/ci_minutes.py --scope\n", 1),
            "the scope step executed directly, with no interpreter named": live.replace(
                "run: python3 eval/tools/ci_minutes.py --scope\n",
                "run: eval/tools/ci_minutes.py --scope\n", 1),
            # Shell syntax that changes no word the shell passes to the program. Splitting
            # on whitespace reddened both, which is a gate firing where nothing is wrong.
            "the scope step's script path quoted": live.replace(
                "run: python3 eval/tools/ci_minutes.py --scope\n",
                'run: python3 "eval/tools/ci_minutes.py" --scope\n', 1),
            "the scope step's command with a trailing shell comment": live.replace(
                "run: python3 eval/tools/ci_minutes.py --scope\n",
                "run: python3 eval/tools/ci_minutes.py --scope  # the filter\n", 1),
        }
        counts["mutants"] += len(mutants)
        counts["variants"] += len(variants)
        # A RAISE IS NOT A VERDICT, and reporting it as one is the difference between
        # "MUTANT SURVIVED: x" and a traceback whose reader has to work out which row it
        # came from. Several of the mutants below are deliberately malformed workflows,
        # which is exactly the input a check is most likely to raise on.
        def problems_of(text, name):
            try:
                return filter_problems(text, gates_yml.read_text())
            # `SystemExit` EXPLICITLY, because it is not an `Exception` and the parser two
            # calls down leaves by raising it. Measured: the mutant renaming `_Parser.exit`
            # made a `--scope --help` row exit the whole selftest at status 0 -- green,
            # silent, nothing asserted -- and SURVIVED, until this line named it.
            # `KeyboardInterrupt` is deliberately still free to leave.
            except (Exception, SystemExit) as exc:  # noqa: BLE001 - nothing may escape
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

    # -- the CLI contract: which mode reads which flag ---------------------------------
    # `MODE_ACCEPTS` is a claim about `main`, and a claim about code is worth what the row
    # that reads the code is worth. What is pinned here: the table's shape, the dispatch
    # ORDER it depends on, that no modifier is dead, and `main`'s refusal end to end for
    # every combination that can be exercised without touching the API. What is NOT pinned:
    # that the census and `--path-filter` really consume `--cache` and `--no-timing`, which
    # cannot be driven offline -- those two rows of the table are read, not measured.
    check("the table covers every mode and the census",
          sorted(MODE_ACCEPTS), sorted(set(MODES) | {""}))
    check("the table names no flag that is not a modifier",
          sorted({m for acc in MODE_ACCEPTS.values() for m in acc} - set(MODIFIERS)), [])
    # THE ORDER IS LOAD-BEARING, not cosmetic: `invocation_problems` reports which mode
    # WOULD have run when several are given, and it reads `MODES[0]`-first. That is the
    # same fact as `main`'s dispatch chain, spelled in two places, so it is asserted here
    # rather than promised in a comment (AGENTS.md rule 12).
    _main_src = inspect.getsource(main)
    _seen: list[str] = []
    for _m in re.findall(r"args\.([a-z_]+)", _main_src):
        # FIRST read of each, because a mode may be consulted again further down --
        # `args.path_filter` also chooses the --cache filename -- and only the first is
        # the dispatch.
        if _m in MODES and _m not in _seen:
            _seen.append(_m)
    check("MODES is main's dispatch order", _seen, list(MODES))
    check("no modifier is unread by every branch",
          [m for m in MODIFIERS if f"args.{m}" not in _main_src], [])

    def _problems_for(argv):
        """`invocation_problems` for one command line, or why it could not be asked.

        A parser edit that drops a flag would make the rows below raise rather than fail,
        and a check that raises has no verdict at all.
        """
        try:
            return invocation_problems(_build_parser().parse_args(argv))
        except _ArgError as exc:
            return [f"the parser rejected {argv}: {exc}"]

    # BOTH DIRECTIONS, one line each. The left column is the invocation; the right is
    # whether this tool honours every flag in it.
    for _argv, _honoured in (
            # A modifier the selected mode does not read. The first row is the one that
            # was measured; the rest are the same defect at every other mode, which is
            # what makes this a property rather than an enumeration of one incident.
            (["--scope", "--json"], False),
            (["--scope", "--cache", "/tmp/ci"], False),
            (["--selftest", "--json"], False),
            (["--path-filter", "--no-timing"], False),
            (["--gates", "--cache", "/tmp/ci"], False),
            (["--hooks", "--no-timing"], False),
            # Two modes: only the first would run, and exiting 0 for it is the same defect.
            (["--scope", "--gates"], False),
            (["--selftest", "--path-filter"], False),
            # The variants. Every one of these is a combination a mode really reads, and a
            # refusal here would be the gate firing where nothing is wrong.
            (["--scope"], True),
            (["--selftest"], True),
            (["--gates"], True),
            (["--gates", "--json"], True),
            (["--hooks", "--json"], True),
            (["--path-filter", "--json"], True),
            (["--path-filter", "--cache", "/tmp/ci"], True),
            ([], True),
            (["--json"], True),
            (["--cache", "/tmp/ci"], True),
            (["--no-timing", "--json"], True),
    ):
        check(f"`{' '.join(_argv) or '(no flags)'}` is "
              f"{'honoured' if _honoured else 'refused'}",
              not _problems_for(_argv), _honoured)
        counts["variants" if _honoured else "mutants"] += 1

    # AND THE EXIT STATUS, because `invocation_problems` returning a list is not the same
    # fact as `main` refusing.
    #
    # WHAT THIS ROW DOES IF IT FAILS is part of its design, and the first draft got it
    # wrong. `--selftest --json` was in the list, so a `main` that stopped refusing would
    # re-enter `_selftest`, which drives subprocesses at every level -- measured as a hang,
    # not a red line. A check whose failure mode is a hang reports nothing at all. Only
    # combinations whose mode is cheap and offline if the refusal fails are driven here,
    # and `--scope` is neutered by the environment below: with no `GITHUB_EVENT_NAME` it
    # reads no diff, and with no `GITHUB_OUTPUT` it appends `relevant=` to no file.
    def _main_rc(argv):
        """`(status, stdout, stderr)` for one `main` call, with `sys.exit` REPORTED.

        The same lesson as the hang, one exit away: argparse leaves by calling `sys.exit`,
        so a `_Parser` that stopped raising would make these rows end the whole selftest at
        status 0 -- green, silent, and having asserted nothing. Measured: the mutant that
        renames `_Parser.exit` SURVIVED until this wrapper existed. A check whose failure
        mode is the process leaving reports nothing at all.
        """
        out, err = io.StringIO(), io.StringIO()
        try:
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                status = main(argv)
        except SystemExit as exc:
            failures.append(f"main({argv}) called sys.exit({exc.code}) instead of "
                            f"returning. A status the process takes is one no row can read")
            status = "sys.exit"
        return status, out.getvalue(), err.getvalue()

    _saved_env = {k: os.environ.pop(k, None)
                  for k in ("GITHUB_OUTPUT", "GITHUB_EVENT_NAME")}
    try:
        for _argv in (["--scope", "--json"], ["--scope", "--cache", "/dev/null/nope"],
                      ["--scope", "--gates"]):
            _rc, _, _err = _main_rc(_argv)
            check(f"main({_argv}) exits non-zero", _rc, 2)
            check(f"main({_argv}) names the flag it refused",
                  [w for w in _argv if w.startswith("--") and w not in _err], [])
            counts["mutants"] += 1
    finally:
        for _k, _v in _saved_env.items():
            if _v is not None:
                os.environ[_k] = _v
    # `--help` STILL WORKS, and that is the variant for the exit re-routing above. Both of
    # argparse's exits now raise, so a `main` that forgot to catch the clean one would kill
    # the process on `-h` instead of printing it. Checked on stdout, not just on the status.
    for _help_flag in ("--help", "-h"):
        _hrc, _hout, _ = _main_rc([_help_flag])
        check(f"main(['{_help_flag}']) exits 0", _hrc, 0)
        check(f"main(['{_help_flag}']) prints the usage and the modes",
              [w for w in ("usage:", "--scope", "--gates", "--selftest") if w not in _hout],
              [])
        counts["variants"] += 1
    # And the same flag inside a workflow step is a MUTANT, adjudicated on the string so
    # nothing has to reach the real file. It must be a verdict, never a raise.
    try:
        _help_step = scope_invocation_problems("python3 eval/tools/ci_minutes.py "
                                               "--scope --help")
    except BaseException as exc:  # noqa: BLE001 - a raise here IS the defect under test
        _help_step = []
        failures.append(f"scope_invocation_problems RAISED on `--scope --help`: {exc!r}. "
                        f"A check that raises returns no verdict at all")
    check("a `--scope --help` step is reported rather than raised on",
          bool(_help_step), True)
    counts["mutants"] += 1
    # AND THE SAME FOR TEXT THAT IS NOT A COMMAND. The workflow mutant carrying an
    # unbalanced quote reddens either way -- a whitespace fallback would leave the quote
    # glued to the path and miss the script -- so the row that discriminates has to ask
    # WHICH answer came back, not merely that one did.
    try:
        _bad_quote = scope_invocation_problems('python3 "eval/tools/ci_minutes.py --scope')
    except BaseException as exc:  # noqa: BLE001 - a raise here IS the defect under test
        _bad_quote = []
        failures.append(f"scope_invocation_problems RAISED on an unbalanced quote: {exc!r}. "
                        f"A check that raises returns no verdict at all")
    check("an unbalanced quote is reported as untokenisable, not as a missing script",
          [p for p in _bad_quote if "tokenise" in p] != [], True)
    counts["mutants"] += 1

    # The variant half of the same question: `main` still dispatches a mode whose flags it
    # honours. `--hooks --json` is offline, and its payload is parsed rather than eyeballed.
    _rc, _out, _ = _main_rc(["--hooks", "--json"])
    check("main(['--hooks', '--json']) exits 0", _rc, 0)
    try:
        _payload = json.loads(_out)
    except json.JSONDecodeError as exc:
        _payload = {"__unparseable__": str(exc)}
    check("and --hooks really reads --json",
          (isinstance(_payload, dict), "tiers" in _payload,
           "producer: python3" in _out),
          (True, True, False))
    counts["variants"] += 1

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

    # -- a run the jobs endpoint has nothing for ----------------------------------------
    # Run 32774427303 was cancelled before a job existed, and the old per-run refusal made
    # the whole census exit 2 over it -- for good, since it stays in the run list. The
    # reader is injected, so this is offline.
    _JOBLESS = 32774427303  # the real one, so the printed line can be asserted verbatim

    def _jobs_reader(endpoint, _jq):
        rid = int(endpoint.split("/runs/")[1].split("/")[0])
        if rid == _JOBLESS:
            return []
        return [json.dumps({"run_id": rid, "job_id": rid * 10, "name": "x",
                            "status": "completed", "conclusion": "success",
                            "started_at": "2026-08-23T15:00:00Z",
                            "completed_at": "2026-08-23T15:01:00Z"})]

    _got_jobs, _jobless = fetch_jobs([1, _JOBLESS, 3], _jobs_reader)
    check("the other runs' jobs still arrive", len(_got_jobs), 2)
    check("the jobless run is carried by id, not dropped", _jobless, [_JOBLESS])
    check("and is not invented as a job", [j["run_id"] for j in _got_jobs], [1, 3])
    _rep_jobless = census(_got_jobs, [{"id": 1, "name": "gates", "event": "push"},
                                      {"id": 3, "name": "gates", "event": "push"}],
                          _jobless)
    check("the jobless run reaches the report",
          _rep_jobless["runs_without_jobs"], [_JOBLESS])
    check("and is outside the counted population", _rep_jobless["jobs_counted"], 2)
    check("census defaults the bucket to empty, never to None",
          census([], [])["runs_without_jobs"], [])
    # MUTANT: the refusal that has to survive. If NOTHING answers, an empty bucket would
    # report 0 minutes over a silent endpoint -- the confident zero this tool exists to
    # refuse. Only the all-empty case raises.
    try:
        fetch_jobs([1, 2, 3], lambda *_: [])
        failures.append("fetch_jobs reported 0 minutes when NO run yielded a job -- that "
                        "is a dead endpoint, not an idle repository")
    except DataError:
        pass
    check("no runs asked for is not a refusal", fetch_jobs([], lambda *_: []), ([], []))
    # The bucket has to reach the PRINTED census too. Recorded and never shown is a total
    # that reads as complete, which is the whole failure -- so this renders it.
    with contextlib_redirect_all() as _shown:
        _print_census(_rep_jobless, None, False)
    _text = _shown()
    check("the printed census names the jobless run's id", str(_JOBLESS) in _text, True)
    check("and says it is NOT counted", "NOT counted" in _text, True)
    # And the visibility reaches the print, rather than a literal doing it again.
    check("the rendered census says PUBLIC when told public", "PUBLIC" in _text, True)
    check("and does not also say PRIVATE", "PRIVATE" in _text, False)
    with contextlib_redirect_all() as _shown_private:
        _print_census(_rep_jobless, None, True)
    check("the same report says PRIVATE when told private",
          "PRIVATE" in _shown_private(), True)

    # -- the visibility read, offline in both directions --------------------------------
    # The tool printed `(PRIVATE -- these minutes are metered)` as a literal, and went on
    # printing it for a day after the repository was made public (task 148). The reader is
    # injected here, so nothing below touches the network.
    check("`.private: false` is not private", fetch_visibility(lambda *_: ["false"]), False)
    check("`.private: true` is private", fetch_visibility(lambda *_: ["true"]), True)
    check("surrounding whitespace still parses",
          fetch_visibility(lambda *_: ["  true  "]), True)
    # The address is an input to the check (AGENTS.md rule 12): a correct parse of the
    # wrong endpoint is a confident answer about a different repository.
    _asked: list[tuple] = []

    def _recording(endpoint, jq):
        _asked.append((endpoint, jq))
        return ["false"]

    fetch_visibility(_recording)
    check("the endpoint read is this repository's record",
          _asked, [(f"repos/{REPO}", ".private")])
    # VARIANTS: everything a `.private` read can come back as that is not an answer. Each
    # must REFUSE. A tool that guesses here prints a sentence about money.
    for _label, _lines in {
        "an empty result": [],
        "a blank line": [""],
        "jq's null": ["null"],
        "Python's True": ["True"],
        "a JSON object": ['{"private": false}'],
        "two lines": ["false", "true"],
        "the whole repo record": ['{"name": "game-stack-bakeoff"}'],
    }.items():
        try:
            _got = fetch_visibility(lambda *_a, _l=_lines: _l)
            failures.append(f"fetch_visibility ANSWERED {_got!r} on {_label} ({_lines!r}) "
                            f"-- an unreadable visibility must refuse, not guess")
        except DataError:
            pass
    # And a `gh` failure propagates rather than becoming an answer: main() turns DataError
    # into exit 2, so this is the census refusing rather than reporting a free minute.
    def _angry(*_a):
        raise DataError("repos/x: gh exited 1")
    try:
        _got = fetch_visibility(_angry)
        failures.append(f"fetch_visibility swallowed a gh failure and returned {_got!r}")
    except DataError:
        pass
    # The two printed lines must actually differ, and each must say the true thing. A
    # formatter that ignored its argument would pass a check on one branch alone.
    check("public is not called metered", "metered" in visibility_line(False), False)
    check("the metered line does not say PUBLIC", "PUBLIC" in visibility_line(True), False)
    check("the free line says PUBLIC", "PUBLIC" in visibility_line(False), True)
    check("private says metered", "metered" in visibility_line(True), True)
    check("the two repository lines differ",
          visibility_line(True) == visibility_line(False), False)
    check("no allowance sentence on a public repository",
          any("allowance" in ln and "No allowance" not in ln
              for ln in allowance_lines(False)), False)
    check("the metered branch still names the billing endpoint",
          any("settings/billing/actions" in ln for ln in allowance_lines(True)), True)
    # MUTANT: _print_census must not have a default for `private`. A default is exactly the
    # remembered value this repair removed, one call site later.
    try:
        _print_census({}, None)  # type: ignore[call-arg]
        failures.append("_print_census accepted no `private` argument -- a default here is "
                        "a remembered answer about whether minutes are billed")
    except TypeError:
        pass

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


def _print_census(rep: dict, billable_field: dict[int, int] | None, private: bool) -> None:
    # `private` has no default on purpose: a caller that forgets it gets a TypeError, not a
    # remembered answer about whether these minutes cost anything.
    print("GitHub Actions minutes consumed, read from the API, not estimated")
    print(visibility_line(private))
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
    if rep["runs_without_jobs"]:
        ids = ", ".join(str(r) for r in rep["runs_without_jobs"])
        print(f"  NOT counted              : {len(rep['runs_without_jobs'])} run(s) the "
              f"jobs endpoint had nothing for ({ids})")
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
    for line in allowance_lines(private):
        print(line)


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
    ap = _build_parser()
    try:
        args = ap.parse_args(argv)
    except _ArgExit as exc:
        # `--help`. The parser has already printed it, because this one is not `quiet`.
        return exc.status
    except _ArgError as exc:
        ap.print_usage(sys.stderr)
        print(f"ci_minutes: {exc}", file=sys.stderr)
        return 2

    # BEFORE DISPATCH, and that placement is the whole point: every branch below is a
    # different report, and reaching one of them having discarded a flag is exit 0 for
    # something other than what was asked for.
    bad = invocation_problems(args)
    if bad:
        for problem in bad:
            print(f"ci_minutes: {problem}", file=sys.stderr)
        print("ci_minutes: refusing to run. An ignored flag is worse than a rejected one.",
              file=sys.stderr)
        return 2

    if args.selftest:
        return _selftest()

    if args.scope:
        return emit_scope()

    if args.gates:
        return gates_report(gate_census(), as_json=args.json)

    if args.hooks:
        return hooks_report(hook_census(), as_json=args.json)

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
            jobs, jobless = fetch_jobs(ids)
            timing = None if args.no_timing else fetch_billable_field(ids)
            private = fetch_visibility()
            rep = census(jobs, runs, jobless)
            if args.json:
                print(json.dumps({**rep, "repository_private": private}, indent=2))
            else:
                _print_census(rep, timing, private)
            payload = {"runs": runs, "jobs": jobs, "census": rep, "timing": timing,
                       "repository_private": private}
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
