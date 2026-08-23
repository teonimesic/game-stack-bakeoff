#!/usr/bin/env python3
"""Rebuild a stored run's judge packs, with the starter-drift exclusion set COMPUTED.

Re-packing an old run is not "run the packer again". `anonymise.build_pack` drops files
byte-identical to the starter, and it compares against the starter AS IT IS NOW. A starter
that has moved since the run was packed makes template code look authored (#77), which
silently changes what every code aspect reads - the opposite failure to the one being
repaired (#95).

`build_pack` takes `exclude_origins` for exactly this and its docstring states the formula:

    E = (origins in a pack rebuilt against today's starter)
        MINUS (origins in the stored manifest)
        MINUS (files the original dropped for length)

The third term is 0 by construction since #69 and is ASSERTED here rather than assumed.

**A formula is not a measurement.** The subtraction gives an answer for any run; nothing in
it can tell you the answer is right, because both of its terms come from the same packer.
So every excluded file is checked against an independent record of the starter the agent
was actually handed: `wholegame.prepare` copies the starter into the work tree and commits
it as `starter baseline`, and that commit is still on disk for a run whose work tree
survives. A file may only be excluded if it is byte-identical to its blob in that commit.

WHERE THIS REFUSES, AND WHY EACH REFUSAL IS THE HONEST OUTCOME:

| refusal | what it means |
|---|---|
| no work tree, or no `starter baseline` root commit | the exclusion set is not recoverable. Mark the run; do not re-pack it |
| an excluded file is NOT identical to the baseline blob | the subtraction and the baseline disagree. One of them is wrong and this cannot say which |
| a stored manifest origin no longer packs | the starter gained a file the agent had written. Drift in the other direction; the same formula does not cover it |
| a stored manifest origin IS identical to the baseline | the stored pack ALREADY counted template code as authored. Exclusion cannot repair that; the pack was wrong when it was written |

Re-packing changes what a judge would be shown. **Any judge round stored before a re-pack
read a field that no longer exists**, and no gate can retroactively tell you what it read -
see the provenance capture in `field.py` and #83. Say so wherever the run's results are
reported.

Usage, and it is a dry run unless you say otherwise:

    python3 judge/repack.py runs/<run>            # compute and show the exclusion set
    python3 judge/repack.py runs/<run> --write    # rebuild the packs and the pack block

Verify with `judge/field.py packcheck --run runs/<run>`, UNPIPED, before and after.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import anonymise  # noqa: E402

#: The message `wholegame.prepare` commits the copied starter under. Anything else means
#: this is not a work tree built by this harness and its first commit proves nothing.
BASELINE_SUBJECTS = ("starter baseline", "baseline")


def _atomic(path: Path, obj: Any) -> None:
    tmp = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    tmp.write_text(json.dumps(obj, indent=2))
    os.replace(tmp, path)


def _git_blob_sha(data: bytes) -> str:
    """git's own object id, so a blob can be compared without checking anything out."""
    h = hashlib.sha1()
    h.update(b"blob %d\0" % len(data))
    h.update(data)
    return h.hexdigest()


def starter_baseline(work: Path) -> dict[str, str] | None:
    """rel -> blob sha of the starter as the agent received it, or None if unrecoverable."""
    if not (work / ".git").exists():
        return None
    try:
        roots = subprocess.run(
            ["git", "-C", str(work), "rev-list", "--max-parents=0", "HEAD"],
            capture_output=True, text=True, check=True).stdout.split()
        if len(roots) != 1:
            return None
        subject = subprocess.run(
            ["git", "-C", str(work), "log", "-1", "--format=%s", roots[0]],
            capture_output=True, text=True, check=True).stdout.strip()
        if subject not in BASELINE_SUBJECTS:
            return None
        listing = subprocess.run(
            ["git", "-C", str(work), "ls-tree", "-r", roots[0]],
            capture_output=True, text=True, check=True).stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    out: dict[str, str] = {}
    for line in listing.splitlines():
        meta, rel = line.split("\t", 1)
        out[rel] = meta.split()[2]
    return out


def starter_dir(rec: dict[str, Any], override: Path | None, stack: str) -> Path | None:
    """THE STARTER IS AN ADDRESS, AND IT IS RECORDED. Do not reconstruct it (rule 12).

    `evaluate.py` writes the absolute starter path it used into `report.json`, so the
    directory whose contents the stored manifest was filtered against is a stored fact,
    not something to derive from where this file happens to live.

    Deriving it cost a run of this tool: a default of `<this file>/../starters` resolves
    inside an agent's git WORKTREE, where the Unity starter's `tools/analyzer/bin/` -
    untracked build output that a fresh checkout does not have - is absent. Three Unity
    files then looked like authored work, the corroboration check refused two submissions,
    and the refusal was correct about the symptom and wrong about the cause.

    `--starters` still overrides, for a run whose repository has moved since. It is a
    directory of per-stack starters, and it is used only if the recorded path is gone.
    """
    rec_path = rec.get("starter")
    if rec_path:
        p = Path(rec_path)
        if p.is_dir():
            return p
    if override is not None:
        p = override / stack
        if p.is_dir():
            return p
    return None


def work_tree(run: Path, submission: str) -> Path | None:
    """Where the submission was built. Stored in the trial record, not guessed from a root.

    Wholegame runs put the work tree OUTSIDE `eval/runs/`; the older small-task runs put it
    at `<run>/work/<trial>`. Both are tried, the trial record first, because the address is
    an input to the check (rule 12).
    """
    rec = run / "trials" / f"{submission}.json"
    if rec.is_file():
        try:
            w = Path(json.loads(rec.read_text())["work"])
            if w.is_dir():
                return w
        except (KeyError, json.JSONDecodeError, OSError):
            pass
    alt = run / "work" / submission
    return alt if alt.is_dir() else None


def plan(run: Path, starters: Path | None, games: list[str] | None) -> dict[str, Any]:
    """Compute the exclusion set for every submission, and every reason not to trust it."""
    art = run / "artifacts"
    names = sorted(d.name for d in art.glob("*__*")
                   if (d / "eval" / "judge_pack" / "code").is_dir()
                   and (not games or d.name.split("__")[0] in games))
    per: dict[str, Any] = {}
    tmp = Path(tempfile.mkdtemp(prefix="repack-plan-"))
    for name in names:
        d = art / name
        stack = name.split("__")[1]
        game = name.split("__")[0]
        row: dict[str, Any] = {"stack": stack, "game": game, "refusals": []}
        per[name] = row

        rep = d / "eval" / "report.json"
        rec: dict[str, Any] = {}
        if rep.is_file():
            try:
                rec = json.loads(rep.read_text())
            except (OSError, json.JSONDecodeError):
                rec = {}
        pack = rec.get("pack") or {}
        manifest = pack.get("manifest")
        if manifest is None:
            row["refusals"].append(
                "no `pack.manifest` in eval/report.json: there is no stored set to "
                "subtract from, so the exclusion set is UNRECOVERABLE, not empty")
            continue
        dropped = pack.get("files_dropped_for_length")
        if dropped != 0:
            row["refusals"].append(
                f"files_dropped_for_length={dropped!r}, not 0. The formula's third term is "
                f"non-zero, so those files are legitimately returning and must NOT be "
                f"excluded - this tool does not cover that case (#62, #69)")
            continue
        stored = {e["label"]: e["origin"] for e in manifest}
        M = set(stored.values())

        work = work_tree(run, name)
        if work is None:
            row["refusals"].append("no work tree on disk; cannot corroborate")
            continue
        row["work"] = str(work)
        starter = starter_dir(rec, starters, stack)
        if starter is None:
            row["refusals"].append(
                f"the starter this pack was filtered against is not on disk "
                f"(report.json records {rec.get('starter')!r}) and no --starters "
                f"directory supplies a {stack}/ replacement")
            continue
        row["starter"] = str(starter)

        info = anonymise.build_pack(work, starter, tmp / name, None,
                                    submission_id=pack.get("submission_id")
                                    or f"{game}-{name}")
        A = {e["origin"] for e in info["manifest"]}
        E = A - M

        base = starter_baseline(work)
        if base is None:
            row["refusals"].append(
                f"{work} has no single root commit subject in {BASELINE_SUBJECTS}: the "
                f"starter as given is not recoverable, so an exclusion set computed by "
                f"subtraction cannot be checked against anything")
            continue

        def identical(rel: str) -> bool:
            sha = base.get(rel)
            f = work / rel
            return bool(sha) and f.is_file() and _git_blob_sha(f.read_bytes()) == sha

        uncorroborated = sorted(r for r in E if not identical(r))
        orphaned = sorted(M - A)
        already_authored = sorted(r for r in M if identical(r))
        if uncorroborated:
            row["refusals"].append(
                f"{len(uncorroborated)} file(s) the subtraction wants excluded are NOT "
                f"byte-identical to the starter baseline: {uncorroborated}. Excluding them "
                f"would hide authored work")
        if orphaned:
            row["refusals"].append(
                f"{len(orphaned)} stored manifest origin(s) no longer pack at all: "
                f"{orphaned}. The starter moved toward the submission; exclusion cannot "
                f"put them back")
        if already_authored:
            row["refusals"].append(
                f"{len(already_authored)} stored manifest origin(s) are byte-identical to "
                f"the starter baseline: {already_authored}. The STORED pack already counted "
                f"template code as authored (#77); re-packing cannot repair that")
        row.update({
            "stored_files": len(M), "rebuilt_files": len(A),
            "exclude": sorted(E),
            "corroborated_against_starter_baseline": not uncorroborated,
            "labels_reproduce": None,
        })
        if not row["refusals"]:
            check = anonymise.build_pack(work, starter, tmp / (name + ".x"), None,
                                         submission_id=pack.get("submission_id")
                                         or f"{game}-{name}",
                                         exclude_origins=frozenset(E))
            row["labels_reproduce"] = (
                {e["label"]: e["origin"] for e in check["manifest"]} == stored)
            if not row["labels_reproduce"]:
                row["refusals"].append(
                    "rebuilding with the exclusion set does not reproduce the stored "
                    "label -> origin mapping; the picked set differs by more than the "
                    "starter drift and this tool cannot say what else changed")
    return per


def write(run: Path, per: dict[str, Any]) -> int:
    art = run / "artifacts"
    changed = 0
    for name, row in sorted(per.items()):
        if row["refusals"]:
            continue
        d = art / name
        rep = d / "eval" / "report.json"
        rec = json.loads(rep.read_text())
        frames = d / "eval" / "frames"
        info = anonymise.build_pack(
            Path(row["work"]), Path(row["starter"]),
            d / "eval" / "judge_pack", frames if frames.is_dir() else None,
            submission_id=rec["pack"]["submission_id"],
            exclude_origins=frozenset(row["exclude"]))
        rec["pack"] = {"built": True, "at": str(d / "eval" / "judge_pack"), **info}
        # THE AUDIT TRAIL IS THE POINT (AGENTS.md). A pack block that merely looks correct
        # cannot answer "was this the original set, or a set someone chose?" later.
        rec["pack"]["repacked"] = {
            "at": __import__("datetime").datetime.now(
                __import__("datetime").timezone.utc).isoformat(),
            "reason": "FINDINGS #95: build_pack did not clear its destination, so nine "
                      "evaluation passes were stacked on disk under shifted labels",
            "starter": row["starter"],
            "excluded_origins": sorted(row["exclude"]),
            "exclusion_set_recovered_by":
                "(rebuilt against today's starter) MINUS (stored manifest) MINUS "
                "(files_dropped_for_length, asserted 0), each excluded file then verified "
                "byte-identical to its blob in the work tree's `starter baseline` commit",
            "labels_reproduce_stored_manifest": row["labels_reproduce"],
            "supersedes_judge_rounds_stored_before": True,
        }
        _atomic(rep, rec)
        changed += 1
    return changed


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("run", type=Path, help="a PATH to eval/runs/<run>, not a run name")
    ap.add_argument("--game", nargs="*")
    ap.add_argument("--starters", type=Path, default=None,
                    help="fallback directory of per-stack starters, used ONLY when the "
                         "path report.json records is no longer on disk")
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()

    run = a.run.resolve()
    if not (run / "artifacts").is_dir():
        print(f"repack: {run} has no artifacts/ - `run` takes a PATH, not a run name",
              file=sys.stderr)
        return 2
    per = plan(run, a.starters.resolve() if a.starters else None, a.game)
    if not per:
        print(f"repack: no judge packs under {run}/artifacts - nothing to do",
              file=sys.stderr)
        return 2

    blocked = 0
    total_excluded = 0
    for name, row in sorted(per.items()):
        if row["refusals"]:
            blocked += 1
            print(f"{name}: REFUSED")
            for r in row["refusals"]:
                print(f"    {r}")
            continue
        total_excluded += len(row["exclude"])
        print(f"{name:<34} stored={row['stored_files']:>3} "
              f"rebuilt={row['rebuilt_files']:>3} exclude={len(row['exclude'])} "
              f"corroborated={row['corroborated_against_starter_baseline']} "
              f"labels_reproduce={row['labels_reproduce']} {row['exclude'] or ''}")
    print(f"\n{len(per)} submission(s), {blocked} refused, "
          f"{total_excluded} file(s) excluded as starter drift")
    if blocked:
        print("A REFUSED submission must be MARKED, not re-packed: its exclusion set "
              "cannot be recovered, and re-packing it anyway would reclassify template "
              "code as authored work (#77).", file=sys.stderr)
    if not a.write:
        print("dry run; pass --write to rebuild the packs")
        return 1 if blocked else 0
    n = write(run, per)
    print(f"re-packed {n} submission(s); every judge round stored before now read a "
          f"field that no longer exists")
    return 1 if blocked else 0


if __name__ == "__main__":
    raise SystemExit(main())
