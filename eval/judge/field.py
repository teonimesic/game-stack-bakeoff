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
import re
import shutil
import statistics
import subprocess
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from anonymise import neutralise  # noqa: E402
from aspects import ASPECTS, Aspect, applicability, task_class  # noqa: E402

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


# ---------------------------------------------------------------------------
# BLINDING THE EXTENSIONS A FILE MENTIONS, NOT ONLY THE ONE IT IS STORED UNDER
# ---------------------------------------------------------------------------
# `blind_language` renamed every file in the pack to `.src` and stopped there, so it
# hid the extension of the file the judge was READING and nothing hid the extensions
# that file MENTIONED (#137). Measured over all 84 stored packs after `neutralise`:
# 1,876 occurrences of `.ts`/`.gd`/`.rs`/`.cs` across 76 of them, 2,083 over the whole
# vocabulary below across all 84 - `import { f32 } from "./vec2.ts"`,
# `tests/render_test.gd builds and positions this entire scene`. A judge that opens
# `sim/01.src` and reads that its sibling is `sim/tuning.gd` is not blind.
#
# WHY THIS IS HERE AND NOT IN `anonymise.neutralise`. `neutralise` runs for EVERY
# aspect. `idiomatic` is asked whether Rust was written like Rust and legitimately
# keeps its extensions; only `architecture` is judged with `blind_language=True`. A
# repair in the shared path would blind the aspect that must not be blinded.
#
# MEMBERSHIP IS DECIDED BY TWO QUESTIONS, BOTH ANSWERED FROM EVIDENCE RATHER THAN
# FROM A LIST OF THE SPELLINGS SOMEBODY HAPPENED TO SEE:
#
#   1. Does the suffix name a language, a shader dialect, or an authored file format
#      that belongs to fewer than all four arms? `blind_ext_selftest.py` derives that
#      set from the four starters and fails on any arm-exclusive suffix that is
#      neither listed here nor excluded by name below, so the next arm-exclusive
#      format is a red test rather than a leak nobody looked for.
#   2. Can the same token be a MEMBER NAME in one of those languages? An extension
#      that fails this is excluded and its collision count recorded - see
#      `_NOT_AN_EXTENSION`. This half cannot be answered from a starter tree; it was
#      measured against the 84 stored packs, and it is what stops `Mutex::lock()`
#      becoming `Mutex::src()`.
#
# Suffixes shared by every arm - `.json`, `.md`, `.png`, `.txt`, `.yaml`, `.sh` -
# are deliberately absent: they identify nothing, and rewriting them would corrupt
# text the judge reads for a different reason while blinding nobody.
BLIND_EXT: frozenset[str] = frozenset({
    # Source languages.
    "rs", "ts", "tsx", "mts", "cts", "js", "mjs", "cjs", "jsx", "cs", "gd",
    # Shader dialects, each owned by one arm's renderer.
    "shader", "gdshader", "wgsl", "hlsl", "cginc",
    # Authored formats only one engine can open.
    "tscn", "tres", "godot", "uid", "import", "gdextension",
    "meta", "asmdef", "prefab", "unity", "asset", "inputactions", "unitypackage",
    "csproj", "sln", "globalconfig",
    # Toolchain manifests and entry documents that exist in one arm only.
    "toml", "html",
})

#: Suffixes that ARE arm-exclusive and are still not rewritten, each with the reason
#: and the count that decided it. Measured over the 84 stored judge packs; the
#: selftest asserts every arm-exclusive starter suffix is in one set or the other, so
#: this list is the place an exclusion has to be argued rather than assumed.
_NOT_AN_EXTENSION: dict[str, str] = {
    "lock": "113 occurrences, 108 of them `Mutex::lock()` and 5 an `enemy.lock` "
            "field; 0 are filenames",
    "anim": "128 occurrences, every one a member access (`player.anim`); 0 filenames",
    "res": "1 occurrence, a method call (`AudioBank.res(path)`)",
    "mat": "a plausible member name (`renderer.mat`) with 0 filename occurrences, so "
           "listing it would buy nothing and risk a false rewrite",
    "controller": "same shape as `mat` - `player.controller`",
    "settings": "same shape as `mat` - `game.settings`",
    "dll": "build output. Never authored, never packed, never mentioned in the corpus",
    "pdb": "build output, as `dll`",
}

#: Dotted constructs that are spelled exactly like `stem.extension` and are not paths.
#: `import.meta` is ESM's namespace object: 83 of the 87 `.meta` occurrences in the
#: stored corpus are `import.meta.url`. The trailing-dot guard in the pattern already
#: spares those; this spares a bare `import.meta` as well.
_NOT_A_PATH = ("import.meta",)

_BLIND_EXT_RE = re.compile(
    r"\.(" + "|".join(sorted(BLIND_EXT, key=len, reverse=True)) + r")"
    # The extension ends here: `.ts` must not fire inside `.tsx`, `.tsconfig`.
    r"(?![A-Za-z0-9_])"
    # ... and is not a method call. `Mutex::lock()` is why `lock` is excluded outright,
    # but the guard is cheap and protects every future entry the same way.
    #
    # THE `\s*` THAT USED TO BE HERE WAS A FALSE NEGATIVE, and only a real pack found
    # it: `// Usage: node tools/audio-manifest.mjs   (or: just audio-manifest)` is a
    # filename followed by three spaces and a parenthesis, and the guard read it as a
    # call. No fixture produced that shape. A call has no gap before its parenthesis in
    # any of the four languages here; prose after a filename usually does.
    r"(?!\()",
    re.IGNORECASE)

#: `Grid.cs.meta` is one file with two suffixes, and both name the arm. Rewriting each
#: gives `Grid.src.src`, which advertises that a substitution happened - the half-
#: substitution shape `_STACK_NAMES` was reordered to avoid. Consecutive neutral
#: suffixes collapse to one.
_COLLAPSE_RE = re.compile(r"(?:" + re.escape(NEUTRAL_EXT) + r"){2,}", re.IGNORECASE)


def blind_extensions(text: str) -> str:
    """Rewrite language-naming file extensions to `NEUTRAL_EXT`. Blind aspects only.

    THE DECISION THE REGEX MUST NOT BE LEFT TO MAKE: what happens to an extension
    inside a string literal, an import specifier, or a data file?

    **It is rewritten, exactly as one in a comment is.** The rewrite is uniform and
    makes no attempt to tell a comment from a string literal from a JSON value, for
    two reasons:

    1. Telling them apart means lexing the language, and not knowing the language is
       the entire point of `blind_language`.
    2. A leak in a string literal is a leak. `load("res://scenes/main.tscn")` names
       the arm every bit as loudly as a comment does, and `import "./vec2.ts"` names
       it twice.

    The cost is that a blind pack contains code that could not run: its module
    specifiers point at files that do not exist under those names. **That was already
    true of every file in the pack before this function existed** - `build_pack`
    renames each one to `.src` on disk - so the change makes the pack internally
    CONSISTENT rather than newly broken. The one aspect this applies to is asked about
    structure, not about whether the tree builds. Aspects that read code as code
    (`idiomatic`) are not `blind_language` and their packs are byte-unchanged, which
    `blind_ext_selftest.py` asserts as a variant rather than a comment.
    """
    holes: list[tuple[int, int]] = []
    for lit in _NOT_A_PATH:
        start = 0
        while (i := text.find(lit, start)) != -1:
            holes.append((i, i + len(lit)))
            start = i + 1

    def repl(m: re.Match[str]) -> str:
        if any(s <= m.start() < e for s, e in holes):
            return m.group(0)
        return NEUTRAL_EXT

    return _COLLAPSE_RE.sub(NEUTRAL_EXT, _BLIND_EXT_RE.sub(repl, text))


# ---------------------------------------------------------------------------
# THE DIRECTORY NAMES `CHANGED.txt` CARRIES - BLINDED THROUGH THE MANIFEST,
# NOT THROUGH A VOCABULARY
# ---------------------------------------------------------------------------
# `blind_extensions` closed the SUFFIX half of this leak. The SEGMENT half survived
# it: measured over the 8 stored `architecture` packs after `neutralise` AND after
# `blind_extensions`, 1,561 arm-naming tokens remained. PARTITIONING THAT TOTAL IS
# WHAT DECIDED THE REPAIR, because the two channels are not the same defect:
#
#   channel        a real path segment    the same word doing something else
#   CHANGED.txt                   182                                       0
#   code content                  149                                   1,230
#
# `CHANGED.txt` is 100% signal because THE HARNESS WROTE IT: a whole `git diff
# --stat`, one true authored path per row, handed to a judge whose every file was
# renamed to `bucket/NN.src`. The code half is 89% collision - 1,129 of the 1,148
# `public` hits are the C# access modifier, 16 of 17 `ProjectSettings` are
# `ProjectSettings.globalize_path()`, and `Assets` is a Bevy type in Rust packs.
#
# THE CODE HALF IS NOT REPAIRED, and four candidate rewrites were measured before
# that was settled. Every one hands the judge the arm partition: over the 9
# independent stored fields, a strict threshold on a single pack's redaction count
# isolates an arm in 6 of 9 fields for the arm-exclusive vocabulary and in 9 of 9 for
# each vocabulary-free alternative, against 7.1% by chance. The census is part 6 of
# `blind_dir_selftest.py` and re-runs with `--runs-root`; the reasoning and the
# reversal condition are in `DECISIONS.md`, and `tasks/103` holds the working.
#
# WHY THE MANIFEST AND NOT A REWRITE. Every row of `--stat` is a real path, and the
# pack already knows what each of those paths became: `pack.manifest` in
# `eval/report.json` is an origin -> label table the packer itself wrote. Mapping
# through it needs no vocabulary, so it cannot fire on a word that merely looks like a
# directory and cannot miss a directory nobody thought of - the two failure modes a
# `BLIND_DIR` list would have had. It also turns `CHANGED.txt` from a contradiction of
# the judge's brief into support for it: the brief says "cite files by the path they
# have HERE", and until now the one file in the pack that named the real paths was the
# one the harness added.
#
# WHAT HAPPENS TO A ROW THAT DOES NOT MAP. It is omitted, and the header says so. 228
# of the 424 rows in the run these packs came from name files that are not in the pack
# at all - `AGENTS.md`, `Cargo.lock`, `Assets/Audio/clear.wav.meta` - so the judge
# could not open them under any name. Their COUNT is not reported either, and that is
# the deliberate part: unmapped rows run 53 and 43 for the two Unity submissions
# against 15 and 15 for the two TypeScript ones, so any count of them hands over a
# partition of the field that nobody chose to measure (#62). The `--stat` summary tail
# (` 37 files changed, ...`) is dropped for that reason and no other.
#
# THE COUNTS ARE STILL RECORDED, beside the pack rather than inside it, as
# `changed_rows` and `changed_rows_dropped` in the evidence counts. Omitting rows is a
# reason not to show something, and every reason not to count a failure is a channel a
# bug can widen (rule 7): a manifest that stopped matching would silently empty this
# file and nothing would look different, so `build_pack` REFUSES when a submission
# with a non-empty manifest and a non-empty diff maps zero rows.

#: A `git diff --stat` body row. The summary tail carries no `|` and does not match.
_STAT_ROW = re.compile(r"^\s*(?P<path>.*?)\s*\|(?P<churn>.*)$")

#: git compresses a rename into one row: `Assets/View/{Flat.meta => Glow.meta}`. One
#: occurrence in the whole stored corpus, and it names TWO real paths, either of which
#: may be the one the manifest lists.
_STAT_RENAME = re.compile(r"\{(?P<before>[^{}]*?) => (?P<after>[^{}]*?)\}")


def _stat_paths(field: str) -> list[str]:
    """Every real path a `--stat` path field names, most-likely first."""
    m = _STAT_RENAME.search(field)
    if not m:
        return [field]
    return [(field[:m.start()] + m.group(g) + field[m.end():]).replace("//", "/")
            for g in ("after", "before")]


def blind_changed_txt(stat_text: str,
                      origin_to_label: dict[str, str]) -> tuple[str, int, int]:
    """Rewrite a `git diff --stat` into the pack's own vocabulary.

    Returns `(body, rows_kept, rows_dropped)`. A row survives only when its path is an
    origin the manifest maps to a label, so every surviving row names a file the judge
    can actually open - which is the property `pack_matches_manifest` protects for the
    directory and this protects for the harness's own commentary on it.
    """
    kept: list[str] = []
    dropped = 0
    for line in stat_text.splitlines():
        m = _STAT_ROW.match(line)
        if not m or not m.group("path"):
            continue
        label = next((origin_to_label[c] for c in _stat_paths(m.group("path"))
                      if c in origin_to_label), None)
        if label is None:
            dropped += 1
            continue
        kept.append(f" {label:<30} |{m.group('churn')}")
    return "\n".join(kept) + ("\n" if kept else ""), len(kept), dropped


def _pack_origins(sub: Path) -> dict[str, str]:
    """The submission's own origin -> label table, from `pack.manifest`.

    Missing or unreadable returns `{}`. That is not a silent excuse: `build_pack`
    reaches this only after `pack_matches_manifest` has already refused a field whose
    packs have no manifest, and the caller's zero-mapped guard turns an empty table
    into a refusal rather than an empty `CHANGED.txt`.
    """
    rep = sub / "eval" / "report.json"
    if not rep.is_file():
        return {}
    try:
        manifest = (json.loads(rep.read_text()).get("pack") or {}).get("manifest")
    except (OSError, json.JSONDecodeError):
        return {}
    if not manifest:
        return {}
    return {e["origin"]: e["label"] for e in manifest
            if e.get("origin") and e.get("label")}


#: What `CHANGED.txt` says about itself, per blinding. The blind header must not name
#: a count of what it dropped; see the block above for why.
CHANGED_HEADER = ("Files this submission's author changed, and by how much.\n"
                  "Everything else is template code they inherited.\n\n")
CHANGED_HEADER_BLIND = (
    "Files this submission's author changed, and by how much.\n"
    "Everything else is template code they inherited.\n"
    "Paths are this pack's own labels, so every row names a file you can open.\n"
    "Rows for files that are not in this pack have been omitted.\n\n")


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

    # THE SCENE STATEMENT IS RESOLVED BEFORE ANY WORK, so a scene this module cannot state
    # costs nothing rather than producing a pack whose brief points at a missing file.
    statement = scene_statement(game) if task_class(game) == "scene" else ""

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

    # ONE function for every piece of text this pack writes, so a blind aspect cannot
    # be blinded on one channel and not another. `neutralise` runs for every aspect;
    # the extension rewrite runs only where `blind_language` is set, which is what
    # keeps `idiomatic`'s pack byte-identical (see `blind_extensions`).
    def _text(raw: str) -> str:
        out = neutralise(raw)
        return blind_extensions(out) if blind_language else out

    mapping: dict[str, str] = {}
    counts: dict[str, dict[str, int]] = {}
    for label, sub in zip(LABELS, order):
        mapping[label] = sub.name
        out = dest / label
        out.mkdir()
        n = {"code": 0, "frames": 0, "telemetry": 0, "audio": 0, "code_unreadable": 0}

        if "code" in need:
            src = sub / "eval" / "judge_pack" / "code"
            written: set[str] = set()
            for f in sorted(src.rglob("*")):
                if not f.is_file():
                    continue
                tgt = out / f.relative_to(src)
                if blind_language:
                    tgt = tgt.with_suffix(NEUTRAL_EXT)
                tgt.parent.mkdir(parents=True, exist_ok=True)
                try:
                    tgt.write_text(_text(f.read_text(errors="ignore")))
                # Narrow, and COUNTED. OSError is the real per-file failure here (an
                # over-long name, an unreadable mode); it drops one file from what the
                # judge is shown, and until 2026-08-23 it did so with nothing recorded
                # anywhere -- an unequal amount of each submission reaching the judge is
                # #62's shape. `code_unreadable` lands in the pack manifest beside
                # `code`. A blind catch also covered `neutralise` raising, which would
                # drop EVERY file and still report a built pack; that now crashes.
                except OSError:
                    n["code_unreadable"] += 1
                    continue
                n["code"] += 1
                written.add(str(tgt.relative_to(out)))
            # CHANGED.txt IS PACK CONTENT AND IT WAS THE DENSEST LEAK OF ALL (#137): it
            # is a whole `git diff --stat`, one true path per authored file, beside a
            # directory whose every file was renamed to `bucket/NN.src`. The eight
            # stored `architecture` packs carried 80 `.cs`, 78 `.gd`, 60 `.meta`, 43
            # `.ts` and 43 `.rs` in this file alone, and 182 arm-naming DIRECTORY
            # segments that `blind_extensions` does not touch.
            #
            # Per pack it is a clean PARTITION, not a smear - each names exactly one
            # arm's suffixes and no other arm's, which is a label rather than a hint.
            # In a whole unblinded field it is 345 of the 667 extension tokens against
            # 322 in all 199 code files put together: THE PACKER CONTRIBUTED MORE OF
            # THIS LEAK THAN THE SUBJECTS DID.
            #
            # Under `blind_language` the whole file is now rebuilt from the pack's own
            # origin -> label manifest rather than rewritten (see `blind_changed_txt`),
            # which repairs both properties at once - a manifest can neither fire on a
            # non-path nor miss an unlisted directory. `_text` still runs over the
            # result: the labels and churn columns are harness-generated and it is a
            # no-op on them, but "one function for every piece of text this pack
            # writes" is the invariant that stops a channel being blinded on one path
            # and not another.
            stat = sub / "diff.stat"
            if stat.is_file():
                raw = stat.read_text(errors="ignore")
                if blind_language:
                    origins = _pack_origins(sub)
                    # THE LABEL MUST NAME A FILE THAT IS ACTUALLY IN THE PACK. The
                    # manifest records the origin's REAL suffix (`sim/01.cs`) and this
                    # loop wrote `sim/01.src`, so the two vocabularies differ by
                    # exactly the rename above. Rather than re-deriving the rename here
                    # - a second copy of a rule, which is how #100 recurred - each
                    # candidate label is checked against what was written. A label that
                    # is not on disk is not a citation the judge can follow.
                    origins = {o: lbl for o, lbl in
                               ((o, str(Path(lbl).with_suffix(NEUTRAL_EXT)))
                                for o, lbl in origins.items())
                               if lbl in written}
                    body, kept, dropped = blind_changed_txt(raw, origins)
                    n["changed_rows"] = kept
                    n["changed_rows_dropped"] = dropped
                    # FAIL CLOSED. An empty CHANGED.txt is indistinguishable from a
                    # correct one that had nothing to say, and the way this breaks is
                    # silent: a manifest whose origins stop matching the diff's paths
                    # still parses, still maps, and maps nothing (rule 12 - the address
                    # is an input to the check).
                    if written and dropped and not kept:
                        raise RuntimeError(
                            f"{sub.name}: CHANGED.txt mapped 0 of {dropped} diff rows "
                            f"through a manifest of {len(origins)} label(s) against "
                            f"{len(written)} file(s) on disk. The manifest's origins "
                            f"and `diff.stat`'s paths no longer share a spelling, so "
                            f"the blind pack would carry an EMPTY CHANGED.txt that "
                            f"looks like a submission which changed nothing. Re-pack "
                            f"the run rather than judging it.")
                else:
                    body = raw
                (out / "CHANGED.txt").write_text(
                    (CHANGED_HEADER_BLIND if blind_language else CHANGED_HEADER)
                    + _text(body))

        if "frames" in need:
            fdir = out / "frames"
            fdir.mkdir(exist_ok=True)
            for f in sorted((sub / "eval" / "frames").glob("*.png")):
                shutil.copy(f, fdir / f.name)
                n["frames"] += 1
            # Geometry per LABEL, not per submission id: the brief is blind, so the judge
            # is told "C is 420x640", never which stack C is. This leaks nothing it does
            # not already have - the size is visible in the PNGs it is about to open.
            # The import is OUTSIDE the try on purpose: a blind catch around it turned
            # "the judge's own PNG reader is broken" -- which blanks the geometry for
            # EVERY submission at once -- into the same silence as one odd frame in one
            # submission. Only the per-file read is allowed to fail quietly.
            import png as _png
            try:
                _f0 = sorted(fdir.glob("*.png"))
                if _f0:
                    _im = _png.read(_f0[0])
                    geometry[label] = f"{_im.width}x{_im.height}"
            # Narrow: an unreadable or non-baseline PNG (PngError) or an IO failure.
            # Geometry is a LABEL in the brief, not a score, so its absence costs the
            # judge one sentence about one submission.
            except (_png.PngError, OSError):  # noqa: S110 — see above; nothing to log
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
    # The completeness claim inside it is a FACT ABOUT THIS PACK, so it is passed in
    # rather than baked into a constant (#69 drift; `COMPLETENESS_NOTE`).
    skill.write_text(pack_skill(knowingly_truncated))

    # THE SCENE STATEMENT, for a scene field and for nothing else. A game pack must not
    # carry one: it would state a task nobody set, and `fidelity` is not asked of a game.
    #
    # Written RAW, like the skill above and unlike everything the submissions contributed.
    # `_text` exists so a blind aspect cannot be blinded on one channel and not another,
    # and this channel is not blinded by rewriting - it is blinded by being written that
    # way and gated by `verify_blind.py --packs`, which reads what is on disk. Passing it
    # through `neutralise` would launder a stack name out of harness-authored text and
    # leave the gate unable to see the leak it exists to catch.
    if statement:
        # UTF-8 BY CONTRACT, on the write and on the read in `run_field`. `write_text`
        # and `read_text` default to the LOCALE encoding, so a packer and a judge host
        # on different code pages would disagree about what the statement says while
        # every check here stayed green - and the invalid-byte refusal below would
        # decode instead of refusing (rule 12: the address is an input, and so is the
        # codec).
        (dest / SCENE_STATEMENT_FILE).write_text(statement, encoding="utf-8")

    leaked = sorted(q.name for q in dest.rglob("*")
                    if q.is_file() and "MAPPING" in q.name)
    if leaked:
        raise RuntimeError(f"identity mapping left inside the pack: {leaked}")
    return {"game": game, "order_seed": order_seed, "sees": sees,
            "mapping": mapping, "evidence_counts": counts,
            "capture_geometry": geometry,
            "knowingly_truncated": knowingly_truncated}


#: WHAT THE JUDGE IS TOLD ABOUT HOW MUCH OF EACH SUBMISSION IT IS SEEING, and it is a
#: FUNCTION OF THE PACK rather than a sentence.
#:
#: This claim lived inside `EVIDENCE_BLURB["code"]` as a constant, and on 2026-08-22 the
#: character budget it described was removed (#69). The constant went on telling every
#: code judge that its evidence "may not contain every file the author wrote" for a pack
#: in which `files_dropped_for_length` is 0 by construction - and the direction is the
#: damaging one: it invites a judge to discount an absence it is seeing in full, the
#: opposite of the caution the sentence was written to induce. All 10 stored code rounds
#: that recorded a `brief_sha256` rebuild byte-identically to that text (`eval/RUNS.md`).
#:
#: Both states are kept because `--allow-truncated` still exists for the capped-vs-uncapped
#: control, and a pack built that way IS incomplete. Keeping one wording and dropping the
#: other is what turned this into a constant the first time: **a claim with only one
#: possible value is not a claim, it is a decoration**, and nothing can check it.
#:
#: `judge/blurb_selftest.py` asserts that the note a pack carries is the note for the state
#: the pack is measurably in, in both directions, and that the complete-state wording
#: contains no truncation caution at all.
COMPLETENESS_NOTE = {
    False: ("**This pack is complete.** Every file this submission's author wrote that "
            "the packer can show you is here, so a concern you cannot find in the code "
            "is evidence about the submission and not a limit on what you were shown."),
    True: ("**This pack is deliberately truncated** - it was built under an explicit "
           "size cap, for a controlled comparison - so it may hold only part of what "
           "this author wrote. Judge what is here, and do not infer that an absent "
           "concern was neglected."),
}

#: HOW THE BRIEF SHOWS A PACK PATH, and it depends on the aspect.
#:
#: Under `blind_language` every file in the pack is renamed to `.src`, so `sim/03.src` is
#: a path the judge can really open. Under a non-blind aspect - `idiomatic`, which cannot
#: be asked whether a language reads like itself with its suffixes removed - the labels
#: keep their REAL suffixes, and the eight submissions in one field carry four different
#: ones. The brief is a single document for the whole field, so an example ending in any
#: real suffix would either name an arm or name a file no judge has. Show the shape and
#: let the pack supply the suffix.
PACK_PATH_EXAMPLE = {
    True: "`sim/03.src`, `view/02.src`",
    False: "`sim/03`, `view/02` -- with whatever suffix they carry here",
}

#: WHO IS WATCHING, in the frames blurb, and it depends on the TASK CLASS.
#:
#: A scene has no player (`eval/SCENES.md`), so "everything the player sees" is a claim
#: about a task nobody set - the same shape as the completeness note describing a cap that
#: no longer exists. Keyed rather than rewritten in place, so the game wording stays one
#: string and every stored game round still rebuilds byte-identically.
FRAMES_AUDIENCE = {
    "game": "Everything the player sees",
    "scene": "Everything the scene shows",
}

EVIDENCE_BLURB = {
    "code": ("`CHANGED.txt` names the files this submission's author actually wrote; "
             "everything else is template code they inherited. The source tree is "
             "beside it. **Cite files by the path "
             "they have HERE** -- {pack_path_example}"
             " -- and never by a name you infer from their contents. The "
             "filenames have been rewritten; a citation to the original name cannot be "
             "checked by anyone, and unverifiable evidence is discarded. MEASURED: 11 "
             "of 16 claims in one field cited a reconstructed name, and every single "
             "one of them turned out to describe something really in the pack."),
    "frames": ("`frames/` holds PNGs sampled evenly across one real run of this "
               "submission -- the first is the opening state, the last is late in the "
               "run. {frames_audience} is in these pixels; there is no "
               "second display."),
    "telemetry": ("`telemetry.json` is measured from a real driven run of this "
                  "submission: event counts, intervals, how long the run went quiet. "
                  "These are facts about the run, not estimates."),
    "audio": ("`audio.json` describes the sound this submission ships, measured by "
              "decoding every file: duration, RMS, peak, and which clips are the same "
              "sound as each other. You cannot listen to them."),
}


#: THE FILE A SCENE PACK CARRIES SAYING WHAT THE SCENE WAS, and its name in the pack.
#:
#: `fidelity` asks "does this read as the scene it was asked for", and until this existed
#: the pack carried nothing that said what was asked for. The rendered scene prompt is not
#: a candidate: it exists PER STACK, and handing a judge one names the arm in the evidence
#: -- measured over the 8 rendered scene prompts, `anonymise.find_stack_names` returns a
#: stack token in every one of them. So the statement is written by hand, once per scene,
#: and is the same text for all 8 submissions.
SCENE_STATEMENT_FILE = "SCENE.md"

#: The header, shared by every scene, and the two things it has to say.
#:
#: WHAT IT IS: the task, not any submission's answer to it. A judge that reads this as a
#: description of a good submission will mark down a field for lacking what nobody asked
#: for.
#:
#: WHAT IT IS NOT: a channel that separates the arms. It is one file, byte-identical in
#: every pack built for this scene, so it carries no information about which submission is
#: which -- and saying so is what stops a judge mining it for one.
SCENE_STATEMENT_HEADER = """# The scene these submissions were asked to build

Every submission in this field was set the same scene, and this is that scene stated
plainly. Nothing in it names the technology any of them was built with, and it is the
same text in every pack, so it tells you nothing about which submission is which.

**This is what was ASKED FOR, not what anything here achieved.** It is the standard to
read your evidence against. An element it describes that NO submission shows is a finding
about the whole field and belongs in `field_note`; an element it does not describe is
not something to look for.

Part of what it describes may not be decidable from the evidence you were given. Where it
is not, say so rather than counting it against a submission.

The craft was asked for as well as the content: the quality of the light, the materials,
the way things ease into and out of motion, the small details that sell the moment. Every
submission was told to push as far as it could on all of that, and how any of it was
achieved was left entirely open.

"""

#: EACH SCENE, STATED WITHOUT NAMING A STACK. Keys must be `scene_prompts.SCENES`.
#:
#: SOURCE. `eval/SCENES.md` is the authority for what a scene is, and this is written from
#: its scene sections -- not from a rendered prompt, which would be laundering an output of
#: it and could carry a vocabulary dict's words out with it. The element list is what the
#: scene asks for; a statement that asks for MORE than the prompt did would have `fidelity`
#: penalise a field for missing something nobody set, which is worse than the narrowing it
#: replaces.
#:
#: WHAT MAY NOT BE IN HERE, and it is the same rule that governs a prompt. `SCENES.md`
#: states what each criterion catches and none of that may reach a judge: a tier-3 opinion
#: told what tier 2 measures is a restatement of tier 2, not a second reading. The two
#: sharpest omissions are the ones the scenes exist for and they look like oversights --
#: s1 does not say the layers scroll at rates ordered by depth, and s2 does not say the
#: water surface stays level while the glass tilts. `blurb_selftest.py` greps this text
#: with `tools/prompt_guard.py`'s own closed lists, which is the same grep the prompts get.
#:
#: NOT PUT THROUGH `neutralise`. Every other piece of pack text is, because it comes from a
#: submission and is not ours to write; this is ours, and a rewrite would launder a stack
#: name out of it and leave `verify_blind.py --packs` unable to see the leak it exists to
#: catch. Written raw, exactly as the pack skill is, and gated the same way.
SCENE_STATEMENTS = {
    "s1_parallax": """## A car on a road, seen from the side

A car drives from left to right along a road that never ends, while the light around it
goes from day to night. The run is a fixed length: the first frame is its opening moment
and the last is near its end.

- The car drives for the whole run. It never stops, it never leaves the frame, and its
  wheels turn as it goes.
- Behind it lies a world with real distance in it -- the sky, whatever is far away,
  whatever is nearer, and the ground the car is on. As the car travels, that world should
  read as genuinely deep rather than as a picture sliding past.
- That world is endless, and it is endless because it repeats. Someone watching the
  horizon should not be able to say the moment a repeat happened.
- Things pass between the camera and the car -- signs, poles, whatever suits the road --
  and while one is passing it covers part of the car.
- The light goes from day to night over a stretch of the run, and it goes there
  gradually: the scene passes through every shade between the two rather than switching
  from one to the other. Everything lit changes with it -- the sky, the ground, the car,
  and what the car itself casts.
- The run ends at night, and what a car at night looks like was asked to be worth the
  effort: headlights reaching down the road, the road surface picking them up, whatever
  the car's own lights do to the world beside it.
- The wheels, the dust or spray they throw up, whatever hangs in the air, and every other
  moving detail belong to the scene. Many small things each moving on their own read as
  alive; a handful of large ones do not.
- Where the scenery stands and what passes in front of the car are drawn from the run's
  seeded random source, so a different seed gives a visibly different run of the same
  scene.
""",
    "s2_glass": """## A glass of water that falls, breaks, and comes back together

A transparent glass, most of the way full of water, stands on a table. It empties, it
tips, it falls, it breaks -- and then the whole thing runs backwards until it is standing
full again. The run is a fixed length: the first frame is its opening moment and the last
is near its end.

The sequence, in order:

- **It empties.** Water leaves the glass a drop at a time and what is inside goes down.
  This is the long, slow part of the run, and it is where the glass gets its good look:
  what the light does passing through it, what it does to whatever is behind it, and what
  it throws onto the table around it.
- **It leans.** The glass tips further and further over, slowly enough to watch, and what
  it was throwing onto the table moves with it.
- **It falls.** It goes over the edge and drops, and this part is quick.
- **It breaks.** It comes apart into many small irregular pieces that fly, tumble and come
  to rest on the surface below. Each piece moves on its own and each is a different shape.
  The pieces are still glass: whatever the whole glass did to the light, its pieces do
  too.
- **It rests**, for a moment, so there is time to see what it has become.
- **It runs backwards.** Every part of the sequence plays in reverse, in order, until the
  glass is standing whole and full on the table exactly as it began. A true reversal, not
  a fade and not a cut.

The scene was also asked for:

- Something with a pattern to it standing behind the glass, in view of the camera and big
  enough to be seen past the glass on both sides, with enough going on that one part of it
  can be told from another.
- A camera placed so that the glass, the table it stands on, the surface it falls to and
  the thing behind it are all in frame for the whole run. It may move, and if it does it
  moves smoothly.
- Lighting as the scene's other subject. A single flat light on a transparent object
  wastes the scene.
- How the glass breaks -- how many pieces, what shape each is, where each one goes --
  drawn from the run's seeded random source, as is anything else that could vary, so a
  different seed gives a visibly different run of the same scene.
""",
}


def scene_statement(game: str) -> str:
    """The stack-neutral statement of one scene, as the pack carries it.

    RAISES for a scene this module cannot state, and that refusal is the point: a scene
    field packed without one would hand `fidelity` a brief pointing at a file that is not
    there, and the aspect would fall back to reading the subject out of the field -- the
    exact narrowing this text was written to remove, restored silently (rule 7).
    """
    body = SCENE_STATEMENTS.get(game)
    if not body:
        raise RuntimeError(
            f"{game}: no stack-neutral statement of this scene in "
            f"field.SCENE_STATEMENTS (which states {sorted(SCENE_STATEMENTS)}). A scene "
            f"pack must carry one -- `fidelity` is asked whether a strip reads as the "
            f"scene it was asked for, and without the statement there is nothing in the "
            f"pack saying what that was. Write it from eval/SCENES.md; do not pack a "
            f"rendered prompt, which exists per stack and names the arm.")
    return SCENE_STATEMENT_HEADER + body


#: A skill written INTO the pack, because the judge runs with `cwd=pack` and
#: `--setting-sources project`, so project settings resolve against the pack directory and
#: a skill in this repository's `.claude/skills/` is invisible to it.
#:
#: Three consequences follow and all three constrain what may be written here:
#:   1. it is EVIDENCE the judge sees, so it must not say anything that biases the verdict
#:      - it describes HOW to sample, never what to conclude or which traits are good;
#:   2. it must be BLIND-SAFE. No stack, engine, language or toolchain names. `verify_blind`
#:      scans it for stack tokens and for the rubric canary, and that is pinned;
#:   3. **it is judge-facing text that makes a claim about the packer**, which is the same
#:      resource `EVIDENCE_BLURB` is, and it had the same defect pointing the other way:
#:      it asserted completeness unconditionally, so a field built on purpose with
#:      `--allow-truncated` would have been handed a skill telling it nothing was removed
#:      for size while the brief said the opposite. Both texts now take the claim from
#:      `COMPLETENESS_NOTE`, so there is ONE sentence about pack completeness in this
#:      module and `blurb_selftest.py` reads it out of both.
#:
#: `{completeness}` and `{history}` are filled by `pack_skill()`; there are no other braces
#: in this template, and the selftest builds it through that function rather than by
#: formatting it here, so a brace added later cannot be filled by accident.
PACK_SKILL_TEMPLATE = """---
name: sampling-code
description: How to read a large submission pack without pretending to have read all of it. Use when a submission has more files than are worth opening, or when deciding what to open next.
---

# Sampling a submission

{completeness} Some submissions are large. You are
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

{history}
"""

#: The closing section, in each of the two states. The complete-state text narrates a
#: mechanism that was REMOVED, in the past tense; the truncated-state text describes one
#: that is acting. Splitting them is the point: the old single version ended "that is
#: fixed - you now get everything", which is simply false for a field packed under
#: `--allow-truncated`.
PACK_SKILL_HISTORY = {
    False: ("A pack used to be truncated to a fixed character budget, so files were "
            "dropped by where their path happened to sort and more than half of some "
            "submissions was never shown to any judge. That is fixed - you now get "
            "everything. The risk moved rather than disappearing: it is now possible to "
            "read a biased sample and not notice, because nothing stops you. Choosing "
            "the sample is your job, and reporting it is what makes the judgement "
            "auditable."),
    True: ("This field was packed under a size cap on purpose, so the sample you are "
           "reading was chosen partly by the packer and partly by you. Files were "
           "dropped by where their path happened to sort, which is not a property of "
           "the work. Say what you opened, and treat anything you cannot find as "
           "unseen rather than as absent."),
}


#: THE THIRD JUDGE-FACING TEXT, and the one nothing was looking at. It is not in the pack
#: at all - it is `claude -p`'s argument - so a check that walks the pack directory cannot
#: see it, and it asserted "The submissions are complete" unconditionally, exactly as the
#: pack skill did. Found while writing `blurb_selftest.py` against the RESOURCE (judge-facing
#: text that claims something about the packer) rather than against the two constants that
#: were known to be wrong.
#:
#: The subagent sentence is here on purpose and is not decoration: subagents are OFFERED,
#: not assumed, and were verified empirically under this exact flag set
#: (`--setting-sources project --strict-mcp-config`) by asking a probe run to spawn one
#: and reading the tool-use stream - `Agent` was really invoked. An instruction for a
#: capability that is not present is the `-disable-audio` failure in a new costume.
JUDGE_PROMPT = {
    False: ("Read BRIEF.md, then read the code in A/ through H/ and produce the "
            "comparative judgement it asks for. Read real files before scoring. "
            "The submissions are complete, so some are large: you may launch subagents "
            "with the Task tool to read parts of them in parallel and report back. "
            "Sample deliberately and say what you sampled."),
    True: ("Read BRIEF.md, then read the code in A/ through H/ and produce the "
           "comparative judgement it asks for. Read real files before scoring. "
           "BRIEF.md says how much of each submission you are being shown; believe it "
           "over any assumption that a pack is whole. Some submissions are large: you "
           "may launch subagents with the Task tool to read parts of them in parallel "
           "and report back. Sample deliberately and say what you sampled."),
}


def judge_prompt(knowingly_truncated: bool = False) -> str:
    """What the judge is asked to do, for the pack it is actually holding."""
    return JUDGE_PROMPT[bool(knowingly_truncated)]


def pack_skill(knowingly_truncated: bool = False) -> str:
    """The sampling skill for a pack in the state it is actually in.

    A FUNCTION rather than a constant because the claim it opens with is a fact about the
    pack, and a fact with one possible value is not checkable. See `COMPLETENESS_NOTE`.
    """
    kt = bool(knowingly_truncated)
    return PACK_SKILL_TEMPLATE.format(completeness=COMPLETENESS_NOTE[kt],
                                      history=PACK_SKILL_HISTORY[kt])


def _brief(aspect: Aspect, game: str, geometry: dict[str, str] | None = None,
           knowingly_truncated: bool = False) -> str:
    anchors = "\n".join(f"  {k} = {v}" for k, v in sorted(aspect.anchors.items()))
    # THE TASK CLASS, read once. A scene has no player and a game has no scene brief, so
    # 3 things in this document depend on it: what the field is said to implement, who is
    # said to be watching the frames, and whether `SCENE.md` is named.
    scene = task_class(game) == "scene"
    blurbs = []
    for k in aspect.sees.split("+"):
        if k not in EVIDENCE_BLURB:
            continue
        text = EVIDENCE_BLURB[k].replace(
            "{pack_path_example}", PACK_PATH_EXAMPLE[aspect.blind_language]).replace(
            "{frames_audience}", FRAMES_AUDIENCE["scene" if scene else "game"])
        # THE COMPLETENESS NOTE IS CODE-ONLY because the thing that was capped was the
        # code pack: `files_dropped_for_length` counts source files, and frames,
        # telemetry and audio were never filled against a character budget. Attaching it
        # to every bucket would state a fact about a mechanism that does not exist there.
        if k == "code":
            text = f"{text} {COMPLETENESS_NOTE[bool(knowingly_truncated)]}"
        blurbs.append(f"- {text}")
    # THE SCENE STATEMENT IS EVIDENCE and is named here, because a file in the pack that
    # the brief does not mention is a file the judge has no reason to open. It is keyed on
    # the TASK CLASS rather than on the aspect: `build_pack` writes it for every scene
    # pack, so every aspect asked of a scene has it, and no game brief may name it -- a
    # game pack does not carry one, and every stored game round rebuilds byte-identically.
    if scene:
        blurbs.append(
            f"- `{SCENE_STATEMENT_FILE}` states the scene every submission in this field "
            f"was asked to build. It is the same text in every pack and it names no "
            f"technology, so it tells you nothing about which submission is which. It "
            f"describes what was ASKED FOR, not what any of them achieved.")
    evidence = "\n".join(blurbs)
    # Do not tell a judge to read code when the pack holds only frames. A stale
    # instruction to open files that are not there burns turns and produces "I could
    # not find the source" as if it were a finding about the submission.
    looked_at = {"code": "Read the code", "frames": "Look at every frame",
                 "telemetry": "Read the telemetry", "audio": "Read the measurements"}
    closing = (" and ".join(looked_at[k] for k in aspect.sees.split("+")
                            if k in looked_at)
               + " before you score. You have the whole field; use it comparatively.")
    if scene:
        closing = f"Read `{SCENE_STATEMENT_FILE}` first. " + closing

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

Eight submissions, `A/` through `H/`. All eight implement the same {"scene" if scene else "game"} from the
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



def _provenance(aspect: Aspect, mapping: dict[str, Any], brief_text: str,
                statement_sha: str | None, max_turns: int, budget: float
                ) -> dict[str, Any]:
    """WHAT THIS ROUND ACTUALLY SAW, so the question is answerable from the record.

    A FUNCTION rather than a dict literal inside `run_field`, because everything else in
    that function's tail needs a model call to exist and this does not. A field recorded
    only on the far side of an 8-call spend is a field no offline check can assert;
    `blurb_selftest.py` drives this directly.

    Two fields were missing before this block existed and both mattered within days.
    `run` was absent, so a round named only its game - and `g2_tetris3d` is 4 stored
    fields in different states of repair. `files_opened` was absent until task 09 added it
    for an unrelated reason, and it is the only thing that bounded #83.

    The rescue that found the missing `run` worked by matching numbers quoted in `fun`'s
    prose against stored telemetry. **That was luck about one aspect's writing style**:
    `ux` or `idiomatic` quote no telemetry and would have been unresolvable. Prose is not
    a substitute for a field.

    So the test applied here is: if someone asks in a month what this round saw, which
    parts of the answer are gone? Everything below was in that category.
    """
    return {
        "sees": mapping.get("sees"),
        "blind_language": aspect.blind_language,
        # The BRIEF is not fixed. A geometry note was added to it on 2026-08-22, and
        # rounds either side of that saw different text - which is why task 08 had to
        # re-run seven repeats rather than top up four. Hashing it makes "same brief?"
        # a comparison instead of an argument.
        "brief_sha256": hashlib.sha256(brief_text.encode()).hexdigest()[:16],
        "brief_chars": len(brief_text),
        # THE SUBJECT A SCENE ROUND WAS SCORED AGAINST, and the brief hash cannot
        # stand in for it: the brief NAMES `SCENE.md` and does not contain it, so
        # two rounds with the same `brief_sha256` can have been read against two
        # different statements. `None` for a game round, which is a third value and
        # not "the statement was empty".
        "scene_statement_sha256": statement_sha,
        "evidence_counts": mapping.get("evidence_counts"),
        "capture_geometry": mapping.get("capture_geometry"),
        "knowingly_truncated": mapping.get("knowingly_truncated"),
        "max_turns": max_turns,
        "per_call_budget_usd": budget,
        "judged_at": _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds"),
    }

def run_field(pack: Path, aspect_id: str, model: str = DEFAULT_MODEL,
              max_turns: int = 120, budget: float = 12.0,
              timeout_s: int = 3600) -> dict[str, Any]:
    """Judge one built pack on one aspect, and return the round.

    THE SPENDER. Everything above it plans; this is the call that consumes account
    capacity, so it is also the last place a wrong field can be stopped -- and it stops
    one by returning `{"usable": False, "error": ...}` rather than by raising, because a
    refusal that is a stored record can be read afterwards and a traceback cannot.

    The guards run in this order, and each is here because the alternative produced a
    confident answer to a question nobody asked:

      1. the identity mapping must not be inside the pack, or the judge is not blind (#32);
      2. the aspect must be one this module defines, and must belong to the task class
         the pack was built for -- `applicability()`, ahead of `ASPECTS[aspect_id]`;
      3. the pack must have been built for this aspect's evidence (`sees`);
      4. a SCENE pack's `SCENE.md` must be on disk AND be this scene's statement.
         `build_pack` refuses a scene it cannot state, but that guards the packer and
         this spends the field -- a pack is built once and judged later, from a directory
         anything may have touched, and an empty or wrong-scene statement passes a
         presence test. It is asked BEFORE the completeness key so that a pack failing
         both reports the statement, which is the one a selftest can distinguish;
      5. the pack must RECORD whether it is complete. A missing key read as falsy would
         assert completeness about a pack nothing on disk describes (#62).

    Returns the parsed judge output with `usable: True`, or a refusal naming which of
    those failed.
    """
    mapping = json.loads(mapping_path(pack).read_text())
    stray = sorted(q.name for q in pack.rglob("*")
                   if q.is_file() and "MAPPING" in q.name)
    if stray:
        return {"usable": False,
                "error": f"refusing to judge: the identity mapping is inside the pack "
                         f"({stray}), so the judge would not be blind"}
    # THE TASK CLASS, and it is the same argument as the `sees` check below one level
    # up: a scene has no player, so `fun` over a scene field would return eight
    # confident scores about pacing nobody asked for, and `fidelity` over a game field
    # would score a strip against a subject the field was never given. Scene and game
    # scores are never pooled (`eval/SCENES.md`), so this is not a preference.
    #
    # CHECKED HERE AS WELL AS AT BOTH CLIs, because the resource is "a judge field run
    # against a task" and this is the function that spends it (rule 13). It refuses an
    # id it cannot classify rather than assuming a game.
    #
    # BEFORE `ASPECTS[aspect_id]`, and that ordering is the guard. `field.py run` takes
    # `--aspect` with no `choices`, so an id this module does not define reached the
    # subscript and raised `KeyError` -- an uncaught traceback where every other refusal
    # here is a stored `usable: False` record saying what was wrong. `applicability`
    # answers for an unknown aspect id as well as for a wrong pairing.
    refusal = applicability(aspect_id, mapping.get("game") or "")
    if refusal:
        return {"usable": False, "error": f"refusing to judge: {refusal}"}
    aspect = ASPECTS[aspect_id]
    # A pack built for one aspect does not carry another aspect's evidence. Judging
    # `fun` over a code-only pack would produce eight confident scores derived from
    # nothing that was asked about.
    built_for = mapping.get("sees", "code")
    if built_for != aspect.sees:
        return {"usable": False,
                "error": f"pack was built with sees={built_for!r} but aspect "
                         f"{aspect_id!r} needs sees={aspect.sees!r}"}
    # THE SCENE STATEMENT ON DISK MUST BE THIS SCENE'S, checked HERE and not only where
    # it is written. `build_pack` refuses a scene it cannot state, but that guard is on
    # the packer and this is the spender: a pack is built once and judged later, possibly
    # from a copy, and the brief this function is about to write tells the judge to read
    # `SCENE.md` first.
    #
    # EXISTENCE IS NOT THE RESOURCE. An empty file, an edited one, or the OTHER scene's
    # statement all pass a presence test, and each buys a judge invocation that scores
    # the whole field against the wrong subject - which is worse than the narrowing the
    # statement removed, because it looks like an answer. So the content is compared, and every
    # failure to establish it - unreadable, unstatable, unequal - is a refusal (rule 7,
    # rule 13).
    #
    # NO ESCAPE FLAG. The comparison establishes that the file differs; it does not
    # establish HOW, and it does not need to (rule 2) - a stale pack, an edited file and
    # a statement changed since packing are one observable state, and re-packing answers
    # all three. There are 0 stored scene packs, so there is nothing to grandfather and
    # an escape would be a fail-open channel with no measured need.
    statement_sha: str | None = None
    if task_class(mapping["game"]) == "scene":
        try:
            expected = scene_statement(mapping["game"])
            on_disk = (pack / SCENE_STATEMENT_FILE).read_text(encoding="utf-8")
        # `UnicodeError` is NOT covered by `OSError`: `read_text` raises
        # `UnicodeDecodeError`, a `ValueError`, on a file that is not UTF-8. Uncaught it
        # is a traceback where every sibling here is a stored `usable: False` record.
        except (OSError, UnicodeError, RuntimeError) as e:
            return {"usable": False,
                    "error": f"this pack's {SCENE_STATEMENT_FILE} could not be read "
                             f"against scene {mapping['game']!r}: {e}. Every brief for "
                             f"a scene aspect tells the judge to read it first, so "
                             f"{aspect_id!r} would score each strip against a subject "
                             f"recovered from the field. Re-pack the run (field.py "
                             f"pack, or a field_sweep round) rather than judging this "
                             f"pack."}
        if on_disk != expected:
            return {"usable": False,
                    "error": f"this pack's {SCENE_STATEMENT_FILE} is not the statement "
                             f"of {mapping['game']!r} that this checkout holds "
                             f"({len(on_disk)} chars on disk against {len(expected)}). "
                             f"A judge reading it would score every strip against some "
                             f"other subject, which is worse than reading none. "
                             f"Re-pack the run (field.py pack, or a field_sweep round) "
                             f"rather than judging this pack."}
        # RECORDED, not merely checked. The brief NAMES `SCENE.md` and does not contain
        # it, so `brief_sha256` cannot answer "what subject was this round scored
        # against?" - the question #83 could not answer about what a judge had read.
        statement_sha = hashlib.sha256(on_disk.encode()).hexdigest()[:16]
    # HOW MUCH OF ITSELF EACH SUBMISSION IS BEING SHOWN IS A THIRD VALUE, not a boolean.
    # `mapping.get("knowingly_truncated")` returning None means the pack was built before
    # `build_pack` recorded it, and a missing key read as falsy would have the brief
    # assert completeness about a pack nothing on disk says is complete - fail-open, in
    # the direction #62 already cost this project a matrix. Refuse and re-pack instead.
    if "knowingly_truncated" not in mapping:
        return {"usable": False,
                "error": "the pack's MAPPING records no `knowingly_truncated`, so "
                         "nothing on disk says whether it holds every file its authors "
                         "wrote. The brief has to state that either way, and guessing "
                         "'complete' is the #62 direction. Re-pack the run "
                         "(field.py pack, or a field_sweep round) rather than judging "
                         "this pack."}
    brief_text = _brief(aspect, mapping["game"], mapping.get("capture_geometry"),
                        knowingly_truncated=bool(mapping["knowingly_truncated"]))
    (pack / "BRIEF.md").write_text(brief_text)

    argv = [
        "claude", "-p",
        judge_prompt(bool(mapping["knowingly_truncated"])),
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
        # check=False: the CLI exits non-zero for reasons that still produce a usable
        # verdict (a budget or turn ceiling reached after the answer was written), so
        # raising on the status would discard rounds that are fine. What the status IS
        # good for is telling an unusable round apart from a crashed one, so it is
        # carried into every failure below instead of being dropped.
        p = subprocess.run(argv, cwd=pack, capture_output=True, text=True,
                           timeout=timeout_s, check=False)
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
        return {"usable": False, "error": "unparseable", "raw": p.stdout[-2000:],
                "cli_exit": p.returncode, "cli_stderr": p.stderr[-2000:]}

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
        # PROVENANCE: what this round actually SAW. `_provenance` above holds it and the
        # reasoning behind every field in it.
        "provenance": _provenance(aspect, mapping, brief_text,
                                 statement_sha, max_turns, budget),
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
        # THE TASK CLASS, refused before anything is packed. `run_field` refuses the
        # same pairing again; this is the earlier of the two, so a wrong pairing costs
        # no pack rather than costing one and then being thrown away.
        refusal = applicability(a.aspect, a.game)
        if refusal:
            print(f"refusing to pack: {refusal}", file=sys.stderr)
            return 2
        # BOTH aspect properties, not one. This read `sees` and not `blind_language`
        # until 2026-08-23, so a pack built through the CLI - the path the module
        # docstring tells a human to type - was not blinded AT ALL: files kept their
        # real suffixes and the `.src` rename never ran (#138). Measured on
        # `wg-g4c/g4_platformer`, architecture, 8 submissions: 199 of the 207 evidence
        # files kept their real suffix, 191 of those names an arm, and the content
        # carried 667 arm-naming extension tokens, against 0 filenames and 11 tokens
        # after the repair - all 11 `import.meta`, which is declined on purpose.
        # `field_sweep.py` passed both at all three of its call sites, so no stored
        # round is affected - which is exactly why nothing noticed. **Guard the
        # resource, and verify on the path that actually holds it** (rule 13);
        # `blind_ext_selftest.py` check 7 now drives this entry point as a subprocess.
        aspect = ASPECTS[a.aspect]
        info = build_pack(a.run, a.game, a.out, a.order_seed,
                          sees=aspect.sees, blind_language=aspect.blind_language)
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
        # THE ADDRESS IS AN INPUT TO THE CHECK (rule 12).
        #
        # `--run` is a PATH, not a run name. Given a name, or a stale path, or any
        # directory without an `artifacts/` child, the glob below returned nothing, `games`
        # was empty, the loop never ran and this returned 0 -- a clean bill of health for a
        # run that was never looked at. Measured 2026-08-23, immediately after this gate
        # was written: `packcheck --run wg-g4c-2026-08-21` (the name, not the path) and
        # `--run /tmp` both exited 0 in silence, while the same gate correctly exited 1 on
        # the real path.
        #
        # A check that certifies nothing when misaddressed is worse than no check, because
        # its silence is indistinguishable from a pass. Refuse instead.
        if not a.run.is_dir():
            print(f"packcheck: no such run directory: {a.run}", file=sys.stderr)
            return 2
        if not (a.run / "artifacts").is_dir():
            print(f"packcheck: {a.run} has no artifacts/ - this is not a run directory. "
                  f"--run takes a PATH (eval/runs/<run>), not a run name.", file=sys.stderr)
            return 2
        games = a.game or sorted({p.name.split("__")[0]
                                  for p in (a.run / "artifacts").glob("*__*")})
        if not games:
            print(f"packcheck: {a.run}/artifacts contains no <game>__<stack>__<trial> "
                  f"directories - nothing was checked", file=sys.stderr)
            return 2
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
