---
id: 181
title: AGENTS.md and DECISIONS.md cite findings as bare (#NN), which DECISIONS.md itself decided against
status: todo
priority: 3
refs: AGENTS.md,DECISIONS.md,eval/tools/linkcheck.py,README.md
done_when: AGENTS.md and DECISIONS.md either carry reference-style [#NN] citations with a definition block and linkcheck.py exit 0 over all four LIVE_DOCS, or DECISIONS.md's reference-style decision is narrowed to say which documents it governs and why the others are exempt - and whichever is chosen, a planted dangling [#999] in each converted file is shown red before and the file green after
---

DECISIONS.md's 'A finding cited in a live document is a reference-style link, gated by linkcheck.py' says LIVE DOCUMENT, and it was implemented in README.md alone. README.md carries all 20 reference definitions in the repository; AGENTS.md has 0 against 26 bare (#NN) citations and DECISIONS.md the same shape. Both are in linkcheck.LIVE_DOCS, so the gate is already pointed at them - it just has nothing to check, because a bare (#NN) is not a link. Converting ONE citation is measurably worse than leaving it: applying that to AGENTS.md's (#92) gives 'AGENTS.md:650: shortcut reference #92 has no definition in this file - it renders as literal text', linkcheck exit 1 (measured on task-169's branch, restored). So the file has to be migrated whole - a definition block at its foot plus every citation converted - or left as it is with the decision scoped to README.md. Raised by the review of PR #51 and declined there as outside tasks/169's done_when.
