---
name: work
description: "Work one item from the open-work queue end to end: read the ticket, do it, verify it in both directions, open a pull request, address the review, and hand it back for the orchestrator to verify and merge. Invoked as /work <id>."
when_to_use: "You have been dispatched to do a single queued task and given its id. Also use it yourself when picking up work from the queue rather than reconstructing the procedure."
argument-hint: "<task-id>"
---

# Work one task

**Authoritative files: the ticket at `tasks/<id>-*.md`, and `AGENTS.md`.** If this skill and
either disagree, they win and this skill is the bug.

> **The ticket is the brief. There is no second brief.** Everything you need is in the ticket
> or in the documents it names. If you were dispatched with extra instructions in a message,
> that is a defect in the ticket — **write what you learned back into the ticket before you
> finish**, with `tasks.py note <id> -` (§5). A brief delivered in a message dies with the
> session.

## 1. Read, in this order

1. `AGENTS.md` — always-loaded rules. Not optional; several were paid for with lost trials.
2. The folder-scoped `AGENTS.md` for wherever the ticket sends you (`eval/`, `eval/judge/`,
   `research/`). Each holds rules that apply only there.
3. `python3 eval/tools/tasks.py show <id>` — the ticket, in full, including anything a previous
   agent or the orchestrator appended to it.
4. Whatever the ticket's `refs` names. Cite by path; two files are named `IMPROVEMENTS.md`.

Then `python3 eval/tools/tasks.py start <id>`.

**The ticket's status is how everyone else knows where this work is.** Five values, and you
move it through four of them; the orchestrator sets the fifth:

| status | means | who sets it |
|---|---|---|
| `todo` | nobody has it | `add` |
| `in_progress` | you are working it | **you**, `tasks.py start <id>` |
| `in_review` | a pull request is open and the review loop is running | **you**, `tasks.py review <id> "<pr url>"` (§6) |
| `in_testing` | you are finished with it; it is waiting on the orchestrator | **you**, `tasks.py testing <id> "<evidence>"` (§7) |
| `done` | merged | the orchestrator, at merge |

`check` fails an `in_review` ticket that names no pull request — the state exists so the PR is
reachable from the ticket without reading the queue.

## 2. Know where you are standing

You run in an **isolated git worktree**. Three consequences bite every time:

| | |
|---|---|
| **The queue is shared** | `tasks.py` resolves `tasks/` to the **main checkout**, so your `start`/`done`/`add`/`note` land in the one real queue and appear as uncommitted changes *there*, not on your branch. That is deliberate (#94). **`Edit` and `Write` cannot reach the shared checkout at all** — worktree isolation refuses them — so `tasks.py` is the only way to touch a ticket, and it is enough. |
| **Your copy of a tool may be stale** | Your worktree was forked at some commit. If `main` has moved, your `eval/tools/*.py` is older. A pre-migration `tasks.py` once wrote an unparseable task file. When in doubt run the tool from the main checkout by absolute path. |
| **`eval/runs/` does not exist here** | It is gitignored. Read stored evidence by absolute path from the main checkout. |

**Do not allocate a finding number. Hand the finding to the orchestrator.**

Write the finding — the claim, the measurement, the control, everything — in your ticket, and say
in your report that it needs a number. The orchestrator allocates it against `main` at merge time,
where every concurrent branch is visible.

This was tried the other way and measured. Agents were told to re-read the highest number from
`main` immediately before taking one. **On 2026-08-23 that produced fourteen collisions**, and one
task collided *three times in a row* — written as #133, renumbered to #135, renumbered again to
#136 — because at this parallelism `main` moves in the window between reading it and committing.
Re-reading is not a fix for a race; it just narrows it.

The cost of handing it over is one line in your report. The cost of a collision is a renumber
across the body, the index row, and **every citation** — and a citation that still resolves, now
pointing at a stranger, which no check can see.

## 3. Do the work — the standard, not the steps

The steps are the ticket's. These are the properties every result here is held to:

- **Establish the broken state first.** A control run after the fix tests the fix, not the claim
  (#60). If you cannot make it fail, you have not measured it.
- **Pin in both directions.** Green proves nothing without a red. A mutant asks whether a check
  *can* fail; only a **variant** asks whether it can still *pass* on an input it mishandles
  (rule 15) — and every false negative adjudicated here has been of the second kind.
- **Prove the extraction before believing a census.** Not the whole set: one row whose true value
  you can state in advance. A census returning one value across a population it exists to
  discriminate is reporting the instrument, not the population.
- **Read unpiped.** A pipeline's exit status is the last stage's, and `|| true` turns an error
  into a plausible in-range number.
- **Read `agent.final_text`** when the ticket concerns a trial. Subjects have twice diagnosed
  harness defects in a paragraph nothing reads.
- **A negative result closes a task.** *"No pair resolves, here is the measured gap"* is a
  result. *"The experiment did not finish"* is not.

## 4. What you may not touch without the ticket saying so

| Never | Why |
|---|---|
| `eval/starters/*/`, `template*/` | The **product** — what a building agent reads. Editing one is a regime boundary: `verify_blind.py`, `starter_parity.py`, `starter_gate_control.py`, and a note in `eval/RUNS.md`. |
| `eval/findings/`, `eval/FINDINGS.md` | The archive. A number published and later proven wrong **stays**, marked. |
| Regime boundaries in `eval/RUNS.md` | They say which runs may be compared with which. |
| Files another agent is editing | Ask the orchestrator, or file a task. A conflict in a doc that states what is true now costs more than the edit is worth. |

## 5. Land the work on a branch

In the same session as the work:

- Update the docs the change makes stale. `README.md` and `DECISIONS.md` state what is true now;
  replace superseded content rather than annotating it.
- Something that ran and measured nothing is a numbered finding.
- Run the gates unpiped: `docstat.py --sweep`, `tasks.py check`, and whatever the area's own
  `AGENTS.md` names.

**Commit on `task-<id>-<slug>`.** Use `git commit -F` with a file: backticks in `-m` are executed
by the shell and silently strip text (#80).

**Never merge.** Nothing below changes that — a review is a second opinion on the code, and the
orchestrator's verification against the artifacts is the measurement.

## 6. Open the pull request, and address the review

This repository is `teonimesic/game-stack-bakeoff`, `gh` is authenticated, and CodeRabbit is
installed and reviews automatically on open. **No API route can tell you the app is authorised
before you try** — `/repos/../installation` needs an App JWT, `/repos/../hooks` is empty because
Apps do not use repo webhooks, and `/user/installations` is 403 under `gh`'s token. Opening the
PR is the test (`tasks/108`).

```bash
git push -u origin task-<id>-<slug>
gh pr create --base main --head task-<id>-<slug> \
  --title "Task <id>: <the ticket's title>" --body-file <a file you wrote>
python3 eval/tools/tasks.py review <id> "<the URL gh printed>"
```

**`--body-file`, never `--body`** — the body will contain paths, flags and code, and backticks in
an argument are command substitution (#80). Put in it: the ticket id, its `done_when` verbatim,
what you established with the numbers, and the control in both directions. The reviewer is
configured to read `tasks/`, so it can check the diff against the brief — but only if the PR says
which ticket it is.

### Waiting for the review

**Bounded, and pinned on a case whose answer you already know.** The address is the full 40-character
`commit_id` the reviews API returns, compared against the sha GitHub thinks is the head — not the
5-character abbreviation in the walkthrough text, which is what made a poll loop report *"not yet
reviewed"* through 8 polls after the review had landed (`tasks/108`, AGENTS.md rule 12).

```bash
REPO=teonimesic/game-stack-bakeoff
PR=<n>
HEAD=$(gh pr view "$PR" --repo "$REPO" --json headRefOid --jq .headRefOid) || exit 1
[ ${#HEAD} -eq 40 ] || { echo "no head sha - this is an error, not a poll result"; exit 1; }
gh api "repos/$REPO/pulls/$PR/reviews" \
  --jq "[.[] | select(.user.login==\"coderabbitai[bot]\") | .commit_id] | index(\"$HEAD\") != null" \
  || exit 1
```

It prints `true` or `false` and exits 0 either way, so read the **word**, not the exit code — and
never wrap it in `|| true`, which would turn an API failure into a plausible `false` that polls
forever. Verified against the merged PR #1 on 2026-08-23: `true` for the head it was reviewed at,
`false` for `941e5f5`, the commit that was pushed and never reviewed.

**All three guards are load-bearing.** If `gh pr view` fails, `$HEAD` is empty — and `jq`'s
`index("")` on an array of shas is `null`, measured, so the query answers `false` about a
question it never asked, and the loop polls to its deadline reporting a review state inferred
from a read that failed (rule 2). Check the exit status **and** that 40 characters came back;
either alone leaves the other hole open. The `|| exit 1` on the query itself is the same rule
one line down: an API that is failing must stop the loop, not quietly contribute a `false` to it.

**How long it takes scales with the diff, so do not size the wait off one number.** Both
measurements, from the 2 pull requests this repository has had:

| PR | diff | acknowledged | review posted |
|---|---|---|---|
| #1 | 2 files | 31s | **2m 30s** |
| #2 | 17 files, 615 insertions | 49s | **6m 15s** |

| | |
|---|---|
| poll | every 30s |
| give up after | **15 minutes** per round — 2.4x the slower of the two. If a diff much larger than 17 files takes longer than that, the bound is wrong and the evidence is in the PR: say so rather than extending it in place |

### The two ways this deadlocks, and what you do

**1. The reviews auto-pause.** CodeRabbit pauses a branch it considers under active development
— *"To avoid overwhelming you with review comments due to an influx of new commits"*. **This is
the most likely way the flow hangs, and it is triggered by being productive.** The notice is in
the PR's issue comments, not in the reviews:

```bash
gh api "repos/$REPO/issues/$PR/comments" \
  --jq '[.[] | select(.body | contains("review paused by coderabbit.ai"))] | length'
```

It prints a count, in one process — no pipe whose exit status would be the last stage's, and no
`grep` that exits 1 on zero matches and reads as a failure. Verified 2026-08-23 in both
directions: `1` on PR #1, which carries the notice, and `0` on PR #2, which does not.

If it is paused, post `@coderabbitai review` as a PR comment and resume polling. **Push once per
round, not once per fix** — batching the fixes is what keeps the pause from firing at all.

**2. The wait expires.** Do not extend it and do not loop again. Say in the PR thread that you
waited 15 minutes and got no review, set the ticket to `in_testing` with that fact in the
evidence, and report it. **A no-review is a result the orchestrator can act on; an agent still
waiting is not.**

**Rounds cost more than pushes.** The plan allows 10 included reviews per hour and a single PR
consumed 4 of them over 3 rounds — the counter went 9, 8, 6, so a round can cost 2. Budget
**two review rounds per task**; if the third round is still finding things, that is a signal to
hand back and say so rather than to keep spending an hour's quota on one ticket.

> **The counter is not a durable artifact.** `tasks/108` read it out of the review body; on
> 2026-08-23 it was no longer anywhere in PR #1's stored reviews or comments, because CodeRabbit
> edits its summary comment in place. Do not build a check on reading it — bound the rounds
> instead.

### Which recommendations to act on

**The reviewer is a second reader, not an authority.** This project's standard is higher than
*the reviewer said so*, and the two useful comments PR #1 received both came from rules this
repository supplied to it (`AGENTS.md` through `code_guidelines`, and a `**/*.md` path
instruction) rather than from generic review.

| the comment | what you do |
|---|---|
| Names a real defect — a wrong path, a check that cannot fail, a false statement | Fix it, push, and let the next round see it |
| Contradicts `AGENTS.md`, a folder-scoped `AGENTS.md`, or a recorded `DECISIONS.md` entry | **It is wrong. Do not comply.** Reply in the thread naming the rule and why, and leave the code alone |
| Would loosen a test, widen an assertion, or excuse a failure | **Refuse**, and say so. Every reason not to count a failure is a channel a bug can widen (rule 7) |
| Style, wording, reordering in a document | Ignore. The prose here is the product and `.coderabbit.yaml` already tells it so; a comment of this shape is a config defect worth a task |
| Touches `eval/starters/*/` | Never act on it without the ticket saying so. Editing a starter is a regime boundary |

**Reply to what you decline.** An unanswered comment is indistinguishable from an unread one, and
the orchestrator would have to re-derive your reasoning from the diff.

## 7. Hand it back

**Write what you learned into the ticket BODY first, then hand it back.**

```bash
python3 eval/tools/tasks.py note <id> - <<'NOTE'
What the next agent would otherwise re-derive. Prose, lists, `backticks`, several
paragraphs — whatever it takes.
NOTE
python3 eval/tools/tasks.py testing <id> "what established it"
```

`note` appends a dated section to the ticket in the **main checkout's** queue and rewrites no
other byte of it, so it works from your worktree where `Edit` cannot reach and a committed edit
to your own copy would only offer the merge a conflict. `-` reads the section from stdin, and a
**quoted** heredoc (`<<'NOTE'`, not `<<NOTE`) is what carries backticks and newlines in
unexpanded.

Do not put the account in `established_by` instead. That field is one unbroken line of prose in
YAML frontmatter, it cannot contain a backtick (#80), and it is not where the next agent looks —
tasks 105 and 106 each emptied a session's findings into it because `note` did not yet exist
(task 113).

Evidence means a measurement, a control, a file — never "completed". **No backticks in that
string**: they execute as command substitution and silently strip text from a durable record
(#80).

`in_testing` is the signal, and it is the whole reason the state exists: the orchestrator can see
which branches are its turn without opening a single pull request. **You never set `done`** — that
is the orchestrator's, at merge, after verifying the result against the artifacts.

## 8. Report

To `main`, in this shape:

- what you **established**, with the numbers, and how
- the control in **both** directions
- what you could **not** establish — stated as plainly as the rest
- what you changed, what you deliberately did not, and why
- anything you filed, and anything the next agent must not re-derive

**Do not round off uncertainty.** A number that is wrong is worse than no number here, because
it gets acted on.
