---
id: 180
title: Seven tools carry a --selftest mode that no gate runs, and the ungated-control census cannot see them
status: todo
priority: 3
refs: eval/tools/ci_minutes.py,.github/workflows/README.md,tasks/177
done_when: 'Each of the 7 is opened, timed, and either placed in a tier with its measured runtime, or recorded in .github/workflows/README.md''s exclusion table with the reason - the same disposal task 177 gave fragment_control.py and runner_capture_selftest.py. Then decide whether the population is worth a producer at all: if the 7 disposals are all ''excluded, needs a corpus'', a census over an open class of modes buys a check that can only report what the exclusion table already says, and the right outcome is to record THAT in the register rather than to build it. If it is worth one, it extends ci_minutes.py --controls and is pinned in both directions there: a planted tool whose --selftest no gate runs goes red, and a tool whose --selftest IS gated stays green.'
---

Task 177 built ci_minutes.py --controls, which censuses scripts whose whole purpose is to be run as a gate - the closed class of stems ending _control, _mutants, _selftest, 40 of them. A SECOND population has the same defect and that census cannot see it: a tool whose main job is something else and which carries a --selftest mode pinning its arithmetic. 28 scripts under eval/ declare a --selftest flag. 15 have that exact invocation in gates.yml or controls.yml. 6 more are control scripts the 177 census already covers, and precampaign_smoke.py is recorded as excluded. That leaves 7 whose --selftest no workflow step, no git hook and no register row names: census.py, disclosure.py, instruction_census.py, judge_ledger.py, tier1_census.py, tier2_census.py, and linkcheck.py (whose BARE form is gated - the --selftest is the half that is not). Measured 2026-08-27 on task 177's branch with: grep -l -- '"--selftest"' eval/tools/*.py eval/judge/*.py, against python3 eval/tools/ci_minutes.py --gates --json. These were deliberately left out of 177 rather than missed: the property there is a closed class of file stems, and 'a tool with a selftest mode' is decided per tool - census.py's selftest may be worth 0.2s in gates.yml or may need a corpus that is gitignored, and neither the 177 check nor its author can tell which without opening each one. Seven undecided rows in front of a reader is what turns a green gate into one people skip.

## note 2026-08-28

## note 2026-08-28 (orchestrator) — current at dispatch

**What moved under your census since filing (2026-08-27):** `.github/workflows/README.md` was
edited by task 193 (6 path prefixes, no gate changes) and by task 196's merge (`b1fb3d9`, one
fixture-path line in controls.yml's comment — also no gate change). Task 194 added
`eval/tools/prompt_guard_control.py` — `_control`-stemmed, so inside task 177's closed class,
not yours — and task 195's `hook_audit_control.py` changes are the same stem. So the 7-tool
population is probably unchanged, but that is a guess: re-run the ticket's own census method
(grep for `"--selftest"` against `ci_minutes.py --gates --json`) before deciding, and treat a
grown population as the more interesting outcome, not a problem.

One of the 7 from your list now has a live consumer worth checking before you time it:
`disclosure.py` is read by `wholegame.py report` per rule 11 (it prints located passages beside
scores), so its selftest's cost class may have changed since filing. `linkcheck.py`'s bare-vs
`--selftest` split (the gated half and the ungated half of one tool) is still the sharpest row
of the 7 — whatever you decide for it generalises to the rest.
