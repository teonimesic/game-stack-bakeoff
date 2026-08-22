#!/usr/bin/env python3
"""Pacing measurements from a probe trace: evidence of TUNING, not correctness.

The play-bot already drives thousands of ticks and asserts that things work. The same
trace also says how the game FEELS - how long a round lasts, whether the player gets
time to react, whether anything ever stalls - and none of that is currently used.

Deliberately game-agnostic: everything here is derived from `events` and `tick`, which
every game's probe contract provides. A per-game version would measure more but would
not be comparable across the three tasks.
"""
from __future__ import annotations

import statistics as st
from typing import Any


def from_trace(history: list[Any], tick_hz: int = 64,
               inputs: list[dict] | None = None) -> dict[str, Any]:
    """`history` is a list of Tick objects (probe.Tick) or dicts.

    `inputs[i]` is what was SENT on tick `history[i]`, when the caller knows. It is used
    for one thing and it is load-bearing: separating events the WORLD raised from events
    that are echoes of the bot's own key presses.

    Without it, pacing is measured over every event name, and a bot pressing a key on a
    steady cadence manufactures a steady cadence of `move`/`rotate` events. Measured: a
    deliberately dead 3D Tetris - nothing falls, hard drop removed - emitted **200 move
    and 100 rotate events and nothing else**, and scored a longest-quiet-stretch of
    0.005 of the run, i.e. indistinguishable from a healthy game. The first repair of
    this metric traded "quiet stretch equals run length" for "quiet stretch equals the
    bot's input interval" and would have shipped (FINDINGS #52).

    The classifier is a PROPERTY, not a list of event names: **an event that never once
    fires on a tick where nothing was pressed is an echo.** A real world event - a piece
    locking, an enemy dying, a wave starting - happens whether or not the player is
    touching the controls.
    """
    def ev(t):
        return t.events if hasattr(t, "events") else (t.get("events") or [])
    def tk(t):
        return t.tick if hasattr(t, "tick") else t.get("tick", 0)

    n = len(history)
    if n < 2:
        return {"usable": False, "reason": "trace too short"}

    counts: dict[str, int] = {}
    at: dict[str, list[int]] = {}
    for t in history:
        for e in ev(t):
            counts[e] = counts.get(e, 0) + 1
            at.setdefault(e, []).append(tk(t))

    def gaps(name):
        ts = at.get(name, [])
        return [ (ts[i] - ts[i-1]) / tick_hz for i in range(1, len(ts)) ]

    # Which event names are echoes of the bot's own input? See the docstring.
    echoes: set[str] = set()
    if inputs is not None and len(inputs) >= n:
        idle_ticks = {tk(h) for h, i in zip(history, inputs) if not i}
        for name, ts in at.items():
            if idle_ticks and not (set(ts) & idle_ticks):
                echoes.add(name)
    world = {k: v for k, v in at.items() if k not in echoes}

    # The longest run of ticks in which NOTHING THE WORLD DID happened. A game that
    # stalls for twenty seconds feels broken even when every assertion passes - and a
    # bot hammering a key is not the world doing something.
    all_ticks = sorted({t for ts in world.values() for t in ts})
    if all_ticks:
        spans = [all_ticks[0]] + [all_ticks[i] - all_ticks[i-1]
                                  for i in range(1, len(all_ticks))]
        spans.append(tk(history[-1]) - all_ticks[-1])
        quiet = max(spans) / tick_hz
    else:
        # NOTHING THE WORLD DID, EVER. The quiet stretch is the WHOLE RUN - it is not
        # zero. Returning 0.0 here read a game in which literally nothing happened as
        # the liveliest possible result, which is the inverse of the truth and exactly
        # the shape this project keeps finding: a measurement that cannot fail.
        quiet = n / tick_hz

    out: dict[str, Any] = {
        "usable": True,
        "ticks": n,
        "seconds_of_play": round(n / tick_hz, 1),
        "event_counts": dict(sorted(counts.items())),
        "input_echo_events": sorted(echoes),
        "world_event_counts": {k: counts[k] for k in sorted(world)},
        "events_per_second": round(sum(counts[k] for k in world) / (n / tick_hz), 2),
        "first_event_after_seconds": round(min(all_ticks) / tick_hz, 2) if all_ticks else None,
        "longest_quiet_stretch_seconds": round(quiet, 2),
    }
    for name in ("paddle_hit", "wall_bounce", "lock", "layer_clear", "enemy_dead",
                 "fire", "player_hit", "wave_start", "spawn"):
        g = gaps(name)
        if g:
            out[f"{name}_interval_seconds"] = {
                "n": len(g), "median": round(st.median(g), 2),
                "min": round(min(g), 2), "max": round(max(g), 2)}
    # round length, where the game defines one
    for scored in ("score_left", "score_right", "game_over"):
        if scored in at:
            out.setdefault("scoring_events", {})[scored] = len(at[scored])
    pts = sorted(at.get("score_left", []) + at.get("score_right", []))
    if len(pts) > 1:
        d = [(pts[i] - pts[i-1]) / tick_hz for i in range(1, len(pts))]
        out["seconds_between_points"] = {"n": len(d), "median": round(st.median(d), 2),
                                         "min": round(min(d), 2), "max": round(max(d), 2)}
    return out
