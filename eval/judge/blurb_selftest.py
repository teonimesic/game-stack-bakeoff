#!/usr/bin/env python3
"""Does the judge-facing text in a pack still describe the packer that built it?

THE DEFECT THIS EXISTS TO PREVENT, and it is a whole class rather than one sentence.

`field.EVIDENCE_BLURB["code"]` told every code judge

    NOTE: the pack is filled until a size budget runs out, so it may not contain every
    file the author wrote - judge what is here and do not infer that an absent concern
    was neglected.

The character budget was removed on 2026-08-22 (#69) and `files_dropped_for_length` has
been 0 by construction ever since, asserted by `field.pack_completeness`. So the harness
went on telling every judge that its evidence might be an alphabetically-selected subset
of each submission when it was the whole of it - and the direction of the error is the
damaging one: it invites a judge to discount an absence it is in fact seeing in full,
which is the opposite of the caution the sentence was written to induce.

**A sentence about the packer that no code reads is how this one survived.** Every gate
this project owns reads the pack, the manifest or the score; none read the brief. So the
subject here is the RESOURCE - *judge-facing text that makes a claim about the packer* -
and not the one constant that happened to be wrong. Today that resource is two objects,
`EVIDENCE_BLURB` (via `BRIEF.md`) and the sampling skill written into every pack; a third
gets the same treatment by being written into `judge_facing_texts()`.

What is checked, and why each direction is needed:

  1. NON-VACUITY. The fixture really builds eight packs with all four evidence buckets in
     them, so every set-membership check below reads a populated set (rule 1).
  2. NAMED ARTIFACT EXISTS. Every artifact a blurb names in backticks is on disk in a
     pack built for an aspect that sees that bucket.
  3. THE COMPLETENESS CLAIM TRACKS THE PACKER, measured from the fixture rather than read
     back out of what `build_pack` recorded about itself, and asserted in BOTH states.
  4. NO CAUTION VOCABULARY IN THE COMPLETE-STATE NOTE. The one check that would have
     fired on the original defect on its first day.
  5. PACK-PATH EXAMPLES. A `bucket/NN.ext` example in the brief has to be a label the
     packer would really write - and under a non-blind aspect it must carry no suffix at
     all, because in a four-arm field a real suffix names an arm.
  6. MUTANTS. The historical sentence restored; a blurb naming an artifact no pack holds;
     a real suffix in the non-blind pack-path example; the two notes collapsed into one;
     a constant `claude -p` prompt. Checks 2 and 5 own two of those, so no check above
     this line is asserted against a pack without something that proves it can go red.
  7. VARIANT (rule 15). A field that really is knowingly truncated, built by the real
     `build_pack(allow_truncated=True)` over a fixture whose stored drop count is
     non-zero. A mutant removes a mechanism; only a variant can manufacture the input
     the mechanism exists for.
  8. FAIL-CLOSED. Deleting the completeness statement altogether must be red, not quiet -
     otherwise "remove the sentence" is a repair that leaves the judge told nothing.
  9. A PACK THAT DOES NOT RECORD ITS STATE IS REFUSED by `run_field`, not assumed
     complete, and every pack the packer writes records one.
 10. EVERY REFUSAL IS A STORED RECORD, including for an aspect id `aspects.py` does not
     define - with the positive half beside it, so the check cannot pass by refusing
     everything.
 11. THE SCENE STATEMENT. `SCENE.md` is judge-facing text making a claim about the TASK
     rather than about the packer, so it is checked against what it IS a function of: it
     must be on disk for a scene field and absent for a game one, byte-identical to
     `field.scene_statement`, different for the 2 scenes, free of stack tokens under
     `verify_blind.py --packs`, and free of `tools/prompt_guard.py`'s criterion and
     threshold vocabulary - with a mutant for each of those last 2, a variant driving a
     leaking statement through the real packer, and a fail-closed case for a scene the
     packer cannot state. `run_field` refuses a statement that is absent, empty,
     undecodable or the other scene's, and each state asserts WHICH refusal answered, so
     the undecodable one cannot pass through the mismatch branch on a host whose locale
     codec happens to accept the bytes. What a round RECORDS about its subject is driven
     through `run_field` with the judge stubbed - `brief_sha256` cannot stand in for it,
     because the brief NAMES `SCENE.md` and does not contain it, and a direct call to
     `_provenance` would prove only that the function copies its argument.
 12. WHO THE FRAMES BLURB SAYS IS WATCHING is a function of the task class, in both
     directions. A scene has no player, so "everything the player sees" in a scene brief
     is check 4's defect in a new place - judge-facing text describing something the task
     does not have. The expected wordings are spelled out in this file and reconciled
     with `field.FRAMES_AUDIENCE` by a row, never imported from it (task 113).
 13. THE STORED-ROUND CENSUS, against a fixture tree whose answer is written out as
     literals beside it. `--stored-rounds` reads a gitignored directory, so nothing could
     see it until this fixture existed - and the table it produces in `eval/RUNS.md` duly
     went stale on 3 rows of 4 with the producer's command printed above them. What went
     stale was the POPULATION rather than the digits, so the census now prints where each
     counted round is and what pack state it recorded, and this checks both. The fixture
     carries a round nested 2 deep (#127), a hashed non-code round that must stay out of
     the code row, a JSON file that is not a round and a file that is not JSON. Its
     VARIANT is a round stored `knowingly_truncated: true` whose hash is the
     truncated-state brief's: it reads `same` only if the census honours the state the
     round recorded, which no mutant of the population block can manufacture.
     `stored_rounds_mutants.py` is the red half - 7 mutants and a `--variant-control`.

Run:  python3 judge/blurb_selftest.py          # unpiped: exit 1 means a claim has drifted
"""
from __future__ import annotations

import contextlib
import hashlib
import io
import itertools
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "tools"))
sys.path.insert(0, str(HERE.parent / "suites"))

import aspects  # noqa: E402
import field  # noqa: E402
import prompt_guard  # noqa: E402
import scene_prompts  # noqa: E402

FAILS: list[str] = []


def expect(name: str, cond: bool, detail: str) -> None:
    if not cond:
        FAILS.append(f"{name}: {detail}")


# ---------------------------------------------------------------------------
# A run in the shape `field.build_pack` reads: four arms, two trials each.
# ---------------------------------------------------------------------------
ARMS = ("rust", "ts", "unity", "godot")
STACK_EXT = {"rust": ".rs", "ts": ".ts", "unity": ".cs", "godot": ".gd"}
ORIGINS = {
    "rust": ["crates/sim/src/world.rs", "crates/game/src/view.rs"],
    "ts": ["src/sim/world.ts", "src/render/view.ts"],
    "unity": ["Assets/Sim/Grid.cs", "Assets/View/GameView.cs"],
    "godot": ["sim/world.gd", "scenes/view.gd"],
}


def stored_run(root: Path, game: str = "g9_probe", *, dropped: int = 0) -> Path:
    """Eight submissions carrying all four evidence buckets.

    `dropped` is what each submission's `eval/report.json` reports as
    `files_dropped_for_length`. It is the ONLY input that puts `pack_completeness` into
    its incomplete state, and it is a stored number rather than a flag on the call, which
    is why check 7 is a variant and not a mutant.
    """
    run = root / "run"
    for stack in ARMS:
        for trial in ("t0", "t1"):
            sub = run / "artifacts" / f"{game}__{stack}__{trial}"
            code = sub / "eval" / "judge_pack" / "code"
            (code / "sim").mkdir(parents=True)
            (code / "view").mkdir(parents=True)
            manifest, rows = [], []
            for i, origin in enumerate(ORIGINS[stack], start=1):
                bucket = "sim" if i == 1 else "view"
                label = f"{bucket}/{i:02d}{STACK_EXT[stack]}"
                body = f"// module {i}\nfn step() {{}}\n"
                (code / label).write_text(body)
                manifest.append({"label": label, "origin": origin,
                                 "chars": str(len(body))})
                rows.append(f" {origin:<44} | {40 + i} ++--")
            rows.append(f" {len(rows)} files changed, 90 insertions(+), 7 deletions(-)")
            (sub / "diff.stat").write_text("\n".join(rows) + "\n")

            # TWO FRAME DIRECTORIES, because the harness has two and they are read by
            # different code: `build_pack` copies from `eval/frames`, while
            # `pack_matches_manifest` counts `eval/judge_pack/frames` against the
            # report's `pack.frames`. A real stored trial has both
            # (`wg-g4c-.../g4_platformer__godot__t0`), and a fixture with one is a
            # fixture that cannot reach the code under test.
            for rel in ("eval/frames", "eval/judge_pack/frames"):
                frames = sub / rel
                frames.mkdir(parents=True, exist_ok=True)
                for i in range(3):
                    # Not a decodable PNG on purpose: `build_pack` reads the geometry
                    # inside a narrow `except (PngError, OSError)` and a missing geometry
                    # costs the brief one sentence. Nothing here is about geometry.
                    (frames / f"frame_{i:02d}.png").write_bytes(b"not-a-png")

            (sub / "eval" / "playbot.json").write_text(json.dumps({
                "ticks_driven": 1800, "events_fired": 12,
                "telemetry": {"usable": True, "seconds_of_play": 30.0,
                              "longest_quiet_stretch_seconds": 4.0,
                              "event_intervals_seconds": [1.0, 2.5, 4.0]}}))
            (sub / "eval" / "programmatic.json").write_text(json.dumps({
                "audio": {"applies": True,
                          "clips": {"hit.wav": {"seconds": 0.4, "rms": 0.11,
                                                "peak": 0.9},
                                    "jump.wav": {"seconds": 0.2, "rms": 0.08,
                                                 "peak": 0.7}}}}))
            (sub / "eval" / "report.json").write_text(json.dumps({
                "game": game,
                "pack": {"built": True, "files_in_pack": len(manifest),
                         "files_dropped_for_length": dropped, "frames": 3,
                         "manifest": manifest}}))
    return run


def measured_incomplete(run: Path, game: str) -> bool:
    """Is this field truncated? Measured from the STORED reports, not from `build_pack`.

    The wiring defect being pinned is exactly that the brief's claim was not a function of
    the packer's state, so the check must not take the packer's own word for the state.
    This reads `eval/report.json` directly - the same source `pack_completeness` reads,
    but through this file's own code, so a `pack_completeness` that stopped answering
    would not silently drag the assertion along with it.
    """
    total = 0
    for d in sorted((run / "artifacts").glob(f"{game}__*")):
        rep = json.loads((d / "eval" / "report.json").read_text())
        total += int(rep["pack"]["files_dropped_for_length"])
    return total > 0


#: Things a blurb may say in backticks that are NOT an artifact the packer writes.
#: An example pack path is checked separately, by check 5, against the labels really on
#: disk - listing it here would excuse it from both.
_PATH_EXAMPLE = re.compile(r"^(sim|view|tests|tools|data|other)/\d{2}(\.[a-z]+)?$")
_ARTIFACT = re.compile(r"`([A-Za-z0-9_./-]+\.[a-z]+|[A-Za-z0-9_-]+/)`")


def artifacts_named(text: str) -> set[str]:
    """Backticked filenames and directories in a blurb, minus the pack-path examples."""
    return {m for m in _ARTIFACT.findall(text) if not _PATH_EXAMPLE.match(m)}


def path_examples(text: str) -> set[str]:
    return set(re.findall(r"`([A-Za-z0-9_-]+/\d{2}(?:\.[a-z]+)?)`", text))


def judge_facing_texts(aspect: aspects.Aspect, mapping: dict, pack: Path) -> dict[str, str]:
    """Every text in a pack that speaks to the judge, and makes a claim by doing so.

    Written as the resource rather than as a list of the two constants that were wrong,
    because a rule whose trigger is an enumeration has to be re-derived by the first
    reader who meets an item that is not on it. A further judge-facing text is covered
    the moment it is added here.

    THE CLAIMS ARE NOT ALL ABOUT THE PACKER, and that is what `SCENE.md` widened. Three
    of these describe how much of each submission the judge is holding; `SCENE.md`
    describes the TASK all 8 were set. Both are text a judge acts on and neither is read
    by any gate that walks the pack, which is the property this file exists for -- so the
    checks below are keyed on which claim a text makes, never on which file it is.
    """
    skill = pack / ".claude" / "skills" / "sampling-code" / "SKILL.md"
    statement = pack / field.SCENE_STATEMENT_FILE
    kt = bool(mapping.get("knowingly_truncated"))
    texts = {
        "BRIEF.md": field._brief(aspect, mapping["game"],
                                 mapping.get("capture_geometry"),
                                 knowingly_truncated=kt),
        "SKILL.md": skill.read_text() if skill.is_file() else "",
        # NOT IN THE PACK AT ALL - it is `claude -p`'s argument. A checker that walked
        # the pack directory would never see it, and it was asserting "The submissions
        # are complete" unconditionally when this file was written. That is why the
        # subject here is the resource and not a directory.
        "claude -p prompt": field.judge_prompt(kt),
    }
    # READ OFF DISK, not rebuilt from the constant. The question this file asks is what
    # the judge is HANDED; rebuilding it would agree with the packer by construction and
    # could not see a pack that failed to write one. Check 11 compares the two.
    if aspects.task_class(mapping["game"]) == "scene":
        texts[field.SCENE_STATEMENT_FILE] = (
            statement.read_text(encoding="utf-8") if statement.is_file() else "")
    return texts


#: WHICH texts STATE the completeness claim, as opposed to merely not contradicting it.
#: BRIEF.md is where a judge is told what its evidence is; the sampling skill is read
#: exactly when it is deciding how much to open. The `claude -p` prompt is a one-paragraph
#: instruction and repeating the sentence there would be a third copy of a claim, which is
#: how #100 recurred - so it is held to the weaker rule (it must not contradict, and it
#: must be a function of the state) and not to the stronger one.
STATES_THE_CLAIM = ("BRIEF.md", "SKILL.md")

#: Judge-facing texts that make NO claim about the packer, so checks 3 and 3b -- which
#: ask whether a text tracks `knowingly_truncated` -- have nothing to read in them.
#:
#: This is an exemption and every exemption is a channel (rule 7), so it buys nothing:
#: `SCENE.md` is not unchecked, it is checked against the thing it IS a function of. Its
#: claim is about the task, so check 11 asserts it varies by SCENE, that it is on disk
#: only for a scene field, that it names no stack and no criterion, and that the packer
#: refuses a scene it cannot state.
CLAIMS_NOTHING_ABOUT_THE_PACK = (field.SCENE_STATEMENT_FILE,)


#: Words a note may use ONLY when the pack really is truncated. A closed class, and
#: deliberately small: it is the anti-direction (a caution word where there is nothing to
#: caution about), which is the shape the original defect had.
#:
#: **WHERE this is applied is the whole design of check 4, and the obvious address is
#: wrong** (rule 12). Aimed at the rendered BRIEF.md or SKILL.md it fires on the skill's
#: closing section, which narrates the removed cap in the past tense - three hits, none of
#: them a defect. Aimed at the CLAIMS THEMSELVES - the `EVIDENCE_BLURB` values and
#: `COMPLETENESS_NOTE[False]`, which describe the pack in the present tense - it is 0 false
#: positives on the live corpus and 2 true positives on the pre-repair one. Measured both
#: ways before choosing; see the module docstring.
CAUTION_WORDS = ("budget", "truncat", "may not contain", "dropped", "subset",
                 "not every")


def caution_hits(text: str) -> list[str]:
    low = text.lower()
    return [w for w in CAUTION_WORDS if w in low]


def present_tense_claims() -> dict[str, str]:
    """Every string in this module that describes the pack a judge is holding NOW.

    The skill's historical paragraph is deliberately not here: it is past tense about a
    mechanism that was removed, and a check that reddens it is a check somebody turns off.
    """
    out = {f"EVIDENCE_BLURB[{k!r}]": v for k, v in field.EVIDENCE_BLURB.items()}
    out["COMPLETENESS_NOTE[False]"] = field.COMPLETENESS_NOTE[False]
    # THE SKILL'S BODY TOO, with `{history}` left unfilled. Without this a stale claim
    # written straight into the template - rather than through COMPLETENESS_NOTE - would
    # be invisible to check 4, which is how the original one survived: it was in the text
    # a judge reads and in nothing a check reads.
    out["PACK_SKILL_TEMPLATE"] = field.PACK_SKILL_TEMPLATE.replace(
        "{history}", "").replace("{completeness}", "")
    out["JUDGE_PROMPT[False]"] = field.JUDGE_PROMPT[False]
    return out


#: WHO THE FRAMES BLURB SAYS IS WATCHING, spelled out HERE rather than imported from
#: `field.FRAMES_AUDIENCE`.
#:
#: A control that builds its expectation by calling its subject is not a control: swap the
#: 2 values in `field.FRAMES_AUDIENCE` and an imported expectation swaps with them, so the
#: scene brief would be checked against the game wording and come back green (task 113).
#: These are the second, independent statement; `audiences-still-agree` is the row that
#: keeps the 2 in step, which is what the rule asks for instead of a shared object.
FRAMES_AUDIENCE_GAME = "Everything the player sees"
FRAMES_AUDIENCE_SCENE = "Everything the scene shows"

CODE_ASPECTS = [a for a in aspects.ASPECTS.values() if "code" in a.sees.split("+")]
LABELS = list(field.LABELS)


def build(run: Path, aspect: aspects.Aspect, dest: Path, game: str = "g9_probe",
          **kw) -> dict:
    return field.build_pack(run, game, dest, 7, sees=aspect.sees,
                            blind_language=aspect.blind_language, **kw)


def census_fixture(root: Path) -> Path:
    """A stored-runs tree whose census answer is stated in the caller, not computed.

    9 rounds, and the shape of the real corpus rather than a flat list of it:

    * `alpha/` - 2 `architecture` rounds hashed against the brief THIS checkout builds,
      so they must read `same`.
    * `alpha/nested/deeper/` - 2 `idiomatic` rounds, `knowingly_truncated: True`. One is
      hashed against the TRUNCATED-state brief and must read `same`; the other against a
      digest no brief has, so it must read `moved`. The first is the VARIANT (rule 15):
      no mutant of the population block can manufacture a round that only rebuilds if
      the census honours the state the round recorded, and a census that always rebuilt
      the complete-state brief would call it `moved` and look like a real drift. Nested
      because a run directory is not always a child of the root (#127) and 4 of the 14
      real hashed code rounds are 2 levels down.
    * `beta/` - 3 code rounds with no `provenance` at all, the shape of every round
      stored before it existed: unassessable, not clean.
    * `gamma/` - 1 hashed `audio` round, which is a round and is not code, plus a JSON
      file that is not a round and a file that is not JSON.
    * `delta/` - 1 hashed code round naming an aspect `aspects.py` does not define. Its
      brief cannot be rebuilt, so it is neither `same` nor `moved` - and it is still one
      of the rounds the headline counts, so it must appear in the population under a
      third verdict rather than be dropped between the two.
    """
    audio, arch, idio = (aspects.ASPECTS[a] for a in ("audio", "architecture",
                                                      "idiomatic"))

    def digest(a: aspects.Aspect, *, kt: bool) -> tuple[str, int]:
        txt = field._brief(a, "g9_probe", None, knowingly_truncated=kt)
        return hashlib.sha256(txt.encode()).hexdigest()[:16], len(txt)

    def write(rel: str, aid: str, prov: dict | None) -> None:
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        rec: dict[str, Any] = {"aspect": aid, "order_seed": 0, "game": "g9_probe"}
        if prov is not None:
            rec["provenance"] = prov
        p.write_text(json.dumps(rec))

    def prov(a: aspects.Aspect, *, kt: bool, real: bool) -> dict:
        h, n = digest(a, kt=kt)
        return {"sees": a.sees, "game": "g9_probe", "knowingly_truncated": kt,
                "brief_sha256": h if real else "0" * 16, "brief_chars": n}

    write("alpha/a1.json", "architecture", prov(arch, kt=False, real=True))
    write("alpha/a2.json", "architecture", prov(arch, kt=False, real=True))
    write("alpha/nested/deeper/i1.json", "idiomatic", prov(idio, kt=True, real=True))
    write("alpha/nested/deeper/i2.json", "idiomatic", prov(idio, kt=True, real=False))
    for i in range(3):
        write(f"beta/b{i}.json", "architecture" if i == 0 else "idiomatic", None)
    write("gamma/au.json", "audio", prov(audio, kt=False, real=True))
    (root / "gamma/notaround.json").write_text(json.dumps({"aspect": "audio"}))
    (root / "gamma/notjson.json").write_text("{")
    # `sees` is spelled out because the aspect it names does not exist to be read off.
    assert "architecture_v0" not in aspects.ASPECTS
    write("delta/x1.json", "architecture_v0",
          dict(prov(arch, kt=False, real=False), sees="code"))
    return root


def main() -> int:
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        run = stored_run(root)

        # -------------------------------------------------------------------
        # 1. NON-VACUITY. One pack per DISTINCT PACK SHAPE, and every one proved to
        #    hold the bucket it is about to be asked about - otherwise check 2 is a
        #    set-membership test over an empty set.
        #
        #    THE KEY IS `(sees, blind_language)`, NOT `sees`. Keyed on `sees` alone
        #    this built ONE code pack, non-blind, because `idiomatic` comes first in
        #    `ASPECTS` - and then checked `architecture`'s brief, which promises
        #    `.src` labels, against it. It reported two failures that were entirely
        #    the fixture's. That is #138 exactly: one call site reading half of an
        #    aspect, invisible to anything that does not build both shapes.
        # -------------------------------------------------------------------
        Shape = tuple[str, bool]
        packs: dict[Shape, tuple[aspects.Aspect, Path, dict]] = {}
        for a in aspects.ASPECTS.values():
            key = (a.sees, a.blind_language)
            if key in packs:
                continue
            dest = root / f"pack-{a.sees.replace('+', '-')}-blind{int(a.blind_language)}"
            packs[key] = (a, dest, build(run, a, dest))

        covered = set().union(*(set(s.split("+")) for s, _b in packs))
        expect("fixture-covers-every-bucket", covered == set(field.EVIDENCE_BLURB),
               f"the fixture builds packs for {sorted(packs)} which between them cover "
               f"{sorted(covered)}, but EVIDENCE_BLURB describes "
               f"{sorted(field.EVIDENCE_BLURB)} - a bucket with no pack is a blurb "
               f"nothing below reads")
        expect("fixture-covers-both-blinding-modes",
               len({b for _s, b in packs}) == 2,
               f"the fixture builds packs in blinding modes "
               f"{sorted({b for _s, b in packs})}; check 5 needs both, and the shape "
               f"it does not build is the shape it cannot judge")

        for (sees, blind), (_a, dest, _m) in sorted(packs.items()):
            n = sum(1 for p in dest.rglob("*") if p.is_file())
            expect(f"fixture-nonempty[{sees}:blind={blind}]",
                   n >= 8 * len(sees.split("+")),
                   f"pack for sees={sees!r} blind={blind} holds {n} file(s); the checks "
                   f"below would pass on an empty pack")

        # -------------------------------------------------------------------
        # 2. NAMED ARTIFACT EXISTS. Every backticked artifact in a blurb is a file
        #    or directory really on disk, in every submission of a pack built for
        #    an aspect that sees that bucket.
        # -------------------------------------------------------------------
        for bucket, blurb in sorted(field.EVIDENCE_BLURB.items()):
            named = artifacts_named(blurb)
            expect(f"blurb-names-something[{bucket}]", bool(named),
                   f"the {bucket!r} blurb names no artifact in backticks, so check 2 "
                   f"reads an empty set for it")
            key = next(k for k in packs if bucket in k[0].split("+"))
            sees = key[0]
            _a, dest, _m = packs[key]
            for art in sorted(named):
                missing = [lab for lab in LABELS
                           if not (dest / lab / art.rstrip("/")).exists()]
                expect(f"named-artifact-on-disk[{bucket}:{art}]", not missing,
                       f"the {bucket!r} blurb tells the judge about {art!r}; it is "
                       f"absent from {len(missing)} of {len(LABELS)} submissions in a "
                       f"pack built with sees={sees!r} ({', '.join(missing[:4])})")

        # -------------------------------------------------------------------
        # 3+4. THE COMPLETENESS CLAIM, complete state. Measured from the stored
        #      reports, not from what `build_pack` recorded about itself.
        # -------------------------------------------------------------------
        expect("fixture-is-complete", not measured_incomplete(run, "g9_probe"),
               "the baseline fixture reports a non-zero drop count, so the complete "
               "state below is never exercised")

        # 4. NO CAUTION VOCABULARY IN A PRESENT-TENSE CLAIM. The check that would have
        #    fired on the original defect on its first day.
        for name, claim in sorted(present_tense_claims().items()):
            hits = caution_hits(claim)
            expect(f"no-caution-in-a-present-tense-claim[{name}]", not hits,
                   f"{name} warns the judge with {hits} about a pack in which "
                   f"files_dropped_for_length is 0 by construction (#69). That is the "
                   f"damaging direction: the judge is invited to discount an absence it "
                   f"is seeing in full")

        # 3. THE NOTE A PACK CARRIES IS THE NOTE FOR THE STATE IT IS MEASURABLY IN, in
        #    every judge-facing text, and the OTHER state's note is absent from it.
        for a, dest, m in [packs[k] for k in sorted(packs)]:
            texts = judge_facing_texts(a, m, dest)
            code = "code" in a.sees.split("+")
            for where, text in sorted(texts.items()):
                expect(f"judge-facing-text-exists[{a.id}:{where}]", bool(text.strip()),
                       f"{where} is empty for aspect {a.id!r}, so every claim check "
                       f"against it reads an empty string")
                if where in CLAIMS_NOTHING_ABOUT_THE_PACK:
                    continue
                # The brief only carries the note for a code aspect - the cap was on the
                # code pack. The skill is aspect-agnostic and carries it always.
                if where in STATES_THE_CLAIM and (where == "SKILL.md" or code):
                    expect(f"complete-state-is-stated[{a.id}:{where}]",
                           field.COMPLETENESS_NOTE[False] in text,
                           f"{where} for aspect {a.id!r} makes no completeness claim at "
                           f"all; an unstated completeness is exactly the state in "
                           f"which a judge discounts absences on its own")
                expect(f"other-state-absent[{a.id}:{where}]",
                       field.COMPLETENESS_NOTE[True] not in text,
                       f"{where} for aspect {a.id!r} carries the TRUNCATED note over a "
                       f"field measured complete")

        # 3b. EVERY judge-facing text is a FUNCTION of the state, whether or not it
        #     states the claim in words. This is the vocabulary-free half, and it is the
        #     one that caught the `claude -p` prompt: that text was a constant, so it
        #     asserted "The submissions are complete" over a field packed on purpose
        #     under a cap. A text identical in both states cannot be describing the pack.
        for a, _dest, m in [packs[k] for k in sorted(packs)]:
            comp = dict(m, knowingly_truncated=False)
            trunc = dict(m, knowingly_truncated=True)
            for where in judge_facing_texts(a, comp, _dest):
                t0 = judge_facing_texts(a, comp, _dest)[where]
                t1 = judge_facing_texts(a, trunc, _dest)[where]
                if where == "SKILL.md":
                    # Read off disk, so it cannot vary with an argument; it is checked
                    # against `pack_skill()` directly instead.
                    t0, t1 = field.pack_skill(False), field.pack_skill(True)
                if where == "BRIEF.md" and "code" not in a.sees.split("+"):
                    continue  # no completeness claim to make; the cap was code-only
                if where in CLAIMS_NOTHING_ABOUT_THE_PACK:
                    continue  # a claim about the task; check 11 is its state test
                expect(f"state-dependent[{a.id}:{where}]", t0 != t1,
                       f"{where} for aspect {a.id!r} is byte-identical for a complete "
                       f"pack and a knowingly truncated one, so whatever it says about "
                       f"the evidence is true of at most one of them")

        # -------------------------------------------------------------------
        # 5. PACK-PATH EXAMPLES are labels the packer would really write, and under
        #    a non-blind aspect they carry no suffix, because a real suffix names an
        #    arm in a four-arm field.
        # -------------------------------------------------------------------
        for a in CODE_ASPECTS:
            _a, dest, _m = packs[(a.sees, a.blind_language)]
            on_disk = {str(p.relative_to(dest / lab))
                       for lab in LABELS for p in (dest / lab).rglob("*")
                       if p.is_file() and p.parent.name in
                       ("sim", "view", "tests", "tools", "data", "other")}
            real_buckets = {Path(x).parent.name for x in on_disk}
            real_suffixes = {Path(x).suffix for x in on_disk}
            expect(f"pack-labels-readable[{a.id}]", bool(on_disk),
                   f"no bucket/NN labels found on disk for aspect {a.id!r}; check 5 "
                   f"would pass vacuously")
            brief = field._brief(a, "g9_probe", None, knowingly_truncated=False)
            examples = path_examples(brief)
            expect(f"brief-shows-an-example[{a.id}]", bool(examples),
                   f"the brief for {a.id!r} shows no pack-path example, so a judge is "
                   f"told to cite by pack path with nothing to pattern-match")
            for ex in sorted(examples):
                expect(f"example-bucket-is-real[{a.id}:{ex}]",
                       Path(ex).parent.name in real_buckets,
                       f"the brief cites {ex!r} but the packer's buckets here are "
                       f"{sorted(real_buckets)}")
                suf = Path(ex).suffix
                if a.blind_language:
                    expect(f"example-suffix-is-packed[{a.id}:{ex}]",
                           suf in real_suffixes,
                           f"the brief cites {ex!r} but the suffixes really written "
                           f"into this pack are {sorted(real_suffixes)}")
                else:
                    expect(f"example-suffix-blind-safe[{a.id}:{ex}]", suf == "",
                           f"aspect {a.id!r} does not blind extensions, so the eight "
                           f"submissions carry four different real suffixes. The brief "
                           f"is ONE document for the whole field: an example ending "
                           f"{suf!r} either names an arm or names a file no judge has")

        # -------------------------------------------------------------------
        # 6. MUTANTS. Each removes a mechanism a check above names; each must turn
        #    a specific check red.
        # -------------------------------------------------------------------
        # The BLIND code shape, because it is the one whose brief makes the most claims
        # about the packer: the `.src` labels and the rebuilt CHANGED.txt are both its.
        a0, dest0, m0 = packs[("code", True)]
        HISTORICAL = ("NOTE: the pack is filled until a size budget runs out, so it "
                      "may not contain every file the author wrote - judge what is "
                      "here and do not infer that an absent concern was neglected. ")

        keep_blurb = dict(field.EVIDENCE_BLURB)
        field.EVIDENCE_BLURB["code"] = HISTORICAL + keep_blurb["code"]
        try:
            mutant_hits = {n: caution_hits(c)
                           for n, c in present_tense_claims().items()
                           if caution_hits(c)}
            mutant_in_brief = caution_hits(
                judge_facing_texts(a0, m0, dest0)["BRIEF.md"])
        finally:
            field.EVIDENCE_BLURB.clear()
            field.EVIDENCE_BLURB.update(keep_blurb)
        expect("mutant-historical-sentence", bool(mutant_hits) and bool(mutant_in_brief),
               f"restoring the 2026-08-22 sentence into EVIDENCE_BLURB['code'] left "
               f"check 4 green (claims flagged: {mutant_hits}, brief hits: "
               f"{mutant_in_brief}), so check 4 cannot fail and measures nothing")

        # MUTANT for CHECK 2. A blurb naming an artifact the packer never writes is the
        # `EVIDENCE_BLURB` defect pointing the other way: the judge is told to open
        # something that is not there and reports its absence as a fact about the
        # submission.
        keep_blurb = dict(field.EVIDENCE_BLURB)
        field.EVIDENCE_BLURB["frames"] = keep_blurb["frames"] + " See `NOTES.txt` too."
        try:
            _a, fdest, _m = packs[next(k for k in packs
                                       if "frames" in k[0].split("+"))]
            phantom = [art for art in artifacts_named(field.EVIDENCE_BLURB["frames"])
                       if any(not (fdest / lab / art.rstrip("/")).exists()
                              for lab in LABELS)]
        finally:
            field.EVIDENCE_BLURB.clear()
            field.EVIDENCE_BLURB.update(keep_blurb)
        expect("mutant-blurb-names-an-artifact-that-is-not-packed", bool(phantom),
               f"adding a backticked filename no pack contains left check 2 green "
               f"(phantoms found: {phantom}), so it cannot fail")

        # MUTANT for CHECK 5. A real suffix in the non-blind brief's pack-path example.
        # One brief serves 8 submissions from 4 stacks, so any real suffix names an arm.
        keep_ex = dict(field.PACK_PATH_EXAMPLE)
        field.PACK_PATH_EXAMPLE[False] = "`sim/03.gd`"
        try:
            plain = next(a for a in CODE_ASPECTS if not a.blind_language)
            suffixed = [e for e in path_examples(field._brief(plain, "g9_probe", None))
                        if Path(e).suffix]
        finally:
            field.PACK_PATH_EXAMPLE.clear()
            field.PACK_PATH_EXAMPLE.update(keep_ex)
        expect("mutant-non-blind-example-carries-a-real-suffix", bool(suffixed),
               f"giving the non-blind pack-path example a real suffix left check 5 "
               f"green (suffixed examples: {suffixed}), so it cannot fail")

        keep_note = dict(field.COMPLETENESS_NOTE)
        field.COMPLETENESS_NOTE[True] = keep_note[False]
        try:
            collapsed = (field.COMPLETENESS_NOTE[True] ==
                         field.COMPLETENESS_NOTE[False])
            trunc_text = field._brief(a0, "g9_probe", None, knowingly_truncated=True)
            collapsed_hits = caution_hits(trunc_text)
        finally:
            field.COMPLETENESS_NOTE.clear()
            field.COMPLETENESS_NOTE.update(keep_note)
        expect("mutant-collapsed-notes", collapsed and not collapsed_hits,
               "collapsing the two completeness notes into one still produced a "
               "cautioning brief for a truncated pack, so the two states are not "
               "actually distinguished by the text")

        # The third mutant, for check 3b: restore the `claude -p` prompt to the constant
        # it was, which is the defect this file found rather than one it was written for.
        keep_prompt = dict(field.JUDGE_PROMPT)
        field.JUDGE_PROMPT[True] = keep_prompt[False]
        try:
            prompt_collapsed = (field.judge_prompt(True) == field.judge_prompt(False))
        finally:
            field.JUDGE_PROMPT.clear()
            field.JUDGE_PROMPT.update(keep_prompt)
        expect("mutant-constant-judge-prompt", prompt_collapsed,
               "making JUDGE_PROMPT state-independent did not collapse "
               "judge_prompt(True) onto judge_prompt(False), so check 3b is not reading "
               "the constant it claims to read")

        # -------------------------------------------------------------------
        # 7. VARIANT (rule 15). A field that really is truncated, through the real
        #    packer. `dropped=4` is a STORED number: no mutant can manufacture it,
        #    and it is the only input that reaches the `allow_truncated` branch.
        # -------------------------------------------------------------------
        trunc_run = stored_run(root / "t", dropped=4)
        expect("variant-fixture-is-truncated",
               measured_incomplete(trunc_run, "g9_probe"),
               "the truncated fixture measures as complete, so the variant below "
               "exercises the same branch as the baseline")

        refused = None
        try:
            build(trunc_run, a0, root / "pack-trunc-refused")
        except RuntimeError as e:
            refused = str(e)
        expect("variant-refuses-without-the-escape", refused is not None,
               "build_pack accepted a field with a non-zero drop count and no "
               "--allow-truncated; the #69 return gate is not firing, and everything "
               "below tests a state the harness would never reach")

        mt = build(trunc_run, a0, root / "pack-trunc", allow_truncated=True)
        expect("variant-stamps-the-pack", mt.get("knowingly_truncated") is True,
               f"a deliberately truncated pack recorded "
               f"knowingly_truncated={mt.get('knowingly_truncated')!r}, so the brief "
               f"has nothing to key on")
        for where, text in sorted(
                judge_facing_texts(a0, mt, root / "pack-trunc").items()):
            if where in STATES_THE_CLAIM:
                expect(f"variant-cautions[{where}]", bool(caution_hits(text)),
                       f"{where} for a KNOWINGLY TRUNCATED pack carries no caution: the "
                       f"judge is told the evidence is complete when files really were "
                       f"dropped. That is the #62 direction of the same defect")
            expect(f"variant-drops-the-complete-claim[{where}]",
                   field.COMPLETENESS_NOTE[False] not in text,
                   f"{where} asserts the pack is complete AND that it is truncated")

        # -------------------------------------------------------------------
        # 8. FAIL-CLOSED. Deleting the completeness statement must be red.
        # -------------------------------------------------------------------
        keep_note = dict(field.COMPLETENESS_NOTE)
        field.COMPLETENESS_NOTE[False] = ""
        try:
            silent = field._brief(a0, "g9_probe", None, knowingly_truncated=False)
            still_stated = keep_note[False] in silent
        finally:
            field.COMPLETENESS_NOTE.clear()
            field.COMPLETENESS_NOTE.update(keep_note)
        expect("fail-closed-on-a-deleted-claim", not still_stated,
               "emptying COMPLETENESS_NOTE[False] left the claim in the brief, so the "
               "brief is not built from the constant this file checks")

        # -------------------------------------------------------------------
        # 9. A PACK THAT DOES NOT RECORD ITS STATE IS REFUSED, not assumed complete.
        #    `mapping.get(...)` reads a missing key as falsy, which would assert
        #    completeness about a pack nothing on disk describes - #62's direction
        #    (rule 7). Both directions, and the positive one is the invariant that
        #    every pack the packer writes carries the key.
        # -------------------------------------------------------------------
        for key, (_a, dest, _m) in sorted(packs.items()):
            rec = json.loads(field.mapping_path(dest).read_text())
            expect(f"packer-records-its-state{list(key)}",
                   "knowingly_truncated" in rec,
                   f"build_pack wrote a MAPPING with no `knowingly_truncated` for "
                   f"sees={key[0]!r} blind={key[1]}, so run_field will refuse every "
                   f"pack and check 9's negative case is not a distinguishing test")

        # The MAPPING lives OUTSIDE the pack - that is the whole point of `mapping_path`
        # (#32) - so copytree does not bring it and it has to be placed by name.
        stripped = root / "pack-no-state"
        shutil.copytree(dest0, stripped)
        shutil.copy(field.mapping_path(dest0), field.mapping_path(stripped))
        rec = json.loads(field.mapping_path(stripped).read_text())
        rec.pop("knowingly_truncated")
        field.mapping_path(stripped).write_text(json.dumps(rec, indent=2))
        res = field.run_field(stripped, a0.id)
        expect("refuses-a-pack-with-no-recorded-state",
               res.get("usable") is False and "knowingly_truncated" in
               (res.get("error") or ""),
               f"run_field returned {str(res)[:160]!r} for a pack whose MAPPING does "
               f"not say whether it is complete; it must refuse rather than let the "
               f"brief guess")

        # -------------------------------------------------------------------
        # 10. EVERY REFUSAL IS A STORED RECORD, including the one for an aspect id
        #     this module does not define. `field.py run` takes `--aspect` with no
        #     `choices`, so an unknown id used to reach `ASPECTS[aspect_id]` and raise
        #     KeyError - an uncaught traceback where every sibling refusal is a
        #     `usable: False` saying what was wrong. The positive half is next to it:
        #     a REAL aspect must not be refused for this reason, or the check would
        #     pass by refusing everything.
        #
        #     Both calls go to `stripped`, the pack with no recorded completeness
        #     state, so each one stops at a guard rather than spawning a judge. A
        #     positive half aimed at a healthy pack would run the model.
        # -------------------------------------------------------------------
        res = field.run_field(stripped, "no_such_aspect")
        expect("refuses-an-unknown-aspect-id-as-a-record",
               res.get("usable") is False and "is not an aspect" in
               (res.get("error") or ""),
               f"run_field returned {str(res)[:160]!r} for an aspect id aspects.py "
               f"does not define; it must refuse in the same shape as its siblings "
               f"rather than raising")
        res = field.run_field(stripped, a0.id)
        expect("a-real-aspect-is-not-refused-as-unknown",
               "is not an aspect" not in (res.get("error") or ""),
               f"run_field refused the real aspect {a0.id!r} as unknown, so check 10 "
               f"passes by refusing everything")

        # -------------------------------------------------------------------
        # 11. THE SCENE STATEMENT. `SCENE.md` is the one judge-facing text whose
        #     claim is about the TASK rather than about the packer, so checks 3 and
        #     3b have nothing to read in it. These are its state tests.
        # -------------------------------------------------------------------
        scene_runs = {s: stored_run(root / f"sc-{s}", game=s)
                      for s in sorted(scene_prompts.SCENES)}
        scene_packs: dict[tuple[str, str, bool], tuple[aspects.Aspect, Path, dict]] = {}
        for sid in aspects.SCENE_ASPECTS:
            a = aspects.ASPECTS[sid]
            for game, srun in scene_runs.items():
                key = (game, a.sees, a.blind_language)
                if key in scene_packs:
                    continue
                dest = root / (f"scenepack-{game}-{a.sees.replace('+', '-')}"
                               f"-blind{int(a.blind_language)}")
                scene_packs[key] = (a, dest, build(srun, a, dest, game=game))

        expect("scene-fixture-builds-both-scenes",
               len({k[0] for k in scene_packs}) == len(scene_prompts.SCENES),
               f"the fixture built packs for {sorted({k[0] for k in scene_packs})} of "
               f"{sorted(scene_prompts.SCENES)}; check 11e reads one scene and cannot "
               f"see a statement that is the same for every one of them")

        # EVERY scene the suites define has a statement, or the packer refuses a field
        # nobody could have known was unstatable until they tried to judge it.
        expect("every-scene-has-a-statement",
               set(field.SCENE_STATEMENTS) == set(scene_prompts.SCENES),
               f"field.SCENE_STATEMENTS states {sorted(field.SCENE_STATEMENTS)} and "
               f"eval/suites/scene_prompts.py defines {sorted(scene_prompts.SCENES)}; a "
               f"scene with no statement cannot be packed at all")

        for (game, sees, blind), (a, dest, m) in sorted(scene_packs.items()):
            tag = f"{game}:{sees}:blind={blind}"
            on_disk = dest / field.SCENE_STATEMENT_FILE
            expect(f"scene-pack-carries-the-statement[{tag}]", on_disk.is_file(),
                   f"a pack built for scene {game!r} has no "
                   f"{field.SCENE_STATEMENT_FILE}; every brief for a scene aspect tells "
                   f"the judge to read it, so this is a brief pointing at nothing")
            if not on_disk.is_file():
                continue
            text = on_disk.read_text(encoding="utf-8")
            expect(f"statement-on-disk-is-the-constant[{tag}]",
                   text == field.scene_statement(game),
                   f"{field.SCENE_STATEMENT_FILE} on disk is not what "
                   f"field.scene_statement({game!r}) returns, so the text this file "
                   f"checks is not the text the judge is handed")
            # A FUNCTION OF THE TASK. This is `SCENE.md`'s analogue of check 3b: a
            # statement identical for both scenes would be describing neither.
            other = next(s for s in scene_prompts.SCENES if s != game)
            expect(f"statement-varies-by-scene[{tag}]",
                   field.SCENE_STATEMENTS[other] not in text,
                   f"the pack for {game!r} carries the body of {other!r}, so the "
                   f"statement is not a function of the scene it claims to state")
            expect(f"statement-is-judge-facing-text[{tag}]",
                   judge_facing_texts(a, m, dest).get(
                       field.SCENE_STATEMENT_FILE) == text,
                   f"judge_facing_texts does not return "
                   f"{field.SCENE_STATEMENT_FILE} for scene aspect {a.id!r}, so none of "
                   f"the resource-wide checks in this file read it")
            # NO CRITERION VOCABULARY, with the same closed lists the PROMPTS are
            # grepped against (`tools/prompt_guard.py`). A tier-3 opinion told what
            # tier 2 measures is a restatement of tier 2, not a second reading.
            hits = prompt_guard.assert_no_rubric_vocabulary({game: text})
            expect(f"statement-states-no-criterion[{tag}]", not hits,
                   f"{field.SCENE_STATEMENT_FILE} for {game!r} carries eval/SCENES.md "
                   f"criterion or threshold vocabulary: {hits[:3]}")

        # NO STACK TOKEN, through the CLI the done-condition names, in both directions.
        # A subprocess and not `check_pack_skill` directly: the exit code is what a gate
        # reads, and `--packs` is the flag an operator runs.
        vb = [sys.executable, str(HERE / "verify_blind.py"), "--packs"]
        clean_pack = next(d for (g, s, b), (_a, d, _m) in sorted(scene_packs.items())
                          if s == "frames")
        r = subprocess.run(vb + [str(clean_pack)], capture_output=True, text=True)
        expect("verify-blind-passes-a-scene-pack", r.returncode == 0,
               f"verify_blind.py --packs exited {r.returncode} on a freshly built scene "
               f"pack: {(r.stdout + r.stderr)[-400:]}")

        # MUTANT: a stack name written into the file on disk must turn that green red.
        # This one says only that `verify_blind` can fail on this file at all.
        planted = root / "scenepack-planted"
        shutil.copytree(clean_pack, planted)
        (planted / field.SCENE_STATEMENT_FILE).write_text(
            field.scene_statement("s1_parallax")
            + "\nThe scene is drawn with Bevy sprites.\n")
        r = subprocess.run(vb + [str(planted)], capture_output=True, text=True)
        expect("mutant-stack-token-in-the-statement", r.returncode == 1,
               f"verify_blind.py --packs exited {r.returncode} on a pack whose "
               f"{field.SCENE_STATEMENT_FILE} names an engine, so the gate the "
               f"statement relies on cannot fail: {(r.stdout + r.stderr)[-400:]}")

        # VARIANT (rule 15). The mutant above edits the pack AFTER the packer ran, so it
        # cannot ask the question that decides how the statement is written: does the
        # leak SURVIVE the packer? Every other piece of pack text goes through
        # `neutralise`, which would rewrite `Bevy` to `engine` and hand `verify_blind` a
        # clean file - the gate green over judge-facing text that had named an arm until
        # the harness edited it. Only a leaking statement driven through the real
        # `build_pack` can tell those apart, and no mutant can manufacture one.
        keep_stmt = dict(field.SCENE_STATEMENTS)
        field.SCENE_STATEMENTS["s1_parallax"] = (
            keep_stmt["s1_parallax"] + "\nThe scene is drawn with Bevy sprites.\n")
        leaky = root / "scenepack-leaky"
        try:
            build(scene_runs["s1_parallax"], aspects.ASPECTS["fidelity"], leaky,
                  game="s1_parallax")
            written = leaky / field.SCENE_STATEMENT_FILE
            # Absent is a THIRD value and is not "the leak was removed": it means the
            # packer wrote no statement at all, which the rows above already report.
            survived = (written.is_file()
                        and "Bevy" in written.read_text(encoding="utf-8"))
        finally:
            field.SCENE_STATEMENTS.clear()
            field.SCENE_STATEMENTS.update(keep_stmt)
        r = subprocess.run(vb + [str(leaky)], capture_output=True, text=True)
        expect("variant-a-leaking-statement-survives-the-packer",
               survived and r.returncode == 1,
               f"a statement naming an engine came out of build_pack "
               f"{'unchanged' if survived else 'REWRITTEN'} and verify_blind.py --packs "
               f"exited {r.returncode}. The statement must be written raw: laundering it "
               f"leaves the blinding gate reading text the harness has already cleaned")

        # MUTANT: the claim the scene exists to WITHHOLD, restated in the statement.
        withheld = (field.scene_statement("s2_glass")
                    + "\nThe water surface stays level while the glass tilts.\n")
        expect("mutant-criterion-in-the-statement",
               bool(prompt_guard.assert_no_rubric_vocabulary({"s2_glass": withheld})),
               "planting s2's deliberately withheld claim into the statement left the "
               "rubric-vocabulary grep green, so that check measures nothing")

        # A GAME PACK MUST NOT CARRY ONE. The other direction of "for scene fields
        # only": a statement in a game pack describes a task nobody set.
        for key, (a, dest, m) in sorted(packs.items()):
            expect(f"game-pack-carries-no-statement{list(key)}",
                   not (dest / field.SCENE_STATEMENT_FILE).exists(),
                   f"a pack built for the game fixture carries "
                   f"{field.SCENE_STATEMENT_FILE}")
            expect(f"game-brief-does-not-name-it{list(key)}",
                   field.SCENE_STATEMENT_FILE not in
                   judge_facing_texts(a, m, dest)["BRIEF.md"],
                   f"a game brief tells the judge to read "
                   f"{field.SCENE_STATEMENT_FILE}, which no game pack contains")
        # EVERY scene aspect, not every pack shape. `fidelity` and `motion` share the
        # `frames` shape, so a per-pack loop checks whichever of the two the packs dict
        # happened to store - and `fidelity` names the file in its own notes, so it would
        # pass a brief that had stopped naming it while `motion` silently did not.
        for sid in aspects.SCENE_ASPECTS:
            a = aspects.ASPECTS[sid]
            for game in sorted(scene_prompts.SCENES):
                _a, dest, m = scene_packs[(game, a.sees, a.blind_language)]
                expect(f"scene-brief-names-it[{sid}:{game}]",
                       field.SCENE_STATEMENT_FILE in
                       judge_facing_texts(a, m, dest)["BRIEF.md"],
                       f"the brief for scene aspect {sid!r} never names "
                       f"{field.SCENE_STATEMENT_FILE}, so a file the judge needs is one "
                       f"it has no reason to open")

        # WHO IS WATCHING is a function of the task class too, in both directions. A
        # scene has no player, so a scene brief saying "everything the player sees" is
        # the completeness note's defect in a new place: judge-facing text describing a
        # thing the task does not have.
        expect("audiences-still-agree",
               field.FRAMES_AUDIENCE == {"game": FRAMES_AUDIENCE_GAME,
                                         "scene": FRAMES_AUDIENCE_SCENE},
               f"field.FRAMES_AUDIENCE is {field.FRAMES_AUDIENCE} and this file expects "
               f"{{'game': {FRAMES_AUDIENCE_GAME!r}, 'scene': {FRAMES_AUDIENCE_SCENE!r}}}. "
               f"The 2 are deliberately separate statements; reconcile them here rather "
               f"than importing one from the other")
        for klass, group, expected in (
                ("game", packs, FRAMES_AUDIENCE_GAME),
                ("scene", scene_packs, FRAMES_AUDIENCE_SCENE)):
            other = (FRAMES_AUDIENCE_SCENE if klass == "game"
                     else FRAMES_AUDIENCE_GAME)
            for key, (a, dest, m) in sorted(group.items()):
                if "frames" not in a.sees.split("+"):
                    continue
                brief = judge_facing_texts(a, m, dest)["BRIEF.md"]
                expect(f"frames-audience-is-the-class[{klass}:{a.id}:{m['game']}]",
                       expected in brief and other not in brief,
                       f"the {klass} brief for {a.id!r} describes its frames' audience "
                       f"as {other!r}; a scene has no player and a game has no scene")

        # FAIL-CLOSED. A scene this module cannot state must be refused, not packed
        # without a statement - that would silently restore the aspect to reading the
        # subject out of the field, which is the narrowing the statement removed.
        unstatable = stored_run(root / "unstatable", game="s9_probe")
        refused = None
        try:
            build(unstatable, aspects.ASPECTS["fidelity"],
                  root / "pack-unstatable", game="s9_probe")
        except RuntimeError as e:
            refused = str(e)
        expect("fail-closed-on-an-unstatable-scene",
               refused is not None and "SCENE_STATEMENTS" in refused,
               f"build_pack returned {str(refused)[:160]!r} for a scene id with no "
               f"statement; it must refuse rather than hand fidelity a brief pointing "
               f"at a file that is not there")

        # AND THE SPENDER GUARDS IT TOO. `build_pack`'s refusal is on the packer; a pack
        # is built once and judged later, from a directory anything may have touched, so
        # `run_field` asks again before spending the judge invocation (rule 13). EXISTENCE
        # IS NOT THE RESOURCE: an empty file and the other scene's statement both pass a
        # presence test and both cost a field scored against the wrong subject.
        #
        # EVERY COPY HAS ITS COMPLETENESS KEY REMOVED, which is what makes these rows
        # distinguishing without ever running a judge. `run_field` asks for the statement
        # BEFORE the completeness key, so the copy that carries the RIGHT one stops at
        # the next guard and each broken copy stops at this one - four packs identical
        # but for one file, and two different refusals.
        _a0, sdest, _sm = scene_packs[("s1_parallax",
                                       aspects.ASPECTS["fidelity"].sees, False)]
        #: `bytes` are written as-is; `str` is encoded; `None` deletes the file.
        #: `undecodable` is the state `(OSError, RuntimeError)` did not cover:
        #: `read_text` raises `UnicodeDecodeError`, which is a `ValueError`, so an
        #: invalid-byte statement was a traceback where every sibling is a record.
        #
        # THE THIRD COLUMN IS WHICH REFUSAL, and it is what makes `undecodable` a test of
        # anything. `read_text` defaults to the LOCALE codec, so on a non-UTF-8 host the
        # invalid bytes would decode and the state would take the MISMATCH branch - green,
        # for a reason that has nothing to do with decoding. `field.py` reads with
        # `encoding="utf-8"` and this column asserts which branch answered.
        STATEMENT_STATES = (
            ("absent", None, "could not be read"),
            ("empty", "", "is not the statement"),
            ("undecodable", b"\xff\xfe not utf-8 \xff", "could not be read"),
            ("the other scene's", field.scene_statement("s2_glass"),
             "is not the statement"),
            ("this scene's", field.scene_statement("s1_parallax"), None),
        )
        for state, body, refusal in STATEMENT_STATES:
            copy = root / f"scenepack-statement-{state.replace(' ', '-')}"
            shutil.copytree(sdest, copy)
            # The MAPPING lives OUTSIDE the pack (#32), so copytree does not bring it.
            rec = json.loads(field.mapping_path(sdest).read_text())
            rec.pop("knowingly_truncated")
            field.mapping_path(copy).write_text(json.dumps(rec, indent=2))
            statement = copy / field.SCENE_STATEMENT_FILE
            if body is None:
                # `missing_ok`: if the packer wrote none, the rows above already say so
                # and this loop must still reach its own.
                statement.unlink(missing_ok=True)
            elif isinstance(body, bytes):
                statement.write_bytes(body)
            else:
                statement.write_text(body, encoding="utf-8")
            err = field.run_field(copy, "fidelity").get("error") or ""
            named = field.SCENE_STATEMENT_FILE in err
            if state == "this scene's":
                expect("a-scene-pack-with-the-right-statement-is-not-refused-for-it",
                       not named and "knowingly_truncated" in err,
                       f"run_field refused a scene pack carrying the correct "
                       f"{field.SCENE_STATEMENT_FILE}, or never reached the next guard: "
                       f"{err[:200]!r}. The rows above would pass by refusing every "
                       f"scene pack")
            else:
                expect(f"run-field-refuses-a-statement-that-is-{state}",
                       named and refusal in err,
                       f"run_field returned {err[:200]!r} for a scene pack whose "
                       f"{field.SCENE_STATEMENT_FILE} is {state}; it must refuse, and "
                       f"the refusal must be the {refusal!r} one - the brief it is "
                       f"about to write tells the judge to read that file first, and a "
                       f"wrong subject is worse than none")

        # WHAT A ROUND RECORDS ABOUT ITS SUBJECT, on the path that really holds it.
        # `brief_sha256` cannot answer the question: the brief NAMES `SCENE.md` and does
        # not contain it, so two rounds with the same brief hash can have been read
        # against two different statements - what #83 could not answer about what a judge
        # had seen.
        #
        # DRIVEN THROUGH `run_field` WITH THE JUDGE STUBBED, not by calling `_provenance`.
        # A direct call proves the function copies its argument and nothing more: it stays
        # green if `run_field` never passes the digest, hashes something else, or drops
        # the field. The stub is `field.subprocess`, replaced for the duration by an
        # object exposing the two names `run_field` uses - so the guards, the brief write
        # and the whole record-assembling tail all execute, and the round costs nothing.
        # `JUDGING.md` has the precedent: the model call is stubbed so both arms run.
        VERDICT = {"submissions": [{"label": lab, "score": 2, "rank": 1,
                                    "evidence": "e" * 60} for lab in LABELS],
                   "best": "A", "worst": "B", "field_note": "stubbed"}

        class _StubJudge:
            """`field.subprocess`, for a round that must not spend anything."""
            TimeoutExpired = subprocess.TimeoutExpired

            def __init__(self) -> None:
                self.calls: list[list[str]] = []

            def run(self, argv, **kw):
                self.calls.append(argv)
                line = json.dumps({"type": "result", "structured_output": VERDICT,
                                   "total_cost_usd": 0.0})
                return subprocess.CompletedProcess(argv, 0, line + "\n", "")

        for game, aid in (("s1_parallax", "fidelity"), ("g9_probe", "ux")):
            a = aspects.ASPECTS[aid]
            scene = aspects.task_class(game) == "scene"
            src = scene_packs[(game, a.sees, a.blind_language)][1] if scene else \
                packs[(a.sees, a.blind_language)][1]
            copy = root / f"stubbed-round-{game}"
            shutil.copytree(src, copy)
            shutil.copy(field.mapping_path(src), field.mapping_path(copy))
            # The expected digest is computed HERE from the BYTES ON DISK - the thing the
            # guard validated - rather than from `field.scene_statement`. That is the
            # second, independent statement of the fact (rule 12's corollary): a
            # `run_field` that hashed the constant instead of the file would agree with a
            # constant-derived expectation and disagree with this one.
            packed = copy / field.SCENE_STATEMENT_FILE
            want = (hashlib.sha256(packed.read_bytes()).hexdigest()[:16]
                    if scene and packed.is_file() else None)
            stub = _StubJudge()
            real, field.subprocess = field.subprocess, stub
            try:
                rec = field.run_field(copy, aid)
            finally:
                field.subprocess = real
            expect(f"stubbed-round-is-usable[{game}]",
                   rec.get("usable") is True and len(stub.calls) == 1,
                   f"the stubbed round for {game!r} returned "
                   f"usable={rec.get('usable')!r} after {len(stub.calls)} judge "
                   f"invocation(s): {str(rec.get('error'))[:200]!r}. The row below would "
                   f"be reading a refusal rather than a record")
            expect(f"provenance-records-the-subject[{game}]",
                   (rec.get("provenance") or {}).get("scene_statement_sha256") == want,
                   f"a {aspects.task_class(game)} round stored "
                   f"scene_statement_sha256="
                   f"{(rec.get('provenance') or {}).get('scene_statement_sha256')!r} "
                   f"against the digest of the {field.SCENE_STATEMENT_FILE} it "
                   f"validated, {want!r}; nothing else in the record says which "
                   f"statement the strips were scored against")

        # -------------------------------------------------------------------
        # 13. THE STORED-ROUND CENSUS, against a tree whose answer is written down
        #     before it runs. `--stored-rounds` reads a gitignored directory, so no
        #     gate has ever been able to see it, and the table it produces in
        #     `eval/RUNS.md` went stale on 3 rows of 4 (task 132). What went stale
        #     was not the digits but the POPULATION sentences beside them - which
        #     directories the hashed rounds are in, and what pack state they read -
        #     and those were never printed at all, so a reader had to re-derive them
        #     by hand and nobody re-did it when 4 more rounds landed.
        #
        #     The expectations here are written out as literals rather than computed
        #     from the census (rule 12's corollary): a census that mis-keys its
        #     population would agree with an expectation derived from itself.
        # -------------------------------------------------------------------
        census_root = census_fixture(root / "census")
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = stored_rounds_census(census_root)
        out = buf.getvalue()
        expect("census-fixture-runs", rc == 0,
               f"the census returned {rc} over the fixture tree, so every row below "
               f"would be asserting against an error path")
        for label, want in (("stored judge rounds", 9), ("code-seeing", 8),
                            ("carrying provenance.brief_sha256", 5),
                            ("NO brief hash (unassessable)", 3)):
            line = next((ln for ln in out.splitlines() if label in ln), "")
            got = line.rsplit(":", 1)[-1].strip()
            expect(f"census-counts[{label}]", got == str(want),
                   f"the fixture holds {want} for {label!r} by construction - 2 hashed "
                   f"architecture rounds in `alpha`, 2 hashed idiomatic rounds nested 2 "
                   f"deep, 3 hash-less code rounds in `beta`, 1 hashed audio round, 1 "
                   f"hashed code round naming a dead aspect in `delta`, and 2 files "
                   f"that are not rounds at all - but the census printed "
                   f"{got!r} on {line.strip()!r}")
        # The population block, which is what the RUNS.md row states in prose. Each
        # tuple is (directory, aspect, knowingly_truncated, n, same, moved,
        # unbuildable) and every value is a property of the fixture, stated here and
        # nowhere else.
        pop_rows = (("alpha", "architecture", "False", 2, 2, 0, 0),
                    ("alpha/nested/deeper", "idiomatic", "True", 2, 1, 1, 0),
                    ("delta", "architecture_v0", "False", 1, 0, 0, 1))
        for dirname, aid, kt, n, same, moved, dead in pop_rows:
            hit = [ln for ln in out.splitlines()
                   if ln.split()[:1] == [dirname] and aid in ln]
            fields = hit[0].split() if hit else []
            expect(f"census-population[{dirname}:{aid}]",
                   len(hit) == 1 and fields[1:] == [aid, kt, str(n), str(same),
                                                    str(moved), str(dead)],
                   f"the {n} hashed {aid} round(s) under {dirname!r} were stored with "
                   f"knowingly_truncated={kt} and rebuild {same} same / {moved} moved "
                   f"/ {dead} unbuildable against this checkout, but the census printed "
                   f"{hit!r}. A row that names no directory and no pack state cannot "
                   f"tell a reader whether the population it counted is still the one "
                   f"the prose describes")
        # THE POPULATION MUST ACCOUNT FOR EVERY ROUND THE HEADLINE COUNTS, read off the
        # CENSUS'S OWN OUTPUT rather than off the literals above - those are the second,
        # independent statement of the fact and summing them would only prove they add
        # up (rule 12's corollary). Every printed row's n must equal same + moved +
        # unbuildable, and the rows must sum to the hashed-code headline. The `delta`
        # round is the one that would go missing.
        lines = out.splitlines()
        head = next(i for i, ln in enumerate(lines) if "the hashed CODE rounds" in ln)
        body = itertools.takewhile(bool, lines[head + 2:])
        printed = [ln.split()[-4:] for ln in body]
        totals = [[int(v) for v in row] for row in printed]
        # The headline is the census's own, not a literal - it is asserted against one
        # above, and what THIS row asks is whether the two halves of one output agree.
        headline = int(next(ln for ln in lines
                            if "carrying provenance.brief_sha256" in ln).rsplit(":")[-1])
        expect("census-population-accounts-for-every-hashed-code-round",
               bool(totals) and sum(n for n, _s, _m, _u in totals) == headline
               and all(n == s + m + u for n, s, m, u in totals),
               f"the census printed population rows {printed!r}; their `n` must sum to "
               f"the {headline} hashed code rounds its own headline counts, and each "
               f"row's `n` must equal same + moved + unbuildable. A population that "
               f"omits a record its own headline counts is the defect this block exists "
               f"to end")
        expect("census-population-excludes-a-non-code-round",
               "gamma" not in out,
               f"the fixture's hashed AUDIO round is in `gamma`, and the population "
               f"block is the population of the CODE row - pooling it would restate "
               f"task 94's defect, two denominators printed as one:\n{out}")
        expect("census-names-the-unassessable-directories",
               any(ln.split()[:2] == ["beta", "3"] for ln in out.splitlines()),
               f"the 3 hash-less code rounds are all in `beta`; nothing in the output "
               f"says where the unassessable rounds are, so the row that calls them "
               f"permanently unassessable names no population:\n{out}")

    if FAILS:
        print(f"BLURB SELFTEST: {len(FAILS)} unmet expectation(s)\n")
        for f in FAILS:
            print(f"  FAIL {f}")
        return 1
    print("BLURB SELFTEST: every claim in the pack's judge-facing text matches what it "
          "claims about - the packer in both completeness states, the scene for the "
          "scene statement - with mutants, a variant and a fail-closed case for each.")
    return 0


#: `sees` for a round stored before `provenance` existed. Read off the aspect, which is
#: the only thing those records carry. Kept beside the census that uses it rather than
#: imported from `aspects`, so that a future `sees` change shows up here as a mismatch
#: rather than silently reclassifying 63 stored rounds.
_SEES_BY_ASPECT = {"idiomatic": "code", "architecture": "code",
                   "fun": "frames+telemetry", "fun_frames": "frames",
                   "audio": "audio", "ux": "frames"}


def stored_rounds_census(runs_root: Path) -> int:
    """WHICH STORED ROUNDS DEMONSTRABLY READ A GIVEN BRIEF, and which cannot be asked.

    THE PRODUCER for the table in `eval/RUNS.md` under "THE CODE JUDGE WAS TOLD ITS PACK
    MIGHT BE TRUNCATED WHEN IT WAS NOT". Do not quote those figures from memory; run this.

    It does not infer from a date. A round that stored `provenance.brief_sha256` has its
    brief REBUILT from the aspect, game and geometry it recorded, and the two hashes are
    compared - so "this round read that text" is an identity, not a guess. A round with no
    hash is reported as **unassessable**, which is a third value and not a clean bill:
    nothing on disk says what brief it was shown (the #83 shape).

    IT PRINTS THE POPULATION, not only the counts, and that is the part task 132 bought.
    The counts drifting is easy to notice; what actually went stale was the prose beside
    them - *all in `wg-aspect-reliability`, all `knowingly_truncated: false`* - written
    when that was true of all 10 hashed code rounds and left standing when a later sweep
    put 4 more in a different directory. **A quantity with no producer goes stale forever,
    and so does a POPULATION with no producer**, which is the same rule one level down.
    So the census names the directory and the recorded pack state of every code round it
    counts, hashed and unassessable alike.

    Run it against the MAIN CHECKOUT's `eval/runs`; the path is gitignored, so a worktree's
    copy is empty and this would print a confident set of zeros.
    """
    if not runs_root.is_dir():
        print(f"runs root does not exist: {runs_root}", file=sys.stderr)
        return 2
    rounds = []
    for p in sorted(runs_root.rglob("*.json")):
        try:
            d = json.loads(p.read_text())
        except (OSError, json.JSONDecodeError, UnicodeDecodeError):
            continue
        if not (isinstance(d, dict) and "aspect" in d and "order_seed" in d):
            continue
        prov = d.get("provenance") or {}
        aid = d["aspect"]
        rounds.append((p, aid, prov.get("sees") or _SEES_BY_ASPECT.get(aid), prov, d))
    if not rounds:
        print(f"no judge rounds under {runs_root} - UNMEASURED, not clean",
              file=sys.stderr)
        return 2

    code = [r for r in rounds if "code" in (r[2] or "").split("+")]
    # EVERY hashed round, not only the code ones. A change meant to touch the code brief
    # alone is a claim about the OTHER aspects too, and the only way to see that it held
    # is to rebuild theirs as well - rule 8, enumerated from the artifacts rather than
    # from what the edit intended.
    hashed = [r for r in rounds if (r[3] or {}).get("brief_sha256")]
    per_aspect: dict[str, dict[str, Any]] = {}
    # THE POPULATION of the code row, keyed on the two things the prose beside it
    # claims: WHERE the rounds are and WHAT PACK STATE they were told about. Both were
    # stated in `eval/RUNS.md` and produced by nothing, so when a later sweep added
    # rounds in a second directory the sentence went on describing the first one and
    # no command disagreed (task 132).
    population: dict[tuple[str, str, bool], dict[str, int]] = {}
    unbuildable: list[str] = []
    for p, aid, sees, prov, d in hashed:
        a = aspects.ASPECTS.get(aid)
        if a is None:
            unbuildable.append(p.name)
            verdict = "unbuildable"
        else:
            txt = field._brief(a, prov.get("game") or d.get("game"),
                               prov.get("capture_geometry"),
                               knowingly_truncated=bool(prov.get("knowingly_truncated")))
            h = hashlib.sha256(txt.encode()).hexdigest()[:16]
            row = per_aspect.setdefault(aid, {"sees": sees, "n": 0, "same": 0,
                                              "moved": 0, "chars": set()})
            row["n"] += 1
            verdict = "same" if h == prov["brief_sha256"] else "moved"
            row[verdict] += 1
            row["chars"].add((prov.get("brief_chars"), len(txt)))
        if "code" in (sees or "").split("+"):
            # The FULL relative parent, not the top-level directory: a run directory is
            # not always a child of the root, and the rounds this row is about really
            # do sit in a dated sub-directory of one (#127).
            #
            # A ROUND WHOSE ASPECT NO LONGER EXISTS GETS A ROW TOO. Its brief cannot be
            # rebuilt, so it is neither `same` nor `moved` - but it IS one of the rounds
            # the headline counts, and a population that omits a record its own total
            # includes is the defect this block was written to end. `n` is the sum of
            # the three verdict columns, which is what makes that checkable rather than
            # promised.
            key = (str(p.parent.relative_to(runs_root)), aid,
                   bool(prov.get("knowingly_truncated")))
            pop = population.setdefault(key, {"n": 0, "same": 0, "moved": 0,
                                              "unbuildable": 0})
            pop["n"] += 1
            pop[verdict] += 1
    unassessable: dict[str, int] = {}
    for p, _aid, _sees, prov, _d in code:
        if not (prov or {}).get("brief_sha256"):
            key = str(p.parent.relative_to(runs_root))
            unassessable[key] = unassessable.get(key, 0) + 1

    print(f"stored judge rounds under {runs_root}          : {len(rounds)}")
    print(f"  code-seeing (idiomatic, architecture)        : {len(code)}")
    print(f"  code rounds carrying provenance.brief_sha256 : "
          f"{sum(1 for r in code if (r[3] or {}).get('brief_sha256'))}")
    print(f"  code rounds with NO brief hash (unassessable): "
          f"{len(code) - sum(1 for r in code if (r[3] or {}).get('brief_sha256'))}")
    if unbuildable:
        print(f"  rounds naming an aspect that no longer exists: {unbuildable}")
    print()
    print("  stored hash vs the brief this checkout builds, per aspect:")
    print(f"    {'aspect':14s} {'sees':17s} {'n':>3s} {'same':>5s} {'moved':>6s}  chars")
    for aid, row in sorted(per_aspect.items()):
        chars = ", ".join(f"{a}->{b}" for a, b in sorted(row["chars"]))
        print(f"    {aid:14s} {str(row['sees']):17s} {row['n']:3d} {row['same']:5d} "
              f"{row['moved']:6d}  {chars}")
    width = max([len(k) for k in list(unassessable) + [k[0] for k in population]]
                + [len("directory")])
    print()
    print("  the hashed CODE rounds - the population the prose beside the table "
          "describes:")
    print(f"    {'directory':{width}s} {'aspect':14s} {'knowingly_truncated':21s} "
          f"{'n':>3s} {'same':>5s} {'moved':>6s} {'unbuildable':>12s}")
    for (where, aid, kt), pop in sorted(population.items()):
        print(f"    {where:{width}s} {aid:14s} {str(kt):21s} {pop['n']:3d} "
              f"{pop['same']:5d} {pop['moved']:6d} {pop['unbuildable']:12d}")
    print()
    print("  the code rounds with NO brief hash, by directory - unassessable, not clean:")
    for where, n in sorted(unassessable.items()):
        print(f"    {where:{width}s} {n:3d}")
    return 0


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--stored-rounds", type=Path, metavar="RUNS_ROOT",
                    help="instead of the selftest, census which stored judge rounds "
                         "demonstrably read which brief. Point it at the MAIN "
                         "checkout's eval/runs - a worktree's is gitignored and empty.")
    args = ap.parse_args()
    if args.stored_rounds:
        raise SystemExit(stored_rounds_census(args.stored_rounds))
    raise SystemExit(main())
