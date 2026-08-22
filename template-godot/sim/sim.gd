## Headless, deterministic game simulation.
##
## This script MUST NOT touch rendering, windowing, audio, input devices, or the
## scene tree. Every class here derives from [RefCounted], never [Node], which is
## what lets the whole simulation run under `godot --headless -s` with no scene
## and no GPU. It is the single source of truth for game state.
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
const PADDLE_HALF_HEIGHT: float = 50.0
const PADDLE_INSET: float = 370.0
const PADDLE_SPEED: float = 300.0
const BALL_RADIUS: float = 8.0
const BALL_START_SPEED: float = 250.0
## Multiplier applied to ball speed on every paddle hit.
const BALL_SPEEDUP: float = 1.05
const MAX_BALL_SPEED: float = 900.0

# --------------------------------------------------------------------------
# Identity
# --------------------------------------------------------------------------

## Which player a paddle belongs to. [constant NO_SIDE] is the "neither" case;
## GDScript has no `Option`, and a nullable int would be a `Variant` that the
## strict-typing warnings reject.
enum Side { LEFT, RIGHT }

const NO_SIDE: int = -1

enum Kind { PADDLE, BALL }


## One simulated thing.
##
## [member id] is the stable simulation identity. Array position is NOT identity:
## it changes when an entity is removed and is not stable across machines. Never
## sort, serialise, or network on array position. Sort on [member id] instead.
class Entity:
	extends RefCounted
	var id: int
	var kind: Kind
	## Meaningful only when [member kind] is [constant Kind.PADDLE]; otherwise
	## [constant NO_SIDE].
	var side: int
	var position: Vector2
	var velocity: Vector2

	func _init(
		p_id: int, p_kind: Kind, p_side: int, p_position: Vector2, p_velocity: Vector2
	) -> void:
		id = p_id
		kind = p_kind
		side = p_side
		position = p_position
		velocity = p_velocity


# --------------------------------------------------------------------------
# Intent — the only way input enters the simulation
# --------------------------------------------------------------------------


## Per-player intent for the current tick.
##
## The simulation reads [b]this[/b], never [method Input.is_key_pressed] or an
## [InputEvent]. Device state is frame-scoped, not tick-scoped: a frame may
## contain 0, 1, or many fixed ticks, so reading it inside a tick drops or
## duplicates inputs. `view/main.gd` translates devices into intent once per
## frame; a server would receive intent over the wire. Both feed the same
## simulation.
class PlayerIntent:
	extends RefCounted
	var up: bool
	var down: bool

	func _init(p_up: bool = false, p_down: bool = false) -> void:
		up = p_up
		down = p_down

	## -1 down, 0 still, +1 up. Opposing inputs cancel.
	func axis() -> float:
		return float(int(up) - int(down))


## Intent for both players this tick.
class Intents:
	extends RefCounted
	var left: PlayerIntent
	var right: PlayerIntent

	func _init(p_left: PlayerIntent = null, p_right: PlayerIntent = null) -> void:
		left = PlayerIntent.new() if p_left == null else p_left
		right = PlayerIntent.new() if p_right == null else p_right


static func no_intents() -> Intents:
	return Intents.new()


# --------------------------------------------------------------------------
# Simulation state
# --------------------------------------------------------------------------


class Score:
	extends RefCounted
	var left: int = 0
	var right: int = 0


## Presentation-facing events produced by a single tick. Replaced at the start of
## every tick, so a reader sees exactly the events of the tick that just ran.
##
## Deliberately per-tick state rather than a Godot [signal] or a queue: signals
## fire on the frame the emitter runs, and a queue drained on the render frame
## would drop or duplicate against a fixed tick rate.
class TickEvents:
	extends RefCounted
	## One [enum Side] per deflection this tick.
	var paddle_hits: Array[int] = []
	var wall_bounces: int = 0
	## The scoring [enum Side], or [constant NO_SIDE] if nobody scored.
	var scored: int = NO_SIDE


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
	var score: Score = Score.new()
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
	world.entities = [
		Entity.new(1, Kind.PADDLE, Side.LEFT, Vector2(-PADDLE_INSET, 0.0), Vector2.ZERO),
		Entity.new(2, Kind.PADDLE, Side.RIGHT, Vector2(PADDLE_INSET, 0.0), Vector2.ZERO),
		Entity.new(3, Kind.BALL, NO_SIDE, Vector2.ZERO, _serve_velocity(world.rng)),
	]
	return world


static func _serve_velocity(rng: SimRng) -> Vector2:
	var toward_right: bool = rng.coin_flip()
	# Keep the serve away from near-vertical so rallies actually start.
	var angle: float = rng.range_f32(-0.5, 0.5)
	var dir := Vector2((1.0 if toward_right else -1.0) * cos(angle), sin(angle))
	return dir * BALL_START_SPEED


# --------------------------------------------------------------------------
# Schedule
# --------------------------------------------------------------------------

## Ordered stages of one simulation tick. A total order is the only ordering
## guarantee worth having, and lockstep netcode needs one.
enum Stage { BEGIN, INTENT, MOTION, COLLISION, SCORING }

const STAGE_NAMES: Array[String] = ["begin", "intent", "motion", "collision", "scoring"]


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
		SimSystem.new(Stage.COLLISION, "collide_walls", _collide_walls),
		SimSystem.new(Stage.COLLISION, "collide_paddles", _collide_paddles),
		SimSystem.new(Stage.SCORING, "score_and_reset", _score_and_reset),
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
	for paddle: Entity in world.of_kind(Kind.PADDLE):
		var intent: PlayerIntent = (
			world.intents.left if paddle.side == Side.LEFT else world.intents.right
		)
		paddle.velocity = Vector2(0.0, intent.axis() * PADDLE_SPEED)


static func _integrate_motion(world: World) -> void:
	# Sorting on the sim id makes iteration order independent of storage layout.
	# Integration is per-entity and order-independent today, but sorting keeps it
	# correct if someone later introduces coupling between entities.
	for entity: Entity in world.by_sim_id():
		entity.position += entity.velocity * TICK_DT


static func _collide_walls(world: World) -> void:
	for entity: Entity in world.by_sim_id():
		if entity.kind == Kind.PADDLE:
			# Paddles clamp against the arena and stop dead.
			var limit: float = ARENA_HALF_HEIGHT - PADDLE_HALF_HEIGHT
			if entity.position.y > limit:
				entity.position = Vector2(entity.position.x, limit)
				entity.velocity = Vector2(entity.velocity.x, 0.0)
			elif entity.position.y < -limit:
				entity.position = Vector2(entity.position.x, -limit)
				entity.velocity = Vector2(entity.velocity.x, 0.0)
		elif entity.kind == Kind.BALL:
			var limit: float = ARENA_HALF_HEIGHT - BALL_RADIUS
			if entity.position.y > limit:
				entity.position = Vector2(entity.position.x, limit - (entity.position.y - limit))
				entity.velocity = Vector2(entity.velocity.x, -entity.velocity.y)
				world.events.wall_bounces += 1
			elif entity.position.y < -limit:
				entity.position = Vector2(entity.position.x, -limit - (entity.position.y + limit))
				entity.velocity = Vector2(entity.velocity.x, -entity.velocity.y)
				world.events.wall_bounces += 1


static func _collide_paddles(world: World) -> void:
	# Deterministic paddle order: without this, two paddles that could both claim
	# the ball on the same tick would resolve in storage order.
	var paddles: Array[Entity] = world.of_kind(Kind.PADDLE)

	for ball: Entity in world.of_kind(Kind.BALL):
		for paddle: Entity in paddles:
			var face_x: float = (
				paddle.position.x + BALL_RADIUS
				if paddle.side == Side.LEFT
				else paddle.position.x - BALL_RADIUS
			)
			var moving_into: bool = (
				ball.velocity.x < 0.0 and ball.position.x <= face_x
				if paddle.side == Side.LEFT
				else ball.velocity.x > 0.0 and ball.position.x >= face_x
			)
			var vertically_overlapping: bool = (
				absf(ball.position.y - paddle.position.y) <= PADDLE_HALF_HEIGHT + BALL_RADIUS
			)

			if moving_into and vertically_overlapping:
				ball.position = Vector2(face_x, ball.position.y)
				# Deflection angle depends on where the ball struck the paddle.
				var offset: float = (ball.position.y - paddle.position.y) / PADDLE_HALF_HEIGHT
				var deflected := Vector2(
					-ball.velocity.x, ball.velocity.y + offset * BALL_START_SPEED * 0.5
				)
				ball.velocity = (deflected * BALL_SPEEDUP).limit_length(MAX_BALL_SPEED)
				world.events.paddle_hits.append(paddle.side)
				break


static func _score_and_reset(world: World) -> void:
	for ball: Entity in world.of_kind(Kind.BALL):
		var scorer: int = NO_SIDE
		if ball.position.x > ARENA_HALF_WIDTH:
			scorer = Side.LEFT
		elif ball.position.x < -ARENA_HALF_WIDTH:
			scorer = Side.RIGHT

		if scorer != NO_SIDE:
			if scorer == Side.LEFT:
				world.score.left += 1
			else:
				world.score.right += 1
			world.events.scored = scorer
			ball.position = Vector2.ZERO
			ball.velocity = _serve_velocity(world.rng)


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
static func state_hash(world: World) -> int:
	var hash_value: int = _FNV_OFFSET

	var values: Array[int] = [world.tick, world.score.left, world.score.right]
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
