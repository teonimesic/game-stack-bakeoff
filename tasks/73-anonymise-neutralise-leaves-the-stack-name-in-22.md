---
id: 73
title: anonymise.neutralise leaves the stack name in 22 of 68 stored code packs, and the architecture aspect is language-blind
status: done
priority: 1
refs: 'eval/judge/anonymise.py _STACK_TOKENS, eval/judge/aspects.py ARCHITECTURE blind_language, eval/FINDINGS #83, tasks/66'
done_when: neutralise rewrites the uppercase env-var and build-tool forms as well, pinned by a selftest that fails before the fix and passes after; a re-sweep of every stored judge_pack/code under eval/runs reports 0 packs carrying a surviving stack token, or the residue is enumerated with the reason each one is judged harmless; and whether any stored architecture round read a leaking pack is answered from the judge file-open log where it exists and stated as unassessable where it does not
established_by: 'neutralise now matches a stack NAME as a whole identifier segment in any case and any position, not a list of spellings: 38 names, 4 residual literal patterns. Pinned by judge/anonymise_selftest.py which was red before the change (the ticket probe CARGO_MANIFEST_DIR=/x/crates/game BEVY_ASSET_ROOT=/y came out unchanged) and is green after, with 38 mutants all live, 128 real leaking lines harvested from the stored packs all closed, 400 real innocent lines byte-identical, and idempotence. Re-sweep of all 84 stored judge_pack/code dirs, 1324 files: 22 leaking packs before, 0 after, by the module detector and by an independent stem list fixed before the repair; 139 distinct lines change and all 139 replace a genuine stack name. Residue enumerated: immunity 50 and Vec3.UnitY 4 are not the name, and file extensions inside content, 1876 hits over 78 of 84 packs, are a separate unrepaired leak now filed as task 87. Architecture rounds answered from the file-open log: 13 stored, 9 have a log, 9 of 9 opened a leaking file always including the Rust submissions, 4 have no log and are unassessable. verify_blind switched from _STACK_RE to find_stack_names, control: the pre-fix vocabulary returned zero hits on a CARGO_MANIFEST_DIR line. FINDINGS #131 (allocated as #130), eval/RUNS.md caveat on the wg-g4c architecture ordering.'
---

field.build_pack writes neutralise(text), so neutralise is the only blinding an architecture round has - ARCHITECTURE is the one aspect with blind_language=True and its .src rewrite hides the extension but not the contents. _STACK_TOKENS is case-sensitive and has no rule for the bare words cargo or rust, so the uppercase env-var forms survive intact. Measured 2026-08-23 by applying neutralise to every file of all 68 stored code packs under eval/runs and grepping the OUTPUT: 22 packs across 6 runs carry a surviving token - wg-matrix 7, wg-audio48 5, wg-audio 4, wg-g4c 3, wg-arena3d 2, wg-calib 1. Counts by token: CARGO_MANIFEST_DIR 51, crates/sim 38, crates/game 34, cargo 20, CARGO_TARGET_TMPDIR 18, CARGO_TARGET_DIR 14, CARGO_BIN_EXE_probe 4, pnpm 3, BEVY_ASSET_ROOT 2, tsc 2. wg-g4c is the run whose fresh architecture ordering RUNS.md reports as available, and 3 of its 8 packs leak. This is the UnityCsReference failure class anonymise.py already documents in a comment, recurring in the case that comment did not cover: a token nobody thought to enumerate. Do not fix by adding the two words - the trigger is the property, an identifier that contains an engine or toolchain name in any case, not the list of instances seen so far.

## Raised to priority 1 by the orchestrator, 2026-08-23, after reproducing it

`neutralise` was run directly on a one-line probe:

    in : CARGO_MANIFEST_DIR=/x/crates/game BEVY_ASSET_ROOT=/y
    out: CARGO_MANIFEST_DIR=/x/crates/game BEVY_ASSET_ROOT=/y

`CARGO`, `BEVY` and `crates` all survive. **This is the live anonymiser, not a stored artefact** —
every pack built from now on carries the same leak.

It is priority 1 rather than 2 because it does not merely sit in stored evidence: `architecture`
is the one aspect with `blind_language=True`, and **3 of the 8 packs behind the `wg-g4c`
architecture ordering that `eval/RUNS.md` reports as available were language-identifiable.** A
reported ordering rests on it.

**Do not repair the stored packs.** `wg-g4c` was re-packed under task 42 with a computed
exclusion set; the other runs cannot be re-packed at all (task 66 established their work trees
lost every git object to the `$TMPDIR` reaper). The repair here is to the anonymiser, plus a
decision about what the affected orderings may still be used for.

**The trigger must not be another token list.** `_STACK_TOKENS` is an enumeration and this is the
second time it has missed one — `anonymise.py`'s own comment records the `UnityCsReference` case.
State the property, and pin it with a variant that feeds real stored pack content rather than the
tokens you thought of.

## Done 2026-08-23. What the next agent must not re-derive

**Where the repair is.** `eval/judge/anonymise.py`: `_STACK_NAMES` (38 lowercase names),
`_segments`, `_match_window`, `_shape`, `_scrub_names`, `find_stack_names`,
`_rebuild_matcher`. `_STACK_TOKENS` is gone; `_STACK_RE` survives holding only four literal
patterns and is still what `verify_blind` imported — that import was changed to
`find_stack_names()`, because a checker with a narrower vocabulary than the rewriter reports
clean on exactly the leaks that motivated the repair.

**The corpus count is 84 packs, not 68.** The ticket's 68 excluded `wg-g4c-capgate` (16
packs), which is a separate directory and not a symlink. Runs holding packs:
`wg-matrix` 24, `wg-audio48` 16, `wg-g4c-capgate` 16, `wg-audio` 11, `wg-arena3d` 8,
`wg-g4c` 8, `wg-calib` 1. 1,324 files.

**Do not implement this as a case-insensitive substring match.** Measured on the same
corpus, that would rewrite `immunity` (54, all four arms — "unity" is inside it),
`Vec3.UnitY` (4, a math constant in the Unity arm's own vector type), `main.tscn` /
`bestScore` / `addInitScript` (146, all contain `tsc`) and `is_three_dimensional` /
`Three tests enforce` / `you trust this macro` (297). Segment matching rejects all of them;
a one-letter segment is refused inside a multi-segment window, which is exactly what
separates `Unit|Y` from `Type|Script`. `three` and `node` are excluded from the vocabulary
outright and kept as literal patterns.

**Three tokens in the ticket's list needed no rule.** `crates/sim` and `crates/game` are
both the `crates` name; `CARGO_BIN_EXE_probe`, `CARGO_TARGET_DIR` and `CARGO_TARGET_TMPDIR`
are all `cargo`. The ticket's per-token counts undercounted the true residue: the sweep also
found `clippy` (76), `Winit` (60), `Rust` in prose (179) and `TypeScript` in prose (30),
none of which were listed.

**The architecture question, answered.** 13 stored `architecture` rounds; 9 have a
file-open log; **9 of 9 opened at least one leaking file**, always including the Rust
submissions (3-9 leaking files opened per round). 4 rounds
(`wg-tetris-judge-2026-08-17`, pre and post) have no log and are permanently unassessable.
Caveat established by mtime rather than assumed: the current `wg-g4c` pack bytes were
written 2026-08-23T07:18Z and the five `wg-aspect-reliability` rounds ran 05:23-05:57Z, so
the intersection uses the label -> origin mapping the re-pack preserved, not the exact bytes.

**What is NOT fixed, and is now task 87.** File extensions inside pack CONTENT —
1,876 occurrences of `.ts`/`.gd`/`.rs`/`.cs` in comments and import specifiers across 78 of
84 packs. That defeats `blind_language` just as thoroughly and belongs in
`field.build_pack`, not in `neutralise`, which runs for every aspect.

**One behaviour deliberately changed.** `\bUnity\w+\b -> EngineThing` collapsed every
`Unity`-prefixed identifier to one token, so `UnityCG.cginc` and `UnityObjectToClipPos` both
became `EngineThing`. They are now `EngineCG.cginc` and `EngineObjectToClipPos`: the name is
gone either way, and the old form destroyed the distinction between two identifiers while
advertising that a substitution had happened.
