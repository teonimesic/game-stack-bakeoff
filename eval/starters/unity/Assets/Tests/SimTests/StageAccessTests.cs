// What this replaces, and why it is not the same thing.
//
// The Rust/Bevy sibling asserts its FixedUpdate schedule has no *ambiguous
// system pairs*: two systems with conflicting data access and no ordering edge
// between them. That check exists because Bevy's scheduler is a partial order —
// it is free to run unordered systems in either order, or in parallel, so an
// undeclared conflict is a real coin flip.
//
// C# has no such scheduler here, and adding one would be strictly worse. The
// tick is a sequential total order (`SimState.Stages`), so "two stages with no
// ordering edge" cannot exist: every pair is ordered by construction. Porting
// the ambiguity check as-is would produce a test that can never fail.
//
// What IS reachable, and is arguably the stronger property, is the half of
// Bevy's guarantee that comes from its type system rather than its scheduler:
// every system declares the state it touches, and the declaration is checked
// against reality. Bevy gets that from `Query<&mut Transform>`. Here each stage
// declares its writes with `[Writes(...)]`, and these tests run the stages and
// record, by reflection over SimState, what each one actually changed.
//
// That catches the things that actually go wrong in this codebase:
//   - a stage quietly starts writing state that belongs to a later stage
//     (the read-stale-data bug that ordering was supposed to prevent)
//   - a new stage is added to the enum but never runs
//   - a stage is removed from the pipeline but left in the enum
//   - a declaration goes stale and stops describing the code

using System;
using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using System.Reflection;
using System.Text;
using NUnit.Framework;
using Starter.Sim;

namespace Starter.Sim.Tests
{
    public class StageAccessTests
    {
        private const int ScenarioTicks = 1800;

        [Test]
        public void EveryStageIsInThePipelineExactlyOnceAndInOrder()
        {
            var declared = (SimStage[])Enum.GetValues(typeof(SimStage));
            Array.Sort(declared);

            CollectionAssert.AreEqual(declared, SimState.Stages,
                "SimState.Stages must run every SimStage exactly once, in enum order. " +
                "A stage in the enum but not in Stages never runs; a stage listed twice " +
                "runs twice per tick. Both silently change every recorded replay.");
        }

        [Test]
        public void NoStageWritesStateItDoesNotDeclare()
        {
            var recorded = RecordWritesOverAScenario();
            var complaints = new List<string>();

            foreach (var stage in SimState.Stages)
            {
                var allowed = DeclaredWrites(stage);
                var undeclared = recorded[stage]
                    .Where(member => !allowed.Any(a => Covers(a, member)))
                    .OrderBy(m => m, StringComparer.Ordinal)
                    .ToList();
                if (undeclared.Count == 0) continue;

                // Report every stage and every member at once, with the exact
                // attribute to paste. Failing on the first one turns a two-line
                // fix into a guessing game played one editor launch at a time.
                var merged = allowed.Concat(undeclared)
                    .OrderBy(m => m, StringComparer.Ordinal);
                complaints.Add(
                    $"SimStage.{stage} wrote {string.Join(", ", undeclared.Select(m => "SimState." + m))} " +
                    "without declaring it.\n" +
                    $"    currently: [Writes({string.Join(", ", allowed.Select(Quote))})]\n" +
                    $"    should be: [Writes({string.Join(", ", merged.Select(Quote))})]");
            }

            Assert.IsEmpty(complaints,
                "A stage wrote simulation state its [Writes(...)] attribute does not " +
                "cover.\n\n" + string.Join("\n\n", complaints) + "\n\n" +
                "Either move the write to the stage that owns that state, or widen the " +
                "declaration on SimStage above. Two stages writing the same field is " +
                "exactly what tick ordering exists to make explicit — declaring it is how " +
                "the next reader finds out.");
        }

        private static string Quote(string member) => "\"" + member + "\"";

        [Test]
        public void NoStageDeclaresStateItNeverWrites()
        {
            // The other direction: a declaration that has gone stale is worse
            // than no declaration, because it makes the audit above too
            // permissive without anyone noticing.
            var recorded = RecordWritesOverAScenario();

            foreach (var stage in SimState.Stages)
            {
                foreach (var declared in DeclaredWrites(stage))
                {
                    Assert.IsTrue(recorded[stage].Any(m => Covers(declared, m)),
                        $"SimStage.{stage} declares it writes SimState.{declared}, but over " +
                        $"{ScenarioTicks} ticks of a scripted run it never did. " +
                        "Remove the stale entry from its [Writes(...)] attribute, or the " +
                        "audit above stops catching real cross-stage writes.");
                }
            }
        }

        [Test]
        public void RunStageRejectsAStageItCannotRun()
        {
            // Guards the failure mode where a new SimStage is added to the enum
            // and to Stages, but RunStage's switch is never updated: the stage
            // would silently do nothing every tick.
            var state = new SimState(1);
            Assert.Throws<ArgumentOutOfRangeException>(
                () => state.RunStage((SimStage)9999, Intents.None));
        }

        // ------------------------------------------------------------------
        // Observation
        // ------------------------------------------------------------------

        /// Run a scenario one stage at a time, recording which SimState members
        /// each stage changed.
        ///
        /// The scenario must exercise every branch a stage can take, or a live
        /// declaration looks stale. It steers hard and often, in both
        /// directions, so that input handling, integration and wall reflections
        /// all run many times over the run.
        private static Dictionary<SimStage, HashSet<string>> RecordWritesOverAScenario()
        {
            var recorded = new Dictionary<SimStage, HashSet<string>>();
            foreach (var stage in SimState.Stages)
            {
                recorded[stage] = new HashSet<string>(StringComparer.Ordinal);
            }

            var state = new SimState(3);
            var before = new Dictionary<string, string>(StringComparer.Ordinal);
            var after = new Dictionary<string, string>(StringComparer.Ordinal);

            for (int tick = 0; tick < ScenarioTicks; tick++)
            {
                var intents = ScenarioIntents(state, tick);
                foreach (var stage in SimState.Stages)
                {
                    Fingerprint(state, before);
                    state.RunStage(stage, intents);
                    Fingerprint(state, after);

                    foreach (var pair in after)
                    {
                        if (!before.TryGetValue(pair.Key, out var was) || was != pair.Value)
                        {
                            recorded[stage].Add(pair.Key);
                        }
                    }
                }
            }
            return recorded;
        }

        /// Steer towards the far side of the arena from wherever the body
        /// currently is, flipping every few seconds, so the run keeps meeting
        /// walls instead of settling into one corner.
        private static Intents ScenarioIntents(SimState state, int tick)
        {
            bool chaseUp = (tick / 97) % 2 == 0;
            float y = state.Marker.Position.Y;
            bool idle = (tick / 31) % 5 == 0;
            if (idle) return Intents.None;
            return chaseUp
                ? new Intents(y < Constants.ARENA_HALF_HEIGHT * 0.5f, false)
                : new Intents(false, y > -Constants.ARENA_HALF_HEIGHT * 0.5f);
        }

        private static string[] DeclaredWrites(SimStage stage)
        {
            var field = typeof(SimStage).GetField(stage.ToString());
            var attribute = field?.GetCustomAttribute<WritesAttribute>();
            Assert.NotNull(attribute,
                $"SimStage.{stage} has no [Writes(...)] attribute. Every stage must " +
                "declare the SimState members it writes so the audit can check it.");
            return attribute.Members;
        }

        /// A declared path covers itself and everything nested under it, so
        /// "Events" covers "Events.Bounces" and "Entities" covers both
        /// "Entities.Count" and "Entities[].Position". Declare the coarse name
        /// when a stage owns the whole thing (spawning an entity), the precise
        /// one when it only moves part of it.
        private static bool Covers(string declared, string actual) =>
            actual.Equals(declared, StringComparison.Ordinal) ||
            actual.StartsWith(declared + ".", StringComparison.Ordinal) ||
            actual.StartsWith(declared + "[", StringComparison.Ordinal);

        // ------------------------------------------------------------------
        // Reflection-based state fingerprinting
        // ------------------------------------------------------------------
        //
        // Keys are member paths from SimState. A collection is expanded into
        // per-member paths ("Entities[].Position") plus a count, so a body that
        // moved is attributed to Position rather than to "the list changed".
        // Nothing here is hard-coded to the current fields: a member added to
        // SimState shows up automatically, which is the point.

        private static void Fingerprint(SimState state, Dictionary<string, string> into)
        {
            into.Clear();
            foreach (var member in Members(typeof(SimState)))
            {
                Expand(member.Name, member.Read(state), into, depth: 0);
            }
        }

        private static void Expand(
            string path, object value, Dictionary<string, string> into, int depth)
        {
            if (value == null) { into[path] = "null"; return; }

            if (value is IEnumerable enumerable && !(value is string))
            {
                var items = enumerable.Cast<object>().ToList();
                into[path + ".Count"] = items.Count.ToString(CultureInfo.InvariantCulture);

                var element = items.FirstOrDefault();
                if (element != null && !IsLeaf(element.GetType()) && depth < 3)
                {
                    foreach (var member in Members(element.GetType()))
                    {
                        var joined = new StringBuilder();
                        foreach (var item in items)
                        {
                            joined.Append(Leaf(member.Read(item))).Append('|');
                        }
                        into[path + "[]." + member.Name] = joined.ToString();
                    }
                }
                else
                {
                    into[path] = string.Join("|", items.Select(Leaf));
                }
                return;
            }

            if (IsLeaf(value.GetType()) || depth >= 3)
            {
                into[path] = Leaf(value);
                return;
            }

            foreach (var member in Members(value.GetType()))
            {
                Expand(path + "." + member.Name, member.Read(value), into, depth + 1);
            }
        }

        /// Value types with no interesting structure of their own, plus
        /// simulation structs whose fields are private (SimRng) — those are
        /// compared whole, including private state, via Leaf().
        private static bool IsLeaf(Type type) =>
            type.IsPrimitive || type.IsEnum || type == typeof(string) ||
            type == typeof(decimal) || type == typeof(Vec2) || type == typeof(SimRng) ||
            Nullable.GetUnderlyingType(type) != null;

        /// Exact textual value, including private fields, so a change to
        /// SimRng's internal state counts as a write to Rng.
        private static string Leaf(object value)
        {
            if (value == null) return "null";
            var type = value.GetType();
            if (type.IsPrimitive || type.IsEnum || value is string || type == typeof(decimal))
            {
                return Convert.ToString(value, CultureInfo.InvariantCulture);
            }

            var parts = new StringBuilder(type.Name).Append('(');
            foreach (var field in AllFields(type))
            {
                parts.Append(field.Name).Append('=').Append(Leaf(field.GetValue(value))).Append(',');
            }
            return parts.Append(')').ToString();
        }

        private static readonly Dictionary<Type, FieldInfo[]> FieldCache =
            new Dictionary<Type, FieldInfo[]>();

        private static FieldInfo[] AllFields(Type type)
        {
            if (FieldCache.TryGetValue(type, out var cached)) return cached;
            var fields = type
                .GetFields(BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic)
                .OrderBy(f => f.Name, StringComparer.Ordinal)
                .ToArray();
            FieldCache[type] = fields;
            return fields;
        }

        private readonly struct Member
        {
            public string Name { get; }
            private readonly Func<object, object> _read;

            public Member(string name, Func<object, object> read) { Name = name; _read = read; }

            public object Read(object owner) => _read(owner);
        }

        private static readonly Dictionary<Type, Member[]> MemberCache = new Dictionary<Type, Member[]>();

        private static Member[] Members(Type type)
        {
            if (MemberCache.TryGetValue(type, out var cached)) return cached;

            // Fields, plus auto-properties (they have a compiler-generated
            // backing field). Computed properties such as `SimState.Marker` are
            // views onto state that is already covered, so counting them would
            // report the same write twice under two names.
            var members = type
                .GetFields(BindingFlags.Instance | BindingFlags.Public)
                .Select(f => new Member(f.Name, f.GetValue))
                .Concat(type
                    .GetProperties(BindingFlags.Instance | BindingFlags.Public)
                    .Where(p => p.CanRead && p.GetIndexParameters().Length == 0 &&
                                type.GetField($"<{p.Name}>k__BackingField",
                                    BindingFlags.Instance | BindingFlags.NonPublic) != null)
                    .Select(p => new Member(p.Name, owner => p.GetValue(owner))))
                .OrderBy(m => m.Name, StringComparer.Ordinal)
                .ToArray();

            MemberCache[type] = members;
            return members;
        }
    }
}
