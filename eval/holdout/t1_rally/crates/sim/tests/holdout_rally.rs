//! HELD-OUT. The agent never sees this file.
//!
//! Grades the rally-counter task by mirroring the expected value from
//! TickEvents, which already existed, and comparing tick by tick.

use sim::replay::headless_app;
use sim::{Intents, PlayerIntent, RallyLength, TickEvents};

/// Drive the RIGHT paddle to the top of the arena so it misses the ball,
/// guaranteeing a point is conceded. Do NOT rely on idle play to score: on the
/// pristine template two centred paddles rally forever, so an idle replay
/// exercises the increment path but never the reset path.
fn miss_on_the_right() -> Intents {
    Intents {
        left: PlayerIntent::default(),
        right: PlayerIntent { up: true, down: false },
    }
}

#[test]
fn rally_length_tracks_paddle_hits_and_resets_on_score() {
    let mut app = headless_app(42);
    assert_eq!(
        app.world().resource::<RallyLength>().0,
        0,
        "rally length should start at zero"
    );

    let mut expected: u32 = 0;
    let mut max_seen: u32 = 0;
    let mut resets = 0;

    for tick in 1..=3000u32 {
        // Force the right paddle out of the way so points actually get scored.
        *app.world_mut().resource_mut::<Intents>() = miss_on_the_right();
        app.update();
        let events = app.world().resource::<TickEvents>().clone();
        if events.scored.is_some() {
            expected = 0;
            resets += 1;
        } else {
            expected += events.paddle_hits.len() as u32;
        }
        max_seen = max_seen.max(expected);

        let actual = app.world().resource::<RallyLength>().0;
        assert_eq!(
            actual, expected,
            "tick {tick}: RallyLength was {actual}, expected {expected} \
             (hits this tick: {}, scored: {:?})",
            events.paddle_hits.len(),
            events.scored
        );
    }

    assert!(
        max_seen > 0,
        "the replay never produced a paddle hit, so a constant zero would pass; \
         this test is not measuring anything"
    );
    assert!(resets > 0, "the replay never produced a score, so the reset path was never exercised");
}

#[test]
fn rally_length_is_part_of_the_simulation_snapshot() {
    // Two runs of the same seed must agree on rally length at every tick,
    // which they cannot if it is derived from anything outside the sim.
    let mut a = headless_app(7);
    let mut b = headless_app(7);
    for tick in 1..=500u32 {
        *a.world_mut().resource_mut::<Intents>() = miss_on_the_right();
        *b.world_mut().resource_mut::<Intents>() = miss_on_the_right();
        a.update();
        b.update();
        assert_eq!(
            a.world().resource::<RallyLength>().0,
            b.world().resource::<RallyLength>().0,
            "tick {tick}: two runs of seed 7 disagreed on RallyLength"
        );
    }
}
