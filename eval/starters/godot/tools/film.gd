## `just film SEED TICKS SCRIPT OUTDIR` — a run, as pictures.
##
## Run with:
##
##     godot --path . --resolution 640x400 -s res://tools/film.gd -- SEED TICKS SCRIPT OUTDIR
##
## Writes at most [constant MAX_FRAMES] PNGs — `frame_0000.png`, `frame_0001.png`,
## … — evenly spaced over `0..TICKS` inclusive, always including tick 0 and tick
## TICKS. `SCRIPT` may be `-`, meaning "nothing pressed, ever".
##
## NOTE THE MISSING `--headless`, and do not add it: it installs a dummy
## rendering driver, after which nothing is drawn and the capture comes back
## null. This recipe needs a display for the same structural reason
## `just test-render` does — see AGENTS.md. `tools/probe.gd` is the headless one.
##
## The capture itself is [method RenderTests.capture_frame], reused verbatim, so
## a film frame and a render-test frame are the same pixels by construction.
extends SceneTree

const MAX_FRAMES: int = 12


func _initialize() -> void:
	# See tests/run_render_tests.gd: `_main` is a coroutine, so this fires on a
	# healthy run too and the frame budget is what distinguishes a hang.
	process_frame.connect(_aborted)
	_main()


## The ticks to capture: evenly spaced over `0..ticks` inclusive, truncating, so
## the first is always 0 and the last is always [param ticks].
static func frame_ticks(ticks: int) -> PackedInt32Array:
	var count: int = mini(MAX_FRAMES, maxi(ticks, 0) + 1)
	var last: int = maxi(count - 1, 1)
	var out := PackedInt32Array()
	for index: int in range(count):
		out.append(index * ticks / last)
	return out


## Whatever is wrong with the command line, as a message, or "" if nothing is.
static func complaint(args: PackedStringArray) -> String:
	if args.size() < 4:
		return "usage: film SEED TICKS SCRIPT OUTDIR   (SCRIPT may be `-`)"
	if not args[0].is_valid_int() or not args[1].is_valid_int():
		return "SEED and TICKS must both be integers, got %s and %s" % [args[0], args[1]]
	if args[1].to_int() < 0:
		return "TICKS must not be negative, got %s" % args[1]
	return ""


func _main() -> void:
	var args: PackedStringArray = OS.get_cmdline_user_args()
	var wrong: String = complaint(args)
	if not wrong.is_empty():
		printerr(wrong)
		_finish(2)
		return

	var seed: int = args[0].to_int()
	var ticks: int = args[1].to_int()
	var problem: Array[String] = []
	var script: Array[Sim.Intents] = Trace.load_input_script(args[2], problem)
	if not problem.is_empty():
		printerr(problem[0])
		_finish(2)
		return

	var outdir: String = args[3]
	var made: Error = DirAccess.make_dir_recursive_absolute(outdir)
	if made != OK and made != ERR_ALREADY_EXISTS:
		printerr("could not create %s: error %d" % [outdir, made])
		_finish(2)
		return

	var camera := RenderTests.new(self, false)
	camera.setup()

	var wanted: PackedInt32Array = frame_ticks(ticks)
	for index: int in range(wanted.size()):
		var upto: int = wanted[index]
		var inputs: Array[Sim.Intents] = []
		for tick: int in range(upto):
			inputs.append(Trace.at(script, tick))

		var frame: Frame = await camera.capture_frame(seed, upto, inputs)
		if frame == null:
			printerr(
				(
					"this environment cannot capture pixels — the root viewport has no "
					+ "texture. `--headless` always does this; on a machine with no display "
					+ "run `xvfb-run -a just film ...`."
				)
			)
			_finish(1)
			return

		var path: String = outdir.path_join("frame_%04d.png" % index)
		if frame.save_png(path) != OK:
			printerr("could not write %s" % path)
			_finish(1)
			return

	printerr(
		(
			"film: %d frame(s) over %d tick(s) from seed %d -> %s"
			% [wanted.size(), ticks, seed, outdir]
		)
	)
	_finish(0)


func _finish(code: int) -> void:
	process_frame.disconnect(_aborted)
	quit(code)


## Generous: one capture is three frames, and there are at most twelve of them.
const FRAME_BUDGET: int = 2000

var _frames: int = 0


func _aborted() -> void:
	_frames += 1
	if _frames < FRAME_BUDGET:
		return
	printerr(
		(
			(
				"FILM ABORTED or hung: %d frames elapsed without finishing. Scroll up for a "
				% FRAME_BUDGET
			)
			+ "SCRIPT ERROR. If there is none, a capture is blocking — check that nothing "
			+ "awaits RenderingServer.frame_post_draw, which never fires without a display."
		)
	)
	quit(70)
