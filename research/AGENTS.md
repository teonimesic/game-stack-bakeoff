# research/ — the briefs

Twelve briefs answering the original questions, plus `DECISION.md`.

| File | Covers |
|---|---|
| `00-prior-art.md` | Existing agent-oriented templates and what they get wrong |
| `01-eval-harness-mechanics.md` | How to drive agents reproducibly |
| `02-templates-and-agent-conventions.md` | `AGENTS.md` conventions, instruction design |
| `03-rust-engines.md` | Bevy and the Rust field |
| `04-backend-netcode-determinism.md` | Netcode, rollback, determinism recipes |
| `05-eval-harness-design.md` | Controls, held-out tests, anti-gaming |
| `06-non-rust-stacks.md` | TypeScript, Unity, Godot, MonoGame, Unreal |
| `07-loop-and-schedule-graph.md` | Fixed timestep, schedule ordering, ambiguity |
| `08-agent-performance-evidence.md` | Published measurements of agent coding performance |
| `09-game-testing-sota.md` | Rendering tests, play-bots, frame verification |
| `10-stack-capability-matrix.md` | **What each stack can do at its pinned version**, with effort and Apple-silicon conditionality marked, and what is unresolved. The evidence base `DECISIONS.md` requires task 26 to cite |
| `11-doc-linting-for-agents.md` | **Prose and markdown linting for documentation read by agents.** Eleven tools run against this repository; what each found; why the recommendation is to adopt none of them, and what to do instead |
| `DECISION.md` | The stack choice made from the briefs |

## `DECISION.md` is a prior, not evidence

It chose a stack from research alone. That was the wrong method for the question being asked, and
two of its eliminations were wrong on the facts — Godot and Unity were both readmitted and
measured. **The bake-off is the evidence; this file is what was expected beforehand.**

Anything here that the measurement has since settled should point at the measured result rather
than restate the prediction.

## Standards for a claim

These briefs are cited elsewhere in the repo, so a wrong claim propagates.

- **Date every claim**, and name the version it applies to. This field moves fast — Bevy published
  ~840 breaking-change entries across eight releases, and a claim without a version is unusable.
- **Source every claim.** Link the release notes, the issue, the paper, the vendored source.
- **Label unverified claims as unverified.** An unlabelled guess is indistinguishable from a
  measured fact once it is quoted somewhere else.
- **Prefer the vendored source over documentation, and documentation over memory.** Reading
  `~/.cargo/registry` is the fastest ground truth available and is always the version actually
  being compiled against.
- When a brief's claim is later measured, **replace it with the measurement** — do not leave the
  prediction standing beside the result.
