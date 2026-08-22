// Batchmode entry points for the probe protocol. See `## Probing a run` in
// AGENTS.md for the contract these implement.
//
// Three of them, all driven by `-executeMethod`:
//
//   Probe.Stream    `just probe`       stdin/stdout, one tick per input line
//   Probe.Batch     `just probe-file`  a whole scripted run to a JSONL file
//   Probe.Film      `just film`        evenly spaced PNGs of the same run
//
// Traps this file exists to avoid:
//
// * A batchmode run that throws still exits 0 on some paths, so every entry
//   point wraps its body and calls `EditorApplication.Exit` with an explicit
//   code. Silence is not success.
// * `Stream` must NOT be launched with `-quit`: the editor would exit before a
//   single line was read. `Batch` and `Film` do use `-quit`, which is safe —
//   the ban is specifically `-quit` together with `-runTests`.
// * stdout carries the trace and nothing else. Diagnostics go to stderr, and
//   the engine's own chatter goes to the `-logFile`.

using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Text;
using Starter.Sim;
using Starter.View;
using UnityEditor;

namespace Starter.EditorTools
{
    public static class Probe
    {
        /// How many frames `Film` writes at most, including both endpoints.
        private const int FilmFrames = 12;

        // ------------------------------------------------------------------
        // Entry points
        // ------------------------------------------------------------------

        /// Long-lived headless process: one JSON input object per stdin line in,
        /// one JSON trace line per tick out, flushed every time.
        public static void Stream()
        {
            int code = 0;
            try
            {
                var state = new SimState(ULongArg("-seed"));
                using var stdout = OpenTrace();

                // The world before any tick has run, so a driver can decide what
                // to do with the very first input.
                Emit(stdout, state);

                string line;
                while ((line = Console.In.ReadLine()) != null)
                {
                    if (string.Equals(line.Trim(), "quit", StringComparison.Ordinal)) break;
                    state.Step(IntentsFrom(line));
                    Emit(stdout, state);
                }
            }
            catch (Exception e)
            {
                Console.Error.WriteLine("probe: " + e);
                code = 1;
            }
            EditorApplication.Exit(code);
        }

        /// Run a scripted number of ticks and write the whole trace to a file.
        public static void Batch()
        {
            int code = 0;
            try
            {
                ulong seed = ULongArg("-seed");
                int ticks = IntArg("-ticks");
                var inputs = ReadScript(StringArg("-script"));
                string outPath = StringArg("-out");

                var state = new SimState(seed);
                var text = new StringBuilder();
                for (int tick = 0; tick < ticks; tick++)
                {
                    state.Step(tick < inputs.Count ? inputs[tick] : Intents.None);
                    text.Append(TraceLine(state)).Append('\n');
                }

                if (state.Tick != (ulong)ticks)
                {
                    throw new InvalidOperationException(
                        $"asked for {ticks} ticks, the simulation reported {state.Tick}");
                }

                string dir = Path.GetDirectoryName(Path.GetFullPath(outPath));
                if (!string.IsNullOrEmpty(dir)) Directory.CreateDirectory(dir);
                File.WriteAllText(outPath, text.ToString());
                Console.Error.WriteLine(
                    $"probe-file: wrote {ticks} lines to {outPath}");
            }
            catch (Exception e)
            {
                Console.Error.WriteLine("probe-file: " + e);
                code = 1;
            }
            EditorApplication.Exit(code);
        }

        /// Capture up to twelve evenly spaced frames of the same scripted run.
        public static void Film()
        {
            int code = 0;
            try
            {
                ulong seed = ULongArg("-seed");
                int ticks = IntArg("-ticks");
                var inputs = ReadScript(StringArg("-script"));
                string outDir = Path.GetFullPath(StringArg("-outdir"));
                Directory.CreateDirectory(outDir);

                var script = inputs.ToArray();
                int written = 0;
                int previous = -1;
                foreach (int tick in FrameTicks(ticks))
                {
                    if (tick == previous) continue;
                    previous = tick;
                    var frame = RenderHarness.CaptureFrame(seed, tick, script);
                    frame.SavePng(Path.Combine(
                        outDir,
                        "frame_" + written.ToString("0000", CultureInfo.InvariantCulture) + ".png"));
                    written++;
                }
                Console.Error.WriteLine($"film: wrote {written} frame(s) to {outDir}");
            }
            catch (Exception e)
            {
                Console.Error.WriteLine("film: " + e);
                code = 1;
            }
            EditorApplication.Exit(code);
        }

        /// Where the trace goes.
        ///
        /// NOT `Console.Out`, and not file descriptor 1 either: `-logFile`
        /// makes batchmode Unity redirect the process's own stdout into the log,
        /// so anything written there would be buried in the engine banner and
        /// the driver would see an empty pipe. `just probe` therefore hands the
        /// real stdout through as descriptor 3 (`3>&1`) and passes its path in
        /// `-trace`. Without that argument the trace goes to descriptor 1, which
        /// is right when nothing has redirected it.
        private static StreamWriter OpenTrace()
        {
            string path = OptionalArg("-trace");
            var stream = string.IsNullOrEmpty(path)
                ? Console.OpenStandardOutput()
                : new FileStream(path, FileMode.Open, FileAccess.Write);
            return new StreamWriter(stream, new UTF8Encoding(false)) { AutoFlush = false };
        }

        /// The ticks `Film` captures: `FilmFrames` samples spread over
        /// `0..=ticks` inclusive, endpoints always included, integer division so
        /// the spacing is reproducible rather than float-rounded.
        internal static IEnumerable<int> FrameTicks(int ticks)
        {
            if (ticks <= 0) { yield return 0; yield break; }
            for (int i = 0; i < FilmFrames; i++)
            {
                yield return (int)((long)i * ticks / (FilmFrames - 1));
            }
        }

        // ------------------------------------------------------------------
        // The trace format
        // ------------------------------------------------------------------

        private static void Emit(StreamWriter stdout, SimState state)
        {
            stdout.Write(TraceLine(state));
            stdout.Write('\n');
            // Mandatory. A block-buffered stdout deadlocks a driver that is
            // waiting for this line before it sends the next input.
            stdout.Flush();
        }

        /// One line of the trace. `state` is game-defined; this is the
        /// placeholder's version of it.
        private static string TraceLine(SimState state)
        {
            var marker = state.Marker;
            var sb = new StringBuilder(160);
            sb.Append("{\"tick\": ").Append(state.Tick.ToString(CultureInfo.InvariantCulture));
            sb.Append(", \"hash\": \"0x")
              .Append(state.StateHash().ToString("x16", CultureInfo.InvariantCulture))
              .Append('"');
            sb.Append(", \"state\": {\"marker\": {\"x\": ").Append(Number(marker.Position.X))
              .Append(", \"y\": ").Append(Number(marker.Position.Y))
              .Append(", \"vx\": ").Append(Number(marker.Velocity.X))
              .Append(", \"vy\": ").Append(Number(marker.Velocity.Y))
              .Append("}}");

            sb.Append(", \"events\": [");
            var names = state.Events.Names;
            for (int i = 0; i < names.Count; i++)
            {
                if (i > 0) sb.Append(", ");
                sb.Append('"').Append(names[i]).Append('"');
            }
            sb.Append("]}");
            return sb.ToString();
        }

        /// Nine significant digits round-trips a float exactly. NaN and infinity
        /// are not JSON numbers, so they fail the run instead of producing a
        /// trace no parser can read.
        private static string Number(float value)
        {
            if (float.IsNaN(value) || float.IsInfinity(value))
            {
                throw new InvalidOperationException(
                    $"the simulation produced a non-finite value ({value}); a trace cannot " +
                    "represent it. Find the division by zero.");
            }
            return value.ToString("G9", CultureInfo.InvariantCulture);
        }

        // ------------------------------------------------------------------
        // Input
        // ------------------------------------------------------------------

        /// One stdin line to one tick of intent. An empty line means "nothing
        /// held", which is what a driver that has nothing to say should send.
        private static Intents IntentsFrom(string line)
        {
            if (string.IsNullOrWhiteSpace(line)) return Intents.None;
            return IntentsFrom(Json.Parse(line));
        }

        private static Intents IntentsFrom(object value)
        {
            if (value == null) return Intents.None;
            if (!(value is Dictionary<string, object> obj))
            {
                throw new FormatException("each input must be a JSON object");
            }
            return new Intents(Json.Flag(obj, "nudge_up"), Json.Flag(obj, "nudge_down"));
        }

        /// `{"version": 1, "inputs": [ {..}, .. ]}`. A missing path, or `-`,
        /// means "nothing held on every tick".
        private static List<Intents> ReadScript(string path)
        {
            var inputs = new List<Intents>();
            if (string.IsNullOrEmpty(path) ||
                string.Equals(path, "-", StringComparison.Ordinal))
            {
                return inputs;
            }
            if (!File.Exists(path))
            {
                throw new FileNotFoundException($"input script not found: {path}", path);
            }

            if (!(Json.Parse(File.ReadAllText(path)) is Dictionary<string, object> root))
            {
                throw new FormatException("an input script must be a JSON object");
            }
            if (!root.TryGetValue("version", out var version) ||
                !(version is double number) || (int)number != 1)
            {
                throw new FormatException("an input script must declare \"version\": 1");
            }
            if (root.TryGetValue("inputs", out var raw))
            {
                if (!(raw is List<object> list))
                {
                    throw new FormatException("\"inputs\" must be an array");
                }
                foreach (var element in list) inputs.Add(IntentsFrom(element));
            }
            return inputs;
        }

        // ------------------------------------------------------------------
        // Command line
        // ------------------------------------------------------------------

        private static string OptionalArg(string name)
        {
            var args = Environment.GetCommandLineArgs();
            for (int i = 0; i < args.Length - 1; i++)
            {
                if (string.Equals(args[i], name, StringComparison.Ordinal)) return args[i + 1];
            }
            return null;
        }

        private static string StringArg(string name) =>
            OptionalArg(name)
            ?? throw new ArgumentException($"missing required argument {name}", nameof(name));

        private static ulong ULongArg(string name) =>
            ulong.Parse(StringArg(name), CultureInfo.InvariantCulture);

        private static int IntArg(string name) =>
            int.Parse(StringArg(name), CultureInfo.InvariantCulture);
    }
}
