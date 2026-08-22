# Agent guide

A deterministic, headlessly-verifiable game template. Unity 6000.0.45f1 + C#.

This starter contains a placeholder, not a game. Replace it with whatever the
task asks for; keep the harness, the boundaries and the verification loop.

## The one command

```
just verify
```

Green means done. Red means not done. Nothing else counts as evidence — not
"it compiles", not "it looks right", not your own reasoning about the code.

`just test-sim` (~5s, no GPU) is the fast inner loop. Every recipe launches a
fresh batchmode editor; measured on an M3 Max, `verify` is ~12s warm and ~22s
with an empty `Library/` — inside the command ceiling, so run it before you
claim to be finished. Also: `just check` (compile only), `just coverage` (~5s,
`Assets/Sim/` line coverage), `just bless` (golden images), `just run`.

## Layout

| Assembly | Contains | GPU? |
|---|---|---|
| `Assets/Sim` | All game rules and state. The source of truth. | **No.** Deliberately cannot — `Sim.asmdef` sets `"noEngineReferences": true`, so `UnityEngine` will not even resolve. |
| `Assets/View` | Rendering, input, window, capture harness. Reads `Sim`, never writes to it. | Yes |
| `Assets/Analyzers` | Vendored Roslyn analyzers. Not game code. | — |

**Put game logic in `Assets/Sim`.** A rule in `Assets/View` cannot be tested
without a GPU and will not be replayable or shareable between machines. This is
the single most important convention in the repo.

## Determinism rules — enforced, not advisory

The simulation must produce byte-identical results from the same seed and
inputs. Replay tests, rollback, and desync detection all depend on it.

1. **One `SimState.Step()` is exactly one tick.** Never drive game logic from
   `Update`, coroutines, or `Time.deltaTime`.
2. **Read `Intents`, never `Input`.** A fixed step runs 0, 1, or many times per
   frame; device state is frame-scoped, so reading it directly drops and
   duplicates inputs. `GameRunner` latches devices → intent once per frame.
3. **No wall clock in `Sim`** — no `DateTime`, `Stopwatch`, `Time`. Use
   `SimState.Tick`. → **compile error `SIM0001`**
4. **All randomness comes from `SimRng`**, part of snapshotted state. No
   `UnityEngine.Random`, no `System.Random`, no OS entropy. → **`SIM0001`**
5. **Never reference `UnityEngine` from `Sim`** — engine math types change
   between versions, which is why `Sim` has its own `Vec2`. → **`SIM0002`**
6. **Sort order-sensitive passes on `SimId`,** never on list position — it
   shifts when entities are added or removed. Never iterate a `Dictionary` or
   `HashSet` inside a tick.
7. **No parallel reductions in `Sim`.** Float addition is not associative.
8. **No C# events or queues for simulation events.** They drain on a frame
   boundary, not a tick boundary. Use per-tick state (`TickEvents`).

`SIM####` comes from `Assets/Analyzers/Starter.Analyzers.dll` (source and ban
list in `tools/analyzer/`). It is an error, not a warning: nondeterminism does
not compile. If a determinism test fails, **find the nondeterminism — do not
relax the assertion.**

## The tick pipeline declares what it writes

`SimStage` is a total order, and each stage carries a `[Writes(...)]` attribute
naming the `SimState` members it may change. `StageAccessTests` runs the stages
and compares those declarations against what actually changed, so a stage in the
enum but not in `SimState.Stages`, a stage writing undeclared state, and a stale
declaration all fail — with the exact attribute to paste in the message. Adding
state (a counter, a spawned entity) means adding its name to the `[Writes(...)]`
of every stage that touches it. That is the point: two stages writing the same
field is what tick ordering exists to make explicit.

## Linting

`just lint` fails on **any** Roslyn diagnostic in `Assets/`, the same bargain as
`clippy -D warnings`. Three analyzer families are active: `SIM####` (this
repo's determinism analyzer, error), `UNT####` (`Microsoft.Unity.Analyzers` —
empty `Update`, tag `==`, allocating `GetComponent`; warning) and `CA####`
(`Microsoft.CodeAnalysis.NetAnalyzers` — .NET correctness, reliability,
performance; warning). Severities live in `Assets/Default.globalconfig`; fix the
code rather than lowering one. `Directory.Build.props` and
`TreatWarningsAsErrors` do nothing here — Unity does not compile via MSBuild.

## Testing

Write the cheapest test that would catch the bug:

1. **Simulation test** (`Assets/Tests/SimTests/`) — pure logic, no scene, no
   GameObject, no GPU. Most changes need only this.
2. **Replay test** — record inputs, assert the hash chain is stable. One replay
   test catches most determinism regressions at once.
3. **Rendering test** (`Assets/Tests/RenderTests/`) — real graphics device, real
   pixels, no window. For bugs *invisible to logic tests*: a quad that never
   spawns, a camera that frames nothing, a view that stops following the sim.

For rendering, prefer **invariants** ("something rendered", "ink is in the
middle band"), then **relational** ("holding up moved its pixels up"), then
**golden image** — only when the exact look is under test. The first two survive
colour tweaks and GPU differences. A failing pixel comparison prints the differing-pixel count, bounding box and
centroid and writes `artifacts/render/*.{actual,expected,diff}.png`. **Open the
diff.** Scattered pixels are GPU rounding; a solid block means geometry moved.
Tolerance exists for the former, never the latter. The baseline is in
`Assets/Tests/RenderTests/golden/`; `just bless` rewrites it — then look at it.

- **Everything the player sees must be drawn through the camera.** `just film`
  and the rendering tests read exactly the pixels `camera.Render()` wrote.
  IMGUI — `OnGUI`, `GUI.Label`, `GUILayout` — is emitted in a separate phase of
  the player loop that no camera render touches, so a HUD built that way looks
  right in a window and is absent from every captured frame, every golden image
  and every filmed PNG. Draw it as geometry instead, in `Assets/View`, so the
  windowed player and the capture harness get the same thing: `Hud` is the
  worked example — a 5x7 bitmap font emitted as `Starter/Flat` quads under the
  view root, updated from `GameView.Sync`, with `Hud.ScreenRegion` naming the
  pixels a test should assert on.
- **A skipped test is not a passing test.** Render tests skip themselves with no
  GPU adapter. That is reported loudly and `just ci` fails on any skip: green
  over zero pixels is the worst possible outcome.
- **`GameView` draws only entity kinds it has a visual for**, so adding a kind
  to `Sim` cannot silently change every frame. Give a new kind a visual in
  `GameView.HasVisual`/`CreateQuad` when you want to see it.

**Gameplay is not correctness.** Tests catch "nothing moves"; not "it moves so
fast the game is unplayable". When you change a tuning constant, assert on the
*consequence* you care about, measured over a run — how long something takes,
how often it happens, where it ends up — not on the constant you changed.

## Probing a run

- `just probe SEED` — a long-lived process. It writes a tick-0 line before
  reading anything, then reads **one JSON input object per stdin line** and
  writes **one trace line per tick** to stdout, flushed. An empty line means
  "nothing held"; `quit` or EOF exits 0. stdout carries the trace and nothing
  else; the engine log goes to `artifacts/probe.log`.
- `just probe-file SEED TICKS SCRIPT OUT` — the same trace for a recorded run.
  `SCRIPT` is `{"version": 1, "inputs": [{..}, ..]}`, or `-` for none; past its
  end the input is all-false. `OUT` gets one line per tick from tick 1; it exits
  non-zero if it could not run every tick.
- `just film SEED TICKS SCRIPT OUTDIR` — up to twelve evenly spaced frames as
  `frame_0000.png`, … Same capture path as the render tests, so it needs a GPU.

Every line:

```json
{"tick": 1, "hash": "0x1234abcd...", "state": { ... }, "events": ["bounce"]}
```

`hash` is `StateHash()` in lowercase hex; `events` is an array of strings.
`state` is **game-defined**: expose the values that describe what the game is
doing right now, in a stable machine-readable shape, as finite JSON numbers that
round-trip a float. Same seed and same input lines give a byte-identical trace.

## Unity 6000.0.45f1 batchmode notes

Your training data is older than this Unity and most Unity CI advice online is
wrong for it. Trust the compiler over your memory; `docs/unity-6-notes.md` has
the full list with measurements.

| You may remember | Unity 6000.0.45f1 |
|---|---|
| `-quit` with `-runTests` | **Never combine them.** The editor exits before the runner starts: exit 0, no results file, a false green. |
| `"optionalUnityReferences": ["TestAssemblies"]` | Removed. Use `"overrideReferences": true`, `"precompiledReferences": ["nunit.framework.dll"]`, `"defineConstraints": ["UNITY_INCLUDE_TESTS"]`, `"includePlatforms": ["Editor"]`. |
| test packages are discovered automatically | `Packages/manifest.json` needs `"testables": ["com.unity.test-framework"]`, or **zero** tests are discovered and the run reports success over nothing. |
| `-nographics` is always safe in CI | It installs a Null graphics device and every pixel capture comes back empty. `just test-render` runs **without** it. |
| exit code 0 means all tests passed | Only if a results file exists. `tools/report.mjs` checks both, and fails on `total="0"`. |
| analyzers live in the `.csproj` | Analyzer DLLs need the `RoslynAnalyzer` asset label; severities go in `Assets/Default.globalconfig`. `.editorconfig` is ignored, and so is `BannedSymbols.txt` — this editor never forwards additional files to the compiler. |

Pin the version (`ProjectSettings/ProjectVersion.txt`). Do not upgrade Unity as
a side effect of another task.

## Boundaries

✅ Always: put game rules in `Assets/Sim`; run `just verify` before finishing;
add a test for behaviour you changed.

⚠️ Ask first: adding a package to `Packages/manifest.json`; changing `TICK_HZ`,
`StateHash`, the replay format or the trace format (compatibility surfaces);
upgrading Unity or a render pipeline.

🚫 Never: `[Ignore]` or delete a failing test to make `verify` pass; widen a
determinism assertion; lower a severity in `Assets/Default.globalconfig` to
silence a diagnostic; delete an analyzer from `Assets/Analyzers/`; add a
`UnityEngine` reference to `Sim.asmdef`; add game logic to `Assets/View`; put
anything the player must see behind `OnGUI`; `git commit --no-verify`. If a test is genuinely wrong, say so explicitly and
explain why — do not silently weaken it.
