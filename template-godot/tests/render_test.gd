## End-to-end rendering tests: the real renderer, a real GPU, real pixels.
##
## These are the tests that catch "the code compiles, the logic is right, and
## nothing appears on screen." Simulation tests cannot catch that class of bug,
## and it is the class that matters most in a game.
##
## Ordered from most robust to most brittle:
##   1. invariants on the pixels (something rendered; it is where we expect)
##   2. relational assertions (it moved in the right direction)
##   3. golden-image comparison (it looks exactly like the approved frame)
##
## Prefer 1 and 2. Reach for 3 only when the exact look is the thing under test.
##
## THESE CANNOT RUN HEADLESS. `godot --headless` swaps in a dummy rendering
## driver: `get_viewport().get_texture().get_image()` returns null and nothing is
## ever drawn. `just test-render` opens a real 640x400 window. See AGENTS.md.
class_name RenderTests
extends RefCounted

const GOLDEN: String = "res://tests/golden/rally.png"
const GOLDEN_ACTUAL: String = "res://tests/golden/rally.actual.png"
const GOLDEN_EXPECTED: String = "res://tests/golden/rally.expected.png"
const GOLDEN_DIFF: String = "res://tests/golden/rally.diff.png"
## Budget for cross-driver rasterisation rounding, as a fraction of all pixels.
const GOLDEN_BUDGET: float = 0.002
const INK_TOLERANCE: int = 8

var _tree: SceneTree
var _view: View
var _bless: bool = false


func _init(tree: SceneTree, bless: bool) -> void:
	_tree = tree
	_bless = bless


func setup() -> void:
	RenderingServer.set_default_clear_color(View.BACKGROUND_COLOR)
	_view = View.new()
	_tree.root.add_child(_view)


## Background as u8 RGB, for "is this pixel ink?" tests.
func background() -> PackedByteArray:
	return View.to_u8(View.BACKGROUND_COLOR)


func whole_frame(frame: Frame) -> Rect2i:
	return Rect2i(0, 0, frame.width, frame.height)


## Advance a fresh world by [param ticks] ticks, draw it, and read the pixels
## back.
##
## The simulation is advanced with the same discipline the pure sim tests use —
## explicit `Sim.step` calls — so the rendered frame corresponds to an exactly
## known tick. There is no "roughly one second in" ambiguity, and no dependence
## on how many frames the window manager decided to give us.
##
## Returns null when the viewport has no texture, which is what a display-less
## run produces.
func capture_frame(seed: int, ticks: int, inputs: Array[Sim.Intents]) -> Frame:
	var world: Sim.World = Sim.spawn_world(seed)
	for tick: int in range(ticks):
		Sim.step(world, inputs[tick] if tick < inputs.size() else null)

	_view.frame_arena(_tree.root.get_visible_rect().size)
	_view.sync(world)

	# Wait for whole frames rather than `RenderingServer.frame_post_draw`. That
	# signal NEVER FIRES under `--headless` and the await deadlocks the script
	# with no error and no timeout — the single most expensive trap in this
	# stack. `process_frame` always fires, so a display-less run reaches the null
	# check below and reports a skip instead of hanging.
	for i: int in range(3):
		await _tree.process_frame
	return Frame.from_image(_tree.root.get_texture().get_image())


func run_all(t: TestRunner) -> void:
	# One probe decides whether this machine can capture pixels at all. Doing it
	# once, up front, keeps the skip message to a single line instead of five.
	var probe: Frame = await capture_frame(0, 1, [])
	if probe == null:
		for name: String in [
			"renders a non-empty frame",
			"both paddles and the ball are visible",
			"moving a paddle up moves its pixels up",
			"rendering is reproducible across runs",
			"matches the golden frame",
		]:
			t.begin(name)
			t.skip(
				(
					"this environment cannot capture pixels — the root viewport has no "
					+ "texture. `--headless` always does this; use `just test-render`, and on "
					+ "a headless Linux box wrap it in `xvfb-run`."
				)
			)
			t.end()
		return

	t.begin("renders a non-empty frame")
	await _non_empty(t)
	t.end()

	t.begin("both paddles and the ball are visible")
	await _paddles_and_ball(t)
	t.end()

	t.begin("moving a paddle up moves its pixels up")
	await _paddle_moves_up(t)
	t.end()

	t.begin("rendering is reproducible across runs")
	await _reproducible(t)
	t.end()

	t.begin("matches the golden frame")
	await _golden(t)
	t.end()


func _non_empty(t: TestRunner) -> void:
	# The single most valuable rendering assertion there is: the renderer ran and
	# drew something other than the clear colour.
	var frame: Frame = await capture_frame(1, 30, [])
	t.eq(
		Vector2i(frame.width, frame.height),
		Vector2i(View.VIEW_WIDTH, View.VIEW_HEIGHT),
		(
			"captured frame is not the configured viewport size; check "
			+ "display/window/size in project.godot and the --resolution flag in the "
			+ "justfile"
		)
	)

	var coverage: float = frame.ink_coverage(background(), INK_TOLERANCE)
	t.gt(
		coverage,
		0.001,
		(
			(
				"nothing was drawn — %.4f%% of pixels differ from the background. The "
				+ "simulation may be running correctly while the view is broken."
			)
			% (coverage * 100.0)
		)
	)
	t.lt(
		coverage,
		0.5,
		(
			(
				"%.1f%% of the frame is non-background; the arena transform is probably "
				+ "mis-scaled or a rectangle is covering the screen"
			)
			% (coverage * 100.0)
		)
	)


func _paddles_and_ball(t: TestRunner) -> void:
	var frame: Frame = await capture_frame(2, 1, [])

	# Paddles sit near the left and right edges; the ball starts centred.
	# (A lambda would read better, but `Callable.call` returns Variant and the
	# strict-typing warnings reject that where a `bool` is wanted.)
	t.check(
		_column_has_ink(frame, 0, frame.width / 6),
		"no ink in the left sixth of the frame — the left paddle is missing"
	)
	t.check(
		_column_has_ink(frame, frame.width * 5 / 6, frame.width),
		"no ink in the right sixth of the frame — the right paddle is missing"
	)
	t.check(
		_column_has_ink(frame, frame.width * 2 / 5, frame.width * 3 / 5),
		"no ink in the centre — the ball is missing"
	)


func _column_has_ink(frame: Frame, x_lo: int, x_hi: int) -> bool:
	var strip := Rect2i(x_lo, 0, x_hi - x_lo, frame.height)
	return frame.ink_centroid(background(), INK_TOLERANCE, strip).found


func _paddle_moves_up(t: TestRunner) -> void:
	# A relational assertion: robust to colour changes, size changes and driver
	# differences, but still a genuine end-to-end check that intent reaches the
	# screen.
	#
	# Screen y grows downward, so "up" in world space means a SMALLER pixel y.
	var hold_up: Array[Sim.Intents] = []
	for i: int in range(60):
		hold_up.append(
			Sim.Intents.new(Sim.PlayerIntent.new(true, false), Sim.PlayerIntent.new(false, false))
		)

	var still: Frame = await capture_frame(3, 60, [])
	var raised: Frame = await capture_frame(3, 60, hold_up)
	var bg: PackedByteArray = background()

	# Look only at the left sixth so the ball and right paddle cannot confuse us.
	var left_strip := Rect2i(0, 0, still.width / 6, still.height)
	var still_centroid: Frame.Centroid = still.ink_centroid(bg, INK_TOLERANCE, left_strip)
	var raised_centroid: Frame.Centroid = raised.ink_centroid(bg, INK_TOLERANCE, left_strip)
	t.check(still_centroid.found and raised_centroid.found, "left paddle not found in frame")
	if not (still_centroid.found and raised_centroid.found):
		return

	t.lt(
		raised_centroid.y,
		still_centroid.y - 10.0,
		(
			(
				"holding 'up' for 60 ticks should raise the left paddle on screen, but its "
				+ "centroid moved from y=%.1f to y=%.1f"
			)
			% [still_centroid.y, raised_centroid.y]
		)
	)


func _reproducible(t: TestRunner) -> void:
	# Same seed, same ticks, same pixels. If this fails, either the simulation is
	# nondeterministic (check `just test-sim` first) or the render path is.
	var a: Frame = await capture_frame(4, 45, [])
	var b: Frame = await capture_frame(4, 45, [])

	var diff: float = a.diff_fraction(b, 0)
	if diff > 0.0:
		var diff_path: String = "res://tests/golden/reproducibility.diff.png"
		a.diff_image(b, 0).save_png(diff_path)
		t.check(
			false,
			(
				(
					"two identical runs produced different frames (%.4f%% of pixels differ). "
					+ "Magenta pixels in %s are where they disagree."
				)
				% [diff * 100.0, ProjectSettings.globalize_path(diff_path)]
			)
		)


## Golden-image comparison.
##
## Regenerate deliberately with `just bless`, and LOOK AT THE NEW IMAGE before
## committing it. Blessing without looking turns this test into a rubber stamp.
func _golden(t: TestRunner) -> void:
	var frame: Frame = await capture_frame(5, 90, [])

	if _bless:
		var status: Error = frame.save_png(GOLDEN)
		t.eq(status, OK, "failed to write %s" % GOLDEN)
		print("      blessed %s" % ProjectSettings.globalize_path(GOLDEN))
		return

	var golden: Frame = Frame.load_png(GOLDEN)
	if golden == null:
		t.skip(
			(
				(
					"no golden image at %s. Create it with `just bless`, then OPEN THE PNG and "
					+ "confirm it looks right before committing."
				)
				% ProjectSettings.globalize_path(GOLDEN)
			)
		)
		return
	if golden.width != frame.width or golden.height != frame.height:
		t.check(
			false,
			(
				(
					"golden image is %dx%d but the capture is %dx%d — re-bless after a "
					+ "viewport size change"
				)
				% [golden.width, golden.height, frame.width, frame.height]
			)
		)
		return

	# Tolerance absorbs cross-driver rasterisation rounding, not misplaced
	# geometry. A rectangle in the wrong place moves thousands of pixels, not a
	# handful. If this fails by a lot, it found a real bug — do not widen the
	# budget.
	var diff: float = frame.diff_fraction(golden, 4)
	if diff <= GOLDEN_BUDGET:
		return

	# Failure legibility: write all three images and print their OS paths, so the
	# next action is "open these", not "guess".
	frame.save_png(GOLDEN_ACTUAL)
	golden.save_png(GOLDEN_EXPECTED)
	frame.diff_image(golden, 4).save_png(GOLDEN_DIFF)
	(
		t
		. check(
			false,
			(
				(
					"rendered frame differs from the golden image in %.3f%% of pixels "
					+ "(budget %.3f%%, %d of %d pixels).\n"
					+ "        actual:   %s\n"
					+ "        expected: %s\n"
					+ "        diff:     %s  (magenta = disagrees)\n"
					+ "        Open them. A silhouette in the diff means geometry moved and this "
					+ "is a real bug. Scattered speckle means driver rounding. If the change is "
					+ "intended, run `just bless` and look at the new PNG."
				)
				% [
					diff * 100.0,
					GOLDEN_BUDGET * 100.0,
					roundi(diff * float(frame.width * frame.height)),
					frame.width * frame.height,
					ProjectSettings.globalize_path(GOLDEN_ACTUAL),
					ProjectSettings.globalize_path(GOLDEN_EXPECTED),
					ProjectSettings.globalize_path(GOLDEN_DIFF),
				]
			)
		)
	)
