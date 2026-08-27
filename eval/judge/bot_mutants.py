#!/usr/bin/env python3
"""Mutation tests for the play-bot criteria. Run: `python3 judge/bot_mutants.py`.

THE POINT OF THIS FILE, and it is the same point as `audio_selftest.py`.

Sixteen play-bot criterion failures were adjudicated against archived source and every
one of them was a harness defect - a criterion that WAITED for a condition instead of
CAUSING it, or that sampled ambient state instead of tracking identity. The repair in
each case turns an observation into an experiment: drive a paddle so the ball must meet
it off-centre; push the piece toward the side that has room; follow one enemy by id and
move its target; serialise probe sessions so a second one cannot be refused.

Every one of those repairs makes the criterion EASIER TO PASS BY CONSTRUCTION. That is
the intent and it is also the hazard: sixteen false negatives replaced by criteria that
can no longer fail is a strictly worse outcome, and it would read as success in every
report. A criterion validated only against good input is indistinguishable from a
criterion that cannot fail.

So each repaired criterion is pinned in both directions:

    healthy reference fixture  -> must PASS
    fixture with the behaviour surgically removed -> must FAIL, and must FAIL SCORED

The second half of that is deliberate. `scored=False` is the honest verdict for "the
instrument could not measure this", and the repairs introduced two new ways to reach it
(a lock conflict, and a precondition that could not be established). A mutant that comes
back unscored has escaped, not been caught, so it is reported as an unmet expectation.

Mutants are made by copying a fixture to a temp directory and patching `game.py` by
exact string replacement, so this file is self-contained and repeatable and no fixture
is ever modified in place. Every patch asserts its target appears exactly once - a
mutant that silently failed to apply would produce a green row that means nothing.

THREE KINDS OF SUBJECT, AND THEY ASK THREE DIFFERENT QUESTIONS.

    MUTANT   can this criterion FAIL?      reference, behaviour removed -> must FAIL
    VARIANT  can it still PASS on a        a correct game the reference does not
             correct game?                 resemble -> EVERY criterion must pass
    PENDING  a correct game it FAILS       a correct game -> the measured failing set
             today, declared               must equal the declared one

`--hazards` prints `HAZARDS`, one recorded answer per criterion to *what
correct-but-unusual game would mis-score this?*, grouped by the failure shapes #34, #29
and #46 adjudicated. `--selftest` proves the registry gate and the pending adjudication
can go red; both are offline and drive nothing.

A VARIANT RUNS THE WHOLE BOT ON ONE FIXTURE, so its coverage is per fixture, never per
suite - and the population is every criterion instance the four bots report, not the
smaller set that carries a mutant. Some pending false negatives sit on criteria with no
mutant at all, so a repair there has nothing asking whether the criterion can still
fail. `--hazards` is the producer for all three counts; a figure typed into this
docstring instead goes stale without anything disagreeing with it.
"""

from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
import textwrap
import time
from dataclasses import dataclass, field, replace
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import probe  # noqa: E402

FIXTURES = HERE / "fixtures"

BOT_FOR = {"ref_pong": "bot_pong",
           "ref_tetris3d": "bot_tetris3d",
           "ref_arena": "bot_arena",
           "ref_platformer": "bot_platformer"}


# --------------------------------------------------------------------------- #
# The mutants
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class Mutant:
    criterion: str
    fixture: str
    label: str
    patches: tuple[tuple[str, str], ...]
    #: other criteria this mutant is EXPECTED to disturb, so the report can separate
    #: "the mutant worked" from "the mutant broke the whole game".
    collateral: tuple[str, ...] = ()
    notes: str = ""


# -- ref_pong ---------------------------------------------------------------- #

WALLS_OFF = ("""        top = ARENA_HALF_H - BALL_RADIUS
        if ny > top:
            ny = 2.0 * top - ny
            self.ball_vy = -self.ball_vy
            events.append("wall_bounce")
        elif ny < -top:
            ny = -2.0 * top - ny
            self.ball_vy = -self.ball_vy
            events.append("wall_bounce")
""", """        top = ARENA_HALF_H - BALL_RADIUS
        # MUTANT: the vertical reflection at the walls is gone.
""")

#: `rally.counts` carried no mutant of its own until 2026-08-26 - only collateral on
#: `ball.moves` and `paddle.deflects`, both of which stop the rally happening at all, so
#: neither asks whether the COUNTER can be read wrong while the game plays normally.
#: Here the ball still rallies and the counter never moves. `rally.resets` survives it:
#: a frozen 0 is 0 on the scoring tick too, which is what makes this mutant isolated.
RALLY_FROZEN = ("        self.rally += 1\n",
                "        # MUTANT: the rally counter never moves.\n")

DEFLECT_OFF = ("        self.ball_vx = sign * self.speed * math.cos(angle)",
               "        self.ball_vx = -sign * self.speed * math.cos(angle)  # MUTANT")

WALLCLOCK_SEED = (
    """import math
import struct
""",
    """import math
import os
import struct
import time
""",
), (
    "        self.seed = int(seed) & _M64",
    "        self.seed = (int(seed) ^ os.getpid() ^ time.time_ns()) & _M64  # MUTANT",
)

# The ball never moves, though it still reports a velocity - so the repaired criterion
# cannot pass merely by detecting that the ball went "live".
BALL_FROZEN = ("""        nx = self.ball_x + self.ball_vx * DT
        ny = self.ball_y + self.ball_vy * DT""",
               """        nx = self.ball_x  # MUTANT: the ball never actually moves
        ny = self.ball_y""")

#: `match.ends` had NO mutant of its own until 2026-08-25 - it appeared only as
#: collateral - so the one criterion pong's `Bot.end_condition` names was pinned in one
#: direction. Two patches, because one is not enough to express the defect: the
#: reference zeroes the ball's velocity when the match is won, so deleting the early-out
#: alone leaves a game that steps a stationary ball and is indistinguishable from a
#: stopped one. The match is won, the ball plays on, and the score keeps climbing past
#: eleven with nobody touching a paddle.
MATCH_PLAYS_ON = ("""        if self.over:
            # First to WIN_SCORE has won: no more play until reset().
            return events
""", """        # MUTANT: the match is won and play carries on regardless
"""), ("""            self.over = True
            self.ball_x = 0.0
            self.ball_y = 0.0
            self.ball_vx = 0.0
            self.ball_vy = 0.0
            self.speed = BALL_SPEED_START""",
       """            self.over = True
            self._serve(serve_dir)  # MUTANT: the winning point serves another ball""")

# NOT a mutant - a VARIANT that must still PASS. An opening title card holding the ball
# for 104 ticks, copied from what an agent-built Godot submission actually shipped
# (`OPENING_DELAY = 104`, "so the title card is readable"). The old `ball.moves` idled a
# fixed 60 ticks and failed this correct game for doing the presentation work the task
# asks for. The reference game serves immediately, which is why the defect was invisible
# for three matrices: the control shared the assertion's assumption.
OPENING_TITLE_CARD = ("""        self._move_paddles(inputs)""",
                      """        self._move_paddles(inputs)
        if not hasattr(self, "_opening"):
            self._opening = 104
            self._held_v = (self.ball_vx, self.ball_vy)
            self.ball_vx = self.ball_vy = 0.0
        if self._opening > 0:
            self._opening -= 1
            if self._opening == 0:
                self.ball_vx, self.ball_vy = self._held_v
            return events""")

SEED_IGNORED = ("        self.seed = int(seed) & _M64",
                "        self.seed = 0  # MUTANT: the seed argument is ignored")

# -- ref_tetris3d ------------------------------------------------------------ #

MOVES_IGNORED = ("""            if self._repeat(field) and self._translate(dx, 0, dz):
                moved = True""",
                 """            if False:  # MUTANT: horizontal move inputs are ignored
                moved = True""")

NEVER_SETTLES = ("""        for x, y, z in self.piece_cells:
            self.grid[(x, y, z)] = self.piece_kind""",
                 """        for x, y, z in self.piece_cells:
            pass  # MUTANT: locked cells never join the settled grid""")

NEVER_ENDS = ("""        if not self._valid(cells):
            self.piece_kind = None
            self.piece_cells = []
            self.game_over = True
            return ["game_over"]""",
              """        if not self._valid(cells):
            self.piece_kind = None
            self.piece_cells = []
            return []  # MUTANT: stacking out never sets game_over""")

#: `piece.spawns` and `piece.falls` are the two criteria `bot_tetris3d.OPENING_BUDGET`
#: widened, from 20 and 120 ticks to 512 (`tasks/158`). Widening a budget can only make
#: a criterion easier to pass, which is this file's own stated hazard, and neither
#: carried a mutant before that change - so a criterion that had become incapable of
#: failing would have read as a clean suite. These two are the negative controls for it,
#: and each removes the mechanism its criterion names rather than stalling the game:
#: NO_PIECE_EVER_SPAWNS pins the TIMEOUT path, which is the path a longer budget
#: touches, and NO_GRAVITY leaves hard drop working so the descent is the only thing gone.
NO_PIECE_EVER_SPAWNS = ("""        self.piece_kind = kind
        self.piece_cells = cells
        return ["spawn"]
""", """        # MUTANT: no piece is ever handed to the player.
        self.piece_kind = None
        self.piece_cells = []
        return []
""")

NO_GRAVITY = ("""        self.fall_timer += 1
        if self.fall_timer >= interval:
            self.fall_timer = 0
            if not self._translate(0, -1, 0):
                self._lock(events)
        return events
""", """        self.fall_timer += 1
        if self.fall_timer >= interval:
            self.fall_timer = 0
            # MUTANT: the piece never descends on its own; only a hard drop moves it.
        return events
""")

# NOT mutants - two VARIANTS that must still PASS, and the reason there are two of them.
# A title card can be drawn over a well that already holds its first piece, frozen, or
# over an empty one the first piece drops into when the card clears. Those two readings
# meet DIFFERENT opening budgets, so before `bot_tetris3d.OPENING_BUDGET` existed a
# repair to either left the other red: the frozen well failed `piece.falls` alone, and
# the empty well failed `gameover.triggers`, `piece.falls`, `piece.spawns` and
# `piece.stacks` - four of fifteen criteria from one 20-tick await. Both were declared
# PENDING against `tasks/158` and promoted here when the budgets became one constant.
#
# 96 is the platformer REFERENCE's own `OPENING_TICKS`, so neither card is longer than
# one this repository ships, and `bot_pong.LIVE_BUDGET` is the same 512 - bought by a
# Godot submission that held the ball for `OPENING_DELAY = 104` "so the title card is
# readable" (#34). Keep both cards at 96: the old boundary was exact, an 18-tick card
# passing and a 21-tick one failing, so a shorter card here would stop biting.
TETRIS_CARD_OVER_A_FROZEN_WELL = ("""        if self.game_over:
            return events
""", """        if self.game_over:
            return events
        if self.tick <= 96:
            # VARIANT: a title card. Control is not handed over yet; nothing falls.
            return events
""")

TETRIS_CARD_OVER_AN_EMPTY_WELL = ("""        self._spawn()  # the first piece is already falling at tick 0
""", """        # VARIANT: the well is shown empty behind a title card; the first piece
        # arrives when the card clears.
"""), ("""        if self.game_over:
            return events
""", """        if self.game_over:
            return events
        if self.tick <= 96:
            return events
        if self.piece_kind is None and not self.grid:
            return self._spawn()
""")

# -- ref_arena (3D / analog spec, 2026-08-15) -------------------------------- #
#
# Every criterion the 3D rewrite ADDED is pinned here. A criterion written against a
# newly specified mechanic has never been seen to fail, and "cannot fail" and "no longer
# produces false negatives" are indistinguishable without a mutant (FINDINGS #29).

FIXED_HEADING = ("""            ux, uy, uz = dx / dist, dy / dist, dz / dist""",
                 """            ux, uy, uz = 1.0, 0.0, 0.0   # MUTANT: a fixed heading""")

ANALOG_SNAPPED = ("""    mag = math.sqrt(x * x + y * y + z * z)
    if mag > 1.0:
        return x / mag, y / mag, z / mag
    return x, y, z""",
                  """    # MUTANT: every axis snaps to -1, 0 or +1. This is eight-way movement wearing
    # the analog contract - identical in a screenshot, and the whole point of the
    # criterion.
    x = 0.0 if abs(x) < 0.5 else (1.0 if x > 0 else -1.0)
    y = 0.0 if abs(y) < 0.5 else (1.0 if y > 0 else -1.0)
    z = 0.0 if abs(z) < 0.5 else (1.0 if z > 0 else -1.0)
    mag = math.sqrt(x * x + y * y + z * z)
    if mag > 1.0:
        return x / mag, y / mag, z / mag
    return x, y, z""")

#: A 96-tick opening title card over `ref_arena`, the same length as the two tetris
#: cards and the platformer reference's own `OPENING_TICKS`. It gates the SIMULATION, so
#: it meets every one of the ten sessions this bot opens from that session's own tick 0.
#:
#: Before `bot_arena.OPENING_BUDGET` it failed `player.moves` and `move.analog` - both
#: read a 30-tick push - and lengthening the card walked nine more criteria red before
#: 400 ticks (`tasks/173`). Keep it at 96: the boundary was exact, a 29-tick card
#: passing and a 30-tick one failing, so a shorter one would stop biting.
ARENA_OPENING_TITLE_CARD = ("""        if self.game_over:
            return events
""", """        if self.game_over:
            return events
        if self.tick <= 96:
            # VARIANT: a title card. Control is not handed over yet; nothing steps.
            return events
""")

#: THE TIMEOUT PATH, and the negative control for `OPENING_BUDGET`. Widening every
#: session's opening from nothing to 512 ticks can only make a criterion easier to pass,
#: so what needs pinning is that a game which NEVER hands control over still goes red
#: after the longer wait. Its collateral is nearly the whole suite by construction: a
#: bot that cannot take control cannot establish any condition, and every criterion says
#: so in the same sentence rather than inventing a downstream reason for it.
ARENA_MOVES_IGNORED = ("""        dx, dy, dz = _vector(inputs, "move")""",
                       """        dx, dy, dz = 0.0, 0.0, 0.0   # MUTANT: movement input is ignored""")

#: `enemies.spawn` had no mutant until 2026-08-27, and the opening budget is what made
#: one necessary: the criterion now tolerates a card before its 300-tick wait, so
#: "cannot fail" and "no longer produces false negatives" needed separating (#29). The
#: wave is still announced - `wave_start` fires and the counter still advances - and
#: nothing arrives, which is the half of the criterion the event cannot carry.
NO_ENEMIES = ("""        for i in range(self.wave_count(self.wave)):""",
              """        for i in range(0):   # MUTANT: a wave is announced and nothing arrives""")

#: `fire.spawns_bullets` asks for bullets THAT TRAVEL, and this is the half a bullet
#: count cannot see: the gun still fires on its own interval, the snapshot still carries
#: a bullet per shot, and none of them ever leaves the muzzle. `fire.rate_limited` reads
#: shooting ticks and is unmoved, which is what keeps this mutant pointed at one thing.
BULLETS_DO_NOT_TRAVEL = ("BULLET_SPEED = 520.0",
                         "BULLET_SPEED = 0.0   # MUTANT: bullets appear and stay put")

#: A twin-stick game ported from a single-stick one: the gun points wherever the player
#: is walking. Pixel-identical to a correct game in any frame where the two happened to
#: agree, and the defect `aim.independent` exists to catch - which had no mutant of its
#: own until the opening budget made one necessary.
AIM_FOLLOWS_MOVEMENT = ("""        ax, ay, az = _vector(inputs, "aim")""",
                        """        # MUTANT: the firing direction is tied to the movement direction.
        ax, ay, az = _vector(inputs, "move")""")

NO_MATERIALISATION = ("SPAWN_TICKS = 32",
                      "SPAWN_TICKS = 0   # MUTANT: enemies appear fully formed")

ONE_KIND = ("KINDS = (KIND_DRIFTER, KIND_WEAVER, KIND_CHARGER)",
            "KINDS = (KIND_DRIFTER,)   # MUTANT: one kind wearing three names")

NO_MULT_RISE = ("""        self.streak += 1
        if self.streak % KILLS_PER_MULT == 0 and self.multiplier < MULT_MAX:
            self.multiplier += 1
            events.append("multiplier")""",
                """        self.streak += 1
        # MUTANT: the streak is counted and never rewarded.""")

NO_MULT_FALL = ("""                self.streak = 0
                if self.multiplier > 1:
                    self.multiplier = 1
                    events.append("multiplier")""",
                """                self.streak = 0
                # MUTANT: the multiplier survives damage.""")

#: THE MULTIPLIER COLLAPSE, IN BOTH DIRECTIONS, and the pair is the point (`tasks/170`).
#: `multiplier.falls` used to compare the peak the killing phase reached with the value
#: on the tick `player_hit` fires. That reading has an error in each direction and one
#: fixture here isolates each: the window between the two readings is 459 idle ticks on
#: the reference, so anything that lowered the multiplier inside it passed, and anything
#: that lowered it one tick late failed.
#:
#: A correct game the old reading FAILED. The g3 contract fixes no tick for the fall -
#: it says the multiplier "falls when the player is hit" and declares a `multiplier`
#: event meaning "the score multiplier changed" - so a game whose collision pass records
#: the damage and whose scoring pass applies it at the top of the next tick has met it.
MULT_DEFERS_THE_DROP = (
    ("""                self.streak = 0
                if self.multiplier > 1:
                    self.multiplier = 1
                    events.append("multiplier")""",
     """                self.streak = 0
                # VARIANT: the collision pass only RECORDS the damage. The scoring pass
                # at the top of the next tick applies the collapse and declares it.
                self._deferred_drop = self.multiplier > 1"""),
    ("""        grazed = self._move_player(inputs)""",
     """        if getattr(self, "_deferred_drop", False):
            self._deferred_drop = False
            self.multiplier = 1
            events.append("multiplier")
        grazed = self._move_player(inputs)"""))

#: An INCORRECT game the old reading PASSED, and it is the reason the baseline moved to
#: the tick before the damage rather than the window merely widening. A combo timer is a
#: real arcade design; this game has one and has no damage link at all, so its multiplier
#: is back at 1 long before the first hit and the old reading credited that decay to the
#: damage. `multiplier.rises` survives because the timer restarts on every kill.
MULT_DECAYS_ON_A_TIMER = (
    ("""                self.streak = 0
                if self.multiplier > 1:
                    self.multiplier = 1
                    events.append("multiplier")""",
     """                self.streak = 0
                # MUTANT: damage does not touch the multiplier."""),
    ("""        self.streak += 1
        if self.streak % KILLS_PER_MULT == 0""",
     """        self.streak += 1
        self._idle = 0            # MUTANT: the combo timer restarts on a kill
        if self.streak % KILLS_PER_MULT == 0"""),
    ("""        grazed = self._move_player(inputs)""",
     """        self._idle = getattr(self, "_idle", 0) + 1
        if self._idle >= 120 and self.multiplier > 1:
            self._idle = 0
            self.multiplier -= 1   # MUTANT: the combo lapses instead
            events.append("multiplier")
        grazed = self._move_player(inputs)"""))

NO_GRAZE = ("""        if grazed:
            events.append("wall_graze")""",
            """        # MUTANT: the boundary is never reported.""")

FLAT_AIM = ("""        ax, ay, az = _vector(inputs, "aim")""",
            """        ax, ay, az = _vector(inputs, "aim")
        az = 0.0  # MUTANT: the depth axis is dropped, as a 2D port would drop it""")

UNBOUNDED = ("""        cx = _clamp(nx, -ARENA_HALF_X + PLAYER_RADIUS, ARENA_HALF_X - PLAYER_RADIUS)
        cy = _clamp(ny, -ARENA_HALF_Y + PLAYER_RADIUS, ARENA_HALF_Y - PLAYER_RADIUS)
        cz = _clamp(nz, -ARENA_HALF_Z + PLAYER_RADIUS, ARENA_HALF_Z - PLAYER_RADIUS)""",
             """        cx, cy, cz = nx, ny, nz   # MUTANT: the volume does not hold""")

NO_RATE_LIMIT = ("FIRE_INTERVAL = 10  # ticks between shots",
                 "FIRE_INTERVAL = 0  # MUTANT: a bullet every tick")

#: The negative control for `_shot_ticks` taking the LARGER of its two signals. A gun
#: with no interval at all, reporting `fire` only on the rising edge of the held
#: control - so the event count says one shot in 120 ticks and the bullets say 120. A
#: criterion that read the event alone would call this rate-limited, which is the
#: fail-open direction: the verdict fails on a HIGH count, so the smaller signal always
#: excuses. Firing on the rising edge is itself legal - it is the recorded hazard for
#: `fire.spawns_bullets` - and it is the missing interval that makes this a mutant.
EDGE_EVENT_NO_RATE_LIMIT = (
    ("""    def _fire(self, inputs: dict, events: list) -> None:
        if self.fire_cooldown > 0:
            self.fire_cooldown -= 1
        if not inputs.get("fire") or self.fire_cooldown > 0:
            return
        self.fire_cooldown = FIRE_INTERVAL
""", """    def _fire(self, inputs: dict, events: list) -> None:
        # MUTANT: no interval at all, and `fire` reported only on the rising edge.
        held = bool(inputs.get("fire"))
        self._edge = held and not getattr(self, "_was_firing", False)
        self._was_firing = held
        if not held:
            return
        self.fire_cooldown = 0
"""),
    ("""        events.append("fire")
""", """        if self._edge:
            events.append("fire")
"""))

NO_SCORE = ("""                self.score += SCORE_PER_KILL * self.wave * self.multiplier""",
            """                pass  # MUTANT: a kill is worth nothing""")

NO_CONTACT_DAMAGE = ("""        if self.invuln > 0:
            return
        reach = PLAYER_RADIUS + ENEMY_RADIUS""",
                     """        if self.invuln > 0:
            return
        return  # MUTANT: enemies pass straight through the player
        reach = PLAYER_RADIUS + ENEMY_RADIUS""")

#: EVERY END CONDITION HAS TWO WAYS TO BE WRONG and only one of them was pinned. The
#: flag-raising half is `NEVER_ENDS` and `PF_NEVER_ENDS`: does the game ever say it is
#: over? The other half is this - does saying so STOP THE GAME - and it is the half the
#: prompt spends its second clause on. Each fixture needs its own, because what a
#: still-running simulation MOVES differs per game, and each one is why its bot guards
#: the value it does: `kills` on the arena (the player is dead, so nothing earns points
#: and the score sits still), the well's filled-cell total on tetris (the well is full, so
#: no layer clears and the score sits still), the score on the platformer and on pong.
ARENA_KEEPS_STEPPING = ("""        if self.game_over:
            return events

        grazed = self._move_player(inputs)""",
                        """        # MUTANT: game over is reported and the simulation keeps stepping
        grazed = self._move_player(inputs)""")

PF_KEEPS_STEPPING = ("""        if self.game_over or self.victory:
            return events
""", """        # MUTANT: the run is over and the simulation keeps stepping
""")

TETRIS_KEEPS_STEPPING = ("""        if self.game_over:
            return events

        if self._edge("rotate_x")""",
                         """        # MUTANT: the well stacked out and the game keeps stepping
        if self._edge("rotate_x")""")



# -- ref_platformer (g4, 2026-08-15) ----------------------------------------- #
#
# Sixteen mutants, one per scored criterion the platformer adds. The genre-defining
# three are `attack.active_frames`, `attack.faces` and `invuln.window`, and each has a
# mutant that is invisible in a still frame: a hitbox that never turns off, a hitbox
# that never turns around, and a grace window of zero.

PF_LEFT_IGNORED = ("""        d = (1.0 if right else 0.0) - (1.0 if left else 0.0)""",
                   """        d = (1.0 if right else 0.0)  # MUTANT: walking left is ignored""")

PF_UNBOUNDED = ("""        self.px = _clamp(self.px + self.vx * DT, PLAYER_HW, LEVEL_W - PLAYER_HW)""",
                """        self.px = self.px + self.vx * DT  # MUTANT: the stage has no edges""")

PF_NO_GRAVITY = ("GRAVITY = -1500.0", "GRAVITY = 0.0  # MUTANT: nothing falls")

PF_NO_LANDING = ("""            if self.vy <= 0.0 and self.py - PLAYER_HH >= top - 1e-6 \\""",
                 """            if False and self.py - PLAYER_HH >= top - 1e-6 \\""")

PF_NO_JUMP = ("""        if inputs.get("jump") and self.grounded:""",
              """        if False:  # MUTANT: the jump input is ignored""")

PF_AIR_JUMP = ("""        if inputs.get("jump") and self.grounded:""",
               """        if inputs.get("jump"):  # MUTANT: jump works in mid-air too""")

PF_ALWAYS_ACTIVE = ("""        return ATTACK_STARTUP < self.attack_t <= ATTACK_STARTUP + ATTACK_ACTIVE""",
                    """        return True  # MUTANT: the hitbox is always live""")

PF_FIXED_SIDE = ("""        return (self.px + self.facing * HITBOX_REACH, self.py, HITBOX_W, HITBOX_H)""",
                 """        return (self.px + HITBOX_REACH, self.py, HITBOX_W, HITBOX_H)  # MUTANT""")

PF_NO_HIT_DAMAGE = ("""    def _hitbox_damage(self, events: list) -> None:
        if not self.attack_active:
            return""",
                    """    def _hitbox_damage(self, events: list) -> None:
        return  # MUTANT: the swing connects with nothing
        if not self.attack_active:
            return""")

PF_NO_CONTACT = ("""    def _contact_damage(self, events: list) -> None:
        if self.invuln > 0:
            return""",
                 """    def _contact_damage(self, events: list) -> None:
        return  # MUTANT: enemies are harmless
        if self.invuln > 0:
            return""")

PF_NO_INVULN = ("INVULN_TICKS = 48", "INVULN_TICKS = 0  # MUTANT: no grace window")

PF_NO_KNOCKBACK = ("KNOCKBACK_X = 240.0", "KNOCKBACK_X = 0.0  # MUTANT: no impulse")

PF_ONE_ANIM = ("""    def _state_for(self, inputs: dict) -> str:
        if self.attack_t > 0:""",
               """    def _state_for(self, inputs: dict) -> str:
        return ANIM_IDLE  # MUTANT: one label for everything the character does
        if self.attack_t > 0:""")

PF_FROZEN_FRAME = ("""            self.anim_frame = (self.anim_frame + 1) % ANIM_FRAMES""",
                   """            self.anim_frame = 0  # MUTANT: the sprite never advances""")

PF_NO_SCORE = ("""                    self.score += SCORE_PER_KILL""",
               """                    pass  # MUTANT: a kill is worth nothing""")

PF_NEVER_ENDS = ("""                if self.hp <= 0:
                    self.hp = 0
                    self.alive = False
                    self.game_over = True
                    events.append("game_over")""",
                 """                if self.hp <= 0:
                    self.hp = 0  # MUTANT: zero health never ends the game""")


# --------------------------------------------------------------------------- #
# VARIANTS - correct games that exercise a branch the reference cannot reach
# --------------------------------------------------------------------------- #
#
# A mutant asks *does this criterion notice when I break the thing it names?* It cannot
# ask *does this criterion still pass work the reference does not happen to do?* - and
# every false negative this project has adjudicated was of the second kind. The
# reference is a frozen answer to the task as its author read it, so a criterion is
# unvalidated on any behaviour the reference never exhibits (FINDINGS #34, #39, #46).
#
# Every entry below was paid for by a real submission, and each one's `#:` block says
# which. Two are worth reading before adding another:
#
# * the title card is what a real Godot submission shipped, and the old `ball.moves`
#   failed it for doing the presentation work the task asks for. The constant sat in
#   this file for a day, correctly labelled "a VARIANT that must still PASS", and was
#   never wired into anything that ran.
# * enemies faster than the player make the tracked enemy reach it mid-leg, which is
#   the one branch of `enemies.chase` the reference never takes. The first version of
#   that branch raised `KeyError` and fail-closed to 0.000 on `g3_arena__godot__t1` -
#   a stack-correlated zero, found by a real submission after both the reference and
#   the whole mutant suite were green.

FAST_ENEMIES = ("ENEMY_BASE_SPEED = 60.0",
                "ENEMY_BASE_SPEED = 420.0  # VARIANT: faster than the player, so it "
                "catches up")

#: The reference sets `attack.active` to EXACTLY the damaging window, so on it "a swing is
#: in progress" and "the hitbox exists" are the same tick set and no fixture can tell the
#: two apart. `g4_platformer__unity__t0` read the contract the other legal way - active for
#: the whole swing, hitbox live only in the middle - and `attack.faces` read the empty
#: rectangle's centre (0, 0) as a position. This variant is that submission's shape.
ACTIVE_SPANS_WHOLE_SWING = (
    '"attack": {"active": self.attack_active, "frame": self.attack_t,',
    '"attack": {"active": self.attack_t > 0, "frame": self.attack_t,  # VARIANT: '
    '"active" means a swing is in progress; the hitbox stays narrow',
)

#: The reference's ground platform spans the whole level, so walking off the start ledge
#: always finds a floor. Real submissions put a PIT there - that is what an opening ledge
#: is for - and five of six `wg-g4c` submissions fell to y=-68..-136 and were failed by a
#: `platform.lands` that walked off and hoped. This variant is a correct, ordinary level
#: with the ground removed from under the start, and EVERY criterion must still pass.
#:
#: THE GEOMETRY IS PART OF THE CHECK, and the first version of it got the geometry wrong
#: in the direction that manufactures a tolerance. It put the far side at x=800, a
#: 680-unit chasm. The fixture's jump clears about 148 units (JUMP_SPEED 520, GRAVITY
#: -1500, WALK_SPEED 180, and a ledge 80 units above the floor), so NO input sequence
#: reaches the far side: an exhaustive sweep over the jump tick, holding right, never
#: landed below the start ledge at all. Six combat criteria were then listed as
#: "tolerated" on the reasoning that the bot could not cross a gap, when four of them
#: were unmeasurable because there was no crossing to make - a level-design error in the
#: variant wearing the vocabulary of a bot limitation (task 76).
#:
#: The pit is now 100 units wide (ground removed for x in 120..220), which is the size
#: the `wg-g4c` submissions actually shipped: `g4_platformer__unity__t0` has a 78.5-unit
#: gap and `g4_platformer__ts__t0` has pits at x 520-600, 1080-1180, 1700-1790. It is
#: still BOTTOMLESS - walking off the ledge falls out of the world and respawns, so a
#: `platform.lands` that reused the fall still fails here - and it is crossable by the
#: bot's edge jump, which is what makes the combat cluster measurable and the tolerance
#: unnecessary. Measured: walking off lands in the pit; jumping at `_EDGE_JUMP_WITHIN`
#: from the edge lands at x=248.1, clearing the far lip at x=208 (ground x=220 minus the
#: player's half width) by 40 units.
PIT_UNDER_LEDGE = (
    '{"id": 1, "x": 1200.0, "y": -8.0, "w": 2400.0, "h": 16.0},    # ground, top y=0',
    '{"id": 1, "x": 1310.0, "y": -8.0, "w": 2180.0, "h": 16.0},    # VARIANT: ground '
    'starts at x=220, so the opening ledge overlooks a bottomless 100-unit pit',
)

#: THE CLOSING CARD ON THE FIXTURE IT WAS PAID FOR. `MATCH_PLAYS_ON` asks whether
#: `match.ends` can fail; only this asks whether it can still pass on the very
#: submission that bought the repair - `g1_pong__rust`, which holds its card for
#: `GAME_OVER_LOCKOUT_TICKS = 96` and then takes any control as the reset. Pong went
#: without one for the whole of `tasks/157` because the pending entries were on the
#: other three fixtures, which is the per-fixture coverage trap this file exists to
#: name (raised by CodeRabbit on PR #40).
#:
#: `_match_ends` runs LAST on the shared session - `_paddle_mechanics` and the
#: determinism criteria open their own - so a restart inside its pressed phase reaches
#: no other criterion.
PONG_RESTART_ON_A_CONTROL = ("""        if self.over:
            # First to WIN_SCORE has won: no more play until reset().
            return events
""", """        if self.over:
            # VARIANT: a game-over card for 96 ticks, then any control starts a new
            # match - the reset the task's own "until it is reset" contemplates.
            self._over = getattr(self, "_over", 0) + 1
            if self._over > 96 and any(inputs.get(f) for f in INPUT_FIELDS):
                t = self.tick
                self.reset()
                self.tick = t
                self._over = 0
            return events
""")

#: THE CLOSING CARD, on the three games whose end condition is a loss. The task prompt
#: says an ended game "stops accepting play until it is reset", which contemplates a
#: reset existing, and an agent is free to bind it to a control: `g1_pong__rust` holds a
#: game-over card for `GAME_OVER_LOCKOUT_TICKS = 96` and then lets any control start a
#: new run. Pong's `match.ends` idled after the win; the other three bots pressed
#: straight away, so this shape was red on `ref_arena` and `ref_platformer` and passed
#: on `ref_tetris3d` for a reason that was not evidence. `probe.end_condition_holds` is
#: now the single copy of that policy - it idles, then presses and reads the pressed
#: phase THROUGH the reset - and these three are what keeps it from drifting back
#: (`tasks/157`).
ARENA_RESTART_ON_A_CONTROL = ("""        if self.game_over:
            return events
""", """        if self.game_over:
            # VARIANT: a game-over card for 96 ticks, then any control starts a new
            # run - the reset the task's own "until it is reset" contemplates.
            self._over = getattr(self, "_over", 0) + 1
            if self._over > 96 and any(inputs.get(f) for f in INPUT_FIELDS):
                t = self.tick
                self.reset()
                self.tick = t
                self._over = 0
            return events
""")

PF_RESTART_ON_A_CONTROL = ("""        if self.game_over or self.victory:
            return events
""", """        if self.game_over or self.victory:
            # VARIANT: a game-over card for 96 ticks, then any control starts a new
            # run - the reset the task's own "until it is reset" contemplates.
            self._over = getattr(self, "_over", 0) + 1
            if self._over > 96 and any(inputs.get(f) for f in INPUT_FIELDS):
                t = self.tick
                self.reset()
                self.tick = t
                self._over = 0
            return events
""")

#: THE CARD IS 190 TICKS HERE, AND THE LENGTH IS THE POINT. At 96 this fixture PASSED
#: the unrepaired bot, and the pass was not evidence: the bot's 200 ticks of held
#: `hard_drop` restarted the run at tick 96 and then stacked it out again inside the
#: remaining window, with the restart's own score reset making `frozen` true. A card
#: longer than the window the criterion presses into removes that luck - the restarted
#: run has too few ticks left to lose again - so this is the one length at which the
#: fixture reports the bot rather than the arithmetic. A longer card is no less correct
#: than a shorter one; nothing in the prompt bounds it.
TETRIS_RESTART_ON_A_CONTROL = ("""        if self.game_over:
            return events
""", """        if self.game_over:
            # VARIANT: a game-over card for 190 ticks, then any control starts a new
            # run - the reset the task's own "until it is reset" contemplates.
            self._over = getattr(self, "_over", 0) + 1
            if self._over > 190 and any(inputs.get(f) for f in INPUT_FIELDS):
                t = self.tick
                self.reset()
                self.tick = t
                self._over = 0
                return ["spawn"]
            return events
""")


#: A weapon that fires a spread puts several bullets in the world per shot, which is an
#: ordinary design for a game the prompt asks to make "loud, fast and readable at a
#: glance". `fire.rate_limited` asks about SHOTS, and until `tasks/160` it counted
#: BULLET IDS - so this game read as 90 shots in 120 ticks and went red, with the true
#: 30 printed in its own evidence string beside the verdict computed from the other
#: number. `bot_arena.ArenaBot._shot_ticks` counts shooting TICKS, and this is the
#: variant that measures it.
SPREAD_WEAPON = ("""        self.fire_cooldown = FIRE_INTERVAL
        self.bullets.append({
            "id": self._take_id(),
            "x": self.px + self.aim_x * MUZZLE_OFFSET,
            "y": self.py + self.aim_y * MUZZLE_OFFSET,
            "z": self.pz + self.aim_z * MUZZLE_OFFSET,
            "vx": self.aim_x * BULLET_SPEED,
            "vy": self.aim_y * BULLET_SPEED,
            "vz": self.aim_z * BULLET_SPEED,
        })
""", """        self.fire_cooldown = 4      # VARIANT: a faster, three-round spread
        for k in (-1, 0, 1):
            self.bullets.append({
                "id": self._take_id(),
                "x": self.px + self.aim_x * MUZZLE_OFFSET,
                "y": self.py + self.aim_y * MUZZLE_OFFSET + k * 3.0,
                "z": self.pz + self.aim_z * MUZZLE_OFFSET,
                "vx": self.aim_x * BULLET_SPEED,
                "vy": self.aim_y * BULLET_SPEED + k * 8.0,
                "vz": self.aim_z * BULLET_SPEED,
            })
""")


@dataclass(frozen=True)
class Variant:
    fixture: str
    label: str
    patches: tuple[tuple[str, str], ...]
    #: the criteria this variant exists to exercise; ALL criteria must still pass.
    exercises: tuple[str, ...]
    #: Criteria this variant legitimately makes UNMEASURABLE, and why, declared the way
    #: `Mutant.collateral` is. A level with a pit where the enemies used to stand cannot
    #: be used to test combat, and pretending otherwise leaves a choice between a red
    #: suite and a quietly narrowed check. Every entry needs a reason in `notes`: this
    #: field is the one place in the suite where a failure is allowed not to count, and
    #: rule 7 says every such channel is one a real bug can widen.
    tolerates: tuple[str, ...] = ()
    notes: str = ""


# Most of these are a correct game under the task prompt, whose shared preamble asks for
# one in every game:
#
#     The game presents itself: a player who has never seen it can tell what to do,
#     can see their progress while playing, and reaches a clear end state.
#
# THE LINE THAT DECIDES WHETHER PRESENTATION IS THIS SUITE'S PROBLEM: whether it gates
# the SIMULATION. A title card that holds the first serve and a game-over card that
# takes a control as a reset both stop the sim from stepping, so the play-bot sees them;
# a paddle that bobs, a screen that shakes and a score that counts up on screen live in
# the view layer, which the prompt puts in a different module and the probe never reads.
VARIANTS: list[Variant] = [
    Variant("ref_pong", "a 104-tick opening title card holds the ball",
            (OPENING_TITLE_CARD,), ("ball.moves",),
            notes="copied from an agent-built Godot submission's OPENING_DELAY = 104"),
    Variant("ref_arena", "enemies faster than the player, so one reaches it mid-leg",
            (FAST_ENEMIES,), ("enemies.chase",),
            notes="exercises the contact branch of enemies.chase, which the reference "
                  "cannot reach"),
    Variant("ref_platformer", "`active` spans the whole swing, hitbox only the middle",
            (ACTIVE_SPANS_WHOLE_SWING,), ("attack.faces", "attack.active_frames"),
            notes="the reading g4_platformer__unity__t0 took, and a legal one: its own "
                  "probe says `active` means a swing is in progress while `hitbox` is "
                  "only the rectangle that damages THIS TICK. The old criterion sampled "
                  "the hitbox on every active tick and read the empty box's centre "
                  "(0, 0) as a position, scoring -61.7 for a hitbox that was simply not "
                  "there yet"),
    Variant("ref_platformer", "the opening ledge overlooks a bottomless pit",
            (PIT_UNDER_LEDGE,),
            ("platform.lands", "player.falls", "attack.damages", "score.on_kill",
             "enemy.damages_player", "invuln.window", "knockback.applied",
             "gameover.triggers"),
            notes="the layout five of six wg-g4c submissions actually had. The old "
                  "criterion walked off the ledge and hoped something was underneath, "
                  "so this correct level failed it; the repaired one jumps and lands on "
                  "the platform underfoot, which needs no level knowledge. IT CARRIED "
                  "SIX TOLERANCES UNTIL TASK 76 AND NOW CARRIES NONE. Four of the six "
                  "really did go red - the contact cluster, which needs the bot to "
                  "REACH an enemy and be hurt by it - and the reason was two defects at "
                  "once. The bot had three separate 'walk toward the target' loops and "
                  "only two of them learned to jump a gap, so `_hurt` walked into the "
                  "pit on every attempt while `_combat` crossed it; and this variant's "
                  "own geometry put the far side 680 units away, past any jump, so no "
                  "bot could have crossed it. Both are fixed: one shared `_walk_toward` "
                  "builds the inputs for all three loops, and the pit is the 100 units "
                  "the real submissions shipped"),
    Variant("ref_pong", "a game-over card, then a control starts a new match",
            (PONG_RESTART_ON_A_CONTROL,), ("match.ends",),
            notes="the shape `g1_pong__rust` shipped, and the one that bought the whole "
                  "repair - pong had no variant for it until `tasks/157`'s review, "
                  "because the pending entries sat on the other 3 fixtures"),
    Variant("ref_arena", "a game-over card, then a control starts a new run",
            (ARENA_RESTART_ON_A_CONTROL,), ("gameover.triggers",),
            notes="declared PENDING for eleven weeks, measured `after 300 more ticks "
                  "of input: game_over=False, alive=True`. `_death` pressed fire, aim "
                  "and move straight after the player died, which pressed this game's "
                  "own reset. Repaired in `probe.end_condition_holds`, which every "
                  "bot's end-condition criterion now calls (`tasks/157`)"),
    Variant("ref_platformer", "a game-over card, then a control starts a new run",
            (PF_RESTART_ON_A_CONTROL,), ("gameover.triggers",),
            notes="the same defect in `_hurt`, which pressed move_right, jump and "
                  "attack for 200 ticks: `after 200 more ticks of input: "
                  "game_over=False, alive=True`"),
    Variant("ref_tetris3d", "a 190-tick game-over card, then a control restarts",
            (TETRIS_RESTART_ON_A_CONTROL,), ("gameover.triggers",),
            notes="the third copy, in `_gameover_check`, and the one that was never "
                  "declared PENDING because at a 96-tick card it PASSED - the "
                  "restarted run stacked out again inside the same window and the "
                  "restart's own score reset satisfied the frozen test. At 190 the "
                  "unrepaired bot reads `still over after 200 more ticks of input: "
                  "False`, so this length is what makes the row report the bot"),
    Variant("ref_tetris3d", "a 96-tick card over a frozen well",
            (TETRIS_CARD_OVER_A_FROZEN_WELL,), ("piece.falls",),
            notes="the well is drawn with its first piece already in it and nothing "
                  "moving, which is how the platformer REFERENCE reads a card, and it "
                  "isolates the DESCENT budget. `piece.falls` stepped 120 ticks against "
                  "a fall interval of 48 and read `lowest cell height went from 11 to "
                  "11 without input`; a 60-tick card passed, so the budget was not "
                  "absent - it was a quarter of what the same shape bought pong. "
                  "PENDING against `tasks/158` until `OPENING_BUDGET` landed"),
    Variant("ref_arena", "a faster three-round spread weapon",
            (SPREAD_WEAPON,), ("fire.rate_limited",),
            notes="PENDING for two days against `tasks/160`, measured `90 bullets from "
                  "120 ticks of held fire (30 fire events)`. 30 shots in 120 ticks IS "
                  "a rate limit, and the criterion printed that number in its own "
                  "evidence beside a verdict computed from the bullet count. It now "
                  "counts SHOOTING TICKS and reads `30 shooting ticks out of 120 ticks "
                  "of held fire`"),
    Variant("ref_arena", "the multiplier collapse lands the tick after the damage",
            MULT_DEFERS_THE_DROP, ("multiplier.falls",),
            notes="the shape `tasks/159` constructed for pong and had to reject there, "
                  "because g1 DEFINES `rally` as a count of the events the tick line "
                  "carries. g3 defines `multiplier` nowhere - it says only that it "
                  "'falls when the player is hit', and the same sentence's other half "
                  "is read by `multiplier.rises` over hundreds of ticks by any "
                  "mechanism. Measured against the one-tick reading: `multiplier was 2 "
                  "before damage and 2 on the tick of the first hit`, FAIL"),
    Variant("ref_arena", "a 96-tick opening title card holds the whole arena",
            (ARENA_OPENING_TITLE_CARD,),
            ("player.moves", "move.analog", "fire.spawns_bullets",
             "fire.rate_limited", "aim.independent", "aim.three_axis",
             "enemy.materialises", "enemies.chase", "enemies.spawn"),
            notes="the fourth game to get one, and the one whose bot had no opening "
                  "budget anywhere. Measured before `bot_arena.OPENING_BUDGET`: this "
                  "card failed `player.moves` (`displacement along each axis after 30 "
                  "ticks of full push: x=0.0, y=0.0, z=0.0`) and `move.analog` (`a full "
                  "push moved only 0.00 units`), and lengthening it walked the other "
                  "seven red by 400 ticks. The nine listed are every criterion a card "
                  "at or under the 512-tick budget used to break; the sweep is in "
                  "`tasks/173`"),
    Variant("ref_tetris3d", "a 96-tick card over an empty well",
            TETRIS_CARD_OVER_AN_EMPTY_WELL,
            ("gameover.triggers", "piece.falls", "piece.spawns", "piece.stacks"),
            notes="the other reading of a card: the well is shown empty and the first "
                  "piece arrives when the card clears. Four of fifteen criteria went "
                  "red off one 20-tick await - `piece.spawns` read `first piece has 0 "
                  "cells: []`, and `piece.stacks` and `gameover.triggers` each opened a "
                  "FRESH session the same card gated, so their own 60-tick first awaits "
                  "expired too (`played 0 pieces over 60 ticks`, `stacked into one "
                  "corner for 60 ticks`). That is why `OPENING_BUDGET` reaches four "
                  "call sites and not two. PENDING against `tasks/158` until it landed"),
]


# --------------------------------------------------------------------------- #
# PENDING VARIANTS - correct games this suite FAILS TODAY
# --------------------------------------------------------------------------- #
#
# A `Variant` is a correct game every criterion passes. A `Pending` is a correct game
# some criterion FAILS, with the failing ids written down, and the suite asserts EXACTLY
# that set every run.
#
# It is not a tolerance and it must never become one. `Variant.tolerates` waives a
# criterion silently and is the one place in this file a failure is allowed not to
# count; a `Pending` names the criterion, names the ticket that will repair it, and goes
# red on any set but the declared one - including the EMPTY set, which is what a landed
# repair looks like and which asks the next agent to promote the entry into `VARIANTS`.


@dataclass(frozen=True)
class Pending:
    fixture: str
    label: str
    patches: tuple[tuple[str, str], ...]
    #: EXACTLY the criteria this correct game fails or leaves unscored today.
    fails: tuple[str, ...]
    #: the ticket that will repair it. A pending entry with no owner is a waiver.
    task: str
    notes: str = ""


#: EMPTY, and that is a state this list is allowed to be in: every declared false
#: negative has been repaired. The last was `ref_arena`'s spread weapon, promoted into
#: `VARIANTS` by `tasks/160`. `selftest` pins `adjudicate_pending` against a synthetic
#: entry rather than against whatever happens to be here, so an empty list is still a
#: check that can go red.
PENDING_VARIANTS: list[Pending] = []


MUTANTS: list[Mutant] = [
    Mutant("ball.moves", "ref_pong", "the ball never actually moves",
           (BALL_FROZEN,), collateral=("ball.wall_bounce", "paddle.deflects",
                                       "rally.counts", "rally.resets",
                                       "score.increments", "serve.resets",
                                       "match.ends"),
           notes="a frozen ball still reports a velocity, so detecting that it went "
                 "live is not enough to pass"),
    Mutant("ball.wall_bounce", "ref_pong", "walls do not reflect the ball",
           (WALLS_OFF,),
           notes="the bot drives the ball into a wall; nothing comes back"),
    Mutant("paddle.deflects", "ref_pong", "paddle contact does not reverse the ball",
           (DEFLECT_OFF,), collateral=("match.ends", "score.increments",
                                       "serve.resets", "rally.resets",
                                       "ball.wall_bounce"),
           notes="a ball that is never sent back never leaves the paddle, so the "
                 "whole match flow stops with it"),
    Mutant("rally.counts", "ref_pong", "the rally counter never moves",
           (RALLY_FROZEN,),
           notes="the rally still happens and every hit is still reported; only the "
                 "counter is dead. `rally.resets` is NOT collateral - a counter frozen "
                 "at 0 reads 0 on the scoring tick, which is what that criterion asks"),
    Mutant("determinism.replay", "ref_pong", "seeded from pid and wall-clock time",
           WALLCLOCK_SEED),
    Mutant("determinism.seed", "ref_pong", "the seed argument is ignored",
           (SEED_IGNORED,)),
    Mutant("piece.spawns", "ref_tetris3d", "no piece is ever handed to the player",
           (NO_PIECE_EVER_SPAWNS,),
           collateral=("piece.falls", "piece.locks", "move.translates",
                       "rotate.reorients", "harddrop.locks", "piece.stacks",
                       "gameover.triggers"),
           notes="the TIMEOUT path, and the negative control for `OPENING_BUDGET`: "
                 "widening the first await from 20 ticks to 512 can only make this "
                 "criterion easier to pass, so what needs pinning is that a game which "
                 "never spawns still goes red after the longer wait. The collateral is "
                 "wide because a game with no piece has nothing to move, rotate, drop "
                 "or stack out with"),
    Mutant("piece.falls", "ref_tetris3d", "the piece never descends on its own",
           (NO_GRAVITY,), collateral=("piece.locks",),
           notes="the other half of the `OPENING_BUDGET` control, on the budget that "
                 "went from 120 ticks to 512. Hard drop is a separate branch and still "
                 "works, so the piece still locks, stacks and ends the game when the "
                 "bot drops it - gravity is the only mechanism removed, and 512 ticks "
                 "of no input is 512 ticks of the piece sitting where it spawned"),
    Mutant("move.translates", "ref_tetris3d", "horizontal move inputs are ignored",
           (MOVES_IGNORED,)),
    Mutant("piece.stacks", "ref_tetris3d", "locked cells never enter the settled grid",
           (NEVER_SETTLES,), collateral=("piece.locks", "harddrop.locks",
                                         "gameover.triggers")),
    Mutant("gameover.triggers", "ref_tetris3d", "game_over is never set",
           (NEVER_ENDS,)),
    Mutant("player.moves", "ref_arena", "the player never answers a movement input",
           (ARENA_MOVES_IGNORED,),
           collateral=("move.analog", "player.bounded", "wall.graze", "enemies.spawn",
                       "enemy.kinds", "enemies.chase", "enemy.materialises",
                       "fire.spawns_bullets", "fire.rate_limited", "aim.independent",
                       "aim.three_axis", "bullets.kill", "score.on_kill",
                       "multiplier.rises", "multiplier.falls", "wave.advances",
                       "player.takes_damage", "gameover.triggers",
                       "determinism.replay", "determinism.seed"),
           notes="the TIMEOUT path, and the negative control for `OPENING_BUDGET`: the "
                 "wait every session now opens with can only make a criterion easier to "
                 "pass, so a game that never hands control over has to stay red after "
                 "it. The collateral is everything but `state.shape`, which is read at "
                 "tick 0 before the wait - a bot that cannot take control establishes "
                 "no condition, and each criterion reports that rather than a "
                 "downstream symptom of it"),
    Mutant("enemies.spawn", "ref_arena", "a wave is announced and nothing arrives",
           (NO_ENEMIES,),
           collateral=("enemy.kinds", "enemies.chase", "enemy.materialises",
                       "bullets.kill", "score.on_kill", "multiplier.rises",
                       "multiplier.falls", "player.takes_damage", "gameover.triggers"),
           notes="`wave_start` still fires and the wave counter still advances, so the "
                 "event half of the criterion is untouched and only the enemies are "
                 "missing. That is the half `wave.advances` cannot stand in for"),
    Mutant("fire.spawns_bullets", "ref_arena", "bullets appear and never travel",
           (BULLETS_DO_NOT_TRAVEL,),
           collateral=("aim.independent", "aim.three_axis", "bullets.kill",
                       "score.on_kill", "multiplier.rises", "multiplier.falls",
                       "wave.advances", "enemy.kinds"),
           notes="the criterion asks for bullets THAT TRAVEL, and a bullet count cannot "
                 "see this: the gun fires on its own interval and every shot is in the "
                 "snapshot. `fire.rate_limited` counts shooting ticks and is unmoved"),
    Mutant("aim.independent", "ref_arena", "the gun points where the player is walking",
           (AIM_FOLLOWS_MOVEMENT,),
           collateral=("aim.three_axis", "multiplier.rises", "multiplier.falls",
                       "wave.advances"),
           notes="aiming and moving are separate vectors in the prompt, so this is the "
                 "single-stick port. `aim.three_axis` is collateral because the bot "
                 "moves along -y in every firing phase, so a gun following the movement "
                 "fires along -y whatever it is aimed at; the rest follow from a bot "
                 "that kites AWAY from its target, which now points the gun away too, "
                 "so the killing streak those criteria have to establish never happens"),
    Mutant("enemies.chase", "ref_arena", "enemies walk a fixed heading",
           (FIXED_HEADING,), collateral=("player.takes_damage", "gameover.triggers",
                                         "wave.advances", "bullets.kill",
                                         "score.on_kill", "multiplier.rises",
                                         "multiplier.falls", "enemy.kinds"),
           notes="enemy.kinds is collateral because kinds unlock by wave and a wave "
                 "only ends when its enemies are gone; enemies that walk away from the "
                 "player are hard to clear, so the later kinds never arrive"),
    Mutant("move.analog", "ref_arena", "analog input snapped to eight-way",
           (ANALOG_SNAPPED,),
           notes="a half push becomes a full push; indistinguishable in a frame"),
    Mutant("enemy.materialises", "ref_arena", "enemies appear fully formed",
           (NO_MATERIALISATION,), collateral=("player.takes_damage", "wave.advances",
                                              "multiplier.rises", "multiplier.falls",
                                              "bullets.kill", "score.on_kill",
                                              "enemies.chase")),
    Mutant("enemy.kinds", "ref_arena", "one kind wearing three names",
           (ONE_KIND,)),
    Mutant("multiplier.rises", "ref_arena", "the multiplier never rewards a streak",
           (NO_MULT_RISE,), collateral=("multiplier.falls",),
           notes="a multiplier that cannot rise can never be seen to fall, so the "
                 "collateral is the honest report rather than a second failure"),
    Mutant("multiplier.falls", "ref_arena", "the multiplier survives damage",
           (NO_MULT_FALL,)),
    Mutant("multiplier.falls", "ref_arena",
           "the multiplier lapses on a combo timer, and damage never touches it",
           MULT_DECAYS_ON_A_TIMER,
           notes="the second direction, and the one `NO_MULT_FALL` cannot ask about. "
                 "Removing the collapse leaves a multiplier that never moves after the "
                 "killing stops; this one moves for a reason that is not the damage, "
                 "and the criterion PASSED it while it compared the killing phase's "
                 "peak with the value on the hit tick - 459 idle ticks apart on this "
                 "fixture (`tasks/170`)"),
    Mutant("wall.graze", "ref_arena", "the boundary is never reported",
           (NO_GRAZE,)),
    Mutant("aim.three_axis", "ref_arena", "the depth axis is dropped from aim",
           (FLAT_AIM,), collateral=("multiplier.rises", "multiplier.falls"),
           notes="a gun that cannot point along z misses any enemy off the player's own "
                 "depth plane, so the killing streak the multiplier criteria have to "
                 "establish first mostly does not happen"),
    Mutant("player.bounded", "ref_arena", "the volume does not hold the player",
           (UNBOUNDED,), collateral=("wall.graze",)),
    Mutant("fire.rate_limited", "ref_arena", "a bullet every tick",
           (NO_RATE_LIMIT,)),
    Mutant("fire.rate_limited", "ref_arena",
           "a bullet every tick, with `fire` reported only on the rising edge",
           EDGE_EVENT_NO_RATE_LIMIT,
           notes="the negative control for reading BOTH signals. `_shot_ticks` takes "
                 "the larger of `fire` events and new-bullet ticks; this game reports 1 "
                 "and 120, so a criterion counting events alone would call it rate-"
                 "limited. Firing on the rising edge is legal on its own - it is the "
                 "recorded hazard for `fire.spawns_bullets` - and the missing interval "
                 "is what makes this a mutant"),
    Mutant("score.on_kill", "ref_arena", "a kill is worth nothing",
           (NO_SCORE,)),
    Mutant("player.takes_damage", "ref_arena", "enemies pass through the player",
           (NO_CONTACT_DAMAGE,), collateral=("gameover.triggers", "multiplier.falls",
                                             "enemies.chase")),
    Mutant("player.walks", "ref_platformer", "walking left is ignored",
           (PF_LEFT_IGNORED,), collateral=("player.bounded",)),
    Mutant("player.bounded", "ref_platformer", "the stage has no edges",
           (PF_UNBOUNDED,)),
    Mutant("player.falls", "ref_platformer", "gravity is zero",
           (PF_NO_GRAVITY,), collateral=("platform.lands", "jump.grounded_only",
                                         "knockback.applied", "enemy.damages_player",
                                         "invuln.window", "gameover.triggers",
                                         "attack.damages", "score.on_kill",
                                         "anim.states")),
    Mutant("platform.lands", "ref_platformer", "nothing ever lands on a platform",
           (PF_NO_LANDING,), collateral=("jump.leaves_ground", "jump.grounded_only",
                                         "anim.states", "attack.damages",
                                         "score.on_kill", "enemy.damages_player",
                                         "invuln.window", "knockback.applied",
                                         "gameover.triggers")),
    Mutant("jump.leaves_ground", "ref_platformer", "the jump input is ignored",
           (PF_NO_JUMP,), collateral=("jump.grounded_only", "anim.states",
                                      "platform.lands"),
           notes="platform.lands is collateral BY CONSTRUCTION and this is the price of "
                 "its repair: it now stages the fall by jumping, so a game that cannot "
                 "jump cannot be asked whether it lands. The alternative was walking off "
                 "a ledge and hoping a floor was underneath, which failed 5 of 6 real "
                 "submissions. The coupling is declared here rather than left as a "
                 "surprise, and the criterion says which failure it saw: its evidence "
                 "reads 'this is a jump failure, not a landing failure'"),
    Mutant("jump.grounded_only", "ref_platformer", "jump works in mid-air",
           (PF_AIR_JUMP,)),
    Mutant("attack.active_frames", "ref_platformer", "the hitbox is always live",
           (PF_ALWAYS_ACTIVE,),
           notes="a permanently active hitbox is pixel-identical to a real swing"),
    Mutant("attack.faces", "ref_platformer", "the hitbox never turns around",
           (PF_FIXED_SIDE,)),
    Mutant("attack.damages", "ref_platformer", "the swing connects with nothing",
           (PF_NO_HIT_DAMAGE,), collateral=("score.on_kill",)),
    Mutant("enemy.damages_player", "ref_platformer", "enemies are harmless",
           (PF_NO_CONTACT,), collateral=("invuln.window", "knockback.applied",
                                         "gameover.triggers")),
    Mutant("invuln.window", "ref_platformer", "no grace window after a hit",
           (PF_NO_INVULN,)),
    Mutant("knockback.applied", "ref_platformer", "no impulse when hurt",
           (PF_NO_KNOCKBACK,),
           notes="deleting the impulse leaves vx at 0, which an earlier version of the "
                 "criterion read as 'decreased, therefore knocked away'"),
    Mutant("anim.states", "ref_platformer", "one animation label for everything",
           (PF_ONE_ANIM,)),
    Mutant("anim.frames_advance", "ref_platformer", "the sprite frame never advances",
           (PF_FROZEN_FRAME,)),
    Mutant("score.on_kill", "ref_platformer", "a kill is worth nothing",
           (PF_NO_SCORE,)),
    Mutant("gameover.triggers", "ref_platformer", "zero health never ends the game",
           (PF_NEVER_ENDS,), collateral=("invuln.window",)),
    Mutant("match.ends", "ref_pong", "the match is won and the ball plays on",
           MATCH_PLAYS_ON,
           notes="the first mutant `match.ends` has ever had of its own; it appeared "
                 "only as collateral until 2026-08-25"),
    Mutant("gameover.triggers", "ref_arena",
           "game over is reported and the simulation keeps stepping",
           (ARENA_KEEPS_STEPPING,),
           notes="the score cannot express this - a dead player earns nothing - so "
                 "`_death` guards `kills` beside it. Measured: `(0, 3) -> (0, 4)` over "
                 "the idle window, against `(0, 3) -> (0, 3)` on the reference"),
    Mutant("gameover.triggers", "ref_platformer",
           "the run is over and the simulation keeps stepping",
           (PF_KEEPS_STEPPING,),
           notes="the one fixture where the score alone says it: `0 -> 200` over the "
                 "pressed window, because the corpse can still swing at an enemy"),
    Mutant("gameover.triggers", "ref_tetris3d",
           "the well stacked out and the game keeps stepping",
           (TETRIS_KEEPS_STEPPING,),
           notes="the score cannot express this either - a full well clears no layer - "
                 "so `_gameover_check` guards the well's filled-cell total. Measured "
                 "over 400 ticks of input: 199 `lock` events and `(0, 62) -> (0, 84)`, "
                 "with the score unchanged at 0"),
]


# --------------------------------------------------------------------------- #
# HAZARDS - one answer per criterion to "what correct game would mis-score this?"
# --------------------------------------------------------------------------- #
#
# THE POPULATION IS EVERY CRITERION, NOT THE SMALLER SET THAT CARRIES A MUTANT. A
# variant runs the whole bot on ONE fixture, so a variant on `ref_pong` says nothing
# about `ref_arena`: the subject count for a criterion is the number of variants on its
# OWN fixture. False negatives have been adjudicated here on criteria carrying no mutant
# at all, so a registry scoped to the mutated set would miss them. `--hazards` prints
# both counts and names the unmutated criteria; a figure typed here goes stale silently.
#
# Every entry names a SHAPE, so the question "does anything cover the shapes #46 names?"
# is a group-by rather than a memory. A shape with no `covered_by` anywhere is a gap.

SHAPES: dict[str, str] = {
    "opening-card": "the game withholds play at the start so its presentation can be "
                    "read (#34: OPENING_DELAY = 104)",
    "closing-card": "the game holds an end-of-game card and then takes a control as "
                    "the reset the prompt says it waits for",
    "late-unlock": "the property is gated behind progress the bot has to earn (#46: "
                   "four enemy kinds behind wave >= 2, 3 and 4)",
    "idle-is-fatal": "the bot's own default input ends the game before the measurement "
                     "completes (#46: enemies.chase measured a corpse)",
    "contract-reading": "a second legal reading of a state field (task 76: `active` as "
                        "the swing rather than the damaging window)",
    "world-geometry": "the level or the playfield has a shape the reference's does not "
                      "(a pit under the opening ledge; a piece flush against a wall)",
    "tuning": "the game's own constants put it in a regime the reference is not in, so "
              "a branch opens that the reference never takes (enemies faster than the "
              "player)",
    "design-branch": "a deliberate branch the reference does not have (#82: a pit "
                     "respawns instead of applying knockback)",
    "edge-vs-level": "the game acts on a rising edge where the reference acts on a held "
                     "control, or the reverse",
    "engine-session": "the engine refuses a second probe session on a project the first "
                      "still holds (#25, #29, #30)",
    "no-construction": "no correct game could be constructed - the property is the task "
                       "itself, and a game without it is incomplete rather than unusual",
}


@dataclass(frozen=True)
class Hazard:
    fixture: str
    criterion: str
    shape: str
    #: the correct-but-unusual game that would mis-score this criterion
    hazard: str
    #: how that hazard is answered today
    answer: str
    #: a `Variant.label` or a `Pending.label` on this fixture, or "" for neither
    covered_by: str = ""


_V_CARD = "a 104-tick opening title card holds the ball"
_V_FAST = "enemies faster than the player, so one reaches it mid-leg"
_V_SWING = "`active` spans the whole swing, hitbox only the middle"
_V_PIT = "the opening ledge overlooks a bottomless pit"
_V_PONG_RESTART = "a game-over card, then a control starts a new match"
_V_RESTART = "a game-over card, then a control starts a new run"
_V_TETRIS_RESTART = "a 190-tick game-over card, then a control restarts"
_V_ARENA_CARD = "a 96-tick opening title card holds the whole arena"
_V_FROZEN = "a 96-tick card over a frozen well"
_V_EMPTY = "a 96-tick card over an empty well"
_V_SPREAD = "a faster three-round spread weapon"
_V_DEFERRED_DROP = "the multiplier collapse lands the tick after the damage"

_SESSION = ("the three session-lock controls, which also pin that a permanently locked "
            "project comes back NOT MEASURED rather than FALSE")
_CONTRACT = ("no correct game constructed: this is the shape the probe protocol "
             "specifies, and a game reporting another one has not met the contract")

HAZARDS: list[Hazard] = [
    # -- ref_pong ---------------------------------------------------------- #
    Hazard("ref_pong", "state.shape", "no-construction",
           "a game that reports the ball, paddles, score and rally under other names",
           _CONTRACT),
    Hazard("ref_pong", "ball.moves", "opening-card",
           "a title card that holds the ball before the first serve",
           "the variant, plus a 512-tick budget that watches POSITION rather than "
           "velocity - the first repair used velocity as a proxy and still failed a "
           "Unity submission that sets the serve velocity at tick 1 and holds the ball",
           _V_CARD),
    Hazard("ref_pong", "ball.wall_bounce", "tuning",
           "a paddle that imparts angle only near its tips, so a small strike offset "
           "returns the ball flat and it never reaches a wall",
           "`_STRIKE_OFFSETS` searches six offsets, widening on a flat return and "
           "walking back on a conceded point, and returns NOT ESTABLISHED when no "
           "paddle return ever happened rather than scoring the serve angle"),
    Hazard("ref_pong", "paddle.moves", "tuning",
           "a paddle that accelerates rather than snapping to speed, so a fixed idle "
           "reads no displacement",
           "`_hold_until_still` runs up to 600 ticks and stops on convergence, not on "
           "a tick count: a slow paddle gets the ticks it needs"),
    Hazard("ref_pong", "paddle.bounded", "design-branch",
           "a paddle with an idle bob or a settle, whose y is never byte-constant at "
           "the limit and so never satisfies the 60-tick convergence test",
           "declined: the prompt puts all drawing in the view module and the probe "
           "reports the simulation, so a bob is not in this state. THE LINE IS WHETHER "
           "THE PRESENTATION GATES THE SIM - a title card does, a bob does not"),
    Hazard("ref_pong", "paddle.deflects", "idle-is-fatal",
           "a match that reaches eleven while the bot is setting something else up, "
           "freezing every criterion measured afterwards",
           "the play order is fixed and documented, and the paddle-mechanics phase runs "
           "last on its own session. Measured cost of the wrong order on the reference: "
           "five false negatives at once"),
    Hazard("ref_pong", "rally.counts", "contract-reading",
           "a sim that emits `paddle_hit` where the collision resolves and settles its "
           "counters in an end-of-tick pass, landing the increment one tick later",
           "DECLINED, tasks/159: that game is not correct. The task defines `rally` as "
           "the number of paddle hits since the last point, and all four starter guides "
           "put the tick's line AFTER its step - so a line carrying `paddle_hit` and a "
           "rally that excludes it contradicts itself. `bot_pong._rally` holds the "
           "derivation and now reports `rose_late` so the fail says WHICH way it read"),
    Hazard("ref_pong", "rally.resets", "contract-reading",
           "the same ordering at the point rather than at the hit",
           "the criterion ORs two independent observations - the reset seen during the "
           "rally drive and the one seen during the scoring drive - so one missed tick "
           "does not decide it"),
    Hazard("ref_pong", "score.increments", "tuning",
           "a game that plays a scoring beat before the counter moves",
           "the score is read from `s.last` after the serve check rather than on the "
           "event tick, so several ticks of delay are absorbed"),
    Hazard("ref_pong", "serve.resets", "opening-card",
           "a get-ready beat between the point and the serve, longer than the six ticks "
           "the criterion looks ahead",
           "measured green: a 40-tick beat with the ball held at the centre passes, "
           "because the test is |x| < 60 and a held ball IS at the centre. It would "
           "fail a game that parks the ball off-centre during the beat, which is a "
           "shape no submission has shipped"),
    Hazard("ref_pong", "match.ends", "closing-card",
           "a game-over card that a control clears into a new match",
           "the variant, which is the shape `g1_pong__rust` shipped. The criterion "
           "idles 600 ticks after the win and only then presses, reading the pressed "
           "phase THROUGH the reset via `probe.end_condition_holds`",
           _V_PONG_RESTART),
    Hazard("ref_pong", "determinism.replay", "engine-session",
           "an engine that refuses a second probe session", _SESSION),
    Hazard("ref_pong", "determinism.seed", "engine-session",
           "an engine that refuses a second probe session", _SESSION),

    # -- ref_tetris3d ------------------------------------------------------- #
    Hazard("ref_tetris3d", "state.shape", "no-construction",
           "a game that reports the well, piece and heights under other names",
           _CONTRACT),
    Hazard("ref_tetris3d", "well.dimensions", "no-construction",
           "a well that is not 5 x 5 x 12",
           "no correct game constructed: the prompt fixes the geometry, so a different "
           "well is a spec miss rather than an unusual correct game"),
    Hazard("ref_tetris3d", "piece.spawns", "opening-card",
           "a title card, a next-piece beat or a materialise animation before the first "
           "piece appears at all",
           "the variant, plus `bot_tetris3d.OPENING_BUDGET`: the await was 20 ticks and "
           "the boundary was exact, an 18-tick card passing and a 21-tick one failing, "
           "so a beat between LATER pieces passed on 60 while the OPENING failed. Now "
           "512 at tick 0 and `MIDGAME_AWAIT` after (`tasks/158`)", _V_EMPTY),
    Hazard("ref_tetris3d", "piece.falls", "opening-card",
           "a title card that holds the well before the first piece descends",
           "the variant, plus `bot_tetris3d.OPENING_BUDGET`: 120 ticks against a fall "
           "interval of 48 was a quarter of the 512 the same shape bought pong and the "
           "platformer, and it read `lowest cell height went from 11 to 11 without "
           "input` on a correct game (`tasks/158`)", _V_FROZEN),
    Hazard("ref_tetris3d", "piece.locks", "tuning",
           "a game with a lock delay, so the `lock` event lands well after the piece "
           "reaches the bottom",
           "the criterion steps up to 600 ticks waiting for the first lock, and it "
           "measures the FIRST lock of a fresh game, where no layer can be complete and "
           "so `settled` cannot fall instead of rising"),
    Hazard("ref_tetris3d", "bounds.respected", "world-geometry",
           "a wall kick that pushes a rotating piece one cell outside the well for the "
           "tick the rotation resolves",
           "correct to fail: the prompt says a rotation that would leave the well simply "
           "does not happen, so the excursion is the defect. The criterion samples every "
           "tick of the move and rotate drives rather than the endpoints"),
    Hazard("ref_tetris3d", "move.translates", "world-geometry",
           "a piece that spawns flush against a wall, so refusing the move is correct",
           "REPAIRED and pinned (#29, `g2_tetris3d__rust__t0`): the direction comes from "
           "the piece's own cells and the well, every direction with clearance is tried, "
           "and a piece spanning both horizontal axes returns NOT MEASURED"),
    Hazard("ref_tetris3d", "rotate.reorients", "edge-vs-level",
           "a game that rotates on the rising edge, so a held control rotates once",
           "the criterion presses for a single tick at a time across nine attempts on "
           "fresh pieces, and `_drop` guarantees a falling edge before every press"),
    Hazard("ref_tetris3d", "harddrop.locks", "tuning",
           "a lock delay after the slam, so the lock lands later than the two ticks the "
           "criterion allows",
           "declined: the prompt defines hard_drop as 'drop straight down and lock "
           "immediately', so a delay is a spec miss rather than a design choice"),
    Hazard("ref_tetris3d", "piece.stacks", "tuning",
           "a game that clears layers as fast as the bot stacks them, so the maximum "
           "column height never rises",
           "the criterion accepts either a higher stack OR a non-zero `layers_cleared`. "
           "It opens its OWN session, so an opening card gates it a second time: that "
           "first await is `bot_tetris3d.OPENING_BUDGET` rather than `MIDGAME_AWAIT`, "
           "which is what the empty-well variant reads (`tasks/158`)"),
    Hazard("ref_tetris3d", "layer.clears", "late-unlock",
           "any correct game: the placement policy cannot fill a 25-cell layer out of "
           "four-cell pieces",
           "DIAGNOSTIC ONLY for exactly that reason, measured across three seeds, two "
           "well geometries and five placement cost functions"),
    Hazard("ref_tetris3d", "score.rewards_clears", "late-unlock",
           "the same: the reward cannot be seen without a clear",
           "DIAGNOSTIC ONLY, with `layer.clears`"),
    Hazard("ref_tetris3d", "gameover.triggers", "closing-card",
           "a game-over card that a control clears into a new run",
           "the variant, and its card is 190 ticks for a reason. At 96 this fixture "
           "PASSED the unrepaired bot - the run restarted and stacked out AGAIN inside "
           "the 200-tick input window, and the restart's own score reset satisfied the "
           "frozen test - so the verdict was a function of the card length rather than "
           "of the game, and only the longer card can tell a repair from the luck. "
           "`_gameover_check` now goes through `probe.end_condition_holds`",
           _V_TETRIS_RESTART),
    Hazard("ref_tetris3d", "determinism.replay", "engine-session",
           "an engine that refuses a second probe session", _SESSION),
    Hazard("ref_tetris3d", "determinism.seed", "engine-session",
           "an engine that refuses a second probe session", _SESSION),

    # -- ref_arena ---------------------------------------------------------- #
    Hazard("ref_arena", "state.shape", "no-construction",
           "a game that reports the arena, player, enemies and bullets under other "
           "names", _CONTRACT),
    Hazard("ref_arena", "player.moves", "opening-card",
           "a title card, a countdown or a wave-1 announcement that holds the arena "
           "before the player can be walked at all",
           "the variant, plus `bot_arena.OPENING_BUDGET`: the criterion reads a 30-tick "
           "push, so the boundary was exact - a 29-tick card passed and a 30-tick one "
           "failed, on a game this bot had no opening wait for anywhere. Every session "
           "now opens with `_take_control`, which steps up to 512 ticks until the "
           "player answers a movement input (`tasks/173`). The other reading of the "
           "criterion is unchanged: the reference travels ~130 units in its 30 ticks, "
           "so the 2-unit floor is two orders of magnitude below it and only a "
           "near-immobile player fails it on speed", _V_ARENA_CARD),
    Hazard("ref_arena", "move.analog", "design-branch",
           "a deadzone above half the stick range, which rounds a half push to nothing "
           "and lands outside the 0.25-0.75 band",
           "declined: the prompt gives the movement axes as a continuous -1.0..1.0 "
           "vector, so a deadzone eating half of it is the control defect this criterion "
           "exists to catch"),
    Hazard("ref_arena", "player.bounded", "world-geometry",
           "an arena whose half-extents differ per axis, so a corner push reaches one "
           "wall long before another",
           "the criterion reads `half_x/half_y/half_z` out of the game's own state "
           "rather than assuming a cube, and asks only for half the extent on each axis"),
    Hazard("ref_arena", "wall.graze", "design-branch",
           "a game that raises `wall_graze` as the player is pushed off the boundary "
           "rather than as it arrives",
           "the criterion presses into the corner for 900 ticks and asks only whether "
           "the event ever fired, so any moment of the contact satisfies it"),
    Hazard("ref_arena", "enemies.spawn", "opening-card",
           "a wave announcement that plays before the enemies appear, beyond the 300 "
           "ticks the criterion waits",
           "the variant, plus `bot_arena.OPENING_BUDGET`: the 300 ticks are counted "
           "from the end of `_take_control` rather than from the session's tick 0, so a "
           "card is no longer spent out of them. Measured before that: the wait ran out "
           "at a 390-tick card, which is 6.1 seconds against the 96 the platformer "
           "reference holds and the 104 that bought pong its budget (`tasks/173`)",
           _V_ARENA_CARD),
    Hazard("ref_arena", "enemy.kinds", "late-unlock",
           "four kinds gated behind wave >= 2, wave >= 3 and wave >= 4, which is what "
           "all six adjudicated submissions shipped (#46)",
           "covered by the REFERENCE, which #46 changed to unlock at waves 1, 2 and 3. "
           "That is the strongest form of variant coverage available: every arena "
           "criterion now runs against a late unlock on every run, not only this one"),
    Hazard("ref_arena", "enemy.materialises", "tuning",
           "a materialise window so short that the enemy is active again before the "
           "bot's first bullet reaches it",
           "the criterion follows the enemy BY ID and counts hits only while its own "
           "`spawning` flag is set, so the window's length cannot decide it; a window "
           "of zero ticks is the mutant"),
    Hazard("ref_arena", "enemies.chase", "tuning",
           "enemies faster than the player, so the tracked one reaches it mid-leg - the "
           "branch that raised KeyError and fail-closed a whole submission to 0.000",
           "the variant, plus one constructor for every leg exit so no exit can carry a "
           "different shape", _V_FAST),
    Hazard("ref_arena", "fire.spawns_bullets", "edge-vs-level",
           "a game that fires on the rising edge, so 120 ticks of held fire produce one "
           "bullet",
           "one bullet is enough: the criterion asks for any bullet with a speed above "
           "1.0, and the interval question belongs to `fire.rate_limited`"),
    Hazard("ref_arena", "fire.rate_limited", "design-branch",
           "a spread weapon, which puts several bullets in the world per shot",
           "the criterion counts SHOOTING TICKS, so a spread of three bullets on one "
           "tick is one shot; the variant measures it. What this does NOT answer is a "
           "game that emits `fire` on every held tick regardless of its own cooldown - "
           "that reads as 120 shots and goes red - and such a game contradicts the "
           "event's stated meaning, `the player fired a shot this tick`", _V_SPREAD),
    Hazard("ref_arena", "aim.independent", "no-construction",
           "a game that ties the firing direction to the movement direction",
           "no correct game constructed: the prompt specifies separate move and aim "
           "vectors, so coupling them is the defect this criterion exists to catch"),
    Hazard("ref_arena", "aim.three_axis", "world-geometry",
           "an arena shallow enough on the depth axis that a bullet leaves it inside "
           "the tick it is created and never appears in a snapshot",
           "the bot moves along -y in every firing phase for exactly this reason - "
           "measured once as 'the game cannot aim upward' on a correct implementation"),
    Hazard("ref_arena", "bullets.kill", "tuning",
           "an enemy with enough health that the bot's kiting fire never finishes one",
           "the combat session runs up to 9000 ticks and stops early only once a kill, "
           "a wave and a multiplier step have all been seen"),
    Hazard("ref_arena", "score.on_kill", "design-branch",
           "a game that banks the score and awards it at the end of the wave",
           "OPEN, and not constructed. The criterion needs the score to rise ON a kill "
           "tick; end-of-wave banking is a real arcade design and nothing here tests it. "
           "Left open rather than guessed at: no stored submission has shipped it"),
    Hazard("ref_arena", "multiplier.rises", "late-unlock",
           "a multiplier needing more kills per step than the bot achieves before it "
           "dies",
           "the criterion plays with the standoff policy - which closes as well as runs, "
           "because unconditional retreat once stalled the bot one kill short of a wave "
           "- and reports the wave and kill counts so a failure to establish reads "
           "differently from a defect"),
    Hazard("ref_arena", "multiplier.falls", "contract-reading",
           "a game that drops the multiplier on the tick AFTER the hit, the same "
           "ordering as `rally.counts`",
           "CONSTRUCTED and PASSING, as the variant. `tasks/159` declined this ordering "
           "for pong because g1 DEFINES `rally` as a count of the events the tick line "
           "carries; g3 defines `multiplier` nowhere, so the tick is free and the "
           "criterion now reads the damage tick AND the 8 ticks after it, taking the "
           "first of those 9 on which the multiplier moves. What it compares moved with "
           "it: the baseline "
           "is the value on the tick BEFORE the damage, never the killing phase's peak, "
           "which is 459 idle ticks earlier on this fixture. A multiplier that lapses "
           "on a combo timer and ignores damage entirely PASSED the old pairing with "
           "evidence byte-identical to the reference's, and is now the mutant `the "
           "multiplier lapses on a combo timer, and damage never touches it`. WHAT IS "
           "STILL OPEN is that game made correct - both a combo timer AND a collapse on "
           "damage - if the timer lapses inside that window. Bounded rather than "
           "closed: the span it could land in was 459 ticks wide and is 9, and a "
           "timer that lapses before the hit is now caught outright. Closing it needs a "
           "second hit to compare against, and the multiplier is at 1 by then",
           _V_DEFERRED_DROP),
    Hazard("ref_arena", "wave.advances", "design-branch",
           "a wave that ends on a timer rather than on the last kill",
           "the criterion asks only that the wave number rose, by any mechanism"),
    Hazard("ref_arena", "player.takes_damage", "idle-is-fatal",
           "a game where standing still is SURVIVABLE, so 9000 idle ticks produce no "
           "hit - the inverse of #46, where standing still was fatal",
           "the criterion reports the hit count and the health beside the verdict, so "
           "'the player was never reached' is legible; a game that never damages an "
           "idle player in 9000 ticks has not met the prompt's patrol behaviour"),
    Hazard("ref_arena", "gameover.triggers", "closing-card",
           "a game-over card that a control clears into a new run",
           "the variant. `_death` used to press fire, aim and move straight after "
           "the player died, which pressed this game's own reset and then read "
           "the fresh run as a failure to end. It now goes through "
           "`probe.end_condition_holds`, which idles first and reads the pressed "
           "phase THROUGH the reset", _V_RESTART),
    Hazard("ref_arena", "determinism.replay", "engine-session",
           "an engine that refuses a second probe session", _SESSION),
    Hazard("ref_arena", "determinism.seed", "engine-session",
           "an engine that refuses a second probe session", _SESSION),

    # -- ref_platformer ----------------------------------------------------- #
    Hazard("ref_platformer", "state.shape", "no-construction",
           "a game that reports the level, player, attack and platforms under other "
           "names", _CONTRACT),
    Hazard("ref_platformer", "player.walks", "opening-card",
           "a title card before control is handed over",
           "`_take_control` waits up to 512 ticks, which is the pong repair carried "
           "across - and the reference itself ships `OPENING_TICKS = 96`, so every "
           "platformer criterion already runs behind a card on every run"),
    Hazard("ref_platformer", "player.bounded", "world-geometry",
           "a stage whose edge is a wall the character collides with rather than a "
           "coordinate clamp",
           "the criterion asks only that x stops changing while the control is held, "
           "which both designs satisfy"),
    Hazard("ref_platformer", "player.falls", "world-geometry",
           "an opening ledge over a pit, which is what an opening ledge is for and what "
           "five of six wg-g4c submissions shipped",
           "the variant, plus a repaired criterion that jumps and lands on the platform "
           "underfoot rather than walking off and hoping", _V_PIT),
    Hazard("ref_platformer", "platform.lands", "world-geometry",
           "the same pit: nothing under the start ledge to land on",
           "the variant. The repair is why `platform.lands` is now collateral of the "
           "`jump.leaves_ground` mutant BY CONSTRUCTION, which is declared rather than "
           "left as a surprise", _V_PIT),
    Hazard("ref_platformer", "jump.leaves_ground", "tuning",
           "a jump with a windup, so the character is still grounded for several ticks "
           "after the press",
           "the criterion watches height rather than the tick of the press, over a "
           "budget that outlasts a windup"),
    Hazard("ref_platformer", "jump.grounded_only", "design-branch",
           "coyote time - a short grace window after walking off a ledge, which is "
           "standard platformer feel and which the prompt's 'the feel of the jump is "
           "the game' invites",
           "measured green: a six-tick coyote window passes every criterion. The "
           "criterion asks whether a SECOND jump is refused before landing, and a "
           "coyote window does not grant one"),
    Hazard("ref_platformer", "attack.active_frames", "contract-reading",
           "`active` meaning a swing is in progress while the hitbox is live only in "
           "the middle - the reading `g4_platformer__unity__t0` took, and a legal one",
           "the variant. The reference sets the two to the same tick set, so no fixture "
           "without this variant can tell them apart", _V_SWING),
    Hazard("ref_platformer", "attack.faces", "contract-reading",
           "the same reading: sampling the hitbox on every active tick reads the empty "
           "rectangle's centre (0, 0) as a position and scores -61.7",
           "the variant", _V_SWING),
    Hazard("ref_platformer", "attack.damages", "world-geometry",
           "a pit between the character and the nearest enemy",
           "the variant, plus one shared `_walk_toward` that jumps a gap seen through "
           "`_edge_distance` before entering it", _V_PIT),
    Hazard("ref_platformer", "enemy.damages_player", "world-geometry",
           "the same pit, in the loop whose whole experiment is making contact",
           "the variant. This is the criterion that read '0 player_hit events over 4097 "
           "ticks' while `attack.damages` passed, because only two of three copies of "
           "'walk toward the target' had learned to jump (task 76)", _V_PIT),
    Hazard("ref_platformer", "invuln.window", "world-geometry",
           "the same pit: no enemy contact means no two hits to measure a gap between",
           "the variant, and the criterion says 'the window could not be measured' "
           "rather than 'there is no window'", _V_PIT),
    Hazard("ref_platformer", "knockback.applied", "design-branch",
           "a pit that puts the character back on the last wide platform instead of "
           "applying an impulse, which is what `g4_platformer__unity__t0` does (#82)",
           "the criterion samples only hits with an enemy within 40 units and no "
           "position jump, and reports NOT MEASURED when no enemy hit landed - the one "
           "criterion here that is unscored rather than false on a real submission",
           _V_PIT),
    Hazard("ref_platformer", "anim.states", "contract-reading",
           "a game whose animation labels are stack-native strings this criterion does "
           "not know",
           "the criterion counts DISTINCT labels across standing, walking, airborne and "
           "swinging rather than matching names, so any vocabulary passes"),
    Hazard("ref_platformer", "anim.frames_advance", "tuning",
           "an animation slow enough that a short walk shows a single frame",
           "OPEN, and not constructed. The criterion walks for `_WALK_TICKS` = 40, so a "
           "sheet advancing every 40-odd ticks would fail. No stored submission is "
           "anywhere near that, and the prompt asks for a frame-indexed sprite"),
    Hazard("ref_platformer", "score.on_kill", "world-geometry",
           "the same pit: no kill means no score tick to read",
           "the variant, and the criterion distinguishes 'no kill was observed' from "
           "'the score did not rise'", _V_PIT),
    Hazard("ref_platformer", "gameover.triggers", "closing-card",
           "a game-over card that a control clears into a new run",
           "the variant. `_hurt` used to press move_right, jump and attack "
           "straight after the player died; it now goes through "
           "`probe.end_condition_holds`", _V_RESTART),
    Hazard("ref_platformer", "stage.completes", "late-unlock",
           "any correct stage the bot cannot cross end to end",
           "DIAGNOSTIC ONLY, and the reason a variant must read `Bot.diagnostic_only` "
           "rather than counting an unscored criterion as an escape"),
    Hazard("ref_platformer", "determinism.replay", "engine-session",
           "an engine that refuses a second probe session", _SESSION),
    Hazard("ref_platformer", "determinism.seed", "engine-session",
           "an engine that refuses a second probe session", _SESSION),
]


# --------------------------------------------------------------------------- #
# Running
# --------------------------------------------------------------------------- #


# --------------------------------------------------------------------------- #
# The session-lock family, which has no mutant because it is not a game defect
# --------------------------------------------------------------------------- #

# `determinism.replay`, `determinism.seed`, `piece.stacks` and `gameover.triggers` each
# open a FRESH probe session, and eleven of the sixteen adjudicated false negatives were
# those four criteria scoring FALSE because the engine refused the second session. That
# is not something a mutant of the game can express - the defect was in the harness - so
# it is pinned with a fixture that behaves the way Unity does: one live probe per
# project directory, and a second one refused by name.
LOCK_WRAPPER = """#!/usr/bin/env bash
# Stands in for an engine that takes a project-wide lock. One live probe per directory;
# a second one is refused with Unity's own wording.
set -u
LOCK="$PWD/.project-lock"
if ! mkdir "$LOCK" 2>/dev/null; then
  echo "It looks like another Unity instance is running with this project open." >&2
  echo "Multiple Unity instances cannot open the same project." >&2
  exit 1
fi
trap 'rmdir "$LOCK" 2>/dev/null || true' EXIT INT TERM
python3 probe.py "$1"
"""

ALWAYS_LOCKED = """#!/usr/bin/env bash
# A project this grader can never open: every session is refused.
echo "It looks like another Unity instance is running with this project open." >&2
echo "Multiple Unity instances cannot open the same project." >&2
exit 1
"""

#: the criteria that open a session of their own, per game
SIBLING_SESSION_CRITERIA = ("determinism.replay", "determinism.seed")


def _locking_fixture(dest: Path, script: str) -> Path:
    repo = _copy_fixture("ref_pong", dest)
    (repo / "lockprobe.sh").write_text(script)
    jf = repo / "justfile"
    text = jf.read_text()
    old = "probe SEED:\n    @python3 probe.py {{SEED}}"
    if text.count(old) != 1:
        raise SystemExit(f"the ref_pong justfile no longer contains {old!r}")
    jf.write_text(text.replace(old, "probe SEED:\n    @bash lockprobe.sh {{SEED}}"))
    return repo


def live_criteria(fixture: str) -> list[str]:
    """The criterion ids this fixture's bot actually reports, read from the bot."""
    return [cid for cid, _q in __import__(BOT_FOR[fixture]).BOT.criteria]


def hazard_gate() -> list[str]:
    """Offline: does every criterion have an answer, and does every answer resolve?

    The registry is only worth having if it cannot drift from the bots. A criterion
    added without a hazard entry is the state this whole file was written to find, and
    a `covered_by` naming a variant that was renamed is a citation that still reads
    like coverage (`AGENTS.md`, the renaming rule).
    """
    problems: list[str] = []
    by_key = {(h.fixture, h.criterion): h for h in HAZARDS}
    if len(by_key) != len(HAZARDS):
        problems.append("HAZARDS has duplicate (fixture, criterion) keys")
    for fixture in sorted(BOT_FOR):
        live = set(live_criteria(fixture))
        mine = {c for f, c in by_key if f == fixture}
        for missing in sorted(live - mine):
            problems.append(
                f"hazards: {fixture}/{missing} has no entry. Every criterion needs an "
                f"answer to 'what correct-but-unusual game would mis-score this?', and "
                f"'nobody could construct one' is an answer - see SHAPES['no-construction']")
        for stale in sorted(mine - live):
            problems.append(f"hazards: {fixture}/{stale} is not a criterion any more")

    labels = {(v.fixture, v.label) for v in VARIANTS}
    labels |= {(p.fixture, p.label) for p in PENDING_VARIANTS}
    for h in HAZARDS:
        if h.shape not in SHAPES:
            problems.append(f"hazards: {h.fixture}/{h.criterion} names shape "
                            f"{h.shape!r}, which SHAPES does not define")
        if h.covered_by and (h.fixture, h.covered_by) not in labels:
            problems.append(
                f"hazards: {h.fixture}/{h.criterion} is covered_by "
                f"{h.covered_by!r}, and no variant or pending entry on that fixture "
                f"carries that label")
    claimed = {(h.fixture, h.covered_by) for h in HAZARDS if h.covered_by}
    for fixture, label in sorted(labels - claimed):
        problems.append(
            f"hazards: the {fixture} subject {label!r} is claimed by no criterion. A "
            f"variant exists to encode a specific way a correct game can differ; one "
            f"no criterion points at was written to raise a count")
    return problems


def hazard_census() -> None:
    """Print the registry grouped by shape - the answer to 'what covers #46's shapes?'

    A shape with no variant or pending subject is NOT automatically a gap: three of them
    are answered by machinery a variant cannot be, and each row's `answer` says which.
    The session-lock family is pinned by `lock_controls`, `late-unlock` by the reference
    itself since #46 changed it to unlock enemy kinds by wave, and `no-construction` is
    the finding that nobody could build a correct game that fails the criterion.
    """
    def wrap(text: str, tag: str) -> None:
        for i, line in enumerate(textwrap.wrap(text, 84)):
            print(f"       {tag if i == 0 else '':<8}{line}")

    mutated = {(m.fixture, m.criterion) for m in MUTANTS}
    declared = {(p.fixture, c) for p in PENDING_VARIANTS for c in p.fails}
    unmutated = sorted(declared - mutated)
    print(f"{len(HAZARDS)} criteria across {len(BOT_FOR)} fixtures; "
          f"{len(VARIANTS)} variants, {len(PENDING_VARIANTS)} pending entries")
    print(f"{len(mutated)} of those criteria carry a mutant. "
          f"{len(declared)} declared false negatives, of which {len(unmutated)} sit on "
          f"a criterion with no mutant at all"
          + (f": {', '.join(f'{f}/{c}' for f, c in unmutated)}" if unmutated else ""))
    for shape, meaning in SHAPES.items():
        rows = sorted((h for h in HAZARDS if h.shape == shape),
                      key=lambda r: (r.fixture, r.criterion))
        covered = sum(1 for h in rows if h.covered_by)
        print(f"\n\n== {shape}  ({covered} of {len(rows)} with a subject)\n   {meaning}")
        for h in rows:
            mark = f"   <- {h.covered_by}" if h.covered_by else ""
            print(f"\n   {h.fixture}/{h.criterion}{mark}")
            wrap(h.hazard, "hazard:")
            wrap(h.answer, "answer:")
    bare = sorted({h.shape for h in HAZARDS}
                  - {h.shape for h in HAZARDS if h.covered_by})
    print(f"\n\nshapes with no VARIANT or PENDING subject: {bare or 'none'}\n"
          f"read those rows' `answer` before calling one a gap")


def adjudicate_pending(p: "Pending", bad: list[str]) -> tuple[bool, str, str]:
    """Read one pending subject's measured failing set. Returns (ok, cell, problem).

    Three outcomes and they are not the same claim. `bad == p.fails` is the declared
    false negative still standing. An EMPTY set means the criterion was repaired and the
    subject is now an ordinary variant, which is a red row on purpose: the entry has to
    move, and nothing else would make that happen. Any other set means the defect
    changed shape, and a declared waiver that changed shape is not a waiver any more.
    """
    got, want = sorted(set(bad)), sorted(set(p.fails))
    if got == want:
        return True, f"still red, as declared ({p.task})", ""
    if not got:
        return False, "REPAIRED - promote it into VARIANTS", (
            f"pending '{p.label}' on {p.fixture} passes every criterion now. The "
            f"criterion it was declared against was repaired, so this is an ordinary "
            f"variant: move it into VARIANTS with its `exercises` set to {want}.")
    return False, f"MOVED: declared {want}, got {got}", (
        f"pending '{p.label}' on {p.fixture}: declared failing set {want}, measured "
        f"{got}. A declared false negative that changed shape is not a waiver any "
        f"more; re-adjudicate it against {p.task}.")


@dataclass
class Verdicts:
    passed: dict[str, bool] = field(default_factory=dict)
    scored: dict[str, bool] = field(default_factory=dict)
    evidence: dict[str, str] = field(default_factory=dict)
    wall_s: float = 0.0


def _copy_fixture(name: str, dest: Path) -> Path:
    shutil.copytree(FIXTURES / name, dest,
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    return dest


def _apply(repo: Path, patches: tuple[tuple[str, str], ...], label: str) -> None:
    game = repo / "game.py"
    text = game.read_text()
    for old, new in patches:
        n = text.count(old)
        if n != 1:
            raise SystemExit(
                f"mutant {label!r}: its target appears {n} times in {game}, expected "
                f"exactly 1. The fixture has changed and this mutant no longer bites; "
                f"a mutation test that silently fails to mutate is worse than none.\n"
                f"--- target ---\n{old}")
        text = text.replace(old, new)
    game.write_text(text)


def unmet(got: Verdicts, fixture: str, tolerates: tuple[str, ...] = ()) -> list[str]:
    """What a CORRECT game failed or left unscored, minus the declared waivers.

    A criterion that is `diagnostic_only` reports `scored=False` BY DESIGN, so counting
    it as "came back unscored" would fail every subject on a fixture that has one. That
    is what `stage.completes` did here, and the first response was to list it in a
    variant's `tolerates` -- which would have buried a harness bug inside the one field
    allowed to excuse failures. Rule 7: every reason not to count a failure is a channel
    a bug can widen, so the design intent is read from the bot rather than waived.

    One copy, because `Variant` and `Pending` both need it and two similar policies in
    one file is how #100 came back.

    DEDUPLICATED, because a criterion can be both. `passed=False, scored=False` is a
    reachable state - the fail-closed path on an unusable probe session sets it - and
    concatenating the two lists printed that criterion twice in a variant's `UNMET`
    row. `adjudicate_pending` took a `set` and was unaffected, so the defect lived
    only where a person reads the output. Raised by CodeRabbit on PR #38.
    """
    diagnostic = getattr(__import__(BOT_FOR[fixture]).BOT,
                         "diagnostic_only", frozenset())
    waived = set(tolerates) | set(diagnostic)
    bad = {cid for cid, ok in got.passed.items() if not ok and cid not in waived}
    bad |= {cid for cid, sc in got.scored.items() if not sc and cid not in waived}
    return sorted(bad)


def run_bot(repo: Path, fixture: str) -> Verdicts:
    mod = __import__(BOT_FOR[fixture])
    t0 = time.monotonic()
    out = probe.drive(mod.BOT, repo)
    v = Verdicts(wall_s=round(time.monotonic() - t0, 1))
    for c in out["criteria"]:
        v.passed[c["id"]] = bool(c["passed"])
        v.scored[c["id"]] = bool(c["scored"])
        v.evidence[c["id"]] = c.get("evidence", "")
    return v


# --------------------------------------------------------------------------- #


def lock_controls(tmp: Path, problems: list[str]) -> list[tuple[str, str, str]]:
    """Three controls for the session-lock repair. Returns rows for the report."""
    rows: list[tuple[str, str, str]] = []

    # (1) POSITIVE: an engine that allows one session at a time must score full marks,
    #     including the criteria that open sibling sessions.
    repo = _locking_fixture(tmp / "lock-serialised", LOCK_WRAPPER)
    v = run_bot(repo, "ref_pong")
    failed = sorted(cid for cid, ok in v.passed.items() if not ok)
    rows.append(("one live session per project, second refused",
                 "every criterion passes",
                 "ok" if not failed else f"UNMET: {failed}"))
    if failed:
        problems.append(
            f"lock control: a project that permits one session at a time still failed "
            f"{failed} -- {'; '.join(v.evidence[c][:200] for c in failed[:2])}")

    # (2) NEGATIVE CONTROL FOR THE CONTROL. (1) is only meaningful if it would notice
    #     the serialisation being gone, so take it away and check it goes red. Without
    #     this, (1) proves nothing: the fixture might simply never have conflicted.
    original = probe.ProbeSession._claim_repo
    probe.ProbeSession._claim_repo = lambda self: None            # type: ignore[method-assign]
    try:
        repo = _locking_fixture(tmp / "lock-unserialised", LOCK_WRAPPER)
        v = run_bot(repo, "ref_pong")
    finally:
        probe.ProbeSession._claim_repo = original                 # type: ignore[method-assign]
    sib = [cid for cid in SIBLING_SESSION_CRITERIA if v.passed.get(cid) is not False]
    rows.append(("...with session serialisation removed",
                 "the sibling-session criteria go red",
                 "ok" if not sib else f"UNMET: {sib} did not fail"))
    if sib:
        problems.append(
            f"lock control: with `_claim_repo` disabled, {sib} still passed against a "
            f"project that refuses concurrent sessions. The positive control above is "
            f"therefore vacuous - it is not exercising the repair.")

    # (3) A project that can NEVER be opened must come back unscored, not zero. Scoring
    #     it FALSE is precisely FINDINGS #25: a deduction that can only land on the
    #     stacks that lock their projects.
    repo = _locking_fixture(tmp / "lock-permanent", ALWAYS_LOCKED)
    v = run_bot(repo, "ref_pong")
    scored = sorted(cid for cid, sc in v.scored.items() if sc)
    rows.append(("every session refused, forever",
                 "every criterion NOT MEASURED, not FALSE",
                 "ok" if not scored else f"UNMET: {scored} were scored"))
    if scored:
        problems.append(
            f"lock control: a permanently locked project scored {scored} as failures. "
            f"A lock conflict measures nothing about the submission and must not "
            f"deduct (FINDINGS #25).")
    return rows


def selftest() -> int:
    """Offline: can the registry gate and the pending adjudication FAIL?

    `hazard_gate` and `adjudicate_pending` are checks like any other here, so each is
    mutated and must go red. A registry gate that cannot fail would report a complete
    per-criterion census of a file that had drifted out from under it, which is the
    shape this whole suite exists to prevent - and it costs no subprocess to pin.
    """
    rows: list[tuple[str, str, str]] = []
    problems: list[str] = []

    def expect(name: str, want: str, got: str) -> None:
        rows.append((name, want, "ok" if want == got else f"UNMET: {got}"))
        if want != got:
            problems.append(f"selftest {name}: expected {want}, got {got}")

    def n_problems(**patch) -> int:
        """`hazard_gate()` with module state temporarily replaced."""
        saved = {k: globals()[k] for k in patch}
        globals().update(patch)
        try:
            return len(hazard_gate())
        finally:
            globals().update(saved)

    expect("the registry is clean as shipped", "0", str(len(hazard_gate())))

    h = HAZARDS[0]
    expect("a criterion with no entry", "1",
           str(n_problems(HAZARDS=[x for x in HAZARDS if x is not h])))
    expect("a duplicated (fixture, criterion)", "1",
           str(n_problems(HAZARDS=HAZARDS + [h])))
    expect("covered_by naming nothing", "1",
           str(n_problems(HAZARDS=[replace(x, covered_by="no such subject")
                                   if x is h else x for x in HAZARDS])))
    # The label really exists - on ANOTHER fixture. A registry keyed on the label alone
    # would call this covered, and a variant only ever runs on its own fixture.
    other = next(v.label for v in VARIANTS if v.fixture != h.fixture)
    expect("covered_by naming a subject on another fixture", "1",
           str(n_problems(HAZARDS=[replace(x, covered_by=other) if x is h else x
                                   for x in HAZARDS])))
    expect("a shape SHAPES does not define", "1",
           str(n_problems(HAZARDS=[replace(x, shape="invented") if x is h else x
                                   for x in HAZARDS])))
    orphan = Variant(h.fixture, "a subject nobody points at", (), ())
    expect("a subject no criterion claims", "1",
           str(n_problems(VARIANTS=VARIANTS + [orphan])))

    # A SYNTHETIC subject, never `PENDING_VARIANTS[0]`. The list is empty whenever every
    # declared false negative has been repaired, and a selftest that borrows its subject
    # from live data stops running exactly then - silently, at exit 0, which is the
    # shape this file exists to prevent.
    p = Pending("ref_arena", "a synthetic pending, for this selftest only", (),
                ("some.criterion",), task="none")
    expect("a pending that still fails what it declared", "ok",
           "ok" if adjudicate_pending(p, list(p.fails))[0] else "red")
    expect("a pending that passes everything", "red",
           "ok" if adjudicate_pending(p, [])[0] else "red")
    expect("a pending that fails something else", "red",
           "ok" if adjudicate_pending(p, ["some.other"])[0] else "red")

    # `unmet` must waive a criterion the BOT calls diagnostic, and nothing else.
    diag = Verdicts(passed={"stage.completes": False}, scored={"stage.completes": False})
    expect("unmet waives a diagnostic-only criterion", "[]",
           str(unmet(diag, "ref_platformer")))
    real = Verdicts(passed={"player.walks": False}, scored={"player.walks": True})
    expect("unmet counts an ordinary one", "['player.walks']",
           str(unmet(real, "ref_platformer")))
    # The row that catches the concatenation this replaced: a criterion the fail-closed
    # path marks failed AND unscored appeared twice in a variant's UNMET line.
    both = Verdicts(passed={"player.walks": False}, scored={"player.walks": False})
    expect("unmet names a failed-and-unscored criterion once", "['player.walks']",
           str(unmet(both, "ref_platformer")))

    w = max(len(r[0]) for r in rows)
    print(f"{'check':<{w}}  expected")
    print("-" * (w + 40))
    for name, want, verdict in rows:
        print(f"{name:<{w}}  {want:<12}  {verdict}")
    print(f"\n{len(rows)} offline checks, {len(problems)} unmet")
    for x in problems:
        print(f"  FAIL {x}")
    return 1 if problems else 0


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--verbose", "-v", action="store_true",
                    help="print the evidence behind every verdict")
    ap.add_argument("--only", default=None,
                    help="run only mutants for this criterion id")
    ap.add_argument("--skip-lock-controls", action="store_true",
                    help="skip the session-lock controls (one of them waits out the "
                         "retry backoff and takes ~40s)")
    ap.add_argument("--hazards", action="store_true",
                    help="print the per-criterion hazard registry grouped by shape and "
                         "exit; offline, drives nothing")
    ap.add_argument("--selftest", action="store_true",
                    help="prove the registry gate and the pending adjudication can go "
                         "red; offline, drives nothing")
    args = ap.parse_args(argv)

    if args.selftest:
        return selftest()

    if args.hazards:
        hazard_census()
        problems = hazard_gate()
        for p in problems:
            print(f"  FAIL {p}")
        return 1 if problems else 0

    wanted = [m for m in MUTANTS if args.only in (None, m.criterion)]
    if not wanted:
        print(f"no mutant for {args.only!r}", file=sys.stderr)
        return 2
    if shutil.which("just") is None:
        print("`just` is not on PATH; these tests cannot run", file=sys.stderr)
        return 2

    rows: list[tuple[str, str, str, str, str, bool]] = []
    variant_rows: list[tuple[str, str, str]] = []
    pending_rows: list[tuple[str, str, str]] = []
    problems: list[str] = hazard_gate()

    with tempfile.TemporaryDirectory(prefix="bot-mutants-") as td:
        tmp = Path(td)

        # -- POSITIVE CONTROL: one healthy run per fixture ------------------- #
        healthy: dict[str, Verdicts] = {}
        for fixture in sorted({m.fixture for m in wanted}):
            repo = _copy_fixture(fixture, tmp / f"healthy-{fixture}")
            healthy[fixture] = run_bot(repo, fixture)
            print(f"healthy {fixture:<14} {healthy[fixture].wall_s:>5.1f}s", flush=True)

        # -- one mutant per repaired criterion -------------------------------- #
        for i, m in enumerate(wanted):
            repo = _copy_fixture(m.fixture, tmp / f"mutant-{i}-{m.criterion}")
            _apply(repo, m.patches, m.label)
            got = run_bot(repo, m.fixture)
            h = healthy[m.fixture]

            h_pass = h.passed.get(m.criterion)
            h_scored = h.scored.get(m.criterion)
            g_pass = got.passed.get(m.criterion)
            g_scored = got.scored.get(m.criterion)

            ok = (h_pass is True and h_scored is True
                  and g_pass is False and g_scored is True)
            if h_pass is not True:
                problems.append(f"{m.criterion}: HEALTHY {m.fixture} did not pass "
                                f"(passed={h_pass}) -- {h.evidence.get(m.criterion, '')[:300]}")
            elif h_scored is not True:
                problems.append(f"{m.criterion}: HEALTHY {m.fixture} passed but was not "
                                f"scored -- {h.evidence.get(m.criterion, '')[:300]}")
            if g_pass is not False:
                problems.append(f"{m.criterion}: MUTANT '{m.label}' did not go red "
                                f"(passed={g_pass}) -- {got.evidence.get(m.criterion, '')[:300]}")
            elif g_scored is not True:
                problems.append(
                    f"{m.criterion}: MUTANT '{m.label}' came back UNSCORED rather than "
                    f"failed. An excluded criterion is not a caught defect -- "
                    f"{got.evidence.get(m.criterion, '')[:300]}")

            rows.append((m.criterion, m.fixture, m.label,
                         _cell(h_pass, h_scored), _cell(g_pass, g_scored), ok))

            # Report, without asserting, what else the mutant disturbed. A mutant that
            # knocks over criteria it was not aiming at is still a valid negative
            # control, but the reader should be able to see it.
            extra = sorted(cid for cid in got.passed
                           if cid != m.criterion
                           and got.passed[cid] != h.passed.get(cid)
                           and cid not in m.collateral)
            if extra:
                print(f"  note: mutant '{m.label}' also flipped {extra}", flush=True)
            if args.verbose:
                print(f"  healthy: {h.evidence.get(m.criterion, '')[:400]}")
                print(f"  mutant : {got.evidence.get(m.criterion, '')[:400]}")
            print(f"  {m.criterion:<22} {got.wall_s:>5.1f}s "
                  f"{'ok' if ok else 'UNMET'}", flush=True)

        # -- VARIANTS: correct games the reference does not resemble --------- #
        variant_rows: list[tuple[str, str, str]] = []
        if args.only is None:
            for i, v in enumerate(VARIANTS):
                repo = _copy_fixture(v.fixture, tmp / f"variant-{i}")
                _apply(repo, v.patches, v.label)
                got = run_bot(repo, v.fixture)
                bad = unmet(got, v.fixture, v.tolerates)
                # A tolerance that never fires is a tolerance hiding nothing today and
                # something tomorrow. Say which ones were actually used.
                used = sorted(c for c in v.tolerates
                              if not got.passed.get(c, True) or not got.scored.get(c, True))
                if v.tolerates:
                    print(f"  note: variant '{v.label}' tolerates {list(v.tolerates)}; "
                          f"fired for {used or 'NOTHING - the tolerance is dead'}",
                          flush=True)
                variant_rows.append(
                    (v.label, ", ".join(v.exercises),
                     "ok" if not bad else f"UNMET: {bad}"))
                if bad:
                    problems.append(
                        f"variant '{v.label}' is a CORRECT game and the bot failed "
                        f"{bad} on it -- "
                        f"{'; '.join(got.evidence.get(c, '')[:200] for c in bad[:2])}")
                print(f"  variant {v.label[:44]:<44} {got.wall_s:>5.1f}s "
                      f"{'ok' if not bad else 'UNMET'}", flush=True)

        # -- PENDING: correct games this suite FAILS, with the failing ids ---- #
        if args.only is None:
            for i, p in enumerate(PENDING_VARIANTS):
                repo = _copy_fixture(p.fixture, tmp / f"pending-{i}")
                _apply(repo, p.patches, p.label)
                got = run_bot(repo, p.fixture)
                ok, cell, problem = adjudicate_pending(p, unmet(got, p.fixture))
                pending_rows.append((p.label, p.fixture, cell))
                if problem:
                    problems.append(problem)
                print(f"  pending {p.label[:44]:<44} {got.wall_s:>5.1f}s "
                      f"{'ok' if ok else 'UNMET'}", flush=True)

        lock_rows: list[tuple[str, str, str]] = []
        if not args.skip_lock_controls and args.only is None:
            print("session-lock controls...", flush=True)
            lock_rows = lock_controls(tmp, problems)

    w = max(len(r[0]) for r in rows)
    print(f"\n{'criterion':<{w}}  {'fixture':<13}  {'healthy':<9}  {'mutant':<9}  "
          f"mutant applied")
    print("-" * (w + 60))
    for cid, fixture, label, hcell, gcell, ok in rows:
        print(f"{cid:<{w}}  {fixture:<13}  {hcell:<9}  {gcell:<9}  "
              f"{label}{'' if ok else '   <-- UNMET'}")
    if variant_rows:
        n = max(len(r[0]) for r in variant_rows)
        print(f"\nvariants - CORRECT games the reference does not resemble; every "
              f"criterion must still pass\n{'variant':<{n}}  exercises")
        print("-" * (n + 40))
        for label, exercises, verdict in variant_rows:
            print(f"{label:<{n}}  {exercises:<24}  {verdict}")
    if pending_rows:
        n = max(len(r[0]) for r in pending_rows)
        print(f"\npending - CORRECT games this suite FAILS TODAY; each declares which "
              f"criteria, and an EMPTY set is a repair to promote\n"
              f"{'subject':<{n}}  fixture")
        print("-" * (n + 50))
        for label, fixture, verdict in pending_rows:
            print(f"{label:<{n}}  {fixture:<14}  {verdict}")
    if lock_rows:
        n = max(len(r[0]) for r in lock_rows)
        print(f"\nsession-lock controls (on ref_pong, whose bot opens four sibling "
              f"sessions)\n{'project behaviour':<{n}}  expected")
        print("-" * (n + 50))
        for behaviour, expected, verdict in lock_rows:
            print(f"{behaviour:<{n}}  {expected:<42}  {verdict}")
    # THE ROWS ARE MUTANTS, NOT CRITERIA, and this line said "criteria" until a second
    # mutant on `multiplier.falls` moved it from 44 to 45 while the number of criteria
    # carrying one stayed at 41 (`tasks/170`). A count has to name the population it
    # counted; `--hazards` is the producer for the per-criterion figure.
    print(f"\n{len(rows)} mutants pinned in both directions over "
          f"{len({(r[1], r[0]) for r in rows})} criteria, "
          f"{len(variant_rows)} variants, "
          f"{len(pending_rows)} pending, "
          f"{len(lock_rows)} session-lock controls, "
          f"{len(HAZARDS)} criteria with a recorded hazard, "
          f"{len(problems)} expectation(s) unmet")
    for p in problems:
        print(f"  FAIL {p}")
    return 1 if problems else 0


def _cell(passed: bool | None, scored: bool | None) -> str:
    if passed is None:
        return "absent"
    if not scored:
        return ("PASS" if passed else "FAIL") + "/unscored"
    return "PASS" if passed else "FAIL"


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
