#!/usr/bin/env python3
"""Evaluate one submission across all three tiers and write a re-judgeable record.

Usage:
    ./evaluate.py --submission <dir> --starter <dir> --game g2_tetris3d \
                  --out runs/wholegame-.../eval/<trial_id>            [--no-judge]

Everything the tiers looked at is written under `--out`, so the run can be re-scored
offline later without paying for new agent rollouts. That is deliberately the same idea
as SWE-bench's `rewrite_reports` and this repo's own `regrade.py`: a grading bug should
cost a re-run of the grader, not a re-run of the agents.
"""

from __future__ import annotations

import argparse
import datetime as dt
import importlib
import json
import os
import shutil
import sys
import time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import aspects  # noqa: E402
import probe  # noqa: E402
import static  # noqa: E402

# USER RULING: the judge tier contributes ZERO to the score. It still runs on every
# submission and its per-criterion verdicts are reported, but as a DIAGNOSTIC only.
# Two independent arguments, which fail differently:
#
#   1. It cannot reorder anything. Bounded contribution 0.10 against a tightest
#      adjacent gap of 0.0622 between submissions on the deterministic tiers. True
#      regardless of how noisy the judge is.
#   2. Its aggregate is noisiest exactly where it would matter. Measured over six
#      judgings each: score spread 0.000 on an uncontested submission, 0.308 on a
#      contested one, with instability reaching 0.462. True regardless of weight.
#
# Zero means zero - not a token weight. See RUBRIC.md and FINDINGS.md #21.
def _atomic(path: Path, obj: Any) -> None:
    """Write JSON via a temp file and rename, so a concurrent writer cannot interleave.

    MEASURED: two judge processes were pointed at the same `judge.json` and both wrote
    it. The result was two JSON documents spliced together in one file - which parsed
    cleanly for a moment, was read, and produced a headline number that was published
    before the corruption surfaced.
    """
    tmp = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps(obj, indent=2))
    os.replace(tmp, path)


# TIER 1 IS A GATE, NOT A SCORE - decided 2026-08-23, on measurement (task 29).
#
# It used to carry 0.31 of `overall` against tier 2's 0.69, a split that appeared in
# the first commit of this repository, was quoted in four documents, and was derived in
# none of them. Two offline sweeps over the stored corpus, both re-runnable:
#
#   judge/weight_sensitivity.py --all   10 groups, FLIPS=0 at every weight in (0,1);
#                                       7 of 10 UNIDENTIFIABLE because tier 1 returns a
#                                       SINGLE value across the whole group (#92).
#   judge/tier1_census.py               68 stored trials, 7 with any tier-1 failure. Two
#                                       are the same build failure (#49) whose tier-2
#                                       0.00 is a restatement of it; the other five are
#                                       a lint finding, three of a submission's own unit
#                                       tests, and an ink-coverage window - on games that
#                                       scored 1.00 on tier 2. In 0 of 10 groups do both
#                                       tiers vary among the trials tier 2 could measure.
#
# So the weight has never had two signals to combine. What tier 1 does is separate a
# submission that fails outright from one that does not, which is a FLOOR TEST, and a
# floor test reported as 0.31 of a quality score reads a lint finding as 4.4% worse game.
#
# The gate keeps every criterion and the whole per-criterion report; it removes only the
# arithmetic that turned them into a fraction of the grade. `tier1_census.py` prints
# FLOOR-ONLY today and DISCRIMINATES the day a tier-1 criterion with real headroom is
# added - at which point this decision has to be re-made rather than inherited.
GATE_TIER = "programmatic"
WEIGHTS = {"playbot": 1.0}
DIAGNOSTIC_TIERS = ("judge",)

#: Stamped into every record so a corpus spanning the change is partitionable. A stored
#: number whose regime you cannot name is not comparable with anything (eval/RUNS.md).
SCORING_REGIME = "gate-2026-08-23"

#: The tier-1 criteria tier 2 DEPENDS ON. The play-bot drives the submission through
#: `just probe`, so a project that does not build, or whose probe never answers, cannot
#: produce tier-2 evidence: its 0.00 there is the same fact as the gate failure, not a
#: second one. `render.frames` is deliberately not here - the bot drives the probe, not
#: the film, so a broken capture recipe still leaves the game measurable.
#: Corroborated, not merely asserted: over the stored corpus every trial that failed one
#: of these has tier 2 = 0.00 (2 of 2) and every trial that failed only other tier-1
#: criteria has tier 2 > 0 (5 of 5). `tier1_census.py` prints that 2x2.
BLOCKING_CRITERIA = ("build.compiles", "probe.responds")


def gate_verdict(tier1: dict[str, Any]) -> dict[str, Any]:
    """PASS iff every SCORED tier-1 criterion passed. Fail-closed on an empty tier.

    An empty criteria list is NOT a pass. `total=0 passed=0` is indistinguishable from
    correct failure, and a gate that green-lights a tier that ran nothing is the exact
    shape this repository keeps finding (rule 1).

    `scored=False` criteria are excluded from the question, not counted as failures:
    that flag marks the engine project-lock exception, which says nothing about the
    submission and can only arise on a subset of the arms (FINDINGS #25).
    """
    crits = [c for c in (tier1.get("criteria") or []) if c.get("scored", True)]
    failed = [c["id"] for c in crits if not c.get("passed")]
    blocking = [cid for cid in failed if cid in BLOCKING_CRITERIA]
    return {
        "tier": GATE_TIER,
        "usable": bool(crits),
        "passed": bool(crits) and not failed,
        "n_scored": len(crits),
        "n_failed": len(failed),
        "failed": failed,
        "blocking_failed": blocking,
        # False means: this trial's `overall` is not independent evidence about the
        # game. Tier 2 could not observe anything, so its score restates the gate.
        "score_is_independent": not blocking,
        "fraction_passed": (round((len(crits) - len(failed)) / len(crits), 4)
                            if crits else None),
    }


def overall_score(tier_scores: dict[str, float]) -> float:
    """`overall` from the SCORED tiers. Tier 1 is not one of them; see WEIGHTS."""
    return round(sum(WEIGHTS[k] * float(tier_scores.get(k, 0.0)) for k in WEIGHTS), 4)


BOTS = {
    "g1_pong": "bot_pong",
    "g2_tetris3d": "bot_tetris3d",
    "g3_arena": "bot_arena",
    "g4_platformer": "bot_platformer",
}

#: WHICH TIER-2 INSTRUMENT EACH TASK GETS, keyed by TASK ID and not derived from the task
#: class.
#:
#: A scene has no player, so a play-bot has no referent (`eval/SCENES.md`); the scene
#: probe replaces it and carries the same weight. Deriving this table from
#: `aspects.task_class` would make the guard below a check that cannot fail - it would be
#: comparing the class against itself. Written out per task, it is a SECOND statement of
#: what each task is, and `aspects.applicability` compares the two: a row that says
#: `"s3_something": "playbot"` is refused before anything is driven.
#:
#: A task id that is not here is refused as well. Until 2026-08-25 the only thing standing
#: between a scene and a play-bot was `BOTS[game]` raising `KeyError`, which is a refusal
#: by accident of a dict holding four keys rather than by design.
TIER2_INSTRUMENT = {
    "g1_pong": "playbot",
    "g2_tetris3d": "playbot",
    "g3_arena": "playbot",
    "g4_platformer": "playbot",
    "s1_parallax": "scene_probe",
    "s2_glass": "scene_probe",
}


#: THE SECOND SEED THE SCENE PROBE NEEDS, as an offset from the run's seed.
#:
#: `seed.pair` is two-sided on purpose (`eval/SCENES.md`): *different seeds differ* alone
#: is satisfied by anything random including a wall-clock source, and *same seed matches*
#: alone by a canned animation. So the probe needs a second seed, and it must not be the
#: first. The offset is 92 so that the standing `--seed 7` gives 99 - the pair every
#: fixture in `scene_mutants.py` was validated at - while a run at another seed still
#: gets a distinct second one rather than silently collapsing the control.
SCENE_SEED_OFFSET = 92


def assert_legacy_judge_allowed(task: str) -> None:
    """THE THIRD RUNNER PATH: `--with-legacy-judge` reaching `judge.judge`.

    All 13 of that judge's criteria are written about a game, and handed a scene it
    answers every one of them: `GAME_BRIEF.get(game, "(unknown game)")` supplies a brief
    rather than refusing. Its own CLI refuses a scene by `choices=sorted(GAME_BRIEF)`,
    and `evaluate()` bypasses the CLI entirely - which is rule 13, guard the resource on
    the path that actually holds it.
    """
    refusal = aspects.applicability("legacy_judge", task)
    if refusal is not None:
        raise ValueError(f"--with-legacy-judge is not available here: {refusal}")


def resolve_instrument(task: str) -> tuple[str, str]:
    """`(task class, tier-2 instrument id)` for one task, or raise.

    THE FIRST OF THE THREE PATHS the runner reaches a grading instrument or a judge pack
    by, and the one that covers the pack: `anonymise.build_pack` is class-agnostic - it
    copies a submission's own files - so what has to be established before it runs is that
    the task has a class at all. `aspects.task_class` is three-valued and an id it cannot
    place comes back `UNKNOWN_TASK`; grading it would stamp a pack, a score and a stored
    record with a task nothing in `eval/suites/` defines.
    """
    klass = aspects.task_class(task)
    if klass == aspects.UNKNOWN_TASK:
        raise ValueError(
            f"{task!r} is in neither eval/suites/wholegame_prompts.py nor "
            f"eval/suites/scene_prompts.py and is not shaped like a task id, so its "
            f"task class cannot be established. Refusing to grade it: every tier, the "
            f"judge pack and the stored record would name a task nothing defines.")
    instrument = TIER2_INSTRUMENT.get(task)
    if instrument is None:
        raise ValueError(
            f"{task!r} has no tier-2 instrument in evaluate.TIER2_INSTRUMENT. A task "
            f"the harness can launch and cannot grade is worse than one it refuses to "
            f"launch: the trial is paid for by then.")
    refusal = aspects.applicability(instrument, task)
    if refusal is not None:
        raise ValueError(f"TIER2_INSTRUMENT disagrees with aspects.INSTRUMENTS about "
                         f"{task!r}: {refusal}")
    return klass, instrument


#: Engine caches that are REGENERATED by the very commands the grader runs. They are
#: excluded when a work tree is created (`wholegame.py: IGNORE`) but grading happens in
#: the tree the AGENT LEFT BEHIND, which by then holds whatever state the agent's own
#: commands produced.
#:
#: MEASURED 2026-08-16: `g1_pong__unity__t0/t1` scored **0 of 14** because a stale
#: `Library/` left `com.unity.testtools.codecoverage` unable to see
#: `UnityEditor.SettingsManagement`. Six `error CS`, every one inside
#: `Library/PackageCache/`, **none in `Assets/`** - the agent's own code was clean. Drop
#: the cache and the identical submission compiles: "all assemblies compile clean".
#:
#: The trigger was the agent adding `com.unity.modules.audio` to `Packages/manifest.json`
#: - exactly what the audio task requires. **The defect did not exist before the task
#: changed, and it fires only in trees where the agent did what it was told.** A grader
#: that penalises compliance is worse than one that penalises nothing.
STALE_CACHES = ("Library", "Temp", "obj", ".godot")


def drop_stale_caches(submission: Path) -> list[str]:
    """Remove regenerable engine caches before grading. Returns what was dropped."""
    dropped = []
    for name in STALE_CACHES:
        d = submission / name
        if d.is_dir():
            shutil.rmtree(d, ignore_errors=True)
            dropped.append(name)
    return dropped


def evaluate(submission: Path, starter: Path, game: str, out: Path,
             seed: int = 7, env: dict[str, str] | None = None,
             run_judge: bool = False, judge_model: str = "sonnet",
             run_coverage: bool = False, audio: bool = True) -> dict[str, Any]:
    """`audio` opts in the six audio criteria (five in tier 1, one in tier 2).

    `run_judge` DEFAULTS OFF, and the default was flipped deliberately. It runs the
    RETIRED 13-criterion generalist judge in `judge.py`, which across 24 submissions
    fired on 2 criteria, and both of those firings were later adjudicated as a
    frame-capture artifact rather than a property of the games (FINDINGS #26). It costs
    a measured $1.75 per submission - about $42 over a 24-trial matrix - to produce a
    tier that carries no information and is weighted 0.00.

    The subjective layer is now `field.py` / `field_sweep.py`: one specialist per aspect,
    each ranking a whole eight-submission field, run separately and under a cost ceiling
    after the deterministic tiers are in. Pass `run_judge=True` only to reproduce the old
    tier deliberately.

    It is True for runs whose task asked for sound. Set it False when re-scoring a
    submission built before audio entered the task set - otherwise the score measures
    the task change rather than the work.
    """
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.monotonic()
    task_class, tier2_instrument = resolve_instrument(game)
    if run_judge:
        assert_legacy_judge_allowed(game)
    rec: dict[str, Any] = {
        "submission": str(submission),
        "starter": str(starter),
        "game": game,
        # WHAT KIND OF TASK THIS WAS, stamped rather than inferrable. A scene score is
        # never pooled with a game score (`eval/SCENES.md`), and a reader that has to
        # re-derive the class from the id prefix is one regex away from pooling them.
        "task_class": task_class,
        "tier2_instrument": tier2_instrument,
        "seed": seed,
        "started_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "weights": WEIGHTS,
    }

    # DROP STALE ENGINE CACHES BEFORE ANY COMMAND RUNS, not after.
    #
    # This call sat AFTER `static.collect` and `probe.drive` on its first outing, which
    # is to say after every command whose result it was supposed to fix. It ran, it
    # recorded `stale_caches_dropped: ["Library"]` in all 24 records, and it changed
    # nothing: the four Unity cells scored exactly what they had before. A repair
    # applied after the measurement is indistinguishable in the record from one that
    # did not work - both leave a truthful log line and an unchanged score.
    rec["stale_caches_dropped"] = drop_stale_caches(submission)

    # -- tier 1 ----------------------------------------------------------- #
    #
    # TWO THINGS ARE TASK-CLASS DEPENDENT HERE, and both would otherwise measure the
    # task rather than the work.
    #
    # 1. THE SCENE HAS NO SOUND. Every rendered scene prompt says so in as many words
    #    ("Do not spend effort on audio; spend it on what is on screen"), so scoring a
    #    scene against the five tier-1 audio criteria deducts for compliance - the same
    #    shape as `STALE_CACHES` above, where the grader penalised the agent for doing
    #    what the task asked. `audio.collect` is keyed by game and would raise on a
    #    scene id in any case, which is a refusal by accident rather than by design.
    # 2. THE TICK COUNT IS THE SCENE'S OWN. `film_ticks` defaults to 900 because that is
    #    a reasonable length for a game; a scene is a fixed-length sequence and its
    #    length is contracted (`eval/SCENES.md`: 660 ticks, 12 frames at
    #    floor(i*660/11)). These frames are also what the `fidelity` and `motion`
    #    aspects read, and their brief says the last frame is late in the run - filming
    #    240 ticks past the end makes that sentence false.
    #
    # `task_class` IS STILL HANDED TO `static.collect`, and no tier-1 BOUND reads it any
    # more: `render.nonempty` was the third item here until `tasks/168` removed its ink
    # ceiling, and `static.TIER1_BOUND_POPULATION` now records 0 class-dependent bounds.
    # `static.assert_task_class` refuses an unplaceable class at the door, which is the
    # only place it can be caught once nothing downstream would read differently.
    #
    # NEITHER IS A CLOCK. Both are read off the task's own contract, so the capture path
    # this touches stays deterministic and wall-clock free.
    frames_dir = out / "frames"
    tier1_kwargs: dict[str, Any] = {}
    if task_class == "scene":
        import scene_probe

        tier1_kwargs["film_ticks"] = scene_probe.SCENES[game].ticks
        rec["scene_ticks"] = tier1_kwargs["film_ticks"]
    tier1 = static.collect(submission, seed=seed, env=env,
                           run_coverage=run_coverage, frames_out=frames_dir,
                           audio_game=game if (audio and task_class == "game") else None,
                           task_class=task_class,
                           **tier1_kwargs)
    rec["programmatic"] = tier1
    _atomic(out / "programmatic.json", tier1)

    # -- tier 2 ----------------------------------------------------------- #
    #
    # THE SECOND OF THE THREE RUNNER PATHS. `resolve_instrument` has already asked
    # `aspects.applicability` whether this instrument may be run against this task; the
    # dispatch below is the only place the answer is acted on.
    #
    # THE TIER SLOT KEEPS THE NAME `playbot` AND SO DOES THE FILE, deliberately. It is
    # the WEIGHTED tier-2 slot, and it is spelled that way in `WEIGHTS`, in the
    # completeness gate below, in `regrade_wholegame.py`, in `paired_verdicts.py`, in
    # `tier2_census.py` and in every stored grading. Renaming it to suit the second task
    # class would rewrite what every one of those reads while changing nothing about the
    # measurement. WHICH INSTRUMENT PRODUCED IT is inside the record - `tier: "playbot"`
    # or `tier: "scene_probe"`, written by the instrument itself - and beside it as
    # `tier2_instrument`. A reader partitions on those; nothing has to parse an id.
    if tier2_instrument == "scene_probe":
        import scene_probe

        tier2 = scene_probe.drive(scene_probe.SCENES[game](), submission,
                                  seed_a=seed, seed_b=seed + SCENE_SEED_OFFSET, env=env)
    else:
        mod = importlib.import_module(BOTS[game])
        tier2 = probe.drive(mod.BOT, submission, seed=seed, env=env,
                            audio_game=game if audio else None)
    rec["playbot"] = tier2
    _atomic(out / "playbot.json", tier2)

    # -- the anonymised source pack ----------------------------------------- #
    # ALWAYS built, whether or not the legacy judge runs.
    #
    # It used to be a side effect of that judge (`keep_pack=`), so turning the judge off
    # by default silently removed the evidence the `idiomatic` and `architecture`
    # specialists read - and `field.build_pack` would then have reported "expected 8
    # submissions, found 0" for every code aspect. A second-order breakage of a cost
    # change, in a different file, found by asking what else consumed the artifact.
    # Building it here costs nothing: it is local file copying, no model call.
    try:
        import anonymise
        pack_manifest = anonymise.build_pack(
            submission, starter, out / "judge_pack",
            frames_dir if frames_dir.exists() else None,
            submission_id=f"{game}-{submission.name}")
        rec["pack"] = {"built": True, "at": str(out / "judge_pack"),
                       **{k: v for k, v in pack_manifest.items() if k != "files"}}
    # noqa BLE001, deliberately blind: `build_pack` walks a submission the harness did
    # not write and raises on its own guards (an empty pack, a leaked mapping) as well as
    # on IO, so the set of exception types is open by construction. The failure is
    # RECORDED, not swallowed -- `pack.built` is False with the type name, and the
    # deterministic tiers, which are what most results rest on, still get written.
    except Exception as e:  # noqa: BLE001
        rec["pack"] = {"built": False, "error": f"{type(e).__name__}: {e}"}

    # -- tier 3 ----------------------------------------------------------- #
    #
    # THE THIRD RUNNER PATH, guarded at the top of this function rather than here - a
    # refusal that arrives after tiers 1 and 2 have run has already spent the thing it
    # was protecting.
    if run_judge:
        import judge as judge_mod
        tier3 = judge_mod.judge(
            submission, starter, game,
            frames_dir=frames_dir if frames_dir.exists() else None,
            model=judge_model,
            submission_id=f"{game}-{submission.name}",
            keep_pack=out / "judge_pack",
        )
    else:
        tier3 = {"tier": "judge", "skipped": True, "usable": False, "passed": 0,
                 "total": len(__import__("judge").ALL_CRITERIA), "score": 0.0,
                 "criteria": [], "instability": None, "cost_usd": 0.0}
    rec["judge"] = tier3
    _atomic(out / "judge.json", tier3)

    # -- combine ----------------------------------------------------------- #
    # `tier_scores` keeps BOTH deterministic tiers even though only one is weighted.
    # Tier 1's fraction is still the thing `weight_sensitivity.py` sweeps and the thing
    # a future headroom criterion would move, and a number that stops being written is
    # a question that stops being answerable.
    scores = {k: float((rec.get(k) or {}).get("score", 0.0))
              for k in (GATE_TIER, *WEIGHTS)}
    rec["tier_scores"] = scores
    rec["gate"] = gate_verdict(tier1)
    rec["scoring_regime"] = SCORING_REGIME
    rec["diagnostic_scores"] = {k: float(rec[k].get("score", 0.0))
                                for k in DIAGNOSTIC_TIERS if k in rec}
    rec["judge_is_diagnostic_only"] = True
    # `judge_usable` is RECORDED, not acted on. The judge tier is in DIAGNOSTIC_TIERS
    # and not in WEIGHTS, so `overall` sums WEIGHTS only: a judge tier that could not
    # run cannot affect the score, and there is nothing to renormalise. The flag is
    # how a reader of the record tells a tier that measured something from one that
    # did not - False on a skip and on a refusal alike, and `scene_runner_control.py`
    # reads the refused case as False. History: while the tier carried weight, an
    # empty judging pack was folded in as a zero and scored a confident 0.08 during
    # validation, which is what made "refuse to score" the rule; the gate regime then
    # removed the last weights the exclusion had anything to renormalise.
    rec["judge_usable"] = bool(tier3.get("usable")) and not tier3.get("skipped")

    # A PLAY-BOT TIER THAT MEASURED NOTHING IS NOT A SCORE OF ZERO.
    #
    # `drive()` returns usable=False only when EVERY criterion came back unscored -
    # which happens when the engine refused every session, not when the game is bad.
    # Folding that in as 0.0 deducts the WHOLE grade - it was two thirds of it before
    # tier 1 became a gate - from
    # a submission that was never driven, and it can only happen on the stacks that take
    # a project-wide lock. That is bias, not noise (FINDINGS #25).
    #
    # It is NOT fixed by renormalising the way the judge tier is. Tier 2 is deliberately
    # fail-closed (RUBRIC.md): a game that cannot be driven has not demonstrated
    # gameplay, and renormalising would let an undriveable submission inherit tier 1's
    # score - a far worse failure, and the one this tier exists to prevent. So the score
    # stays fail-closed and the CONDITION is made loud instead: `cmd_report` excludes
    # these from every aggregate and prints them for adjudication, exactly as it does
    # for a trial with a missing tier.
    rec["playbot_usable"] = bool(tier2.get("usable", True))
    rec["playbot_unscored"] = tier2.get("unscored") or {}
    # Neither the judge nor the gate is in WEIGHTS, so `overall` is the play-bot tier
    # alone. A judge tier that failed to run cannot affect the score - which is the
    # point - and neither can a lint finding, which is the change of 2026-08-23.
    #
    # A GATE FAILURE DOES NOT DEDUCT AND DOES NOT EXCLUDE. It is reported beside the
    # score with the failing criterion ids. Deducting would restore the thing being
    # removed; excluding would be a reason not to count a failure, and every one of
    # those is a channel a bug can widen (rule 7).
    rec["overall"] = overall_score(scores)
    rec["wall_s"] = round(time.monotonic() - t0, 1)
    rec["finished_at"] = dt.datetime.now(dt.timezone.utc).isoformat()

    # HARD COMPLETENESS GATE. A trial that produced two tiers must never be reported
    # as if it produced three. The tier-3 subprocess died mid-run during calibration,
    # leaving programmatic.json and playbot.json on disk and no judge.json - and
    # nothing downstream noticed. Two tiers silently averaged as three is precisely
    # the "reported confidently, measured nothing" failure this project keeps hitting,
    # so the record is only stamped complete when every tier file is present and
    # parseable.
    missing = []
    for tier, fname in (("programmatic", "programmatic.json"),
                        ("playbot", "playbot.json"), ("judge", "judge.json")):
        p = out / fname
        if not p.exists() or p.stat().st_size == 0:
            missing.append(fname)
            continue
        try:
            json.loads(p.read_text())
        except json.JSONDecodeError:
            missing.append(f"{fname} (unparseable)")
    rec["tiers_complete"] = not missing
    if missing:
        rec["missing_tiers"] = missing
    _atomic(out / "report.json", rec)
    if missing:
        raise RuntimeError(
            f"INCOMPLETE EVALUATION for {submission.name}: missing {missing}. "
            f"The partial record is at {out / 'report.json'} and is marked "
            f"tiers_complete=false. Re-run the evaluation; do not aggregate it.")
    return rec


def gate_line(gate: dict[str, Any] | None) -> str:
    """One line, and it must never be silent about a gate that did not run."""
    if not gate:
        return "GATE   (absent - this record predates the gate regime)"
    if not gate.get("usable"):
        return "GATE   UNUSABLE: tier 1 scored no criteria. This is not a pass."
    if gate.get("passed"):
        return f"GATE   PASS   ({gate['n_scored']}/{gate['n_scored']} tier-1 criteria)"
    ids = ", ".join(gate.get("failed") or [])
    note = ("  *** BLOCKING: tier 2 could not observe this submission, so `overall` "
            "is not independent evidence ***" if gate.get("blocking_failed") else "")
    return (f"GATE   FAIL   {gate['n_failed']} of {gate['n_scored']} tier-1 criteria: "
            f"{ids}{note}")


def summarise(rec: dict[str, Any]) -> str:
    lines = [
        f"=== {rec['game']}  {Path(rec['submission']).name} ===",
        f"overall {rec['overall']:.3f}   = playbot   ({rec['wall_s']}s)",
        gate_line(rec.get("gate")),
        "tier 1 is a GATE and tier 3 is DIAGNOSTIC; neither contributes to `overall`",
        "",
    ]
    # No NOTE about the judge tier here. One used to hang off `judge_usable` claiming
    # the tier was "excluded from `overall`" with "the remaining weights renormalised"
    # - false under the gate regime on both counts, since the judge carries no weight
    # and nothing is renormalised (task 223). What the reader needs is already here,
    # truthfully: the line above, and the `judge  SKIPPED` / `judge  UNUSABLE: ...`
    # row below saying whether the tier ran.
    for tier in ("programmatic", "playbot", "judge"):
        t = rec.get(tier) or {}
        diag = tier in DIAGNOSTIC_TIERS
        if t.get("skipped"):
            lines.append(f"{tier:<14} SKIPPED")
            continue
        if t.get("usable") is False:
            lines.append(f"{tier:<14} UNUSABLE: {t.get('error')}")
            continue
        extra = ""
        if tier == "judge" and t.get("instability") is not None:
            extra = f"  instability={t['instability']}"
        label = ("DIAGNOSTIC - not scored" if diag
                 else "GATE - not scored" if tier == GATE_TIER
                 else f"weight={WEIGHTS[tier]}")
        lines.append(f"{tier:<14} {t.get('passed', 0)}/{t.get('total', 0)}"
                     f"  score={t.get('score', 0.0):.2f}"
                     f"  [{label}]{extra}")
        for c in t.get("criteria", []):
            mark = "PASS" if c["passed"] else "FAIL"
            lines.append(f"    [{mark}] {c['id']:<26} {c.get('evidence', '')[:110]}")
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--submission", required=True, type=Path)
    ap.add_argument("--starter", required=True, type=Path)
    ap.add_argument("--game", required=True, choices=sorted(TIER2_INSTRUMENT),
                    help="a game or a scene id. Scenes are graded by scene_probe.py "
                         "rather than by a play-bot; see eval/SCENES.md.")
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--with-legacy-judge", action="store_true",
                    help="run the RETIRED 13-criterion generalist judge (~$1.75 per "
                         "submission, weight 0.00, measured to carry no information). "
                         "The current subjective layer is judge/field_sweep.py.")
    ap.add_argument("--no-judge", action="store_true",
                    help="deterministic tiers only - useful while iterating, since "
                         "tier 3 is the only tier that costs money")
    ap.add_argument("--judge-model", default="sonnet")
    ap.add_argument("--coverage", action="store_true")
    ap.add_argument("--no-audio", action="store_true",
                    help="score without the audio criteria - for submissions built "
                         "before audio entered the task set")
    a = ap.parse_args()
    rec = evaluate(a.submission.resolve(), a.starter.resolve(), a.game,
                   a.out.resolve(), seed=a.seed,
                   run_judge=a.with_legacy_judge and not a.no_judge,
                   judge_model=a.judge_model, run_coverage=a.coverage,
                   audio=not a.no_audio)
    print(summarise(rec))
    print(f"artifacts: {a.out.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
