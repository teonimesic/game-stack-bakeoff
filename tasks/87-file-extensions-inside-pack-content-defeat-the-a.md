---
id: 87
title: 'File extensions inside pack CONTENT defeat the architecture aspect''s blinding: 1,876 occurrences of .ts/.gd/.rs/.cs across 78 of 84 stored packs'
status: done
priority: 2
refs: 'eval/judge/field.py build_pack blind_language, eval/judge/anonymise.py CODE_EXT, eval/FINDINGS #131'
done_when: a rewrite of extension references applies only where blind_language is true, pinned by a selftest that fails before the change and passes after, and by a variant proving a non-blind aspect's pack is byte-unchanged; a re-sweep of stored packs reports the count under the blind path; and the decision about what an extension inside a string literal or a data file should become is stated rather than left to the regex
established_by: 'field.build_pack now rewrites language-naming file extensions inside pack CONTENT to NEUTRAL_EXT, only where blind_language is true. RED BEFORE: judge/blind_ext_selftest.py against the unrepaired field.py reports 16 of 24 files in a blind field leaking, 28 extension tokens, all 8 CHANGED.txt among them. GREEN AFTER: 0 unmet expectations. Mutant: blind_extensions neutered in-process reproduces the 16 files and 28 tokens, so check 1 can fail. Variant, rule 15: the same field built with blind_language=False is byte-identical to neutralise alone and keeps all 16 files naming their extensions - and on REAL data, diff -r of the idiomatic pack for wg-g4c g4_platformer built before and after the change exits 0, 207 files byte-identical. Re-sweep of all 84 stored judge_pack/code dirs: 2083 arm-naming extension tokens after neutralise, 0 after blind_extensions, with 81 import.meta occurrences DECLINED and reported on their own line as a language construct that names no file. Ticket figure reproduced exactly on the count, 1876 = ts 973 + gd 583 + rs 258 + cs 62, and corrected on the pack union, 76 of 84 not 78. THE DECISION THE TICKET ASKED FOR IS STATED IN THE FUNCTION DOCSTRING: the rewrite is uniform across comment, string literal, import specifier and data file, because telling them apart requires lexing the language that blind_language exists not to know, and because a leak in a string literal is a leak; the resulting pack contains code that could not run, which was already true of every file in it since the .src rename. Vocabulary decided by two questions with evidence behind each: arm-exclusivity audited mechanically against the four starters by the selftest, and member-name collision measured against the corpus - .lock is 108 Mutex::lock calls and 0 filenames, .anim is 128 player.anim accesses and 0 filenames, both excluded by name in field._NOT_AN_EXTENSION with the count. CHANGED.txt goes through the same path: it is a git diff --stat the HARNESS writes, and it carried 80 .cs, 78 .gd, 60 .meta, 43 .ts, 43 .rs in the 8 stored architecture packs. TWO DEFECTS FOUND BY AIMING THE FINISHED REPAIR AT A REAL RUN, neither reachable from the fixture: field.py pack read the aspect sees and not its blind_language, so the entry point the module docstring names produced an entirely unblinded architecture pack, 199 of 207 files keeping a language-naming filename and 663 content tokens, now 0 and 11 with the 11 all import.meta - field_sweep.py passes both at all three call sites so no stored round is affected; and the method-call guard (?!\s*\() read a filename followed by whitespace and a parenthesis as a call, one occurrence in 84 packs, now (?!\(). Gates unpiped: tasks.py check 0, docstat.py --sweep 0 with the same 13 pre-existing stale citations before and after, blind_ext_selftest 0, pack_selftest 0, anonymise_selftest 0, aspects_selftest 0, gate_selftest 0, capture_selftest 0, field.py packcheck 0. Docs: eval/judge/AGENTS.md replaced, eval/judge/JUDGING.md repair-2 paragraph and table row, eval/RUNS.md second caveat stating every stored architecture round read a field carrying its arms extensions, eval/IMPROVEMENTS.md iteration 14. NOT repaired and filed: directory names, 1561 arm-naming segments in the stored blind packs, task 95. Finding number deliberately NOT allocated - peer worktrees hold findings-heavy tasks and eleven collisions happened on 2026-08-23 - filed as task 96. Branch task-87-blind-extensions commit 26c835b.'
---

The architecture aspect is the one judged with blind_language=True, and its whole blinding is renaming every source file to .src. That hides the extension of the file the judge is READING and nothing hides the extensions the file MENTIONS. Measured 2026-08-23 while closing task 73, by searching every stored judge_pack/code file after neutralise: 1,876 hits across 78 of 84 packs - .ts 973, .gd 583, .rs 258, .cs 62. They are cross-file references in comments and import specifiers - import { f32 } from ./vec2.ts, tests/render_test.gd builds and positions this entire scene. A judge that opens one file and sees a sibling named sim/tuning.gd is not blind. This is NOT a stack name and must not be fixed in neutralise: neutralise runs for every aspect, and idiomatic legitimately keeps its extensions. The repair belongs in field.build_pack, in the branch that already knows blind_language is set and already rewrites the target suffix to NEUTRAL_EXT.

## What was measured while closing this, so the next agent does not re-derive it

**The ticket's figure reproduces on the count and not on the pack union.** 1,876 = .ts 973 +
.gd 583 + .rs 258 + .cs 62, exactly. The union of packs carrying at least one is **76 of 84**,
not 78. Widening the pattern to every arm-naming suffix gives **2,083** across all 84.

**Two extraction traps, both of which returned a confident wrong answer first (rule 12):**

1. A `(?<![A-Za-z0-9_])` lookbehind in front of the dot excludes exactly the character a
   filename stem ends with. `vec2.ts` and `bot_arena.gd` are invisible to it: it reported
   **10** hits where the truth is 1,876.
2. `runs/*/artifacts/*/eval/judge_pack/code` finds **68** of the 84 packs. `wg-g4c-capgate`
   nests its two arms one level deeper. Use `**/judge_pack/code`.

**The vocabulary needs two questions and a starter census answers only one.** Which suffixes are
arm-exclusive comes from `eval/starters/` and is audited mechanically. Which suffixes can *also
be a member name* comes only from the corpus, and it is what stops the obvious repair being
worse than the leak: `.lock` is **108 `Mutex::lock()` calls and 0 filenames**, `.anim` is **128
`player.anim` accesses and 0 filenames**. A starter census lists both as Rust- and
Unity-exclusive.

**The densest leak was written by the harness, not by an agent.** `CHANGED.txt` is a whole
`git diff --stat`; the 8 stored `architecture` packs carry 80 `.cs`, 78 `.gd`, 60 `.meta`, 43
`.ts` and 43 `.rs` in that file alone.

**`field.py pack` was passing `sees` and not `blind_language`.** A pack built the documented way
was not blinded at all. Found by aiming the finished repair at a real run; the fixture could not
produce it, and neither could `field_sweep.py`, which passes both.

**Still open:** the directory half of the same leak — `public` 1,148, `Assets` 128, `res://` 34,
1,561 segments in the stored blind packs — is **task 95**. The finding number was deliberately
not allocated (peer worktrees hold findings-heavy tasks); it is **task 96**.
