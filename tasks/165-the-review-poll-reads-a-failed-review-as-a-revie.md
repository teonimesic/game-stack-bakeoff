---
id: 165
title: The review poll reads a FAILED review as a review that found nothing
status: in_review
priority: 1
refs: 'eval/tools/pr_review_state.py, .agents/skills/work/SKILL.md, tasks/127, tasks/162, #185, #165'
done_when: A branch in the 'Review failed - the head commit changed' state does NOT return LANDED from pr_review_state.py, proved by constructing that state deliberately rather than waiting for it; the notice table in work/SKILL.md names each notice with what it implies for the poll; --ignore-notice keeps working for the paused case, pinned; and the ambiguous case - no notice, summary comment only, no review object - is decided and the decision written where the flag is defined.
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/41
---

`pr_review_state.py --wait --ignore-notice` returned **`LANDED_COMMENT` in 1 second** on a branch
where CodeRabbit had just posted **`Review failed — the head commit changed during the review`**.
The real review arrived **540 s** later. Measured on PR #39 (task 162).

The poll asked *"is there a comment at this head"* and the procedure reads the answer as *"has this
head been reviewed"*. A failed review leaves the same artifact a successful one leaves — a summary
comment at the right sha — so the two are indistinguishable to everything except the text nobody
parses.

**It is fail-open in the expensive direction.** The next step in `work/SKILL.md` is to act on the
review, so *"nothing to say"* and *"the reviewer was interrupted"* produce the same behaviour: the
branch proceeds as though it had been read. `#185` records it.

## `--ignore-notice` is the flag that made it worse, and it was right to exist

It was added so *Reviews paused* — a pool-exhaustion notice — could not block a poll forever. That
reasoning stands. `Review failed` is a different notice with the **opposite** meaning, and one flag
covers both because the flag names the **mechanism** (there is a notice) rather than the
**property** (whether this head was actually reviewed).

This is AGENTS.md's own rule about triggers, inside the tool written to fix the previous instance of
it.

## What would answer it

The poll must distinguish notices by what they imply, not by their existence:

| notice | means | poll should |
|---|---|---|
| `Reviews paused` | pool exhausted, nothing is coming | report UNRESOLVED and say why |
| `Review failed — the head commit changed` | a round started and died; another is needed | **not** report LANDED; request and wait |
| no notice, review object present | reviewed | LANDED_REVIEW |
| no notice, summary comment only | ambiguous — this is the hole | decide, and say which |

**Wait on a review OBJECT at the expected head**, not on a comment, wherever the two can disagree.

## What NOT to do

Do not remove `--ignore-notice`. It is load-bearing for the paused case, and removing it trades a
false LANDED for a poll that never returns.

Do not verify the fix with this poll. That is #37's shape and this ticket's own subject — build the
expectation from the API by a different route, and construct a failed-review state deliberately
(merge `main` into a branch mid-review, which is how this one was found).

## note 2026-08-26

## note 2026-08-26 — the agent was KILLED by an account limit, not by the work

Terminated mid-task: *"You've hit your weekly limit · resets 6pm (America/Sao_Paulo)"*. Its last
line was **"Both are real. Fixing."** — so it had confirmed two findings and was part-way through
repairing them. What those two are is not recorded anywhere durable, which is the cost of the
interruption.

State left behind: **PR #41 is open**, `gates` and `controls` both **SUCCESS**. Green here means
the tree is consistent, **not** that the ticket is done — the fix was in progress.

**Whoever resumes: re-establish the broken state before trusting anything on the branch.** The
ticket's own `done_when` requires constructing the `Review failed — the head commit changed` state
deliberately, and a half-applied repair is exactly the tree where a control run after the fact
tests the fix rather than the claim (#60).

## note 2026-08-26

## note 2026-08-26 — the two findings the interruption nearly cost, and where the work stands

**The two findings behind *"Both are real. Fixing."*** Both came from CodeRabbit round 3 on PR #41,
both were adjudicated valid, and both are **repaired and pushed** at `b9c8338` — the working tree
is clean and `failed_rounds` carries the per-block read. Recorded here so a third interruption is
cheap.

1. **`failed_rounds` flattened every block's shas and read one of them.** A comment can carry more
   than one failure block; flattening meant a block naming *your* head could be overruled by a
   later block naming another, and the comment would then be dropped — **fail-open, reachable
   inside a single comment**. Repaired by dating each block on its own:
   `dated = [(SHA_ANYWHERE.findall(b) or [None])[-1] for b in blocks]`, and the comment counts
   when **any** block is about the head or cannot be dated. `B24` (a head-matching block followed
   by another head's → `REVIEW_FAILED`) and `B25` (two blocks, neither about this head, beside a
   clean summary → `LANDED_COMMENT`) pin it; `failed_blocks_flattened` restores the old read and
   reddens `B24` alone.

2. **`DECISIONS.md`'s *Would re-open this* row contradicted the row above it.** It said a failure
   block naming no sha could go unseen. It cannot — undated blocks **count**, which is the decided
   behaviour one line up. The reversal condition now names only the case that can happen: a block
   naming a sha that is not the head it died on.

### What the ticket's `done_when` got, and the one part that is a negative

- **The state is constructed, not waited for.** `pr_review_state.selftest` holds a **verbatim**
  `coderabbitai[bot]` failure block and classifies it at the head that block names. The bytes are
  real: PR #39's own instance was rewritten in place and is gone, so they were read from
  `meshery/meshery#21612`, found with `gh api search/issues` — a route independent of this poll.
  They settle 2 things the ticket could only assert: the block is bracketed by its own HTML marker
  `auto-generated comment: failure by coderabbit.ai`, and **the body writes the new head sha into
  itself**, which is exactly why a dead round satisfied the comment arm.
- **The live reconstruction did NOT reproduce, and that is the negative worth keeping.** Pushing an
  ordinary commit into PR #41 while a round was in flight — the in-progress marker observed through
  `gh api`, deliberately not through this poll — produced no failure callout: the marker went
  absent for ~100 s and returned for a new round against the new head. `tasks/162`'s instance came
  from a **merge** of `main` mid-review. **A push mid-round is not sufficient**, and what separates
  the 2 is unmeasured. Do not re-derive this by burning review rounds.
- **`--ignore-notice` keeps working for the paused case, pinned**: `B15`/`B15b` (a pause and a
  spent allowance beside a clean summary must still return `LANDED_COMMENT`), `F6`, `F7`.
- **The ambiguous case is decided**: no notice, a summary naming the head, no review object stays
  `LANDED_COMMENT`. A clean round creates no review object, and `DECISIONS.md` counts 3 of 6
  reviewed heads reaching only that arm. Written beside the `--ignore-notice` definition in
  `pr_review_state.py`, derived in `DECISIONS.md`.

### `--census` cannot exercise this, by construction

40 pull requests, `failed=0` on every row, agreeing with `DECISIONS.md`'s 6-row known-answer table.
The repair is **inert on the stored corpus** — no live pull request carries a failure callout today
— which is the whole reason the state has to be constructed rather than sampled.
