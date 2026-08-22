using UnityEditor;

namespace Starter.EditorTools
{
    /// The EDITOR half of the launch guard.
    ///
    /// The render tests run `-testPlatform EditMode` with a REAL graphics device, so they
    /// are a launch path in the only sense that matters: they are a Unity process that can
    /// open an audio device on somebody's machine while nobody is watching.
    ///
    /// `[RuntimeInitializeOnLoadMethod]` does not fire for EditMode tests, so the runtime
    /// guard alone leaves this path uncovered. Whether the editor path is ACTUALLY audible
    /// is an OPEN QUESTION — `-disable-audio` is documented for the editor and was measured
    /// ignored only by the standalone PLAYER. It is guarded anyway, because the cost of the
    /// guard is one assignment and the cost of being wrong is somebody's afternoon.
    [InitializeOnLoad]
    public static class StarterLaunchGuardEditor
    {
        static StarterLaunchGuardEditor()
        {
            Starter.View.StarterLaunchGuard.Apply("editor");
        }
    }
}
