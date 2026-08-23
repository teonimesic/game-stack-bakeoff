---
id: 94
title: disclosure.py located 4 of the 12 rust trials that reported the broken just run recipe - the starter-arrived-broken cue set under-reports by 3x and its docstring states no rate for that family
status: done
priority: 3
refs: eval/tools/disclosure.py, tasks/81, eval/RUNS.md, AGENTS.md rule 11
done_when: either the cue set is widened and re-measured against a hand pass over the same 90 messages, with the new located/hand pair recorded in the docstring for BOTH families and a control showing the widened set does not fire on a trial that reported nothing; or the family is documented as a locator with no measured rate and every doc citing its counts says so
established_by: 'hand pass over all 75 readable stored messages against a criterion fixed before reading: 18 qualify, of which the 12 rust just-run rows equal tasks/81''s independently counted 12. Starter family widened from 4 to 15 located of 18, zero false positives, 12 of 12 on the rust subfamily. The two families were sharing one counter, so the docstring''s 26 for the unverified family was one too high against its hand pass of 31 - comparable number 25, corrected in eval/AGENTS.md, root AGENTS.md rule 11 and the docstring. Controls both ways: 8 corpus rows pinned as MUST_HAVE_NO_STARTER_CUE including the row saying the starter documents the refusal as not a defect, 8 new quiet variants one per guard property, 60 of 75 readable rows do not fire, 15 no_message rows stay no_message. Mutants 6 to 10, all caught, including two whose loss raises the located figure. disclosure --selftest exit 0, disclosure_mutants exit 0, docstat --sweep exit 0, tasks check exit 0'
---

tasks/81 reproduced the default-run defect and, while doing so, counted the corpus directly: 12 rust trials across 5 runs say in their closing message that just run was broken and that they added default-run themselves. disclosure.py fires on 4 of them, and its docstring quotes an under-report ratio only for the what-I-could-not-verify family (26 located against 31 hand-classified), not for this one. A locator that finds a third of a family it names as a family will be read as a census by the next reader, exactly as tasks/81 was written from it. The producer for the 12 is a grep of runs/**/artifacts/*rust*/agent_result.json .result for default-run|two binar|ambiguous|could not determine which binar|just run|cargo run; the 8 it misses are phrased as fixes rather than as complaints - 'default-run = game was needed', 'crates/game gained default-run', 'it needed default-run in the manifest'.

## What was established, 2026-08-23 (branch task-94-widen-starter-cue-set)

TAKEN: the first branch of done_when. The cue set is widened, re-measured against a hand
pass, and both families now carry a located/hand pair in the docstring.

THE HAND PASS. All 75 readable messages of the 90 (15 are no_message: 6 null, 9 the API's
own limit string) were read WHOLE, from artifacts/<trial>/agent_result.json .result, against
a criterion fixed in writing BEFORE reading: the agent states that something in the DELIVERED
TREE - a recipe, manifest, config or harness file - did not work as given, or had to be
repaired before it would. 18 of 75 qualify: 15 core plus 3 borderline. Deliberately excluded,
and this is the boundary the next reader will want: a HOST defect (#49's wedged syspolicyd is
the OTHER family's job, and all four arena3d rows are already located by it); replacing
placeholder content the starter documents as replaceable; closing a coverage gap in the gate
('just verify never loads main.ts, so I added just smoke'); a defect the agent introduced
itself.

THE EXTRACTION WAS PROVED BEFORE THE CENSUS WAS BELIEVED. 12 of the 18 are the rust just-run
subfamily, and that set is EQUAL to the 12 tasks/81 counted independently, by a different
producer, before this cue set existed. Same five runs, same twelve trial ids.

RESULT, measured with the shipped tool over eval/runs:

  starter family      4 -> 15 located of 18 hand, ZERO false positives
  rust just-run       4 -> 12 of 12
  unverified family   25 located of 31 hand, behaviour unchanged

THE DOCSTRING'S 26 WAS ALREADY WRONG, and nothing in the ticket anticipated it. The two
families shared one list and one counter, so wg-matrix g2_tetris3d__rust__t1 - located ONLY
by the starter cue - sat inside the figure compared against a hand pass that never covered
that family. Comparable number 25, not 26. Per stack the only row that moves is rust, 12 ->
11. Corrected in eval/AGENTS.md, root AGENTS.md rule 11 and the module docstring; the archive
copy in eval/findings/one-arm-bias.md is left as-is under the archive rule.

THE THREE IT STILL MISSES ARE NAMED IN THE DOCSTRING, with the reason. All three are godot,
all three an inherited defect in starter-owned code that the agent never attributes to the
starter in words: wg-arena3d g3_arena__godot__t0 (capture_frame synced once, 'every filmed
frame was missing its bursts'), wg-audio48 g2_tetris3d__godot__t1 ('the old latch-and-clear'),
wg-matrix g1_pong__godot__t1 (project.godot warns on every run). Every draft wide enough to
catch them produced false positives, because those sentence shapes are identical to an agent
describing a bug in code it wrote itself. DO NOT RE-DERIVE THIS.

TWO SELFTEST EXPECTATIONS MOVED SIDES, both deliberate, both recorded in the file:
  - VARIANTS_QUIET held 'Bare cargo run -p game failed with ...' asserting this family must
    NOT fire on it. That assertion IS the defect. Moved to VARIANTS_LOCATED.
  - MUST_BE_QUIET held archive-arena2d g3_arena__rust__t0. RUNS.md's 0% for that run is a rate
    for the UNVERIFIED family only - the row says 'default-run had to go into
    crates/game/Cargo.toml' and is one of tasks/81's 12. The pin is now on the unverified
    family (MUST_HAVE_NO_UNVERIFIED_CUE), not on the row's overall status.

CONTROLS, BOTH DIRECTIONS. MUST_HAVE_NO_STARTER_CUE pins 8 corpus rows adjudicated out,
including the sharp one: wg-g4c g4_platformer__rust__t0 says just run IS refused AND that the
starter documents it as a property of Bevy-on-macOS, not a defect to repair. 8 new quiet
variants, one per property of the NOT_A_REPORT guard (documented-as-design, counterfactual,
negated-failure-or-test-count) plus addition-is-not-repair and present-tense-habitual. 60 of
the 75 readable rows do not fire, and the 15 no_message rows stay no_message.

MUTANTS 6 -> 10, all caught. The two worth knowing about are not_a_report and family_split,
because losing either makes the instrument look HEALTHIER - a dead guard and a pooled counter
both RAISE the located figure, and nothing that only asks 'does the family still find what it
should' can see either.

GATES, all unpiped: disclosure --selftest exit 0 against the real corpus; disclosure_mutants
10 of 10 caught; docstat.py --sweep exit 0; tasks.py check exit 0 (99 tasks). The 13
renumbered-citation warnings docstat prints are pre-existing on this branch and untouched.

NO FINDING NUMBER WAS ALLOCATED - 7 agent worktrees were live, which is the collision the
work skill says to avoid. If one is wanted for 'a locator answering two questions kept one
counter, so a figure quoted in three documents was one too high', the orchestrator should
allocate it.
