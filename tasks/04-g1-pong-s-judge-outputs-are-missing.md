---
established_by: 'Re-ran idiomatic on the stored g1_pong field (wg-matrix-2026-08-13; packs complete and original - 0 dropped, never rebuilt, so no truncation and no starter drift). ALL 4 ordered rounds stored under runs/wg-funframes-crossgame/pong/, $17.66; the #53 pong row is now backed by files. RESULT at n=4: ordering reproduces exactly (rust 3.38 > ts 3.00 > unity 2.75 = godot 2.75) INCLUDING the godot/unity tie, but every value is ~0.6 lower than #53''s (3.0/4.0/3.5/3.0) - the row is sound as a RANKING and not reproducible as SCORES; #53 annotated in place. For task 02, pong resolves rust>godot and rust>unity with zero contradictions, so rust>unity now resolves in ALL FOUR games across 32 submissions. CORRECTION: an interim report at n=3 also listed ts>godot as resolved on pong; the 4th round removed it (godot 2.50->2.75, gap fell inside the combined SE). Adding evidence WEAKENED that pair - corrected in FINDINGS #79, and a live instance of separation()''s low-n warning.'
id: 04
status: done
priority: 3
title: Recover or retract the missing g1_pong judge outputs
refs: 'eval/FINDINGS.md #53, eval/judge/JUDGING.md:213'
done_when: 'the pong row in #53 is backed by a file on disk, or annotated in eval/FINDINGS.md as unreproducible'
---

This project measures how well coding agents build whole games in four stacks
(Rust/Bevy, TypeScript/three.js, Unity, Godot). Submissions are graded in three tiers:
tier 1 programmatic checks, tier 2 a scripted play-bot, tier 3 six LLM-judged 'aspects'
(architecture, idiomatic, fun, fun_frames, ux, audio) that score eight anonymised
submissions side by side as a 'field'. Tier 3 currently has weight 0.00.

THE PROBLEM: finding #53 contains a table quoting `idiomatic` scores for `g1_pong` (godot 3.0,
rust 4.0, ts 3.5, unity 3.0). `eval/judge/JUDGING.md:213` records that the round happened and
what it cost. But no `g1_pong__idiomatic__seed*.json` exists anywhere on disk.

WHY IT MATTERS: this project's standing rule is never to quote a value you did not just read from
its source. A published number whose artifact is gone cannot be checked, and #53 is one of the
findings currently shaping decisions about the whole subjective layer.

TWO ACCEPTABLE OUTCOMES:
  (a) re-run architecture and idiomatic on the stored g1_pong field, restoring the artifact; or
  (b) mark that row in #53 as unreproducible, so nobody builds on it.

Either is fine. Leaving it as an unsourced number is not.
