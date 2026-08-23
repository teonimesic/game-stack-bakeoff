# Agent guide

Deterministic, headlessly-verifiable games. TypeScript + three.js.

This starter contains a placeholder, not a game. Replace it with whatever the
task asks for; keep the harness, the boundaries and the verification loop.

## Commands

| Command       | Time  | What it proves                                                              |
| ------------- | ----- | --------------------------------------------------------------------------- |
| `just fast`   | ~2s   | Types (both projects) + all 53 sim tests. **Run after every edit.**         |
| `just verify` | ~5s   | THE gate. fmt, lint, sim tests, real-pixel render tests.                    |
| `just watch`  | —     | Sim tests re-run on save.                                                   |
| `just warm`   | ~2min | One-time: install deps + Chromium. Run first if `node_modules/` is missing. |

`just verify` green means done. Red means not done. Nothing else is evidence —
not "it type-checks", not "it looks right", not your own reasoning. A Stop hook
re-runs it when you try to finish, so ending the turn red does not work.
`just --list` has the rest (`bless`, `run`, `probe`, `film`).

## Layout

| Module     | Contains                                                            | Browser?    |
| ---------- | ------------------------------------------------------------------- | ----------- |
| `src/sim`  | All game rules and state. The source of truth.                      | **Cannot.** |
| `src/view` | Rendering, input, capture harness. Reads `sim`, never writes to it. | Yes         |

**Put game logic in `src/sim`.** A rule in `src/view` needs a browser to test
and will never replay.

**Everything the player sees must go through the renderer.** `just film` and
`tests/render` read back the pixels of an offscreen render target, not the page,
so a `#hud` div, an overlaid second canvas or a `console.log` is not in a single
captured frame — a scoreboard built that way looks right in `just run` and is
absent from every PNG you film. Draw it as geometry instead. The HUD in
`src/view/index.ts` is the worked example: a screen-space `OrthographicCamera` in
pixel units and a `CanvasTexture` on a quad, composited over the arena by
`renderFrame()` — the one call both `main.ts` and `capture.ts` make, so the
window and the capture cannot diverge. Its glyphs are a 5x7 bitmap filled with
`fillRect`, not `fillText`: installed fonts differ between your machine and CI,
and the pixels here are compared byte for byte.

## The capture page: assets, and the one thing it will not do

`just film` and `tests/render` render in a headless page served from `public/` at
a real origin, so **a relative asset URL resolves exactly as it does under
`just run`** — `./sprites/hero.png` is the same file in both. `TextureLoader`,
`GLTFLoader` and plain `fetch` all work.

**But `capture()` is synchronous.** It steps the simulation, renders one frame
and reads the pixels back inside a single call, which is what makes a captured
frame a pure function of `(seed, ticks, inputs)`. A loader, an `<img>` decode or
a `fetch` resolves on a LATER task, so it cannot finish inside a capture: start
one there and the frame is taken with the texture still pending, showing an
untextured quad in every filmed PNG while `just run` looks perfect.

So load assets in **`window.__capturePreload`**, which the harness awaits once
before each capture. Resolve your loaders there into a module-level cache that
`createView()` can then read synchronously:

```ts
let sheet: THREE.Texture | null = null;
window.__capturePreload = async () => {
  sheet ??= await new THREE.TextureLoader().loadAsync('./sprites/hero.png');
};
```

If the hook throws, the capture fails loudly rather than filming a frame with
its assets missing. Generating art in code (`DataTexture`, `CanvasTexture`) is
still the simplest thing that works and needs no hook at all.

**Time in a captured frame is virtual.** `performance.now()` and `Date.now()`
return the time of the tick being captured, not wall time — the same tick always
gives the same reading, so captures stay reproducible, but the value _advances_
across the 12 frames of `just film`. `Math.random()` is seeded for the same
reason. Note that each capture builds a **fresh view with no history**, so
`clock.getDelta()` has nothing to measure: drive animation from the simulation
tick, or from the absolute time, not from a frame-to-frame delta.

## Drawing many things: reach for `Points`, not `InstancedMesh`

three 0.185 ships **no particle system and no emitter**. `Points`, `Sprite`,
`InstancedMesh` and `BatchedMesh` are batching primitives; lifetimes, spawning
and fading are yours to write, and that is real work — budget for it before
promising sparks. `Points` needs nothing added to this template:

```ts
const geometry = new THREE.BufferGeometry();
geometry.setAttribute('position', new THREE.BufferAttribute(new Float32Array(n * 3), 3));
scene.add(new THREE.Points(geometry, new THREE.PointsMaterial({ color, size: 10 })));
```

Measured here, on the SwiftShader rasteriser every render test and `just film`
uses — mean ms per 640x400 frame rendered and read back:

| objects | N separate `Mesh` | one `InstancedMesh` | one `Points` |
| ------- | ----------------- | ------------------- | ------------ |
| 300     | 5.06              | 4.73                | 0.49         |
| 2 000   | 30.19             | 28.47               | 0.69         |
| 10 000  | 149.16            | 140.68              | 1.71         |

**`InstancedMesh` buys about 6% here, at every size.** It is not the cheap
option it is on a hardware GPU, and it is not what to reach for. `Points` is
10-87x, and that is the choice worth making deliberately.

Two things about `Points` under this template's **orthographic** camera.
`PointsMaterial.size` is in **device pixels, not world units**, and
`sizeAttenuation` is ignored — three's point shader only attenuates when the
projection matrix is perspective, so the size you want is
`worldSize * VIEW_HEIGHT / (2 * ARENA_HALF_HEIGHT)`. And `setDrawRange` draws
fewer points than the buffer holds without reallocating it.

Keep it in proportion: `just film` on the pristine starter costs 3.9 s of CPU
for twelve frames, so at 300 objects the whole difference is ~55 ms. This is
about how the game feels at thousands of sprites, not about any harness timing.

## The firewall around src/sim

Three overlapping mechanisms; each catches what the others miss. You will be told
when you trip one — this is here so the message makes sense.

1. **`tsconfig.sim.json`** re-checks `src/sim` with `lib: ["ES2023"]`,
   `types: []`. `document`, `window`, `performance`, `process` are **compile
   errors**. Cannot be silenced with a comment. Run by `just check`.
2. **`eslint.config.js`** bans, inside `src/sim` only: importing `three`,
   `src/view` or any `node:*` builtin; `Math.random`, `Date.now`, `new Date`,
   `crypto.getRandomValues`; `setTimeout`/`queueMicrotask`; `async`/`await`/
   `new Promise`; `Object.keys`; `.sort()` with no comparator. Each error says
   what to use instead.
3. **`tests/sim/boundary.test.ts`** walks the real import graph and scans every
   reachable file, so a dynamic `import()` or a transitive hop is caught too. It
   also feeds each rule a violating source string and asserts the checker fires —
   read it to see exactly what is rejected.

## Determinism rules — load-bearing, not style

The simulation must produce byte-identical results from the same seed and
inputs. Replay, rollback and desync detection depend on it.

1. **One tick is one `step()`, and `step()` runs `SIM_PIPELINE` in stage order.**
   Add systems to that array with an explicit stage; never call a system from
   inside another one.
2. **Read `Intents`, never key state.** A frame contains 0, 1, or many ticks, so
   device state is frame-scoped; reading it in a tick drops and duplicates
   inputs. `src/view/main.ts` converts devices → intent once per frame.
3. **Sort order-sensitive iteration on `SimId`** (`bySimId`), never on array
   position — array order changes when an entity is removed.
4. **All randomness comes from `world.rng`** (`SimRng`, part of the snapshot).
   `rng.rangeF32(lo, hi)` is how you place something randomly.
5. **f32 is a type, not a convention.** `Vec2` holds `F32`, a branded `number`
   whose only producer is `f32()`. `a.x + b.x` widens to plain `number` and
   **will not compile** as a coordinate — use `add`/`sub`/`scale`/`neg`/`vec2`
   from `src/sim/vec2.ts`. `stateHash` reads f32 bit patterns, so mixed precision
   silently makes the hash lossy. Two things the type cannot catch:
   `f32(a * b + c * d)` is one rounding, not three (round every intermediate),
   and `Math.cos`/`Math.sin` are implementation-defined — keep them out of the
   tick.
6. **Don't route simulation events through callbacks or DOM events.** They fire
   on the frame, not the tick. Use per-tick state (`TickEvents`).

If a determinism test fails, **find the nondeterminism — do not relax the
assertion.** An exact hash comparison that becomes approximate is worthless.

## Testing

Write the cheapest test that would actually catch the bug:

1. **Simulation test** (`tests/sim/`) — pure logic, milliseconds, no browser.
   Most changes need only this.
2. **Replay test** — record inputs, assert the hash chain is stable. One catches
   most determinism regressions at once.
3. **Rendering test** (`tests/render/`) — real GL, real pixels, no window. For
   bugs _invisible to logic tests_: a mesh that never spawns, a camera that
   frames nothing, a view that stops following the sim.

For rendering, prefer **invariants** ("something rendered", "ink is in the left
sixth") → **relational** ("holding up moved the entity's pixels up") → **golden
image** (only when the exact look is under test). The first two survive colour
tweaks and rasteriser differences; golden does not.

Every render failure writes PNGs to `tests/render/artifacts/` and prints their
paths, a bounding box, a max channel delta and an 8×5 region map, so you need
not open an image to know what broke. A wide, low-delta diff is a colour/AA
change; a dense diff in a small box is geometry that moved.
**Tolerance exists for cross-vendor rounding, not misplaced geometry** — a
golden test that fails by a lot found a real bug; do not widen the budget.

## Gameplay is not correctness

A change can pass every test and still make the game worse. Tests catch "nothing
moves"; not "it moves too fast to follow". When you change a tuning constant, assert on the _consequence you care about, measured
over a run_ — not on the constant you changed. Those assertions live in
`tests/sim/invariants.test.ts`.

## Probing a run

Three recipes watch a run from outside, no display.

**`just probe SEED`** is a live headless simulation on a pipe: one JSON trace
line per tick to stdout, one JSON input object per line from stdin, so a driver
can pick its next input from what just happened. Line one is tick 0, before any
input is read; then one input line in, one trace line out. An empty line means
"nothing pressed"; `quit` or EOF exits 0. stdout carries nothing but trace
lines — diagnostics go to stderr.

**`just probe-file SEED TICKS SCRIPT OUT`** is the same trace in batch: TICKS
ticks driven by a script `{"version": 1, "inputs": [{…}, …]}` (`-` for none),
written to OUT as JSON Lines from tick 1.

**`just film SEED TICKS SCRIPT OUTDIR`** renders at most 12 PNGs, evenly spaced
over `0..=TICKS`, into OUTDIR. It needs the browser, like the render tests.

Every trace line is exactly:

```json
{ "tick": 1, "hash": "0x1234abcd...", "state": {}, "events": ["bounce"] }
```

`hash` is `stateHash` as a lowercase `0x` unsigned 64-bit string; `events` is a
list of strings. `state` is game-defined: the values that describe what the game
is doing right now, in a stable machine-readable shape, as finite JSON numbers
precise enough to round-trip f32. Define it in `scripts/trace.ts`.

Same seed and inputs must produce a byte-identical trace.

## Versions

Exact pins, no ranges: `three` 0.185.1, `@types/three` 0.185.4, `playwright`
1.62.1, `vitest` 4.1.10, `typescript` 6.0.3, `esbuild` 0.28.2, `eslint` 10.8.1,
Node 22. Your training data is older than these. Trust `tsc` over your memory
and the docs; do not upgrade three as a side effect of another task.

- `docs/three-api.md` — signatures, **generated** from the installed types
  (`just api-notes`). Look here first.
- `docs/three-0.185-notes.md` — behaviours that compile and then misbehave
  (readback is bottom-up; colour management defaults ON; ~16 live GL contexts).
- `docs/three-llms.txt` — upstream's llms.txt, pinned, with the parts that are
  wrong for a bundled project called out.

## Boundaries

✅ Always: game rules in `src/sim`; `just fast` while working; `just verify`
before finishing; a test for behaviour you changed.

⚠️ Ask first: adding a dependency; changing the tick rate; changing `stateHash`,
the replay format, or the trace format; upgrading three, Playwright or TypeScript.

🚫 Never: `.skip`/`.todo` or delete a failing test to make `verify` pass; widen a
determinism assertion or a pixel budget; `eslint-disable` a `src/sim` firewall
rule; `git commit --no-verify`; put game logic in `src/view`. If a test is
genuinely wrong, say so explicitly and explain why — do not silently weaken it.

## When the gate itself is wrong

`just verify` and `just check` can be wrong, and this template's are not exempt. If one
of them is red on a tree you have not changed yet, that is a defect here, not in your
work.

1. **Say so in your final message**, naming the recipe and the file. Nothing else
   reports it, and the turns you spend on it are otherwise invisible.
2. **Repairing it is allowed** — it is not on the never-list above.
3. **A repair must leave the check able to fail.** Fix how the check handles the input
   it got wrong. Do not take that input out of what the check looks at: narrowing a
   check's scope — a skip list, an ignore entry, an exclusion — turns a check that
   fails wrongly into one that cannot fail at all. That is worse than the defect it
   replaces, and it reads as compliance.

**How to tell the two apart, before you move on:** put a real error into the thing the
gate stopped complaining about, run the gate, and confirm it goes red; then take the
error out. A repair you cannot make go red is not a repair — say so in your final
message and leave the gate red rather than shipping it.
