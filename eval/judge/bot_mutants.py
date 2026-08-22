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
"""

from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
import time
from dataclasses import dataclass, field
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

NO_SCORE = ("""                self.score += SCORE_PER_KILL * self.wave * self.multiplier""",
            """                pass  # MUTANT: a kill is worth nothing""")

NO_CONTACT_DAMAGE = ("""        if self.invuln > 0:
            return
        reach = PLAYER_RADIUS + ENEMY_RADIUS""",
                     """        if self.invuln > 0:
            return
        return  # MUTANT: enemies pass straight through the player
        reach = PLAYER_RADIUS + ENEMY_RADIUS""")



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
# Both entries below were paid for:
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
#: with the ground removed from under the start, and the criterion must still pass.
PIT_UNDER_LEDGE = (
    '{"id": 1, "x": 1200.0, "y": -8.0, "w": 2400.0, "h": 16.0},    # ground, top y=0',
    '{"id": 1, "x": 1600.0, "y": -8.0, "w": 1600.0, "h": 16.0},    # VARIANT: ground '
    'starts at x=800, so the opening ledge overlooks a bottomless pit',
)


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
            (PIT_UNDER_LEDGE,), ("platform.lands", "player.falls"),
            tolerates=("attack.damages", "score.on_kill", "enemy.damages_player",
                       "invuln.window", "knockback.applied", "gameover.triggers"),
            notes="the layout five of six wg-g4c submissions actually had. The old "
                  "criterion walked off the ledge and hoped something was underneath, "
                  "so this correct level failed it; the repaired one jumps and lands on "
                  "the platform underfoot, which needs no level knowledge. THE "
                  "TOLERANCES ARE A SECOND FINDING, not a convenience: the reference "
                  "spawns enemies at x=320..2050 on the ground this variant removes, "
                  "and the bot reaches every enemy by WALKING RIGHT. Put a gap in the "
                  "floor and the combat criteria stop being measurable, because the bot "
                  "cannot cross one. That is the same cluster ts__t0 failed on wg-g4c. "
                  "The bot's unstated assumption is a continuous walkable floor; until "
                  "it can jump a gap, a correct level with one cannot be graded on "
                  "combat"),
]


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
    Mutant("determinism.replay", "ref_pong", "seeded from pid and wall-clock time",
           WALLCLOCK_SEED),
    Mutant("determinism.seed", "ref_pong", "the seed argument is ignored",
           (SEED_IGNORED,)),
    Mutant("move.translates", "ref_tetris3d", "horizontal move inputs are ignored",
           (MOVES_IGNORED,)),
    Mutant("piece.stacks", "ref_tetris3d", "locked cells never enter the settled grid",
           (NEVER_SETTLES,), collateral=("piece.locks", "harddrop.locks",
                                         "gameover.triggers")),
    Mutant("gameover.triggers", "ref_tetris3d", "game_over is never set",
           (NEVER_ENDS,)),
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
    Mutant("wall.graze", "ref_arena", "the boundary is never reported",
           (NO_GRAZE,)),
    Mutant("aim.three_axis", "ref_arena", "the depth axis is dropped from aim",
           (FLAT_AIM,)),
    Mutant("player.bounded", "ref_arena", "the volume does not hold the player",
           (UNBOUNDED,), collateral=("wall.graze",)),
    Mutant("fire.rate_limited", "ref_arena", "a bullet every tick",
           (NO_RATE_LIMIT,)),
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


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--verbose", "-v", action="store_true",
                    help="print the evidence behind every verdict")
    ap.add_argument("--only", default=None,
                    help="run only mutants for this criterion id")
    ap.add_argument("--skip-lock-controls", action="store_true",
                    help="skip the session-lock controls (one of them waits out the "
                         "retry backoff and takes ~40s)")
    args = ap.parse_args(argv)

    wanted = [m for m in MUTANTS if args.only in (None, m.criterion)]
    if not wanted:
        print(f"no mutant for {args.only!r}", file=sys.stderr)
        return 2
    if shutil.which("just") is None:
        print("`just` is not on PATH; these tests cannot run", file=sys.stderr)
        return 2

    rows: list[tuple[str, str, str, str, str, bool]] = []
    variant_rows: list[tuple[str, str, str]] = []
    problems: list[str] = []

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
                # A criterion that is `diagnostic_only` reports scored=False BY DESIGN,
                # so counting it as "came back unscored" fails every variant on a fixture
                # that has one. That is what `stage.completes` did here, and the first
                # response was to list it in a variant's `tolerates` -- which would have
                # buried a harness bug inside the one field allowed to excuse failures.
                # Rule 7: every reason not to count a failure is a channel a bug can
                # widen, so the design intent is read from the bot rather than waived.
                diagnostic = getattr(__import__(BOT_FOR[v.fixture]).BOT,
                                     "diagnostic_only", frozenset())
                waived = set(v.tolerates) | set(diagnostic)
                failed = sorted(cid for cid, ok in got.passed.items()
                                if not ok and cid not in waived)
                unscored = sorted(cid for cid, sc in got.scored.items()
                                  if not sc and cid not in waived)
                bad = failed + unscored
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
    if lock_rows:
        n = max(len(r[0]) for r in lock_rows)
        print(f"\nsession-lock controls (on ref_pong, whose bot opens four sibling "
              f"sessions)\n{'project behaviour':<{n}}  expected")
        print("-" * (n + 50))
        for behaviour, expected, verdict in lock_rows:
            print(f"{behaviour:<{n}}  {expected:<42}  {verdict}")
    print(f"\n{len(rows)} criteria pinned in both directions, "
          f"{len(variant_rows)} variants, "
          f"{len(lock_rows)} session-lock controls, "
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
