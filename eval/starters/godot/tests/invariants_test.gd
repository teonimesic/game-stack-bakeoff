## Invariant assertions: the tests that catch "correct but not a game".
##
## The documented signature failure of agent-built games is that everything
## compiles, every unit test passes, and the result is unplayable — zero damage
## in sixty seconds, or level-ups every 3.9s instead of the intended 10-30s.
## Correctness tests cannot see that class of defect, because nothing is
## *wrong*; the numbers are just bad.
##
## So these assert on CONSEQUENCES measured over a run — where things ended up,
## how often something happened, whether a held input changed the outcome — and
## never on the tuning constants themselves. That is what makes them survive a
## rewrite of the rules and still catch a bad one.
##
## Keep the bounds wide. They exist to catch "this is not a game any more", not
## to freeze the design.
class_name InvariantsTests
extends RefCounted

## Long enough that anything cumulative (drift, leaks, escapes) has shown itself.
const LONG_RUN: int = 3000
## Long enough for held intent to visibly change where things end up.
const NUDGE_RUN: int = 120
## Long enough to see whether speed wanders once intent is involved.
const SPEED_RUN: int = 600


## Where a marker is after [param ticks] ticks, given a per-tick intent.
static func marker_after(seed: int, ticks: int, intents: Sim.Intents) -> Sim.Entity:
	var world: Sim.World = Replay.headless_world(seed)
	for i: int in range(ticks):
		Sim.step(world, intents)
	return world.first_of_kind(Sim.Kind.MARKER)


static func run_all(t: TestRunner) -> void:
	t.run("nothing escapes the arena over a long run", _stays_in_bounds)
	t.run("a long idle run actually produces events", _events_fire)
	t.run("held intent changes where the marker ends up", _intent_moves_it)
	t.run("speed stays put while intent is applied", _speed_is_stable)


static func _stays_in_bounds(t: TestRunner) -> void:
	# An entity that leaks out of the world passes every determinism test — the
	# escape is perfectly reproducible — while making the game unplayable.
	var world: Sim.World = Replay.headless_world(1)
	var limit_x: float = Sim.ARENA_HALF_WIDTH - Sim.MARKER_HALF_SIZE
	var limit_y: float = Sim.ARENA_HALF_HEIGHT - Sim.MARKER_HALF_SIZE
	var worst := Vector2.ZERO
	var worst_tick: int = 0

	for i: int in range(LONG_RUN):
		Sim.step(world)
		for entity: Sim.Entity in world.by_sim_id():
			if absf(entity.position.x) > absf(worst.x) or absf(entity.position.y) > absf(worst.y):
				worst = entity.position
				worst_tick = world.tick

	t.check(
		absf(worst.x) <= limit_x + 0.001 and absf(worst.y) <= limit_y + 0.001,
		(
			(
				"an entity reached (%.2f, %.2f) on tick %d, outside the arena bounds "
				+ "(±%.1f, ±%.1f). Collision is letting it through."
			)
			% [worst.x, worst.y, worst_tick, limit_x, limit_y]
		)
	)


static func _events_fire(t: TestRunner) -> void:
	# A world where nothing ever happens is the other way to be "correct" and
	# dead. Assert on the consequence — an event was produced — not on the rule
	# that produces it.
	var outcome: Replay.Outcome = Replay.run(Replay.idle(2, LONG_RUN))
	var bounces: int = 0
	for name: String in outcome.events:
		if name == "bounce":
			bounces += 1
	t.gt(
		float(bounces),
		0.0,
		(
			(
				"%d ticks of idle simulation produced no `bounce` event at all. Either "
				+ "nothing is moving or nothing can interact with the arena."
			)
			% LONG_RUN
		)
	)


static func _intent_moves_it(t: TestRunner) -> void:
	# Relational, not absolute: whatever the rules are, holding "up" must end up
	# further up than not holding it. This is the cheapest possible proof that
	# input reaches the simulation and means something.
	var idle: Sim.Entity = marker_after(3, NUDGE_RUN, Sim.no_intents())
	var raised: Sim.Entity = marker_after(3, NUDGE_RUN, Sim.Intents.new(true, false))
	t.check(idle != null and raised != null, "no marker in the world after the run")
	if idle == null or raised == null:
		return

	t.gt(
		raised.position.y,
		idle.position.y,
		(
			(
				"holding nudge_up for %d ticks left the marker at y=%.2f, no higher than the "
				+ "y=%.2f it reaches with no input at all — intent is not reaching motion."
			)
			% [NUDGE_RUN, raised.position.y, idle.position.y]
		)
	)


static func _speed_is_stable(t: TestRunner) -> void:
	# Intent steers; it must not secretly be an accelerator. A rule that adds
	# velocity every tick reads fine and turns the game into a blur after a
	# minute — which no correctness test can see.
	var world: Sim.World = Replay.headless_world(4)
	var worst: float = Sim.MARKER_SPEED
	var worst_tick: int = 0

	for i: int in range(SPEED_RUN):
		# Input on half the ticks: enough to exercise the intent path, not so
		# much that it becomes one long held key.
		var pressed: bool = (i / 8) % 2 == 0
		Sim.step(world, Sim.Intents.new(pressed, false))
		for entity: Sim.Entity in world.by_sim_id():
			var speed: float = entity.velocity.length()
			if absf(speed - Sim.MARKER_SPEED) > absf(worst - Sim.MARKER_SPEED):
				worst = speed
				worst_tick = world.tick

	var drift: float = absf(worst - Sim.MARKER_SPEED) / Sim.MARKER_SPEED
	t.lt(
		drift,
		0.01,
		(
			(
				"speed reached %.3f on tick %d, %.2f%% away from the %.1f it is supposed to "
				+ "hold. Intent is changing how fast things move, not just where they go."
			)
			% [worst, worst_tick, drift * 100.0, Sim.MARKER_SPEED]
		)
	)
