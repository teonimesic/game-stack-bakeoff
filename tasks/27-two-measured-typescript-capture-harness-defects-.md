---
id: 27
title: Two measured TypeScript capture-harness defects that bias one arm
status: open
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
