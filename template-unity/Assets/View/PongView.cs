// Presentation layer: turns simulation state into something you can see.
//
// Strict one-way data flow. This assembly reads `Sim` and never writes to it.
// Everything here is disposable; the simulation is the source of truth.

using System.Collections.Generic;
using Pong.Sim;
using UnityEngine;

namespace Pong.View
{
    public static class ViewConfig
    {
        public const int VIEW_WIDTH = 640;
        public const int VIEW_HEIGHT = 400;

        public static readonly Color BALL_COLOR = new Color(1.0f, 0.92f, 0.30f, 1f);
        public static readonly Color PADDLE_COLOR = new Color(0.35f, 0.78f, 1.0f, 1f);
        public static readonly Color BACKGROUND_COLOR = new Color(0.04f, 0.05f, 0.09f, 1f);

        /// Background as 8-bit RGB, for "is this pixel ink?" tests.
        public static Color32 BackgroundRgb => new Color32(
            (byte)Mathf.RoundToInt(BACKGROUND_COLOR.r * 255f),
            (byte)Mathf.RoundToInt(BACKGROUND_COLOR.g * 255f),
            (byte)Mathf.RoundToInt(BACKGROUND_COLOR.b * 255f), 255);
    }

    /// Draws one simulation into a set of GameObjects.
    ///
    /// `ViewOf` is the link back to the simulation entity a quad draws. The
    /// indirection is what lets the simulation run with no view at all — which
    /// is exactly what every test in `SimTests` does.
    public sealed class PongView
    {
        private readonly Transform _root;
        private readonly Material _paddleMaterial;
        private readonly Material _ballMaterial;
        private readonly Dictionary<int, Transform> _viewOf = new Dictionary<int, Transform>();

        public Transform Root => _root;

        public PongView(string name = "pong-view")
        {
            _root = new GameObject(name).transform;
            var shader = Shader.Find("Pong/Flat");
            if (shader == null)
            {
                throw new System.InvalidOperationException(
                    "shader 'Pong/Flat' not found — Assets/View/Flat.shader failed to import");
            }
            _paddleMaterial = new Material(shader) { color = ViewConfig.PADDLE_COLOR };
            _ballMaterial = new Material(shader) { color = ViewConfig.BALL_COLOR };
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
        }

        private static bool HasVisual(EntityKind kind) =>
            kind == EntityKind.Paddle || kind == EntityKind.Ball;

        /// A unit quad centred on the origin, built by hand.
        ///
        /// Not `GameObject.CreatePrimitive`: that attaches a MeshCollider and so
        /// drags in the Physics module, and the view has no business owning
        /// colliders — collision is a simulation concern and lives in `Sim`.
        private static Mesh UnitQuad()
        {
            if (_quad != null) return _quad;
            _quad = new Mesh { name = "pong-unit-quad" };
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
            bool isBall = entity.Kind == EntityKind.Ball;
            var go = new GameObject(isBall ? "ball" : "paddle-" + entity.Side,
                typeof(MeshFilter), typeof(MeshRenderer));
            go.GetComponent<MeshFilter>().sharedMesh = UnitQuad();
            go.transform.SetParent(_root, false);
            go.transform.localScale = isBall
                ? new Vector3(Constants.BALL_RADIUS * 2f, Constants.BALL_RADIUS * 2f, 1f)
                : new Vector3(16f, Constants.PADDLE_HALF_HEIGHT * 2f, 1f);
            go.GetComponent<MeshRenderer>().sharedMaterial =
                isBall ? _ballMaterial : _paddleMaterial;
            return go.transform;
        }

        public void Destroy()
        {
            if (_root != null) Object.DestroyImmediate(_root.gameObject);
            if (_paddleMaterial != null) Object.DestroyImmediate(_paddleMaterial);
            if (_ballMaterial != null) Object.DestroyImmediate(_ballMaterial);
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
