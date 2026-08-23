---
id: 121
title: The work skill's review-wait cannot observe a CLEAN review, so every clean PR burns its 15-minute deadline
status: todo
priority: 2
refs: .agents/skills/work/SKILL.md section 6, tasks/108, PR 5 vs PR 1
done_when: 'The recipe in .agents/skills/work/SKILL.md section 6 treats a review as landed when EITHER a coderabbitai review object carries the head sha OR the coderabbitai summary issue comment contains the full 40-character head sha, and it says which one fired. Pinned in both directions against stored PRs: true for PR 5 at 24bc9aff9233cd481534df260c72a8d1077e2dd8 with zero review objects, false for a sha that was never reviewed, and still true for PR 1 where the review object exists. The three guards the current recipe has - exit status, 40 characters, no fallback to a plausible false - are kept, because an API failure must stop the loop rather than contribute a false to it. docstat.py --sweep and tasks.py check exit 0 unpiped.'
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
