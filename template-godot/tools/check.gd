## `just check` — the fastest signal in the repo (~1s, no display, no tests).
##
## Two things, both of which the test runners would otherwise only find
## indirectly:
##
##   1. COMPILE EVERY SCRIPT. `godot --check-only` checks one file and always
##      exits 0, so it cannot gate anything. Loading a [GDScript] and calling
##      `reload()` returns a real [enum Error] instead, and with the warnings in
##      project.godot set to level 2 an untyped declaration IS a compile error.
##      A script nothing imports yet is still checked here.
##   2. RUN THE BOUNDARY GUARD over `sim/`.
##
## Run with: godot --headless --path . -s res://tools/check.gd
extends SceneTree

const SCANNED_DIRS: Array[String] = ["res://sim", "res://view", "res://tests", "res://tools"]
const SELF: String = "res://tools/check.gd"


func _initialize() -> void:
	process_frame.connect(_aborted)
	var failures: int = 0
	var checked: int = 0

	# The boundary scan runs FIRST. The compile loop below calls `reload()` on
	# every script including `tools/boundary.gd`, and re-parsing a script gives
	# its inner classes a fresh identity — after which `Array[Boundary.Violation]`
	# no longer matches `Array[Boundary.Violation]`. Scanning first side-steps it.
	var violations: Array[Boundary.Violation] = Boundary.scan_project()
	var paths := PackedStringArray()
	for dir: String in SCANNED_DIRS:
		paths.append_array(Boundary.gd_files(dir))

	if not violations.is_empty():
		printerr(Boundary.report(violations))
		failures += violations.size()

	for path: String in paths:
		# Godot refuses to reload a script that is currently executing, and this is
		# it. A parse error here shows up as the abort guard firing instead.
		if path == SELF:
			continue
		checked += 1
		var script := ResourceLoader.load(path, "GDScript") as GDScript
		if script == null:
			printerr("COMPILE %s — could not be loaded at all" % path)
			failures += 1
			continue
		# `reload()` re-parses and returns OK / ERR_PARSE_ERROR. The parser prints
		# the specific line and reason above this message.
		if script.reload() != OK:
			printerr("COMPILE %s — see the SCRIPT ERROR lines above" % path)
			failures += 1

	print("CHECK scripts=%d failures=%d" % [checked, failures])
	if failures > 0:
		printerr("check failed: %d problem(s)" % failures)
	_finish(1 if failures > 0 else 0)


func _finish(code: int) -> void:
	process_frame.disconnect(_aborted)
	quit(code)


func _aborted() -> void:
	printerr("CHECK ABORTED before finishing — scroll up for the SCRIPT ERROR")
	quit(70)
