---
id: 99
title: eval/FINDINGS.md line 6 is an orphaned half-sentence left by an edit that replaced the line above it
status: done
priority: 4
refs: eval/FINDINGS.md, eval/tools/docstat.py, tasks/88
done_when: eval/FINDINGS.md line 6 is gone, docstat.py --sweep exits 0, and the sweep gains a check that would have caught it -- an unfenced line in a live or archive instruction document that is a strict suffix of the sentence ending on the line above, pinned red on the real line as it stands at HEAD before the fix and green after
established_by: 'docstat.py --sweep gains an INTEGRITY check: an unfenced prose line of >=5 words repeating text already in the paragraph above it. Red pin reads the real blob 1f6fb65:eval/FINDINGS.md and flags line 6; green on the same file at HEAD; four green variants of ordinary markdown repetition. 0 false positives over all 180 reference docs, live and archive -- the tighter paragraph-end variant is also 0, so the looser one shipped. Corpus traversal controlled separately: an orphan planted in README.md and eval/findings/documentation.md takes --sweep to exit 1 naming both, reverting clean. The trigger done_when specified (strict suffix of the sentence ending on the line above) does NOT fire on the real blob and would have shipped a gate green on the only known instance; see the ticket note. Branch task-99-orphaned-edit-tail.'
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

## note 2026-08-23, the shipped trigger

**The trigger this ticket specified does not fire on the defect this ticket is about.** That is
the single thing the next reader must not re-derive.

`done_when` asked for "a strict suffix of the sentence ending on the line above". Measured
against the blob the ticket itself pointed at:

    git show 1f6fb65:eval/FINDINGS.md

line 6 is `number has been retracted before trusting it.**`, and the sentence ending on line 5
ends `...enforces it over the live documents.` The fragment is a suffix of the sentence that was
DELETED -- whose head, `**Check whether a`, still sits on line 3 -- not of anything ending on the
line above. Implementing the ticket literally would have shipped a gate that is GREEN on the only
instance of this defect the project has ever seen.

It was caught only because the note above required the red pin to come from a **blob** rather
than a reconstruction. A defect retyped from memory would have been retyped into the shape the
trigger already assumed, and the pin would have passed. That instruction did the work it was
written for; keep it in any ticket of this shape.

**What shipped instead** -- the orphan is a REPETITION, which is what half a replaced sentence
is. An unfenced, non-structural prose line of >=5 words whose normalised text already appears
verbatim in the paragraph above it. Normalisation strips backticks, emphasis runs and terminal
punctuation, because the orphan and its surviving copy differ by exactly the debris of the cut.

**False-positive census, which is what the note asked for before shipping: 0 over all 180
reference documents at HEAD** (live AND archive). The tighter variant that also requires the line
to end its paragraph is also 0, so the looser one shipped -- same measured cost, strictly more
coverage. This is the first trigger of this family to open at 0 rather than at 8, 18 or 26
(#140, #142, #146). Scope deliberately includes the archive, against the formatting-gate rule,
because the one instance was IN the archive and debris is not evidence; a findings entry quoting
such a defect would sit in a fence, which is masked.

**Two controls, because the pins and the corpus are different questions.** The pins prove the
function fires; they say nothing about whether the sweep's traversal reaches real files, which is
rule 12's failure mode. Planting a duplicated line in README.md and in
eval/findings/documentation.md takes `--sweep` to exit 1 naming both, and the tree reverts clean.

Cost: 0.23s added to an 11.8s sweep.

Also corrected while here: nothing. The orphaned line really is gone, as the previous note said,
and AGENTS.md is already current on the `.agents/skills` move -- the copy injected into a fresh
session's context can be a stale snapshot, so check the file at HEAD before acting on it.
