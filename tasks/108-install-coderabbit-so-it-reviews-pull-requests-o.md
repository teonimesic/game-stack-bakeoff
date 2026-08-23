---
id: 108
title: Install CodeRabbit so it reviews pull requests on this repository
status: done
priority: 1
refs: .coderabbit.yaml (does not exist yet), .github/ (does not exist yet), https://github.com/teonimesic/game-stack-bakeoff, .claude/skills/work/SKILL.md, .claude/skills/dispatch/SKILL.md
done_when: a real pull request on this repository has received a CodeRabbit review and the review comment is quoted in the report; .coderabbit.yaml is committed and its settings are justified against what this repository actually is; and the exact steps a human must perform outside the repository are written down in the ticket, distinguished from what was done inside it
established_by: 'PR #1 on teonimesic/game-stack-bakeoff was opened and reviewed by coderabbitai[bot] on 2026-08-23: acknowledged 31s after opening, finished review 119s later, plan Pro Plus, Configuration used: Path: .coderabbit.yaml, profile CHILL, both changed files processed so the new exclusions did not swallow it. Its 1 actionable comment was a true positive against this project''s own digits rule and is quoted in full in the ticket; fixed in 5df349a. .coderabbit.yaml is committed on branch task-108-coderabbit and validated against the published schema in both directions - the real file passes and 5 deliberately broken variants all fail. Corrections recorded in the ticket: eval/runs/** is gitignored and matches 0 tracked files while the committed stored evidence is eval/instrfollow/runs/ at 115 records, and all 3 GitHub API routes for detecting the installation return 401/403/empty regardless of whether the app is installed, so a pull request is the only test. Branch pushed and PR left open and unmerged for the orchestrator.'
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

## Measured at dispatch, 2026-08-23 — the repository is PRIVATE

    gh repo view --json visibility,licenseInfo
    {"licenseInfo":{"key":"mit","name":"MIT License"},"visibility":"PRIVATE"}

MIT-licensed and private are independent settings, and CodeRabbit's plans distinguish them: its
free tier is generally aimed at **public** repositories, with private repositories on a paid or
trial plan. The operator said they have signed up, so a plan may already cover this.

**Do not buy anything and do not start a trial that converts to a charge.** If the review does not
arrive because the plan does not cover a private repository, that is a complete and useful result:
say so, name what plan would be needed, and leave the decision to the operator.

---

## RESULT, 2026-08-23 — the app IS authorised, and a real PR was reviewed

**PR #1, https://github.com/teonimesic/game-stack-bakeoff/pull/1** — the first pull request ever
opened on this repository. CodeRabbit acknowledged it **31 seconds** after it was opened and
posted a finished review **119 seconds** after that. The plan covers this private repository:

    Configuration used: Path: .coderabbit.yaml
    Review profile: CHILL
    Plan: Pro Plus
    Included review availability: Your plan provides up to 10 included reviews
    per hour; 9 remain after this review.

Both changed files were processed — `.coderabbit.yaml` and `DECISIONS.md` — so the exclusions
written in the same PR did not swallow it.

**The one actionable comment, quoted in full** (inline on `DECISIONS.md:1165`):

> _📐 Maintainability & Code Quality_ | _🟡 Minor_ | _⚡ Quick win_
>
> **Write numeric counts as digits.**
>
> This new live policy uses `single`, `one`, `three`, and `six` as counts. Replace them with
> digit forms such as `1`, `3`, and `6`.
>
> Also applies to: 1172-1172, 1186-1189, 1191-1194, 1201-1205
>
> _Source: Coding guidelines_

**That is a true positive, and it is against this repository's own rules rather than a style
guide.** `AGENTS.md` requires a count in a live document to be in digits, because no check can
read a cardinal spelled in words — the reason a stale findings figure survived 11 days. The
reviewer reached that rule through `knowledge_base.code_guidelines.filePatterns`, which is why
that key is set. Fixed in commit `5df349a`.

Merge risk was reported **Minimal**; the 5 pre-merge checks passed; no comment was made on
markdown prose.

## WHAT WAS DONE INSIDE THE REPOSITORY

Branch `task-108-coderabbit`, 2 commits, **not merged**:

- `dbb1299` — adds `.coderabbit.yaml`, and a `DECISIONS.md` section with 2 reversal conditions.
- `5df349a` — the digits fix the review asked for, and a record of what the first review did.

`.coderabbit.yaml` was validated against the published schema
(`https://storage.googleapis.com/coderabbit_public_assets/schema.v2.json`) in both directions:
the real file passes, and 5 deliberately broken variants — a misspelled `profile` enum, an
unknown key, `review_details` as a string, a bad `learnings.scope`, and a `path_instructions`
item missing its required `path` — all fail. `jsonschema` will not install on this machine
(homebrew python's `pyexpat` is broken), so the checker is a small recursive one; it is in the
session scratchpad and was **not** committed, because CodeRabbit reports `Configuration used:
Path: .coderabbit.yaml` in every review, which is a live per-run audit trail that a separate
offline gate would only duplicate.

## WHAT A HUMAN MUST DO AT GITHUB.COM

**Nothing. It was already done before this task ran** — the operator's sign-up had already
granted the app access to this repository, which is why PR #1 was reviewed. This section exists
so the next person does not have to rediscover it, and applies if access is ever revoked or a
second repository is added:

1. Go to **https://github.com/apps/coderabbitai** and press **Configure**.
2. Choose the account that owns the repository — **teonimesic**.
3. Under *Repository access*, either **All repositories**, or **Only select repositories** with
   **game-stack-bakeoff** ticked. Press **Save**.
4. Sign in at **https://app.coderabbit.ai** with the same GitHub account and confirm the
   repository is listed. A **private** repository needs a paid plan; this one is on **Pro Plus**.

Nothing has to be added to the repository for that step — no `.github/` directory, no workflow,
no webhook. The app posts as `coderabbitai[bot]`.

## CORRECTIONS TO THIS TICKET, for whoever writes the next one

**1. `eval/runs/**` cannot appear in a diff, and the ticket's premise for excluding it was
wrong.** It is in `.gitignore`; `git ls-files eval/runs` returns **0**. The committed stored
evidence that *can* dominate a diff is **`eval/instrfollow/runs/`, 115 tracked JSON trial
records**, which the ticket does not mention. Both are excluded in the config, but only one of
them was ever reachable. Rule 12: the address is an input to the check.

**2. Neither API route suggested in step 1 can answer "is the app authorised", and a third one
cannot either.** All three were run:

| route | result | why it cannot answer |
|---|---|---|
| `gh api /repos/OWNER/REPO/installation` | **401** `A JSON web token could not be decoded` | needs a GitHub **App** JWT. A user token gets 401 whether or not the app is installed |
| `gh api /repos/OWNER/REPO/hooks` | **`[]`**, exit 0 | GitHub Apps use app-level webhooks, not repository webhooks. `[]` is the expected answer either way |
| `gh api /user/installations` | **403** `You must authenticate with an access token authorized to a GitHub App` | `gh`'s token is an OAuth-app token, not an App user-to-server token |

**Opening a pull request is the only test available from the CLI.** Do not spend time on the
API routes; go straight to step 3.

**3. `path_filters` also drives a sparse checkout** (it is in the schema's own description of the
field). One positive pattern turns the list into an allowlist and hides everything unnamed —
including `.coderabbit.yaml`, i.e. the verification PR itself. Keep it exclusion-only.

## WHAT WAS NOT ESTABLISHED

- **Whether `markdownlint` or `languagetool` are noisy on this corpus.** `reviews.tools` is empty
  and 1 review over a 2-file diff is not a measurement. The reversal condition in `DECISIONS.md`
  says what would settle it.
- **Whether excluding the archives was necessary or merely prudent.** No PR has yet touched
  `eval/FINDINGS.md` or `eval/findings/`, so the false positives those exclusions were written to
  prevent have not been observed — only predicted from what `AGENTS.md` says lives there.
- **Whether keeping `tasks/` reviewable costs more than it gives.** Also predicted, not measured;
  its reversal condition names the observation that would decide it.

## STILL OPEN

The `done_when` is met, and this ticket is **closed**. `tasks/109` is unblocked: a PR on this
repository does receive a CodeRabbit review, so an agent told to wait for one will not wait
forever — 150 seconds end to end on a 2-file diff, and the plan allows 10 reviews per hour, which
is a real constraint on a parallel queue and `tasks/109` should account for it.

**PR #1 is left OPEN and unmerged** for the orchestrator, per `.claude/skills/work/SKILL.md`.

Filed while here: `tasks/111` — `AGENTS.md` says `template*/` is deleted, and 5 files of it are
still tracked on `main`.

## WHAT 3 REVIEW ROUNDS MEASURED, added after the first append

The PR ran to 4 commits and 3 review rounds. **2 actionable comments, both true positives, 0
false positives** — and the 2 arrived through the 2 different mechanisms this config sets up:

| round | head | comments | source it cited | what it caught |
|---|---|---|---|---|
| 1 | `dbb1299` | 1 | `Coding guidelines` | `DECISIONS.md` spelling counts as words against the digits rule |
| 2 | `5df349a` | 0 | — | *No actionable comments were generated* |
| 3 | `c7d4c34` | 1 | `Path instructions` | `README.md` saying the config "drops the archives" when `tasks/` is an archive it deliberately keeps |

The second comment, quoted:

> _🎯 Functional Correctness_ | _🟡 Minor_ | _⚡ Quick win_
>
> **Clarify that only excluded archive paths are dropped.**
>
> `tasks/` is an archive, but `.coderabbit.yaml` deliberately keeps it reviewable. Replace
> "drops the archives" with "drops the excluded archive paths" to match `DECISIONS.md`.
>
> As per path instructions, this comment addresses a false statement in the live Markdown
> document.
>
> _Source: Path instructions_

**Both of the useful comments came from rules this repository supplied.** A default
configuration would have had neither: the digits rule is in `AGENTS.md` and reached the reviewer
through `code_guidelines.filePatterns`; the *only-when-FALSE* rule is the `**/*.md` path
instruction. That is the argument for spending effort on the config rather than accepting
defaults, and it is now evidence rather than an argument.

**Rate limit, for `tasks/109`.** The plan allows **10 included reviews per hour** and every round
prints what remains. Across 3 rounds on this 1 pull request the counter read **9, then 8, then
6** — 4 of the hour's 10 spent on 1 PR, with the third round consuming 2. **The cost is per
review round, not per pull request, and it is not 1 per push.** Anything that sizes a parallel
queue should read the counter out of the review body rather than assume a rate.

**A defect in this session's own instrument, worth not repeating.** The script waiting for the
head commit to be reviewed compared a **7-character** sha against the walkthrough's
**5-character** abbreviation, so it reported "not yet reviewed" through 8 consecutive polls after
the review had landed. Rule 12 — the address is an input to the check — against a poll loop.

Final head of the branch is `941e5f5`; the last commit is the fix for round 3 and has not itself
been reviewed.

## FINAL STATE

`main` moved under the branch while PR #1 was being reviewed (tasks 102, 104 and 107 merged; task
107 rewrote `README.md` from 643 lines to 281). The PR read `mergeable=CONFLICTING` in
`DECISIONS.md` and `README.md`, both files this branch had edited, so `origin/main` was merged in
and the conflicts resolved: both sides had appended a new section and new reversal-condition rows
in the same place, and the README row was re-added in the tighter style the rewrite established.
The population counts were re-read rather than carried over — **673** tracked files, **173**
markdown, **117** python.

Branch head **4f95b99**, pushed. PR #1 now reads **mergeable=MERGEABLE, CLEAN**, is **open and
unmerged**, and is the orchestrator's to merge. `docstat.py --sweep` exit 0 and `tasks.py check`
exit 0 against the merged tree.
