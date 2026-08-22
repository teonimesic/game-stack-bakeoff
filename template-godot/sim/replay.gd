## Deterministic replay: the template's most load-bearing test primitive.
##
## A replay is `(seed, per-tick intents)`. Running it produces a per-tick hash
## chain. Two runs of the same replay must produce identical chains; if they do
## not, something in the simulation is order-dependent, clock-dependent, or
## reading unseeded entropy.
##
## This single mechanism catches most determinism regressions, which is why every
## gameplay change should come with a replay test.
class_name Replay
extends RefCounted

## A recorded run: everything needed to reproduce a simulation exactly.
var seed: int
## Intent for each tick, in order. Length determines the run length.
var inputs: Array[Sim.Intents]


func _init(p_seed: int, p_inputs: Array[Sim.Intents]) -> void:
	seed = p_seed
	inputs = p_inputs


func size() -> int:
	return inputs.size()


## A replay with no player input — useful for testing the ball alone.
static func idle(p_seed: int, ticks: int) -> Replay:
	var recorded: Array[Sim.Intents] = []
	for i: int in range(ticks):
		recorded.append(Sim.no_intents())
	return Replay.new(p_seed, recorded)


## Repeat one [Sim.Intents] for every tick of a run.
static func held(p_seed: int, ticks: int, intents: Sim.Intents) -> Replay:
	var recorded: Array[Sim.Intents] = []
	for i: int in range(ticks):
		recorded.append(intents)
	return Replay.new(p_seed, recorded)


## Outcome of running a replay.
class Outcome:
	extends RefCounted
	## World hash after each tick. `hashes[i]` is the state after tick `i + 1`.
	var hashes: PackedInt64Array = PackedInt64Array()
	var final_tick: int = 0
	var final_score_left: int = 0
	var final_score_right: int = 0

	## Hash of the whole run — cheap to compare and to store as a golden value.
	func digest() -> int:
		var acc: int = -3750763034362895579  # 0xcbf29ce484222325
		for h: int in hashes:
			acc = (acc ^ h) * 1099511628211
		return acc


## Build a headless world.
##
## There is nothing to warm up, no scene tree, and no engine loop to drive: the
## invariant is exact by construction — [b]after `headless_world`, one
## `Sim.step()` is one tick.[/b] Tests advance time by calling [method Sim.step],
## never by elapsed seconds and never via `_physics_process`.
static func headless_world(p_seed: int) -> Sim.World:
	return Sim.spawn_world(p_seed)


## Run a replay to completion, hashing the world after every tick.
static func run(replay: Replay) -> Outcome:
	var world: Sim.World = headless_world(replay.seed)
	var outcome := Outcome.new()
	outcome.hashes.resize(replay.size())

	var index: int = 0
	for intents: Sim.Intents in replay.inputs:
		Sim.step(world, intents)
		outcome.hashes[index] = Sim.state_hash(world)
		index += 1

	outcome.final_tick = world.tick
	outcome.final_score_left = world.score.left
	outcome.final_score_right = world.score.right
	return outcome


## Run the same replay twice and return the first tick at which the two runs
## diverge, or -1 if they are identical.
##
## This is the assertion behind `just test-determinism`. It is deliberately
## exact: any divergence at all is a bug, not a tolerance to be widened.
static func find_divergence(replay: Replay) -> int:
	var a: Outcome = run(replay)
	var b: Outcome = run(replay)
	var shared: int = mini(a.hashes.size(), b.hashes.size())
	for tick: int in range(shared):
		if a.hashes[tick] != b.hashes[tick]:
			return tick
	return -1 if a.hashes.size() == b.hashes.size() else shared
