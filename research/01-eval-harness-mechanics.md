# Eval harness mechanics — verified empirically 2026-08-10

Claude Code CLI 2.1.220 on macOS (darwin 25.2.0).

## Blank-session invocation

```
cd <fresh-work-dir> && claude -p "<task>" \
  --output-format json \
  --model <fable|opus|sonnet> \
  --max-turns N \
  --setting-sources project
```

## VERIFIED: experimental control over the global CLAUDE.md

The user's global `~/.claude/CLAUDE.md` (which mandates TDD and `rm -f`) **contaminates
blank sessions by default**. This would mask the effect of any TDD guidance we put in the
template — a fatal confound for the eval.

Empirical probe (asked the agent to self-report whether those rules were in its context):

| Arm | Flags | RMF rule seen | TDD rule seen |
|---|---|---|---|
| A | *(default)* | yes | yes |
| B | `--setting-sources project` | **no** | **no** |

=> **`--setting-sources project` is the required flag for every eval run.** It gates
user-level memory while leaving authentication working.

## REJECTED: `HOME` isolation
Overriding `HOME` to a sandbox dir kills auth (`"Not logged in · Please run /login"`) —
credentials live outside the overridden HOME. Do not use. `--bare` has the same problem
(requires `ANTHROPIC_API_KEY`). `--setting-sources project` achieves the isolation we
actually need without touching credentials.

## Output schema (`--output-format json`)

Returns a **JSON array** of message objects; the run summary is the element with
`type == "result"` (take the last). Parse defensively — it is not a bare object.

Fields useful for grading/telemetry:

| Field | Use |
|---|---|
| `result` | final assistant text |
| `is_error`, `terminal_reason`, `api_error_status` | run health; `terminal_reason: "api_error"` |
| `num_turns` | efficiency metric |
| `total_cost_usd` | cost metric (sonnet 1-turn probe ≈ $0.03) |
| `duration_ms`, `duration_api_ms` | wall-clock metric |
| `usage.{input_tokens,output_tokens,cache_read_input_tokens,cache_creation_input_tokens}` | token accounting |
| `permission_denials` | detects harness friction — should be empty in a well-configured run |
| `session_id`, `uuid` | correlate to transcript for failure-mode analysis |
| `stop_reason` | e.g. `stop_sequence` |
| `modelUsage` | per-model breakdown |

`--output-format stream-json` + `--include-partial-messages` gives the full turn-by-turn
transcript for failure-taxonomy analysis (tool-call counts, thrash/loop detection).

## Other relevant flags
- `--allowedTools` / `--disallowedTools` — restrict the action space per eval arm
- `--permission-mode` — `acceptEdits|auto|bypassPermissions|manual|dontAsk|plan`
- `--append-system-prompt` / `--system-prompt` — inject instruction variants without
  touching repo files (useful for ablations that must not change the git diff)
- `--session-id <uuid>` — pin session IDs for reproducible correlation
- `--agents <json>` — inject custom subagent definitions per arm
- `--json-schema` — structured output, useful for forcing a machine-gradable self-report
- `--fallback-model` — resilience for long unattended eval batches

## Gotchas
- macOS has no `timeout`; use `gtimeout` (coreutils) or a shell-level watchdog.
- Nested `claude ... --dangerously-skip-permissions` is blocked by the auto-mode
  classifier when spawned from inside Claude Code. Use `--permission-mode` +
  `--allowedTools` instead, or run eval batches from a plain terminal.
- Each `cd` in a compound command can reset cwd; wrap runs in an explicit subshell.
