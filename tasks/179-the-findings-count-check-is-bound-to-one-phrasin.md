---
id: 179
title: The findings-count check is bound to one phrasing, and a count 28 short survived beside its own producer
status: todo
priority: 2
refs: eval/tools/docstat.py,README.md,AGENTS.md,tasks/177
done_when: 'Every place a live document states how many findings there are is reconciled against `docstat.py --findings`, not only those phrased ''N numbered findings''. The trigger is chosen the way the census-trigger section of DECISIONS.md requires: candidates measured against the live corpus and selected on false positives, with the count of red lines and the number of shipped pins each candidate gets wrong both recorded - the quantifier-based trigger that section rejected is the obvious wrong answer here too. Pinned red and green, with the ''entries'' phrasing among the pins. A null result is acceptable and closes this: if no closed-class trigger beats the current enumeration on the live corpus, extend the enumeration to cover ''entries'', say so with the numbers, and note that the next unlisted wording will fail the same way.'
---

Found while clearing review on PR #46 on 2026-08-27.

`README.md` line 187 read '143 entries. Findings #19-#189, count and range from `python3 eval/tools/docstat.py --findings`' against a measured **171**. It was 28 short. The producer was named in the same sentence.

AGENTS.md's rule is 'a count with a producer goes stale for an hour; a count with none goes stale forever'. This is the case that rule does not cover: a count with a producer NAMED BESIDE IT and nothing running the comparison. The citation is what makes it dangerous - a reader has every reason to treat the figure as derived, and it was typed.

The mechanism is that `docstat.py --findings` reconciles counts written as 'N numbered findings' - it does enforce that, and correctly reddened `README.md` line 311 during this same session - while line 187 says 'entries' and matches nothing. **Same file, same fact, one gated and one not.** The RANGE on line 187 is checked (my first repair reworded it and the gate went red immediately, which is the system working); the COUNT beside it is not.

This is the open-class trigger problem AGENTS.md's rule audit records at length, in its documented-failure direction: the trigger is an enumeration of wordings, so it fails on the first wording nobody had when it was written. The audit's conclusion applies - prefer a CLOSED class, and choose between candidate triggers on the live-corpus false-positive count rather than on which sounds more general.
