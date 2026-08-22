---
id: 12
title: Explain why idiomatic gives every unity submission the same score
status: open
priority: 1
refs: eval/FINDINGS.md #79, eval/judge/field.py
done_when: the mechanism behind unity's zero within-stack variance is either named in the code and demonstrated, or the hypothesis is reported as unsupported with the measurement that rules it out
---

This project measures how well coding agents build whole games in four stacks (Rust/Bevy, TypeScript/three.js, Unity, Godot), graded in three tiers; tier 3 is six LLM-judged aspects scoring eight anonymised submissions side by side as a field, currently weight 0.00.

THE OBSERVATION: on g2_tetris3d and g3_arena, 'idiomatic' scored ALL EIGHT unity submissions exactly 3 in every one of four rounds. Standard error 0.00, twice, on unrelated work by different agents. On g4_platformer the same aspect DOES vary for unity (2/3/4 present).

WHY IT MATTERS: rule 9 - a repeated identical measurement across independent subjects is the signature of a shared cause, and the shared cause is usually the instrument. Every previous instance of this shape in this project has been an instrument defect (six for six). It is also the sharpest unexplained thing on the board and the strongest remaining lead on whether tier 3 reads submissions or priors.

CANDIDATE MECHANISMS, each cheap to test offline against stored packs:
  - the .cs extension plus a per-language checklist gives unity a default score the evidence rarely moves (this is #53's mechanism, and would predict the same flatness for other stacks - it does not appear for rust or ts)
  - unity packs are the most truncated historically (#62: unity mean 6.1 files dropped vs godot 1.1), so the judge saw least of them and defaulted. NOTE the g4 packs are now uncapped and that is the game where unity DOES vary - a testable coincidence
  - unity submissions genuinely are more uniform, because the template constrains structure more

DO NOT run new trials. All three are answerable by re-reading stored packs and rounds, and by comparing the judge's own evidence strings across the flat and varying games.
