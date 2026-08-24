---
id: 136
title: 'Make the agent harness a variable: abstract runner.py off the claude CLI and add a prime-agent arm'
status: done
priority: 2
refs: 'eval/runner.py, eval/RUNS.md, eval/PROTOCOL.md, eval/tools/tokenvalue.py, #159, #36, #31, eval/SCENES.md'
done_when: run_agent is split into per-harness argv/parse/normalise with the claude arm producing byte-identical argv to today (assert it, do not eyeball it); a prime-agent arm runs one real trial end to end and stores a record whose token counts and turns are populated and whose terminal reason maps to the shared enumeration; no cross-harness dollar comparison is produced anywhere; the isolation flags for prime-agent are established or their absence recorded with what it costs; and eval/RUNS.md gains the harness as a recorded arm dimension.
pr: https://github.com/teonimesic/game-stack-bakeoff/pull/21
established_by: 'PR #21 squash-merged. Verified independently: the stored prime-agent trial reads 2 turns, 8342 in / 254 out / 6656 cache-read, terminal_reason=completed from stopReason=stop, cost_usd=None, model gpt-5.6-sol; the raw event stream shows per-message input falling 7367 to 975, which proves usage is NOT cumulative and refutes the instruction I put in this ticket (now FINDINGS #168); agent_harness_control passes with every mutant caught; and the review tool reports ''Reviews paused'' at the final head rather than silence, so the last round''s absence is pool exhaustion and is stated in the PR thread.'
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

## note 2026-08-24

## note 2026-08-24 — prime-agent probed headless. Measured, not assumed.

Ran once in an empty scratch directory, exit 0:

    prime-agent -p --mode json --no-session "Reply with exactly: PROBE_OK"

It answered `PROBE_OK` on **`gpt-5.6-sol`**, provider `openai-codex`, api `openai-codex-responses`
— the configuration the operator described. So the arm is feasible. Four shape differences from the
claude CLI, each of which breaks a naive port:

1. **It emits JSONL, not one JSON object.** `claude -p --output-format json` gives a single object
   and `parse_agent_result` does `json.loads(stdout)`. prime-agent streams events — `session`,
   `agent_start`, `turn_start`, `message_start`, many `message_update`, `message_end`, `turn_end`,
   `agent_end`. **Read the terminal `agent_end` event**, which carries the full message list. A
   `json.loads` of the whole stdout raises, and a `json.loads` of the FIRST line silently returns
   the session header with no usage in it — the quiet wrong answer.
2. **Usage keys differ.** prime-agent: `message.usage.{input, output, cacheRead, cacheWrite,
   totalTokens}`. Claude: `modelUsage[*].{inputTokens, outputTokens, cacheReadInputTokens}`. The
   normaliser must map names, and **an absent key is a `None` to report, never a 0 to sum** (#36).
3. **`usage` is per-message, and appears repeatedly during streaming with zeros.** The probe's
   `message_start` carried `totalTokens: 0` and only the final `message_end`/`turn_end` carried
   `3912 / 7 / 3919`. Summing every event double-counts; reading the first gives zero. Take the
   terminal event, the same discipline `agent_usage`'s docstring already records for `modelUsage`.
4. **`stopReason`** is the terminal-reason field — `"stop"` on the probe. Map it into the shared
   enumeration, and surface anything unrecognised as unknown rather than bucketing it (#31).

**The baseline system prompt is ~3912 input tokens** for a one-line prompt, measured. That is the
floor to subtract before comparing per-trial input tokens across harnesses, and it is a reason the
comparison must be on tokens with the floor stated rather than on raw totals.

**It reports `cost` in USD too**, per message and per turn. That is OpenAI list price on a ChatGPT
subscription — the same defect as #159 with a second vendor, and the reason this ticket says
normalise on tokens. Do not add it to any total.

### Flags that map

| claude CLI | prime-agent |
|---|---|
| `--max-turns` | `--autonomous-max-turns` (with `--autonomous`) |
| `--allowedTools` | `-t, --tools <list>` |
| `--model` | `--model`, plus `--provider` |
| working directory | `--cwd` |
| `--output-format json` | `--mode json` |

**No `--permission-mode` equivalent was found in `--help`.** Establish how it behaves on a trial
that must write files unattended BEFORE running a matrix, and if there is no way to pre-authorise,
say so — that is a finding about whether the arm is runnable at all, not a detail.

**No isolation equivalents were found either** for `--setting-sources project` or
`--strict-mcp-config`. The claude arm uses both to keep the operator's global `CLAUDE.md` and MCP
servers out of the experiment. Find prime-agent's equivalents or record that there are none and
what that costs the comparison — an uncontrolled config difference between arms is exactly the
confound rule 8 names, and it will not appear in any artifact.

## note 2026-08-24

## note 2026-08-24 — done, on PR 21. What the next agent must not re-derive

**The address in this ticket was wrong and it cost nothing only because it was caught early.**
`eval/runner.py` is RETIRED — `run` and `check-suite` exit 2, its `template*/` trees are
deleted — so its `run_agent` is unreachable code. The live launcher is `eval/wholegame.py`,
which held its own copy of `run_agent`, `parse_agent` and `agent_metrics`. That is where the
split happened. `agent_usage`, which this ticket names, exists in neither file; it is
`agent_metrics`. **`eval/instrfollow/run.py` still carries the same duplicated claude-CLI
readers** and was left alone: separate suite, separate records, not in this ticket.

### THE TICKET'S OWN INSTRUCTION WAS WRONG, and this is the finding to number

The note above says *"Read the terminal `agent_end` event"* for prime-agent usage. It is
right for the claude CLI, where `modelUsage` is a **running total**, and wrong for
prime-agent, where `usage` is **per assistant message and not cumulative**. Measured on a
2-turn probe: assistant 1 `input 4034`, assistant 2 `input 539, cacheRead 3584`. A running
total cannot go down. Reading only the terminal event under-reports every multi-turn trial
**silently**, and the probe that produced the instruction was a ONE-turn run, where the last
event and the correct sum are the same number.

> **The general shape, and it is worth a finding number: an extraction validated on a
> population of one cannot distinguish "read the last" from "sum them all". The wrong rule
> and the right one return the same value, so the check that would fail is the one nobody
> runs — a second turn.** Same family as rule 12's "prove the extraction on one case whose
> answer you know", with the twist that the case has to be one where the candidate readings
> DISAGREE.

`eval/tools/agent_harness_control.py` pins the correct reading on a 2-message fixture built
from the real probe's numbers, and `prime reads only the terminal message` is a mutant.

### Measured facts about prime-agent 0.7.1 (openai-codex / gpt-5.6-sol)

| | |
|---|---|
| permission model | **none.** No `--permission-mode`, no command allowlist. `-p` writes files unattended through an `ipython` kernel that runs arbitrary code — verified by a probe that created a file |
| context files | `loadProjectContextFiles` walks **every ancestor of cwd to `/`** plus `~/.prime/agent`. An `AGENTS.md` one level above cwd came back through the model verbatim (`MAGPIE-4`) |
| `-nc` | suppresses all of it **including the starter's own `AGENTS.md`** (`ZEBRA-7` → `NONE`), so it cannot be the isolation flag |
| settings | `~/.prime/agent/settings.json` supplies `defaultProvider`, `defaultModel`, `defaultThinkingLevel`, and ordinary interactive use rewrites it — so the arm pins provider, model and thinking on the argv |
| resource discovery | `~/.prime/agent/{skills,extensions,prompts,themes}` and `<cwd>/.prime/agent/...` and `<cwd>/.agents/skills`. **None exist on this machine today**, which is why the guard is an assertion rather than a repair |
| system-prompt floor | **~3931–4034 input tokens** on a one-line prompt. Subtract a floor before comparing per-trial input across harnesses |
| turn ceiling | none without `--autonomous`, which changes the treatment (continuations, gate re-runs). The arm is bounded by the 4-hour harness timeout |
| hooks | no equivalent. The starters' Stop gate is wired in `.claude/settings.json`, which only the claude CLI reads |

### What landed

`eval/agent_harness.py` (argv / parse / normalise / preflight, one object per CLI),
`--harness` on `wholegame.py`, `harness` in the manifest and in every trial record,
`eval/tools/agent_harness_control.py` (52 rows, 21 mutants), the harness partition in
`census.py` and `cost_census.py` (`harness_of` and `TOKVAL_HARNESS` are defined ONCE, in
`agent_harness.py`, and imported), `eval/RUNS.md`'s fifth comparability breaker and the arm
table, `DECISIONS.md`, `eval/AGENTS.md`, `eval/PROTOCOL.md`, and the gate in `gates.yml` and
`precampaign_smoke.py`.

**The claude argv is byte-identical**, measured against `git show HEAD:eval/wholegame.py`
driven through the same call with the subprocess intercepted, in 3 configurations, with a
mutated argv as the control. That measurement cannot be repeated once this is merged; the
control keeps the argv as a literal.

**The end-to-end evidence is `eval/runs/wg-harness-probe-primeagent-2026-08-24/`** in the
MAIN checkout (gitignored, so not on the branch): 2 turns, 8342 in / 254 out / 6656
cache-read, `completed` from `stopReason: stop`, `cost_usd: null`, isolation audit stored.
**It is not a submission** — `prompt_override: true`, a 598-byte probe prompt — and it
carries `game: g1_pong` because every record does. Never pool it with a game population.

### Left for someone else

- `eval/instrfollow/run.py`'s duplicated claude readers.
- Whether a probe/non-submission record should be a partition in `census.py` rather than a
  `prompt_override` flag plus a warning in `eval/RUNS.md`.
- `--thinking` is a free parameter of the prime arm with no claude counterpart, pinned at
  `high` and recorded. Rule 16 says a free parameter is a claim until someone varies it.
