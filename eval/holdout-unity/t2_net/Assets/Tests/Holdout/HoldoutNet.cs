// HELD-OUT. The agent never sees this file.
// Grades the "draw a centre net" task by looking at real rendered pixels.
using NUnit.Framework;
using Pong.Sim;
using UnityEngine;
using Pong.View;

namespace Pong.Holdout
{
    public class HoldoutNet
    {
        static readonly Color32 Bg = ViewConfig.BackgroundRgb;
        const int Tol = 8;

        static Frame CaptureOrSkip(ulong seed, int ticks)
        {
            try { return RenderHarness.CaptureFrame(seed, ticks, null); }
            catch (System.Exception e) { Assert.Ignore($"no usable graphics device: {e.Message}"); return null; }
        }

        static bool IsInk(Frame f, int x, int y)
        {
            var p = f.Pixel(x, y);
            return System.Math.Abs(p.r - Bg.r) > Tol
                || System.Math.Abs(p.g - Bg.g) > Tol
                || System.Math.Abs(p.b - Bg.b) > Tol;
        }

        [Test]
        public void ACentreNetIsDrawnDownTheMiddle()
        {
            var frame = CaptureOrSkip(11, 20);
            int mid = frame.Width / 2, litRows = 0;
            for (int y = 0; y < frame.Height; y++)
                for (int x = mid - 3; x <= mid + 3; x++)
                    if (IsInk(frame, x, y)) { litRows++; break; }

            float fraction = (float)litRows / frame.Height;
            Assert.Greater(fraction, 0.30f,
                $"expected a visible net: only {litRows}/{frame.Height} rows " +
                $"({fraction * 100:F0}%) have ink within 3px of the middle. A ball " +
                "alone lights a few rows; a net lights most of them.");
        }

        [Test]
        public void TheNetDoesNotCoverThePlayArea()
        {
            var frame = CaptureOrSkip(12, 20);
            float coverage = frame.InkCoverage(Bg, Tol);
            Assert.Less(coverage, 0.25f,
                $"{coverage * 100:F1}% of the frame is non-background - the net is far too wide");
        }

        [Test]
        public void AddingTheNetDidNotBreakThePaddles()
        {
            var frame = CaptureOrSkip(13, 20);
            bool BandHasInk(int lo, int hi)
            {
                for (int x = lo; x < hi; x++)
                    for (int y = 0; y < frame.Height; y++)
                        if (IsInk(frame, x, y)) return true;
                return false;
            }
            Assert.IsTrue(BandHasInk(0, frame.Width / 6), "left paddle disappeared");
            Assert.IsTrue(BandHasInk(frame.Width * 5 / 6, frame.Width), "right paddle disappeared");
        }
    }
}
