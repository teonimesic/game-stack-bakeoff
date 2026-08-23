# Stack bake-off design

> ### RETIRED 2026-08-23 — history, kept because 71 stored trials are read against it
>
> This describes the **spec-change** suite: three small tasks against a finished Pong, run by
> `eval/runner.py --template`. It **cannot be run**: the four `template*/` trees were deleted
> (`DECISIONS.md`, #119), and `eval/run-bakeoff.sh` with them. It has not run since 2026-08-12.
>
> **Its answer, and the reason it was not repeated: it did not separate the four stacks.** All
> four scored 6/6. `eval/AGENTS.md` states the design limit — this suite resolves large gaps only.
>
> Still live, and what to read instead: **`eval/PROTOCOL.md`** for the whole-game matrix that
> replaced it, and `eval/RUNS.md` for what every run cost. Still readable from here: the 71 trials
> in `eval/runs/{bakeoff,core}-*`, via `runner.py report` and `regrade.py`, with the task text in
> `eval/suites/`.

Purpose: pick the template's stack on measured agent performance, not on paper tradeoffs.

## Why a bake-off at all

Research so far surfaces a genuine, unresolvable-on-paper tension:

- **Rust/Bevy** has the best verification *signal* (compiler as harness, `bevy_brp_mcp` giving
  the agent live ECS query + screenshot + input injection) and the **worst** feedback *latency*
  (10–15 s incremental, 105–158 s clean, measurably 22% worse over the last 6 months) plus the
  **worst API churn** (agents "confidently implement an imagined Bevy 0.17 API").
- **Godot + C#** is the documented consensus best-fit for Claude Code (text-serialized scenes,
  `--headless`, huge training density, mature editor, real iOS + console paths).
- **TypeScript/web** has the best automated testing story (Playwright, headless Chrome, pixel
  diffing) and the highest training density, but the weakest native/console story.

Nobody has published a head-to-head. So measure it.

## Controlled variables

Every arm gets the identical treatment:
- Same three tasks, same prompts (modulo stack-specific command names).
- Same scaffold quality: a minimal working project + a `just verify` entrypoint + a README
  stating the verification command. **No stack gets a hand-tuned CLAUDE.md in the bake-off** —
  instruction tuning is a *later*, separate experiment (task #5), and mixing them would confound.
- `--setting-sources project` on every run (isolates the user's global CLAUDE.md — verified
  necessary, see research/01).
- Same model, same `--max-turns`, N trials per cell.

## The three tasks

Each targets a distinct failure mode the research identified.

### B1 — API fluency under churn
*"Add a second player entity controlled by WASD that cannot leave the play area."*

Measures the dominant Rust/Bevy risk directly: does the agent write code against the **pinned,
current** engine API, or against a remembered older one? Graded by compile/run + held-out
behavioural tests. Expect Bevy to underperform here; the question is by how much, and whether
in-repo doc grounding closes the gap (that becomes an arm in the instruction experiment).

### B2 — Pure simulation logic, no engine API
*"Implement the scoring and round-reset rules to satisfy the given test signatures."*

Isolates baseline language competence with the engine held out of the picture. This is the
control: if a stack loses B1 but wins B2, the deficit is churn, not language.

### B3 — Render-and-prove (the E2E loop)
*"Make the ball visibly change colour when it hits a paddle, and prove it with an automated
check that inspects the rendered output."*

Measures whether the agent can actually close the render-verify loop the template provides —
the entire point of the template. Graded on whether a held-out screenshot/pixel assertion passes.

## Metrics per trial

From the harness (`eval/runner.py`, all already captured):
- `passed` (held-out tests, tampering-gated)
- `num_turns`, `total_cost_usd`, `wall_s`
- `permission_denials` (harness friction)
- tampering findings (test deletion, `#[ignore]`, `--no-verify`, assertion tautologies)
- failure taxonomy, notably **`holdout_failed(agent_thought_it_passed)`** — the agent's own
  verify passed but held-out tests failed. This is the "tests pass ≠ correct" signal and the
  single most diagnostic number for template design.

## Statistics

With N=5 trials/cell, only large effects are detectable. The harness reports **Wilson score
intervals**, which behave correctly at small n unlike the normal approximation. Treat
non-overlapping intervals as a real difference and overlapping ones as "not resolved" — do not
over-claim from 5 runs. Where arms tie, prefer the stack on the qualitative criteria
(iOS/console path, open-source licence, portability).

## Decision rule, fixed in advance

1. If one stack wins B1+B2+B3 with non-overlapping intervals → pick it.
2. If results are mixed → weight **B3 highest** (it is the template's reason to exist), then B1.
3. If two stacks tie → break the tie on the user's stated constraints in this order:
   performance ceiling → iOS support → console path → open-source licence.
4. Record the decision and the evidence in `research/DECISION.md` before building the template.
