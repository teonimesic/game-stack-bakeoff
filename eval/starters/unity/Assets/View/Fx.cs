// Particle bursts — Unity's own particle system, wired so the capture path can
// actually see it.
//
// Unity ships Shuriken (`UnityEngine.ParticleSystem`) in
// `com.unity.modules.particlesystem`, which resolves from inside the editor
// with no network. This file exists so that using it costs one call instead of
// a turn spent discovering the two traps below.
//
// It is scaffolding, not gameplay: nothing here decides when anything bursts.
// `GameView` owns an idle `Fx` and never calls it. Deciding what a burst MEANS
// — a line cleared, an enemy killed, a landing — is the game, and that is
// yours.
//
// THE ONE RULE: a burst is a pure function of simulation state.
//
// `RenderHarness.CaptureFrame` — which `just film` reuses verbatim — steps the
// simulation to tick N with NO VIEW ATTACHED, then builds a fresh `GameView`,
// syncs once, and renders once. The view never observes ticks 1..N-1, and no
// player loop ever runs. So presentation state that accumulates frame by frame
// (an emitter you started when an event fired, a tween, a screen shake) is
// STRUCTURALLY INVISIBLE to every filmed frame and every rendering test, with
// nothing red to say so. It is the same trap as "everything the player sees
// goes through the camera", on the time axis instead of the tree axis.
//
// The way through is to derive the burst from state the simulation still holds
// at tick N — keep the tick a thing happened on, and pass the age:
//
//     var bursts = new List<Fx.Burst>();
//     foreach (var entity in state.Entities)
//     {
//         if (entity.ExplodedAtTick < 0) continue;
//         float age = (state.Tick - entity.ExplodedAtTick) * Constants.TICK_DT;
//         if (age <= Fx.LIFETIME)
//         {
//             bursts.Add(new Fx.Burst(
//                 new Vector2(entity.Position.X, entity.Position.Y),
//                 new Color(1f, 0.42f, 0.16f), age, entity.SimId));
//         }
//     }
//     view.Fx.ShowBursts(bursts);
//
// The second trap: a particle system is wall-clock animated, and the render
// tests assert byte equality. A `ParticleSystem` left to its own devices
// advances by the frame delta, so two identical captures disagree and
// `RenderingIsReproducibleAcrossRuns` goes red for a reason that looks like a
// GPU bug. Every emitter here therefore has `playOnAwake` off and a fixed seed,
// and the only thing that advances one is `ParticleSystem.Simulate(age, ...,
// fixedTimeStep: true)` — a fast-forward from a restart, in steps of
// `Time.fixedDeltaTime` (`ProjectSettings/TimeManager.asset`, 1/50 s here).
// Frame rate cannot reach it.
//
// Gravity is `forceOverLifetime`, deliberately NOT `main.gravityModifier`: that
// one multiplies `Physics.gravity`, which lives in `com.unity.modules.physics`
// — a module this template does not carry, and a physics engine is banned from
// `Sim` by every prompt that mentions one.

using System.Collections.Generic;
using UnityEngine;

namespace Starter.View
{
    /// A pool of deterministic one-shot particle bursts, drawn through the same
    /// camera as everything else.
    public sealed class Fx
    {
        /// Seconds a particle lives. A burst older than this shows nothing, so
        /// it is also the cutoff for "is this burst still worth drawing".
        public const float LIFETIME = 0.45f;

        /// Bursts drawable at once. Past this, `ShowBursts` draws the first
        /// `SLOTS` and drops the rest — deliberately, and in the order you
        /// passed them, so the frame stays a function of the state you sorted.
        public const int SLOTS = 8;

        /// Particles per burst.
        public const int AMOUNT = 24;

        /// Particle side length in world units, at spawn.
        public const float PARTICLE_SIZE = 6.0f;

        /// How fast particles leave the burst, world units per second.
        public const float SPEED_MIN = 40.0f;
        public const float SPEED_MAX = 180.0f;

        /// World units per second squared, pulling particles the way the arena
        /// calls down.
        public const float GRAVITY = -220.0f;

        /// Between the entity quads (z = 0) and the HUD (z = -1). The camera
        /// looks down +z from z = -10, so smaller z is nearer.
        private const float BurstZ = -0.5f;

        /// One burst to draw: where it is, what colour, and how long ago it
        /// started.
        ///
        /// `id` is what keeps a burst looking like itself. The emitter is
        /// seeded from it, so pass something stable — the `SimId` of whatever
        /// spawned the burst is ideal. Two bursts sharing an id look identical,
        /// which is fine; a burst whose id changes between frames visibly
        /// re-rolls, which is not.
        public readonly struct Burst
        {
            public Burst(Vector2 at, Color color, float age, int id)
            {
                At = at;
                Color = color;
                Age = age;
                Id = id;
            }

            public Vector2 At { get; }
            public Color Color { get; }
            public float Age { get; }
            public int Id { get; }
        }

        private readonly Transform _parent;
        private ParticleSystem[] _pool;
        private Material[] _materials;

        public Fx(Transform parent)
        {
            _parent = parent;
        }

        /// Draw exactly these bursts, and nothing else.
        ///
        /// Stateless by design: whatever was on screen last call is gone unless
        /// it is in `bursts` again. Call it once per `GameView.Sync`, every
        /// sync, including with an empty list.
        public void ShowBursts(IReadOnlyList<Burst> bursts)
        {
            int wanted = bursts == null ? 0 : bursts.Count;
            // A starter that never bursts pays nothing for this file — no
            // GameObjects, no materials, and no time in `just film`.
            if (_pool == null && wanted == 0) return;
            BuildPool();

            for (int slot = 0; slot < SLOTS; slot++)
            {
                var system = _pool[slot];
                if (slot >= wanted)
                {
                    if (system.gameObject.activeSelf)
                    {
                        system.Stop(true, ParticleSystemStopBehavior.StopEmittingAndClear);
                        system.Clear(true);
                        system.gameObject.SetActive(false);
                    }
                    continue;
                }

                var burst = bursts[slot];
                system.gameObject.SetActive(true);
                system.transform.localPosition = new Vector3(burst.At.x, burst.At.y, BurstZ);
                _materials[slot].color = burst.Color;

                // The seed only takes effect on a system that is stopped, so it
                // has to be set BEFORE the restart, not after.
                system.Stop(true, ParticleSystemStopBehavior.StopEmittingAndClear);
                system.Clear(true);
                system.randomSeed = (uint)Mathf.Abs(burst.Id) + 1u;

                float age = Mathf.Clamp(burst.Age, 0f, LIFETIME);
                system.Simulate(age, true, true, true);
            }
        }

        public void Destroy()
        {
            if (_pool != null)
            {
                for (int slot = 0; slot < _pool.Length; slot++)
                {
                    if (_pool[slot] != null) Object.DestroyImmediate(_pool[slot].gameObject);
                }
                _pool = null;
            }
            if (_materials != null)
            {
                for (int slot = 0; slot < _materials.Length; slot++)
                {
                    if (_materials[slot] != null) Object.DestroyImmediate(_materials[slot]);
                }
                _materials = null;
            }
        }

        /// One burst of `AMOUNT` particles at t = 0, which is what makes it a
        /// burst rather than a stream. Hoisted so the array is allocated once
        /// (CA1861).
        private static readonly ParticleSystem.Burst[] OneShot =
        {
            new ParticleSystem.Burst(0f, (short)AMOUNT),
        };

        /// Create `SLOTS` emitters configured for deterministic one-shot
        /// bursts.
        ///
        /// Everything here is code rather than a prefab or a `.unity` scene on
        /// purpose: an asset cannot be reviewed in a diff, and this template
        /// commits no scene.
        private void BuildPool()
        {
            if (_pool != null) return;

            var shader = Shader.Find("Starter/Flat");
            if (shader == null)
            {
                throw new System.InvalidOperationException(
                    "shader 'Starter/Flat' not found — Assets/View/Flat.shader failed to import");
            }

            _pool = new ParticleSystem[SLOTS];
            _materials = new Material[SLOTS];
            for (int slot = 0; slot < SLOTS; slot++)
            {
                var go = new GameObject("fx-burst-" + slot.ToString(
                    System.Globalization.CultureInfo.InvariantCulture));
                go.transform.SetParent(_parent, false);
                var system = go.AddComponent<ParticleSystem>();

                var main = system.main;
                main.loop = false;
                main.playOnAwake = false;
                main.duration = LIFETIME;
                main.startLifetime = new ParticleSystem.MinMaxCurve(LIFETIME);
                main.startSpeed = new ParticleSystem.MinMaxCurve(SPEED_MIN, SPEED_MAX);
                main.startSize =
                    new ParticleSystem.MinMaxCurve(PARTICLE_SIZE * 0.6f, PARTICLE_SIZE);
                main.startColor = UnityEngine.Color.white;
                main.simulationSpace = ParticleSystemSimulationSpace.Local;
                main.maxParticles = AMOUNT;
                // Physics.gravity is in a module this template does not carry.
                main.gravityModifier = 0f;
                // A capture never runs a player loop, so nothing would tick a
                // culled system back into existence.
                main.cullingMode = ParticleSystemCullingMode.AlwaysSimulate;

                var emission = system.emission;
                emission.enabled = true;
                emission.rateOverTime = 0f;
                emission.SetBursts(OneShot);

                var shape = system.shape;
                shape.enabled = true;
                shape.shapeType = ParticleSystemShapeType.Circle;
                shape.radius = 2f;
                shape.radiusThickness = 1f;
                shape.arc = 360f;
                shape.arcMode = ParticleSystemShapeMultiModeValue.Random;

                var force = system.forceOverLifetime;
                force.enabled = true;
                force.space = ParticleSystemSimulationSpace.Local;
                force.y = new ParticleSystem.MinMaxCurve(GRAVITY);

                // THE DETERMINISM LINE. Read it as "wall time cannot reach this
                // emitter": with no auto seed and no play-on-awake, the only
                // thing that ever advances it is the `Simulate` call above.
                system.useAutoRandomSeed = false;
                system.randomSeed = 1u;

                var material = new Material(shader) { color = UnityEngine.Color.white };
                var renderer = system.GetComponent<ParticleSystemRenderer>();
                renderer.renderMode = ParticleSystemRenderMode.Billboard;
                renderer.alignment = ParticleSystemRenderSpace.View;
                renderer.sortMode = ParticleSystemSortMode.None;
                renderer.sharedMaterial = material;

                go.SetActive(false);
                _pool[slot] = system;
                _materials[slot] = material;
            }
        }
    }
}
