#!/usr/bin/env python3
"""Design judge: aesthetics and game feel, from frames and telemetry.

Sees no source code. Graded 0-4 with anchors (see design_criteria.py), because the
information in "does this look good" is all in the middle and a binary throws it away.
Carries NO WEIGHT until it separates a tuned fixture from a detuned one by more than
its own run-to-run spread.
"""
from __future__ import annotations

import argparse, json, os, shutil, subprocess, tempfile, uuid
from pathlib import Path
from typing import Any

from design_criteria import DESIGN_CRITERIA, SCALE

MODEL = "sonnet"

SCHEMA = {
    "type": "object",
    "properties": {"criteria": {"type": "array", "items": {
        "type": "object",
        "properties": {
            "id": {"type": "string"},
            "evidence": {"type": "string", "description":
                         "Which frames, and what in them. Or which telemetry figure. "
                         "Concrete and checkable, not a restatement of the question."},
            "reason": {"type": "string"},
            "score": {"type": "integer", "minimum": 0, "maximum": 4},
        },
        "required": ["id", "evidence", "reason", "score"],
        "additionalProperties": False}}},
    "required": ["criteria"], "additionalProperties": False,
}

PROMPT = ("Read BRIEF.md, then look at every PNG in frames/ in filename order as images. "
          "If telemetry.json is present, read it. Score each criterion in the brief "
          "using its anchors, writing the evidence and reason before the score. "
          "Return the structured result.")


def _brief(game: str, n_frames: int, telemetry: dict | None) -> str:
    L = ["# Design review brief", "",
         "You are looking at a game the way a player meets it: rendered frames from a "
         "real play session, in order. You are NOT reviewing source code and none is "
         "provided.", "",
         f"The game is: {game}", "",
         f"`frames/` holds {n_frames} PNGs captured across one session.",
         ]
    if telemetry:
        L += ["`telemetry.json` holds measurements taken while a bot played it - "
              "evidence of how the game is TUNED, not whether it works.", ""]
    L += ["", "## Scale", "", "```", SCALE, "```", "",
          "Use the anchors. A score means the same thing on every submission.", "",
          "## Criteria", ""]
    for cid, q, anchors in DESIGN_CRITERIA:
        L.append(f"### `{cid}`\n{q}\n")
        for lvl in sorted(anchors):
            L.append(f"- **{lvl}** — {anchors[lvl]}")
        L.append("")
    L += ["Write evidence and reason BEFORE the score. If you cannot point at a "
          "specific frame or figure, the score is 0.",
          "Do not guess the engine or language, and do not let any such guess affect a "
          "score."]
    return "\n".join(L)


def judge_design(frames: Path, game: str, telemetry: dict | None = None,
                 model: str = MODEL, timeout_s: int = 900) -> dict[str, Any]:
    pack = Path(tempfile.mkdtemp(prefix="dpack-"))
    fd = pack / "frames"; fd.mkdir()
    n = 0
    for i, f in enumerate(sorted(frames.glob("*.png"))):
        shutil.copy(f, fd / f"frame_{i:02d}.png"); n += 1
    if telemetry:
        (pack / "telemetry.json").write_text(json.dumps(telemetry, indent=2))
    (pack / "BRIEF.md").write_text(_brief(game, n, telemetry))

    argv = ["claude", "-p", PROMPT, "--model", model, "--output-format", "json",
            "--json-schema", json.dumps(SCHEMA, separators=(",", ":")),
            "--max-turns", "40", "--max-budget-usd", "2.0",
            "--setting-sources", "project", "--strict-mcp-config",
            "--exclude-dynamic-system-prompt-sections", "--no-session-persistence",
            "--permission-mode", "acceptEdits"]
    try:
        p = subprocess.run(argv, cwd=pack, capture_output=True, text=True,
                           timeout=timeout_s)
        raw = json.loads(p.stdout)
    except Exception as e:
        shutil.rmtree(pack, ignore_errors=True)
        return {"usable": False, "error": f"{type(e).__name__}: {e}"}
    if isinstance(raw, list):
        r = [x for x in raw if isinstance(x, dict) and x.get("type") == "result"]
        raw = r[-1] if r else {}
    items = []
    txt = raw.get("result")
    for cand in (raw.get("structured_output"), txt):
        if isinstance(cand, dict) and isinstance(cand.get("criteria"), list):
            items = cand["criteria"]; break
        if isinstance(cand, str):
            try:
                v = json.loads(cand[cand.find("{"): cand.rfind("}") + 1])
                if isinstance(v.get("criteria"), list):
                    items = v["criteria"]; break
            except Exception:
                pass
    by = {str(x.get("id")): x for x in items if isinstance(x, dict)}
    out = []
    for cid, q, _a in DESIGN_CRITERIA:
        it = by.get(cid) or {}
        ev = str(it.get("evidence") or "").strip()
        sc = it.get("score")
        sc = int(sc) if isinstance(sc, (int, float)) and len(ev) >= 20 else 0
        out.append({"id": cid, "score": sc, "evidence": ev[:500],
                    "reason": str(it.get("reason") or "")[:300]})
    usage = raw.get("modelUsage") or {}
    shutil.rmtree(pack, ignore_errors=True)
    total = sum(c["score"] for c in out)
    return {"usable": bool(items), "game": game, "model": model,
            "criteria": out, "total": total, "max": 4 * len(DESIGN_CRITERIA),
            "normalised": round(total / (4 * len(DESIGN_CRITERIA)), 3),
            "frames": n,
            "cost_usd": round(sum((m or {}).get("costUSD", 0) or 0
                                  for m in usage.values()), 4)}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--frames", required=True, type=Path)
    ap.add_argument("--game", required=True)
    ap.add_argument("--telemetry", type=Path, default=None)
    ap.add_argument("--out", required=True, type=Path)
    a = ap.parse_args()
    if a.out.exists() and a.out.stat().st_size > 0:
        raise SystemExit(f"refusing to overwrite {a.out}")
    tel = json.loads(a.telemetry.read_text()) if a.telemetry else None
    res = judge_design(a.frames.resolve(), a.game, tel)
    tmp = a.out.with_suffix(a.out.suffix + f".{os.getpid()}.tmp")
    a.out.parent.mkdir(parents=True, exist_ok=True)
    tmp.write_text(json.dumps(res, indent=2)); os.replace(tmp, a.out)
    print(f"wrote {a.out}: normalised={res.get('normalised')} "
          f"total={res.get('total')}/{res.get('max')} ${res.get('cost_usd')}")
