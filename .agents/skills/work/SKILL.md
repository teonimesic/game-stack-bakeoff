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

### Waiting for the review

**Bounded, and pinned on cases whose answer you already know.** The address is the full
40-character head sha — never the 5-character abbreviation in the walkthrough text, which is what
made a poll loop report *"not yet reviewed"* through 8 polls after the review had landed
(`tasks/108`, AGENTS.md rule 12).

**A landed review has 2 shapes, and a check that reads only the first one times out on the good
outcome.** When CodeRabbit finds nothing actionable it creates **no review object at all** — it
edits its summary issue comment instead. So *reviewed at this head* is: a `coderabbitai[bot]`
**review object** carrying the head sha, **OR** a `coderabbitai[bot]` **issue comment** that names
the head sha and does **not** carry the in-progress marker. **`DECISIONS.md` holds the derivation,
the per-pull-request evidence and what was rejected** — if it and this recipe disagree, it wins and
the recipe is the bug.

```bash
REPO=teonimesic/game-stack-bakeoff
PR=<n>
INPROG='auto-generated comment: review in progress by coderabbit.ai'

HEAD=$(gh pr view "$PR" --repo "$REPO" --json headRefOid --jq .headRefOid) || exit 1
[ ${#HEAD} -eq 40 ] || { echo "no head sha - an error, not a poll result"; exit 1; }

REVIEWS=$(gh api --paginate "repos/$REPO/pulls/$PR/reviews") || exit 1
BY_REVIEW=$(jq -s "[.[][] | select(.user.login==\"coderabbitai[bot]\") | .commit_id]
                   | index(\"$HEAD\") != null" <<<"$REVIEWS") || exit 1
case "$BY_REVIEW" in true|false) ;; *) echo "reviews query returned no boolean - an error"; exit 1;; esac

COMMENTS=$(gh api --paginate "repos/$REPO/issues/$PR/comments") || exit 1
BY_COMMENT=$(jq -s "[.[][] | select(.user.login==\"coderabbitai[bot]\") | .body
                    | select(contains(\"$HEAD\")) | select(contains(\"$INPROG\") | not)]
                   | length" <<<"$COMMENTS") || exit 1
case "$BY_COMMENT" in ''|*[!0-9]*) echo "comments query returned no count - an error"; exit 1;; esac

if   [ "$BY_REVIEW" = true ]; then echo "LANDED by review object at $HEAD"
elif [ "$BY_COMMENT" -gt 0 ]; then echo "LANDED by summary comment naming $HEAD, not in progress"
else echo "not yet (by_review=$BY_REVIEW by_comment=$BY_COMMENT)"
fi
```

**Say which arm fired, because they mean different things.** *Review object* means the reviewer
wrote comments and you have something to read; *summary comment* means it finished and had nothing
to say. Read the **word**, never the exit code: exit 1 is an API failure and must stop the loop,
which is why nothing here is wrapped in `|| true`.

**Read every page.** `gh api` returns only the first 30 records without `--paginate`, and the review
at the head sha is the **newest**, so it is the first thing to fall off page 1 — a PR that
accumulates reviews would poll to its deadline about a review sitting on page 2. Measured on PR #6's
reviews at `per_page=2`: **2** records unpaginated against **10** paginated. `gh` rejects `--slurp`
alongside `--jq`, so the pages are aggregated by an external `jq -s` reading a **here-string, not a
pipe** — a pipeline's exit status is the last stage's (rule 3), and each of the 4 commands keeps its
own `|| exit 1`.

**The in-progress clause is load-bearing, and the obvious fix without it is fail-open.** CodeRabbit
writes the head sha into the summary comment **while the round is still running** — the line
`Reviewing files that changed from the base of the PR and between <base> and <head>`, under
`<!-- This is an auto-generated comment: review in progress by coderabbit.ai -->` — and the
*"No actionable comments were generated"* line sitting below it at that moment is the **previous**
round's verdict. Matching the sha alone reported `LANDED` **31 seconds** after a push, mid-review.
Taking PR #5's real stored comment and injecting the marker: the arm returns **0** with the
`| not` clause and **1** without it, while on the real finished body it is **1** either way.

**The guards are what keep an empty `$HEAD` from ever reaching the queries, and that matters more
now than it did.** Nothing below is a description of what the recipe above does — it is what would
happen **without** each guard, which is the only reason each one is there:

| removed | what an empty or short `$HEAD` would then do |
|---|---|
| `\|\| exit 1` on `gh pr view` | a failed read becomes a poll result: the loop reports a review state inferred from a command that did not run (rule 2) |
| `[ ${#HEAD} -eq 40 ]` | `contains("")` is **true for every string**, measured, so the comment arm reports **every** pull request reviewed. The reviews arm fails the other way — `index("")` is `null`, hence `false` — so adding the comment arm turned this from fail-slow into fail-**open** (rule 7) |
| `\|\| exit 1` on either query | an API that is failing quietly contributes a `false`, and the loop polls to its deadline |
| either `case` | an empty or `null` jq result falls through to a plausible "not yet" instead of stopping |

With all 4 in place a failed `gh pr view` and a short sha both exit before either query runs —
verified, the 5-character abbreviation exits 1 with `no head sha`.

**How long it takes scales with the diff, so do not size the wait off one number.** Every
measurement taken so far:

| PR | diff | acknowledged | review posted |
|---|---|---|---|
| #1 | 2 files | 31s | **2m 30s** |
| #2 | 17 files, 615 insertions | 49s | **6m 15s** |
| #5 round 2 | 3 commits, 1 file plus 2 docs | 65s | **~35s after acknowledgement** |

| | |
|---|---|
| poll | every 30s |
| give up after | **15 minutes** per round — 2.4x the slowest measured. If a diff much larger than 17 files takes longer than that, the bound is wrong and the evidence is in the PR: say so rather than extending it in place |

### The ways this deadlocks, and what you do

**CodeRabbit says *"I am not going to review this"* in an issue comment, never in the reviews
array** — and it says it without naming a sha, so **neither arm of the check above can tell
"declined" from "not yet"**: the 2 deadlock notices this repository has received carry **zero**
40-character shas between them, measured, which is also what keeps them from firing the comment
arm falsely. Both are a **GitHub alert callout with a heading**, and GitHub's alert vocabulary is
a closed class of 5. So: extract the heading, and **read it.**

```bash
gh api "repos/$REPO/issues/$PR/comments" --jq \
 '[.[] | select(.user.login=="coderabbitai[bot]") | .body
   | scan("> \\[!(?:NOTE|TIP|IMPORTANT|WARNING|CAUTION)\\]\\n> ## ([^\\n]*)")]
  | flatten | join(" | ")'
```

One process, printing the headings — no pipe whose exit status would be the last stage's, and no
`grep` that exits 1 on zero matches and reads as a failure. Measured 2026-08-23 across every PR
this repository has had: **`Reviews paused`** on #1, **`Review limit reached`** on #6, and
**empty on #2**, which was reviewed normally. 2 true positives, 0 false positives on a corpus of
3 — small, so treat a heading you have not seen before as *read this comment*, not as a verdict.
**Every one of these notices states its own remedy in its body.**

> **This block matched the single string `review paused by coderabbit.ai` until 2026-08-23, and
> it is the rule audit's enumeration failure inside a skill.** PR #6 came back
> *"Review limit reached — you've used all 10 included reviews currently available"*; the
> phrase-match read **0**, and the poll loop was on course to spend its whole 15 minutes
> reporting "not yet reviewed" about a review that had never started (`tasks/120`).
>
> **The first replacement was worse than what it replaced, and only measuring said so.** Keying
> on `> [!WARNING]` — the notice in front of me — reads **1 on #6 and 0 on #1**, because the
> pause notice is a `> [!NOTE]`. It would have swapped which of the two deadlocks hangs the
> loop, and it looked like a generalisation. *Choose between candidate triggers on the
> live-corpus counts, never on which one sounds more general.*
>
> **`select(.user.login=="coderabbitai[bot]")` is load-bearing, and it is not hypothetical.**
> The old check read every comment by anyone. Twenty minutes later, on this same PR, it went to
> **1** — matching a comment *I* had posted, which quoted the string while explaining the bug.
> A check on an unfiltered comment stream is a check the agent can trip by describing it.

The headings seen so far, and what each means. **This table is its own census** — a heading
you meet that is not a row here is new, and the row to add is what you learn from its body:

| heading | why | what you do |
|---|---|---|
| **Reviews paused** — *"this branch is under active development … to avoid overwhelming you with review comments"* | **triggered by being productive.** `@coderabbitai resume` restores automatic reviews; `@coderabbitai review` buys one | post `@coderabbitai review`, resume polling |
| **Review limit reached** — *"you've used all N included reviews currently available"* | the org's allowance is spent. The body states how long until the next one frees up | wait out the stated interval, post `@coderabbitai review`, resume polling **within the same 15-minute bound** — do not restart the clock |
| **Review skipped** — *"No new commits to review since the last review"* | not a deadlock: you asked for a review of a head that has already had one | nothing. Push first, then ask. **It is stale the moment you push** — CodeRabbit edits its comments in place, so a heading here is a diagnostic and the check above is the authority |

**Push once per round, not once per fix.** Batching is what keeps the pause from firing at all,
and under a spent allowance it is the difference between one round and none.

**And the wait can simply expire.** Do not extend it and do not loop again. Say in the PR thread
that you waited 15 minutes and got no review, set the ticket to `in_testing` with that fact in
the evidence, and report it. **A no-review is a result the orchestrator can act on; an agent
still waiting is not.**

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
