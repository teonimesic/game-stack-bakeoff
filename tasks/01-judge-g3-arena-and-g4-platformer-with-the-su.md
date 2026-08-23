---
established_by: '$61.26. g4_platformer (wg-g4c) has all SIX aspects x2 orders; g3_arena (wg-matrix-2026-08-13) has its FOUR: architecture, fun_frames, idiomatic, ux. Two aspects skipped on arena and both verified as genuine evidence gaps, not oversights - build_pack refuses them: ''audio'' because that field predates the audio task set and has 0 submissions carrying audio evidence, and ''fun'' (frames+telemetry) because g3_arena__ts__t0 has no telemetry evidence. Do NOT re-run those two on arena; the evidence does not exist. Unblocking required rebuilding both fields'' packs uncapped (#69) and, for arena, an exclusion set for 3 starter-drift files (#77) that restored the original starter-identical counts exactly.'
id: 01
status: done
priority: 1
title: Judge g3_arena and g4_platformer with the subjective layer
refs: 'eval/FINDINGS.md #71, eval/judge/JUDGING.md'
done_when: every aspect that HAS evidence to read has a stored round for g3_arena and g4_platformer under eval/runs/, and any aspect skipped is named with the evidence it lacks
---

This project measures how well coding agents build whole games in four stacks
(Rust/Bevy, TypeScript/three.js, Unity, Godot). Submissions are graded in three tiers:
tier 1 programmatic checks, tier 2 a scripted play-bot, tier 3 six LLM-judged 'aspects'
(architecture, idiomatic, fun, fun_frames, ux, audio) that score eight anonymised
submissions side by side as a 'field'. Tier 3 currently has weight 0.00.

THE GAP: every stored tier-3 judgement on disk is for ONE game, g2_tetris3d. `g3_arena` and
`g4_platformer` have never been judged by any aspect. `g1_pong` was judged once and its output
files are missing (see task 04). So every conclusion tier 3 has produced — including findings
#53 and #59, which are quoted in prose — rests on one game out of four.

WHY NOBODY NOTICED: tier 3 carries weight 0.00 in the final score, so its coverage was never
audited. A quantity excluded from the arithmetic still gets cited in the writing.

WHAT TO DO: build judge packs for `g3_arena` and `g4_platformer` from their stored runs and run
all six aspects at both presentation orders. This is a RE-GRADE of stored submissions — no new
build trials, no agent time. Both fields are already geometry-clean, so nothing is blocked.

COST: field calls are $0.63 (audio) to $6.47 (idiomatic) each; roughly $35 per game for all six
aspects at two orders.

This task unblocks tasks 02 and 03, which are the reason it matters.

NOT EVERY ASPECT CAN RUN ON EVERY GAME, AND THAT IS NOT A FAILURE:

An aspect reads a specific kind of evidence, and a game that was never asked to produce that
evidence cannot be judged on it. Measured while working this task:

  - g4_platformer supports all six.
  - g3_arena supports four. `audio` has no audio evidence on that field at all, and `fun`
    needs telemetry that one arena submission does not have.

These are task-scope gaps — the arena task did not ask for what those aspects read — not defects
in the submissions or the judge. Record the skip with the missing evidence named, so a later
reader does not treat the absence as an oversight and re-run it.

The earlier form of this done-when demanded all six on both games, which arena cannot satisfy.
That is the same unachievable-criterion defect recorded against task 08 (#75): a completion
condition placed where the data cannot reach it.
