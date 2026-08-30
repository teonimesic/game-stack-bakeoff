---
id: 227
title: cost_census.py and census.py partition the same tree by two rules that agreed when written — 91 vs 92 whole-game records today
status: todo
priority: 2
refs: 'eval/tools/cost_census.py, eval/tools/census.py, eval/SCENES.md, agent_harness.py, tasks/145, CLEANUP-LOG.md pass 34'
done_when: '1. ONE classifier decides whole-game/scene/spec-change, and ONE definition of NOT_A_RUN, exist in the repository and are imported by both eval/tools/census.py and eval/tools/cost_census.py — agent_harness.py is the natural home (cost_census.py:114 already imports TOKVAL_HARNESS from it). Neither CLI keeps a local literal copy: no `frozenset({"work", "artifacts", "targets"})` outside the shared module, and cost_census.py:120''s "Same test as census.py" comment replaced by the import it describes. 2. cost_census''s whole-game population is task_class-aware, and the scene record it miscounts today is not silently absent: the report states the scene population under a named label (or a counted exclusion), so a skip nobody counts is not the replacement defect. 3. Selftest pins on both sides: a fixture record carrying BOTH `game` and `task_class: scene` classifies as scene in the shared classifier and lands in NEITHER producer''s whole-game population; a mutant that reverts either producer to a local literal partition turns a pin red. 4. Both producers re-run over eval/runs/ (read-only) and AGREE: census.py''s WHOLE-GAME record count equals cost_census''s whole-game records-read count, with the commands, the date and both numbers recorded in this ticket. 5. Gates exit 0 at the branch head, unpiped: docstat.py --sweep, docstat.py --renumbered, tasks.py check, ci_minutes --selftest and --controls; nothing under eval/runs/ written.'
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
