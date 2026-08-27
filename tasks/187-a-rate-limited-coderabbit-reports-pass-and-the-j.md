---
id: 187
title: A rate-limited CodeRabbit reports 'pass', and the JSON rollup mergeable.py reads gives it no conclusion at all
status: in_review
priority: 2
refs: eval/tools/mergeable.py,.agents/skills/dispatch/SKILL.md,#188
done_when: '`mergeable.py` reports the CodeRabbit row''s DESCRIPTION alongside its state, so ''pass - Review rate limited'' cannot read as ''reviewed'', and says explicitly when a non-required check has no conclusion rather than passing over it. Pinned both directions from recorded payloads, including this exact one: a rate-limited row must not read as reviewed, and a genuinely clean row must. Also decide, and record either way, whether the head CodeRabbit last read should be compared against the branch head - the data is in the review timeline and task 179 established the gap is real, three commits on that branch. A null result closes the second half: if the last-reviewed head cannot be read reliably from the API, say so with what was tried, because ''the orchestrator must ask the agent'' is a worse answer than a producer but a better one than an unstated assumption.'
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/65
---

Measured 2026-08-27 on PR #58. Two views of the same check disagree, and the one a human reads is the misleading one:

    gh pr checks 58   ->  CodeRabbit   pass   0   Review rate limited
    gh pr view --json statusCheckRollup  ->  CodeRabbit -> (conclusion and status both null)

So a review that **did not happen** presents in the checks list as `pass`, with the only contradicting evidence in a description column, and `mergeable.py` - which reads the rollup - sees no conclusion at all and reports the row as neither green nor red.

**This is #188's shape one layer up.** That finding is about the merge gate enumerating the blockers it knew while the host had one it did not. Here the gate CAN see the row and cannot see what the row means, because the meaning is in a field the rollup does not carry. A gate that reports SUCCESS while measuring nothing is the pattern this repository names in AGENTS.md as the single most common one behind its findings.

**It has already changed a decision.** Task 179's last three commits - two of them repairs to real defects CodeRabbit itself had found, one of them the fix for #198 committed inside the file whose job is to be the independent reader - were never read by any reviewer, and the checks row said `pass` throughout. The agent caught it and said so; nothing mechanical would have.

CodeRabbit is NOT a required check, so this never blocked or wrongly unblocked a merge. What it does is corrupt the orchestrator's reading of whether a branch has been reviewed, which is a judgement made on every hand-back.
