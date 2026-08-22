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
const BALL_COLOR: Color = Color(1.0, 0.92, 0.30)
const PADDLE_COLOR: Color = Color(0.35, 0.78, 1.0)
const BACKGROUND_COLOR: Color = Color(0.04, 0.05, 0.09)

const PADDLE_WIDTH: float = 16.0

## The world being drawn. Read-only from here.
var world: Sim.World = null


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


## Copy simulation state onto the scene. One way only.
func sync(p_world: Sim.World) -> void:
	world = p_world
	queue_redraw()


func _draw() -> void:
	if world == null:
		return
	# Sim-id order, so draw order (and therefore overlap) is deterministic.
	for entity: Sim.Entity in world.by_sim_id():
		if entity.kind == Sim.Kind.BALL:
			draw_rect(
				Rect2(
					entity.position - Vector2(Sim.BALL_RADIUS, Sim.BALL_RADIUS),
					Vector2(Sim.BALL_RADIUS * 2.0, Sim.BALL_RADIUS * 2.0)
				),
				BALL_COLOR
			)
		elif entity.kind == Sim.Kind.PADDLE:
			draw_rect(
				Rect2(
					entity.position - Vector2(PADDLE_WIDTH * 0.5, Sim.PADDLE_HALF_HEIGHT),
					Vector2(PADDLE_WIDTH, Sim.PADDLE_HALF_HEIGHT * 2.0)
				),
				PADDLE_COLOR
			)
