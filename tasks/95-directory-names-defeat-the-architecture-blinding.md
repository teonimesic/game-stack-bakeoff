---
id: 95
title: 'Directory names defeat the architecture blinding the way extensions did: 1,561 arm-naming path segments survive in the 8 stored blind packs'
status: open
priority: 2
refs: eval/judge/field.py blind_extensions, eval/judge/anonymise.py _bucket, tasks/87
done_when: a decision is recorded for CHANGED.txt - mapped through the manifest, or dropped for blind aspects, or rewritten - with the measurement that chose it; any rewrite applies only where blind_language is true, pinned by a mutant AND a variant proving a non-blind pack is byte-unchanged; and a re-sweep reports the surviving count per arm-naming segment rather than a single total
---

Task 87 closed the EXTENSION half of the blind_language leak. The same measurement, run over the 8 stored architecture packs after neutralise AND after the new blind_extensions, finds the directory half untouched: in code content, public 1148, Assets 128, src/sim 39, res:// 34, ProjectSettings 16, scripts 13, Library 1; in CHANGED.txt, Assets 138, public 21, scripts 11, src/sim 7, Packages 4, ProjectSettings 1. anonymise relabels a pack file to sim/03.ts precisely because crates/sim vs Assets/Sim vs src/sim is a dead giveaway - and then hands the judge a CHANGED.txt listing the real tree, plus code that names those directories in string constants. res:// is one engine's resource scheme and identifies an arm on sight. This is the SAME defect as 87 through the sibling property, and 87 deliberately did not widen its scope into it: an extension vocabulary can be audited against the starters mechanically, a directory vocabulary probably cannot, and the honest repair for CHANGED.txt may be to map each row through the pack's own origin-to-label manifest rather than to rewrite text at all.

## What was measured while closing this, so the next agent does not re-derive it

**The ticket's 1,561 reproduces to the digit** — `sweep`ing the 8 packs under
`runs/wg-aspect-reliability/packcheck/architecture` after `neutralise` + `blind_extensions`
with the ticket's own token list gives code 1,379 + `CHANGED.txt` 182 = 1,561 exactly.

**And it is the wrong shape, which is the whole result.** The total pools two channels with
opposite properties — rule 4, one level below where it usually fires (not over submissions,
over *who wrote the text*):

| channel | a real path segment | the same word doing something else |
|---|---|---|
| `CHANGED.txt` | **182** | **0** |
| code content | 149 | **1,230** |

1,129 of the 1,148 `public` are the C# access modifier or `'public'.length`; 16 of the 17
`ProjectSettings` are `ProjectSettings.globalize_path()`; 81 of the 266 `Assets` are
`GameAssets.HERO_SHEET` in *Godot* and `ResMut<Assets<Image>>` in *Rust*. **The number that
was handed on would have chosen a vocabulary rewrite aimed mostly at words that are not paths.**

**The ticket's guess about the starters is wrong, and it still does not change the answer.**
A directory vocabulary *can* be audited mechanically: read from `git ls-files` over the four
starters (19 arm-exclusive segments), matched whole-segment and path-adjacent, it finds **536**
hits across all 84 stored packs with exactly **1** in an arm the segment does not name. Two
extraction traps on the way, both of which returned a confident wrong answer first:

1. **`/`-adjacency is not segmenthood.** `tests/render_test.gd` is not the `render/` directory
   and `audio/game_over.wav` is not the `game/` directory. A bare adjacency test reported 116
   wrong-arm hits where the truth is 1 — the `.ts`-inside-`.tsx` shape one level up.
2. **The detector must read `git ls-files`, not the disk.** An `rglob` over `eval/starters`
   returns **21** segments in a working checkout and **19** in a fresh worktree, because the
   checkout has run Unity and carries untracked `Logs/`, `Generated/`, `Analyzers/`.

**What disqualified the code half was not feasibility but the SHAPE of its output.** Only some
starters have arm-exclusive directories, so the redaction density is stack-correlated by
construction: **godot 0, rust 43, unity 228, ts 265.** Filed as `tasks/103` with the table.

**Two alternatives measured and also not clean.** Mapping code content through the manifest the
way `CHANGED.txt` now is covers 166 occurrences over 77 of 199 origins and is stack-correlated
too — Rust is **0**, because it names modules `crate::sim::world` and never as a path. Rewriting
*every* path segment would destroy the `sim/`, `view/`, `tests/` bucket labels the judge's own
brief instructs it to cite.

**`CHANGED.txt` mapping coverage, the number that chose "map" over "drop":** 196 of 424 rows
across the 8 `wg-g4c` submissions map to a pack label, and the mapped set is essentially the
whole pack (26 of 26, 31 of 31, 27 of 30). The 228 unmapped rows are `AGENTS.md`, `Cargo.lock`,
`.wav`, `.meta` — files the judge cannot open under any name. **Their count is stack-correlated
53/43 (unity) against 15/15 (ts), which is why neither it nor the `--stat` summary tail is
shown to the judge.**

**A trap for whoever tests this next.** `Path(__file__).resolve()` follows symlinks, so a
"pre-change tree" assembled by symlinking `judge/*.py` into a temp directory imports the
**new** module and reports a confident green. Copy the files, or swap `field.py` in place.

**Left alone deliberately, and worth a task:** `field.EVIDENCE_BLURB["code"]` still tells every
judge *"the pack is filled until a size budget runs out, so it may not contain every file the
author wrote"*. The budget was removed on 2026-08-22 (#69) and `files_dropped_for_length` is 0
by construction. That is judge-facing text stating something false; it is not this ticket's
scope and changing it moves what the judge reads.
