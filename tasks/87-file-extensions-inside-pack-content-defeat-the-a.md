---
id: 87
title: 'File extensions inside pack CONTENT defeat the architecture aspect''s blinding: 1,876 occurrences of .ts/.gd/.rs/.cs across 78 of 84 stored packs'
status: open
priority: 2
refs: 'eval/judge/field.py build_pack blind_language, eval/judge/anonymise.py CODE_EXT, eval/FINDINGS #130'
done_when: a rewrite of extension references applies only where blind_language is true, pinned by a selftest that fails before the change and passes after, and by a variant proving a non-blind aspect's pack is byte-unchanged; a re-sweep of stored packs reports the count under the blind path; and the decision about what an extension inside a string literal or a data file should become is stated rather than left to the regex
---

The architecture aspect is the one judged with blind_language=True, and its whole blinding is renaming every source file to .src. That hides the extension of the file the judge is READING and nothing hides the extensions the file MENTIONS. Measured 2026-08-23 while closing task 73, by searching every stored judge_pack/code file after neutralise: 1,876 hits across 78 of 84 packs - .ts 973, .gd 583, .rs 258, .cs 62. They are cross-file references in comments and import specifiers - import { f32 } from ./vec2.ts, tests/render_test.gd builds and positions this entire scene. A judge that opens one file and sees a sibling named sim/tuning.gd is not blind. This is NOT a stack name and must not be fixed in neutralise: neutralise runs for every aspect, and idiomatic legitimately keeps its extensions. The repair belongs in field.build_pack, in the branch that already knows blind_language is set and already rewrites the target suffix to NEUTRAL_EXT.
