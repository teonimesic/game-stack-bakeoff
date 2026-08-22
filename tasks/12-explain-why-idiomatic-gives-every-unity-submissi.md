---
established_by: Hypothesis UNSUPPORTED, with the measurements that rule it out. Three candidates each eliminated offline, no new trials: (1) truncated packs - REFUTED, g3_arena is uncapped and flat while the g4_platformer CAPPED arm varies at SD 0.50, so completeness does not predict flatness; (2) caching or identical reasoning - REFUTED, 4 of 4 evidence strings are distinct in every flat cell, so the judge re-derives the same verdict from different observations; (3) nothing to say so it defaulted to the anchor - REFUTED, 883-1011 chars of specific detail with line references. THE ACTUAL FINDING is a framing error: rule 9 is about independent SUBJECTS agreeing, and this was ONE subject measured four times, where low variance is reliability rather than collusion. The only independent agreement is between two trials landing on the field's modal anchor. Residual pattern is chance: P(a specific stack has both trials invariant in >=2 of 4 games) = 0.076, P(any of the four does) = 0.272. Unity was noticed because it was looked at. SIDE FINDING worth more than the investigation: the judge opens nearly every evidence string by naming the stack, and on g4_platformer wrote 'EngineBehaviour = renamed MonoBehaviour' - it reverse-engineered anonymise.neutralise() and reported the original token. Feeds task 14. FINDINGS #81.
id: 12
title: Explain why idiomatic gives every unity submission the same score
status: done
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
