---
id: 193
title: 'Bare judge/ and tools/ paths in live documents: settle each document''s path frame and repair the references that do not resolve'
status: todo
priority: 5
refs: DECISIONS.md, tasks/190, eval/tools/docstat.py, eval/tools/lint.py, AGENTS.md
done_when: 'Every backticked judge/- or tools/-prefixed reference in every LIVE document (ARCHIVE_PATHS in eval/tools/docstat.py minus the archive: eval/RUNS.md, eval/SCENES.md, eval/AGENTS.md, eval/PROTOCOL.md, eval/judge/AGENTS.md, eval/judge/RUBRIC.md, eval/judge/JUDGING.md, .github/workflows/README.md, AGENTS.md, .agents/skills/*/SKILL.md, research/10-stack-capability-matrix.md, eval/G4-PLATFORMER.md) is read against its document''s path frame and either resolves or is repaired. The frame question is the adjudication, not a formality: a doc under eval/ writes eval-relative commands (eval/judge/AGENTS.md says python3 judge/bot_mutants.py, which works from eval/), so bare paths there can be correct-in-frame, while a root-frame doc like DECISIONS.md or README.md names paths from the repository root and bare judge/ there is always wrong. Starters (eval/starters/**) are OUT of scope entirely: their tools/ paths are starter-internal and correct, and starter edits are regime boundaries. Counts at filing (line-matches, DECISIONS.md already repaired): RUNS.md 53, SCENES.md 24, eval/AGENTS.md 20, PROTOCOL.md 8, judge/AGENTS.md 6, workflows/README.md 6, G4-PLATFORMER.md 5, judge/RUBRIC.md 3, root AGENTS.md 3, audit-docs SKILL.md 3, add-game SKILL.md 2, research/10-stack-capability-matrix.md 1, judge/JUDGING.md 1. docstat.py --sweep and linkcheck.py exit 0 unpiped after.'
---

Task 190 repaired 23 bare judge/- and tools/-prefixed references in DECISIONS.md, where every one named a file that exists only under eval/ (verified per reference against the filesystem, and against lint.py's own output which prints full eval/-rooted paths). The same shape is present in the other live documents, and no gate covers it: docstat.py --sweep deliberately does not check file paths (AGENTS.md records the exclusion, task 77 measured that it was removed rather than tuned), and linkcheck.py covers markdown links only. A path that does not exist as written is the defect class AGENTS.md calls confidently wrong: a reader following it looks in a directory that is not there.

## note 2026-08-28 (orchestrator) — current at dispatch

**The DECISIONS.md half of this class has LANDED** — task 190's pull request #70 merged as
`f84972d`. Read that diff for the repair pattern before starting: every bare reference was
existence-verified per reference against the filesystem, one deliberate exception was recorded in
prose where the bare form is correct in its own frame (`tools/boundary.gd`, which is
starter-relative), and the scope was held to the one document rather than blind-prefixing the
repo. That last point is this ticket's whole adjudication, now with precedent: **the frame
question is decided per document, and a bare path that resolves from the document's own working
directory is correct, not a defect.**

The per-document counts in the done_when are the filing agent's line-match census, not one I have
re-run — re-derive them before repairing, and treat drift as information about which documents
moved since filing.

**File-conflict check at dispatch:** task 194 (dispatched alongside this one) touches only
`eval/tools/prompt_guard.py` — no document overlap with your scope. Nothing else open touches
your documents. Root `AGENTS.md` IS in your scope (3 refs): it is the always-loaded project
instruction, so an edit there must survive the same scrutiny as any other live document — repair
only references that do not resolve in the document's frame, never reword around them.

Gates unchanged: docstat.py --sweep and linkcheck.py exit 0, both unpiped, in your worktree at
your head.
