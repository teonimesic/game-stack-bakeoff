---
id: 192
title: ci_minutes' register checks row is matched anywhere in the document, not in its table
status: done
priority: 3
refs: eval/tools/ci_minutes.py,.github/workflows/README.md
done_when: 'The checks row is located by its TABLE - found by the opening table''s header cells the way the exclusion table already is, then its checks row read - so a matching row elsewhere in the document cannot answer for it. Pinned in both directions in ci_minutes --selftest: a decoy row carrying the right numbers above a corrupted opening table must go RED, and the live register must stay green. Add the variants that must NOT redden: the row re-spaced, the table moved, and a ''| checks |'' line inside a fenced code block.'
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/68
established_by: 'Verified against artifacts, not the handback: selftest in the worktree at b23c286 exit 0 with 115 mutants died / 66 variants passed, byte-identical to the quoted line; the defect-direction control reproduced myself - decoy row prepended plus table row 60->99 on the live register exited 1 with got (99, 11), want (60, 11), the exact input that read exit 0 before the repair; live register on main carries one clean checks row, no decoy; mergeable exit 0 at the head, review NOTICE Reviews-paused reported and not gated; diff scoped to ci_minutes.py +321/-8; PR body round-count corrected and is the squash message'
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

## note 2026-08-28

## note 2026-08-28 (agent) — repaired on task-192-register-checks-row-in-its-table, PR #68

`CHECKS_ROW_RE` is gone. `register_checks_row(text)` in `eval/tools/ci_minutes.py` finds the
opening table by its own header cells `["", "`gates.yml`", "`controls.yml`"]` — the same
header-cells discipline as `register_exclusions` and `register_hook_table` — and reads the
`checks` row inside it. A matching `| checks |` line anywhere else answers for nothing. The
scope boundary from the dispatch note is held: the repair is where the row is FOUND; the
numbers are read exactly as the old regex read them (leading digits of each cell) and are
returned as the row states them, corrupt and all — the comparison against the measured census
stays the caller's, because a reader that refused a disagreeing number would be grading its
own answer sheet (the PR #63 drift this row exists to catch IS the caller's comparison going
red).

Fail-closed refusals, each with a message naming what it found: no opening table; two opening
tables; header with no `|---|---|---|` row; table with no checks row; a row with the wrong
cell count; a cell that does not open with a count; two checks rows in one table (refused even
when the two agree — one fact, two answers).

Verified against the LIVE register of the branch, end to end, in both directions:

- Red: the ticket's exact scenario — decoy with the right numbers inserted above, the table's
  row corrupted to 99 — went from **exit 0 (defect, measured before the repair)** to **exit 1
  `got (99, 11), want (60, 11)`** after it.
- Green: the three ticket variants, each run alone against the live register at exit 0 — the
  row re-spaced inside its pipes; the opening table moved from line 8 to line 200 under added
  prose; a `| checks | 999 gates | 999 suites |` line inside a fenced code block above the
  table (wrong numbers, so green proves non-reading).

All of it is pinned in `ci_minutes --selftest`: the decoy mutant asserts the table's corrupted
row is what was read (`((99, 11), [])`), plus 7 further mutants and the 3 variants. Closing
line: **109 mutants died, 66 variants passed** (baseline on this head: 101/63). All six
pre-commit and pre-push gates green against the staged tree.

One trap worth keeping: my first reproduction replaced the FIRST occurrence of the row text —
which was the decoy I had just inserted — and went red "correctly" for the wrong reason. The
decoy must carry the RIGHT numbers and the TABLE be corrupted (find the table's row from the
end), or the demonstration proves nothing. The selftest fixture encodes the right shapes.

## note 2026-08-28

## note 2026-08-28 (agent) — review round 2 pushed (ebb21dc), both Majors accepted and fixed

CodeRabbit's first round found 2 real fail-open holes in the round-1 reader; both were
verified against the code before the repair, and both reproduced:

1. **A fenced example table was selectable as the register's.** A complete table inside a
   ``` fence — header, delimiter, checks row carrying numbers that AGREE with the pin — with
   no real table returned `((60, 11), [])` from round 1: selftest would stay green on an
   example's values. Fixed with `_unfenced(lines)`: fenced lines are excluded before the
   header search and the row scan. Opening fence: 3+ backticks or tildes, optional info
   string. Closing: SAME character, at least as long, nothing else on the line — strict on
   purpose, because the dangerous direction is the one that unfences early. A fence that
   never closes hides the rest of the document, which reads as "no opening table" — refused,
   never misread. A fence inside the table region ends the table.

2. **`(\d+)\b` read `60.5` and `60-11` as 60** (a word boundary falls before `.` and `-`):
   a malformed count cell truncated to a plausible integer and stayed green. `_COUNT_LEAD`
   is now `(\d+)(?=\s|$)` — the digits must be the whole leading token; the refusal names
   the cell and the required form.

Pinned as 3 new selftest mutants: fenced full table with agreeing numbers and no real table
(must go red), decimal cell, range-like cell. Closing line: **112 mutants died, 66 variants
passed** (round 1: 109/63→66; the branch baseline was 101/63). Live register end to end,
all five shapes in the wanted direction: decoy + corrupted table RED; fenced full table,
no real table RED; re-spaced row, moved table, fenced decoy line GREEN. All six gates green
against the staged tree. Branch was rebased onto origin/main before the PR and contains
origin/main as of the round-2 push (8326169).

## note 2026-08-28

## note 2026-08-28 (agent) — review round 3 pushed (b6161e7): the delimiter row is held to the header's cell count

Round 2's one new finding, verified before the repair: `|---|---|` under the three-cell
header matched `_MD_DELIM` cell by cell and was accepted, so the reader published (60, 11)
from a table whose own shape disagrees with itself — the rows below were held to the
header's cell count while the delimiter was not. Fixed: `len(delim) ==
len(CHECKS_TABLE_HEADER)` joins the refusal, and the shape is pinned as a mutant ("the
delimiter row with the wrong cell count"). Closing line: **113 mutants died, 66 variants
passed** (round 2: 112/66). Live register still reads ((60, 11), []).

## note 2026-08-28

## note 2026-08-28 (agent) — review round 4 pushed (3a7cbef): an indented code block is not the register either

Round 3's Major, verified before the repair: a complete table indented four spaces or a tab —
header, delimiter, checks row carrying numbers that AGREE with the pin — was selected as the
register's table with the real table gone, reading `((60, 11), [])` green; `_md_cells` strips
leading spaces, so indent never stopped the read. `_unfenced` is now `_document_lines` and
excludes lines indented 4 spaces or a tab as well as fenced lines. A table indented into a
code block IS a code block in markdown, so refusing it is correct, and an indented row inside
a real table ends the table (reads as "no checks row") — both the fail-closed direction.
Pinned as the mutant "a complete table indented into a code block, with no real table".
Closing line: **114 mutants died, 66 variants passed** (round 3: 113/66).

Round 3's Trivial (add a caller-level corrupted-register assertion) was declined with
evidence: the caller-level comparison is already pinned one line under the fixture —
`check("and the decoy did not answer for it, so the measured comparison reddens",
_row != (60, 11), True)` — and the production end-to-end (exit 1, `got (99, 11), want
(60, 11)`) was demonstrated on the live register. Reply posted as a PR comment
(id 5448301883), read back against the sent text.

## note 2026-08-28

## note 2026-08-28 (agent) — review round 5 pushed (680975b): indentation is measured in columns

Round 4's Major, verified before the repair: `" \t| checks | ..."` — one space, one tab — is
4 columns of indentation (a tab advances to the next multiple of 4), so the line is an
indented code block in markdown, but `_INDENT_CODE` `^(?: {4}|\t)` matched neither prefix and
the block was read as document: a complete space-tab-indented table with agreeing numbers was
selected as the register's with the real table gone. Now column-correct: `^(?: {4}| {0,3}\t)`;
space+tab, 2sp+tab, 3sp+tab, tab and 5-space prefixes all probed and refuse. Pinned as the
mutant "a space-and-tab indented table, with no real table". Closing line: **115 mutants
died, 66 variants passed** (round 4: 114/66).
