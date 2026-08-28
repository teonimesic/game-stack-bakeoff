---
id: 181
title: AGENTS.md and DECISIONS.md cite findings as bare (#NN), which DECISIONS.md itself decided against
status: todo
priority: 3
refs: AGENTS.md,DECISIONS.md,eval/tools/linkcheck.py,README.md
done_when: AGENTS.md and DECISIONS.md either carry reference-style [#NN] citations with a definition block and linkcheck.py exit 0 over all four LIVE_DOCS, or DECISIONS.md's reference-style decision is narrowed to say which documents it governs and why the others are exempt - and whichever is chosen, a planted dangling [#999] in each converted file is shown red before and the file green after
---

DECISIONS.md's 'A finding cited in a live document is a reference-style link, gated by linkcheck.py' says LIVE DOCUMENT, and it was implemented in README.md alone. README.md carries all 20 reference definitions in the repository; AGENTS.md has 0 against 26 bare (#NN) citations and DECISIONS.md the same shape. Both are in linkcheck.LIVE_DOCS, so the gate is already pointed at them - it just has nothing to check, because a bare (#NN) is not a link. Converting ONE citation is measurably worse than leaving it: applying that to AGENTS.md's (#92) gives 'AGENTS.md:650: shortcut reference #92 has no definition in this file - it renders as literal text', linkcheck exit 1 (measured on task-169's branch, restored). So the file has to be migrated whole - a definition block at its foot plus every citation converted - or left as it is with the decision scoped to README.md. Raised by the review of PR #51 and declined there as outside tasks/169's done_when.

## note 2026-08-28

## note 2026-08-28 (orchestrator) — current at dispatch

**The conflict window that held this ticket is closed** — DECISIONS.md and AGENTS.md have
stopped moving: task 190 (PR #70, `f84972d`) prefixed 23 bare `judge/`/`tools/` paths in
DECISIONS.md, task 193 (PR #72, `2303ec2`) prefixed the 3 in root AGENTS.md, and the
findings-range lines in both files now read #19-#208 (finding #208 landed this session). No
open task touches either file; task 197 touches only README.md, so a whole-file citation
migration here conflicts with nothing in flight — but README.md IS in linkcheck's live set and
197 will edit it, so if your migration touches README's definitions block, expect 197's PR to
land first and rebase against it rather than editing definitions yourself.

**What moved under your census:** the bare-#nn counts (26 in AGENTS.md at filing) need
re-derivation — DECISIONS.md gained prose from tasks 190/167-era decisions and now carries the
`#19-#208` range plus new citations. One signal from 190's review round worth weighing in the
migrate-or-narrow adjudication: the reviewer accepted that DECISIONS.md's citation convention
is **bare `#nn` throughout** (173 plain vs 2 linked, both `#95` with definitions into
`eval/findings/`), which is evidence for the *narrow the decision* outcome rather than a
173-citation migration — but that is your call to make from the current text, not a
prescription. Whichever outcome: the planted dangling `[#999]` red-before/green-after control
in the done_when is the part that makes it more than an opinion.
