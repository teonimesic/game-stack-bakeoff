---
id: 64
title: README's opening line states counts nobody re-derives, and the cost figure in it was 34% low
status: open
priority: 4
refs: 'README.md:8, eval/RUNS.md:31, eval/findings/limits-and-cost.md #119'
done_when: 'Each count in README.md''s opening sentence is either reproduced from stored artifacts by a named command, or removed. State the population for each: 24 whole-game submissions and three games were both true once, and the stored tree now holds 137 trial records across 19 run directories and four games. If a count cannot be reproduced without choosing a population, say which population and why - an aggregate without its scope is unfalsifiable (#113).'
---

The cost figure in that sentence was corrected on 2026-08-23 from ~1,794 to 2,710.94, measured over every runs/*/trials/*.json plus every stored judge round. The correction exposed the shape rather than fixing it: the same sentence still asserts 24 whole-game submissions and three games, and no command in this repository produces either number. The cost half went stale because three runs worth 698.21 landed after it was written and nothing re-read it; the other halves have the same exposure and no producer at all. eval/RUNS.md's own headline went stale twice over for the same reason and now carries the date it was read and the command that reproduces it, which is the pattern to copy. Do not guess the counts - derive them or delete them.

## What the work established, 2026-08-23 - do not re-derive

The producer is `eval/tools/census.py`. Four things it encodes that cost time to find:

1. **`runs/*/trials/*.json` holds TWO populations and the glob does not separate them.** 90
   records carry a `game` field (whole-game, `wholegame.py`); 47 do not (the retired `runner.py`
   spec-change suite). 90+47=137, which is the figure `eval/RUNS.md` quotes, and it is a sum
   across two instruments - correct as a tree total, wrong as a submission count.
2. **`eval/AGENTS.md` says the retired suite has "71 stored trials". The tree holds 47 trial
   JSONs with no `game` field.** Not investigated here and not touched - it may count something
   other than `trials/*.json`. Filed as its own task; establish it before quoting either number.
3. **Known-answer control for the extraction (AGENTS.md rule 12).** `eval/findings/one-arm-bias.md`
   line 1804 states, independently and before this tool existed, "20 stored Godot whole-game
   submissions exist across seven runs". `census.py` returns godot 20 over exactly those 7 run
   directories. That is the single row whose true value was stateable in advance.
4. **`eval/RUNS.md` line 60 says the non-`wg-*` runs are $91.73; the records sum to $91.7227.**
   One cent, from subtracting per-run figures already rounded to the cent rather than summing
   records. Same class as the $118.62/$118.63 note that file already carries. Left as found -
   a figure quietly adjusted to match another figure is no longer a reading.

`agent.terminal_reason` is **absent** on 4 records (`archive-arena2d`, pre-dating the field).
Reported as its own bucket, never folded into `completed` or into a failure.
