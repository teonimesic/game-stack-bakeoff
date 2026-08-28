---
id: 189
title: Task 171's rally.counts prose was reviewed in another branch's merge and both findings are unaddressed
status: done
priority: 4
refs: eval/RUNS.md, DECISIONS.md, eval/judge/bot_pong.py, tasks/171, pull request 62
done_when: Both passages reworded, with the DECISIONS.md input domain confirmed against eval/judge/bot_pong.py rather than against the review's wording. bot_pong._rally and the criterion itself unchanged. docstat.py --sweep and linkcheck.py exit 0, both unpiped.
established_by: 'Closed as the duplicate its own note declares: items 1 and 4 landed in tasks/188 (PR 69), including the code confirmation of the non-scoring domain this done_when required; nothing dispatched'
---

CodeRabbit raised two readability findings against the rally.counts prose while it sat inside pull request 62's merge commit; being outside-diff, they were never posted against task 171's own pull request. One is a hard-to-parse comparison clause; the other is a DECISIONS.md rule whose stated input domain disagrees with its own exception.

## note 2026-08-27

`rally.counts` is the pong play-bot criterion task 171 repaired: it now requires the rally
counter to rise on every hit the drive can read, rather than passing on a single increment. The
repair landed on `main` as `e03be27`, and it wrote prose into two live documents.

## What is wrong, and how do we know

CodeRabbit reviewed those two passages on 2026-08-27 while they sat in another branch's merge
commit (pull request #62, task 138, review at head `03189ef`) and raised both as
readability findings. They are outside-diff comments, so they were never posted inline against
task 171's own pull request and nothing else has looked at them.

**1. `eval/RUNS.md:2647-2650`** — the comparison clause makes the reader reconstruct it:

> It now requires a rise on **every** hit the drive can read, which is the standard
> `paddle.deflects` beside it already held.

Suggested: state the rule and the matching standard as separate sentences — *"...which is the
standard already used by `paddle.deflects`."*

**2. `DECISIONS.md:3243-3251`** — the rule and its exception name different input domains.
Line 3243 says **every** readable hit must be counted; lines 3249-3251 then exclude a hit that
also carries the point. Suggested: say `non-scoring` in the first rule, so the criterion has one
stated input domain.

## Why it matters

`DECISIONS.md` states what is in force, and the second one is not only wording: as written, the
all-or-nothing rule and its own exception disagree about which hits are in scope, so a reader
implementing against it could count a scoring hit and be contradicted by the sentence below.
`.coderabbit.yaml` asks for the readability class on purpose since 2026-08-23, and `AGENTS.md`
says to act on it.

## What should be done

Reword both passages. **Do not change `bot_pong._rally` or the criterion** — this is the prose
about the repair, not the repair. Confirm against `eval/judge/bot_pong.py` which hits the
criterion actually counts before writing `non-scoring` into `DECISIONS.md`, so the document
states what the code does rather than what the review suggested.

Gates: `python3 eval/tools/docstat.py --sweep`, `python3 eval/tools/linkcheck.py`, both unpiped.

## Where this came from

Task 138's agent declined to make these edits inside pull request #62 and said so in the thread:
the lines arrived there through `git merge origin/main` and are already on `main`, so editing
them would have buried another ticket's wording change inside task 138's squash commit.

## note 2026-08-27

**Superseded by `tasks/188` — close this as a duplicate.**

`tasks/188` was filed from pull request **#61** (task 185) for the same reason and against the
same prose, and it was not yet visible on `main` when this ticket was written. It is the better
ticket: it carries 3 findings rather than 1, it names the line ranges, and its `done_when`
requires the `rally.counts` contradiction to be settled by reading `eval/judge/bot_pong.py`
beside `DECISIONS.md` and saying which of the two is wrong.

The one item this ticket had that `188` did not — the `eval/RUNS.md:2647-2650` comparison clause,
raised on pull request #62 — has been appended to `188` as a fourth item, together with the note
that it and `188`'s item 1 describe the same criterion in two documents and must not be edited to
say different things.

Nothing is lost by closing this. **Two agents filing the same ticket within the hour is the
signal worth keeping**: both were reviewing a merge commit, and CodeRabbit reviews the whole file
set a merge brings in rather than the branch's own diff, so any branch that merges `main` inherits
review comments on other people's landed prose.
