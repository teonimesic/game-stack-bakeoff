---
established_by: Applied. starters/unity/tools/unity-compile.sh now deletes Library/ from its scratch copy when STRICT=warnings, so 'just lint' and 'just verify' answer from the code while 'just check' keeps its warm cache (4.9s). Root cause was the copy inheriting Library/; deleting only ScriptAssemblies is NOT enough (measured: still exit 0) because Unity caches the analysis elsewhere - that obvious surgical fix would have shipped as a no-op repair. PINNED THREE WAYS: a warm tree with 5 real CA1861 flips exit 0 -> exit 1 reporting all five; the clean starter stays exit 0 (no false failure); 'just check' stays warm and green. Cost 10.9s cold vs 8.9s warm. verify_blind exit 0 (BLIND, 74 ids, 9 trees) and starter_parity exit 0 ('No drift detected on any measured axis') re-run after the edit. eval/RUNS.md records the EIGHTH comparability break with what it does and does not invalidate. g4_platformer__unity__t1 reclassified as the project's THIRD genuine submission defect; README.md, RUNS.md and FINDINGS #66 updated, #66 marked superseded-in-part and dated rather than rewritten.
id: 07
status: done
priority: 2
title: Fix Unity's `just verify` answering from its build cache
refs: eval/FINDINGS.md #66, starters/unity/justfile
done_when: just lint gives the same answer on a warm tree and a cold extract, pinned both ways, and the starter edit is recorded in eval/RUNS.md as a regime boundary
---

This project measures how well coding agents build whole games in four stacks
(Rust/Bevy, TypeScript/three.js, Unity, Godot). Submissions are graded in three tiers:
tier 1 programmatic checks, tier 2 a scripted play-bot, tier 3 six LLM-judged 'aspects'
(architecture, idiomatic, fun, fun_frames, ux, audio) that score eight anonymised
submissions side by side as a 'field'. Tier 3 currently has weight 0.00.

WHAT `just verify` IS: the single command each starter gives a building agent to know whether its
work is done — format, lint, tests, render tests. Its own justfile calls it "ONE command to know
whether the work is done".

THE DEFECT (#66): on Unity it can pass on code that does not compile clean. A submission's own
final `just verify` printed "lint: all assemblies compile clean" and "verify passed". The same
submission, extracted from its tarball into an empty directory, fails with five CA1861 analyzer
errors — with `cmp` confirming the file is byte-identical. The Editor assembly was not re-analysed
after the agent's edit, so violations it had already been shown never reappeared.

THE SCOPE: this gate has been green on the Unity arm across FOUR matrices, and nothing has ever
checked its answer against a cold build. So "Unity passed lint" has never been the claim it
appeared to be. `judge/starter_parity.py` did not catch it because it compares recipe TEXT, not
recipe REPRODUCIBILITY.

DO NOT COUNT IT AS A SUBMISSION DEFECT. An agent that runs the gate it is told to run, and is told
it passed, has done the task as specified. The genuine-defect count stays at two.

WHAT TO DO: make `lint` force a non-incremental analyze so the answer cannot depend on what was
compiled before it. Pin both ways: a tree with a real violation must fail warm AND cold.

CAREFUL: `starters/` is the product being measured. Editing it is a regime boundary — re-run
`judge/verify_blind.py` and `judge/starter_parity.py`, and record in `eval/RUNS.md` that runs
before and after are not comparable.
