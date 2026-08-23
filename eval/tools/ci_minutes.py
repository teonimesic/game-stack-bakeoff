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

--selftest pins both directions offline, in ~0.06s and without touching a file. Mutants that
must be caught: truncation instead of rounding up, and five ways `controls.yml`'s filter can
lose a path. Variants that must still PASS: an in-flight job, a job of exactly 60s, a 22s job,
a filename that merely starts with a filtered directory's letters, and a reordered, re-quoted
or commented filter. The variants are not decoration -- the substring check this replaced went
red on a re-quote, which is a gate firing where nothing is wrong.

Usage:
    python3 eval/tools/ci_minutes.py                 # the census, from the API
    python3 eval/tools/ci_minutes.py --path-filter   # the path-filter audit
    python3 eval/tools/ci_minutes.py --cache DIR     # also write the raw JSON it consumed
    python3 eval/tools/ci_minutes.py --selftest      # controls, both directions, offline

Exit 0 on success, 1 if --selftest fails, 2 if the data could not be read. Read it unpiped.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import math
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


def matches_filter(path: str) -> bool:
    """Does one changed path satisfy controls.yml's filter?

    The prefixes carry their trailing slash, so `evaluation.md` is not `eval/**` -- a
    filename that merely starts with a filtered directory's letters is the variant this
    would otherwise mishandle.
    """
    return path.startswith(FILTER_PREFIXES) or path in FILTER_EXACT


def filter_problems(controls_text: str, gates_text: str | None = None) -> list[str]:
    """Does `controls.yml` still declare, per EVENT, every path `FILTER_*` claims?

    PURE, and parsed rather than substring-matched, for one measured reason: the first
    version asked `if "'.claude/**'" not in text` over the whole file, and the mutant that
    deletes `.claude/**` from the `pull_request` filter alone SURVIVED it -- the string was
    still there under `push`. A check that reads a two-filter file as one flat blob cannot
    see which filter a path fell out of, which is exactly the drift worth gating. Parsing
    also stops the check false-positiving on a re-quote or a reorder, which the substring
    version did.

    Pure so the mutants can be planted on a STRING. Planting them on the real workflow
    file works and is what `skill_layout_control.py` does, but a control that rewrites
    `.github/workflows/controls.yml` can leave it broken if it dies mid-run, and this one
    has no need to touch a file at all.
    """
    problems: list[str] = []
    for label, text in (("controls.yml", controls_text), ("gates.yml", gates_text)):
        if text is None:
            continue
        if "ubuntu-latest" not in text:
            problems.append(f"{label} is not on ubuntu-latest; the 1x multiplier is wrong")

    try:
        import yaml
    except ImportError:  # pragma: no cover - pyyaml is installed in CI and locally
        return problems + [
            ("pyyaml is missing, so the filter could not be parsed. "
             "That is a refusal, not a passing filter check.")
        ]

    doc = yaml.safe_load(controls_text) or {}
    # YAML 1.1 resolves a bare `on:` key to the boolean True, so `doc["on"]` is a KeyError
    # and `doc.get("on", {})` would silently check nothing at all.
    triggers = doc.get(True, doc.get("on"))
    if not isinstance(triggers, dict):
        return problems + ["controls.yml has no parseable `on:` block"]

    want = {f"{p}**" for p in FILTER_PREFIXES} | set(FILTER_EXACT)
    for event in ("pull_request", "push"):
        cfg = triggers.get(event)
        if not isinstance(cfg, dict) or not cfg.get("paths"):
            problems.append(
                f"controls.yml's `{event}` trigger declares no `paths:`. An absent filter "
                f"is not an empty one -- it runs on every event")
            continue
        missing = want - set(cfg["paths"])
        if missing:
            problems.append(
                f"controls.yml's `{event}` filter is missing {sorted(missing)}; FILTER_* in "
                f"this tool and the workflow have drifted apart")
    return problems


def path_filter_audit(runs: list[dict], compare) -> dict:
    """For each `controls` PR run after the first on its branch, did the LATEST PUSH touch
    a filter path?

    `compare(base_sha, head_sha) -> list[str]` supplies the push's own diff. The first run
    on a branch has no predecessor, so its push range IS the whole-PR diff; it matches by
    construction and is reported in its own bucket rather than counted as evidence either
    way.

    IT DELIBERATELY DOES NOT COMPUTE THE ACCUMULATED PULL-REQUEST DIFF, and a `no-match`
    row is still evidence about it. The inference has two halves, and only one of them is
    a measurement:

      1. the run EXISTS, with `event: pull_request`. GitHub dispatches a `pull_request`
         workflow only when its `paths:` filter matches, and that filter is defined over
         the accumulated diff. So the accumulated diff matched -- observed, not computed.
      2. the latest push's own diff matched NOTHING filtered -- measured here.

    Together: the run was bought by something other than the push that triggered it, and
    the only thing that can buy it is the accumulated diff. Computing that diff as well
    would re-derive half of what the run's existence already states.

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


def compare_via_api(base: str, head: str) -> list[str]:
    return _gh(f"repos/{REPO}/compare/{base}...{head}", ".files[]?.filename")


# ---------------------------------------------------------------- the controls


def _selftest() -> int:
    failures: list[str] = []

    def check(name: str, got, want):
        if got != want:
            failures.append(f"{name}: got {got!r}, want {want!r}")

    # -- the boundary, and the mutant it exists to kill ---------------------------------
    # Truncation is the plausible wrong implementation, and it is what this tool was first
    # written with on purpose. The 22s and 61s rows are what separate it from ceil; a
    # fixture set of whole minutes only would let that mutant survive.
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

        mutants = {
            ".claude/** gone from pull_request only":
                drop(live, "      - '.claude/**'\n"),
            "eval/** gone from pull_request only":
                drop(live, "      - 'eval/**'\n"),
            "the controls.yml self-reference gone":
                drop(live, "      - '.github/workflows/controls.yml'\n"),
            "the whole pull_request paths: block gone":
                live.replace(
                    "  pull_request:\n    paths:\n      - 'eval/**'\n      - '.agents/**'\n"
                    "      - '.claude/**'\n      - '.github/workflows/controls.yml'\n",
                    "  pull_request:\n"),
            "the runner moved off ubuntu-latest":
                live.replace("runs-on: ubuntu-latest", "runs-on: macos-latest"),
        }
        variants = {
            "the paths are reordered": live.replace(
                "    paths:\n      - 'eval/**'\n      - '.agents/**'\n      - '.claude/**'\n",
                "    paths:\n      - '.claude/**'\n      - 'eval/**'\n      - '.agents/**'\n",
                1),
            "an extra path this tool does not name": live.replace(
                "      - 'eval/**'\n", "      - 'eval/**'\n      - 'scripts/**'\n", 1),
            "a comment inside the filter": live.replace(
                "    paths:\n", "    paths:\n      # a note\n", 1),
            "the paths are double-quoted": live.replace("- 'eval/**'", '- "eval/**"'),
        }
        for name, text in mutants.items():
            if text == live:
                failures.append(f"mutant '{name}' changed nothing; it is void, not caught")
            elif not filter_problems(text, gates_yml.read_text()):
                failures.append(f"MUTANT SURVIVED: {name}")
        for name, text in variants.items():
            if text == live:
                failures.append(f"variant '{name}' changed nothing; it is void, not passed")
            elif filter_problems(text, gates_yml.read_text()):
                failures.append(f"FALSE POSITIVE on variant: {name}")

    check("eval/ source matches", matches_filter("eval/tools/tasks.py"), True)
    check("a skill matches", matches_filter(".claude/skills/work/SKILL.md"), True)
    check("the workflow itself matches", matches_filter(".github/workflows/controls.yml"), True)
    check("its README does NOT match", matches_filter(".github/workflows/README.md"), False)
    check("a task file does NOT match", matches_filter("tasks/124-ci-path-filter.md"), False)
    check("a root doc does NOT match", matches_filter("README.md"), False)
    # The variant: a filename that merely begins with a filtered directory's letters.
    check("evaluation.md is not eval/", matches_filter("evaluation.md"), False)

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
          "(billing arithmetic, the third value, the filter, the audit)")
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
    print("controls.yml's path filter: was each run bought by the LATEST PUSH, or by the "
          "whole-PR diff?")
    print(f"  controls runs on pull_request : {aud['controls_pr_runs']}")
    print("  first-on-branch (no predecessor push; matches by construction): "
          f"{aud['first_on_branch']}")
    print(f"  analysed                      : {aud['analysed']}")
    print(f"    latest push touched a filter path   : {aud['match']}")
    print(f"    latest push touched NOTHING filtered: {aud['no_match']}  "
          "<-- bought by the accumulated diff")
    print(f"    same sha as the previous run        : {aud['same_sha']}")
    print()
    for row in aud["rows"]:
        print(f"  {row['verdict']:9} {row['run']}  {row['branch']}")
        if row["verdict"] == "no-match":
            for f in row["files"]:
                print(f"              {f}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    ap.add_argument("--selftest", action="store_true",
                    help="controls, both directions, offline")
    ap.add_argument("--path-filter", action="store_true", help="the path-filter audit")
    ap.add_argument("--no-timing", action="store_true",
                    help="skip the per-run /timing read (one extra API call per run)")
    ap.add_argument("--cache", metavar="DIR",
                    help="write the raw JSON consumed, so the number is re-derivable offline")
    ap.add_argument("--json", action="store_true", help="machine-readable")
    args = ap.parse_args(argv)

    if args.selftest:
        return _selftest()

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
        d = pathlib.Path(args.cache)
        d.mkdir(parents=True, exist_ok=True)
        target = d / ("path_filter.json" if args.path_filter else "minutes.json")
        target.write_text(json.dumps(payload, indent=2))
        print(f"\n  raw JSON written to {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
