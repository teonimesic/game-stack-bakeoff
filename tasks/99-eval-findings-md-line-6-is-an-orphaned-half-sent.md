---
id: 99
title: eval/FINDINGS.md line 6 is an orphaned half-sentence left by an edit that replaced the line above it
status: in_progress
priority: 4
refs: eval/FINDINGS.md, eval/tools/docstat.py, tasks/88
done_when: eval/FINDINGS.md line 6 is gone, docstat.py --sweep exits 0, and the sweep gains a check that would have caught it -- an unfenced line in a live or archive instruction document that is a strict suffix of the sentence ending on the line above, pinned red on the real line as it stands at HEAD before the fix and green after
---

Task 88 found it while giving the findings count a producer, and did not touch it: eval/FINDINGS.md is the archive and the ticket did not authorise editing it. Lines 3-6 read 'Check whether a number has been retracted before trusting it -- eval/withdrawn.json is the machine-readable half of that, and docstat.py --withdrawn enforces it over the live documents.' followed by a bare 'number has been retracted before trusting it.**'. git blame: line 4-5 come from 07dea94b, which rewrote the sentence and left the tail of the old one behind. It is not a number and not a claim, so no withdrawal register entry applies; it is text corruption in the file every session is told to read first. Related shape, same paragraph family: an evil merge (8fef835) duplicated the range ROW in AGENTS.md and README.md, which task 88 did fix and now gates.

## note 2026-08-23

The orphaned line is ALREADY GONE, removed as a side effect of `7f01125` bumping the range
sentence for #141. `git blame -L3,7 eval/FINDINGS.md` shows lines 4-5 from `07dea94b` and no
trailing fragment. So the first half of `done_when` is met and you must not go looking for it.

**What is left is the harder half, and it got harder.** `done_when` asks for a sweep check pinned
RED on the real line "as it stands at HEAD before the fix" — and that line no longer exists at
HEAD. The red pin has to come from a **blob**, not from a reconstruction:

    git show 1f6fb65:eval/FINDINGS.md

`eval/tools/tasks_control.py` direction 5 and `eval/tools/lint_coverage.py` are both worked
examples of reading a historical tree through `git cat-file` rather than checking anything out.
A defect retyped from memory is a defect whose shape you have already decided.

**Measure the false-positive count before wiring anything in.** The trigger — an unfenced line
that is a strict suffix of the sentence ending on the line above — is the fourth open-class
trigger this project has tried in two days, and the previous three each turned correct live text
red at 8, 18 and 26 hits with zero true positives (#140, #142, #146). Run yours over all live
documents and publish the count. **If it is not 0, do not ship it** — say so, say what it caught,
and that closes this task as a measured decline.

`.agents/skills/` is now the authoritative skill path, not `.claude/skills/` — the latter is a
symlink. `docstat.py` moved with it.
