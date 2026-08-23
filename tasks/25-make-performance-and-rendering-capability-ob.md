---
id: 25
status: in_flight
priority: 2
title: Make performance and rendering capability observable at all
refs: eval/starters/_shared/, eval/judge/, blocks task 26
done_when: the probe contract reports the same performance fields with the same units for all four stacks, populated on a real run, and the distribution across existing submissions has been looked at before any of it becomes a criterion
---

This project measures how well coding agents build whole games in four stacks (Rust/Bevy,
TypeScript/three.js, Unity 6, Godot 4). Grading is three tiers: programmatic checks, a
scripted play-bot, and six LLM-judged aspects that read code, frames, telemetry and audio.

THE PROBLEM: **the evidence pipeline is structurally blind to performance and to every advanced
rendering or audio capability.** Measured 2026-08-22:

  - `playbot.json` telemetry records only gameplay events — ticks, event counts, quiet
    fractions, scoring. There is **no fps, frametime, memory, draw-call or resolution field
    anywhere** in `judge/` or in any starter's justfile.
  - frames are **12 PNGs at 640x400**. That is what every frames-reading aspect sees.
  - audio criteria decode clip FILES with ffmpeg. Nothing measures runtime mixing, positioning
    or spatialisation.

CONSEQUENCE: a submission that ray-traces at 4k with HRTF audio and one that draws flat quads
at 640x400 produce **identical evidence**. Task 26 would change the templates and change no
score, and the LLM judges — which see those same 12 low-res stills — would not see it either.

**So this task gates task 26.** Showcasing capabilities the harness cannot observe is
unfalsifiable work: it cannot be shown to have helped or hurt.

WHAT TO DO:

1. Decide what is worth capturing. Candidates, cheapest first: frametime distribution (not mean
   — the tail is what a player feels), peak memory, draw calls, texture/VRAM budget, capture
   resolution, and whether audio is positioned. Prefer signals every stack can report honestly.
2. Extend the probe/telemetry contract in `eval/starters/_shared/` so all four report the same
   fields with the same units. **A field one stack cannot fill is worse than no field** — it
   becomes a stack-correlated gap, which is this project's most-repeated defect (#62, #72, #77).
3. Only then decide whether any of it becomes a CRITERION. Capturing is cheap and reversible;
   scoring changes what agents optimise for and is a regime boundary.
4. Consider raising or varying capture resolution — but note geometry is a submission's own
   design choice (#81), so any change must not force uniformity.

WHAT NOT TO DO: do not add a criterion in the same change as the capture. Capture first,
look at the distribution across existing submissions, then decide. A criterion added at the
same time as its measurement has no baseline to be calibrated against.
