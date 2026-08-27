---
id: 188
title: Three readability findings against DECISIONS.md prose from tasks 171 and 167, one of them a claimed contradiction in rally.counts
status: todo
priority: 3
refs: DECISIONS.md,eval/judge/bot_pong.py,eval/judge/scene_mutants.py
done_when: each of the 3 is read against its source and either applied or declined in writing, with the reason. Item 1 is settled by reading judge/bot_pong.py's rally.counts beside DECISIONS.md 3219-3227 and saying which of the two is wrong; a decline needs the sentence that resolves the apparent conflict quoted. docstat.py --sweep and linkcheck.py exit 0 after.
---

Three CodeRabbit readability findings against DECISIONS.md prose that landed on main from tasks 171 and 167. They surfaced on PR #61 (task 185) only because merging main put those lines in that review's file set; task 185's diff touches DECISIONS.md at one hunk, @@ -1443,13 +1443,30 @@, and none of these lines. `git log -1 -L 3219,3232:DECISIONS.md` names e03be27 (task 171) and `-L 3309,3312` names 2b9a82a (task 167), so neither belongs to the branch that was asked about them.

The three, verbatim in substance:

1. DECISIONS.md ~3219-3227, FUNCTIONAL: "Limit the rule to non-scoring hits." Line 3219 says every readable hit must be counted while line 3226 excludes a hit that also carries the point, which is an internal contract conflict. Suggested: "Every non-scoring hit visible to the play-bot must be counted. A skipped increment is as incorrect as a late increment. Therefore rally.counts is all-or-nothing, like paddle.deflects in the same loop." This is the one worth reading first: it is a claimed contradiction inside a criterion's own definition, not a style note, and if it is real the rule as written admits two readings of what rally.counts requires.

2. DECISIONS.md ~3230-3232 and ~3278-3282, READABILITY: both re-open notes for rally.counts read as fragments rather than rules. The first opens "To re-open the all-or-nothing reading of `rally.counts`:" with a noun phrase and calls the partial-counter case a "correct submission"; the second packs trigger, consequence, alternatives and rationale into one sentence. A re-open condition is the part of a decision a future session acts on, so it is the worst place for prose that has to be parsed twice.

3. DECISIONS.md ~3309-3312, READABILITY: "Read the count from `python3 eval/judge/scene_mutants.py`, not from this sentence." tells the reader not to trust the sentence they are reading. The producer is right; the self-reference is the defect. Suggested: "Run `python3 eval/judge/scene_mutants.py` to refresh these counts."

Whoever takes this should check each against the source before editing - a review comment is a second opinion, not a finding - and item 1 in particular needs `judge/bot_pong.py`'s rally.counts read alongside the paragraph, because the fix is either the sentence or the criterion and the two are not the same task.
