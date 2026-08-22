## HELD-OUT. The agent never sees this file.
## A determinism trap: randf()/Time.* pass review and fail here.
class_name HoldoutPowerupTests
extends RefCounted

# The template runs GDScript warnings as errors. A held-out test must reach for
# members the implementation may not have yet — inherently unsafe access, which
# is the entire point of it.
@warning_ignore_start("unsafe_method_access", "unsafe_property_access", "unsafe_cast", "unsafe_call_argument", "untyped_declaration", "inferred_declaration")


# Kind.PADDLE=0, Kind.BALL=1. Anything beyond is the new powerup kind. Compared
# numerically so this file compiles before the enum value exists.
#
# A tick with no powerup is recorded as "" so the shape of the series (when the
# powerup exists, when it moves) is compared, not just the positions.
static func _positions(seed_value: int, ticks: int) -> Array[String]:
	var world := Sim.spawn_world(seed_value)
	var out: Array[String] = []
	for _i: int in range(ticks):
		Sim.step(world)
		var found: Array[String] = []
		for e: Sim.Entity in world.by_sim_id():
			if int(e.kind) > 1:
				found.append("%d,%d" % [Sim.f32_bits(e.position.x), Sim.f32_bits(e.position.y)])
		found.sort()
		out.append(found[0] if found.size() > 0 else "")
	return out


## Index of the first differing tick, or -1 when the two series are identical.
static func _first_difference(a: Array[String], b: Array[String]) -> int:
	var shared: int = mini(a.size(), b.size())
	for i: int in range(shared):
		if a[i] != b[i]:
			return i
	if a.size() != b.size():
		return shared
	return -1


static func _exists_and_moves(t: TestRunner) -> void:
	var seen := _positions(3, 900)
	var present: int = 0
	var distinct := {}
	for p: String in seen:
		if p != "":
			present += 1
			distinct[p] = true
	t.gt(
		float(present),
		0.0,
		"no entity with a powerup kind (a Kind value beyond BALL) ever existed in 900 ticks"
	)
	t.gt(
		float(distinct.size()),
		1.0,
		(
			"the powerup never changed position in 900 ticks — it is supposed to move to a "
			+ "new random position every 200 ticks"
		)
	)


static func _is_deterministic_for_a_seed(t: TestRunner) -> void:
	# The trap. randf(), RandomNumberGenerator.new(), or Time.get_ticks_msec()
	# all fail here while looking perfectly reasonable in review.
	var a := _positions(11, 900)
	var b := _positions(11, 900)
	var diff := _first_difference(a, b)
	t.eq(
		diff,
		-1,
		(
			"two runs with seed 11 disagreed about the powerup position at this tick index — "
			+ "the placement is reading entropy from outside the simulation snapshot"
		)
	)


static func _depends_on_the_seed(t: TestRunner) -> void:
	# Guards the opposite failure: a hardcoded position is trivially
	# deterministic and would sail through the test above.
	var a := _positions(1, 900)
	var b := _positions(2, 900)
	t.gt(
		float(_first_difference(a, b)),
		-1.0,
		(
			"seeds 1 and 2 produced identical powerup placements — the position is not "
			+ "actually random, or it ignores the simulation RNG"
		)
	)


static func _stays_inside_the_arena(t: TestRunner) -> void:
	for s: int in [5, 6, 7]:
		for p: String in _positions(s, 600):
			if p == "":
				continue
			var parts := p.split(",")
			var x := Sim.f32_from_bits(int(parts[0]))
			var y := Sim.f32_from_bits(int(parts[1]))
			# Report the FIRST escape and stop, as the Rust holdout's `assert!`
			# would; 1800 copies of the same line bury the summary.
			if absf(x) > Sim.ARENA_HALF_WIDTH or absf(y) > Sim.ARENA_HALF_HEIGHT:
				t.check(
					false, "seed %d: powerup outside the arena at (%f, %f)" % [s, x, y]
				)
				return


static func run_all(t: TestRunner) -> void:
	t.run("powerup exists and moves over time", _exists_and_moves)
	t.run("powerup placement is deterministic for a seed", _is_deterministic_for_a_seed)
	t.run("powerup placement depends on the seed", _depends_on_the_seed)
	t.run("powerup stays inside the arena", _stays_inside_the_arena)
