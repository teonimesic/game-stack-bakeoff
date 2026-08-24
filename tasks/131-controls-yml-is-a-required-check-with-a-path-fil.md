---
id: 131
title: controls.yml is a required check with a path filter, so a PR touching neither eval/ nor .agents/ can never merge
status: in_review
priority: 1
refs: '#162, .github/workflows/controls.yml, eval/tools/ci_minutes.py, DECISIONS.md'
done_when: A pull request changing ONLY tasks/ or README.md reports a green `controls` check and is mergeable. `ci_minutes.py --selftest` green, with the one-path-from-one-trigger mutant still dying. `.github/workflows/README.md` states where the filter now lives, and DECISIONS.md records whether `controls` is required.
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/16
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
