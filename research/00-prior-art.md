# Prior art: agents building games (found 2026-08-10)

## godogen — https://github.com/htdt/godogen
Generator that emits *game repositories* seeded for agent operation. Closest existing
thing to what we want.

- `./publish.sh --engine [godot|babylon|bevy] --agent [claude|codex] --out [path]`
- Engines: Godot 4 (C#/.NET, build-time scene generation), Bevy (Rust/ECS, **offscreen
  capture**), Babylon.js (TS/Vite, live URL)
- Structure: `prompts/runtime.md` (runtime manifest), `asset-gen/` skill,
  `engines/` per-engine guides, publish script renders engine × host-agent
- **Verification philosophy**: agent judges the *running game* (live URL or recorded
  clip), not just a clean compile. "Visible defects drive the next iteration."
- Asset gen: Gemini (character refs), Grok (textures), Tripo3D (rigged 3D models)
- No published performance comparison between engines.

Takeaway: validates the multi-engine + offscreen-capture + agent-judges-render approach.
Does NOT have a graded eval suite or deterministic test harness — that's our differentiator.

## "Claude Code for Game Development" survey — Chier Hu, Jun 2026
https://chierhu.medium.com/claude-code-for-game-development-7a88fcd19992

**Modality divide is the headline finding**: agents excel with text-serialized, headless
engines; fail with binary-asset GUI workflows.

- Best: Godot (human-readable `.tscn`/`.gd` → autonomous read-edit-run loop),
  web stack (Three.js/Phaser — instant visual feedback + huge training density),
  Python/Pygame
- Worst: Unreal (opaque `.uasset` defeats reasoning — "40+ messages trying to figure out
  which classes"), Unity (good C# but GUI-centric + binary scenes)

**Signature failure mode: "tests pass ≠ fun."** Documented case: agent compiled fine but
produced unplayable mechanics — zero damage in 60s, level-ups every 3.9s instead of the
intended 10–30s. Correctness verification does not catch game-feel/balance defects.
=> Implication for us: the harness needs **gameplay/balance metric assertions**, not just
   pass/fail unit tests. Assert on TTK, DPS, pacing curves, progression rates.

**One-shot variance**: Minesweeper, 10 runs of the same spec, $0.18–$0.28 each, produced
10 different implementations. Specs alone are insufficient → the repo's structure and
tests must constrain the solution space, not the prompt.

Other notes: context collapse ~40min into a session; MCP servers named for closing the
run-verify loop (Godot MCP, `bevy_debugger_mcp`); economics — sustained autonomous dev
$100–200/mo.
