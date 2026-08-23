---
id: 65
title: Tier 2 is now the only scored tier and it is at its ceiling on 24 of 56 matrix trials
status: in_flight
priority: 4
refs: 'eval/judge/RUBRIC.md, eval/judge/tier1_census.py, DECISIONS.md open item, FINDINGS #92 #123'
done_when: eval/judge/tier1_census.py --runs-root <main checkout>/eval/runs shows at least one (run, game) group whose tier-2 values are not a single value, on a run where it currently is - OR a written decision in DECISIONS.md that the saturation is acceptable and why, naming what it costs. A new or strengthened play-bot criterion needs both halves of judge/bot_mutants.py before it counts.
---

Task 29 made tier 1 a gate, so overall = tier2 and the play-bot tier now carries the entire deterministic grade. It is itself at the ceiling on 24 of 56 matrix trials: overall is a constant 1.000 across all 16 wg-audio48 trials and all 8 of wg-g4c. Before the change a tier-1 lint nit or two per field produced a spread, which looked like discrimination and was not (FINDINGS #123) - the saturation is not new, it is now undisguised. An instrument whose only scored tier returns one value for a whole run cannot rank anything in it, and no weight can fix that. The remedy is harder play-bot criteria or harder tasks. Note the two criteria already measured and deliberately NOT scored, layer.clears and stage.completes, are the obvious candidates and both were withheld because the bot cannot satisfy them on correct work - promoting either needs the instrument to improve first, not the rubric.

## What was measured while doing this — do not re-derive it

`judge/tier2_census.py --runs-root <main>/eval/runs` now answers the whole first half of this
ticket mechanically. Three things it took a day to establish and which the tool now prints:

1. **5 of 10 groups are flat, not 2.** The ticket said "24 of 56 matrix trials"; over the full
   68-trial corpus it is `wg-audio` g1/g2, `wg-audio48` g1/g2 and `wg-g4c` g4 — 35 of 68.
2. **Every selective tier-2 failure in the corpus is from `wg-matrix-2026-08-13`** — 9 of 11;
   the other 2 are whole-trial (#49). Tier 2 has not separated two submissions in four later runs.
3. **The two obvious repairs are dead, measured, not argued.** Promoting a withheld diagnostic
   moves every score in its group by the same amount (single-valued `False` on all 7 pairs).
   Four criteria built from requirements the g4 prompt states and no criterion checks — no
   re-trigger mid-swing, enemies patrol, the `land` event fires, replay determinism under a
   played 900-tick tape — passed **8/8** driven against the `wg-g4c` work trees, which are the
   only ones that survive.

**A near-miss worth knowing about before anyone re-runs it.** Held every tick for 240 ticks,
`g4_platformer__unity__t0` keeps `attack.active` true for all 240 with its frame counter
restarting 13 times, while the other seven show 12-14 swings of 5-6 ticks. That looks like a
clean 1-of-8 failure of "attacking again before the swing finishes does nothing". Driven with one
press to start the swing and one at its midpoint, it is identical to its own clean swing. It
chains swings with no idle tick, which is what "a control held across consecutive ticks takes
effect on every one of those ticks" asks for. #89's shape, one measurement from being scored.

Follow-ons filed: **74** (price a harder task — the only route left) and **76** (the play-bot
cannot cross a gap, which is what makes `stage.completes` unpromotable and costs six g4 criteria
their measurability on a correct level).
