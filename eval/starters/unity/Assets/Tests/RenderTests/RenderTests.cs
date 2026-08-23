// End-to-end rendering tests: the real renderer, a real GPU path, real pixels.
//
// These are the tests that catch "the code compiles, the logic is right, and
// nothing appears on screen." Unit tests on `Sim` cannot catch that class of
// bug, and it is the class that matters most in a game.
//
// Ordered from most robust to most brittle:
//   1. invariants on the pixels (something rendered; it is where we expect)
//   2. relational assertions (it moved in the right direction)
//   3. golden-image comparison (it looks exactly like the approved frame)
//
// Prefer 1 and 2. Reach for 3 only when the exact look is the thing under test.
//
// These need a graphics device, so they run in batchmode WITHOUT `-nographics`.
// `just test-render` does that; `just test-sim` keeps `-nographics` and is
// faster.

using System.Collections.Generic;
using System.IO;
using NUnit.Framework;
using Starter.Sim;
using Starter.View;
using UnityEngine;

namespace Starter.View.Tests
{
    public class RenderTests
    {
        private static readonly Color32 Bg = ViewConfig.BackgroundRgb;
        private static readonly Color32 MarkerInk = ViewConfig.MarkerRgb;
        private static readonly Color32 HudInk = ViewConfig.HudRgb;
        private const int Tol = 8;

        /// Skip rather than fail when there is no usable GPU adapter. A
        /// developer without a graphics device should not see red tests they
        /// cannot fix; CI runs them for real.
        private static Frame CaptureOrSkip(ulong seed, int ticks, Intents[] inputs = null,
                                          IReadOnlyList<Fx.Burst> bursts = null)
        {
            try
            {
                return RenderHarness.CaptureFrame(seed, ticks, inputs, bursts);
            }
            catch (NoGraphicsDeviceException e)
            {
                Assert.Ignore("SKIP: " + e.Message);
                return null;
            }
        }

        /// Golden images live next to the tests that use them, the same way the
        /// Rust and TypeScript siblings place theirs. That keeps `just bless`
        /// inside the directory a rendering change is allowed to touch.
        private static string GoldenPath => Path.GetFullPath(Path.Combine(
            Application.dataPath, "Tests", "RenderTests", "golden", "frame.png"));

        [Test]
        public void RendersANonEmptyFrame()
        {
            // The single most valuable rendering assertion there is: the
            // renderer ran and drew something other than the clear colour.
            var frame = CaptureOrSkip(1, 30);

            Assert.AreEqual(ViewConfig.VIEW_WIDTH, frame.Width);
            Assert.AreEqual(ViewConfig.VIEW_HEIGHT, frame.Height);

            float coverage = frame.InkCoverage(Bg, Tol);
            Assert.Greater(coverage, 0.001f,
                $"nothing was drawn — {coverage * 100f:F4}% of pixels differ from the " +
                "background. The simulation may be running correctly while the view is broken.");
            Assert.Less(coverage, 0.5f,
                $"{coverage * 100f:F1}% of the frame is non-background; the camera is " +
                "probably mis-scaled or a quad is covering the screen");
        }

        [Test]
        public void TheMarkerIsVisible()
        {
            // One tick in, the body has barely left the origin, so its ink must
            // be in the middle of the frame. This is the assertion that fails
            // when the camera frames empty space, or the view stops following
            // the simulation at all.
            var frame = CaptureOrSkip(2, 1);

            Assert.IsTrue(
                frame.ColumnBandHasInk(Bg, Tol, frame.Width * 2 / 5, frame.Width * 3 / 5),
                "no ink in the middle fifth of the frame — nothing is being drawn where " +
                "the simulation says the marker is");

            // Measured on the marker's own colour: the HUD is ink too, it sits
            // at the top of every frame, and it does not move.
            float centroidY = frame.ColorCentroidY(MarkerInk, Tol, 0, frame.Width);
            Assert.AreNotEqual(-1f, centroidY, "the frame is empty");
            Assert.That(centroidY, Is.InRange(frame.Height * 0.375f, frame.Height * 0.625f),
                $"ink centroid is at y={centroidY:F1}, outside the middle band of a " +
                $"{frame.Height}px frame — the view and the simulation disagree about where " +
                "the world is");
        }

        [Test]
        public void MovingTheMarkerUpMovesItsPixelsUp()
        {
            // A relational assertion: robust to colour changes, quad-size
            // changes and GPU differences, but still a genuine end-to-end check
            // that input reaches the screen.
            //
            // Screen y grows downward, so "up" in world space means a SMALLER
            // pixel y.
            var holdUp = new Intents[60];
            for (int i = 0; i < holdUp.Length; i++) holdUp[i] = new Intents(true, false);

            var still = CaptureOrSkip(3, 60);
            var raised = CaptureOrSkip(3, 60, holdUp);

            float stillY = still.ColorCentroidY(MarkerInk, Tol, 0, still.Width);
            float raisedY = raised.ColorCentroidY(MarkerInk, Tol, 0, raised.Width);
            Assert.AreNotEqual(-1f, stillY, "marker not found in frame");
            Assert.AreNotEqual(-1f, raisedY, "marker not found in frame");

            Assert.Less(raisedY, stillY - 10f,
                "holding nudge_up for 60 ticks should raise the marker on screen, " +
                $"but its centroid moved from y={stillY:F1} to y={raisedY:F1}");
        }

        [Test]
        public void TheHudIsInTheCapturedFrame()
        {
            // The HUD has to be drawn BY THE CAMERA. `camera.Render()` is the
            // only thing that writes into the texture this test reads, into the
            // golden image, and into `just film`'s PNGs — IMGUI (`OnGUI`,
            // `GUI.Label`) is emitted in another phase of the player loop
            // entirely and reaches none of them. A HUD built that way looks
            // right in a window and is absent from every frame anyone measures.
            var early = CaptureOrSkip(6, 100);
            var late = CaptureOrSkip(6, 300);

            // Asked of the HUD's own region and its own colour, so a marker that
            // happens to drift under the text cannot stand in for it.
            var region = Hud.ScreenRegion(early.Width, early.Height);
            int earlyInk = early.CountColor(HudInk, Tol, region);
            int lateInk = late.CountColor(HudInk, Tol, region);

            Assert.Greater(earlyInk, 100,
                $"only {earlyInk} HUD pixels in x=[{region.xMin},{region.xMax}] " +
                $"y=[{region.yMin},{region.yMax}] — the HUD is not in the rendered frame. " +
                "If it is drawn with OnGUI/IMGUI it never will be: draw it as geometry the " +
                "camera can see (Assets/View/Hud.cs).");
            Assert.Greater(lateInk, 100,
                $"only {lateInk} HUD pixels at tick 300 — the HUD stopped being rendered");

            // The HUD reports the tick, so two different tick counts must not
            // draw the same glyphs. This is what catches a HUD that renders but
            // has stopped following the simulation.
            int changed = HudPixelsChanged(early, late, region);
            Assert.Greater(changed, 0,
                "the HUD drew identical pixels at tick 100 and tick 300 — it is being " +
                "rendered but no longer reflects simulation state");
        }

        /// Pixels inside `region` that are HUD-coloured in one frame and not the
        /// other. Comparing masks rather than counts means two different strings
        /// with the same number of lit pixels still register as different.
        private static int HudPixelsChanged(Frame a, Frame b, RectInt region)
        {
            int changed = 0;
            for (int y = region.yMin; y < region.yMax; y++)
            {
                for (int x = region.xMin; x < region.xMax; x++)
                {
                    bool inA = !Frame.Differs(a.Pixel(x, y), HudInk, Tol);
                    bool inB = !Frame.Differs(b.Pixel(x, y), HudInk, Tol);
                    if (inA != inB) changed++;
                }
            }
            return changed;
        }

        [Test]
        public void RenderingIsReproducibleAcrossRuns()
        {
            // Same seed, same ticks, same pixels. If this fails, either the
            // simulation is nondeterministic (check the Sim tests first) or the
            // render path is.
            var a = CaptureOrSkip(4, 45);
            var b = CaptureOrSkip(4, 45);

            var diff = a.Compare(b, 0);
            if (diff.DifferingPixels > 0)
            {
                Assert.Fail(
                    "two identical runs produced different frames.\n" +
                    $"  {diff}\n" +
                    a.WriteComparisonArtifacts(b, 0, "reproducible") + "\n" +
                    "  Check the Sim tests first: if the simulation is nondeterministic the " +
                    "renderer is only the messenger.");
            }
        }

        /// The colour the burst tests emit in: deliberately neither the
        /// marker's nor the HUD's, so "burst ink" cannot be satisfied by either
        /// of them.
        private static readonly Color BurstColor = new Color(1.0f, 0.42f, 0.16f, 1f);

        /// Seeded from a fixed id, so the burst these tests draw is the same
        /// burst every time — see Assets/View/Fx.cs.
        private const int BurstId = 1;

        /// One burst at the centre of the arena, `age` seconds old.
        private static Fx.Burst[] OneBurst(float age) =>
            new[] { new Fx.Burst(Vector2.zero, BurstColor, age, BurstId) };

        [Test]
        public void ABurstIsDrawn()
        {
            // The weakest of the three burst tests and the one that has to pass
            // first: everything else here is a statement about a burst that is
            // assumed to exist.
            var bare = CaptureOrSkip(8, 20);
            var lit = CaptureOrSkip(8, 20, null, OneBurst(0.12f));

            float bareInk = bare.InkCoverage(Bg, Tol);
            float litInk = lit.InkCoverage(Bg, Tol);
            Assert.Greater(litInk, bareInk + 0.0005f,
                $"a burst added {(litInk - bareInk) * 100f:F4}% ink to a frame that already " +
                $"had {bareInk * 100f:F4}% — the particle system is not reaching the captured " +
                "frame. Check that Fx builds its emitters under GameView.Root (the camera " +
                "renders that tree) and that the burst is inside the arena.");
        }

        [Test]
        public void ABurstAges()
        {
            // THE VARIANT, not the mutant (AGENTS.md rule 15). Freezing an
            // emitter is what makes a burst reproducible, and one frozen so
            // hard it never advances at all would pass the reproducibility test
            // perfectly. Two ages have to produce two different pictures, or
            // the parameter is decorative.
            var young = CaptureOrSkip(8, 20, null, OneBurst(0.02f));
            var old = CaptureOrSkip(8, 20, null, OneBurst(0.40f));

            float diff = young.DiffFraction(old, Tol);
            Assert.Greater(diff, 0.0005f,
                $"a burst 0.02 s old and one 0.40 s old differ in only {diff * 100f:F4}% of " +
                "pixels. The age is not reaching the emitter — check that Simulate() is " +
                "called with the age in Assets/View/Fx.cs.");
        }

        [Test]
        public void RenderingIsReproducibleWithABurstOnScreen()
        {
            // Same state, same pixels — with a particle system on screen. This
            // is the one that goes red if an emitter is reading wall time.
            var a = CaptureOrSkip(9, 25, null, OneBurst(0.20f));
            var b = CaptureOrSkip(9, 25, null, OneBurst(0.20f));

            var diff = a.Compare(b, 0);
            if (diff.DifferingPixels > 0)
            {
                Assert.Fail(
                    "two identical captures holding the same burst produced different " +
                    "frames.\n" +
                    $"  {diff}\n" +
                    a.WriteComparisonArtifacts(b, 0, "reproducible-burst") + "\n" +
                    "  A particle system advancing on the frame delta is the usual cause: " +
                    "Assets/View/Fx.cs keeps playOnAwake off and a fixed seed so that only " +
                    "Simulate() can move one.");
            }
        }

        /// Golden-image comparison.
        ///
        /// Regenerate deliberately with `just bless`, and *look at the new
        /// image* before committing it. Blessing without looking turns this test
        /// into a rubber stamp.
        [Test]
        public void MatchesGoldenFrame()
        {
            var frame = CaptureOrSkip(5, 90);
            string goldenPath = GoldenPath;

            if (!string.IsNullOrEmpty(System.Environment.GetEnvironmentVariable("BLESS")))
            {
                frame.SavePng(goldenPath);
                Debug.Log("blessed " + goldenPath);
                return;
            }

            var golden = Frame.LoadPng(goldenPath);
            if (golden == null)
            {
                Assert.Ignore(
                    $"SKIP: no golden image at {goldenPath}. Create it with `just bless`, " +
                    "then inspect the PNG before committing.");
            }

            // Tolerance absorbs cross-vendor GPU rounding, not misplaced
            // geometry. A quad in the wrong place moves thousands of pixels, not
            // a handful.
            const int Tolerance = 4;
            const float Budget = 0.002f;

            var diff = frame.Compare(golden, Tolerance);
            if (diff.Fraction > Budget)
            {
                Assert.Fail(
                    "rendered frame does not match the golden image.\n" +
                    $"  {diff}\n" +
                    $"  budget: {Budget * 100f:F1}% of pixels ({(int)(Budget * diff.TotalPixels)} " +
                    $"pixels); measured {diff.Fraction * 100f:F3}%\n" +
                    frame.WriteComparisonArtifacts(golden, Tolerance, "golden") + "\n" +
                    "  Open the diff. A handful of scattered pixels is GPU rounding; a solid " +
                    "block means geometry moved. If the new look is intended, `just bless` — " +
                    "and look at the PNG before committing it.");
            }
        }
    }
}
