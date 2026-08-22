## Determinism guarantees. These tests are the template's safety net: they fail
## loudly when a change makes the simulation depend on iteration order, wall
## clock, or unseeded entropy.
##
## If one of these fails, DO NOT relax the assertion. An exact hash comparison
## that becomes an approximate one is worthless. Find the nondeterminism.
class_name DeterminismTests
extends RefCounted


static func alternating_inputs(ticks: int) -> Array[Sim.Intents]:
	# A pattern that actually moves both paddles and produces rallies, so the
	# hash chain exercises collisions rather than an untouched ball.
	var inputs: Array[Sim.Intents] = []
	for tick: int in range(ticks):
		inputs.append(
			Sim.Intents.new(
				Sim.PlayerIntent.new((tick / 17) % 2 == 0, (tick / 17) % 2 == 1),
				Sim.PlayerIntent.new((tick / 23) % 2 == 1, (tick / 23) % 2 == 0)
			)
		)
	return inputs


static func run_all(t: TestRunner) -> void:
	t.run("identical replays produce identical hash chains", _identical_replays)
	t.run("different seeds produce different runs", _different_seeds)
	t.run("different inputs produce different runs", _different_inputs)
	t.run("tick count is exactly the number of steps", _tick_count)
	t.run("replay is resumable from a prefix", _prefix)
	t.run("the tick pipeline is a declared total order", _pipeline_order)
	t.run("simulation state stays in f32", _state_is_f32)
	t.run("a headless world starts spawned and at tick zero", _headless_world)


static func _identical_replays(t: TestRunner) -> void:
	var replay := Replay.new(0xDEADBEEF, alternating_inputs(600))
	t.eq(
		Replay.find_divergence(replay),
		-1,
		(
			"the same replay produced different state on two runs — the simulation is "
			+ "reading something outside its snapshot (iteration order, wall clock, or "
			+ "unseeded RNG)"
		)
	)


static func _different_seeds(t: TestRunner) -> void:
	# Guards against the opposite failure: a "deterministic" simulation that is
	# actually ignoring its seed would pass every determinism test trivially.
	var a: Replay.Outcome = Replay.run(Replay.idle(1, 400))
	var b: Replay.Outcome = Replay.run(Replay.idle(2, 400))
	t.ne(
		a.digest(),
		b.digest(),
		"two different seeds produced identical runs — the seed is not reaching the simulation"
	)


static func _different_inputs(t: TestRunner) -> void:
	var seed: int = 7
	var idle: Replay.Outcome = Replay.run(Replay.idle(seed, 400))
	var active: Replay.Outcome = Replay.run(Replay.new(seed, alternating_inputs(400)))
	t.ne(idle.digest(), active.digest(), "player intent had no effect on the simulation")


static func _tick_count(t: TestRunner) -> void:
	# Time in the simulation is a count of `Sim.step` calls and nothing else. If
	# this regresses — for instance because someone moved the tick into
	# `_physics_process` — every other determinism test silently becomes
	# time-dependent.
	for ticks: int in [1, 10, 137]:
		var outcome: Replay.Outcome = Replay.run(Replay.idle(3, ticks))
		t.eq(outcome.final_tick, ticks, "expected exactly %d ticks from %d steps" % [ticks, ticks])
		t.eq(outcome.hashes.size(), ticks, "expected %d hashes" % ticks)


static func _prefix(t: TestRunner) -> void:
	# A replay's first N hashes must not depend on what comes after them. This is
	# what makes rollback and mid-run desync detection possible.
	var inputs: Array[Sim.Intents] = alternating_inputs(500)
	var long_run: Replay.Outcome = Replay.run(Replay.new(11, inputs))
	var short_inputs: Array[Sim.Intents] = []
	short_inputs.assign(inputs.slice(0, 200))
	var short_run: Replay.Outcome = Replay.run(Replay.new(11, short_inputs))

	t.eq(
		long_run.hashes.slice(0, 200),
		short_run.hashes,
		"a 500-tick run and a 200-tick run diverged within their common prefix"
	)


static func _pipeline_order(t: TestRunner) -> void:
	# The analogue of Bevy's schedule-ambiguity check: every system names the
	# stage it belongs to, and the systems run in stage order. Two systems that
	# touch the same state with no declared order between them are exactly the
	# race this catches — inserting a system without a stage, or out of stage
	# order, fails here rather than showing up as an unreproducible desync months
	# later.
	var stages: Array[int] = []
	var names: Array[String] = []
	for system: Sim.SimSystem in Sim.SIM_PIPELINE:
		stages.append(int(system.stage))
		names.append(system.name)

	var sorted: Array[int] = stages.duplicate()
	sorted.sort()
	t.eq(
		stages,
		sorted,
		"SIM_PIPELINE is not sorted by stage; the declared order and the run order disagree"
	)
	t.eq(names.size(), _unique(names).size(), "two systems in SIM_PIPELINE share a name")
	t.gt(float(stages.size()), 0.0, "SIM_PIPELINE is empty; nothing would run")


static func _unique(values: Array[String]) -> Array[String]:
	var seen: Array[String] = []
	for value: String in values:
		if not seen.has(value):
			seen.append(value)
	return seen


static func _state_is_f32(t: TestRunner) -> void:
	# Rust gets this from the type system; here it is a property of [Vector2],
	# whose components are `real_t` — 32-bit in a standard Godot build.
	# `Sim.state_hash` reads f32 bit patterns, so any state that escaped into a
	# bare GDScript `float` (64-bit) would be hashed lossily and a real divergence
	# could hide inside the rounding. Every coordinate must survive a round trip
	# through f32 unchanged.
	var world: Sim.World = Replay.headless_world(19)
	var pattern: Array[Sim.Intents] = alternating_inputs(400)
	for tick: int in range(400):
		Sim.step(world, pattern[tick])
		for entity: Sim.Entity in world.entities:
			for value: float in [
				entity.position.x, entity.position.y, entity.velocity.x, entity.velocity.y
			]:
				var round_tripped: float = Sim.f32_from_bits(Sim.f32_bits(value))
				if round_tripped != value:
					t.check(
						false,
						(
							(
								"entity %d holds %s, which is not representable in f32 — some "
								+ "simulation state escaped Vector2 into a 64-bit float"
							)
							% [entity.id, value]
						)
					)
					return


static func _headless_world(t: TestRunner) -> void:
	# If this breaks, every replay length in the suite silently shifts by one.
	var world: Sim.World = Replay.headless_world(0)
	t.eq(world.tick, 0, "a fresh world must be at tick 0")
	# Counted by KIND, not by total. A test that asserts `entities.size() == 3`
	# fails the moment anyone adds a new kind of entity, which is a false alarm:
	# what matters is that startup produced the players and the ball.
	t.eq(world.of_kind(Sim.Kind.PADDLE).size(), 2, "expected two paddles after startup")
	t.eq(world.of_kind(Sim.Kind.BALL).size(), 1, "expected exactly one ball after startup")

	Sim.step(world)
	t.eq(world.tick, 1, "one step, one tick")
