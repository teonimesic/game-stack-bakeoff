---
id: 121
title: The work skill's review-wait cannot observe a CLEAN review, so every clean PR burns its 15-minute deadline
status: in_testing
priority: 2
refs: .agents/skills/work/SKILL.md section 6, tasks/108, PR 5 vs PR 1
done_when: 'The recipe in .agents/skills/work/SKILL.md section 6 treats a review as landed when EITHER a coderabbitai review object carries the head sha OR the coderabbitai summary issue comment contains the full 40-character head sha, and it says which one fired. Pinned in both directions against stored PRs: true for PR 5 at 24bc9aff9233cd481534df260c72a8d1077e2dd8 with zero review objects, false for a sha that was never reviewed, and still true for PR 1 where the review object exists. The three guards the current recipe has - exit status, 40 characters, no fallback to a plausible false - are kept, because an API failure must stop the loop rather than contribute a false to it. docstat.py --sweep and tasks.py check exit 0 unpiped.'
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/7
established_by: 'Three defects fixed and pinned both ways on live PRs: a clean review creates no review object (PR 5, 6 both false under the old recipe); the head sha appears in the summary comment mid-round, so sha-matching alone is fail-open (0 with the not-clause, 1 without, on PR 5 stored body; confirmed live on PR 7 for 317s); and a coderabbitai reply creates a review object stamped with the current head, which made the poll report LANDED 33s after a push on a round that had not started (PR 4 head is a reply container only; 23 objects, 15 real bodies 2829-18578 chars, 8 containers at 0, no overlap). Recipe extracted from the shipped skill text and re-run: 0 false negatives, PR 3 true negative kept. Gates unpiped: docstat --sweep 0, run-gates pre-commit 0 with 100 PASS 0 FAIL, linkcheck 0, tasks.py check 0, withdrawn_control 0, findings_control 0, triage_control 0, dead_private_control 0, skill_layout_control 0. docstat pins 18, 0 wrong; mutant reverting the exemption to prefix matching turns exactly the 2 new red pins wrong. PR 7, 2 review rounds.'
---

Measured on PR 5, 2026-08-23, task 118. The recipe polls repos/OWNER/REPO/pulls/N/reviews for a coderabbitai review whose commit_id equals the head sha. When CodeRabbit finds nothing actionable it creates NO review object at all: PR 5 returned reviews=0 and pulls/5/comments=0 while its issue comment read 'No actionable comments were generated in the recent review' and named the reviewed head sha in full. So the loop reported reviewed=false for 10 minutes on a PR that had already been reviewed, and would have run to its 15-minute deadline and reported a no-review that never happened. The pin in the skill was taken on PR 1, which HAD actionable comments and has 3 review objects, so the control shared the defect it was controlling for - AGENTS.md rule 12 and finding 37. The fail direction is slow rather than wrong, and it costs 15 idle minutes on exactly the good outcome, which is the common one.

## note 2026-08-23

## measured further on PR 5, 2026-08-23, while task 118 was waiting on it

**The obvious fix has a false positive, and it fired on the first use.** Treating *"the
coderabbitai summary comment contains the head sha"* as landed reported `REVIEW LANDED`
**31 seconds** after the round-2 push, while the review was still running. The summary
comment names the head sha inside its **in-progress** block:

```
<!-- This is an auto-generated comment: review in progress by coderabbit.ai -->
> Currently processing new changes in this PR. This may take a few minutes, please wait...
...
> Reviewing files that changed from the base of the PR and between <base sha> and <head sha>.
```

The *"No actionable comments were generated"* line sitting below it at that moment was the
**previous** round's verdict, so the check would have handed back a clean result the reviewer
had not yet reached — a fail-**open** defect, and worse than the timeout it was fixing
(AGENTS.md rule 7).

**What actually separates the two states** is the in-progress marker, which CodeRabbit removes
when it edits the comment in place. Measured in three states of one comment:

| state | names head | has in-progress marker | verdict wanted |
|---|---|---|---|
| round 1 finished (`24bc9af`) | yes | no | landed |
| round 2 running (`f022ebc`) | yes | **yes** | not landed |
| round 2 finished (`f022ebc`) | yes | no | landed |

So the rule is: **a coderabbitai review object at the head sha, OR a coderabbitai issue
comment that names the head sha AND does not contain
`auto-generated comment: review in progress by coderabbit.ai`.**

```bash
DONE=$(gh api "repos/$REPO/issues/$PR/comments" \
  --jq "[.[] | select(.user.login==\"coderabbitai[bot]\") | .body
        | select(contains(\"$HEAD\")) | select(contains(\"$INPROG\") | not)] | length") || exit 1
```

`0` while round 2 was running, `1` once it finished, and it is a count from one process — no
pipe whose exit status is the last stage's, and no `grep` that exits 1 on zero matches.

**Round 2 took 35 seconds** (push 13:45:11, in-progress at 13:46:16, finished by 13:46:51) for
a 3-commit, 1-file-plus-2-docs diff. Both rounds returned *"No actionable comments"* with
**zero review objects**, so PR 5 is a two-round positive control for the whole defect: the
shipped recipe would have timed out twice, at 15 minutes each.

**Run ids, if you need to tell the rounds apart**: round 1 `d76bfef7-f32f-4875-a25b-dd73973e344d`,
round 2 `5bac98f8-b1cd-48f1-9d23-154f077154bd`. They are in the summary comment and are the only
thing that distinguishes one round's verdict from another's, because the comment is edited in
place and keeps no history.

## note 2026-08-23

Done on branch `task-121-review-wait-cannot-observe-a-clean-review`, PR 7. Three defects, not
one — the ticket named the first, the second was already in the ticket's own note, and the third
was found by running the procedure on its own pull request.

## The check, as shipped

`.agents/skills/work/SKILL.md` §6. A review has landed at this head when **either** a
`coderabbitai[bot]` review object **with a non-empty body** carries the head sha, **or** a
`coderabbitai[bot]` issue comment names the head sha and does not carry
`auto-generated comment: review in progress by coderabbit.ai`. It says which arm fired. Both
queries are `gh api --paginate` aggregated by an external `jq -s` over a here-string.
`DECISIONS.md`'s review-completion entry is the authoritative record; the skill points at it.

## What the next agent must not re-derive

**1. `select(.body != "")` is load-bearing and the reason is not obvious.** When
`coderabbitai[bot]` replies to a comment, GitHub creates a *review object* to hold the reply and
stamps it with the pull request's **current head** — body empty, 1 reply, 0 top-level comments.
A check reading only `.commit_id` cannot tell it from a review. **The agent triggers this by
following §6, which tells it to reply to what it declines.** Replying to 3 comments made the poll
report `LANDED` 33 seconds after the next push, on a round that had not started; the real review
arrived ~5 minutes later. Same shape as the already-recorded `select(.user.login=="coderabbitai[bot]")`
lesson — a check on an unfiltered stream is one the agent can trip by acting normally.

**2. PR 4 is the pin for that.** Its head `372681afa673c87aec8d059e6d621b314907778a` carries
**only** a reply container, so the review arm must not fire there and the comment arm must. Its
commit `1937817f3c06aae384d01049ed9c07919a54ade9` carries a real review — the green half.

**3. Neither arm alone works, and each fails on the PR the other covers.** PR 1's summary comment
contains **no 40-character sha at all** (only `4f95b`), so the comment arm cannot fire there.
PRs 5 and 6 have no real review object at head, so the review arm cannot fire there. A control
taken on PR 1 alone shares the defect it is controlling for — which is how the original recipe
shipped broken.

**4. PR 3 is the true negative.** Head `6e0c843…`, last review at 16:25:14Z on `4062e61`, then
commits at 16:25:34Z and 16:35:34Z. Both arms must stay quiet. Use it before believing any change
to this check.

**5. The in-progress marker is the only thing separating a finished round from a running one.**
CodeRabbit edits the summary comment in place and keeps no history, so the *"No actionable
comments"* line visible mid-round is the **previous** round's verdict. The run ids in the comment
are the only way to tell rounds apart.

**6. The 40-character guard changed class.** `contains("")` is true for every string, so with the
comment arm an empty `$HEAD` would report **every** pull request reviewed. The reviews arm failed
the other way (`index("")` is `null`). The guard now protects against a fail-open defect, not a
slow one.

**7. Pagination.** `gh api` returns 30 records without `--paginate`, and the review at the head sha
is the **newest** — the first to fall off page 1. PR 6's reviews at `per_page=2`: 2 unpaginated,
10 paginated. `gh` rejects `--slurp` alongside `--jq`, so aggregate with an external `jq -s` over a
**here-string**, never a pipe.

## Two mistakes I made, recorded because both were the project's own rules failing on me

**I published two wrong counts.** "22 review objects, 16 real, 6 containers" — the true figures at
that moment were 14 and 8. I counted rows off a printed table instead of running a producer, which
is exactly what `AGENTS.md`'s quantity row forbids. The producer is now published beside the figure
in `DECISIONS.md`; re-run it rather than quoting the line, because the population grows with every
review.

**My first red control was a false green.** Testing the phantom-flag gate, I planted
`--zzqphantomflag` — and `_DELIBERATELY_FAKE` in `docstat.py` matches the substring `phantom`, so
the sweep reported clean about a line it never read. **Never put an exemption word inside a planted
token.** `--zzqnotaflag` works. This is recorded in the comment beside `FOREIGN_FLAGS_EXACT`.

## Collateral changes

- `eval/tools/docstat.py`: gh's `--paginate`, `--slurp`, `--jq` are foreign flags, matched by
  **equality** in a new `FOREIGN_FLAGS_EXACT` frozenset rather than by prefix — a prefix entry
  would silently exempt a future `--jq-local` of ours. `FOREIGN_FLAG_PREFIXES` is untouched;
  `--experimental-` and `--max-budget` need prefix semantics. 4 new pins in `_bare_flag_pins`
  (18 total, 0 wrong), and a mutant reverting to prefix matching turns exactly the 2 new red ones
  wrong.
- `DECISIONS.md` review-completion entry rewritten: the disjunction, the per-PR table, 5 rejected
  alternatives with the measurement that rejected each.

## Needs a finding number

A poll loop that reads **one of the shapes an event can take** is a mechanism that runs, returns a
plausible in-range answer and measures nothing. Two of the three defects here were of that shape,
and the control for the original was taken on the one pull request that had the shape it could see.
The third is sharper and worth the number on its own: **the agent's own prescribed conduct —
replying to a review — manufactured the false positive**, so the instrument was measuring the
observer.

## Review

5 comments round 1, 1 round 2. Accepted: pagination, the empty-`$HEAD` description, exact matching
for the exemption. Accepted in part: moving the derivation to `DECISIONS.md`, digits for genuine
counts. **Declined:** reference-style links for `tasks/108` and `tasks/121` — `DECISIONS.md` line
1772 defines that rule for **finding** citations (`[#68]` into `eval/findings/`), `linkcheck.py` is
exit 0, and no reference-style task link exists anywhere in the repository. Every decline has a
reply in the PR thread. Handed back at the 2-round budget rather than opening a third.
