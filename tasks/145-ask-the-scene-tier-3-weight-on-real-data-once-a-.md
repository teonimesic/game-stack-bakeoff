---
id: 145
title: Ask the scene tier-3 weight on real data, once a scene matrix exists
status: todo
priority: 3
refs: 'eval/SCENES.md, eval/judge/RUBRIC.md, eval/judge/weight_sensitivity.py, eval/judge/aspects.py, tasks/135, #92, #123'
done_when: 'A scene matrix has been run and graded, and the scene tier-3 weight has been swept over the OPEN interval with a tool that actually varies it - which means weight_sensitivity.py gains a w3 mode with its own constructed-crossover control, or a sibling does. The result is recorded in RUBRIC.md and eval/RUNS.md whichever way it comes out. If the sweep says the weight cannot act, do NOT tune it: read #92 and go and measure what the scene tier 3 has ever separated, the way tier1_census.py did for tier 1.'
---

Task 135 shipped the three scene aspects at weight 0.00 and could not ask whether that weight should ever move. Two reasons, first measured 2026-08-24 and RE-STATED 2026-09-01 after cleanup pass 52 corrected the figures (they had gone stale in this ticket, RUBRIC.md and SCENES.md alike): weight_sensitivity.py today finds 11 groups - 10 game groups and, since 2026-08-25, 1 scene group (wg-scene-s1ts s1_parallax, n=1, tier-1 and tier-2 gradings only); what is empty is scene TIER-3 rounds specifically - 0 of the judge ledger's 97 stored rounds - because no scene FIELD has ever been packed, so a w3 sweep would have no scene rounds to vary; and the parameter the tool sweeps is w1 over (tier 1, tier 2), while the scene question is w3 over (tier 2, tier 3), which it does not sweep. The answer today is NOT ASKED, which is not the same claim as no effect, and eval/SCENES.md names this as the reason to build scenes at all. eval/judge/RUBRIC.md's NOT ASKED block holds the current counts and the producer commands.
