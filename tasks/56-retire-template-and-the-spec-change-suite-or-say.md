---
id: 56
title: Retire template*/ and the spec-change suite, or say why four forked product trees stay
status: done
priority: 2
refs: 'template-ts/, template/, template-unity/, template-godot/, eval/run-bakeoff.sh, eval/suites/bakeoff-ts.toml, eval/FINDINGS.md #112, eval/findings/documentation.md #99'
done_when: either all four template*/ trees and eval/run-bakeoff.sh and eval/suites/bakeoff-*.toml are removed with the retirement stated in eval/RUNS.md and README.md, and eval/tools/docstat.py --sweep green afterwards; or DECISIONS.md carries a dated row saying the four templates stay, naming the consumer that justifies them, and a gate exists that compares the instrument files shared by each template*/ and eval/starters/*/ pair, green on the repaired trees and red under a planted single-line divergence in each of the four
established_by: 'RETIRED. Deleted 197 tracked files: the four template*/ trees (195) plus eval/run-bakeoff.sh and eval/archive-and-rerun.sh, the only two things that could launch a spec-change trial. KEPT, and this is the part the ticket got wrong: eval/suites/*.toml, suites/prompts.py, holdout*/ and variants/ stay, because a stored trial records task: t1_rally and no prompt - scanned the first line of the rally prompt across eval/runs and got 0 hits over 12 run directories and 71 trials including the work trees and bakeoff.log, against 6 hits in eval/suites, with the scanner proved on eval/suites first (rule 12). Deleting those tomls would have made 71 trials well-formed and uninterpretable; filed as FINDINGS #119. runner.py stays whole: judge/static.py resolves it by path for the one-policy capture (#114), and it is the definition of the measurement the stored verdicts report. Its run and check-suite now exit 2 naming the retirement instead of raising in copytree three frames down - negative control exit 2 with the message, positive controls runner.py report on bakeoff-ts-2026-08-11 printing 6/6 100% $2.57 and regrade.py --suite bakeoff-ts.toml reading 6 trials 0 changed. Baseline before touching anything (rule 14): sweep exit 0, runner_capture_selftest 50/50, judge/capture_selftest 39/39; identical after. Template-only files, three kinds across the four pairs and nothing outside template*/ depends on any: a golden rally.png per stack, a playability test per stack, and unity''s Pong.Analyzers.dll with PongView/PongRunner - the analyzer is a 22-line namespace rename of the starter''s Starter.Analyzers, and the starter is the better copy because it ships the csproj that template-unity never had. Task 48''s 3-only-in-template for the ts pair does not reproduce: 2 at ee8625f and 2 at ee8625f~1, tracked or on disk. No stored evidence became unreadable - every run directory holds full work trees with a baseline commit. Recoverable: 139 commits, a3d0fd1 and ee8625f both verified on origin/main with git branch -r --contains, which is the property #104 did not have. Cost accepted and stated: task 48''s capture-page port into template-ts, six hours old, is discarded. Docs: DECISIONS.md carries the retirement, the reason and a reversal condition; README.md, AGENTS.md, eval/AGENTS.md, eval/BAKEOFF.md, eval/FINE-TUNING-BRIEF.md, eval/RUNS.md and three skills updated; RUNS.md records that this is NOT a fifteenth comparability boundary because there is no future run to bound. sweep 0 after, corpus 131 -> 117 docs. Branch task-56-retire-templates.'
---

Task 48 found the pre-fix TS capture page alive in template-ts a day after task 31 repaired it in eval/starters/ts, and ported the fix. That closes the instance and not the shape. Measured while doing it: 0 of the 105 commits since the repo import touched any template*/ directory and 6 touched eval/starters/; the only executable reference to template*/ anywhere is eval/run-bakeoff.sh driving runner.py --template; the spec-change suite it feeds has not run since 2026-08-12; and DECISIONS.md records the user decision that tasks are whole-game builds, not spec changes, with the same file noting the spec-change suite already failed to separate four stacks that all scored 6/6. Nothing compares the two trees: starter_parity.py defaults to eval/starters and measures stacks against each other, never a stack against its own second tree. This is not #99's remedy, because these are not copies. Measured across the ts pair: 15 shared paths byte-identical, 18 differing, 1119 changed lines, 3 files only in the template and 7 only in the starter. template-ts is a finished Pong, eval/starters/ts a game-agnostic placeholder with probe and film contracts. Most of that difference is intended, so no content-parity gate can be written until someone decides what agreement means, and a gate red on the day it lands gets switched off (DECISIONS.md). The recommendation from task 48 is retirement of all four templates together with the spec-change suite that is their only consumer, because a fork with a dormant consumer has nothing pulling it back into line. That deletes an experiment, which is a programme decision rather than a technical one, so it is filed rather than made. If the answer is instead to keep them, the same session must name the shared part - the capture and verification instrument, as distinct from the game - and gate on that, since after task 48 template-ts/src/view/harness.ts differs from the starter on prose only.

## Dispatch knowledge, 2026-08-23 — written back from a launch message

**The operator decided: RETIRE.** Do not re-litigate it.

**A constraint created AFTER this ticket was filed.** `eval/judge/static.py:34` resolves
`runner.py` by path and takes `parse_test_counts`, `parse_skipped`, and the capture functions
task 50 deliberately consolidated there so two truncation policies could not diverge (#114).
**So `runner.py` cannot be deleted.** This ticket's `done_when` says "delete all four templates
plus the bakeoff suite"; that was written before the dependency existed. If the clean outcome is
that `runner.py` stays and only its `--template` entry points go, that is the right answer —
record it.

**What is emphatically NOT in scope:** `eval/starters/{rust,ts,unity,godot}/` are the fine-tuned
starting points every whole-game trial copies (`wholegame.py:60`). Measured distinction —
`template-ts/src/sim/index.ts` carries 70 game-specific terms (a finished Pong) against the
starter's 1 (a game-agnostic placeholder). The templates ship the interesting part, which is why
they are not starting points and why they are being retired.

**Establish what is lost before losing it.** Task 48 measured 3 files present only in a template.
Name them. Check whether any stored `eval/runs/bakeoff-*` evidence becomes uninterpretable
without the tree that produced it. `template-ts` received the capture-page repair hours ago
(#112) — deleting it discards that work, which is correct, but say so.

**The safety property that makes this different from #104:** these trees are in git and pushed —
`git log -- template-ts` resolves across 139 commits. A work tree that was never committed had no
such recovery. State that in the commit so nobody generalises from this to something
unrecoverable.
