---
id: 72
title: docstat --renumbered reports 33 decided stale citations after the 2026-08-23 merge wave, and nothing has repaired them
status: done
priority: 3
refs: 'eval/tools/docstat.py --renumbered, eval/FINDINGS.md, eval/findings/documentation.md #118'
done_when: 'python3 eval/tools/docstat.py --renumbered reports zero DECIDED stale citations, with every repair made to the CITATION and never to a finding number; the undecidable list is read individually and each entry either repaired or recorded as correct, with the count stated. A positive control is required: the tool must still fire on a planted stale citation after the sweep is clean, otherwise a green result is indistinguishable from a tool that stopped looking.'
established_by: 'Branch task-72-renumbered-citations, commits e46807b a52de71 36b3681. 42 citations repaired across 18 files, zero finding numbers touched. DECIDED STALE 33 to 0, verified with a committed tree because uncommitted lines blame to UNCOMMITTED and are skipped, so the first green over a dirty tree measured nothing. UNDECIDABLE 31 read individually: 22 correct as written and 9 stale, all 9 in tasks/ and all citing 119; repaired to 121 (tasks 11 x2, 64), 123 (tasks 29, 65 x2), 120 (tasks 30, 63), 122 (task 56); the list now stands at exactly those 22. POSITIVE CONTROL, and a plant at HEAD cannot fire because a repair committed today carries today findings tree: rooted a citation of 119 at e86e09d0 where 119 was the retired suite and merged it forward, decided went 0 to 1 naming the plant and 122, removing it returned 0. The docstring historical control at 1120695^ still gives decided 8 including eval/PROTOCOL.md:541. Both green-for-the-wrong-reason properties written into _check_renumbered_citations docstring. Gates: --sweep exit 0 over 138 docs, --withdrawn exit 0, 77 worktree task files parse.'
---

Task 58 built --renumbered and repaired the five citations known then, recording that the 21 remaining were read and correct. A later merge wave renumbered #119 four ways - it is #120 (the manifest guard), #121 (the ceiling counter), #122 (the retired suite) and #123 (the tier-1 weight) depending on which sentence you are reading - and 33 citations across 16 files now name a finding that history shows meant something else. Every one of them RESOLVES, which is why --sweep stays exit 0 and nothing else can see them. Found while closing task 63, whose own ticket cites documentation.md #119 for what is now #120; the two citations inside the changed sentences were repaired there and the rest were deliberately left rather than expand that task's diff into sixteen documents.

## What was measured while doing this — do not re-derive it

Branch `task-72-renumbered-citations`. 42 citations repaired across 18 files, none a finding
number.

**The 33 decided** were in 11 files, not the 16 the ticket says — 16 counts the undecidable
half's files too. Every substitution was driven by the tool's own output and refused on any
line where the `#NNN` token was not unique; 0 were refused. Two rows were predicted before
looking and both held (`README.md:305` to #121, `eval/RUNS.md:112` to #123), which is what
licensed the bulk pass.

**The 31 undecidable: 22 correct as written, 9 stale and repaired.** Every one of the nine is
in `tasks/` and every one cites `#119`. tasks/11 twice and tasks/64 to **#121**; tasks/29 and
tasks/65 twice to **#123**; tasks/30 and tasks/63 to **#120**; tasks/56 to **#122**. The 22
correct ones are the 22 the tool still lists, so the undecidable list is now exactly the
adjudicated-correct set and a future entry appearing there is new. Two of them
(`tasks/54:2`, `tasks/55:8`) cite hashless as `FINDINGS 115` / `FINDINGS 119`, which
`_CITE_RX` matches and a `#NNN` search does not; both are correct.

**The check cannot grade a repair, and goes green for two reasons that are not the repair.**
Uncommitted lines blame to UNCOMMITTED and are skipped, so the decided count fell to 0 before
anything was committed — a clean report over a dirty tree is the tool declining to look.
Committed, a repair carries today's findings tree as its authoring tree, so it can never be
stale whatever number was written. Zero after a repair is necessary and not sufficient. Both
properties are now in `_check_renumbered_citations`'s docstring next to THE CONTROL.

**The positive control has to reproduce the mechanism.** A plant at HEAD cannot fire, for the
second reason above. Committing the citation on a branch rooted at `e86e09d0` — where `#119`
was the retired suite — and merging it forward moved decided **0 to 1**, naming the plant and
`#122`; removing it returned 0. The docstring's own historical control also still holds: at
`1120695^` decided is 8 and contains `eval/PROTOCOL.md:541` (#103 to #104).

Gates after: `--sweep` exit 0 over 138 docs, `--withdrawn` exit 0, all 77 worktree task files
parse. `tasks.py check` resolves `tasks/` to the main checkout, so it does **not** validate an
agent's edited copies — parse those with `tasks._parse` against the worktree path instead.
