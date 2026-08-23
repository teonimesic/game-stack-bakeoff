---
established_by: Surveyed 15 capabilities across the four pinned stacks into research/10-stack-capability-matrix.md, with status, an E1-E4 effort tier, Apple-silicon conditionality and a source per cell, plus 10 unresolved cells each with what would settle it. Ground truth was the vendored Bevy 0.19.0 crate sources, the three 0.185.1 npm tarball with live Playwright probes on the real capture path, live Unity batchmode probes plus the installed 6000.0.45f1 editor, and the installed Godot 4.7.1 binary via doctool, headless ProjectSettings reads and otool. Measured on the machine rather than inferred: a wgpu 29.0.4 adapter probe showing EXPERIMENTAL_RAY_QUERY true but BUFFER_BINDING_ARRAY false, so bevy_solari 0.19 cannot initialise on this M3 Max and fails open with a warn; Unity supportsRayTracing False corroborated by absence of the five Metal acceleration-structure selectors, with the same otool command on the Godot binary as the positive control; Godot Jolt present in-tree but NOT the default, settled behaviourally with both positive controls. Established that three narrowings decide most outcomes: the Rust pin is Bevy's 2d bundle with no PBR, lights, glTF or audio; Unity is Built-in RP with five packages and no physics, particle, audio or animation module; the TypeScript arm films on SwiftShader. Nine of the fifteen capabilities are irrelevant to the current four games and that judgement is argued in the document. DECISIONS.md corrected in two places where the survey contradicted it, and a new task 27 filed for two measured TypeScript capture-harness defects found along the way.
id: 24
status: done
priority: 2
title: Survey what each stack can actually do at its pinned version
refs: research/AGENTS.md, feeds tasks 25 and 26
done_when: research/ holds a sourced capability matrix covering the surveyed capabilities across the four stacks, with effort and platform-conditionality marked; any capability that could not be established at the pinned version is listed as unresolved with what would settle it, rather than omitted
---

This project measures how well coding agents build whole games in four stacks (Rust/Bevy,
TypeScript/three.js, Unity 6, Godot 4). Grading is three tiers: programmatic checks, a
scripted play-bot, and six LLM-judged aspects that read code, frames, telemetry and audio.

THE QUESTION: each engine has advanced capabilities the others lack or reach differently —
hardware ray tracing, GPU instancing, sprite atlasing, texture compression formats, LOD and mesh
simplification, spatial/HRTF audio, compute shaders, multithreaded scheduling, streaming asset
loading. **None of this is currently surveyed, so nobody knows what each stack is capable of
that the templates do not use.**

WHY IT MATTERS: the project's headline is that four templates are indistinguishable. That is
currently a claim about four templates built to the same modest bar, NOT about what the four
stacks can do. If a stack has a capability that would materially change what an agent can build,
and the template never exposes it, the comparison is measuring the templates' common denominator.

WHAT TO DO — this is a research task, offline, no trials:

1. For each stack, survey what is actually available **in the version pinned by the template**
   (Bevy 0.19, three.js as pinned in package.json, Unity 6, Godot 4.7). Version matters: Bevy's
   renderer changes fast and half of what is written about it online is about a different release.
2. Record, per capability: available / not available / available with caveats, WITH A SOURCE.
   `research/AGENTS.md` governs how claims are sourced here — follow it.
3. Separate **capability** from **effort**: something reachable in 5 lines is a different
   proposition from something needing a custom render pass. An agent on a 1000-turn budget can
   reach the first and probably not the second.
4. Flag anything that is platform-conditional. The measurement machine is an M-series Mac —
   hardware ray tracing on Metal is a different story from D3D12 or Vulkan, and a capability
   that does not exist on the measurement machine cannot be part of this comparison at all.

OUTPUT: a capability matrix in `research/`, four stacks by capability, each cell sourced and
marked for effort. It feeds tasks 25 and 26; do not change any template from this task.

WHAT NOT TO CONCLUDE: a capability a stack has is not thereby a capability that matters for
these games. A 3D Tetris does not need HRTF audio. Note which capabilities are plausibly
relevant to the current task set and which are not — that judgement belongs here, where it can
be argued, not inside a template change.

WORKED EXAMPLES FROM THE OPERATOR (2026-08-22) — start here, they are concrete:

**Ray tracing on 3D Tetris.** A ray-traced or path-traced 3D Tetris plausibly looks markedly
better than a flat-shaded one: reflections off the well, contact shadows under a landing piece,
bounce light from the coloured blocks. This is the clearest case where a capability changes the
artifact a judge actually sees.

**Native particle systems.** Unity's Particle System / VFX Graph, Godot's GPUParticles3D,
Bevy's options, three.js's lack of a built-in one. A line-clear or an enemy death is exactly
where particles land, and the effort gap between "engine ships it" and "write it yourself" is
large under a turn budget.

**Native physics.** Unity ships PhysX, Godot ships Jolt, Bevy needs a crate (avian/rapier),
three.js needs a separate library entirely. That asymmetry is real and may be the single
biggest capability difference in the set — survey it carefully, including what the template
would have to pin.

**AND THE INTERACTION THAT MATTERS MOST — check this before recommending anything:**

`ux` scores correlate **+0.53 to +0.73** with the number of DISTINCT COLOURS in the frames
(#59, replicated on three games). Colour count already splits ~60-fold by renderer: flat-shaded
TypeScript and Unity in the tens, gradient- and antialias-heavy Godot and Rust in the hundreds
to thousands. `ux` was RETIRED for exactly this reason — it was measuring the rasteriser, not
whether a newcomer can tell what to do.

**Ray tracing, soft shadows, bloom and particles would all raise distinct-colour count
enormously.** So making the games prettier moves a metric already established as invalid, in
the direction that looks like improvement. Any capability recommendation must say whether its
effect on the judge layer would be a real quality signal or a louder version of #59.

This is the sharpest reason to do task 25 first: without a signal that is not palette-coupled,
"the ray-traced one scored higher" is unfalsifiable.
