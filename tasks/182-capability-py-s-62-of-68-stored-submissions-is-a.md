---
id: 182
title: capability.py's '62 of 68 stored submissions' is a hardcoded string, printed beside a computed header reading 69
status: todo
priority: 3
refs: eval/judge/capability.py,DECISIONS.md
done_when: the figure is computed by capability.py from the records it just read, with the population it counted stated beside it and the 2 submissions whose capture failed accounted for explicitly rather than silently - a mutant that freezes the count is red - or the sentence says it is a hand reading of a named date's corpus and DECISIONS.md's row stops saying 'currently'
---

capability.py prints '62 of 68 stored submissions captured at exactly the starter default' as the 'why' text of capture.resolution_as_a_variable. It is a literal in the WHY dict at capability.py:181, not a count of anything the run just read - and the same invocation prints '69 stored submissions' in its own header two screens above it. DECISIONS.md's re-open table quotes it in the present tense: 'Currently 62 of 68 sit on the starter default'. AGENTS.md's rule is that a quantity with no producer goes stale forever, and this one is worse than that: it LOOKS produced, because a producer prints it. It is a capture-geometry figure rather than a tier census, so tasks/169 left it alone deliberately.

## note 2026-08-27

## note 2026-08-27 (orchestrator) — 169 has MERGED and it gives you the rule to apply

`tasks/169` landed and recorded the decision in `DECISIONS.md`: **a corpus figure in a live document
is CURRENT or DATED, and which one is a choice made per figure.** A CURRENT figure must match its
producer re-run in the same session and carry the date it was last read; a DATED one names the
population and date it describes. *The date is provenance, not permission.*

`capability.py`'s hardcoded '62 of 68' is the case that rule does not yet reach, and your ticket
already names why it is worse than an unproduced number: it is printed **beside a computed header**,
so it looks produced. A reader has no way to see that one number came from the tree and the other
from a string literal.

Two things from 169 worth carrying: neither classification was applied as a blanket - '61 of 68'
became '61 of 69' with its numerator right **by coincidence**, and '35 of 68' had its numerator
re-derived from the group table - so decide per figure and show the derivation. And #194 records the
structural reason these drift at all: **a census reads stored gradings, so a criterion repair never
reaches it**, which is why a figure can be correct and stale at once.

`eval/runs/` is read-only for you.
