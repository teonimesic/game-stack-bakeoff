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

using System.IO;
using NUnit.Framework;
using Pong.Sim;
using Pong.View;
using UnityEngine;

namespace Pong.View.Tests
{
    public class RenderTests
    {
        private static readonly Color32 Bg = ViewConfig.BackgroundRgb;
        private const int Tol = 8;

        /// Skip rather than fail when there is no usable GPU adapter. A
        /// developer without a graphics device should not see red tests they
        /// cannot fix; CI runs them for real.
        private static Frame CaptureOrSkip(ulong seed, int ticks, Intents[] inputs = null)
        {
            try
            {
                return RenderHarness.CaptureFrame(seed, ticks, inputs);
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
            Application.dataPath, "Tests", "RenderTests", "golden", "rally.png"));

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
        public void BothPaddlesAndTheBallAreVisible()
        {
            var frame = CaptureOrSkip(2, 1);

            // Paddles sit near the left and right edges; the ball starts centred.
            Assert.IsTrue(frame.ColumnBandHasInk(Bg, Tol, 0, frame.Width / 6),
                "no ink in the left sixth of the frame — the left paddle is missing");
            Assert.IsTrue(frame.ColumnBandHasInk(Bg, Tol, frame.Width * 5 / 6, frame.Width),
                "no ink in the right sixth of the frame — the right paddle is missing");
            Assert.IsTrue(frame.ColumnBandHasInk(Bg, Tol, frame.Width * 2 / 5, frame.Width * 3 / 5),
                "no ink in the centre — the ball is missing");
        }

        [Test]
        public void MovingAPaddleUpMovesItsPixelsUp()
        {
            // A relational assertion: robust to colour changes, quad-size
            // changes and GPU differences, but still a genuine end-to-end check
            // that input reaches the screen.
            //
            // Screen y grows downward, so "up" in world space means a SMALLER
            // pixel y.
            var holdUp = new Intents[60];
            for (int i = 0; i < holdUp.Length; i++)
            {
                holdUp[i] = new Intents(new PlayerIntent(true, false), default);
            }

            var still = CaptureOrSkip(3, 60);
            var raised = CaptureOrSkip(3, 60, holdUp);

            // Look only at the left sixth so the ball and right paddle cannot
            // confuse us.
            float stillY = still.InkCentroidY(Bg, Tol, 0, still.Width / 6);
            float raisedY = raised.InkCentroidY(Bg, Tol, 0, raised.Width / 6);
            Assert.AreNotEqual(-1f, stillY, "left paddle not found in frame");
            Assert.AreNotEqual(-1f, raisedY, "left paddle not found in frame");

            Assert.Less(raisedY, stillY - 10f,
                "holding 'up' for 60 ticks should raise the left paddle on screen, " +
                $"but its centroid moved from y={stillY:F1} to y={raisedY:F1}");
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
