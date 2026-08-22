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
use game::{BACKGROUND_COLOR, HUD_REGION, VIEW_HEIGHT, VIEW_WIDTH};
use sim::Intents;

/// Background as u8 RGB, for "is this pixel ink?" tests.
fn background_rgb() -> [u8; 3] {
    let srgb = BACKGROUND_COLOR.to_srgba();
    [
        (srgb.red * 255.0).round() as u8,
        (srgb.green * 255.0).round() as u8,
        (srgb.blue * 255.0).round() as u8,
    ]
}

/// Pixels in the HUD box that are the HUD's colour rather than the marker's.
///
/// "Something is lit in that corner" is not proof the HUD rendered — the marker
/// reaches every corner of the arena. The HUD is blue and the marker is yellow,
/// so `blue > red` separates them, anti-aliased edges included.
fn hud_ink(frame: &Frame) -> usize {
    let background = background_rgb();
    let [x0, y0, x1, y1] = HUD_REGION;
    let mut lit = 0;
    for y in y0..y1.min(frame.height) {
        for x in x0..x1.min(frame.width) {
            let pixel = frame.pixel(x, y);
            let differs = (0..3).any(|c| pixel[c].abs_diff(background[c]) > 8);
            if differs && pixel[2] > pixel[0] {
                lit += 1;
            }
        }
    }
    lit
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
fn the_marker_is_visible() {
    // Where the ink is, not just that there is some. A view that renders the
    // whole scene into one corner, or a camera framing empty space, passes the
    // coverage test above and fails this one.
    //
    // The HUD box is excluded so this measures the *arena*: the HUD is ink too,
    // it sits in a corner by design, and averaging it in would turn this into an
    // assertion about how many characters the readout happens to be printing.
    let frame = frame_or_skip!(capture_frame(2, 1, &[]));
    let (x, y) = frame
        .ink_centroid_outside(HUD_REGION, background_rgb(), 8)
        .expect("the frame is entirely background — nothing was drawn at all");

    let (width, height) = (frame.width as f32, frame.height as f32);
    assert!(
        (width / 3.0..width * 2.0 / 3.0).contains(&x)
            && (height / 3.0..height * 2.0 / 3.0).contains(&y),
        "one tick in, the ink centroid is at ({x:.1}, {y:.1}); it should still \
         be in the middle band of the {width}x{height} frame"
    );
}

#[test]
fn nudging_the_marker_up_moves_its_pixels_up() {
    // A relational assertion: robust to colour changes, sprite-size changes and
    // GPU differences, but still a genuine end-to-end check that input reaches
    // the screen.
    //
    // Screen y grows downward, so "up" in world space means a SMALLER pixel y.
    let hold_up = vec![
        Intents {
            nudge_up: true,
            nudge_down: false,
        };
        60
    ];

    let still = frame_or_skip!(capture_frame(3, 60, &[]));
    let raised = frame_or_skip!(capture_frame(3, 60, &hold_up));
    let bg = background_rgb();

    // Outside the HUD box, for the same reason as above — and here it is load
    // bearing rather than tidy: the two runs put the marker in different places,
    // so the HUD prints different text in each, and its ink would land on the
    // scale being weighed.
    let centroid_y = |frame: &Frame| -> f32 {
        frame
            .ink_centroid_outside(HUD_REGION, bg, 8)
            .expect("nothing was drawn in the frame")
            .1
    };

    let still_y = centroid_y(&still);
    let raised_y = centroid_y(&raised);
    assert!(
        raised_y < still_y - 10.0,
        "holding `nudge_up` for 60 ticks should raise the marker on screen, \
         but its centroid moved from y={still_y:.1} to y={raised_y:.1}"
    );
}

#[test]
fn the_hud_is_in_the_captured_frame() {
    // Everything the player reads has to be drawn through the camera the capture
    // reads, and this is the test that says so. If the HUD is moved onto a
    // second camera, a different render target, or any path that only ever
    // resolves to a window surface, `just film` and every test in this file go
    // on rendering an arena with no readout in it — and nothing else here
    // notices, because the arena is still perfectly correct.
    let early = frame_or_skip!(capture_frame(6, 12, &[]));
    let late = frame_or_skip!(capture_frame(6, 250, &[]));

    for (ticks, frame) in [(12u32, &early), (250, &late)] {
        let ink = hud_ink(frame);
        assert!(
            ink > 100,
            "at tick {ticks} only {ink} HUD-coloured pixels are inside the HUD \
             box {HUD_REGION:?} of the captured frame. The HUD is not reaching \
             the capture's render target: draw it with the 2D camera \
             (`Text2d`), the way `game::spawn_hud` does."
        );
    }

    // The HUD reports the tick, so two different ticks cannot paint the same
    // pixels. Without this a HUD frozen on its startup text — the readout that
    // never learned to read the simulation — passes the check above.
    let [x0, y0, x1, y1] = HUD_REGION;
    let changed = (y0..y1.min(early.height))
        .flat_map(|y| (x0..x1.min(early.width)).map(move |x| (x, y)))
        .filter(|&(x, y)| {
            let (a, b) = (early.pixel(x, y), late.pixel(x, y));
            (0..3).any(|c| a[c].abs_diff(b[c]) > 8)
        })
        .count();
    assert!(
        changed > 20,
        "the HUD box is byte-identical at tick 12 and tick 250 ({changed} \
         pixels differ). It is rendering, but it is not reading the simulation."
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
    let golden_path = concat!(env!("CARGO_MANIFEST_DIR"), "/tests/golden/frame.png");

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
