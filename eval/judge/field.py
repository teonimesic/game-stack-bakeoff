"""Field judging: one specialist, one game, all eight submissions at once.

Build a pack whose top level is eight anonymous submission directories, hand it
to a judge that must rank them against one another, and record the mapping
separately so the analyst reading the ranking cannot see the stacks.

Usage:
    python3 judge/field.py pack   --run RUN --game g1_pong --out DIR [--order-seed N]
    python3 judge/field.py run    --pack DIR --aspect idiomatic --out results.json
    python3 judge/field.py gates  --results a.json b.json
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import os
import random
import shutil
import statistics
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from anonymise import neutralise  # noqa: E402
from aspects import ASPECTS, Aspect  # noqa: E402

LABELS = "ABCDEFGH"
DEFAULT_MODEL = "sonnet"


# ----------------------------------------------------------------------------
# Pack building
# ----------------------------------------------------------------------------

def _submissions(run: Path, game: str, sees: str = "code") -> list[Path]:
    """Submissions that carry the evidence this aspect needs.

    An aspect that reads frames must not be handed a submission whose only artifact
    is a source pack: it would score a blank field confidently. Requiring the
    evidence up front is why `judge_pack/code` was checked here in the first place.
    """
    need = set(sees.split("+"))
    def has(p: Path) -> bool:
        e = p / "eval"
        if "code" in need and not (e / "judge_pack" / "code").is_dir():
            return False
        if "frames" in need and not any(e.glob("frames/*.png")):
            return False
        if "telemetry" in need and not (e / "playbot.json").is_file():
            return False
        if "audio" in need and _audio_evidence(p) is None:
            return False
        return True
    return sorted(p for p in (run / "artifacts").glob(f"{game}__*") if has(p))


def _audio_evidence(sub: Path) -> dict[str, Any] | None:
    """Measured properties of every clip, with paths reduced to bare names.

    A path leaks the stack -- `assets/audio/hit.wav` and `Assets/Audio/hit.wav` are a
    giveaway -- and the judge is told not to guess which stack it is looking at. So it
    gets what it can reason about (duration, level, grouping) and nothing that would
    let it identify the arm.
    """
    try:
        prog = json.loads((sub / "eval" / "programmatic.json").read_text())
    except (OSError, json.JSONDecodeError):
        return None
    info = prog.get("audio") or {}
    if not info.get("applies"):
        return None
    clips = {k: {"seconds": v.get("seconds"), "rms": v.get("rms"),
                 "peak": v.get("peak")}
             for k, v in (info.get("clips") or {}).items()}
    # NO CLIPS IS NOT AUDIO EVIDENCE. The empty-pack guard below counts the file that
    # gets written, not what is in it, so a submission that ships no sound at all - the
    # two `g3_arena` rust trials, which do not compile - produced `{"clips": {}}` and
    # sailed through a check whose whole purpose is to stop a judge scoring a blank
    # field. Measured 2026-08-16 while validating the packs before spending anything on
    # them, which is the only reason it was seen.
    if not clips:
        return None
    return {
        "clips": clips,
        "distinct_sound_groups": [[Path(n).name for n in g]
                                  for g in info.get("distinct_sound_groups") or []],
        "declared_events": info.get("expected_events"),
        "events_with_no_cue": info.get("missing_events"),
        "deterministic_verdicts": {c["id"]: c["passed"]
                                   for c in info.get("criteria") or []},
    }


def _telemetry_evidence(sub: Path) -> dict[str, Any] | None:
    try:
        pb = json.loads((sub / "eval" / "playbot.json").read_text())
    except (OSError, json.JSONDecodeError):
        return None
    tele = pb.get("telemetry")
    if not isinstance(tele, dict) or not tele.get("usable"):
        return None
    out = {"ticks_driven": pb.get("ticks_driven"),
           "events_fired": pb.get("events_fired"), **tele}
    # SAY WHEN THE PACING NUMBER CARRIES NOTHING.
    #
    # `longest_quiet_stretch_seconds` is meant to answer "does this game go dead?". It is
    # computed over the play-bot's own driven session, and that session exists to satisfy
    # criteria, not to be a representative play. Measured 2026-08-16 on the eight
    # `g2_tetris3d` submissions: 6-9 events over 6-9 seconds, so the longest gap between
    # events is 0.93-1.00 of the WHOLE RUN in every single one. The metric is degenerate
    # by construction - it is run length wearing a pacing label - and the `fun` judge's
    # scores correlate -0.45 to -0.60 with run length across two presentation orders.
    #
    # Reporting the ratio does not fix the evidence. It stops the number being read as
    # pacing when it cannot be, which is the difference between a weak signal and an
    # artifact presented as a measurement (FINDINGS #26, #52).
    secs = tele.get("seconds_of_play") or 0.0
    quiet = tele.get("longest_quiet_stretch_seconds")
    if secs and quiet is not None:
        frac = round(quiet / secs, 3)
        out["quiet_fraction_of_run"] = frac
        if frac >= 0.9:
            out["pacing_evidence_warning"] = (
                f"the longest quiet stretch is {frac:.0%} of the entire driven run, so "
                f"this run contains no pacing information: the bot produced "
                f"{sum((tele.get('event_counts') or {}).values())} events in "
                f"{secs:.1f}s. Do not read quiet-stretch or events-per-second as a "
                f"property of the game.")
    return out


def mapping_path(pack: Path) -> Path:
    """Where the label -> submission mapping lives: BESIDE the pack, never in it."""
    return pack.parent / f"{pack.name}.MAPPING.json"


#: A neutral extension for packs whose aspect must not be told the language.
NEUTRAL_EXT = ".src"


def pack_completeness(run: Path, game: str) -> dict[str, Any]:
    """How much of each submission the judge will actually be shown.

    ITS JOB CHANGED ON 2026-08-22, and the code did not.

    Originally it detected a defect: `anonymise.py` filled a code pack until `max_chars`
    ran out, dropping files by where their path sorted. `files_dropped_for_length` sat in
    every manifest since the first matrix and nothing read it - 60 submissions carried it,
    32 dropped at least one file, and the deficit was stack-correlated (#62).

    **The budget is now gone**, so drops are 0 by construction and this gate can no longer
    fire on any field built today. That is exactly the shape of #57 - a check that cannot
    fail - so it was deliberately repurposed rather than deleted: it now asserts the
    invariant `files_dropped_for_length == 0` and refuses loudly if a future budget
    silently reintroduces truncation. A gate that detected a defect became one that
    detects the defect's RETURN.

    Deleting it was the alternative and was rejected in `eval/IMPROVEMENTS.md`: deletion
    removes the only thing that would notice a cap coming back, and a cap coming back is
    precisely how this defect arrived the first time - as a reasonable-looking guard on
    prompt size.

    **#62's finding stays valid.** It describes what was true of every round already run,
    and every stored code judgement was made on a truncated sample.
    """
    import json as _j
    out: dict[str, int] = {}
    for d in sorted((run / "artifacts").glob(f"{game}__*")):
        rep = d / "eval" / "report.json"
        if not rep.is_file():
            continue

        def _find(o):
            if isinstance(o, dict):
                for k, v in o.items():
                    if k == "files_dropped_for_length":
                        return v
                    r = _find(v)
                    if r is not None:
                        return r
            return None

        n = _find(_j.loads(rep.read_text()))
        if n is not None:
            out[d.name] = int(n)
    vals = list(out.values())
    return {
        "per_submission": out,
        "any_dropped": sum(1 for v in vals if v > 0),
        "max_dropped": max(vals) if vals else 0,
        "spread": (max(vals) - min(vals)) if vals else 0,
        "complete": bool(vals) and all(v == 0 for v in vals),
    }


def pack_matches_manifest(run: Path, game: str) -> dict[str, Any]:
    """Does each stored judge pack hold exactly the files its own manifest lists?

    THIS READS THE PACK. `pack_completeness` reads `files_dropped_for_length` - a number
    `anonymise.build_pack` computed about its INPUT - and that number is 0 by construction
    since #69. A gate that reads its input instead of its output cannot see a file that
    arrived from somewhere else, which is why 23 stale files in `wg-g4c` survived nine
    evaluations and every gate the project owns.

    The mechanism: `build_pack` used to `mkdir(exist_ok=True)` and never clear, and labels
    are `bucket/NN.ext` counted within the bucket. Change the picked SET between two passes
    - a starter edit, a new exclusion, an extension added to `CODE_EXT` - and the numbering
    shifts, so the earlier pass's files stay under labels the new manifest does not list.
    The judge then reads code no manifest accounts for, twelve of the 23 being a second
    copy of a live file under a second name.

    Three verdicts, and the middle one must not be collapsed into either neighbour:

    | state | meaning |
    |---|---|
    | `clean` | disk set == manifest set for every submission, frames included |
    | `unmeasurable` | a pack exists but its report has no manifest - 25 stored submissions predate it. NOT clean |
    | stale/missing | named per submission and counted per stack, because the deficit was stack-correlated both times (#62 and this one) |
    """
    import json as _j
    per: dict[str, dict[str, Any]] = {}
    unmeasurable: list[str] = []
    for d in sorted((run / "artifacts").glob(f"{game}__*")):
        code = d / "eval" / "judge_pack" / "code"
        if not code.is_dir():
            continue
        rep = d / "eval" / "report.json"
        pack = {}
        if rep.is_file():
            try:
                pack = _j.loads(rep.read_text()).get("pack") or {}
            except (OSError, _j.JSONDecodeError):
                pack = {}
        manifest = pack.get("manifest")
        if manifest is None:
            unmeasurable.append(d.name)
            continue
        listed = {e["label"] for e in manifest}
        disk = {str(p.relative_to(code)) for p in code.rglob("*") if p.is_file()}
        fdir = d / "eval" / "judge_pack" / "frames"
        frames_disk = sum(1 for p in fdir.glob("*.png")) if fdir.is_dir() else 0
        per[d.name] = {
            "stack": d.name.split("__")[1] if "__" in d.name else "?",
            "files_on_disk": len(disk),
            "files_in_manifest": len(listed),
            "stale": sorted(disk - listed),
            "missing": sorted(listed - disk),
            "frames_on_disk": frames_disk,
            "frames_in_manifest": pack.get("frames"),
        }
    by_stack: dict[str, int] = {}
    for v in per.values():
        if v["stale"]:
            by_stack[v["stack"]] = by_stack.get(v["stack"], 0) + len(v["stale"])
    stale_total = sum(len(v["stale"]) for v in per.values())
    missing_total = sum(len(v["missing"]) for v in per.values())
    frames_wrong = sorted(k for k, v in per.items()
                          if v["frames_in_manifest"] is not None
                          and v["frames_on_disk"] != v["frames_in_manifest"])
    return {
        "per_submission": per,
        "unmeasurable": unmeasurable,
        "stale_total": stale_total,
        "missing_total": missing_total,
        "stale_by_stack": by_stack,
        "frames_mismatched": frames_wrong,
        "files_on_disk": sum(v["files_on_disk"] for v in per.values()),
        "clean": (bool(per) and not unmeasurable and not stale_total
                  and not missing_total and not frames_wrong),
    }


def pack_parity(run: Path, game: str) -> dict[str, Any]:
    """Capture geometry across the submissions a frames-reading aspect will be shown.

    `tools/frame_parity.py` has been able to answer this since #59, and on 2026-08-21 it
    was run AFTER a $10.20 judge round rather than before it - its own docstring says
    "Run BEFORE reading any frame-derived number". It then reported
    `g2_tetris3d__unity__t1` filmed at 420x640 against the field's 640x400, a
    portrait/landscape flip shown directly to both frames-only aspects.

    A rule that has to be remembered is a rule that will not fire, so it is code now, on
    the path, beside the completeness gate that DID fire for exactly that reason.
    """
    import importlib.util as _ilu
    spec = _ilu.spec_from_file_location(
        "_frame_parity", Path(__file__).resolve().parent.parent / "tools" / "frame_parity.py")
    fp = _ilu.module_from_spec(spec)
    spec.loader.exec_module(fp)

    geo = {k: v for k, v in fp.geometry(run).items() if k.startswith(f"{game}__")}
    sizes: dict[str, int] = {}
    for rec in geo.values():
        for s, n in rec["sizes"].items():
            sizes[s] = sizes.get(s, 0) + n
    modal = max(sizes, key=lambda k: sizes[k]) if sizes else ""
    divergent = sorted(k for k, v in geo.items()
                       if list(v["sizes"]) != [modal] or not v["uniform_within_submission"])
    return {"per_submission": geo, "modal_size": modal,
            "divergent": divergent, "uniform": bool(geo) and not divergent}


def build_pack(run: Path, game: str, dest: Path, order_seed: int,
               sees: str = "code", blind_language: bool = False,
               allow_truncated: bool = False) -> dict[str, Any]:
    subs = _submissions(run, game, sees)
    if len(subs) != 8:
        raise RuntimeError(f"{game}: expected 8 submissions, found {len(subs)}")

    knowingly_truncated = False

    # GEOMETRY, for aspects that read frames. It INFORMS; it does not refuse.
    #
    # This gate used to reject a field whose submissions filmed at different sizes. That
    # was wrong, and the reason matters: only godot's `film` recipe passes `--resolution`,
    # so the other three capture at whatever their own render target defaults to - which
    # means the geometry is a DESIGN CHOICE THE TASK LEFT OPEN. `g2_tetris3d__unity__t1`
    # in `wg-matrix-2026-08-13` filmed at 420x640: a portrait well for a falling-block
    # game, which is a perfectly sensible thing to build. Refusing it treated variation as
    # corruption, and forcing every submission to 640x400 would have erased a real
    # difference between submissions and called it normalisation - the harness overwriting
    # the thing it exists to measure.
    #
    # So the geometry is measured, recorded, and passed to the judge in its brief.
    #
    # WHY ANNOTATION IS RIGHT HERE AND WAS WRONG IN #62, since these look identical and
    # are not: #62's caveat was `files_dropped_for_length`, a JSON field that no code read
    # and no human opened - annotation into a void. This annotation goes into BRIEF.md,
    # which is read by an agent whose whole task is to read it. A sentence in a brief a
    # model reads is a different object from a key in a manifest nothing parses. The test
    # is not "annotate vs refuse", it is WHETHER ANYTHING IS ON THE OTHER END.
    geometry: dict[str, str] = {}

    # COMPLETENESS GATE, for aspects that read code. Refuse rather than judge a field
    # whose members were shown different amounts of themselves (#62).
    if "code" in sees.split("+"):
        comp = pack_completeness(run, game)
        # NOT MEASURED is a third state, and it must not print as a measurement. With no
        # eval/report.json on disk the counts are all zero and the refusal reads "0 of 0
        # submissions dropped files" - a reading of an empty set dressed as a reading of
        # the field. It fails closed, so it costs a round rather than corrupting one, but
        # the operator would be debugging the wrong sentence.
        if not comp["per_submission"]:
            raise RuntimeError(
                f"{game}: pack completeness is UNMEASURED, not clean - no "
                f"eval/report.json under runs/*/artifacts/{game}__*. Grade the "
                f"programmatic tier first; the drop counts are written there. This is "
                f"not a #62 refusal.")
        if not comp["complete"] and allow_truncated:
            # A DELIBERATE control, not an accident. The gate exists to stop a truncated
            # field being judged unnoticed; the capped-vs-uncapped experiment (task 09)
            # has to judge one on purpose. So the escape is explicit, must be passed by
            # name, and STAMPS the pack - a downstream reader cannot mistake this field
            # for a complete one, which is the property the gate was really protecting.
            knowingly_truncated = True
        elif not comp["complete"]:
            raise RuntimeError(
                f"{game}: TRUNCATION HAS RETURNED - {comp['any_dropped']} of "
                f"{len(comp['per_submission'])} submissions dropped files for length "
                f"(max {comp['max_dropped']}, spread {comp['spread']}). The character "
                f"budget was REMOVED on 2026-08-22 (#69), so this must be 0 for every "
                f"submission; a non-zero count means a cap has been reintroduced "
                f"somewhere in anonymise.build_pack and the judge is again being shown "
                f"an alphabetically-selected subset of each submission. Do not judge this "
                f"field. Find the cap. See FINDINGS #62 for what it cost last time.")

        # AND THE SAME QUESTION ASKED OF THE OUTPUT. The gate above reads a count
        # `anonymise` wrote about its input; this one reads the directory the judge is
        # about to be handed. They are not redundant - the first is 0 by construction and
        # the second found 23 files it could never have seen.
        #
        # `--allow-truncated` does NOT excuse this. That escape exists for the
        # capped-vs-uncapped control, where the truncation is the experiment; a stale file
        # is not an experimental condition, it is a pack that does not know what is in it.
        parity = pack_matches_manifest(run, game)
        if parity["unmeasurable"]:
            raise RuntimeError(
                f"{game}: pack/manifest parity is UNMEASURABLE for "
                f"{len(parity['unmeasurable'])} submission(s) - "
                f"{', '.join(parity['unmeasurable'])} have a judge pack on disk and no "
                f"`pack.manifest` in eval/report.json, so nothing can say whether what "
                f"the judge would read is what was packed. Re-pack the run (evaluate or "
                f"regrade writes the manifest) rather than judging it. This is not a "
                f"clean field; it is an unmeasured one.")
        if not parity["clean"]:
            raise RuntimeError(
                f"{game}: STALE FILES IN THE JUDGE PACKS - {parity['stale_total']} file(s) "
                f"in {parity['files_on_disk']} on disk are under labels no manifest lists "
                f"(by stack: {parity['stale_by_stack']}), {parity['missing_total']} listed "
                f"file(s) are absent, frames mismatched on {parity['frames_mismatched']}. "
                f"`anonymise.build_pack` wrote each re-evaluation ON TOP of the previous "
                f"one until 2026-08-23, so a run evaluated more than once carries earlier "
                f"passes under shifted labels. Re-pack the run before judging it: the "
                f"amount of itself each submission is shown is otherwise unequal and "
                f"stack-correlated, which is FINDINGS #62's shape through a third "
                f"mechanism.")

    order = list(subs)
    random.Random(order_seed).shuffle(order)

    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)

    need = set(sees.split("+"))
    mapping: dict[str, str] = {}
    counts: dict[str, dict[str, int]] = {}
    for label, sub in zip(LABELS, order):
        mapping[label] = sub.name
        out = dest / label
        out.mkdir()
        n = {"code": 0, "frames": 0, "telemetry": 0, "audio": 0}

        if "code" in need:
            src = sub / "eval" / "judge_pack" / "code"
            for f in sorted(src.rglob("*")):
                if not f.is_file():
                    continue
                tgt = out / f.relative_to(src)
                if blind_language:
                    tgt = tgt.with_suffix(NEUTRAL_EXT)
                tgt.parent.mkdir(parents=True, exist_ok=True)
                try:
                    tgt.write_text(neutralise(f.read_text(errors="ignore")))
                except Exception:
                    continue
                n["code"] += 1
            stat = sub / "diff.stat"
            if stat.is_file():
                (out / "CHANGED.txt").write_text(
                    "Files this submission's author changed, and by how much.\n"
                    "Everything else is template code they inherited.\n\n"
                    + neutralise(stat.read_text(errors="ignore")))

        if "frames" in need:
            fdir = out / "frames"
            fdir.mkdir(exist_ok=True)
            for f in sorted((sub / "eval" / "frames").glob("*.png")):
                shutil.copy(f, fdir / f.name)
                n["frames"] += 1
            # Geometry per LABEL, not per submission id: the brief is blind, so the judge
            # is told "C is 420x640", never which stack C is. This leaks nothing it does
            # not already have - the size is visible in the PNGs it is about to open.
            try:
                import png as _png
                _f0 = sorted(fdir.glob("*.png"))
                if _f0:
                    _im = _png.read(_f0[0])
                    geometry[label] = f"{_im.width}x{_im.height}"
            except Exception:
                pass

        if "telemetry" in need:
            tele = _telemetry_evidence(sub)
            if tele is not None:
                (out / "telemetry.json").write_text(json.dumps(tele, indent=2))
                n["telemetry"] = 1

        if "audio" in need:
            aud = _audio_evidence(sub)
            if aud is not None:
                (out / "audio.json").write_text(json.dumps(aud, indent=2))
                n["audio"] = 1

        # An empty pack must never reach a judge. MEASURED: one scored an empty
        # file pack at 0.08, confidently. Fail here instead.
        for kind in need:
            if n.get(kind, 0) == 0:
                raise RuntimeError(
                    f"{sub.name}: pack has no {kind} evidence, and the {sees!r} "
                    f"aspect needs it. Refusing to build a pack a judge would score "
                    f"blind.")
        counts[label] = n

    # THE MAPPING MUST NOT BE INSIDE THE PACK.
    # The judge runs with the pack as its working directory and is told it is not shown
    # which stack is which. A file in that directory naming `A -> g1_pong__godot__t0`
    # for all eight hands it the entire answer, and every "blind" ranking produced
    # afterwards would be worthless - the same failure as the rubric being reachable
    # from a trial tree, which is why `verify_blind.py` walks ancestors at all.
    # Found by listing the pack instead of trusting the code that wrote it.
    mapping_path(dest).write_text(json.dumps(
        {"game": game, "run": run.name, "order_seed": order_seed, "sees": sees,
         "mapping": mapping, "evidence_counts": counts,
         "capture_geometry": geometry,
         "knowingly_truncated": knowingly_truncated}, indent=2))
    # The skill goes INSIDE the pack: the judge runs `cwd=pack` with
    # `--setting-sources project`, so project settings resolve against the pack and a
    # skill in this repository is invisible to it. Written by the CONSTRUCTOR rather than
    # beside the aspect brief, so it is aspect-agnostic and every built pack carries it -
    # which is also what lets `verify_blind.check_pack_skill` inspect a pack without a
    # judge ever being run.
    skill = dest / ".claude" / "skills" / "sampling-code" / "SKILL.md"
    skill.parent.mkdir(parents=True, exist_ok=True)
    skill.write_text(PACK_SKILL)

    leaked = sorted(q.name for q in dest.rglob("*")
                    if q.is_file() and "MAPPING" in q.name)
    if leaked:
        raise RuntimeError(f"identity mapping left inside the pack: {leaked}")
    return {"game": game, "order_seed": order_seed, "sees": sees,
            "mapping": mapping, "evidence_counts": counts,
            "capture_geometry": geometry,
            "knowingly_truncated": knowingly_truncated}


EVIDENCE_BLURB = {
    "code": ("`CHANGED.txt` names the files this submission's author actually wrote; "
             "everything else is template code they inherited. The source tree is "
             "beside it. NOTE: the pack is filled until a size budget runs out, so it "
             "may not contain every file the author wrote - judge what is here and do "
             "not infer that an absent concern was neglected. **Cite files by the path "
             "they have HERE** -- `sim/03.src`, "
             "`view/02.src` -- and never by a name you infer from their contents. The "
             "filenames have been rewritten; a citation to the original name cannot be "
             "checked by anyone, and unverifiable evidence is discarded. MEASURED: 11 "
             "of 16 claims in one field cited a reconstructed name, and every single "
             "one of them turned out to describe something really in the pack."),
    "frames": ("`frames/` holds PNGs sampled evenly across one real run of this "
               "submission -- the first is the opening state, the last is late in the "
               "run. Everything the player sees is in these pixels; there is no "
               "second display."),
    "telemetry": ("`telemetry.json` is measured from a real driven run of this "
                  "submission: event counts, intervals, how long the run went quiet. "
                  "These are facts about the run, not estimates."),
    "audio": ("`audio.json` describes the sound this submission ships, measured by "
              "decoding every file: duration, RMS, peak, and which clips are the same "
              "sound as each other. You cannot listen to them."),
}


#: A skill written INTO the pack, because the judge runs with `cwd=pack` and
#: `--setting-sources project`, so project settings resolve against the pack directory and
#: a skill in this repository's `.claude/skills/` is invisible to it.
#:
#: Two consequences follow and both constrain what may be written here:
#:   1. it is EVIDENCE the judge sees, so it must not say anything that biases the verdict
#:      - it describes HOW to sample, never what to conclude or which traits are good;
#:   2. it must be BLIND-SAFE. No stack, engine, language or toolchain names. `verify_blind`
#:      scans it for stack tokens and for the rubric canary, and that is pinned.
PACK_SKILL = """---
name: sampling-code
description: How to read a large submission pack without pretending to have read all of it. Use when a submission has more files than are worth opening, or when deciding what to open next.
---

# Sampling a submission

Every submission here is COMPLETE: nothing was removed for size. Some are large. You are
expected to sample, and the only thing that matters is that you sample deliberately and
say what you did.

## Do

1. **Look at the layout first.** `ls` each submission's directory before opening anything.
   The shape of a tree is evidence, and it is cheap.
2. **Read the simulation code before the presentation code.** That is where behaviour
   lives; presentation is easier to judge from the frames if you have them.
3. **Spend your reading unevenly and on purpose.** If two submissions look similar, read
   more of the one you are least sure about, not more of both.
4. **Use subagents for breadth.** The Task tool can open several files in parallel and
   report back. Breadth first, then read the interesting parts yourself.
5. **Say what you sampled** in your evidence: which files you opened, and roughly how much
   of each submission you saw. An honest "I read 6 of 31 files, chosen thus" is worth more
   than an implied complete reading.

## Do not

- Do not assume file count means anything. More files is not better or worse; it is a
  structural choice, and you are not scoring structure unless the brief asks you to.
- Do not treat unread files as absent. If you did not open something, that is a limit on
  your evidence, not a fact about the submission.
- Do not let one submission's sample size decide another's score. Sampling differences are
  yours, not theirs.

## The failure this exists to prevent

A pack used to be truncated to a fixed character budget, so files were dropped by where
their path happened to sort and more than half of some submissions was never shown to any
judge. That is fixed - you now get everything. The risk moved rather than disappearing: it
is now possible to read a biased sample and not notice, because nothing stops you. Choosing
the sample is your job, and reporting it is what makes the judgement auditable.
"""


def _brief(aspect: Aspect, game: str, geometry: dict[str, str] | None = None) -> str:
    anchors = "\n".join(f"  {k} = {v}" for k, v in sorted(aspect.anchors.items()))
    evidence = "\n".join(f"- {EVIDENCE_BLURB[k]}" for k in aspect.sees.split("+")
                         if k in EVIDENCE_BLURB)
    # Do not tell a judge to read code when the pack holds only frames. A stale
    # instruction to open files that are not there burns turns and produces "I could
    # not find the source" as if it were a finding about the submission.
    looked_at = {"code": "Read the code", "frames": "Look at every frame",
                 "telemetry": "Read the telemetry", "audio": "Read the measurements"}
    closing = (" and ".join(looked_at[k] for k in aspect.sees.split("+")
                            if k in looked_at)
               + " before you score. You have the whole field; use it comparatively.")

    # TELL THE JUDGE THE GEOMETRY when it varies, and tell it that varying is allowed.
    # Only one stack's film recipe passes an explicit resolution, so the others capture at
    # whatever their own render target defaults to: the frame size is a presentation choice
    # the task left open, not a defect. A judge shown a portrait strip beside seven
    # landscape ones will notice; unexplained, the obvious readings are "this one is broken"
    # or "this one is cropped", and both are wrong. Naming it costs one sentence and
    # removes a false inference the judge would otherwise have to make unaided.
    geom_note = ""
    if geometry and len(set(geometry.values())) > 1:
        sizes = ", ".join(f"{k} = {v}" for k, v in sorted(geometry.items()))
        geom_note = (
            "\n**These submissions were captured at different frame sizes** "
            f"({sizes}). That is a presentation choice each submission was free to "
            "make -- the task did not specify a window shape -- so it is neither a "
            "defect nor evidence of one. Judge what the frames show, not how large "
            "they are, and do not reward or penalise a submission for its aspect "
            "ratio unless the shape genuinely helps or hurts the thing you are "
            "judging.\n")
    return f"""# {aspect.title}

You are judging **one aspect only**: {aspect.title.lower()}. Ignore every other
dimension. Another specialist is judging those, and double-counting corrupts both.

## The field

Eight submissions, `A/` through `H/`. All eight implement the same game from the
same brief. They were produced by different starting templates across four
different technology stacks, two attempts each -- you are not told which is which,
and you should not guess.

## What is in each directory

{evidence}
{geom_note}
**Judge the authored work, not the template.**

## The question

{aspect.question}

{aspect.notes}

## Scale

{anchors}

Note that 2 is "competent and unremarkable". All eight of these submissions work.
A field where everything is competent should mostly sit at 2, with 3 and 4 earned
by specific evidence and 0 and 1 given where the evidence supports them.

## What you must produce

- A score 0-4 for every one of the eight.
- For each, `evidence`: concrete file paths and constructs, written BEFORE you
  settle on the number. {aspect.evidence_rule}
- A `rank` for every submission, 1 = best. Ties are allowed, but every tie must be
  defended in `tie_reason` -- if you cannot say why two are indistinguishable, they
  are not.
- `best` and `worst` labels, and one sentence each on why.

Do not award the same score to everything. If after reading all eight you truly
cannot separate them on this aspect, say so in `field_note` and explain what you
looked for and did not find -- that is a real finding, not a failure.

{closing}
"""


SCHEMA = {
    "type": "object",
    "required": ["submissions", "best", "worst", "field_note"],
    "properties": {
        "submissions": {
            "type": "array", "minItems": 8, "maxItems": 8,
            "items": {
                "type": "object",
                "required": ["label", "evidence", "score", "rank"],
                "properties": {
                    "label": {"type": "string", "enum": list(LABELS)},
                    "evidence": {"type": "string", "minLength": 60},
                    "score": {"type": "integer", "minimum": 0, "maximum": 4},
                    "rank": {"type": "integer", "minimum": 1, "maximum": 8},
                    "tie_reason": {"type": "string"},
                },
            },
        },
        "best": {"type": "string", "enum": list(LABELS)},
        "best_reason": {"type": "string"},
        "worst": {"type": "string", "enum": list(LABELS)},
        "worst_reason": {"type": "string"},
        "field_note": {"type": "string"},
    },
}


def run_field(pack: Path, aspect_id: str, model: str = DEFAULT_MODEL,
              max_turns: int = 120, budget: float = 12.0,
              timeout_s: int = 3600) -> dict[str, Any]:
    aspect = ASPECTS[aspect_id]
    mapping = json.loads(mapping_path(pack).read_text())
    stray = sorted(q.name for q in pack.rglob("*")
                   if q.is_file() and "MAPPING" in q.name)
    if stray:
        return {"usable": False,
                "error": f"refusing to judge: the identity mapping is inside the pack "
                         f"({stray}), so the judge would not be blind"}
    # A pack built for one aspect does not carry another aspect's evidence. Judging
    # `fun` over a code-only pack would produce eight confident scores derived from
    # nothing that was asked about.
    built_for = mapping.get("sees", "code")
    if built_for != aspect.sees:
        return {"usable": False,
                "error": f"pack was built with sees={built_for!r} but aspect "
                         f"{aspect_id!r} needs sees={aspect.sees!r}"}
    brief_text = _brief(aspect, mapping["game"], mapping.get("capture_geometry"))
    (pack / "BRIEF.md").write_text(brief_text)

    argv = [
        "claude", "-p",
        # Subagents are OFFERED, not assumed. Verified empirically under this exact flag
        # set (`--setting-sources project --strict-mcp-config` etc.) by asking a probe run
        # to spawn one and reading the tool-use stream: `Agent` was actually invoked. An
        # instruction for a capability that is not present is the `-disable-audio` failure
        # in a new costume, so this line is only here because the tool answered.
        #
        # There is no character budget any more (#69): every packable file is present, so
        # some submissions carry 30+ files. Sampling is now the judge's decision, which is
        # the point - it was always making it, just downstream of an alphabetical filter.
        "Read BRIEF.md, then read the code in A/ through H/ and produce the "
        "comparative judgement it asks for. Read real files before scoring. "
        "The submissions are complete, so some are large: you may launch subagents "
        "with the Task tool to read parts of them in parallel and report back. "
        "Sample deliberately and say what you sampled.",
        "--model", model,
        "--output-format", "stream-json", "--verbose",
        "--json-schema", json.dumps(SCHEMA, separators=(",", ":")),
        "--max-turns", str(max_turns),
        "--max-budget-usd", str(budget),
        "--setting-sources", "project",
        "--strict-mcp-config",
        "--exclude-dynamic-system-prompt-sections",
        "--no-session-persistence",
        "--permission-mode", "acceptEdits",
    ]
    # stream-json, so the TOOL CALLS are visible and not only the verdict. Nothing in
    # this project could previously answer "what did the judge actually read?" - the
    # audit trail stopped at the score. With the pack budget gone (#69) a judge chooses
    # its own sample, which makes the question load-bearing rather than curious: an
    # unchanged ordering means one thing if it read 30 files and another if it read 4.
    try:
        p = subprocess.run(argv, cwd=pack, capture_output=True, text=True,
                           timeout=timeout_s)
    except subprocess.TimeoutExpired:
        return {"usable": False, "error": "timeout"}
    except OSError as e:
        return {"usable": False, "error": str(e)}

    events = []
    for line in p.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    if not events:
        return {"usable": False, "error": "unparseable", "raw": p.stdout[-2000:]}

    reads: list[dict[str, Any]] = []
    for ev in events:
        content = (ev.get("message") or {}).get("content")
        if not isinstance(content, list):
            continue
        for b in content:
            if isinstance(b, dict) and b.get("type") == "tool_use":
                inp = b.get("input") or {}
                target = (inp.get("file_path") or inp.get("path") or inp.get("pattern")
                          or inp.get("command") or "")
                reads.append({"tool": b.get("name"), "target": str(target)[:200]})

    results = [d for d in events if isinstance(d, dict) and d.get("type") == "result"]
    data = results[-1] if results else {}
    payload = data.get("structured_output") or data.get("result")
    if isinstance(payload, str):
        try:
            payload = json.loads(payload)
        except json.JSONDecodeError:
            return {"usable": False, "error": "no structured output",
                    "raw": str(payload)[-2000:]}
    if not isinstance(payload, dict) or "submissions" not in payload:
        return {"usable": False, "error": "no submissions array", "raw": str(payload)[:2000]}

    # Attach the true identity only now, after the judgement exists.
    for s in payload["submissions"]:
        s["submission"] = mapping["mapping"].get(s["label"], "?")
        s["stack"] = s["submission"].split("__")[1] if "__" in s["submission"] else "?"
    payload.update({
        # RECORD WHICH RUN THE PACK CAME FROM. Its absence cost a round of confusion on
        # 2026-08-22: `g2_tetris3d` has four stored fields in different states of repair,
        # and a round that names only the GAME cannot say which it judged. #68 was briefly
        # reported as compromised because the wrong field was inspected; it had in fact
        # read `wg-audio48`, re-driven for exactly that reason the day before.
        #
        # This is #70 one level up - an id is not a key - with the id being a GAME and the
        # namespace being the run. `build_pack` already writes `run` into the mapping
        # record; `run_field` simply never carried it into the stored round.
        "usable": True, "aspect": aspect_id, "game": mapping["game"],
        "run": mapping.get("run"),
        # PROVENANCE: what this round actually SAW, so the question "what exactly did it
        # see?" is answerable from the record instead of reconstructed.
        #
        # Two fields were missing before this and both mattered within days. `run` was
        # absent, so a round named only its game - and `g2_tetris3d` is four stored fields
        # in different states of repair. `files_opened` was absent until task 09 added it
        # for an unrelated reason, and it is the only thing that bounded #83.
        #
        # The rescue that found the missing `run` worked by matching numbers quoted in
        # `fun`'s prose against stored telemetry. **That was luck about one aspect's
        # writing style**: `ux` or `idiomatic` quote no telemetry and would have been
        # unresolvable. Prose is not a substitute for a field.
        #
        # So the test applied here is: if someone asks in a month what this round saw,
        # which parts of the answer are gone? Everything below was in that category.
        "provenance": {
            "sees": mapping.get("sees"),
            "blind_language": aspect.blind_language,
            # The BRIEF is not fixed. A geometry note was added to it on 2026-08-22, and
            # rounds either side of that saw different text - which is why task 08 had to
            # re-run seven repeats rather than top up four. Hashing it makes "same brief?"
            # a comparison instead of an argument.
            "brief_sha256": hashlib.sha256(brief_text.encode()).hexdigest()[:16],
            "brief_chars": len(brief_text),
            "evidence_counts": mapping.get("evidence_counts"),
            "capture_geometry": mapping.get("capture_geometry"),
            "knowingly_truncated": mapping.get("knowingly_truncated"),
            "max_turns": max_turns,
            "per_call_budget_usd": budget,
            "judged_at": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
        },
        "order_seed": mapping["order_seed"], "model": model,
        "cost_usd": data.get("total_cost_usd"),
        "mapping": mapping["mapping"],
        "tool_calls": reads,
        "n_tool_calls": len(reads),
        "files_opened": sorted({r["target"] for r in reads
                                if r["tool"] in ("Read", "NotebookRead")}),
        "n_files_opened": len({r["target"] for r in reads
                               if r["tool"] in ("Read", "NotebookRead")}),
        "n_subagents": sum(1 for r in reads if r["tool"] in ("Task", "Agent")),
    })
    return payload


# ----------------------------------------------------------------------------
# Gates
# ----------------------------------------------------------------------------

#: A judge with more than this share of the field on ONE score has not separated it,
#: whichever score that is.
MODAL_CEILING = 0.7


def ceiling(result: dict[str, Any]) -> dict[str, Any]:
    """SUPERSEDED by `separation()` — kept because it explains every round already run.

    Do not use it to decide whether an aspect separates a field: it tests BUNCHING from a
    single round, and #74 measured it passing and failing four rounds that all had the
    same two distinct scores. Its threshold sits where the data cannot land (#58). It is
    still computed and still reported, as a description of one round's score shape.

    A judge that gives (nearly) everything the same score has no discriminating power.

    Watches the MODE, not the maximum. The pre-registered falsifier was ">70% sit at the
    top score", which misses the symmetric failure: a judge that puts seven of eight at
    the BOTTOM has separated the field exactly as poorly, while reporting a healthy-
    looking `at_max_fraction` of 0.125. A ceiling at the floor is still a ceiling - the
    same mistake as validating a judge on a fixture scoring 0/13 and calling the
    agreement reassuring (FINDINGS #21).
    """
    scores = [s["score"] for s in result["submissions"]]
    top = max(scores)
    counts: dict[int, int] = {}
    for v in scores:
        counts[v] = counts.get(v, 0) + 1
    modal_score = max(counts, key=lambda k: (counts[k], -k))
    modal_fraction = counts[modal_score] / len(scores)
    saturated = len(set(scores)) == 1
    return {
        "scores": scores,
        "distinct": len(set(scores)),
        "spread": max(scores) - min(scores),
        "at_max_fraction": round(sum(1 for s in scores if s == top) / len(scores), 3),
        "modal_score": modal_score,
        "modal_fraction": round(modal_fraction, 3),
        "stdev": round(statistics.pstdev(scores), 3),
        "saturated": saturated,
        "separates_field": not saturated and modal_fraction <= MODAL_CEILING,
        "verdict": ("SATURATED - every submission got the same score; this judge "
                    "measured nothing" if saturated
                    else f"CEILING - {counts[modal_score]} of {len(scores)} sit at "
                         f"score {modal_score}; the field is not separated"
                    if modal_fraction > MODAL_CEILING
                    else "separates the field"),
    }


def separation(rounds: list[dict[str, Any]]) -> dict[str, Any]:
    """Does this aspect resolve ANY pair of submissions? Replaces #58's modal threshold.

    #58's gate asks whether the scores are bunched, using `modal_fraction <= 0.7`. Over
    eight submissions that statistic can only take k/8, so **0.7 sits in the gap between
    0.625 and 0.75 with nothing between**, and 52% of measured judgements sit on that
    edge: three of six verdicts flipped on unchanged input, two of them because a single
    score out of eight moved.

    Worse, it answers the wrong question. Measured on `idiomatic`/`g4_platformer`, two of
    four rounds "passed" this gate and two "failed" while ALL FOUR had the same two
    distinct scores across eight submissions (#74). Bunching is not separation.

    This asks the question directly, and it needs repeats rather than one round:

        SE = SD / sqrt(n)    per submission, from n judgements of the SAME field
        resolved(i, j)  iff  |mean_i - mean_j| > SE_i + SE_j

    A field is separated if it resolves at least one pair. **SD is the judge's own
    reliability and repeats do not shrink it** - only SE moves - so a field with no real
    gaps never resolves however long you run, and that is a MEASUREMENT rather than a
    failed experiment: those submissions are indistinguishable to this aspect.
    """
    if not rounds:
        return {"n": 0, "usable": False, "verdict": "no rounds supplied"}
    per: dict[str, list[float]] = {}
    for r in rounds:
        for s in r["submissions"]:
            per.setdefault(s["submission"], []).append(float(s["score"]))
    n = min(len(v) for v in per.values())
    if n < 2:
        return {"n": n, "usable": False,
                "verdict": "SE is undefined at n<2; separation cannot be tested from a "
                           "single round - that is what #58 tried to do"}
    # SD CONVENTION, stated because it moves the answer. `statistics.stdev` is the SAMPLE
    # standard deviation (n-1 denominator); pooling is root-mean-square across submissions.
    # Both choices are the conservative ones - they give the LARGEST SD, hence the widest
    # error bars and the fewest resolved pairs. Measured on the n=7 fun_frames set:
    #
    #   RMS of sample SD (n-1)      0.577   ->  18/28 pairs      <- used here
    #   mean of sample SD (n-1)     0.565   ->  19/28
    #   RMS of population SD (n)    0.534   ->  19/28
    #
    # One pair (godot__t0 vs ts__t1, gap 0.4286) straddles the line, so the count is 18 or
    # 19 depending on a convention nobody had written down. Fixing the convention is not
    # enough on its own - see `marginal_pairs` below, which makes a near-boundary result
    # visible instead of letting an exact-looking integer hide it.
    stats = {}
    for k, v in per.items():
        sd = statistics.stdev(v)
        stats[k] = {"mean": round(statistics.mean(v), 3), "sd": round(sd, 3),
                    "se": round(sd / (len(v) ** 0.5), 3), "n": len(v)}
    names = sorted(stats)
    resolved, unresolved, marginal = [], [], []
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a, b = stats[names[i]], stats[names[j]]
            gap = abs(a["mean"] - b["mean"])
            thresh = a["se"] + b["se"]
            if gap > thresh:
                resolved.append((names[i], names[j], round(gap, 3)))
            else:
                unresolved.append((names[i], names[j], round(gap, 3)))
            # Within 10% of the threshold either way: these flip under a different but
            # equally defensible SD convention, so a reader must see them.
            if thresh > 0 and abs(gap - thresh) / thresh < 0.10:
                marginal.append((names[i], names[j], round(gap, 3), round(thresh, 3)))
    # A LOW-n WARNING, because this gate can otherwise claim separation from an SD
    # estimated off two points. Measured: `idiomatic`/g4c uncapped reported "SEPARATES:
    # 4 of 28" at n=2 while every round had only two distinct scores (#74). An SD from
    # n=2 is one number's worth of evidence about spread, and SE = SD/sqrt(2) flatters it.
    low_n = n < 4
    sds = [s["sd"] for s in stats.values()]
    pooled = (sum(x * x for x in sds) / len(sds)) ** 0.5
    means = sorted(s["mean"] for s in stats.values())
    gaps = [round(b - a, 3) for a, b in zip(means, means[1:]) if b - a > 1e-9]
    smallest = min(gaps) if gaps else 0.0
    # n to resolve the smallest real gap, if one exists at all.
    n_needed = int((2 * pooled / smallest) ** 2) + 1 if smallest > 0 else None
    return {
        "n": n,
        "usable": True,
        "per_submission": stats,
        "pooled_sd": round(pooled, 3),
        "smallest_nonzero_gap": smallest,
        "n_to_resolve_smallest_gap": n_needed,
        "resolved_pairs": len(resolved),
        "marginal_pairs": len(marginal),
        "marginal_examples": marginal[:5],
        "sd_convention": "sample stdev (n-1), pooled as RMS - the conservative choice",
        "total_pairs": len(resolved) + len(unresolved),
        "examples": resolved[:5],
        "separates_field": bool(resolved) and not low_n,
        "low_n_warning": low_n,
        "verdict": (("LOW n=%d - SD is estimated from too few points to trust; treat any "
                     "separation here as unmeasured, not established. " % n) if low_n else "") + (
            f"SEPARATES: {len(resolved)} of {len(resolved) + len(unresolved)} pairs "
            f"resolved at n={n} (pooled SD {pooled:.3f})" if resolved
            else f"UNRESOLVABLE BY REPETITION at n={n}: no pair's gap exceeds its "
                 f"combined SE. Smallest non-zero gap {smallest}, pooled SD "
                 f"{pooled:.3f}"
                 + (f", would need n>={n_needed}" if n_needed
                    else " - all means identical, so no n resolves anything. These "
                         "submissions are indistinguishable to this aspect, which is a "
                         "measurement and not a failed experiment")),
    }


def reproducibility(a: dict[str, Any], b: dict[str, Any]) -> dict[str, Any]:
    """Two judgements of the SAME field in the SAME presentation order.

    THE GATE THIS PROJECT DID NOT HAVE, and the one that reinterprets the others.

    `ceiling` asks whether a judge separated the field. `order_invariance` asks whether it
    survives a reshuffle. Neither asks the prior question: **does the judge agree with
    ITSELF on unchanged input?** Nothing here measured that, and the answer turned out to
    be no.

    Measured 2026-08-17, by accident. `audio` reads `audio.json` and nothing else, so
    neither the telemetry repair nor `blind_language` touched its evidence; two sweeps ran
    it with a byte-identical pack and a verified-identical label->submission mapping. On
    seed 1, four of eight scores moved, the modal fraction went 0.750 -> 0.375, and the
    ceiling verdict flipped from CEILING to "separates the field". The order-invariance
    tau went 0.75 -> 0.333 - a pass turning into a failure against the pre-registered
    floor - with nothing changed at all.

    So a single-run gate verdict is a sample, not a measurement, and any conclusion drawn
    from one is drawn at n=1. Run this before believing either of the other two.
    """
    sa = {s["submission"]: s["score"] for s in a["submissions"]}
    sb = {s["submission"]: s["score"] for s in b["submissions"]}
    common = sorted(set(sa) & set(sb))
    if not common:
        return {"error": "no common submissions"}
    if a.get("order_seed") != b.get("order_seed"):
        return {"error": f"different presentation orders ({a.get('order_seed')} vs "
                         f"{b.get('order_seed')}) - that is order_invariance, not "
                         f"reproducibility"}
    ca, cb = ceiling(a), ceiling(b)
    moved = [k for k in common if sa[k] != sb[k]]
    return {
        "n": len(common),
        "order_seed": a.get("order_seed"),
        "scores_changed": len(moved),
        "submissions_that_moved": moved,
        "mean_abs_change": round(sum(abs(sa[k] - sb[k]) for k in common) / len(common), 3),
        "modal_fraction": [ca["modal_fraction"], cb["modal_fraction"]],
        "ceiling_verdict": [ca["verdict"], cb["verdict"]],
        # THE HEADLINE. A gate whose verdict flips on unchanged input cannot support a
        # conclusion from one run, whatever the scores did.
        "ceiling_verdict_stable": ca["separates_field"] == cb["separates_field"],
        "identical": not moved,
    }


def order_invariance(a: dict[str, Any], b: dict[str, Any]) -> dict[str, Any]:
    """Same field, different presentation order. A ranking that moves is an artifact.

    THE TAU IS TIE-AWARE, and it was not until 2026-08-16. This function used to convert
    scores to ranks by sorting, which hands every TIED submission an arbitrary distinct
    rank, and then counted those invented orderings as concordant or discordant. With
    eight submissions on a 0-4 scale most pairs are tied - measured: 21 of 28 on the
    first real field - so most of what it was correlating did not exist.

    `independence()` was fixed for exactly this and carries a comment explaining why.
    Nobody asked whether the same defect lived in its sibling, which is this project's
    "a control shares the assumptions of the thing it controls" in a new place: two
    functions, one lesson, applied once.

    It now reports `comparable_pairs` for the same reason `_tau` does: a tau computed on
    three real pairs must not be read like one computed on twenty-eight.
    """
    sa = {s["submission"]: s["score"] for s in a["submissions"]}
    sb = {s["submission"]: s["score"] for s in b["submissions"]}
    common = sorted(set(sa) & set(sb))
    if not common:
        return {"error": "no common submissions"}
    diffs = [abs(sa[k] - sb[k]) for k in common]
    out = dict(_tau(sa, sb))
    out.update({
        "mean_abs_score_shift": round(statistics.fmean(diffs), 3),
        "max_score_shift": max(diffs),
        "identical_scores": sum(1 for d in diffs if d == 0),
        "kendall_tau": out.pop("tau"),
    })
    return out


#: Below this many comparable pairs, a tau is arithmetic rather than evidence. With 8
#: submissions there are 28 pairs; a judge that separates them into only two groups
#: leaves few pairs comparable, and a tau computed on three of them must not be read
#: like one computed on twenty-eight.
MIN_COMPARABLE_PAIRS = 6


def _tau(a: dict[str, float], b: dict[str, float]) -> dict[str, Any]:
    """Kendall tau plus the thing a bare tau hides: how much of the field was tied.

    Ties are not a detail here. These judges score 0-4 over 8 submissions, so a judge
    that puts everything at 2 produces NO comparable pairs, and every correlation
    against it is undefined. Returning a bare `0.0` in that case would read as "these
    two aspects are independent" when the truth is "one of them measured nothing" -
    turning a ceiling failure into apparent good news, which is the exact shape of
    every artifact-mistaken-for-a-result in this project.
    """
    common = sorted(set(a) & set(b))
    conc = dis = tied = 0
    for i in range(len(common)):
        for j in range(i + 1, len(common)):
            x, y = common[i], common[j]
            s = (a[x] - a[y]) * (b[x] - b[y])
            if s > 0:
                conc += 1
            elif s < 0:
                dis += 1
            else:
                tied += 1
    comparable = conc + dis
    total = conc + dis + tied
    out: dict[str, Any] = {"n": len(common), "comparable_pairs": comparable,
                           "tied_pairs": tied, "total_pairs": total}
    if comparable == 0:
        out["tau"] = None
        out["note"] = ("no comparable pairs - at least one aspect gave the whole field "
                       "the same score, so this says nothing about independence")
    elif comparable < MIN_COMPARABLE_PAIRS:
        out["tau"] = round((conc - dis) / comparable, 3)
        out["note"] = (f"only {comparable} of {total} pairs are comparable; this tau is "
                       f"arithmetic, not evidence")
    else:
        out["tau"] = round((conc - dis) / comparable, 3)
    return out


def independence(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Do the specialists disagree with each other?

    THE GATE MOST LIKELY TO FAIL, and the reason for splitting the aspects at all: if
    `fun`, `idiomatic` and `architecture` produce the same ordering, there are not four
    judges, there is one judge with four names, and the extra three cost money and add
    nothing. Kendall tau between every pair of aspects on the same game.

    A tau near 1.0 means the pair is redundant. A tau near 0 means they are measuring
    different things - which is what a specialist layer is for. Report it; do not
    average it away.
    """
    # WHICH PRESENTATION ORDER EACH ASPECT IS BEING CORRELATED ON IS PART OF THE ANSWER.
    # This used to key by (game, aspect) and let a later result silently overwrite an
    # earlier one, so with several orders per aspect it correlated whichever seed
    # happened to come last - mixing aspect disagreement with presentation noise, in a
    # gate whose whole job is to tell those two apart. It still takes the last, because
    # callers rely on that, but it now SAYS SO: `_basis` names the seed behind every
    # aspect's scores and `_orders_collapsed` lists any aspect that contributed more than
    # one. Hold the basis fixed (same seed for every aspect) when the answer matters.
    by_game: dict[str, dict[str, dict[str, float]]] = {}
    basis: dict[str, dict[str, Any]] = {}
    seen: dict[str, dict[str, list[Any]]] = {}
    for r in results:
        if not r.get("usable"):
            continue
        scores = {s["submission"]: float(s["score"]) for s in r["submissions"]}
        by_game.setdefault(r["game"], {})[r["aspect"]] = scores
        basis.setdefault(r["game"], {})[r["aspect"]] = r.get("order_seed")
        seen.setdefault(r["game"], {}).setdefault(r["aspect"], []).append(
            r.get("order_seed"))

    out: dict[str, Any] = {}
    for game, aspects in sorted(by_game.items()):
        names = sorted(aspects)
        # A saturated aspect cannot be tested for independence at all, and saying so is
        # the finding. Gate 1 exists before gate 2 for this reason.
        saturated = sorted(n for n in names if len(set(aspects[n].values())) == 1)
        pairs: dict[str, Any] = {}
        for i in range(len(names)):
            for j in range(i + 1, len(names)):
                pairs[f"{names[i]}~{names[j]}"] = _tau(aspects[names[i]],
                                                       aspects[names[j]])
        # PER PAIR, not over the minimum. A set containing one redundant pair and one
        # opposed pair has a low minimum and is NOT independent - the redundant pair is
        # still two names for one judge. Aggregating here would hide exactly the thing
        # the gate exists to find, which is the same mistake as averaging a criterion
        # that is sound on three stacks and broken on the fourth (FINDINGS #25).
        judged = {k: v for k, v in pairs.items()
                  if v["tau"] is not None and v["comparable_pairs"] >= MIN_COMPARABLE_PAIRS}
        redundant = sorted(k for k, v in judged.items() if v["tau"] >= 0.8)
        pairs["_basis_order_seed"] = basis.get(game, {})
        collapsed = {a: s for a, s in seen.get(game, {}).items() if len(s) > 1}
        if collapsed:
            pairs["_orders_collapsed"] = {
                a: {"seeds_supplied": s, "used": basis[game][a]}
                for a, s in sorted(collapsed.items())}
        pairs["_saturated_aspects"] = saturated
        pairs["_redundant_pairs"] = redundant
        pairs["_pairs_with_enough_evidence"] = sorted(judged)
        if saturated:
            verdict = (f"CEILING FAILURE first: {', '.join(saturated)} gave the whole "
                       f"field one score. Independence cannot be assessed against an "
                       f"aspect that measured nothing - fix the ceiling before reading "
                       f"any tau here.")
        elif not judged:
            verdict = ("no pair has enough comparable pairs to judge; the field is too "
                       "tied to say anything about independence")
        elif redundant:
            verdict = (f"REDUNDANT: {', '.join(redundant)} rank the field the same way "
                       f"- each of those pairs is one judge with two names")
        else:
            verdict = ("every pair with enough evidence is independent enough to be "
                       "worth running separately")
        pairs["_verdict"] = verdict
        out[game] = pairs
    return out


def by_stack(result: dict[str, Any]) -> dict[str, float]:
    agg: dict[str, list[int]] = {}
    for s in result["submissions"]:
        agg.setdefault(s["stack"], []).append(s["score"])
    return {k: round(statistics.fmean(v), 3) for k, v in sorted(agg.items())}


def _atomic(path: Path, obj: Any) -> None:
    tmp = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps(obj, indent=2))
    os.replace(tmp, path)


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("pack")
    p.add_argument("--run", type=Path, required=True)
    p.add_argument("--game", required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--order-seed", type=int, default=0)
    p.add_argument("--aspect", required=True, choices=sorted(ASPECTS),
                   help="decides WHICH evidence goes in the pack")

    r = sub.add_parser("run")
    r.add_argument("--pack", type=Path, required=True)
    r.add_argument("--aspect", required=True)
    r.add_argument("--out", type=Path, required=True)
    r.add_argument("--model", default=DEFAULT_MODEL)

    g = sub.add_parser("gates")
    g.add_argument("--results", type=Path, nargs="+", required=True)

    pc = sub.add_parser(
        "packcheck",
        help="does every stored judge pack in a run hold exactly what its manifest "
             "lists? Reads the packs on disk. Exit 1 if not - so run it UNPIPED.")
    pc.add_argument("--run", type=Path, required=True)
    pc.add_argument("--game", nargs="*",
                    help="default: every game with submissions in the run")

    a = ap.parse_args()
    if a.cmd == "pack":
        info = build_pack(a.run, a.game, a.out, a.order_seed,
                          sees=ASPECTS[a.aspect].sees)
        print(json.dumps(info, indent=2))
        return 0
    if a.cmd == "run":
        if a.out.exists():
            print(f"refusing to overwrite {a.out}", file=sys.stderr)
            return 2
        res = run_field(a.pack, a.aspect, a.model)
        _atomic(a.out, res)
        if not res.get("usable"):
            print(json.dumps(res, indent=2)[:1500], file=sys.stderr)
            return 1
        print(json.dumps({"ceiling": ceiling(res), "by_stack": by_stack(res)}, indent=2))
        return 0
    if a.cmd == "gates":
        loaded = [json.loads(p.read_text()) for p in a.results]
        ok = [r for r in loaded if r.get("usable")]
        out: dict[str, Any] = {"n_results": len(ok)}
        for r in ok:
            out[f"ceiling:{r['aspect']}:{r['game']}:seed{r['order_seed']}"] = ceiling(r)
            out[f"by_stack:{r['aspect']}:{r['game']}:seed{r['order_seed']}"] = by_stack(r)
        for i in range(len(ok)):
            for j in range(i + 1, len(ok)):
                x, y = ok[i], ok[j]
                if x["game"] == y["game"] and x["aspect"] == y["aspect"]:
                    out[f"order_invariance:{x['game']}:{x['aspect']}"] = order_invariance(x, y)
        out["independence"] = independence(ok)
        print(json.dumps(out, indent=2))
        return 0
    if a.cmd == "packcheck":
        games = a.game or sorted({p.name.split("__")[0]
                                  for p in (a.run / "artifacts").glob("*__*")})
        bad = 0
        for game in games:
            res = pack_matches_manifest(a.run, game)
            if not res["per_submission"] and not res["unmeasurable"]:
                print(f"{game}: no judge packs on disk - nothing to check")
                continue
            dirty = {k: v for k, v in res["per_submission"].items()
                     if v["stale"] or v["missing"]}
            print(f"{game}: submissions={len(res['per_submission'])} "
                  f"files_on_disk={res['files_on_disk']} "
                  f"stale={res['stale_total']} missing={res['missing_total']} "
                  f"by_stack={res['stale_by_stack']} "
                  f"unmeasurable={len(res['unmeasurable'])} clean={res['clean']}")
            for k, v in sorted(dirty.items()):
                print(f"    {k}: disk={v['files_on_disk']} "
                      f"manifest={v['files_in_manifest']} stale={v['stale']} "
                      f"missing={v['missing']}")
            for k in res["unmeasurable"]:
                print(f"    {k}: pack on disk, NO manifest - unmeasurable, not clean")
            if not res["clean"]:
                bad += 1
        return 1 if bad else 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
