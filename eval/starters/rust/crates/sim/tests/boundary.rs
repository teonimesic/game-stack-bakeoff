//! The hexagonal boundary and the determinism ban, enforced against the real
//! dependency graph rather than against a convention in a markdown file.
//!
//! `crates/sim` is the headless source of truth. It must stay compilable and
//! testable with no GPU, no window and no wall clock. Rust gives us a *compiler*
//! guarantee for direct use — `sim` does not depend on `bevy`, so `use bevy::…`
//! will not compile — but nothing stops someone adding `bevy_render` to
//! `crates/sim/Cargo.toml` and then writing whatever they like. These tests
//! close that gap: they read the actual resolved dependency graph via
//! `cargo tree` and fail if a banned crate is reachable from `sim`.
//!
//! Why not `cargo-deny`? Its `[bans]` section is workspace-scoped. It can say
//! "nothing may depend on wgpu", which is false here (`crates/game` must), but
//! it cannot say "nothing *in sim's subtree* may depend on wgpu". That is the
//! rule we actually need, so we assert it directly.

use std::process::Command;

/// Crates that would break the "no GPU, no window, no OS" property of `sim`.
/// Adding any of these to `crates/sim/Cargo.toml` makes the simulation
/// untestable headlessly and unusable on a headless host.
const RENDER_BANNED: &[&str] = &[
    "bevy",
    "bevy_internal",
    "bevy_render",
    "bevy_sprite",
    "bevy_sprite_render",
    "bevy_core_pipeline",
    "bevy_camera",
    "bevy_image",
    "bevy_pbr",
    "bevy_ui",
    "bevy_text",
    "bevy_window",
    "bevy_winit",
    "bevy_audio",
    "bevy_gilrs",
    "bevy_input",
    "bevy_asset",
    "wgpu",
    "wgpu-core",
    "wgpu-hal",
    "winit",
    "image",
];

/// Crates whose whole purpose is a source of entropy or wall-clock time. Any of
/// them in `sim`'s tree means replays and rollback stop working.
const NONDETERMINISM_BANNED: &[&str] = &[
    "rand",
    "rand_core",
    "rand_chacha",
    "fastrand",
    "getrandom",
    "nanorand",
    "oorandom",
    "chrono",
    "time",
    "instant",
    "web-time",
    "uuid",
];

fn cargo_tree(args: &[&str]) -> String {
    let output = Command::new(env!("CARGO"))
        .current_dir(env!("CARGO_MANIFEST_DIR"))
        // `--locked --offline` so this test can never mutate Cargo.lock or hit
        // a remote registry as a side effect of running the test suite.
        .args(["tree", "--locked", "--offline", "--prefix", "none"])
        .args(args)
        .output()
        .expect("failed to run `cargo tree` — is cargo on PATH?");
    assert!(
        output.status.success(),
        "`cargo tree {}` failed:\n{}",
        args.join(" "),
        String::from_utf8_lossy(&output.stderr)
    );
    String::from_utf8(output.stdout).expect("cargo tree emitted non-UTF-8")
}

/// Every crate name reachable from `sim` through normal and build edges.
fn sim_dependency_names() -> Vec<String> {
    cargo_tree(&["-p", "sim", "--edges", "normal,build", "--no-dedupe"])
        .lines()
        .filter_map(|line| line.split_whitespace().next())
        .filter(|name| !name.is_empty() && *name != "(*)")
        .map(str::to_owned)
        .collect()
}

fn assert_absent(banned: &[&str], why: &str) {
    let present = sim_dependency_names();
    let found: Vec<&str> = banned
        .iter()
        .copied()
        .filter(|b| present.iter().any(|p| p == b))
        .collect();
    assert!(
        found.is_empty(),
        "`crates/sim` now depends on {found:?}.\n\n{why}\n\n\
         Fix it in `crates/sim/Cargo.toml`, not here. If the code that needs \
         this really is presentation, it belongs in `crates/game`. Removing an \
         entry from the ban list in this file is not a fix — it deletes the \
         guarantee the whole template is built on."
    );
}

#[test]
fn sim_does_not_depend_on_the_renderer() {
    assert_absent(
        RENDER_BANNED,
        "The simulation must run with no GPU, no window and no display: \
         that is what makes `just test-sim` take milliseconds, what lets the \
         same code run on a headless host, and what keeps replays portable.",
    );
}

#[test]
fn sim_does_not_depend_on_entropy_or_a_wall_clock() {
    assert_absent(
        NONDETERMINISM_BANNED,
        "All randomness in the simulation must come from `SimRng`, which is \
         part of snapshotted state, and all time from `Tick`. A crate that \
         reads OS entropy or the system clock makes replay, rollback and \
         desync detection impossible — and the failure is silent until a \
         replay diverges.",
    );
}

#[test]
fn transcendental_maths_goes_through_libm_not_the_platform() {
    // `glam/libm` routes sin/cos/tan/powf through a pure-Rust implementation so
    // two machines agree bit-for-bit. `glam/fast-math` explicitly trades that
    // away. Both are silent, graph-level properties that no unit test on game
    // logic would ever notice.
    let features = cargo_tree(&["-p", "sim", "--edges", "features"]);
    assert!(
        features.contains(r#"glam feature "libm""#),
        "`glam/libm` is no longer enabled for `crates/sim`. Transcendental \
         functions would fall back to the platform's libm, which differs \
         between macOS, Linux and Windows — replays would stop matching across \
         machines. Restore `features = [\"libm\"]` on `bevy_math` in the \
         workspace Cargo.toml."
    );
    assert!(
        !features.contains(r#"glam feature "fast-math""#),
        "`glam/fast-math` is enabled. It documents that it trades bit-for-bit \
         cross-platform identity for speed, which is exactly the property this \
         template exists to protect. Turn it off."
    );
}
