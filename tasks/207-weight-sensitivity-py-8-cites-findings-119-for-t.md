---
id: 207
title: 'weight_sensitivity.py:8 cites FINDINGS #119 for the tier-1-gate story, which is #123'
status: todo
priority: 3
refs: eval/judge/weight_sensitivity.py, eval/findings/certifies-nothing.md, eval/findings/documentation.md, tasks/206
done_when: 'The citation names the finding that holds the story it is cited for, checked by reading each cited finding beside the claim that cites it; every other #119 citation surviving the 2026-08-23 renumbers in live (non-archive) code is read the same way and either confirmed correct or fixed - the spot-check rows are runner.py:20 (''the sole copy, so they stay (#119)''), docstat.py:596, docstat.py:2954, docstat.py:5100.'
---

Found 2026-08-29 while working task 206 (grep for surviving #119 citations in live code, after fixing the two in the judge_ledger/field_sweep pair). eval/judge/weight_sensitivity.py line 8 reads: 'On 2026-08-23 tier 1 became a GATE and overall = tier2 (#119, ...'. The tier-1-gate story ('Tier 1 is now a gate: overall = tier2') is the body of finding 123 (eval/findings/certifies-nothing.md, heading at line 3189, the sentence at line 3233). #119 is the withdrawal-register finding (eval/findings/documentation.md line 955). Same shape as the #119-meant-#121 drift the sixth cleanup pass fixed in judge_ledger.py's docstring - a citation that resolves and means something else. The module was not read whole here, so there may be more where that came from; the fix is citation-only, never renumber the finding.
