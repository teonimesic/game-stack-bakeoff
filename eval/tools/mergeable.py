#!/usr/bin/env python3
"""Is this pull request safe to merge? Green is not the question that failed.

    python3 eval/tools/mergeable.py <pr>      # exit 0 = merge it, 1 = do not
    python3 eval/tools/mergeable.py --selftest

On 2026-08-23 main went red on the merge of pull request #13 while #12 and #13 were
**both green**. Both were tested at 23:00 against a main containing neither. #12 added
three comments to `cost_census.py` spelling token valuations with a `$`; #13 added the
gate forbidding exactly that in a producer. Neither run could see the other's change,
and the head each pull request would actually produce was never built.

So a merge gate that asks only *are the checks green* would have passed both, and did.
The gate has to ask two things:

  1. **Are the required checks green at the pull request's CURRENT head?** A green run
     against an earlier push is a statement about a commit nobody is merging.
  2. **Is the branch up to date with the base?** This is the one that catches the
     semantic conflict above - two changes that are individually correct and jointly
     red. GitHub calls it `strict` required status checks and gates it behind a paid
     plan for private repositories, so on this repository it is enforced here instead.

It also **reports** a third thing without gating on it: what the non-required rows of the
rollup say, and which head the reviewer last wrote at. `CodeRabbit` arrives as a
`StatusContext`, whose verdict is `state` and whose `description` the rollup drops
entirely - so a row reading `pass ... Review rate limited` in `gh pr checks` reached this
tool as a row with no conclusion at all, and was printed in no line of its output. Why
that half is reported rather than gated, and why the description is quoted rather than
matched on, is in `DECISIONS.md`, *A review is reported against the head it was written
at, and never gated*.

`--selftest` drives both directions off recorded API payloads, including the #12/#13
shape itself, because a gate that has only ever seen a mergeable pull request is a gate
whose failing branch has never run.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys

#: The check runs that must be green. A name not in this set is reported and ignored -
#: a new workflow should be a deliberate addition here, never a silent requirement.
REQUIRED = ("gates", "controls")

#: `mergeable_state` values that mean the branch is behind its base. GitHub returns
#: `behind` only when the repository requires up-to-date branches; without that setting
#: it returns `clean` for a stale branch, which is why `--selftest` pins the commit
#: comparison as the real test and treats this as corroboration only.
BEHIND_STATES = ("behind", "dirty")

#: `mergeStateStatus` values where GITHUB refuses the merge, whatever this tool thinks.
#: The named checks above enumerate the reasons this tool knows about; that enumeration
#: has already been incomplete once, so this is the PROPERTY that catches the rest. On
#: 2026-08-27 PR #42 had both required checks green at its own head and 0 commits of
#: drift, and every named check here passed - while GitHub refused it for two unresolved
#: review threads, because `main` sets `required_conversation_resolution`. A gate that
#: reports `mergeable` on a pull request the host will not merge is the shape this
#: repository logs as "a mechanism that runs, reports success, and measures nothing".
REFUSING_STATES = ("blocked", "behind", "dirty", "draft", "unstable")

#: The App that reviews here, by the login the API returns. **The `[bot]` suffix is part
#: of the login.** A filter written as `coderabbitai` selects nothing from any pull
#: request's reviews, and `AGENTS.md` rule 12 records that exact miss returning a
#: confident "no review exists" about a review that was sitting there.
REVIEWER = "coderabbitai[bot]"

#: The commit-status context the same App posts under. It is deliberately NOT `REVIEWER`:
#: the status carries the human-facing name, the review object carries the login, and
#: reading either one for the other is the rule-12 shape above.
REVIEWER_CONTEXT = "CodeRabbit"


def _gh(args: list[str]) -> str:
    """Run `gh` and return stdout. Raises on non-zero: never `|| echo 0` a measurement."""
    return subprocess.run(["gh", *args], check=True, capture_output=True,
                          text=True).stdout


def pr_facts(pr: str) -> dict:
    """The pull request's head, base, check runs and merge state, read from the API."""
    raw = _gh(["pr", "view", pr, "--json",
               "number,headRefName,headRefOid,baseRefName,mergeable,mergeStateStatus,"
               "statusCheckRollup,state,title"])
    return json.loads(raw)


def base_head(base: str) -> str:
    """The base branch's current head on the remote, not in the local checkout."""
    return _gh(["api", f"repos/{{owner}}/{{repo}}/commits/{base}",
                "--jq", ".sha"]).strip()


def behind_by(base: str, head: str) -> int:
    """How many commits the base is ahead of this head. 0 means up to date."""
    raw = _gh(["api", f"repos/{{owner}}/{{repo}}/compare/{head}...{base}",
               "--jq", ".ahead_by"]).strip()
    return int(raw)


def check_problems(facts: dict) -> list[str]:
    """Every reason the checks do not clear this pull request's current head.

    Two distinct failures, kept distinct: a required check that is red, and a required
    check that ran against some **other** commit. The second is invisible to any gate
    that reads a conclusion without reading the sha it belongs to.
    """
    problems: list[str] = []
    head = facts["headRefOid"]
    rollup = facts.get("statusCheckRollup") or []
    seen: dict[str, dict] = {}
    for run in rollup:
        name = run.get("name") or run.get("context") or "?"
        if name in REQUIRED:
            seen[name] = run

    for name in REQUIRED:
        run = seen.get(name)
        if run is None:
            problems.append(f"required check {name!r} has no run at head {head[:8]}")
            continue
        status = run.get("status")
        conclusion = (run.get("conclusion") or "").upper()
        if status and status.upper() != "COMPLETED":
            problems.append(f"required check {name!r} is {status.lower()}, not finished")
        elif conclusion != "SUCCESS":
            problems.append(f"required check {name!r} concluded "
                            f"{conclusion.lower() or 'nothing'}, not success")
    return problems


def staleness_problems(facts: dict, ahead: int) -> list[str]:
    """Is the branch behind its base? The #12/#13 failure, and it reads as green."""
    problems: list[str] = []
    if ahead > 0:
        base = facts["baseRefName"]
        problems.append(
            f"branch is {ahead} commit(s) behind {base}: the checks passed against a "
            f"head nobody is merging. Update the branch and let CI re-run.")
    state = (facts.get("mergeStateStatus") or "").lower()
    if state in BEHIND_STATES and ahead == 0:
        problems.append(f"mergeStateStatus is {state!r} with no commit gap - "
                        f"conflict or a stale API read; resolve before merging")
    if facts.get("mergeable") == "CONFLICTING":
        problems.append("pull request conflicts with its base; a conflicted pull "
                        "request gets no CI run at all")
    return problems


def unresolved_threads(pr: str) -> list[dict] | None:
    """Unresolved review threads, or `None` if the query could not be run.

    `gh pr view --json` has no field for these, so the REST rollup this tool reads
    cannot see them at all - which is exactly how they went unnoticed. `None` is a
    THIRD value and never an empty list: "nobody could ask" must not read as "no
    unresolved threads", which is the fail-open direction (rule 7).
    """
    q = ("query($o:String!,$r:String!,$n:Int!){repository(owner:$o,name:$r)"
         "{pullRequest(number:$n){reviewThreads(first:100){nodes{isResolved path "
         "comments(first:1){nodes{author{login}}}}}}}}")
    try:
        slug = json.loads(_gh(["repo", "view", "--json", "nameWithOwner"]))
        owner, repo = slug["nameWithOwner"].split("/", 1)
        raw = _gh(["api", "graphql", "-f", f"query={q}", "-F", f"o={owner}",
                   "-F", f"r={repo}", "-F", f"n={int(pr)}"])
        nodes = json.loads(raw)["data"]["repository"]["pullRequest"][
            "reviewThreads"]["nodes"]
    except Exception:
        return None
    out = []
    for t in nodes:
        if t.get("isResolved"):
            continue
        c = (t.get("comments") or {}).get("nodes") or [{}]
        out.append({"path": t.get("path") or "?",
                    "author": ((c[0] or {}).get("author") or {}).get("login") or "?"})
    return out


def conversation_problems(threads: list[dict] | None) -> list[str]:
    """`main` requires conversation resolution, so an open thread blocks the merge."""
    if threads is None:
        return ["could not read review threads: this tool cannot tell whether an "
                "unresolved conversation is blocking. Not the same as zero."]
    if not threads:
        return []
    where = ", ".join(sorted({f"{t['path']} ({t['author']})" for t in threads})[:4])
    return [f"{len(threads)} unresolved review thread(s): {where}. `main` sets "
            f"required_conversation_resolution, so these block the merge even with "
            f"every check green. Read them and reply - resolving one you did not act "
            f"on is tidying feedback away."]


def agreement_problems(facts: dict, problems: list[str]) -> list[str]:
    """Does this tool's verdict AGREE with the host's? A disagreement is OUR bug.

    An expectation is a SECOND, independent statement of a fact, and this is the only
    row here that compares the two rather than sharing an address with them.
    """
    state = (facts.get("mergeStateStatus") or "").lower()
    if problems or state not in REFUSING_STATES:
        return []
    return [f"every check in this tool passes and GitHub still reports "
            f"mergeStateStatus={state!r}. The tool's list of blockers is INCOMPLETE - "
            f"do not merge on its say-so; read the pull request and then fix this tool."]


def head_statuses(head: str) -> dict[str, dict] | None:
    """Every commit status at ONE sha, keyed by context, or `None` if unreadable.

    `gh pr view --json statusCheckRollup` returns a `StatusContext` carrying `context`,
    `state` and `targetUrl` and **no `description`**. That missing field is the whole
    defect: on 2026-08-27 PR #60's row read `SUCCESS` in the rollup this tool consumes
    and `pass ... Review rate limited` in `gh pr checks`, the view a human reads. The
    words saying no review happened exist only on the status object.

    The address is the **combined** status endpoint, `/commits/<sha>/status`, not
    `/commits/<sha>/statuses`: the combined one returns one row per context, already the
    latest, so nothing here depends on the order a list came back in. `<sha>` is the head
    this tool has already read, passed in - never "the pull request's current head"
    resolved a second time (rule 12).

    `None` is a THIRD value and never an empty dict: "the descriptions could not be read"
    must not read as "there is no description", which is the fail-open direction (rule 7).
    """
    try:
        raw = _gh(["api", f"repos/{{owner}}/{{repo}}/commits/{head}/status"])
        statuses = json.loads(raw).get("statuses") or []
    except Exception:
        return None
    return {s.get("context") or "?": s for s in statuses}


def rollup_rows(facts: dict, statuses: dict[str, dict] | None) -> list[dict]:
    """Every rollup row in one shape, required or not, with the description folded back.

    Two shapes arrive in one list and they do not share a vocabulary. A `CheckRun` has
    `status` and `conclusion`; a `StatusContext` has **neither** - its verdict is `state`.
    Reading `conclusion or status` therefore returns nothing at all for the second shape,
    which is why the `CodeRabbit` row was absent from this tool's output rather than
    merely unexplained.
    """
    rows: list[dict] = []
    for run in facts.get("statusCheckRollup") or []:
        name = run.get("name") or run.get("context") or "?"
        kind = run.get("__typename") or ("CheckRun" if "conclusion" in run
                                         or "status" in run else "StatusContext")
        verdict = (run.get("conclusion") or run.get("state") or "").upper() or None
        desc = (statuses or {}).get(name, {}).get("description") or None
        rows.append({"name": name, "kind": kind, "required": name in REQUIRED,
                     "verdict": verdict, "status": (run.get("status") or "").upper() or None,
                     "description": desc, "descriptions_readable": statuses is not None})
    return rows


def unconcluded_note(row: dict) -> str:
    """The line for a row the rollup gives no verdict at all.

    Its own function so that removing it is a mutation with a visible effect rather than
    a crash: a mutant that only raises says nothing about which check it defeated.
    """
    return (f"non-required check {row['name']!r} reports no conclusion and no state in "
            f"the rollup"
            + (f" (status {row['status'].lower()})" if row["status"] else "")
            + ": this tool cannot say whether it ran. An absent verdict is not a pass")


def unrequired_notes(rows: list[dict]) -> list[str]:
    """What the rollup's NON-required rows say - including that one says nothing.

    A row this tool does not gate on is still evidence, and the row that mattered was
    invisible: `check_problems` skips every name outside `REQUIRED`, and `report` printed
    only `REQUIRED`, so `CodeRabbit` appeared in no line of the output. An unprinted row
    is not a neutral one when the orchestrator is using this output to decide whether a
    branch has been reviewed.
    """
    notes: list[str] = []
    for row in rows:
        if row["required"]:
            continue
        name = row["name"]
        if row["verdict"] is None:
            notes.append(unconcluded_note(row))
        elif row["description"]:
            notes.append(f"non-required check {name!r}: {row['verdict'].lower()} - "
                         f"{row['description']!r}")
        elif row["descriptions_readable"]:
            notes.append(f"non-required check {name!r}: {row['verdict'].lower()}, with no "
                         f"description posted at this head")
        else:
            notes.append(f"non-required check {name!r}: {row['verdict'].lower()}; the "
                         f"commit statuses at this head could not be read, so the "
                         f"description - the only field separating a review from a rate "
                         f"limit - is unknown")
    return notes


def reviewer_reviews_from(payload: list[dict]) -> list[dict]:
    """`REVIEWER`'s SUBMITTED reviews out of a raw `/pulls/<n>/reviews` payload, oldest
    first.

    Sorted here rather than trusted: the endpoint's order is not part of its contract,
    and "the last review" is the one fact this tool reads out of the list. A review with
    no `submitted_at` has not been submitted and is dropped, which can only make a head
    look less reviewed than it is - the fail-closed direction. The sort key tolerates a
    missing timestamp rather than raising on one, so that dropping the filter produces a
    WRONG ANSWER the selftest can catch instead of a crash it cannot distinguish.
    """
    mine = [r for r in payload
            if ((r.get("user") or {}).get("login") or "") == REVIEWER
            and r.get("submitted_at")]
    return sorted(mine, key=lambda r: (r.get("submitted_at") or "", r.get("id") or 0))


def reviewer_reviews(pr: str) -> list[dict] | None:
    """`REVIEWER`'s reviews on this pull request, or `None` if they could not be read."""
    try:
        raw = _gh(["api", "--paginate", f"repos/{{owner}}/{{repo}}/pulls/{pr}/reviews"])
        return reviewer_reviews_from(json.loads(raw))
    except Exception:
        return None


def branch_commits(pr: str) -> list[dict] | None:
    """`{sha, subject}` for every commit on the pull request, oldest first, or `None`."""
    try:
        raw = _gh(["api", "--paginate", f"repos/{{owner}}/{{repo}}/pulls/{pr}/commits"])
        return [{"sha": c["sha"],
                 "subject": ((c.get("commit") or {}).get("message") or "").split("\n")[0]}
                for c in json.loads(raw)]
    except Exception:
        return None


def review_notes(facts: dict, reviews: list[dict] | None,
                 commits: list[dict] | None, rows: list[dict]) -> list[str]:
    """Which head `REVIEWER` last WROTE at, against the head that is about to be merged.

    A commit status is posted when a round is attempted; a review object is written when
    a round has something to say. **Neither alone answers "was this head read", and the
    two disagree in both directions** - measured 2026-08-27 on two pull requests:

    | | status at head | review object at head | actually |
    |---|---|---|---|
    | PR #60 | `success` `Review rate limited` | none, last 2 commits back | no round ran |
    | PR #62 | `success` `Review completed` | none, last 1 commit back | `pr_review_state.py` says `NOTICE / Reviews paused` |

    PR #62 is why the description is REPORTED AND NEVER PARSED. Its wording says the round
    finished, at a head where none did; a set of strings meaning "no review happened" is
    an open class, and this project's rule audit records what an open-class trigger costs.

    And the sha comparison alone is not the verdict either, in the other direction: a
    clean incremental round writes no review object, so a head with none may have been
    read and found sound. What is stated here is the fact - *nothing was written about
    this head* - with `pr_review_state.py` named as the producer of the verdict.
    """
    head = facts["headRefOid"]
    verdict_cmd = (f"python3 eval/tools/pr_review_state.py --pr {facts['number']} "
                   f"--branch {facts['headRefName']} --expect-head {head}")
    if reviews is None:
        return [f"the review timeline could not be read, so this tool cannot say which "
                f"head {REVIEWER} last wrote at. That is neither 'unreviewed' nor "
                f"'reviewed'"]
    if not reviews:
        notes = [f"{REVIEWER} has written no review on this pull request at any head"]
    else:
        at = reviews[-1].get("commit_id") or ""
        if at == head:
            return [f"{REVIEWER} wrote a review at {at[:8]}, which IS the current head"]
        if commits is None:
            notes = [f"{REVIEWER} last wrote at {at[:8]} and the head is {head[:8]}: NOT "
                     f"the same commit. The commit list could not be read, so the size "
                     f"of the gap is unknown"]
        else:
            shas = [c["sha"] for c in commits]
            if at not in shas:
                notes = [f"{REVIEWER} last wrote at {at[:8]}, which is not on the branch "
                         f"at all - a force-push or rebase since. Nothing has been "
                         f"written about the head {head[:8]}"]
            else:
                after = commits[shas.index(at) + 1:]
                listed = "; ".join(f"{c['sha'][:8]} {c['subject'][:58]}" for c in after)
                notes = [f"{REVIEWER} last wrote at {at[:8]}; the head {head[:8]} is "
                         f"{len(after)} commit(s) later and carries no review of its own"
                         + (f": {listed}" if listed else
                            " - and the commit list does not end at the head, so this "
                            "reading is inconsistent; check the pull request by hand")]

    row = next((r for r in rows if r["name"] == REVIEWER_CONTEXT), None)
    if row and row["verdict"]:
        desc = f" - {row['description']!r}" if row["description"] else ""
        notes.append(f"...and the {REVIEWER_CONTEXT!r} commit status at that head reads "
                     f"{row['verdict'].lower()}{desc}. A status is posted when a round is "
                     f"ATTEMPTED, and on 2026-08-27 one read 'Review completed' at a head "
                     f"no round finished on")
    notes.append(f"a clean round writes no review object, so 'no review of its own' is "
                 f"not proof the head went unread. For the verdict run: {verdict_cmd}")
    return notes


def report(pr: str) -> int:
    facts = pr_facts(pr)
    if facts.get("state") != "OPEN":
        print(f"PR #{facts['number']} is {facts['state']}, not open")
        return 1
    head = facts["headRefOid"]
    ahead = behind_by(facts["baseRefName"], head)
    threads = unresolved_threads(pr)
    rows = rollup_rows(facts, head_statuses(head))
    problems = (check_problems(facts) + staleness_problems(facts, ahead)
                + conversation_problems(threads))
    problems += agreement_problems(facts, problems)

    print(f"PR #{facts['number']}  {facts['title'][:64]}")
    print(f"  head {head[:8]} on {facts['headRefName']} "
          f"-> {facts['baseRefName']} (behind by {ahead})")
    for row in rows:
        tag = "required" if row["required"] else "not required"
        desc = f"  {row['description']!r}" if row["description"] else ""
        # A run with no conclusion still has a status, and dropping it would lose the
        # difference between "still running" and "finished and said nothing".
        run_state = (f" status={row['status'].lower()}"
                     if row["verdict"] is None and row["status"] else "")
        print(f"  {row['name']:12s} {row['verdict'] or 'NO CONCLUSION':14s} "
              f"({tag}){run_state}{desc}")
    for name in REQUIRED:
        if name not in {r["name"] for r in rows}:
            print(f"  {name:12s} {'ABSENT':14s} (required)")

    # Reported, never gated. `DECISIONS.md`, "A review is reported against the head it
    # was made at, and never gated", records why - the merge procedure itself makes the
    # final head unreviewed, so refusing on it would fire where nothing is wrong.
    print("\nREVIEW STATE (reported, not gated):")
    for note in unrequired_notes(rows) + review_notes(
            facts, reviewer_reviews(pr), branch_commits(pr), rows):
        print(f"  - {note}")

    if problems:
        print("\nDO NOT MERGE:")
        for p in problems:
            print(f"  - {p}")
        return 1
    print("\nmergeable: required checks green at the current head, branch up to "
          "date, no unresolved review thread, and GitHub agrees. Read the review state "
          "above before merging - this tool does not gate on it")
    return 0


# --------------------------------------------------------------------------- selftest

def _facts(head="a" * 40, base="main", checks=(("gates", "SUCCESS"),
                                               ("controls", "SUCCESS")),
           state="OPEN", merge_state="CLEAN", mergeable="MERGEABLE"):
    return {
        "number": 1, "title": "t", "headRefName": "b", "headRefOid": head,
        "baseRefName": base, "state": state, "mergeStateStatus": merge_state,
        "mergeable": mergeable,
        "statusCheckRollup": [{"name": n, "status": "COMPLETED", "conclusion": c}
                              for n, c in checks],
    }


# --------------------------------------------------------- recorded payloads, 2026-08-27
# Read from the API on 2026-08-27 and pasted verbatim. These two pull requests are the
# known-answer pair rule 12 asks for before believing any extraction: #60's head was NOT
# reviewed and its check row says `pass`, #63's head WAS. If a change makes them agree,
# the reading is coming from the instrument rather than from the pull requests.
#
#   gh pr checks 60   ->  CodeRabbit  pass  0     Review rate limited
#   gh pr checks 63   ->  CodeRabbit  pass  0     Review completed

_PR60_HEAD = "a90c5e802b884ec0fe93469a3b4a923310ff942a"
_PR60_LAST_REVIEW = "0445e1fa3068d5ec1693a35f79ceb077a1758af9"
#: `gh pr view 60 --json statusCheckRollup`. The `CodeRabbit` row is a `StatusContext`:
#: it carries `state` and has no `conclusion` and no `status` at all, and no description.
_PR60_ROLLUP = [
    {"__typename": "CheckRun", "name": "controls", "status": "COMPLETED",
     "conclusion": "SUCCESS"},
    {"__typename": "CheckRun", "name": "gates", "status": "COMPLETED",
     "conclusion": "SUCCESS"},
    {"__typename": "StatusContext", "context": "CodeRabbit", "state": "SUCCESS",
     "targetUrl": ""},
]
#: `gh api repos/{owner}/{repo}/commits/<head>/status` - where the description lives.
_PR60_STATUSES = {"CodeRabbit": {"context": "CodeRabbit", "state": "success",
                                 "description": "Review rate limited"}}
#: `gh api repos/{owner}/{repo}/pulls/60/commits`, oldest first.
_PR60_COMMITS = [
    {"sha": "6934d67e1b13ad3de77b3127a8e7cf459495fca5",
     "subject": "Task 175: the gate that reads the CI register now runs before a push"},
    {"sha": "57b28ebd03e04f68a4a1d72493723da39c9060c1",
     "subject": "Task 175, review round 1: the ceiling matched a closed set"},
    {"sha": "c2790fff867bc304712ad4bc57d6f7f94dd150b1",
     "subject": "Task 175, review round 2: the depth rows tested acceptance"},
    {"sha": "f39dd97b7a372f0fb04e88abd5a6b4eeff9002da",
     "subject": "Task 175: the register's workflow band was published on 2026-08-25"},
    {"sha": "4f1b99077e9ea6e628ab5733a81548617779ba86",
     "subject": "Task 175, review round 3: the depth rows reported the value"},
    {"sha": _PR60_LAST_REVIEW,
     "subject": "Merge remote-tracking branch 'origin/main' into task-175-ci-minutes"},
    {"sha": "4434776f1315095235de34d5cb2b5f980f8515a3",
     "subject": "Task 175, review round 4: a refusal that names the variable"},
    {"sha": _PR60_HEAD,
     "subject": "Merge remote-tracking branch 'origin/main' into task-175-ci-minutes"},
]
#: `gh api repos/{owner}/{repo}/pulls/60/reviews`, trimmed to the fields read here. Both
#: logins are present on purpose: `teonimesic` is the human, and the App's login carries
#: the `[bot]` suffix that `AGENTS.md` rule 12 records a filter dropping.
_PR60_REVIEWS = [
    {"id": 5044908132, "user": {"login": "coderabbitai[bot]"},
     "commit_id": "6934d67e1b13ad3de77b3127a8e7cf459495fca5",
     "submitted_at": "2026-08-27T19:34:44Z"},
    {"id": 5044964080, "user": {"login": "teonimesic"},
     "commit_id": "57b28ebd03e04f68a4a1d72493723da39c9060c1",
     "submitted_at": "2026-08-27T19:41:26Z"},
    {"id": 5045055345, "user": {"login": "coderabbitai[bot]"},
     "commit_id": "c2790fff867bc304712ad4bc57d6f7f94dd150b1",
     "submitted_at": "2026-08-27T19:52:42Z"},
    {"id": 5045525394, "user": {"login": "coderabbitai[bot]"},
     "commit_id": _PR60_LAST_REVIEW, "submitted_at": "2026-08-27T20:48:22Z"},
]

_PR63_HEAD = "733ed97cd053f2bac2f218afba9aa47636f127fe"
_PR63_ROLLUP = [{"__typename": "StatusContext", "context": "CodeRabbit",
                 "state": "SUCCESS", "targetUrl": ""}]
_PR63_STATUSES = {"CodeRabbit": {"context": "CodeRabbit", "state": "success",
                                 "description": "Review completed"}}
_PR63_COMMITS = [
    {"sha": "f6f5f1e02f68aaff29f9aedcb65eb187d478ed60", "subject": "Task 186: two clocks"},
    {"sha": _PR63_HEAD, "subject": "Task 186, review round 4: a negative delta"},
]
_PR63_REVIEWS = [{"id": 5045973266, "user": {"login": "coderabbitai[bot]"},
                  "commit_id": _PR63_HEAD, "submitted_at": "2026-08-27T21:59:27Z"}]

# PR #62 is the third recorded case and the one that fixes the DESIGN. Its status at head
# reads `success` `Review completed` - byte-identical to #63's, which really was reviewed
# - while no review object sits at that head and `pr_review_state.py --pr 62 --branch
# task-138-judge-ledger-heading-is-not-money --expect-head f1af78ce...` answers
# `NOTICE / Reviews paused`. So no set of description strings separates a reviewed head
# from an unreviewed one, and the words are reported rather than judged on.
_PR62_HEAD = "f1af78ce716832b0f1b8f24c8a783450c67b3ab9"
_PR62_LAST_REVIEW = "7804aee5"  # short: only the comparison and the printout read it
_PR62_ROLLUP = [
    {"__typename": "CheckRun", "name": "controls", "status": "COMPLETED",
     "conclusion": "SUCCESS"},
    {"__typename": "CheckRun", "name": "gates", "status": "COMPLETED",
     "conclusion": "SUCCESS"},
    {"__typename": "StatusContext", "context": "CodeRabbit", "state": "SUCCESS",
     "targetUrl": ""},
]
_PR62_STATUSES = {"CodeRabbit": {"context": "CodeRabbit", "state": "success",
                                 "description": "Review completed"}}
_PR62_COMMITS = [
    {"sha": _PR62_LAST_REVIEW, "subject": "Merge remote-tracking branch 'origin/main'"},
    {"sha": _PR62_HEAD, "subject": "Merge branch 'main' into task-138-judge-ledger"},
]
_PR62_REVIEWS = [{"id": 5045861846, "user": {"login": "coderabbitai[bot]"},
                  "commit_id": _PR62_LAST_REVIEW,
                  "submitted_at": "2026-08-27T21:34:07Z"}]


def _last_commit(reviews: list[dict]) -> str | None:
    """The sha of the last review, or `None` for an empty list.

    A selftest row that indexes an empty list raises, and a mutant whose only effect is a
    traceback says nothing about which check it defeated - `pr_review_state_mutants.py`
    rejects one for exactly that reason. This makes the row go RED instead.
    """
    return reviews[-1]["commit_id"] if reviews else None


def _pr(head, rollup):
    """A `pr_facts` payload carrying a recorded rollup."""
    f = _facts(head=head)
    f["statusCheckRollup"] = rollup
    return f


def selftest() -> int:
    failures = 0

    def check(label, got, want=True):
        nonlocal failures
        ok = got == want
        if not ok:
            failures += 1
        print(f"  {'ok  ' if ok else 'FAIL'} {label}"
              + ("" if ok else f"\n         got {got!r} want {want!r}"))

    # ---- The gate can go GREEN. Without this the suite is `total=0 passed=0`.
    check("a green, up-to-date PR has no problems",
          check_problems(_facts()) + staleness_problems(_facts(), 0), [])

    # ---- The gate can go RED, one direction per failure mode.
    check("a failing required check is caught",
          len(check_problems(_facts(checks=(("gates", "FAILURE"),
                                            ("controls", "SUCCESS"))))), 1)
    check("a missing required check is caught",
          len(check_problems(_facts(checks=(("gates", "SUCCESS"),)))), 1)
    check("both required checks failing gives two problems",
          len(check_problems(_facts(checks=(("gates", "FAILURE"),
                                            ("controls", "FAILURE"))))), 2)
    check("a cancelled check is not success",
          len(check_problems(_facts(checks=(("gates", "CANCELLED"),
                                            ("controls", "SUCCESS"))))), 1)

    # ---- THE #12/#13 SHAPE: every check green, and merging it broke main.
    stale = _facts()
    check("a green PR behind its base is refused",
          len(check_problems(stale)) == 0 and len(staleness_problems(stale, 3)) == 1,
          True)
    check("the refusal names the commit gap",
          "3 commit(s) behind main" in staleness_problems(stale, 3)[0])

    # ---- A check still running is not a pass.
    running = _facts()
    running["statusCheckRollup"] = [{"name": "gates", "status": "IN_PROGRESS",
                                     "conclusion": None},
                                    {"name": "controls", "status": "COMPLETED",
                                     "conclusion": "SUCCESS"}]
    check("an in-progress check is refused", len(check_problems(running)), 1)

    # ---- A conflicted PR gets no run at all, so absence of red is not green.
    check("a conflicting PR is refused",
          len(staleness_problems(_facts(mergeable="CONFLICTING"), 0)), 1)

    # ---- A check outside REQUIRED must not silently become a requirement, and must
    #      not mask a missing one either.
    extra = _facts(checks=(("gates", "SUCCESS"), ("controls", "SUCCESS"),
                           ("coderabbit", "FAILURE")))
    check("an unlisted check does not gate", check_problems(extra), [])
    only_extra = _facts(checks=(("coderabbit", "SUCCESS"),))
    check("an unlisted check does not satisfy a required one",
          len(check_problems(only_extra)), 2)

    # ---- VARIANT: not a removed mechanism, an input the gate mishandles. A run whose
    #      conclusion is absent because the key is missing rather than null.
    keyless = _facts()
    keyless["statusCheckRollup"] = [{"name": "gates", "status": "COMPLETED"},
                                    {"name": "controls", "status": "COMPLETED",
                                     "conclusion": "SUCCESS"}]
    check("a conclusion-less completed run is refused", len(check_problems(keyless)), 1)

    # ---- VARIANT: the rollup is absent entirely (no workflow has ever run).
    empty = _facts()
    empty["statusCheckRollup"] = None
    check("an absent rollup is refused, not treated as green",
          len(check_problems(empty)), 2)

    # ---- REQUIRED is the address, and the address is an input to the check (rule 12).
    check("REQUIRED names the two workflows that exist",
          sorted(REQUIRED), ["controls", "gates"])

    # ---- The gate can go GREEN on conversations too: zero threads is not a problem.
    check("no unresolved thread is not a problem", conversation_problems([]), [])

    # ---- THE #42 SHAPE. Every named check green, and GitHub refuses it anyway.
    thr = [{"path": "DECISIONS.md", "author": "coderabbitai"},
           {"path": "eval/judge/ink_window_control.py", "author": "coderabbitai"}]
    check("two unresolved threads are refused", len(conversation_problems(thr)), 1)
    check("the refusal names the files, so it is actionable",
          "DECISIONS.md" in conversation_problems(thr)[0], True)
    blocked = _facts(merge_state="BLOCKED")
    named = check_problems(blocked) + staleness_problems(blocked, 0)
    check("PR #42 exactly: the NAMED checks all pass on it", named, [])
    check("...and the conversation check is what catches it",
          len(conversation_problems(thr)), 1)

    # ---- VARIANT, and the fail-open direction: the query could not be run at all.
    # `None` must not read as "no unresolved threads" - rule 7, every reason not to
    # count a failure is a channel a bug can widen.
    check("an unreadable thread query is refused, not read as zero",
          len(conversation_problems(None)), 1)

    # ---- The AGREEMENT row: this tool disagreeing with the host is THIS TOOL's bug.
    check("a clean state with no problems raises no disagreement",
          agreement_problems(_facts(merge_state="CLEAN"), []), [])
    check("BLOCKED with no problems found is reported as an incomplete blocker list",
          len(agreement_problems(blocked, [])), 1)
    check("...but stays quiet when a problem was already found, to avoid double-"
          "reporting the same refusal",
          agreement_problems(blocked, ["something"]), [])

    # ---- MUTANT: drop `blocked` from REFUSING_STATES and the #42 shape goes silent.
    # Patch THIS module's globals, not `import mergeable`. Run as `__main__`, that
    # import builds a SECOND module object, and `agreement_problems` would keep reading
    # the original binding - the mutant edits a copy nothing executes and comes back
    # SURVIVED. It did, on the first run of this row. `AGENTS.md` rule 12 already lists
    # the shape: "a monkeypatched module constant / a value already derived at import".
    g = globals()
    saved = g["REFUSING_STATES"]
    try:
        g["REFUSING_STATES"] = ("behind", "dirty")
        check("MUTANT: REFUSING_STATES without 'blocked' stops catching #42",
              len(agreement_problems(blocked, [])), 0)
    finally:
        g["REFUSING_STATES"] = saved
    check("...and REFUSING_STATES is restored", "blocked" in REFUSING_STATES, True)

    # ---------------------------------------------------------------- the review state
    # The known-answer pair, recorded 2026-08-27. Both read `pass` in `gh pr checks`; one
    # of them had not been reviewed. Every row below is checked against #60 AND #63,
    # because a reading that answers the same way on both is reporting the instrument.
    pr60 = _pr(_PR60_HEAD, _PR60_ROLLUP)
    pr63 = _pr(_PR63_HEAD, _PR63_ROLLUP)
    rows60 = rollup_rows(pr60, _PR60_STATUSES)
    rows63 = rollup_rows(pr63, _PR63_STATUSES)
    r60 = reviewer_reviews_from(_PR60_REVIEWS)
    r63 = reviewer_reviews_from(_PR63_REVIEWS)
    notes60 = review_notes(pr60, r60, _PR60_COMMITS, rows60)
    notes63 = review_notes(pr63, r63, _PR63_COMMITS, rows63)

    # ---- The rollup alone cannot tell the two apart. This is the defect, pinned.
    check("PR #60: the rollup gives the CodeRabbit row no conclusion and no status",
          [(r.get("conclusion"), r.get("status")) for r in _PR60_ROLLUP
           if r.get("context") == "CodeRabbit"], [(None, None)])
    check("...and the rollup rows of #60 and #63 are indistinguishable without it",
          [(r["name"], r["verdict"]) for r in rollup_rows(pr60, None)
           if r["name"] == REVIEWER_CONTEXT]
          == [(r["name"], r["verdict"]) for r in rollup_rows(pr63, None)
              if r["name"] == REVIEWER_CONTEXT], True)

    # ---- The description is folded back in, and it discriminates.
    check("PR #60's CodeRabbit row carries its description",
          [r["description"] for r in rows60 if r["name"] == REVIEWER_CONTEXT],
          ["Review rate limited"])
    check("PR #63's CodeRabbit row carries a different one",
          [r["description"] for r in rows63 if r["name"] == REVIEWER_CONTEXT],
          ["Review completed"])
    check("a rate-limited row is reported with the words that say so, not as a bare pass",
          "Review rate limited" in " ".join(unrequired_notes(rows60)), True)
    check("...and a real review's row reads differently",
          "Review completed" in " ".join(unrequired_notes(rows63)), True)

    # ---- The reading is the review TIMELINE, never the description's wording.
    check("PR #60: the head carries no review of its own",
          "carries no review of its own" in " ".join(notes60), True)
    check("...naming the gap in commits", "2 commit(s) later" in " ".join(notes60), True)
    check("...and listing what went unwritten-about",
          "4434776f" in " ".join(notes60) and _PR60_HEAD[:8] in " ".join(notes60), True)
    check("...and crossing it against the status that says pass",
          "'Review rate limited'" in " ".join(notes60), True)
    check("PR #63: the head IS the commit the review was written at", notes63,
          [f"{REVIEWER} wrote a review at {_PR63_HEAD[:8]}, which IS the current head"])
    check("THE DISCRIMINATION: the two pull requests do not get the same answer",
          notes60 == notes63, False)

    # ---- PR #62, and it is the row that decides the DESIGN. Its status description
    #      reads 'Review completed' at a head where no round finished - so no set of
    #      description strings could have separated it from a real review, and the tool
    #      must report the words rather than judge on them.
    pr62 = _pr(_PR62_HEAD, _PR62_ROLLUP)
    rows62 = rollup_rows(pr62, _PR62_STATUSES)
    notes62 = review_notes(pr62, reviewer_reviews_from(_PR62_REVIEWS), _PR62_COMMITS,
                           rows62)
    check("PR #62's description is indistinguishable from a clean review's",
          [r["description"] for r in rows62 if r["name"] == REVIEWER_CONTEXT],
          [r["description"] for r in rows63 if r["name"] == REVIEWER_CONTEXT])
    check("...and the timeline separates them anyway",
          "carries no review of its own" in " ".join(notes62), True)
    check("...by one commit", "1 commit(s) later" in " ".join(notes62), True)
    check("...and the note quotes the misleading words rather than acting on them",
          "'Review completed'" in " ".join(notes62), True)

    # ---- The limit is stated, in the other direction: a clean round writes no review
    #      object, so this reading is not a verdict and must not present as one.
    for label, n in (("#60", notes60), ("#62", notes62)):
        check(f"PR {label} names the producer of the verdict rather than deciding it",
              "pr_review_state.py" in " ".join(n)
              and "not proof the head went unread" in " ".join(n), True)

    # ---- Rule 12, the recorded miss: the App's login carries `[bot]`.
    check("REVIEWER is the login the API returns, suffix included",
          REVIEWER, "coderabbitai[bot]")
    check("a filter without the suffix selects nothing from the recorded reviews",
          [r for r in _PR60_REVIEWS
           if (r.get("user") or {}).get("login") == "coderabbitai"], [])
    check("...while the real login selects 3 of the 4", len(r60), 3)
    check("the last review is the latest by time, not by list position",
          _last_commit(r60), _PR60_LAST_REVIEW)
    # ---- VARIANT: an input the reading mishandles if it trusts the payload's order.
    #      The endpoint's ordering is not part of its contract, and the recorded payload
    #      happens to arrive sorted - so reversing it is the only thing that asks.
    check("...and reversing the payload does not move the answer",
          _last_commit(reviewer_reviews_from(list(reversed(_PR60_REVIEWS)))),
          _PR60_LAST_REVIEW)
    # ---- VARIANT: a review that was never submitted is not the last review. Dropping it
    #      can only make a head look LESS reviewed, which is the fail-closed direction.
    unsubmitted = {"id": 9, "user": {"login": REVIEWER}, "commit_id": _PR60_HEAD,
                   "submitted_at": None}
    check("an unsubmitted review is not read as a review of the head",
          _last_commit(reviewer_reviews_from(_PR60_REVIEWS + [unsubmitted])),
          _PR60_LAST_REVIEW)
    check("...and a pull request whose ONLY review is unsubmitted reads as unwritten-at",
          "has written no review on this pull request" in " ".join(review_notes(
              pr60, reviewer_reviews_from([unsubmitted]), _PR60_COMMITS, rows60)), True)

    # ---- A required check is unaffected by any of this.
    check("PR #60's required checks are still green", check_problems(pr60), [])
    check("...and #63, whose rollup holds only the status context, is still refused for "
          "having no required run at all", len(check_problems(pr63)), 2)
    check("a required row is not reported as an unrequired one",
          [n for n in unrequired_notes(rows60) if "'gates'" in n or "'controls'" in n],
          [])

    # ---- VARIANT: a status context with no description at all. Not a removed mechanism
    #      - an input the reading mishandles if it assumes the field is there.
    nodesc = rollup_rows(pr60, {})
    check("a status row with no description says so rather than going quiet",
          "no description posted at this head" in " ".join(unrequired_notes(nodesc)),
          True)
    check("...and it still does not read as reviewed",
          "Review rate limited" in " ".join(unrequired_notes(nodesc)), False)

    # ---- VARIANT: the descriptions could not be read. THIRD value, not "no description".
    unread = rollup_rows(pr60, None)
    check("unreadable statuses are reported as unknown, not as absent",
          "could not be read" in " ".join(unrequired_notes(unread)), True)
    check("...and that is a different note from the empty-dict one",
          unrequired_notes(unread) == unrequired_notes(nodesc), False)

    # ---- VARIANT: the rollup row has neither a conclusion nor a state. The ticket's
    #      literal complaint, and an absent verdict must not be passed over.
    blank = _pr(_PR60_HEAD, [{"__typename": "StatusContext", "context": "CodeRabbit"}])
    check("a run with no conclusion keeps its status, so 'still running' stays "
          "distinguishable from 'finished and said nothing'",
          [(r["verdict"], r["status"]) for r in rollup_rows(
              _pr(_PR60_HEAD, [{"__typename": "CheckRun", "name": "controls",
                                "status": "IN_PROGRESS", "conclusion": ""}]), {})],
          [(None, "IN_PROGRESS")])
    running = _pr(_PR60_HEAD, [{"__typename": "StatusContext", "context": "CodeRabbit",
                                "status": "IN_PROGRESS"}])
    check("...and a row with no verdict but a status says which status",
          "(status in_progress)" in
          " ".join(unrequired_notes(rollup_rows(running, {}))), True)
    check("...which is what keeps 'still running' apart from 'finished and said nothing'",
          unrequired_notes(rollup_rows(running, {}))
          == unrequired_notes(rollup_rows(
              _pr(_PR60_HEAD, [{"__typename": "StatusContext",
                                "context": "CodeRabbit"}]), {})), False)
    check("a row with no conclusion and no state is named explicitly",
          "reports no conclusion and no state" in
          " ".join(unrequired_notes(rollup_rows(blank, {}))), True)
    check("...and is not treated as a pass",
          "An absent verdict is not a pass" in
          " ".join(unrequired_notes(rollup_rows(blank, {}))), True)

    # ---- VARIANT: reviews readable and empty. Not the same as unreadable.
    check("zero reviews is reported as zero reviews, not as reviewed",
          "has written no review on this pull request" in
          " ".join(review_notes(pr60, [], _PR60_COMMITS, rows60)), True)
    check("...and the status description is still quoted beside it",
          "'Review rate limited'" in
          " ".join(review_notes(pr60, [], _PR60_COMMITS, rows60)), True)
    # ---- VARIANT, fail-open direction: the timeline could not be read at all (rule 7).
    unreadable = review_notes(pr60, None, _PR60_COMMITS, rows60)
    check("an unreadable timeline is a third value",
          "neither 'unreviewed' nor 'reviewed'" in " ".join(unreadable), True)
    check("...and it never claims the head was reviewed",
          "IS the current head" in " ".join(unreadable), False)

    # ---- VARIANT: commits unreadable while the head is stale. Still NOT reviewed.
    nocommits = review_notes(pr60, r60, None, rows60)
    check("an unreadable commit list still reports the head as a different commit",
          "NOT the same commit" in " ".join(nocommits), True)

    # ---- VARIANT: the reviewed sha is not on the branch - a rebase or force-push.
    rebased = review_notes(pr60, r60, _PR60_COMMITS[6:], rows60)
    check("a reviewed commit no longer on the branch is reported as such",
          "not on the branch" in " ".join(rebased), True)

    # ---- MUTANT: stop folding the description into the row, and #60's rate limit goes
    #      silent - the exact state the tool shipped in until 2026-08-27.
    saved_rows = rollup_rows
    try:
        g = globals()
        g["rollup_rows"] = lambda facts, statuses: saved_rows(facts, None)
        check("MUTANT: without the description fold-in, the rate limit is unreportable",
              "Review rate limited" in
              " ".join(unrequired_notes(rollup_rows(pr60, _PR60_STATUSES))), False)
    finally:
        globals()["rollup_rows"] = saved_rows
    check("...and the fold-in is restored",
          "Review rate limited" in
          " ".join(unrequired_notes(rollup_rows(pr60, _PR60_STATUSES))), True)

    # ---- MUTANT: read the App by a login without the `[bot]` suffix, and #60 and #63
    #      both come back "no review exists" - one wrong answer for every subject, which
    #      is what made the original miss look like a finding (rule 12).
    g = globals()
    saved_reviewer = g["REVIEWER"]
    try:
        g["REVIEWER"] = "coderabbitai"
        check("MUTANT: a login without '[bot]' finds no review on either pull request",
              (reviewer_reviews_from(_PR60_REVIEWS),
               reviewer_reviews_from(_PR63_REVIEWS)), ([], []))
    finally:
        g["REVIEWER"] = saved_reviewer
    check("...and REVIEWER is restored", len(reviewer_reviews_from(_PR60_REVIEWS)), 3)


    print(f"\nmergeable selftest: {'ok' if not failures else 'FAILED'} "
          f"({failures} failures)")
    return 1 if failures else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("pr", nargs="?", help="pull request number or URL")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return selftest()
    if not args.pr:
        ap.error("give a pull request number, or --selftest")
    return report(args.pr)


if __name__ == "__main__":
    sys.exit(main())
