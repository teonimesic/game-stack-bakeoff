## Playable entry point: window, keyboard, and the engine's fixed timestep.
##
## The ONLY script in the repo allowed to read an input device. It latches
## devices into [Sim.Intents] on the render frame and hands them to the
## simulation on the physics tick; the simulation never sees a key.
extends Node2D

var _world: Sim.World = Sim.spawn_world(0)
var _view: View = null

## Intent accumulated since the last physics tick. Latched with `or` rather than
## sampled, so a key that is pressed and released between two physics ticks is
## still seen exactly once instead of being dropped.
var _latched: Sim.Intents = Sim.Intents.new()


func _ready() -> void:
	assert(
		Engine.physics_ticks_per_second == Sim.TICK_HZ,
		"engine tick rate and Sim.TICK_HZ disagree; see tests/boundary_test.gd"
	)
	RenderingServer.set_default_clear_color(View.BACKGROUND_COLOR)
	_view = View.new()
	add_child(_view)
	get_viewport().size_changed.connect(_fit)
	_fit()


func _fit() -> void:
	_view.frame_arena(get_viewport().get_visible_rect().size)


func _process(_delta: float) -> void:
	# Devices -> intent, once per rendered frame.
	_latched.left.up = _latched.left.up or Input.is_physical_key_pressed(KEY_W)
	_latched.left.down = _latched.left.down or Input.is_physical_key_pressed(KEY_S)
	_latched.right.up = _latched.right.up or Input.is_physical_key_pressed(KEY_UP)
	_latched.right.down = _latched.right.down or Input.is_physical_key_pressed(KEY_DOWN)
	_view.sync(_world)


func _physics_process(_delta: float) -> void:
	# Godot's physics loop IS the fixed timestep: it runs at exactly
	# `physics/common/physics_ticks_per_second` (64, asserted above), accumulates
	# leftover frame time itself, and caps catch-up after a stall via
	# `max_physics_steps_per_frame`. There is deliberately no hand-rolled
	# accumulator in this repo — but note that the TESTS never come through here.
	# They call `Sim.step` directly, because a test that advances time by elapsed
	# seconds is not reproducible.
	Sim.step(_world, _latched)
	_latched = Sim.Intents.new()
