# Unity 6000.0.45f1 — what will break, and why

**This file is deliberately a table of signatures and deltas, not a tutorial with examples.**
That is an evidence-based choice: a 2025 ICSE study measured that when the surrounding context
already contains stale API usage, deprecated-API output rises to **70–90%** (versus 9–18% with
clean context), and a separate study found that retrieving *similar code* hurt accuracy by up to
**−15%** while retrieving *API descriptions* helped by up to **+20%**. Stale example code is worse
than no example code.

**When in doubt, trust the compiler over this file, and trust this file over your memory.**

## Batchmode traps — every one of these has produced a false green

| If you write | What actually happens |
|---|---|
| `-runTests` **and** `-quit` | The editor quits before the test runner starts. Exit code **0**, no results file, no tests run. Never combine them. `-quit` is fine on its own (`tools/unity-compile.sh` uses it). |
| `-runTests -nographics` for render tests | `SystemInfo.graphicsDeviceType == Null`. `Camera.Render()` draws nothing and `ReadPixels` returns the clear colour. Verified: real pixel capture **does** work in macOS batchmode as long as `-nographics` is omitted. |
| tests but no `testables` entry | `Packages/manifest.json` needs `"testables": ["com.unity.test-framework"]`. Without it **zero** tests are discovered and the run reports success over nothing. `tools/report.mjs` fails on `total="0"` for exactly this reason. |
| exit code as the pass/fail signal | `0` = all passed, `2` = one or more failed, `3` = run could not start. But `0` also means "quit before running anything". Always check that a results file exists too. |
| `-logFile` omitted | Unity writes to `~/Library/Logs/Unity/Editor.log` and your CI captures nothing. Omitting it in batchmode also dumps the whole banner on **stdout**. |
| `-logFile <path>` leaves your own stdout alone | It redirects the process's file descriptor 1 into that file, so `Console.Out` — and `Console.OpenStandardOutput()` — land in the log, not in the pipe. `just probe` therefore hands the real stdout through as descriptor 3 (`3>&1`) and `Probe.OpenTrace` writes to `/dev/fd/3`. |
| two Unity processes on one project | The second blocks on the `Library/` lock, or silently corrupts the asset database. `just verify` runs its steps sequentially on purpose. |
| grepping the log for `error CS` | Misses every analyzer diagnostic — `SIM0001`, `UNT0002`, `CA1861`. Match `error [A-Z]+[0-9]+`. |

Batchmode flags used here, with their exact spelling:

```
-batchmode -logFile <path> -projectPath <dir> -quit                       # compile only
-batchmode -logFile <path> -projectPath <dir> \
    -runTests -testPlatform EditMode -testResults <xml> \
    [-assemblyNames <Asmdef>] [-testFilter <Namespace.Class[.Method]>]    # tests, NO -quit
-enableCodeCoverage -coverageResultsPath <dir> -coverageOptions "k:v;k:v" # coverage
```

## Assembly definitions

Unity 6 rejects the 2018-era test asmdef shape. The old form does not warn — it fails the whole
compile with `Scripts have compiler errors` followed by `Aborting batchmode`.

| If you write | Unity 6 wants |
|---|---|
| `"optionalUnityReferences": ["TestAssemblies"]` | **removed.** Use the four keys below together. |
| — | `"overrideReferences": true` |
| — | `"precompiledReferences": ["nunit.framework.dll"]` |
| — | `"defineConstraints": ["UNITY_INCLUDE_TESTS"]` |
| — | `"includePlatforms": ["Editor"]` |

`Assets/Sim/Sim.asmdef` additionally sets `"noEngineReferences": true`. That is the mechanism
that makes "the simulation does not depend on the engine" a compiler error rather than a code
review comment. Do not remove it to make something compile — and if you do, `SIM0002` still
fails the build.

## Roslyn analyzers in Unity — measured on this editor, not from memory

Unity does **not** compile through MSBuild. `Directory.Build.props`, `TreatWarningsAsErrors`,
`<PackageReference>` and `.csproj` edits affect only the IDE-facing project files and are ignored
by the editor's own compile. The asset-database mechanisms below are the ones that work.

| Mechanism | How Unity picks it up | Verified here |
|---|---|---|
| Analyzer DLL | asset label `RoslynAnalyzer` on the `.dll`, all platforms **disabled** in the `PluginImporter` meta | ✅ appears as `-analyzer:` in `Library/Bee/artifacts/*.dag/<Asm>.rsp` |
| Severity config | `Assets/Default.globalconfig` (`is_global = true`) | ✅ appears as `/analyzerconfig:` |
| Per-assembly severity | `<AssemblyName>.ruleset` or a `.globalconfig` beside the `.asmdef` | not used here |
| Additional files | extension `.additionalfile`, importer `RoslynAdditionalFileImporter` | ❌ **imported but never passed to csc** in 6000.0.45f1 — no `/additionalfile:` for it |
| `.editorconfig` | — | ❌ ignored: Unity's asset pipeline skips dotfiles. Use `.globalconfig`. |

Consequences, learned the expensive way:

- **`Microsoft.CodeAnalysis.BannedApiAnalyzers` cannot work here.** It reads its ban list from an
  additional file named `BannedSymbols.txt`, and Unity 6000.0.45f1 does not forward additional
  files to the compiler. `Assets/Analyzers/Starter.Analyzers.dll` (source in `tools/analyzer/`)
  hard-codes the ban list instead.
- **Analyzers must target the Roslyn Unity ships.** This editor bundles **4.3.1**
  (`Unity.app/Contents/DotNetSdkRoslyn`). An analyzer built against a newer
  `Microsoft.CodeAnalysis` loads, warns `CS8032`, and then silently reports nothing —
  a green build that checks nothing.
- **Leaving an analyzer DLL's platforms enabled makes it a managed plugin**, and every type in it
  collides with the engine: `error CS0433: The type 'KeyCode' exists in both
  'Microsoft.Unity.Analyzers' and 'UnityEngine.CoreModule'`.

Bulk severity keys that work in `Assets/Default.globalconfig`:

```
dotnet_analyzer_diagnostic.category-<Category>.severity = error|warning|suggestion|none
dotnet_diagnostic.<Id>.severity                          = error|warning|suggestion|none
```

## API-level surprises in this project

| You may remember | Unity 6 / .NET Standard 2.1 |
|---|---|
| `BitConverter.SingleToUInt32Bits` | .NET 6+ only. Unity 6 ships netstandard 2.1, which has `SingleToInt32Bits`. `SimState.FloatBits` wraps it; the bytes are identical. |
| `GameObject.CreatePrimitive` is free | It attaches a `MeshCollider`, which drags in the Physics module. `GameView` builds a 4-vertex quad by hand instead. |
| `Texture2D.EncodeToPNG` is in core | It needs `com.unity.modules.imageconversion` in `Packages/manifest.json`. |
| `Shader.Find("Unlit/Color")` survives a build | Shaders reached only through `Shader.Find` are stripped from players. `Assets/View/Flat.shader` is listed in `ProjectSettings/GraphicsSettings.asset` under `m_AlwaysIncludedShaders`. |
| `ReadPixels` returns top-down rows | It returns **bottom-up**. `Frame` stores top-down (screen convention, `y` grows downward) and flips on both read and write. Get this wrong and "moving up moves pixels up" silently inverts. |
| colour space does not matter for pixel asserts | `ProjectSettings` pins **Gamma** (`m_ActiveColorSpace: 0`), so `Color(0.04, 0.05, 0.09)` reads back as exactly `(10, 13, 23)`. Switching to Linear changes every golden image. |

## Determinism-relevant engine behaviour

- `Time.fixedDeltaTime` is a global, not a per-object setting. `GameRunner` sets it once, to
  `Constants.TICK_DT`. It does **not** feed the simulation — `SimState.Step` takes no delta at all.
- Unity's fixed loop can run zero or several times in a frame. That is exactly why device input is
  latched in `Update` and consumed in `FixedUpdate`, and why the simulation reads `Intents`.
- EditMode tests run on the main thread in one editor process with no parallelism, so unlike the
  Rust sibling there is no test-group configuration to keep render tests off each other's GPU
  devices — the framework already serialises them.
- `Dictionary<K,V>` and `HashSet<T>` enumeration order is an implementation detail of the runtime,
  not part of the contract. `SIM0001` does not ban them, because they are fine as lookups. Do not
  iterate one inside a tick; sort on `SimId` instead.

Pin the version in `ProjectSettings/ProjectVersion.txt`. Unity rewrites project files on first
open with a newer editor and there is no downgrade path.
