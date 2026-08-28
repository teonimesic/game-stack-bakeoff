---
id: 180
title: Seven tools carry a --selftest mode that no gate runs, and the ungated-control census cannot see them
status: done
priority: 3
refs: eval/tools/ci_minutes.py,.github/workflows/README.md,tasks/177
done_when: 'Each of the 7 is opened, timed, and either placed in a tier with its measured runtime, or recorded in .github/workflows/README.md''s exclusion table with the reason - the same disposal task 177 gave fragment_control.py and runner_capture_selftest.py. Then decide whether the population is worth a producer at all: if the 7 disposals are all ''excluded, needs a corpus'', a census over an open class of modes buys a check that can only report what the exclusion table already says, and the right outcome is to record THAT in the register rather than to build it. If it is worth one, it extends ci_minutes.py --controls and is pinned in both directions there: a planted tool whose --selftest no gate runs goes red, and a tool whose --selftest IS gated stays green.'
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/77
established_by: 'Task 180 merged as PR 77 squash. Verified against artifacts in the agent worktree at a2d027e2, not the report: ci_minutes --controls reproduces 26 declared / 25 gated / 1 recorded (skill_layout_control, register row at .github/workflows/README.md:404); ci_minutes --selftest exit 0 with 124 mutants dead and 80 variants passed; gates.yml carries 68 steps; tasks_mutants --selftest and the bare skill_layout_control run in controls.yml. Review verdict LANDED_COMMENT at the head, 3 round-1 threads resolved with measurements. Pre-merge repair: the PR body fixture counts 123/78 were stale from before review round 1; corrected to the measured 124/80 with the producer named, since the body is the squash commit message. Branch was behind by 3 (the handback note said 2; the queue commit landed after it was written) - mergeable.py taken as the live source, then update-branch and --squash --auto.'
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

## note 2026-08-28

Task 180 hand-back findings (PR #77, branch task-180-selftest-mode-census, head a2d027e).

THE TICKET'S 7 WERE REAL AND THE POPULATION WAS BIGGER. The ticket named 7 tools
whose --selftest no gate ran; a census over git-tracked .py under eval/ that declare
a --selftest mode (ast-based: an argparse add_argument Call whose first constant is
--selftest, or a Compare/membership dispatch -- two spellings) finds 26 declarers,
not 7. pool.py lives in eval/instrfollow/, outside the ticket's tools+judge glob;
tasks_mutants and skill_layout_control declare without being in any list. The ticket's
sharpest row was right: linkcheck --selftest existed and only its bare form was gated.

DISPOSAL: 9 gated in gates.yml tiers with measured local runtimes (linkcheck 0.039s;
census 0.055s; disclosure --skip-corpus 0.054s, bare form refuses exit 2 by design and
the corpus arm reads gitignored eval/runs/ which the whole-game report consumes per
rule 11; instruction_census 0.037s; judge_ledger 0.049s; tier1_census 0.059s;
tier2_census 0.047s; instrfollow pool 1.7s). tasks_mutants --selftest moved to
controls.yml (runs the whole suite plus baseline and inert controls, ~30s marginal).
1 recorded excluded: skill_layout_control --selftest is an alias of the gated
skill_layout_selftest.py and would only re-run the same pins. gates.yml is now 68
checks, controls.yml 11 suites; the register README carries all of it.

THE PRODUCER WAS WORTH BUILDING, and the hand census was wrong in both directions a
hand list can be. ci_minutes --controls now carries the mode census (one command
tokenisation, one register read, one problems list shared with the control census);
gated means the MODE is named. Pinned in both directions, run live before commit:
a planted tool (zz_task180_plant.py, argparse declarer, ungated) reddened the census
naming it; gating it in gates.yml turned the same census green; the tree reverted
byte-identical after. ci_minutes --selftest is now 124 mutants and 80 variants.

WHAT CAUGHT ME: the pre-commit docstat pin that forbids the register naming harness
scripts reddened my first README prose (I had named wholegame.py); reworded to the
register's unbackticked convention. Second: my first gates.yml edit was staged green
but the disclosure corpus arm would read eval/runs/ in CI, where it is absent -- hence
--skip-corpus, with the reason in the register.

REVIEW ROUND 1 (ceiling 5): 3 CodeRabbit threads on ci_minutes.py, all accepted with
evidence. (1) Major: the Compare branch of the declarer matcher missed two dispatch
spellings ("--selftest" in sys.argv with an Attribute; sys.argv[1:] == ["--selftest"]
with the token in a list literal). Widened to a closed class of three node kinds after
measuring on the live tree: 26 scripts before, 26 after, 0 false positives; two new
fixtures were non-members under the old matcher so their pins died on it. (2) Trivial:
the stem/address index was byte-identical in two functions; now one _script_index.
(3) Minor, defect reproduced first: the register was parsed twice and its problems
appended twice -- 2 duplicate-cause rows through controls_census at the previous head;
now one read with the spans passed like the pairs, pinned at exactly 1. CodeRabbit
confirmed the matcher fix and all 3 threads are resolved. Commit a2d027e; gates
workflow green in CI on it, controls workflow green on the parent commit 1071496.

Branch is behind main by 2 commits (c504021, 7c51c05); the coordinator confirmed the
update happens at merge time, and there is no overlap with those commits' files.
