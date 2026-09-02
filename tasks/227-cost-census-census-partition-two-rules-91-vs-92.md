---
id: 227
title: cost_census.py and census.py partition the same tree by two rules that agreed when written — 91 vs 92 whole-game records today
status: done
priority: 2
refs: 'eval/tools/cost_census.py, eval/tools/census.py, eval/SCENES.md, agent_harness.py, tasks/145, CLEANUP-LOG.md pass 34'
done_when: '1. ONE classifier decides whole-game/scene/spec-change, and ONE definition of NOT_A_RUN, exist in the repository and are imported by both eval/tools/census.py and eval/tools/cost_census.py — agent_harness.py is the natural home (cost_census.py:114 already imports TOKVAL_HARNESS from it). Neither CLI keeps a local literal copy: no `frozenset({"work", "artifacts", "targets"})` outside the shared module, and cost_census.py:120''s "Same test as census.py" comment replaced by the import it describes. 2. cost_census''s whole-game population is task_class-aware, and the scene record it miscounts today is not silently absent: the report states the scene population under a named label (or a counted exclusion), so a skip nobody counts is not the replacement defect. 3. Selftest pins on both sides: a fixture record carrying BOTH `game` and `task_class: scene` classifies as scene in the shared classifier and lands in NEITHER producer''s whole-game population; a mutant that reverts either producer to a local literal partition turns a pin red. 4. Both producers re-run over eval/runs/ (read-only) and AGREE: census.py''s WHOLE-GAME record count equals cost_census''s whole-game records-read count, with the commands, the date and both numbers recorded in this ticket. 5. Gates exit 0 at the branch head, unpiped: docstat.py --sweep, docstat.py --renumbered, tasks.py check, ci_minutes --selftest and --controls; nothing under eval/runs/ written.'
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/107
established_by: 'Merge 594841c (PR #107 squash), re-verified on main 2026-09-02: census.py and cost_census.py over the main checkout''s eval/runs both print whole-game 91, scene 1, spec-change 71. cost_census_mutants 42/42 with partition_by_field_presence red and control green; census hand-mutation 19 named failures; wallclock 13/13; NOT_A_RUN identity pins green. Finding #213 allocated at merge; establishment note in the ticket.'
---

WHAT IT IS: two producers read the same stored tree. `census.py` is the tree census — it partitions
every `trials/*.json` record into WHOLE-GAME / SCENE / SPEC-CHANGE off `task_class_of()`
(census.py:111: whole-game iff `task_class == "game"` or the key is absent; scene iff `"scene"`;
any other value refused by name). `cost_census.py` is the cost-result producer — between-stack
range over the within-cell floor, per (run, game) — and its whole-game test is
`WHOLEGAME_KEY not in d` (cost_census.py:344): field PRESENCE, not task_class value.

WHAT IS WRONG, MEASURED 2026-08-30 at main 9328a03: the two producers disagree on the tree as it
stands. `python3 eval/tools/census.py` → WHOLE-GAME **91** records over 12 run directories, SCENE
**1** record. `python3 eval/tools/cost_census.py` → "whole-game trial records read **92**". The
disputed record is `eval/runs/wg-scene-s1ts-2026-08-25/trials/s1_parallax__ts__t0.json`, which
carries BOTH `game: s1_parallax` AND `task_class: scene` — census.py files it under SCENE
(verified: census.py selftest Direction 8, census.py:539-546, plants exactly this both-fields
shape and pins it to SCENE), while cost_census's presence-only test admits it as whole-game. The
comment at cost_census.py:120 says **"Same test as census.py, deliberately — two spellings of one
partition disagree eventually"** — the test stopped being the same when the first scene record
landed (2026-08-25), and the prediction in the comment's second clause is now true: the two
totals disagree and neither producer reports a disagreement. Second channel, same shape:
`NOT_A_RUN = frozenset({"work", "artifacts", "targets"})` is defined independently at
cost_census.py:124 and census.py:144 — identical today, no import, no assertion. The file's own
TOKVAL_HARNESS comment (cost_census.py:111-114) names this exact failure shape for the harness
definition ("restating the rule in both, with nothing asserting they agree, is how one tree comes
to have two totals") and then commits it four lines down for the partition and the skip-list.

WHY IT MATTERS: cost_census's published `wholegame_records: 92` is wrong by one under its own
label, and the miscounted record also surfaces in its exclusion table as `harness_kill_external
1` — a table whose other rows are whole-game exclusions, so the scene record is counted inside a
population it does not belong to. **No cost figure moves today** (verified): the record is
excluded before grouping by terminal_reason and its `cost_usd` is None, so the 7 qualifying
groups, the 42%–254% range and every `--ordering` p-value are unchanged. The exposure is forward:
every future scene record (the scene matrix is pending on the operator decision, task 145) enters
cost_census's whole-game count while census.py files it under SCENE — a whole-game population
that grows wrong by N, silently, under a comment asserting the two producers agree. This is
AGENTS.md rule 12's shape: a partition rule restated in two files, with a comment promising they
match instead of code asserting it.

WHAT NOT TO CONCLUDE: this is not a defect in census.py — its partition is the documented one
(eval/SCENES.md forbids pooling scene trials with game trials, and census.py refuses unknown
task_class values by name rather than guessing). cost_census is the file that drifted. Nor does
the 92 figure invalidate the cost result it fronts: verified above, no cost figure moves — the
claim being repaired is the population count and the exclusion table's scope, not any range,
ratio or p-value.

THE FIX IS A PROPERTY, NOT A MECHANISM: after the fix, changing the partition rule in one place
cannot leave the other producer behind — because there is one place. Suggested shape, agent's
judgment to improve: move `task_class_of` and `NOT_A_RUN` into `agent_harness.py` (the module
both tools already share), have both CLIs import them, delete the local literals, and have
cost_census classify with the shared function instead of field presence. The selftest pins are
the part that must outlive the fix: a both-fields fixture record in each tool's selftest, a
structural pin that no local `frozenset({"work"...})` literal survives outside the shared module,
and a mutant of either producer reverting to a local copy turning a pin red — the same
red/green discipline every other selftest in this repo carries. Decide and record whether
cost_census should REPORT scene records as their own labelled population (census.py does) or
count them as a labelled exclusion — either is defensible; letting them vanish from the report
is not.

## note 2026-08-30

2026-08-30. The two producers re-run over the main checkout's stored tree and they AGREE; the one-classifier repair is in place and pinned in both directions.

BROKEN STATE (before the fix):
    python3 eval/tools/census.py --runs-dir /Users/stefano/Documents/heavenstudio/game-research-claude/eval/runs
        -> WHOLE-GAME trial records 91 (the scene record counted in its own SCENE population)
    python3 eval/tools/cost_census.py --runs-dir <same path>
        -> whole-game trial records read 92
    The disputed record is runs/wg-scene-s1ts-2026-08-25/trials/s1_parallax__ts__t0.json:
    it carries `game` AND `task_class: scene`, so cost_census's field-presence spelling
    counted it whole-game while census.py's task_class spelling put it in scene — the
    same tree, two totals, neither reporting the disagreement.

AFTER THE FIX (one classifier, eval/agent_harness.py: task_class_of / population_of /
NOT_A_RUN / TaskClassError; census.py, cost_census.py and wallclock.py import it; manifest.py
and tier1_census.py import NOT_A_RUN):
    python3 eval/tools/census.py --runs-dir <same path>
        -> WHOLE-GAME trial records 91
    python3 eval/tools/cost_census.py --runs-dir <same path>
        -> whole-game trial records read 91
           records by population scene 1, spec-change 71, whole-game 91
    Date 2026-08-30. Nothing written under eval/runs/: `find <runs> -newer <marker>` returned
    empty around both runs.

DECISION (done_when 2): the scene population is reported under its OWN LABEL —
`records_by_population` in the JSON result and a "records by population" line in the
rendered report — a counted population, never a silent exclusion.

DONE_WHEN 3, BOTH DIRECTIONS:
- cost_census: permanent mutant `partition_by_field_presence` (the exact pre-fix spelling,
  re-implemented as a search-span replacement) added to eval/tools/cost_census_mutants.py ->
  4 named selftest failures; unmutated control green; full sweep 42/42 mutants caught.
- census: hand mutation re-introducing a local literal `WHOLEGAME_KEY = "game"` with a
  field-presence partition -> `census --selftest` FAILED with 19 named rows, including
  "no literal whole-game key is left in this file: got True, want False" and the scene tokval
  (40.0) inside the whole-game total (46.0); reverted, selftest ok (0 failures).
- wallclock: its `pool_populations` mutant re-spanned to force the shared classifier's
  verdict to a constant -> 18 named failures; wallclock_mutants sweep 13/13, control green.
- manifest_selftest and tier1_census --selftest pin `NOT_A_RUN is agent_harness.NOT_A_RUN`
  by IDENTITY and that no literal skip-list frozenset remains in their files.

Green after the fix: census --selftest, cost_census --selftest, wallclock --selftest,
manifest_selftest, tier1_census --selftest (29/29).

Also updated: eval/RUNS.md's wallclock section said wallclock "takes its ... population
partition from census.py"; the partition now lives in eval/agent_harness.py, which wallclock
imports directly, so the sentence names the shared module. No other live document pins the
old 92 as a whole-game figure — RUNS.md's "86 of its 92" uses the writing script's own output
as its denominator, which that section defines explicitly as "not a task class", and is
unaffected.

The producer defect this task repairs may deserve a finding number at merge (a mechanism
that ran, reported a count, and counted one record into the wrong population across every
run since scenes existed); allocation left to the orchestrator.

## review adjudication 2026-08-30 (orchestrator, PR 107 round 1)

CodeRabbit posted 4 actionable comments. Verified against code before judging; three
accepted, one declined:

1. **ACCEPT (major) — validate the task class on the spec-change path too.**
   Verified: `population_of({"task_class": "cutscene"})` returns `"spec-change"`, while
   `census.py` load_records calls `task_class_of(data)` over EVERY record (census.py:163)
   and refuses the tree on the same record. Two producers, two answers, one record — the
   exact defect this task exists to kill, surviving one level down. Fix:
   `population_of` calls `task_class_of(record)` before the spec-change return. Safe for
   the stored tree: census.py already refuses unknown classes tree-wide and reads all 163
   records today, so no stored record can newly raise. cost_census must convert the
   raised `TaskClassError` into a `CostCensusError` naming the file at its own load
   point, the way census.py does (its comprehension call site has no path to name; the
   early validation exists for that reason and stays). Add a pin: a fixture record with
   an unknown class and NO `game` field raises in BOTH producers.
2. **ACCEPT (minor) — unhashable task_class raises TypeError, not the named refusal.**
   Verified: `task_class_of({"task_class": []})` raises
   `TypeError: cannot use 'list' as a set element`; the loaders catch TaskClassError
   only. Check `isinstance(klass, str)` (or equivalent) and raise `TaskClassError` so the
   refusal stays named. Pin it.
3. **DECLINE — "replace the RUNS.md history with the current contract."** The sentence
   states the current choices and carries the provenance citation `(task 227)`;
   citation-bearing prose is this repository's convention in live documents (README,
   RUNS.md, DECISIONS.md all cite what produced a rule). Narrating WHAT WAS REPLACED is
   what the convention forbids; naming the producer of a rule is not that.
4. **ACCEPT (minor) — census.py's whole-game population label misstates the
   population.** The classifier puts `game`-bearing scene records in scene, but the
   output still prints "stored trial records carrying a \`game\` field" (census.py:260).
   Change to state: `task_class` absent or `game`. Pin the label against the fixture
   that classifies scene.

After fixing, re-run the done_when gates plus both producers over the stored tree; the
agreement numbers in the note above must still hold (91 / 91, scene 1, spec-change 71).

## note 2026-08-30

## review round 1 addressed (2026-08-30)

CodeRabbit posted 4 actionable comments; adjudicated per the orchestrator's section above.
Three accepted and fixed at the ONE classifier in eval/agent_harness.py, one declined as
adjudicated (the RUNS.md sentence states the current contract and carries the (task 227)
provenance citation; no change).

1. ACCEPTED — population_of now calls task_class_of(record) BEFORE the no-`game` return,
   so an unknown class on a spec-change record is refused by BOTH producers. cost_census's
   loader already wraps the raised TaskClassError in a CostCensusError naming the file,
   which is what its validation-through-population_of call site relies on; census.py's
   loader refuses through task_class_of directly. Verified broken first:
   population_of({"task": "x", "task_class": "cutscene"}) returned "spec-change" while
   census.py refused the same record.
2. ACCEPTED — task_class_of checks isinstance(klass, str) before membership, so an
   unhashable value (`task_class: []`) raises the NAMED TaskClassError the loaders wrap,
   not the TypeError nothing catches. Verified broken first: TypeError
   "cannot use 'list' as a set element".
4. ACCEPTED — census.py's wholegame.population label now reads "stored trial records whose
   `task_class` is `game` or absent" (was "carrying a `game` field", the field-presence
   spelling this task removes).

Pins added (red demonstrated by hand-reverting both fixes: census --selftest FAILED 2 named
rows, cost_census --selftest FAILED 2 named rows including "raised TypeError, not
CostCensusError"; restored, both ok):
- census selftest: population_of refuses a spec-change record's unknown class;
  task_class_of raises TaskClassError (not TypeError) on an unhashable class;
  Direction 8e: census() refuses a no-`game` + unknown-class tree, naming file and class;
  the wholegame population label is pinned to the class-based wording beside the
  both-fields fixture.
- cost_census selftest Direction 11c: a no-`game` + unknown-class record and an unhashable
  class both raise CostCensusError naming the file.

Still green after the fixes: census --selftest, cost_census --selftest,
cost_census_mutants (42/42 caught, control green), wallclock --selftest,
wallclock_mutants (13/13, control green), manifest_selftest, tier1_census --selftest (29/29).

Agreement re-run 2026-08-30 after the round-1 fixes, over the main checkout's eval/runs
(read-only; find -newer against a fresh marker returned empty):
    python3 eval/tools/census.py --runs-dir <main>/eval/runs
        -> WHOLE-GAME 91 (label: task_class is `game` or absent), SCENE 1, SPEC-CHANGE 71
    python3 eval/tools/cost_census.py --runs-dir <main>/eval/runs
        -> whole-game trial records read 91; records by population scene 1, spec-change 71,
           whole-game 91
The numbers in the note above still hold: 91 / 91, scene 1, spec-change 71.

## Established at merge

ESTABLISHED at merge 594841c, re-verified on main 2026-09-02: the two producers read the same stored tree and print the same whole-game count - census.py 'trial records 91', cost_census.py 'whole-game trial records read 91', both reporting 'scene 1, spec-change 71' - so the 92-vs-91 split is closed, and finding #213 is allocated at this merge (the only finding this task warrants: the drift and the pin-satisfied-by-wrong-cause lesson; the repair itself is task 227's deliverable, not a finding). Both-direction pins landed with the branch: cost_census_mutants partition_by_field_presence 42/42, control green; census hand-mutation 19 named failures; wallclock pool_populations 13/13; NOT_A_RUN identity pins in manifest and tier1_census. done_when clause 4's agreement record: commands run over the main checkout's eval/runs read-only, 2026-08-30 by the branch and re-run 2026-09-02 at merge, both print 91/91.
