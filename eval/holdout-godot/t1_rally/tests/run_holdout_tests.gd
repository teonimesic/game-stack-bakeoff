extends SceneTree
var _frames: int = 0

func _initialize() -> void:
	process_frame.connect(_aborted)
	var t := TestRunner.new()
	HoldoutRallyTests.run_all(t)
	process_frame.disconnect(_aborted)
	quit(t.summary())

func _aborted() -> void:
	_frames += 1
	if _frames > 2:
		push_error("RUNNER ABORTED")
		quit(70)
