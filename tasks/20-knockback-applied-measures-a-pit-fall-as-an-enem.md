---
established_by: REPAIRED and pinned. knockback.applied sampled the FIRST player_hit, which on a level with pits is a pit fall. g4_platformer__unity__t0 (wg-g4c-2026-08-21) implements knockback correctly - Sim.cs applies Velocity=(knockDirX*KNOCKBACK_X, KNOCKBACK_Y) for an enemy hit and deliberately takes the other branch for a pit, with the author's reasoning in the source: 'a pit instead puts the character back on the last wide platform it stood on, because falling forever is not a punishment, it is an ending.' The criterion read that respawn and reported absent knockback. FIX: the sample is taken only from a demonstrable enemy hit - an enemy within 40 units at the moment of the hit AND no position jump (a respawn moves ~85 units in one tick against ~3 for walking). A session with no enemy hit now reports scored=False NOT MEASURED rather than False, because absence of an observation is not evidence of an absent feature. VERIFIED: unity__t0 -> NOT MEASURED (none of its 5 player_hit events came from an enemy in contact); ts__t0 -> passes, first enemy hit vx 170.0 -> -240.0. PINNED both ways: mutant 'no impulse when hurt' still reddens it; full suite green at 36 criteria both directions, 4 variants, 3 session-lock controls, 0 unmet. MOVED: unity__t0 0.966 -> 1.000, field now 6 of 8 at exactly 1.000 with tier 2 at 1.00 in ALL EIGHT cells. FINDINGS #89.
id: 20
title: knockback.applied measures a pit fall as an enemy hit
status: done
priority: 2
refs: eval/FINDINGS.md #82, eval/judge/bot_platformer.py
done_when: knockback.applied establishes that the hit it measures came from an enemy, demonstrated by g4_platformer__unity__t0 passing it or by the criterion being shown to fail for a reason in that submission's code
---

Tier 2's play-bot scores knockback.applied by taking the FIRST player_hit event and checking the player's velocity moved away from the enemy it was approaching.

THE DEFECT: it assumes the first hit came from that enemy. On a level with pits it often does not.

ADJUDICATED TO SOURCE on g4_platformer__unity__t0 (wg-g4c-2026-08-21). Its Sim.cs has two damage paths. An enemy hit applies Velocity = (knockDirX * KNOCKBACK_X, KNOCKBACK_Y) - real knockback, correctly implemented. A PIT hit takes the other branch on purpose, with the reasoning written in the source: 'a pit instead puts the character back on the last wide platform it stood on, because falling forever is not a punishment, it is an ending'. It sets Position = Safe and Velocity = Zero.

The bot's first player_hit on that level is a pit fall. So the criterion reads a deliberate respawn, sees vx 190 -> 0, and reports absent knockback on a submission that implements knockback correctly.

WHAT TO DO: the criterion must ESTABLISH that the hit it measures is an enemy hit - by requiring contact with an enemy on the tick of the hit, or by rejecting hits where position jumped discontinuously (a respawn), or by driving the hit deliberately on flat ground away from any gap. FINDINGS #29 and #34 are the pattern: assert the property in its own name rather than accepting whatever event arrives first.

FALSIFIER: if unity__t0 still fails after the criterion establishes an enemy hit, the cause is in that submission and the criterion was right.

Offline: reference fixtures and stored submissions, no new trials. Must pass both halves of bot_mutants.
