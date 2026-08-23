---
established_by: 'Neither renamed nor merely documented - made mechanically answerable. Every bot now declares end_condition (PongBot=''match.ends''; the other three=''gameover.triggers''), with a comment at each declaration explaining why two spellings exist and that pong''s is a match WIN not a loss. precampaign_smoke.py gained a check asserting every bot declares one AND that it names a criterion the bot actually has; pinned both ways (a deliberately wrong declaration fails: "PongBot.end_condition=''gameover.triggers'' is not one of its criteria"). Documented in judge/RUBRIC.md under g1_pong telling a cross-game audit to read the attribute rather than grep for ''gameover''. Smoke now 14 checks, exit 0. No criterion id was renamed, so RUBRIC vocabulary, blinding and mutants are untouched.'
id: 06
status: done
priority: 4
title: Reconcile pong's `match.*` with the other games' `gameover.*`
refs: eval/judge/bot_pong.py, eval/judge/bot_tetris3d.py
done_when: the naming is reconciled, or the difference is documented where someone writing a cross-game sweep would find it
---

This project measures how well coding agents build whole games in four stacks
(Rust/Bevy, TypeScript/three.js, Unity, Godot). Submissions are graded in three tiers:
tier 1 programmatic checks, tier 2 a scripted play-bot, tier 3 six LLM-judged 'aspects'
(architecture, idiomatic, fun, fun_frames, ux, audio) that score eight anonymised
submissions side by side as a 'field'. Tier 3 currently has weight 0.00.

THE FACT: tetris, arena and platformer each have a `gameover.*` criterion checking the game's end
condition. Pong instead has `match.*` (it is first-to-11, so its end condition is a match win).

WHY IT IS WORTH A TASK: the substance is probably fine — pong does check its end condition. But
anyone writing a cross-game audit that asks "does every game verify its own end condition?" will
grep for `gameover` and report a false gap for pong. This project has already lost time to a
mechanical sweep reporting something that was not true.

WHAT TO DO: either rename so the concept has one name across games, or document the equivalence
in a place a sweep author would actually look — the bot module docstrings and the criteria
inventory, not a findings entry.
