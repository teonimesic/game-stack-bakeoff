# Vendored Roslyn analyzers

These DLLs are committed on purpose. They make `just lint` a real static-analysis
gate with no `dotnet` SDK, no NuGet restore and no network at any point.

| DLL | Source | Version | Rules |
|---|---|---|---|
| `Pong.Analyzers.dll` | this repo, `tools/analyzer/` | — | `PONG0001` banned nondeterministic API in `Sim`, `PONG0002` UnityEngine in `Sim` |
| `Microsoft.Unity.Analyzers.dll` | NuGet `Microsoft.Unity.Analyzers` | 1.21.0 | `UNT####` Unity idioms |
| `Microsoft.CodeAnalysis.NetAnalyzers.dll`, `Microsoft.CodeAnalysis.CSharp.NetAnalyzers.dll` | NuGet `Microsoft.CodeAnalysis.NetAnalyzers` | 8.0.0 | `CA####` .NET correctness, reliability, performance, globalization |

Three things have to be true or an analyzer silently checks nothing:

1. **The `.meta` carries the `RoslynAnalyzer` label**, or Unity passes the DLL as
   `-r:` instead of `-analyzer:` and every type in it collides with the engine.
2. **All platforms are disabled** in the `PluginImporter` section of the `.meta`,
   for the same reason.
3. **It targets Roslyn ≤ 4.3.1**, the version Unity 6000.0.45f1 bundles in
   `Unity.app/Contents/DotNetSdkRoslyn`. A newer analyzer loads, emits `CS8032`,
   and then reports nothing.

Severities are in `Assets/Default.globalconfig` (**not** `.editorconfig` — Unity's
asset pipeline skips dotfiles). Rebuild the local analyzer with `just analyzers`.

`Microsoft.CodeAnalysis.BannedApiAnalyzers` is deliberately absent: it reads its
ban list from an additional file, and Unity 6000.0.45f1 imports `.additionalfile`
assets but never forwards them to the compiler. It would have been a rule that
looked enforced and was not.
