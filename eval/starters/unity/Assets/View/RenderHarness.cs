// Headless render harness — the template's answer to "prove it actually drew
// something".
//
// Runs the real renderer with no window, into an offscreen RenderTexture, reads
// the pixels back to the CPU, and hands them to a test. This is a genuine GPU
// path: shaders run, the camera projects, quads rasterise. It is not a mock.
//
// Verified working in `Unity -batchmode` on macOS (Metal). It requires a
// graphics device, so render tests must run WITHOUT `-nographics`; `just
// test-render` does exactly that.

using System.IO;
using Starter.Sim;
using UnityEngine;

namespace Starter.View
{
    /// A captured frame: tightly packed RGBA8, width * height * 4 bytes, with
    /// row 0 at the TOP of the image (screen convention: y grows downward).
    /// `Texture2D.ReadPixels` returns bottom-up, so `Capture` flips.
    public sealed class Frame
    {
        public readonly int Width;
        public readonly int Height;
        public readonly byte[] Rgba;

        public Frame(int width, int height, byte[] rgba)
        {
            Width = width;
            Height = height;
            Rgba = rgba;
        }

        public Color32 Pixel(int x, int y)
        {
            int i = (y * Width + x) * 4;
            return new Color32(Rgba[i], Rgba[i + 1], Rgba[i + 2], Rgba[i + 3]);
        }

        public static bool Differs(Color32 a, Color32 b, int tolerance) =>
            Mathf.Abs(a.r - b.r) > tolerance ||
            Mathf.Abs(a.g - b.g) > tolerance ||
            Mathf.Abs(a.b - b.b) > tolerance;

        /// Fraction of pixels that are not the background colour. A cheap,
        /// robust "did anything actually render?" signal that does not depend on
        /// a golden file and does not break when colours are tweaked.
        public float InkCoverage(Color32 background, int tolerance)
        {
            int lit = 0;
            for (int y = 0; y < Height; y++)
            {
                for (int x = 0; x < Width; x++)
                {
                    if (Differs(Pixel(x, y), background, tolerance)) lit++;
                }
            }
            return lit / (float)(Width * Height);
        }

        /// Mean y of non-background pixels within a column band, or -1 if empty.
        /// This is how you assert "it moved up" without a golden image.
        public float InkCentroidY(Color32 background, int tolerance, int xLo, int xHi)
        {
            double sum = 0;
            int count = 0;
            for (int y = 0; y < Height; y++)
            {
                for (int x = xLo; x < xHi; x++)
                {
                    if (Differs(Pixel(x, y), background, tolerance)) { sum += y; count++; }
                }
            }
            return count == 0 ? -1f : (float)(sum / count);
        }

        /// Mean y of pixels that MATCH `color`, or -1 if there are none.
        ///
        /// Once a frame holds more than one thing — bodies and a HUD — "not the
        /// background" stops meaning "the marker". Asking for a colour keeps a
        /// relational assertion about one object measuring that object, and not
        /// the static ink somewhere else in the frame.
        public float ColorCentroidY(Color32 color, int tolerance, int xLo, int xHi)
        {
            double sum = 0;
            int count = 0;
            for (int y = 0; y < Height; y++)
            {
                for (int x = xLo; x < xHi; x++)
                {
                    if (!Differs(Pixel(x, y), color, tolerance)) { sum += y; count++; }
                }
            }
            return count == 0 ? -1f : (float)(sum / count);
        }

        /// How many pixels inside `rect` match `color`. "Is the HUD on screen?"
        /// is exactly this question asked about the HUD's own region.
        public int CountColor(Color32 color, int tolerance, RectInt rect)
        {
            int count = 0;
            for (int y = rect.yMin; y < rect.yMax; y++)
            {
                for (int x = rect.xMin; x < rect.xMax; x++)
                {
                    if (!Differs(Pixel(x, y), color, tolerance)) count++;
                }
            }
            return count;
        }

        public bool ColumnBandHasInk(Color32 background, int tolerance, int xLo, int xHi)
        {
            for (int y = 0; y < Height; y++)
            {
                for (int x = xLo; x < xHi; x++)
                {
                    if (Differs(Pixel(x, y), background, tolerance)) return true;
                }
            }
            return false;
        }

        /// Fraction of pixels whose colour differs from `other` by more than
        /// `tolerance` on any channel.
        ///
        /// Tolerance exists because GPUs are not bit-identical across vendors,
        /// drivers, or backends. Tolerance does NOT exist to paper over a sprite
        /// being in the wrong place; that shows up as a large fraction, not a
        /// small one.
        public float DiffFraction(Frame other, int tolerance) => Compare(other, tolerance).Fraction;

        /// Full comparison: how many pixels differ, by how much, and WHERE.
        ///
        /// "0.4% of pixels differ" does not tell an agent what to do next.
        /// "1021 pixels differ, all inside x=[312,328] y=[0,400], worst channel
        /// delta 214" says "something appeared in a vertical strip down the
        /// middle" — which is a diagnosis.
        public DiffReport Compare(Frame other, int tolerance)
        {
            if (Width != other.Width || Height != other.Height)
            {
                throw new System.ArgumentException(
                    $"cannot diff frames of different sizes: {Width}x{Height} vs " +
                    $"{other.Width}x{other.Height}");
            }

            var report = new DiffReport { TotalPixels = Width * Height };
            double sumX = 0, sumY = 0;
            for (int y = 0; y < Height; y++)
            {
                for (int x = 0; x < Width; x++)
                {
                    var a = Pixel(x, y);
                    var b = other.Pixel(x, y);
                    int delta = Mathf.Max(Mathf.Abs(a.r - b.r),
                        Mathf.Max(Mathf.Abs(a.g - b.g), Mathf.Abs(a.b - b.b)));
                    if (delta <= tolerance) continue;

                    report.DifferingPixels++;
                    report.MaxChannelDelta = Mathf.Max(report.MaxChannelDelta, delta);
                    report.MinX = Mathf.Min(report.MinX, x);
                    report.MaxX = Mathf.Max(report.MaxX, x);
                    report.MinY = Mathf.Min(report.MinY, y);
                    report.MaxY = Mathf.Max(report.MaxY, y);
                    sumX += x;
                    sumY += y;
                }
            }
            if (report.DifferingPixels > 0)
            {
                report.CentroidX = (float)(sumX / report.DifferingPixels);
                report.CentroidY = (float)(sumY / report.DifferingPixels);
            }
            return report;
        }

        /// A frame where every differing pixel is magenta and everything else is
        /// the actual frame at quarter brightness, so the eye lands on the
        /// difference immediately.
        public Frame DiffImage(Frame other, int tolerance)
        {
            var rgba = new byte[Width * Height * 4];
            for (int y = 0; y < Height; y++)
            {
                for (int x = 0; x < Width; x++)
                {
                    var a = Pixel(x, y);
                    int i = (y * Width + x) * 4;
                    if (Differs(a, other.Pixel(x, y), tolerance))
                    {
                        rgba[i] = 255; rgba[i + 1] = 0; rgba[i + 2] = 255; rgba[i + 3] = 255;
                    }
                    else
                    {
                        rgba[i] = (byte)(a.r / 4); rgba[i + 1] = (byte)(a.g / 4);
                        rgba[i + 2] = (byte)(a.b / 4); rgba[i + 3] = 255;
                    }
                }
            }
            return new Frame(Width, Height, rgba);
        }

        /// Write actual / expected / diff next to each other and return the
        /// paths, so a failure message can point at real files.
        public string WriteComparisonArtifacts(Frame expected, int tolerance, string name)
        {
            string dir = Path.GetFullPath(Path.Combine(
                Application.dataPath, "..", "artifacts", "render"));
            string actualPath = Path.Combine(dir, name + ".actual.png");
            string expectedPath = Path.Combine(dir, name + ".expected.png");
            string diffPath = Path.Combine(dir, name + ".diff.png");

            SavePng(actualPath);
            expected.SavePng(expectedPath);
            DiffImage(expected, tolerance).SavePng(diffPath);

            return $"  actual:   {actualPath}\n" +
                   $"  expected: {expectedPath}\n" +
                   $"  diff:     {diffPath}  (magenta = differing pixels)";
        }

        public void SavePng(string path)
        {
            var dir = Path.GetDirectoryName(path);
            if (!string.IsNullOrEmpty(dir)) Directory.CreateDirectory(dir);
            var texture = new Texture2D(Width, Height, TextureFormat.RGBA32, false);
            // Texture2D rows are bottom-up; our rows are top-down.
            var flipped = new byte[Rgba.Length];
            int stride = Width * 4;
            for (int y = 0; y < Height; y++)
            {
                System.Array.Copy(Rgba, y * stride, flipped, (Height - 1 - y) * stride, stride);
            }
            texture.LoadRawTextureData(flipped);
            texture.Apply();
            File.WriteAllBytes(path, texture.EncodeToPNG());
            Object.DestroyImmediate(texture);
        }

        public static Frame LoadPng(string path)
        {
            if (!File.Exists(path)) return null;
            var texture = new Texture2D(2, 2, TextureFormat.RGBA32, false);
            if (!texture.LoadImage(File.ReadAllBytes(path)))
            {
                Object.DestroyImmediate(texture);
                return null;
            }
            var frame = FromTexture(texture);
            Object.DestroyImmediate(texture);
            return frame;
        }

        internal static Frame FromTexture(Texture2D texture)
        {
            var pixels = texture.GetPixels32();
            int w = texture.width, h = texture.height;
            var rgba = new byte[w * h * 4];
            for (int y = 0; y < h; y++)
            {
                for (int x = 0; x < w; x++)
                {
                    // GetPixels32 is bottom-up; Frame is top-down.
                    var p = pixels[(h - 1 - y) * w + x];
                    int i = (y * w + x) * 4;
                    rgba[i] = p.r; rgba[i + 1] = p.g; rgba[i + 2] = p.b; rgba[i + 3] = p.a;
                }
            }
            return new Frame(w, h, rgba);
        }
    }

    /// Where two frames differ, in numbers an agent can act on.
    public sealed class DiffReport
    {
        public int DifferingPixels;
        public int TotalPixels;
        public int MaxChannelDelta;
        public int MinX = int.MaxValue;
        public int MinY = int.MaxValue;
        public int MaxX = int.MinValue;
        public int MaxY = int.MinValue;
        public float CentroidX;
        public float CentroidY;

        public float Fraction => TotalPixels == 0 ? 0f : DifferingPixels / (float)TotalPixels;

        public override string ToString()
        {
            if (DifferingPixels == 0) return "0 pixels differ";
            return $"{DifferingPixels} of {TotalPixels} pixels differ ({Fraction * 100f:F3}%), " +
                   $"worst channel delta {MaxChannelDelta}/255, " +
                   $"bounding box x=[{MinX},{MaxX}] y=[{MinY},{MaxY}], " +
                   $"centroid ({CentroidX:F0},{CentroidY:F0})";
        }
    }

    public static class RenderHarness
    {
        /// Render the simulation headlessly and capture one frame after `ticks`
        /// simulation ticks.
        ///
        /// The simulation is advanced with the same fixed-step discipline the
        /// pure `Sim` tests use, so the rendered frame corresponds to an exactly
        /// known tick — there is no "roughly one second in" ambiguity.
        public static Frame CaptureFrame(ulong seed, int ticks, Intents[] inputs) =>
            CaptureFrameSized(seed, ticks, inputs, ViewConfig.VIEW_WIDTH, ViewConfig.VIEW_HEIGHT);

        public static Frame CaptureFrameSized(
            ulong seed, int ticks, Intents[] inputs, int width, int height)
        {
            if (SystemInfo.graphicsDeviceType == UnityEngine.Rendering.GraphicsDeviceType.Null)
            {
                throw new NoGraphicsDeviceException(
                    "no graphics device: this session was started with -nographics or has no " +
                    "usable adapter. Run render tests without -nographics (`just test-render`).");
            }

            var state = new SimState(seed);
            for (int tick = 0; tick < ticks; tick++)
            {
                var intents = inputs != null && tick < inputs.Length ? inputs[tick] : Intents.None;
                state.Step(intents);
            }
            if (state.Tick != (ulong)ticks)
            {
                throw new System.InvalidOperationException(
                    $"expected {ticks} ticks before capture, simulation reported {state.Tick}");
            }

            var view = new GameView();
            view.Sync(state);
            var camera = GameView.CreateArenaCamera();

            var descriptor = new RenderTextureDescriptor(width, height, RenderTextureFormat.ARGB32, 24)
            {
                msaaSamples = 1,
                sRGB = false,
                useMipMap = false,
                autoGenerateMips = false,
            };
            var target = new RenderTexture(descriptor);
            target.Create();

            Texture2D readback = null;
            var previous = RenderTexture.active;
            try
            {
                camera.targetTexture = target;
                camera.Render();
                RenderTexture.active = target;
                readback = new Texture2D(width, height, TextureFormat.RGBA32, false);
                readback.ReadPixels(new Rect(0, 0, width, height), 0, 0);
                readback.Apply();
                return Frame.FromTexture(readback);
            }
            finally
            {
                RenderTexture.active = previous;
                if (readback != null) Object.DestroyImmediate(readback);
                camera.targetTexture = null;
                Object.DestroyImmediate(camera.gameObject);
                view.Destroy();
                target.Release();
                Object.DestroyImmediate(target);
            }
        }
    }

    /// Thrown when the session has no GPU adapter. Tests treat this as "skip",
    /// not "fail": a developer without a graphics device should not see red
    /// tests they cannot fix. CI runs render tests for real.
    public sealed class NoGraphicsDeviceException : System.Exception
    {
        public NoGraphicsDeviceException(string message) : base(message) { }
    }
}
