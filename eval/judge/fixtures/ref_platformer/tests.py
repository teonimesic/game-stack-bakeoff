"""2D sprite platformer - behavioural tests.

A GOOD control fixture. Real assertions about the rules, not smoke tests.
Run with `python3 tests.py`; exits non-zero if anything fails.
"""

from __future__ import annotations

import sys
import traceback

import game as g
from probe import trace_line

TESTS = []


def test(fn):
    TESTS.append(fn)
    return fn


def start(seed: int = 7) -> g.Game:
    """A game with the title card already elapsed and control handed over."""
    sim = g.Game(seed)
    for _ in range(g.OPENING_TICKS):
        sim.step({})
    return sim


def run(sim: g.Game, ticks: int, **inputs) -> list:
    seen = []
    for _ in range(ticks):
        seen.extend(sim.step(dict(inputs)))
    return seen


def plant(sim: g.Game, x: float, hp: int = g.ENEMY_HP) -> dict:
    """One enemy at a known place, and nothing else. Tests ESTABLISH conditions."""
    e = {"id": sim._take_id(), "x": x, "y": g.ENEMY_HH, "home": x, "hp": hp,
         "facing": 1}
    sim.enemies = [e]
    return e


@test
def determinism_same_seed_same_run():
    def trace(seed):
        sim = g.Game(seed)
        out = [sim.hash_hex()]
        for i in range(1200):
            sim.step({"move_right": True, "attack": i % 40 == 0})
            out.append(sim.hash_hex())
        return out
    assert trace(3) == trace(3), "same seed produced different hash sequences"


@test
def different_seeds_place_enemies_differently():
    layouts = {tuple(round(e["x"], 3) for e in g.Game(s).enemies) for s in range(8)}
    assert len(layouts) >= 7, "enemy placement barely depends on the seed: %d" % len(layouts)


@test
def the_title_card_holds_control_and_then_releases_it():
    sim = g.Game(1)
    x0 = sim.px
    for _ in range(g.OPENING_TICKS):
        sim.step({"move_right": True})
    assert sim.px == x0, "the player moved during the title card"
    run(sim, 30, move_right=True)
    assert sim.px > x0 + 10.0, "control was never handed over"


@test
def walking_moves_and_sets_facing():
    sim = start()
    x0 = sim.px
    run(sim, 20, move_right=True)
    assert sim.px > x0 and sim.facing == 1, (sim.px, sim.facing)
    x1 = sim.px
    run(sim, 20, move_left=True)
    assert sim.px < x1 and sim.facing == -1, (sim.px, sim.facing)


@test
def the_player_cannot_leave_the_stage():
    sim = start()
    run(sim, 900, move_left=True)
    assert sim.px >= g.PLAYER_HW - 1e-9, "walked off the left edge: %r" % sim.px
    assert sim.px <= g.LEVEL_W - g.PLAYER_HW + 1e-9


@test
def walking_off_a_ledge_falls_and_landing_stops_it():
    sim = start()
    y0 = sim.py
    seen = []
    for _ in range(300):
        seen.extend(sim.step({"move_right": True}))
        if "land" in seen:
            break
    assert not sim.grounded or "land" in seen, "never left the ledge"
    assert "land" in seen, "never landed: %r" % seen
    assert sim.py < y0, "landed at the same height it started (%r -> %r)" % (y0, sim.py)
    assert sim.grounded and abs(sim.vy) < 1e-9, "still moving vertically after landing"


@test
def jumping_only_works_from_the_ground():
    sim = start()
    # Jump from where the player starts. An earlier version walked right for 40 ticks
    # "to settle on the ledge" and walked straight OFF it (the ledge ends at x=120), so
    # the test was already falling when it pressed jump - a control that established the
    # opposite of the condition it needed.
    assert sim.grounded, "the player does not start on the ground"
    y0 = sim.py
    seen = run(sim, 6, jump=True)
    assert "jump" in seen, "no jump event"
    assert sim.py > y0 and not sim.grounded, "the jump did not leave the ground"
    # holding jump must not produce a second jump before landing
    airborne = run(sim, 20, jump=True)
    assert "jump" not in airborne, "jumped again in mid-air: %r" % airborne
    landed = run(sim, 240, jump=True)
    assert "land" in landed, "never came back down while holding jump"


@test
def the_swing_has_active_frames_and_then_stops():
    sim = start()
    sim.step({"attack": True})
    window = []
    for _ in range(g.ATTACK_TOTAL + 10):
        window.append(sim.attack_active)
        sim.step({})
    assert any(window), "the swing was never active"
    assert not all(window), "the swing never stopped being active"
    assert sum(window) == g.ATTACK_ACTIVE, \
        "active for %d ticks, wanted %d" % (sum(window), g.ATTACK_ACTIVE)
    assert not sim.attack_active and sim.attack_t == 0, "the swing never finished"


@test
def attacking_again_mid_swing_does_nothing():
    sim = start()
    first = sim.step({"attack": True})
    assert first == ["attack"], first
    more = run(sim, g.ATTACK_TOTAL - 2, attack=True)
    assert "attack" not in more, "a second swing started during the first: %r" % more


@test
def the_hitbox_is_in_front_and_flips_with_facing():
    sim = start()
    run(sim, 10, move_right=True)
    sim.step({"attack": True})
    run(sim, g.ATTACK_STARTUP)
    hx_r, _, w_r, _ = sim.hitbox()
    assert w_r > 0.0 and hx_r > sim.px, "hitbox is not in front when facing right"
    run(sim, g.ATTACK_TOTAL)
    run(sim, 10, move_left=True)
    sim.step({"attack": True})
    run(sim, g.ATTACK_STARTUP)
    hx_l, _, w_l, _ = sim.hitbox()
    assert w_l > 0.0 and hx_l < sim.px, "hitbox did not flip with facing"


@test
def the_hitbox_is_zero_sized_when_no_swing_is_active():
    sim = start()
    x, y, w, h = sim.hitbox()
    assert (w, h) == (0.0, 0.0), "a hitbox exists with no swing: %r" % ((x, y, w, h),)
    st = sim.state()["attack"]
    assert st["active"] is False and st["hitbox"]["w"] == 0.0, st


@test
def the_swing_damages_an_enemy_and_kills_it_for_score():
    sim = start()
    run(sim, 200, move_right=True)          # get onto the ground
    plant(sim, sim.px + g.HITBOX_REACH)
    before = sim.score
    seen = []
    for _ in range(300):
        seen.extend(sim.step({"attack": True}))
        if "enemy_dead" in seen:
            break
    assert "enemy_hit" in seen, "the swing never connected: %r" % seen[:12]
    assert "enemy_dead" in seen, "the enemy never died"
    assert sim.score > before, "a kill scored nothing"
    assert seen.count("enemy_hit") == g.ENEMY_HP, \
        "took %d hits for %d hp" % (seen.count("enemy_hit"), g.ENEMY_HP)


@test
def touching_an_enemy_costs_health_knocks_back_and_grants_grace():
    sim = start()
    run(sim, 200, move_right=True)
    sim.enemies = []
    plant(sim, sim.px + 8.0)
    hp0, x0 = sim.hp, sim.px
    seen = run(sim, 4)
    assert "player_hit" in seen, "contact did no damage: %r" % seen
    assert sim.hp == hp0 - 1, "health did not drop by one"
    assert sim.px < x0 or sim.vx < 0.0, "no knockback away from the enemy"
    assert sim.invuln > 0, "no grace window"
    # a second hit must not land inside the window
    again = run(sim, g.INVULN_TICKS - 2)
    assert "player_hit" not in again, "hit again inside the grace window"


@test
def the_animation_state_machine_distinguishes_what_the_player_is_doing():
    sim = start()
    seen = {sim.anim}
    run(sim, 4)
    seen.add(sim.anim)
    run(sim, 6, move_right=True)
    seen.add(sim.anim)
    run(sim, 3, jump=True)
    seen.add(sim.anim)
    run(sim, 40)
    seen.add(sim.anim)
    sim.step({"attack": True})
    run(sim, 2)
    seen.add(sim.anim)
    assert len(seen) >= 3, "the animation never changed state: %r" % sorted(seen)
    assert g.ANIM_ATTACK in seen and g.ANIM_WALK in seen, sorted(seen)


@test
def the_animation_frame_advances_and_cycles():
    sim = start()
    frames = []
    for _ in range(g.ANIM_FRAME_TICKS * g.ANIM_FRAMES * 2):
        sim.step({"move_right": True})
        frames.append(sim.anim_frame)
    assert len(set(frames)) >= 2, "anim_frame never advanced: %r" % sorted(set(frames))
    assert max(frames) < g.ANIM_FRAMES, "anim_frame left its range"
    assert frames.count(0) >= 2, "anim_frame never cycled back"


@test
def zero_health_ends_the_game_and_freezes_it():
    sim = start()
    run(sim, 200, move_right=True)
    sim.enemies = []
    plant(sim, sim.px, hp=99)
    overs = 0
    for _ in range(3000):
        sim.enemies[0]["x"] = sim.px      # it stays on the player
        overs += sim.step({}).count("game_over")
        if sim.game_over:
            break
    assert sim.game_over and sim.hp == 0 and sim.alive is False, sim.state()["player"]
    assert overs == 1, "game_over fired %d times" % overs
    frozen = sim.state()
    for _ in range(60):
        assert sim.step({"move_right": True, "jump": True, "attack": True}) == [], \
            "events kept firing after game over"
    assert sim.state() == frozen, "the world kept changing after game over"


@test
def reaching_the_goal_clears_the_stage_and_stops_play():
    sim = start()
    sim.enemies = []
    sim.px = g.GOAL_X - 20.0
    sim.py = 20.0
    seen = run(sim, 60, move_right=True)
    assert "stage_clear" in seen, "never cleared the stage: %r" % seen
    assert sim.victory is True and sim.game_over is False
    frozen = sim.state()
    for _ in range(60):
        assert sim.step({"move_right": True}) == [], "events after the stage cleared"
    assert sim.state() == frozen, "the world kept changing after the stage cleared"


@test
def state_shape_is_exactly_the_contract():
    st = start().state()
    assert set(st) == {"level", "player", "attack", "platforms", "enemies", "score",
                       "game_over", "victory"}, sorted(st)
    assert set(st["level"]) == {"w", "h", "goal_x"}
    assert set(st["player"]) == {"x", "y", "vx", "vy", "hp", "grounded", "facing",
                                 "invuln", "anim", "anim_frame", "alive"}, \
        sorted(st["player"])
    assert set(st["attack"]) == {"active", "frame", "hitbox"}
    assert set(st["attack"]["hitbox"]) == {"x", "y", "w", "h"}
    assert set(st["platforms"][0]) == {"id", "x", "y", "w", "h"}
    assert set(st["enemies"][0]) == {"id", "x", "y", "hp", "facing"}
    ids = [e["id"] for e in st["enemies"]]
    assert ids == sorted(ids), "enemies are not sorted by id"


@test
def every_trace_line_is_finite_and_only_uses_contracted_events():
    allowed = {"jump", "land", "attack", "enemy_hit", "enemy_dead", "player_hit",
               "stage_clear", "game_over"}
    sim = g.Game(11)
    for i in range(2500):
        events = sim.step({"move_right": True, "jump": i % 90 == 0,
                           "attack": i % 37 == 0})
        line = trace_line(sim.tick, sim, events)  # allow_nan=False
        assert "NaN" not in line and "Infinity" not in line, line
        for name in events:
            assert name in allowed, "unknown event %r" % name


def main() -> int:
    failed = 0
    for fn in TESTS:
        try:
            fn()
            print("ok   %s" % fn.__name__)
        except Exception:
            failed += 1
            print("FAIL %s" % fn.__name__)
            traceback.print_exc()
    print("%d/%d passed" % (len(TESTS) - failed, len(TESTS)))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
