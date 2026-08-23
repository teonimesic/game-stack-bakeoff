---
name: refine
description: "Close the loop after a run: turn its evidence into the next iteration by improving templates, task prompts, judge rubrics and documentation, with each change stated as a falsifiable hypothesis."
when_to_use: "A matrix has finished AND been evaluated; an improvement iteration is ending; asked what to change next or what the run taught. Run evaluate-run first. Trigger phrases: what did we learn, improve the template, what should change, next iteration, reflect on the run."
---

# Refining after a run

The point of a run is not the number it produced. It is what the number licenses you to
change. This skill turns evidence into the next iteration.

Authoritative references: `eval/FINDINGS.md`, `eval/RUNS.md`, `eval/IMPROVEMENTS.md`
(the evaluator loop), `IMPROVEMENTS.md` at root (the template loop), `DECISIONS.md`.
**If this file disagrees with them, they win and this file is the bug.**

Run `evaluate-run` first. Refining on ungraded or unadjudicated results refines against
grader defects, which is how three matrices produced rankings that were withdrawn.

## 1. Separate what the run measured from what it revealed

Two different harvests, and the second is usually larger.

- **Measured** — the scores, costs, turn counts the run was designed to produce.
- **Revealed** — everything that broke, surprised, or turned out to be unmeasurable.
  Every finding in this project came from here, not from the intended measurement.

Write both down before deciding anything. A run that produced a null and six harness
defects was not a wasted run.

## 2. Adjudicate before generalising

For every failure the run produced, in this order:

1. Was it a **submission** defect or a **grader** defect? Trace it to source. Across three
   matrices, every single criterion failure was the grader.
2. Did any criterion **pass for the wrong reason**? Read the evidence strings of *passing*
   criteria, not only failing ones. Mutants cannot catch this class, and it is the class
   that produced the withdrawn ranking.
3. Is any pattern **stack-correlated**? If so it is an instrument defect until a causal
   chain is named in the code. Four for four here. Do not invent a mechanism to fill the
   gap; record the split as unresolved.

## 3. Then decide what to change

Work down; stop when the evidence runs out.

**The templates** (`template*/`, `eval/starters/*/`) — did agents fight the harness, or
work around something the starter should have provided? A defect that misleads a building
agent is a *product* defect, not a grader one: `just film` omitting the HUD meant an agent
could delete working code chasing a ghost. Any edit here changes the thing being measured
— never mid-run, and re-run `verify_blind.py` after.

**The task prompts** — did every submission pass everything? Then the task is too easy and
the suite cannot rank anything, which is a statement about the task, not the stacks. Did
agents systematically miss something? Decide whether the prompt should ask for it or the
rubric should stop expecting it. Remember `_preamble()` is shared: editing it for one game
changes all of them.

**The rubric and judges** — which criteria fired? Which never fired, and could they? A
criterion that has only ever fired wrongly is worse than absent. If a judge tier ceilings
— everything passing — it carries no information regardless of how stable it is, and
stability measured on uncontested artifacts is not stability.

**The documentation** — invoke `audit-docs`. Which rule should have caught each failure,
and why didn't it fire?

## 4. State every change as a hypothesis that could come out against you

Before running anything:

> **Hypothesis** — what you believe is wrong.
> **Change** — what you will do about it.
> **Prediction** — what the next run shows if you are right.
> **Falsifier** — what result would mean you were wrong.

Pre-register it in the relevant `IMPROVEMENTS.md`. A prediction written after the result
is fitted to it, and nobody can tell afterwards — including you.

**Keep or revert on the measurement, not the impression. A revert is a successful
iteration**: it bought a real answer. An iteration that ends "I improved X" with no number
is this project's central failure mode wearing a new hat.

## 5. Cost and comparability

- Any change to task, limits, allowlist or starters means the next run is **not comparable**
  to this one. Record it in `RUNS.md` with the reason, as the earlier regime breaks are.
- Calibrate cost with **two trials in different cells** and quote the **range**. Within-cell
  spread has measured 1.6×, and a single trial cannot calibrate that. A figure with a
  stated uncertainty is still acted on as a figure — so where the spread is wide, do not
  quote a point estimate at all.

## 6. Update, in the same session

`README.md` status · `DECISIONS.md` · `eval/RUNS.md` · `eval/FINDINGS.md` ·
`eval/judge/RUBRIC.md` if weights or criteria moved · the relevant `IMPROVEMENTS.md`.

State what is true now; replace superseded content rather than annotating it. The
exceptions are a published number later proven wrong, and a published reading of evidence
later overturned — both stay marked, because someone may have acted on them.

## The question to end on

**What would the next run have to show for us to conclude we were wrong about this?**

If there is no such result, the change is not a hypothesis — it is a preference, and it
should be labelled as one.
