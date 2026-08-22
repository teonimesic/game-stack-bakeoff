## Rendering test entry point. Run with:
##
##     godot --path . --resolution 640x400 -s res://tests/run_render_tests.gd
##
## NOTE THE MISSING `--headless`. It is missing on purpose and adding it breaks
## every test in this file: the headless display driver installs a dummy
## rendering driver, so nothing is ever drawn and
## `get_viewport().get_texture().get_image()` returns null. This runner detects
## that and reports SKIP rather than hanging, but a skipped render suite proves
## nothing. Use `just test-render`.
##
## Pass `--bless` to regenerate golden images (`just bless`).
extends SceneTree


func _initialize() -> void:
	# See tests/run_sim_tests.gd for why this is connected before anything else.
	process_frame.connect(_aborted)
	_main()


func _main() -> void:
	var args: PackedStringArray = OS.get_cmdline_user_args()
	var t := TestRunner.new()
	# `just ci` passes `-- --strict`. It is the whole point of this flag that a CI
	# box with no display FAILS here instead of quietly skipping all five tests
	# and letting the pipeline report green over zero render coverage.
	t.strict = "--strict" in args
	var tests := RenderTests.new(self, "--bless" in args)
	tests.setup()
	await tests.run_all(t)
	_finish(t.summary())


func _finish(code: int) -> void:
	process_frame.disconnect(_aborted)
	quit(code)


func _aborted() -> void:
	# `_main` is a coroutine, so it yields back to the engine on its first await
	# and this fires immediately on a healthy run too. Only a genuine abort leaves
	# it connected past that point, which is why it is disconnected in `_finish`
	# rather than here — see the counter below.
	_frames += 1
	if _frames < FRAME_BUDGET:
		return
	printerr(
		(
			(
				"RUNNER ABORTED or hung: %d frames elapsed without the suite finishing. "
				% FRAME_BUDGET
			)
			+ "Scroll up for a SCRIPT ERROR. If there is none, a capture is blocking — "
			+ "check that nothing awaits RenderingServer.frame_post_draw, which never "
			+ "fires when there is no display."
		)
	)
	quit(70)


## Generous: the whole suite is ~20 captures at 3 frames each, plus warm-up.
const FRAME_BUDGET: int = 2000

var _frames: int = 0
