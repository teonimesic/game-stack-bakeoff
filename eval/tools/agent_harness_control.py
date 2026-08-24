#!/usr/bin/env python3
"""Can `agent_harness.py` fail — and can it still pass on the inputs it must not flag?

WHY THIS EXISTS
---------------
`eval/agent_harness.py` is the file that decides what a trial record SAYS about a trial:
which command line was run, which token counts were read out of the output, and which
terminal reason the record carries. Every one of those is silent when it is wrong. The
claude arm's argv in particular must not move at all — a changed command line is a changed
experiment, and no stored artifact records the argv it was built with.

THE FOUR KINDS OF ROW
---------------------
  PRISTINE   the shipped module gives the answer this file states in advance. Not a result
             on its own; it is what makes a red mutant row attributable.

  MUTANT     the mechanism removed, one edit at a time, asserting some row goes red.
             "Can this check fail?"

  VARIANT    an input the module must still handle CORRECTLY, where the obvious wrong
             reading returns a plausible number instead of an error (rule 15). Every one
             here is a reading that was live in this project's own instructions:
             `json.loads(first line)` on a JSONL stream, summing every streamed `usage`
             including the zero-filled `message_start` copies, reading only the terminal
             event on a harness whose usage is per-message, and treating a missing count
             as a zero.

  EXPECTATION  every expected value in this file is written out as a LITERAL. It is not
             computed by calling the module, because a control that derives its
             expectation from its subject is edited by the mutant it is meant to catch
             (`tasks/113`).

WHAT IS NOT PINNED HERE
-----------------------
That the claude argv equals the argv the PRE-CHANGE code built. That was measured once,
against `git show HEAD:eval/wholegame.py` driven through the same call with the subprocess
intercepted — identical in all three configurations — and it cannot be re-run once the old
revision is no longer HEAD. The literal below is that argv.

Run it unpiped and read its own exit code:

    python3 eval/tools/agent_harness_control.py
"""

from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
EVAL = HERE.parent
SOURCE = EVAL / "agent_harness.py"

# --------------------------------------------------------------------------- fixtures

#: A `claude` result object, shaped like the ones in `runs/*/artifacts/*/agent_result.json`
#: and carrying that file's real field names. Two models, because `modelUsage` is keyed by
#: model and a reader that takes one entry silently drops the other.
CLAUDE_RESULT = {
    "type": "result", "subtype": "success", "is_error": False,
    "num_turns": 258, "terminal_reason": "completed",
    "result": "Knight's Run is built and `just verify` is green.",
    "permission_denials": [{"tool": "Bash"}, {"tool": "Bash"}],
    "total_cost_usd": 42.921086,
    "usage": {"input_tokens": 1, "output_tokens": 2},
    "modelUsage": {
        "claude-haiku-4-5-20251001": {
            "inputTokens": 2716, "outputTokens": 17, "cacheReadInputTokens": 0,
            "cacheCreationInputTokens": 0, "costUSD": 0.002801},
        "claude-opus-5": {
            "inputTokens": 488, "outputTokens": 240993,
            "cacheReadInputTokens": 65953980, "cacheCreationInputTokens": 391403,
            "costUSD": 42.918285},
    },
}

#: A prime-agent stream, from the 2026-08-24 probe. The numbers are the measured ones:
#: two assistant messages whose usage is PER MESSAGE, the second reporting a smaller
#: `input` than the first because most of its context came from cache. A cumulative
#: counter cannot go down, which is the whole reason this harness needs the opposite
#: reader from the claude one.
PRIME_ASSISTANT_1 = {
    "role": "assistant", "model": "gpt-5.6-sol", "provider": "openai-codex",
    "stopReason": "toolUse",
    "content": [{"type": "text", "text": "writing the file"},
                {"type": "toolCall", "toolName": "ipython"}],
    "usage": {"input": 4034, "output": 70, "cacheRead": 0, "cacheWrite": 0,
              "totalTokens": 4104,
              "cost": {"input": 0.02017, "output": 0.0021, "cacheRead": 0,
                       "cacheWrite": 0, "total": 0.02227}},
}
PRIME_ASSISTANT_2 = {
    "role": "assistant", "model": "gpt-5.6-sol", "provider": "openai-codex",
    "stopReason": "stop",
    "content": [{"type": "text", "text": "ZEBRA-7"}],
    "usage": {"input": 539, "output": 9, "cacheRead": 3584, "cacheWrite": 0,
              "totalTokens": 4132,
              "cost": {"input": 0.002695, "output": 0.00027, "cacheRead": 0.001792,
                       "cacheWrite": 0, "total": 0.004757}},
}
PRIME_TOOL_RESULT = {"role": "toolResult", "toolName": "ipython", "isError": False,
                     "content": [{"type": "text", "text": "b'ZEBRA-7'\n"}]}


def prime_stream(messages, *, agent_end=True, trailing_garbage=False) -> str:
    """The stream as prime-agent emits it: JSONL, session header first, totals last.

    The interleaved `message_start` events carry a ZERO-FILLED usage block, exactly as the
    real CLI does. Any reader that sums every `usage` it sees counts those, and any reader
    that takes the FIRST line gets the session header, which has no usage at all.
    """
    events = [
        {"type": "session", "version": 3, "id": "01a034ed-596c-747e", "cwd": "/w"},
        {"type": "agent_start"},
        {"type": "turn_start"},
        {"type": "message_start",
         "message": {"role": "assistant",
                     "usage": {"input": 0, "output": 0, "cacheRead": 0,
                               "cacheWrite": 0, "totalTokens": 0}}},
        {"type": "message_update"},
        {"type": "message_end", "message": messages[0] if messages else {}},
        {"type": "turn_end", "toolResults": []},
    ]
    if agent_end:
        events.append({"type": "agent_end", "messages": messages})
    lines = [json.dumps(e) for e in events]
    if trailing_garbage:
        lines.append('{"type": "agent_e')      # a stream killed mid-line
    return "\n".join(lines) + "\n"


# ------------------------------------------------------------------------------- rows


class Row:
    def __init__(self, kind: str, name: str, ok: bool, detail: str = ""):
        self.kind, self.name, self.ok, self.detail = kind, name, ok, detail

    def render(self) -> str:
        return (f"{self.kind:<9} {self.name:<34} {'ok' if self.ok else 'FAILED'}"
                f"{'  ' + self.detail if self.detail else ''}")


def _eq(kind, name, got, want) -> Row:
    return Row(kind, name, got == want, "" if got == want else f"got {got!r}, want {want!r}")


def rows(mod) -> list[Row]:
    out: list[Row] = []
    claude, prime = mod.CLAUDE, mod.PRIME_AGENT

    # ---------------------------------------------------------------- claude argv
    base = ["claude", "-p", "PROMPT TEXT",
            "--output-format", "json",
            "--model", "opus",
            "--max-turns", "1000",
            "--setting-sources", "project",
            "--strict-mcp-config",
            "--exclude-dynamic-system-prompt-sections",
            "--permission-mode", "acceptEdits",
            "--allowedTools", "Bash(just *)", "Bash(cargo *)", "Bash(pnpm *)",
            "Bash(git *)",
            "--session-id", "SID"]
    tools = ("Bash(just *)", "Bash(cargo *)", "Bash(pnpm *)", "Bash(git *)")
    got = claude.argv(prompt="PROMPT TEXT", turns=1000, session_id="SID",
                      cwd=Path("/w"), allowed_tools=tools, budget_usd=None)
    out.append(_eq("PRISTINE", "claude argv, standing config", got, base))
    got = claude.argv(prompt="PROMPT TEXT", turns=1000, session_id="SID",
                      cwd=Path("/w"), allowed_tools=tools, budget_usd=48.0)
    out.append(_eq("PRISTINE", "claude argv, a budget regime",
                   got, base + ["--max-budget-usd", "48.0"]))
    got = claude.argv(prompt="PROMPT TEXT", turns=17, session_id="SID",
                      cwd=Path("/w"), allowed_tools=tools, budget_usd=None)
    want = list(base)
    want[want.index("--max-turns") + 1] = "17"
    out.append(_eq("PRISTINE", "claude argv, turn override", got, want))

    # --------------------------------------------------------------- claude parse
    out.append(_eq("PRISTINE", "claude parse, one object",
                   claude.parse(json.dumps(CLAUDE_RESULT), 0).get("num_turns"), 258))
    stream = json.dumps([{"type": "system"}, CLAUDE_RESULT])
    out.append(_eq("PRISTINE", "claude parse, a json array",
                   claude.parse(stream, 0).get("num_turns"), 258))
    older = dict(CLAUDE_RESULT, num_turns=1)
    jsonl = "\n".join(json.dumps(x) for x in
                      ({"type": "system"}, older, CLAUDE_RESULT))
    out.append(_eq("PRISTINE", "claude parse, jsonl takes the LAST result",
                   claude.parse(jsonl, 0).get("num_turns"), 258))
    # VARIANT: a stream killed mid-line. The previous spelling built its fallback with a
    # comprehension INSIDE the `except json.JSONDecodeError` handler, so this input raised
    # out of the parser, out of the build thread, and took the rest of the matrix with it.
    out.append(_eq("VARIANT", "claude parse, truncated last line",
                   claude.parse(jsonl + '\n{"type": "res', 0).get("num_turns"), 258))
    out.append(_eq("VARIANT", "claude parse, empty stdout", claude.parse("", 0), {}))

    # ----------------------------------------------------------- claude normalise
    want = {
        "harness": "claude", "is_error": False, "subtype": "success",
        "terminal_reason": "completed", "terminal_reason_raw": "completed",
        "num_turns": 258,
        "turns_definition": "claude CLI `num_turns` — every turn of its loop",
        "permission_denials": 2,
        "final_text": "Knight's Run is built and `just verify` is green.",
        "stderr": "some stderr",
        "cost_usd": 42.9211, "input_tokens": 3204, "output_tokens": 241010,
        "cache_read": 65953980, "cache_write": 391403,
        "models": ["claude-haiku-4-5-20251001", "claude-opus-5"],
    }
    out.append(_eq("PRISTINE", "claude normalise, modelUsage",
                   claude.normalise(CLAUDE_RESULT, "some stderr"), want))
    # A SESSION LIMIT IS NOT AN API ERROR: the CLI reports one as `api_error` with the
    # cause only in the result text, and the two are different populations.
    limited = dict(CLAUDE_RESULT, terminal_reason="api_error",
                   result="You've hit your session limit · resets 11:50pm")
    got = claude.normalise(limited, "")
    out.append(_eq("PRISTINE", "claude normalise, session limit",
                   (got["terminal_reason"], got["terminal_reason_raw"]),
                   ("session_limit", "api_error")))
    out.append(_eq("PRISTINE", "claude normalise, unrecognised reason",
                   claude.normalise(dict(CLAUDE_RESULT, terminal_reason="weird"),
                                    "")["terminal_reason"], "unknown:weird"))
    # VARIANT: absent is not unknown. Killed trials store `terminal_reason: null` and
    # `eval/RUNS.md` documents those records; turning them into `unknown:None` would
    # invent a population.
    out.append(_eq("VARIANT", "claude normalise, absent reason stays absent",
                   claude.normalise(dict(CLAUDE_RESULT, terminal_reason=None),
                                    "")["terminal_reason"], None))
    # VARIANT: no modelUsage at all - the pre-2026 fallback path.
    got = claude.normalise({"total_cost_usd": 1.5, "usage": {"input_tokens": 10,
                                                            "output_tokens": 20}}, "")
    out.append(_eq("VARIANT", "claude normalise, usage fallback",
                   (got["cost_usd"], got["input_tokens"], got["output_tokens"],
                    got["models"]), (1.5, 10, 20, [])))

    # ----------------------------------------------------------------- prime argv
    want = ["prime-agent", "-p", "--mode", "json", "--no-session",
            "--cwd", "/w/trial", "--provider", "openai-codex",
            "--model", "gpt-5.6-sol", "--thinking", "high", "--", "PROMPT TEXT"]
    out.append(_eq("PRISTINE", "prime argv",
                   prime.argv(prompt="PROMPT TEXT", turns=1000, session_id="SID",
                              cwd=Path("/w/trial"), allowed_tools=tools,
                              budget_usd=48.0), want))
    # VARIANT: a budget figure must NOT reach this argv. Nothing on this arm can be told
    # a dollar ceiling, and passing one would make the record claim a bound it never had.
    # ASSERTED ON WHAT THE HARNESS RETURNED, not on `want`: the first version of this row
    # tested `want`, a literal four lines above with no budget flag in it by
    # construction, so no edit to the module could redden it (rule 1, and CodeRabbit
    # found it on pull request 21). `budget_usd=48.0` is passed in on purpose.
    got = prime.argv(prompt="PROMPT TEXT", turns=1000, session_id="SID",
                     cwd=Path("/w/trial"), allowed_tools=tools, budget_usd=48.0)
    leaked = [x for x in got if "budget" in x or x == "48.0"]
    out.append(Row("VARIANT", "prime argv carries no budget", not leaked,
                   "" if not leaked else f"leaked {leaked!r}"))

    # ---------------------------------------------------- prime parse + normalise
    stdout = prime_stream([{"role": "user"}, PRIME_ASSISTANT_1, PRIME_TOOL_RESULT,
                           PRIME_ASSISTANT_2])
    parsed = prime.parse(stdout, 0)
    out.append(_eq("PRISTINE", "prime parse, closing message",
                   parsed["result"], "ZEBRA-7"))
    out.append(_eq("PRISTINE", "prime parse, session id",
                   parsed["session_id"], "01a034ed-596c-747e"))
    got = prime.normalise(parsed, "err")
    # THE MEASUREMENT THIS FILE EXISTS FOR. 4034+539, 70+9, 0+3584 - the SUM over
    # assistant messages. Reading only the terminal event gives 539/9/3584 and reading the
    # first gives 4034/70/0; both are plausible numbers and both are wrong.
    out.append(_eq("PRISTINE", "prime normalise, tokens are SUMMED",
                   (got["input_tokens"], got["output_tokens"], got["cache_read"],
                    got["cache_write"]), (4573, 79, 3584, 0)))
    out.append(_eq("PRISTINE", "prime normalise, turns",
                   (got["num_turns"], got["turns_definition"]),
                   (2, "assistant messages in the terminal `agent_end` event")))
    out.append(_eq("PRISTINE", "prime normalise, terminal reason",
                   (got["terminal_reason"], got["terminal_reason_raw"]),
                   ("completed", "stop")))
    # NO CROSS-HARNESS DOLLARS. `cost_usd` is tokval and this harness has none; its
    # vendor's list price is stored under a name that says so at every read site.
    out.append(_eq("PRISTINE", "prime normalise, cost_usd is None",
                   got["cost_usd"], None))
    out.append(_eq("PRISTINE", "prime normalise, vendor USD kept aside",
                   got["vendor_cost_usd_not_comparable"], 0.027027))
    out.append(_eq("PRISTINE", "prime normalise, no permission layer",
                   got["permission_denials"], None))
    out.append(_eq("PRISTINE", "prime normalise, models", got["models"], ["gpt-5.6-sol"]))

    # VARIANT: the zero-filled `message_start` usage is in the stream above. If it were
    # being summed, input would be 4573 either way - so this row uses a stream with three
    # extra zero-usage streaming events and asserts the total did not move.
    noisy = stdout.replace(
        '{"type": "message_update"}',
        '{"type": "message_update"}\n' + "\n".join(
            [json.dumps({"type": "message_start", "message": {
                "role": "assistant", "usage": {"input": 0, "output": 0, "cacheRead": 0,
                                               "cacheWrite": 0, "totalTokens": 0}}})] * 3))
    out.append(_eq("VARIANT", "prime, streaming events add nothing",
                   prime.normalise(prime.parse(noisy, 0), "")["input_tokens"], 4573))
    # VARIANT: an assistant message with no usage block. `None` to report, never `0` to
    # sum (#36) - a zero would average as a cheap trial.
    no_usage = {k: v for k, v in PRIME_ASSISTANT_2.items() if k != "usage"}
    got = prime.normalise(prime.parse(prime_stream([PRIME_ASSISTANT_1, no_usage]), 0), "")
    out.append(_eq("VARIANT", "prime, one message missing usage",
                   (got["input_tokens"], got["usage_missing_messages"]), (4034, 1)))
    got = prime.normalise(prime.parse(prime_stream([no_usage]), 0), "")
    out.append(_eq("VARIANT", "prime, NO usage anywhere is None not 0",
                   (got["input_tokens"], got["output_tokens"], got["cache_read"]),
                   (None, None, None)))
    # VARIANT: an unmapped stopReason. Only `stop` has been measured; anything else must
    # surface rather than land in the nearest bucket (#31).
    got = prime.normalise(prime.parse(prime_stream(
        [dict(PRIME_ASSISTANT_2, stopReason="length")]), 0), "")
    out.append(_eq("VARIANT", "prime, unmapped stopReason",
                   got["terminal_reason"], "unknown:length"))
    # VARIANT, and the nastiest one here: a foreign stopReason that COLLIDES with the
    # shared enumeration by spelling. `TERMINAL_REASONS` is a set of ordinary English
    # words, so `error` and `completed` would pass a membership test and be stored as
    # MEASURED reasons on a harness where nothing measured them - in the field every
    # aggregate partitions on. A collision is not a measurement.
    for raw in ("error", "completed", "max_turns"):
        got = prime.normalise(prime.parse(prime_stream(
            [dict(PRIME_ASSISTANT_2, stopReason=raw)]), 0), "")
        out.append(_eq("VARIANT", f"prime, `{raw}` is a collision not a measurement",
                       got["terminal_reason"], f"unknown:{raw}"))
    # VARIANT: the stream stopped before `agent_end`. Not zero turns - unknown turns.
    got = prime.parse(prime_stream([PRIME_ASSISTANT_1], agent_end=False,
                                   trailing_garbage=True), 1)
    norm = prime.normalise(got, "")
    out.append(_eq("VARIANT", "prime, truncated stream",
                   (got["agent_end_present"], got["malformed_lines"],
                    norm["num_turns"], norm["terminal_reason"], norm["input_tokens"]),
                   (False, 1, None, "error", None)))
    # VARIANT: the first line is the session header, which carries no usage. A
    # `json.loads(stdout.splitlines()[0])` reader returns it and reports nothing, at
    # exit 0.
    out.append(_eq("VARIANT", "prime, first line is not the result",
                   json.loads(stdout.splitlines()[0]).get("type"), "session"))

    # ------------------------------------------------------------ timeout records
    got = claude.normalise(claude.timeout_record(), "")
    out.append(_eq("PRISTINE", "claude timeout record",
                   (got["terminal_reason"], got["num_turns"]),
                   ("harness_timeout", None)))
    got = prime.normalise(prime.timeout_record(), "")
    out.append(_eq("PRISTINE", "prime timeout record",
                   (got["terminal_reason"], got["num_turns"], got["input_tokens"]),
                   ("harness_timeout", None, None)))

    # ----------------------------------------------------------------- preflight
    out.extend(preflight_rows(mod))

    # --------------------------------------------------- who built a stored record
    # ONE definition, imported by `tools/census.py` and `tools/cost_census.py` - the two
    # producers that decide which records may be summed. It was spelled out in both until
    # pull request 21, with nothing asserting they agreed; two readings of one tree with
    # neither reporting a disagreement is rule 12 with a dollar figure attached.
    out.append(_eq("PRISTINE", "harness_of reads agent.harness",
                   mod.harness_of({"agent": {"harness": "prime-agent"}}), "prime-agent"))
    out.append(_eq("PRISTINE", "harness_of reads the launch record",
                   mod.harness_of({"harness": {"name": "prime-agent"}}), "prime-agent"))
    # PROVENANCE, not a default: every record stored before 2026-08-24 was built by the
    # claude CLI because there was no other one.
    out.append(_eq("VARIANT", "harness_of: an unstamped record is claude",
                   mod.harness_of({"agent": {"cost_usd": 1.0}}), "claude"))
    out.append(_eq("VARIANT", "harness_of survives a malformed record",
                   (mod.harness_of({}), mod.harness_of({"agent": None}),
                    mod.harness_of({"harness": "a string, not an object"})),
                   ("claude", "claude", "claude")))
    out.append(_eq("PRISTINE", "TOKVAL_HARNESS", mod.TOKVAL_HARNESS, "claude"))

    # ------------------------------------------------------------------- env_for
    env = {"STARTER_HOOK_LOG": "/somewhere/hook_log.tsv", "PATH": "/usr/bin"}
    out.append(_eq("PRISTINE", "env_for claude keeps the hook log",
                   mod.env_for(claude, env).get("STARTER_HOOK_LOG"),
                   "/somewhere/hook_log.tsv"))
    # The Stop gate is wired in `.claude/settings.json`, which only the claude CLI reads.
    # Leaving the variable set for a harness with no hooks would produce a `log: absent`
    # that reads as "the gate passed silently".
    out.append(_eq("PRISTINE", "env_for prime drops the hook log",
                   mod.env_for(prime, env).get("STARTER_HOOK_LOG"), None))
    return out


def preflight_rows(mod) -> list[Row]:
    """The isolation this arm has INSTEAD of `--setting-sources project`.

    Measured 2026-08-24: prime-agent reads a context file from every ancestor of its cwd
    to `/`, and from its agent directory. Its one flag that stops this, `-nc`, also
    removes the STARTER's own `AGENTS.md` — the product — so the guard is an assertion
    over the tree instead.
    """
    out: list[Row] = []
    with tempfile.TemporaryDirectory(prefix="harness-preflight-") as tmp:
        root = Path(tmp)
        agent_dir = root / "agent-dir"
        agent_dir.mkdir()
        outer = root / "work-root"
        tree = outer / "run" / "g1_pong__rust__t0"
        tree.mkdir(parents=True)
        # The starter's own guide. This is the product; it must NOT be read as a leak.
        (tree / "AGENTS.md").write_text("the starter's guide\n")

        prime = mod.PrimeAgentHarness()
        prime.AGENT_DIR = agent_dir

        audit = None
        try:
            audit = prime.preflight(tree)
            clean = True
        except SystemExit as exc:
            clean, audit = False, str(exc)
        out.append(Row("VARIANT", "preflight: the starter's own AGENTS.md is not a leak",
                       clean, "" if clean else f"refused: {audit}"))
        if clean:
            out.append(_eq("PRISTINE", "preflight audit records what it checked",
                           (audit["context_files_found"], audit["resource_dirs_found"],
                            audit["settings_pinned_on_argv"]["model"]),
                           ([], [], "gpt-5.6-sol")))

        # An ancestor context file. MEASURED to leak: an `AGENTS.md` one directory above
        # cwd came back through the model verbatim.
        (outer / "AGENTS.md").write_text("the operator's own instructions\n")
        try:
            prime.preflight(tree)
            caught = False
            detail = "preflight returned instead of refusing"
        except SystemExit as exc:
            caught = "AGENTS.md" in str(exc)
            detail = "" if caught else f"refused for the wrong reason: {exc}"
        out.append(Row("PRISTINE", "preflight refuses an ancestor context file",
                       caught, detail))
        (outer / "AGENTS.md").unlink()

        # A discoverable skill in the agent directory: it would enter every trial and
        # appear in no artifact. An EMPTY directory is not a finding.
        skills = agent_dir / "skills"
        skills.mkdir()
        try:
            prime.preflight(tree)
            empty_ok = True
        except SystemExit as exc:
            empty_ok, _ = False, exc
        out.append(Row("VARIANT", "preflight: an empty resource dir is not a leak",
                       empty_ok))
        (skills / "some-skill").mkdir()
        try:
            prime.preflight(tree)
            caught, detail = False, "preflight returned instead of refusing"
        except SystemExit as exc:
            caught = "skills" in str(exc)
            detail = "" if caught else f"refused for the wrong reason: {exc}"
        out.append(Row("PRISTINE", "preflight refuses a discoverable skill", caught))
    return out


# ---------------------------------------------------------------------------- mutants

#: Each removes ONE mechanism. A mutant that survives every row is a mechanism nothing
#: checks, which is the state this whole file exists to keep the module out of.
MUTANTS: list[tuple[str, str, str]] = [
    ("claude argv drops --setting-sources",
     '            "--setting-sources", "project",\n', ""),
    ("claude argv drops the allowlist",
     '            "--allowedTools", *allowed_tools,\n', ""),
    ("claude parse takes the FIRST result",
     "return results[-1] if results else (data[-1] if data else {})",
     "return results[0] if results else (data[0] if data else {})"),
    ("claude normalise loses the session-limit split",
     'if raw == "api_error" and "session limit" in (parsed.get("result") or "").lower():',
     "if False:"),
    ("unrecognised reasons are bucketed as completed",
     "    return unknown_reason(raw)", '    return "completed"'),
    ("the enumeration shortcut applies to every harness",
     "    if native and raw in TERMINAL_REASONS:", "    if raw in TERMINAL_REASONS:"),
    ("harness_of defaults an unstamped record to the other harness",
     "    return TOKVAL_HARNESS\n", '    return "prime-agent"\n'),
    ("harness_of stops reading the launch record",
     "    launched = record.get(\"harness\")", "    launched = None"),
    ("prime reads only the terminal message",
     "        for m in assistants:", "        for m in assistants[-1:]:"),
    ("prime treats a missing usage block as zero",
     "        have = seen > 0", "        have = True"),
    ("prime publishes its vendor's price as tokval",
     '            "cost_usd": None,', '            "cost_usd": round(vendor_usd, 6),'),
    ("prime parse takes the first event as the result",
     "        end = ends[-1] if ends else None", "        end = events[0] if events else None"),
    # The pin for the budget row above, which was vacuous until pull request 21: it now
    # reads the argv the harness returned, so a budget flag leaking into it reddens.
    ("prime argv gains a budget flag",
     '            "--", prompt,',
     '            "--max-budget-usd", str(budget_usd), "--", prompt,'),
    ("preflight never refuses", "        if context or resources:", "        if False:"),
    ("preflight ignores ancestors",
     "        current = Path(cwd).resolve().parent",
     "        current = Path('/nonexistent-ancestor-root')"),
    ("env_for leaves the hook log set for a hookless harness",
     '        out.pop("STARTER_HOOK_LOG", None)', "        pass"),
]


def load_module(source: str, name: str):
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False,
                                     prefix=f"{name}_") as fh:
        fh.write(source)
        path = fh.name
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    try:
        spec.loader.exec_module(mod)
        return mod, path
    except Exception:
        os.unlink(path)
        raise


def main(argv: list[str] | None = None) -> int:
    source = SOURCE.read_text()
    failures = 0
    print(f"subject: {SOURCE}")
    for row in rows(load_module(source, "_ah_pristine")[0]):
        print("  " + row.render())
        if not row.ok:
            failures += 1
    print()
    for label, find, replace in MUTANTS:
        if source.count(find) != 1:
            print(f"  MUTANT    {label:<52} UNPLANTABLE  "
                  f"({source.count(find)} matches for its anchor - the source moved)")
            failures += 1
            continue
        mod, path = load_module(source.replace(find, replace), "_ah_mutant")
        try:
            red = [r.name for r in rows(mod) if not r.ok]
        except Exception as exc:            # noqa: BLE001 - a crash is a caught mutant
            red = [f"raised {type(exc).__name__}"]
        finally:
            os.unlink(path)
        # Up to TWO names, because a mutant is often caught by a row that is not the one
        # it was written for, and printing only the first hides whether the intended row
        # fired at all.
        print(f"  MUTANT    {label:<52} "
              f"{'caught by ' + '; '.join(red[:2]) if red else 'SURVIVED - nothing checks this'}")
        if not red:
            failures += 1
    print()
    if failures:
        print(f"{failures} FAILED")
    else:
        print("all rows ok; every mutant caught")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
