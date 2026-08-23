---
id: 64
title: README's opening line states counts nobody re-derives, and the cost figure in it was 34% low
status: in_flight
priority: 4
refs: 'README.md:8, eval/RUNS.md:31, eval/findings/limits-and-cost.md #119'
done_when: 'Each count in README.md''s opening sentence is either reproduced from stored artifacts by a named command, or removed. State the population for each: 24 whole-game submissions and three games were both true once, and the stored tree now holds 137 trial records across 19 run directories and four games. If a count cannot be reproduced without choosing a population, say which population and why - an aggregate without its scope is unfalsifiable (#113).'
---

The cost figure in that sentence was corrected on 2026-08-23 from ~1,794 to 2,710.94, measured over every runs/*/trials/*.json plus every stored judge round. The correction exposed the shape rather than fixing it: the same sentence still asserts 24 whole-game submissions and three games, and no command in this repository produces either number. The cost half went stale because three runs worth 698.21 landed after it was written and nothing re-read it; the other halves have the same exposure and no producer at all. eval/RUNS.md's own headline went stale twice over for the same reason and now carries the date it was read and the command that reproduces it, which is the pattern to copy. Do not guess the counts - derive them or delete them.
