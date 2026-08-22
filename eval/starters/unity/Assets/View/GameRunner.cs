// The playable game. `just run` builds a player that boots straight into this.
//
// Note what it does NOT do: it never puts a game rule here. It converts devices
// to intent, steps the simulation on a fixed timestep, and draws the result.

using Starter.Sim;
using UnityEngine;

namespace Starter.View
{
    public sealed class GameRunner : MonoBehaviour
    {
        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        private static void Boot()
        {
            var go = new GameObject("game-runner");
            DontDestroyOnLoad(go);
            go.AddComponent<GameRunner>();
        }

        private SimState _state;
        private GameView _view;
        // Latched intent: devices are sampled every frame, the simulation
        // consumes it on the next fixed tick. Sampling inside FixedUpdate would
        // drop presses on frames where the fixed step runs zero or twice.
        private bool _up, _down;

        private void Awake()
        {
            Time.fixedDeltaTime = Constants.TICK_DT;
            _state = new SimState((ulong)System.DateTime.UtcNow.Ticks);
            _view = new GameView();
            GameView.CreateArenaCamera().transform.SetParent(transform, false);
        }

        private void Update()
        {
            _up |= Input.GetKey(KeyCode.W) || Input.GetKey(KeyCode.UpArrow);
            _down |= Input.GetKey(KeyCode.S) || Input.GetKey(KeyCode.DownArrow);
            if (Input.GetKeyDown(KeyCode.Escape)) Application.Quit();
            // Draws the bodies AND the HUD. There is no `OnGUI` here on purpose:
            // IMGUI never reaches `camera.Render()`, so anything drawn that way
            // is missing from `just film` and from every rendering test.
            _view.Sync(_state);
        }

        private void FixedUpdate()
        {
            _state.Step(new Intents(_up, _down));
            _up = _down = false;
        }
    }
}
