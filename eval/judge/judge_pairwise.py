#!/usr/bin/env python3
"""Comparative judging: "which of these two is better, and why?"

An absolute rubric saturates when every submission is good - 24 of 24 scored 13/13 on
the old one. A comparison cannot saturate: every pair is contested by construction.

That also gives a better noise estimate than the old `instability` metric. Instability
measured presentation-order sensitivity within ONE artifact, and turned out to be a
property of how borderline that artifact was (FINDINGS #21). Here noise is measured two
ways that are directly interpretable:

  * ORDER DISAGREEMENT - A-vs-B must agree with B-vs-A. The rate is the judge's
    self-consistency, measured on contested pairs rather than obvious ones.
  * INTRANSITIVITY - if A>B and B>C then A>C. The rate of violated triples is a noise
    floor for the whole ranking, not for a single comparison.

Ties are allowed but must be justified, so "indistinguishable" is a finding rather than
an escape hatch.
"""
from __future__ import annotations

import argparse, json, os, random, shutil, subprocess, tempfile
from itertools import combinations
from pathlib import Path
from typing import Any

from rubric_hard import HARD_CRITERIA

MODEL = "sonnet"

SCHEMA = {
    "type": "object",
    "properties": {
        "comparisons": {"type": "array", "items": {
            "type": "object",
            "properties": {
                "id": {"type": "string"},
                "evidence": {"type": "string", "description":
                             "Concrete: which frame, which file, which telemetry figure, "
                             "for BOTH submissions. Not a restatement of the question."},
                "winner": {"type": "string", "enum": ["A", "B", "indistinguishable"]},
                "reason": {"type": "string", "description":
                           "Why that verdict. If indistinguishable, say what you looked "
                           "for and why neither was ahead - this must be justified, not "
                           "a default."},
            },
            "required": ["id", "evidence", "winner", "reason"],
            "additionalProperties": False}},
        "overall": {"type": "string", "enum": ["A", "B", "indistinguishable"]},
        "overall_reason": {"type": "string"},
    },
    "required": ["comparisons", "overall", "overall_reason"],
    "additionalProperties": False,
}

PROMPT = ("Read BRIEF.md. Study both submissions in full: every frame in A/frames and "
          "B/frames as images, both telemetry files, and the source under A/code and "
          "B/code. Then answer each comparison, writing evidence for BOTH submissions "
          "before the verdict. Return the structured result.")


def _brief(game: str) -> str:
    L = ["# Comparative review", "",
         f"Two independent submissions of the same task: {game}", "",
         "They are labelled A and B. The labelling is arbitrary and carries no "
         "information. Both were built by competent agents and both work - the "
         "question is never whether one is broken, it is which is **better**, and why.",
         "",
         "For each criterion below, decide which submission is stronger. You may answer "
         "`indistinguishable`, but only with a justification saying what you looked for "
         "and why neither was ahead. A tie you cannot justify is not a tie.",
         "",
         "Write the evidence for BOTH submissions before giving a verdict. Cite frames "
         "by filename, code by path, telemetry by figure.",
         "",
         "Do not guess the engine or language of either, and do not let any such guess "
         "affect a verdict.", "",
         "## Criteria", ""]
    for cid, q, anchors in HARD_CRITERIA:
        L.append(f"### `{cid}`\n{q}\n")
        L.append("Reference points for what 'better' means here:")
        for lvl in (2, 3, 4):
            L.append(f"- {lvl}: {anchors[lvl]}")
        L.append("")
    L += ["Finally give an `overall` verdict for which submission is the better piece "
          "of work, with a reason."]
    return "\n".join(L)


def _stage(dst: Path, frames: Path | None, telemetry: dict | None, code: Path | None,
           max_code_chars: int = 60_000) -> None:
    dst.mkdir(parents=True, exist_ok=True)
    if frames and frames.exists():
        fd = dst / "frames"; fd.mkdir(exist_ok=True)
        for i, f in enumerate(sorted(frames.glob("*.png"))):
            shutil.copy(f, fd / f"frame_{i:02d}.png")
    if telemetry:
        (dst / "telemetry.json").write_text(json.dumps(telemetry, indent=2))
    if code and code.exists():
        cd = dst / "code"; cd.mkdir(exist_ok=True)
        used = 0
        for i, f in enumerate(sorted(code.rglob("*"))):
            if not f.is_file() or f.suffix.lower() not in {
                    ".rs", ".ts", ".cs", ".gd", ".js", ".mjs", ".py"}:
                continue
            try:
                txt = f.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            if used + len(txt) > max_code_chars:
                break
            (cd / f"{i:02d}{f.suffix.lower()}").write_text(txt)
            used += len(txt)


def compare(a: dict, b: dict, game: str, model: str = MODEL,
            seed: int | None = None, timeout_s: int = 1200) -> dict[str, Any]:
    """`a`/`b` are {'id','frames','telemetry','code'}. Returns verdicts in A/B terms."""
    pack = Path(tempfile.mkdtemp(prefix="pair-"))
    _stage(pack / "A", a.get("frames"), a.get("telemetry"), a.get("code"))
    _stage(pack / "B", b.get("frames"), b.get("telemetry"), b.get("code"))
    (pack / "BRIEF.md").write_text(_brief(game))
    argv = ["claude", "-p", PROMPT, "--model", model, "--output-format", "json",
            "--json-schema", json.dumps(SCHEMA, separators=(",", ":")),
            "--max-turns", "60", "--max-budget-usd", "3.0",
            "--setting-sources", "project", "--strict-mcp-config",
            "--exclude-dynamic-system-prompt-sections", "--no-session-persistence",
            "--permission-mode", "acceptEdits"]
    # check=False: the CLI exits non-zero for reasons that still produce a usable
    # verdict (a budget or turn ceiling reached after the answer was written). The
    # status is recorded on the unreadable-output path instead, where it separates
    # "the judge said something we could not read" from "the judge never ran".
    # The two failure modes are caught separately, and narrowly: a blind `except`
    # here would report a BUG IN THIS FILE as an unusable comparison.
    try:
        p = subprocess.run(argv, cwd=pack, capture_output=True, text=True,
                           timeout=timeout_s, check=False)
    except (subprocess.SubprocessError, OSError) as e:
        shutil.rmtree(pack, ignore_errors=True)
        return {"usable": False, "error": f"{type(e).__name__}: {e}",
                "a": a["id"], "b": b["id"]}
    try:
        raw = json.loads(p.stdout)
    except json.JSONDecodeError as e:
        shutil.rmtree(pack, ignore_errors=True)
        return {"usable": False, "error": f"{type(e).__name__}: {e}",
                "cli_exit": p.returncode, "cli_stderr": p.stderr[-2000:],
                "a": a["id"], "b": b["id"]}
    if isinstance(raw, list):
        r = [x for x in raw if isinstance(x, dict) and x.get("type") == "result"]
        raw = r[-1] if r else {}
    payload: dict[str, Any] = {}
    for cand in (raw.get("structured_output"), raw.get("result")):
        if isinstance(cand, dict) and "comparisons" in cand:
            payload = cand; break
        if isinstance(cand, str):
            try:
                v = json.loads(cand[cand.find("{"): cand.rfind("}") + 1])
                if "comparisons" in v:
                    payload = v; break
            # Narrow: the brace-slice may not be JSON (JSONDecodeError) or may decode to
            # a scalar, where `in` is not defined (TypeError). Anything else is a defect
            # here and must not be swallowed -- an empty `payload` scores every criterion
            # 0, which is a verdict, not an error.
            except (json.JSONDecodeError, TypeError):
                pass
    usage = raw.get("modelUsage") or {}
    shutil.rmtree(pack, ignore_errors=True)
    by = {c.get("id"): c for c in payload.get("comparisons", []) if isinstance(c, dict)}
    out = []
    for cid, _q, _a in HARD_CRITERIA:
        c = by.get(cid) or {}
        ev = str(c.get("evidence") or "").strip()
        w = c.get("winner") if len(ev) >= 20 else None
        out.append({"id": cid, "winner": w if w in ("A", "B", "indistinguishable") else None,
                    "evidence": ev[:400], "reason": str(c.get("reason") or "")[:300]})
    return {"usable": bool(by), "a": a["id"], "b": b["id"], "game": game,
            "criteria": out, "overall": payload.get("overall"),
            "overall_reason": str(payload.get("overall_reason") or "")[:400],
            "cost_usd": round(sum((m or {}).get("costUSD", 0) or 0
                                  for m in usage.values()), 4)}
