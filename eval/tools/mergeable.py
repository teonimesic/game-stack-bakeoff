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


def report(pr: str) -> int:
    facts = pr_facts(pr)
    if facts.get("state") != "OPEN":
        print(f"PR #{facts['number']} is {facts['state']}, not open")
        return 1
    ahead = behind_by(facts["baseRefName"], facts["headRefOid"])
    threads = unresolved_threads(pr)
    problems = (check_problems(facts) + staleness_problems(facts, ahead)
                + conversation_problems(threads))
    problems += agreement_problems(facts, problems)

    print(f"PR #{facts['number']}  {facts['title'][:64]}")
    print(f"  head {facts['headRefOid'][:8]} on {facts['headRefName']} "
          f"-> {facts['baseRefName']} (behind by {ahead})")
    for name in REQUIRED:
        runs = [r for r in (facts.get("statusCheckRollup") or [])
                if (r.get("name") or r.get("context")) == name]
        got = runs[0] if runs else None
        print(f"  {name:10s} {(got or {}).get('conclusion') or (got or {}).get('status') or 'ABSENT'}")
    if problems:
        print("\nDO NOT MERGE:")
        for p in problems:
            print(f"  - {p}")
        return 1
    print("\nmergeable: required checks green at the current head, branch up to "
          "date, no unresolved review thread, and GitHub agrees")
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
