---
id: 187
title: A rate-limited CodeRabbit reports 'pass', and the JSON rollup mergeable.py reads gives it no conclusion at all
status: done
priority: 2
refs: eval/tools/mergeable.py,.agents/skills/dispatch/SKILL.md,#188
done_when: '`mergeable.py` reports the CodeRabbit row''s DESCRIPTION alongside its state, so ''pass - Review rate limited'' cannot read as ''reviewed'', and says explicitly when a non-required check has no conclusion rather than passing over it. Pinned both directions from recorded payloads, including this exact one: a rate-limited row must not read as reviewed, and a genuinely clean row must. Also decide, and record either way, whether the head CodeRabbit last read should be compared against the branch head - the data is in the review timeline and task 179 established the gap is real, three commits on that branch. A null result closes the second half: if the last-reviewed head cannot be read reliably from the API, say so with what was tried, because ''the orchestrator must ask the agent'' is a worse answer than a producer but a better one than an unstated assumption.'
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/65
established_by: 'Merged as PR #65. The broken state was measured first: mergeable.py 58 printed gates SUCCESS / controls SUCCESS and CodeRabbit appeared in NO line of the output. Two mechanisms combined - report() iterated REQUIRED only, and CodeRabbit arrives as a StatusContext carrying ''state'', with no ''conclusion'' and no ''status'', so the old ''conclusion or status'' read returned None for it anyway. The description, the field carrying the words, is not in statusCheckRollup at all. THE TICKET''S DESIGN WAS CHANGED BY A CASE I HAD NOT SEEN, AND CHANGED CORRECTLY: PR #62''s description is byte-identical to #63''s at a head where no round finished - queued to in-progress to completed in 6 seconds with nothing written - so NO SET OF DESCRIPTION STRINGS separates a reviewed head from an unreviewed one. That is a live counterexample to the open-class trigger this project already rejects. The description is quoted and never matched on; the reading is the review timeline. THE TICKET''S SECOND HALF WAS OFFERED AS A POSSIBLE NULL AND IS NOT ONE: the last-reviewed head is readable from pulls/<n>/reviews via commit_id, filtered to coderabbitai[bot] WITH the [bot] suffix - the exact spelling I got wrong earlier in this session and recorded in AGENTS.md''s rule-12 table. Verified by the orchestrator on the branch: mergeable.py 62 now prints ''CodeRabbit SUCCESS (not required) Review completed'' and then ''coderabbitai[bot] last wrote at 7804aee5; the head f1af78ce is 1 commit(s) later and carries no review of its own'', with the warning that a status is posted when a round is ATTEMPTED. selftest exit 0 and mergeable_mutants.py catches all 14, every mutant turning a NAMED row red - a crash-only catch is reported NOT CAUGHT, so two mechanisms were factored out to fail by disagreement. REPORTED, NEVER GATED, and the reasoning is right: the merge recipe ends by merging main in, so the landing head is unreviewed by construction and a gate would be red on every pull request at merge time. Recorded in DECISIONS.md with its reversal condition. Review round 1 found a genuine correctness defect the agent missed - /pulls/<n>/commits caps at 250, so the gap was counted in a list that need not reach the head, yielding a plausible in-range number. Flagged and not acted on: polling at the merge head returned LANDED_COMMENT at 1s and NOT_YET minutes later, with the summary naming a commit range that excludes that head - one observation, worth a ticket rather than trust. Findings #204.'
---

Measured 2026-08-27 on PR #58. Two views of the same check disagree, and the one a human reads is the misleading one:

    gh pr checks 58   ->  CodeRabbit   pass   0   Review rate limited
    gh pr view --json statusCheckRollup  ->  CodeRabbit -> (conclusion and status both null)

So a review that **did not happen** presents in the checks list as `pass`, with the only contradicting evidence in a description column, and `mergeable.py` - which reads the rollup - sees no conclusion at all and reports the row as neither green nor red.

**This is #188's shape one layer up.** That finding is about the merge gate enumerating the blockers it knew while the host had one it did not. Here the gate CAN see the row and cannot see what the row means, because the meaning is in a field the rollup does not carry. A gate that reports SUCCESS while measuring nothing is the pattern this repository names in AGENTS.md as the single most common one behind its findings.

**It has already changed a decision.** Task 179's last three commits - two of them repairs to real defects CodeRabbit itself had found, one of them the fix for #198 committed inside the file whose job is to be the independent reader - were never read by any reviewer, and the checks row said `pass` throughout. The agent caught it and said so; nothing mechanical would have.

CodeRabbit is NOT a required check, so this never blocked or wrongly unblocked a merge. What it does is corrupt the orchestrator's reading of whether a branch has been reviewed, which is a judgement made on every hand-back.

## note 2026-08-27

Done on PR #65. Both halves of `done_when` are answered; the second half is **not** a null
result.

## What the ticket did not know, and it changes the design

The ticket's case is PR #60: status `success`, description `Review rate limited`, head not
reviewed. **PR #62 is a second case with the same shape and a different description** — status
`success`, description `Review completed`, byte-identical to PR #63's which really was reviewed,
at a head where `pr_review_state.py` answers `NOTICE / Reviews paused` and no round finished.
CodeRabbit posted `Review queued` -> `Review in progress` -> `Review completed` inside 6 seconds
and wrote nothing.

So **no set of description strings separates a reviewed head from an unreviewed one.** Anything
built as *"these words mean no review happened"* is the open-class trigger `DECISIONS.md`'s
census-trigger section rejects, and here it has a live counterexample rather than an argument.
The description is therefore **reported verbatim and never matched on**; the reading is the
review timeline.

## The second half: yes, readable, and here is the address

- `repos/{owner}/{repo}/pulls/<n>/reviews` carries `commit_id` per review. Filter to
  `coderabbitai[bot]` — **with the `[bot]` suffix**; without it the filter is empty on every
  pull request, which `AGENTS.md` rule 12 already records — drop reviews with no
  `submitted_at`, sort by it, and the last one is the head the reviewer last wrote at.
- The description is **not** in `gh pr view --json statusCheckRollup`. A `StatusContext` there
  carries `context`, `state`, `targetUrl` and nothing else. Use the **combined** status
  endpoint `repos/{owner}/{repo}/commits/<sha>/status`, not `/statuses`: the combined one
  returns one row per context already reduced to the latest, so no ordering assumption is
  needed. Pass the head you already read (rule 12).
- `/pulls/<n>/commits` **caps at 250 whatever the pagination**. Assert the list ends at the
  head before measuring any distance in it — otherwise a long branch yields a plausible
  in-range gap. This was found by the reviewer, not by me, and it is pinned as a variant with
  `commit_list_completeness` as its mutant.

## What it must NOT claim, and this is the limit

**A clean incremental round writes no review object.** `DECISIONS.md` records 3 of 6 reviewed
heads reaching only `pr_review_state.py`'s comment arm. So the sha comparison establishes
*nothing was written about this head* — evidence, not a verdict. `mergeable.py` says exactly
that and prints the `pr_review_state.py` command instead of guessing past it. Do not tighten the
wording back to *"was not reviewed"*.

## Reported, never gated — and why a future agent should not "fix" that

The exit code is unchanged. The merge recipe in `.agents/skills/dispatch/SKILL.md` **ends** by
merging `main` into the branch and re-running CI, so the landing head is unreviewed by
construction. A gate on it would be red on every pull request at the moment it is merged, which
is the *"fires where nothing is wrong"* failure `AGENTS.md` rule 16 names. The reversal condition
is in `DECISIONS.md`: a merge policy that does not leave an unreviewed head.

## What is live on PR #65 itself

The tool caught its own ticket's defect on its own pull request. At head `64d78875`:

    gh pr checks 65      ->  CodeRabbit  pass  0  Review rate limited
    mergeable.py 65      ->  ...the head 64d78875 is 2 commit(s) later and carries no
                             review of its own; the status reads success - 'Review rate limited'

## A separate observation, NOT acted on, for whoever owns `pr_review_state.py`

Polling `--expect-head 64d78875...` at 22:41 returned **`LANDED_COMMENT` at elapsed=1s** with
`notice=Review limit reached`. Re-run minutes later, the same command returns `NOT_YET`
(`by_comment=0`), and the summary comment's own Commits block says it reviewed
`8d9cf1f8..b151bd5c` — it does not name `64d78875` anywhere. So the comment body named the head
at the instant of the poll and was rewritten within seconds, and the comment arm read a landing
out of it.

That is `DECISIONS.md`'s own *"CodeRabbit edits comments in place, so a heading outlives the state
it described"*, with the **landing** signal as the transient one rather than the notice. It is
one observation, not two, and I did not try to reproduce it deliberately — worth a ticket, not
worth trusting yet.

## Review rounds

Round 1: 4 comments, all real, all acted on, all 4 threads resolved by the reviewer after the
replies. Round 2: clean — `LANDED_COMMENT` at `b151bd5c`, summary reads *"No actionable comments
were generated"* over `8d9cf1f8..b151bd5c`, which is the whole substantive diff. The `main` merge
after it (`64d78875`, a conflict resolution of a gate count both sides had raised) is unreviewed
and the pool reads **0 remain** for the hour.
