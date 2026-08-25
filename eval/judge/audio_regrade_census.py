#!/usr/bin/env python3
"""Which STORED audio verdicts move under the repaired criteria? Offline, from evidence.

`tasks/151` and `tasks/152` changed two tier-1 audio criteria, and tier 1 gates. So the
question a grader change owes an answer to is not "is the new rule better" but "how many
stored verdicts does it move, and which" - and a null needs its number as much as a hit.

This is the producer for that count. It re-applies the SHIPPED rule - `audio.py`'s own
`manifest_problems`, `distinct_floor` and `distinct_ok` - to what each stored grading
wrote down, and reports every verdict that changes. It re-runs no submission and decodes
no audio - it reconstructs the declared-event grouping from the stored `clips` and
`distinct_sound_groups`. Rebuilding the work trees would be a re-grading pass, which
`eval/judge/AGENTS.md` reserves for a separate decision.

    ./audio_regrade_census.py --selftest
    ./audio_regrade_census.py --runs-root <main checkout>/eval/runs
    ./audio_regrade_census.py --runs-root ... --json

`--runs-root` is required and is never guessed. `eval/runs/` is gitignored, so an agent
worktree's copy of that path is empty and the census would report "0 verdicts move" -
confident, uniform, and about nothing (`AGENTS.md` rule 12).

## Which criteria can move, stated rather than assumed

`audio.manifest` and `audio.distinct` are the only criteria that read the declared event
list. `audio.files_exist`, `audio.not_silent` and `audio.music_loops` range over the
manifest alone and are untouched by both tickets - EXCEPT through the fail-closed
refusal, which fails every criterion at once for a game the suites declare no events for.
That case is reported as `NO_CONTRACT` and counted separately, because it is a different
kind of move from a criterion changing its mind.

## Rebuilding the grouping from stored evidence, and when it refuses

`audio.distinct` now counts sound groups over the DECLARED events' clips only. A stored
grading recorded its groups over every `sfx` entry, as lists of file basenames, so the
new group count is that partition restricted to the declared entries - and restricting a
greedy partition is exact only when every group holding a declared clip has a declared
REPRESENTATIVE. `distinct_groups` matches each clip against `g[0]`; drop `g[0]` and the
members that matched it are no longer known to match each other.

Four refusals, each fail-closed. A refused grading is counted and named, never resolved
by assuming: an assumed group count is a verdict about a submission nobody measured, and
a row that could not be asked must not enter the null it is meant to be evidence for.

  UNDECLARED_REPRESENTATIVE   a group holding a declared clip is represented by an
                              undeclared one, so restricting the partition is not exact.
  AMBIGUOUS_BASENAMES         two `sfx` entries resolve to different paths with the same
                              file name, so a basename no longer identifies a clip.
  GROUPS_INCOMPLETE           the recorded groups do not account for exactly the
                              recorded `sfx` clips. The record is not what this assumes.
  INCOMPLETE_STORED_VERDICTS  the record carries no boolean verdict for one of the 5
                              criteria, so there is nothing to compare against.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import audio  # noqa: E402
from audio import CRITERIA  # noqa: E402
from tier1_census import report_paths  # noqa: E402

#: A grading this tool declines to answer for, and why. Every one is fail-closed: the
#: alternative to refusing is a verdict about a submission that was never measured.
REFUSALS = ("AMBIGUOUS_BASENAMES", "GROUPS_INCOMPLETE", "UNDECLARED_REPRESENTATIVE",
            "INCOMPLETE_STORED_VERDICTS")


def stored_verdicts(audio_block: dict) -> dict[str, bool] | None:
    """The stored verdict per criterion, or None unless the record carries every one.

    `None` rather than a partial dict, and `bool` rather than truthiness. A row missing
    `audio.distinct` would otherwise contribute no comparison and be counted as
    unchanged - a row that could not be asked, silently entering the null it is supposed
    to be evidence for. And `bool("false")` is `True`, so a verdict stored as a string
    would compare as a pass.
    """
    want = {cid for cid, _q in CRITERIA}
    got: dict[str, bool] = {}
    for c in audio_block.get("criteria", []):
        if not isinstance(c, dict):
            continue
        cid = c.get("id")
        if not isinstance(cid, str) or cid not in want:
            continue
        if cid in got or not isinstance(c.get("passed"), bool):
            return None
        got[cid] = c["passed"]
    return got if set(got) == want else None


def sfx_labels_in_scan_order(clips: dict) -> list[str]:
    """The `sfx.*` clip labels in the order `collect()` fed them to `distinct_groups`."""
    return [k for k in sorted(clips) if k.startswith("sfx.")]


def regroup(audio_block: dict, expected: tuple[str, ...]
            ) -> tuple[int | None, int, str | None]:
    """(groups over declared clips, declared clips found, refusal).

    `refusal` is None when the two counts are exact.
    """
    clips = audio_block.get("clips") or {}
    groups = audio_block.get("distinct_sound_groups") or []
    labels = sfx_labels_in_scan_order(clips)
    basename = {lab: Path(str(clips[lab].get("path", ""))).name for lab in labels}

    by_name: dict[str, set[str]] = {}
    for lab in labels:
        by_name.setdefault(basename[lab], set()).add(str(clips[lab].get("path", "")))
    if any(len(paths) > 1 for paths in by_name.values()):
        return None, 0, "AMBIGUOUS_BASENAMES"

    group_of: dict[str, int] = {}
    seen: Counter[str] = Counter()
    for idx, members in enumerate(groups):
        if not isinstance(members, list):
            return None, 0, "GROUPS_INCOMPLETE"
        for name in members:
            if not isinstance(name, str):
                return None, 0, "GROUPS_INCOMPLETE"
            seen[name] += 1
            if group_of.setdefault(name, idx) != idx:
                return None, 0, "AMBIGUOUS_BASENAMES"
    # MULTISETS, not a total and a membership test. Those two agree with a group list
    # that drops one occurrence of a repeated basename and adds one of another, which is
    # a grouping this tool would then score rather than refuse.
    if seen != Counter(basename.values()):
        return None, 0, "GROUPS_INCOMPLETE"

    declared = [lab for lab in labels if lab[len("sfx."):] in set(expected)]
    hit = {group_of[basename[lab]] for lab in declared}
    for idx in hit:
        rep = next(lab for lab in labels if group_of[basename[lab]] == idx)
        if rep not in declared:
            return None, len(declared), "UNDECLARED_REPRESENTATIVE"
    return len(hit), len(declared), None


def rescore(game: str, audio_block: dict) -> dict:
    """What `audio.py` says today about one stored grading, from its stored evidence."""
    expected = audio.GAME_EVENTS.get(game)
    if not expected:
        return {"outcome": "NO_CONTRACT", "now": {c: False for c, _q in audio.CRITERIA}}
    manifest = audio_block.get("manifest")
    if not isinstance(manifest, dict):
        # The stored grading never got a manifest, so it failed every criterion and
        # still does.
        return {"outcome": "NO_MANIFEST",
                "now": {c: False for c, _q in audio.CRITERIA}}

    problems, missing, extra = audio.manifest_problems(manifest, expected)
    n_groups, n_declared, refusal = regroup(audio_block, expected)
    now = {"audio.manifest": not problems}
    if refusal is None:
        now["audio.distinct"] = audio.distinct_ok(n_declared, n_groups, expected)
    return {"outcome": refusal or "SCORED", "now": now,
            "missing_events": missing, "extra_events": extra,
            "groups_over_declared": n_groups, "declared_clips": n_declared,
            "floor": audio.distinct_floor(expected)}


def load(runs_root: Path) -> tuple[list[dict], int, int]:
    """(rows with an audio grading, reports read, reports skipped as not-a-run)."""
    counted, skipped = report_paths(runs_root)
    rows = []
    for rep in counted:
        rec = json.loads(rep.read_text())
        block = ((rec.get("programmatic") or {}).get("audio")) or {}
        if not block.get("applies"):
            continue
        rows.append({
            "run": str(rep.parents[3].relative_to(runs_root)),
            "trial": rep.parents[1].name,
            "game": rec.get("game"),
            "submission": rec.get("submission") or f"::report::{rep}",
            "report": str(rep),
            "stored": stored_verdicts(block),
            "audio": block,
        })
    return rows, len(counted), len(skipped)


def census(rows: list[dict]) -> dict:
    moves, refused, unchanged = [], [], 0
    for r in rows:
        res = rescore(r["game"], r["audio"])
        if r["stored"] is None:
            res = {"outcome": "INCOMPLETE_STORED_VERDICTS", "now": {}}
        r["result"] = res
        if res["outcome"] in REFUSALS:
            refused.append(r)
            continue
        changed = {cid: (r["stored"][cid], now)
                   for cid, now in res["now"].items()
                   if r["stored"][cid] != now}
        if changed:
            r["changed"] = changed
            moves.append(r)
        else:
            unchanged += 1
    return {"gradings": len(rows),
            "submissions": len({r["submission"] for r in rows}),
            "moved": moves, "refused": refused, "unchanged": unchanged,
            "with_missing": sum(1 for r in rows
                                if r["result"].get("missing_events")),
            "with_undeclared": sum(1 for r in rows
                                   if r["result"].get("extra_events")),
            "no_manifest": sum(1 for r in rows
                               if r["result"]["outcome"] == "NO_MANIFEST")}


def render(out: dict, reports: int, skipped: int) -> None:
    print(f"stored reports read {reports}, skipped as not-a-run {skipped}")
    print(f"gradings with an audio grading: {out['gradings']} "
          f"over {out['submissions']} distinct submissions")
    print(f"unchanged {out['unchanged']}  moved {len(out['moved'])}  "
          f"refused {len(out['refused'])}")
    # A null over a population this tool exists to discriminate has to say what the
    # population was like, or it is indistinguishable from a broken extraction
    # (`AGENTS.md` rule 12). These 2 counts are the whole reason a verdict can move.
    print(f"  gradings whose manifest omits a declared event: {out['with_missing']}")
    print(f"  gradings carrying an undeclared sfx entry:      {out['with_undeclared']}")
    print(f"  gradings that produced no manifest at all:      {out['no_manifest']}")
    by_game: dict[str, int] = {}
    for r in out["moved"]:
        by_game[r["game"]] = by_game.get(r["game"], 0) + 1
    if by_game:
        print("moved, by game: " + ", ".join(f"{g} {n}" for g, n in sorted(by_game.items())))
    for r in out["moved"]:
        print(f"\n  {r['run']}/{r['trial']}  {r['game']}  [{r['result']['outcome']}]")
        for cid, (was, now) in sorted(r["changed"].items()):
            print(f"    {cid}: {'PASS' if was else 'FAIL'} -> {'PASS' if now else 'FAIL'}")
        res = r["result"]
        if res.get("missing_events"):
            print(f"    now missing: {', '.join(res['missing_events'])}")
        if res.get("groups_over_declared") is not None:
            print(f"    groups over declared {res['groups_over_declared']} of "
                  f"{res['declared_clips']} clips, floor {res['floor']}")
    for r in out["refused"]:
        print(f"\n  REFUSED {r['run']}/{r['trial']}  {r['game']}  "
              f"{r['result']['outcome']}")


# --------------------------------------------------------------------------- #
# selftest
# --------------------------------------------------------------------------- #


def _block(game: str, sfx: dict[str, str], groups: list[list[str]],
           verdicts: dict[str, bool]) -> dict:
    """A stored-shaped audio block. `sfx` maps event name -> file basename."""
    return {
        "applies": True,
        "manifest": {"music": {"file": "audio/music.wav", "loops": True},
                     "sfx": {k: {"file": f"audio/{v}"} for k, v in sfx.items()}},
        "clips": {"music": {"path": "/w/audio/music.wav"},
                  **{f"sfx.{k}": {"path": f"/w/audio/{v}"} for k, v in sfx.items()}},
        "distinct_sound_groups": groups,
        "criteria": [{"id": cid, "passed": verdicts.get(cid, True)}
                     for cid, _q in audio.CRITERIA],
        "game": game,
    }


def selftest() -> int:
    """Fixtures whose answers are written into the checks, not read off the tool."""
    fails: list[str] = []
    checks = 0

    def row(label: str, block: dict, game: str, want_outcome: str,
            want: dict[str, bool] | None = None) -> None:
        nonlocal checks
        checks += 1 + len(want or {})
        res = rescore(game, block)
        if res["outcome"] != want_outcome:
            fails.append(f"{label}: outcome {res['outcome']}, expected {want_outcome}")
            return
        for cid, expected in (want or {}).items():
            if res["now"].get(cid) != expected:
                fails.append(f"{label}: {cid} now {res['now'].get(cid)}, "
                             f"expected {expected}")

    pong = audio.GAME_EVENTS["g1_pong"]

    # 5 declared events, 5 distinct clips, no extras: floor 3, 5 groups -> PASS.
    sfx = {e: f"{e}.wav" for e in pong}
    row("five_distinct", _block("g1_pong", sfx, [[f"{e}.wav"] for e in pong], {}),
        "g1_pong", "SCORED", {"audio.manifest": True, "audio.distinct": True})

    # THE tasks/152 INPUT: all 5 on one clip plus 2 unique extras. Groups over the
    # DECLARED entries is 1, floor 3 -> FAIL, where counting all 7 entries gave 3.
    sfx = {e: "one.wav" for e in pong}
    sfx.update({"x1": "x1.wav", "x2": "x2.wav"})
    row("one_clip_plus_extras",
        _block("g1_pong", sfx, [["one.wav"] * 5, ["x1.wav"], ["x2.wav"]], {}),
        "g1_pong", "SCORED", {"audio.manifest": True, "audio.distinct": False})

    # ...and the extras still do not fail the manifest, nor help a healthy submission.
    sfx = {e: f"{e}.wav" for e in pong}
    sfx.update({"x1": "x1.wav", "x2": "x2.wav"})
    row("healthy_plus_extras",
        _block("g1_pong", sfx,
               [[f"{e}.wav"] for e in pong] + [["x1.wav"], ["x2.wav"]], {}),
        "g1_pong", "SCORED", {"audio.manifest": True, "audio.distinct": True})

    # A declared event with no entry fails the manifest.
    sfx = {e: f"{e}.wav" for e in pong[:-1]}
    row("missing_declared",
        _block("g1_pong", sfx, [[f"{e}.wav"] for e in pong[:-1]], {}),
        "g1_pong", "SCORED", {"audio.manifest": False})

    # A game the suites declare no events for: every criterion refused, fail-closed.
    row("no_contract", _block("g9_probe", {"a": "a.wav"}, [["a.wav"]], {}),
        "g9_probe", "NO_CONTRACT", {cid: False for cid, _q in audio.CRITERIA})

    # THE REFUSAL. One group whose representative is undeclared and which also holds a
    # declared clip: restricting the partition is not exact, so the tool declines.
    sfx = {e: f"{e}.wav" for e in pong}
    sfx["aaa_extra"] = "aaa.wav"
    row("undeclared_representative",
        _block("g1_pong", sfx,
               [["aaa.wav", "paddle_hit.wav"]] + [[f"{e}.wav"] for e in pong[1:]], {}),
        "g1_pong", "UNDECLARED_REPRESENTATIVE")

    # ...and it is a refusal about the REPRESENTATIVE, not about mixing: the same mixed
    # group with a declared representative is scored.
    sfx = {e: f"{e}.wav" for e in pong}
    sfx["zzz_extra"] = "zzz.wav"
    row("declared_representative",
        _block("g1_pong", sfx,
               [["game_over.wav", "zzz.wav"]]
               + [[f"{e}.wav"] for e in pong if e != "game_over"], {}),
        "g1_pong", "SCORED", {"audio.distinct": True})

    # Groups that do not account for the recorded clips: refused, never guessed.
    sfx = {e: f"{e}.wav" for e in pong}
    row("groups_incomplete", _block("g1_pong", sfx, [["paddle_hit.wav"]], {}),
        "g1_pong", "GROUPS_INCOMPLETE")

    # Two entries, same basename, different paths: a basename stops identifying a clip.
    amb = _block("g1_pong", {e: f"{e}.wav" for e in pong},
                 [[f"{e}.wav"] for e in pong], {})
    amb["clips"]["sfx.game_over"]["path"] = "/w/other/paddle_hit.wav"
    row("ambiguous_basenames", amb, "g1_pong", "AMBIGUOUS_BASENAMES")

    # A stored record that cannot be compared is REFUSED, never counted as unchanged.
    all_crits = [{"id": cid, "passed": True} for cid, _q in audio.CRITERIA]
    for label, crits in (
            ("a criterion missing from the record", all_crits[:-1]),
            ("a verdict stored as the string 'false'",
             [{"id": cid, "passed": ("false" if cid == "audio.distinct" else True)}
              for cid, _q in audio.CRITERIA]),
            ("a criterion recorded twice", all_crits + [all_crits[0]]),
            ("an id that is not a string",
             all_crits[:-1] + [{"id": ["audio.music_loops"], "passed": True}])):
        checks += 1
        b = _block("g1_pong", {e: f"{e}.wav" for e in pong},
                   [[f"{e}.wav"] for e in pong], {})
        b["criteria"] = crits
        out = census([{"run": "r", "trial": "t", "game": "g1_pong", "submission": "s",
                       "report": "-", "stored": stored_verdicts(b), "audio": b}])
        if (len(out["refused"]), out["unchanged"]) != (1, 0):
            fails.append(f"{label}: refused {len(out['refused'])}, unchanged "
                         f"{out['unchanged']}; expected 1, 0")

    # ...and a grouping whose basename MULTIPLICITIES do not match the recorded clips.
    # THE VARIANT A TOTAL CANNOT SEE: one occurrence of a repeated name dropped and one
    # of another added. Same total, every name present, every name in one group only,
    # and a different partition of the submission.
    sfx_dup = {e: ("one.wav" if e in pong[:2] else f"{e}.wav") for e in pong}
    right = [["one.wav", "one.wav"]] + [[f"{e}.wav"] for e in pong[2:]]
    wrong = [["one.wav"], [f"{pong[2]}.wav"] * 2,
             [f"{pong[3]}.wav"], [f"{pong[4]}.wav"]]
    row("groups_wrong_multiplicities",
        _block("g1_pong", sfx_dup, wrong, {}), "g1_pong", "GROUPS_INCOMPLETE")
    # GREEN: the same fixture with the multiplicities right is scored, 4 groups, floor 3.
    row("groups_right_multiplicities",
        _block("g1_pong", sfx_dup, right, {}),
        "g1_pong", "SCORED", {"audio.distinct": True})

    # And the whole census over a 2-row population: 1 moves, 1 does not.
    sfx_bad = {e: "one.wav" for e in pong}
    sfx_bad.update({"x1": "x1.wav", "x2": "x2.wav"})
    rows = [
        {"run": "r", "trial": "moves", "game": "g1_pong", "submission": "a",
         "report": "-", "stored": {"audio.distinct": True, "audio.manifest": True},
         "audio": _block("g1_pong", sfx_bad,
                         [["one.wav"] * 5, ["x1.wav"], ["x2.wav"]], {})},
        {"run": "r", "trial": "steady", "game": "g1_pong", "submission": "b",
         "report": "-", "stored": {"audio.distinct": True, "audio.manifest": True},
         "audio": _block("g1_pong", {e: f"{e}.wav" for e in pong},
                         [[f"{e}.wav"] for e in pong], {})},
    ]
    out = census(rows)
    checks += 1
    if (len(out["moved"]), out["unchanged"], len(out["refused"])) != (1, 1, 0):
        fails.append(f"census over 2 rows: moved {len(out['moved'])}, unchanged "
                     f"{out['unchanged']}, refused {len(out['refused'])}; "
                     f"expected 1, 1, 0")

    print(f"{checks} expectations checked, {len(fails)} unmet")
    for f in fails:
        print(f"  FAIL {f}")
    return 1 if fails else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--runs-root", type=Path,
                    help="the MAIN CHECKOUT's eval/runs (gitignored; never guessed)")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--report", type=Path,
                    help="one stored report.json: print its stored verdicts beside the "
                         "recomputed ones. Prove the extraction on a row whose answer "
                         "you can state in advance before believing the census")
    a = ap.parse_args()
    if a.selftest:
        return selftest()
    if a.report is not None:
        rec = json.loads(a.report.read_text())
        block = ((rec.get("programmatic") or {}).get("audio")) or {}
        if not block.get("applies"):
            print(f"{a.report}: no audio grading")
            return 1
        res = rescore(rec.get("game"), block)
        print(f"{a.report}\n  game {rec.get('game')}  outcome {res['outcome']}")
        print(f"  expected events now: {list(audio.GAME_EVENTS.get(rec.get('game'), ()))}")
        print(f"  stored extra_events: {block.get('extra_events')}")
        print(f"  stored groups: {block.get('distinct_sound_groups')}")
        for k in ("missing_events", "groups_over_declared", "declared_clips", "floor"):
            if k in res:
                print(f"  {k}: {res[k]}")
        stored = stored_verdicts(block)
        if stored is None:
            print(f"  REFUSED INCOMPLETE_STORED_VERDICTS: this record does not carry "
                  f"a boolean verdict for each of the {len(CRITERIA)} criteria, so "
                  f"nothing can be compared")
            return 1
        for cid, now in sorted(res["now"].items()):
            was = stored[cid]
            print(f"  {cid}: stored {'PASS' if was else 'FAIL'} -> "
                  f"now {'PASS' if now else 'FAIL'}"
                  f"{'   MOVED' if was != now else ''}")
        return 0
    if a.runs_root is None:
        ap.error("--runs-root is required: eval/runs/ is gitignored, and a census run "
                 "against an empty tree reports that nothing moved")
    if not a.runs_root.is_dir():
        ap.error(f"{a.runs_root} is not a directory")
    rows, reports, skipped = load(a.runs_root)
    out = census(rows)
    if a.json:
        print(json.dumps({
            "reports": reports, "skipped": skipped,
            "gradings": out["gradings"], "submissions": out["submissions"],
            "unchanged": out["unchanged"],
            "with_missing": out["with_missing"],
            "with_undeclared": out["with_undeclared"],
            "no_manifest": out["no_manifest"],
            "moved": [{"run": r["run"], "trial": r["trial"], "game": r["game"],
                       "changed": {k: list(v) for k, v in r["changed"].items()},
                       "result": {k: v for k, v in r["result"].items() if k != "now"}}
                      for r in out["moved"]],
            "refused": [{"run": r["run"], "trial": r["trial"], "game": r["game"],
                         "outcome": r["result"]["outcome"]} for r in out["refused"]],
        }, indent=2))
    else:
        render(out, reports, skipped)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
