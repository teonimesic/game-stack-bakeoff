#!/usr/bin/env python3
"""Tier 3: the LLM judge.

Scope is deliberately narrow. The judge is asked ONLY what a script cannot answer -
code quality, and whether the result reads as a coherent game from a frame sequence.
Everything mechanical was already settled in `static.py`, and everything behavioural in
the play-bots. Four independent studies put VLM game-test oracles near chance on
temporal properties, so nothing temporal is asked here.

Constraints, each traceable to research/05-eval-harness-design.md:

  * A DIFFERENT MODEL from the one being evaluated. Builders run on `opus`; the judge
    defaults to `sonnet`. Anthropic's eval guidance states this outright. Caveat worth
    stating plainly: same vendor, same family - a genuinely independent judge would be
    a different lab's model, and this harness cannot provide one. Self-enhancement bias
    is reduced, not eliminated.
  * BINARY criteria. Calibratable against human labels; 1-5 scales are not.
  * GRADED INDEPENDENTLY, one submission per session. That removes position bias
    outright rather than averaging it away.
  * BOTH CRITERIA ORDERS. Each submission is judged twice, criteria forward then
    reversed; a criterion passes only if both agree. The disagreement rate is reported
    as `instability` - a direct measurement of how much this tier can be trusted.
  * EVIDENCE BEFORE THE VERDICT. The schema puts `evidence` and `reason` ahead of
    `passed`, and an empty evidence field forces the criterion to FALSE.
  * BLIND. The judge's working directory is a neutralised pack (see anonymise.py) and
    nothing tells it which stack it is looking at.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import tempfile
import time
import uuid
from pathlib import Path
from typing import Any

from anonymise import build_pack

DEFAULT_MODEL = "sonnet"      # builders are on `opus`

CODE_CRITERIA: list[tuple[str, str]] = [
    ("code.separation",
     "Is the game's logic kept out of the rendering layer, so the rules could run "
     "without a screen?"),
    ("code.placeholder_gone",
     "Has the starter's placeholder entity - a single marker that drifts and bounces, "
     "with `nudge` controls - been removed, rather than left sitting alongside the "
     "real game?"),
    ("code.naming",
     "Do the names describe the game's own concepts, rather than being generic "
     "(`a`, `tmp`, `data`, `handle`, `manager`, `doStuff`)?"),
    ("code.function_size",
     "Are the functions small enough to read in one sitting, with no single function "
     "carrying most of the game?"),
    ("code.magic_numbers",
     "Are tuning values named constants gathered in one place, rather than bare "
     "numeric literals scattered through the logic?"),
    ("code.comments",
     "Where comments exist, do they explain WHY, rather than restating what the next "
     "line already says?"),
    ("code.tests_meaningful",
     "Do the tests assert on behaviour that could actually break, rather than being "
     "smoke tests, tautologies, or assertions that cannot fail?"),
    ("code.duplication",
     "Ignoring test files, and ignoring any repeated idiom the code's own comments "
     "state is required for correctness or determinism: is the codebase free of any "
     "block of five or more consecutive lines of game logic that appears "
     "near-identically in three or more places?"),
    ("code.robustness",
     "Are there no obvious crash paths - unchecked indexing, unwrapping an empty "
     "option, dividing by something that can be zero - on code reachable during "
     "normal play?"),
    ("code.navigable",
     "Judging ONLY what is inside the files - their names have been replaced with "
     "neutral ones and carry no information, so do not reason about the file layout - "
     "is the game's logic broken into named units (modules, impl blocks, or clearly "
     "titled comment sections) whose names identify which rule they implement, rather "
     "than one long undifferentiated run of functions?"),
]

LOOK_CRITERIA: list[tuple[str, str]] = [
    ("look.legible",
     "From the frames alone, and without being told, is it apparent what kind of game "
     "this is?"),
    ("look.consistent",
     "Do the frames read as one deliberate scene, rather than debug shapes at "
     "mismatched scales and colours?"),
    ("look.feedback",
     "Looking ONLY at the frames: does at least one on-screen element visibly change "
     "between frames in a way that reports the game's progress to the player - a score "
     "readout, a counter, a life or wave indicator, or a state banner? The moving game "
     "objects changing position does NOT count on its own."),
]

ALL_CRITERIA = CODE_CRITERIA + LOOK_CRITERIA

# Stack-neutral one-paragraph summaries. The judge must know what the game was supposed
# to be - otherwise `look.legible` is unanswerable - but must not see stack vocabulary.
GAME_BRIEF = {
    "g1_pong": (
        "Pong. Two paddles, one ball, a rectangular arena. Paddles move along the "
        "arena's short axis; the ball reflects off the top and bottom walls and off "
        "the paddles, with the contact point changing the angle. The ball speeds up "
        "during a rally, up to a ceiling. A point is scored when the ball passes "
        "behind a paddle; first to eleven wins."
    ),
    "g2_tetris3d": (
        "3D Tetris. Four-cell pieces fall down a 5 x 5 x 12 shaft. The player slides "
        "them along either horizontal axis, rotates them a quarter turn about any of "
        "the three axes, and drops them. A piece locks when it can fall no further. "
        "When every one of the 25 cells in a horizontal layer is filled, that layer is "
        "removed and everything above falls down. Scoring rewards clears, more so for "
        "several at once. The game ends when a new piece has nowhere to go."
    ),
    "g3_arena": (
        "A twin-stick arena shooter. One player in a closed rectangular arena. The "
        "player moves in eight directions and aims in eight directions chosen "
        "separately from the movement direction, firing while the fire control is "
        "held. Bullets travel straight and vanish on leaving the arena or hitting an "
        "enemy. Enemies spawn at the arena edge in waves and move toward the player; "
        "touching the player costs health. Clearing a wave starts a larger one. The "
        "player starts with three health and the game ends at zero."
    ),
}

SCHEMA = {
    "type": "object",
    "properties": {
        "criteria": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "evidence": {
                        "type": "string",
                        "description": "A concrete quotation from a file, or a file "
                                       "path plus what is in it, or a description of "
                                       "a specific frame. Not a restatement of the "
                                       "criterion.",
                    },
                    "reason": {
                        "type": "string",
                        "description": "One sentence connecting that evidence to the "
                                       "verdict.",
                    },
                    "passed": {"type": "boolean"},
                },
                "required": ["id", "evidence", "reason", "passed"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["criteria"],
    "additionalProperties": False,
}


def _brief(game: str, criteria: list[tuple[str, str]], n_files: int,
           n_frames: int) -> str:
    lines = [
        "# Review brief",
        "",
        "You are reviewing one submission: somebody was asked to build the game "
        "described below, starting from a project skeleton that already provided a "
        "test harness, a verification command and a placeholder entity.",
        "",
        "## The game they were asked to build",
        "",
        # Direct index, not `.get(..., default)`: the placeholder brief is the defect
        # this module was carrying (tasks/221). judge() refuses an unbriefed game above,
        # so a missing key here can only mean judge() was bypassed - and a KeyError is
        # the right answer to that, not a brief nobody wrote.
        GAME_BRIEF[game],
        "",
        "## What you have",
        "",
        f"- `code/` - {n_files} source files they wrote or changed. Files they did not "
        "touch have been removed, and the paths have been renamed to neutral ones, so "
        "what you see is their work rather than the skeleton's.",
    ]
    if n_frames:
        lines.append(f"- `frames/` - {n_frames} PNG frames captured in order from a "
                     "single recorded play session. Read them as images.")
    lines += [
        "",
        "## How to review",
        "",
        "Answer each question below with yes or no. For each one, first write down the "
        "specific evidence - a quotation, a file path and what is in it, or which frame "
        "shows what - and a one-sentence reason, and only then the verdict. If you "
        "cannot point at specific evidence, the answer is no.",
        "",
        "Do not score, rank, or grade. Do not guess at what language, engine or "
        "framework this is, and do not let that guess influence any answer. Judge only "
        "what is in front of you.",
        "",
        "## Questions",
        "",
    ]
    for i, (cid, q) in enumerate(criteria, 1):
        lines.append(f"{i}. `{cid}` - {q}")
    lines += [
        "",
        "Return one entry per question, using the exact `id` strings above.",
    ]
    return "\n".join(lines)


PROMPT = (
    "Read BRIEF.md in this directory, then review the submission it describes. "
    "Read every file under code/. If frames/ exists, read the PNG images in it in "
    "order. Then answer every question in the brief, following the brief's rules "
    "about evidence. Return the structured result."
)


def _run_claude(pack: Path, model: str, max_turns: int, budget: float,
                timeout_s: int, attempts: int = 3) -> tuple[dict[str, Any], str]:
    """Invoke the judge, retrying a transient failure.

    A judging pass that produces no parseable criteria is retried rather than
    silently scored as thirteen failures. `is_error`, a timeout, or an unparseable
    result all count as transient; a clean run with a full criteria array does not.
    """
    last: tuple[dict[str, Any], str] = ({}, "")
    for attempt in range(1, attempts + 1):
        raw, stderr = _run_claude_once(pack, model, max_turns, budget, timeout_s)
        if not raw.get("is_error") and _extract(raw):
            raw["judge_attempts"] = attempt
            return raw, stderr
        last = (raw, stderr)
        time.sleep(min(30, 5 * attempt))
    last[0]["judge_attempts"] = attempts
    last[0]["judge_retries_exhausted"] = True
    return last


def _run_claude_once(pack: Path, model: str, max_turns: int, budget: float,
                     timeout_s: int) -> tuple[dict[str, Any], str]:
    argv = [
        "claude", "-p", PROMPT,
        "--model", model,
        "--output-format", "json",
        "--json-schema", json.dumps(SCHEMA, separators=(",", ":")),
        "--max-turns", str(max_turns),
        "--max-budget-usd", str(budget),
        # The same isolation the builder runs use: no operator CLAUDE.md, no operator
        # MCP servers, no machine-specific system prompt sections.
        "--setting-sources", "project",
        "--strict-mcp-config",
        "--exclude-dynamic-system-prompt-sections",
        "--no-session-persistence",
        "--permission-mode", "acceptEdits",
    ]
    try:
        # check=False: the CLI exits non-zero for reasons that still produce a usable
        # verdict (a budget or turn ceiling reached after the answer was written), so
        # raising on the status would discard rounds that are fine. It is recorded on
        # the unparseable path, where it is the only thing separating "the judge said
        # something we could not read" from "the judge never ran".
        p = subprocess.run(argv, cwd=pack, capture_output=True, text=True,
                           timeout=timeout_s, check=False)
    except subprocess.TimeoutExpired:
        return {"is_error": True, "result": "judge timed out"}, "timeout"
    except OSError as e:
        return {"is_error": True, "result": f"could not run claude: {e}"}, str(e)
    try:
        data = json.loads(p.stdout)
    except json.JSONDecodeError:
        data = {"is_error": True, "cli_exit": p.returncode,
                "result": p.stdout[-3000:]}
    if isinstance(data, list):
        results = [d for d in data if isinstance(d, dict) and d.get("type") == "result"]
        data = results[-1] if results else (data[-1] if data else {})
    return data, p.stderr[-2000:]


def _extract(result: dict[str, Any]) -> list[dict[str, Any]]:
    """Pull the criteria array out of whatever shape the CLI handed back."""
    for key in ("structured_output", "structuredOutput", "output"):
        v = result.get(key)
        if isinstance(v, dict) and isinstance(v.get("criteria"), list):
            return v["criteria"]
    text = result.get("result")
    if isinstance(text, dict) and isinstance(text.get("criteria"), list):
        return text["criteria"]
    if isinstance(text, str):
        for candidate in (text, text[text.find("{"): text.rfind("}") + 1]):
            try:
                v = json.loads(candidate)
            except (json.JSONDecodeError, ValueError):
                continue
            if isinstance(v, dict) and isinstance(v.get("criteria"), list):
                return v["criteria"]
    return []


def _pass_one(pack: Path, game: str, criteria: list[tuple[str, str]], model: str,
              n_files: int, n_frames: int, max_turns: int, budget: float,
              timeout_s: int) -> dict[str, Any]:
    (pack / "BRIEF.md").write_text(_brief(game, criteria, n_files, n_frames))
    raw, stderr = _run_claude(pack, model, max_turns, budget, timeout_s)
    items = _extract(raw)
    by_id = {str(it.get("id")): it for it in items if isinstance(it, dict)}
    verdicts: dict[str, dict[str, Any]] = {}
    for cid, _q in criteria:
        it = by_id.get(cid)
        if not it:
            verdicts[cid] = {"passed": False, "evidence": "",
                             "reason": "the judge returned no entry for this criterion"}
            continue
        evidence = str(it.get("evidence") or "").strip()
        # Evidence before verdict is a hard requirement, not a formatting preference.
        passed = bool(it.get("passed")) and len(evidence) >= 20
        verdicts[cid] = {
            "passed": passed,
            "evidence": evidence[:800],
            "reason": str(it.get("reason") or "")[:400],
            "dropped_for_missing_evidence": bool(it.get("passed")) and not passed,
        }
    usage = raw.get("modelUsage") or {}
    return {
        "verdicts": verdicts,
        "returned": len(items),
        "model": model,
        "models_used": sorted(usage.keys()),
        "cost_usd": round(sum((m or {}).get("costUSD", 0) or 0
                              for m in usage.values()), 4),
        "num_turns": raw.get("num_turns"),
        "terminal_reason": raw.get("terminal_reason"),
        "is_error": bool(raw.get("is_error")),
        "stderr": stderr[-600:],
    }


def judge(submission: Path, starter: Path, game: str, frames_dir: Path | None = None,
          model: str = DEFAULT_MODEL, submission_id: str | None = None,
          keep_pack: Path | None = None, max_turns: int = 60,
          budget: float = 2.0, timeout_s: int = 1800) -> dict[str, Any]:
    sid = submission_id or uuid.uuid4().hex[:12]

    # HARD GUARD, GAME AXIS. The 2026-08-25 instruments decision (DECISIONS.md) guarded
    # the CLASS axis - `aspects.INSTRUMENTS` declares `legacy_judge: game`, and
    # `evaluate.assert_legacy_judge_allowed` refuses a scene before tier 1 - but the
    # GAME axis stood open: GAME_BRIEF holds 3 entries and the suite has 4 games, so
    # `--with-legacy-judge` on g4_platformer passed the class guard into a placeholder
    # brief and would have answered all 13 criteria about a game nobody described. Only
    # this function could close it: it owns GAME_BRIEF (rule 13), and its own CLI
    # already refuses the same set by argparse choices. `evaluate.py --game
    # g4_platformer --with-legacy-judge` is the path that was exposed.
    #
    # A RECORD, not an exception. evaluate() writes judge.json and its completeness
    # gate refuses a trial whose tier files are missing, so a raise here would convert
    # a tier-3 subject problem into a failed grading of tiers 1 and 2, which are valid
    # whatever the tier-3 answer. `refused: true` is what makes this verdict distinct
    # from the empty-pack refusal below and from evaluate()'s skipped marker; the
    # census that partitions them is judge_refusal_selftest.py.
    if game not in GAME_BRIEF:
        return {
            "tier": "judge", "refused": True,
            "error": f"no GAME_BRIEF entry for {game!r} - the retired judge's 13 "
                     f"criteria are written about the briefed games only "
                     f"({sorted(GAME_BRIEF)}), so it is refused rather than answered "
                     "against a placeholder brief. Do not extend GAME_BRIEF to admit "
                     "it: the table is what every stored round was read against.",
            "game": game, "model": model, "submission_id": sid,
            "usable": False, "passed": 0, "total": len(ALL_CRITERIA), "score": 0.0,
            "instability": None, "criteria": [], "pack": None, "cost_usd": 0.0,
        }

    pack = Path(tempfile.mkdtemp(prefix=f"pack-{sid}-"))
    manifest = build_pack(submission, starter, pack, frames_dir, sid)

    forward = ALL_CRITERIA
    reverse = list(reversed(ALL_CRITERIA))
    n_files = int(manifest["files_in_pack"])          # type: ignore[arg-type]
    n_frames = int(manifest["frames"])                # type: ignore[arg-type]

    # HARD GUARD. An empty pack makes the judge answer "no" to every code question for
    # the correct reason - there is nothing to point at - and that is indistinguishable
    # from a submission whose code is terrible. It happened: `.py` was missing from the
    # extension allowlist, three fixtures shipped zero files, and the tier reported a
    # confident 0.08 that measured nothing. Refuse to score instead of scoring zero.
    if n_files == 0:
        shutil.rmtree(pack, ignore_errors=True)
        return {
            "tier": "judge", "game": game, "model": model, "submission_id": sid,
            "error": "the judging pack contains no source files - check "
                     "anonymise.CODE_EXT and the starter used for de-duplication",
            "usable": False, "passed": 0, "total": len(ALL_CRITERIA), "score": 0.0,
            "instability": None, "criteria": [], "pack": manifest, "cost_usd": 0.0,
        }

    a = _pass_one(pack, game, forward, model, n_files, n_frames, max_turns, budget,
                  timeout_s)
    b = _pass_one(pack, game, reverse, model, n_files, n_frames, max_turns, budget,
                  timeout_s)

    criteria_out: list[dict[str, Any]] = []
    disagreements = 0
    for cid, q in ALL_CRITERIA:
        va, vb = a["verdicts"][cid], b["verdicts"][cid]
        agree = va["passed"] == vb["passed"]
        if not agree:
            disagreements += 1
        criteria_out.append({
            "id": cid,
            "question": q,
            # Both orders must agree it passes. A criterion the judge is not stable
            # about is not evidence.
            "passed": bool(va["passed"] and vb["passed"]),
            "agreed": agree,
            "evidence": va["evidence"] or vb["evidence"],
            "reason": va["reason"] or vb["reason"],
            "forward": va["passed"],
            "reverse": vb["passed"],
        })

    npass = sum(1 for c in criteria_out if c["passed"])
    out: dict[str, Any] = {
        "tier": "judge",
        "usable": True,
        "game": game,
        "model": model,
        "submission_id": sid,
        "passed": npass,
        "total": len(criteria_out),
        "score": npass / len(criteria_out) if criteria_out else 0.0,
        "instability": round(disagreements / len(ALL_CRITERIA), 3),
        "criteria": criteria_out,
        "pack": manifest,
        "passes": {"forward": {k: v for k, v in a.items() if k != "verdicts"},
                   "reverse": {k: v for k, v in b.items() if k != "verdicts"}},
        "cost_usd": round(a["cost_usd"] + b["cost_usd"], 4),
    }
    if keep_pack:
        keep_pack.parent.mkdir(parents=True, exist_ok=True)
        shutil.rmtree(keep_pack, ignore_errors=True)
        shutil.copytree(pack, keep_pack)
        out["pack_kept_at"] = str(keep_pack)
    shutil.rmtree(pack, ignore_errors=True)
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--submission", required=True, type=Path)
    ap.add_argument("--starter", required=True, type=Path)
    ap.add_argument("--game", required=True, choices=sorted(GAME_BRIEF))
    ap.add_argument("--frames", type=Path, default=None)
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--keep-pack", type=Path, default=None)
    ap.add_argument("--out", type=Path, default=None,
                    help="write the result here ATOMICALLY. Strongly preferred over "
                         "shell redirection: `> file` truncates and does not lock, so "
                         "two judge processes aimed at one path splice their JSON "
                         "together into a file that can still parse. That happened "
                         "three times in one session and produced a published number "
                         "that was one of two contradictory results chosen by a race.")
    ap.add_argument("--force", action="store_true",
                    help="overwrite a non-empty --out instead of refusing")
    a = ap.parse_args()
    if a.out and a.out.exists() and a.out.stat().st_size > 0 and not a.force:
        raise SystemExit(
            f"refusing to overwrite {a.out} ({a.out.stat().st_size} bytes). Another "
            f"judging already wrote it; pick a distinct path or pass --force.")
    result = judge(a.submission.resolve(), a.starter.resolve(), a.game,
                   a.frames, a.model, keep_pack=a.keep_pack)
    blob = json.dumps(result, indent=2)
    if a.out:
        tmp = a.out.with_suffix(a.out.suffix + f".{os.getpid()}.tmp")
        a.out.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_text(blob)
        os.replace(tmp, a.out)
        print(f"wrote {a.out} ({len(blob)} bytes)")
    else:
        print(blob)
