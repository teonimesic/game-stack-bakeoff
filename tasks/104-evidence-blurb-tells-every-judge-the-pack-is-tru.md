---
id: 104
title: EVIDENCE_BLURB tells every judge the pack is truncated by a size budget that was removed on 2026-08-22
status: done
priority: 3
refs: 'eval/judge/field.py EVIDENCE_BLURB, eval/FINDINGS #69, tasks/95'
done_when: the sentence is either corrected to what is true now or removed, with a note in eval/RUNS.md recording that every stored round read the stale text; and a check exists that would fail if a claim in EVIDENCE_BLURB stops matching the packer - a sentence about the packer that no code reads is how this one survived a year
established_by: 'field.COMPLETENESS_NOTE now selects the claim from the pack state, and judge/blurb_selftest.py asserts every judge-facing claim against a really-built pack. THE TICKET''S PREMISE WAS WRONG TWICE. Not every stored round read the sentence: it is in EVIDENCE_BLURB code, which only reaches an aspect whose sees includes code - 36 of 93 stored rounds. Of those 36 only 10 recorded a provenance.brief_sha256, all 10 rebuild BYTE-IDENTICALLY to the pre-repair brief so they demonstrably read it, and the other 26 stored no hash and are UNASSESSABLE, not clean (the FINDINGS 83 shape). Producer, run it rather than quoting: python3 eval/judge/blurb_selftest.py --stored-rounds MAIN/eval/runs. And the subject is not EVIDENCE_BLURB but the RESOURCE - judge-facing text that claims something about the packer - which is THREE objects: the blurb, the sampling skill written into every pack, and the claude -p prompt, which is an argv string no checker walking the pack directory could ever see. The skill and the prompt both asserted completeness UNCONDITIONALLY, so a field built on purpose with --allow-truncated would have been described three contradictory ways; the prompt was found only because the check was written against the resource. THE DESIGN, and why the obvious repair is wrong: deleting the sentence passes any check that merely forbids the bad wording and leaves the judge to guess how much it holds, which is the state in which it discounts absences; hard-coding complete is wrong because --allow-truncated still exists. A claim with only one possible value is not a claim and nothing can check it - that is why the constant survived the deletion of the mechanism it described. run_field now REFUSES a pack whose MAPPING has no knowingly_truncated key rather than reading a missing key as falsy. A SECOND STALE CLAIM in the same constant: the brief told both code aspects to cite sim/03.src, but only architecture blinds extensions, so half the code briefs named a path shape no judge had; it cannot be repaired by printing the real suffix because one brief serves eight submissions from four stacks and any real suffix names an arm, so PACK_PATH_EXAMPLE False is suffix-free. RED BEFORE GREEN, rule 14, shipped predicates against a git archive HEAD copy rather than memory: EVIDENCE_BLURB code red on budget and may-not-contain, the other three blurbs and the skill body green, idiomatic path example red. Green after: exit 0. WHERE THE CHECK IS AIMED was chosen on the false-positive count, not on which address sounded more general - the rendered BRIEF.md/SKILL.md gives 3 false positives, all the skill history narrating the removed cap in the past tense, against 0 for the claims themselves, same 2 true positives. SEVEN MUTANTS, each driving the WHOLE selftest because a mutant that only flips its own local predicate proves nothing about the shipped check: baseline 0 red, historical sentence 2, notes collapsed 12, prompt back to a constant 5, non-blind example given a real suffix 2, claim deleted outright 4, skill stops varying 6, brief ignores the flag 4. VARIANT, rule 15: a field whose STORED files_dropped_for_length is 4, through the real build_pack allow_truncated=True - no mutant can manufacture that input - plus the same fixture without the escape proving build_pack still refuses it. ISOLATION, rule 8, enumerated from the artifacts: rebuilding all 30 hashed rounds'' briefs moves architecture 3536 to 3576 and idiomatic 3928 to 4000; audio is byte-identical; fun, fun_frames and ux move by the same 938 characters BEFORE AND AFTER the change, which is the pre-existing FRAMES_BLIND_SPOT paragraph already in RUNS.md. TWO FIXTURE TRAPS RECORDED IN THE TICKET: keying packs on sees alone builds one code pack not two, because idiomatic and architecture share sees and differ on blind_language - it reported two failures that were entirely the fixture''s, FINDINGS 138 again; and there are two frames directories read by different code, build_pack from eval/frames and pack_matches_manifest from eval/judge_pack/frames. NO FINDING NUMBER ALLOCATED - the claim, measurement and control are written in the ticket for the orchestrator to number at merge. NO STARTER OR TEMPLATE FILE CHANGED, so verify_blind, starter_parity and a starter regime note are not required; the new judge-facing text was scanned with anonymise.find_stack_names and _TRIAL_ID_RE in both completeness states and the six pre-existing hits are byte-identical before and after. GATES UNPIPED: blurb_selftest 0, pack_selftest 0, aspects_selftest 0, blind_ext_selftest 0, blind_dir_selftest 0, anonymise_selftest 0, gate_selftest 0, capture_selftest 0, sequential_selftest 0, field.py packcheck on wg-g4c 0, docstat.py --sweep clean with the same 16 pre-existing renumbered citations, tasks.py check 106 tasks all well-formed, ruff on the two changed modules clean except two pre-existing B905 in field.py. Docs: eval/RUNS.md new grader-side boundary section with the producer command and a per-aspect before/after table, eval/judge/AGENTS.md new section on judge-facing claims, DECISIONS.md new decision plus a reversal condition. Branch task-104-evidence-blurb-completeness-claim, not pushed.'
---

field.EVIDENCE_BLURB['code'] reads: NOTE: the pack is filled until a size budget runs out, so it may not contain every file the author wrote - judge what is here and do not infer that an absent concern was neglected. The character budget was REMOVED on 2026-08-22 (FINDINGS 69) and files_dropped_for_length is now 0 by construction, asserted by the completeness gate in field.build_pack. So the harness tells every judge, in the brief, that its evidence may be an alphabetically-selected subset when it is not. The direction of the error matters: it invites a judge to discount an absence it is actually seeing in full, which is the opposite of the caution the sentence was written to induce. Found while closing task 95, which repaired CHANGED.txt in the same function; not fixed there because judge-facing text is what the judge reads and changing it is a change to the instrument, not to a leak. It should be corrected before the next round rather than after.

## What was done, and what the next agent must not re-derive — 2026-08-23

### The ticket's own premise was wrong in two places, and both matter

**"every stored round read the stale text" is not true and cannot be made true.** The sentence
lives in `EVIDENCE_BLURB["code"]`, which only reaches an aspect whose `sees` includes `code`, so
`ux`, `fun`, `fun_frames` and `audio` never carried it. Of 93 stored rounds, 36 are code-seeing.
Of those 36 only 10 stored a `provenance.brief_sha256`, and **only those 10 can be asked at all**;
all 10 rebuilt byte-identically to the pre-repair brief, so they demonstrably read it. The other
26 predate `provenance` and are **unassessable, not clean** — the #83 shape. `eval/RUNS.md` states
it that way and the producer is
`python3 eval/judge/blurb_selftest.py --stored-rounds <main checkout>/eval/runs`.

**"a check that would fail if a claim in EVIDENCE_BLURB stops matching the packer" names the wrong
subject, and writing it as the RESOURCE instead found a third instance nobody knew about.** The
resource is *judge-facing text that makes a claim about the packer*. It is three objects, not one:

| | where | what was wrong |
|---|---|---|
| `EVIDENCE_BLURB["code"]` | rendered into `BRIEF.md` | the ticket's sentence |
| the sampling skill | written into every pack | asserted completeness **unconditionally**, so a field built on purpose with `--allow-truncated` would have got a skill and a brief that contradicted each other |
| the `claude -p` prompt | **not in the pack at all** — it is an argv string | *"The submissions are complete, so some are large"*, a constant. **A checker that walked the pack directory could never have seen it** |

The third was found only because the check was written against the resource. Anyone extending
this must add the new text to `blurb_selftest.judge_facing_texts()`, not to a list of constants.

### The design, and why the obvious repair is wrong

Deleting the sentence passes any check that only forbids the bad wording, and leaves the judge to
decide for itself how much of a submission it is holding — which is the state in which it
discounts absences. Hard-coding "this pack is complete" is wrong too, because `--allow-truncated`
still exists. **A claim with only one possible value is not a claim and nothing can check it** —
that is exactly why the constant survived the deletion of the mechanism it described.

So the claim is a function of the pack: `field.COMPLETENESS_NOTE[knowingly_truncated]`, selected
by `build_pack`, `pack_skill()` and `run_field`. `DECISIONS.md` records it with a reversal
condition (removing `--allow-truncated` collapses it back to a constant).

`run_field` **refuses** a pack whose MAPPING has no `knowingly_truncated` key rather than reading
the missing key as falsy, which would assert completeness about a pack nothing on disk describes.

### A second stale claim in the same constant

The brief told **both** code aspects to cite files as `sim/03.src`. Only `architecture` sets
`blind_language`; under `idiomatic` the packer keeps each file's real suffix, so half the code
briefs named a path shape no judge had. It cannot be fixed by printing the real suffix — one brief
serves eight submissions from four stacks and any real suffix names an arm — so
`field.PACK_PATH_EXAMPLE[False]` is suffix-free.

### Where the caution-vocabulary check is AIMED was chosen on the false-positive count

Rule 12, and the census-trigger derivation in `DECISIONS.md`. Measured both ways:

| address | false positives | true positives |
|---|---|---|
| the rendered `BRIEF.md` / `SKILL.md` | **3** — the skill's closing paragraph narrates the removed cap in the past tense, legitimately | 2 |
| the **claims themselves** (present tense: `EVIDENCE_BLURB`, `COMPLETENESS_NOTE[False]`, `JUDGE_PROMPT[False]`, the skill template minus its history slot) | **0** | 2 |

The second is what shipped. Do not "simplify" it back to scanning the rendered text.

### Traps paid for in this ticket

- **`packs` keyed on `sees` alone builds one code pack, not two.** `idiomatic` and `architecture`
  share `sees="code"` and differ on `blind_language`; keyed on `sees` the fixture built the
  non-blind pack and then judged `architecture`'s `.src` promise against it, reporting two
  failures that were entirely the fixture's. That is #138 again — one call site reading half an
  aspect. The key is `(sees, blind_language)`.
- **There are two frames directories and they are read by different code.** `build_pack` copies
  from `eval/frames`; `pack_matches_manifest` counts `eval/judge_pack/frames` against the report's
  `pack.frames`. A real trial has both. A fixture with one cannot reach the code under test.
- **`mapping_path()` puts the MAPPING outside the pack**, so `copytree` does not bring it.
- **Do not run the new selftest against a pre-repair tree assembled by symlink** — the constants
  it reads would not exist and it dies on the name. The informative red control applies the
  shipped predicates to a `git archive HEAD` copy instead.

### Controls, both directions

- **Red, before any change**, shipped predicates against `git archive HEAD`: `EVIDENCE_BLURB['code']`
  red on budget and may-not-contain; the other three blurbs and the skill body green; the
  `idiomatic` path example red.
- **Green after**: `blurb_selftest.py` exit 0.
- **Seven mutants, each driving the WHOLE selftest** (a mutant that only flips its own local
  predicate has proved nothing about the shipped check). Baseline 0 red; historical sentence
  restored 2 red; notes collapsed 12; `claude -p` prompt back to a constant 5; non-blind example
  given a real suffix 2; completeness claim deleted outright 4; skill stops varying 6; brief
  ignores the flag 4.
- **Variant (rule 15)**: a field whose *stored* `files_dropped_for_length` is 4, built through the
  real `build_pack(allow_truncated=True)`. No mutant can manufacture that input, and the same
  fixture without the escape proves `build_pack` still refuses it.
- **Isolation (rule 8)**, from the artifacts rather than the intent: rebuilding all 30 hashed
  rounds' briefs shows `architecture` 3536 to 3576 and `idiomatic` 3928 to 4000 moved; `audio` is
  byte-identical; `fun`/`fun_frames`/`ux` moved by the same 938 characters *before and after* the
  change — that is the pre-existing `FRAMES_BLIND_SPOT` paragraph already recorded in `RUNS.md`.

### NEEDS A FINDING NUMBER — not allocated here (14 collisions on 2026-08-23)

**Claim:** the harness told every code-reading judge that its evidence might be an
alphabetically-selected subset of each submission for the whole period after the character budget
was removed on 2026-08-22 (#69), and the direction of the error is the damaging one — it invites a
judge to discount an absence it is seeing in full, which is most of what a code judge has to work
with.

**Measurement:** 10 of 10 stored code rounds carrying a brief hash rebuild byte-identically to
that text; 26 further code rounds stored no hash and are permanently unassessable; 93 stored
rounds in total, 36 code-seeing. Producer:
`python3 eval/judge/blurb_selftest.py --stored-rounds <main checkout>/eval/runs`.

**Why nothing caught it:** every gate this project owns reads the pack, the manifest or the score.
**None read the brief.** The general form is the one worth publishing: *a claim with only one
possible value is not a claim, it is a decoration, and no check can disagree with it.* The same
property put the opposite error in two sibling texts — the pack skill and the `claude -p` prompt
both asserted completeness unconditionally, so a deliberately truncated field would have been
described three ways at once.

**Control:** shipped predicates against `git archive HEAD` give 2 true positives and 0 false
positives on the live corpus; seven mutants each turn the shipped check red against a clean
baseline.

### Files

`eval/judge/field.py` (`COMPLETENESS_NOTE`, `PACK_PATH_EXAMPLE`, `JUDGE_PROMPT`, `judge_prompt`,
`pack_skill`, `PACK_SKILL_TEMPLATE`/`PACK_SKILL_HISTORY`, `_brief`, `build_pack`, `run_field`),
`eval/judge/blurb_selftest.py` (new), `eval/RUNS.md`, `eval/judge/AGENTS.md`, `DECISIONS.md`.
**No starter or template file changed**, so `verify_blind.py`, `starter_parity.py` and a starter
regime note are not required — but the new judge-facing text was scanned with
`anonymise.find_stack_names` and `_TRIAL_ID_RE` in both completeness states and adds nothing:
the six pre-existing hits (`idiomatic` naming all four stacks by design, and the excluded English
numeral `three`) are byte-identical before and after.
