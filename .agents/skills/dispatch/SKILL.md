---
name: dispatch
description: "Send one queued task to an agent, and take its pull request back. Covers making the ticket current before dispatch, the launch itself, and verifying and merging the result. Invoked as /dispatch <id>."
when_to_use: "You are orchestrating and want work started on a queued task; an agent has reported and its pull request needs verifying and merging; the queue is idle and the heartbeat says to pick something."
argument-hint: "<task-id>"
---

# Dispatch one task

**Authoritative files: `tasks/<id>-*.md` (the ticket), `.claude/skills/tasks/SKILL.md` (the
queue), `.claude/skills/work/SKILL.md` (what the agent will follow).** If this skill and any of
those disagree, they win and this skill is the bug.

> **You may not put task-specific instructions in the agent's prompt.** The prompt is
> `/work <id>` and nothing else. Anything the agent needs to know goes in the **ticket**, before
> you launch. A brief in a message dies with the session, and on 2026-08-23 roughly 1,500 words
> of real constraints were dispatched that way and had to be retrofitted into seven tickets.
>
> **If you catch yourself typing the constraint, that is the signal the ticket is not ready.**

---

## 1. Make the ticket current — this is the actual work of dispatching

Read the ticket in full: `python3 eval/tools/tasks.py show <id>`. Then ask what has changed since
it was filed, and **write the answers into the file**.

| Check | If it has moved, put in the ticket |
|---|---|
| Does anything it *assumes* still hold? | The correction, dated, and what it now implies |
| Has a **dependency appeared** since filing? | Which file, what it forbids, and who created it |
| Has a peer's result landed that bears on it? | The measurement itself, never a pointer to a conversation |
| Is its `done_when` still reachable and still right? | Rewrite it, and say why it moved |
| Did an earlier agent hand back knowledge? | Append it under a dated heading |
| Do its **`refs`** still resolve? | Fix them — a renumbered finding still resolves and now means something else |

Then hold the ticket to the standard in the `tasks` skill: **a stranger in a fresh session, with
no memory of why this exists, must be able to start it and know when to stop.** Concretely, before
you launch, the ticket must answer:

1. **What is this thing?** — define the component before naming its problem.
2. **What is wrong, and how do we know?** — the defect *with its measurement*.
3. **Why does it matter?** — what conclusion is unsafe while it stands.
4. **What should be done?** — the concrete first move, naming files.

And where they apply: what **not** to conclude; what each outcome would mean, so a null result
closes it; and any regime boundary the work would cross.

**A ticket that only you could work is not a ticket.** Fix it now, in the file — the next agent,
and every future reader, gets it for free.

### Mark what you MEASURED and what you GUESSED, in the note itself

A ticket note is read as a brief, and the agent following it treats a stated cause as settled.
**On 2026-08-25/26 three orchestrator-written causes were wrong**, each corrected by the agent that
measured instead of complying:

| the note said | it actually was |
|---|---|
| skills escape the flag census because they are outside `project_docs()` | a file-wide harness gate; skills are in the corpus |
| carry pong's repair across — press nothing after the end | fail-open: with the player dead nothing moves the score |
| `gates` is red because a `$` entered a producer | a local named `spent` matched a discovery regex keyed on the identifier NAME |

None was careless. Each was a plausible reading of real evidence, written to save the agent time —
and **that is the mechanism**: a cause offered helpfully is indistinguishable, in the ticket, from
a cause established.

> **Write the measurement, and label the inference as an inference.** *"`gates` is red on
> `tokenvalue --selftest`, one named step; I have not run it"* costs one clause and cannot mislead.
> *"a `$` entered a producer"* is a conclusion the reader has no reason to re-derive, and they will
> not.

The agent is the one holding the tree. **Where a cause is cheap for them to measure and expensive
for you to verify from outside, state the symptom and let them find it** — the ticket's job is to
say what is wrong and how you know, not to pre-solve it.

## 2. Check it is safe to run now

- **Dependencies.** The ticket's `refs` may say "blocked by". Do not launch behind an unmet one.
- **File conflicts.** List what your running agents are touching. Two agents editing the same
  document is the one conflict worth spending effort to avoid — especially in a file that states
  what is true *now*. If the ticket collides, either wait or write the scope limit **into the
  ticket**.
- **Shared, non-branchable state.** `eval/runs/`, the operator's machine, anything outside the
  repo: only one agent at a time, and say so in the ticket.
- **Irreversible or outward-facing work** — deleting evidence, spending money, anything touching
  the operator's machine — is **not** dispatchable on your own authority. Ask first.

## 3. Launch

`Agent` tool, and only these settings:

| | |
|---|---|
| `prompt` | `/work <id>` — exactly this, nothing appended |
| `model` | `opus` — the queue is the project's reasoning about its own instrument |
| `isolation` | `worktree` |
| `subagent_type` | `general-purpose` |
| `description` | `Task <id> — <a few words>` |

**Concurrency is how the review pool gets spent, and it is yours to control — not the agent's.**
Every dispatched agent opens a pull request and runs up to 5 review rounds, a round can cost more
than one review, and they all draw on one shared hourly allowance. Four agents finishing together
is four PRs in review at once.

**Nothing can read that allowance.** The counter CodeRabbit once printed lives in a summary
comment it overwrites in place, and it is in none of the stored pull requests (#158). So it cannot
be budgeted against, only observed: **if reviews stop arriving on several PRs at once, that is the
pool, not a clean review.** The two are indistinguishable from inside an agent, which is why the
agent-side rule is to hand back and report rather than wait.

Capping rounds per PR does not control this — the number of PRs in review at once does. Stagger
dispatches when a wave would land together, and prefer fewer agents on bigger tickets over many on
small ones.

Then `python3 eval/tools/tasks.py` to confirm it shows `in_progress`, and keep dispatching.
**Never leave the queue idle behind one item** — a task in the queue was authorised when it was
filed.

## 4. Take the pull request back

**The queue tells you whose turn it is.** Five statuses, and only one of them is yours:

| status | what it means for you |
|---|---|
| `todo` | not dispatched. Step 1 |
| `in_progress` | the agent is working. Nothing to do |
| `in_review` | its pull request is open and the review loop is running. Nothing to do — the `pr` field in the ticket is the link, and `check` fails a ticket in this state that has none |
| `in_testing` | **yours.** The agent has finished. Its evidence says whether a review arrived and what it did with it — an `UNRESOLVED` wait ends here too |
| `done` | merged. You set this |

```bash
python3 eval/tools/tasks.py list --status in_testing
```

That is the whole reason the vocabulary grew from 3 values to 5 on 2026-08-23: `in_flight` said
an agent had picked the task up and nothing else, so the only way to find out whether it was
still working was to ask it.

**Then verify against the artifacts, not against the report.** Run its controls yourself; a
result you have not reproduced is a claim.

> **A CodeRabbit review does not shorten this step and must not be read as if it does.** It is a
> second opinion on the code, not a measurement of the claim, and it has no access to the
> artifacts your verification runs against. *"It passed review"* is precisely the shape this
> project calls a mechanism that runs and reports success.

Read the PR thread for one thing beyond that: **comments the agent declined, and why.** A
declined comment naming a rule is the flow working; a declined comment with no reply is a gap in
the handback.

**An agent may hand back `in_testing` reporting `UNRESOLVED`** — `pr_review_state.py --wait`
gave up. That is the outcome the wait is designed to produce and it is not a failure of the task.
The evidence says which bound expired: `seen_in_flight=False` means no round ever started, which
is a reviewer problem (check for a deadlock notice on the pull request); `seen_in_flight=True`
means one started and ran past an hour. Merge on your own verification as you would have before
the flow existed, and if it happens twice in a row that is evidence about the reviewer — a task,
with the 2 PR numbers in it.

### Merging

**Merge through the pull request, not with a local `git merge`.** The PR is the durable record
of what was reviewed and what was declined, and a local merge closes it as *"merged"* by
inference rather than by fact.

**Check the merge is safe before you make it — green is not the question that failed.**

```bash
python3 eval/tools/mergeable.py <n>   # exit 1 = do not merge. Read the reasons
```

```bash
python3 eval/tools/mergeable.py <n>         # exit 1 = do not merge. Read the reasons
gh pr merge <n> --squash --auto --delete-branch   # --auto: lands itself when checks pass
# ... only once it has MERGED:
git pull                                    # bring the squashed commit down
git add tasks/ && git commit -m "Queue: agents' status writes through the shared queue"
git push
git worktree remove --force <path>
git branch -D task-<id>-<slug>              # -D, not -d: see below
python3 eval/tools/tasks.py done <id> "what you verified, and how"
```

> **The queue commit goes AFTER the merge, and this reversed on 2026-08-24.** It used to go first,
> because agents write status into the main checkout and an uncommitted `tasks/` blocked a local
> merge. Under `strict` required checks that ordering is actively wrong: **any push to `main`
> puts every open pull request out of date**, so pushing the queue commit between verifying
> `mergeable.py` and merging invalidates the very thing you just verified. It did exactly that
> here — `mergeable.py` said *behind by 0*, the queue push landed, and `gh pr merge` came back
> *"the head branch is not up to date"* seconds later.
>
> The local merge that made the old order necessary is gone, so nothing needs `tasks/` committed
> first any more.

**Use `--auto`.** With `strict` on and several pull requests open, the branch you verified goes
stale whenever anything else lands, and `controls` takes minutes
(`.github/workflows/README.md` is the register for what each tier costs), so the window
between *green* and
*merged* is minutes wide and someone else's merge closes it. `--auto` merges the moment the
requirements are met instead of asking you to win a race. It needs `allow_auto_merge` on the
repository, which is set.

**While a pull request is waiting on `--auto`, do not push to `main`.** Every push restarts its
checks from behind. Batch your own commits and land them after the queue drains, or accept that
each push costs another `controls` round trip per open pull request.

**The repository is squash-only** — `allow_merge_commit` and `allow_rebase_merge` are both off,
so `--merge` and `--rebase` now fail rather than silently doing something else. A task branch
arrives as **one commit on `main`**, which is what the six review-round commits of PR #13 argued
for: the rounds are the reviewed record and they live on the pull request, not in `main`'s history.

Two consequences, both of which bite the first time:

- **The squashed commit's message is the pull request's TITLE and BODY**, by repository setting
  (`PR_TITLE` / `PR_BODY`). Nothing you write locally reaches it. So the PR body is now the merge
  message, and it must record **what was established and what it cost** — the standard this skill
  has always applied to a merge message applies there instead. Edit it before merging with
  `gh pr edit <n> --body-file <file>` if the agent's body does not carry that, and read back
  `gh pr view <n> --json title,body` afterwards — `--body-file` is silent about having picked up
  the wrong file, and this text is the permanent commit message.
- **`git branch -d` refuses a squash-merged branch.** Its commits are not ancestors of `main` —
  the content is, the commits are not — so git reports it unmerged and is correct. Use `-D`, and
  only after `mergeable.py` and the merge have both succeeded. **Leaving the branch behind is not
  a failure of the queue gate**: `tasks.py check` reads the change, not only the tip, so a
  squash-merged branch that survives reads `LANDED` rather than `ORPHANED`. A deleted one reads
  `NOT_CHECKED`, which is not a pass (`DECISIONS.md`, *A closed ticket is checked against the
  tree*).

### The merge gate, and why green was not the question

On 2026-08-23 `main` went red on the merge of PR #13 while **#12 and #13 were both green**.
Both were tested against a base that contained neither. #12 added three comments to
`cost_census.py` spelling token valuations with a `$`; #13 added the gate forbidding exactly
that in a producer. Individually correct, jointly red — and no run anywhere had ever built the
head the merge would produce.

`mergeable.py` therefore asks two questions, and the second is the one that caught it:

| it refuses when | because |
|---|---|
| a required check is red, running, or **absent at the pull request's current head** | a green run against an earlier push is a statement about a commit nobody is merging. PR #13's final head had **no `gates` or `controls` run at all** — the green run belonged to a commit two pushes earlier |
| the branch is **behind its base** | PR #13 merged **12 commits behind**, and those 12 commits contained the very lines its own new gate forbids |

**GitHub enforces both natively since 2026-08-24**, when the repository went public and
`strict` required status checks became available: `gh pr merge` is refused if a check is red or
the branch is behind. So `mergeable.py` is now the pre-flight that tells you **why** a merge will
be refused, before you spend a round trip finding out.

**It is not redundant, because `enforce_admins` is off.** An admin can still push straight to
`main` and can still merge with `gh pr merge --admin`. The server-side protection covers the
ordinary path; the person most able to bypass it is the one who broke `main` last time, and
running the pre-flight is what covers that.

**When it refuses for staleness, the fix is on the branch, never at the merge button:** update
the branch from `main`, push, and let CI re-run at the head that will actually land. That is also
what makes the re-run meaningful — it builds the combination, which is the thing that was never
built.

**Never merge the branch into `main` locally. There is no longer an exception.** The rule was
already here and it did not fire, because the paragraph under it explained *how* to do it well —
so the local path read as sanctioned, and PR #13 was merged that way with a composed message.
What that cost is measured: its review rounds **3, 4, 5 and 6 have zero check-runs each**, because
`push` is narrowed to `main` and a `pull_request` synchronize event only fires while the pull
request is OPEN. Pushing `main` first closed #13 by inference, and four commits reached `main`
having never been built anywhere. The green tick the pull request displayed belonged to round 2.

> **A local merge does not merely skip the record — it skips the CI.** A branch merged locally and
> pushed to `main` arrives as commits nobody tested, and GitHub marks the pull request *merged* one
> second before the push, so nothing is left in a state that looks wrong.

**Conflicts are resolved on the BRANCH**, which is where the `git merge` guidance below belongs
and the only direction it now applies in: merge `origin/main` **into** the task branch, push, let
CI re-run, then merge the pull request. That is also what `mergeable.py` demands, and the re-run
is the only thing that ever builds the combination.

> **When you merge `main` into the branch, `git merge --no-ff -m "<placeholder>"` AUTO-COMMITS if
> there is no conflict.** A message written
> afterwards then has nothing to apply to: `git commit -F` prints *"nothing to commit, working
> tree clean"* and exits **0**, which reads exactly like success. Five merges on 2026-08-23 landed
> carrying only a placeholder; three had the real message land as a separate follow-up commit and
> **two lost it entirely**.
>
> The habit works only on the CONFLICTED merges, because those are the ones that leave something
> to commit — **so the message is correct exactly when the merge was hard, and missing when it was
> easy**, which is the least likely pattern to notice.
>
> `git commit --amend` has the sibling trap: **without `-a` it amends the message and the STAGED
> changes only.** Amending to fix a message while edits sit unstaged leaves the message on one
> commit and its content on the next. That happened in the repair of this very paragraph.
>
> Write the message first and pass it — `git merge --no-ff -F <file>` — and read
> `git log --oneline -1` and `git show --stat HEAD` afterwards. Neither command fails when it
> does nothing.

Three orderings in those six lines, and each one was paid for:

- **The queue commit LAST**, because any push to `main` puts every open pull request behind its
  base under `strict`. This was the opposite until 2026-08-24; see the note above for what
  reversed it.
- **`git worktree remove` before `--delete-branch`.** `gh pr merge --delete-branch` deletes the
  remote branch and then fails on the local one while an agent worktree still holds it
  (`tasks/108`) — so you are left having half-cleaned up, with the remote gone and the local
  branch pinned by a checkout.
- **`git pull` afterwards is not optional.** The merge happened on GitHub; until you pull, your
  local `main` does not contain the work you just merged and the next dispatch is made against a
  tree that is missing it.

`-m` is used above and it is not an exception to anything: **the rule is about the CONTENT of a
message, not about which flag carries it.** A fixed literal with no backticks in it cannot be
altered by the shell. Anything you compose — a merge message, a resolution note, an agent's
evidence — contains paths and identifiers, and goes through `git commit -F` with a file, because
backticks in a double-quoted argument are command substitution and strip text silently (#80).

**When the PR conflicts with `main`**, `gh` cannot merge it and the resolution is still local:
`git fetch`, merge `origin/main` into the task branch, resolve with the table below, push, and
merge the PR. Resolving on the branch keeps the resolution inside the reviewed record instead of
appearing on `main` unreviewed.

**Conflicts you will meet every time, and how they resolve:**

| Conflict | Resolution |
|---|---|
| `eval/FINDINGS.md` range line | Keep one, then set it to the real highest number |
| Two findings with the same number | The already-merged one keeps it; renumber the incoming one **in the body, the index row, and every citation** |
| Appended sections in `RUNS.md`, `IMPROVEMENTS.md`, `CLEANUP-LOG.md` | Keep both |
| The same fix made twice | Take the better one, and say in the commit why |
| **A structured file (JSON, TOML, lock)** | Merge by STRUCTURE, not by text. Keeping both sides of `eval/withdrawn.json` produced a file that PARSED while silently dropping an entry — duplicate keys keep the last, so the loss is invisible to `json.load` and to the eye. Rebuild by id from both sides and count the entries |
| **Two branches added code to one file** | Keeping both sides is right and does not mean the result parses. A nested marker whose outer pair was already consumed, and two halves of one statement each ending differently, both surface as `SyntaxError`, not as a conflict. Parse the file before you trust the merge |
| **`--theirs` or `--ours` on a document that is a LIST** | Never. On 2026-08-23 `git checkout --theirs eval/FINDINGS.md` resolved a conflict cleanly and silently dropped an index row the other side had added — the file was well-formed, the merge was green, and `docstat.py --findings` was the only thing that noticed. Same shape as the structured-file row below: a list resolved by side loses entries without malforming |
| **Keeping both sides of a document that states one fact** | Keeping both is right for logs and wrong for assertions. It duplicated `eval/FINDINGS.md`'s range sentence, and `_check_range_in` validates *each copy*, so **N correct copies are N passes** and the duplicate survives. One statement per live document |
| **Both sides right in the same region** | Neither `--ours` nor `--theirs`. Merge by hand and say what each contributed — on 2026-08-23 `DECISIONS.md` held a withdrawal-register sentence on one side and a corrected cost figure on the other, and taking either wholesale would have discarded a real result |

**You allocate the finding number, not the agent — and do it at merge, not before.**

Three branches on 2026-08-23 each independently took **#137**, having each correctly read the
highest number on `main` before starting. That is not carelessness and re-reading does not fix it:
**nothing can gate a number a peer has not committed yet**, and the merging tree is the only one
that holds every claim at once. `docstat.py --findings` gates a *gap*, so an agent choosing between
a collision and a gap should choose the collision and say so — the collision is repairable here and
the gap is invisible.

When two branches collide, the rule is *the merged one keeps it* — but neither is merged yet, so
apply the rule's purpose instead: **renumber whichever side has fewer citations to chase.** One of
those three had spread `#137`/`#138` through three code files and two had a body and an index row;
the bodies moved. Renumbering means the heading, the index row, **and** every citation.

Then, unpiped: `docstat.py --sweep`, `docstat.py --renumbered`, `tasks.py check`. Renumbering
creates stale citations that still *resolve* — `--renumbered` is what finds them.

Whatever records **what was established and what it cost** — not what was changed — is now the
**pull request body**, because that is what the squash lands as the commit message. Resolution
commits made on the branch still go in through `git commit -F` with a file, for the reason given
under *Merging* above: composed prose carries paths and identifiers, and backticks in a
double-quoted `-m` are command substitution that strips text silently (#80).

## 5. Go back to step 1 before you report

**A merge is not the end of the loop. It is the middle of it.**

The moment a branch is merged, ask the queue what is open — and dispatch it, **before** writing
a word to the operator. Reporting first is how the queue goes idle, because a report reads like
a stopping point and the next thing to happen is whatever the operator says.

This has failed **twice on 2026-08-23**, both times with the same shape: a wave of agents
reported, every branch was merged and verified carefully, a summary was written — and six
authorised tasks sat untouched until the operator asked why nothing was running. The rule *never
leave the queue idle* was already in step 3 and did not fire, because it reads as advice about
dispatching and the failure happens after merging.

```bash
python3 eval/tools/tasks.py        # open count, every time you finish a merge
```

If that number is above zero and no agent is running, **you are the bottleneck.** Dispatch, then
report — and say in the report what is now in flight, so the state is visible without asking.

The two legitimate reasons not to dispatch an open task, and they are the only two:

- it is **blocked** by an unmet dependency in its `refs`, or
- it needs a decision that is **not yours** (step 2's last bullet) — in which case ask *and*
  dispatch everything else. **Never idle a queue behind one item.**

## 6. Improve this skill as you use it

**When a dispatch goes wrong, the defect is here or in the ticket — not in the agent.** If you had
to explain something in a message, put it in a ticket and add the case to the table in step 1. If a
merge surprised you, add it to the table in step 4. This file is how the next orchestration session
starts ahead of this one.
