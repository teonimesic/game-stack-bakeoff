## Playability assertions: the tests that catch "correct but not a game".
##
## The documented signature failure of agent-built games is that everything
## compiles, every unit test passes, and the result is unplayable — zero damage
## in sixty seconds, or level-ups every 3.9s instead of the intended 10-30s.
## Correctness tests cannot see that class of defect, because nothing is
## *wrong*; the numbers are just bad.
##
## So these assert on CONSEQUENCES of the tuning constants, not on the constants
## themselves. Changing `BALL_SPEEDUP` from 1.05 to 1.5 leaves every other test
## green and breaks this file immediately.
##
## Keep the bounds wide. They exist to catch "this is not a game any more", not
## to freeze the design.
class_name PlayabilityTests
extends RefCounted


## Outcome of [method perfect_tracking_run].
class Tracked:
	extends RefCounted
	var hits: int = 0
	var peak_speed: float = 0.0
	var scores: int = 0


## Drive both paddles to track the ball perfectly. A skilled-player upper bound:
## if a rally cannot be sustained under perfect play, it cannot be sustained.
static func perfect_tracking_run(seed: int, ticks: int) -> Tracked:
	var world: Sim.World = Replay.headless_world(seed)
	var result := Tracked.new()

	for i: int in range(ticks):
		var ball: Sim.Entity = world.first_of_kind(Sim.Kind.BALL)
		var ball_y: float = 0.0 if ball == null else ball.position.y
		result.peak_speed = maxf(result.peak_speed, 0.0 if ball == null else ball.velocity.length())

		var intents := Sim.Intents.new()
		for paddle: Sim.Entity in world.of_kind(Sim.Kind.PADDLE):
			var intent := Sim.PlayerIntent.new(
				ball_y > paddle.position.y + 2.0, ball_y < paddle.position.y - 2.0
			)
			if paddle.side == Sim.Side.LEFT:
				intents.left = intent
			else:
				intents.right = intent

		Sim.step(world, intents)
		result.hits += world.events.paddle_hits.size()
		if world.events.scored != Sim.NO_SIDE:
			result.scores += 1
	return result


static func run_all(t: TestRunner) -> void:
	t.run("a skilled rally can actually be sustained", _skilled_rally)
	t.run("ball speed stays within playable bounds", _ball_speed_bounds)
	t.run("a missing player concedes at a reasonable pace", _missing_player)
	t.run("the ball never gets stuck", _never_stuck)
	t.run("a point is always reachable", _point_reachable)


static func _skilled_rally(t: TestRunner) -> void:
	# 30 seconds of perfect play should produce a real rally. If paddles cannot
	# reach the ball, or the ball outruns them immediately, the game is unplayable
	# no matter how correct the physics are.
	var tracked: Tracked = perfect_tracking_run(1, 30 * Sim.TICK_HZ)
	t.ge(
		float(tracked.hits),
		10.0,
		(
			(
				"only %d paddle hits in 30s of perfect tracking. Either the paddle is too "
				+ "slow to reach the ball or the ball is too fast to return."
			)
			% tracked.hits
		)
	)


static func _ball_speed_bounds(t: TestRunner) -> void:
	var tracked: Tracked = perfect_tracking_run(2, 60 * Sim.TICK_HZ)
	t.le(
		tracked.peak_speed,
		Sim.MAX_BALL_SPEED + 1.0,
		(
			"ball reached %.0f u/s, above the %.0f cap — the clamp is not being applied"
			% [tracked.peak_speed, Sim.MAX_BALL_SPEED]
		)
	)
	# NOTE: there is deliberately no "the ball escalates" assertion here.
	# Mutation testing showed peak speed cannot distinguish BALL_SPEEDUP=1.05
	# from 1.00 over 60s — the per-hit deflection term adds more speed than the
	# multiplier does at these constants, so any such assertion passes either way
	# and would give false confidence. If escalation becomes a design
	# requirement, measure it directly (speed sampled at hit N vs hit 1 in a
	# scripted rally), not via observed peak.
	# A ball that crosses the arena in under ~2 fixed ticks is untrackable.
	var ticks_to_cross: float = (Sim.ARENA_HALF_WIDTH * 2.0) / (tracked.peak_speed * Sim.TICK_DT)
	t.gt(
		ticks_to_cross,
		8.0,
		(
			(
				"at peak speed the ball crosses the arena in %.1f ticks, which is faster than "
				+ "a player can react"
			)
			% ticks_to_cross
		)
	)


static func _miss_intents() -> Sim.Intents:
	return Sim.Intents.new(Sim.PlayerIntent.new(false, false), Sim.PlayerIntent.new(true, false))


static func _missing_player(t: TestRunner) -> void:
	# NOTE: this deliberately does NOT use idle input. Two stationary paddles
	# parked at the centre rally forever, which is correct Pong behaviour, not a
	# defect — measured 25-31 hits and 0 scores over 3000 ticks at every seed.
	# Asserting that idle play scores would be asserting a falsehood.
	#
	# What IS a requirement: when a player stops defending, they concede at a sane
	# rate. Not instantly (the ball is trivially fast) and not never (the ball
	# cannot leave the arena).
	var outcome: Replay.Outcome = Replay.run(Replay.held(3, 60 * Sim.TICK_HZ, _miss_intents()))
	var total: int = outcome.final_score_left + outcome.final_score_right
	t.check(
		total >= 2 and total <= 120,
		(
			(
				"%d points in 60s while the right player holds up and never defends; expected "
				+ "roughly 2-120. Too few means the ball cannot leave the arena; too many "
				+ "means a round resets almost instantly."
			)
			% total
		)
	)


static func _never_stuck(t: TestRunner) -> void:
	# A ball trapped in a corner, or oscillating inside a paddle, passes every
	# correctness test while making the game unplayable.
	var world: Sim.World = Replay.headless_world(4)
	var stalled: int = 0
	var worst: int = 0
	var last := Vector2(INF, INF)

	for i: int in range(60 * Sim.TICK_HZ):
		Sim.step(world)
		var ball: Sim.Entity = world.first_of_kind(Sim.Kind.BALL)
		var position: Vector2 = last if ball == null else ball.position
		if position == last:
			stalled += 1
			worst = maxi(worst, stalled)
		else:
			stalled = 0
		last = position

	t.lt(
		float(worst),
		float(Sim.TICK_HZ),
		(
			(
				"the ball held exactly the same position for %d consecutive ticks (~%.1fs). "
				+ "It is stuck."
			)
			% [worst, float(worst) / float(Sim.TICK_HZ)]
		)
	)


static func _point_reachable(t: TestRunner) -> void:
	# Guards against a change that makes scoring impossible — e.g. widening the
	# paddles until they seal the goal. Again: driven by a player who is actively
	# out of position, not by idle input.
	for seed: int in [10, 11, 12]:
		var outcome: Replay.Outcome = Replay.run(
			Replay.held(seed, 30 * Sim.TICK_HZ, _miss_intents())
		)
		t.gt(
			float(outcome.final_score_left + outcome.final_score_right),
			0.0,
			(
				(
					"seed %d: nobody scored in 30s even though the right player never defended "
					+ "— scoring may be unreachable"
				)
				% seed
			)
		)
