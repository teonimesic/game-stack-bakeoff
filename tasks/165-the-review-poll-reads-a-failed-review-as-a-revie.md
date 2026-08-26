---
id: 165
title: The review poll reads a FAILED review as a review that found nothing
status: todo
priority: 1
refs: 'eval/tools/pr_review_state.py, .agents/skills/work/SKILL.md, tasks/127, tasks/162, #185, #165'
done_when: A branch in the 'Review failed - the head commit changed' state does NOT return LANDED from pr_review_state.py, proved by constructing that state deliberately rather than waiting for it; the notice table in work/SKILL.md names each notice with what it implies for the poll; --ignore-notice keeps working for the paused case, pinned; and the ambiguous case - no notice, summary comment only, no review object - is decided and the decision written where the flag is defined.
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
