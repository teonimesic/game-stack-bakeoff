## `just probe-file SEED TICKS SCRIPT OUT` — a whole run, written to a file.
##
## Run with:
##
##     godot --headless --path . -s res://tools/probe_file.gd -- SEED TICKS SCRIPT OUT
##
## The batch form of `tools/probe.gd`: same seed, same input, same trace lines,
## but the inputs come from a recorded script instead of a live driver and the
## trace goes to a file instead of stdout. One JSON Lines record per tick,
## starting at tick 1. `SCRIPT` may be `-`, meaning "nothing pressed, ever".
##
## Exits non-zero if it could not run the ticks that were asked for, so a caller
## can trust a zero exit to mean "OUT holds exactly TICKS lines".
extends SceneTree


func _initialize() -> void:
	# See tests/run_sim_tests.gd for why a watchdog is connected before anything
	# else. It is disconnected in `_finish`.
	process_frame.connect(_aborted)
	_main()


func _main() -> void:
	var args: PackedStringArray = OS.get_cmdline_user_args()
	if args.size() < 4:
		printerr("usage: probe-file SEED TICKS SCRIPT OUT   (SCRIPT may be `-`)")
		_finish(2)
		return
	if not args[0].is_valid_int() or not args[1].is_valid_int():
		printerr("SEED and TICKS must both be integers, got %s and %s" % [args[0], args[1]])
		_finish(2)
		return

	var seed: int = args[0].to_int()
	var ticks: int = args[1].to_int()
	if ticks < 0:
		printerr("TICKS must not be negative, got %d" % ticks)
		_finish(2)
		return

	var problem: Array[String] = []
	var inputs: Array[Sim.Intents] = Trace.load_input_script(args[2], problem)
	if not problem.is_empty():
		printerr(problem[0])
		_finish(2)
		return

	var out: FileAccess = FileAccess.open(args[3], FileAccess.WRITE)
	if out == null:
		printerr("could not open %s for writing: error %d" % [args[3], FileAccess.get_open_error()])
		_finish(2)
		return

	var world: Sim.World = Sim.spawn_world(seed)
	var lines := PackedStringArray()
	for index: int in range(ticks):
		Sim.step(world, Trace.at(inputs, index))
		if not Trace.is_representable(world):
			printerr(
				(
					(
						"tick %d: simulation state is NaN or infinite, which JSON cannot hold. "
						% world.tick
					)
					+ "Ran %d of the %d ticks asked for." % [index, ticks]
				)
			)
			out.close()
			_finish(1)
			return
		lines.append(Trace.line(world))

	# One write, so a reader never sees a half-finished trace.
	out.store_string("\n".join(lines) + ("\n" if ticks > 0 else ""))
	out.close()
	printerr("probe: %d tick(s) from seed %d -> %s" % [ticks, seed, args[3]])
	_finish(0)


func _finish(code: int) -> void:
	process_frame.disconnect(_aborted)
	quit(code)


func _aborted() -> void:
	printerr("PROBE ABORTED before finishing — scroll up for the SCRIPT ERROR")
	quit(70)
