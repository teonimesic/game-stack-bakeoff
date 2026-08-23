---
established_by: 'Ran idiomatic on g4c both ways, 2 orders each, $27.30, reading pre-registered in JUDGING.md before spending. Verdict: outcome 3 of 3 - UNINTERPRETABLE at this n. Between-arm tau -0.231 (13 pairs) but the capped arm disagrees with ITSELF at +0.333 (6 pairs), so the effect is not separable from instrument noise; the #68 floor of +0.853 was measured on a different aspect/game and does not transfer. Root cause: 2 distinct scores in every round and 2 of 4 rounds FAIL the ceiling gate. Interpretable result: the judge reads more when given more - 1.74x content gave 115/178 files opened vs 79/98, first audit trail of judge file-opens in the project. Needs a measured floor for idiomatic on g4c (task 08).'
id: 09
status: done
priority: 3
title: Test whether the removed pack budget changed any judgement
refs: 'eval/FINDINGS.md #69, eval/FINDINGS.md #62, eval/IMPROVEMENTS.md 10'
done_when: idiomatic has been run on g4c both with and without the character budget, at both orders, with the reading pre-registered before spending
---

This project measures how well coding agents build whole games in four stacks
(Rust/Bevy, TypeScript/three.js, Unity, Godot). Submissions are graded in three tiers:
tier 1 programmatic checks, tier 2 a scripted play-bot, tier 3 six LLM-judged 'aspects'
(architecture, idiomatic, fun, fun_frames, ux, audio) that score eight anonymised
submissions side by side as a 'field'. Tier 3 currently has weight 0.00.

BACKGROUND: judge packs used to be truncated. `judge/anonymise.py` filled a pack in sorted path
order until it hit 160,000 characters and silently dropped the rest. Measured on one submission,
that hid 32 files down to 15 — 53% of its packable code (#69). The loss was uneven and correlated
with stack: Unity lost 6.1 files on average against Godot's 1.1, because C# spreads across more
files and so exhausts a fixed budget sooner (#62).

The budget has now been removed — the judge is an agent with 120 turns that chooses what to read,
so a pre-filter in front of it only removed files it might have chosen, by alphabetical accident.

WHAT THIS TASK ESTABLISHES: whether the hidden code was actually changing judgements.

METHOD: run `idiomatic` on the `g4c` field twice — once against the old capped packs, once
against uncapped — at both presentation orders. PRE-REGISTER THE READING IN `eval/judge/JUDGING.md`
BEFORE SPENDING:
  - ordering UNCHANGED -> the extra 59% of code did not affect the judgement. That is a finding
    about what the judge attends to, not a non-result.
  - ordering CHANGED -> every stored code-aspect judgement in this project was made on a biased
    sample, and #53 must be re-read from scratch.

Also capture WHICH FILES the judge opens, from its tool calls. Nobody has ever known what a judge
attended to; with the budget gone that becomes measurable, and it makes "did the judge that read
3 files score like the one that read 30?" answerable.

COST: about 4 calls at ~$6.47, plus whatever subagent sampling adds — measure that, it is new.
