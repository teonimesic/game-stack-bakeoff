## Presentation layer: turns simulation state into something you can see.
##
## Strict one-way data flow. This script reads [Sim] and never writes to it.
## Everything here is disposable; the simulation is the source of truth.
class_name View
extends Node2D

const VIEW_WIDTH: int = 640
const VIEW_HEIGHT: int = 400

## Colours are written to the framebuffer verbatim: Godot's 2D canvas does no
## sRGB/linear conversion, so a channel of 0.35 lands on screen as
## `round(0.35 * 255) = 89`. That is what makes byte-exact pixel assertions in
## `tests/render_test.gd` meaningful rather than a test of Godot's colour
## pipeline. Do not add a WorldEnvironment with tonemapping to this scene.
const MARKER_COLOR: Color = Color(1.0, 0.92, 0.30)
const BACKGROUND_COLOR: Color = Color(0.04, 0.05, 0.09)

## The HUD is drawn by THIS node, not by a sibling of it, because the frame
## capture (`RenderTests.capture_frame`, which `just film` reuses) renders a
## viewport containing only the [View]. A HUD parented under `main.tscn` would
## show up in `just run` and be missing from every filmed frame and every
## rendering test. See AGENTS.md.
const HUD_COLOR: Color = Color(0.55, 0.87, 1.0)
const HUD_FONT_SIZE: int = 14
## Baseline of the HUD line, in viewport pixels from the top-left.
const HUD_BASELINE: Vector2 = Vector2(12.0, 38.0)

## The world being drawn. Read-only from here.
var world: Sim.World = null

## Godot's GPU particle system, wired up and idle. Nothing emits until something
## calls [method Fx.show_bursts]; the starter never does. Godot is the only stack
## in this comparison that ships particles at all — see `view/fx.gd`, which also
## explains the one rule (a burst is a pure function of simulation state, because
## the capture path never sees the ticks in between).
var fx: Fx = null


## `_init`, not `_ready`: a [View] built with `View.new()` and parented to the
## SceneTree root during `_initialize` does not get `_ready` until the first
## frame, and `RenderTests.capture_frame` reaches for `fx` before then.
func _init() -> void:
	fx = Fx.new()
	add_child(fx)


## The same colour as the renderer writes it: 0..255 per channel, RGB only.
static func to_u8(color: Color) -> PackedByteArray:
	var bytes := PackedByteArray()
	bytes.resize(3)
	bytes[0] = roundi(color.r * 255.0)
	bytes[1] = roundi(color.g * 255.0)
	bytes[2] = roundi(color.b * 255.0)
	return bytes


## The transform that frames the whole arena inside a viewport of [param size].
##
## The half-extents come from the simulation, so the view cannot drift out of
## sync with the arena the rules are enforced against. The negative Y scale is
## the "camera": simulation Y grows upward, screen Y grows downward.
static func arena_transform(size: Vector2) -> Transform2D:
	var scale := Vector2(
		size.x / (Sim.ARENA_HALF_WIDTH * 2.0), -size.y / (Sim.ARENA_HALF_HEIGHT * 2.0)
	)
	return Transform2D(0.0, scale, 0.0, size * 0.5)


## Fit this node to a viewport of [param size].
func frame_arena(size: Vector2) -> void:
	transform = arena_transform(size)


## The viewport-pixel box the HUD line occupies. The rendering tests assert that
## HUD ink lands in here, so it is defined next to the constants that place it
## rather than duplicated in the test.
static func hud_region() -> Rect2i:
	return Rect2i(0, 0, VIEW_WIDTH, roundi(HUD_BASELINE.y) + HUD_FONT_SIZE)


## The HUD line for a world. Pure and headless, so the text can be asserted on
## without a display; the pixels it becomes are asserted on separately.
static func hud_text(p_world: Sim.World) -> String:
	if p_world == null:
		return ""
	var marker: Sim.Entity = p_world.first_of_kind(Sim.Kind.MARKER)
	if marker == null:
		return "tick %d" % p_world.tick
	return (
		"tick %d   marker %d, %d"
		% [p_world.tick, roundi(marker.position.x), roundi(marker.position.y)]
	)


## Copy simulation state onto the scene. One way only.
func sync(p_world: Sim.World) -> void:
	world = p_world
	queue_redraw()


func _draw() -> void:
	if world == null:
		return
	# Sim-id order, so draw order (and therefore overlap) is deterministic.
	for entity: Sim.Entity in world.by_sim_id():
		if entity.kind == Sim.Kind.MARKER:
			draw_rect(
				Rect2(
					entity.position - Vector2(Sim.MARKER_HALF_SIZE, Sim.MARKER_HALF_SIZE),
					Vector2(Sim.MARKER_HALF_SIZE * 2.0, Sim.MARKER_HALF_SIZE * 2.0)
				),
				MARKER_COLOR
			)
	_draw_hud()


## The HUD, in viewport pixels rather than arena units.
##
## [member Node2D.transform] frames the arena and carries a NEGATIVE Y scale, and
## every draw call in this node inherits it — text drawn naively comes out
## upside-down and stretched with the arena. Undoing the node transform for the
## duration of the HUD puts these calls back in screen space, so the HUD keeps
## its size and orientation whatever the arena does.
func _draw_hud() -> void:
	draw_set_transform_matrix(transform.affine_inverse())
	draw_string(
		ThemeDB.fallback_font,
		HUD_BASELINE,
		hud_text(world),
		HORIZONTAL_ALIGNMENT_LEFT,
		-1.0,
		HUD_FONT_SIZE,
		HUD_COLOR
	)
	draw_set_transform_matrix(Transform2D.IDENTITY)
