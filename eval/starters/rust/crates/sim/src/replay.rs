//! Deterministic replay: the template's most load-bearing test primitive.
//!
//! A replay is `(seed, per-tick intents)`. Running it produces a per-tick hash
//! chain. Two runs of the same replay must produce identical chains; if they do
//! not, something in the simulation is order-dependent, clock-dependent, or
//! reading unseeded entropy.
//!
//! This single mechanism catches most determinism regressions, which is why
//! every gameplay change should come with a replay test.

use bevy_app::prelude::*;
use bevy_time::{Fixed, Time, TimePlugin, TimeUpdateStrategy};

use crate::{Intents, SimPlugin, SimRng, TICK_HZ, Tick, state_hash};

/// A recorded run: everything needed to reproduce a simulation exactly.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Replay {
    pub seed: u64,
    /// Intent for each tick, in order. Length determines the run length.
    pub inputs: Vec<Intents>,
}

impl Replay {
    pub fn new(seed: u64, inputs: Vec<Intents>) -> Self {
        Self { seed, inputs }
    }

    /// A replay with no player input — the world left to its own devices.
    pub fn idle(seed: u64, ticks: usize) -> Self {
        Self::new(seed, vec![Intents::default(); ticks])
    }

    pub fn len(&self) -> usize {
        self.inputs.len()
    }

    pub fn is_empty(&self) -> bool {
        self.inputs.is_empty()
    }
}

/// Outcome of running a replay.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct ReplayOutcome {
    /// World hash after each tick. `hashes[i]` is the state after tick `i + 1`.
    pub hashes: Vec<u64>,
    pub final_tick: u64,
}

impl ReplayOutcome {
    /// Hash of the whole run — cheap to compare and to store as a golden value.
    pub fn digest(&self) -> u64 {
        const PRIME: u64 = 0x0000_0100_0000_01b3;
        self.hashes.iter().fold(0xcbf2_9ce4_8422_2325, |acc, h| {
            (acc ^ h).wrapping_mul(PRIME)
        })
    }
}

/// Build a headless simulation `App`.
///
/// Deliberately **not** `MinimalPlugins`: this crate does not depend on
/// `bevy_internal` at all, so there is no way to accidentally pull in a
/// renderer. `TimePlugin` is required because it drives the `FixedUpdate` loop.
///
/// `TimeUpdateStrategy::FixedTimesteps(1)` is the key line — it makes each
/// `App::update()` run the fixed loop **exactly once**, so tick count is a pure
/// function of how many times we call update. Without it the number of fixed
/// steps per update depends on wall-clock time and nothing is reproducible.
pub fn headless_app(seed: u64) -> App {
    let mut app = App::new();
    app.add_plugins(TimePlugin)
        .add_plugins(SimPlugin)
        .insert_resource(Time::<Fixed>::from_hz(f64::from(TICK_HZ)))
        .insert_resource(TimeUpdateStrategy::FixedTimesteps(1))
        .insert_resource(SimRng::from_seed(seed));
    app.finish();
    app.cleanup();

    // Warm-up update. Measured behaviour of `FixedTimesteps(1)` on Bevy 0.19:
    // the first `update()` runs Startup but advances the fixed loop ZERO times,
    // because the virtual clock has no delta to accumulate yet. Every update
    // after that runs exactly one fixed tick.
    //
    // Absorbing that here buys two things: the world is fully spawned before the
    // caller touches it, and the invariant becomes exact and easy to reason
    // about — **after `headless_app`, one `update()` == one tick.**
    app.update();
    debug_assert_eq!(
        app.world().resource::<Tick>().0,
        0,
        "warm-up update should not have advanced the simulation"
    );
    app
}

/// Run a replay to completion, hashing the world after every tick.
pub fn run(replay: &Replay) -> ReplayOutcome {
    let mut app = headless_app(replay.seed);
    let mut hashes = Vec::with_capacity(replay.len());

    for intents in &replay.inputs {
        *app.world_mut().resource_mut::<Intents>() = *intents;
        app.update();
        hashes.push(state_hash(app.world_mut()));
    }

    ReplayOutcome {
        hashes,
        final_tick: app.world().resource::<Tick>().0,
    }
}

/// Run the same replay twice and return the first tick at which the two runs
/// diverge, or `None` if they are identical.
///
/// This is the assertion behind `just test-determinism`. It is deliberately
/// exact: any divergence at all is a bug, not a tolerance to be widened.
pub fn find_divergence(replay: &Replay) -> Option<usize> {
    let a = run(replay);
    let b = run(replay);
    a.hashes
        .iter()
        .zip(b.hashes.iter())
        .position(|(x, y)| x != y)
}
