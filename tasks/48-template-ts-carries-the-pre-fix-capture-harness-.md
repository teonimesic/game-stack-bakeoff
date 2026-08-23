---
id: 48
title: template-ts carries the pre-fix capture harness, a second live copy of a repaired defect
status: open
priority: 3
refs: template-ts/src/view/harness.ts, eval/starters/ts/src/view/harness.ts, eval/findings/one-arm-bias.md
done_when: either template-ts/src/view/harness.ts serves a real origin with addInitScript before goto and a virtual rather than frozen clock, with that tree's own just verify green and the capture-environment tests ported and passing; or template-ts is recorded as retired for the spec-change suite and no longer accepting trials, stated in eval/RUNS.md
---

Task 31 repaired three capture-page defects in eval/starters/ts: a null document origin that made every three loader fail, a DETERMINISM_SCRIPT that never ran because addInitScript was registered before a setContent that does not navigate, and a frozen clock that the origin fix would have activated. template-ts/src/view/harness.ts still has lines 273/322/323 in the pre-fix form and is a LIVE tree: runner.py takes --template, and eval/runs/bakeoff-ts-2026-08-11 was built from it. It is not what wholegame.py copies (that reads eval/starters/ only), so no whole-game number is affected. The two trees have already diverged in every src file, so this is a port plus a full re-verify of that tree, not a cherry-pick. This is finding #99's shape: a second copy that is never in sync and that no gate compares.
