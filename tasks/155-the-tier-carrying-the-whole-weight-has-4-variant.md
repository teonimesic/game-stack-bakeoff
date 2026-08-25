---
id: 155
title: The tier carrying the whole weight has 4 variant games for 36 criteria; the newest tier has 8 for 15
status: todo
priority: 2
refs: 'eval/judge/bot_mutants.py, eval/judge/scene_mutants.py, AGENTS.md rule 15, #46'
done_when: 'A per-criterion answer to ''what correct-but-unusual game would mis-score this'', recorded for all 36; the 4 existing variants checked against the shapes #46 names, with any uncovered shape either added as a variant or recorded as deliberately out of scope with the reason; and bot_mutants.py still exits 0 with every criterion pinned in both directions. Concluding that 4 is sufficient, with the per-criterion reasoning, is a complete answer and closes this.'
---

The play-bot tier carries **the whole weight** of a submission's score — tier 1 is a gate, tier 3 is
0.00. Its correctness rests on `judge/bot_mutants.py`, which runs both halves the rules require:
mutants (can a criterion fail?) and variants (can it still pass on a **correct** game the reference
does not resemble?).

Measured 2026-08-25:

| suite | criteria | variant subjects |
|---|---|---|
| `bot_mutants.py` — tier 2, weight **1.00** | 36 | **4** |
| `scene_mutants.py` — scene probe, built 2026-08-24 | 15 | **8** |

Every criterion is exercised by every variant, so this is not *"32 criteria have no variant"*.
The honest statement is: **each play-bot criterion has been tested against 4 correct-but-different
games; each scene criterion against 8.**

## Why this is a question and not yet a defect

`AGENTS.md` rule 15 says every false negative ever adjudicated in this project has been of the
variant kind, and #46 is **sixteen in one sweep**, then three more under a harder task, then two
more. So the variant is the half that has historically found things, and the tier carrying all the
weight has the thinner coverage of it.

**That may still be enough.** Four variants chosen well can beat eight chosen badly, and the four
here are pointed at real failure shapes — a title card that holds the ball for 104 ticks, enemies
faster than the player, an `active` span wider than the hitbox, an opening ledge over a pit. This
ticket asks whether the number is right, not whether the existing ones are good.

**The asymmetry has a cause worth naming**: the scene probe's ticket carried the mutant/variant
rule explicitly, and the play-bot suite predates that being written into a brief. The discipline
was applied to new work and never retrofitted.

## What would answer it

1. **What correct-but-unusual game would each criterion mis-score?** Ask it per criterion rather
   than per suite. A criterion nobody can construct a failing input for is either robust or
   under-imagined, and saying which is the work.
2. **Do the 4 existing variants cover the shapes #46 actually found?** That finding names sixteen
   adjudicated false negatives; if the variants do not exercise those shapes, the gap is concrete.
3. Add variants where a shape is missing. **Finding that the 4 are sufficient, with the reasoning
   per criterion, closes this ticket** — a null here is a real answer and is cheaper than adding
   variants nobody derived from a failure mode.

## What NOT to do

Do not add variants to match a ratio. A variant exists to encode a specific way a correct game can
differ from the reference; one written to raise a count tests nothing and costs 226s of CI.

Do not touch the 36 criteria themselves. This ticket is about coverage of the checks, not about
what they check — changing a criterion moves stored verdicts and is a different ticket with a
re-scoring census.
