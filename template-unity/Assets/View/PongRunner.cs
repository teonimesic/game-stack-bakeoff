// The playable game. `just run` builds a player that boots straight into this.
//
// Note what it does NOT do: it never puts a game rule here. It converts devices
// to intent, steps the simulation on a fixed timestep, and draws the result.

using Pong.Sim;
using UnityEngine;

namespace Pong.View
{
    public sealed class PongRunner : MonoBehaviour
    {
        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.AfterSceneLoad)]
        private static void Boot()
        {
            var go = new GameObject("pong-runner");
            DontDestroyOnLoad(go);
            go.AddComponent<PongRunner>();
        }

        private SimState _state;
        private PongView _view;
        // Latched intent: devices are sampled every frame, the simulation
        // consumes it on the next fixed tick. Sampling inside FixedUpdate would
        // drop presses on frames where the fixed step runs zero or twice.
        private bool _lUp, _lDown, _rUp, _rDown;

        private void Awake()
        {
            Time.fixedDeltaTime = Constants.TICK_DT;
            _state = new SimState((ulong)System.DateTime.UtcNow.Ticks);
            _view = new PongView();
            PongView.CreateArenaCamera().transform.SetParent(transform, false);
        }

        private void Update()
        {
            _lUp |= Input.GetKey(KeyCode.W);
            _lDown |= Input.GetKey(KeyCode.S);
            _rUp |= Input.GetKey(KeyCode.UpArrow);
            _rDown |= Input.GetKey(KeyCode.DownArrow);
            if (Input.GetKeyDown(KeyCode.Escape)) Application.Quit();
            _view.Sync(_state);
        }

        private void FixedUpdate()
        {
            _state.Step(new Intents(
                new PlayerIntent(_lUp, _lDown),
                new PlayerIntent(_rUp, _rDown)));
            _lUp = _lDown = _rUp = _rDown = false;
        }

        private void OnGUI()
        {
            GUI.Label(new Rect(10, 10, 300, 20),
                $"{_state.Score.Left} : {_state.Score.Right}   tick {_state.Tick}");
        }
    }
}
