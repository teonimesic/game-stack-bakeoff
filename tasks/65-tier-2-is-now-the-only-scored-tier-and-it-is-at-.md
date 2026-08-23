---
id: 65
title: Tier 2 is now the only scored tier and it is at its ceiling on 24 of 56 matrix trials
status: open
priority: 4
refs: 'eval/judge/RUBRIC.md, eval/judge/tier1_census.py, DECISIONS.md open item, FINDINGS #92 #119'
done_when: eval/judge/tier1_census.py --runs-root <main checkout>/eval/runs shows at least one (run, game) group whose tier-2 values are not a single value, on a run where it currently is - OR a written decision in DECISIONS.md that the saturation is acceptable and why, naming what it costs. A new or strengthened play-bot criterion needs both halves of judge/bot_mutants.py before it counts.
---

Task 29 made tier 1 a gate, so overall = tier2 and the play-bot tier now carries the entire deterministic grade. It is itself at the ceiling on 24 of 56 matrix trials: overall is a constant 1.000 across all 16 wg-audio48 trials and all 8 of wg-g4c. Before the change a tier-1 lint nit or two per field produced a spread, which looked like discrimination and was not (FINDINGS #119) - the saturation is not new, it is now undisguised. An instrument whose only scored tier returns one value for a whole run cannot rank anything in it, and no weight can fix that. The remedy is harder play-bot criteria or harder tasks. Note the two criteria already measured and deliberately NOT scored, layer.clears and stage.completes, are the obvious candidates and both were withheld because the bot cannot satisfy them on correct work - promoting either needs the instrument to improve first, not the rubric.
