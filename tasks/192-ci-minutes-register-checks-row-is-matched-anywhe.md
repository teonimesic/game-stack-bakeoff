---
id: 192
title: ci_minutes' register checks row is matched anywhere in the document, not in its table
status: todo
priority: 3
refs: eval/tools/ci_minutes.py,.github/workflows/README.md
done_when: 'The checks row is located by its TABLE - found by the opening table''s header cells the way the exclusion table already is, then its checks row read - so a matching row elsewhere in the document cannot answer for it. Pinned in both directions in ci_minutes --selftest: a decoy row carrying the right numbers above a corrupted opening table must go RED, and the live register must stay green. Add the variants that must NOT redden: the row re-spaced, the table moved, and a ''| checks |'' line inside a fenced code block.'
---

CHECKS_ROW_RE in eval/tools/ci_minutes.py is applied with re.search over the whole register, so it reads the FIRST '| checks | N ... | M ... |' row anywhere in the document rather than the row of the opening table it exists to pin. Measured 2026-08-27 on the live register: with a decoy row '| checks | 59 gates | 11 suites |' prepended and the real opening-table row corrupted to 99, the check still reads (59, 11) and stays green. That is the failure this row was added to prevent, one level up - PR #63 added it because the opening table said 56 while the coverage sentence and the pin both said 58, and a matcher that accepts any row can go stale the same way with nothing disagreeing. Found by CodeRabbit on PR #64 (task 184), which only re-pinned the number and did not write this matcher, so it is filed rather than fixed there.
