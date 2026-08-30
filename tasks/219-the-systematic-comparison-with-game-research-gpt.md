---
id: 219
title: 'The systematic comparison with game-research-gpt has never been done: three targeted extractions prove the sibling holds adoptable mechanisms, and the rest of it is unread'
status: done
priority: 3
refs: DECISIONS.md:3651, tasks/29, tasks/55, ~/Documents/heavenstudio/game-research-gpt, research/11-doc-linting-for-agents.md
done_when: 'research/12-sibling-comparison.md exists, read whole sibling-side (docs/, evaluation/ harness, research/ decisions), with every candidate mechanism marked ADOPTED-CANDIDATE-with-ticket, ALREADY-HERE-with-pointer, or REJECTED-with-reason; the three prior extractions (tasks 29 and 55, DECISIONS ADR conditions) are cited as already-landed so nobody re-files them; and the note states what the sibling has that this repo deliberately does not, where that is a decision rather than an oversight. Queue check first: no open task already covers this.'
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/99
established_by: 'PR #99 squash-merged at 25d4cd3; census 20+1+8+7 landed with ticket 220 filed; verified in orchestrator checkout; findings: none'
---

Session task 18 has sat pending across many sessions. The sibling repo at ~/Documents/heavenstudio/game-research-gpt is a mature parallel research programme: a matched four-engine pilot (Godot/Defold/Bevy/Unity), attested agent sessions with disclosed revisions, frozen baseline trees, its own scorer/spec harness, ADRs, and a research synthesis. This repo has mined it exactly three times, each productively: the withdrawal register was imported from its FINAL-CORRECTIONS.json (task 55, done), tier 1 was re-scoped as a gate following its hard-gates-before-scoring model (task 29, done), and ADR reversal conditions were adopted 2026-08-23 (DECISIONS.md:3651). Three hits from three looks is evidence the remaining surface is worth one systematic read - not proof any particular mechanism transfers. The deliverable is a comparison note (research/12-sibling-comparison.md, following research/11's numbering) listing every mechanism the sibling has that this repo lacks, each marked with one of: ADOPTED-CANDIDATE (ticket filed, with the measurement that would accept or reject it), ALREADY-HERE (pointer to this repo's equivalent - most mechanisms will land here), or REJECTED (the reason it does not transfer - different measurement object, different scale, or this repo tried it and measured against). Read-only on the sibling: nothing is written there, and its git metadata failed to read from here (exit 128) which is fine - the trees on disk are the subject. What NOT to conclude: different means better; the sibling measures a different object (a template recommendation for humans vs this repo's agent-capability measurement), so a mechanism can be right there and wrong here, and only this repo's own measurement loop decides adoption. Regime caution: any change this comparison motivates to starters, criteria or prompts goes through the refine loop with a measurement, never directly from the note.

## note 2026-08-30

## 2026-08-30 — done, PR #99

The deliverable is `research/12-sibling-comparison.md` (188 lines, commit b4e2588). Its tables
are the census, derived inside the document: **20 ALREADY-HERE** (each row: the sibling path and
our equivalent — the ticket's prediction that most mechanisms land here was right), **1
ADOPTED-CANDIDATE**, **8 REJECTED** with reasons, **7 deliberate absences** stated as decisions.

- **The one candidate is ticket 220** — trial failure-cause labels with a producer, folding in
  the sibling's rule that a preflight defect is recorded separately from an admitted-agent
  failure. It carries its own accept/reject measurement. Everything else was already built here
  or does not transfer.
- **Read-only on the sibling was verified, not assumed**: `find <sibling> -newermt 2026-08-29`
  returns nothing. Its git metadata still exits 128; the read is against the trees, as the
  ticket anticipated.
- **The sibling's numbers are marked non-comparable** with `eval/RUNS.md` — different judge,
  task set, scale — and the note's one interpretive claim (the play-bot tier structurally
  excludes the sibling's frozen-field-name failure shape, where 3 of their 16 cells failed on
  `observations.independent_processes` field-name mismatches) is labelled INTERPRETATION.

One incident worth carrying: **the first draft quoted "18 comparability breaks" from
`eval/AGENTS.md`'s older sentence; the register in `eval/RUNS.md` was already at its
twenty-eighth entry (2026-08-29).** Rule 5 caught it only because the number was re-read at its
source before landing — a pointer to the register replaced the numeral. Quoting a live
document's count secondhand is quoting a snapshot.

Also confirmed on our side while checking pointers: `runner_capture_selftest.py` lives at
`eval/` top level, not `eval/tools/`; the note cites it name-only rather than guess a directory.

Gates at commit: `docstat.py --sweep` exit 0 (286 docs, new file included); `tasks.py check`
exit 0. Staged before the gates ran, re-checked after; tree clean.

## note 2026-08-30

Review round: the 3 round-1 threads were addressed on-branch (scope not review history; measured status; boundary paragraph split + hyphen) and landed as 8c2590b, after which all 3 showed resolved. CodeRabbit round 2 raised 1 new thread (L57, self-referential table preface) - fixed in 5913c6c along with the same-shaped census closing sentence; latest review over 8c2590b..5913c6c: no actionable comments, 4 of 4 threads resolved, CI controls+gates success at 5913c6c. Incident worth the log: the round-1 commit message was written with printf to stdout without the redirect, so commit -F read the stale round-0 message file; caught by reading back the stored message, amended to 8c2590b before push.

## note 2026-08-30

PR #99 squash-merged at 25d4cd3. research/12-sibling-comparison.md landed: the whole
sibling tree read read-only (verified: no file newer than the read), census 20
ALREADY-HERE with pointers + 1 ADOPTED-CANDIDATE (ticket 220, pending its own
measurement) + 8 REJECTED with reasons + 7 deliberate absences stated as decisions.
Three prior extractions cited as already-landed. Three review rounds - the round-1
approval, the 3 coordinator-flagged threads fixed in 8c2590b, the re-review's 1 thread
in 5913c6c; all threads resolved, LANDED_COMMENT failed=0. Verified in orchestrator
checkout at the content head: gates unpiped green (sweep 286 docs, renumbered 0 stale
of 37, tasks.py check 219 well-formed), census re-derived from the note's tables,
sibling claims spot-checked against the sibling tree (manifest 301, 16 taxonomy
labels, 4 ADRs with reversal conditions, empty decisions/, field-name failure story
verbatim, rubric weights). Findings: none - no new measurement of this repo's corpus;
the note's figures are marked non-comparable with eval/RUNS.md.
