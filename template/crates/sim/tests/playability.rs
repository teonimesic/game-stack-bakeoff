//! Playability assertions: the tests that catch "correct but not a game".
//!
//! The documented signature failure of agent-built games is that everything
//! compiles, every unit test passes, and the result is unplayable — zero damage
//! in sixty seconds, or level-ups every 3.9s instead of the intended 10–30s.
//! Correctness tests cannot see that class of defect, because nothing is
//! *wrong*; the numbers are just bad.
//!
//! So these assert on CONSEQUENCES of the tuning constants, not on the
//! constants themselves. Changing `BALL_SPEEDUP` from 1.05 to 1.5 leaves every
//! other test green and breaks this file immediately.
//!
//! Keep the bounds wide. They exist to catch "this is not a game any more", not
//! to freeze the design.

use sim::replay::{Replay, headless_app, run};
use sim::*;

/// Drive both paddles to track the ball perfectly. A skilled-player upper bound:
/// if a rally cannot be sustained under perfect play, it cannot be sustained.
fn perfect_tracking_run(seed: u64, ticks: usize) -> (u32, f32, u32) {
    let mut app = headless_app(seed);
    let (mut hits, mut peak_speed, mut scores) = (0u32, 0f32, 0u32);

    for _ in 0..ticks {
        let (ball_y, ball_speed) = {
            let mut q = app.world_mut().query::<(&Ball, &Position, &Velocity)>();
            match q.iter(app.world()).next() {
                Some((_, p, v)) => (p.0.y, v.0.length()),
                None => (0.0, 0.0),
            }
        };
        peak_speed = peak_speed.max(ball_speed);

        let paddle_ys: Vec<(Side, f32)> = {
            let mut q = app.world_mut().query::<(&Side, &Position)>();
            q.iter(app.world()).map(|(s, p)| (*s, p.0.y)).collect()
        };
        let intent_for = |side: Side| {
            let y = paddle_ys
                .iter()
                .find(|(s, _)| *s == side)
                .map_or(0.0, |(_, y)| *y);
            PlayerIntent {
                up: ball_y > y + 2.0,
                down: ball_y < y - 2.0,
            }
        };
        *app.world_mut().resource_mut::<Intents>() = Intents {
            left: intent_for(Side::Left),
            right: intent_for(Side::Right),
        };

        app.update();
        let ev = app.world().resource::<TickEvents>().clone();
        hits += ev.paddle_hits.len() as u32;
        if ev.scored.is_some() {
            scores += 1;
        }
    }
    (hits, peak_speed, scores)
}

#[test]
fn a_skilled_rally_can_actually_be_sustained() {
    // 30 seconds of perfect play should produce a real rally. If paddles cannot
    // reach the ball, or the ball outruns them immediately, the game is
    // unplayable no matter how correct the physics are.
    let (hits, _, _) = perfect_tracking_run(1, 30 * TICK_HZ as usize);
    assert!(
        hits >= 10,
        "only {hits} paddle hits in 30s of perfect tracking. Either the paddle \
         is too slow to reach the ball or the ball is too fast to return."
    );
}

#[test]
fn ball_speed_stays_within_playable_bounds() {
    let (_, peak, _) = perfect_tracking_run(2, 60 * TICK_HZ as usize);
    assert!(
        peak <= MAX_BALL_SPEED + 1.0,
        "ball reached {peak:.0} u/s, above the {MAX_BALL_SPEED:.0} cap - the \
         clamp is not being applied"
    );
    // NOTE: there is deliberately no "the ball escalates" assertion here.
    // Mutation testing showed peak speed cannot distinguish BALL_SPEEDUP=1.05
    // from 1.00 over 60s - the per-hit deflection term adds more speed than the
    // multiplier does at these constants, so any such assertion passes either
    // way and would give false confidence. If escalation becomes a design
    // requirement, measure it directly (speed sampled at hit N vs hit 1 in a
    // scripted rally), not via observed peak.
    // A ball that crosses the arena in under ~2 fixed ticks is untrackable.
    let ticks_to_cross = (ARENA_HALF_WIDTH * 2.0) / (peak * TICK_DT);
    assert!(
        ticks_to_cross > 8.0,
        "at peak speed the ball crosses the arena in {ticks_to_cross:.1} ticks, \
         which is faster than a player can react"
    );
}

#[test]
fn a_missing_player_concedes_at_a_reasonable_pace() {
    // NOTE: this deliberately does NOT use idle input. Two stationary paddles
    // parked at the centre rally forever, which is correct Pong behaviour, not
    // a defect - measured 25-31 hits and 0 scores over 3000 ticks at every
    // seed. Asserting that idle play scores would be asserting a falsehood.
    //
    // What IS a requirement: when a player stops defending, they concede at a
    // sane rate. Not instantly (the ball is trivially fast) and not never (the
    // ball cannot leave the arena).
    let miss = Intents {
        left: PlayerIntent::default(),
        right: PlayerIntent {
            up: true,
            down: false,
        },
    };
    let outcome = run(&Replay::new(3, vec![miss; 60 * TICK_HZ as usize]));
    let total = outcome.final_score.left + outcome.final_score.right;
    assert!(
        (2..=120).contains(&total),
        "{total} points in 60s while the right player holds up and never \
         defends; expected roughly 2-120. Too few means the ball cannot leave \
         the arena; too many means a round resets almost instantly."
    );
}

#[test]
fn the_ball_never_gets_stuck() {
    // A ball trapped in a corner, or oscillating inside a paddle, passes every
    // correctness test while making the game unplayable.
    let mut app = headless_app(4);
    let mut stalled = 0u32;
    let mut worst = 0u32;
    let mut last = None;

    for _ in 0..(60 * TICK_HZ as usize) {
        app.update();
        let mut q = app.world_mut().query::<(&Ball, &Position)>();
        let pos = q.iter(app.world()).next().map(|(_, p)| p.0);
        if pos == last {
            stalled += 1;
            worst = worst.max(stalled);
        } else {
            stalled = 0;
        }
        last = pos;
    }
    assert!(
        worst < TICK_HZ,
        "the ball held exactly the same position for {worst} consecutive ticks \
         (~{:.1}s). It is stuck.",
        worst as f32 / TICK_HZ as f32
    );
}

#[test]
fn a_point_is_always_reachable() {
    // Guards against a change that makes scoring impossible - e.g. widening the
    // paddles until they seal the goal. Again: driven by a player who is
    // actively out of position, not by idle input.
    let miss = Intents {
        left: PlayerIntent::default(),
        right: PlayerIntent {
            up: true,
            down: false,
        },
    };
    for seed in [10u64, 11, 12] {
        let outcome = run(&Replay::new(seed, vec![miss; 30 * TICK_HZ as usize]));
        assert!(
            outcome.final_score.left + outcome.final_score.right > 0,
            "seed {seed}: nobody scored in 30s even though the right player \
             never defended - scoring may be unreachable"
        );
    }
}
