---
id: 226
title: verify_blind.py trial-tree checks have no can-fail proof anywhere
status: done
priority: 3
refs: 'eval/judge/verify_blind.py, eval/judge/blurb_selftest.py, finding #39, task 224, task 200'
done_when: '1. eval/judge/verify_blind.py carries a --selftest mode: builds fixture trial trees under tempfile (no eval/runs, no network), plants at minimum the four shapes - canary GUID in a trial tree, a real criterion id in a trial tree, RUBRIC.md at an ancestor of one, bare invocation - each asserted to the nonzero exit WITH the offending file named in output, plus one clean fixture asserted to exit 0 (the positive control), plus a floor pin that criterion_ids() is nonempty. 2. The can-fail half: a mutant copy of the tool with the trial-tree scan neutered makes the selftest fail - run it, record the red rows here, and state the neutering mechanism. 3. A CI tier names the mode (verify_blind --selftest in controls.yml); the register count and coverage sentence move 29 to 30 selftest-declaring scripts; ci_minutes --selftest exits 0. 4. eval/tools/docstat.py --sweep and --renumbered and eval/tools/tasks.py check all exit 0 at the branch head. 5. The live starters stay untouched - every plant lives in the selftest own fixtures, and the selftest exits 0 at the branch head.'
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/106
established_by: 'Merged as #106 squash 195b47a, branch updated onto main and CI re-run green at 7d24aca (controls 13m2s, gates 2m44s). Verified by orchestrator in own detached checkout: --selftest 25/25 exit 0; can-fail re-proven BY HAND, not only via the selftest''s mutants - scan line hand-neutered -> selftest exit 1 at 21/25 with the recorded red rows; vocab hand-emptied (isolated from ancestor RUBRIC.md) -> planted ball.wall_bounce leak reads ''0 checked''/BLIND/exit 0 while shipped exits 1, so the if-strict_vocab-and-ids fail-open shape is real and now pinned. Register both directions live: controls.yml step removed -> ci_minutes --controls exit 1 UNRECORDED eval/judge/verify_blind.py; restored -> exit 0 at 31 declared/30 gated/1 recorded-bare. Producer read 30/29 at main against prose saying 29/28-of-29 - stale by one from task 224 (pins moved, prose did not); repaired to the produced value, deviation from done_when 3''s 29->30 prediction accepted and recorded in the PR body. Gates at head: docstat sweep/renumbered/findings/withdrawn 0, tasks check well-formed, ci_minutes --selftest exit 0 (124 mutants, 80 variants). --packs over stored packcheck/repack dirs flags only #131''s recorded unrepaired stored-pack state and the intentional audit copy - pre-existing at main, packs code byte-identical. Starters untouched. Review: one CodeRabbit summary, no actionable comments; verdict NOT_YET at merged head (no round), merged on artifact verification. Findings decision: no new finding - both candidates (the fail-open gate: rule 7/#31 family, never fired, now floored; the stale prose: recorded restatement-drift, producer run and repaired in the same PR) are instances of recorded lessons and no published figure moves.'
---

WHAT IT IS: eval/judge/verify_blind.py is the blinding gate - run-matrix and evaluate-run invoke it unpiped as a gate on every run (both SKILL.md files, line 20), and README.md:10 points readers at it for the blinding claim. Three checks on trial trees: the RUBRIC canary, rubric reachability from any ancestor, the criterion vocabulary.

WHAT IS WRONG, MEASURED 2026-08-30 at main HEAD c33e55b: nothing in the repository proves the trial-tree half can fail. Grep for the canary across eval/judge/*_selftest.py, *_mutants.py and *_control.py returns zero files; the only can-fail pins are blurb_selftest.py:1094/:1102, which exercise --packs, not the trial-tree path the skills gate on. The CI register cannot see the file either: ci_minutes --controls censuses _control/_mutants/_selftest stems plus scripts declaring a --selftest mode, and verify_blind.py is in neither population, with no left-out row - consistent with the table rules, which is exactly why nothing asks. Pass 29 of CLEANUP-LOG.md proved by hand that all three checks still CAN fail (canary GUID planted in a trial tree - exit 1 naming the file; ball.wall_bounce planted in the ts tree - exit 1 CRITERION ID; RUBRIC.md at an ancestor s/judge/ - exit 1 REACHABLE; bare invocation - exit 2), but that proof lives in a shell history, not in a script the next session can run.

WHY IT MATTERS: a scan that stops being able to fail prints BLIND at exit 0 on every future run and nothing disagrees - finding #39 (the grader green on everything including its own mutant) pre-emptively, on the gate behind the README blinding claim. Sibling defect in the same function: check 3 gates on (strict_vocab and ids), so an empty criterion vocabulary silently no-ops it - the run prints 0 checked but still exits 0 BLIND.

THE FIX IS A PROPERTY, NOT A MECHANISM: after the fix it must be possible to make verify_blind.py FAIL, from a script in the repository, on each of its trial-tree checks - and the register must see the file, which a --selftest mode does by construction (it enters the ci_minutes second population, where a tier must name the mode). The pins are the agent to shape, subject to: fixture trees only (offline, nothing under eval/runs); each contaminated shape asserts the nonzero exit AND the offending file named; a floor pin asserts the criterion vocabulary is nonempty (84 ids on 2026-08-30); a mutant that neuters the scan turns the pins red. WHAT MUST STILL FAIL AFTER THE FIX: a verify_blind whose scan returns nothing on contaminated input must fail the selftest - the same thing the pass-29 hand probe did to the shipped checks.

## note 2026-08-30

## Established

Broken state (before, measured on the shipped tool, unpiped): canary GUID planted in a
trial tree -> exit 1 naming `CANARY IN TRIAL TREE` + the file; a real criterion id
(`ball.wall_bounce`) planted -> exit 1 naming `CRITERION ID ball.wall_bounce` + the file;
RUBRIC.md at a trial-tree ancestor -> exit 1 naming the planted path; clean fixture ->
exit 0 BLIND; bare invocation -> exit 2 with the argparse refusal. So all three
trial-tree checks CAN fail by hand - and no script in the repository pinned any of it:
no `*_selftest.py`/`*_mutants.py`/`*_control.py` under eval/judge carries the canary,
and `ci_minutes --controls` had verify_blind.py in NEITHER census population.

Fix: `verify_blind.py --selftest` - 25 expectations, all holding at the branch head.
Fixtures under tempfile (no eval/runs, no network, starters untouched), one subtree per
shape: canary plant, criterion plant (id read from the live vocabulary, sorted[0]),
both ancestor arms (planted RUBRIC.md file; planted `judge/RUBRIC.md` dir), clean tree,
bare invocation. Each contaminated shape asserted exit 1 with the offending file named;
clean asserted exit 0 BLIND; bare asserted exit 2. Floor pins imported from the file:
`criterion_ids()` nonempty (84 today; the pin is nonempty, not the cardinal - the
vocabulary moves when the rubric does) and `canary()` nonempty, plus a row requiring the
printed `criterion ids : N checked` to equal the imported len().

Can-fail half, both mutants built from the tool's own source by marked-line surgery:
- MUTANT scan-neutered: the line carrying the SELFTEST-NEUTER-SCAN marker - scan()'s
  only hit append - replaced by `pass`. Run by hand over a leaking tree: exit 0, BLIND,
  CONTAMINATED absent (the check dead). Its own --selftest exits 1 at 21/25 with red
  rows: `canary plant exits 1 naming the file`, `criterion plant exits 1 naming the id
  and the file`, `MUTANT scan-neutered: the mutation changed the source`, and
  `MUTANT vocab-emptied: the canary plant is STILL caught` (inheritance: the
  second-order mutant is built from already-neutered source, so its scan is neutered
  too). In the shipped suite the same rows are asserted in the red direction while the
  ancestor arms, clean tree, bare refusal and printed count are asserted STILL GREEN -
  the neutering must take check 1 and 3 down without taking check 2 with it.
- MUTANT vocab-emptied: the `ids = set(...)` line carrying SELFTEST-VOCAB-SOURCE
  replaced by `ids: set[str] = set()`. Check 3 is gated on `if strict_vocab and ids`,
  so the leak passes as BLIND with `0 checked` - pinned red as exactly that signature,
  plus the imported vocabulary asserted empty, while the canary plant, ancestor arms,
  clean tree and bare refusal stay green.
Structural rows count the marker (2 in shipped source: the constant and the marked
line; 1 in a correctly mutated copy) rather than searching the mutant for a guard
string - task 113's shared-object trap.

Register, both directions measured live: after the mode existed but before wiring,
`ci_minutes --controls` exited 1 with `UNRECORDED eval/judge/verify_blind.py` (the
register check CAN fail; census read 31 declarers / 29 gated). After wiring controls.yml:
exit 0 at 31 declarers / 30 gated / 1 recorded-bare, and the stem census unchanged at
47/43 named/4 recorded. Pins moved in ci_minutes.py: controls gate count 11->12 (two
sites), mode population 30->31, gated 29->30, precedent comment extended with task 226.
Register `.github/workflows/README.md`: opening table 11->12 controls gates; controls
prose names `verify_blind --selftest` and what it proves.

Gates at the staged head, all unpiped, all exit 0: docstat --selftest / --findings /
--withdrawn / --sweep / --renumbered (0 stale, 0 untriaged of 37), tasks.py check (225
well-formed; the pre-existing done_when 'all' warning on 226 is the ticket's own
wording), ci_minutes --selftest, ci_minutes --controls, verify_blind --selftest, and
verify_blind --packs on a scratch dir (the path blurb_selftest drives, unchanged).
git status re-checked clean after the gates - nothing rewrote a staged file.

Needs a finding number (orchestrator): the register prose was stale by one BEFORE this
task - it said 29 scripts declare --selftest and `28 of the 29` gated while the producer
said 30/29 (task 224 moved the pins but not the prose; the files were identical between
main and this worktree before I touched anything, so the miss is on main). Repaired here
to 31/30, the produced value. The counts had a producer; the PROSE beside them had none
reading it - same shape as task 132's population prose.
