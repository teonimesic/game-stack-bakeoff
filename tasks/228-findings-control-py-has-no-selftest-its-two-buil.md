---
id: 228
title: 'findings_control.py has no --selftest: its two build() refusals are unpinned'
status: done
priority: 2
refs: CLEANUP-LOG pass 39; .agents/skills/tasks/SKILL.md
done_when: 'python3 eval/tools/findings_control.py --selftest exists, prints ok/FAIL per assertion and exits 1 on failure, asserting: (a) a mutant whose anchor is absent from docstat.py refuses; (b) a mutant whose anchor is AMBIGUOUS refuses — built at run time from a string measured to occur more than once in the live docstat.py, never a hardcoded line (the code moves). Read .github/workflows/README.md before adding the mode: ci_minutes.py --controls''s selftest census counts scripts declaring --selftest and asks that a workflow step or git hook names each one, so the new mode must be added to the workflow step that runs findings_control.py, or the census goes red. Plain controls and --all-mutants must still exit 0.'
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/108
established_by: 'Merge 59674c2 (PR #108 squash), verified on main 2026-09-02: --selftest prints 4 assertions 0 failed and exits 0 — absent-anchor refusal, ambiguous-anchor refusal (anchor measured at run time: 26 occurrences in live docstat.py), real mutant applies exactly once, docstat.py byte-identical before/after. No finding: the task pinned existing refusals, it published no number and no defect was measured beyond the absence of pins.'
---

Pass 39 (CLEANUP-LOG) added the ambiguity refusal to build() — a mutant anchor occurring more than once in docstat.py must SystemExit rather than silently mutate whichever copy came first — beside the existing absent-anchor refusal, and verified both by ad-hoc invocation in that session only. Nothing in the repository pins them. tasks_mutants.py pins its drifted-anchor refusal with a --selftest mode and is named in CI for it; findings_control's guards are one edit away from silent removal, and the failure is invisible when they go: a deleted guard just means the next ambiguous anchor mutates the first copy and the controls grade a mutation the file did not name.

## note 2026-08-31

Landed as PR #108, one review round, LANDED_COMMENT (nothing actionable; the pool then read "Review limit reached", so expect no further rounds on this branch).

What exists now: `findings_control.py --selftest` - 4 assertions, ok/FAIL per row, exit 1 on failure, 0.09s locally. (a) an anchor absent from docstat.py refuses; the sentinel is itself measured absent first, so a row that stops naming its refusal fails saying so. (b) an ambiguous anchor refuses, built at run time by `_repeated_line()` walking the live docstat.py - first non-blank line whose count exceeds 1, with that count; a hardcoded anchor would read zero once the code moves and then trip the ABSENT refusal, passing while naming a refusal it is not about. If no line repeats the row FAILs - never a skip. (c) a real mutant (`no_count_check`) must still apply, exactly once - rule 15's variant half, without which both refusal rows are equally green under a build() that refuses everything. (d) docstat.py byte-identical before and after.

Two lessons the next agent should not re-derive:

- **"Occurs" is two measurements.** `_repeated_line` first counted LINES while `build()` refuses on SUBSTRING counts; the mode's own first run went red on the gap - the docstring fence measured 86 as a line and 190 as a substring, refusal correct at 190, assertion demanding 86. The count returned is now the substring count, the same expression build() computes, and the lesson is in the function docstring.
- **The red-direction demo's own anchor was ambiguous.** Deleting the refusal via `if n > 1:` -> `if False:` matched twice, because `_repeated_line` also contains that test; the demo had to anchor on the comment line below it. Same hazard the refusal itself guards against, met one hour later in the tool verifying it.

Red direction demonstrated per refusal (ad-hoc, in-session, copies only): a copy of findings_control.py with `if n > 1:` -> `if False:` exits 1 naming the ambiguous row; with `if n == 0:` -> `if False:` it exits 1 naming the absent row. Nothing permanent pins findings_control.py itself against mutants (no findings_control_mutants.py) - the green half re-runs on every push via gates.yml, the red half is this session's demonstration.

CI wiring the ticket required: gates.yml runs the mode beside the bare form, so the ci_minutes --controls mode census reads it NAMED (32 declaring / 31 gated / 1 recorded, 0 unrecorded). Three live pins moved and were updated: ci_minutes --selftest gates count 74 -> 75, mode population 31 -> 32, gated 30 -> 31 (history comment records task 228). Register: opening-table checks row and pre-push coverage sentence to 75, findings_control paragraph documents the mode. All gates green unpiped against the staged tree: ci_minutes --selftest (124 mutants died, 80 variants passed), --controls, --gates, docstat --sweep, tasks.py check, and findings_control plain (21 controls, 0 failed) / --all-mutants (9, 0 survived) / --selftest.

No finding number needed - nothing new measured about the world; the guard pass 39 added is now pinned.

## note 2026-08-31

Orchestrator verification (against artifacts, not the report): PR #108 head 8dce659 verified in a throwaway worktree at /tmp/p108-verify — --selftest 4/4 exit 0 (ambiguous anchor measured live at 26 occurrences, not hardcoded); plain controls exit 0; --all-mutants 9 mutants 0 survived; RED half reproduced by silencing only the ambiguous-anchor raise: selftest exits 1 naming exactly that row, other three stay green; ci_minutes --selftest ok (124 mutants died, 80 variants passed); census reads 32 declaring / 31 named / 1 recorded / 0 unrecorded; docstat --sweep clean; 227 tasks well-formed at the PR tree; diff scope exactly the ticket's 4 files. First red attempt was my own broken control (regex deletion left an unterminated string; its exit 1 was a SyntaxError, not the selftest) — redone as a neutralized raise. Merge awaits the operator, same as PR #107.
