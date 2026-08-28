---
id: 192
title: ci_minutes' register checks row is matched anywhere in the document, not in its table
status: todo
priority: 3
refs: eval/tools/ci_minutes.py,.github/workflows/README.md
done_when: 'The checks row is located by its TABLE - found by the opening table''s header cells the way the exclusion table already is, then its checks row read - so a matching row elsewhere in the document cannot answer for it. Pinned in both directions in ci_minutes --selftest: a decoy row carrying the right numbers above a corrupted opening table must go RED, and the live register must stay green. Add the variants that must NOT redden: the row re-spaced, the table moved, and a ''| checks |'' line inside a fenced code block.'
---

CHECKS_ROW_RE in eval/tools/ci_minutes.py is applied with re.search over the whole register, so it reads the FIRST '| checks | N ... | M ... |' row anywhere in the document rather than the row of the opening table it exists to pin. Measured 2026-08-27 on the live register: with a decoy row '| checks | 59 gates | 11 suites |' prepended and the real opening-table row corrupted to 99, the check still reads (59, 11) and stays green. That is the failure this row was added to prevent, one level up - PR #63 added it because the opening table said 56 while the coverage sentence and the pin both said 58, and a matcher that accepts any row can go stale the same way with nothing disagreeing. Found by CodeRabbit on PR #64 (task 184), which only re-pinned the number and did not write this matcher, so it is filed rather than fixed there.

## note 2026-08-28 (orchestrator) — current at dispatch

Filed from PR #64's review; **#64 has since MERGED** (squash `5c3871b`) and the premise is
re-verified on the merged head: `CHECKS_ROW_RE` is defined at `ci_minutes.py:1000` and applied at
`:1882` as a single `CHECKS_ROW_RE.search(read_register())` — one row, anywhere in the document,
answers for the opening table. The live numbers have moved since filing: the register now reads
**60 gates / 11 controls** (`python3 eval/tools/ci_minutes.py --gates`), and the selftest pin at
`ci_minutes.py:1852` asserts 60. Your decoy-row example written with 59 is still a valid decoy —
the defect is the ADDRESS, not the number.

**Baseline, at the merged head:** `ci_minutes --selftest` exit 0 — 101 mutants died, 63 variants
passed. `--controls` exit 0. Nothing holds `eval/tools/ci_minutes.py` or
`.github/workflows/README.md`; branch from `main`, expect no rebase. Task 191 is in flight on
`eval/judge/bot_*` files only — no conflict with yours.

One boundary from the ticket's own done_when, restated because it decides scope: the repair is
where the row is FOUND (table-located, the way the exclusion table is), not what the row must
say. The selftest's existing `gates.yml gate count` pin stays; you are adding pins, not moving
that one's meaning.
