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


def report(pr: str) -> int:
    facts = pr_facts(pr)
    if facts.get("state") != "OPEN":
        print(f"PR #{facts['number']} is {facts['state']}, not open")
        return 1
    ahead = behind_by(facts["baseRefName"], facts["headRefOid"])
    problems = check_problems(facts) + staleness_problems(facts, ahead)

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
    print("\nmergeable: required checks green at the current head, branch up to date")
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
