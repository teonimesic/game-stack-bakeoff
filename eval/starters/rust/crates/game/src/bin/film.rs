//! `film SEED TICKS SCRIPT OUTDIR` — render a run as a short strip of PNGs.
//!
//! At most [`MAX_FRAMES`] frames, evenly spaced over `0..=TICKS` inclusive and
//! always including both ends, written as `frame_0000.png`, `frame_0001.png`, …
//!
//! This is deliberately a thin wrapper over the single-frame capture the
//! rendering tests already use: one renderer, one code path, one thing to keep
//! working. Unlike `probe` it needs a GPU, for the same reason the rendering
//! tests do.

use std::process::ExitCode;

use game::harness::capture_frame;
use sim::{Intents, script};

/// Twelve is enough to see the shape of a run at a glance and cheap enough to
/// regenerate often. Each frame is a separate capture, so this is the cost knob.
const MAX_FRAMES: u32 = 12;

fn main() -> ExitCode {
    match run() {
        Ok(()) => ExitCode::SUCCESS,
        Err(why) => {
            eprintln!("film: {why}");
            ExitCode::FAILURE
        }
    }
}

fn run() -> Result<(), String> {
    let args: Vec<String> = std::env::args().skip(1).collect();
    let [seed, ticks, script_path, out_dir] = args.as_slice() else {
        return Err(
            "usage: film SEED TICKS SCRIPT OUTDIR   (SCRIPT may be '-' for no input)".to_owned(),
        );
    };
    let seed: u64 = seed
        .parse()
        .map_err(|_| format!("SEED must be a non-negative integer, got {seed:?}"))?;
    let ticks: u32 = ticks
        .parse()
        .map_err(|_| format!("TICKS must be a non-negative integer, got {ticks:?}"))?;
    let inputs = load_script(script_path)?;

    for (index, tick) in frame_ticks(ticks).into_iter().enumerate() {
        let frame = capture_frame(seed, tick, &inputs)
            .map_err(|why| format!("could not render tick {tick}: {why}"))?;
        let path = format!("{out_dir}/frame_{index:04}.png");
        frame.save_png(&path)?;
        eprintln!("tick {tick} -> {path}");
    }
    Ok(())
}

/// Evenly spaced sample points over `0..=ticks`, both ends included, at most
/// [`MAX_FRAMES`] of them. Integer division throughout so the same TICKS always
/// yields the same ticks.
fn frame_ticks(ticks: u32) -> Vec<u32> {
    let count = MAX_FRAMES.min(ticks + 1);
    if count <= 1 {
        return vec![0];
    }
    (0..count).map(|i| i * ticks / (count - 1)).collect()
}

fn load_script(path: &str) -> Result<Vec<Intents>, String> {
    if path == "-" || path.is_empty() {
        return Ok(Vec::new());
    }
    let text = std::fs::read_to_string(path).map_err(|e| format!("could not read {path}: {e}"))?;
    script::parse_script(&text).map_err(|why| format!("{path}: {why}"))
}
