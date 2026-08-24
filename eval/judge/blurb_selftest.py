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
  6. MUTANTS. The historical sentence restored; the two notes collapsed into one.
  7. VARIANT (rule 15). A field that really is knowingly truncated, built by the real
     `build_pack(allow_truncated=True)` over a fixture whose stored drop count is
     non-zero. A mutant removes a mechanism; only a variant can manufacture the input
     the mechanism exists for.
  8. FAIL-CLOSED. Deleting the completeness statement altogether must be red, not quiet -
     otherwise "remove the sentence" is a repair that leaves the judge told nothing.

Run:  python3 judge/blurb_selftest.py          # unpiped: exit 1 means a claim has drifted
"""
from __future__ import annotations

import json
import re
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import aspects  # noqa: E402
import field  # noqa: E402

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
    """Every text in a pack that speaks to the judge about the packer.

    Written as the resource rather than as a list of the two constants that were wrong,
    because a rule whose trigger is an enumeration has to be re-derived by the first
    reader who meets an item that is not on it. A third judge-facing text is covered the
    moment it is added here.
    """
    skill = pack / ".claude" / "skills" / "sampling-code" / "SKILL.md"
    kt = bool(mapping.get("knowingly_truncated"))
    return {
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


#: WHICH texts STATE the completeness claim, as opposed to merely not contradicting it.
#: BRIEF.md is where a judge is told what its evidence is; the sampling skill is read
#: exactly when it is deciding how much to open. The `claude -p` prompt is a one-paragraph
#: instruction and repeating the sentence there would be a third copy of a claim, which is
#: how #100 recurred - so it is held to the weaker rule (it must not contradict, and it
#: must be a function of the state) and not to the stronger one.
STATES_THE_CLAIM = ("BRIEF.md", "SKILL.md")


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


CODE_ASPECTS = [a for a in aspects.ASPECTS.values() if "code" in a.sees.split("+")]
LABELS = list(field.LABELS)


def build(run: Path, aspect: aspects.Aspect, dest: Path, **kw) -> dict:
    return field.build_pack(run, "g9_probe", dest, 7, sees=aspect.sees,
                            blind_language=aspect.blind_language, **kw)


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

    if FAILS:
        print(f"BLURB SELFTEST: {len(FAILS)} unmet expectation(s)\n")
        for f in FAILS:
            print(f"  FAIL {f}")
        return 1
    print("BLURB SELFTEST: every claim in the pack's judge-facing text matches the "
          "packer, in both completeness states, with mutants and a variant.")
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

    THE PRODUCER for the table in `eval/RUNS.md` under "EVERY STORED CODE ROUND WAS TOLD
    ITS PACK MIGHT BE TRUNCATED". Do not quote those figures from memory; run this.

    It does not infer from a date. A round that stored `provenance.brief_sha256` has its
    brief REBUILT from the aspect, game and geometry it recorded, and the two hashes are
    compared - so "this round read that text" is an identity, not a guess. A round with no
    hash is reported as **unassessable**, which is a third value and not a clean bill:
    nothing on disk says what brief it was shown (the #83 shape).

    Run it against the MAIN CHECKOUT's `eval/runs`; the path is gitignored, so a worktree's
    copy is empty and this would print a confident set of zeros.
    """
    import hashlib
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
    unbuildable: list[str] = []
    for p, aid, sees, prov, d in hashed:
        a = aspects.ASPECTS.get(aid)
        if a is None:
            unbuildable.append(p.name)
            continue
        txt = field._brief(a, prov.get("game") or d.get("game"),
                           prov.get("capture_geometry"),
                           knowingly_truncated=bool(prov.get("knowingly_truncated")))
        h = hashlib.sha256(txt.encode()).hexdigest()[:16]
        row = per_aspect.setdefault(aid, {"sees": sees, "n": 0, "same": 0, "moved": 0,
                                          "chars": set()})
        row["n"] += 1
        row["same" if h == prov["brief_sha256"] else "moved"] += 1
        row["chars"].add((prov.get("brief_chars"), len(txt)))

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
