//! Invariants: the tests that catch "correct but not a game".
//!
//! The documented signature failure of agent-built games is that everything
//! compiles, every unit test passes, and the result is unplayable — zero damage
//! in sixty seconds, or level-ups every 3.9s instead of the intended 10–30s.
//! Correctness tests cannot see that class of defect, because nothing is
//! *wrong*; the numbers are just bad.
//!
//! So these assert on CONSEQUENCES measured over a run — where things end up,
//! how often something happens, whether input changes the outcome — never on
//! the tuning constants themselves. A constant you changed will always equal
//! itself; that assertion proves nothing.
//!
//! Keep the bounds wide. They exist to catch "this is not a game any more", not
//! to freeze the design.

use bevy_math::Vec2;
use sim::replay::headless_app;
use sim::*;

/// Run `ticks` ticks with a fixed input held, and report where the marker ended
/// up, how many events fired, and the worst speed error seen along the way.
fn measure(seed: u64, ticks: usize, input: impl Fn(usize) -> Intents) -> Measured {
    let mut app = headless_app(seed);
    let mut report = Measured::default();

    for tick in 0..ticks {
        *app.world_mut().resource_mut::<Intents>() = input(tick);
        app.update();

        report.events += app.world().resource::<TickEvents>().events.len();

        let mut query = app.world_mut().query::<(&Marker, &Position, &Velocity)>();
        let (_, position, velocity) = query
            .iter(app.world())
            .next()
            .expect("no marker in the world");
        report.final_position = position.0;
        report.worst_x = report.worst_x.max(position.0.x.abs());
        report.worst_y = report.worst_y.max(position.0.y.abs());
        report.worst_speed_error = report
            .worst_speed_error
            .max((velocity.0.length() - MARKER_SPEED).abs());
    }
    report
}

#[derive(Default)]
struct Measured {
    final_position: Vec2,
    events: usize,
    worst_x: f32,
    worst_y: f32,
    worst_speed_error: f32,
}

fn idle(_: usize) -> Intents {
    Intents::default()
}

#[test]
fn the_marker_never_leaves_the_arena() {
    // A body that can tunnel out of the world passes every correctness test and
    // makes the game unplayable the moment it happens.
    let report = measure(1, 3000, idle);
    assert!(
        report.worst_x <= ARENA_HALF_WIDTH && report.worst_y <= ARENA_HALF_HEIGHT,
        "over 3000 ticks the marker reached |x|={:.1}, |y|={:.1}, outside the \
         {ARENA_HALF_WIDTH}x{ARENA_HALF_HEIGHT} arena. Collision is letting it \
         escape.",
        report.worst_x,
        report.worst_y,
    );
}

#[test]
fn something_happens_without_any_input() {
    // A world that is silent when left alone is a world where nothing is
    // running. Assert that events actually fire, not that a constant is set.
    let report = measure(2, 3000, idle);
    assert!(
        report.events > 0,
        "3000 ticks of idle simulation produced no events at all — nothing in \
         the world is interacting with anything else"
    );
}

#[test]
fn input_changes_where_things_end_up() {
    // Relational, and the cheapest end-to-end proof that intent reaches state:
    // the same seed, the same tick count, one held input, a different outcome
    // in the direction that input names.
    let ticks = 120;
    let still = measure(3, ticks, idle);
    let nudged = measure(3, ticks, |_| Intents {
        nudge_up: true,
        nudge_down: false,
    });
    assert!(
        nudged.final_position.y > still.final_position.y,
        "holding `nudge_up` for {ticks} ticks left the marker at y={:.2}, no \
         higher than the y={:.2} it reaches with no input at all",
        nudged.final_position.y,
        still.final_position.y,
    );
}

#[test]
fn speed_is_invariant_under_input() {
    // The marker steers, it does not accelerate. If input can make it faster or
    // slower, every tuning number downstream of speed becomes a lottery.
    let report = measure(4, 600, |tick| Intents {
        nudge_up: tick % 4 == 0,
        nudge_down: tick % 4 == 2,
    });
    let budget = MARKER_SPEED * 0.01;
    assert!(
        report.worst_speed_error <= budget,
        "speed drifted {:.3} u/s away from {MARKER_SPEED} while input was \
         applied on half the ticks; the budget is 1% ({budget:.2} u/s)",
        report.worst_speed_error,
    );
}
