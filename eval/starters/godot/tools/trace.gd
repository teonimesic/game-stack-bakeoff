## The probe wire format, in one place.
##
## `tools/probe.gd`, `tools/probe_file.gd` and `tools/film.gd` all speak it, and
## anything outside this repo that reads a trace depends on it, so it is a
## compatibility surface: adding a field is cheap, renaming or reordering one is
## not.
##
## One trace line, exactly:
##
##     {"tick": 1, "hash": "0x...", "state": { ... }, "events": ["bounce"]}
##
## Key order is fixed and the lines are built by hand rather than handed to
## [method JSON.stringify] on a [Dictionary], because dictionary iteration order
## is an implementation detail and a trace that reorders its keys is no longer
## byte-comparable between two runs.
class_name Trace
extends RefCounted

## Decimal places used for every number in `state`. Enough to round-trip the f32
## the simulation actually stores, at the coordinate magnitudes this arena uses.
const DECIMALS: int = 9


## Lowercase, zero-padded, unsigned 64-bit hex — `0x` + 16 digits.
##
## [method Sim.state_hash] returns a signed GDScript int holding a u64 bit
## pattern, so this reads it a nibble at a time instead of formatting it as a
## number; `%x` on a negative int is not the u64 rendering anyone wants.
static func hex_u64(value: int) -> String:
	var digits: String = "0123456789abcdef"
	var out: String = ""
	for index: int in range(16):
		out += digits[(value >> ((15 - index) * 4)) & 0xF]
	return "0x" + out


## One finite JSON number. Returns an empty string for NaN/Infinity, which is not
## representable in JSON and must be reported rather than smuggled out as a bare
## token no parser accepts.
static func number(value: float) -> String:
	if not is_finite(value):
		return ""
	return String.num(value, DECIMALS)


## The game-defined part of a trace line.
##
## THIS IS THE PART YOU CHANGE when the game changes. Expose the values that
## describe what the world is doing right now — positions, velocities, counters,
## whatever a reader would need to tell one tick from another — in a stable,
## machine-readable shape. Everything else in this file is format plumbing.
static func state_json(world: Sim.World) -> String:
	var marker: Sim.Entity = world.first_of_kind(Sim.Kind.MARKER)
	if marker == null:
		return "{}"
	return (
		'{"marker": {"x": %s, "y": %s, "vx": %s, "vy": %s}}'
		% [
			number(marker.position.x),
			number(marker.position.y),
			number(marker.velocity.x),
			number(marker.velocity.y),
		]
	)


static func events_json(world: Sim.World) -> String:
	var quoted := PackedStringArray()
	for name: String in world.events.events:
		quoted.append(JSON.stringify(name))
	return "[" + ", ".join(quoted) + "]"


## One trace line for the world as it stands. Call it after [method Sim.step];
## call it before any step at all for the tick-0 header line.
static func line(world: Sim.World) -> String:
	return (
		'{"tick": %d, "hash": "%s", "state": %s, "events": %s}'
		% [world.tick, hex_u64(Sim.state_hash(world)), state_json(world), events_json(world)]
	)


## True when every number the state line will contain is finite.
static func is_representable(world: Sim.World) -> bool:
	for entity: Sim.Entity in world.by_sim_id():
		for value: float in [
			entity.position.x, entity.position.y, entity.velocity.x, entity.velocity.y
		]:
			if not is_finite(value):
				return false
	return true


# --------------------------------------------------------------------------
# Input scripts
# --------------------------------------------------------------------------


## One tick of input, from a JSON object. Absent fields are false, so a script
## only has to name the inputs it wants pressed.
static func intents_from_json(value: Variant) -> Sim.Intents:
	var fields: Dictionary = value if value is Dictionary else {}
	return Sim.Intents.new(_flag(fields, "nudge_up"), _flag(fields, "nudge_down"))


static func _flag(fields: Dictionary, key: String) -> bool:
	return true if fields.get(key, false) else false


## Parse a `{"version": 1, "inputs": [ {...}, ... ]}` script file.
##
## [param path] may be `-` or empty, meaning "no input on any tick". Returns an
## empty array and leaves [param problem] untouched on success; on failure the
## caller gets a message to print and should exit non-zero.
static func load_input_script(path: String, problem: Array[String]) -> Array[Sim.Intents]:
	var inputs: Array[Sim.Intents] = []
	if path.is_empty() or path == "-":
		return inputs

	if not FileAccess.file_exists(path):
		problem.append("input script not found: %s" % path)
		return inputs
	var handle: FileAccess = FileAccess.open(path, FileAccess.READ)
	if handle == null:
		problem.append("could not read input script: %s" % path)
		return inputs

	var parsed: Variant = JSON.parse_string(handle.get_as_text())
	if not (parsed is Dictionary):
		problem.append("input script is not a JSON object: %s" % path)
		return inputs
	var document: Dictionary = parsed
	var raw: Variant = document.get("inputs", [])
	if not (raw is Array):
		problem.append('input script has no "inputs" array: %s' % path)
		return inputs

	var recorded: Array = raw
	for element: Variant in recorded:
		inputs.append(intents_from_json(element))
	return inputs


## Input for tick [param index] (0-based). Past the end of a script, nothing is
## pressed.
static func at(inputs: Array[Sim.Intents], index: int) -> Sim.Intents:
	return inputs[index] if index >= 0 and index < inputs.size() else Sim.no_intents()
