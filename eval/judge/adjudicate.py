#!/usr/bin/env python3
"""Gate 4: check a judge's claims against the evidence it says it read.

    python3 judge/adjudicate.py --results RUN/judge-sweep/*.json --run RUN

The first three gates — ceiling, order-invariance, independence — are statistical, and
all three can pass on a judgement that is simply wrong. This project has now found four
instrument defects that were *perfectly consistent* and therefore looked like results:
the Rust 1-ULP oscillation, the Unity project lock, the HUD capture defect, and the Godot
unrealised-viewport race. `instability` read 0.000 on 22 of 24 submissions while the
third of those was corrupting the entire subjective ordering.

**Consistency is not correctness. The only thing that separated artifact from effect in
all four cases was reading the mechanism.** So this tool does not score anything. It
prints, for every claim a judge made, the identity of the submission it was really about
and the concrete artifacts it must be checked against — and it flags the two ways a claim
can be unfalsifiable before anyone opens a file:

* **A path that does not exist.** A judge citing `src/foo.ts` in a submission that has no
  such file has not read what it says it read, whatever the score.
* **Evidence with nothing checkable in it.** No path, no filename, no number. "The
  architecture is weak" cannot be adjudicated, so it cannot support a deduction.

Neither check proves a claim right. They only remove the claims nobody could ever have
verified, which is where the previous rubric's entire measured signal turned out to live.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

# THE TRAILING BOUNDARY IS LOAD-BEARING. Without it `js` matches inside `.json`, so every
# honest citation of `telemetry.json` or `audio.json` was captured as `telemetry.js` and then
# reported as a path that exists nowhere. Measured 2026-08-16: 16 of 31 remaining "found
# nowhere" flags were this one regex - the THIRD mechanism in one session by which this
# adjudicator inflated its own headline number (FINDINGS #51).
PATH_RE = re.compile(
    r"[\w./-]+\.(?:tsx|json|shader|wgsl|mjs|rs|ts|js|cs|gd|png|md)(?![A-Za-z0-9_])")
NUMBER_RE = re.compile(r"\d")


def artifacts_for(run: Path, submission: str) -> Path:
    return run / "artifacts" / submission / "eval"


#: Where each kind of evidence actually lives under a submission's `eval/` directory.
#: A judge can only cite what it was given, so the adjudicator must look where the ASPECT
#: looked. Resolving every aspect against `judge_pack/code` flags a `ux` judge's honest
#: `frame_0000.png` as a phantom citation - the frames are real, they are just in
#: `eval/frames/`. Measured 2026-08-16: that alone accounted for most of a "54 of 80 claims
#: cite something that does not exist" reading, one message after the same class of error
#: was written up as FINDINGS #51.
EVIDENCE_ROOTS = {"code": ("judge_pack/code",), "frames": ("frames",),
                  "telemetry": (), "audio": ()}

#: Files `build_pack` WRITES INTO the pack for a given kind of evidence. The pack itself is a
#: temp directory and is gone by the time anyone adjudicates, so a judge citing the very file
#: it was handed - `telemetry.json`, `audio.json`, `CHANGED.txt` - cannot be resolved against
#: anything on disk and was reported as a citation to a file that does not exist. That was 16
#: of 80 claims, i.e. every single `fun` and `audio` claim, flagged for quoting its own
#: evidence by name.
PACK_ARTIFACTS = {"telemetry": ("telemetry.json",), "audio": ("audio.json",),
                  "code": ("CHANGED.txt",), "frames": ()}


def _sees(aspect_id: str) -> str:
    try:
        from aspects import ASPECTS
        return ASPECTS[aspect_id].sees
    # Narrow: `aspects` not importable from here (ImportError) or an aspect id this
    # build does not know (KeyError). "code" is the conservative default -- it is the
    # SMALLEST evidence set, so a wrong guess shows the adjudicator less, never more.
    # A blind catch would have hidden an AttributeError from a renamed field behind the
    # same silent default.
    except (ImportError, KeyError):
        return "code"


def _roots(art: Path, aspect_id: str) -> list[Path]:
    out: list[Path] = []
    for kind in _sees(aspect_id).split("+"):
        for rel in EVIDENCE_ROOTS.get(kind, ()):
            d = art / rel
            if d.is_dir():
                out.append(d)
    return out or [art / "judge_pack" / "code"]


def _pack_artifacts(aspect_id: str) -> set[str]:
    names: set[str] = set()
    for kind in _sees(aspect_id).split("+"):
        names.update(PACK_ARTIFACTS.get(kind, ()))
    return names


def check_one(run: Path, result: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    aspect_id = result.get("aspect", "idiomatic")
    for s in result["submissions"]:
        sub = s.get("submission", "?")
        ev = s.get("evidence", "") or ""
        cited = sorted(set(PATH_RE.findall(ev)))
        art = artifacts_for(run, sub)
        roots = _roots(art, aspect_id)
        pack = roots[0]
        # A CITATION CAN BE REAL WITHOUT BEING A PATH IN THE TREE, and conflating those
        # two overstates this flag by about half.
        #
        # `anonymise.py` renames files to `sim/01.gd`, `view/02.cs` and so on, but it
        # does NOT rewrite filenames that appear inside the files. The agents' own doc
        # comments are full of them - "Read sim/intents.gd instead", "this is what lets
        # `sim/sim.gd` depend on it" - so a judge reading `sim/04.gd` sees the string
        # `sim/sim.gd` and cites it. That citation is traceable to something it really
        # read; it is simply not a path.
        #
        # MEASURED 2026-08-16 on the first `architecture` field: 37 citations were not
        # paths in the tree, and 17 of them appear verbatim in the pack's CONTENTS. A
        # single "paths not found" count reported that as 37 unverifiable claims, which
        # is the population the old rubric's entire measured signal turned out to live
        # in - so overcounting it is not a harmless conservatism, it is a number someone
        # would act on.
        blob = ""
        for d in roots:
            for f in d.rglob("*"):
                if f.is_file() and f.suffix.lower() not in (".png", ".jpg", ".wav"):
                    blob += f.read_text(errors="ignore") + "\n"
        artifacts = _pack_artifacts(aspect_id)
        # PATH RECONSTRUCTION IS NOT FABRICATION, and collapsing them hides which
        # defect you have. A judge reading an anonymised `sim/03.src` and citing
        # `sim/pieces.gd` has renamed a file it really read - the stem is a symbol in
        # the pack. A judge citing something whose stem appears nowhere and whose
        # quoted code is absent has made a claim no one can check. Measured on the
        # first full field: 11 of 11 `architecture` flags were reconstruction and
        # ZERO were fabrication, which points the fix at the pack's naming and the
        # brief, not at the judge (FINDINGS #51).
        lowblob = blob.lower()
        resolved, in_content, missing = [], [], []
        for c in cited:
            if Path(c).name in artifacts:
                resolved.append(c)
                continue
            hits = [h for d in roots for h in d.rglob(Path(c).name)]
            if hits:
                resolved.append(c)
            elif c in blob:
                in_content.append(c)
            else:
                missing.append(c)
        rows.append({
            "label": s.get("label"),
            "submission": sub,
            "stack": s.get("stack"),
            "score": s.get("score"),
            "rank": s.get("rank"),
            "cited_paths": cited,
            "paths_named_in_pack_contents": in_content,
            "paths_not_found": missing,
            # Of the not-found ones, which look like a renamed real file?
            "paths_reconstructed": [c for c in missing
                                    if Path(c).stem.lower() in lowblob],
            "paths_unlocatable": [c for c in missing
                                  if Path(c).stem.lower() not in lowblob],
            "has_number": bool(NUMBER_RE.search(ev)),
            "checkable": bool(cited) or bool(NUMBER_RE.search(ev)),
            "artifacts": str(art),
            "evidence": ev,
        })
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", nargs="+", type=Path, required=True)
    ap.add_argument("--run", type=Path, required=True)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    report: dict[str, Any] = {}
    unfalsifiable = 0
    phantom = 0
    in_content = 0
    reconstructed = 0
    total = 0
    for rp in a.results:
        res = json.loads(rp.read_text())
        if not res.get("usable"):
            print(f"[skip] {rp.name}: unusable ({res.get('error')})")
            continue
        key = f"{res['game']}:{res['aspect']}:seed{res['order_seed']}"
        rows = check_one(a.run, res)
        report[key] = rows
        if a.json:
            continue
        print(f"\n=== {key} ===")
        for r in sorted(rows, key=lambda r: r["score"]):
            total += 1
            flags = []
            if not r["checkable"]:
                flags.append("UNFALSIFIABLE: no path and no number in the evidence")
                unfalsifiable += 1
            if r["paths_named_in_pack_contents"]:
                flags.append(
                    f"named in the pack's CONTENTS but not a path in it (the "
                    f"anonymiser renames files, not the filenames written inside them "
                    f"- these are traceable, just not as paths): "
                    f"{r['paths_named_in_pack_contents']}")
                in_content += 1
            if r["paths_reconstructed"]:
                flags.append(
                    f"RECONSTRUCTED name - the stem is a symbol in the pack, so this "
                    f"is a renamed real file rather than an invented one: "
                    f"{r['paths_reconstructed']}")
                reconstructed += 1
            if r["paths_unlocatable"]:
                flags.append(f"UNLOCATABLE - neither the path, the string, nor the "
                             f"stem appears anywhere: {r['paths_unlocatable']}")
                phantom += 1
            print(f"  {r['label']} score={r['score']} rank={r['rank']}  "
                  f"{r['submission']} [{r['stack']}]")
            print(f"     evidence: {r['evidence'][:220]}")
            if r["cited_paths"]:
                print(f"     cites   : {r['cited_paths']}")
            print(f"     open    : {r['artifacts']}")
            for f in flags:
                print(f"     !! {f}")

    if a.json:
        print(json.dumps(report, indent=2))
        return 0
    print(f"\n=== adjudication summary ===")
    print(f"  claims examined                           : {total}")
    print(f"  with no path and no number (unfalsifiable): {unfalsifiable}")
    print(f"  citing a name found only in the pack's TEXT: {in_content}")
    print(f"  citing a RECONSTRUCTED name (renamed real file): {reconstructed}")
    print(f"  citing a name that is UNLOCATABLE anywhere     : {phantom}")
    print("\nThe middle row is NOT a defect. `anonymise.py` renames files but leaves the "
          "filenames\nthe authors wrote inside them, so a judge legitimately cites "
          "`sim/sim.gd` after reading\nit in a doc comment in `sim/04.gd`. Counting "
          "those as phantom citations overstated this\nflag by about half on its first "
          "real use.\n\nNeither number says a claim is WRONG. They say how many claims "
          "could never have been\nchecked, which is the population the previous "
          "rubric's only measured signal came from.\nOpen the artifacts above and read "
          "the mechanism for the rest.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
