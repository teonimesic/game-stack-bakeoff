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

const GOLDEN: String = "res://tests/golden/frame.png"
const GOLDEN_ACTUAL: String = "res://tests/golden/frame.actual.png"
const GOLDEN_EXPECTED: String = "res://tests/golden/frame.expected.png"
const GOLDEN_DIFF: String = "res://tests/golden/frame.diff.png"
## Budget for cross-driver rasterisation rounding, as a fraction of all pixels.
const GOLDEN_BUDGET: float = 0.002
const INK_TOLERANCE: int = 8
## Captures to allow the window before giving up on it reaching its final size.
const SETTLE_ATTEMPTS: int = 20

var _tree: SceneTree
var _view: View
var _bless: bool = false


func _init(tree: SceneTree, bless: bool) -> void:
	_tree = tree
	_bless = bless


func setup() -> void:
	_hide_window()
	RenderingServer.set_default_clear_color(View.BACKGROUND_COLOR)
	_view = View.new()
	_tree.root.add_child(_view)


## Keep the render window OUT OF THE WAY. It still exists and still draws — that
## is the whole reason `--headless` is not used here — but it must not steal the
## keyboard from whoever is at the machine.
##
## Two grading runs happen concurrently under the evaluation harness, and a window
## that takes focus makes the operator's machine unusable for the duration and can
## interrupt whatever else is typing. `WINDOW_FLAG_NO_FOCUS` stops the steal;
## moving it off the visible desktop stops the flash. Neither changes a pixel of
## what is rendered, because the readback is of the viewport texture and not of
## the screen.
##
## Skipped under the headless driver, where there is no window to move and these
## calls mean nothing — that run still reaches the SKIP path in `run_all`.
func _hide_window() -> void:
	if DisplayServer.get_name() == "headless":
		return
	DisplayServer.window_set_flag(DisplayServer.WINDOW_FLAG_NO_FOCUS, true)
	# Far enough off the primary display that it cannot appear, near enough that
	# no compositor clamps it back into view.
	DisplayServer.window_set_position(Vector2i(-4000, -4000))


## A capture needs a window that is still DRAWING, and a MINIMISED one is not.
##
## macOS stops producing frames for a minimised window and keeps handing back the last
## image it drew, so `get_texture().get_image()` returns a STALE picture rather than
## null — every capture in this file then compares the same frozen frame, with nothing
## red to say why. Measured on the pristine starter: the golden test was handed the
## tick-1 probe capture, the HUD was identical at tick 20 and tick 200, a burst added
## 0.0000% ink, and 6 of the 9 tests failed pointing at the arena transform, the
## particle system and the HUD — none of which was wrong.
##
## The cause here is `tools/no_raise.gd`, an `[autoload]` that therefore runs in THIS
## process too and minimises the window as its last resort when the window took focus
## anyway. That is racy: 5 of 12 pristine `just test-render` runs took it. But this is
## written as the PRECONDITION the capture needs and not as a fix for that one cause,
## so a window minimised by anything else — a future guard, a person, the OS — is
## handled too.
##
## Restoring does NOT hand focus back to this app: measured, the frontmost application
## returned to the operator's and stayed there.
func _ensure_drawing_window() -> void:
	if DisplayServer.get_name() == "headless":
		return
	if DisplayServer.window_get_mode() != DisplayServer.WINDOW_MODE_MINIMIZED:
		return
	DisplayServer.window_set_mode(DisplayServer.WINDOW_MODE_WINDOWED)
	# Restoring re-applies the mode, not the position or the focus flag.
	_hide_window()
	for i: int in range(3):
		await _tree.process_frame


## Background as u8 RGB, for "is this pixel ink?" tests.
func background() -> PackedByteArray:
	return View.to_u8(View.BACKGROUND_COLOR)


## The marker's colour as u8 RGB, for "is this pixel the MARKER?" tests. The
## frame carries a HUD as well as the arena, so the tests that are about the
## marker have to say which ink they mean.
func marker_ink() -> PackedByteArray:
	return View.to_u8(View.MARKER_COLOR)


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
## [param bursts] is the [Fx] layer's whole input, and it is a parameter of the
## capture rather than something the view remembers for the same reason the tick
## count is: this helper syncs the view exactly once, at a known tick. See
## `view/fx.gd`.
func capture_frame(
	seed: int, ticks: int, inputs: Array[Sim.Intents], bursts: Array[Fx.Burst] = []
) -> Frame:
	var world: Sim.World = Sim.spawn_world(seed)
	for tick: int in range(ticks):
		Sim.step(world, inputs[tick] if tick < inputs.size() else null)

	# The root viewport reports its DEFAULT rect for the first frames of a run,
	# while the texture it hands back is already the real window size. Framing the
	# arena against that stale size draws a miniature arena in the corner of a
	# full-size capture, which reads exactly like a broken transform. So the size
	# the arena was framed against has to agree with the pixels that came back, or
	# the capture is taken again. On a settled window this costs one pass.
	var frame: Frame = null
	for attempt: int in range(SETTLE_ATTEMPTS):
		# Before the size settles, the window has to be drawing at all. This consumes
		# no settle attempt: exhausting them returns a null frame, which `run_all`
		# reports as nine SKIPs and exit 0 — a green that measured nothing (rule 1).
		await _ensure_drawing_window()
		var size: Vector2 = _tree.root.get_visible_rect().size
		_view.frame_arena(size)
		_view.sync(world)
		_view.fx.show_bursts(bursts)

		# Wait for whole frames rather than `RenderingServer.frame_post_draw`. That
		# signal NEVER FIRES under `--headless` and the await deadlocks the script
		# with no error and no timeout — the single most expensive trap in this
		# stack. `process_frame` always fires, so a display-less run reaches the null
		# check below and reports a skip instead of hanging.
		for i: int in range(3):
			await _tree.process_frame

		frame = Frame.from_image(_tree.root.get_texture().get_image())
		if frame == null:
			return null
		if frame.width == roundi(size.x) and frame.height == roundi(size.y):
			return frame
	# Never settled. Return the last capture rather than null: a test that fails on
	# the pixels says more than a skip that blames the machine.
	return frame


func run_all(t: TestRunner) -> void:
	# One probe decides whether this machine can capture pixels at all. Doing it
	# once, up front, keeps the skip message to a single line instead of five.
	var probe: Frame = await capture_frame(0, 1, [])
	if probe == null:
		for name: String in [
			"renders a non-empty frame",
			"the marker is visible",
			"moving the marker up moves its pixels up",
			"the HUD is inside the captured frame",
			"rendering is reproducible across runs",
			"matches the golden frame",
			"a particle burst reaches the captured frame",
			"a particle burst is driven by its age, not by the clock",
			"a particle burst is reproducible across runs",
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

	t.begin("the marker is visible")
	await _marker_visible(t)
	t.end()

	t.begin("moving the marker up moves its pixels up")
	await _marker_moves_up(t)
	t.end()

	t.begin("the HUD is inside the captured frame")
	await _hud_in_frame(t)
	t.end()

	t.begin("rendering is reproducible across runs")
	await _reproducible(t)
	t.end()

	t.begin("matches the golden frame")
	await _golden(t)
	t.end()

	# Godot ships a particle system and the other three stacks in this comparison
	# do not, so `view/fx.gd` is a capability the template exposes deliberately.
	# These three are its controls, and the middle one is the load-bearing one: a
	# reproducibility test alone would pass just as happily on a burst that never
	# renders at all.
	t.begin("a particle burst reaches the captured frame")
	await _burst_is_drawn(t)
	t.end()

	t.begin("a particle burst is driven by its age, not by the clock")
	await _burst_ages(t)
	t.end()

	t.begin("a particle burst is reproducible across runs")
	await _burst_reproducible(t)
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


func _marker_visible(t: TestRunner) -> void:
	# One tick in, the marker has barely left the origin, so its ink must land in
	# the middle band of the frame. An invariant, not a golden: it survives a
	# colour or size change and still fails if the view stops following the sim.
	#
	# It asks specifically for MARKER-coloured pixels, because the frame also
	# carries a HUD: "the centroid of everything that is not the background" would
	# be a statement about the marker and the HUD averaged together, and moving the
	# HUD would move it without the simulation having moved at all. Reading the
	# colour from `View` rather than hard-coding it keeps the test surviving a
	# palette change.
	var frame: Frame = await capture_frame(2, 1, [])
	var centroid: Frame.Centroid = frame.color_centroid(
		marker_ink(), INK_TOLERANCE, whole_frame(frame)
	)
	t.check(centroid.found, "no marker-coloured pixel anywhere in the frame")
	if not centroid.found:
		return

	var middle := Rect2i(frame.width / 4, frame.height / 4, frame.width / 2, frame.height / 2)
	t.check(
		middle.has_point(Vector2i(roundi(centroid.x), roundi(centroid.y))),
		(
			(
				"marker ink is centred at (%.1f, %.1f), outside the middle band of a %dx%d frame — "
				+ "the arena transform is probably wrong, or the view is drawing something "
				+ "other than the simulation."
			)
			% [centroid.x, centroid.y, frame.width, frame.height]
		)
	)


func _marker_moves_up(t: TestRunner) -> void:
	# A relational assertion: robust to colour changes, size changes and driver
	# differences, but still a genuine end-to-end check that intent reaches the
	# screen.
	#
	# Screen y grows downward, so "up" in world space means a SMALLER pixel y.
	var hold_up: Array[Sim.Intents] = []
	for i: int in range(60):
		hold_up.append(Sim.Intents.new(true, false))

	var still: Frame = await capture_frame(3, 60, [])
	var raised: Frame = await capture_frame(3, 60, hold_up)
	var ink: PackedByteArray = marker_ink()

	var region: Rect2i = whole_frame(still)
	var still_centroid: Frame.Centroid = still.color_centroid(ink, INK_TOLERANCE, region)
	var raised_centroid: Frame.Centroid = raised.color_centroid(ink, INK_TOLERANCE, region)
	t.check(still_centroid.found and raised_centroid.found, "no marker-coloured pixel in frame")
	if not (still_centroid.found and raised_centroid.found):
		return

	t.lt(
		raised_centroid.y,
		still_centroid.y - 10.0,
		(
			(
				"holding nudge_up for 60 ticks should raise the marker on screen, but its "
				+ "centroid moved from y=%.1f to y=%.1f"
			)
			% [still_centroid.y, raised_centroid.y]
		)
	)


## The HUD has to be drawn by a node the capture path renders.
##
## `capture_frame` puts a bare [View] in the root viewport — `main.tscn` and its
## `Main` node are never instantiated. A HUD parented under the main scene
## instead of under the view therefore shows up in `just run` and is ABSENT from
## every rendering test and every frame of `just film`, with nothing red to say
## so. This test is what makes that arrangement fail loudly.
##
## It matches on the HUD colour rather than on "not the background", so a marker
## bouncing through the same corner cannot stand in for the HUD.
func _hud_in_frame(t: TestRunner) -> void:
	var early: Frame = await capture_frame(6, 20, [])
	var later: Frame = await capture_frame(6, 200, [])
	var region: Rect2i = View.hud_region()
	var hud: PackedByteArray = View.to_u8(View.HUD_COLOR)

	var early_mask: PackedByteArray = early.color_mask(hud, INK_TOLERANCE, region)
	var later_mask: PackedByteArray = later.color_mask(hud, INK_TOLERANCE, region)
	var early_ink: int = early_mask.count(1)

	t.gt(
		float(early_ink),
		40.0,
		(
			(
				"only %d pixel(s) in the HUD region %s are the HUD colour. The HUD did not "
				+ "reach the captured frame. The capture renders a viewport holding ONLY the "
				+ "View node, so a HUD parented anywhere else — under Main, under a sibling "
				+ "CanvasLayer — is invisible here and in every `just film` frame."
			)
			% [early_ink, region]
		)
	)
	if early_ink <= 0:
		return

	# The HUD reports the tick, so two different tick counts must not paint the
	# same pixels. Comparing the colour masks, not the raw pixels, keeps the
	# marker's own movement out of the comparison.
	t.check(
		early_mask != later_mask,
		(
			(
				"the HUD is identical at tick 20 and tick 200 (%d and %d lit pixels). It is "
				+ "being drawn, but it is not showing the state — a HUD that never changes "
				+ "reports nothing."
			)
			% [early_ink, later_mask.count(1)]
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


## The colour the burst controls emit in: deliberately neither the marker's nor
## the HUD's, so "burst ink" cannot be satisfied by either of them.
const BURST_COLOR: Color = Color(1.0, 0.42, 0.16)
## Seeded from a fixed id, so the burst these tests draw is the same burst every
## time — see `view/fx.gd`.
const BURST_ID: int = 1


## One burst at the centre of the arena, [param age] seconds old.
func _one_burst(age: float) -> Array[Fx.Burst]:
	var bursts: Array[Fx.Burst] = []
	bursts.append(Fx.Burst.new(Vector2.ZERO, BURST_COLOR, age, BURST_ID))
	return bursts


## Does asking for a burst put more ink on screen than not asking for one?
##
## The weakest of the three and the one that has to pass first: everything else
## here is a statement about a burst that is assumed to exist.
func _burst_is_drawn(t: TestRunner) -> void:
	var bare: Frame = await capture_frame(8, 20, [])
	var lit: Frame = await capture_frame(8, 20, [], _one_burst(0.12))
	var bare_ink: float = bare.ink_coverage(background(), INK_TOLERANCE)
	var lit_ink: float = lit.ink_coverage(background(), INK_TOLERANCE)
	t.gt(
		lit_ink,
		bare_ink + 0.0005,
		(
			(
				"a burst added %.4f%% ink to a frame that already had %.4f%% — the particle "
				+ "system is not reaching the captured viewport. Check that Fx is a child of "
				+ "the View (the capture renders a viewport holding ONLY the View) and that "
				+ "the burst is inside the arena."
			)
			% [(lit_ink - bare_ink) * 100.0, bare_ink * 100.0]
		)
	)


## Is `age` actually driving the particle system?
##
## THE VARIANT, not the mutant (AGENTS.md rule 15). `speed_scale = 0` is what
## makes a burst reproducible, and a burst that has been frozen so hard that it
## never advances at all would pass the reproducibility test perfectly. Two ages
## have to produce two different pictures, or the parameter is decorative.
func _burst_ages(t: TestRunner) -> void:
	var young: Frame = await capture_frame(8, 20, [], _one_burst(0.02))
	var old: Frame = await capture_frame(8, 20, [], _one_burst(0.40))
	var diff: float = young.diff_fraction(old, INK_TOLERANCE)
	t.gt(
		diff,
		0.0005,
		(
			(
				"a burst 0.02 s old and one 0.40 s old differ in only %.4f%% of pixels. The "
				+ "age is not reaching the emitter — check that `preprocess` is set BEFORE "
				+ "`restart()` in view/fx.gd."
			)
			% (diff * 100.0)
		)
	)


## Same state, same pixels — with a burst on screen.
##
## Particles are the one thing in this template that is animated by wall time by
## default, and `rendering is reproducible across runs` covers the frame without
## one. This is the same assertion over the path where it can actually fail.
func _burst_reproducible(t: TestRunner) -> void:
	var a: Frame = await capture_frame(9, 33, [], _one_burst(0.20))
	var b: Frame = await capture_frame(9, 33, [], _one_burst(0.20))
	var diff: float = a.diff_fraction(b, 0)
	if diff > 0.0:
		var diff_path: String = "res://tests/golden/burst.diff.png"
		a.diff_image(b, 0).save_png(diff_path)
		t.check(
			false,
			(
				(
					"two identical bursts produced different frames (%.4f%% of pixels differ). "
					+ "A particle emitter that is advanced by the frame delta rather than by "
					+ "`preprocess` does exactly this. Magenta pixels in %s are where they "
					+ "disagree."
				)
				% [diff * 100.0, ProjectSettings.globalize_path(diff_path)]
			)
		)
