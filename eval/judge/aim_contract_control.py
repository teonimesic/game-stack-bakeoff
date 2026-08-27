#!/usr/bin/env python3
"""Does `ref_arena` obey the aim contract the g3_arena prompt states, and does any
criterion score the part of it the prompt leaves free?

The prompt (`suites/wholegame_prompts.py`, `_G3_INPUTS`) says two things about aim:

* an aim vector of zero length - including a tick that omits the aim fields - is *no new
  direction this tick*: the gun holds its last orientation and `fire` still fires along
  it. **Specified**, so a criterion may rest on it.
* where the gun points before any aim has ever been given is the submission's choice.
  **Free**, so nothing may be graded on it.

Until 2026-08-25 the prompt said neither. The reference held the last aim, the play-bot
sent 33 firing ticks with no aim field in them, and a submission reading a zero aim as
"return to +x" or as "no direction, so no shot" was consistent with every word of the
task and inconsistent with the reference the criteria were written against.

    python3 aim_contract_control.py --contract   # offline, sub-second, gated
    python3 aim_contract_control.py              # the above, plus the census and arms

`--contract` pins the specified half in both directions against `Game` alone, in both
shapes a zero aim arrives in - the fields omitted, and the fields present and zero - and
needs no probe, no `just` and no subprocess. The default run adds what has to drive the
whole play-bot: the tick census, and one arm per reading. It is the producer for the
figures `eval/RUNS.md` states for this boundary.
"""

from __future__ import annotations

import argparse
import importlib.util
import math
import shutil
import sys
import tempfile
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIXTURE = HERE / "fixtures" / "ref_arena"
sys.path.insert(0, str(HERE))

# --------------------------------------------------------------------------- #
# The arms
# --------------------------------------------------------------------------- #
# Each is a source patch on a copy of the fixture, and each refuses if its target is not
# present exactly once - a mutation that silently fails to mutate is worse than none.

HOLD = """        if mag > 1e-6:
            self.aim_x, self.aim_y, self.aim_z = ax / mag, ay / mag, az / mag
"""

RESET_AIM = "        self.aim_x = 1.0\n        self.aim_y = 0.0\n        self.aim_z = 0.0\n"
FIRE_GUARD = '        if not inputs.get("fire") or self.fire_cooldown > 0:\n'

#: `None` is the fixture unmodified.
AIM_PATCH = {
    "ref": None,
    "resetx": """        if mag > 1e-6:
            self.aim_x, self.aim_y, self.aim_z = ax / mag, ay / mag, az / mag
        else:  # ARM: no direction given, so the gun returns to +x
            self.aim_x, self.aim_y, self.aim_z = 1.0, 0.0, 0.0
""",
    "nofire": """        if mag > 1e-6:
            self.aim_x, self.aim_y, self.aim_z = ax / mag, ay / mag, az / mag
        self.aim_given = mag > 1e-6  # ARM: no direction given, so withhold the shot
""",
    "startz": HOLD,   # the contract is untouched; only the FREE starting orientation moves
}

#: What each arm does with a firing tick that carries no aim field, after the gun has
#: been aimed along +y. Stated here, independently of the code that produces it.
EXPECTED_HELD_SHOT = {
    "ref": (0.0, 520.0, 0.0),
    "startz": (0.0, 520.0, 0.0),
    "resetx": (520.0, 0.0, 0.0),
    "nofire": None,
}

ARM_NOTE = {
    "ref": "the reference as shipped: the gun holds its last orientation, starting at +x",
    "startz": "the FREE half moved: an identical game whose gun starts at -z, which is "
              "what 8 of the 8 stored 3D-arena submissions chose",
    "resetx": "a reading the prompt now forbids: a zero aim returns the gun to +x",
    "nofire": "the other reading it now forbids: a zero aim withholds the shot",
}


def build(arm: str) -> Path:
    """Copy the fixture and apply `arm`. Exits 1 if a patch target has moved."""
    repo = Path(tempfile.mkdtemp(prefix="aim-%s-" % arm)) / "ref_arena"
    shutil.copytree(FIXTURE, repo, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    patch = AIM_PATCH[arm]
    if patch is None and arm == "ref":
        return repo
    game = repo / "game.py"
    text = game.read_text()

    def swap(old: str, new: str) -> None:
        nonlocal text
        n = text.count(old)
        if n != 1:
            raise SystemExit(
                "arm %r: its target appears %d times in %s, expected exactly 1. The "
                "fixture has changed and this arm no longer bites.\n--- target ---\n%s"
                % (arm, n, game, old))
        text = text.replace(old, new)

    swap(HOLD, patch)
    if arm == "nofire":
        swap(RESET_AIM, RESET_AIM + "        self.aim_given = False\n")
        swap(FIRE_GUARD,
             '        if not inputs.get("fire") or not self.aim_given '
             'or self.fire_cooldown > 0:\n')
    if arm == "startz":
        swap(RESET_AIM,
             "        self.aim_x = 0.0\n        self.aim_y = 0.0\n"
             "        self.aim_z = -1.0\n")
    game.write_text(text)
    return repo


def load_game(repo: Path, arm: str):
    spec = importlib.util.spec_from_file_location("game_%s" % arm, repo / "game.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


#: The two ways the prompt's *zero-length aim* can arrive on the wire. They are one
#: sentence in the task and two shapes in a submission - `"aim_x" in inputs` separates
#: them, and a reader written that way is honest and reads the contract wrongly on one of
#: the two. The play-bot sends only the first; a mouse or a stick releasing to centre
#: sends the second, so both are in scope and both are checked.
NO_AIM_TICKS = {
    "omitted": {"fire": True},
    "explicit zero": {"fire": True, "aim_x": 0.0, "aim_y": 0.0, "aim_z": 0.0},
}


def held_shot(mod, no_aim: dict):
    """Aim +y and fire, then hold `no_aim` until a shot comes out. Returns its velocity.

    `no_aim` carries no direction, so what comes out is the arm's answer to the
    unspecified case. `None` means the arm never fired again.
    """
    g = mod.Game(7)
    g.step({"fire": True, "aim_x": 0.0, "aim_y": 1.0, "aim_z": 0.0})
    before = {b["id"] for b in g.state()["bullets"]}
    for _ in range(30):
        g.step(dict(no_aim))
        new = [(b["vx"], b["vy"], b["vz"]) for b in g.state()["bullets"]
               if b["id"] not in before]
        if new:
            return new[0]
    return None


def same(got, want) -> bool:
    if got is None or want is None:
        return got is None and want is None
    return all(abs(a - b) < 1e-6 for a, b in zip(got, want))


# --------------------------------------------------------------------------- #
# The specified half - offline, and the gated one
# --------------------------------------------------------------------------- #

def contract(problems: list[str]) -> list[tuple[str, str, str]]:
    """The reference holds its last aim, and two arms that do not are visible here.

    The positive row alone would pass against a fixture that always fired +y; the two
    arms are what make it a measurement rather than an observation.
    """
    rows = []
    for arm in ("ref", "resetx", "nofire"):
        mod = load_game(build(arm), arm)
        want = EXPECTED_HELD_SHOT[arm]
        for shape, no_aim in NO_AIM_TICKS.items():
            got = held_shot(mod, no_aim)
            ok = same(got, want)
            rows.append(("%-7s %s" % (arm, ARM_NOTE[arm]),
                         "%-13s -> %s" % (shape, want),
                         "ok" if ok else "UNMET: got %s" % (got,)))
            if not ok:
                problems.append(
                    "the aim contract: arm %r fired %s where the prompt's sentence "
                    "requires %s, on a zero aim of the %r shape. Either `_update_aim` no "
                    "longer implements what `_G3_INPUTS` states, or this arm has "
                    "stopped biting." % (arm, got, want, shape))
    return rows


# --------------------------------------------------------------------------- #
# The free half, and the census - both need the play-bot
# --------------------------------------------------------------------------- #

def _axis(d: dict, k: str) -> float:
    v = d.get(k)
    try:
        f = float(bool(v)) if isinstance(v, bool) else float(v)
    except (TypeError, ValueError):
        return 0.0
    return f if math.isfinite(f) else 0.0


def _aim_mag(d: dict) -> float:
    return math.sqrt(sum(_axis(d, k) ** 2 for k in ("aim_x", "aim_y", "aim_z")))


def drive(arm: str):
    """Run the arena play-bot against `arm`, recording every tick's inputs.

    `ProbeSession.step_raw` is the single choke point: the interactive criteria and
    `checks.hash_chain`'s tape replay both go through it.
    """
    import probe
    import bot_arena

    sent: list[dict] = []
    original = probe.ProbeSession.step_raw

    def spy(self, inputs):
        sent.append(dict(inputs))
        return original(self, inputs)

    probe.ProbeSession.step_raw = spy                # type: ignore[method-assign]
    try:
        out = probe.drive(bot_arena.BOT, build(arm))
    finally:
        probe.ProbeSession.step_raw = original       # type: ignore[method-assign]
    verdicts = {c["id"]: (bool(c["passed"]), bool(c["scored"])) for c in out["criteria"]}
    return sent, verdicts, out


def census(sent: list[dict]) -> dict:
    zero = [d for d in sent if _aim_mag(d) <= 1e-6]
    firing = [d for d in zero if d.get("fire") is True or d.get("fire") == 1.0]
    return {"ticks": len(sent), "zero": len(zero), "zero_firing": len(firing),
            "shapes": Counter(tuple(sorted(d.keys())) for d in zero)}


def extraction_control(sent: list[dict], problems: list[str]) -> list[tuple[str, str, str]]:
    """Two rows whose true value is stated before the census is believed (rule 12).

    The tape opens with exactly 92 pure-movement ticks and `ref_arena` is what makes
    that number what it is: 1 from the main session's `_take_control`, which holds a
    full +x push and returns on the first tick the player answers - here tick 1, moving
    3.4 units against a 1.0-unit threshold - then 90 from `_moves`, 30 on each axis,
    then 1 more because `enemies.spawn` finds the wave already present and steps
    nothing, so the next tick on the tape is `_kinds`' own `_take_control`. Tick 93 is
    that session's first `_play_inputs`, which carries an aim and a fire.
    `_firing_in` sends 120 ticks aiming +x. If the reader cannot tell those apart it is
    reporting itself.

    BOTH DIRECTIONS, because "the first 92 are pure movement" is also true of any
    smaller prefix: the row asserts that tick 93 is NOT one of them, so the boundary is
    exact rather than merely satisfied. The 92 is written here rather than read out of
    `bot_arena` - a control that imports its expectation from its subject is not a
    control - so a change to the opening wait, to the per-axis push or to the order of
    the sessions turns this row red, which is the point of it.
    """
    rows = []
    opening = 92
    head = sent[:opening]
    ok = (len(head) == opening
          and all(set(d) == {"move_x", "move_y", "move_z"} for d in head)
          and all(_aim_mag(d) <= 1e-6 for d in head)
          and len(sent) > opening
          and set(sent[opening]) != {"move_x", "move_y", "move_z"})
    rows.append((f"the {opening} opening `_take_control` and `player.moves` ticks carry "
                 f"no aim field", "all read as zero-aim, and tick 93 does not",
                 "ok" if ok else "UNMET"))
    if not ok:
        problems.append(f"the census extraction: the {opening} opening pure-movement "
                        f"ticks did not read as zero-aim, or the tick after them did, "
                        f"so its zero is not trustworthy.")

    aimed = [d for d in sent
             if abs(_axis(d, "aim_x") - 1.0) < 1e-9
             and _axis(d, "aim_y") == 0.0 and _axis(d, "aim_z") == 0.0]
    ok2 = len(aimed) >= 120 and all(abs(_aim_mag(d) - 1.0) < 1e-9 for d in aimed)
    rows.append(("the `aim.independent` ticks aim +x",
                 "none reads as zero-aim (n>=120)",
                 "ok" if ok2 else "UNMET: n=%d" % len(aimed)))
    if not ok2:
        problems.append("the census extraction: ticks aiming +x did not read as "
                        "non-zero, so its count of zero-aim ticks is not trustworthy.")
    return rows


def arms(problems: list[str]) -> list[tuple[str, str, str]]:
    base_sent, base_verdicts, base_out = drive("ref")
    c = census(base_sent)
    rows = extraction_control(base_sent, problems)

    print("\ncensus - population: every tick the arena play-bot sends against `ref`")
    print("  ticks sent                      %d" % c["ticks"])
    print("  carrying a zero or absent aim   %d" % c["zero"])
    print("  of those, holding `fire`        %d" % c["zero_firing"])
    for keys, n in c["shapes"].most_common():
        print("      %6d  %s" % (n, list(keys) or "{} (no input at all)"))
    print("  criteria passed                 %s/%s\n" % (base_out["passed"],
                                                         base_out["total"]))

    # Both of these fail closed. A zero here is the shape of a bot that no longer drives
    # the case AND the shape of a census aimed at the wrong field, and neither may pass
    # quietly: the FIRING count is the one that carries the ticket, because a zero-aim
    # tick that does not fire cannot make two honest submissions diverge on a shot.
    rows.append(("the play-bot drives the unspecified case",
                 "some tick carries a zero or absent aim",
                 "ok (%d)" % c["zero"] if c["zero"] else "UNMET: 0"))
    rows.append(("...and fires on it",
                 "some zero-aim tick holds `fire`",
                 "ok (%d)" % c["zero_firing"] if c["zero_firing"] else "UNMET: 0"))
    if c["zero"] == 0 or c["zero_firing"] == 0:
        problems.append(
            "the census found %d zero-aim tick(s), %d of them firing. A zero here means "
            "the bot no longer drives the case this control exists for, so the arms "
            "below are measuring nothing - which may be a result, but it has to be "
            "established rather than read off a silent zero."
            % (c["zero"], c["zero_firing"]))

    for arm in ("startz", "resetx", "nofire"):
        _, verdicts, _ = drive(arm)
        differ = sorted(k for k in base_verdicts
                        if verdicts.get(k) != base_verdicts[k])
        ok = not differ
        rows.append(("%-7s %s" % (arm, ARM_NOTE[arm]),
                     "every criterion returns what `ref` returned",
                     "ok" if ok else "UNMET: %s" % differ))
        if differ and arm == "startz":
            problems.append(
                "a criterion moved when only the FREE starting orientation changed: %s. "
                "The prompt leaves that to the submission, so no criterion may rest on "
                "it." % differ)
        elif differ:
            problems.append(
                "arm %r moved %s. That is not automatically wrong - the prompt now "
                "SPECIFIES this case, so a criterion may legitimately fail a submission "
                "that reads it the other way. Decide which, then update this row."
                % (arm, differ))
    return rows


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--contract", action="store_true",
                    help="only the offline half: the reference against the prompt's "
                         "sentence, with two arms that break it")
    args = ap.parse_args(argv)

    problems: list[str] = []
    rows = contract(problems)
    if not args.contract:
        rows += arms(problems)

    width = max(len(r[0]) for r in rows)
    print("aim contract, `ref_arena` against `_G3_INPUTS`")
    for what, expected, verdict in rows:
        print("  %-*s  %-46s %s" % (width, what, expected, verdict))

    if problems:
        print("\n%d problem(s):" % len(problems))
        for p in problems:
            print("  - %s" % p)
        return 1
    print("\n%d row(s) as declared" % len(rows))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
