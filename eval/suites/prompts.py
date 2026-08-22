"""Semantically identical task prompts, expressed in each stack's own vocabulary.

The first bake-off used BYTE-identical prompts, which sounded like the fair
choice and was the opposite: the shared text said "a public Bevy resource
`RallyLength(pub u32)` defined in `crates/sim`", so Rust received a prompt in
its own language while every other stack had to translate Bevy nouns, Rust paths
and a Rust integer type into C#, TypeScript and GDScript.

It also caused a real failure: `u32` has no C# equivalent, one Unity agent chose
`int`, and the held-out test asserted `0u` — NUnit reported the type mismatch as
the baffling "Expected: 0, But was: 0". That measured my ambiguity, not Unity.

So: same behaviour, same acceptance criteria, same constraints — each written
natively. No prompt names a type width; held-out tests must not depend on one.
"""

SYMBOL = {                      # (rally counter, powerup marker, sim location)
    "rust":  ("RallyLength",  "Powerup",  "the `sim` crate"),
    "ts":    ("rallyLength",  "'powerup'", "the sim module"),
    "unity": ("RallyLength",  "Powerup",  "the Sim assembly"),
    "godot": ("rally_length", "a powerup kind", "the sim module"),
}

DECL = {
    "rust":  "a public `RallyLength` resource, exported from the crate root so `sim::RallyLength` resolves",
    "ts":    "a public `rallyLength` field on the simulation world, exported from the sim module root",
    "unity": "a public `RallyLength` field on `SimState`",
    "godot": "a public `rally_length` field on `World`",
}

POWERUP_DECL = {
    "rust":  "a public `Powerup` marker component, exported from the crate root, on an entity that also has a `Position`",
    "ts":    "a new entity kind `'powerup'`, on an entity that also has a position",
    "unity": "a new `EntityKind.Powerup` value, on a `SimEntity` that also has a position",
    "godot": "a new powerup value on the entity `Kind` enum, on an entity that also has a position",
}

NET_LOC = {
    "rust":  "the view layer", "ts": "the view layer",
    "unity": "the view layer", "godot": "the view layer",
}


def rally(stack: str) -> str:
    return f"""Add a rally counter to the game simulation.

Requirements:
- {DECL[stack]}.
- It is a non-negative integer count. Use whichever integer type is natural in
  this codebase.
- It counts consecutive paddle hits since the last point was scored.
- It increases by one for every paddle hit. A single tick can contain more than
  one hit.
- It resets to zero on the tick a point is scored.
- It starts at zero and is initialised wherever the simulation sets up its
  other state.
- It must be part of deterministic simulation state: two runs with the same
  seed must agree on its value at every tick.

Add tests covering the behaviour, then make sure `just verify` passes.
"""


def net(stack: str) -> str:
    return f"""Draw a centre net in the game's rendered output: a vertical line down the
middle of the arena, like the dividing line in Pong.

Requirements:
- It must be visible in the rendered frame, spanning most of the arena height.
- It must not obscure gameplay - the paddles and ball must remain clearly
  visible, and the net must stay narrow.
- It is presentation only. It must not affect the simulation or collisions.

Add a test that proves the net actually renders, then make sure `just verify`
passes.
"""


def powerup(stack: str) -> str:
    return f"""Add a collectable powerup to the game simulation.

Requirements:
- {POWERUP_DECL[stack]}.
- Exactly one powerup exists at a time. Every 200 ticks it moves to a new
  randomly chosen position inside the arena.
- It must always be inside the arena bounds.
- Its position must be reproducible: two runs of the simulation with the same
  seed must place it identically at every tick, and different seeds must produce
  different placements.
- It does not need to interact with the ball or the paddles yet.
- If the view layer draws simulation entities, make sure the powerup renders
  sensibly rather than as a stray copy of another entity.

Add tests covering the behaviour, then make sure `just verify` passes.
"""

TASKS = {"t1_rally": rally, "t2_net": net, "t3_powerup": powerup}
