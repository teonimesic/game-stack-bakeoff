//! HELD-OUT. The agent never sees this file.
//!
//! Grades the "draw a centre net" task by looking at actual rendered pixels.

use game::harness::capture_frame;
use game::BACKGROUND_COLOR;

fn background_rgb() -> [u8; 3] {
    let s = BACKGROUND_COLOR.to_srgba();
    [
        (s.red * 255.0).round() as u8,
        (s.green * 255.0).round() as u8,
        (s.blue * 255.0).round() as u8,
    ]
}

#[test]
fn a_centre_net_is_drawn_down_the_middle() {
    let frame = match capture_frame(11, 20, &[]) {
        Ok(f) => f,
        Err(e) => {
            eprintln!("SKIP: no GPU ({e})");
            return;
        }
    };
    let bg = background_rgb();
    let mid = frame.width / 2;

    // Count rows that have ink somewhere in a narrow band at the exact centre.
    // The ball is small and only occupies a handful of rows, so a passing score
    // here genuinely requires a full-height net.
    let lit_rows = (0..frame.height)
        .filter(|&y| {
            ((mid - 3)..=(mid + 3)).any(|x| {
                let p = frame.pixel(x, y);
                (0..3).any(|c| p[c].abs_diff(bg[c]) > 8)
            })
        })
        .count();

    let fraction = lit_rows as f32 / frame.height as f32;
    assert!(
        fraction > 0.30,
        "expected a visible net down the centre: only {lit_rows}/{} rows \
         ({:.0}%) have ink within 3px of the middle. A ball alone lights a few \
         rows; a net lights most of them.",
        frame.height,
        fraction * 100.0
    );
}

#[test]
fn the_net_does_not_cover_the_play_area() {
    let frame = match capture_frame(12, 20, &[]) {
        Ok(f) => f,
        Err(e) => {
            eprintln!("SKIP: no GPU ({e})");
            return;
        }
    };
    let coverage = frame.ink_coverage(background_rgb(), 8);
    assert!(
        coverage < 0.25,
        "{:.1}% of the frame is non-background - the net is far too wide or \
         something is covering the arena",
        coverage * 100.0
    );
}

#[test]
fn adding_the_net_did_not_break_the_paddles() {
    let frame = match capture_frame(13, 20, &[]) {
        Ok(f) => f,
        Err(e) => {
            eprintln!("SKIP: no GPU ({e})");
            return;
        }
    };
    let bg = background_rgb();
    let band_has_ink = |lo: u32, hi: u32| {
        (lo..hi).any(|x| {
            (0..frame.height).any(|y| {
                let p = frame.pixel(x, y);
                (0..3).any(|c| p[c].abs_diff(bg[c]) > 8)
            })
        })
    };
    assert!(band_has_ink(0, frame.width / 6), "left paddle disappeared");
    assert!(
        band_has_ink(frame.width * 5 / 6, frame.width),
        "right paddle disappeared"
    );
}
