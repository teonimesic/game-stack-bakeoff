//! Headless observation of a run, in two forms.
//!
//! * `probe stream SEED` — a long-lived process. Writes one trace line for the
//!   world before any tick has run, then reads one JSON input object per line
//!   from stdin, steps exactly one tick per line, and writes one trace line per
//!   tick. Flushes after every line, so a driver can read the state it just
//!   caused and decide what to send next. EOF or a line reading `quit` exits 0.
//! * `probe file SEED TICKS SCRIPT OUT` — the batch form. Replays a whole
//!   script and writes the trace to a file.
//!
//! **stdout carries nothing but trace lines.** Everything else goes to stderr:
//! a stray banner on stdout desynchronises whatever is reading it.
//!
//! Both forms are the same loop over [`sim::replay::headless_app`], so a trace
//! is exactly what the determinism tests hash — no second implementation of the
//! tick loop to drift out of sync.

use std::io::{self, BufRead, Write};
use std::process::ExitCode;

use bevy_app::App;
use bevy_ecs::prelude::With;
use sim::replay::headless_app;
use sim::{Intents, Marker, Position, Tick, TickEvents, Velocity, script, state_hash};

fn main() -> ExitCode {
    match run() {
        Ok(()) => ExitCode::SUCCESS,
        Err(why) => {
            eprintln!("probe: {why}");
            ExitCode::FAILURE
        }
    }
}

const USAGE: &str = "usage:\n  \
     probe stream SEED\n  \
     probe file SEED TICKS SCRIPT OUT   (SCRIPT may be '-' for no input)";

fn run() -> Result<(), String> {
    let args: Vec<String> = std::env::args().skip(1).collect();
    match args.iter().map(String::as_str).collect::<Vec<_>>()[..] {
        ["stream", seed] => stream(parse_u64(seed, "SEED")?),
        ["file", seed, ticks, path, out] => batch(
            parse_u64(seed, "SEED")?,
            usize::try_from(parse_u64(ticks, "TICKS")?).map_err(|_| "TICKS is too large")?,
            path,
            out,
        ),
        _ => Err(format!("bad arguments.\n{USAGE}")),
    }
}

fn parse_u64(text: &str, what: &str) -> Result<u64, String> {
    text.parse()
        .map_err(|_| format!("{what} must be a non-negative integer, got {text:?}"))
}

/// Interactive form: one input line in, one trace line out, flushed every time.
fn stream(seed: u64) -> Result<(), String> {
    let mut app = headless_app(seed);
    let stdout = io::stdout();
    let mut out = stdout.lock();

    emit(&mut out, &mut app)?;

    for line in io::stdin().lock().lines() {
        let line = line.map_err(|e| format!("could not read stdin: {e}"))?;
        if line.trim() == "quit" {
            break;
        }
        let intents = script::parse_intents(&line)?;
        step(&mut app, intents);
        emit(&mut out, &mut app)?;
    }
    Ok(())
}

/// Batch form: replay a whole script, then write the trace in one go.
fn batch(seed: u64, ticks: usize, script_path: &str, out_path: &str) -> Result<(), String> {
    let inputs = load_script(script_path)?;
    let mut app = headless_app(seed);
    let mut trace = String::new();

    for tick in 0..ticks {
        step(&mut app, inputs.get(tick).copied().unwrap_or_default());
        trace.push_str(&trace_line(&mut app)?);
        trace.push('\n');
    }

    let reached = app.world().resource::<Tick>().0;
    if reached != ticks as u64 {
        return Err(format!(
            "asked for {ticks} ticks, the simulation reached {reached}"
        ));
    }

    std::fs::write(out_path, trace).map_err(|e| format!("could not write {out_path}: {e}"))
}

fn load_script(path: &str) -> Result<Vec<Intents>, String> {
    if path == "-" || path.is_empty() {
        return Ok(Vec::new());
    }
    let text = std::fs::read_to_string(path).map_err(|e| format!("could not read {path}: {e}"))?;
    script::parse_script(&text).map_err(|why| format!("{path}: {why}"))
}

fn step(app: &mut App, intents: Intents) {
    *app.world_mut().resource_mut::<Intents>() = intents;
    app.update();
}

fn emit(out: &mut impl Write, app: &mut App) -> Result<(), String> {
    let line = trace_line(app)?;
    writeln!(out, "{line}").map_err(|e| format!("could not write to stdout: {e}"))?;
    out.flush()
        .map_err(|e| format!("could not flush stdout: {e}"))
}

/// One JSON Lines record: `{"tick": N, "hash": "0x…", "state": {…}, "events": […]}`.
///
/// `state` is game-defined. Expose the values that describe what the game is
/// doing right now, keep the shape stable, and keep every number finite.
fn trace_line(app: &mut App) -> Result<String, String> {
    let tick = app.world().resource::<Tick>().0;
    let events = app.world().resource::<TickEvents>().events.clone();
    let hash = state_hash(app.world_mut());

    let mut markers = app
        .world_mut()
        .query_filtered::<(&Position, &Velocity), With<Marker>>();
    let (position, velocity) = markers
        .iter(app.world())
        .next()
        .ok_or("the world contains no marker to report on")?;

    let state = format!(
        r#"{{"marker": {{"x": {}, "y": {}, "vx": {}, "vy": {}}}}}"#,
        number(position.0.x)?,
        number(position.0.y)?,
        number(velocity.0.x)?,
        number(velocity.0.y)?,
    );

    let events = events
        .iter()
        .map(|name| json_string(name))
        .collect::<Vec<_>>()
        .join(", ");

    Ok(format!(
        r#"{{"tick": {tick}, "hash": "0x{hash:016x}", "state": {state}, "events": [{events}]}}"#
    ))
}

/// f32 as a finite JSON number. `{:?}` on an f32 is the shortest decimal that
/// round-trips and always carries a `.` or an exponent, so it is both exact and
/// valid JSON. NaN and infinity are errors, not values: they mean the
/// simulation has already diverged and a consumer cannot parse them anyway.
fn number(value: f32) -> Result<String, String> {
    if value.is_finite() {
        Ok(format!("{value:?}"))
    } else {
        Err(format!(
            "the simulation produced a non-finite value ({value}); a trace must \
             contain only finite JSON numbers"
        ))
    }
}

fn json_string(text: &str) -> String {
    let mut out = String::with_capacity(text.len() + 2);
    out.push('"');
    for ch in text.chars() {
        match ch {
            '"' => out.push_str("\\\""),
            '\\' => out.push_str("\\\\"),
            '\n' => out.push_str("\\n"),
            '\r' => out.push_str("\\r"),
            '\t' => out.push_str("\\t"),
            c if (c as u32) < 0x20 => out.push_str(&format!("\\u{:04x}", c as u32)),
            c => out.push(c),
        }
    }
    out.push('"');
    out
}
