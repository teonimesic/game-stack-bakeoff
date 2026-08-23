---
id: 98
title: AGENTS.md's enumeration-trigger rule says to write the trigger as the PROPERTY, and does not say the first property you reach for is usually wrong
status: open
priority: 3
refs: AGENTS.md the rule audit 2026-08-15, tasks/92, DECISIONS.md the census trigger section
done_when: either AGENTS.md states how to choose between candidate properties and cites a measurement, or the omission is recorded as deliberate because the rule is already long enough
---

AGENTS.md's most-cited rule is: a rule whose trigger is a list must be re-derived by every reader who meets an item not on the list, so write the trigger as the RESOURCE or the PROPERTY. Every instance it cites is PROSE - a rule in a document. Task 92 is the first time it fired against CODE, a regex, and the repair produced something the rule does not currently say.

There is more than one candidate property, and picking the wrong one is worse than the enumeration you started with. For the aspect-census trigger the obvious property was the QUANTIFIER - a cardinal or all/every governing aspects. Measured over the live corpus it produced 26 red lines, every one a false positive, against an enumeration that produced 0. The property that worked was the PREDICATE - existence, identity or definition - and the reason it worked is stateable: copula, existential there-are and define are CLOSED classes of English, while the phrasings the original enumerated are open.

The candidate addition, one or two sentences, not a new rule: when you replace an enumeration with a property, more than one property fits, and the live-corpus false-positive count is what decides between them. Prefer a property that is a closed class, because that is what makes it not an enumeration in disguise.

Task 92 did not make this edit itself. AGENTS.md is the highest-traffic file here and 7 tasks were in flight; the work skill says to hand a contended file to the orchestrator rather than risk a conflict in a document that states what is true now.
