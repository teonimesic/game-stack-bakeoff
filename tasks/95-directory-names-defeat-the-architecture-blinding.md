---
id: 95
title: 'Directory names defeat the architecture blinding the way extensions did: 1,561 arm-naming path segments survive in the 8 stored blind packs'
status: open
priority: 2
refs: eval/judge/field.py blind_extensions, eval/judge/anonymise.py _bucket, tasks/87
done_when: a decision is recorded for CHANGED.txt - mapped through the manifest, or dropped for blind aspects, or rewritten - with the measurement that chose it; any rewrite applies only where blind_language is true, pinned by a mutant AND a variant proving a non-blind pack is byte-unchanged; and a re-sweep reports the surviving count per arm-naming segment rather than a single total
---

Task 87 closed the EXTENSION half of the blind_language leak. The same measurement, run over the 8 stored architecture packs after neutralise AND after the new blind_extensions, finds the directory half untouched: in code content, public 1148, Assets 128, src/sim 39, res:// 34, ProjectSettings 16, scripts 13, Library 1; in CHANGED.txt, Assets 138, public 21, scripts 11, src/sim 7, Packages 4, ProjectSettings 1. anonymise relabels a pack file to sim/03.ts precisely because crates/sim vs Assets/Sim vs src/sim is a dead giveaway - and then hands the judge a CHANGED.txt listing the real tree, plus code that names those directories in string constants. res:// is one engine's resource scheme and identifies an arm on sight. This is the SAME defect as 87 through the sibling property, and 87 deliberately did not widen its scope into it: an extension vocabulary can be audited against the starters mechanically, a directory vocabulary probably cannot, and the honest repair for CHANGED.txt may be to map each row through the pack's own origin-to-label manifest rather than to rewrite text at all.
