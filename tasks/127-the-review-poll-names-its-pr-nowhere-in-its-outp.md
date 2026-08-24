---
id: 127
title: The review poll names its PR nowhere in its output, and a shared scratchpad repointed one at another agent's pull request mid-run
status: todo
priority: 2
refs: .claude/skills/work/SKILL.md section 6, AGENTS.md rule 12, DECISIONS.md 'An agent hands back a pull request', tasks/123, tasks/108
done_when: .claude/skills/work/SKILL.md section 6's recipe either asserts the branch it is polling or prints the PR and branch on every poll line - decide which and say why on the property, not on the instance; the choice is pinned by a control that goes red when the recipe is aimed at a PR that is not the agent's own branch; the same question is asked of every other recipe in .claude/skills/ that writes to a fixed scratchpad path, with the ones that are safe named and why; and if AGENTS.md rule 12's instance table gains a row it is written as the PROPERTY - an address that can change after it is written - not as 'the scratchpad'
---

Measured during task 123 on 2026-08-23. The work skill's section 6 poll recipe hardcodes PR=<n> and prints only the head sha, so the PR being polled appears in NO line of output. I wrote the recipe to scratchpad/pollreview.sh - a generic name in a directory shared with every concurrent session - and an agent working task 124 wrote its own copy to the same path with PR=10. My background loop calls the script by path each iteration, so it silently switched to polling PR #10 (task-124-ci-path-filter-and-minutes) and kept reporting 'not yet' at exit 0. Nothing in 16 polls of output could have shown it. This is AGENTS.md rule 12 - a correct method aimed at an address nobody re-verified - in a variant its own five-instance table does not contain: a SHARED MUTABLE address, where the address was right when written and wrong later. The failure direction is the dangerous one: had PR 10's review landed, my loop would have reported LANDED for a review of someone else's diff, and the next step in the procedure is to read that review and act on it. The repair used in task 123 is in scratchpad/task123-poll-pr9.sh and is two lines: name the script for the ticket AND the PR, and assert headRefName equals the expected branch before believing any answer, exiting 1 with 'WRONG PR' otherwise. Controls both directions: PR=9 returns 'not yet (... head=55a0901)' exit 0; the same script with PR=10 returns "WRONG PR: #10 is 'task-124-ci-path-filter-and-minutes'" exit 1.

## note 2026-08-24

## note 2026-08-24 — the WAIT BOUND is measured wrong, and here is the number

Not this ticket's `done_when`, but the same recipe, so it is recorded here rather than lost.

Task 130's agent polled PR #15 **29 times over a 15-minute bound**, reported *"no review object,
no summary comment naming the sha"*, and handed back saying the review had not landed. It had not
— **yet**. Measured from the GitHub API afterwards:

| event | time (UTC) |
|---|---|
| head `8adba4a` pushed | 11:06:52 |
| 15-minute bound expires | ~11:21:52 |
| CodeRabbit review submitted | **11:26:18** |

**19m26s on a 4-file documentation diff**, so the bound missed by 4m26s. The agent flagged the
bound as suspect in its own hand-back ("15 min is 2.4x the slowest previously measured round"),
which is the right instinct and the wrong conclusion — the slowest previously measured round was
not the population.

The consequence was not a wasted wait. The work was handed back as ready, and the review contained
**four threads, one Major**, naming a real AGENTS.md rule-4 violation. `required_conversation_
resolution` on `main` is what stopped it merging; without that setting it would have merged
unreviewed on a green tick.

**Do not just raise the number.** A fixed bound derived from a handful of observations is the same
defect at a larger value. What the recipe cannot currently do is distinguish *not finished* from
*never coming*, and the agent noted the alert-heading extractor returns empty for both. Either find
a signal that says a round is in flight — the summary comment's in-progress marker was present and
observed, so that signal exists — and wait on THAT rather than on a clock, or make the timeout a
loud unresolved outcome rather than a quiet "no review".

## note 2026-08-24

## note 2026-08-24 — two more defects in the same recipe, both now findings

Found by task 131's agent while following `work/SKILL.md` section 6. Both are in scope for this
ticket, and both have finding numbers allocated against `main`, so cite rather than re-derive.

**[#165] The poll believes a head the API has not caught up to.** The recipe reads the head once.
Run straight after `git push`, `gh pr view` returns the PREVIOUS head for a few seconds, and the
poll reported `LANDED ... at eff4821` while local `HEAD` was `822f488`. The same race returned a
green `check-runs` answer about a commit no longer under review.

This is the **fail-open** direction and it compounds the defect this ticket was filed for: the
recipe already names no pull request in its output, and now it can also name the wrong commit
while saying LANDED. The next step in the procedure is to read that review and act on it.

The fix is the same shape as this ticket's: **pass the expected sha in and refuse to poll until
the API agrees**, an expectation stated independently of the thing it checks. Do not fix it with
a sleep — a sleep makes the race less likely and leaves it fail-open.

**[#166] `gh api -f body="..."` executes backticks.** A reply lost three words silently. `#80` is
about `git commit -m`; the flag was different so the rule did not match, in the file documenting
`#80`. Route composed text through `gh api --input <json>` and compare the round trip.

**Together with the bound measurement above, this recipe now has four known defects**: it names no
pull request, it can name the wrong commit, its timeout is 4m26s too short on a 4-file diff, and
its reply path corrupts text. Consider whether the `done_when` should be widened to "the recipe is
rewritten and controlled as a whole" rather than repaired one clause at a time.

## note 2026-08-24

## note 2026-08-24 (later) — the stakes changed today, and so did what "done" is worth

`main` is now protected with **`required_conversation_resolution`**, so an unresolved review thread
**blocks the merge**. This recipe is no longer advisory: what it reports decides whether work can
land, and its two false-positive modes (#165 reporting LANDED at a stale head, and reporting a
clean review that has not happened) now translate directly into merging on a review nobody read.

Both merges today needed a review round the recipe had already declared finished or absent.

## Do not verify this recipe with this recipe

The obvious test — run the fixed poll and see whether it reports correctly — shares every
assumption with its subject. That is #37's shape and this project has paid for it twice. Build the
expectation independently: a pull request whose review state you know in advance from the API by a
different route, ideally one you set up deliberately (a thread left unresolved, a head pushed and
polled immediately, a body containing backticks whose round trip you compare byte for byte).

The `gh api -f body=` corruption (#166) is the easiest to control and the easiest to get wrong:
compare what you sent with what the API stored, not with what you meant to send.
