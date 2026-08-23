# three.js 0.185 (and friends) — behaviours that bite

> Three documents in this folder, deliberately split:
>
> - **`three-api.md`** — signatures, GENERATED from the installed `@types/three` (`just api-notes`).
>   Use it to find out what a call takes and returns.
> - **`three-llms.txt`** — the relevant part of upstream's llms.txt, pinned, with the parts that are
>   wrong for a bundled pinned project called out.
> - **this file** — behaviour, not signatures. The things that compile fine and then do the wrong
>   thing.

three ships a breaking release roughly every month and does not follow semver: the minor number
_is_ the version. Between r150 and r185 the colour pipeline, the addons path, the WebGPU entry
point and the type story all changed. If your training data predates 2026 you will confidently
write APIs that no longer exist.

**Descriptions of behaviour, never worked examples.** Stale example code is worse than no example
code: when the surrounding context already contains outdated API usage, the rate of deprecated
output goes up sharply, while a plain description of the current API helps. **Trust `tsc` over this
file, and this file over your memory.**

three signatures live in `three-api.md` and are generated. What follows is everything that is NOT
in the type signatures.

## Signatures the generator does not cover

```ts
// playwright 1.62.1
chromium.launch({ args }); // headless by default
page.addInitScript(source); // runs BEFORE page scripts, on every
// NAVIGATION — and `setContent` is not one.
// Register it, then `goto`. Registering it
// before a bare `setContent` leaves it DEAD,
// and a dead init script is invisible: the
// page just quietly keeps the real clock and
// an unseeded Math.random. See FINDINGS #101.
page.addScriptTag({ content }); // injects a bundle into the page
page.evaluate(fn, arg); // arg and result cross as JSON
```

## Behaviours that are easy to get wrong

- **`gl.readPixels` and `readRenderTargetPixels` return rows bottom-up.** Every `Frame` in this
  repo, and every PNG, is top-down. `capture.ts` flips once, on the way out. Flipping twice looks
  almost right and inverts every "moved up" assertion.
- **Colour management is ON by default (r152+).** With it on, a material colour is treated as sRGB,
  converted to linear for shading and back on output, so the byte you read back is a function of
  three's transfer functions rather than of your geometry. This repo turns it off and uses
  `LinearSRGBColorSpace` so `0.35` lands on screen as `round(0.35 * 255) = 89`.
- **Reading back from the default framebuffer requires `preserveDrawingBuffer: true`**, which is
  slow and easy to get subtly wrong. Render into a `WebGLRenderTarget` instead — readback from a
  target is always defined.
- **A browser tab allows only ~16 live WebGL contexts.** Capturing many frames in one page without
  `renderer.dispose()` + `forceContextLoss()` silently starts losing the oldest contexts, which
  shows up as blank frames, not as an error.
- **Playwright's `chromium.launch()` uses the headless shell**, which has no GPU and falls back to
  ANGLE + SwiftShader. That is the intended path here: software rasterisation is what makes the
  render tests reproducible on any machine. `--use-angle=swiftshader` pins it explicitly so a
  workstation with a discrete GPU produces the same pixels as CI.
- **`page.evaluate` marshals through JSON.** A `Uint8Array` does not survive; pixels come back
  base64-encoded (~1.4x the bytes, still far cheaper than a JSON array of numbers).
- **Node's `--experimental-strip-types` needs explicit `.ts` extensions** and rejects TypeScript
  that is not erasable (parameter properties, `enum`, namespaces). The imports here use `.ts`
  suffixes so `src/sim` runs under bare Node with no bundler at all.
- **Vitest 4 removed `poolOptions`.** Pool settings (`maxWorkers`, `isolate`) are top-level now.
- **`typescript-eslint` 8.x refuses TypeScript ≥ 6.1**, which is why TypeScript is pinned to 6.0.3
  rather than 7.x.

## Determinism inside a browser

The render harness injects `DETERMINISM_SCRIPT` before any page script runs: seeded `Math.random`,
frozen `Date.now`/`performance.now`, single-shot `requestAnimationFrame`. This is the same trick
three uses in its own screenshot CI. It does not make the _simulation_ deterministic — that is
`src/sim`'s job, with no help from the browser — it makes the _page_ deterministic, so a stray
animation frame or a UUID cannot change the pixels.

## Verifying a claim about the API

Do not guess, and do not trust this file blindly either — it will age too.

```
just api-notes                                                            # regenerate three-api.md
rg "readRenderTargetPixels" node_modules/@types/three/src/                # the real signature
rg "class WebGLRenderTarget" -A 30 node_modules/three/src/core/           # the real implementation
node -e "console.log(require('three/package.json').version)"              # what is installed
pnpm why three                                                            # who pulled it in
```

Reading the installed source under `node_modules` is the fastest ground truth available, and it is
always the version you are actually running against.
