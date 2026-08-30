---
id: 220
title: 'ADOPTED-CANDIDATE from task 219: trial failure-cause labels with a producer, from the sibling failure taxonomy'
status: done
priority: 3
refs: research/12-sibling-comparison.md, ~/Documents/heavenstudio/game-research-gpt/research/raw/evaluation-methodology.md, eval/FINDINGS.md, eval/tools/census.py, eval/tools/disclosure.py
done_when: 'A closed label vocabulary for trial failure cause exists in the repo; every stored whole-game trial carries one label applied by hand in one session, population taken from tools/census.py, the retired suite excluded or named; a producer cross-tabs labels by run and by stack; and the accept-or-reject measurement is written into the ticket: ACCEPT when some label group surfaces a cross-run or cross-stack pattern not already recorded in FINDINGS or DECISIONS - a rule-9 shared-cause cluster, or a published figure the labels qualify; REJECT and withdraw the vocabulary when every group maps one-to-one onto an already-recorded finding or a terminal_reason partition, which would mean the labels add no dimension. Either outcome closes the task.'
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/100
established_by: 'PR #100 squash-merged at 83e69a8; measurement REJECT with the vocabulary withdrawn and the re-open condition in DECISIONS.md; verified in orchestrator checkout; findings: none'
---

Task 219, research/12-sibling-comparison.md, marks the sibling failure taxonomy and its infrastructure-versus-agent failure separation as the one ADOPTED-CANDIDATE from the systematic comparison with game-research-gpt. This repo answers why trials failed ad hoc each time: FINDINGS #45 TMPDIR deletion, #46 a bot that stood still, #49 a daemon gating execve, #37 stalled versus compiling - each found by hand, each invisible to terminal_reason, which partitions how a session ended and not whose fault the outcome was. The sibling applies stable labels per output (setup/version, oracle-weakened, claim-not-reproduced and 13 more, research/raw/evaluation-methodology.md) and aggregates them in its final tables.

## note 2026-08-30

## Measurement: trial failure-cause labels — REJECT, vocabulary withdrawn (2026-08-30)

### Population (producer: `python3 eval/tools/census.py`, read 2026-08-30)

Whole-game population: **91 trial records over 12 run directories** (stacks godot 20 / rust 25 /
ts 26 / unity 20; terminal_reason absent 4, api_error 9, budget_exhausted 1, completed 76,
max_turns 1). Excluded and named, not labelled: the retired spec-change suite's **71 records
over 12 run directories** (records with no `game` field, #122) and **1 scene record**.

### The vocabulary — 9 closed labels with a precedence

Terminal-determining causes first: account-limit > machine-wedge > turn-ceiling > budget-cap.
Then outcome-qualifying: machine-degraded, grading-artifact-loss, starter-defect. Then
agent-work. not-a-submission for a trial that never ran the task.

1. **agent-work** — completed and externally unqualified; the outcome is attributable to the agent's work
2. **starter-defect** — the submission discloses a defect that arrived in the starter it was given (disclosure family 2; #98, tasks/81)
3. **account-limit** — the session ended on the account's capacity (session limit, weekly quota); `eval/runs/wg-cal48-2026-08-14T14-30-58/NOTES.md` and `eval/RUNS.md` distinguish these from genuine API errors
4. **machine-wedge** — the record carries no terminal reason; the process died with the machine (the arena2d wedges, recorded as an unresolved observation by design)
5. **machine-degraded** — ran on the degraded side of a recorded machine event (#49)
6. **turn-ceiling** — ended on max_turns (#35)
7. **budget-cap** — ended on budget_exhausted (#33)
8. **grading-artifact-loss** — the submission's artifacts were destroyed between build and grade (#45)
9. **not-a-submission** — a harness probe, never a game population

### The labelling — applied by hand in one session (2026-08-30)

agent-work 53 | starter-defect 18 | account-limit 9 | machine-wedge 4 | machine-degraded 4 |
turn-ceiling 1 | budget-cap 1 | grading-artifact-loss 0 | not-a-submission 1

Per-trial identities of every non-agent-work label:

- **starter-defect 18** — rust 12 (tasks/81's list): wg-matrix g1_pong rust t0/t1,
  g2_tetris3d rust t0/t1, g3_arena rust t0/t1; wg-audio g1_pong rust t0/t1; wg-audio48
  g1_pong rust t0 and g2_tetris3d rust t1; archive-arena2d-wg-audio48 g3_arena rust t0;
  wg-g4 g4_platformer rust t1. godot 5: wg-g4c g4_platformer godot t0/t1 (#98);
  wg-arena3d-2026-08-15T12-46-30 g3_arena godot t0 (capture_frame); wg-audio48 g2_tetris3d
  godot t1 (latch-and-clear); wg-matrix g1_pong godot t1 (user:// warning) — the last three
  are the disclosure hand pass's named misses (tasks/94 widened the cue set, not the hand
  count). unity 1: wg-audio g1_pong unity t0. Same 18 identities the disclosure hand pass
  classified (`eval/tools/disclosure.py` docstring; per-stack godot 5 / rust 12 / ts 0 /
  unity 1).
- **account-limit 9** — wg-g4b all 8 (weekly quota: the 6 one-turn trials never got a turn,
  the 2 rust trials ran ~53 min first); wg-cal48 g1_pong ts t0 (session limit, 40 turns in).
- **machine-wedge 4** — archive-arena2d-wg-audio48 g3_arena godot t0/t1 and unity t0/t1
  (terminal reason absent).
- **machine-degraded 4** — wg-arena3d-2026-08-15T12-46-30 rust t0/t1 and ts t0/t1 (15 Aug,
  the syspolicyd-pegged machine; #49's exact split).
- **turn-ceiling 1** — archive-arena2d-wg-audio48 g3_arena rust t1 (251 turns).
- **budget-cap 1** — wg-audio g1_pong godot t1.
- **grading-artifact-loss 0** — #45's six TS cases are the retired suite's; zero whole-game
  applications.
- **not-a-submission 1** — wg-harness-probe-primeagent-2026-08-24 g1_pong rust t0 (2 turns;
  `eval/RUNS.md` bars this record from every game population).

### Cross-tab by terminal_reason (exact, verified against the records)

api_error 9 -> account-limit 9 (0 of 9 a genuine API error); absent 4 -> machine-wedge 4;
max_turns 1 -> turn-ceiling 1; budget_exhausted 1 -> budget-cap 1; completed 76 -> agent-work
53 + starter-defect 18 + machine-degraded 4 + not-a-submission 1.

### Cross-tab by run

| run | n | agent | starter | account | wedge | degraded | ceiling | budget | probe |
|---|---|---|---|---|---|---|---|---|---|
| archive-arena2d-wg-audio48 | 8 | 2 | 1 | 0 | 4 | 0 | 1 | 0 | 0 |
| wg-arena3d-2026-08-15T12-46-30 | 8 | 3 | 1 | 0 | 0 | 4 | 0 | 0 | 0 |
| wg-audio-2026-08-14T12-29-42 | 11 | 7 | 3 | 0 | 0 | 0 | 0 | 1 | 0 |
| wg-audio48-2026-08-14T19-55-47 | 16 | 13 | 3 | 0 | 0 | 0 | 0 | 0 | 0 |
| wg-cal48-2026-08-14T14-30-58 | 1 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 0 |
| wg-cal48b-2026-08-14T18-53-25 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| wg-calib-2026-08-12T12-18-14 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| wg-g4-2026-08-17T09-38-32 | 4 | 3 | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| wg-g4b-2026-08-17T19-50-43 | 8 | 0 | 0 | 8 | 0 | 0 | 0 | 0 | 0 |
| wg-g4c-2026-08-21T02-26-46 | 8 | 6 | 2 | 0 | 0 | 0 | 0 | 0 | 0 |
| wg-harness-probe-primeagent-2026-08-24 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |
| wg-matrix-2026-08-13T14-02-50 | 24 | 17 | 7 | 0 | 0 | 0 | 0 | 0 | 0 |
| **total** | **91** | **53** | **18** | **9** | **4** | **4** | **1** | **1** | **1** |

### Cross-tab by stack

| stack | trials | agent-work | externally qualified (of which) |
|---|---|---|---|
| ts | 26 | 21 | 5 — 2 machine-degraded, 3 account-limit |
| unity | 20 | 15 | 5 — 2 machine-wedge, 2 account-limit, 1 starter-defect |
| godot | 20 | 10 | 10 — 5 starter-defect, 2 machine-wedge, 2 account-limit, 1 budget-cap |
| rust | 25 | 7 | 18 — 12 starter-defect, 2 account-limit, 2 machine-degraded, 1 turn-ceiling, 1 not-a-submission |

### VERDICT: REJECT — every group maps one-to-one onto recorded material

| label | maps onto |
|---|---|
| agent-work 53 | the default, not a finding |
| starter-defect 18 | the disclosure hand pass in the `eval/tools/disclosure.py` docstring — same 18 identities, per-stack counts already published — plus #98 and tasks/81 |
| account-limit 9 | the api_error partition, split by the cal48 NOTES session-limit note and the RUNS.md wg-g4b section |
| machine-wedge 4 | the absent-terminal_reason partition + the RUNS.md arena2d sections (unresolved by design) |
| machine-degraded 4 | #49 + the RUNS.md arena3d two-populations banner |
| turn-ceiling 1 | max_turns + #35 |
| budget-cap 1 | budget_exhausted + #33 |
| grading-artifact-loss 0 | #45 — its population was the retired suite; 0 whole-game applications (recorded as the reason the group is empty) |
| not-a-submission 1 | the RUNS.md harness-probe section |

Two ACCEPT candidates were examined and neither survives decomposition:

1. **Infrastructure damage concentrates on the arena runs** (all 4 wedges + the 1 ceiling in
   archive-arena2d; all 8 wg-g4b account-limit trials). Rejected: the wedges are recorded as an
   unresolved observation on purpose (#37's lesson — record the observation, not a diagnosis);
   a concentration finding would manufacture a diagnosis from causes the repository deliberately
   records without one.
2. **Rust carries 18 externally qualified trials of 25**, far above the other stacks. Rejected:
   it pools five mechanisms (starter defects, account limits, a turn ceiling, the harness probe,
   the degraded machine) that share nothing but the stack column — the heterogeneous-mean shape
   rule 4 bans — and decomposed, every mechanism is already measured and published with
   per-trial identities.

### Withdrawal

Per this ticket's own clause, the vocabulary is withdrawn and nothing ships: no label register,
no cross-tab producer, nothing to maintain. The distinctions the labels made are already
carried by `terminal_reason` (how the session ended), the two disclosure families (what the
agent said about its own work; what arrived broken), the comparability register in
`eval/RUNS.md` (what changed in the world mid-run) and #49's banner (the machine split). A
hand-maintained register has no producer, so its counts would go stale forever. **Re-open when
a trial ends in a way no existing partition expresses**; the repair is then to extend
`terminal_reason`'s closed set at the runner — which has both a writer and a reader — never to
revive a hand label.

Recorded in `DECISIONS.md` ("Trial failure-cause labels: measured and rejected — decided
2026-08-30") on branch task-220-failure-taxonomy-rejected; `research/12-sibling-comparison.md`'s
ADOPTED-CANDIDATE section is updated to the measured outcome on the same branch.

## note 2026-08-30

PR #100 squash-merged at 83e69a8. The ticket's own accept-or-reject measurement was run
and came out REJECT: a closed 9-label vocabulary applied by hand in one session
(2026-08-30) to all 91 stored whole-game records (population from census.py, retired
suite's 71 + 1 scene excluded and named) - agent-work 53 / starter-defect 18 /
account-limit 9 / machine-wedge 4 / machine-degraded 4 / turn-ceiling 1 / budget-cap 1 /
grading-artifact-loss 0 / not-a-submission 1. Cross-tab against terminal_reason exact
with no remainder; every group maps one-to-one onto recorded material (disclosure hand
pass, #49's banner, cal48 + wg-g4b account limits, RUNS.md sections); both ACCEPT
candidates dissolved under decomposition. Vocabulary withdrawn, nothing ships - re-open
when a trial ends with a cause no existing partition represents, repaired by extending
terminal_reason's closed set at the runner. DECISIONS.md entry + reversal-conditions row
landed; research/12 census updated to 20/9/7. Verified in orchestrator checkout at
4819954: population re-derived from census.py byte-identical, arithmetic exact, sources
spot-checked, 5 gates unpiped green (sweep/withdrawn/renumbered/check/linkcheck), 10
threads 0 unresolved, CI green. Findings: none - the negative result is the ticket's
rejection clause, recorded as a DECISIONS entry with a falsifiable re-open condition.
