---
id: 127
title: The review poll names its PR nowhere in its output, and a shared scratchpad repointed one at another agent's pull request mid-run
status: done
priority: 2
refs: .claude/skills/work/SKILL.md section 6, AGENTS.md rule 12, DECISIONS.md 'An agent hands back a pull request', tasks/123, tasks/108
done_when: .claude/skills/work/SKILL.md section 6's recipe either asserts the branch it is polling or prints the PR and branch on every poll line - decide which and say why on the property, not on the instance; the choice is pinned by a control that goes red when the recipe is aimed at a PR that is not the agent's own branch; the same question is asked of every other recipe in .claude/skills/ that writes to a fixed scratchpad path, with the ones that are safe named and why; and if AGENTS.md rule 12's instance table gains a row it is written as the PROPERTY - an address that can change after it is written - not as 'the scratchpad'
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/18
established_by: 'PR #18 squash-merged. Verified independently on real subjects: --pr 9 --branch task-123 returns LANDED_REVIEW exit 0 and --pr 10 with that same branch returns ''WRONG PR ... you are polling somebody else''s pull request'' exit 1, with the PR, branch and head named in the output the old recipe printed none of. 64 selftest checks (9 variants), 32 mutants all caught, gate count 41 agreeing with its producer on the merged tree. I adjudicated the last review thread myself: the staged-content guidance said ''prove'' via git status and proving is what it did not do; now stage, assert porcelain empty, run gates, assert empty again.'
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

## note 2026-08-24

## note 2026-08-24 — what was built, and what the next agent must not re-derive

**The poll is `eval/tools/pr_review_state.py`.** There is no scratchpad recipe any more, and that
is the fix rather than an implementation detail of it: the defect was the interval between
writing an address down and using it, and a tool takes the address as an argument on every
invocation so there is no interval.

    python3 eval/tools/pr_review_state.py --pr <n> --branch task-<id>-<slug> \
        --expect-head "$(git rev-parse HEAD)" --wait

`--selftest` is offline — it injects its own `gh` runner and its own clock;
`eval/tools/pr_review_state_mutants.py` is the other half. Both gate in `gates.yml`.

### The decision, on the property

**Assert, and also print — but the assertion is the guard.** An assertion fails closed at the
moment of use; a printed line is only as good as the reader who happens to look at it, and the
consumer of this verdict is the next step of a procedure (*read that review and act on it*), not
a person reading output. Printing stays as the audit trail. `DECISIONS.md`, *The review poll is a
tool that asserts its own address*, holds the rejected alternatives.

### Do not re-measure these

| | |
|---|---|
| the retired recipe aimed at #9 and #10 | `LANDED by review object at <sha>` at **exit 0 for both**, nothing in either line distinguishing them |
| the tool aimed at #10 while expecting task 123's branch | `WRONG PR: #10 is on branch 'task-124-…'`, **exit 1** |
| `--census` against `DECISIONS.md`'s per-pull-request table | agrees on **all 6** rows, including #3 where both arms correctly read false. 3 distinct verdicts over 17 pull requests |
| squash merges | a merged branch tip is an ancestor of **nothing**. Filed as `tasks/140`, and already landed on `main` as `c2e8f45` |

### 6 things this pull request's own review rounds measured, live

Every one of these came from using the tool on the pull request that adds it, and none could have
been reached by a fixture:

1. **The in-progress marker vanishes mid-round.** Round 1 went `IN_FLIGHT` → `NOT_YET` →
   `LANDED_REVIEW` over 12 polls / 345s. That is why `seen_in_flight` **latches** rather than
   being recomputed from the last poll — variant `F2`, occurring for real.
2. **A `--wait` under a harness printed 0 bytes** until it exited, because Python block-buffers
   stdout off a terminal. Fixed with a flushing emitter; without it the per-poll audit trail
   arrives only after the answer does.
3. **A deadlock notice outlives the pause it describes.** After `@coderabbitai review` cleared a
   pause, the next `--wait` returned `NOTICE` at **elapsed=1s** — the notice is a comment, and
   CodeRabbit leaves it in place until it next rewrites the summary. A stop condition that
   survives being acted on makes `--wait` a no-op and the remedy unobservable. Hence
   `--ignore-notice`, which keeps printing the notice and stops treating it as a stop condition;
   a pause that is never lifted then ends `UNRESOLVED` on the quiet bound, which is loud.
4. **The clean arm fires.** Round 5 came back `LANDED_COMMENT` — no review object at all, a
   summary comment instead — with a **stale `Reviews paused` notice sitting beside it**. Had
   `NOTICE` outranked the landed arms, that would have read as a deadlock on a clean review.
5. **Replying to a review creates empty review objects stamped with the current head.** 5 replies
   made 5 such objects at `810172b`; the poll still read `NOT_YET`, because the body guard and the
   login filter both exclude them.
6. **`gh api -f body=` really does eat backticks**, and `jq -n --rawfile b f '{body:$b}'` through
   `--input` round-trips byte for byte. All 11 replies and 2 trigger comments were compared
   against what the API stored; the only difference each time was a trailing newline the API
   appends.

Round times, all with the marker observable throughout: **345s**, **411s**, **506s**, **317s**,
**223s**. The retired 15-minute clock would have expired on the 506s round.

### What the review rounds changed, and they were right every time

11 threads over 4 rounds, 0 declined outright; round 5 came back clean. 6 of the 11 were about
**one** thing — the `audit-docs` planted-phantom control this ticket's census turned up — and each
round went a level deeper than the last. Worth carrying forward:

- **The resource, not the copy** (`AGENTS.md` rule 13). Giving the backup a unique name stops 2
  passes restoring each other's copy and does nothing about 2 passes mutating `judge/JUDGING.md`.
  The backup is gone.
- **The reference the guard reads.** `git diff --quiet` compares against the **index**, so a
  staged edit passes, and `git checkout --` then restores from that same index — guard and restore
  sharing the wrong reference, agreeing with each other and disagreeing with the document. It is
  `git diff --quiet HEAD` and `git restore --source=HEAD --worktree` now.
- **`cmd ; echo "expect exit 1"` asserts nothing**, and `set -e` cannot stand in here because half
  the controls are *supposed* to exit 1 — it would abort before the restore and leave a phantom in
  a tracked document. A `sweep <expected>` function asserts and restores on every path.
- **A failed append is how a control goes green having tested nothing.** The positive halves
  survive it (`sweep 1` against a clean corpus reddens), the `sweep 0` halves do not. `plant`
  reports and restores, checks its own restore, and every call is `|| exit 1`.
- **A mutant that crashes is not a mutant that was caught.** `drop_field` exited non-zero with a
  `KeyError` and 0 red rows, and the harness scored it green. It now rejects a mutant with no red
  row — and that rule immediately rejected 1 of the 3 mutants added in the same round. Both halves
  matter: the harness must reject a crash, **and** the selftest must redden on drift rather than
  die on it.

### The merge, and a defect in the procedure it exposed

`main` moved 4 commits while this was in review, and its task 133 added **2** gates to `gates.yml`
while this branch adds **2** of its own — so both sides pinned 39 and the merged workflow has 41.
Two changes each correct and jointly red, which is what keeping the branch current is for.

**The repair was made in the worktree and the merge commit did not carry it.** `git commit
--no-edit` finishes a merge from the **index**, so an edit made after the conflict resolution is
silently left behind: `ci_minutes --selftest` was green locally and red in CI on the same second.
`work/SKILL.md` §5 now says to run the gates against what is about to be pushed and to prove it
with `git status --short`. It is rule 12 with the worktree as the wrong address.

### Two observations that are not defects here

- **A push produced no CI runs at all.** `aada0f1` has **0** workflow runs and **0** check runs,
  measured from the API, while CodeRabbit reviewed it normally. The next 3 pushes triggered
  normally, so this was a GitHub-side hiccup rather than configuration — but it is the shape
  `.github/workflows/README.md` warns about (*a workflow that does not match produces no check at
  all, not a passing one*), and a required check that never arrives blocks a merge silently.
- **`NOTICE` fires on any bot alert callout the pull request has ever carried**, and CodeRabbit
  edits comments in place, so a stale notice outlives its state. That is why `NOTICE` ranks
  **below** both landed arms. A freshness window on the notice was considered and rejected: it is
  a parameter chosen by judgement that nothing here can measure, and the failure it would
  introduce (missing a real pause) is worse than the one it removes (1 review from the shared pool
  spent on an unnecessary `@coderabbitai review`).

## note 2026-08-24

## note 2026-08-24 (hand-back) — the round budget, and what the last 2 rounds were for

**6 review rounds, over the ceiling of 5, and here is why that is not the ticket being bigger
than it was filed as.** Round 5 came back **clean** — `LANDED_COMMENT`, *"No actionable comments
were generated"* — which is where the procedure says to stop. What followed was not another fix
iteration:

| after round 5 | why it needed a push |
|---|---|
| merge from `main` | `main` moved 4 commits and its task 133 added 2 gates to `gates.yml` while this branch adds 2. Both sides pinned 39; the merged workflow has 41. `mergeable.py` refuses a branch behind its base |
| the pin the merge left unstaged | `git commit --no-edit` finishes a merge from the index. Green locally, red in CI, same second |
| `--ignore-notice` | found by using the tool: a notice outlives the pause it describes, so the poll started **after** acting on one stops at `elapsed=1s` for ever |

Round 6 then found 2 real things in that work, both taken. If the budget matters, the honest
count is **5 rounds of review on the deliverable and 1 on the merge**.

**Final state.** Head `c84adc6`, `gates` **1m27s** pass, `controls` **10m15s** pass, CodeRabbit
pass. 13 threads over 6 rounds, **0 declined outright** — the only partial decline was round 2's
request to name a shell producer for `AGENTS.md` rule 12's row counts, where the population is the
table 1 line below and `docstat.py --sweep` already reads adjacent counts green; the numbers now
name that population instead.

**Producers for every count in the pull request body:**

    python3 eval/tools/pr_review_state.py --selftest        # 64 checks, 9 variants
    python3 eval/tools/pr_review_state_mutants.py           # 32 mutants
    python3 eval/tools/ci_minutes.py --gates                # 41 gates.yml gates
