//! Headless, deterministic game simulation.
//!
//! This crate MUST NOT depend on rendering, windowing, audio, or input devices.
//! It is the single source of truth for game state and is fully testable with no
//! GPU and no window.
//!
//! What is here now is a **placeholder**, not a game: a single [`Marker`] that
//! drifts around the arena and reflects off the walls. It exists so the harness
//! has something to assert on. Replace it with the real game; keep the shape.
//!
//! Determinism rules, and what enforces each of them:
//! - all simulation runs in [`SimSet`] inside `FixedUpdate`, `.chain()`ed
//!   — `tests/determinism.rs::fixed_update_schedule_has_no_ambiguities`
//! - systems read intent ([`Intents`]), never raw input devices
//!   — `tests/boundary.rs` (no input crate is reachable from here)
//! - no wall-clock reads; tick count comes from [`Tick`]
//!   — `clippy.toml` bans `Instant`/`SystemTime`; `tests/boundary.rs` bans
//!   the crates that would smuggle one in
//! - order-sensitive queries sort on [`SimId`], never on `Entity`
//!   — `clippy.toml` bans `HashMap`/`HashSet`; replay tests catch the rest
//! - randomness comes from [`SimRng`], which is part of snapshotted state
//!   — `tests/boundary.rs` bans `rand`, `getrandom` and friends
//! - transcendentals go through `bevy_math::ops` (libm), never `f32::sin`
//!   — `clippy.toml` bans the std methods, `tests/boundary.rs` asserts the
//!   `glam/libm` feature is on and `glam/fast-math` is off

use bevy_app::prelude::*;
use bevy_ecs::prelude::*;
use bevy_ecs::schedule::{LogLevel, ScheduleBuildSettings};
use bevy_math::{Vec2, ops};

pub mod replay;
pub mod script;

/// Fixed simulation rate. A power of two so `1.0 / TICK_HZ` is exact in binary
/// floating point, which matters for reproducible accumulation.
pub const TICK_HZ: u32 = 64;
/// Duration of one tick in seconds. Exact in f32 (1/64).
pub const TICK_DT: f32 = 1.0 / TICK_HZ as f32;

pub const ARENA_HALF_WIDTH: f32 = 400.0;
pub const ARENA_HALF_HEIGHT: f32 = 250.0;
pub const MARKER_HALF_SIZE: f32 = 12.0;
/// Invariant speed of the marker, in world units per second.
pub const MARKER_SPEED: f32 = 220.0;
/// How hard one tick of intent turns the marker.
pub const NUDGE_SPEED: f32 = 300.0;

// --------------------------------------------------------------------------
// Identity
// --------------------------------------------------------------------------

/// Stable simulation identity.
///
/// `Entity` is explicitly documented by Bevy as an opaque id whose bit pattern
/// may change between releases and whose index is **reused** after despawn.
/// Never sort, serialise, or send an `Entity` over the wire. Sort on this
/// instead.
#[derive(Component, Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub struct SimId(pub u32);

#[derive(Component, Debug, Clone, Copy, PartialEq)]
pub struct Position(pub Vec2);

#[derive(Component, Debug, Clone, Copy, PartialEq)]
pub struct Velocity(pub Vec2);

/// The one placeholder entity. Delete it when there is a real game here.
#[derive(Component, Debug, Clone, Copy)]
pub struct Marker;

// --------------------------------------------------------------------------
// Intent — the only way input enters the simulation
// --------------------------------------------------------------------------

/// Intent for the current tick.
///
/// The simulation reads *this*, never `ButtonInput`. Bevy's `ButtonInput` is
/// frame-scoped, not tick-scoped: `FixedUpdate` may run 0, 1, or many times per
/// frame, so reading it directly drops or duplicates inputs
/// (bevyengine/bevy#6183, still open). The client translates devices into intent
/// once per frame; a remote host receives intent over the wire. Both feed the
/// same simulation.
#[derive(Resource, Debug, Clone, Copy, Default, PartialEq, Eq)]
pub struct Intents {
    pub nudge_up: bool,
    pub nudge_down: bool,
}

impl Intents {
    /// -1 down, 0 still, +1 up. Opposing inputs cancel.
    pub fn axis(self) -> f32 {
        f32::from(i8::from(self.nudge_up) - i8::from(self.nudge_down))
    }
}

// --------------------------------------------------------------------------
// Simulation resources
// --------------------------------------------------------------------------

/// Monotonic simulation tick counter. Simulation code uses this instead of any
/// wall clock so that a replay produces byte-identical results.
#[derive(Resource, Debug, Clone, Copy, Default, PartialEq, Eq)]
pub struct Tick(pub u64);

/// Deterministic PRNG (PCG-XSH-RR 64/32), seeded explicitly and carried in the
/// snapshot. Never use `rand::thread_rng` or any OS entropy source in the
/// simulation: it would make replays and rollback impossible.
#[derive(Resource, Debug, Clone, Copy, PartialEq, Eq)]
pub struct SimRng {
    state: u64,
}

impl SimRng {
    const MUL: u64 = 6_364_136_223_846_793_005;
    const INC: u64 = 1_442_695_040_888_963_407;

    pub fn from_seed(seed: u64) -> Self {
        let mut rng = Self { state: 0 };
        rng.next_u32();
        rng.state = rng.state.wrapping_add(seed);
        rng.next_u32();
        rng
    }

    pub fn next_u32(&mut self) -> u32 {
        let old = self.state;
        self.state = old.wrapping_mul(Self::MUL).wrapping_add(Self::INC);
        let xorshifted = (((old >> 18) ^ old) >> 27) as u32;
        let rot = (old >> 59) as u32;
        xorshifted.rotate_right(rot)
    }

    /// Uniform in [0, 1).
    pub fn next_f32(&mut self) -> f32 {
        // 24 bits of mantissa, exactly representable, no rounding surprise.
        (self.next_u32() >> 8) as f32 / (1u32 << 24) as f32
    }

    /// Uniform in [lo, hi).
    pub fn range_f32(&mut self, lo: f32, hi: f32) -> f32 {
        lo + self.next_f32() * (hi - lo)
    }

    pub fn coin_flip(&mut self) -> bool {
        self.next_u32() & 1 == 1
    }
}

impl Default for SimRng {
    fn default() -> Self {
        Self::from_seed(0)
    }
}

/// What happened during the current tick. Consumed by presentation layers for
/// sound and VFX, and by `just probe` as the per-tick event list. Because this
/// is presentation-facing it lives in a resource that is cleared every tick, not
/// in a `Message` buffer — message buffers are frame-scoped and would drop or
/// duplicate against a fixed tick.
#[derive(Resource, Debug, Clone, Default, PartialEq)]
pub struct TickEvents {
    /// How many arena reflections happened this tick.
    pub bounces: u32,
    /// The same information as a flat, machine-readable list. Every structured
    /// field above has a name here; `just probe` emits this array verbatim.
    pub events: Vec<String>,
}

impl TickEvents {
    fn clear(&mut self) {
        self.bounces = 0;
        self.events.clear();
    }

    fn record_bounce(&mut self) {
        self.bounces += 1;
        self.events.push("bounce".to_owned());
    }
}

// --------------------------------------------------------------------------
// Schedule
// --------------------------------------------------------------------------

/// Ordered stages of one simulation tick. Explicitly `.chain()`ed: a total order
/// is the only ordering guarantee Bevy actually documents, and lockstep
/// multiplayer needs one.
#[derive(SystemSet, Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum SimSet {
    /// Advance the tick counter and clear per-tick event state.
    Begin,
    /// Apply intent to velocities.
    Intent,
    /// Integrate positions.
    Motion,
    /// Resolve collisions.
    Collision,
    /// Round outcomes: win/loss, resets, whatever ends a round.
    Scoring,
}

/// The headless simulation. Contains no rendering, windowing, audio, or input.
pub struct SimPlugin;

impl Plugin for SimPlugin {
    fn build(&self, app: &mut App) {
        app.init_resource::<Tick>()
            .init_resource::<Intents>()
            .init_resource::<TickEvents>()
            .init_resource::<SimRng>()
            .add_systems(Startup, spawn_world)
            .add_systems(
                FixedUpdate,
                (
                    begin_tick.in_set(SimSet::Begin),
                    apply_intent.in_set(SimSet::Intent),
                    integrate_motion.in_set(SimSet::Motion),
                    collide_bounds.in_set(SimSet::Collision),
                    resolve_round.in_set(SimSet::Scoring),
                ),
            )
            .configure_sets(
                FixedUpdate,
                (
                    SimSet::Begin,
                    SimSet::Intent,
                    SimSet::Motion,
                    SimSet::Collision,
                    SimSet::Scoring,
                )
                    .chain(),
            );

        // Turn the ambiguity checker into a hard error. Bevy ships this OFF
        // (`LogLevel::Ignore`), which means two systems writing the same data
        // with no ordering edge between them silently race and produce
        // frame-order-dependent results. `auto_insert_apply_deferred: false`
        // stops auto-inserted sync points from masking genuine ambiguities.
        app.edit_schedule(FixedUpdate, |schedule| {
            schedule.set_build_settings(ScheduleBuildSettings {
                ambiguity_detection: LogLevel::Error,
                auto_insert_apply_deferred: false,
                use_shortnames: false,
                ..Default::default()
            });
        });
    }
}

/// Deterministic initial world. Ids are assigned explicitly and never derived
/// from spawn order of `Entity`.
pub fn spawn_world(mut commands: Commands, mut rng: ResMut<SimRng>) {
    commands.spawn((
        SimId(1),
        Marker,
        Position(Vec2::ZERO),
        Velocity(launch_velocity(&mut rng)),
    ));
}

/// A direction drawn from the seeded RNG: a coin flip for the sign, then a small
/// random angle. Two RNG calls, in this order — changing the call sequence
/// changes every seeded run, so keep the shape if you keep the seed.
fn launch_velocity(rng: &mut SimRng) -> Vec2 {
    let toward_right = rng.coin_flip();
    let angle = rng.range_f32(-0.5, 0.5);
    // `ops::sin_cos`, not `f32::sin_cos`: the std versions call the *platform's*
    // libm, and Apple's, glibc's and MSVC's disagree in the last bit. One bit
    // here diverges a replay within seconds. `crates/sim/clippy.toml` makes
    // reaching for the std versions a build error.
    let (sin, cos) = ops::sin_cos(angle);
    let dir = Vec2::new(if toward_right { cos } else { -cos }, sin);
    dir * MARKER_SPEED
}

fn begin_tick(mut tick: ResMut<Tick>, mut events: ResMut<TickEvents>) {
    tick.0 += 1;
    events.clear();
}

/// Intent steers, it does not accelerate: the nudge is applied to `y` and the
/// result is renormalised, so speed is an invariant of the simulation and only
/// direction is under player control.
fn apply_intent(intents: Res<Intents>, mut movers: Query<&mut Velocity, With<Marker>>) {
    let axis = intents.axis();
    if axis == 0.0 {
        // Nothing pressed, or both directions pressed and cancelling. Leave the
        // velocity byte-identical rather than rescaling it to the same magnitude:
        // `v * (SPEED / |v|)` is NOT a fixed point in f32, so rescaling on every
        // idle tick makes the low bit of the velocity oscillate forever. That is
        // invisible on screen and fatal to a state hash - it was caught by
        // comparing this starter's hash chain against another stack's, which
        // diverged at tick 161 of an identical input tape.
        return;
    }
    let nudge = axis * NUDGE_SPEED * TICK_DT;
    for mut velocity in &mut movers {
        velocity.0.y += nudge;
        velocity.0 = velocity.0.clamp_length(MARKER_SPEED, MARKER_SPEED);
    }
}

fn integrate_motion(mut movers: Query<(&SimId, &mut Position, &Velocity)>) {
    // Sorting on SimId makes iteration order independent of archetype layout.
    // Bevy documents query iteration order as "not guaranteed", and unordered
    // iteration is the single most common cause of a divergent replay.
    // Integration is per-entity and order-independent today, but sorting keeps
    // it correct if someone later introduces coupling.
    let mut items: Vec<_> = movers.iter_mut().collect();
    items.sort_by_key(|(id, _, _)| **id);
    for (_, position, velocity) in &mut items {
        position.0 += velocity.0 * TICK_DT;
    }
}

/// Reflect off the arena walls, and clamp so nothing can ever be outside them
/// even if a single tick overshoots by more than the arena is wide.
fn collide_bounds(
    mut events: ResMut<TickEvents>,
    mut movers: Query<(&SimId, &mut Position, &mut Velocity), With<Marker>>,
) {
    let x_limit = ARENA_HALF_WIDTH - MARKER_HALF_SIZE;
    let y_limit = ARENA_HALF_HEIGHT - MARKER_HALF_SIZE;

    let mut items: Vec<_> = movers.iter_mut().collect();
    items.sort_by_key(|(id, _, _)| **id);

    for (_, position, velocity) in &mut items {
        if position.0.x.abs() > x_limit {
            let limit = x_limit.copysign(position.0.x);
            position.0.x = (limit - (position.0.x - limit)).clamp(-x_limit, x_limit);
            velocity.0.x = -velocity.0.x;
            events.record_bounce();
        }
        if position.0.y.abs() > y_limit {
            let limit = y_limit.copysign(position.0.y);
            position.0.y = (limit - (position.0.y - limit)).clamp(-y_limit, y_limit);
            velocity.0.y = -velocity.0.y;
            events.record_bounce();
        }
    }
}

/// Intentionally empty in the starter: the placeholder has no rounds to win or
/// lose. The stage is part of the pipeline's shape, so it stays — put whatever
/// ends a round (win conditions, resets, run summaries) here.
fn resolve_round() {}

// --------------------------------------------------------------------------
// State hashing — the backbone of replay and desync detection
// --------------------------------------------------------------------------

/// A whole-world checksum for a single tick.
///
/// Floats are hashed via `to_bits` so the hash is exact rather than
/// tolerance-based: a replay either reproduces the run bit-for-bit or it does
/// not. Entities are visited in `SimId` order so the hash cannot depend on
/// archetype layout.
pub fn state_hash(world: &mut World) -> u64 {
    // FNV-1a, chosen because it is trivially reimplementable in any language
    // (external tooling can verify a hash chain without linking this crate).
    const OFFSET: u64 = 0xcbf2_9ce4_8422_2325;
    const PRIME: u64 = 0x0000_0100_0000_01b3;

    let mut hash = OFFSET;
    let feed = |value: u64, hash: &mut u64| {
        for byte in value.to_le_bytes() {
            *hash ^= u64::from(byte);
            *hash = hash.wrapping_mul(PRIME);
        }
    };

    let tick = world.resource::<Tick>().0;
    feed(tick, &mut hash);

    let mut query = world.query::<(&SimId, &Position, &Velocity)>();
    let mut rows: Vec<(u32, [u32; 4])> = query
        .iter(world)
        .map(|(id, position, velocity)| {
            (
                id.0,
                [
                    position.0.x.to_bits(),
                    position.0.y.to_bits(),
                    velocity.0.x.to_bits(),
                    velocity.0.y.to_bits(),
                ],
            )
        })
        .collect();
    rows.sort_by_key(|(id, _)| *id);

    for (id, bits) in rows {
        feed(u64::from(id), &mut hash);
        for value in bits {
            feed(u64::from(value), &mut hash);
        }
    }
    hash
}
