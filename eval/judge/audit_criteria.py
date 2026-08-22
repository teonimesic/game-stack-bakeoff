#!/usr/bin/env python3
"""Which deterministic criteria have ever fired, on which stacks, and were they right?

Two questions, deliberately separated:

  1. HAS it fired?           - answerable from stored results
  2. COULD it fail a CORRECT submission? - answerable only by construction

A criterion that has never fired is not thereby good. It may be a genuine invariant
nothing has violated (fine), or untestable as written (dead weight). Only (2)
distinguishes them, and (2) is a judgement recorded by hand below, not inferred.

PER-STACK IS MANDATORY. A criterion sound on three stacks and broken on the fourth
presents in aggregate as a 25% failure rate - which reads like a criterion that works.
That is exactly how the Unity project-lock defect stayed invisible (FINDINGS #25).
"""
from __future__ import annotations

import json, glob, sys
from collections import defaultdict
from pathlib import Path

# The run these adjudications belong to. TRIAL IDS REPEAT ACROSS RUNS -
# `g1_pong__unity__t0` is the first Unity Pong trial of EVERY run - so applying this
# table to a different run would silently mark that run's GENUINE failures as harness
# defects, on the strength of a same-named trial in an unrelated run. That is a
# fail-open defect (FINDINGS #31): it excuses real failures, produces a higher score
# than the truth, and shows no anomaly to investigate. The same id collision already
# destroyed a work tree once, which is why work trees are namespaced by run.
ADJUDICATED_RUN = "wg-matrix-2026-08-13T14-02-50"

# Adjudications made by reading the failing submission's archived source.
# "false_negative" = the submission was correct and the criterion fired anyway.
ADJUDICATED: dict[tuple[str, str], str] = {
    ("g1_pong__godot__t0", "ball.wall_bounce"): "false_negative",
    ("g1_pong__unity__t0", "determinism.replay"): "false_negative",
    ("g1_pong__unity__t0", "determinism.seed"): "false_negative",
    ("g1_pong__unity__t1", "ball.wall_bounce"): "false_negative",
    ("g1_pong__unity__t1", "determinism.replay"): "false_negative",
    ("g1_pong__unity__t1", "determinism.seed"): "false_negative",
    ("g2_tetris3d__rust__t0", "move.translates"): "false_negative",
    ("g2_tetris3d__unity__t0", "piece.stacks"): "false_negative",
    ("g2_tetris3d__unity__t0", "gameover.triggers"): "false_negative",
    ("g2_tetris3d__unity__t0", "determinism.replay"): "false_negative",
    ("g2_tetris3d__unity__t0", "determinism.seed"): "false_negative",
    ("g2_tetris3d__unity__t1", "piece.stacks"): "false_negative",
    ("g2_tetris3d__unity__t1", "gameover.triggers"): "false_negative",
    ("g2_tetris3d__unity__t1", "determinism.replay"): "false_negative",
    ("g2_tetris3d__unity__t1", "determinism.seed"): "false_negative",
    ("g3_arena__rust__t0", "enemies.chase"): "false_negative",
}

# Can a plausible CORRECT submission fail this criterion? Recorded by construction.
#
# REPAIRED entries keep the original finding, because the answer "no" is only worth
# anything alongside what it used to be. Each repair turned an observation into an
# experiment and each is pinned in BOTH directions by `bot_mutants.py`: the healthy
# reference fixture must pass it, and a fixture with the behaviour surgically removed
# must fail it, scored. A repair that only removed false negatives would be a criterion
# that can no longer fail, which is worse than the defect it replaced.
CONSTRUCTIBLE_FAILURE: dict[str, str] = {
    "ball.wall_bounce": "REPAIRED - was: a shallow serve never reaches a wall while "
                        "paddles are centred. Now the bot meets the ball off-centre "
                        "with a searched paddle offset and drives it into a wall. "
                        "Mutant: remove the vertical reflection.",
    "move.translates": "REPAIRED - was: a piece already against a wall correctly "
                       "refuses to move. Now the direction is chosen from the piece's "
                       "cells and the well dimensions, every side with clearance is "
                       "tried, and a piece that spans the well is NOT MEASURED rather "
                       "than failed. Mutant: ignore the horizontal move inputs.",
    "determinism.replay": "REPAIRED - was: any engine holding a project lock refuses a "
                          "second session. ProbeSession now serialises sessions per "
                          "repository and a lock conflict comes back unscored. "
                          "Mutant: seed from pid and wall-clock time.",
    "determinism.seed": "REPAIRED - same mechanism. Mutant: ignore the seed argument.",
    "piece.stacks": "REPAIRED - same mechanism (opens its own session). Mutant: never "
                    "add locked cells to the settled grid.",
    "gameover.triggers": "REPAIRED - same mechanism (opens its own session). Mutant: "
                         "never set game_over.",
    "render.animates": "yes - a low-contrast game animates below the pixel-diff tolerance",
    "layer.clears": "yes - demoted already; no correct implementation satisfied it",
    "score.rewards_clears": "yes - depends on layer.clears",
    "enemies.chase": "REPAIRED TWICE. (1) was: the nearest enemy reaches the player "
                     "and is destroyed on contact, so the NEXT nearest is further "
                     "away; the criterion failed when an enemy chased most "
                     "effectively. (2) 2026-08-16, was: it watched a distance shrink "
                     "while the player STOOD STILL, which is fatal in this game - on "
                     "all six real submissions the player was already dead and the "
                     "evidence read 'distance went 0.4 -> 0.4'. Now it runs in its own "
                     "session and the player CIRCLES one enemy at a fixed radius: "
                     "every step the enemy takes must point at the player (measured "
                     "per tick) and its heading must turn when the player moves. A "
                     "contact counts only if the enemy was closing, so a collision the "
                     "player caused cannot pass it. Mutant: enemies walk a fixed "
                     "heading. Variant: enemies faster than the player, which is the "
                     "only way to reach the contact branch.",
    "enemy.kinds": "REPAIRED 2026-08-16 - was: it sampled kinds while the player sent "
                   "empty inputs, so the bot died in wave 1 and never met kinds that "
                   "unlock in waves 2, 3 and 4. All six real submissions ship four "
                   "kinds gated by wave and all six were failed with the evidence "
                   "'distinct kinds observed: [drifter]'. Now it plays - aim, fire, "
                   "hold a standoff - so meeting three kinds requires clearing waves, "
                   "and the evidence reports the wave reached so a submission defect "
                   "can be told from a bot that never established its condition. "
                   "Mutant: one kind wearing three names. THE REFERENCE was changed "
                   "with it: it used to spawn all three kinds in every wave, so the "
                   "criterion passed by construction and no mutant could have found "
                   "this.",
    "paddle.moves": "REPAIRED - was: the paddle may already be pinned against the "
                    "ceiling when the check starts. Now measured on its own session "
                    "from a paddle parked at the bottom.",
    "paddle.bounded": "REPAIRED - was: a fixed 900-tick hold assumed to be long enough. "
                      "Now holds until the paddle stops moving.",
}


# A probe that died before emitting tick 0 measured NOTHING about the submission.
# That is not a judgement call, so it is detected rather than hand-listed: the failure
# says the harness could not start, not that the game is wrong. Everything else stays
# in ADJUDICATED, decided by reading source.
HARNESS_SIGNATURES = ("probe unusable", "while waiting for the tick-0 header",
                      "another unity instance", "cannot open the same project")


def is_harness_failure(trial: str, cid: str, evidence: str,
                       adjudications_apply: bool) -> bool:
    if adjudications_apply and ADJUDICATED.get((trial, cid)) == "false_negative":
        return True
    e = (evidence or "").lower()
    return ("probe unusable" in e or "waiting for the tick-0 header" in e)


def main(run_dir: str) -> int:
    # Hand-made adjudications are valid ONLY for the run they were made against.
    adjudications_apply = Path(run_dir).name == ADJUDICATED_RUN
    if not adjudications_apply:
        print(f"NOTE: the {len(ADJUDICATED)} hand adjudications in this file belong to "
              f"{ADJUDICATED_RUN!r} and are NOT applied to {Path(run_dir).name!r}.\n"
              f"      Trial ids repeat across runs, so applying them would excuse this "
              f"run's genuine failures.\n"
              f"      Every failure below is counted as GENUINE until somebody reads the "
              f"submission and says otherwise.\n")
    fired: dict[str, list[tuple[str, str]]] = defaultdict(list)   # cid -> [(trial, stack)]
    seen: dict[str, set[str]] = defaultdict(set)                  # cid -> stacks evaluated
    tiers: dict[str, str] = {}
    n = 0
    for p in sorted(glob.glob(f"{run_dir}/artifacts/*/eval/report.json")):
        r = json.loads(Path(p).read_text()); tid = p.split("/")[-3]
        game, stack, _t = tid.split("__"); n += 1
        for tier in ("programmatic", "playbot"):
            for c in r[tier]["criteria"]:
                if not c.get("scored", True):
                    continue
                cid = c["id"]; tiers[cid] = tier
                seen[cid].add(stack)
                if not c["passed"]:
                    fired[cid].append((tid, stack, c.get("evidence", "")))
    print(f"{n} evaluated submissions\n")
    print(f"{'criterion':<26}{'tier':<14}{'fired':>6}{'genuine':>9}{'false':>7}  stacks affected")
    dead = []
    harmful = []
    working = []
    for cid in sorted(tiers, key=lambda c: (tiers[c], c)):
        hits = fired.get(cid, [])
        fn = sum(1 for t, _s, ev in hits
                 if is_harness_failure(t, cid, ev, adjudications_apply))
        gen = len(hits) - fn
        stacks = sorted({s for _t, s, _e in hits})
        print(f"{cid:<26}{tiers[cid]:<14}{len(hits):>6}{gen:>9}{fn:>7}  {','.join(stacks) or '-'}")
        if not hits:
            dead.append(cid)
        elif gen == 0:
            harmful.append(cid)
        else:
            working.append(cid)
    print(f"\n--- verdict ---")
    print(f"criteria that have NEVER fired          : {len(dead)}")
    print(f"criteria that fired ONLY wrongly        : {len(harmful)}  {harmful}")
    print(f"criteria that caught a genuine defect   : {len(working)}  {working}")
    print(f"\nof the never-fired, those a correct submission COULD still fail:")
    for cid in dead:
        if cid in CONSTRUCTIBLE_FAILURE:
            print(f"  {cid}: {CONSTRUCTIBLE_FAILURE[cid]}")
    print(f"\nSTACK ASYMMETRY (a criterion firing on one stack only is bias, not noise):")
    for cid, hits in sorted(fired.items()):
        stacks = {s for _t, s, _e in hits}
        if len(stacks) == 1 and len(seen[cid]) > 1:
            print(f"  {cid}: fires ONLY on {stacks.pop()} (evaluated on {len(seen[cid])} stacks)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1] if len(sys.argv) > 1
                          else "runs/wg-matrix-2026-08-13T14-02-50"))
