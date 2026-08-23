---
id: 119
title: No gate detects a half-overwritten paragraph, and a 12-word in-block n-gram trigger measures red 4 green 0
status: done
priority: 3
refs: eval/tools/docstat.py, DECISIONS.md, tasks/99, tasks/116
done_when: 'docstat.py grows an in-block duplicate-fragment check, pinned in both directions: red on the pre-fix DECISIONS.md at commit 75dde71 (4 windows of the ''40 of 56 matrix trials at the ceiling with zero variance, not merely near it'' fragment) and green on the live corpus, plus a mutant that deletes the check and a variant that feeds it a duplicated fragment split across a list-item line break. OR a measurement showing the false-positive count does not hold up, which retires it.'
established_by: 'docstat.py grows _check_duplicate_fragment: any 12-word window occurring twice inside one paragraph, list item or frontmatter key, fences and GFM table rows and cross-key frontmatter excluded, wired into --sweep over the same 183-doc reference_docs corpus as the stranded-tail check and into --selftest. RED, from the real blob not a reconstruction: 75dde71:DECISIONS.md gives exactly 4 overlapping windows at line 745 referencing line 737, the half-applied rewrite task 116 removed by hand. GREEN: 0 hits over all 183 reference docs, live AND archive. BROKEN STATE ESTABLISHED FIRST, per rule 14: with that blob planted in the tree, --sweep at HEAD exits 0 and _check_orphaned_tail returns 0 on it; after the fix the same planted tree takes --sweep to exit 1 with 5 red lines, all from this check, and restoring the file returns exit 0. Both read unpiped. WINDOW CHOSEN ON THE LIVE FALSE-POSITIVE COUNT, not on which size sounds general: 10 gives 1 corpus hit, 11 gives 0, 12 gives 0, 14 gives 0, 16 gives 0 and cannot see the defect. The single hit at 10 is an ANTITHESIS - DECISIONS.md headroom blockquote, repetition carrying the argument, a 10-word run - so 11 sits on the boundary and 12 ships with a word of margin at each end. Ticket predicted 2 corpus hits: measured 0, because docstat _fence_mask is already a line-state parser. Ticket did not anticipate frontmatter; tasks/42 done_when and established_by read as one window under _claim_blocks, fixed as ONE BLOCK PER KEY rather than a header mask - masking also measures 0, per-key is strictly more coverage since established_by is routinely a paragraph on one line, and both directions are pinned. MUTANTS AND VARIANTS in eval/tools/fragment_control.py: 12 controls pass unmutated, and 8 mutants each flip a row that names them - no_check, whole_line, one_block, per_line, no_tables, no_fence, flat_frontmatter, window_16. one_block takes the corpus from 0 hits to 676. whole_line is the design measured at 0 on the real defect and it fails all four positives, confirming that sentence and line exact-match is a complete false negative. The ticket''s named VARIANT, a duplicated fragment split across a list-item line break, is red at 3 windows - and it kills no mutant the in-paragraph positive does not, which is stated rather than smoothed over. NON-REDUNDANCY MEASURED IN BOTH DIRECTIONS and pinned: the stranded-tail instance 1f6fb65:eval/FINDINGS.md line 6 repeats a run of exactly 6 words, so the fragment rule scores 0 on it at every window from 7 up, while the stranded-tail rule scores 0 on the fragment defect. Neither check subsumes the other and merging them would lose an instance. Gates after the change, all unpiped: --sweep 0, --selftest 0 with 0 pins wrong, --findings 0, --withdrawn 0, --renumbered 0, withdrawn_control 0, linkcheck 0, tasks.py check 0, fragment_control 0. DECISIONS.md gains a section beside the stranded-tail one; audit-docs SKILL.md integrity row updated, it described only the stranded-tail half. Branch task-119-in-block-duplicate-fragment commit 8f979a4. OWES A FINDING NUMBER from the orchestrator: a check written for one shape of edit debris was green on the other shape of the same damage, and only running each check against the other''s known instance revealed it.'
---

Task 116 removed a duplicated, half-overwritten paragraph fragment from DECISIONS.md's Open section. Every existing gate was green with the defect in place - docstat.py --sweep, --findings, --withdrawn, --renumbered, linkcheck.py, tasks.py check and withdrawn_control.py all exit 0 both before and after the repair. Task 99 is the same class in eval/FINDINGS.md line 6. Three instances, nothing mechanical looking for them.

Measured 2026-08-23 in the task-116 worktree, so the next agent does not re-derive it.

SENTENCE-LEVEL EXACT MATCH DOES NOT WORK. An in-block repeated sentence of 40+ chars scores 0 on the live corpus AND 0 on the pre-fix DECISIONS.md - it misses the real defect entirely, because the duplicated span is a FRAGMENT starting mid-sentence and ending mid-sentence: the tail of one sentence plus the head of the next. This is the obvious property and it is a complete false negative.

12-WORD N-GRAM WITHIN A BLOCK DOES WORK. Repeated 12-word window inside one paragraph or list item, fenced code stripped and markdown table rows excluded:
  RED   pre-fix DECISIONS.md: 4 hits, all four overlapping windows of the true defect.
  GREEN repaired live corpus: 2 hits over 39 live md files, both in .agents/skills/audit-docs/SKILL.md and both a DELIBERATELY repeated shell recipe inside the fence opened at its line 119. They survive only because a non-greedy triple-backtick regex mis-parses its lines 143 and 146, which carry literal triple backticks inside a printf string. A line-state fence parser drops both, giving 0 false positives.

Shorter windows are worse and the count grows with the corpus, which is the open-class signature AGENTS.md warns about: n=8 gives 58 live hits, n=10 gives 27, n=12 gives 8 before the table exclusion. Choose n on the live false-positive count, not on which sounds more general.

Do not ship it without the mutant and the variant. The variant that matters is a duplicated fragment split across a list-item line break, because that is the shape the real one had, and splitting blocks on blank lines alone may not group it.

## measured 2026-08-23, task 119

Shipped. `_check_duplicate_fragment` + `_fragment_blocks` + `_duplicate_fragment_pins` in
`eval/tools/docstat.py`, wired into `--sweep` (over the same 183-doc `reference_docs()` corpus as
the stranded-tail check) and `--selftest`. Controls and 8 mutants in `eval/tools/fragment_control.py`.
Decision recorded in `DECISIONS.md`, sibling to the stranded-tail section. `audit-docs` SKILL.md's
integrity row updated - it described only the stranded-tail half and was about to be read as
covering both.

WHAT THE TICKET GOT RIGHT, AND THE THREE PLACES IT WAS OFF. Re-measured 2026-08-23 in this
worktree; do not re-derive.

1. n=12 within a block, tables excluded, is correct and the RED count is exactly the ticket's:
   4 overlapping windows at DECISIONS.md:745 referencing 737, on the blob at 75dde71.

2. THE LIVE CORPUS MEASURES 0, NOT 2. The ticket predicted the 2 audit-docs SKILL.md hits would
   disappear under a line-state fence parser, and they do: `docstat._fence_mask` already is one.
   Nothing had to be written for that.

3. THE FRONTMATTER IS A THIRD EXCLUSION THE TICKET DID NOT ANTICIPATE, and it is the only hit in
   the archive. `_claim_blocks` sees no blank line in a YAML header and returns the whole header
   as ONE window, so `tasks/42`'s `done_when` and `established_by` - the goal, and the report that
   it was met - read as a duplicated fragment. Fixed as ONE BLOCK PER KEY rather than a mask over
   the header: masking also measures 0, per-key is strictly more coverage at the same cost because
   `established_by` is routinely a paragraph on one line, and a rewrite can strand a fragment
   inside one exactly as it can inside a bullet. There is a pin for each direction.

4. THE TICKET'S SHORTER-WINDOW FIGURES ARE NOT REPRODUCIBLE AND THE SHAPE OF THE CURVE MATTERS
   MORE THAN THEY DO. Measured over 183 reference docs with fences, tables and frontmatter keys
   handled: 10 -> 1 hit, 11 -> 0, 12 -> 0, 14 -> 0, 16 -> 0. The ticket's "n=8 gives 58, n=10
   gives 27" came from a prototype without the table exclusion; with it, n=8 is 3 and n=10 is 1.
   The one hit at 10 is the number that decides the parameter and it is worth knowing by name:
   DECISIONS.md's headroom blockquote is an ANTITHESIS - "a stated mechanic gives an axis with no
   direction and every submission at the same point; a free parameter gives an axis with no
   direction and every submission at a different point" - where the repetition carries the
   argument. Its repeated run is exactly 10 words. 11 measures 0 and 12 ships instead, because 11
   sits directly on that boundary; 12 keeps a word of margin at each end and still clears the real
   defect by three (14 red, 16 green).

5. THE VARIANT THE TICKET ASKED FOR PASSES, AND IT KILLS NO MUTANT THE SAME-LINE POSITIVE DOES
   NOT. Stated rather than smoothed over: a duplicated fragment split across a list-item line
   break is red (3 windows), but so is the in-paragraph positive, and both die to the same four
   mutants. It is kept because it is the real defect's structure, not because it discriminates.

THE BROKEN STATE, ESTABLISHED BEFORE THE FIX (rule 14). With 75dde71's DECISIONS.md in the tree,
`--sweep` at HEAD exits 0 and `_check_orphaned_tail` (#152, written for the sibling defect) returns
0 hits on it. After the fix the same planted tree takes `--sweep` to exit 1 with 5 red lines, all
from this check, and restoring the file returns it to exit 0. Both read unpiped.

THE FINDING THIS OWES, NEEDS A NUMBER FROM THE ORCHESTRATOR: a check written for one shape of
edit debris was green on the other shape of the same damage, and nothing distinguished the two
until they were measured against each other. #152's stranded-tail rule scores 0 on the task-116
defect and this rule scores 4; the reverse also holds - the fragment rule scores 0 on
1f6fb65:eval/FINDINGS.md line 6, because that orphan's repeated run is under 12 words. NEITHER
CHECK SUBSUMES THE OTHER, and the plausible-looking move of merging them into one parameterised
rule would lose one instance or the other. The general form: two defects that a reader describes
with the same sentence can have no trigger in common, and the only way to find that out is to run
each check against the other's known instance.

WHAT I DID NOT ESTABLISH. Whether 12 is right for a corpus twice this size. The count grows with
the corpus for an open-class trigger and the table above is the evidence that this one is not
open-class - but it is 183 documents, and the margin over the antithesis boundary is two words.
`eval/tools/fragment_control.py` prints the corpus count on every run, so the day it stops being 0
the number is in front of whoever ran it. Retune on a re-measured count, never on the argument
that a different size sounds more principled.

## cross-measurement, task 119

Sharpening the previous note's last claim, which was written before it was measured.

I wrote that the fragment rule scores 0 on the stranded-tail instance "because that orphan's
repeated run is under 12 words". Measured: the run is exactly 6 WORDS. Sweeping the window down
over 1f6fb65:eval/FINDINGS.md gives 3 hits at 4, 2 at 5, 1 at 6, and 0 from 7 upward - so the
fragment rule would need a window of 6 to reach that defect, against a corpus that already turns
red at 10. There is no window at which one rule does both jobs.

The full cross-measurement, each check run against the other's real instance:

    1f6fb65:eval/FINDINGS.md:6   stranded tail 1 hit    duplicate fragment 0
    75dde71:DECISIONS.md:745     stranded tail 0 hits   duplicate fragment 4

That is now a PIN, not a sentence. `_duplicate_fragment_pins` asserts the top-right cell on every
`--sweep`, with a message saying that a change there is not a defect - it means the reason for
running two checks has to be re-derived. The alternative was to leave "neither subsumes the other"
as prose in DECISIONS.md, which is precisely the promise-in-a-comment the project keeps paying for.
