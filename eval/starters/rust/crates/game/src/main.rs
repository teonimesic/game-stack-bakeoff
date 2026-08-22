use bevy::camera::RenderTarget;
use bevy::prelude::*;
use game::{ViewPlugin, arena_camera};
use sim::{Intents, SimPlugin, TICK_HZ};

/// Does the launch discipline ask this process not to take focus?
///
/// Set by `just run` from the shared `tools/launch.just`. The rule there is stated as a
/// RESOURCE - anything that opens a window or an audio device - because the previous
/// attempt was stated as a list of recipes and missed the one that plays to a human.
///
/// `Window::focused` is a CREATION hint: bevy_window documents that it "cannot be set
/// unfocused after creation", so it has to go in the `WindowPlugin` and not into a
/// startup system.
///
/// AUDIO IS NOT GUARDED HERE, and that is not an oversight. This starter builds bevy with
/// `default-features = false` and no audio feature, so a pristine tree cannot open an
/// audio device at all. An agent that adds audio to satisfy the task should honour
/// `STARTER_SILENT_LAUNCH` - see `tools/launch.just` - and there is no engine-level null
/// sink to fall back on the way godot has `--audio-driver Dummy`.
fn no_raise() -> bool {
    std::env::var("STARTER_NO_RAISE").as_deref() == Ok("1")
}

fn main() {
    App::new()
        .add_plugins(DefaultPlugins.set(WindowPlugin {
            primary_window: Some(Window {
                focused: !no_raise(),
                ..default()
            }),
            ..default()
        }))
        .add_plugins(SimPlugin)
        .add_plugins(ViewPlugin)
        .insert_resource(Time::<Fixed>::from_hz(f64::from(TICK_HZ)))
        .add_systems(Startup, setup)
        // HARNESS SCAFFOLDING, gated on STARTER_NO_RAISE which is UNSET BY DEFAULT.
        // A human running `just run` gets the window the author wrote: it raises and
        // takes focus. Only the evaluation harness sets the variable.
        .add_systems(Update, no_raise_correction)
        // Devices are read once per frame and turned into intent. The
        // simulation never sees `ButtonInput` directly.
        .add_systems(Update, read_input)
        .run();
}

/// Hand the keyboard back if the window raised itself anyway.
///
/// `Window::focused` is a CREATION hint and bevy_window says it "cannot be set unfocused
/// after creation" - so `WindowPlugin` asks for `focused: false` and, MEASURED, the window
/// still takes focus on macOS. `open -g -j` does not help either: that hint works for
/// Unity's player and is overridden here, because the engine activates itself.
///
/// So this is a CORRECTION, not a prevention, and the distinction is the finding: the
/// engine could not be stopped from raising, only undone afterwards. It runs once.
fn no_raise_correction(
    mut windows: Query<&mut Window>,
    mut done: Local<bool>,
) {
    if *done {
        return;
    }
    if std::env::var("STARTER_NO_RAISE").as_deref() != Ok("1") {
        *done = true;
        return;
    }
    let Ok(mut w) = windows.single_mut() else {
        return;
    };
    if w.focused {
        // Order of escalation, cheapest first: hide the window, THEN minimise. A hidden
        // window may release the app's active state where a minimised one does not.
        w.visible = false;
        w.set_minimized(true);
        info!("[no_raise] window raised despite focused:false - hidden and minimised");
    } else {
        info!("[no_raise] creation hint sufficient: window did not take focus");
    }
    *done = true;
}

fn setup(mut commands: Commands) {
    commands.spawn(arena_camera(RenderTarget::default()));
}

fn read_input(keys: Res<ButtonInput<KeyCode>>, mut intents: ResMut<Intents>) {
    *intents = Intents {
        nudge_up: keys.any_pressed([KeyCode::KeyW, KeyCode::ArrowUp]),
        nudge_down: keys.any_pressed([KeyCode::KeyS, KeyCode::ArrowDown]),
    };
}
