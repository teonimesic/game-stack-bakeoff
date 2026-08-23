---
id: 26
status: open
priority: 3
title: Let each template showcase its own stack's strengths
refs: blocked by tasks 24 and 25; eval/RUNS.md regime rules
done_when: each template exposes its stack's best available capabilities per the sourced survey, with verify_blind, starter_parity and a RUNS.md regime note; any capability surveyed as available but deliberately not adopted is listed with the reason
---

This project measures how well coding agents build whole games in four stacks (Rust/Bevy,
TypeScript/three.js, Unity 6, Godot 4). Grading is three tiers: programmatic checks, a
scripted play-bot, and six LLM-judged aspects that read code, frames, telemetry and audio.

THE GOAL (operator's, 2026-08-22): each template should showcase the best of its own stack's
capabilities, so the comparison reflects what these stacks can do rather than what four
similarly-modest templates happen to share.

BLOCKED BY TASKS 24 AND 25. Do not start before both land:
  - 24 establishes what each stack can actually do at its pinned version, with effort marked.
  - 25 makes the difference observable. Without it this work cannot be shown to have any effect:
    the graders capture no performance signal and the judges see 12 PNGs at 640x400.

DESIGN — DECIDED 2026-08-22, see DECISIONS.md. Each template at its stack's BEST, not a common floor. The reasoning and its costs are recorded there; do not re-litigate it here. Historical context on what was rejected:

The project's control is **same task, four stacks**. Templates that each showcase different
strengths weaken that control — a difference in outcome could then be the stack, or the
template author's choice of what to showcase. Two coherent designs:

  (a) **Common capability floor.** Every template exposes the same capabilities where all four
      can. Preserves the controlled comparison; measures the stacks on shared ground; ignores
      what makes each distinctive.
  (b) **Each at its best.** Every template showcases its own strengths. Answers "what can a good
      agent build in this stack", which is arguably the more useful question; but cross-stack
      score differences stop being attributable to the stack alone.

They answer different questions and (b) may be the better project. It is not a smaller change —
it changes what the headline finding means.

WHEN IMPLEMENTING (either way):

- Editing `starters/` is a REGIME BOUNDARY. `verify_blind.py`, `starter_parity.py`, and a
  `eval/RUNS.md` note that runs before and after are not comparable.
- `starter_parity` currently checks recipes, determinism, shared launch discipline, audio
  capability and capture geometry. Capability parity is REPORTED, not failed (#72's shape) —
  if the templates deliberately diverge, that note must say so rather than reading as drift.
- Showcase code must be **scaffolding the agent can use, not gameplay the agent inherits**. The
  templates are what an agent starts from; a template that ships the interesting part measures
  the template, not the agent.
- Effort matters more than availability. A capability an agent can reach in a few lines changes
  what gets built; one needing a custom render pass will be ignored under a turn budget and is
  a capability the template has, not one the comparison sees.
