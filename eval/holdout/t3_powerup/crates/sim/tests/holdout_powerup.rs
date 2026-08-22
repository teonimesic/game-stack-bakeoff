//! HELD-OUT. The agent never sees this file.
//!
//! This task is a determinism trap. The obvious implementation reaches for
//! `rand::thread_rng` or a wall clock, both of which pass a casual eyeball test
//! and fail here.

use bevy_math::Vec2;
use sim::replay::headless_app;
use sim::{Powerup, Position};

fn powerup_positions(seed: u64, ticks: u32) -> Vec<Option<Vec2>> {
    let mut app = headless_app(seed);
    let mut out = Vec::with_capacity(ticks as usize);
    for _ in 0..ticks {
        app.update();
        let mut q = app.world_mut().query::<(&Powerup, &Position)>();
        let mut found: Vec<Vec2> = q.iter(app.world()).map(|(_, p)| p.0).collect();
        found.sort_by(|a, b| a.x.total_cmp(&b.x).then(a.y.total_cmp(&b.y)));
        out.push(found.first().copied());
    }
    out
}

#[test]
fn powerup_exists_and_moves_over_time() {
    let seen = powerup_positions(3, 900);
    let present = seen.iter().filter(|p| p.is_some()).count();
    assert!(
        present > 0,
        "no entity with a Powerup component ever existed during 900 ticks"
    );

    let distinct: std::collections::BTreeSet<(u32, u32)> = seen
        .iter()
        .flatten()
        .map(|v| (v.x.to_bits(), v.y.to_bits()))
        .collect();
    assert!(
        distinct.len() > 1,
        "the powerup never changed position in 900 ticks - it is supposed to \
         respawn somewhere new periodically"
    );
}

#[test]
fn powerup_placement_is_deterministic_for_a_seed() {
    // The trap. thread_rng, SystemTime, or HashMap iteration order all fail here
    // while looking perfectly reasonable in review.
    let a = powerup_positions(11, 900);
    let b = powerup_positions(11, 900);
    let first_diff = a.iter().zip(b.iter()).position(|(x, y)| x != y);
    assert_eq!(
        first_diff, None,
        "two runs with seed 11 disagreed about the powerup position at tick {:?}. \
         The placement is reading entropy from outside the simulation snapshot.",
        first_diff
    );
}

#[test]
fn powerup_placement_actually_depends_on_the_seed() {
    // Guards the opposite failure: a hardcoded position is trivially
    // deterministic and would pass the test above.
    let a = powerup_positions(1, 900);
    let b = powerup_positions(2, 900);
    assert_ne!(
        a, b,
        "seeds 1 and 2 produced identical powerup positions - the placement is \
         not actually random, or it ignores the simulation RNG"
    );
}

#[test]
fn powerup_stays_inside_the_arena() {
    for seed in [5u64, 6, 7] {
        for pos in powerup_positions(seed, 600).into_iter().flatten() {
            assert!(
                pos.x.abs() <= sim::ARENA_HALF_WIDTH && pos.y.abs() <= sim::ARENA_HALF_HEIGHT,
                "powerup spawned outside the arena at {pos:?} (seed {seed})"
            );
        }
    }
}
