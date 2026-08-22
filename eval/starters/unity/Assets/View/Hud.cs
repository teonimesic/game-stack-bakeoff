// The HUD, drawn as geometry so that the camera renders it.
//
// Anything the player is supposed to see has to go through the camera. `just
// film` and the rendering tests read exactly the pixels `camera.Render()` wrote
// into the offscreen RenderTexture; IMGUI (`OnGUI`, `GUI.Label`) is emitted in
// a different phase of the player loop and is in none of them. A HUD built that
// way looks correct in a window and is absent from every captured frame.
//
// So the text is a mesh of quads in world space, under the same view root as
// everything else, drawn with the same `Starter/Flat` material. The font is a
// 5x7 bitmap: no font asset, no rasteriser, no extra package, and the same
// pixels on every machine — which is what the golden image needs.
//
// The layout is expressed in view pixels and converted to world units once, so
// the block lands on exact pixel boundaries at `ViewConfig.VIEW_WIDTH` x
// `VIEW_HEIGHT` and stays the same fraction of the frame at other sizes.

using System.Collections.Generic;
using Starter.Sim;
using UnityEngine;

namespace Starter.View
{
    /// A fixed-position bitmap text overlay, rendered as camera-visible quads.
    public sealed class Hud
    {
        public const int GLYPH_WIDTH = 5;
        public const int GLYPH_HEIGHT = 7;

        /// View pixels per glyph pixel.
        public const int PIXEL_SCALE = 2;

        /// View pixels between the top-left corner of the frame and the text.
        public const int MARGIN = 6;

        /// Glyph pixels of horizontal advance per character.
        public const int ADVANCE = GLYPH_WIDTH + 1;

        /// Glyph pixels between the tops of consecutive lines.
        public const int LINE_PITCH = GLYPH_HEIGHT + 2;

        /// The block `ScreenRegion` reserves, in characters and lines. Text may
        /// run past it; tests assert on what is inside it.
        public const int REGION_COLUMNS = 16;
        public const int REGION_LINES = 2;

        /// In front of the entity quads (z = 0), still inside the near plane.
        private const float HudZ = -1f;

        private const float UnitsPerViewPixel =
            2f * Constants.ARENA_HALF_HEIGHT / ViewConfig.VIEW_HEIGHT;

        /// Half the world width the camera frames at the default view size.
        private const float FramedHalfWidth =
            Constants.ARENA_HALF_HEIGHT * ViewConfig.VIEW_WIDTH / ViewConfig.VIEW_HEIGHT;

        private const float CellSize = PIXEL_SCALE * UnitsPerViewPixel;
        private const float OriginX = -FramedHalfWidth + (MARGIN * UnitsPerViewPixel);
        private const float OriginY = Constants.ARENA_HALF_HEIGHT - (MARGIN * UnitsPerViewPixel);

        private readonly Mesh _mesh;
        private readonly Material _material;
        private readonly Transform _transform;
        private readonly List<Vector3> _vertices = new List<Vector3>();
        private readonly List<int> _triangles = new List<int>();
        private string _text = string.Empty;

        public Hud(Transform parent, string name = "hud")
        {
            var shader = Shader.Find("Starter/Flat");
            if (shader == null)
            {
                throw new System.InvalidOperationException(
                    "shader 'Starter/Flat' not found — Assets/View/Flat.shader failed to import");
            }
            _material = new Material(shader) { color = ViewConfig.HUD_COLOR };
            _mesh = new Mesh { name = "hud-text" };
            _mesh.MarkDynamic();

            var go = new GameObject(name, typeof(MeshFilter), typeof(MeshRenderer));
            go.transform.SetParent(parent, false);
            go.GetComponent<MeshFilter>().sharedMesh = _mesh;
            var renderer = go.GetComponent<MeshRenderer>();
            renderer.sharedMaterial = _material;
            renderer.shadowCastingMode = UnityEngine.Rendering.ShadowCastingMode.Off;
            renderer.receiveShadows = false;
            _transform = go.transform;
        }

        public Transform Transform => _transform;

        /// Set the displayed text. `\n` starts a new line; the font is
        /// uppercase-only, so the text is upper-cased and characters the font
        /// does not have are left blank. Rebuilds the mesh only when the text
        /// actually changed, so calling this every frame is cheap.
        public void SetText(string text)
        {
            string upper = text == null ? string.Empty : text.ToUpperInvariant();
            if (string.Equals(upper, _text, System.StringComparison.Ordinal)) return;
            _text = upper;
            Rebuild(upper);
        }

        /// The screen-space rectangle the HUD reserves, in a capture of
        /// `viewWidth` x `viewHeight`, with y growing downward — the same
        /// convention `Frame` uses. This is what a test should assert on, so
        /// moving the HUD moves the assertion with it.
        public static RectInt ScreenRegion(int viewWidth, int viewHeight)
        {
            float pixelsPerUnit = viewHeight / (2f * Constants.ARENA_HALF_HEIGHT);
            float framedHalfWidth = Constants.ARENA_HALF_HEIGHT * viewWidth / (float)viewHeight;

            int left = Mathf.FloorToInt((OriginX + framedHalfWidth) * pixelsPerUnit);
            int top = Mathf.FloorToInt((Constants.ARENA_HALF_HEIGHT - OriginY) * pixelsPerUnit);
            int width = Mathf.CeilToInt(REGION_COLUMNS * ADVANCE * CellSize * pixelsPerUnit);
            int height = Mathf.CeilToInt(REGION_LINES * LINE_PITCH * CellSize * pixelsPerUnit);

            left = Mathf.Clamp(left, 0, viewWidth);
            top = Mathf.Clamp(top, 0, viewHeight);
            return new RectInt(left, top,
                Mathf.Min(width, viewWidth - left), Mathf.Min(height, viewHeight - top));
        }

        public void Destroy()
        {
            if (_transform != null) Object.DestroyImmediate(_transform.gameObject);
            if (_mesh != null) Object.DestroyImmediate(_mesh);
            if (_material != null) Object.DestroyImmediate(_material);
        }

        private void Rebuild(string text)
        {
            _vertices.Clear();
            _triangles.Clear();

            int line = 0;
            int column = 0;
            foreach (char c in text)
            {
                if (c == '\n') { line++; column = 0; continue; }
                int index = Alphabet.IndexOf(c);
                if (index >= 0) AppendGlyph(Glyphs[index], line, column);
                column++;
            }

            _mesh.Clear();
            _mesh.SetVertices(_vertices);
            _mesh.SetTriangles(_triangles, 0);
            _mesh.RecalculateBounds();
        }

        private void AppendGlyph(string glyph, int line, int column)
        {
            for (int row = 0; row < GLYPH_HEIGHT; row++)
            {
                for (int col = 0; col < GLYPH_WIDTH; col++)
                {
                    if (glyph[(row * GLYPH_WIDTH) + col] != '#') continue;

                    float x = OriginX + (((column * ADVANCE) + col) * CellSize);
                    float y = OriginY - (((line * LINE_PITCH) + row) * CellSize);
                    int v = _vertices.Count;
                    _vertices.Add(new Vector3(x, y - CellSize, HudZ));
                    _vertices.Add(new Vector3(x + CellSize, y - CellSize, HudZ));
                    _vertices.Add(new Vector3(x + CellSize, y, HudZ));
                    _vertices.Add(new Vector3(x, y, HudZ));
                    _triangles.Add(v); _triangles.Add(v + 2); _triangles.Add(v + 1);
                    _triangles.Add(v); _triangles.Add(v + 3); _triangles.Add(v + 2);
                }
            }
        }

        /// The characters the font has, in the same order as `Glyphs`.
        private const string Alphabet = " ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.,:-+()%/";

        /// One 5x7 glyph per entry, seven rows of five, top row first. Add a
        /// character by adding it to `Alphabet` and its bitmap here, at the same
        /// index.
        private static readonly string[] Glyphs =
        {
            "....." + "....." + "....." + "....." + "....." + "....." + ".....", // space
            ".###." + "#...#" + "#...#" + "#####" + "#...#" + "#...#" + "#...#", // A
            "####." + "#...#" + "#...#" + "####." + "#...#" + "#...#" + "####.", // B
            ".###." + "#...#" + "#...." + "#...." + "#...." + "#...#" + ".###.", // C
            "####." + "#...#" + "#...#" + "#...#" + "#...#" + "#...#" + "####.", // D
            "#####" + "#...." + "#...." + "####." + "#...." + "#...." + "#####", // E
            "#####" + "#...." + "#...." + "####." + "#...." + "#...." + "#....", // F
            ".###." + "#...#" + "#...." + "#.###" + "#...#" + "#...#" + ".###.", // G
            "#...#" + "#...#" + "#...#" + "#####" + "#...#" + "#...#" + "#...#", // H
            "#####" + "..#.." + "..#.." + "..#.." + "..#.." + "..#.." + "#####", // I
            "..###" + "...#." + "...#." + "...#." + "...#." + "#..#." + ".##..", // J
            "#...#" + "#..#." + "#.#.." + "##..." + "#.#.." + "#..#." + "#...#", // K
            "#...." + "#...." + "#...." + "#...." + "#...." + "#...." + "#####", // L
            "#...#" + "##.##" + "#.#.#" + "#...#" + "#...#" + "#...#" + "#...#", // M
            "#...#" + "##..#" + "#.#.#" + "#..##" + "#...#" + "#...#" + "#...#", // N
            ".###." + "#...#" + "#...#" + "#...#" + "#...#" + "#...#" + ".###.", // O
            "####." + "#...#" + "#...#" + "####." + "#...." + "#...." + "#....", // P
            ".###." + "#...#" + "#...#" + "#...#" + "#.#.#" + "#..#." + ".##.#", // Q
            "####." + "#...#" + "#...#" + "####." + "#.#.." + "#..#." + "#...#", // R
            ".####" + "#...." + "#...." + ".###." + "....#" + "....#" + "####.", // S
            "#####" + "..#.." + "..#.." + "..#.." + "..#.." + "..#.." + "..#..", // T
            "#...#" + "#...#" + "#...#" + "#...#" + "#...#" + "#...#" + ".###.", // U
            "#...#" + "#...#" + "#...#" + "#...#" + "#...#" + ".#.#." + "..#..", // V
            "#...#" + "#...#" + "#...#" + "#...#" + "#.#.#" + "##.##" + "#...#", // W
            "#...#" + "#...#" + ".#.#." + "..#.." + ".#.#." + "#...#" + "#...#", // X
            "#...#" + "#...#" + ".#.#." + "..#.." + "..#.." + "..#.." + "..#..", // Y
            "#####" + "....#" + "...#." + "..#.." + ".#..." + "#...." + "#####", // Z
            ".###." + "#...#" + "#..##" + "#.#.#" + "##..#" + "#...#" + ".###.", // 0
            "..#.." + ".##.." + "..#.." + "..#.." + "..#.." + "..#.." + ".###.", // 1
            ".###." + "#...#" + "....#" + "...#." + "..#.." + ".#..." + "#####", // 2
            "#####" + "...#." + "..#.." + "...#." + "....#" + "#...#" + ".###.", // 3
            "...#." + "..##." + ".#.#." + "#..#." + "#####" + "...#." + "...#.", // 4
            "#####" + "#...." + "####." + "....#" + "....#" + "#...#" + ".###.", // 5
            "..##." + ".#..." + "#...." + "####." + "#...#" + "#...#" + ".###.", // 6
            "#####" + "....#" + "...#." + "..#.." + ".#..." + ".#..." + ".#...", // 7
            ".###." + "#...#" + "#...#" + ".###." + "#...#" + "#...#" + ".###.", // 8
            ".###." + "#...#" + "#...#" + ".####" + "....#" + "...#." + ".##..", // 9
            "....." + "....." + "....." + "....." + "....." + ".##.." + ".##..", // .
            "....." + "....." + "....." + "....." + ".##.." + ".##.." + ".#...", // ,
            "....." + ".##.." + ".##.." + "....." + ".##.." + ".##.." + ".....", // :
            "....." + "....." + "....." + "#####" + "....." + "....." + ".....", // -
            "....." + "..#.." + "..#.." + "#####" + "..#.." + "..#.." + ".....", // +
            "...#." + "..#.." + ".#..." + ".#..." + ".#..." + "..#.." + "...#.", // (
            ".#..." + "..#.." + "...#." + "...#." + "...#." + "..#.." + ".#...", // )
            "##..#" + "##..#" + "...#." + "..#.." + ".#..." + "#..##" + "#..##", // %
            "....#" + "....#" + "...#." + "..#.." + ".#..." + "#...." + "#....", // /
        };
    }
}
