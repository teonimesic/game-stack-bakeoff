---
established_by: 'eval/RUNS.md now states the criterion-count disparity (pong 13, tetris 15, platformer 20, arena 22) as a pooling ban INDEPENDENT of the regime rule, with an explicit note that fixing the regime problem would not retire it, plus the checked exception that tier 1''s 14 criteria apply to all four games. Cross-game aggregates audited: README''s headline ''20 of 24 cells score exactly 1.000'' WITHDRAWN as unreproducible - eight different combinations of three 8-cell groups give 20/24 and it never named which cells, some spanning regime boundaries the docs call void; replaced by per-game figures (wg-matrix pong 5/8 tetris 5/8 arena 5/8; wg-audio48 8/8 and 8/8; wg-g4c 4/8), explicitly not summed. Second aggregate ''380 paired criteria'' flagged as scope-unstated and not reproduced, but NOT withdrawn since the reading may differ.'
id: 05
status: done
priority: 2
title: Write down that a perfect score means different things in different games
refs: 'eval/FINDINGS.md #72, eval/RUNS.md'
done_when: eval/RUNS.md states the criterion-count disparity as a reason not to pool across games, independent of the regime rule, and existing cross-game aggregates are checked against it
---

This project measures how well coding agents build whole games in four stacks
(Rust/Bevy, TypeScript/three.js, Unity, Godot). Submissions are graded in three tiers:
tier 1 programmatic checks, tier 2 a scripted play-bot, tier 3 six LLM-judged 'aspects'
(architecture, idiomatic, fun, fun_frames, ux, audio) that score eight anonymised
submissions side by side as a 'field'. Tier 3 currently has weight 0.00.

THE FACT: tier 2's play-bot has a different number of criteria per game — pong 13, tetris 15,
platformer 20, arena 22. Only three families are shared by all four (`determinism`, `score`,
`state`); the rest are game-specific, which is correct and expected.

THE CONSEQUENCE NOBODY WROTE DOWN: a submission scoring 1.000 on pong cleared 13 hurdles; one
scoring 1.000 on arena cleared 22. Those are not the same achievement, so any average across
games silently treats the easiest game as equal in weight to the hardest.

WHY IT NEEDS ITS OWN ENTRY: `eval/RUNS.md` already forbids pooling across games, but for a
different reason — runs straddle REGIME boundaries (task changes, cap changes, starter edits).
If someone later fixes the regime problem, the ban would look obsolete. It would not be. Two
independent reasons need two entries, or the surviving one gets deleted with the other.

WHAT TO DO: add it to `eval/RUNS.md` in its own right, then grep the docs for any figure that
averages across games and check it against the new rule.
