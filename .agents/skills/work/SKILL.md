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

> **Run them against what you are about to push, not against your worktree — which means STAGING
> FIRST, not looking at a status line.**
>
> ```bash
> git add -A                       # or the paths you mean; the point is that nothing is left out
> git status --porcelain           # MUST be empty of ` M`/`??` rows before you continue
> <run the gates>
> git status --porcelain           # MUST still be empty: a gate that rewrote a file un-stages it
> ```
>
> Reading a status line proves nothing on its own — `git status` reports a difference, it does not
> make the gate read the index. The second check is the one people skip and it is not optional: a
> formatter or a producer that rewrites a file during the gate run leaves the fix unstaged, which
> is the same defect one step later.
>
> A gate reads the files on disk; a commit records the index,
> and those are the same thing only until they are not. Merging `main` and then repairing what
> the merge broke is where they part: `git commit --no-edit` finishes the merge from the **index**
> and silently leaves any edit made after the conflict resolution behind. That happened on this
> branch — `ci_minutes --selftest` was green locally and red in CI on the same second, because
> the fix it was reading had never been staged. It is `AGENTS.md` rule 12 with the worktree as
> the wrong address.

**Commit on `task-<id>-<slug>`.** Use `git commit -F` with a file: backticks in `-m` are executed
by the shell and silently strip text (#80).

> **Name that file for the ticket, and read back what the commit got.** The scratchpad outlives
> nothing but is not empty: on 2026-08-23 a `git commit -F .../commitmsg2.txt` on this branch
> picked up a **previous session's** file and shipped a commit titled *"Task 117, review round
> 1"* onto task 120's work, at exit 0 (`tasks/120`). That is rule 12 against the author — a
> correct method aimed at an address nobody verified — and `-F` is the one place it is silent,
> because a message file that exists is indistinguishable from the one you meant. `git log
> --oneline -1` after every commit costs nothing; `--amend -F` is the repair while it is
> unpushed.

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

> **The title and body you write here BECOME the commit message on `main`.** The repository is
> squash-only and takes the squashed commit's subject from the pull request title and its body
> from the pull request body. Your review-round commits do not survive the merge; this text does,
> and it is what `git log` will show for the whole task. Write it as the permanent record of what
> was established and what it cost — not as a note to the reviewer — and re-edit it with
> `gh pr edit <n> --body-file <file>` if the review changed what you established.
>
> **Read back what the pull request got**, exactly as §5 reads back what the commit got, and for
> the same reason: `--body-file` is silent about picking up the wrong file, because a file that
> exists is indistinguishable from the one you meant. `gh pr view <n> --json title,body` costs
> nothing, and this body is a permanent commit message.

**Keep the branch current with `main`.** A pull request that is behind its base was tested against
a head nobody will merge, and the orchestrator's `mergeable.py` refuses it — two changes can each
be correct and jointly red, which is exactly how `main` broke on 2026-08-23. If `main` moves while
you are in the review loop, merge it into your branch, push, and let the checks re-run at the head
that will actually land.

### Waiting for the review

**1 command, and the address is an argument to it.** From the worktree whose branch it is:

```bash
python3 eval/tools/pr_review_state.py --pr <n> --branch task-<id>-<slug> \
    --expect-head "$(git rev-parse HEAD)" --wait
```

It prints 1 line per poll, and every line names the pull request, the branch and the full head
sha:

```text
#18 task-127-poll-asserts-its-branch head=<40 hex> verdict=IN_FLIGHT by_review=0 by_comment=0 in_flight=1 failed=0 elapsed=90s
```

**Read the word.** `DECISIONS.md`, *An agent hands back a pull request*, is the authority on what
counts as reviewed and holds the per-pull-request evidence; the tool's docstring states every
guard and why it is there. If they disagree, `DECISIONS.md` wins.

| verdict | exit | what you do |
|---|---|---|
| `LANDED_REVIEW` | 0 | the reviewer wrote comments. Read them and work the round |
| `LANDED_COMMENT` | 0 | it finished and had nothing to say. You are done unless you have pushed since |
| `REVIEW_FAILED` | 14 | a round started and **died**. This head has not been reviewed. See the table below |
| `NOTICE` | 12 | a deadlock notice, printed after `notice=`. See the table below |
| `UNRESOLVED` | 13 | the wait expired. Say so in the thread, hand back `in_testing` with that fact |
| — | 1 | a refusal — `WRONG PR`, `STALE HEAD`, `NO HEAD SHA`, `EXPECTED HEAD NOT A FULL SHA`, or `gh` failed. **Stop.** None of these is a poll result |

> **The tool asserts the branch as well as printing it, and the assertion is the guard.**
> `tasks/127`: the recipe this replaces hardcoded `PR=<n>`, printed only a head sha, and was
> copied into a scratchpad file under a generic name in a directory shared with every concurrent
> session. A second agent wrote its own copy over the same path, and the first loop spent 16
> polls reporting `not yet` at exit 0 about the second agent's pull request. Run against those
> same 2 pull requests today, the old recipe answers `LANDED by review object at <sha>` for
> **both** #9 and #10, with nothing in either line to tell them apart; the tool answers
> `WRONG PR: #10 is on branch 'task-124-ci-path-filter-and-minutes'` at exit 1.
>
> **The property, not the instance: an assertion fails closed at the moment of use, and a printed
> line is only as good as the reader who happens to look at it.** Where a wrong answer is
> consumed by the next step of a procedure rather than by a person — and the next step here is
> *read that review and act on it* — printing is an audit trail, not a guard. It is still worth
> printing, because what an instrument did is worth more than the confidence you had in it.

> **Pass `--expect-head`, and pass the full sha.** `gh pr view` returns the previous head for a
> few seconds after a push: a poll run straight after `git push` reported `LANDED` at a commit
> that was no longer under review, and the same race returned a green checks answer about it
> (#165). The flag makes the tool refuse to answer until the API agrees. A `sleep` makes that
> race less likely and leaves it fail-open.

**The wait is bounded on silence, not on a clock.** A fixed 15-minute bound was measured wrong:
task 130's agent polled 29 times, handed the work back as ready, and the review arrived at
**19m26s** on a 4-file diff carrying 4 threads and a Major. Raising the constant is the same
defect at a larger value, so the bound is on the in-progress marker instead — 20 minutes while no
round has ever been seen in flight, 60 minutes once one has, and the observation latches because
CodeRabbit rewrites the summary comment mid-round. Expiry is `UNRESOLVED` and loud. **A no-review
is a result the orchestrator can act on; an agent still waiting is not.**

**Do not verify this tool with this tool.** `python3 eval/tools/pr_review_state.py --census`
prints which arm fires at every pull request's head, and `DECISIONS.md` states that answer per
pull request from before the tool existed — that is the known-good row rule 12 asks for.
`--selftest` (offline) and `eval/tools/pr_review_state_mutants.py` are the pinned halves.

### The ways this deadlocks, and what you do

A `coderabbitai[bot]` comment carrying a GitHub alert callout is what produces both `NOTICE` and
`REVIEW_FAILED`, and the tool prints the heading after `notice=`. **Every one of these states its
own remedy in its body — read it.** The table is its own census: a heading that is not a row here
is new, and the row to add is what you learn from that comment.

**The middle column is the one to read**, because the headings do not mean the same kind of thing.
Three of them say a round has **not started**; one says a round started and **died**, and that one
leaves behind exactly the artifact a clean review leaves — a summary comment sitting at your head
sha.

| heading | what it implies about your head | what you do |
|---|---|---|
| **Reviews paused** — *"this branch is under active development … to avoid overwhelming you with review comments"* | not reviewed, nothing is coming. **Triggered by being productive** | post `@coderabbitai review` (or `@coderabbitai resume` to restore automatic reviews), then poll again |
| **Review limit reached** — *"you've used all N included reviews currently available"* | not reviewed; the org's allowance is spent and the body says how long until one frees up | wait out the stated interval, post `@coderabbitai review`, poll again — **do not restart the round budget** |
| **Review skipped** — *"No new commits to review since the last review"* | already reviewed. Not a deadlock: you asked for a review of a head that has had one | nothing. Push first, then ask |
| **Review failed** — *"the head commit changed during the review"* | **a round started and died. Not reviewed, and the summary it left at your head looks clean** | post `@coderabbitai review` **once**, then poll again with `--ignore-notice` |

**Merging `main` into your branch mid-review produces the last row**, and §6 asks you to keep the
branch current — so expect it. The poll answers `REVIEW_FAILED` at exit 14, never a landing: the
summary a dead round leaves behind names your head and reads as clean.

**Once you have acted on any of these, poll again with `--ignore-notice`** — otherwise the wait
stops on the comment you just answered, which CodeRabbit leaves in place until it next rewrites
the summary. The flag governs **stopping only**: it can never turn a notice or a failed round into
a landing, and a remedy that never takes expires as `UNRESOLVED`. The tool's docstring says why.

**A notice is a diagnostic, and it is stale the moment anything changes.** CodeRabbit edits its
comments in place, so a heading outlives the state it described. That is why `LANDED_REVIEW`
outranks everything: a stale *Reviews paused* or *Review failed* beside a real review object is
still a review.

**Push once per round, not once per fix.** Batching is what keeps the pause from firing at all,
and under a spent allowance it is the difference between one round and none.

**The ceiling is 5 rounds per task, and it is a ceiling rather than a target.** Stop as soon as a
round comes back clean. If you reach 5 and it is still finding real defects, hand back and say so
— the ticket is bigger than it was filed as, and the orchestrator needs to know that.

**Rounds are drawn from a pool shared with every other agent, and a round can cost more than one
review.** One PR consumed 4 reviews over 3 rounds. **You cannot see the pool** — the counter that
once showed it is written into a summary comment CodeRabbit overwrites in place, and it appears
in none of the stored pull requests today (#158). Keep your own rounds few because they are
shared, and if reviews stop arriving, treat it as the pool being exhausted rather than as a clean
review.

### Which recommendations to act on

**Keep going until the review has nothing left to say, up to 5 rounds.** A comment naming a real
defect is fixed, pushed, and seen by the next round. **A clean round is the goal**, not an
accident — hand back when the reviewer stops finding things, not when you run out of patience.

**Do not assume your standard is higher than the reviewer's.** It is a second reader with no
stake in what you just wrote, which is exactly what makes it useful, and on this repository its
comments have found real fail-open defects, a control that was green for the wrong reason, and a
gate that broke the very rule it was written to enforce. **The default is that it is right and
you are wrong.** Start there and let it change your mind, rather than treating each comment as
something to get past.

**Declining is for a conflict you can demonstrate**, not for disagreement. If you decline, the
reply has to carry the evidence — the rule it contradicts, the measurement that refutes it, the
mutant that shows its suggestion fails. A decline with only an opinion behind it is a comment you
lost an argument with.

| the comment | what you do |
|---|---|
| Names a real defect — a wrong path, a check that cannot fail, a false statement | Fix it, push, and let the next round see it |
| Contradicts `AGENTS.md`, a folder-scoped `AGENTS.md`, or a recorded `DECISIONS.md` entry | **It is wrong. Do not comply.** Reply in the thread naming the rule and why, and leave the code alone |
| Would loosen a test, widen an assertion, or excuse a failure | **Refuse**, and say so. Every reason not to count a failure is a channel a bug can widen (rule 7) |
| Readability of a document — hard to follow, more complex than its content warrants, over-specific, narrating past events, or explaining itself | **Act on it.** `.coderabbit.yaml` asks for these on purpose since 2026-08-23. A document states the choices in force, the current state and how to do things; it is not a log of what happened or of its own contents |
| Touches `eval/starters/*/` | Never act on it without the ticket saying so. Editing a starter is a regime boundary |

**Reply to what you decline.** An unanswered comment is indistinguishable from an unread one, and
the orchestrator would have to re-derive your reasoning from the diff.

> **Compose the reply in a file and send it as JSON, then read back what the API stored (#166).**
> `gh api -f body="…"` is an argument, so backticks in it are command substitution and the words
> between them vanish silently — a reply lost 3 words that way. `#80` is about `git commit
> -m`; the flag was different, so the rule did not match, in the file that documents `#80`.
>
> ```bash
> jq -n --rawfile b reply.md '{body: $b}' > reply.json
> gh api "repos/$REPO/pulls/$PR/comments/<comment id>/replies" --input reply.json --jq .id
> ```
>
> Then fetch the stored body and `diff` it against `reply.md`. **Compare what you sent with what
> the API kept, never with what you meant to send** — the corruption is invisible in the
> transcript, because the shell ate the text before `gh` ever saw it.

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
YAML frontmatter, and it is not where the next agent looks — tasks 105 and 106 each emptied a
session's findings into it because `note` did not yet exist (task 113). `testing` and `done`
now **refuse** a multi-line evidence string and name `note` in the message, rather than writing
a wall of prose into frontmatter.

Evidence means a measurement, a control, a file — never "completed". An empty evidence string is
refused. **A backtick cannot go in that argument** — it executes as command substitution before
`tasks.py` runs and silently strips text from a durable record (#80). Pass it on stdin instead:
`testing <id> -` reads one line from stdin exactly as `note <id> -` reads a section, and the
sentinel means the same thing in both. It used to mean the same thing in neither: `done <id> -`
stored the literal one character `-` at exit 0 over 2280 characters of redirected account, and
closed the ticket while doing it (task 120).

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
