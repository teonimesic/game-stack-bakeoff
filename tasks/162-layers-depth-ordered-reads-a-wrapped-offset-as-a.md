---
id: 162
title: layers.depth_ordered reads a WRAPPED offset as a scroll rate, and scored the first real scene FALSE
status: done
priority: 1
refs: eval/judge/scene_probe.py,eval/SCENES.md,eval/RUNS.md,tasks/156
done_when: layers.depth_ordered returns a scroll rate that survives wrapping - unwrap the offset series against each layer's declared span, or read the per-tick deltas the wrap events bound - and scene_mutants.py carries a VARIANT built from a wrapping scene that is red before the repair and green after; the stored grading in eval/runs/wg-scene-s1ts-2026-08-25 is re-graded offline and the new verdict recorded either way; and whether the contract means offset cumulative or wrapped is decided and written in eval/SCENES.md, since the prompt does not say
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/39
established_by: 'PR #39 squash-merged. Verified the control from BOTH sides myself: with main''s unrepaired probe restored alongside this branch''s variants, the wrapping variant goes RED - exit 1 naming layers.depth_ordered and loop.seamless with the same ''not strictly decreasing'' evidence - and against the repair the suite is 23 mutants over 15 criteria, 9 variants, 0 unmet. The decision the ticket said gates the repair came out as ''neither encoding is named and the prompt does not change'': each layer declares its own span, so wrapped and cumulative carry the same information. Unwrapping is per TICK because the road crosses 1.6-2.25 spans between captures against a 4.0% per-tick step. Re-grade: layers.depth_ordered FAIL to PASS, 0.833 to 0.857. Allocated FINDINGS #184 and #185.'
---

The criterion computes abs(offset_last - offset_first) per layer and asks whether it decreases with declared depth. A submission that WRAPS offset - which the scene contract asks for, and which loop.seamless exists to check - returns a modular residue instead of a scroll rate. Measured on s1_parallax__ts__t0, the first scene ever built: all 7 layers came back BELOW their own declared span (road 120.1/240, verge 165.1/340, grove 304.0/440, ridge 232.0/400, range 36.0/480, clouds 245.7/900, sky 84.6/1800) while 37 wrap events fired in the same trace. The submission's own convention agrees with the criterion's (layerFactor = 1/(1+depth)), so a sign-convention reading does not rescue it. This is a FALSE NEGATIVE and a mutant could not have found it: only a submission that wraps could, which is rule 15 and #46's shape.

## note 2026-08-25

## note 2026-08-25 (orchestrator) — the evidence reproduced, and the decision is the harder half

Read from the stored grading rather than the hand-back:

    layers.depth_ordered  passed=False  scored=True
    evidence: depth 0 moved 120.1, depth 0.6 moved 165.1, depth 1.5 moved 304.0,
              depth 4 moved 232.0, depth 9 moved 36.0, depth 20 moved 245.7,
              depth 60 moved 84.6 - not strictly decreasing at separation 0.95

Every figure is below its layer's own declared span, and 37 `wrap` events fired in the same trace.
The numbers are residues, and the criterion read them as rates.

## The decision is not downstream of the repair — it gates it

`done_when` asks whether the contract means `offset` **cumulative** or **wrapped**, and the prompt
does not say. **Decide that first**, because the two answers give different repairs:

- **cumulative** → the submission is wrong and the criterion is right, and the fix is in the
  *prompt*, which is a regime boundary against every scene trial ever run (currently 1).
- **wrapped** → the criterion is wrong, unwrap against each layer's declared span, and the stored
  grading changes.

The submission chose wrapped and nothing told it not to. **A contract that does not say, read by a
submission that had to choose, is a prompt defect whichever way the decision goes** — so say which
in `eval/SCENES.md` even if the code change lands in `scene_probe.py`.

## The variant is the whole test and cannot be a mutant

Rule 15, and this ticket is its cleanest instance to date: **no mutant could have found this**,
because a mutant removes a mechanism and what was needed was an *input* — a scene that wraps. The
8 existing variants were written by the hand that wrote the criteria and none of them wrapped.

So the variant must be **built from a wrapping scene**, red before the repair and green after, and
established in that order (#60: a control run after the fix tests the fix, not the claim).

## What NOT to do

Do not widen the tolerance until the stored submission passes. The separation threshold is 0.95 and
the numbers are residues — a tolerance that admits residues admits anything.

Do not re-grade beyond the one stored scene grading. There is exactly **1**, in
`eval/runs/wg-scene-s1ts-2026-08-25`, and it was salvaged from a killed build — record the new
verdict either way, and keep saying the trial never reached `completed`.

## note 2026-08-25

## What landed, and the decision that gated it — 2026-08-25

PR #39, `task-162-scene-offset-unwrap`, 5 review rounds. `eval/RUNS.md` is the authority for
the run figures; `DECISIONS.md` and `eval/SCENES.md` for the decision.

### The decision: both encodings are contracted, and the prompt does not change

The trace contract says `offset` is *"how far that layer has been displaced sideways so far"*
and `span` is *"the width after which the layer repeats itself"*, and it does not say which. A
layer declares its own `span`, so a wrapped series and a cumulative one carry the same
information. Naming an encoding would be a regime boundary across every scene trial and would
deduct marks for reporting `offset` the way a renderer wants it. So the cost falls on the
instrument.

### The repair

`ParallaxScene._walk` rebuilds each layer's offset series from the per-tick trace, mapping every
step into `(-span/2, span/2]` before adding it. `layers.depth_ordered`, `_measure_shifts` (so
`layers.image_parallax` and `loop.seamless`) and the telemetry half of `loop.seamless` all read
that series.

**It has to be per tick, and that is measured.** Captures are 60 ticks apart, and the
submission's road crosses **1.6-2.25 spans** between two of them; its widest *per-tick* step is
**4.0%** of its span. No per-frame unwrap could have recovered the step.

**It is a no-op on a cumulative scene**, exactly: driven against `judge/fixtures/ref_parallax`,
all 4 layers return their old travel with delta `0.00e+00`. That is why no pre-existing mutant
or variant verdict moved.

### The control, in the order #60 asks for

The variant went in **first** and was red: `10 mutants, 5 variants, 1 expectation(s) unmet`,
exit 1, on `layers.depth_ordered` and `loop.seamless`. After the repair the whole suite is
`23 mutants over 15 criteria, 9 variants, 0 expectation(s) unmet`, exit 0.

The variant is the reference scene reporting the other encoding. `film.py` already draws
`offset % span`, so the picture is identical and only the telemetry changes.

### The re-grade

    tar -xzf <run>/artifacts/s1_parallax__ts__t0/submission.tar.gz -C <tree>
    pnpm install --frozen-lockfile && pnpm exec playwright install chromium
    python3 eval/judge/scene_probe.py s1_parallax <tree>

`layers.depth_ordered` FAIL -> PASS. **5 of 6 = 0.833 -> 6 of 7 = 0.857.** The unwrapped travel
is strictly decreasing with depth by 1.56-2.90 at every step (table in `eval/RUNS.md`). The
stored `playbot.json` was not rewritten - durable records are append-only.

### What the next agent must not re-derive

- **`layers.image_parallax` also moved, `scored=False` -> FAIL, and that FAIL is not
  trustworthy.** Fixing `d_offset` promoted the road band past `_reliable`, which let the
  criterion establish itself on 3 bands. The road crosses 1.6-2.25 spans between captures, so
  its shift is aliased against its own tile; it clears the agreement test only because the slack
  is a floor **in ratio units** - 0.15 against a median ratio of 0.053, so nearly any shift
  inside the +/-89px search window agrees with any other. The 2 bands it is compared against
  read **0px on 11 of 11 and 9 of 11 pairs**. `tasks/164` carries it with the per-pair numbers.
- **`loop.seamless` is still `scored=False`, and now for a reason worth knowing**: the road
  wraps on every one of the 11 captured pairs, so there is no away-from-the-wrap baseline, and
  the layers that have one (sky, clouds) never wrap. 12 frames over 660 ticks cannot see this
  scene's seam. That is a property of the capture contract against this scene, not of the
  instrument.
- **The submission reports all 7 layers on all 660 trace lines**, checked - so the continuity
  guard below does not touch its verdict.
- The stored trial has **no stored trace**; re-grading means re-driving the submission, which
  needs `pnpm install` and `pnpm exec playwright install chromium` in the extracted tree. It
  takes ~20s once warm.

### A finding is owed and I did not number it

The work skill forbids allocating one. The claim, the measurement and the control are above and
in `eval/RUNS.md`; **the orchestrator should number it at merge.**

### What the review found, and it was not cosmetic

6 findings over 5 rounds, 5 acted on:

- **A hole in a layer's telemetry was bridged** (round 1). Then **2 more shapes the round-1
  guard let through** (round 5): a layer that stops reporting and never resumes, where the
  prefix walk is perfectly continuous; and a row with no usable `span`, where the raw difference
  was accumulated. All 3 are fail-open and all 3 read as a smaller, plausible travel, because
  `state.shape` reads tick 0 only. One comparison now covers them: a layer declared at tick 0
  earns a walk only by contributing a row with a finite `offset` and a finite `span > 0` to
  every trace line, exactly once. `layers.depth_ordered` FAILS anything else.
- 3 mutants pin it, and the first is measured against the alternative: `the sky stops being
  reported for 19 ticks` - ticks 101-119 hold no captured frame, so the picture is
  byte-identical - and **a bridging unwrap returns PASS on it while the guard returns FAIL.**
  Then `the sky stops being reported for good after tick 500` and `the sky declares no span for
  19 ticks`.
- **`round` is half-to-even**, so a step of exactly `-span/2` stayed outside the
  `(-span/2, span/2]` the line is documented to produce. `math.ceil(step / span - 0.5)` holds
  both signs: at `span` 100, `round` leaves `-50.0` and sends `+150` to `-50.0`; `ceil` sends
  both to `+50.0` and leaves every non-tie step alone.
- 1 finding **declined with evidence** and withdrawn by the reviewer: `[#46]` in
  `eval/judge/AGENTS.md`. `linkcheck.py`'s `LIVE_DOCS` is `README.md`, `AGENTS.md`,
  `DECISIONS.md`, `eval/FINDINGS.md`; that file has **0** reference definitions against **18**
  bare citations, so the link would render as literal `[#46]` and nothing would check it.

**Round 5's fixes were not themselves reviewed** - that would be round 6, past the ceiling.

### The poll deadlocked once, and the notice is not in the skill's table

After merging `main` into the branch mid-review, CodeRabbit posted **`Review failed - the head
commit changed during the review`**. `pr_review_state.py` reported it as `notice=Review failed`
and, because the summary comment sits at the head, `--wait --ignore-notice` then returned
`LANDED_COMMENT` in 1 second - a false "the round finished with nothing to say". The remedy is
`@coderabbitai review` and then waiting on a **review object at the expected head** rather than
on the tool's verdict; the real review arrived 540s later. Worth a row in
`.agents/skills/work/SKILL.md`.
