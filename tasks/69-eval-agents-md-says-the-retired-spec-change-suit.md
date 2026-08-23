---
id: 69
title: eval/AGENTS.md says the retired spec-change suite has 71 stored trials; the tree holds 47 trial JSONs
status: done
priority: 3
refs: ''
done_when: State what population gives 71 and what gives 47, with the command for each, or correct whichever is wrong in every live doc that states it. If 71 is unreproducible from the stored tree, say so and say what evidence would have been needed - a count that cannot be reproduced is the defect task 64 existed to remove, not a smaller version of it.
established_by: '71 and 47 are the same population read at two depths, and 71 is right. eval/runs/archive-run1-byte-identical-prompts/ is a WRAPPER holding four run directories, each with its own trials/, one level deeper than every other run. census.py globbed */trials/*.json - exactly one level - so 24 records were dropped silently. find eval/runs -path ''*/trials/*.json'' | wc -l gives 161; census.py gave 137. After the fix census.py gives spec-change 71 over 12 run directories at $153.82, tree 161 over 23 at $2,466.31; whole-game is unchanged at 90 over 11 and $2,312.49 because no whole-game run is nested. The post-fix 71/12 reproduces DECISIONS.md''s independently-written ''71 trials in 12 run directories'' exactly. CONTROL BOTH WAYS: census.py --selftest 0 failures with a fixture that now contains a run nested in an archive wrapper and an agent-authored work/*/trials/ plant, answers stated before measuring; restoring the one-level glob turns it into 9 failures exit 1, naming the nested run, the relative-path run identifier and the unreported skip. WHY IT SURVIVED: task 64 cross-checked census.py against eval/RUNS.md and logged the agreement as evidence, but RUNS.md''s source column names the same one-level glob run by hand - two readings of one blind spot, agreeing to the digit. CHANGED: census.py searches at any depth, identifies a run by path relative to runs/, and prints how many trials/*.json it skipped as agent-authored, currently 0. README.md, eval/RUNS.md and eval/AGENTS.md corrected; RUNS.md''s $91.73 was correct for the population its own sentence named but the sentence called it ''the remaining'', so it now states $153.82 = $91.72 flat + $62.09 archived. 137/$2,404.21 registered as WR-tree-census-one-level; docstat.py --withdrawn exits 0 with the id present and exits 1 naming README.md:37-45 with it removed. Published as FINDINGS #126, NOT #125, and renumbered to #127 by a later merge - tasks 74 and 76 already cited #125 and main has since published its own #125. FILED task 75: manifest.py audit has the same one-level shape and examines 19 run directories, auditing none of the four archived runs, verified by 0 lines of its output naming archive-run1; judge/tier1_census.py globs */artifacts/*/eval/report.json. Gates unpiped: docstat.py --sweep 0, --withdrawn 0, withdrawn_control.py 33/33, tasks_control.py 0, census.py --selftest 0. Branch task-69-census-glob-depth, commit 943daaf, rebased onto main.'
---

census.py partitions runs/*/trials/*.json into 90 whole-game records (a game field) and 47 without one. eval/AGENTS.md, DECISIONS.md and eval/RUNS.md all say 71 for that suite, in three places that describe it as the sole surviving record of what those trials were asked to do. Either 71 counts something other than trials/*.json - arms, tasks, a run that was pruned - or one of the two numbers is wrong. Nobody has established which, and 71 is quoted as a reason to keep files.

## RESOLVED — 71 was right, 47 was the instrument (2026-08-23)

**Both numbers describe the same population. They differ by how deep the search went.**

| command | answer |
|---|---|
| `find eval/runs -path '*/trials/*.json' \| wc -l` | **161** trial records |
| `python3 eval/tools/census.py` **before the fix** | 137 records; spec-change **47** over 8 run dirs |
| `python3 eval/tools/census.py` **after the fix** | 161 records; spec-change **71** over 12 run dirs, $153.82 |

`eval/runs/archive-run1-byte-identical-prompts/` **is not a run directory — it is a wrapper
holding four of them**, each with its own `trials/`, one level deeper than every other run in the
tree. `census.py` globbed `*/trials/*.json`, exactly one level, so all 24 of their records were
dropped silently. They are all spec-change, which is why the whole-game half of the census (90
over 11) never moved and only the spec-change and tree rows were ever wrong.

**Do not re-derive these:**

- The four nested runs are `bakeoff-godot-2026-08-11T12-56-42`, `bakeoff-rust-2026-08-11T10-06-27`, `bakeoff-ts-2026-08-11T10-57-18`, `bakeoff-unity-2026-08-11T11-46-57` — 6 records each, $62.09 total. The eight top-level `bakeoff-*` / `core-*` directories hold the other 47, $91.72.
- **`archive-arena2d-wg-audio48/` is NOT nested** — it sits directly under `runs/` with its 8 whole-game records, so "archive" in a directory name does not predict the shape. Nothing else in the tree is nested: `find eval/runs -type d -name trials` returns 23, 19 at depth 1 and 4 at depth 2.
- `eval/RUNS.md`'s `$91.73` was **not** a fourth wrong number in a different way. It is $91.7227 rounded, and correct for the population its own sentence named (`bakeoff-*`, `core-*`) — but the sentence called it *"the remaining"*, i.e. tree minus whole-game, which it is not. Task 64 item 4 read the 1-cent gap as the defect; the real defect was the missing $62.09.

**Why this was not caught for a day.** Task 64 cross-checked `census.py` against `eval/RUNS.md`
and recorded the agreement as evidence. `eval/RUNS.md`'s source column read
`agent.cost_usd in every runs/*/trials/*.json` — **the same one-level glob, run by hand.** Two
readings of one blind spot agree to the digit. What disagreed was `DECISIONS.md`, `eval/AGENTS.md`
and #122, all saying 71 over 12, all reached by someone who counted the archive instead of
globbing past it. This ticket read that disagreement as *the docs are probably wrong*, because the
docs had no producer and the tool did. Published as **#126**, renumbered to **#127** by a later merge.

**Filed:** task 75 — `manifest.py audit` and `judge/tier1_census.py` have the same one-level shape.
`manifest.py audit` examines 19 run directories and audits none of the four archived runs
(verified: 0 lines of its output name `archive-run1`). Neither publishes a count, so neither was
repaired here.

**Note for whoever merges:** the finding was allocated **#126, not #125** (it is **#127** today) — tasks 74 and 76 on
`main` already cite `#125` for an unmerged tier-2-saturation finding, so #125 is left as a gap.
`docstat.py --sweep` is clean with the gap present.
