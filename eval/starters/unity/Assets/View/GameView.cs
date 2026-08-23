// Presentation layer: turns simulation state into something you can see.
//
// Strict one-way data flow. This assembly reads `Sim` and never writes to it.
// Everything here is disposable; the simulation is the source of truth.

using System.Collections.Generic;
using System.Globalization;
using Starter.Sim;
using UnityEngine;

namespace Starter.View
{
    public static class ViewConfig
    {
        public const int VIEW_WIDTH = 640;
        public const int VIEW_HEIGHT = 400;

        public static readonly Color MARKER_COLOR = new Color(1.0f, 0.92f, 0.30f, 1f);
        public static readonly Color BACKGROUND_COLOR = new Color(0.04f, 0.05f, 0.09f, 1f);
        public static readonly Color HUD_COLOR = new Color(0.80f, 0.86f, 1.0f, 1f);

        /// Background as 8-bit RGB, for "is this pixel ink?" tests.
        public static Color32 BackgroundRgb => Rgb(BACKGROUND_COLOR);

        /// The frame holds more than one thing, so "not the background" is no
        /// longer the same question as "is this the marker". These let a test
        /// name the thing it is measuring.
        public static Color32 MarkerRgb => Rgb(MARKER_COLOR);
        public static Color32 HudRgb => Rgb(HUD_COLOR);

        private static Color32 Rgb(Color color) => new Color32(
            (byte)Mathf.RoundToInt(color.r * 255f),
            (byte)Mathf.RoundToInt(color.g * 255f),
            (byte)Mathf.RoundToInt(color.b * 255f), 255);
    }

    /// Draws one simulation into a set of GameObjects.
    ///
    /// `ViewOf` is the link back to the simulation entity a quad draws. The
    /// indirection is what lets the simulation run with no view at all — which
    /// is exactly what every test in `SimTests` does.
    public sealed class GameView
    {
        private readonly Transform _root;
        private readonly Material _markerMaterial;
        private readonly Hud _hud;
        private readonly Fx _fx;
        private readonly Dictionary<int, Transform> _viewOf = new Dictionary<int, Transform>();

        public Transform Root => _root;

        /// The on-screen readout. It lives here, in the view, so every path that
        /// builds a `GameView` gets it: the windowed player, and the offscreen
        /// capture that `just film` and the rendering tests read back.
        public Hud Hud => _hud;

        /// Particle bursts, idle until something asks for one. `Sync` never
        /// calls it: what a burst MEANS is the game, not the template. See
        /// `Assets/View/Fx.cs` — a burst has to be a pure function of
        /// simulation state or the capture path cannot show it.
        public Fx Fx => _fx;

        public GameView(string name = "game-view")
        {
            _root = new GameObject(name).transform;
            var shader = Shader.Find("Starter/Flat");
            if (shader == null)
            {
                throw new System.InvalidOperationException(
                    "shader 'Starter/Flat' not found — Assets/View/Flat.shader failed to import");
            }
            _markerMaterial = new Material(shader) { color = ViewConfig.MARKER_COLOR };
            _hud = new Hud(_root);
            _fx = new Fx(_root);
        }

        /// Give every simulation entity that lacks a view a quad, then copy
        /// simulation positions onto view transforms. One way only.
        public void Sync(SimState state)
        {
            foreach (var entity in state.Entities)
            {
                if (!_viewOf.TryGetValue(entity.SimId, out var view))
                {
                    // A simulation entity the view has no visual for is skipped,
                    // not drawn as a default quad. The simulation is free to
                    // grow — a spawner, a trigger volume, a collectable that has
                    // no art yet — without silently changing every rendered
                    // frame and every golden image. Give a new kind a visual
                    // HERE, deliberately, when you want to see it.
                    if (!HasVisual(entity.Kind)) continue;
                    view = CreateQuad(entity);
                    _viewOf[entity.SimId] = view;
                }
                view.localPosition = new Vector3(entity.Position.X, entity.Position.Y, 0f);
            }

            var marker = state.Marker;
            _hud.SetText(string.Format(CultureInfo.InvariantCulture,
                "tick {0}\n({1:F1}, {2:F1})",
                state.Tick, marker.Position.X, marker.Position.Y));
        }

        private static bool HasVisual(EntityKind kind) => kind == EntityKind.Marker;

        /// A unit quad centred on the origin, built by hand.
        ///
        /// Not `GameObject.CreatePrimitive`: that attaches a MeshCollider and so
        /// drags in the Physics module, and the view has no business owning
        /// colliders — collision is a simulation concern and lives in `Sim`.
        private static Mesh UnitQuad()
        {
            if (_quad != null) return _quad;
            _quad = new Mesh { name = "unit-quad" };
            _quad.SetVertices(QuadVertices);
            _quad.SetTriangles(QuadTriangles, 0);
            _quad.RecalculateBounds();
            return _quad;
        }

        private static Mesh _quad;

        // Hoisted out of UnitQuad so the arrays are allocated once, not on every
        // call (CA1861).
        private static readonly Vector3[] QuadVertices =
        {
            new Vector3(-0.5f, -0.5f, 0f), new Vector3(0.5f, -0.5f, 0f),
            new Vector3(0.5f, 0.5f, 0f), new Vector3(-0.5f, 0.5f, 0f),
        };

        private static readonly int[] QuadTriangles = { 0, 2, 1, 0, 3, 2 };

        private Transform CreateQuad(SimEntity entity)
        {
            var go = new GameObject("marker-" + entity.SimId,
                typeof(MeshFilter), typeof(MeshRenderer));
            go.GetComponent<MeshFilter>().sharedMesh = UnitQuad();
            go.transform.SetParent(_root, false);
            float side = Constants.MARKER_HALF_SIZE * 2f;
            go.transform.localScale = new Vector3(side, side, 1f);
            go.GetComponent<MeshRenderer>().sharedMaterial = _markerMaterial;
            return go.transform;
        }

        public void Destroy()
        {
            _fx.Destroy();
            _hud.Destroy();
            if (_root != null) Object.DestroyImmediate(_root.gameObject);
            if (_markerMaterial != null) Object.DestroyImmediate(_markerMaterial);
        }

        /// A camera that frames the whole arena.
        ///
        /// Orthographic size is the arena's HALF height, so the vertical extent
        /// is exactly the arena. At the 640x400 view size the aspect ratio then
        /// makes the horizontal extent exactly the arena too.
        public static Camera CreateArenaCamera(string name = "arena-camera")
        {
            var camera = new GameObject(name).AddComponent<Camera>();
            camera.orthographic = true;
            camera.orthographicSize = Constants.ARENA_HALF_HEIGHT;
            camera.clearFlags = CameraClearFlags.SolidColor;
            camera.backgroundColor = ViewConfig.BACKGROUND_COLOR;
            camera.nearClipPlane = 0.1f;
            camera.farClipPlane = 100f;
            camera.transform.position = new Vector3(0f, 0f, -10f);
            // Deterministic pixels: no MSAA, no HDR tonemapping, no post.
            camera.allowMSAA = false;
            camera.allowHDR = false;
            camera.useOcclusionCulling = false;
            return camera;
        }
    }
}
