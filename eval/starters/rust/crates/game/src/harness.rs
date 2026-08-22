//! Headless render harness — the template's answer to "prove it actually drew
//! something".
//!
//! Runs the real renderer with no window, into an offscreen texture, reads the
//! pixels back to the CPU, and hands them to a test. This is a genuine GPU path:
//! shaders run, the camera projects, sprites rasterise. It is not a mock.
//!
//! Works on macOS (Metal), Windows (DX12/Vulkan) and Linux (Vulkan, or lavapipe
//! for CPU-only CI runners). No display required.

use std::sync::{Arc, Mutex};
use std::time::Duration;

use bevy::app::ScheduleRunnerPlugin;
use bevy::camera::RenderTarget;
use bevy::image::{Image, TextureFormatPixelInfo};
use bevy::prelude::*;
use bevy::render::gpu_readback::{Readback, ReadbackComplete};
use bevy::render::render_resource::{TextureFormat, TextureUsages};
use bevy::window::ExitCondition;
use bevy::winit::WinitPlugin;
use sim::{Intents, SimPlugin, SimRng, TICK_HZ, Tick};

use crate::{ViewPlugin, arena_camera};

/// A captured frame: tightly packed RGBA8, `width * height * 4` bytes.
#[derive(Debug, Clone)]
pub struct Frame {
    pub width: u32,
    pub height: u32,
    pub rgba: Vec<u8>,
}

impl Frame {
    pub fn pixel(&self, x: u32, y: u32) -> [u8; 4] {
        let index = ((y * self.width + x) * 4) as usize;
        [
            self.rgba[index],
            self.rgba[index + 1],
            self.rgba[index + 2],
            self.rgba[index + 3],
        ]
    }

    /// Fraction of pixels that are not the background colour. A cheap, robust
    /// "did anything actually render?" signal that does not depend on a golden
    /// file and does not break when colours are tweaked.
    pub fn ink_coverage(&self, background: [u8; 3], tolerance: u8) -> f32 {
        let mut lit = 0usize;
        for pixel in self.rgba.chunks_exact(4) {
            let differs =
                (0..3).any(|channel| pixel[channel].abs_diff(background[channel]) > tolerance);
            if differs {
                lit += 1;
            }
        }
        lit as f32 / (self.width * self.height) as f32
    }

    /// Centre of mass of non-background pixels, in pixel coordinates.
    /// Returns `None` if the frame is empty.
    ///
    /// This is how you assert "it moved right" without a golden image and
    /// without caring about exact pixel values.
    pub fn ink_centroid(&self, background: [u8; 3], tolerance: u8) -> Option<(f32, f32)> {
        self.centroid(background, tolerance, |_, _| true)
    }

    /// Centre of mass of the non-background pixels **outside** `region`, a
    /// half-open pixel box `[x0, y0, x1, y1]`.
    ///
    /// Reach for this the moment a fixed overlay shares the frame with the thing
    /// you are measuring. [`Frame::ink_centroid`] averages the HUD in with the
    /// scene, so a HUD whose text is one character longer in one of two runs
    /// reads as scene movement that never happened — and the assertion's
    /// headroom silently becomes a function of how much the HUD says.
    pub fn ink_centroid_outside(
        &self,
        region: [u32; 4],
        background: [u8; 3],
        tolerance: u8,
    ) -> Option<(f32, f32)> {
        let [x0, y0, x1, y1] = region;
        self.centroid(background, tolerance, |x, y| {
            !((x0..x1).contains(&x) && (y0..y1).contains(&y))
        })
    }

    /// Number of non-background pixels inside `region`, a half-open pixel box
    /// `[x0, y0, x1, y1]`.
    ///
    /// This is the assertion for anything drawn at a fixed place on screen — a
    /// HUD, a scoreboard, a countdown. Whole-frame coverage cannot answer "is it
    /// still on screen?", because the arena's own sprites swamp the count.
    pub fn ink_pixels_in(&self, region: [u32; 4], background: [u8; 3], tolerance: u8) -> usize {
        let [x0, y0, x1, y1] = region;
        let mut lit = 0usize;
        for y in y0..y1.min(self.height) {
            for x in x0..x1.min(self.width) {
                if self.is_ink(x, y, background, tolerance) {
                    lit += 1;
                }
            }
        }
        lit
    }

    fn is_ink(&self, x: u32, y: u32, background: [u8; 3], tolerance: u8) -> bool {
        let pixel = self.pixel(x, y);
        (0..3).any(|channel| pixel[channel].abs_diff(background[channel]) > tolerance)
    }

    fn centroid(
        &self,
        background: [u8; 3],
        tolerance: u8,
        keep: impl Fn(u32, u32) -> bool,
    ) -> Option<(f32, f32)> {
        let (mut sum_x, mut sum_y, mut count) = (0f64, 0f64, 0usize);
        for y in 0..self.height {
            for x in 0..self.width {
                if keep(x, y) && self.is_ink(x, y, background, tolerance) {
                    sum_x += f64::from(x);
                    sum_y += f64::from(y);
                    count += 1;
                }
            }
        }
        (count > 0).then(|| ((sum_x / count as f64) as f32, (sum_y / count as f64) as f32))
    }

    /// Fraction of pixels whose colour differs from `other` by more than
    /// `tolerance` on any channel.
    ///
    /// Tolerance exists because GPUs are not bit-identical across vendors,
    /// drivers, or backends — the same scene rendered on Metal and on lavapipe
    /// will differ in the last bit or two of a gradient. Tolerance does NOT
    /// exist to paper over a sprite being in the wrong place; that shows up as a
    /// large fraction, not a small one.
    pub fn diff_fraction(&self, other: &Frame, tolerance: u8) -> f32 {
        self.diff_report(other, tolerance).fraction()
    }

    /// Where and how much two frames differ. Use this over [`Frame::diff_fraction`]
    /// in an assertion message: "0.9% of pixels differ" tells an agent nothing,
    /// "3 412 pixels differ, all inside x 316..324 — a 8px-wide vertical band in
    /// the centre" tells it what it drew.
    pub fn diff_report(&self, other: &Frame, tolerance: u8) -> DiffReport {
        assert_eq!(
            (self.width, self.height),
            (other.width, other.height),
            "cannot diff frames of different sizes ({}x{} vs {}x{})",
            self.width,
            self.height,
            other.width,
            other.height
        );
        let mut report = DiffReport {
            differing: 0,
            total: (self.width * self.height) as usize,
            bounds: None,
            max_channel_delta: 0,
        };
        for y in 0..self.height {
            for x in 0..self.width {
                let (a, b) = (self.pixel(x, y), other.pixel(x, y));
                let delta = (0..3).map(|c| a[c].abs_diff(b[c])).max().unwrap_or(0);
                report.max_channel_delta = report.max_channel_delta.max(delta);
                if delta > tolerance {
                    report.differing += 1;
                    report.bounds = Some(match report.bounds {
                        None => (x, y, x, y),
                        Some((x0, y0, x1, y1)) => (x0.min(x), y0.min(y), x1.max(x), y1.max(y)),
                    });
                }
            }
        }
        report
    }

    /// A human-readable diff image: `self` dimmed to a grey backdrop, with every
    /// pixel that differs from `other` painted opaque magenta. Open it and the
    /// shape of the failure is obvious in a second — a shifted sprite is a pair
    /// of blobs, a colour tweak is a solid silhouette, a missing entity is one
    /// blob.
    pub fn diff_image(&self, other: &Frame, tolerance: u8) -> Frame {
        let mut rgba = Vec::with_capacity(self.rgba.len());
        for y in 0..self.height {
            for x in 0..self.width {
                let (a, b) = (self.pixel(x, y), other.pixel(x, y));
                if (0..3).any(|c| a[c].abs_diff(b[c]) > tolerance) {
                    rgba.extend_from_slice(&[255, 0, 255, 255]);
                } else {
                    let grey = (u16::from(a[0]) + u16::from(a[1]) + u16::from(a[2])) / 3;
                    let dim = (grey / 3) as u8;
                    rgba.extend_from_slice(&[dim, dim, dim, 255]);
                }
            }
        }
        Frame {
            width: self.width,
            height: self.height,
            rgba,
        }
    }

    /// Write `<stem>.actual.png`, `<stem>.expected.png` and `<stem>.diff.png`
    /// next to `reference_path`, and return their absolute paths.
    ///
    /// Call this on any failing pixel assertion. A test that says "the image is
    /// wrong" and leaves nothing on disk costs a whole turn to reproduce; CI
    /// uploads these three files as artifacts.
    pub fn write_diff_artifacts(
        &self,
        expected: &Frame,
        reference_path: impl AsRef<std::path::Path>,
        tolerance: u8,
    ) -> Vec<std::path::PathBuf> {
        let reference = reference_path.as_ref();
        let stem = reference.with_extension("");
        let mut written = Vec::new();
        let mut put = |suffix: &str, frame: &Frame| {
            let path = std::path::PathBuf::from(format!("{}.{suffix}.png", stem.display()));
            if frame.save_png(&path).is_ok() {
                written.push(path.canonicalize().unwrap_or(path));
            }
        };
        put("actual", self);
        put("expected", expected);
        put("diff", &self.diff_image(expected, tolerance));
        written
    }

    pub fn save_png(&self, path: impl AsRef<std::path::Path>) -> Result<(), String> {
        let path = path.as_ref();
        if let Some(parent) = path.parent() {
            std::fs::create_dir_all(parent).map_err(|e| e.to_string())?;
        }
        image::save_buffer(
            path,
            &self.rgba,
            self.width,
            self.height,
            image::ColorType::Rgba8,
        )
        .map_err(|e| e.to_string())
    }

    pub fn load_png(path: impl AsRef<std::path::Path>) -> Result<Frame, String> {
        let img = image::open(path.as_ref())
            .map_err(|e| e.to_string())?
            .to_rgba8();
        Ok(Frame {
            width: img.width(),
            height: img.height(),
            rgba: img.into_raw(),
        })
    }
}

/// Quantified result of comparing two frames. Every field exists to answer a
/// question an agent will otherwise have to spend a turn answering by hand.
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct DiffReport {
    /// Pixels differing by more than the tolerance on at least one channel.
    pub differing: usize,
    pub total: usize,
    /// Inclusive pixel bounding box `(x0, y0, x1, y1)` of the differing region.
    /// `None` when the frames match.
    pub bounds: Option<(u32, u32, u32, u32)>,
    /// Largest per-channel difference anywhere, tolerance ignored. A value of a
    /// few units is GPU rounding; a value near 255 is a different picture.
    pub max_channel_delta: u8,
}

impl DiffReport {
    pub fn fraction(&self) -> f32 {
        self.differing as f32 / self.total as f32
    }

    /// One line, with numbers, suitable for pasting straight into a panic
    /// message.
    pub fn summary(&self) -> String {
        match self.bounds {
            None => format!("identical (max channel delta {})", self.max_channel_delta),
            Some((x0, y0, x1, y1)) => format!(
                "{} of {} pixels differ ({:.3}%), max channel delta {}, \
                 all inside x {}..={} y {}..={} ({}x{} px region)",
                self.differing,
                self.total,
                self.fraction() * 100.0,
                self.max_channel_delta,
                x0,
                x1,
                y0,
                y1,
                x1 - x0 + 1,
                y1 - y0 + 1,
            ),
        }
    }
}

#[derive(Resource, Clone)]
struct CaptureSink(Arc<Mutex<Option<Vec<u8>>>>);

#[derive(Resource)]
struct CaptureTarget {
    width: u32,
    height: u32,
}

/// Render the simulation headlessly and capture one frame after `ticks`
/// simulation ticks.
///
/// The simulation is advanced with the same fixed-timestep discipline the pure
/// `sim` tests use, so the rendered frame corresponds to an exactly known tick —
/// there is no "roughly one second in" ambiguity.
pub fn capture_frame(seed: u64, ticks: u32, inputs: &[Intents]) -> Result<Frame, String> {
    capture_frame_sized(seed, ticks, inputs, crate::VIEW_WIDTH, crate::VIEW_HEIGHT)
}

pub fn capture_frame_sized(
    seed: u64,
    ticks: u32,
    inputs: &[Intents],
    width: u32,
    height: u32,
) -> Result<Frame, String> {
    let sink = CaptureSink(Arc::new(Mutex::new(None)));

    let mut app = App::new();
    app.add_plugins(
        DefaultPlugins
            .set(WindowPlugin {
                // No window at all. This is what makes the harness runnable on a
                // CI box with no display.
                primary_window: None,
                exit_condition: ExitCondition::DontExit,
                ..default()
            })
            // Winit owns the event loop and would take over `run()`. Without a
            // window we drive the loop ourselves.
            .disable::<WinitPlugin>()
            // Several harness apps may exist in one test binary; only the first
            // can install the global tracing subscriber, and the rest log an
            // alarming-looking error. We don't need logs here.
            .disable::<bevy::log::LogPlugin>(),
    )
    .add_plugins(ScheduleRunnerPlugin::run_loop(Duration::ZERO))
    .add_plugins(SimPlugin)
    .add_plugins(ViewPlugin)
    .insert_resource(bevy::time::Time::<bevy::time::Fixed>::from_hz(f64::from(
        TICK_HZ,
    )))
    .insert_resource(bevy::time::TimeUpdateStrategy::FixedTimesteps(1))
    .insert_resource(SimRng::from_seed(seed))
    .insert_resource(sink.clone())
    .insert_resource(CaptureTarget { width, height })
    .add_systems(Startup, setup_capture);

    app.finish();
    app.cleanup();

    // Warm-up: Startup runs, zero fixed ticks (see sim::replay::headless_app).
    app.update();

    for tick in 0..ticks {
        let intents = inputs.get(tick as usize).copied().unwrap_or_default();
        *app.world_mut().resource_mut::<Intents>() = intents;
        app.update();
    }

    let reached = app.world().resource::<Tick>().0;
    if reached != u64::from(ticks) {
        return Err(format!(
            "expected {ticks} ticks before capture, simulation reported {reached}"
        ));
    }

    // Freeze the simulation, then pump render frames until the picture SETTLES.
    //
    // MEASURED (this is the fix for the template's worst flake): taking the
    // first readback that arrives is not enough. Readback is asynchronous, and
    // on top of that wgpu compiles render pipelines lazily, so the first frames
    // out of a freshly-created App can be a bare clear colour with no sprites
    // in them. The symptom is a render test that fails on the FIRST run after a
    // build and passes on every run after — measured 2 first-run failures in 2
    // cold runs, 0 in the 2 warm runs that followed, in two *different* tests.
    // An agent sees a red `just verify` it did not cause.
    //
    // With the simulation frozen the scene is static, so "two consecutive
    // readbacks are byte-identical" is a sound settling criterion: it cannot be
    // satisfied while pipelines are still coming online and frames are still
    // changing. The minimum-frames floor stops two identical *empty* frames
    // from qualifying.
    const MIN_SETTLE_FRAMES: usize = 8;
    const MAX_SETTLE_FRAMES: usize = 240;

    app.world_mut()
        .insert_resource(bevy::time::TimeUpdateStrategy::FixedTimesteps(0));
    *sink.0.lock().unwrap() = None;

    let mut previous: Option<Vec<u8>> = None;
    let mut settled: Option<Vec<u8>> = None;
    for frame in 0..MAX_SETTLE_FRAMES {
        app.update();
        let Some(latest) = sink.0.lock().unwrap().take() else {
            continue;
        };
        if frame >= MIN_SETTLE_FRAMES && previous.as_ref() == Some(&latest) {
            settled = Some(latest);
            break;
        }
        previous = Some(latest);
    }

    // Falling back to the last readback rather than erroring: on a very slow
    // software rasteriser the frames may still be identical without our having
    // seen two in a row, and a usable frame beats a spurious failure.
    let data = settled.or(previous).ok_or_else(|| {
        "GPU readback never completed — no adapter, or the render \
                        target was never drawn"
            .to_string()
    })?;

    let expected = (width * height * 4) as usize;
    if data.len() < expected {
        return Err(format!(
            "readback returned {} bytes, expected at least {expected}",
            data.len()
        ));
    }

    Ok(Frame {
        width,
        height,
        rgba: data[..expected].to_vec(),
    })
}

fn setup_capture(
    mut commands: Commands,
    mut images: ResMut<Assets<Image>>,
    target: Res<CaptureTarget>,
) {
    let format = TextureFormat::Rgba8UnormSrgb;
    let mut image = Image::new_target_texture(target.width, target.height, format, None);
    // `new_target_texture` sets the flags needed to *render into* the image.
    // Reading it back additionally requires COPY_SRC.
    image.texture_descriptor.usage |= TextureUsages::COPY_SRC;
    debug_assert!(
        format.pixel_size().is_ok_and(|size| size == 4),
        "harness assumes 4 bytes per pixel"
    );

    let handle = images.add(image);
    commands.spawn(arena_camera(RenderTarget::Image(handle.clone().into())));
    commands
        .spawn(Readback::texture(handle))
        // Always overwrite: readback fires every rendered frame, and we want the
        // MOST RECENT one. Keeping the first would capture the warm-up frame,
        // rendered before any views had been spawned — an empty screen that
        // looks like a broken renderer.
        .observe(|event: On<ReadbackComplete>, sink: Res<CaptureSink>| {
            *sink.0.lock().unwrap() = Some(event.data.clone());
        });
}
