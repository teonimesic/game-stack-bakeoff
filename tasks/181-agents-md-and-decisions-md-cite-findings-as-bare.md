---
id: 181
title: AGENTS.md and DECISIONS.md cite findings as bare (#NN), which DECISIONS.md itself decided against
status: done
priority: 3
refs: AGENTS.md,DECISIONS.md,eval/tools/linkcheck.py,README.md
done_when: AGENTS.md and DECISIONS.md either carry reference-style [#NN] citations with a definition block and linkcheck.py exit 0 over all four LIVE_DOCS, or DECISIONS.md's reference-style decision is narrowed to say which documents it governs and why the others are exempt - and whichever is chosen, a planted dangling [#999] in each converted file is shown red before and the file green after
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/76
established_by: 'Verified against artifacts at adc332e6 in the agent worktree: diff scope is exactly DECISIONS.md + eval/RUNS.md + linkcheck.py as claimed; the narrowed section states scope as a property (clickable vs raw-text reader) with three explicit re-open triggers; RUNS.md [#46] -> (#46) in the diff; LIVE_DOCS gains eval/RUNS.md, data-only. Reproduced myself, unpiped: linkcheck 0 unresolved across 5 files exit 0; docstat --sweep exit 0; planted dangling [#999] in DECISIONS.md -> exit 1 naming DECISIONS.md:3801, restored -> exit 0 with clean git status. PR body read - it is the permanent record (done_when, outcome, why migration lost, controls both directions). Review: 4 rounds, round 4 LANDED_COMMENT clean; controls CI was pending at handback, green before --auto merged as 7c51c05. Merge: gh pr merge 76 --squash --auto; no branch update needed (behind by 0).'
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

## note 2026-08-28

**Outcome: the decision was NARROWED, not the corpus migrated** — DECISIONS.md's entry now
reads as standing policy: `README.md` cites findings reference-style (`[#NN]` + one definition
block at the foot, gated by `linkcheck.py`); **every other document that cites findings cites
bare `(#NN)`**; the scope is the reader property, not a list of files — *where the reader can
click, cite linked; where the reader reads raw text, the number is the citation*. The
exemption is from the convention, not from the check: a `[#NN]` shortcut in a working document
still goes red unless that file defines it.

**Why migration lost (the adjudication's numbers, 2026-08-28, masked like the tool masks —
fenced lines and inline codespans blanked):** 0 reference links exist outside `README.md`
repo-wide, against 26 bare in `AGENTS.md` (18 distinct findings), 39 in `DECISIONS.md`
(28 distinct), 6 in `eval/FINDINGS.md`, 19 in `eval/RUNS.md`, 8 in `eval/judge/RUBRIC.md`, 19
in `eval/judge/JUDGING.md`, 13 in `eval/PROTOCOL.md`. The wording said *live document*; the
corpus never followed it. A migration also could not be held: the gate reads links that exist
and cannot see a bare citation, so each new bare citation in a converted file is silently
off-convention — and converting ONE citation is measurably worse than leaving it
(re-measured on this head: `[#92]` undefined in `AGENTS.md` is `linkcheck.py` exit 1 at line
665, agreeing with the task-169 measurement). Precedents that declined the linked form:
tasks/121, tasks/124, tasks/146, tasks/137 (which recorded the migration's cost and said
nobody had filed it — this ticket was that filing).

**Controls, both directions.** Red: a planted dangling `[#999]` took `linkcheck.py` to exit 1
naming each of the five files (`README.md`, `AGENTS.md`, `DECISIONS.md`, `eval/FINDINGS.md`,
`eval/RUNS.md`) — run on all five rather than only the converted one, so the exemption is
shown not to have blinded the gate. Variant (rule 15): a well-formed shortcut WITH a
definition planted in `AGENTS.md` still passes — nothing the gate could see was disabled.
Green: the five files as shipped, exit 0 unpiped; `--selftest` PASS; `docstat.py --sweep`
exit 0; every gate run against the STAGED tree with a clean second `git status --porcelain`.

**Two adjacent live defects the narrowing exposed, repaired in the same PR:**

1. `eval/RUNS.md:271` carried the ONLY `[#NN]` shortcut outside `README.md` in the live
   corpus — `[#46]`, undefined, rendering as literal text. It predates `tasks/138`, which
   flagged it and did not act, and it survived because the gate never looked at that file.
   Repaired to the bare `(#46)`, which the narrowed decision makes that file's convention:
   `linkcheck.py eval/RUNS.md` exit 1 before, exit 0 after.
2. `eval/RUNS.md` was missing from `linkcheck.LIVE_DOCS` although `README.md` links into it
   five times — the set's own comment defines the set as "the front door and the documents it
   links into", so the omission was a defect by the tool's own definition (rule 12's shape:
   the address spelled in two places, not asserted). The file joins the set; the gate now
   reads 5 documents and `LIVE_DOCS` is data-only — no tool logic changed.

**Review:** 4 rounds of the 5 ceiling. Round 1 (Minor, acted): state the section as current
policy, not migration history — the census, the first wording, the same-commit narrative and
the scope date came out of the live document (they survive here and in the PR body); the
`decided 2026-08-23` title date and the 18/28 distinct-finding counts behind the
machinery-cost claim were kept deliberately, the count counts being standing evidence, not
narration. Round 2 (Minor, acted): the inherited re-open clause "a second consumer that does
not render Markdown links" could not fire — a non-rendering consumer IS the terminal-reader
case the exemption covers; the triggers are now stated explicitly. Round 3 (Minor, acted):
same paragraph as a three-item list. Round 4: `LANDED_COMMENT`, clean.

**Not established / deliberately not done:** AGENTS.md and README.md are untouched, by
design — the narrowing exists so they do not have to be. No gate now enforces bare-vs-linked
form on NEW prose in any file (the gate sees links, not bare citations) — that gap is the
enforcement re-open trigger now stated in the decision, and nobody has filed it. `controls`
CI was still pending at hand-back; `gates` and CodeRabbit were green at `adc332e`.
