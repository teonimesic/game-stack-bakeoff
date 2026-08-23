#!/usr/bin/env python3
"""A durable record of what a measurement was CONFIGURED to be is written once, never
overwritten - and an offline audit says whether the stored ones still describe their runs.

    python3 eval/tools/manifest.py audit                     # sweep eval/runs
    python3 eval/tools/manifest.py audit --runs-dir PATH [--json]
    python3 eval/tools/manifest.py mark RUN_DIR --why "..." [--reconstruct]
    python3 eval/tools/manifest_selftest.py                  # the controls

## What this guards, and why it is stated as a resource

FINDINGS #77 already said *keep manifests, not just scores*. Its trigger named **judge
packs**, so it never reached run manifests, and `wholegame.py cmd_build` went on writing
`runs/<run>/suite.json` unconditionally: a partial re-run launched into an existing run
directory overwrote it, the canonical manifest ended up describing the re-run, and the run
it is named for had no manifest at all (#93). That is AGENTS.md's own meta-lesson - a rule
whose trigger is an enumeration has to be re-derived by every reader who meets an instance
that is not on the list.

So the trigger here is the RESOURCE, not the mechanism:

> **Any durable record of what a measurement was configured to be is append-only. A second
> launch adds a record; it never replaces one.**

Not "suite.json". Not "run manifests". Anything a later reader would use to establish what
a stored measurement WAS - suite manifests, prompt snapshots, blinding mappings, control
floors, regime notes. A fix that only handles `suite.json` repeats #77's mistake one size
down.

`write_manifest()` is the write path. It reserves the name with `O_EXCL` before writing, so
"does it already exist" and "claim it" are one operation rather than two, and on collision
it writes a stamped sibling carrying `supersedes` and `previous_started_at`. Nothing it
does can shorten, replace or truncate a record already on disk. The precedent is already in
`cmd_build`: the prompt snapshot has been kept-not-overwritten since #57, for exactly this
reason, and the manifest three lines below it was not.

## Append-only has TWO shapes, and choosing the wrong one makes a live name stale

The property being protected is *no record on disk is destroyed*. Two different file
layouts both satisfy it, and they differ in **what the canonical name means afterwards**:

| | canonical name holds | superseded record goes to | writer |
|---|---|---|---|
| **pinned** | the FIRST record | `<stem>-<stamp>` (the new one) | `write_manifest()` |
| **rolling** | the LATEST record | `<stem>-<stamp>` (the old one) | `write_rolling_json()` / `write_rolling()` |

**The criterion is whether the directory has an identity the record is named for.**
`runs/wg-g4-2026-08-17T09-38-32/suite.json` is *the manifest of the launch the directory
is named after*; a later launch into it is an intruder and must not take the name, which
is why `write_manifest` pins. A judge sweep directory and a backup destination have no such
identity: they accumulate, and their summary describes the accumulation **as of the last
invocation**. Pinning there would silently make the canonical name the oldest statement, and
`eval/PROTOCOL.md` instructs a reader in as many words to *"never quote the evidence count
from this table - read it from `MEASURED.json`"*. A guard that turns that instruction into
a stale number has protected the record and broken the reader.

Both shapes live here, in one file, deliberately: two similar policies written in two
places is how #100 came back and how `suite.json` came to be guarded in one harness and
overwritten in the other (#120).

`write_rolling()` hard-links the existing file aside before `os.replace` puts the new one
under the canonical name, so the preservation happens *first* and is atomic. **An identical
restatement is not a new record**: when the bytes match what is already there, nothing is
written and nothing is rolled, so `--verify-only` re-run against an unchanged evidence set
does not accumulate a megabyte of identical checksum manifests.

## What the audit asks

Two independent questions, because neither one alone finds all five affected directories:

1. **Does the manifest describe the reports beside it?** Derives the declared trial ids
   from `games x stacks x trials` and compares them with `trials/*.json`.
2. **Does the manifest belong to the directory it sits in?** Schema 2 records `run_dir`,
   so this is an equality test. Legacy manifests have only `started_at`, so it is compared
   with the directory-name stamp.

The census alone clears `wg-arena3d`, whose manifest WAS overwritten by a second wave
(rust/ts trials on 2026-08-15, unity/godot on 2026-08-16, `started_at` rewritten to the
second) and happens to declare the same shape both times. The stamp check alone clears
`wg-audio`, which is content-wrong and stamp-clean.

## The timezone trap this file exists to not re-create

Run directory names are chosen by the operator on the command line - `--run-dir` - and this
project has stamped them BOTH ways: `wg-calib`, `wg-cal48`, `wg-cal48b` and `wg-audio` in
local time (UTC-3), `wg-g4b` and `wg-g4c` in UTC. A checker that assumes one basis reports
a 3-hour drift on half the corpus. #93's third row is exactly that mistake made by hand: it
listed `wg-audio-2026-08-14T12-29-42` as carrying the tell because `15:29:43` does not look
like `12-29-42`, when the two are the same instant. Measured deltas over the stored corpus,
taking the closer of the two bases: 1s, 1s, 1s, 1s, 12s, 24s for the consistent runs and
4748s, 27668s, 50225s, 79237s for the inconsistent ones. `STAMP_TOLERANCE_S` sits in the
gap, an order of magnitude clear of both edges.

Schema 2 removes the guesswork for everything written from now on: the manifest names its
own directory, and `MISPLACED` is an equality failure with no timezone in it.

## Marking, and why it is not a mute

`eval/runs` is evidence. A manifest reconstructed today is not the record that was written
then, so the three known-bad directories are MARKED rather than repaired, and the marker
stores the exact issue list it acknowledges. The audit re-measures every time and compares:
a marker that still matches downgrades ERROR to `marked`, and a marker that no longer
matches raises `MARKER_STALE`. So it cannot hide a change - only an unchanged, already-known
state. Any reconstructed configuration lives INSIDE the marker under `reconstructed_*`
keys, never under a `suite*.json` name, because a file named like a manifest reads like one.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

# Schema 1: stacks/games/trials/model/max_turns/max_budget_usd/work_root/started_at.
# Schema 2 adds `run_dir` (self-identification) and `manifest_schema`, and on a re-run
# `supersedes` / `previous_started_at`.
SCHEMA = 2

# Derived, not chosen: see the docstring. The consistent runs land at <=24s, the
# inconsistent ones at >=4748s.
STAMP_TOLERANCE_S = 900

# The machine that produced every stored run is UTC-3 with no DST; a directory stamp is
# accepted if it matches `started_at` in EITHER basis.
LOCAL_UTC_OFFSET_HOURS = -3

MARKER_NAME = "MANIFEST-DEFECT.json"
CANONICAL = "suite.json"

# Keys under which a record may state when it was made, read in this order. A record
# carrying none of them is stamped from its mtime, which is strictly weaker: a `cp`
# rewrites every mtime in glob order and produces a clean, ordered, meaningless
# chronology - the defect `judge_ledger.MIN_SPLIT_S` was bought with. An embedded field
# travels with the bytes; an mtime does not.
RECORD_TIME_KEYS = ("started_at", "verified_at", "written_at", "generated_at")
_STAMP_RE = re.compile(r"(\d{4}-\d{2}-\d{2})T(\d{2})-(\d{2})-(\d{2})")

# Keys that make a manifest a WHOLEGAME manifest. `runner.py` writes a different, smaller
# shape into a directory it creates fresh every launch, so it cannot collide - it is
# reported as LEGACY_SHAPE rather than silently skipped, because "skipped" and "clean"
# print the same way.
WHOLEGAME_KEYS = ("stacks", "games", "trials", "started_at")


# --------------------------------------------------------------------------- write path

def _iso_compact(value: str) -> str:
    try:
        t = dt.datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return "unstamped"
    if t.tzinfo is not None:
        t = t.astimezone(dt.timezone.utc)
    return t.strftime("%Y%m%dT%H%M%SZ")


def _reserve(path: Path) -> bool:
    """Claim `path` exclusively. Returns False if it already exists.

    O_EXCL makes "is it there" and "take it" one operation. Checking with `exists()` and
    then writing is two, and two is where a record gets lost.
    """
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
    except FileExistsError:
        return False
    os.close(fd)
    return True


def _atomic_bytes(path: Path, data: bytes) -> None:
    tmp = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)


def _atomic_write(path: Path, obj: dict) -> None:
    _atomic_bytes(path, (json.dumps(obj, indent=2) + "\n").encode())


def write_manifest(run_dir: Path, payload: dict, *, name: str = CANONICAL,
                   quiet: bool = False) -> Path:
    """Write a configuration record into `run_dir` WITHOUT destroying any already there.

    Returns the path actually written, which is `run_dir/name` the first time and a
    stamped sibling every time after.
    """
    run_dir = Path(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    rec = dict(payload)
    rec["run_dir"] = run_dir.name
    rec["manifest_schema"] = SCHEMA

    target = run_dir / name
    if _reserve(target):
        _atomic_write(target, rec)
        return target

    existing = read_json(target) or {}
    rec["supersedes"] = name
    rec["previous_started_at"] = existing.get("started_at")
    stem = Path(name).stem
    base = f"{stem}-{_iso_compact(rec.get('started_at'))}"
    n = 1
    while True:
        candidate = run_dir / (f"{base}.json" if n == 1 else f"{base}-{n}.json")
        if _reserve(candidate):
            break
        n += 1
    _atomic_write(candidate, rec)
    if not quiet:
        print(f"\n  {name} ALREADY EXISTS in {run_dir.name} and was NOT overwritten.\n"
              f"  This launch's configuration went to {candidate.name}.\n"
              f"  {name} remains the record of what this directory was named for; the\n"
              f"  reports now beside it may come from more than one launch, and\n"
              f"  `tools/manifest.py audit` will say so (FINDINGS #93).\n")
    return candidate


# ------------------------------------------------------- the rolling append-only path

def record_stamp(path: Path) -> str:
    """When the record at `path` was made, as a compact UTC stamp for a filename.

    Prefers a timestamp the record carries in its own bytes over the filesystem's mtime,
    for the reason in `RECORD_TIME_KEYS`. Returns `unstamped` rather than raising: a
    record whose time cannot be established still has to be KEPT, and refusing to name it
    would be a reason to destroy it, which is the one outcome this module exists to
    prevent (AGENTS.md rule 7).
    """
    path = Path(path)
    obj = read_json(path)
    if obj is not None:
        for k in RECORD_TIME_KEYS:
            v = obj.get(k)
            if isinstance(v, str):
                s = _iso_compact(v)
                if s != "unstamped":
                    return s
    try:
        mt = path.stat().st_mtime
    except OSError:
        return "unstamped"
    return dt.datetime.fromtimestamp(mt, dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def keep_previous(path: Path) -> Path | None:
    """Preserve whatever is at `path` under a stamped sibling. Returns the sibling.

    `None` means there was nothing there - not that nothing was kept.

    `os.link` is the reservation: it fails with `FileExistsError` if the sibling name is
    taken, so choosing the name and claiming it are one operation, exactly as `O_EXCL` is
    for `write_manifest`. It also costs nothing for a large file and leaves the old inode
    reachable after `os.replace` renames a new file over the canonical path.

    The fallback matters on a real destination: this project's evidence copy is meant to
    move to an external disk, and exFAT has no hard links.
    """
    path = Path(path)
    if not path.exists():
        return None
    base = f"{path.stem}-{record_stamp(path)}"
    n = 1
    while True:
        cand = path.with_name(f"{base}{path.suffix}" if n == 1
                              else f"{base}-{n}{path.suffix}")
        try:
            os.link(path, cand)
            return cand
        except FileExistsError:
            n += 1
        except OSError:
            if _reserve(cand):
                _atomic_bytes(cand, path.read_bytes())
                return cand
            n += 1


def write_rolling(path: Path, data: bytes | str, *,
                  quiet: bool = False) -> tuple[Path, Path | None]:
    """Write `data` to `path`, keeping the copy it replaces. Returns `(path, kept)`.

    The canonical name holds the LATEST record; see the module docstring for when that is
    the right shape and when `write_manifest` is. `kept` is `None` when there was nothing
    to keep, and also when the new bytes are identical to the bytes already there - an
    identical restatement is not a new record, and in that case nothing is written at all,
    so the mtime goes on recording when the content last CHANGED.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = data if isinstance(data, bytes) else data.encode()
    if path.exists() and path.read_bytes() == payload:
        return path, None
    kept = keep_previous(path)
    _atomic_bytes(path, payload)
    if kept is not None and not quiet:
        print(f"  {path.name} already existed and was NOT overwritten in place: the "
              f"record it replaces is kept as {kept.name}.")
    return path, kept


def write_rolling_json(path: Path, payload: dict, *,
                       quiet: bool = False) -> tuple[Path, Path | None]:
    """`write_rolling` for a JSON record, which can name what it superseded.

    The key is `superseded_record`, NOT `supersedes`: `write_manifest` writes `supersedes`
    on the sibling to name the canonical file it did not take, and here it is the
    canonical file naming the sibling. Same word, opposite direction - so it gets a
    different word, because a reader who has met one of these will meet the other.

    There is no identical-bytes short-circuit here, and it would never fire if there were:
    every caller's payload carries one of `RECORD_TIME_KEYS`, so two writes differ in at
    least that field.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    kept = keep_previous(path)
    rec = dict(payload)
    rec["superseded_record"] = kept.name if kept is not None else None
    _atomic_bytes(path, (json.dumps(rec, indent=2) + "\n").encode())
    if kept is not None and not quiet:
        print(f"  {path.name} already existed and was NOT overwritten in place: the "
              f"record it replaces is kept as {kept.name}.")
    return path, kept


# --------------------------------------------------------------------------- read path

def read_json(path: Path) -> dict | None:
    try:
        obj = json.loads(Path(path).read_text())
    except (OSError, ValueError):
        return None
    return obj if isinstance(obj, dict) else None


def read_manifests(run_dir: Path) -> list[tuple[Path, dict]]:
    """Every configuration record in the directory, canonical first."""
    out = []
    for p in sorted(Path(run_dir).glob("suite*.json")):
        obj = read_json(p)
        if obj is not None:
            out.append((p, obj))
    out.sort(key=lambda pair: (pair[0].name != CANONICAL, pair[0].name))
    return out


def declared_trial_ids(m: dict) -> set[str] | None:
    if not all(k in m for k in ("stacks", "games", "trials")):
        return None
    try:
        n = int(m["trials"])
    except (TypeError, ValueError):
        return None
    return {f"{g}__{s}__t{i}"
            for g in m["games"] for s in m["stacks"] for i in range(n)}


def present_trial_ids(run_dir: Path) -> set[str]:
    d = Path(run_dir) / "trials"
    return {p.stem for p in d.glob("*.json")} if d.is_dir() else set()


def stamp_delta_seconds(dir_name: str, started_at: str) -> tuple[float, str] | None:
    """Closest distance between the directory-name stamp and `started_at`, in either basis.

    Returns None when the directory name carries no stamp - which is a fact about the
    name, not a pass.
    """
    mo = _STAMP_RE.search(dir_name)
    if not mo:
        return None
    try:
        started = dt.datetime.fromisoformat(started_at)
    except (TypeError, ValueError):
        return None
    if started.tzinfo is None:
        started = started.replace(tzinfo=dt.timezone.utc)
    naive = dt.datetime.fromisoformat(
        f"{mo.group(1)}T{mo.group(2)}:{mo.group(3)}:{mo.group(4)}")
    local = dt.timezone(dt.timedelta(hours=LOCAL_UTC_OFFSET_HOURS))
    options = {"utc": naive.replace(tzinfo=dt.timezone.utc),
               "local": naive.replace(tzinfo=local)}
    best = min(options, key=lambda k: abs((started - options[k]).total_seconds()))
    return (started - options[best]).total_seconds(), best


# --------------------------------------------------------------------------- the audit

@dataclass(frozen=True)
class Issue:
    code: str
    detail: str
    level: str  # error | warn | skip

    @property
    def key(self) -> str:
        return f"{self.code}:{self.detail}"


@dataclass
class RunAudit:
    run_dir: Path
    issues: list[Issue] = field(default_factory=list)
    marker: dict | None = None
    severity: str = "ok"
    rel: str | None = None

    @property
    def name(self) -> str:
        """How the audit report names this directory.

        The path RELATIVE to the swept root when it is known, so a nested run is
        distinguishable from a top-level one of the same name and the line says where it
        was read from (rule 12). The bare name is still what `run_dir` in a manifest is
        compared against - a manifest records its own directory's basename, not a path.
        """
        return self.rel or self.run_dir.name


def is_run_directory(d: Path) -> bool:
    return d.is_dir() and (
        (d / "trials").is_dir() or any(d.glob("suite*.json")))


#: Directories written by a building agent or a toolchain rather than by a harness. Not
#: descended into. Same list as `tools/census.py::NOT_A_RUN` and
#: `judge/tier1_census.py::NOT_A_RUN`, for the same reason and against the same tree.
NOT_A_RUN = frozenset({"work", "artifacts", "targets"})


def find_run_directories(runs_dir: Path) -> tuple[list[Path], list[Path]]:
    """(runs, pruned): every run directory under `runs_dir`, at ANY depth.

    `runs_dir` is not a flat list of runs. `archive-run1-byte-identical-prompts/` wraps
    four of them one level deeper, and an `iterdir()` sweep examined none of the four
    while printing the same word for the 19 it did examine (#126, task 75). A run that
    was never looked at and a run that measures clean are indistinguishable in the
    output, which is the shape this project keeps paying for.

    The walk stops descending as soon as it identifies a run: a run's own `work/`,
    `artifacts/` and `targets/` trees are agent-authored, can be enormous (one stored
    Unity tree alone holds tens of thousands of directories) and hold nothing this audit
    is asking about. `pruned` is returned rather than discarded, because a skip nobody
    counts is the defect being replaced.
    """
    runs: list[Path] = []
    pruned: list[Path] = []
    stack = [Path(runs_dir)]
    while stack:
        d = stack.pop()
        try:
            children = sorted(p for p in d.iterdir() if p.is_dir())
        except OSError:
            continue
        for c in children:
            if c.name in NOT_A_RUN or c.name.startswith("."):
                pruned.append(c)
            elif is_run_directory(c):
                runs.append(c)          # a run's own subtree is not searched further
            else:
                stack.append(c)
    runs.sort()
    return runs, pruned


def audit_run(run_dir: Path) -> RunAudit:
    run_dir = Path(run_dir)
    a = RunAudit(run_dir=run_dir)
    present = present_trial_ids(run_dir)
    manifests = read_manifests(run_dir)
    canonical = next((m for p, m in manifests if p.name == CANONICAL), None)

    if canonical is None:
        if present:
            a.issues.append(Issue(
                "NO_MANIFEST", f"reports={len(present)} manifests=0", "error"))
        return _finish(a)

    if not all(k in canonical for k in WHOLEGAME_KEYS):
        a.issues.append(Issue(
            "LEGACY_SHAPE",
            "keys=" + ",".join(sorted(canonical)) + " (pre-wholegame manifest, "
            "no declared matrix to compare against)", "skip"))
        return _finish(a)

    # --- 1. does the manifest describe the reports beside it?
    declared = declared_trial_ids(canonical)
    if declared is None:
        a.issues.append(Issue("UNPARSEABLE_MATRIX",
                              f"stacks/games/trials not usable: "
                              f"{canonical.get('stacks')!r} {canonical.get('games')!r} "
                              f"{canonical.get('trials')!r}", "error"))
    else:
        unexpected = present - declared
        missing = declared - present
        if unexpected:
            dead = sorted({g for g in canonical["games"]
                           if not any(t.startswith(f"{g}__") for t in present)})
            a.issues.append(Issue(
                "MISMATCH",
                f"declared={len(declared)} present={len(present)} "
                f"unexpected={len(unexpected)} missing={len(missing)} "
                f"declared_games_with_no_reports={','.join(dead) or 'none'}",
                "error"))
        elif not present:
            a.issues.append(Issue(
                "NO_REPORTS", f"declared={len(declared)} present=0", "warn"))
        elif missing:
            a.issues.append(Issue(
                "INCOMPLETE",
                f"declared={len(declared)} present={len(present)} "
                f"missing={len(missing)}", "error"))

    # --- 2. does the manifest belong to the directory it sits in?
    #
    # BOTH tests run, never one instead of the other. `run_dir` is exact and needs no
    # timezone reasoning, but it is only present from schema 2 onward, and a check that
    # switched to it would be WEAKER on new data than on old - a schema-2 manifest sitting
    # in the right directory with a started_at from another day would sail through. The
    # stamp test costs nothing and covers the whole corpus.
    own = canonical.get("run_dir")
    if own is not None and own != run_dir.name:
        a.issues.append(Issue(
            "MISPLACED", f"manifest.run_dir={own} directory={run_dir.name}", "error"))

    d = stamp_delta_seconds(run_dir.name, canonical.get("started_at"))
    if d is None:
        if own is None:
            a.issues.append(Issue(
                "UNSTAMPED",
                f"directory name carries no timestamp and the manifest has no run_dir "
                f"field (schema {canonical.get('manifest_schema', 1)}) - cannot be "
                f"placed", "warn"))
    else:
        delta, basis = d
        if abs(delta) > STAMP_TOLERANCE_S:
            a.issues.append(Issue(
                "STAMP_DRIFT",
                f"started_at is {int(delta)}s from the directory-name stamp "
                f"(closest basis {basis}, tolerance {STAMP_TOLERANCE_S}s)", "error"))

    # --- extra manifests are informational: they are what the repair writes.
    extras = [p.name for p, _ in manifests if p.name != CANONICAL]
    if extras:
        a.issues.append(Issue("SIBLING_MANIFESTS", ",".join(extras), "skip"))

    return _finish(a)


def _finish(a: RunAudit) -> RunAudit:
    marker = read_json(a.run_dir / MARKER_NAME)
    live = {i.key for i in a.issues if i.level == "error"}
    if marker is not None:
        a.marker = marker
        acked = set(marker.get("acknowledges") or [])
        if acked == live and live:
            a.severity = "marked"
            return a
        gone = sorted(acked - live)
        new = sorted(live - acked)
        a.issues.append(Issue(
            "MARKER_STALE",
            f"{MARKER_NAME} acknowledges {len(acked)} issue(s); the directory now "
            f"measures {len(live)}. no_longer_present={gone or 'none'} "
            f"newly_present={new or 'none'}", "error"))
        a.severity = "error"
        return a
    levels = {i.level for i in a.issues}
    a.severity = ("error" if "error" in levels else
                  "warn" if "warn" in levels else
                  "skip" if "skip" in levels else "ok")
    return a


def audit_tree(runs_dir: Path) -> list[RunAudit]:
    audits, _ = audit_tree_with_skips(runs_dir)
    return audits


def audit_tree_with_skips(runs_dir: Path) -> tuple[list[RunAudit], list[Path]]:
    runs_dir = Path(runs_dir)
    found, pruned = find_run_directories(runs_dir)
    out = []
    for d in found:
        a = audit_run(d)
        a.rel = str(d.relative_to(runs_dir))
        out.append(a)
    return out, pruned


# --------------------------------------------------------------------------- marking

def reconstruct_from_reports(run_dir: Path) -> dict:
    """What the directory's own reports say it was, derived TODAY.

    This is an inference from `trials/*.json`, not a record written at run time, and the
    key names in the marker say so. It cannot recover `max_turns`, `max_budget_usd` or the
    model unless a trial record happens to carry them.
    """
    present = sorted(present_trial_ids(run_dir))
    games, stacks, idx = set(), set(), set()
    for tid in present:
        parts = tid.split("__")
        if len(parts) == 3:
            games.add(parts[0])
            stacks.add(parts[1])
            idx.add(parts[2])
    starts = []
    for p in sorted((Path(run_dir) / "trials").glob("*.json")):
        rec = read_json(p) or {}
        if rec.get("started_at"):
            starts.append(rec["started_at"])
    return {"games": sorted(games), "stacks": sorted(stacks),
            "trials_per_cell": len(idx), "report_count": len(present),
            "trial_ids": present,
            "earliest_trial_started_at": min(starts) if starts else None,
            "latest_trial_started_at": max(starts) if starts else None}


def write_marker(run_dir: Path, audit: RunAudit, *, why: str,
                 reconstructed: dict | None) -> Path:
    run_dir = Path(run_dir)
    has_canonical = (run_dir / CANONICAL).exists()
    state = ("does not describe the reports beside it" if has_canonical
             else "is ABSENT, and reports are present without one")
    doc = {
        "kind": "manifest-defect",
        "NOTE": (f"This directory's canonical {CANONICAL} {state}. NOTHING here has been "
                 f"repaired: {CANONICAL} is left exactly as it was found - or left "
                 f"absent - because a manifest reconstructed after the fact is not the "
                 f"record that was written at run time, and a file under a suite*.json "
                 f"name reads like one. Any value under a reconstructed_* key was "
                 f"DERIVED from trials/*.json on written_at, not read from a manifest."),
        "written_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "written_by": "eval/tools/manifest.py mark",
        "run_dir": run_dir.name,
        "why": why,
        "canonical_manifest_present": has_canonical,
        "canonical_manifest_is_wrong": has_canonical,
        "canonical_manifest_left_unmodified": True,
        "acknowledges": sorted(i.key for i in audit.issues if i.level == "error"),
        "rescued_originals": sorted(
            p.name for p in run_dir.iterdir()
            if p.is_file() and p.suffix == ".json"
            and p.name not in (CANONICAL, MARKER_NAME)),
        "reconstructed_configuration": reconstructed,
        "reconstruction_provenance": (
            None if reconstructed is None else
            "derived from trials/*.json by eval/tools/manifest.py at written_at; "
            "an inference, not a contemporaneous record"),
    }
    path = run_dir / MARKER_NAME
    _atomic_write(path, doc)
    return path


# --------------------------------------------------------------------------- CLI

def default_runs_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "runs"


def _print_audit(a: RunAudit) -> None:
    tag = {"ok": "ok    ", "warn": "warn  ", "skip": "skip  ",
           "marked": "marked", "error": "ERROR "}[a.severity]
    print(f"{tag}  {a.name}")
    for i in a.issues:
        print(f"          {i.code}: {i.detail}")
    if a.severity == "marked":
        print(f"          (acknowledged by {MARKER_NAME}: "
              f"{a.marker.get('why', '')[:80]})")


def cmd_audit(a: argparse.Namespace) -> int:
    runs = Path(a.runs_dir).resolve()
    # AGENTS.md rule 12: the address is an input to the check. A sweep that examined
    # nothing must not print the same word as a sweep that found nothing wrong.
    print(f"runs-dir: {runs}")
    if not runs.is_dir():
        print("REFUSING TO REPORT: that path is not a directory. Examined 0 run "
              "directories - this is not a pass.")
        return 2
    audits, pruned = audit_tree_with_skips(runs)
    if not audits:
        print("REFUSING TO REPORT: 0 run directories under that path. A sweep over "
              "nothing is not a pass.")
        return 2

    if a.json:
        print(json.dumps([{"run": x.name, "severity": x.severity,
                           "issues": [{"code": i.code, "detail": i.detail,
                                       "level": i.level} for i in x.issues]}
                          for x in audits], indent=2))
    else:
        for x in audits:
            _print_audit(x)

    counts: dict[str, int] = {}
    for x in audits:
        counts[x.severity] = counts.get(x.severity, 0) + 1
    nested = sum(1 for x in audits if "/" in x.name)
    print(f"\nexamined {len(audits)} run directories ({nested} of them nested below "
          f"the top level; {len(pruned)} agent-authored directories not descended "
          f"into): " + ", ".join(f"{k}={v}" for k, v in sorted(counts.items())))
    bad = [x.name for x in audits if x.severity == "error"]
    if bad:
        print(f"manifests that do not describe their directory: {', '.join(bad)}")
        return 1
    return 0


def cmd_mark(a: argparse.Namespace) -> int:
    run = Path(a.run_dir).resolve()
    if not run.is_dir():
        print(f"no such run directory: {run}")
        return 2
    live = audit_run(run)
    errors = [i for i in live.issues if i.level == "error" and i.code != "MARKER_STALE"]
    if not errors:
        print(f"{run.name} measures clean - refusing to mark a directory that has "
              f"nothing wrong with it.")
        return 2
    # Re-measure from a marker-free view so the stored acknowledgement is the real
    # issue list rather than one contaminated by an earlier marker.
    marker_path = run / MARKER_NAME
    if marker_path.exists():
        marker_path.unlink()
        live = audit_run(run)
    rec = reconstruct_from_reports(run) if a.reconstruct else None
    p = write_marker(run, live, why=a.why, reconstructed=rec)
    print(f"wrote {p}")
    for i in live.issues:
        print(f"  acknowledged {i.code}: {i.detail}" if i.level == "error"
              else f"  (informational {i.code})")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("audit", help="check every stored run's manifest against its reports")
    p.add_argument("--runs-dir", default=str(default_runs_dir()))
    p.add_argument("--json", action="store_true")
    p.set_defaults(fn=cmd_audit)

    p = sub.add_parser("mark", help="record a known-bad manifest WITHOUT repairing it")
    p.add_argument("run_dir")
    p.add_argument("--why", required=True)
    p.add_argument("--reconstruct", action="store_true",
                   help="also store what the reports say the run was, labelled as an "
                        "inference made today")
    p.set_defaults(fn=cmd_mark)

    a = ap.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
