---
id: 136
title: 'Make the agent harness a variable: abstract runner.py off the claude CLI and add a prime-agent arm'
status: todo
priority: 2
refs: 'eval/runner.py, eval/RUNS.md, eval/PROTOCOL.md, eval/tools/tokenvalue.py, #159, #36, #31, eval/SCENES.md'
done_when: run_agent is split into per-harness argv/parse/normalise with the claude arm producing byte-identical argv to today (assert it, do not eyeball it); a prime-agent arm runs one real trial end to end and stores a record whose token counts and turns are populated and whose terminal reason maps to the shared enumeration; no cross-harness dollar comparison is produced anywhere; the isolation flags for prime-agent are established or their absence recorded with what it costs; and eval/RUNS.md gains the harness as a recorded arm dimension.
---

`eval/runner.py`'s `run_agent()` hardcodes the `claude` CLI in its argv, and `parse_agent_result`
and `agent_usage` read Claude-CLI JSON specifically - `modelUsage`, `total_cost_usd`, `usage`,
`num_turns`. So "which agent harness built this" is currently a constant, not a variable, and
every result this project has is a statement about one harness.

The operator wants a GPT-based arm. `prime-agent` 0.7.1 is installed and configured against a
ChatGPT subscription; it exposes `--print`, `--mode json`, `--cwd`, `--model`, `--provider` and
`--thinking`, which map onto what `run_agent` needs. `codex` is also installed but is **0.46.0
against a current 0.149.1**, so it is not a candidate until upgraded (`brew upgrade codex`, or the
npm `@openai/codex` build) - decide whether to bother, and say why either way.

## What has to be abstracted, and what must not be

Split `run_agent` into: build argv, run, parse result, normalise usage. One harness object per
CLI. The rest of the runner should not learn a second vocabulary.

**Normalise to TOKENS AND TURNS, not to dollars.** Every `$` figure this project produces is a
list-price valuation of tokens on a subscription account and is not an expenditure (#159). Across
two vendors with different published rates it is worse than that: a cross-harness dollar
comparison is a comparison of two price lists, not of two agents. Token counts and wall-clock are
the comparable quantities; if a harness reports no token count, that is a `None` to be reported,
never a zero to be summed (#36, and `runstat --selftest` pins exactly this).

Terminal reasons must map per harness. `budget_exhausted`, `max_turns` and `harness_timeout` are
Claude-CLI vocabulary; whatever prime-agent reports has to land in a shared enumeration, with
anything unrecognised surfacing as unknown rather than being quietly bucketed. Every reason not to
count a failure is a channel a bug can widen (#31).

## The isolation the current arm gets, which the new one also needs

The claude arm passes `--setting-sources project` to keep the operator's global CLAUDE.md out,
and `--strict-mcp-config` to keep their MCP servers out. Establish the equivalents for
prime-agent, or record that there are none and what that costs the comparison - an uncontrolled
config difference between arms is exactly the confound rule 8 is about, and it will not be visible
in any artifact.

## What NOT to do

Do not launch a scene run and a harness run as the same experiment. Scenes (133/134) are one new
variable and the harness is another; each cell differing in two ways is the failure this project
has paid for twice. Cross them deliberately as a factorial design, or sequence them.
