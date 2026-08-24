#!/usr/bin/env python3
"""WHICH AGENT CLI BUILT A TRIAL, as a variable rather than a constant.

Until 2026-08-24 `wholegame.py` spelled the `claude` CLI into its argv, read Claude-CLI
JSON out of its stdout, and stored the result under Claude-CLI field names. Every number
this project holds is therefore a statement about one harness, and nothing said so.

This module is the split the rest of the runner reads through: **build argv, parse
stdout, normalise the result.** One object per CLI, and the runner learns no second
vocabulary.

    argv(...)       the exact command line, per harness
    parse(...)      stdout -> the harness's own result object (also what gets stored)
    normalise(...)  that object -> the trial record's `agent` block, shared field names
    preflight(...)  the isolation this arm needs, asserted at launch, and its audit trail

## What normalises, and what MUST NOT

**Tokens and wall clock normalise. Dollars do not, and turns do not without their
definition.**

Every `$` figure this project produces is `tokval` — a list-price valuation of tokens on a
subscription account, not an expenditure (#159). Across two vendors it is worse than that: a
cross-harness dollar comparison compares two published price lists, and neither vendor was
paid per token. So `cost_usd` is populated **only** for a harness whose figure `tokenvalue.py`
covers, and is `None` — never `0` — for any other (#36: an absent count is reported, never
summed as zero). prime-agent's own USD figure is stored under
`vendor_cost_usd_not_comparable`, whose name is the documentation at every read site.

**Turn counts are per-harness units.** The `claude` CLI's `num_turns` counts every turn in
its loop; prime-agent has no such counter, so this module counts assistant messages. Both
are recorded, and every record carries `turns_definition` beside the number so no reader has
to guess which was which.

## The terminal reason is mapped, and an unrecognised one stays unrecognised

`TERMINAL_REASONS` is the shared enumeration; it is the `claude` vocabulary because 161
stored records already use it. A harness value with no measured mapping becomes
`unknown:<raw>` rather than being bucketed into the nearest member — every reason not to
count a failure is a channel a bug can widen (#31).

**`None` is not `unknown`.** A killed trial stores `terminal_reason: null` and `eval/RUNS.md`
documents those records; absent stays absent.

**The prime-agent map has ONE measured entry** (`stop` -> `completed`). Entries are added by
observing a value in a stored run, never by guessing from the CLI's help text.

## prime-agent, measured 2026-08-24 (0.7.1, provider openai-codex, model gpt-5.6-sol)

| | |
|---|---|
| output | **JSONL, one event per line.** `json.loads(stdout)` raises; `json.loads(first line)` silently returns the `session` header, which carries no usage — the quiet wrong answer. The totals live in the terminal `agent_end` event's `messages` list |
| usage | `message.usage.{input, output, cacheRead, cacheWrite, totalTokens}`, **per assistant message and NOT cumulative** |
| terminal reason | `stopReason` on the last assistant message |
| USD | reported per message and per turn. OpenAI list price on a ChatGPT subscription — #159 with a second vendor |
| tools | one `ipython` kernel that runs arbitrary code. There is no `--permission-mode` and no command allowlist: a `-p` run writes files unattended, measured |

> **`modelUsage` IS cumulative and prime-agent's per-message `usage` IS NOT, so the two
> harnesses need opposite readers.** Measured on a 2-turn probe: the first assistant message
> reports `input 4034`, the second `input 539, cacheRead 3584`. A running total cannot go
> down. Reading only the terminal event — which is what the ticket that commissioned this
> module instructed, having probed a ONE-turn run where the last event and the total are the
> same number — under-reports every multi-turn trial and does it silently. Sum the assistant
> messages; the probe that would have caught it is any run with two model calls in it.

## The isolation the claude arm gets, and what prime-agent has instead

The claude arm passes `--setting-sources project` (the operator's global `CLAUDE.md` stays
out) and `--strict-mcp-config` (their MCP servers stay out). **prime-agent has no equivalent
of either, and its one nearby flag is strictly too strong.** Measured, both directions:

| | cwd's own `AGENTS.md` | an `AGENTS.md` one directory ABOVE cwd |
|---|---|---|
| no flag | read (`ZEBRA-7` came back) | **read** (`MAGPIE-4` came back) |
| `-nc` | **not read** (`NONE`) | not read — same code path |

`loadProjectContextFiles` walks every ancestor of cwd to `/` and also loads a global context
file from `~/.prime/agent`. `-nc` disables the lot, **including the starter's own
`AGENTS.md`** — which is the product the trial exists to measure, so the flag cannot be the
isolation mechanism.

So isolation here is an **assertion, not a flag**: `preflight()` refuses to launch when a
context file sits above the trial tree or in the agent directory, and when the agent
directory holds discoverable skills, extensions, prompts or themes. It returns what it
checked, and that goes into the trial record — a guard that leaves no trace cannot be
distinguished afterwards from one that never ran.

**Model, provider and thinking level are pinned on the argv** because
`~/.prime/agent/settings.json` otherwise supplies them: it holds `defaultProvider`,
`defaultModel` and `defaultThinkingLevel` and is rewritten by ordinary interactive use, so an
unpinned arm is configured by whatever the operator last selected in the TUI.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

#: The shared terminal-reason enumeration. `claude` vocabulary, because the stored corpus
#: is written in it; a harness that reports something else is MAPPED into it or surfaces
#: as `unknown:<raw>`.
TERMINAL_REASONS = frozenset({
    "completed", "max_turns", "budget_exhausted", "harness_timeout",
    "api_error", "session_limit", "error",
})

#: Prefix for a terminal reason no measurement has mapped. Never a bucket.
UNKNOWN_PREFIX = "unknown:"

#: Context-file names prime-agent looks for, in its own order. `loadContextFileFromDir`
#: takes the FIRST that exists, which is why a starter carrying both `AGENTS.md` and a
#: `CLAUDE.md` that only says `@AGENTS.md` feeds both harnesses the same guide.
CONTEXT_FILENAMES = ("AGENTS.md", "AGENTS.MD", "CLAUDE.md", "CLAUDE.MD")

#: Resource kinds prime-agent discovers under its agent directory. Anything found here
#: enters every trial and appears in no artifact.
RESOURCE_DIRS = ("skills", "extensions", "prompts", "themes")


def unknown_reason(raw: Any) -> str:
    return f"{UNKNOWN_PREFIX}{raw}"


def _map_reason(raw: Any, table: dict[str, str], *, native: bool = False) -> Any:
    """Absent stays absent; measured values map; everything else is `unknown:<raw>`.

    `native` says the raw value is drawn from the vocabulary `TERMINAL_REASONS` IS — which
    is true of exactly one harness, the `claude` CLI whose words the enumeration was
    copied from. **Off by default, and that default is the point.** The enumeration is a
    set of English-looking strings, so a foreign harness reporting `error`, `completed` or
    `max_turns` would land in it by spelling alone and be stored as a measured terminal
    reason on a harness where nothing measured it — the bucketing this module refuses,
    landing in the field every aggregate partitions on (#31). A collision is not a
    measurement; it goes through the harness's own table or it comes out `unknown:<raw>`.

    A raw value that is not a string is `unknown:<raw>` and never reaches a membership
    test: a `stopReason` arrives out of JSON this project does not control, and a list or
    an object there raises `TypeError` on `in` — killing a trial record after the build
    that produced it was already paid for.
    """
    if raw is None:
        return None
    if not isinstance(raw, str):
        return unknown_reason(raw)
    if native and raw in TERMINAL_REASONS:
        return raw
    if raw in table:
        return table[raw]
    return unknown_reason(raw)


#: The harness whose `cost_usd` figures `tokenvalue.py` defines, and the one reader of
#: which harness a stored record came from. **Defined here, imported by every tool that
#: partitions on it.** It was spelled out in `tools/census.py` and again in
#: `tools/cost_census.py`, the two producers that decide which records are priced, with
#: nothing asserting the two agreed — a path spelled twice with a comment promising they
#: match is the shape of rule 12, and here it would surface as two totals over one tree
#: with neither reporting a disagreement.
TOKVAL_HARNESS = CLAUDE_NAME = "claude"


#: What `harness_of` returns when a record's two provenance fields DISAGREE. It is a
#: value, not an exception, and it is deliberately not the name of any harness: it can
#: never equal `TOKVAL_HARNESS`, so the record is excluded from every priced sum by the
#: same test that excludes a foreign one, and it appears in the harness partition where a
#: reader cannot miss it. An exception here would abandon a whole census over one record;
#: picking one of the two silently is the thing that must not happen.
CONFLICT_PREFIX = "conflict:"


def harness_of(record: dict[str, Any]) -> str:
    """Which harness built a stored trial record.

    Two addresses, because the record carries the name in two places: `agent.harness` from
    the normaliser, and `harness.name` from the launch. One writer sets both, so they
    disagree only in a record that was corrupted or hand-edited — and then the honest
    answer is that the provenance is unknown, never one of the two chosen by precedence.
    A record read as `claude` on the strength of a field that disagrees with the other one
    lands in the tokval sum, which is the outcome this whole partition exists to prevent.

    **Absent is read as `claude`**, and that is provenance rather than a default — every
    record stored before 2026-08-24 was built by that CLI, because there was no other.
    """
    agent = record.get("agent")
    from_agent = agent.get("harness") if isinstance(agent, dict) else None
    launched = record.get("harness")
    from_launch = launched.get("name") if isinstance(launched, dict) else None
    if from_agent and from_launch and from_agent != from_launch:
        return f"{CONFLICT_PREFIX}{from_agent}|{from_launch}"
    return from_agent or from_launch or TOKVAL_HARNESS


class Harness:
    """One agent CLI. Subclasses implement the four verbs and nothing else."""

    name = ""
    binary = ""
    model = ""
    #: Whether this CLI runs the starters' `.claude/hooks/` Stop gate. The gate is wired
    #: in every starter's `.claude/settings.json`, which only the claude CLI reads.
    supports_stop_hook = False
    turns_definition = ""

    def argv(self, *, prompt: str, turns: int, session_id: str, cwd: Path,
             allowed_tools: tuple[str, ...], budget_usd: float | None) -> list[str]:
        raise NotImplementedError

    def parse(self, stdout: str, returncode: int) -> dict[str, Any]:
        raise NotImplementedError

    def normalise(self, parsed: dict[str, Any], stderr: str) -> dict[str, Any]:
        raise NotImplementedError

    def preflight(self, cwd: Path) -> dict[str, Any]:
        """What this arm needs to be true of the machine before it launches.

        Returns the audit trail of what was checked. Raises SystemExit on a leak.
        """
        return {"harness": self.name, "checked": [], "note": "no preflight for this arm"}

    def timeout_record(self) -> dict[str, Any]:
        """What `parse` would have returned had the process not been killed by the clock."""
        return {"harness": self.name, "is_error": True, "result": "HARNESS TIMEOUT",
                "terminal_reason": "harness_timeout"}

    def final_text(self, parsed: dict[str, Any]) -> str:
        """The agent's own closing message, whole. AGENTS.md rule 11's field."""
        return parsed.get("result") or ""


# --------------------------------------------------------------------------- claude


class ClaudeHarness(Harness):
    """The `claude` CLI. Its argv is the standing configuration and is pinned byte for byte
    by `tools/agent_harness_control.py` — a changed argv is a changed experiment."""

    name = "claude"
    binary = "claude"
    model = "opus"       # builders. The judge deliberately runs a different model.
    supports_stop_hook = True
    turns_definition = "claude CLI `num_turns` — every turn of its loop"

    def argv(self, *, prompt, turns, session_id, cwd, allowed_tools, budget_usd):
        argv = [
            self.binary, "-p", prompt,
            "--output-format", "json",
            "--model", self.model,
            "--max-turns", str(turns),
            # Verified necessary: without it the operator's global CLAUDE.md leaks in.
            "--setting-sources", "project",
            "--strict-mcp-config",
            "--exclude-dynamic-system-prompt-sections",
            "--permission-mode", "acceptEdits",
            "--allowedTools", *allowed_tools,
            "--session-id", session_id,
        ]
        # Appended only when set. A budget cap is an instruction to the agent, so the
        # no-cap regime has to actually OMIT the flag rather than pass a large number.
        if budget_usd is not None:
            argv += ["--max-budget-usd", str(budget_usd)]
        return argv

    def parse(self, stdout, returncode=0):
        """`--output-format json` emits the summary as the last `type == 'result'` object.

        A malformed line is SKIPPED rather than raised on. The previous spelling built the
        fallback list with a comprehension inside an `except json.JSONDecodeError` block,
        so a truncated final line raised out of the parser, out of the build thread and
        took the rest of the matrix with it — losing trials already paid for. On
        well-formed output this returns exactly what it always did.
        """
        try:
            data = json.loads(stdout)
        except json.JSONDecodeError:
            data = []
            for line in stdout.splitlines():
                line = line.strip()
                if line.startswith("{"):
                    try:
                        data.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
        if isinstance(data, dict):
            data = [data]
        if not isinstance(data, list) or not data:
            return {}
        results = [d for d in data if isinstance(d, dict) and d.get("type") == "result"]
        return results[-1] if results else (data[-1] if data else {})

    def normalise(self, parsed, stderr):
        """Cost and tokens from `modelUsage`, which the SDK docs say to prefer over
        `usage` — `usage` is the main loop only and excludes subagents. It is already a
        RUNNING TOTAL, so it is read rather than accumulated."""
        mu = parsed.get("modelUsage") or {}
        if mu:
            metrics = {
                "cost_usd": round(sum((m or {}).get("costUSD", 0) or 0
                                      for m in mu.values()), 4),
                "input_tokens": sum((m or {}).get("inputTokens", 0) or 0
                                    for m in mu.values()),
                "output_tokens": sum((m or {}).get("outputTokens", 0) or 0
                                     for m in mu.values()),
                "cache_read": sum((m or {}).get("cacheReadInputTokens", 0) or 0
                                  for m in mu.values()),
                "cache_write": sum((m or {}).get("cacheCreationInputTokens", 0) or 0
                                   for m in mu.values()),
                "models": sorted(mu),
            }
        else:
            u = parsed.get("usage") or {}
            metrics = {"cost_usd": parsed.get("total_cost_usd") or 0,
                       "input_tokens": u.get("input_tokens", 0),
                       "output_tokens": u.get("output_tokens", 0),
                       "cache_read": u.get("cache_read_input_tokens", 0),
                       "cache_write": u.get("cache_creation_input_tokens", 0),
                       "models": []}

        # A SESSION LIMIT IS NOT AN API ERROR.
        # MEASURED, twice: the CLI reports an account session limit as
        # terminal_reason="api_error" with the real cause only in the result text
        # ("You've hit your session limit - resets 11:50pm"). They are different
        # populations - a genuine API error is a property of the run, a session limit is a
        # property of the account's day and is RETRYABLE - and merging them means a
        # partition by terminal_reason cannot tell "this trial failed" from "we ran out of
        # quota". It cost four trials in the first matrix, the whole 8-trial arena set in
        # another, and a calibration trial in between.
        raw = parsed.get("terminal_reason")
        # `native`: this CLI's vocabulary IS the shared enumeration - it is where the
        # words came from - so a value already in it is a measured reason here and only
        # here.
        reason = _map_reason(raw, {}, native=True)
        if raw == "api_error" and "session limit" in (parsed.get("result") or "").lower():
            reason = "session_limit"
        return {
            "harness": self.name,
            "is_error": bool(parsed.get("is_error")),
            "subtype": parsed.get("subtype"),
            "terminal_reason": reason,
            "terminal_reason_raw": raw,
            "num_turns": parsed.get("num_turns"),
            "turns_definition": self.turns_definition,
            "permission_denials": len(parsed.get("permission_denials") or []),
            "final_text": (parsed.get("result") or "")[-3000:],
            "stderr": stderr[-2000:],
            **metrics,
        }


# ----------------------------------------------------------------------- prime-agent


class PrimeAgentIsolationError(SystemExit):
    """Refusing to launch: a channel this arm cannot close is open."""


class PrimeAgentHarness(Harness):
    """prime-agent 0.7.1 against a ChatGPT subscription (`openai-codex`).

    Every shape here was measured on 2026-08-24, not read off `--help`; the module
    docstring records what each probe returned.
    """

    name = "prime-agent"
    binary = "prime-agent"
    model = "gpt-5.6-sol"
    provider = "openai-codex"
    #: Pinned because `~/.prime/agent/settings.json` otherwise decides it. It has no
    #: `claude` counterpart in this harness's argv, so it is a free parameter of this arm
    #: and is recorded in `eval/RUNS.md` as one.
    thinking = "high"
    supports_stop_hook = False
    turns_definition = "assistant messages in the terminal `agent_end` event"

    #: The one MEASURED mapping. Add an entry when a run stores the value, never before.
    STOP_REASONS = {"stop": "completed"}

    #: prime-agent's agent directory — the source of the global context file, of
    #: `settings.json`, and of discoverable skills/extensions/prompts/themes.
    AGENT_DIR = Path.home() / ".prime" / "agent"

    def argv(self, *, prompt, turns, session_id, cwd, allowed_tools, budget_usd):
        """The prime-agent command line.

        Four deliberate absences, each of which is an arm difference rather than an
        oversight, and all four are recorded in `eval/RUNS.md`:

        * **no turn ceiling.** `--autonomous-max-turns` exists only under `--autonomous`,
          which is a different treatment — it appends continuations and re-runs gate
          commands the claude arm never sees. The bound on this arm is the harness's
          wall-clock timeout, and `harness_timeout` is already in the enumeration.
        * **no allowlist.** `-t/--tools` filters tool NAMES; the claude arm's allowlist
          filters COMMAND PATTERNS (`Bash(just *)`). There is no way to express one in the
          other, so `allowed_tools` is deliberately unused here.
        * **no budget flag.** Nothing on this arm can be told a dollar ceiling, and on a
          subscription account no such ceiling bounds a resource anyway (#159).
        * **no `-nc`.** It would remove the starter's own `AGENTS.md`. See the module
          docstring; isolation is `preflight()`'s assertion instead.

        `session_id` is unused: `--no-session` keeps the run out of the operator's session
        store, and prime-agent mints its own id into the `session` event either way.
        """
        return [
            self.binary, "-p",
            "--mode", "json",
            "--no-session",
            "--cwd", str(cwd),
            "--provider", self.provider,
            "--model", self.model,
            "--thinking", self.thinking,
            "--", prompt,
        ]

    def parse(self, stdout, returncode=0):
        """JSONL in, one harness-shaped result out.

        The totals live in the LAST `agent_end` event. Three wrong readings this replaces,
        all of them silent: `json.loads(stdout)` raises; `json.loads(first line)` returns
        the `session` header, which has no usage in it; and summing every `usage` seen in
        the stream double-counts the `message_end` copy of each `message_start`.
        """
        events, malformed = [], 0
        for line in stdout.splitlines():
            line = line.strip()
            if not line.startswith("{"):
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                malformed += 1
        session = next((e for e in events if e.get("type") == "session"), {})
        ends = [e for e in events if e.get("type") == "agent_end"]
        end = ends[-1] if ends else None
        messages = (end or {}).get("messages") or []
        assistants = [m for m in messages
                      if isinstance(m, dict) and m.get("role") == "assistant"]
        text = []
        for chunk in (assistants[-1].get("content") if assistants else []) or []:
            if isinstance(chunk, dict) and chunk.get("type") == "text":
                text.append(chunk.get("text") or "")
        return {
            "harness": self.name,
            # `end is None` is the whole error condition: the stream stopped before the
            # agent reported. A non-zero exit alone is not one — the claude arm exits
            # non-zero on an ordinary ceiling stop and its trial is still worth grading.
            "is_error": end is None or returncode != 0,
            "exit_code": returncode,
            "agent_end_present": end is not None,
            "malformed_lines": malformed,
            "event_types": sorted({e.get("type") for e in events if e.get("type")}),
            "session_id": session.get("id"),
            "cwd": session.get("cwd"),
            # `None` when the stream ended before `agent_end`, never `[]`: a truncated
            # stream did not observe zero assistant messages, it observed nothing, and
            # `num_turns: 0` would read as a trial that did no work.
            "messages": messages if end is not None else None,
            # `result` is the same quantity the claude CLI stores under that name — the
            # agent's own closing message — so `tools/disclosure.py` reads both harnesses
            # at one address (AGENTS.md rule 11).
            "result": "".join(text),
            "stop_reason": assistants[-1].get("stopReason") if assistants else None,
        }

    def normalise(self, parsed, stderr):
        """Sum the assistant messages. THE PER-MESSAGE USAGE IS NOT CUMULATIVE.

        An absent `usage` is a `None` to report, never a `0` to sum (#36): a trial whose
        counts could not be read is unmeasurable, and a zero would average as a cheap
        trial. So the totals are `None` unless at least one assistant message carried a
        usage block, and `usage_missing_messages` records how many did not.
        """
        assistants = [m for m in (parsed.get("messages") or [])
                      if isinstance(m, dict) and m.get("role") == "assistant"]
        totals = {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0}
        vendor_usd, seen, missing = 0.0, 0, 0
        for m in assistants:
            usage = m.get("usage")
            if not isinstance(usage, dict):
                missing += 1
                continue
            seen += 1
            for key in totals:
                value = usage.get(key)
                totals[key] += value if isinstance(value, (int, float)) else 0
            cost = usage.get("cost")
            if isinstance(cost, dict) and isinstance(cost.get("total"), (int, float)):
                vendor_usd += cost["total"]
        have = seen > 0
        reason = _map_reason(parsed.get("stop_reason"), self.STOP_REASONS)
        if parsed.get("terminal_reason"):          # a timeout record, not a parsed stream
            reason = parsed["terminal_reason"]
        elif not parsed.get("agent_end_present", True):
            reason = "error"
        return {
            "harness": self.name,
            "is_error": bool(parsed.get("is_error")),
            "subtype": None,
            "terminal_reason": reason,
            "terminal_reason_raw": parsed.get("stop_reason"),
            "num_turns": len(assistants) if parsed.get("messages") is not None else None,
            "turns_definition": self.turns_definition,
            # There is no permission layer on this arm, so 0 would be a measurement of a
            # mechanism that does not exist. Absent, not zero.
            "permission_denials": None,
            "final_text": (parsed.get("result") or "")[-3000:],
            "stderr": stderr[-2000:],
            # NOT tokval and not comparable with one. Never populated for this harness.
            "cost_usd": None,
            "vendor_cost_usd_not_comparable": round(vendor_usd, 6) if have else None,
            "input_tokens": totals["input"] if have else None,
            "output_tokens": totals["output"] if have else None,
            "cache_read": totals["cacheRead"] if have else None,
            "cache_write": totals["cacheWrite"] if have else None,
            "usage_missing_messages": missing,
            "models": sorted({m.get("model") for m in assistants if m.get("model")}),
        }

    def timeout_record(self):
        rec = super().timeout_record()
        rec["agent_end_present"] = False
        # `None`, not `[]`. A killed process did not run zero turns; its turn count is
        # unknown, and `num_turns: 0` would average as a trial that did nothing.
        rec["messages"] = None
        return rec

    # ------------------------------------------------------------------ preflight

    def context_leaks(self, cwd: Path) -> list[str]:
        """Context files prime-agent would load that the claude arm would not see.

        Every STRICT ancestor of the trial tree, to `/`, plus the agent directory. The
        tree's OWN context file is the starter's guide — the product — and is not a leak.
        """
        found = []
        for name in CONTEXT_FILENAMES:
            candidate = self.AGENT_DIR / name
            if candidate.exists():
                found.append(str(candidate))
        current = Path(cwd).resolve().parent
        while True:
            for name in CONTEXT_FILENAMES:
                candidate = current / name
                if candidate.exists():
                    found.append(str(candidate))
                    break        # prime-agent takes the first match per directory
            if current == current.parent:
                break
            current = current.parent
        return found

    def resource_leaks(self) -> list[str]:
        """Discoverable skills/extensions/prompts/themes in the agent directory."""
        found = []
        for kind in RESOURCE_DIRS:
            path = self.AGENT_DIR / kind
            if path.is_dir() and any(path.iterdir()):
                found.append(str(path))
        return found

    def preflight(self, cwd: Path) -> dict[str, Any]:
        """Refuse to launch with a channel open that no artifact would record.

        This is what this arm has INSTEAD of `--setting-sources project` and
        `--strict-mcp-config`, which it has no equivalent of. It returns what it checked
        so the trial record says the check ran — a guard that leaves no trace is
        indistinguishable afterwards from one that never fired (`eval/AGENTS.md`, the
        Stop-hook log).
        """
        context = self.context_leaks(cwd)
        resources = self.resource_leaks()
        audit = {
            "harness": self.name,
            "checked": ["ancestor context files", "agent-dir context file",
                        "agent-dir resource directories"],
            "agent_dir": str(self.AGENT_DIR),
            "trial_tree": str(cwd),
            "context_files_found": context,
            "resource_dirs_found": resources,
            "settings_pinned_on_argv": {"provider": self.provider, "model": self.model,
                                        "thinking": self.thinking},
        }
        if context or resources:
            raise PrimeAgentIsolationError(
                "REFUSING TO LAUNCH the prime-agent arm: it reads context files from every "
                "ancestor of the trial tree and resources from its agent directory, and "
                f"these exist:\n  context: {context or 'none'}\n  resources: "
                f"{resources or 'none'}\nThe claude arm keeps the equivalents out with "
                "--setting-sources project and --strict-mcp-config; this harness has no "
                "flag that does it (`-nc` also removes the STARTER's AGENTS.md, which is "
                "the thing being measured). Move or remove them, or launch elsewhere.")
        return audit


CLAUDE = ClaudeHarness()
PRIME_AGENT = PrimeAgentHarness()

HARNESSES: dict[str, Harness] = {CLAUDE.name: CLAUDE, PRIME_AGENT.name: PRIME_AGENT}


def get(name: str) -> Harness:
    try:
        return HARNESSES[name]
    except KeyError:
        raise SystemExit(f"unknown harness {name!r}; known: {sorted(HARNESSES)}") from None


def env_for(harness: Harness, env: dict[str, str]) -> dict[str, str]:
    """The environment a trial runs under, per harness.

    The Stop-hook variable is only meaningful to a CLI that runs the starters'
    `.claude/hooks/`. Passing it to one that does not would leave `STARTER_HOOK_LOG` set
    for a hook that never runs, and the resulting `log: "absent"` would read as "the gate
    passed silently" rather than "this harness has no gate".
    """
    out = dict(env)
    if not harness.supports_stop_hook:
        out.pop("STARTER_HOOK_LOG", None)
    return out


def _definition() -> str:
    return __doc__ or ""


if __name__ == "__main__":
    print(_definition())
    print(f"harnesses: {sorted(HARNESSES)}")
    print(f"terminal reasons: {sorted(TERMINAL_REASONS)} (+ '{UNKNOWN_PREFIX}<raw>')")
    print(f"PATH sees prime-agent: "
          f"{any((Path(p) / 'prime-agent').exists() for p in os.environ.get('PATH', '').split(':'))}")
