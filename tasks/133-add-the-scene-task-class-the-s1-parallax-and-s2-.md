---
id: 133
title: 'Add the scene task class: the s1_parallax and s2_glass prompts, rendered per stack from one template each'
status: todo
priority: 1
refs: 'eval/SCENES.md, eval/suites/wholegame_prompts.py, eval/tools/prompt_guard.py, .agents/skills/add-game/SKILL.md, #41'
done_when: Both scenes render for all four stacks through one template each; `prompt_guard.py` exits 0 with no engine name in a scene body and the per-stack rule sets identical; a rendered-prompt snapshot is stored; the byte-identical share across stacks is MEASURED and written down rather than asserted; and no criterion, threshold or tolerance from eval/SCENES.md appears in any prompt - checked by grepping the rendered prompts for the criterion vocabulary, not by reading them.
---

The suite has one task class: whole games, driven by a held-out play-bot. A **scene** is a timed
audiovisual sequence with no player, added to ask what games cannot — how well a stack's rendering
and animation facilities can be driven, and how well an agent drives them. `eval/SCENES.md` holds
the design, the criteria and the research questions; read it first, it is the authority and this
ticket is the bug if they disagree.

This ticket is **the prompts and the contract only**. The probe that grades them is task 134.

## What already exists, and is why this is affordable

Every starter's capture harness makes a frame a pure function of `(seed, ticks, inputs)`
(`eval/starters/*/AGENTS.md`). A scene is that contract with `inputs` dropped: render at a fixed
list of TICK indices, never wall-clock; emit one telemetry record per captured tick; identical
frames for a given seed across runs. Nothing new is needed in the starters for this — verify that
claim per stack before relying on it, because it is the whole basis of the estimate.

## The two scenes

`s1_parallax` (2D) and `s2_glass` (3D), specified in `eval/SCENES.md`. Write them the way
`wholegame_prompts.py` writes games: ONE template per scene rendered per stack through the
vocabulary dicts, not four hand-written copies. 97-98% of every existing prompt is byte-identical
across stacks and the identity is structural — keep it that way.

## The three prompt rules, all of which cost a run when broken

1. Semantically identical across stacks, natively worded. Byte-identical prompts are not
   neutral; they end up in one stack's vocabulary.
2. No type widths.
3. **The prompt is not the rubric.** State what to render and what "done" means. Do NOT name a
   criterion, a threshold or a tolerance. `eval/SCENES.md` lists what each criterion catches —
   that file is for us, and none of it may appear in a prompt. Writing "make sure the water stays
   level" because the probe checks it is teaching to the test and invalidates the comparison.

The probe CONTRACT is legitimately in the prompt: the telemetry field names, the tick list, the
seed handling. Field names are functional spec; thresholds are not.

## The trap that is specific to this ticket

`_preamble()` is shared by every task. An edit aimed at scenes reaches all four games, correctly
where aimed and invisibly everywhere else — that is #41, which contaminated the one experiment
designed around a single variable. If scenes need preamble text that games do not, it goes in a
scene-specific block, and `prompt_guard.py` must still pass.
