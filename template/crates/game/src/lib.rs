//! Presentation layer: turns simulation state into something you can see.
//!
//! Strict one-way data flow. This crate reads `sim` and never writes to it.
//! Everything here is disposable; the simulation is the source of truth.

use bevy::camera::RenderTarget;
use bevy::prelude::*;
use sim::{
    ARENA_HALF_HEIGHT, ARENA_HALF_WIDTH, BALL_RADIUS, Ball, PADDLE_HALF_HEIGHT, Paddle, Position,
    SimId,
};

pub mod harness;

pub const VIEW_WIDTH: u32 = 640;
pub const VIEW_HEIGHT: u32 = 400;

pub const BALL_COLOR: Color = Color::srgb(1.0, 0.92, 0.30);
pub const PADDLE_COLOR: Color = Color::srgb(0.35, 0.78, 1.0);
pub const BACKGROUND_COLOR: Color = Color::srgb(0.04, 0.05, 0.09);

/// Links a view entity back to the simulation entity it draws.
///
/// This mirrors Bevy's own `MainEntity`/`RenderEntity` pairing between the main
/// and render worlds. The indirection is what lets the simulation run with no
/// view at all — which is exactly what every test in `sim` does.
#[derive(Component, Debug, Clone, Copy)]
pub struct ViewOf(pub Entity);

/// Draws the simulation. Add on top of [`sim::SimPlugin`].
pub struct ViewPlugin;

impl Plugin for ViewPlugin {
    fn build(&self, app: &mut App) {
        app.insert_resource(ClearColor(BACKGROUND_COLOR))
            .add_systems(Update, (spawn_views, sync_view_transforms).chain());
    }
}

/// Give every simulation entity the view layer knows how to draw a sprite.
///
/// Note the query: it matches on the *component that says what the thing is*
/// (`Ball`, `Paddle`), not on every entity that happens to have a `SimId`.
///
/// That is deliberate and it is load-bearing. Matching on `SimId` means any new
/// simulation entity — a powerup, a particle, a trigger volume — instantly
/// appears on screen as whatever the fallback branch happens to draw, silently
/// changes the golden image, and turns a correct simulation-only change into a
/// red rendering test that has nothing to do with what changed. Measured: it
/// did exactly that.
///
/// So: the view draws what it understands, and adding a new drawable is an
/// explicit, one-line decision here. Sim stays free to add entities without
/// asking the renderer's permission — which is the whole point of the split.
fn spawn_views(
    mut commands: Commands,
    drawable: Query<(Entity, Option<&Ball>), (With<SimId>, Or<(With<Ball>, With<Paddle>)>)>,
    existing: Query<&ViewOf>,
) {
    for (entity, ball) in &drawable {
        if existing.iter().any(|view| view.0 == entity) {
            continue;
        }
        let (color, size) = if ball.is_some() {
            (BALL_COLOR, Vec2::splat(BALL_RADIUS * 2.0))
        } else {
            (PADDLE_COLOR, Vec2::new(16.0, PADDLE_HALF_HEIGHT * 2.0))
        };
        commands.spawn((
            ViewOf(entity),
            Sprite {
                color,
                custom_size: Some(size),
                ..default()
            },
            Transform::default(),
        ));
    }
}

/// Copy simulation positions onto view transforms. One way only.
fn sync_view_transforms(positions: Query<&Position>, mut views: Query<(&ViewOf, &mut Transform)>) {
    for (view, mut transform) in &mut views {
        if let Ok(position) = positions.get(view.0) {
            transform.translation.x = position.0.x;
            transform.translation.y = position.0.y;
        }
    }
}

/// A camera that frames the whole arena, rendering to `target`.
///
/// NOTE (Bevy 0.19): `RenderTarget` is a **component**, not a field on `Camera`.
/// It moved in 0.19. Older code — and most model training data — writes
/// `Camera { target, .. }`, which no longer compiles.
pub fn arena_camera(target: RenderTarget) -> impl Bundle {
    (
        Camera2d,
        target,
        // Scale so the full arena fits the viewport regardless of pixel size.
        Projection::from(OrthographicProjection {
            scaling_mode: bevy::camera::ScalingMode::Fixed {
                width: ARENA_HALF_WIDTH * 2.0,
                height: ARENA_HALF_HEIGHT * 2.0,
            },
            ..OrthographicProjection::default_2d()
        }),
    )
}
