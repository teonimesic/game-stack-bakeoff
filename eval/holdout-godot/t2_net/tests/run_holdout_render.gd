## HELD-OUT rendering entry point. Run with:
##
##     godot --path . --resolution 640x400 -s res://tests/run_holdout_render.gd
##
## NOTE THE MISSING `--headless`, exactly as in `tests/run_render_tests.gd`. The
## headless display driver installs a dummy rendering driver: nothing is ever
## drawn and the viewport capture comes back null. Worse, anything that awaits
## `RenderingServer.frame_post_draw` deadlocks with no error and no timeout.
extends SceneTree

## Generous: three captures at three frames each, plus warm-up.
const FRAME_BUDGET: int = 2000

var _frames: int = 0


func _initialize() -> void:
	# Connected FIRST, on purpose: a runtime error inside `_initialize` aborts the
	# function but does NOT stop the engine, and the process would otherwise hang
	# with no output and no exit code.
	process_frame.connect(_aborted)
	_main()


func _main() -> void:
	var t := TestRunner.new()
	t.strict = "--strict" in OS.get_cmdline_user_args()
	var tests := HoldoutNetTests.new(self)
	await tests.run_all(t)
	_finish(t.summary())


func _finish(code: int) -> void:
	process_frame.disconnect(_aborted)
	quit(code)


func _aborted() -> void:
	# `_main` is a coroutine, so it yields back to the engine on its first await
	# and this fires on a healthy run too. Only a genuine abort leaves it
	# connected past the budget below.
	_frames += 1
	if _frames < FRAME_BUDGET:
		return
	printerr(
		(
			"HOLDOUT RUNNER ABORTED or hung: %d frames elapsed without the suite " % FRAME_BUDGET
			+ "finishing. Scroll up for a SCRIPT ERROR. If there is none, a capture is "
			+ "blocking — check that nothing awaits RenderingServer.frame_post_draw."
		)
	)
	quit(70)
