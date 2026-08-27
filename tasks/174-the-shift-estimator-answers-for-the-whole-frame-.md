---
id: 174
title: The shift estimator answers for the whole frame, not for the band it was asked about
status: done
priority: 2
refs: eval/judge/scene_probe.py,eval/SCENES.md,tasks/164,#189
done_when: 'The estimator either scores each band from pixels belonging to that band only - masking or windowing the search to the band''s own region - or it is established with a measurement that it cannot, and the criterion is re-scoped to what it can actually read. Either way: the cross-band agreement above is re-measured and stated per pair, the 6 s1_parallax fixtures are run before and after with each criterion''s fail and unsc columns compared, scene_mutants.py exits 0 with its counts stated, and eval/runs/wg-scene-s1ts-2026-08-25 is re-graded READ-ONLY with layers.image_parallax recorded either way. A null result - the estimator is doing the best obtainable thing and three bands are genuinely unreadable - closes this, provided the cross-band figures are what establishes it.'
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/50
established_by: 'Merged as PR #50. A NULL on recovery, and an honest one. The ticket''s premise was half right: band_profile already windows to the band''s rows, and what no windowing can do is attribute a row to a LAYER, because layers[].top/bottom mark where a layer is DRAWN and a layered background overlaps by construction - so a far band holds nearer layers'' pixels where they cover it. best_shift then answers confidently for the wrong layer. The agent reproduced the cross-band table independently from the stored frames (pair 4 = -9px on all five lower bands) and MEASURED the obvious painter''s-algorithm fix rather than assuming it: masking to rows no nearer band covers leaves range and grove returning the identical 11-pair series, which is clouds'' rate - a band farther than both - so the subtraction is over every other band, under which 5 of the submission''s 7 bands hold no row of their own at all. The stored trial is unchanged at 6 of 6 = 1.000 with layers.image_parallax still scored=False; what changed is that the recorded REASON was false. What the work buys is a false negative that had never fired: a new variant with bands at the layers'' full extents, same simulation and same picture, was read at 25px/frame against a drawn 13.5px and FAILED, and is now refused - no mutant could have reached it, which is rule 15 and #46''s shape. The review also found a genuine fail-open the agent says it would not have: _bands accepted top/bottom outside [0,1], so a band declared -1.000 to 0.010 counted 363 rows of a 360-row frame, cleared the floor and was profiled from the 3 rows that exist. Fixed with two cases and a mutant. Verified by the orchestrator on the merged tree: scene_mutants --attribution-selftest exit 0 at 9 band tables / 4 mutants / 0 unmet, --reliability-selftest exit 0, and ci_minutes --controls exit 0, which is 177''s census meeting the first branch to add a gate after it.'
---

`ParallaxScene` measures each layer's per-frame shift by searching for the offset that best aligns a band between two captures. The repair in tasks/164 stopped the reliability filter from passing every layer regardless of what came back, and doing so made a SECOND defect legible that the first was hiding: the estimator locks onto one whole-frame feature rather than onto the band it is scoring.

Measured on the first stored scene (eval/runs/wg-scene-s1ts-2026-08-25). At frame pair 4 all five lower bands answer -9px. At pairs 1, 3, 5 and 10, four of them answer -46, -19, -66 and +8 respectively. Bands that are contracted to move at DIFFERENT rates - that is the entire point of a parallax scene - are returning the same number, which is the signature of one dominant feature crossing the frame and every band's search finding it.

Consequence now that the filter is honest: three bands fail on CONFIDENCE rather than on aliasing. So the criterion is currently unable to read a scene it should be able to read, and the reason is the instrument rather than the submission. tasks/164 recorded this as visible-and-out-of-scope rather than repairing it, which was the right call - it is a different mechanism from the slack floor and the aliasing precondition.

Note the shape: near-identical readings ACROSS independent subjects at the same pair is rule 9 - a repeated identical measurement across subjects that share nothing but the instrument is reporting the instrument.

## note 2026-08-27

## What the estimator's problem actually is (2026-08-27)

**The ticket's premise was half right.** `band_profile` already windows to the band's rows.
What no windowing can do is attribute a row to a *layer*. `layers[].top`/`bottom` are
contracted as *where the layer is drawn*, and that does not partition the frame: a layered
background overlaps by construction. A far band holds the nearer layers' pixels where they
cover it and the farther ones' where they show through, so `best_shift` answers for whichever
content carries the band's gradient energy — confidently, and for another layer.

**Do not re-derive the painter's-algorithm fix. It was measured and it fails.** Masking to the
rows no NEARER band covers is the obvious repair and it is wrong: on
`eval/runs/wg-scene-s1ts-2026-08-25` it leaves `range` (3 own rows) and `grove` (7) returning
the identical 11-pair series `20, 17, 15, 19, 20, 15, 16, -4, 6, 5, 6` px — the rate of
`clouds`, which is FARTHER than both. `ridge` gets 0 rows either way. That measurement is in
`eval/SCENES.md` and in `DECISIONS.md`, and it is what "to re-open" has to beat.

**What shipped:** `ParallaxScene.MIN_OWN_ROWS`. Bands are clipped to the frame in `_bands`,
then a layer is measured only on the tallest run of rows no OTHER declared band covers, and one
left fewer than `PROFILE_ROWS` (10) is UNATTRIBUTABLE — reported, excluded, never given a
neighbour's motion.

### Numbers the next agent should not re-measure

Per-band own rows on the stored submission (640x400 frames, +/-89px search window):

| band | declared band | own rows of 400 | spans crossed per pair |
|---|---|---|---|
| sky | 0.000-0.460 | 3 of 184 | 0.00 |
| clouds | 0.008-0.408 | 0 of 160 | 0.02-0.03 |
| range | 0.284-0.468 | 0 of 74 | 0.10 |
| ridge | 0.344-0.476 | 0 of 53 | 0.24-0.26 |
| grove | 0.292-0.492 | 0 of 80 | 0.46-0.48 |
| verge | 0.308-0.692 | 0 of 153 | 0.76-0.99 |
| road | 0.460-1.000 | 124 of 216 | 1.66-2.25 |

**Why the fixtures never showed it:** `judge/fixtures/ref_parallax` declares
`BANDS = {1: (0.00, 0.30), 2: (0.30, 0.52), 3: (0.52, 0.66), 4: (0.66, 1.00)}` — four bands
that **tile the frame and overlap nowhere**. Every threshold in the estimator was set against
that. It is the fixture author's choice, not the contract's.

**Expected per-pair drawn shift**, useful for any future work on this trial: travel over the run
(`eval/RUNS.md`, unwrapped) / 11 pairs x 0.8 px per reported unit — road 375px, verge 235,
grove 150, ridge 75, range 37.5, clouds 17.9, sky 6.2. Only sky, clouds, range and ridge are
inside the +/-89px window at all; road and verge are also past the Nyquist limit.

### A finding, which needs a number from the orchestrator

**Claim.** A criterion validated entirely against a fixture whose geometry is degenerate
reports the fixture's geometry, not the instrument's competence. `layers.image_parallax` was
green on the reference, on 5 variants and on 13 mutants, and could not read a correct scene
whose declared bands overlap — which is what a parallax scene's bands do.

**Measurement.** `scene_mutants.py`'s new variant `the layers are declared at their full
extent` is `ref_parallax` with `BANDS = {1: (0.00, 0.66), 2: (0.30, 0.66), 3: (0.52, 0.66),
4: (0.66, 1.00)}` and nothing else changed — same simulation, same painter's order, same
picture, `layers.depth_ordered` still PASS. Before the repair the probe published
`depth 8 shifted 25px/frame` for a band whose drawn shift is 13.5px — the rate of a layer two
steps nearer — and FAILED the criterion. 7/8. After, `scored=False` and 7/7.

**Control, both directions.** The 6 pre-existing s1_parallax fixture subjects are unmoved on
every criterion: `--only s1_parallax --census` before against after has every `fail` column
identical (1, 5, 4, 2, 2, 2, 2, 3) and `unsc` moving 0 -> 1 only on `layers.image_parallax`,
which is the new variant. `--attribution-selftest` carries 9 hand-written band tables and 4
mutants of the shipped file, all 4 of which move rows.

**Shape.** #46's — a false negative needing an INPUT rather than a missing mechanism, so no
mutant could reach it. Its distinguishing feature against the earlier ones is *where* the blind
spot came from: not a criterion written too narrowly, but a **fixture written too tidily**.

### Two things deliberately not done

- **No windowing recovers a reading on this submission.** 5 of 7 bands have no row of their own
  at any threshold. The repair converts a confident wrong answer into a stated refusal; the
  stored trial's tier 2 is unchanged at 6 of 6 with `layers.image_parallax` `scored=False`.
  A contract change — declaring the bands disjoint, or adding a per-layer mask — would be a
  prompt change and a regime boundary, and is not decided here.
- **The 8-of-132 fixture miss rate** (a large object stationary on screen) is a different
  mechanism, untouched and unre-measured. The fixtures' bands tile, so this repair cannot move
  it.

### Loose end for whoever passes next

`.github/workflows/gates.yml`'s comment says the ruff pinned set *"stands at 97 findings (read
2026-08-25)"*. `python3 eval/tools/lint.py --counts` reads **96** on unmodified `main` as well
as on this branch, so it was already stale. It is a comment, not a gate, and I left it rather
than change a number whose history I had not looked into.

## note 2026-08-27

## What the review found that the measurements did not (2026-08-27)

5 rounds on `https://github.com/teonimesic/game-stack-bakeoff/pull/50`. Rounds 1 and 2 found
real defects; 3, 4 and 5 were documentation wording, and round 5 found nothing in the code.

**The one worth carrying forward is a FAIL-OPEN neither the fixtures nor the stored trial
could reach**, because neither carries a band declared outside `[0, 1]`:

> `_bands` accepted any finite `top`/`bottom`. `_own_band` counted them raw while
> `band_profile` clamps to the image — so a band declared `-1.000` to `0.010` counts **363
> rows of a 360-row frame**, clears `MIN_OWN_ROWS`, and is then profiled from the **3 rows
> that exist**. `_bands` now clips before either reads the band, and the `bottom <= top`
> refusal moved AFTER the clip so a band entirely off the frame collapses to an edge and is
> refused rather than measured as a sliver.

That is `AGENTS.md` rule 7 in the shape this repository keeps meeting: **a guard whose input
is unvalidated is a guard on a number rather than on the thing.** The pin grew with it —
`--attribution-selftest` routes its table through `_bands` as well as `_own_band`, so the clip
is inside what the table measures, and it carries 2 cases and a 4th mutant for exactly this.

The other 3 code findings, all of which the suites were green through:

- `only N of len(shifts) + len(unattributable) declared layers` under-counts, because `_bands`
  drops a row with no usable `top`/`bottom` and `state.shape` asks for neither. The old code
  had the same hole with `len(shifts)` alone. Now taken from `self._layers(r.trace_a[0].state)`.
- The grouped evidence note said *"so nothing drawn there is theirs alone"* about every
  refused layer, false of the 1-to-9 own-row case — and the stored trial has a layer at 3, so
  the false form was already in a durable record. Now *"too few to attribute what is drawn
  there"*, true of 0 through 9.
- `_image_parallax` and `_seamless` annotated `unattributable` as `dict[Any, str]` where the
  value is a 4-tuple.

**A stale count I introduced and the review caught 2 commits later:** `eval/SCENES.md` said the
selftest carries "3 mutants" after round 2 took it to 4. Counts in that section are now stated
without a number that can go stale — the producer is the selftest's own closing line.

### The final head is NOT the reviewed head

Review round 5 read `658d8a3`. `main` moved again afterwards (`4258c13`), so the branch was
merged forward to `0c2f44a` and that head has had no review round — the round ceiling is 5 and
`.agents/skills/work/SKILL.md` says to hand back rather than open a sixth. The merge is a
fast-forward of documents plus this ticket's own file; every gate was re-run at `0c2f44a` and
is green.
