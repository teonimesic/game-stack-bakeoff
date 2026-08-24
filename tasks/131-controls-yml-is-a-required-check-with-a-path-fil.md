---
id: 131
title: controls.yml is a required check with a path filter, so a PR touching neither eval/ nor .agents/ can never merge
status: done
priority: 1
refs: '#162, .github/workflows/controls.yml, eval/tools/ci_minutes.py, DECISIONS.md'
done_when: A pull request changing ONLY tasks/ or README.md reports a green `controls` check and is mergeable. `ci_minutes.py --selftest` green, with the one-path-from-one-trigger mutant still dying. `.github/workflows/README.md` states where the filter now lives, and DECISIONS.md records whether `controls` is required.
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/16
established_by: 'PR #16 squash-merged. Verified independently: controls.yml declares no paths on any trigger; the guard is != ''false'' so an unwritten output runs the suites; --scope with no event defaults to relevant=true; selftest 18 mutants died, 5 variants passed; PR #17 proved both directions on one commit (pull_request skipped 5 suites in 7s, push ran all 5 in 627s). Merge conflict in the CI register composed, not sided, and the gate count verified against its producer on the merged tree.'
---

A workflow filtered by `paths:` does not run when a pull request matches none of them, and
GitHub reports NO check rather than a passing one. A required check that never reports blocks
the merge permanently.

Measured on control PR #14 (closed): it changed one line of `CLEANUP-LOG.md`, `gates` went green,
`controls` was ABSENT, and `mergeable.py` correctly refused with `required check 'controls' has
no run at head`. Updating the branch would not have helped - nothing would ever produce that check.

The filter is `eval/**`, `.agents/**`, `.claude/**`, `.github/workflows/controls.yml`. **`tasks/`,
`README.md`, `DECISIONS.md` and `eval/FINDINGS.md` are not in it**, so a documentation or queue
pull request - which is a large share of the work here - is exactly the case that hangs.

`main` currently requires BOTH `gates` and `controls`, so this is live. Reducing the requirement
to `gates` alone was attempted as an interim and blocked by a permission classifier; the operator
has to make that change or approve it.

Note `gates` alone would still have caught #162: the step that went red, `tokenvalue --selftest`,
is in `gates.yml`, not `controls.yml`.

THE FIX, and it is not "delete the filter". The recommended shape is: trigger `controls` on every
pull request, compute in a FIRST STEP whether any relevant path changed, and guard the five suite
steps on that output. The job then always reports, so the required check always lands, and the
685s is still only spent when it can find something.

`eval/tools/ci_minutes.py`'s `filter_problems()` asserts `paths:` exists under BOTH the
`pull_request` and `push` triggers, and `tasks_mutants` pins it. Moving the filter means moving
that check to read the step, and the existing mutant - deleting one path from ONE trigger - must
still die. Do not weaken it to a substring test; its docstring records that the substring version
let exactly that mutant survive.

## note 2026-08-24

## The repository went public on 2026-08-24, which changes the cost side of this

Actions minutes on Linux are now **free and unlimited** — the filter existed to save metered
minutes on a private repository (`DECISIONS.md`). So "delete the filter and let `controls` run on
every pull request" is no longer expensive in money. It is still expensive in **wall-clock**: both
tiers are required checks, so 685s would sit in front of every merge, including a one-line
documentation fix. That is the tradeoff to argue with, and it is a different argument from the one
the filter was written for. Say which one you are answering.

## The interim narrowing is the operator's, not yours

Reducing `main`'s required checks to `gates` alone was attempted on 2026-08-24 and refused by a
permission classifier. **Do not attempt it, and do not treat it as done.** Your job is the
workflow-side fix that makes `controls` always report; whether the requirement is narrowed
meanwhile is a separate, operator-side action.

## What NOT to conclude

A green `controls` on your own pull request does not test this. Your branch will touch
`.github/workflows/controls.yml`, which is IN the filter — so `controls` runs for you whatever you
do. **The case that must be proved is a pull request touching NONE of the filtered paths**, and
proving it needs a real pull request that changes, say, only `tasks/` or only `README.md`. A
control branch is cheap now that minutes are free; PR #14 (closed) is the worked example of the
failing shape, and its refusal text is recorded in the commit that filed this ticket.

## note 2026-08-24

## What was built, and the one thing not to re-derive

`controls.yml` declares **no `paths:` and no `paths-ignore:`** on any trigger. It runs on every
pull request and decides inside the job: the first step is `python3 eval/tools/ci_minutes.py
--scope`, which diffs the merge commit against its **first parent** — the same population
`on: paths:` was matched against, so the filter *moved* and did not change — and writes
`relevant=true|false` to `$GITHUB_OUTPUT`. Every `run:` step below it carries the guard.

**The guard is `!= 'false'`, never `== 'true'`, and that single choice is the whole safety
argument.** A step output nothing wrote reads as the empty string. `== 'true'` skips on it and
reports a green `controls` that executed no gate; `!= 'false'` runs the suites. The only way to
skip is for the scope step to have run and said so.

`DECISIONS.md` had **rejected** step-gating the day before, on the grounds that it buys its saving
with exactly that green-and-measured-nothing run. That objection is right and is answered rather
than overridden — the entry is rewritten with the 3 things that answer it, and the question is now
a correctness one rather than the cost one it was.

## Measurements, so nobody repeats them

| | |
|---|---|
| the defect, before any change | at PR #14's head `bb3a775` (one changed file, `CLEANUP-LOG.md`): **2** `gates` check runs, **0** `controls`, read from `repos/.../commits/<sha>/check-runs` |
| the fix, on the runner | control PR #17 head `05fc528a`, **one** `CLEANUP-LOG.md` line. `pull_request` run 32721384791 → `controls` **success**, all 5 suites and all 4 toolchain installs `skipped`. `push` run 32721380341, **same commit** → `controls` **success**, all 5 suites **ran** |
| wall clock | skipped run **7s**; full run on the same commit **627s** |
| mergeable | `mergeable.py 17` exit 0, both required checks green at the head |

The two rows of the second measurement are the point: the same tree gets an unconditional full run
on the push, so a filter that is wrong is wrong for **at most one merge**, not indefinitely.

## The old per-path drift gate is gone, and what replaced it is stronger

The ticket asked that "the one-path-from-one-trigger mutant still dies". **Its subject no longer
exists** — there is one filter, not two `paths:` blocks — so `--selftest` would have reported it
*void*, which it already treats as a failure rather than a pass.

The filter is spelled **once**, as `FILTER_PREFIXES`/`FILTER_EXACT` in `ci_minutes.py`, so drift is
impossible rather than gated. What replaces the mutant pins the FACT instead of the spelling: every
entry must redden some pinned path when deleted. Both directions measured — an entry no pin depends
on reddens the selftest, and so does a `matches_filter` that ignores its own parameters (the
rule-12 addendum: a check whose expectation is the same object as its subject cannot fail).

## `--path-filter` is now a HISTORICAL instrument, and its docstring says so

Its verdict rested on the run's mere existence: *GitHub dispatched a `pull_request` workflow only
when its filter matched*. **That premise is false from 2026-08-24.** It now reports only the half it
ever measured — did the latest push touch a filtered path — and names itself historical. Do not
quote a `no-match` row as "this run was bought by the accumulated diff" for any run after that date.

## 5 review rounds, 9 findings, and 8 of them one family

Every round found a real defect. The family, in the reviewer's order:

1. the first `jobs` entry only — a second `ubuntu-latest` job with an unguarded gate passed
2. a scalar `steps:` **raised** `TypeError` instead of reporting
3. unparseable YAML **raised** `ScannerError`
4. `gate_census` — which `_selftest` runs **first** — still had the bare loader, so a malformed live
   workflow tracebacked ahead of every diagnostic written for it
5. `jobs: 1` / `jobs: []` / no `jobs:` became `{}`, publishing **0 gates at exit 0**
6. `--gates --json` returned 0 before the refusal
7. pyyaml missing **raised** — the handler was at a caller, not at the parse
8. `read_text()` **raised** `OSError` — one line before the loader that exists so nothing raises
9. and one that is not of the family: the guard was accepted by **containment**, so
   `${{ ... != 'false' && false }}` passed while skipping every gate

**The generalisation, and it is the thing worth keeping:** *a check that raises produces no verdict
at all, and a check that reports a confident zero produces a wrong one — both are worse than a red
row, and both hide behind a green suite.* Every one of 1–8 was a guard written at a caller rather
than at the address the failure happens (rule 12), and each was found only because the previous
round's fix moved the traceback one function along. If this file grows another reader of a
workflow, put it behind `_parse_workflow`/`_workflow_jobs`/`_job_steps` — that is what they are for.

Finding 9 is the other rule: the guard's own text is not the guard. It is matched **whole** now,
against a closed set of 2 accepted expressions.

## Two defects in the REVIEW PROCEDURE itself, measured here

Neither is in this ticket's scope; both cost time and both are reproducible.

**The poll believes a head it has not checked.** `.agents/skills/work/SKILL.md` reads `$HEAD` once
at the top. Run straight after `git push`, `gh pr view` still returns the **previous** head for a
few seconds, so the poll matched the *previous round's* review and printed `LANDED by review object
at eff4821` while the local `HEAD` was `822f488`. Reading the head once is right; believing it
without an independent statement of what it should be is rule 12's addendum. **The fix is one line:
pass the expected sha and refuse to poll until the API agrees.** The same race hits any
check-runs poll — it reported a completed, green `gates`/`controls` pair for a commit that was not
the one just pushed.

**`gh api -f body="…"` executes backticks.** #80, on the procedure that documents #80: a reply
posted that way came out with three words silently deleted. Replies must go through a file —
`gh api --input <json>` — and the round trip should be compared, not assumed.

## What was deliberately NOT done

- **`main`'s required-check list is untouched.** The ticket records the narrowing to `gates` as the
  operator's action; this makes it unnecessary rather than performing it.
- **No starter, rubric or run artifact touched.**
- **No finding number allocated.** The 2 procedure defects above are the orchestrator's to number
  and file if they are worth findings.
