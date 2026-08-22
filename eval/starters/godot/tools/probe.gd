## `just probe SEED` — a live simulation on stdin/stdout.
##
## Run with:
##
##     godot --headless --no-header --path . -s res://tools/probe.gd -- SEED
##
## Protocol, exactly:
##
##   1. Print one trace line for tick 0, before anything has been stepped.
##   2. Read one line from stdin. It is a JSON object of input fields; anything
##      it does not name is false. Step EXACTLY ONE tick. Print one trace line.
##   3. Repeat until stdin ends or a line reads `quit`. Exit 0.
##
## stdout carries trace lines and nothing else — that is the whole contract, and
## it is why every diagnostic in here goes through `printerr`. Three details of
## this stack make it work, and all three are load-bearing:
##
##   * `--no-header`, not `--quiet`. `--quiet` silences ALL of stdout including
##     `print`, so the trace disappears; `--no-header` drops only the engine
##     banner, which is otherwise the first two lines of stdout.
##   * `print()` flushes on every call, so a driver can read a line and write the
##     next input without deadlocking. Do not batch lines.
##   * `OS.read_string_from_stdin(n)` is line-oriented: it blocks until a whole
##     line is available and returns it WITHOUT the newline. It returns the empty
##     string both at end of input and for a blank line, which is why a blank line
##     ends the run here — send `{}` for "nothing pressed".
extends SceneTree

## Plenty for an input line; a longer one is truncated, not silently merged.
const STDIN_BUFFER: int = 65536


func _initialize() -> void:
	# See tests/run_sim_tests.gd for why a watchdog is connected before anything
	# else. It is disconnected in `_finish`.
	process_frame.connect(_aborted)
	_main()


func _main() -> void:
	var args: PackedStringArray = OS.get_cmdline_user_args()
	if args.size() < 1:
		printerr("usage: probe SEED   (one JSON input object per line on stdin)")
		_finish(2)
		return
	if not args[0].is_valid_int():
		printerr("SEED must be an integer, got %s" % args[0])
		_finish(2)
		return

	var world: Sim.World = Sim.spawn_world(args[0].to_int())
	if not _emit(world):
		return

	while true:
		var line: String = OS.read_string_from_stdin(STDIN_BUFFER).strip_edges()
		if line.is_empty() or line == "quit":
			break
		var parsed: Variant = JSON.parse_string(line)
		if parsed == null:
			printerr("tick %d: input line is not valid JSON: %s" % [world.tick + 1, line])
			_finish(1)
			return
		Sim.step(world, Trace.intents_from_json(parsed))
		if not _emit(world):
			return

	_finish(0)


## Print one trace line, or bail out. Returns false when the caller must stop.
func _emit(world: Sim.World) -> bool:
	if not Trace.is_representable(world):
		printerr(
			(
				(
					"tick %d: simulation state is NaN or infinite, which JSON cannot hold. "
					% world.tick
				)
				+ "Something is dividing by zero or accumulating without a bound."
			)
		)
		_finish(1)
		return false
	print(Trace.line(world))
	return true


func _finish(code: int) -> void:
	process_frame.disconnect(_aborted)
	quit(code)


func _aborted() -> void:
	printerr("PROBE ABORTED before finishing — scroll up for the SCRIPT ERROR")
	quit(70)
