//! Presentation layer: turns simulation state into something you can see.
//!
//! Strict one-way data flow. This crate reads `sim` and never writes to it.
//! Everything here is disposable; the simulation is the source of truth.

use bevy::camera::RenderTarget;
use bevy::prelude::*;
use bevy::sprite::Anchor;
use sim::{ARENA_HALF_HEIGHT, ARENA_HALF_WIDTH, MARKER_HALF_SIZE, Marker, Position, SimId, Tick};

pub mod harness;

pub const VIEW_WIDTH: u32 = 640;
pub const VIEW_HEIGHT: u32 = 400;

pub const MARKER_COLOR: Color = Color::srgb(1.0, 0.92, 0.30);
pub const BACKGROUND_COLOR: Color = Color::srgb(0.04, 0.05, 0.09);
pub const HUD_COLOR: Color = Color::srgb(0.45, 0.85, 1.0);

/// Top-left corner of the HUD text, in world units, inset from the arena corner.
pub const HUD_ORIGIN: Vec2 = Vec2::new(-ARENA_HALF_WIDTH + 12.0, ARENA_HALF_HEIGHT - 10.0);
/// HUD glyph height in world units. Kept small on purpose: the HUD is an
/// overlay, and every pixel it lights is a pixel the arena assertions have to
/// live with.
pub const HUD_FONT_SIZE: f32 = 15.0;
/// The pixel box the HUD draws into, `[x0, y0, x1, y1]`, half-open, in captured
/// frame coordinates. The rendering tests count ink inside it — see
/// `crates/game/tests/render.rs::the_hud_is_in_the_captured_frame`.
pub const HUD_REGION: [u32; 4] = [0, 0, 220, 32];

/// Links a view entity back to the simulation entity it draws.
///
/// This mirrors Bevy's own `MainEntity`/`RenderEntity` pairing between the main
/// and render worlds. The indirection is what lets the simulation run with no
/// view at all — which is exactly what every test in `sim` does.
#[derive(Component, Debug, Clone, Copy)]
pub struct ViewOf(pub Entity);

/// The readout in the corner of the arena.
#[derive(Component, Debug, Clone, Copy)]
pub struct Hud;

/// Draws the simulation. Add on top of [`sim::SimPlugin`].
pub struct ViewPlugin;

impl Plugin for ViewPlugin {
    fn build(&self, app: &mut App) {
        app.insert_resource(ClearColor(BACKGROUND_COLOR))
            .add_systems(Startup, spawn_hud)
            .add_systems(
                Update,
                (spawn_views, sync_view_transforms, update_hud).chain(),
            );
    }
}

/// The HUD, as [`Text2d`] — drawn by the 2D camera, into whatever that camera's
/// [`RenderTarget`] is.
///
/// That is the whole point, and it is the one thing to get right when you add
/// anything else the player reads. `capture_frame` points the arena camera at an
/// offscreen image and reads that image back; `just film` and every rendering
/// test see exactly those pixels and nothing else. A readout drawn by some other
/// camera, or through a path that only ever resolves to a window surface, is
/// invisible to all of them — and an agent then cannot tell a broken scoreboard
/// from a scoreboard the capture never looked at.
///
/// The font is Bevy's built-in one: the `default_font` feature arrives via
/// `bevy`'s `2d` feature (`2d` → `default_platform` → `default_font`), so
/// `TextFont::default()`'s font source resolves with no asset on disk.
fn spawn_hud(mut commands: Commands) {
    commands.spawn((
        Hud,
        Text2d::new(hud_line(0, None)),
        TextFont::from_font_size(HUD_FONT_SIZE),
        TextColor(HUD_COLOR),
        Anchor::TOP_LEFT,
        // In front of the sprites.
        Transform::from_xyz(HUD_ORIGIN.x, HUD_ORIGIN.y, 10.0),
    ));
}

/// What the HUD says: a pure function of simulation state, and nothing else.
///
/// No wall clock, no frame counter, no unseeded randomness — the capture path is
/// asserted byte-reproducible across runs, and a HUD that reads the clock breaks
/// that without breaking anything in `sim`.
fn hud_line(tick: u64, marker: Option<Vec2>) -> String {
    match marker {
        Some(at) => format!(
            "t{tick} x{x} y{y}",
            x = at.x.round() as i32,
            y = at.y.round() as i32
        ),
        None => format!("t{tick}"),
    }
}

/// Refresh the readout. Reads `sim`, writes only the view — same one-way flow as
/// every other system here.
fn update_hud(
    tick: Res<Tick>,
    markers: Query<(&SimId, &Position), With<Marker>>,
    mut hud: Query<&mut Text2d, With<Hud>>,
) {
    // Lowest SimId wins, so the readout does not depend on query iteration order.
    let marker = markers
        .iter()
        .min_by_key(|(id, _)| **id)
        .map(|(_, position)| position.0);
    let line = hud_line(tick.0, marker);
    for mut text in &mut hud {
        // Assigning unconditionally would mark the text changed every frame and
        // re-run layout for nothing.
        if text.0 != line {
            text.0.clone_from(&line);
        }
    }
}

/// Give every simulation entity the view layer knows how to draw a sprite.
///
/// Note the query: it matches on the *component that says what the thing is*
/// (`Marker`), not on every entity that happens to have a `SimId`.
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
    drawable: Query<Entity, (With<SimId>, With<Marker>)>,
    existing: Query<&ViewOf>,
) {
    for entity in &drawable {
        if existing.iter().any(|view| view.0 == entity) {
            continue;
        }
        commands.spawn((
            ViewOf(entity),
            Sprite {
                color: MARKER_COLOR,
                custom_size: Some(Vec2::splat(MARKER_HALF_SIZE * 2.0)),
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
