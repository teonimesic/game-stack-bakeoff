# Agent guide

Deterministic, headlessly-verifiable Pong. TypeScript + three.js.

## Commands

| Command       | Time  | What it proves                                                              |
| ------------- | ----- | --------------------------------------------------------------------------- |
| `just fast`   | ~2s   | Types (both projects) + all 53 sim tests. **Run after every edit.**         |
| `just verify` | ~5s   | THE gate. fmt, lint, sim tests, real-pixel render tests.                    |
| `just watch`  | —     | Sim tests re-run on save.                                                   |
| `just warm`   | ~2min | One-time: install deps + Chromium. Run first if `node_modules/` is missing. |

`just verify` green means done. Red means not done. Nothing else counts as
evidence — not "it type-checks", not "it looks right", not your own reasoning.
`just --list` has the rest (`bless`, `run`, `coverage`, `api-notes`).

## Layout

| Module     | Contains                                                            | Browser?    |
| ---------- | ------------------------------------------------------------------- | ----------- |
| `src/sim`  | All game rules and state. The source of truth.                      | **Cannot.** |
| `src/view` | Rendering, input, capture harness. Reads `sim`, never writes to it. | Yes         |

**Put game logic in `src/sim`.** A rule in `src/view` cannot be tested without a
browser and will not be replayable or networkable.

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
   read that file if you want to see exactly what is rejected.

## Determinism rules — load-bearing, not style

The simulation must produce byte-identical results from the same seed and
inputs. Replay, rollback and desync detection all depend on it.

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
   and `Math.cos`/`Math.sin` are implementation-defined by the spec — keep them
   in `serveVelocity` rather than spreading them through the tick.
6. **Don't route simulation events through callbacks or DOM events.** They fire
   on the frame, not the tick. Use per-tick state (`TickEvents`).

If a determinism test fails, **find the nondeterminism — do not relax the
assertion.** An exact hash comparison that becomes approximate is worthless.

## Testing

Write the cheapest test that would actually catch the bug:

1. **Simulation test** (`tests/sim/`) — pure logic, milliseconds, no browser.
   Most changes need only this.
2. **Replay test** — record inputs, assert the hash chain is stable. One replay
   test catches most determinism regressions at once.
3. **Rendering test** (`tests/render/`) — real GL, real pixels, no window. For
   bugs _invisible to logic tests_: a mesh that never spawns, a camera that
   frames nothing, a view that stops following the sim.

For rendering, prefer assertions in this order: **invariants** ("something
rendered", "ink is in the left sixth") → **relational** ("holding up moved the
paddle's pixels up") → **golden image** (only when the exact look is under test).
The first two survive colour tweaks and rasteriser differences; golden does not.

Every render failure writes PNGs to `tests/render/artifacts/` and prints their
absolute paths, a bounding box, a max channel delta and an 8×5 region map — you
should not need to open an image to know what broke. A wide, low-delta diff is a
colour/AA change; a dense diff in a small box is geometry that moved.
**Tolerance exists for cross-vendor rounding, not misplaced geometry** — if a
golden test fails by a lot it found a real bug; do not widen the budget.

## Gameplay is not correctness

A change can pass every test and still make the game worse. Tests catch "the ball
does not move"; they do not catch "the ball is unplayably fast". When you change
`PADDLE_SPEED`, `BALL_SPEEDUP` or `MAX_BALL_SPEED`, add or update an assertion on
the _consequence_ — rally length, time-to-score, speed after N hits — in
`tests/sim/playability.test.ts`, not just on the constant.

## Versions

Exact pins, no ranges: `three` 0.185.1, `@types/three` 0.185.4, `playwright`
1.62.1, `vitest` 4.1.10, `typescript` 6.0.3, `esbuild` 0.28.2, `eslint` 10.8.1,
Node 22. Your training data is older than these. Trust `tsc` over your memory and
over the docs; do not upgrade three as a side effect of another task.

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
the replay format, or the wire protocol; upgrading three, Playwright or TypeScript.

🚫 Never: `.skip`/`.todo` or delete a failing test to make `verify` pass; widen a
determinism assertion or a pixel budget; `eslint-disable` a `src/sim` firewall
rule; `git commit --no-verify`; put game logic in `src/view`. If a test is
genuinely wrong, say so explicitly and explain why — do not silently weaken it.
