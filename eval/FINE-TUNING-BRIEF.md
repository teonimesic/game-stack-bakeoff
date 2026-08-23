# Fine-tuning brief: make each stack's template as good as that stack can be

> ### The TREES this briefed are deleted (2026-08-23); the PRINCIPLE is live and moved
>
> "template" here means the four `template*/` Pong trees, retired with the spec-change suite
> (`DECISIONS.md`, #122). The principle they were fine-tuned under — **hold the tasks constant,
> tune each stack to its own best rather than to a common floor** — survived them and now governs
> `eval/starters/*/`. It is stated as a decision in `DECISIONS.md`, *"The templates are measured at
> each stack's best, not at a common floor"*, which is where to read it as current policy.
>
> Kept because it is the reasoning behind that decision, and because the 71 stored spec-change
> trials were run against trees built to this brief.

## The methodological point

The first round of templates were **faithful parity ports** of the Rust/Bevy one. That was the
wrong instruction. Forcing every stack into Bevy's shape measures "how well does this stack
imitate Bevy", not "how well can an agent build a game in this stack".

**Hold the TASKS constant. Fine-tune the TEMPLATES.**

Each template should be the best version of itself: idiomatic for its stack, using its stack's
strongest tooling, giving an agent the highest realistic chance of success. If a stack has an
affordance the others lack, it should USE it — that advantage is a real property of the stack and
the comparison should surface it, not erase it.

## What must stay identical (or the comparison is void)

1. The same game with the same constants.
2. The same three task prompts, byte-identical.
3. The same held-out grading criteria — the tasks are graded on behaviour, not implementation.
4. `just verify` as the single gate, exiting non-zero on any failure.
5. The three verification layers must all genuinely exist: unit/simulation, deterministic replay,
   and REAL rendered-pixel assertions. No stack may skip a layer or fake it.

## What should now differ, deliberately

Each stack should add whatever gives an agent the best chance in that stack:

- **Hexagonal boundary enforcement.** The sim/view split must be enforced by the strongest
  mechanism the stack offers, not by convention. Compiler-enforced beats lint-enforced beats
  documented. Add a test that FAILS if the boundary is violated, and make it a real check.
- **Stack-native static checking turned up as far as it will go** — analyzers, strict lint rules,
  type-level guarantees, warnings-as-errors.
- **Fast feedback.** The inner loop should be as fast as the stack allows; if a slow path exists,
  give the agent a documented fast alternative.
- **Failure legibility.** When a test fails, the message must tell an agent what to do next.
  Attach artifacts (diff images, traces, logs) where the stack supports it.
- **Version grounding** in the stack's own idiom (vendored llms.txt, API delta notes, analyzer
  rules that catch stale idioms).

## The bar

An expert in that stack, asked "is this the best template you could hand an agent for this
engine?", should say yes. Where you deliberately diverge from the Rust template, say so and say
why — divergence is now expected, but it must be justified rather than accidental.
