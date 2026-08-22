## HELD-OUT. The agent never sees this file.
##
## Grades the "draw a centre net" task by looking at real rendered pixels.
##
## THIS CANNOT RUN HEADLESS. `godot --headless` swaps in a dummy rendering
## driver: the root viewport has no texture and nothing is ever drawn. The
## holdout command deliberately omits `--headless`; see
## `tests/run_holdout_render.gd`.
class_name HoldoutNetTests
extends RefCounted

# The template runs GDScript warnings as errors. A held-out test must reach for
# members the implementation may not have yet — inherently unsafe access, which
# is the entire point of it.
@warning_ignore_start("unsafe_method_access", "unsafe_property_access", "unsafe_cast", "unsafe_call_argument", "untyped_declaration", "inferred_declaration", "integer_division")

const TOLERANCE: int = 8

const NAMES: Array[String] = [
	"a centre net is drawn down the middle",
	"the net does not cover the play area",
	"adding the net did not break the paddles",
]

var _r: RenderTests
var _bg: PackedByteArray


func _init(tree: SceneTree) -> void:
	_r = RenderTests.new(tree, false)
	_r.setup()
	_bg = _r.background()


func _is_ink(frame: Frame, x: int, y: int) -> bool:
	var p := frame.pixel(x, y)
	return (
		absi(p[0] - _bg[0]) > TOLERANCE
		or absi(p[1] - _bg[1]) > TOLERANCE
		or absi(p[2] - _bg[2]) > TOLERANCE
	)


func _band_has_ink(frame: Frame, x_lo: int, x_hi: int) -> bool:
	for x: int in range(x_lo, x_hi):
		for y: int in range(frame.height):
			if _is_ink(frame, x, y):
				return true
	return false


func run_all(t: TestRunner) -> void:
	# One probe decides whether this machine can capture pixels at all, exactly
	# as `tests/render_test.gd` does. A skip is NOT a pass — the harness counts
	# any skipped held-out test as a broken trial — but it beats hanging.
	var probe: Frame = await _r.capture_frame(0, 1, [])
	if probe == null:
		for name: String in NAMES:
			t.begin(name)
			t.skip(
				(
					"this environment cannot capture pixels — the root viewport has no "
					+ "texture. `--headless` always does this; the holdout command must "
					+ "run windowed, and on a headless Linux box under `xvfb-run`."
				)
			)
			t.end()
		return

	t.begin(NAMES[0])
	await _net_down_the_middle(t)
	t.end()

	t.begin(NAMES[1])
	await _does_not_cover_the_play_area(t)
	t.end()

	t.begin(NAMES[2])
	await _paddles_still_render(t)
	t.end()


## Rows with ink in a narrow band at the exact centre. The ball is small and
## lights a handful of rows; a net lights most of them.
func _net_down_the_middle(t: TestRunner) -> void:
	var frame: Frame = await _r.capture_frame(11, 20, [])
	var mid: int = frame.width / 2
	var lit_rows: int = 0
	for y: int in range(frame.height):
		for x: int in range(maxi(mid - 3, 0), mini(mid + 4, frame.width)):
			if _is_ink(frame, x, y):
				lit_rows += 1
				break
	var fraction: float = float(lit_rows) / float(frame.height)
	t.gt(
		fraction,
		0.30,
		(
			(
				"expected a visible net down the centre: only %d/%d rows (%.0f%%) have ink "
				+ "within 3px of the middle. A ball alone lights a few rows; a net lights "
				+ "most of them."
			)
			% [lit_rows, frame.height, fraction * 100.0]
		)
	)


func _does_not_cover_the_play_area(t: TestRunner) -> void:
	var frame: Frame = await _r.capture_frame(12, 20, [])
	var coverage: float = frame.ink_coverage(_bg, TOLERANCE)
	t.lt(
		coverage,
		0.25,
		(
			(
				"%.1f%% of the frame is non-background — the net is far too wide, or "
				+ "something is covering the arena"
			)
			% (coverage * 100.0)
		)
	)


func _paddles_still_render(t: TestRunner) -> void:
	var frame: Frame = await _r.capture_frame(13, 20, [])
	t.check(_band_has_ink(frame, 0, frame.width / 6), "left paddle disappeared")
	t.check(
		_band_has_ink(frame, frame.width * 5 / 6, frame.width), "right paddle disappeared"
	)
