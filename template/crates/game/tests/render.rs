//! End-to-end rendering tests: the real renderer, a real GPU path, real pixels.
//!
//! These are the tests that catch "the code compiles, the logic is right, and
//! nothing appears on screen." Unit tests on `sim` cannot catch that class of
//! bug, and it is the class that matters most in a game.
//!
//! Ordered from most robust to most brittle:
//!   1. invariants on the pixels (something rendered; it is where we expect)
//!   2. relational assertions (it moved in the right direction)
//!   3. golden-image comparison (it looks exactly like the approved frame)
//!
//! Prefer 1 and 2. Reach for 3 only when the exact look is the thing under test.

use game::harness::{Frame, capture_frame};
use game::{BACKGROUND_COLOR, VIEW_HEIGHT, VIEW_WIDTH};
use sim::{Intents, PlayerIntent};

/// Background as u8 RGB, for "is this pixel ink?" tests.
fn background_rgb() -> [u8; 3] {
    let srgb = BACKGROUND_COLOR.to_srgba();
    [
        (srgb.red * 255.0).round() as u8,
        (srgb.green * 255.0).round() as u8,
        (srgb.blue * 255.0).round() as u8,
    ]
}

/// A skipped rendering test is a test that proved nothing, so skipping is kept
/// as narrow as it can be.
///
/// MEASURED, and worth knowing before you trust this macro: an environment with
/// **no adapter at all** does not reach here. Bevy's `RenderPlugin` panics
/// during `App::finish()` with "Unable to find a GPU! Make sure you have
/// installed required drivers!", so the test goes red. That is the right
/// outcome and the message is actionable — do not add a `catch_unwind` to
/// soften it.
///
/// What survives to here is the ambiguous middle: an adapter exists but the
/// readback never lands (virtualised GPUs, some remote sessions). That is soft
/// by default so a developer is not stuck with a red they cannot fix, and it is
/// escalated to a failure whenever `REQUIRE_GPU` is set — which `just ci` and
/// both CI render jobs do. `just test-render` additionally counts skips and
/// prints them beside the summary, so a locally green `verify` can never
/// quietly mean "zero rendering coverage".
macro_rules! frame_or_skip {
    ($expr:expr) => {
        match $expr {
            Ok(frame) => frame,
            Err(err) if err.contains("no adapter") || err.contains("readback never completed") => {
                assert!(
                    std::env::var_os("REQUIRE_GPU").is_none(),
                    "REQUIRE_GPU is set and the GPU never delivered a frame: {}. \
                     This is a real failure — the rendering layer is unverified. \
                     On a Linux runner install lavapipe (see .github/workflows/ci.yaml); \
                     on macOS this needs a real GPU runner, there is no software Metal.",
                    err
                );
                eprintln!(
                    "SKIP: the GPU never delivered a frame here ({err}). \
                     This test asserted NOTHING about the rendered output."
                );
                // nextest hides the stderr of a passing test, so the line above
                // is not enough on its own. Leave a note on disk that
                // `just test-render` counts and reports next to the summary.
                record_skip(concat!(file!(), ":", line!()));
                return;
            }
            Err(err) => panic!("render harness failed: {err}"),
        }
    };
}

/// Append one line to `$CARGO_TARGET_DIR/tmp/render-skips.log`. `just
/// test-render` truncates it before the run and reports the count after, so a
/// green summary can never quietly mean "no rendering was verified".
fn record_skip(what: &str) {
    use std::io::Write as _;
    let path = concat!(env!("CARGO_TARGET_TMPDIR"), "/render-skips.log");
    if let Ok(mut file) = std::fs::OpenOptions::new()
        .create(true)
        .append(true)
        .open(path)
    {
        let _ = writeln!(file, "{what}");
    }
}

#[test]
fn renders_a_non_empty_frame() {
    // The single most valuable rendering assertion there is: the renderer ran
    // and drew something other than the clear colour.
    let frame = frame_or_skip!(capture_frame(1, 30, &[]));

    assert_eq!(frame.width, VIEW_WIDTH);
    assert_eq!(frame.height, VIEW_HEIGHT);

    let coverage = frame.ink_coverage(background_rgb(), 8);
    assert!(
        coverage > 0.001,
        "nothing was drawn — {:.4}% of pixels differ from the background. \
         The simulation may be running correctly while the view is broken.",
        coverage * 100.0
    );
    assert!(
        coverage < 0.5,
        "{:.1}% of the frame is non-background; the camera is probably \
         mis-scaled or a sprite is covering the screen",
        coverage * 100.0
    );
}

#[test]
fn both_paddles_and_the_ball_are_visible() {
    let frame = frame_or_skip!(capture_frame(2, 1, &[]));
    let bg = background_rgb();

    // Paddles sit near the left and right edges; the ball starts centred.
    let column_has_ink = |x_lo: u32, x_hi: u32| {
        (x_lo..x_hi).any(|x| {
            (0..frame.height).any(|y| {
                let p = frame.pixel(x, y);
                (0..3).any(|c| p[c].abs_diff(bg[c]) > 8)
            })
        })
    };

    assert!(
        column_has_ink(0, frame.width / 6),
        "no ink in the left sixth of the frame — the left paddle is missing"
    );
    assert!(
        column_has_ink(frame.width * 5 / 6, frame.width),
        "no ink in the right sixth of the frame — the right paddle is missing"
    );
    assert!(
        column_has_ink(frame.width * 2 / 5, frame.width * 3 / 5),
        "no ink in the centre — the ball is missing"
    );
}

#[test]
fn moving_a_paddle_up_moves_its_pixels_up() {
    // A relational assertion: robust to colour changes, sprite-size changes and
    // GPU differences, but still a genuine end-to-end check that input reaches
    // the screen.
    //
    // Screen y grows downward, so "up" in world space means a SMALLER pixel y.
    let hold_up = vec![
        Intents {
            left: PlayerIntent {
                up: true,
                down: false
            },
            right: PlayerIntent::default(),
        };
        60
    ];

    let still = frame_or_skip!(capture_frame(3, 60, &[]));
    let raised = frame_or_skip!(capture_frame(3, 60, &hold_up));
    let bg = background_rgb();

    // Look only at the left sixth so the ball and right paddle can't confuse us.
    let left_centroid = |frame: &Frame| -> f32 {
        let (mut sum, mut count) = (0f64, 0usize);
        for y in 0..frame.height {
            for x in 0..frame.width / 6 {
                let p = frame.pixel(x, y);
                if (0..3).any(|c| p[c].abs_diff(bg[c]) > 8) {
                    sum += f64::from(y);
                    count += 1;
                }
            }
        }
        assert!(count > 0, "left paddle not found in frame");
        (sum / count as f64) as f32
    };

    let still_y = left_centroid(&still);
    let raised_y = left_centroid(&raised);
    assert!(
        raised_y < still_y - 10.0,
        "holding 'up' for 60 ticks should raise the left paddle on screen, \
         but its centroid moved from y={still_y:.1} to y={raised_y:.1}"
    );
}

#[test]
fn rendering_is_reproducible_across_runs() {
    // Same seed, same ticks, same pixels. If this fails, either the simulation
    // is nondeterministic (check the `sim` tests first) or the render path is.
    let a = frame_or_skip!(capture_frame(4, 45, &[]));
    let b = frame_or_skip!(capture_frame(4, 45, &[]));

    let report = a.diff_report(&b, 0);
    if report.differing > 0 {
        let written = a.write_diff_artifacts(&b, artifact_base("reproducibility"), 0);
        panic!(
            "two identical runs produced different frames: {}.\n\
             Run `just test-sim` first — if those pass, the nondeterminism is in \
             the render path, not the simulation.\nWrote: {}",
            report.summary(),
            paths(&written),
        );
    }
}

/// Where failure artifacts go. Same directory as the goldens, so CI's
/// upload-artifact glob picks everything up with one pattern.
fn artifact_base(name: &str) -> String {
    format!(
        "{}/tests/golden/{name}.png",
        env!("CARGO_MANIFEST_DIR"),
        name = name
    )
}

fn paths(written: &[std::path::PathBuf]) -> String {
    written
        .iter()
        .map(|p| format!("\n  {}", p.display()))
        .collect()
}

/// Golden-image comparison.
///
/// Regenerate deliberately with `just bless`, and *look at the new image*
/// before committing it. Blessing without looking turns this test into a
/// rubber stamp.
#[test]
fn matches_golden_frame() {
    let frame = frame_or_skip!(capture_frame(5, 90, &[]));
    let golden_path = concat!(env!("CARGO_MANIFEST_DIR"), "/tests/golden/rally.png");

    if std::env::var("BLESS").is_ok() {
        frame.save_png(golden_path).expect("failed to write golden");
        eprintln!("blessed {golden_path}");
        return;
    }

    let Ok(golden) = Frame::load_png(golden_path) else {
        eprintln!(
            "SKIP: no golden image at {golden_path}. Create it with `just bless`, \
             then inspect the PNG before committing."
        );
        return;
    };

    // Tolerance absorbs cross-vendor GPU rounding, not misplaced geometry.
    // A sprite in the wrong place moves thousands of pixels, not a handful.
    let report = frame.diff_report(&golden, 4);
    if report.fraction() > 0.002 {
        let written = frame.write_diff_artifacts(&golden, golden_path, 4);
        panic!(
            "rendered frame does not match the golden image (budget 0.2% of \
             pixels).\n  {}\nWrote three images — open the diff first, magenta \
             marks every differing pixel:{}\n\n\
             A small fraction with a small max delta is GPU rounding; widen \
             nothing, re-bless nothing. A large fraction, or a tight bounding \
             box away from where you changed something, is a real bug. If the \
             change is intended, run `just bless` and LOOK at the new PNG.",
            report.summary(),
            paths(&written),
        );
    }
}
