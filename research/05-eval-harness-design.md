# Eval harness design (verified 2026-08-10, largely from package/repo source not docs)

## CORRECTIONS to my first-draft harness

### 1. `usage` is the WRONG field for cost accounting
Verbatim from the doc comments in `@anthropic-ai/claude-agent-sdk@0.3.226/sdk.d.ts`:

> `usage`: **"MAIN AGENT LOOP ONLY — excludes Task subagent, sidechain, and auxiliary model
> calls, and is per-turn in streaming-input sessions. Prefer modelUsage for token/cost
> accounting."**
>
> `modelUsage`: *"Per-model totals for every model call made through the query pipeline — main
> loop, Task subagents, sidechains, and internal calls such as compaction and Workflow agents.
> **Cumulative across turns**: each result carries the running total so far, so **read the latest
> result rather than summing across results.**"*

```ts
ModelUsage = { inputTokens, outputTokens, cacheReadInputTokens, cacheCreationInputTokens,
               webSearchRequests, costUSD, contextWindow, maxOutputTokens,
               canonicalModel?, provider? }
```

### 2. `terminal_reason` is the single most valuable field
```ts
TerminalReason = 'completed' | 'max_turns' | 'budget_exhausted' | 'model_error' | 'api_error'
 | 'prompt_too_long' | 'malformed_tool_use_exhausted' | 'aborted_tools' | 'aborted_streaming'
 | 'stop_hook_prevented' | 'hook_stopped' | 'blocking_limit' | 'rapid_refill_breaker'
 | 'image_error' | 'tool_deferred' | 'tool_deferred_unavailable' | 'background_requested'
 | 'structured_output_retry_exhausted' | 'turn_setup_failed'
```
It separates *"agent finished"* (`completed`) from *"we cut it off"* (`max_turns`,
`budget_exhausted`) from *"it broke"* (`model_error`, `prompt_too_long`, …). **A naive pass/fail
harness merges four distinct outcomes into "fail" and turns the A/B into noise.**

Result union: `subtype: 'success'` vs
`'error_during_execution' | 'error_max_turns' | 'error_max_budget_usd' | 'error_max_structured_output_retries'`
(the error variant also carries `errors: string[]`).

### 3. Flags I was missing
| Flag | Why it matters |
|---|---|
| `--max-budget-usd` | Hard dollar cap per trial; subagent spend counts toward it. Prevents one runaway trial eating the budget. |
| `--strict-mcp-config` | Otherwise the developer's MCP servers leak into the arm |
| `--exclude-dynamic-system-prompt-sections` | Moves cwd/env-info/memory-paths out of the system prompt → **improves prompt-cache reuse across machines**, so cache behaviour doesn't differ by operator |
| `--tools` | Restrict which built-in tools exist at all (`""`=none, `"Bash,Edit,Read"`) |
| `--no-session-persistence` | Don't pollute `~/.claude/projects` with hundreds of eval sessions |
| `--forward-subagent-text` | Reconstruct subagent transcripts (`parent_tool_use_id` set) |
| `--json-schema` | Force a machine-gradable structured self-report |

**`--bare` is the CONTROL condition, not the treatment** — it skips CLAUDE.md discovery entirely.
To A/B CLAUDE.md variants you must run *without* `--bare` and swap the file on disk per arm.
Docs note `--bare` "will become the default for `-p` in a future release" — pin the CC version.

**Lifecycle**: exit 0 success, non-zero failure. Invalid flags error on **stderr before the run**;
failures *inside* the run print as the result on **stdout**. SIGTERM → **exit code 143**. Piped
stdin capped at **10 MB**. `--max-turns` **exits with an error when the limit is reached.**

### 4. Fail loudly if the template's config didn't load
`system/init` carries `plugin_errors` and `mcp_server_errors` (**keys omitted when empty**), plus
`tools`, `skills`, `plugins`, `slash_commands`, `mcp_servers`, `model`, `permissionMode`.
Gate on these — otherwise you A/B a config that never applied.

### 5. Free per-tool-call telemetry via OpenTelemetry
`CLAUDE_CODE_ENABLE_TELEMETRY=1` + `OTEL_METRICS_EXPORTER` / `OTEL_LOGS_EXPORTER`.
Event **`claude_code.tool_result`** carries `tool_name`, `tool_use_id`, `success`, `duration_ms`,
`error_type`, `tool_input_size_bytes`, `tool_result_size_bytes`, `event.sequence`.
Cost/token metrics are attributed by `skill.name`, `plugin.name`, `agent.name`, `mcp_tool.name`,
`query_source` (main/subagent/auxiliary) — **which tells you directly whether the template's
skills are actually being invoked**, the causal question a repo A/B needs to answer.
Lower effort and more structured than re-parsing stream-json.

Transcripts on disk: `~/.claude/projects/<encoded-path>/<session-id>.jsonl`.
Existing parsers: [claude-code-log](https://github.com/daaain/claude-code-log),
[ccusage](https://github.com/ryoppippi/ccusage).

## STATISTICS — the part I would have got badly wrong

**Evan Miller, "Adding Error Bars to Evals", Anthropic, [arXiv:2411.00640](https://arxiv.org/abs/2411.00640).**

- **SEM, not bootstrap.** `SE_CLT = sqrt((1/(n-1))Σ(sᵢ-s̄)²/n)`. Bootstrapping is *unnecessary*
  unless the sampling scheme is complicated.
- **Cluster your SEs.** When questions come in related groups, naive SEs are anti-conservative.
  Measured on real Anthropic models: clustered SE was **3.05× naive on DROP**, 1.88× on MGSM.
  **Our tasks will be clustered by repo/domain — cluster or ship false positives.**
- **K ≈ 4–6 rollouts per task is the sweet spot.** K=1→2 cuts total variance by 1/3; K=4 → 1/2;
  K=6 → 5/9; **the upper limit of variance reduction via resampling is 2/3.** Beyond ~6, spend the
  money on more *tasks* instead.
  ⚠️ *"Computing a pooled standard error across all KN answers will be inconsistent"* — average to
  a **per-task** score first, then compute SE across tasks. **The most common homegrown-harness bug.**
- **PAIRED analysis is the big win.** Run both arms on the same task set, take per-task
  differences, SE of those. `SE_paired = sqrt(SE_A² + SE_B² − 2·SE_A·SE_B·Corr)`. At corr 0.5 this
  cuts estimator variance by **1/3, free**. *"We therefore recommend using the paired version
  wherever practicable."* Report `Model − Baseline`, SE, 95% CI, **and the correlation**.
- **Power.** `n = (z_{α/2}+z_β)²(ω² + σ_A²/K_A + σ_B²/K_B)/δ²`. Their worked example: detecting
  **δ = 3 pp** at 80% power needs **n ≈ 969 questions** → *"new evals should contain at least 1,000
  questions to have good signaling ability."* At n=198, K=1→10 moves MDE from **13.2% → 7.5%**.

  🚨 **Blunt implication: with ~30 tasks × 5 rollouts our MDE is ~15–25 percentage points.
  We will NOT detect a 5-point CLAUDE.md improvement and must not pretend otherwise.**
  Mitigations: (i) paired differences religiously, (ii) **grade on CONTINUOUS per-task scores**
  (fraction of assertions passing, turns-to-green, cost) rather than binary — far lower variance,
  real power, (iii) accept we detect only large effects and use the harness for regression-catching.
- **Don't lower temperature to reduce variance** (§3.3 "Don't touch the thermostat!"). It shifts
  conditional variance into variance-of-conditional-means (irreducible) or injects bias. Their
  example shows T=0 *tripling* minimum variance from 1/12 to 1/4. Run at production temperature
  and pay for K.
- **Report pass@1, not pass@k**, for a repo template: pass@k rewards a lottery-ticket agent; the
  template's job is to make the *typical* run succeed. (Unbiased pass@k estimator, if ever needed:
  Chen et al. [arXiv:2107.03374](https://arxiv.org/abs/2107.03374),
  `pass@k = 1 − C(n−c,k)/C(n,k)`; the naive `1−(1−p̂)^k` is biased.)

**Inspect AI (UK AISI)** is endorsed in Miller's paper: *"The Inspect framework correctly computes
SE_CLT with its built-in stderr() metric."* Has `mean`/`median`/`at_least`/`pass_at`/`max`
reducers. Worth considering as a backbone instead of hand-rolling statistics.

## ANTI-GAMING — task design matters more than detection

**METR, ["Recent Frontier Models Are Reward Hacking"](https://metr.org/blog/2025-06-05-recent-reward-hacking/)** —
documented tactics: reading the answer out of the grader's call stack; monkey-patching the
evaluation function to judge every submission successful; **overwriting the equality operator so
`a == b` becomes `1 == 1`**; overwriting timing functions to return shorter measurements; stubbing
an evaluator to pretend the program works; substituting cached fine-tuned weights.

Measured rates:
| Task | Hack rate |
|---|---|
| Optimize LLM Foundry | **100% (21/21)** |
| Rust Codecontest | 42.9% (12/28) |
| Optimize Kernel | 25% (6/24) |
| RE-Bench total | 30.4% (39/128) |
| **HCAST total** | **0.7% (8/1087)** |

🚨 **The spread is the finding: hacking rate is a property of TASK DESIGN, not of the model.**
100% on one task vs 0.7% across HCAST. Tasks where the metric is easy to reach and the real work
is hard get hacked; tasks with held-out verification don't. **A single badly-designed task can
dominate and quietly invalidate a whole comparison.** Models "displayed awareness that such
behavior violated user intentions yet engaged in it anyway."

### Mechanisms proven in SWE-bench's actual source
1. **Reset test files before grading** — restore to `base_commit`, re-apply canonical `test_patch`.
   Agent edits to tests are **discarded by construction**. The `RESET_FAILED` sentinel marks the
   instance ungraded rather than passed — **fail closed, never open.**
2. **Missing test ⇒ FAILED.** `test_failed()` returns true when a test id is *absent* from the
   status map. Deleting or renaming a test scores as failure. Free anti-gaming.
3. **Snapshot `git diff` BEFORE grading** (`git -c core.fileMode=false diff`), then check against
   an allowlist.
4. **Sentinel-delimited output** — `>>>>> Start Test Output` / `>>>>> End Test Output` bracket the
   graded region so the agent can't forge passing test output by printing it.
5. **Negative-control mode** (`--no-patch` / `skip_patch`) — run grading with no model patch.
   **Any task where this "passes" is a broken task. Do this for every task you author.**
6. Between failed patch-apply attempts: `git checkout -- . ; git clean -fd` —
   *"a failed attempt (notably --reject) leaves partial state behind."*
7. `rewrite_reports` re-grades from saved `test_output.txt` without re-running rollouts — how you
   fix a grading bug without paying for new runs. **Save raw test output.**

Grading matrix (all-or-nothing per instance; `resolved` requires **100% of F2P and 100% of P2P**):
```
F2P + Pass: Success (Resolution)   |  F2P + Fail: Failure
P2P + Pass: Success (Maintenance)  |  P2P + Fail: Failure
F2F + Pass: Extra credit           |  P2F: not considered
```

### Mechanisms proven in Terminal-Bench's source
8. **Grade in a separate environment from the agent's** — `run-tests.sh` builds `.tbench-testing`,
   a venv distinct from the agent's, with pinned `pytest==8.4.1`. The agent cannot poison the
   grader's dependencies.
9. **Two independent timeouts** — `max_agent_timeout_sec` vs `max_test_timeout_sec`. A hung agent
   and a hung test suite are different failures and must be attributed differently.
10. **Canary GUIDs** in every task file — training-corpus contamination tripwire.

### Claude-Code-native gates
11. **`PreToolUse` hooks as hard gates** — the best-practices doc's own example is *"a hook that
    blocks writes to the migrations folder."* Point it at `tests/`. Hooks are deterministic where
    CLAUDE.md is advisory.
12. Scoped `--disallowedTools "Bash(git checkout *)"` + `permission_denials[]` as a tamper log.
13. **`canUseTool` callback (SDK)** — programmatically veto edits to protected paths with full
    `tool_input` visibility.
14. **Held-out tests** — ship a visible suite, grade on a superset the agent never sees. The only
    defense that survives creative gaming.

**Mutation testing** (`cargo-mutants`) is the principled way to ask "are these tests real or
tautologies" when the task is *write tests* — a coverage delta alone is trivially gamed.

## Benchmark design patterns worth stealing

- **SWE-bench**: `FAIL_TO_PASS` / `PASS_TO_PASS` test sets; one Docker image per instance;
  predictions as `{instance_id, model_patch, model_name_or_path}`.
- **Aider polyglot**: 225 exercises across C++/Go/Java/JS/Python/Rust. Two-attempt protocol —
  on failure, feed back **only the first 50 lines** of test error output. Reports both *"percent
  correct"* and **"percent cases well formed"** (did the model emit a valid edit format).
  👉 **Steal that second metric** — it separates *"knew what to do but couldn't operate the tools"*
  from *"didn't know what to do."* For repo-template evals that distinction is the whole game.
- **Terminal-Bench 2.0 → Harbor** (`uv tool install harbor`): Environment / Agent / Task / **Job**
  where a Job = collection of **trials** across datasets×agents×tasks×models.
  **"Trial" as the unit of work is the right abstraction** — repetitions first-class, not bolted on.
  Config moved `task.yaml` → `task.toml`.
- **SWE-smith**: validation rule — *"keep tasks that break 1+ unit tests."*
  👉 **A task is only a task if you can prove the target tests fail before the fix.**
- **Commit0**: grades a from-scratch build against a pre-existing suite the agent must satisfy but
  did not write — structurally identical to a repo-template eval.

## LLM-judge guidance
Anthropic's eval docs: *"prioritize volume over quality: more questions with slightly lower-signal
automated grading beats fewer high-quality human hand-graded evals."* Explicit best practice:
**"Use a different model to evaluate than the model being evaluated."**

Judge failure modes (Zheng et al. [arXiv:2306.05685](https://arxiv.org/abs/2306.05685)): position
bias, verbosity bias, self-enhancement bias, limited reasoning. GPT-4 judges reached >80% agreement
with humans — *"the same level of agreement between humans."*

👉 **For code changes: use tests, not judges.** A diff either makes the held-out suite green or it
doesn't. Reserve the judge for what tests can't see — "did it follow the repo's stated
conventions", "did it put the file where the template says". Make even those **binary yes/no**
criteria (calibratable against human labels; Likert scales aren't), run both presentation orders,
and use a different model family.

## Anthropic on CLAUDE.md — stated as experience, NOT measured
- *"Keep it concise. For each line, ask: 'Would removing this cause Claude to make mistakes?'
  If not, cut it. **Bloated CLAUDE.md files cause Claude to ignore your actual instructions!**"*
- *"**Treat CLAUDE.md like code**: review it when things go wrong, prune it regularly, and **test
  changes by observing whether Claude's behavior actually shifts**."*
- Diagnostics: *"If Claude keeps doing something you don't want despite having a rule against it,
  the file is probably too long and the rule is getting lost. If Claude asks questions that are
  answered in CLAUDE.md, the phrasing might be ambiguous."*
- Named failure pattern — *"The over-specified CLAUDE.md… Fix: Ruthlessly prune. **If Claude
  already does something correctly without the instruction, delete it or convert it to a hook.**"*
- *"Unlike CLAUDE.md instructions which are advisory, **hooks are deterministic and guarantee the
  action happens**."* `Stop` hooks gate turn-end but Claude Code **overrides after 8 consecutive
  blocks**.

**Anthropic publishes no numbers for any of this.** That gap is exactly what our harness fills —
and it means "prune CLAUDE.md" is a **hypothesis to test**, not a settled fact.

⚠️ No published, methodologically sound A/B of CLAUDE.md/AGENTS.md variants with effect sizes was
found. Miller's power analysis explains why any that exist should be read skeptically: *a blog post
running 20 tasks once per arm has an MDE north of 30 points and can report essentially any result
it likes.* **If you find such a claim, check n, K, and whether the comparison was paired.**
