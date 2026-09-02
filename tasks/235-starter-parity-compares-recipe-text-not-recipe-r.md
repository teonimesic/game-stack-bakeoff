---
id: 235
title: starter_parity compares recipe text, not recipe reproducibility
status: todo
priority: 3
refs: 'IMPROVEMENTS.md (root, the #66 iteration''s Scope section), eval/judge/starter_parity.py, #66'
done_when: 'EITHER starter_parity (or a sibling) measures at least one recipe''s reproducibility per stack - cold versus warm agreement on the pristine tree, the same check #66''s fix now performs for Unity - with a mutant or variant proving the new check can fail, OR DECISIONS.md records why text comparison is sufficient and the archive''s Scope note is closed by reference to it. A real toolchain cost is the likeliest objection: measure it before arguing it (the #66 iteration''s own cost objection did not survive measurement).'
---

#66's defect - a warm-cache lint answering from the build cache rather than the code - was invisible to recipe-TEXT comparison, which is why starter_parity never fired. The fix is Unity-only, and nothing re-checks that the other three stacks' gates answer from code rather than cache; 'stack X passed its gate' still has never been compared against a cold run on 3 of 4 arms. The gap was named in the archive's Scope section and never filed.
