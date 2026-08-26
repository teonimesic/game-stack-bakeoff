#!/usr/bin/env python3
"""Has CodeRabbit reviewed the head of *this branch's* pull request yet?

This is the producer behind `.agents/skills/work/SKILL.md` section 6. It replaces a shell
recipe that agents copied into a scratchpad file and ran in a loop.

WHY IT IS A TOOL AND NOT A RECIPE
---------------------------------
The recipe hardcoded `PR=<n>` and printed only a head sha, so **the pull request being
polled appeared in no line of its output**. On 2026-08-23 the agent working task 123 wrote
its copy to a generic scratchpad name in a directory shared with every concurrent session;
the agent working task 124 wrote its own copy over the same path with `PR=10`; and the
first loop silently began polling the second agent's pull request, reporting `not yet` at
exit 0 for 16 polls (`tasks/127`). Had #10's review landed, the loop would have reported
`LANDED` for a review of a diff its agent had never written — and the next step in the
procedure is to read that review and act on it.

`AGENTS.md` rule 12 is *the address is an input to the check*, and its instance table was
five cases of an address that was **wrong when it was written**. This is the other kind: an
address that was **right when written and wrong later**, because something else could write
it. A tool takes the address as an argument on every invocation, so there is no interval
between writing the address down and using it.

WHAT IT ASSERTS BEFORE IT WILL ANSWER
-------------------------------------
Each of these refuses with exit 1. None of them is a poll result:

| guard | what its absence lets through |
|---|---|
| `--branch` equals the pull request's `headRefName`, exactly | a verdict about somebody else's pull request, which is the defect above |
| `--expect-head`, when given, equals `headRefOid` | the API had not caught up to your push, and the poll answers about the previous head (#165) |
| the head is 40 lowercase hex | `contains("")` is true of every string, so an empty head reports every pull request reviewed — fail-**open** |
| `gh` exited 0 | a state inferred from a command that did not run (rule 2) |

WHAT COUNTS AS REVIEWED, AND WHY IT IS A DISJUNCTION
----------------------------------------------------
`DECISIONS.md`, *An agent hands back a pull request*, holds the derivation and the
per-pull-request evidence; if it and this file disagree, it wins and this file is the bug.
In short: a landed review has two shapes, and reading only one of them times out on the
good outcome. Neither arm alone covers this repository's own pull requests.

| verdict | exit | what fired |
|---|---|---|
| `LANDED_REVIEW` | 0 | a `coderabbitai[bot]` review object with a **non-empty body** whose `commit_id` is the head. A reply to a comment also creates a review object, stamped with the current head and with an empty body — without the body guard that is indistinguishable from a review |
| `LANDED_COMMENT` | 0 | a `coderabbitai[bot]` issue comment naming the head and **not** carrying the review-in-progress marker. This is the clean outcome, and it creates no review object at all |
| `IN_FLIGHT` | 11 | a `coderabbitai[bot]` comment naming the head **with** the marker. The round is running; the verdict printed below it is the previous round's |
| `REVIEW_FAILED` | 14 | a `Review failed` alert heading. A round started and died, and the summary it left behind is a comment at the head that looks exactly like a clean one. Post `@coderabbitai review` |
| `NOTICE` | 12 | any other GitHub alert callout heading in a bot comment — a pause, a spent allowance, a skip. Read the body; each states its own remedy |
| `NOT_YET` | 10 | none of the above |
| — | 1 | a guard refused, or `gh` failed |
| `UNRESOLVED` | 13 | `--wait` gave up. A loud outcome, never a quiet "no review" |

`LANDED_REVIEW` outranks `IN_FLIGHT` outranks `REVIEW_FAILED` outranks `LANDED_COMMENT`
outranks `NOTICE`. A notice is last because CodeRabbit **edits its comments in place**: PR
#6's `Review limit reached` heading was measured on 2026-08-23 and is no longer extractable
from PR #6 today. A notice is a diagnostic; the two landed arms are the authority.

WHY A FAILED ROUND IS A VERDICT AND NOT A NOTICE
------------------------------------------------
A notice heading used to be one thing, and the poll asked only whether one existed. That is
the mechanism, not the property — and the property is *has this head been reviewed*.
`Reviews paused` and `Review limit reached` say a round has not **started**, and they sit
beside whatever the previous round left, so they leave the comment arm alone. **`Review
failed — the head commit changed during the review` says a round started and DIED**, and it
rewrites the summary comment at the head, so the artifact is byte-for-byte the shape of a
clean landing. Merging `main` into a branch mid-review produces it.

Measured on PR #39 (`tasks/162`): `--wait --ignore-notice` returned `LANDED_COMMENT` at
`elapsed=0s` with `notice=Review failed` on the same line, and the real review arrived
**540 s** later (#185). The procedure's next step is to act on the review, so *nothing to
say* and *the reviewer was interrupted* produced the same behaviour.

So a failed round gets its own verdict, ranked **above** the comment arm and **below** both a
real review object and a round in flight. A review object at the head means the head was
reviewed whatever a stale callout beside it says; an in-progress marker at the head means a
new round is already running and the wait should keep waiting.

It is detected by **its HTML marker or its alert heading** — 2 signals, for the same reason a
landing is read 2 ways: either alone can be wrong later, and each arm covers the other. Both
strings come from a real `coderabbitai[bot]` failure block, which also shows *why* the comment
arm was satisfied: the block **writes the new head sha into its own body**.

That sha is also what dates it. A failure suppresses the comment arm at the head its own block
names and at no other, so a previous round's callout cannot hold up a landing that really
happened. A block naming no sha cannot be dated and counts.

WHY THE WAIT IS NOT A CLOCK
---------------------------
A fixed 15-minute bound was measured wrong. Task 130's agent polled PR #15 29 times, said
no review had landed, and handed the work back as ready; the review was submitted at
**19m26s** on a 4-file documentation diff, and it carried four threads, one Major, naming a
real rule-4 violation. Raising the constant is the same defect at a larger value.

So the bound is on **silence**, not on elapsed time. `--quiet-timeout` (default 20 min)
applies while no round has ever been observed in flight; once one has — the in-progress
marker is a real, observable signal, and it was present throughout that 19m26s —
`--flight-timeout` (default 60 min) governs instead, and the observation **latches**,
because CodeRabbit rewrites the summary comment during a round and the marker can come and
go. Expiry prints `UNRESOLVED` and exits 13; a timeout is a result to hand back, not a
silence to mistake for one.

USE
---
    # one poll, from the worktree whose branch it is about
    python3 eval/tools/pr_review_state.py --pr 18 --branch task-127-poll-asserts-its-branch \\
        --expect-head "$(git rev-parse HEAD)"

    # wait for the round, printing a line every 30s
    python3 eval/tools/pr_review_state.py --pr 18 --branch task-127-poll-asserts-its-branch \\
        --expect-head "$(git rev-parse HEAD)" --wait

    # the poll you start AFTER posting `@coderabbitai review`, so the comment the reviewer
    # has not rewritten yet cannot stop you the moment you look
    python3 eval/tools/pr_review_state.py --pr 18 --branch task-127-poll-asserts-its-branch \\
        --expect-head "$(git rev-parse HEAD)" --wait --ignore-notice

    python3 eval/tools/pr_review_state.py --census      # every PR, which arm fires
    python3 eval/tools/pr_review_state.py --selftest    # offline, no network

Every line of output names the pull request, the branch and the full head sha. The
assertion is the guard; the printing is the audit trail (`AGENTS.md`, *capture what the
instrument did*). Neither replaces the other: an assertion fails closed at the moment of
use, and a printed line is only as good as the reader who happens to look at it.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import re
import subprocess
import sys
import time
from typing import Any, Callable, Iterable, Sequence

REPO = "teonimesic/game-stack-bakeoff"
BOT = "coderabbitai[bot]"

# The HTML comment CodeRabbit writes above a summary while the round is still running. The
# "No actionable comments were generated" line sitting below it at that moment belongs to
# the PREVIOUS round.
INPROGRESS_MARKER = "auto-generated comment: review in progress by coderabbit.ai"

# GitHub's alert vocabulary is a closed class of five. The deadlock notices are alert
# callouts with a heading; matching one alert TYPE was measured worse than matching the
# heading, because the pause notice is a NOTE and the limit notice is a WARNING.
ALERT_HEADING = re.compile(r"> \[!(?:NOTE|TIP|IMPORTANT|WARNING|CAUTION)\]\n> ## ([^\n]*)")

# A failed round is read two ways, for the same reason the landed arms are: either signal
# alone can be wrong later. The HTML comment is the machine one, bracketing the block exactly
# as INPROGRESS_MARKER brackets a running round; the heading is what a reader sees and what
# the poll line prints. Both are taken from the real artifact on meshery/meshery#21612 — this
# repository's own instance was rewritten in place and is no longer extractable from PR #39.
FAILURE_MARKER = "auto-generated comment: failure by coderabbit.ai"

# The quoted alert block a failed round leaves, captured so the shas INSIDE it can be read
# apart from any other sha in the same comment — CodeRabbit writes the failure into the very
# summary comment that names the current head elsewhere.
#
# The heading is ANCHORED: `> ## Review failed`, so a heading that merely mentions a failed
# review is not one. It is left open at the end, because the reason CodeRabbit gives ("The
# head commit changed during the review from <sha> to <sha>.") is in the block body today and
# could be appended to the heading tomorrow.
FAILURE_ALERT_BLOCK = re.compile(
    r"> \[!(?:NOTE|TIP|IMPORTANT|WARNING|CAUTION)\]\n> ## Review failed[^\n]*\n((?:>[^\n]*\n?)*)",
    re.IGNORECASE)

FULL_SHA = re.compile(r"\A[0-9a-f]{40}\Z")
SHA_ANYWHERE = re.compile(r"(?<![0-9a-f])[0-9a-f]{40}(?![0-9a-f])")

QUIET_TIMEOUT = 20 * 60
FLIGHT_TIMEOUT = 60 * 60
POLL_SECONDS = 30

# Every `gh` call is bounded. A hung `gh` never returns, so `wait_for` never reaches the
# line that checks its budget: the silence bound would be unreachable and `--wait` would
# hang forever on the one failure mode it exists to bound. 60s is 2x the poll interval,
# so a call that overruns it has already lost its slot.
GH_TIMEOUT = 60

# `gh pr list` takes a --limit and silently returns that many. A census that stops at the
# cap is a census reporting the cap, so the cap is high and reaching it is a REFUSAL.
CENSUS_LIMIT = 1000

EXIT = {
    "LANDED_REVIEW": 0,
    "LANDED_COMMENT": 0,
    "NOT_YET": 10,
    "IN_FLIGHT": 11,
    "NOTICE": 12,
    "UNRESOLVED": 13,
    "REVIEW_FAILED": 14,
}


class PrReviewStateError(Exception):
    """A refusal. Never a poll result — the caller must stop, not poll again."""


# --------------------------------------------------------------------------- gh access

def _gh(args: Sequence[str], runner: Callable[..., Any] = subprocess.run) -> str:
    """Run `gh` and return stdout, bounded by `GH_TIMEOUT`. A non-zero exit RAISES.

    Without the returncode check a failing API becomes a poll result: the loop reports a
    review state inferred from a command that did not run (rule 2), and an empty stdout
    then parses as "no reviews", which is a plausible in-range answer rather than a crash.
    """
    try:
        proc = runner(["gh", *args], capture_output=True, text=True, check=False,
                      timeout=GH_TIMEOUT)
    except subprocess.TimeoutExpired as exc:
        raise PrReviewStateError(
            f"gh {' '.join(args)} did not return within {GH_TIMEOUT}s") from exc
    if proc.returncode != 0:
        raise PrReviewStateError(
            f"gh {' '.join(args)} exited {proc.returncode}: "
            f"{(proc.stderr or proc.stdout or '').strip()[:400]}")
    return proc.stdout


def parse_pages(raw: str) -> list[dict]:
    """Flatten what `gh api --paginate` prints for an array endpoint.

    gh 2.98 merges the pages into ONE array; older versions concatenate one array per
    page. Reading only the first decoded value is correct on the first and silently drops
    every page but one on the second — and the review at the head sha is the NEWEST, so it
    is the first record to fall off page 1. Measured on PR #6 at `per_page=2`: 2 records
    read one-page, 10 read paginated.
    """
    decoder = json.JSONDecoder()
    out: list[dict] = []
    i = 0
    while i < len(raw):
        while i < len(raw) and raw[i].isspace():
            i += 1
        if i >= len(raw):
            break
        value, i = decoder.raw_decode(raw, i)
        if isinstance(value, list):
            out.extend(value)
        else:
            out.append(value)
    return out


def fetch_view(pr: int, repo: str = REPO, runner: Callable[..., Any] = subprocess.run) -> dict:
    """The address, read once and in ONE call so branch and sha cannot disagree."""
    raw = _gh(["pr", "view", str(pr), "--repo", repo, "--json", "headRefOid,headRefName"],
              runner=runner)
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise PrReviewStateError(f"gh pr view #{pr} returned unparseable JSON: {exc}") from exc


def fetch_reviews(pr: int, repo: str = REPO,
                  runner: Callable[..., Any] = subprocess.run) -> list[dict]:
    return parse_pages(_gh(["api", "--paginate", f"repos/{repo}/pulls/{pr}/reviews"],
                           runner=runner))


def fetch_comments(pr: int, repo: str = REPO,
                   runner: Callable[..., Any] = subprocess.run) -> list[dict]:
    return parse_pages(_gh(["api", "--paginate", f"repos/{repo}/issues/{pr}/comments"],
                           runner=runner))


# ------------------------------------------------------------------------- the address

def check_address(pr: int, view: dict, expect_branch: str,
                  expect_head: str | None = None) -> str | None:
    """Return a refusal message, or None if this pull request is the one you meant.

    This is the whole point of the tool. Everything below it is the question; this is
    whether the question is being asked of the right subject.
    """
    head = (view or {}).get("headRefOid") or ""
    branch = (view or {}).get("headRefName") or ""

    if not FULL_SHA.match(head):
        return (f"NO HEAD SHA: #{pr} gave {head!r}, which is not 40 lowercase hex. "
                "This is an error, not a poll result.")
    if not branch:
        return f"NO BRANCH: #{pr} gave no headRefName. This is an error, not a poll result."
    if branch != expect_branch:
        return (f"WRONG PR: #{pr} is on branch {branch!r}, expected {expect_branch!r}. "
                "You are polling somebody else's pull request.")
    if expect_head is not None:
        if not FULL_SHA.match(expect_head):
            return (f"EXPECTED HEAD NOT A FULL SHA: {expect_head!r}. Pass "
                    "`$(git rev-parse HEAD)`, never an abbreviation.")
        if head != expect_head:
            return (f"STALE HEAD: #{pr} on {branch} reads {head}, you expected "
                    f"{expect_head}. Either the API has not caught up to your push, or "
                    "someone else pushed. Do not poll until it agrees.")
    return None


# ------------------------------------------------------------------------ the question

def _by_bot(records: Iterable[dict]) -> list[dict]:
    """Only the reviewer's own records.

    Without this filter the agent trips the check by following the procedure: §6 tells it
    to reply to what it declines, and a comment quoting the marker while explaining it
    already matched once.
    """
    return [r for r in records if ((r.get("user") or {}).get("login")) == BOT]


def alert_headings(comments: Iterable[dict]) -> list[str]:
    out: list[str] = []
    for c in _by_bot(comments):
        out.extend(ALERT_HEADING.findall(c.get("body") or ""))
    return out


def failed_rounds(comments: Iterable[dict], head: str | None = None) -> list[dict]:
    """The bot comments saying a round STARTED AND DIED at `head`.

    Splitting the notices by what they imply is the whole repair. A pause or a spent
    allowance says a round has not started, and it sits beside whatever the previous round
    left — so it must not touch the comment arm, or every paused branch stops landing. A
    failed round writes *"The head commit changed during the review from <old> to <new>"*
    into its own body, so the artifact it leaves satisfies the comment arm exactly and the
    comment arm must not read it as a landing.

    **Each block is dated by the LAST sha in it, and a comment counts if any of its blocks
    is about `head`.**
    Both cheaper answers are wrong in one direction each: reading every failure on the pull
    request lets a previous round's callout suppress a landing that really happened, and
    scoping to the comment that names the head misses a failure posted in a comment of its
    own — which is `LANDED_COMMENT` at exit 0 on an unreviewed head, the defect itself.
    Reading the sha out of the block answers both, because the block says which head it died
    on. It has to come from the BLOCK: CodeRabbit writes the failure into the same summary
    comment that names the current head elsewhere.

    **A block that names no sha cannot be dated, so it counts.** That is fail-closed where
    the evidence is missing (rule 7), and its cost is a wait that expires loudly.
    """
    # `head=None` asks the question without a head, which is what the extraction rows below
    # use: is this comment a failed round at all?
    out: list[dict] = []
    for c in _by_bot(comments):
        body = c.get("body") or ""
        blocks = FAILURE_ALERT_BLOCK.findall(body)
        if not blocks and FAILURE_MARKER not in body:
            continue
        if head is not None and blocks:
            dated = [(SHA_ANYWHERE.findall(b) or [None])[-1] for b in blocks]
            # Each block is its own round. Flattening them and reading one sha lets a block
            # that names this head be overruled by a later block that names another.
            if not any(d is None or d == head for d in dated):
                continue
        out.append(c)
    return out


def classify(head: str, reviews: Iterable[dict], comments: Iterable[dict]) -> dict:
    """Decide the verdict at `head`. Raises if `head` is not a full sha.

    The guard is repeated here rather than left to `check_address` because `contains("")`
    is true of every string: an empty head makes the comment arm report every pull request
    reviewed, which turns a fail-slow defect into a fail-open one.
    """
    if not FULL_SHA.match(head or ""):
        raise PrReviewStateError(
            f"classify called with {head!r}, which is not 40 lowercase hex")

    by_review = [r for r in _by_bot(reviews)
                 if (r.get("body") or "") != "" and r.get("commit_id") == head]

    naming = [c for c in _by_bot(comments) if head in (c.get("body") or "")]
    in_flight = [c for c in naming if INPROGRESS_MARKER in (c.get("body") or "")]
    finished = [c for c in naming if INPROGRESS_MARKER not in (c.get("body") or "")]
    headings = alert_headings(comments)
    failed = failed_rounds(comments, head)

    if by_review:
        verdict = "LANDED_REVIEW"
    elif in_flight:
        verdict = "IN_FLIGHT"
    elif failed:
        verdict = "REVIEW_FAILED"
    elif finished:
        verdict = "LANDED_COMMENT"
    elif headings:
        verdict = "NOTICE"
    else:
        verdict = "NOT_YET"

    # `by_comment` still counts the summary at the head under `REVIEW_FAILED`, and `failed`
    # sits beside it. Both are true — a comment does name the head, and it is not evidence
    # of a review — and the verdict says which won. Zeroing the count instead would hide
    # the artifact the verdict is about.
    return {
        "verdict": verdict,
        "by_review": len(by_review),
        "by_comment": len(finished),
        "in_flight": len(in_flight),
        "failed": len(failed),
        "headings": headings,
    }


def poll(pr: int, expect_branch: str, expect_head: str | None = None, repo: str = REPO,
         runner: Callable[..., Any] = subprocess.run) -> dict:
    """One poll: assert the address, then answer. Raises `PrReviewStateError` on refusal."""
    view = fetch_view(pr, repo=repo, runner=runner)
    refusal = check_address(pr, view, expect_branch, expect_head)
    if refusal:
        raise PrReviewStateError(refusal)
    head = view["headRefOid"]
    result = classify(head, fetch_reviews(pr, repo=repo, runner=runner),
                      fetch_comments(pr, repo=repo, runner=runner))
    result.update(pr=pr, branch=view["headRefName"], head=head)
    return result


def render(result: dict, elapsed: float | None = None) -> str:
    """Every line names the pull request, the branch and the full head sha."""
    line = (f"#{result['pr']} {result['branch']} head={result['head']} "
            f"verdict={result['verdict']} by_review={result['by_review']} "
            f"by_comment={result['by_comment']} in_flight={result['in_flight']} "
            f"failed={result['failed']}")
    if result.get("headings"):
        line += " notice=" + " | ".join(result["headings"])
    if elapsed is not None:
        line += f" elapsed={int(elapsed)}s"
    return line


# ----------------------------------------------------------------------------- waiting

def _emit(line: str) -> None:
    """Print a poll line and FLUSH it.

    Python block-buffers stdout when it is not a terminal, so a `--wait` running under a
    harness that captures its output shows nothing at all until the loop exits — measured,
    0 bytes through a live round. An audit trail that only appears once the answer is
    already known is not an audit trail.
    """
    print(line, flush=True)


def wait_for(poll_fn: Callable[[], dict], *, now_fn: Callable[[], float] = time.monotonic,
             sleep_fn: Callable[[float], None] = time.sleep,
             emit: Callable[[str], None] = _emit,
             poll_seconds: int = POLL_SECONDS, quiet_timeout: int = QUIET_TIMEOUT,
             flight_timeout: int = FLIGHT_TIMEOUT, ignore_notice: bool = False) -> dict:
    """Poll until the round resolves, or until SILENCE — not elapsed time — runs out.

    `seen_in_flight` LATCHES. CodeRabbit rewrites the summary comment during a round, so
    the marker can appear and disappear while the round is still running; a bound
    recomputed from the latest poll alone would expire at the quiet timeout on exactly the
    case this design exists for.

    `ignore_notice` is for the poll you start AFTER acting on a notice. A deadlock notice
    is a comment, and CodeRabbit leaves it in place until it next rewrites the summary — so
    a wait that stops on it stops instantly, every time, and the remedy you just applied can
    never be observed to have worked. Measured on this tool's own pull request: `--wait`
    returned `NOTICE` at `elapsed=1s` on a pause that had already been answered with
    `@coderabbitai review`. With the flag the notice is still printed on every line; it just
    stops being a stop condition, and a genuinely new pause then costs the quiet bound —
    loud, not silent.

    **The flag governs STOPPING, and it can never turn anything into a landing.** That
    distinction is the repair for #185: `--ignore-notice` used to make `REVIEW_FAILED`'s
    artifact — a rewritten summary comment sitting at the head — return `LANDED_COMMENT` at
    exit 0, because the flag named the mechanism (a notice exists) rather than the property
    (was this head reviewed). `REVIEW_FAILED` is now a verdict above the comment arm, so no
    flag reaches it; the flag only decides whether the wait stops to let you act. Un-flagged
    it stops, because you have not asked for the round again yet. Flagged — the poll you run
    after posting `@coderabbitai review` — it keeps waiting, so the callout the reviewer has
    not rewritten yet cannot deadlock you, and if nothing ever comes the bound expires as
    `UNRESOLVED`.
    """
    started = now_fn()
    seen_in_flight = False
    polls = 0
    last: dict = {}
    while True:
        last = poll_fn()
        polls += 1
        elapsed = now_fn() - started
        emit(render(last, elapsed))
        stop = ("LANDED_REVIEW", "LANDED_COMMENT") if ignore_notice else (
            "LANDED_REVIEW", "LANDED_COMMENT", "REVIEW_FAILED", "NOTICE")
        if last["verdict"] in stop:
            return {**last, "polls": polls, "elapsed": elapsed,
                    "seen_in_flight": seen_in_flight}
        if last["verdict"] == "IN_FLIGHT":
            seen_in_flight = True
        budget = flight_timeout if seen_in_flight else quiet_timeout
        if elapsed >= budget:
            return {**last, "verdict": "UNRESOLVED", "polls": polls, "elapsed": elapsed,
                    "seen_in_flight": seen_in_flight, "budget": budget}
        sleep_fn(poll_seconds)


# ------------------------------------------------------------------------------ census

def census(repo: str = REPO, runner: Callable[..., Any] = subprocess.run) -> list[dict]:
    """Which arm fires at every pull request's head. The extraction's known-answer proof.

    `DECISIONS.md` states, per pull request, which arm fires — an expectation written down
    before this tool existed and independently of it. Running this and comparing is the
    single known-good row rule 12 asks for before believing a census.
    """
    raw = _gh(["pr", "list", "--repo", repo, "--state", "all",
               "--limit", str(CENSUS_LIMIT), "--json", "number,headRefName"], runner=runner)
    listing = json.loads(raw)
    if len(listing) >= CENSUS_LIMIT:
        raise PrReviewStateError(
            f"gh pr list returned {len(listing)} rows at a --limit of {CENSUS_LIMIT}: the "
            "listing is capped and this census would be reporting the cap, not the "
            "repository. Raise CENSUS_LIMIT.")
    rows = []
    for pr in sorted(listing, key=lambda d: d["number"]):
        n, branch = pr["number"], pr["headRefName"]
        view = fetch_view(n, repo=repo, runner=runner)
        refusal = check_address(n, view, branch)
        if refusal:
            rows.append({"pr": n, "branch": branch, "head": "", "verdict": "REFUSED",
                         "by_review": 0, "by_comment": 0, "in_flight": 0, "failed": 0,
                         "headings": [refusal]})
            continue
        rows.append(poll(n, branch, repo=repo, runner=runner))
    return rows


# ---------------------------------------------------------------------------- selftest

def _review(login: str = BOT, body: str = "x" * 3000, commit: str = "") -> dict:
    return {"user": {"login": login}, "body": body, "commit_id": commit}


def _comment(login: str = BOT, body: str = "") -> dict:
    return {"user": {"login": login}, "body": body}


HEAD_A = "a" * 40
HEAD_B = "b" * 40
PAUSED = ("> [!NOTE]\n> ## Reviews paused\n>\n> It looks like this branch is under active "
          "development.\n")
LIMIT = ("> [!WARNING]\n> ## Review limit reached\n>\n> You've used all 10 included "
         "reviews currently available.\n")
# The state this file's `REVIEW_FAILED` arm exists for, constructed rather than waited for.
# These are the REAL bytes, read from `coderabbitai[bot]` on meshery/meshery#21612 — this
# repository's own instance on PR #39 was rewritten in place and is gone. Note that the body
# writes the NEW head sha into itself, which is why a failed round satisfied the comment arm
# exactly and was indistinguishable from a clean landing (#185).
REAL_HEAD = "ff9816d00a90fffb86e5fd602bf3e37f035084ba"
REAL_FAILED = (
    "<!-- This is an auto-generated comment: failure by coderabbit.ai -->\n"
    "\n"
    "> [!CAUTION]\n"
    "> ## Review failed\n"
    "> \n"
    "> The head commit changed during the review from "
    "b7a7fde482ff94828c2e9253315e381f80808ff7 to "
    f"{REAL_HEAD}.\n"
    "\n"
    "<!-- end of auto-generated comment: failure by coderabbit.ai -->\n")
def _failed_at(new_head: str, old_head: str = HEAD_B) -> str:
    """A failure alert block for a named head, in the real one's shape."""
    return ("> [!CAUTION]\n> ## Review failed\n> \n"
            f"> The head commit changed during the review from {old_head} to "
            f"{new_head}.\n\n")


# The two halves on their own, so each arm of the disjunction has a row only it covers.
FAILED = ("> [!WARNING]\n> ## Review failed\n>\n> The head commit changed during the "
          "review.\n")
FAILED_MARKER_ONLY = ("<!-- This is an auto-generated comment: failure by coderabbit.ai -->\n"
                      "\n> The head commit changed during the review.\n")
SUMMARY_DONE = f"Actionable comments posted: 0\n\n...between base and {HEAD_A}.\n"
SUMMARY_FAILED = FAILED + SUMMARY_DONE
SUMMARY_RUNNING = (f"<!-- This is an {INPROGRESS_MARKER} -->\n"
                   f"Reviewing files that changed from the base of the PR and between "
                   f"{HEAD_B} and {HEAD_A}.\nNo actionable comments were generated.\n")


def selftest() -> int:
    """Table-driven, offline, no network. Rows marked `variant` must PASS."""
    fails: list[str] = []
    ran = [0]
    variants = [0]

    def check(label: str, got: Any, want: Any) -> None:
        ran[0] += 1
        # A row labelled `variant` must PASS on an input the check might mishandle. It is
        # counted here so the figure has a producer rather than a sentence in a docstring.
        variants[0] += "variant" in label
        if got != want:
            fails.append(f"{label}: got {got!r}, want {want!r}")

    def attempt(fn: Callable[[], Any]) -> Any:
        """Run a row's expression, turning a CRASH into a red value.

        A row that dies takes the whole suite with it, and a mutant whose only effect is
        a traceback exits non-zero with no FAIL line — which the mutant harness scores as
        caught while telling nobody what broke. Every field read below goes through here
        so drift reddens one named row.
        """
        try:
            return fn()
        except Exception as exc:  # a crash is a RESULT here, not an abort
            return f"<raised {type(exc).__name__}: {exc}>"

    def raises(label: str, fn: Callable[[], Any]) -> None:
        """The row passes only on a NAMED refusal.

        Any other exception is a red row rather than an abort: a refusal the tool never
        converted reaches the caller as a stray traceback, which is a different defect
        from not refusing at all and must say which.
        """
        ran[0] += 1
        try:
            fn()
        except PrReviewStateError:
            return
        except Exception as exc:
            fails.append(f"{label}: raised {type(exc).__name__} instead of a named refusal")
            return
        fails.append(f"{label}: no refusal was raised")

    def firstword(msg: str | None) -> str:
        return "" if msg is None else msg.split(":")[0]

    view = {"headRefOid": HEAD_A, "headRefName": "task-127-poll"}

    # --- the address. Row A2 is the control this tool was filed for.
    check("A1 right pull request", check_address(9, view, "task-127-poll"), None)
    check("A2 WRONG PR — aimed at another agent's branch",
          firstword(check_address(10, {"headRefOid": HEAD_A,
                                       "headRefName": "task-124-ci-path-filter-and-minutes"},
                                  "task-123-cost-result-producer")), "WRONG PR")
    # Variant A: a branch name that is a PREFIX of the expected one. `in` would pass this.
    check("A3 variant — prefix is not equality",
          firstword(check_address(9, {"headRefOid": HEAD_A, "headRefName": "task-127-poll-x"},
                                  "task-127-poll")), "WRONG PR")
    check("A4 five-character abbreviation",
          firstword(check_address(9, {"headRefOid": "55a09", "headRefName": "task-127-poll"},
                                  "task-127-poll")), "NO HEAD SHA")
    check("A5 empty head",
          firstword(check_address(9, {"headRefOid": "", "headRefName": "task-127-poll"},
                                  "task-127-poll")), "NO HEAD SHA")
    # Variant B: 40 characters that are not a sha. Length alone accepts this.
    check("A6 variant — 40 non-hex characters",
          firstword(check_address(9, {"headRefOid": "Z" * 40, "headRefName": "task-127-poll"},
                                  "task-127-poll")), "NO HEAD SHA")
    check("A7 no headRefName",
          firstword(check_address(9, {"headRefOid": HEAD_A, "headRefName": ""},
                                  "task-127-poll")), "NO BRANCH")
    check("A8 STALE HEAD — the API has not caught up (#165)",
          firstword(check_address(9, view, "task-127-poll", HEAD_B)), "STALE HEAD")
    check("A9 expected head agrees",
          check_address(9, view, "task-127-poll", HEAD_A), None)
    check("A10 expected head abbreviated",
          firstword(check_address(9, view, "task-127-poll", "55a09")),
          "EXPECTED HEAD NOT A FULL SHA")

    # --- the question
    def v(reviews: list[dict], comments: list[dict], head: str = HEAD_A) -> str:
        return classify(head, reviews, comments)["verdict"]

    check("B1 review object with a body at head",
          v([_review(commit=HEAD_A)], []), "LANDED_REVIEW")
    # Variant C: a reply container. GitHub stamps it with the CURRENT head, body empty.
    check("B2 variant — reply container only",
          v([_review(body="", commit=HEAD_A)], []), "NOT_YET")
    check("B3 summary comment naming head, finished",
          v([], [_comment(body=SUMMARY_DONE)]), "LANDED_COMMENT")
    check("B3 counted as 1 finished summary",
          attempt(lambda: classify(HEAD_A, [], [_comment(body=SUMMARY_DONE)])["by_comment"]), 1)
    check("B4 summary comment naming head, still running",
          v([], [_comment(body=SUMMARY_RUNNING)]), "IN_FLIGHT")
    # The running summary must not be COUNTED as a finished one. Verdict order already
    # puts IN_FLIGHT first, so the count is the only place this exclusion can be seen.
    check("B4 not counted as a finished summary",
          attempt(lambda: classify(HEAD_A, [], [_comment(body=SUMMARY_RUNNING)])["by_comment"]), 0)
    # Variant D: the agent's own comment, quoting both the sha and the marker.
    check("B5 variant — a human comment naming the head and the marker",
          v([], [_comment(login="teonimesic",
                          body=f"the marker is {INPROGRESS_MARKER} and the head is {HEAD_A}")]),
          "NOT_YET")
    check("B6 a human review object at head",
          v([_review(login="teonimesic", commit=HEAD_A)], []), "NOT_YET")
    check("B7 a real review of a DIFFERENT commit",
          v([_review(commit=HEAD_B)], []), "NOT_YET")
    check("B8 deadlock notice alone", v([], [_comment(body=PAUSED)]), "NOTICE")
    # Variant E: a stale notice beside a real review. The notice must not win — CodeRabbit
    # edits comments in place and a notice outlives the state it described.
    check("B9 variant — stale notice beside a landed review",
          v([_review(commit=HEAD_A)], [_comment(body=LIMIT)]), "LANDED_REVIEW")
    check("B10 variant — in-flight comment beside a landed review",
          v([_review(commit=HEAD_A)], [_comment(body=SUMMARY_RUNNING)]), "LANDED_REVIEW")
    # Variant F: a round running against a DIFFERENT head, and this head finished.
    check("B11 variant — in-flight names another head",
          v([], [_comment(body=SUMMARY_RUNNING.replace(HEAD_A, "c" * 40)),
                 _comment(body=SUMMARY_DONE)]), "LANDED_COMMENT")
    raises("B12 classify refuses an empty head",
           lambda: classify("", [], [_comment(body="anything at all")]))

    # --- the round that started and DIED. Before this arm, every row here read
    # LANDED_COMMENT at exit 0, which is #185.
    check("B13 a failed round is not a landing",
          v([], [_comment(body=SUMMARY_FAILED)]), "REVIEW_FAILED")
    check("B13 and its exit code is not 0", EXIT["REVIEW_FAILED"] != 0, True)
    check("B13 the summary is still counted, honestly",
          attempt(lambda: classify(HEAD_A, [], [_comment(body=SUMMARY_FAILED)])["by_comment"]), 1)
    check("B13 and the failure is counted beside it",
          attempt(lambda: classify(HEAD_A, [], [_comment(body=SUMMARY_FAILED)])["failed"]), 1)
    # Variant I: the failure and the summary in SEPARATE comments, which is the same state
    # reached by CodeRabbit posting rather than rewriting. A check scoped to one comment
    # body would read this as clean.
    check("B14 variant — the failure sits in its own comment",
          v([], [_comment(body=FAILED), _comment(body=SUMMARY_DONE)]), "REVIEW_FAILED")
    # Variant J: the pause must keep landing. Narrowing the comment arm by "a notice
    # exists" would stop every paused branch resolving — the flag this repairs was added
    # because that case deadlocks.
    check("B15 variant — a paused notice still leaves the comment arm alone",
          v([], [_comment(body=PAUSED), _comment(body=SUMMARY_DONE)]), "LANDED_COMMENT")
    check("B15b variant — a spent allowance likewise",
          v([], [_comment(body=LIMIT), _comment(body=SUMMARY_DONE)]), "LANDED_COMMENT")
    # Variant K: a real review object outranks a stale failure callout. CodeRabbit edits in
    # place, so the callout of a round that later succeeded can still be on the page.
    check("B16 variant — a real review beside a stale failure",
          v([_review(commit=HEAD_A)], [_comment(body=SUMMARY_FAILED)]), "LANDED_REVIEW")
    # Variant L: the replacement round is already running. Keep waiting, do not ask again.
    check("B17 variant — a new round in flight beside the failure",
          v([], [_comment(body=SUMMARY_RUNNING), _comment(body=FAILED)]), "IN_FLIGHT")
    check("B18 a human quoting the failure is not a failure",
          v([], [_comment(login="teonimesic", body=SUMMARY_FAILED)]), "NOT_YET")
    # --- the REAL artifact. The extraction proved on one row whose answer is known in
    # advance: this head was NOT reviewed, because the round reading it died.
    check("B19 the real failure comment, verbatim, at the head it names",
          attempt(lambda: classify(REAL_HEAD, [], [_comment(body=REAL_FAILED)])["verdict"]),
          "REVIEW_FAILED")
    check("B19 and the comment arm WAS satisfied — this is why it read as clean",
          attempt(lambda: classify(REAL_HEAD, [], [_comment(body=REAL_FAILED)])["by_comment"]),
          1)
    # Variant O: a PREVIOUS round's failure beside a clean summary for the head you are
    # asking about. The block says which head it died on, so it is not yours and the
    # landing stands. Reading every failure on the pull request reddens this.
    check("B20 variant — a previous round's failure does not suppress this landing",
          attempt(lambda: classify(HEAD_A, [], [_comment(body=REAL_FAILED),
                                               _comment(body=SUMMARY_DONE)])["verdict"]),
          "LANDED_COMMENT")
    # Variant P: the same 2 artifacts in ONE comment, which is the shape CodeRabbit
    # actually writes. Dating the failure by the comment's last sha rather than by its own
    # block's reddens this.
    check("B21 variant — failure and summary in one comment, failure is the older head",
          attempt(lambda: classify(HEAD_A, [],
                                   [_comment(body=REAL_FAILED + SUMMARY_DONE)])["verdict"]),
          "LANDED_COMMENT")
    # And the case comment-scoping would miss: a CURRENT failure posted on its own, with a
    # clean summary of the same head beside it. Suppressed, because the block names it.
    check("B22 a current failure in its own comment still suppresses",
          attempt(lambda: classify(REAL_HEAD, [],
                                   [_comment(body=REAL_FAILED),
                                    _comment(body=f"...between base and {REAL_HEAD}.\n")]
                                   )["verdict"]),
          "REVIEW_FAILED")
    # Variant Q: a failure block naming no sha cannot be dated, so it counts. Fail-closed
    # where the evidence is missing, and the direction rule 7 asks for.
    check("B23 variant — an undatable failure still suppresses",
          v([], [_comment(body=FAILED), _comment(body=SUMMARY_DONE)]), "REVIEW_FAILED")

    check("C5 the marker alone is a failed round",
          len(failed_rounds([_comment(body=FAILED_MARKER_ONLY)])), 1)
    check("C6 the heading alone is a failed round",
          len(failed_rounds([_comment(body=FAILED)])), 1)
    check("C7 a pause is neither", failed_rounds([_comment(body=PAUSED)]), [])
    check("C8 a clean summary is neither", failed_rounds([_comment(body=SUMMARY_DONE)]), [])
    # Variant R: 2 failure blocks in one comment, the FIRST about this head. Flattening
    # the blocks and reading one sha lets the second overrule the first.
    check("B24 variant — a head-matching block followed by another head's",
          attempt(lambda: classify(HEAD_A, [],
                                   [_comment(body=_failed_at(HEAD_A) + REAL_FAILED)]
                                   )["verdict"]),
          "REVIEW_FAILED")
    check("B25 two blocks, neither about this head",
          attempt(lambda: classify(HEAD_A, [],
                                   [_comment(body=_failed_at("c" * 40) + REAL_FAILED),
                                    _comment(body=SUMMARY_DONE)])["verdict"]),
          "LANDED_COMMENT")
    check("C11 the real block is dated to the head it died on",
          len(failed_rounds([_comment(body=REAL_FAILED)], REAL_HEAD)), 1)
    check("C12 and not to any other head",
          failed_rounds([_comment(body=REAL_FAILED)], HEAD_A), [])
    # Variant M: the reason moved into the heading. It is in the body today, and the poll
    # must not go quietly fail-open if CodeRabbit appends it.
    check("C9 variant — the reason appended to the heading",
          len(failed_rounds([_comment(
              body="> [!CAUTION]\n> ## Review failed — the head commit changed\n")])), 1)
    check("C10 a heading merely containing the words is not a failure",
          failed_rounds([_comment(body="> [!NOTE]\n> ## Why your review failed to post\n")]),
          [])

    check("C1 pause heading", alert_headings([_comment(body=PAUSED)]), ["Reviews paused"])
    check("C2 limit heading", alert_headings([_comment(body=LIMIT)]), ["Review limit reached"])
    check("C3 no callout", alert_headings([_comment(body=SUMMARY_DONE)]), [])
    check("C4 a human's callout", alert_headings([_comment(login="teonimesic", body=PAUSED)]), [])

    # --- pagination. gh 2.98 merges pages; older versions concatenate.
    check("D1 one merged array", [r["id"] for r in parse_pages('[{"id":1},{"id":2}]')], [1, 2])
    check("D2 concatenated arrays",
          [r["id"] for r in parse_pages('[{"id":1}]\n[{"id":2}]')], [1, 2])

    # --- gh failure is not a poll result, and neither is gh not returning at all
    def failing(_args, **_kw):
        return subprocess.CompletedProcess(_args, 1, "", "HTTP 502")
    raises("E1 a non-zero gh exit is not a poll result",
           lambda: _gh(["api", "x"], runner=failing))

    def hanging(_args, **_kw):
        raise subprocess.TimeoutExpired(cmd="gh", timeout=_kw.get("timeout", 0))
    raises("E1b a gh that never returns is not a poll result",
           lambda: _gh(["api", "x"], runner=hanging))

    seen_kw: dict = {}

    def recording(argv, **kw):
        seen_kw.update(kw)
        return subprocess.CompletedProcess(argv, 0, "[]", "")
    _gh(["api", "x"], runner=recording)
    # Handling a timeout is not the same as ASKING for one: without this row the
    # conversion above is unreachable and every gh call still blocks forever.
    check("E1c every gh call carries a finite timeout",
          isinstance(seen_kw.get("timeout"), (int, float)) and seen_kw["timeout"] > 0, True)

    # --- the wait. The timeline is task 130's, measured from the GitHub API.
    def timeline(events: list[tuple[float, str]]) -> tuple[Any, Any, Any]:
        clock = [0.0]

        def now() -> float:
            return clock[0]

        def sleep(sec: float) -> None:
            clock[0] += sec

        def poll_fn() -> dict:
            verdict = "NOT_YET"
            for at, val in events:
                if clock[0] >= at:
                    verdict = val
            return {"pr": 15, "branch": "task-130", "head": HEAD_A, "verdict": verdict,
                    "by_review": 0, "by_comment": 0, "in_flight": 0, "failed": 0,
                    "headings": []}
        return poll_fn, now, sleep

    def run_wait(events, **kw):
        poll_fn, now, sleep = timeline(events)
        return wait_for(poll_fn, now_fn=now, sleep_fn=sleep, emit=lambda _s: None, **kw)

    # F1: 19m26s, in flight throughout — the exact case a 15-minute clock got wrong.
    out = run_wait([(60, "IN_FLIGHT"), (1166, "LANDED_REVIEW")])
    check("F1 review at 19m26s while in flight", out["verdict"], "LANDED_REVIEW")
    check("F1 elapsed", int(out["elapsed"]), 1170)
    # F1b: the SAME timeline under the retired 15-minute clock. The red half of the
    # bound change: the number that was shipped returns UNRESOLVED on a review that landed.
    out = run_wait([(60, "IN_FLIGHT"), (1166, "LANDED_REVIEW")],
                   quiet_timeout=900, flight_timeout=900)
    check("F1b the retired 15-minute clock misses it", out["verdict"], "UNRESOLVED")
    # F1c: a slower diff. 40 minutes, in flight throughout. The quiet bound alone cannot
    # reach this; only the latch to the flight bound can.
    out = run_wait([(60, "IN_FLIGHT"), (2400, "LANDED_REVIEW")])
    check("F1c review at 40m while in flight", out["verdict"], "LANDED_REVIEW")
    # Variant G: the marker vanishes mid-round. The latch is what carries the wait past
    # the quiet bound.
    out = run_wait([(60, "IN_FLIGHT"), (150, "NOT_YET"), (2400, "LANDED_COMMENT")])
    check("F2 variant — marker disappears mid-round", out["verdict"], "LANDED_COMMENT")
    # F3: nothing ever starts. Quiet bound, loud outcome.
    out = run_wait([])
    check("F3 silent throughout", out["verdict"], "UNRESOLVED")
    check("F3 gave up at the quiet bound", int(out["elapsed"]), QUIET_TIMEOUT)
    check("F3 never saw a round", out["seen_in_flight"], False)
    # F4: in flight and never lands. The longer bound, still loud.
    out = run_wait([(60, "IN_FLIGHT")])
    check("F4 in flight forever", out["verdict"], "UNRESOLVED")
    check("F4 gave up at the flight bound", int(out["elapsed"]), FLIGHT_TIMEOUT)
    # F5: a notice returns at once — the agent has something to do.
    out = run_wait([(60, "NOTICE")])
    check("F5 notice stops the wait", out["verdict"], "NOTICE")
    check("F5 stopped at once", int(out["elapsed"]), 60)
    # F6: the SAME timeline once the notice has been acted on. The notice comment outlives
    # the pause it described, so without this the wait stops instantly, for ever.
    out = run_wait([(60, "NOTICE"), (900, "LANDED_REVIEW")], ignore_notice=True)
    check("F6 an answered notice does not stop the wait", out["verdict"], "LANDED_REVIEW")
    # Variant H: --ignore-notice must not become "wait for ever". A pause that is never
    # answered still expires, loudly, on the quiet bound.
    out = run_wait([(60, "NOTICE")], ignore_notice=True)
    check("F7 variant — an ignored notice still expires loudly", out["verdict"], "UNRESOLVED")
    check("F7 on the quiet bound", int(out["elapsed"]), QUIET_TIMEOUT)
    # F8: the failed round stops the wait, so the agent finds out and can ask again. This
    # is the wait-level half of #185 — before it, the same timeline returned at 60s calling
    # itself LANDED_COMMENT.
    out = run_wait([(60, "REVIEW_FAILED"), (600, "LANDED_REVIEW")])
    check("F8 a failed round stops the wait", out["verdict"], "REVIEW_FAILED")
    check("F8 at the poll that saw it", int(out["elapsed"]), 60)
    # F9: the poll started AFTER `@coderabbitai review`. The callout is still on the page
    # until CodeRabbit rewrites the summary, so the flag has to carry the wait past it —
    # and the review that lands 540s later is what the wait returns.
    out = run_wait([(60, "REVIEW_FAILED"), (600, "LANDED_REVIEW")], ignore_notice=True)
    check("F9 the answered failure does not stop the wait", out["verdict"], "LANDED_REVIEW")
    check("F9 and it waited for the real review", int(out["elapsed"]), 600)
    # Variant N: the flag must not become "wait for ever" here either, and it must never
    # convert the failure into a landing. Silence expires loudly instead.
    out = run_wait([(60, "REVIEW_FAILED")], ignore_notice=True)
    check("F10 variant — an ignored failure still expires loudly",
          out["verdict"], "UNRESOLVED")
    check("F10 on the quiet bound", int(out["elapsed"]), QUIET_TIMEOUT)

    # --- the poll line reaches the reader while the wait is still running
    class Recorder:
        def __init__(self) -> None:
            self.wrote: list[str] = []
            self.flushed = 0

        def write(self, text: str) -> int:
            self.wrote.append(text)
            return len(text)

        def flush(self) -> None:
            self.flushed += 1

    rec = Recorder()
    with contextlib.redirect_stdout(rec):  # type: ignore[arg-type]
        _emit("#18 task-127 head=x verdict=NOT_YET")
    check("E2 the poll line is written", "".join(rec.wrote).strip(),
          "#18 task-127 head=x verdict=NOT_YET")
    check("E3 and flushed, so a captured --wait is not silent", rec.flushed >= 1, True)
    check("E4 wait_for emits through it by default",
          wait_for.__kwdefaults__["emit"], _emit)

    # --- the census, and its refusal when the two API reads disagree about the branch
    def fake_gh(branch_from_view: str):
        def runner(argv, **_kw):
            args = argv[1:]
            if args[:2] == ["pr", "list"]:
                body = json.dumps([{"number": 7, "headRefName": "task-121-x"}])
            elif args[:2] == ["pr", "view"]:
                body = json.dumps({"headRefOid": HEAD_A, "headRefName": branch_from_view})
            elif args[-1].endswith("/reviews"):
                body = json.dumps([_review(commit=HEAD_A)])
            else:
                body = json.dumps([])
            return subprocess.CompletedProcess(argv, 0, body, "")
        return runner

    def capped_gh(argv, **_kw):
        args = argv[1:]
        if args[:2] == ["pr", "list"]:
            limit = int(args[args.index("--limit") + 1])
            body = json.dumps([{"number": n, "headRefName": f"b{n}"}
                               for n in range(1, limit + 1)])
        else:
            body = json.dumps([])
        return subprocess.CompletedProcess(argv, 0, body, "")

    # `gh pr list` honours --limit silently, so a full page means TRUNCATED, not complete.
    raises("H0 a census that hits its own listing cap refuses",
           lambda: census(runner=capped_gh))

    rows = census(runner=fake_gh("task-121-x"))
    check("H1 census reads the arm", [r["verdict"] for r in rows], ["LANDED_REVIEW"])
    check("H1 census names the branch", rows[0]["branch"], "task-121-x")
    try:
        rows = census(runner=fake_gh("task-999-someone-else"))
        check("H2 census refuses when the two reads disagree",
              [r["verdict"] for r in rows], ["REFUSED"])
    except PrReviewStateError as exc:
        ran[0] += 1
        fails.append(f"H2 census raised instead of reporting a REFUSED row: {exc}")

    # --- the CLI forwards the flag it parses. Every `wait_for` row above calls the
    # function DIRECTLY, so replacing `ignore_notice=args.ignore_notice` with a constant
    # leaves all of them green while the flag does nothing.
    real_wait = wait_for
    forwarded: list = []

    def fake_wait(_poll_fn, **kw):
        forwarded.append(kw.get("ignore_notice"))
        return {"pr": 18, "branch": "b", "head": HEAD_A, "verdict": "LANDED_COMMENT",
                "by_review": 0, "by_comment": 1, "in_flight": 0, "failed": 0,
                "headings": [], "polls": 1, "elapsed": 0.0, "seen_in_flight": False}

    globals()["wait_for"] = fake_wait
    try:
        main(["--pr", "18", "--branch", "b", "--wait"])
        main(["--pr", "18", "--branch", "b", "--wait", "--ignore-notice"])
    finally:
        globals()["wait_for"] = real_wait
    check("I1 the CLI forwards --ignore-notice, both ways", forwarded, [False, True])

    # --- the drift guard: a field the rows above read, by name.
    r = classify(HEAD_A, [_review(commit=HEAD_A)], [])
    for field in ("verdict", "by_review", "by_comment", "in_flight", "failed", "headings"):
        check(f"G1 classify still returns {field!r}", field in r, True)
    line = attempt(lambda: render({**r, "pr": 18, "branch": "task-127-poll", "head": HEAD_A}))
    for token in ("#18", "task-127-poll", HEAD_A, "failed="):
        check(f"G2 render still names {token!r}", token in str(line), True)

    for f in fails:
        print(f"FAIL {f}")
    # The count is what ran, never a constant beside it: a suite that reports a number it
    # did not derive is the shape this repository exists to distrust.
    print(f"{'ok' if not fails else 'FAILED'} ({len(fails)} failures, {ran[0]} checks, "
          f"{variants[0]} of them variants)")
    return 1 if fails else 0


# --------------------------------------------------------------------------------- cli

def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--pr", type=int, help="the pull request number")
    ap.add_argument("--branch", help="the branch you believe it is on. Asserted, not assumed")
    ap.add_argument("--expect-head", help="the full 40-hex sha you pushed. Refuses to poll "
                                          "until the API agrees")
    ap.add_argument("--repo", default=REPO)
    ap.add_argument("--wait", action="store_true", help="poll until the round resolves")
    ap.add_argument("--poll-seconds", type=int, default=POLL_SECONDS)
    ap.add_argument("--quiet-timeout", type=int, default=QUIET_TIMEOUT,
                    help="seconds of never having seen a round in flight")
    ap.add_argument("--flight-timeout", type=int, default=FLIGHT_TIMEOUT,
                    help="seconds once a round HAS been seen in flight")
    # THE AMBIGUOUS CASE IS DECIDED HERE, beside the flag that used to swallow it.
    #
    # No notice, a summary comment naming the head, no review object: that is
    # `LANDED_COMMENT`, and it is a real landing. It has to be. When CodeRabbit finds
    # nothing actionable it creates NO review object at all, and `DECISIONS.md` counted 3
    # of 6 reviewed heads reaching only that arm — requiring a review object would spend
    # the full bound on the common good outcome.
    #
    # So the comment arm keeps its authority and is narrowed by EXCLUSION, one observed
    # mechanism at a time: a comment at the head is not a landing while the in-progress
    # marker is on it (the round is running), and not a landing while a `Review failed`
    # callout is on the pull request (the round died). When a third way is found for a
    # comment to sit at a head nobody reviewed, the answer is a third exclusion — not
    # discarding the arm, and not a flag that hides it.
    ap.add_argument("--ignore-notice", action="store_true",
                    help="do not stop --wait on a deadlock notice or a failed round. Use it "
                         "for the poll you start after acting on one: the comment outlives "
                         "the state it described, so it would stop every wait instantly. It "
                         "governs stopping only — it can never turn either into a landing")
    ap.add_argument("--census", action="store_true",
                    help="every pull request, and which arm fires at its head")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)

    if args.selftest:
        return selftest()

    try:
        if args.census:
            for row in census(repo=args.repo):
                print(render(row))
            return 0

        if args.pr is None or not args.branch:
            ap.error("--pr and --branch are both required. The branch is the address this "
                     "tool exists to assert; there is no default for it")

        if args.wait:
            out = wait_for(
                lambda: poll(args.pr, args.branch, args.expect_head, repo=args.repo),
                poll_seconds=args.poll_seconds, quiet_timeout=args.quiet_timeout,
                flight_timeout=args.flight_timeout, ignore_notice=args.ignore_notice)
            if out["verdict"] == "REVIEW_FAILED":
                print(f"REVIEW_FAILED: #{args.pr} {args.branch} head={out['head']} — a "
                      "round started and died, and the summary it left at this head is not "
                      "a review. Post `@coderabbitai review`, then poll again with "
                      "--ignore-notice so the callout it has not rewritten yet cannot stop "
                      "you. Do not request a second review because the same callout is "
                      "still there.")
            if out["verdict"] == "UNRESOLVED":
                print(f"UNRESOLVED: #{args.pr} {args.branch} head={out['head']} — "
                      f"{out['polls']} polls over {int(out['elapsed'])}s, budget "
                      f"{out['budget']}s, seen_in_flight={out['seen_in_flight']}. "
                      "Say so in the pull request thread, set the ticket to in_testing "
                      "with this fact as the evidence, and hand it back.")
            return EXIT[out["verdict"]]

        result = poll(args.pr, args.branch, args.expect_head, repo=args.repo)
        print(render(result))
        return EXIT[result["verdict"]]
    except PrReviewStateError as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
