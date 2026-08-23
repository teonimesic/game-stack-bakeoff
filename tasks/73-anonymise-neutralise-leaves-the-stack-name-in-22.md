---
id: 73
title: anonymise.neutralise leaves the stack name in 22 of 68 stored code packs, and the architecture aspect is language-blind
status: in_flight
priority: 1
refs: 'eval/judge/anonymise.py _STACK_TOKENS, eval/judge/aspects.py ARCHITECTURE blind_language, eval/FINDINGS #83, tasks/66'
done_when: neutralise rewrites the uppercase env-var and build-tool forms as well, pinned by a selftest that fails before the fix and passes after; a re-sweep of every stored judge_pack/code under eval/runs reports 0 packs carrying a surviving stack token, or the residue is enumerated with the reason each one is judged harmless; and whether any stored architecture round read a leaking pack is answered from the judge file-open log where it exists and stated as unassessable where it does not
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
