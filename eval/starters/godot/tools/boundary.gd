## The hexagonal boundary, mechanically enforced.
##
## Rust gets this from the crate graph: `sim` cannot call into `bevy_render`
## because it does not depend on it, and the compiler says so. GDScript has no
## module system and no visibility rules — every global class and every engine
## singleton is reachable from every script — so the strongest mechanism this
## stack offers is a source scan that FAILS THE BUILD. That is what this is.
##
## It runs three ways, and all three use the same rules:
##   * `just check`     — fast, standalone
##   * `just test-sim`  — as `tests/boundary_test.gd`, so the fast loop covers it
##   * `just verify`    — via both of the above
##
## `tests/boundary_test.gd` also feeds this scanner deliberate violations and
## asserts they are caught. A guard nobody has seen fire is not a guard.
class_name Boundary
extends RefCounted

## Directories whose contents must stay pure. Everything else may do as it likes.
const GUARDED_DIRS: Array[String] = ["res://sim"]


## One banned construct.
class Rule:
	extends RefCounted
	var pattern: String
	var category: String
	var reason: String
	## Compiled ONCE. Building a RegEx per line per rule turned a 0.2s scan into a
	## multi-minute one — the guard has to stay inside the fast loop to be run.
	var regex: RegEx

	func _init(p_pattern: String, p_category: String, p_reason: String) -> void:
		pattern = p_pattern
		category = p_category
		reason = p_reason
		regex = RegEx.create_from_string(p_pattern)


## One violation found in a source file.
class Violation:
	extends RefCounted
	var path: String
	var line: int
	var text: String
	var rule: Rule

	func _init(p_path: String, p_line: int, p_text: String, p_rule: Rule) -> void:
		path = p_path
		line = p_line
		text = p_text
		rule = p_rule

	func describe() -> String:
		return (
			"%s:%d  [%s] `%s`\n            %s\n            > %s"
			% [path, line, rule.category, rule.pattern, rule.reason, text.strip_edges()]
		)


const SCENE_TREE_REASON: String = (
	"sim/ must run under `--headless -s` with no scene and no GPU. Anything that "
	+ "reaches the scene tree or the renderer belongs in view/."
)
const INPUT_REASON: String = (
	"Device state is frame-scoped; a frame contains 0, 1, or many ticks, so reading "
	+ "it inside a tick drops and duplicates input. Read Sim.Intents instead; "
	+ "view/main.gd is the only place allowed to touch a device."
)
const RANDOM_REASON: String = (
	"Unseeded entropy makes replay, rollback, and desync detection impossible. Use "
	+ "world.rng (Sim.SimRng), which is part of snapshotted state."
)
const CLOCK_REASON: String = (
	"Wall clock and frame counters are not part of the snapshot, so a replay cannot "
	+ "reproduce them. Use world.tick."
)
const ASYNC_REASON: String = (
	"Signals and coroutines resolve on the frame, not on the tick, and their "
	+ "ordering is not part of the snapshot. Use per-tick state (Sim.TickEvents)."
)


## The rule table. Patterns are RegEx, matched against source with comments and
## string literals removed — so the prose in a doc comment may name a banned
## symbol, but the code may not use it.
static func rules() -> Array[Rule]:
	var all: Array[Rule] = []
	for word: String in [
		"Node",
		"Node2D",
		"Node3D",
		"CanvasItem",
		"CanvasLayer",
		"SceneTree",
		"Viewport",
		"SubViewport",
		"Window",
		"Control",
		"Camera2D",
		"Camera3D",
		"Sprite2D",
		"AnimationPlayer",
		"RenderingServer",
		"PhysicsServer2D",
		"DisplayServer",
		"AudioServer",
		"Image",
		"Texture2D",
		"Shader",
		"Material",
		"Tween",
		"Timer",
	]:
		all.append(Rule.new("\\b%s\\b" % word, "scene-tree", SCENE_TREE_REASON))
	for call: String in [
		"get_tree",
		"get_node",
		"get_viewport",
		"get_window",
		"add_child",
		"remove_child",
		"queue_free",
		"queue_redraw",
		"draw_rect",
		"draw_line",
		"instantiate",
	]:
		all.append(Rule.new("\\b%s\\s*\\(" % call, "scene-tree", SCENE_TREE_REASON))
	for callback: String in [
		"_ready",
		"_process",
		"_physics_process",
		"_draw",
		"_input",
		"_unhandled_input",
		"_enter_tree"
	]:
		all.append(Rule.new("func\\s+%s\\b" % callback, "scene-tree", SCENE_TREE_REASON))
	all.append(Rule.new("res://view", "layering", SCENE_TREE_REASON))
	all.append(Rule.new("\\bView\\b", "layering", SCENE_TREE_REASON))

	for word: String in ["Input", "InputEvent", "InputMap"]:
		all.append(Rule.new("\\b%s\\b" % word, "input", INPUT_REASON))

	for call: String in ["randf", "randi", "randfn", "rand_from_seed", "randomize", "randf_range"]:
		all.append(Rule.new("\\b%s\\s*\\(" % call, "nondeterminism", RANDOM_REASON))
	all.append(Rule.new("\\bRandomNumberGenerator\\b", "nondeterminism", RANDOM_REASON))
	# Godot's global `hash()` is documented as unspecified across versions.
	all.append(Rule.new("\\bhash\\s*\\(", "nondeterminism", RANDOM_REASON))

	for singleton: String in ["Time", "OS", "Engine", "Performance"]:
		all.append(Rule.new("\\b%s\\s*\\." % singleton, "nondeterminism", CLOCK_REASON))

	for word: String in ["await", "signal", "emit_signal", "Thread", "WorkerThreadPool", "Mutex"]:
		all.append(Rule.new("\\b%s\\b" % word, "async", ASYNC_REASON))
	return all


## Remove comments and string literals so the scan sees code, not prose.
##
## Doc comments in `sim/sim.gd` deliberately NAME the banned symbols in order to
## explain why they are banned; without this step the guard would flag its own
## documentation.
static func strip_noise(line: String) -> String:
	var out: String = ""
	var quote: String = ""
	var index: int = 0
	while index < line.length():
		var character: String = line[index]
		if quote.is_empty():
			if character == "#":
				break
			if character == '"' or character == "'":
				quote = character
			else:
				out += character
		else:
			if character == "\\":
				index += 1
			elif character == quote:
				quote = ""
		index += 1
	return out


## Scan one source string. [param path] is only used to label violations.
static func scan_source(path: String, source: String, rule_table: Array[Rule]) -> Array[Violation]:
	var found: Array[Violation] = []
	var lines: PackedStringArray = source.split("\n")
	for index: int in range(lines.size()):
		var code: String = strip_noise(lines[index])
		if code.strip_edges().is_empty():
			continue
		for rule: Rule in rule_table:
			if rule.regex != null and rule.regex.search(code) != null:
				found.append(Violation.new(path, index + 1, lines[index], rule))
	return found


## Every `.gd` file under [param dir], recursively.
static func gd_files(dir: String) -> PackedStringArray:
	var out := PackedStringArray()
	var handle: DirAccess = DirAccess.open(dir)
	if handle == null:
		return out
	handle.list_dir_begin()
	var entry: String = handle.get_next()
	while not entry.is_empty():
		var full: String = dir.path_join(entry)
		if handle.current_is_dir():
			if not entry.begins_with("."):
				out.append_array(gd_files(full))
		elif entry.ends_with(".gd"):
			out.append(full)
		entry = handle.get_next()
	handle.list_dir_end()
	return out


## Scan every guarded directory. An empty result means the boundary holds.
static func scan_project() -> Array[Violation]:
	var rule_table: Array[Rule] = rules()
	var found: Array[Violation] = []
	for dir: String in GUARDED_DIRS:
		for path: String in gd_files(dir):
			var file: FileAccess = FileAccess.open(path, FileAccess.READ)
			if file == null:
				continue
			found.append_array(scan_source(path, file.get_as_text(), rule_table))
	return found


## Human-readable report for a set of violations.
static func report(found: Array[Violation]) -> String:
	var lines := PackedStringArray()
	lines.append(
		(
			(
				"%d boundary violation(s). sim/ is the pure, headless, replayable core; "
				% found.size()
			)
			+ "these symbols cannot appear in it."
		)
	)
	for violation: Violation in found:
		lines.append("  " + violation.describe())
	return "\n".join(lines)
