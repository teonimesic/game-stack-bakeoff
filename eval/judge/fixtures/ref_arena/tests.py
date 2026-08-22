"""3D twin-stick arena shooter - behavioural tests.

A GOOD control fixture. Real assertions about the rules, not smoke tests.
Run with `python3 tests.py`; exits non-zero if anything fails.

Rewritten 2026-08-15 for the 3D/analog spec. Every new mechanic the task added has a
test here, because a reference that does not exercise a behaviour cannot validate the
criterion that measures it (FINDINGS #34).
"""

from __future__ import annotations

import math
import sys
import traceback

import game as g
from probe import trace_line

TESTS = []


def test(fn):
    TESTS.append(fn)
    return fn


def aim_at(sim: g.Game, target: dict) -> dict:
    """A unit analog aim vector pointing from the player at `target`."""
    dx = target["x"] - sim.px
    dy = target["y"] - sim.py
    dz = target["z"] - sim.pz
    n = math.sqrt(dx * dx + dy * dy + dz * dz) or 1.0
    return {"aim_x": dx / n, "aim_y": dy / n, "aim_z": dz / n}


def hunter(sim: g.Game) -> dict:
    """Stand still, aim at the nearest hittable enemy, hold fire."""
    out = {"fire": True}
    live = [e for e in sim.enemies if e["spawn"] <= 0]
    if not live:
        return out
    target = min(live, key=lambda e: ((sim.px - e["x"]) ** 2 + (sim.py - e["y"]) ** 2
                                      + (sim.pz - e["z"]) ** 2))
    out.update(aim_at(sim, target))
    return out


def play(seed: int, ticks: int, driver):
    sim = g.Game(seed)
    log = []
    for _ in range(ticks):
        log.append((sim.tick + 1, sim.step(driver(sim))))
    return sim, log


def flat(log):
    out = []
    for _t, events in log:
        out.extend(events)
    return out


def plant(sim: g.Game, x: float, y: float, z: float, kind: str = g.KIND_DRIFTER,
          hp: int = 1) -> dict:
    """One fully materialised enemy at a known place, and nothing else.

    Tests that need an enemy in a specific position ESTABLISH it. Waiting for one to
    wander into range is the defect this project has paid for sixteen times.
    """
    e = {"id": sim._take_id(), "kind": kind, "x": x, "y": y, "z": z, "hp": hp,
         "spawn": 0, "phase": 0}
    sim.enemies = [e]
    return e


@test
def determinism_same_seed_same_run():
    def trace(seed):
        sim = g.Game(seed)
        out = [sim.hash_hex()]
        for _ in range(1500):
            sim.step(hunter(sim))
            out.append(sim.hash_hex())
        return out
    assert trace(3) == trace(3), "same seed produced different hash sequences"


@test
def different_seeds_place_enemies_differently():
    layouts = set()
    for seed in range(8):
        sim = g.Game(seed)
        sim.step({})  # wave 1 spawns on the first tick
        layouts.add(tuple(round(e["x"], 3) for e in sim.enemies))
    assert len(layouts) >= 7, "enemy spawn barely depends on the seed: %d" % len(layouts)


@test
def wave_one_spawns_on_a_face_of_the_volume():
    sim = g.Game(1)
    assert sim.state()["enemies"] == [], "enemies existed before the first tick"
    events = sim.step({})
    assert events.count("wave_start") == 1, events
    assert events.count("enemy_spawn") == g.Game.wave_count(1), events
    assert len(sim.enemies) == g.Game.wave_count(1), "wrong wave size"
    for e in sim.enemies:
        face = min(abs(abs(e["x"]) - g.ARENA_HALF_X),
                   abs(abs(e["y"]) - g.ARENA_HALF_Y),
                   abs(abs(e["z"]) - g.ARENA_HALF_Z))
        assert face <= g.ENEMY_RADIUS + 1e-6, "enemy %r did not spawn on a face" % e


@test
def movement_is_analog_and_proportional():
    """A half-pushed axis moves at half speed. Eight-way rounding fails this."""
    full = g.Game(1)
    full.step({"move_x": 1.0})
    half = g.Game(1)
    half.step({"move_x": 0.5})
    assert abs(full.px - g.PLAYER_SPEED * g.DT) < 1e-9, "full push speed is wrong"
    assert abs(half.px - 0.5 * g.PLAYER_SPEED * g.DT) < 1e-9, \
        "half push moved %.6f, wanted %.6f" % (half.px, 0.5 * g.PLAYER_SPEED * g.DT)
    # An off-axis direction is honoured as a direction, not snapped to a compass point.
    odd = g.Game(1)
    odd.step({"move_x": 1.0, "move_z": 0.25})
    ratio = odd.pz / odd.px
    assert abs(ratio - 0.25) < 1e-6, "direction was snapped: z/x = %.6f" % ratio
    # Over-long vectors clamp to unit speed rather than moving faster diagonally.
    diag = g.Game(1)
    diag.step({"move_x": 1.0, "move_y": 1.0, "move_z": 1.0})
    speed = math.sqrt(diag.px ** 2 + diag.py ** 2 + diag.pz ** 2)
    assert abs(speed - g.PLAYER_SPEED * g.DT) < 1e-9, "diagonal is faster than cardinal"


@test
def the_player_moves_on_all_three_axes_and_cannot_leave_the_volume():
    sim = g.Game(1)
    for _ in range(900):
        sim.step({"move_x": 1.0, "move_y": 1.0, "move_z": 1.0})
        assert -g.ARENA_HALF_X + g.PLAYER_RADIUS - 1e-9 <= sim.px <= g.ARENA_HALF_X - g.PLAYER_RADIUS + 1e-9
        assert -g.ARENA_HALF_Y + g.PLAYER_RADIUS - 1e-9 <= sim.py <= g.ARENA_HALF_Y - g.PLAYER_RADIUS + 1e-9
        assert -g.ARENA_HALF_Z + g.PLAYER_RADIUS - 1e-9 <= sim.pz <= g.ARENA_HALF_Z - g.PLAYER_RADIUS + 1e-9
    assert abs(sim.px - (g.ARENA_HALF_X - g.PLAYER_RADIUS)) < 1e-9, "never reached +x"
    assert abs(sim.py - (g.ARENA_HALF_Y - g.PLAYER_RADIUS)) < 1e-9, "never reached +y"
    assert abs(sim.pz - (g.ARENA_HALF_Z - g.PLAYER_RADIUS)) < 1e-9, "never reached +z"


@test
def reaching_the_boundary_grazes_it():
    sim = g.Game(1)
    seen = []
    for _ in range(900):
        seen.extend(sim.step({"move_x": 1.0}))
    assert "wall_graze" in seen, "pushing into the wall never grazed it"
    quiet = g.Game(1)
    early = quiet.step({})
    assert "wall_graze" not in early, "grazed the wall without touching it: %r" % early


@test
def aim_is_chosen_independently_of_movement_in_three_axes():
    sim = g.Game(1)
    events = sim.step({"move_x": -1.0, "aim_z": 1.0, "fire": True})
    assert "fire" in events, events
    assert sim.px < 0.0, "the player did not move along -x"
    assert len(sim.bullets) == 1, "no bullet"
    b = sim.bullets[0]
    assert b["vz"] > 0.0 and abs(b["vx"]) < 1e-9 and abs(b["vy"]) < 1e-9, \
        "bullet followed the movement direction, not the aim: %r" % b


@test
def fire_respects_a_minimum_interval():
    sim = g.Game(1)
    shots = []
    for _ in range(200):
        if "fire" in sim.step({"fire": True, "aim_y": 1.0}):
            shots.append(sim.tick)
    assert len(shots) >= 5, "only %d shots in 200 ticks of held fire" % len(shots)
    gaps = {shots[i + 1] - shots[i] for i in range(len(shots) - 1)}
    assert gaps == {g.FIRE_INTERVAL}, "shot spacing was %r, wanted %d" % (gaps, g.FIRE_INTERVAL)


@test
def bullets_fly_straight_and_leave_the_volume():
    sim = g.Game(1)
    sim.step({"fire": True, "aim_x": 1.0})
    b = dict(sim.bullets[0])
    sim.step({})
    moved = sim.bullets[0]
    assert abs(moved["x"] - (b["x"] + b["vx"] * g.DT)) < 1e-9, "bullet did not integrate"
    assert (moved["vx"], moved["vy"], moved["vz"]) == (b["vx"], b["vy"], b["vz"]), \
        "bullet velocity changed"
    for _ in range(300):
        sim.step({})
        if not sim.bullets:
            break
    assert not sim.bullets, "the bullet never left the arena"


@test
def an_enemy_materialises_before_it_can_be_hit_or_hurt_anyone():
    sim = g.Game(2)
    sim.step({})  # spawn wave 1
    e = sim.enemies[0]
    e["x"], e["y"], e["z"] = 40.0, 0.0, 0.0    # right on top of the player
    e["spawn"] = g.SPAWN_TICKS
    sim.enemies = [e]
    assert sim.state()["enemies"][0]["spawning"] is True, "spawning is not reported"
    seen = []
    for _ in range(g.SPAWN_TICKS - 1):
        seen.extend(sim.step({"fire": True, "aim_x": 1.0}))
    assert "enemy_hit" not in seen, "a materialising enemy was hit: %r" % seen
    assert "player_hit" not in seen, "a materialising enemy hurt the player: %r" % seen
    assert sim.hp == g.PLAYER_START_HP, "health dropped during materialisation"
    # Clear the shots still in flight. One of them arrives a few ticks after the window
    # closes and kills the enemy legitimately - which is correct behaviour and would
    # make the next assertion read as "it never materialised".
    sim.bullets = []
    for _ in range(4):
        sim.step({})
    assert sim.state()["enemies"][0]["spawning"] is False, "never finished materialising"
    seen = []
    for _ in range(120):
        seen.extend(sim.step({"fire": True, "aim_x": 1.0}))
        if "enemy_dead" in seen:
            break
    assert "enemy_hit" in seen, "still could not be hit after materialising: %r" % seen


@test
def there_are_three_kinds_and_they_move_by_different_RULES():
    sim = g.Game(1)
    sim.step({})
    kinds = {e["kind"] for e in sim.enemies}
    assert len(kinds) >= 3, "only %r in the first wave" % sorted(kinds)
    assert kinds <= set(g.KINDS), "unknown kind in %r" % sorted(kinds)

    # Drive one of each from the SAME start and compare the paths. A difference in
    # speed alone would leave them collinear; these must not be.
    paths = {}
    for kind in g.KINDS:
        s = g.Game(1)
        s.step({})
        e = plant(s, 200.0, 0.0, 0.0, kind=kind)
        e["phase"] = 0
        pts = []
        for _ in range(120):
            s.step({})
            if not s.enemies:
                break
            pts.append((s.enemies[0]["x"], s.enemies[0]["y"], s.enemies[0]["z"]))
        paths[kind] = pts

    # the charger spends most of its cycle stationary; the drifter never stops
    drifter_still = sum(1 for a, b in zip(paths[g.KIND_DRIFTER], paths[g.KIND_DRIFTER][1:])
                        if a == b)
    charger_still = sum(1 for a, b in zip(paths[g.KIND_CHARGER], paths[g.KIND_CHARGER][1:])
                        if a == b)
    assert drifter_still == 0, "the drifter stopped moving"
    assert charger_still > 10, "the charger never held still (%d)" % charger_still
    # the weaver leaves the straight line between its start and the player
    off = max(abs(p[1]) + abs(p[2]) for p in paths[g.KIND_WEAVER])
    assert off > 1.0, "the weaver travelled in a straight line (max offset %.3f)" % off


@test
def a_bullet_kills_an_enemy_and_scores():
    sim = g.Game(2)
    sim.step({})
    plant(sim, 80.0, 0.0, 0.0)
    before_score, before_kills = sim.score, sim.kills
    seen = []
    for _ in range(80):
        seen.extend(sim.step({"fire": True, "aim_x": 1.0}))
        if "enemy_dead" in seen:
            break
    assert "enemy_hit" in seen, "the bullet never connected: %r" % seen
    assert "enemy_dead" in seen, "the enemy never died: %r" % seen
    assert sim.kills == before_kills + 1, "kills did not rise"
    assert sim.score > before_score, "score did not rise on a kill"


@test
def a_tougher_enemy_takes_two_hits():
    assert g.Game.wave_hp(1) == 1, "wave 1 enemies should die to one shot"
    later = next(w for w in range(1, 40) if g.Game.wave_hp(w) >= 2)
    sim = g.Game(2)
    sim.wave = later
    sim.pending = 1
    sim.step({})
    plant(sim, 60.0, 0.0, 0.0, hp=g.Game.wave_hp(later))
    hits, deaths = 0, 0
    for _ in range(60):
        events = sim.step({"fire": True, "aim_x": 1.0})
        hits += events.count("enemy_hit")
        deaths += events.count("enemy_dead")
        if deaths:
            break
    assert deaths == 1 and hits == g.Game.wave_hp(later), \
        "wave %d enemy took %d hits for %d deaths" % (later, hits, deaths)


@test
def the_multiplier_rises_on_a_streak_and_collapses_on_damage():
    sim = g.Game(3)
    sim.step({})
    assert sim.multiplier == 1, "did not start at 1"
    raised = []
    for _ in range(g.KILLS_PER_MULT):
        plant(sim, 80.0, 0.0, 0.0)
        for _ in range(80):
            events = sim.step({"fire": True, "aim_x": 1.0})
            raised.extend(events)
            if "enemy_dead" in events:
                break
    assert sim.multiplier == 2, "%d kills left the multiplier at %d" % (
        g.KILLS_PER_MULT, sim.multiplier)
    assert "multiplier" in raised, "no multiplier event was emitted"

    # a kill at x2 is worth more than the same kill at x1
    at_two = sim.score
    plant(sim, 80.0, 0.0, 0.0)
    for _ in range(80):
        if "enemy_dead" in sim.step({"fire": True, "aim_x": 1.0}):
            break
    gained = sim.score - at_two
    assert gained == g.SCORE_PER_KILL * sim.wave * 2, \
        "a kill at x2 scored %d" % gained

    # taking damage collapses it
    plant(sim, 20.0, 0.0, 0.0)
    seen = []
    for _ in range(200):
        seen.extend(sim.step({}))
        if "player_hit" in seen:
            break
    assert "player_hit" in seen, "never took damage: %r" % seen
    assert sim.multiplier == 1, "the multiplier survived damage at %d" % sim.multiplier
    assert seen.count("multiplier") >= 1, "no multiplier event on the collapse"


@test
def touching_the_player_costs_health_and_destroys_the_enemy():
    sim = g.Game(4)
    sim.step({})
    plant(sim, 20.0, 0.0, 0.0)
    hp_before = sim.hp
    seen = []
    for _ in range(120):
        seen.extend(sim.step({}))
        if "player_hit" in seen:
            break
    assert "player_hit" in seen, "the enemy never reached the player: %r" % seen
    assert sim.hp == hp_before - 1, "health did not drop"
    assert "enemy_dead" in seen, "the colliding enemy was not destroyed"


@test
def there_is_a_grace_window_after_being_hit():
    sim = g.Game(5)
    hit_ticks = []
    for _ in range(6000):
        if "player_hit" in sim.step({}):
            hit_ticks.append(sim.tick)
        if sim.game_over:
            break
    assert len(hit_ticks) >= 2, "the player was hit %d times standing still" % len(hit_ticks)
    for a, b in zip(hit_ticks, hit_ticks[1:]):
        assert b - a >= g.INVULN_TICKS, "hit twice within the grace window (%d -> %d)" % (a, b)


@test
def zero_health_ends_the_game_once_and_freezes_it():
    sim = g.Game(5)
    overs = 0
    for _ in range(12000):
        events = sim.step({})
        overs += events.count("game_over")
        if sim.game_over:
            break
    assert sim.game_over, "standing still never killed the player"
    assert overs == 1, "game_over fired %d times" % overs
    st = sim.state()
    assert st["player"]["hp"] == 0 and st["player"]["alive"] is False, st["player"]
    frozen = sim.state()
    for _ in range(100):
        assert sim.step({"move_y": 1.0, "fire": True, "aim_y": 1.0}) == [], \
            "events kept firing after game over"
    assert sim.state() == frozen, "the world kept changing after game over"


@test
def clearing_a_wave_starts_a_bigger_one():
    sim, log = play(7, 9000, hunter)
    starts = [t for t, events in log if "wave_start" in events]
    assert len(starts) >= 3, "only %d waves in 9000 ticks: %r" % (len(starts), starts)
    assert sim.wave >= 3, "wave counter stuck at %d" % sim.wave
    assert g.Game.wave_count(2) > g.Game.wave_count(1), "waves do not grow"
    assert g.Game.wave_speed(2) > g.Game.wave_speed(1), "waves do not speed up"
    assert g.Game.wave_speed(999) <= g.ENEMY_MAX_SPEED, "enemy speed has no ceiling"


@test
def ids_are_unique_and_never_reused_and_lists_are_sorted():
    retired = set()
    live = set()
    sim = g.Game(9)
    for _ in range(3000):
        sim.step(hunter(sim))
        st = sim.state()
        enemy_ids = [e["id"] for e in st["enemies"]]
        bullet_ids = [b["id"] for b in st["bullets"]]
        assert enemy_ids == sorted(enemy_ids), "enemies are not sorted by id"
        assert bullet_ids == sorted(bullet_ids), "bullets are not sorted by id"
        now = set(enemy_ids) | set(bullet_ids)
        assert len(now) == len(enemy_ids) + len(bullet_ids), "an id is shared by two entities"
        assert not (now & retired), "a retired id came back: %r" % sorted(now & retired)
        retired |= (live - now)
        live = now
    assert len(retired) > 20, "hardly any entities lived and died (%d)" % len(retired)


@test
def state_shape_is_exactly_the_contract():
    st = g.Game(1).state()
    assert set(st) == {"arena", "player", "enemies", "bullets", "wave", "score",
                       "kills", "multiplier", "game_over"}, sorted(st)
    assert set(st["arena"]) == {"half_x", "half_y", "half_z"}
    assert set(st["player"]) == {"x", "y", "z", "hp", "alive"}
    sim = g.Game(1)
    sim.step({"fire": True, "aim_y": 1.0})
    st = sim.state()
    assert set(st["enemies"][0]) == {"id", "kind", "x", "y", "z", "hp", "spawning"}, \
        sorted(st["enemies"][0])
    assert set(st["bullets"][0]) == {"id", "x", "y", "z", "vx", "vy", "vz"}, \
        sorted(st["bullets"][0])


@test
def every_trace_line_is_finite_and_only_uses_contracted_events():
    allowed = {"fire", "enemy_spawn", "enemy_hit", "enemy_dead", "player_hit",
               "wall_graze", "multiplier", "wave_start", "game_over"}
    sim = g.Game(11)
    for _ in range(2500):
        events = sim.step(hunter(sim))
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
