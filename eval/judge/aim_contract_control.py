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

`--contract` pins the specified half in both directions against `Game` alone: it needs no
probe, no `just` and no subprocess. The default run adds the two measurements that take
minutes because they drive the whole play-bot - the tick census, and one arm per reading
- and is the producer for the figures `eval/RUNS.md` states for this boundary.
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


def held_shot(mod, arm: str):
    """Aim +y, fire, then hold fire with NO aim field. Returns that shot's velocity."""
    g = mod.Game(7)
    g.step({"fire": True, "aim_x": 0.0, "aim_y": 1.0, "aim_z": 0.0})
    before = {b["id"] for b in g.state()["bullets"]}
    for _ in range(30):
        g.step({"fire": True})
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
        got = held_shot(load_game(build(arm), arm), arm)
        want = EXPECTED_HELD_SHOT[arm]
        ok = same(got, want)
        rows.append(("%-7s %s" % (arm, ARM_NOTE[arm]),
                     "shot with no aim field: %s" % (want,),
                     "ok" if ok else "UNMET: got %s" % (got,)))
        if not ok:
            problems.append(
                "the aim contract: arm %r fired %s where the prompt's sentence requires "
                "%s. Either `_update_aim` no longer implements what `_G3_INPUTS` states, "
                "or this arm has stopped biting." % (arm, got, want))
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

    `_moves` opens the run with exactly 90 pure-movement ticks; `_firing_in` sends 120
    ticks aiming +x. If the reader cannot tell those apart it is reporting itself.
    """
    rows = []
    head = sent[:90]
    ok = (len(head) == 90
          and all(set(d) == {"move_x", "move_y", "move_z"} for d in head)
          and all(_aim_mag(d) <= 1e-6 for d in head))
    rows.append(("the 90 opening `player.moves` ticks carry no aim field",
                 "all read as zero-aim", "ok" if ok else "UNMET"))
    if not ok:
        problems.append("the census extraction: the 90 opening pure-movement ticks did "
                        "not read as zero-aim, so its zero is not trustworthy.")

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

    if c["zero"] == 0:
        problems.append(
            "the census found no zero-aim tick at all. The bot has changed, and the "
            "case this control exists for may now be unreachable - which would be a "
            "result, but it must be established rather than read off a silent zero.")

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
