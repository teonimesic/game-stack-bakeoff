use bevy::camera::RenderTarget;
use bevy::prelude::*;
use game::{ViewPlugin, arena_camera};
use sim::{Intents, PlayerIntent, SimPlugin, TICK_HZ};

fn main() {
    App::new()
        .add_plugins(DefaultPlugins)
        .add_plugins(SimPlugin)
        .add_plugins(ViewPlugin)
        .insert_resource(Time::<Fixed>::from_hz(f64::from(TICK_HZ)))
        .add_systems(Startup, setup)
        // Devices are read once per frame and turned into intent. The
        // simulation never sees `ButtonInput` directly.
        .add_systems(Update, read_input)
        .run();
}

fn setup(mut commands: Commands) {
    commands.spawn(arena_camera(RenderTarget::default()));
}

fn read_input(keys: Res<ButtonInput<KeyCode>>, mut intents: ResMut<Intents>) {
    intents.left = PlayerIntent {
        up: keys.pressed(KeyCode::KeyW),
        down: keys.pressed(KeyCode::KeyS),
    };
    intents.right = PlayerIntent {
        up: keys.pressed(KeyCode::ArrowUp),
        down: keys.pressed(KeyCode::ArrowDown),
    };
}
