## Particle bursts — Godot's own GPU particle system, wired so the capture path
## can actually see it.
##
## Godot is the only one of this project's four stacks that ships a particle
## system at all ([GPUParticles2D], [GPUParticles3D], [CPUParticles2D],
## [CPUParticles3D] are all in the engine). This file exists so that using it
## costs one call instead of a turn spent discovering the two traps below.
##
## It is scaffolding, not gameplay: nothing here decides when anything bursts.
## The starter's [View] never calls it. Deciding what a burst MEANS — a line
## cleared, an enemy killed, a landing — is the game, and that is yours.
##
## [b]THE ONE RULE: a burst is a pure function of simulation state.[/b]
##
## [method RenderTests.capture_frame] — which `just film` reuses verbatim —
## builds a FRESH [View], steps the simulation to tick N with no view attached,
## and syncs once. The view never sees ticks 1..N-1. So presentation state that
## accumulates frame by frame (an emitter you started when an event fired, a
## tween, a screen shake) is [b]structurally invisible[/b] to every filmed frame
## and every rendering test, with nothing red to say so. It is the same trap as
## "everything the player sees goes under the view", on the time axis instead of
## the tree axis.
##
## The way through is to derive the burst from state the simulation still holds
## at tick N — keep the tick a thing happened on, and pass the age:
##
## [codeblock]
## var bursts: Array[Fx.Burst] = []
## for entity: Sim.Entity in world.by_sim_id():
##     if entity.exploded_at_tick >= 0:
##         var age: float = float(world.tick - entity.exploded_at_tick) * Sim.TICK_DT
##         if age <= Fx.LIFETIME:
##             bursts.append(Fx.Burst.new(entity.position, Color.ORANGE, age, entity.id))
## fx.show_bursts(bursts)
## [/codeblock]
##
## [b]The second trap: particles are wall-clock animated, and the render tests
## assert byte equality.[/b] A [GPUParticles2D] left to its own devices advances
## by the frame delta, so two identical captures disagree and
## `rendering is reproducible across runs` goes red for a reason that looks like
## a GPU bug. Every emitter here therefore runs with [member
## GPUParticles2D.speed_scale] at zero, [member GPUParticles2D.interpolate] and
## [member GPUParticles2D.fract_delta] off, and a fixed seed; the only thing that
## advances one is [member GPUParticles2D.preprocess], set from the age you pass.
## Frame rate cannot reach it.
class_name Fx
extends Node2D

## Seconds a particle lives. A burst older than this shows nothing, so it is also
## the cutoff for "is this burst still worth drawing".
const LIFETIME: float = 0.45

## Bursts drawable at once. Past this, [method show_bursts] draws the first
## [constant SLOTS] and drops the rest — deliberately, and in the order you
## passed them, so the frame stays a function of the state you sorted.
const SLOTS: int = 8

## Particles per burst.
const AMOUNT: int = 24

## The particle simulation's own step rate. Nothing to do with the display: with
## [member GPUParticles2D.speed_scale] at zero these steps only ever happen
## inside [member GPUParticles2D.preprocess].
const PROCESS_HZ: int = 60

## Particle size in world units, at spawn.
const PARTICLE_SIZE: float = 6.0

## How fast particles leave the burst, world units per second.
const SPEED_MIN: float = 40.0
const SPEED_MAX: float = 180.0

## World units per second squared, pulling particles the way the arena calls
## down. [View] carries a negative Y scale, so this is expressed in arena space.
const GRAVITY: Vector3 = Vector3(0.0, -220.0, 0.0)


## One burst to draw: where it is, what colour, and how long ago it started.
##
## [param p_id] is what keeps a burst looking like itself. Every emitter is
## seeded from it, so pass something stable — the sim id of whatever spawned the
## burst is ideal. Two bursts sharing an id look identical, which is fine; a
## burst whose id changes between frames visibly re-rolls, which is not.
class Burst:
	extends RefCounted
	var at: Vector2
	var color: Color
	var age: float
	var id: int

	func _init(p_at: Vector2, p_color: Color, p_age: float, p_id: int = 0) -> void:
		at = p_at
		color = p_color
		age = p_age
		id = p_id


## The emitter pool, built on first use. A starter that never bursts pays
## nothing for this file — no nodes, no materials, no texture, and no time in
## `just film`.
var _pool: Array[GPUParticles2D] = []
var _dot: ImageTexture = null


## Draw exactly these bursts, and nothing else.
##
## Stateless by design: whatever was on screen last call is gone unless it is in
## [param bursts] again. Call it once per [method View.sync], every sync,
## including with an empty array.
func show_bursts(bursts: Array[Burst]) -> void:
	if _pool.is_empty() and bursts.is_empty():
		return
	_build_pool()
	for slot: int in range(SLOTS):
		var emitter: GPUParticles2D = _pool[slot]
		if slot >= bursts.size():
			emitter.visible = false
			emitter.emitting = false
			continue
		var burst: Burst = bursts[slot]
		var age: float = clampf(burst.age, 0.0, LIFETIME)
		emitter.visible = true
		emitter.position = burst.at
		emitter.seed = absi(burst.id)
		var material: ParticleProcessMaterial = emitter.process_material
		material.color = burst.color
		# `preprocess` is applied when the system (re)starts, so it has to be set
		# BEFORE the restart, not after.
		emitter.preprocess = age
		emitter.restart()


## Create [constant SLOTS] emitters configured for deterministic one-shot bursts.
##
## Everything here is code rather than a `.tscn` on purpose: a scene file cannot
## be reviewed in a diff, and this template ships no editor.
func _build_pool() -> void:
	if not _pool.is_empty():
		return
	_dot = _make_dot()
	for slot: int in range(SLOTS):
		var emitter := GPUParticles2D.new()
		emitter.texture = _dot
		emitter.amount = AMOUNT
		emitter.lifetime = LIFETIME
		emitter.one_shot = true
		# Every particle leaves at t=0, which is what makes it a burst rather
		# than a stream.
		emitter.explosiveness = 1.0
		# THE DETERMINISM BLOCK. Read `speed_scale = 0` as "wall time cannot
		# reach this node"; the other three keep the same age producing the same
		# pixels on every machine and at every frame rate.
		emitter.speed_scale = 0.0
		emitter.interpolate = false
		emitter.fract_delta = false
		emitter.fixed_fps = PROCESS_HZ
		emitter.use_fixed_seed = true
		emitter.local_coords = true
		# Generous: particles travel in arena units, and the default rect is
		# small enough to cull a burst that is still on screen.
		emitter.visibility_rect = Rect2(-512.0, -512.0, 1024.0, 1024.0)
		emitter.process_material = _make_material()
		emitter.visible = false
		emitter.emitting = false
		add_child(emitter)
		_pool.append(emitter)


## The per-emitter process material. One each, not shared: [member
## ParticleProcessMaterial.color] is what gives a burst its colour, and a shared
## material would give every burst on screen the colour of the last one set.
func _make_material() -> ParticleProcessMaterial:
	var material := ParticleProcessMaterial.new()
	material.emission_shape = ParticleProcessMaterial.EMISSION_SHAPE_SPHERE
	material.emission_sphere_radius = 2.0
	material.particle_flag_disable_z = true
	material.direction = Vector3(0.0, 1.0, 0.0)
	material.spread = 180.0
	material.initial_velocity_min = SPEED_MIN
	material.initial_velocity_max = SPEED_MAX
	material.gravity = GRAVITY
	material.scale_min = 0.6
	material.scale_max = 1.0
	material.damping_min = 20.0
	material.damping_max = 60.0
	return material


## A soft round dot, generated rather than shipped: this template carries no
## assets, and an 8x8 image costs less than an import step.
func _make_dot() -> ImageTexture:
	var size: int = 8
	var image := Image.create_empty(size, size, false, Image.FORMAT_RGBA8)
	var centre: float = float(size - 1) * 0.5
	var radius: float = float(size) * 0.5
	for y: int in range(size):
		for x: int in range(size):
			var distance: float = Vector2(float(x) - centre, float(y) - centre).length()
			var alpha: float = clampf(1.0 - distance / radius, 0.0, 1.0)
			image.set_pixel(x, y, Color(1.0, 1.0, 1.0, alpha))
	var texture := ImageTexture.create_from_image(image)
	# The dot is authored in pixels; PARTICLE_SIZE says how big it is in the
	# arena, which is what a caller actually reasons about.
	texture.set_size_override(Vector2i(roundi(PARTICLE_SIZE), roundi(PARTICLE_SIZE)))
	return texture
