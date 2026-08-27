#!/usr/bin/env python3
"""Scripted play-bot for the 3D Tetris task.

The interesting criterion is `layer.clears`: a game can spawn pieces, move them and
lock them and still never remove a layer. Proving a layer clears requires actually
playing well enough to fill one, which is why this bot closes the loop - it reads
`heights` and the falling piece's cells out of the trace and chooses where to drop.
That is only possible because the probe is a live stdin/stdout session rather than a
recorded tape.
"""

from __future__ import annotations

from typing import Any

from checks import determinism_criteria, idle_tape
from probe import (Bot, Criterion, ProbeError, ProbeSession, Tick,
                   end_condition_holds, unusable_criteria)


def _piece(t: Tick) -> dict[str, Any] | None:
    p = t.state.get("piece")
    return p if isinstance(p, dict) else None


def _cells(t: Tick) -> list[tuple[int, int, int]]:
    p = _piece(t)
    if not p:
        return []
    out = []
    for c in p.get("cells") or []:
        try:
            out.append((int(c[0]), int(c[1]), int(c[2])))
        except (TypeError, ValueError, IndexError):
            return []
    return out


def _well(t: Tick) -> tuple[int, int, int] | None:
    w = t.state.get("well")
    if not isinstance(w, dict):
        return None
    try:
        return int(w["w"]), int(w["d"]), int(w["h"])
    except (KeyError, TypeError, ValueError):
        return None


def _heights(t: Tick) -> list[list[int]] | None:
    h = t.state.get("heights")
    if not isinstance(h, list) or not h:
        return None
    try:
        return [[int(v) for v in row] for row in h]
    except (TypeError, ValueError):
        return None


def _shape(cells: list[tuple[int, int, int]]) -> frozenset[tuple[int, int, int]]:
    """Cell offsets normalised to the piece's own corner - orientation, not position."""
    if not cells:
        return frozenset()
    mx, my, mz = (min(c[i] for c in cells) for i in range(3))
    return frozenset((x - mx, y - my, z - mz) for x, y, z in cells)


def _extent(cells: list[tuple[int, int, int]]) -> int:
    """Vertical span of the piece, in cells. Zero means it lies flat."""
    if not cells:
        return 99
    return max(c[1] for c in cells) - min(c[1] for c in cells)


def _filled(t: Tick) -> int | None:
    """Total filled cells in the well, summed out of the CONTRACTED `heights` grid.

    `settled` carries the same number directly and is not in the state contract
    `state.shape` checks, so a submission may omit it - and a guard that reads a
    missing field gets 0 on every tick, which is a check that cannot fail. `None` when
    the grid is unreadable, which is a third value and not a zero.
    """
    h = _heights(t)
    return None if h is None else sum(sum(row) for row in h)


def _int(t: Tick, key: str, default: int = 0) -> int:
    v = t.state.get(key, default)
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


#: How long the bot waits at the START of a session for the game to hand play over.
#: Eight seconds at 64 Hz covers an opening title card, a countdown and a pause, and a
#: game that has not started by then is not withholding play for presentation.
#:
#: ONE CONSTANT, FOUR PLACES, because a card gates the whole opening rather than one
#: criterion: the first piece appearing, the first piece descending, and the first piece
#: of each of the two fresh sessions `_play_for_a_clear` and `_gameover_check` open. The
#: budgets were 20, 120, 60 and 60, so a repair to any one of them left the others red -
#: which is why the two card subjects now in `bot_mutants.VARIANTS` declared different
#: failing sets against the same card while they were pending.
#:
#: `bot_pong.LIVE_BUDGET`, `bot_platformer._CONTROL_TICKS` and
#: `bot_arena.OPENING_BUDGET` are this same 512, all
#: bought by a Godot submission that held the ball for `OPENING_DELAY = 104` so its title
#: card would be readable (FINDINGS #34). This bot was never revisited, and against a
#: 96-tick card - the platformer REFERENCE's own `OPENING_TICKS`, so no longer than one
#: this repository ships - it failed `piece.falls` over a frozen well and four of fifteen
#: criteria over an empty one (`tasks/158`).
OPENING_BUDGET = 512

#: What an await costs once play HAS started and a piece has already been seen. Not an
#: opening budget: a game that stops spawning mid-play is failing, not presenting itself.
MIDGAME_AWAIT = 60


class Tetris3DBot(Bot):
    #: Long enough to lock a few dozen pieces, so "how often does something happen"
    #: is a property of the game rather than of the criteria drive (FINDINGS #52).
    play_ticks = 3000
    game = "g2_tetris3d"
    #: The criterion that checks THIS GAME'S END CONDITION, whatever it is called.
    #: Named explicitly because the concept has two spellings across the suite:
    #: `gameover.triggers` in three games and `match.ends` in pong, which is
    #: first-to-11, so its end condition is a WIN rather than a loss. This game
    #: ends when the well fills up and play stops.
    #: A cross-game audit asking "does every game verify its own end condition?"
    #: would grep for `gameover` and report a false gap for pong - a mechanical sweep
    #: reporting something untrue, which this project has lost time to before (#38).
    #: Read this attribute instead of guessing from the id.
    end_condition = "gameover.triggers"

    criteria = [
        ("state.shape", "Does the probe report the contracted state shape (well, "
                        "piece, heights, score, layers_cleared, game_over)?"),
        ("well.dimensions", "Is the well the specified 5 x 5 x 12 with a matching "
                            "heights grid?"),
        ("piece.spawns", "Does a four-cell piece spawn at the top of the well?"),
        ("piece.falls", "Does the falling piece descend on its own?"),
        ("piece.locks", "Does a piece that reaches the bottom lock and become part of "
                        "the settled stack?"),
        ("bounds.respected", "Does the falling piece stay inside the well at every "
                             "tick, including while being moved?"),
        ("move.translates", "Does a horizontal control slide the piece without "
                            "changing its shape?"),
        ("rotate.reorients", "Does a rotation control change the piece's orientation "
                             "while keeping its four cells?"),
        ("harddrop.locks", "Does a hard drop land and lock the piece immediately?"),
        ("piece.stacks", "Do locked pieces accumulate, raising the column heights they "
                         "land on?"),
        ("layer.clears", "Does a completely filled horizontal layer get removed?"),
        ("score.rewards_clears", "Does the score increase when a layer is cleared?"),
        ("gameover.triggers", "Does the game end when the well stacks out, and stop "
                              "accepting play?"),
        ("determinism.replay", "Does replaying the same seed and the same inputs "
                               "reproduce the same state hash at every tick?"),
        ("determinism.seed", "Do two different seeds produce different runs?"),
    ]

    # MEASURED, and the reason these two are not scored:
    # against a known-correct reference implementation of this exact spec, this bot
    # failed to clear a single layer across 3 seeds x 2 well geometries (5x5 and 4x4)
    # x 5 placement cost functions, including full rotate_y orientation enumeration
    # and piece flattening. It reaches 40-51 placements and then stacks out. A layer
    # in a 5x5 well is 25 cells and pieces are 4, so completing one needs interlocking
    # play this greedy surface heuristic does not achieve.
    #
    # Scoring a criterion the instrument cannot pass on correct work would manufacture
    # a false negative for every honest submission, and a false negative is
    # indistinguishable from a real failure once it is averaged. So both are measured,
    # both are reported, and neither counts - the mirror of removing an assertion that
    # could not fail (FINDINGS.md, the BALL_SPEEDUP escape).
    #
    # To promote them back: strengthen the placement policy until it clears on at
    # least 3 seeds against the reference, or change the task's well geometry to one
    # where a scripted bot demonstrably can. Do not promote them on reasoning alone.
    diagnostic_only = frozenset({"layer.clears", "score.rewards_clears"})

    # ------------------------------------------------------------------ #

    def run(self, s: ProbeSession) -> list[Criterion]:
        out: list[Criterion] = []
        add = out.append
        t0 = s.last

        well = _well(t0)
        heights = _heights(t0)
        shape_ok = (
            well is not None and heights is not None
            and isinstance(t0.state.get("score"), (int, float))
            and isinstance(t0.state.get("layers_cleared"), (int, float))
            and isinstance(t0.state.get("game_over"), bool)
        )
        add(Criterion("state.shape", self._q("state.shape"), shape_ok,
                      f"tick 0 state keys: {sorted(t0.state)}; "
                      f"well={well} heights={'ok' if heights else 'missing'}"))
        if not shape_ok or well is None or heights is None:
            for cid, q in self.criteria[1:]:
                add(Criterion(cid, q, False, "state shape contract not met"))
            return out

        w, d, h = well
        dims_ok = (w, d, h) == (5, 5, 12) and len(heights) == w and \
            all(len(row) == d for row in heights)
        add(Criterion("well.dimensions", self._q("well.dimensions"), dims_ok,
                      f"well {w}x{d}x{h}, heights grid "
                      f"{len(heights)}x{len(heights[0]) if heights else 0}"))

        # --- spawn, fall, lock, bounds ----------------------------------- #
        spawned = _cells(t0)
        spawn_evt = False
        for _ in range(OPENING_BUDGET):
            if len(spawned) == 4:
                break
            t = s.step_raw({})
            spawn_evt = spawn_evt or "spawn" in t.events
            spawned = _cells(t)
        add(Criterion("piece.spawns", self._q("piece.spawns"), len(spawned) == 4,
                      f"first piece has {len(spawned)} cells: {spawned}"))

        y_start = min((c[1] for c in spawned), default=-1)
        fell = False
        oob: list[str] = []
        for _ in range(OPENING_BUDGET):
            t = s.step_raw({})
            for (x, y, z) in _cells(t):
                if not (0 <= x < w and 0 <= y < h and 0 <= z < d):
                    oob.append(f"tick {t.tick}: cell ({x},{y},{z}) outside {w}x{d}x{h}")
            cur = _cells(t)
            if cur and min(c[1] for c in cur) < y_start:
                fell = True
            if "lock" in t.events:
                break
        add(Criterion("piece.falls", self._q("piece.falls"), fell,
                      f"lowest cell height went from {y_start} to "
                      f"{min((c[1] for c in _cells(s.last)), default='n/a')} without "
                      f"input"))

        locked_settled_before = _int(s.history[0], "settled")
        lock_seen = any("lock" in t.events for t in s.history)
        for _ in range(600):
            if lock_seen:
                break
            t = s.step_raw({})
            lock_seen = "lock" in t.events
            for (x, y, z) in _cells(t):
                if not (0 <= x < w and 0 <= y < h and 0 <= z < d):
                    oob.append(f"tick {t.tick}: cell ({x},{y},{z}) out of bounds")
        settled_after = _int(s.last, "settled")
        add(Criterion("piece.locks", self._q("piece.locks"),
                      lock_seen and settled_after >= locked_settled_before + 4,
                      f"lock event seen: {lock_seen}; settled cells "
                      f"{locked_settled_before} -> {settled_after}"))

        # --- move and rotate --------------------------------------------- #
        add(self._move_check(s, w, d, h, oob))
        add(self._rotate_check(s, w, d, h, oob))

        add(Criterion("bounds.respected", self._q("bounds.respected"), not oob,
                      "no out-of-bounds cells observed" if not oob
                      else f"{len(oob)} violations, first: {oob[0]}"))

        # --- hard drop ---------------------------------------------------- #
        add(self._harddrop_check(s, w, d))

        # --- a real game: stacking, layer clears, scoring ------------------ #
        stack_c, clear_c, score_c = self._play_for_a_clear(s.repo, s.env, w, d, h)
        add(stack_c)
        add(clear_c)
        add(score_c)

        # --- stacking out -------------------------------------------------- #
        add(self._gameover_check(s.repo, s.env, w, d, h))

        out.extend(determinism_criteria(s.repo, idle_tape(300), env=s.env))
        return out

    # ------------------------------------------------------------------ #

    def _q(self, cid: str) -> str:
        return next(q for c, q in self.criteria if c == cid)

    @staticmethod
    def _await_piece(s: ProbeSession, limit: int = MIDGAME_AWAIT) -> Tick | None:
        for _ in range(limit):
            if len(_cells(s.last)) == 4:
                return s.last
            s.step_raw({})
        return s.last if len(_cells(s.last)) == 4 else None

    def play_inputs(self, tick: Tick) -> dict[str, Any]:
        """A steady rhythm of shuffle-rotate-drop.

        Deliberately NOT the greedy placement policy `_play_for_a_clear` uses: that one
        needs multi-tick sequencing and hunts for a layer clear, which is a criteria
        question. What pacing needs is a player who keeps the game moving - pieces
        entering, being nudged, and locking at a natural cadence - so the intervals
        between events describe the GAME rather than a search.
        """
        # The contract is four DIRECTIONAL booleans, not signed axes:
        # move_neg_x / move_pos_x / move_neg_z / move_pos_z. Getting that wrong makes
        # every move a no-op, which shows up as a well filled in one column and a game
        # that ends in four seconds - measured, before this comment existed.
        # NO HARD DROP. It would make every `lock` fire on the tick the drop was
        # pressed, and a lock that is caused by the player pressing a key is not
        # evidence about the game's pacing - it is evidence about the bot's cadence.
        # Letting gravity land the pieces is both the honest pacing question ("how
        # fast does this game actually move?") and what makes `lock` and `spawn`
        # classifiable as world events at all.
        cycle = tick.tick % 30
        lane = (tick.tick // 30) % 4          # spread the stack so the run lasts
        if cycle < 6:
            return {("move_pos_x" if lane in (0, 1) else "move_neg_x"): True}
        if cycle < 12:
            return {("move_pos_z" if lane in (0, 3) else "move_neg_z"): True}
        if cycle == 14:
            return {"rotate_y": True}
        return {}

    @staticmethod
    def _drop(s: ProbeSession, limit: int = 80) -> bool:
        """Hard-drop the falling piece and wait for it to lock. Returns whether it did.

        MEASURED HAZARD, and the reason this is a method rather than an inline loop:
        the task spec says an input field means "this control is held during this
        tick", but it does not say whether a game acts on the level or on the rising
        edge - and both are reasonable readings. Against an edge-triggered reference
        implementation, holding `hard_drop` true for sixty consecutive ticks fired it
        exactly once (or never, if it was already held when the piece spawned), the
        bot mistook ordinary gravity for a drop, and it counted the same piece as
        seven different ones. The bot must therefore be trigger-agnostic: always
        release for a tick before pressing, and re-press rather than hold.
        """
        s.step_raw({})                      # guarantee a falling edge first
        for _ in range(limit):
            if "lock" in s.step_raw({"hard_drop": True}).events:
                return True
            if "lock" in s.step_raw({}).events:
                return True
        return False

    def _move_check(self, s: ProbeSession, w: int, d: int, h: int,
                    oob: list[str]) -> Criterion:
        """Push the piece toward a side that HAS room, not toward a fixed one.

        The version this replaces always pressed `move_neg_x`. It failed
        `g2_tetris3d__rust__t0` with `min x 0 -> 0`, adjudicated a FALSE NEGATIVE: the
        piece had spawned flush against the left wall, so refusing to move it was the
        correct behaviour and the criterion was measuring where the piece happened to
        sit. Here the piece's own cells and the well's dimensions decide the direction,
        and every direction with clearance is tried before the criterion fails.

        If no direction has clearance the piece spans the well on both horizontal axes.
        Then "it did not move" is right, there is no experiment to run, and the
        criterion is recorded as not measured rather than failed.
        """
        t = self._await_piece(s)
        if t is None:
            return Criterion("move.translates", self._q("move.translates"), False,
                             "no falling piece to move")
        cells = _cells(t)
        if len(cells) != 4:
            return Criterion("move.translates", self._q("move.translates"), False,
                             f"the falling piece reports {len(cells)} cells, not 4")

        # (input, axis index, direction, room?) - horizontal axes only.
        span = {i: (min(c[i] for c in cells), max(c[i] for c in cells)) for i in (0, 2)}
        limit = {0: w, 2: d}
        candidates = [
            ("move_neg_x", 0, -1, span[0][0] >= 1),
            ("move_pos_x", 0, +1, span[0][1] <= limit[0] - 2),
            ("move_neg_z", 2, -1, span[2][0] >= 1),
            ("move_pos_z", 2, +1, span[2][1] <= limit[2] - 2),
        ]
        with_room = [c for c in candidates if c[3]]
        geometry = (f"piece x in [{span[0][0]},{span[0][1]}] of {w}, "
                    f"z in [{span[2][0]},{span[2][1]}] of {d}")
        if not with_room:
            return self.not_established(
                "move.translates", self._q("move.translates"),
                f"the piece spans the well on both horizontal axes, so refusing every "
                f"move is correct and there is no clearance to push into ({geometry})")

        tried: list[str] = []
        for field, axis, direction, _room in with_room:
            t = self._await_piece(s)
            if t is None:
                break
            before = _cells(t)
            if len(before) != 4:
                break
            shape_before = _shape(before)
            edge_before = min(c[axis] for c in before) if direction < 0 \
                else max(c[axis] for c in before)
            # Alternate press/release: works whether the game moves per held tick or
            # only on the rising edge.
            moved = False
            for i in range(8):
                t = s.step_raw({field: True} if i % 2 == 0 else {})
                for (x, y, z) in _cells(t):
                    if not (0 <= x < w and 0 <= y < h and 0 <= z < d):
                        oob.append(f"tick {t.tick}: cell ({x},{y},{z}) out of bounds")
                cur = _cells(t)
                if len(cur) != 4:
                    break        # it locked mid-push; that attempt is inconclusive
                edge_now = min(c[axis] for c in cur) if direction < 0 \
                    else max(c[axis] for c in cur)
                if (edge_now - edge_before) * direction > 0:
                    moved = True
                    if _shape(cur) == shape_before:
                        return Criterion(
                            "move.translates", self._q("move.translates"), True,
                            f"{field} slid the piece from {edge_before} to {edge_now} "
                            f"on axis {'xyz'[axis]} with its shape unchanged "
                            f"({geometry})")
                    return Criterion(
                        "move.translates", self._q("move.translates"), False,
                        f"{field} moved the piece from {edge_before} to {edge_now} but "
                        f"CHANGED its shape: {sorted(shape_before)} -> "
                        f"{sorted(_shape(cur))}")
            tried.append(f"{field}:{'moved-but-shape-lost' if moved else 'no movement'}")
        return Criterion(
            "move.translates", self._q("move.translates"), False,
            f"pushed toward every side with clearance and the piece never slid: "
            f"{', '.join(tried) or 'no attempt completed'} ({geometry})")

    def _rotate_check(self, s: ProbeSession, w: int, d: int,
                      h: int, oob: list[str]) -> Criterion:
        """Try each rotation axis across several pieces - a cube is symmetric."""
        tried: list[str] = []
        for attempt in range(9):
            t = self._await_piece(s)
            if t is None:
                break
            axis = ("rotate_x", "rotate_y", "rotate_z")[attempt % 3]
            before = _shape(_cells(t))
            t = s.step_raw({axis: True})
            for (x, y, z) in _cells(t):
                if not (0 <= x < w and 0 <= y < h and 0 <= z < d):
                    oob.append(f"tick {t.tick}: cell ({x},{y},{z}) out of bounds "
                               f"after {axis}")
            after_cells = _cells(t)
            after = _shape(after_cells)
            tried.append(f"{axis}:{'changed' if after != before else 'same'}")
            if after != before and len(after_cells) == 4:
                return Criterion("rotate.reorients", self._q("rotate.reorients"), True,
                                 f"{axis} changed the piece orientation "
                                 f"({sorted(before)} -> {sorted(after)})")
            # let this piece settle so the next attempt gets a fresh one
            self._drop(s, limit=40)
        return Criterion("rotate.reorients", self._q("rotate.reorients"), False,
                         f"no rotation changed the piece across {len(tried)} attempts: "
                         f"{', '.join(tried)}")

    def _harddrop_check(self, s: ProbeSession, w: int, d: int) -> Criterion:
        t = self._await_piece(s)
        if t is None:
            return Criterion("harddrop.locks", self._q("harddrop.locks"), False,
                             "no falling piece to drop")
        before_y = min(c[1] for c in _cells(t))
        settled_before = _int(t, "settled")
        s.step_raw({})                       # falling edge first - see _drop()
        t1 = s.step_raw({"hard_drop": True})
        locked = "lock" in t1.events
        if not locked:
            locked = "lock" in s.step_raw({}).events
        settled_after = _int(s.last, "settled")
        return Criterion(
            "harddrop.locks", self._q("harddrop.locks"),
            locked and settled_after >= settled_before + 4,
            f"hard drop from height {before_y}: lock within 2 ticks = {locked}; "
            f"settled {settled_before} -> {settled_after}")

    # -- the closed-loop player ---------------------------------------- #

    @staticmethod
    def _flatten(s: ProbeSession, axes: tuple[str, ...] = ("rotate_x", "rotate_z")
                 ) -> Tick:
        """Rotate the falling piece until it lies in a single horizontal plane.

        This is the difference between a bot that clears layers and one that does not.
        A piece with vertical extent cannot sit flush on level ground, so every
        placement buries an empty cell, holes accumulate, and the well stacks out
        without a single layer completing - measured, on a correct reference
        implementation: 34 pieces, max height 12, zero clears. Flattened pieces
        contribute their four cells to one layer and leave the surface level.

        Rotations are cyclic, so at most three presses per axis are needed, and the
        loop stops the moment the extent reaches zero.
        """
        best_extent = _extent(_cells(s.last))
        if best_extent == 0:
            return s.last
        for axis in axes:
            for _ in range(3):
                s.step_raw({})            # falling edge first - see _drop()
                t = s.step_raw({axis: True})
                if len(_cells(t)) != 4:
                    return t          # it locked mid-rotation; caller re-reads
                e = _extent(_cells(t))
                if e == 0:
                    return t
                if e >= best_extent:
                    # This axis is not helping; the piece may be symmetric about it.
                    best_extent = min(best_extent, e)
                else:
                    best_extent = e
        return s.last

    @staticmethod
    def _best_placement(cells: list[tuple[int, int, int]], heights: list[list[int]],
                        w: int, d: int, h: int) -> tuple[int, int]:
        """Choose (dx, dz): fewest buried cells, then lowest landing, then flattest.

        `buried` is the empty space sealed underneath the piece when it comes to rest -
        the 3D generalisation of Tetris "holes", and the single term that matters most.
        Landing height comes second so the floor fills before the stack grows, and
        aggregate height and bumpiness break the remaining ties.
        """
        base_x = min(c[0] for c in cells)
        base_z = min(c[2] for c in cells)
        base_y = min(c[1] for c in cells)
        rel = [(x - base_x, y - base_y, z - base_z) for x, y, z in cells]
        span_x = max(r[0] for r in rel) + 1
        span_z = max(r[2] for r in rel) + 1
        top = max(r[1] for r in rel)

        best: tuple[int, ...] | None = None
        best_move = (0, 0)
        for ox in range(0, w - span_x + 1):
            for oz in range(0, d - span_z + 1):
                rest = max(heights[ox + rx][oz + rz] - ry for rx, ry, rz in rel)
                rest = max(rest, 0)
                if rest + top >= h:
                    continue
                buried = sum(max(0, (rest + ry) - heights[ox + rx][oz + rz])
                             for rx, ry, rz in rel)
                new_heights = [row[:] for row in heights]
                for rx, ry, rz in rel:
                    new_heights[ox + rx][oz + rz] = max(
                        new_heights[ox + rx][oz + rz], rest + ry + 1)
                bumpy = sum(abs(new_heights[x][z] - new_heights[x2][z2])
                            for x in range(w) for z in range(d)
                            for x2, z2 in ((x + 1, z), (x, z + 1))
                            if x2 < w and z2 < d)
                key = (buried, rest, sum(sum(r) for r in new_heights), bumpy)
                if best is None or key < best:
                    best, best_move = key, (ox - base_x, oz - base_z)
        return best_move

    def _play_for_a_clear(self, repo, env, w: int, d: int,
                          h: int) -> tuple[Criterion, Criterion, Criterion]:
        """A fresh game, played greedily, hunting for a layer clear."""
        try:
            with ProbeSession(repo=repo, env=env, seed=7,
                              total_timeout_s=1800.0) as s:
                heights_start = _heights(s.last) or [[0] * d for _ in range(w)]
                clears = 0
                score_before_clear = None
                score_after_clear = None
                settled_drop = False
                pieces = 0
                budget = 9000
                while pieces < 150 and s.ticks_sent < budget:
                    # THIS SESSION HAS ITS OWN OPENING. It is a fresh `ProbeSession`,
                    # so the title card that gated the criteria drive gates this one
                    # too, from tick 0 - and until a piece has been placed there is no
                    # evidence play has started. `MIDGAME_AWAIT` only applies after it.
                    t = self._await_piece(
                        s, OPENING_BUDGET if pieces == 0 else MIDGAME_AWAIT)
                    if t is None or _int(t, "game_over", 0) or \
                            s.last.state.get("game_over") is True:
                        break
                    t = self._flatten(s)
                    cells = _cells(t)
                    if len(cells) != 4:
                        continue
                    heights = _heights(t) or heights_start
                    dx, dz = self._best_placement(cells, heights, w, d, h)
                    settled_before = _int(s.last, "settled")
                    pre_score = _int(s.last, "score")
                    # translate (alternating press/release), then drop
                    for _ in range(abs(dx)):
                        s.step_raw({"move_pos_x" if dx > 0 else "move_neg_x": True})
                        s.step_raw({})
                    for _ in range(abs(dz)):
                        s.step_raw({"move_pos_z" if dz > 0 else "move_neg_z": True})
                        s.step_raw({})
                    mark = len(s.history)
                    self._drop(s)
                    s.step_raw({})     # let the clear resolve and the next piece spawn
                    for t in s.history[mark:]:
                        if "layer_clear" in t.events:
                            clears += t.events.count("layer_clear")
                            if score_before_clear is None:
                                score_before_clear = pre_score
                                score_after_clear = _int(t, "score")
                            if _int(t, "settled") < settled_before + 4:
                                settled_drop = True
                    pieces += 1
                    if clears and score_after_clear is not None:
                        break
                heights_end = _heights(s.last) or heights_start
                max_start = max(max(r) for r in heights_start)
                max_end = max(max(r) for r in heights_end)
                total_clears = _int(s.last, "layers_cleared")
                detail = (f"played {pieces} pieces over {s.ticks_sent} ticks; "
                          f"max column height {max_start} -> {max_end}; "
                          f"layer_clear events {clears}, reported layers_cleared "
                          f"{total_clears}")
        except ProbeError as e:
            ids = ("piece.stacks", "layer.clears", "score.rewards_clears")
            a, b, c = unusable_criteria([(cid, self._q(cid)) for cid in ids], e,
                                        "the play session", self.diagnostic_only)
            return a, b, c

        stacks = Criterion("piece.stacks", self._q("piece.stacks"),
                           max_end > max_start or total_clears > 0, detail)
        cleared = Criterion("layer.clears", self._q("layer.clears"),
                            clears > 0 and total_clears > 0,
                            detail + f"; settled count dropped on the clear: "
                                     f"{settled_drop}")
        if score_before_clear is None:
            scored = Criterion("score.rewards_clears", self._q("score.rewards_clears"),
                               False, "no layer was cleared, so the reward could not "
                                      "be observed. " + detail)
        else:
            scored = Criterion(
                "score.rewards_clears", self._q("score.rewards_clears"),
                (score_after_clear or 0) > score_before_clear,
                f"score {score_before_clear} -> {score_after_clear} across the tick "
                f"that cleared a layer")
        return stacks, cleared, scored

    def _gameover_check(self, repo, env, w: int, d: int, h: int) -> Criterion:
        """Hard-drop everything into one corner until the well stacks out."""
        try:
            with ProbeSession(repo=repo, env=env, seed=7,
                              total_timeout_s=900.0) as s:
                over_at = None
                for placed in range(60):
                    # A fresh session, so its first await is an opening budget for the
                    # same reason `_play_for_a_clear`'s is - see the note there.
                    t = self._await_piece(
                        s, OPENING_BUDGET if placed == 0 else MIDGAME_AWAIT)
                    if t is None:
                        # NO FALLING PIECE IS WHAT GAME OVER LOOKS LIKE.
                        # The contract says `piece` is null when no piece is falling, and
                        # a stacked-out game never spawns another one - so this branch is
                        # reached BY the success condition. Breaking out of it without
                        # looking at `game_over` is why this criterion failed two correct
                        # submissions while its own evidence string read
                        # "without the game ending; game_over=True". The verdict
                        # contradicted the evidence printed beside it.
                        if (s.last.state.get("game_over") is True
                                or any("game_over" in h.events
                                       for h in s.history)):
                            over_at = s.last.tick
                        break
                    cells = _cells(t)
                    dx = -min(c[0] for c in cells)
                    dz = -min(c[2] for c in cells)
                    for _ in range(abs(dx)):
                        s.step_raw({"move_neg_x": True})
                        s.step_raw({})
                    for _ in range(abs(dz)):
                        s.step_raw({"move_neg_z": True})
                        s.step_raw({})
                    mark = len(s.history)
                    self._drop(s)
                    s.step_raw({})
                    for t in s.history[mark:]:
                        if t.state.get("game_over") is True or "game_over" in t.events:
                            over_at = t.tick
                            break
                    if over_at is not None:
                        break
                if over_at is None:
                    return Criterion(
                        "gameover.triggers", self._q("gameover.triggers"), False,
                        f"stacked into one corner for {s.ticks_sent} ticks without the "
                        f"game ending; game_over={s.last.state.get('game_over')}")
                # IDLE FIRST, THEN PRESS AND READ THROUGH THE RESET -
                # `probe.end_condition_holds` holds the reason, and holds it once for
                # all four bots. This loop used to press hard_drop and move_pos_x
                # straight away, which pressed the restart control of a correct game
                # that clears its game-over card on any input. Here that read as a PASS
                # rather than a failure, and the pass was not evidence: the run
                # restarted and stacked out again inside the window, with the restart's
                # own score reset making the frozen test true. Lengthening the card
                # flipped the verdict on a game that had not changed (`tasks/157`).
                # `hard_drop` is an EDGE, so the press set is released every other tick:
                # held flat it drops once and a game that kept playing would have
                # nothing left to move its score with.
                end = end_condition_holds(
                    s, idle_ticks=200, press_ticks=200,
                    inputs=lambda i: ({"hard_drop": True, "move_pos_x": True}
                                      if i % 2 == 0 else {}),
                    # THE WELL AS WELL AS THE SCORE. A stacked-out game that keeps
                    # stepping leaves the score alone - clearing a layer is what pays,
                    # and the well is full - but it goes on locking: measured on a
                    # reference with the step function's `game_over` early-out deleted,
                    # 199 `lock` events over 400 ticks with the score unchanged at 0.
                    # The filled-cell TOTAL rather than the `heights` grid, because the
                    # grid prints ~250 characters twice and `Criterion.evidence` is
                    # stored truncated at 600 - an audit trail whose tail is cut off is
                    # the half that carries the pressed-phase verdict. Both terms come
                    # back to their tick-0 values on a reset.
                    sample=lambda t: (_int(t, "score"), _filled(t)))
                return Criterion(
                    "gameover.triggers", self._q("gameover.triggers"), end.passed,
                    f"game over at tick {over_at}; "
                    f"{end.detail('(score, filled cells)')}")
        except ProbeError as e:
            return unusable_criteria(
                [("gameover.triggers", self._q("gameover.triggers"))], e,
                "the stack-out session")[0]


BOT = Tetris3DBot()
