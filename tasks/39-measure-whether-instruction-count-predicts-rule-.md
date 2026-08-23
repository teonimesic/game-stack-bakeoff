---
id: 39
title: Measure whether instruction count predicts rule compliance in this project's own docs
status: open
priority: 5
refs: research/11-doc-linting-for-agents.md, AGENTS.md, eval/PROTOCOL.md
done_when: a design exists naming the instructions to be varied, the compliance measure, the control arm and the cost; then either a run reports a compliance-vs-instruction-count relationship with n per arm, or it reports no measurable relationship with the effect bounded - both close the task
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
