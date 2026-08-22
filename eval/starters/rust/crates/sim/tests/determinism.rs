//! Determinism guarantees. These tests are the starter's backstop: they fail
//! loudly when a change makes the simulation depend on iteration order, wall
//! clock, or unseeded entropy.
//!
//! If one of these fails, DO NOT relax the assertion. An exact hash comparison
//! that becomes an approximate one is worthless. Find the nondeterminism.

use bevy_app::prelude::*;
use bevy_ecs::prelude::With;
use bevy_ecs::schedule::Schedule;
use bevy_ecs::schedule::{LogLevel, ScheduleBuildSettings, Schedules};
use sim::replay::{Replay, find_divergence, headless_app, run};
use sim::{Intents, SimPlugin, Tick};

fn alternating_inputs(ticks: usize) -> Vec<Intents> {
    // A pattern that keeps changing direction, so the hash chain exercises the
    // input path rather than a world left to coast.
    (0..ticks)
        .map(|t| Intents {
            nudge_up: (t / 17) % 2 == 0,
            nudge_down: (t / 23) % 2 == 1,
        })
        .collect()
}

#[test]
fn identical_replays_produce_identical_hash_chains() {
    let replay = Replay::new(0xDEAD_BEEF, alternating_inputs(600));
    assert_eq!(
        find_divergence(&replay),
        None,
        "the same replay produced different state on two runs — the simulation \
         is reading something outside its snapshot (iteration order, wall clock, \
         or unseeded RNG)"
    );
}

#[test]
fn different_seeds_produce_different_runs() {
    // Guards against the opposite failure: a "deterministic" simulation that is
    // actually ignoring its seed would pass every determinism test trivially.
    let a = run(&Replay::idle(1, 400));
    let b = run(&Replay::idle(2, 400));
    assert_ne!(
        a.digest(),
        b.digest(),
        "two different seeds produced identical runs — the seed is not reaching \
         the simulation"
    );
}

#[test]
fn different_inputs_produce_different_runs() {
    let seed = 7;
    let idle = run(&Replay::idle(seed, 400));
    let active = run(&Replay::new(seed, alternating_inputs(400)));
    assert_ne!(
        idle.digest(),
        active.digest(),
        "player intent had no effect on the simulation"
    );
}

#[test]
fn tick_count_is_exactly_the_number_of_updates() {
    // This asserts TimeUpdateStrategy::FixedTimesteps(1) is doing its job. If it
    // regresses, every other determinism test silently becomes time-dependent.
    for ticks in [1usize, 10, 137] {
        let outcome = run(&Replay::idle(3, ticks));
        assert_eq!(
            outcome.final_tick, ticks as u64,
            "expected exactly {ticks} fixed ticks from {ticks} updates"
        );
        assert_eq!(outcome.hashes.len(), ticks);
    }
}

#[test]
fn replay_is_resumable_from_a_prefix() {
    // A replay's first N hashes must not depend on what comes after them.
    // This is what makes rollback and mid-run desync detection possible.
    let inputs = alternating_inputs(500);
    let long = run(&Replay::new(11, inputs.clone()));
    let short = run(&Replay::new(11, inputs[..200].to_vec()));

    assert_eq!(
        &long.hashes[..200],
        &short.hashes[..],
        "a 500-tick run and a 200-tick run diverged within their common prefix"
    );
}

#[test]
fn state_hash_notices_a_single_changed_float_bit() {
    // The hash is only worth having if it is exact. Nudging one position by one
    // ULP is the smallest possible change to the world; it must change the hash.
    let mut app = headless_app(5);
    app.update();
    let before = sim::state_hash(app.world_mut());

    let entity = app
        .world_mut()
        .query_filtered::<bevy_ecs::entity::Entity, With<sim::Marker>>()
        .iter(app.world())
        .next()
        .expect("no marker in the world");
    let mut position = app.world_mut().get_mut::<sim::Position>(entity).unwrap();
    position.0.x = f32::from_bits(position.0.x.to_bits() ^ 1);

    assert_ne!(
        before,
        sim::state_hash(app.world_mut()),
        "changing one bit of one position left `state_hash` unchanged — the \
         hash is not covering the state it claims to, so a desync can go \
         undetected"
    );
}

#[test]
fn simulation_floats_round_trip_exactly() {
    // Every float that leaves the simulation — into a hash, a trace line, a
    // snapshot — must survive the trip. `to_bits` is the exact channel;
    // `{:?}` is the shortest decimal that round-trips and is what `just probe`
    // writes. Both must be lossless, or two machines comparing traces will
    // disagree about a run that never actually diverged.
    let mut app = headless_app(6);
    for _ in 0..200 {
        app.update();
        let mut query = app.world_mut().query::<(&sim::Position, &sim::Velocity)>();
        for (position, velocity) in query.iter(app.world()) {
            for value in [position.0.x, position.0.y, velocity.0.x, velocity.0.y] {
                assert!(value.is_finite(), "simulation produced {value}");
                assert_eq!(f32::from_bits(value.to_bits()), value);
                assert_eq!(
                    format!("{value:?}").parse::<f32>().unwrap(),
                    value,
                    "{value:?} does not parse back to the same f32"
                );
            }
        }
    }
}

#[test]
fn fixed_update_schedule_has_no_ambiguities() {
    // Two systems with conflicting data access and no ordering edge between them
    // race, and the winner decides the result. Bevy ships this check disabled
    // (LogLevel::Ignore), so we assert it here directly.
    //
    // `auto_insert_apply_deferred: false` matters: auto-inserted sync points
    // create incidental ordering that hides genuine ambiguities.
    let mut app = App::new();
    app.add_plugins(bevy_time::TimePlugin)
        .add_plugins(SimPlugin);
    app.finish();
    app.cleanup();

    let mut offenders = Vec::new();
    // Take each schedule out by its concrete label, rebuild it with detection
    // turned up, count conflicts, then put it back.
    let mut audit = |app: &mut App, label: &'static str, schedule: Option<Schedule>| {
        let Some(mut schedule) = schedule else { return };
        schedule.set_build_settings(ScheduleBuildSettings {
            ambiguity_detection: LogLevel::Warn,
            auto_insert_apply_deferred: false,
            use_shortnames: false,
            ..Default::default()
        });
        schedule
            .initialize(app.world_mut())
            .expect("schedule failed to build");
        let conflicts = schedule.graph().conflicting_systems();
        if !conflicts.is_empty() {
            offenders.push(format!("{label}: {} conflicting pair(s)", conflicts.len()));
        }
        app.world_mut().resource_mut::<Schedules>().insert(schedule);
    };

    let fixed = app
        .world_mut()
        .resource_mut::<Schedules>()
        .remove(FixedUpdate);
    audit(&mut app, "FixedUpdate", fixed);

    let update = app.world_mut().resource_mut::<Schedules>().remove(Update);
    audit(&mut app, "Update", update);

    assert!(
        offenders.is_empty(),
        "schedules contain ambiguous system pairs (conflicting access, no \
         ordering edge): {offenders:?}. Add an explicit .before()/.after()/\
         .chain(), or .ambiguous_with() with a comment explaining why the race \
         is genuinely harmless."
    );
}

#[test]
fn headless_app_starts_spawned_and_at_tick_zero() {
    // `headless_app` absorbs Bevy's warm-up update so that the world is spawned
    // and the tick invariant is exact. If this breaks, every replay length in
    // the suite silently shifts by one.
    let mut app = headless_app(0);
    assert_eq!(app.world().resource::<Tick>().0, 0);

    // Counted BY KIND, deliberately, not as a total. A total-entity assertion
    // is a trap: adding any new simulation entity turns this test red for a
    // reason that has nothing to do with what it is testing, and the only way
    // to get green is to edit a determinism test — exactly the habit this suite
    // exists to discourage. Assert the invariants you actually mean.
    let markers = app
        .world_mut()
        .query_filtered::<&sim::SimId, With<sim::Marker>>()
        .iter(app.world())
        .count();
    assert_eq!(markers, 1, "expected exactly one marker after startup");

    // What every simulation entity must satisfy, however many there are:
    // a `SimId`, and a unique one. Duplicated ids silently corrupt `state_hash`
    // and every sort that depends on them.
    let mut ids: Vec<u32> = app
        .world_mut()
        .query::<&sim::SimId>()
        .iter(app.world())
        .map(|id| id.0)
        .collect();
    let total = ids.len();
    ids.sort_unstable();
    ids.dedup();
    assert_eq!(
        ids.len(),
        total,
        "two simulation entities share a SimId. Ids must be unique: they are \
         the sort key for every order-sensitive query and the identity used by \
         `state_hash`."
    );

    app.update();
    assert_eq!(app.world().resource::<Tick>().0, 1, "one update, one tick");
}
