#!/usr/bin/env python3
"""Mutants of `pr_review_state.py`, each deleting one mechanism its selftest names.

`pr_review_state.py --selftest` returns `ok (0 failures)`, and a green selftest is exactly
the shape this repository exists to distrust: `total=0 passed=0` is indistinguishable from
a correctly-passing suite. The only thing that establishes a check can fail is removing the
mechanism it names and watching it go red.

**The count is `len(MUTANTS)` and nothing else** — a count with a producer goes stale for an
hour; a count with none goes stale forever.

WHAT EACH ONE REMOVES, AND WHY ITS LOSS WOULD BE INVISIBLE
-----------------------------------------------------------
None of these crashes. Every one returns a verdict that looks exactly like a verdict:

| mutant | what it deletes | what the tool would then report |
|---|---|---|
| `branch_assert` | the `headRefName` equality | **the defect this tool was built for**: a review verdict about another agent's pull request, at exit 0 |
| `branch_substring` | equality, keeping containment | `--branch task-12` accepts `task-127-…`. A prefix of a task id is another task id here |
| `head_shape_guard` | the 40-hex check on the head | `contains("")` is true of every string, so an empty head reports **every** pull request reviewed — fail-open |
| `head_len_only` | the hex half, keeping the length | 40 characters of anything passes, and a truncated or error string is 40 characters often enough |
| `branch_present_guard` | the empty-`headRefName` refusal | a missing branch is reported as the wrong branch, so the reader repairs the wrong thing |
| `expect_head_compare` | `--expect-head` against `headRefOid` | #165: the API has not caught up to your push and the poll answers about the previous head |
| `expect_head_shape` | the 40-hex check on `--expect-head` | an abbreviation never equals a full sha, so the poll refuses forever — the loud direction, but it refuses for a reason it does not state |
| `classify_head_guard` | the same shape check inside `classify` | the fail-open above, reached by any caller that is not the CLI |
| `review_body_guard` | `body != ""` on review objects | a **reply container** counts as a review. GitHub creates one when the bot answers a comment and stamps it with the current head, so declining a comment manufactures a review of a round that has not started |
| `review_commit_match` | `commit_id == head` | any review this pull request ever had counts as a review of this head |
| `reviews_bot_filter` | the login filter on reviews | the agent's own review object counts |
| `comments_bot_filter` | the login filter on comments | the agent trips the check by describing it — measured once already, on a comment quoting the marker while explaining the bug |
| `headings_bot_filter` | the login filter on the notice extractor | a human quoting a deadlock notice becomes a deadlock |
| `inprogress_detect` | the in-progress marker match | a round that is **running** reads as finished. The "No actionable comments" line under that marker is the PREVIOUS round's verdict |
| `inprogress_exclude` | the marker exclusion from the finished COUNT | the verdict is still right and `by_comment` says a review exists that does not — the audit trail disagreeing with the verdict it accompanies |
| `notice_before_landed` | the precedence of a real review over a notice | a stale `Review limit reached` — CodeRabbit edits comments in place, and PR #6's is already gone — outranks the review sitting next to it |
| `inflight_before_review` | the precedence of a review object over a running round | a landed review is reported as still in flight, and the wait runs to its bound with the answer already on the page |
| `gh_exit_ignored` | the `gh` returncode check | a failing API becomes a poll result (rule 2), and empty stdout parses as "no reviews" |
| `gh_no_timeout` | the `timeout=` argument itself | a hung `gh` never returns, so `wait_for` never reaches the line that checks its budget. **The silence bound becomes unreachable on the one failure it exists to bound** |
| `gh_timeout_ignored` | the `TimeoutExpired` conversion | the same hang surfaces as an uncaught exception rather than a named refusal, so `--wait` dies where it should have reported |
| `census_cap_ignored` | the refusal when `gh pr list` returns a full page | `--limit` is honoured silently, so a repository past the cap gives a census of the cap. **The census is the known-answer proof; a truncated one still agrees with every row it kept** |
| `first_page_only` | page aggregation | the review at the head sha is the NEWEST and the first to fall off page 1. gh 2.98 merges pages, older versions concatenate — so this is invisible on the version you happen to have |
| `flight_bound_is_quiet` | the longer bound once a round has been seen | the 15-minute-clock defect at a different constant: a review that lands at 40 minutes is handed back as "no review" |
| `latch_not_sticky` | the latch on `seen_in_flight` | CodeRabbit rewrites the summary during a round, so the marker comes and goes; recomputing from the last poll expires at the quiet bound mid-round |
| `notice_does_not_stop` | `NOTICE` ending the wait | a paused or limit-reached review is waited out in full instead of being acted on, and the remedy is in the comment the tool already read |
| `census_skips_address_check` | the address assertion inside `--census` | `pr list` and `pr view` are two reads and can disagree; the known-answer proof stops being one |
| `render_drops_the_branch` | the branch from the output line | the audit trail loses the thing the assertion is about — and printing was one of the two things `tasks/127` asked for |
| `emit_not_flushed` | the `flush=True` on the poll line | Python block-buffers stdout when it is not a terminal, so a `--wait` under a harness prints **0 bytes** for the whole round and the lines arrive after the answer does. Measured on this pull request's own first round |
| `wait_emits_through_print` | `wait_for` using the flushing emitter | the same silence, reached through the default argument instead of through the function |
| `drop_field` | a field the selftest reads, renamed | a row silently reading a field that is no longer there. **It must redden a named row, not raise** — a mutant that only crashes exits non-zero without saying which check it defeated, so the harness rejects a mutant that produced no red row |

WHAT THIS DOES NOT DO
---------------------
A mutant asks whether a check **can** fail. Only a **variant** asks whether it can still
**pass** on an input it mishandles (`AGENTS.md` rule 15). The variants live in
`pr_review_state.selftest`, because a variant must pass. **The count is the closing line of
`pr_review_state.py --selftest`**, which counts the rows labelled `variant` rather than
restating a number here. Each is paired with the mutant that proves its row can go red:

| variant, by its label in the selftest | the input it must still handle | proved reddenable by |
|---|---|---|
| `A3` | a branch name that is a prefix of the expected one | `branch_substring` |
| `A6` | 40 characters that are not hex | `head_len_only` |
| `B2` | a reply container at the head | `review_body_guard` |
| `B5` | a human comment quoting the head and the marker | `comments_bot_filter` |
| `B9` | a stale deadlock notice beside a landed review | `notice_before_landed` |
| `B10` | a running round beside a landed review | `inflight_before_review` |
| `B11` | a round running against a different head | `inprogress_detect` |
| `F2` | the marker disappearing mid-round | `latch_not_sticky` |

**Needs no corpus and no network.** `pr_review_state.py --selftest` injects its own `gh`
runner and its own clock.

    python3 eval/tools/pr_review_state_mutants.py          # every mutant
    python3 eval/tools/pr_review_state_mutants.py --list   # the count and the names only
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "pr_review_state.py"

# (name, exact span to replace, replacement). The span must be present VERBATIM: a mutant
# whose search text has drifted is a no-op that reports a pass for a check that never
# changed. Drift is a failure below, never a skip.
MUTANTS: dict[str, tuple[str, str]] = {
    # ---- the address. The reason this file exists.
    "branch_assert": (
        "    if branch != expect_branch:",
        "    if False:"),
    "branch_substring": (
        "    if branch != expect_branch:",
        "    if expect_branch not in branch:"),
    "head_shape_guard": (
        "    if not FULL_SHA.match(head):",
        "    if len(head) < 0:"),
    "head_len_only": (
        "    if not FULL_SHA.match(head):",
        "    if len(head) != 40:"),
    "branch_present_guard": (
        "    if not branch:\n        return f\"NO BRANCH",
        "    if False:\n        return f\"NO BRANCH"),
    "expect_head_compare": (
        "        if head != expect_head:",
        "        if False:"),
    "expect_head_shape": (
        "        if not FULL_SHA.match(expect_head):",
        "        if False:"),
    "classify_head_guard": (
        '    if not FULL_SHA.match(head or ""):',
        "    if False:"),

    # ---- what counts as a review
    "review_body_guard": (
        '                 if (r.get("body") or "") != "" and r.get("commit_id") == head]',
        '                 if r.get("commit_id") == head]'),
    "review_commit_match": (
        '                 if (r.get("body") or "") != "" and r.get("commit_id") == head]',
        '                 if (r.get("body") or "") != ""]'),
    "reviews_bot_filter": (
        "    by_review = [r for r in _by_bot(reviews)",
        "    by_review = [r for r in reviews"),
    "comments_bot_filter": (
        '    naming = [c for c in _by_bot(comments) if head in (c.get("body") or "")]',
        '    naming = [c for c in comments if head in (c.get("body") or "")]'),
    "headings_bot_filter": (
        "    for c in _by_bot(comments):",
        "    for c in comments:"),
    "inprogress_detect": (
        '    in_flight = [c for c in naming if INPROGRESS_MARKER in (c.get("body") or "")]',
        "    in_flight = []"),
    "inprogress_exclude": (
        '    finished = [c for c in naming if INPROGRESS_MARKER not in (c.get("body") or "")]',
        "    finished = list(naming)"),

    # ---- precedence between the arms
    "notice_before_landed": (
        '    if by_review:\n        verdict = "LANDED_REVIEW"',
        '    if headings:\n        verdict = "NOTICE"\n'
        '    elif by_review:\n        verdict = "LANDED_REVIEW"'),
    "inflight_before_review": (
        '    if by_review:\n        verdict = "LANDED_REVIEW"\n'
        '    elif in_flight:\n        verdict = "IN_FLIGHT"',
        '    if in_flight:\n        verdict = "IN_FLIGHT"\n'
        '    elif by_review:\n        verdict = "LANDED_REVIEW"'),

    # ---- reading the API at all
    "gh_exit_ignored": (
        "    if proc.returncode != 0:",
        "    if False:"),
    "gh_no_timeout": (
        "                      timeout=GH_TIMEOUT)",
        "                      )"),
    "gh_timeout_ignored": (
        "    except subprocess.TimeoutExpired as exc:",
        "    except ValueError as exc:"),
    "census_cap_ignored": (
        "    if len(listing) >= CENSUS_LIMIT:",
        "    if False:"),
    "first_page_only": (
        "        if isinstance(value, list):\n            out.extend(value)",
        "        if isinstance(value, list):\n            return value"),

    # ---- the wait, which is bounded on silence rather than on a clock
    "flight_bound_is_quiet": (
        "        budget = flight_timeout if seen_in_flight else quiet_timeout",
        "        budget = quiet_timeout"),
    "latch_not_sticky": (
        "        budget = flight_timeout if seen_in_flight else quiet_timeout",
        '        budget = (flight_timeout if last["verdict"] == "IN_FLIGHT"'
        "                  else quiet_timeout)"),
    "notice_does_not_stop": (
        '        if last["verdict"] in ("LANDED_REVIEW", "LANDED_COMMENT", "NOTICE"):',
        '        if last["verdict"] in ("LANDED_REVIEW", "LANDED_COMMENT"):'),

    # ---- the census, which is the known-answer proof of the extraction
    "census_skips_address_check": (
        "        refusal = check_address(n, view, branch)",
        "        refusal = None"),

    # ---- the audit trail, and the selftest's own drift guard
    "emit_not_flushed": (
        "    print(line, flush=True)",
        "    print(line)"),
    "wait_emits_through_print": (
        "             emit: Callable[[str], None] = _emit,",
        "             emit: Callable[[str], None] = print,"),
    "render_drops_the_branch": (
        "    line = (f\"#{result['pr']} {result['branch']} head={result['head']} \"",
        "    line = (f\"#{result['pr']} head={result['head']} \""),
    "drop_field": (
        '        "by_comment": len(finished),',
        '        "by_comment_RENAMED": len(finished),'),
}


def run_selftest(path: Path) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(path), "--selftest"],
                          capture_output=True, text=True, check=False)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--list", action="store_true",
                    help="print the count and the mutant names, and run nothing")
    args = ap.parse_args()

    if args.list:
        print(f"{len(MUTANTS)} mutants of {SOURCE.name}:")
        for name in MUTANTS:
            print(f"  {name}")
        return 0

    base = SOURCE.read_text()
    problems: list[str] = []

    with tempfile.TemporaryDirectory() as tmp:
        # THE CONTROL FIRST. An unmutated copy must go GREEN from the same temp directory
        # and the same interpreter the mutants use. Without it, every mutant "failing"
        # could be the harness failing, and the sweep would report a clean bill of health
        # for a file that cannot run at all.
        control = Path(tmp) / "control_unmutated.py"
        control.write_text(base)
        proc = run_selftest(control)
        if proc.returncode != 0:
            print("CONTROL FAILED — an unmutated copy does not pass its own selftest. "
                  "Every mutant below would be 'caught' by the same breakage.")
            for line in (proc.stdout + proc.stderr).splitlines():
                print(f"    {line}")
            return 1
        print(f"control (unmutated): exit 0, {proc.stdout.strip().splitlines()[-1]}")

        for name, (old, new) in MUTANTS.items():
            if old not in base:
                # NOT a skip. A mutant whose search text has drifted tests nothing, and
                # counting it as caught is how a suite reports a pass for a check that no
                # longer exists.
                print(f"--- {name}: NOT APPLIED — its search text is no longer in "
                      f"{SOURCE.name}")
                problems.append(f"{name}: search text drifted")
                continue
            mutated = Path(tmp) / f"mutant_{name}.py"
            mutated.write_text(base.replace(old, new, 1))
            proc = run_selftest(mutated)
            last = (proc.stdout.strip().splitlines() or ["<no output>"])[-1]
            if proc.returncode == 0:
                print(f"--- {name}: SURVIVED — the selftest passed without this mechanism")
                problems.append(f"{name}: survived")
            else:
                red = [ln for ln in proc.stdout.splitlines() if ln.startswith("FAIL ")]
                print(f"    {name}: caught, {len(red)} red row(s) — {last}")
                for ln in red[:3]:
                    print(f"        {ln}")
                if not red:
                    # NOT caught. Non-zero with no red row is a TRACEBACK, and a traceback
                    # is the selftest dying rather than the selftest disagreeing: it tells
                    # you nothing about which check the mutant defeated, and a mutant whose
                    # only effect is a crash would score green on a check that no longer
                    # exists. Both exit non-zero; only one of them is a measurement.
                    tail = (proc.stderr.strip().splitlines() or ["<no stderr>"])[-1]
                    print(f"        NOT CAUGHT — no red row, died with: {tail}")
                    problems.append(f"{name}: crashed without a red row")

    print()
    if problems:
        print(f"{len(problems)} problem(s) of {len(MUTANTS)} mutants:")
        for p in problems:
            print(f"  {p}")
        return 1
    print(f"all {len(MUTANTS)} mutants caught")
    return 0


if __name__ == "__main__":
    sys.exit(main())
