---
id: 230
title: 'census.py reads d["stack"] bare: a whole-game record without one dies in a comprehension naming no file'
status: done
priority: 3
refs: 'eval/tools/census.py:269,275,276,305,326; eval/agent_harness.py population_of (PR #107 tree); LANDS AFTER #107 MERGES — same file, in-flight'
done_when: 'A fixture record classified whole-game carrying `game` and no `stack` (and a scene variant: `task_class`: scene, no `stack`) makes census.py exit 2 with a CensusError naming the record''s file; same for cost_census.py if the check lands in shared code; pinned in both directions in the module''s selftest (red: the crash shape refuses by name; green: every existing fixture still counts) and any control runner that covers it updated; gates unpiped exit 0'
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/113
established_by: 'Merged as f686d78 (squash of PR #113, operator-approved on a documented basis: CodeRabbit clean on first head 94664ce, gates+controls green at 86c5243 and re-run green at 03a1313 after branch update, empty diff on the three reviewed files between review head and merge head, both selftests re-run independently in the PR worktree). Verified on main after pull: census.py --selftest ok 0 failures, cost_census.py --selftest ok 0 failures; refusal lives in load_records via shared agent_harness.stack_of/StackError/STACK_KEY, cost_census._validate_wholegame delegates, population_of deliberately pure. Stored tree unaffected: 163 records over 25 dirs counted clean before and after (at PR time).'
---

Reproduced 2026-09-01, main tree: a record carrying `game` but no `stack` makes `python3 eval/tools/census.py --runs-dir <fixture>` die with a bare `KeyError: 'stack'` at census.py:269, exit 1, no path named. This is the exact shape the module refuses three times over elsewhere — a non-object record (line 190), a null `agent` block (line 200) and an unknown `task_class` (line 206) all fail BY NAME, each with a comment saying an error several frames away naming no file is loud and useless. The partition reads `d["stack"]` bare in five places (lines 269, 275, 276, 305, 326) over records guaranteed only `game`; a scene record without `stack` hits the same crash via lines 326-327. NOT closed by PR #107: reproduced against /tmp/p107-verify at its census.py:229 — `population_of` in eval/agent_harness.py validates the class on every record but no key presence. cost_census.py shares the classifier after #107, so the fix belongs where both producers read it (agent_harness, raised by the loaders which already wrap classifier errors naming the file) or in each loader — decide from the file's own conventions. Fixture left at /tmp/p41-fixture/runs (one record: game, no stack); rebuild rather than trust it to persist. The stored tree does not currently hold such a record — this is the fail-loudly-by-name standard the file already holds itself to, applied to the one key it missed.

## note 2026-09-02

Landed as PR #113 (branch task-230-census-stack-refusal, head 94664ce).

**What was measured on the pre-fix tree (2026-09-02, 9f95538), so nobody re-derives it.**
The defect was census.py's ALONE. Whole-game fixture (game, no stack): bare `KeyError:
'stack'` at census.py:229, exit 1, no path. Scene variant: same KeyError at the scene
stacks counter, exit 1, no path. cost_census.py on the same two fixtures: whole-game
already refused by name (exit 2, `_validate_wholegame`, file + field); scene exits 0
correctly — that tool never reads a scene stack, and its docstring says a record that is
not its own is counted under its population label, not refused. The stored tree holds no
such record (163 records / 25 run dirs counted clean before and after, byte-identical
output), so no published figure was ever wrong.

**Where the check landed, and the decision behind it.** In census.py's `load_records` —
the file's own convention, three refusals earlier in the same function (non-object, null
`agent`, unknown class): anything the partition reads inside a comprehension over every
record fails at load, where the path exists. The predicate is defined once as
`agent_harness.stack_of` + `StackError` + `STACK_KEY` (task 227's pattern: one
definition, imported, pinned by IDENTITY in both selftests); cost_census's stack branch
delegates to it, so "usable stack" has one spelling, and the message still names the
field its selftest requires. `population_of` was deliberately NOT made to raise on a
missing stack: it answers "which population", and making classification refuse
stack-carrying questions would break it for consumers that never read a stack. The
loaders call it first, then `stack_of` only for whole-game/scene.

**Adjacent shape deliberately left alone (candidate follow-up).** A whole-game record
with an unusable `game` value: cost_census refuses it ("no usable `game`"), but
census.py would GROUP a null `game` (hashable, prints as a game named `None`) and
CRASH on a list (`TypeError: unhashable type` in the same cells counter). Same
field-family, same comprehensions, not claimed by this ticket. If filed, the natural
home is the same shared module beside `stack_of`.

**Checked, not an instance:** `judge/discrimination.py` reads `stack` from the trial-id
FILENAME, not from the record — it cannot hit this shape.

**No finding number needed:** the defect was ticketed before it was fixed and never
produced a wrong number; nothing new was measured that `eval/FINDINGS.md` should hold.
