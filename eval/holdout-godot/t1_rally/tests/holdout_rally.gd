## HELD-OUT. The agent never sees this file.
class_name HoldoutRallyTests
extends RefCounted

# The template runs GDScript warnings as errors. A held-out test must reach for
# members the implementation may not have yet — inherently unsafe access, which
# is the entire point of it.
@warning_ignore_start("unsafe_method_access", "unsafe_property_access", "unsafe_cast", "unsafe_call_argument", "untyped_declaration", "inferred_declaration")

# Drive the right paddle up so it misses and a point is conceded. Idle input
# rallies forever: it exercises the increment path but never the reset path.
static func _miss() -> Sim.Intents:
	return Sim.Intents.new(Sim.PlayerIntent.new(false, false), Sim.PlayerIntent.new(true, false))


# `Object.get` on a property that does not exist returns null. Left unchecked,
# null compares equal to null and the "two runs agree" test below would pass
# vacuously on a template with no counter at all — so the type is asserted
# explicitly, the way the TypeScript holdout asserts `typeof === 'number'`.
static func _has_counter(t: TestRunner, world: Sim.World) -> bool:
	if typeof(world.get("rally_length")) == TYPE_INT:
		return true
	t.check(false, "World has no integer `rally_length` property")
	return false


static func _tracks_hits_and_resets(t: TestRunner) -> void:
	var world := Sim.spawn_world(42)
	if not _has_counter(t, world):
		return
	t.eq(world.get("rally_length"), 0, "rally_length must start at 0")
	var expected: int = 0
	var max_seen: int = 0
	var resets: int = 0
	for tick: int in range(1, 3001):
		Sim.step(world, _miss())
		if world.events.scored != Sim.NO_SIDE:
			expected = 0
			resets += 1
		else:
			expected += world.events.paddle_hits.size()
		max_seen = maxi(max_seen, expected)
		# Report the FIRST disagreement and stop, as an `assert_eq!` in the Rust
		# holdout would. Accumulating 3000 copies of the same line buries the
		# summary and tells a reader nothing the first one did not.
		if world.get("rally_length") != expected:
			t.eq(world.get("rally_length"), expected, "tick %d disagreed" % tick)
			return
	t.gt(float(max_seen), 0.0, "no paddle hit occurred; a constant zero would pass")
	t.gt(float(resets), 0.0, "no score occurred; the reset path was never exercised")


static func _is_snapshotted(t: TestRunner) -> void:
	var a := Sim.spawn_world(7)
	var b := Sim.spawn_world(7)
	if not _has_counter(t, a):
		return
	for tick: int in range(1, 501):
		Sim.step(a, _miss())
		Sim.step(b, _miss())
		if a.get("rally_length") != b.get("rally_length"):
			t.eq(a.get("rally_length"), b.get("rally_length"), "tick %d: seed 7 disagreed" % tick)
			return


static func run_all(t: TestRunner) -> void:
	t.run("rally length tracks paddle hits and resets on a score", _tracks_hits_and_resets)
	t.run("rally length is part of the simulation snapshot", _is_snapshotted)
