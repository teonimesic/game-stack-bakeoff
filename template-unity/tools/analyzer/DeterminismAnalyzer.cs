// Compile-time enforcement of the determinism rules in AGENTS.md.
//
// `Sim.asmdef` already sets "noEngineReferences": true, which makes UnityEngine
// unresolvable inside the simulation. That covers UnityEngine.Random,
// UnityEngine.Time and MonoBehaviour. It does NOT cover the rest of the BCL:
// `System.Random`, `DateTime.Now` and `Stopwatch` all resolve happily and are
// exactly the trap an agent falls into when asked to randomise something.
//
// This analyzer closes that gap. Diagnostics are reported as ERRORS (see
// Assets/Default.globalconfig), so nondeterminism does not compile.

using System.Collections.Generic;
using System.Collections.Immutable;
using System.Linq;
using Microsoft.CodeAnalysis;
using Microsoft.CodeAnalysis.CSharp;
using Microsoft.CodeAnalysis.CSharp.Syntax;
using Microsoft.CodeAnalysis.Diagnostics;

namespace Pong.Analyzers
{
    [DiagnosticAnalyzer(LanguageNames.CSharp)]
    public sealed class DeterminismAnalyzer : DiagnosticAnalyzer
    {
        public const string BannedApiId = "PONG0001";
        public const string EngineInSimId = "PONG0002";

        /// Assemblies held to the determinism rules. Overridable from a
        /// .globalconfig with `pong_deterministic_assemblies = A,B`.
        private const string DefaultDeterministicAssemblies = "Sim";
        private const string AssembliesOptionKey = "pong_deterministic_assemblies";

        /// Path fragment that also marks a file as simulation code, so the rule
        /// still applies if someone renames the assembly.
        private const string SimPathFragment = "/Assets/Sim/";

        private static readonly DiagnosticDescriptor BannedApi = new DiagnosticDescriptor(
            BannedApiId,
            "Nondeterministic API in the simulation",
            "'{0}' is not allowed in the simulation: {1}",
            "Determinism",
            DiagnosticSeverity.Error,
            isEnabledByDefault: true,
            description:
                "The simulation must produce byte-identical results from the same seed and " +
                "inputs, or replay, rollback and desync detection all break. Anything that " +
                "reads the wall clock, OS entropy, the filesystem or another thread makes " +
                "that impossible.");

        private static readonly DiagnosticDescriptor EngineInSim = new DiagnosticDescriptor(
            EngineInSimId,
            "UnityEngine used in the simulation",
            "'{0}' is a UnityEngine symbol and the simulation must not depend on the engine",
            "Determinism",
            DiagnosticSeverity.Error,
            isEnabledByDefault: true,
            description:
                "Sim.asmdef sets \"noEngineReferences\": true so this is normally a resolve " +
                "error. This rule keeps it an error even if that flag is ever removed: engine " +
                "math types have changed implementation between Unity versions, so a " +
                "simulation that uses them is not replayable across upgrades.");

        public override ImmutableArray<DiagnosticDescriptor> SupportedDiagnostics =>
            ImmutableArray.Create(BannedApi, EngineInSim);

        /// Banned whole types, keyed by metadata name, with the reason an agent
        /// needs in order to fix it rather than work around it.
        private static readonly (string Metadata, string Reason)[] BannedTypes =
        {
            ("System.Random", "OS-seeded and not part of the snapshot. Use Pong.Sim.SimRng."),
            ("System.DateTime", "wall clock. Use SimState.Tick, which is snapshotted."),
            ("System.DateTimeOffset", "wall clock. Use SimState.Tick."),
            ("System.TimeZoneInfo", "machine-dependent. The simulation has no notion of local time."),
            ("System.Diagnostics.Stopwatch", "wall clock. Use SimState.Tick."),
            ("System.Threading.Thread", "thread scheduling is not reproducible. The tick is single-threaded."),
            ("System.Threading.Tasks.Task", "task scheduling is not reproducible. The tick is single-threaded."),
            ("System.Threading.Tasks.Parallel", "float addition is not associative; parallel reductions are not reproducible."),
            ("System.IO.File", "the filesystem is not part of the snapshot."),
            ("System.IO.Directory", "the filesystem is not part of the snapshot."),
            ("System.Console", "the simulation has no I/O. Surface state through TickEvents."),
            // Present only if someone removes "noEngineReferences"; harmless otherwise.
            ("UnityEngine.Random", "engine RNG is not snapshotted. Use Pong.Sim.SimRng."),
            ("UnityEngine.Time", "frame-scoped clock. Use SimState.Tick."),
        };

        /// Banned individual members of types that are otherwise fine.
        private static readonly (string Metadata, string Member, string Reason)[] BannedMembers =
        {
            ("System.Guid", "NewGuid", "OS entropy. Assign SimIds explicitly."),
            ("System.Environment", "TickCount", "wall clock. Use SimState.Tick."),
            ("System.Environment", "TickCount64", "wall clock. Use SimState.Tick."),
            ("System.Runtime.CompilerServices.RuntimeHelpers", "GetHashCode",
                "reference hash codes depend on allocation addresses. Hash SimId instead."),
            ("System.Linq.ParallelEnumerable", "AsParallel",
                "float addition is not associative; parallel reductions are not reproducible."),
        };

        public override void Initialize(AnalysisContext context)
        {
            context.EnableConcurrentExecution();
            context.ConfigureGeneratedCodeAnalysis(GeneratedCodeAnalysisFlags.None);
            context.RegisterCompilationStartAction(OnCompilationStart);
        }

        private static void OnCompilationStart(CompilationStartAnalysisContext context)
        {
            var deterministicAssemblies = ReadAssemblyList(context.Options);
            bool assemblyIsDeterministic =
                deterministicAssemblies.Contains(context.Compilation.AssemblyName ?? string.Empty);

            var bannedTypes = new Dictionary<ISymbol, string>(SymbolEqualityComparer.Default);
            foreach (var (metadata, reason) in BannedTypes)
            {
                var type = context.Compilation.GetTypeByMetadataName(metadata);
                if (type != null) bannedTypes[type] = reason;
            }

            var bannedMembers = new Dictionary<ISymbol, string>(SymbolEqualityComparer.Default);
            foreach (var (metadata, member, reason) in BannedMembers)
            {
                var type = context.Compilation.GetTypeByMetadataName(metadata);
                if (type == null) continue;
                foreach (var symbol in type.GetMembers(member)) bannedMembers[symbol] = reason;
            }

            context.RegisterSyntaxNodeAction(
                node => Inspect(node, assemblyIsDeterministic, bannedTypes, bannedMembers),
                SyntaxKind.IdentifierName,
                SyntaxKind.GenericName);
        }

        private static void Inspect(
            SyntaxNodeAnalysisContext context,
            bool assemblyIsDeterministic,
            Dictionary<ISymbol, string> bannedTypes,
            Dictionary<ISymbol, string> bannedMembers)
        {
            if (!assemblyIsDeterministic && !IsSimFile(context.Node.SyntaxTree.FilePath)) return;

            // `DateTime.Now.Second` would otherwise report three times. Report
            // once, on the leftmost banned symbol, so the message points at the
            // thing to delete rather than burying it in duplicates.
            if (ReceiverAlreadyReports(context, bannedTypes, bannedMembers)) return;

            var symbol = context.SemanticModel.GetSymbolInfo(context.Node, context.CancellationToken).Symbol;
            if (symbol == null) return;

            if (RootNamespace(symbol) == "UnityEngine")
            {
                context.ReportDiagnostic(Diagnostic.Create(
                    EngineInSim, context.Node.GetLocation(), Display(symbol)));
                return;
            }

            // A member reference also implicates its containing type, so
            // `DateTime.Now` is caught by the type entry for System.DateTime.
            var subject = symbol is INamedTypeSymbol ? symbol : symbol.OriginalDefinition;
            if (bannedMembers.TryGetValue(subject, out var memberReason))
            {
                context.ReportDiagnostic(Diagnostic.Create(
                    BannedApi, context.Node.GetLocation(), Display(symbol), memberReason));
                return;
            }

            var owner = symbol as INamedTypeSymbol ?? symbol.ContainingType;
            if (owner != null && bannedTypes.TryGetValue(owner.OriginalDefinition, out var typeReason))
            {
                context.ReportDiagnostic(Diagnostic.Create(
                    BannedApi, context.Node.GetLocation(), Display(symbol), typeReason));
            }
        }

        /// True when this node is the `.Name` of a member access whose receiver
        /// is already banned, so the receiver's diagnostic is enough.
        private static bool ReceiverAlreadyReports(
            SyntaxNodeAnalysisContext context,
            Dictionary<ISymbol, string> bannedTypes,
            Dictionary<ISymbol, string> bannedMembers)
        {
            if (context.Node.Parent is not MemberAccessExpressionSyntax access) return false;
            if (access.Name != context.Node) return false;

            var receiver = context.SemanticModel
                .GetSymbolInfo(access.Expression, context.CancellationToken).Symbol;
            if (receiver != null &&
                (bannedMembers.ContainsKey(receiver.OriginalDefinition) ||
                 (receiver is INamedTypeSymbol named &&
                  bannedTypes.ContainsKey(named.OriginalDefinition))))
            {
                return true;
            }

            var receiverType = context.SemanticModel
                .GetTypeInfo(access.Expression, context.CancellationToken).Type;
            return receiverType != null &&
                   bannedTypes.ContainsKey(receiverType.OriginalDefinition);
        }

        private static bool IsSimFile(string path) =>
            !string.IsNullOrEmpty(path) &&
            path.Replace('\\', '/').Contains(SimPathFragment);

        private static string RootNamespace(ISymbol symbol)
        {
            var ns = (symbol as INamespaceOrTypeSymbol)?.ContainingNamespace ?? symbol.ContainingNamespace;
            if (ns == null) return string.Empty;
            while (ns.ContainingNamespace is { IsGlobalNamespace: false }) ns = ns.ContainingNamespace;
            return ns.Name;
        }

        private static string Display(ISymbol symbol) =>
            symbol.ToDisplayString(SymbolDisplayFormat.CSharpErrorMessageFormat);

        private static HashSet<string> ReadAssemblyList(AnalyzerOptions options)
        {
            var configured = DefaultDeterministicAssemblies;
            if (options.AnalyzerConfigOptionsProvider.GlobalOptions
                    .TryGetValue(AssembliesOptionKey, out var value) &&
                !string.IsNullOrWhiteSpace(value))
            {
                configured = value;
            }
            return new HashSet<string>(
                configured.Split(',').Select(s => s.Trim()).Where(s => s.Length > 0));
        }
    }
}
