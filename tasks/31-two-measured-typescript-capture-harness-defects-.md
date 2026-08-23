---
established_by: Radius zero on all 26 stored TS submissions, established four ways: no three loader constructed in any capture-reachable view file (comments and strings stripped, stripper positive-controlled), no AnimationMixer or Clock, no entropy or wall-clock read, and 206 of 216 filmed TS frames distinct with adjacent-frame diff 0.0370 and non-background fraction 0.229, both second-highest of the four arms. No published number is affected; nothing retracted. Defect 1 (null origin, relative fetch throws at URL parsing) reproduced and fixed. Defect 2 as filed is FALSE: performance.now measured 231.6 then 293.7 ms across a 60 ms sleep. It was not frozen because DETERMINISM_SCRIPT never ran at all -- addInitScript fires on navigation and setContent is not one -- leaving the page byte-indistinguishable from one with no init script registered: Math.random unseeded, both clocks on wall time. Fixing the origin activates the freeze, so all three were repaired together: page.route serving a real origin from public/, addInitScript before goto, a virtual clock at ticks/TICK_HZ*1000, and an awaited window.__capturePreload. Pinned in both directions by tests/render/capture-environment.test.ts (8 tests) against three mutants: setContent reddens 7, the frozen clock reddens the clock test, an unawaited preload reddens 2; the sweep also caught a vacuous test of my own. just verify green at 53 sim + 14 render with the golden frame unchanged, starter_gate_control --stack ts green on pristine and still red on a plant, verify_blind BLIND on an out-of-repo copy, starter_parity no drift. FINDINGS #101, tenth comparability break recorded in eval/RUNS.md, the ts starter AGENTS.md documents the residual synchronous-capture limitation, and the starter doc note that said addInitScript must precede setContent is corrected. Filed task 48: template-ts carries the identical pre-fix harness and is a second live tree. Branch task-31-ts-capture-defects, commit da1db9e, not pushed.
id: 31
title: Two measured TypeScript capture-harness defects that bias one arm
status: done
priority: 2
refs: eval/starters/ts/src/view/harness.ts, eval/starters/ts/src/view/capture.ts, research/10-stack-capability-matrix.md
done_when: either both defects are fixed and a render test proves each (an asset-loaded texture appears in a filmed frame; a skeletal or time-driven animation differs between frame_0000 and frame_0011), or each is recorded as an accepted limitation in the ts starter AGENTS.md with the reason, and eval/FINDINGS.md carries the one-arm-bias entry
---

Found while surveying stack capabilities for task 24 (2026-08-23), both measured live through Playwright 1.62.1 with the harness's exact page setup, not inferred.

DEFECT 1 - the capture page cannot load a file. harness.ts:323 builds the page with
page.setContent(...), so the document origin is null and there is no base URL. Measured in that
page: a relative fetch THROWS (Failed to parse URL from ./model.glb), an http fetch fails, and
only data: and blob: URLs return 200. three's FileLoader, GLTFLoader, TextureLoader and every
other loader route through fetch. So an asset pipeline that works perfectly under just run (real
dev server, real http) renders NOTHING into any of the 12 filmed PNGs the judges see.

DEFECT 2 - frozen clocks silently stop animation. harness.ts:273 sets performance.now = () => 0
in DETERMINISM_SCRIPT, which is correct for page determinism. But three's Clock and Timer both
read performance.now(), so mixer.update(clock.getDelta()) is update(0) forever. Skeletal
animation, tweens and any time-driven view effect appear to work and show the bind pose or the
t=0 state in every captured frame.

WHY IT MATTERS: both are one-arm defects, which is finding #25's shape - a harness defect that
can only fire on one arm is bias, not noise. Neither produces an error. Both make a TS submission
that did the work look identical in the evidence to one that did not, and the frames channel is
what three of the five judged aspects read.

NOT YET ESTABLISHED, and worth checking before fixing: whether any stored TS submission actually
tripped either of these. That is what decides whether this is a latent trap or an explanation for
results already published. Check the stored ts submissions for loader use and for
AnimationMixer/Clock use before deciding the priority.

Both defects have cheap candidate fixes (a data: URL document or a real base URL for the first; a
monotonically advancing stub rather than a frozen constant, or driving the mixer from the sim
tick, for the second) - but do not pick one from this description. Editing starters is a regime
boundary per eval/RUNS.md, so this needs verify_blind, starter_parity and a RUNS.md note.
