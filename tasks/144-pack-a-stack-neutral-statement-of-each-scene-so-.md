---
id: 144
title: Pack a stack-neutral statement of each scene, so fidelity can ask the question it is named for
status: in_testing
priority: 3
refs: eval/SCENES.md, eval/judge/RUBRIC.md, eval/judge/aspects.py, eval/judge/field.py, eval/judge/verify_blind.py, tasks/135
done_when: 'A stack-neutral statement of each scene exists, is written into the pack by field.build_pack for scene fields only, and carries no arm-naming token: verify_blind.py --packs over a built scene pack is green, and a planted stack token in the statement turns it red. blurb_selftest.judge_facing_texts() covers it, because it is judge-facing text making a claim. fidelity''s notes stop telling the judge to recover the subject from the field. The ''cannot find what all eight missed'' caveat is removed from SCENES.md and RUBRIC.md in the same change.'
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/34
established_by: 'verify_blind.py --packs exit 0 on a built s1_parallax pack and exit 1 with a planted stack token; blurb_selftest.py green with 13 of 14 field.py mutants red; 90 game briefs byte-identical; PR #34, 6 review rounds, round 6 unreviewed'
---

fidelity asks 'does this read as the scene it was asked for'. The pack carries no statement of the scene: the rendered prompt exists per stack (eval/suites/rendered/s1_parallax__ts.txt and its three siblings), so handing a judge one names the arm in its own evidence - the leak blind_extensions and neutralise exist to close. Until a neutral statement is packed, the aspect recovers the subject from the field of eight and can find a submission that omits what seven others drew, but CANNOT find one where all eight missed the same requirement. That narrowing is recorded in eval/SCENES.md, eval/judge/RUBRIC.md and the aspect's own comment; this ticket removes it.

## note 2026-08-25

## note 2026-08-25 — the tier-3 layer is merged, so this is the gap it shipped with

Tasks 133, 134 and 135 are all on `main`: scene prompts, the 15-criterion probe, and the three
tier-3 aspects. `fidelity` exists and is asked only of scenes. **This ticket is the thing it cannot
do yet**, stated in three places at merge: no pack carries a statement of the scene, and the
rendered prompt is **per stack**, so handing a judge one names the arm.

The consequence is precise and worth keeping precise: `fidelity` can currently find a submission
that omitted what 7 others drew. It **cannot** find one where all 8 missed the same requirement —
which is exactly the case a fidelity judge exists for.

## The constraint that makes this hard

A stack-neutral statement is not the prompt with the engine nouns removed. The prompts differ by
2.7% of lines across stacks, and the differences are *"where things go"* and *"how to make sound"*
— so a naive strip leaves a text that still reads as one stack's. **`verify_blind.py` is the gate**
and it must still pass; `eval/judge/anonymise.py` is the existing machinery for this class.

**Write the statement from `eval/SCENES.md`, not from a rendered prompt.** The design document
describes both scenes in stack-free terms already, and it is the source the prompts were written
from — going back to it is cheaper than laundering an output of it, and it cannot leak a vocabulary
dict by construction.

## What NOT to do

Do not put anything from the criteria into the pack. `SCENES.md` states what each criterion catches
and none of that may reach a judge — the same rule that governs prompts. Task 133 checked this by
grepping the rendered prompts for criterion vocabulary; do the same for the pack, and say what you
grepped for.

## note 2026-08-25

## What the statement is, and where the constraints on it live

`field.SCENE_STATEMENTS` holds one hand-written statement per scene, joined to a shared
`field.SCENE_STATEMENT_HEADER` by `field.scene_statement(game)`. `field.build_pack` writes
the result into a scene pack — and only a scene pack — as `SCENE.md`, **raw**.

Three constraints bind anything written there, and two of them are not obvious:

- **No stack token.** `anonymise.find_stack_names` returns a stack token in every one of
  the 8 rendered scene prompts, which is why the prompt was never a candidate. Note that
  the word **`three`** and the word **`node`** are literal patterns in
  `anonymise._LITERAL_TOKENS` — the English numeral will turn `verify_blind.py --packs`
  red. Do not write "three numbers" in a statement.
- **No criterion or threshold vocabulary**, checked with `tools/prompt_guard.py`'s two
  closed lists, the same grep the prompts get. That bans `judge`, `score`, `graded`,
  `monotonic`, `occlude`, `at least`, `up to`, `more than` and 40 others **with English
  inflections** — `score` matches `scores` and `scored`. A judge-facing text cannot use
  the word "judge".
- **It must ask for no MORE than the prompt did.** Nothing mechanical can check this. What
  can be checked is where the elements come from: `prompt_guard._shared_lines` puts 30 of
  31 s1 scene-section lines and 39 of 40 s2 lines in the all-four-stacks-identical set, so
  every element the statement encodes is asked of every arm word for word. The single
  divergent line in each is the 2D/3D starter note, which the statement omits.

## Do not write it through `neutralise`

Every other piece of pack text goes through `_text` because it came from a submission.
This text is ours, and laundering it would rewrite `Bevy` to `engine` and leave
`verify_blind.py --packs` green over judge-facing text that named an arm until the harness
edited it. `blurb_selftest.py` drives a leaking statement through the real `build_pack` and
requires the leak to survive and the gate to go red; the mutant that plants a token on disk
after the packer ran cannot ask that question and did not.

## Both the packer and the spender refuse, and existence is not the resource

`build_pack` refuses a scene it cannot state. `run_field` refuses a pack whose `SCENE.md`
is missing, undecodable or **not this scene's statement** — an empty file and the other
scene's text both pass a presence test. It is checked BEFORE the `knowingly_truncated`
guard, deliberately, so a selftest can distinguish the two refusals without spawning a
judge. There is no escape flag.

`provenance.scene_statement_sha256` records the statement the round validated;
`brief_sha256` cannot stand in, because the brief NAMES `SCENE.md` and does not contain it.
`field._provenance` was extracted from `run_field`'s tail for this: the whole provenance
block had been unreachable to any offline check, on the far side of an 8-submission judge
invocation. `blurb_selftest.py` drives it through `run_field` with `field.subprocess`
stubbed.

**`SCENE.md` is UTF-8 by contract**, named on both the write and the read. Both default to
the locale codec.

## A FINDING THAT NEEDS A NUMBER — the rubric grep could not see the leak it exists to prevent

`eval/SCENES.md` names 2 claims the scene prompts deliberately withhold and calls them the
sharpest omissions in the design. `prompt_guard.RUBRIC_TERMS` held only their *measurement*
wordings — `distinct rates`, `declared depth`, `world-horizontal` — while `eval/SCENES.md`
states the same 2 claims in plain English in the very paragraph saying they are withheld.

Planted into a rendered prompt, measured 2026-08-25:

| planted sentence | hits over the 8 rendered scene prompts |
|---|---|
| `The layers scroll at rates ordered by depth.` | **0** |
| `The water surface stays level while the glass tilts.` | **0** |

The baseline over the 8 shipped prompts is also 0, so the check was green on a clean corpus
and on a leaking one alike — a mechanism that runs, reports success, and measures the thing
it was written for not at all.

`ordered by depth` and `stays level` are now `RUBRIC_TERMS` entries. Both appear in
`eval/SCENES.md`, so the anti-invention guard accepts them; both are at 0 false positives on
the 8 shipped prompts and on the 2 packed statements; `prompt_guard_control.py` is green on
all 25 rows. **This is 2 spellings and not a property** (#30, #83, #131) — a third phrasing
still walks past, and `DECISIONS.md` says so rather than claiming the class is closed.

## Two false claims corrected, one of them pre-existing

- `eval/judge/AGENTS.md` said `blurb_selftest.py` carries "a mutant per check". False:
  checks 2 and 5 had none. Both now exist.
- **"a field is 8 model calls"** was in `aspects.applicability`'s docstring before this
  ticket and I copied it into 3 more places. `run_field` has exactly one `subprocess.run`:
  one `claude -p` invocation judges the whole field of 8 and returns one `cost_usd`. All 4
  now say so.

## What is NOT established

- No scene has been built or judged. Whether a judge reading `SCENE.md` scores differently
  from one recovering the subject from the field is unmeasured and unmeasurable until a
  scene matrix exists.
- Faithfulness of the statement rests on the line-sharing figures above plus a reading.
  Nothing mechanical can say it asks for no MORE than the prompt did, which is
  `DECISIONS.md`'s first reversal condition for this decision.
- The mutant that drops `encoding="utf-8"` from the write **survives** on this machine:
  the locale is UTF-8 and both statements are pure ASCII, so it is a genuine no-op here
  rather than an uncaught defect.
- The review ran **6 rounds against a ceiling of 5** and was still finding real defects at
  the ceiling. **The round-6 commit has not been reviewed.**
