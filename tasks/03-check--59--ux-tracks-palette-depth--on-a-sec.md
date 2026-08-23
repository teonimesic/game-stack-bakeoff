---
established_by: 'ux ~ distinct-colour count recomputed on THREE games (Spearman, average ranks, n=8 each): g2_tetris3d +0.528, g3_arena +0.733, g4_platformer +0.573. #59 CONFIRMED and generalised - it was not a tetris artifact. Robustness: arena has one extreme outlier (godot__t1 at 512 colours vs 3-10 for the rest); dropping it still gives +0.596 at n=7. Colour ranges differ hugely by game (3-512, 6-1254, 31-874), so the aspect tracks relative position within its own field. Pairs with #76: fun_frames correlates -0.120 on the same pixels, so the frames CHANNEL is clean and the defect is in ux specifically. FINDINGS #78.'
id: 03
status: done
priority: 2
title: Check whether `ux` measures usability or just picture quality
refs: 'eval/FINDINGS.md #59, blocked by task 01'
done_when: the ux-score vs distinct-colour-count correlation is reported for g3_arena and g4_platformer
---

This project measures how well coding agents build whole games in four stacks
(Rust/Bevy, TypeScript/three.js, Unity, Godot). Submissions are graded in three tiers:
tier 1 programmatic checks, tier 2 a scripted play-bot, tier 3 six LLM-judged 'aspects'
(architecture, idiomatic, fun, fun_frames, ux, audio) that score eight anonymised
submissions side by side as a 'field'. Tier 3 currently has weight 0.00.

WHAT `ux` ASKS: whether a newcomer could tell what to do, judged from 12 gameplay screenshots.

WHAT IT APPEARS TO MEASURE (#59): its scores correlate +0.735 and +0.823 with the number of
DISTINCT COLOURS in the frames. Colour count splits about 60-fold by renderer — flat-shaded
TypeScript and Unity in the tens, gradient- and antialias-heavy Godot and Rust in the hundreds to
thousands. Palette depth is a property of the rasteriser, not of whether a player understands the
game. `ux` was retired on that basis.

THE PROBLEM WITH THE RETIREMENT: it rests on one game. If the correlation does not reproduce
elsewhere, #59 described one field's accident rather than a property of the aspect, and `ux` may
be recoverable.

WHAT TO DO: recompute the same correlation — ux score against distinct colours per submission,
counted over every pixel of one frame per submission — for `g3_arena` and `g4_platformer`.
Use average ranks, and return None for a constant field: a tie-blind rank manufactures a
correlation with nothing, which has already happened once here.

Depends on task 01 for the ux rounds.
