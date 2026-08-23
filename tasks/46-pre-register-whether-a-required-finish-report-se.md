---
id: 46
title: Pre-register whether a required finish-report section changes what agents disclose
status: open
priority: 5
refs: 'AGENTS.md rule 11, eval/IMPROVEMENTS.md axis 2 candidate 5, eval/FINDINGS.md #98'
done_when: either the experiment has run on a fresh matrix and the pre-registered outcome table has been filled in, or it is closed as declined with the cost argument recorded in eval/RUNS.md
---

## What this thing is

Every whole-game trial ends with the building agent writing a free-form closing message. The
harness stores it as `agent.final_text` inside `agent_result.json`, next to the diff, the tree
listing and the tarball. Nothing in the evaluator reads it. The four starters
(`eval/starters/{godot,rust,ts,unity}/AGENTS.md`) tell the agent what to build and what to verify;
none of them says anything about what its closing message must contain.

## What is wrong, and how we know

`AGENTS.md` rule 11 was written because four agents, unprompted, wrote a paragraph headed *"What
I could not verify — and why"* that named the exact mechanism behind a whole run's spread — and
the graders re-derived it independently. #98 is the second instance: both graded Godot agents in
`wg-g4c-2026-08-21T02-26-46` stated in their own words that the starter's gate was red before they
touched anything, and that is how the blast radius of that defect was eventually bounded.

So the disclosures exist, they are load-bearing, and they arrive **by luck**. An agent that does
not volunteer one is indistinguishable from an agent that had nothing to disclose.

`game-research-gpt`'s `template/AGENTS.md:102-113` requires the section instead of hoping for it:
player-visible behaviour delivered; design choices; exact verification commands and results;
*"screenshot/video/log/metric paths you personally inspected"*; remaining risks and anything not
verified on real hardware; and *"do not claim Windows, iOS, PS5 or Switch validation unless it
actually ran on that target."*

## Why it matters

The disclosure is the cheapest evidence in the run and it is the only channel through which the
subject can report something the instrument does not measure. Two of this project's more expensive
findings were recovered from it after the fact.

Nothing is blocked while this stands, which is why the priority is 5. It is filed so it is not
re-derived from scratch a third time.

## What should be done

**Do not install this quietly.** Editing `eval/starters/*/AGENTS.md` is a regime boundary: runs
before and after stop being comparable, `judge/verify_blind.py` and `judge/starter_parity.py` must
be re-run, and the boundary is recorded in `eval/RUNS.md`. It also costs a fresh matrix — read the
current figure out of `eval/RUNS.md` rather than quoting one from memory (rule 5).

So the first move is not a code change. It is to establish the baseline offline, for free:

1. **Measure the current disclosure rate.** Read `agent.final_text` from every stored
   `agent_result.json` under `eval/runs/**`. Classify each: does it name anything the agent could
   not verify, or any risk it is leaving behind? Report the rate **per stack and per run**, with
   `n` per group - a mean over completed and aborted trials together describes nothing (rule 4).
   Classification by hand is acceptable at this scale and is more trustworthy than a regex; record
   the rule used so someone can disagree with it.
2. **Only then** decide whether the experiment is worth a matrix.

### Pre-registration - fill this in BEFORE running anything

State what each outcome would mean, so that a null is a finding rather than a disappointment.

| baseline disclosure rate | what it means | next move |
|---|---|---|
| already high (say >70% across all four arms) | the instruction would change little; the disclosures are a property of the model, not of the prompt | close as declined, record the rate |
| low and **uniform** across stacks | a real gap, and a template change is the plausible fix | worth a matrix arm if one is being run anyway |
| low and **stack-correlated** | the more interesting result, and a warning: it would mean the arms differ in how much they tell us, which biases every after-the-fact reconstruction | investigate the correlation before changing any starter |

If the experiment does run, the change must land in **all four** starters in the same words, and
`starter_parity.py`'s AGENTS.md size-and-headings comparison must be re-run: a section added to
one arm is a helpfulness difference that would be attributed to the stack.

### What not to conclude

A higher disclosure rate after the change is **not** evidence that the work got better. It is
evidence that the reporting changed. Do not let it move any tier-1 or tier-2 number, and do not
report it beside one.

Also do not import the sibling instruction from `game-research-gpt` - *"translate every acceptance
phrase into an implementation state/action and an evidence check before coding"* - as part of this.
It is plausible and there is **no offline measurement that would show it helped**, because no
stored artifact records whether an agent decomposed the prompt. If it is ever run, it must be a
separate arm, or the two changes confound each other (rule 8).
