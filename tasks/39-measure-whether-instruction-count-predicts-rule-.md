---
id: 39
title: Measure whether instruction count predicts rule compliance in this project's own docs
status: done
priority: 5
refs: research/11-doc-linting-for-agents.md, AGENTS.md, eval/PROTOCOL.md
done_when: a design exists naming the instructions to be varied, the compliance measure, the control arm and the cost; then either a run reports a compliance-vs-instruction-count relationship with n per arm, or it reports no measurable relationship with the effect bounded - both close the task
established_by: '104 trials, 9.06 USD, eval/instrfollow/runs/main, all terminal_reason=success. 320 of 320 instruction-instances complied; every arm 1.000 at k=1,2,4,8,16 and at the padded length control. Newcombe 95pct CI on k16-k1 over the 14 instructions with a measured given-vs-not-given effect: -0.0332 to +0.1206, so the largest decline consistent with the data is 3.3 percentage points. Design pre-registered in eval/instrfollow/DESIGN.md before any trial ran; the within-instruction paired estimand removes the count-vs-content confound the ticket flagged as a possible non-termination. Controls green both directions offline via run.py gates: gold 16/16, sixteen mutants each flipping exactly one checker, variant 16/16, unparseable artifact 0/16. Census: the always-loaded set holds 73-113 instructions against ManyIFEval''s ceiling of 10, so the gap above k=16 is untested and is recorded as a re-open condition in DECISIONS.md. Two contradictions in the always-loaded set verified against source and filed as tasks 77 and 79.'
---
## What is this thing?

`AGENTS.md` is the always-loaded root instruction file: 462 lines, ~7,300 tokens, 16 numbered
rules plus roughly a dozen unnumbered ones. Every session pays for it, and the rule audit inside
it records that several rules were **read, understood, and still failed to fire** -- including by
the person who had just written them.

## What is wrong, and how do we know?

Nothing is known to be wrong. The point is that nothing is known at all.

The survey in `research/11-doc-linting-for-agents.md` established (2026-08-23) that **no published
study relates human-readability metrics -- Flesch-Kincaid, passive voice, weasel words, reading
grade -- to LLM instruction-following, in either direction.** Every available prose linter
optimises for a human reader, and adopting one on that basis would be a guess wearing a number.

But one adjacent result **is** measured and is directly testable here. arXiv:2509.21051, *When
Instructions Multiply* (2025-09-25), built two benchmarks (ManyIFEval, text, up to 10 instructions;
StyleMBPP, code, up to 6) across 10 LLMs and found compliance degrades consistently as instruction
count rises -- with **a logistic regression on instruction count alone predicting compliance to
about 10 percent error, including for unseen instruction combinations**. arXiv:2510.14842
identifies the mechanism as conflict between instructions and contributes a conflict-scoring tool.

Separately, the best-controlled studies of repository context files find they do **not** improve
agent task success at all (arXiv:2602.11988, ETH; arXiv:2607.27250, 288 runs). Their decomposition
matters: **instructions are followed; repository overviews are not helpful.** `AGENTS.md` is
almost entirely instructions, so the null does not obviously apply -- but nobody has checked.

## Why does it matter?

This project spends real money measuring how agents behave and owns a harness, a blinded judging
layer and 68 stored trials. It is one of a very small number of places that could answer whether
its own instruction file does anything. Every session pays 7,300 tokens for an artefact whose
effect has never been measured, and the project's own standard is that an unmeasured mechanism is
exactly what it distrusts.

## What should be done?

**Design first. Do not launch anything from this ticket without a written design.** It needs, at
minimum: which instructions are varied, what "compliance" is measured as, what the control arm is,
how many trials per arm, and the cost. Read `eval/PROTOCOL.md` and the `run-matrix` skill before
proposing a run.

Cheap things worth doing before any spend:

- Count the instructions in `AGENTS.md` mechanically and see where it sits on 2509.21051's curve.
- Look for **contradictions** between `AGENTS.md`, the folder-scoped `AGENTS.md` files and the
  seven skills. Anthropic's memory documentation states verbatim: *"if two rules contradict each
  other, Claude may pick one arbitrarily."* Contradiction is measurable without a run.

## Outcomes that count as success -- pre-register these

| result | what it means |
|---|---|
| compliance varies measurably with instruction count, n reported per arm | a real finding, and it changes how this file is maintained |
| no measurable relationship, effect bounded | **also a finding**, and it closes the ticket |
| the experiment cannot be designed without confounding instruction count with instruction content | record why, and close -- non-termination is a result |

## What NOT to conclude

- **Do not conclude from a null that `AGENTS.md` is useless.** The rules in it were each bought
  with a real incident; an unmeasured benefit is not an absent one.
- **Do not conclude from a positive result that the file should simply be shorter.** Instruction
  count and instruction content move together unless the design separates them, and a comparison
  that changes more than one thing is rule 8.
- **Do not adopt a readability score as the compliance measure.** That is the proxy failure of
  #59 with prose substituted for `ux`.

---

## Worked 2026-08-23 -- what exists now, so the next agent does not re-derive it

**The design is written and pre-registered: `eval/instrfollow/DESIGN.md`.** Read that before
anything here. The apparatus is `eval/instrfollow/pool.py` (16 instructions + deterministic
checkers + the control suite) and `eval/instrfollow/run.py` (assignment, trials, analysis).

### Settled, and not to be re-opened without a reason

- **The third pre-registered outcome does not apply. The experiment CAN be designed without
  confounding count with content**, and the way is a *within-instruction paired* estimand: the
  same instruction at k=1 against itself at k=16. Content is then held constant because both
  members of the pair are the same sentence. Anyone re-deriving this should not spend the time.
- **Instruction count of the always-loaded set: 73-113** (`AGENTS.md` alone 39-60), by
  `eval/tools/instruction_census.py`, which reports three definitions and never one number. Main
  checkout and branch agree to the digit. ManyIFEval, the benchmark the hypothesis comes from,
  tops out at 10.
- **A length control arm is mandatory**, not optional. Count and prompt length rise together, so
  without `k1pad` the comparison changes two things and rule 8 forbids the reading.
- **Arms must NOT have equal trial counts.** A trial yields k observations; equal n leaves
  instructions with zero observations in the small-k arms. `run.py plan` exits non-zero on it.

### Found while doing this, and filed separately

Two contradictions inside the always-loaded set, both re-read from source rather than taken
from the scan that proposed them:

- `AGENTS.md:215` claims the sweep covers file paths; `eval/tools/docstat.py:1597` reads
  `# NO PATH CHECK.` -> **task 77**
- `.claude/skills/evaluate-run/SKILL.md:59` says five aspects exist; `eval/judge/aspects.py:281`
  defines six -> **task 79**

These matter to this ticket and not only as defects: arXiv:2510.14842 identifies conflict
between instructions, not their number, as the mechanism. The pool is therefore proved
conflict-free by construction (the gold artifact obeys all 16 at once).

### What the pilot cost and what it changed

$0.83 for 8 trials, and it changed the apparatus twice -- both times in ways the offline control
suite could not have found, because every mutant is derived from an artifact that already obeys
everything. Details in `DESIGN.md`; the short version is that one shared fixture made the
behavioural checkers dependent on one another, and one instruction was ambiguous enough that a
defensible reading scored as non-compliance.

### The trap in the length control, and where its measurement lives

The padding for `k1pad` is drawn from this project's own docs and twice leaked an actual
instruction -- once the source rule behind pool instruction F2, once the source rule behind B1.
Both were caught by RENDERING the prompt and reading it, not by reasoning about the filter.
`python3 eval/instrfollow/run.py padcheck` is the standing control and must stay green. Its
residual limitation, and the direction the residual biases the result, is stated in `DESIGN.md`
-- read it before quoting the length arm.

### The result, 2026-08-23

`eval/instrfollow/RESULT.md`. 104 trials, $9.06, all `terminal_reason=success`.
**320 of 320 instruction-instances complied; every arm 1.000.** Largest decline consistent
with the data: **3.3 percentage points** over the 14 instructions the not-given control
shows are doing work. Length and block position moved nothing either.

This is the ticket's second pre-registered outcome -- no measurable relationship, effect
bounded -- and it closes the ticket.

**What is still open, and it is the interesting half.** The always-loaded set holds 73-113
instructions; this reached 16. Anyone wanting to close that gap needs INSTRUCTIONS, not
trials: the pool must grow past 32 live ones, and 2 of this run's 16 were already satisfied
by default, so a nominal pool of 100 is perhaps 85 live. Cost rises steeply with k --
measured $0.056 at k1, $0.273 at k16 -- so price a k32 pilot rather than extrapolating.
Recorded as a re-open condition in `DECISIONS.md`.
