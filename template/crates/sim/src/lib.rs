//! Headless, deterministic game simulation.
//!
//! This crate MUST NOT depend on rendering, windowing, audio, or input devices.
//! It is the single source of truth for game state and is fully testable with no
//! GPU and no window. See `docs/architecture.md`.
//!
//! Determinism rules, and what enforces each of them:
//! - all simulation runs in [`SimSet`] inside `FixedUpdate`, `.chain()`ed
//!   — `tests/determinism.rs::fixed_update_schedule_has_no_ambiguities`
//! - systems read intent ([`PlayerIntent`]), never raw input devices
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

/// Fixed simulation rate. A power of two so `1.0 / TICK_HZ` is exact in binary
/// floating point, which matters for reproducible accumulation.
pub const TICK_HZ: u32 = 64;
/// Duration of one tick in seconds. Exact in f32 (1/64).
pub const TICK_DT: f32 = 1.0 / TICK_HZ as f32;

pub const ARENA_HALF_WIDTH: f32 = 400.0;
pub const ARENA_HALF_HEIGHT: f32 = 250.0;
pub const PADDLE_HALF_HEIGHT: f32 = 50.0;
pub const PADDLE_INSET: f32 = 370.0;
pub const PADDLE_SPEED: f32 = 300.0;
pub const BALL_RADIUS: f32 = 8.0;
pub const BALL_START_SPEED: f32 = 250.0;
/// Multiplier applied to ball speed on every paddle hit.
pub const BALL_SPEEDUP: f32 = 1.05;
pub const MAX_BALL_SPEED: f32 = 900.0;

// --------------------------------------------------------------------------
// Identity
// --------------------------------------------------------------------------

/// Stable simulation identity.
///
/// `Entity` is explicitly documented by Bevy as an opaque id whose bit pattern
/// may change between releases and whose index is **reused** after despawn.
/// Never sort, serialise, or network on `Entity`. Sort on this instead.
#[derive(Component, Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub struct SimId(pub u32);

/// Which player a paddle belongs to.
#[derive(Component, Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub enum Side {
    Left,
    Right,
}

#[derive(Component, Debug, Clone, Copy, PartialEq)]
pub struct Position(pub Vec2);

#[derive(Component, Debug, Clone, Copy, PartialEq)]
pub struct Velocity(pub Vec2);

#[derive(Component, Debug, Clone, Copy)]
pub struct Paddle;

#[derive(Component, Debug, Clone, Copy)]
pub struct Ball;

// --------------------------------------------------------------------------
// Intent — the only way input enters the simulation
// --------------------------------------------------------------------------

/// Per-player intent for the current tick.
///
/// The simulation reads *this*, never `ButtonInput`. Bevy's `ButtonInput` is
/// frame-scoped, not tick-scoped: `FixedUpdate` may run 0, 1, or many times per
/// frame, so reading it directly drops or duplicates inputs
/// (bevyengine/bevy#6183, still open). The client translates devices into intent
/// once per frame; the server receives intent over the wire. Both feed the same
/// simulation.
#[derive(Debug, Clone, Copy, Default, PartialEq, Eq)]
pub struct PlayerIntent {
    pub up: bool,
    pub down: bool,
}

impl PlayerIntent {
    /// -1 down, 0 still, +1 up. Opposing inputs cancel.
    pub fn axis(self) -> f32 {
        f32::from(i8::from(self.up) - i8::from(self.down))
    }
}

/// Intent for both players this tick.
#[derive(Resource, Debug, Clone, Copy, Default, PartialEq, Eq)]
pub struct Intents {
    pub left: PlayerIntent,
    pub right: PlayerIntent,
}

// --------------------------------------------------------------------------
// Simulation resources
// --------------------------------------------------------------------------

/// Monotonic simulation tick counter. Simulation code uses this instead of any
/// wall clock so that a replay produces byte-identical results.
#[derive(Resource, Debug, Clone, Copy, Default, PartialEq, Eq)]
pub struct Tick(pub u64);

#[derive(Resource, Debug, Clone, Copy, Default, PartialEq, Eq)]
pub struct Score {
    pub left: u32,
    pub right: u32,
}

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

/// Emitted when a paddle deflects the ball. Consumed by presentation layers for
/// sound and VFX. Because this is presentation-facing it lives in a resource
/// that is cleared every tick, not in a `Message` buffer — message buffers are
/// frame-scoped and would drop or duplicate against a fixed tick.
#[derive(Resource, Debug, Clone, Default, PartialEq)]
pub struct TickEvents {
    pub paddle_hits: Vec<Side>,
    pub wall_bounces: u32,
    pub scored: Option<Side>,
}

impl TickEvents {
    fn clear(&mut self) {
        self.paddle_hits.clear();
        self.wall_bounces = 0;
        self.scored = None;
    }
}

// --------------------------------------------------------------------------
// Schedule
// --------------------------------------------------------------------------

/// Ordered stages of one simulation tick. Explicitly `.chain()`ed: a total order
/// is the only ordering guarantee Bevy actually documents, and lockstep netcode
/// needs one.
#[derive(SystemSet, Debug, Clone, Copy, PartialEq, Eq, Hash)]
pub enum SimSet {
    /// Advance the tick counter and clear per-tick event state.
    Begin,
    /// Apply intent to paddle velocities.
    Intent,
    /// Integrate positions.
    Motion,
    /// Resolve collisions.
    Collision,
    /// Scoring and round reset.
    Scoring,
}

/// The headless simulation. Contains no rendering, windowing, audio, or input.
pub struct SimPlugin;

impl Plugin for SimPlugin {
    fn build(&self, app: &mut App) {
        app.init_resource::<Tick>()
            .init_resource::<Score>()
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
                    (collide_walls, collide_paddles)
                        .chain()
                        .in_set(SimSet::Collision),
                    score_and_reset.in_set(SimSet::Scoring),
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
        Paddle,
        Side::Left,
        Position(Vec2::new(-PADDLE_INSET, 0.0)),
        Velocity(Vec2::ZERO),
    ));
    commands.spawn((
        SimId(2),
        Paddle,
        Side::Right,
        Position(Vec2::new(PADDLE_INSET, 0.0)),
        Velocity(Vec2::ZERO),
    ));
    commands.spawn((
        SimId(3),
        Ball,
        Position(Vec2::ZERO),
        Velocity(serve_velocity(&mut rng)),
    ));
}

fn serve_velocity(rng: &mut SimRng) -> Vec2 {
    let toward_right = rng.coin_flip();
    // Keep the serve away from near-vertical so rallies actually start.
    let angle = rng.range_f32(-0.5, 0.5);
    // `ops::sin_cos`, not `f32::sin_cos`: the std versions call the *platform's*
    // libm, and Apple's, glibc's and MSVC's disagree in the last bit. One bit
    // here diverges a replay within seconds. `crates/sim/clippy.toml` makes
    // reaching for the std versions a build error.
    let (sin, cos) = ops::sin_cos(angle);
    let dir = Vec2::new(if toward_right { cos } else { -cos }, sin);
    dir * BALL_START_SPEED
}

fn begin_tick(mut tick: ResMut<Tick>, mut events: ResMut<TickEvents>) {
    tick.0 += 1;
    events.clear();
}

fn apply_intent(intents: Res<Intents>, mut paddles: Query<(&Side, &mut Velocity), With<Paddle>>) {
    for (side, mut velocity) in &mut paddles {
        let intent = match side {
            Side::Left => intents.left,
            Side::Right => intents.right,
        };
        velocity.0 = Vec2::new(0.0, intent.axis() * PADDLE_SPEED);
    }
}

fn integrate_motion(mut movers: Query<(&SimId, &mut Position, &Velocity)>) {
    // Sorting on SimId makes iteration order independent of archetype layout.
    // Bevy documents query iteration order as "not guaranteed", and bevy_ggrs
    // names unordered iteration as the single most common desync cause.
    // Integration is per-entity and order-independent today, but sorting keeps
    // it correct if someone later introduces coupling.
    let mut items: Vec<_> = movers.iter_mut().collect();
    items.sort_by_key(|(id, _, _)| **id);
    for (_, position, velocity) in &mut items {
        position.0 += velocity.0 * TICK_DT;
    }
}

fn collide_walls(
    mut events: ResMut<TickEvents>,
    mut movers: Query<(&mut Position, &mut Velocity, Option<&Ball>, Option<&Paddle>)>,
) {
    for (mut position, mut velocity, ball, paddle) in &mut movers {
        if paddle.is_some() {
            // Paddles clamp against the arena and stop dead.
            let limit = ARENA_HALF_HEIGHT - PADDLE_HALF_HEIGHT;
            if position.0.y > limit {
                position.0.y = limit;
                velocity.0.y = 0.0;
            } else if position.0.y < -limit {
                position.0.y = -limit;
                velocity.0.y = 0.0;
            }
        } else if ball.is_some() {
            let limit = ARENA_HALF_HEIGHT - BALL_RADIUS;
            if position.0.y > limit {
                position.0.y = limit - (position.0.y - limit);
                velocity.0.y = -velocity.0.y;
                events.wall_bounces += 1;
            } else if position.0.y < -limit {
                position.0.y = -limit - (position.0.y + limit);
                velocity.0.y = -velocity.0.y;
                events.wall_bounces += 1;
            }
        }
    }
}

fn collide_paddles(
    mut events: ResMut<TickEvents>,
    paddles: Query<(&SimId, &Side, &Position), (With<Paddle>, Without<Ball>)>,
    mut balls: Query<(&mut Position, &mut Velocity), With<Ball>>,
) {
    // Deterministic paddle order: without this, two paddles that could both
    // claim the ball on the same tick would resolve in archetype order.
    let mut ordered: Vec<_> = paddles.iter().collect();
    ordered.sort_by_key(|(id, _, _)| **id);

    for (mut ball_pos, mut ball_vel) in &mut balls {
        for (_, side, paddle_pos) in &ordered {
            let face_x = match side {
                Side::Left => paddle_pos.0.x + BALL_RADIUS,
                Side::Right => paddle_pos.0.x - BALL_RADIUS,
            };
            let moving_into = match side {
                Side::Left => ball_vel.0.x < 0.0 && ball_pos.0.x <= face_x,
                Side::Right => ball_vel.0.x > 0.0 && ball_pos.0.x >= face_x,
            };
            let vertically_overlapping =
                (ball_pos.0.y - paddle_pos.0.y).abs() <= PADDLE_HALF_HEIGHT + BALL_RADIUS;

            if moving_into && vertically_overlapping {
                ball_pos.0.x = face_x;
                ball_vel.0.x = -ball_vel.0.x;
                // Deflection angle depends on where the ball struck the paddle.
                let offset = (ball_pos.0.y - paddle_pos.0.y) / PADDLE_HALF_HEIGHT;
                ball_vel.0.y += offset * BALL_START_SPEED * 0.5;
                ball_vel.0 = (ball_vel.0 * BALL_SPEEDUP).clamp_length_max(MAX_BALL_SPEED);
                events.paddle_hits.push(**side);
                break;
            }
        }
    }
}

fn score_and_reset(
    mut score: ResMut<Score>,
    mut events: ResMut<TickEvents>,
    mut rng: ResMut<SimRng>,
    mut balls: Query<(&mut Position, &mut Velocity), With<Ball>>,
) {
    for (mut position, mut velocity) in &mut balls {
        let scorer = if position.0.x > ARENA_HALF_WIDTH {
            Some(Side::Left)
        } else if position.0.x < -ARENA_HALF_WIDTH {
            Some(Side::Right)
        } else {
            None
        };

        if let Some(side) = scorer {
            match side {
                Side::Left => score.left += 1,
                Side::Right => score.right += 1,
            }
            events.scored = Some(side);
            position.0 = Vec2::ZERO;
            velocity.0 = serve_velocity(&mut rng);
        }
    }
}

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
    // (the Elixir meta-service and future tooling can verify hashes too).
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
    let score = *world.resource::<Score>();
    feed(tick, &mut hash);
    feed(u64::from(score.left), &mut hash);
    feed(u64::from(score.right), &mut hash);

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
