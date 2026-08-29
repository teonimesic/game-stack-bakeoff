---
id: 202
title: 'The capture-geometry gate: JUDGING.md and frame_parity.py describe a refused path the packer deliberately replaced with annotate'
status: done
priority: 3
refs: eval/judge/JUDGING.md, eval/judge/field.py, eval/tools/frame_parity.py, eval/RUNS.md
done_when: 'JUDGING.md and the frame_parity.py header describe the mechanism that exists - measured per label, annotated into the brief, never refused - with the #62 contrast and the reason refusing was rejected carried over from the code comment; pack_parity is either deleted or reduced to an honest hand-inspection wrapper whose docstring claims no path membership, the choice recorded; a measurement over the stored packs says whether any submission holds frames of more than one size (the property the first-frame read loses), recorded in eval/RUNS.md or as a finding either way. docstat.py --sweep exit 0 unpiped after.'
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/82
established_by: 'Orchestrator merge, verified against artifacts at branch head 3717b1b4ca5cc2b845b2ee9fd16408c5d3cc4f70: frame_parity --selftest exit 0 unpiped; corpus census re-run over the main checkout''s eval/runs = 67 submissions with frames in 7 run dirs / uniform within submission 67 / 0 unreadable / 804 frames (420x640 x12, 640x400 x768, 720x540 x12, 768x576 x12), matching eval/RUNS.md''s dated section and its three documented divergences; pack_parity absent from field.py at the head; JUDGING.md states measure-annotate-never-refuses with the refusal-rejected reasoning; DECISIONS.md 2026-08-28 entry present; sweep, tasks check, ci_minutes --selftest all exit 0 unpiped; no unresolved threads at the final head (round-5 fix 3717b1b is RUNS.md prose only, verified); squash-merged as a29b35b with gates green and controls in flight at that head, --auto confirmed merged.'
---

JUDGING.md:910-918 (live) says pack_parity runs inside build_pack, that mixed capture geometry is REFUSED beside the completeness gate, and that the remedy for the 420x640 unity trial is to re-film at 640x400 and re-judge. frame_parity.py:6 carries the same refuse claim. None of that is the code: build_pack has no pack_parity call at any committed revision (git log -S pack_parity( over field.py returns only the initial squash a3d0fd1), and its own comment at field.py:581-600 records refusing as WRONG - geometry is a design choice the task left open; the shipped mechanism measures geometry per label from the FIRST frame (field.py:789-799) and annotates the brief when sizes vary (the geom_note in _brief), the annotated-into-a-read-brief contrast the comment draws against #62. A reader following JUDGING.md would re-film a real design difference and call the erasure normalisation - the move the code comment warns against in terms. Two losses ride with it: pack_parity (field.py:538) has no caller while its docstring claims it is code on the path; and frame_parity.geometry() reads every frame and reports uniform_within_submission, a property the first-frame-only inline read cannot see, so a mid-run size change inside one submission has no reader anywhere on the path. eval/findings/certifies-nothing.md:1783 carries the same refuse claim and is ARCHIVE - it stands.

## note 2026-08-28 (orchestrator, before dispatch) — what changed since filing

- Task 201 merged (squash 57f757b; main at ea9a09c). It edited field.py only at lines 1197+ (the claude -p prompt, run_field) and eval/RUNS.md (a dated pre-registration section near the top). This ticket's addresses - field.py:538, :581-600, :789-799, JUDGING.md:910-918, frame_parity.py:6 - are all before that region and still resolve; re-verify them after pulling main rather than quoting them from this ticket.
- eval/RUNS.md takes DATED SECTIONS. Your stored-pack measurement, whichever way it comes out, appends a new dated section after 201's 2026-08-28 one; do not edit that section.
- Findings are allocated at merge, on main, by the orchestrator - never on the branch (the rule that just produced #209). Record the measurement in RUNS.md; if it deserves a finding number, say so in the handback and leave the allocation to the merge.
- The stored runs are UNTRACKED and absent from agent worktrees: any measurement over them takes a --runs-root flag and is run against the main checkout's eval/runs. A one-off hand walk over this corpus has produced a wrong-everywhere census four times in this log (most recently the frame-classification filter in 201's filing pass); build the measurement as a fixture-pinned --selftest like prompt_capture_census.py (new on main, a worked example of exactly this shape) rather than as a shell pipeline.

## note 2026-08-28

## Review loop closed at the 5-round ceiling (PR #82)

Round history, one push per round:

- Round 1 (9414914): 6 findings, all acted on but 2 declined with evidence in-thread
  (reference-style finding links: 150 bare `#NN` citations in DECISIONS.md vs 2 reference
  links total and the instrument reads bare `#(\d+)`; RUNS.md MD040/MD046: no markdownlint
  config exists anywhere in the repo, 13 sibling bare fenced blocks, and converting the
  one measured census block moved docstat's published 71 to 70, so it was reverted).
- Round 2 (64481ef): the corpus key synthesized `f"{run}/artifacts/{trial}"` and never
  read the path it named — now keys on the trial path relative to the root, pinned by
  set-equality of the fixture population (t_clone read under artifacts AND submissions).
- Round 3 (002922c): all-unreadable submission crashed `--run` (IndexError) and an
  all-unreadable run vanished from the census report (silent continue) — both now
  UNMEASURED exits/lines, pinned.
- Round 4 (d942e35): `--selftest --json` still ran the fixture (my refusal sat after the
  branch); whole-corpus all-unreadable returned 0 (fail-open); `--run` kept its own
  first-encounter modal so a tie read as one odd submission. All fixed, all pinned.
- Round 5 (3717b1b): one Minor — RUNS.md described the 804-frame `artifacts/*/eval/frames`
  count as proving the extraction. Reworded: it is a stored-tree cross-check covering the
  standard layout only; the fixture rows (run-a/submissions/t_clone, run-n/capped) carry
  the non-artifacts and nested layouts. **This fix landed after round 5 and is unreviewed.**

Figures stable through every round, re-read at push: 67 submissions with frames in 7 run
dirs, 804 frames (768 at 640x400; 12 each at 420x640, 720x540, 768x576), 0 submissions
holding frames of more than one size, 0 unreadable, the same 3 known cross-submission
divergences (wg-matrix-2026-08-13 unity t1 420x640, wg-audio48-2026-08-14 rust t0 768x576,
wg-audio-2026-08-14 ts t1 720x540).

**No finding number was allocated** — per the dispatch note the orchestrator allocates at
merge. The negative result lives in eval/RUNS.md (dated section, corrected 2026-08-28):
the capture-geometry refusal gate JUDGING.md described never existed; build_pack measures
per label from the first frame and annotates BRIEF.md, and pack_parity is deleted.
