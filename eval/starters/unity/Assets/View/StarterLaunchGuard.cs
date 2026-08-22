using UnityEngine;

namespace Starter.View
{
    /// Keeps a LAUNCHED game off the operator's speakers. Harness code, not game code.
    ///
    /// WHY A RUNTIME HOOK AND NOT A COMMAND-LINE FLAG.
    ///
    /// `-disable-audio` is an EDITOR flag. The standalone player ACCEPTS IT WITHOUT ERROR
    /// AND IGNORES IT: measured 2026-08-17, a player launched with the flag explicitly
    /// present in its argv was audible on the default output device, and the process was
    /// identified from `ps` while it was making the sound. An accepted-but-ignored flag is
    /// worse than an unsupported one, because no exit code can tell the two apart — which
    /// is exactly how this guard came to be marked complete once already while doing
    /// nothing.
    ///
    /// WHAT THIS DOES AND DOES NOT DO.
    ///
    /// It sets `AudioListener.volume` to zero, so nothing reaches the output. It does not
    /// necessarily prevent Unity from OPENING an audio device — that is a project setting
    /// baked into the build, and turning it off would change the artifact under
    /// measurement rather than the way it is launched. The requirement is that a launch
    /// must not make noise on somebody's machine, and silence at the listener satisfies it.
    ///
    /// It must never be extended into disabling audio at project level. The task asks the
    /// agent to ship sound and the audio criteria grade it — by decoding the shipped clip
    /// FILES with ffmpeg, verified: there is no playback call anywhere in the grader. So
    /// silencing the LAUNCH changes no criterion, and silencing the PRODUCT would change
    /// the deliverable.
    ///
    /// SCOPE IS THE RESOURCE, NOT THE RECIPE. Anything that opens an audio device goes
    /// through this. The previous attempt guarded the recipes someone had enumerated —
    /// the capture and test paths, which were already silent — and left the one that
    /// actually plays to a human untouched.
    public static class StarterLaunchGuard
    {
        /// Passed by `just run`. Also honoured as STARTER_SILENT_LAUNCH=1 so the same
        /// switch works when the binary is started by something other than `just`.
        public const string SilentArg = "-starter-silent";

        public static bool SilentRequested()
        {
            if (System.Environment.GetEnvironmentVariable("STARTER_SILENT_LAUNCH") == "1")
            {
                return true;
            }
            foreach (var a in System.Environment.GetCommandLineArgs())
            {
                if (a == SilentArg)
                {
                    return true;
                }
            }
            return false;
        }

        /// Applied and LOGGED. The log line is the assertion: a guard whose effect can only
        /// be confirmed by listening is a guard nobody can put in a test.
        public static void Apply(string where)
        {
            if (!SilentRequested())
            {
                Debug.Log($"[StarterLaunchGuard] {where}: silent launch NOT requested; "
                          + "audio left on the default device.");
                return;
            }
            // REFLECTION, BECAUSE THE STARTER HAS NO AUDIO MODULE.
            //
            // `Packages/manifest.json` does not include `com.unity.modules.audio`, so
            // `AudioListener` does not exist to compile against here and a direct
            // reference does not build. The agent ADDS the module in order to ship the
            // sound the task asks for — which is exactly when this guard has to work.
            // So it must compile in a project without audio and take effect in one with
            // it. That is what reflection buys, and it is the only reason it is used.
            var t = System.Type.GetType(
                "UnityEngine.AudioListener, UnityEngine.AudioModule", false);
            if (t == null)
            {
                Debug.Log($"[StarterLaunchGuard] {where}: SILENT LAUNCH REQUESTED, and "
                          + "this project has no audio module — nothing can play. "
                          + "No action needed.");
                return;
            }
            var vol = t.GetProperty("volume",
                System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.Static);
            var pause = t.GetProperty("pause",
                System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.Static);
            if (vol != null) { vol.SetValue(null, 0f); }
            if (pause != null) { pause.SetValue(null, true); }
            Debug.Log($"[StarterLaunchGuard] {where}: SILENT LAUNCH ACTIVE — "
                      + $"AudioListener.volume={(vol == null ? "?" : vol.GetValue(null).ToString())}, "
                      + $"pause={(pause == null ? "?" : pause.GetValue(null).ToString())}");
        }

        [RuntimeInitializeOnLoadMethod(RuntimeInitializeLoadType.BeforeSceneLoad)]
        private static void OnRuntimeLoad()
        {
            Apply("runtime");
        }
    }
}
