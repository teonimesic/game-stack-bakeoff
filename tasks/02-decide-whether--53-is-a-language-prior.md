---
established_by: $14.04 extra to raise arena to n=4. idiomatic ordering reported for THREE games at n=4 each (96 observations), joined on submission not label. #53 NARROWED and CONFIRMED but its ARGUMENT REPLACED. Confirmed: resolved stack pairs never contradict across games; rust>unity resolves in all three; tetris and platformer resolve the IDENTICAL 4 of 6 pairs despite different pack regimes. Refuted: #53's supporting contrast that submission-level scores are 'not stable at all' - they are stable (6/8, 3/8, 2/8 submissions invariant across 4 rounds); that asymmetry was an artifact of n=1 per game, where a single draw carries the full judge SD. Effect is small: all 96 observations are 2/3/4 on a 0-4 scale, stack means span 2.88-3.88. The extension leak remains the live mechanism and is unfixable for this aspect. FINDINGS #79.
id: 02
status: done
priority: 1
title: Find out whether `idiomatic` reads the code or guesses from the language
refs: eval/FINDINGS.md #53, blocked by task 01
done_when: idiomatic's per-stack ordering is reported for three different games, and #53 is confirmed, narrowed or withdrawn on that evidence
---

This project measures how well coding agents build whole games in four stacks
(Rust/Bevy, TypeScript/three.js, Unity, Godot). Submissions are graded in three tiers:
tier 1 programmatic checks, tier 2 a scripted play-bot, tier 3 six LLM-judged 'aspects'
(architecture, idiomatic, fun, fun_frames, ux, audio) that score eight anonymised
submissions side by side as a 'field'. Tier 3 currently has weight 0.00.

WHAT `idiomatic` IS: the aspect that asks whether code is written the way its language and engine
expect — pooling instead of per-frame allocation, correct update/fixed-update separation, and so on.

THE SUSPICION (#53): across every round so far it produces the SAME stack ordering — Rust and
TypeScript at 3.5-4.0, Godot and Unity at 2.5-3.0 — and it barely moves between runs. That
stability could mean it is measuring something real, or it could be a PRIOR: the model's general
opinion of those languages, applied regardless of what was submitted.

WHY IT IS HARD TO TELL: submissions are blinded — paths neutralised to `sim/01.cs`, engine names
substituted, order shuffled — but the language SYNTAX is inherently visible and cannot be removed
without rewriting the code, which would change the thing being judged.

EVIDENCE ON BOTH SIDES: its evidence strings cite specific code with line ranges (a `BoxPool`
implementation, `Mesh.MarkDynamic()`, an Update/FixedUpdate input-latching split with the comment
explaining it). That is a judge reading files. But a judge can read carefully AND still order by
prior — the two are not exclusive.

THE TEST: run it on games it has never seen. Same four stacks, different submitted work. If the
identical ordering appears on arena and platformer, the ordering is about the languages, not the
work, and `idiomatic` can never contribute to a cross-stack comparison — which is this project's
central question. If the ordering moves, it is reading the work.

Depends on task 01. Costs nothing beyond that.
