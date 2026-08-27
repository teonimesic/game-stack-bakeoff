---
id: 182
title: capability.py's '62 of 68 stored submissions' is a hardcoded string, printed beside a computed header reading 69
status: todo
priority: 3
refs: eval/judge/capability.py,DECISIONS.md
done_when: the figure is computed by capability.py from the records it just read, with the population it counted stated beside it and the 2 submissions whose capture failed accounted for explicitly rather than silently - a mutant that freezes the count is red - or the sentence says it is a hand reading of a named date's corpus and DECISIONS.md's row stops saying 'currently'
---

capability.py prints '62 of 68 stored submissions captured at exactly the starter default' as the 'why' text of capture.resolution_as_a_variable. It is a literal in the WHY dict at capability.py:181, not a count of anything the run just read - and the same invocation prints '69 stored submissions' in its own header two screens above it. DECISIONS.md's re-open table quotes it in the present tense: 'Currently 62 of 68 sit on the starter default'. AGENTS.md's rule is that a quantity with no producer goes stale forever, and this one is worse than that: it LOOKS produced, because a producer prints it. It is a capture-geometry figure rather than a tier census, so tasks/169 left it alone deliberately.
