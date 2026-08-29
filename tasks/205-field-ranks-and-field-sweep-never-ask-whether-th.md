---
id: 205
title: field_ranks and field_sweep never ask whether the rounds they pool or pair share a run
status: done
priority: 2
refs: 'eval/judge/field_ranks.py, eval/judge/field_sweep.py, eval/judge/aspects.py, FINDINGS #70 #80 #86, DECISIONS.md tier-3 producer section, eval/withdrawn.json WR-tier3-pair (the instead: names field_ranks --rounds), CLEANUP-LOG.md 2026-08-28 fifth pass'
done_when: 'field_ranks refuses (raises, fail-closed) any population where rounds CARRYING top-level run disagree on its value, and prints the existing warn_rounds_without_provenance listing for rounds that do not carry it, wired into main so the operator of --rounds sees it without remembering to ask; field_sweep refuses or loudly warns before any round is written or paired when a stored round in --out carries a run different from --run. Both directions pinned in the selftests: refuse-disagree red/green, warn-absent green on a corpus with no run fields (the tetris-judge corpus stays readable, verified against eval/runs/wg-tetris-judge-2026-08-17/pre via --runs-root on the main checkout). The 30-round aspect-reliability directory must still report identically to today (all one run), diff the output before and after.'
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/85
established_by: 'Verified by the orchestrator against artifacts at head 0b7b4983, merged as fe96eee (#85). field_ranks --selftest 24 checks 0 unmet (corpus row prints [NOT RUN] without --runs-root; with it: 10 of 10 tetris-pre rounds run-less, 0 refused, report exit 0, published 1.3125/2.5625 reproduces - pre-change tool on main read the same pair). wg-aspect-reliability --per-aspect byte-identical pre/post; tetris-pre figures unchanged, diff adds only the NO PROVENANCE listing. field_sweep --selftest exit 0 (wiring pin + CLI refusal); sweep_bounds_control 20/20; dead_private_control 18 measurements 0 FAILED; gates.yml 72 steps; ci_minutes --selftest ok (124 mutants, pins 29/28). Live RED through the real CLI: foreign provenanced round in a fresh --out refused exit 1, both runs named, nothing written; main had no assert_out_run (grep 0). docstat --sweep 271 docs clean, tasks.py check clean, --renumbered clean. CodeRabbit round 1''s 2 inline findings verified fixed at head (10-of-10 wording; register 29/28). Findings: none new - the join defect is #70/#80''s subject, the capture-without-consumer lesson is #86''s, count moves pinned in ci_minutes.'
---

FOUND 2026-08-28 cleanup pass, the area the fourth pass deferred (field_ranks.py 743 lines and field_sweep.py 619 lines, both read whole). Two defects, one mechanism family. (1) field_ranks._by_stack joins every round in a directory by submission id - per_sub[s['submission']].append(...) across ALL rounds - and assert_poolable checks aspect classes only; no line asks whether the rounds share a run. #80 established that a game is not unique across runs (four stored g2_tetris3d fields in different repair states) and fixed it AT THE SOURCE: field.py writes mapping run into every round since 2026-08-22. The capture exists; no analysis consumer reads it. The join that #70 made infamous (same trial id, different games, plausible tables) is one --rounds flag away in the tool DECISIONS.md names as THE producer for tier-3 figures and the withdrawn register points operators at. (2) field_sweep ACCUMULATES rounds into --out across invocations by design (rolling summary, task 63), keyed by filename {game}__{aspect}__seed{N}.json with no run component; the [have] resume path loads them and the gates pair on game+aspect equality only (line 597), so re-running the same command with --run aimed at a different stored run silently produces order_invariance and reproducibility gates across two fields, a field_cost_usd summing both, and a directory field_ranks then pools. The #93/#120 finding measured that partial re-runs into existing directories HAPPEN here. MEASURED on the stored corpus: 30 of 30 wg-aspect-reliability rounds carry top-level run (all one run); 0 of 10 wg-tetris-judge-2026-08-17/pre rounds do (they predate provenance), so any guard must warn-absent rather than refuse when run is missing, or the tool becomes unable to read the very corpus the withdrawn register cites. Baseline: field_ranks --selftest 0 unmet, sweep import and SUMMARIES assert green at HEAD 59732aa.

## note 2026-08-28

## Done — PR #85, review clean at round 2

Branch `task-205-cross-run-pooling-guard` (worktree `agent-a81e607aa6d06b44b`), two commits: `30b264a` (the guard) and `0b7b498` (review round 1).

### What exists now

- `eval/judge/field_ranks.py`: new `assert_one_run(rounds) -> list[dict]` — rounds CARRYING top-level `run` must agree or `figures()`/`report()` refuse (ValueError naming both runs, their files, #70/#80, "Split the directory by run"); rounds carrying none are RETURNED as a third value and LISTED via `warn_rounds_without_provenance`, never refused. Called inside `figures()` beside `assert_poolable` (rule 13: at the resource) and at the top of `report()` before any output. `main()` prints the warning listing with `out_dir=Path(args.rounds)`; new `--runs-root` flag for the selftest corpus pins. CLI catches the ValueError and prints `REFUSED: ...` to stderr, exit 1.
- `eval/judge/field_sweep.py`: new `stored_round_run(out)` and `assert_out_run(out, run)` — SystemExit BEFORE any mode writes or pairs when a stored round in `--out` names a run different from `--run`; run-less rounds returned and listed by `main()` (same `warn_rounds_without_provenance` listing plus a summary line). Guard wired after the applicability refusal, before all three mode dispatches. New `--selftest` mode (previously the module had none).
- The `warn_rounds_without_provenance` listing — #86 cited it, the 2026-08-28 fifth cleanup pass measured it invoked by nothing — now has two callers, one per CLI.

### Both directions pinned

- refuse-disagree: ranks selftest checks 19-21 (same-run measurable as before; mixed-run raises with EMPTY stdout; mutant shows the unguarded join returns the plausible 2.0/0.5 so the guard acts). sweep selftest checks 2-3 and 6-7 (matching run reused; foreign run refused naming file/both runs/remedy; wiring pinned called-exactly-once-in-main before every dispatch and before the first `a.out.mkdir(`, with the delete-the-call mutant going red; CLI subprocess refusal exit 1, nothing new written).
- warn-absent stays green: ranks checks 22-24; sweep checks 1, 4, 5. Corpus pin: `wg-tetris-judge-2026-08-17/pre` via `--runs-root` on the main checkout — 10 of 10 rounds run-less, 0 refused, report exits 0, all 10 listed, published rank+pool pair 1.3125/2.5625 reproduces.
- Byte-identity: 30-round `wg-aspect-reliability` (30/30 carry run, all one run) reports BYTE-IDENTICAL to the pre-change baseline, diffed, exit 0.

### Numbers

- selftests: field_ranks 24 checks, 0 unmet; field_sweep 7 groups, 0 unmet; sweep_bounds_control 20/20; dead_private_control 18 measurements 0 FAILED (152 methods, 0 dead); ci_minutes --selftest ok; docstat --sweep and tasks.py check clean.
- Adding the sweep --selftest step moved 3 counts ci_minutes pins: gates 71→72, --selftest-declaring scripts 28→29, mode-named-by-a-tier 27→28. Register README's counts moved with them in the same commit (caught by the pre-push gate's ci_minutes run, which is the gate working).

### Review (2 rounds, then clean)

Round 1 found 2 real defects, both fixed in `0b7b498`: (1) my field_ranks docstrings said "0 of 10 rounds predate the field" — inverted, 10 of 10 do, and the wrong figure removed the reason for warn-not-refuse; (2) the register's mode-census paragraph I edited disagreed with its own producer (28/27 vs 29/28). Round 2: LANDED_COMMENT, nothing further.

### Docs

DECISIONS.md tier-3 producer section: population is now 3 properties (run row added to the table) plus the sweep-end guard and the warn-absent half; JUDGING.md pooled-population section: ONE RUN paragraph; field_ranks/field_sweep module docstrings; gates.yml gains `judge/field_sweep --selftest` beside the field_ranks step; workflows README register updated.

### For the orchestrator

No new finding number needed: the underlying defect (join by submission id across runs; #70/#80 already numbered) is this task's subject, and the counts moved here are pinned in ci_minutes rather than findings. PR #85: https://github.com/teonimesic/game-stack-bakeoff/pull/85
