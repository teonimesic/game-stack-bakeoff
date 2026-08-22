## The boundary guard, and a test that the guard actually fires.
##
## The first test is the one that matters day to day: `sim/` is clean. The rest
## are a POSITIVE CONTROL — they feed [Boundary] deliberate violations and assert
## each is caught. Without them, deleting a rule from the table would leave the
## suite green and the boundary unenforced.
class_name BoundaryTests
extends RefCounted


static func run_all(t: TestRunner) -> void:
	t.run("sim/ contains no scene-tree, input, or nondeterminism symbols", _sim_is_pure)
	t.run("the boundary guard fires on every banned category", _guard_fires)
	t.run("the boundary guard ignores comments and string literals", _guard_ignores_prose)
	t.run("the boundary guard actually reads the sim sources", _guard_reads_sources)
	t.run("the physics tick rate agrees with Sim.TICK_HZ", _tick_rate_agrees)


static func _sim_is_pure(t: TestRunner) -> void:
	var found: Array[Boundary.Violation] = Boundary.scan_project()
	t.check(found.is_empty(), "" if found.is_empty() else Boundary.report(found))


## Each snippet is real GDScript that a plausible change might introduce.
static func _guard_fires(t: TestRunner) -> void:
	var cases: Dictionary[String, String] = {
		"scene-tree": "var root: Node = get_tree().root",
		"input": "var up: bool = Input.is_key_pressed(KEY_W)",
		"nondeterminism": "var angle: float = randf() * TAU",
		"async": "await some_signal",
	}
	var rule_table: Array[Boundary.Rule] = Boundary.rules()
	for category: String in cases:
		var found: Array[Boundary.Violation] = Boundary.scan_source(
			"synthetic.gd", cases[category], rule_table
		)
		var categories: Array[String] = []
		for violation: Boundary.Violation in found:
			categories.append(violation.rule.category)
		t.check(
			categories.has(category),
			(
				(
					"the boundary guard did NOT flag `%s` as %s — a rule has been deleted or "
					+ "weakened, and sim/ is no longer protected against it. Restore the rule "
					+ "in tools/boundary.gd; do not delete this assertion."
				)
				% [cases[category], category]
			)
		)

	var spawn: String = "marker.position = Vector2(randf_range(-100.0, 100.0), 0.0)"
	t.check(
		not Boundary.scan_source("synthetic.gd", spawn, rule_table).is_empty(),
		"randf_range in sim/ was not caught; a randomised spawn would break every replay"
	)
	var clock: String = "var now: int = Time.get_ticks_msec()"
	t.check(
		not Boundary.scan_source("synthetic.gd", clock, rule_table).is_empty(),
		"a wall-clock read in sim/ was not caught"
	)


static func _guard_ignores_prose(t: TestRunner) -> void:
	# sim/sim.gd names the banned symbols in its own documentation on purpose.
	# If the guard flagged prose, the only way to keep it green would be to
	# delete the explanation of why the rule exists.
	var rule_table: Array[Boundary.Rule] = Boundary.rules()
	var doc_line: String = "## Never call Input.is_key_pressed here."
	t.eq(
		Boundary.scan_source("doc.gd", doc_line, rule_table).size(),
		0,
		"the guard flagged a doc comment; it must scan code, not prose"
	)
	t.eq(
		Boundary.scan_source("doc.gd", '\tvar label: String = "randf"', rule_table).size(),
		0,
		"the guard flagged a string literal"
	)
	t.eq(
		Boundary.scan_source("doc.gd", "var input_axis: float = 0.0", rule_table).size(),
		0,
		"the guard matched inside an identifier; rules must be word-bounded"
	)


static func _guard_reads_sources(t: TestRunner) -> void:
	# Guards against the silent-success failure: a scanner pointed at a directory
	# that does not exist reports zero violations and looks perfect.
	var files: PackedStringArray = Boundary.gd_files("res://sim")
	t.ge(float(files.size()), 2.0, "the boundary scan found no sim/ sources to read")


static func _tick_rate_agrees(t: TestRunner) -> void:
	# `view/main.gd` steps the simulation from `_physics_process`, so the engine's
	# fixed rate and the simulation's must be the same number. If they drift, the
	# played game runs at a different speed from every recorded replay — which no
	# other test in the suite can see, because no other test uses the engine loop.
	# `Engine.physics_ticks_per_second` is the typed, already-resolved view of
	# `physics/common/physics_ticks_per_second`; `ProjectSettings.get_setting`
	# returns a Variant that the strict-typing warnings reject.
	var configured: int = Engine.physics_ticks_per_second
	t.eq(
		configured,
		Sim.TICK_HZ,
		(
			(
				"physics/common/physics_ticks_per_second is %d but Sim.TICK_HZ is %d. "
				+ "Change both or neither."
			)
			% [configured, Sim.TICK_HZ]
		)
	)
