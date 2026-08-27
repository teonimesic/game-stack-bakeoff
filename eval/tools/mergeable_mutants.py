#!/usr/bin/env python3
"""Mutants of `mergeable.py`, each deleting one mechanism its selftest names.

`mergeable.py --selftest` returns `ok (0 failures)`, and a green selftest is exactly the
shape this repository exists to distrust: `total=0 passed=0` is indistinguishable from a
correctly-passing suite. The only thing that establishes a check can fail is removing the
mechanism it names and watching it go red.

**The count is `len(MUTANTS)` and nothing else** — a count with a producer goes stale for
an hour; a count with none goes stale forever.

WHAT EACH ONE REMOVES, AND WHY ITS LOSS WOULD BE INVISIBLE
-----------------------------------------------------------
None of these crashes. Every one leaves a report that reads exactly like a report:

| mutant | what it deletes | what the tool would then report |
|---|---|---|
| `blocked_state` | `blocked` from `REFUSING_STATES` | the #42 shape: every named check passes and GitHub refuses the merge, silently |
| `description_fold_in` | the commit-status `description` joined onto its rollup row | the state this tool shipped in until 2026-08-27: `CodeRabbit` reported as `success` with the words `Review rate limited` nowhere in the output |
| `statuscontext_verdict` | `state` as a fallback verdict | a `StatusContext` has no `conclusion` and no `status`, so the reviewer's row reads `NO CONCLUSION` for ever and every pull request looks the same |
| `unconcluded_named` | the line for a row with no verdict at all | a row the rollup says nothing about produces no line, and absence of a line is indistinguishable from absence of a problem |
| `unconcluded_loses_status` | the run status from that line | `still running` and `finished and said nothing` become the same sentence |
| `descriptions_third_value` | the `None`/`{}` distinction on the status read | an API failure reads as *no description was posted*, which is the fail-open direction (rule 7) |
| `reviewed_head_compare` | `commit_id` against `headRefOid` | every pull request with any review ever reads as reviewed at its head — the half of the defect the description cannot cover, since PR #62's said `Review completed` |
| `reviewer_bot_suffix` | the `[bot]` on the App's login | **empty on every pull request**, read as *no review exists*. `AGENTS.md` rule 12 records this exact miss being committed while checking someone else's finding |
| `reviews_third_value` | the `None` refusal on an unreadable timeline | *nobody could ask* reads as *reviewed*, fail-open again |
| `reviews_unsorted` | the sort by `submitted_at` | the endpoint's order is not part of its contract, and "the last review" is the one fact read out of the list |
| `unsubmitted_counts` | the `submitted_at` filter | a review nobody has submitted becomes the review of the head it was started against |
| `commit_list_completeness` | the assertion that the commit list ends at the head | `/pulls/<n>/commits` caps at 250, so a long branch returns a list holding the reviewed commit and not the head — and counting in it gives a confident wrong gap, a number in range |
| `status_not_crossed` | quoting the reviewer's own status beside a stale head | the reader is told the head is unwritten-about and not what the status claims, which is the pair that made this findable |
| `verdict_caveat` | the caveat and the `pr_review_state.py` command | a clean incremental round writes no review object, so the report would present *no review of its own* as a verdict it is not |

WHAT THIS DOES NOT DO
---------------------
A mutant asks whether a check **can** fail. Only a **variant** asks whether it can still
**pass** on an input it mishandles (`AGENTS.md` rule 15). The variants live in
`mergeable.selftest`, marked `VARIANT` in its comments, because a variant must pass. Each
is paired with the mutant that proves its row can go red:

| the variant | the input it must still handle | proved reddenable by |
|---|---|---|
| a completed run whose `conclusion` key is missing rather than null | a shape the rollup really returns | (pre-existing) |
| an absent rollup entirely | no workflow has ever run | (pre-existing) |
| a status context with no description at head | `{}`, readable and empty | `descriptions_third_value` |
| the statuses unreadable | `None`, the third value | `descriptions_third_value` |
| a rollup row with neither conclusion nor state | the ticket's literal complaint | `unconcluded_named` |
| a review payload in reverse order | an ordering the endpoint does not promise | `reviews_unsorted` |
| a review with no `submitted_at` | a PENDING review | `unsubmitted_counts` |
| the reviewed sha absent from the branch | a force-push or rebase | `reviewed_head_compare` |
| the commit list unreadable while the head is stale | a partial answer that must stay a refusal | `reviewed_head_compare` |
| a commit list that stops short of the head | the 250-commit cap on the endpoint | `commit_list_completeness` |
| PR #62's `Review completed` at an unreviewed head | a description no wordlist could reject | `reviewed_head_compare` |

**Needs no corpus and no network.** `mergeable.py --selftest` drives recorded payloads.

    python3 eval/tools/mergeable_mutants.py          # every mutant
    python3 eval/tools/mergeable_mutants.py --list   # the count and the names only
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "mergeable.py"

# (name, exact span to replace, replacement). The span must be present VERBATIM: a mutant
# whose search text has drifted is a no-op that reports a pass for a check that never
# changed. Drift is a failure below, never a skip.
MUTANTS: dict[str, tuple[str, str]] = {
    # ---- the pre-existing gate, kept here so one command covers the whole file.
    "blocked_state": (
        'REFUSING_STATES = ("blocked", "behind", "dirty", "draft", "unstable")',
        'REFUSING_STATES = ("behind", "dirty", "draft", "unstable")'),

    # ---- the rollup row, and the field it does not carry.
    "description_fold_in": (
        '        desc = (statuses or {}).get(name, {}).get("description") or None',
        '        desc = None'),
    "statuscontext_verdict": (
        '        verdict = (run.get("conclusion") or run.get("state") or "").upper() or None',
        '        verdict = (run.get("conclusion") or "").upper() or None'),
    "descriptions_third_value": (
        '"descriptions_readable": statuses is not None})',
        '"descriptions_readable": True})'),
    "unconcluded_named": (
        '        if row["verdict"] is None:\n'
        '            notes.append(unconcluded_note(row))',
        '        if row["verdict"] is None:\n'
        '            pass'),
    "unconcluded_loses_status": (
        '            + (f" (status {row[\'status\'].lower()})" if row["status"] else "")',
        '            + ""'),

    # ---- the review timeline, which is what the description cannot answer.
    "reviewed_head_compare": (
        '        if at == head:\n'
        '            return [f"{REVIEWER} wrote a review at',
        '        if True:\n'
        '            return [f"{REVIEWER} wrote a review at'),
    "reviewer_bot_suffix": (
        'REVIEWER = "coderabbitai[bot]"',
        'REVIEWER = "coderabbitai"'),
    "reviews_third_value": (
        '    if reviews is None:\n'
        '        return [f"the review timeline could not be read',
        '    if False:\n'
        '        return [f"the review timeline could not be read'),
    "reviews_unsorted": (
        '    return sorted(mine, key=lambda r: (r.get("submitted_at") or "", '
        'r.get("id") or 0))',
        '    return mine'),
    "unsubmitted_counts": (
        '            and r.get("submitted_at")]',
        '            and True]'),

    "commit_list_completeness": (
        '            if not shas or shas[-1] != head:',
        '            if False:'),

    # ---- what the report says ABOUT its own reading.
    "status_not_crossed": (
        '    row = next((r for r in rows if r["name"] == REVIEWER_CONTEXT), None)',
        '    row = None'),
    "verdict_caveat": (
        '    notes.append(f"a clean round writes no review object, so \'no review of '
        'its own\' is "\n'
        '                 f"not proof the head went unread. For the verdict run: '
        '{verdict_cmd}")\n',
        ''),
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
                print(f"--- {name}: SURVIVED — the selftest passed without this "
                      f"mechanism")
                problems.append(f"{name}: survived")
                continue
            red = [ln for ln in proc.stdout.splitlines() if ln.strip().startswith("FAIL")]
            print(f"    {name}: caught, {len(red)} red row(s) — {last}")
            for ln in red[:3]:
                print(f"        {ln.strip()}")
            if not red:
                # NOT caught. Non-zero with no red row is a TRACEBACK, and a traceback is
                # the selftest dying rather than the selftest disagreeing: it tells you
                # nothing about which check the mutant defeated, and a mutant whose only
                # effect is a crash would score green on a check that no longer exists.
                # Both exit non-zero; only one of them is a measurement.
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
