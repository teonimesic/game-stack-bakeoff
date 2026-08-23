---
id: 21
title: Audit the other criteria that hold an input down while moving
status: in_flight
priority: 2
refs: eval/FINDINGS.md #84, eval/judge/bot_arena.py, eval/judge/bot_tetris3d.py
done_when: for each of the two candidates, either a submission is shown to be penalised by the held input and the bot is fixed, or the input is shown not to restrict movement in any stored submission and the candidate is cleared with that measurement
---

FINDINGS #84 named a class: a play-bot's input policy is part of the instrument, and a criterion can measure the policy rather than the submission.

THE INSTANCE ALREADY FOUND: bot_platformer's _combat held 'attack' down on every tick. On g4_platformer__unity__t0, whose swing roots the character - a normal design choice - the bot could not build enough speed to cross a 78.5-unit gap. Measured: attack off reaches x=387.4 and crosses at full health, attack on reaches x=360.3 and falls in. It then reported '0 enemy_hit' and failed attack.damages, a criterion about whether attacks damage.

TWO CANDIDATES IN THE SAME SHAPE, both unmeasured:

  1. bot_arena sends {'fire': True, **_aim(...)} while closing on enemies. A submission where firing applies recoil, roots the shooter, or imposes a reload lock would be penalised on every criterion that needs the bot to ARRIVE somewhere - enemies.chase, player.takes_damage, wave.advances.

  2. bot_tetris3d sends {'hard_drop': True, 'move_pos_x': True} on a single tick. A submission that locks the piece on hard-drop may legitimately ignore the simultaneous lateral move, and a criterion reading the resulting position would score a correct implementation as wrong.

HOW TO TEST, cheaply and offline: for each stored submission, drive the same movement twice - once with the input held, once without - and compare distance covered or final position. If they differ, the input restricts movement in that submission and any criterion depending on arrival is measuring the bot's policy.

NAMING A CLASS DOES NOT CONVICT ITS MEMBERS. Both may be fine. The point is that they are now checkable, and 'we did not check' is a different statement from 'it is fine'.

Offline: stored submissions and reference fixtures, no new trials. Any bot change must pass both halves of bot_mutants.
