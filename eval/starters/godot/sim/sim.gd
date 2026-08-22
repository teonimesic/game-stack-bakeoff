## Headless, deterministic game simulation.
##
## This script MUST NOT touch rendering, windowing, audio, input devices, or the
## scene tree. Every class here derives from [RefCounted], never [Node], which is
## what lets the whole simulation run under `godot --headless -s` with no scene
## and no GPU. It is the single source of truth for game state.
##
## What is in here now is a PLACEHOLDER, not a game: one [constant Kind.MARKER]
## entity that drifts and reflects off the arena. It exists so the harness has
## something to assert on. Replace it; keep the shape.
##
## Determinism rules enforced here (see AGENTS.md for the why):
## - one tick is one call to [method step]; systems run in declared stage order
## - systems read intent ([Intents]), never [Input] / [InputEvent]
## - no wall clock; time is [member World.tick], never [method Time.get_ticks_msec]
## - order-sensitive iteration sorts on [member Entity.id], never on array order
## - simulation state lives in [Vector2], which is 32-bit; see STATE HASHING
## - randomness comes from [SimRng], which is part of snapshotted state
class_name Sim
extends RefCounted

## Fixed simulation rate. A power of two so `1.0 / TICK_HZ` is exact in binary
## floating point, which matters for reproducible accumulation.
const TICK_HZ: int = 64
## Duration of one tick in seconds. Exact in both f32 and f64 (1/64).
const TICK_DT: float = 1.0 / 64.0

const ARENA_HALF_WIDTH: float = 400.0
const ARENA_HALF_HEIGHT: float = 250.0
const MARKER_HALF_SIZE: float = 12.0
## The marker's speed is an invariant: intent rotates the velocity, never
## lengthens it.
const MARKER_SPEED: float = 220.0
## How hard one tick of intent pulls the velocity vertically, before the
## magnitude is restored to [constant MARKER_SPEED].
const NUDGE_SPEED: float = 300.0

# --------------------------------------------------------------------------
# Identity
# --------------------------------------------------------------------------

## The kinds of thing the world can contain. One, for now.
enum Kind { MARKER }


## One simulated thing.
##
## [member id] is the stable simulation identity. Array position is NOT identity:
## it changes when an entity is removed and is not stable across machines. Never
## sort, serialise, or network on array position. Sort on [member id] instead.
class Entity:
	extends RefCounted
	var id: int
	var kind: Kind
	var position: Vector2
	var velocity: Vector2

	func _init(p_id: int, p_kind: Kind, p_position: Vector2, p_velocity: Vector2) -> void:
		id = p_id
		kind = p_kind
		position = p_position
		velocity = p_velocity


# --------------------------------------------------------------------------
# Intent — the only way input enters the simulation
# --------------------------------------------------------------------------


## Player intent for the current tick.
##
## The simulation reads [b]this[/b], never [method Input.is_key_pressed] or an
## [InputEvent]. Device state is frame-scoped, not tick-scoped: a frame may
## contain 0, 1, or many fixed ticks, so reading it inside a tick drops or
## duplicates inputs. `view/main.gd` translates devices into intent once per
## frame; a server would receive intent over the wire. Both feed the same
## simulation.
##
## Widen this struct as the game needs; it is the seam every input path goes
## through, so a new field is automatically available to replays and to the
## probe.
class Intents:
	extends RefCounted
	var nudge_up: bool
	var nudge_down: bool

	func _init(p_nudge_up: bool = false, p_nudge_down: bool = false) -> void:
		nudge_up = p_nudge_up
		nudge_down = p_nudge_down

	## -1 down, 0 still, +1 up. Opposing inputs cancel.
	func axis() -> float:
		return float(int(nudge_up) - int(nudge_down))


static func no_intents() -> Intents:
	return Intents.new()


# --------------------------------------------------------------------------
# Simulation state
# --------------------------------------------------------------------------


## Presentation-facing events produced by a single tick. Replaced at the start of
## every tick, so a reader sees exactly the events of the tick that just ran.
##
## Deliberately per-tick state rather than a Godot [signal] or a queue: signals
## fire on the frame the emitter runs, and a queue drained on the render frame
## would drop or duplicate against a fixed tick rate.
##
## Two views of the same thing on purpose. Typed counters and payloads are what
## the view and the tests want; [member events] is the flat, machine-readable
## list the probe emits, and every structured event should push a name onto it.
class TickEvents:
	extends RefCounted
	## Reflections off the arena bounds this tick.
	var bounces: int = 0
	## Event names produced this tick, in the order they happened.
	var events: Array[String] = []

	func record(name: String) -> void:
		events.append(name)


## Deterministic PRNG (PCG-XSH-RR 64/32), seeded explicitly and carried in the
## simulation state. Never use [RandomNumberGenerator], [method @GlobalScope.randi],
## or [method @GlobalScope.randomize] in the simulation: they would make replays
## and rollback impossible.
##
## GDScript `int` is a 64-bit [b]signed[/b] integer that wraps on overflow, which
## is exactly the wrapping-u64 arithmetic PCG is defined on — so `*` and `+` need
## no masking. What DOES need care is `>>`: GDScript's is an arithmetic shift and
## sign-extends, while PCG needs a logical shift. That is what [method _lsr] is
## for. Every shift of the 64-bit state goes through it.
class SimRng:
	extends RefCounted
	const MUL: int = 6364136223846793005
	const INC: int = 1442695040888963407

	var _state: int = 0

	static func from_seed(seed: int) -> SimRng:
		var rng := SimRng.new()
		rng.next_u32()
		rng._state += seed
		rng.next_u32()
		return rng

	func clone() -> SimRng:
		var copy := SimRng.new()
		copy._state = _state
		return copy

	## Logical (zero-filling) right shift of a 64-bit pattern held in a signed int.
	static func _lsr(value: int, bits: int) -> int:
		if bits <= 0:
			return value
		return (value >> bits) & ((1 << (64 - bits)) - 1)

	static func _rotr32(value: int, rot: int) -> int:
		var r: int = rot & 31
		if r == 0:
			return value & 0xFFFFFFFF
		return ((value >> r) | (value << (32 - r))) & 0xFFFFFFFF

	func next_u32() -> int:
		var old: int = _state
		_state = old * MUL + INC
		var xorshifted: int = _lsr(_lsr(old, 18) ^ old, 27) & 0xFFFFFFFF
		var rot: int = _lsr(old, 59)
		return _rotr32(xorshifted, rot)

	## Uniform in [0, 1).
	func next_f32() -> float:
		# 24 bits of mantissa, exactly representable, no rounding surprise.
		return float(next_u32() >> 8) / 16777216.0

	## Uniform in [lo, hi).
	func range_f32(lo: float, hi: float) -> float:
		return lo + next_f32() * (hi - lo)

	func coin_flip() -> bool:
		return (next_u32() & 1) == 1


## The whole simulation. Everything needed to reproduce the next tick.
class World:
	extends RefCounted
	var tick: int = 0
	var intents: Intents = Intents.new()
	var events: TickEvents = TickEvents.new()
	var rng: SimRng = SimRng.new()
	var entities: Array[Entity] = []

	## Entities in [member Entity.id] order — iteration that does not depend on
	## array layout or removal history.
	func by_sim_id() -> Array[Entity]:
		var chosen: Array[Entity] = entities.duplicate()
		chosen.sort_custom(func(a: Entity, b: Entity) -> bool: return a.id < b.id)
		return chosen

	## Entities of one kind, in [member Entity.id] order.
	func of_kind(kind: Kind) -> Array[Entity]:
		var chosen: Array[Entity] = []
		for entity: Entity in by_sim_id():
			if entity.kind == kind:
				chosen.append(entity)
		return chosen

	func first_of_kind(kind: Kind) -> Entity:
		var found: Array[Entity] = of_kind(kind)
		return null if found.is_empty() else found[0]


## Deterministic initial world. Ids are assigned explicitly and never derived
## from creation order.
static func spawn_world(seed: int) -> World:
	var world := World.new()
	world.rng = SimRng.from_seed(seed)
	world.entities = [Entity.new(1, Kind.MARKER, Vector2.ZERO, _launch_velocity(world.rng))]
	return world


## Seed-sensitive starting direction: a sign, then a small angle offset. Two
## draws, always in this order — the RNG call sequence is part of the snapshot,
## so reordering or skipping a draw changes every replay.
static func _launch_velocity(rng: SimRng) -> Vector2:
	var toward_right: bool = rng.coin_flip()
	# Keep the launch away from near-vertical so the run is not a straight line
	# between two walls.
	var angle: float = rng.range_f32(-0.5, 0.5)
	var dir := Vector2((1.0 if toward_right else -1.0) * cos(angle), sin(angle))
	return dir * MARKER_SPEED


# --------------------------------------------------------------------------
# Schedule
# --------------------------------------------------------------------------

## Ordered stages of one simulation tick. A total order is the only ordering
## guarantee worth having, and lockstep netcode needs one.
enum Stage { BEGIN, INTENT, MOTION, COLLISION, RESOLVE }

const STAGE_NAMES: Array[String] = ["begin", "intent", "motion", "collision", "resolve"]


class SimSystem:
	extends RefCounted
	var stage: Stage
	var name: String
	var run: Callable

	func _init(p_stage: Stage, p_name: String, p_run: Callable) -> void:
		stage = p_stage
		name = p_name
		run = p_run


## The tick, as data. Systems run top to bottom, always, on every machine.
##
## Add new systems HERE with an explicit stage rather than calling them from
## inside another system — the declared order is what `just test-sim` checks and
## what makes the tick reviewable at a glance.
static var SIM_PIPELINE: Array[SimSystem] = []


static func _static_init() -> void:
	SIM_PIPELINE = [
		SimSystem.new(Stage.BEGIN, "begin_tick", _begin_tick),
		SimSystem.new(Stage.INTENT, "apply_intent", _apply_intent),
		SimSystem.new(Stage.MOTION, "integrate_motion", _integrate_motion),
		SimSystem.new(Stage.COLLISION, "collide_bounds", _collide_bounds),
		SimSystem.new(Stage.RESOLVE, "resolve_outcomes", _resolve_outcomes),
	]


## Advance the world by exactly one tick. The only way time passes.
static func step(world: World, intents: Intents = null) -> void:
	world.intents = no_intents() if intents == null else intents
	for system: SimSystem in SIM_PIPELINE:
		system.run.call(world)


static func _begin_tick(world: World) -> void:
	world.tick += 1
	world.events = TickEvents.new()


static func _apply_intent(world: World) -> void:
	var axis: float = world.intents.axis()
	if is_zero_approx(axis):
		return
	for entity: Entity in world.of_kind(Kind.MARKER):
		var pulled := Vector2(entity.velocity.x, entity.velocity.y + axis * NUDGE_SPEED * TICK_DT)
		# Intent steers, it does not accelerate. Restoring the magnitude keeps
		# speed out of the tuning surface, so a test can assert on direction
		# without also pinning down how fast things go.
		entity.velocity = pulled.normalized() * MARKER_SPEED


static func _integrate_motion(world: World) -> void:
	# Sorting on the sim id makes iteration order independent of storage layout.
	# Integration is per-entity and order-independent today, but sorting keeps it
	# correct if someone later introduces coupling between entities.
	for entity: Entity in world.by_sim_id():
		entity.position += entity.velocity * TICK_DT


static func _collide_bounds(world: World) -> void:
	var limit_x: float = ARENA_HALF_WIDTH - MARKER_HALF_SIZE
	var limit_y: float = ARENA_HALF_HEIGHT - MARKER_HALF_SIZE
	for entity: Entity in world.by_sim_id():
		var position: Vector2 = entity.position
		var velocity: Vector2 = entity.velocity
		var bounced: bool = false

		if position.x > limit_x:
			position.x = limit_x - (position.x - limit_x)
			velocity.x = -velocity.x
			bounced = true
		elif position.x < -limit_x:
			position.x = -limit_x - (position.x + limit_x)
			velocity.x = -velocity.x
			bounced = true

		if position.y > limit_y:
			position.y = limit_y - (position.y - limit_y)
			velocity.y = -velocity.y
			bounced = true
		elif position.y < -limit_y:
			position.y = -limit_y - (position.y + limit_y)
			velocity.y = -velocity.y
			bounced = true

		if bounced:
			# Reflection can only ever move the entity back toward the middle, but
			# clamp anyway: a future rule that teleports or accelerates hard should
			# fail a test, not leak an entity out of the world.
			entity.position = Vector2(
				clampf(position.x, -limit_x, limit_x), clampf(position.y, -limit_y, limit_y)
			)
			entity.velocity = velocity
			world.events.bounces += 1
			world.events.record("bounce")


static func _resolve_outcomes(_world: World) -> void:
	# INTENTIONALLY EMPTY in the starter. This is the stage where a tick decides
	# what its motion and collisions MEANT — a life lost, a level cleared, an
	# entity removed — and it is kept as a declared, empty system so that logic
	# has a named home instead of being wedged into the collision pass.
	pass


# --------------------------------------------------------------------------
# State hashing — the backbone of replay and desync detection
# --------------------------------------------------------------------------

# 0xcbf29ce484222325 and 0x100000001b3. GDScript CANNOT parse a hex literal above
# 2**63 - 1 (it clamps to INT64_MAX and prints an error), so the FNV offset basis
# is written as its signed two's-complement equivalent.
const _FNV_OFFSET: int = -3750763034362895579
const _FNV_PRIME: int = 1099511628211

static var _f32_scratch: PackedByteArray = _make_scratch()


static func _make_scratch() -> PackedByteArray:
	var buffer := PackedByteArray()
	buffer.resize(4)
	return buffer


## The IEEE-754 f32 bit pattern of a value — the equivalent of Rust's
## `f32::to_bits`.
##
## Simulation state lives in [Vector2], whose components are `real_t`, i.e.
## [b]32-bit[/b] in a standard Godot build. A GDScript `float` is 64-bit, so
## reading `entity.position.x` widens an f32 to f64; encoding it back to f32 here
## is exact and round-trips. See AGENTS.md for the one build flag that breaks this.
static func f32_bits(value: float) -> int:
	_f32_scratch.encode_float(0, value)
	return _f32_scratch.decode_u32(0)


## Inverse of [method f32_bits]. Used by the "state stays in f32" test to prove a
## coordinate survives the round trip unchanged.
static func f32_from_bits(bits: int) -> float:
	_f32_scratch.encode_u32(0, bits)
	return _f32_scratch.decode_float(0)


## A whole-world checksum for a single tick.
##
## Floats are hashed via their bit pattern so the hash is exact rather than
## tolerance-based: a replay either reproduces the run bit for bit or it does
## not. Entities are visited in [member Entity.id] order so the hash cannot
## depend on storage layout.
##
## FNV-1a, chosen because it is trivially reimplementable in any language — a
## server or a tool in another stack can verify the same hashes. The result is a
## signed 64-bit int holding a u64 bit pattern; compare it, do not order it.
##
## Everything that decides the next tick belongs in here. State you leave out is
## state a desync can hide in.
static func state_hash(world: World) -> int:
	var hash_value: int = _FNV_OFFSET

	var values: Array[int] = [world.tick]
	for entity: Entity in world.by_sim_id():
		values.append(entity.id)
		values.append(f32_bits(entity.position.x))
		values.append(f32_bits(entity.position.y))
		values.append(f32_bits(entity.velocity.x))
		values.append(f32_bits(entity.velocity.y))

	for value: int in values:
		for byte_index: int in range(8):
			hash_value ^= SimRng._lsr(value, 8 * byte_index) & 0xFF
			hash_value *= _FNV_PRIME
	return hash_value
