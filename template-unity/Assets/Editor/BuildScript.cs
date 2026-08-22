// Player build for `just run`.
//
// There is no committed .unity scene on purpose: a scene asset is opaque YAML
// that agents cannot review, and every object it would hold is created at boot
// by PongRunner. The build script generates a throwaway empty scene instead, so
// the only reviewable artefacts in the repo are C# and JSON.

using UnityEditor;
using UnityEditor.Build.Reporting;
using UnityEditor.SceneManagement;
using UnityEngine;

namespace Pong.EditorTools
{
    public static class BuildScript
    {
        private const string ScenePath = "Assets/Generated/Boot.unity";
        private const string OutputPath = "build/Pong.app";

        public static void BuildMacOS()
        {
            System.IO.Directory.CreateDirectory("Assets/Generated");
            var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            EditorSceneManager.SaveScene(scene, ScenePath);
            AssetDatabase.Refresh();

            var options = new BuildPlayerOptions
            {
                scenes = new[] { ScenePath },
                locationPathName = OutputPath,
                target = BuildTarget.StandaloneOSX,
                options = BuildOptions.None,
            };
            var report = BuildPipeline.BuildPlayer(options);
            Debug.Log($"BUILD result={report.summary.result} errors={report.summary.totalErrors}");
            if (report.summary.result != BuildResult.Succeeded)
            {
                EditorApplication.Exit(1);
            }
            EditorApplication.Exit(0);
        }
    }
}
