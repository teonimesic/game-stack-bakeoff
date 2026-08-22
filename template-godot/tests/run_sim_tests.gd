## Simulation test entry point. Run with:
##
##     godot --headless --path . -s res://tests/run_sim_tests.gd
##
## HEADLESS IS CORRECT HERE and nowhere else. `sim/` touches no scene tree and no
## renderer, so it runs with no display at all — which is what makes this the
## fast inner loop. `tests/run_render_tests.gd` must NOT be run this way: headless
## Godot cannot render, and the capture comes back null. See AGENTS.md.
extends SceneTree


func _initialize() -> void:
	# Connected FIRST, on purpose. A runtime error inside `_initialize` aborts the
	# function but does NOT stop the engine: SceneTree keeps iterating forever with
	# no scene, and the process hangs with no output and no exit code until
	# something kills it. That failure mode costs a whole turn. This turns it into
	# a fast, loud, non-zero exit instead.
	process_frame.connect(_aborted)

	var t := TestRunner.new()
	# `just ci` passes `-- --strict`, which turns a skip into a failure.
	t.strict = "--strict" in OS.get_cmdline_user_args()
	BoundaryTests.run_all(t)
	DeterminismTests.run_all(t)
	PlayabilityTests.run_all(t)
	_finish(t.summary())


func _finish(code: int) -> void:
	process_frame.disconnect(_aborted)
	quit(code)


func _aborted() -> void:
	printerr(
		(
			"RUNNER ABORTED before it finished — scroll up for the SCRIPT ERROR. Not every "
			+ "test ran, so there is no summary line. This is almost always a compile "
			+ "error in a file the runner depends on; `just check` prints those on their "
			+ "own."
		)
	)
	quit(70)
