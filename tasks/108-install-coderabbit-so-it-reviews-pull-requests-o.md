---
id: 108
title: Install CodeRabbit so it reviews pull requests on this repository
status: in_flight
priority: 1
refs: .coderabbit.yaml (does not exist yet), .github/ (does not exist yet), https://github.com/teonimesic/game-stack-bakeoff, .claude/skills/work/SKILL.md, .claude/skills/dispatch/SKILL.md
done_when: a real pull request on this repository has received a CodeRabbit review and the review comment is quoted in the report; .coderabbit.yaml is committed and its settings are justified against what this repository actually is; and the exact steps a human must perform outside the repository are written down in the ticket, distinguished from what was done inside it
---

The operator wants agent work reviewed by CodeRabbit before it is merged, and has already signed up. Nothing in the repository is configured for it: there is no .coderabbit.yaml, no .github/ directory, and no pull request has ever been opened here - agents hand back branches that the orchestrator merges directly. This task is the prerequisite for the whole review flow: until a PR on this repository actually receives a CodeRabbit review, changing the agent workflow to wait for one would make every agent wait forever.

WHAT THIS IS

CodeRabbit is a hosted code-review service that installs as a **GitHub App** on a repository and
comments on pull requests. The operator has already signed up for the service. What is missing is
the connection between the service and this repository.

There are two halves, and they fail differently:

| half | where it happens | who can do it |
|---|---|---|
| **authorising the app on the repository** | github.com, in the operator's account — the app is granted access to `teonimesic/game-stack-bakeoff` | **the operator only.** It is an account action on their machine and their identity |
| **repository configuration** | `.coderabbit.yaml` at the repo root | an agent |

**Read that table before starting.** The second half is committable work; the first is not, and no
amount of writing YAML makes a review appear if the app was never authorised.

STATE OF THE REPOSITORY, read 2026-08-23

    remote        https://github.com/teonimesic/game-stack-bakeoff.git
    gh auth       logged in as teonimesic (GH_TOKEN, gho_ token)
    .github/      does not exist
    .coderabbit.yaml   does not exist
    open PRs      none — `gh pr list` returns empty
    workflow      agents hand back BRANCHES; the orchestrator merges with `git merge --no-ff`

**No pull request has ever been opened on this repository.** That matters for the verification
step: you will be creating the first one.

WHAT SHOULD BE DONE

1. **Find out whether the app is already authorised before writing anything.** Do not assume
   either way — the operator said they signed up, which is not the same as having granted the app
   access to this repository. `gh api /repos/teonimesic/game-stack-bakeoff/installation` and
   `gh api /repos/teonimesic/game-stack-bakeoff/hooks` are two routes; a 404 on the first is
   informative, and so is a 403, and they mean different things. **Report which you got.**

2. **Write `.coderabbit.yaml`, and justify it against what this repository actually is.** Default
   configurations assume an application codebase. This is a research repository:

   - `eval/runs/**` is **stored evidence**, not source. Thousands of JSON records and per-trial
     copies of the starters. Reviewing it is noise, and it will dominate every diff that touches
     a run.
   - `eval/starters/*/` is **the product being measured**. A review comment suggesting an
     improvement to a starter is a suggestion to change the experiment — see the note in
     `AGENTS.md`. Whether to exclude these or merely flag them is a judgement; make it and say
     which and why.
   - `tasks/`, `eval/findings/`, `eval/FINDINGS.md`, `CLEANUP-LOG.md` and both `IMPROVEMENTS.md`
     are **archives**. They record what was believed at a time, including figures later retired.
     A reviewer that "corrects" a retired figure in an archive is wrong, and `AGENTS.md` says why.
   - The interesting review surface is `eval/tools/`, `eval/judge/`, `eval/*.py` and the
     always-loaded instruction documents.

   **Do not copy a config from a blog post.** Every exclusion you write should be one you can
   defend by naming what is in that directory.

3. **Prove it works, with a real pull request.** This is the `done_when`, and it is not optional:
   a configuration file that has never caused a review is exactly the shape this project calls a
   mechanism that runs and measures nothing. Open a small, genuine PR — the `.coderabbit.yaml`
   itself is the obvious candidate — and wait for the review. **Quote the review comment in your
   report.** If no review arrives, say so plainly and say what you checked; a null here is a
   result and closes this task with "the app is not authorised, and here is the exact thing the
   operator must click."

4. **Write down the human steps.** Whatever the operator has to do at github.com — the app URL,
   which repository to grant, which permissions — goes in this ticket under its own heading, in
   the order they must be done. That is the handoff, and a chat message is not one.

WHAT NOT TO DO

- **Do not change the branch protection or the merge settings on the repository.** The
  orchestrator merges; that is not yours to alter, and it is outward-facing.
- **Do not change `.claude/skills/work/SKILL.md` or `.claude/skills/dispatch/SKILL.md`.** The
  workflow change is `tasks/109`, and it is blocked on this one for a reason: an agent told to
  wait for a review that cannot arrive waits forever.
- **Do not sign up for anything, pay for anything, or authorise an app on the operator's
  account.** If a step needs their identity, it is a step for the ticket, not for you.

WHAT EACH OUTCOME MEANS

- **A PR gets a CodeRabbit review** — the task is done, and `tasks/109` is unblocked. Quote the
  review.
- **The app is not authorised** — also a complete result. Land `.coderabbit.yaml`, record exactly
  what the operator must do, and say clearly in your report that the verification could not run.
  Do **not** close this as done: leave it open with the blocker named, because the `done_when`
  asks for a review that happened.
- **The app is authorised but reviews nothing** — the most useful outcome to investigate. Check
  whether your own exclusions swallowed the PR you opened. That is a live failure mode of step 2
  and the reason step 3 exists.
