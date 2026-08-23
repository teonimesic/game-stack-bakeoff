---
id: 55
title: 'A withdrawal register: declare retired figures so a gate can find them restated'
status: in_flight
priority: 4
refs: 'eval/findings/certifies-nothing.md #113, eval/tools/docstat.py, README.md, game-research-gpt evaluation/cross-engine/results/FINAL-CORRECTIONS.json'
done_when: 'a machine-readable register of withdrawn figures exists; a check asserts that no live document restates one outside a block citing that entry''s id; the check is red on the three sites #113 names before task 54 and green after; it carries a positive control planting a withdrawn pair in a temp copy and a negative control proving a declared withdrawal notice does not trip it; and it is wired into docstat.py --sweep only once it is green'
---


WHAT THIS IS

The import from `game-research-gpt`, axis 3. Their `cross-engine/results/FINAL-CORRECTIONS.json`
is an append-only machine-readable correction stored **beside** a frozen result: the frozen file
is never rewritten, and the correction is a declared delta a machine consumer can apply. The
property worth taking is not the freezing — this repository has git — it is that **a correction
is declared rather than inferred.**

WHY IT IS THE ONLY THING THAT COULD HAVE CAUGHT #113

The obvious alternative was built first and measured, and it comes out against: a cross-document
figure-agreement check found 52 labelled figures in the six live documents, one disagreement, and
that one a false positive. It could not see the real defect and never could, because the four
restatements of the withdrawn pair **agree to the digit**. A stale number that has been copied
forward is consistent; propagation and agreement are the same observation.

What separates a live figure from a retired one is not in the numbers at all. It is whether a
withdrawal was ever declared — a fact about the record.

THE DESIGN THAT AVOIDS A HAND-MAINTAINED ALLOWLIST GOING STALE

Do not key the exemption on file and line; lines move. Do not key it on a marker vocabulary
(`WITHDRAWN`, `superseded`, `a previous version read`); AGENTS.md's own audit is that a trigger
spelled as an enumeration has to be re-derived by the first reader who meets an item not on it.

Key it on the register id. The convention becomes: **a withdrawal notice cites its entry id**, and
the check is then one rule with no vocabulary in it — if every string of an entry co-occurs inside
a window and the window does not carry that entry's id, it is a live restatement.

FIRST ENTRY, ALREADY MEASURED

The pair 1.70 and 2.05, withdrawn 2026-08-22, replaced by figures reproducible with
`judge/field_ranks.py`. Its true sites are in #113. The check must be RED on them before task 54
runs and GREEN after — which is the positive control, and it is available for free because the
defect is real and currently unrepaired.

Two live documents are `eval/RUNS.md` and `eval/judge/RUBRIC.md`, which the scope must include;
`eval/FINDINGS.md`, `eval/findings/`, both `IMPROVEMENTS.md` and `CLEANUP-LOG.md` are the archive
and must be exempt. That live/archive partition currently exists only inside `docstat.py`'s scope
lists and in prose in `AGENTS.md`, and it does not classify `JUDGING.md`, `RUBRIC.md` or
`RUNS.md`. Deciding it explicitly is part of this task, because a gate whose scope is undeclared
is a gate whose scope will drift.

## Dispatch knowledge, 2026-08-23 — written back from a launch message

**Why the obvious design does not work, measured under task 11:** a cross-document
*figure-agreement* check was built and run — 52 labelled figures across six live docs, **1
disagreement, and that one a false positive.** It cannot work, because when a stale figure
propagates the restatements agree to the digit. **Propagation and consistency are the same
observation.** So the register inverts it: a figure is declared retired *by id*, and the check
asks whether anything still states it as current.

**Two live customers, so this is not hypothetical:**

1. **1.70 / 2.05** — retired under task 54, now correct in the live documents and marked in the
   archive. That is the green case.
2. **#54's claim** — `README.md`'s In-flight section still cites it as current (*"architecture
   and ux rank the field identically on both orders"*) while `JUDGING.md` says it is withdrawn on
   the repeat (tau 0.385 / 0.667). Confirm before building: if `README.md` turns out right, the
   register's first customer differs from what this ticket assumed, and that should be said.

**The archive must be able to state a retired figure freely** — `eval/findings/` exists to keep
it — so the register has to distinguish *stating* from *asserting as current*. If that
distinction cannot be made mechanical, report rather than gate, and say so.
